#!/usr/bin/env bash
#
# restore.sh — the one command that restores the ccf_dataprep estate.
#
# Run it from inside the unpacked bundle, after installing the engines
# (INSTALL-ubuntu.md / INSTALL-macos.md):
#
#     export NEO4J_PASSWORD='the-password-you-set'   # optional, see below
#     bash restore.sh
#
# It does, in order, everything the install guides used to list as separate
# steps, and stops at the first one that fails:
#
#   1. verify_bundle.sh   every artifact matches MANIFEST.json
#   2. Fluree             native CLI, or the Intel-Mac `ccf-fluree` container
#   3. Fluree server      started here if nothing serves 127.0.0.1:8090
#   4. Postgres, MongoDB, SQLite, Neo4j
#   5. verify_install.py  the acceptance test; its exit code is ours
#
# Neo4j is optional. With no NEO4J_PASSWORD (or CCF_NEO4J_PASSWORD) set, or no
# cypher-shell installed, it is skipped and the verifier is told so; the
# result then says "excluding neo4j" rather than claiming a full pass.
#
# Safe to re-run. Every restore script drops and recreates what it owns.
#
# Exit codes are the verifier's: 0 verified, 1 a check failed, 2 a store was
# unreachable (an install problem, not a data problem). A failure before the
# verifier runs exits with that step's own code.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
. "$HERE/restore/platform.sh"

export CCF_FLUREE_HOME="${CCF_FLUREE_HOME:-$HOME/ccf-fluree}"
export CCF_FLUREE_URL="${CCF_FLUREE_URL:-http://127.0.0.1:8090}"
export CCF_SQLITE_PATH="${CCF_SQLITE_PATH:-$HOME/ccf-data/departmental.sqlite}"
# The restore reads NEO4J_PASSWORD, the verifier CCF_NEO4J_PASSWORD. Either
# one set is enough; both get the same value.
NEO4J_PASSWORD="${NEO4J_PASSWORD:-${CCF_NEO4J_PASSWORD:-}}"
export NEO4J_PASSWORD CCF_NEO4J_PASSWORD="$NEO4J_PASSWORD"

FLUREE_CONTAINER="${CCF_FLUREE_CONTAINER:-ccf-fluree}"
PIDFILE="$CCF_FLUREE_HOME/.ccf-server.pid"

step() { printf '\n== %s\n' "$*"; }
fail() { printf '\nSTOPPED: %s\n' "$1" >&2; exit "${2:-1}"; }

fluree_up() { curl -s -o /dev/null -m 3 "$CCF_FLUREE_URL"; }
wait_fluree() {
  local _
  for _ in $(seq 1 30); do fluree_up && return 0; sleep 1; done
  return 1
}

# --- 1. bundle integrity ---------------------------------------------------
step "1/5 checking the bundle"
bash "$HERE/verify_bundle.sh" || fail "the bundle is damaged or incomplete — fetch it again" $?

# --- 2+3. Fluree -------------------------------------------------------------
if command -v fluree >/dev/null 2>&1; then
  FLUREE_MODE=native
elif command -v docker >/dev/null 2>&1 \
     && docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$FLUREE_CONTAINER"; then
  FLUREE_MODE=docker
else
  echo "MISSING: fluree" >&2
  echo "  Install Fluree 4.2.4 per INSTALL-${CCF_OS}.md, or on an Intel Mac start" >&2
  echo "  the '$FLUREE_CONTAINER' Docker container that guide describes." >&2
  exit 2
fi

step "2/5 Fluree ($FLUREE_MODE)"
if [ "$FLUREE_MODE" = native ]; then
  # A server this script started on an earlier run is holding the storage the
  # restore is about to replace: stop it first, start a fresh one after.
  if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    pid="$(cat "$PIDFILE")"
    ccf_log "stopping the Fluree server a previous run started (pid $pid)"
    kill "$pid" 2>/dev/null || true
    # Wait for the PROCESS to go, not the port: a closing server can still
    # answer for a moment. Escalate if it ignores the polite signal.
    for _ in $(seq 1 20); do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
    kill -0 "$pid" 2>/dev/null && { kill -9 "$pid" 2>/dev/null || true; sleep 1; }
    for _ in $(seq 1 10); do fluree_up || break; sleep 1; done
  fi
  rm -f "$PIDFILE"
  if fluree_up; then
    fail "something is already serving $CCF_FLUREE_URL, and this script did not
