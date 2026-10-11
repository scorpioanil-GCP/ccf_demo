"""Run a perf suite in its own session and reap it within a stated allowance — ``GROK-BRIEF-9`` §2.

``D-IMPL-380``, 2026-10-11 07:13 and 07:32 (Dave). The earlier cleanup read the suite's output
through pipes and, after killing the process group, called ``communicate()`` with no timeout; a
descendant that had left the group and still held a pipe kept that read waiting indefinitely
(reproduced: the direct child reaped at 3.0 s, the read still blocked at a 40 s bound).

Here:

1. **No pipes.** Output goes to two files under ``out_dir``. Nothing waits for a writer to close
   anything, so a descendant holding an inherited file cannot block the harness.
2. **Every wait is bounded.** ``wait(timeout)``; on expiry SIGTERM to the group and
   ``wait(term_grace)``; then SIGKILL and ``wait(reap)``. The **allowance** for one run is
   ``timeout + term_grace + reap``, plus scheduling slack.
3. **Escaped descendants are looked for, killed and named.** The child's environment carries a
   unique marker (``CCF_PERF_SMOKE_RUN``); after the run, ``/proc/*/environ`` is scanned for it and
   any process still carrying it is SIGKILLed and returned in ``survivors``. This *assists*
   cleanup and is **not a universal guarantee** (Dave, 07:32): a descendant that replaces its own
   environment, or one whose ``environ`` cannot be read, is not found by it.
"""

from __future__ import annotations

import os
import signal
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

MARKER_VARIABLE = "CCF_PERF_SMOKE_RUN"


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


def _carrying(marker: str) -> list[tuple[int, str]]:
    """Every process whose environment holds ``marker``, with its command line (best effort)."""
    needle = f"{MARKER_VARIABLE}={marker}".encode()
    found: list[tuple[int, str]] = []
    own = os.getpid()
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == own:
            continue
        try:
            if needle not in (entry / "environ").read_bytes():
                continue
            cmdline = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
        except OSError:
            continue
        found.append((int(entry.name), cmdline))
    return found


def _kill_carriers(marker: str) -> list[tuple[int, str]]:
    survivors = _carrying(marker)
    for pid, _ in survivors:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    return survivors


def _signal_group(group: int, signum: int) -> bool:
    try:
        os.killpg(group, signum)
        return True
    except ProcessLookupError:
        return False


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
    """Run ``argv`` in its own session; return within ``timeout + term_grace + reap`` plus slack."""
    out_dir.mkdir(parents=True, exist_ok=True)
    marker = uuid.uuid4().hex
    child_env = dict(env)
    child_env[MARKER_VARIABLE] = marker
    out_path, err_path = out_dir / f"run-{marker}.stdout", out_dir / f"run-{marker}.stderr"
    start = time.monotonic()
    ladder: list[str] = []
    with out_path.open("wb") as out, err_path.open("wb") as err:
        proc = subprocess.Popen(
            argv, cwd=cwd, env=child_env, stdout=out, stderr=err, stdin=subprocess.DEVNULL, start_new_session=True
        )
    group = proc.pid  # start_new_session: the child leads its own group
    timed_out = False
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        ladder.append("timeout")
        if _signal_group(group, signal.SIGTERM):
            ladder.append("term")
        try:
            proc.wait(timeout=term_grace)
        except subprocess.TimeoutExpired:
            if _signal_group(group, signal.SIGKILL):
                ladder.append("kill")
            try:
                proc.wait(timeout=reap)
            except subprocess.TimeoutExpired:
                ladder.append("not-reaped")
    if timed_out and proc.returncode is not None:
        ladder.append("reaped")
    # The group may still hold members whose leader has exited; and a descendant may have left it.
    _signal_group(group, signal.SIGKILL)
    survivors = _kill_carriers(marker)
    stdout = out_path.read_text(errors="replace")
    stderr = err_path.read_text(errors="replace")
    return BoundedResult(timed_out, proc.returncode, time.monotonic() - start, stdout, stderr, ladder, survivors)
