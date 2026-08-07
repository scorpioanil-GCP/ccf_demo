"""Row-source independence of the materialization core (plan 15.2-03).

The proof the non-SQL readers of this phase rely on: any Row-Protocol source —
a plain ``dict`` qualifies — fed into ``ccf.graph.reader.materialize_view``
with a lineage supplier produces a ``GraphView`` byte-identical to the one the
sqlite SQL path renders over the same content. The comparison is on
``canonical_bytes``, never raw rows, so the assertion is about the contract
layer (04-RESEARCH.md Pitfall 3) and the later differential suites compare
semantics rather than materialization accidents (15.2-RESEARCH.md Pitfall 5).

Discipline inherited from the conformance suite: nothing here constructs a
writer — every claim enters through booted L2. The direct parameterized
SELECTs below are *reads* against the same database file the fabric booted
over; this is a reader test, not a writer bypass.
"""

from __future__ import annotations

import random
import sqlite3
from collections.abc import Callable, Sequence
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ccf.contracts.canonical import canonical_bytes, canonical_timestamp
from ccf.contracts.claims import EntityClaim, LineageEntry, RelationshipClaim
from ccf.graph.reader import ENTITY_KIND, RELATIONSHIP_KIND, Row, materialize_view
from ccf.signal.envelope import SourceIdentity

if TYPE_CHECKING:
    from ccf.boot import FabricHandle

TENANT_A = "tenant-a"

T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = datetime(2026, 2, 1, tzinfo=UTC)
T2 = datetime(2026, 3, 1, tzinfo=UTC)

# The as-of row filter, verbatim from the sqlite backend's dialect but with the
# ORDER BY deliberately omitted: the core orders the view, never the source
# (locked roadmap constraint 3), so an unordered row set must materialize the
# same canonical bytes the ordered SQL path does.
_ENTITY_ROWS_AS_OF = """
    SELECT entity_uri, claim_id, claim_json, policy_bundle_version,
           superseded_by, superseded_at
    FROM entity_claims
    WHERE tenant_id = ?
      AND observed_at <= ?
      AND (superseded_at IS NULL OR superseded_at > ?)
"""
_RELATIONSHIP_ROWS_AS_OF = """
    SELECT relationship_key, claim_id, claim_json, policy_bundle_version,
           superseded_by, superseded_at
    FROM relationship_claims
    WHERE tenant_id = ?
      AND observed_at <= ?
      AND (superseded_at IS NULL OR superseded_at > ?)
"""
_ALL_LINEAGE_ROWS = """
    SELECT claim_kind, node_key, claim_id, entry_json
    FROM lineage
    WHERE tenant_id = ?
"""


def _lineage(system_id: str, envelope_id: str, observed_at: datetime) -> LineageEntry:
    return LineageEntry(
        source=SourceIdentity(system_id=system_id),
        envelope_id=envelope_id,
        observed_at=observed_at,
    )


def _entity(
    *,
    entity_uri: str,
    entity_class: str = "counterparty",
    attributes: dict[str, str] | None = None,
    observed_at: datetime = T1,
    lineage_entries: tuple[LineageEntry, ...],
) -> EntityClaim:
    return EntityClaim(
        tenant_id=TENANT_A,
        entity_uri=entity_uri,
        entity_class=entity_class,
        attributes=attributes or {"legal_name": "Acme Holdings"},
        observed_at=observed_at,
        valid_from=T0,
        lineage=frozenset(lineage_entries),
    )


def _dict_rows(rows: Sequence[sqlite3.Row]) -> list[dict[str, Any]]:
    """Rebuild substrate rows as plain dicts keyed by the SQL column names."""
    return [{key: row[key] for key in row.keys()} for row in rows]


def _dict_lineage_supplier(
    lineage_rows: Sequence[sqlite3.Row],
) -> Callable[[str, str, str], Sequence[Row]]:
    """A dict-backed lineage supplier — an index lookup, no SQL, no boundary.

    Deliberately returns *every* accumulated entry for a claim, exactly as
    ``SELECT_LINEAGE`` does: the boundary filter is the core's job, and a
    supplier that pre-filtered would be the fork this plan exists to prevent.
    """
    index: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in lineage_rows:
        key = (row["claim_kind"], row["node_key"], row["claim_id"])
        index.setdefault(key, []).append({"entry_json": row["entry_json"]})

    def rows_for(kind: str, node_key: str, claim_id: str) -> Sequence[Row]:
        return tuple(index.get((kind, node_key, claim_id), ()))

    return rows_for


