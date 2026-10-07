"""SEC353-J-01 — an undeclared wire argument is refused at the MCP door, not dropped.

``D-IMPL-353`` residual R4, ruled with ``TP-04`` as one defect class
(``D-IMPL-361``; Global Constraint 7 of the TP-01…05 plan): **unknown wire
arguments are REFUSED, never dropped.** Measured against ``mcp==1.28.1`` before
this module existed, on the real egress door the product door builds
(``build_egress_server(expose_product_tool=True)``): a call to
:data:`~ccf_runtime.mcp.egress.PRODUCT_REQUEST_TOOL` carrying one argument its
schema does not name was SERVED, the resolver was reached, and the argument
vanished — FastMCP's argument model (``mcp/server/fastmcp/utilities/
func_metadata.py:48-66``) is a pydantic model with the default
``extra="ignore"``, ``call_fn_with_arg_validation`` (``:87-89``) dumps only the
declared fields, and ``FastMCP`` registers its low-level handler with
``validate_input=False`` (``server.py:308``), so nothing compares the call with
the advertised schema.

Two legs: the wire (a real MCP client session over the door's own ASGI app,
bearer-authenticated) proves the refusal reaches a client as an error naming the
key with the resolver untouched; the in-process call proves the refusal is the
typed :class:`~ccf.skills._wire_arguments.UndeclaredArgumentRefused`, not
whatever prose a wrapper happened to print. Each carries its positive control.

Tenant, principal, scope and argument names are test deployment vocabulary.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import anyio
import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken

from crossproc.servers.mcp_egress_child import build_servable_product
from ccf_runtime.mcp.auth import TokenGrant
from ccf_runtime.mcp.egress import PRODUCT_REQUEST_TOOL
from ccf_runtime.mcp.tenancy import tenant_claims
from tests.mcp.test_egress_parameters import (
    PRINCIPAL,
    SCOPE,
    _drive_mcp,
    _mcp_server,
    _tool_arguments,
    _tool_operation,
)

#: A key :data:`PRODUCT_REQUEST_TOOL`'s schema does not name. Test vocabulary.
UNDECLARED = "not_declared_by_this_tool"


@pytest.fixture(scope="module")
def assembled(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """One assembled, gate-admitted product (a local SQLite fabric, no estate)."""
    return build_servable_product(
        database_path=tmp_path_factory.mktemp("undeclared-wire") / "door.sqlite3"
    )


def _ask_over_the_wire(
    assembled: Any, root: Path, extra: dict[str, Any]
) -> tuple[bool, str, int]:
    """One bearer-authenticated tool call; (is_error, text, resolver calls)."""
    carried: list[Any] = []
    server = _mcp_server(
        root, servable=assembled.served, address=assembled.address, carried=carried
    )
    arguments = {**_tool_arguments(assembled.address, None), **extra}
    is_error, detail = _drive_mcp(server, _tool_operation(arguments))
    return is_error, detail, len(carried)


def test_over_the_wire_an_undeclared_argument_is_refused_naming_the_key(
    assembled: Any, tmp_path: Path
) -> None:
    """SEC353-J-01: the client gets an error naming the key; nothing is resolved."""
    is_error, detail, resolved = _ask_over_the_wire(
        assembled, tmp_path, {UNDECLARED: "smuggled"}
    )

    assert is_error is True, f"the undeclared argument was served: {detail[:200]}"
    assert UNDECLARED in detail
    assert resolved == 0, "the door reached the resolver before refusing"


def test_over_the_wire_the_control_a_declared_call_is_served(
    assembled: Any, tmp_path: Path
) -> None:
    """The positive control: the identical call minus the extra key is served."""
    is_error, detail, resolved = _ask_over_the_wire(assembled, tmp_path, {})

    assert is_error is False, detail
    assert resolved == 1


def _in_process(assembled: Any, root: Path, extra: dict[str, Any]) -> Any:
    """Call the registered tool through FastMCP's own ``call_tool``.

    Under the auth context the bearer middleware would populate, for the
    tenant the door's credential carries.
    """
    carried: list[Any] = []
    server = _mcp_server(
        root, servable=assembled.served, address=assembled.address, carried=carried
    )
    grant = TokenGrant(
        client_id=PRINCIPAL,
        scopes=(SCOPE,),
        tenants=frozenset({assembled.address.tenant}),
    )
    reset = auth_context_var.set(
        AuthenticatedUser(
            AccessToken(
                token="in-process",
                client_id=grant.client_id,
                scopes=list(grant.scopes),
                claims=dict(tenant_claims(grant)),
            )
        )
    )
    try:
        arguments = {**_tool_arguments(assembled.address, None), **extra}
        return anyio.run(server.call_tool, PRODUCT_REQUEST_TOOL, arguments), carried
    finally:
        auth_context_var.reset(reset)


def test_in_process_the_refusal_is_typed_and_names_the_key(
    assembled: Any, tmp_path: Path
) -> None:
    """The refusal under FastMCP's wrapper is ``UndeclaredArgumentRefused``."""
    from ccf.skills._wire_arguments import UndeclaredArgumentRefused

    with pytest.raises(Exception) as raised:
        _in_process(assembled, tmp_path, {UNDECLARED: "smuggled"})

    seen: list[BaseException] = []
    current: BaseException | None = raised.value
    while current is not None and current not in seen:
        seen.append(current)
        current = current.__cause__ or current.__context__
    typed = [error for error in seen if isinstance(error, UndeclaredArgumentRefused)]
    assert typed, f"no typed refusal under {[type(e).__name__ for e in seen]}"
    assert typed[0].undeclared == (UNDECLARED,)
    assert typed[0].surface == PRODUCT_REQUEST_TOOL


def test_in_process_the_control_a_declared_call_is_served(
    assembled: Any, tmp_path: Path
) -> None:
    """The positive control for the typed leg."""
    (_, structured), carried = _in_process(assembled, tmp_path, {})

    assert len(carried) == 1
    assert json.loads(structured["result"])["answered"]


def test_the_advertised_schema_states_the_closed_world(
    assembled: Any, tmp_path: Path
) -> None:
    """What ``tools/list`` advertises is what the door enforces.

    Supplementary to the two refusal legs: the refusal is the enforcement, and
    ``additionalProperties: false`` on the advertised ``inputSchema`` is the
    statement of it a client can read before calling.
    """
    server = _mcp_server(
        tmp_path, servable=assembled.served, address=assembled.address, carried=[]
    )
    listed = {tool.name: tool for tool in anyio.run(server.list_tools)}

    assert listed[PRODUCT_REQUEST_TOOL].inputSchema.get("additionalProperties") is False
