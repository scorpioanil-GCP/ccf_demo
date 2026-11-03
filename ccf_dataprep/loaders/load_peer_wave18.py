#!/usr/bin/env python3
"""Wave 18 Task 14 -- load the CO-LENDER's estate.

    uv run loaders/load_peer_wave18.py

This is the only file in this repository that WRITES to the peer fabric.
Everything it writes comes from `sources/screening/wave18_peer.json`
(`generators/generate_peer_positions.py`), and it touches nothing on our
side except one read-only lookup it does not perform at all -- the
generator already resolved every facility against `ccf_v2.facility`.

## Why the gates are the first thing in the file

`parkavedb` (ours) and `bofa_syndicated` (the peer's) sit on the SAME host
and the SAME port and differ by nothing but a name. A misdirected
`CREATE TABLE` lands in the wrong bank's estate, and the failure is
silent: the DDL succeeds, the load reports its counts, and the thing this
whole wave exists to demonstrate -- assembly ACROSS an organizational
boundary -- has quietly become assembly within one.

So every write path here passes `_assert_peer_target(cur)` first, and it
runs three checks in order:

    assert_distinct_fabrics()          the two configurations are not
                                       secretly one (same db, same role,
                                       same ledger)
    assert_co_lender_schema(...)       the schema is the peer's, and is
                                       not one of ours
    SELECT current_database(), ...     the SERVER's own account of what
                                       this connection reached

The third is the one that cannot be fooled by configuration, and it holds
the expected values as **hardcoded literals** on purpose. Reading them
from `CO_LENDER_PG` instead would look tidier and would be worthless: a
gate that derives its expectation from the same source that opened the
connection agrees with whatever it is handed, including a `.env` edited to
point at `parkavedb`. The literal is the entire value of the check.

`_assert_peer_ledger()` is the same idea for Fluree, which needs it just
as much: the peer's Fluree is our own host on a different PORT, and Fluree
is append-only, so a misdirected write could not be undone.

## What lands, and at what precision

One table, `colender.peer_position`, and two typed counterparty nodes on
the peer's ledger. §F's floor is that one counterparty discloses an exact
figure and another discloses only a band -- Bank of America exact,
Citibank band-only -- and the loader enforces that shape three times over
before it writes anything: the CHECK constraint on the table, an
artifact-level assertion that no banded counterparty carries an exact
figure on ANY of its rows (the denominator, not just the banded rows), and
`validators/test_syndicate.py`, which re-derives the concealed figure from
the filed schedule and proves the band neither reveals it nor excludes it.

## Idempotency

Postgres: upsert on `position_id`, which the generator derives from
content (LEI + facility_id), never from row order. Rows the artifact no
longer proposes are deleted -- this loader owns the whole table, so a row
left behind by an earlier scheme is a stale row, not another writer's.

Fluree is append-only, so idempotency there is retract-then-insert:
`reconcile_peer_graph()` removes every triple whose subject falls under
`ex:peer/` -- this loader's own prefix, and nothing else's -- before the
insert. That makes a change of node SCHEME safe to re-run, not merely a
change of value.
"""

from __future__ import annotations

import json
import sys

import requests

from ccf import fluree
from ccf.config import (
    CO_LENDER_FLUREE_LEDGER,
    CO_LENDER_FLUREE_URL,
    CO_LENDER_PG_SCHEMA,
    EX,
    FLUREE_URL,
    REPO_ROOT,
    FabricBoundaryError,
    assert_co_lender_schema,
    assert_distinct_fabrics,
    co_lender_pg_connect,
)
from ccf.syndicate import (
    EX_DISCLOSURE_PRECISION,
    FIBO_FINANCE_SYNDICATE_MEMBER,
    LOCAL_COMPOSITE_TTL_SECONDS,
    MAX_FEDERATION_LATENCY_MS,
)
from loaders.load_collateral_wave9 import triple, uri

SCREEN = REPO_ROOT / "sources" / "screening"
PEER_PATH = SCREEN / "wave18_peer.json"

PS = CO_LENDER_PG_SCHEMA

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
EX_PROVENANCE = f"{EX}provenance"

#: The one subject prefix this loader mints on the peer ledger. Retracting
#: everything under it before each insert is what makes a re-run safe in an
#: append-only store.
PEER_SUBJECT_PREFIX = f"{EX}peer/"

BATCH = 200

PROVENANCE_CLASSES = {"public", "synthetic — internal", "synthetic — engineered"}


