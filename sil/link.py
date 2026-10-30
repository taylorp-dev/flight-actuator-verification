"""Bus-in-the-loop link: ARINC 429 words over Ethernet (UDP).

One UDP datagram carries one 32-bit ARINC 429 word, big-endian, the way one
word goes out on a 429 bus. The physical layer is Ethernet, not a 429 bus, so
this exercises real timing, a real cable, and a second computer, but not 429
electrical levels. That needs a 429 interface card (next rung up).

Captures are CSV: t_rx_s (receive time from first word), word_hex. Header lines
start with '#' and record where and how the capture was made.
"""

from __future__ import annotations

import csv
import struct
from dataclasses import dataclass, field
from pathlib import Path

from .arinc429 import LabelDef, _reverse8

DEFAULT_PORT = 42900


def pack_word(word: int) -> bytes:
    return struct.pack(">I", word & 0xFFFFFFFF)


def unpack_word(data: bytes) -> int:
    return struct.unpack(">I", data[:4])[0]


def label_of(word: int) -> int:
    """Label number (octal value as int, e.g. 0o324) from a raw word."""
    return _reverse8(word & 0xFF)


def label_lookup(labels: dict[str, LabelDef]) -> dict[int, str]:
    return {ld.label_octal: name for name, ld in labels.items()}


def write_capture(path: Path, rows: list[tuple[float, int]], meta: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        for k, v in meta.items():
            fh.write(f"# {k}: {v}\n")
        w = csv.writer(fh)
        w.writerow(["t_rx_s", "word_hex"])
        for t, word in rows:
            w.writerow([f"{t:.6f}", f"{word:08X}"])


def read_capture(path: Path) -> tuple[list[tuple[float, int]], dict]:
    meta, rows = {}, []
    with open(path) as fh:
        for line in fh:
            if line.startswith("#"):
                k, _, v = line[1:].partition(":")
                meta[k.strip()] = v.strip()
            elif line.startswith("t_rx_s") or not line.strip():
                continue
            else:
                t, word = line.strip().split(",")
                rows.append((float(t), int(word, 16)))
    return rows, meta


@dataclass
class ReplayChannel:
    """Plays a recorded word stream back into the SIL as one sensor channel.

    Has the same transmit(t, truth) interface as SensorChannel, so the receiver,
    voter, command law and actuator see recorded real-link words exactly as they
    arrived (same values, same timing, same gaps)."""

    rows: list[tuple[float, int]]
    labels: dict[str, LabelDef]
    t_offset: float = 0.0
    _i: int = 0
    _lookup: dict = field(default_factory=dict)

    def __post_init__(self):
        self._lookup = label_lookup(self.labels)

    def transmit(self, t: float, truth: dict[str, float]) -> list[tuple[str, int]]:
        out = []
        while self._i < len(self.rows) and self.rows[self._i][0] + self.t_offset <= t + 1e-9:
            word = self.rows[self._i][1]
            name = self._lookup.get(label_of(word))
            if name is not None:
                out.append((name, word))
            self._i += 1
        return out
