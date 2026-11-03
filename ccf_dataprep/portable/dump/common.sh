#!/usr/bin/env bash
# Shared helpers for the dump side. Runs on db1 (Ubuntu).
set -euo pipefail

BUNDLE_ROOT="${BUNDLE_ROOT:-/data/data_bundle}"
export BUNDLE_ROOT

ccf_log()  { printf '  %s\n' "$*"; }
ccf_step() { printf '\n== %s\n' "$*"; }

ccf_require_dir() {
  [ -d "$1" ] || { echo "bundle root missing: $1" >&2; exit 2; }
}

# Idempotency: replace an artifact wholesale rather than merging into a stale
# one. A mongodump written over a previous dump's directory keeps orphaned
# collections that nothing will ever notice.
ccf_reset_path() {
  rm -rf "$1"
  mkdir -p "$(dirname "$1")"
}