# --- the gates -------------------------------------------------------------

def _assert_peer_target(cur) -> None:
    """Three gates, in order, before any DDL touches the peer.

    Both databases sit on 192.168.4.76:5432 and differ by nothing but a
    name. A one-character difference is not something to trust an eye with.
    """
    assert_distinct_fabrics()
    assert_co_lender_schema(CO_LENDER_PG_SCHEMA)
    cur.execute("SELECT current_database(), current_user")
    db, user = cur.fetchone()
    if db != "bofa_syndicated" or user != "colender":
        raise FabricBoundaryError(
            f"refusing to write: connected to {db!r} as {user!r}, "
            f"expected 'bofa_syndicated' as 'colender'")


def _assert_peer_ledger() -> str:
    """The Fluree half of the same discipline.

    The peer's Fluree is the SAME HOST as ours on a different port, and
    Fluree is append-only: a write aimed at the wrong instance cannot be
    taken back. `_co_lender_guard` already refuses our ledger NAMES; this
    adds the two things it cannot see -- that the peer's endpoint is not
    our endpoint, and that the ledger is the specific one this task was
    told to write, held as a literal for the same reason the Postgres gate
    holds its database name as one.
    """
    assert_distinct_fabrics()
    if not CO_LENDER_FLUREE_URL or \
            CO_LENDER_FLUREE_URL.rstrip("/") == FLUREE_URL.rstrip("/"):
        raise FabricBoundaryError(
            f"the co-lender Fluree endpoint is {CO_LENDER_FLUREE_URL!r}, "
            f"which is our own ({FLUREE_URL!r}) -- the peer needs its own "
            f"instance, not our instance under another ledger name")
    if CO_LENDER_FLUREE_LEDGER != "bofa/syndicate":
        raise FabricBoundaryError(
            f"refusing to write ledger {CO_LENDER_FLUREE_LEDGER!r}, expected "
            f"'bofa/syndicate'")
    return fluree._co_lender_guard(CO_LENDER_FLUREE_LEDGER)


def _ensure_peer_ledger() -> bool:
    """Create the peer ledger if it is absent. Returns True if created."""
    ledger = _assert_peer_ledger()
    if fluree.co_lender_ledger_t() is not None:
        return False
    base = CO_LENDER_FLUREE_URL.rstrip("/")
    resp = requests.post(f"{base}/v1/fluree/create",
                         json={"ledger": ledger}, timeout=60)
    if resp.status_code >= 400:
        raise fluree.FlureeError(
            f"peer ledger create failed {resp.status_code}: {resp.text[:200]}")
    return True


# --- DDL -------------------------------------------------------------------

DDL = f'''
CREATE TABLE IF NOT EXISTS "{PS}".peer_position (
    position_id     TEXT PRIMARY KEY,
    counterparty    TEXT NOT NULL,
    facility_id     TEXT NOT NULL,
    -- Exactly one of (share_usd) or (band_low, band_high) is populated.
    -- A counterparty that discloses at band granularity must have NO
    -- exact figure anywhere on this fabric, or the mixed-precision floor
    -- is theatre. Enforced by CHECK and re-proved live in Task 16.
    share_usd       NUMERIC NULL,
    band_low        NUMERIC NULL,
    band_high       NUMERIC NULL,
    internal_rating TEXT NOT NULL,
    workout_posture TEXT NOT NULL,
    as_of           DATE NOT NULL,
    provenance      TEXT NOT NULL,
    CHECK ((share_usd IS NOT NULL AND band_low IS NULL AND band_high IS NULL)
        OR (share_usd IS NULL AND band_low IS NOT NULL AND band_high IS NOT NULL
            AND band_low < band_high))
);

-- Task 15. The three §F conditions that sound like runtime behaviour --
-- a request that times out, a claim nobody attested, a remote TTL
-- shorter than ours -- represented as declarations in data. The SDK
-- reads and acts on these; this loader only writes the row.
CREATE TABLE IF NOT EXISTS "{PS}".peer_product_declaration (
    declaration_id        TEXT PRIMARY KEY,
    counterparty          TEXT NOT NULL,
    product_id            TEXT NOT NULL,
    declared_ttl_seconds  INTEGER NOT NULL,
    declared_latency_ms   INTEGER NOT NULL,
    -- NULL is the point of the unattested-claim floor: an absent
    -- attestation, not a boolean flag standing in for one.
    attestation           JSONB NULL,
    provenance            TEXT NOT NULL
);
'''


# --- artifact --------------------------------------------------------------

