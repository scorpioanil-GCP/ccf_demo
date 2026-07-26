---
phase: 04-phase-i-1-fabric-core
plan: 10
subsystem: graph-postgres-backend
tags: [l3, graph-store, postgres, psycopg, conformance, dual-backend, ci]
requires:
  - 04-04 (GraphReader/GraphWriter Protocols, SQLite backend, the six-semantics conformance suite, boot composition root)
  - 04-06/04-07 (contracts and Control Plane surfaces the suite drives through)
  - 04-08 (as-of reads render supersession and lineage as of the boundary — the rule both backends now share by construction)
provides:
  - Postgres reference GraphStore (psycopg 3, sync) behind the same GraphReader Protocol
  - PostgresGraphWriter, in ccf.graph._writer alongside the SQLite writer
  - BaseGraphWriter / BaseGraphReader — the write and read semantics held once, dialect supplied per backend
  - explicit backend selection at boot (database_path XOR postgres_dsn)
  - the conformance suite running identically on both substrates, locally and in CI
affects:
  - FABR-01 is complete: one suite, two backends, both green
  - later plans that boot a fabric may now name Postgres; SQLite remains the default and the examples substrate
  - a third backend adds two dialect classes and one fixture param — it does not restate a semantic
tech-stack:
  added:
    - psycopg 3.3.4 (sync, hand-rolled SQL — no ORM; physical layout is backend-internal per D-IMPL-34)
    - testcontainers postgres:16 for the local conformance leg (D-10)
  patterns:
    - semantics in a shared base, dialect in the subclass — the two backends cannot drift where the suite is least able to notice
    - canonical RFC3339 text timestamps on both substrates, so cross-backend comparison is byte equality rather than tolerance
    - one throwaway Postgres schema per booted fabric — the shared-server analogue of a temp file
    - CCF_REQUIRE_POSTGRES: an environment that declares the substrate mandatory turns a skip into a failure
key-files:
  created:
    - src/ccf/graph/backends/postgres.py
    - src/ccf/graph/reader.py
  modified:
    - src/ccf/graph/_writer.py
    - src/ccf/graph/backends/sqlite.py
    - src/ccf/boot.py
    - tests/conftest.py
    - tests/conformance/test_graphstore.py
    - .github/workflows/ci.yml
decisions:
  - "Timestamps are canonical RFC3339 *text* on Postgres, not timestamptz. The conformance suite compares canonical_bytes across substrates; a native timestamp column round-trips at the substrate's own precision, which is exactly the drift Pitfall 3 names. Canonical text still sorts chronologically, so the range and ordering predicates are unaffected."
  - "The write semantic lives once, in BaseGraphWriter; each backend supplies only SQL and transaction handling. Two hand-written copies of the supersession restitch would be two chances to get late-arriving observations wrong, and the conformance suite could only report that they disagreed — not which was right."
  - "Likewise the bitemporal *rendering* rules (lineage boundary, supersession-as-of) moved to a shared BaseGraphReader. Only one of the three places 'as of' must be honoured is expressible in SQL; the other two were the divergence risk."
  - "Backend selection is by explicit argument (database_path XOR postgres_dsn), never inferred from the shape of a string. A fabric that guessed its substrate could boot against a development SQLite file in production and still pass every test."
  - "The Postgres connection runs autocommit with writes in explicit transactions. Under psycopg's default implicit transaction every read would hold an open snapshot on the shared connection, so a write committed inside a nested transaction() would land in a savepoint of a transaction nobody ever commits."
  - "Graph identity for Postgres is host/port/database#schema — credentials stripped. It is the string the single-writer violation message prints, so dropping the password is structural rather than a logging convention (T-04-24)."
  - "Test isolation on Postgres is a fresh schema per booted fabric rather than a fresh server. It gives the shared CI service container the same per-test cleanliness a temp file gives SQLite, and it makes 'two schemas are two graphs' a property the single-writer check can key on."
  - "CI sets CCF_REQUIRE_POSTGRES so an unavailable substrate fails rather than skips. A marker-selected job that collects twelve tests and skips all twelve is a green build that proved nothing — the specific failure mode this leg is most exposed to."
metrics:
  duration: ~45 min
  completed: 2026-07-25
  tasks: 2
  commits: 2
---

# Phase 4 Plan 10: Postgres Reference GraphStore Summary

