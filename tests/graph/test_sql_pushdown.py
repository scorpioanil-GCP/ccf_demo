"""Pushdown unit tests — the translated SQL path proven, not assumed (15.2-09).

The differential suite (``tests/conformance/test_substrate_differential.py``)
holds every backend byte-identical to the fallback over the corpus, but byte
identity alone cannot tell a *pushed* answer from a silently-degraded one —
D-04 makes the two indistinguishable everywhere except telemetry. This module
asserts the distinction where the known defects would hide: every named shape
is asked with a counter assertion proving ``_translate_query`` actually
answered (``translated_answers`` incremented, ``fallback_answers`` did not),
so the hop-admissibility and resurrection closures are proven *of the SQL*,
not of the fallback the SQL might have quietly deferred to.

The shapes, and the clauses they pin:

* the full policy+temporal+traverse question — the common no-Similarity plan
  pushed whole (`GQ-32` at docs/GRAPH_QUERY_SEMANTICS.md:583);
* depth-0 — the CTE base case alone answers the walk starting points only
  (`GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201);
* the Pitfall-1 chain — a policy-excluded intermediate does not bridge the
  pushed walk (`GQ-13` at docs/GRAPH_QUERY_SEMANTICS.md:261);
* the RESURRECTION chain — in-set seed and target, out-of-set intermediate:
  the pushed walk does not cross outside ``allowed_entities`` (`GQ-15` at
  docs/GRAPH_QUERY_SEMANTICS.md:300; D-IMPL-87; threat T-15.2-26);
* the empty survivor set — the empty answer without a substrate round trip
  (`GQ-04` at docs/GRAPH_QUERY_SEMANTICS.md:98);
* the validity window across both claim-JSON timestamp widths — the
  whole-second ``Z`` rendering and the fixed-width canonical boundary must
  compare chronologically in SQL (`GQ-09` at
  docs/GRAPH_QUERY_SEMANTICS.md:185; `GQ-24` at
  docs/GRAPH_QUERY_SEMANTICS.md:482);
* the unsafe-attribute-name decline — the one ``None`` the sqlite translation
  returns, proven to land on the fallback byte-identically (`GQ-32`, D-04).

Disciplines inherited from the differential suite: every write goes through
booted L2 (nothing here constructs a writer), and every equality is asserted
on canonical bytes, never raw rows.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

import pytest

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
    ON_BOUNDARY,
    TENANT,
    chain_claims,
    chain_uris,
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

#: sqlite runs always-on; the postgres twins carry their mark and run against
#: a real server on the CI service leg (D-10/D-11).
BACKEND_PARAMS = (
    pytest.param("sqlite"),
    pytest.param("postgres", marks=pytest.mark.postgres),
)


@pytest.fixture(params=BACKEND_PARAMS)
def backend_name(request: pytest.FixtureRequest) -> str:
    """Which SQL substrate this run pushes into."""
    return str(request.param)


@pytest.fixture
def pushdown_fabric(
    backend_name: str, fabric_boot: Callable[..., "FabricHandle"]
) -> "FabricHandle":
    """One booted fabric per backend param — writes go through L2 only."""
    return fabric_boot(backend=backend_name)


def _frozen(
    entities: Sequence[EntityRecord],
    relationships: Sequence[RelationshipRecord],
    *,
    tenant_id: str,
    as_of: "datetime",
) -> GraphView:
    """Freeze a fallback answer under the interface's ordering (`GQ-22`)."""
    return GraphView(
        tenant_id=tenant_id,
        as_of=as_of,
        entities=tuple(sorted(entities, key=lambda r: r.claim.entity_uri)),
        relationships=tuple(
            sorted(relationships, key=lambda r: r.relationship_key)
        ),
    )


def _expected(handle: "FabricHandle", q: GraphQuery) -> GraphView:
    """The fallback-derived oracle over the full as-of state.

    Computed AFTER the counter assertions in every test below: this helper
    itself routes a degenerate query through ``reader.query()``, so calling
    it inside a counter window would make the telemetry assertion count the
    oracle's own read.
    """
    full = handle.reader.as_of(tenant_id=q.tenant_id, at=q.as_of)
    entities, relationships = answer(
        full.entities, full.relationships, query=q
    )
    return _frozen(
        entities, relationships, tenant_id=q.tenant_id, as_of=q.as_of
    )


