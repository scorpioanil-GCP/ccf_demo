#!/usr/bin/env bash
#
# package_release.sh — turn the built bundle on db1 into the three files we
# hand out:
#
#     ccf-estate-bundle.tar   the bundle, unpacking to ccf-estate-bundle/
#     SHA256SUMS              checksum of the tar
#     README.md               the outer README (portable/bundle/RELEASE-README.md)
#
# Run on the WORKSTATION, after `bash portable/dump/dump_all.sh`:
#
#     bash portable/dump/package_release.sh
#
# The tar is streamed straight off db1, leaving out what never ships: the
# dump-side `.scripts/` tree, the `.ledger-t.json` sidecar build_manifest.py
# already folded into MANIFEST.json, laptop-loader.sh (an rsync fetcher,
# useless to someone who has the tar) and any `dave.txt`.
#
# Before reporting success it unpacks the tar it just wrote and runs the
# shipped verify_bundle.sh against the copy, so what was checked is the
# thing that ships, not the folder it came from.
#
# Override from the environment:
#   REMOTE       default parkave@192.168.4.76
#   BUNDLE_ROOT  default /data/data_bundle
#   DIST         default $HOME/ccf-dist
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
REMOTE="${REMOTE:-parkave@192.168.4.76}"
BUNDLE_ROOT="${BUNDLE_ROOT:-/data/data_bundle}"
DIST="${DIST:-$HOME/ccf-dist}"
NAME=ccf-estate-bundle
TAR="$DIST/$NAME.tar"

say() { printf '\n== %s\n' "$*"; }

say "checking the bundle on $REMOTE:$BUNDLE_ROOT"
# Every file the outer README and restore.sh promise must be in the bundle.
ssh "$REMOTE" "cd '$BUNDLE_ROOT' && for f in MANIFEST.json restore.sh verify_bundle.sh verify_install.py \
    README.md INSTALL-ubuntu.md INSTALL-macos.md PURGE.md restore/restore_all.sh; do \
    [ -f \"\$f\" ] || { echo \"bundle is missing \$f — re-run dump_all.sh\" >&2; exit 1; }; done"

mkdir -p "$DIST"
say "writing $TAR"
# GNU tar on db1. The transform renames the leading "." to the bundle name,
# so the archive unpacks into one folder rather than over the current one.
ssh "$REMOTE" "cd '$BUNDLE_ROOT' && tar -cf - \
    --exclude=./.scripts --exclude=./.ledger-t.json \
    --exclude=./laptop-loader.sh --exclude=./dave.txt \
    --exclude='__pycache__' \
    --owner=0 --group=0 --numeric-owner \
    --transform='s,^\\.,$NAME,' ." > "$TAR.part"
mv "$TAR.part" "$TAR"

( cd "$DIST" && sha256sum "$NAME.tar" > SHA256SUMS )
cp "$REPO/portable/bundle/RELEASE-README.md" "$DIST/README.md"
rm -f "$DIST/._README.md"   # a macOS resource-fork leftover, not ours

say "proving the tar restores what it claims"
CHECK="$(mktemp -d)"
trap 'rm -rf "$CHECK"' EXIT
( cd "$DIST" && sha256sum -c SHA256SUMS )
tar -xf "$TAR" -C "$CHECK"
[ "$(ls -A "$CHECK")" = "$NAME" ] || { echo "tar does not unpack to a single $NAME/ folder" >&2; exit 1; }
for leak in .scripts .ledger-t.json laptop-loader.sh; do
  [ ! -e "$CHECK/$NAME/$leak" ] || { echo "tar leaked $leak" >&2; exit 1; }
done
bash "$CHECK/$NAME/verify_bundle.sh"

say "done"
ls -l "$DIST"
