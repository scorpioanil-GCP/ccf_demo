#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/platform.sh"
BUNDLE="$(cd "$HERE/.." && pwd)"
ccf_need sqlite3

SRC="$BUNDLE/v2/primary/departmental.sqlite"
DEST="${CCF_SQLITE_PATH:-$HOME/ccf-data/departmental.sqlite}"

# A missing or empty snapshot is a broken bundle, not a notice to forgive.
if [ ! -f "$SRC" ]; then
  echo "MISSING SNAPSHOT: $SRC" >&2
  exit 2
fi
if [ ! -s "$SRC" ]; then
  echo "EMPTY SNAPSHOT: $SRC" >&2
  exit 2
fi

mkdir -p "$(dirname "$DEST")"
cp "$SRC" "$DEST"

# Prove the restore landed: assert the expected table count, printing
# expected AND found on one line so a mismatch is visible without re-running.
expected=8
found="$(sqlite3 "$DEST" "select count(*) from sqlite_master where type='table'")"
ccf_log "$DEST — expected tables=$expected found=$found"
if [ "$found" != "$expected" ]; then
  echo "RESTORE MISMATCH: $DEST expected=$expected found=$found" >&2
  exit 1
fi
