# /// script
# requires-python = ">=3.11"
# dependencies = ["psycopg[binary]", "pymongo", "neo4j", "requests"]
# ///
"""Confirm a restored ccf_dataprep estate is complete and joined.

Run:  uv run --no-project verify_install.py
 or:  python3 -m venv /tmp/ccfv
      /tmp/ccfv/bin/pip install 'psycopg[binary]' pymongo neo4j requests
      /tmp/ccfv/bin/python verify_install.py

The venv form matters, not just a bare `pip install`: both Ubuntu 24.04 and
Homebrew Python on macOS mark their system Python "externally managed"
(PEP 668) and refuse a bare `pip install` outright. A venv sidesteps that
on both platforms with one identical command; a bare `pip`/`pip3` split by
OS would not be.

--no-project matters: bare `uv run` inside any directory that happens to
contain a pyproject.toml (e.g. a repo checkout) adopts THAT project's
environment instead of resolving this script's own inline PEP 723
dependencies, and fails with ImportError on a perfectly good restore.

Exit 0 every check passed; 1 a check failed OR zero checks ran at all
(e.g. every store was skipped -- a verifier that verified nothing must never
exit 0); 2 a store could not be reached.

This asserts LANDMARK VALUES, not liveness. A checker that passes because it
looked at nothing is the defect this estate has recorded most often, so every
check prints the value it found beside the value it required. The same
discipline applies to failure: every individual query is wrapped so an
exception (a missing/renamed table, a corrupt file -- exactly what a broken
restore looks like) becomes `found=None`, a FAIL, on THAT check, rather than
an uncaught traceback that aborts the run before the remaining stores get a
chance to report. `run_all` additionally wraps each store's whole check
function as a last-resort net against a genuinely unanticipated bug.

This file ships standalone inside the bundle and must run on a laptop with no
repo checkout present. It imports nothing from `ccf.*` or anywhere else in
this repository -- only the four PEP 723 dependencies above, plus stdlib.

CCF_SKIP_STORES (comma-separated, case-insensitive: fluree, postgres, mongo,
sqlite, neo4j) lets a rehearsal legitimately skip a store it cannot restore
(e.g. the only Neo4j reachable from the build host is the live source graph,
and its own restore Cypher opens with `MATCH (n) DETACH DELETE n`). A skip
still exits 0 on an otherwise-clean run, but the summary must never say
"Estate verified" when something went unchecked -- it says how many stores
were skipped and names them. Skipping EVERY store exits 1, not 0: nothing
was verified. An unrecognized store name in CCF_SKIP_STORES skips nothing
(never guesses) but is printed as a warning naming the valid store list,
rather than silently doing nothing.
"""
from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import sys
from dataclasses import dataclass, field

#: Each ledger's commit count AS EXPORTED, read from the bundle's own
#: MANIFEST.json rather than typed in below with the other landmarks.
#:
#: Every other expectation in this file is deliberately independent of the
#: artifact it checks -- see PG_LANDMARKS. `t` cannot be, and pretending
#: otherwise was worse than admitting it: `t` counts COMMITS, and commits
#: accumulate from work that changes no data. This repo's validator suite
#: re-runs `loaders/load_fluree_wave17.py` twice per run to prove that loader
#: is safe to re-run; measured three times on 2026-09-01, that adds exactly
#: 46 commits per run while the triple count holds at 88,072. A hardcoded t
#: went stale between writing it and running the suite once.
#:
#: So the ledger-t checks below prove REPLAY COMPLETENESS -- every commit the
#: archive held arrived -- and the triple counts, which stay hardcoded
#: because they are stable, remain the independent check on the archive's
#: content. Saying which check proves which is the point; one number quietly
#: doing neither job was the failure.
def _manifest_ledger_t() -> dict[str, int]:
    path = pathlib.Path(__file__).resolve().parent / "MANIFEST.json"
    try:
        table = json.loads(path.read_text()).get("ledger_t") or {}
    except Exception:
        return {}
    return {k: int(v) for k, v in table.items()}


MANIFEST_LEDGER_T = _manifest_ledger_t()

