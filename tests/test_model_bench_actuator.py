"""M1: the bench actuator model matches its datasheet.

Before the desk rig is built, the model of its actuator (Actuonix L16-P) is
checked against the manufacturer's published points. The same Part A analyses
then give the predicted bench results (tools/predict_bench.py), which the real
hardware gets compared against. That comparison is model correlation.
"""

import pytest

from sil import analysis as an
from sil.ema import EMA, EMAParams


def l16p(cfg, load_n=0.0):
    return EMA(EMAParams.from_dict(cfg["bench_actuator_l16p"]["params"]), load_n=load_n)


def _points(cfg):
    ds = load_ds(cfg)
    return [(0.0, ds["no_load_speed_mm_s"])] + [tuple(p) for p in ds["points_n_mm_s"]]


def load_ds(cfg):
    return cfg["bench_actuator_l16p"]["datasheet"]


@pytest.mark.req("M1")
@pytest.mark.parametrize("point", [0, 1, 2], ids=["no_load", "peak_power", "peak_efficiency"])
def test_m1_speed_force_matches_datasheet(cfg, point, record_property):
    force_n, speed = _points(cfg)[point]
    measured = an.max_rate(l16p(cfg, force_n), direction=+1.0)
    err_pct = abs(measured - speed) / speed * 100
    record_property("force_n", force_n)
    record_property("datasheet_mm_s", speed)
    record_property("model_mm_s", round(measured, 1))
    record_property("error_pct", round(err_pct, 1))
    assert err_pct <= load_ds(cfg)["tolerance_pct"]


@pytest.mark.req("M1")
def test_m1_backlash_matches_datasheet(cfg, record_property):
    """The model uses the datasheet's mechanical backlash. The hysteresis a
    position sensor would see on the bench can come out a bit smaller, because
    the motor side overshoots slightly on approach and takes up part of the free play. That predicted
    value is recorded for the bench comparison."""
    params = cfg["bench_actuator_l16p"]["params"]
    _, hyst = an.backlash_and_accuracy(l16p(cfg), points_mm=(-20, 0, 20))
    record_property("model_backlash_param_mm", params["backlash_mm"])
    record_property("predicted_bench_hysteresis_mm", round(hyst, 3))
    assert params["backlash_mm"] == load_ds(cfg)["backlash_mm"]
    assert 0.0 < hyst <= params["backlash_mm"] + 1e-9