start it. The verifier would check THAT server, not the one restored here.
Stop it (or set CCF_FLUREE_URL to a free port) and re-run." 2
  fi

  bash "$HERE/restore/restore_fluree.sh"

  step "3/5 starting the Fluree server"
  port="${CCF_FLUREE_URL##*:}"; port="${port%%/*}"
  # cd on its own line: `cd X && nohup fluree … &` backgrounds the whole
  # `&&` list as a subshell, so $! would be that wrapper's pid, and killing it
  # on the next run leaves the real server holding the port.
  ( cd "$CCF_FLUREE_HOME" || exit 1
    nohup fluree server run --listen-addr "127.0.0.1:$port" \
      > "$CCF_FLUREE_HOME/server.log" 2>&1 &
    echo $! > "$PIDFILE" )
  wait_fluree || fail "the Fluree server did not come up on $CCF_FLUREE_URL — see $CCF_FLUREE_HOME/server.log" 2
  ccf_log "serving $CCF_FLUREE_URL (pid $(cat "$PIDFILE"), log $CCF_FLUREE_HOME/server.log)"
else
  # Intel Mac: the CLI exists only inside the container, which must have
  # this bundle mounted at /bundle (INSTALL-macos.md's `docker run`).
  docker exec "$FLUREE_CONTAINER" test -f /bundle/MANIFEST.json \
    || fail "container '$FLUREE_CONTAINER' has no bundle at /bundle. Re-create it
from inside this folder with the docker run command in INSTALL-macos.md." 2
  for pair in "fibo-v2:v2/primary/fluree-fibo-v2.flpack" \
              "fibo:v1/fluree-fibo.flpack" \
              "bofa/syndicate:v2/colender/fluree-bofa-syndicate.flpack"; do
    ledger="${pair%%:*}"; pack="${pair#*:}"
    ccf_log "restoring $ledger"
    docker exec "$FLUREE_CONTAINER" fluree drop "$ledger" --force >/dev/null 2>&1 || true
    docker exec "$FLUREE_CONTAINER" fluree create "$ledger" --from "/bundle/$pack"
  done
  step "3/5 Fluree server"
  wait_fluree || fail "container '$FLUREE_CONTAINER' is not serving $CCF_FLUREE_URL" 2
  ccf_log "the container serves $CCF_FLUREE_URL; the verifier checks each ledger's t"
fi

# --- 4. the other stores ----------------------------------------------------
step "4/5 Postgres, MongoDB, SQLite, Neo4j"
for s in postgres mongo sqlite; do
  printf '\n-- %s\n' "$s"
  bash "$HERE/restore/restore_$s.sh"
done

printf '\n-- neo4j\n'
if [ -z "$NEO4J_PASSWORD" ] || ! command -v cypher-shell >/dev/null 2>&1; then
  ccf_log "SKIPPED: $( [ -z "$NEO4J_PASSWORD" ] && echo 'no NEO4J_PASSWORD set' || echo 'cypher-shell not installed')."
  ccf_log "Neo4j is optional; it holds nothing the other four stores lack."
  export CCF_SKIP_STORES="${CCF_SKIP_STORES:+$CCF_SKIP_STORES,}neo4j"
else
  bash "$HERE/restore/restore_neo4j.sh"
fi

# --- 5. acceptance test -----------------------------------------------------
step "5/5 verifying the estate"
set +e
if command -v uv >/dev/null 2>&1; then
  uv run --no-project "$HERE/verify_install.py"
  rc=$?
else
  # No uv: a private venv, never a bare pip install (both platforms' system
  # Python refuse one under PEP 668).
  VENV="$HOME/.cache/ccf-verify-venv"
  if [ ! -x "$VENV/bin/python" ]; then
    ccf_log "no uv — building a one-off venv at $VENV"
    python3 -m venv "$VENV" && "$VENV/bin/pip" -q install 'psycopg[binary]' pymongo neo4j requests \
      || fail "could not build the verifier's venv (Ubuntu: sudo apt-get install -y python3-venv)" 2
  fi
  "$VENV/bin/python" "$HERE/verify_install.py"
  rc=$?
fi
set -e

if [ "$rc" -eq 0 ]; then
  cat <<EOF

Restore complete. To point a ccf_dataprep clone at it, put these in its .env:

  FLUREE_URL=$CCF_FLUREE_URL
  PGHOST=127.0.0.1
  PGPORT=5432
  PGDATABASE=parkavedb
  PGUSER=$(id -un)
  MONGO_URI=${CCF_MONGO_URI:-mongodb://127.0.0.1:27017}
  SQLITE_PATH=$CCF_SQLITE_PATH
  NEO4J_URI=${NEO4J_URI:-bolt://127.0.0.1:7687}
  NEO4J_USER=${NEO4J_USER:-neo4j}
  NEO4J_PASSWORD=<the password you set>
EOF
  if [ "$FLUREE_MODE" = native ]; then
    echo ""
    echo "The Fluree server keeps running in the background. Stop it with:"
    echo "  kill \$(cat $PIDFILE)"
  fi
fi
exit "$rc"
