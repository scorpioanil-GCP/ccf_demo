"""Per-module ledger and schema naming, and the one seeding routine cp-04 uses.

**NOT A TEST MODULE.** A helper the six cp-04 test modules import — the plans
that build the census (24.4-04), the cycles and controls (24.4-05), and the
four gate modules (24.4-09 through 24.4-12). It contains no `test_` function
and pytest collects nothing from it.

## The collision this exists to prevent

`tests/conftest.py::fluree_url` makes ``fluree_url`` ``scope="session"`` and
env-driven: **one server for the whole run**, no per-module container, and no
analog of the fresh-schema isolation ``postgres_dsn``'s own docstring
describes. ``postgres_dsn`` is session-scoped too, and says in as many words
that isolation comes from a fresh *schema* rather than a fresh server.

Six modules transact this one fixture. **Every claim below was measured
against ``fluree/server:4.1.4`` and ``postgres:16``, not reasoned about** — the
first draft of this docstring asserted that a repeat transaction doubles every
triple, and that is FALSE:

* **Fluree, same body twice into one ledger: a data no-op.** Measured — the
  second transaction returns ``200`` and advances ``t`` from 1 to 2, and the
  family-triple count stays **1,058**. RDF set semantics render a re-assertion
  of byte-identical triples a no-op, so nothing doubles.
* **Fluree, a fixed ledger name: the second module cannot seed at all.**
  Measured — ``create`` on an existing ledger answers **409
  ``err:db/LedgerExists``**, so whichever of the six ran second would fail in
  its fixture rather than in an assertion.
* **Fluree, two modules sharing one ledger: permanent contamination.**
  Measured — module A seeds and reads **1,058**; module B admits ONE extra
  ``owns`` edge into the same ledger; module A now reads **1,059**. Fluree is
  append-only, so B's write cannot be undone, and plans 24.4-10 through
  24.4-12 exist precisely to admit untyped nodes and seventh predicates as
  sabotage. A shared ledger would leak every one of those into the census.
* **Postgres, a fixed schema: a silent clobber, not an error.** Measured —
  module A seeds 142 rows and deletes one for its own sabotage, leaving 141;
  module B seeds the same schema; A now reads **142** again. The schema DDL
  leads with ``DROP TABLE IF EXISTS ... CASCADE``, so the second seed does not
  raise ``relation "legal_entity" already exists`` — it quietly rebuilds the
  first module's table underneath it, and A finishes asserting against B's.

This repository has already shipped a red ``leg-postgres`` on ``main`` from
shared CI fixtures colliding by collection order. The failure is not
deterministic and it does not name its cause; it depends on the order pytest
happened to collect in, which is why the fix is a name nobody else can be
using rather than a cleanup step somebody has to remember.

## The naming

``ledger_for`` follows ``tests/graph/test_fluree_backend.py::_fresh_ledger``
(``ccf:probe-{uuid4().hex}``) and adds the module stem, so a failure message
names **which module owns the ledger** rather than leaving a bare UUID in the
log. ``schema_for`` applies the same discipline on the Postgres side.

## Why seeding verifies rather than trusting a 200

Measured against ``fluree/server:4.1.4``: a transaction body carrying an
unrecognized top-level key is accepted with **HTTP 200** and a real commit
receipt. So a body whose ``insert`` key were misspelled would report success
having written nothing, and every census assertion downstream would be a true
statement about an empty graph. :func:`seed` therefore reads both stores back
and refuses to return until each holds what the fixture carries.

The Fluree readback polls until two **consecutive** reads agree, not until the
read matches the expectation. A verification query issued immediately after a
write can be served before the index catches up — measured in ``ccf_dataprep``,
where three aggregates over one freshly-written predicate returned 40, 0 and 40
in succession. Retrying until the number matches what the caller wants is a
check that cannot fail; retrying until the store says the same thing twice, and
comparing once afterwards, is a check that can.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import time
import uuid
from typing import Any

import httpx
import psycopg
import pytest

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
FLUREE_FIXTURE = FIXTURES / "cp_04_family_fluree.json"
SCHEMA_SQL = FIXTURES / "cp_04_family_schema.sql"
ROWS_SQL = FIXTURES / "cp_04_family_rows.sql"

#: The token `tools/dump_cp04_fixture.py` writes where a schema name would
#: otherwise be baked into the SQL.
SCHEMA_PLACEHOLDER = "{schema}"

#: The attribute table the two SQL files create and fill.
ATTRIBUTE_TABLE = "legal_entity"

FIBO = "https://spec.edmcouncil.org/fibo/ontology/"

#: The six family predicates, in the orientation the fixture stores them.
FAMILY_PREDICATES: tuple[str, ...] = (
    FIBO + "FND/OwnershipAndControl/Ownership/owns",
    FIBO + "FND/Relations/Relations/controls",
    FIBO + "BE/LegalEntities/LEIEntities/isDirectlyConsolidatedBy",
    FIBO + "BE/LegalEntities/LEIEntities/isUltimatelyConsolidatedBy",
    FIBO + "BE/OwnershipAndControl/CorporateControl/hasGlobalUltimateParent",
    FIBO + "BE/OwnershipAndControl/CorporateControl/hasDomesticUltimateParent",
)

_UNSAFE = re.compile(r"[^a-z0-9]+")


def _stem(module_name: str) -> str:
    """A short, identifier-safe tag from a module name or a ``__file__``."""
    stem = pathlib.Path(module_name).stem
    return _UNSAFE.sub("_", stem.lower()).strip("_") or "cp04"


def ledger_for(module_name: str) -> str:
    """A Fluree ledger name nobody else can be using.

    Pass ``__file__`` or ``__name__``. The stem is carried into the name so a
    failure message says which module owns the ledger; the UUID suffix is what
    makes two modules — or two runs against one long-lived container — unable
    to transact into the same append-only ledger.
    """
    return f"ccf:cp04-{_stem(module_name)}-{uuid.uuid4().hex[:12]}"


def schema_for(module_name: str) -> str:
    """A Postgres schema name nobody else can be using.

    The same discipline as :func:`ledger_for`, on the store whose session-scoped
    fixture explicitly delegates isolation to the schema. Kept inside Postgres's
    63-character identifier limit by construction.
    """
    return f"cp04_{_stem(module_name)[:40]}_{uuid.uuid4().hex[:12]}"


def expected_counts() -> dict[str, int]:
    """What the committed fixture carries, read FROM THE FIXTURE.

    Not authored here. A number this module stated would be this module
    agreeing with itself about what it just wrote.
    """
    body = json.loads(FLUREE_FIXTURE.read_text(encoding="utf-8"))
    documents: list[dict[str, Any]] = body["insert"]
    triples = sum(
        len(document.get(predicate, []))
        for document in documents
        for predicate in FAMILY_PREDICATES
    )
    rows = len(re.findall(r"^  \('", ROWS_SQL.read_text(encoding="utf-8"), re.M))
    return {"nodes": len(documents), "family_triples": triples, "legal_entity_rows": rows}


def _sparql(client: httpx.Client, url: str, query: str) -> list[dict[str, Any]]:
    response = client.post(
        f"{url}/v1/fluree/query",
        headers={"Content-Type": "application/sparql-query"},
        content=query.encode("utf-8"),
    )
    response.raise_for_status()
    bindings: list[dict[str, Any]] = response.json()["results"]["bindings"]
    return bindings


def _family_triples(client: httpx.Client, url: str, ledger: str) -> int:
    """ENUMERATE the six predicates and count the rows. Never an aggregate.

    The aggregate forms over this data invent phantoms — the estate returns 178
    from ``COUNT(DISTINCT ?p)`` and 198 from ``GROUP BY ?p`` where
    ``SELECT DISTINCT ?p`` returns 171 — so every count in cp-04 is taken over
    enumerated rows.
    """
    total = 0
    for predicate in FAMILY_PREDICATES:
        total += len(
            _sparql(
                client,
                url,
                f"SELECT ?s ?o FROM <{ledger}> WHERE {{ ?s <{predicate}> ?o }}",
            )
        )
    return total


def _stable(read, *, attempts: int = 8, delay: float = 0.75) -> int:
    """Read until two CONSECUTIVE reads agree. Stability, not correctness.

    This function has no idea what the caller expects, which is the point: a
    retry loop that stopped when the number matched the expectation would be a
    check that cannot fail.
    """
    previous: int | None = None
    for attempt in range(attempts):
        current = read()
        if previous is not None and current == previous:
            return current
        previous = current
        if attempt < attempts - 1:
            time.sleep(delay)
    return previous if previous is not None else 0


def seed(fluree_url: str, ledger: str, dsn: str, schema: str) -> None:
    """Seed one ledger and one schema from the committed fixture.

    Creates ``ledger``, transacts ``cp_04_family_fluree.json`` into it, applies
    the two SQL files into ``schema``, and returns **only after both are
    readable**. Raises rather than returning a partially seeded fabric: a
    census run against a short seed is a true statement about the wrong
    population, which is the defect class this whole rung exists to catch.

    **The write target must be disposable.** Seeding a curated store is refused
    by name before anything is created — see
    :func:`refuse_to_write_the_curated_estate`. The division `D-IMPL-318`
    settles: **the curated estate is read-only and writes go to a local,
    disposable store**, so a test that must perturb data still can, and cannot
    do it where the damage is permanent.
    """
    refuse_to_write_the_curated_estate(fluree_url, dsn)
    expected = expected_counts()
    body = json.loads(FLUREE_FIXTURE.read_text(encoding="utf-8"))

    with httpx.Client(timeout=180) as client:
        created = client.post(
            f"{fluree_url}/v1/fluree/create",
            headers={"Content-Type": "application/json"},
            content=json.dumps({"ledger": ledger}),
        )
        if created.status_code != 201:
            raise RuntimeError(
                f"could not create ledger {ledger!r}: "
                f"{created.status_code} {created.text[:200]}"
            )
        applied = client.post(
            f"{fluree_url}/v1/fluree/update/{ledger}",
            headers={"Content-Type": "application/json"},
            content=json.dumps(body),
        )
        applied.raise_for_status()

        triples = _stable(lambda: _family_triples(client, fluree_url, ledger))
        if triples != expected["family_triples"]:
            raise RuntimeError(
                f"ledger {ledger!r} holds {triples} family triples, expected "
                f"{expected['family_triples']}. The server accepts an unknown "
                f"top-level key with HTTP 200, so a 200 is not evidence the "
                f"transaction wrote anything."
            )

    with psycopg.connect(dsn, autocommit=True) as db, db.cursor() as cursor:
        cursor.execute(SCHEMA_SQL.read_text(encoding="utf-8").replace(SCHEMA_PLACEHOLDER, schema))
        cursor.execute(ROWS_SQL.read_text(encoding="utf-8").replace(SCHEMA_PLACEHOLDER, schema))
        cursor.execute(f'SELECT count(*) FROM "{schema}".{ATTRIBUTE_TABLE}')
        row = cursor.fetchone()
        rows = int(row[0]) if row else 0
    if rows != expected["legal_entity_rows"]:
        raise RuntimeError(
            f"schema {schema!r} holds {rows} {ATTRIBUTE_TABLE} rows, expected "
            f"{expected['legal_entity_rows']}"
        )


# ---------------------------------------------------------------------------
# The curated estate, read-only — `D-IMPL-318`.
# ---------------------------------------------------------------------------

#: The four variables cp-04's deployment reads. A converted module supplies
#: none of them: it runs against whatever estate the operator exported.
ESTATE_VARIABLES: tuple[str, ...] = (
    "CCF_CP_04_FLUREE_URL",
    "CCF_CP_04_FLUREE_LEDGER",
    "CCF_CP_04_POSTGRES_DSN",
    "CCF_CP_04_POSTGRES_SCHEMA",
)

#: Where a missing estate must FAIL rather than skip. A leg that quietly skips
#: is a green build that proved nothing.
ESTATE_REQUIRED = "CCF_REQUIRE_ESTATE"


def live_estate() -> tuple[str, str]:
    """The curated `.76` estate, seeding nothing (`D-IMPL-318`, CLAUDE.md §9).

    Returns the ledger and schema the operator pointed cp-04 at, so a converted
    module's fixture keeps the same ``(ledger, schema)`` shape :func:`seed`
    returned and nothing downstream of it has to change.

    **This function writes nothing.** That is the whole reason it exists: every
    call to :func:`seed` mints a Fluree ledger, Fluree is append-only, and the
    27 ``ccf:cp04-*`` ledgers already on the curated server can never be
    removed. A converted module stops adding to that pile.

    **It supplies no values of its own.** A default here would be a server
    nobody chose, and pointing at the v1 names in ``ccf_dataprep/.env`` —
    ``fibo:main``, ``public`` — resolves an anchor in Postgres that has no node
    in the graph, which is the trap CLAUDE.md §9 records.
    """
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = (
            f"the curated estate is not configured: {', '.join(missing)} unset."
            " Point them at the v2 namespaces — Fluree ledger `fibo-v2`,"
            " PostgreSQL schema `ccf_v2` — never the v1 names in"
            " `ccf_dataprep/.env` (CLAUDE.md §9)"
        )
        if os.environ.get(ESTATE_REQUIRED):
            pytest.fail(message)
        pytest.skip(message)
    return (
        os.environ["CCF_CP_04_FLUREE_LEDGER"],
        os.environ["CCF_CP_04_POSTGRES_SCHEMA"],
    )

# ---------------------------------------------------------------------------
# The write fence — `D-IMPL-318`.
# ---------------------------------------------------------------------------

#: Hosts whose stores are CURATED and must never be written by a test. Declared
#: rather than hard-coded so a second estate is a configuration change; the
#: default is the estate CLAUDE.md §9 names.
CURATED_HOSTS_ENV = "CCF_CURATED_ESTATE_HOSTS"
DEFAULT_CURATED_HOSTS = "192.168.4.76"


def _curated_hosts() -> frozenset[str]:
    raw = os.environ.get(CURATED_HOSTS_ENV, DEFAULT_CURATED_HOSTS)
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


def _redacted(target: str) -> str:
    """A connection target safe to put in a message.

    A DSN carries a password. This guard's whole job is to be LOUD — it raises,
    pytest prints the message once per erroring test, and CI keeps that output
    — so an un-redacted DSN here would publish the estate's credential every
    time somebody misconfigured a run. Found by reading this guard's own first
    failure output rather than by review.
    """
    return re.sub(r"://([^:/@]+):[^@]*@", r"://\1:***@", target)


def refuse_to_write_the_curated_estate(*targets: str) -> None:
    """Refuse, by name, to seed anything that lives on a curated host.

    ``D-IMPL-318``. The modules that still seed do so because they must —
    `anchor` and `debt` perturb data to prove a guard fires, and a perturbation
    has nowhere to happen but a store the test owns. What they must NOT do is
    perform that write against the curated estate.

    **The failure this closes is a configuration accident, not a coding
    mistake.** ``CCF_TEST_FLUREE_URL`` already defaults to
    ``http://localhost:8090``; the 27 ``ccf:cp04-*`` ledgers on the curated
    server exist because runs exported it pointing there instead. Fluree is
    append-only, so each of those is permanent. Nothing in the code said no.

    **Refused rather than silently redirected.** Rewriting the target to
    localhost would run the suite against a store the operator did not choose
    and did not populate, and report the result as though they had.

    Raises:
        RuntimeError: any target names a curated host.
    """
    curated = _curated_hosts()
    offending = [
        _redacted(target)
        for target in targets
        if target and any(host in target for host in curated)
    ]
    if offending:
        raise RuntimeError(
            "refusing to SEED a curated store: "
            + ", ".join(sorted(offending))
            + f". Hosts in {CURATED_HOSTS_ENV} (default {DEFAULT_CURATED_HOSTS})"
            " hold the curated estate; Fluree is append-only, so every seeded"
            " ledger there is permanent. Point CCF_TEST_FLUREE_URL and"
            " CCF_TEST_POSTGRES_DSN at a local container. Reading the curated"
            " estate is expected — see `live_estate` — writing to it is not"
            " (CLAUDE.md §9, `D-IMPL-318`)"
        )
