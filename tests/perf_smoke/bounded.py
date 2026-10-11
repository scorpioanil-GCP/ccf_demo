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
3. **Leftover processes are found, killed and named.** After the run, two populations are looked
   for and returned in ``survivors``: members of the suite's own process group (a clean exit that
   left a child running is a leak, not a pass — review of ``b66ab4fa``), and processes carrying
   the run's unique environment marker (``CCF_PERF_SMOKE_RUN``), which finds descendants that
   left the group. Each is killed through a process file descriptor opened first and re-checked
   after, so a recycled process id is never signaled; no group signal is sent once the leader has
   been reaped. The marker *assists* cleanup and is **not a universal guarantee** (Dave, 07:32): a
   descendant that leaves the group AND replaces its own environment, or whose ``/proc`` entries
   cannot be read, is not found.

**Residual, stated:** the ``/proc`` reads are not themselves bounded by the allowance; reading a
process's ``environ`` waits on that process's memory lock, so a process stuck in uninterruptible
sleep can delay the scan (review of ``b66ab4fa``, R2).
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


def _group_of(pid: int) -> int | None:
    """The process group id of ``pid``, from ``/proc/<pid>/stat`` (field 5, after the parenthesized name)."""
    try:
        stat = (Path("/proc") / str(pid) / "stat").read_text()
    except OSError:
        return None
    fields = stat[stat.rfind(")") + 2 :].split()
    return int(fields[2]) if len(fields) > 2 else None


def _cmdline(pid: int) -> str:
    try:
        return (Path("/proc") / str(pid) / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
    except OSError:
        return ""


def _members(group: int) -> list[tuple[int, str]]:
    """Live members of process group ``group``. While any member lives, the kernel does not reuse its id."""
    own = os.getpid()
    return [
        (int(entry.name), _cmdline(int(entry.name)))
        for entry in Path("/proc").iterdir()
        if entry.name.isdigit() and int(entry.name) != own and _group_of(int(entry.name)) == group
    ]


def _carries(pid: int, marker: str) -> bool:
    try:
        return f"{MARKER_VARIABLE}={marker}".encode() in (Path("/proc") / str(pid) / "environ").read_bytes()
    except OSError:
        return False


def _kill_verified(pid: int, *, group: int, marker: str) -> None:
    """SIGKILL ``pid`` only if, after a pidfd pins it, it is still in ``group`` or still carries ``marker``."""
    try:
        pidfd = os.pidfd_open(pid)
    except OSError:
        return  # already gone
    try:
        if _group_of(pid) == group or _carries(pid, marker):
            signal.pidfd_send_signal(pidfd, signal.SIGKILL)
    except OSError:
        pass
    finally:
        os.close(pidfd)


def _leftovers(group: int, marker: str) -> list[tuple[int, str]]:
    found = dict(_members(group))
    found.update(dict(_carrying(marker)))
    for pid in found:
        _kill_verified(pid, group=group, marker=marker)
    return sorted(found.items())


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
    # No group signal after the leader is reaped: its id is only pinned while members live. The
    # members still alive, and marker carriers that left the group, are found, killed and named.
    survivors = _leftovers(group, marker)
    stdout = out_path.read_text(errors="replace")
    stderr = err_path.read_text(errors="replace")
    return BoundedResult(timed_out, proc.returncode, time.monotonic() - start, stdout, stderr, ladder, survivors)
