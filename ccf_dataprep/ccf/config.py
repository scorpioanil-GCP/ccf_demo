"""Connection config and namespace constants for the v2 estate.

Two jobs:

1. Resolve connection settings from .env.
2. **Refuse to touch anything that is not ours.** db1 (192.168.4.76) is a
   shared host. Its MongoDB carries `rtdetect` — ~5.5M documents of live
   pool-safety telemetry — alongside our 14-document `fibo` v1 database.
   A cleanup loop that enumerated databases and dropped non-matching ones
   would destroy it. The guards here make that impossible rather than
   merely inadvisable.

v2 loads into fresh namespaces beside v1, never over it:

    Fluree    ledger  fibo-v2      (v1 fibo:main untouched)
    Postgres  schema  ccf_v2       (v1 public.* untouched)
    MongoDB   db      fibo_v2      (v1 fibo untouched)
    SQLite    file    ./data/departmental.sqlite

Rollback is dropping one namespace per store.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent

# --- v2 namespaces ---------------------------------------------------------
# Not secrets, so they live here rather than in the shared .env. Env vars
# override for anyone who needs to point elsewhere.

# A separate LEDGER, not a branch. `fibo:main` is a name:branch alias, so
# "fibo:v2" would have been a *branch of the v1 ledger*. "fibo-v2" cannot
# interact with "fibo" at all.
FLUREE_LEDGER_V2 = os.getenv("FLUREE_LEDGER_V2", "fibo-v2")
PG_SCHEMA_V2 = os.getenv("PG_SCHEMA_V2", "ccf_v2")
MONGO_DB_V2 = os.getenv("MONGO_DB_V2", "fibo_v2")

# --- v1 namespaces — READ ONLY, never written by v2 code -------------------

FLUREE_LEDGER_V1 = os.getenv("FLUREE_LEDGER", "fibo:main")
PG_SCHEMA_V1 = "public"
MONGO_DB_V1 = os.getenv("MONGO_DB", "fibo")

# --- Connections -----------------------------------------------------------

# Fluree 4.2.4 since 2026-10-15 (cutover, docs/fluree-42-migration-design.md).
# The old 4.1.4 server on :8090 was stopped the same night (its storage stays
# at /data/fluree, unserved); nothing runs or writes there. New installs must point at the 4.2 storage-dir
# layout -- see the design doc's "--storage-path semantics changed" note.
FLUREE_URL = os.getenv("FLUREE_URL", "http://192.168.4.76:8092")
FLUREE_QUERY_ENDPOINT = f"{FLUREE_URL}/v1/fluree/query"
FLUREE_TRANSACT_ENDPOINT = f"{FLUREE_URL}/v1/fluree/transact"

PG = {
    "host": os.getenv("PGHOST", "192.168.4.76"),
    "port": os.getenv("PGPORT", "5432"),
    "dbname": os.getenv("PGDATABASE", "parkavedb"),
    "user": os.getenv("PGUSER", "parkave"),
    "password": os.getenv("PGPASSWORD"),
}

MONGO_URI = os.getenv("MONGO_URI", "mongodb://192.168.4.76:27017")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://192.168.4.76:7687")
NEO4J_AUTH = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD"))

SQLITE_PATH = REPO_ROOT / os.getenv("SQLITE_PATH", "./data/departmental.sqlite").lstrip("./")

SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "")

# --- Namespaces under FIBO / application ------------------------------------

EX = "http://example.org/fibo/"

#: The self-describing note every `ex:` extension CLASS carries in Fluree,
#: alongside `ex:isFiboTerm false`. It exists so the graph explains its own
#: invented vocabulary to a consumer holding only the graph — someone who
#: cannot tell, from an IRI under `example.org`, whether the term is a real
#: FIBO class this project failed to find or a deliberate extension.
#:
#: Defined here rather than per-loader because three loaders declare these
#: classes (Waves 5, 6, 7) and the string must be byte-identical across them:
#: it is asserted as a literal, so a reworded copy would show up in the ledger
#: as a second, competing value for the same predicate.
#:
#: Restored 2026-08-21 (Wave 11c). It had been asserted 9 times in Fluree by a
#: loader version no longer in the repo — see `validators/orphan_terms.py`.
EX_EXTENSION_SCHEMA_NOTE = (
    "application extension: no FIBO term exists for this concept. "
    "See docs/ccf_dataprep_v2.md and the fibo-iri-binding article."
)
FIBO_BASE = "https://spec.edmcouncil.org/fibo/ontology/"


# --- Guards -----------------------------------------------------------------

class ProtectedResourceError(RuntimeError):
    """Raised on any attempt to reach a datastore namespace we do not own."""


#: Databases on the shared Mongo host that v2 code must never open for write.
#: `rtdetect` is the live pool-safety system; `fibo` is the v1 dataset we are
#: deliberately preserving for comparison.
#: `_CO_LENDER_MONGO_DB` is read early so the peer's database can join this
#: denylist. Mongo's guard is a denylist plus a narrow allowlist, unlike the
#: Postgres and Fluree guards, which are allowlists and therefore already
#: refuse the peer's namespaces without any change.
_CO_LENDER_MONGO_DB = os.getenv("CO_LENDER_MONGO_DB", "colender")

PROTECTED_MONGO_DBS = frozenset(
    {"rtdetect", "rtdetect_test", "admin", "config", "local", MONGO_DB_V1,
     _CO_LENDER_MONGO_DB}
)

#: The only Mongo database v2 loaders may write to.
WRITABLE_MONGO_DBS = frozenset({MONGO_DB_V2})


def mongo_db(name: str | None = None, *, write: bool = True):
    """Return a MongoDB handle, refusing any database v2 does not own.

    Always pass an explicit name or accept the v2 default. There is
    deliberately no helper that lists databases — enumeration is how an
    unrelated system gets caught in a cleanup loop.
    """
    from pymongo import MongoClient

    name = name or MONGO_DB_V2
    if write:
        if name in PROTECTED_MONGO_DBS:
            raise ProtectedResourceError(
                f"Refusing to open '{name}' for write. It is protected: "
                f"{sorted(PROTECTED_MONGO_DBS)}. v2 writes only to "
                f"{sorted(WRITABLE_MONGO_DBS)}."
            )
        if name not in WRITABLE_MONGO_DBS:
            raise ProtectedResourceError(
                f"Refusing to open unknown database '{name}' for write. "
                f"Add it to WRITABLE_MONGO_DBS deliberately if this is intended."
            )
    return MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)[name]


def assert_v2_ledger(ledger: str) -> str:
    """Guard Fluree writes to the v2 ledger."""
    if ledger != FLUREE_LEDGER_V2:
        raise ProtectedResourceError(
            f"Refusing to transact against '{ledger}'. v2 writes only to "
            f"'{FLUREE_LEDGER_V2}'. Note Fluree is append-only: a write to "
            f"'{FLUREE_LEDGER_V1}' could not be undone."
        )
    return ledger


def assert_v2_schema(schema: str) -> str:
    """Guard Postgres DDL/DML to the v2 schema."""
    if schema != PG_SCHEMA_V2:
        raise ProtectedResourceError(
            f"Refusing to write to schema '{schema}'. v2 writes only to "
            f"'{PG_SCHEMA_V2}'."
        )
    return schema


def pg_connect(*, autocommit: bool = False):
    """Open a Postgres connection with the v2 schema first on search_path."""
    import psycopg

    conn = psycopg.connect(**PG, connect_timeout=8, autocommit=autocommit)
    with conn.cursor() as cur:
        cur.execute(f'SET search_path TO "{PG_SCHEMA_V2}", public')
    return conn


# ===========================================================================
# The co-lender fabric — `syndicated-lending-co-lender`
# ===========================================================================
#
# §C of that spec files one element as `separate instance`:
#
#     Simulated peer fabric — a second CCF instance | required to demonstrate
#     A2A | synthetic — engineered | separate instance
#
# and the article is explicit that "A2A cannot be demonstrated against one
# fabric." So there are now TWO fabrics, and the demonstration rests entirely
# on a property that is trivial to break by accident: **our queries must not be
# able to reach the peer's data except through the negotiated interface.**
#
# ## What these guards are actually protecting
#
# Not the data. A stray write to the peer's store is recoverable. What is not
# recoverable is the CLAIM — if a loader on our side can read or write the
# peer's tables, then "the co-lender's policy envelope" was never enforced by
# anything, and every federation result the demonstration produces is an
# artifact of a shared connection rather than a negotiated one. The failure is
# silent and it invalidates the product's entire point.
#
# ## The local guards already refuse the peer, for free
#
# `assert_v2_schema` and `ccf.fluree._guard` are ALLOWLISTS — they accept
# exactly `ccf_v2` and `fibo-v2` and refuse everything else. So a local loader
# already cannot write to a co-lender schema or ledger, and that needed no
# change. Only `PROTECTED_MONGO_DBS` needed widening, because Mongo's guard is
# a denylist plus a narrow allowlist.
#
# What did NOT exist is the reverse direction, and the check that the two
# fabrics are actually distinct rather than two names for one database. Both
# are below.

CO_LENDER_FLUREE_URL = os.getenv("CO_LENDER_FLUREE_URL")
CO_LENDER_FLUREE_LEDGER = os.getenv("CO_LENDER_FLUREE_LEDGER", "colender-main")

def _co_lender_env(*names: str, default: str | None = None) -> str | None:
    """First non-empty value among `names`.

    Two spellings are in the wild and both are reasonable. This module was
    written against the libpq-style names (`CO_LENDER_PGHOST`, mirroring
    `PGHOST`), while the provisioned instance exports the more readable
    `CO_LENDER_PG_HOST` family. Accepting both costs six lines and removes a
    whole class of "everything is configured and nothing connects" — which is
    exactly the silent-misconfiguration failure the rest of this module exists
    to prevent, so it would be perverse to leave a trap in the reader itself.

    `.env.example` documents the libpq-style names as canonical.
    """
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


CO_LENDER_PG = {
    # `CO_LENDER_HOST` is accepted for the host only: the provisioned block
    # spells it without the `PG` infix, and there is no other CO_LENDER host
    # it could be confused with (Mongo carries its host inside its URI).
    "host": _co_lender_env("CO_LENDER_PGHOST", "CO_LENDER_PG_HOST",
                           "CO_LENDER_HOST"),
    "port": _co_lender_env("CO_LENDER_PGPORT", "CO_LENDER_PG_PORT",
                           default="5432"),
    "dbname": _co_lender_env("CO_LENDER_PGDATABASE", "CO_LENDER_PG_DB",
                             default="colenderdb"),
    "user": _co_lender_env("CO_LENDER_PGUSER", "CO_LENDER_PG_USER"),
    "password": _co_lender_env("CO_LENDER_PGPASSWORD",
                               "CO_LENDER_PG_PASSWORD"),
}
CO_LENDER_PG_SCHEMA = os.getenv("CO_LENDER_PG_SCHEMA", "colender")

#: Optional. The peer needs Fluree and Postgres; MongoDB only if its product
#: carries its own passage lineage, which our side already holds from EDGAR.
CO_LENDER_MONGO_URI = os.getenv("CO_LENDER_MONGO_URI")
CO_LENDER_MONGO_DB = os.getenv("CO_LENDER_MONGO_DB", "colender")


class CoLenderNotConfigured(RuntimeError):
    """The peer fabric has not been provisioned, or its .env block is absent."""


class FabricBoundaryError(ProtectedResourceError):
    """The two fabrics are not distinct, or a write crossed between them."""


def co_lender_configured() -> bool:
    """True when enough of the peer fabric is set to connect to it."""
    return bool(CO_LENDER_FLUREE_URL and CO_LENDER_PG["host"]
                and CO_LENDER_PG["user"])


def _require_co_lender() -> None:
    if not co_lender_configured():
        raise CoLenderNotConfigured(
            "The co-lender fabric is not configured. Set CO_LENDER_FLUREE_URL, "
            "CO_LENDER_PGHOST and CO_LENDER_PGUSER (see .env.example). "
            "Nothing falls back to the local fabric on purpose: a silent "
            "fallback would run a federation demonstration against a single "
            "store and report success."
        )


def assert_distinct_fabrics() -> None:
    """Refuse two fabrics that are secretly one.

    Every check here is a way the peer could end up pointing at our own data
    while every connection still succeeds and every query still returns rows.
    That is the shape of failure this whole module exists for — it does not
    announce itself, and the demonstration keeps producing plausible output.

    The role check is deliberately as hard as the database check. A peer that
    connects as `parkave` can reach `parkavedb` whether or not it is pointed
    at it today, so the boundary would be a convention rather than a control.
    """
    if not co_lender_configured():
        return

    local_pg = (PG["host"], str(PG["port"]), PG["dbname"])
    peer_pg = (CO_LENDER_PG["host"], str(CO_LENDER_PG["port"]),
               CO_LENDER_PG["dbname"])
    if local_pg == peer_pg:
        raise FabricBoundaryError(
            f"The co-lender Postgres is the SAME database as ours "
            f"({local_pg[0]}:{local_pg[1]}/{local_pg[2]}). A separate schema "
            f"is not sufficient — cross-schema joins are a search_path away. "
            f"Give the peer its own database."
        )
    if CO_LENDER_PG["user"] == PG["user"]:
        raise FabricBoundaryError(
            f"The co-lender connects as {PG['user']!r}, the same role we use. "
            f"That role can reach {PG['dbname']!r}, so the boundary is a "
            f"convention rather than a control. Give the peer its own role "
            f"with no grant on {PG['dbname']!r}."
        )
    if CO_LENDER_FLUREE_LEDGER in (FLUREE_LEDGER_V2, FLUREE_LEDGER_V1):
        raise FabricBoundaryError(
            f"The co-lender ledger is {CO_LENDER_FLUREE_LEDGER!r}, which is "
            f"one of ours. Fluree is append-only, so a write here could not "
            f"be undone."
        )
    if CO_LENDER_MONGO_URI and CO_LENDER_MONGO_DB in (MONGO_DB_V2, MONGO_DB_V1):
        raise FabricBoundaryError(
            f"The co-lender MongoDB database is {CO_LENDER_MONGO_DB!r}, which "
            f"is one of ours."
        )
    if CO_LENDER_MONGO_DB in PROTECTED_MONGO_DBS - {CO_LENDER_MONGO_DB}:
        raise FabricBoundaryError(
            f"The co-lender MongoDB database {CO_LENDER_MONGO_DB!r} is "
            f"protected: {sorted(PROTECTED_MONGO_DBS)}"
        )


def assert_co_lender_schema(schema: str) -> str:
    """Guard the PEER's Postgres writes, mirroring `assert_v2_schema`."""
    if schema in (PG_SCHEMA_V2, PG_SCHEMA_V1):
        raise FabricBoundaryError(
            f"Refusing to write schema {schema!r} on the co-lender fabric. "
            f"That is one of OUR schemas — a loader has crossed the boundary."
        )
    if schema != CO_LENDER_PG_SCHEMA:
        raise FabricBoundaryError(
            f"Refusing to write to schema {schema!r}. The co-lender fabric "
            f"writes only to {CO_LENDER_PG_SCHEMA!r}."
        )
    return schema


