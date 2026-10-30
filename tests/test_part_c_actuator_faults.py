"""Part C: faults inside the actuation system (R11-R13).

Inspired by the jam-tolerant, multi-motor actuator designs in public fly-by-wire
patents. Not a model of anyone's actual actuator.

  R11  lose one of two motor channels: can the actuator still hold position?
  R12  jam: does the tracking monitor catch it, fast, without false alarms?
  R13  three lanes on one surface: equalization and force-fight monitoring.
"""

import math

import numpy as np
import pytest

from sil import analysis as an
from sil.actuator_monitor import ActuatorMonitor
from sil.ema import EMA, EMAParams
from sil.force_fight import ForceFightParams, run_force_fight
from sil.sim import DT, run_scenario
from sil.sources import Fault

from .test_part_b_system import FAULTS, maneuver

pytestmark = pytest.mark.system


def make_ema(cfg, load_n=0.0):
    return EMA(EMAParams.from_dict(cfg["actuator"]), load_n=load_n)


# ------------------------------------------------------------------- R11
def motor_loss_run(cfg, load_n, t_fail=1.0, duration_s=None):
    """Hold position 0, lose one motor at t_fail, watch the rod for R11_hold_s."""
    spec = cfg["system_spec"]
    duration_s = duration_s or t_fail + spec["R11_hold_s"]
    ema = make_ema(cfg, load_n)
    ema.reset(0.0)
    mon = ActuatorMonitor.from_cfg(cfg["actuator_monitor"], DT)
    n = int(round(duration_s / DT))
    t = np.arange(n) * DT
    x = np.empty(n)
    for k in range(n):
        if t[k] >= t_fail and ema.motors_healthy == ema.p.n_motors:
            ema.fail_motor()
        x[k] = ema.step(0.0, DT)
        mon.update(t[k], 0.0, ema.own_feedback)
    return t, x, mon, ema


def r11_check(cfg, load_n, record_property, plot_data=None, name=None):
    spec = cfg["system_spec"]
    t, x, mon, ema = motor_loss_run(cfg, load_n)
    dev = float(np.max(np.abs(x[t >= 1.0])))
    record_property("load_n", load_n)
    record_property("stall_after_loss_n", round(ema.stall_force_effective))
    record_property("max_deviation_mm", round(dev, 3))
    record_property("monitor_trip_after_s", None if mon.trip_t is None else round(mon.trip_t - 1.0, 2))
    if plot_data is not None:            # saved before the check, so the failing case is kept too
        plot_data.save(name, {"t_s": t, "rod_mm": x}, load_n=load_n, t_fail_s=1.0,
                       stall_after_loss_n=ema.stall_force_effective, max_deviation_mm=dev,
                       monitor_trip_t_s=mon.trip_t, hold_limit_mm=spec["R11_hold_max_mm"])
    assert dev <= spec["R11_hold_max_mm"]


@pytest.mark.req("R11")
@pytest.mark.parametrize("load_name", [
    "unloaded",
    pytest.param("rated", marks=pytest.mark.xfail(
        reason="FINDING-003: one motor's stall force is below rated load; rod is back-driven")),
])
def test_r11_motor_channel_loss_hold(cfg, load_name, record_property, plot_data):
    """Baseline sizing: each motor gives half the total stall force. At rated load
    (70 % of total stall = 140 % of one motor) the actuator cannot hold."""
    r11_check(cfg, cfg["load_conditions"][load_name], record_property,
              plot_data, f"r11_motor_loss_baseline_{load_name}")


@pytest.mark.req("R11")
def test_r11_if_position_is_lost_it_is_annunciated(cfg, load_condition, record_property):
    """Whenever the actuator can't hold after a motor loss, the tracking monitor
    must say so (it must never drift silently)."""
    name, load_n = load_condition
    t, x, mon, _ = motor_loss_run(cfg, load_n)
    drifted = float(np.max(np.abs(x[t >= 1.0]))) > cfg["actuator_monitor"]["err_threshold_mm"]
    record_property("load", name)
    record_property("drifted_past_threshold", drifted)
    record_property("monitor_trip_after_s", None if mon.trip_t is None else round(mon.trip_t - 1.0, 2))
    assert mon.tripped == drifted


