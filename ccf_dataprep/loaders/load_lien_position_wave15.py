#!/usr/bin/env python3
"""Wave 15 — move lien priority into Fluree, where §C assigns it.

`collateral-and-setoff-coverage` §C says:

    | Lien priority and filing date | UCC-1 filing records | public | Fluree | R, T |

Since Wave 9 it has lived in `ccf_v2.collateral_pledge.priority` as the free
text 'first' / 'second', and Fluree has held 95 *unqualified* collateral edges.
Walking the graph, a first lien and a second lien were indistinguishable --
which is verbatim the failure the product exists to refute (§A: "a second-lien
position recorded as 'secured' alongside a first-lien position recorded
identically produces two facilities that look equally protected and are not").

`partition.py` never saw it because every one of its checks runs in the one
direction: nothing had LEAKED into a store. A missing element cannot leak.
`validators/spec_coverage.py` is the other half and is what caught this.

## Why the pledge is reified

Priority is a property of the (facility, asset) PAIR, not of either endpoint.
`COL-00012` and `COL-00044` are each pledged to two facilities at DIFFERENT
priorities, so hanging `lienPosition` on the asset would have to pick one and
silently lose the other -- the same shape as the composite-threshold defect in
Wave 14, where one value per subject dropped half of each pair. So each pledge
becomes a node.

## Why FIBO's named individuals rather than the free text

FIBO models this enumeration as a classifier class plus two values, and the
definitions are an exact fit for what the column already held:

    LenderLienPosition      "classifier indicating whether the lender has the
                             primary lien position with respect to an asset
                             used as collateral for the loan"
    PrimaryLienPosition     "first position in the order of seniority..."
    SubordinateLienPosition "secondary or lower position..."

'first' -> PrimaryLienPosition, 'second' -> SubordinateLienPosition, 1:1.

Both individuals were on the vault's do-not-bind list until 2026-08-24, recorded
as "referenced in the FIBO sources but not declared". They ARE declared -- as
`owl:NamedIndividual`, which the old type-filtered scan could not see. Verified
here by grepping the ontology for `rdf:about`, never by fetching the term URL:
that path is content-negotiated and returns HTTP 200 for names that do not
exist.

## Single writer

Fluree becomes sole authority. `collateral_pledge.priority` is dropped, but
only after this loader has verified the ledger holds a lien position for every
pledge -- the drop is guarded, not sequenced-and-hoped. The two source
artifacts keep `priority`, so the move is reversible by reload.

Run: uv run loaders/load_lien_position_wave15.py
     uv run loaders/load_lien_position_wave15.py --drop-postgres-column
"""

from __future__ import annotations

import argparse
import json
import sys

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2, PG_SCHEMA_V2, REPO_ROOT, pg_connect

SCREEN = REPO_ROOT / "sources" / "screening"
FIBO = "https://spec.edmcouncil.org/fibo/ontology/"

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
OWL_CLASS = "http://www.w3.org/2002/07/owl#Class"

#: The classifier class, bound since Wave 9 and until now declared with zero
#: instances -- the schema half of §C row 1 with nothing classified by it.
C_LIEN_POSITION = f"{FIBO}LOAN/LoansGeneral/Loans/LenderLienPosition"

#: The two values. Verified declared in LOAN/LoansGeneral/Loans as
#: owl:NamedIndividual of LenderLienPosition, 2026-08-24.
I_PRIMARY = f"{FIBO}LOAN/LoansGeneral/Loans/PrimaryLienPosition"
I_SUBORDINATE = f"{FIBO}LOAN/LoansGeneral/Loans/SubordinateLienPosition"

#: Free text -> FIBO individual. Anything outside this map is a hard error: a
#: silently unmapped priority would produce a pledge node with no position,
#: which reads downstream as "unqualified" -- the exact defect being fixed.
POSITION = {"first": I_PRIMARY, "second": I_SUBORDINATE}

C_PLEDGE = f"{EX}CollateralPledge"
P_PLEDGED_FACILITY = f"{EX}pledgedFacility"
P_PLEDGED_ASSET = f"{EX}pledgedAsset"
P_LIEN_POSITION = f"{EX}lienPosition"

BATCH = 400


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def triple(s: str, p: str, o: str, *, literal: bool = False) -> str:
    obj = f'"{esc(o)}"' if literal else f"<{o}>"
    return f"<{s}> <{p}> {obj} ."


def pledge_uri(facility_id: str, asset_id: str) -> str:
    return f"{EX}pledge-{facility_id}-{asset_id}"


