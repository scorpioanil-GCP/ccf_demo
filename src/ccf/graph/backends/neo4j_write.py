"""The Neo4j graph write path — extras-gated (plan 15.2-12).

DESIGN.md §2A.5.3; whitepaper §7.3 (append-only-with-supersession graph state)
and INV-CH7-10 (only the Assembly worker holds a write handle). CCF SDK
extension surface: the module split itself is D-01 of Phase 15.4, not a
whitepaper commitment.

**This module is one of the modules CINV-02 guards.** The
``cinv02-graph-writer`` rule's guarded set is a *class* of modules — the
neutral base :mod:`ccf.graph._writer` plus every
``ccf.graph.backends.<name>_write`` — so this file joined the guard the moment
it existed, with no lint edit. Only ``ccf.assembly`` (L2) and ``ccf.boot`` (the
composition root) may import it. Threat T-15.2-06 is the reason the Cypher
write statements below are here rather than beside the read statements: write
code outside the guard is write code the lint never sees.

**Import direction is one-way, and that is structural.** This module imports
its own reader module, :mod:`ccf.graph.backends.neo4j`, freely. The reverse is
forbidden: if the reader imported the writer, every importer of the reader
would transitively reach write code and the CINV-02 rule would flag the reader
itself. The write module is therefore also where a ``REGISTRATION`` record
belongs (plan 15.4-04).

The driver stays an optional extra. Importing this module imports the reader
module, which demands the driver at *store construction* rather than at import,
so a tree without the extra remains importable.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any

from ccf.contracts.canonical import canonical_timestamp
from ccf.graph._writer import BaseGraphWriter, BootToken, _GraphTxn
from ccf.graph.backends.neo4j import ATTRIBUTE_PROPERTY_PREFIX, Neo4jGraphStore
from ccf.graph.reader import ENTITY_KIND, RELATIONSHIP_KIND, Row, parse_timestamp

__ccf_mode__ = "algorithmic"

__all__ = ["Neo4jGraphWriter"]


# --- the Neo4j write path (plan 15.2-12) --------------------------------------
#
# The nine typed operations as parameterized Cypher, confined to this module
# per the CINV-02 rule the module docstring states: the typed operation seam
# is part of the write path, and write code outside this module is write code
# outside the guard (threat T-15.2-06). Every value below travels as a driver
# parameter; no statement text is assembled from values. The `CCF_EDGE`
# Cypher relationship type is fixed SDK vocabulary — the artifact-authored
# CCF relationship type travels as the `relationship_type` property, never
# rendered into a pattern (threat T-15.2-01).

#: The insertion-order counter — the graph rendering of SQLite's ``rowid`` /
#: Postgres's ``BIGSERIAL``. Per-partition, so each graph owns its own
#: arrival order. Single-writer (INV-CH7-10) makes the read-increment safe.
_NEO4J_NEXT_SEQ = """
    MERGE (m:CcfMeta {partition: $partition, key: $key})
    ON CREATE SET m.value = 0
    SET m.value = m.value + 1
    RETURN m.value AS seq
"""

_NEO4J_UPSERT_ENTITY_NODE = """
    MERGE (e:CcfEntity {partition: $partition, tenant_id: $tenant_id,
                        entity_uri: $entity_uri})
    SET e.entity_class = coalesce(e.entity_class, $entity_class),
        e.first_observed_at = CASE
            WHEN e.first_observed_at IS NULL
                 OR $observed_at < e.first_observed_at
            THEN $observed_at ELSE e.first_observed_at END,
        e.last_observed_at = CASE
            WHEN e.last_observed_at IS NULL
                 OR $observed_at > e.last_observed_at
            THEN $observed_at ELSE e.last_observed_at END
"""

_NEO4J_INSERT_ENTITY_CLAIM = """
    MERGE (c:CcfEntityClaim {partition: $partition, tenant_id: $tenant_id,
                             entity_uri: $entity_uri, claim_id: $claim_id})
    ON CREATE SET c += $props, c.seq = $seq
"""

_NEO4J_SELECT_ENTITY_CHAIN = """
    MATCH (c:CcfEntityClaim {partition: $partition, tenant_id: $tenant_id,
                             entity_uri: $entity_uri})
    RETURN c.claim_id AS claim_id, c.observed_at AS observed_at
    ORDER BY c.observed_at, c.seq
