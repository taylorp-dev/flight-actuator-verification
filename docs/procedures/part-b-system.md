# Part B system: test procedures

These tests inject one fault at a sensor channel and measure the effect all the way out at the actuator. They are **System** level: the whole loop runs together (sensors → ARINC 429 words → receivers → voter → command law → actuator), through `run_scenario()` in `sil/sim.py`. The one exception is TC-R10-U01, which drives the command law on its own and is marked **Unit**. Test file: `tests/test_part_b_system.py`.

| TC | Requirement(s) | Test function | Cases | Last result (run for record) |
|---|---|---|---|---|
| [TC-FM-S01](#tc-fm-s01-fault-matrix-with-one-sensor-fault-at-a-time) | R1, R2, R3, R4, R6, R7, R8, R10 | `test_fault_matrix` | 27 | PASS (27 of 27) |
| [TC-F002-S01](#tc-f002-s01-finding-002-reproduced-at-the-old-threshold) | R6 | `test_finding002_reproduced_at_old_threshold` | 1 | PASS |
| [TC-R9-S01](#tc-r9-s01-reconfiguration-transient-baseline-design) | R9 | `test_r9_reconfiguration_transient_baseline` | 2 | Unloaded PASS; rated OPEN DEFECT (expected fail, RCA-001) |
| [TC-R9-S02](#tc-r9-s02-reconfiguration-transient-with-anti-windup-fix) | R9 | `test_r9_corrective_action_verified` | 2 | PASS (2 of 2) |
| [TC-R10-U01](#tc-r10-u01-command-limits-hold-for-worst-case-inputs) | R10 | `test_r10_command_limits_worst_case_inputs` | 1 | PASS |

**How to run the whole file (PowerShell, from the repo folder):**
```
python -m pytest tests/test_part_b_system.py -v
```
Expected output: `32 passed, 1 xfailed`. (One file is a partial run: its report goes to `reports/dev/`, not for record.)

**Common setup for this file** (pytest does this before every test):

| Item | Python command | Where |
|---|---|---|
| Mark every test in the file as a system test | `pytestmark = pytest.mark.system` | test file line 16 |
| Load settings once per session (shared, read only) | `return load_config()` in fixture `cfg` | conftest.py lines 68–71 |
| Load a private copy a test may change | `return load_config()` in fixture `fresh_cfg` | conftest.py lines 74–77 |
| Run the test once per load condition (unloaded 0.0 N, rated 4550.0 N, from `load_conditions`) | `@pytest.fixture(params=_load_ids())` / `return name, cfg["load_conditions"][name]` in fixture `load_condition` | conftest.py lines 80–88 |
| Save measured values into the report | `record_property(...)` (built into pytest) | pytest |
| Save plot data for a figure (written to `reports/data/` at the end of the run, stamped with test, result, commit and config hash) | `plot_data.save(name, {column: values}, key=value)` | conftest.py lines 92–125 |
| Pitch swing used by the fault matrix: -2.0° ± 3.0° at 0.3 Hz | `return -2.0 + 3.0 * math.sin(2 * math.pi * 0.3 * t)` | test file lines 19–21 |
| Fault table: kind → magnitude, expected response, requirements | `FAULTS = {...}` | test file lines 25–35 |
| Case list: every fault kind on channel A, B and C | `MATRIX = [(k, ch) for k in FAULTS for ch in (0, 1, 2)]` | test file line 36 |

**What every `run_scenario()` call does at the start** (sil/sim.py lines 90–114): builds three sensor channels with biases A +1.0°, B 0.0°, C -1.0° (`sensors.bias_deg`), noise 0.02° (`sensors.noise_sd_deg`) and send phases 0, 7 and 13 ms; three receivers (stale after 3 intervals); one voter per label (threshold 2.5°, persistence 0.10 s, frame 0.02 s); the command law; and the actuator model. The actuator and the command law start in equilibrium at the healthy commanded position: middle of (pitch + bias) at time 0 = -2.0°, so 4.0 mm/° × (0 − (−2.0)) = 8.0 mm. The loop runs at 1 kHz; the voter and command law run every 20th tick. The Part C actuator monitor also runs, observe only (lines 115–117, 148–149), so it does not change Part B results.

---

## TC-FM-S01: Fault matrix with one sensor fault at a time

| Field | Value |
| --- | --- |
| Requirements | Per fault kind (see Cases), plus R10 on every case. R1: reject bad parity. R2: SSM Failure Warning or No Computed Data is invalid. R3: stale after 3 intervals. R4: reject values out of physical range. R6: fail a channel that miscompares beyond threshold for longer than persistence. R7: don't fail a channel on a single short spike. R8: after one failure, continue on the other two and annunciate. R10: the command never exceeds the position or rate limits. |
| Level | System (whole loop, `run_scenario()` in sil/sim.py) |
| Test file | `tests/test_part_b_system.py` |
| Test function | `test_fault_matrix` (lines 39–82) |

**Purpose:** for each fault kind on each channel, show the bad channel never pulls the voted pitch outside the healthy band, the system responds the right way (isolate the channel, ignore the glitch, or drop the channel at the receiver), the right annunciations are raised (R8), and the actuator command stays inside its limits. (Added 2026-10-29: the `ssm_ncd` fault kind, so both invalid SSM codes in R2 are covered at system level, and the annunciation checks in step 8a.)

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_b_system.py::test_fault_matrix" -v
```
Expected output: `27 passed`. One case only, for example: `python -m pytest "tests/test_part_b_system.py::test_fault_matrix[bad_parity-chA]" -v` gives `1 passed`. (Partial run: report goes to `reports/dev/`, not for record.)

**Initial condition:** all three channels healthy, voter in TRIPLEX, actuator at 8.0 mm in equilibrium, no load (`load_n` defaults to 0.0). The fault starts at 0.5 s and stays on to the end of the 4 s run.

**Setup (done automatically by pytest before step 1):** `cfg`, `record_property`, `request` (see Common setup). The case ID, for example `frozen-chA`, comes from line 40.

**Cases** (measured values from the run for record; each cell is max voted error, final mode, detect latency when recorded):

| Fault kind | Magnitude | Expected response | Requirements | Channel A | Channel B | Channel C |
|---|---|---|---|---|---|---|
| `frozen` | 0.0 (value stops updating) | isolate | R6, R8, R10 | PASS: 0.69°, DUAL, 1099 ms | PASS: 1.25°, DUAL, 1459 ms | PASS: 1.25°, DUAL, 1659 ms |
| `drift` | 2.0 °/s | isolate | R6, R8, R10 | PASS: 0.69°, DUAL, 839 ms | PASS: 1.25°, DUAL, 1859 ms | PASS: 1.25°, DUAL, 2299 ms |
| `bias_jump` | +6.0° step | isolate | R6, R8, R10 | PASS: 0.69°, DUAL, 99 ms | PASS: 0.96°, DUAL, 99 ms | PASS: 0.96°, DUAL, 99 ms |
| `spike` | +15.0° on one word | ignore | R7, R10 | PASS: 0.21°, TRIPLEX, none | PASS: 0.94°, TRIPLEX, none | PASS: 0.94°, TRIPLEX, none |
| `bad_parity` | 0.0 (parity bit flipped) | exclude | R1, R8, R10 | PASS: 0.69°, DUAL, none | PASS: 0.24°, DUAL, none | PASS: 0.73°, DUAL, none |
| `ssm_fail` | 0.0 (SSM = Failure Warning) | exclude | R2, R8, R10 | PASS: 0.69°, DUAL, none | PASS: 0.21°, DUAL, none | PASS: 0.73°, DUAL, none |
| `ssm_ncd` | 0.0 (SSM = No Computed Data) | exclude | R2, R8, R10 | PASS: 0.69°, DUAL, none | PASS: 0.21°, DUAL, none | PASS: 0.73°, DUAL, none |
| `dropout` | 0.0 (label not sent) | exclude | R3, R8, R10 | PASS: 0.69°, DUAL, none | PASS: 0.24°, DUAL, none | PASS: 0.73°, DUAL, none |
| `out_of_range` | value replaced by 120.0° | exclude | R4, R8, R10 | PASS: 0.69°, DUAL, none | PASS: 0.21°, DUAL, none | PASS: 0.73°, DUAL, none |

"none" = no channel was latched failed, so no detect latency was recorded (line 51). This is what the ignore and exclude cases expect.

Annunciations recorded (`annunciations`, step 7a): every isolate case `CHANNEL_FAILED:<faulted channel>,DEGRADED_DUAL`; every exclude case `DEGRADED_DUAL` only; every spike case `none`.

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Look up this fault kind's magnitude, expected response and requirements | `magnitude, expect, reqs = FAULTS[kind]` | Values from the Cases table | 42 |
| 2 | Tag the test with its requirements plus R10, for the traceability matrix | `for r in reqs + ["R10"]:` / `request.node.add_marker(pytest.mark.req(r))` | Tags added | 43–44 |
| 3 | Define the fault on the chosen channel's pitch label, starting at 0.5 s | `Fault(kind, channel, "pitch", t_start=0.5, magnitude=magnitude)` | Fault set up | 45 |
| 4 | Run the whole system for 4 s with the pitch swing | `run_scenario(cfg, duration_s=4.0, pitch_fn=maneuver, faults=[fault])` | Run completes | 46 |
| 4a | *(inside the run)* Each channel sends a pitch word every 20 ms (50 Hz). From 0.5 s the faulty channel changes its output: frozen keeps its first faulted value; drift adds 2.0 °/s × time since 0.5 s; bias_jump adds 6.0°; spike adds 15.0° to one word only; out_of_range sends 120.0° | `_value()` in `SensorChannel` | Faulty value goes out | sil/sources.py 62–78 |
| 4b | *(inside the run)* For the word-level faults: dropout sends nothing; ssm_fail sets SSM to Failure Warning; ssm_ncd sets SSM to No Computed Data; bad_parity flips the parity bit | `transmit()` | Word skipped, flagged or corrupted | sil/sources.py 93–102 |
| 4c | *(inside the run)* Receiver checks each word. Bad parity: word thrown away, time of last good word not updated. Otherwise it stores value, SSM and an in-range flag (-90.0° to +90.0°, from `icd.labels.pitch`) | `receive()` | Bad words rejected | sil/receiver.py 44–56 |
| 4d | *(inside the run)* Each tick the receiver reports a channel invalid if stale (no good word for more than 3 × 20 ms = 60 ms), SSM not Normal, or value out of range | `read()` / `reasons()` | bad_parity and dropout go stale; ssm_fail, ssm_ncd and out_of_range go invalid on the first faulted word | sil/receiver.py 24–32, 58–62; sil/sim.py 136 |
| 4e | *(inside the run)* Every 20 ms the voter runs. With three valid channels it takes the middle value and counts frames where a channel is more than 2.5° from it; 5 frames in a row (0.10 s / 0.02 s) latches that channel failed. With two valid channels it outputs their average (DUAL) | `voters["pitch"].update(...)` | isolate kinds: faulty channel latched, mode DUAL. spike: one frame only, count resets, stays TRIPLEX. exclude kinds: channel never reaches the voter as valid, mode DUAL, nothing latched | sil/voter.py 49–78; sil/sim.py 137–141 |
| 4f | *(inside the run)* Each frame the voter also lists its annunciations: `CHANNEL_FAILED:<channel>` while a channel is latched failed, and `DEGRADED_<mode>` whenever the mode is not TRIPLEX. The run collects every annunciation seen into `run.annunciations` (sil/sim.py 142) | `ann.append("CHANNEL_FAILED:" + ",".join("ABC"[i] for i in sorted(self.failed)))` | isolate: `CHANNEL_FAILED:<ch>` and `DEGRADED_DUAL`. exclude: `DEGRADED_DUAL` only. spike: none | sil/voter.py 80–83 |
| 4g | *(inside the run)* The first time any channel is latched, the run saves that time as `detect_t` | `if out.failed and detect_t is None: detect_t = float(tk)` | Set for isolate kinds only | sil/sim.py 143–144 |
| 4h | *(inside the run)* Command law turns voted pitch into a position command: 4.0 mm/° × (0 − voted), clipped to ±22.0 mm, then step limited to 60.0 mm/s × 0.02 s = 1.2 mm per frame | `law.update(cur_v, v["frame_s"])` | Command inside limits | sil/command_law.py 26–34; sil/sim.py 144 |
| 4i | *(inside the run)* Actuator model follows the command every 1 ms tick | `ema.step(cur_cmd, DT)` | Rod moves | sil/sim.py 146 |
| 5 | Find the largest error between voted pitch and true pitch over the run | `err = float(np.max(np.abs(run.voted - run.truth)))` | Number computed | 48 |
| 6 | Record max error, final mode and (if a channel was latched) detect latency from 0.5 s | `record_property("max_voted_error_deg", ...)` / `record_property("final_mode", ...)` / `record_property("detect_latency_ms", ...)` | Values saved to the report | 49–52 |
| 6a | Save this case as one cell of the fault matrix figure: fault, channel, expected response, which channel was latched, whether the receiver excluded it, detect latency, max voted error, final mode. The figure reads the verdict from this test's result, so a failing case shows as failed | `plot_data.save(f"fault_matrix_{kind}_ch{'ABC'[channel]}", kind=kind, ...)` | `reports/data/fault_matrix_<kind>_ch<A/B/C>.csv` | 53–59 |
| 7 | Check the voted pitch stayed in the healthy band | `assert err <= cfg["voter"]["tolerance_deg"] + cfg["voter"]["latency_allowance_deg"]` | Max error ≤ 1.35° (1.0° from `voter.tolerance_deg` + 0.35° from `voter.latency_allowance_deg`, an allowance for sample and frame latency during the swing) | 63 |
| 7a | Record the annunciations seen during the run, sorted and comma separated (`none` if there were none) | `ann = run.annunciations` / `record_property("annunciations", ",".join(sorted(ann)) or "none")` | Saved to the report | 64–65 |
| 8 | Check the response. **If isolate:** only the faulted channel is latched and the final mode is DUAL. **If ignore:** no channel latched and final mode is TRIPLEX. **If exclude:** no channel latched, the faulted channel is invalid at the last sample, and final mode is DUAL | isolate: `assert run.failed == {channel} and run.mode[-1].value == "DUAL"`; ignore: `assert not run.failed and run.mode[-1].value == "TRIPLEX"`; exclude: `assert not run.failed and not run.valid[-1, channel]` / `assert run.mode[-1].value == "DUAL"` | As described for the case's response | 66–76 |
| 8a | Check the annunciations. **If isolate (R8):** `CHANNEL_FAILED:<faulted channel>` and `DEGRADED_DUAL` were raised. **If ignore (R7):** nothing starting with `CHANNEL_FAILED` or `DEGRADED` was raised. **If exclude (R8):** `DEGRADED_DUAL` was raised and nothing starting with `CHANNEL_FAILED` | isolate: `assert f"CHANNEL_FAILED:{'ABC'[channel]}" in ann and "DEGRADED_DUAL" in ann`; ignore: `assert not any(a.startswith(("CHANNEL_FAILED", "DEGRADED")) for a in ann)`; exclude: `assert "DEGRADED_DUAL" in ann and not any(a.startswith("CHANNEL_FAILED") for a in ann)` | As described for the case's response | 69, 73, 78 |
| 9 | R10: read the command law limits | `law = cfg["command_law"]` | Limits loaded | 80 |
| 10 | R10: check the command never went past the position limit | `assert np.max(np.abs(run.cmd)) <= law["pos_limit_mm"] + 1e-9` | Largest command ≤ 22.0 mm (`command_law.pos_limit_mm`; the 1e-9 only covers rounding) | 81 |
| 11 | R10: check the command never changed faster than the rate limit | `assert np.max(np.abs(np.diff(run.cmd))) <= law["rate_limit_mm_s"] * cfg["voter"]["frame_s"] + 1e-9` | Largest change between samples ≤ 1.2 mm (60.0 mm/s from `command_law.rate_limit_mm_s` × 0.02 s from `voter.frame_s`). The command only changes once a frame, so this is the per-frame step | 82 |

**Pass criteria:** every step gives its expected result for every case. Each check is an `assert`; if any one fails, that case fails.

**Last result (run for record):** PASS, 27 of 27. Largest voted error 1.25° (frozen and drift on channels B and C), limit 1.35°. All isolate cases latched only the faulted channel, ended in DUAL and annunciated `CHANNEL_FAILED` for that channel plus `DEGRADED_DUAL`; all exclude cases (including the new `ssm_ncd`) annunciated `DEGRADED_DUAL` only; spike cases annunciated nothing; detect latency 99 ms for bias_jump, 839 to 2299 ms for frozen and drift. The R10 checks (steps 10 and 11) passed in every case but their values are not recorded for this test.

---

## TC-F002-S01: FINDING-002 reproduced at the old threshold

| Field | Value |
| --- | --- |
| Requirement | R6: The voter shall fail a channel that miscompares beyond threshold for longer than the persistence time. |
| Level | System (whole loop, `run_scenario()` in sil/sim.py) |
| Test file | `tests/test_part_b_system.py` |
| Test function | `test_finding002_reproduced_at_old_threshold` (lines 86–116) |
| Finding | [FINDING-002](../rca/FINDING-002-wrong-channel-isolated.md) |

**Purpose:** keep the FINDING-002 defect as a regression test. The first fault matrix run (during the build) isolated the WRONG channel: with channel B frozen in the middle, noise tripped healthy channel C, because the miscompare threshold was exactly twice the sensor tolerance (zero margin). This test runs that exact case twice: at the old 2.0° threshold it checks the wrong channel is still isolated (the defect is real and reproducible), and at the configured 2.5° it checks channel B is isolated (the margin is what fixed it). Both runs are saved for the slide 16 figure.

**Why a test checks for bad behavior:** if the old setting ever stops failing, something in the model changed (noise, biases, voter), and the margin argument in FINDING-002 has to be looked at again. The test fails and says so.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_b_system.py::test_finding002_reproduced_at_old_threshold" -v
```
Expected output: `1 passed`. (Partial run: report goes to `reports/dev/`, not for record.)

**Initial condition:** same as TC-FM-S01: all channels healthy, voter in TRIPLEX, actuator at 8.0 mm, no load. Channel B freezes at 0.5 s and stays frozen to the end of the 4 s run, during the -2.0° ± 3.0° pitch swing.

**Setup (done automatically by pytest before step 1):** `cfg`, `record_property`, `plot_data` (see Common setup).

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Set the old threshold and the fault: channel B (index 1) frozen from 0.5 s | `old_threshold = 2.0` / `fault = Fault("frozen", 1, "pitch", t_start=0.5)` | Set | 97–98 |
| 2 | For each threshold (old 2.0°, then configured `voter.threshold_deg` 2.5°): copy the settings and set the threshold | `c = copy.deepcopy(cfg)` / `c["voter"]["threshold_deg"] = threshold` | Private copy | 100–102 |
| 3 | Run the whole loop for 4 s with the pitch swing and the fault | `run = run_scenario(c, duration_s=4.0, pitch_fn=maneuver, faults=[fault])` | Run completes | 103 |
| 4 | Voted error = voted pitch minus true pitch; list the latched channel(s) | `err = run.voted - run.truth` / `failed = ",".join("ABC"[i] for i in sorted(run.failed)) or "none"` | Values found | 104–105 |
| 5 | Record threshold, failed channel and max voted error for each run | `record_property(f"{label}_failed_channel", failed)` ... | Saved in the report | 106–108 |
| 6 | Save each run for the FINDING-002 figure | `plot_data.save(f"finding002_threshold_{label}", {"t_s": run.t, "voted_err_deg": err}, ...)` | `reports/data/finding002_threshold_old.csv` / `finding002_threshold_configured.csv` | 109–112 |
| 7 | Check the old threshold reproduces the defect: some channel latched, and it is NOT channel B | `assert results["old"].failed and 1 not in results["old"].failed` | `True` (message "old 2.0 deg threshold no longer isolates the wrong channel: FINDING-002 needs review" if not) | 114–115 |
| 8 | Check the configured threshold isolates channel B only | `assert results["configured"].failed == {1}` | `True` | 116 |

**Pass criteria:** steps 7 and 8 are both `True`.

**Last result (run for record):** PASS. Old 2.0° isolated channel C (wrong), max voted error 3.24°; configured 2.5° isolated channel B, max voted error 1.25°.

---

## TC-R9-S01: Reconfiguration transient baseline design

| Field | Value |
| --- | --- |
| Requirement | R9: After a single-channel failure, the actuator reconfiguration transient shall overshoot <= 0.60 mm and settle within +/-0.25 mm in <= 0.80 s. |
| Level | System (whole loop, `run_scenario()` in sil/sim.py) |
| Test file | `tests/test_part_b_system.py` |
| Test function | `test_r9_reconfiguration_transient_baseline` (lines 155–165), helpers `r9_run` (lines 123–129) and `r9_check` (lines 132–152) |

**Purpose:** measure the actuator transient when the voter drops from TRIPLEX to DUAL, with the baseline actuator design (no anti-windup), at no load and at rated load. The rated case is the headline finding RCA-001 and is kept as an expected failure. The same defect is also checked on the actuator alone, with a 4 mm step: [TC-A6-U01](part-a-actuator.md#tc-a6-u01-large-4-mm-step-baseline-actuator).

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_b_system.py::test_r9_reconfiguration_transient_baseline" -v
```
Expected output: `1 passed, 1 xfailed`. `xfail_strict = true` in pytest.ini (line 8), so if the rated case ever passes it is reported as a failure and someone has to look. (Partial run: report goes to `reports/dev/`, not for record.)

**Initial condition:** all three channels healthy, voter in TRIPLEX, pitch held steady at -2.0°, actuator at 8.0 mm in equilibrium (at rated load the actuator's integrator is pre-loaded to hold against the load, sil/ema.py lines 93–97). `actuator.anti_windup` is `false` (config/sil.yaml line 15).

**Setup (done automatically by pytest before step 1):** `cfg`, `record_property` (see Common setup). The load case comes from the parametrize list at lines 156–160; the rated case carries `xfail(reason="RCA-001: integrator windup during rate saturation at rated load")`.

**Cases:**

| Case | Load | Result | step_mm | overshoot_mm | settle_s |
|---|---|---|---|---|---|
| `unloaded` | 0.0 N | PASS | 4.04 | 0.307 | 0.619 |
| `rated` | 4550.0 N | OPEN DEFECT (expected fail, RCA-001): "RCA-001: integrator windup during rate saturation at rated load" | 4.06 | 0.922 | 1.164 |

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Run the R9 scenario at this case's load | `run = r9_run(cfg, cfg["load_conditions"][load_name])` | Run completes | 163 |
| 1a | *(helper r9_run)* Run the whole system for 4.5 s, pitch steady at -2.0°, channel B (index 1) drifting at 2.0 °/s from 0.5 s, with the given opposing load | `run_scenario(cfg, duration_s=4.5, pitch_fn=lambda t: -2.0, faults=[Fault("drift", 1, "pitch", t_start=R9_FAULT_T, magnitude=2.0)], load_n=load_n)` | Run completes | 127–129 |
| 1b | *(inside the run)* Channel B starts at -2.0° (bias 0) and drifts up. Once it passes channel A (-1.0°, bias +1.0), A becomes the middle value, so the voted pitch moves to about -1.0° and the command to about 4.0 mm | `_value()` drift branch; `voters["pitch"].update(...)` | Voted value follows A | sil/sources.py 69–70; sil/voter.py 56–69 |
| 1c | *(inside the run)* When B is more than 2.5° from A for 5 frames in a row, B is latched failed and `detect_t` is saved. The voter goes to DUAL: average of A and C, about -2.0° | `voters["pitch"].update(...)` | Mode DUAL, B failed | sil/voter.py 56–74; sil/sim.py 143–144 |
| 1d | *(inside the run)* The command law steps the command back up by about 4 mm (extending, against the load), at up to 1.2 mm per frame | `law.update(cur_v, v["frame_s"])` | Command rises toward about 8 mm | sil/command_law.py 26–34 |
| 1e | *(inside the run)* The actuator's extend rate is limited by load: 40.0 mm/s × (1 − load / 6500.0 N). Unloaded: 40.0 mm/s. Rated: 40.0 × (1 − 4550/6500) = 12.0 mm/s, so the 4 mm move saturates the actuator for a while | `v_max(1.0)` | Rate limited | sil/ema.py 82–90 |
| 1f | *(inside the run)* Baseline design: the position-loop integrator keeps adding error while the rate is saturated (windup), which drives overshoot when the rod arrives | `if not (p.anti_windup and saturated) and not self.drive_inhibited: s.integ += err * dt` | Integrator winds up at rated load | sil/ema.py 104–107 |
| 2 | Record the load case name | `record_property("load", load_name)` | Saved | 164 |
| 3 | Run the R9 checks and save the run for the figures | `r9_check(cfg, run, record_property, plot_data, f"r9_baseline_{load_name}")` | See 3a to 3e | 165 |
| 3a | *(helper r9_check)* Check a channel was latched, and that it was channel B only | `assert run.detect_t is not None and run.failed == {1}` | `True` | 134 |
| 3b | *(helper r9_check)* Measure the rod position from `detect_t` on: final value = mean of the last 200 samples (0.2 s); step = final − rod position at `detect_t`; overshoot = how far the rod went past final in the direction of the step; settle = last time the rod was outside ±0.25 mm of final | `m = run.metrics_after(run.detect_t, spec["R9_settle_band_mm"])` | Numbers computed (band 0.25 mm from `system_spec.R9_settle_band_mm`). Measured on the rod (truth sensor), not the actuator's own feedback | 135; sil/sim.py 65–76 |
| 3c | *(helper r9_check)* Record step, overshoot and settle time | `record_property("step_mm", ...)` / `record_property("overshoot_mm", ...)` / `record_property("settle_s", ...)` | Saved | 136–138 |
| 3c2 | *(helper r9_check)* Save the run for the figures (all three channels, voted, true pitch, command, rod position, detect time, step, overshoot, settle). Saved before the checks, so the failing rated case is kept as evidence too | `plot_data.save(name, {"t_s": run.t, ...}, detect_t_s=run.detect_t, ...)` | `reports/data/r9_baseline_unloaded.csv` / `r9_baseline_rated.csv` | 139–150 |
| 3d | *(helper r9_check)* Check overshoot | `assert m["overshoot_mm"] <= spec["R9_overshoot_max_mm"]` | Overshoot ≤ 0.60 mm (limit from `system_spec.R9_overshoot_max_mm`) | 151 |
| 3e | *(helper r9_check)* Check settling time | `assert m["settle_s"] <= spec["R9_settle_time_max_s"]` | Settle ≤ 0.80 s (limit from `system_spec.R9_settle_time_max_s`) | 152 |

**Pass criteria:** unloaded case: every step gives its expected result. Rated case: expected to fail step 3d (and 3e) until the baseline design changes; pytest reports it as `xfailed`, and as a failure if it passes.

**Last result (run for record):** Unloaded PASS: step 4.04 mm, overshoot 0.307 mm, settle 0.619 s. Rated OPEN DEFECT (expected fail, RCA-001), reason "RCA-001: integrator windup during rate saturation at rated load": step 4.06 mm, overshoot 0.922 mm (limit 0.60), settle 1.164 s (limit 0.80). See `docs/rca/RCA-001-reconfig-transient-under-load.md`.

---

## TC-R9-S02: Reconfiguration transient with anti-windup fix

| Field | Value |
| --- | --- |
| Requirement | R9: After a single-channel failure, the actuator reconfiguration transient shall overshoot <= 0.60 mm and settle within +/-0.25 mm in <= 0.80 s. |
| Level | System (whole loop, `run_scenario()` in sil/sim.py) |
| Test file | `tests/test_part_b_system.py` |
| Test function | `test_r9_corrective_action_verified` (lines 168–174), helpers `r9_run` (lines 123–129) and `r9_check` (lines 132–152) |

**Purpose:** verify the RCA-001 corrective action (conditional integration, anti-windup) makes the R9 transient pass at every load condition.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_b_system.py::test_r9_corrective_action_verified" -v
```
Expected output: `2 passed`. (Partial run: report goes to `reports/dev/`, not for record.)

**Initial condition:** same as TC-R9-S01, except `anti_windup` is turned on in a private copy of the settings. The shared `cfg` and config/sil.yaml are not changed.

**Setup (done automatically by pytest before step 1):** `fresh_cfg`, `load_condition`, `record_property` (see Common setup). `load_condition` runs this test once per load condition.

**Cases:**

| Case | Load | Result | step_mm | overshoot_mm | settle_s |
|---|---|---|---|---|---|
| `unloaded` | 0.0 N | PASS | 4.04 | 0.259 | 0.527 |
| `rated` | 4550.0 N | PASS | 4.03 | 0.017 | 0.366 |

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Get the load case name and force | `name, load_n = load_condition` | For example `("rated", 4550.0)` | 171 |
| 2 | Turn on anti-windup in the private settings copy | `fresh_cfg["actuator"]["anti_windup"] = True` | Set | 172 |
| 3 | Record the load case name | `record_property("load", name)` | Saved | 173 |
| 4 | Run the R9 scenario with the fix, then run the R9 checks and save the run | `r9_check(fresh_cfg, r9_run(fresh_cfg, load_n), record_property, plot_data, f"r9_antiwindup_{name}")` | See 4a to 4f | 174 |
| 4a | *(helper r9_run)* Same run as TC-R9-S01 step 1a: 4.5 s, pitch -2.0°, channel B drifting 2.0 °/s from 0.5 s, given load | `run_scenario(fresh_cfg, ...)` | Run completes | 127–129 |
| 4b | *(inside the run)* The actuator model reads `anti_windup: True` from the settings | `EMA(EMAParams.from_dict(cfg["actuator"]), load_n=load_n)` | Fix active | sil/sim.py 107 |
| 4c | *(inside the run)* Same sequence as TC-R9-S01 steps 1b to 1e: B latched, DUAL, about +4 mm command step against the load. Now the integrator holds while the rate limit is active | `if not (p.anti_windup and saturated) and not self.drive_inhibited: s.integ += err * dt` | No windup | sil/ema.py 104–107 |
| 4d | *(helper r9_check)* Check channel B only was latched | `assert run.detect_t is not None and run.failed == {1}` | `True` | 134 |
| 4e | *(helper r9_check)* Measure and record step, overshoot, settle (same as TC-R9-S01 steps 3b and 3c) | `m = run.metrics_after(run.detect_t, spec["R9_settle_band_mm"])` / `record_property(...)` | Saved | 135–138 |
| 4e2 | *(helper r9_check)* Save the run for the R9 figure (same as TC-R9-S01 step 3c2) | `plot_data.save(name, ...)` | `reports/data/r9_antiwindup_unloaded.csv` / `r9_antiwindup_rated.csv` | 139–150 |
| 4f | *(helper r9_check)* Check overshoot and settle time | `assert m["overshoot_mm"] <= spec["R9_overshoot_max_mm"]` / `assert m["settle_s"] <= spec["R9_settle_time_max_s"]` | Overshoot ≤ 0.60 mm (`system_spec.R9_overshoot_max_mm`), settle ≤ 0.80 s (`system_spec.R9_settle_time_max_s`) | 151–152 |

**Pass criteria:** every step gives its expected result in both cases. Each check is an `assert`; if any one fails, the test fails.

**Last result (run for record):** PASS, 2 of 2. Unloaded: step 4.04 mm, overshoot 0.259 mm, settle 0.527 s. Rated: step 4.03 mm, overshoot 0.017 mm, settle 0.366 s.

---

## TC-R10-U01: Command limits hold for worst-case inputs

| Field | Value |
| --- | --- |
| Requirement | R10: The actuator command shall never exceed the position or rate limits, whatever the input. |
| Level | Unit (the command law alone; it does not call `run_scenario()`). Marked `@pytest.mark.level("Unit")` at line 179, so the matrix shows it as Unit even though it lives in the system file |
| Test file | `tests/test_part_b_system.py` |
| Test function | `test_r10_command_limits_worst_case_inputs` (lines 178–192) |

**Purpose:** feed the command law the worst inputs it could get (full-scale reversals, random values, huge values) and show the command never goes past ±22.0 mm or 60.0 mm/s.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_b_system.py::test_r10_command_limits_worst_case_inputs" -v
```
Expected output: `1 passed`. (Partial run: report goes to `reports/dev/`, not for record.)

**Initial condition:** command law starts with its last command at 0.0 mm.

**Setup (done automatically by pytest before step 1):** `cfg`, `record_property` (see Common setup).

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Create the command law from the settings: gain 4.0 mm/°, target 0.0°, position limit 22.0 mm, rate limit 60.0 mm/s | `law = AttitudeHold(**cfg["command_law"])` | Created | 181 |
| 2 | Start it at 0.0 mm | `law.reset(0.0)` | Last command 0.0 | 182 |
| 3 | Set the frame time | `dt = cfg["voter"]["frame_s"]` | 0.02 s | 183 |
| 4 | Make a repeatable random generator (seed 7) | `rng = np.random.default_rng(7)` | Created | 184 |
| 5 | Build the inputs: 100 values alternating +180.0° and -180.0°, 2000 random values between -180° and +180°, 50 zeros, then +1,000,000° and -1,000,000° (2152 inputs) | `np.concatenate([[180.0, -180.0] * 50, rng.uniform(-180, 180, 2000), [0.0] * 50, [1e6, -1e6]])` | Inputs ready | 185–186 |
| 6 | Feed every input to the command law, one per frame | `cmds = [law.update(x, dt) for x in inputs]` | 2152 commands | 187 |
| 6a | *(inside the call)* Raw command = 4.0 × (0 − input), clipped to ±22.0 mm, then the change from the last command is limited to 60.0 × 0.02 = 1.2 mm | `raw = ...` / `max(-self.pos_limit_mm, min(self.pos_limit_mm, raw))` / `cmd = self._last + max(-max_step, min(max_step, raw - self._last))` | Command clipped and step limited | sil/command_law.py 26–34 |
| 7 | Work out every step size, starting from 0.0 mm | `steps = np.abs(np.diff([0.0] + cmds))` | Step sizes computed | 188 |
| 8 | Record the largest command and largest rate | `record_property("max_cmd_mm", ...)` / `record_property("max_rate_mm_s", ...)` | Saved | 189–190 |
| 9 | Check the position limit | `assert np.max(np.abs(cmds)) <= law.pos_limit_mm + 1e-9` | Largest command ≤ 22.0 mm (`command_law.pos_limit_mm`; 1e-9 covers rounding only) | 191 |
| 10 | Check the rate limit | `assert steps.max() <= law.rate_limit_mm_s * dt + 1e-9` | Largest step ≤ 1.2 mm (60.0 mm/s from `command_law.rate_limit_mm_s` × 0.02 s from `voter.frame_s`) | 192 |

**Pass criteria:** every step gives its expected result. Each check is an `assert`; if any one fails, the test fails.

**Last result (run for record):** PASS. Largest command 22.0 mm (limit 22.0), largest rate 60.0 mm/s (limit 60.0). Both sit exactly on the limit, which is what a clip does.
