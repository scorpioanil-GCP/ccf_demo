"""Read-only estate position reads, before and after a census run.

`D-IMPL-358` ruling 8 and ruling 12's write rule. CLAUDE.md §9: *"READ the
curated estate … WRITE to a local disposable store. Never the reverse."*

**Zero movement is the pass condition.** A Fluree ledger is append-only, so a
single accidental write can never be removed — 27 ``ccf:cp04-*`` ledgers on the
curated server are the standing proof. So the census measures a position before
and after, and `tools/estate_census/classify.py::classify` asserts equality
mechanically rather than trusting that nothing wrote.

**No write path exists here, and that is checked rather than asserted.** Three
separate guarantees, of decreasing strength:

* **PostgreSQL is server-enforced.** Every connection sets
  ``connection.read_only = True`` before issuing a statement, so the server
  itself refuses a write on this connection. Not a convention — a posture the
  database holds.
* **Fluree is method-restricted.** `_fluree_ledgers` issues one ``GET`` against
  the toolkit's own ``/v1/fluree/ledgers`` path. No transact endpoint is named
  anywhere in this module.
* **Mongo is call-restricted.** Only ``list_collection_names`` and
  ``count_documents`` are called.

and one structural check over all three:
`tools/estate_census_tests/test_watermarks.py::test_this_module_names_no_write_verb`
reads this file's own source and refuses any write verb, so a future edit that
adds one reddens a control instead of shipping.

**An unreachable store is UNMEASURED, never zero.** A probe that cannot connect
records an ``error`` key and no position. Recording zero would make an outage
indistinguishable from an empty store, and comparing two zeros would then
*prove* the estate did not move — the exact shape of collapsing *don't know*
into *pass*.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from tools.estate_census.redaction import redact_target

#: Read timeout for every probe, in seconds. Generous: a census runs once and a
#: slow answer is worth more than a fast unknown.
TIMEOUT_SECONDS = 30.0


def _sha(items: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(items)).encode()).hexdigest()


@dataclasses.dataclass(frozen=True)
class StoreDeclaration:
    """One store to measure, named by the ENVIRONMENT VARIABLE that locates it.

    The roster declares variable NAMES, never values, which is what lets the
    roster live in the repository while the credential does not. `D-IMPL-358`
    ruling 10 — *"the co-lender estate is included WHEN Wave 2 exercises a path
    backed by it, and not otherwise"* — is therefore a roster edit rather than a
    code change.
    """

    key: str
    kind: str
    target_env: str
    scope_env: str = ""
    scopes: tuple[str, ...] = ()

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> StoreDeclaration:
        return StoreDeclaration(
            key=str(raw["key"]),
            kind=str(raw["kind"]),
            target_env=str(raw["target_env"]),
            scope_env=str(raw.get("scope_env", "")),
            scopes=tuple(str(item) for item in raw.get("scopes", ())),
        )


def load_roster(path: Path) -> tuple[StoreDeclaration, ...] | None:
    """The declared store roster, or ``None`` when it cannot be read.

    ``None`` is *don't know*: a census whose roster failed to load has measured
    nothing, and must not proceed as though the estate had no stores.
    """
    try:
        loaded = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(loaded, list):
        return None
    try:
        return tuple(StoreDeclaration.from_dict(entry) for entry in loaded)
    except (KeyError, TypeError, ValueError):
        return None


def _fluree_ledgers(url: str) -> dict[str, Any]:
    """Every ledger the server holds, with each one's transaction position.

    Deliberately the WHOLE roster rather than one named ledger: a stray write
    creates a *new* ledger as readily as it advances a known one, and a probe
    watching only ``fibo-v2`` would not see the 27 ``ccf:cp04-*`` ledgers this
    rule exists because of.
    """
    import httpx

    response = httpx.get(f"{url}/v1/fluree/ledgers", timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    entries = response.json()
    roster = [f"{entry.get('name')}:{entry.get('branch')}" for entry in entries]
    return {
        "ledger_count": len(entries),
        "ledger_roster_sha256": _sha(roster),
        "ledger_positions": {
            f"{entry.get('name')}:{entry.get('branch')}": entry.get("t") for entry in entries
        },
    }


def _postgres_counts(dsn: str, schemas: tuple[str, ...]) -> dict[str, Any]:
    """Row counts per table for each declared schema, on a READ-ONLY connection."""
    import psycopg

    position: dict[str, Any] = {}
    with psycopg.connect(dsn, connect_timeout=int(TIMEOUT_SECONDS)) as connection:
        connection.read_only = True
        with connection.cursor() as cursor:
            cursor.execute("select count(*) from information_schema.schemata")
            row = cursor.fetchone()
            position["server_schema_count"] = row[0] if row else None
            for schema in schemas:
                cursor.execute(
                    "select table_name from information_schema.tables"
                    " where table_schema = %s and table_type = 'BASE TABLE'"
                    " order by table_name",
                    (schema,),
                )
                tables = [record[0] for record in cursor.fetchall()]
                counts: dict[str, int] = {}
                for table in tables:
                    cursor.execute(f'select count(*) from "{schema}"."{table}"')
                    record = cursor.fetchone()
                    counts[table] = record[0] if record else -1
                position[f"schema:{schema}"] = {
                    "table_count": len(tables),
                    "total_rows": sum(counts.values()),
                    "per_table_sha256": _sha([f"{k}={v}" for k, v in counts.items()]),
                    "per_table": counts,
                }
    return position


def _mongo_counts(uri: str, database: str) -> dict[str, Any]:
    """Document counts per collection. Only read calls are made."""
    import pymongo

    client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=int(TIMEOUT_SECONDS * 1000))
    try:
        handle = client[database]
        collections = sorted(handle.list_collection_names())
        counts = {name: handle[name].count_documents({}) for name in collections}
    finally:
        client.close()
    return {
        "collection_count": len(counts),
        "per_collection_sha256": _sha([f"{k}={v}" for k, v in counts.items()]),
        "per_collection": counts,
    }


def _sqlite_digest(path_text: str) -> dict[str, Any]:
    """File digest and size. A byte-level position for a file-backed store."""
    blob = Path(path_text).read_bytes()
    return {"sha256": hashlib.sha256(blob).hexdigest(), "size_bytes": len(blob)}


def measure_one(store: StoreDeclaration, environ: dict[str, str] | None = None) -> dict[str, Any]:
    """One store's position, or an ``error`` describing why there is none.

    The rendered target is always `redact_target`'d, so the measurement records
    WHICH store was read without recording the credential that reached it.
    """
    env = os.environ if environ is None else environ
    target = env.get(store.target_env, "")
    record: dict[str, Any] = {"kind": store.kind, "target": redact_target(target)}
    if not target:
        record["error"] = f"{store.target_env} is unset — nothing was measured"
        return record
    scopes = store.scopes
    if store.scope_env:
        declared = env.get(store.scope_env, "")
        if declared:
            scopes = tuple(part.strip() for part in declared.split(",") if part.strip())
    try:
        if store.kind == "fluree":
            record["position"] = _fluree_ledgers(target)
        elif store.kind == "postgres":
            record["position"] = _postgres_counts(target, scopes)
        elif store.kind == "mongo":
            record["position"] = _mongo_counts(target, scopes[0] if scopes else "")
        elif store.kind == "sqlite":
            record["position"] = _sqlite_digest(target)
        else:
            record["error"] = f"unknown store kind {store.kind!r} — nothing was measured"
    except Exception as exc:                       # noqa: BLE001 — an outage is a fact
        record["error"] = f"{type(exc).__name__}: {exc}"
    return record


def measure(
    roster: tuple[StoreDeclaration, ...], environ: dict[str, str] | None = None
) -> dict[str, Any]:
    """Every declared store's position, keyed by declaration key."""
    return {store.key: measure_one(store, environ) for store in roster}
