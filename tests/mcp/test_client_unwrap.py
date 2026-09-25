"""The client names the error it could not classify (Tier 1 join).

`McpServerUnreachable`'s own docstring is the standard this holds itself to:
*"An error the client cannot classify is an outage, not an absence, because an
outage invites a retry while a misreported absence gets written down."*

Tier 1 gave the MCP servers a mandatory tenancy floor that RAISES a named
refusal. anyio's task groups wrap that refusal in `ExceptionGroup`, sometimes
nested, so the fallback branch rendered `ExceptionGroup: unhandled errors in a
TaskGroup` and the named refusal never reached the operator. The classification
is deliberately broad (D-IMPL ruling: an auth refusal is a fact about reaching
the server); what is NOT deliberate is writing down a sentence that names
nothing.
"""

from __future__ import annotations

import pytest

from ccf.mcp.client import _unwrap_exception_group


def test_a_bare_exception_is_its_own_cause() -> None:
    error = ValueError("plain")
    assert _unwrap_exception_group(error) is error


def test_a_single_member_group_yields_the_member() -> None:
    inner = ValueError("named refusal")
    group = ExceptionGroup("task group", [inner])
    assert _unwrap_exception_group(group) is inner


def test_a_nested_single_member_group_yields_the_innermost() -> None:
    inner = ValueError("named refusal")
    group = ExceptionGroup("outer", [ExceptionGroup("inner", [inner])])
    assert _unwrap_exception_group(group) is inner


def test_a_multi_member_group_is_left_alone() -> None:
    """Two concurrent failures have no single cause to name, and picking one
    would be a guess presented as a fact."""
    group = ExceptionGroup("two", [ValueError("a"), KeyError("b")])
    assert _unwrap_exception_group(group) is group


def test_a_classified_client_error_raised_inside_the_session_keeps_its_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`SEC353-J-02`: an error the client CAN classify is the answer, not a symptom.

    `run_with_session` wrapped every exception from the operation as
    `McpServerUnreachable`, so a tool that reported an error — a door refusing at
    its tenancy floor (`SEC-018`) — reached `dispatch_skill` as unreachability and
    its `tool-error` branch (and the `McpTimeout` branch) could never fire. A
    `McpClientError` raised inside the session propagates as ITSELF, bare or
    inside the single-member exception group the transport's task group wraps it
    in; only an error the client cannot classify is the fallback.
    """
    import asyncio
    import contextlib

    import ccf.mcp.client as client_module
    from ccf.mcp.errors import McpServerUnreachable, McpTimeout, McpToolFailed

    @contextlib.asynccontextmanager
    async def transport(url: str, http_client: object = None):  # type: ignore[no-untyped-def]
        yield (object(), object(), lambda: None)

    class Session:
        def __init__(self, read: object, write: object) -> None:
            pass

        async def __aenter__(self) -> "Session":
            return self

        async def __aexit__(self, *exc: object) -> bool:
            return False

        async def initialize(self) -> None:
            return None

    monkeypatch.setattr(client_module, "streamable_http_client", transport)
    monkeypatch.setattr(client_module, "ClientSession", Session)

    def run(error: BaseException) -> object:
        async def operation(session: object) -> object:
            raise error

        return asyncio.run(client_module.run_with_session(url="http://fixture/mcp", operation=operation))

    refused = McpToolFailed("request_context_product", "the verified caller's grant does not carry tenant 'x' (SEC-018)")
    timed_out = McpTimeout("no answer within the budget")
    for raised, expected in (
        (refused, McpToolFailed),
        (timed_out, McpTimeout),
        (ExceptionGroup("task group", [refused]), McpToolFailed),
    ):
        with pytest.raises(expected) as caught:
            run(raised)
        assert caught.value is refused or caught.value is timed_out, caught.value
    # The positive control: an UNCLASSIFIED error is still the fallback, named.
    with pytest.raises(McpServerUnreachable) as fallback:
        run(RuntimeError("boom"))
    assert type(fallback.value) is McpServerUnreachable and "RuntimeError" in str(fallback.value)
