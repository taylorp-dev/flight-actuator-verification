"""Live bench helpers: record channel A, and drive the Raspberry Pi over SSH.

Used by tools/bench_capture.py (manual) and by `pytest --live` (automated).
LiveMonitor checks channel A during the run (L2), not just afterwards.

Control goes over SSH on Wi-Fi (e.g. taylor@dronepi.local). Data goes over the
direct Ethernet cable (Pi 192.168.2.1 -> laptop 192.168.2.2). Keeping them on
different paths is what lets the test take the Ethernet link down without
cutting its own control line.
"""

from __future__ import annotations

import hashlib
import shlex
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable

from .arinc429 import SSM, decode_bnr
from .link import DEFAULT_PORT, label_lookup, label_of, unpack_word
from .receiver import Receiver

PI_REPO = "~/actuator-verification"
PI_PYTHON = "~/av-env/bin/python"


class LiveMonitor:
    """Checks channel A while the words arrive, not afterwards (L2).

    Runs the same receiver code as the SIL on every word as it arrives, and
    re-checks validity every check period even when no words come in (so a
    link loss is caught live, at real time). Keeps what it saw: decode errors,
    word intervals, every valid/invalid transition, and how late its own checks
    ran (the PC is not a real-time computer, so that is measured, not assumed).
    """

    def __init__(self, labels, stale_intervals: float, check_period_s: float = 0.001):
        self.labels = labels
        self.lookup = label_lookup(labels)
        self.rx = Receiver(labels, stale_intervals=stale_intervals)
        self.check_period_s = check_period_s
        self.words = 0
        self.errors = {"label_not_in_icd": 0, "parity": 0, "sdi_not_1": 0, "ssm_not_normal": 0}
        self.pitch_t: list[float] = []
        self.pitch_sum = 0.0
        self.checks = 0
        self.max_check_gap_s = 0.0
        self.transitions: list[tuple[float, bool, list]] = []
        self._last_check = None
        self._valid = None
        self._fingerprint = hashlib.sha256()

    @staticmethod
    def row_text(t: float, word: int) -> str:
        """One word as the recording stores it (sil/link.py write_capture)."""
        return f"{t:.6f},{word:08X}\n"

    def on_word(self, t: float, word: int) -> None:
        self.words += 1
        self._fingerprint.update(self.row_text(t, word).encode())
        name = self.lookup.get(label_of(word))
        if not name:
            self.errors["label_not_in_icd"] += 1
            return
        d = decode_bnr(word, self.labels[name])
        self.errors["parity"] += not d.parity_ok
        self.errors["sdi_not_1"] += d.sdi != 1
        self.errors["ssm_not_normal"] += d.ssm != SSM.NORMAL
        if name == "pitch" and d.parity_ok:
            self.pitch_t.append(t)
            self.pitch_sum += d.value
        self.rx.receive(name, word, t)

    def on_check(self, t: float) -> None:
        if self._last_check is not None:
            self.max_check_gap_s = max(self.max_check_gap_s, t - self._last_check)
        self._last_check = t
        self.checks += 1
        valid, _, reasons = self.rx.read("pitch", t)
        if valid != self._valid:
            self.transitions.append((t, valid, reasons))
            self._valid = valid

    def results(self, pull_min_gap_s: float = 0.5) -> dict:
        """What the live checks saw. If the run had a link drop (a pitch gap of at
        least pull_min_gap_s), also when the live check flagged it and recovered."""
        pt = self.pitch_t
        gaps = [b - a for a, b in zip(pt, pt[1:])]
        out = {
            "words": self.words,
            "decode_errors": dict(self.errors),
            "pitch_words": len(pt),
            "pitch_mean_deg": round(self.pitch_sum / len(pt), 3) if pt else None,
            "words_sha256": self._fingerprint.hexdigest(),
            "checks": self.checks,
            "check_period_ms": round(self.check_period_s * 1000, 3),
            "max_check_gap_ms": round(self.max_check_gap_s * 1000, 2),
            "transitions": [{"t_s": round(t, 6), "valid": v, "reasons": r}
                            for t, v, r in self.transitions],
        }
        i = max(range(len(gaps)), key=gaps.__getitem__) if gaps else None
        if i is not None and gaps[i] >= pull_min_gap_s:
            t_last, t_back = pt[i], pt[i + 1]
            flag = next((t for t, v, _ in self.transitions if t > t_last and not v), None)
            back = next((t for t, v, _ in self.transitions if t >= t_back and v), None)
        else:
            t_last = t_back = flag = back = None
        # invalid stretches after the first valid check, anywhere except the link
        # drop itself (from the last word before it to the first word back)
        first_valid = next((t for t, v, _ in self.transitions if v), None)
        out["false_stale_outside_drop"] = sum(
            1 for t, v, _ in self.transitions
            if not v and first_valid is not None and t > first_valid
            and not (t_last is not None and t_last < t <= t_back))
        out["link_drop"] = None if t_last is None else {
            "last_word_s": round(t_last, 6), "first_word_back_s": round(t_back, 6),
            "cable_out_s": round(t_back - t_last, 2),
            "flagged_after_ms": None if flag is None else round((flag - t_last) * 1000, 1),
            "recovered_after_reconnect_ms": None if back is None else round((back - t_back) * 1000, 1),
        }
        return out


@contextmanager
def _fine_timer():
    """Windows wakes sleeping code on a ~15.6 ms tick by default, which would make
    a 1 ms live check run up to 16 ms late. Ask for a 1 ms tick for the capture
    (standard winmm call), and put it back after. No-op on other systems."""
    winmm = None
    if sys.platform == "win32":
        try:
            import ctypes
            winmm = ctypes.WinDLL("winmm")
            winmm.timeBeginPeriod(1)
        except Exception:
            winmm = None
    try:
        yield
    finally:
        if winmm is not None:
            winmm.timeEndPeriod(1)


