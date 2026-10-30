# FINDING-005: Jam monitor false alarms, caused by the RCA-001 windup

| Field | Value |
| --- | --- |
| Requirement | R12: annunciate a jam within 0.30 s, and no false alarms in normal operation or Part B fault cases |
| Found by | The R12 false-alarm test (every Part B sensor fault, both channels' worth of maneuvers, swept across load) |
| Status | Open on the baseline actuator (strict xfail). Closed on the corrected actuator: threshold sized from data, margin guard added |

## Symptom

The actuator tracking monitor flags "not tracking" when position error is above a threshold while the actuator is barely moving, held for 0.1 s. The actuator was healthy in every case below; only the sensors had faults.

- First try, threshold 0.5 mm, rated load: false alarms on 6 of 24 channel-B fault cases.
- Raising the threshold didn't converge. Sweeping load showed the worst case is **not at rated load**: the healthy envelope reached **5.6 mm at about 75 % of rated load** (channel A drift while maneuvering).

| Load (fraction of rated) | Worst healthy error, baseline actuator | With RCA-001 anti-windup fix |
| --- | --- | --- |
| 0 % | 0.66 mm | 0.66 mm |
| 50 % | 1.22 to 1.87 mm | 0.66 mm |
| 75 % | 3.4 to 5.6 mm | 0.66 mm |
| 100 % | 0.85 mm | 0.66 mm |

## Root cause

A sensor fault makes the *command* stop or step suddenly. On the baseline actuator, the integrator winds up while the actuator is rate-limited (the RCA-001 defect), so it overshoots well past the command, then creeps back slowly. Big error + slow speed = looks stuck.

At mid loads the actuator is rate-limited during normal maneuvering but not stalled, which gives the windup the most time to build, so the worst case sits between the corners.

## Corrective action

- **Prerequisite:** adopt the RCA-001 anti-windup fix. With it, the healthy envelope is 0.66 mm at every load.
- Threshold set from that data: 0.66 mm + margin = **1.0 mm** (`config/sil.yaml`).
- `test_r12_no_false_alarm_across_part_b_faults` runs all 54 fault cases (9 Part B fault kinds x 3 channels x maneuvering and steady; 48 before `ssm_ncd` was added) at 0, 50, 75 and 100 % of rated load on the corrected actuator, and fails if the margin drops below 0.25 mm (currently 0.34 mm).
- `test_r12_no_false_alarm_baseline_actuator` keeps the baseline case as a strict xfail. It closes when RCA-001's fix is adopted.

## Lessons

- RCA-001 isn't just one transient missing its spec. Left in, it makes a sensible jam monitor impossible. That raises its priority.
- Sweep load, don't just test the corners. The worst case here was at 75 %.
- Size a monitor threshold from the measured healthy envelope plus margin, and guard the margin with a test (same as FINDING-002).

## Trade-off

A higher threshold means slower jam detection (0.17 s at 10 mm/s, still inside 0.30 s) and later annunciation of a slow back-drive (FINDING-003). A better long-term monitor compares the actuator to a model of a *healthy* actuator fed the same command, so normal overshoot isn't counted as error. Next step.
