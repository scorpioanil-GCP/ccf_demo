"""The L2 write path: envelope in, resolved and policy-bound graph state out.

DESIGN.md §2A.3 (the four converging concerns) and §2A.5.4 (the write path end
to end). The conformance suite next door asserts what the *store* owes; this
module asserts what *assembly* owes — that source vocabulary becomes canonical
E and R under a stated temporal rule, with policy bound on the way in.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from ccf.controlplane.registry import ControlPlaneMissing, ControlPlaneRegistry
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

if TYPE_CHECKING:
    from ccf.boot import FabricHandle

TENANT = "tenant-a"
SPEC_KEY = "test/entity-resolution-spec"
POLICY_KEY = "test/policy-bundle"
INGESTED_AT = datetime(2026, 2, 1, tzinfo=UTC)
OCCURRED_AT = datetime(2026, 1, 15, tzinfo=UTC)


def envelope(
    *,
    envelope_id: str = "env-1",
    system_id: str = "core-banking",
    observed_time: datetime | None = OCCURRED_AT,
    payload: dict[str, Any] | None = None,
) -> SignalEnvelope:
    return SignalEnvelope(
        tenant_id=TENANT,
        envelope_id=envelope_id,
        source=SourceIdentity(system_id=system_id),
        ingestion_timestamp=INGESTED_AT,
        observed_time=observed_time,
        raw_payload=payload
        if payload is not None
        else {
            "counterparty_lei": "5493001KJTIIGC8Y1R12",
            "counterparty_name": "Acme Holdings",
            "jurisdiction": "GB",
            "facility_id": "RCF-0001",
            "facility_type": "revolver",
            "currency": "GBP",
        },
    )


def test_ingest_resolves_entities_and_the_typed_edge_between_them(
    fabric: "FabricHandle",
) -> None:
    """One source event becomes two canonical E nodes and one first-class R.

    The edge is persisted, not derived at query time (INV-CH7-20): a later read
    finds it in the graph without re-deriving it from the payload, which is what
    lets it carry its own lineage and its own supersession history.
    """
    result = fabric.worker.ingest(envelope())

    assert len(result.entities) == 2
    assert len(result.relationships) == 1

    view = fabric.reader.as_of(tenant_id=TENANT, at=INGESTED_AT)
    assert {r.claim.entity_class for r in view.entities} == {
        "counterparty",
        "facility",
    }
    edge = view.relationships[0].claim
    assert edge.relationship_type == "obligor_of"
    assert edge.subject_uri.startswith("counterparty://")
    assert edge.object_uri.startswith("facility://")


def test_entity_uris_converge_across_source_systems(
    fabric: "FabricHandle",
) -> None:
    """The same identifier from two systems resolves to one node (INV-CH7-18).

    Convergence is the whole point of resolution: without it the graph holds
    two Acmes and every operator over it is wrong. The URI is derived from
    declared identity values, never from where the record lived, so it also
    survives a source migration (INV-CH8-01).
    """
    first = fabric.worker.ingest(envelope(envelope_id="env-1", system_id="core"))
    second = fabric.worker.ingest(envelope(envelope_id="env-2", system_id="kyc"))

    assert [r.node_key for r in first.entities] == [r.node_key for r in second.entities]

    uri = first.entities[0].node_key
    history = fabric.reader.entity_history(tenant_id=TENANT, entity_uri=uri)
    assert len(history) == 1, "one node, one claim — the state did not change"
    assert {e.source.system_id for e in history[0].claim.lineage} == {"core", "kyc"}
    assert {e.envelope_id for e in history[0].claim.lineage} == {"env-1", "env-2"}


def test_replaying_one_envelope_changes_nothing(fabric: "FabricHandle") -> None:
    """Idempotence end to end, not merely at the store (INV-CH7-17)."""
    fabric.worker.ingest(envelope())
    second = fabric.worker.ingest(envelope())

    assert all(r.lineage_added == 0 for r in second.entities)
    assert all(not r.claim_created for r in second.entities)


def test_valid_time_opens_at_the_source_time_when_the_source_can_say(
    fabric: "FabricHandle",
) -> None:
    """Bitemporal stitching: observed-time is ingestion, valid-time is the event."""
    fabric.worker.ingest(envelope())

    view = fabric.reader.as_of(tenant_id=TENANT, at=INGESTED_AT)
    claim = view.entities[0].claim

    assert claim.observed_at == INGESTED_AT
    assert claim.valid_from == OCCURRED_AT


def test_valid_time_opens_at_ingestion_when_the_source_cannot_say(
    fabric: "FabricHandle",
) -> None:
    """The stated reconciliation rule, not a silent default (D-IMPL-38).

    The fabric never invents an earlier valid-time than it can justify: an
    assumed origin would let a historical read assert knowledge the fabric did
    not have, which is precisely the leakage as-of reads exist to prevent.
    """
    fabric.worker.ingest(envelope(observed_time=None))

    view = fabric.reader.as_of(tenant_id=TENANT, at=INGESTED_AT)
    claim = view.entities[0].claim

    assert claim.valid_from == INGESTED_AT


def test_partial_identity_is_refused_rather_than_hashed() -> None:
    """A URI minted from partial identity would silently split an entity.

    A rule can legitimately match on one key and identify on several — an
    account is selected by its presence and identified by institution plus
    number. When the second identity key is absent, hashing what is there would
    mint a *different* URI for the same real entity, and the graph would hold
    two of it with no way to notice. Refusing is the only safe answer.
    """
    from ccf.assembly.worker import (
        EntityResolutionRule,
        EntityResolutionSpec,
        SpecDrivenEntityResolution,
    )

    strategy = SpecDrivenEntityResolution(
        spec=EntityResolutionSpec(
            semver="1.0.0",
            entity_rules=(
                EntityResolutionRule(
                    match_key="account_number",
                    entity_class="account",
                    identity_keys=("institution_id", "account_number"),
                ),
            )
        )
    )

    with pytest.raises(ValueError, match="partial identity"):
        strategy.resolve(envelope=envelope(payload={"account_number": "0001"}))


def test_an_unresolvable_payload_produces_no_graph_state(
    fabric: "FabricHandle",
) -> None:
    """No rule matched is a legitimate outcome, not an error or a guess."""
    result = fabric.worker.ingest(envelope(payload={"unrelated_key": "value"}))

    assert result.entities == ()
    assert result.relationships == ()
    assert fabric.reader.as_of(tenant_id=TENANT, at=INGESTED_AT).entities == ()


def test_every_claim_carries_the_bound_policy_bundle_version(
    fabric: "FabricHandle",
) -> None:
    """P is bound at assembly, never post-processed (INV-CH7-03)."""
    fabric.worker.ingest(envelope())

    view = fabric.reader.as_of(tenant_id=TENANT, at=INGESTED_AT)

    bound = {r.policy_bundle_version for r in view.entities}
    bound |= {r.policy_bundle_version for r in view.relationships}
    assert bound == {fabric.worker.policy_bundle_version}


def test_a_fabric_whose_policy_bundle_is_unregistered_refuses_to_boot(
    tmp_path: Path, banking_spec: Any
) -> None:
    """Fail at boot, not on the first write (D-IMPL-38, no silent defaults).

    A fabric that started without a policy binding would write unbound claims
    until someone noticed — and those claims are exactly the ones an audit
    would later be unable to explain.
    """
    from ccf.boot import boot

    registry = ControlPlaneRegistry()
    spec_version = registry.register(SPEC_KEY, banking_spec)

    with pytest.raises(ControlPlaneMissing):
        boot(
            backend="sqlite",
            connection={"database_path": tmp_path / "unbound.sqlite3"},
            registry=registry,
            resolution_spec_key=SPEC_KEY,
            resolution_spec_version=spec_version,
            policy_bundle_key=POLICY_KEY,
            policy_bundle_version="never-registered",
        )


def test_a_failed_boot_leaves_the_graph_bootable(
    tmp_path: Path, banking_spec: Any
) -> None:
    """A half-boot must not strand the graph as permanently written-to.

    Otherwise a configuration typo would make the database unusable until the
    process restarted — the single-writer check turning into a footgun instead
    of a guardrail.
    """
    from ccf.boot import boot

    database_path = tmp_path / "retry.sqlite3"
    registry = ControlPlaneRegistry()
    spec_version = registry.register(SPEC_KEY, banking_spec)

    with pytest.raises(ControlPlaneMissing):
        boot(
            backend="sqlite",
            connection={"database_path": database_path},
            registry=registry,
            resolution_spec_key=SPEC_KEY,
            resolution_spec_version=spec_version,
            policy_bundle_key=POLICY_KEY,
            policy_bundle_version="never-registered",
        )

    policy_version = registry.register(POLICY_KEY, {"regime": "retry"})
    handle = boot(
        backend="sqlite",
        connection={"database_path": database_path},
        registry=registry,
        resolution_spec_key=SPEC_KEY,
        resolution_spec_version=spec_version,
        policy_bundle_key=POLICY_KEY,
        policy_bundle_version=policy_version,
    )
    try:
        assert handle.worker.policy_bundle_version == policy_version
    finally:
        handle.close()
