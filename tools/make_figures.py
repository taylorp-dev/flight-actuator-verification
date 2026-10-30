"""Draw the presentation figures from the data the tests saved in the run for record.

    python tools/make_figures.py                 -> reports/figures/*.png, from reports/data/
    python tools/make_figures.py --dev           preview from reports/dev/data/ (any run that is
                                                 not for record), watermarked, in reports/dev/figures/

Nothing here runs the simulation. Every point on every figure is read from the
CSV files the tests wrote with the `plot_data` fixture (tests/conftest.py), and
every number in a legend or title comes from those files or from the test's
recorded result. The script refuses to draw if:

  - the run is not a run for record (full run on committed code, known commit),
    unless --dev is given (then each figure is watermarked and goes to reports/dev/figures/);
  - a data file is missing, or comes from a different run (commit, config or run
    time) than the traceability matrix next to it;
  - config/sil.yaml today is not the config the run used.

Figures are drawn into a staging folder first; the figure set is replaced only
if every figure drew, so a refusal never leaves a mix of old and new figures.

Each figure's footer names the data files, the commit and the config hash, so a
slide traces to a run, and docs/EVIDENCE.md lists which test produced which file.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sil.sim import load_config  # noqa: E402

OUT = ROOT / "reports" / "figures"

# reference palette (light mode), fixed slot order
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
SURFACE = "#fcfcfb"
CRIT = "#e34948"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "axes.titlecolor": INK,
    "axes.titleweight": "bold", "axes.titlesize": 12, "axes.titlelocation": "left",
    "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
    "lines.linewidth": 2.0, "font.size": 10, "legend.frameon": False,
    "legend.labelcolor": INK2,
})


class EvidenceError(RuntimeError):
    pass


# ------------------------------------------------------------- the run's data
class Run:
    """The saved data of one test run (reports/ or reports/dev/)."""

    def __init__(self, report_dir: Path, require_record: bool):
        self.dir = report_dir
        summary_path = report_dir / "test_summary.json"
        index_path = report_dir / "data" / "index.json"
        if not summary_path.exists() or not index_path.exists():
            raise EvidenceError(f"no test run with saved plot data in {report_dir}: run the tests first")
        self.summary = json.loads(summary_path.read_text())["summary"]
        self.index = json.loads(index_path.read_text())
        self.commit = self.summary["git_commit"]
        self.config = self.summary["config_sha256_12"]
        self.label = self.summary["run_label"]
        self.generated = self.summary["generated_utc"]
        self.is_record = (bool(self.summary.get("record")) and self.summary["run_type"] == "FULL RUN"
                          and self.commit != "no-git" and not self.commit.endswith("-dirty")
                          and self.label.endswith(", record"))
        if require_record and not self.is_record:
            raise EvidenceError(f"{report_dir} is not a run for record ({self.label}). Commit, run the "
                                "full suite, then draw; or use --dev for a watermarked preview.")
        if (self.index["git_commit"], self.index["config_sha256_12"], self.index["generated_utc"]) != \
                (self.commit, self.config, self.generated):
            raise EvidenceError("plot data and traceability matrix come from different runs")
        cfg_now = load_config()["_hash"]
        if cfg_now != self.config:
            raise EvidenceError(f"config/sil.yaml is {cfg_now} today but the run used {self.config}")
        self.files = {f["file"]: f for f in self.index["files"]}
        self.status = {r["test"]: r["status"] for r in
                       json.loads(summary_path.read_text())["results"]}

    def load(self, name: str) -> tuple[dict, dict]:
        """(header, columns) of reports/data/<name>.csv."""
        fname = f"{name}.csv"
        if fname not in self.files:
            raise EvidenceError(f"missing plot data {fname}: the test that saves it did not run")
        path = self.dir / "data" / fname
        if not path.exists():
            raise EvidenceError(f"missing plot data {fname}: listed in the index but the file is gone")
        header, names, rows = {}, None, []
        for line in path.read_text().splitlines():
            if line.startswith("# "):
                k, _, v = line[2:].partition(": ")
                header[k] = v
            elif names is None:
                names = line.split(",")
            else:
                rows.append([float(x) for x in line.split(",")])
        if (header.get("git_commit"), header.get("config_sha256_12"), header.get("generated_utc")) != \
                (self.commit, self.config, self.generated):
            raise EvidenceError(f"{fname} comes from a different run")
        arr = np.array(rows) if rows else np.empty((0, len(names or [])))
        cols = {n: arr[:, i] for i, n in enumerate(names or [])}
        return header, cols

    def footer(self, fig, files, note="", y=-0.06, real_hw=False):
        kind = ("Real hardware recording, replayed through the SIL." if real_hw
                else "Software-in-the-loop simulation, representative values.")
        src = "from the run for record" if self.is_record else "NOT FOR RECORD: " + self.label
        fig.text(0.01, y, f"{kind} {src}, commit {self.commit}, config sha256 {self.config}"
                 + (f"  |  {note}" if note else ""), color=MUTED, fontsize=7.5)
        rel = self.dir.relative_to(ROOT).as_posix()
        fig.text(0.01, y - 0.035, "data: " + ", ".join(f"{rel}/data/{f}.csv" for f in files),
                 color=MUTED, fontsize=7)
        if not self.is_record:
            fig.text(0.5, 0.5, "NOT FOR RECORD", color=CRIT, alpha=0.25, fontsize=40,
                     ha="center", va="center", rotation=20, fontweight="bold")


def num(h, key):
    v = h.get(key, "None")
    return None if v in ("None", "") else float(v)


def fmt(v, spec, none="n/a"):
    return none if v is None else format(v, spec)


def verdict(status: str) -> str:
    return {"passed": "PASS", "xfail": "FAIL (open defect)", "failed": "FAIL"}.get(status, status.upper())


STAGE: Path | None = None       # figures are drawn here first, and only moved to OUT if all succeed


def save(fig, name):
    STAGE.mkdir(parents=True, exist_ok=True)
    fig.savefig(STAGE / name, dpi=200, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- Part A
def fig_step(run, cfg):
    spec = cfg["actuator_spec"]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    files = ["a1_step_unloaded", "a5_step_rated"]
    for name, col, lab in zip(files, (BLUE, ORANGE), ("unloaded", "rated")):
        h, c = run.load(name)
        keep = c["t_s"] <= 0.8
        ax.plot(c["t_s"][keep] * 1000, c["rod_mm"][keep], color=col,
                label=f"{lab} ({num(h, 'load_n'):.0f} N): rise {num(h, 'rise_s') * 1000:.0f} ms, "
                      f"overshoot {num(h, 'overshoot_pct'):.1f}%")
    ax.plot(c["t_s"][keep] * 1000, c["cmd_mm"][keep], color=MUTED, lw=1.2, ls="--", label="command")
    ax.axhline(spec["A1_step_mm"] * (1 + spec["A1_overshoot_max_pct"] / 100), color=CRIT,
               lw=1, ls=":", label=f"overshoot limit ({spec['A1_overshoot_max_pct']:.0f}%)")
    ax.set(title="A1 / A5: 1 mm step response at the output rod",
           xlabel="time (ms)", ylabel="rod position (mm)")
    ax.legend(loc="lower right", fontsize=8.5)
    run.footer(fig, files)
    save(fig, "a1_a5_step_response.png")


def fig_bode(run, cfg):
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7, 4.8), sharex=True)
    files = ["a4_bode_unloaded", "a4_bode_rated"]
    for name, col, lab in zip(files, (BLUE, ORANGE), ("unloaded", "rated")):
        h, c = run.load(name)
        a1.semilogx(c["freq_hz"], c["gain_db"], color=col, marker="o", ms=3.5,
                    label=f"{lab}: -3 dB at {num(h, 'bandwidth_hz'):.2f} Hz")
        a2.semilogx(c["freq_hz"], c["phase_deg"], color=col, marker="o", ms=3.5)
    lim = cfg["actuator_spec"]["A4_bandwidth_min_hz"]
    a1.axhline(-3, color=MUTED, lw=1, ls="--")
    a1.axvline(lim, color=CRIT, lw=1, ls=":", label=f"required >= {lim} Hz")
    a1.set(title="A4: frequency response (1 mm sine dwell)", ylabel="gain (dB)")
    a1.legend(fontsize=8.5, loc="lower left")
    a2.set(xlabel="frequency (Hz)", ylabel="phase (deg)")
    run.footer(fig, files)
    save(fig, "a4_bode.png")


def fig_backlash(run, cfg):
    h, c = run.load("a3_backlash_sine")
    fig, ax = plt.subplots(figsize=(5.4, 4.2))
    ax.plot(c["cmd_mm"], c["own_err_mm"], color=MUTED, lw=1.5,
            label=f"actuator's own feedback ({num(h, 'sine_own_feedback_hysteresis_mm'):.3f} mm)")
    ax.plot(c["cmd_mm"], c["rod_err_mm"], color=BLUE,
            label=f"independent truth sensor, rod ({num(h, 'sine_truth_hysteresis_mm'):.3f} mm)")
    ok = h["test_status"] == "passed"
    ax.set(title="A3: the unit can't see its own backlash" if ok
           else f"A3 own-feedback test: {verdict(h['test_status'])}",
           xlabel="command (mm)", ylabel="position error (mm)")
    ax.legend(fontsize=8.5, loc="upper left", bbox_to_anchor=(0, -0.16), ncol=1)
    run.footer(fig, ["a3_backlash_sine"], "hysteresis at the command's zero crossings", y=-0.22)
    save(fig, "a3_backlash.png")


# ---------------------------------------------------------------- Part B
def fig_fault_response(run, cfg):
    h, c = run.load("r9_baseline_unloaded")
    keep = c["t_s"] >= 0.05          # skip the first-word startup frame
    t = c["t_s"][keep]
    detect = num(h, "detect_t_s")
    t_fault = num(h, "fault_t_s")
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 5.4), sharex=True)
    for key, col, lab in (("ch_a_deg", BLUE, "channel A"), ("ch_b_deg", ORANGE, "channel B (drift fault)"),
                          ("ch_c_deg", AQUA, "channel C")):
        a1.plot(t, c[key][keep], color=col, lw=1.4, label=lab)
    a1.plot(t, c["voted_deg"][keep], color=INK, lw=2.2, label="voted")
    a1.plot(t, c["truth_deg"][keep], color=MUTED, lw=1, ls="--", label="true pitch")
    for ax in (a1, a2):
        ax.axvline(t_fault, color=MUTED, lw=1, ls=":")
        ax.axvline(detect, color=CRIT, lw=1, ls=":")
    a1.text(t_fault + 0.03, 2.6, "fault starts", color=INK2, fontsize=8.5)
    a1.text(detect + 0.05, -1.6, f"{h['failed']} latched failed, voter {h['final_mode']} at the end",
            color=INK2, fontsize=8.5, ha="left")
    a1.set(title=f"Sensor fault to actuator: {h['fault']}", ylabel="pitch (deg)", ylim=(-4, 3.5))
    a1.legend(ncol=5, fontsize=8, loc="lower left")
    a2.plot(t, c["cmd_mm"][keep], color=MUTED, lw=1.2, ls="--", label="actuator command")
    a2.plot(t, c["rod_mm"][keep], color=BLUE,
            label=f"rod position (truth sensor), step {num(h, 'step_mm'):.2f} mm")
    a2.set(xlabel="time (s)", ylabel="actuator (mm)")
    a2.legend(fontsize=8.5, loc="lower right")
    run.footer(fig, ["r9_baseline_unloaded"], "unloaded")
    save(fig, "b_fault_to_actuator.png")


def fig_finding(run, cfg):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
    files, verdicts = [], {}
    for ax, prefix, title in ((axes[0], "r9_baseline", "Baseline design"),
                              (axes[1], "r9_antiwindup", "After corrective action (anti-windup)")):
        for load, col in (("unloaded", BLUE), ("rated", ORANGE)):
            name = f"{prefix}_{load}"
            files.append(name)
            h, c = run.load(name)
            detect = num(h, "detect_t_s")
            verdicts[name] = verdict(h["test_status"])
            keep = (c["t_s"] >= detect - 0.1) & (c["t_s"] <= detect + 1.6)
            ax.plot(c["t_s"][keep] - detect, c["rod_mm"][keep], color=col,
                    label=f"{load}: overshoot {num(h, 'overshoot_mm'):.2f} mm, "
                          f"settle {num(h, 'settle_s'):.2f} s  {verdict(h['test_status'])}")
        final = num(h, "final_mm")
        ax.axhline(final + num(h, "overshoot_limit_mm"), color=CRIT, lw=1, ls=":",
                   label=f"overshoot limit +{num(h, 'overshoot_limit_mm'):g} mm")
        band = num(h, "settle_band_mm")
        ax.axhspan(final - band, final + band, color=GRID, alpha=0.6, lw=0)
        ax.axvline(num(h, "settle_limit_s"), color=MUTED, lw=1, ls="--",
                   label=f"settle by {num(h, 'settle_limit_s'):g} s")
        ax.set(title=title, xlabel="time after channel failure declared (s)")
        ax.legend(fontsize=8, loc="lower right")
    axes[0].set_ylabel("rod position (mm)")
    word = lambda v: "passes" if v == "PASS" else "fails"
    fig.suptitle(f"R9 baseline, same fault, same test: {word(verdicts['r9_baseline_unloaded'])} unloaded, "
                 f"{word(verdicts['r9_baseline_rated'])} at rated load.",
                 x=0.01, ha="left", fontweight="bold", color=INK, fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    run.footer(fig, files, f"gray band = +/-{band:g} mm settle band (around the rated case's final value)", y=-0.02)
    save(fig, "finding_loaded_vs_unloaded.png")


def fig_wrong_channel(run, cfg):
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.9), sharey=True)
    files = ["finding002_threshold_old", "finding002_threshold_configured"]
    status = None
    for ax, name in zip(axes, files):
        h, c = run.load(name)
        status = h["test_status"]
        margin = num(h, "threshold_deg") - 2 * num(h, "tolerance_deg")
        why = "= 2 x tolerance, no margin" if abs(margin) < 1e-9 else f"2 x tolerance {margin:+.1f} deg"
        failed = h["failed_channel"]
        ax.plot(c["t_s"], c["voted_err_deg"], color=BLUE if failed == "B" else ORANGE,
                label=f"voted - true; channel failed: {failed}")
        tol = num(h, "tolerance_deg")
        ax.axhspan(-tol, tol, color=GRID, alpha=0.6, lw=0)
        ax.set(title=f"Threshold {num(h, 'threshold_deg'):.1f} deg ({why})", xlabel="time (s)")
        ax.legend(fontsize=8.5, loc="lower left")
    axes[0].set_ylabel("voted pitch error (deg)")
    fig.suptitle("FINDING-002 reproduced: frozen middle channel B, old vs configured threshold"
                 f" (reproduction test: {verdict(status)})",
                 x=0.01, ha="left", fontweight="bold", color=INK, fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    run.footer(fig, files, "gray band = healthy sensor tolerance; reproduced by "
               "test_finding002_reproduced_at_old_threshold", y=-0.02)
    save(fig, "finding_wrong_channel_isolated.png")


def fig_fault_matrix(run, cfg):
    # fault types come from the run's data (one file per case); this list only sets the row order
    order = ["frozen", "drift", "bias_jump", "spike", "bad_parity", "ssm_fail", "ssm_ncd", "dropout", "out_of_range"]
    found = sorted({f[len("fault_matrix_"):-len("_chA.csv")] for f in run.files
                    if f.startswith("fault_matrix_") and f.endswith("_chA.csv")})
    kinds = [k for k in order if k in found] + [k for k in found if k not in order]
    if not kinds:
        raise EvidenceError("no fault matrix data in this run")
    labels = {"ssm_fail": "SSM failure warn.", "ssm_ncd": "SSM no comp. data"}
    cells, passed, total, files = [], 0, 0, []
    for k in kinds:
        row = []
        for ch in "ABC":
            name = f"fault_matrix_{k}_ch{ch}"
            files.append(name)
            h, _ = run.load(name)
            total += 1
            ok = h["test_status"] == "passed"
            passed += ok
            if h["expect"] == "isolate":
                lat = num(h, "detect_latency_ms")
                txt = (f"isolated\n{fmt(lat, '.0f')} ms" if h["failed"] == ch
                       else f"WRONG ({h['failed']})")
            elif h["expect"] == "ignore":
                txt = "ignored" if h["failed"] == "none" else "FALSE TRIP"
            else:
                txt = "excluded\n(receiver)" if h["excluded_by_receiver"] == "True" else "MISSED"
            row.append(txt if ok else f"{txt}\nTEST {h['test_status'].upper()}")
        cells.append(row)
    fig, ax = plt.subplots(figsize=(6.4, 5.0))
    ax.axis("off")
    tbl = ax.table(cellText=cells, rowLabels=[labels.get(k, k.replace("_", " ")) for k in kinds],
                   colLabels=["channel A", "channel B", "channel C"], loc="center", cellLoc="center")
    tbl.scale(1, 2.2)
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor(SURFACE)
        cell.set_linewidth(2)
        if r == 0 or c == -1:
            cell.set_facecolor("#efeeea")
            cell.get_text().set_color(INK)
            cell.get_text().set_fontweight("bold")
        else:
            bad = "TEST" in cell.get_text().get_text()
            cell.set_facecolor("#fbe3e3" if bad else "#e6f2fb")
            cell.get_text().set_color(INK)
    result = "all pass" if passed == total else f"{passed} of {total} pass"
    allow = cfg["voter"]["latency_allowance_deg"]
    sub = (f"(each test also checks the voted value stays within the voter tolerance + {allow:g} deg latency allowance,\n"
           "the R8 annunciations, and that the R10 command limits hold)"
           if passed == total else "(failed cells: see the traceability matrix for which check failed)")
    ax.set_title(f"Fault matrix: {len(kinds)} fault types x 3 channels, {result}\n{sub}", loc="left", fontsize=11)
    fig.text(0.01, 0.02, f"Software-in-the-loop simulation. {'from the run for record' if run.is_record else 'NOT FOR RECORD'}, "
             f"commit {run.commit}, config sha256 {run.config}  |  detect latency from fault onset",
             color=MUTED, fontsize=7.5)
    fig.text(0.01, -0.015, f"data: {run.dir.relative_to(ROOT).as_posix()}/data/fault_matrix_<fault>_ch<A|B|C>.csv "
             f"({total} files, one per test_fault_matrix case; verdicts from the test results)", color=MUTED, fontsize=7)
    if not run.is_record:
        fig.text(0.5, 0.5, "NOT FOR RECORD", color=CRIT, alpha=0.25, fontsize=40, ha="center",
                 va="center", rotation=20, fontweight="bold")
    save(fig, "b_fault_matrix.png")


# ------------------------------------------------------------- Part C
def fig_motor_loss(run, cfg):
    fig, ax = plt.subplots(figsize=(8, 3.8))
    files = ["r11_motor_loss_baseline_unloaded", "r11_motor_loss_baseline_rated",
             "r11_motor_loss_option_a_rated"]
    kinds = ("baseline motors", "baseline motors", "each motor sized for full load")
    verdicts, t_fail = {}, None
    for name, col, kind in zip(files, (AQUA, CRIT, BLUE), kinds):
        h, c = run.load(name)
        load = num(h, "load_n")
        lab = "unloaded" if load == 0 else f"{load:,.0f} N"
        verdicts[name] = verdict(h["test_status"])
        ax.plot(c["t_s"], c["rod_mm"], color=col, lw=2.6 if load == 0 else 2.0,
                label=f"{lab}, {kind}: max {num(h, 'max_deviation_mm'):.2f} mm, {verdicts[name]}")
        t_fail = num(h, "t_fail_s")
        trip = num(h, "monitor_trip_t_s")
        if trip is not None:
            ax.axvline(trip, color=col, ls=":", lw=1.2)
            y = float(np.interp(trip, c["t_s"], c["rod_mm"]))
            ax.annotate(f"monitor annunciates (+{trip - t_fail:.2f} s)", (trip, y),
                        xytext=(trip - 2.3, y - 0.3), color=col, fontsize=8.5,
                        arrowprops=dict(arrowstyle="->", color=col))
        lim = num(h, "hold_limit_mm")
    ax.axhspan(-lim, lim, color=AQUA, alpha=0.08)
    ax.axhline(-lim, color=MUTED, ls="--", lw=1)
    ax.axvline(t_fail, color=INK2, lw=1)
    ax.text(t_fail + 0.05, 0.3, "one motor lost", color=INK2, fontsize=8.5)
    ax.set_xlabel("time (s)"); ax.set_ylabel("rod position (mm)")
    ax.set_ylim(-2.0, 0.6)
    word = lambda v: "holds" if v == "PASS" else "not held"
    ax.set_title(f"R11 motor channel loss, baseline: {word(verdicts[files[0]])} unloaded, "
                 f"{word(verdicts[files[1]])} at rated load")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), fontsize=8, ncol=1)
    run.footer(fig, files, f"band = R11 hold limit +/-{lim:g} mm; lines overlap where both hold at 0", y=-0.33)
    save(fig, "c_motor_loss.png")


def fig_jam(run, cfg):
    name = "r12_jam_rated-mid"
    h, c = run.load(name)
    trip, t_jam = num(h, "monitor_trip_t_s"), num(h, "t_jam_s")
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 4.6), sharex=True,
                                 gridspec_kw={"height_ratios": [2, 1]})
    a1.plot(c["t_s"], c["cmd_mm"], color=MUTED, ls="--", lw=1.4,
            label=f"command ({num(h, 'cmd_rate_mm_s'):g} mm/s ramp)")
    a1.plot(c["t_s"], c["rod_mm"], color=BLUE, label="rod position")
    a1.axvline(t_jam, color=CRIT, lw=1.2)
    a1.text(t_jam + 0.01, float(np.min(c["rod_mm"])) + 0.4, "jam", color=CRIT, fontsize=9)
    if trip is not None:
        a1.axvline(trip, color=ORANGE, lw=1.2)
        a1.text(trip + 0.02, float(np.min(c["rod_mm"])) + 1.8,
                f"JAM annunciated\n+{(trip - t_jam) * 1000:.0f} ms", color=ORANGE, fontsize=9)
        a2.axvline(trip, color=ORANGE, lw=1.2)
    a1.set_ylabel("position (mm)"); a1.legend(loc="upper left", fontsize=8.5)
    load = num(h, "load_n")
    a1.set_title(f"R12 jam at {load:,.0f} N: test {verdict(h['test_status'])}"
                 + ("" if trip is not None else " (jam NOT annunciated)"))
    a2.plot(c["t_s"], c["drive_mm_s"], color=ORANGE)
    a2.axvline(t_jam, color=CRIT, lw=1.2)
    a2.set_ylabel("drive (mm/s)"); a2.set_xlabel("time (s)")
    fig.tight_layout()
    run.footer(fig, [name], f"monitor threshold {num(h, 'monitor_threshold_mm'):g} mm, sized from the "
               "healthy envelope", y=-0.03)
    save(fig, "c_jam_detection.png")


def fig_force_fight(run, cfg):
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.9), sharey=True)
    cases = [("r13_equalization_off_healthy", "No equalization, all lanes healthy"),
             ("r13_equalization_on_healthy", "Equalization on, all lanes healthy"),
             ("r13_faulty_laneA+5mm", "Equalization on, lane A sensor +5 mm")]
    for ax, (name, title) in zip(axes, cases):
        h, c = run.load(name)
        for key, col, lane in (("force_a_n", BLUE, "A"), ("force_b_n", ORANGE, "B"), ("force_c_n", AQUA, "C")):
            ax.plot(c["t_s"], c[key], color=col, label=f"lane {lane}")
        if h["disengaged"] != "none":
            for item in h["disengaged"].split(";"):
                lane, td = item.split("@")
                ax.axvline(float(td), color=CRIT, lw=1.2)
                ax.text(float(td) + 0.05, -3600, f"lane {lane} disengaged", color=CRIT, fontsize=8.5)
        if "fault_t_s" in h:
            ax.axvline(num(h, "fault_t_s"), color=INK2, lw=1)
        ax.set_title(f"{title}\ntest {verdict(h['test_status'])}", fontsize=10.5)
        ax.set_ylim(-4200, 6200)
        ax.set_xlabel("time (s)")
    axes[0].set_ylabel("lane force (N)")
    axes[1].legend(loc="upper right", fontsize=8.5, ncol=3)
    h0, _ = run.load(cases[0][0])
    if h0["disengaged"] != "none":       # no equalization: a healthy lane is disengaged (that test's point)
        lane, td = h0["disengaged"].split(";")[0].split("@")
        axes[0].text(float(td) + 0.8, -1900, f"lane {lane} was healthy:\nfalse disengage", color=CRIT, fontsize=8.5)
    fig.suptitle("R13 force fight: three lanes on one surface, rated load shared",
                 x=0.01, ha="left", fontweight="bold", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    run.footer(fig, [n for n, _ in cases], f"rig offsets per lane (mm): {h0['rig_offsets_mm']}", y=-0.03)
    save(fig, "c_force_fight.png")


# ------------------------------------------------------------- bench link (real Pi)
def fig_bench_link(run, cfg):
    """Link-drop timeline from the real Raspberry Pi recording, as the bench tests replayed it."""
    hi, ci = run.load("bench_pitch_intervals")
    hv, cv = run.load("bench_receiver_valid")
    hm, cm = run.load("bench_voter_channels")
    t_last, t_back = num(hv, "t_last_word_s"), num(hv, "t_back_s")
    stale_ms = num(hv, "stale_limit_s") * 1000.0
    flag_ms = num(hv, "flag_s") * 1000.0
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.2, 4.9), sharex=True,
                                 gridspec_kw={"height_ratios": [2.2, 1]})
    a1.axvspan(t_last, t_back, color=CRIT, alpha=0.08)
    keep = ci["interval_ms"] < 200
    a1.plot(ci["t_s"][keep], ci["interval_ms"][keep], ".", ms=2.5, color=BLUE,
            label="interval between words (ms)")
    a1.axhline(num(hi, "nominal_interval_ms"), color=MUTED, lw=1, ls=":")
    a1.axhline(stale_ms, color=CRIT, lw=1.2, ls="--", label=f"stale limit {stale_ms:.0f} ms")
    a1.set_ylim(0, stale_ms * 1.35)
    a1.set_ylabel("ms between words")
    a1.text(t_last + 0.15, stale_ms * 1.12, f"no words for {t_back - t_last:.1f} s\n({hv.get('link_drop', 'link drop')})",
            color=CRIT, fontsize=9)
    a1.legend(loc="lower left", fontsize=8.5)
    a1.set_title(f"Real Raspberry Pi over Ethernet: link drop flagged in {flag_ms:.1f} ms")
    a2.step(cm["t_s"], cm["channels_in_use"], where="post", color=ORANGE, label="voter channels in use")
    a2.step(cv["t_s"], cv["ch_a_valid"] * 0.6 + 0.3, where="post", color=AQUA, lw=1.5,
            label="ch. A receiver valid")
    a2.set_yticks([2, 3])
    a2.set_yticklabels(["2", "3"])
    a2.text(cm["t_s"][-1], 0.95, "valid", color=AQUA, fontsize=8, ha="right", va="bottom")
    a2.set_ylim(0, 3.5)
    a2.set_ylabel("voter")
    a2.set_xlabel("time from first word (s)")
    a2.legend(loc="center", bbox_to_anchor=(0.5, 0.42), fontsize=8, ncol=2)
    fig.tight_layout()
    run.footer(fig, ["bench_pitch_intervals", "bench_receiver_valid", "bench_voter_channels"],
               f"recording {hv.get('recording', '?')}, {hv.get('recorded_utc', '')}, sender {hv.get('sender', '')}",
               y=-0.03, real_hw=True)
    save(fig, "bench_link_drop.png")


FIGURES = [fig_step, fig_bode, fig_backlash, fig_fault_response, fig_finding, fig_wrong_channel,
           fig_fault_matrix, fig_motor_loss, fig_jam, fig_force_fight, fig_bench_link]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dev", action="store_true",
                    help="preview from reports/dev/ (any run that is not for record), watermarked, "
                         "written to reports/dev/figures/")
    a = ap.parse_args(argv)
    report_dir = ROOT / "reports" / ("dev" if a.dev else "")
    global STAGE
    out = ROOT / "reports" / "dev" / "figures" if a.dev else OUT
    STAGE = out.parent / (out.name + ".tmp")
    if STAGE.exists():
        shutil.rmtree(STAGE)
    try:
        run = Run(report_dir, require_record=not a.dev)
        cfg = load_config()
        print(f"drawing from {report_dir / 'data'}: {run.label}, commit {run.commit}, config {run.config}")
        for f in FIGURES:
            f(run, cfg)
    except EvidenceError as e:
        shutil.rmtree(STAGE, ignore_errors=True)
        print("make_figures: REFUSED:", e, file=sys.stderr)
        print("make_figures: no figure was changed", file=sys.stderr)
        return 2
    except Exception as e:                     # a bug or odd data: never leave a half-updated set
        shutil.rmtree(STAGE, ignore_errors=True)
        print(f"make_figures: FAILED while drawing ({type(e).__name__}: {e}); no figure was changed",
              file=sys.stderr)
        raise
    # every figure drew from the same run: replace the whole set at once
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.png"):
        old.unlink()
    for new in STAGE.glob("*.png"):
        shutil.move(str(new), out / new.name)
        print("wrote", out / new.name)
    shutil.rmtree(STAGE, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
