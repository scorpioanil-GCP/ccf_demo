"""Export the v1 Neo4j graph as a replayable Cypher script.

14 nodes, 16 relationships. `neo4j-admin database dump` refuses a running
database and its archive is major-version-bound; a Cypher script is neither.

Every node is given a stable `_b1id` property derived from its element id so
relationships can be reconnected on replay without relying on Neo4j's internal
ids, which are NOT stable across a reload.

Runs on the WORKSTATION, not db1: db1 has no repo checkout, no `uv`, and no
`neo4j` Python driver -- only bare python3. Bolt is reachable from here. After
writing the script locally, this ships it to db1 the same way dump_sqlite.sh
ships its snapshot: ssh mkdir, then rsync.

Known limitations (checked 2026-08-27 against the real 14-node/16-rel v1
graph -- neither triggers there, both are latent for a future graph):

1. `literal()`/`props()` wrap property keys, labels, and relationship types
   in bare backticks and do NOT escape a backtick occurring inside one. A
   name containing a backtick would produce a syntactically broken script.
   Every key/label/type in the current graph is backtick-free.
2. Neo4j temporal (Date, DateTime, Duration), spatial (Point), and byte-array
   property values fall through `literal()`'s `str(v)` branch and would
   replay as plain strings, silently losing their native type. Every
   property in the current graph is already a plain string.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from neo4j import GraphDatabase


def literal(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(literal(x) for x in v) + "]"
    return "'" + str(v).replace("\\", "\\\\").replace("'", "\\'") + "'"


def props(d: dict, extra: dict | None = None) -> str:
    merged = dict(d)
    if extra:
        merged.update(extra)
    if not merged:
        return "{}"
    return "{" + ", ".join(f"`{k}`: {literal(v)}"
                           for k, v in sorted(merged.items())) + "}"


def ship(local_path: Path) -> None:
    remote = os.getenv("REMOTE", "parkave@192.168.4.76")
    dest = os.getenv("DEST", "/data/data_bundle/v1/neo4j-v1.cypher")
    dest_dir = dest.rsplit("/", 1)[0]
    subprocess.run(["ssh", remote, f"mkdir -p {dest_dir}"], check=True)
    subprocess.run(["rsync", "-a", str(local_path), f"{remote}:{dest}"],
                    check=True)
    print(f"  shipped to {remote}:{dest}")


def main() -> int:
    uri = os.getenv("NEO4J_URI", "bolt://192.168.4.76:7687")
    auth = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD"))
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "// ccf_dataprep v1 Neo4j graph — replayable export",
        "// Replay with: cypher-shell -u neo4j -p <pw> -f neo4j-v1.cypher",
        "MATCH (n) DETACH DELETE n;",
        "CREATE CONSTRAINT b1id IF NOT EXISTS "
        "FOR (n:`_B1`) REQUIRE n.`_b1id` IS UNIQUE;",
    ]
    driver = GraphDatabase.driver(uri, auth=auth)
    with driver.session() as s:
        nodes = 0
        for rec in s.run("MATCH (n) RETURN n, elementId(n) AS eid"):
            n, eid = rec["n"], rec["eid"]
            labels = "".join(f":`{l}`" for l in sorted(n.labels))
            lines.append(
                f"CREATE (n{labels}:`_B1` {props(dict(n), {'_b1id': eid})});")
            nodes += 1
        rels = 0
        for rec in s.run(
            "MATCH (a)-[r]->(b) RETURN elementId(a) AS a, elementId(b) AS b, "
            "type(r) AS t, properties(r) AS p"
        ):
            lines.append(
                f"MATCH (a:`_B1` {{`_b1id`: {literal(rec['a'])}}}), "
                f"(b:`_B1` {{`_b1id`: {literal(rec['b'])}}}) "
                f"CREATE (a)-[:`{rec['t']}` {props(rec['p'])}]->(b);")
            rels += 1
    driver.close()

    # The scaffolding label and id exist only to reconnect relationships.
    # Leaving them behind would silently add a label to every v1 node. The
    # constraint created above is the same kind of leftover, just invisible
    # to a node/property check: restore_neo4j.sh's and verify_install.py's
    # counts both look at `_B1` NODES, so a surviving constraint on a label
    # nothing carries anymore would never show up in either. Drop it too.
    lines.append("MATCH (n:`_B1`) REMOVE n:`_B1` REMOVE n.`_b1id`;")
    lines.append("DROP CONSTRAINT b1id IF EXISTS;")
    out.write_text("\n".join(lines) + "\n")
    print(f"  {nodes} nodes, {rels} relationships -> {out}")

    if nodes == 0:
        return 1

    ship(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
