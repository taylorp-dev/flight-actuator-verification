"""Bench link (L1): channel A from a real Raspberry Pi over a real Ethernet cable.

Two ways to feed these tests:

  python -m pytest tests/test_bench_link.py            replay the recordings in bench_data/
  python -m pytest tests/test_bench_link.py --live     drive the real Pi now

--live: pytest logs in to the Pi (SSH over Wi-Fi), starts the channel A sender,
records live over the Ethernet cable, and halfway through takes the Pi's
Ethernet port down for a few seconds and back up (automated cable pull). The
fresh recording is saved to bench_data/ (so CI replays the latest live run) and
the same tests below run on it.

While it records, a live monitor (sil/bench.py LiveMonitor) checks every word as
it arrives and re-checks validity every 1 ms, so the link loss is also caught
live, at real time. Its results are saved next to the recording, the tests below
check them as well as the replay, and L2 checks that live and replay agree.

    healthy.csv        part of the run before the link drop
    cable_pull.csv     the whole run, including the drop and recovery
    live_monitor.json  what the live checks saw during that same run

If no recording exists and --live isn't given, tests are skipped (verdict
NOT RUN), never passed. ARINC 429 is software-encoded; the physical layer is
Ethernet.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import platform
from pathlib import Path

import numpy as np
import pytest

from sil.arinc429 import SSM, decode_bnr
from sil.bench import LiveMonitor, PiRemote, capture_udp
from sil.link import ReplayChannel, label_lookup, label_of, read_capture, write_capture
from sil.receiver import Receiver
from sil.sim import label_defs, run_scenario
from sil.voter import Mode

ROOT = Path(__file__).resolve().parent.parent
BENCH = Path(os.environ.get("BENCH_DATA_DIR", ROOT / "bench_data"))
TRUE_PITCH = -2.0          # what tools/pi_channel_a.py sends by default
PULL_MIN_GAP_S = 0.5       # a gap this long in cable_pull.csv is the pull
REPLAY_MAX_S = 30.0        # cap closed-loop replay length to keep the suite fast


def run_live(cfg, opt) -> dict:
    """Automated live run against the real Pi. Returns {name: (rows, meta)}."""
    labels = label_defs(cfg)
    pi = PiRemote(target=opt.getoption("--pi"), data_host=opt.getoption("--data-host"))
    drop_at, drop_for = opt.getoption("--drop-at"), opt.getoption("--drop-for")
    record_s = drop_at + drop_for + 12.0
    pi.check_ready()
    pi_commit = pi.update_code()
    pi.stop_sender()
    monitor = LiveMonitor(labels, cfg["icd"]["stale_intervals"],
                          check_period_s=cfg["bench_link"]["live_check_period_s"])
    capman = opt.pluginmanager.getplugin("capturemanager")

    def show(t, n, value, valid, reasons):
        """Live status on the console while the run is going (not captured by pytest)."""
        txt = "VALID" if valid else "INVALID: " + ",".join(reasons)
        with capman.global_and_fixture_disabled():
            print(f"[live] t={t:5.1f} s  words {n:5d}  pitch {value:+7.3f} deg  {txt}", flush=True)

    def start():
        pi.start_sender(duration_s=record_s + 8.0)
        pi.schedule_link_drop(at_s=drop_at, for_s=drop_for)

    print(f"\n[live] Pi {pi.target} (code {pi_commit}) -> {pi.data_host}; "
          f"link drop at {drop_at:g} s for {drop_for:g} s; recording {record_s:g} s")
    try:
        rows, sender = capture_udp(labels, cfg["icd"]["stale_intervals"], record_s,
                                   after_bind=start, first_word_timeout_s=25.0,
                                   status=show, status_every_s=1.0, monitor=monitor)
    finally:
        pi.stop_sender()
        pi.link_up()
    pt = pitch_times(rows, labels)
    gaps = np.diff(pt)
    i = int(np.argmax(gaps)) if len(gaps) else 0
    if len(pt) and record_s - pt[-1] >= PULL_MIN_GAP_S:
        raise RuntimeError(f"live run: no words after {pt[-1]:.1f} s of {record_s:g} s, the link "
                           "never came back: check the Pi's network (BENCH-GUIDE troubleshooting)")
    if not len(gaps) or gaps[i] < PULL_MIN_GAP_S:
        raise RuntimeError("live run saw no link drop: check the sudo rule for 'ip link' on the Pi")
    healthy = [r for r in rows if r[0] < pt[i] - 0.5]
    meta = {
        "recorded_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "mode": "live, automated (pytest --live)",
        "sender": sender,
        "pi_ssh": pi.target,
        "pi_code": pi_commit,
        "receiver_host": platform.node(),
        "receiver_os": f"{platform.system()} {platform.release()}",
        "link": "direct Ethernet cable, UDP, one ARINC 429 word per datagram",
        "link_drop": f"Pi eth0 down at {drop_at:g} s for {drop_for:g} s (ip link set)",
        "recorded_s": record_s,
        "config_sha256_12": cfg["_hash"],
    }
    out = {"healthy": (healthy, {**meta, "capture": "healthy", "words": len(healthy),
                                 "note": "portion of the live run before the link drop"}),
           "cable_pull": (rows, {**meta, "capture": "cable_pull", "words": len(rows)})}
    for name, (r, m) in out.items():
        write_capture(BENCH / f"{name}.csv", r, m)
    live = {"meta": {**meta, "capture": "live_monitor",
                     "note": "results of the checks made live during the cable_pull run"},
            "results": monitor.results(PULL_MIN_GAP_S)}
    (BENCH / "live_monitor.json").write_text(json.dumps(live, indent=2))
    out["live"] = live
    return out


@pytest.fixture(scope="session")
def bench(request, cfg):
    if request.config.getoption("--live"):
        return run_live(cfg, request.config)
    out = {}
    for name in ("healthy", "cable_pull"):
        path = BENCH / f"{name}.csv"
        if path.exists():
            out[name] = read_capture(path)
    path = BENCH / "live_monitor.json"
    if path.exists() and "cable_pull" in out:
        live = json.loads(path.read_text())
        # only use live results recorded in the same run as the recording
        if live["meta"].get("recorded_utc") == out["cable_pull"][1].get("recorded_utc"):
            out["live"] = live
    return out


def _rel(p: Path) -> str:
    """Path of a recording as written in plot data: relative to the repo when it's inside it."""
    try:
        return Path(p).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def capture(bench, name: str):
    if name not in bench:
        pytest.skip(f"no bench recording {name}.csv yet: run with --live, "
                    f"or tools/bench_capture.py --name {name}")
    return bench[name]


