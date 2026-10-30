"""Run the full test suite and save a readable log.

    python tools/run_tests.py     -> runs pytest -v, prints it, saves reports/test_log.txt,
                                     refreshes reports/l16p_predictions.md, and draws the
                                     figures from this run's saved data (run for record only)

The log is plain text so it reads cleanly in a browser on GitHub. It records
when the run happened, on what machine/Python, and every test's result.
"""

from __future__ import annotations

import datetime as dt
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "reports" / "test_log.txt"


def main() -> int:
    LOG.parent.mkdir(exist_ok=True)
    started = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "-p", "no:cacheprovider"],
        cwd=ROOT, capture_output=True, text=True)
    output = proc.stdout + proc.stderr
    header = (
        "Actuator Verification SIL: test log\n"
        f"Run (UTC):  {started}\n"
        f"Python:     {platform.python_version()} on {platform.system()}\n"
        f"Exit code:  {proc.returncode} (0 = all passed or expected-fail)\n"
        "Traceability matrix for this run: reports/traceability.md\n"
        + "=" * 78 + "\n"
    )
    LOG.write_text(header + output, encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT / "tools" / "predict_bench.py")],
                   cwd=ROOT, capture_output=True, text=True)
    print(output)
    print(f"Log saved to {LOG.relative_to(ROOT)}")
    fig = subprocess.run([sys.executable, str(ROOT / "tools" / "make_figures.py")],
                         cwd=ROOT, capture_output=True, text=True)
    if fig.returncode == 0:
        print("Figures drawn from this run's data: reports/figures/")
    else:
        print("Figures not drawn: " + (fig.stderr.strip() or fig.stdout.strip()))
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
