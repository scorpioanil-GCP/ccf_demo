"""The shared door adapter: the standard door over a HAND-COMPOSED product (round 5, item 1).

**SDK-defined** (CLAUDE.md §7.1, §8.3, §11). Dave, 2026-10-11 20:19 MST: *"Build
the listed SDK repairs in one round. Scope: ... the shared door adapter ...
Preserve exact decimal meaning, authorization and record integrity."*

Round 3 wrote the same ~60-line ``ServesProducts`` conformer three times (cp-07,
cp-04, door-cp-05) because a deployment that composes its product by hand could
reach the standard door no other way after ``D-IMPL-353``.
:func:`ccf_runtime.mcp.composed_product.compose_for_door` is that conformer,
once. Held here over the real MCP door (ASGI, real bearer verification), with a
hand-written resolver standing in for a deployment's own governed path:

* the authorizer and scope mapping are derived exactly as the standard door
  derives them for a paved product (same key, pinned at the registered version);
* the deployment's DECLARED ``product_entitlement:`` is what is in force — the
  door registered no default over it;
* each declared principal is served under its OWN role;
* a principal with a valid credential and no declaration is refused
  ``principal-not-entitled`` on the record, and the resolver never runs;
* an unknown credential is refused at the verifier (HTTP 401).
"""

from __future__ import annotations

import asyncio
import os
import importlib
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from mcp.types import TextContent

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import ReplayMint
from ccf.client.wire import WireRequest
from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.leases import LOCK_DIRECTORY_SETTING, sdk_managed_lock_directory
from ccf.mcp.client import run_with_session
from ccf.mcp.errors import McpServerUnreachable
from ccf.products.contract import SUBJECT_WITHHOLDING_NEVER
from ccf.products.entitlement import product_entitlement_key
from ccf.products.product import open_product
from ccf.projection.plan import Perspective
from ccf.replay.record import DecisionReplayRecord
from ccf_runtime.authz.artifact import SCOPE_MAPPING
from ccf_runtime.mcp.auth import SourceBackedTokenVerifier, StaticTokenSource, TokenGrant
from ccf_runtime.mcp.egress import PRODUCT_REQUEST_TOOL
from ccf_runtime.mcp.product_door import open_door_with_verifier, scope_mapping_key

from tests.composition import declare_wide_temporal_boundary, declared_erasure_trust
from tests.products import paved_fixture as fixture

FULL = "principal-full"
NARROW = "principal-narrow"
UNDECLARED = "principal-undeclared"
FULL_ROLE = "role-full"
NARROW_ROLE = "role-narrow"
BASE_URL = "http://127.0.0.1:8141"
MODULE = "ccf_runtime.mcp.composed_product"


ABSENT = (
    "the SDK provides no shared door adapter for a hand-composed product; every"
    " such deployment writes its own ServesProducts conformer (round 3: cp-07,"
    " cp-04, door-cp-05)"
)


@pytest.fixture()
def composed_module() -> Any:
    """The SDK's shared adapter, or ``None`` — its absence is the defect this module measures.

    Asserted in each test body (``_present``) rather than here, so on an SDK
    without it every test FAILS by assertion instead of erroring at setup.
    """
    if importlib.util.find_spec(MODULE) is None:
        return None
    return importlib.import_module(MODULE)


def _present(value: Any) -> Any:
    assert value is not None, ABSENT
    return value


def _tree(tmp_path: Path) -> Path:
    return fixture.write_tree(
        tmp_path / "deployment",
        config=fixture.producer_config(
            subject_withholding=SUBJECT_WITHHOLDING_NEVER,
            product_entitlement={
                "tenant_id": fixture.PRODUCER_TENANT,
                "policy_version": fixture.CHILD_VERSION,
                "principals": {
                    FULL: {"permitted_schema_names": [fixture.CHILD_CLASS], "permitted_roles": [FULL_ROLE]},
                    NARROW: {"permitted_schema_names": [fixture.CHILD_CLASS], "permitted_roles": [NARROW_ROLE]},
                },
            },
        ),
        environment=fixture.producer_environment_text(),
    )


