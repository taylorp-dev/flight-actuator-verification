"""Part A: actuator characterization, bench acceptance test style (A1-A6).

Measurements are taken at the output rod (independent truth sensor), never
from the actuator's own feedback.
"""

import math

import numpy as np
import pytest

from sil import analysis as an
from sil.ema import EMA, EMAParams


def make_ema(cfg, load_n=0.0):
    return EMA(EMAParams.from_dict(cfg["actuator"]), load_n=load_n)


@pytest.mark.req("A1")
def test_a1_small_signal_step_unloaded(cfg, record_property, plot_data):
    spec = cfg["actuator_spec"]
    r = an.step_response(make_ema(cfg), spec["A1_step_mm"])
    record_property("rise_s", round(r.rise_time_s, 3))
    record_property("overshoot_pct", round(r.overshoot_pct, 1))
    plot_data.save("a1_step_unloaded", {"t_s": r.t, "cmd_mm": r.cmd, "rod_mm": r.pos},
                   load_n=0.0, rise_s=r.rise_time_s, overshoot_pct=r.overshoot_pct)
    assert r.rise_time_s <= spec["A1_rise_time_max_s"]
    assert r.overshoot_pct <= spec["A1_overshoot_max_pct"]


@pytest.mark.req("A2")
@pytest.mark.parametrize("direction", ["extend", "retract"])
def test_a2_max_rate(cfg, load_condition, direction, record_property):
    """Both directions: extend works against the load, retract is helped by it."""
    name, load_n = load_condition
    spec = cfg["actuator_spec"]
    limit = spec["A2_rate_min_unloaded_mm_s"] if load_n == 0 else spec["A2_rate_min_rated_mm_s"]
    rate = an.max_rate(make_ema(cfg, load_n), direction=+1.0 if direction == "extend" else -1.0)
    record_property("load", name)
    record_property("direction", direction)
    record_property("rate_mm_s", round(rate, 1))
    assert rate >= limit


@pytest.mark.req("A3")
def test_a3_accuracy_and_backlash(cfg, record_property):
    spec = cfg["actuator_spec"]
    acc, backlash = an.backlash_and_accuracy(make_ema(cfg))
    record_property("accuracy_mm", round(acc, 3))
    record_property("backlash_mm", round(backlash, 3))
    assert acc <= spec["A3_accuracy_max_mm"]
    assert backlash <= spec["A3_backlash_max_mm"]


@pytest.mark.req("A3")
def test_a3_own_feedback_cannot_see_backlash(cfg, record_property, plot_data):
    """Why the truth sensor matters: the unit's own sensor reports ~zero error.

    Two measurements of the same thing: (1) approach the same point from both
    sides and compare readings; (2) a slow 1 mm sine (8 s period, second cycle
    kept) and compare the position when the command crosses zero going up and
    going down. The sine is what the A3 figure shows.
    """
    ema = make_ema(cfg)
    readings = []
    for start in (-2.0, 2.0):
        an.run_profile(ema, lambda t: 0.0, 3.0, start)
        readings.append(ema.own_feedback)
    own_hyst = abs(readings[0] - readings[1])
    _, truth_hyst = an.backlash_and_accuracy(make_ema(cfg), points_mm=(0,))
    record_property("own_feedback_hysteresis_mm", round(own_hyst, 3))
    record_property("truth_hysteresis_mm", round(truth_hyst, 3))

    period = 8.0
    ema = make_ema(cfg)
    ema.reset(0.0)
    n = int(round(2 * period / an.DT))
    t = np.arange(n) * an.DT
    cmd = np.sin(2 * math.pi * t / period)
    rod, own = np.empty(n), np.empty(n)
    for k in range(n):
        rod[k] = ema.step(cmd[k], an.DT)
        own[k] = ema.own_feedback
    keep = t >= period
    tk, ck, rk, ok = t[keep], cmd[keep], rod[keep], own[keep]

    def crossing_gap(x):
        """x where the command crosses 0 rising, minus x where it crosses 0 falling."""
        up = np.where((ck[:-1] < 0) & (ck[1:] >= 0))[0]
        down = np.where((ck[:-1] > 0) & (ck[1:] <= 0))[0]
        return abs(float(x[up[0]] - x[down[0]]))

    sine_truth, sine_own = crossing_gap(rk), crossing_gap(ok)
    record_property("sine_truth_hysteresis_mm", round(sine_truth, 3))
    record_property("sine_own_feedback_hysteresis_mm", round(sine_own, 3))
    plot_data.save("a3_backlash_sine", {"t_s": tk, "cmd_mm": ck, "rod_err_mm": rk - ck,
                                         "own_err_mm": ok - ck},
                   period_s=period, sine_truth_hysteresis_mm=sine_truth,
                   sine_own_feedback_hysteresis_mm=sine_own)
    frac = cfg["actuator_spec"]["A3_own_feedback_max_frac"]
    assert own_hyst < frac * truth_hyst
    assert sine_own < frac * sine_truth


