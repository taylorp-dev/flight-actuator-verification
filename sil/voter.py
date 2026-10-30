"""Triplex mid-value-select voter with miscompare monitoring (R5-R8).

TRIPLEX : output the middle of three valid values. A channel whose difference
          from the middle exceeds `threshold` for `persistence_s` is latched failed.
DUAL    : output the average of the two remaining channels. A disagreement
          beyond threshold can be detected but not isolated, so it is annunciated.
SIMPLEX : pass the single remaining channel through, annunciated.
FAIL    : no valid input, hold last output, annunciated.

Generic pattern for illustration, not any specific aircraft's voter.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum


class Mode(str, Enum):
    TRIPLEX = "TRIPLEX"
    DUAL = "DUAL"
    SIMPLEX = "SIMPLEX"
    FAIL = "FAIL"


@dataclass
class VoterOutput:
    value: float
    mode: Mode
    failed: frozenset
    annunciations: tuple


@dataclass
class MidValueVoter:
    threshold: float = 2.0
    persistence_s: float = 0.10
    frame_s: float = 0.02
    n: int = 3
    failed: set = field(default_factory=set)
    _count: list = field(default_factory=list)
    _last: float = 0.0
    events: list = field(default_factory=list)   # (frame_index, channel, reason)
    _frame: int = 0

    def __post_init__(self):
        self._count = [0] * self.n
        self._needed = max(1, math.ceil(self.persistence_s / self.frame_s - 1e-9))

    def update(self, inputs: list[tuple[bool, float]]) -> VoterOutput:
        self._frame += 1
        avail = [i for i in range(self.n) if inputs[i][0] and i not in self.failed]
        ann: list[str] = []

        if len(avail) == 3:
            mid = sorted(inputs[i][1] for i in avail)[1]
            for i in avail:
                if abs(inputs[i][1] - mid) > self.threshold:
                    self._count[i] += 1
                    if self._count[i] >= self._needed:
                        self.failed.add(i)
                        self.events.append((self._frame, i, "miscompare"))
                else:
                    self._count[i] = 0
            avail = [i for i in avail if i not in self.failed]

        if len(avail) == 3:
            out, mode = sorted(inputs[i][1] for i in avail)[1], Mode.TRIPLEX
        elif len(avail) == 2:
            a, b = (inputs[i][1] for i in avail)
            out, mode = (a + b) / 2.0, Mode.DUAL
            if abs(a - b) > self.threshold:
                ann.append("DUAL_MISCOMPARE")
        elif len(avail) == 1:
            out, mode = inputs[avail[0]][1], Mode.SIMPLEX
        else:
            out, mode = self._last, Mode.FAIL

        if self.failed:
            ann.append("CHANNEL_FAILED:" + ",".join("ABC"[i] for i in sorted(self.failed)))
        if mode != Mode.TRIPLEX:
            ann.append(f"DEGRADED_{mode.value}")
        self._last = out
        return VoterOutput(out, mode, frozenset(self.failed), tuple(ann))
