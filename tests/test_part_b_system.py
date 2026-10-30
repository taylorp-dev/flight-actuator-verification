"""Part B, system level: inject a fault at a sensor, measure the effect at the actuator.

Fault matrix (R1-R8, R10), reconfiguration transient (R9), command limits (R10).
"""

import copy
import math

import numpy as np
import pytest

from sil.command_law import AttitudeHold
from sil.sim import run_scenario
from sil.sources import Fault

pytestmark = pytest.mark.system


def maneuver(t: float) -> float:
    """Gentle pitch oscillation around -2 deg so a frozen channel gets exposed."""
    return -2.0 + 3.0 * math.sin(2 * math.pi * 0.3 * t)


# kind -> (magnitude, how the system must respond, requirements exercised)
FAULTS = {
    "frozen":       (0.0,   "isolate", ["R6", "R8"]),
    "drift":        (2.0,   "isolate", ["R6", "R8"]),
    "bias_jump":    (6.0,   "isolate", ["R6", "R8"]),
    "spike":        (15.0,  "ignore",  ["R7"]),
    "bad_parity":   (0.0,   "exclude", ["R1", "R8"]),
    "ssm_fail":     (0.0,   "exclude", ["R2", "R8"]),
    "dropout":      (0.0,   "exclude", ["R3", "R8"]),
    "out_of_range": (120.0, "exclude", ["R4", "R8"]),
}
MATRIX = [(k, ch) for k in FAULTS for ch in (0, 1, 2)]


@pytest.mark.parametrize("kind,channel", MATRIX,
                         ids=[f"{k}-ch{'ABC'[c]}" for k, c in MATRIX])
def test_fault_matrix(cfg, kind, channel, record_property, request, plot_data):
    magnitude, expect, reqs = FAULTS[kind]
    for r in reqs + ["R10"]:
        request.node.add_marker(pytest.mark.req(r))
    fault = Fault(kind, channel, "pitch", t_start=0.5, magnitude=magnitude)
    run = run_scenario(cfg, duration_s=4.0, pitch_fn=maneuver, faults=[fault])

    err = float(np.max(np.abs(run.voted - run.truth)))
    record_property("max_voted_error_deg", round(err, 2))
    record_property("final_mode", run.mode[-1].value)
    if run.detect_t is not None:
        record_property("detect_latency_ms", round((run.detect_t - 0.5) * 1000))
    # one cell of the fault matrix figure: what happened to the faulted channel
    plot_data.save(f"fault_matrix_{kind}_ch{'ABC'[channel]}", kind=kind, channel="ABC"[channel],
                   expect=expect,
                   failed=",".join("ABC"[i] for i in sorted(run.failed)) or "none",
                   excluded_by_receiver=bool(not run.valid[-1, channel]),
                   detect_latency_ms=None if run.detect_t is None else round((run.detect_t - 0.5) * 1000),
                   max_voted_error_deg=err, final_mode=run.mode[-1].value)

    # the bad channel never drives the voted value outside the healthy tolerance band
    # (+0.35 deg allowance for sample/frame latency during the maneuver)
    assert err <= cfg["voter"]["tolerance_deg"] + 0.35
    if expect == "isolate":
        assert run.failed == {channel} and run.mode[-1].value == "DUAL"
    elif expect == "ignore":
        assert not run.failed and run.mode[-1].value == "TRIPLEX"
    else:  # receiver-level exclusion: voter never needs to latch it
        assert not run.failed and not run.valid[-1, channel]
        assert run.mode[-1].value == "DUAL"
    # R10 holds through every fault
    law = cfg["command_law"]
    assert np.max(np.abs(run.cmd)) <= law["pos_limit_mm"] + 1e-9
    assert np.max(np.abs(np.diff(run.cmd))) <= law["rate_limit_mm_s"] * cfg["voter"]["frame_s"] + 1e-9


# ------------------------------------------------------- FINDING-002 reproduction
@pytest.mark.req("R6")
def test_finding002_reproduced_at_old_threshold(cfg, record_property, plot_data):
    """FINDING-002, kept as a regression test: the defect is reproduced on purpose.

    Channel B frozen in the middle during the maneuver. At the old threshold
    (2.0 deg = exactly 2 x the 1.0 deg sensor tolerance, zero margin) noise trips
    a HEALTHY channel instead of B. At the configured threshold (2.5 deg, with
    margin) B is isolated. This test asserts both, which proves the finding was
    real and that the margin is what fixed it. If the old setting ever stops
    failing, the model changed and FINDING-002 needs a fresh look.
    """
    old_threshold = 2.0
    fault = Fault("frozen", 1, "pitch", t_start=0.5)
    results = {}
    for label, threshold in (("old", old_threshold), ("configured", cfg["voter"]["threshold_deg"])):
        c = copy.deepcopy(cfg)
        c["voter"]["threshold_deg"] = threshold
        run = run_scenario(c, duration_s=4.0, pitch_fn=maneuver, faults=[fault])
        err = run.voted - run.truth
        failed = ",".join("ABC"[i] for i in sorted(run.failed)) or "none"
        record_property(f"{label}_threshold_deg", threshold)
        record_property(f"{label}_failed_channel", failed)
        record_property(f"{label}_max_voted_error_deg", round(float(np.max(np.abs(err))), 2))
        plot_data.save(f"finding002_threshold_{label}", {"t_s": run.t, "voted_err_deg": err},
                       threshold_deg=threshold, failed_channel=failed,
                       max_voted_error_deg=float(np.max(np.abs(err))),
                       tolerance_deg=cfg["voter"]["tolerance_deg"])
        results[label] = run
    assert results["old"].failed and 1 not in results["old"].failed, \
        "old 2.0 deg threshold no longer isolates the wrong channel: FINDING-002 needs review"
    assert results["configured"].failed == {1}, "configured threshold must isolate channel B"


