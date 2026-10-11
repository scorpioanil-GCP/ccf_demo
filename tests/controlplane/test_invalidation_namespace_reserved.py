"""The invalidation key range belongs to the invalidation-record capability alone (D-IMPL-382, review of b66ab4fa).

Found by the focused independent review (Dave, 09:46: *"Run the focused independent review …
including the registry, capability checks, boot wiring and serve path"*), each reproduced by
execution before this file was written:

* a door ``Register`` or a ``CompositionRegister`` minted for an exact record key could write there:
  planting an earlier-dated record made a refused product serve (fail-open); planting other content
  made every serve touching that entity raise, and blocked the sink;
* a tenant id containing ``/`` produced invalidation keys whose tenant segment is another tenant;
* the class check compared only the class id, so another contract (or a subclass) under that id
  was stored as a record;
* ``invalidation_history`` silently dropped foreign content and filed a record under the entity it
  names rather than the key it sits under.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ccf.authz.capability import (
    COMPOSITION_PRINCIPAL,
    CapabilityBypassError,
    InvalidationRecordRegister,
    Register,
    mint_at_composition,
)
from ccf.controlplane.artifact_base import ArtifactClass
from ccf.controlplane.artifacts import HALF_LIFE_TABLE, HalfLifeEntry, HalfLifeTable
from ccf.controlplane.invalidation import (
    ENTITY_INVALIDATION_RECORD,
    RECORD_SEMVER,
    EntityInvalidationRecord,
    invalidation_history,
    record_key,
    register_key,
)
from ccf.controlplane.registry import ControlPlaneRegistry, CrossTenantKeyRefused
from tests.composition import composition_invalidation_records, composition_register
from tests.controlplane.capabilities import register_capability
from tests.products import test_dependency_invalidation as fixture

TENANT = fixture.TENANT_A
ENTITY = fixture.ENTITY_X


def _planted(at: datetime, entity_uri: str = ENTITY) -> EntityInvalidationRecord:
    return EntityInvalidationRecord(semver=RECORD_SEMVER, tenant_id=TENANT, entity_uri=entity_uri,
                                    invalidated_from=at, reason="planted", source="not-the-sink")


def _table() -> HalfLifeTable:
    return HalfLifeTable(semver="1.0.0", entries={"s": HalfLifeEntry(half_life_seconds=1, decay_driver="d", supersession_event="e")})


@pytest.mark.parametrize("door", ["config.register", "composition.register"])
@pytest.mark.parametrize("key", [record_key(TENANT, ENTITY), register_key(TENANT), f"{register_key(TENANT)}/anything"])
def test_no_other_capability_can_write_anywhere_in_the_invalidation_range(door: str, key: str) -> None:
    registry = ControlPlaneRegistry()
    cap = register_capability(key, Register) if door == "config.register" else composition_register(registry, key)
    for attempt in (
        lambda: registry.register(cap, {"a": 1}),
        lambda: registry.register_typed(cap, _table(), HALF_LIFE_TABLE),
        lambda: registry.register_typed(cap, _planted(datetime(2000, 1, 1, tzinfo=UTC)), ENTITY_INVALIDATION_RECORD),
    ):
        with pytest.raises((CapabilityBypassError, CrossTenantKeyRefused)):
            attempt()
    assert registry.versions(key) == ()


def test_a_refused_product_cannot_be_made_to_serve_by_planting_an_earlier_record() -> None:
    """The fail-open the review reproduced: before the fix, the plant moved the boundary back and the product served."""
    registry = ControlPlaneRegistry()
    registered = fixture._registered(registry)
    fixture._supersede(registry, tenant_id=TENANT, entity_uri=ENTITY, at=fixture.T2)
    def serve() -> object:
        return fixture._serve(registry, registered, tenant_id=TENANT, snapshot=fixture.T1, touched=(ENTITY,))
    assert type(serve()).__name__ == "DependencyInvalidationRefusal"
    with pytest.raises((CapabilityBypassError, CrossTenantKeyRefused)):
        registry.register_typed(register_capability(record_key(TENANT, ENTITY), Register),
                                _planted(datetime(2000, 1, 1, tzinfo=UTC)), ENTITY_INVALIDATION_RECORD)
    assert type(serve()).__name__ == "DependencyInvalidationRefusal"


def test_a_tenant_id_containing_a_separator_cannot_write_invalidation_records() -> None:
    registry = ControlPlaneRegistry()
    cap = mint_at_composition(InvalidationRecordRegister, tenant="acme/x", principal=COMPOSITION_PRINCIPAL,
                              resource="acme/x/ccf.entity-invalidation", decision_id="d")
    record = EntityInvalidationRecord(semver=RECORD_SEMVER, tenant_id="acme/x", entity_uri=ENTITY,
                                      invalidated_from=fixture.T2, reason="r", source="s")
    with pytest.raises(CrossTenantKeyRefused):
        registry.register_typed(cap, record, ENTITY_INVALIDATION_RECORD)
    assert not [e for e in registry.audit_events() if e.action == "register_typed" and e.resolved]


def test_boot_refuses_a_tenant_id_containing_a_separator() -> None:
    from ccf.boot import _composed_tenants

    with pytest.raises(ValueError):
        _composed_tenants(("acme/x",))


class _NotARecord(EntityInvalidationRecord):
    def advanced_by(self, later: EntityInvalidationRecord) -> bool:  # freezes every boundary
        return False


def test_only_the_record_class_itself_is_admitted_under_the_record_class_id() -> None:
    registry = ControlPlaneRegistry()
    cap = composition_invalidation_records(registry, TENANT)
    impostor = ArtifactClass(class_id=ENTITY_INVALIDATION_RECORD.class_id, contract=HalfLifeTable)
    with pytest.raises(CapabilityBypassError):
        registry.register_typed(cap, _table(), impostor)
    sub = ArtifactClass(class_id=ENTITY_INVALIDATION_RECORD.class_id, contract=_NotARecord)
    with pytest.raises(CapabilityBypassError):
        registry.register_typed(cap, _NotARecord(**_planted(fixture.T2).model_dump()), sub)
    assert not [e for e in registry.audit_events() if e.action == "register_typed" and e.resolved]


def test_history_refuses_content_that_is_not_this_keys_record() -> None:
    """Defense in depth below the reservation: history raises, as resolve_record does, instead of dropping or misfiling."""
    registry = ControlPlaneRegistry()
    fixture._supersede(registry, tenant_id=TENANT, entity_uri=ENTITY, at=fixture.T2)
    key = record_key(TENANT, ENTITY)
    real = registry.resolve(key, registry.versions(key)[0])
    other = _planted(fixture.T3, entity_uri="entity://other")
    # Reach below every door: the registry's own record for this key now holds another entity's record.
    held = registry._artifacts[(key, registry.versions(key)[0])]
    from ccf.contracts.canonical import canonical_bytes, content_hash
    rendered = canonical_bytes(other)
    registry._artifacts[(key, content_hash(other))] = type(held)(artifact=other, rendered=rendered)
    registry._versions[key].append(content_hash(other))
    with pytest.raises(TypeError):
        invalidation_history(registry, tenant_id=TENANT)
    assert real.entity_uri == ENTITY