def _write_chain(
    handle: "FabricHandle", *, mid_classification: str, index: int = 0
) -> None:
    """Write the seed - mid - target chain through booted L2."""
    entities, relationships = chain_claims(
        mid_classification=mid_classification, index=index
    )
    for claim in entities:
        handle.worker.admit_entity_claim(tenant_id=TENANT, claim=claim)
    for edge in relationships:
        handle.worker.admit_relationship_claim(tenant_id=TENANT, claim=edge)


def _pushed(handle: "FabricHandle", q: GraphQuery) -> GraphView:
    """Ask ``q`` and assert the translation answered it — not the fallback.

    The counter pair is the proof the push happened where a defect would
    hide: a translation that silently declined would keep byte-identity
    (D-04) while the defect it was supposed to close went unexercised.
    """
    translated_before = handle.reader.translated_answers
    fallback_before = handle.reader.fallback_answers
    answered = handle.reader.query(q)
    assert handle.reader.translated_answers == translated_before + 1, (
        "the substrate translation did not fire — the answer fell back"
    )
    assert handle.reader.fallback_answers == fallback_before
    return answered


def _policy_family(handle: "FabricHandle") -> dict[str, object]:
    """The whole policy family (`GQ-02`), bound to the booted bundle version."""
    return {
        "permitted_policy_bundle_versions": frozenset(
            {handle.worker.policy_bundle_version}
        ),
        "classification_attribute_by_class": dict(CLASSIFICATION_ATTRIBUTE),
        "permitted_classifications": frozenset(PERMITTED_CLASSIFICATIONS),
    }


def test_the_full_predicate_stack_is_answered_by_the_substrate(
    pushdown_fabric: "FabricHandle",
) -> None:
    """The common no-Similarity plan's query pushes whole, byte-identically.

    Policy + temporal + traverse in one statement pair (`GQ-32` at
    docs/GRAPH_QUERY_SEMANTICS.md:583), proven pushed by telemetry and
    proven right by canonical-byte equality with the fallback oracle.
    """
    _write_chain(pushdown_fabric, mid_classification=PERMITTED_CLASSIFICATION)
    q = GraphQuery(
        tenant_id=TENANT,
        as_of=ON_BOUNDARY,
        require_valid_at_boundary=True,
        traverse=CHAIN_TRAVERSE,
        **_policy_family(pushdown_fabric),  # type: ignore[arg-type]
    )
    answered = _pushed(pushdown_fabric, q)
    assert canonical_bytes(answered) == canonical_bytes(
        _expected(pushdown_fabric, q)
    )
    reached = {record.claim.entity_uri for record in answered.entities}
    assert reached == set(chain_uris())


def test_depth_zero_answers_exactly_the_walk_starting_points(
    pushdown_fabric: "FabricHandle",
) -> None:
    """``depth_limit=0`` is the CTE base case alone (`GQ-10`).

    The walk starting points only — a legal, meaningful bound, not an
    error and not "unlimited" (`GQ-10` at
    docs/GRAPH_QUERY_SEMANTICS.md:201).
    """
    _write_chain(pushdown_fabric, mid_classification=PERMITTED_CLASSIFICATION)
    seed_uri, _, _ = chain_uris()
    q = GraphQuery(
        tenant_id=TENANT,
        as_of=ON_BOUNDARY,
        traverse=CHAIN_TRAVERSE.model_copy(update={"depth_limit": 0}),
    )
    answered = _pushed(pushdown_fabric, q)
    assert [record.claim.entity_uri for record in answered.entities] == [
        seed_uri
    ]
    assert canonical_bytes(answered) == canonical_bytes(
        _expected(pushdown_fabric, q)
    )