FLUREE_URL = os.getenv("CCF_FLUREE_URL", "http://127.0.0.1:8090")
PG_DSN = os.getenv("CCF_PG_DSN", "dbname=parkavedb")
PEER_PG_DSN = os.getenv("CCF_PEER_PG_DSN", "dbname=bofa_syndicated")
MONGO_URI = os.getenv("CCF_MONGO_URI", "mongodb://127.0.0.1:27017")
SQLITE_PATH = os.getenv("CCF_SQLITE_PATH",
                        os.path.expanduser("~/ccf-data/departmental.sqlite"))
NEO4J_URI = os.getenv("CCF_NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_AUTH = (os.getenv("CCF_NEO4J_USER", "neo4j"),
              os.getenv("CCF_NEO4J_PASSWORD", ""))


#: Postgres landmark row counts, asserted against a RESTORED estate.
#:
#: Deliberately hardcoded rather than derived from the dump. A verifier that
#: reads its expectations out of the artifact it is verifying can only prove
#: the restore matched the dump -- it cannot see a DUMP that silently lost
#: rows, which is the more expensive failure. These are independent knowledge
#: and that is the point ("asserts LANDMARK VALUES, not liveness", above).
#:
#: The cost is that they go stale whenever the estate changes, and they have
#: twice: `ccf_v2 base tables` was 113 before Wave 20 added two tables, and
#: `crosswalk rows` was 53 before Wave 20 added 30 no-LEI clients. Staleness
#: used to surface on a laptop mid-restore; `validators/test_bundle_landmarks.py`
#: now fails in the repo suite instead, BEFORE a rebuild can ship it.
#:
#: 2026-10-10: `public (v1) base tables` 3 -> 2, REVERSING the 2026-09-10
#: change below. `companies` was never v1: it is ccf-sdk's s1-00 example table
#: (10 fabricated rows), written into the live `public` schema by an unguarded
#: ccf-sdk test run on 2026-09-08 and dropped today; a copy is kept at
#: docs/evidence/2026-10-10-public-companies-from-ccf-sdk-s1-00.sql. The
#: original 2 was RIGHT. The failure it raised from 09-08 on was this guard
#: catching the contamination, and raising the landmark to 3 taught it to
#: accept it. See known-issues.md 63.2.
#:
#: 2026-10-09: `fibo-v2 triples` 88,325 -> 89,148. 823 missing party-chain
#: types (Party, Agent, LegalPerson) asserted on 315 entities -- known-issues
#: 62. The same rebuild is the first bundle carrying the ccf_v2 keys that
#: ccf-sdk's fixtures had stripped before the 09-13 dump (63): row counts are
#: unchanged, so no Postgres landmark moves, but a restore of the old bundle
#: had no primary keys on eight tables.
#:
#: 2026-09-13, Wave 22: `fibo-v2 triples` 88,072 -> 88,325. Anchor identity
#: remediation -- 396 collided triples retracted, 44 correctly-keyed nodes
#: written, plus 44 types and 170 `declaredAt`. See known-issues.md 61.4.
#:
#: 2026-09-10, Wave 21: `ccf_v2 base tables` 115 -> 116 (ucc_debtor_crosswalk)
#: and `fibo-v2 triples` 87,162 -> 88,072 (+910 UCC filing triples). Separately,
#: `public (v1) base tables` moved 2 -> 3 — that one was never right: the v1
#: schema holds `companies`, `entities` and `relationships`, and the bundle
#: dumps the whole schema, so a restore has always produced 3. The 2 was
#: carried forward from a hardcoded literal and had been failing since the
#: guard was introduced. [WRONG -- corrected 2026-10-10 above: `companies`
#: was ccf-sdk's, and the failure was the guard working.]
PG_LANDMARKS: dict[str, int] = {
    "ccf_v2 base tables": 116,
    "public (v1) base tables": 2,
    "legal_entity rows": 156,
    "crosswalk rows": 83,
    "internal_client rows": 30,
    "principal_jurisdiction grants": 17,
}


