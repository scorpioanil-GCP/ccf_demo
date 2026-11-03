#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/platform.sh"
BUNDLE="$(cd "$HERE/.." && pwd)"
ccf_need mongorestore mongosh

URI="${CCF_MONGO_URI:-mongodb://127.0.0.1:27017}"

# The allowlist below MUST equal portable/manifest.py::ALLOWED_MONGO_DBS.
# This script cannot import Python (it has to run on a laptop with no repo
# checkout present), so it carries its own copy rather than reaching across
# languages -- portable/tests/test_mongo_guard.py parses this exact `case`
# pattern and fails the suite if the two lists ever diverge.
guard_db() {
  case "$1" in
    fibo|fibo_v2|bofa_syndicated) ;;
    *) echo "Refusing MongoDB database '$1' — not in this bundle." >&2; exit 2 ;;
  esac
}

# Prove the restore landed rather than trusting mongorestore's exit code:
# counts collections AND total documents, printing expected and found on one
# line so a mismatch is visible without re-running anything.
assert_mongo_counts() {
  local db="$1" expected_colls="$2" expected_docs="$3" out found_colls found_docs
  out="$(mongosh "$URI" --quiet --eval "
    const d = db.getSiblingDB('$db');
    const cols = d.getCollectionNames();
    let total = 0;
    for (const c of cols) total += d.getCollection(c).countDocuments({});
    print(cols.length + ' ' + total);
  " | tail -1)"
  found_colls="$(echo "$out" | awk '{print $1}')"
  found_docs="$(echo "$out" | awk '{print $2}')"
  ccf_log "$db: expected collections=$expected_colls docs=$expected_docs — found collections=$found_colls docs=$found_docs"
  if [ "$found_colls" != "$expected_colls" ] || [ "$found_docs" != "$expected_docs" ]; then
    echo "RESTORE MISMATCH: $db expected collections=$expected_colls docs=$expected_docs found collections=$found_colls docs=$found_docs" >&2
    exit 1
  fi
}

# The expectation is declared HERE, per database, and drives the decision --
# never inferred from whether a directory happens to exist on disk. A
# missing directory for a database that expects content is a broken bundle,
# full stop; it is only a legitimate skip for a database that is declared
# empty. Without this, a re-run against a target that already holds a good
# prior restore would skip silently on a missing/corrupt dump dir and then
# have assert_mongo_counts re-measure the STALE existing data and pass --
# reporting success for a restore that never ran.
restore_and_verify() {
  local db="$1" dir="$2" expected_colls="$3" expected_docs="$4"
  guard_db "$db"

  if [ "$expected_colls" = "0" ] && [ "$expected_docs" = "0" ]; then
    if [ -d "$dir/$db" ]; then
      ccf_log "restoring $db"
      mongorestore --uri="$URI" --db="$db" --gzip --drop --quiet "$dir/$db"
    else
      ccf_log "$db: empty BY EXPECTATION — no dump directory is correct here, not a missing file"
    fi
  else
    if [ ! -d "$dir/$db" ]; then
      echo "BUNDLE INCOMPLETE: $db expects $expected_colls collections / $expected_docs docs but the dump directory is missing: $dir/$db" >&2
      exit 2
    fi
    ccf_log "restoring $db"
    # --drop makes this re-runnable; without it a second run doubles every doc.
    mongorestore --uri="$URI" --db="$db" --gzip --drop --quiet "$dir/$db"
  fi

  assert_mongo_counts "$db" "$expected_colls" "$expected_docs"
}

restore_and_verify fibo_v2         "$BUNDLE/v2/primary/mongo-fibo_v2"          6 38238
restore_and_verify fibo            "$BUNDLE/v1/mongo-fibo"                    2 30
# The peer's bofa_syndicated is dumped and restored anyway; 0 collections /
# 0 documents is the CORRECT expectation here, not evidence of a broken
# restore -- so an absent dump directory for THIS db is a clean skip, not a
# failure.
restore_and_verify bofa_syndicated "$BUNDLE/v2/colender/mongo-bofa_syndicated" 0 0
