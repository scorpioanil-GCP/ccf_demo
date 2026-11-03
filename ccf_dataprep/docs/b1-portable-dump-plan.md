# B1 Portable Dump and Restore — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a physical extract of every datastore in the estate under `/data/laptop` on db1, plus restore scripts and a self-contained verifier, so a clean macOS or Ubuntu machine can be loaded from it and proved correct.

**Architecture:** Dump scripts live in the repo under `portable/dump/` and execute **on db1** (which has `pg_dump`/`mongodump`; the workstation has neither). Restore scripts and the verifier also live in the repo under `portable/restore/` and `portable/verify_install.py`, and are **copied into the bundle** by the dump orchestrator so the shipped artifacts are version-controlled rather than hand-written on a server. One restore code path serves both platforms; `platform.sh` is the only file that branches.

**Tech Stack:** bash (POSIX-leaning, no `sed -i`, no `readlink -f`), Python 3.11+ with `uv`, Fluree 4.1.4/4.1.6 CLI, `pg_dump`/`pg_restore` 16, `mongodump`/`mongorestore` 100.x, `sqlite3`, Neo4j bolt driver.

**Spec:** `docs/b1-portable-dump-design.md`

## Global Constraints

Every task's requirements implicitly include this section.

- **Never enumerate MongoDB databases.** db1 also runs `rtdetect` (~5.5M docs). Every dump and restore names its database explicitly and validates it against an allowlist **in code**, not in a comment.
- **Never inline a multi-line script through `ssh`.** Quoting mangles it — this failed twice while measuring for this design, once silently killing the calling shell via `pkill -f` matching its own command line. Always `rsync` the script to db1 and execute the file.
- **Compare content as a set, never by count.** A dump with the right number of wrong rows is exactly what a count check cannot see. This is `loaders/dump_fluree.py`'s existing rule for this estate.
- **No `sed -i`, no `readlink -f`** anywhere in shipped scripts. BSD and GNU differ, and the failure mode is a corrupted restore rather than an error.
- **Target versions:** Fluree **4.1.6**; Postgres **16**; MongoDB **8.x** plus **`mongodb-database-tools`** (a separate package on both platforms); Neo4j **2026.07.x**; SQLite 3.4x.
- **Bundle root** is `/data/laptop` on db1. It already contains `dave.txt`, a user test file — leave it alone.
- **Idempotent.** Every dump and restore script is safely re-runnable.
- **The live estate is read-only to this work.** Dumps read; all restore verification happens in scratch namespaces suffixed `_b1chk`.
- `uv run pytest` is broken repo-wide — use `uv run --with pytest pytest`.

## File Structure

```
portable/
  README.md                  what this directory is; repo-side, not shipped
  dump/
    common.sh                shared: logging, sha256 (both platforms), manifest append
    dump_fluree.sh           v1 fibo, v2 fibo-v2, peer bofa/syndicate
    dump_postgres.sh         public, ccf_v2, colender
    dump_mongo.sh            fibo, fibo_v2, bofa_syndicated — allowlist enforced
    dump_sqlite.sh           departmental (runs on the workstation, then ships up)
    dump_neo4j.py            v1 graph as a Cypher script, via bolt
    dump_all.sh              orchestrator; writes MANIFEST.json; stages the bundle
  restore/                   SHIPPED to /data/laptop/restore/
    platform.sh              the only file that knows macOS from Ubuntu
    restore_fluree.sh  restore_postgres.sh  restore_mongo.sh
    restore_sqlite.sh  restore_neo4j.sh     restore_all.sh
  verify_install.py          SHIPPED to /data/laptop/
  bundle/                    SHIPPED docs
    README.md  INSTALL-macos.md  INSTALL-ubuntu.md
  tests/
    test_manifest.py         manifest writer + sha256 agreement
    test_verify_checks.py    every verifier check, incl. its failure direction
    test_mongo_guard.py      the allowlist refuses what it must
```

---

### Task 1: Foundation — platform shim, manifest, and the MongoDB guard

**Files:**
- Create: `portable/dump/common.sh`
- Create: `portable/restore/platform.sh`
- Create: `portable/manifest.py`
- Test: `portable/tests/test_manifest.py`, `portable/tests/test_mongo_guard.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `platform.sh` exports `CCF_OS` (`macos`|`ubuntu`), `PG_BIN`, `SHA256_CMD`, and function `ccf_sha256 <file>` → hex string on stdout
  - `manifest.py`: `add_artifact(root: Path, rel_path: str, *, store: str, fabric: str, method: str, extra: dict | None = None) -> dict` and `write_manifest(root: Path, entries: list[dict]) -> Path`
  - `manifest.py`: `assert_mongo_db_allowed(name: str) -> str` — returns the name or raises `MongoScopeError`

- [ ] **Step 1: Write the failing tests**

```python
# portable/tests/test_mongo_guard.py
import pytest
from portable.manifest import assert_mongo_db_allowed, MongoScopeError

ALLOWED = ["fibo", "fibo_v2", "bofa_syndicated"]

@pytest.mark.parametrize("name", ALLOWED)
def test_allowed_names_pass(name):
    assert assert_mongo_db_allowed(name) == name

@pytest.mark.parametrize("name", ["rtdetect", "rtdetect_test", "admin",
                                  "config", "local", "", "fibo_v2_backup"])
def test_everything_else_is_refused(name):
    with pytest.raises(MongoScopeError):
        assert_mongo_db_allowed(name)

def test_refusal_names_the_database_and_the_allowlist():
    with pytest.raises(MongoScopeError) as e:
        assert_mongo_db_allowed("rtdetect")
    msg = str(e.value)
    assert "rtdetect" in msg
    assert "fibo_v2" in msg
```

```python
# portable/tests/test_manifest.py
import hashlib, json, subprocess
from pathlib import Path
from portable.manifest import add_artifact, write_manifest

def test_sha256_matches_the_shell_tool(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"ccf" * 1000)
    entry = add_artifact(tmp_path, "a.bin", store="test", fabric="test",
                         method="write_bytes")
    expected = hashlib.sha256(f.read_bytes()).hexdigest()
    assert entry["sha256"] == expected
    assert entry["bytes"] == 3000

def test_directory_artifact_hashes_its_contents_not_the_dirname(tmp_path):
    d = tmp_path / "dump"
    (d / "sub").mkdir(parents=True)
    (d / "sub" / "x.bson").write_bytes(b"one")
    first = add_artifact(tmp_path, "dump", store="mongo", fabric="v2",
                         method="mongodump")
    (d / "sub" / "x.bson").write_bytes(b"two")
    second = add_artifact(tmp_path, "dump", store="mongo", fabric="v2",
                          method="mongodump")
    assert first["sha256"] != second["sha256"], \
        "a directory hash that ignores content cannot detect a changed dump"

