"""The hash-transparent mark and the omission rule (``D-IMPL-243``).

Whitepaper §7.10 (a decision reconstructible years later against the exact
identities it was made with); CLAUDE.md §7.4 (replay resolves exact versions,
never "latest"). Phase 24.5's close review (CR-01) measured that every
sentinel-defaulted field the phase added moved the content hash of every model
carrying it — a replay record's per-step ``parameter_hash``, its
``graph_query_sequence`` pins, every Control Plane version — because
``ccf.contracts.canonical::_normalize`` renders every field. ``D-IMPL-243``
rules that such a field is a generation change unless its owner marks it
``ccf_hash_transparent``, meaning its sentinel *is* the old contract; a marked
field is omitted at its sentinel and rendered otherwise. Dave's rule, verbatim:
"silence equals yesterday". Amendment 1 gives the key its three states —
``True`` omits at the sentinel, ``False`` is a declared generation boundary
that ``generation_mismatch`` names when absent, and no key is the pre-243
``D-IMPL-89`` lineage: rendered, never named.

Every model here is a scratch model owned by this module: the rule is about
the canonicalizer, and proving it on a real SDK contract would prove the mark
on that contract rather than the mechanism. The real marks are proven against
the ``13bd250`` tree in ``tests/replay/`` (the golden fixture) and were
measured per model in ``24.5-FIX-01-SUMMARY.md``.
"""

from __future__ import annotations

import pytest
from pydantic import Field

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import (
    HASH_TRANSPARENT_KEY,
    CanonicalizationError,
    canonical_bytes,
    content_hash,
    generation_mismatch,
    hash_transparent_fields,
)
from ccf.graph.protocols import NO_STORE_SNAPSHOT_PIN, StoreSnapshotPin


class _Yesterday(CCFContract):
    """The contract as it was before any field below existed."""

    a: int


class _Today(CCFContract):
    """The same contract after three transparent fields were added.

    One sentinel of each declared form the SDK uses: a plain ``default``, a
    ``default_factory``, and a model-valued default that compares by value.
    """

    a: int
    t: str | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    f: dict[str, str] = Field(
        default_factory=dict, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    pin: StoreSnapshotPin = Field(
        default=NO_STORE_SNAPSHOT_PIN,
        json_schema_extra={HASH_TRANSPARENT_KEY: True},
    )


class _TodayUnmarked(CCFContract):
    """The same addition with NO key — the pre-243 lineage (amendment 1).

    Rendered into every hash, so it IS a generation change for the hashes
    (the rule is not "defaults never count"); but never *named* by
    ``generation_mismatch``, because an absent key declares nothing and
    ``D-IMPL-89`` promises a record written before the field existed still
    resolves and replays.
    """

    a: int
    n: int = 0


class _TodayBoundary(CCFContract):
    """The same addition marked ``False`` — a DECLARED generation boundary.

    Rendered exactly as ``_TodayUnmarked.n`` is; the difference is entirely
    what ``generation_mismatch`` says about a stored object that lacks it.
    """

    a: int
    b: int = Field(default=0, json_schema_extra={HASH_TRANSPARENT_KEY: False})


class _NoSentinel(CCFContract):
    """A mark on a field with no default: nothing to be silent at."""

    a: int
    t: str = Field(json_schema_extra={HASH_TRANSPARENT_KEY: True})


class _Outer(CCFContract):
    inner: _TodayBoundary
    optional: _TodayBoundary | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: False}
    )
    lineage: _TodayUnmarked | None = None
    silent: _Today | None = Field(
        default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )


# --- the mark ---------------------------------------------------------------


def test_the_mark_is_read_from_the_field_declaration() -> None:
    assert hash_transparent_fields(_Today) == frozenset({"t", "f", "pin"})
    assert hash_transparent_fields(_Yesterday) == frozenset()
    assert hash_transparent_fields(_TodayUnmarked) == frozenset()


def test_only_the_literal_true_is_a_mark() -> None:
    class _Loose(CCFContract):
        a: int
        yes: int = Field(default=0, json_schema_extra={HASH_TRANSPARENT_KEY: 1})
        text: int = Field(
            default=0, json_schema_extra={HASH_TRANSPARENT_KEY: "true"}
        )

    assert hash_transparent_fields(_Loose) == frozenset()
    assert canonical_bytes(_Loose(a=1)) == b'{"a":1,"text":0,"yes":0}'


def test_a_mark_without_a_default_is_refused_not_ignored() -> None:
    with pytest.raises(CanonicalizationError, match="_NoSentinel.t") as refused:
        content_hash(_NoSentinel(a=1, t="q"))
    assert "D-IMPL-243" in str(refused.value)


