"""C-2 over MCP — a record decided under another tenant reads exactly as a missing address.

The MCP artifact server's split sends an address the caller's tenant never filed
to :func:`ccf_runtime.authz.delivery_boundary.govern_dereference` (the
``nonexistent`` shell for everything that is not a record this principal may
read). The independent review of the ``D-IMPL-376`` close-out (C-2) measured
that the governed dereference held the caller to the record's PRINCIPAL and
re-decided the grant under the record's TENANT, but compared the capability's
tenant with the record's nowhere — so another tenant's governed replay record
crossed to a caller whose principal id collided with the record's, and at
``full`` another tenant's record answered ``unauthorized`` where a missing
address answers ``nonexistent`` (a cross-tenant existence oracle).

The ruling (``D-IMPL-345`` R-2: held to the record's retained
principal/tenant/product identity): a record decided under any other tenant
answers exactly as a missing address does, at every disclosure level. Within the
caller's own tenant nothing changes. Each case asks the SAME address before the
other tenant files its record there and after, over the blob and presence
resources, and requires the same bytes.

Tenant, principal, class, scope and token names are test deployment
vocabulary, meaningful nowhere else (CINV-01 applied to test data).
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from typing import Any

import anyio
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import DerivedWrite
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.disclosure import DISCLOSURE_FULL
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.refusal import RefusalEnvelope
from ccf.products.request import ProductRequest
from ccf.replay.record import DecisionReplayRecord
from ccf_runtime.authz.product_entitlement import ControlPlaneProductEntitlementSource
from ccf_runtime.http_api.errors import ERROR_EVIDENCE_ABSENT, ERROR_EVIDENCE_PRINCIPAL_MISMATCH
from ccf_runtime.mcp.artifact_server import artifact_blob_uri, artifact_meta_uri, build_artifact_server
from ccf_runtime.mcp.auth import SourceBackedTokenVerifier, StaticTokenSource, TokenGrant
from tests.composition import declared_erasure_trust, no_erasures
from tests.http_api.composition_authority import (
    composition_replay_mint,
    deployment_store,
    refusal_recorder,
    register_typed_at_composition,
)
from tests.mcp.guarded_servers import (
    AUDIT_INSTANT,
    FOREIGN,
    PRINCIPAL,
    PRODUCT_CLASS,
    REPLAY_RECORD_CLASS,
    SCOPE,
    TENANT,
    authorizer_granting,
)
from tests.mcp.test_artifact_server_authorized import _as_grant

ROLE = "role-guard"

#: A principal of the other tenant that collides with no caller here.
OTHERS_OWN_PRINCIPAL = "c2-other-tenants-principal"

SURFACES = ("blob", "meta")


def _grant() -> TokenGrant:
    """The caller: ``PRINCIPAL``, whose grant names ONLY ``TENANT``."""
    return TokenGrant(client_id=PRINCIPAL, scopes=(SCOPE,), tenants=frozenset({TENANT}))


def _policy(tenant: str) -> ProductEntitlementPolicy:
    return ProductEntitlementPolicy(
        tenant_id=tenant,
        policy_version="1.0.0",
        principals={
            PRINCIPAL: ProductEntitlementGrant(
                permitted_schema_names=frozenset({PRODUCT_CLASS}),
                permitted_roles=frozenset({ROLE}),
                disclosure_level=DISCLOSURE_FULL,
            )
        },
        # Dave's Q12 (`D-IMPL-378`): owner read-back is default-deny behind an
        # explicit tenant class allowlist; this suite is about the tenant hold,
        # so its governed class is listed (and `_record` carries the affirmation).
        evidence_readable_classes=frozenset({PRODUCT_CLASS}),
    )


@dataclass
class _World:
    server: FastMCP
    store: FileArtifactStore
    recorded: FileArtifactStore


def _world(tmp_path: pathlib.Path, *, also_entitled_in: str | None = None) -> _World:
    """The shipped server: the caller at ``full`` in its own tenant, and — for
    the collision — the same principal id entitled to the class in another."""
    registry = ControlPlaneRegistry()
    for tenant in (TENANT, *((also_entitled_in,) if also_entitled_in else ())):
        register_typed_at_composition(
            registry, product_entitlement_key(tenant_id=tenant), _policy(tenant), PRODUCT_ENTITLEMENT_POLICY
        )
    source = ControlPlaneProductEntitlementSource(control_plane=registry, clock=lambda: AUDIT_INSTANT)
    recorded = deployment_store(tmp_path / "replay", REPLAY_RECORD_CLASS)
    recorder = refusal_recorder(
        registry,
        store=recorded,
        tenant=TENANT,
        replay_record_class=REPLAY_RECORD_CLASS,
        assembly_mode="algorithmic",
        policy_bundle_pin=None,
        disclosure_level_for=source.disclosure_level_for,
    )
    store = deployment_store(tmp_path / "artifacts", REPLAY_RECORD_CLASS)
    server = build_artifact_server(
        server_name="c2-tenant-hold",
        store=store,
        token_verifier=SourceBackedTokenVerifier(source=StaticTokenSource(grants={"tok": _grant()})),
        auth_settings=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.invalid"),
            resource_server_url=AnyHttpUrl("https://artifact.invalid/mcp"),
            required_scopes=[SCOPE],
        ),
        authorizer=authorizer_granting(tenants=(TENANT, FOREIGN)),
        entitlement_source=source,
        refusal_recorder=recorder,
        audit_log=ControlPlaneRegistry().audit_log,
        erasure_trust=declared_erasure_trust(),
        erasure_index=no_erasures(),
        control_plane=ControlPlaneRegistry(),
    )
    return _World(server=server, store=store, recorded=recorded)


def _record(*, tenant: str, principal: str, subject: str) -> DecisionReplayRecord:
    """A served record of ``tenant`` for ``principal`` — built, not yet filed."""
    from http_api.conftest import _replay_record

    base = _replay_record()
    served = base.content_generation_path.model_copy(
        update={
            "request": ProductRequest(
                schema_name=PRODUCT_CLASS,
                schema_version="1.0.0",
                subject=subject,
                intent="intent-1",
                freshness="event-driven",
                asked_at=AUDIT_INSTANT,
                parameters={},
            ),
            # Dave's Q12 (`D-IMPL-378`): the deciding class's affirmation that
            # its answers never withhold their subject, which read-back needs.
            "subject_withholding": "never",
        }
    )
    return base.model_copy(
        update={
            "tenant_id": tenant,
            "perspective_conditioning": base.perspective_conditioning.model_copy(
                update={"principal_id": principal, "role": ROLE}
            ),
            "content_generation_path": served,
        }
    )


def _file(world: _World, record: DecisionReplayRecord) -> str:
    """The record's own tenant files it under the governed class (its fabric's write)."""
    filed = world.store.put(
        composition_replay_mint(ControlPlaneRegistry(), tenant=record.tenant_id, artifact_class=REPLAY_RECORD_CLASS),
        DerivedWrite(artifact_class=REPLAY_RECORD_CLASS, name="record", artifact=record),
    )
    return filed.content_address


def _read(world: _World, surface: str, address: str) -> bytes:
    uri = (artifact_blob_uri if surface == "blob" else artifact_meta_uri)(content_address=address)
    reset = _as_grant(_grant())
    try:
        (answer,) = list(anyio.run(world.server.read_resource, uri))
    finally:
        auth_context_var.reset(reset)
    content = answer.content
    return content if isinstance(content, bytes) else content.encode("utf-8")


def _answers(world: _World, address: str) -> dict[str, bytes]:
    return {surface: _read(world, surface, address) for surface in SURFACES}


def _assert_identical(before: dict[str, bytes], after: dict[str, bytes]) -> None:
    """Every surface's bytes equal — all mismatches reported at once."""
    changed = [
        f"{surface}: missing={before[surface][:120]!r} / filed={after[surface][:120]!r}"
        for surface in SURFACES
        if after[surface] != before[surface]
    ]
    assert not changed, "another tenant's record at the address changed the answer on: " + " | ".join(changed)


