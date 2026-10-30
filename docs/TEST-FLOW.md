# Test flow: unit, system and bench tests

How a test run goes from `pytest` to the traceability matrix, for each of the three test levels. Every test follows the same four steps: **set up, act, check, record**. What changes from level to level is how much of the system runs in "act".

| Level | What runs in "act" | Where the words come from | Example |
| --- | --- | --- | --- |
| **Unit** | One component alone (encoder, receiver, voter, actuator model, command law) | The test makes them by hand | [TC-R1-U01](procedures/part-b-receiver.md#tc-r1-u01-receiver-rejects-a-word-with-bad-parity) |
| **System** | The whole loop: sensors, receiver, voter, command law, actuator, monitor | Simulated sensors | [TC-FM-S01](procedures/part-b-system.md) |
| **Bench** | The same receiver, voter and actuator code, fed by real hardware | A Raspberry Pi over a real Ethernet cable | [TC-L1-B03](procedures/bench-link.md) |

## 1. The common flow (every test)

```mermaid
flowchart TD
    A["python -m pytest<br/>or tools/run_tests.py"] --> B["pytest.ini<br/>finds tests/ and the req marker"]
    B --> C["tests/conftest.py fixtures<br/>cfg = config/sil.yaml (fingerprinted)<br/>load_condition = unloaded and rated"]
    C --> D["Each test function"]
    D --> E["1. Set up<br/>build what it needs from cfg"]
    E --> F["2. Act<br/>unit, system or bench (below)"]
    F --> G["3. Check<br/>assert against limits from cfg"]
    G --> H["4. Record<br/>record_property: measured values<br/>plot_data: what a figure shows"]
    H --> I{"Full run on<br/>committed code?"}
    I -- "yes" --> J["reports/traceability.md<br/>FULL RUN ... record"]
    I -- "no: one file, one test,<br/>-k, -m, stopped early" --> K["reports/dev/traceability.md<br/>PARTIAL RUN, not for record"]
```

The report hook (end of `tests/conftest.py`) groups results by requirement, gives each a verdict (PASS, FAIL, OPEN DEFECT, NOT RUN, NOT TESTED) and shows each requirement's tests by name and level, stamped with the git commit and the config fingerprint. It also writes the plot data the tests saved to `reports/data/`, each file stamped with its test, that test's result, the commit and the config. `tools/make_figures.py` then draws the figures only from those files, so every point on a plot traces to the run for record ([EVIDENCE.md](EVIDENCE.md)).

## 2. Unit test

One component, driven step by step by the test. Example: R1, a word with bad parity is rejected.

```mermaid
flowchart LR
    T["Test<br/>test_r1_bad_parity_rejected"] -->|"good word 5.0 deg"| E1["encode_bnr<br/>sil/arinc429.py"]
    E1 --> R["Receiver.receive<br/>sil/receiver.py"]
    T -->|"30.0 deg, parity flipped"| E2["encode_bnr<br/>corrupt_parity=True"]
    E2 --> R
    R --> Q["Receiver.read<br/>still 5.0, 1 reject"]
    Q --> A["assert"]
```

Only two files run. Timing is exact and made up by the test. It proves the logic is right.

## 3. System test

The whole loop runs inside one call, `run_scenario()` in `sil/sim.py`, ticking every millisecond. The test describes a fault, runs the loop, then checks the results. Example: the fault matrix (9 faults x 3 channels).

```mermaid
flowchart TD
    T["Test<br/>Fault('bad_parity', channel A, from 0.5 s)"] --> S["run_scenario<br/>sil/sim.py, 1 ms ticks"]
    subgraph LOOP["Inside run_scenario, every tick"]
        direction LR
        S1["3 sensor channels<br/>bias, noise, fault<br/>sil/sources.py"] --> S2["ARINC 429 words<br/>encode_bnr"]
        S2 --> S3["3 receivers<br/>parity, SSM, stale, range<br/>sil/receiver.py"]
        S3 -->|"every 20 ms"| S4["Mid-value voter<br/>sil/voter.py"]
        S4 --> S5["Command law<br/>position and rate limits<br/>sil/command_law.py"]
        S5 --> S6["Actuator model<br/>load, backlash, 2 motors<br/>sil/ema.py"]
        S6 --> S7["Jam monitor<br/>sil/actuator_monitor.py"]
    end
    S --> LOOP
    LOOP --> R["Result: truth, voted, mode,<br/>failed channel, command, rod position"]
    R --> A["assert: voted error, mode,<br/>limits held"]
```

Timing is exact but simulated. It proves the whole system stays safe when a part fails.

## 4. Bench test (Raspberry Pi)

Two parts: **capture** (needs the Pi, live mode only) and **check** (needs only the recording, so it runs anywhere). With `--live`, a live monitor also checks every word while it arrives.

```mermaid
flowchart TD
    subgraph CAP["Part 1: capture (pytest --live only)"]
        P1["PC: pytest --live<br/>run_live in tests/test_bench_link.py"] -->|"SSH: check, start sender,<br/>schedule link drop"| P2["Raspberry Pi<br/>tools/pi_channel_a.py"]
        P2 -->|"ARINC 429 words, UDP,<br/>every 20 ms, Ethernet cable"| P3["PC: capture_udp<br/>timestamps each word on arrival"]
        P3 --> P4["LiveMonitor<br/>checks each word now,<br/>re-checks every 1 ms"]
        P2 -.->|"at 15 s: link down 5 s,<br/>then back up"| P3
        P3 --> F1["bench_data/cable_pull.csv<br/>bench_data/healthy.csv"]
        P4 --> F2["bench_data/live_monitor.json<br/>(with a fingerprint of every word)"]
    end
    subgraph CHK["Part 2: check (live run, or replay of the saved files)"]
        C1["Decode per ICD, rate and jitter,<br/>no false stale, cable pull<br/>(receiver replay, 1 ms checks)"]
        C2["Closed loop: recording replayed as<br/>channel A in run_scenario<br/>(voter 3 to 2 to 3, actuator holds)"]
        C3["L2: live vs replay agree<br/>same words, flag and recovery within 5 ms"]
    end
    F1 --> C1
    F1 --> C2
    F1 --> C3
    F2 --> C1
    F2 --> C3
```

Timing is real, with network jitter. It proves the logic still works with messy real timing and a real link loss.

**Why capture and check are separate:** one capture feeds all seven bench tests; anyone (GitHub CI, any laptop) can re-check real Pi data without the Pi; and the recording, with its header, is kept as evidence. A replay alone re-checks old data; the run for record starts with a fresh live run.

**The three levels on one requirement (R3, stale detection):** the unit test checks the logic with perfect timing, the system fault matrix checks the whole loop rides through a dropout, and the bench cable pull checks it on a real link. Each level catches something the one below can't.

## Where to go next

- Test procedures for every test, step by step with the Python line each step runs: [docs/procedures/](procedures/README.md)
- The hardware this grows into: [docs/RIG-OVERVIEW.md](RIG-OVERVIEW.md)
- Running it yourself: [docs/USER-GUIDE.md](USER-GUIDE.md); the Pi: [docs/BENCH-GUIDE.md](BENCH-GUIDE.md)