def source_pledges() -> list[dict]:
    """Every pledge, from the generated artifacts rather than from Postgres.

    Deliberately NOT read from `collateral_pledge`: this loader drops that
    column, so reading it would make the loader non-re-runnable the moment it
    succeeded. The artifacts are where the priority was decided.
    """
    wave9 = json.loads((SCREEN / "collateral_layer.json").read_text())
    wave13a = json.loads((SCREEN / "wave13a_collateral_extension.json").read_text())
    rows = list(wave9["secured_edges"]) + list(wave13a["pledges"])

    seen: dict[tuple[str, str], str] = {}
    for r in rows:
        key = (r["facility_id"], r["asset_id"])
        if key in seen and seen[key] != r["priority"]:
            raise RuntimeError(
                f"two artifacts disagree on priority for {key}: "
                f"{seen[key]!r} vs {r['priority']!r}"
            )
        seen[key] = r["priority"]
    return rows


def existing_nodes() -> set[str]:
    """Every node present in the ledger -- subject of at least one triple.

    Constructing `ex:{id}` and trusting it is the Wave 5 phantom-borrower
    defect: a valid triple with the right count, pointing at nothing. Resolve
    instead.

    Presence, deliberately, NOT typedness. The first cut of this asked for
    subjects of `rdf:type` and refused nine facilities that are really there --
    see `untyped_facilities()`. Refusing a node that exists because it is
    under-described would have been the wrong remedy applied by the wrong
    loader: this one does not own facility nodes.
    """
    q = f"SELECT DISTINCT ?s FROM <{FLUREE_LEDGER_V2}> WHERE {{ ?s ?p ?o }}"
    return {b["s"]["value"] for b in fluree.query(q)["results"]["bindings"]}


def untyped_facilities() -> list[str]:
    """Facilities carrying collateral edges but no `rdf:type` in the ledger.

    Not this loader's defect and not its to fix -- `load_exposure_wave9.py` is
    the single writer for facility nodes, and `load_collateral_wave13a.py`
    asserted `isCollateralizedBy` from ten facilities without asking it to
    create them. Reported rather than swallowed, because it bounds what this
    fix achieves: Fluree runs without inference, so a traversal that starts
    from `?f rdf:type CreditFacility` reaches neither those facilities nor the
    lien positions written here for them. Lien priority becomes queryable for
    41 of 50 facilities, not 50.
    """
    p_coll = f"{FIBO}FBC/DebtAndEquities/Debt/isCollateralizedBy"
    subj = {b["s"]["value"] for b in fluree.query(
        f"SELECT ?s ?o FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ ?s <{p_coll}> ?o }}")["results"]["bindings"]}
    typed = {b["s"]["value"] for b in fluree.query(
        f"SELECT ?s ?t FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ ?s <{RDF_TYPE}> ?t }}")["results"]["bindings"]}
    return sorted(subj - typed)


def ledger_positions() -> dict[str, str]:
    """pledge node -> lien position IRI currently asserted."""
    q = (f"SELECT ?s ?o FROM <{FLUREE_LEDGER_V2}> "
         f"WHERE {{ ?s <{P_LIEN_POSITION}> ?o }}")
    out: dict[str, str] = {}
    for b in fluree.query(q)["results"]["bindings"]:
        out[b["s"]["value"]] = b["o"]["value"]
    return out


def build(pledges: list[dict], nodes: set[str]) -> tuple[list[str], list[str]]:
    """Returns (triples, problems). Problems are fatal; nothing is written."""
    triples: list[str] = []
    problems: list[str] = []

    # Schema: the classifier and its two values, typed explicitly. Fluree runs
    # without inference, so a query for LenderLienPosition finds these only if
    # they carry the type outright (CLAUDE.md rule 7).
    triples += [
        triple(C_LIEN_POSITION, RDF_TYPE, OWL_CLASS),
        triple(C_LIEN_POSITION, RDFS_LABEL, "LenderLienPosition", literal=True),
        triple(C_PLEDGE, RDF_TYPE, OWL_CLASS),
        triple(C_PLEDGE, RDFS_LABEL, "CollateralPledge", literal=True),
    ]
    for iri, label in ((I_PRIMARY, "PrimaryLienPosition"),
                       (I_SUBORDINATE, "SubordinateLienPosition")):
        triples += [
            triple(iri, RDF_TYPE, C_LIEN_POSITION),
            triple(iri, RDFS_LABEL, label, literal=True),
        ]

    for p in pledges:
        fac, ast, pri = p["facility_id"], p["asset_id"], p["priority"]
        position = POSITION.get(pri)
        if position is None:
            problems.append(f"unmapped priority {pri!r} on {fac}/{ast}")
            continue
        fac_uri, ast_uri = f"{EX}{fac}", f"{EX}{ast}"
        if fac_uri not in nodes:
            problems.append(f"facility node absent from ledger: {fac}")
            continue
        if ast_uri not in nodes:
            problems.append(f"asset node absent from ledger: {ast}")
            continue
        node = pledge_uri(fac, ast)
        triples += [
            triple(node, RDF_TYPE, C_PLEDGE),
            triple(node, P_PLEDGED_FACILITY, fac_uri),
            triple(node, P_PLEDGED_ASSET, ast_uri),
            triple(node, P_LIEN_POSITION, position),
            triple(node, RDFS_LABEL, f"{fac} / {ast} ({pri} lien)", literal=True),
        ]
    return triples, problems


