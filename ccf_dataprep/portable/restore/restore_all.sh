#!/usr/bin/env bash
# Ordered restore. The stores are independent, but the verifier's join checks
# need Postgres and Fluree both present.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/platform.sh"
echo "Restoring the ccf_dataprep estate on $CCF_OS"
echo ""
echo "== fluree"
bash "$HERE/restore_fluree.sh"

echo ""
echo "== fluree server reachability"
# restore_fluree.sh only creates ledgers -- it never starts a server, and the
# verifier needs one reachable. Catching that HERE, right after the ledgers
# were just restored, turns the verifier's later exit-2 "unreachable" (which
# reads as an install problem and sends the operator hunting in the wrong
# place) into an actionable message at the moment the cause exists. This
# never starts a server itself -- that would leave a background process the
# operator never asked for.
CCF_FLUREE_URL="${CCF_FLUREE_URL:-http://127.0.0.1:8090}"
if curl -s -o /dev/null -m 3 "$CCF_FLUREE_URL"; then
  ccf_log "reachable: $CCF_FLUREE_URL"
else
  echo "" >&2
  echo "Ledgers restored fine, but no Fluree server is reachable at $CCF_FLUREE_URL." >&2
  echo "Start one, then re-run the verifier:" >&2
  echo "" >&2
  echo "  ( cd \$CCF_FLUREE_HOME && nohup fluree server run --listen-addr 127.0.0.1:8090 )" >&2
  echo "" >&2
  echo "See the install guide's \"start the Fluree server\" step (INSTALL-macos.md / INSTALL-ubuntu.md)." >&2
  exit 2
fi

# Run the reachability probe (above) BEFORE these four, not after: if any of
# them fails (missing cypher-shell, unset NEO4J_PASSWORD, a Postgres role
# problem), `set -e` stops this script right there and the probe -- the
# thing that turns the verifier's generic exit-2 into an actionable message
# -- would never run. Fluree has no such dependency on the other four, so
# there is no reason its own check has to wait on them.
for s in postgres mongo sqlite neo4j; do
  echo ""
  echo "== $s"
  bash "$HERE/restore_$s.sh"
done

echo ""
echo "Now run:  uv run --no-project verify_install.py"