# ------------------------------------------------------------------- R9
R9_FAULT_T = 0.5          # s, when channel B starts drifting


def r9_run(cfg, load_n):
    """Channel B drifts high; while it passes channel A, the voter selects A.
    When B is latched failed, the voter drops to the A/C average: a step at the
    actuator that opposes the load."""
    return run_scenario(cfg, duration_s=4.5, pitch_fn=lambda t: -2.0,
                        faults=[Fault("drift", 1, "pitch", t_start=R9_FAULT_T, magnitude=2.0)],
                        load_n=load_n)


def r9_check(cfg, run, record_property, plot_data=None, name=None):
    spec = cfg["system_spec"]
    assert run.detect_t is not None and run.failed == {1}
    m = run.metrics_after(run.detect_t, spec["R9_settle_band_mm"])
    record_property("step_mm", round(m["step_mm"], 2))
    record_property("overshoot_mm", round(m["overshoot_mm"], 3))
    record_property("settle_s", round(m["settle_s"], 3))
    if plot_data is not None:            # saved before the pass/fail checks, so a failing case is kept too
        plot_data.save(name, {"t_s": run.t, "truth_deg": run.truth, "ch_a_deg": run.channels[:, 0],
                              "ch_b_deg": run.channels[:, 1], "ch_c_deg": run.channels[:, 2],
                              "voted_deg": run.voted, "cmd_mm": run.cmd, "rod_mm": run.pos},
                       detect_t_s=run.detect_t, final_mm=m["final_mm"], step_mm=m["step_mm"],
                       overshoot_mm=m["overshoot_mm"], settle_s=m["settle_s"],
                       overshoot_limit_mm=spec["R9_overshoot_max_mm"],
                       settle_band_mm=spec["R9_settle_band_mm"],
                       settle_limit_s=spec["R9_settle_time_max_s"],
                       anti_windup=cfg["actuator"]["anti_windup"], fault_t_s=R9_FAULT_T,
                       fault="drift on channel B", failed=",".join("ABC"[i] for i in sorted(run.failed)),
                       final_mode=run.mode[-1].value)
    assert m["overshoot_mm"] <= spec["R9_overshoot_max_mm"]
    assert m["settle_s"] <= spec["R9_settle_time_max_s"]


@pytest.mark.req("R9")
@pytest.mark.parametrize("load_name", [
    "unloaded",
    pytest.param("rated", marks=pytest.mark.xfail(
        reason="RCA-001: integrator windup during rate saturation at rated load")),
])
def test_r9_reconfiguration_transient_baseline(cfg, load_name, record_property, plot_data):
    """Baseline design. Passes unloaded, fails at rated load (the headline finding)."""
    run = r9_run(cfg, cfg["load_conditions"][load_name])
    record_property("load", load_name)
    r9_check(cfg, run, record_property, plot_data, f"r9_baseline_{load_name}")


@pytest.mark.req("R9")
def test_r9_corrective_action_verified(fresh_cfg, load_condition, record_property, plot_data):
    """RCA-001 corrective action: conditional integration (anti-windup). Must pass at every load."""
    name, load_n = load_condition
    fresh_cfg["actuator"]["anti_windup"] = True
    record_property("load", name)
    r9_check(fresh_cfg, r9_run(fresh_cfg, load_n), record_property, plot_data, f"r9_antiwindup_{name}")


# ------------------------------------------------------------------ R10
@pytest.mark.req("R10")
@pytest.mark.level("Unit")      # command law alone, not the closed loop
def test_r10_command_limits_worst_case_inputs(cfg, record_property):
    law = AttitudeHold(**cfg["command_law"])
    law.reset(0.0)
    dt = cfg["voter"]["frame_s"]
    rng = np.random.default_rng(7)
    inputs = np.concatenate([[180.0, -180.0] * 50, rng.uniform(-180, 180, 2000),
                             [0.0] * 50, [1e6, -1e6]])
    cmds = [law.update(x, dt) for x in inputs]
    steps = np.abs(np.diff([0.0] + cmds))
    record_property("max_cmd_mm", round(float(np.max(np.abs(cmds))), 2))
    record_property("max_rate_mm_s", round(float(steps.max() / dt), 1))
    assert np.max(np.abs(cmds)) <= law.pos_limit_mm + 1e-9
    assert steps.max() <= law.rate_limit_mm_s * dt + 1e-9