def live_results(bench) -> dict | None:
    """Results of the live checks from the same run, or None (replay-only data)."""
    return bench["live"]["results"] if "live" in bench else None


def pitch_times(rows, labels):
    lookup = label_lookup(labels)
    return np.array([t for t, w in rows if lookup.get(label_of(w)) == "pitch"])


def receiver_trace(rows, cfg, labels, t_end, step=0.001):
    """Run the SIL receiver over the capture; return sample times and validity."""
    rx = Receiver(labels, stale_intervals=cfg["icd"]["stale_intervals"])
    lookup = label_lookup(labels)
    ts = np.arange(0.0, t_end, step)
    valid = np.zeros(len(ts), dtype=bool)
    i = 0
    for k, t in enumerate(ts):
        while i < len(rows) and rows[i][0] <= t:
            name = lookup.get(label_of(rows[i][1]))
            if name:
                rx.receive(name, rows[i][1], rows[i][0])
            i += 1
        valid[k] = rx.read("pitch", t)[0]
    return ts, valid


def replay_link_drop(cfg, rows, meta=None) -> dict:
    """Replay the cable-pull recording through the receiver (1 ms checks) and
    measure when the link loss was flagged and when it recovered, and how many
    times it went invalid anywhere else (false stale)."""
    labels = label_defs(cfg)
    pt = pitch_times(rows, labels)
    t_end = float((meta or {}).get("recorded_s", rows[-1][0]))   # newer recordings save it
    if t_end - pt[-1] >= PULL_MIN_GAP_S:
        pytest.fail(f"no words after {pt[-1]:.1f} s of a {t_end:g} s recording: "
                    "the link never came back")
    gaps = np.diff(pt)
    i = int(np.argmax(gaps))
    if gaps[i] < PULL_MIN_GAP_S:
        pytest.skip("cable_pull.csv has no gap: re-record and pull the cable mid-run")
    t_last, t_back = pt[i], pt[i + 1]
    ts, valid = receiver_trace(rows, cfg, labels, t_end)
    went_invalid = ts[(ts > t_last) & ~valid]
    back_valid = ts[(ts >= t_back) & valid]
    # invalid stretches outside the drop window (after the first valid sample)
    first_ok = int(np.argmax(valid)) if valid.any() else len(valid)
    outside = ~valid & ~((ts > t_last) & (ts <= t_back))
    outside[:first_ok] = False
    starts = int(np.sum(outside[1:] & ~outside[:-1]) + (1 if outside[0] else 0))
    return {
        "pitch_times": pt, "ts": ts, "valid": valid,
        "t_last": t_last, "t_back": t_back, "cable_out_s": float(gaps[i]),
        "flag_s": float(went_invalid[0] - t_last) if len(went_invalid) else None,
        "recover_s": float(back_valid[0] - t_back) if len(back_valid) else None,
        "false_stale_outside_drop": starts,
        "stale_limit_s": cfg["icd"]["stale_intervals"] / labels["pitch"].rate_hz,
    }


