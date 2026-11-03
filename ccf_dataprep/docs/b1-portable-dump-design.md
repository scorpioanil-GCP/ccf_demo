# B1 · Portable dump and restore — design

**Status:** approved in outline 2026-08-27; awaiting spec review before planning.
**Deadline:** clean-macOS restore test on the evening of 2026-08-28.
**Backlog item:** `docs/backlog.md` §B1.

## Goal

Produce a physical extract of every datastore in the estate, on db1, under
`/data/laptop`, such that a clean macOS laptop with the five database engines
installed can be loaded from it and **proved correct by a script that ships
with the data**.

Dave's words, from the backlog: *install all the data stores on a laptop, load
all the data into them, and run the examples.* The deliverable is a **dump plus
a restore path**, not a re-derivation pipeline. Reproducibility (§B2) is a
separate and harder problem and is explicitly out of scope here.

## Decisions taken

| Question | Ruling | Who |
|---|---|---|
| Where do extracts live | `/data/laptop` on db1 (not the project folder) | Dave, 2026-08-27 |
| Is `./data` committed | No — gitignored, travels as a copied folder | Dave |
| v1 stores included | Yes, in their own `v1/` folder | Dave |
| v2 coverage | Both fabrics — primary and co-lender | Dave |
| Neo4j | Archive it | Dave |
| SQLite | Archive it | Dave |
| Repo on the laptop | Not required; verifier must stand alone | Dave |
| Target platforms | **macOS and Ubuntu** — two install guides, one restore code path | Dave, 2026-08-27 |
| Scope | Full B1: extracts + restore + install guide + verification | Dave |

## What was measured, 2026-08-27

Every figure below was taken live. The backlog's own sizing table is stale and
is corrected here.

### Fluree: the 47 GB is ~1,421 accumulated indexes

`/data/fluree/fibo-v2` is 47 GB, against 87,162 triples. It decomposes as:

| Component | Size | Files |
|---|---|---|
| `main/commit/` — the append-only chain | 27 MB | 4,468 (one per `t`) |
| `main/index/` — accumulated index generations | 46 GB | 27,034 |
| `@shared/dicts/` | 1.9 GB | 9,091 |

The cause is `reindex_min_bytes = 100` — *"bytes of novelty before a background
reindex (default ~ every commit)"*. Fluree writes a complete new index
generation on essentially every commit and never collects the superseded ones,
though `index/garbage/` records exactly which objects are dead.

**One current index, measured on a scratch copy: 47 MB, 18 files, 1.5 s to
build.** Queries go from 354 ms (no index) to 644 us (indexed) — 550x. The
ledger is carrying roughly a thousand copies of its own index.

This is a live operational issue on db1 independent of B1: `fibo-v2` grows by
roughly 33 MB per commit indefinitely. Recorded, not acted on — reclaiming it
touches the authoritative ledger and is Dave's call.

### Fluree round-trip is verified, byte for byte

A scratch Fluree served from **the 27 MB commit chain alone** — no index, no
dicts — reproduced the ledger exactly:

| | live | rebuilt from commits |
|---|---|---|
| head `t` | 4468 | 4468 |
| triples | 87,162 | 87,162 |
| content sha256 | `7d6007c7577a15b7` | `7d6007c7577a15b7` |

Compared **as a set**, not counted — `loaders/dump_fluree.py`'s existing rule,
because a dump with the right number of wrong lines is precisely what a
count-based check cannot see.

### The archive format to use is `.flpack`

`fluree export --format ledger` produces a `.flpack` carrying commits and
index artifacts, restored by `fluree create --from <file>.flpack`. Measured:

| Artifact | Size | Note |
|---|---|---|
| `.flpack` with indexes | **69 MB** | fast on arrival, no post-restore step |
| `.flpack --no-indexes` | 19 MB | needs `fluree index` (1.5 s) before use |
| raw commit directory | 27 MB | works, but not the supported path |
| N-Triples | 12 MB | **requires an index to export at all** |

**Chosen: `.flpack` with indexes.** One file, the vendor's own format, correct
immediately.

### Corrections to earlier claims in this project

