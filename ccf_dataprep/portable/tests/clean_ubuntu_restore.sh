#!/usr/bin/env bash
#
# clean_ubuntu_restore.sh — install and restore the hand-out bundle on a
# brand-new Ubuntu 24.04, following INSTALL-ubuntu.md literally.
#
# Run on the workstation, after package_release.sh:
#
#     bash portable/tests/clean_ubuntu_restore.sh [DIST]    # default ~/ccf-dist
#
# A throwaway `ubuntu:24.04` container gets the three hand-out files and
# nothing else, follows the guide's steps 0-4 as an ordinary sudo user, then
# runs `bash restore.sh` twice: once to restore, once to prove a re-run
# stops its own Fluree server and comes back green. Neo4j is left out
# (no NEO4J_PASSWORD), which also exercises the skip path.
#
# The only departures from the guide: no systemd in a container, so
# Postgres and mongod are started directly instead of via systemctl.
#
# Its first runs (2026-10-17) found two guide bugs that every earlier check
# had missed: minimal Ubuntu lacks xz-utils (the Fluree installer fails),
# and the 4.2.4 installer puts fluree in ~/bin, not ~/.cargo/bin. Plus one
# restore.sh bug: the recorded server pid was a wrapper subshell's.
#
# Exit 0 only if both restore.sh runs exit 0. About 5 minutes, mostly apt.
set -euo pipefail
DIST="$(cd "${1:-$HOME/ccf-dist}" && pwd)"
HERE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$DIST/ccf-estate-bundle.tar" ] || { echo "no ccf-estate-bundle.tar in $DIST" >&2; exit 2; }
exec docker run --rm --name ccf-clean-restore-test \
  -v "$DIST:/dist:ro" -v "$HERE/clean_ubuntu_restore.inner.sh:/inner.sh:ro" \
  ubuntu:24.04 bash /inner.sh
