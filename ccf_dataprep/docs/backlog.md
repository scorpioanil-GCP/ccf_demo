# Backlog

Work that is agreed and scoped but deliberately not scheduled yet. Items here
are **not** open questions — they are decided, waiting on sequence.

**Not to be confused with `docs/wave18-deferred-findings.md`.** Backlog items are
*decided work waiting on sequence*; deferred findings are *review findings judged
minor and left*. A deferred finding that someone decides to schedule becomes a
backlog item; until then it is not committed work.

---

## B1 · Portable dump and restore of every store — *the final phase*

> **DELIVERED 2026-08-28.** Merged to `main` at `c899026` and pushed. The
> bundle is live at `/data/data_bundle` on db1: 373 MB, 19 manifest entries
> (11 data artifacts + 8 shipped scripts), every sha256 independently
> recomputed with 0 mismatches. Reference: `docs/b1-portable-dump-design.md`
> (design, measurements, rehearsal record), `docs/b1-portable-dump-plan.md`
> (the 10-task plan), `docs/b1-rulings.md` (decisions taken during execution).
>
> **One acceptance criterion is NOT yet discharged:** the macOS branch of
> the restore scripts is unexercised. The Ubuntu branch was rehearsed on db1
> (Ubuntu 24.04) — verifier exit 0, 20/20 checks, "Estate verified" with
> nothing skipped, Neo4j included via a throwaway container. The macOS run
> is scheduled for the evening of 2026-08-28. **Until it passes, B1 is
> delivered but not proven on both targets.**
>
> Also never exercised, recorded rather than hidden: a truncated-Fluree
> archive as a damage case (the CLI cannot produce one and the on-disk
> commit format is undocumented), and there is no Neo4j case inside
> `portable/tests/damaged_restore.sh` — Neo4j restore correctness was proven
> directly against the throwaway container instead.

**Requested by the user 2026-08-22. To be done LAST, once all 21 products'
data is loaded.**

**The goal, in the user's words:** install all the data stores on a laptop,
load all the data into them, and run the examples in the reference documents.
So the deliverable is a **dump plus a restore path**, not a re-derivation
pipeline.

### Partial delivery — the Fluree half exists as of 2026-08-24

`loaders/dump_fluree.py` was built during Wave 15 because the ultimate-parent
remediation (`known-issues.md` §19.3) needed a rollback path before it touched
139 real edges. The user confirmed it belongs to B1 rather than being a one-off,
so it is recorded here rather than left in a wave note.

    uv run loaders/dump_fluree.py                    # dump current state
    uv run loaders/dump_fluree.py --check            # verify against the ledger
    uv run loaders/dump_fluree.py --restore <file>   # re-assert

What it establishes for the rest of B1:

- **Fluree 4.1.4 has no backup, snapshot, export or dump endpoint over HTTP** —
  all four paths return 404. That finding is still true and still the reason
  `loaders/dump_fluree.py`'s logical dump through the query API exists: at the
  time it was built, 63,973 triples, 8.7 MB of N-Triples. **It is false of the
  CLI, corrected 2026-08-27/28 (Task 10) — see the note below the table.**
- **The verification compares content as a set, not counts.** A dump with the
  right number of wrong lines is exactly what a count-based check cannot see,
  and the checker is falsified against that case specifically — a swapped line
  leaving the total at 63,973 is caught.
- **Restore is deliberately additive.** It asserts what the file holds and does
  not retract whatever the ledger has gained since, because a restore that
  deleted unknown triples would be more dangerous than the operation it
  protects against.
- **`xsd:date` is a trap on this build** — see `known-issues.md` §19.4. The dump
  exits non-zero if a typed literal ever appears, so the estate finds out on a
  backup rather than on a restore.

Still outstanding for B1: Postgres, MongoDB, SQLite, and the second Fluree
instance, plus the stand-up instructions that make the dumps usable on a
laptop.

### Why this is the right shape, and easier than it sounds

An earlier discussion framed portability as making every loader replay from a
saved artifact and extending `artifact_reproduces_store.py` to all 51
artifacts. **That is a different and harder problem, and this phase does not
need it.** A physical dump captures each store *as it is*, so it sidesteps
every question about whether re-fetching returns the same answer — which today
it would not, for at least four reasons recorded in §B2 below.

Reproducibility and portability are separable. This item is portability.

### Measured size, 2026-08-22 (SUPERSEDED — see 2026-08-27 below)

| Store | Content | Size |
|---|---|---|
| **MongoDB** `fibo_v2` | 16,057 docs (documents, passages, memoranda, research notes) | 375 MB data / **211 MB stored** — embeddings dominate |
| **Postgres** schema `ccf_v2` | 62 tables | **68 MB** |
| **Fluree** `fibo-v2` | 55,751 triples at `t=1315` | small; see the ledger caveat |
| **SQLite** `data/departmental.sqlite` | departmental store | **60 KB** — already a file, just copy |
| **Neo4j** | optional, undecided per CLAUDE.md | — |

