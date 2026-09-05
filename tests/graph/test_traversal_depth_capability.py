"""The technical limit, asked of the substrate that has one — no server needed.

Plan ``24.6-03``; ``D-IMPL-253`` Q21 (Dave: *"6 is measurement/default history;
100 is the genuine technical capability boundary"*). The subject is
:class:`ccf.graph.protocols.TraversalDepthCapability` and the two backends that
satisfy it.

**What the Protocol is for, restated so these assertions are readable.** The
graph seam has no refusal path: an over-ceiling ``depth_limit`` declines the
native translation and the memory-bounded fallback answers (`GQ-29` at
docs/GRAPH_QUERY_SEMANTICS.md:554). Refusing a depth **by name** happens one
layer up, in :mod:`ccf.products.constraints`, where a governed response exists
to put the refusal in — and that layer can only do it if the substrate can be
*asked* what it can technically do. This module asserts that it can be asked,
that the answer is the backend's own constant rather than a copy of it, and
that a store with no ceiling is not asked at all.

Everything here runs without a server and without the ``neo4j`` extra: the
stores are constructed by ``__new__`` and given the one attribute their
identity property reads — the idiom this directory already uses for the readers
(``tests/graph/test_neo4j_backend.py::test_over_ceiling_depth_declines_to_the_fallback``). Constructing them for real would
demand a live substrate to answer a question that has nothing to do with one.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ccf.graph.backends.fluree import MAX_DEPTH_CEILING as FLUREE_CEILING
from ccf.graph.backends.fluree import FlureeGraphStore
from ccf.graph.backends.neo4j import MAX_DEPTH_CEILING as NEO4J_CEILING
from ccf.graph.backends.neo4j import Neo4jGraphStore
from ccf.graph.backends.sqlite import SqliteGraphStore
from ccf.graph.protocols import TraversalDepthCapability

#: A credential-free identity string, this module's own fixture vocabulary.
IDENTITY = "fixture://graph.example:0/ledger#partition"


def _detached(store_class: type[Any]) -> Any:
    """A store object without a connection, carrying only its identity.

    ``__new__`` and one attribute: enough for the two capability members and
    for nothing else, which is the point — a capability question must be
    answerable without a session, because the layer that asks it does so before
    any read.
    """
    store = store_class.__new__(store_class)
    store._identity = IDENTITY
    return store


@pytest.mark.parametrize(
    ("store_class", "ceiling"),
    [
        pytest.param(FlureeGraphStore, FLUREE_CEILING, id="fluree"),
        pytest.param(Neo4jGraphStore, NEO4J_CEILING, id="neo4j"),
    ],
)
def test_a_ceilinged_backend_satisfies_the_capability(
    store_class: type[Any], ceiling: int
) -> None:
    """``isinstance`` is a real check: the Protocol is ``@runtime_checkable``."""
    assert isinstance(_detached(store_class), TraversalDepthCapability)


@pytest.mark.parametrize(
    ("store_class", "ceiling"),
    [
        pytest.param(FlureeGraphStore, FLUREE_CEILING, id="fluree"),
        pytest.param(Neo4jGraphStore, NEO4J_CEILING, id="neo4j"),
    ],
)
def test_the_reported_depth_is_the_backends_own_constant(
    store_class: type[Any], ceiling: int
) -> None:
    """Read from the module, never copied: a second literal is a second truth.

    The comparison is against the adapter's own ``MAX_DEPTH_CEILING`` — the
    constant that bounds the literal it injects into query text — so a backend
    that changed its bound and forgot this property goes RED here rather than
    reporting a number nothing enforces.
    """
    assert _detached(store_class).max_traversal_depth == ceiling


@pytest.mark.parametrize(
    "store_class", [FlureeGraphStore, Neo4jGraphStore], ids=["fluree", "neo4j"]
)
def test_the_capability_identity_is_the_graph_identity(
    store_class: type[Any],
) -> None:
    """One identity, not two: the bound's source is the graph the fabric names.

    ``graph_identity`` is credential-free by its own construction (threats
    ``T-15.2-05`` / ``T-04-24``), which is what makes it safe to record on a
    ``capability``-kind provenance source that lands in a replay record.
    """
    store = _detached(store_class)
    assert store.capability_identity == store.graph_identity == IDENTITY


def test_a_backend_with_no_ceiling_does_not_satisfy_the_capability(
    tmp_path: Path,
) -> None:
    """The negative half, and the reason the Protocol is structural.

    The SQLite reference store answers any depth by scan-and-filter and has no
    technical bound to report. It implements neither member and needs no stub —
    ``isinstance`` is simply ``False``, and the resolver records no technical
    bound for a deployment running on it. A capability *flag* would have forced
    every ceiling-free store to answer a question it has no answer to.
    """
    store = SqliteGraphStore(database_path=tmp_path / "capability.sqlite3")
    try:
        assert not isinstance(store, TraversalDepthCapability)
        assert not hasattr(store, "max_traversal_depth")
    finally:
        store.close()


def test_the_two_ceilinged_backends_agree_by_measurement_not_by_assumption() -> None:
    """A positive control for the two parametrized cases above.

    Both adapters declare 100 today, on the Neo4j precedent Fluree cites in its
    own comment. The pair is asserted equal *as a measured fact* so that a
    future divergence is visible here rather than silently making the two
    parametrized cases assert two different numbers under one name.
    """
    assert FLUREE_CEILING == NEO4J_CEILING
    assert FLUREE_CEILING > 0
