# Actuator Verification SIL

[![SIL regression](https://github.com/taylorp-dev/flight-actuator-verification/actions/workflows/ci.yml/badge.svg)](https://github.com/taylorp-dev/flight-actuator-verification/actions/workflows/ci.yml)

EMA characterization, triplex ARINC 429 sensor fault response, and actuator-level faults, in a Python/pytest **software-in-the-loop** (SIL here means software-in-the-loop, not a hardware Systems Integration Lab; this is the software step that comes before one).

> Simplified plant, representative numbers. The flight-class actuator is sized to the published force class of production fly-by-wire actuators (about 1,000 lbf), but it is not a model of anyone's actual actuator or architecture. The point is the **test method**. Sources: [docs/REFERENCES.md](docs/REFERENCES.md).

## What it does

```
 3 x attitude sources --ARINC 429--> receivers --> mid-value voter --> attitude-hold --> EMA --> rod position
   (bias, noise,          (parity, SSM,           (miscompare +        command law      (PI loop,     (independent
    fault injection)       staleness, range)        persistence)        (limits R10)     rate limit,    truth sensor)
                                                                                         load, backlash)
         ^                                                                                                  |
         +------------------------------ pytest: fixtures, fault matrix, req markers -----------------------+
```

- **Part A, actuator acceptance (A1-A6):** small (1 mm) and large (4 mm) step response, max rate in both directions, accuracy and backlash, bandwidth, performance at rated load. Measured at the output rod, never the unit's own feedback.
- **Part B, system fault response (ICD-1, R1-R10):** receiver validity checks, voter isolation, then the effect of each fault at the actuator.
- **Part C, actuator faults (R11-R13):** loss of one of two motor channels, jam detection by a tracking monitor, and force fight between three lanes active on one surface (equalization and faulty-lane disengage).
- **Bench link (L1-L3):** first step off pure simulation. Channel A runs on a Raspberry Pi, a separate computer, and sends its ARINC 429 words to the laptop over a real Ethernet cable in real time. `pytest --live` drives the Pi end to end: starts the sender over SSH, records, takes the Pi's Ethernet link down and back up (automated cable pull), then checks timing and integrity (L3 sets limits on the worst gap and the jitter), link-loss detection and recovery, and runs the recording through the same receiver, voter and actuator. A **live monitor (L2)** runs the same checks during the run, every 1 ms, and a test checks that the live results agree with the replay of the recording within 5 ms. Also runnable from a GitHub "Run workflow" button on a self-hosted runner. ARINC 429 is software-encoded; the physical layer is Ethernet. Guide: [docs/BENCH-GUIDE.md](docs/BENCH-GUIDE.md).
- **Model check (M1):** the desk-rig actuator (Actuonix L16-P) model is checked against its datasheet, then used to predict the bench results ([reports/l16p_predictions.md](reports/l16p_predictions.md)) for model correlation once the rig is built.

## Results (current baseline)

- 24/24 requirements traced, 136 tests (132 pass, 4 strict xfail covering 3 open defects: A6 rated and R9 rated are both RCA-001), full suite about a minute. Run for record (its commit and config fingerprint are at the top): [reports/traceability.md](reports/traceability.md). Every figure is drawn from that run's saved data ([docs/EVIDENCE.md](docs/EVIDENCE.md)).
- Tests by level: Unit 53, System 76, Bench 7. Every test has a written procedure: [docs/procedures/](docs/procedures/README.md).
- **Bench link on a real Raspberry Pi** (15 live runs in four test sets, 2026-10-16 to 10-19; one report per run in [bench_runs/](bench_runs/README.md)): a link drop is flagged at 60.0-61.0 ms and recovers within 1 ms after data returns, with zero false stale, every run. With the live monitor on (11 runs), live and replay agreed within 1.8 ms (L2, limit 5 ms). End-to-end recovery is bounded by the network re-connecting (about 3.4-4.4 s after the 5 s drop), not by the software.
- **Open bench finding, jitter:** p99 jitter was 2.5 ms in Test Set 1 (Oct 16) and 6.3-14.6 ms in Test Set 2 (10 runs, Oct 18, monitor on); worst gap 43 ms, still under the 60 ms stale limit. Test Set 3, an A/B with the live monitor off, gave 4.9-8.2 ms: mostly the bench setup, a smaller effect from the monitor. Test Set 4 (the run for record, Oct 19): 9.5 ms. Requirement L3 now limits it (worst gap ≤ 45 ms, p99 jitter ≤ 15 ms), so a worse link fails on the next live capture; the finding itself stays open. Next: timestamp words in their own thread, live checks on a real-time target, repeat on a quiet PC, longer soak runs.
- **RCA-001:** R9 reconfiguration transient passes unloaded, **fails at rated load** (integrator windup during rate saturation). The actuator passed all its original acceptance tests, which used only 1 mm steps. The new A6 large-step test (4 mm, the reconfiguration step size) now catches the defect on the actuator alone. Corrective action (anti-windup) verified in the SIL, at system level (R9) and actuator level (A6).
- **FINDING-002:** first fault-matrix run isolated the **wrong** channel. Threshold had zero margin over the sensor tolerance stack. Fixed, guarded by a test, and kept as a reproduction test.
- **FINDING-003:** after losing one of two motors, the actuator holds unloaded but is **back-driven at rated load** (one motor = half the stall force). Sizing option verified; open.
- **FINDING-004:** first force-fight monitor disengaged **all three** lanes on a large fault. Now isolates only the largest outlier; guarded by a test.
- **FINDING-005:** jam monitor false-alarmed on healthy actuators. Cause: the RCA-001 windup, worst at 75 % load, not at rated. With RCA-001's fix the threshold is sized from data with margin.

## Test evidence

| What | Where |
| --- | --- |
| Requirements traceability matrix (every requirement, its level, its tests by name, verdict, measured values, commit + config fingerprint, run type) | [reports/traceability.md](reports/traceability.md) |
| **Test procedures**, plain language, every test, with the exact Python line each step runs | [docs/procedures/README.md](docs/procedures/README.md) |
| **Test flow** diagrams: how a unit, system and bench test runs, start to finish | [docs/TEST-FLOW.md](docs/TEST-FLOW.md) |
| **Tier 1 rig overview**: built vs to build, and how the parts work together end to end | [docs/RIG-OVERVIEW.md](docs/RIG-OVERVIEW.md) |
| Full test run log (every test name and result) | [reports/test_log.txt](reports/test_log.txt) |
| **Evidence map**: every figure and slide number, which test produced it, which data file, which run | [docs/EVIDENCE.md](docs/EVIDENCE.md) |
| Plot data from the run for record (one CSV per plotted series, stamped with test, result, commit, config) | [reports/data/](reports/data/) |
| Requirements, full text | [requirements/requirements.yaml](requirements/requirements.yaml) |
| Test cases: actuator acceptance (A1-A6) | [tests/test_part_a_actuator.py](tests/test_part_a_actuator.py) |
| Test cases: ARINC 429 receiver (ICD-1, R1-R4) | [tests/test_part_b_receiver.py](tests/test_part_b_receiver.py) |
| Test cases: voter (R5-R8) | [tests/test_part_b_voter.py](tests/test_part_b_voter.py) |
| Test cases: fault matrix and system level (R9, R10) | [tests/test_part_b_system.py](tests/test_part_b_system.py) |
| Test cases: actuator faults (R11-R13) | [tests/test_part_c_actuator_faults.py](tests/test_part_c_actuator_faults.py) |
| Test cases: bench link, channel A on a Raspberry Pi (L1-L3) | [tests/test_bench_link.py](tests/test_bench_link.py) |
| Bench recordings from the Raspberry Pi (raw words, arrival times) | [bench_data/](bench_data/) |
| Test cases: bench actuator model vs datasheet (M1) | [tests/test_model_bench_actuator.py](tests/test_model_bench_actuator.py) |
| Predicted bench results, Actuonix L16-P | [reports/l16p_predictions.md](reports/l16p_predictions.md) |
| Lab-rig style procedure (bandwidth) | [docs/procedures/TP-A4-bandwidth.md](docs/procedures/TP-A4-bandwidth.md) |
| RCA-001: loaded reconfiguration transient | [docs/rca/RCA-001-reconfig-transient-under-load.md](docs/rca/RCA-001-reconfig-transient-under-load.md) |
| FINDING-002: wrong channel isolated | [docs/rca/FINDING-002-wrong-channel-isolated.md](docs/rca/FINDING-002-wrong-channel-isolated.md) |
| FINDING-003: motor channel loss at rated load | [docs/rca/FINDING-003-motor-loss-at-rated-load.md](docs/rca/FINDING-003-motor-loss-at-rated-load.md) |
| FINDING-004: force-fight monitor dropped all lanes | [docs/rca/FINDING-004-force-fight-monitor-dropped-all-lanes.md](docs/rca/FINDING-004-force-fight-monitor-dropped-all-lanes.md) |
| FINDING-005: jam monitor false alarm | [docs/rca/FINDING-005-jam-monitor-false-alarm.md](docs/rca/FINDING-005-jam-monitor-false-alarm.md) |
| References (public sources and what each informed) | [docs/REFERENCES.md](docs/REFERENCES.md) |
| Figures | [reports/figures/](reports/figures/) |
| Configuration under control (all parameters and limits) | [config/sil.yaml](config/sil.yaml) |
| Automated runs on GitHub (fresh run on every push, full logs, downloadable reports) | [Actions tab](https://github.com/taylorp-dev/flight-actuator-verification/actions) |

## Run it

**Two ways to run, one rule: live = Pi, everything else = recordings.**

| How | Where it runs | Uses the Pi? | What the bench-link tests do |
| --- | --- | --- | --- |
| `python tools/run_tests.py` or `python -m pytest` | Your PC | No | Replay the recordings in `bench_data/` |
| Every push (automatic), or **SIL regression → Run workflow** on the Actions tab | GitHub's machines | No | Replay the recordings in `bench_data/` |
| `python -m pytest tests/test_bench_link.py --live ...` | Your PC | **Yes** | Drive the Pi live, automated link drop, fresh recording |
| **Bench live (Raspberry Pi) → Run workflow** on the Actions tab | Your PC, via a self-hosted runner | **Yes** | Same as `--live`, started from GitHub |

**Run for record vs partial run.** Only a full, unfiltered run (`python tools/run_tests.py` or `python -m pytest`) writes `reports/`; its matrix header says `FULL RUN ... record`, or "not for record" if the code had uncommitted changes. Any partial run (one file, one test, `-k`, `-m`, the live bench tests alone) writes to `reports/dev/` (not committed), so it can't overwrite the record. To make the record: commit, run the full suite, commit `reports/`.

The Pi can be on or off for the first two; they never touch it, so normal runs stay fast, repeatable, and can't fail because the Pi is off. The live ways need the one-time setup in [docs/BENCH-GUIDE.md](docs/BENCH-GUIDE.md), and the button also needs the runner (`run.cmd`) open.

New to Python or the terminal? Start with **[docs/USER-GUIDE.md](docs/USER-GUIDE.md)**: setup, running, reading results, experiments, troubleshooting. Running channel A on a Raspberry Pi: **[docs/BENCH-GUIDE.md](docs/BENCH-GUIDE.md)**.


```bash
pip install -r requirements.txt
python tools/run_tests.py        # tests + test_log.txt + traceability.md + l16p_predictions.md
python -m pytest                 # same tests, no saved log
python tools/make_figures.py     # reports/figures/*.png
python -m pytest tests/test_bench_link.py --live -v   # drive the real Raspberry Pi (setup: docs/BENCH-GUIDE.md)
```

## Layout

| Path | What |
| --- | --- |
| `sil/` | EMA model (with motor-loss and jam faults), ARINC 429 encode/decode, sources + faults, receiver, voter, command law, actuator tracking monitor, three-lane force-fight model, closed-loop sim |
| `config/sil.yaml` | All parameters and limits, under version control; its hash is stamped on every report |
| `requirements/requirements.yaml` | Requirement text, source for the traceability matrix |
| `tests/` | Part A, B and C suites and the bench link; `conftest.py` holds fixtures, the plot-data saver and the traceability hook |
| `docs/USER-GUIDE.md` | Step-by-step setup, running, experiments, troubleshooting |
| `docs/procedures/` | Test procedures for every test (index: `README.md`), plus the lab-rig style TP-A4 |
| `docs/rca/` | RCA-001 and FINDING-002 to FINDING-005 |
| `docs/REFERENCES.md` | Public sources used to size and scope the project |
| `tools/make_figures.py` | Presentation figures, drawn only from the data the tests saved in the run for record (`reports/data/`); refuses otherwise |
| `tools/predict_bench.py` | Predicted results for the desk-rig actuator (L16-P) |
| `tools/pi_channel_a.py` | Runs on the Raspberry Pi: channel A sender over Ethernet |
| `tools/bench_capture.py` | Runs on the laptop: live receiver status + recording to `bench_data/` |
| `sil/link.py` | Word-over-UDP format, capture files, replay into the SIL |
| `.github/workflows/ci.yml` | Runs the full suite on every push (and on its "Run workflow" button), replaying `bench_data/`; publishes the matrix and report artifact |
| `.github/workflows/bench-live.yml` | Manual "Run workflow" button: live bench test on a self-hosted runner cabled to the Pi (partial run: its matrix is in `reports/dev/`) |
| `sil/bench.py` | Live capture, live monitor (checks during the run, L2), and Pi control over SSH (start sender, automated link drop) |

## Framework design

- **Fixtures** give each test a fresh, known configuration (config control in code). `load_condition` runs a test once per load.
- **Parametrize** drives the fault matrix: 9 fault types x 3 channels.
- **`@pytest.mark.req("R6")`** tags each test; a hook builds the traceability matrix with git commit, config hash, measured values, each test's level (Unit / System / Bench, by file or `@pytest.mark.level`), and whether it was a full run for record or a partial run.
- **Strict xfail** keeps a known open defect in regression, tied to its RCA.

## How it was built

Built with an AI coding assistant (Claude), which wrote most of the code and proposed many of the specifics. Taylor Park set the scope, steered what got tested (actuator-internal faults, a real Raspberry Pi instead of simulation only, an automated cable pull, live checking during the bench run), set up and ran the Pi bench, and reviewed every result. Every finding was reproduced, and every result in this repo comes from the tests here.

## Next steps

Live checks for the closed-loop bench tests too (sim stepped to the real clock) and on a real-time target, an IMU on the Pi for real attitude data on channel A, real ARINC 429 bus hardware, RS-422 actuator command link and CAN health bus as plug-ins, a hardware fixture so the same tests run against the L16-P bench actuator (compare to `l16p_predictions.md`), actuator HIL on a load stand, a model-following jam monitor and two-level force-fight monitor (FINDING-004/005 open items), periodic built-in test to expose latent jams, dissimilar sensors, second-fault and common-mode cases, a second airframe ICD.