"""

_NEO4J_UPDATE_ENTITY_SUPERSESSION = """
    MATCH (c:CcfEntityClaim {partition: $partition, tenant_id: $tenant_id,
                             entity_uri: $entity_uri, claim_id: $claim_id})
    SET c.superseded_by = $superseded_by, c.superseded_at = $superseded_at
    RETURN count(c) AS matched
"""

# Two statements rather than one: the endpoint upsert and the edge upsert run
# back-to-back inside the same driver transaction, so the MATCH below always
# finds the endpoints statement one just merged (reads see own writes — the
# _GraphTxn contract). Endpoint nodes merged here without an entity claim are
# placeholders — the graph rendering of a relationships-table row whose
# subject was never upserted as an entity; a later upsert_entity_node fills
# their identity columns via coalesce.
_NEO4J_UPSERT_RELATIONSHIP_ENDPOINTS = """
    MERGE (a:CcfEntity {partition: $partition, tenant_id: $tenant_id,
                        entity_uri: $subject_uri})
    MERGE (b:CcfEntity {partition: $partition, tenant_id: $tenant_id,
                        entity_uri: $object_uri})
"""

_NEO4J_UPSERT_RELATIONSHIP_EDGE = """
    MATCH (a:CcfEntity), (b:CcfEntity)
    WHERE a.partition = $partition AND a.tenant_id = $tenant_id
      AND a.entity_uri = $subject_uri
      AND b.partition = $partition AND b.tenant_id = $tenant_id
      AND b.entity_uri = $object_uri
    MERGE (a)-[e:CCF_EDGE {partition: $partition, tenant_id: $tenant_id,
                           relationship_key: $relationship_key}]->(b)
    SET e.relationship_type = coalesce(e.relationship_type, $relationship_type),
        e.subject_uri = $subject_uri, e.object_uri = $object_uri,
        e.first_observed_at = CASE
            WHEN e.first_observed_at IS NULL
                 OR $observed_at < e.first_observed_at
            THEN $observed_at ELSE e.first_observed_at END,
        e.last_observed_at = CASE
            WHEN e.last_observed_at IS NULL
                 OR $observed_at > e.last_observed_at
            THEN $observed_at ELSE e.last_observed_at END
"""

_NEO4J_INSERT_RELATIONSHIP_CLAIM = """
    MERGE (c:CcfRelationshipClaim {partition: $partition,
                                   tenant_id: $tenant_id,
                                   relationship_key: $relationship_key,
                                   claim_id: $claim_id})
    ON CREATE SET c += $props, c.seq = $seq
"""

_NEO4J_SELECT_RELATIONSHIP_CHAIN = """
    MATCH (c:CcfRelationshipClaim {partition: $partition,
                                   tenant_id: $tenant_id,
                                   relationship_key: $relationship_key})
    RETURN c.claim_id AS claim_id, c.observed_at AS observed_at
    ORDER BY c.observed_at, c.seq
"""

_NEO4J_UPDATE_RELATIONSHIP_SUPERSESSION = """
    MATCH (c:CcfRelationshipClaim {partition: $partition,
                                   tenant_id: $tenant_id,
                                   relationship_key: $relationship_key,
                                   claim_id: $claim_id})
    SET c.superseded_by = $superseded_by, c.superseded_at = $superseded_at
    RETURN count(c) AS matched
"""

_NEO4J_INSERT_LINEAGE = """
    MERGE (l:CcfLineage {partition: $partition, tenant_id: $tenant_id,
                         claim_kind: $claim_kind, node_key: $node_key,
                         claim_id: $claim_id, lineage_id: $lineage_id})
    ON CREATE SET l.entry_json = $entry_json
