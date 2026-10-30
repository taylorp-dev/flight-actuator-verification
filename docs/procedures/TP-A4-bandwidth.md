# TP-A4: Actuator Position Bandwidth Test

| Field | Value |
| --- | --- |
| Procedure ID | TP-A4 rev A |
| Requirement | A4: position bandwidth (-3 dB) >= 2.5 Hz |
| Unit under test | Linear EMA (simulated in this SIL; procedure written for the lab rig) |
| Automated test | `tests/test_part_a_actuator.py::test_a4_bandwidth` |

## 1. Purpose

Verify the actuator's small-signal position bandwidth meets A4, measured at the output rod by an independent position sensor.

## 2. Equipment

| Item | Lab rig | This SIL |
| --- | --- | --- |
| Command source | Test host + RS-422 command link | `sil.analysis.run_profile` |
| Position truth sensor | LVDT on output rod, via DAQ | `EMA.position` (rod) |
| Load | Load stand, unloaded for this test | `load_n = 0` |
| Data acquisition | >= 1 kHz, command and position time-synced | 1 kHz fixed step |

Calibration: truth sensor and DAQ within cal date, recorded in the test log.

## 3. Configuration

- Actuator software and config under control. Record git commit and `config/sil.yaml` hash (the automated report does this).
- Actuator at neutral, powered at nominal supply (28 V), no load.

## 4. Steps

1. Command neutral and hold 2 s. Confirm position within accuracy limit (A3).
2. For each frequency in the sweep (0.1 to 16 Hz, 22 log-spaced points):
   1. Command a 1.0 mm amplitude sine about neutral.
   2. Dwell for at least 6 full cycles after a settling period of 2 cycles.
   3. Record command and rod position for the steady-state cycles.
3. For each frequency, compute gain (dB) and phase (deg) of rod position relative to command at the excitation frequency (single-bin DFT).
4. Find the -3 dB frequency by linear interpolation between the bracketing points.

Amplitude note: 1.0 mm keeps peak rate below the rate limit up to the top of the sweep and stays well above backlash (0.10 mm), so the result reflects linear bandwidth, not rate saturation or free play.

## 5. Pass/fail

| Criterion | Limit | Pass if |
| --- | --- | --- |
| -3 dB bandwidth | 2.5 Hz | measured >= 2.5 Hz |

## 6. Data recorded

- Gain and phase at every frequency (Bode plot: `reports/figures/a4_bode.png`)
- Measured -3 dB frequency (recorded as a test property in `reports/junit.xml` and `reports/traceability.md`)
- Git commit, config hash, load condition, date

## 7. Last result (run for record)

-3 dB at 2.99 Hz unloaded (2.85 Hz at rated load). **PASS.**
