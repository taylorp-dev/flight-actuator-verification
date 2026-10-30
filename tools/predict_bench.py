"""Predicted bench results for the desk-rig actuator (Actuonix L16-P).

    python tools/predict_bench.py   -> reports/l16p_predictions.md

Runs the same Part A analyses the flight-class tests use, but on the L16-P
model, unloaded and at the planned bench spring load. When the desk rig is
built, the measured values go in the last column. If they disagree, the model
gets corrected (model correlation) before the bench results are trusted for
anything else.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sil import analysis as an  # noqa: E402
from sil.ema import EMA, EMAParams  # noqa: E402
from sil.sim import load_config  # noqa: E402

OUT = ROOT / "reports" / "l16p_predictions.md"
FREQS = [0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 8]


def predict(cfg) -> list[tuple[str, str, str]]:
    b = cfg["bench_actuator_l16p"]
    p = EMAParams.from_dict(b["params"])
    load = b["bench_load_n"]
    rows = []
    for name, ld in (("unloaded", 0.0), (f"bench load {load:.0f} N", load)):
        r = an.step_response(EMA(p, load_n=ld), 1.0)
        rows.append((f"Step 1 mm, {name}: rise time", f"{r.rise_time_s * 1000:.0f} ms", "A1/A5"))
        rows.append((f"Step 1 mm, {name}: overshoot", f"{r.overshoot_pct:.1f} %", "A1/A5"))
        rows.append((f"Max extend rate, {name}", f"{an.max_rate(EMA(p, load_n=ld), +1.0):.1f} mm/s", "A2"))
    acc, hyst = an.backlash_and_accuracy(EMA(p), points_mm=(-20, 0, 20))
    rows.append(("Static accuracy (pot on rod)", f"{acc:.3f} mm", "A3"))
    rows.append(("Hysteresis seen at rod", f"{hyst:.3f} mm", "A3"))
    g, _ = an.frequency_response(EMA(p), FREQS)
    rows.append(("Bandwidth (-3 dB, 1 mm sine)", f"{an.bandwidth_hz(FREQS, g):.2f} Hz", "A4"))
    return rows


def main() -> None:
    cfg = load_config()
    b = cfg["bench_actuator_l16p"]
    rows = predict(cfg)
    lines = [
        "# Predicted bench results: Actuonix L16-P (35:1, 12 V, 100 mm)",
        "",
        "Model parameters come from the manufacturer datasheet (`config/sil.yaml`, "
        "`bench_actuator_l16p`). The model is checked against the datasheet by requirement M1. "
        "These are predictions only. The desk rig is not built yet; the last column is filled in "
        "when it is.",
        "",
        f"- Config sha256: `{cfg['_hash']}`",
        f"- Planned bench spring load: {b['bench_load_n']:.0f} N",
        "",
        "| Measurement | Predicted | Same test as | Measured on bench |",
        "| --- | --- | --- | --- |",
    ]
    lines += [f"| {m} | {v} | {t} | (not built) |" for m, v, t in rows]
    lines += ["", "Assumed values (not on the datasheet, measured on the bench first): "
              "motor lag, back-drive behavior.",
              "",
              "Bench note: the L16-P's built-in pot has < 2 % linearity (up to ~2 mm over the full stroke) "
              "and 0.3 mm repeatability, so on the bench it will swamp a 0.1 mm accuracy reading. "
              "Calibrate it against a reference first, or read the rod with a separate sensor. "
              "Same principle as the flight-class tests: the unit never grades itself."]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