1. **`fluree history` works.** It returns per-`t` change records with a working
   `--from/--to` range, including from a commit-only store. An earlier reading
   in this design process said as-of did not exist on this build; that was true
   only of the HTTP endpoints (`/v1/fluree/history` is 404, and the `t` query
   parameter is silently ignored — on the live server too) and was wrongly
   generalised. Time travel survives the dump.
2. **Indexes are persistable and shippable.** An earlier reading implied
   otherwise. They persist fine; the 46 GB is bloat from generation
   accumulation, not the cost of one index.
3. **`ccf_v2` is 718 MB across 113 `BASE TABLE`s** (unfiltered `information_schema.tables` also counts 2 views), not the 68 MB / 62 tables the
   backlog records from 2026-08-22 — roughly 10x growth.
4. **Neo4j holds v1 data, not v2.** 14 nodes, 16 relationships, labels
   `KGEntity` / `Corporation` / `Party` / `Address`. The only writer in the
   repo is `docs/fibo_files/load_neo4j.py`; no v2 loader touches it. It
   therefore belongs in `v1/`.

### Current sizes, all stores

| Fabric | Store | Content | Raw size |
|---|---|---|---|
| v1 | Fluree `fibo` | t=5 | 812 KB |
| v1 | Postgres `public` | 2 tables | 160 KB |
| v1 | MongoDB `fibo` | 30 docs | <1 MB |
| v1 | Neo4j `neo4j` | 14 nodes / 16 rels | 1.2 MB graph |
| v2 primary | Fluree `fibo-v2` | t=4468, 87,162 triples | 69 MB as `.flpack` |
| v2 primary | Postgres `ccf_v2` | 113 `BASE TABLE`s (+2 views) | 718 MB |
| v2 primary | MongoDB `fibo_v2` | 38,238 docs, 6 collections | 576 MB data |
| v2 primary | SQLite departmental | 8 tables | 102 KB |
| v2 peer | Fluree `bofa/syndicate` | t=16 | small |
| v2 peer | Postgres `colender` schema | 2 tables | 64 KB |
| v2 peer | MongoDB `bofa_syndicated` | **0 collections** | 0 |

### Engine versions — the two fabrics differ

| | primary (db1 host) | peer (docker) |
|---|---|---|
| Fluree | 4.1.4 | **4.1.6** |
| MongoDB | 8.0.29 | **8.2.12** |
| Postgres | 16.15 | 16.15 |
| Neo4j | 2026.07.1 | — |

The laptop needs one Fluree binary that reads both archives. This must be
**tested, not assumed**, before the laptop night.

## Layout

```
/data/laptop/
  MANIFEST.json          per artifact: source, method, timestamp, bytes, sha256
  README.md              start here; restore order, then points at your platform
  INSTALL-macos.md       Homebrew, pinned
  INSTALL-ubuntu.md      apt + PGDG, pinned
  verify_install.py      the standalone acceptance test
  v1/
    fluree-fibo.flpack
    postgres-public.dump
    mongo-fibo/
    neo4j-v1.cypher
  v2/
    primary/
      fluree-fibo-v2.flpack
      postgres-ccf_v2.dump
      mongo-fibo_v2/
      departmental.sqlite
    colender/
      fluree-bofa-syndicate.flpack
      postgres-colender.dump
      mongo-bofa_syndicated/
  restore/
    restore_all.sh       orchestrator, ordered
    restore_fluree.sh    restore_postgres.sh  restore_mongo.sh
    restore_sqlite.sh    restore_neo4j.sh
    platform.sh          the only file that knows macOS from Ubuntu
```

## Method per store

| Store | Dump | Restore |
|---|---|---|
| Fluree | `fluree export --format ledger` | `fluree create --from *.flpack` |
| Postgres | `pg_dump -Fc` per schema | `pg_restore` |
| MongoDB | `mongodump --db <name> --gzip` | `mongorestore --gzip` |
| SQLite | `VACUUM INTO` | file copy |
| Neo4j | Cypher script via the bolt driver | `cypher-shell` replay |

Dumps run **on db1**: `pg_dump` and `mongodump` exist there and are absent on
the workstation.

**Two stores are not on db1 and need an explicit hop.** SQLite lives on the
workstation at `data/departmental.sqlite`; it is snapshotted with `VACUUM INTO`
— never `cp`, which can capture a torn write on a live file — and the snapshot is
then copied to `/data/laptop`. The **peer Fluree runs inside the `fluree-demo`
container**, so its export runs via `docker exec` and the archive is copied out;
the peer MongoDB is likewise a separate `mongod` on port 27018, not the host
instance.

