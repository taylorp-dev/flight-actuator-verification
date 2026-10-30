# M1 bench actuator model: test procedures

These tests check the model of the desk rig actuator (Actuonix L16-P) against the manufacturer's datasheet, before the rig is built. Both are Unit tests: the actuator model runs alone, with no receiver, voter or link. They live in `tests/test_model_bench_actuator.py`.

| TC | Requirement(s) | Test function | Cases | Last result (run for record) |
|---|---|---|---|---|
| [TC-M1-U01](#tc-m1-u01-model-speed-matches-the-datasheet-at-three-force-points) | M1 | `test_m1_speed_force_matches_datasheet` | 3 | PASS |
| [TC-M1-U02](#tc-m1-u02-model-uses-the-datasheet-backlash) | M1 | `test_m1_backlash_matches_datasheet` | 1 | PASS |

**Common setup for this file** (pytest does this before every test):

| Item | Python command | Where |
|---|---|---|
| Load settings (once per session, shared by all tests) | `load_config()` | conftest.py lines 68–71 (`cfg` fixture) |
| Recorder for measured values (built into pytest) | `record_property(name, value)` | pytest built-in, values go to the report |
| Helper: build the L16-P model with a given opposing load | `EMA(EMAParams.from_dict(cfg["bench_actuator_l16p"]["params"]), load_n=load_n)` | test file lines 15–16 (`l16p`) |
| Helper: list the datasheet speed-force points, no-load point first | `[(0.0, ds["no_load_speed_mm_s"])] + [tuple(p) for p in ds["points_n_mm_s"]]` | test file lines 19–21 (`_points`) |
| Helper: get the datasheet block from the config | `cfg["bench_actuator_l16p"]["datasheet"]` | test file lines 24–25 (`load_ds`) |

Model settings used (from `config/sil.yaml`, `bench_actuator_l16p.params`): no-load speed `v0_mm_s` 32.0 mm/s, `stall_force_n` 100.0 N, `damping_n_s_per_mm` 100.0, `backlash_mm` 0.25 mm, `stroke_mm` 50.0 (±50 mm), `tau_motor_s` 0.020 s, kp 15.0, ki 30.0, 12 V supply, no anti-windup.

---

## TC-M1-U01: Model speed matches the datasheet at three force points

| Field | Value |
| --- | --- |
| Requirement | M1: The bench actuator model (Actuonix L16-P) shall reproduce the manufacturer datasheet speed-force points within 5 % and use the datasheet backlash. |
| Level | Unit (bench actuator model only) |
| Test file | `tests/test_model_bench_actuator.py` |
| Test function | `test_m1_speed_force_matches_datasheet` (lines 28–38) |

**Purpose:** show that the model's top extend speed, against each datasheet load, is within 5 % of the speed the datasheet gives for that load.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_model_bench_actuator.py::test_m1_speed_force_matches_datasheet" -v
```
Expected output: `3 passed` (one per case). (A single test is a partial run: its report goes to `reports/dev/`, not for record.)

**Initial condition:** fresh model for each case, rod at -20 mm, motor and rod at rest, 12 V supply.

**Cases** (from `config/sil.yaml`, `bench_actuator_l16p.datasheet`; the case is picked by index on line 29):

| Case id | Index | Opposing force | Datasheet speed | Model speed | Error | Result |
|---|---|---|---|---|---|---|
| `no_load` | 0 | 0.0 N | 32.0 mm/s (`no_load_speed_mm_s`) | 32.0 mm/s | 0.0 % | PASS |
| `peak_power` | 1 | 50.0 N | 16.0 mm/s (`points_n_mm_s[0]`) | 15.5 mm/s | 3.1 % | PASS |
| `peak_efficiency` | 2 | 24.0 N | 24.0 mm/s (`points_n_mm_s[1]`) | 24.1 mm/s | 0.3 % | PASS |

**Steps** (run once per case):

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Look up this case's datasheet force and speed | `force_n, speed = _points(cfg)[point]` | Force and speed as in the Cases table | 31 |
| 2 | Build the model with that force pushing against extension, and measure its top extend speed | `measured = an.max_rate(l16p(cfg, force_n), direction=+1.0)` | Returns the peak rod speed in mm/s | 32 |
| 2a | *(inside the call)* Set the move: 80 % of `stroke_mm` (40 mm), from -20 mm to +20 mm | `span = ema.p.stroke_mm * stroke_frac` ... | Start -20 mm, end +20 mm | sil/analysis.py 68–70 |
| 2b | *(inside the call)* Hold -20 mm, step the command to +20 mm at 0.05 s, run 2.5 s at 1 kHz | `run_profile(ema, lambda ti: end if ti >= 0.05 else start, 2.5, start)` | The big step drives the model into its rate limit | sil/analysis.py 71 |
| 2c | *(inside the model, each 1 ms step)* Speed demand is capped at the load-dependent limit, 32 × (1 - force / 100) mm/s, then the load back-drives the motor side by force / 100 mm/s | `v0 * (1.0 - self.load_n / stall)`, `s.xm += (s.v - droop) * dt` | Net extend speed = cap minus back-drive | sil/ema.py 89, 117–118 |
| 2d | *(inside the call)* Work out rod speed from the rod position record and take the highest value | `vel = np.gradient(pos, DT)`, `np.max(vel * direction)` | Peak rod speed, extend direction | sil/analysis.py 72–73 |
| 3 | Work out the error against the datasheet | `err_pct = abs(measured - speed) / speed * 100` | Percent error | 33 |
| 4 | Record force, datasheet speed, model speed and error for the report | `record_property("force_n", force_n)` ... `record_property("error_pct", round(err_pct, 1))` | Values stored (model speed and error rounded to 0.1) | 34–37 |
| 5 | Check the error | `err_pct <= load_ds(cfg)["tolerance_pct"]` | `True`: error ≤ 5.0 % (limit from `bench_actuator_l16p.datasheet.tolerance_pct`) | 38 |

**Pass criteria:** every step gives its expected result, for all three cases. Step 5 is an `assert`; if it fails for any case, that case fails.

**Last result (run for record):** PASS, all 3 cases. No load: 32.0 mm/s vs 32.0 (0.0 %). 50 N: 15.5 mm/s vs 16.0 (3.1 %). 24 N: 24.1 mm/s vs 24.0 (0.3 %).

---

## TC-M1-U02: Model uses the datasheet backlash

| Field | Value |
| --- | --- |
| Requirement | M1: The bench actuator model (Actuonix L16-P) shall reproduce the manufacturer datasheet speed-force points within 5 % and use the datasheet backlash. |
| Level | Unit (bench actuator model only) |
| Test file | `tests/test_model_bench_actuator.py` |
| Test function | `test_m1_backlash_matches_datasheet` (lines 41–52) |

**Purpose:** show that the model's backlash setting is the datasheet value, and record the hysteresis a rod position sensor should see on the bench, for the later model correlation. The predicted hysteresis can come out smaller than the backlash setting (test docstring, lines 43–46).

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_model_bench_actuator.py::test_m1_backlash_matches_datasheet" -v
```
Expected output: `1 passed`. (A single test is a partial run: its report goes to `reports/dev/`, not for record.)

**Initial condition:** model with no load (`l16p(cfg)` uses the default `load_n=0.0`), 12 V supply. Each approach run starts from rest with the rod centered in its free play.

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Read the model settings for the L16-P | `params = cfg["bench_actuator_l16p"]["params"]` | Settings loaded | 47 |
| 2 | Build an unloaded model and run the backlash check at -20, 0 and +20 mm | `_, hyst = an.backlash_and_accuracy(l16p(cfg), points_mm=(-20, 0, 20))` | Returns the largest hysteresis in mm (the accuracy value is thrown away) | 48 |
| 2a | *(inside the call)* For each point, start 2 mm below it, command the point, run 3.0 s, read the rod; then do the same starting 2 mm above | `start = p + side * approach_mm`, `run_profile(ema, lambda ti, p=p: p, 3.0, start)` | Two settled rod readings per point | sil/analysis.py 83–88 |
| 2b | *(inside the model)* The loop closes on the motor-side position; the rod only moves once the motor side has taken up half the free play (0.125 mm) | `if s.xm - s.x > half:` ... | Rod settles a little short of the point, on the side it came from | sil/ema.py 101, 127–131 |
| 2c | *(inside the call)* Hysteresis at each point = gap between the two readings; keep the largest | `hyst.append(abs(readings[0] - readings[1]))`, `max(hyst)` | Largest hysteresis of the three points | sil/analysis.py 90–91 |
| 3 | Record the backlash setting and the predicted bench hysteresis | `record_property("model_backlash_param_mm", params["backlash_mm"])`, `record_property("predicted_bench_hysteresis_mm", round(hyst, 3))` | Values stored (hysteresis rounded to 0.001 mm) | 49–50 |
| 4 | Check the backlash setting equals the datasheet | `params["backlash_mm"] == load_ds(cfg)["backlash_mm"]` | `True`: 0.25 mm = 0.25 mm (setting `bench_actuator_l16p.params.backlash_mm`, datasheet `bench_actuator_l16p.datasheet.backlash_mm`) | 51 |
| 5 | Check the hysteresis is above zero and not more than the backlash | `0.0 < hyst <= params["backlash_mm"] + 1e-9` | `True`: 0 < hysteresis ≤ 0.25 mm (the `1e-9` only allows for rounding in the arithmetic) | 52 |

**Pass criteria:** every step gives its expected result. Steps 4 and 5 are `assert`s; if either fails, the test fails.

**Last result (run for record):** PASS. Backlash setting 0.25 mm, predicted bench hysteresis 0.19 mm.
