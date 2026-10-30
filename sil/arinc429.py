"""ARINC 429 word encode/decode (software only, no physical layer).

32-bit word layout used here (bit 1 = LSB):
    bits 1-8    label (octal), transmitted MSB first, so stored bit-reversed
    bits 9-10   SDI (source/destination identifier)
    bits 11-28  BNR data field (MSB at bit 28)
    bit  29     sign (two's complement)
    bits 30-31  SSM
    bit  32     odd parity

BNR SSM codes: 00 Failure Warning, 01 No Computed Data, 10 Functional Test,
11 Normal Operation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class SSM(IntEnum):
    FAILURE_WARNING = 0b00
    NO_COMPUTED_DATA = 0b01
    FUNCTIONAL_TEST = 0b10
    NORMAL = 0b11


@dataclass(frozen=True)
class LabelDef:
    name: str
    label_octal: int      # e.g. 0o324
    range_units: float    # full-scale range, e.g. 180.0 deg
    sig_bits: int         # significant bits, excluding sign
    min_valid: float      # physical range check (receiver R4)
    max_valid: float
    rate_hz: float        # nominal transmit rate

    @property
    def resolution(self) -> float:
        return self.range_units / (1 << self.sig_bits)


def _reverse8(b: int) -> int:
    return int(f"{b & 0xFF:08b}"[::-1], 2)


def _parity_bit(word31: int) -> int:
    """Odd parity: set bit 32 so the total number of ones is odd."""
    return 0 if bin(word31).count("1") % 2 else 1


def encode_bnr(ld: LabelDef, value: float, ssm: SSM = SSM.NORMAL, sdi: int = 0,
               corrupt_parity: bool = False) -> int:
    counts = int(round(value / ld.resolution))
    full = 1 << ld.sig_bits
    counts = max(-full, min(full - 1, counts))           # saturate at full scale
    nbits = ld.sig_bits + 1                              # sign + magnitude bits
    twos = counts & ((1 << nbits) - 1)
    field = twos << (19 - nbits)                         # left-justify; sign lands on bit 29
    word = _reverse8(ld.label_octal)                     # bits 1-8
    word |= (sdi & 0b11) << 8                            # bits 9-10
    word |= field << 10                                  # bits 11-29
    word |= (int(ssm) & 0b11) << 29                      # bits 30-31
    p = _parity_bit(word)
    if corrupt_parity:
        p ^= 1
    return word | (p << 31)


@dataclass
class Decoded:
    label_octal: int
    sdi: int
    value: float
    ssm: SSM
    parity_ok: bool


def decode_bnr(word: int, ld: LabelDef) -> Decoded:
    label = _reverse8(word & 0xFF)
    sdi = (word >> 8) & 0b11
    field = (word >> 10) & ((1 << 19) - 1)               # bits 11-29
    nbits = ld.sig_bits + 1
    raw = field >> (19 - nbits)
    if raw & (1 << (nbits - 1)):                         # sign bit set
        raw -= 1 << nbits
    value = raw * ld.resolution
    ssm = SSM((word >> 29) & 0b11)
    parity_ok = bin(word).count("1") % 2 == 1
    return Decoded(label, sdi, value, ssm, parity_ok)
