"""The ``GraphStore`` conformance suite — the acceptance bar for every backend.

DESIGN.md §2A.5.2 fixes exactly six invariant semantics every conforming
backend must carry (the D-IMPL-34 requirement surface). This module asserts all
six, once, parametrized over a backend factory — so the Postgres wave (D-11)
implements against a suite that already exists rather than against a suite
written to describe whatever it happened to build (D-16).

Two disciplines are load-bearing here and are easy to lose:

* **Nothing constructs a writer.** Every write goes through the L2 admission
  path on a fabric booted by the real composition root. A conformance suite
  that reached for the concrete writer would be testing the store while
  demonstrating the exact bypass the D-IMPL-41 stack exists to prevent.
* **Comparisons happen on canonical bytes, never on raw rows.** SQLite and
  Postgres disagree about timestamp precision, numeric affinity, and row order;
  the contract layer does not (04-RESEARCH.md Pitfall 3). Comparing
  ``canonical_bytes`` of contracts is what keeps this suite backend-neutral
  instead of backend-flaky.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from ccf.contracts.canonical import canonical_bytes
from ccf.contracts.claims import EntityClaim, LineageEntry, RelationshipClaim
from ccf.signal.envelope import SourceIdentity

if TYPE_CHECKING:
    from ccf.boot import FabricHandle

pytestmark = pytest.mark.conformance

TENANT_A = "tenant-a"
TENANT_B = "tenant-b"

T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = datetime(2026, 2, 1, tzinfo=UTC)
T2 = datetime(2026, 3, 1, tzinfo=UTC)


@pytest.fixture(
    params=[
        pytest.param("sqlite"),
        pytest.param("memory"),
        pytest.param("demo"),
        pytest.param("postgres", marks=pytest.mark.postgres),
        pytest.param("neo4j", marks=pytest.mark.neo4j),
        pytest.param("mongo", marks=pytest.mark.mongo),
        pytest.param("fluree", marks=pytest.mark.fluree),
    ]
)
def graph_backend(
    request: pytest.FixtureRequest, fabric_boot: Callable[..., "FabricHandle"]
) -> "FabricHandle":
    """A booted fabric per backend under test.

    The Postgres reference backend (D-11) landed as a *param*, exactly as this
    fixture's original note promised: not one test body below changed, and no
    test body knows which substrate it is running on. That is what makes the
    suite evidence of parity rather than two suites that happen to agree.

    The Phase 15.2 backends landed the same way, and for the same reason —
    this is **DI-15.2-02 routed at the phase-close audit (plan 15.2-14)**: the
    three new substrates were passing the six D-IMPL-34 write semantics only
    *indirectly* (the differential corpus writes through booted L2, and the
    per-backend unit modules pin boot and idempotent re-arrival), which left
    the suite that OWNS those semantics silent about them. It is no longer:
    ``memory`` runs always-on beside ``sqlite``, and ``neo4j``/``mongo`` carry
    their container marks. Not one test body changed — exactly what the
    deferred item predicted, and the reason the five-backend claim in SUBQ-11
    is now asserted by the suite rather than inferred from a neighbouring one.

    Each extras-gated param carries its own mark, so ``-m "not postgres and
    not neo4j and not mongo"`` still gives a run with no external substrate
    while ``-m <backend>`` runs the same semantics against a real server.

    **``demo`` is different in kind from every param above it (plan 15.4-11).**
    Each of the others names an adapter living in ``src/ccf``, so the suite was
    holding this repository's own code to its own bar; ``demo`` names an adapter
    that ships in a separate installable distribution
    (``tests/fixtures/ccf-demo-adapter``) and imports nothing from
    ``ccf.graph.backends``, so from here the suite demonstrates the *contract*
    rather than the *implementation* — the six D-IMPL-34 semantics are shown to
    be reachable by a third party through the published seam, not merely
    upheld by code the seam's authors also wrote. It carries no mark because
    its store is an in-process dict: no container, no extra, no temp file, so
    it runs on the always-on leg beside ``sqlite`` and ``memory``.
    """
    if request.param == "sqlite":
        return fabric_boot()
    if request.param in {"memory", "demo", "postgres", "neo4j", "mongo", "fluree"}:
        return fabric_boot(backend=request.param)
    raise NotImplementedError(request.param)


def lineage(system_id: str, envelope_id: str, observed_at: datetime) -> LineageEntry:
    return LineageEntry(
        source=SourceIdentity(system_id=system_id),
        envelope_id=envelope_id,
        observed_at=observed_at,
    )


def entity(
    *,
    tenant_id: str = TENANT_A,
    entity_uri: str = "counterparty://acme",
    entity_class: str = "counterparty",
    attributes: Mapping[str, str] | None = None,
    observed_at: datetime = T1,
    valid_from: datetime = T0,
    lineage_entries: tuple[LineageEntry, ...] = (),
) -> EntityClaim:
    return EntityClaim(
        tenant_id=tenant_id,
        entity_uri=entity_uri,
        entity_class=entity_class,
        attributes=dict(attributes or {"legal_name": "Acme Holdings"}),
        observed_at=observed_at,
        valid_from=valid_from,
        lineage=frozenset(lineage_entries or (lineage("core-banking", "env-1", T1),)),
    )


def relationship(
    *,
    tenant_id: str = TENANT_A,
    relationship_type: str = "obligor_of",
    observed_at: datetime = T1,
    lineage_entries: tuple[LineageEntry, ...] = (),
) -> RelationshipClaim:
    return RelationshipClaim(
        tenant_id=tenant_id,
        relationship_type=relationship_type,
        subject_uri="counterparty://acme",
        object_uri="facility://rcf-1",
        attributes={},
        observed_at=observed_at,
        valid_from=T0,
        lineage=frozenset(lineage_entries or (lineage("core-banking", "env-1", T1),)),
    )


# --- Semantic 2: idempotent upsert ------------------------------------------


def test_same_envelope_twice_yields_one_claim_and_one_lineage_entry(
    graph_backend: "FabricHandle",
) -> None:
    """A replayed envelope must not manufacture history (INV-CH7-17).

    This is the half of the semantic that is easy to get right; the next test
    is the half that a naive "upsert overwrites the row" implementation passes
    while quietly violating the invariant.
    """
    claim = entity()
    first = graph_backend.worker.admit_entity_claim(tenant_id=TENANT_A, claim=claim)
    second = graph_backend.worker.admit_entity_claim(tenant_id=TENANT_A, claim=claim)

    assert first.claim_created is True
    assert first.lineage_added == 1
    assert second.claim_created is False
    assert second.lineage_added == 0
    assert second.claim_id == first.claim_id

    history = graph_backend.reader.entity_history(
        tenant_id=TENANT_A, entity_uri=claim.entity_uri
    )
    assert len(history) == 1
    assert len(history[0].claim.lineage) == 1


def test_same_observation_from_two_sources_accumulates_lineage_by_union(
    graph_backend: "FabricHandle",
) -> None:
    """Multi-source corroboration is additive, never replacing (INV-CH7-17).

    Lineage is deliberately *not* idempotent: one entity row, two lineage
    entries with their own source identities and timestamps preserved. An
    implementation that overwrites the lineage column passes the idempotence
    test above and fails here — which is precisely why both exist
    (04-RESEARCH.md Pitfall 2).
    """
    from_core = entity(lineage_entries=(lineage("core-banking", "env-1", T1),))
    from_kyc = entity(lineage_entries=(lineage("kyc-registry", "env-2", T1),))

    graph_backend.worker.admit_entity_claim(tenant_id=TENANT_A, claim=from_core)
    result = graph_backend.worker.admit_entity_claim(tenant_id=TENANT_A, claim=from_kyc)

    assert result.claim_created is False, "same claim content — no new claim row"
    assert result.lineage_added == 1

    history = graph_backend.reader.entity_history(
        tenant_id=TENANT_A, entity_uri=from_core.entity_uri
    )
    assert len(history) == 1
    persisted = history[0].claim.lineage
    assert len(persisted) == 2
    assert {e.source.system_id for e in persisted} == {"core-banking", "kyc-registry"}
    assert canonical_bytes(persisted) == canonical_bytes(
        from_core.lineage | from_kyc.lineage
    )


# --- Semantics 3 and 4: supersession, append-only-forward -------------------


def test_supersession_appends_and_leaves_the_prior_claim_readable(
    graph_backend: "FabricHandle",
) -> None:
    """Supersession is a logical event, never an overwrite (INV-CH7-04/21).

    The prior claim keeps its content byte-for-byte and gains only the
    supersession edge. Overwrite in place is what would make Decision Replay at
    T+2 years structurally impossible.
    """
    original = entity(attributes={"legal_name": "Acme Holdings"}, observed_at=T1)
    revised = entity(attributes={"legal_name": "Acme Holdings plc"}, observed_at=T2)

    first = graph_backend.worker.admit_entity_claim(tenant_id=TENANT_A, claim=original)
    second = graph_backend.worker.admit_entity_claim(tenant_id=TENANT_A, claim=revised)

    assert second.claim_created is True
    assert second.superseded_claim_id == first.claim_id

    history = graph_backend.reader.entity_history(
        tenant_id=TENANT_A, entity_uri=original.entity_uri
    )
    assert len(history) == 2, "the prior claim remains — nothing is deleted"
    prior, current = history
    assert prior.superseded_by == current.claim_id
    assert prior.superseded_at == revised.observed_at
    assert current.superseded_by is None
    assert canonical_bytes(prior.claim.attributes) == canonical_bytes(
        original.attributes
    ), "superseded claim content is untouched"


def test_as_of_before_and_after_supersession_renders_each_state(
    graph_backend: "FabricHandle",
) -> None:
    """Bitemporal reads reproduce prior state exactly (INV-CH7-14).

    No future-information leakage: an as-of read positioned between the two
    observations must not know about the second one.
    """
    original = entity(attributes={"legal_name": "Acme Holdings"}, observed_at=T1)
    revised = entity(attributes={"legal_name": "Acme Holdings plc"}, observed_at=T2)
    graph_backend.worker.admit_entity_claim(tenant_id=TENANT_A, claim=original)
    graph_backend.worker.admit_entity_claim(tenant_id=TENANT_A, claim=revised)

    before = graph_backend.reader.as_of(tenant_id=TENANT_A, at=T1)
    after = graph_backend.reader.as_of(tenant_id=TENANT_A, at=T2)

    assert [r.claim.attributes["legal_name"] for r in before.entities] == [
        "Acme Holdings"
    ]
    assert [r.claim.attributes["legal_name"] for r in after.entities] == [
        "Acme Holdings plc"
    ]


def test_as_of_before_any_observation_is_empty_not_an_error(
    graph_backend: "FabricHandle",
) -> None:
    """"Nothing is known" is an answer operators compose over, not a failure."""
    graph_backend.worker.admit_entity_claim(tenant_id=TENANT_A, claim=entity())

    view = graph_backend.reader.as_of(tenant_id=TENANT_A, at=T0)

    assert view.entities == ()
    assert view.relationships == ()


def test_empty_graph_reads_return_empty_views(
    graph_backend: "FabricHandle",
) -> None:
    view = graph_backend.reader.as_of(tenant_id=TENANT_A, at=T2)

    assert view.tenant_id == TENANT_A
    assert view.entities == ()
    assert view.relationships == ()
    assert (
        graph_backend.reader.entity_history(
            tenant_id=TENANT_A, entity_uri="counterparty://unknown"
        )
        == ()
    )


# --- Semantics 1 and tenancy ------------------------------------------------


def test_compound_uniqueness_is_on_tenant_and_uri_together(
    graph_backend: "FabricHandle",
) -> None:
    """Uniqueness is ``(tenant_id, entity_uri)``, not ``entity_uri`` (INV-CH7-16).

    The same URI under two tenants is two distinct nodes; the same URI twice
    under one tenant is one node.
    """
    graph_backend.worker.admit_entity_claim(
        tenant_id=TENANT_A,
        claim=entity(tenant_id=TENANT_A, attributes={"legal_name": "Acme A"}),
    )
    graph_backend.worker.admit_entity_claim(
        tenant_id=TENANT_B,
        claim=entity(tenant_id=TENANT_B, attributes={"legal_name": "Acme B"}),
    )

    a_history = graph_backend.reader.entity_history(
        tenant_id=TENANT_A, entity_uri="counterparty://acme"
    )
    b_history = graph_backend.reader.entity_history(
        tenant_id=TENANT_B, entity_uri="counterparty://acme"
    )

    assert len(a_history) == 1
    assert len(b_history) == 1
    assert a_history[0].claim.attributes["legal_name"] == "Acme A"
    assert b_history[0].claim.attributes["legal_name"] == "Acme B"


def test_reads_never_cross_the_tenant_boundary(
    graph_backend: "FabricHandle",
) -> None:
    """No code path resolves an entity without tenant scope (D-IMPL-05)."""
    graph_backend.worker.admit_entity_claim(
        tenant_id=TENANT_B,
        claim=entity(tenant_id=TENANT_B, entity_uri="counterparty://only-b"),
    )

    view = graph_backend.reader.as_of(tenant_id=TENANT_A, at=T2)

    assert view.entities == ()
    assert (
        graph_backend.reader.entity_history(
            tenant_id=TENANT_A, entity_uri="counterparty://only-b"
        )
        == ()
    )


def test_claim_tenant_must_agree_with_the_call_scope(
    graph_backend: "FabricHandle",
) -> None:
    """A claim that disagrees with its call scope is refused, not reconciled.

    Silently trusting either side would make cross-tenant writes a typo away.
    """
    with pytest.raises(ValueError, match="tenant"):
        graph_backend.worker.admit_entity_claim(
            tenant_id=TENANT_A, claim=entity(tenant_id=TENANT_B)
        )


# --- Semantic 5: per-relationship-type edge lineage -------------------------


def test_relationships_are_first_class_with_their_own_lineage(
    graph_backend: "FabricHandle",
) -> None:
    """Edges are persisted, typed, and carry their own lineage (INV-CH7-20).

    Not derived joins: a relationship accumulates multi-source evidence exactly
    as an entity does, and two relationship *types* over the same endpoints are
    two distinct edges.
    """
    obligor_core = relationship(lineage_entries=(lineage("core-banking", "e1", T1),))
    obligor_kyc = relationship(lineage_entries=(lineage("kyc-registry", "e2", T1),))
    guarantee = relationship(relationship_type="guarantees")

    first = graph_backend.worker.admit_relationship_claim(
        tenant_id=TENANT_A, claim=obligor_core
    )
    second = graph_backend.worker.admit_relationship_claim(
        tenant_id=TENANT_A, claim=obligor_kyc
    )
    third = graph_backend.worker.admit_relationship_claim(
        tenant_id=TENANT_A, claim=guarantee
    )

    assert second.node_key == first.node_key
    assert second.lineage_added == 1
    assert third.node_key != first.node_key, "type is part of edge identity"

    history = graph_backend.reader.relationship_history(
        tenant_id=TENANT_A, relationship_key=first.node_key
    )
    assert len(history) == 1
    assert {e.source.system_id for e in history[0].claim.lineage} == {
        "core-banking",
        "kyc-registry",
    }

    view = graph_backend.reader.as_of(tenant_id=TENANT_A, at=T2)
    assert {r.claim.relationship_type for r in view.relationships} == {
        "obligor_of",
        "guarantees",
    }


def test_graph_view_ordering_is_deterministic(
    graph_backend: "FabricHandle",
) -> None:
    """A view must serialize identically however it was assembled.

    Operator composition is asserted bit-for-bit downstream (whitepaper §7.4);
    an insertion-ordered view would make that assertion a coin flip.
    """
    for uri in ("counterparty://zeta", "counterparty://alpha", "counterparty://mid"):
        graph_backend.worker.admit_entity_claim(
            tenant_id=TENANT_A, claim=entity(entity_uri=uri)
        )

    view = graph_backend.reader.as_of(tenant_id=TENANT_A, at=T2)

    uris = [r.claim.entity_uri for r in view.entities]
    assert uris == sorted(uris)


def test_policy_bundle_version_is_stamped_at_assembly_time(
    graph_backend: "FabricHandle",
) -> None:
    """P travels with the subgraph, bound at assembly (INV-CH7-03).

    The fabric does not persist state first and ask who may see it afterwards.
    """
    graph_backend.worker.admit_entity_claim(tenant_id=TENANT_A, claim=entity())

    view = graph_backend.reader.as_of(tenant_id=TENANT_A, at=T2)

    assert view.entities[0].policy_bundle_version == (
        graph_backend.worker.policy_bundle_version
    )
    assert view.entities[0].policy_bundle_version != ""
