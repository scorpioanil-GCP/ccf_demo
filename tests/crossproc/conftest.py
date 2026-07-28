"""THE shared cross-process fixture (D-17): ephemeral port + stdout handshake.

Every cross-process proof in this phase — MCP egress, the MCP-backed
ArtifactStore, both A2A transports, the harness adapters — reuses this fixture
by supplying a *different child module*, never by copying the mechanics. That
is the whole point of it being here: the subprocess lifecycle, the port
allocation, and the readiness gate are exactly the three things that go subtly
wrong per-copy.

Two disciplines are load-bearing (D-15/D-16):

**Readiness is a handshake, never a sleep.** The child binds its own socket at
port ``0``, learns the OS-assigned port before the server starts, and prints
``READY {port}`` once its server reports started. The parent's *blocking*
``readline()`` is the gate. Nothing here sleeps, retries until it connects, or
polls — a sleep-gated test passes against a server that never started, which is
precisely the failure a cross-process suite exists to catch.

**Teardown is guaranteed.** ``terminate`` → ``wait(timeout)`` → ``kill`` runs
from a ``finally``, so a failing test body still reaps its child. An orphaned
server holds a port and a SQLite file and poisons every later test in the
session (T-06-17).

Ephemeral binding also removes the scan-then-bind race: nothing here picks a
port and hopes it is still free when the child gets to it.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

#: The stdout token a child prints once it is listening. Test-side protocol
#: vocabulary, shared by the fixture and every child module.
READY_TOKEN = "READY"

#: How long to wait for a terminated child to exit before escalating to kill.
TERMINATE_TIMEOUT_SECONDS = 10


@contextmanager
def spawn_child_server(child_module_path: Path) -> Iterator[int]:
    """Run ``child_module_path`` as a server subprocess; yield its port.

    Args:
        child_module_path: Absolute path to a child entry point that binds an
            ephemeral loopback port and prints ``READY {port}`` on stdout.

    Yields:
        The port the child bound.

    Raises:
        AssertionError: the child died before announcing, or announced
            something unparseable. The child's captured stderr is included —
            without it a child that raised at import surfaces as an opaque
            ``int('')`` failure and every debugging session starts by
            rediscovering that.
    """
    proc = subprocess.Popen(
        [sys.executable, str(child_module_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert proc.stdout is not None
        announcement = proc.stdout.readline().strip()
        if not announcement.startswith(f"{READY_TOKEN} "):
            _, stderr = proc.communicate(timeout=TERMINATE_TIMEOUT_SECONDS)
            raise AssertionError(
                f"{child_module_path.name} did not announce readiness "
                f"(got {announcement!r}); its stderr was:\n{stderr}"
            )
        yield int(announcement.split()[1])
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=TERMINATE_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        for stream in (proc.stdout, proc.stderr):
            if stream is not None:
                stream.close()


@pytest.fixture
def child_server_port(request: pytest.FixtureRequest) -> Iterator[int]:
    """Port of a running child server, chosen by indirect parametrization.

    Usage — the seam every later cross-process plan uses::

        @pytest.mark.parametrize("child_server_port", [CHILD], indirect=True)
        def test_something(child_server_port: int) -> None: ...

    ``request.param`` is the child module's path. Parametrized rather than
    hard-wired so adding a server means adding a module, not editing this
    fixture.
    """
    child_module_path = Path(request.param)
    with spawn_child_server(child_module_path) as port:
        yield port


@pytest.fixture
def loopback_url(child_server_port: int) -> str:
    """The child's streamable-HTTP endpoint on loopback.

    The address is assembled test-side. ``/src`` and ``/runtime`` hold no host
    and no port (CINV-01, T-06-14); the deployment — here, the test — chooses
    the interface, and choosing loopback is what keeps the proof off any
    routable one.
    """
    return f"http://127.0.0.1:{child_server_port}/mcp"
