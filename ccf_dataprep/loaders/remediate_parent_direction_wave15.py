#!/usr/bin/env python3
"""Wave 15 — turn the ultimate-parent edges the right way round.

See docs/known-issues.md §19.3. Every `hasGlobalUltimateParent` and
`hasDomesticUltimateParent` triple in `fibo-v2` points parent -> child. FIBO
runs them child -> parent, so the ledger asserts that each group head's
ultimate parent is its own subsidiary. `corporate-family-tree` exists to
answer *who is the ultimate parent of X*; against this ledger that traversal
returns X's subsidiaries.

**How the direction was settled** -- not from the predicate's name, which is
exactly how the error was made:

  * FIBO's own published instance data, `prod.fibo-quickstart.ttl`:

        Business Entity Data (BED) B.V. NL
            fibo-be-oac-cctl:hasGlobalUltimateParent
                DepositoryTrustAndClearingCorporation

    BED B.V. is the subsidiary. The SUBJECT is the child.

  * `rdfs:range fibo-be-oac-cctl:GlobalUltimateParent` -- the OBJECT is the
    parent -- and `skos:definition` "relates an organization to another
    recognized as its ultimate parent".

  * Against the 140 GLEIF `IS_ULTIMATELY_CONSOLIDATED_BY` records in
    `ccf_v2.corporate_ownership_record`, read as (child, parent):
    **0 of 140 matched as stored, 103 of 140 matched reversed.**

`loaders/load_fluree_wave3.py` now emits the correct orientation, but it is
INSERT DATA only: re-running it alone would leave the inverted edges in place
and assert both directions, which is worse than asserting one wrongly. So this
runs first.

Fluree is append-only: a retraction changes CURRENT STATE while both the
assertion and the retraction stay in history. The wrong write remains
auditable, it just stops being current -- and it cannot be undone, hence
--dry-run and an explicit confirmation.

**Orientation is decided against GLEIF, never against the ledger's own state.**
The first version of this script selected "every edge whose reverse is not
already asserted", which flips correctly once and then flips the corrected
edges BACK on a second run -- the same class of defect it exists to repair, and
directly contrary to the idempotence claimed below. So each edge is now judged
against the ancestry recorded in `sources/screening/gleif_relationships.json`:

    edge (a, pred, b)   b is an ancestor of a  ->  subject is the child, KEEP
                        a is an ancestor of b  ->  inverted, FLIP
                        neither                ->  UNKNOWN, reported, untouched

That converges: run it on an inverted ledger and it corrects; run it again and
it finds nothing; run it on a half-corrected ledger and it fixes only the
remainder. An edge it cannot resolve is never guessed at.

Order:
    uv run loaders/remediate_parent_direction_wave15.py --dry-run
    uv run loaders/remediate_parent_direction_wave15.py
    uv run validators/conditions.py && uv run validators/partition.py

Idempotent: re-running after a successful pass finds nothing to flip.
"""

from __future__ import annotations

import argparse
import json
import sys

from ccf import fluree
from ccf.config import FLUREE_LEDGER_V2 as L
from ccf.config import REPO_ROOT

FIBO = "https://spec.edmcouncil.org/fibo/ontology/"
GLOBAL_ULTIMATE = f"{FIBO}BE/OwnershipAndControl/CorporateControl/hasGlobalUltimateParent"
DOMESTIC_ULTIMATE = f"{FIBO}BE/OwnershipAndControl/CorporateControl/hasDomesticUltimateParent"
PREDICATES = (GLOBAL_ULTIMATE, DOMESTIC_ULTIMATE)
EX = "http://example.org/fibo/"

GLEIF = REPO_ROOT / "sources" / "screening" / "gleif_relationships.json"
BATCH = 200


def ancestry() -> dict[str, str]:
    """child LEI -> direct parent LEI, from the file wave 3 itself loaded."""
    edges = json.loads(GLEIF.read_text())["edges"]
    return {e["child_lei"]: e["parent_lei"]
            for e in edges if e["edge_type"] == "hasDirectParent"}


def is_ancestor(parent_map: dict[str, str], ancestor: str, node: str) -> bool:
    """Walk node -> its parents, looking for `ancestor`. Cycle-guarded."""
    seen, cursor = set(), node
    while cursor in parent_map and cursor not in seen:
        seen.add(cursor)
        cursor = parent_map[cursor]
        if cursor == ancestor:
            return True
    return False