def test_manifest_is_valid_json_with_every_entry(tmp_path):
    (tmp_path / "a.bin").write_bytes(b"x")
    entries = [add_artifact(tmp_path, "a.bin", store="s", fabric="f",
                            method="m")]
    path = write_manifest(tmp_path, entries)
    doc = json.loads(path.read_text())
    assert doc["artifact_count"] == 1
    assert doc["artifacts"][0]["path"] == "a.bin"
    assert "generated_at" in doc
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --with pytest pytest portable/tests/ -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'portable.manifest'`

- [ ] **Step 3: Write `portable/manifest.py`**

```python
"""Bundle manifest and the MongoDB scope guard.

The guard is here rather than in a comment because db1's MongoDB also carries
`rtdetect` — roughly 5.5 million documents of an unrelated live system. A dump
or restore that reached it would be destructive and silent. `ccf/config.py`
takes the same position for the same host; this is its dump-side twin.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

#: The only MongoDB databases this bundle may read or write. Anything absent is
#: refused — an allowlist, never a denylist, because a denylist silently admits
#: whatever nobody thought of.
ALLOWED_MONGO_DBS = frozenset({"fibo", "fibo_v2", "bofa_syndicated"})


class MongoScopeError(RuntimeError):
    """An attempt to dump or restore a MongoDB database outside the bundle."""


def assert_mongo_db_allowed(name: str) -> str:
    if name not in ALLOWED_MONGO_DBS:
        raise MongoScopeError(
            f"Refusing to touch MongoDB database {name!r}. This bundle covers "
            f"only {sorted(ALLOWED_MONGO_DBS)}. db1's MongoDB also carries "
            f"'rtdetect' (~5.5M documents) belonging to an unrelated live "
            f"system; naming databases explicitly is what keeps it safe."
        )
    return name


def _hash_path(path: Path) -> tuple[str, int]:
    """sha256 over a file, or over a directory's sorted contents.

    A directory hash must fold in each file's relative path AND its bytes: a
    hash over bytes alone cannot see a file being renamed, and a hash over
    names alone cannot see its content change.
    """
    h = hashlib.sha256()
    total = 0
    if path.is_file():
        data = path.read_bytes()
        h.update(data)
        return h.hexdigest(), len(data)
    for child in sorted(p for p in path.rglob("*") if p.is_file()):
        rel = child.relative_to(path).as_posix()
        data = child.read_bytes()
        h.update(rel.encode())
        h.update(b"\0")
        h.update(data)
        total += len(data)
    return h.hexdigest(), total


def add_artifact(root: Path, rel_path: str, *, store: str, fabric: str,
                 method: str, extra: dict | None = None) -> dict:
    target = Path(root) / rel_path
    if not target.exists():
        raise FileNotFoundError(f"manifest names a missing artifact: {target}")
    digest, size = _hash_path(target)
    entry = {
        "path": rel_path,
        "store": store,
        "fabric": fabric,
        "method": method,
        "bytes": size,
        "sha256": digest,
    }
    if extra:
        entry.update(extra)
    return entry


def write_manifest(root: Path, entries: list[dict]) -> Path:
    doc = {
        "bundle": "ccf_dataprep portable estate",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_host": "db1 (192.168.4.76)",
        "artifact_count": len(entries),
        "artifacts": sorted(entries, key=lambda e: e["path"]),
    }
    path = Path(root) / "MANIFEST.json"
    path.write_text(json.dumps(doc, indent=2) + "\n")
    return path
```

- [ ] **Step 4: Write `portable/restore/platform.sh`**

```bash
#!/usr/bin/env bash
# The ONLY file in this bundle that knows macOS from Ubuntu.
#
# Every restore_*.sh sources this and is otherwise identical on both platforms.
# Two parallel script sets would drift, and only the one somebody happened to
# run would ever be exercised.
#
# `sed -i` and `readlink -f` are deliberately absent from every script here:
# BSD and GNU disagree on both, and the failure mode is a corrupted restore
# rather than an error message.
set -euo pipefail

case "$(uname -s)" in
  Darwin) CCF_OS="macos"  ;;
  Linux)  CCF_OS="ubuntu" ;;
  *) echo "Unsupported platform: $(uname -s). This bundle targets macOS and Ubuntu." >&2
     exit 2 ;;
esac
export CCF_OS

if [ "$CCF_OS" = "macos" ]; then
  SHA256_CMD="shasum -a 256"
  for c in /opt/homebrew/opt/postgresql@16/bin /usr/local/opt/postgresql@16/bin; do
    [ -d "$c" ] && PG_BIN="$c" && break
  done
else
  SHA256_CMD="sha256sum"
  [ -d /usr/lib/postgresql/16/bin ] && PG_BIN="/usr/lib/postgresql/16/bin"
fi
PG_BIN="${PG_BIN:-}"
export SHA256_CMD PG_BIN

ccf_sha256() { $SHA256_CMD "$1" | awk '{print $1}'; }

ccf_need() {
  # Report EVERY missing tool, not just the first. Finding out about
  # mongorestore only after installing three other things wastes an evening.
  local missing=0 tool
  for tool in "$@"; do
    if ! command -v "$tool" >/dev/null 2>&1; then
      echo "MISSING: $tool" >&2
      missing=1
    fi
  done
  if [ "$missing" -ne 0 ]; then
    echo "" >&2
    echo "See INSTALL-${CCF_OS}.md. Note mongorestore ships in" >&2
    echo "'mongodb-database-tools', NOT in the MongoDB server package." >&2
    exit 2
  fi
}

ccf_log() { printf '  %s\n' "$*"; }
```

- [ ] **Step 5: Write `portable/dump/common.sh`**

```bash
#!/usr/bin/env bash
# Shared helpers for the dump side. Runs on db1 (Ubuntu).
set -euo pipefail

BUNDLE_ROOT="${BUNDLE_ROOT:-/data/laptop}"
export BUNDLE_ROOT

ccf_log()  { printf '  %s\n' "$*"; }
ccf_step() { printf '\n== %s\n' "$*"; }

ccf_require_dir() {
  [ -d "$1" ] || { echo "bundle root missing: $1" >&2; exit 2; }
}

# Idempotency: replace an artifact wholesale rather than merging into a stale
# one. A mongodump written over a previous dump's directory keeps orphaned
# collections that nothing will ever notice.
ccf_reset_path() {
  rm -rf "$1"
  mkdir -p "$(dirname "$1")"
}
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run --with pytest pytest portable/tests/ -q`
Expected: PASS, 6 tests

- [ ] **Step 7: Verify the platform shim on this machine**

Run: `bash -c 'source portable/restore/platform.sh && echo "$CCF_OS $PG_BIN" && ccf_sha256 README.md'`
Expected: prints `ubuntu` and a 64-char hex digest. Confirm the digest matches `sha256sum README.md`.

- [ ] **Step 8: Commit**

```bash
git add portable/manifest.py portable/dump/common.sh portable/restore/platform.sh portable/tests/
git commit -m "B1 Task 1: bundle manifest, platform shim, MongoDB scope guard"
```

---

### Task 2: Fluree — dump and restore, all three ledgers

**Files:**
- Create: `portable/dump/dump_fluree.sh`
- Create: `portable/restore/restore_fluree.sh`

**Interfaces:**
- Consumes: `portable/dump/common.sh`, `portable/restore/platform.sh`
- Produces: `v1/fluree-fibo.flpack`, `v2/primary/fluree-fibo-v2.flpack`, `v2/colender/fluree-bofa-syndicate.flpack`

**Background established by the design spike — do not re-derive:**
- `fluree export --format ledger` writes a `.flpack` carrying commits **and** index artifacts. `fluree create <ledger> --from <file>.flpack` imports it. The ledger name is a positional argument on `create` and omitting it fails with a usage message, not an error.
- The CLI needs a project directory (`fluree init` creates `.fluree/`), and `--direct` bypasses any running server.
- A 4.1.4 archive imports into 4.1.6 keeping `t`, all index artifacts, and sub-millisecond queries. Verified 2026-08-27.
- The peer Fluree runs **inside the `fluree-demo` container**, so its export runs through `docker exec` and the archive is copied out.

- [ ] **Step 1: Write `portable/dump/dump_fluree.sh`**

```bash
#!/usr/bin/env bash
# Fluree dumps for all three ledgers, both fabrics.
#
# The primary host binary is 4.1.4; the peer container runs 4.1.6. A 4.1.4
# archive imports cleanly into 4.1.6 (verified 2026-08-27), so the target
# installs 4.1.6 and reads both.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/common.sh"
ccf_require_dir "$BUNDLE_ROOT"

FLUREE_BIN="${FLUREE_BIN:-/home/parkave/bin/fluree}"
LIVE_STORAGE="${LIVE_STORAGE:-/data/fluree}"
WORK="${WORK:-/data/laptop/.work/fluree}"

# Export from a COPY of the live storage, never from the live path itself.
# `fluree export` needs a project directory and may write cache or index
# artifacts; pointing it at the authoritative ledger to save a copy would
# trade an irreversible risk for 27 MB of disk.
export_local_ledger() {
  local ledger="$1" out="$2"
  ccf_step "Fluree $ledger -> $out"
  local proj="$WORK/$ledger"
  ccf_reset_path "$proj"; mkdir -p "$proj"
  ( cd "$proj" && "$FLUREE_BIN" init >/dev/null )
  local st="$proj/.fluree/storage"
  mkdir -p "$st/$ledger/main" "$st/ns@v2/$ledger"
  cp -r "$LIVE_STORAGE/$ledger/main/commit" "$st/$ledger/main/"
  cp "$LIVE_STORAGE/ns@v2/$ledger/main.json" "$st/ns@v2/$ledger/"
  : > "$st/ns@v2/$ledger/main.commits.jsonl"
  # Build ONE index. The live ledger carries ~1,421 accumulated generations
  # (46 GB); one current index is 47 MB and makes queries 550x faster.
  ( cd "$proj" && "$FLUREE_BIN" index "$ledger" --direct >/dev/null )
  ccf_reset_path "$out"
  ( cd "$proj" && "$FLUREE_BIN" export "$ledger" --format ledger -o "$out" --direct )
  ccf_log "$(ls -lh "$out" | awk '{print $5}') $(basename "$out")"
}

export_local_ledger "fibo-v2" "$BUNDLE_ROOT/v2/primary/fluree-fibo-v2.flpack"
export_local_ledger "fibo"    "$BUNDLE_ROOT/v1/fluree-fibo.flpack"

# --- peer, inside the container -------------------------------------------
ccf_step "Fluree bofa/syndicate (peer container)"
PEER_OUT="$BUNDLE_ROOT/v2/colender/fluree-bofa-syndicate.flpack"
ccf_reset_path "$PEER_OUT"
docker exec fluree-demo sh -c \
  'cd /tmp && fluree export bofa/syndicate --format ledger -o /tmp/peer.flpack --direct' >/dev/null
docker cp fluree-demo:/tmp/peer.flpack "$PEER_OUT"
docker exec fluree-demo rm -f /tmp/peer.flpack
ccf_log "$(ls -lh "$PEER_OUT" | awk '{print $5}') $(basename "$PEER_OUT")"

rm -rf "$WORK"
```

- [ ] **Step 2: Run it and verify each archive exists and is non-trivial**

Run: `rsync -a portable/dump/ parkave@192.168.4.76:/data/laptop/.scripts/dump/ && ssh parkave@192.168.4.76 'bash /data/laptop/.scripts/dump/dump_fluree.sh'`

Expected: three `.flpack` files. `fluree-fibo-v2.flpack` about 69 MB and reported as carrying **100 index artifacts**; the other two small.

Do **not** move on if any export reports `0 index artifacts` for `fibo-v2` — that means the index step did not run and queries on the target will be 550× slower.

- [ ] **Step 3: Write `portable/restore/restore_fluree.sh`**

```bash
#!/usr/bin/env bash
# Restore all Fluree ledgers into one project directory.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/platform.sh"
BUNDLE="$(cd "$HERE/.." && pwd)"
ccf_need fluree

TARGET="${CCF_FLUREE_HOME:-$HOME/ccf-fluree}"
mkdir -p "$TARGET"
( cd "$TARGET" && [ -d .fluree ] || fluree init >/dev/null )

restore_one() {
  local ledger="$1" pack="$2"
  [ -f "$pack" ] || { echo "missing archive: $pack" >&2; exit 1; }
  ccf_log "restoring $ledger"
  # Idempotent: drop any prior copy first, or `create` fails on a re-run.
  ( cd "$TARGET" && fluree drop "$ledger" --direct >/dev/null 2>&1 || true )
  ( cd "$TARGET" && fluree create "$ledger" --from "$pack" --direct )
}

restore_one "fibo-v2"        "$BUNDLE/v2/primary/fluree-fibo-v2.flpack"
restore_one "fibo"           "$BUNDLE/v1/fluree-fibo.flpack"
restore_one "bofa/syndicate" "$BUNDLE/v2/colender/fluree-bofa-syndicate.flpack"

ccf_log "ledgers now present:"
( cd "$TARGET" && fluree list --direct )
```

- [ ] **Step 4: Prove the round trip by content, not by count**

Restore into a scratch project on db1 and compare N-Triples against the live ledger as a **set**:

```bash
ssh parkave@192.168.4.76 'bash -s' <<'SH'
set -e
rm -rf /tmp/b1chk && mkdir -p /tmp/b1chk && cd /tmp/b1chk
/home/parkave/bin/fluree init >/dev/null
/home/parkave/bin/fluree create fibo-v2 --from /data/laptop/v2/primary/fluree-fibo-v2.flpack --direct
/home/parkave/bin/fluree export fibo-v2 --format ntriples -o /tmp/b1chk/restored.nt --direct
echo "restored lines: $(wc -l < /tmp/b1chk/restored.nt)"
echo "restored sha  : $(sort /tmp/b1chk/restored.nt | sha256sum | cut -c1-32)"
/home/parkave/bin/fluree list --direct
SH
```

Expected: **87,162 lines**, ledger `fibo-v2` at **t=4468**, and the sorted sha256 equal to the live ledger's. Record the digest in the task notes — later tasks compare against it.

- [ ] **Step 5: Prove idempotency by re-running, then re-checking**

Run the restore a second time into the same project, then repeat Step 4's export and hash.
Expected: identical digest, no error. A restore that only works once is not a restore.

- [ ] **Step 6: Commit**

```bash
git add portable/dump/dump_fluree.sh portable/restore/restore_fluree.sh
git commit -m "B1 Task 2: Fluree dump and restore for all three ledgers"
```

---

### Task 3: Postgres — dump and restore, three schemas across two databases

**Files:**
- Create: `portable/dump/dump_postgres.sh`
- Create: `portable/restore/restore_postgres.sh`

**Interfaces:**
- Consumes: `common.sh`, `platform.sh`
- Produces: `v1/postgres-public.dump`, `v2/primary/postgres-ccf_v2.dump`, `v2/colender/postgres-colender.dump`

**Facts:** `ccf_v2` holds **113 tables / 718 MB**; `public` holds 2 tables / 160 kB; the peer's `colender` schema holds 2 tables / 64 kB inside database `bofa_syndicated`. Server is 16.15 on both. The peer connects as a different role to a different database — that separation is a control, not a convention, so the dump must not "simplify" by reusing our role.

- [ ] **Step 1: Write `portable/dump/dump_postgres.sh`**

```bash
#!/usr/bin/env bash
# -Fc (custom format) rather than plain SQL: compressed, and pg_restore can
# list and select from it, which plain SQL cannot.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/common.sh"
ccf_require_dir "$BUNDLE_ROOT"

: "${PGHOST:=192.168.4.76}"
: "${PGPORT:=5432}"
export PGHOST PGPORT

dump_schema() {
  local db="$1" schema="$2" user="$3" out="$4"
  ccf_step "Postgres $db.$schema -> $(basename "$out")"
  ccf_reset_path "$out"
  PGPASSWORD="${5:-}" pg_dump -Fc --no-owner --no-privileges \
      --schema="$schema" --dbname="$db" --username="$user" --file="$out"
  ccf_log "$(ls -lh "$out" | awk '{print $5}')"
  # A dump that lists zero tables is a silent disaster: pg_dump exits 0 when a
  # --schema matches nothing at all.
  local n
  n="$(pg_restore --list "$out" | grep -c 'TABLE DATA' || true)"
  ccf_log "tables with data: $n"
  [ "$n" -gt 0 ] || { echo "REFUSING: $schema dumped 0 tables" >&2; exit 1; }
}

dump_schema parkavedb ccf_v2 "${PGUSER:-parkave}" \
    "$BUNDLE_ROOT/v2/primary/postgres-ccf_v2.dump" "${PGPASSWORD:-}"
dump_schema parkavedb public "${PGUSER:-parkave}" \
    "$BUNDLE_ROOT/v1/postgres-public.dump" "${PGPASSWORD:-}"
dump_schema "${CO_LENDER_PG_DB:-bofa_syndicated}" \
    "${CO_LENDER_PG_SCHEMA:-colender}" "${CO_LENDER_PG_USER:-colender}" \
    "$BUNDLE_ROOT/v2/colender/postgres-colender.dump" \
    "${CO_LENDER_PG_PASSWORD:-}"
```

- [ ] **Step 2: Run it and check the table counts land where expected**

Run the script on db1 with the environment loaded from `~/.bashrc` (that is where the peer credentials live on this machine — **not** `.env`; `load_dotenv()` does not override an already-set variable).

Expected: `ccf_v2` reports **113** tables with data, `public` reports 2, `colender` reports 2. A count of 0 aborts by design.

- [ ] **Step 3: Write `portable/restore/restore_postgres.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/platform.sh"
BUNDLE="$(cd "$HERE/.." && pwd)"
[ -n "$PG_BIN" ] && PATH="$PG_BIN:$PATH" && export PATH
ccf_need psql pg_restore createdb createuser

PGDB="${CCF_PGDATABASE:-parkavedb}"
PEERDB="${CCF_CO_LENDER_PGDATABASE:-bofa_syndicated}"

server_major="$(psql -tAc 'show server_version' postgres | cut -d. -f1)"
if [ "$server_major" != "16" ]; then
  echo "Postgres server is major version $server_major; these dumps are 16." >&2
  echo "pg_restore cannot read a 16 custom-format dump into an older server," >&2
  echo "and a newer one may reject it. Install postgresql@16." >&2
  exit 2
fi

createdb "$PGDB" 2>/dev/null || ccf_log "$PGDB exists"
createdb "$PEERDB" 2>/dev/null || ccf_log "$PEERDB exists"

# --clean --if-exists makes this re-runnable. Without it a second run leaves
# every table intact and reports only constraint errors, which reads as noise.
pg_restore --clean --if-exists --no-owner --no-privileges \
  --dbname="$PGDB" "$BUNDLE/v2/primary/postgres-ccf_v2.dump" || true
pg_restore --clean --if-exists --no-owner --no-privileges \
  --dbname="$PGDB" "$BUNDLE/v1/postgres-public.dump" || true
pg_restore --clean --if-exists --no-owner --no-privileges \
  --dbname="$PEERDB" "$BUNDLE/v2/colender/postgres-colender.dump" || true

ccf_log "ccf_v2 tables: $(psql -tAc "select count(*) from information_schema.tables where table_schema='ccf_v2'" "$PGDB")"
```

`pg_restore` exits non-zero on ignorable `DROP ... does not exist` notices during a first run, which is why each call tolerates that; the table count printed at the end is the real check, and Task 6's verifier is the binding one.

- [ ] **Step 4: Restore into a scratch database on db1 and count tables**

```bash
ssh parkave@192.168.4.76 'createdb b1chk_pg && pg_restore --no-owner --no-privileges --dbname=b1chk_pg /data/laptop/v2/primary/postgres-ccf_v2.dump; psql -tAc "select count(*) from information_schema.tables where table_schema=\"ccf_v2\"" b1chk_pg'
```

Expected: **113**.

- [ ] **Step 5: Compare a landmark row, not just the count**

```bash
ssh parkave@192.168.4.76 'for db in parkavedb b1chk_pg; do echo -n "$db: "; psql -tAc "select count(*)||\" \"||coalesce(md5(string_agg(lei,\",\" order by lei)),\"none\") from ccf_v2.legal_entity" $db; done'
```

Expected: both print **156** and the **same md5**. A row count alone would pass on a table restored with the right number of wrong rows.

- [ ] **Step 6: Drop the scratch database and commit**

```bash
ssh parkave@192.168.4.76 'dropdb b1chk_pg'
git add portable/dump/dump_postgres.sh portable/restore/restore_postgres.sh
git commit -m "B1 Task 3: Postgres dump and restore across three schemas"
```

---

### Task 4: MongoDB — dump and restore, with the scope guard wired in

**Files:**
- Create: `portable/dump/dump_mongo.sh`
- Create: `portable/restore/restore_mongo.sh`

**Interfaces:**
- Consumes: `common.sh`, `platform.sh`, `portable/manifest.py::assert_mongo_db_allowed`
- Produces: `v1/mongo-fibo/`, `v2/primary/mongo-fibo_v2/`, `v2/colender/mongo-bofa_syndicated/`

**Facts:** `fibo_v2` holds 38,238 documents in 6 collections (576 MB); `fibo` holds 30 documents; the peer's `bofa_syndicated` currently holds **0 collections** and is dumped anyway, recorded `"empty": true`. The peer Mongo is a **separate mongod on port 27018**, not the host instance.

- [ ] **Step 1: Write `portable/dump/dump_mongo.sh`**

```bash
#!/usr/bin/env bash
# Every invocation names its database. There is deliberately no loop over a
# database list: db1's MongoDB also carries `rtdetect`, ~5.5M documents of an
# unrelated live system, and enumeration is how it would get swept up.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/common.sh"
REPO="${REPO:-/home/parkave/ccf_dataprep}"

guard() {
  # The guard is Python so there is ONE allowlist in the estate, not a shell
  # copy that drifts from it.
  python3 -c "import sys; sys.path.insert(0,'$REPO'); \
from portable.manifest import assert_mongo_db_allowed as a; a(sys.argv[1])" "$1"
}

dump_db() {
  local uri="$1" db="$2" out="$3"
  guard "$db"
  ccf_step "MongoDB $db -> $(basename "$out")"
  ccf_reset_path "$out"; mkdir -p "$out"
  mongodump --uri="$uri" --db="$db" --gzip --out="$out" --quiet
  local n
  n="$(find "$out" -name '*.bson.gz' | wc -l)"
  ccf_log "collections dumped: $n"
}

dump_db "${MONGO_URI:-mongodb://192.168.4.76:27017}" "fibo_v2" \
        "$BUNDLE_ROOT/v2/primary/mongo-fibo_v2"
dump_db "${MONGO_URI:-mongodb://192.168.4.76:27017}" "fibo" \
        "$BUNDLE_ROOT/v1/mongo-fibo"
dump_db "${CO_LENDER_MONGO_URI:?peer Mongo URI not set}" "bofa_syndicated" \
        "$BUNDLE_ROOT/v2/colender/mongo-bofa_syndicated"
```

- [ ] **Step 2: Prove the guard actually refuses**

Run: `bash -c '. portable/dump/common.sh; REPO=$PWD python3 -c "import sys;sys.path.insert(0,\".\");from portable.manifest import assert_mongo_db_allowed as a;a(\"rtdetect\")"'`
Expected: `MongoScopeError` naming `rtdetect` and listing the allowlist, non-zero exit. A guard nobody has watched refuse is not a guard.

- [ ] **Step 3: Run the dump and check collection counts**

Expected: `fibo_v2` reports **6** collections, `fibo` reports 2, `bofa_syndicated` reports **0**. Zero is correct for the peer and must not be treated as a failure.

- [ ] **Step 4: Write `portable/restore/restore_mongo.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/platform.sh"
BUNDLE="$(cd "$HERE/.." && pwd)"
ccf_need mongorestore mongosh

URI="${CCF_MONGO_URI:-mongodb://127.0.0.1:27017}"

restore_db() {
  local db="$1" dir="$2"
  case "$db" in
    fibo|fibo_v2|bofa_syndicated) ;;
    *) echo "Refusing MongoDB database '$db' — not in this bundle." >&2; exit 2 ;;
  esac
  if [ ! -d "$dir/$db" ]; then
    ccf_log "$db: nothing to restore (dump recorded as empty)"
    return 0
  fi
  ccf_log "restoring $db"
  # --drop makes this re-runnable; without it a second run doubles every doc.
  mongorestore --uri="$URI" --db="$db" --gzip --drop --quiet "$dir/$db"
}

restore_db fibo_v2         "$BUNDLE/v2/primary/mongo-fibo_v2"
restore_db fibo            "$BUNDLE/v1/mongo-fibo"
restore_db bofa_syndicated "$BUNDLE/v2/colender/mongo-bofa_syndicated"
```

- [ ] **Step 5: Restore into a scratch database on db1 and compare content**

```bash
ssh parkave@192.168.4.76 'mongorestore --db=b1chk_mongo --gzip --drop --quiet /data/laptop/v2/primary/mongo-fibo_v2/fibo_v2 && mongosh --quiet --eval "
const a=db.getSiblingDB(\"fibo_v2\"), b=db.getSiblingDB(\"b1chk_mongo\");
for (const c of a.getCollectionNames().sort()) {
  print(c, a[c].countDocuments({}), b[c].countDocuments({}));
}"'
```

Expected: six collections, each with **equal counts on both sides**, totalling 38,238.

- [ ] **Step 6: Drop the scratch database and commit**

```bash
ssh parkave@192.168.4.76 'mongosh --quiet --eval "db.getSiblingDB(\"b1chk_mongo\").dropDatabase()"'
git add portable/dump/dump_mongo.sh portable/restore/restore_mongo.sh
git commit -m "B1 Task 4: MongoDB dump and restore with allowlist guard"
```

---

### Task 5: SQLite and Neo4j

**Files:**
- Create: `portable/dump/dump_sqlite.sh`
- Create: `portable/dump/dump_neo4j.py`
- Create: `portable/restore/restore_sqlite.sh`
- Create: `portable/restore/restore_neo4j.sh`

**Interfaces:**
- Produces: `v2/primary/departmental.sqlite`, `v1/neo4j-v1.cypher`

**Why Neo4j is a Cypher script and not `neo4j-admin database dump`:** that command refuses a running database ("It is not possible to dump a database that is mounted in a running Neo4j server", verified 2026-08-27), so it would mean stopping Neo4j on db1. Its archive is also major-version-bound. The graph is **14 nodes and 16 relationships** — a Cypher script is version-portable, human-readable, and needs no service interruption.

**SQLite runs on the workstation,** not db1: the file lives at `data/departmental.sqlite` in the repo. `VACUUM INTO` is used rather than `cp`, because copying a live SQLite file can capture a torn write.

- [ ] **Step 1: Write `portable/dump/dump_sqlite.sh`**

```bash
#!/usr/bin/env bash
# Runs on the WORKSTATION (the file is local), then ships the snapshot to db1.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
SRC="${SQLITE_SRC:-$REPO/data/departmental.sqlite}"
OUT="${SQLITE_OUT:-$REPO/.b1-staging/departmental.sqlite}"
REMOTE="${REMOTE:-parkave@192.168.4.76}"
DEST="${DEST:-/data/laptop/v2/primary/departmental.sqlite}"

[ -f "$SRC" ] || { echo "no SQLite file at $SRC" >&2; exit 1; }
mkdir -p "$(dirname "$OUT")"
rm -f "$OUT"
# VACUUM INTO takes a consistent snapshot of a live database. `cp` does not.
sqlite3 "$SRC" "VACUUM INTO '$OUT'"

src_tables="$(sqlite3 "$SRC" "select count(*) from sqlite_master where type='table'")"
out_tables="$(sqlite3 "$OUT" "select count(*) from sqlite_master where type='table'")"
echo "  tables: source=$src_tables snapshot=$out_tables"
[ "$src_tables" = "$out_tables" ] || { echo "table count differs" >&2; exit 1; }

ssh "$REMOTE" "mkdir -p $(dirname "$DEST")"
rsync -a "$OUT" "$REMOTE:$DEST"
echo "  shipped to $REMOTE:$DEST"
```

- [ ] **Step 2: Write `portable/dump/dump_neo4j.py`**

```python
"""Export the v1 Neo4j graph as a replayable Cypher script.