def _internal_cause(world: _World, answer: bytes) -> tuple[str, str]:
    """The recorded determination behind a disclosed shell: (cause, error code)."""
    shell = RefusalEnvelope.model_validate_json(answer)
    record = DecisionReplayRecord.model_validate_json(
        world.recorded.get(content_address=world.recorded.resolve_uri(uri=shell.replay_reference))
    )
    internal = RefusalEnvelope.model_validate_json(record.content_generation_path.assembly_refusal)
    return json.loads(internal.fields["cause"]), json.loads(internal.fields["error_code"])


def test_another_tenants_record_with_a_colliding_principal_answers_as_a_missing_address_does(
    tmp_path: pathlib.Path,
) -> None:
    """(a) The collision: the caller's grant names only ``TENANT``; the record
    is ``FOREIGN``'s, for a principal with the caller's id, who is entitled to
    its class in ``FOREIGN``; the caller is at ``full``. The record's bytes must
    not cross: blob and presence answer what they answered while the address
    was empty — the recorded absence."""
    world = _world(tmp_path, also_entitled_in=FOREIGN)
    record = _record(tenant=FOREIGN, principal=PRINCIPAL, subject="c2-collision")
    address = content_hash(record)
    before = _answers(world, address)

    assert _file(world, record) == address
    after = _answers(world, address)

    assert after["blob"] != canonical_bytes(record), "another tenant's record crossed"
    _assert_identical(before, after)
    for surface in SURFACES:
        assert _internal_cause(world, after[surface]) == ("nonexistent", ERROR_EVIDENCE_ABSENT), surface
    # Control: the caller's OWN tenant's record, for the caller, still crosses.
    own = _record(tenant=TENANT, principal=PRINCIPAL, subject="c2-own")
    assert _read(world, "blob", _file(world, own)) == canonical_bytes(own)


def test_at_full_another_tenants_record_answers_as_a_missing_address_does(
    tmp_path: pathlib.Path,
) -> None:
    """(b) The oracle, with no collision: at ``full``, another tenant's genuine
    record answers exactly what a missing address answers. Within the tenant,
    R-4 stands: another principal's genuine record still reads
    ``unauthorized`` at ``full``."""
    world = _world(tmp_path)
    record = _record(tenant=FOREIGN, principal=OTHERS_OWN_PRINCIPAL, subject="c2-oracle")
    address = content_hash(record)
    # The instrument: a missing address answers the same bytes twice.
    first = _answers(world, address)
    before = _answers(world, address)
    _assert_identical(first, before)

    assert _file(world, record) == address
    after = _answers(world, address)

    _assert_identical(before, after)
    for surface in SURFACES:
        assert _internal_cause(world, after[surface]) == ("nonexistent", ERROR_EVIDENCE_ABSENT), surface
    # Control (R-4, unchanged): the caller's own tenant, another principal's record.
    theirs = _record(tenant=TENANT, principal=OTHERS_OWN_PRINCIPAL, subject="c2-same-tenant")
    poached = _read(world, "blob", _file(world, theirs))
    assert _internal_cause(world, poached) == ("unauthorized", ERROR_EVIDENCE_PRINCIPAL_MISMATCH)
