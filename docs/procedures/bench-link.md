# Bench link (Raspberry Pi): test procedures

These tests check channel A when it comes from a real, separate computer: a Raspberry Pi sending ARINC 429 words over a real Ethernet cable. All 7 are **Bench** level, in `tests/test_bench_link.py`. They run either live (pytest drives the Pi, records, and pulls the link) or on the last recordings in `bench_data/` (replay). A live monitor also checks the words while they arrive; its results are checked when they come from the same run as the recording.

Last results below come from the run for record: FULL RUN, 127 of 127 tests (124 passed, 3 xfail), commit `d716c1f`, config `f1bfb3f5a287`, generated 2026-10-30T01:13:46 UTC (Oct 19 morning Pacific). It replays the recording from the Test Set 4 live run, below. The official record is [reports/traceability.md](../../reports/traceability.md).

| TC | Requirement(s) | Test function | Cases | Last result (run for record, commit d716c1f) |
|---|---|---|---|---|
| [TC-ICD-1-B01](#tc-icd-1-b01-words-from-the-pi-decode-per-the-icd) | ICD-1, L1 | `test_l1_words_on_the_wire_decode_per_icd` | 1 | PASS |
| [TC-L1-B01](#tc-l1-b01-word-rate-and-timing-on-the-real-link) | L1 | `test_l1_rate_and_jitter_on_real_link` | 1 | PASS |
| [TC-L1-B02](#tc-l1-b02-no-false-stale-on-a-healthy-link) | L1, R3 | `test_l1_no_false_stale_on_healthy_link` | 1 | PASS |
| [TC-L1-B03](#tc-l1-b03-link-loss-flagged-stale-then-recovers) | L1, R3 | `test_l1_cable_pull_flagged_stale_and_recovers` | 1 | PASS |
| [TC-L1-B04](#tc-l1-b04-closed-loop-with-the-real-channel-a) | L1, R5 | `test_l1_closed_loop_with_real_channel_a` | 1 | PASS |
| [TC-L1-B05](#tc-l1-b05-closed-loop-through-the-link-loss) | L1, R8, R10 | `test_l1_closed_loop_cable_pull` | 1 | PASS |
| [TC-L2-B01](#tc-l2-b01-live-checks-agree-with-the-replay) | L2 | `test_l2_live_vs_replay_agree` | 1 | PASS |

In every TC, the live-monitor rows are marked "(live results only, when present)". They run when `bench_data/live_monitor.json` comes from the same run as the recording. For the current recording it does, so they ran in the run for record.

**Common setup for this file** (pytest does this before every test):

| Item | Python command | Where |
|---|---|---|
| Load settings (once per session) | `load_config()` | conftest.py lines 68–71 |
| Get the bench data (once per session). Live: do the capture (Part 1). Replay: read `healthy.csv` and `cable_pull.csv`, and `live_monitor.json` only if its `recorded_utc` matches the recording's | `bench(request, cfg)` | test file lines 121–136 |
| Live mode switch and options | `--live`, `--pi` (default `taylor@dronepi.local`), `--data-host` (default `192.168.2.2`), `--drop-at` (15.0 s), `--drop-for` (5.0 s) | conftest.py lines 55–64 |
| Pick one recording; skip the test (NOT RUN) if it doesn't exist | `capture(bench, name)` | test file lines 147–151 |
| Get the live results from the same run, or `None` | `live_results(bench)` | test file lines 154–156 |
| Save measured values to the report | `record_property` (built into pytest) | |

Fixed values in the test file: `TRUE_PITCH = -2.0` (what the Pi sends by default, line 49), `PULL_MIN_GAP_S = 0.5` (a gap this long is the link drop, line 50), `REPLAY_MAX_S = 30.0` (line 51).

Limits from `config/sil.yaml`: pitch label 324 octal at `icd.labels.pitch.rate_hz` = 50 Hz, so one interval is 20 ms; `icd.stale_intervals` = 3, so the stale limit is 3 / 50 Hz = 60 ms; `bench_link.live_check_period_s` = 0.001 s; `bench_link.live_vs_replay_tol_ms` = 5.0 ms.

**Recordings used for the last result (run for record, Test Set 4)** (header lines of `bench_data/cable_pull.csv`, same in `healthy.csv`):

| Header | Value |
|---|---|
| recorded_utc | 2026-10-19T16:12:43+00:00 (Oct 19 morning Pacific) |
| mode | live, automated (pytest --live) |
| sender | 192.168.2.1 |
| pi_ssh | taylor@dronepi.local |
| pi_code | unknown (git pull failed: fatal: not a git repository ...) |
| receiver_host / receiver_os | razor / Windows 11 |
| link | direct Ethernet cable, UDP, one ARINC 429 word per datagram |
| link_drop | Pi eth0 down at 15 s for 5 s (ip link set) |
| recorded_s | 32.0 (replay end) |
| config_sha256_12 | baae11ef69bb |
| words | cable_pull.csv 2321 (0 to 32.0 s); healthy.csv 1438 (0 to 14.4 s, "portion of the live run before the link drop") |

The recording's config fingerprint (`baae11ef69bb`) is from when it was captured. Since then `config/sil.yaml` changed only in a comment, so the settings are identical; the run for record's fingerprint is `f1bfb3f5a287`.

`bench_data/live_monitor.json` is from the same run (`recorded_utc` 2026-10-19T16:12:43+00:00), so the live rows are checked.

---

## Part 1: Capture (live mode only), shared by all TCs

The capture runs **once per pytest session**, inside the `bench` fixture (test file line 124), before the first test. All 7 tests then run on the files it saves. In replay mode Part 1 is skipped and the tests read the saved files. Code: `run_live()` in `tests/test_bench_link.py`, lines 54–118, using `sil/bench.py`.

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| C1 | Build the label list and the Pi controller: SSH target from `--pi`, data address from `--data-host` | `pi = PiRemote(target=opt.getoption("--pi"), data_host=opt.getoption("--data-host"))` | Ready | 56–57 |
| C2 | Work out the timing: drop at 15 s for 5 s, record 15 + 5 + 12 = 32 s | `record_s = drop_at + drop_for + 12.0` | `record_s` = 32 s | 58–59 |
| C3 | Check the Pi is ready over SSH: venv Python, sender script, and `sudo -n ip link show eth0` without a password | `pi.check_ready()` | Returns `"ok"`; otherwise stops with "Pi not ready for live tests" | 60 (sil/bench.py 234–243) |
| C4 | Update the code on the Pi | `pi_commit = pi.update_code()` | Short git commit; if `git pull` fails, "unknown (git pull failed: ...)" and the run carries on | 61 (sil/bench.py 245–250) |
| C5 | Stop any sender left running | `pi.stop_sender()` | No old sender running | 62 |
| C6 | Create the live monitor: same receiver code as the SIL, stale after 3 intervals, re-check every 1 ms | `monitor = LiveMonitor(labels, cfg["icd"]["stale_intervals"], check_period_s=cfg["bench_link"]["live_check_period_s"])` | Monitor ready, `check_period_s` = 0.001 | 63–64 |
| C7 | Print the run banner | `print(f"\n[live] Pi {pi.target} (code {pi_commit}) -> {pi.data_host}; " ...)` | Console shows e.g. `[live] Pi taylor@192.168.2.1 (code ...) -> 192.168.2.10; link drop at 15 s for 5 s; recording 32 s` | 77–78 |
| C8 | Open UDP port 42900, then start the Pi sender for 40 s (`record_s + 8.0`) and schedule the link drop on the Pi; record for 32 s; stop if no word arrives within 25 s | `rows, sender = capture_udp(labels, ..., record_s, after_bind=start, first_word_timeout_s=25.0, status=show, status_every_s=1.0, monitor=monitor)` | Recording made | 80–82, `start()` 73–75 |
| C8a | *(inside the capture)* Each word is timestamped on arrival (time from the first word) and saved, then handed to the live monitor. The monitor adds the word, written exactly as the recording stores it (`row_text`), to a SHA-256 fingerprint; counts decode errors (label not in ICD, parity, SDI not 1, SSM not Normal); and feeds its receiver | `rows.append((t, word))` ... `monitor.on_word(t, word)` / `self._fingerprint.update(self.row_text(t, word).encode())` | Every word goes to both the recording and the monitor | sil/bench.py 178–189, `row_text` 58–61, `on_word` 63–77 |
| C8b | *(inside the capture)* After every word, and every 1 ms when no word comes (socket timeout = check period), the monitor re-reads pitch validity at the current time, records each valid/invalid change, and measures how late its own checks ran | `monitor.on_check(time.perf_counter() - t0)` | A link loss is caught live, at real time | sil/bench.py 166, 198–199, `on_check` 79–87 |
| C8c | *(inside the capture)* Once a second, live status on the console (printed even though pytest normally hides output) | `print(f"[live] t={t:5.1f} s  words {n:5d}  pitch {value:+7.3f} deg  {txt}", flush=True)` | e.g. `[live] t=  5.0 s  words   501  pitch  -1.001 deg  VALID`; during the drop `INVALID: stale` | 67–71 (called from sil/bench.py 200–203) |
| C8d | *(inside the capture, on the Pi)* Take the Pi's Ethernet port down at 15 s, back up 5 s later; runs detached on the Pi so the link always comes back | `sleep 15; sudo -n /usr/sbin/ip link set eth0 down; sleep 5; ... up` | Words stop, then come back | sil/bench.py 261–265 |
| C9 | Whatever happens, stop the sender and make sure the Pi port is up | `pi.stop_sender()` / `pi.link_up()` | Pi back to normal | 83–85 |
| C10 | Check the link came back: there must be pitch words in the last 0.5 s of the recording | `if len(pt) and record_s - pt[-1] >= PULL_MIN_GAP_S: raise RuntimeError(...)` | Words at the end; otherwise the run stops with "live run: no words after ... s of 32 s, the link never came back: check the Pi's network (BENCH-GUIDE troubleshooting)" | 86, 89–91 |
| C11 | Find the longest gap between pitch words; it must be at least 0.5 s | `if not len(gaps) or gaps[i] < PULL_MIN_GAP_S: raise RuntimeError(...)` | Gap found; otherwise the run stops with "live run saw no link drop: check the sudo rule for 'ip link' on the Pi" | 87–88, 92–93 |
| C12 | Cut the healthy part: every word up to 0.5 s before the last word before the gap | `healthy = [r for r in rows if r[0] < pt[i] - 0.5]` | Healthy rows | 94 |
| C13 | Write the header info (time, sender, Pi, receiver PC, link, drop, recording length `recorded_s`, config hash) and save both recordings | `"recorded_s": record_s,` ... `write_capture(BENCH / f"{name}.csv", r, m)` | `bench_data/healthy.csv` and `bench_data/cable_pull.csv` written, header includes `recorded_s: 32.0` | 95–112 |
| C14 | Save the live monitor's results next to them, with the same `recorded_utc` | `(BENCH / "live_monitor.json").write_text(json.dumps(live, indent=2))` | `bench_data/live_monitor.json` written (includes `words_sha256`, `false_stale_outside_drop`, `link_drop`) | 113–116 (results: sil/bench.py 89–126) |
| C15 | Hand all three to the tests | `return out` | Tests run on this fresh data | 117–118, 124 |

---

## TC-ICD-1-B01: Words from the Pi decode per the ICD

| Field | Value |
| --- | --- |
| Requirements | ICD-1: ARINC 429 BNR words shall be encoded per the ICD (label, SDI, sign, resolution, SSM, odd parity). L1: Channel A sent from a separate computer over a real Ethernet link shall decode per the ICD, arrive at the nominal label rate (mean interval within 2 %) without gaps long enough to trip the stale check, and a link loss shall be flagged stale within 3 intervals and recover automatically. |
| Level | Bench (hardware in the loop) |
| Test file | `tests/test_bench_link.py` |
| Test function | `test_l1_words_on_the_wire_decode_per_icd` (lines 221–243) |

**Purpose:** show that every word that came over the real cable has a known label, good parity, SDI 1 and Normal SSM, and that the pitch value is what the Pi was told to send.

**Equipment:**

| Item | What |
|---|---|
| Sender | Raspberry Pi 4 "dronepi" running `tools/pi_channel_a.py` (channel A: pitch -2.0°, channel A bias +1.0°, noise, 50 Hz) |
| Receiver | Windows PC running pytest |
| Data link | One direct Ethernet cable, Pi 192.168.2.1 → PC 192.168.2.10, UDP port 42900 |
| Control link | SSH from PC to Pi, key login |
| Note | ARINC 429 words are encoded in software; the physical layer is Ethernet, not a 429 bus |

**Pre-conditions:**
- Pi on and reachable over SSH, sender code up to date (copy it over if `git pull` can't run on the Pi).
- Firewall rule allows UDP 42900 from the Pi.
- Pi allows `ip link` without a password, which makes the automated cable pull work.
- Replay only: `bench_data/healthy.csv` exists, or the test is skipped (NOT RUN).

**How to run (PowerShell, from the repo folder):**

Live (all 7 tests, fresh capture):
```
python -m pytest tests/test_bench_link.py --live -v --pi taylor@192.168.2.1 --data-host 192.168.2.10
```
Replay (this test only):
```
python -m pytest "tests/test_bench_link.py::test_l1_words_on_the_wire_decode_per_icd" -v
```
Expected output: `1 passed`. (A single test is a partial run: its report goes to `reports/dev/`, not for record.)

**Part 1: Capture (live mode only):** steps C1–C15 in [Part 1](#part-1-capture-live-mode-only-shared-by-all-tcs). This test uses `healthy.csv` and, when present, the monitor's decode error counts (C8a).

**Part 2: Test steps (same in both modes):**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Get the healthy recording | `rows, meta = capture(bench, "healthy")` | Recording loaded (skip if missing) | 224 |
| 2 | Build the label list and the label number → name lookup | `labels = label_defs(cfg)` / `lookup = label_lookup(labels)` | pitch 324, roll 325 (octal) | 225–226 |
| 3 | List words whose label is not in the ICD | `bad_label = [w for _, w in rows if label_of(w) not in lookup]` | List made | 227 |
| 4 | Decode every word with a known label | `decoded = [decode_bnr(w, labels[lookup[label_of(w)]]) for _, w in rows if ...]` | Decoded list | 228 |
| 5 | Work out the expected pitch: true pitch plus channel A's bias (`sensors.bias_deg[0]`) | `expect = TRUE_PITCH + cfg["sensors"]["bias_deg"][0]` | -2.0 + 1.0 = -1.0° | 229 |
| 6 | Pick out the pitch values | `pitch = [d.value for ... if lookup[label_of(w)] == "pitch"]` | Pitch list | 230–231 |
| 7 | Save word count, sender address, mean pitch | `record_property("words", len(rows))` ... | Saved | 232–234 |
| 8 | Check labels | `assert not bad_label` | No word has a label outside the ICD | 235 |
| 9 | Check parity | `assert all(d.parity_ok for d in decoded)` | Every word has good (odd) parity | 236 |
| 10 | Check SDI | `assert all(d.sdi == 1 for d in decoded)` | Every word has SDI 1 (channel A) | 237 |
| 11 | Check SSM | `assert all(d.ssm == SSM.NORMAL for d in decoded)` | Every word has SSM Normal | 238 |
| 12 | Check the mean pitch | `assert abs(np.mean(pitch) - expect) < 0.05` | Mean pitch between -1.05° and -0.95° (0.05° limit is in the test file) | 239 |
| 13 | *(live results only, when present)* Get the live results from the same run | `live = live_results(bench)` | Present only with a matching `live_monitor.json` | 240 |
| 14 | *(live results only, when present)* Save the total live decode errors | `record_property("live_decode_errors", sum(live["decode_errors"].values()))` | Saved | 242 |
| 15 | *(live results only, when present)* Check the live checks found no decode errors | `assert not any(live["decode_errors"].values())` | All four counts are 0: label not in ICD, parity, SDI not 1, SSM not Normal | 243 |

**Pass criteria:** every step gives its expected result. Each check is an `assert`; if any one fails, the test fails.

**Last result (run for record, commit d716c1f):** PASS, on `bench_data/healthy.csv` (recorded 2026-10-19T16:12:43 UTC, Oct 19 morning Pacific) and the live results from the same run. 1438 words, sender 192.168.2.1, mean pitch -0.999°. Live decode errors 0.

---

## TC-L1-B01: Word rate and timing on the real link

| Field | Value |
| --- | --- |
| Requirement | L1: Channel A sent from a separate computer over a real Ethernet link shall decode per the ICD, arrive at the nominal label rate (mean interval within 2 %) without gaps long enough to trip the stale check, and a link loss shall be flagged stale within 3 intervals and recover automatically. |
| Level | Bench (hardware in the loop) |
| Test file | `tests/test_bench_link.py` |
| Test function | `test_l1_rate_and_jitter_on_real_link` (lines 247–265) |

**Purpose:** show that pitch words arrive at 50 Hz on average and that no healthy gap is long enough to trip the 60 ms stale check.

**Equipment:**

| Item | What |
|---|---|
| Sender | Raspberry Pi 4 "dronepi" running `tools/pi_channel_a.py` |
| Receiver | Windows PC running pytest |
| Data link | One direct Ethernet cable, Pi 192.168.2.1 → PC 192.168.2.10, UDP port 42900 |
| Control link | SSH from PC to Pi, key login |
| Note | ARINC 429 words are encoded in software; the physical layer is Ethernet, not a 429 bus |

**Pre-conditions:**
- Pi on and reachable over SSH, sender code up to date.
- Firewall rule allows UDP 42900 from the Pi.
- Pi allows `ip link` without a password, which makes the automated cable pull work.
- Replay only: `bench_data/healthy.csv` exists, or the test is skipped (NOT RUN).

**How to run (PowerShell, from the repo folder):**

Live (all 7 tests, fresh capture):
```
python -m pytest tests/test_bench_link.py --live -v --pi taylor@192.168.2.1 --data-host 192.168.2.10
```
Replay (this test only):
```
python -m pytest "tests/test_bench_link.py::test_l1_rate_and_jitter_on_real_link" -v
```
Expected output: `1 passed`. (Partial run: report goes to `reports/dev/`, not for record.)

**Part 1: Capture (live mode only):** steps C1–C15 in [Part 1](#part-1-capture-live-mode-only-shared-by-all-tcs). This test uses `healthy.csv` and, when present, how late the monitor's own checks ran (C8b).

**Part 2: Test steps (same in both modes):**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Get the healthy recording | `rows, _ = capture(bench, "healthy")` | Recording loaded (skip if missing) | 249 |
| 2 | Get the pitch label | `ld = labels["pitch"]` | 50 Hz | 250–251 |
| 3 | Time between each pair of pitch words | `dt = np.diff(pitch_times(rows, labels))` | Interval list (helper `pitch_times`, lines 159–161: arrival times of words with the pitch label) | 252 |
| 4 | Nominal interval and stale limit | `nominal = 1.0 / ld.rate_hz` / `stale_limit = cfg["icd"]["stale_intervals"] / ld.rate_hz` | 20 ms / 60 ms | 253–254 |
| 5 | How far each interval is from 20 ms | `jitter = np.abs(dt - nominal)` | Jitter list | 255 |
| 6 | Save interval count, mean, 99th percentile jitter, longest interval, stale limit | `record_property("intervals", len(dt))` ... | Saved (jitter is recorded, not checked) | 256–260 |
| 7 | Check the mean rate (limit from L1, 2 % in the test file) | `assert abs(dt.mean() - nominal) / nominal <= 0.02` | Mean interval between 19.6 and 20.4 ms | 261 |
| 8 | Check the longest gap | `assert dt.max() < stale_limit` | Longest interval under 60 ms (`icd.stale_intervals` 3 / `rate_hz` 50) | 262 |
| 9 | *(live results only, when present)* Get the live results from the same run | `live = live_results(bench)` | Present only with a matching `live_monitor.json` | 263 |
| 10 | *(live results only, when present)* Save the longest gap between the monitor's own checks (the PC is not real-time, so it is measured) | `record_property("live_max_check_gap_ms", live["max_check_gap_ms"])` | Saved (recorded only, no limit checked here) | 265 |

**Pass criteria:** every step gives its expected result. Each check is an `assert`; if any one fails, the test fails.

**Last result (run for record, commit d716c1f):** PASS, on `bench_data/healthy.csv` (recorded 2026-10-19T16:12:43 UTC, Oct 19 morning Pacific) and the live results from the same run. 718 intervals, mean 20.0 ms, 99th percentile jitter 9.52 ms, longest interval 33.75 ms, stale limit 60.0 ms. Longest gap between live checks 20.61 ms.

Note on jitter (open finding): across all 15 live runs (Test Sets 1-4: the 14 run reports in `bench_runs/` plus the run for record), 99th percentile jitter ranged 2.51–14.64 ms and the worst gap 23.27–42.68 ms, always under the 60 ms stale limit, with zero false stale. An A/B with the live monitor off (Test Set 3, 3 runs, using a temporary switch that is not in the code) gave 4.9–8.15 ms. So the rise in Test Set 2 is mostly the bench setup that night, with a smaller effect from the monitor. This test only checks the mean rate and the worst gap, not jitter. Next steps: timestamp words in their own thread, a real-time target, a repeat on a quiet PC, a jitter requirement, and soak runs.

---

## TC-L1-B02: No false stale on a healthy link

| Field | Value |
| --- | --- |
| Requirements | L1 (above). R3: The receiver shall declare a label stale if not updated within 3 nominal transmit intervals. |
| Level | Bench (hardware in the loop) |
| Test file | `tests/test_bench_link.py` |
| Test function | `test_l1_no_false_stale_on_healthy_link` (lines 268–280), helper `receiver_trace` (lines 164–178) |

**Purpose:** show that on a healthy link the receiver never calls pitch invalid, so real-world timing jitter does not cause a false stale. The replay part checks `healthy.csv`; the live part checks the whole live run except the link drop itself.

**Equipment:**

| Item | What |
|---|---|
| Sender | Raspberry Pi 4 "dronepi" running `tools/pi_channel_a.py` |
| Receiver | Windows PC running pytest |
| Data link | One direct Ethernet cable, Pi 192.168.2.1 → PC 192.168.2.10, UDP port 42900 |
| Control link | SSH from PC to Pi, key login |
| Note | ARINC 429 words are encoded in software; the physical layer is Ethernet, not a 429 bus |

**Pre-conditions:**
- Pi on and reachable over SSH, sender code up to date.
- Firewall rule allows UDP 42900 from the Pi.
- Pi allows `ip link` without a password, which makes the automated cable pull work.
- Replay only: `bench_data/healthy.csv` exists, or the test is skipped (NOT RUN).

**How to run (PowerShell, from the repo folder):**

Live (all 7 tests, fresh capture):
```
python -m pytest tests/test_bench_link.py --live -v --pi taylor@192.168.2.1 --data-host 192.168.2.10
```
Replay (this test only):
```
python -m pytest "tests/test_bench_link.py::test_l1_no_false_stale_on_healthy_link" -v
```
Expected output: `1 passed`. (Partial run: report goes to `reports/dev/`, not for record.)

**Part 1: Capture (live mode only):** steps C1–C15 in [Part 1](#part-1-capture-live-mode-only-shared-by-all-tcs). This test uses `healthy.csv` and, when present, the monitor's valid/invalid changes over the whole run (C8b).

**Part 2: Test steps (same in both modes):**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Get the healthy recording | `rows, _ = capture(bench, "healthy")` | Recording loaded (skip if missing) | 271 |
| 2 | Run the SIL receiver over the recording, checking pitch validity every 1 ms | `ts, valid = receiver_trace(rows, cfg, labels, rows[-1][0])` | Validity at every 1 ms sample | 272–273 |
| 2a | *(inside the helper)* A fresh receiver (stale after 3 intervals) gets each word at its recorded arrival time; at each 1 ms sample, pitch validity is read | `rx.receive(name, rows[i][1], rows[i][0])` / `valid[k] = rx.read("pitch", t)[0]` | Invalid only if stale (over 60 ms since last good word), SSM not Normal, or out of range | test file 164–178; sil/receiver.py 24–32, 44–62 |
| 3 | Skip the first two samples (0 and 1 ms, before the first word is in) | `after_first = ts > 0.001` | Mask made | 274 |
| 4 | Save the number of invalid samples | `record_property("invalid_samples", int((~valid[after_first]).sum()))` | Saved | 275 |
| 5 | Check every sample is valid | `assert valid[after_first].all()` | Pitch valid at every sample after 1 ms | 276 |
| 6 | *(live results only, when present)* Get the live results from the same run | `live = live_results(bench)` | Present only with a matching `live_monitor.json` | 277 |
| 7 | *(live results only, when present)* Save the live false-stale count: times the live check went invalid after it first went valid, anywhere in the run except inside the link drop (from the last word before the drop to the first word back) | `record_property("live_false_stale", live["false_stale_outside_drop"])` | Saved (counted in sil/bench.py 113–119) | 279 |
| 8 | *(live results only, when present)* Check the live check never went stale outside the link drop | `assert live["false_stale_outside_drop"] == 0` | 0 | 280 |

**Pass criteria:** every step gives its expected result. Each check is an `assert`; if any one fails, the test fails.

**Last result (run for record, commit d716c1f):** PASS, on `bench_data/healthy.csv` (recorded 2026-10-19T16:12:43 UTC, Oct 19 morning Pacific) and the live results from the same run. 0 invalid samples; live false stale 0.

Loopback check (2026-10-18, local sender standing in for the Pi, not a Pi result): a 150 ms glitch after recovery made this test fail at step 8.

---

## TC-L1-B03: Link loss flagged stale, then recovers

| Field | Value |
| --- | --- |
| Requirements | L1 (above). R3: The receiver shall declare a label stale if not updated within 3 nominal transmit intervals. |
| Level | Bench (hardware in the loop) |
| Test file | `tests/test_bench_link.py` |
| Test function | `test_l1_cable_pull_flagged_stale_and_recovers` (lines 284–315), helper `replay_link_drop` (lines 181–211) |

**Purpose:** show that when the Pi's Ethernet link goes down, the receiver flags pitch stale within 3 intervals, and goes valid again by itself as soon as words come back. When live results exist, show the live check did the same at real time.

**Equipment:**

| Item | What |
|---|---|
| Sender | Raspberry Pi 4 "dronepi" running `tools/pi_channel_a.py` |
| Receiver | Windows PC running pytest |
| Data link | One direct Ethernet cable, Pi 192.168.2.1 → PC 192.168.2.10, UDP port 42900 |
| Control link | SSH from PC to Pi, key login |
| Note | ARINC 429 words are encoded in software; the physical layer is Ethernet, not a 429 bus |

**Pre-conditions:**
- Pi on and reachable over SSH, sender code up to date.
- Firewall rule allows UDP 42900 from the Pi.
- Pi allows `ip link` without a password, which makes the automated cable pull work.
- Replay only: `bench_data/cable_pull.csv` exists (or the test is skipped, NOT RUN) and has a gap of at least 0.5 s (or skipped). If the recording ends with no words for 0.5 s or more, the test fails.

**How to run (PowerShell, from the repo folder):**

Live (all 7 tests, fresh capture):
```
python -m pytest tests/test_bench_link.py --live -v --pi taylor@192.168.2.1 --data-host 192.168.2.10
```
Replay (this test only):
```
python -m pytest "tests/test_bench_link.py::test_l1_cable_pull_flagged_stale_and_recovers" -v
```
Expected output: `1 passed`. (Partial run: report goes to `reports/dev/`, not for record.)

**Part 1: Capture (live mode only):** steps C1–C15 in [Part 1](#part-1-capture-live-mode-only-shared-by-all-tcs). This test uses `cable_pull.csv` (with the link drop from C8d) and, when present, the live link-drop result (C8b, C14).

**Part 2: Test steps (same in both modes):**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Get the cable-pull recording and its header | `rows, meta = capture(bench, "cable_pull")` | Recording loaded (skip if missing) | 287 |
| 2 | Replay the link drop through the receiver | `d = replay_link_drop(cfg, rows, meta)` | Flag and recovery times worked out | 288 |
| 2a | Save what the replay saw, for the bench figure: the interval between pitch words, and the receiver's valid/invalid trace each 1 ms, with the drop times and the flag and recovery times | `plot_data.save("bench_pitch_intervals", ...)` / `plot_data.save("bench_receiver_valid", ...)` | `reports/data/bench_pitch_intervals.csv`, `bench_receiver_valid.csv` | 289–298 |
| 2a | *(inside the helper)* Replay end: `recorded_s` from the header if there is one, else the last word | `t_end = float((meta or {}).get("recorded_s", rows[-1][0]))` | 32.0 s for this recording (`recorded_s` in the header) | 186–187 |
| 2b | *(inside the helper)* Check the link came back: fail if there are no pitch words in the last 0.5 s | `pytest.fail(f"no words after {pt[-1]:.1f} s of a {t_end:g} s recording: " "the link never came back")` | Words at the end, so carry on | 188–190 |
| 2c | *(inside the helper)* Find the longest gap between pitch words; skip if it is under 0.5 s | `if gaps[i] < PULL_MIN_GAP_S: pytest.skip(...)` | Gap found: last word before it (`t_last`), first word after (`t_back`) | 191–195 |
| 2d | *(inside the helper)* Run the SIL receiver from 0 to the replay end, 1 ms samples | `ts, valid = receiver_trace(rows, cfg, labels, t_end)` | Validity at every 1 ms sample (see TC-L1-B02 step 2a) | 196 |
| 2e | *(inside the helper)* Flag time = first invalid sample after `t_last`, minus `t_last`. Recovery time = first valid sample at or after `t_back`, minus `t_back`. Also counts invalid stretches outside the drop window, after the first valid sample (used by TC-L2-B01). Stale limit = 3 / 50 Hz | `"flag_s": ...` / `"recover_s": ...` / `"false_stale_outside_drop": starts` / `"stale_limit_s": ...` | `stale_limit_s` = 0.060 s | 197–211 |
| 3 | Save how long the link was out, the flag time and the recovery time | `record_property("cable_out_s", round(d["cable_out_s"], 2))` ... | Saved | 299–302 |
| 4 | Check the receiver flagged the loss at all | `assert d["flag_s"] is not None` | A flag time exists | 303 |
| 5 | Check the flag came in time (stale limit plus 2 ms, the 2 ms is in the test file) | `assert d["flag_s"] <= d["stale_limit_s"] + 0.002` | Flagged within 62 ms of the last word | 304 |
| 6 | Check recovery | `assert d["recover_s"] is not None and d["recover_s"] <= 0.002` | Valid again within 2 ms of the first word back | 305 |
| 7 | *(live results only, when present)* Get the live results from the same run | `live = live_results(bench)` | Present only with a matching `live_monitor.json` | 306 |
| 8 | *(live results only, when present)* Tolerance for live times (`bench_link.live_vs_replay_tol_ms`) | `tol_s = cfg["bench_link"]["live_vs_replay_tol_ms"] / 1000` | 0.005 s | 308 |
| 9 | *(live results only, when present)* Check the live check saw the drop and flagged it | `assert drop and drop["flagged_after_ms"] is not None` | Live link-drop result exists with a flag time | 309–310 |
| 10 | *(live results only, when present)* Save the live flag and recovery times | `record_property("live_flagged_after_ms", drop["flagged_after_ms"])` ... | Saved | 311–312 |
| 11 | *(live results only, when present)* Check the live flag came in time | `assert drop["flagged_after_ms"] / 1000 <= d["stale_limit_s"] + tol_s` | Live flag within 60 + 5 = 65 ms of the last word | 313 |
| 12 | *(live results only, when present)* Check live recovery | `assert drop["recovered_after_reconnect_ms"] is not None` / `assert drop["recovered_after_reconnect_ms"] / 1000 <= tol_s` | Live check valid again within 5 ms of the first word back | 314–315 |

**Pass criteria:** every step gives its expected result. Each check is an `assert` (or `pytest.fail` in step 2b); if any one fails, the test fails.

**Last result (run for record, commit d716c1f):** PASS, on `bench_data/cable_pull.csv` (recorded 2026-10-19T16:12:43 UTC, Oct 19 morning Pacific) and the live results from the same run. Link out 8.82 s. Replay: flagged stale 60.6 ms after the last word, valid again 0.5 ms after the first word back. Live: flagged 61.1 ms, valid again 0.1 ms.

Note: the port was down for 5 s, but words were missing for 8.82 s. The extra time is most likely the Pi's Ethernet link and network coming back up after `ip link set eth0 up`; the test does not check it. Loopback check (2026-10-18, not a Pi result): when the link never recovered, this test failed at step 2b with "the link never came back".

---

## TC-L1-B04: Closed loop with the real channel A

| Field | Value |
| --- | --- |
| Requirements | L1 (above). R5: With three valid sources, the voter shall output the middle value. |
| Level | Bench (hardware in the loop); also marked `system` (closed loop) |
| Test file | `tests/test_bench_link.py` |
| Test function | `test_l1_closed_loop_with_real_channel_a` (lines 319–332), helper `replay` (lines 214–217) |

**Purpose:** show that with the real channel A words in place of the simulated channel A, the whole loop (receivers, voter, command law, actuator) stays in triplex and the voted pitch stays close to the true pitch.

**Equipment:**

| Item | What |
|---|---|
| Sender | Raspberry Pi 4 "dronepi" running `tools/pi_channel_a.py` (channel A only; B and C stay simulated) |
| Receiver | Windows PC running pytest |
| Data link | One direct Ethernet cable, Pi 192.168.2.1 → PC 192.168.2.10, UDP port 42900 |
| Control link | SSH from PC to Pi, key login |
| Note | ARINC 429 words are encoded in software; the physical layer is Ethernet, not a 429 bus |

**Pre-conditions:**
- Pi on and reachable over SSH, sender code up to date.
- Firewall rule allows UDP 42900 from the Pi.
- Pi allows `ip link` without a password, which makes the automated cable pull work.
- Replay only: `bench_data/healthy.csv` exists, or the test is skipped (NOT RUN).

**How to run (PowerShell, from the repo folder):**

Live (all 7 tests, fresh capture):
```
python -m pytest tests/test_bench_link.py --live -v --pi taylor@192.168.2.1 --data-host 192.168.2.10
```
Replay (this test only):
```
python -m pytest "tests/test_bench_link.py::test_l1_closed_loop_with_real_channel_a" -v
```
Expected output: `1 passed`. (Partial run: report goes to `reports/dev/`, not for record.)

**Part 1: Capture (live mode only):** steps C1–C15 in [Part 1](#part-1-capture-live-mode-only-shared-by-all-tcs). This test uses `healthy.csv`. It does not use the live monitor results, so it has no live-only steps.

**Part 2: Test steps (same in both modes):**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Get the healthy recording | `rows, _ = capture(bench, "healthy")` | Recording loaded (skip if missing) | 323 |
| 2 | Length of the replay: the recording, capped at 30 s | `dur = min(rows[-1][0], REPLAY_MAX_S)` | About 14.4 s | 324 |
| 3 | Run the whole system with the recording as channel A, true pitch -2.0° | `run = replay(cfg, rows, dur)` | Run completes | 325 |
| 3a | *(inside the run)* Channel A is replaced by the recording; B and C are simulated (bias 0.0° and -1.0°, noise 0.02°) | `chans[i] = src` | A = real words, B and C = simulated | sil/sim.py 94–101 |
| 3b | *(inside the run)* Every 1 ms step, the recording hands over every word whose recorded arrival time has come, with the same values, timing and gaps | `ReplayChannel.transmit(t, truth)` | Words reach receiver A as they arrived | sil/link.py 84–92; sil/sim.py 133–135 |
| 3c | *(inside the run)* Every 20 ms frame, the voter takes the three pitch readings; with three valid it outputs the middle one (B, about -2.0°); the command law and actuator follow | `voters["pitch"].update(...)` / `law.update(cur_v, v["frame_s"])` | Mode TRIPLEX | sil/sim.py 136–146; sil/voter.py 56–69 |
| 4 | Ignore the first 0.2 s (start-up), then work out the voted pitch error | `settled = run.t > 0.2` / `err = np.abs(run.voted[settled] - TRUE_PITCH)` | Error list | 326–327 |
| 5 | Save replay length and largest error | `record_property("replayed_s", round(dur, 1))` ... | Saved | 328–329 |
| 6 | Check no channel was latched failed | `assert not run.failed` | No failed channels | 330 |
| 7 | Check the voter stayed in triplex | `assert all(m == Mode.TRIPLEX for m, s in zip(run.mode, settled) if s)` | TRIPLEX at every step after 0.2 s | 331 |
| 8 | Check the voted pitch error (limit from `voter.tolerance_deg` plus 0.35° in the test file) | `assert err.max() <= cfg["voter"]["tolerance_deg"] + 0.35` | Largest error ≤ 1.0 + 0.35 = 1.35° | 332 |

**Pass criteria:** every step gives its expected result. Each check is an `assert`; if any one fails, the test fails.

**Last result (run for record, commit d716c1f):** PASS, on `bench_data/healthy.csv` (recorded 2026-10-19T16:12:43 UTC, Oct 19 morning Pacific). Replayed 14.4 s, largest voted error 0.066°.

---

## TC-L1-B05: Closed loop through the link loss

| Field | Value |
| --- | --- |
| Requirements | L1 (above). R8: After one channel failure, the voter shall continue on the remaining two and annunciate. R10: The actuator command shall never exceed the position or rate limits, whatever the input. |
| Level | Bench (hardware in the loop); also marked `system` (closed loop) |
| Test file | `tests/test_bench_link.py` |
| Test function | `test_l1_closed_loop_cable_pull` (lines 335–360), helpers `replay_link_drop` (lines 181–211) and `replay` (lines 214–217) |

**Purpose:** show that when the real channel A link drops, the voter goes to dual on B and C, annunciates, keeps the command inside limits, and goes back to triplex by itself when the link returns, without latching channel A failed.

**Equipment:**

| Item | What |
|---|---|
| Sender | Raspberry Pi 4 "dronepi" running `tools/pi_channel_a.py` (channel A only; B and C stay simulated) |
| Receiver | Windows PC running pytest |
| Data link | One direct Ethernet cable, Pi 192.168.2.1 → PC 192.168.2.10, UDP port 42900 |
| Control link | SSH from PC to Pi, key login |
| Note | ARINC 429 words are encoded in software; the physical layer is Ethernet, not a 429 bus |

**Pre-conditions:**
- Pi on and reachable over SSH, sender code up to date.
- Firewall rule allows UDP 42900 from the Pi.
- Pi allows `ip link` without a password, which makes the automated cable pull work.
- Replay only: `bench_data/cable_pull.csv` exists (or the test is skipped, NOT RUN) and has a gap of at least 0.5 s (or skipped). If the recording ends with no words for 0.5 s or more, the test fails.

**How to run (PowerShell, from the repo folder):**

Live (all 7 tests, fresh capture):
```
python -m pytest tests/test_bench_link.py --live -v --pi taylor@192.168.2.1 --data-host 192.168.2.10
```
Replay (this test only):
```
python -m pytest "tests/test_bench_link.py::test_l1_closed_loop_cable_pull" -v
```
Expected output: `1 passed`. (Partial run: report goes to `reports/dev/`, not for record.)

**Part 1: Capture (live mode only):** steps C1–C15 in [Part 1](#part-1-capture-live-mode-only-shared-by-all-tcs). This test uses `cable_pull.csv` (with the link drop from C8d). It does not use the live monitor results, so it has no live-only steps.

**Part 2: Test steps (same in both modes):**

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | Get the cable-pull recording and its header | `rows, meta = capture(bench, "cable_pull")` | Recording loaded (skip if missing) | 340 |
| 2 | Check the recording: fails if the link never came back, skips if there is no drop (result not otherwise used here) | `replay_link_drop(cfg, rows, meta)` | Carries on (see TC-L1-B03 steps 2a–2c) | 341 |
| 3 | Run the whole system over the full recording (no 30 s cap), true pitch -2.0° | `dur = rows[-1][0]` / `run = replay(cfg, rows, dur)` | Run of about 32.0 s completes | 342–343 |
| 3a | Save the voter's channels in use over time (3 = TRIPLEX, 2 = DUAL) for the bench figure | `plot_data.save("bench_voter_channels", {"t_s": run.t, "channels_in_use": [...]}, ...)` | `reports/data/bench_voter_channels.csv` | 344–347 |
| 3a | *(inside the run)* Channel A is the recording; B and C are simulated | `chans[i] = src` | As TC-L1-B04 step 3a | sil/sim.py 94–101 |
| 3b | *(inside the run)* During the gap no words come; receiver A goes stale 60 ms after the last word | `reasons()`: `t - self.last_rx_t > stale_intervals / ld.rate_hz + 1e-9` | Channel A invalid | sil/receiver.py 26–27 |
| 3c | *(inside the run)* The voter only counts valid channels, so A drops out without a miscompare count; with two left it averages B and C and annunciates `DEGRADED_DUAL` | `avail = [i for i in range(self.n) if inputs[i][0] and i not in self.failed]` / `ann.append(f"DEGRADED_{mode.value}")` | Mode DUAL, A not latched failed | sil/voter.py 53, 70–72, 82–83 |
| 3d | *(inside the run)* When words come back, receiver A is valid again and the voter goes back to the middle of three | `voters["pitch"].update(...)` | Mode TRIPLEX | sil/voter.py 68–69 |
| 3e | *(inside the run)* The command law clamps the command to the position limit | `raw = max(-self.pos_limit_mm, min(self.pos_limit_mm, raw))` | Command within ±22.0 mm | sil/command_law.py 28 |
| 4 | Modes seen after 0.2 s; save them, the final mode and the actuator travel | `modes = {m for m, s in zip(run.mode, settled) if s}` / `record_property(...)` | Saved | 348–353 |
| 5 | Check the voter dropped to dual | `assert Mode.DUAL in modes` | DUAL seen | 354 |
| 6 | Check it came back | `assert run.mode[-1] == Mode.TRIPLEX` | Last mode TRIPLEX | 355 |
| 7 | Check A was excluded, not latched failed | `assert not run.failed` | No failed channels | 356 |
| 8 | Check the annunciation | `assert "DEGRADED_DUAL" in run.annunciations` | `DEGRADED_DUAL` raised | 357 |
| 9 | Check the command position limit (`command_law.pos_limit_mm`) | `assert np.max(np.abs(run.cmd)) <= law["pos_limit_mm"] + 1e-9` | Largest command ≤ 22.0 mm | 358 |
| 10 | Check the voted pitch error (limit from `voter.tolerance_deg` plus 0.35° in the test file) | `err = np.abs(run.voted[settled] - TRUE_PITCH)` / `assert err.max() <= cfg["voter"]["tolerance_deg"] + 0.35` | Largest error ≤ 1.35° | 359–360 |

**Pass criteria:** every step gives its expected result. Each check is an `assert` (or `pytest.fail` inside step 2); if any one fails, the test fails.

**Last result (run for record, commit d716c1f):** PASS, on `bench_data/cable_pull.csv` (recorded 2026-10-19T16:12:43 UTC, Oct 19 morning Pacific). Modes seen DUAL and TRIPLEX, ended in TRIPLEX, actuator travel 2.342 mm.

Note: R10 covers position and rate limits; this test checks only the position limit. Loopback check (2026-10-18, not a Pi result): when the link never recovered, this test failed at step 2 with "the link never came back".

---

## TC-L2-B01: Live checks agree with the replay

| Field | Value |
| --- | --- |
| Requirement | L2: The bench link checks shall also run live, during the capture, and the live results shall agree with the replay of the same recording (same words, fingerprint of the saved recording; no decode errors; no false stale anywhere outside the link drop; stale flag and recovery times within 5 ms). |
| Level | Bench (hardware in the loop) |
| Test file | `tests/test_bench_link.py` |
| Test function | `test_l2_live_vs_replay_agree` (lines 364–416), helper `replay_link_drop` (lines 181–211) |

**Purpose:** show that the checks made live, while the words arrived, give the same answers as the replay of the same recording: the saved recording is exactly what the live checks saw (word count and fingerprint), no decode errors, no false stale outside the link drop, and stale flag and recovery times within 5 ms.

**Equipment:**

| Item | What |
|---|---|
| Sender | Raspberry Pi 4 "dronepi" running `tools/pi_channel_a.py` |
| Receiver | Windows PC running pytest, with the live monitor (`LiveMonitor`, sil/bench.py) |
| Data link | One direct Ethernet cable, Pi 192.168.2.1 → PC 192.168.2.10, UDP port 42900 |
| Control link | SSH from PC to Pi, key login |
| Note | ARINC 429 words are encoded in software; the physical layer is Ethernet, not a 429 bus |

**Pre-conditions:**
- Pi on and reachable over SSH, sender code up to date.
- Firewall rule allows UDP 42900 from the Pi.
- Pi allows `ip link` without a password, which makes the automated cable pull work.
- Replay only: `bench_data/live_monitor.json` exists with the same `recorded_utc` as `cable_pull.csv`, or the test is skipped (NOT RUN). For the current recording it exists.

**How to run (PowerShell, from the repo folder):**

Live (all 7 tests, fresh capture):
```
python -m pytest tests/test_bench_link.py --live -v --pi taylor@192.168.2.1 --data-host 192.168.2.10
```
Replay (this test only):
```
python -m pytest "tests/test_bench_link.py::test_l2_live_vs_replay_agree" -v
```
Expected output: `1 passed` (`1 skipped` if there are no live results from the same run). (Partial run: report goes to `reports/dev/`, not for record.)

**Part 1: Capture (live mode only):** steps C1–C15 in [Part 1](#part-1-capture-live-mode-only-shared-by-all-tcs). This test needs both the recordings (C13) and the live monitor's results from the same run (C8a, C8b, C14).

**Part 2: Test steps (same in both modes):**

If there are no live results, the test stops at step 2 and is skipped. Every step after that only runs when live results are present.

| Step | Action | Python command | Expected result | Line |
|---|---|---|---|---|
| 1 | *(live results only, when present)* Get the live results from the same run | `live = live_results(bench)` | Present only with a matching `live_monitor.json` | 367 |
| 2 | Skip if there are none | `pytest.skip("no live monitor results for this recording yet: run with --live")` | Skipped (NOT RUN) when there are no live results | 368–369 |
| 3 | Get the cable-pull recording, its header and the tolerance (`bench_link.live_vs_replay_tol_ms`) | `rows, meta = capture(bench, "cable_pull")` / `tol_ms = cfg["bench_link"]["live_vs_replay_tol_ms"]` | 5.0 ms | 370–373 |
| 4 | Replay side: fingerprint the saved recording, each word written the same way the live monitor wrote it | `replay_sha = hashlib.sha256("".join(LiveMonitor.row_text(t, w) for t, w in rows).encode()).hexdigest()` | SHA-256 made | 376 (`row_text`: sil/bench.py 58–61) |
| 5 | Replay side: count decode errors in every word of the recording (label not in ICD, bad parity, SDI not 1, SSM not Normal) | `replay_errors += (not dw.parity_ok) + (dw.sdi != 1) + (dw.ssm != SSM.NORMAL)` | Count made | 379–386 |
| 6 | Replay side: replay the link drop over the whole cable-pull recording: flag and recovery times, and false stale outside the drop | `d = replay_link_drop(cfg, rows, meta)` / `replay_false_stale = d["false_stale_outside_drop"]` | As TC-L1-B03 steps 2a–2e (fails if the link never came back) | 387–388 |
| 7 | Check the replay saw a complete link drop (flag and recovery both found) | `assert d["flag_s"] is not None and d["recover_s"] is not None` | `True`, otherwise fails with "replay saw no complete link drop" | 389 |
| 8 | Replay side: flag and recovery times in ms | `replay_flag_ms = d["flag_s"] * 1000` / `replay_recover_ms = d["recover_s"] * 1000` | Times made | 390–391 |
| 9 | *(live results only, when present)* Check the live checks saw a complete link drop | `assert drop and drop["flagged_after_ms"] is not None and drop["recovered_after_reconnect_ms"] is not None` | `True`, otherwise fails with "live checks saw no complete link drop" | 394–396 |
| 10 | *(live results only, when present)* Live side: total decode errors, and how far the live flag and recovery times are from the replay ones | `diff_flag = abs(drop["flagged_after_ms"] - replay_flag_ms)` / `diff_recover = abs(...)` | Differences made | 397–399 |
| 11 | *(live results only, when present)* Save live vs replay words, flag and recovery times, the differences, the longest gap between live checks, false stale live vs replay, and the tolerance | `record_property("words_live_vs_replay", f"{live['words']} vs {len(rows)}")` ... `record_property("false_stale_live_vs_replay", ...)` | Saved | 401–409 |
| 12 | *(live results only, when present)* Check same number of words | `assert live["words"] == len(rows)` | Live word count = recording word count | 411 |
| 13 | *(live results only, when present)* Check the fingerprints match | `assert live["words_sha256"] == replay_sha` | Same SHA-256, otherwise fails with "the saved recording is not what the live checks saw" | 412 |
| 14 | *(live results only, when present)* Check no decode errors on either side | `assert live_errors == 0 and replay_errors == 0` | Both 0 | 413 |
| 15 | *(live results only, when present)* Check no false stale outside the link drop on either side | `assert live["false_stale_outside_drop"] == 0 and replay_false_stale == 0` | Both 0 | 414 |
| 16 | *(live results only, when present)* Check the stale flag times agree | `assert diff_flag <= tol_ms` | Live and replay flag times within 5.0 ms | 415 |
| 17 | *(live results only, when present)* Check the recovery times agree | `assert diff_recover <= tol_ms` | Live and replay recovery times within 5.0 ms | 416 |

**Where the 5 ms comes from** (comment at `bench_link` in `config/sil.yaml`, lines 100–107): replay 1 ms step + live check period 1 ms + Windows scheduling delay (word jitter up to 2.5 ms, measured 2026-10-16) = about 5 ms. Ceiling from the 4:1 rule: 60 ms stale limit / 4 = 15 ms. So 5 ms covers the budget and stays well under the ceiling.

**Pass criteria:** every step gives its expected result. Each check is an `assert` (or `pytest.fail` inside step 6); if any one fails, the test fails.

**Last result (run for record, commit d716c1f):** PASS, on `bench_data/cable_pull.csv` (recorded 2026-10-19T16:12:43 UTC, Oct 19 morning Pacific) and `bench_data/live_monitor.json` from the same run. Words 2321 live vs 2321 replay (fingerprints match). Stale flag 61.1 ms live vs 60.6 ms replay, 0.5 ms apart. Recovery 0.1 ms live vs 0.5 ms replay, 0.4 ms apart. False stale 0 vs 0. Longest gap between live checks 20.61 ms. Tolerance 5.0 ms.

**Loopback check (not a Pi result, not for record):** on 2026-10-18, a local sender on the PC stood in for the Pi. It is not the Pi and not the real cable, so it does not count as an L2 result. Live flagged the drop at 60.1 ms and replay at 60.9 ms, 0.8 ms apart (inside 5 ms). With the old 50 ms live check period, the same check failed: 39.7 ms apart. That is why the live check period is now 1 ms (`bench_link.live_check_period_s` = 0.001).

**Negative checks (loopback, 2026-10-18, local sender standing in for the Pi, not a Pi result):**

| Case | What was done | Result |
|---|---|---|
| Normal | Link drop and recovery as planned | All 7 tests pass |
| Glitch after recovery | A 150 ms gap in words after the link came back | TC-L1-B02 and this test FAIL (false stale outside the drop) |
| Link never recovers | No words after the drop to the end of the recording | TC-L1-B03, TC-L1-B05 and this test FAIL with "the link never came back" |
| Recording changed | One word changed in the saved recording after the run | This test FAILS on the fingerprint (step 13) |
