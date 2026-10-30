# Test procedures

Plain-language procedures for every automated test in this repo: purpose, setup, numbered steps, the expected result, and next to each step the exact line of Python it runs (file and line number). They're written for a test engineer who wants to follow a test without reading the code first.

- **Levels:** **Unit** = one component alone (encoder, receiver, voter, actuator model, command law). **System** = components working together in closed loop. **Bench** = real hardware data (a Raspberry Pi sending channel A over a real Ethernet cable). The traceability matrix shows the same levels.
- **TC IDs:** `TC-<requirement>-<U|S|B><nn>`, one per test function. A parametrized test (several cases, or both load conditions) is one TC with a table of its cases.
- **Last result** in each TC comes from the run for record: FULL RUN, 127 of 127 tests (124 passed, 3 xfail), commit `19de3ef`, config `baae11ef69bb`, generated 2026-10-19T16:14:37 UTC. The bench TCs (Raspberry Pi) in that run replay the live recording in `bench_data/` (recorded 2026-10-19T16:12:43 UTC, Oct 19 morning Pacific). The official, current result is always the record: [reports/traceability.md](../../reports/traceability.md).
- **Running one test** (the "How to run" line in each TC) is a partial run: its report goes to `reports/dev/`, not for record. The record is a full run on committed code (USER-GUIDE section 7).
- **Plot data:** tests that are behind a figure also save the data they measured (`plot_data` fixture). Those steps say which file in `reports/data/` they write. The figures are drawn only from those files ([docs/EVIDENCE.md](../EVIDENCE.md)).
- Lab-rig style procedure for the bandwidth test, written for real hardware: [TP-A4-bandwidth.md](TP-A4-bandwidth.md).

## By file

| Procedures | Level | Test file | TCs |
| --- | --- | --- | --- |
| [Part A actuator](part-a-actuator.md) | Unit | [`tests/test_part_a_actuator.py`](../../tests/test_part_a_actuator.py) | 7 |
| [M1 bench actuator model](model-bench-actuator.md) | Unit | [`tests/test_model_bench_actuator.py`](../../tests/test_model_bench_actuator.py) | 2 |
| [Part B receiver](part-b-receiver.md) | Unit | [`tests/test_part_b_receiver.py`](../../tests/test_part_b_receiver.py) | 8 |
| [Part B voter](part-b-voter.md) | Unit | [`tests/test_part_b_voter.py`](../../tests/test_part_b_voter.py) | 9 |
| [Part B system](part-b-system.md) | System | [`tests/test_part_b_system.py`](../../tests/test_part_b_system.py) | 5 |
| [Part C actuator faults](part-c-actuator-faults.md) | System | [`tests/test_part_c_actuator_faults.py`](../../tests/test_part_c_actuator_faults.py) | 14 |
| [Bench link (Raspberry Pi)](bench-link.md) | Bench | [`tests/test_bench_link.py`](../../tests/test_bench_link.py) | 7 |

## Every test case

