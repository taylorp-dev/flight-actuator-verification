"""Run on the Raspberry Pi: sensor channel A as a real, separate computer.

    python tools/pi_channel_a.py --host 192.168.2.2

Sends channel A's pitch and roll as ARINC 429 BNR words over Ethernet (UDP, one
word per datagram) to the laptop, in real time at the ICD label rate (50 Hz).
It uses the SAME channel code as the simulation (sil/sources.py) and the same
config (config/sil.yaml): channel A's bias and noise, label numbers, SDI.

No IMU yet, so the attitude is a steady value (default pitch -2.0, roll 0.0 deg),
plus channel A's bias and noise. The point of this step is the link: real timing,
a real cable, a second computer.

Optional fault from the Pi side (same fault kinds as the SIL):
    --fault ssm_fail --fault-start 20 --fault-end 25

Pulling the Ethernet cable is the physical fault: the sender keeps running and
counts send errors; the laptop sees the words stop.
"""

from __future__ import annotations

import argparse
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sil.link import DEFAULT_PORT, pack_word  # noqa: E402
from sil.sim import label_defs, load_config  # noqa: E402
from sil.sources import FAULT_KINDS, Fault, SensorChannel  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Channel A sender (Raspberry Pi)")
    ap.add_argument("--host", default="192.168.2.2", help="laptop IP on the direct cable")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--pitch", type=float, default=-2.0, help="true pitch, deg")
    ap.add_argument("--roll", type=float, default=0.0, help="true roll, deg")
    ap.add_argument("--duration", type=float, default=0.0, help="seconds, 0 = until Ctrl+C")
    ap.add_argument("--fault", choices=FAULT_KINDS, help="optional fault on pitch")
    ap.add_argument("--fault-start", type=float, default=20.0)
    ap.add_argument("--fault-end", type=float, default=25.0)
    ap.add_argument("--magnitude", type=float, default=0.0, help="fault magnitude if it needs one")
    args = ap.parse_args()

    cfg = load_config()
    labels = label_defs(cfg)
    s = cfg["sensors"]
    faults = []
    if args.fault:
        faults.append(Fault(args.fault, 0, "pitch", args.fault_start, args.fault_end, args.magnitude))
    ch = SensorChannel(index=0, labels=labels,
                       bias={"pitch": s["bias_deg"][0], "roll": s["bias_deg"][0]},
                       noise_sd=s["noise_sd_deg"], phase_s=0.0, seed=int(time.time()),
                       faults=faults)
    truth = {"pitch": args.pitch, "roll": args.roll}

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dest = (args.host, args.port)
    print(f"Channel A -> {dest[0]}:{dest[1]}  labels "
          + ", ".join(f"{n} {ld.label_octal:o} @ {ld.rate_hz:g} Hz" for n, ld in labels.items())
          + f"  config {cfg['_hash']}")
    if faults:
        f = faults[0]
        print(f"Fault: {f.kind} on pitch from {f.t_start:g} s to {f.t_end:g} s")
    print("Ctrl+C to stop. Pull the Ethernet cable any time to test link loss.\n")

    t0 = time.perf_counter()
    sent = errors = 0
    worst_late = 0.0
    next_report = 5.0
    try:
        while True:
            due = ch.next_due()
            now = time.perf_counter() - t0
            if due > now:
                time.sleep(due - now)
                now = time.perf_counter() - t0
            worst_late = max(worst_late, now - due)
            for _, word in ch.transmit(now, truth):
                try:
                    sock.sendto(pack_word(word), dest)
                    sent += 1
                except OSError:
                    errors += 1           # cable pulled / link down: keep going
            if now >= next_report:
                print(f"t={now:6.1f} s  sent {sent}  send errors {errors}  "
                      f"worst scheduling lateness {worst_late * 1000:.1f} ms")
                next_report += 5.0
                worst_late = 0.0
            if args.duration and now >= args.duration:
                break
    except KeyboardInterrupt:
        pass
    print(f"\nStopped. Sent {sent} words, {errors} send errors.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
