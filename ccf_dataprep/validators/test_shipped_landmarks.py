#!/usr/bin/env python3
"""Every hardcoded count SHIPPED IN THE BUNDLE must match the live estate.

`test_bundle_landmarks.py` guards `PG_LANDMARKS` in `portable/verify_install.py`.
That was half the surface. The bundle ships expectations in **two other
places** nothing was checking:

* `portable/verify_install.py` also hardcodes Fluree, MongoDB, SQLite and
  Neo4j counts inline in `Check(...)` calls -- outside `PG_LANDMARKS`.
* every `portable/restore/restore_*.sh` carries its OWN copy of the numbers
  and aborts the restore on a mismatch, BEFORE the verifier ever runs.

That second one bit on 2026-09-01. Wave 20 took `ccf_v2` from 113 to 115
tables. `PG_LANDMARKS` was updated and guarded; `restore_postgres.sh` kept
asserting 113. A bundle rebuilt from the current estate would have aborted
mid-restore with `RESTORE MISMATCH: parkavedb.ccf_v2 expected=113 found=115`
-- a correct dump, a correct restore, and a hard failure, discovered on a
laptop with no repo checkout on it.

So this harvests expectations from BOTH shipped sources and measures each
against the live estate. The harvest is the important half: a number nobody
extracted is a number nobody can find stale, so an assertion added to a
restore script fails `test_every_shipped_expectation_is_registered` until
somebody says how to measure it.

    uv run --with pytest pytest validators/test_shipped_landmarks.py
"""

from __future__ import annotations

import ast
import os
import re
import sqlite3
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
VERIFY = REPO / "portable" / "verify_install.py"
RESTORE_DIR = REPO / "portable" / "restore"


# --------------------------------------------------------------------------
# Harvest — pull every shipped expectation out of the files that ship it
# --------------------------------------------------------------------------

def harvest_verify_install() -> dict[str, int]:
    """`Check("label", <int literal>, ...)` call sites, read by AST.

    AST rather than regex because the second argument must be an *integer
    literal* to count: `Check("...", 87162, n)` is an expectation, and
    `Check("...", expected, n)` is a variable the harvest cannot resolve and
    must not silently treat as absent.
    """
    tree = ast.parse(VERIFY.read_text())
    out: dict[str, int] = {}
    unresolved: list[str] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "Check"
                and len(node.args) >= 2):
            continue
        label, expected = node.args[0], node.args[1]
        if not isinstance(label, ast.Constant) or not isinstance(label.value, str):
            continue
        # `bool` is an `int` subclass in Python, so a Check(..., True, ...)
        # would harvest as the landmark "1". A boolean is a yes/no about the
        # restore, never a count of anything -- exclude it explicitly.
        if (isinstance(expected, ast.Constant)
                and isinstance(expected.value, int)
                and not isinstance(expected.value, bool)):
            out[label.value] = expected.value
        else:
            unresolved.append(label.value)
    # The PG_LANDMARKS loop builds its Checks from a dict, so its labels
    # arrive here unresolved. Fold the dict in explicitly rather than
    # dropping them.
    import importlib.util
    import sys
    spec = importlib.util.spec_from_file_location("_vi_harvest", VERIFY)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_vi_harvest"] = mod
    spec.loader.exec_module(mod)
    for name, value in mod.PG_LANDMARKS.items():
        out[f"postgres {name}"] = value
    return out


def _resolve_db(var: str) -> str:
    """Turn `PGDB` into `parkavedb` by reading the script's own default.

    Keeping the shell variable name as the label would hide a changed default:
    `PGDB="${CCF_PGDATABASE:-somethingelse}"` would still read `PGDB` and
    still find a registered measurement pointing at the old database.
    """
    text = (RESTORE_DIR / "restore_postgres.sh").read_text()
    m = re.search(rf'^{var}="\$\{{[A-Z_]+:-([^}}]+)\}}"', text, re.M)
    assert m, f"no default assignment found for ${var} in restore_postgres.sh"
    return m.group(1)


