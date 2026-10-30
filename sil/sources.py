"""Simulated redundant attitude sources with fault injection.

Each channel shadows the same "true" attitude plus its own bias and noise, the
way three real sensors would. Faults are injected per channel and label.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .arinc429 import SSM, LabelDef, encode_bnr

FAULT_KINDS = (
    "frozen",        # value stops updating, word still looks perfect
    "drift",         # value walks away at `magnitude` units/s
    "bias_jump",     # value steps by `magnitude` (hardover-like)
    "spike",         # single word off by `magnitude`
    "bad_parity",    # parity bit corrupted
    "ssm_fail",      # SSM = Failure Warning
    "ssm_ncd",       # SSM = No Computed Data
    "dropout",       # label stops being transmitted
    "out_of_range",  # value replaced by `magnitude` (beyond physical range)
)


@dataclass
class Fault:
    kind: str
    channel: int
    label: str = "pitch"
    t_start: float = 0.0
    t_end: float = math.inf
    magnitude: float = 0.0

    def __post_init__(self):
        if self.kind not in FAULT_KINDS:
            raise ValueError(f"unknown fault kind {self.kind!r}")

    def active(self, t: float) -> bool:
        return self.t_start <= t < self.t_end


@dataclass
class SensorChannel:
    index: int
    labels: dict[str, LabelDef]
    bias: dict[str, float] = field(default_factory=dict)
    noise_sd: float = 0.0
    phase_s: float = 0.0
    seed: int = 0
    faults: list[Fault] = field(default_factory=list)

    def __post_init__(self):
        self._rng = np.random.default_rng(self.seed + 101 * self.index)
        self._next_tx = {name: self.phase_s for name in self.labels}
        self._frozen: dict[str, float] = {}
        self._spiked: set[int] = set()

    def _value(self, name: str, truth: float, t: float) -> float:
        v = truth + self.bias.get(name, 0.0) + self._rng.normal(0.0, self.noise_sd)
        for f in self.faults:
            if f.label != name or not f.active(t):
                continue
            if f.kind == "frozen":
                v = self._frozen.setdefault(name, v)
            elif f.kind == "drift":
                v += f.magnitude * (t - f.t_start)
            elif f.kind == "bias_jump":
                v += f.magnitude
            elif f.kind == "out_of_range":
                v = f.magnitude
            elif f.kind == "spike" and id(f) not in self._spiked:
                v += f.magnitude
                self._spiked.add(id(f))
        return v

    def next_due(self) -> float:
        """Time of this channel's next scheduled transmission (used by the
        real-time sender on the Raspberry Pi to sleep until then)."""
        return min(self._next_tx.values())

    def transmit(self, t: float, truth: dict[str, float]) -> list[tuple[str, int]]:
        """Return the (label name, 32-bit word) pairs sent at time t."""
        out = []
        for name, ld in self.labels.items():
            if t + 1e-9 < self._next_tx[name]:
                continue
            self._next_tx[name] += 1.0 / ld.rate_hz
            active = [f for f in self.faults if f.label == name and f.active(t)]
            if any(f.kind == "dropout" for f in active):
                continue
            ssm = SSM.NORMAL
            if any(f.kind == "ssm_fail" for f in active):
                ssm = SSM.FAILURE_WARNING
            elif any(f.kind == "ssm_ncd" for f in active):
                ssm = SSM.NO_COMPUTED_DATA
            word = encode_bnr(ld, self._value(name, truth[name], t), ssm,
                              sdi=self.index + 1,
                              corrupt_parity=any(f.kind == "bad_parity" for f in active))
            out.append((name, word))
        return out
