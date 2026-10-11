#!/usr/bin/env bash
# Copyright (c) 2026 David Castillo. All rights reserved.
# Install a built ccf-sdk wheel into a fresh virtual environment, OUTSIDE any source tree, and verify:
# the installed version, that it was built from the expected commit, the CLI entry point, that the code
# imported is the wheel's (not a checkout), and that adapter provenance (what replay records pin) names
# the installed version. Usage: verify_wheel.sh <wheel> <expected-commit-prefix> <work-dir>
set -euo pipefail
WHEEL=$(realpath "${1:?wheel}"); COMMIT=${2:?commit prefix}; WORK=${3:?work dir}
rm -rf "$WORK/venv"; mkdir -p "$WORK"; cd "$WORK"
python3 -m venv venv
venv/bin/python -m pip install -q --upgrade pip
venv/bin/python -m pip install -q "$WHEEL"
sha256sum "$WHEEL"
env -i PATH="$WORK/venv/bin:/usr/bin:/bin" HOME="$WORK" venv/bin/python -I - "$COMMIT" <<'PY'
import importlib.metadata as md, sys, pathlib
import ccf, ccf_runtime
from ccf.graph.registry import resolve
commit = sys.argv[1]
version = md.version("ccf-sdk")
ok = True
def check(name, cond, detail=""):
    global ok; ok &= bool(cond); print(("PASS " if cond else "FAIL ") + name + (f"  ({detail})" if detail else ""))
check("installed version names the commit", f"+g{commit}" in version, version)
site = pathlib.Path(ccf.__file__).resolve()
check("ccf imported from the installed wheel", "site-packages" in str(site), str(site))
check("ccf_runtime imported from the installed wheel", "site-packages" in str(pathlib.Path(ccf_runtime.__file__).resolve()))
record = resolve("sqlite")
check("adapter provenance (replay pin) names the installed version", getattr(record, "version", None) == version,
      f"{getattr(record, 'version', None)}")
sys.exit(0 if ok else 1)
PY
venv/bin/ccf --help > /dev/null && echo "PASS ccf CLI entry point runs"