Roughly **300 MB** total, before compression. Nothing here argues for
sampling. The estate kept growing after this measurement — Wave 19 alone
added the capital-units repair, the regime corpus, and the large-exposure
product — so the table above is now stale by a wide margin. It is kept for
the record, not as current sizing.

### Measured size, 2026-08-27 — current, laptop-scale bundle shipped

| Store | Content | Size |
|---|---|---|
| **MongoDB** `fibo_v2` | 38,238 docs, 6 collections | **576 MB data / 329 MB stored** |
| **Postgres** schema `ccf_v2` | 113 base tables (115 unfiltered — 2 views) | **718 MB** |
| **Fluree** `fibo-v2` | 87,162 triples at `t=4468` | **47 GB on disk** (index bloat — see `known-issues.md` §50) |
| **SQLite** `data/departmental.sqlite` | departmental store | **8 tables** (not 5 — corrected below) |
| **Neo4j** | 14 nodes / 16 relationships | holds **v1** data, not v2 |

The 47 GB Fluree figure is on-disk ledger storage, not what ships — the
bundle exports the ledger via the CLI (see below) rather than copying
`/data/fluree` wholesale. **The shipped bundle is 373 MB across 11
artifacts.**

**SQLite is 8 tables, not 5.** `CLAUDE.md`'s "Done — `data/departmental.sqlite`,
5 tables" line and the store-assignment table's "created, 5 tables" note are
both stale; both are corrected in this same close (CLAUDE.md's copy is fixed
directly, since it is not versioned narrative like this backlog).

### What already works in our favour

`ccf/config.py` is **fully environment-driven** — `FLUREE_URL`, `PGHOST`,
`MONGO_URI`, `NEO4J_URI` and every database/schema/ledger name read from the
environment with db1 as the default. A laptop install therefore needs a
different `.env` and nothing else. `.env.example` already documents the shape.
No code change is required for the connection layer.

### The three things that need real care

**1 · MongoDB: dump ONE database, never the instance.** db1 also runs
`rtdetect` with roughly 5.5 million documents, entirely unrelated to this
project. `mongo_db()` deliberately offers no way to enumerate databases, for
exactly this reason. The dump must name `fibo_v2` explicitly —
`mongodump --db fibo_v2` — and the restore must target it explicitly. A
whole-instance `mongodump` would pull in a system that is not ours and is
several times larger than everything we have.

**2 · Fluree: `t` is part of the data, not an implementation detail.**
The ledger is immutable and every Context Product records `graph_snapshot_at`
as a ledger `t`. Replaying 55,751 triples into a fresh ledger reproduces the
final *state* but not the *history* — the restored ledger's `t` sequence will
not match, so any as-of query, any lineage record pinned to a `t`, and the
`covenant-in-force-as-of` product's whole mechanism will disagree with what
the reference documents say. Decide deliberately between:

- shipping Fluree's ledger files directly, preserving `t` exactly; or
- replaying triples and accepting that recorded `t` values become wrong,
  which then requires every document quoting a `t` to be regenerated.

**The first is almost certainly right.** This needs checking against how
Fluree stores `fibo-v2` on db1 before the phase starts.

**Resolved 2026-08-27/28 (Task 2 of this phase) — there was a third door.**
The dilemma above was framed as HTTP-ledger-files-vs-replay because the HTTP
API has no export endpoint (still true — see above). The Fluree **CLI** does:
`fluree export --format ledger` produces a `.flpack` archive carrying commits
and index artifacts, restored with `fluree create <ledger> --from <file>.flpack`;
`--no-indexes` makes a smaller archive when the index generations (see
`known-issues.md` §50) aren't worth shipping. This preserves `t` exactly
without shipping the raw 47 GB `/data/fluree` directory, so the bundle used
the CLI export rather than either horn of the original choice. `fluree
history <entity> --from N --to M` also works from the CLI, even though the
equivalent HTTP endpoint 404s (`known-issues.md` §51).

**3 · The restore has to be verified by the existing gates, not by eyeballing
counts.** After restoring to a fresh machine, `partition.py` (26/26),
`conditions.py`, `orphan_terms.py` and the per-wave gates must all pass
against the restored stores. A restore that loads without error and fails a
condition is the failure mode to design against — and it is the same shape as
every defect this project has recorded: it looks fine because nothing checked
the thing that matters.

> **Superseded by `docs/b1-portable-dump-design.md` § Acceptance.** Both this
> paragraph's `partition.py`/`conditions.py`/`orphan_terms.py` re-run and the
> two Acceptance bullets below it (validator parity, `ccf_dataprep_v2.md`
> examples runnable) were consciously descoped during the build. The design
> doc's `verify_install.py` is a standalone landmark-value-and-join checker
> that runs on a laptop with no repo checkout — it asserts fixed counts (e.g.
> `t=4468`, 87,162 triples, 113 `BASE TABLE`s) and peer-fabric distinctness
> directly against the restored stores, rather than re-implementing
> `partition.py` and the other repo-resident validators, which assume a
> checkout and a live connection to the *original* estate. The
> reference-document examples in `docs/ccf_dataprep_v2.md` were never in
> scope for this phase either. See that doc's Acceptance section (criteria
> 1–7) for what actually gates this work.