def load_artifact() -> dict:
    return json.loads(PEER_PATH.read_text())


def assert_artifact_shape(doc: dict) -> None:
    """Refuse to write an artifact that does not already satisfy §F.

    The CHECK constraint catches a row disclosing both ways. It cannot
    catch the thing that actually defeats the floor: one counterparty with
    an exact row on one facility and a banded row on another, each
    individually legal. So the DENOMINATOR is checked here, per
    counterparty, over every row -- the same question
    `validators/test_syndicate.py` asks of the loaded fabric afterwards,
    asked once before anything is written.
    """
    rows = doc["positions"]
    assert rows, "the artifact carries no positions"

    by_counterparty: dict[str, set[str]] = {}
    for row in rows:
        exact = row["share_usd"] is not None
        banded = row["band_low"] is not None and row["band_high"] is not None
        assert exact != banded, (
            f"{row['position_id']}: a position must disclose exactly one way, "
            f"got share_usd={row['share_usd']!r} band=[{row['band_low']!r}, "
            f"{row['band_high']!r}]")
        if banded:
            assert row["band_low"] < row["band_high"], (
                f"{row['position_id']}: a band whose bounds are equal or "
                f"inverted is an exact figure wearing a costume")
        assert row["provenance"] in PROVENANCE_CLASSES, (
            f"{row['position_id']}: provenance {row['provenance']!r} is not "
            f"one of CLAUDE.md's three classes")
        by_counterparty.setdefault(row["counterparty"], set()).add(
            "exact" if exact else "band")

    mixed = {cp: sorted(kinds) for cp, kinds in by_counterparty.items()
             if len(kinds) > 1}
    assert not mixed, (
        f"{mixed} disclose both ways -- precision is then not a property of "
        f"the counterparty and §F's floor proves nothing")

    kinds = {k for kinds in by_counterparty.values() for k in kinds}
    assert kinds == {"exact", "band"}, (
        f"§F needs one counterparty at each precision; the artifact has "
        f"{sorted(kinds)}")

    ids = [row["position_id"] for row in rows]
    assert len(ids) == len(set(ids)), "duplicate position_id in the artifact"


# MAX_FEDERATION_LATENCY_MS and LOCAL_COMPOSITE_TTL_SECONDS (both §B) are
# imported from ccf/syndicate.py, not redefined here (whole-branch review
# fix -- consolidates what were four independent copies under two names).


def assert_declarations_shape(doc: dict) -> None:
    """Task 15: refuse to write an artifact whose declarations collapse a
    contrast. Defense in depth -- `generate_peer_positions.py` already
    proves this before the artifact is written; re-checked here so a
    stale or hand-edited artifact cannot slip past the loader."""
    declarations = doc["declarations"]
    assert declarations, "the artifact carries no product declarations"
    assert len(declarations) > 1, (
        "only one declaration -- if everything is unattested, nothing is "
        "contrasted")

    for d in declarations:
        assert d["provenance"] in PROVENANCE_CLASSES, (
            f"{d['declaration_id']}: provenance {d['provenance']!r} is not "
            f"one of CLAUDE.md's three classes")

    unattested = [d["declaration_id"] for d in declarations
                  if d["attestation"] is None]
    assert len(unattested) == 1, (
        f"{len(unattested)} unattested declarations; the floor needs "
        f"exactly one so the case stays identifiable")

    latencies = [d["declared_latency_ms"] for d in declarations]
    assert any(l > MAX_FEDERATION_LATENCY_MS for l in latencies), (
        "no declaration would breach the 5s default bound")
    assert any(l <= MAX_FEDERATION_LATENCY_MS for l in latencies), (
        "every declaration is slow -- fail-closed would demonstrate nothing")

    ttls = [d["declared_ttl_seconds"] for d in declarations]
    assert min(ttls) < LOCAL_COMPOSITE_TTL_SECONDS, (
        f"shortest declared TTL is {min(ttls)}s; never below the "
        f"{LOCAL_COMPOSITE_TTL_SECONDS}s local composite")
    assert max(ttls) > LOCAL_COMPOSITE_TTL_SECONDS, (
        "no declared TTL exceeds the local composite -- a TTL merely equal "
        "to it does not show the local composite winning as the shorter "
        "value, so the 'shortest of them' rule would bind trivially")

    ids = [d["declaration_id"] for d in declarations]
    assert len(ids) == len(set(ids)), "duplicate declaration_id in the artifact"


# --- Postgres --------------------------------------------------------------

