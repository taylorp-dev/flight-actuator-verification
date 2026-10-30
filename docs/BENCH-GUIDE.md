# Bench Guide: Channel A on a Real Raspberry Pi

This is the first step off pure simulation: **bus-in-the-loop**. Sensor channel A moves off the laptop and onto a Raspberry Pi, a separate computer. The Pi sends channel A's ARINC 429 words to the laptop over a real Ethernet cable, in real time. Channels B and C stay simulated.

What this adds over the pure SIL:
- **Real timing.** The Pi runs Linux, which isn't real-time, so words don't arrive exactly every 20 ms. The tests measure how far off they are.
- **Real link loss.** The test takes the Pi's Ethernet port down for a few seconds (automatically, or you can pull the cable by hand). The receiver should flag channel A stale (R3), the voter should drop to dual and keep going (R8), and everything should recover on its own.
- **The same code.** The Pi runs the same channel code (`sil/sources.py`) and config (`config/sil.yaml`) as the simulation. The tests run the recording through the same receiver, voter, command law and actuator as every other test.

What this is **not**: a real ARINC 429 bus. The words are ARINC 429 bit-for-bit, but they travel over Ethernet (one word per UDP packet), not 429 wiring. A real 429 bus needs an interface card. That's the next rung.

```
              control: SSH over Wi-Fi (start sender, drop link)
   Laptop  ─────────────────────────────────────────────▶  Raspberry Pi
   pytest --live                                           tools/pi_channel_a.py
   192.168.2.2  ◀──────── data: Ethernet cable ──────────  192.168.2.1
                 ARINC 429 words, UDP port 42900
        │
        ▼
   bench_data/*.csv  →  receiver → voter (+ simulated B, C) → command law → actuator
```

Control and data use **different paths on purpose**: the test can take the Ethernet link down without cutting its own control line.

Three ways to run it, easiest first once it's set up:

| Mode | You do | Good for |
| --- | --- | --- |
| **Live** | `python -m pytest tests/test_bench_link.py --live -v` | One command: fresh live run, automated link drop, tests |
| **GitHub button** | Click "Run workflow" on GitHub | Same as live, started from GitHub, results on the Actions page |
| **Manual** | Two windows, you pull the cable by hand | Demos: watching it go stale live |

Without `--live`, the tests replay the last recordings in `bench_data/`. That's what GitHub's normal CI does on every push, so the Pi doesn't have to be on.

---

## 1. One-time setup

**Order matters:** push this repo update to GitHub first. The Pi downloads the code from there.

### 1a. Check the network

- Pi and laptop connected with the direct Ethernet cable: Pi `192.168.2.1`, laptop Ethernet `192.168.2.2`. Check with `ping 192.168.2.1`.
- Pi also on Wi-Fi (for control and to download code). Check with `ping dronepi.local`. If the name doesn't work, use the Pi's Wi-Fi IP from your router's device list everywhere this guide says `dronepi.local`.