### Acceptance

- ~~A documented install path for all four stores on a clean machine.~~
  **Done** — `INSTALL-macos.md` and `INSTALL-ubuntu.md`, version-pinned,
  plus `laptop-loader.sh` which fetches the bundle and verifies every
  artifact against `MANIFEST.json` before you spend an evening on it.
- ~~A `dump/` and `restore/` command pair per store, idempotent, with the
  MongoDB scoping rule enforced **in code**, not in a comment.~~
  **Done** — five stores, both fabrics, plus v1. The MongoDB allowlist is
  `portable/manifest.py::assert_mongo_db_allowed`, and it was observed
  refusing `rtdetect` on db1 itself, not merely written.
- ~~Every existing validator green against the restored stores.~~
- ~~The examples in `docs/ccf_dataprep_v2.md` runnable end to end.~~

  Both struck bullets are superseded — see the note above. What actually
  gates completion is `docs/b1-portable-dump-design.md` § Acceptance.

---

## B2 · Make re-derivation from persisted sources actually hold

**Related to B1 but genuinely separate, and lower priority.** B1 gives the
user a working copy; this gives the estate the property that saved sources
rebuild the stores identically. Recorded because the gap was measured
2026-08-22 and should not have to be rediscovered.

| Gap | Detail |
|---|---|
| Loaders that fetch live at load time | `load_xbrl_peers.py`, `load_xbrl_wave2.py`, `load_peer_cohorts_wave13a.py` re-query the SEC rather than replaying a saved file. XBRL facts are revised over time, so a reload can legitimately differ |
| Reproduction gate covers 18 of 51 artifacts | `artifact_reproduces_store.py`'s `IN_SCOPE` names Wave 10/11a/11b only; it says so, and everything from Waves 0–9 and 12 is unchecked |
| Fetch and load fused | `fetch_rating_actions.py` writes `context_debt` inside the fetch, so there is no saved intermediate. Its own comment records that its confirmation heuristic changed "sharply" between runs |
| Collateral chain not re-runnable under input change | `known-issues.md` §13.1 — positional asset ids renumber when `facility` gains a row |

---

## B3 · Restore capabilities do not survive an estate that keeps changing

**Raised by Dave 2026-09-13**, on the observation that the bundle's landmarks
went stale twice in four days. Recorded because the *fix each time* has been to
bump a number, and that is treating the symptom.

### What actually happens today

The bundle asserts landmark values on restore — `88,325` triples, `116` tables.
Those are **frozen measurements of an append-only store**, which is the same
defect class this repo has now hit at four layers: the `ex:` register's
Assertions column, the vault's `fibo-iri-binding` mirror, `ccf-sdk`'s dumped
example fixtures, and here.

Each estate change breaks the deployed bundle silently — it keeps restoring,
and only the assertion fails, on someone else's laptop, later:

| date | change | landmark move |
|---|---|---|
| 2026-09-10 | Wave 21, UCC filings | 87,162 → 88,072 · 115 → 116 tables |
| 2026-09-12 | `public` schema count | was 2, had **never** matched the live 3 |
| 2026-09-13 | Wave 22, anchor re-key | 88,072 → 88,325 |

The `public` row is the instructive one: it was wrong from the day the guard
was written and nothing noticed, because a landmark that has never passed looks
exactly like one that is merely stale.

### The shape of the problem

- **A rebuild is a whole-estate operation.** `dump_all.sh` SSHes to db1, dumps
  five stores across two fabrics, ~377M. It is not something to run per commit.
- **The landmark is the only thing tying a bundle to an estate**, and it is
  hand-maintained in **four places** (`verify_install.py`,
  `restore_postgres.sh`, `restore_fluree.sh`, `manifest.py`).
- `validators/test_shipped_landmarks.py` catches the drift **in the repo**,
  which is the right place — but it only tells you the bundle is stale, not
  what the bundle should now say, and nothing stops a rebuild being deferred
  indefinitely.

### Options, not a decision

1. **Derive the landmarks from `MANIFEST.json`** rather than hand-editing four
   files, so a rebuild updates them by construction and a human cannot update
   one and miss three.
2. **Record an age rather than assert a value** — a restore reports "this
   bundle describes the estate as of `<t>`; the live estate is now `<t'>`"
   and warns rather than fails. A bundle is *supposed* to lag.
3. **Rebuild on a schedule** and accept staleness between runs, with the
   validator naming the delta so the decision to defer is visible.

Option 2 is the one consistent with how every other instance of this defect was
resolved this week — the vault's split precedence rule says *for counts the
ledger wins and neither document is authoritative*, and a bundle landmark is
exactly such a count.

### Standing debt right now

The deployed bundle at `/data/laptop` says **88,072**; the estate holds
**88,325**. A restore from it fails its own assertion today.
