#!/usr/bin/env bash
#
# laptop-loader.sh — fetch the ccf_dataprep portable estate bundle onto a laptop.
#
# This is step 0. Everything else (INSTALL-macos.md / INSTALL-ubuntu.md) assumes
# you already have the bundle; this is how you get it.
#
# CHICKEN AND EGG: this script lives INSIDE the bundle it fetches, so grab it on
# its own first:
#
#     scp parkave@192.168.4.76:/data/data_bundle/laptop-loader.sh .
#     bash laptop-loader.sh
#
# Two directories are deliberately excluded:
#   .scripts/  the dump-side tree staged onto the build host so IT can build the
#              bundle. Useless on a laptop, and it names the build host's paths.
#   dave.txt   a scratch file that used to sit beside the bundle. It is no
#              longer there (checked 2026-09-23); the exclude stays because it
#              costs nothing and the directory is not ours to depend on.
#
# Roughly 378 MB. rsync resumes a partial transfer, so a dropped connection
# costs you the remainder, not the whole thing.
#
# Override any of these from the environment:
#   CCF_SRC_HOST   default parkave@192.168.4.76
#   CCF_SRC_PATH   default /data/data_bundle
#   CCF_DEST       default $HOME/ccf-bundle
set -euo pipefail

SRC_HOST="${CCF_SRC_HOST:-parkave@192.168.4.76}"
SRC_PATH="${CCF_SRC_PATH:-/data/data_bundle}"
DEST="${CCF_DEST:-$HOME/ccf-bundle}"

command -v rsync >/dev/null 2>&1 || {
  echo "rsync not found." >&2
  echo "  macOS:  it ships with the OS; check your PATH" >&2
  echo "  Ubuntu: sudo apt-get install -y rsync" >&2
  exit 2
}

echo "Fetching the ccf_dataprep bundle"
echo "  from: ${SRC_HOST}:${SRC_PATH}/"
echo "  to:   ${DEST}/"
echo

mkdir -p "$DEST"
rsync -avP \
  --exclude='.scripts' \
  --exclude='dave.txt' \
  "${SRC_HOST}:${SRC_PATH}/" "${DEST}/"

# A transfer that "succeeded" while dropping or corrupting a file is exactly
# what a byte count cannot see, so check the manifest rather than the size.
echo
if [ ! -f "${DEST}/MANIFEST.json" ]; then
  echo "MANIFEST.json did not arrive — the transfer is incomplete." >&2
  exit 1
fi

echo "Verifying every artifact against MANIFEST.json..."
# Delegated to verify_bundle.sh, which travelled with the bundle we just
# fetched, rather than reimplemented here. Two copies of a hashing rule are
# two things that drift, and the copy that drifts is the one nobody runs.
# It is also the check a bundle obtained any OTHER way (a download, a USB
# stick) needs, so it has to stand alone regardless.
if [ ! -f "${DEST}/verify_bundle.sh" ]; then
  echo "verify_bundle.sh did not arrive — the transfer is incomplete." >&2
  exit 1
fi
bash "${DEST}/verify_bundle.sh"

echo
echo "Bundle verified at ${DEST}"
echo
echo "Next:"
echo "  macOS   less ${DEST}/INSTALL-macos.md"
echo "  Ubuntu  less ${DEST}/INSTALL-ubuntu.md"
