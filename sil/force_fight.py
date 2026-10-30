"""Triplex active/active actuation on one control surface: force fight.

Three actuator lanes push on the same surface. Each lane has its own position
sensor and its own controller, so small rigging/sensor differences make each
lane want a slightly different position. Bolted to one surface, they push
against each other: force fight.

Two protections are modeled, both common in industry:
  - Force equalization: each lane bleeds its integrator toward the mean force
    of the other lanes, so healthy lanes share the load instead of fighting.
  - Force-fight monitor: a lane whose force differs from the mean of the others
    by more than a threshold for longer than a persistence time is disengaged
    (switched to bypass, zero force). Only the largest outlier is disengaged.

Simplified on purpose: lanes are force sources with PI + damping control, the
surface is a mass with a constant opposing load. Units: mm, N, kg, s.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class ForceFightParams:
    kp_n_per_mm: float = 1000.0
    ki_n_per_mm_s: float = 5000.0
    kd_n_s_per_mm: float = 11.0
    surface_mass_kg: float = 200.0
    lane_force_max_n: float = 6500.0
    load_n: float = 4550.0
    eq_gain_mm_per_n: float = 0.001        # 0 = equalization off
    monitor_threshold_n: float = 1000.0
    monitor_persistence_s: float = 0.20
    isolate_largest_only: bool = True      # False reproduces FINDING-004
    dt_s: float = 0.0005

    @classmethod
    def from_dict(cls, d: dict) -> "ForceFightParams":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ForceFightResult:
    t: np.ndarray
    x: np.ndarray                 # surface position (truth), mm
    force: np.ndarray             # lane forces, shape (n, 3), N
    fight: np.ndarray             # lane force minus mean of other engaged lanes, (n, 3)
    disengaged: dict = field(default_factory=dict)   # lane -> time

    def max_fight(self, t0: float = 0.0, t1: float | None = None) -> float:
        m = (self.t >= t0) & (self.t < (t1 if t1 is not None else np.inf))
        return float(np.abs(self.fight[m]).max()) if m.any() else 0.0

    def max_abs_x(self, t0: float = 0.0) -> float:
        return float(np.abs(self.x[self.t >= t0]).max())


def run_force_fight(p: ForceFightParams, *, rig_offsets_mm, duration_s: float,
                    fault_lane: int | None = None, fault_offset_mm: float = 0.0,
                    fault_t: float = 1.0, cmd_mm: float = 0.0) -> ForceFightResult:
    """Hold the surface at cmd_mm. Optionally a lane's sensor offset jumps at fault_t
    (a sensor or rigging fault). Returns time histories and disengage times."""
    dt = p.dt_s
    n = int(round(duration_s / dt))
    base = np.asarray(rig_offsets_mm, float)
    x = v = 0.0
    integ = np.full(3, p.load_n / 3.0 / p.ki_n_per_mm_s)     # start sharing the load
    engaged = np.ones(3, bool)
    persist = np.zeros(3)
    out_t = np.arange(n) * dt
    out_x = np.empty(n); out_f = np.zeros((n, 3)); out_d = np.zeros((n, 3))
    dis: dict = {}

    for k in range(n):
        t = out_t[k]
        offs = base.copy()
        if fault_lane is not None and t >= fault_t:
            offs[fault_lane] += fault_offset_mm
        err = cmd_mm - (x + offs)                      # each lane sees its OWN sensor
        raw = p.kp_n_per_mm * err + p.ki_n_per_mm_s * integ - p.kd_n_s_per_mm * v
        f = np.where(engaged, np.clip(raw, -p.lane_force_max_n, p.lane_force_max_n), 0.0)

        idx = np.flatnonzero(engaged)
        fight = np.zeros(3)
        for i in idx:
            others = idx[idx != i]
            if len(others):
                fight[i] = f[i] - f[others].mean()

        for i in idx:
            if abs(raw[i]) < p.lane_force_max_n:       # no integration while saturated
                integ[i] += dt * (err[i] - p.eq_gain_mm_per_n * fight[i])

        # force-fight monitor (needs three lanes to tell which one is the outlier)
        if len(idx) == 3:
            over = np.abs(fight) > p.monitor_threshold_n
            persist = np.where(over, persist + dt, 0.0)
            ready = [i for i in idx if persist[i] >= p.monitor_persistence_s]
            if ready:
                if p.isolate_largest_only:
                    ready = [max(ready, key=lambda i: abs(fight[i]))]
                for i in ready:
                    engaged[i] = False
                    dis[int(i)] = float(t)
                persist[:] = 0.0

        a = 1000.0 * (f.sum() - p.load_n) / p.surface_mass_kg   # mm/s^2
        v += a * dt
        x += v * dt
        out_x[k] = x; out_f[k] = f; out_d[k] = fight

    return ForceFightResult(out_t, out_x, out_f, out_d, dis)
