#!/usr/bin/env python3
"""192 graph entities carry no provenance class. Rule #1 says every one must.

Non-negotiable rule #1: *three provenance classes, labelled per element.* 624
of the ledger's 816 `cmns-org:LegalEntity` nodes carry `ex:provenance`; 192 do
not, and have not since the waves that loaded them:

    150  ICJ-SPV-*    ICIJ Offshore Leaks vehicles      (Wave 13b)
     40  ICJ-INT-*    ICIJ Offshore Leaks intermediaries (Wave 13b)
      2  RSSD-*       JPMorgan Chase reporting bank      (Wave 13b)

**Nothing could see them.** `conditions.py` counts entities as
`?s ex:provenance ?p`, so an unlabelled node is not merely unlabelled — it is
INVISIBLE to the check that is supposed to police labelling. The floor of 500
was cleared by the 624 that were labelled, and the 192 that were not could
never have failed it. A gate whose population is defined by the property it
polices cannot detect the property's absence.

**The class is read from each node's own source row, never inferred.**
`offshore_vehicle` and `offshore_intermediary` are `synthetic — engineered`;
`reporting_bank` is `public`. Postgres is the single writer for those, so this
copies a recorded fact rather than choosing one. A node whose row cannot be
found is reported and skipped, because guessing a provenance class is exactly
the dishonesty rule #1 exists to prevent.

Idempotent: nodes that already carry a class are not touched.

Run: uv run loaders/label_unlabelled_provenance_wave15.py --dry-run
     uv run loaders/label_unlabelled_provenance_wave15.py
"""

from __future__ import annotations

import argparse
import sys

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2
from ccf.config import PG_SCHEMA_V2 as S
from ccf.config import pg_connect

LEGAL_ENTITY = "https://www.omg.org/spec/Commons/Organizations/LegalEntity"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
BATCH = 400

#: local-name prefix -> (table, id column, how the local name maps to the id)
SOURCES = [
    ("ICJ-SPV-", "offshore_vehicle", "vehicle_id", lambda n: n),
    ("ICJ-INT-", "offshore_intermediary", "intermediary_id", lambda n: n),
    ("RSSD-", "reporting_bank", "rssd", lambda n: n[len("RSSD-"):]),
]


def unlabelled() -> list[str]:
    def subjects(where: str) -> set[str]:
        return {b["s"]["value"] for b in fluree.query(
            f"SELECT ?s FROM <{FLUREE_LEDGER_V2}> WHERE {{ {where} }} "
            f"LIMIT 9000")["results"]["bindings"]}

    typed = subjects(f"?s <{RDF_TYPE}> <{LEGAL_ENTITY}>")
    labelled = subjects(f"?s <{RDF_TYPE}> <{LEGAL_ENTITY}> . "
                        f"?s <{EX}provenance> ?p")
    return sorted(typed - labelled)


def provenance_by_id() -> dict[str, str]:
    """Every candidate id mapped to the class ITS OWN source row records."""
    out: dict[str, str] = {}
    with pg_connect() as conn, conn.cursor() as cur:
        for _prefix, table, idcol, _strip in SOURCES:
            cur.execute(f'SELECT {idcol}, provenance FROM "{S}".{table}')
            for key, prov in cur.fetchall():
                out[f"{table}:{key}"] = prov
    return out


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    bare = unlabelled()
    print(f"  LegalEntity nodes with no provenance   {len(bare)}")
    if not bare:
        print("\n  nothing to label — rule #1 already holds.")
        return 0

    recorded = provenance_by_id()
    triples: list[str] = []
    unresolved: list[str] = []
    counts: dict[str, int] = {}
    sample: tuple[str, str] | None = None

    for subject in bare:
        local = subject.rsplit("/", 1)[-1]
        prov = None
        for prefix, table, _idcol, strip in SOURCES:
            if local.startswith(prefix):
                prov = recorded.get(f"{table}:{strip(local)}")
                break
        if prov is None:
            unresolved.append(local)
            continue
        triples.append(f'<{subject}> <{EX}provenance> "{esc(prov)}" .')
        counts[prov] = counts.get(prov, 0) + 1
        if sample is None:
            sample = (subject, prov)

    print(f"  resolved from their source rows        {len(triples)}")
    for prov, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"     {prov:26s} {n}")

    if unresolved:
        # Not a warning. A node with no source row has no honest class, and
        # inventing one is the failure rule #1 is written against.
        print(f"\n  FAIL: {len(unresolved)} nodes have no source row and so no "
              f"honest provenance: {unresolved[:8]}", file=sys.stderr)
        print("  Find where they were loaded before labelling them.",
              file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"\n  [dry-run] nothing written. Sample: {triples[0][:100]}")
        return 0

    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(triples[i:i + BATCH]) + "\n}")

    assert sample is not None
    subject, prov = sample
    got = [b["p"]["value"] for b in fluree.query(
        f"SELECT ?p FROM <{FLUREE_LEDGER_V2}> WHERE {{ "
        f"<{subject}> <{EX}provenance> ?p }}")["results"]["bindings"]]
    if got != [prov]:
        print(f"\n  FAIL: <{subject}> reads back as {got}, expected [{prov!r}]",
              file=sys.stderr)
        return 1
    left = len(unlabelled())
    print(f"\n  verified: <{subject.rsplit('/', 1)[-1]}> -> {prov!r}")
    print(f"  LegalEntity nodes still unlabelled: {left}  (must be 0)")
    return 1 if left else 0


if __name__ == "__main__":
    sys.exit(main())
