# Part B voter: test procedures

These tests cover the triplex mid-value-select voter, requirements R5 to R8. They are Unit tests: the voter (`sil/voter.py`) is tested alone, and the test feeds it one frame of three channel values at a time. All tests are in `tests/test_part_b_voter.py`.

| TC | Requirement(s) | Test function | Cases | Last result (run for record) |
|---|---|---|---|---|
| [TC-R5-U01](#tc-r5-u01-voter-outputs-the-middle-of-three-values) | R5 | `test_r5_mid_value_select` | 6 | PASS |
| [TC-R6-U01](#tc-r6-u01-channel-fails-only-after-the-full-persistence-time) | R6 | `test_r6_fail_after_persistence` | 1 | PASS |
| [TC-R6-U02](#tc-r6-u02-threshold-has-margin-over-the-healthy-tolerance-stack) | R6 | `test_r6_threshold_has_margin_over_tolerance_stack` | 1 | PASS |
| [TC-R6-U03](#tc-r6-u03-channels-just-inside-threshold-never-fail) | R6 | `test_r6_within_threshold_never_fails` | 1 | PASS |
| [TC-R7-U01](#tc-r7-u01-a-single-one-frame-spike-is-ignored) | R7 | `test_r7_single_spike_ignored` | 1 | PASS |
| [TC-R7-U02](#tc-r7-u02-short-repeated-spikes-reset-the-counter-and-never-latch) | R7 | `test_r7_intermittent_spikes_reset_counter` | 1 | PASS |
| [TC-R8-U01](#tc-r8-u01-after-one-failure-the-voter-averages-the-other-two-and-annunciates) | R8 | `test_r8_dual_mode_average_and_annunciate` | 1 | PASS |
| [TC-R8-U02](#tc-r8-u02-a-disagreement-in-dual-mode-is-annunciated) | R8 | `test_r8_second_fault_in_dual_is_annunciated` | 1 | PASS |
| [TC-R8-U03](#tc-r8-u03-an-invalid-channel-is-left-out-of-the-vote) | R8 | `test_r8_invalid_channel_excluded` | 1 | PASS |

**Common setup for this file** (pytest does this before every test):

| Item | Python command | Where |
|---|---|---|
| Load settings from `config/sil.yaml` (once per run, shared by all tests) | `load_config()` | conftest.py line 71 |
| Read the voter settings | `v = cfg["voter"]` | test file line 12 |
| Create a fresh voter for each test: threshold 2.5°, persistence 0.10 s, frame 0.02 s | `MidValueVoter(v["threshold_deg"], v["persistence_s"], v["frame_s"])` | test file line 13 |
| Helper used by several tests: send the same three values, all marked valid, for `n` frames in a row, and return the output of the last frame | `frames(voter, values, n)`: loops `voter.update([(True, x) for x in values])` | test file lines 16–20 |

Limits used below (all from `config/sil.yaml`): `voter.threshold_deg` = 2.5°, `voter.tolerance_deg` = 1.0°, `voter.persistence_s` = 0.10 s, `voter.frame_s` = 0.02 s.

**How the voter decides, in short** (`sil/voter.py`, `update()`, lines 51–85):

- A channel counts only if it is marked valid and has not already been failed (line 53).
- With three channels, each one is compared to the middle value. A channel more than the threshold (2.5°) away adds 1 to its counter; a channel within threshold has its counter reset to 0 (lines 56–65).
- A channel is latched failed when its counter reaches `ceil(persistence_s / frame_s)` = `ceil(0.10 / 0.02)` = 5 frames in a row (lines 49, 61–63). Once failed, it stays failed.
- Three channels left: output the middle value, mode TRIPLEX. Two left: output their average, mode DUAL, and add `DUAL_MISCOMPARE` if they differ by more than 2.5°. One left: pass it through, mode SIMPLEX. None: hold the last output, mode FAIL (lines 68–78).
- Annunciations: `CHANNEL_FAILED:<letters>` if any channel is failed, and `DEGRADED_<mode>` for any mode other than TRIPLEX (lines 80–83). Channels are 0 = A, 1 = B, 2 = C.

---

## TC-R5-U01: Voter outputs the middle of three values

| Field | Value |
| --- | --- |
| Requirement | R5: With three valid sources, the voter shall output the middle value. |
| Level | Unit (voter only, driven frame by frame) |
| Test file | `tests/test_part_b_voter.py` |
| Test function | `test_r5_mid_value_select` (lines 23–27) |

**Purpose:** show that the voter picks the middle value no matter which channel carries it. The test runs once for each of the 6 orders of the values 4.0°, 5.0° and 5.8°.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_b_voter.py::test_r5_mid_value_select" -v
```
Expected output: `6 passed`. (A single test is a partial run: its report goes to `reports/dev/`, not for record.)

**Initial condition:** fresh voter, no frames received yet, no channel failed.

**Setup (done automatically by pytest before step 1):** common setup above, plus the case list.

| Item | Python command | Where |
|---|---|---|
| Make the 6 cases: every order of 4.0, 5.0, 5.8 | `@pytest.mark.parametrize("perm", list(itertools.permutations([4.0, 5.0, 5.8])))` | test file line 24 |

**Cases:**

| Case | Channel A | Channel B | Channel C | Expected output | Result |
|---|---|---|---|---|---|
| perm0 | 4.0 | 5.0 | 5.8 | 5.0, TRIPLEX | PASS |
| perm1 | 4.0 | 5.8 | 5.0 | 5.0, TRIPLEX | PASS |
| perm2 | 5.0 | 4.0 | 5.8 | 5.0, TRIPLEX | PASS |
| perm3 | 5.0 | 5.8 | 4.0 | 5.0, TRIPLEX | PASS |
| perm4 | 5.8 | 4.0 | 5.0 | 5.0, TRIPLEX | PASS |
| perm5 | 5.8 | 5.0 | 4.0 | 5.0, TRIPLEX | PASS |

**Steps (same for every case):**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Send one frame with the three values in this case's order, all valid | `out = voter.update([(True, x) for x in perm])` | Voter returns an output | 26 |
| 2 | Check the value and the mode | `out.value == 5.0 and out.mode is Mode.TRIPLEX` | `True`: output is exactly 5.0° and mode is TRIPLEX | 27 |

Note: the outer values are 1.0° and 0.8° from the middle, both inside the 2.5° threshold (`voter.threshold_deg`), so no miscompare counting happens.

**Pass criteria:** every case gives its expected result. Each check is an `assert`; if any one fails, that case fails.

**Last result (run for record):** PASS, 6 of 6 cases (no measured values recorded).

---

## TC-R6-U01: Channel fails only after the full persistence time

| Field | Value |
| --- | --- |
| Requirement | R6: The voter shall fail a channel that miscompares beyond threshold for longer than the persistence time. |
| Level | Unit (voter only, driven frame by frame) |
| Test file | `tests/test_part_b_voter.py` |
| Test function | `test_r6_fail_after_persistence` (lines 30–38) |

**Purpose:** show that a channel that is far off is still trusted one frame before the persistence time is up, and is latched failed on the frame that completes it.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_b_voter.py::test_r6_fail_after_persistence" -v
```
Expected output: `1 passed`. (A single test is a partial run: its report goes to `reports/dev/`, not for record.)

**Initial condition:** fresh voter, no frames received yet, no channel failed.

**Setup (done automatically by pytest before step 1):** common setup above.

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Work out how many frames make up the persistence time: 0.10 s / 0.02 s | `needed = round(cfg["voter"]["persistence_s"] / cfg["voter"]["frame_s"])` | `needed` = 5 (from `voter.persistence_s` and `voter.frame_s`) | 33 |
| 2 | Record that number in the report | `record_property("frames_to_latch", needed)` | Saved as `frames_to_latch` | 34 |
| 3 | Send 4 frames (one short) with B at 9.0°, A at 5.0°, C at 5.1° | `out = frames(voter, [5.0, 9.0, 5.1], needed - 1)` | Middle is 5.1°; B is 3.9° off, more than the 2.5° threshold, so B's counter goes to 4 | 35 |
| 4 | Check no channel has failed yet | `assert not out.failed` | `True`: failed set is empty | 36 |
| 5 | Send the 5th frame with the same values | `out = voter.update([(True, 5.0), (True, 9.0), (True, 5.1)])` | B's counter reaches 5 and B is latched failed | 37 |
| 6 | Check only channel B (index 1) failed | `assert out.failed == {1}` | `True`: failed set is exactly {B} | 38 |

**Pass criteria:** every step gives its expected result. Each check is an `assert`; if any one fails, the test fails.

**Last result (run for record):** PASS. `frames_to_latch` = 5.

---

## TC-R6-U02: Threshold has margin over the healthy tolerance stack

| Field | Value |
| --- | --- |
| Requirement | R6: The voter shall fail a channel that miscompares beyond threshold for longer than the persistence time. |
| Level | Unit (configuration check, no voter is run) |
| Test file | `tests/test_part_b_voter.py` |
| Test function | `test_r6_threshold_has_margin_over_tolerance_stack` (lines 41–48) |

**Purpose:** guard against FINDING-002. Two healthy sensors at opposite ends of their ±1.0° spec can differ by 2.0°. The voter threshold must be bigger than that by a margin, or normal noise can fail a good channel. This test only checks numbers in `config/sil.yaml`; it does not create or run a voter.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_b_voter.py::test_r6_threshold_has_margin_over_tolerance_stack" -v
```
Expected output: `1 passed`. (A single test is a partial run: its report goes to `reports/dev/`, not for record.)

**Initial condition:** baseline configuration loaded.

**Setup (done automatically by pytest before step 1):** only the settings load from the common setup (`load_config()`, conftest.py line 71). This test does not use the voter fixture.

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Read the voter settings | `v = cfg["voter"]` | Settings available | 45 |
| 2 | Margin = threshold minus 2 x tolerance = 2.5 − 2 x 1.0 | `margin = v["threshold_deg"] - 2 * v["tolerance_deg"]` | `margin` = 0.5° (from `voter.threshold_deg` and `voter.tolerance_deg`) | 46 |
| 3 | Record the margin in the report, rounded to 2 places | `record_property("margin_deg", round(margin, 2))` | Saved as `margin_deg` | 47 |
| 4 | Check the margin is at least 0.25° | `assert margin >= cfg["voter"]["margin_min_deg"]` | `True`: 0.5° ≥ 0.25° (minimum from `voter.margin_min_deg`) | 48 |

**Pass criteria:** every step gives its expected result. The check is an `assert`; if it fails, the test fails.

**Last result (run for record):** PASS. `margin_deg` = 0.5.

---

## TC-R6-U03: Channels just inside threshold never fail

| Field | Value |
| --- | --- |
| Requirement | R6: The voter shall fail a channel that miscompares beyond threshold for longer than the persistence time. |
| Level | Unit (voter only, driven frame by frame) |
| Test file | `tests/test_part_b_voter.py` |
| Test function | `test_r6_within_threshold_never_fails` (lines 51–55) |

**Purpose:** show the other side of R6. Channels that sit just inside the threshold for a long time (200 frames, 4 s) are never failed.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_b_voter.py::test_r6_within_threshold_never_fails" -v
```
Expected output: `1 passed`. (A single test is a partial run: its report goes to `reports/dev/`, not for record.)

**Initial condition:** fresh voter, no frames received yet, no channel failed.

**Setup (done automatically by pytest before step 1):** common setup above.

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Read the threshold | `thr = cfg["voter"]["threshold_deg"]` | `thr` = 2.5° (from `voter.threshold_deg`) | 53 |
| 2 | Send 200 frames: A at 5.0°, B at 5.0 + 0.99 x 2.5 = 7.475°, C at 5.0 − 0.99 x 2.5 = 2.525° | `out = frames(voter, [5.0, 5.0 + 0.99 * thr, 5.0 - 0.99 * thr], 200)` | Middle is A at 5.0°. B and C are each 2.475° from it, inside 2.5°, so no counter ever goes up | 54 |
| 3 | Check nothing failed and mode is still TRIPLEX | `assert not out.failed and out.mode is Mode.TRIPLEX` | `True`: failed set empty, mode TRIPLEX | 55 |

Note: B and C are 4.95° apart from each other. That does not matter in TRIPLEX, because each channel is compared to the middle value, not to the other channels.

**Pass criteria:** every step gives its expected result. The check is an `assert`; if it fails, the test fails.

**Last result (run for record):** PASS (no measured values recorded).

---

## TC-R7-U01: A single one-frame spike is ignored

| Field | Value |
| --- | --- |
| Requirement | R7: The voter shall not fail a channel on a single short spike. |
| Level | Unit (voter only, driven frame by frame) |
| Test file | `tests/test_part_b_voter.py` |
| Test function | `test_r7_single_spike_ignored` (lines 58–63) |

**Purpose:** show that one bad frame on one channel does not fail that channel.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_b_voter.py::test_r7_single_spike_ignored" -v
```
Expected output: `1 passed`. (A single test is a partial run: its report goes to `reports/dev/`, not for record.)

**Initial condition:** fresh voter, no frames received yet, no channel failed.

**Setup (done automatically by pytest before step 1):** common setup above.

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Send 5 good frames, all three at 5.0° | `frames(voter, [5.0, 5.0, 5.0], 5)` | All counters stay at 0 | 60 |
| 2 | Send one frame with B spiked to 40.0° | `voter.update([(True, 5.0), (True, 40.0), (True, 5.0)])` | B is 35° off, so B's counter goes to 1 (5 are needed to fail) | 61 |
| 3 | Send 20 more good frames, all at 5.0° | `out = frames(voter, [5.0, 5.0, 5.0], 20)` | B is back inside threshold, so its counter resets to 0 | 62 |
| 4 | Check nothing failed and mode is TRIPLEX | `assert not out.failed and out.mode is Mode.TRIPLEX` | `True`: failed set empty, mode TRIPLEX | 63 |

**Pass criteria:** every step gives its expected result. The check is an `assert`; if it fails, the test fails.

**Last result (run for record):** PASS (no measured values recorded).

---

## TC-R7-U02: Short repeated spikes reset the counter and never latch

| Field | Value |
| --- | --- |
| Requirement | R7: The voter shall not fail a channel on a single short spike. |
| Level | Unit (voter only, driven frame by frame) |
| Test file | `tests/test_part_b_voter.py` |
| Test function | `test_r7_intermittent_spikes_reset_counter` (lines 66–73) |

**Purpose:** show that the miscompare counter resets on every good frame. Ten bursts of 4 bad frames (one short of the 5 needed), each followed by 1 good frame, never fail the channel.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_b_voter.py::test_r7_intermittent_spikes_reset_counter" -v
```
Expected output: `1 passed`. (A single test is a partial run: its report goes to `reports/dev/`, not for record.)

**Initial condition:** fresh voter, no frames received yet, no channel failed.

**Setup (done automatically by pytest before step 1):** common setup above.

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Work out the frames in the persistence time: 0.10 s / 0.02 s | `needed = round(cfg["voter"]["persistence_s"] / cfg["voter"]["frame_s"])` | `needed` = 5 | 69 |
| 2 | Repeat steps 2a and 2b 10 times | `for _ in range(10):` | 10 bursts, 50 frames total | 70 |
| 2a | Send 4 frames with B spiked to 40.0° | `frames(voter, [5.0, 40.0, 5.0], needed - 1)` | B's counter climbs to 4, one short of failing | 71 |
| 2b | Send 1 good frame, all at 5.0° | `frames(voter, [5.0, 5.0, 5.0], 1)` | B's counter resets to 0 | 72 |
| 3 | Check the voter's failed set | `assert not voter.failed` | `True`: no channel failed | 73 |

**Pass criteria:** every step gives its expected result. The check is an `assert`; if it fails, the test fails.

**Last result (run for record):** PASS (no measured values recorded).

---

## TC-R8-U01: After one failure the voter averages the other two and annunciates

| Field | Value |
| --- | --- |
| Requirement | R8: After one channel failure, the voter shall continue on the remaining two and annunciate. |
| Level | Unit (voter only, driven frame by frame) |
| Test file | `tests/test_part_b_voter.py` |
| Test function | `test_r8_dual_mode_average_and_annunciate` (lines 76–83) |

**Purpose:** show that once channel B is latched failed, the voter goes to DUAL, outputs the average of A and C, and raises both the channel-failed and the degraded-mode annunciations.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_b_voter.py::test_r8_dual_mode_average_and_annunciate" -v
```
Expected output: `1 passed`. (A single test is a partial run: its report goes to `reports/dev/`, not for record.)

**Initial condition:** fresh voter, no frames received yet, no channel failed.

**Setup (done automatically by pytest before step 1):** common setup above.

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Work out the frames in the persistence time | `needed = round(cfg["voter"]["persistence_s"] / cfg["voter"]["frame_s"])` | `needed` = 5 | 78 |
| 2 | Send 6 frames (5 + 1): A at 4.0°, B at 30.0°, C at 6.0° | `out = frames(voter, [4.0, 30.0, 6.0], needed + 1)` | Middle is 6.0°; B is 24° off. B fails on frame 5; frame 6 runs on A and C only | 79 |
| 3 | Check the mode | `assert out.mode is Mode.DUAL` | Mode is DUAL | 80 |
| 4 | Check the value is the average of A and C, (4.0 + 6.0) / 2 | `assert out.value == pytest.approx(5.0)` | Value is 5.0° | 81 |
| 5 | Check the channel-failed annunciation | `assert "CHANNEL_FAILED:B" in out.annunciations` | Present | 82 |
| 6 | Check the degraded-mode annunciation | `assert "DEGRADED_DUAL" in out.annunciations` | Present | 83 |

Note: A and C differ by 2.0°, inside the 2.5° threshold, so `DUAL_MISCOMPARE` is not expected here (the test does not check for it either way).

**Pass criteria:** every step gives its expected result. Each check is an `assert`; if any one fails, the test fails.

**Last result (run for record):** PASS (no measured values recorded).

---

## TC-R8-U02: A disagreement in dual mode is annunciated

| Field | Value |
| --- | --- |
| Requirement | R8: After one channel failure, the voter shall continue on the remaining two and annunciate. |
| Level | Unit (voter only, driven frame by frame) |
| Test file | `tests/test_part_b_voter.py` |
| Test function | `test_r8_second_fault_in_dual_is_annunciated` (lines 86–92) |

**Purpose:** with only two channels left, the voter can tell they disagree but cannot tell which one is wrong. Show that it raises `DUAL_MISCOMPARE` instead of failing either one.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_b_voter.py::test_r8_second_fault_in_dual_is_annunciated" -v
```
Expected output: `1 passed`. (A single test is a partial run: its report goes to `reports/dev/`, not for record.)

**Initial condition:** fresh voter, no frames received yet, no channel failed.

**Setup (done automatically by pytest before step 1):** common setup above.

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Work out the frames in the persistence time | `needed = round(cfg["voter"]["persistence_s"] / cfg["voter"]["frame_s"])` | `needed` = 5 | 89 |
| 2 | Send 6 frames with B at 30.0° to fail B (same as TC-R8-U01 step 2) | `frames(voter, [4.0, 30.0, 6.0], needed + 1)` | B latched failed, voter in DUAL on A and C | 90 |
| 3 | Send one frame with C moved to 12.0° (B still at 30.0°, but B is already failed and ignored) | `out = voter.update([(True, 4.0), (True, 30.0), (True, 12.0)])` | A and C differ by 8.0°, more than the 2.5° threshold | 91 |
| 4 | Check the dual miscompare annunciation | `assert "DUAL_MISCOMPARE" in out.annunciations` | Present | 92 |

**Pass criteria:** every step gives its expected result. The check is an `assert`; if it fails, the test fails.

**Last result (run for record):** PASS (no measured values recorded).

---

## TC-R8-U03: An invalid channel is left out of the vote

| Field | Value |
| --- | --- |
| Requirement | R8: After one channel failure, the voter shall continue on the remaining two and annunciate. |
| Level | Unit (voter only, driven frame by frame) |
| Test file | `tests/test_part_b_voter.py` |
| Test function | `test_r8_invalid_channel_excluded` (lines 95–98) |

**Purpose:** show that a channel marked invalid (for example, stale or rejected by the receiver) is left out right away, on the same frame, and its value is not used. The voter runs on the other two.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_b_voter.py::test_r8_invalid_channel_excluded" -v
```
Expected output: `1 passed`. (A single test is a partial run: its report goes to `reports/dev/`, not for record.)

**Initial condition:** fresh voter, no frames received yet, no channel failed.

**Setup (done automatically by pytest before step 1):** common setup above.

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Send one frame: A valid at 4.0°, B marked invalid with a junk value 99.0°, C valid at 6.0° | `out = voter.update([(True, 4.0), (False, 99.0), (True, 6.0)])` | B is not counted; only A and C are available | 97 |
| 2 | Check the mode and the value | `out.mode is Mode.DUAL and out.value == pytest.approx(5.0)` | `True`: mode DUAL, value is the average of A and C, 5.0° (99.0 is not used) | 98 |

Note: this test does not check annunciations. B is not latched failed here (it is only invalid for this frame), so the voter would raise `DEGRADED_DUAL` but not `CHANNEL_FAILED:B`.

**Pass criteria:** every step gives its expected result. The check is an `assert`; if it fails, the test fails.

**Last result (run for record):** PASS (no measured values recorded).
