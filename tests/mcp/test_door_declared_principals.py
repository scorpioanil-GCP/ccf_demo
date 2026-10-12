"""Several principals on the standard door, declared as Control Plane data (G4-F-04).

**SDK-defined** (CLAUDE.md §11). Dave, 2026-10-11 16:23 MST, ruling 4: *"Preserve
separate principal permissions ... show the permitted case serving and the
corresponding unauthorized ... case refusing. Do not obtain success by bypassing a
gate or inventing a grant."*

Since ``D-IMPL-353`` a deployment cannot register its own entitlement policy (the
registry takes a capability only SDK composition code mints), so a door serving
several principals had no supported path. The path now: the deployment DECLARES
its ``ccf.product-entitlement-policy`` in ``ccf_config.yaml``
(``product_entitlement:``); ``open_product`` registers it at open under the
composition recipe; the standard door composes OVER it instead of replacing it
with its one-principal default.

Held here, over the real MCP door, in one module:

* each declared principal is served under ITS OWN role;
* a declared principal asking under a role it was not granted is refused;
* a principal holding a valid credential but absent from the declaration is
  refused;
* an unknown credential is refused at the verifier;
* a declaration naming another tenant, or a class this deployment does not serve,
  is refused by name at open — before anything is registered.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.client.wire import WireRequest
from ccf.products.contract import SUBJECT_WITHHOLDING_NEVER
from ccf.products.entitlement import product_entitlement_key
from ccf.products.product import open_product
from ccf.projection.plan import Perspective
from ccf_runtime.mcp.auth import SourceBackedTokenVerifier, StaticTokenSource, TokenGrant
from ccf_runtime.mcp.egress import PRODUCT_REQUEST_TOOL
from ccf_runtime.mcp.product_door import open_door_with_verifier

from tests.composition import declare_wide_temporal_boundary, declared_erasure_trust
from tests.products import paved_fixture as fixture

FULL = "principal-full"
NARROW = "principal-narrow"
UNDECLARED = "principal-undeclared"
FULL_ROLE = "role-full"
NARROW_ROLE = "role-narrow"
BASE_URL = "http://127.0.0.1:8137"


def _policy(*, tenant: str = fixture.PRODUCER_TENANT, classes: tuple[str, ...] = (fixture.CHILD_CLASS,)) -> dict[str, Any]:
    return {
        "tenant_id": tenant,
        "policy_version": fixture.CHILD_VERSION,
        "principals": {
            FULL: {"permitted_schema_names": list(classes), "permitted_roles": [FULL_ROLE]},
            NARROW: {"permitted_schema_names": list(classes), "permitted_roles": [NARROW_ROLE]},
        },
    }


def _open(tmp_path: Path, *, policy: dict[str, Any] | None) -> Any:
    overrides: dict[str, Any] = {}
    if policy is not None:
        overrides["product_entitlement"] = policy
    root = fixture.write_tree(
        tmp_path / "deployment",
        config=fixture.producer_config(subject_withholding=SUBJECT_WITHHOLDING_NEVER, **overrides),
        environment=fixture.producer_environment_text(),
    )
    control_plane = ControlPlaneRegistry()
    declare_wide_temporal_boundary(control_plane, tenant_id=fixture.PRODUCER_TENANT)
    return open_product(
        erasure_trust=declared_erasure_trust(fixture.PRODUCER_TENANT),
        config_root=root,
        scratch=tmp_path / "scratch",
        acquire=fixture.Acquire(),
        project=fixture.plan_factory,
        assess=fixture.assess,
        environ={fixture.CHILD_DSN_VAR: "postgresql://fixture"},
        control_plane=control_plane,
    )


class _Door:
    """The standard door over ``opened``, with the deployment's own verifier and role map."""

    def __init__(self, opened: Any) -> None:
        scope = opened.door.required_scope
        tenants = frozenset({opened.tenant_id})
        self.roles = {FULL: FULL_ROLE, NARROW: NARROW_ROLE, UNDECLARED: FULL_ROLE}
        source = StaticTokenSource(
            grants={
                f"token-{principal}": TokenGrant(client_id=principal, scopes=(scope,), tenants=tenants)
                for principal in (FULL, NARROW, UNDECLARED)
            }
        )

        def resolve(*, grant: TokenGrant, tenant: str, requested_role: str | None) -> Perspective:
            del tenant, requested_role
            return Perspective(principal_id=grant.client_id, role=self.roles[grant.client_id])

        self.opened = opened
        self.door = open_door_with_verifier(
            opened,
            environ={fixture.CREDENTIAL_VAR: "door-boot-token"},
            token_verifier=SourceBackedTokenVerifier(source=source),
            perspective_resolver=resolve,
        )

    def ask(self, token: str) -> dict[str, Any]:
        from mcp.types import TextContent

        from ccf.mcp.client import run_with_session
        from ccf.mcp.errors import McpServerUnreachable

        now = datetime.now(UTC)
        parameters = {fixture.THRESHOLD_PARAMETER: 1000}
        arguments = {
            "tenant": self.opened.tenant_id,
            "product_class": fixture.CHILD_CLASS,
            "version": fixture.CHILD_VERSION,
            "request": canonical_bytes(
                WireRequest(product_id=fixture.CHILD_CLASS, parameters=parameters, temporal_boundary=now)
            ).decode("utf-8"),
            "subject": "acct-1",
            "intent": "fixture-intent",
            "freshness": "fixture-freshness",
            "asked_at": now.isoformat(),
            "parameters": parameters,
        }
        app = self.door.server(
            issuer_url="https://issuer.invalid", resource_server_url=f"{BASE_URL}/mcp"
        ).streamable_http_app()

        async def operation(session: Any) -> Any:
            result = await session.call_tool(PRODUCT_REQUEST_TOOL, arguments)
            return {
                "is_error": bool(result.isError),
                "text": " | ".join(c.text for c in result.content if isinstance(c, TextContent)),
            }

        async def go() -> Any:
            async with app.router.lifespan_context(app):

                def factory() -> httpx.AsyncClient:
                    return httpx.AsyncClient(
                        transport=httpx.ASGITransport(app=app),
                        base_url=BASE_URL,
                        headers={"Authorization": f"Bearer {token}"},
                    )

                try:
                    return await run_with_session(
                        url=f"{BASE_URL}/mcp", operation=operation, http_client_factory=factory
                    )
                except McpServerUnreachable as refused:
                    return {"is_error": True, "unreachable": str(refused), "text": ""}

        return asyncio.run(go())


