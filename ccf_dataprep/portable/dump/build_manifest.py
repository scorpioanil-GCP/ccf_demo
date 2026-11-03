"""Build MANIFEST.json for a bundle root.

Runs on db1 with BARE python3 -- portable/manifest.py is pure stdlib
(hashlib, json, datetime, pathlib), so this needs no uv and no virtualenv.

This exists as its own file, rather than a heredoc piped through ssh, because
the global rule for this bundle is: never inline a multi-line script through
ssh. dump_all.sh rsyncs `portable/` to db1 first; this file rides along
under portable/dump/, and locates its OWN staged package two directories up
from itself -- never a hardcoded repo path, which does not exist on db1.

Usage:  python3 build_manifest.py /data/data_bundle
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from portable.manifest import add_artifact, write_manifest  # noqa: E402

# (relative path under the bundle root, store, fabric, method)
ARTIFACT_SPEC = [
    ("v1/fluree-fibo.flpack", "fluree", "v1", "fluree export --format ledger"),
    ("v1/postgres-public.dump", "postgres", "v1", "pg_dump -Fc"),
    ("v1/mongo-fibo", "mongodb", "v1", "mongodump --db fibo --gzip"),
    ("v1/neo4j-v1.cypher", "neo4j", "v1", "cypher export via bolt"),
    ("v2/primary/fluree-fibo-v2.flpack", "fluree", "v2-primary",
     "fluree export --format ledger"),
    ("v2/primary/postgres-ccf_v2.dump", "postgres", "v2-primary", "pg_dump -Fc"),
    ("v2/primary/mongo-fibo_v2", "mongodb", "v2-primary",
     "mongodump --db fibo_v2 --gzip"),
    ("v2/primary/departmental.sqlite", "sqlite", "v2-primary", "VACUUM INTO"),
    ("v2/colender/fluree-bofa-syndicate.flpack", "fluree", "v2-colender",
     "fluree export via docker exec"),
    ("v2/colender/postgres-colender.dump", "postgres", "v2-colender",
     "pg_dump -Fc"),
    ("v2/colender/mongo-bofa_syndicated", "mongodb", "v2-colender",
     "mongodump --db bofa_syndicated --gzip"),
    # The 8 shipped scripts: a truncated verify_install.py or restore_*.sh is
    # otherwise invisible to this manifest -- it only covered the 11 data
    # artifacts above, and the operator has no other way to check transit
    # damage on the tool that runs the restore itself.
    ("restore/platform.sh", "script", "bundle", "copied from portable/restore/"),
    ("restore/restore_all.sh", "script", "bundle", "copied from portable/restore/"),
    ("restore/restore_fluree.sh", "script", "bundle", "copied from portable/restore/"),
    ("restore/restore_mongo.sh", "script", "bundle", "copied from portable/restore/"),
    ("restore/restore_neo4j.sh", "script", "bundle", "copied from portable/restore/"),
    ("restore/restore_postgres.sh", "script", "bundle", "copied from portable/restore/"),
    ("restore/restore_sqlite.sh", "script", "bundle", "copied from portable/restore/"),
    ("verify_install.py", "script", "bundle", "copied from portable/"),
]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: build_manifest.py <bundle_root>", file=sys.stderr)
        return 2
    root = Path(sys.argv[1])

    # dump_fluree.sh records each ledger's exported commit count here. A
    # MISSING sidecar is a build error, not a default: shipping a manifest
    # with no ledger_t would make every restore skip its own replay check
    # and report success for a truncated ledger.
    sidecar = root / ".ledger-t.json"
    if not sidecar.exists():
        print(f"  MISSING: {sidecar.name} -- run dump_fluree.sh first",
              file=sys.stderr)
        return 2
    ledger_t = json.loads(sidecar.read_text())
    if not ledger_t:
        print(f"  EMPTY: {sidecar.name} recorded no ledgers", file=sys.stderr)
        return 2

    entries = []
    for rel, store, fabric, method in ARTIFACT_SPEC:
        p = root / rel
        if not p.exists():
            print(f"  MISSING: {rel}")
            continue
        extra = {}
        # The peer MongoDB is legitimately empty. Say so in the manifest, or a
        # later reader will mistake an empty directory for a failed dump.
        if store == "mongodb" and not any(p.rglob("*.bson.gz")):
            extra["empty"] = True
        entries.append(add_artifact(root, rel, store=store, fabric=fabric,
                                    method=method, extra=extra))

    path = write_manifest(root, entries, ledger_t=ledger_t)
    print(f"  {len(entries)} artifacts -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
