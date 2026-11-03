#!/usr/bin/env python3
"""Wave 19 Task 7 — the engineered `economicallyDependentOn` edges.

§C names this "the one relationship the public estate cannot supply" — a
judgment that lives in an analyst's head or a spreadsheet, not in a filing.
This generator writes that judgment down as data: which entity depends on
which, on what basis, asserted by whom, on what date. `loaders/load_group_edges.py`
turns it into Fluree triples.

## Why these four pairs, not some other four

Chosen by measuring the live estate (`connectedTo` edges + `ccf_v2.facility`),
not by picking company names that sounded plausible. Three jobs, one edge set:

1. **A group control-based grouping alone would miss.** TransDigm Group Inc
   is a $14.6bn borrower with ZERO `connectedTo` edges of any kind (confirmed
   live: its node never appears as subject or object of any `connectedTo`
   triple) -- it is not merely a small control component, it is not a
   component at all. Merging it with Vertiv Holdings Co produces a group that
   the control graph cannot produce by any traversal, at any depth.

2. **An edge that changes which limit binds**, without inventing a limit.
   Measured (`$` = tier 1 capital $295.8bn):

   | Entity                    | Basis    | Exposure   | % of tier 1 |
   |---------------------------|----------|-----------:|------------:|
   | Bausch Health (largest control group) | control | $16.015bn | 5.415% |
   | TransDigm Group Inc       | singleton | $14.600bn | 4.936% |
   | Vertiv Holdings Co        | control  |  $7.887bn | 2.666% |
   | TransDigm + Vertiv        | **both** | $22.487bn | **7.602%** |

   Neither TransDigm nor Vertiv alone crosses 4.936%; merged, they cross
   7.602%. Any internal appetite set in **(4.936%, 7.602%]** -- e.g. the
   design doc's own recommended band, below Bausch's 5.415% -- makes this
   merged group breach an appetite that neither predecessor would have
   breached alone. Task 9 sets the actual number; Task 15 recomputes the
   crossing live. Nothing here is flagged as a breach -- there is no limit
   yet to breach against (see the brief's ordering note).

3. **Close the jurisdiction gap honestly.** 9 of 26 control-basis groups
   span >= 3 jurisdictions on their own. Every one of this estate's 10
   facility-holding singletons is US-only, so pairing a singleton with
   anything adds no country -- only merging two groups that each already
   carry a DIFFERENT non-US country crosses a third. Three such pairs exist
   with a genuinely defensible judgment behind them (below); a fourth was
   considered (Agilysys/Hain Celestial: hospitality software vendor and a
   packaged-foods company) and rejected -- no supply, funding or tenancy
   relationship between them is remotely plausible, so it is not forced.
   That leaves the collective count at 9 + 3 = 12 of ~15, and the shortfall
   is recorded in the task report rather than papered over.

## The four edges

| Dependent -> depended-upon | Basis | Countries added |
|---|---|---|
| Vertiv Holdings Co -> TransDigm Group Inc | shared funding | none (US/US) |
| The Container Store Group, Inc. -> Griffon Corporation | supplier concentration | SE+US -> SE+AU+US |
| Super Micro Computer, Inc. -> Extreme Networks, Inc. | supplier concentration | NL+US -> NL+IN+US |
| The Hain Celestial Group, Inc. -> Tupperware Brands Corporation | supplier concentration | GB+US -> GB+IN+US |

Each is between two REAL, GLEIF-registered public companies -- the entities
are `public`, exactly as Task 6 loaded them. Only the RELATIONSHIP is
invented, which is why the edge (not the node) carries
`ex:edgeProvenance "synthetic — engineered"`. This is the same shape the
design doc already committed to for Reg O (real bank, invented insider): a
real company's public identity is never in question, and no sentence here
asserts anything about it as fact.

**Every edge is directed from the smaller/more concentration-exposed party
to the larger/anchor party** -- a modelling convention, not a claim that the
larger party is somehow the "control" side; `economicallyDependentOn` groups
symmetrically for large-exposure purposes regardless of which name is
subject.

Asserted by a single named credit-risk analyst who already exists in
`ccf_v2.banker` (`BKR011`, Rafael Adeyemi, `credit` / `analyst` / `Credit
Risk` desk) -- reusing an existing identifier rather than inventing a new
one, the same discipline the estate applies to entity URIs. One analyst
maintaining a standing "connected clients" watchlist is exactly the
spreadsheet-in-an-analyst's-head this product's data is supposed to
formalise.

Output: sources/screening/wave19_dependency_edges.json

    uv run generators/generate_dependency_edges.py
"""

from __future__ import annotations

import json
import sys

from ccf.config import REPO_ROOT

SCREEN = REPO_ROOT / "sources" / "screening"
ARTIFACT = SCREEN / "wave19_dependency_edges.json"