"""


def _neo4j_claim_projection(claim_json: str, *, kind: str) -> dict[str, object]:
    """Write-time projections of the predicate-relevant claim fields.

    The adapter's physical model (D-IMPL-34) stores, beside the verbatim
    ``claim_json``, the fields the pushed predicates compare — so the read
    path needs no JSON parsing in Cypher:

    * ``valid_from_cmp`` / ``valid_to_cmp``: the claim's validity window
      re-rendered through :func:`ccf.contracts.canonical.canonical_timestamp`,
      so the pushed `GQ-09` cut is fixed-width canonical-text comparison
      against the canonical boundary — chronologically exact whatever offset
      the claim was authored with (`GQ-24` at
      docs/GRAPH_QUERY_SEMANTICS.md:482);
    * entity claims: ``entity_class``, plus every **string-valued** attribute
      under ``ATTRIBUTE_PROPERTY_PREFIX``. Non-string attribute values are
      deliberately not projected: ``permitted_classifications`` is a set of
      strings, so a non-string value can never satisfy the `GQ-08`
      membership test — an absent property answers NULL, NULL is never IN a
      permitted set, and the two renderings are exactly equivalent to the
      fallback's ``attributes.get(name) in classifications``;
    * relationship claims: ``relationship_type`` / ``subject_uri`` /
      ``object_uri`` — the edge triple the traverse family and the
      induced-subgraph rule (`GQ-16` at docs/GRAPH_QUERY_SEMANTICS.md:316)
      constrain.

    ``None`` values are omitted rather than set: Cypher ``+=`` removes a
    property for a null map entry, and an absent property already reads back
    as NULL.
    """
    payload: dict[str, Any] = json.loads(claim_json)
    props: dict[str, object] = {}
    valid_from = payload.get("valid_from")
    if valid_from is not None:
        parsed_from = parse_timestamp(valid_from)
        assert parsed_from is not None  # narrowed by the None check above
        props["valid_from_cmp"] = canonical_timestamp(parsed_from)
    valid_to = payload.get("valid_to")
    if valid_to is not None:
        parsed_to = parse_timestamp(valid_to)
        assert parsed_to is not None  # narrowed by the None check above
        props["valid_to_cmp"] = canonical_timestamp(parsed_to)
    if kind == ENTITY_KIND:
        props["entity_class"] = payload["entity_class"]
        for name, value in payload.get("attributes", {}).items():
            if isinstance(value, str):
                props[ATTRIBUTE_PROPERTY_PREFIX + name] = value
    else:
        props["relationship_type"] = payload["relationship_type"]
        props["subject_uri"] = payload["subject_uri"]
        props["object_uri"] = payload["object_uri"]
    return props


class _Neo4jTxn:
    """The nine :class:`_GraphTxn` operations as parameterized Cypher.

    One open driver transaction (explicit ``begin_transaction``), so the two
    contract rules hold natively: reads inside the transaction see its own
    writes (``select_*_chain`` includes claims appended earlier in the same
    transaction), and mutating operations resolve their rowcounts before
    commit — ``MERGE … ON CREATE`` reports creation through the result
    summary's ``nodes_created`` counter, which is 1 for a new claim and 0
    for a re-arrival: the writer's idempotency signal, and for lineage the
    L-axis set-union itself (INV-CH7-17).

    Lives in this module and only this module, per the CINV-02 rule the
    module docstring states (threat T-15.2-06): no session or transaction
    construction exists in ``ccf.graph.backends.neo4j`` beyond reads.
    """

    def __init__(self, *, tx: Any, partition: str) -> None:
        self._tx = tx
        self._partition = partition

    def _run(self, statement: str, params: dict[str, object]) -> Any:
        params["partition"] = self._partition
        return self._tx.run(statement, params)

    def _created(self, statement: str, params: dict[str, object]) -> int:
        """Rows actually created — 0 for an ignored duplicate (the contract)."""
        counters = self._run(statement, params).consume().counters
        return int(counters.nodes_created)

    def _matched(self, statement: str, params: dict[str, object]) -> int:
        record = self._run(statement, params).single()
        return int(record["matched"]) if record is not None else 0

    def _next_seq(self) -> int:
        record = self._run(_NEO4J_NEXT_SEQ, {"key": "seq"}).single()
        return int(record["seq"])

    def upsert_entity_node(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        entity_class: str,
        observed_at: str,
    ) -> int:
        self._run(
            _NEO4J_UPSERT_ENTITY_NODE,
            {
                "tenant_id": tenant_id,
                "entity_uri": entity_uri,
                "entity_class": entity_class,
                "observed_at": observed_at,
            },
        ).consume()
        return 1

    def insert_entity_claim(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        claim_id: str,
        claim_json: str,
        observed_at: str,
        policy_bundle_version: str,
    ) -> int:
        props = _neo4j_claim_projection(claim_json, kind=ENTITY_KIND)
        props["claim_json"] = claim_json
        props["observed_at"] = observed_at
        props["policy_bundle_version"] = policy_bundle_version
        return self._created(
            _NEO4J_INSERT_ENTITY_CLAIM,
            {
                "tenant_id": tenant_id,
                "entity_uri": entity_uri,
                "claim_id": claim_id,
                "props": props,
                "seq": self._next_seq(),
            },
        )

    def select_entity_chain(
        self, *, tenant_id: str, entity_uri: str
    ) -> Sequence[Row]:
        result = self._run(
            _NEO4J_SELECT_ENTITY_CHAIN,
            {"tenant_id": tenant_id, "entity_uri": entity_uri},
        )
        return [dict(record) for record in result]

    def update_entity_supersession(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        claim_id: str,
        superseded_by: str | None,
        superseded_at: str | None,
    ) -> int:
        return self._matched(
            _NEO4J_UPDATE_ENTITY_SUPERSESSION,
            {
                "tenant_id": tenant_id,
                "entity_uri": entity_uri,
                "claim_id": claim_id,
                "superseded_by": superseded_by,
                "superseded_at": superseded_at,
            },
        )

    def upsert_relationship_node(
        self,
        *,
        tenant_id: str,
        relationship_key: str,
        relationship_type: str,
        subject_uri: str,
        object_uri: str,
        observed_at: str,
    ) -> int:
        self._run(
            _NEO4J_UPSERT_RELATIONSHIP_ENDPOINTS,
            {
                "tenant_id": tenant_id,
                "subject_uri": subject_uri,
                "object_uri": object_uri,
            },
        ).consume()
        self._run(
            _NEO4J_UPSERT_RELATIONSHIP_EDGE,
            {
                "tenant_id": tenant_id,
                "relationship_key": relationship_key,
                "relationship_type": relationship_type,
                "subject_uri": subject_uri,
                "object_uri": object_uri,
                "observed_at": observed_at,
            },
        ).consume()
        return 1

    def insert_relationship_claim(
        self,
        *,
        tenant_id: str,
        relationship_key: str,
        claim_id: str,
        claim_json: str,
        observed_at: str,
        policy_bundle_version: str,
    ) -> int:
        props = _neo4j_claim_projection(claim_json, kind=RELATIONSHIP_KIND)
        props["claim_json"] = claim_json
        props["observed_at"] = observed_at
        props["policy_bundle_version"] = policy_bundle_version
        return self._created(
            _NEO4J_INSERT_RELATIONSHIP_CLAIM,
            {
                "tenant_id": tenant_id,
                "relationship_key": relationship_key,
                "claim_id": claim_id,
                "props": props,
                "seq": self._next_seq(),
            },
        )

    def select_relationship_chain(
        self, *, tenant_id: str, relationship_key: str
    ) -> Sequence[Row]:
        result = self._run(
            _NEO4J_SELECT_RELATIONSHIP_CHAIN,
            {"tenant_id": tenant_id, "relationship_key": relationship_key},
        )
        return [dict(record) for record in result]

    def update_relationship_supersession(
        self,
        *,
        tenant_id: str,
        relationship_key: str,
        claim_id: str,
        superseded_by: str | None,
        superseded_at: str | None,
    ) -> int:
        return self._matched(
            _NEO4J_UPDATE_RELATIONSHIP_SUPERSESSION,
            {
                "tenant_id": tenant_id,
                "relationship_key": relationship_key,
                "claim_id": claim_id,
                "superseded_by": superseded_by,
                "superseded_at": superseded_at,
            },
        )

    def insert_lineage(
        self,
        *,
        tenant_id: str,
        claim_kind: str,
        node_key: str,
        claim_id: str,
        lineage_id: str,
        entry_json: str,
    ) -> int:
        return self._created(
            _NEO4J_INSERT_LINEAGE,
            {
                "tenant_id": tenant_id,
                "claim_kind": claim_kind,
                "node_key": node_key,
                "claim_id": claim_id,
                "lineage_id": lineage_id,
                "entry_json": entry_json,
            },
        )


class Neo4jGraphWriter(BaseGraphWriter):
    """The single ``GraphWriter`` over one Neo4j graph — extras-gated (plan 15.2-12).

    Same algorithm as every other writer, inherited rather than restated.
    What differs is the transaction: :class:`_Neo4jTxn` implements the nine
    typed operations as parameterized Cypher over one explicit driver
    transaction — no SQL ``ClassVar`` statements are set here, exactly as
    the memory backend (the typed seam's second non-SQL implementation).
    All-or-nothing comes from the driver transaction: commit on success,
    rollback on exception.
    """

    def __init__(self, *, store: Neo4jGraphStore, token: BootToken) -> None:
        super().__init__(store=store, token=token)
        self._store = store

    @contextmanager
    def _transaction(self) -> Iterator[_GraphTxn]:
        self._check_open()
        with self._store.session() as session:
            tx = session.begin_transaction()
            try:
                yield _Neo4jTxn(tx=tx, partition=self._store.partition)
            except BaseException:
                tx.rollback()
                raise
            else:
                tx.commit()
