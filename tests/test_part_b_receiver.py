"""Part B, receiver stage: ARINC 429 word validity checks (ICD-1, R1-R4)."""

import pytest

from sil.arinc429 import SSM, decode_bnr, encode_bnr
from sil.receiver import Receiver
from sil.sim import label_defs


@pytest.fixture
def labels(cfg):
    return label_defs(cfg)


@pytest.fixture
def rx(cfg, labels):
    return Receiver(labels, stale_intervals=cfg["icd"]["stale_intervals"])


# ------------------------------------------------------------------ ICD
@pytest.mark.req("ICD-1")
@pytest.mark.parametrize("value", [0.0, 2.5, -2.5, 45.37, -89.99, 89.99, 179.9, -180.0])
def test_icd_bnr_round_trip(labels, value):
    ld = labels["pitch"]
    d = decode_bnr(encode_bnr(ld, value), ld)
    assert abs(d.value - value) <= ld.resolution / 2 + 1e-9
    assert d.label_octal == 0o324 and d.ssm is SSM.NORMAL and d.parity_ok


@pytest.mark.req("ICD-1")
def test_icd_label_bits_are_reversed(labels):
    """Label 324 octal = 11 010 100; transmitted MSB first, so bits 1-8 hold it reversed."""
    word = encode_bnr(labels["pitch"], 0.0)
    assert word & 0xFF == int("11010100"[::-1], 2)


@pytest.mark.req("ICD-1")
def test_icd_odd_parity(labels):
    for v in (0.0, 1.0, -33.3):
        assert bin(encode_bnr(labels["pitch"], v)).count("1") % 2 == 1


# --------------------------------------------------------------- R1-R4
@pytest.mark.req("R1")
def test_r1_bad_parity_rejected(rx, labels):
    ld = labels["pitch"]
    assert rx.receive("pitch", encode_bnr(ld, 5.0), 0.0)
    assert not rx.receive("pitch", encode_bnr(ld, 30.0, corrupt_parity=True), 0.02)
    valid, value, _ = rx.read("pitch", 0.03)
    assert valid and abs(value - 5.0) < 0.02          # bad word never reached the value
    assert rx.status["pitch"].parity_rejects == 1


@pytest.mark.req("R2")
@pytest.mark.parametrize("ssm", [SSM.FAILURE_WARNING, SSM.NO_COMPUTED_DATA])
def test_r2_ssm_invalid(rx, labels, ssm):
    rx.receive("pitch", encode_bnr(labels["pitch"], 5.0, ssm=ssm), 0.0)
    valid, _, reasons = rx.read("pitch", 0.001)
    assert not valid and any(r.startswith("ssm_") for r in reasons)


@pytest.mark.req("R2")
def test_r2_ssm_normal_valid(rx, labels):
    rx.receive("pitch", encode_bnr(labels["pitch"], 5.0), 0.0)
    assert rx.read("pitch", 0.001)[0]


@pytest.mark.req("R3")
def test_r3_stale_boundary(cfg, rx, labels, record_property):
    """Valid at exactly 3 intervals after the last word, stale just after."""
    ld = labels["pitch"]
    rx.receive("pitch", encode_bnr(ld, 5.0), 0.0)
    limit = cfg["icd"]["stale_intervals"] / ld.rate_hz
    record_property("stale_limit_ms", round(limit * 1000, 1))
    assert rx.read("pitch", limit)[0]
    valid, _, reasons = rx.read("pitch", limit + 0.001)
    assert not valid and "stale" in reasons


@pytest.mark.req("R4")
@pytest.mark.parametrize("value,expect_valid", [(90.0, True), (-90.0, True),
                                                 (90.5, False), (-120.0, False)])
def test_r4_physical_range(rx, labels, value, expect_valid):
    rx.receive("pitch", encode_bnr(labels["pitch"], value), 0.0)
    assert rx.read("pitch", 0.001)[0] is expect_valid
