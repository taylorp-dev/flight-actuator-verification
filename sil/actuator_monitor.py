"""Actuator tracking monitor (runs in the actuator controller).

Flags ACT_NOT_TRACKING when the actuator is told to be somewhere else but is
not moving there: position error above a threshold while the measured speed is
near zero, held for a persistence time. That catches a jam and also a loss of
force (e.g. a lost motor channel at high load), without tripping when the
actuator is simply rate-limited on a big move (big error, but moving fast).

Uses the actuator's own feedback, as a real controller would. Tests check it
against the independent truth sensor.
"""

from __future__ import annotations

from collections import deque


class ActuatorMonitor:
    def __init__(self, err_threshold_mm: float, vel_threshold_mm_s: float,
                 persistence_s: float, vel_window_s: float, dt: float):
        self.err_thr = err_threshold_mm
        self.vel_thr = vel_threshold_mm_s
        self.persist_s = persistence_s
        self.dt = dt
        self.hist: deque = deque(maxlen=max(2, int(round(vel_window_s / dt)) + 1))
        self.timer = 0.0
        self.tripped = False
        self.trip_t: float | None = None

    @classmethod
    def from_cfg(cls, m: dict, dt: float) -> "ActuatorMonitor":
        return cls(m["err_threshold_mm"], m["vel_threshold_mm_s"],
                   m["persistence_s"], m["vel_window_s"], dt)

    def update(self, t: float, cmd_mm: float, feedback_mm: float) -> bool:
        self.hist.append(feedback_mm)
        if len(self.hist) < self.hist.maxlen:
            return self.tripped
        speed = abs(self.hist[-1] - self.hist[0]) / (self.dt * (len(self.hist) - 1))
        stuck = abs(cmd_mm - feedback_mm) > self.err_thr and speed < self.vel_thr
        self.timer = self.timer + self.dt if stuck else 0.0
        if not self.tripped and self.timer >= self.persist_s:
            self.tripped, self.trip_t = True, t
        return self.tripped
