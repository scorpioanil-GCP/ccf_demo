# CCF data estate — restore and connect

The financial-services Context Product examples rely on the shared data ecosystem,
which combines public source data with engineered synthetic internal data.
This folder contains restoration instructions and the archive checksum. The
377 MB archive is distributed separately through a permission-controlled
Google Drive location; it is not committed to this repository.

## Obtain the data bundle first

1. Contact the repository owner, David Castillo, for the Google Drive link to
   `ccf-estate-bundle.tar`.
2. Request access using the Google account you will use to download it. Wait
   for access to be granted before continuing.
3. Download the archive and place it beside this folder's `SHA256SUMS`, or
   copy that checksum file into your download directory.
4. Continue with Phase 0 below. Verify the archive and its 19 artifacts before
   restoring any database.

The private download URL is supplied by the owner. Access to the GitHub
repository does not automatically grant access to the Google Drive bundle.
Restoring the archive supplies the estate used by the examples; each example's
README supplies any additional local fixtures, producer processes and settings.

| File | What it is |
|---|---|
| `ccf-estate-bundle.tar` | Download separately — 377 MB, 19 artifacts |
| `SHA256SUMS` | Checksum of the archive above |
| `README.md` | This file |

There are three phases, in this order. Each depends on the one before.

1. **Install the database engines** — Postgres, MongoDB, Fluree, SQLite, and
   optionally Neo4j.
2. **Restore the data** into them from the bundle.
3. **Clone `ccf_dataprep`** and point it at your local stores.

Budget roughly an hour for a first run, most of it waiting on package installs.

---

## Phase 0 · Check the download before you unpack it

A 377 MB transfer can truncate without any visible error. Check it first:

```bash
sha256sum -c SHA256SUMS
tar xf ccf-estate-bundle.tar
cd ccf-estate-bundle
bash verify_bundle.sh
```

`verify_bundle.sh` re-hashes all 19 artifacts against the manifest that
shipped with them. It must print `19 checked, 0 bad`. If it doesn't, stop —
download it again rather than restoring from a damaged copy.

It also prints the Fluree commit counts you should see after the restore.
Note them; on one platform path they are the only check you get.

---

## Phase 1 · Install the database engines

The bundle carries its own platform-specific guides. **Follow the one for your
system, then come back here.**

```bash
less INSTALL-ubuntu.md     # Ubuntu 22.04 or 24.04
less INSTALL-macos.md      # macOS, Apple silicon or Intel
```

Use the supported estate baseline below. The supplied Postgres restore instructions
target version 16; this table does not establish compatibility with other versions.

| Engine | Pinned to | Notes |
|---|---|---|
| Postgres | **16** | Use the versioned package `postgresql@16` when following the macOS guide. |
| MongoDB | **8.x** | `mongorestore` is in a *separate* package, `mongodb-database-tools`. |
| Fluree | **4.2.4** | Follow the platform-specific installation path using the current SDK pin. |
| SQLite | any | Already present on both platforms. |
| Neo4j | 2026.07.x | **Optional** — see "Skipping Neo4j" below. |

> **On macOS, run `uname -m` first.** `arm64` follows the guide straight
> through. `x86_64` branches at Fluree and again at the restore step.

---

## Phase 2 · Restore the data

Configure the endpoints and credentials explicitly for the stores you installed. The table records the original bundle defaults for troubleshooting; it does not prescribe current host ports. Check each restore script against the bundle you downloaded.

### Variables the restore reads

| Variable | Original bundle default | Override when… |
|---|---|---|
| `CCF_FLUREE_URL` | `http://127.0.0.1:8090` | Fluree is on another port |
| `CCF_FLUREE_HOME` | `$HOME/ccf-fluree` | you want ledgers elsewhere |
| `CCF_MONGO_URI` | `mongodb://127.0.0.1:27017` | Mongo is elsewhere |
| `CCF_SQLITE_PATH` | `$HOME/ccf-data/departmental.sqlite` | you want the file elsewhere |
| `CCF_PGDATABASE` | `parkavedb` | you want a different database name |
| `CCF_CO_LENDER_PGDATABASE` | `bofa_syndicated` | ditto, for the peer fabric |
| `NEO4J_URI` | `bolt://127.0.0.1:7687` | Neo4j is elsewhere |
| `NEO4J_USER` | `neo4j` | you use another role |
| `NEO4J_PASSWORD` | — | **always** (no default; `CCF_NEO4J_PASSWORD` also accepted) |

**Postgres host, port and user are not `CCF_` variables.** The restore calls
`psql`, `createdb` and `pg_restore` with no connection flags, so they follow
the standard libpq variables — `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD` — or
your local socket defaults. Set them explicitly for the intended restore destination. Restore credentials need the permissions required to restore the data; use separate read-only roles when running SDK examples.