def test_excluded_intermediate_does_not_bridge_the_pushed_walk(
    pushdown_fabric: "FabricHandle",
) -> None:
    """Pitfall 1 in the CTE: prune on every hop, not the result set.

    Chain 0 carries a policy-excluded intermediate; chain 1 is the fully
    admissible control leg proving the walk *would* reach a target the
    predicates admit. The pushed recursive term must not cross chain 0's
    excluded middle (`GQ-13` at docs/GRAPH_QUERY_SEMANTICS.md:261,
    INV-CH7-40; threat T-15.2-03).
    """
    _write_chain(
        pushdown_fabric, mid_classification=EXCLUDED_CLASSIFICATION, index=0
    )
    _write_chain(
        pushdown_fabric, mid_classification=PERMITTED_CLASSIFICATION, index=1
    )
    q = GraphQuery(
        tenant_id=TENANT,
        as_of=ON_BOUNDARY,
        traverse=CHAIN_TRAVERSE,
        **_policy_family(pushdown_fabric),  # type: ignore[arg-type]
    )
    answered = _pushed(pushdown_fabric, q)
    reached = {record.claim.entity_uri for record in answered.entities}

    seed_0, mid_0, target_0 = chain_uris(0)
    seed_1, mid_1, target_1 = chain_uris(1)
    assert mid_0 not in reached, "excluded state must be structurally absent"
    assert target_0 not in reached, "a path through an excluded node exists"
    assert {seed_1, mid_1, target_1} <= reached, "the control leg must reach"
    assert canonical_bytes(answered) == canonical_bytes(
        _expected(pushdown_fabric, q)
    )


def test_pushed_resurrection_shape_does_not_cross_outside_the_set(
    pushdown_fabric: "FabricHandle",
) -> None:
    """The D-IMPL-87 defect closed in SQL, on the shape plans actually issue.

    The segment-2 query of a multi-segment plan — temporal + traverse +
    ``allowed_entities`` — with seed and target IN the set and the
    intermediate OUT of it, everything policy-admissible: only the uniform
    rule (`GQ-15` at docs/GRAPH_QUERY_SEMANTICS.md:300) stands between the
    walk and the target. ``translated_answers`` proves the SQL path
    answered — the one place the resurrection defect could hide behind a
    silently-conformant fallback (threat T-15.2-26). The control leg
    proves the walk reaches the target when the set admits the path.
    """
    _write_chain(pushdown_fabric, mid_classification=PERMITTED_CLASSIFICATION)
    seed_uri, mid_uri, target_uri = chain_uris()

    resurrection = GraphQuery(
        tenant_id=TENANT,
        as_of=ON_BOUNDARY,
        require_valid_at_boundary=True,
        traverse=CHAIN_TRAVERSE,
        allowed_entities=frozenset({seed_uri, target_uri}),
    )
    answered = _pushed(pushdown_fabric, resurrection)
    reached = {record.claim.entity_uri for record in answered.entities}
    assert target_uri not in reached, "the pushed walk crossed outside the set"
    assert reached == {seed_uri}
    assert answered.relationships == ()
    assert canonical_bytes(answered) == canonical_bytes(
        _expected(pushdown_fabric, resurrection)
    )

    control = GraphQuery(
        tenant_id=TENANT,
        as_of=ON_BOUNDARY,
        require_valid_at_boundary=True,
        traverse=CHAIN_TRAVERSE,
        allowed_entities=frozenset({seed_uri, mid_uri, target_uri}),
    )
    control_answered = _pushed(pushdown_fabric, control)
    assert {
        record.claim.entity_uri for record in control_answered.entities
    } == {seed_uri, mid_uri, target_uri}
    assert canonical_bytes(control_answered) == canonical_bytes(
        _expected(pushdown_fabric, control)
    )


