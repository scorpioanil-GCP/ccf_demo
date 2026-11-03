#!/usr/bin/env python3
"""Introspect all five stores and emit the estate's data catalog.

    uv run generators/build_store_catalog.py

## Why this is a generator and not a written document

A hand-written catalog of 115 Postgres tables, 1,009 columns, 178 Fluree
predicates and six schemaless Mongo collections is stale the day it is
written, and this repository has recorded the cost of stale documents often
enough (`known-issues.md` §53–§55 are all a claim outliving the thing it
described). Everything here is READ FROM THE LIVE STORES on every run, so the
catalog can be regenerated rather than corrected.

## What it is for

The SDK side engineers Context Products from these sources and needs to know
what actually exists: types, nullability, keys, provenance class, and for
MongoDB the document shape, which no schema declares. Per the exchange
agreement of 2026-08-29, `ccf_dataprep` is authoritative for the "what data
exists" term — SOR, provenance class, `G` axis, volumetrics — so this file is
the evidence behind that claim rather than an assertion of it.

## Two deliberate limits

**MongoDB is SAMPLED, not scanned.** `passage` holds 37,865 documents and the
host is shared with an unrelated production database. Field presence is
reported as a percentage OF THE SAMPLE with the sample size stated, never as a
fact about the collection. A field appearing in 100% of 500 sampled documents
is not a field that is always present, and this file does not say it is.

**Database enumeration never happens.** The Mongo host also carries an
unrelated 5.5M-document estate. Every connection here is scoped to the
configured database by name.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from ccf.config import (  # noqa: E402
    FLUREE_LEDGER_V2, MONGO_DB_V2, PG, PG_SCHEMA_V2, SQLITE_PATH, pg_connect,
)

MONGO_SAMPLE = 500
OUT_JSON = REPO_ROOT / "docs" / "store-catalog.json"
OUT_MD = REPO_ROOT / "docs" / "store-catalog.md"


# --------------------------------------------------------------------------
# Postgres
# --------------------------------------------------------------------------

def postgres() -> dict:
    S = PG_SCHEMA_V2
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT table_name, column_name, data_type, is_nullable, "
            "character_maximum_length, numeric_precision, numeric_scale "
            "FROM information_schema.columns WHERE table_schema = %s "
            "ORDER BY table_name, ordinal_position", (S,))
        cols: dict[str, list] = defaultdict(list)
        for t, c, dt, nul, clen, nprec, nscale in cur.fetchall():
            typ = dt
            if clen:
                typ = f"{dt}({clen})"
            elif nprec and dt in ("numeric", "decimal"):
                typ = f"{dt}({nprec},{nscale})"
            cols[t].append({"column": c, "type": typ, "nullable": nul == "YES"})

        cur.execute(
            "SELECT t.relname, c.contype, pg_get_constraintdef(c.oid) "
            "FROM pg_constraint c JOIN pg_class t ON t.oid = c.conrelid "
            "JOIN pg_namespace n ON n.oid = t.relnamespace "
            "WHERE n.nspname = %s AND c.contype IN ('p','f','u') "
            "ORDER BY 1", (S,))
        keys: dict[str, list] = defaultdict(list)
        kind = {"p": "PRIMARY KEY", "f": "FOREIGN KEY", "u": "UNIQUE"}
        for t, ct, definition in cur.fetchall():
            keys[t].append({"kind": kind[ct], "definition": definition})

        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = %s AND table_type = 'BASE TABLE' "
            "ORDER BY 1", (S,))
        tables = [r[0] for r in cur.fetchall()]

        out = {}
        for t in tables:
            cur.execute(f'SELECT count(*) FROM "{S}"."{t}"')
            n = cur.fetchone()[0]
            prov = None
            if any(c["column"] == "provenance" for c in cols[t]):
                cur.execute(f'SELECT DISTINCT provenance FROM "{S}"."{t}" '
                            "WHERE provenance IS NOT NULL ORDER BY 1")
                prov = [r[0] for r in cur.fetchall()]
            out[t] = {"rows": n, "columns": cols[t], "keys": keys.get(t, []),
                      "provenance_values": prov}
        # VIEWS, which the base-table filter above deliberately excludes and
        # which a consumer still needs to know exist -- `v_ownership_cross_border`
        # is a join a Context Product would otherwise rebuild by hand.
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = %s AND table_type = 'VIEW' ORDER BY 1", (S,))
        views = {}
        for (v,) in cur.fetchall():
            cur.execute(f'SELECT count(*) FROM "{S}"."{v}"')
            views[v] = {"rows": cur.fetchone()[0], "columns": cols.get(v, [])}

    return {"schema": S, "database": PG["dbname"],
            "table_count": len(out), "view_count": len(views),
            "views": views,
            "column_count": sum(len(v["columns"]) for v in out.values()),
            "tables": out}


# --------------------------------------------------------------------------
# SQLite
# --------------------------------------------------------------------------

def sqlite_store() -> dict:
    con = sqlite3.connect(SQLITE_PATH)
    out = {}
    for (t,) in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        cols = [{"column": r[1], "type": r[2] or "(untyped)",
                 "nullable": not r[3], "primary_key": bool(r[5])}
                for r in con.execute(f'PRAGMA table_info("{t}")')]
        n = con.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0]
        out[t] = {"rows": n, "columns": cols}
    con.close()
    return {"path": str(SQLITE_PATH.relative_to(REPO_ROOT)),
            "table_count": len(out), "tables": out}


# --------------------------------------------------------------------------
# MongoDB — inferred document specifications
# --------------------------------------------------------------------------

def _walk(doc, prefix, acc):
    """Record every field PATH and the BSON type(s) seen at it."""
    for k, v in doc.items():
        path = f"{prefix}.{k}" if prefix else k
        acc[path].append(type(v).__name__)
        if isinstance(v, dict):
            _walk(v, path, acc)
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            _walk(v[0], f"{path}[]", acc)


def mongo() -> dict:
    from ccf.config import mongo_db
    db = mongo_db()          # scoped by name; never enumerates databases
    out = {}
    for name in sorted(db.list_collection_names()):
        coll = db[name]
        total = coll.estimated_document_count()
        sample = list(coll.aggregate(
            [{"$sample": {"size": min(MONGO_SAMPLE, max(total, 1))}}]))
        acc: dict[str, list] = defaultdict(list)
        for d in sample:
            _walk(d, "", acc)
        fields = []
        for path in sorted(acc):
            types = Counter(acc[path])
            fields.append({
                "field": path,
                "types": sorted(types),
                "present_in_sample_pct": round(100 * len(acc[path]) / max(len(sample), 1), 1),
            })
        out[name] = {"documents": total, "sampled": len(sample),
                     "fields": fields}
    return {"database": MONGO_DB_V2, "collection_count": len(out),
            "sample_size": MONGO_SAMPLE,
            "note": "Field presence is a percentage OF THE SAMPLE, not of the "
                    "collection. Absence from a sample is not absence.",
            "collections": out}


# --------------------------------------------------------------------------
# Fluree
# --------------------------------------------------------------------------

def fluree_store() -> dict:
    from ccf import fluree
    L = FLUREE_LEDGER_V2

    def scalar(q):
        b = fluree.query(q)["results"]["bindings"]
        return int(b[0]["n"]["value"]) if b else 0

    # PREDICATES ARE ENUMERATED AND THEN VERIFIED ONE BY ONE, because this
    # ledger's three ways of answering "how many predicates" give three
    # different answers (measured 2026-08-29, known-issues §56):
    #
    #     COUNT(DISTINCT ?p)   178   wrong
    #     GROUP BY ?p          198   wrong -- invents 27 phantoms
    #     SELECT DISTINCT ?p   171   correct
    #
    # The phantoms are not harmless noise: `ex:_d0` and
    # `ex:AdministrativeAgent` appear in the GROUP BY result and return ZERO
    # rows when queried directly as predicates. A catalog published from the
    # GROUP BY would hand the SDK 27 predicates that do not exist.
    #
    # So every candidate is confirmed by asking for one row through it, and
    # its assertion count is taken with its own COUNT rather than from the
    # GROUP BY that produced the phantoms.
    candidates = {b["p"]["value"] for b in fluree.query(
        f"SELECT DISTINCT ?p FROM <{L}> WHERE {{ ?s ?p ?o }} "
        f"LIMIT 1000")["results"]["bindings"]}
    group_by_rows = fluree.query(
        f"SELECT ?p (COUNT(?s) AS ?n) FROM <{L}> WHERE {{ ?s ?p ?o }} "
        f"GROUP BY ?p LIMIT 1000")["results"]["bindings"]
    candidates |= {b["p"]["value"] for b in group_by_rows}
    # Both wrong answers are MEASURED on every build, never quoted. They were
    # literals (178, 198) until 2026-10-09, and the published sentence then
    # set a stale 198 beside a live 181 and a live 29 phantoms -- three
    # numbers that cannot all be true at once.
    aggregate_answers = {
        "count_distinct": scalar(
            f"SELECT (COUNT(DISTINCT ?p) AS ?n) FROM <{L}> WHERE {{ ?s ?p ?o }}"),
        "group_by_rows": len(group_by_rows),
    }
    predicates, phantoms = [], []
    for iri in sorted(candidates):
        if fluree.query(f"SELECT ?s FROM <{L}> WHERE {{ ?s <{iri}> ?o }} "
                        f"LIMIT 1")["results"]["bindings"]:
            predicates.append({
                "predicate": iri,
                "assertions": scalar(f"SELECT (COUNT(?s) AS ?n) FROM <{L}> "
                                     f"WHERE {{ ?s <{iri}> ?o }}")})
        else:
            phantoms.append(iri)
    predicates.sort(key=lambda d: -d["assertions"])
    types = fluree.query(
        f"SELECT ?t (COUNT(?s) AS ?n) FROM <{L}> WHERE "
        f"{{ ?s a ?t }} GROUP BY ?t ORDER BY DESC(?n) LIMIT 200")["results"]["bindings"]
    return {
        "ledger": L,
        "triples": scalar(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ ?s ?p ?o }}"),
        "subjects": scalar(f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{L}> WHERE {{ ?s ?p ?o }}"),
        "predicate_count": len(predicates),
        "predicate_count_method": (
            "SELECT DISTINCT then verified one-by-one by direct query. This "
            f"ledger's COUNT(DISTINCT ?p) says {aggregate_answers['count_distinct']} "
            f"and GROUP BY ?p says {aggregate_answers['group_by_rows']}; "
            "neither is trusted. See known-issues §56."),
        "aggregate_answers": aggregate_answers,
        "phantom_predicates_rejected": phantoms,
        "predicates": predicates,
        "types": [{"type": b["t"]["value"], "instances": int(b["n"]["value"])}
                  for b in types],
    }


# --------------------------------------------------------------------------
# Neo4j
# --------------------------------------------------------------------------

def neo4j_store() -> dict:
    import os
    db_name = os.getenv("NEO4J_DATABASE", "neo4j")
    try:
        from neo4j import GraphDatabase
        drv = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://192.168.4.76:7687"),
            auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD")))
        with drv.session() as s:
            out = {
                "nodes": s.run("MATCH (n) RETURN count(n) AS n").single()["n"],
                "relationships": s.run(
                    "MATCH ()-[r]->() RETURN count(r) AS n").single()["n"],
                "labels": sorted(s.run("CALL db.labels()").value()),
                "relationship_types": sorted(
                    s.run("CALL db.relationshipTypes()").value()),
                "property_keys": sorted(s.run("CALL db.propertyKeys()").value()),
            }
        drv.close()
        out["database"] = db_name
        out["status"] = ("v1 starter set only — no v2 Context Product depends "
                         "on this store; see CLAUDE.md's open decision")
        return out
    except Exception as exc:  # noqa: BLE001
        return {"database": db_name,
                "status": f"unreachable: {type(exc).__name__}: {str(exc)[:80]}"}



def render_markdown(cat: dict) -> str:
    """The human-readable half. The JSON carries every column; this carries
    the shape, the volumetrics and the caveats a reader needs BEFORE trusting
    either."""
    pg, fl = cat["stores"]["postgres"], cat["stores"]["fluree"]
    mg, sq, n4 = (cat["stores"]["mongodb"], cat["stores"]["sqlite"],
                  cat["stores"]["neo4j"])
    L: list[str] = []
    w = L.append

    w("# ccf_dataprep — estate data catalog\n")
    w(f"Generated **{cat['generated_at']}** by "
      "`generators/build_store_catalog.py`, read from the live stores. "
      "Regenerate rather than correct.\n")
    w("`ccf_dataprep` is authoritative for the **what data exists** term "
      "(exchange agreement, 2026-08-29): SOR, provenance class, `G` axis, "
      "volumetrics. This file is the evidence behind that claim.\n")
    w("Full column-level detail, including every type and key, is in the "
      "companion **`store-catalog.json`**.\n")

    w("## The partition\n")
    w("Nothing is mirrored. Each store is authoritative for a different "
      "slice, which is what makes cross-store assembly a real operation "
      "rather than a staged one.\n")
    w("| Store | Address | Owns | Scale |")
    w("|---|---|---|---|")
    w(f"| **Fluree** | ledger `{fl['ledger']}` | "
      "`R`, `T`, lineage, policy binding | "
      f"{fl['triples']:,} triples · {fl['subjects']:,} subjects · "
      f"{fl['predicate_count']} predicates |")
    w(f"| **Postgres** | schema `{pg['schema']}` in database "
      f"`{pg['database']}` | `E`, policy reference | "
      f"{pg['table_count']} tables · {pg['column_count']} columns · "
      f"{pg['view_count']} views |")
    w(f"| **MongoDB** | database `{mg['database']}` | "
      f"passage-level lineage | {mg['collection_count']} collections |")
    w(f"| **SQLite** | file `{sq['path']}` | departmental | "
      f"{sq['table_count']} tables |")
    w(f"| **Neo4j** | database `{n4.get('database', '?')}` | optional | "
      f"{n4.get('nodes', '?')} nodes · "
      f"{n4.get('relationships', '?')} relationships |")
    w("")
    w("**Every address above names its own level**, because the five names "
      "are not the same kind of thing — a Fluree ledger, a Postgres schema "
      "*inside* a database, two databases, a file path — and `fibo-v2` and "
      "`fibo_v2` differ by one character. An unqualified name in that column "
      "is a defect, not a shorthand: it reads as a database name, and a "
      "reader who tries to connect to it fails. Anything mirroring this "
      "table must carry the Address column intact.\n")

    w("## Read this before trusting a number\n")
    w(f"- **Fluree predicate counts are not obtainable by aggregate.** This "
      f"ledger answers *\"how many predicates\"* three ways and only one is "
      f"right: `COUNT(DISTINCT ?p)` says "
      f"{fl['aggregate_answers']['count_distinct']}, `GROUP BY ?p` says "
      f"{fl['aggregate_answers']['group_by_rows']}, and "
      f"the truth is **{fl['predicate_count']}**. The aggregates surface "
      f"{len(fl['phantom_predicates_rejected'])} phantoms — `ex:_d0` and "
      f"`ex:AdministrativeAgent` among them — which return ZERO rows when "
      f"queried directly. Every predicate below was enumerated and then "
      f"confirmed by asking for a row through it. See known-issues §56.")
    w(f"- **MongoDB field presence is sampled**, {mg['sample_size']} documents "
      f"per collection. A field in 100% of a sample is not a field that is "
      f"always present, and absence from a sample is not absence.")
    w("- **Neo4j holds the v1 starter set only.** No v2 Context Product "
      "depends on it.\n")

    w("## Postgres — `E`, the bank-internal slice and all entity attributes\n")
    w("| Table | Rows | Cols | Provenance classes |")
    w("|---|---:|---:|---|")
    for t, v in sorted(pg["tables"].items(), key=lambda kv: -kv[1]["rows"]):
        prov = ", ".join(v["provenance_values"]) if v["provenance_values"] else "—"
        w(f"| `{t}` | {v['rows']:,} | {len(v['columns'])} | {prov} |")
    w("")
    if pg["views"]:
        w("**Views** (not base tables; a consumer would otherwise rebuild "
          "these joins by hand):\n")
        for v, meta in pg["views"].items():
            w(f"- `{v}` — {meta['rows']:,} rows")
        w("")

    w("## Fluree — `R` and `T`, the typed edge graph and its valid time\n")
    w("Nodes carry `lei` plus a display label and nothing else; every "
      "attribute resolves from Postgres. Top 40 predicates by assertion "
      "count:\n")
    w("| Predicate | Assertions |")
    w("|---|---:|")
    for d in fl["predicates"][:40]:
        w(f"| `{d['predicate']}` | {d['assertions']:,} |")
    w(f"\n*{fl['predicate_count']} predicates total; the full list is in the "
      f"JSON.*\n")
    if fl.get("types"):
        w("Declared types by instance count (top 15):\n")
        w("| Type | Instances |")
        w("|---|---:|")
        for d in fl["types"][:15]:
            w(f"| `{d['type']}` | {d['instances']:,} |")
        w("")

    w("## MongoDB — passage-level lineage\n")
    for name, meta in sorted(mg["collections"].items()):
        w(f"### `{name}` — {meta['documents']:,} documents "
          f"({meta['sampled']} sampled)\n")
        w("| Field | Type(s) | Present in sample |")
        w("|---|---|---:|")
        for f in meta["fields"]:
            w(f"| `{f['field']}` | {', '.join(f['types'])} | "
              f"{f['present_in_sample_pct']}% |")
        w("")

    w("## SQLite — the departmental store\n")
    w("Deliberately a local file. The point of the narrative is that the "
      "fabric must reach a small, locally-maintained system to enforce an "
      "enterprise-critical policy.\n")
    for t, meta in sorted(sq["tables"].items()):
        cols = ", ".join(f"`{c['column']}` {c['type']}" for c in meta["columns"])
        w(f"- **`{t}`** — {meta['rows']:,} rows · {cols}")
    w("")

    w("## Neo4j\n")
    w(f"{n4.get('status', 'unknown')}\n")
    if n4.get("labels"):
        w(f"- Labels: {', '.join('`' + x + '`' for x in n4['labels'])}")
        w(f"- Relationship types: "
          f"{', '.join('`' + x + '`' for x in n4['relationship_types'])}")
        w("")
    return "\n".join(L) + "\n"


def main() -> int:
    print("Building the estate catalog from live introspection…")
    cat = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "ccf_dataprep, generators/build_store_catalog.py",
        "authoritative_for": (
            "the 'what data exists' term per the 2026-08-29 exchange "
            "agreement: SOR, provenance class, G axis, volumetrics"),
        "stores": {},
    }
    for name, fn in (("postgres", postgres), ("fluree", fluree_store),
                     ("mongodb", mongo), ("sqlite", sqlite_store),
                     ("neo4j", neo4j_store)):
        print(f"  {name}…", flush=True)
        cat["stores"][name] = fn()

    OUT_JSON.write_text(json.dumps(cat, indent=2, default=str) + "\n")
    OUT_MD.write_text(render_markdown(cat))
    print(f"\n  -> {OUT_JSON.relative_to(REPO_ROOT)} "
          f"({OUT_JSON.stat().st_size / 1024:.0f} KB)")
    pg = cat["stores"]["postgres"]
    print(f"     postgres {pg['table_count']} tables / {pg['column_count']} columns")
    print(f"     fluree   {cat['stores']['fluree']['predicate_count']} predicates")
    print(f"     mongodb  {cat['stores']['mongodb']['collection_count']} collections")
    print(f"     sqlite   {cat['stores']['sqlite']['table_count']} tables")
    return 0


if __name__ == "__main__":
    sys.exit(main())
