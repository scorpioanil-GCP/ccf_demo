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

import pytest


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