#: One pattern per assertion shape the restore scripts actually use. A shape
#: that stops matching yields ZERO rows for that file, which
#: `test_every_restore_script_yields_expectations` turns into a failure --
#: otherwise a renamed helper would quietly empty the harvest and every
#: check below would pass by measuring nothing.
RESTORE_PATTERNS = {
    "restore_postgres.sh": [
        (re.compile(r'^assert_table_count\s+"?\$?\{?(\w+)\}?"?\s+(\S+)\s+(\d+)',
                    re.M),
         lambda m: (f"postgres {_resolve_db(m.group(1))}.{m.group(2)} "
                    f"base tables", int(m.group(3)))),
    ],
    "restore_mongo.sh": [
        (re.compile(r'^restore_and_verify\s+(\S+)\s+\S+\s+(\d+)\s+(\d+)', re.M),
         lambda m: [(f"mongo {m.group(1)} collections", int(m.group(2))),
                    (f"mongo {m.group(1)} documents", int(m.group(3)))]),
    ],
    "restore_fluree.sh": [
        (re.compile(r'^assert_eq\s+"([^"]+)"\s+(\d+)', re.M),
         lambda m: (m.group(1), int(m.group(2)))),
    ],
    "restore_sqlite.sh": [
        (re.compile(r'^expected=(\d+)', re.M),
         lambda m: ("sqlite departmental tables", int(m.group(1)))),
    ],
}


def harvest_restore_scripts() -> dict[str, dict[str, int]]:
    per_file: dict[str, dict[str, int]] = {}
    for fname, patterns in RESTORE_PATTERNS.items():
        found: dict[str, int] = {}
        text = (RESTORE_DIR / fname).read_text()
        for rx, build in patterns:
            for m in rx.finditer(text):
                pairs = build(m)
                for label, value in (pairs if isinstance(pairs, list) else [pairs]):
                    found[label] = value
        per_file[fname] = found
    return per_file


# --------------------------------------------------------------------------
# Measure — how each expectation is checked against the live estate
# --------------------------------------------------------------------------

def _pg_scalar(sql: str, dbname: str | None = None) -> int:
    from ccf.config import PG, pg_connect
    if dbname is None:
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchone()[0]
    import psycopg
    dsn = (f"host={PG['host']} port={PG['port']} dbname={dbname} "
           f"user={os.getenv('CO_LENDER_PG_USER', 'colender')} "
           f"password={os.getenv('CO_LENDER_PG_PASSWORD')}")
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchone()[0]


def _base_tables(schema: str, dbname: str | None = None) -> int:
    return _pg_scalar(
        "SELECT count(*) FROM information_schema.tables "
        f"WHERE table_schema = '{schema}' AND table_type = 'BASE TABLE'",
        dbname)


def _mongo(db: str, peer: bool = False) -> tuple[int, int]:
    from pymongo import MongoClient
    uri = (os.environ["CO_LENDER_MONGO_URI"] if peer
           else os.getenv("MONGO_URI", "mongodb://192.168.4.76:27017"))
    cli = MongoClient(uri, serverSelectionTimeoutMS=8000)
    try:
        # Named db only. db1's MongoDB also carries an unrelated live
        # system's millions of documents; this never lists databases.
        d = cli[db]
        names = sorted(d.list_collection_names())
        return len(names), sum(d[n].count_documents({}) for n in names)
    finally:
        cli.close()


#: `bofa/syndicate` lives on the CO-LENDER fabric, not the primary. Asking
#: the primary for it returns "no such ledger", not a wrong number -- which
#: reads as a broken peer rather than as a query pointed at the wrong host.
#: This is exactly the "every default in the repo points at the primary"
#: trap the portable bundle exists to make concrete.
PEER_LEDGERS = {"bofa/syndicate"}


def _fluree_url(ledger: str) -> str:
    from ccf.config import CO_LENDER_FLUREE_URL, FLUREE_URL
    if ledger in PEER_LEDGERS:
        assert CO_LENDER_FLUREE_URL, (
            "CO_LENDER_FLUREE_URL is unset, so the peer fabric cannot be "
            "measured. It is a SECOND Fluree instance; the primary does not "
            "hold this ledger.")
        return CO_LENDER_FLUREE_URL
    return FLUREE_URL


def _fluree_t(ledger: str) -> int:
    import requests
    url = _fluree_url(ledger)
    rows = requests.get(f"{url}/v1/fluree/ledgers", timeout=20).json()
    names = {r["name"]: r["t"] for r in rows}
    assert ledger in names, (
        f"ledger {ledger!r} not on {url} -- it holds {sorted(names)}")
    return names[ledger]


def _fluree_triples(ledger: str) -> int:
    import requests
    r = requests.post(
        f"{_fluree_url(ledger)}/v1/fluree/query",
        headers={"Content-Type": "application/sparql-query"},
        data=f"SELECT (COUNT(*) AS ?n) FROM <{ledger}> "
             "WHERE {{ ?s ?p ?o }}".replace("{{", "{").replace("}}", "}").encode(),
        timeout=180)
    r.raise_for_status()
    return int(r.json()["results"]["bindings"][0]["n"]["value"])


def _sqlite_tables() -> int:
    from ccf.config import SQLITE_PATH
    con = sqlite3.connect(SQLITE_PATH)
    try:
        return con.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    finally:
        con.close()


