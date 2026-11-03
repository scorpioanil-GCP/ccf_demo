# Install guide — Ubuntu

Tested lineage: Ubuntu 22.04 (jammy) and 24.04 (noble). Every command below
works unchanged on both — Postgres uses the PGDG apt repository on **both**
releases (22.04 needs it; 24.04 already has it, but using PGDG for both means
one instruction covers each release rather than two).

Run these from the directory you unpacked this bundle into. Copy-paste each
block in order; do not skip ahead.

## 0. Update apt and grab prerequisites

```bash
sudo apt update
sudo apt install -y curl ca-certificates gnupg lsb-release xz-utils sqlite3 python3-venv
```

`sqlite3` is the only engine here that's *already* in Ubuntu's own repos —
nothing else to pin for it. `python3-venv` is here for step 6's pip
fallback (Ubuntu splits the `venv` module out of base `python3`); it's not
needed at all if `uv` install works.
`xz-utils` unpacks the Fluree installer's download; desktop Ubuntu has it,
minimal and server images often do not.

## 1. Install `uv`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"   # or open a new terminal
uv --version
```

If you'd rather not add another installer, the verifier's own docstring
documents a plain-`pip` fallback — see step 6 below.

## 2. Fluree — pinned to **4.2.4**

The Fluree estate was cut over to 4.2.4 on 2026-10-15 and every Fluree dump
in this bundle is a 4.2.4 archive (the dump-side round-trip was proven exact:
6,157 commits, 89,148 triples on fibo-v2). A 4.2.4 archive is not guaranteed
to import into 4.1.x. Install the exact version via the vendor's own
installer (not a distro package, which would not pin the version):

```bash
curl --proto '=https' --tlsv1.2 -LsSf \
  https://github.com/fluree/db/releases/download/v4.2.4/fluree-db-cli-installer.sh | sh
source "$HOME/bin/env"      # the installer puts fluree in ~/bin; or open a new terminal
fluree --version
```

Expect: `fluree 4.2.4`.

## 3. Postgres — pinned to **16**, via PGDG (both 22.04 and 24.04)

Plain `apt install postgresql` gives whatever version the release happens to
ship — wrong against these dumps, which are 16 custom-format archives.

```bash
sudo apt install -y postgresql-common
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y
sudo apt install -y postgresql-16 postgresql-client-16
sudo systemctl start postgresql
psql --version
```

Expect the client to report `16.x`.

**One extra step Ubuntu needs that macOS doesn't.** The PGDG package's default
`pg_hba.conf` authenticates local socket connections by matching a Postgres
role to your OS username (`peer` auth) — there is no such role yet. Create
one with permission to make databases, so every plain `psql` / `createdb` /
`pg_restore` call in `restore_postgres.sh` (none of which pass a username)
just works with no password prompt:

```bash
sudo -u postgres createuser --superuser "$(whoami)"
```

## 4. MongoDB — **8.x server** PLUS the **separate** database-tools package

`mongorestore` is not in the MongoDB server package on Ubuntu — it is easy to
install `mongodb-org` and be surprised the restore script can't find it.

```bash
curl -fsSL https://pgp.mongodb.com/server-8.0.asc | \
  sudo gpg --dearmor -o /usr/share/keyrings/mongodb-server-8.0.gpg
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg ] \
https://repo.mongodb.org/apt/ubuntu $(lsb_release -cs)/mongodb-org/8.0 multiverse" | \
  sudo tee /etc/apt/sources.list.d/mongodb-org-8.0.list
sudo apt update
sudo apt install -y mongodb-org mongodb-mongosh mongodb-database-tools
sudo systemctl start mongod
mongorestore --version
mongosh --version
```

## 5. Neo4j — pinned to **2026.07.x**

Neo4j needs a JVM; install one explicitly rather than letting apt guess:

```bash
sudo apt install -y openjdk-21-jdk
curl -fsSL https://debian.neo4j.com/neotechnology.gpg.key | \
  sudo gpg --dearmor -o /usr/share/keyrings/neo4j.gpg
echo "deb [signed-by=/usr/share/keyrings/neo4j.gpg] https://debian.neo4j.com stable latest" | \
  sudo tee /etc/apt/sources.list.d/neo4j.list
sudo apt update
sudo apt install -y neo4j
neo4j --version
```

Expect `2026.07.x`. The Cypher export in this bundle is not version-bound —
this pin is only to match the source database.

**Set the password BEFORE the first start** (Neo4j refuses to skip this):

```bash
export NEO4J_PASSWORD='choose-a-password'
sudo neo4j-admin dbms set-initial-password "$NEO4J_PASSWORD"
sudo systemctl start neo4j
```

## 6. Restore and verify — one command

From inside the bundle:

```bash
export NEO4J_PASSWORD='choose-a-password'   # same value as step 5; leave out to skip Neo4j
bash restore.sh
```

`restore.sh` does everything that used to be separate steps here, in order,
and stops at the first one that fails:

1. checks every artifact against `MANIFEST.json` (`verify_bundle.sh`);
2. restores the Fluree ledgers into `$CCF_FLUREE_HOME` (default `~/ccf-fluree`);
3. starts the Fluree server on `127.0.0.1:8090`, logging to `~/ccf-fluree/server.log`;
4. restores Postgres, MongoDB, SQLite, and Neo4j (skipped, and reported as
   skipped, when no `NEO4J_PASSWORD` is set or `cypher-shell` is missing);
5. runs `verify_install.py` (through `uv`, or a private venv if `uv` is absent).

Every restore step prints expected vs. found. It is safe to re-run.

**Reading the result** — `restore.sh` exits with the verifier's code:

- Exit **0**, "Estate verified." — done. It also prints the `.env` lines a
  `ccf_dataprep` clone needs to see this restore.
- Exit **1** — a specific check failed; it prints required vs. found.
- Exit **2** — a store could not be reached. **This means an install
  problem** (a service not started, a wrong password, a port not open) —
  **not** a problem with the data in this bundle. It names which store.

To run the pieces by hand instead, see `restore/restore_all.sh` and the
individual `restore/restore_*.sh` scripts it calls.
