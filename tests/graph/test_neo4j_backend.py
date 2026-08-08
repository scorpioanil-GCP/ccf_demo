"""Always-on unit tests for the Neo4j backend — no server, no driver required.

Plan 15.2-12. Everything here runs in an environment WITHOUT the ``neo4j``
extra installed, which is itself half the point: the module stays importable
(lazy import, the chroma_index precedent), the boot exclusivity check names
the new selector before any driver import, and the credential-hygiene helper
is pure (threat T-15.2-05). The live-server behavior — writes through booted
L2, differential byte-identity, the translated Cypher — runs under the
``neo4j`` marker in ``tests/conformance/test_substrate_differential.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ccf.contracts.canonical import canonical_bytes
from tests.conformance.query_corpus import (
    ON_BOUNDARY,
    RELATIONSHIP_TYPES,
    SEED_CLASSES,
    TENANT,
    chain_claims,
    chain_uris,
)
from tests.conformance.test_substrate_properties import PERMITTED_CLASSIFICATION

if TYPE_CHECKING:
    from collections.abc import Callable

    from ccf.boot import FabricHandle


def test_module_imports_without_the_driver() -> None:
    """`import ccf.graph.backends.neo4j` and `import ccf.boot` need no extra.

    The lazy-import posture (the chroma_index precedent): the driver is
    demanded at store *construction*, never at import, so the no-extra tree
    stays fully importable.
    """
    import ccf.boot  # noqa: F401 - the import IS the assertion
    import ccf.graph.backends.neo4j  # noqa: F401


def test_graph_identity_carries_no_credentials() -> None:
    """The identity string drops userinfo entirely (threat T-15.2-05).

    The single-writer check keys on this string and it lands in exception
    messages, so the password and user are dropped rather than merely "not
    usually shown" — the T-04-24 postgres precedent, unit-asserted here
    given a credentialed URI.
    """
    from ccf.graph.backends.neo4j import _graph_identity

    identity = _graph_identity(
        "neo4j://alice:s3cret-password@graph.example.com:7687",
        database="neo4j",
        partition="ccf_test",
    )
    assert "s3cret-password" not in identity
    assert "alice" not in identity
    assert identity == "neo4j://graph.example.com:7687/neo4j#ccf_test"


def test_split_credentials_hands_auth_to_the_driver_only() -> None:
    """Userinfo is parsed once into an auth pair; the clean URI carries none."""
    from ccf.graph.backends.neo4j import _split_credentials

    clean, auth = _split_credentials("neo4j://alice:s3cret@host.example:7687")
    assert auth == ("alice", "s3cret")
    assert "s3cret" not in clean
    assert "alice" not in clean
    assert clean == "neo4j://host.example:7687"

    unchanged, no_auth = _split_credentials("neo4j://host.example:7687")
    assert no_auth is None
    assert unchanged == "neo4j://host.example:7687"


def test_partitions_are_distinct_graphs() -> None:
    """Two partitions on one database are two graph identities.

    The Postgres two-schemas-are-two-graphs rule, carried over: what makes
    the single-writer check meaningful per fabric rather than per server.
    """
    from ccf.graph.backends.neo4j import _graph_identity

    one = _graph_identity(
        "neo4j://host:7687", database="neo4j", partition="fabric_a"
    )
    two = _graph_identity(
        "neo4j://host:7687", database="neo4j", partition="fabric_b"
    )
    assert one != two


def test_over_ceiling_depth_declines_to_the_fallback() -> None:
    """`_translate_query` returns None above MAX_DEPTH_CEILING (D-04).

    The ceiling bounds the ONE inlined Cypher literal, never the query
    vocabulary: an over-ceiling `depth_limit` is still answered — by the
    memory-bounded fallback (`GQ-29`). The decline is a pure function of
    the query value, asserted here with no store and no server: the check
    runs before any session could be touched.
    """
    from datetime import UTC, datetime

    from ccf.graph.backends.neo4j import (
        MAX_DEPTH_CEILING,
        Neo4jGraphReader,
    )
    from ccf.graph.protocols import GraphQuery, TraversalSpec

    reader = Neo4jGraphReader.__new__(Neo4jGraphReader)
    over_ceiling = GraphQuery(
        tenant_id="t",
        as_of=datetime(2026, 1, 1, tzinfo=UTC),
        traverse=TraversalSpec(
            seed_entity_classes=frozenset({"counterparty"}),
            relationship_types=frozenset({"obligor_of"}),
            depth_limit=MAX_DEPTH_CEILING + 1,
        ),
    )
    assert reader._translate_query(over_ceiling) is None


def test_empty_allowed_set_answers_empty_without_a_round_trip() -> None:
    """The empty survivor set IS the answer (`GQ-04`) — no session touched."""
    from datetime import UTC, datetime

    from ccf.graph.backends.neo4j import Neo4jGraphReader
    from ccf.graph.protocols import GraphQuery

    reader = Neo4jGraphReader.__new__(Neo4jGraphReader)
    empty = GraphQuery(
        tenant_id="t",
        as_of=datetime(2026, 1, 1, tzinfo=UTC),
        allowed_entities=frozenset(),
    )
    assert reader._translate_query(empty) == ((), ())


def test_reach_pattern_admits_only_validated_depth_literals() -> None:
    """The one formatting site refuses everything but a bounded genuine int.

    Pitfall 7: the depth literal is the concentrated injection surface
    (threat T-15.2-01), so its validation contract is asserted directly —
    bools, negatives, zero, and over-ceiling values all refuse.
    """
    from ccf.graph.backends.neo4j import MAX_DEPTH_CEILING, _reach_pattern

    assert _reach_pattern(1) == "-[:CCF_EDGE*1..1]-"
    assert _reach_pattern(MAX_DEPTH_CEILING) == (
        f"-[:CCF_EDGE*1..{MAX_DEPTH_CEILING}]-"
    )
    for bad in (0, -1, MAX_DEPTH_CEILING + 1, True):
        with pytest.raises(ValueError, match="depth literal"):
            _reach_pattern(bad)


def test_exactly_one_formatting_site_renders_query_text() -> None:
    """Grep the module: one f-string touches query text (Pitfall 7).

    ``_reach_pattern``'s depth literal is the sanctioned site; ``_query``'s
    ``f"p{index}"`` renders parameter NAMES (the positional binding
    convention), never query text, and everything else is concatenation of
    code-authored constants with values as driver parameters.
    """
    import re
    from inspect import getsource

    import ccf.graph.backends.neo4j as module

    source = getsource(module)
    # f-strings whose rendered text lands in a Cypher statement: the reach
    # pattern is the only one containing Cypher syntax.
    cypher_shaped = re.findall(r'f"[^"]*(?:MATCH|MERGE|\[:|\*1\.\.)[^"]*"', source)
    assert len(cypher_shaped) == 1, cypher_shaped
    assert "*1..{depth}" in cypher_shaped[0]


def test_boot_refuses_neo4j_plus_another_backend() -> None:
    """Selecting neo4j *and* memory is a contradiction, refused loudly.

    The exactly-one exclusivity check runs before any lazy driver import,
    so the refusal needs no extra installed — the fabric does not infer
    its substrate and does not pick a winner.
    """
    from ccf.boot import boot
    from ccf.controlplane.registry import ControlPlaneRegistry

    with pytest.raises(ValueError, match="exactly one"):
        boot(
            neo4j_uri="neo4j://localhost:7687",
            memory=True,
            registry=ControlPlaneRegistry(),
            resolution_spec_key="never",
            resolution_spec_version="never",
            policy_bundle_key="never",
            policy_bundle_version="never",
        )


@pytest.mark.neo4j
def test_cypher_traversal_is_pushed_not_silently_degraded(
    fabric_boot: "Callable[..., FabricHandle]",
) -> None:
    """The Cypher walk ran in the engine — telemetry, not byte-identity alone.

    Added by plan 15.2-14 on a BLOCKING finding from the §3.1 phase-close
    self-review. **Byte-identity to the fallback is a conformance bar, not a
    pushdown bar.** D-04 makes the degraded posture byte-identical *by design*
    (`GQ-34` at docs/GRAPH_QUERY_SEMANTICS.md:609), so a `_translate_query`
    that always returned ``None`` would pass the entire differential corpus —
    which was, until this test, the whole of the neo4j leg's evidence. The SQL
    backends prove the push with ``_pushed()``
    (``tests/graph/test_sql_pushdown.py``) and Mongo with
    ``translated_answers == len(queries)``
    (``tests/graph/test_mongo_backend.py``); Neo4j asserted neither, so the
    phase's strongest-pushdown-substrate claim rested on evidence that could
    not distinguish a working Cypher translation from an absent one.

    The four shapes are the ones a variable-length ``MATCH`` can get wrong,
    mirroring the Mongo trap-shape test so a regression names *which*
    correction broke:

    * **depth 0** — starts only, no hop (`GQ-10`);
    * **depth 1** — one hop;
    * **depth 2 over a mixed-direction chain** — CCF traversal is undirected,
      so the second edge pointing target→mid must still be crossable;
    * **the resurrection shape** — the same depth-2 question with the
      intermediate outside ``allowed_entities``. A walk that crossed it would
      re-reach the target the set excludes (`GQ-15` at
      docs/GRAPH_QUERY_SEMANTICS.md:300; threat T-15.2-26). This is the one
      that most needs the telemetry: a degrade answers it correctly too.

    ``memory`` is the differential control — the always-on KV floor, which
    has no native translation at all — so the reached sets and the canonical
    bytes are held identical while only the neo4j leg is asserted pushed.
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
    for backend in ("neo4j", "memory"):
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
        if backend == "neo4j":
            # The whole point of this test: every one of the four answers came
            # out of Cypher, none out of the fallback.
            assert handle.reader.translated_answers == len(queries)
            assert handle.reader.fallback_answers == 0

    assert answers["neo4j"] == answers["memory"]
    assert reached["neo4j"] == [
        {seed_uri},
        {seed_uri, mid_uri},
        {seed_uri, mid_uri, target_uri},
        {seed_uri},
    ]