@pytest.mark.req("R11")
def test_r11_corrective_option_verified(fresh_cfg, load_condition, record_property, plot_data):
    """FINDING-003 option A: size each motor to carry rated load alone
    (total stall doubled, so one motor = the original total). Must hold at every load."""
    name, load_n = load_condition
    fresh_cfg["actuator"]["stall_force_n"] *= 2
    record_property("load", name)
    r11_check(fresh_cfg, load_n, record_property, plot_data, f"r11_motor_loss_option_a_{name}")


# ------------------------------------------------------------------- R12
def jam_run(cfg, load_n, *, t_jam=0.5, start_mm=-5.0, rate_mm_s=None,
            stationary=False, duration_s=1.5):
    """Command a ramp (or hold still), jam the screw at t_jam, let the monitor act."""
    rate = rate_mm_s if rate_mm_s is not None else cfg["system_spec"]["R12_cmd_rate_mm_s"]
    ema = make_ema(cfg, load_n)
    ema.reset(start_mm)
    mon = ActuatorMonitor.from_cfg(cfg["actuator_monitor"], DT)
    n = int(round(duration_s / DT))
    t = np.arange(n) * DT
    cmd = np.full(n, start_mm) if stationary else start_mm + rate * t
    x = np.empty(n); demand = np.empty(n); integ = np.empty(n)
    for k in range(n):
        if t[k] >= t_jam and not ema.jammed:
            ema.jam()
        x[k] = ema.step(cmd[k], DT)
        if mon.update(t[k], cmd[k], ema.own_feedback) and not ema.drive_inhibited:
            ema.inhibit_drive()
        demand[k], integ[k] = ema.last_demand, ema.s.integ
    return t, cmd, x, demand, integ, mon


@pytest.mark.req("R12")
@pytest.mark.parametrize("start_mm", [-15.0, -5.0, 5.0], ids=["near-retract", "mid", "near-extend"])
def test_r12_jam_detected_and_drive_removed(cfg, load_condition, start_mm, record_property,
                                           plot_data, request):
    name, load_n = load_condition
    spec = cfg["system_spec"]
    t, cmd, x, demand, integ, mon = jam_run(cfg, load_n, start_mm=start_mm)
    if name == "rated" and start_mm == -5.0:         # the case the R12 jam figure shows
        plot_data.save(f"r12_jam_{request.node.callspec.id}",
                       {"t_s": t, "cmd_mm": cmd, "rod_mm": x, "drive_mm_s": demand},
                       load_n=load_n, start_mm=start_mm, t_jam_s=0.5, monitor_trip_t_s=mon.trip_t,
                       cmd_rate_mm_s=spec["R12_cmd_rate_mm_s"],
                       monitor_threshold_mm=cfg["actuator_monitor"]["err_threshold_mm"])
    assert mon.tripped, "jam not annunciated"
    latency = mon.trip_t - 0.5
    after = t > mon.trip_t + 0.01
    record_property("load", name)
    record_property("jam_detect_s", round(latency, 3))
    assert latency <= spec["R12_detect_max_s"]
    assert np.all(demand[after] == 0.0), "motor drive not removed"
    assert np.ptp(integ[after]) == 0.0, "controller still winding up after annunciation"


@pytest.mark.req("R12")
def test_r12_jam_with_stationary_command_is_latent(cfg, record_property):
    """Characterization, not a pass/fail on the design: a jam while the command
    is not moving cannot be seen by a tracking monitor. It stays latent until the
    next move. That's why real systems add a periodic built-in test (BIT) move.
    This test pins that behavior so nobody assumes otherwise."""
    _, _, _, _, _, mon = jam_run(cfg, cfg["load_conditions"]["rated"], stationary=True)
    record_property("annunciated", mon.tripped)
    assert not mon.tripped


