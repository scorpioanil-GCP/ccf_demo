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

import json
import os
import sys
from pathlib import Path

import pytest

from tests.perf_smoke.bounded import run_bounded

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Hard per-suite subprocess timeout in seconds (T-11-14): generous against
#: the measured smoke wall times, but a hang fails loudly instead of wedging
#: the always-on job.
SUITE_TIMEOUT_SECONDS = 300

#: Grace given to a timed-out suite's process group after SIGTERM before
#: escalating to SIGKILL (mirrors the crossproc fixture's own discipline).
KILL_GRACE_SECONDS = 10

#: The four battery suites under ``perf/suites/`` (D-25 taxonomy).
SUITES = (
    "micro",
    "scale",
    # D-IMPL-265 / carry row 24.7-C-02: the crossproc suite spawns
    # archive/examples/04-cross-process/producer_child.py — retired usage model,
    # non-gating until a phase re-points it at a supported child.
    pytest.param("crossproc", marks=pytest.mark.archived),
    "replay",
)


#: Where each case's evidence is written as it finishes, when set (the hosted diagnostic sets it;
#: ``GROK-BRIEF-9`` §4). One JSON line per case is appended and flushed at once, so a run that is
#: cut off still leaves the cases that completed — where the runner lets the files be read.
EVIDENCE_DIR_VARIABLE = "CCF_PERF_SMOKE_EVIDENCE_DIR"

#: Lines of the suite's own output kept in a failure message.
TAIL_LINES = 200


def _tail(text: str) -> str:
    return "\n".join(text.splitlines()[-TAIL_LINES:])


@pytest.mark.parametrize("suite", SUITES)
def test_suite_runs_untimed(suite: str, tmp_path: Path) -> None:
    """Run one suite once, untimed; fail on a timeout, a non-zero exit or a leaked process.

    Every wait in the cleanup is timed (``tests/perf_smoke/bounded.py``): a case is designed to return within
    ``SUITE_TIMEOUT_SECONDS + KILL_GRACE_SECONDS + KILL_GRACE_SECONDS`` plus scheduling slack,
    except for the two limits ``bounded.py`` discloses (the ``/proc`` scan is not itself timed; a
    descendant that leaves the group and clears its environment is not found). The 300 s per-suite
    cap is unchanged (Dave, 2026-10-11).
    """
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
    evidence = os.environ.get(EVIDENCE_DIR_VARIABLE)
    out_dir = Path(evidence) / suite if evidence else tmp_path
    result = run_bounded(
        [sys.executable, "-m", "pytest", f"perf/suites/{suite}", "-q", "--benchmark-disable", "-x"],
        cwd=REPO_ROOT,
        env=env,
        timeout=SUITE_TIMEOUT_SECONDS,
        term_grace=KILL_GRACE_SECONDS,
        reap=KILL_GRACE_SECONDS,
        out_dir=out_dir,
    )
    if result.timed_out:
        outcome = "timed_out"
    elif result.returncode != 0:
        outcome = "failed"
    elif result.survivors:
        outcome = "leaked"
    else:
        outcome = "passed"
    if evidence:
        record = {
            "suite": suite,
            "outcome": outcome,
            "elapsed_seconds": round(result.elapsed, 3),
            "cap_seconds": SUITE_TIMEOUT_SECONDS,
            "returncode": result.returncode,
            "ladder": result.ladder,
            "survivors": result.survivors,
            "last_line": (result.stdout.strip().splitlines() or [""])[-1],
        }
        with (Path(evidence) / "cases.jsonl").open("a") as handle:
            handle.write(json.dumps(record) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    detail = (
        f"elapsed {result.elapsed:.1f}s against a {SUITE_TIMEOUT_SECONDS}s cap; ladder {result.ladder or ['none']};"
        f" exit {result.returncode}; survivors {result.survivors or 'none'}\n"
        f"--- stdout (last {TAIL_LINES} lines) ---\n{_tail(result.stdout)}\n"
        f"--- stderr (last {TAIL_LINES} lines) ---\n{_tail(result.stderr)}"
    )
    if outcome == "timed_out":
        pytest.fail(f"perf suite '{suite}' timed out after {SUITE_TIMEOUT_SECONDS}s; its process group was reaped; {detail}")
    assert outcome != "failed", f"perf suite '{suite}' failed under --benchmark-disable; {detail}"
    assert outcome != "leaked", f"perf suite '{suite}' passed but left processes running, now killed; {detail}"
