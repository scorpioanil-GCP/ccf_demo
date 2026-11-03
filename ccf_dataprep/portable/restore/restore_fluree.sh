#!/usr/bin/env bash
# Restore all Fluree ledgers into one project directory.
#
# The archives are 4.2.4 `.flpack`s (rebuilt from the 4.2 estate since the
# 2026-10-15 cutover). The target must run Fluree 4.2.4 -- a 4.2 pack is not
# guaranteed to import into 4.1.x. The 4.2 CLI reads the project directory
# directly; the 4.1.x `--direct` flag no longer exists on drop/create/list/
# query, so nothing here passes it.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/platform.sh"
BUNDLE="$(cd "$HERE/.." && pwd)"
ccf_need fluree python3

TARGET="${CCF_FLUREE_HOME:-$HOME/ccf-fluree}"
mkdir -p "$TARGET"
TARGET="$(cd "$TARGET" && pwd)"
ccf_log "restore target: $TARGET"

# Guard: the ledger names below are hardcoded to the live estate's exact
# names. If CCF_FLUREE_HOME ever pointed at a pre-existing Fluree project
# that happens to hold ledgers by those names -- the production project
# directory, say -- restore_one's forced drop would delete them with no
# confirmation. Refuse unless this script is the one that owns $TARGET:
# safe means the target has no .fluree/storage yet, or it carries the
# marker this script writes right after `fluree init`.
MARKER="$TARGET/.fluree/.ccf-b1-restore-target"
if [ -d "$TARGET/.fluree/storage" ] && [ ! -f "$MARKER" ]; then
  echo "refusing to use $TARGET as a restore target" >&2
  echo "it already holds a Fluree project this script did not create" >&2
  echo "point CCF_FLUREE_HOME at a different, empty directory" >&2
  exit 1
fi

( cd "$TARGET" && [ -d .fluree ] || fluree init >/dev/null )
mkdir -p "$(dirname "$MARKER")"
: > "$MARKER"

restore_one() {
  local ledger="$1" pack="$2"
  [ -f "$pack" ] || { echo "missing archive: $pack" >&2; exit 1; }
  ccf_log "restoring $ledger"
  # Idempotent: drop any prior copy first, or `create` fails on a re-run.
  # --force is required by `fluree drop` to confirm deletion; without it the
  # drop is refused (exit 2) and silently swallowed by `|| true`, leaving the
  # ledger in place so the next `create` fails with "Ledger already exists".
  ( cd "$TARGET" && fluree drop "$ledger" --force >/dev/null 2>&1 || true )
  ( cd "$TARGET" && fluree create "$ledger" --from "$pack" )
}

restore_one "fibo-v2"        "$BUNDLE/v2/primary/fluree-fibo-v2.flpack"
restore_one "fibo"           "$BUNDLE/v1/fluree-fibo.flpack"
restore_one "bofa/syndicate" "$BUNDLE/v2/colender/fluree-bofa-syndicate.flpack"

ccf_log "ledgers now present:"
LIST_OUT="$( cd "$TARGET" && fluree list )"
echo "$LIST_OUT"

# Prove each ledger's restore landed: assert the expected commit count (t)
# for all three, plus the expected triple count for the two whose content is
# the point of the demonstration (fibo-v2 and the peer bofa/syndicate; the
# tiny v1 fabric's t alone is enough for it). Every other restore_*.sh in
# this bundle already ends with an expected-vs-found assertion; this was the
# one store whose archive format is most fragile (a copy-first export, not a
# vendor dump) and whose 4.2.4-exported / 4.2.4-imported path is this
# branch's riskiest assumption -- ending at `fluree list` with no check
# proved nothing.
#
# Everything below goes through the CLI against the project directory,
# never HTTP: this script never starts (and must not assume) a running
# Fluree server, so there is no URL to query against yet -- that only
# exists after the install guide's later "start the Fluree server" step.

# `fluree list` prints a fixed-width table:
#   |   | LEDGER  | BRANCH | T    |
#   | * | fibo-v2 | main   | 5112 |
# Field 3 (ledger name) and field 5 (t) on a `|`-delimited split; the active-
# ledger marker in field 2 and the header/separator rows never match a real
# ledger name, so no extra filtering is needed.
found_t() {
  local ledger="$1"
  echo "$LIST_OUT" | awk -F'|' -v led="$ledger" '{
    name = $3; gsub(/^[ \t]+|[ \t]+$/, "", name);
    if (name == led) { t = $5; gsub(/^[ \t]+|[ \t]+$/, "", t); print t }
  }'
}

# Triple count via a direct SPARQL COUNT(*), --format csv so the value is
# alone on line 2 (line 1 is the header "n", the CLI also prints a timing
# footer on line 3 that this ignores by only reading line 2).
found_triples() {
  local ledger="$1"
  ( cd "$TARGET" && fluree query "$ledger" \
      -e 'SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }' \
      --sparql --format csv ) | sed -n '2p' | tr -d '[:space:]'
}

# The EXPECTED t comes from the manifest, not from a number typed into this
# file. `t` is a commit count, and commits accumulate from activity that
# changes no data at all: this repo's validator suite re-runs
# `loaders/load_fluree_wave17.py` twice per run to prove that loader is
# re-runnable, which adds ~46 commits while the triple count stays exactly
# where it was. A hardcoded t was stale within one test run of being written.
#
# What this still proves: the replay carried EVERY commit the archive held.
# What it cannot prove, and no longer pretends to: that the archive itself
# was complete. The triple counts below stay hardcoded for that -- they are
# stable, so they remain knowledge independent of the artifact being checked.
manifest_t() {
  local ledger="$1"
  python3 - "$BUNDLE/MANIFEST.json" "$ledger" <<'EOF'
import json, sys
try:
    doc = json.load(open(sys.argv[1]))
except Exception as exc:
    raise SystemExit("cannot read %s: %s" % (sys.argv[1], exc))
table = doc.get("ledger_t") or {}
if sys.argv[2] not in table:
    raise SystemExit(
        "MANIFEST.json records no ledger_t for %r (it has %s). This bundle "
        "predates manifest-recorded commit counts -- rebuild it."
        % (sys.argv[2], sorted(table)))
print(table[sys.argv[2]])
EOF
}

assert_eq() {
  local label="$1" expected="$2" found="$3"
  ccf_log "$label: expected=$expected found=$found"
  if [ "$found" != "$expected" ]; then
    echo "RESTORE MISMATCH: $label expected=$expected found=$found" >&2
    exit 1
  fi
}

assert_eq "fluree fibo-v2 t"             "$(manifest_t fibo-v2)"  "$(found_t fibo-v2)"
assert_eq "fluree fibo-v2 triples"       89148 "$(found_triples fibo-v2)"
assert_eq "fluree fibo (v1) t"           "$(manifest_t fibo)"  "$(found_t fibo)"
assert_eq "fluree bofa/syndicate t"      "$(manifest_t "bofa/syndicate")"  "$(found_t "bofa/syndicate")"
assert_eq "fluree bofa/syndicate triples" 10   "$(found_triples "bofa/syndicate")"
