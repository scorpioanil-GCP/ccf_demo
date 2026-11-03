"""Bundle manifest and the MongoDB scope guard.

The guard is here rather than in a comment because db1's MongoDB also carries
`rtdetect` — measured twice at 7,062,417 documents (2026-08-27), not the
roughly 5.5 million once assumed here — of an unrelated live system. A dump
or restore that reached it would be destructive and silent. `ccf/config.py`
takes the same position for the same host; this is its dump-side twin.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

#: The only MongoDB databases this bundle may read or write. Anything absent is
#: refused — an allowlist, never a denylist, because a denylist silently admits
#: whatever nobody thought of.
ALLOWED_MONGO_DBS = frozenset({"fibo", "fibo_v2", "bofa_syndicated"})


class MongoScopeError(RuntimeError):
    """An attempt to dump or restore a MongoDB database outside the bundle."""


def assert_mongo_db_allowed(name: str) -> str:
    if name not in ALLOWED_MONGO_DBS:
        raise MongoScopeError(
            f"Refusing to touch MongoDB database {name!r}. This bundle covers "
            f"only {sorted(ALLOWED_MONGO_DBS)}. db1's MongoDB also carries "
            f"'rtdetect' (7,062,417 documents, measured 2026-08-27) belonging to an unrelated live "
            f"system; naming databases explicitly is what keeps it safe."
        )
    return name


def _hash_path(path: Path) -> tuple[str, int]:
    """sha256 over a file, or over a directory's sorted contents.

    A directory hash must fold in each file's relative path AND its bytes: a
    hash over bytes alone cannot see a file being renamed, and a hash over
    names alone cannot see its content change.
    """
    h = hashlib.sha256()
    total = 0
    if path.is_file():
        data = path.read_bytes()
        h.update(data)
        return h.hexdigest(), len(data)
    for child in sorted(p for p in path.rglob("*") if p.is_file()):
        rel = child.relative_to(path).as_posix()
        data = child.read_bytes()
        h.update(rel.encode())
        h.update(b"\0")
        h.update(data)
        total += len(data)
    return h.hexdigest(), total


def add_artifact(root: Path, rel_path: str, *, store: str, fabric: str,
                 method: str, extra: dict | None = None) -> dict:
    target = Path(root) / rel_path
    if not target.exists():
        raise FileNotFoundError(f"manifest names a missing artifact: {target}")
    digest, size = _hash_path(target)
    entry = {
        "path": rel_path,
        "store": store,
        "fabric": fabric,
        "method": method,
        "bytes": size,
        "sha256": digest,
    }
    if extra:
        entry.update(extra)
    return entry


def write_manifest(root: Path, entries: list[dict],
                   ledger_t: dict[str, int] | None = None) -> Path:
    """Write MANIFEST.json.

    `ledger_t` records each Fluree ledger's commit count AS EXPORTED. It is
    deliberately manifest-derived rather than hardcoded in the restore
    scripts, unlike every other landmark in this bundle, because `t` is not a
    property of the estate's CONTENT: this repo's own validator suite re-runs
    `loaders/load_fluree_wave17.py` to prove it is re-runnable, which records
    ~46 commits per suite run while the triple count does not move at all. A
    hardcoded `t` therefore goes stale on activity that changes no data, and
    no rebuild can outrun it.

    What this check still proves is REPLAY COMPLETENESS -- that the restored
    ledger carries every commit the archive held. What it cannot prove, and
    does not claim to, is that the archive itself was complete. The triple
    counts stay hardcoded for exactly that reason: they are stable (88,325
    through every sample taken while this was diagnosed) and so they remain
    independent knowledge.
    """
    doc = {
        "bundle": "ccf_dataprep portable estate",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_host": "db1 (192.168.4.76)",
        "ledger_t": dict(sorted((ledger_t or {}).items())),
        "artifact_count": len(entries),
        "artifacts": sorted(entries, key=lambda e: e["path"]),
    }
    path = Path(root) / "MANIFEST.json"
    path.write_text(json.dumps(doc, indent=2) + "\n")
    return path
