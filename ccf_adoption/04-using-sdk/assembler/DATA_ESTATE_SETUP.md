# Prepare the Demonstration Data Estate

## Why the assembler path starts here

A Context Product is assembled over an estate; it is not a toy function over an invented dictionary. The learning environment therefore uses the `ccf_dataprep` portable estate rather than reducing the main assembler story to SQLite.

The portable bundle represents the kind of heterogeneous estate CCF is designed to compose over. It contains two FIBO fabrics and a small peer spread across five datastore technologies, with a common restore path and an acceptance verifier.

## Canonical source

Repository: `drcastillo/ccf_dataprep`

Pinned evidence baseline for Phase 4B:

`main@fcf7dddf79c7f443300d745e90bf39510ef12ab7`

Primary paths:

- `portable/bundle/README.md`
- `portable/bundle/INSTALL-macos.md`
- `portable/bundle/INSTALL-ubuntu.md`
- `portable/restore/restore_all.sh`
- `portable/verify_install.py`

## What the bundle contains

The restorer-facing bundle describes:

- Fluree
- PostgreSQL
- MongoDB
- SQLite
- Neo4j
- a primary v2 estate
- a smaller v1 starter fabric
- a co-lender peer
- `MANIFEST.json` with artifact identity / hashes
- one cross-platform restore orchestrator
- one post-restore verifier

The standard restore sequence is:

**Fluree → PostgreSQL → MongoDB → SQLite → Neo4j → verify**

The platform-specific guides install and start the required technologies; the data restore itself follows the same code path on macOS and Ubuntu.

## Learning workflow

The adoption portal should present the data-estate setup as a gated prerequisite:

1. Obtain the portable bundle.
2. Select the macOS or Ubuntu installation guide.
3. Install/start the required datastore technologies.
4. Verify `MANIFEST.json` integrity before restore.
5. Run `restore/restore_all.sh`.
6. Run `verify_install.py`.
7. Do not begin an estate-dependent assembly tutorial until the verifier result is understood.

A store that cannot be reached is an installation problem, not evidence that CCF assembly failed. A data assertion failure is a different class and should remain distinguishable.

## Provenance posture

The estate deliberately mixes several provenance classes:

- public source data;
- synthetic-internal records standing in for information a bank would possess but cannot be reproduced publicly;
- engineered relationships/events designed to exercise a specific decision condition;
- derived values produced from those sources.

Later tutorials and Financial Services examples must say which class they are using. A synthetic or engineered data limitation must never be mislabeled as an SDK limitation.

## Current readiness note

David received an operational confirmation from the Dataprep workstream on 2026-09-13 that **portable is good to go**, and Phase 4B proceeds on that basis for the learning architecture.

However, the pinned Dataprep `main` commit still carries a documented maintenance debt: the restore bundle's fixed landmark assertions can lag the append-only estate. That commit records an example where the stored bundle landmark and live estate count differ, causing the bundle to fail a fixed-value assertion even though the restore mechanism itself is sound.

For that reason:

- Phase 4B may teach the restore architecture and use the portable estate as the canonical environment;
- Phase 4C's reproducible zero-to-running tutorial must pin the exact bundle snapshot it validates and record the verifier outcome;
- publication must not promise that an arbitrary older bundle's frozen landmark equals the latest live estate.

This is **bundle metadata/measurement debt**, not a CCF SDK limitation.

## Why not make SQLite the canonical Hello World?

A SQLite-only example could be useful as a consumer smoke test, but it would hide the assembler's central problem: constructing governed context across heterogeneous sources and semantics.

The full learning path should expose that reality early. A lightweight fixture can still exist later for someone who only wants to experience `ask → Result` without installing an estate.

## Phase 4C acceptance requirement

Before the progressive assembler tutorial is declared reproducible, it must record:

- the exact portable bundle identity;
- the exact Dataprep commit/documentation baseline;
- platform used for the validation run;
- restore command(s);
- verifier command and outcome;
- any accepted bundle-age warning or landmark exception;
- the Context Product example run against the restored estate.

The goal is not “installation instructions exist.” The goal is **zero to verified estate to served Context Product with evidence**.