@dataclass
class Check:
    name: str
    required: object
    found: object
    detail: str = ""
    unreachable: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        # found is None means "could not read it" -- that is a FAILURE, never
        # a pass and never silently skipped. Do not special-case it away.
        return self.found is not None and self.found == self.required

    def render(self) -> str:
        status = "PASS" if self.ok else "FAIL"
        got = "unreadable" if self.found is None else self.found
        line = f"  [{status}] {self.name:<44} required {self.required}, got {got}"
        return line + (f"  ({self.detail})" if self.detail else "")


def exit_code(checks: list[Check], unreachable: list | None = None) -> int:
    # A store that could not be reached is an install problem, not a data
    # problem -- report it as exit 2, never folded into the exit-1 data
    # failures, or the reader is sent to the wrong place.
    if unreachable:
        return 2
    # Zero checks ran -- e.g. CCF_SKIP_STORES named every store, or some
    # other reason run_all produced nothing -- means nothing was verified.
    # any() over an empty list is False, which would otherwise read this as
    # a clean pass. A verifier that verified nothing must never exit 0.
    if not checks:
        return 1
    return 1 if any(not c.ok for c in checks) else 0


# --- store name normalization for CCF_SKIP_STORES --------------------------

STORE_ALIASES = {
    "fluree": "fluree",
    "postgres": "postgres", "postgresql": "postgres", "pg": "postgres",
    "mongo": "mongo", "mongodb": "mongo",
    "sqlite": "sqlite", "sqlite3": "sqlite",
    "neo4j": "neo4j",
}

#: The five canonical store names CCF_SKIP_STORES recognizes -- every value
#: STORE_ALIASES can canonicalize to. Anything else is an unrecognized token
#: (see parse_skip_stores / run_all): it skips nothing, and that fact is
#: surfaced as a warning rather than swallowed silently.
KNOWN_STORES = frozenset(STORE_ALIASES.values())


def parse_skip_stores(raw: str | None) -> frozenset[str]:
    """Parse CCF_SKIP_STORES into canonical store tokens.

    Blank/None yields an empty set. Tokens are case-insensitive and
    whitespace-trimmed; recognized aliases (mongodb -> mongo, postgresql/pg ->
    postgres, sqlite3 -> sqlite) are canonicalized. An unrecognized token is
    kept as-is rather than raising -- it will simply match no store below, so
    a typo skips nothing instead of skipping something silently.
    """
    if not raw:
        return frozenset()
    tokens = (tok.strip().lower() for tok in raw.split(","))
    return frozenset(STORE_ALIASES.get(tok, tok) for tok in tokens if tok)


def _sparql(ledger: str, query: str):
    import requests
    r = requests.post(f"{FLUREE_URL}/v1/fluree/query",
                      headers={"Content-Type": "application/sparql-query"},
                      data=query.encode(), timeout=120)
    r.raise_for_status()
    return r.json()["results"]["bindings"]