def replay(cfg, rows, duration):
    labels = label_defs(cfg)
    return run_scenario(cfg, duration_s=duration, pitch_fn=lambda t: TRUE_PITCH,
                        channel_override={0: ReplayChannel(rows, labels)})


# --------------------------------------------------------------- the words
@pytest.mark.req("ICD-1")
@pytest.mark.req("L1")
def test_l1_words_on_the_wire_decode_per_icd(cfg, bench, record_property):
    rows, meta = capture(bench, "healthy")
    labels = label_defs(cfg)
    lookup = label_lookup(labels)
    bad_label = [w for _, w in rows if label_of(w) not in lookup]
    decoded = [decode_bnr(w, labels[lookup[label_of(w)]]) for _, w in rows if label_of(w) in lookup]
    expect = TRUE_PITCH + cfg["sensors"]["bias_deg"][0]
    pitch = [d.value for (_, w), d in zip([r for r in rows if label_of(r[1]) in lookup], decoded)
             if lookup[label_of(w)] == "pitch"]
    record_property("words", len(rows))
    record_property("sender", meta.get("sender"))
    record_property("pitch_mean_deg", round(float(np.mean(pitch)), 3))
    assert not bad_label, f"{len(bad_label)} words with labels not in the ICD"
    assert all(d.parity_ok for d in decoded), "parity error on the wire"
    assert all(d.sdi == 1 for d in decoded), "channel A must send SDI 1"
    assert all(d.ssm == SSM.NORMAL for d in decoded)
    assert abs(np.mean(pitch) - expect) < 0.05
    live = live_results(bench)                       # same checks, made live during the run
    if live:
        record_property("live_decode_errors", sum(live["decode_errors"].values()))
        assert not any(live["decode_errors"].values()), f"live: {live['decode_errors']}"


# --------------------------------------------------------------- the timing
@pytest.mark.req("L1")
def test_l1_rate_and_jitter_on_real_link(cfg, bench, record_property):
    rows, _ = capture(bench, "healthy")
    labels = label_defs(cfg)
    ld = labels["pitch"]
    dt = np.diff(pitch_times(rows, labels))
    nominal = 1.0 / ld.rate_hz
    stale_limit = cfg["icd"]["stale_intervals"] / ld.rate_hz
    jitter = np.abs(dt - nominal)
    record_property("intervals", len(dt))
    record_property("mean_ms", round(float(dt.mean()) * 1000, 3))
    record_property("p99_jitter_ms", round(float(np.percentile(jitter, 99)) * 1000, 2))
    record_property("max_interval_ms", round(float(dt.max()) * 1000, 2))
    record_property("stale_limit_ms", round(stale_limit * 1000, 1))
    assert abs(dt.mean() - nominal) / nominal <= 0.02
    assert dt.max() < stale_limit, "a healthy-link gap would trip the stale check"
    live = live_results(bench)
    if live:                                         # how late the live checks themselves ran
        record_property("live_max_check_gap_ms", live["max_check_gap_ms"])