# --- the omission rule: silence equals yesterday ------------------------------


def test_a_boundary_mark_renders_exactly_as_no_mark_does() -> None:
    """``False`` changes what is *named*, never what is *rendered*."""
    assert canonical_bytes(_TodayBoundary(a=1)) == b'{"a":1,"b":0}'
    assert hash_transparent_fields(_TodayBoundary) == frozenset()
    assert content_hash(_TodayBoundary(a=1)) != content_hash(_Yesterday(a=1))


def test_a_marked_field_at_its_sentinel_is_omitted() -> None:
    assert canonical_bytes(_Today(a=1)) == canonical_bytes(_Yesterday(a=1))
    assert content_hash(_Today(a=1)) == content_hash(_Yesterday(a=1))
    assert canonical_bytes(_Today(a=1)) == b'{"a":1}'


def test_the_sentinel_is_compared_by_value_not_identity() -> None:
    same_pin = StoreSnapshotPin(substrate="none", pin="no-store-snapshot-pin")
    assert same_pin is not NO_STORE_SNAPSHOT_PIN
    assert content_hash(_Today(a=1, pin=same_pin)) == content_hash(
        _Yesterday(a=1)
    )
    assert content_hash(_Today(a=1, f={})) == content_hash(_Yesterday(a=1))


@pytest.mark.parametrize(
    ("field", "value", "rendered"),
    [
        ("t", "x", b'{"a":1,"t":"x"}'),
        ("f", {"k": "v"}, b'{"a":1,"f":{"k":"v"}}'),
        (
            "pin",
            StoreSnapshotPin(substrate="fluree", pin="7"),
            b'{"a":1,"pin":{"pin":"7","substrate":"fluree"}}',
        ),
    ],
)
def test_a_non_sentinel_value_is_rendered_and_moves_the_hash(
    field: str, value: object, rendered: bytes
) -> None:
    today = _Today(a=1, **{field: value})
    assert canonical_bytes(today) == rendered
    assert content_hash(today) != content_hash(_Yesterday(a=1))


def test_an_unmarked_default_still_renders() -> None:
    """The rule is not "defaults never count"."""
    assert canonical_bytes(_TodayUnmarked(a=1)) == b'{"a":1,"n":0}'
    assert content_hash(_TodayUnmarked(a=1)) != content_hash(_Yesterday(a=1))


def test_a_transparent_model_valued_field_is_walked_when_present() -> None:
    outer = _Outer(inner=_TodayBoundary(a=1), silent=_Today(a=2, t="deep"))
    assert canonical_bytes(outer) == (
        b'{"inner":{"a":1,"b":0},"lineage":null,"optional":null,'
        b'"silent":{"a":2,"t":"deep"}}'
    )


# --- the converse: generation_mismatch, in DECLARED scope (amendment 1) ------


def test_a_stored_object_lacking_only_transparent_fields_is_the_same_generation() -> None:
    assert generation_mismatch(_Today, {"a": 1}) == ()


def test_a_stored_object_lacking_a_boundary_field_is_named() -> None:
    """``False`` → generation boundary, refuse by name."""
    assert generation_mismatch(_TodayBoundary, {"a": 1}) == ("b",)


def test_a_stored_object_lacking_an_unmarked_field_is_never_named() -> None:
    """No key → the D-IMPL-89 lineage: render, never refuse.

    This is the control amendment 1 was written for. Under the first
    specification this object was named ``("n",)``, and on a real
    pre-extension record the same rule named fifteen pre-243 fields.
    """
    assert generation_mismatch(_TodayUnmarked, {"a": 1}) == ()


def test_only_the_literal_false_is_a_boundary_mark() -> None:
    class _Loose(CCFContract):
        a: int
        zero: int = Field(default=0, json_schema_extra={HASH_TRANSPARENT_KEY: 0})
        none: int = Field(
            default=0, json_schema_extra={HASH_TRANSPARENT_KEY: None}
        )
        text: int = Field(
            default=0, json_schema_extra={HASH_TRANSPARENT_KEY: "false"}
        )

    assert generation_mismatch(_Loose, {"a": 1}) == ()


def test_a_stored_object_carrying_every_field_crosses_no_boundary() -> None:
    assert generation_mismatch(_TodayBoundary, {"a": 1, "b": 0}) == ()
    assert generation_mismatch(_TodayUnmarked, {"a": 1, "n": 0}) == ()
    assert generation_mismatch(_Today, {"a": 1, "t": "x"}) == ()


