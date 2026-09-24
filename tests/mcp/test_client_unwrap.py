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
