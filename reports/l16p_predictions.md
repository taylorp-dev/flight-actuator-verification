# Predicted bench results: Actuonix L16-P (35:1, 12 V, 100 mm)

Model parameters come from the manufacturer datasheet (`config/sil.yaml`, `bench_actuator_l16p`). The model is checked against the datasheet by requirement M1. These are predictions only. The desk rig is not built yet; the last column is filled in when it is.

- Config sha256: `cf49a2d63e6a`
- Planned bench spring load: 35 N

| Measurement | Predicted | Same test as | Measured on bench |
| --- | --- | --- | --- |
| Step 1 mm, unloaded: rise time | 110 ms | A1/A5 | (not built) |
| Step 1 mm, unloaded: overshoot | 0.0 % | A1/A5 | (not built) |
| Max extend rate, unloaded | 32.0 mm/s | A2 | (not built) |
| Step 1 mm, bench load 35 N: rise time | 110 ms | A1/A5 | (not built) |
| Step 1 mm, bench load 35 N: overshoot | 0.0 % | A1/A5 | (not built) |
| Max extend rate, bench load 35 N | 20.5 mm/s | A2 | (not built) |
| Static accuracy (pot on rod) | 0.095 mm | A3 | (not built) |
| Hysteresis seen at rod | 0.190 mm | A3 | (not built) |
| Bandwidth (-3 dB, 1 mm sine) | 3.09 Hz | A4 | (not built) |

Assumed values (not on the datasheet, measured on the bench first): motor lag, back-drive behavior.

Bench note: the L16-P's built-in pot has < 2 % linearity (up to ~2 mm over the full stroke) and 0.3 mm repeatability, so on the bench it will swamp a 0.1 mm accuracy reading. Calibrate it against a reference first, or read the rod with a separate sensor. Same principle as the flight-class tests: the unit never grades itself.