def conflicts(pledges: list[dict]) -> list[str]:
    """Refuse to write when the ledger holds a DIFFERENT position.

    Fluree is append-only with set semantics, so a re-run is a no-op but a
    CHANGED source value would insert a second, contradicting position on the
    same pledge and leave both standing forever with nothing marking which
    supersedes which. Same guard as `load_abs_fluree_wave14.ledger_conflicts`.
    """
    held = ledger_positions()
    out: list[str] = []
    for p in pledges:
        node = pledge_uri(p["facility_id"], p["asset_id"])
        want = POSITION.get(p["priority"])
        got = held.get(node)
        if got is not None and got != want:
            out.append(f"{node}: ledger holds {got.rsplit('/', 1)[-1]}, "
                       f"source says {p['priority']!r}")
    return out


def drop_postgres_column(expected: int) -> int:
    """Drop `collateral_pledge.priority`, but only if Fluree really has it.

    Guarded rather than sequenced: an unguarded drop after a partially failed
    load destroys the only copy. Counts the pledges carrying a position in the
    ledger and refuses unless every one is there.
    """
    held = ledger_positions()
    if len(held) < expected:
        print(f"  REFUSING to drop: ledger holds {len(held)} lien positions, "
              f"expected {expected}")
        return 1
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'ALTER TABLE "{PG_SCHEMA_V2}".collateral_pledge '
                    "DROP COLUMN IF EXISTS priority")
        conn.commit()
    print(f"  dropped collateral_pledge.priority "
          f"({len(held)} positions verified in Fluree first)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--drop-postgres-column", action="store_true",
                    help="hand single-writer authority to Fluree")
    args = ap.parse_args()

    print("Wave 15 — lien position into Fluree\n")

    pledges = source_pledges()
    print(f"  {len(pledges)} pledges in the source artifacts")

    bad = conflicts(pledges)
    if bad:
        print("\n  LEDGER CONFLICT — a different position is already asserted:")
        for b in bad:
            print(f"    {b}")
        print("\n  Superseding is a modelled act, never a side effect of a "
              "reload. Nothing written.")
        return 1

    nodes = existing_nodes()
    triples, problems = build(pledges, nodes)
    if problems:
        print("\n  REFUSING TO WRITE — unresolved targets or values:")
        for p in problems[:20]:
            print(f"    {p}")
        return 1

    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(triples[i:i + BATCH]) + "\n}")
    print(f"  wrote {len(triples)} triples")

    held = ledger_positions()
    n_primary = sum(1 for v in held.values() if v == I_PRIMARY)
    n_sub = sum(1 for v in held.values() if v == I_SUBORDINATE)
    print(f"  lien positions in ledger: {len(held)} "
          f"({n_primary} primary · {n_sub} subordinate)")
    if len(held) != len(pledges):
        print(f"  MISMATCH: {len(pledges)} pledges but {len(held)} positions")
        return 1

    untyped = untyped_facilities()
    if untyped:
        print(f"\n  BOUNDED: {len(untyped)} facilities carry collateral edges "
              f"but no rdf:type in Fluree —")
        print(f"    {', '.join(u.rsplit('/', 1)[-1] for u in untyped)}")
        print("  written by load_collateral_wave13a.py, which asserts "
              "isCollateralizedBy without")
        print("  creating the facility node. Under no-inference a traversal "
              "from CreditFacility")
        print("  reaches neither them nor their lien positions. Owner is "
              "load_exposure_wave9.py.")

    if args.drop_postgres_column:
        return drop_postgres_column(len(pledges))

    print("\n  Postgres still holds collateral_pledge.priority — two copies of "
          "one fact.")
    print("  Re-run with --drop-postgres-column to hand authority to Fluree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
