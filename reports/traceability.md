# Requirements Traceability Matrix

- **Run: FULL RUN (127 of 127 tests), record**
- Generated: 2026-10-30T01:13:46+00:00
- Git commit: `d716c1f`
- Config: `config/sil.yaml` (sha256 `f1bfb3f5a287`)
- ICD: Generic Rotorcraft A
- Load conditions: {'unloaded': 0.0, 'rated': 4550.0}
- Requirements traced: 22/22 (100.0%)
- Tests: 127 (passed 124, xfail 3)
- Tests by level: Unit 47, System 73, Bench 7
- Suite runtime: 47.5 s

Levels: **Unit** = one component alone; **System** = components together in closed loop; **Bench** = real hardware data (Raspberry Pi over a real Ethernet cable). Written procedures for every test: [docs/procedures/](../docs/procedures/README.md).

| Req | Stage | Requirement | Level | Tests | Test names | Passed | Verdict | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ICD-1 | Interface | ARINC 429 BNR words shall be encoded per the ICD (label, SDI, sign, resolution, SSM, odd parity). | Unit + Bench | 11 | `test_l1_words_on_the_wire_decode_per_icd`, `test_icd_bnr_round_trip` x8, `test_icd_label_bits_are_reversed`, `test_icd_odd_parity` | 11 | **PASS** |  |
| A1 | Actuator | Small-signal step response (1 mm, unloaded) shall have rise time <= 0.15 s and overshoot <= 10 %. | Unit | 1 | `test_a1_small_signal_step_unloaded` | 1 | **PASS** |  |
| A2 | Actuator | Maximum rate shall be >= 35 mm/s unloaded and >= 10 mm/s at rated opposing load. | Unit | 2 | `test_a2_max_rate` x2 | 2 | **PASS** |  |
| A3 | Actuator | Static position accuracy shall be <= 0.10 mm and backlash <= 0.15 mm, measured at the output rod. | Unit | 2 | `test_a3_accuracy_and_backlash`, `test_a3_own_feedback_cannot_see_backlash` | 2 | **PASS** |  |
| A4 | Actuator | Position bandwidth (-3 dB) shall be >= 2.5 Hz. | Unit | 2 | `test_a4_bandwidth` x2 | 2 | **PASS** |  |
| A5 | Actuator | At rated opposing load, small-signal step overshoot shall be <= 10 %, rise time <= 0.15 s, accuracy <= 0.10 mm. | Unit | 2 | `test_a5_small_signal_step_rated_load`, `test_a5_accuracy_rated_load` | 2 | **PASS** |  |
| M1 | Model | The bench actuator model (Actuonix L16-P) shall reproduce the manufacturer datasheet speed-force points within 5 % and use the datasheet backlash. | Unit | 4 | `test_m1_speed_force_matches_datasheet` x3, `test_m1_backlash_matches_datasheet` | 4 | **PASS** |  |
| R1 | Receiver | The receiver shall reject words with bad parity. | Unit + System | 4 | `test_r1_bad_parity_rejected`, `test_fault_matrix` x3 | 4 | **PASS** |  |
| R2 | Receiver | The receiver shall treat SSM Failure Warning or No Computed Data as invalid. | Unit + System | 6 | `test_r2_ssm_invalid` x2, `test_r2_ssm_normal_valid`, `test_fault_matrix` x3 | 6 | **PASS** |  |
| R3 | Receiver | The receiver shall declare a label stale if not updated within 3 nominal transmit intervals. | Unit + System + Bench | 6 | `test_l1_no_false_stale_on_healthy_link`, `test_l1_cable_pull_flagged_stale_and_recovers`, `test_r3_stale_boundary`, `test_fault_matrix` x3 | 6 | **PASS** |  |
| R4 | Receiver | The receiver shall reject values outside the physical range. | Unit + System | 7 | `test_r4_physical_range` x4, `test_fault_matrix` x3 | 7 | **PASS** |  |
| R5 | Voter | With three valid sources, the voter shall output the middle value. | Unit + Bench | 7 | `test_l1_closed_loop_with_real_channel_a`, `test_r5_mid_value_select` x6 | 7 | **PASS** |  |
| R6 | Voter | The voter shall fail a channel that miscompares beyond threshold for longer than the persistence time. | Unit + System | 13 | `test_fault_matrix` x9, `test_finding002_reproduced_at_old_threshold`, `test_r6_fail_after_persistence`, `test_r6_threshold_has_margin_over_tolerance_stack`, `test_r6_within_threshold_never_fails` | 13 | **PASS** |  |
| R7 | Voter | The voter shall not fail a channel on a single short spike. | Unit + System | 5 | `test_fault_matrix` x3, `test_r7_single_spike_ignored`, `test_r7_intermittent_spikes_reset_counter` | 5 | **PASS** |  |
| R8 | Voter | After one channel failure, the voter shall continue on the remaining two and annunciate. | Unit + System + Bench | 25 | `test_l1_closed_loop_cable_pull`, `test_fault_matrix` x21, `test_r8_dual_mode_average_and_annunciate`, `test_r8_second_fault_in_dual_is_annunciated`, `test_r8_invalid_channel_excluded` | 25 | **PASS** |  |
| R9 | System | After a single-channel failure, the actuator reconfiguration transient shall overshoot <= 0.60 mm and settle within +/-0.25 mm in <= 0.80 s. | System | 4 | `test_r9_reconfiguration_transient_baseline` x2, `test_r9_corrective_action_verified` x2 | 3 | **OPEN DEFECT** | RCA-001: integrator windup during rate saturation at rated load |
| R10 | System | The actuator command shall never exceed the position or rate limits, whatever the input. | Unit + System + Bench | 26 | `test_l1_closed_loop_cable_pull`, `test_fault_matrix` x24, `test_r10_command_limits_worst_case_inputs` | 26 | **PASS** |  |
| L1 | Bench link | Channel A sent from a separate computer over a real Ethernet link shall decode per the ICD, arrive at the nominal label rate (mean interval within 2 %) without gaps long enough to trip the stale check, and a link loss shall be flagged stale within 3 intervals and recover automatically. | Bench | 6 | `test_l1_words_on_the_wire_decode_per_icd`, `test_l1_rate_and_jitter_on_real_link`, `test_l1_no_false_stale_on_healthy_link`, `test_l1_cable_pull_flagged_stale_and_recovers`, `test_l1_closed_loop_with_real_channel_a`, `test_l1_closed_loop_cable_pull` | 6 | **PASS** |  |
| L2 | Bench link | The bench link checks shall also run live, during the capture, and the live results shall agree with the replay of the same recording (same words, fingerprint of the saved recording; no decode errors; no false stale anywhere outside the link drop; stale flag and recovery times within 5 ms). | Bench | 1 | `test_l2_live_vs_replay_agree` | 1 | **PASS** |  |
| R11 | Actuator fault | After loss of one of two motor channels, the actuator shall hold commanded position within 0.50 mm for 5 s at every load condition up to rated. | System | 6 | `test_r11_motor_channel_loss_hold` x2, `test_r11_if_position_is_lost_it_is_annunciated` x2, `test_r11_corrective_option_verified` x2 | 5 | **OPEN DEFECT** | FINDING-003: one motor's stall force is below rated load; rod is back-driven |
| R12 | Actuator fault | The actuator monitor shall annunciate a jam within 0.30 s while the command is moving, remove motor drive, and not annunciate during normal operation (including rate-limited moves at rated load and all Part B fault cases). | System | 14 | `test_r12_jam_detected_and_drive_removed` x6, `test_r12_jam_with_stationary_command_is_latent`, `test_r12_no_false_alarm_on_rate_limited_move_at_rated_load`, `test_r12_no_false_alarm_on_bandwidth_sine`, `test_r12_no_false_alarm_across_part_b_faults` x4, `test_r12_no_false_alarm_baseline_actuator` | 13 | **OPEN DEFECT** | FINDING-005: monitor needs the RCA-001 anti-windup fix; baseline windup gives false jam alarms |
| R13 | Actuator fault | With three lanes active on one surface, equalization shall keep force fight between healthy lanes <= 500 N; a faulty lane shall be disengaged (only that lane) with surface error <= 0.25 mm after; a lane fault too small to detect shall cause <= 0.60 mm surface error. | System | 24 | `test_r13_healthy_lanes_share_load_with_equalization`, `test_r13_without_equalization_healthy_lanes_fight_and_trip`, `test_r13_faulty_lane_disengaged` x15, `test_r13_undetected_lane_fault_stays_small` x6, `test_r13_guard_monitor_isolates_only_the_largest_outlier` | 24 | **PASS** |  |

