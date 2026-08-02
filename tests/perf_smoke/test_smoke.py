"""Perf-tree bitrot smoke: every suite runs once, never timed (D-04).

The perf battery is excluded from the always-on collection (``perf/`` is its
own pytest rootdir; ``testpaths = ["tests"]``), so without this smoke a
refactor in ``/src`` or ``/runtime`` could silently break the suites between
opt-in dispatches. This module runs each suite in a subprocess with
``--benchmark-disable`` — pytest-benchmark's documented mode in which every
benchmarked callable executes **exactly once as a plain test** and nothing is
timed (RESEARCH assumption A3, confirmed against the installed
pytest-benchmark 5.2.3 ``--help`` text: "Benchmarked functions are only ran
once"). Correctness asserts (byte-exact replay reproduction, graph-shape
sanity checks) still fire; timing judgments never do — always-on CI never
times anything (D-IMPL-70).

Runtime containment:

* ``CCF_PERF_SMOKE=1`` collapses the scale and replay ladders to their
  smallest rung (see ``perf/suites/scale/conftest.py`` and
  ``perf/suites/replay/test_replay_scale.py``).
* Each subprocess carries a hard timeout so a hang fails the job instead of
  wedging it (threat T-11-14).
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Hard per-suite subprocess timeout in seconds (T-11-14): generous against
#: the measured smoke wall times, but a hang fails loudly instead of wedging
#: the always-on job.
SUITE_TIMEOUT_SECONDS = 300

#: Grace given to a timed-out suite's process group after SIGTERM before
#: escalating to SIGKILL (mirrors the crossproc fixture's own discipline).
KILL_GRACE_SECONDS = 10

#: The four battery suites under ``perf/suites/`` (D-25 taxonomy).
SUITES = ("micro", "scale", "crossproc", "replay")


@pytest.mark.parametrize("suite", SUITES)
def test_suite_runs_untimed(suite: str) -> None:
    env = dict(os.environ)
    # Mirror the Makefile's ENV_PERF (src:runtime:perf) plus the repo root so
    # package-style ``perf.*`` imports resolve from the subprocess.
    env["PYTHONPATH"] = os.pathsep.join(
        [
            str(REPO_ROOT / "src"),
            str(REPO_ROOT / "runtime"),
            str(REPO_ROOT / "perf"),
            str(REPO_ROOT),
        ]
    )
    # Smallest-rung-only parametrization for the ladder suites (D-04 knob).
    env["CCF_PERF_SMOKE"] = "1"
    env.setdefault("CCF_PERF_RUNNER_CLASS", "local")

    # The inner pytest gets its own session so a timeout can reap the WHOLE
    # process group: the crossproc suite's producer child is itself spawned
    # with ``start_new_session=True`` inside a group descended from this one,
    # and killing only the direct child would orphan it holding ports
    # (threat T-11-10) — its fixture ``finally`` never runs after a SIGKILL.
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "pytest",
            f"perf/suites/{suite}",
            "-q",
            "--benchmark-disable",
            "-x",
        ],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=SUITE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        # SIGTERM → wait(grace) → SIGKILL on the whole group, mirroring the
        # crossproc fixture's own teardown ladder, then fail loudly.
        group = os.getpgid(proc.pid)
        try:
            os.killpg(group, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=KILL_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(group, signal.SIGKILL)
            except ProcessLookupError:
                pass
        stdout, stderr = proc.communicate()
        pytest.fail(
            f"perf suite '{suite}' timed out after {SUITE_TIMEOUT_SECONDS}s; "
            "its process group was reaped\n"
            f"--- stdout ---\n{stdout}\n"
            f"--- stderr ---\n{stderr}"
        )
    assert proc.returncode == 0, (
        f"perf suite '{suite}' failed under --benchmark-disable "
        f"(exit {proc.returncode})\n"
        f"--- stdout ---\n{stdout}\n"
        f"--- stderr ---\n{stderr}"
    )
