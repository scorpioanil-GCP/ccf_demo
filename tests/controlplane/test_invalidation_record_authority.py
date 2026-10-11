"""The invalidation-record capability authorizes one tenant's records of one class, and nothing else.

``D-IMPL-382``, Dave, 2026-10-11 07:32 MST: *"The authorization amendment covers only
entity-invalidation records belonging to the capability's tenant. It must not authorize another
tenant, another artifact class, or general registry writes."* *"Test the unauthorized cases
explicitly."* *"Preserve … nested-object isolation."*
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ccf.authz.capability import (
    COMPOSITION_PRINCIPAL,
    CapabilityBypassError,
    InvalidationRecordRegister,
    kind_for_action,
    mint_at_composition,
)
from ccf.controlplane.artifacts import HALF_LIFE_TABLE, HalfLifeEntry, HalfLifeTable
from ccf.controlplane.invalidation import (
    ENTITY_INVALIDATION_RECORD,
    RECORD_SEMVER,
    EntityInvalidationRecord,
    record_key,
    register_key,
    resolve_record,
)
from ccf.controlplane.registry import ControlPlaneRegistry, CrossTenantKeyRefused
from tests.composition import composition_invalidation_records
from tests.controlplane.capabilities import fabrications

TENANT_A = "tenant-alpha"
TENANT_B = "tenant-beta"
ENTITY = "entity://obligor-x"
AT = datetime(2026, 3, 2, 12, 0, 0, tzinfo=UTC)


def _record(tenant_id: str = TENANT_A, entity_uri: str = ENTITY, at: datetime = AT) -> EntityInvalidationRecord:
    return EntityInvalidationRecord(
        semver=RECORD_SEMVER, tenant_id=tenant_id, entity_uri=entity_uri,
        invalidated_from=at, reason="entity-claim-superseded", source="claim-1",
    )


def _nothing_registered(registry: ControlPlaneRegistry) -> None:
    assert not [e for e in registry.audit_events() if e.action.startswith("register") and e.resolved]


def _table() -> HalfLifeTable:
    return HalfLifeTable(semver="1.0.0", entries={"spread": HalfLifeEntry(
        half_life_seconds=86_400, decay_driver="market-movement", supersession_event="next-observation")})


def test_no_door_can_obtain_the_kind() -> None:
    with pytest.raises(CapabilityBypassError, match="no door declares it"):
        kind_for_action(InvalidationRecordRegister.action_id)


def test_the_capability_writes_its_own_tenants_record_under_a_key_it_derives() -> None:
    registry = ControlPlaneRegistry()
    version = registry.register_typed(composition_invalidation_records(registry, TENANT_A), _record(), ENTITY_INVALIDATION_RECORD)
    assert registry.versions(record_key(TENANT_A, ENTITY)) == (version,)
    written = {e.key for e in registry.audit_events() if e.action == "register_typed" and e.resolved}
    assert written == {record_key(TENANT_A, ENTITY)}


def test_another_tenant_is_refused() -> None:
    """The record names tenant B; the capability is A's."""
    registry = ControlPlaneRegistry()
    with pytest.raises(CrossTenantKeyRefused):
        registry.register_typed(composition_invalidation_records(registry, TENANT_A), _record(tenant_id=TENANT_B), ENTITY_INVALIDATION_RECORD)
    _nothing_registered(registry)


@pytest.mark.parametrize("resource", [register_key(TENANT_B), f"{TENANT_A}/ccf.half-life", f"{TENANT_A}/ccf.entity-invalidation/extra", TENANT_A])
def test_a_capability_minted_for_any_other_prefix_is_refused(resource: str) -> None:
    """A composition root that mints the kind for another tenant's prefix, or any other prefix, opens nothing."""
    registry = ControlPlaneRegistry()
    cap = mint_at_composition(
        InvalidationRecordRegister, tenant=TENANT_A, principal=COMPOSITION_PRINCIPAL, resource=resource, decision_id="d",
    )
    with pytest.raises(CrossTenantKeyRefused, match="must be minted for"):
        registry.register_typed(cap, _record(), ENTITY_INVALIDATION_RECORD)
    _nothing_registered(registry)


def test_another_artifact_class_is_refused() -> None:
    registry = ControlPlaneRegistry()
    with pytest.raises(CapabilityBypassError, match="no other artifact class"):
        registry.register_typed(composition_invalidation_records(registry, TENANT_A), _table(), HALF_LIFE_TABLE)
    _nothing_registered(registry)


def test_general_registry_writes_are_refused() -> None:
    """``register`` and ``register_versioned`` refuse the kind, as they refuse every non-door kind."""
    registry = ControlPlaneRegistry()
    cap = composition_invalidation_records(registry, TENANT_A)
    with pytest.raises(CapabilityBypassError):
        registry.register(cap, {"anything": "at all"})  # type: ignore[arg-type]
    with pytest.raises(CapabilityBypassError):
        registry.register(cap, _record())  # type: ignore[arg-type]
    with pytest.raises(CapabilityBypassError):
        registry.register_versioned(cap, _record(), ENTITY_INVALIDATION_RECORD)  # type: ignore[arg-type]
    _nothing_registered(registry)


def test_every_fabrication_of_the_kind_is_refused() -> None:
    registry = ControlPlaneRegistry()
    for label, forged in fabrications(InvalidationRecordRegister, tenant=TENANT_A, resource=register_key(TENANT_A)):
        with pytest.raises(CapabilityBypassError):
            registry.register_typed(forged, _record(), ENTITY_INVALIDATION_RECORD)  # type: ignore[arg-type]
        _nothing_registered(registry)


def test_a_record_read_is_a_fresh_object_and_a_mutation_reaches_no_later_read() -> None:
    """Nested-object isolation holds for records: neither the registrant nor a reader reaches stored state."""
    registry = ControlPlaneRegistry()
    original = _record()
    registry.register_typed(composition_invalidation_records(registry, TENANT_A), original, ENTITY_INVALIDATION_RECORD)
    object.__setattr__(original, "source", "rewritten-by-registrant")
    first = resolve_record(registry, tenant_id=TENANT_A, entity_uri=ENTITY)
    assert first is not None and first.source == "claim-1"
    object.__setattr__(first, "invalidated_from", datetime(1999, 1, 1, tzinfo=UTC))
    second = resolve_record(registry, tenant_id=TENANT_A, entity_uri=ENTITY)
    assert second is not None and second is not first
    assert second.invalidated_from == AT and second.source == "claim-1"
