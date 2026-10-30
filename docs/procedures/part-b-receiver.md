# Part B receiver: test procedures

These tests check the ARINC 429 word format (ICD-1) and the receiver's per-word validity checks: parity (R1), SSM (R2), staleness (R3) and physical range (R4). All of them are **Unit** tests: they exercise the encoder, decoder and `Receiver` alone, with no simulation loop. Test file: `tests/test_part_b_receiver.py`.

| TC | Requirement(s) | Test function | Cases | Last result (run for record, commit d716c1f) |
|---|---|---|---|---|
| [TC-ICD-1-U01](#tc-icd-1-u01-bnr-value-survives-encode-and-decode) | ICD-1 | `test_icd_bnr_round_trip` | 8 | PASS (8 of 8) |
| [TC-ICD-1-U02](#tc-icd-1-u02-label-bits-are-stored-reversed) | ICD-1 | `test_icd_label_bits_are_reversed` | 1 | PASS |
| [TC-ICD-1-U03](#tc-icd-1-u03-every-word-has-odd-parity) | ICD-1 | `test_icd_odd_parity` | 1 | PASS |
| [TC-R1-U01](#tc-r1-u01-receiver-rejects-a-word-with-bad-parity) | R1 | `test_r1_bad_parity_rejected` | 1 | PASS |
| [TC-R2-U01](#tc-r2-u01-failure-warning-and-no-computed-data-make-the-label-invalid) | R2 | `test_r2_ssm_invalid` | 2 | PASS (2 of 2) |
| [TC-R2-U02](#tc-r2-u02-normal-ssm-makes-the-label-valid) | R2 | `test_r2_ssm_normal_valid` | 1 | PASS |
| [TC-R3-U01](#tc-r3-u01-stale-boundary-at-3-transmit-intervals) | R3 | `test_r3_stale_boundary` | 1 | PASS |
| [TC-R4-U01](#tc-r4-u01-values-outside-the-physical-range-are-invalid) | R4 | `test_r4_physical_range` | 4 | PASS (4 of 4) |

**Common setup for this file** (pytest does this before every test):

| Item | Python command | Where |
|---|---|---|
| Load settings from `config/sil.yaml` (once per session) | `load_config()` | conftest.py line 71 |
| Build the label list (pitch label 324, roll label 325) | `label_defs(cfg)` | test file line 12 |
| Create a fresh receiver, stale limit 3 intervals (from `icd.stale_intervals`) | `Receiver(labels, stale_intervals=cfg["icd"]["stale_intervals"])` | test file line 17 |

The ICD-1 tests only use the label list. The R1 to R4 tests also use the fresh receiver.

Pitch label values used below (from `icd.labels.pitch` in `config/sil.yaml`): label 324 octal, full-scale range 180.0°, 14 significant bits, so resolution = 180 / 2^14 = 0.010986°. Valid physical range -90.0° to +90.0°. Nominal rate 50 Hz.

---

## TC-ICD-1-U01: BNR value survives encode and decode

| Field | Value |
| --- | --- |
| Requirement | ICD-1: ARINC 429 BNR words shall be encoded per the ICD (label, SDI, sign, resolution, SSM, odd parity). |
| Level | Unit (encoder and decoder only) |
| Test file | `tests/test_part_b_receiver.py` |
| Test function | `test_icd_bnr_round_trip` (lines 23–27), parametrized at line 22 |

**Purpose:** show that a pitch value packed into a word and unpacked again comes back within half a bit, with the right label, Normal SSM and good parity, across positive, negative and full-scale values.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_b_receiver.py::test_icd_bnr_round_trip" -v
```
Expected output: `8 passed`. (A single test is a partial run: its report goes to `reports/dev/`, not for record.)

**Initial condition:** none. No receiver is used.

**Setup (done automatically by pytest before step 1):**

| Item | Python command | Where |
|---|---|---|
| Load settings | `load_config()` | conftest.py line 71 |
| Build the label list | `label_defs(cfg)` | test file line 12 |
| Pick the pitch label | `ld = labels["pitch"]` | test file line 24 |

**Steps (run once per case):**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Encode the case value as a pitch word, then decode it | `d = decode_bnr(encode_bnr(ld, value), ld)` | Decoded word returned | 25 |
| 2 | Check the decoded value | `abs(d.value - value) <= ld.resolution / 2 + 1e-9` | `True`: error ≤ 0.005493° (half of the 0.010986° resolution, from `icd.labels.pitch`) | 26 |
| 3 | Check the label | `d.label_octal == 0o324` | `True`: label 324 octal | 27 |
| 4 | Check the SSM | `d.ssm is SSM.NORMAL` | `True`: Normal Operation (default when encoding) | 27 |
| 5 | Check parity | `d.parity_ok` | `True`: odd parity | 27 |

**Cases:**

| Case | Value (°) | Result |
|---|---|---|
| 1 | 0.0 | PASS |
| 2 | 2.5 | PASS |
| 3 | -2.5 | PASS |
| 4 | 45.37 | PASS |
| 5 | -89.99 | PASS |
| 6 | 89.99 | PASS |
| 7 | 179.9 | PASS |
| 8 | -180.0 | PASS |

Note: 179.9° and -180.0° are outside the pitch physical range (±90°) but inside the word's full-scale range (±180°). This test checks encoding only, not the R4 range check.

**Pass criteria:** every step gives its expected result for every case. Each check is an `assert`; if any one fails, that case fails.

**Last result (run for record, commit d716c1f):** PASS, 8 of 8 cases (no measured values recorded).

---

## TC-ICD-1-U02: Label bits are stored reversed

| Field | Value |
| --- | --- |
| Requirement | ICD-1: ARINC 429 BNR words shall be encoded per the ICD (label, SDI, sign, resolution, SSM, odd parity). |
| Level | Unit (encoder only) |
| Test file | `tests/test_part_b_receiver.py` |
| Test function | `test_icd_label_bits_are_reversed` (lines 31–34) |

**Purpose:** show that the label sits in bits 1 to 8 in reversed bit order. ARINC 429 sends the label most significant bit first, so in the stored word it reads backwards. Label 324 octal is `11010100` in binary; reversed it is `00101011` (0x2B).

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_b_receiver.py::test_icd_label_bits_are_reversed" -v
```
Expected output: `1 passed`. (Partial run: report goes to `reports/dev/`, not for record.)

**Initial condition:** none. No receiver is used.

**Setup (done automatically by pytest before step 1):**

| Item | Python command | Where |
|---|---|---|
| Load settings | `load_config()` | conftest.py line 71 |
| Build the label list | `label_defs(cfg)` | test file line 12 |

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Encode a 0.0° pitch word | `word = encode_bnr(labels["pitch"], 0.0)` | Word returned | 33 |
| 2 | Take the low 8 bits and compare with the reversed label | `word & 0xFF == int("11010100"[::-1], 2)` | `True`: low byte is `00101011` (0x2B, decimal 43) | 34 |

**Pass criteria:** step 2 is `True`. It is an `assert`; if it fails, the test fails.

**Last result (run for record, commit d716c1f):** PASS (no measured values recorded).

---

## TC-ICD-1-U03: Every word has odd parity

| Field | Value |
| --- | --- |
| Requirement | ICD-1: ARINC 429 BNR words shall be encoded per the ICD (label, SDI, sign, resolution, SSM, odd parity). |
| Level | Unit (encoder only) |
| Test file | `tests/test_part_b_receiver.py` |
| Test function | `test_icd_odd_parity` (lines 38–40) |

**Purpose:** show that the encoder sets bit 32 so each full 32-bit word has an odd number of ones.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_b_receiver.py::test_icd_odd_parity" -v
```
Expected output: `1 passed`. (Partial run: report goes to `reports/dev/`, not for record.)

**Initial condition:** none. No receiver is used.

**Setup (done automatically by pytest before step 1):**

| Item | Python command | Where |
|---|---|---|
| Load settings | `load_config()` | conftest.py line 71 |
| Build the label list | `label_defs(cfg)` | test file line 12 |

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | For each of 0.0°, 1.0° and -33.3° | `for v in (0.0, 1.0, -33.3):` | Loop runs 3 times | 39 |
| 2 | Encode a pitch word and count its ones | `bin(encode_bnr(labels["pitch"], v)).count("1") % 2 == 1` | `True` each time: odd number of ones | 40 |

These three values are not separate pytest cases; they run inside one test. The first value that fails stops the test.

**Pass criteria:** step 2 is `True` for all three values. It is an `assert`; if it fails, the test fails.

**Last result (run for record, commit d716c1f):** PASS (no measured values recorded).

---

## TC-R1-U01: Receiver rejects a word with bad parity

| Field | Value |
| --- | --- |
| Requirement | R1: The receiver shall reject words with bad parity. |
| Level | Unit (receiver only) |
| Test file | `tests/test_part_b_receiver.py` |
| Test function | `test_r1_bad_parity_rejected` (lines 45–51) |

**Purpose:** show that a corrupted word is thrown away, the last good value is kept, and the reject is counted.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_b_receiver.py::test_r1_bad_parity_rejected" -v
```
Expected output: `1 passed`. (Partial run: report goes to `reports/dev/`, not for record.)

**Initial condition:** receiver just powered up, no words received yet.

**Setup (done automatically by pytest before step 1):**

| Item | Python command | Where |
|---|---|---|
| Load settings | `load_config()` | conftest.py line 71 |
| Build the label list | `label_defs(cfg)` | test file line 12 |
| Create a fresh receiver | `Receiver(labels, stale_intervals=cfg["icd"]["stale_intervals"])` (3) | test file line 17 |
| Pick the pitch label | `ld = labels["pitch"]` | test file line 46 |

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Send a good pitch word, 5.0°, at time 0 | `rx.receive("pitch", encode_bnr(ld, 5.0), 0.0)` | Returns `True` (accepted) | 47 |
| 2 | Send a 30.0° word with the parity bit flipped, at 20 ms | `rx.receive("pitch", encode_bnr(ld, 30.0, corrupt_parity=True), 0.02)` | Returns `False` (rejected). Inside `receive()` (sil/receiver.py lines 48–50) the reject counter goes up and nothing else changes | 48 |
| 3 | Read pitch at 30 ms | `valid, value, _ = rx.read("pitch", 0.03)` | `valid` is `True` | 49–50 |
| 4 | Check the value | `abs(value - 5.0) < 0.02` | `True`: value is still about 5.0°, not 30.0° | 50 |
| 5 | Check the reject count | `rx.status["pitch"].parity_rejects == 1` | `True` | 51 |

**Pass criteria:** every step gives its expected result. Each check is an `assert`; if any one fails, the test fails.

**Last result (run for record, commit d716c1f):** PASS (no measured values recorded).

---

## TC-R2-U01: Failure Warning and No Computed Data make the label invalid

| Field | Value |
| --- | --- |
| Requirement | R2: The receiver shall treat SSM Failure Warning or No Computed Data as invalid. |
| Level | Unit (receiver only) |
| Test file | `tests/test_part_b_receiver.py` |
| Test function | `test_r2_ssm_invalid` (lines 56–59), parametrized at line 55 |

**Purpose:** show that a word with good parity and an in-range value is still marked invalid when its SSM says Failure Warning or No Computed Data.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_b_receiver.py::test_r2_ssm_invalid" -v
```
Expected output: `2 passed`. pytest shows the cases as `[0]` and `[1]`, the SSM codes. (Partial run: report goes to `reports/dev/`, not for record.)

**Initial condition:** receiver just powered up, no words received yet.

**Setup (done automatically by pytest before step 1):**

| Item | Python command | Where |
|---|---|---|
| Load settings | `load_config()` | conftest.py line 71 |
| Build the label list | `label_defs(cfg)` | test file line 12 |
| Create a fresh receiver | `Receiver(labels, stale_intervals=cfg["icd"]["stale_intervals"])` (3) | test file line 17 |

**Steps (run once per case):**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Send a 5.0° pitch word with the case SSM, at time 0 | `rx.receive("pitch", encode_bnr(labels["pitch"], 5.0, ssm=ssm), 0.0)` | Word accepted (parity is good). The return value is not checked | 57 |
| 2 | Read pitch at 1 ms | `valid, _, reasons = rx.read("pitch", 0.001)` | Result returned | 58 |
| 3 | Check validity | `not valid` | `True`: pitch is invalid | 59 |
| 4 | Check the reason | `any(r.startswith("ssm_") for r in reasons)` | `True`: an SSM reason is listed (built in sil/receiver.py line 29) | 59 |

**Cases:**

| Case | SSM (code) | Reason the receiver gives | Result |
|---|---|---|---|
| `[0]` | Failure Warning (00) | `ssm_failure_warning` | PASS |
| `[1]` | No Computed Data (01) | `ssm_no_computed_data` | PASS |

**Pass criteria:** steps 3 and 4 are `True` for both cases. They are `assert`s; if one fails, that case fails.

**Last result (run for record, commit d716c1f):** PASS, 2 of 2 cases (no measured values recorded).

---

## TC-R2-U02: Normal SSM makes the label valid

| Field | Value |
| --- | --- |
| Requirement | R2: The receiver shall treat SSM Failure Warning or No Computed Data as invalid. |
| Level | Unit (receiver only) |
| Test file | `tests/test_part_b_receiver.py` |
| Test function | `test_r2_ssm_normal_valid` (lines 63–65) |

**Purpose:** the other half of R2. Show that a good word with Normal SSM is valid, so TC-R2-U01 is not passing just because the receiver marks everything invalid.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_b_receiver.py::test_r2_ssm_normal_valid" -v
```
Expected output: `1 passed`. (Partial run: report goes to `reports/dev/`, not for record.)

**Initial condition:** receiver just powered up, no words received yet.

**Setup (done automatically by pytest before step 1):**

| Item | Python command | Where |
|---|---|---|
| Load settings | `load_config()` | conftest.py line 71 |
| Build the label list | `label_defs(cfg)` | test file line 12 |
| Create a fresh receiver | `Receiver(labels, stale_intervals=cfg["icd"]["stale_intervals"])` (3) | test file line 17 |

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Send a 5.0° pitch word with Normal SSM (the default), at time 0 | `rx.receive("pitch", encode_bnr(labels["pitch"], 5.0), 0.0)` | Word accepted. The return value is not checked | 64 |
| 2 | Read pitch at 1 ms and check the valid flag | `rx.read("pitch", 0.001)[0]` | `True`: pitch is valid | 65 |

**Pass criteria:** step 2 is `True`. It is an `assert`; if it fails, the test fails.

**Last result (run for record, commit d716c1f):** PASS (no measured values recorded).

---

## TC-R3-U01: Stale boundary at 3 transmit intervals

| Field | Value |
| --- | --- |
| Requirement | R3: The receiver shall declare a label stale if not updated within 3 nominal transmit intervals. |
| Level | Unit (receiver only) |
| Test file | `tests/test_part_b_receiver.py` |
| Test function | `test_r3_stale_boundary` (lines 69–77) |

**Purpose:** show the stale limit is exactly 3 intervals: pitch is still valid at 3 intervals after the last word and stale 1 ms later.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_b_receiver.py::test_r3_stale_boundary" -v
```
Expected output: `1 passed`. (Partial run: report goes to `reports/dev/`, not for record.)

**Initial condition:** receiver just powered up, no words received yet.

**Setup (done automatically by pytest before step 1):**

| Item | Python command | Where |
|---|---|---|
| Load settings | `load_config()` | conftest.py line 71 |
| Build the label list | `label_defs(cfg)` | test file line 12 |
| Create a fresh receiver | `Receiver(labels, stale_intervals=cfg["icd"]["stale_intervals"])` (3) | test file line 17 |
| Pick the pitch label | `ld = labels["pitch"]` | test file line 71 |

**Steps:**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Send a good 5.0° pitch word at time 0 | `rx.receive("pitch", encode_bnr(ld, 5.0), 0.0)` | Word accepted. The return value is not checked | 72 |
| 2 | Work out the stale limit: 3 intervals at the pitch rate | `limit = 3 / ld.rate_hz` | 3 / 50 Hz = 0.060 s (rate from `icd.labels.pitch.rate_hz`) | 73 |
| 3 | Record the limit in the report | `record_property("stale_limit_ms", round(limit * 1000, 1))` | `stale_limit_ms` saved | 74 |
| 4 | Read pitch exactly at the limit, 60 ms | `rx.read("pitch", limit)[0]` | `True`: still valid | 75 |
| 5 | Read pitch 1 ms past the limit, 61 ms | `valid, _, reasons = rx.read("pitch", limit + 0.001)` | Result returned | 76 |
| 6 | Check it went stale | `not valid and "stale" in reasons` | `True`: invalid, reason `stale` | 77 |

How the receiver decides (sil/receiver.py line 26): stale when time since the last word is more than `stale_intervals / rate_hz` (3 from `icd.stale_intervals`, / 50 Hz = 60 ms) plus 1e-9 s. The tiny extra keeps "exactly 60 ms" on the valid side despite rounding.

**Pass criteria:** steps 4 and 6 are `True`. They are `assert`s; if either fails, the test fails.

**Last result (run for record, commit d716c1f):** PASS. Stale limit recorded: `stale_limit_ms` = 60.0.

---

## TC-R4-U01: Values outside the physical range are invalid

| Field | Value |
| --- | --- |
| Requirement | R4: The receiver shall reject values outside the physical range. |
| Level | Unit (receiver only) |
| Test file | `tests/test_part_b_receiver.py` |
| Test function | `test_r4_physical_range` (lines 83–85), parametrized at lines 81–82 |

**Purpose:** show that pitch is valid at the ±90.0° edges and invalid just past +90° and well past -90°.

**How to run (PowerShell, from the repo folder):**
```
python -m pytest "tests/test_part_b_receiver.py::test_r4_physical_range" -v
```
Expected output: `4 passed`. (Partial run: report goes to `reports/dev/`, not for record.)

**Initial condition:** receiver just powered up, no words received yet.

**Setup (done automatically by pytest before step 1):**

| Item | Python command | Where |
|---|---|---|
| Load settings | `load_config()` | conftest.py line 71 |
| Build the label list | `label_defs(cfg)` | test file line 12 |
| Create a fresh receiver | `Receiver(labels, stale_intervals=cfg["icd"]["stale_intervals"])` (3) | test file line 17 |

**Steps (run once per case):**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Send a pitch word with the case value, at time 0 | `rx.receive("pitch", encode_bnr(labels["pitch"], value), 0.0)` | Word accepted (parity good). Inside `receive()` (sil/receiver.py line 53) the decoded value is checked against -90.0° to +90.0° (`icd.labels.pitch.min_valid` / `max_valid`), edges included | 84 |
| 2 | Read pitch at 1 ms and compare the valid flag with the expected one | `rx.read("pitch", 0.001)[0] is expect_valid` | `True`: valid flag matches the case | 85 |

**Cases:**

| Case | Value sent (°) | Expected valid | Result |
|---|---|---|---|
| `[90.0-True]` | 90.0 (upper edge) | `True` | PASS |
| `[-90.0-True]` | -90.0 (lower edge) | `True` | PASS |
| `[90.5-False]` | 90.5 | `False` | PASS |
| `[-120.0-False]` | -120.0 | `False` | PASS |

The test checks only the valid flag, not the reason. For the two invalid cases the receiver's reason would be `out_of_range` (sil/receiver.py line 31).

**Pass criteria:** step 2 is `True` for all four cases. It is an `assert`; if it fails, that case fails.

**Last result (run for record, commit d716c1f):** PASS, 4 of 4 cases (no measured values recorded).