14 nodes, 16 relationships. `neo4j-admin database dump` refuses a running
database and its archive is major-version-bound; a Cypher script is neither.

Every node is given a stable `_b1id` property derived from its element id so
relationships can be reconnected on replay without relying on Neo4j's internal
ids, which are NOT stable across a reload.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from neo4j import GraphDatabase


def literal(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(literal(x) for x in v) + "]"
    return "'" + str(v).replace("\\", "\\\\").replace("'", "\\'") + "'"


def props(d: dict, extra: dict | None = None) -> str:
    merged = dict(d)
    if extra:
        merged.update(extra)
    if not merged:
        return "{}"
    return "{" + ", ".join(f"`{k}`: {literal(v)}"
                           for k, v in sorted(merged.items())) + "}"


def main() -> int:
    uri = os.getenv("NEO4J_URI", "bolt://192.168.4.76:7687")
    auth = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD"))
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "// ccf_dataprep v1 Neo4j graph — replayable export",
        "// Replay with: cypher-shell -u neo4j -p <pw> -f neo4j-v1.cypher",
        "MATCH (n) DETACH DELETE n;",
        "CREATE CONSTRAINT b1id IF NOT EXISTS "
        "FOR (n:`_B1`) REQUIRE n.`_b1id` IS UNIQUE;",
    ]
    driver = GraphDatabase.driver(uri, auth=auth)
    with driver.session() as s:
        nodes = 0
        for rec in s.run("MATCH (n) RETURN n, elementId(n) AS eid"):
            n, eid = rec["n"], rec["eid"]
            labels = "".join(f":`{l}`" for l in sorted(n.labels))
            lines.append(
                f"CREATE (n{labels}:`_B1` {props(dict(n), {'_b1id': eid})});")
            nodes += 1
        rels = 0
        for rec in s.run(
            "MATCH (a)-[r]->(b) RETURN elementId(a) AS a, elementId(b) AS b, "
            "type(r) AS t, properties(r) AS p"
        ):
            lines.append(
                f"MATCH (a:`_B1` {{`_b1id`: {literal(rec['a'])}}}), "
                f"(b:`_B1` {{`_b1id`: {literal(rec['b'])}}}) "
                f"CREATE (a)-[:`{rec['t']}` {props(rec['p'])}]->(b);")
            rels += 1
    driver.close()

    # The scaffolding label and id exist only to reconnect relationships.
    # Leaving them behind would silently add a label to every v1 node.
    lines.append("MATCH (n:`_B1`) REMOVE n:`_B1` REMOVE n.`_b1id`;")
    out.write_text("\n".join(lines) + "\n")
    print(f"  {nodes} nodes, {rels} relationships -> {out}")
    return 0 if nodes else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Run both dumps and check the counts**