def test_nested_models_are_walked_and_reported_dotted() -> None:
    stored = {
        "inner": {"a": 1},
        "optional": {"a": 2},
        "lineage": {"a": 3},
        "silent": {"a": 4},
    }
    assert generation_mismatch(_Outer, stored) == ("inner.b", "optional.b")


def test_an_absent_nested_boundary_field_is_reported_once_as_the_outer_name() -> None:
    assert generation_mismatch(_Outer, {"inner": {"a": 1, "b": 0}}) == (
        "optional",
    )


def test_an_absent_nested_lineage_field_is_not_reported() -> None:
    stored = {"inner": {"a": 1, "b": 0}, "optional": {"a": 2, "b": 0}}
    assert generation_mismatch(_Outer, stored) == ()


def test_a_null_nested_value_is_a_leaf_not_a_walk() -> None:
    stored = {"inner": {"a": 1, "b": 0}, "optional": None, "lineage": None}
    assert generation_mismatch(_Outer, stored) == ()


# --- the marks in the tree: the ticked table, as a roster --------------------

#: Every hash-transparent field the SDK declares, as ``D-IMPL-243``'s ticked
#: table (rows 1–5 and 7–10) plus the ONE inherited occurrence: the artifact
#: form of row 1 subclasses the parameters class and carries the same
#: declaration, so the mark rides the inheritance — which is the CR-01
#: consequence for a registered table's content-hash version. Rows 6, 11 and
#: 12 (``ExecutionResult.store_snapshot_pin``, ``ResolvedEntity.resolved_by``,
#: ``ExecutionResult.empty_results``) are never content-hashed and carry no
#: mark. A roster, never a count: a right count with a wrong member audits
#: clean forever.
_MARKED_IN_THE_TREE = frozenset(
    {
        "ccf.operators.params.TraversalNeighborhoodParameters.admitted_entity_classes",
        "ccf.controlplane.artifacts.TraversalNeighborhoodParametersArtifact.admitted_entity_classes",
        "ccf.graph.protocols.TraversalSpec.admitted_entity_classes",
        "ccf.graph.protocols.TraversalSpec.direction",
        "ccf.products.contract.ProductLineage.store_snapshot_pin",
        "ccf.replay.record.ContextFabricSnapshot.store_snapshot_pin",
        "ccf.controlplane.artifacts.HalfLifeEntry.decay",
        "ccf.controlplane.artifacts.ProductClassDeclaration.serve_obligations",
        "ccf.products.contract.RegisteredProductClass.serve_obligations",
        "ccf.products.request.ProductRequestContract.unsupported_arguments",
        "ccf.assembly.worker.RelationshipResolutionRule.predicate_key",
        "ccf.assembly.worker.RelationshipResolutionRule.subject_rule",
        "ccf.assembly.worker.RelationshipResolutionRule.object_rule",
    }
)


def _every_marked_field_in_the_sdk() -> frozenset[str]:
    import importlib
    import pkgutil

    from pydantic import BaseModel

    import ccf

    for module in pkgutil.walk_packages(ccf.__path__, "ccf."):
        importlib.import_module(module.name)
    found: set[str] = set()
    seen: set[type] = set()

    def walk(cls: type) -> None:
        for sub in cls.__subclasses__():
            if sub in seen:
                continue
            seen.add(sub)
            if sub.__module__.startswith("ccf."):
                for name in hash_transparent_fields(sub):
                    found.add(f"{sub.__module__}.{sub.__name__}.{name}")
            walk(sub)

    walk(BaseModel)
    return frozenset(found)


def test_the_marked_fields_in_the_tree_are_exactly_the_ticked_table() -> None:
    assert _every_marked_field_in_the_sdk() == _MARKED_IN_THE_TREE


# --- silence equals yesterday, on the real models, against 13bd250 -----------