### The MongoDB scoping rule is enforced in code

db1's MongoDB also carries `rtdetect`, roughly 5.5 M documents of an unrelated
live system. Every dump and restore names its database explicitly. The scripts
**refuse to run** without an explicit `--db`, and refuse any name not on a
declared allowlist. This is a guard in the script, not a comment above it —
`ccf/config.py` already takes this position for the same host and the same
reason.

## The verifier — `verify_install.py`

The deliverable Dave asked for: *a test to run in python on the laptop that
confirms a successful installation.*

**Standalone.** No repo import. Only DB drivers, declared inline as PEP 723
script metadata so `uv run --no-project verify_install.py` resolves them, with a documented
`pip install` fallback.

**Falsifiable, which is the whole point.** A checker that passes because it
looked at nothing is this project's most-recorded defect class. So:

- It asserts **landmark values**, not liveness: `t = 4468`; 87,162 triples;
  113 `BASE TABLE`s in `ccf_v2`; 38,238 documents across 6 collections; 8 SQLite
  tables; 14 Neo4j nodes and 16 relationships; named rows that must exist.
- It asserts **cross-store joins resolve** — the LEI <-> `internal_client_id`
  crosswalk is the estate's correlation key, and five stores that each load
  cleanly but do not join is exactly the failure this project was warned about
  from the start.
- It asserts the **fabric boundary**: the peer's stores are reachable and
  distinct, and no peer-owned row sits in a primary store.
- Every check reports the value it found next to the value it required, so a
  pass is legible as evidence rather than as a green tick.

**It must be proved able to fail.** Before shipping, the verifier is run
against deliberately damaged restores — a dropped table, a truncated
collection, a ledger restored without its last commits, a swapped SQLite file.
Each must produce a specific, named failure. A verifier not tested against a
broken restore is decoration; on this estate that has happened often enough to
be a memory entry.

**Env-driven targets.** Connection settings and namespace names are read from
the environment with laptop defaults, so the same file verifies the scratch
restore on db1 (where namespaces are suffixed to avoid collision with the live
estate) and the laptop restore, unchanged. A verifier that only ever runs
against its final target gets its first real exercise on the night it matters.

**Exit codes:** 0 all green; 1 one or more checks failed; 2 could not connect.
A connection failure must never be reported as a data failure.

## Install guides — two platforms, one restore path

A clean **macOS** machine (Dave, 2026-08-28) and a clean **Ubuntu** machine (a
second person). These differ in how the engines are installed and supervised.
They do not differ in how the data is restored.

**So the restore logic exists once.** `restore/platform.sh` is the only file
that branches: it detects the OS, resolves tool paths, and normalises the
handful of commands that genuinely differ. Every `restore_*.sh` sources it and
is otherwise identical on both. Two parallel script sets would drift, and only
the one someone happened to run would ever be exercised.

### What actually differs

