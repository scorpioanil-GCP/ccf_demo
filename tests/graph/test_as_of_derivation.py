"""``as_of`` is the degenerate query — the D-07 pin, byte-for-byte.

`GQ-21` at docs/GRAPH_QUERY_SEMANTICS.md:446: ``as_of(tenant, at)`` is
*defined* as ``query(GraphQuery(tenant_id=tenant, as_of=at))`` — identical
records, identical ordering, identical canonical bytes. This module asserts
the definition on a booted sqlite fabric with claims written through L2 (the
real write path — nothing here constructs a writer), at two boundaries so
the equality covers both a pre-supersession view and a post-supersession
view, and on an empty tenant so the empty answer is covered too (`GQ-23` at
docs/GRAPH_QUERY_SEMANTICS.md:474).

Comparison is on ``canonical_bytes``, never records: the claim is about the
delivered bytes replay depends on, not about record-count coincidence.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from ccf.contracts.canonical import canonical_bytes
from ccf.contracts.claims import EntityClaim, LineageEntry, RelationshipClaim
from ccf.graph.protocols import GraphQuery
from ccf.signal.envelope import SourceIdentity

if TYPE_CHECKING:
    from ccf.boot import FabricHandle

TENANT_A = "tenant-a"

T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = datetime(2026, 2, 1, tzinfo=UTC)
T2 = datetime(2026, 3, 1, tzinfo=UTC)


def _lineage(system_id: str, envelope_id: str, observed_at: datetime) -> LineageEntry:
    return LineageEntry(
        source=SourceIdentity(system_id=system_id),
        envelope_id=envelope_id,
        observed_at=observed_at,
    )


def _entity(
    *,
    entity_uri: str,
    entity_class: str = "counterparty",
    attributes: dict[str, str] | None = None,
    observed_at: datetime = T1,
    lineage_entries: tuple[LineageEntry, ...],
) -> EntityClaim:
    return EntityClaim(
        tenant_id=TENANT_A,
        entity_uri=entity_uri,
        entity_class=entity_class,
        attributes=attributes or {"legal_name": "Acme Holdings"},
        observed_at=observed_at,
        valid_from=T0,
        lineage=frozenset(lineage_entries),
    )


def test_as_of_equals_the_degenerate_query_byte_for_byte(
    fabric_boot: Callable[..., "FabricHandle"],
) -> None:
    """The D-07 derivation, pinned on written state.

    Claims enter through booted L2 — including a supersession, so the two
    boundaries exercise a claim that is current at T1 and superseded at T2
    — and the same reader answers both phrasings of the same question.
    """
    fabric = fabric_boot()

    acme_v1 = _entity(
        entity_uri="counterparty://acme",
        lineage_entries=(_lineage("core-banking", "env-1", T1),),
    )
    facility = _entity(
        entity_uri="facility://rcf-1",
        entity_class="facility",
        attributes={"commitment": "250000000"},
        lineage_entries=(_lineage("core-banking", "env-2", T1),),
    )
    edge = RelationshipClaim(
        tenant_id=TENANT_A,
        relationship_type="obligor_of",
        subject_uri="counterparty://acme",
        object_uri="facility://rcf-1",
        attributes={},
        observed_at=T1,
        valid_from=T0,
        lineage=frozenset({_lineage("core-banking", "env-3", T1)}),
    )
    acme_v2 = _entity(
        entity_uri="counterparty://acme",
        attributes={"legal_name": "Acme Holdings plc"},
        observed_at=T2,
        lineage_entries=(_lineage("kyc-registry", "env-4", T2),),
    )

    fabric.worker.admit_entity_claim(tenant_id=TENANT_A, claim=acme_v1)
    fabric.worker.admit_entity_claim(tenant_id=TENANT_A, claim=facility)
    fabric.worker.admit_relationship_claim(tenant_id=TENANT_A, claim=edge)
    fabric.worker.admit_entity_claim(tenant_id=TENANT_A, claim=acme_v2)

    for at in (T1, T2):
        named = fabric.reader.as_of(tenant_id=TENANT_A, at=at)
        degenerate = fabric.reader.query(
            GraphQuery(tenant_id=TENANT_A, as_of=at)
        )
        assert canonical_bytes(named) == canonical_bytes(degenerate)
        # The equality is not vacuous: the view carries the written state.
        assert named.entities, "the pinned view must not be empty at this boundary"


def test_the_derivation_holds_on_an_empty_tenant(
    fabric_boot: Callable[..., "FabricHandle"],
) -> None:
    """The empty answer is an answer (`GQ-23`), identically phrased both ways."""
    fabric = fabric_boot()
    named = fabric.reader.as_of(tenant_id=TENANT_A, at=T1)
    degenerate = fabric.reader.query(GraphQuery(tenant_id=TENANT_A, as_of=T1))
    assert canonical_bytes(named) == canonical_bytes(degenerate)
    assert named.entities == ()
    assert named.relationships == ()
