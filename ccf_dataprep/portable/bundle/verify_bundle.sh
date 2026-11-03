#!/usr/bin/env bash
#
# verify_bundle.sh — prove an unpacked bundle is complete and undamaged.
#
# Run it from inside the bundle, before you restore anything:
#
#     cd ~/ccf-bundle && bash verify_bundle.sh
#
# This is the check that used to live only inside `laptop-loader.sh`, which
# fetches the bundle by rsync from the build host. A bundle that arrives any
# other way — a download, a USB stick, a shared drive — never ran through that
# script, and so had no integrity check at all. That is the gap this closes:
# the thing most likely to go wrong in a 378 MB transfer is a truncated or
# silently corrupted file, and a byte count cannot see it.
#
# It verifies the 19 artifacts MANIFEST.json names. It deliberately does NOT
# verify the install guides, this script, or laptop-loader.sh: those are not in
# the manifest, because the manifest is generated at dump time from what the
# dump produced. Read them, don't hash them.
#
# Exit 0 — every artifact present and matching.
# Exit 1 — something is missing or damaged; it names which.
# Exit 2 — the bundle itself is unusable (no MANIFEST.json, no python3).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"

if [ ! -f "$HERE/MANIFEST.json" ]; then
  echo "No MANIFEST.json beside this script ($HERE)." >&2
  echo "Run it from inside the unpacked bundle, not from the repository." >&2
  exit 2
fi

command -v python3 >/dev/null 2>&1 || {
  echo "python3 not found — required to check the manifest." >&2
  echo "  macOS:  xcode-select --install" >&2
  echo "  Ubuntu: sudo apt-get install -y python3" >&2
  exit 2
}

cd "$HERE"
python3 - <<'PY'
import hashlib
import json
import pathlib
import sys

root = pathlib.Path(".")
doc = json.load(open("MANIFEST.json"))
artifacts = doc["artifacts"]

def digest(path):
    """sha256 over a file, or over a directory's sorted contents.

    Must match portable/manifest.py's _hash_path exactly: a directory folds in
    each file's relative path AND its bytes, because names alone cannot see an
    edit and bytes alone cannot see a rename.
    """
    h = hashlib.sha256()
    if path.is_file():
        h.update(path.read_bytes())
        return h.hexdigest()
    for child in sorted(p for p in path.rglob("*") if p.is_file()):
        h.update(child.relative_to(path).as_posix().encode())
        h.update(b"\0")
        h.update(child.read_bytes())
    return h.hexdigest()

bad = []
for entry in artifacts:
    path = root / entry["path"]
    if not path.exists():
        bad.append((entry["path"], "MISSING"))
        continue
    if digest(path) != entry["sha256"]:
        bad.append((entry["path"], "sha256 mismatch — truncated or corrupted"))

print("  bundle    %s" % doc.get("bundle", "?"))
print("  built     %s" % doc.get("generated_at", "?"))
print("  artifacts %d checked, %d bad" % (len(artifacts), len(bad)))
for name, why in bad:
    print("  FAILED    %s — %s" % (name, why))

if bad:
    print("")
    print("  Do not restore from this bundle. Fetch it again.")
    sys.exit(1)

t = doc.get("ledger_t") or {}
if t:
    print("")
    print("  expected Fluree commit counts after restore:")
    for ledger in sorted(t):
        print("    %-16s t=%s" % (ledger, t[ledger]))
PY

echo ""
echo "Bundle verified. Next: read INSTALL-macos.md or INSTALL-ubuntu.md."
