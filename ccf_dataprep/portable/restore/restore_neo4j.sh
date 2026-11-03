#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/platform.sh"
BUNDLE="$(cd "$HERE/.." && pwd)"
ccf_need cypher-shell
# Accept either name: restore_neo4j.sh has always read NEO4J_PASSWORD,
# but verify_install.py reads CCF_NEO4J_PASSWORD -- two different names
# for the same value is exactly the kind of thing that gets missed
# once, at night. Either alone is now enough.
NEO4J_PASSWORD="${NEO4J_PASSWORD:-${CCF_NEO4J_PASSWORD:-}}"
: "${NEO4J_PASSWORD:?set NEO4J_PASSWORD or CCF_NEO4J_PASSWORD before restoring Neo4j}"

URI="${NEO4J_URI:-bolt://127.0.0.1:7687}"
USER="${NEO4J_USER:-neo4j}"
SCRIPT="$BUNDLE/v1/neo4j-v1.cypher"

# A missing or empty script is a broken bundle, not a notice to forgive.
if [ ! -f "$SCRIPT" ]; then
  echo "MISSING SCRIPT: $SCRIPT" >&2
  exit 2
fi
if [ ! -s "$SCRIPT" ]; then
  echo "EMPTY SCRIPT: $SCRIPT" >&2
  exit 2
fi

# The script itself opens with `MATCH (n) DETACH DELETE n;` -- this must only
# ever be replayed against the laptop's OWN restore target, never the live
# db1 Neo4j that holds the source graph.
cypher-shell -a "$URI" -u "$USER" -p "$NEO4J_PASSWORD" -f "$SCRIPT"

# Prove the restore landed: assert the expected node AND relationship count,
# printing expected AND found on one line so a mismatch is visible without
# re-running anything.
expected_nodes=14
expected_rels=16
found_nodes="$(cypher-shell -a "$URI" -u "$USER" -p "$NEO4J_PASSWORD" \
  --format plain 'MATCH (n) RETURN count(n)' | tail -1 | tr -d '"')"
found_rels="$(cypher-shell -a "$URI" -u "$USER" -p "$NEO4J_PASSWORD" \
  --format plain 'MATCH ()-[r]->() RETURN count(r)' | tail -1 | tr -d '"')"

ccf_log "expected nodes=$expected_nodes rels=$expected_rels — found nodes=$found_nodes rels=$found_rels"
if [ "$found_nodes" != "$expected_nodes" ] || [ "$found_rels" != "$expected_rels" ]; then
  echo "RESTORE MISMATCH: expected nodes=$expected_nodes rels=$expected_rels found nodes=$found_nodes rels=$found_rels" >&2
  exit 1
fi

# The node/relationship counts alone cannot see a replay that stopped between
# the last CREATE and the script's own final line. That final line is what
# strips the `_B1` scaffolding label and `_b1id` property -- if the process
# was interrupted or killed just before it, the graph would already show
# 14 nodes and 16 relationships and the assertion above would PASS on a
# partially-restored, scaffolding-contaminated graph. Count remaining `_B1`
# nodes explicitly; it must be zero.
expected_scaffold=0
found_scaffold="$(cypher-shell -a "$URI" -u "$USER" -p "$NEO4J_PASSWORD" \
  --format plain 'MATCH (n:`_B1`) RETURN count(n)' | tail -1 | tr -d '"')"

ccf_log "expected scaffold nodes=$expected_scaffold found=$found_scaffold"
if [ "$found_scaffold" != "$expected_scaffold" ]; then
  echo "RESTORE INCOMPLETE: $found_scaffold node(s) still carry the _B1 scaffolding label/_b1id property -- the replay did not reach its final line and the graph is in a PARTIAL state, not a clean restore." >&2
  exit 1
fi
