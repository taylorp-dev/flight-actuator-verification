# FINDING-002: Voter isolated the wrong channel

| Field | Value |
| --- | --- |
| Requirement | R6: fail the channel that miscompares (implies: the right one) |
| Found by | First run of the fault matrix (during the build), `frozen-chB` and `drift-chB` cases |
| Status | Closed. Threshold changed 2.0 -> 2.5 deg, guard test added, defect kept as a reproduction test |

## Symptom

Channel B frozen while the aircraft maneuvers. Expected: B latched failed. Actual: **C** latched failed, and the voted value then averaged the frozen B with A, reaching 3.2 deg of error (healthy band is +/-1.0 deg).

## Root cause

The worst-case healthy tolerance stack puts A at +1.0 deg and C at -1.0 deg, so A and C differ by 2.0 deg. The miscompare threshold was also 2.0 deg (exactly 2 x tolerance, zero margin). When B froze and the middle value moved to A or C, the outer healthy channel sat right on the threshold and noise tripped it for the full persistence time.

## Corrective action

- Threshold set to 2.5 deg (2 x tolerance + 0.5 deg margin for noise and sample latency). `config/sil.yaml`, commented with this finding.
- Guard test `test_r6_threshold_has_margin_over_tolerance_stack` fails if anyone sets the threshold back without margin.
- Reproduction test `test_finding002_reproduced_at_old_threshold` (added 2026-10-19, procedure [TC-F002-S01](../procedures/part-b-system.md#tc-f002-s01-finding-002-reproduced-at-the-old-threshold)) runs the original case at the old 2.0 deg and checks it still isolates the wrong channel, and at the configured threshold checks channel B is isolated. It proves the finding was real and that the margin is what fixed it; if the old setting ever stops failing, the model changed and this finding needs another look.
- Figure: `reports/figures/finding_wrong_channel_isolated.png`, drawn from the reproduction test's saved data in the run for record (`reports/data/finding002_threshold_old.csv` and `finding002_threshold_configured.csv`).

## Trade-off to raise with GNC

A larger threshold delays detection of slow faults (drift latency grows). That's the R6 vs R7 tuning tension. The test gives the numbers to decide with, it doesn't pick the number.
