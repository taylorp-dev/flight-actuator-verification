"""System-level SIL: sensors -> ARINC 429 -> receivers -> voter -> command law -> EMA.

Runs at 1 kHz. Sensors transmit at their label rate on independent phases,
the voter and command law run on a fixed frame, the actuator runs every tick.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
import yaml

from .actuator_monitor import ActuatorMonitor
from .arinc429 import LabelDef
from .command_law import AttitudeHold
from .ema import EMA, EMAParams
from .receiver import Receiver
from .sources import Fault, SensorChannel
from .voter import MidValueVoter, Mode

DT = 0.001
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "sil.yaml"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path) as fh:
        cfg = yaml.safe_load(fh)
    # line endings normalized, so a Windows checkout (CRLF) and Linux/CI (LF) give the same fingerprint
    cfg["_hash"] = hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:12]
    cfg["_path"] = str(path)
    return cfg


def label_defs(cfg: dict) -> dict[str, LabelDef]:
    out = {}
    for name, d in cfg["icd"]["labels"].items():
        out[name] = LabelDef(name=name, label_octal=int(str(d["label_octal"]), 8),
                             range_units=d["range_units"], sig_bits=d["sig_bits"],
                             min_valid=d["min_valid"], max_valid=d["max_valid"],
                             rate_hz=d["rate_hz"])
    return out


@dataclass
class RunResult:
    t: np.ndarray
    truth: np.ndarray
    channels: np.ndarray        # decoded value per channel (pitch), shape (n, 3)
    valid: np.ndarray           # receiver validity per channel (pitch), shape (n, 3)
    voted: np.ndarray
    mode: list
    cmd: np.ndarray
    pos: np.ndarray             # rod position (truth sensor)
    own_fb: np.ndarray          # actuator's own feedback
    detect_t: float | None      # first time a channel was latched failed
    failed: frozenset
    annunciations: set = field(default_factory=set)
    roll_voted: np.ndarray | None = None

    def metrics_after(self, t0: float, band: float) -> dict:
        """Overshoot past the final value and settling time, measured from t0."""
        keep = self.t >= t0
        tt, x = self.t[keep] - t0, self.pos[keep]
        final = float(np.mean(x[-200:]))
        start = float(x[0])
        direction = 1.0 if final >= start else -1.0
        overshoot = max(0.0, float(np.max((x - final) * direction)))
        outside = np.where(np.abs(x - final) > band)[0]
        settle = float(tt[outside[-1]]) if len(outside) else 0.0
        return {"final_mm": final, "start_mm": start, "overshoot_mm": overshoot,
                "settle_s": settle, "step_mm": final - start}


def run_scenario(cfg: dict, *, duration_s: float,
                 pitch_fn: Callable[[float], float] = lambda t: -2.0,
                 roll_fn: Callable[[float], float] = lambda t: 0.0,
                 faults: list[Fault] | None = None,
                 load_n: float = 0.0,
                 bias_deg: list[float] | None = None,
                 seed: int = 1,
                 channel_override: dict | None = None) -> RunResult:
    """channel_override: {index: source} replaces a simulated channel with any
    object that has transmit(t, truth), e.g. a ReplayChannel of words captured
    from the Raspberry Pi over a real Ethernet link."""
    labels = label_defs(cfg)
    s_cfg = cfg["sensors"]
    biases = bias_deg if bias_deg is not None else s_cfg["bias_deg"]
    faults = faults or []
    chans = [SensorChannel(index=i, labels=labels,
                           bias={"pitch": biases[i], "roll": biases[i]},
                           noise_sd=s_cfg["noise_sd_deg"],
                           phase_s=s_cfg["phase_offsets_s"][i], seed=seed,
                           faults=[f for f in faults if f.channel == i])
             for i in range(3)]
    for i, src in (channel_override or {}).items():
        chans[i] = src
    rxs = [Receiver(labels, stale_intervals=cfg["icd"]["stale_intervals"]) for _ in range(3)]
    v = cfg["voter"]
    voters = {name: MidValueVoter(v["threshold_deg"], v["persistence_s"], v["frame_s"])
              for name in labels}
    law = AttitudeHold(**cfg["command_law"])
    ema = EMA(EMAParams.from_dict(cfg["actuator"]), load_n=load_n)

    # start in equilibrium at the healthy commanded position
    healthy = sorted(pitch_fn(0.0) + b for b in biases)[1]
    x0 = max(-law.pos_limit_mm, min(law.pos_limit_mm,
                                     law.gain_mm_per_deg * (law.target_deg - healthy)))
    ema.reset(x0)
    law.reset(x0)
    # Part C tracking monitor runs alongside, observe-only here (no drive inhibit),
    # so Part B results are unchanged; it just records any false alarm.
    mon = ActuatorMonitor.from_cfg(cfg["actuator_monitor"], DT) if "actuator_monitor" in cfg else None

    n = int(round(duration_s / DT))
    frame_ticks = int(round(v["frame_s"] / DT))
    t = np.arange(n) * DT
    truth = np.empty(n); voted = np.empty(n); cmd = np.empty(n)
    pos = np.empty(n); fb = np.empty(n); rvoted = np.empty(n)
    chv = np.zeros((n, 3)); val = np.zeros((n, 3), dtype=bool)
    modes: list = []
    ann: set = set()
    cur_v, cur_rv, cur_cmd, cur_mode = healthy, roll_fn(0.0), x0, Mode.TRIPLEX
    detect_t = None

    for k in range(n):
        tk = t[k]
        tr = {"pitch": pitch_fn(tk), "roll": roll_fn(tk)}
        for i, ch in enumerate(chans):
            for name, word in ch.transmit(tk, tr):
                rxs[i].receive(name, word, tk)
        reads = [rx.read("pitch", tk) for rx in rxs]
        if k % frame_ticks == frame_ticks - 1:            # voter + command law frame
            out = voters["pitch"].update([(r[0], r[1]) for r in reads])
            rout = voters["roll"].update([(rx.read("roll", tk)[0], rx.read("roll", tk)[1])
                                          for rx in rxs])
            cur_v, cur_mode, cur_rv = out.value, out.mode, rout.value
            ann.update(out.annunciations)
            if out.failed and detect_t is None:
                detect_t = float(tk)
            cur_cmd = law.update(cur_v, v["frame_s"])
        pos[k] = ema.step(cur_cmd, DT)
        fb[k] = ema.own_feedback
        if mon is not None and mon.update(tk, cur_cmd, fb[k]):
            ann.add("ACT_NOT_TRACKING")
        truth[k], voted[k], cmd[k], rvoted[k] = tr["pitch"], cur_v, cur_cmd, cur_rv
        chv[k] = [r[1] for r in reads]
        val[k] = [r[0] for r in reads]
        modes.append(cur_mode)

    return RunResult(t, truth, chv, val, voted, modes, cmd, pos, fb, detect_t,
                     frozenset(voters["pitch"].failed), ann, rvoted)
