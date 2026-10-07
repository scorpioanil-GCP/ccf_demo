"""SEC-023 — the fifth path: a reader no boot composed refuses a classification query.

Coordinator ruling (1) on the deadline-row concerns under ``D-IMPL-374``
(2026-10-06): a store opened without ``ccf.boot.boot`` answering a
classification ``GraphQuery`` is a classification consumer with no authority
stamp available, so under ruling (2) it REFUSES, fail closed, by name. The
booted fabric's reader (``src/ccf/graph/governed_reader.py``) checks a query
against the resolution spec's authority and hands the store a query stamped
with it; a query arriving at a store reader any other way carries no stamp.

Every reader entry that answers a ``GraphQuery`` is named and covered:

* ``ccf.graph.reader.BaseGraphReader.query`` — the SQL/graph backends
  (SQLite measured here; Postgres, MongoDB, Neo4j and Fluree inherit it);
* ``ccf.graph.backends.memory.MemoryGraphReader.query``;
* ``ccf.graph.backends.fluree.FlureeGraphReader.query_pinned`` — the one
  ``SnapshotPinnable`` store entry (exercised offline over a stand-in store);
* ``ccf.graph.product_source.ProductSource.query`` — a mounted peer product,
  whose labels no local L2 governed (fail closed, ruling (3)).

Each test is RED on the tree before this repair: the query is answered.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ccf.assembly.worker import EntityResolutionSpec
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.graph.backends.memory import MemoryGraphStore
from ccf.graph.backends.sqlite import SqliteGraphStore
from ccf.graph.protocols import GraphQuery, StoreSnapshotPin
from ccf.signal.envelope import SignalEnvelope, SourceIdentity
from tests.composition import register_at_composition

TENANT = "tenant-a"
AS_OF = datetime(2026, 3, 1, tzinfo=UTC)


def _classification_query(tenant_id: str = TENANT, policy_version: str = "v1") -> GraphQuery:
    return GraphQuery(
        tenant_id=tenant_id,
        as_of=AS_OF,
        permitted_policy_bundle_versions=frozenset({policy_version}),
        classification_attribute_by_class={"counterparty": "classification"},
        permitted_classifications=frozenset({"public"}),
    )


def _assert_refused_by_name(error: pytest.ExceptionInfo[ValueError]) -> None:
    assert type(error.value).__name__ == "ClassificationAuthorityMissing"
    assert "SEC-023" in str(error.value)


def test_a_sqlite_store_opened_without_boot_refuses_a_classification_query(
    tmp_path: Path,
) -> None:
    """Data a GOVERNED fabric wrote is still not readable by label through a raw store."""
    from ccf.boot import boot

    database = tmp_path / "fabric.sqlite3"
    spec = EntityResolutionSpec.model_validate(
        {
            "semver": "1.0.0",
            "entity_rules": [
                {
                    "match_key": "counterparty_lei",
                    "entity_class": "counterparty",
                    "identity_keys": ["counterparty_lei"],
                    "attribute_keys": ["classification"],
                    "attribute_authorities": {"classification": ["source-a"]},
                }
            ],
        }
    )
    registry = ControlPlaneRegistry()
    spec_version = register_at_composition(registry, "test/spec", spec)
    policy_version = register_at_composition(registry, "test/policy", {"regime": "x"})
    handle = boot(
        backend="sqlite",
        connection={"database_path": str(database)},
        registry=registry,
        resolution_spec_key="test/spec",
        resolution_spec_version=spec_version,
        policy_bundle_key="test/policy",
        policy_bundle_version=policy_version,
        tenant_ids=(TENANT,),
    )
    try:
        handle.worker.ingest(
            SignalEnvelope(
                tenant_id=TENANT,
                envelope_id="env-a",
                source=SourceIdentity(system_id="source-a"),
                ingestion_timestamp=datetime(2026, 2, 1, tzinfo=UTC),
                observed_time=datetime(2026, 1, 31, tzinfo=UTC),
                raw_payload={"counterparty_lei": "LEI-1", "classification": "public"},
            )
        )
    finally:
        handle.close()

    with SqliteGraphStore(database_path=database) as raw:
        # Not a classification consumer: the raw store still answers.
        assert len(raw.reader.query(GraphQuery(tenant_id=TENANT, as_of=AS_OF)).entities) == 1
        with pytest.raises(ValueError) as refused:
            raw.reader.query(_classification_query(policy_version=policy_version))
    _assert_refused_by_name(refused)


def test_a_memory_store_reader_refuses_a_classification_query() -> None:
    reader = MemoryGraphStore().reader
    reader.query(GraphQuery(tenant_id=TENANT, as_of=AS_OF))
    with pytest.raises(ValueError) as refused:
        reader.query(_classification_query())
    _assert_refused_by_name(refused)


def test_the_fluree_pinned_entry_refuses_a_classification_query_before_any_io() -> None:
    from ccf.graph.backends.fluree import FLUREE_SUBSTRATE, FlureeGraphReader

    issued: list[Any] = []

    class _StandInStore:
        partition = "ccf_test"

        def post_query_pinned(self, query: Any, *, pin_t: int) -> list[dict[str, Any]]:
            issued.append(query)
            return []

    reader = FlureeGraphReader.__new__(FlureeGraphReader)
    reader._store = _StandInStore()  # type: ignore[assignment]
    pin = StoreSnapshotPin(substrate=FLUREE_SUBSTRATE, pin="7")
    reader.query_pinned(GraphQuery(tenant_id=TENANT, as_of=AS_OF), pin=pin)
    assert issued, "the stand-in must be reached by an unclassified pinned query"
    issued.clear()
    with pytest.raises(ValueError) as refused:
        reader.query_pinned(_classification_query(), pin=pin)
    _assert_refused_by_name(refused)
    assert issued == [], "the refusal must precede any substrate I/O"


def test_a_mounted_peer_product_refuses_a_classification_query(tmp_path: Path) -> None:
    from tests.graph.test_product_source import mounted

    source = mounted(work_dir=tmp_path, graph_state={"entities": [], "relationships": []})
    from tests.properties.strategies import TENANT as PRODUCT_TENANT

    source.query(GraphQuery(tenant_id=PRODUCT_TENANT, as_of=AS_OF))
    with pytest.raises(ValueError) as refused:
        source.query(_classification_query(tenant_id=PRODUCT_TENANT))
    _assert_refused_by_name(refused)
