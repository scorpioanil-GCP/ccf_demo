#!/usr/bin/env bash
# Every invocation names its database. There is deliberately no loop over a
# database list: db1's MongoDB also carries `rtdetect`, ~5.5M documents of an
# unrelated live system, and enumeration is how it would get swept up.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/common.sh"
# CORRECTED: the repo is not checked out on db1 and it has no uv install —
# only bare python3. `portable/` (not just `portable/dump/`) is staged to
# this path by rsync before this script runs, so `from portable.manifest
# import ...` resolves against the staged tree, and manifest.py being pure
# stdlib means bare python3 3.12 runs it with no virtualenv.
REPO="${REPO:-/data/data_bundle/.scripts}"

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