Run: `uv run --with neo4j portable/dump/dump_neo4j.py .b1-staging/neo4j-v1.cypher && bash portable/dump/dump_sqlite.sh`
Expected: `14 nodes, 16 relationships`; SQLite reports `tables: source=5 snapshot=5`.

- [ ] **Step 4: Write the two restore scripts**

```bash
# portable/restore/restore_sqlite.sh
#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/platform.sh"
BUNDLE="$(cd "$HERE/.." && pwd)"
ccf_need sqlite3
DEST="${CCF_SQLITE_PATH:-$HOME/ccf-data/departmental.sqlite}"
mkdir -p "$(dirname "$DEST")"
cp "$BUNDLE/v2/primary/departmental.sqlite" "$DEST"
ccf_log "$DEST — $(sqlite3 "$DEST" "select count(*) from sqlite_master where type='table'") tables"
```

```bash
# portable/restore/restore_neo4j.sh
#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/platform.sh"
BUNDLE="$(cd "$HERE/.." && pwd)"
ccf_need cypher-shell
: "${NEO4J_PASSWORD:?set NEO4J_PASSWORD before restoring Neo4j}"
cypher-shell -a "${NEO4J_URI:-bolt://127.0.0.1:7687}" \
  -u "${NEO4J_USER:-neo4j}" -p "$NEO4J_PASSWORD" \
  -f "$BUNDLE/v1/neo4j-v1.cypher"
ccf_log "restored: $(cypher-shell -a "${NEO4J_URI:-bolt://127.0.0.1:7687}" \
  -u "${NEO4J_USER:-neo4j}" -p "$NEO4J_PASSWORD" --format plain \
  'MATCH (n) RETURN count(n)' | tail -1) nodes"
```

