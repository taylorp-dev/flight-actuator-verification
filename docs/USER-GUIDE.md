# Actuator Verification SIL: User Guide

From a fresh computer to running the tests, reading the results, and running your own experiments.

**Who this is for:** engineers who know test and avionics but haven't used Python, a terminal, or Linux much. Every step is one command. Nothing assumes you know programming.

**Time needed:** about 15 minutes for first-time setup, then about 10 seconds per test run.

---

## Contents

1. [What this project is](#1-what-this-project-is)
2. [How the test setup maps to a real lab](#2-how-the-test-setup-maps-to-a-real-lab)
3. [Before you start: terminal basics](#3-before-you-start-terminal-basics)
4. [One-time setup](#4-one-time-setup)
5. [Running the tests](#5-running-the-tests)
6. [Reading the results](#6-reading-the-results)
7. [Reports and figures](#7-reports-and-figures)
8. [Running part of the suite](#8-running-part-of-the-suite)
9. [Experiments: learn by changing things](#9-experiments-learn-by-changing-things)
10. [Troubleshooting](#10-troubleshooting)
11. [Where things live](#11-where-things-live)
12. [Glossary](#12-glossary)

---

## 1. What this project is

A **software-in-the-loop** test bench for a flight-control actuator, written in Python. ("SIL" here means software-in-the-loop. Some companies use SIL for a *Systems Integration Lab*, which is real hardware. This project is the software step that comes before that.) The core of it is all simulation, every part of the chain:

```
3 attitude sensors --ARINC 429--> receivers --> voter --> command law --> actuator --> rod position
```

The test suite checks four things:

- **Part A, actuator acceptance (A1-A6):** does the actuator, on its own, meet its spec? Step response (small 1 mm and large 4 mm steps), maximum rate in both directions, accuracy, backlash, bandwidth, behavior under load.
- **Part B, system fault response (ICD-1, R1-R10):** when a sensor fails, does the system catch it, isolate it, and keep the actuator inside its limits?
- **Part C, actuator faults (R11-R13):** when something inside the actuation system fails (a motor channel lost, a jam, two lanes fighting each other on one surface), is it caught and handled?
- **Model check (M1):** does the model of the desk-rig actuator (Actuonix L16-P) match its datasheet? It gives the predictions the real bench will be compared against.

One optional part uses real hardware: the **bench link (L1-L3)** runs sensor channel A on a Raspberry Pi and sends it to the PC over a real Ethernet cable. Its recordings are saved in `bench_data/`, so the normal run replays them and you don't need the Pi to run anything in this guide. Setting up and running the Pi live: `docs/BENCH-GUIDE.md`.

All numbers are representative, not from any real aircraft. The flight-class actuator is sized to the published force class of production fly-by-wire actuators (about 1,000 lbf), but it is not a model of anyone's actual actuator. The point is the **test method**. Sources: `docs/REFERENCES.md`.

---

## 2. How the test setup maps to a real lab

Think of each piece of code as a piece of lab equipment.

| In a real lab | In this SIL | File |
| --- | --- | --- |
| Unit under test (actuator) | Simplified EMA model | `sil/ema.py` |
| Load stand | `load_n` value (0 N or 4,550 N) | `config/sil.yaml` |
| Independent position sensor (LVDT) | Rod position, measured separately from the actuator's own feedback | `sil/ema.py` |
| Sensor boxes on the aircraft | Three simulated attitude sources | `sil/sources.py` |
| Fault injection (breakout box, bus tool) | `Fault(...)` objects: frozen, drift, bad parity, dropout, and more | `sil/sources.py` |
| ARINC 429 bus card (e.g. Ballard) | Software encode/decode of 32-bit words | `sil/arinc429.py` |
| Flight computer software | Receiver, voter, command law | `sil/receiver.py`, `sil/voter.py`, `sil/command_law.py` |
| Test procedures | Python test files | `tests/` |
| Test configuration under change control | One settings file, hashed on every report | `config/sil.yaml` |
| DOORS / JAMA traceability | Auto-generated matrix | `reports/traceability.md` |
| Test log / data package | JUnit XML, JSON summary, plots | `reports/` |

**The rule behind the design:** the actuator's own sensor is used to control it, but pass/fail is judged from a separate truth sensor. The unit never grades itself, just like on a real rig.

---

## 3. Before you start: terminal basics

You'll type commands into a **terminal**, a text window where you run programs by name.

| You are on | The terminal is called | How to open it |
| --- | --- | --- |
| Windows | PowerShell | Start menu, type `PowerShell`, press Enter |
| Mac | Terminal | Spotlight (Cmd+Space), type `Terminal` |
| Linux | Terminal | Usually Ctrl+Alt+T |

**Five habits that prevent most problems:**

1. **One command at a time.** Paste one line, press Enter, wait for the prompt to come back. Pasting several lines at once can leave PowerShell stuck at a `>>` prompt (see [Troubleshooting](#10-troubleshooting)).
2. **Watch which folder you're in.** The prompt shows it, e.g. `PS D:\projects\actuator-verification-sil>`. Almost every command here must be run from the project folder.
3. **Read the last few lines of output.** That's where errors and results appear.
4. **Copy errors exactly** when asking for help. The exact text matters.
5. **Windows uses `\` in paths, Mac/Linux use `/`.** This guide shows Windows first, then Mac/Linux where they differ.

A few commands worth knowing:

| What | Windows (PowerShell) | Mac / Linux |
| --- | --- | --- |
| Show current folder | `pwd` | `pwd` |
| List files here | `ls` | `ls` |
| Go into a folder | `cd foldername` | `cd foldername` |
| Go up one folder | `cd ..` | `cd ..` |
| Clear the screen | `cls` | `clear` |
| Stop a running command | Ctrl+C | Ctrl+C |

---

## 4. One-time setup

### 4.1 Install Python (skip if you already have 3.10 or newer)

Check first:

```
python --version
```

You want `Python 3.10` or higher. Tested with 3.12 and 3.13.

If you get an error or an old version:

- **Windows:** download from [python.org/downloads](https://www.python.org/downloads/). On the first installer screen, **tick "Add python.exe to PATH"** before clicking Install. Then close and reopen PowerShell.
- **Mac:** download from python.org, then use `python3` instead of `python` everywhere in this guide.
- **Linux:** usually already installed as `python3`. If not: `sudo apt install python3 python3-venv`.

> On Windows, if `python` doesn't work but `py --version` does, use `py` instead of `python` everywhere in this guide.

### 4.2 Get the project

Unzip `actuator-verification-sil.zip` into a short path with no spaces, for example:

- Windows: `D:\projects\actuator-verification-sil`
- Mac/Linux: `~/projects/actuator-verification-sil`

Avoid OneDrive, Dropbox, or other synced folders. They can lock files mid-run.

### 4.3 Go to the project folder

```
cd D:\projects\actuator-verification-sil
```

Check you're in the right place:

```
ls
```

You should see `config`, `sil`, `tests`, `pytest.ini`, `README.md`, and others. If you don't, you're in the wrong folder.

### 4.4 Create a virtual environment

A **virtual environment** is a private copy of Python just for this project, so its packages don't mix with anything else on your computer. You create it once.

```
python -m venv .venv
```

This makes a hidden `.venv` folder. It takes a few seconds and prints nothing when it works.

### 4.5 Turn on the virtual environment

**You do this every time you open a new terminal window.**

Windows:

```
.\.venv\Scripts\Activate.ps1
```

Mac/Linux:

```
source .venv/bin/activate
```

When it's on, your prompt starts with `(.venv)`:

```
(.venv) PS D:\projects\actuator-verification-sil>
```

If Windows says *"running scripts is disabled on this system,"* run this once, answer `Y`, then try activating again:

```
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 4.6 Install the packages

```
pip install -r requirements.txt
```

This installs four packages: **numpy** (math), **matplotlib** (plots), **pytest** (test runner), and **pyyaml** (reads the config file). It takes under a minute and needs internet. The last line should start with `Successfully installed`.

Setup is done. You never need to repeat 4.1 to 4.4 or 4.6 on this computer.

---

## 5. Running the tests

### Every session, the short version

```
cd D:\projects\actuator-verification-sil
```

```
.\.venv\Scripts\Activate.ps1
```

```
python -m pytest
```

### What you should see

```
collected 136 items

tests\test_bench_link.py .......                                         [  5%]
tests\test_model_bench_actuator.py ....                                  [  8%]
tests\test_part_a_actuator.py ............x..                            [ 19%]
tests\test_part_b_receiver.py ...................                        [ 33%]
tests\test_part_b_system.py .............................x...            [ 57%]
tests\test_part_b_voter.py ..............                                [ 67%]
tests\test_part_c_actuator_faults.py .x.................x............... [ 93%]
.........                                                                [100%]

XFAIL tests/test_part_a_actuator.py::test_a6_large_step_baseline[rated] - RCA-001: ...
XFAIL tests/test_part_b_system.py::test_r9_reconfiguration_transient_baseline[rated] - RCA-001: ...
XFAIL tests/test_part_c_actuator_faults.py::test_r11_motor_channel_loss_hold[rated] - FINDING-003: ...
XFAIL tests/test_part_c_actuator_faults.py::test_r12_no_false_alarm_baseline_actuator - FINDING-005: ...
======================= 132 passed, 4 xfailed in 27.3s ========================
```

**This is the correct, healthy result.** The first line, `test_bench_link.py`, is the bench link: those 7 tests replay the Raspberry Pi recordings in `bench_data/`, so the Pi doesn't need to be on. L2 (live checks agree with the replay) also reads `bench_data/live_monitor.json`, saved by the same live run as the recording; if that file is missing or from a different run, L2 shows as `s` (skipped) and the result is `131 passed, 1 skipped, 4 xfailed`. If `bench_data/` is ever missing, all 7 show as `s` and the result is `125 passed, 7 skipped, 4 xfailed`. Skipped is never counted as passed. Run time varies by computer (15 to 40 seconds is normal; the Part C false-alarm sweep is the slow part).

**Live = Pi, everything else = recordings.** Nothing in this guide talks to the Pi. Only `--live` (or the "Bench live (Raspberry Pi)" button on GitHub) does, and that's covered in `docs/BENCH-GUIDE.md`.

---

## 6. Reading the results

### The symbols

Each character in the progress line is one test:

| Symbol | Word in summary | Meaning |
| --- | --- | --- |
| `.` | passed | Test met its requirement |
| `F` | failed | Test did not meet its requirement. Investigate. |
| `x` | xfailed | **Expected failure.** A known, documented defect that is still present. Good. |
| `X` | xpassed | A test marked as a known defect unexpectedly passed. In this project that counts as a **failure** (see below). |
| `E` | error | The test couldn't run at all (setup problem, missing file) |
| `s` | skipped | Deliberately not run |

### Why are there expected failures?

Each `x` is a known, documented open defect. There are 4 `x` but 3 defects, because RCA-001 is checked twice:

- **RCA-001**, the headline finding: the actuator's reconfiguration transient passes with no load but fails at rated load (R9). The same windup shows on the actuator alone with a 4 mm step at rated load (A6).
- **FINDING-003**: after losing one of two motors, the actuator can't hold position at rated load.
- **FINDING-005**: the jam monitor gives false alarms unless RCA-001's fix is adopted.

Rather than delete a failing test, it's kept and marked "expected to fail, here's why." This is how you keep a known open defect in regression.

The marking is **strict**. If one of these tests ever starts passing on its own, the suite turns red with `XPASS(strict)`. That forces someone to look and ask, "Did we fix it, or did we break the test?" Then they update the test on purpose. Section 9 shows this happening.

### When a test fails

Pytest prints the failing line and the values involved. For example:

```
>       assert err <= cfg["voter"]["tolerance_deg"] + 0.35
E       assert 3.24 <= (1.0 + 0.35)
```

Read it as: *the measured value (3.24) broke the limit (1.35).* The line marked `>` is the check that failed. The `FAILED ...` lines at the bottom list every failed test by name.

---

## 7. Reports and figures

A **full run** (`python -m pytest` or `python tools\run_tests.py`, nothing filtered) writes these to the `reports` folder. That's the **run for record**. Any **partial run** (one file, one test, `-k`, `-m`, `-x` that stopped early) writes the same files to `reports\dev\` instead, labeled "PARTIAL RUN, not for record", so it can never overwrite the record. `reports\dev\` is not committed.

| File | What it is | Open with |
| --- | --- | --- |
| `traceability.md` | Requirements matrix: each requirement, its tests, verdict, and measured values. Stamped with git commit and config hash. | Notepad, VS Code, or any Markdown viewer |
| `traceability.csv` | Same matrix as a spreadsheet | Excel |
| `junit.xml` | Standard test result format that CI tools read | (used by CI) |
| `test_summary.json` | Everything above, machine-readable | Any text editor |
| `l16p_predictions.md` | Predicted bench results for the desk-rig actuator (written by `python tools\run_tests.py`) | Notepad or any Markdown viewer |

Open the matrix (Windows):

```
notepad reports\traceability.md
```

Mac: `open -e reports/traceability.md`. Linux: `xdg-open reports/traceability.md`.

The top of the file shows what kind of run it was and the **configuration evidence**:

```
- Run: FULL RUN (136 of 136 tests), record
- Git commit: `<commit>`
- Config: `config/sil.yaml` (sha256 `<first 12 characters>`)
- Requirements traced: 24/24 (100.0%)   <- L1-L3 (bench link) show NOT RUN if the Pi recordings are missing
- Tests by level: Unit 53, System 76, Bench 7
```

If anyone changes `config/sil.yaml`, the hash changes. That's how a result traces back to the exact configuration that produced it. A `-dirty` suffix on the commit means there were uncommitted changes when the tests ran: the Run line then says "not for record" and the report goes to `reports\dev\`, not `reports\`. The same happens if git isn't available (commit `no-git`) or `BENCH_DATA_DIR` points at recordings outside the repo. Only a run for record ever writes `reports\`.

The matrix shows, for each requirement, its **level** (Unit = one component alone, System = components together in closed loop, Bench = real hardware data) and the **names** of the tests that cover it. Plain-language procedures for every test, with the exact Python line each step runs, are in `docs\procedures\` (start at `README.md` there).

**Making a run for record:**

1. `git status` must say "nothing to commit, working tree clean". If not, commit first.
2. `python tools\run_tests.py` (runs the full suite, saves the log, then draws the figures from this run's data)
3. Check the top of `reports\traceability.md` says `FULL RUN ... record` and the commit has no `-dirty`.
4. Commit the `reports` folder (matrix, log, `reports\data\` and `reports\figures\`).

> **`reports\` only ever holds the last run for record.** Experiments (uncommitted config changes) write to `reports\dev\`, so they can't overwrite the record.

### Figures

```
python tools\make_figures.py
```

This draws eleven PNGs into `reports\figures` **from the data the tests saved in the run for record** (`reports\data\`). It doesn't run the simulation itself: every point on a plot is a value a test measured, and every number in a legend comes from that test's saved data or result. `tools\run_tests.py` calls it for you at the end of a run for record. No window pops up; open the files from File Explorer.

It refuses to draw (and says why) if the last run isn't a run for record, if a data file is missing, or if `config\sil.yaml` changed since the run. For a quick look after an experiment or a partial run, use `python tools\make_figures.py --dev`: it draws from `reports\dev\` and the plots go to `reports\dev\figures\` with a "NOT FOR RECORD" watermark, so they never overwrite the record. If anything is missing it changes no figure at all. Which test made which data file: [docs/EVIDENCE.md](EVIDENCE.md).

| Figure | Shows |
| --- | --- |
| `a1_a5_step_response.png` | 1 mm step, unloaded vs rated load |
| `a4_bode.png` | Frequency response, -3 dB bandwidth |
| `a3_backlash.png` | Truth sensor sees backlash the actuator's own sensor can't |
| `b_fault_to_actuator.png` | Sensor drift fault traced all the way to actuator motion |
| `b_fault_matrix.png` | 9 fault types x 3 channels, all results, including the R8 annunciations |
| `finding_loaded_vs_unloaded.png` | RCA-001: passes unloaded, fails loaded, fix verified |
| `finding_wrong_channel_isolated.png` | FINDING-002: voter failed the wrong channel |
| `c_motor_loss.png` | R11 / FINDING-003: one motor lost, holds unloaded, back-driven at rated load |
| `c_jam_detection.png` | R12: jam detected, motor drive removed |
| `c_force_fight.png` | R13: three lanes on one surface, with and without equalization, faulty lane disengaged |
| `bench_link_drop.png` | L1: the real Raspberry Pi link drop, flagged and recovered (real hardware recording) |

---

## 8. Running part of the suite

| You want to | Command |
| --- | --- |
| See every test name and result | `python -m pytest -v` |
| Only the actuator tests | `python -m pytest tests\test_part_a_actuator.py -v` |
| Only the actuator fault tests (Part C) | `python -m pytest tests\test_part_c_actuator_faults.py -v` |
| Only tests with "r9" in the name | `python -m pytest -k r9 -v` |
| Only one fault matrix case | `python -m pytest -k "frozen-chB" -v` |
| Skip the slower closed-loop tests | `python -m pytest -m "not system"` |
| Stop at the first failure | `python -m pytest -x` |
| Show print output and full detail | `python -m pytest -v -s` |
| List tests without running them | `python -m pytest --collect-only -q` |

Example, `python -m pytest -k r9 -v`:

```
test_r9_reconfiguration_transient_baseline[unloaded] PASSED
test_r9_reconfiguration_transient_baseline[rated] XFAIL
test_r9_corrective_action_verified[unloaded] PASSED
test_r9_corrective_action_verified[rated] PASSED
3 passed, 132 deselected, 1 xfailed
```

The words in square brackets, like `[rated]`, are the **load condition** the test ran under. One test definition runs once per load automatically.

All of these are **partial runs**: their matrix goes to `reports\dev\`, not `reports\`. Use them while you work; make the record with a full run.

---

## 9. Experiments: learn by changing things

All settings live in one file: `config/sil.yaml`. Open it in Notepad or VS Code. Lines starting with `#` are comments.

**For each experiment:** change one value, save, run `python -m pytest`, read the result, then **change it back** and run again to confirm you're back at your baseline: `132 passed, 4 xfailed`.

> Safety net: if you lose track of what you changed and the project is in git, `git checkout config/sil.yaml` restores the file. Or just unzip a fresh copy.

### Experiment 1: Reproduce FINDING-002 (wrong channel isolated)

In `config/sil.yaml`, under `voter:`, change:

```
  threshold_deg: 2.5
```

to:

```
  threshold_deg: 2.0
```

Run the suite. You should see:

```
FAILED tests/test_part_b_system.py::test_fault_matrix[frozen-chB]
FAILED tests/test_part_b_system.py::test_fault_matrix[drift-chB]
FAILED tests/test_part_b_system.py::test_finding002_reproduced_at_old_threshold
FAILED tests/test_part_b_voter.py::test_r6_threshold_has_margin_over_tolerance_stack
4 failed, 128 passed, 4 xfailed
```

**What happened:** with the threshold at exactly 2x the sensor tolerance, a healthy channel sits right on the limit, noise trips it, and the voter fails the wrong channel. The last two failures are the guards: the FINDING-002 reproduction test (the configured threshold no longer isolates channel B) and the margin test, so this mistake can't slip back in. Details: `docs/rca/FINDING-002-wrong-channel-isolated.md`.

Change it back to `2.5`.

### Experiment 2: Turn on the RCA-001 fix

Under `actuator:`, change `anti_windup: false` to `anti_windup: true`. Run the suite. You should see:

```
[XPASS(strict)] RCA-001: integrator windup during rate saturation at rated load
[XPASS(strict)] RCA-001: integrator windup during rate saturation at rated load
[XPASS(strict)] FINDING-005: monitor needs the RCA-001 anti-windup fix; baseline windup gives false jam alarms
FAILED tests/test_part_a_actuator.py::test_a6_large_step_baseline[rated]
FAILED tests/test_part_b_system.py::test_r9_reconfiguration_transient_baseline[rated]
FAILED tests/test_part_c_actuator_faults.py::test_r12_no_false_alarm_baseline_actuator
3 failed, 132 passed, 1 xfailed
```

**What happened:** the fix works, so both "known defect" tests for RCA-001 (R9 at system level, A6 on the actuator alone) now pass. It also closes FINDING-005: with the windup gone, the jam monitor stops false-alarming. One fix, two defects closed. Because it's marked strict, that unexpected pass is reported as a failure. On a real program, this is the moment you'd close the defect: remove the xfail marking and make the fixed design the new baseline.

Change it back to `false`.

### Experiment 3: Lighter load

Under `load_conditions:`, change `rated: 4550.0` to `rated: 2275.0`. Run the suite. You should see three `XPASS(strict)` lines (RCA-001 for R9, FINDING-003, FINDING-005) and `3 failed, 132 passed, 1 xfailed`. The one still xfailed is A6 at rated load: even at half the load, the 4 mm step on the actuator alone still overshoots past 10 %.

**What happened:** at half the load, all three load-dependent defects disappear at system level. The actuator doesn't saturate long enough for the windup to matter, and one motor can carry half the load on its own. These defects only show up with a realistic load. That's the core lesson of the project: **test environment fidelity decides what you can catch.**

Change it back to `4550.0`.

### Ideas for further exploration

- Raise `noise_sd_deg` under `sensors:` and see when the voter starts tripping on healthy channels.
- Change `bias_deg` to `[0.2, 0.0, -0.2]` (healthier sensors) and see how the R9 reconfiguration step shrinks.
- Lower `kp` under `actuator:` from `15.0` to `9.0`. A4 bandwidth fails (unloaded and rated), and so do A1/A5 rise time, the unloaded A6 and R9 overshoot (baseline and with the fix), and the jam-monitor false-alarm checks (12 failures). One design change ripples across several requirements, which is exactly why you run the whole suite, not just the test you think is affected.

Run `python tools\make_figures.py --dev` after any change to see the effect in the plots (watermarked, in `reports\dev\figures\`).

---

## 10. Troubleshooting

### Setup problems

| Symptom | Cause | Fix |
| --- | --- | --- |
| `python : The term 'python' is not recognized` | Python not installed or not on PATH | Try `py --version`. If that works, use `py`. Otherwise reinstall from python.org with **"Add python.exe to PATH"** ticked, then reopen PowerShell. |
| Typing `python` opens the Microsoft Store | Windows app alias intercepting | Install from python.org, or turn off the alias: Settings > Apps > Advanced app settings > App execution aliases > turn off python.exe and python3.exe |
| `running scripts is disabled on this system` | PowerShell execution policy | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, answer `Y` |
| `No module named venv` (Linux) | venv package missing | `sudo apt install python3-venv` |
| `pip` errors mentioning SSL, proxy, or timeout | Network or corporate proxy | Try another network, or ask IT for proxy settings |
| `externally-managed-environment` (Mac/Linux) | Installing without the venv active | Activate the venv first (4.5), then `pip install` again |

### Running problems

| Symptom | Cause | Fix |
| --- | --- | --- |
| `No module named pytest` / `numpy` / `yaml` | Virtual environment not active | Check the prompt starts with `(.venv)`. If not, activate it (4.5). You must do this in every new window. |
| `No module named 'sil'` | Running from the wrong folder | `cd` into the project folder (the one with `pytest.ini`) |
| `no tests ran` or `file or directory not found` | Wrong folder | Same: `cd` into the project folder, check with `ls` |
| A `reports` folder appeared somewhere unexpected | Ran pytest from a different folder | Always run from the project folder. Delete the stray folder. |
| Prompt shows `>>` and nothing happens | Pasted several lines at once, or an unclosed quote | Press **Ctrl+C**, then paste one line at a time |
| `PermissionError` writing to `reports` | Report file open in Excel, or a synced folder locking it | Close Excel; move the project out of OneDrive/Dropbox |
| Very slow first run | Python compiling, antivirus scanning new files | Normal; second run is faster |

### Result problems

| Symptom | What it means | What to do |
| --- | --- | --- |
| Result isn't your baseline (`132 passed, 4 xfailed`) and you didn't change anything | Config or code changed | `git status` to see what changed; `git checkout config/sil.yaml` to restore config, or unzip a fresh copy |
| `XPASS(strict)` | The known RCA-001 defect stopped failing | Expected if you turned on the fix or lowered the load (Experiments 2-3). Otherwise check what changed. |
| `E` (error) instead of `F` | Test couldn't start; usually a typo in `config/sil.yaml` | YAML is picky about indentation. Use spaces, not tabs, and keep the same indent as neighboring lines. |
| Different run time from someone else | Different computer speed | Not a problem. Results should match exactly; only timing differs. |
| `make_figures: REFUSED` | The last run isn't a run for record, a data file is missing, or the config changed since the run | Read the reason it prints. For a preview use `--dev`; for the record, commit and run `tools\run_tests.py` |

### Still stuck?

Copy **the command you ran and the last 20 lines of output** exactly, plus the output of:

```
python --version
```

```
pip list
```

That's almost always enough to diagnose it.

---

## 11. Where things live

```
actuator-verification-sil/
├── config/sil.yaml              <- every setting and limit (start here)
├── requirements/requirements.yaml  <- requirement text (ICD-1, A1-A6, M1, R1-R13, L1-L3)
├── sil/                         <- the simulated system
│   ├── ema.py                   <-   actuator model
│   ├── analysis.py              <-   bench measurements (step, rate, Bode, backlash)
│   ├── arinc429.py              <-   ARINC 429 word encode/decode
│   ├── sources.py               <-   3 sensors + fault injection
│   ├── receiver.py              <-   parity / SSM / stale / range checks
│   ├── voter.py                 <-   mid-value voter
│   ├── command_law.py           <-   attitude-hold command, position and rate limits
│   ├── actuator_monitor.py      <-   jam / not-tracking monitor (Part C)
│   ├── force_fight.py           <-   three lanes on one surface (Part C)
│   └── sim.py                   <-   wires it all together, runs at 1 kHz
├── tests/                       <- the automated tests
│   ├── conftest.py              <-   shared setup + traceability matrix builder
│   ├── test_part_a_actuator.py  <-   A1-A6
│   ├── test_part_b_receiver.py  <-   ICD-1, R1-R4
│   ├── test_part_b_voter.py     <-   R5-R8
│   ├── test_part_b_system.py    <-   fault matrix, R9, R10
│   ├── test_part_c_actuator_faults.py <- R11-R13
│   ├── test_model_bench_actuator.py   <- M1 (L16-P model vs datasheet)
│   └── test_bench_link.py             <- L1-L3 (real Pi over Ethernet: replay + live monitor)
├── tools/make_figures.py        <- presentation plots, drawn only from reports/data/ of the record run
├── tools/predict_bench.py       <- predicted L16-P bench results
├── tools/pi_channel_a.py        <- runs on the Raspberry Pi: channel A sender
├── tools/bench_capture.py       <- runs on the laptop: records channel A
├── bench_data/                  <- recordings from the Pi + live_monitor.json (see BENCH-GUIDE.md)
├── docs/
│   ├── USER-GUIDE.md            <-   this file
│   ├── procedures/              <-   written test procedures for every test (README.md = index)
│   ├── BENCH-GUIDE.md           <-   channel A on a real Raspberry Pi, step by step
│   ├── REFERENCES.md            <-   public sources and what each informed
│   └── rca/                     <-   RCA-001, FINDING-002 to 005
├── reports/                     <- the record: written by a full run
│   ├── data/                    <-   what the tests measured for each figure (one CSV per series)
│   ├── figures/                 <-   the plots, drawn only from data/
│   └── dev/                     <-   partial runs (not committed, not for record)
├── .github/workflows/ci.yml     <- runs the suite automatically on GitHub
├── pytest.ini                   <- pytest settings
└── requirements.txt             <- Python packages to install
```

### Reading a test

Every test follows the same shape. From `tests/test_part_a_actuator.py`:

```python
@pytest.mark.req("A4")                         # which requirement this verifies
def test_a4_bandwidth(cfg, record_property):   # cfg = settings from config/sil.yaml
    freqs = np.logspace(-1, 1.2, 22)           # 22 test frequencies, 0.1 to 16 Hz
    gains, _ = an.frequency_response(make_ema(cfg), freqs)
    bw = an.bandwidth_hz(freqs, gains)         # find the -3 dB point
    record_property("bandwidth_hz", round(bw, 2))   # save the measured value to the report
    assert bw >= cfg["actuator_spec"]["A4_bandwidth_min_hz"]   # pass/fail
```

That's the same as a lab procedure: setup, stimulus, measure, record, compare to limit. The written version of this exact test is `docs/procedures/TP-A4-bandwidth.md`.

### Continuous integration (optional)

If you push the project to GitHub, `.github/workflows/ci.yml` runs the full suite on every push, posts the traceability matrix to the run summary, and saves the `reports` folder as a downloadable artifact. You don't need to set anything up beyond pushing the repo. It replays the bench recordings, so it never needs the Pi.

To run it without pushing: GitHub → **Actions** → **SIL regression** → **Run workflow**.

There's a second workflow, **Bench live (Raspberry Pi)**, which runs the bench test live on the Pi through a self-hosted runner on your PC. It needs the Pi, the cable, and the runner open. See `docs/BENCH-GUIDE.md`, section 3.

---

## 12. Glossary

| Term | Meaning |
| --- | --- |
| **SIL** | Software-in-the-loop. Everything simulated, no hardware. |
| **HIL** | Hardware-in-the-loop. Real hardware in the test, with simulated surroundings. |
| **EMA** | Electromechanical actuator. Electric motor driving a screw to make linear motion. |
| **ARINC 429** | One-way avionics data bus. Each message is a 32-bit word with a label, data, status (SSM), and parity bit. |
| **Label** | Which quantity a 429 word carries, in octal. Here, 324 = pitch, 325 = roll. |
| **SSM** | Sign/Status Matrix: 2 bits saying if the data is Normal, Failure Warning, No Computed Data, or Functional Test. |
| **Parity** | One check bit. This project uses odd parity: total number of 1-bits must be odd. |
| **BNR** | Binary number format in ARINC 429 (two's complement). |
| **Stale** | No fresh word received within the allowed time (3 transmit intervals here). |
| **Triplex / dual / simplex** | Three, two, or one healthy sensor channel available. |
| **Mid-value select** | Voter picks the middle of three values, so one bad value can never be the output. |
| **Miscompare** | A channel disagreeing with the others by more than the threshold. |
| **Persistence** | How long a miscompare must last before the channel is declared failed (filters out short spikes). |
| **Reconfiguration** | Voter dropping from 3 channels to 2 after a failure. Can cause a jump in the output. |
| **Rate saturation** | Actuator can't move any faster; heavier load lowers the max rate. |
| **Integrator windup** | Controller keeps building up correction while the actuator is maxed out, then overshoots. Root cause of RCA-001. |
| **Anti-windup** | Pausing that buildup while saturated. The corrective action for RCA-001. |
| **Backlash** | Free play between motor and output rod. |
| **Bandwidth (-3 dB)** | Frequency where the actuator's response drops to about 70% of the command. |
| **Fixture** | Reusable setup a test asks for by name, e.g. `cfg` (settings) or `load_condition`. |
| **Parametrize** | Running one test definition many times with different inputs, e.g. every fault x every channel. |
| **Marker** | A tag on a test, e.g. `@pytest.mark.req("R6")`, used here to build traceability. |
| **xfail (strict)** | "Expected to fail, here's why." Strict means an unexpected pass is treated as a failure. |
| **Virtual environment (venv)** | A private Python install for one project. |
| **Config hash** | A short fingerprint of the settings file. Changes if any setting changes. |