@pytest.mark.req("R12")
def test_r12_no_false_alarm_on_rate_limited_move_at_rated_load(cfg, record_property):
    """A big step at rated load leaves a big position error for about a second,
    but the actuator is moving at its rate limit, so the monitor must stay quiet."""
    ema = make_ema(cfg, cfg["load_conditions"]["rated"])
    mon = ActuatorMonitor.from_cfg(cfg["actuator_monitor"], DT)
    span = 0.8 * ema.p.stroke_mm
    t, cmd, _ = an.run_profile(ema, lambda ti: span / 2 if ti >= 0.05 else -span / 2, 3.0, -span / 2)
    ema.reset(-span / 2)
    for k in range(len(t)):
        ema.step(cmd[k], DT)
        mon.update(t[k], cmd[k], ema.own_feedback)
    record_property("step_mm", span)
    assert not mon.tripped


@pytest.mark.req("R12")
def test_r12_no_false_alarm_on_bandwidth_sine(cfg):
    ema = make_ema(cfg)
    mon = ActuatorMonitor.from_cfg(cfg["actuator_monitor"], DT)
    f = cfg["actuator_spec"]["A4_bandwidth_min_hz"]
    ema.reset(0.0)
    for k in range(int(4.0 / DT)):
        c = 1.0 * math.sin(2 * math.pi * f * k * DT)
        ema.step(c, DT)
        mon.update(k * DT, c, ema.own_feedback)
    assert not mon.tripped


def worst_healthy_slow_error(run, mon_cfg) -> float:
    """Largest monitor threshold this run would have tripped: the max, over every
    persistence-length window where the actuator is 'not moving', of the smallest
    command-vs-feedback error in that window."""
    win = int(round(mon_cfg["vel_window_s"] / DT))
    n = int(round(mon_cfg["persistence_s"] / DT))
    fb = run.own_fb
    err = np.abs(run.cmd - fb)
    speed = np.abs(np.r_[np.zeros(win), (fb[win:] - fb[:-win]) / (win * DT)])
    slow_err = np.where(speed < mon_cfg["vel_threshold_mm_s"], err, 0.0)
    return float(np.lib.stride_tricks.sliding_window_view(slow_err, n).min(axis=1).max())


def part_b_envelope(cfg, load_n):
    """Run every Part B sensor fault on every channel (maneuvering and steady) at
    one load. Returns (cases that tripped the monitor, worst healthy error, case)."""
    mon_cfg = cfg["actuator_monitor"]
    tripped, worst, worst_case = [], 0.0, ""
    for kind, (mag, _, _) in FAULTS.items():
        for ch in range(3):
            for pname, pfn in (("maneuver", maneuver), ("steady", lambda t: -2.0)):
                run = run_scenario(cfg, duration_s=3.0, pitch_fn=pfn, load_n=load_n,
                                   faults=[Fault(kind, ch, "pitch", t_start=0.5, magnitude=mag)])
                tag = f"{kind}-ch{'ABC'[ch]}-{pname}"
                if "ACT_NOT_TRACKING" in run.annunciations:
                    tripped.append(tag)
                w = worst_healthy_slow_error(run, mon_cfg)
                if w > worst:
                    worst, worst_case = w, tag
    return tripped, worst, worst_case


def _envelope_fractions():
    from sil.sim import load_config
    return load_config()["actuator_monitor"]["envelope_load_fractions"]


@pytest.mark.req("R12")
@pytest.mark.parametrize("load_frac", _envelope_fractions(),
                         ids=[f"{int(f * 100)}pct_rated" for f in _envelope_fractions()])