def test_dict_rows_materialize_byte_identically_to_the_sqlite_path(
    fabric_boot: Callable[..., "FabricHandle"], tmp_path: Path
) -> None:
    """The load-bearing assertion: the view does not depend on the row source.

    Claims enter through booted L2 (idempotent upsert, lineage union,
    supersession — the real write path). The same database is then read twice:
    once through ``reader.as_of()`` (the SQL client of the core) and once as
    raw rows rebuilt into plain dicts and fed to ``materialize_view`` with a
    dict-backed lineage supplier. Byte equality at two boundaries exercises
    both centralized rules differentially — at T1 the superseding claim and
    the late lineage entry are future information; at T2 both are in view.
    """
    database_path = tmp_path / "fabric.sqlite3"
    fabric = fabric_boot(database_path=database_path)

    acme_v1 = _entity(
        entity_uri="counterparty://acme",
        lineage_entries=(_lineage("core-banking", "env-1", T1),),
    )
    facility = _entity(
        entity_uri="facility://rcf-1",
        entity_class="facility",
        attributes={"commitment": "250000000"},
        lineage_entries=(_lineage("core-banking", "env-2", T1),),
    )
    edge = RelationshipClaim(
        tenant_id=TENANT_A,
        relationship_type="obligor_of",
        subject_uri="counterparty://acme",
        object_uri="facility://rcf-1",
        attributes={},
        observed_at=T1,
        valid_from=T0,
        lineage=frozenset({_lineage("core-banking", "env-3", T1)}),
    )
    # Supersedes acme_v1 at T2: current at T2, future information at T1.
    acme_v2 = _entity(
        entity_uri="counterparty://acme",
        attributes={"legal_name": "Acme Holdings plc"},
        observed_at=T2,
        lineage_entries=(_lineage("core-banking", "env-4", T2),),
    )
    # Same claim content as `facility`, corroborated by a second source at T2:
    # the lineage set unions, and the T2 entry must be absent from a T1 view.
    facility_corroborated = _entity(
        entity_uri="facility://rcf-1",
        entity_class="facility",
        attributes={"commitment": "250000000"},
        lineage_entries=(_lineage("kyc", "env-5", T2),),
    )

    fabric.worker.admit_entity_claim(tenant_id=TENANT_A, claim=acme_v1)
    fabric.worker.admit_entity_claim(tenant_id=TENANT_A, claim=facility)
    fabric.worker.admit_relationship_claim(tenant_id=TENANT_A, claim=edge)
    fabric.worker.admit_entity_claim(tenant_id=TENANT_A, claim=acme_v2)
    fabric.worker.admit_entity_claim(
        tenant_id=TENANT_A, claim=facility_corroborated
    )

    for at in (T1, T2):
        sql_view = fabric.reader.as_of(tenant_id=TENANT_A, at=at)

        with closing(sqlite3.connect(database_path)) as connection:
            connection.row_factory = sqlite3.Row
            boundary = canonical_timestamp(at)
            entity_rows = _dict_rows(
                connection.execute(
                    _ENTITY_ROWS_AS_OF, (TENANT_A, boundary, boundary)
                ).fetchall()
            )
            relationship_rows = _dict_rows(
                connection.execute(
                    _RELATIONSHIP_ROWS_AS_OF, (TENANT_A, boundary, boundary)
                ).fetchall()
            )
            lineage_rows_for = _dict_lineage_supplier(
                connection.execute(_ALL_LINEAGE_ROWS, (TENANT_A,)).fetchall()
            )

        dict_view = materialize_view(
            entity_rows=entity_rows,
            relationship_rows=relationship_rows,
            tenant_id=TENANT_A,
            as_of=at,
            lineage_rows_for=lineage_rows_for,
        )

        assert canonical_bytes(dict_view) == canonical_bytes(sql_view)


