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

from tests.conformance.query_corpus import (
    EARLY,
    LATE,
    ON_BOUNDARY,
    RELATIONSHIP_TYPES,
    TENANT,
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


def test_module_imports_without_the_driver() -> None:
    """`import ccf.graph.backends.mongo` and `import ccf.boot` need no extra.

    The lazy-import posture: the driver is demanded at store *construction*,
    never at import, so the no-extra tree stays fully importable — including
    ``ccf.graph._writer``, which imports the backend module for its collection
    names and the field-path helper.
    """
    import ccf.boot  # noqa: F401 - the import IS the assertion
    import ccf.graph._writer  # noqa: F401
    import ccf.graph.backends.mongo  # noqa: F401


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


def test_boot_refuses_mongo_plus_another_backend() -> None:
    """Selecting mongo *and* memory is a contradiction, refused loudly.

    The exactly-one exclusivity check runs before any lazy driver import, so
    the refusal needs no extra installed — the fabric does not infer its
    substrate and does not pick a winner.
    """
    from ccf.boot import boot
    from ccf.controlplane.registry import ControlPlaneRegistry

    with pytest.raises(ValueError, match="exactly one"):
        boot(
            mongo_uri="mongodb://localhost:27017",
            memory=True,
            registry=ControlPlaneRegistry(),
            resolution_spec_key="never",
            resolution_spec_version="never",
            policy_bundle_key="never",
            policy_bundle_version="never",
        )


def test_manifest_declares_mongo_and_preflight_requires_the_uri() -> None:
    """`backend: mongo` is a declarable kind; the URI stays environment-supplied.

    The D-08 kind-only posture: a MongoDB URI can carry userinfo, and the
    manifest is a content-hashed audit artifact, so the connection value never
    lives in it. Preflight refuses a `mongo` declaration with no URI before
    any document is read.
    """
    from ccf.controlplane.artifacts import DeploymentManifest
    from ccf.deployment.manifest import _preflight_backend

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
    with pytest.raises(ValueError, match="mongo"):
        _preflight_backend(
            manifest,
            database_path=None,
            postgres_dsn=None,
            neo4j_uri=None,
            mongo_uri=None,
        )
    # And the mirror: the right argument is accepted, the wrong one refused.
    _preflight_backend(
        manifest,
        database_path=None,
        postgres_dsn=None,
        neo4j_uri=None,
        mongo_uri="mongodb://localhost:27017",
    )
    with pytest.raises(ValueError, match="also supplied"):
        _preflight_backend(
            manifest,
            database_path=None,
            postgres_dsn=None,
            neo4j_uri="neo4j://localhost:7687",
            mongo_uri="mongodb://localhost:27017",
        )


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