## Test results

| Test | Reqs | Level | Status | Measured |
| --- | --- | --- | --- | --- |
| `test_l1_words_on_the_wire_decode_per_icd` | L1, ICD-1 | Bench | passed | words=1438, sender=192.168.2.1, pitch_mean_deg=-0.999, live_decode_errors=0 |
| `test_l1_rate_and_jitter_on_real_link` | L1 | Bench | passed | intervals=718, mean_ms=20.0, p99_jitter_ms=9.52, max_interval_ms=33.75, stale_limit_ms=60.0, live_max_check_gap_ms=20.61 |
| `test_l1_no_false_stale_on_healthy_link` | R3, L1 | Bench | passed | invalid_samples=0, live_false_stale=0 |
| `test_l1_cable_pull_flagged_stale_and_recovers` | R3, L1 | Bench | passed | cable_out_s=8.82, flagged_after_ms=60.6, recovered_after_reconnect_ms=0.5, live_flagged_after_ms=61.1, live_recovered_after_reconnect_ms=0.1 |
| `test_l1_closed_loop_with_real_channel_a` | R5, L1 | Bench | passed | replayed_s=14.4, max_voted_error_deg=0.066 |
| `test_l1_closed_loop_cable_pull` | R10, R8, L1 | Bench | passed | modes_seen=['DUAL', 'TRIPLEX'], ended_in=TRIPLEX, actuator_span_mm=2.342 |
| `test_l2_live_vs_replay_agree` | L2 | Bench | passed | words_live_vs_replay=2321 vs 2321, flag_ms_live_vs_replay=61.1 vs 60.6, recover_ms_live_vs_replay=0.1 vs 0.5, flag_diff_ms=0.5, recover_diff_ms=0.4, live_max_check_gap_ms=20.61, false_stale_live_vs_replay=0 vs 0, tol_ms=5.0 |
| `test_m1_speed_force_matches_datasheet[no_load]` | M1 | Unit | passed | force_n=0.0, datasheet_mm_s=32.0, model_mm_s=32.0, error_pct=0.0 |
| `test_m1_speed_force_matches_datasheet[peak_power]` | M1 | Unit | passed | force_n=50.0, datasheet_mm_s=16.0, model_mm_s=15.5, error_pct=3.1 |
| `test_m1_speed_force_matches_datasheet[peak_efficiency]` | M1 | Unit | passed | force_n=24.0, datasheet_mm_s=24.0, model_mm_s=24.1, error_pct=0.3 |
| `test_m1_backlash_matches_datasheet` | M1 | Unit | passed | model_backlash_param_mm=0.25, predicted_bench_hysteresis_mm=0.19 |
| `test_a1_small_signal_step_unloaded` | A1 | Unit | passed | rise_s=0.108, overshoot_pct=4.4 |
| `test_a2_max_rate[unloaded]` | A2 | Unit | passed | load=unloaded, rate_mm_s=40.0 |
| `test_a2_max_rate[rated]` | A2 | Unit | passed | load=rated, rate_mm_s=11.7 |
| `test_a3_accuracy_and_backlash` | A3 | Unit | passed | accuracy_mm=0.05, backlash_mm=0.101 |
| `test_a3_own_feedback_cannot_see_backlash` | A3 | Unit | passed | own_feedback_hysteresis_mm=0.001, truth_hysteresis_mm=0.101, sine_truth_hysteresis_mm=0.113, sine_own_feedback_hysteresis_mm=0.013 |
| `test_a4_bandwidth[unloaded]` | A4 | Unit | passed | load=unloaded, bandwidth_hz=2.99 |
| `test_a4_bandwidth[rated]` | A4 | Unit | passed | load=rated, bandwidth_hz=2.85 |
| `test_a5_small_signal_step_rated_load` | A5 | Unit | passed | rise_s=0.108, overshoot_pct=5.1 |
| `test_a5_accuracy_rated_load` | A5 | Unit | passed | accuracy_mm=0.051 |
| `test_icd_bnr_round_trip[0.0]` | ICD-1 | Unit | passed |  |
| `test_icd_bnr_round_trip[2.5]` | ICD-1 | Unit | passed |  |
| `test_icd_bnr_round_trip[-2.5]` | ICD-1 | Unit | passed |  |
| `test_icd_bnr_round_trip[45.37]` | ICD-1 | Unit | passed |  |
| `test_icd_bnr_round_trip[-89.99]` | ICD-1 | Unit | passed |  |
| `test_icd_bnr_round_trip[89.99]` | ICD-1 | Unit | passed |  |
| `test_icd_bnr_round_trip[179.9]` | ICD-1 | Unit | passed |  |
| `test_icd_bnr_round_trip[-180.0]` | ICD-1 | Unit | passed |  |
| `test_icd_label_bits_are_reversed` | ICD-1 | Unit | passed |  |
| `test_icd_odd_parity` | ICD-1 | Unit | passed |  |
| `test_r1_bad_parity_rejected` | R1 | Unit | passed |  |
| `test_r2_ssm_invalid[0]` | R2 | Unit | passed |  |
| `test_r2_ssm_invalid[1]` | R2 | Unit | passed |  |
| `test_r2_ssm_normal_valid` | R2 | Unit | passed |  |
| `test_r3_stale_boundary` | R3 | Unit | passed | stale_limit_ms=60.0 |
| `test_r4_physical_range[90.0-True]` | R4 | Unit | passed |  |
| `test_r4_physical_range[-90.0-True]` | R4 | Unit | passed |  |
| `test_r4_physical_range[90.5-False]` | R4 | Unit | passed |  |
| `test_r4_physical_range[-120.0-False]` | R4 | Unit | passed |  |
| `test_fault_matrix[frozen-chA]` | R6, R8, R10 | System | passed | max_voted_error_deg=0.69, final_mode=DUAL, detect_latency_ms=1099 |
| `test_fault_matrix[frozen-chB]` | R6, R8, R10 | System | passed | max_voted_error_deg=1.25, final_mode=DUAL, detect_latency_ms=1459 |
| `test_fault_matrix[frozen-chC]` | R6, R8, R10 | System | passed | max_voted_error_deg=1.25, final_mode=DUAL, detect_latency_ms=1659 |
| `test_fault_matrix[drift-chA]` | R6, R8, R10 | System | passed | max_voted_error_deg=0.69, final_mode=DUAL, detect_latency_ms=839 |
| `test_fault_matrix[drift-chB]` | R6, R8, R10 | System | passed | max_voted_error_deg=1.25, final_mode=DUAL, detect_latency_ms=1859 |
| `test_fault_matrix[drift-chC]` | R6, R8, R10 | System | passed | max_voted_error_deg=1.25, final_mode=DUAL, detect_latency_ms=2299 |
| `test_fault_matrix[bias_jump-chA]` | R6, R8, R10 | System | passed | max_voted_error_deg=0.69, final_mode=DUAL, detect_latency_ms=99 |
| `test_fault_matrix[bias_jump-chB]` | R6, R8, R10 | System | passed | max_voted_error_deg=0.96, final_mode=DUAL, detect_latency_ms=99 |
| `test_fault_matrix[bias_jump-chC]` | R6, R8, R10 | System | passed | max_voted_error_deg=0.96, final_mode=DUAL, detect_latency_ms=99 |
| `test_fault_matrix[spike-chA]` | R7, R10 | System | passed | max_voted_error_deg=0.21, final_mode=TRIPLEX |
| `test_fault_matrix[spike-chB]` | R7, R10 | System | passed | max_voted_error_deg=0.94, final_mode=TRIPLEX |
| `test_fault_matrix[spike-chC]` | R7, R10 | System | passed | max_voted_error_deg=0.94, final_mode=TRIPLEX |
| `test_fault_matrix[bad_parity-chA]` | R1, R8, R10 | System | passed | max_voted_error_deg=0.69, final_mode=DUAL |
| `test_fault_matrix[bad_parity-chB]` | R1, R8, R10 | System | passed | max_voted_error_deg=0.24, final_mode=DUAL |
| `test_fault_matrix[bad_parity-chC]` | R1, R8, R10 | System | passed | max_voted_error_deg=0.73, final_mode=DUAL |
| `test_fault_matrix[ssm_fail-chA]` | R2, R8, R10 | System | passed | max_voted_error_deg=0.69, final_mode=DUAL |
| `test_fault_matrix[ssm_fail-chB]` | R2, R8, R10 | System | passed | max_voted_error_deg=0.21, final_mode=DUAL |
| `test_fault_matrix[ssm_fail-chC]` | R2, R8, R10 | System | passed | max_voted_error_deg=0.73, final_mode=DUAL |
| `test_fault_matrix[dropout-chA]` | R3, R8, R10 | System | passed | max_voted_error_deg=0.69, final_mode=DUAL |
| `test_fault_matrix[dropout-chB]` | R3, R8, R10 | System | passed | max_voted_error_deg=0.24, final_mode=DUAL |
| `test_fault_matrix[dropout-chC]` | R3, R8, R10 | System | passed | max_voted_error_deg=0.73, final_mode=DUAL |
| `test_fault_matrix[out_of_range-chA]` | R4, R8, R10 | System | passed | max_voted_error_deg=0.69, final_mode=DUAL |
| `test_fault_matrix[out_of_range-chB]` | R4, R8, R10 | System | passed | max_voted_error_deg=0.21, final_mode=DUAL |
| `test_fault_matrix[out_of_range-chC]` | R4, R8, R10 | System | passed | max_voted_error_deg=0.73, final_mode=DUAL |
| `test_finding002_reproduced_at_old_threshold` | R6 | System | passed | old_threshold_deg=2.0, old_failed_channel=C, old_max_voted_error_deg=3.24, configured_threshold_deg=2.5, configured_failed_channel=B, configured_max_voted_error_deg=1.25 |
| `test_r9_reconfiguration_transient_baseline[unloaded]` | R9 | System | passed | load=unloaded, step_mm=4.04, overshoot_mm=0.307, settle_s=0.619 |
| `test_r9_reconfiguration_transient_baseline[rated]` | R9 | System | xfail | load=rated, step_mm=4.06, overshoot_mm=0.922, settle_s=1.164 |
| `test_r9_corrective_action_verified[unloaded]` | R9 | System | passed | load=unloaded, step_mm=4.04, overshoot_mm=0.259, settle_s=0.527 |
| `test_r9_corrective_action_verified[rated]` | R9 | System | passed | load=rated, step_mm=4.03, overshoot_mm=0.017, settle_s=0.366 |
| `test_r10_command_limits_worst_case_inputs` | R10 | Unit | passed | max_cmd_mm=22.0, max_rate_mm_s=60.0 |
| `test_r5_mid_value_select[perm0]` | R5 | Unit | passed |  |
| `test_r5_mid_value_select[perm1]` | R5 | Unit | passed |  |
| `test_r5_mid_value_select[perm2]` | R5 | Unit | passed |  |
| `test_r5_mid_value_select[perm3]` | R5 | Unit | passed |  |
| `test_r5_mid_value_select[perm4]` | R5 | Unit | passed |  |
| `test_r5_mid_value_select[perm5]` | R5 | Unit | passed |  |
| `test_r6_fail_after_persistence` | R6 | Unit | passed | frames_to_latch=5 |
| `test_r6_threshold_has_margin_over_tolerance_stack` | R6 | Unit | passed | margin_deg=0.5 |
| `test_r6_within_threshold_never_fails` | R6 | Unit | passed |  |
| `test_r7_single_spike_ignored` | R7 | Unit | passed |  |
| `test_r7_intermittent_spikes_reset_counter` | R7 | Unit | passed |  |
| `test_r8_dual_mode_average_and_annunciate` | R8 | Unit | passed |  |
| `test_r8_second_fault_in_dual_is_annunciated` | R8 | Unit | passed |  |
| `test_r8_invalid_channel_excluded` | R8 | Unit | passed |  |
| `test_r11_motor_channel_loss_hold[unloaded]` | R11 | System | passed | load_n=0.0, stall_after_loss_n=3250, max_deviation_mm=0.0, monitor_trip_after_s=None |
| `test_r11_motor_channel_loss_hold[rated]` | R11 | System | xfail | load_n=4550.0, stall_after_loss_n=3250, max_deviation_mm=1.697, monitor_trip_after_s=2.97 |
| `test_r11_if_position_is_lost_it_is_annunciated[unloaded]` | R11 | System | passed | load=unloaded, drifted_past_threshold=False, monitor_trip_after_s=None |
| `test_r11_if_position_is_lost_it_is_annunciated[rated]` | R11 | System | passed | load=rated, drifted_past_threshold=True, monitor_trip_after_s=2.97 |
| `test_r11_corrective_option_verified[unloaded]` | R11 | System | passed | load=unloaded, load_n=0.0, stall_after_loss_n=6500, max_deviation_mm=0.0, monitor_trip_after_s=None |
| `test_r11_corrective_option_verified[rated]` | R11 | System | passed | load=rated, load_n=4550.0, stall_after_loss_n=6500, max_deviation_mm=0.0, monitor_trip_after_s=None |
| `test_r12_jam_detected_and_drive_removed[unloaded-near-retract]` | R12 | System | passed | load=unloaded, jam_detect_s=0.171 |
| `test_r12_jam_detected_and_drive_removed[unloaded-mid]` | R12 | System | passed | load=unloaded, jam_detect_s=0.171 |
| `test_r12_jam_detected_and_drive_removed[unloaded-near-extend]` | R12 | System | passed | load=unloaded, jam_detect_s=0.171 |
| `test_r12_jam_detected_and_drive_removed[rated-near-retract]` | R12 | System | passed | load=rated, jam_detect_s=0.171 |
| `test_r12_jam_detected_and_drive_removed[rated-mid]` | R12 | System | passed | load=rated, jam_detect_s=0.171 |
| `test_r12_jam_detected_and_drive_removed[rated-near-extend]` | R12 | System | passed | load=rated, jam_detect_s=0.171 |
| `test_r12_jam_with_stationary_command_is_latent` | R12 | System | passed | annunciated=False |
| `test_r12_no_false_alarm_on_rate_limited_move_at_rated_load` | R12 | System | passed | step_mm=20.0 |
| `test_r12_no_false_alarm_on_bandwidth_sine` | R12 | System | passed |  |
| `test_r12_no_false_alarm_across_part_b_faults[0pct_rated]` | R12 | System | passed | load_n=0, cases=48, false_alarms=0, worst_healthy_mm=0.659, worst_case=frozen-chB-maneuver, margin_mm=0.341 |
| `test_r12_no_false_alarm_across_part_b_faults[50pct_rated]` | R12 | System | passed | load_n=2275, cases=48, false_alarms=0, worst_healthy_mm=0.659, worst_case=frozen-chB-maneuver, margin_mm=0.341 |
| `test_r12_no_false_alarm_across_part_b_faults[75pct_rated]` | R12 | System | passed | load_n=3412, cases=48, false_alarms=0, worst_healthy_mm=0.659, worst_case=frozen-chB-maneuver, margin_mm=0.341 |
| `test_r12_no_false_alarm_across_part_b_faults[100pct_rated]` | R12 | System | passed | load_n=4550, cases=48, false_alarms=0, worst_healthy_mm=0.659, worst_case=frozen-chB-maneuver, margin_mm=0.341 |
| `test_r12_no_false_alarm_baseline_actuator` | R12 | System | xfail | load_n=3412, false_alarms=2, worst_healthy_mm=4.895, worst_case=drift-chA-maneuver |
| `test_r13_healthy_lanes_share_load_with_equalization` | R13 | System | passed | max_fight_n=300 |
| `test_r13_without_equalization_healthy_lanes_fight_and_trip` | R13 | System | passed | max_fight_n=8454, healthy_lane_disengaged_at_s={0: 0.67} |
| `test_r13_faulty_lane_disengaged[laneA+2mm]` | R13 | System | passed | disengaged={0: 0.2}, peak_surface_mm=0.83, final_surface_mm=0.1 |
| `test_r13_faulty_lane_disengaged[laneA-2mm]` | R13 | System | passed | disengaged={0: 0.2}, peak_surface_mm=0.74, final_surface_mm=0.1 |
| `test_r13_faulty_lane_disengaged[laneA+5mm]` | R13 | System | passed | disengaged={0: 0.2}, peak_surface_mm=1.85, final_surface_mm=0.1 |
| `test_r13_faulty_lane_disengaged[laneA-5mm]` | R13 | System | passed | disengaged={0: 0.2}, peak_surface_mm=1.85, final_surface_mm=0.1 |
| `test_r13_faulty_lane_disengaged[laneA+10mm]` | R13 | System | passed | disengaged={0: 0.2}, peak_surface_mm=3.69, final_surface_mm=0.1 |
| `test_r13_faulty_lane_disengaged[laneB+2mm]` | R13 | System | passed | disengaged={1: 0.2}, peak_surface_mm=0.9, final_surface_mm=-0.0 |
| `test_r13_faulty_lane_disengaged[laneB-2mm]` | R13 | System | passed | disengaged={1: 0.2}, peak_surface_mm=0.74, final_surface_mm=-0.0 |
| `test_r13_faulty_lane_disengaged[laneB+5mm]` | R13 | System | passed | disengaged={1: 0.2}, peak_surface_mm=1.85, final_surface_mm=-0.0 |
| `test_r13_faulty_lane_disengaged[laneB-5mm]` | R13 | System | passed | disengaged={1: 0.2}, peak_surface_mm=1.85, final_surface_mm=-0.0 |
| `test_r13_faulty_lane_disengaged[laneB+10mm]` | R13 | System | passed | disengaged={1: 0.2}, peak_surface_mm=3.69, final_surface_mm=-0.0 |
| `test_r13_faulty_lane_disengaged[laneC+2mm]` | R13 | System | passed | disengaged={2: 0.2}, peak_surface_mm=0.98, final_surface_mm=-0.1 |
| `test_r13_faulty_lane_disengaged[laneC-2mm]` | R13 | System | passed | disengaged={2: 0.2}, peak_surface_mm=0.82, final_surface_mm=-0.1 |
| `test_r13_faulty_lane_disengaged[laneC+5mm]` | R13 | System | passed | disengaged={2: 0.2}, peak_surface_mm=1.85, final_surface_mm=-0.1 |
| `test_r13_faulty_lane_disengaged[laneC-5mm]` | R13 | System | passed | disengaged={2: 0.2}, peak_surface_mm=1.85, final_surface_mm=-0.1 |
| `test_r13_faulty_lane_disengaged[laneC+10mm]` | R13 | System | passed | disengaged={2: 0.2}, peak_surface_mm=3.69, final_surface_mm=-0.1 |
| `test_r13_undetected_lane_fault_stays_small[0.5]` | R13 | System | passed | worst_undetected_surface_mm=0.167 |
| `test_r13_undetected_lane_fault_stays_small[1.0]` | R13 | System | passed | worst_undetected_surface_mm=0.333 |
| `test_r13_undetected_lane_fault_stays_small[1.5]` | R13 | System | passed | worst_undetected_surface_mm=0.5 |
| `test_r13_undetected_lane_fault_stays_small[-1.5]` | R13 | System | passed | worst_undetected_surface_mm=0.5 |
| `test_r13_undetected_lane_fault_stays_small[1.6]` | R13 | System | passed | worst_undetected_surface_mm=0.533 |
| `test_r13_undetected_lane_fault_stays_small[-1.6]` | R13 | System | passed | worst_undetected_surface_mm=0.533 |
| `test_r13_guard_monitor_isolates_only_the_largest_outlier` | R13 | System | passed | old_logic_lanes_disengaged=3 |
