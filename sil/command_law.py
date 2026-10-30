"""Simplified attitude-hold command law.

    error   = target - voted attitude
    command = gain * error, clipped to position limit, rate-limited  (R10)

Deliberately simple. Real control laws are far more complex; this exists so the
test can measure the system-level effect of a sensor fault at the actuator.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AttitudeHold:
    gain_mm_per_deg: float = 4.0
    target_deg: float = 0.0
    pos_limit_mm: float = 22.0
    rate_limit_mm_s: float = 60.0
    _last: float | None = None

    def reset(self, initial_mm: float = 0.0) -> None:
        self._last = initial_mm

    def update(self, voted_deg: float, dt: float) -> float:
        raw = self.gain_mm_per_deg * (self.target_deg - voted_deg)
        raw = max(-self.pos_limit_mm, min(self.pos_limit_mm, raw))
        if self._last is None:
            self._last = raw
        max_step = self.rate_limit_mm_s * dt
        cmd = self._last + max(-max_step, min(max_step, raw - self._last))
        self._last = cmd
        return cmd