### Run it

```bash
# Replace every placeholder with the endpoint/credential chosen at installation.
export CCF_FLUREE_URL='http://127.0.0.1:<fluree-port>'
export CCF_MONGO_URI='mongodb://127.0.0.1:<mongo-port>'
export PGHOST='127.0.0.1' PGPORT='<postgres-port>'
export PGUSER='<restore-user>' PGPASSWORD='<restore-password>'
export NEO4J_URI='bolt://127.0.0.1:<neo4j-port>'
export NEO4J_PASSWORD='the-password-you-set-during-install'
export CCF_FLUREE_HOME="$HOME/ccf-fluree"

bash restore/restore_all.sh
```

It restores Fluree, Postgres, MongoDB, SQLite and Neo4j in that order, and
prints an expected-vs-found count after each, so a bad restore stops there
rather than surfacing later as a confusing verification failure.

### Start the Fluree server

`restore_all.sh` creates the ledgers but deliberately leaves no server
running. The verifier needs one. Use the same host port as `CCF_FLUREE_URL`, replacing the placeholder before running:

```bash
( cd "$CCF_FLUREE_HOME" && nohup fluree server start --listen-addr "127.0.0.1:<fluree-port>" \
    > /tmp/fluree-server.log 2>&1 & )
sleep 3
```

*(Intel Mac: skip this — your Fluree is already running in its container.)*

### Verify

```bash
uv run --no-project verify_install.py
```

Always pass `--no-project`. Read the exit code:

| Exit | Meaning |
|---|---|
| **0** | `Estate verified.` Done. |
| **1** | A check failed. It prints required vs. found. |
| **2** | A store was unreachable — **an install problem, not a data problem.** A service isn't started, a password is wrong, or a port is closed. It names which store. |

### Skipping Neo4j

Neo4j is optional — it holds no data the other four don't. To skip it, run the
restores individually rather than `restore_all.sh`, which has no skip logic:

```bash
for s in fluree postgres mongo sqlite; do bash restore/restore_$s.sh; done
CCF_SKIP_STORES=neo4j uv run --no-project verify_install.py
```

`CCF_SKIP_STORES` takes a comma-separated list (`fluree`, `postgres`, `mongo`,
`sqlite`, `neo4j`) and is understood by the **verifier only**.

---

## Phase 3 · Clone `ccf_dataprep` and point it at your restore

The repository holds the generators, loaders and validators. You need it to
run anything against the estate you just restored.

```bash
git clone git@github.com:drcastillo/ccf_dataprep.git
cd ccf_dataprep
uv sync
```

Requires Python 3.12 or newer. Ask the repository owner for access if the
clone is refused.

### ⚠ The repository uses DIFFERENT variable names from the bundle

This is the single most common thing to get wrong. The bundle's restore
scripts read `CCF_`-prefixed variables that default to **localhost**. The
repository reads *unprefixed* variables that default to **the original build
host, `192.168.4.76`** — a machine you cannot reach and should not try to.

Leave them at their defaults and every command will hang or fail against an
address that means nothing on your network.

| Concept | Bundle (restore) | Repository (`ccf/config.py`) |
|---|---|---|
| Fluree endpoint | `CCF_FLUREE_URL` | `FLUREE_URL` |
| Mongo endpoint | `CCF_MONGO_URI` | `MONGO_URI` |
| SQLite file | `CCF_SQLITE_PATH` | `SQLITE_PATH` |
| Postgres database | `CCF_PGDATABASE` | `PGDATABASE` |
| Postgres host | `PGHOST` (libpq) | `PGHOST` |
| Neo4j password | `NEO4J_PASSWORD` | `NEO4J_PASSWORD` |

### Write your `.env`

```bash
cp .env.example .env
```

Then edit it so every endpoint points at your own machine:

```bash
FLUREE_URL='http://127.0.0.1:<fluree-port>'
PGHOST=127.0.0.1
PGPORT='<postgres-port>'
PGDATABASE=parkavedb
PGUSER=<your-os-username>
PGPASSWORD=
MONGO_URI='mongodb://127.0.0.1:<mongo-port>'
NEO4J_URI='bolt://127.0.0.1:<neo4j-port>'
NEO4J_USER=neo4j
NEO4J_PASSWORD=the-password-you-set-during-install
SQLITE_PATH=/home/<you>/ccf-data/departmental.sqlite
```

Two details that cause silent trouble:

- **`PGUSER` is your own OS username**, not `parkave`. Both install guides
  create a Postgres role matching your OS user.
