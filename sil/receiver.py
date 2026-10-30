"""ARINC 429 receiver: per-word validity checks (requirements R1-R4).

A word is accepted only if parity is good. An accepted word updates the
channel's value and freshness. The channel is valid for a label only if the
latest accepted word has Normal SSM, is inside the physical range, and is fresh.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .arinc429 import SSM, LabelDef, decode_bnr


@dataclass
class LabelStatus:
    value: float = 0.0
    last_rx_t: float = -1e9
    ssm: SSM = SSM.NO_COMPUTED_DATA
    in_range: bool = False
    parity_rejects: int = 0
    words_accepted: int = 0

    def reasons(self, t: float, ld: LabelDef, stale_intervals: float) -> list[str]:
        r = []
        if t - self.last_rx_t > stale_intervals / ld.rate_hz + 1e-9:
            r.append("stale")
        if self.ssm != SSM.NORMAL:
            r.append(f"ssm_{self.ssm.name.lower()}")
        if not self.in_range:
            r.append("out_of_range")
        return r


@dataclass
class Receiver:
    labels: dict[str, LabelDef]
    stale_intervals: float = 3.0
    status: dict[str, LabelStatus] = field(default_factory=dict)

    def __post_init__(self):
        self.status = {name: LabelStatus() for name in self.labels}

    def receive(self, name: str, word: int, t: float) -> bool:
        ld = self.labels[name]
        d = decode_bnr(word, ld)
        st = self.status[name]
        if not d.parity_ok:
            st.parity_rejects += 1          # R1: discard the word entirely
            return False
        st.value = d.value
        st.ssm = d.ssm
        st.in_range = ld.min_valid <= d.value <= ld.max_valid
        st.last_rx_t = t
        st.words_accepted += 1
        return True

    def read(self, name: str, t: float) -> tuple[bool, float, list[str]]:
        """Return (valid, value, reasons_if_invalid) for a label at time t."""
        st = self.status[name]
        reasons = st.reasons(t, self.labels[name], self.stale_intervals)
        return (not reasons, st.value, reasons)
