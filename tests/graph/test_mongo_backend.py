"""Unit tests for the MongoDB backend — always-on half needs no server.

Plan 15.2-13. Everything above the ``mongo`` marker runs in an environment
WITHOUT the ``mongo`` extra installed, which is itself half the point: the
module stays importable (lazy import, the chroma_index / neo4j precedent), the
boot exclusivity check names the new selector before any driver import, and
the field-path validation site is pure (threat T-15.2-01).

The marked half proves the D-06 obligation the unmarked half cannot: a fabric
that **boots against MongoDB and writes through booted L2** answers the same
records the zero-dependency memory backend answers, at three boundaries. The
differential byte-identity bar over the generated corpus lives in
``tests/conformance/test_substrate_differential.py``'s ``mongo`` param.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from ccf.contracts.canonical import canonical_bytes
from ccf.graph.backends.mongo_write import REGISTRATION as MONGO_REGISTRATION

from tests.conformance.query_corpus import (
    EARLY,
    LATE,
    ON_BOUNDARY,
    RELATIONSHIP_TYPES,
    SEED_CLASSES,
    TENANT,
    chain_claims,
    chain_uris,
    entity_claim,
    relationship_claim,
)
from tests.conformance.test_substrate_properties import (
    EXCLUDED_CLASSIFICATION,
    PERMITTED_CLASSIFICATION,
    SEED_CLASS,
)
from tests.properties.strategies import ENTITY_POOL

if TYPE_CHECKING:
    from collections.abc import Callable

    from ccf.boot import FabricHandle

#: A crossable edge type from the fixture vocabulary — the tests hold
#: mechanism; the vocabulary is the fixtures' (CLAUDE.md §6.4).
EDGE_TYPE = sorted(RELATIONSHIP_TYPES)[0]

#: This module's subject, read off the adapter's own registration record
#: rather than typed here. Importing the write module needs no extra: the
#: driver import lives inside the store constructor.
BACKEND_NAME = MONGO_REGISTRATION.name


def test_module_imports_without_the_driver() -> None:
    """`import ccf.graph.backends.mongo` and `import ccf.boot` need no extra.

    The lazy-import posture: the driver is demanded at store *construction*,
    never at import, so the no-extra tree stays fully importable — including
    ``ccf.graph.backends.mongo_write``, which imports the reader module for its
    collection names and the field-path helper (D-01: the write module imports
    its reader, never the reverse).
    """
    import ccf.boot  # noqa: F401 - the import IS the assertion
    import ccf.graph.backends.mongo  # noqa: F401
    import ccf.graph.backends.mongo_write  # noqa: F401


def test_graph_identity_carries_no_credentials() -> None:
    """The identity string drops userinfo entirely (threat T-15.2-05).

    The single-writer check keys on this string and it lands in exception
    messages, so the password and user are dropped rather than merely "not
    usually shown" — the T-04-24 postgres precedent, unit-asserted here given
    a credentialed URI.
    """
    from ccf.graph.backends.mongo import _graph_identity

    identity = _graph_identity(
        "mongodb://alice:s3cret-password@graph.example.com:27017/fabric",
        database="fabric",
        partition="ccf_test",
    )
    assert "s3cret-password" not in identity
    assert "alice" not in identity
    assert identity == "mongodb://graph.example.com:27017/fabric#ccf_test"


def test_partitions_are_distinct_graphs() -> None:
    """Two partitions in one database are two graph identities.

    The Postgres two-schemas-are-two-graphs rule, carried over: what makes the
    single-writer check meaningful per fabric rather than per server.
    """
    from ccf.graph.backends.mongo import _graph_identity

    one = _graph_identity(
        "mongodb://host:27017", database="ccf", partition="fabric_a"
    )
    two = _graph_identity(
        "mongodb://host:27017", database="ccf", partition="fabric_b"
    )
    assert one != two


def test_attribute_field_path_refuses_unsafe_names() -> None:
    """The ONE field-path site rejects `$` and `.` names (threat T-15.2-01).

    A MongoDB field path is *structure*: it cannot be parameterized, a dotted
    name addresses a nested key rather than the literal one, and a
    ``$``-prefixed name is read as an operator or a field reference. Only the
    ``^[A-Za-z0-9_-]+$`` charset becomes a path; everything else answers
    ``None``, and both callers treat that as a refusal to make it structure.
    """
    from ccf.graph.backends.mongo import (
        ATTRIBUTE_FIELD_PREFIX,
        attribute_field_path,
    )

    assert attribute_field_path("classification") == (
        ATTRIBUTE_FIELD_PREFIX + "classification"
    )
    assert attribute_field_path("risk-tier_2") == (
        ATTRIBUTE_FIELD_PREFIX + "risk-tier_2"
    )
    for unsafe in ("$where", "a.b", "$", ".", "", "attr$op", "spaced name"):
        assert attribute_field_path(unsafe) is None, unsafe


class _RefusingStore:
    """A store whose collections cannot be reached.

    Touching :meth:`collection` is the failure the tests below are asserting
    the absence of: a translation that declined must decline *before* it
    builds anything a server could run.
    """

    def scope(self, tenant_id: str) -> dict[str, str]:
        return {"partition": "ccf_test", "tenant_id": tenant_id}

    def collection(self, name: str) -> Any:
        raise AssertionError(
            f"a declined translation reached collection {name!r}"
        )


def _reader_over_a_refusing_store() -> Any:
    """A ``MongoGraphReader`` bound to :class:`_RefusingStore`, no server."""
    from ccf.graph.backends.mongo import MongoGraphReader

    reader = MongoGraphReader.__new__(MongoGraphReader)
    reader._store = _RefusingStore()
    return reader


@pytest.mark.parametrize("unsafe", ["$where", "attributes.classification"])
def test_an_unsafe_attribute_name_declines_before_any_pipeline(
    unsafe: str,
) -> None:
    """A `$`-prefixed or dotted attribute name never becomes a field path.

    The decline is asserted where it matters — *before* a filter document
    exists — by binding the reader to a store whose collections raise. The
    query is still answered: the hook returns ``None`` and the fallback
    answers the whole query (`GQ-32` at
    docs/GRAPH_QUERY_SEMANTICS.md:583), byte-identical under D-04.
    """
    from datetime import UTC, datetime

    from ccf.graph.protocols import GraphQuery

    reader = _reader_over_a_refusing_store()
    q = GraphQuery(
        tenant_id=TENANT,
        as_of=datetime(2026, 1, 1, tzinfo=UTC),
        permitted_policy_bundle_versions=frozenset({"1.0.0"}),
        classification_attribute_by_class={SEED_CLASS: unsafe},
        permitted_classifications=frozenset({PERMITTED_CLASSIFICATION}),
    )
    assert reader._translate_query(q) is None


def test_empty_allowed_set_answers_empty_without_a_round_trip() -> None:
    """The empty survivor set IS the answer (`GQ-04`) — no collection touched."""
    from datetime import UTC, datetime

    from ccf.graph.protocols import GraphQuery

    reader = _reader_over_a_refusing_store()
    empty = GraphQuery(
        tenant_id=TENANT,
        as_of=datetime(2026, 1, 1, tzinfo=UTC),
        allowed_entities=frozenset(),
    )
    assert reader._translate_query(empty) == ((), ())


def test_no_query_text_is_assembled_anywhere_in_the_module() -> None:
    """Grep the module: nothing formats or concatenates a filter.

    The Neo4j adapter's twin test has to name its ONE sanctioned formatting
    site (the Cypher depth literal, which cannot be a parameter). MongoDB's
    claim is stronger and needs no exception: a filter is a ``dict``, so there
    is no query text for a value to be interpolated into (threat T-15.2-01).
    The f-strings that do exist render an identity string, an exception
    message and a prefixed field name — never anything a server parses — and
    the field name passes ``attribute_field_path`` first.
    """
    import re
    from inspect import getsource

    import ccf.graph.backends.mongo as module

    source = getsource(module)
    # Nothing in the module builds a Mongo operator token out of a value: no
    # f-string and no concatenation produces a leading `$`.
    assert not re.findall(r'f"\$\{', source)
    assert not re.findall(r'"\$"\s*\+', source)
    assert not re.findall(r'\+\s*"\$', source)
    # Every `$`-prefixed string literal in the module is a code-authored
    # operator key or the ONE aggregation field reference the `$graphLookup`
    # walk starts from. The pattern admits `_` deliberately, so a field
    # reference cannot slip through on the strength of its spelling.
    tokens = set(re.findall(r'"(\$[A-Za-z_][A-Za-z0-9_]*)"', source))
    assert tokens <= {
        "$and",
        "$or",
        "$in",
        # `D-IMPL-332`. `GQ-09`'s absence limb asks whether a claim carries a
        # valid-time at all, and `$lte` alone cannot: it does not match a
        # missing field. Code-authored like every other member here — the
        # token is a literal in the filter, never built from a value.
        "$exists",
        "$lte",
        "$gt",
        "$graphLookup",
        "$match",
        "$project",
        # The walk's `startWith` — SDK-owned, never artifact-authored.
        "$entity_uri",
    }, sorted(tokens)


def test_boot_refuses_this_adapter_plus_another_substrates_setting() -> None:
    """Naming this adapter and supplying another's setting is refused loudly.

    The guarantee is unchanged — the fabric does not infer its substrate and
    does not pick a winner — and so is the property that made this test cheap:
    the refusal still runs before any driver is loaded. Validation happens
    against the adapter's connection contract and no store is constructed, and
    this adapter's driver import lives inside its store constructor, so the
    refusal needs no extra installed.

    What changed is the shape of the contradiction. Before D-IMPL-93 it was
    two of eleven keyword arguments; now it is a connection key this adapter
    does not declare, refused by the ``extra="forbid"`` its contract inherits.
    """
    from ccf.boot import boot
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.graph.registry import InvalidBackendConfig

    with pytest.raises(InvalidBackendConfig) as caught:
        boot(
            backend=BACKEND_NAME,
            connection={
                "uri": "mongodb://localhost:27017",
                "database_path": "never-created.sqlite3",
            },
            registry=ControlPlaneRegistry(),
            resolution_spec_key="never",
            resolution_spec_version="never",
            policy_bundle_key="never",
            policy_bundle_version="never",
            tenant_ids=(TENANT,),
        )
    assert BACKEND_NAME in str(caught.value)
    assert "database_path" in str(caught.value)


def test_manifest_declares_mongo_and_preflight_requires_the_uri() -> None:
    """`backend: mongo` is a declarable kind; the URI stays environment-supplied.

    The D-08 kind-only posture: a MongoDB URI can carry userinfo, and the
    manifest is a content-hashed audit artifact, so the connection value never
    lives in it. Preflight refuses a `mongo` declaration with no URI before
    any document is read.

    The refusals moved and the guarantees did not (15.4-06). Preflight no longer
    holds a substrate-to-argument table: it resolves the adapter the manifest
    names and validates one connection mapping against that adapter's own
    contract, so "the URI is required" is a required field and "this setting is
    not yours" is the inherited `extra="forbid"`. One assertion is *added* while
    migrating, because a MongoDB URI carries userinfo: the supplied value must be
    absent from the refusal.
    """
    from ccf.controlplane.artifacts import DeploymentManifest
    from ccf.deployment.manifest import _preflight_adapter

    manifest = DeploymentManifest.model_validate(
        {
            "semver": "1.0.0",
            "backend": "mongo",
            "tenant_id": TENANT,
            "resolution_spec_key": "ccf.resolution-spec",
            "policy_bundle_key": "ccf.policy-bundle",
            "artifacts": [
                {
                    "path": "resolution.yaml",
                    "key": "ccf.resolution-spec",
                    "class_id": "ccf.resolution-spec",
                    "role": "register",
                    "registration": "typed",
                },
                {
                    "path": "policy.yaml",
                    "key": "ccf.policy-bundle",
                    "class_id": "ccf.policy-bundle",
                    "role": "register",
                    "registration": "versioned",
                },
            ],
        }
    )
    with pytest.raises(ValueError, match="mongo") as missing:
        _preflight_adapter(manifest, {})
    assert "uri" in str(missing.value)

    # And the mirror: the right setting is accepted, a setting the adapter does
    # not declare is refused.
    _preflight_adapter(manifest, {"uri": "mongodb://localhost:27017"})

    stray = "postgresql://user:pw@localhost:5432/never-connected"
    with pytest.raises(ValueError, match="dsn") as refused:
        _preflight_adapter(
            manifest, {"uri": "mongodb://localhost:27017", "dsn": stray}
        )
    # The refusal names the key and never reproduces what was supplied under
    # it. A URI under an undeclared key is precisely the shape that carries
    # userinfo into a message nobody meant to write.
    assert stray not in str(refused.value)


# --- the live-server half (needs the extra AND a reachable mongo) ------------


@pytest.mark.mongo
def test_l2_writes_round_trip_byte_identically_to_the_memory_backend(
    fabric_boot: "Callable[..., FabricHandle]",
) -> None:
    """A fabric boots on MongoDB, writes through L2, and answers identically.

    Task 1's own bar, before any translation exists: the same claims admitted
    through booted L2 on MongoDB and on the zero-dependency memory backend
    answer byte-identical views at three observed-time boundaries — before the
    revision, on it, and after it — so the supersession chain, the lineage
    set-union and the canonical timestamps all round-trip through the document
    layout unchanged.
    """
    uri = ENTITY_POOL[SEED_CLASS][0]
    other = ENTITY_POOL[SEED_CLASS][1]
    claims = (
        entity_claim(
            entity_uri=uri,
            entity_class=SEED_CLASS,
            classification=PERMITTED_CLASSIFICATION,
            observed_at=EARLY,
        ),
        entity_claim(
            entity_uri=other,
            entity_class=SEED_CLASS,
            classification=PERMITTED_CLASSIFICATION,
            observed_at=EARLY,
        ),
        entity_claim(
            entity_uri=uri,
            entity_class=SEED_CLASS,
            classification=EXCLUDED_CLASSIFICATION,
            observed_at=LATE,
        ),
    )
    edge = relationship_claim(
        relationship_type=EDGE_TYPE,
        subject_uri=uri,
        object_uri=other,
        observed_at=EARLY,
    )

    views: dict[str, list[bytes]] = {}
    for backend in ("mongo", "memory"):
        handle = fabric_boot(backend=backend)
        for claim in claims:
            handle.worker.admit_entity_claim(tenant_id=TENANT, claim=claim)
        handle.worker.admit_relationship_claim(tenant_id=TENANT, claim=edge)
        views[backend] = [
            canonical_bytes(handle.reader.as_of(tenant_id=TENANT, at=at))
            for at in (EARLY, ON_BOUNDARY, LATE)
        ]
        if backend == "mongo":
            # The history read is the second contract the document layout has
            # to satisfy: the whole chain, oldest first, with the supersession
            # edge restitched by the shared writer algorithm.
            history: Any = handle.reader.entity_history(
                tenant_id=TENANT, entity_uri=uri
            )
            assert len(history) == 2
            assert history[0].superseded_by == history[1].claim_id

    assert views["mongo"] == views["memory"]


@pytest.mark.mongo
def test_graphlookup_traversal_holds_on_every_pitfall_3_trap_shape(
    fabric_boot: "Callable[..., FabricHandle]",
) -> None:
    """The stage-2 promotion, asserted on the four shapes it can get wrong.

    Plan 15.2-13 Task 3. The differential corpus is the byte-identity bar;
    this test names the specific traps so a regression says *which* correction
    broke rather than "the corpus went red":

    * **depth 0** — the stage is skipped entirely (``maxDepth`` has no value
      meaning "no hops"); the answer is the walk starting points, which is a
      legal bound, not an error;
    * **depth 1** — ``maxDepth: 0``, the off-by-one: ``depthField`` starts at
      0 for the *first* lookup, so CCF hop *h* is ``depthField`` *h−1*;
    * **depth 2 over a mixed-direction path** — the chain's second edge points
      target→mid, so reaching the target from the seed is an out-then-in walk.
      ``$graphLookup`` is directed and two directed lookups do not compose;
      only the doubled-edge layout makes this reachable
      (15.2-RESEARCH.md Pitfall 3);
    * **the resurrection shape** — the same depth-2 question with the
      intermediate outside ``allowed_entities``. A walk that crossed it would
      re-reach the target the set excludes (`GQ-15` at
      docs/GRAPH_QUERY_SEMANTICS.md:300; threat T-15.2-26).

    Seed re-inclusion is asserted by every case at once: ``$graphLookup``
    excludes the starting document from its ``as`` array, so a seed missing
    from any answer would fail the byte-identity comparison.

    ``translated_answers`` is the promotion evidence — the one place a
    silently-conformant fallback could hide a broken walk, since D-04 makes
    the degraded posture byte-identical by design.
    """
    from ccf.graph.protocols import GraphQuery, TraversalSpec

    seed_uri, mid_uri, target_uri = chain_uris()
    entities, relationships = chain_claims(
        mid_classification=PERMITTED_CLASSIFICATION
    )

    def walk_at(depth: int) -> TraversalSpec:
        return TraversalSpec(
            seed_entity_classes=SEED_CLASSES,
            relationship_types=RELATIONSHIP_TYPES,
            depth_limit=depth,
        )

    queries = (
        GraphQuery(tenant_id=TENANT, as_of=ON_BOUNDARY, traverse=walk_at(0)),
        GraphQuery(tenant_id=TENANT, as_of=ON_BOUNDARY, traverse=walk_at(1)),
        GraphQuery(tenant_id=TENANT, as_of=ON_BOUNDARY, traverse=walk_at(2)),
        GraphQuery(
            tenant_id=TENANT,
            as_of=ON_BOUNDARY,
            traverse=walk_at(2),
            allowed_entities=frozenset({seed_uri, target_uri}),
        ),
    )

    answers: dict[str, list[bytes]] = {}
    reached: dict[str, list[set[str]]] = {}
    for backend in ("mongo", "memory"):
        handle = fabric_boot(backend=backend)
        for claim in entities:
            handle.worker.admit_entity_claim(tenant_id=TENANT, claim=claim)
        for edge in relationships:
            handle.worker.admit_relationship_claim(tenant_id=TENANT, claim=edge)
        views = [handle.reader.query(q) for q in queries]
        answers[backend] = [canonical_bytes(view) for view in views]
        reached[backend] = [
            {record.claim.entity_uri for record in view.entities}
            for view in views
        ]
        if backend == "mongo":
            assert handle.reader.translated_answers == len(queries)
            assert handle.reader.fallback_answers == 0

    assert answers["mongo"] == answers["memory"]
    assert reached["mongo"] == [
        {seed_uri},
        {seed_uri, mid_uri},
        {seed_uri, mid_uri, target_uri},
        {seed_uri},
    ]


@pytest.mark.mongo
def test_the_doubled_edge_layout_is_maintained_by_the_write_path(
    fabric_boot: "Callable[..., FabricHandle]",
) -> None:
    """Every edge is two traversal documents — forward and reverse.

    ``$graphLookup`` follows one direction only while CCF traversal is
    undirected (`GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201), so the layout
    the directed stage requires is asserted directly against the store rather
    than inferred from a traversal answer.
    """
    from ccf.graph.backends.mongo import TRAVERSAL_EDGES

    uri = ENTITY_POOL[SEED_CLASS][0]
    other = ENTITY_POOL[SEED_CLASS][1]
    handle = fabric_boot(backend="mongo")
    for entity_uri in (uri, other):
        handle.worker.admit_entity_claim(
            tenant_id=TENANT,
            claim=entity_claim(
                entity_uri=entity_uri,
                entity_class=SEED_CLASS,
                classification=PERMITTED_CLASSIFICATION,
                observed_at=EARLY,
            ),
        )
    written = handle.worker.admit_relationship_claim(
        tenant_id=TENANT,
        claim=relationship_claim(
            relationship_type=EDGE_TYPE,
            subject_uri=uri,
            object_uri=other,
            observed_at=EARLY,
        ),
    )

    store: Any = handle.reader._store
    documents = sorted(
        (
            (doc["direction"], doc["from"], doc["to"])
            for doc in store.collection(TRAVERSAL_EDGES).find(
                {
                    **store.scope(TENANT),
                    "relationship_key": written.node_key,
                }
            )
        )
    )
    assert documents == [
        ("forward", uri, other),
        ("reverse", other, uri),
    ]
