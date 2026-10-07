"""TP-STDIO (EX-03 / EX-04, D-IMPL-361 §7.3): the stdio door never fabricates an identity.

``ProductDoor.serve_stdio`` used to compose an ``AuthenticatedUser`` from the
door's own ``credential``, ``principal_id``, ``scope`` and ``tenant_id`` and set
it for EVERY caller of the process. The ruling: the caller of the door composes
the ambient identity and passes it; the door states none of its own. Offline —
``FastMCP.run`` is stubbed so no transport starts.

What would fail here: a door that, asked to serve stdio with no identity, still
sets an authenticated context from its own fields (the defect as worded), or one
that sets anything other than exactly the identity it was handed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.fastmcp import FastMCP

from ccf_runtime.mcp.product_door import ProductDoor, open_door
from ccf_runtime.mcp.tenancy import ambient_stdio_identity
from tests.mcp.test_product_door_composition import PRINCIPAL, TENANT, _Product

ENVIRON = {
    "DOOR_TOKEN": "t",
    "DOOR_ISSUER": "https://issuer.invalid",
    "DOOR_RESOURCE": "https://resource.invalid",
}


@pytest.fixture
def seen(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    """What ``auth_context_var`` held at the instant the transport would start."""
    observed: list[object] = []

    def _run(self: FastMCP, transport: str = "stdio", **_: object) -> None:
        observed.append(auth_context_var.get())

    monkeypatch.setattr(FastMCP, "run", _run)
    return observed


def _door(tmp_path: Path) -> ProductDoor:
    return open_door(_Product(tmp_path), environ=ENVIRON)


def test_serve_stdio_with_no_identity_refuses_and_sets_no_context(
    tmp_path: Path, seen: list[object]
) -> None:
    door = _door(tmp_path)
    reset = auth_context_var.set(None)
    try:
        with pytest.raises(ValueError, match="D-IMPL-361") as refused:
            door.serve_stdio()  # type: ignore[call-arg]
        assert type(refused.value).__name__ == "StdioIdentityRequired"
        assert auth_context_var.get() is None, "the door fabricated an identity"
    finally:
        auth_context_var.reset(reset)
    assert seen == [], "the transport started without a caller-composed identity"


def test_serve_stdio_sets_exactly_the_identity_it_was_passed(
    tmp_path: Path, seen: list[object]
) -> None:
    door = _door(tmp_path)
    passed = AuthenticatedUser(
        ambient_stdio_identity(
            credential="caller-credential",
            principal_id="caller-principal",
            scope="caller:scope",
            tenant=TENANT,
        )
    )
    reset = auth_context_var.set(None)
    try:
        door.serve_stdio(identity=passed)
    finally:
        auth_context_var.reset(reset)
    assert seen == [passed]
    assert seen[0] is passed
    assert passed.access_token.client_id != PRINCIPAL, "not the door's own principal"
