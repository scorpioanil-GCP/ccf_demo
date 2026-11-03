#!/usr/bin/env bash
# Runs on the WORKSTATION (the file is local), then ships the snapshot to db1.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
SRC="${SQLITE_SRC:-$REPO/data/departmental.sqlite}"
OUT="${SQLITE_OUT:-$REPO/.b1-staging/departmental.sqlite}"
REMOTE="${REMOTE:-parkave@192.168.4.76}"
DEST="${DEST:-/data/data_bundle/v2/primary/departmental.sqlite}"

[ -f "$SRC" ] || { echo "no SQLite file at $SRC" >&2; exit 1; }
mkdir -p "$(dirname "$OUT")"
rm -f "$OUT"
# VACUUM INTO takes a consistent snapshot of a live database. `cp` does not.
sqlite3 "$SRC" "VACUUM INTO '$OUT'"

src_tables="$(sqlite3 "$SRC" "select count(*) from sqlite_master where type='table'")"
out_tables="$(sqlite3 "$OUT" "select count(*) from sqlite_master where type='table'")"
echo "  tables: source=$src_tables snapshot=$out_tables"
[ "$src_tables" = "$out_tables" ] || { echo "table count differs" >&2; exit 1; }

ssh "$REMOTE" "mkdir -p $(dirname "$DEST")"
rsync -a "$OUT" "$REMOTE:$DEST"
echo "  shipped to $REMOTE:$DEST"
