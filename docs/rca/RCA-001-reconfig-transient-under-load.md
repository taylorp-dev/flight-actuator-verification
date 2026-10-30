# RCA-001: Reconfiguration transient exceeds R9 at rated load

| Field | Value |
| --- | --- |
| Requirement | R9: overshoot <= 0.60 mm, settle within +/-0.25 mm in <= 0.80 s |
| Test | `tests/test_part_b_system.py::test_r9_reconfiguration_transient_baseline[rated]`; actuator level: `tests/test_part_a_actuator.py::test_a6_large_step_baseline[rated]` (A6) |
| Status | Root cause found, corrective action verified in SIL, baseline test kept as a strict xfail |

## Symptom

Channel B drift fault, steady attitude. When the voter latches B and drops from triplex to dual, the actuator command steps +4 mm (extension, against the load).

| Load | Overshoot | Settle | Result |
| --- | --- | --- | --- |
| Unloaded | 0.31 mm | 0.62 s | PASS |
| Rated (4,550 N) | 0.92 mm | 1.16 s | **FAIL** |

The actuator passed every original Part A acceptance test, including A2 (rate at rated load) and A5 (step response at rated load). In the system it appeared when a realistic fault, a realistic load, and a realistic sensor tolerance stack were combined. On the bare actuator it shows with any large step at rated load, which is what A6 now tests.

## Investigation

1. Re-ran with identical config and seed: repeatable, so not noise.
2. Swept load (0, 2,275, 4,550 N): overshoot grows with load. Load-dependent, not a voter problem.
3. Plotted velocity demand: at rated load the extension rate limit drops from 40 to 11.7 mm/s, so a 4 mm step saturates the actuator for roughly 0.3 s instead of 0.03 s.
4. Plotted the position-loop integrator: it keeps integrating error during saturation (windup), then overshoots once the rod arrives.
5. Checked why Part A missed it: A5 uses a 1 mm step, which never saturates the motor. The acceptance test was small-signal only.

## Root cause

Integrator windup in the actuator position loop during load-induced rate saturation. Contributing cause: the acceptance test (A5) only exercised small-signal steps, and the reconfiguration step size (set by the worst-case sensor tolerance stack x command gain) was never flowed down to the actuator spec.

## Corrective action

1. **Design (recommended to the actuator team):** conditional integration (anti-windup), so the integrator holds while the rate limit is active. `actuator.anti_windup: true`.
2. **Verification:** `test_r9_corrective_action_verified` runs R9 at every load condition with the fix. Rated load: overshoot 0.02 mm, settle 0.37 s. PASS.
3. **Regression:** baseline R9 at rated load kept as a strict xfail tied to this RCA. If the baseline ever starts passing unexpectedly, the suite goes red and someone has to look.
4. **Requirements:** a large-signal step test sized from the reconfiguration step is now in the actuator acceptance set as **A6** (4 mm step, overshoot <= 10 %, unloaded and at rated load; added 2026-10-29). As expected, the baseline actuator fails A6 at rated load (overshoot 28.8 %, kept as a strict xfail tied to this RCA, `test_a6_large_step_baseline[rated]`) and passes unloaded (9.5 %). With the corrective action it passes at both loads (`test_a6_large_step_corrective_action`: 4.1 % unloaded, 0.3 % rated). So the actuator spec now catches this defect on its own, without the full system.

## Lesson

The unit passed its own acceptance test and the system failed. The fix to the test set is to flow the system's real operating condition (here, the reconfiguration step size) down to the unit's acceptance test, which A6 now does. Test environment fidelity (here, realistic load during a fault) decides what you can catch.
