"""Run on the laptop: receive channel A from the Raspberry Pi and record it.

    python tools/bench_capture.py --name healthy --duration 60
    python tools/bench_capture.py --name cable_pull --duration 60

Listens for ARINC 429 words over UDP, timestamps each one on arrival, and shows
a live status line every half second, run through the SAME receiver code the SIL
uses (sil/receiver.py). So when you pull the cable you watch the receiver go
STALE, and when you plug it back in you watch it recover.

The capture is saved to bench_data/<name>.csv. The bench tests
(tests/test_bench_link.py) replay it through the receiver, voter, command law
and actuator, so the evidence is repeatable and traced like every other test.
"""

from __future__ import annotations

import argparse
import datetime as dt
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sil.arinc429 import decode_bnr  # noqa: E402
from sil.bench import capture_udp  # noqa: E402
from sil.link import DEFAULT_PORT, label_lookup, label_of, write_capture  # noqa: E402
from sil.sim import label_defs, load_config  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Capture channel A from the Pi")
    ap.add_argument("--name", required=True, help="capture name, e.g. healthy or cable_pull")
    ap.add_argument("--duration", type=float, default=60.0, help="seconds after the first word")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--note", default="", help="free text saved in the capture header")
    args = ap.parse_args()

    cfg = load_config()
    labels = label_defs(cfg)
    lookup = label_lookup(labels)
    print(f"Listening on UDP port {args.port}. Start the sender on the Pi.")
    print("(Windows may ask to allow Python through the firewall: allow it.)\n")

    state = {"was_valid": False, "went_stale": 0, "first": True}

    def show(t, n, value, valid, reasons):
        if state["first"]:
            print(f"Recording {args.duration:g} s...\n")
            state["first"] = False
        if state["was_valid"] and not valid:
            state["went_stale"] += 1
        state["was_valid"] = valid
        txt = "VALID " if valid else "INVALID: " + ",".join(reasons)
        print(f"t={t:6.1f} s  words {n:6d}  pitch {value:+7.3f} deg  {txt}")

    try:
        rows, sender = capture_udp(labels, cfg["icd"]["stale_intervals"], args.duration,
                                   port=args.port, first_word_timeout_s=3600, status=show)
    except KeyboardInterrupt:
        print("\nStopped early, nothing saved.")
        return 1
    went_stale = state["went_stale"]

    meta = {
        "capture": args.name,
        "recorded_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "sender": sender,
        "receiver_host": platform.node(),
        "receiver_os": f"{platform.system()} {platform.release()}",
        "link": "direct Ethernet cable, UDP, one ARINC 429 word per datagram",
        "config_sha256_12": cfg["_hash"],
        "words": len(rows),
        "note": args.note,
    }
    out = ROOT / "bench_data" / f"{args.name}.csv"
    write_capture(out, rows, meta)
    p = [decode_bnr(w, labels["pitch"]) for _, w in rows if lookup.get(label_of(w)) == "pitch"]
    print(f"\nSaved {len(rows)} words to {out.relative_to(ROOT)}")
    print(f"pitch words {len(p)}, times the receiver went invalid: {went_stale}")
    print("Next: python -m pytest tests/test_bench_link.py -v")
    return 0


if __name__ == "__main__":
    sys.exit(main())