def check_fluree(checks, unreachable):
    import requests
    try:
        led = requests.get(f"{FLUREE_URL}/v1/fluree/ledgers", timeout=20).json()
    except Exception as e:
        unreachable.append(f"fluree ({e.__class__.__name__})")
        return
    # A reachable server can still return a malformed/unexpected ledger
    # listing (wrong shape, missing keys). That is a DATA problem, not a
    # connection problem -- render every ledger-t check as an unreadable
    # FAIL rather than letting a KeyError/TypeError here abort the run.
    try:
        t = {row["name"]: row["t"] for row in led}
    except Exception:
        t = {}
    # One clear failure beats three cryptic "required None" lines. A bundle
    # built before ledger_t existed is a REBUILD, not a mystery.
    if not MANIFEST_LEDGER_T:
        checks.append(Check(
            "bundle MANIFEST.json records ledger_t", True, False,
            "this bundle predates manifest-recorded commit counts -- rebuild it"))
    checks.append(Check("fluree fibo-v2 ledger t",
                        MANIFEST_LEDGER_T.get("fibo-v2"), t.get("fibo-v2"),
                        "expected from MANIFEST.json, not hardcoded"))
    checks.append(Check("fluree fibo (v1) ledger t",
                        MANIFEST_LEDGER_T.get("fibo"), t.get("fibo")))
    checks.append(Check("fluree bofa/syndicate ledger t",
                        MANIFEST_LEDGER_T.get("bofa/syndicate"),
                        t.get("bofa/syndicate")))
    try:
        n = int(_sparql("fibo-v2",
                        "SELECT (COUNT(*) AS ?n) FROM <fibo-v2> "
                        "WHERE { ?s ?p ?o }")[0]["n"]["value"])
    except Exception:
        n = None
    checks.append(Check("fluree fibo-v2 triples", 89148, n))

    # The peer ledger's `t` is commit-chain metadata: a peer that replayed
    # its commits but served no content could still report t=16. The triple
    # count is the only check on the peer fabric's actual graph content, and
    # the co-lender demonstration is the whole reason a second fabric
    # exists. All three ledgers live on one Fluree server on the laptop, so
    # this goes through the same CCF_FLUREE_URL as fibo-v2 -- no separate
    # peer endpoint.
    try:
        n_peer = int(_sparql("bofa/syndicate",
                            "SELECT (COUNT(*) AS ?n) FROM <bofa/syndicate> "
                            "WHERE { ?s ?p ?o }")[0]["n"]["value"])
    except Exception:
        n_peer = None
    checks.append(Check("fluree bofa/syndicate triples", 10, n_peer))


def _pg_scalar(conn, cur, sql):
    """Run a single-value query; return the scalar, or None if it raised.

    A missing/renamed table or a corrupt restore is exactly the input this
    verifier exists to catch -- it must render as an unreadable FAIL on
    THAT check, never crash the whole run before the remaining stores get a
    chance to report. Rolling back after a caught failure resets the
    connection's transaction state so one bad query does not poison every
    query that runs after it on the same connection.
    """
    try:
        cur.execute(sql)
        return cur.fetchone()[0]
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return None