def capture_udp(labels, stale_intervals: float, duration_s: float, *,
                port: int = DEFAULT_PORT, first_word_timeout_s: float = 20.0,
                after_bind: Callable[[], None] | None = None,
                status: Callable[[float, int, float, bool, list], None] | None = None,
                status_every_s: float = 0.5,
                monitor: LiveMonitor | None = None):
    """Receive ARINC 429 words over UDP and timestamp them on arrival.

    after_bind runs once the port is open (e.g. start the remote sender), so no
    words are missed. status(t, n_words, pitch, valid, reasons) is called every
    status_every_s with the live receiver state. monitor (optional) checks every
    word as it arrives and re-checks every monitor.check_period_s while waiting.
    Returns (rows, sender_ip)."""
    lookup = label_lookup(labels)
    rx = Receiver(labels, stale_intervals=stale_intervals)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", port))
    sock.settimeout(monitor.check_period_s if monitor else 0.05)
    rows: list[tuple[float, int]] = []
    sender = None
    try:
        with _fine_timer():
            if after_bind:
                after_bind()
            t_wait = time.perf_counter()
            t0 = None
            next_status = 0.0
            while True:
                try:
                    data, addr = sock.recvfrom(64)
                    now = time.perf_counter()
                    if t0 is None:
                        t0, sender = now, addr[0]
                    t = now - t0
                    word = unpack_word(data)
                    rows.append((t, word))
                    name = lookup.get(label_of(word))
                    if name:
                        rx.receive(name, word, t)
                    if monitor:
                        monitor.on_word(t, word)
                except socket.timeout:
                    if t0 is None:
                        if time.perf_counter() - t_wait > first_word_timeout_s:
                            raise TimeoutError(
                                f"no words on UDP {port} within {first_word_timeout_s:g} s: "
                                "is the sender running, pointed at this PC, and the firewall open?")
                        continue
                    t = time.perf_counter() - t0
                if monitor:
                    monitor.on_check(time.perf_counter() - t0)
                if status and t >= next_status:
                    valid, value, reasons = rx.read("pitch", t)
                    status(t, len(rows), value, valid, reasons)
                    next_status += status_every_s
                if t >= duration_s:
                    break
    finally:
        sock.close()
    return rows, sender


@dataclass
class PiRemote:
    """Runs commands on the Pi over SSH (key-based login, no password prompts)."""

    target: str = "taylor@dronepi.local"     # control path: Wi-Fi
    data_host: str = "192.168.2.2"           # where the Pi sends words: laptop on the cable
    iface: str = "eth0"
    timeout_s: float = 20.0

    def run(self, cmd: str, check: bool = True) -> subprocess.CompletedProcess:
        full = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", self.target, cmd]
        p = subprocess.run(full, capture_output=True, text=True, timeout=self.timeout_s)
        if check and p.returncode != 0:
            raise RuntimeError(f"ssh {self.target} {cmd!r} failed ({p.returncode}): "
                               f"{(p.stderr or p.stdout).strip()}")
        return p

    def background(self, cmd: str) -> None:
        """Start cmd on the Pi detached from this SSH session, so it keeps going
        even if the session drops."""
        self.run(f"setsid nohup sh -c {shlex.quote(cmd)} > /dev/null 2>&1 < /dev/null &")

    # --- steps used by the live test -----------------------------------------
    def check_ready(self) -> str:
        p = self.run(f"test -x {PI_PYTHON} && test -f {PI_REPO}/tools/pi_channel_a.py "
                     f"&& sudo -n /usr/sbin/ip link show {self.iface} > /dev/null && echo ok",
                     check=False)
        if p.returncode != 0 or "ok" not in p.stdout:
            raise RuntimeError(
                "Pi not ready for live tests. Check, on the Pi: the repo is at "
                f"{PI_REPO}, the venv at ~/av-env, and the sudo rule for 'ip link' "
                f"(docs/BENCH-GUIDE.md, live setup). ssh said: {(p.stderr or p.stdout).strip()}")
        return "ok"

    def update_code(self) -> str:
        p = self.run(f"git -C {PI_REPO} pull -q && git -C {PI_REPO} rev-parse --short HEAD",
                     check=False)
        if p.returncode == 0:
            return p.stdout.strip()
        return "unknown (git pull failed: " + (p.stderr.strip().splitlines() or ["?"])[0] + ")"

    def stop_sender(self) -> None:
        # "[p]i_..." so the pattern doesn't match the shell running pkill itself
        self.run("pkill -f '[p]i_channel_a.py' || true", check=False)

    def start_sender(self, duration_s: float) -> None:
        self.background(f"cd {PI_REPO} && {PI_PYTHON} tools/pi_channel_a.py "
                        f"--host {self.data_host} --duration {duration_s:g} "
                        f"> /tmp/av_sender.log 2>&1")

    def schedule_link_drop(self, at_s: float, for_s: float) -> None:
        """Automated cable pull: take the Ethernet port down, then back up.
        Runs detached on the Pi so it always brings the link back."""
        ip = f"sudo -n /usr/sbin/ip link set {self.iface}"
        self.background(f"sleep {at_s:g}; {ip} down; sleep {for_s:g}; {ip} up")

    def link_up(self) -> None:
        self.run(f"sudo -n /usr/sbin/ip link set {self.iface} up", check=False)
