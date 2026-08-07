"""The differential suite — every backend byte-identical to the fallback (D-05).

D-05 artifact 3a: the prose decides (``docs/GRAPH_QUERY_SEMANTICS.md``), the
fallback executes it, the property suite audits the fallback
(``tests/conformance/test_substrate_properties.py``) — and *this* suite holds
every registered backend byte-identical to the fallback over the generated
corpus (``tests/conformance/query_corpus.py``), which deliberately includes
the shapes where the known defects would hide: mixed-admissibility multi-hop
paths (Pitfall 1), the D-IMPL-87 ``allowed_entities`` resurrection chain
(Pitfall 2 — in-set seed and target, out-of-set intermediate), depth-0/1 and
mixed-direction chains (Pitfall 3), orphaned nodes, self-loops, and the
dangling first-class edge.

**Scope: query-level facts only.** This suite pins byte-identity,
determinism, and the tenant boundary of ``reader.query()``. The D-01 "pin
the split itself" obligation — which segments the engine issued, in which
order, with which survivor sets — is an engine-level fact and belongs
exclusively to plan 15.2-07's tests. No segmentation or pin-sequence
assertion may be added here: a query-level suite asserting engine internals
would couple every adapter's conformance to the planner's shape.

**Property coverage per adapter — the direct subset and the transitivity
reading.** D-06 says every adapter runs under BOTH suites. For the always-on
params (sqlite, memory) property coverage must not be transitive-only, so a
DIRECT property-assertion subset runs against each always-on param's own
``reader.query()``: the INV-CH7-14 as-of assertions, the hop-admissibility
seed-excluded-target shape (Pitfall 1), the ``allowed_entities``
resurrection-closure shape (Pitfall 2 — the amendment's defect, held
directly per adapter), and the determinism twin. For extras-gated adapters
(neo4j, mongo — plans 15.2-12/-13), property coverage is TRANSITIVE through
differential byte-identity with the audited fallback: an adapter
byte-identical to the fallback over the corpus inherits every property the
fallback was audited under. That reading is recorded here and is presented
for Dave's ratification in the 15.2-14 design-choice register.

Two disciplines inherited from ``tests/conformance/test_graphstore.py``:

* **Nothing constructs a writer.** Every corpus write goes through the L2
  admission path of a fabric booted by the real composition root; this
  module imports nothing from ``ccf.graph._writer`` (RESEARCH Pitfall 6 —
  the suite must not become the second writer it exists to catch).
* **Comparisons happen on canonical bytes, never raw rows** — what keeps
  the suite backend-neutral instead of backend-flaky.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

import pytest
from hypothesis import HealthCheck, given, settings

from ccf.contracts.canonical import canonical_bytes
from ccf.graph.fallback import answer
from ccf.graph.protocols import (
    EntityRecord,
    GraphQuery,
    GraphView,
    RelationshipRecord,
)

from tests.conformance.query_corpus import (
    EARLY,
    LATE,
    ON_BOUNDARY,
    CorpusCase,
    TENANT,
    build_queries,
    chain_claims,
    chain_uris,
    corpus_cases,
    entity_claim,
)
from tests.conformance.test_substrate_properties import (
    CHAIN_TRAVERSE,
    EXCLUDED_CLASSIFICATION,
    PERMITTED_CLASSIFICATION,
    PERMITTED_CLASSIFICATIONS,
    SEED_CLASS,
)
from tests.properties.strategies import CLASSIFICATION_ATTRIBUTE, ENTITY_POOL

if TYPE_CHECKING:
    from datetime import datetime

    from ccf.boot import FabricHandle

pytestmark = pytest.mark.conformance

#: The always-on params run in every `make ci`; postgres carries its mark and
#: runs the identical tests against a real server in CI (D-10/D-11).
BACKEND_PARAMS = (
    pytest.param("sqlite"),
    pytest.param("memory"),
    pytest.param("postgres", marks=pytest.mark.postgres),
)


@pytest.fixture(params=BACKEND_PARAMS)
def backend_name(request: pytest.FixtureRequest) -> str:
    """Which substrate this run answers from — no test body knows or cares."""
    return str(request.param)


@pytest.fixture
def substrate_fabric(
    backend_name: str, fabric_boot: Callable[..., "FabricHandle"]
) -> "FabricHandle":
    """One booted fabric per backend param, for the deterministic tests."""
    return fabric_boot(backend=backend_name)


def _frozen_at(
    entities: Sequence[EntityRecord],
    relationships: Sequence[RelationshipRecord],
    *,
    tenant_id: str,
    as_of: "datetime",
) -> GraphView:
    """Freeze a fallback answer under the interface's ordering (`GQ-22`).

    The differential comparison happens between two frozen views on
    canonical bytes; the expected side freezes here exactly as the
    interface freezes the answered side.
    """
    return GraphView(
        tenant_id=tenant_id,
        as_of=as_of,
        entities=tuple(sorted(entities, key=lambda r: r.claim.entity_uri)),
        relationships=tuple(
            sorted(relationships, key=lambda r: r.relationship_key)
        ),
    )


def _expected(handle: "FabricHandle", q: GraphQuery) -> GraphView:
    """The fallback-derived expected view: the oracle over the full as-of state."""
    full = handle.reader.as_of(tenant_id=q.tenant_id, at=q.as_of)
    entities, relationships = answer(
        full.entities, full.relationships, query=q
    )
    return _frozen_at(
        entities, relationships, tenant_id=q.tenant_id, as_of=q.as_of
    )


def _write_case(handle: "FabricHandle", case: CorpusCase) -> None:
    """Write the case's content through booted L2 — the only write path."""
    for claim in case.entities:
        handle.worker.admit_entity_claim(tenant_id=TENANT, claim=claim)
    for edge in case.relationships:
        handle.worker.admit_relationship_claim(tenant_id=TENANT, claim=edge)