def check_postgres(checks, unreachable):
    import psycopg
    try:
        conn = psycopg.connect(PG_DSN, connect_timeout=10)
    except Exception as e:
        unreachable.append(f"postgres ({e.__class__.__name__})")
        return
    with conn, conn.cursor() as cur:
        ver_raw = _pg_scalar(conn, cur, "select current_setting('server_version')")
        ver = ver_raw.split(".")[0] if ver_raw is not None else None
        checks.append(Check("postgres server major version", "16", ver,
                            "pg_restore needs 16 for these dumps"))
        # CORRECTED: information_schema.tables without a table_type filter
        # also counts views -- ccf_v2 carries 2, so the unfiltered answer is
        # 115, not 113. Filter to base tables explicitly, both schemas.
        checks.append(Check(
            "postgres ccf_v2 base tables", PG_LANDMARKS["ccf_v2 base tables"],
            _pg_scalar(conn, cur,
                      "select count(*) from information_schema.tables "
                      "where table_schema='ccf_v2' and table_type='BASE TABLE'")))
        checks.append(Check(
            "postgres public (v1) base tables",
            PG_LANDMARKS["public (v1) base tables"],
            _pg_scalar(conn, cur,
                      "select count(*) from information_schema.tables "
                      "where table_schema='public' and table_type='BASE TABLE'")))
        checks.append(Check(
            "postgres legal_entity rows", PG_LANDMARKS["legal_entity rows"],
            _pg_scalar(conn, cur, "select count(*) from ccf_v2.legal_entity")))
        # The correlation key's row count. A partial restore of ccf_v2 can
        # still show every base table (all created, few rows loaded) -- a
        # table count alone cannot see that. Count the crosswalk directly.
        checks.append(Check(
            "postgres crosswalk rows", PG_LANDMARKS["crosswalk rows"],
            _pg_scalar(conn, cur, "select count(*) from ccf_v2.crosswalk"),
            "the correlation key row count"))
        # Wave 20's two tables get their own landmarks. Without them a restore
        # that created both and loaded neither would pass the base-table count
        # and lose the entire no-LEI population silently -- the population
        # whose ABSENCE is the thing rung 1 exists to demonstrate.
        checks.append(Check(
            "postgres internal_client rows",
            PG_LANDMARKS["internal_client rows"],
            _pg_scalar(conn, cur, "select count(*) from ccf_v2.internal_client"),
            "no-LEI clients; a restore losing these loses §D's whole point"))
        checks.append(Check(
            "postgres principal_jurisdiction grants",
            PG_LANDMARKS["principal_jurisdiction grants"],
            _pg_scalar(conn, cur,
                       "select count(*) from ccf_v2.principal_jurisdiction"),
            "entitlement grants; without them the Policy Operator is a no-op"))
        # WIDENED for Wave 20. This was a bare
        # `left join legal_entity on e.lei = c.lei where e.lei is null`, which
        # counts every legitimate no-LEI internal client as an orphan -- it
        # would have reported 30 failures on the first rebuilt bundle, and the
        # restore would have looked broken when it was correct.
        #
        # The RESOLUTION TARGET is widened, not the new rows exempted, and the
        # two halves stay strict: a row WITH an LEI must still match a
        # `legal_entity`, a row WITHOUT one must match an `internal_client`,
        # and a NULL-lei row nothing backs is still an orphan. Mirrors the
        # same correction made to validators/conditions.py.
        checks.append(Check(
            "crosswalk rows resolving to nothing", 0,
            _pg_scalar(conn, cur, """
                select count(*) from ccf_v2.crosswalk c
                left join ccf_v2.legal_entity e on e.lei = c.lei
                left join ccf_v2.internal_client i
                       on i.internal_client_id = c.internal_client_id
                where (c.lei is not null and e.lei is null)
                   or (c.lei is null and i.internal_client_id is null)
            """),
            "the correlation key must resolve — to a legal_entity if it "
            "carries an LEI, to an internal_client if it does not"))
        checks.append(Check(
            "internal clients no crosswalk row reaches", 0,
            _pg_scalar(conn, cur, """
                select count(*) from ccf_v2.internal_client i
                left join ccf_v2.crosswalk c
                       on c.internal_client_id = i.internal_client_id
                where c.internal_client_id is null
            """),
            "the other direction: a client the bank side cannot key"))

    # CORRECTED: the co-lender peer was never connected to by anything in
    # this file, so a completely broken peer restore verified as nothing at
    # all. Connect separately and assert its own schema.
    try:
        peer = psycopg.connect(PEER_PG_DSN, connect_timeout=10)
    except Exception as e:
        unreachable.append(f"postgres-peer ({e.__class__.__name__})")
        return
    with peer, peer.cursor() as cur:
        checks.append(Check(
            "postgres peer colender base tables", 2,
            _pg_scalar(peer, cur,
                      "select count(*) from information_schema.tables "
                      "where table_schema='colender' and table_type='BASE TABLE'"),
            "makes the fabric boundary concrete"))


def _mongo_collections(db):
    """List a named db's collections, or None if the call raised.

    A reachable Mongo that has lost/renamed a database's collections (a
    broken restore) must render as an unreadable FAIL here, not crash the
    whole run before the remaining stores get checked.
    """
    try:
        return sorted(db.list_collection_names())
    except Exception:
        return None


def _mongo_doc_total(db, names):
    """Sum count_documents() across `names`, or None if listing failed or
    any count raised."""
    if names is None:
        return None
    try:
        return sum(db[c].count_documents({}) for c in names)
    except Exception:
        return None


def check_mongo(checks, unreachable):
    from pymongo import MongoClient
    try:
        cli = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
        cli.admin.command("ping")
    except Exception as e:
        unreachable.append(f"mongodb ({e.__class__.__name__})")
        return
    # Named explicitly. This file never lists databases -- db1's MongoDB
    # also carries an unrelated live system's ~7M documents.
    v2 = cli["fibo_v2"]
    v2_names = _mongo_collections(v2)
    checks.append(Check("mongo fibo_v2 collections", 6,
                        None if v2_names is None else len(v2_names),
                        ", ".join(v2_names) if v2_names else ""))
    checks.append(Check("mongo fibo_v2 documents", 38238,
                        _mongo_doc_total(v2, v2_names)))
    v1 = cli["fibo"]
    v1_names = _mongo_collections(v1)
    checks.append(Check("mongo fibo (v1) collections", 2,
                        None if v1_names is None else len(v1_names),
                        ", ".join(v1_names) if v1_names else ""))
    checks.append(Check("mongo fibo (v1) documents", 30,
                        _mongo_doc_total(v1, v1_names)))