**No Wi-Fi? One cable for everything works too.** If the PC shares its internet with the Pi over the Ethernet cable (Windows Internet Connection Sharing, or the Pi's default route pointing at the PC), you don't need Wi-Fi at all:

- Everywhere this guide says `taylor@dronepi.local`, use **`taylor@192.168.2.1`**. For live runs, add `--pi taylor@192.168.2.1`, or set it once per PowerShell window: `$env:PI_SSH="taylor@192.168.2.1"`.
- `git clone`, `pip install`, and the automatic `git pull` before each live run all go through the PC's connection. The pull happens before the link drop, so the Pi has internet when it needs it.
- The live test still works: pytest sends all its commands *before* the drop, the drop-and-restore runs on the Pi detached from the SSH session, and pytest only talks to the Pi again after the link is back.
- **Check which address the Pi sends data to.** On the Pi, run `ip route` and look at the `default via ...` line. If it says `default via 192.168.2.2`, nothing changes. If it's a different address (Windows sharing often uses `192.168.137.1`), that's your PC's address on the cable: add `--data-host <that address>` to the pytest command, and use the Pi's address in the firewall rule (step 1e) for `-RemoteAddress`.
- Two limits: if the Pi's network doesn't come back after a drop, you can't log in to fix it, so power-cycle the Pi (its settings survive a reboot). And **manual mode (section 4) doesn't work over one cable**, because pulling the cable kills your SSH login and the sender with it. Use live mode.

### 1b. Code on the Pi

```
ssh taylor@dronepi.local
git clone https://github.com/taylorp-dev/flight-actuator-verification.git
python3 -m venv ~/av-env
~/av-env/bin/pip install numpy pyyaml
```

(Live mode pulls the latest code onto the Pi automatically before each run.)

**No internet on the Pi?** Copy everything over the cable instead. In PowerShell on the PC, in the repo folder:

```
ssh taylor@192.168.2.1 "mkdir -p ~/actuator-verification"
scp -r sil tools config requirements taylor@192.168.2.1:~/actuator-verification/
ssh taylor@192.168.2.1 "python3 --version; python3 -c 'import numpy, yaml; print(123)'"
```

- Prints `123` (Raspberry Pi OS often includes them): `ssh taylor@192.168.2.1 "python3 -m venv --system-site-packages ~/av-env"`. Done.
- Errors: download the libraries on the PC for the Pi, then copy them. Use the Python version printed above (e.g. `3.13`):
  ```
  pip download numpy pyyaml --only-binary=:all: --platform manylinux2014_aarch64 --platform manylinux_2_17_aarch64 --python-version 3.13 --implementation cp -d pi-wheels
  scp -r pi-wheels taylor@192.168.2.1:~/
  ssh taylor@192.168.2.1 "python3 -m venv ~/av-env && ~/av-env/bin/pip install --no-index --find-links ~/pi-wheels numpy pyyaml"
  ```
  Then delete the local `pi-wheels` folder so it isn't committed.

Without internet, the automatic `git pull` before each live run prints `code unknown (git pull failed ...)` and carries on. That's fine. **When the code in `sil/`, `tools/` or `config/` changes, re-run the `scp` line** to update the Pi.

### 1c. Let the Pi take its Ethernet port down without a password

The automated "cable pull" runs `ip link set eth0 down`, then `up`, which needs `sudo`. This rule allows exactly those commands and nothing else. On the Pi:

```
echo 'taylor ALL=(root) NOPASSWD: /usr/sbin/ip link set eth0 down, /usr/sbin/ip link set eth0 up, /usr/sbin/ip link show eth0' | sudo tee /etc/sudoers.d/av-bench
sudo chmod 440 /etc/sudoers.d/av-bench
sudo visudo -c
```

The last line should say the files `parsed OK`. Test it: `sudo -n /usr/sbin/ip link show eth0` should print the interface **without asking for a password**. Then type `exit` to leave the Pi.

### 1d. Log in to the Pi without a password (SSH key)

pytest logs in to the Pi by itself, so it can't type a password. On the **laptop**, in PowerShell:

```
ssh-keygen -t ed25519
```

Press Enter three times (default file, no passphrase). Then copy the key to the Pi (asks your Pi password one last time):

```
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh taylor@dronepi.local "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

Test it, which must **not** ask for a password:

```
ssh -o BatchMode=yes taylor@dronepi.local echo ok
```

### 1e. Let the data through the laptop's firewall

PowerShell **as Administrator**:

```
New-NetFirewallRule -DisplayName "Actuator bench UDP 42900" -Direction Inbound -Protocol UDP -LocalPort 42900 -RemoteAddress 192.168.2.1 -Action Allow
```

One port, only for the Pi.

---

## 2. Live mode (one command)

In the repo folder on the laptop, with your venv active:

```
python -m pytest tests/test_bench_link.py --live -v
```

What happens, in about 45 seconds:
1. pytest checks the Pi is ready and pulls the latest code onto it.
2. It starts the channel A sender on the Pi and starts recording.
3. At 15 s it takes the Pi's Ethernet port down; at 20 s it brings it back up.
4. It records until 32 s, stops the sender, and makes sure the port is up.
5. All through the run, a **live monitor** checks every word the moment it arrives (label, parity, SDI, SSM) and re-checks "is channel A valid?" every 1 ms, so the link drop is caught live, at real time, not only afterwards. A status line prints once a second.
6. It saves `bench_data/healthy.csv` (the part before the drop), `bench_data/cable_pull.csv` (the whole run) and `bench_data/live_monitor.json` (what the live checks saw), then runs the 7 tests on the replay of the recording. The decode, false-stale and cable-pull tests also check the live results (the closed-loop tests use the replay only), and L2 checks that live and replay agree: same words (fingerprint of the saved recording), no false stale anywhere outside the drop, stale flag and recovery times within 5 ms.

Expected:

```
[live] Pi taylor@dronepi.local (code 1a2b3c4) -> 192.168.2.2; link drop at 15 s for 5 s; recording 32 s
[live] t=  0.0 s  words     1  pitch  -0.987 deg  VALID
...
[live] t= 16.0 s  words  1500  pitch  -1.012 deg  INVALID: stale
...
test_l1_words_on_the_wire_decode_per_icd PASSED
test_l1_rate_and_jitter_on_real_link PASSED
test_l1_no_false_stale_on_healthy_link PASSED
test_l1_cable_pull_flagged_stale_and_recovers PASSED
test_l1_closed_loop_with_real_channel_a PASSED
test_l1_closed_loop_cable_pull PASSED
test_l2_live_vs_replay_agree PASSED
7 passed
```

The measured numbers (mean interval, jitter, worst gap, how fast the drop was flagged and recovered, live and replay side by side, and `live_max_check_gap_ms`, how late the live checks themselves ran) land in the traceability matrix under L1 and L2. This is a **partial run** (bench tests only), so the matrix goes to `reports/dev/traceability.md`, not for record. The record comes from the full suite afterwards (below).

**Why live and replay both:** the replay keeps the PC's own hiccups out of the verdict and leaves evidence anyone can re-check; the live checks show it works at real time. Windows and Python are not a real-time system, so the live monitor asks Windows for a 1 ms timer during the run and records how late its checks ran. If L2 fails, look at `live_max_check_gap_ms` first: a big value means the PC was busy, not that the link is wrong.

Options: `--pi taylor@10.0.0.40` if `dronepi.local` doesn't resolve (or set `$env:PI_SSH`), `--drop-at 10 --drop-for 3` to change the timing.

**Save the evidence** so GitHub's normal CI replays your latest live run (the three files must come from the same run; L2 checks that):

```
git add bench_data
git commit -m "Bench link: live run"
git push
```

Then make the **run for record** on the committed code (`python tools/run_tests.py`, see USER-GUIDE section 7) and commit `reports/`.

**If a timing test fails, that's not necessarily a mistake.** It may be a real finding about Linux timing on the Pi. Keep the recording and look at `max_interval_ms` before changing anything.

---

## 3. GitHub button (self-hosted runner)

This makes your laptop a **self-hosted runner**: a machine GitHub can hand jobs to (the GitHub version of a Jenkins agent node). The workflow `.github/workflows/bench-live.yml` runs the live test on it when you click a button. The normal CI keeps running on GitHub's machines.

**Set up once:**
1. On GitHub: your repo → **Settings** → **Actions** → **Runners** → **New self-hosted runner** → **Windows**, x64.
2. GitHub shows a short list of PowerShell commands. Run them in a new folder, e.g. `D:\actions-runner`: download, extract, then `./config.cmd ...` with your token.
3. During `config.cmd`:
   - runner group, name: press Enter (defaults are fine)
   - **additional labels: type `pi-bench`**
   - work folder: Enter
   - **run as a service: `N`**. Running it yourself means it uses your login, which has the SSH key from step 1d.

**Each time you want to use it:**
1. PowerShell in `D:\actions-runner`: `./run.cmd`. Wait for `Listening for Jobs`.
2. GitHub → **Actions** → **Bench live (Raspberry Pi)** → **Run workflow**. The form shows the Pi address (`taylor@192.168.2.1`), this PC's address on the cable (`192.168.2.10`), and the drop timing, pre-filled for a single-cable setup. Change them if yours differ (Wi-Fi setup: `taylor@dronepi.local` and `192.168.2.2`), then click **Run workflow**.
3. Watch the live log. When it finishes, the traceability matrix is on the run's summary page, and the recordings and reports are under **Artifacts**.
4. Ctrl+C in the runner window when done.

**Security note:** the repo is public. GitHub warns that self-hosted runners on public repos can run code from other people's pull requests. Three things keep that safe here: the workflow only runs when **you** click it, the runner only runs while `run.cmd` is open, and you should check **Settings → Actions → General → "Require approval for all external contributors"** (fork pull request workflows). Close `run.cmd` when you're not using it.

---

## 4. Manual mode (watch it live, pull the cable yourself)

Good for demos. Log in to the Pi **over Wi-Fi** (`ssh taylor@dronepi.local`) so pulling the cable doesn't kill your login. Needs Wi-Fi: over a single cable, pulling it would kill your login and the sender.

**Window 1, laptop:**

```
python tools/bench_capture.py --name cable_pull --duration 60
```

**Window 2, Pi:**

```
cd ~/actuator-verification
~/av-env/bin/python tools/pi_channel_a.py --host 192.168.2.2
```

Window 1 prints a line every half second:

```
t=   5.0 s  words    501  pitch  -1.001 deg  VALID
```

Pitch reads about **-1.0**, not -2.0. That's correct: true pitch -2.0 plus channel A's +1.0 deg bias from `config/sil.yaml`.

At about 20 s, **pull the Ethernet cable**. Window 1 shows `INVALID: stale` within a fraction of a second. Plug it back in after about 5 s, and a few seconds later it's `VALID` again. For a manual `healthy` recording, run the same command with `--name healthy` and leave the cable alone.

Optional, inject a fault from the Pi side (same fault kinds as the SIL):

```
~/av-env/bin/python tools/pi_channel_a.py --host 192.168.2.2 --fault ssm_fail --fault-start 20 --fault-end 25
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `Pi not ready for live tests` | Repo, venv, or sudo rule missing on the Pi | Steps 1b and 1c; the message says what ssh reported |
| `Permission denied (publickey,password)` | SSH key not set up | Step 1d; test with `ssh -o BatchMode=yes taylor@dronepi.local echo ok` |
| `Could not resolve hostname dronepi.local` | Name lookup doesn't work on your network | Use the Wi-Fi IP: `--pi taylor@10.0.0.40` (check your router) |
| Live run fails, Pi only on the cable (no Wi-Fi) | Default control address is the Wi-Fi name | Add `--pi taylor@192.168.2.1`; check `ip route` on the Pi for the data address (section 1a, "One cable for everything") |
| Can't log in to the Pi after a live run (single cable) | Pi network didn't come back after the drop | Power-cycle the Pi; re-run with `--drop-for 3` |
| `no words on UDP 42900 within 25 s` | The laptop's Ethernet IP isn't 192.168.2.2 (Windows can change it), firewall, or the Pi can't reach the laptop | `ipconfig`: if the Ethernet IP is different, add `--data-host <that IP>` (or set it back to 192.168.2.2); step 1e; `ping 192.168.2.1` |
| `live run saw no link drop` | sudo rule not working | Step 1c test: `sudo -n /usr/sbin/ip link show eth0` must not ask for a password |
| Link drop flagged, but no recovery before the run ends | Pi network slow to come back up | Re-run with `--drop-for 3`; on the Pi, `nmcli connection up netplan-eth0` |
| `OSError: ... address already in use` | Another capture still running | Close the other window |
| GitHub job stays "Queued" | Runner not running, or missing the `pi-bench` label | Start `./run.cmd`; check the runner's labels in Settings → Actions → Runners |
| GitHub job: `Permission denied (publickey)` | Runner installed as a service (different user) | Re-configure with "run as a service: N", start it with `run.cmd` |