FABR-01's dual-backend commitment closes: the identical twelve-test
six-semantics conformance suite passes on SQLite and on a real Postgres, with
zero backend-specific test forks and not one changed test body — because the
Postgres backend was implemented against a suite that already existed (D-11),
and because everything the suite is least able to distinguish now lives in one
place rather than two.

## What Was Built

**Task 1 — the Postgres backend** (`8d315e4`). `backends/postgres.py` carries
compound `UNIQUE (tenant_id, entity_uri)` at the persistence tier, `ON CONFLICT
(tenant_id, entity_uri) DO UPDATE` node upsert, ignore-on-conflict lineage
append keyed on full entry identity, and supersession columns — the SQLite
layout table for table, with `seq BIGSERIAL` standing in for `rowid` as the
insertion-order tiebreak within one observed-time instant. The schema name is
the one identifier that must be interpolated; it goes through
`psycopg.sql.Identifier`, which quotes and escapes rather than pastes, and
`search_path` is set session-wide so no other statement needs qualification or
could be tricked into resolving elsewhere.

Two shared modules came out of the work rather than being planned for, and both
are the substance of the parity claim:

- `ccf/graph/reader.py` — `BaseGraphReader`. An as-of read has to honour "as
  of" in three places: the row filter, the lineage set, and the supersession
  edge. Only the first is expressible in SQL. Two independent copies of the
  other two would have made the conformance suite an assertion that two
  implementations of a subtle rule happened to agree.
- `BaseGraphWriter` inside `_writer.py` — content identity, lineage set-union,
  chain restitching, and tenant-scope refusal, held once. Both writers stay in
  the CINV-02-restricted module, honouring the rule 04-04 wrote down: **a new
  backend adds a writer class here, never a writer module elsewhere.**

`boot.py` selects the backend by explicit argument. SQLite stays the default
because it is the development backend (D-IMPL-02); Postgres is chosen by
saying so.

**Task 2 — the second param and the CI leg** (`a625e58`). `graph_backend` gains
a `postgres` param marked `pytest.mark.postgres`. The fixture's original note
promised the Postgres wave would add a param and leave the bodies alone; that
is literally what happened — the diff to `test_graphstore.py` is the fixture
and nothing else. `conftest.py` grew a session-scoped `postgres_dsn` (CI's
service container via `CCF_TEST_POSTGRES_DSN`, else a testcontainers
`postgres:16`, else a skip naming what is missing) and
`fabric_boot(backend="postgres")`, which boots each fabric into a schema unique
to that boot.

## Key Implementation Details

- **No substrate-quirk test class was needed.** D-16 permits backend-specific
  tests for genuine quirks; none arose, because the quirks were absorbed where
  they belong — dialect in the SQL constants, precision in the canonical
  timestamp policy. `grep` for a backend branch in a test body returns only the
  fixture's own dispatch.
- **`INSERT OR IGNORE` became `ON CONFLICT ... DO NOTHING` on both backends.**
  SQLite has supported it since 3.24, and using one spelling means the two
  statement sets differ only in placeholder style and function names, which is
  the difference a reviewer can actually check.
- **Rowcount is part of the `_Txn` contract, not a driver detail.** The whole of
  how the writer distinguishes a new claim from a re-arrival is "did that insert
  change a row", so each backend's transaction wrapper states it explicitly.
- **`CCF_REQUIRE_POSTGRES` is the guard against a vacuous leg.** Verified in
  both directions locally: with Docker unreachable the required mode errors and
  the default mode skips with a named reason.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical structure] Shared read/write bases rather than a
second hand-written implementation**

- **Found during:** Task 1
- **Issue:** The plan says "mirroring `sqlite.py` semantics exactly". Mirroring
  by hand produces two copies of the supersession-as-of rule, the lineage
  boundary rule, and the chain restitch — the three rules that are subtle,
  recently changed (04-08), and invisible to a suite that only asks whether the
  two backends agree.
- **Fix:** Extracted `BaseGraphReader` (new `src/ccf/graph/reader.py`) and
  `BaseGraphWriter` (inside the existing `_writer.py`), and rewrote the SQLite
  backend onto them. Each backend now contributes SQL and a transaction wrapper.
- **Files modified:** `src/ccf/graph/reader.py` (new),
  `src/ccf/graph/backends/sqlite.py`, `src/ccf/graph/_writer.py`