def check_sqlite(checks, unreachable):
    if not os.path.exists(SQLITE_PATH):
        unreachable.append(f"sqlite (no file at {SQLITE_PATH})")
        return
    # A present-but-corrupt file (truncated, not a database, mid-copy) is
    # precisely what a broken restore looks like -- that must render as an
    # unreadable FAIL on this check, not crash the run.
    n = None
    try:
        con = sqlite3.connect(SQLITE_PATH)
        try:
            n = con.execute("select count(*) from sqlite_master "
                            "where type='table'").fetchone()[0]
        finally:
            con.close()
    except Exception:
        n = None
    # CORRECTED: measured live at 8 tables (_schema_meta, covenant_tracker,
    # large_exposure_limit_workbook, prospect_note, restricted_list,
    # risk_limit_workbook, sar_classification, syndicate_desk_tracker), not
    # the 5 both the original brief and CLAUDE.md still say.
    checks.append(Check("sqlite departmental tables", 8, n))


def _neo4j_scalar(session, query):
    """Run a single-value Cypher query; return its scalar, or None if it
    raised. A Neo4j that connects fine but whose content query fails (a
    missing label, a broken restore) must render as an unreadable FAIL on
    THAT check -- not get reported as 'could not reach', which sends the
    reader to a connectivity problem that isn't the one they have.
    """
    try:
        return session.run(query).single()["c"]
    except Exception:
        return None


def check_neo4j(checks, unreachable):
    from neo4j import GraphDatabase
    try:
        d = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
        s = d.session()
    except Exception as e:
        unreachable.append(f"neo4j ({e.__class__.__name__})")
        return
    try:
        nodes = _neo4j_scalar(s, "MATCH (n) RETURN count(n) AS c")
        rels = _neo4j_scalar(s, "MATCH ()-[r]->() RETURN count(r) AS c")
        # The restore Cypher's own final line strips the `_B1`
        # scaffolding label. Node/relationship counts alone cannot see a
        # replay interrupted just before that line runs -- they would
        # already read 14/16 on a partial, scaffolding-contaminated
        # graph. Count remaining `_B1` nodes directly; it must be zero.
        scaffold = _neo4j_scalar(s, "MATCH (n:`_B1`) RETURN count(n) AS c")
    finally:
        try:
            s.close()
        except Exception:
            pass
        try:
            d.close()
        except Exception:
            pass
    checks.append(Check("neo4j v1 nodes", 14, nodes))
    checks.append(Check("neo4j v1 relationships", 16, rels))
    checks.append(Check("neo4j restore scaffolding removed", 0, scaffold,
                        "_B1 label must not survive the replay"))


STORE_CHECKS = (
    ("fluree", check_fluree),
    ("postgres", check_postgres),
    ("mongo", check_mongo),
    ("sqlite", check_sqlite),
    ("neo4j", check_neo4j),
)