| TC | Requirement(s) | Level | Test function | Cases | Last result (run for record, commit 19de3ef) |
| --- | --- | --- | --- | --- | --- |
| [TC-A1-U01](part-a-actuator.md#tc-a1-u01-small-1-mm-step-unloaded) | A1 | Unit | `test_a1_small_signal_step_unloaded` | 1 | PASS |
| [TC-A2-U01](part-a-actuator.md#tc-a2-u01-maximum-extend-rate-unloaded-and-at-rated-load) | A2 | Unit | `test_a2_max_rate` | 2 | PASS (2 of 2) |
| [TC-A3-U01](part-a-actuator.md#tc-a3-u01-static-accuracy-and-backlash-at-the-rod) | A3 | Unit | `test_a3_accuracy_and_backlash` | 1 | PASS |
| [TC-A3-U02](part-a-actuator.md#tc-a3-u02-own-feedback-cannot-see-backlash) | A3 | Unit | `test_a3_own_feedback_cannot_see_backlash` | 1 | PASS |
| [TC-A4-U01](part-a-actuator.md#tc-a4-u01-position-bandwidth) | A4 | Unit | `test_a4_bandwidth` | 2 | PASS (2 of 2) |
| [TC-A5-U01](part-a-actuator.md#tc-a5-u01-small-1-mm-step-at-rated-load) | A5 | Unit | `test_a5_small_signal_step_rated_load` | 1 | PASS |
| [TC-A5-U02](part-a-actuator.md#tc-a5-u02-static-accuracy-at-rated-load) | A5 | Unit | `test_a5_accuracy_rated_load` | 1 | PASS |
| [TC-M1-U01](model-bench-actuator.md#tc-m1-u01-model-speed-matches-the-datasheet-at-three-force-points) | M1 | Unit | `test_m1_speed_force_matches_datasheet` | 3 | PASS |
| [TC-M1-U02](model-bench-actuator.md#tc-m1-u02-model-uses-the-datasheet-backlash) | M1 | Unit | `test_m1_backlash_matches_datasheet` | 1 | PASS |
| [TC-ICD-1-U01](part-b-receiver.md#tc-icd-1-u01-bnr-value-survives-encode-and-decode) | ICD-1 | Unit | `test_icd_bnr_round_trip` | 8 | PASS (8 of 8) |
| [TC-ICD-1-U02](part-b-receiver.md#tc-icd-1-u02-label-bits-are-stored-reversed) | ICD-1 | Unit | `test_icd_label_bits_are_reversed` | 1 | PASS |
| [TC-ICD-1-U03](part-b-receiver.md#tc-icd-1-u03-every-word-has-odd-parity) | ICD-1 | Unit | `test_icd_odd_parity` | 1 | PASS |
| [TC-R1-U01](part-b-receiver.md#tc-r1-u01-receiver-rejects-a-word-with-bad-parity) | R1 | Unit | `test_r1_bad_parity_rejected` | 1 | PASS |
| [TC-R2-U01](part-b-receiver.md#tc-r2-u01-failure-warning-and-no-computed-data-make-the-label-invalid) | R2 | Unit | `test_r2_ssm_invalid` | 2 | PASS (2 of 2) |
| [TC-R2-U02](part-b-receiver.md#tc-r2-u02-normal-ssm-makes-the-label-valid) | R2 | Unit | `test_r2_ssm_normal_valid` | 1 | PASS |
| [TC-R3-U01](part-b-receiver.md#tc-r3-u01-stale-boundary-at-3-transmit-intervals) | R3 | Unit | `test_r3_stale_boundary` | 1 | PASS |
| [TC-R4-U01](part-b-receiver.md#tc-r4-u01-values-outside-the-physical-range-are-invalid) | R4 | Unit | `test_r4_physical_range` | 4 | PASS (4 of 4) |
| [TC-R5-U01](part-b-voter.md#tc-r5-u01-voter-outputs-the-middle-of-three-values) | R5 | Unit | `test_r5_mid_value_select` | 6 | PASS |
| [TC-R6-U01](part-b-voter.md#tc-r6-u01-channel-fails-only-after-the-full-persistence-time) | R6 | Unit | `test_r6_fail_after_persistence` | 1 | PASS |
| [TC-R6-U02](part-b-voter.md#tc-r6-u02-threshold-has-margin-over-the-healthy-tolerance-stack) | R6 | Unit | `test_r6_threshold_has_margin_over_tolerance_stack` | 1 | PASS |
| [TC-R6-U03](part-b-voter.md#tc-r6-u03-channels-just-inside-threshold-never-fail) | R6 | Unit | `test_r6_within_threshold_never_fails` | 1 | PASS |
| [TC-R7-U01](part-b-voter.md#tc-r7-u01-a-single-one-frame-spike-is-ignored) | R7 | Unit | `test_r7_single_spike_ignored` | 1 | PASS |
| [TC-R7-U02](part-b-voter.md#tc-r7-u02-short-repeated-spikes-reset-the-counter-and-never-latch) | R7 | Unit | `test_r7_intermittent_spikes_reset_counter` | 1 | PASS |
| [TC-R8-U01](part-b-voter.md#tc-r8-u01-after-one-failure-the-voter-averages-the-other-two-and-annunciates) | R8 | Unit | `test_r8_dual_mode_average_and_annunciate` | 1 | PASS |
| [TC-R8-U02](part-b-voter.md#tc-r8-u02-a-disagreement-in-dual-mode-is-annunciated) | R8 | Unit | `test_r8_second_fault_in_dual_is_annunciated` | 1 | PASS |
| [TC-R8-U03](part-b-voter.md#tc-r8-u03-an-invalid-channel-is-left-out-of-the-vote) | R8 | Unit | `test_r8_invalid_channel_excluded` | 1 | PASS |
| [TC-FM-S01](part-b-system.md#tc-fm-s01-fault-matrix-with-one-sensor-fault-at-a-time) | R1, R2, R3, R4, R6, R7, R8, R10 | System | `test_fault_matrix` | 24 | PASS (24 of 24) |
| [TC-F002-S01](part-b-system.md#tc-f002-s01-finding-002-reproduced-at-the-old-threshold) | R6 | System | `test_finding002_reproduced_at_old_threshold` | 1 | PASS |
| [TC-R9-S01](part-b-system.md#tc-r9-s01-reconfiguration-transient-baseline-design) | R9 | System | `test_r9_reconfiguration_transient_baseline` | 2 | Unloaded PASS; rated OPEN DEFECT (expected fail, RCA-001) |
| [TC-R9-S02](part-b-system.md#tc-r9-s02-reconfiguration-transient-with-anti-windup-fix) | R9 | System | `test_r9_corrective_action_verified` | 2 | PASS (2 of 2) |
| [TC-R10-U01](part-b-system.md#tc-r10-u01-command-limits-hold-for-worst-case-inputs) | R10 | Unit | `test_r10_command_limits_worst_case_inputs` | 1 | PASS |
| [TC-R11-S01](part-c-actuator-faults.md#tc-r11-s01-hold-position-after-losing-one-motor) | R11 | System | `test_r11_motor_channel_loss_hold` | 2 | 1 PASS, 1 OPEN DEFECT (FINDING-003) |
| [TC-R11-S02](part-c-actuator-faults.md#tc-r11-s02-position-loss-after-a-motor-loss-is-annunciated) | R11 | System | `test_r11_if_position_is_lost_it_is_annunciated` | 2 | PASS |
| [TC-R11-S03](part-c-actuator-faults.md#tc-r11-s03-corrective-option-a-holds-at-every-load) | R11 | System | `test_r11_corrective_option_verified` | 2 | PASS |
| [TC-R12-S01](part-c-actuator-faults.md#tc-r12-s01-jam-is-detected-and-motor-drive-is-removed) | R12 | System | `test_r12_jam_detected_and_drive_removed` | 6 | PASS |
| [TC-R12-S02](part-c-actuator-faults.md#tc-r12-s02-jam-with-a-still-command-stays-latent) | R12 | System | `test_r12_jam_with_stationary_command_is_latent` | 1 | PASS |
| [TC-R12-S03](part-c-actuator-faults.md#tc-r12-s03-no-false-alarm-on-a-rate-limited-move-at-rated-load) | R12 | System | `test_r12_no_false_alarm_on_rate_limited_move_at_rated_load` | 1 | PASS |
| [TC-R12-S04](part-c-actuator-faults.md#tc-r12-s04-no-false-alarm-on-a-bandwidth-sine) | R12 | System | `test_r12_no_false_alarm_on_bandwidth_sine` | 1 | PASS |
| [TC-R12-S05](part-c-actuator-faults.md#tc-r12-s05-no-false-alarm-across-all-part-b-sensor-faults) | R12 | System | `test_r12_no_false_alarm_across_part_b_faults` | 4 | PASS |
| [TC-R12-S06](part-c-actuator-faults.md#tc-r12-s06-baseline-actuator-gives-false-alarms-open-defect) | R12 | System | `test_r12_no_false_alarm_baseline_actuator` | 1 | OPEN DEFECT (FINDING-005) |
| [TC-R13-S01](part-c-actuator-faults.md#tc-r13-s01-healthy-lanes-share-load-with-equalization) | R13 | System | `test_r13_healthy_lanes_share_load_with_equalization` | 1 | PASS |
| [TC-R13-S02](part-c-actuator-faults.md#tc-r13-s02-without-equalization-healthy-lanes-fight-and-trip) | R13 | System | `test_r13_without_equalization_healthy_lanes_fight_and_trip` | 1 | PASS |
| [TC-R13-S03](part-c-actuator-faults.md#tc-r13-s03-faulty-lane-is-disengaged-and-only-that-lane) | R13 | System | `test_r13_faulty_lane_disengaged` | 15 | PASS |
| [TC-R13-S04](part-c-actuator-faults.md#tc-r13-s04-undetected-lane-fault-stays-small) | R13 | System | `test_r13_undetected_lane_fault_stays_small` | 6 | PASS |
| [TC-R13-S05](part-c-actuator-faults.md#tc-r13-s05-guard-test-for-finding-004-drops-only-the-largest-outlier) | R13 | System | `test_r13_guard_monitor_isolates_only_the_largest_outlier` | 1 | PASS |
| [TC-ICD-1-B01](bench-link.md#tc-icd-1-b01-words-from-the-pi-decode-per-the-icd) | ICD-1, L1 | Bench | `test_l1_words_on_the_wire_decode_per_icd` | 1 | PASS |
| [TC-L1-B01](bench-link.md#tc-l1-b01-word-rate-and-timing-on-the-real-link) | L1 | Bench | `test_l1_rate_and_jitter_on_real_link` | 1 | PASS |
| [TC-L1-B02](bench-link.md#tc-l1-b02-no-false-stale-on-a-healthy-link) | L1, R3 | Bench | `test_l1_no_false_stale_on_healthy_link` | 1 | PASS |
| [TC-L1-B03](bench-link.md#tc-l1-b03-link-loss-flagged-stale-then-recovers) | L1, R3 | Bench | `test_l1_cable_pull_flagged_stale_and_recovers` | 1 | PASS |
| [TC-L1-B04](bench-link.md#tc-l1-b04-closed-loop-with-the-real-channel-a) | L1, R5 | Bench | `test_l1_closed_loop_with_real_channel_a` | 1 | PASS |
| [TC-L1-B05](bench-link.md#tc-l1-b05-closed-loop-through-the-link-loss) | L1, R8, R10 | Bench | `test_l1_closed_loop_cable_pull` | 1 | PASS |
| [TC-L2-B01](bench-link.md#tc-l2-b01-live-checks-agree-with-the-replay) | L2 | Bench | `test_l2_live_vs_replay_agree` | 1 | PASS |
