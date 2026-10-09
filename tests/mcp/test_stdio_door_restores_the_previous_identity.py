"""Item 9 (b) (``D-IMPL-378``, Dave, 2026-10-08 21:24 MST): ``serve_stdio`` restores the previous login identity.

``runtime/ccf_runtime/mcp/product_door.py::ProductDoor.serve_stdio`` sets the MCP library's login identity,
``auth_context_var``, to the identity its caller composed, before the stdio server starts. Stdio carries no
authentication channel, so while the server runs that one identity answers for every caller of the process. The door
never reset the variable, so after ``serve_stdio`` left, by any path, whatever the process did next still ran as the
stdio identity. The ruling, verbatim: *"b. Restore the previous login identity in finally; verify normal return,
exception and cancellation."*

Every test here drives the REAL stdio transport: ``FastMCP.run`` -> ``anyio.run`` -> ``FastMCP.run_stdio_async`` ->
``mcp.server.stdio.stdio_server``, which reads ``sys.stdin.buffer`` and writes ``sys.stdout.buffer``; both are
replaced by in-memory streams. The three ways out of the call:

* **normal return**: standard input is at end of file, so the transport reads it and returns;
* **exception**: reading standard input raises ``OSError`` inside the transport, and ``serve_stdio`` raises the
  transport's ``ExceptionGroup`` holding that very error;
* **cancellation**: the transport's first read of standard input delivers ``asyncio`` cancellation to the task that is
  serving, and ``serve_stdio`` raises ``asyncio.CancelledError``.

Each runs twice: with a PRIOR identity set before the call, so that "restored" is tested as "the previous identity"
and not as "cleared", and with none set. The variable is read directly: before the call, during it (by a wrapper
around ``FastMCP.run_stdio_async`` that records it and then runs the transport unchanged, which holds the documented
process-scoped behavior while the server runs), and after it. Each case runs in a fresh ``contextvars.Context``, so
nothing a case sets reaches another test, even when the restore is severed.

Fixture vocabulary only (CINV-01).
"""

from __future__ import annotations

import asyncio
import contextvars
import errno
import io
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken
from mcp.server.fastmcp import FastMCP

from ccf_runtime.mcp.product_door import ProductDoor, open_door
from ccf_runtime.mcp.tenancy import ambient_stdio_identity
from tests.mcp.test_product_door_composition import _Product

#: Stdio reads neither advertised address (C2-A (b), ``D-IMPL-378``): the door needs only its credential.
ENVIRON = {"DOOR_TOKEN": "t"}

#: The two states the variable can be in when the call begins.
PRIOR_STATES = ("a-prior-identity", "no-prior-identity")


@dataclass
class _Serving:
    """What the transport saw while it served: the task serving, its loop, the login identity, its reads."""

    task: asyncio.Task[object] | None = None
    loop: asyncio.AbstractEventLoop | None = None
    identity: object = None
    reads: int = 0


@dataclass(frozen=True)
class _Outcome:
    """The variable before and after the call, what was passed, and how the call left."""

    prior: AuthenticatedUser | None
    before: AuthenticatedUser | None
    passed: AuthenticatedUser
    raised: BaseException | None
    after: AuthenticatedUser | None


class _Stdin(io.RawIOBase):
    """The bytes under ``sys.stdin.buffer``; ``on_read`` decides what each of the transport's reads gets."""

    def __init__(self, on_read: Callable[[], int]) -> None:
        super().__init__()
        self._on_read = on_read

    def readable(self) -> bool:
        return True

    def readinto(self, buffer: object) -> int:
        return self._on_read()


@pytest.fixture
def serving(monkeypatch: pytest.MonkeyPatch) -> Iterator[_Serving]:
    """Observe the transport from inside: wrap ``FastMCP.run_stdio_async``, record, then run it unchanged."""
    observed = _Serving()
    transport = FastMCP.run_stdio_async

    async def _observed(self: FastMCP) -> None:
        observed.task = asyncio.current_task()
        observed.loop = asyncio.get_running_loop()
        observed.identity = auth_context_var.get()
        await transport(self)

    monkeypatch.setattr(FastMCP, "run_stdio_async", _observed)
    yield observed


def _a_prior_identity() -> AuthenticatedUser:
    """Another login identity the process held before it served stdio."""
    return AuthenticatedUser(
        AccessToken(token="prior-credential", client_id="prior-principal", scopes=["prior:scope"])
    )


def _the_stdio_identity(door: ProductDoor) -> AuthenticatedUser:
    """The identity a caller composes for the stdio door, as every ``server/serve.py`` does."""
    return AuthenticatedUser(
        ambient_stdio_identity(
            credential=door.credential,
            principal_id=door.principal_id,
            scope=door.scope,
            tenant=door.tenant_id,
        )
    )


