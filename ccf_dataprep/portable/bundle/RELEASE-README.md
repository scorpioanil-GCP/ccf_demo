# CCF data estate — restore and connect

This folder holds a complete, restorable copy of the `ccf_dataprep` data
estate: five datastores across two fabrics, in one archive. Restoring it gives
you the same data the CCF SDK is built and evaluated against.

| File | What it is |
|---|---|
| `ccf-estate-bundle.tar` | The estate, about 390 MB |
| `SHA256SUMS` | Checksum of the archive |
| `README.md` | This file |

Four steps. Budget about an hour the first time, mostly package installs.

---

## 1 · Check and unpack

```bash
sha256sum -c SHA256SUMS          # macOS: shasum -a 256 -c SHA256SUMS
tar xf ccf-estate-bundle.tar
cd ccf-estate-bundle
```

If the checksum fails, download again. Don't restore from a damaged copy.

## 2 · Install the database engines

Follow the guide for your machine, **up to the "Restore" step**, then come back:

```bash
less INSTALL-ubuntu.md     # Ubuntu 22.04 or 24.04
less INSTALL-macos.md      # macOS — run `uname -m` first; Intel Macs use Docker for Fluree
```

| Engine | Version | Notes |
|---|---|---|
| Fluree | **4.2.4** | Intel Mac: the `fluree/server:4.2.4` Docker image |
| Postgres | **16** | Not 17: the dumps are version 16 archives. Homebrew: `postgresql@16` |
| MongoDB | **8.x** | Plus the separate `mongodb-database-tools` package |
| SQLite | any | Already on both platforms |
| Neo4j | 2026.07.x | **Optional** |

## 3 · Restore — one command

From inside `ccf-estate-bundle/`:

```bash
export NEO4J_PASSWORD='the-password-you-set'   # leave out to skip Neo4j
bash restore.sh
```

It checks every file in the bundle, restores all five stores, starts the
Fluree server, and runs the acceptance test, stopping at the first problem.
It is safe to re-run.

| Exit | Meaning |
|---|---|
| **0** | `Estate verified.` Done. |
| **1** | A check failed. It prints expected vs. found. |
| **2** | A store couldn't be reached. **An install problem, not a data problem.** A service isn't started, a password is wrong, or a port is closed. It names which store. |

On success it prints the exact `.env` lines for step 4.

Defaults work for a normal local install. Override only if you changed something:

| Variable | Default |
|---|---|
| `CCF_FLUREE_HOME` | `$HOME/ccf-fluree` (where the ledgers go) |
| `CCF_FLUREE_URL` | `http://127.0.0.1:8090` |
| `CCF_MONGO_URI` | `mongodb://127.0.0.1:27017` |
| `CCF_SQLITE_PATH` | `$HOME/ccf-data/departmental.sqlite` |
| `PGHOST` `PGPORT` `PGUSER` | standard Postgres variables; unset means local socket |

## 4 · Clone `ccf_dataprep` and point it at your machine

```bash
git clone git@github.com:drcastillo/ccf_dataprep.git
cd ccf_dataprep
uv sync
cp .env.example .env      # then paste in the lines restore.sh printed
```

Requires Python 3.12+. Ask the repository owner for access if the clone is refused.

> **The repository defaults to the original build host, `192.168.4.76`.**
> Until `.env` points everything at `127.0.0.1`, commands will hang against an
> address that means nothing on your network. The lines `restore.sh` prints
> do this, including the two easy-to-miss ones: `PGUSER` is **your** OS
> username, and `SQLITE_PATH` is where the restore actually wrote the file.

**Don't run the loaders** (`loaders/init_*.py` and friends). They build the
estate from sources and will overwrite what you just restored.

Check the repository sees your stores, then run the validators:

```bash
uv run validators/conditions.py
uv run --with pytest pytest validators/
```

Two results that look like failures but aren't:

- `validators/spec_coverage.py` exits **1** by design: it reports catalog
  rows that have no coverage manifest yet, rather than hiding them.
- The test suite **writes to Fluree**, adding commits without changing data.
  A rising ledger `t` after the tests is expected.

---

## If something goes wrong

| Symptom | Cause |
|---|---|
| Exit **2**, a store unreachable | That service isn't running, or a password/port is wrong |
| `MISSING: mongorestore` | `mongodb-database-tools` isn't installed; it's separate from the server |
| `pg_restore` version error | Postgres 17 installed instead of 16 |
| "something is already serving :8090" | Another Fluree is running. Stop it, or set `CCF_FLUREE_URL` to a free port |
| A repo command hangs | `.env` still points at `192.168.4.76` |

`PURGE.md` explains how to tear a restore down. **Read its first section
before running any of it.**

## What you have restored

| Store | Contents |
|---|---|
| **Fluree** `fibo-v2` | FIBO ontology and the typed relationship graph: 89,148 triples |
| **Postgres** `ccf_v2` | Obligors, facilities, exposures, covenants, signals |
| **MongoDB** `fibo_v2` | Filed documents and passages with character offsets |
| **SQLite** | The departmental store: restricted list, covenant tracker, workbooks |
| **Neo4j** | Graph-algorithm store (optional) |
| *peer fabric* | A second Postgres, Fluree and Mongo standing in for a syndicate co-lender |

Public data carries real identifiers from named public sources. Every internal
element is synthetic, labelled `synthetic — internal` or `synthetic — engineered`
(invented deliberately to create a condition public data would not supply).
