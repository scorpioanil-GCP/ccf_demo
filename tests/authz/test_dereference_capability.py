"""``govern_dereference`` under the capability (D-IMPL-353 §1.2; the join).

The governed evidence read takes ``Authorized[ArtifactRead] |
Authorized[ReplayRead]`` first, and ``verify_any`` against it — bound to the
reference the caller asked for — is its first statement. Every claim below is
drafted from what would fail:

=====================================  =====================================
Claim                                  What would fail here
=====================================  =====================================
the capability is verified FIRST       a fabricated, retargeted or wrong-kind
                                       capability could reach the clock, the
                                       store, or the recorder
the resource is the reference          a capability for address X could
                                       dereference address Y
the principal is the capability's      a read could be decided for a caller
                                       other than the one the gate minted for
the audited action is the kind's       a ``replay.read`` capability could leave
                                       an ``artifact.read`` trail
MCP-minted read refusals are read      a read refusal minted at the MCP blob
refusals                               resource would be withheld from its own
                                       principal at hold 2 as a record with no
                                       recoverable class
=====================================  =====================================
"""

from __future__ import annotations

import pathlib
from datetime import UTC, datetime
from typing import Any

import pytest

from ccf.authz.capability import (
    ArtifactRead,
    ArtifactWrite,
    CapabilityBypassError,
    ReplayRead,
)
from ccf.controlplane.audit import AuthzDecisionAuditEvent
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.entitlement import (
    PRODUCT_ENTITLEMENT_POLICY,
    ProductEntitlementGrant,
    ProductEntitlementPolicy,
    product_entitlement_key,
)
from ccf.products.refusal import (
    RefusalEnvelope,
    RequestIdentity,
    ResourceRequestIdentity,
    SubjectUnavailableRefusal,
    envelope_for,
)
from ccf_runtime.authz.delivery_boundary import (
    DEREFERENCE_PRODUCT_ID,
    EVIDENCE_SURFACES,
    SURFACE_HTTP_ARTIFACT_READ,
    SURFACE_HTTP_REPLAY_READ,
    SURFACE_MCP_RESOURCE,
    SURFACE_MCP_TOOL,
    DereferenceRequest,
    _is_read_refusal,
    govern_dereference,
)
from ccf_runtime.authz.product_entitlement import ControlPlaneProductEntitlementSource
from ccf_runtime.authz.refusals import ACTION_ARTIFACT_READ, ACTION_REPLAY_READ
from http_api.composition_authority import (
    deployment_store,
    refusal_recorder,
    register_typed_at_composition,
)
from ccf.erasure import compose_erasure_consult
from tests.composition import declared_erasure_trust, no_erasures
from tests.controlplane.capabilities import capability, fabrications, retarget

TENANT = "tenant-dereference"
PRINCIPAL = "principal-dereference"
ROLE = "role-dereference"
PRODUCT_CLASS = "class-dereference"
REPLAY_RECORD_CLASS = "ccf.decision-replay-record"
INSTANT = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
NOWHERE = "e" * 64


class _World:
    def __init__(self, tmp_path: pathlib.Path) -> None:
        self.registry = ControlPlaneRegistry()
        register_typed_at_composition(
            self.registry,
            product_entitlement_key(tenant_id=TENANT),
            ProductEntitlementPolicy(
                tenant_id=TENANT,
                policy_version="1.0.0",
                principals={
                    PRINCIPAL: ProductEntitlementGrant(
                        permitted_schema_names=frozenset({PRODUCT_CLASS}),
                        permitted_roles=frozenset({ROLE}),
                    )
                },
            ),
            PRODUCT_ENTITLEMENT_POLICY,
        )
        self.clock_reads = 0

        def clock() -> datetime:
            self.clock_reads += 1
            return INSTANT

        self.source = ControlPlaneProductEntitlementSource(
            control_plane=self.registry, clock=clock
        )
        self.raw = deployment_store(tmp_path / "artifacts", REPLAY_RECORD_CLASS)
        # PM5 (panel C5; `D-IMPL-374`): U12 composes the erasure consult
        # always, and `govern_dereference` now refuses a store that does not
        # consult; the store a door hands it is the composed one.
        self.store = compose_erasure_consult(
            self.raw, index=no_erasures(), audit_log=self.registry.audit_log,
            clock=lambda: INSTANT, control_plane=self.registry,
            erasure_trust=declared_erasure_trust(TENANT),
        )
        self.recorder = refusal_recorder(
            self.registry,
            store=self.raw,
            tenant=TENANT,
            replay_record_class=REPLAY_RECORD_CLASS,
            disclosure_level_for=self.source.disclosure_level_for,
        )

    def addresses(self) -> set[str]:
        return {p.name for p in self.raw.root.iterdir() if len(p.name) == 64}

    def dereference(self, authorized: Any, *, reference: str = NOWHERE, by_uri: bool = False, wants_bytes: bool = True) -> Any:
        return govern_dereference(
            authorized,
            reference=DereferenceRequest(reference=reference, by_uri=by_uri, wants_bytes=wants_bytes),
            store=self.store,
            entitlement_source=self.source,
            refusal_recorder=self.recorder,
            audit_log=self.registry.audit_log,
            surface=SURFACE_HTTP_ARTIFACT_READ,
            address="/artifact/{content_address}",
        )

    def read_trail(self) -> list[AuthzDecisionAuditEvent]:
        return [
            e
            for e in self.registry.audit_log.events()
            if isinstance(e, AuthzDecisionAuditEvent)
            and e.artifact_class == DEREFERENCE_PRODUCT_ID
        ]


