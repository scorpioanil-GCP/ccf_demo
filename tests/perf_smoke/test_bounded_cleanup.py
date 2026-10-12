# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""The smoke harness's cleanup terminates within its stated allowance — ``GROK-BRIEF-9`` §3.

``D-IMPL-380``, 2026-10-11 07:13 and 07:32 (Dave): *"Include a test proving that cleanup
terminates within its stated allowance even when a child process ignores termination or keeps
an output pipe open."* Each case drives :func:`tests.perf_smoke.bounded.run_bounded` in a
**separate process under an outer timeout**, so a cleanup that blocks fails this test instead
of hanging the suite. Small allowances keep the cases to seconds.

The environment marker that finds escaped descendants *assists* cleanup; it is not a universal
guarantee (Dave, 07:32): a descendant that replaces its own environment is not found by it.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
#: The run's own timeout, the TERM-to-KILL grace and the KILL-to-reaped wait, kept small so each case takes seconds.
TIMEOUT = 1.0
TERM_GRACE = 1.0
REAP = 1.0
#: The stated allowance for one case, plus scheduling slack for a loaded runner.
ALLOWANCE = TIMEOUT + TERM_GRACE + REAP
SLACK = 3.0
OUTER = ALLOWANCE + SLACK + 12.0

IGNORES_TERM = "import signal, time\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\ntime.sleep(60)\n"
HOLDS_PIPE = textwrap.dedent(
    """
    import subprocess, sys, time
    subprocess.Popen([sys.executable, "-c",
        "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)"],
        start_new_session=True)
    time.sleep(60)
    """
)
BOTH = "import signal\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\n" + HOLDS_PIPE
CLEAN = "print('suite ran')\n"

DRIVER = textwrap.dedent(
    """
    import json, sys
    from pathlib import Path
    from tests.perf_smoke.bounded import run_bounded
    script, out_dir, marker = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
    import os
    env = dict(os.environ); env["CCF_PERF_SMOKE_TEST_MARKER"] = marker
    r = run_bounded([sys.executable, script], cwd=out_dir, env=env, timeout=float(sys.argv[4]),
                    term_grace=float(sys.argv[5]), reap=float(sys.argv[6]), out_dir=out_dir)
    print(json.dumps({"timed_out": r.timed_out, "returncode": r.returncode, "elapsed": r.elapsed,
                      "stdout": r.stdout, "ladder": r.ladder, "survivors": r.survivors}))
    """
)


def _marked_pids(marker: str) -> list[int]:
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if marker.encode() in (entry / "environ").read_bytes():
                found.append(int(entry.name))
        except OSError:
            continue
    return found


@pytest.fixture()
def marker(request: pytest.FixtureRequest) -> str:
    """A unique marker, and a teardown that kills anything still carrying it (a red run must not leak)."""
    value = f"bounded-cleanup-{os.getpid()}-{time.monotonic_ns()}-{request.node.name}"
    yield value
    for pid in _marked_pids(value):
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _drive(tmp_path: Path, marker: str, body: str) -> tuple[dict, float]:
    script = tmp_path / "child.py"
    script.write_text(body)
    driver = tmp_path / "driver.py"
    driver.write_text(DRIVER)
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(REPO_ROOT), env.get("PYTHONPATH", "")])
    env["CCF_PERF_SMOKE_TEST_MARKER"] = marker
    start = time.monotonic()
    try:
        done = subprocess.run(
            [sys.executable, str(driver), str(script), str(tmp_path), marker, str(TIMEOUT), str(TERM_GRACE), str(REAP)],
            cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=OUTER,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(f"cleanup did not terminate: the driver was still running after the {OUTER:.0f}s outer bound")
    wall = time.monotonic() - start
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout.strip().splitlines()[-1]), wall


def _within_allowance(result: dict) -> None:
    assert result["elapsed"] <= ALLOWANCE + SLACK, (
        f"cleanup took {result['elapsed']:.1f}s against an allowance of {ALLOWANCE:.0f}s (+{SLACK:.0f}s slack)"
    )


def test_a_child_that_ignores_termination_is_killed_within_the_allowance(tmp_path: Path, marker: str) -> None:
    result, _ = _drive(tmp_path, marker, IGNORES_TERM)
    assert result["timed_out"] is True
    assert "kill" in result["ladder"], result["ladder"]
    _within_allowance(result)
    assert _marked_pids(marker) == []


