#!/usr/bin/env python3
"""`verify_bundle.sh` must agree with `manifest.py`, and must be able to fail.

    uv run --with pytest pytest portable/tests/test_bundle_verifier.py

The bundle's integrity check exists twice over: `portable/manifest.py` computes
the hashes at dump time, and `verify_bundle.sh` recomputes them on the target
machine. Those are two implementations of one rule, in two languages, and the
rule has a subtlety -- a directory artifact folds in each file's relative path
AND its bytes. If they ever disagree, every bundle looks corrupt on arrival or,
far worse, a corrupt one looks fine.

So these tests build a real miniature bundle, hash it with `manifest.py`, and
require the shell script to accept it -- then damage it and require the script
to refuse. A checker that cannot say no is not a checker.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from portable.manifest import _hash_path

REPO = Path(__file__).resolve().parents[2]
VERIFY = REPO / "portable" / "bundle" / "verify_bundle.sh"
LOADER = REPO / "portable" / "bundle" / "laptop-loader.sh"


def _bundle(tmp_path: Path) -> Path:
    """A miniature bundle: one file artifact, one directory artifact."""
    root = tmp_path / "bundle"
    (root / "v2" / "primary" / "mongo-x").mkdir(parents=True)
    (root / "v1").mkdir(parents=True)

    (root / "v1" / "small.flpack").write_bytes(b"ledger archive bytes")
    (root / "v2" / "primary" / "mongo-x" / "a.bson.gz").write_bytes(b"alpha")
    (root / "v2" / "primary" / "mongo-x" / "b.bson.gz").write_bytes(b"beta")

    artifacts = []
    for rel in ("v1/small.flpack", "v2/primary/mongo-x"):
        sha, size = _hash_path(root / rel)
        artifacts.append({"path": rel, "store": "test", "fabric": "test",
                          "method": "fixture", "bytes": size, "sha256": sha})

    (root / "MANIFEST.json").write_text(json.dumps({
        "bundle": "test fixture",
        "generated_at": "2026-09-23T00:00:00+00:00",
        "ledger_t": {"fibo-v2": 5832},
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }))
    shutil.copy(VERIFY, root / "verify_bundle.sh")
    return root


def _run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(root / "verify_bundle.sh")],
                          capture_output=True, text=True)


def test_verify_bundle_exists_and_parses():
    assert VERIFY.is_file(), "verify_bundle.sh is missing"
    assert subprocess.run(["bash", "-n", str(VERIFY)]).returncode == 0


def test_accepts_a_bundle_manifest_py_hashed(tmp_path):
    """The agreement test: what manifest.py wrote, verify_bundle.sh accepts.

    This is the one that catches the two implementations drifting apart -- in
    particular the directory rule, which is where they could plausibly differ.
    """
    r = _run(_bundle(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "2 checked, 0 bad" in r.stdout


def test_reports_the_expected_ledger_t(tmp_path):
    """It must surface ledger_t -- on the Intel Mac path this is the only
    place the operator learns what `fluree list` should print."""
    r = _run(_bundle(tmp_path))
    assert "fibo-v2" in r.stdout and "5832" in r.stdout


def test_rejects_a_missing_artifact(tmp_path):
    root = _bundle(tmp_path)
    (root / "v1" / "small.flpack").unlink()
    r = _run(root)
    assert r.returncode == 1
    assert "MISSING" in r.stdout and "v1/small.flpack" in r.stdout


def test_rejects_a_corrupted_file_artifact(tmp_path):
    """One appended byte. Size changes, so this is the easy case -- but it
    must be reported as a mismatch, not as missing."""
    root = _bundle(tmp_path)
    p = root / "v1" / "small.flpack"
    p.write_bytes(p.read_bytes() + b"x")
    r = _run(root)
    assert r.returncode == 1
    assert "sha256 mismatch" in r.stdout


def test_rejects_an_edit_that_preserves_size(tmp_path):
    """The hard case: same byte count, different content. A size check alone
    cannot see this, which is why the manifest carries a hash at all."""
    root = _bundle(tmp_path)
    p = root / "v2" / "primary" / "mongo-x" / "a.bson.gz"
    assert p.read_bytes() == b"alpha"
    p.write_bytes(b"ALPHA")  # same length
    r = _run(root)
    assert r.returncode == 1
    assert "sha256 mismatch" in r.stdout


def test_rejects_a_rename_inside_a_directory_artifact(tmp_path):
    """The subtlety the directory rule exists for: bytes unchanged, names
    swapped. A hash over content alone would pass this."""
    root = _bundle(tmp_path)
    d = root / "v2" / "primary" / "mongo-x"
    (d / "a.bson.gz").rename(d / "c.bson.gz")
    r = _run(root)
    assert r.returncode == 1
    assert "sha256 mismatch" in r.stdout


def test_refuses_to_run_without_a_manifest(tmp_path):
    root = _bundle(tmp_path)
    (root / "MANIFEST.json").unlink()
    r = _run(root)
    assert r.returncode == 2, "no manifest is an unusable bundle, not a failed check"


def test_loader_delegates_rather_than_reimplementing(tmp_path):
    """laptop-loader.sh must not carry its own copy of the hashing rule.

    It used to. Two copies drift, and the one that drifts is the one nobody
    runs -- the bundle is fetched by rsync far less often than it is checked.
    """
    text = LOADER.read_text()
    assert "verify_bundle.sh" in text, "the loader no longer calls the verifier"
    assert "hashlib" not in text, "the loader has grown its own hashing again"


@pytest.mark.parametrize("script", [VERIFY, LOADER])
def test_scripts_are_strict_bash(script):
    assert "set -euo pipefail" in script.read_text()
