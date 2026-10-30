# FINDING-003: Can't hold position at rated load after losing one motor

| Field | Value |
| --- | --- |
| Requirement | R11: after loss of one of two motor channels, hold commanded position within 0.50 mm for 5 s at every load up to rated |
| Found by | `tests/test_part_c_actuator_faults.py::test_r11_motor_channel_loss_hold[rated]` (first run of Part C) |
| Status | Open. Kept as a strict xfail. Corrective option A verified in the SIL; sizing decision belongs to the actuator design team |

## Symptom

Two motors drive one screw and share the load. Lose one at t = 1 s while holding position:

| Load | Stall force left | Max deviation in 5 s | Result |
| --- | --- | --- | --- |
| Unloaded | 3,250 N | 0.00 mm | PASS |
| Rated (4,550 N) | 3,250 N | 1.70 mm, still growing | **FAIL** |

The tracking monitor (R12) does annunciate it, about 3 s after the loss, so it isn't silent. It just can't be held.

## Root cause

Sizing, not software. Each motor provides half the total stall force (3,250 N). Rated load is 70 % of total stall, which is 140 % of what one motor can push. With one motor, the actuator can't hold the load, so the load slowly back-drives the rod.

Single-motor tests and two-motor acceptance tests can't show this. It only appears when the fault (motor loss) and a realistic load are combined, the same pattern as RCA-001.

## Options

- **A. Size each motor for rated load alone** (total stall doubled). Verified: `test_r11_corrective_option_verified` holds 0.00 mm at every load. Costs weight and power.
- **B. Accept a reduced load envelope after a motor loss.** Annunciate, then limit authority or load (flight-condition dependent). Needs a requirement change and a flight-envelope analysis.
- **C. Faster annunciation** from motor-driver health data (phase current) instead of position tracking, so the crew/flight control knows in milliseconds rather than seconds.

## Lesson

Redundancy inside the actuator only covers you at loads one channel can carry. The test matrix needs fault x load, not fault alone.
