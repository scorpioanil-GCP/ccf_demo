# portable/ — the laptop-portable dump

Builds a self-contained, offline-restorable copy of the whole ccf_dataprep
estate (both fabrics, all five stores) for a machine with no access to
db1 or the peer container. See `docs/b1-portable-dump-design.md` for the
design, and `docs/b1-portable-dump-plan.md` / `.superpowers/sdd/b1-portable-dump-plan/`
for how it was built, task by task.

**This file is for people working on this repo.** The bundle itself ships
its own docs — `bundle/README.md`, `bundle/INSTALL-macos.md`,
`bundle/INSTALL-ubuntu.md` — written for someone restoring on a clean
machine with no repo checkout at all.

## Layout

```
portable/
  dump/            runs to BUILD the bundle
    common.sh                shared shell helpers (BUNDLE_ROOT, ccf_log, ...)
    dump_all.sh               the orchestrator — run this one
    dump_fluree.sh  dump_postgres.sh  dump_mongo.sh   run ON db1 (via ssh)
    dump_sqlite.sh  dump_neo4j.py                       run on THIS workstation
    run_db1_dumps.sh           staged to db1; chains the three db1-side dumps
    stage_bundle_files.sh      staged to db1; copies restore/ + docs into the bundle
    build_manifest.py          staged to db1; builds MANIFEST.json with bare python3
    package_release.sh         workstation; turns the built bundle into the hand-out tar
  restore/         ships INSIDE the bundle — restores it elsewhere
    restore_all.sh             orchestrator, ordered: fluree, postgres, mongo, sqlite, neo4j
    restore_fluree.sh  restore_postgres.sh  restore_mongo.sh
    restore_sqlite.sh  restore_neo4j.sh
    platform.sh                the ONLY file that knows macOS from Ubuntu
  bundle/          ships INSIDE the bundle — docs for the restorer
    restore.sh                 the one command: check, restore, start Fluree, verify
    verify_bundle.sh           hashes every artifact against MANIFEST.json
    README.md  INSTALL-macos.md  INSTALL-ubuntu.md  PURGE.md
    RELEASE-README.md          ships BESIDE the tar, as its README.md
  manifest.py       shared by dump_all.sh's build step AND the shipped bundle
  verify_install.py  ships INSIDE the bundle — standalone acceptance test
  tests/            pytest, exercised against portable/ code (not against a
                    live estate — these run with no ssh, no db1, no bundle)
```

## Building the bundle

```bash
bash portable/dump/dump_all.sh
```

**Runs on your workstation, not on db1.** db1 has no repo checkout and no
`uv` — bare python3 3.12.3 only. `dump_all.sh` stages `portable/` there over
rsync, ssh-runs the three db1-side dumps from that staged copy, runs the two
workstation-side dumps locally (they ship their own output up), and builds
`MANIFEST.json` on db1 with bare python3 against the staged tree.

Requires passwordless ssh to `parkave@192.168.4.76` and the peer Postgres /
peer MongoDB credentials already exported in **this workstation's own**
shell startup (`~/.bashrc`) — `PGPASSWORD`, `CO_LENDER_PG_USER`,
`CO_LENDER_PG_DB`, `CO_LENDER_PG_PASSWORD`, `CO_LENDER_MONGO_URI`. db1 has no
such block; `dump_all.sh` forwards these itself, via a chmod-600 temp file
that never appears in a printed command and is deleted from both ends
immediately after use — never a literal secret inlined into an ssh
invocation.

Then package it for hand-out:

```bash
bash portable/dump/package_release.sh     # -> ~/ccf-dist/{ccf-estate-bundle.tar,SHA256SUMS,README.md}
```

It streams the tar off db1 without `.scripts/`, `.ledger-t.json` or
`laptop-loader.sh`, then unpacks its own output and runs `verify_bundle.sh`
on the copy before calling it done. The recipient gets three files and runs
one command, `bash restore.sh`.

**Idempotent.** Safe to re-run in full. `dump_sqlite.sh` snapshots the *live*
workstation SQLite file with `VACUUM INTO`, ships it, and because it runs
outside `dump_all.sh`'s db1-side stage, you re-run `dump_all.sh` afterward
so the manifest step picks the SQLite artifact up (11 artifacts total; a
manifest built before the SQLite ship reports 10, with `MISSING:` for it).

## Testing

```bash
uv run --with pytest pytest portable/tests -q
```

**Not bare `uv run pytest`** — `pytest` isn't a project dependency, so a bare
`uv run pytest` silently falls back to whatever `pytest` happens to be on
`$PATH` (a global install, missing `psycopg`/`pymongo`/`neo4j`), and four
tests fail with `ModuleNotFoundError` that has nothing to do with the code
under test. `--with pytest` runs it inside the project's own resolved
environment instead.

## Store credentials and env vars, cheat sheet

| Var | Read by | Default |
|---|---|---|
| `PGHOST` / `PGPORT` / `PGUSER` / `PGPASSWORD` | `dump_postgres.sh` (primary) | `192.168.4.76:5432`, `parkave` |
| `CO_LENDER_PG_*` | `dump_postgres.sh` (peer) | none — required |
| `MONGO_URI` | `dump_mongo.sh` (primary) | `mongodb://192.168.4.76:27017` |
| `CO_LENDER_MONGO_URI` | `dump_mongo.sh` (peer) | none — required |
| `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` | `dump_neo4j.py` | `bolt://192.168.4.76:7687`, `neo4j` |
| `FLUREE_BIN` / `LIVE_STORAGE` | `dump_fluree.sh` | `/home/parkave/bin/fluree-42`, `/data/fluree-42/storage` |
| `SQLITE_SRC` / `SQLITE_OUT` | `dump_sqlite.sh` | `data/departmental.sqlite`, `.b1-staging/` |
| `REMOTE` / `REMOTE_SCRIPTS` | `dump_all.sh` | `parkave@192.168.4.76`, `$BUNDLE_ROOT/.scripts` |
| `BUNDLE_ROOT` | everything on the db1 side | `/data/data_bundle` |

## `/data/data_bundle` is a symlink

It points at `/data/mongodb/data_bundle`. `find` / `du` need `-L`. It has also held
a user file, `dave.txt`, which is not ours to touch — absent when last checked
(2026-09-23), and `laptop-loader.sh` excludes it either way.

## MongoDB never gets enumerated

db1's MongoDB also carries `rtdetect`, an unrelated live system — measured
twice at 7,062,417 documents (2026-08-27), not the ~5.5M once assumed here.
Every dump/restore names its database explicitly, and
`portable/manifest.py`'s `ALLOWED_MONGO_DBS` allowlist (mirrored in
`restore_mongo.sh` as a `case` pattern the test suite checks stays in sync)
refuses anything else.