def test_a_descendant_holding_the_output_pipe_cannot_block_cleanup_and_is_named(tmp_path: Path, marker: str) -> None:
    result, _ = _drive(tmp_path, marker, HOLDS_PIPE)
    assert result["timed_out"] is True
    _within_allowance(result)
    assert result["survivors"], "the escaped descendant was not named"
    assert any("time.sleep(60)" in cmd for _, cmd in result["survivors"]), result["survivors"]
    assert _marked_pids(marker) == [], "the escaped descendant is still running after cleanup"


def test_both_at_once(tmp_path: Path, marker: str) -> None:
    result, _ = _drive(tmp_path, marker, BOTH)
    assert result["timed_out"] is True
    _within_allowance(result)
    assert result["survivors"]
    assert _marked_pids(marker) == []


def test_a_clean_suite_returns_its_output_and_leaves_no_survivor(tmp_path: Path, marker: str) -> None:
    result, _ = _drive(tmp_path, marker, CLEAN)
    assert result["timed_out"] is False and result["returncode"] == 0
    assert "suite ran" in result["stdout"]
    assert result["survivors"] == []
    assert _marked_pids(marker) == []


def _pids_with_argv_token(token: str) -> list[int]:
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if token.encode() in (entry / "cmdline").read_bytes():
                found.append(int(entry.name))
        except OSError:
            continue
    return found


def test_a_descendant_the_marker_cannot_find_still_cannot_block_cleanup(tmp_path: Path, marker: str) -> None:
    """The marker's stated limit, and why output goes to files rather than pipes.

    The grandchild leaves the group AND replaces its environment, so the marker scan cannot see
    it. Cleanup must still return within the allowance — nothing waits on its inherited output —
    and the result honestly names no survivor. The test's own teardown kills it by a token in its
    command line.
    """
    token = f"unfindable-{marker}"
    body = textwrap.dedent(
        f"""
        import subprocess, sys, time
        subprocess.Popen([sys.executable, "-c",
            "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)  # {token}"],
            start_new_session=True, env={{}})
        time.sleep(60)
        """
    )
    try:
        result, _ = _drive(tmp_path, marker, body)
        assert result["timed_out"] is True
        _within_allowance(result)
        assert result["survivors"] == [], "the marker cannot see a descendant that replaced its environment"
        assert _pids_with_argv_token(token), "the unfindable descendant should still be running here"
    finally:
        for pid in _pids_with_argv_token(token):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def test_a_descendant_left_in_the_group_after_a_clean_exit_is_reported_and_killed(tmp_path: Path, marker: str) -> None:
    """Review of b66ab4fa (F3): the post-run group kill used to remove an in-group leak silently,
    so a suite that left a process running reported ``passed``. A clean exit that leaves a member
    of its own process group must name it as a survivor."""
    body = textwrap.dedent(
        """
        import subprocess, sys, time
        subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])  # same group, same session
        time.sleep(0.3)
        """
    )
    result, _ = _drive(tmp_path, marker, body)
    assert result["timed_out"] is False and result["returncode"] == 0
    assert result["survivors"], "a process left in the suite's own group was killed without being reported"
    assert any("time.sleep(60)" in cmd for _, cmd in result["survivors"]), result["survivors"]
    assert _marked_pids(marker) == []


def test_a_group_member_the_marker_cannot_see_is_still_found(tmp_path: Path, marker: str) -> None:
    """The group scan is load-bearing on its own: a leftover in the suite's group that replaced its
    environment carries no marker, and is found because it is still a member of the group."""
    token = f"in-group-unmarked-{marker}"
    body = textwrap.dedent(
        f"""
        import subprocess, sys, time
        subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)  # {token}"], env={{}})
        time.sleep(0.3)
        """
    )
    try:
        result, _ = _drive(tmp_path, marker, body)
        assert result["returncode"] == 0
        assert any(token in cmd for _, cmd in result["survivors"]), result["survivors"]
        assert not _pids_with_argv_token(token), "the unmarked group member is still running"
    finally:
        for pid in _pids_with_argv_token(token):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
