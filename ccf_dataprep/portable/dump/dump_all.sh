#!/usr/bin/env bash
# Full bundle build. WORKSTATION-side orchestrator. Safely re-runnable.
#
# CORRECTED 2026-08-27: the repo is NOT checked out on db1, and db1 has no
# `uv` install -- bare python3 3.12.3 only. So this script runs HERE, on the
# machine holding the repo checkout (this laptop/workstation), and:
#
#   1. stages `portable/` to db1 over rsync
#   2. ssh-runs the three db1-side dumps (Fluree, Postgres, MongoDB) from
#      that staged copy
#   3. runs the two workstation-side dumps LOCALLY -- they ship their own
#      output up to db1 themselves (dump_sqlite.sh, dump_neo4j.py)
#   4. builds MANIFEST.json on db1 with bare python3, against the staged tree
#
# Re-run this after dump_sqlite.sh so the manifest picks up the SQLite
# artifact -- see docs/b1-portable-dump-plan.md Ruling C7. Every stage here
# is itself idempotent, so a second full run is safe and expected.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
. "$HERE/common.sh"

REMOTE="${REMOTE:-parkave@192.168.4.76}"
REMOTE_SCRIPTS="${REMOTE_SCRIPTS:-$BUNDLE_ROOT/.scripts}"

ccf_step "staging portable/ to $REMOTE:$REMOTE_SCRIPTS"
# Create the parent first -- mkdir -p on the far end does not nest through
# rsync; rsync will not create $REMOTE_SCRIPTS itself if it is missing.
ssh "$REMOTE" "mkdir -p '$REMOTE_SCRIPTS'"
# --delete: a script removed here must not linger staged on db1 forever.
rsync -a --delete "$REPO/portable/" "$REMOTE:$REMOTE_SCRIPTS/portable/"

ccf_step "bundle directories on $REMOTE"
ssh "$REMOTE" "mkdir -p '$BUNDLE_ROOT/v1' '$BUNDLE_ROOT/v2/primary' '$BUNDLE_ROOT/v2/colender' '$BUNDLE_ROOT/restore'"

# --- credentials the db1-side dump scripts need ----------------------------
# Peer Postgres and peer MongoDB credentials live in THIS workstation's own
# ~/.bashrc, not db1's (Task 3's finding) -- and none of this may ever be
# printed. A local temp file (chmod 600) is written from this shell's own
# env vars, shipped to db1, sourced there by run_db1_dumps.sh, and removed
# from both ends. The command text below never contains a literal secret --
# only variable names -- so nothing is printed even if this script's own
# invocation is echoed.
CREDS_LOCAL="$(mktemp)"
CREDS_REMOTE="$REMOTE_SCRIPTS/.ccf_env"
cleanup() {
  rm -f "$CREDS_LOCAL"
  ssh "$REMOTE" "rm -f '$CREDS_REMOTE'" 2>/dev/null || true
}
trap cleanup EXIT

chmod 600 "$CREDS_LOCAL"
cat > "$CREDS_LOCAL" <<EOF
export PGPASSWORD='${PGPASSWORD:-}'
export CO_LENDER_PG_USER='${CO_LENDER_PG_USER:-colender}'
export CO_LENDER_PG_DB='${CO_LENDER_PG_DB:-bofa_syndicated}'
export CO_LENDER_PG_PASSWORD='${CO_LENDER_PG_PASSWORD:-}'
export CO_LENDER_MONGO_URI='${CO_LENDER_MONGO_URI:?peer Mongo URI not set in this shell -- see ~/.bashrc}'
EOF
rsync -a "$CREDS_LOCAL" "$REMOTE:$CREDS_REMOTE"
ssh "$REMOTE" "chmod 600 '$CREDS_REMOTE'"

ccf_step "db1-side dumps: Fluree, Postgres, MongoDB"
ssh "$REMOTE" "bash '$REMOTE_SCRIPTS/portable/dump/run_db1_dumps.sh' '$CREDS_REMOTE'"

# Credentials are no longer needed -- remove them now rather than waiting for
# the trap, so they sit on disk for as little time as possible.
cleanup
trap - EXIT

ccf_step "workstation-side dumps: SQLite, Neo4j -- these ship their own output"
bash "$HERE/dump_sqlite.sh"
uv run "$HERE/dump_neo4j.py" "$REPO/.b1-staging/neo4j-v1.cypher"

ccf_step "leftover scratch on $REMOTE"
# dump_fluree.sh clears its OWN subdirectory ($BUNDLE_ROOT/.work/fluree) but
# leaves the now-empty .work parent behind. Clean it here so dump_all.sh
# never leaves scratch, on this run or a prior one.
ssh "$REMOTE" "rm -rf '$BUNDLE_ROOT/.work'"

ccf_step "staging shipped scripts and docs from $REMOTE:$REMOTE_SCRIPTS"
ssh "$REMOTE" "bash '$REMOTE_SCRIPTS/portable/dump/stage_bundle_files.sh' '$BUNDLE_ROOT' '$REMOTE_SCRIPTS/portable'"

ccf_step "manifest"
ssh "$REMOTE" "python3 '$REMOTE_SCRIPTS/portable/dump/build_manifest.py' '$BUNDLE_ROOT'"

ccf_step "bundle size"
# -L: $BUNDLE_ROOT (/data/data_bundle) is itself a symlink to /data/mongodb/data_bundle.
ssh "$REMOTE" "du -shL '$BUNDLE_ROOT'"