def test_boundary_rendering_holds_over_dict_rows() -> None:
    """The two centralized rules fire on dict rows exactly as documented.

    A lineage entry observed after the boundary is absent from the record's
    lineage (the lineage-at-boundary rule), and a supersession that took
    effect after the boundary renders as ``(None, None)`` (the
    supersession-as-of rule) — the ``reader.py`` docstring semantics,
    unchanged by the refactor.
    """
    early = _lineage("core-banking", "env-1", T0)
    late = _lineage("kyc", "env-2", T2)
    claim = _entity(
        entity_uri="counterparty://acme",
        observed_at=T0,
        lineage_entries=(early,),
    )
    entity_row: dict[str, Any] = {
        "entity_uri": "counterparty://acme",
        "claim_id": "claim-1",
        "claim_json": claim.model_dump_json(),
        "policy_bundle_version": "policy-v1",
        # Superseded after the boundary: the row filter keeps the claim
        # current; the core must keep its supersession edge out of the view.
        "superseded_by": "claim-2",
        "superseded_at": canonical_timestamp(T2),
    }
    index = {
        (ENTITY_KIND, "counterparty://acme", "claim-1"): (
            {"entry_json": early.model_dump_json()},
            {"entry_json": late.model_dump_json()},
        )
    }

    def rows_for(kind: str, node_key: str, claim_id: str) -> Sequence[Row]:
        return index.get((kind, node_key, claim_id), ())

    view = materialize_view(
        entity_rows=(entity_row,),
        relationship_rows=(),
        tenant_id=TENANT_A,
        as_of=T1,
        lineage_rows_for=rows_for,
    )

    (record,) = view.entities
    assert record.claim.lineage == frozenset({early})
    assert record.superseded_by is None
    assert record.superseded_at is None


def test_shuffled_rows_materialize_in_canonical_order() -> None:
    """View ordering belongs to the core, never to the row source.

    A source that answers rows in arbitrary order still materializes entities
    sorted by ``entity_uri`` and relationships sorted by ``relationship_key``
    — the ``GraphView`` determinism contract, applied at materialization.
    """
    uris = [f"counterparty://{name}" for name in ("alpha", "beta", "gamma", "delta")]
    entity_rows: list[dict[str, Any]] = []
    for uri in uris:
        claim = _entity(
            entity_uri=uri,
            observed_at=T0,
            lineage_entries=(_lineage("core-banking", f"env-{uri}", T0),),
        )
        entity_rows.append(
            {
                "entity_uri": uri,
                "claim_id": f"claim-{uri}",
                "claim_json": claim.model_dump_json(),
                "policy_bundle_version": "policy-v1",
                "superseded_by": None,
                "superseded_at": None,
            }
        )

    keys = [f"rel-{name}" for name in ("north", "east", "south", "west")]
    relationship_rows: list[dict[str, Any]] = []
    for key in keys:
        edge = RelationshipClaim(
            tenant_id=TENANT_A,
            relationship_type="obligor_of",
            subject_uri=uris[0],
            object_uri=uris[1],
            attributes={},
            observed_at=T0,
            valid_from=T0,
            lineage=frozenset({_lineage("core-banking", f"env-{key}", T0)}),
        )
        relationship_rows.append(
            {
                "relationship_key": key,
                "claim_id": f"claim-{key}",
                "claim_json": edge.model_dump_json(),
                "policy_bundle_version": "policy-v1",
                "superseded_by": None,
                "superseded_at": None,
            }
        )

    shuffle = random.Random(15203)
    shuffle.shuffle(entity_rows)
    shuffle.shuffle(relationship_rows)

    def rows_for(kind: str, node_key: str, claim_id: str) -> Sequence[Row]:
        return ()

    view = materialize_view(
        entity_rows=entity_rows,
        relationship_rows=relationship_rows,
        tenant_id=TENANT_A,
        as_of=T1,
        lineage_rows_for=rows_for,
    )

    assert [record.claim.entity_uri for record in view.entities] == sorted(uris)
    assert [record.relationship_key for record in view.relationships] == sorted(keys)