def test_empty_allowed_entities_answers_empty_from_the_hook(
    pushdown_fabric: "FabricHandle",
) -> None:
    """The empty survivor set IS the answer — no substrate round trip.

    ``allowed_entities=frozenset()`` is a different fact from ``None``
    (`GQ-04` at docs/GRAPH_QUERY_SEMANTICS.md:98): the hook answers the
    empty view itself, counted as a translated answer, and an empty answer
    is an answer, never an error (`GQ-23` at
    docs/GRAPH_QUERY_SEMANTICS.md:474).
    """
    _write_chain(pushdown_fabric, mid_classification=PERMITTED_CLASSIFICATION)
    q = GraphQuery(
        tenant_id=TENANT, as_of=ON_BOUNDARY, allowed_entities=frozenset()
    )
    answered = _pushed(pushdown_fabric, q)
    assert answered.entities == ()
    assert answered.relationships == ()
    assert canonical_bytes(answered) == canonical_bytes(
        _expected(pushdown_fabric, q)
    )


def test_validity_window_pushes_across_both_claim_json_widths(
    pushdown_fabric: "FabricHandle",
) -> None:
    """`GQ-09` pushed over the claim's own JSON renderings, both widths.

    Claim JSON renders whole-second UTC instants without a fractional part
    while the bound boundary is fixed-width canonical text — forms that do
    NOT compare chronologically as raw text (``...00Z`` sorts after
    ``...00.000000Z``). A naive text comparison would empty this answer;
    the width-normalized pushed predicate must keep the still-valid chain
    (`GQ-24` at docs/GRAPH_QUERY_SEMANTICS.md:482) and exclude the claim
    whose ``valid_to`` closed at the boundary (`GQ-09` at
    docs/GRAPH_QUERY_SEMANTICS.md:185).
    """
    _write_chain(pushdown_fabric, mid_classification=PERMITTED_CLASSIFICATION)
    expired_uri = ENTITY_POOL[SEED_CLASS][1]
    pushdown_fabric.worker.admit_entity_claim(
        tenant_id=TENANT,
        claim=entity_claim(
            entity_uri=expired_uri,
            entity_class=SEED_CLASS,
            classification=PERMITTED_CLASSIFICATION,
            observed_at=EARLY,
            valid_to=ON_BOUNDARY,
        ),
    )
    q = GraphQuery(
        tenant_id=TENANT, as_of=ON_BOUNDARY, require_valid_at_boundary=True
    )
    answered = _pushed(pushdown_fabric, q)
    surviving = {record.claim.entity_uri for record in answered.entities}
    assert surviving == set(chain_uris()), (
        "the still-valid chain must survive the pushed validity window"
    )
    assert expired_uri not in surviving
    assert canonical_bytes(answered) == canonical_bytes(
        _expected(pushdown_fabric, q)
    )


def test_unsafe_attribute_name_declines_to_the_fallback(
    fabric_boot: Callable[..., "FabricHandle"],
) -> None:
    """The one sqlite decline: a name the JSON path cannot carry literally.

    ``$.attributes.a.b`` names a *nested* key, so an attribute name with a
    dot cannot be pushed as a bound path without changing meaning; the
    translation returns ``None`` at its single named validation site and
    the fallback answers the whole query (`GQ-32` at
    docs/GRAPH_QUERY_SEMANTICS.md:583) — byte-identical under D-04,
    visible only in telemetry. sqlite-only: the postgres dialect binds the
    bare key, not a path, and translates any name.
    """
    handle = fabric_boot(backend="sqlite")
    _write_chain(handle, mid_classification=PERMITTED_CLASSIFICATION)
    q = GraphQuery(
        tenant_id=TENANT,
        as_of=ON_BOUNDARY,
        permitted_policy_bundle_versions=frozenset(
            {handle.worker.policy_bundle_version}
        ),
        classification_attribute_by_class={SEED_CLASS: "not.a.plain.name"},
        permitted_classifications=frozenset(PERMITTED_CLASSIFICATIONS),
    )
    translated_before = handle.reader.translated_answers
    fallback_before = handle.reader.fallback_answers
    answered = handle.reader.query(q)
    assert handle.reader.translated_answers == translated_before
    assert handle.reader.fallback_answers == fallback_before + 1
    assert canonical_bytes(answered) == canonical_bytes(_expected(handle, q))