@pytest.mark.req("L1")
@pytest.mark.req("R3")
def test_l1_no_false_stale_on_healthy_link(cfg, bench, record_property):
    rows, _ = capture(bench, "healthy")
    labels = label_defs(cfg)
    ts, valid = receiver_trace(rows, cfg, labels, rows[-1][0])
    after_first = ts > 0.001
    record_property("invalid_samples", int((~valid[after_first]).sum()))
    assert valid[after_first].all()
    live = live_results(bench)
    if live:
        record_property("live_false_stale", live["false_stale_outside_drop"])
        assert live["false_stale_outside_drop"] == 0, "live check went stale on a healthy link"


# --------------------------------------------------------------- cable pull
@pytest.mark.req("L1")
@pytest.mark.req("R3")
def test_l1_cable_pull_flagged_stale_and_recovers(cfg, bench, record_property, plot_data):
    rows, meta = capture(bench, "cable_pull")
    d = replay_link_drop(cfg, rows, meta)
    pt = d["pitch_times"]
    src = {k: meta.get(k, "") for k in ("recorded_utc", "sender", "mode", "link_drop")}
    src["recording"] = _rel(BENCH / "cable_pull.csv")
    nominal_ms = 1000.0 / label_defs(cfg)["pitch"].rate_hz
    plot_data.save("bench_pitch_intervals", {"t_s": pt[1:], "interval_ms": np.diff(pt) * 1000.0},
                   nominal_interval_ms=nominal_ms, **src)
    plot_data.save("bench_receiver_valid", {"t_s": d["ts"], "ch_a_valid": d["valid"]},
                   t_last_word_s=d["t_last"],
                   t_back_s=d["t_back"], flag_s=d["flag_s"], recover_s=d["recover_s"],
                   stale_limit_s=d["stale_limit_s"], **src)
    record_property("cable_out_s", round(d["cable_out_s"], 2))
    record_property("flagged_after_ms", None if d["flag_s"] is None else round(d["flag_s"] * 1000, 1))
    record_property("recovered_after_reconnect_ms",
                    None if d["recover_s"] is None else round(d["recover_s"] * 1000, 1))
    assert d["flag_s"] is not None, "receiver never flagged the pulled link"
    assert d["flag_s"] <= d["stale_limit_s"] + 0.002
    assert d["recover_s"] is not None and d["recover_s"] <= 0.002, "no recovery after reconnect"
    live = live_results(bench)                       # the same link drop, caught live
    if live:
        tol_s = cfg["bench_link"]["live_vs_replay_tol_ms"] / 1000
        drop = live["link_drop"]
        assert drop and drop["flagged_after_ms"] is not None, "live check never flagged the link loss"
        record_property("live_flagged_after_ms", drop["flagged_after_ms"])
        record_property("live_recovered_after_reconnect_ms", drop["recovered_after_reconnect_ms"])
        assert drop["flagged_after_ms"] / 1000 <= d["stale_limit_s"] + tol_s
        assert drop["recovered_after_reconnect_ms"] is not None
        assert drop["recovered_after_reconnect_ms"] / 1000 <= tol_s, "live: no recovery after reconnect"


# --------------------------------------------------------------- closed loop
@pytest.mark.req("L1")
@pytest.mark.req("R5")
@pytest.mark.system
def test_l1_closed_loop_with_real_channel_a(cfg, bench, record_property):
    rows, _ = capture(bench, "healthy")
    dur = min(rows[-1][0], REPLAY_MAX_S)
    run = replay(cfg, rows, dur)
    settled = run.t > 0.2
    err = np.abs(run.voted[settled] - TRUE_PITCH)
    record_property("replayed_s", round(dur, 1))
    record_property("max_voted_error_deg", round(float(err.max()), 3))
    assert not run.failed
    assert all(m == Mode.TRIPLEX for m, s in zip(run.mode, settled) if s)
    assert err.max() <= cfg["voter"]["tolerance_deg"] + 0.35