def _served(outcome: dict[str, Any]) -> bool:
    """A served answer: no tool error, no refusal, and a content address."""
    body = json.loads(outcome["text"]) if outcome["text"] else {}
    return (not outcome["is_error"]) and body.get("refusal") is None and bool(body.get("content_address"))


def _recorded(opened: Any, outcome: dict[str, Any]) -> tuple[str, str]:
    """``(cause recorded in dimension 5, perspective role recorded)`` behind a door outcome.

    The door discloses a refusal MINIMALLY to the caller (``subject-unavailable``),
    so the mechanism that refused is read where an auditor reads it: the record.
    """
    from ccf.replay.record import DecisionReplayRecord

    reference = json.loads(outcome["text"])["replay_ref"]
    store = opened.artifact_store
    record = DecisionReplayRecord.model_validate_json(
        store.get(content_address=store.resolve_uri(uri=reference))
    )
    return (
        record.content_generation_path.assembly_refusal,
        record.perspective_conditioning.role,
    )


# --- permitted --------------------------------------------------------------------------


def test_each_declared_principal_is_served_under_its_own_role(tmp_path: Path) -> None:
    with _open(tmp_path, policy=_policy()) as opened:
        door = _Door(opened)
        for principal in (FULL, NARROW):
            outcome = door.ask(f"token-{principal}")
            assert _served(outcome), (principal, outcome)
            assert _recorded(opened, outcome)[1] == door.roles[principal], principal
        # The policy in force is the DECLARED one, not the door's one-principal default.
        versions = opened.control_plane.versions(product_entitlement_key(tenant_id=opened.tenant_id))
        assert len(versions) == 1, versions


# --- refused, beside it -----------------------------------------------------------------


def test_a_declared_principal_asking_under_a_role_it_was_not_granted_is_refused(tmp_path: Path) -> None:
    with _open(tmp_path, policy=_policy()) as opened:
        door = _Door(opened)
        door.roles[NARROW] = FULL_ROLE  # the narrow principal now asks under the wider role
        outcome = door.ask(f"token-{NARROW}")
        assert not _served(outcome), outcome
        assert "product-role-ungranted" in _recorded(opened, outcome)[0], outcome


def test_a_credential_whose_principal_is_not_declared_is_refused(tmp_path: Path) -> None:
    with _open(tmp_path, policy=_policy()) as opened:
        outcome = _Door(opened).ask(f"token-{UNDECLARED}")
        assert not _served(outcome), outcome
        assert "principal-not-entitled" in _recorded(opened, outcome)[0], outcome


def test_an_unknown_credential_is_refused(tmp_path: Path) -> None:
    with _open(tmp_path, policy=_policy()) as opened:
        outcome = _Door(opened).ask("token-nobody-issued")
        assert outcome["is_error"], outcome


def test_without_the_declaration_only_the_doors_default_principal_is_entitled(tmp_path: Path) -> None:
    """The one-principal default is unchanged: the declared principals are NOT served."""
    with _open(tmp_path, policy=None) as opened:
        outcome = _Door(opened).ask(f"token-{FULL}")
        assert not _served(outcome), outcome
        assert "principal-not-entitled" in _recorded(opened, outcome)[0], outcome


def test_a_declaration_for_another_tenant_is_refused_at_open(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="its own tenant.s entitlements and no other"):
        _open(tmp_path, policy=_policy(tenant="someone-else"))


def test_a_declaration_granting_a_class_this_deployment_does_not_serve_is_refused_at_open(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="serves only"):
        _open(tmp_path, policy=_policy(classes=(fixture.CHILD_CLASS, "some.other-class")))
