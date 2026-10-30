<!-- Test Set 2, run 10 of 10 (2026-10-18 evening Pacific, live monitor on). Report written by that live run (pytest tests/test_bench_link.py --live) to reports/dev/traceability.md; source file run10.md, unchanged below. -->

# Requirements Traceability Matrix

- **Run: PARTIAL RUN (7 tests selected), not for record**
- Generated: 2026-10-19T04:48:34+00:00
- Git commit: `80b6c14-dirty`
- Config: `config/sil.yaml` (sha256 `baae11ef69bb`)
- ICD: Generic Rotorcraft A
- Load conditions: {'unloaded': 0.0, 'rated': 4550.0}
- Requirements traced: 7/22 (31.8%)
- Tests: 7 (passed 7)
- Tests by level: Bench 7
- Suite runtime: 35.2 s

Levels: **Unit** = one component alone; **System** = components together in closed loop; **Bench** = real hardware data (Raspberry Pi over a real Ethernet cable). Written procedures for every test: [docs/procedures/](../../docs/procedures/README.md).

| Req | Stage | Requirement | Level | Tests | Test names | Passed | Verdict | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ICD-1 | Interface | ARINC 429 BNR words shall be encoded per the ICD (label, SDI, sign, resolution, SSM, odd parity). | Bench | 1 | `test_l1_words_on_the_wire_decode_per_icd` | 1 | **PASS** |  |
| A1 | Actuator | Small-signal step response (1 mm, unloaded) shall have rise time <= 0.15 s and overshoot <= 10 %. |  | 0 |  | 0 | **NOT TESTED** |  |
| A2 | Actuator | Maximum rate shall be >= 35 mm/s unloaded and >= 10 mm/s at rated opposing load. |  | 0 |  | 0 | **NOT TESTED** |  |
| A3 | Actuator | Static position accuracy shall be <= 0.10 mm and backlash <= 0.15 mm, measured at the output rod. |  | 0 |  | 0 | **NOT TESTED** |  |
| A4 | Actuator | Position bandwidth (-3 dB) shall be >= 2.5 Hz. |  | 0 |  | 0 | **NOT TESTED** |  |
| A5 | Actuator | At rated opposing load, small-signal step overshoot shall be <= 10 %, rise time <= 0.15 s, accuracy <= 0.10 mm. |  | 0 |  | 0 | **NOT TESTED** |  |
| M1 | Model | The bench actuator model (Actuonix L16-P) shall reproduce the manufacturer datasheet speed-force points within 5 % and use the datasheet backlash. |  | 0 |  | 0 | **NOT TESTED** |  |
| R1 | Receiver | The receiver shall reject words with bad parity. |  | 0 |  | 0 | **NOT TESTED** |  |
| R2 | Receiver | The receiver shall treat SSM Failure Warning or No Computed Data as invalid. |  | 0 |  | 0 | **NOT TESTED** |  |
| R3 | Receiver | The receiver shall declare a label stale if not updated within 3 nominal transmit intervals. | Bench | 2 | `test_l1_no_false_stale_on_healthy_link`, `test_l1_cable_pull_flagged_stale_and_recovers` | 2 | **PASS** |  |
| R4 | Receiver | The receiver shall reject values outside the physical range. |  | 0 |  | 0 | **NOT TESTED** |  |
| R5 | Voter | With three valid sources, the voter shall output the middle value. | Bench | 1 | `test_l1_closed_loop_with_real_channel_a` | 1 | **PASS** |  |
| R6 | Voter | The voter shall fail a channel that miscompares beyond threshold for longer than the persistence time. |  | 0 |  | 0 | **NOT TESTED** |  |
| R7 | Voter | The voter shall not fail a channel on a single short spike. |  | 0 |  | 0 | **NOT TESTED** |  |
| R8 | Voter | After one channel failure, the voter shall continue on the remaining two and annunciate. | Bench | 1 | `test_l1_closed_loop_cable_pull` | 1 | **PASS** |  |
| R9 | System | After a single-channel failure, the actuator reconfiguration transient shall overshoot <= 0.60 mm and settle within +/-0.25 mm in <= 0.80 s. |  | 0 |  | 0 | **NOT TESTED** |  |
| R10 | System | The actuator command shall never exceed the position or rate limits, whatever the input. | Bench | 1 | `test_l1_closed_loop_cable_pull` | 1 | **PASS** |  |
| L1 | Bench link | Channel A sent from a separate computer over a real Ethernet link shall decode per the ICD, arrive at the nominal label rate (mean interval within 2 %) without gaps long enough to trip the stale check, and a link loss shall be flagged stale within 3 intervals and recover automatically. | Bench | 6 | `test_l1_words_on_the_wire_decode_per_icd`, `test_l1_rate_and_jitter_on_real_link`, `test_l1_no_false_stale_on_healthy_link`, `test_l1_cable_pull_flagged_stale_and_recovers`, `test_l1_closed_loop_with_real_channel_a`, `test_l1_closed_loop_cable_pull` | 6 | **PASS** |  |
| L2 | Bench link | The bench link checks shall also run live, during the capture, and the live results shall agree with the replay of the same recording (same words, fingerprint of the saved recording; no decode errors; no false stale anywhere outside the link drop; stale flag and recovery times within 5 ms). | Bench | 1 | `test_l2_live_vs_replay_agree` | 1 | **PASS** |  |
| R11 | Actuator fault | After loss of one of two motor channels, the actuator shall hold commanded position within 0.50 mm for 5 s at every load condition up to rated. |  | 0 |  | 0 | **NOT TESTED** |  |
| R12 | Actuator fault | The actuator monitor shall annunciate a jam within 0.30 s while the command is moving, remove motor drive, and not annunciate during normal operation (including rate-limited moves at rated load and all Part B fault cases). |  | 0 |  | 0 | **NOT TESTED** |  |
| R13 | Actuator fault | With three lanes active on one surface, equalization shall keep force fight between healthy lanes <= 500 N; a faulty lane shall be disengaged (only that lane) with surface error <= 0.25 mm after; a lane fault too small to detect shall cause <= 0.60 mm surface error. |  | 0 |  | 0 | **NOT TESTED** |  |