def write_positions(cur, rows: list[dict]) -> tuple[int, int]:
    """Upsert every position; delete any this loader wrote before and no
    longer proposes. Owns every column in `DDL` and names no other task's.
    Returns (upserted, deleted)."""
    _assert_peer_target(cur)

    keep = [row["position_id"] for row in rows]
    cur.execute(f'DELETE FROM "{PS}".peer_position '
                f"WHERE position_id <> ALL(%s)", (keep,))
    deleted = cur.rowcount

    values = [(r["position_id"], r["counterparty"], r["facility_id"],
               r["share_usd"], r["band_low"], r["band_high"],
               r["internal_rating"], r["workout_posture"], r["as_of"],
               r["provenance"]) for r in rows]
    cur.executemany(
        f'INSERT INTO "{PS}".peer_position '
        "(position_id, counterparty, facility_id, share_usd, band_low, "
        " band_high, internal_rating, workout_posture, as_of, provenance) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
        "ON CONFLICT (position_id) DO UPDATE SET "
        "counterparty=EXCLUDED.counterparty, "
        "facility_id=EXCLUDED.facility_id, "
        "share_usd=EXCLUDED.share_usd, "
        "band_low=EXCLUDED.band_low, band_high=EXCLUDED.band_high, "
        "internal_rating=EXCLUDED.internal_rating, "
        "workout_posture=EXCLUDED.workout_posture, "
        "as_of=EXCLUDED.as_of, provenance=EXCLUDED.provenance",
        values)
    return len(values), deleted


def write_declarations(cur, declarations: list[dict]) -> tuple[int, int]:
    """Upsert every product declaration; delete any this loader wrote
    before and no longer proposes. Owns every column in `DDL`'s
    `peer_product_declaration` and names no other task's. Returns
    (upserted, deleted). `attestation` is stored as-is (a dict, or None
    for the deliberately unattested row) -- psycopg serializes the dict
    for the JSONB column the same way `raw_names` is serialized in
    `loaders/load_postgres_wave18.py`."""
    _assert_peer_target(cur)

    keep = [d["declaration_id"] for d in declarations]
    cur.execute(f'DELETE FROM "{PS}".peer_product_declaration '
                f"WHERE declaration_id <> ALL(%s)", (keep,))
    deleted = cur.rowcount

    values = [(d["declaration_id"], d["counterparty"], d["product_id"],
               d["declared_ttl_seconds"], d["declared_latency_ms"],
               json.dumps(d["attestation"]) if d["attestation"] is not None
               else None,
               d["provenance"]) for d in declarations]
    cur.executemany(
        f'INSERT INTO "{PS}".peer_product_declaration '
        "(declaration_id, counterparty, product_id, declared_ttl_seconds, "
        " declared_latency_ms, attestation, provenance) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s) "
        "ON CONFLICT (declaration_id) DO UPDATE SET "
        "counterparty=EXCLUDED.counterparty, product_id=EXCLUDED.product_id, "
        "declared_ttl_seconds=EXCLUDED.declared_ttl_seconds, "
        "declared_latency_ms=EXCLUDED.declared_latency_ms, "
        "attestation=EXCLUDED.attestation, provenance=EXCLUDED.provenance",
        values)
    return len(values), deleted


# --- Fluree ----------------------------------------------------------------

def counterparty_node(lei: str) -> str:
    """Keyed on the LEI, the one identifier both fabrics genuinely share.
    Under `ex:peer/` so `reconcile_peer_graph()` has a prefix that belongs
    to this loader alone."""
    return uri(f"peer/counterparty/{lei}")