- [ ] **Step 5: Verify the Cypher script replays to the same shape**

Replay into the live Neo4j is **not** acceptable as a test — it starts with `DETACH DELETE`. Instead, confirm by inspection that the script contains exactly 14 `CREATE (n` lines and 16 `CREATE (a)-[` lines, and that the final line removes the `_B1` scaffolding:

Run: `grep -c '^CREATE (n' .b1-staging/neo4j-v1.cypher; grep -c 'CREATE (a)-\[' .b1-staging/neo4j-v1.cypher; tail -1 .b1-staging/neo4j-v1.cypher`
Expected: `14`, `16`, and a line removing `:_B1` and `_b1id`.

- [ ] **Step 6: Commit**

```bash
git add portable/dump/dump_sqlite.sh portable/dump/dump_neo4j.py portable/restore/restore_sqlite.sh portable/restore/restore_neo4j.sh
git commit -m "B1 Task 5: SQLite snapshot and Neo4j Cypher export"
```

---

### Task 6: The verifier

**Files:**
- Create: `portable/verify_install.py`
- Test: `portable/tests/test_verify_checks.py`

**Interfaces:**
- Consumes: nothing from the repo — it ships standalone and must not import `ccf.*`
- Produces: `Check` dataclass (`name`, `required`, `found`, `ok`, `detail`), `run_all(cfg) -> list[Check]`, exit codes 0 / 1 / 2

**Landmark values it asserts** (all measured 2026-08-27):

| Store | Landmark |
|---|---|
| Fluree `fibo-v2` | `t = 4468`; 87,162 triples |
| Fluree `fibo` | `t = 5` |
| Fluree `bofa/syndicate` | `t = 16` |
| Postgres `ccf_v2` | 113 tables; `legal_entity` holds 156 rows |
| Postgres `public` | 2 tables |
| MongoDB `fibo_v2` | 6 collections; 38,238 documents |
| MongoDB `fibo` | 30 documents |
| SQLite | 5 tables |
| Neo4j | 14 nodes, 16 relationships |
| Join | every `crosswalk.lei` resolves to a `legal_entity.lei` |

- [ ] **Step 1: Write the failing tests**

```python
# portable/tests/test_verify_checks.py
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "vi", Path(__file__).resolve().parents[1] / "verify_install.py")
vi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vi)


def test_check_is_ok_only_when_found_equals_required():
    assert vi.Check("t", 4468, 4468).ok is True
    assert vi.Check("t", 4468, 4467).ok is False


def test_check_reports_both_numbers_so_a_pass_is_evidence():
    line = vi.Check("triples", 87162, 87162).render()
    assert "87162" in line
    assert "PASS" in line
    bad = vi.Check("triples", 87162, 12).render()
    assert "87162" in bad and "12" in bad and "FAIL" in bad


def test_a_missing_value_is_a_failure_not_a_skip():
    # None means "could not read it" — that must never render as a pass.
    assert vi.Check("triples", 87162, None).ok is False


def test_exit_code_is_1_for_failure_and_0_for_all_green():
    assert vi.exit_code([vi.Check("a", 1, 1)]) == 0
    assert vi.exit_code([vi.Check("a", 1, 1), vi.Check("b", 2, 3)]) == 1


def test_connection_failure_is_exit_2_not_exit_1():
    # A store that cannot be reached is an install problem, not a data problem.
    # Reporting it as a data failure sends the reader to the wrong place.
    assert vi.exit_code([vi.Check("a", 1, 1)], unreachable=["mongodb"]) == 2
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run --with pytest pytest portable/tests/test_verify_checks.py -q`
Expected: FAIL — `verify_install.py` does not exist.

