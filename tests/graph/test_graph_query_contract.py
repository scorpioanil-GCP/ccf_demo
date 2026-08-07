"""The query vocabulary, pinned: hash identity, closure, and tiers (15.2-04).

Phase 15.2 landed the contract family the ``GraphReader.query()`` seam speaks
— ``GraphQuery``, ``TraversalSpec``, ``QueryFragment``, ``SourceAttestation``
— as frozen values rendering ``docs/GRAPH_QUERY_SEMANTICS.md`` clause-for-
clause. Five facts must stay true for plans 05-13 to build on them, and each
gets one test here:

* **Determinism** — ``content_hash(q)`` is the per-round-trip replay pin
  (D-02), so two structurally equal queries must produce identical bytes
  whatever order their frozensets were constructed in, and any one-field
  difference must produce a different pin.
* **Survivor-set identity** — ``allowed_entities`` is part of the question's
  identity (the D-IMPL-87 pin surface): ``None``, the empty set, and a
  populated set are three different questions with three different hashes,
  so a capped (in-process) execution and a pushed execution can never share
  a pin.
* **Closure** — ``extra=forbid`` refuses unknown fields at construction and
  ``frozen`` refuses mutation afterwards: the bytes always describe the
  value that was validated.
* **Tier values** — the three D-09 attestation tiers are three well-known
  values of one schema, tier 3 (``none``/``none``/``None``) included — the
  no-refactor commitment pinned as a test.
* **The degenerate query** — ``tenant_id`` + ``as_of`` alone is the
  everything-question every adapter will answer (D-07), constructible and
  hashable with ``allowed_entities`` ``None``.

A sixth test pins T-15.2-26's mitigation structurally: ``QueryFragment``
declares no ``allowed_entities`` field, so no operator's declared intent can
smuggle a survivor set — the constraint is engine-authored only.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ccf.contracts.canonical import content_hash
from ccf.graph.protocols import (
    GraphQuery,
    QueryFragment,
    SourceAttestation,
    TraversalSpec,
)
from ccf.peering.protocol import PeerRef

TENANT = "tenant-a"
AT = datetime(2026, 3, 1, tzinfo=UTC)


def _traverse() -> TraversalSpec:
    return TraversalSpec(
        seed_entity_classes=frozenset({"account", "person"}),
        relationship_types=frozenset({"owns", "controls"}),
        depth_limit=2,
    )


def _full_query(**overrides: object) -> GraphQuery:
    """A query carrying every family, so one-field variation is expressible."""
    fields: dict[str, object] = {
        "tenant_id": TENANT,
        "as_of": AT,
        "permitted_policy_bundle_versions": frozenset({"pb-1", "pb-2"}),
        "classification_attribute_by_class": {
            "account": "sensitivity",
            "person": "clearance",
        },
        "permitted_classifications": frozenset({"public", "internal"}),
        "require_valid_at_boundary": True,
        "traverse": _traverse(),
        "seeds": frozenset({"urn:e:1", "urn:e:2"}),
        "allowed_entities": None,
    }
    fields.update(overrides)
    return GraphQuery.model_validate(fields)


class TestContentHashDeterminism:
    """``content_hash(GraphQuery)`` is well-defined over the value (D-02)."""

    def test_equal_values_hash_identically_whatever_the_set_order(self) -> None:
        forward = _full_query(
            permitted_policy_bundle_versions=frozenset(["pb-1", "pb-2"]),
            seeds=frozenset(["urn:e:1", "urn:e:2"]),
        )
        reversed_ = _full_query(
            permitted_policy_bundle_versions=frozenset(["pb-2", "pb-1"]),
            seeds=frozenset(["urn:e:2", "urn:e:1"]),
        )
        assert content_hash(forward) == content_hash(reversed_)

    def test_one_field_difference_changes_the_pin(self) -> None:
        baseline = _full_query()
        variants = (
            _full_query(tenant_id="tenant-b"),
            _full_query(as_of=datetime(2026, 3, 2, tzinfo=UTC)),
            _full_query(
                permitted_policy_bundle_versions=frozenset({"pb-1"}),
            ),
            _full_query(require_valid_at_boundary=False),
            _full_query(
                traverse=TraversalSpec(
                    seed_entity_classes=frozenset({"account", "person"}),
                    relationship_types=frozenset({"owns", "controls"}),
                    depth_limit=3,
                )
            ),
            _full_query(seeds=frozenset({"urn:e:1"})),
        )
        baseline_hash = content_hash(baseline)
        variant_hashes = {content_hash(v) for v in variants}
        assert baseline_hash not in variant_hashes
        assert len(variant_hashes) == len(variants)


class TestAllowedEntitiesDistinctness:
    """The survivor set is part of the question's identity (D-IMPL-87)."""

    def test_none_empty_and_populated_are_three_questions(self) -> None:
        unconstrained = _full_query(allowed_entities=None)
        empty = _full_query(allowed_entities=frozenset())
        populated = _full_query(allowed_entities=frozenset({"urn:e:1", "urn:e:2"}))
        hashes = {
            content_hash(unconstrained),
            content_hash(empty),
            content_hash(populated),
        }
        assert len(hashes) == 3


class TestClosure:
    """Validation at the boundary, immutability after it (CLAUDE.md §11)."""

    def test_unknown_field_is_refused_at_construction(self) -> None:
        with pytest.raises(ValidationError):
            GraphQuery.model_validate(
                {"tenant_id": TENANT, "as_of": AT, "version": "1.0.0"}
            )

    def test_mutation_of_a_constructed_query_is_refused(self) -> None:
        query = _full_query()
        with pytest.raises(ValidationError):
            query.tenant_id = "tenant-b"  # type: ignore[misc]


class TestSourceAttestationTiers:
    """The three tiers are three values of one schema (D-09)."""

    def test_tier_1_the_live_graph(self) -> None:
        tier_1 = SourceAttestation(
            policy_binding="assembly-stamped",
            lineage="graph-supplied",
            peer=None,
        )
        assert content_hash(tier_1)

    def test_tier_2_a_mounted_admitted_product(self) -> None:
        tier_2 = SourceAttestation(
            policy_binding="admission-verified",
            lineage="product-carried",
            peer=PeerRef(tenant_id=TENANT, peer_id="peer-1"),
        )
        assert content_hash(tier_2)

    def test_tier_3_is_expressible_today(self) -> None:
        """The no-refactor commitment, by construction: admitting a
        lower-trust source class later changes no schema."""
        tier_3 = SourceAttestation(
            policy_binding="none",
            lineage="none",
            peer=None,
        )
        assert content_hash(tier_3)


class TestDegenerateQuery:
    """``tenant_id`` + ``as_of`` alone is the everything-question (D-07)."""

    def test_constructible_hashable_and_unconstrained(self) -> None:
        degenerate = GraphQuery(tenant_id=TENANT, as_of=AT)
        assert degenerate.allowed_entities is None
        assert degenerate.seeds is None
        assert degenerate.traverse is None
        assert content_hash(degenerate)


class TestFragmentCannotSmuggleASurvivorSet:
    """T-15.2-26: ``allowed_entities`` is engine-authored only."""

    def test_query_fragment_declares_no_allowed_entities_field(self) -> None:
        assert "allowed_entities" not in QueryFragment.model_fields

    def test_query_fragment_declares_no_seeds_field(self) -> None:
        assert "seeds" not in QueryFragment.model_fields