class _Deployment:
    """A hand-composed deployment: its own governed path, the SDK's shared adapter, the standard door."""

    def __init__(self, module: Any, tmp_path: Path) -> None:
        root = _tree(tmp_path)
        control_plane = ControlPlaneRegistry()
        declare_wide_temporal_boundary(control_plane, tenant_id=fixture.PRODUCER_TENANT)
        # The deployment's OWN governed path. A paved product stands in for the
        # hand-built assembler here; the door never sees it, only `resolve`.
        self.assembler = open_product(
            erasure_trust=declared_erasure_trust(fixture.PRODUCER_TENANT),
            config_root=root,
            scratch=tmp_path / "assembler",
            acquire=fixture.Acquire(),
            project=fixture.plan_factory,
            assess=fixture.assess,
            environ={fixture.CHILD_DSN_VAR: "postgresql://fixture"},
            control_plane=control_plane,
        )
        self.resolved: list[Perspective] = []

        def resolve(*, tenant: str, product_class: str, version: str, perspective: Perspective,
                    request: Any) -> Any:
            self.resolved.append(perspective)
            return self.assembler.resolve(tenant=tenant, product_class=product_class, version=version,
                                          perspective=perspective, request=request)

        replay_root = tmp_path / "door-replay"
        replay_root.mkdir(mode=0o700)
        boot_root = tmp_path / "door-boot"
        boot_root.mkdir()
        self.product = module.compose_for_door(
            root / "ccf_config.yaml",
            boot_connection={
                "database_path": str(boot_root / "boot.sqlite3"),
                LOCK_DIRECTORY_SETTING: sdk_managed_lock_directory(os.path.realpath(boot_root)),
            },
            environment_root=root,
            door=None,
            replay_store=FileArtifactStore(
                root=replay_root,
                write_kinds=WriteKinds.declare({fixture.RECORD_CLASS: (ReplayMint,)}),
            ),
            replay_record_class=fixture.RECORD_CLASS,
            resolver=resolve,
        )
        self.roles = {FULL: FULL_ROLE, NARROW: NARROW_ROLE, UNDECLARED: FULL_ROLE}
        scope = self.product.door.required_scope
        tenants = frozenset({self.product.tenant_id})
        source = StaticTokenSource(
            grants={
                f"token-{p}": TokenGrant(client_id=p, scopes=(scope,), tenants=tenants)
                for p in (FULL, NARROW, UNDECLARED)
            }
        )

        def perspective(*, grant: TokenGrant, tenant: str, requested_role: str | None) -> Perspective:
            del tenant, requested_role
            return Perspective(principal_id=grant.client_id, role=self.roles[grant.client_id])

        self.door = open_door_with_verifier(
            self.product,
            environ={fixture.CREDENTIAL_VAR: "door-boot-token"},
            token_verifier=SourceBackedTokenVerifier(source=source),
            perspective_resolver=perspective,
        )

    def close(self) -> None:
        self.assembler.close()

    def ask(self, token: str) -> dict[str, Any]:
        now = datetime.now(UTC)
        parameters = {fixture.THRESHOLD_PARAMETER: 1000}
        arguments = {
            "tenant": self.product.tenant_id,
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

    def record(self, outcome: dict[str, Any]) -> DecisionReplayRecord:
        reference = json.loads(outcome["text"])["replay_ref"]
        for store in (self.product.replay_store, self.assembler.artifact_store):
            try:
                address = store.resolve_uri(uri=reference)
            except Exception:  # noqa: BLE001 — the other store holds it
                continue
            return DecisionReplayRecord.model_validate_json(store.get(content_address=address))
        raise AssertionError(f"no store holds {reference}")


def _served(outcome: dict[str, Any]) -> bool:
    body = json.loads(outcome["text"]) if outcome["text"] else {}
    return (not outcome["is_error"]) and body.get("refusal") is None and bool(body.get("content_address"))


@pytest.fixture()
def deployment(composed_module: Any, tmp_path: Path) -> Any:
    if composed_module is None:
        yield None
        return
    built = _Deployment(composed_module, tmp_path)
    try:
        yield built
    finally:
        built.close()


def test_the_authorizer_and_scope_mapping_are_derived_as_for_a_paved_product(deployment: Any) -> None:
    deployment = _present(deployment)
    plane = deployment.product.control_plane
    tenant = deployment.product.tenant_id
    versions = plane.versions(scope_mapping_key(tenant_id=tenant))
    assert len(versions) == 1, versions
    mapping = plane.resolve(scope_mapping_key(tenant_id=tenant), versions[0])
    assert isinstance(mapping, SCOPE_MAPPING.contract)
    entry = mapping.scopes[deployment.product.door.required_scope]
    assert entry.tenant_patterns == (tenant,)
    assert entry.resource_patterns == (fixture.CHILD_CLASS,)
    # The authorizer is PINNED at the version that registration returned (SEC-002).
    assert deployment.door._authorizer.scope_mapping_version == versions[0]


def test_the_declared_entitlement_is_the_policy_in_force(deployment: Any) -> None:
    deployment = _present(deployment)
    plane = deployment.product.control_plane
    key = product_entitlement_key(tenant_id=deployment.product.tenant_id)
    versions = plane.versions(key)
    assert len(versions) == 1, versions  # the declared policy; no door default over it
    assert sorted(plane.resolve(key, versions[0]).principals) == sorted([FULL, NARROW])


def test_each_declared_principal_is_served_under_its_own_permissions(deployment: Any) -> None:
    deployment = _present(deployment)
    for principal in (FULL, NARROW):
        outcome = deployment.ask(f"token-{principal}")
        assert _served(outcome), (principal, outcome)
        assert deployment.resolved[-1] == Perspective(principal_id=principal, role=deployment.roles[principal])
        assert deployment.record(outcome).perspective_conditioning.role == deployment.roles[principal]


def test_an_undeclared_principal_is_refused_principal_not_entitled(deployment: Any) -> None:
    deployment = _present(deployment)
    before = len(deployment.resolved)
    outcome = deployment.ask(f"token-{UNDECLARED}")
    assert not _served(outcome), outcome
    assert len(deployment.resolved) == before, "the deployment's resolver ran for an unentitled caller"
    record = deployment.record(outcome)
    assert "principal-not-entitled" in record.content_generation_path.assembly_refusal
    assert record.perspective_conditioning.principal_id == UNDECLARED


def test_an_unknown_token_is_refused_401(deployment: Any) -> None:
    deployment = _present(deployment)
    outcome = deployment.ask("token-nobody-issued")
    assert outcome["is_error"] and "401" in outcome.get("unreachable", ""), outcome


def test_exactly_one_resolver_seam_is_required(composed_module: Any, tmp_path: Path) -> None:
    composed_module = _present(composed_module)
    root = _tree(tmp_path)
    with pytest.raises(ValueError, match="exactly one of resolver="):
        composed_module.compose_for_door(
            root / "ccf_config.yaml",
            boot_connection={"database_path": str(tmp_path / "boot.sqlite3")},
            environment_root=root,
            door=None,
            replay_store=FileArtifactStore(
                root=tmp_path / "r", write_kinds=WriteKinds.declare({fixture.RECORD_CLASS: (ReplayMint,)})
            ),
            replay_record_class=fixture.RECORD_CLASS,
        )
