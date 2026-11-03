#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/platform.sh"
BUNDLE="$(cd "$HERE/.." && pwd)"
[ -n "$PG_BIN" ] && PATH="$PG_BIN:$PATH" && export PATH
ccf_need psql pg_restore createdb createuser

PGDB="${CCF_PGDATABASE:-parkavedb}"
PEERDB="${CCF_CO_LENDER_PGDATABASE:-bofa_syndicated}"

# CORRECTED: the brief's original form connected to a database named
# "postgres" to read the server version. That database exists on db1, but
# Homebrew's postgresql@16 on macOS creates a database named after the local
# user and does NOT reliably create "postgres". template1 exists in every
# PostgreSQL cluster by definition, so bootstrap queries connect there.
server_major="$(psql -tAc 'show server_version' template1 | cut -d. -f1)"
if [ "$server_major" != "16" ]; then
  echo "Postgres server is major version $server_major; these dumps are 16." >&2
  echo "pg_restore cannot read a 16 custom-format dump into an older server," >&2
  echo "and a newer one may reject it. Install postgresql@16." >&2
  exit 2
fi

# A missing or empty dump file is a broken bundle, not a notice to forgive.
# Check every path before attempting any restore.
require_dump() {
  local path="$1"
  if [ ! -f "$path" ]; then
    echo "MISSING DUMP: $path" >&2
    exit 2
  fi
  if [ ! -s "$path" ]; then
    echo "EMPTY DUMP: $path" >&2
    exit 2
  fi
}

CCF_V2_DUMP="$BUNDLE/v2/primary/postgres-ccf_v2.dump"
PUBLIC_DUMP="$BUNDLE/v1/postgres-public.dump"
COLENDER_DUMP="$BUNDLE/v2/colender/postgres-colender.dump"

require_dump "$CCF_V2_DUMP"
require_dump "$PUBLIC_DUMP"
require_dump "$COLENDER_DUMP"

createdb "$PGDB" 2>/dev/null || ccf_log "$PGDB exists"
createdb "$PEERDB" 2>/dev/null || ccf_log "$PEERDB exists"

# --clean --if-exists makes this re-runnable. Without it a second run leaves
# every table intact and reports only constraint errors, which reads as noise.
# pg_restore's exit status is still tolerated here: a first run against an
# empty database logs benign "DROP ... does not exist" notices as errors, and
# distinguishing those from a real failure by exit code alone is not
# reliable. The count assertions below are what actually prove the restore
# landed.
pg_restore --clean --if-exists --no-owner --no-privileges \
  --dbname="$PGDB" "$CCF_V2_DUMP" || true
pg_restore --clean --if-exists --no-owner --no-privileges \
  --dbname="$PGDB" "$PUBLIC_DUMP" || true
pg_restore --clean --if-exists --no-owner --no-privileges \
  --dbname="$PEERDB" "$COLENDER_DUMP" || true

# Prove each restore landed: assert the expected BASE TABLE count per
# target/schema. Unfiltered information_schema.tables would also count views
# (ccf_v2 carries 2), so this filters to table_type='BASE TABLE' explicitly.
assert_table_count() {
  local db="$1" schema="$2" expected="$3" found
  found="$(psql -tAc "select count(*) from information_schema.tables where table_schema='$schema' and table_type='BASE TABLE'" "$db")"
  found="$(echo "$found" | tr -d '[:space:]')"
  if [ "$found" != "$expected" ]; then
    echo "RESTORE MISMATCH: $db.$schema expected=$expected found=$found" >&2
    exit 1
  fi
  ccf_log "$db.$schema base tables: $found (expected $expected)"
}

assert_table_count "$PGDB" ccf_v2 116
assert_table_count "$PGDB" public 2
assert_table_count "$PEERDB" colender 2
