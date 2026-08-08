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