# --- the differential bar ----------------------------------------------------


@given(case=corpus_cases())
@settings(
    # The factory boots a FRESH fabric per drawn example, which is exactly
    # the isolation the function_scoped_fixture health check exists to
    # demand — the fixture value is a factory, not shared state, so
    # suppressing the check is honest rather than convenient.
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=25,
)
def test_every_backend_answers_byte_identical_to_the_fallback(
    backend_name: str,
    fabric_boot: Callable[..., "FabricHandle"],
    case: CorpusCase,
) -> None:
    """The D-05 differential assertion, plus the determinism twin.

    Per corpus query: ``canonical_bytes(reader.query(q))`` equals
    ``canonical_bytes`` of the fallback-derived expected view — byte
    identity, never raw-row comparison — and a second asking answers the
    identical bytes.
    """
    handle = fabric_boot(backend=backend_name)
    _write_case(handle, case)
    for q in build_queries(
        case, policy_bundle_version=handle.worker.policy_bundle_version
    ):
        answered = handle.reader.query(q)
        expected = _expected(handle, q)
        assert canonical_bytes(answered) == canonical_bytes(expected), (
            f"{backend_name} diverged from the fallback on corpus case"
            f" {case.name!r}"
        )
        # The determinism twin: same question, same bytes.
        assert canonical_bytes(handle.reader.query(q)) == canonical_bytes(
            answered
        )


# --- the tenant boundary, as a query() twin ---------------------------------


