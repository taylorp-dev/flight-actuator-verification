# Evidence map: every figure and number, back to the run that produced it

Rule for this project: every point on a figure and every result stated on it traces to the **run for record** (a full run of all tests on committed code, with a known git commit). Nothing is redrawn from a separate run. Results in titles and legends (verdicts, measured values, which channel failed, when the monitor tripped) are read from the run's data; the only fixed text on a figure describes the setup (axis names, what a panel shows). This page says where each piece of evidence lives, so a reviewer can trace any of it without asking.

## How to check a figure yourself

1. Open the figure in `reports/figures/`. Its footer names the commit, the config fingerprint (sha256) and the data files it was drawn from.
2. Open the top of [reports/traceability.md](../reports/traceability.md). The commit and the config fingerprint must be the same, and the Run line must say `FULL RUN ... record`. Only a run for record ever writes `reports/`; any other run writes `reports/dev/`.
3. Open the data file in `reports/data/`. Its header names the test that wrote it, that test's result in this run (`test_status`), the commit, the config and the run time (`generated_utc`, the same in every file and in the matrix of that run). The rows are the points on the plot.
4. Numbers in a legend or a title (rise time, bandwidth, overshoot, detect time, "all pass") are read from that data file's header or from the test results, not computed separately by the drawing script.

`tools/make_figures.py` checks steps 2 and 3 before drawing and refuses if anything doesn't match (commit, config or run time), if the run isn't a run for record, if a file is missing, or if `config/sil.yaml` changed since the run. It never runs the simulation. It draws every figure into a staging folder first and replaces the figure set only if all of them drew, so a refusal never leaves a mix of old and new figures.

## Figures

| Figure (`reports/figures/`) | What it shows | Test that saved the data | Data files (`reports/data/`) | Requirement |
| --- | --- | --- | --- | --- |
| `a1_a5_step_response.png` | 1 mm step, unloaded and at rated load | `test_a1_small_signal_step_unloaded`, `test_a5_small_signal_step_rated_load` | `a1_step_unloaded.csv`, `a5_step_rated.csv` | A1, A5 |
| `a4_bode.png` | Frequency response, -3 dB bandwidth, both loads | `test_a4_bandwidth[unloaded]`, `test_a4_bandwidth[rated]` | `a4_bode_unloaded.csv`, `a4_bode_rated.csv` | A4 |
| `a3_backlash.png` | Slow sine: the truth sensor sees the backlash, the actuator's own sensor doesn't | `test_a3_own_feedback_cannot_see_backlash` | `a3_backlash_sine.csv` | A3 |
| `b_fault_to_actuator.png` | Drift on channel B traced to the actuator (unloaded) | `test_r9_reconfiguration_transient_baseline[unloaded]` | `r9_baseline_unloaded.csv` | R9 |
| `b_fault_matrix.png` | 9 fault types x 3 channels (including SSM No Computed Data); each cell and its verdict. The fault types are read from the run's data files, and the latency allowance in the subtitle from `config/sil.yaml` (`voter.latency_allowance_deg`); the subtitle notes each case also checks the R8 annunciations | `test_fault_matrix` (27 cases) | `fault_matrix_<fault>_ch<A/B/C>.csv` (27 files) | R1, R2, R3, R4, R6, R7, R8, R10 |
| `finding_loaded_vs_unloaded.png` | R9 transient: baseline (passes unloaded, fails rated) and with the anti-windup fix | `test_r9_reconfiguration_transient_baseline` x2, `test_r9_corrective_action_verified` x2 | `r9_baseline_unloaded.csv`, `r9_baseline_rated.csv`, `r9_antiwindup_unloaded.csv`, `r9_antiwindup_rated.csv` | R9, RCA-001 |
| `finding_wrong_channel_isolated.png` | FINDING-002: old 2.0 deg threshold isolates the wrong channel, 2.5 deg the right one | `test_finding002_reproduced_at_old_threshold` | `finding002_threshold_old.csv`, `finding002_threshold_configured.csv` | R6, FINDING-002 |
| `c_motor_loss.png` | One motor lost: holds unloaded, back-driven at rated load, holds with option A | `test_r11_motor_channel_loss_hold` x2, `test_r11_corrective_option_verified[rated]` | `r11_motor_loss_baseline_unloaded.csv`, `r11_motor_loss_baseline_rated.csv`, `r11_motor_loss_option_a_rated.csv` | R11, FINDING-003 |
| `c_jam_detection.png` | Jam at rated load: detected, drive removed | `test_r12_jam_detected_and_drive_removed[rated-mid]` | `r12_jam_rated-mid.csv` | R12 |
| `c_force_fight.png` | Three lanes: no equalization, equalization on, lane A sensor +5 mm | `test_r13_without_equalization_healthy_lanes_fight_and_trip`, `test_r13_healthy_lanes_share_load_with_equalization`, `test_r13_faulty_lane_disengaged[laneA+5mm]` | `r13_equalization_off_healthy.csv`, `r13_equalization_on_healthy.csv`, `r13_faulty_laneA+5mm.csv` | R13 |
| `bench_link_drop.png` | **Real hardware:** the Raspberry Pi link drop, flagged and recovered | `test_l1_cable_pull_flagged_stale_and_recovers`, `test_l1_closed_loop_cable_pull` (replaying `bench_data/cable_pull.csv`) | `bench_pitch_intervals.csv`, `bench_receiver_valid.csv`, `bench_voter_channels.csv` | L1 |

A test saves its data before its pass/fail checks, so a failing or open-defect case (for example R9 at rated load, a strict expected failure) is still on the figure, labeled with its real verdict from the run. (One exception: the R9 check first confirms channel B was latched; if it wasn't, no data is saved and the figures refuse to draw.)

For the parametrized tests that run many cases (jam at 6 start points and loads, 15 force-fight fault cases), only the case a figure shows saves plot data, to keep the repo small. Every case's measured values are in the traceability matrix.

## Numbers quoted in the README and the procedures

| Kind of number | Where it comes from |
| --- | --- |
| Pass/fail of a requirement, tests per requirement, test counts | [reports/traceability.md](../reports/traceability.md) (verdict per requirement, Tests by level, Run line) |
| A measured value (rise time, bandwidth, overshoot, detect latency, max deviation, flag time, ...) | The "Measured" column of the same file, one row per test case; also `reports/test_summary.json` |
| Every test name and result in order | [reports/test_log.txt](../reports/test_log.txt) |
| Bench link (Raspberry Pi) timing for the run for record | The record matrix rows for L1, L2 and L3, and `bench_data/cable_pull.csv`, `bench_data/healthy.csv`, `bench_data/live_monitor.json` (the live run the record replays; header line `recorded_utc`) |
| Bench link numbers across several live runs (jitter ranges, worst gaps) | The report of each live run (`reports/dev/traceability.md` from each `pytest tests/test_bench_link.py --live`), kept under `bench_runs/`, one file per run |
| Settings and pass/fail limits | `config/sil.yaml`; its fingerprint is on every report and figure |
| Predicted results for the desk-rig actuator (L16-P) | [reports/l16p_predictions.md](../reports/l16p_predictions.md): **predictions**, not measurements |

## Not evidence of a measurement

- `docs/figures/tier1_rig_built_vs_next.png` is a design diagram. Its timing label summarizes the bench runs listed under `bench_runs/`.
- Everything except the bench link is software-in-the-loop simulation with representative values. The figures say so in their footers.
