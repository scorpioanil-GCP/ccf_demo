#!/usr/bin/env bash
# -Fc (custom format) rather than plain SQL: compressed, and pg_restore can
# list and select from it, which plain SQL cannot.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/common.sh"
ccf_require_dir "$BUNDLE_ROOT"

: "${PGHOST:=192.168.4.76}"
: "${PGPORT:=5432}"
export PGHOST PGPORT

dump_schema() {
  local db="$1" schema="$2" user="$3" out="$4"
  ccf_step "Postgres $db.$schema -> $(basename "$out")"
  ccf_reset_path "$out"
  PGPASSWORD="${5:-}" pg_dump -Fc --no-owner --no-privileges \
      --schema="$schema" --dbname="$db" --username="$user" --file="$out"
  ccf_log "$(ls -lh "$out" | awk '{print $5}')"
  # A dump that lists zero tables is a silent disaster: pg_dump exits 0 when a
  # --schema matches nothing at all.
  local n
  n="$(pg_restore --list "$out" | grep -c 'TABLE DATA' || true)"
  ccf_log "tables with data: $n"
  [ "$n" -gt 0 ] || { echo "REFUSING: $schema dumped 0 tables" >&2; exit 1; }
}

dump_schema parkavedb ccf_v2 "${PGUSER:-parkave}" \
    "$BUNDLE_ROOT/v2/primary/postgres-ccf_v2.dump" "${PGPASSWORD:-}"
dump_schema parkavedb public "${PGUSER:-parkave}" \
    "$BUNDLE_ROOT/v1/postgres-public.dump" "${PGPASSWORD:-}"
# The peer connects as a DIFFERENT role to a DIFFERENT database on the same
# host -- that separation is a control, not a convention, so this reuses none
# of the primary's PGUSER/PGPASSWORD.
dump_schema "${CO_LENDER_PG_DB:-bofa_syndicated}" \
    "${CO_LENDER_PG_SCHEMA:-colender}" "${CO_LENDER_PG_USER:-colender}" \
    "$BUNDLE_ROOT/v2/colender/postgres-colender.dump" \
    "${CO_LENDER_PG_PASSWORD:-}"
