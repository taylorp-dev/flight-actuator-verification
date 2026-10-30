"""Measurement helpers used by the Part A acceptance tests.

Each function drives the EMA the way a bench test would and returns what an
independent measurement system would record (output rod position, not the
actuator's own feedback).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .ema import EMA

DT = 0.001  # 1 kHz sample rate, 10x+ above the bandwidth being verified


@dataclass
class StepResult:
    t: np.ndarray
    cmd: np.ndarray
    pos: np.ndarray
    rise_time_s: float
    overshoot_pct: float
    settling_time_s: float
    steady_error_mm: float


def run_profile(ema: EMA, cmd_fn, duration_s: float, start_mm: float = 0.0):
    ema.reset(start_mm)
    n = int(round(duration_s / DT))
    t = np.arange(n) * DT
    cmd = np.array([cmd_fn(ti) for ti in t])
    pos = np.empty(n)
    for i in range(n):
        pos[i] = ema.step(cmd[i], DT)
    return t, cmd, pos


def step_response(ema: EMA, amplitude_mm: float, start_mm: float = 0.0,
                  t_step: float = 0.1, duration_s: float = 2.0,
                  settle_band_mm: float = 0.1) -> StepResult:
    target = start_mm + amplitude_mm
    t, cmd, pos = run_profile(ema, lambda ti: target if ti >= t_step else start_mm,
                              duration_s, start_mm)
    after = t >= t_step
    ta, pa = t[after] - t_step, pos[after]
    base = pos[~after][-1] if (~after).any() else start_mm
    span = target - base
    frac = (pa - base) / span
    try:
        t10 = ta[np.argmax(frac >= 0.1)]
        t90 = ta[np.argmax(frac >= 0.9)]
        rise = float(t90 - t10) if (frac >= 0.9).any() else math.inf
    except ValueError:
        rise = math.inf
    overshoot = max(0.0, float((frac.max() - 1.0) * 100.0))
    outside = np.where(np.abs(pa - target) > settle_band_mm)[0]
    settling = float(ta[outside[-1]]) if len(outside) else 0.0
    return StepResult(t, cmd, pos, rise, overshoot, settling,
                      float(abs(pa[-1] - target)))


def max_rate(ema: EMA, direction: float = 1.0, stroke_frac: float = 0.8) -> float:
    """Command a large step and report the peak rod velocity (mm/s)."""
    span = ema.p.stroke_mm * stroke_frac
    start = -span / 2 * direction
    end = span / 2 * direction
    t, _, pos = run_profile(ema, lambda ti: end if ti >= 0.05 else start, 2.5, start)
    vel = np.gradient(pos, DT)
    return float(np.max(vel * direction))


def backlash_and_accuracy(ema: EMA, points_mm=(-15, -5, 0, 5, 15), approach_mm=2.0):
    """Approach each point from below and above; measure rod position after settling.

    Returns (max accuracy error, max hysteresis) in mm. Hysteresis is the
    backlash a truth sensor sees; the unit's own feedback cannot see it.
    """
    errors, hyst = [], []
    for p in points_mm:
        readings = []
        for side in (-1, 1):
            start = p + side * approach_mm
            _, _, pos = run_profile(ema, lambda ti, p=p: p, 3.0, start)
            readings.append(pos[-1])
            errors.append(abs(pos[-1] - p))
        hyst.append(abs(readings[0] - readings[1]))
    return float(max(errors)), float(max(hyst))


def frequency_response(ema: EMA, freqs_hz, amplitude_mm: float = 1.0, cycles: int = 6):
    """Sine dwell at each frequency. Returns gain (dB) and phase (deg) arrays."""
    gains, phases = [], []
    for f in freqs_hz:
        period = 1.0 / f
        duration = max(cycles * period, 1.0) + 2.0 * period
        t, cmd, pos = run_profile(
            ema, lambda ti, f=f: amplitude_mm * math.sin(2 * math.pi * f * ti), duration)
        keep = t >= (duration - cycles * period)      # drop the transient
        tt, c, y = t[keep], cmd[keep], pos[keep]
        y = y - y.mean()
        ref = np.exp(-1j * 2 * math.pi * f * tt)
        c_ph = np.sum(c * ref)
        y_ph = np.sum(y * ref)
        h = y_ph / c_ph
        gains.append(20 * math.log10(max(abs(h), 1e-6)))
        phases.append(math.degrees(np.angle(h)))
    return np.array(gains), np.array(phases)


def bandwidth_hz(freqs_hz, gains_db) -> float:
    """First frequency where gain falls below -3 dB (linear interpolation)."""
    freqs_hz = np.asarray(freqs_hz)
    below = np.where(gains_db <= -3.0)[0]
    if not len(below):
        return float(freqs_hz[-1])
    i = below[0]
    if i == 0:
        return float(freqs_hz[0])
    f0, f1 = freqs_hz[i - 1], freqs_hz[i]
    g0, g1 = gains_db[i - 1], gains_db[i]
    return float(f0 + (-3.0 - g0) * (f1 - f0) / (g1 - g0))