## Test results

| Test | Reqs | Level | Status | Measured |
| --- | --- | --- | --- | --- |
| `test_l1_words_on_the_wire_decode_per_icd` | L1, ICD-1 | Bench | passed | words=1434, sender=192.168.2.1, pitch_mean_deg=-1.0, live_decode_errors=0 |
| `test_l1_rate_and_jitter_on_real_link` | L1 | Bench | passed | intervals=716, mean_ms=20.0, p99_jitter_ms=14.64, max_interval_ms=36.56, stale_limit_ms=60.0, live_max_check_gap_ms=3.4 |
| `test_l1_no_false_stale_on_healthy_link` | R3, L1 | Bench | passed | invalid_samples=0, live_false_stale=0 |
| `test_l1_cable_pull_flagged_stale_and_recovers` | R3, L1 | Bench | passed | cable_out_s=9.38, flagged_after_ms=60.7, recovered_after_reconnect_ms=0.2, live_flagged_after_ms=61.7, live_recovered_after_reconnect_ms=0.1 |
| `test_l1_closed_loop_with_real_channel_a` | R5, L1 | Bench | passed | replayed_s=14.3, max_voted_error_deg=0.066 |
| `test_l1_closed_loop_cable_pull` | R10, R8, L1 | Bench | passed | modes_seen=['DUAL', 'TRIPLEX'], ended_in=TRIPLEX, actuator_span_mm=2.273 |
| `test_l2_live_vs_replay_agree` | L2 | Bench | passed | words_live_vs_replay=2367 vs 2367, flag_ms_live_vs_replay=61.7 vs 60.7, recover_ms_live_vs_replay=0.1 vs 0.2, flag_diff_ms=1.0, recover_diff_ms=0.1, live_max_check_gap_ms=3.4, false_stale_live_vs_replay=0 vs 0, tol_ms=5.0 |