def test_r12_no_false_alarm_across_part_b_faults(fresh_cfg, load_frac, record_property):
    """Every Part B sensor fault, every channel, maneuvering and steady, swept
    across load (the worst case is NOT at a corner). Sensor faults jerk the command
    around, but the actuator is healthy, so: no actuator alarm, and the threshold
    keeps its margin over the worst healthy case (FINDING-005 guard).
    Runs on the corrected actuator (RCA-001 anti-windup), which the monitor needs."""
    fresh_cfg["actuator"]["anti_windup"] = True
    mon_cfg = fresh_cfg["actuator_monitor"]
    load = load_frac * fresh_cfg["load_conditions"]["rated"]
    tripped, worst, worst_case = part_b_envelope(fresh_cfg, load)
    margin = mon_cfg["err_threshold_mm"] - worst
    record_property("load_n", round(load))
    record_property("cases", len(FAULTS) * 3 * 2)
    record_property("false_alarms", len(tripped))
    record_property("worst_healthy_mm", round(worst, 3))
    record_property("worst_case", worst_case)
    record_property("margin_mm", round(margin, 3))
    assert not tripped, tripped
    assert margin >= mon_cfg["margin_min_mm"]


@pytest.mark.req("R12")
@pytest.mark.xfail(strict=True, reason="FINDING-005: monitor needs the RCA-001 anti-windup fix; "
                                       "baseline windup gives false jam alarms")
def test_r12_no_false_alarm_baseline_actuator(cfg, record_property):
    """Same check on the BASELINE actuator (windup still in) at the worst load found
    in the sweep. Kept as a strict xfail: it closes when RCA-001's fix is adopted."""
    load = 0.75 * cfg["load_conditions"]["rated"]
    tripped, worst, worst_case = part_b_envelope(cfg, load)
    record_property("load_n", round(load))
    record_property("false_alarms", len(tripped))
    record_property("worst_healthy_mm", round(worst, 3))
    record_property("worst_case", worst_case)
    assert not tripped, tripped


# ------------------------------------------------------------------- R13
def ff_params(cfg, **over):
    d = dict(cfg["force_fight"])
    d.update(over)
    return ForceFightParams.from_dict(d)


def _save_ff(plot_data, name, r, cfg, **meta):
    """Save a force-fight run for the R13 figure: lane forces and surface position."""
    meta["rig_offsets_mm"] = " ".join(f"{v:+.2f}" for v in cfg["force_fight"]["rig_offsets_mm"])
    plot_data.save(name, {"t_s": r.t, "force_a_n": r.force[:, 0], "force_b_n": r.force[:, 1],
                          "force_c_n": r.force[:, 2], "surface_mm": r.x},
                   disengaged=";".join(f"{'ABC'[int(k)]}@{v:.3f}" for k, v in r.disengaged.items()) or "none",
                   **meta)


@pytest.mark.req("R13")
def test_r13_healthy_lanes_share_load_with_equalization(cfg, record_property, plot_data):
    p = ff_params(cfg)
    r = run_force_fight(p, rig_offsets_mm=cfg["force_fight"]["rig_offsets_mm"], duration_s=10.0)
    fight = r.max_fight()
    record_property("max_fight_n", round(fight))
    _save_ff(plot_data, "r13_equalization_on_healthy", r, cfg, eq_gain_mm_per_n=p.eq_gain_mm_per_n)
    assert fight <= cfg["system_spec"]["R13_fight_max_n"]
    assert not r.disengaged


@pytest.mark.req("R13")
def test_r13_without_equalization_healthy_lanes_fight_and_trip(cfg, record_property, plot_data):
    """Why equalization is required: with integrators and no equalization, two
    healthy lanes inside tolerance wind up against each other until the monitor
    disengages a lane that has nothing wrong with it."""
    p = ff_params(cfg, eq_gain_mm_per_n=0.0)
    r = run_force_fight(p, rig_offsets_mm=cfg["force_fight"]["rig_offsets_mm"], duration_s=10.0)
    record_property("max_fight_n", round(r.max_fight()))
    _save_ff(plot_data, "r13_equalization_off_healthy", r, cfg, eq_gain_mm_per_n=0.0)
    record_property("healthy_lane_disengaged_at_s", {int(k): round(v, 2) for k, v in r.disengaged.items()})
    assert r.max_fight() > cfg["system_spec"]["R13_fight_max_n"]
    assert r.disengaged, "expected a false disengage without equalization"