def build_counterparty_triples(doc: dict) -> list[str]:
    """One node per counterparty identity.

    Fluree runs without OWL inference (CLAUDE.md rule 7), so the node is
    typed explicitly as a `FinanceSyndicateMember` -- the role every query
    against it uses. `ex:disclosurePrecision` is the term
    `docs/ccf_dataprep_v2.md` already binds for exactly this ("`exact` or
    `band`, on a peer position"); nothing new is minted by this task, so
    the binding table and its vault mirror are unchanged.

    Node discipline: lei, label, precision, provenance. No amount, no band
    -- the figures live in the peer's Postgres and nowhere else.
    """
    triples: list[str] = []
    for cp in doc["counterparties"]:
        node = counterparty_node(cp["counterparty"])
        triples += [
            triple(node, RDF_TYPE, FIBO_FINANCE_SYNDICATE_MEMBER),
            triple(node, RDFS_LABEL, cp["legal_name"], literal=True),
            triple(node, f"{EX}lei", cp["counterparty"], literal=True),
            triple(node, EX_DISCLOSURE_PRECISION, cp["disclosure_precision"],
                   literal=True),
            triple(node, EX_PROVENANCE, cp["provenance"], literal=True),
        ]
    return triples


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def reconcile_peer_graph() -> int:
    """Retract every triple on the peer ledger whose SUBJECT falls under
    `PEER_SUBJECT_PREFIX`. Returns the number retracted."""
    ledger = _assert_peer_ledger()
    q = (f'SELECT ?s ?p ?o FROM <{ledger}> WHERE {{ ?s ?p ?o . '
         f'FILTER(STRSTARTS(STR(?s), "{PEER_SUBJECT_PREFIX}")) }}')
    statements = []
    for b in fluree.co_lender_query(q).get("results", {}).get("bindings", []):
        s, p, o = b["s"]["value"], b["p"]["value"], b["o"]["value"]
        obj = f'"{_esc(o)}"' if b["o"].get("type") == "literal" else f"<{o}>"
        statements.append(f"<{s}> <{p}> {obj} .")

    for i in range(0, len(statements), BATCH):
        fluree.co_lender_update(
            "DELETE DATA {\n" + "\n".join(statements[i:i + BATCH]) + "\n}")
    return len(statements)


def write_peer_graph(triples: list[str]) -> int:
    ledger = _assert_peer_ledger()
    for i in range(0, len(triples), BATCH):
        fluree.co_lender_update(
            "INSERT DATA {\n" + "\n".join(triples[i:i + BATCH]) + "\n}",
            ledger=ledger)
    return len(triples)


# --- entry point -----------------------------------------------------------

def load_peer(dry_run: bool = False) -> dict:
    """Load the peer estate. Returns counts.

    `dry_run` builds and validates everything and still runs all three
    gates against a live connection -- a dry run that skipped the gates
    would tell you nothing about the run that matters.
    """
    doc = load_artifact()
    assert_artifact_shape(doc)
    assert_declarations_shape(doc)
    rows = doc["positions"]
    declarations = doc["declarations"]
    triples = build_counterparty_triples(doc)

    result = {
        "dry_run": dry_run,
        "counterparties": len(doc["counterparties"]),
        "positions": len(rows),
        "exact_rows": sum(1 for r in rows if r["share_usd"] is not None),
        "banded_rows": sum(1 for r in rows if r["share_usd"] is None),
        "graph_triples": len(triples),
        "declarations": len(declarations),
        "unattested_declarations": sum(
            1 for d in declarations if d["attestation"] is None),
    }

    with co_lender_pg_connect() as conn, conn.cursor() as cur:
        _assert_peer_target(cur)
        cur.execute("SELECT current_database(), current_user")
        result["database"], result["user"] = cur.fetchone()
        result["schema"] = PS

        if dry_run:
            conn.rollback()
            result.update(upserted=0, deleted_stale=0, retracted=0,
                          written=0, declarations_upserted=0,
                          declarations_deleted_stale=0,
                          ledger_t=fluree.co_lender_ledger_t())
            return result

        cur.execute(DDL)
        upserted, deleted = write_positions(cur, rows)
        result["upserted"], result["deleted_stale"] = upserted, deleted
        d_upserted, d_deleted = write_declarations(cur, declarations)
        result["declarations_upserted"] = d_upserted
        result["declarations_deleted_stale"] = d_deleted

    result["ledger_created"] = _ensure_peer_ledger()
    result["retracted"] = reconcile_peer_graph()
    result["written"] = write_peer_graph(triples)
    result["ledger_t"] = fluree.co_lender_ledger_t()
    return result


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    result = load_peer(dry_run=dry_run)

    print("\nWave 18 Task 14 -- co-lender estate"
          f"{' (DRY RUN, nothing written)' if dry_run else ''}\n")
    print(f"  target        {result['database']}/{result['schema']} "
          f"as {result['user']} · ledger {CO_LENDER_FLUREE_LEDGER}")
    for key in ("counterparties", "positions", "exact_rows", "banded_rows",
                "upserted", "deleted_stale", "graph_triples", "retracted",
                "written", "declarations", "unattested_declarations",
                "declarations_upserted", "declarations_deleted_stale"):
        print(f"  {key:<24} {result[key]:>6}")
    print(f"\n  peer ledger now at t={result['ledger_t']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