| Concern | macOS | Ubuntu |
|---|---|---|
| Package manager | Homebrew | apt (PGDG for Postgres, MongoDB's own repo) |
| Postgres binaries | `/opt/homebrew/opt/postgresql@16/bin` | `/usr/lib/postgresql/16/bin` |
| Service control | `brew services start` | `systemctl start` |
| SHA-256 | `shasum -a 256` | `sha256sum` |
| Fluree binary | darwin build | linux build |
| SQLite | ships with the OS | `apt install sqlite3` |

`readlink -f` and `sed -i` also differ between BSD and GNU userland. The scripts
avoid both rather than branching on them — a portability bug in a restore script
surfaces as a corrupted restore, not as an error.

### Pinned versions, both platforms

| Engine | Install as | Why pinned |
|---|---|---|
| Fluree | **4.1.6** | Reads both fabrics' archives; verified 2026-08-27 |
| Postgres | **16** (`postgresql@16` / PGDG `postgresql-16`) | `pg_restore` from 17 against a 16 dump is a hard failure, and both default package names give the latest |
| MongoDB | **8.x** + `mongodb-database-tools` | `mongorestore` is a separate package on both platforms and is easy to miss |
| Neo4j | **2026.07.x** | Only to match the source; the Cypher export is not version-bound |
| SQLite | 3.4x | Present on macOS; `apt install` on Ubuntu |

### Restore order

**Fluree → Postgres → MongoDB → SQLite → Neo4j**, then `verify_install.py`.
The stores are independent of each other, but the verifier's join checks need
Postgres and Fluree both present.

### The Ubuntu path gets tested first, for free

db1 is Ubuntu 24.04. The scratch-namespace restore that acceptance criterion 2
requires therefore **is** the Ubuntu rehearsal — the Linux branch of every
script runs there before either machine is touched. Only the macOS branch is
first exercised on the night, and it is the smaller half.

## Acceptance

1. Every artifact present under `/data/laptop`, with a `MANIFEST.json` entry
   carrying its sha256.
2. Every dump restores into scratch namespaces on db1 and is verified there
   before the laptop night — a dump proved only on the target is proved too
   late.
3. `verify_install.py` passes against the restored scratch namespaces.
4. `verify_install.py` **fails**, specifically and by name, against each
   deliberately damaged restore.
5. ~~A `.flpack` written by Fluree 4.1.4 is confirmed importable by whichever
   binary the laptop will run.~~ **Done 2026-08-27** — see Risks.
6. The backlog's stale sizing table and the `known-issues` record are corrected.
7. The Linux branch of every restore script is exercised on db1 (Ubuntu 24.04)
   before the laptop night; the macOS branch is exercised on the night.

## Risks

| Risk | Mitigation |
|---|---|
| ~~Fluree 4.1.4 archive unreadable by 4.1.6~~ | **RETIRED 2026-08-27.** Tested: a 4.1.4 `.flpack` (69 MB, 100 index artifacts) imports into 4.1.6 keeping `t=4468`, all 100 index artifacts, and 677 us query time. N-Triples from both stores are identical as a set (sha256 `2cb32316d302c3b7`). **The laptop installs Fluree 4.1.6 and reads both fabrics' archives.** |
| Homebrew installs Postgres 17 | Pin `postgresql@16` in the README, and have the verifier report the server version it found |
| ~~Neo4j major-version dump incompatibility~~ | **DESIGNED OUT 2026-08-27.** `neo4j-admin database dump` refuses a running database (verified), so it would mean stopping Neo4j on db1, and its archive is major-version-bound. The graph is 14 nodes and 16 relationships, so it is exported as a **Cypher script** instead: no service stop, no version binding, human-readable, diffable |
| Peer MongoDB is empty | Dump anyway, record `"empty": true` in the manifest, so a later reader does not mistake it for a failed dump |
| Verifier passes on a partial restore | Damaged-restore tests are acceptance criterion 4, not an optional extra |
| A restore script works on Ubuntu and silently misbehaves on macOS | One code path with a single `platform.sh`; avoid `sed -i` and `readlink -f` entirely rather than branching on them |
| `mongorestore` missing — it is not in the MongoDB server package | `mongodb-database-tools` named explicitly in both install guides; the verifier checks for the binary before blaming the data |

## Rehearsal, 2026-08-27

Full Ubuntu rehearsal on db1 (Task 9). Every store in `/data/laptop`
restored into scratch namespaces — `b1chk` throughout — and proved with
the verifier, the damaged-restore suite, and a byte-for-byte script check.

**Neo4j was not skipped.** The original plan (Task 7) deferred Neo4j
because its restore Cypher opens with `MATCH (n) DETACH DELETE n` and the
only reachable Neo4j on the network is the live source graph. Instead of
skipping it again, a **throwaway Neo4j 2026.07.1 container** (matching the
live server's major version exactly) was stood up in Docker on db1, on
non-default ports (7688 bolt / 7475 http) with its own volume. The
bundle's own unmodified `restore_neo4j.sh` was replayed against it and
landed 14 nodes / 16 relationships / 0 `_B1` scaffolding nodes — the
first time this script has ever been executed against anything. The
container, its volume, and the pulled image were all removed afterward and
confirmed gone; the live Neo4j graph was queried before and after and
never touched (14 nodes / 16 relationships throughout).

**Verifier result: 20/20 checks passed, exit 0, nothing skipped.**
`uv run --no-project verify_install.py` against the full scratch estate
(scratch Postgres `b1chk_pg`/`b1chk_peer_pg` under the `postgres` role;
throwaway `mongod` on 27019 holding `fibo_v2`/`fibo`; a scratch Fluree
project + its own server on 8095 holding all three ledgers; a local scratch
SQLite copy; the throwaway Neo4j container) printed `Estate verified.` —
the honest, unqualified line the verifier only prints when no store was
skipped. This is a stronger result than planned: the original Task 9 brief
expected Neo4j to read as "unreachable-or-skipped."

**Damaged-restore suite: all four named failures fired.**
`portable/tests/damaged_restore.sh` ran unmodified against the scratch
namespaces: dropped Postgres table (113→112 tables), truncated Mongo
collection (38238→37989 docs), swapped-in empty SQLite file (8→1 tables),
and Postgres rows deleted without a table drop (crosswalk 53→48) — each
produced its own specific `FAILED:` line, never a bare non-zero exit, and
the baseline verified green again afterward.

**Shipped scripts match the repo, byte for byte.** sha256 of every file in
`/data/laptop/restore/` plus `verify_install.py`, compared against the
repo copies, first 16 hex characters of each digest shown (full sha256sum
is what actually ran):

| file | repo | bundle |
|---|---|---|
| `platform.sh` | `5100876737de43dd` | `5100876737de43dd` |
| `restore_all.sh` | `1642297b308a3e57` | `1642297b308a3e57` |
| `restore_fluree.sh` | `aeca5ab9c8de7635` | `aeca5ab9c8de7635` |
| `restore_mongo.sh` | `6f622f894fda8754` | `6f622f894fda8754` |
| `restore_neo4j.sh` | `2df26a781e89c54f` | `2df26a781e89c54f` |
| `restore_postgres.sh` | `b4927c75998674f6` | `b4927c75998674f6` |
| `restore_sqlite.sh` | `64f358f71cfbb7a4` | `64f358f71cfbb7a4` |
| `verify_install.py` | `a67f6ec3d3d717c2` | `a67f6ec3d3d717c2` |

All 8 pairs match. No drift between what was designed and what ships.

**Teardown confirmed complete:** scratch Postgres databases dropped
(`select datname ... like 'b1chk%'` → empty), scratch mongod (27019) and
Fluree server (8095) both stopped and unlistening, the Neo4j container/
volume/image all removed, and every staged helper file and credential
file (`~/.pgpass_b1chk`, `~/.neo4j_b1chk_env`, `~/b1chk-work`) removed from
db1.

**Live estate reconfirmed untouched afterward**, queried directly against
the live endpoints (not read from a manifest): Fluree `fibo-v2` t=4468 /
87,162 triples, `fibo` t=5, peer `bofa/syndicate` (port 8091) t=16 / 10
triples; Postgres `ccf_v2` 113 `BASE TABLE`s / `legal_entity` 156 rows /
`crosswalk` 53 rows / 0 orphan LEIs, `public` 2 tables, peer `colender`
schema 2 tables; MongoDB `fibo_v2` 6 collections / 38,238 docs, `fibo` 2
collections / 30 docs; SQLite 8 tables; Neo4j 14 nodes / 16 relationships;
`/data/laptop/dave.txt` unchanged. `rtdetect` (named explicitly, never
enumerated) is intact at 104 collections / 7,062,417 documents.

**What did not work first time:** `fluree` and `cypher-shell` are not on
db1's default `PATH` in a non-interactive `ssh` session (full paths were
needed); `fluree server stop` must be run from the Fluree project
directory that started the server, not an arbitrary one. Neither is a
bundle-script defect. Full detail, including one disclosed mistake (a
`env | grep` during setup that incidentally printed a peer-Mongo URI
containing its password), is in
`.superpowers/sdd/b1-portable-dump-plan/task-9-report.md`.

**Not exercised:** a truncated/corrupted Fluree archive as a
damaged-restore case (same CLI limitation recorded in Task 7 — no
time-travel flag on either the export or import side); a Neo4j-specific
case inside `damaged_restore.sh` itself (that script has no such case by
design — Neo4j's restore correctness was instead proven directly against
the throwaway container, a stronger check for that one script).

Acceptance criteria 2, 3, and 7 are satisfied. Only the macOS branch of the
restore path remains to be exercised, on the night of 2026-08-28.