def run_all(skip: frozenset[str] | None = None):
    """Run every store's checks except those named in `skip`.

    `skip` defaults to CCF_SKIP_STORES from the environment when not passed
    explicitly (tests pass it explicitly to stay hermetic). Returns
    (checks, unreachable, skipped, unknown_skip) -- four lists, never
    conflated:
      - a skipped store contributes to neither `checks` nor `unreachable`,
        and its absence must never read as a pass;
      - `unknown_skip` names any CCF_SKIP_STORES token that matched no real
        store (a typo skips nothing, but must not do so silently either).

    Belt and braces: each store's check function is called inside its own
    try/except. Every query each of them runs is ALREADY guarded to turn a
    failure into `found=None` (a FAIL) rather than raising -- this outer
    guard is only for a genuinely unanticipated crash (a bug in this file
    itself), and its job is solely to stop that from taking down the
    remaining stores' reporting. It surfaces as its own always-failing
    Check rather than vanishing into `unreachable`, so it is never mistaken
    for either a normal data failure or a normal connection failure.
    """
    if skip is None:
        skip = parse_skip_stores(os.getenv("CCF_SKIP_STORES", ""))
    else:
        skip = frozenset(STORE_ALIASES.get(s.lower(), s.lower()) for s in skip)

    unknown_skip = sorted(skip - KNOWN_STORES)

    checks: list[Check] = []
    unreachable: list[str] = []
    skipped: list[str] = []
    for name, fn in STORE_CHECKS:
        if name in skip:
            skipped.append(name)
            continue
        try:
            fn(checks, unreachable)
        except Exception as e:
            checks.append(Check(
                f"{name} check crashed unexpectedly", "no exception",
                f"{e.__class__.__name__}: {e}",
                "a bug in verify_install.py itself, not a store finding -- "
                "please report it; other stores were still checked"))
    return checks, unreachable, skipped, unknown_skip


def render_report(checks: list[Check], unreachable: list[str],
                  skipped: list[str], unknown_skip: list[str] = ()) -> str:
    """Build the full printed report as one string, so it can be tested
    without touching a network or a filesystem."""
    lines = ["ccf_dataprep — portable estate verification", ""]
    for c in checks:
        lines.append(c.render())

    if unknown_skip:
        lines.append("")
        lines.append(
            f"  WARNING: CCF_SKIP_STORES named unrecognized store(s): "
            f"{', '.join(unknown_skip)} -- nothing was skipped for "
            f"{'it' if len(unknown_skip) == 1 else 'them'}; "
            f"{'it' if len(unknown_skip) == 1 else 'they'} ran normally. "
            f"Valid names: {', '.join(sorted(KNOWN_STORES))}.")

    if skipped:
        lines.append("")
        lines.append(f"  SKIPPED (CCF_SKIP_STORES): {', '.join(skipped)} "
                     f"-- not checked at all, not a pass.")

    if unreachable:
        lines.append("")
        lines.append("  COULD NOT REACH: " + "; ".join(unreachable))
        lines.append("  This is an install problem, not a data problem. "
                     "See INSTALL-macos.md / INSTALL-ubuntu.md.")
        return "\n".join(lines)

    if not checks:
        # Every store was skipped (or run_all otherwise produced nothing).
        # This must read as a FAILURE, not a quiet pass -- exit_code()
        # returns 1 for this same condition; the wording has to match.
        lines.append("")
        lines.append(
            "  NOTHING WAS VERIFIED: zero checks ran"
            + (f" (every requested store was skipped: {', '.join(skipped)})"
               if skipped else "")
            + ".")
        lines.append("  This is a FAILURE, not a clean pass -- a verifier "
                     "that verifies nothing must not exit 0.")
        return "\n".join(lines)

    failed = [c for c in checks if not c.ok]
    lines.append("")
    lines.append(f"  {len(checks) - len(failed)} passed, {len(failed)} failed")
    if failed:
        lines.append("  FAILED:")
        for c in failed:
            lines.append(f"    {c.name}: required {c.required}, got {c.found}")
        return "\n".join(lines)

    # A skip must never be laundered into the unqualified "Estate verified"
    # claim -- exit 0 is still correct (nothing that WAS checked failed),
    # but the wording has to say what did not get checked.
    if skipped:
        lines.append(f"  Passed with {len(skipped)} store(s) skipped: "
                     f"{', '.join(skipped)}. This is NOT a full estate "
                     f"verification.")
    else:
        lines.append("  Estate verified.")
    return "\n".join(lines)


def main() -> int:
    checks, unreachable, skipped, unknown_skip = run_all()
    print(render_report(checks, unreachable, skipped, unknown_skip))
    return exit_code(checks, unreachable)


if __name__ == "__main__":
    sys.exit(main())