FF_CASES = [(lane, off) for lane in (0, 1, 2) for off in (2.0, -2.0, 5.0, -5.0, 10.0)]
FF_FIGURE_CASE = (0, 5.0)    # lane A sensor +5 mm: the faulty-lane case shown in the R13 figure


@pytest.mark.req("R13")
@pytest.mark.parametrize("lane,offset_mm", FF_CASES,
                         ids=[f"lane{'ABC'[l]}{o:+.0f}mm" for l, o in FF_CASES])
def test_r13_faulty_lane_disengaged(cfg, lane, offset_mm, record_property, plot_data, request):
    spec = cfg["system_spec"]
    p = ff_params(cfg)
    r = run_force_fight(p, rig_offsets_mm=cfg["force_fight"]["rig_offsets_mm"], duration_s=4.0,
                        fault_lane=lane, fault_offset_mm=offset_mm, fault_t=1.0)
    if (lane, offset_mm) == FF_FIGURE_CASE:          # the case the R13 figure shows
        _save_ff(plot_data, f"r13_faulty_{request.node.callspec.id}", r, cfg,
                 eq_gain_mm_per_n=p.eq_gain_mm_per_n, fault_lane="ABC"[lane],
                 fault_offset_mm=offset_mm, fault_t_s=1.0)
    record_property("disengaged", {int(k): round(v - 1.0, 3) for k, v in r.disengaged.items()})
    record_property("peak_surface_mm", round(r.max_abs_x(1.0), 2))
    record_property("final_surface_mm", round(float(r.x[-1]), 3))
    assert list(r.disengaged) == [lane], "wrong lane(s) disengaged"
    assert abs(r.x[-1]) <= spec["R13_final_err_max_mm"]


@pytest.mark.req("R13")
@pytest.mark.parametrize("offset_mm", [0.5, 1.0, 1.5, -1.5, 1.6, -1.6])
def test_r13_undetected_lane_fault_stays_small(cfg, offset_mm, record_property):
    """Below the monitor threshold, the other two lanes outvote the bad one (the
    surface moves by about a third of the offset). Worst cases on every lane."""
    p = ff_params(cfg)
    worst = 0.0
    for lane in (0, 1, 2):
        r = run_force_fight(p, rig_offsets_mm=cfg["force_fight"]["rig_offsets_mm"], duration_s=4.0,
                            fault_lane=lane, fault_offset_mm=offset_mm, fault_t=1.0)
        if not r.disengaged:
            worst = max(worst, abs(float(r.x[-1])))
        else:
            assert list(r.disengaged) == [lane]
    record_property("worst_undetected_surface_mm", round(worst, 3))
    assert worst <= cfg["system_spec"]["R13_undetected_err_max_mm"]


@pytest.mark.req("R13")
def test_r13_guard_monitor_isolates_only_the_largest_outlier(cfg, record_property):
    """FINDING-004 regression guard. The first monitor version disengaged every
    lane over threshold. On a large fault all three lanes cross together and all
    three were dropped: surface lost. Re-run the old logic to prove the guard
    still catches it, then check the fixed logic."""
    old = ff_params(cfg, isolate_largest_only=False)
    r_old = run_force_fight(old, rig_offsets_mm=cfg["force_fight"]["rig_offsets_mm"], duration_s=3.0,
                            fault_lane=0, fault_offset_mm=5.0, fault_t=1.0)
    record_property("old_logic_lanes_disengaged", len(r_old.disengaged))
    assert len(r_old.disengaged) == 3       # the defect, reproduced
    new = ff_params(cfg)
    r_new = run_force_fight(new, rig_offsets_mm=cfg["force_fight"]["rig_offsets_mm"], duration_s=3.0,
                            fault_lane=0, fault_offset_mm=5.0, fault_t=1.0)
    assert list(r_new.disengaged) == [0]