#: label -> how to measure it live, or INVARIANT for a value that is a
#: property of the RESTORE rather than of the estate (a version floor, an
#: absence that must hold no matter what the estate contains).
INVARIANT = "invariant"

MEASURE = {
    # --- Postgres ---------------------------------------------------------
    "postgres ccf_v2 base tables": lambda: _base_tables("ccf_v2"),
    "postgres parkavedb.ccf_v2 base tables": lambda: _base_tables("ccf_v2"),
    "postgres public (v1) base tables": lambda: _base_tables("public"),
    "postgres parkavedb.public base tables": lambda: _base_tables("public"),
    "postgres legal_entity rows":
        lambda: _pg_scalar("SELECT count(*) FROM ccf_v2.legal_entity"),
    "postgres crosswalk rows":
        lambda: _pg_scalar("SELECT count(*) FROM ccf_v2.crosswalk"),
    "postgres internal_client rows":
        lambda: _pg_scalar("SELECT count(*) FROM ccf_v2.internal_client"),
    "postgres principal_jurisdiction grants":
        lambda: _pg_scalar("SELECT count(*) FROM ccf_v2.principal_jurisdiction"),
    "postgres peer colender base tables":
        lambda: _base_tables("colender", os.getenv("CO_LENDER_PG_DB",
                                                   "bofa_syndicated")),
    "postgres bofa_syndicated.colender base tables":
        lambda: _base_tables("colender", os.getenv("CO_LENDER_PG_DB",
                                                   "bofa_syndicated")),
    "postgres server major version": INVARIANT,
    "crosswalk LEIs with no legal_entity": INVARIANT,
    "crosswalk rows resolving to nothing": INVARIANT,
    "internal clients no crosswalk row reaches": INVARIANT,
    # --- MongoDB ----------------------------------------------------------
    "mongo fibo_v2 collections": lambda: _mongo("fibo_v2")[0],
    "mongo fibo_v2 documents": lambda: _mongo("fibo_v2")[1],
    "mongo fibo (v1) collections": lambda: _mongo("fibo")[0],
    "mongo fibo (v1) documents": lambda: _mongo("fibo")[1],
    "mongo fibo collections": lambda: _mongo("fibo")[0],
    "mongo fibo documents": lambda: _mongo("fibo")[1],
    "mongo bofa_syndicated collections": lambda: _mongo("bofa_syndicated", True)[0],
    "mongo bofa_syndicated documents": lambda: _mongo("bofa_syndicated", True)[1],
    # --- Fluree -----------------------------------------------------------
    "fluree fibo-v2 ledger t": lambda: _fluree_t("fibo-v2"),
    "fluree fibo-v2 t": lambda: _fluree_t("fibo-v2"),
    "fluree fibo (v1) ledger t": lambda: _fluree_t("fibo"),
    "fluree fibo (v1) t": lambda: _fluree_t("fibo"),
    "fluree bofa/syndicate ledger t": lambda: _fluree_t("bofa/syndicate"),
    "fluree bofa/syndicate t": lambda: _fluree_t("bofa/syndicate"),
    "fluree fibo-v2 triples": lambda: _fluree_triples("fibo-v2"),
    "fluree bofa/syndicate triples": lambda: _fluree_triples("bofa/syndicate"),
    # --- SQLite / Neo4j ---------------------------------------------------
    "sqlite departmental tables": lambda: _sqlite_tables(),
    "neo4j v1 nodes": INVARIANT,
    "neo4j v1 relationships": INVARIANT,
    "neo4j restore scaffolding removed": INVARIANT,
}


def all_shipped() -> dict[str, int]:
    out = dict(harvest_verify_install())
    for found in harvest_restore_scripts().values():
        out.update(found)
    return out


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------

def test_the_harvest_is_not_empty():
    """A parser that silently matches nothing makes every check below pass."""
    assert len(harvest_verify_install()) >= 15


@pytest.mark.parametrize("fname", sorted(RESTORE_PATTERNS))
def test_every_restore_script_yields_expectations(fname):
    """A renamed helper must fail here, not empty the harvest in silence."""
    assert harvest_restore_scripts()[fname], (
        f"{fname} yielded no expectations -- its assertion shape changed and "
        f"RESTORE_PATTERNS no longer matches it. Nothing in this file is "
        f"being checked.")


def test_every_shipped_expectation_is_registered():
    """A number nobody extracted is a number nobody can find stale."""
    missing = sorted(set(all_shipped()) - set(MEASURE))
    assert not missing, (
        f"shipped expectations with no live measurement: {missing}. Add each "
        f"to MEASURE (or mark it INVARIANT if it is a property of the restore "
        f"rather than of the estate).")