@pytest.mark.req("L1")
@pytest.mark.req("R8")
@pytest.mark.req("R10")
@pytest.mark.system
def test_l1_closed_loop_cable_pull(cfg, bench, record_property, plot_data):
    rows, meta = capture(bench, "cable_pull")
    replay_link_drop(cfg, rows, meta)      # fails if the link never came back, skips if no drop
    dur = rows[-1][0]
    run = replay(cfg, rows, dur)
    channels = {"TRIPLEX": 3, "DUAL": 2, "SIMPLEX": 1, "FAIL": 0}
    plot_data.save("bench_voter_channels", {"t_s": run.t,
                                            "channels_in_use": [channels[m.value] for m in run.mode]},
                   recording=_rel(BENCH / "cable_pull.csv"), recorded_utc=meta.get("recorded_utc", ""))
    settled = run.t > 0.2
    modes = {m for m, s in zip(run.mode, settled) if s}
    law = cfg["command_law"]
    record_property("modes_seen", sorted(m.value for m in modes))
    record_property("ended_in", run.mode[-1].value)
    record_property("actuator_span_mm", round(float(np.ptp(run.pos[settled])), 3))
    assert Mode.DUAL in modes, "voter never dropped to dual while the cable was out"
    assert run.mode[-1] == Mode.TRIPLEX, "voter didn't return to triplex after reconnect"
    assert not run.failed, "a link loss must exclude channel A, not latch it failed"
    assert "DEGRADED_DUAL" in run.annunciations
    assert np.max(np.abs(run.cmd)) <= law["pos_limit_mm"] + 1e-9
    err = np.abs(run.voted[settled] - TRUE_PITCH)
    assert err.max() <= cfg["voter"]["tolerance_deg"] + 0.35


# --------------------------------------------------------------- live vs replay
@pytest.mark.req("L2")
def test_l2_live_vs_replay_agree(cfg, bench, record_property):
    """The checks made live during the run agree with the replay of the same recording."""
    live = live_results(bench)
    if live is None:
        pytest.skip("no live monitor results for this recording yet: run with --live")
    rows, meta = capture(bench, "cable_pull")
    labels = label_defs(cfg)
    lookup = label_lookup(labels)
    tol_ms = cfg["bench_link"]["live_vs_replay_tol_ms"]

    # same words: fingerprint of what the live checks saw vs the saved recording
    replay_sha = hashlib.sha256("".join(LiveMonitor.row_text(t, w) for t, w in rows).encode()).hexdigest()

    # replay side
    replay_errors = 0
    for _, w in rows:
        name = lookup.get(label_of(w))
        if name is None:
            replay_errors += 1
            continue
        dw = decode_bnr(w, labels[name])
        replay_errors += (not dw.parity_ok) + (dw.sdi != 1) + (dw.ssm != SSM.NORMAL)
    d = replay_link_drop(cfg, rows, meta)
    replay_false_stale = d["false_stale_outside_drop"]
    assert d["flag_s"] is not None and d["recover_s"] is not None, "replay saw no complete link drop"
    replay_flag_ms = d["flag_s"] * 1000
    replay_recover_ms = d["recover_s"] * 1000

    # live side
    drop = live["link_drop"]
    assert drop and drop["flagged_after_ms"] is not None \
        and drop["recovered_after_reconnect_ms"] is not None, "live checks saw no complete link drop"
    live_errors = sum(live["decode_errors"].values())
    diff_flag = abs(drop["flagged_after_ms"] - replay_flag_ms)
    diff_recover = abs(drop["recovered_after_reconnect_ms"] - replay_recover_ms)

    record_property("words_live_vs_replay", f"{live['words']} vs {len(rows)}")
    record_property("flag_ms_live_vs_replay", f"{drop['flagged_after_ms']} vs {replay_flag_ms:.1f}")
    record_property("recover_ms_live_vs_replay",
                    f"{drop['recovered_after_reconnect_ms']} vs {replay_recover_ms:.1f}")
    record_property("flag_diff_ms", round(diff_flag, 1))
    record_property("recover_diff_ms", round(diff_recover, 1))
    record_property("live_max_check_gap_ms", live["max_check_gap_ms"])
    record_property("false_stale_live_vs_replay", f"{live['false_stale_outside_drop']} vs {replay_false_stale}")
    record_property("tol_ms", tol_ms)

    assert live["words"] == len(rows), "live and recording saw a different number of words"
    assert live["words_sha256"] == replay_sha, "the saved recording is not what the live checks saw"
    assert live_errors == 0 and replay_errors == 0
    assert live["false_stale_outside_drop"] == 0 and replay_false_stale == 0
    assert diff_flag <= tol_ms, f"stale flag differs by {diff_flag:.1f} ms (tol {tol_ms} ms)"
    assert diff_recover <= tol_ms, f"recovery differs by {diff_recover:.1f} ms (tol {tol_ms} ms)"
