"""Part B, voter stage (R5-R8). Unit-level tests drive the voter directly."""

import itertools

import pytest

from sil.voter import MidValueVoter, Mode


@pytest.fixture
def voter(cfg):
    v = cfg["voter"]
    return MidValueVoter(v["threshold_deg"], v["persistence_s"], v["frame_s"])


def frames(voter, values, n):
    out = None
    for _ in range(n):
        out = voter.update([(True, x) for x in values])
    return out


@pytest.mark.req("R5")
@pytest.mark.parametrize("perm", list(itertools.permutations([4.0, 5.0, 5.8])))
def test_r5_mid_value_select(voter, perm):
    out = voter.update([(True, x) for x in perm])
    assert out.value == 5.0 and out.mode is Mode.TRIPLEX


@pytest.mark.req("R6")
def test_r6_fail_after_persistence(voter, cfg, record_property):
    """Miscompare must persist for the full persistence time before latching."""
    needed = round(cfg["voter"]["persistence_s"] / cfg["voter"]["frame_s"])
    record_property("frames_to_latch", needed)
    out = frames(voter, [5.0, 9.0, 5.1], needed - 1)
    assert not out.failed                       # one frame short: still trusted
    out = voter.update([(True, 5.0), (True, 9.0), (True, 5.1)])
    assert out.failed == {1}


@pytest.mark.req("R6")
def test_r6_threshold_has_margin_over_tolerance_stack(cfg, record_property):
    """FINDING-002 guard: two healthy channels at opposite tolerance limits differ by
    2 x tolerance. The threshold needs margin above that or noise trips a good channel."""
    v = cfg["voter"]
    margin = v["threshold_deg"] - 2 * v["tolerance_deg"]
    record_property("margin_deg", round(margin, 2))
    assert margin >= cfg["voter"]["margin_min_deg"]


@pytest.mark.req("R6")
def test_r6_within_threshold_never_fails(voter, cfg):
    thr = cfg["voter"]["threshold_deg"]
    out = frames(voter, [5.0, 5.0 + 0.99 * thr, 5.0 - 0.99 * thr], 200)
    assert not out.failed and out.mode is Mode.TRIPLEX


@pytest.mark.req("R7")
def test_r7_single_spike_ignored(voter):
    frames(voter, [5.0, 5.0, 5.0], 5)
    voter.update([(True, 5.0), (True, 40.0), (True, 5.0)])      # one-frame spike
    out = frames(voter, [5.0, 5.0, 5.0], 20)
    assert not out.failed and out.mode is Mode.TRIPLEX


@pytest.mark.req("R7")
def test_r7_intermittent_spikes_reset_counter(voter, cfg):
    """Spikes shorter than persistence, separated by good data, never latch."""
    needed = round(cfg["voter"]["persistence_s"] / cfg["voter"]["frame_s"])
    for _ in range(10):
        frames(voter, [5.0, 40.0, 5.0], needed - 1)
        frames(voter, [5.0, 5.0, 5.0], 1)
    assert not voter.failed


@pytest.mark.req("R8")
def test_r8_dual_mode_average_and_annunciate(voter, cfg):
    needed = round(cfg["voter"]["persistence_s"] / cfg["voter"]["frame_s"])
    out = frames(voter, [4.0, 30.0, 6.0], needed + 1)
    assert out.mode is Mode.DUAL
    assert out.value == pytest.approx(5.0)
    assert "CHANNEL_FAILED:B" in out.annunciations
    assert "DEGRADED_DUAL" in out.annunciations


@pytest.mark.req("R8")
def test_r8_second_fault_in_dual_is_annunciated(voter, cfg):
    """Two channels left: a disagreement can be detected but not isolated."""
    needed = round(cfg["voter"]["persistence_s"] / cfg["voter"]["frame_s"])
    frames(voter, [4.0, 30.0, 6.0], needed + 1)
    out = voter.update([(True, 4.0), (True, 30.0), (True, 12.0)])
    assert "DUAL_MISCOMPARE" in out.annunciations


@pytest.mark.req("R8")
def test_r8_invalid_channel_excluded(voter):
    out = voter.update([(True, 4.0), (False, 99.0), (True, 6.0)])
    assert out.mode is Mode.DUAL and out.value == pytest.approx(5.0)