#: ``content_hash`` of each marked model at its sentinel, MEASURED under the
#: ``13bd250`` tree (the Phase 24.5 base, before any of these fields existed)
#: by ``git archive 13bd250 src | tar -x`` and the same construction under
#: ``PYTHONPATH=<scratch>/src``. The digests are the base tree's, verbatim;
#: HEAD must reproduce every one. The first is CR-01's own reproduction
#: (``34df2d94…``, the number the review measured at base).
_BASE_TREE_DIGESTS = {
    "TraversalNeighborhoodParameters": (
        "34df2d942bbe6d91bdb31d304a50a35a26ea5b291eb13d90fabca17b101775a9"
    ),
    "TraversalSpec": (
        "34df2d942bbe6d91bdb31d304a50a35a26ea5b291eb13d90fabca17b101775a9"
    ),
    "GraphQuery": "5e94449b20e50be3e6be2c7d5e566fde5226ed3062074db02f31493d1f0213e5",
    "ProductLineage": (
        "2c321c21705091837fbce2ab234e289c2f07d4fae85a960aaec03221ba0b39fc"
    ),
    "ContextFabricSnapshot": (
        "e0575d5da1537f9a5da9c9ddf3121c7c364f7509d73d24f7e78dba8758337aac"
    ),
    "HalfLifeTable": (
        "66d55b5f9358cce2e7b93a5d0198fd4df96acb3a1297e2bddd7330dba89b894c"
    ),
    "ProductClassDeclaration": (
        "99ca269ca18f91b88cc8f0769aad16646b825dbe3b9387996f4723d76e3252f1"
    ),
    "RegisteredProductClass": (
        "b79c57556c91866267adebe5f8309bab6939ff59888181fb90f5fc61f4d23b43"
    ),
    "ProductRequestContract": (
        "cbc7c95d8564e5e3065eb76f00c1bfe2bf040be906cc81d32687969a9704dfbf"
    ),
    "RelationshipResolutionRule": (
        "657bc97be381a5cf0d5afb1741462624a934a1ddc13eba5b8db76760ed0dffd1"
    ),
}


def _real_models_at_their_sentinels() -> dict[str, object]:
    from datetime import UTC, datetime

    from ccf.assembly.worker import RelationshipResolutionRule
    from ccf.controlplane.artifacts import (
        HalfLifeEntry,
        HalfLifeTable,
        ProductClassDeclaration,
    )
    from ccf.graph.protocols import GraphQuery, TraversalSpec
    from ccf.operators.params import TraversalNeighborhoodParameters
    from ccf.products.contract import ProductLineage, RegisteredProductClass
    from ccf.products.request import ProductRequestContract, SkillArgumentSchema
    from ccf.replay.record import ContextFabricSnapshot

    at = datetime(2026, 3, 15, tzinfo=UTC)
    spec = TraversalSpec(
        seed_entity_classes=frozenset({"a"}),
        relationship_types=frozenset({"r"}),
        depth_limit=1,
    )
    return {
        "TraversalNeighborhoodParameters": TraversalNeighborhoodParameters(
            seed_entity_classes=frozenset({"a"}),
            relationship_types=frozenset({"r"}),
            depth_limit=1,
        ),
        "TraversalSpec": spec,
        "GraphQuery": GraphQuery(tenant_id="t", as_of=at, traverse=spec),
        "ProductLineage": ProductLineage(
            operators_invoked=frozenset({"o"}),
            policy_bundle_versions=frozenset({"v"}),
            graph_snapshot_at=at,
        ),
        "ContextFabricSnapshot": ContextFabricSnapshot.build(
            tenant_id="t",
            temporal_boundary=at,
            store_watermark="w",
            touched_entities=("e",),
            touched_relationships=(),
        ),
        "HalfLifeTable": HalfLifeTable(
            semver="1.0.0",
            entries={
                "x": HalfLifeEntry(
                    half_life_seconds=10, decay_driver="d", supersession_event="e"
                )
            },
        ),
        "ProductClassDeclaration": ProductClassDeclaration(
            semver="1.0.0",
            schema_name="s",
            schema_version="1.0.0",
            ttl_anchor="from_decision",
            assembly_mode="algorithmic",
            max_ttl_key="k",
            required_operator_keys=("o",),
        ),
        "RegisteredProductClass": RegisteredProductClass(
            schema_name="s",
            schema_version="1.0.0",
            ttl_anchor="from_decision",
            assembly_mode="algorithmic",
            max_ttl_key="k",
            max_ttl_version="v",
        ),
        "ProductRequestContract": ProductRequestContract(
            semver="1.0.0",
            schema_name="s",
            schema_version="1.0.0",
            arguments=SkillArgumentSchema(properties={}, required=()),
        ),
        "RelationshipResolutionRule": RelationshipResolutionRule(
            relationship_type="rel", subject_entity_class="a", object_entity_class="b"
        ),
    }


@pytest.mark.parametrize("model_name", sorted(_BASE_TREE_DIGESTS))
def test_each_marked_model_at_its_sentinel_hashes_as_the_base_tree_did(
    model_name: str,
) -> None:
    """Silence equals yesterday, model by model (``D-IMPL-243``)."""
    instance = _real_models_at_their_sentinels()[model_name]
    assert content_hash(instance) == _BASE_TREE_DIGESTS[model_name]


def test_the_digest_table_and_the_construction_table_name_the_same_models() -> None:
    assert set(_real_models_at_their_sentinels()) == set(_BASE_TREE_DIGESTS)