def test_the_two_shipped_sources_agree_with_each_other():
    """verify_install.py and the restore scripts must not drift apart.

    This is the 2026-09-01 defect exactly: PG_LANDMARKS said 115 while
    restore_postgres.sh still said 113, and each was internally consistent.
    """
    vi = harvest_verify_install()
    disagreements = []
    for found in harvest_restore_scripts().values():
        for label, value in found.items():
            twin = {
                "postgres parkavedb.ccf_v2 base tables": "postgres ccf_v2 base tables",
                "postgres parkavedb.public base tables": "postgres public (v1) base tables",
                "postgres bofa_syndicated.colender base tables": "postgres peer colender base tables",
                "mongo fibo collections": "mongo fibo (v1) collections",
                "mongo fibo documents": "mongo fibo (v1) documents",
                "fluree fibo-v2 t": "fluree fibo-v2 ledger t",
                "fluree fibo (v1) t": "fluree fibo (v1) ledger t",
                "fluree bofa/syndicate t": "fluree bofa/syndicate ledger t",
            }.get(label, label)
            if twin in vi and vi[twin] != value:
                disagreements.append(
                    f"{label}: restore script says {value}, "
                    f"verify_install says {vi[twin]}")
    assert not disagreements, disagreements


@pytest.mark.parametrize("label", sorted(
    l for l in all_shipped() if MEASURE.get(l) not in (None, INVARIANT)))
def test_shipped_expectation_matches_the_live_estate(label):
    expected = all_shipped()[label]
    live = MEASURE[label]()
    assert live == expected, (
        f"{label}: the bundle ships {expected}, the live estate has {live}. "
        f"Update it in portable/verify_install.py AND portable/restore/, then "
        f"REBUILD the bundle -- the deployed one no longer describes this "
        f"estate.")


# --------------------------------------------------------------------------
# Fluree `t` is deliberately NOT a shipped constant
# --------------------------------------------------------------------------
#
# Ruled 2026-09-01. `t` counts COMMITS, and commits accumulate from work that
# changes no data: the validator suite re-runs `loaders/load_fluree_wave17.py`
# twice per run to prove that loader is re-runnable, adding exactly 46 commits
# per run (measured three times) while the triple count holds at 87,162. So a
# hardcoded `t` goes stale on activity that changed nothing, and no rebuild
# can outrun it -- it was stale again before the bundle finished building.
#
# The expected `t` now comes from MANIFEST.json, recorded at export time. That
# is a WEAKER claim, honestly labelled: it proves the replay carried every
# commit the archive held, not that the archive was complete. The triple
# counts stay hardcoded, because they are stable, and they are what still
# checks the archive's content independently.
#
# These two tests exist so nobody quietly types a number back in.

LEDGERS = ("fibo-v2", "fibo", "bofa/syndicate")


def _hardcoded_t_offenders(verify_src: str, restore_src: str) -> list[str]:
    bad = []
    for m in re.finditer(r'Check\(\s*"(fluree [^"]*?ledger t)"\s*,\s*(\d+)',
                         verify_src):
        bad.append(f"verify_install.py hardcodes {m.group(1)} = {m.group(2)}")
    for m in re.finditer(r'^assert_eq\s+"(fluree [^"]*\bt)"\s+(\d+)',
                         restore_src, re.M):
        bad.append(f"restore_fluree.sh hardcodes {m.group(1)} = {m.group(2)}")
    return bad


def test_ledger_t_is_read_from_the_manifest_not_hardcoded():
    verify_src = VERIFY.read_text()
    restore_src = (RESTORE_DIR / "restore_fluree.sh").read_text()
    assert not _hardcoded_t_offenders(verify_src, restore_src), (
        _hardcoded_t_offenders(verify_src, restore_src))
    # ...and confirm they actually reach the manifest, so deleting the check
    # altogether cannot pass this test by absence.
    assert "MANIFEST_LEDGER_T" in verify_src
    assert "manifest_t" in restore_src
    for ledger in LEDGERS:
        assert ledger in restore_src, f"{ledger} no longer restored at all"


def test_control_the_hardcoded_t_detector_can_actually_fire():
    """A detector that has never seen its target is a detector on paper."""
    offenders = _hardcoded_t_offenders(
        'checks.append(Check("fluree fibo-v2 ledger t", 5112, t.get("x")))',
        'assert_eq "fluree fibo-v2 t"  5112  "$(found_t fibo-v2)"\n')
    assert len(offenders) == 2, offenders
    assert "verify_install.py" in offenders[0]
    assert "restore_fluree.sh" in offenders[1]