- **`SQLITE_PATH` must match where the restore actually put the file.** The
  repository defaults to `./data/departmental.sqlite` *inside the clone*; the
  restore writes to `$HOME/ccf-data/departmental.sqlite`. Point the repository
  at the restored file, or copy it into the clone. If they disagree you get a
  working estate with an empty departmental store, and nothing announces it.

The remaining keys in `.env.example` — `SEC_USER_AGENT`, `FRED_API_KEY`,
`COMPANIES_HOUSE_API_KEY` — are only used to *fetch* public data when building
the estate from scratch. Restoring needs none of them; leave them blank.

### ⚠ Do not run the loaders

The repository's own README describes a setup that **builds** the estate:
`uv run loaders/init_sqlite.py`, `init_fluree.py`, and the rest. Those are for
constructing an estate from sources, not for restoring one.

You have already restored. Running them will overwrite what you restored.

### Confirm the repository can see your estate

```bash
uv run python - <<'PY'
from ccf.config import pg_connect, mongo_db
from ccf import fluree

with pg_connect() as c, c.cursor() as cur:
    cur.execute("SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema='ccf_v2' AND table_type='BASE TABLE'")
    print("postgres ccf_v2 tables :", cur.fetchone()[0], "  (expect 116)")

print("mongo fibo_v2 passages :",
      mongo_db(write=False).passage.count_documents({}), "  (expect 37,865)")
print("fluree fibo-v2 ledger t:", fluree.ledger_t())
PY
```

All three must answer from **your** machine. If any of them hangs, an endpoint
in `.env` is still pointing at `192.168.4.76`.

### Run the validators

```bash
uv run validators/conditions.py          # every '>= N' condition the specs require
uv run validators/spec_coverage.py       # each store holds the elements its spec names
uv run --with pytest pytest validators/  # the full suite
```

Use `uv run --with pytest pytest`, not a bare `uv run pytest`.

Two expected results that are **not** failures:

- `spec_coverage.py` exits **1**, and that is the correct result. Of 282
  catalog rows across 21 products it accounts for 144: eleven products have
  no coverage manifest yet, and ten mapped rows are real, named absences in
  the data. The exit code reports that rather than hiding it — a gap is never
  waived to make the run green.
- The validator suite **writes to Fluree**. One test re-runs a loader, adding
  46 commits per run without changing any data. A rising ledger `t` after
  running the tests is expected and is not drift.

---

## If something goes wrong

| Symptom | Cause |
|---|---|
| Verifier exits **2** | A store isn't running, or a password/port is wrong. Not a data problem. |
| A command hangs for a long time | An endpoint still points at `192.168.4.76`. Check `.env`. |
| `pg_restore` version error | Postgres 17 installed instead of 16. |
| `MISSING: mongorestore` | The database-tools package wasn't installed — it is separate from the server. |
| `MISSING: fluree` on an Intel Mac | Expected. That path uses Docker; see `INSTALL-macos.md`. |
| Departmental checks pass but the data looks empty | `SQLITE_PATH` disagrees with where the restore wrote the file. |

`PURGE.md` in the bundle explains how to tear a restore down and start clean.
**Read its first section before running any of it** — the laptop database and
the original estate share a name, and only the host distinguishes them.

---

## What you have restored

| Store | Contents |
|---|---|
| **Fluree** `fibo-v2` | FIBO ontology and the typed relationship graph — 88,325 triples |
| **Postgres** `ccf_v2` | 116 tables: obligors, facilities, exposures, covenants, signals |
| **MongoDB** `fibo_v2` | Filed documents and 37,865 passages with character offsets |
| **SQLite** | The departmental store — restricted list, covenant tracker, workbooks |
| **Neo4j** | Graph-algorithm store (optional) |
| *peer fabric* | A second Postgres, Fluree and Mongo standing in for a syndicate co-lender |

Public data carries real identifiers and comes from named public sources. Every
internal element is synthetic, labelled either `synthetic — internal` or
`synthetic — engineered`, the latter meaning it was invented deliberately to
create a condition public data would not supply.

## Current SDK engine requirement — 17 October 2026

Use **Fluree 4.2.4**. The SDK [CI service](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/.github/workflows/ci.yml) and [differential test](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/tests/graph/test_fluree_backend.py) pin that version. If the separately distributed estate bundle's installation guide names an older Fluree version, that engine pin is superseded here; the bundle's checksum still verifies the original data package. This refresh does not claim a newly built or requalified data bundle.

The connection defaults above describe the bundle's restore scripts, not required SDK ports. For SDK examples configure the actual endpoint and use complete Postgres DSNs. Protect curated estate data with read-only roles; S1-01's writable graph demonstration requires its own disposable Fluree instance.