@pytest.fixture
def world(tmp_path: pathlib.Path) -> _World:
    return _World(tmp_path)


# --- the capability first ------------------------------------------------------


def test_a_genuine_read_capability_for_the_reference_dereferences(world: _World) -> None:
    """Positive control: a nonexistent address answers the recorded shell,
    under the capability's principal, and the trail names the kind's action."""
    decided = world.dereference(capability(ArtifactRead, tenant=TENANT, resource=NOWHERE, principal=PRINCIPAL))
    assert isinstance(decided, RefusalEnvelope)
    assert decided.request.product_id == DEREFERENCE_PRODUCT_ID
    (trail,) = world.read_trail()
    assert trail.actor == PRINCIPAL
    assert trail.authz_action_id == ACTION_ARTIFACT_READ
    assert trail.key == NOWHERE


def test_a_replay_read_capability_leaves_a_replay_read_trail(world: _World) -> None:
    world.dereference(
        capability(ReplayRead, tenant=TENANT, resource=NOWHERE, principal=PRINCIPAL),
        wants_bytes=False,
    )
    (trail,) = world.read_trail()
    assert trail.authz_action_id == ACTION_REPLAY_READ


def test_a_wrong_kind_capability_dies_before_the_clock_the_store_or_the_recorder(
    world: _World,
) -> None:
    """A write capability for the very address: refused at the first line.
    Nothing is recorded, no audit trail is left, and the entitlement source's
    clock — the determination instant — is never read."""
    before = world.addresses()
    with pytest.raises(CapabilityBypassError):
        world.dereference(capability(ArtifactWrite, tenant=TENANT, resource=NOWHERE, principal=PRINCIPAL))
    assert world.addresses() == before
    assert world.read_trail() == []
    assert world.clock_reads == 0


def test_a_capability_for_another_reference_dies_at_the_resource_bind(world: _World) -> None:
    before = world.addresses()
    other = "f" * 64
    with pytest.raises(CapabilityBypassError, match="resource"):
        world.dereference(
            capability(ArtifactRead, tenant=TENANT, resource=other, principal=PRINCIPAL),
            reference=NOWHERE,
        )
    assert world.addresses() == before
    assert world.clock_reads == 0


def test_every_fabrication_dies_at_the_first_line(world: _World) -> None:
    before = world.addresses()
    for name, forged in fabrications(ArtifactRead, tenant=TENANT, resource=NOWHERE):
        with pytest.raises(CapabilityBypassError):
            world.dereference(forged)
        assert world.addresses() == before, name
    assert world.clock_reads == 0


@pytest.mark.parametrize("field", ["kind", "tenant", "principal", "resource", "decision_id"])
def test_a_retargeted_capability_is_unusable_for_the_read(world: _World, field: str) -> None:
    genuine = capability(ArtifactRead, tenant=TENANT, resource=NOWHERE, principal=PRINCIPAL)
    value: object = ReplayRead if field == "kind" else "retargeted"
    with pytest.raises(CapabilityBypassError):
        setattr(genuine, field, value)
    retarget(genuine, field, value)
    with pytest.raises(CapabilityBypassError):
        world.dereference(genuine, reference=NOWHERE)
    assert world.clock_reads == 0


def test_a_moving_target_is_still_refused_before_any_lookup_but_after_the_capability(
    world: _World,
) -> None:
    from ccf.artifacts.protocol import MovingTargetRefused

    uri = f"ccf-artifact://{TENANT}/{REPLAY_RECORD_CLASS}/x@latest"
    with pytest.raises(MovingTargetRefused):
        world.dereference(
            capability(ReplayRead, tenant=TENANT, resource=uri, principal=PRINCIPAL),
            reference=uri, by_uri=True, wants_bytes=False,
        )
    # And the capability is still first: a wrong kind for the same URI never
    # reaches the parser.
    with pytest.raises(CapabilityBypassError):
        world.dereference(
            capability(ArtifactWrite, tenant=TENANT, resource=uri, principal=PRINCIPAL),
            reference=uri, by_uri=True, wants_bytes=False,
        )


# --- the MCP surface is an evidence surface --------------------------------------


def _read_refusal_at(surface: str) -> RefusalEnvelope:
    return envelope_for(
        SubjectUnavailableRefusal(cause="nonexistent", detail="x", error_code="evidence-absent"),
        request=RequestIdentity(
            product_id=DEREFERENCE_PRODUCT_ID,
            product_version=None,
            parameters={"reference": NOWHERE},
            temporal_boundary=None,
        ),
        resource=ResourceRequestIdentity(
            surface=surface, address="ccf-artifact-blob://" + NOWHERE, tenant_id=TENANT, determined_at=INSTANT
        ),
        policy_bindings=(),
    )


def test_the_mcp_resource_surface_is_an_evidence_surface() -> None:
    assert SURFACE_MCP_RESOURCE in EVIDENCE_SURFACES
    assert EVIDENCE_SURFACES == frozenset(
        {SURFACE_HTTP_REPLAY_READ, SURFACE_HTTP_ARTIFACT_READ, SURFACE_MCP_RESOURCE}
    )


def test_an_mcp_minted_read_refusal_is_recognized_as_a_read_refusal() -> None:
    assert _is_read_refusal(_read_refusal_at(SURFACE_MCP_RESOURCE)) is True
    assert _is_read_refusal(_read_refusal_at(SURFACE_HTTP_ARTIFACT_READ)) is True
    # Both constants together, never either alone: a serve-surface record with
    # the dereference product id is not a read refusal.
    assert _is_read_refusal(_read_refusal_at(SURFACE_MCP_TOOL)) is False
    assert _is_read_refusal(None) is False