def _serve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, prior_state: str, on_read: Callable[[], int]
) -> _Outcome:
    """Serve stdio once over ``on_read``'s standard input, in a fresh context, and read the variable around it."""
    door = open_door(_Product(tmp_path), environ=ENVIRON)
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BufferedReader(_Stdin(on_read)), encoding="utf-8"))
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding="utf-8"))

    def _in_a_fresh_context() -> _Outcome:
        prior = _a_prior_identity() if prior_state == "a-prior-identity" else None
        if prior is not None:
            auth_context_var.set(prior)
        before = auth_context_var.get()
        passed = _the_stdio_identity(door)
        raised: BaseException | None = None
        try:
            door.serve_stdio(identity=passed)
        except (Exception, asyncio.CancelledError) as left:  # how it left is judged by each test
            raised = left
        return _Outcome(prior=prior, before=before, passed=passed, raised=raised, after=auth_context_var.get())

    return contextvars.Context().run(_in_a_fresh_context)


def _leaves(raised: BaseException) -> list[BaseException]:
    """Every exception inside ``raised``, through any exception groups."""
    if isinstance(raised, BaseExceptionGroup):
        return [leaf for inner in raised.exceptions for leaf in _leaves(inner)]
    return [raised]


def _who(identity: AuthenticatedUser | None) -> str:
    return "nothing" if identity is None else f"{identity.access_token.client_id!r}"


def _held_while_serving_and_restored_after(outcome: _Outcome, serving: _Serving, exit_path: str) -> None:
    assert outcome.before is outcome.prior, "the case was not constructed: the variable did not hold the prior state"
    assert serving.reads >= 1, f"the case was not constructed: the transport never read standard input ({exit_path})"
    assert serving.identity is outcome.passed, (
        f"while serving, the login identity was {_who(serving.identity)}, not the identity passed"
        f" ({_who(outcome.passed)}): stdio's one identity must answer for every caller while the server runs"
    )
    assert outcome.after is outcome.prior, (
        f"after serve_stdio left by {exit_path}, the login identity is {_who(outcome.after)}, not the previous one"
        f" ({_who(outcome.prior)}): the identity it set outlived the call"
    )


@pytest.mark.parametrize("prior_state", PRIOR_STATES)
def test_after_a_normal_return_the_previous_identity_is_restored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, serving: _Serving, prior_state: str
) -> None:
    def _end_of_file() -> int:
        serving.reads += 1
        return 0

    outcome = _serve(tmp_path, monkeypatch, prior_state, _end_of_file)

    assert outcome.raised is None, f"the transport did not return normally: {outcome.raised!r}"
    _held_while_serving_and_restored_after(outcome, serving, "a normal return")


@pytest.mark.parametrize("prior_state", PRIOR_STATES)
def test_after_an_exception_inside_the_transport_the_previous_identity_is_restored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, serving: _Serving, prior_state: str
) -> None:
    failure = OSError(errno.EIO, "the stdin pipe failed inside the transport")

    def _the_pipe_fails() -> int:
        serving.reads += 1
        raise failure

    outcome = _serve(tmp_path, monkeypatch, prior_state, _the_pipe_fails)

    assert isinstance(outcome.raised, ExceptionGroup), (
        f"serve_stdio did not raise the transport's exception group: {outcome.raised!r}"
    )
    assert any(leaf is failure for leaf in _leaves(outcome.raised)), (
        f"the exception that left serve_stdio is not the one raised inside the transport: {outcome.raised!r}"
    )
    _held_while_serving_and_restored_after(outcome, serving, "an exception")


@pytest.mark.parametrize("prior_state", PRIOR_STATES)
def test_after_cancellation_while_serving_the_previous_identity_is_restored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, serving: _Serving, prior_state: str
) -> None:
    def _cancel_the_serving_task() -> int:
        serving.reads += 1
        if serving.reads == 1:
            assert serving.loop is not None and serving.task is not None
            # Read in anyio's worker thread: the cancellation reaches the serving task through its own loop,
            # queued before this read's result, so the task is cancelled while the transport is serving.
            serving.loop.call_soon_threadsafe(serving.task.cancel)
        return 0

    outcome = _serve(tmp_path, monkeypatch, prior_state, _cancel_the_serving_task)

    assert isinstance(outcome.raised, asyncio.CancelledError), (
        f"serve_stdio did not leave by cancellation: {outcome.raised!r}"
    )
    _held_while_serving_and_restored_after(outcome, serving, "cancellation")