def co_lender_pg_connect(*, autocommit: bool = False):
    """Open a Postgres connection to the PEER fabric. Never falls back."""
    import psycopg

    _require_co_lender()
    assert_distinct_fabrics()
    conn = psycopg.connect(**CO_LENDER_PG, connect_timeout=8,
                           autocommit=autocommit)
    with conn.cursor() as cur:
        cur.execute(f'SET search_path TO "{CO_LENDER_PG_SCHEMA}", public')
    return conn


def co_lender_mongo_db(name: str | None = None, *, write: bool = True):
    """Open the PEER's MongoDB, refusing any database either fabric owns."""
    from pymongo import MongoClient

    _require_co_lender()
    if not CO_LENDER_MONGO_URI:
        raise CoLenderNotConfigured(
            "CO_LENDER_MONGO_URI is unset. MongoDB is optional for the peer "
            "fabric — omit it unless the peer's product carries its own "
            "passage lineage."
        )
    assert_distinct_fabrics()
    name = name or CO_LENDER_MONGO_DB
    if write and name in PROTECTED_MONGO_DBS:
        raise FabricBoundaryError(
            f"Refusing to open {name!r} for write on the co-lender fabric. "
            f"It is protected: {sorted(PROTECTED_MONGO_DBS)}"
        )
    return MongoClient(CO_LENDER_MONGO_URI, serverSelectionTimeoutMS=8000)[name]


#: Wave 16 (`ib-opportunity-synthesis`) ranks at a PINNED instant.
#:
#: Spec §E gives a half-life per signal class -- 30d for 13D, 14d for 8-K, 7d
#: for GDELT -- so a ranking computed at `date.today()` reorders itself as the
#: calendar moves. Two things break if this floats:
#:
#:   * §F's divergent prospect passes on build day and rots afterwards, with
#:     no check able to see it happen;
#:   * §F's "replay under the prior weight version" becomes unattributable,
#:     since a reorder could be the weight change or the clock.
#:
#: So the ranking path MUST read this constant and never the system clock.
AS_OF_IB = "2026-08-24"

#: The 12-month window §F's ~600 signals span. SYNTHETIC signals are dated
#: into it. REAL filing dates are never shifted -- a filing date is a public
#: fact, and moving one to make a window look full is fabrication.
IB_WINDOW_START = "2025-08-25"
IB_WINDOW_END = "2026-08-24"
