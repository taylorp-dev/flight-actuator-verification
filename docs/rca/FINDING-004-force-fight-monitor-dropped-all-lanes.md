# FINDING-004: Force-fight monitor disengaged all three lanes

| Field | Value |
| --- | --- |
| Requirement | R13: disengage the faulty lane, and only that lane |
| Found by | Fault-size sweep while building the R13 tests (offsets 0.5 to 10 mm, every lane) |
| Status | Closed. Monitor isolates only the largest outlier; guard test added |

## Symptom

Three lanes active on one surface. Lane A's sensor offset jumps 3 mm or more. Expected: lane A disengaged. Actual: **all three lanes** disengaged in the same instant, so nothing held the surface and it ran away under load.

## Root cause

The first monitor disengaged every lane whose force differed from the mean of the others by more than the threshold for the persistence time. A big fault in one lane pulls the healthy lanes' differences over the threshold too (they're about half the faulty lane's), so all three timers expired together.

Same family as FINDING-002: a threshold check alone can't tell you *which* channel is bad; you need to pick the outlier.

## Corrective action

- When the persistence time expires, disengage only the lane with the largest force difference, then reset the timers. (`isolate_largest_only: true` in `config/sil.yaml`.)
- Guard test `test_r13_guard_monitor_isolates_only_the_largest_outlier` re-runs the old logic, proves it still drops all three lanes, then checks the fix drops only lane A.
- Verified across 15 cases (3 lanes x offsets +/-2, +/-5, +10 mm): correct lane every time, surface back within 0.10 mm.

## Open item

During the 0.2 s persistence time, a large fault (10 mm) moves the surface up to 3.7 mm before the lane is dropped. A two-level monitor (fast trip for very large differences, slower trip for small ones) would cut that. Next step.