def test_query_reads_never_cross_the_tenant_boundary(
    substrate_fabric: "FabricHandle",
) -> None:
    """The ``query()`` twin of the graphstore suite's tenant-boundary test.

    State written under one tenant is invisible to another tenant's
    questions — degenerate and predicate-bearing alike — on every param
    (D-IMPL-05; threat T-15.2-02).
    """
    tenant_b = f"{TENANT}-b"
    claim = entity_claim(
        entity_uri=ENTITY_POOL[SEED_CLASS][0],
        entity_class=SEED_CLASS,
        classification=PERMITTED_CLASSIFICATION,
        observed_at=EARLY,
        tenant_id=tenant_b,
    )
    substrate_fabric.worker.admit_entity_claim(tenant_id=tenant_b, claim=claim)

    degenerate = substrate_fabric.reader.query(
        GraphQuery(tenant_id=TENANT, as_of=LATE)
    )
    assert degenerate.entities == ()
    assert degenerate.relationships == ()

    constrained = substrate_fabric.reader.query(
        GraphQuery(
            tenant_id=TENANT,
            as_of=LATE,
            allowed_entities=frozenset({claim.entity_uri}),
            traverse=CHAIN_TRAVERSE,
        )
    )
    assert constrained.entities == ()

    own_view = substrate_fabric.reader.query(
        GraphQuery(tenant_id=tenant_b, as_of=LATE)
    )
    assert [record.claim.entity_uri for record in own_view.entities] == [
        claim.entity_uri
    ]


# --- the direct property subset, per always-on param -------------------------
#
# These re-assert the named invariants against each param's own
# reader.query(), reusing the shapes and vocabulary of
# test_substrate_properties rather than re-implementing them: the fallback
# was audited under these names; the always-on adapters are held to them
# directly, not only transitively.


def test_as_of_cut_holds_directly_on_each_reader(
    substrate_fabric: "FabricHandle",
) -> None:
    """INV-CH7-14, directly per param: no future information in an as-of answer.

    A claim observed after ``q.as_of`` never appears (late-observed half);
    a claim superseded after ``q.as_of`` is still current and renders with
    no supersession edge (early-superseded completeness half).
    """
    uri = ENTITY_POOL[SEED_CLASS][0]
    original = entity_claim(
        entity_uri=uri,
        entity_class=SEED_CLASS,
        classification=PERMITTED_CLASSIFICATION,
        observed_at=EARLY,
    )
    revised = entity_claim(
        entity_uri=uri,
        entity_class=SEED_CLASS,
        classification=EXCLUDED_CLASSIFICATION,
        observed_at=LATE,
    )
    substrate_fabric.worker.admit_entity_claim(tenant_id=TENANT, claim=original)
    superseding = substrate_fabric.worker.admit_entity_claim(
        tenant_id=TENANT, claim=revised
    )
    assert superseding.superseded_claim_id is not None

    between = substrate_fabric.reader.query(
        GraphQuery(tenant_id=TENANT, as_of=ON_BOUNDARY)
    )
    (record,) = between.entities
    attribute = CLASSIFICATION_ATTRIBUTE[SEED_CLASS]
    assert record.claim.attributes[attribute] == PERMITTED_CLASSIFICATION
    assert record.claim.observed_at <= ON_BOUNDARY
    # Superseded LATER: still current, and the future edge does not leak.
    assert record.superseded_by is None
    assert record.superseded_at is None

    after = substrate_fabric.reader.query(
        GraphQuery(tenant_id=TENANT, as_of=LATE)
    )
    (current,) = after.entities
    assert current.claim.attributes[attribute] == EXCLUDED_CLASSIFICATION


def test_hop_admissibility_holds_directly_on_each_reader(
    substrate_fabric: "FabricHandle",
) -> None:
    """Pitfall 1 directly per param: prune before walking (INV-CH7-40, `GQ-13`).

    Two chains in one graph: chain 0 with a policy-excluded intermediate,
    chain 1 fully admissible. The walk must not reach chain 0's target
    through its excluded middle, while chain 1's target — the control leg
    proving this test would catch the leak — is reached.
    """
    excluded_entities, excluded_edges = chain_claims(
        mid_classification=EXCLUDED_CLASSIFICATION, index=0
    )
    control_entities, control_edges = chain_claims(
        mid_classification=PERMITTED_CLASSIFICATION, index=1
    )
    for claim in (*excluded_entities, *control_entities):
        substrate_fabric.worker.admit_entity_claim(tenant_id=TENANT, claim=claim)
    for edge in (*excluded_edges, *control_edges):
        substrate_fabric.worker.admit_relationship_claim(
            tenant_id=TENANT, claim=edge
        )

    q = GraphQuery(
        tenant_id=TENANT,
        as_of=ON_BOUNDARY,
        traverse=CHAIN_TRAVERSE,
        permitted_policy_bundle_versions=frozenset(
            {substrate_fabric.worker.policy_bundle_version}
        ),
        classification_attribute_by_class=dict(CLASSIFICATION_ATTRIBUTE),
        permitted_classifications=frozenset(PERMITTED_CLASSIFICATIONS),
    )
    answered = {
        record.claim.entity_uri
        for record in substrate_fabric.reader.query(q).entities
    }

    seed_0, mid_0, target_0 = chain_uris(0)
    seed_1, mid_1, target_1 = chain_uris(1)
    assert mid_0 not in answered, "excluded state must be structurally absent"
    assert target_0 not in answered, "a path through an excluded node exists"
    assert {seed_1, mid_1, target_1} <= answered, "the control leg must reach"