- **Commit:** `8d315e4`
- **Note:** `sqlite.py` and a new module were outside the plan's
  `files_modified`. The alternative was a 200-line duplicate of the fabric's
  most correctness-sensitive code.

**2. [Rule 2 - Missing critical functionality] `CCF_REQUIRE_POSTGRES`**

- **Found during:** Task 2
- **Issue:** With the postgres marker selecting real tests, the CI step passes
  whether the tests run or skip. A missing DSN would produce a green job that
  asserted nothing about Postgres — the exact outcome D-10 exists to prevent.
- **Fix:** The `postgres_dsn` fixture fails instead of skipping when the
  environment declares Postgres mandatory; `ci.yml` sets the variable.
- **Files modified:** `tests/conftest.py`, `.github/workflows/ci.yml`
- **Commit:** `a625e58`

### Interpretations

- **`ON CONFLICT` count in `postgres.py`.** The acceptance criterion greps
  `backends/postgres.py` for ≥ 2 occurrences, but the same task instructs that
  the concrete writer live behind the `_writer` restriction. Upsert is write
  SQL, so it is in `_writer.py` (10 occurrences); `postgres.py` has none in code
  *because it has no write path at all* — the same reading 04-04 recorded, and
  the stronger one.
- **`grep -rl "ccf.graph._writer" src/`** returns seven files because the module
  is *named* in docstrings explaining the invariant. Import-level the answer is
  `src/ccf/boot.py` alone, asserted by the existing invariant test and by the
  CINV-02 lint, both green.
- **Backend selection signature.** The plan says "construct the Postgres backend
  from a DSN (selection by explicit config)". Realized as
  `boot(database_path=... )` XOR `boot(postgres_dsn=..., postgres_schema=...)`,
  with a `ValueError` when neither or both are given, rather than a mode enum —
  the arguments a caller supplies already name the substrate unambiguously.

## Verification

| Check | Result |
|---|---|
| `pytest tests -q` (full suite, testcontainers Postgres included) | 321 passed, 3 skipped |
| `pytest tests -q -m postgres`, `CCF_TEST_POSTGRES_DSN` **unset** (testcontainers path) | 12 passed |
| `pytest tests -q -m postgres` against a service-container-shaped DSN on `postgres:16` | 12 passed |
| `pytest tests -q -m "not postgres and not chroma"` (the pre-existing SQLite bar) | 309 passed, 3 skipped |
| `pytest -m postgres --collect-only -q` | 12 collected, 30 deselected |
| `CCF_REQUIRE_POSTGRES=1` with Docker unreachable | 12 errors (fails, does not skip) |
| No `CCF_REQUIRE_POSTGRES`, Docker unreachable | 12 skipped with a named reason |
| `python -m tools.lints --all` | exit 0, zero allowlist entries added |
| `pytest tools/lints/tests -q` | 45 passed |
| `mypy --strict src` | Success, 48 source files |
| `grep -cE 'f"(INSERT\|UPDATE\|SELECT\|DELETE)'` on `postgres.py`, `_writer.py`, `reader.py` | 0 — no f-string SQL |
| `grep -ci "DELETE FROM"` on `postgres.py` / `_writer.py` | 0 — nothing is ever deleted |
| Backend branch in a conformance test body | none — only the fixture's own dispatch |
| Import-level importers of `ccf.graph._writer` under `src/` | `ccf/boot.py` only |
| Post-commit deletion check, both commits | no deletions |

**On the Postgres runs specifically:** these were real, on this machine, against
real `postgres:16` servers — both a testcontainers instance and a manually
started container standing in for the GitHub Actions service container. Docker
29.2.1 was available, so nothing here is a claim about a run that could not be
performed. What has *not* been executed is the GitHub Actions workflow itself;
the service-container leg is verified by equivalence (same image, same DSN
shape, same command) rather than by observation.

## Known Stubs

None.

## Threat Flags

None. The two registered threats are mitigated as planned: T-04-23 (SQL
injection) by parameterized statements throughout, with the single identifier
interpolation going through `psycopg.sql.Identifier` and the f-string SQL grep
gate at zero; T-04-24 (DSN/credentials) by taking the DSN from the caller's
environment, never committing it, and building the graph identity — the string
that appears in single-writer violation messages — from host/port/database and
schema only.

## Self-Check: PASSED

All 2 created files and 6 modified files exist on disk; both commit hashes
(`8d315e4`, `a625e58`) are present in `git log`.
