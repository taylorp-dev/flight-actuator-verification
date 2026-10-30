# Part A actuator: test procedures

These tests characterize the linear EMA (electromechanical actuator) model by itself, bench acceptance style, against requirements A1 to A5. Every test is **Unit** level: the actuator model alone, measured at the output rod (the independent truth sensor), never from the actuator's own feedback. Test file: `tests/test_part_a_actuator.py`.

| TC | Requirement(s) | Test function | Cases | Last result (run for record, commit d716c1f) |
|---|---|---|---|---|
| [TC-A1-U01](#tc-a1-u01-small-1-mm-step-unloaded) | A1 | `test_a1_small_signal_step_unloaded` | 1 | PASS |
| [TC-A2-U01](#tc-a2-u01-maximum-extend-rate-unloaded-and-at-rated-load) | A2 | `test_a2_max_rate` | 2 | PASS (2 of 2) |
| [TC-A3-U01](#tc-a3-u01-static-accuracy-and-backlash-at-the-rod) | A3 | `test_a3_accuracy_and_backlash` | 1 | PASS |
| [TC-A3-U02](#tc-a3-u02-own-feedback-cannot-see-backlash) | A3 | `test_a3_own_feedback_cannot_see_backlash` | 1 | PASS |
| [TC-A4-U01](#tc-a4-u01-position-bandwidth) | A4 | `test_a4_bandwidth` | 2 | PASS (2 of 2) |
| [TC-A5-U01](#tc-a5-u01-small-1-mm-step-at-rated-load) | A5 | `test_a5_small_signal_step_rated_load` | 1 | PASS |
| [TC-A5-U02](#tc-a5-u02-static-accuracy-at-rated-load) | A5 | `test_a5_accuracy_rated_load` | 1 | PASS |

**Common setup for this file** (pytest does this before every test):

| Item | Python command | Where |
|---|---|---|
| Load settings from `config/sil.yaml` (once per session) | `load_config()` | conftest.py line 71 (`cfg` fixture, lines 68–71) |
| Load condition (only for tests that take it): runs the test once per entry in `load_conditions`, unloaded (0.0 N) and rated (4550.0 N) | `return name, cfg["load_conditions"][name]` | conftest.py lines 84–88 |
| Recorder for measured values (built into pytest) | `record_property(...)` | pytest built-in fixture |
| Saver for plot data (tests behind a figure): series kept in memory, written to `reports/data/` (or `reports/dev/data/`) at the end of the run, stamped with the test, its result, the commit and the config hash | `plot_data.save(name, {column: values}, key=value)` | conftest.py lines 92–125 (written by lines 128–160) |
| Build a fresh actuator from the `actuator` section of the config, with an optional opposing load | `EMA(EMAParams.from_dict(cfg["actuator"]), load_n=load_n)` | test file lines 16–17 (`make_ema`) |

Notes that apply to every TC in this file:

- The simulation runs at a fixed 1 kHz step (`DT = 0.001`, sil/analysis.py line 17).
- Each measurement helper starts by calling `ema.reset(start_mm)` (sil/analysis.py line 32). Reset puts the motor side and the rod at the start position and pre-loads the integrator so a loaded actuator starts in balance (sil/ema.py lines 93–97).
- "Position" in every check is the output rod (`EMA.position`, the truth sensor), except TC-A3-U02, which reads the actuator's own motor-side sensor on purpose.
- Last results below come from the run for record: FULL RUN, 127 of 127 tests (124 passed, 3 xfail), commit `d716c1f`, config `f1bfb3f5a287`, generated 2026-10-30T01:13:46 UTC. The official record is [reports/traceability.md](../../reports/traceability.md).

---

## TC-A1-U01: Small 1 mm step, unloaded

| Field | Value |
| --- | --- |
| Requirement | A1: Small-signal step response (1 mm, unloaded) shall have rise time <= 0.15 s and overshoot <= 10 %. |
| Level | Unit (actuator model alone, measured at the output rod) |
| Test file | `tests/test_part_a_actuator.py` |
| Test function | `test_a1_small_signal_step_unloaded` (lines 21–29) |

**Purpose:** show that with no load, a small 1 mm step command is followed quickly (rise time) and without much overshoot.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_a_actuator.py::test_a1_small_signal_step_unloaded" -v
```
Expected output: `1 passed`. (A single test is a partial run: its report goes to `reports/dev/`, not for record.)

**Initial condition:** actuator at 0 mm (neutral), no load, nominal supply (28 V), at rest.

**Setup (done automatically by pytest before step 1):**

| Item | Python command | Where |
|---|---|---|
| Load settings | `load_config()` | conftest.py line 71 |
| Pick the acceptance limits | `spec = cfg["actuator_spec"]` | test file line 22 |

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Build an unloaded actuator and command a 1 mm step (`A1_step_mm` = 1.0) | `r = an.step_response(make_ema(cfg), spec["A1_step_mm"])` | Step response measured | 23 |
| 1a | *(inside the helper)* Hold 0 mm for 0.1 s, then command 1 mm; run 2 s total and record the rod position every 1 ms | `run_profile(ema, lambda ti: target if ti >= t_step else start_mm, duration_s, start_mm)` | 2000 samples recorded | sil/analysis.py 46–47 |
| 1b | *(inside the helper)* Rise time = time from 10 % to 90 % of the step. Overshoot = how far the peak goes past the target, as % of the step (0 if it never goes past) | `rise = float(t90 - t10) ...` / `overshoot = max(0.0, float((frac.max() - 1.0) * 100.0))` | Numbers computed | sil/analysis.py 54–59 |
| 2 | Record the measured values | `record_property("rise_s", ...)`, `record_property("overshoot_pct", ...)` | Saved in the report | 24–25 |
| 2a | Save the step response for the A1/A5 figure: time, command, rod position | `plot_data.save("a1_step_unloaded", {"t_s": r.t, "cmd_mm": r.cmd, "rod_mm": r.pos}, ...)` | `reports/data/a1_step_unloaded.csv` (written at the end of the run) | 26–27 |
| 3 | Check rise time | `r.rise_time_s <= spec["A1_rise_time_max_s"]` | Rise time ≤ 0.15 s (limit from `actuator_spec.A1_rise_time_max_s`) | 28 |
| 4 | Check overshoot | `r.overshoot_pct <= spec["A1_overshoot_max_pct"]` | Overshoot ≤ 10.0 % (limit from `actuator_spec.A1_overshoot_max_pct`) | 29 |

**Pass criteria:** every step gives its expected result. Each check is an `assert`; if any one fails, the test fails.

**Last result (run for record, commit d716c1f):** PASS. Rise time 0.108 s, overshoot 4.4 %.

---

## TC-A2-U01: Maximum extend rate, unloaded and at rated load

| Field | Value |
| --- | --- |
| Requirement | A2: Maximum rate shall be >= 35 mm/s unloaded and >= 10 mm/s at rated opposing load. |
| Level | Unit (actuator model alone, measured at the output rod) |
| Test file | `tests/test_part_a_actuator.py` |
| Test function | `test_a2_max_rate` (lines 33–40) |

**Purpose:** show the actuator can extend fast enough with no load and while pushing against the rated opposing load.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_a_actuator.py::test_a2_max_rate" -v
```
Expected output: `2 passed` (one per load condition). (A partial run: report goes to `reports/dev/`, not for record.)

**Initial condition:** actuator at -10 mm (start of the move), at rest, nominal supply (28 V), opposing load as given by the case.

**Cases** (from the `load_condition` fixture):

| Case | Load (N) | Rate limit (mm/s) | Limit from | Measured rate (mm/s) | Result |
|---|---|---|---|---|---|
| `unloaded` | 0.0 | 35.0 | `actuator_spec.A2_rate_min_unloaded_mm_s` | 40.0 | PASS |
| `rated` | 4550.0 | 10.0 | `actuator_spec.A2_rate_min_rated_mm_s` | 11.7 | PASS |

**Setup (done automatically by pytest before step 1):**

| Item | Python command | Where |
|---|---|---|
| Load settings | `load_config()` | conftest.py line 71 |
| Pick the load case | `name, load_n = load_condition` | test file line 34 |
| Pick the acceptance limits | `spec = cfg["actuator_spec"]` | test file line 35 |

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Pick the rate limit for this case: 35.0 mm/s if load is 0, else 10.0 mm/s | `limit = spec["A2_rate_min_unloaded_mm_s"] if load_n == 0 else spec["A2_rate_min_rated_mm_s"]` | Limit set | 36 |
| 2 | Build an actuator with this load and command a large extend move | `rate = an.max_rate(make_ema(cfg, load_n), direction=+1.0)` | Peak rate measured | 37 |
| 2a | *(inside the helper)* Move span is 80 % of `stroke_mm` (25.0): 20 mm, from -10 mm to +10 mm. Command jumps at 0.05 s; run 2.5 s | `run_profile(ema, lambda ti: end if ti >= 0.05 else start, 2.5, start)` | Rod position recorded | sil/analysis.py 68–71 |
| 2b | *(inside the helper)* Rod velocity from the position samples; take the peak in the extend direction | `vel = np.gradient(pos, DT)` / `np.max(vel * direction)` | Peak extend rate (mm/s) | sil/analysis.py 72–73 |
| 3 | Record the measured values | `record_property("load", name)`, `record_property("rate_mm_s", ...)` | Saved in the report | 38–39 |
| 4 | Check the rate | `rate >= limit` | Rate ≥ 35.0 mm/s (unloaded) or ≥ 10.0 mm/s (rated) | 40 |

**Pass criteria:** every step gives its expected result in both cases. Each check is an `assert`; if any one fails, that case fails.

**Last result (run for record, commit d716c1f):** PASS, both cases. Unloaded 40.0 mm/s; rated 11.7 mm/s.

---

## TC-A3-U01: Static accuracy and backlash at the rod

| Field | Value |
| --- | --- |
| Requirement | A3: Static position accuracy shall be <= 0.10 mm and backlash <= 0.15 mm, measured at the output rod. |
| Level | Unit (actuator model alone, measured at the output rod) |
| Test file | `tests/test_part_a_actuator.py` |
| Test function | `test_a3_accuracy_and_backlash` (lines 44–50) |

**Purpose:** show the rod settles close to each commanded position, and that the free play (backlash) seen at the rod is small.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_a_actuator.py::test_a3_accuracy_and_backlash" -v
```
Expected output: `1 passed`. (A partial run: report goes to `reports/dev/`, not for record.)

**Initial condition:** no load, nominal supply (28 V). Each approach starts at rest, 2 mm below or above the test point.

**Setup (done automatically by pytest before step 1):**

| Item | Python command | Where |
|---|---|---|
| Load settings | `load_config()` | conftest.py line 71 |
| Pick the acceptance limits | `spec = cfg["actuator_spec"]` | test file line 45 |

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Build an unloaded actuator and run the accuracy and backlash sweep | `acc, backlash = an.backlash_and_accuracy(make_ema(cfg))` | Worst accuracy error and worst backlash returned | 46 |
| 1a | *(inside the helper)* For each point -15, -5, 0, 5, 15 mm: start 2 mm below, hold the point as the command for 3 s, read the final rod position. Repeat starting 2 mm above | `run_profile(ema, lambda ti, p=p: p, 3.0, start)` / `readings.append(pos[-1])` | 10 settled readings | sil/analysis.py 83–88 |
| 1b | *(inside the helper)* Accuracy = largest distance from any reading to its point. Backlash = largest difference between the from-below and from-above readings at one point | `errors.append(abs(pos[-1] - p))` / `hyst.append(abs(readings[0] - readings[1]))` | Two numbers in mm | sil/analysis.py 89–91 |
| 2 | Record the measured values | `record_property("accuracy_mm", ...)`, `record_property("backlash_mm", ...)` | Saved in the report | 47–48 |
| 3 | Check accuracy | `acc <= spec["A3_accuracy_max_mm"]` | Accuracy error ≤ 0.10 mm (limit from `actuator_spec.A3_accuracy_max_mm`) | 49 |
| 4 | Check backlash | `backlash <= spec["A3_backlash_max_mm"]` | Backlash ≤ 0.15 mm (limit from `actuator_spec.A3_backlash_max_mm`) | 50 |

**Pass criteria:** every step gives its expected result. Each check is an `assert`; if any one fails, the test fails.

**Last result (run for record, commit d716c1f):** PASS. Accuracy error 0.05 mm, backlash 0.101 mm.

---

## TC-A3-U02: Own feedback cannot see backlash

| Field | Value |
| --- | --- |
| Requirement | A3: Static position accuracy shall be <= 0.10 mm and backlash <= 0.15 mm, measured at the output rod. |
| Level | Unit (actuator model alone, own sensor compared with the output rod) |
| Test file | `tests/test_part_a_actuator.py` |
| Test function | `test_a3_own_feedback_cannot_see_backlash` (lines 54–99) |

**Purpose:** show why A3 must be measured at the rod. The actuator closes its loop on its own motor-side sensor, so that sensor reports almost no hysteresis even though the rod has real backlash.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_a_actuator.py::test_a3_own_feedback_cannot_see_backlash" -v
```
Expected output: `1 passed`. (A partial run: report goes to `reports/dev/`, not for record.)

**Initial condition:** no load, nominal supply (28 V). Each approach starts at rest at -2 mm or +2 mm.

**Setup (done automatically by pytest before step 1):**

| Item | Python command | Where |
|---|---|---|
| Load settings | `load_config()` | conftest.py line 71 |
| Build an unloaded actuator | `ema = make_ema(cfg)` | test file line 62 |
| Empty list for own-sensor readings | `readings = []` | test file line 63 |

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Start at -2 mm, command 0 mm for 3 s, read the actuator's own (motor-side) sensor | `an.run_profile(ema, lambda t: 0.0, 3.0, start)` / `readings.append(ema.own_feedback)` | First reading saved | 64–66 |
| 2 | Same again starting at +2 mm | (same lines, second pass of the loop) | Second reading saved | 64–66 |
| 3 | Own-sensor hysteresis = difference between the two readings | `own_hyst = abs(readings[0] - readings[1])` | Number in mm | 67 |
| 4 | Measure the rod (truth) hysteresis at 0 mm only, on a new actuator | `_, truth_hyst = an.backlash_and_accuracy(make_ema(cfg), points_mm=(0,))` | Number in mm (same method as TC-A3-U01 step 1, one point) | 68 |
| 5 | Record the measured values | `record_property("own_feedback_hysteresis_mm", ...)`, `record_property("truth_hysteresis_mm", ...)` | Saved in the report | 69–70 |
| 6 | Run a slow 1 mm sine on a new actuator: 8 s period, two cycles, keep the second cycle. Save rod and own-sensor position each 1 ms | `cmd = np.sin(2 * math.pi * t / period)` / `rod[k] = ema.step(cmd[k], an.DT)` / `own[k] = ema.own_feedback` | Sine run done | 72–83 |
| 7 | Hysteresis from the sine: position where the command crosses 0 going up, minus where it crosses 0 going down, for the rod and for the own sensor | `sine_truth, sine_own = crossing_gap(rk), crossing_gap(ok)` | Two numbers in mm (the rod number also includes a little lag from the moving sine) | 85–91 |
| 8 | Record the sine values and save the sine data for the A3 figure (error vs command for both sensors) | `record_property("sine_truth_hysteresis_mm", ...)` / `plot_data.save("a3_backlash_sine", ...)` | Saved; `reports/data/a3_backlash_sine.csv` | 92–97 |
| 9 | Check the own sensor sees much less than the rod | `own_hyst < 0.25 * truth_hyst` | Own-sensor hysteresis is less than a quarter of the rod hysteresis. The limit is computed from the measured rod value, not from the config (0.25 × 0.101 = 0.025 mm on the run for record) | 98 |
| 10 | Same check on the sine | `sine_own < 0.25 * sine_truth` | Own-sensor sine hysteresis is less than a quarter of the rod value (0.25 × 0.113 = 0.028 mm on the run for record) | 99 |

**Pass criteria:** every step gives its expected result. The check is an `assert`; if it fails, the test fails.

**Last result (run for record, commit d716c1f):** PASS. Own-sensor hysteresis 0.001 mm, rod hysteresis 0.101 mm. Sine (steps 6-8 and 10, added so the A3 figure is drawn from this test's own data): rod 0.113 mm, own sensor 0.013 mm.

---

## TC-A4-U01: Position bandwidth

| Field | Value |
| --- | --- |
| Requirement | A4: Position bandwidth (-3 dB) shall be >= 2.5 Hz. |
| Level | Unit (actuator model alone, measured at the output rod) |
| Test file | `tests/test_part_a_actuator.py` |
| Test function | `test_a4_bandwidth` (lines 103–113) |

Lab-rig version: [TP-A4](TP-A4-bandwidth.md)

**Purpose:** show the rod follows a small sine command up to at least 2.5 Hz before the response drops by 3 dB, unloaded and at rated load. (The rated case was added on 2026-10-19: the A4 figure showed it, but no test checked it.)

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_a_actuator.py::test_a4_bandwidth" -v
```
Expected output: `2 passed` (one per load condition). (A partial run: report goes to `reports/dev/`, not for record.)

**Initial condition:** actuator at 0 mm (neutral), unloaded or at rated load (4550 N) per case, nominal supply (28 V), at rest before each frequency.

**Setup (done automatically by pytest before step 1):**

| Item | Python command | Where |
|---|---|---|
| Load settings | `load_config()` | conftest.py line 71 |

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Make the list of test frequencies: 22 points, evenly spaced on a log scale, 0.1 Hz to about 15.8 Hz (10^1.2) | `freqs = np.logspace(-1, 1.2, 22)` | 22 frequencies | 106 |
| 1a | Get the load case | `name, load_n = load_condition` | `("unloaded", 0.0)` or `("rated", 4550.0)` | 105 |
| 2 | Build an actuator with this load and run a sine dwell at each frequency | `gains, phases = an.frequency_response(make_ema(cfg, load_n), freqs)` | One gain (dB) and one phase (deg) per frequency | 107 |
| 2a | *(inside the helper)* At each frequency: command a ±1 mm sine for at least 6 cycles plus 2 extra cycles (at least 1 s plus 2 cycles), starting from reset at 0 mm | `run_profile(ema, lambda ti, f=f: amplitude_mm * math.sin(...), duration)` | Rod position recorded | sil/analysis.py 98–101 |
| 2b | *(inside the helper)* Drop the start-up transient and keep the last 6 cycles. Remove the rod mean, then compare rod and command at the test frequency. Gain = 20·log10(rod amplitude / command amplitude) | `keep = t >= (duration - cycles * period)` ... `gains.append(20 * math.log10(max(abs(h), 1e-6)))` | Gain in dB | sil/analysis.py 102–109 |
| 3 | Find the bandwidth: the first frequency where gain is at or below -3 dB, interpolated between that point and the one before | `bw = an.bandwidth_hz(freqs, gains)` | Bandwidth in Hz | 108 |
| 4 | Record the load case and the measured value | `record_property("load", name)` / `record_property("bandwidth_hz", round(bw, 2))` | Saved in the report | 109–110 |
| 4a | Save gain and phase vs frequency for the A4 figure | `plot_data.save(f"a4_bode_{name}", {"freq_hz": freqs, "gain_db": gains, "phase_deg": phases}, ...)` | `reports/data/a4_bode_unloaded.csv` / `a4_bode_rated.csv` | 111–112 |
| 5 | Check the bandwidth | `bw >= cfg["actuator_spec"]["A4_bandwidth_min_hz"]` | Bandwidth ≥ 2.5 Hz (limit from `actuator_spec.A4_bandwidth_min_hz`) | 113 |

**Pass criteria:** every step gives its expected result. The check is an `assert`; if it fails, the test fails.

**Last result (run for record, commit d716c1f):** PASS, both cases. Unloaded 2.99 Hz; rated 2.85 Hz.

---

## TC-A5-U01: Small 1 mm step at rated load

| Field | Value |
| --- | --- |
| Requirement | A5: At rated opposing load, small-signal step overshoot shall be <= 10 %, rise time <= 0.15 s, accuracy <= 0.10 mm. |
| Level | Unit (actuator model alone, measured at the output rod) |
| Test file | `tests/test_part_a_actuator.py` |
| Test function | `test_a5_small_signal_step_rated_load` (lines 117–126) |

**Purpose:** show the small-step response still meets rise time and overshoot limits while the actuator pushes against the rated load.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_a_actuator.py::test_a5_small_signal_step_rated_load" -v
```
Expected output: `1 passed`. (A partial run: report goes to `reports/dev/`, not for record.)

**Initial condition:** actuator at 0 mm, rated opposing load 4550.0 N (from `load_conditions.rated`), nominal supply (28 V), at rest and in balance (integrator pre-loaded by reset).

**Setup (done automatically by pytest before step 1):**

| Item | Python command | Where |
|---|---|---|
| Load settings | `load_config()` | conftest.py line 71 |
| Pick the acceptance limits | `spec = cfg["actuator_spec"]` | test file line 118 |

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Build an actuator with the rated load and command a 1 mm step (same step size as A1, `A1_step_mm` = 1.0) | `load_n = cfg["load_conditions"]["rated"]` / `r = an.step_response(make_ema(cfg, load_n), spec["A1_step_mm"])` | Step response measured (same method as TC-A1-U01 steps 1a–1b) | 119–120 |
| 2 | Record the measured values | `record_property("rise_s", ...)`, `record_property("overshoot_pct", ...)` | Saved in the report | 121–122 |
| 2a | Save the step response for the A1/A5 figure | `plot_data.save("a5_step_rated", {"t_s": r.t, "cmd_mm": r.cmd, "rod_mm": r.pos}, ...)` | `reports/data/a5_step_rated.csv` | 123–124 |
| 3 | Check rise time | `r.rise_time_s <= spec["A5_rise_time_max_s"]` | Rise time ≤ 0.15 s (limit from `actuator_spec.A5_rise_time_max_s`) | 125 |
| 4 | Check overshoot | `r.overshoot_pct <= spec["A5_overshoot_max_pct"]` | Overshoot ≤ 10.0 % (limit from `actuator_spec.A5_overshoot_max_pct`) | 126 |

**Pass criteria:** every step gives its expected result. Each check is an `assert`; if any one fails, the test fails.

**Last result (run for record, commit d716c1f):** PASS. Rise time 0.108 s, overshoot 5.1 %.

---

## TC-A5-U02: Static accuracy at rated load

| Field | Value |
| --- | --- |
| Requirement | A5: At rated opposing load, small-signal step overshoot shall be <= 10 %, rise time <= 0.15 s, accuracy <= 0.10 mm. |
| Level | Unit (actuator model alone, measured at the output rod) |
| Test file | `tests/test_part_a_actuator.py` |
| Test function | `test_a5_accuracy_rated_load` (lines 130–133) |

**Purpose:** show the rod still settles within 0.10 mm of each commanded position while holding against the rated load.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_a_actuator.py::test_a5_accuracy_rated_load" -v
```
Expected output: `1 passed`. (A partial run: report goes to `reports/dev/`, not for record.)

**Initial condition:** rated opposing load 4550.0 N, nominal supply (28 V). Each approach starts at rest and in balance, 2 mm below or above the test point.

**Setup (done automatically by pytest before step 1):**

| Item | Python command | Where |
|---|---|---|
| Load settings | `load_config()` | conftest.py line 71 |

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Build an actuator with the rated load and run the accuracy sweep (points -15, -5, 0, 5, 15 mm, each approached from both sides; same method as TC-A3-U01 steps 1a–1b). The backlash number is thrown away | `acc, _ = an.backlash_and_accuracy(make_ema(cfg, cfg["load_conditions"]["rated"]))` | Worst accuracy error returned | 131 |
| 2 | Record the measured value | `record_property("accuracy_mm", round(acc, 3))` | Saved in the report | 132 |
| 3 | Check accuracy | `acc <= cfg["actuator_spec"]["A3_accuracy_max_mm"]` | Accuracy error ≤ 0.10 mm (limit from `actuator_spec.A3_accuracy_max_mm`; there is no separate A5 accuracy key) | 133 |

**Pass criteria:** every step gives its expected result. The check is an `assert`; if it fails, the test fails.

**Last result (run for record, commit d716c1f):** PASS. Accuracy error 0.051 mm.