def test_resurrection_closure_holds_directly_on_each_reader(
    substrate_fabric: "FabricHandle",
) -> None:
    """Pitfall 2 directly per param: the amendment's defect, closed (D-IMPL-87).

    Seed and target IN the allowed set, intermediate OUT of it, everything
    policy-admissible — only the uniform rule (`GQ-15`) stands between the
    walk and the target, and the target is provably not reached. The
    control leg (intermediate in-set) proves the walk reaches the target
    when the set admits the path.
    """
    entities, relationships = chain_claims(
        mid_classification=PERMITTED_CLASSIFICATION
    )
    for claim in entities:
        substrate_fabric.worker.admit_entity_claim(tenant_id=TENANT, claim=claim)
    for edge in relationships:
        substrate_fabric.worker.admit_relationship_claim(
            tenant_id=TENANT, claim=edge
        )
    seed_uri, mid_uri, target_uri = chain_uris()

    resurrection = substrate_fabric.reader.query(
        GraphQuery(
            tenant_id=TENANT,
            as_of=ON_BOUNDARY,
            traverse=CHAIN_TRAVERSE,
            allowed_entities=frozenset({seed_uri, target_uri}),
        )
    )
    answered = {record.claim.entity_uri for record in resurrection.entities}
    assert target_uri not in answered, "the walk crossed outside the set"
    assert answered == {seed_uri}
    assert resurrection.relationships == ()

    control = substrate_fabric.reader.query(
        GraphQuery(
            tenant_id=TENANT,
            as_of=ON_BOUNDARY,
            traverse=CHAIN_TRAVERSE,
            allowed_entities=frozenset({seed_uri, mid_uri, target_uri}),
        )
    )
    assert {record.claim.entity_uri for record in control.entities} == {
        seed_uri,
        mid_uri,
        target_uri,
    }


def test_repeat_query_answers_are_deterministic_on_each_reader(
    substrate_fabric: "FabricHandle",
) -> None:
    """The determinism twin, directly per param, on a fully loaded question."""
    entities, relationships = chain_claims(
        mid_classification=PERMITTED_CLASSIFICATION
    )
    for claim in entities:
        substrate_fabric.worker.admit_entity_claim(tenant_id=TENANT, claim=claim)
    for edge in relationships:
        substrate_fabric.worker.admit_relationship_claim(
            tenant_id=TENANT, claim=edge
        )
    seed_uri, mid_uri, target_uri = chain_uris()
    q = GraphQuery(
        tenant_id=TENANT,
        as_of=ON_BOUNDARY,
        require_valid_at_boundary=True,
        traverse=CHAIN_TRAVERSE,
        allowed_entities=frozenset({seed_uri, mid_uri, target_uri}),
        permitted_policy_bundle_versions=frozenset(
            {substrate_fabric.worker.policy_bundle_version}
        ),
        classification_attribute_by_class=dict(CLASSIFICATION_ATTRIBUTE),
        permitted_classifications=frozenset(PERMITTED_CLASSIFICATIONS),
    )
    first = substrate_fabric.reader.query(q)
    second = substrate_fabric.reader.query(q)
    assert canonical_bytes(first) == canonical_bytes(second)