#: An existing credit-risk-desk analyst id from ccf_v2.banker -- reused, not
#: invented. Live-checked 2026-08-27: BKR011 = Rafael Adeyemi, role=credit,
#: seniority=analyst, desk=Credit Risk.
ANALYST = "BKR011"

PROVENANCE = "synthetic — engineered"

#: (dependent_lei, dependent_name, depended_lei, depended_name, basis,
#:  asserted_on) -- names are recorded for the report/docstring only; the
#: loader resolves both LEIs live via entity_uri_by_lei(), never constructs
#: a URI from them.
EDGES = [
    {
        "dependent_lei": "549300KTTIRAOGXCRV69",
        "dependent_name": "Vertiv Holdings Co",
        "depended_lei": "549300EQD0ZXRSMG3549",
        "depended_name": "TransDigm Group Inc",
        "basis": (
            "shared funding — Vertiv's committed-but-undrawn revolver sits "
            "within a lending syndicate whose largest capacity provider also "
            "leads TransDigm's term loan B; the desk's note treats a "
            "liquidity shock at that shared lender as a common driver of "
            "available capacity for both names (depended-upon: TransDigm "
            "Group Inc, 549300EQD0ZXRSMG3549)."
        ),
        "asserted_on": "2026-05-14",
        "job": "job1 (new group) + job2 (changes binding limit)",
    },
    {
        "dependent_lei": "529900L7KB2N9KXCDI76",
        "dependent_name": "The Container Store Group, Inc.",
        "depended_lei": "5493000C2SGNC7ZN3242",
        "depended_name": "Griffon Corporation",
        "basis": (
            "supplier concentration — Container Store's private-label "
            "closet and shelving line sources a material share of "
            "components from Griffon's ClosetMaid/home-storage segment; "
            "the coverage desk's note treats continuity of that single "
            "supplier as a point of failure for a same-day-available SKU "
            "range (depended-upon: Griffon Corporation, "
            "5493000C2SGNC7ZN3242)."
        ),
        "asserted_on": "2026-06-02",
        "job": "job1 (new group) + job3 (SE, AU, US)",
    },
    {
        "dependent_lei": "54930022CZO1N2UGVW07",
        "dependent_name": "Super Micro Computer, Inc.",
        "depended_lei": "549300WRECW11X94UB57",
        "depended_name": "Extreme Networks, Inc.",
        "basis": (
            "supplier concentration — Super Micro's qualified rack-scale "
            "AI/GPU reference architecture designates Extreme Networks' "
            "switch fabric as the sole qualified network interconnect for "
            "that platform SKU; the desk's vendor-concentration note flags "
            "that single-sourced component as a shipment-risk driver "
            "(depended-upon: Extreme Networks, Inc., 549300WRECW11X94UB57)."
        ),
        "asserted_on": "2026-07-08",
        "job": "job1 (new group) + job3 (NL, IN, US)",
    },
    {
        "dependent_lei": "5493000S8QXWHLIXDP75",
        "dependent_name": "The Hain Celestial Group, Inc.",
        "depended_lei": "G8NWFN4YP7CR6FOP4886",
        "depended_name": "Tupperware Brands Corporation",
        "basis": (
            "supplier concentration — a material share of Hain Celestial's "
            "on-the-go snack and beverage SKUs ship in Tupperware-"
            "manufactured reusable packaging under a single-source "
            "packaging arrangement the coverage desk has flagged "
            "(depended-upon: Tupperware Brands Corporation, "
            "G8NWFN4YP7CR6FOP4886)."
        ),
        "asserted_on": "2026-07-29",
        "job": "job1 (new group) + job3 (GB, IN, US)",
    },
]


def build() -> dict:
    subjects = [e["dependent_lei"] for e in EDGES]
    if len(subjects) != len(set(subjects)):
        # Each subject carries at most one outgoing edge in this design --
        # that is what makes ex:assertedBy/assertedOn/dependencyBasis safe
        # as node-level literals (Task 6's own docstring: a node-level mark
        # is wrong ONLY when the node could carry more than one such edge).
        # A repeat here would silently break that guarantee.
        raise SystemExit(
            "FATAL: a dependent LEI appears more than once -- the "
            "node-level-literal design requires at most one outgoing "
            "economicallyDependentOn edge per subject. Fix EDGES or move "
            "to a reified assertion node."
        )
    return {
        "analyst": ANALYST,
        "provenance": PROVENANCE,
        "edges": EDGES,
    }


def main() -> int:
    doc = build()
    SCREEN.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")

    print("Wave 19 Task 7 — engineered economicallyDependentOn edges\n")
    print(f"  analyst          {doc['analyst']}")
    print(f"  provenance       {doc['provenance']}")
    print(f"  edges            {len(doc['edges'])}")
    for e in doc["edges"]:
        print(f"    {e['dependent_name']!r} -> {e['depended_name']!r}  "
              f"asserted {e['asserted_on']}  [{e['job']}]")
    print(f"\n  wrote {ARTIFACT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