@pytest.mark.req("A4")
def test_a4_bandwidth(cfg, load_condition, record_property, plot_data):
    """Checked unloaded and at rated load (the A4 figure shows both)."""
    name, load_n = load_condition
    freqs = np.logspace(-1, 1.2, 22)
    gains, phases = an.frequency_response(make_ema(cfg, load_n), freqs)
    bw = an.bandwidth_hz(freqs, gains)
    record_property("load", name)
    record_property("bandwidth_hz", round(bw, 2))
    plot_data.save(f"a4_bode_{name}", {"freq_hz": freqs, "gain_db": gains, "phase_deg": phases},
                   load=name, load_n=load_n, bandwidth_hz=bw)
    assert bw >= cfg["actuator_spec"]["A4_bandwidth_min_hz"]


@pytest.mark.req("A5")
def test_a5_small_signal_step_rated_load(cfg, record_property, plot_data):
    spec = cfg["actuator_spec"]
    load_n = cfg["load_conditions"]["rated"]
    r = an.step_response(make_ema(cfg, load_n), spec["A1_step_mm"])
    record_property("rise_s", round(r.rise_time_s, 3))
    record_property("overshoot_pct", round(r.overshoot_pct, 1))
    plot_data.save("a5_step_rated", {"t_s": r.t, "cmd_mm": r.cmd, "rod_mm": r.pos},
                   load_n=load_n, rise_s=r.rise_time_s, overshoot_pct=r.overshoot_pct)
    assert r.rise_time_s <= spec["A5_rise_time_max_s"]
    assert r.overshoot_pct <= spec["A5_overshoot_max_pct"]


@pytest.mark.req("A5")
def test_a5_accuracy_rated_load(cfg, record_property):
    acc, _ = an.backlash_and_accuracy(make_ema(cfg, cfg["load_conditions"]["rated"]))
    record_property("accuracy_mm", round(acc, 3))
    assert acc <= cfg["actuator_spec"]["A3_accuracy_max_mm"]


# ------------------------------------------------- A6: large step (RCA-001 flow-down)
def a6_step(cfg, load_n, anti_windup=None):
    """4 mm step, the size of a reconfiguration step, on the bare actuator."""
    params = dict(cfg["actuator"])
    if anti_windup is not None:
        params["anti_windup"] = anti_windup
    ema = EMA(EMAParams.from_dict(params), load_n=load_n)
    return an.step_response(ema, cfg["actuator_spec"]["A6_step_mm"], duration_s=3.0)


@pytest.mark.req("A6")
def test_a6_large_step_baseline(cfg, load_condition, record_property, request):
    """Baseline actuator (anti-windup off). Rated load is the RCA-001 open defect,
    kept as a strict expected failure so it can't quietly disappear."""
    name, load_n = load_condition
    if load_n > 0:
        request.node.add_marker(pytest.mark.xfail(
            strict=True, raises=AssertionError,
            reason="RCA-001: integrator windup during rate saturation at rated load"))
    r = a6_step(cfg, load_n)
    record_property("load", name)
    record_property("overshoot_pct", round(r.overshoot_pct, 1))
    record_property("overshoot_mm", round(r.overshoot_pct * cfg["actuator_spec"]["A6_step_mm"] / 100, 3))
    record_property("rise_s", round(r.rise_time_s, 3))
    assert r.overshoot_pct <= cfg["actuator_spec"]["A6_overshoot_max_pct"]


@pytest.mark.req("A6")
def test_a6_large_step_corrective_action(cfg, load_condition, record_property):
    """RCA-001 corrective action (anti-windup on) passes A6 at both loads."""
    name, load_n = load_condition
    r = a6_step(cfg, load_n, anti_windup=True)
    record_property("load", name)
    record_property("overshoot_pct", round(r.overshoot_pct, 1))
    record_property("overshoot_mm", round(r.overshoot_pct * cfg["actuator_spec"]["A6_step_mm"] / 100, 3))
    record_property("rise_s", round(r.rise_time_s, 3))
    assert r.overshoot_pct <= cfg["actuator_spec"]["A6_overshoot_max_pct"]
