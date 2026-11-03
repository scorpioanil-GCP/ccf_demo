#!/usr/bin/env bash
# Fluree dumps for all three ledgers, both fabrics.
#
# Both fabrics are Fluree 4.2.4 since the 2026-10-15 cutover (see
# docs/fluree-42-migration-design.md): the primary is the host binary
# ~/bin/fluree-42 with storage under /data/fluree-42/storage (on the
# /data/mongodb partition since 2026-10-15, moved off the system disk), and
# the peer is the pinned fluree/server:4.2.4 container `fluree-demo-42`.
# A 4.2.4 archive imports cleanly into 4.2.4 (spiked 2026-10-15: fibo-v2
# round-tripped at 6,157 commits / 89,148 triples, exact).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/common.sh"
ccf_require_dir "$BUNDLE_ROOT"

# Each ledger's commit count AS EXPORTED, recorded here and folded into
# MANIFEST.json by build_manifest.py. The restore asserts against THIS rather
# than a hardcoded number, because `t` is not a property of the estate's
# content -- the repo's own validator suite advances it ~46 per run (it
# re-runs load_fluree_wave17.py to prove that loader is re-runnable) while
# the triple count does not move. A hardcoded t is stale before the operator
# finishes reading the install guide. See known-issues.md.
T_SIDECAR="$BUNDLE_ROOT/.ledger-t.json"
T_SCRATCH="$(mktemp)"
trap 'rm -f "$T_SCRATCH"' EXIT

# Parse the exporter's OWN statement about the archive it just wrote:
#   ✓ Archived 'fibo-v2' → /path (5112 commits, 0 txn blobs, 100 index …)
# An unparseable line is fatal. Recording a blank would ship a manifest whose
# replay check silently compares "" against "" and passes on any archive.
# The 4.2.4 announcement carries the same shape (spiked 2026-10-15: 103
# index artifacts on fibo-v2), so this parser is unchanged from 4.1.x.
record_ledger_t() {
  local ledger="$1" output="$2" n
  n="$(printf '%s' "$output" | sed -n 's/.*(\([0-9][0-9]*\) commits.*/\1/p' | head -1)"
  if [ -z "$n" ]; then
    echo "could not read a commit count from the export of $ledger:" >&2
    printf '%s\n' "$output" >&2
    exit 1
  fi
  printf '%s\t%s\n' "$ledger" "$n" >> "$T_SCRATCH"
  ccf_log "$ledger exported at t=$n"
}

FLUREE_BIN="${FLUREE_BIN:-/home/parkave/bin/fluree-42}"
LIVE_STORAGE="${LIVE_STORAGE:-/data/fluree-42/storage}"
WORK="${WORK:-/data/data_bundle/.work/fluree}"

# Export from a COPY of the live storage, never from the live path itself.
# `fluree export` reads the project directory and may write cache artifacts;
# pointing it at the authoritative ledger to save a copy would trade an
# irreversible risk for a few hundred MB of disk.
#
# 4.2 differs from the 4.1.4 script in two ways (both verified by the spike):
#   - The live storage holds ONE current index (not ~1,421 accumulated
#     generations totalling 46 GB), so the WHOLE ledger directory is copied
#     -- commits, index and shared dictionaries together -- and no index
#     rebuild is needed. The 4.1.4 script copied commit files only and ran
#     `fluree index --direct` in the scratch copy to build one fresh index.
#   - 4.2 export reads the project storage directly: there is no --direct
#     flag and no server contact, so the per-user ~/.fluree/server.pid state
#     shared with any other Fluree on the host is never touched.
export_local_ledger() {
  local ledger="$1" out="$2"
  ccf_step "Fluree $ledger -> $out"
  local proj="$WORK/$ledger"
  ccf_reset_path "$proj"; mkdir -p "$proj"
  ( cd "$proj" && "$FLUREE_BIN" init >/dev/null )
  local st="$proj/.fluree/storage"
  mkdir -p "$st/ns@v2"
  cp -r "$LIVE_STORAGE/$ledger" "$st/"
  cp -r "$LIVE_STORAGE/ns@v2/$ledger" "$st/ns@v2/"
  # Lock files copied from the running server are stale by definition --
  # export takes no locks, but drop them so nothing downstream mistakes
  # the scratch copy for a held ledger.
  find "$st" -name '*.lock' -delete
  ccf_reset_path "$out"
  local export_out
  # 2>&1: the exporter announces the archive on STDERR. Capturing stdout
  # alone yields an empty string and the commit count is lost.
  export_out="$( cd "$proj" && "$FLUREE_BIN" export "$ledger" --format ledger -o "$out" 2>&1 )"
  printf '%s\n' "$export_out"
  record_ledger_t "$ledger" "$export_out"
  ccf_log "$(ls -lh "$out" | awk '{print $5}') $(basename "$out")"
}

export_local_ledger "fibo-v2" "$BUNDLE_ROOT/v2/primary/fluree-fibo-v2.flpack"
export_local_ledger "fibo"    "$BUNDLE_ROOT/v1/fluree-fibo.flpack"

# --- peer, inside the container -------------------------------------------
# Same copy-first discipline as the host ledgers: copy the whole project
# inside the container to a scratch path, then export from the copy, so
# export never touches the live project. The container's own binary is the
# pinned 4.2.4 (docker exec fluree-demo-42 fluree --version) and the project
# lives at the image's /var/lib/fluree (bind-mounted from the host's
# /data/fluree-42/peer) -- not /tmp, where the 4.1.x image had no .fluree/.
ccf_step "Fluree bofa/syndicate (peer container)"
PEER_OUT="$BUNDLE_ROOT/v2/colender/fluree-bofa-syndicate.flpack"
ccf_reset_path "$PEER_OUT"
docker exec fluree-demo-42 rm -rf /tmp/peerwork
docker exec fluree-demo-42 cp -r /var/lib/fluree /tmp/peerwork
PEER_EXPORT_OUT="$(docker exec -w /tmp/peerwork fluree-demo-42 \
  fluree export bofa/syndicate --format ledger -o /tmp/peer.flpack 2>&1)"
record_ledger_t "bofa/syndicate" "$PEER_EXPORT_OUT"
docker cp fluree-demo-42:/tmp/peer.flpack "$PEER_OUT"
docker exec fluree-demo-42 rm -rf /tmp/peerwork /tmp/peer.flpack
ccf_log "$(ls -lh "$PEER_OUT" | awk '{print $5}') $(basename "$PEER_OUT")"

# Sorted, one object, written whole -- never appended to, so a partial run
# cannot leave a half-file that parses.
python3 - "$T_SCRATCH" "$T_SIDECAR" <<'EOF'
import json, sys
rows = {}
for line in open(sys.argv[1]):
    ledger, n = line.rstrip("\n").split("\t")
    rows[ledger] = int(n)
assert rows, "no ledger commit counts were recorded"
open(sys.argv[2], "w").write(json.dumps(dict(sorted(rows.items())), indent=2) + "\n")
print("  wrote %s: %s" % (sys.argv[2], rows))
EOF

rm -rf "$WORK"