"""Run a perf suite in its own session and reap it — the smoke harness's run-and-reap step.

Moved out of ``test_smoke.py`` unchanged in behavior (``D-IMPL-380``, 2026-10-11 07:32,
``GROK-BRIEF-9`` §3) so the cleanup can be driven directly with small allowances.
"""

from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BoundedResult:
    """What one run produced, and how far the cleanup ladder had to go."""

    timed_out: bool
    returncode: int | None
    elapsed: float
    stdout: str
    stderr: str
    ladder: list[str] = field(default_factory=list)
    survivors: list[tuple[int, str]] = field(default_factory=list)


def run_bounded(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: float,
    term_grace: float,
    reap: float,
    out_dir: Path,
) -> BoundedResult:
    """The pre-``GROK-BRIEF-9`` cleanup, verbatim in shape: pipes, then an untimed final read."""
    start = time.monotonic()
    proc = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    ladder: list[str] = []
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return BoundedResult(False, proc.returncode, time.monotonic() - start, stdout, stderr, ladder)
    except subprocess.TimeoutExpired:
        ladder.append("timeout")
        group = os.getpgid(proc.pid)
        try:
            os.killpg(group, signal.SIGTERM)
            ladder.append("term")
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=term_grace)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(group, signal.SIGKILL)
                ladder.append("kill")
            except ProcessLookupError:
                pass
        stdout, stderr = proc.communicate()
        ladder.append("reaped")
        return BoundedResult(True, proc.returncode, time.monotonic() - start, stdout, stderr, ladder)
