#!/usr/bin/env bash
# The ONLY file in this bundle that knows macOS from Ubuntu.
#
# Every restore_*.sh sources this and is otherwise identical on both platforms.
# Two parallel script sets would drift, and only the one somebody happened to
# run would ever be exercised.
#
# `sed -i` and `readlink -f` are deliberately absent from every script here:
# BSD and GNU disagree on both, and the failure mode is a corrupted restore
# rather than an error message.
set -euo pipefail

case "$(uname -s)" in
  Darwin) CCF_OS="macos"  ;;
  Linux)  CCF_OS="ubuntu" ;;
  *) echo "Unsupported platform: $(uname -s). This bundle targets macOS and Ubuntu." >&2
     exit 2 ;;
esac
export CCF_OS

if [ "$CCF_OS" = "macos" ]; then
  SHA256_CMD="shasum -a 256"
  for c in /opt/homebrew/opt/postgresql@16/bin /usr/local/opt/postgresql@16/bin; do
    [ -d "$c" ] && PG_BIN="$c" && break
  done
else
  SHA256_CMD="sha256sum"
  [ -d /usr/lib/postgresql/16/bin ] && PG_BIN="/usr/lib/postgresql/16/bin"
fi
PG_BIN="${PG_BIN:-}"
export SHA256_CMD PG_BIN

ccf_sha256() { $SHA256_CMD "$1" | awk '{print $1}'; }

ccf_need() {
  # Report EVERY missing tool, not just the first. Finding out about
  # mongorestore only after installing three other things wastes an evening.
  local missing=0 tool
  for tool in "$@"; do
    if ! command -v "$tool" >/dev/null 2>&1; then
      echo "MISSING: $tool" >&2
      missing=1
    fi
  done
  if [ "$missing" -ne 0 ]; then
    echo "" >&2
    echo "See INSTALL-${CCF_OS}.md. Note mongorestore ships in" >&2
    echo "'mongodb-database-tools', NOT in the MongoDB server package." >&2
    exit 2
  fi
}

ccf_log() { printf '  %s\n' "$*"; }
