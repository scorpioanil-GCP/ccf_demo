# Install guide — macOS

Works on Apple silicon and Intel, but **not via the same Fluree path.** Every
other tool is a straight Homebrew install on both (Homebrew just lives in a
different place — `/opt/homebrew` vs `/usr/local`; `brew --prefix` confirms
which one you're on, and the restore scripts already probe both). Fluree is
the exception: the vendor's 4.2.4 installer has no Intel-Mac binary at all
(checked directly against its target list — see step 2), so Intel Macs use a
Docker fallback instead of the native installer. `restore.sh` detects which
one you have; everything from Postgres onward is identical on both.

Run these from the directory you unpacked this bundle into. Copy-paste each
block in order; do not skip ahead. First, find out which Mac you have:

```bash
uname -m
```

`arm64` = Apple silicon, follow the guide straight through. `x86_64` = Intel
— step 2 branches for you (Fluree runs in Docker); the restore in step 7 is
the same single command on both.

## 0. Confirm Homebrew

```bash
brew --version
brew --prefix
```

(If you don't have Homebrew: `https://brew.sh` has the one-line installer.
Everything below assumes it's already there.)

## 1. Install `uv`

```bash
brew install uv
uv --version
```

If you'd rather not, the verifier's own docstring documents a plain-`pip`
fallback — see step 7 below.

## 2. Fluree — pinned to **4.2.4**

The Fluree estate was cut over to 4.2.4 on 2026-10-15, so every Fluree dump
in this bundle is a 4.2.4 archive (the dump-side round-trip was proven
exact: 6,157 commits, 89,148 triples on fibo-v2). A 4.2.4 archive is not
guaranteed to import into 4.1.x — install the exact version.

**The vendor's 4.2.4 installer ships no Intel-Mac binary.** Its target list
(checked directly against the installer script) is `aarch64-apple-darwin`,
`aarch64-pc-windows-msvc`, `aarch64-unknown-linux-gnu`,
`x86_64-pc-windows-msvc`, `x86_64-unknown-linux-gnu` — no
`x86_64-apple-darwin`. On an Intel Mac the command below runs but the binary
it fetches does not exist; there is no native path. **If `uname -m` printed
`x86_64`, skip to "Intel Mac: Docker fallback" below instead of running the
installer.**

### Apple silicon (`arm64`): native installer

Install the exact version via the vendor's own installer (a distro/brew
package would not let you pin the version this precisely):

```bash
curl --proto '=https' --tlsv1.2 -LsSf \
  https://github.com/fluree/db/releases/download/v4.2.4/fluree-db-cli-installer.sh | sh
source "$HOME/bin/env"      # the installer puts fluree in ~/bin; or open a new terminal
fluree --version
```

Expect: `fluree 4.2.4`. Skip the Docker section below entirely and continue
to step 3.

### Intel Mac (`x86_64`): Docker fallback

Fluree publishes a `fluree/server` Docker image — this project runs the
pinned 4.2.4 tag for the co-lender peer fabric in production (since the
2026-10-15 cutover), so this is a proven route, not a guess.

Install Docker Desktop if you don't have it, then pull the image — **pinned
to the exact tag; never `latest`**, which floats to whatever Fluree most
recently shipped and can silently mismatch these archives:

```bash
brew install --cask docker   # if not already installed; launch it once from
                              # Applications so the daemon is running
docker pull fluree/server:4.2.4
```

Run one container that holds all three ledgers, with persistent storage on
your Mac and this bundle's archives mounted in read-only so the CLI inside
the container can read them:

```bash
mkdir -p ~/ccf-fluree-docker
docker run -d --name ccf-fluree \
  -v ~/ccf-fluree-docker:/var/lib/fluree \
  -v "$(pwd)":/bundle:ro \
  -p 8090:8090 \
  fluree/server:4.2.4
sleep 3
docker logs ccf-fluree --tail 5
```

Expect a line like `Fluree server starting addr=0.0.0.0:8090`. The container
runs the server continuously on the same port (8090) the verifier already
expects — **leave `CCF_FLUREE_URL` at its default; do not override it.**

That container is all the Intel path needs from this step. **Do not restore
the ledgers by hand:** `restore.sh` (step 7) finds the running `ccf-fluree`
container, restores all three ledgers through `docker exec`, and the verifier
then checks each ledger's commit count against `MANIFEST.json`. Run the
`docker run` above from inside the unpacked bundle; the `/bundle` mount is
how the container sees the archives.

## 3. Postgres — pinned to **16**

`brew install postgresql` (no version) installs **17** — wrong against these
dumps, which are 16 custom-format archives. Install the versioned formula
explicitly:

```bash
brew install postgresql@16
brew services start postgresql@16
brew --prefix postgresql@16
$(brew --prefix postgresql@16)/bin/psql --version
```

Expect the client to report `16.x`. No extra role-creation step is needed
here (unlike Ubuntu) — Homebrew's `postgresql@16` initializes its cluster
with your own macOS user as the superuser and trusts local connections by
default.

## 4. MongoDB — **8.x server** PLUS the **separate** database-tools package

`mongorestore` is not in the MongoDB server package on macOS either — a very
easy thing to install around and then find missing.

```bash
brew tap mongodb/brew
brew install mongodb-community@8.0 mongodb-database-tools
brew services start mongodb-community@8.0
mongorestore --version
mongosh --version
```

## 5. Neo4j — pinned to **2026.07.x**

```bash
brew install neo4j
neo4j --version
```

Expect `2026.07.x`. The Cypher export in this bundle is not version-bound —
this pin is only to match the source database.

**Set the password BEFORE the first start** (Neo4j refuses to skip this):

```bash
export NEO4J_PASSWORD='choose-a-password'
neo4j-admin dbms set-initial-password "$NEO4J_PASSWORD"
brew services start neo4j
```

## 6. SQLite

Already on macOS — nothing to install.

```bash
sqlite3 --version
```

## 7. Restore and verify — one command

From inside the bundle:

```bash
export NEO4J_PASSWORD='choose-a-password'   # same value as step 5; leave out to skip Neo4j
bash restore.sh
```

`restore.sh` does everything that used to be separate steps here, in order,
and stops at the first one that fails:

1. checks every artifact against `MANIFEST.json` (`verify_bundle.sh`);
2. restores the Fluree ledgers into `$CCF_FLUREE_HOME` (default `~/ccf-fluree`) — on an Intel Mac,
   through the `ccf-fluree` container instead, which already serves `:8090`;
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
