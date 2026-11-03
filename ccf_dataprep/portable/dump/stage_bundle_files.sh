#!/usr/bin/env bash
# Copy the shipped restore scripts, verifier, and docs from the staged
# portable/ tree into the actual bundle root. Runs ON DB1, invoked by
# dump_all.sh over ssh as a single `bash <staged-path>` call.
#
# Arg 1: bundle root (e.g. /data/data_bundle)
# Arg 2: staged portable/ directory (e.g. /data/data_bundle/.scripts/portable)
set -euo pipefail
BUNDLE="${1:?usage: stage_bundle_files.sh <bundle_root> <staged_portable_dir>}"
STAGED="${2:?usage: stage_bundle_files.sh <bundle_root> <staged_portable_dir>}"

cp "$STAGED"/restore/*.sh "$BUNDLE/restore/"
cp "$STAGED/verify_install.py" "$BUNDLE/"
cp "$STAGED/bundle/laptop-loader.sh" "$BUNDLE/"
cp "$STAGED/bundle/restore.sh" "$BUNDLE/"
cp "$STAGED/bundle/verify_bundle.sh" "$BUNDLE/"
chmod +x "$BUNDLE/laptop-loader.sh" "$BUNDLE/restore.sh"
cp "$STAGED/bundle/README.md" "$BUNDLE/"
cp "$STAGED/bundle/INSTALL-macos.md" "$BUNDLE/"
cp "$STAGED/bundle/PURGE.md" "$BUNDLE/"
cp "$STAGED/bundle/INSTALL-ubuntu.md" "$BUNDLE/"
chmod +x "$BUNDLE"/restore/*.sh