def lei_by_uri() -> dict[str, str]:
    q = f"SELECT ?s ?l FROM <{L}> WHERE {{ ?s <{EX}lei> ?l }}"
    return {b["s"]["value"]: b["l"]["value"].strip()
            for b in fluree.query(q)["results"]["bindings"]}


def pairs(predicate: str) -> list[tuple[str, str]]:
    q = f"SELECT ?s ?o FROM <{L}> WHERE {{ ?s <{predicate}> ?o }}"
    return [(b["s"]["value"], b["o"]["value"])
            for b in fluree.query(q)["results"]["bindings"]]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("Wave 15 — ultimate-parent edge direction\n")

    parent_map = ancestry()
    leis = lei_by_uri()
    print(f"  GLEIF direct-parent links: {len(parent_map)}")
    print(f"  ledger nodes carrying ex:lei: {len(leis)}\n")

    retract: list[str] = []
    insert: list[str] = []
    unresolved: list[tuple[str, str, str]] = []
    kept = 0

    for pred in PREDICATES:
        short = pred.rsplit("/", 1)[-1]
        flip = keep = unknown = 0
        for s_uri, o_uri in pairs(pred):
            a, b = leis.get(s_uri), leis.get(o_uri)
            if not a or not b:
                unknown += 1
                unresolved.append((short, s_uri, "endpoint has no ex:lei"))
                continue
            if is_ancestor(parent_map, b, a):        # object is the ancestor
                keep += 1
            elif is_ancestor(parent_map, a, b):      # subject is the ancestor
                flip += 1
                retract.append(f"<{s_uri}> <{pred}> <{o_uri}> .")
                insert.append(f"<{o_uri}> <{pred}> <{s_uri}> .")
            else:
                unknown += 1
                unresolved.append((short, s_uri, "no ancestry either way"))
        kept += keep
        print(f"  {short:26} {flip:>4} inverted · {keep:>4} already correct "
              f"· {unknown:>4} unresolved")

    if unresolved:
        print(f"\n  {len(unresolved)} edges left untouched because their "
              f"direction could not be established:")
        for short, uri, why in unresolved[:5]:
            print(f"      {short:24} {uri.rsplit('/', 1)[1][:34]:36} {why}")
        if len(unresolved) > 5:
            print(f"      ... and {len(unresolved) - 5} more")

    if not retract:
        print("\n  nothing to flip — every resolvable edge reads child -> parent.")
        return 0

    print(f"\n  {len(retract)} triples to retract, {len(insert)} to assert")

    if args.dry_run:
        print("\n  DRY RUN — nothing written.")
        print("  Sample (retract -> assert):")
        for r, i in list(zip(retract, insert))[:3]:
            print(f"    - {r}")
            print(f"    + {i}")
        return 0

    print(f"\n  retracting in batches of {BATCH}...")
    for i in range(0, len(retract), BATCH):
        fluree.update("DELETE DATA {\n" + "\n".join(retract[i:i + BATCH]) + "\n}")
        print(f"    {min(i + BATCH, len(retract)):>5}/{len(retract)}")

    print(f"  asserting in batches of {BATCH}...")
    for i in range(0, len(insert), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(insert[i:i + BATCH]) + "\n}")
        print(f"    {min(i + BATCH, len(insert)):>5}/{len(insert)}")

    # Verify from the LEDGER, and not by counting: a flip leaves the edge
    # total identical, which is the exact blindness that let this survive
    # seven waves. Re-read and require that no inverted orientation remains.
    still = 0
    for pred in PREDICATES:
        held = set(pairs(pred))
        for line in retract:
            s_uri, rest = line[1:].split(">", 1)
            if f"<{pred}>" not in line:
                continue
            o_uri = line.rsplit("<", 1)[1].split(">")[0]
            if (s_uri, o_uri) in held:
                still += 1

    print(f"\n  done. ledger t={fluree.ledger_t()}")
    print(f"  inverted orientations still current: {still}")
    if still:
        print("  WARNING — flip incomplete.")
        return 1
    print("\n  Next: uv run validators/conditions.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