- [ ] **Step 3: Write `portable/verify_install.py`**

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["psycopg[binary]", "pymongo", "neo4j", "requests"]
# ///
"""Confirm a restored ccf_dataprep estate is complete and joined.

Run:  uv run --no-project verify_install.py
 or:  pip install 'psycopg[binary]' pymongo neo4j requests
      python3 verify_install.py

Exit 0 every check passed; 1 a check failed; 2 a store could not be reached.

This asserts LANDMARK VALUES, not liveness. A checker that passes because it
looked at nothing is the defect this estate has recorded most often, so every
check prints the value it found beside the value it required.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from dataclasses import dataclass, field

FLUREE_URL = os.getenv("CCF_FLUREE_URL", "http://127.0.0.1:8090")
PG_DSN = os.getenv("CCF_PG_DSN", "dbname=parkavedb")
PEER_PG_DSN = os.getenv("CCF_PEER_PG_DSN", "dbname=bofa_syndicated")
MONGO_URI = os.getenv("CCF_MONGO_URI", "mongodb://127.0.0.1:27017")
SQLITE_PATH = os.getenv("CCF_SQLITE_PATH",
                        os.path.expanduser("~/ccf-data/departmental.sqlite"))
NEO4J_URI = os.getenv("CCF_NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_AUTH = (os.getenv("CCF_NEO4J_USER", "neo4j"),
              os.getenv("CCF_NEO4J_PASSWORD", ""))


@dataclass
class Check:
    name: str
    required: object
    found: object
    detail: str = ""
    unreachable: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.found is not None and self.found == self.required

    def render(self) -> str:
        status = "PASS" if self.ok else "FAIL"
        got = "unreadable" if self.found is None else self.found
        line = f"  [{status}] {self.name:<44} required {self.required}, got {got}"
        return line + (f"  ({self.detail})" if self.detail else "")


def exit_code(checks: list[Check], unreachable: list | None = None) -> int:
    if unreachable:
        return 2
    return 1 if any(not c.ok for c in checks) else 0


def _sparql(ledger: str, query: str):
    import requests
    r = requests.post(f"{FLUREE_URL}/v1/fluree/query",
                      headers={"Content-Type": "application/sparql-query"},
                      data=query.encode(), timeout=120)
    r.raise_for_status()
    return r.json()["results"]["bindings"]


def check_fluree(checks, unreachable):
    import requests
    try:
        led = requests.get(f"{FLUREE_URL}/v1/fluree/ledgers", timeout=20).json()
    except Exception as e:
        unreachable.append(f"fluree ({e.__class__.__name__})")
        return
    t = {row["name"]: row["t"] for row in led}
    checks.append(Check("fluree fibo-v2 ledger t", 4468, t.get("fibo-v2")))
    checks.append(Check("fluree fibo (v1) ledger t", 5, t.get("fibo")))
    checks.append(Check("fluree bofa/syndicate ledger t", 16,
                        t.get("bofa/syndicate")))
    try:
        n = int(_sparql("fibo-v2",
                        "SELECT (COUNT(*) AS ?n) FROM <fibo-v2> "
                        "WHERE { ?s ?p ?o }")[0]["n"]["value"])
    except Exception:
        n = None
    checks.append(Check("fluree fibo-v2 triples", 87162, n))


def check_postgres(checks, unreachable):
    import psycopg
    try:
        conn = psycopg.connect(PG_DSN, connect_timeout=10)
    except Exception as e:
        unreachable.append(f"postgres ({e.__class__.__name__})")
        return
    with conn, conn.cursor() as cur:
        cur.execute("select current_setting('server_version')")
        ver = cur.fetchone()[0].split(".")[0]
        checks.append(Check("postgres server major version", "16", ver,
                            "pg_restore needs 16 for these dumps"))
        cur.execute("select count(*) from information_schema.tables "
                    "where table_schema='ccf_v2'")
        checks.append(Check("postgres ccf_v2 tables", 113, cur.fetchone()[0]))
        cur.execute("select count(*) from information_schema.tables "
                    "where table_schema='public'")
        checks.append(Check("postgres public (v1) tables", 2,
                            cur.fetchone()[0]))
        cur.execute("select count(*) from ccf_v2.legal_entity")
        checks.append(Check("postgres legal_entity rows", 156,
                            cur.fetchone()[0]))
        # The correlation key. Five stores that each load cleanly but refuse
        # to join is the failure this project was warned about from the start.
        cur.execute("""
            select count(*) from ccf_v2.crosswalk c
            left join ccf_v2.legal_entity e on e.lei = c.lei
            where e.lei is null
        """)
        checks.append(Check("crosswalk LEIs with no legal_entity", 0,
                            cur.fetchone()[0],
                            "the correlation key must resolve"))


def check_mongo(checks, unreachable):
    from pymongo import MongoClient
    try:
        cli = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
        cli.admin.command("ping")
    except Exception as e:
        unreachable.append(f"mongodb ({e.__class__.__name__})")
        return
    # Named explicitly. This file never lists databases.
    v2 = cli["fibo_v2"]
    names = sorted(v2.list_collection_names())
    checks.append(Check("mongo fibo_v2 collections", 6, len(names),
                        ", ".join(names)))
    checks.append(Check("mongo fibo_v2 documents", 38238,
                        sum(v2[c].count_documents({}) for c in names)))
    v1 = cli["fibo"]
    checks.append(Check("mongo fibo (v1) documents", 30,
                        sum(v1[c].count_documents({})
                            for c in v1.list_collection_names())))


def check_sqlite(checks, unreachable):
    if not os.path.exists(SQLITE_PATH):
        unreachable.append(f"sqlite (no file at {SQLITE_PATH})")
        return
    con = sqlite3.connect(SQLITE_PATH)
    n = con.execute("select count(*) from sqlite_master "
                    "where type='table'").fetchone()[0]
    con.close()
    checks.append(Check("sqlite departmental tables", 5, n))


def check_neo4j(checks, unreachable):
    from neo4j import GraphDatabase
    try:
        d = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
        with d.session() as s:
            nodes = s.run("MATCH (n) RETURN count(n) AS c").single()["c"]
            rels = s.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
            scaffold = s.run("MATCH (n:`_B1`) RETURN count(n) AS c"
                             ).single()["c"]
        d.close()
    except Exception as e:
        unreachable.append(f"neo4j ({e.__class__.__name__})")
        return
    checks.append(Check("neo4j v1 nodes", 14, nodes))
    checks.append(Check("neo4j v1 relationships", 16, rels))
    checks.append(Check("neo4j restore scaffolding removed", 0, scaffold,
                        "_B1 label must not survive the replay"))


def run_all():
    checks: list[Check] = []
    unreachable: list[str] = []
    for fn in (check_fluree, check_postgres, check_mongo, check_sqlite,
               check_neo4j):
        fn(checks, unreachable)
    return checks, unreachable


def main() -> int:
    print("ccf_dataprep — portable estate verification\n")
    checks, unreachable = run_all()
    for c in checks:
        print(c.render())
    if unreachable:
        print("\n  COULD NOT REACH: " + "; ".join(unreachable))
        print("  This is an install problem, not a data problem. "
              "See INSTALL-macos.md / INSTALL-ubuntu.md.")
        return 2
    failed = [c for c in checks if not c.ok]
    print(f"\n  {len(checks) - len(failed)} passed, {len(failed)} failed")
    if failed:
        print("  FAILED:")
        for c in failed:
            print(f"    {c.name}: required {c.required}, got {c.found}")
        return 1
    print("  Estate verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the unit tests**

Run: `uv run --with pytest pytest portable/tests/test_verify_checks.py -q`
Expected: PASS, 5 tests

- [ ] **Step 5: Confirm the crosswalk table and column names against the live estate**

The join check names `ccf_v2.crosswalk(lei)`. Verify that table and column actually exist before trusting the check — a check written against a guessed schema fails for the wrong reason:

Run: `uv run python -c "from ccf.config import pg_connect; c=pg_connect(); cur=c.cursor(); cur.execute(\"select column_name from information_schema.columns where table_schema='ccf_v2' and table_name='crosswalk' order by 1\"); print([r[0] for r in cur.fetchall()])"`

If the table or column is named differently, correct `check_postgres` to match the live schema and re-run Step 4.

- [ ] **Step 6: Commit**

```bash
git add portable/verify_install.py portable/tests/test_verify_checks.py
git commit -m "B1 Task 6: standalone estate verifier with landmark assertions"
```

---

### Task 7: Prove the verifier can fail

**Files:**
- Create: `portable/tests/damaged_restore.sh`

**Interfaces:**
- Consumes: `portable/verify_install.py`
- Produces: a record, in the task notes, of the exact failure each damage produces

This is acceptance criterion 4. A verifier never watched to fail is decoration — the estate has recorded checks that passed for seven waves while reading nothing.

- [ ] **Step 1: Restore a full scratch copy on db1**

Restore every store into `_b1chk`-suffixed namespaces (scratch Fluree project, `b1chk_pg`, `b1chk_mongo`, a copied SQLite file). Point the verifier at them with the `CCF_*` environment variables and confirm it exits **0** first. A damage test against an already-failing baseline proves nothing.

- [ ] **Step 2: Write `portable/tests/damaged_restore.sh`**

```bash
#!/usr/bin/env bash
# Each damage must produce a SPECIFIC named failure, not a generic red.
# Run against the scratch namespaces only — never a real one.
set -uo pipefail
: "${CCF_PG_DSN:?point this at the scratch database}"
case "$CCF_PG_DSN" in *b1chk*) ;; *) echo "refusing: not a scratch DSN" >&2; exit 2;; esac

expect_fail() {
  local label="$1"; shift
  echo "== $label"
  "$@" >/dev/null 2>&1
  python3 "$(dirname "$0")/../verify_install.py" > /tmp/b1out.txt 2>&1
  local rc=$?
  if [ "$rc" -eq 0 ]; then
    echo "   DEFECT: verifier passed on a damaged restore"; exit 1
  fi
  echo "   exit $rc; named failure:"
  grep -E '^\s+(FAILED|  )' /tmp/b1out.txt | head -3
}

expect_fail "dropped a Postgres table" \
  psql "$CCF_PG_DSN" -c 'DROP TABLE ccf_v2.legal_entity CASCADE'
expect_fail "truncated a Mongo collection" \
  mongosh --quiet --eval 'db.getSiblingDB("b1chk_mongo").document.deleteMany({})'
expect_fail "swapped the SQLite file for an empty one" \
  sh -c 'rm -f "$CCF_SQLITE_PATH" && sqlite3 "$CCF_SQLITE_PATH" "create table x(a)"'
echo
echo "All damages produced a specific failure."
```

- [ ] **Step 3: Run it and record what each damage reports**

Run: `bash portable/tests/damaged_restore.sh`
Expected: three sections, each exiting non-zero with a named check — `postgres ccf_v2 tables: required 113, got 112`, `mongo fibo_v2 documents`, `sqlite departmental tables: required 5, got 1`. Paste the actual output into the task notes.

- [ ] **Step 4: Add the fourth damage — a short Fluree restore**

Restore `fibo-v2` from a `.flpack` truncated to fewer commits (build one with `fluree export --no-indexes` from a store rolled back by dropping the last commit files), and confirm the verifier reports `fluree fibo-v2 ledger t: required 4468, got <lower>`.

If the truncated archive cannot be built in reasonable time, record that plainly in the task notes as an untested damage rather than claiming four when three were run.

- [ ] **Step 5: Rebuild the scratch restore and confirm green again**

Re-run the full restore into the scratch namespaces and confirm `verify_install.py` exits 0. This proves the damages were the cause, not the test harness.

- [ ] **Step 6: Commit**

```bash
git add portable/tests/damaged_restore.sh
git commit -m "B1 Task 7: prove the verifier fails on damaged restores"
```

---

### Task 8: Install guides, bundle README, and the orchestrator

**Files:**
- Create: `portable/bundle/README.md`, `portable/bundle/INSTALL-macos.md`, `portable/bundle/INSTALL-ubuntu.md`
- Create: `portable/dump/dump_all.sh`
- Create: `portable/README.md`

**Interfaces:**
- Consumes: every dump script from Tasks 2–5, `portable/manifest.py`
- Produces: a complete `/data/laptop` bundle with `MANIFEST.json`

- [ ] **Step 1: Write the two install guides**

Each must be a literal copy-paste sequence, pinned, ending at the point where `restore_all.sh` is run. Required content in both:

- Install the five engines at the pinned versions from the Global Constraints.
- **`mongodb-database-tools` named explicitly** — `mongorestore` is not in the server package on either platform.
- **Postgres pinned to 16** — `brew install postgresql` gives 17, `apt install postgresql` gives whatever the release ships; both are wrong against these dumps.
- Start each service (`brew services start` / `systemctl start`).
- Set `NEO4J_PASSWORD` and any non-default connection variables.
- Run `bash restore/restore_all.sh`, then `uv run --no-project verify_install.py`.
- State that `verify_install.py` exiting 2 means a store is unreachable — an install problem, not a data problem.

macOS-specific: Homebrew paths differ between Apple silicon (`/opt/homebrew`) and Intel (`/usr/local`); `platform.sh` probes both, but `brew --prefix` is the reliable way to confirm.
Ubuntu-specific: Postgres 16 comes from the PGDG apt repository on 22.04 and is in the archive on 24.04 — the guide uses PGDG for both so one instruction covers each release.

- [ ] **Step 2: Write `portable/dump/dump_all.sh`**

```bash
#!/usr/bin/env bash
# Full bundle build. Runs on db1. Safely re-runnable.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/common.sh"
REPO="${REPO:-/home/parkave/ccf_dataprep}"
ccf_require_dir "$BUNDLE_ROOT"

mkdir -p "$BUNDLE_ROOT/v1" "$BUNDLE_ROOT/v2/primary" "$BUNDLE_ROOT/v2/colender" \
         "$BUNDLE_ROOT/restore"

bash "$HERE/dump_fluree.sh"
bash "$HERE/dump_postgres.sh"
bash "$HERE/dump_mongo.sh"
python3 "$HERE/dump_neo4j.py" "$BUNDLE_ROOT/v1/neo4j-v1.cypher"
ccf_log "SQLite is shipped from the workstation by dump_sqlite.sh — not here"

ccf_step "staging shipped scripts and docs"
cp "$REPO"/portable/restore/*.sh "$BUNDLE_ROOT/restore/"
cp "$REPO"/portable/verify_install.py "$BUNDLE_ROOT/"
cp "$REPO"/portable/bundle/README.md "$BUNDLE_ROOT/"
cp "$REPO"/portable/bundle/INSTALL-macos.md "$BUNDLE_ROOT/"
cp "$REPO"/portable/bundle/INSTALL-ubuntu.md "$BUNDLE_ROOT/"
chmod +x "$BUNDLE_ROOT"/restore/*.sh

ccf_step "manifest"
python3 - "$BUNDLE_ROOT" <<'PY'
import sys
sys.path.insert(0, "/home/parkave/ccf_dataprep")
from pathlib import Path
from portable.manifest import add_artifact, write_manifest

root = Path(sys.argv[1])
spec = [
    ("v1/fluree-fibo.flpack", "fluree", "v1", "fluree export --format ledger"),
    ("v1/postgres-public.dump", "postgres", "v1", "pg_dump -Fc"),
    ("v1/mongo-fibo", "mongodb", "v1", "mongodump --db fibo --gzip"),
    ("v1/neo4j-v1.cypher", "neo4j", "v1", "cypher export via bolt"),
    ("v2/primary/fluree-fibo-v2.flpack", "fluree", "v2-primary", "fluree export --format ledger"),
    ("v2/primary/postgres-ccf_v2.dump", "postgres", "v2-primary", "pg_dump -Fc"),
    ("v2/primary/mongo-fibo_v2", "mongodb", "v2-primary", "mongodump --db fibo_v2 --gzip"),
    ("v2/primary/departmental.sqlite", "sqlite", "v2-primary", "VACUUM INTO"),
    ("v2/colender/fluree-bofa-syndicate.flpack", "fluree", "v2-colender", "fluree export via docker exec"),
    ("v2/colender/postgres-colender.dump", "postgres", "v2-colender", "pg_dump -Fc"),
    ("v2/colender/mongo-bofa_syndicated", "mongodb", "v2-colender", "mongodump --db bofa_syndicated --gzip"),
]
entries = []
for rel, store, fabric, method in spec:
    p = root / rel
    if not p.exists():
        print(f"  MISSING: {rel}")
        continue
    extra = {}
    # The peer MongoDB is legitimately empty. Say so in the manifest, or a
    # later reader will mistake an empty directory for a failed dump.
    if store == "mongodb" and not any(p.rglob("*.bson.gz")):
        extra["empty"] = True
    entries.append(add_artifact(root, rel, store=store, fabric=fabric,
                                method=method, extra=extra))
path = write_manifest(root, entries)
print(f"  {len(entries)} artifacts -> {path}")
PY

ccf_step "bundle size"
du -sh "$BUNDLE_ROOT"
```

- [ ] **Step 3: Write `restore_all.sh`**

```bash
#!/usr/bin/env bash
# Ordered restore. The stores are independent, but the verifier's join checks
# need Postgres and Fluree both present.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/platform.sh"
echo "Restoring the ccf_dataprep estate on $CCF_OS"
for s in fluree postgres mongo sqlite neo4j; do
  echo ""
  echo "== $s"
  bash "$HERE/restore_$s.sh"
done
echo ""
echo "Now run:  uv run --no-project ../verify_install.py"
```

- [ ] **Step 4: Build the full bundle and check the manifest**

Run `dump_all.sh` on db1, then `dump_sqlite.sh` from the workstation, then re-run the manifest step so the SQLite entry is included.

Expected: `MANIFEST.json` lists **11 artifacts**, each with a non-empty sha256, and the peer MongoDB entry carries `"empty": true`.

- [ ] **Step 5: Verify the manifest hashes actually match the files**

Run: `ssh parkave@192.168.4.76 'cd /data/laptop && python3 -c "
import json,hashlib,pathlib
d=json.load(open(\"MANIFEST.json\"))
bad=0
for a in d[\"artifacts\"]:
    p=pathlib.Path(a[\"path\"])
    h=hashlib.sha256()
    if p.is_file(): h.update(p.read_bytes())
    else:
        for c in sorted(x for x in p.rglob(\"*\") if x.is_file()):
            h.update(c.relative_to(p).as_posix().encode()); h.update(b\"\\0\"); h.update(c.read_bytes())
    if h.hexdigest()!=a[\"sha256\"]: print(\"MISMATCH\",a[\"path\"]); bad+=1
print(\"artifacts\",len(d[\"artifacts\"]),\"mismatched\",bad)
"'`

Expected: `mismatched 0`. A manifest that records hashes nobody re-computes is a hash nobody can trust.

- [ ] **Step 6: Commit**

```bash
git add portable/bundle/ portable/dump/dump_all.sh portable/restore/restore_all.sh portable/README.md
git commit -m "B1 Task 8: install guides, bundle orchestrator, manifest"
```

---

### Task 9: Full Ubuntu rehearsal on db1

**Files:** none created — this task produces evidence, recorded in `docs/b1-portable-dump-design.md`

This is acceptance criteria 2, 3 and 7. db1 is Ubuntu 24.04, so running the restore there **is** the Ubuntu test. Only the macOS branch is first exercised on the night.

- [ ] **Step 1: Restore every store into scratch namespaces**

Use `_b1chk` names throughout: a scratch Fluree project directory, `b1chk_pg`, `b1chk_mongo`, a copied SQLite path, and — because Neo4j's replay begins with `DETACH DELETE` — **skip the Neo4j restore here** and record it as verified only on the laptop. Damaging the live v1 graph to rehearse is not a trade worth making for 14 nodes.

- [ ] **Step 2: Run the verifier against the scratch namespaces**

Point every `CCF_*` variable at the scratch namespaces and run `uv run --no-project portable/verify_install.py`.
Expected: exit 0, with the Neo4j checks reported as unreachable-or-skipped and that fact written down, not glossed.

- [ ] **Step 3: Run the damaged-restore suite**

Run `portable/tests/damaged_restore.sh` against the scratch namespaces. Expected: every damage produces a specific named failure.

- [ ] **Step 4: Confirm the shipped scripts are the committed ones**

Run: `ssh parkave@192.168.4.76 'cd /data/laptop && for f in restore/*.sh verify_install.py; do echo "$(sha256sum "$f" | cut -c1-16)  $f"; done'` and compare against `sha256sum` of the repo copies.
Expected: identical digests. A bundle carrying a hand-edited script that differs from the repo is how the next person restores something nobody can reproduce.

- [ ] **Step 5: Tear down the scratch namespaces**

Drop `b1chk_pg`, drop `b1chk_mongo`, remove the scratch Fluree project and SQLite copy. Confirm the live estate is untouched: `fibo-v2` still at t=4468, `ccf_v2` still 113 tables.

- [ ] **Step 6: Record the rehearsal in the design doc and commit**

Append a "Rehearsal, 2026-08-27" section to `docs/b1-portable-dump-design.md` with the actual numbers observed and anything that did not work first time.

```bash
git add docs/b1-portable-dump-design.md
git commit -m "B1 Task 9: Ubuntu rehearsal on db1, evidence recorded"
```

---

### Task 10: Correct the stale records

**Files:**
- Modify: `docs/backlog.md`
- Modify: `docs/known-issues.md`
- Modify: `docs/HANDOFF.md`

- [ ] **Step 1: Correct the backlog's sizing table**

`docs/backlog.md` §B1 records MongoDB 375 MB / 211 MB, Postgres 68 MB / 62 tables, Fluree 55,751 triples at t=1315. Measured 2026-08-27: MongoDB `fibo_v2` 576 MB data / 329 MB stored across 38,238 docs; Postgres `ccf_v2` **718 MB / 113 tables**; Fluree **87,162 triples at t=4468**, 47 GB on disk. Replace the table and date it.

- [ ] **Step 2: Correct the backlog's Fluree paragraph**

§B1 states "Fluree 4.1.4 has no backup, snapshot, export or dump endpoint — all four paths return 404". That is true of the **HTTP endpoints** and false of the **CLI**, which has `fluree export --format ledger` producing a `.flpack`, and `fluree history` with a working `--from/--to`. Correct it without deleting the original observation — the HTTP finding is still true and still useful.

- [ ] **Step 3: Add the index-bloat finding to known-issues**

New entry: `fibo-v2` carries ~1,421 accumulated index generations, 46 GB, because `reindex_min_bytes = 100` reindexes on nearly every commit and nothing collects the superseded generations, though `index/garbage/` records exactly which objects are dead. One current index is 47 MB / 18 files / 1.5 s and makes queries 550× faster. Growth is roughly 33 MB per commit, indefinitely. Not acted on — reclaiming it touches the authoritative ledger.

- [ ] **Step 4: Add the as-of finding to known-issues**

New entry: on Fluree 4.1.4/4.1.6, `/v1/fluree/history` returns 404 and the `t` query parameter is **silently ignored** — a query at `t=100` returns the full current graph, on a live server. Any claim in this estate that as-of reconstruction is queryable over HTTP is false. The CLI's `fluree history --from/--to` does work. Note that the silent-ignore is the dangerous half: it returns a plausible number rather than an error.

- [ ] **Step 5: Update HANDOFF.md**

Record B1's state, the bundle location, how to rebuild it, and that the macOS branch of the restore scripts is unexercised until the laptop night.

- [ ] **Step 6: Commit**

```bash
git add docs/backlog.md docs/known-issues.md docs/HANDOFF.md
git commit -m "B1 Task 10: correct stale sizing, Fluree export and as-of records"
```

---

## Self-Review

**Spec coverage.** Every design section maps to a task: layout and manifest → 1, 8; Fluree method → 2; Postgres → 3; MongoDB and its guard → 4; SQLite and Neo4j → 5; the verifier and its landmark values → 6; acceptance criterion 4 → 7; install guides and restore order → 8; criteria 2, 3, 7 → 9; criterion 6 → 10. Criterion 5 was completed during design and is marked done in the spec.

**Two deliberate deviations from the design, both narrowing:**
1. Neo4j is exported as a Cypher script rather than `neo4j-admin database dump` — that command refuses a running database, verified 2026-08-27. The design was updated to match before this plan was written.
2. The Neo4j **restore** is not rehearsed on db1 (Task 9 Step 1), because its replay opens with `DETACH DELETE` and the only Neo4j available is the live v1 graph. It is first exercised on the laptop. This is a real gap and is written down rather than hidden.

**Placeholder scan.** No TBD, no "add error handling", no "similar to Task N". Every code step carries the code. Task 8 Step 1 specifies install-guide content as a required list rather than full prose — the guides are documentation whose exact wording depends on what Task 9 finds, and the required elements are enumerated.

**Type consistency.** `Check(name, required, found, detail, unreachable)`, `.ok`, `.render()`, `exit_code(checks, unreachable=None)`, `run_all()` are used identically in Task 6's tests and implementation. `add_artifact(root, rel_path, *, store, fabric, method, extra)` and `write_manifest(root, entries)` match between Task 1's tests, Task 1's implementation, and Task 8's manifest step. `assert_mongo_db_allowed` / `MongoScopeError` match across Tasks 1 and 4. `ccf_sha256`, `ccf_need`, `ccf_log`, `CCF_OS`, `PG_BIN` are defined in Task 1's `platform.sh` and used unchanged in Tasks 2–5 and 8.
