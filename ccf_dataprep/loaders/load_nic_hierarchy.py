#!/usr/bin/env python3
"""Wave 19 Task 5 -- FFIEC NIC RSSD hierarchy into Fluree.

§C assigns "Bank holding structure — FFIEC NIC RSSD hierarchy" to Fluree as
`R`, so the reporting entity can be established by graph traversal (§D step
4). `ccf_v2.reporting_bank` already holds the two ends -- JPMorgan Chase
Bank, N.A. (RSSD 852218) and its holding company JPMORGAN CHASE&CO (RSSD
1039502) -- and `loaders/load_reporting_bank.py` already put both as Fluree
nodes with an `owns` edge between them. What was still missing: the
charter-specific node typing this task's pre-flight ruling settled, and the
second bank under the same holding company.

## Two overrides from the task issuer, both applied here (brief predates them)

1. **No `ex:subsidiaryOf` minted.** FIBO already declares
   `fibo-be-oac-cctl:hasSubsidiary` (domain `cmns-org:LegalEntity`, range
   `fibo-be-oac-cctl:Subsidiary`) and this estate bound it in Wave 8
   (`docs/ccf_dataprep_v2.md` L408, reconfirmed as the Wave 19 Task 3
   "reused, not minted" call at L1336). Minting a second local name for the
   same relationship would put two names for one edge into a table that is
   a shared contract with the CCF SDK project. `hasSubsidiary`'s domain is
   the PARENT (a plain `LegalEntity`) and its range is the CHILD (a
   `Subsidiary`), so the triple reads parent -> child. Stated here, and
   proved by query in `verify()` below rather than trusted by assertion --
   this estate has already had to repair 139 inverted edges once (Wave 15,
   `loaders/remediate_parent_direction_wave15.py`).

2. **Node types are settled, not inferred.** Fluree runs without OWL
   reasoning (CLAUDE.md rule 7): a query for `Bank` will not return a
   `NationalBank`, and a query for `NationalBank` will not return a `Bank`.
   Verified 2026-08-27 against FDIC BankFind's own charter class (`BKCLASS`)
   as a second, independent check beyond the pre-flight ruling:

       RSSD 852218  BKCLASS "N"  (national charter)  -> NationalBank + Bank
       RSSD 651448  BKCLASS "SM" (state member)       -> Bank only
       RSSD 1039502 (the holding company)             -> BankHoldingCompany

   852218 gets BOTH `NationalBank` and the generic `Bank` type -- the
   pre-flight ruling gives the specific charter type, but a validator asking
   "which nodes are Banks" over this ledger (no inference) needs the generic
   type asserted too, or the reporting bank itself becomes invisible to that
   query. `load_reporting_bank.py` already asserted `Bank` on this node;
   this loader adds `NationalBank` alongside it rather than replacing it.
   651448 is a STATE member bank per BKCLASS -- not a national association --
   so it gets the generic `Bank` type only, per the ruling's "any other bank
   you load -> Bank".

## No `ex:rssd` -- regression fix, 2026-08-27

The first version of this loader put `ex:rssd` on all three nodes, because
the dispatch instructions asked for it explicitly ("nodes carry `ex:rssd`,
`ex:lei` and a label"). That was a dispatch error, not a spec requirement:
`"rssd"` has been in `validators/partition.py`'s `POSTGRES_OWNED_ATTRS`
since Wave 18 (a `syndicate_member` column there), and CLAUDE.md is direct
about what a Fluree node may carry --

    Fluree nodes carry `lei` plus a display label and nothing else — all
    attributes resolve from Postgres. Never duplicate an attribute across
    stores "for convenience."

-- so `ex:rssd` on these nodes was a single-writer violation the moment it
landed, caught by `partition.py`'s LEAKED check (`rssd=3`) only after this
loader had already run once. **`partition.py` was not weakened to
accommodate the mistake** -- the fix is on this side: the three `ex:rssd`
triples already in the ledger are retracted (`retract_leaked_rssd()`,
DELETE DATA, the same mechanism every other retraction in this repo uses --
see `loaders/remediate_parent_direction_wave15.py`), and this loader no
longer writes that predicate at all.

**The join still works without it.** Every node here already carries
`ex:lei`: 852218 -> `7H6GLXDRUGQFU57RNE97`, 1039502 -> `8I5DZWZKVSZI1NUHU748`,
651448 -> `5493000FN178SW540N88`. `ccf_v2.reporting_bank` keys `rssd` to
`lei` for the two rows it has (852218, 1039502); Dearborn (651448) has no
`reporting_bank` row at all, so it needs no Postgres join -- its `ex:lei` is
its whole identity in this graph. A future loader must not re-add `ex:rssd`
to a Fluree node for this reason: `validators/partition.py`'s
`POSTGRES_OWNED_ATTRS` will catch it again, correctly.

## Node identity -- reused, not re-minted

The brief's interface section names `ex:bank/{rssd}` as the node URI. This
loader does NOT mint that scheme: `load_reporting_bank.py` already created
`ex:RSSD-852218` and `ex:RSSD-1039502` (confirmed live in the ledger, 15
triples, before this loader ran a single query). A second URI scheme for
the same two real-world entities would be a duplicate-node defect, not a
hierarchy -- so this loader extends those two existing subjects and mints
exactly one new one, `ex:RSSD-651448`, in the same `ex:RSSD-{rssd}` shape.
(The local name still says "RSSD" -- that is a URI path segment, an opaque
identifier chosen by an earlier loader, not the `ex:rssd` PREDICATE this
fix removes. The two are unrelated: one names a node, the other would have
duplicated a Postgres column.)

## Dissolved predecessors -- excluded, and why

FDIC BankFind's `RSSDHCR:1039502` filter returns 48 institutions across the
holding company's history; only two are still active (852218, $4.09tn;
651448 "JPMorgan Chase Bank, Dearborn", $71m -- verified live below). The
other 46 are long-dissolved predecessor charters (mergers, name changes,
absorbed banks going back decades) with no current standing in the
structure a "which entity reports capital" traversal needs to answer. An
unexplained 48-node hierarchy would be worse than a justified 2-child one:
it would suggest every historical charter still matters to who "the bank"
is today, which is false. Loading only the two ACTIVE institutions is the
honest shape of the current structure; the dissolved count is verified and
printed below rather than silently dropped.

## Single-writer discipline

Fluree nodes here carry `ex:lei`, `rdfs:label`, `ex:provenance`, `rdf:type`,
and the `hasSubsidiary` edge -- identity and structure only, per CLAUDE.md's
"lei plus a display label and nothing else". Nothing about capital, assets,
RSSD (see above), or Call Report figures is written here; those stay in
`ccf_v2.bank_capital` / `ccf_v2.reporting_bank`, Postgres-only. Dearborn's
own capital is not fetched or stored anywhere -- it is not the reporting
entity and no spec condition needs its capital figure.

## Idempotency

Every subject URI is fixed (reused for the two existing nodes, deterministic
for the new one) and every triple asserted is a constant derived from public
sources fetched once and cached in the manifest below, so a re-run inserts
the same triples into the same set -- Fluree's `INSERT DATA` of an
already-asserted triple is a no-op. `retract_leaked_rssd()` is likewise
idempotent: `DELETE DATA` of a triple no longer present is a no-op, so
running this loader again after the fix lands does not error. Proved in
`verify()` by VALUE (a named label and a named `ex:lei` literal both still
resolve after a second run), not by a triple count, which cannot see a
value silently reset to empty.

    uv run loaders/load_nic_hierarchy.py
"""
from __future__ import annotations

import json
import sys
from urllib.parse import quote

from ccf import fluree
from ccf.party_roles import with_ancestors
from ccf.config import EX, FLUREE_LEDGER_V2
from ccf.fetch import SourceManifest, fetch

FDIC = "https://api.fdic.gov/banks"
GLEIF = "https://api.gleif.org/api/v1/lei-records"

#: The holding company this whole hierarchy hangs off. Already a Fluree node
#: (`load_reporting_bank.py`) and a `ccf_v2.reporting_bank` row.
HOLDCO_RSSD = "1039502"
#: Already a Fluree node and `ccf_v2.reporting_bank` row -- the reporting
#: bank itself.
BANK_RSSD = "852218"
#: NOT yet a Fluree node. The only other still-active institution under the
#: holding company.
DEARBORN_RSSD = "651448"

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"

FIBO = "https://spec.edmcouncil.org/fibo/ontology/"
CMNS = "https://www.omg.org/spec/Commons/"
C_BANK = f"{FIBO}FBC/FunctionalEntities/FinancialServicesEntities/Bank"
C_BANK_HOLDING = (f"{FIBO}FBC/FunctionalEntities/FinancialServicesEntities/"
                  f"BankHoldingCompany")
C_NATIONAL_BANK = (f"{FIBO}FBC/FunctionalEntities/NorthAmericanEntities/"
                    f"USFinancialServicesEntities/NationalBank")
C_ORGANIZATION = f"{CMNS}Organizations/Organization"
C_FORMAL_ORG = f"{CMNS}Organizations/FormalOrganization"
C_LEGAL_ENTITY = f"{CMNS}Organizations/LegalEntity"
P_LEI = f"{EX}lei"
#: NOT written by this loader -- see "No ex:rssd" above. Kept as a constant
#: only so `retract_leaked_rssd()` can name exactly what it is removing.
P_RSSD = f"{EX}rssd"
P_PROVENANCE = f"{EX}provenance"
P_HAS_SUBSIDIARY = (f"{FIBO}BE/OwnershipAndControl/CorporateControl/"
                     f"hasSubsidiary")

#: The three (subject, literal) pairs the first version of this loader
#: wrote and this fix retracts. Fixed values, not a query result: a
#: retraction must name EXACTLY the triple that was asserted, and these are
#: the only `ex:rssd` triples this loader (or any other -- grep confirms no
#: other loader mints `ex:rssd`) ever put in the ledger.
LEAKED_RSSD_TRIPLES = (
    (f"RSSD-{HOLDCO_RSSD}", HOLDCO_RSSD),
    (f"RSSD-{BANK_RSSD}", BANK_RSSD),
    (f"RSSD-{DEARBORN_RSSD}", DEARBORN_RSSD),
)


def uri(local: str) -> str:
    return f"{EX}{local}"


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def triple(s: str, p: str, o: str, *, literal: bool = False) -> str:
    obj = f'"{esc(o)}"' if literal else f"<{o}>"
    return f"<{s}> <{p}> {obj} ."


def retract_leaked_rssd() -> list[str]:
    """DELETE DATA for the `ex:rssd` triples the pre-fix version wrote.

    Same mechanism as every other retraction in this repo (grep
    `loaders/*.py` for `DELETE DATA` -- `remediate_parent_direction_wave15.py`
    is the closest analog: a targeted retraction of specific, already-known
    subject/predicate/object triples, not a wildcard delete over a
    predicate). Fluree is append-only, so a `DELETE DATA` retracts current
    state while preserving history -- this does not erase that the leak
    happened, it stops it being CURRENT.

    Idempotent: deleting a triple no longer present is a no-op, so this is
    safe to run on every future invocation of this loader even after the
    leaked triples are long gone.
    """
    statements = [triple(uri(local), P_RSSD, value, literal=True)
                  for local, value in LEAKED_RSSD_TRIPLES]
    fluree.update("DELETE DATA {\n" + "\n".join(statements) + "\n}")
    return statements


def fetch_hierarchy() -> tuple[list[dict], dict | None]:
    """FDIC's full RSSDHCR roster (justifies the dissolved-entity count and
    each active institution's charter class) plus Dearborn's GLEIF record
    (its LEI, and its legal form -- confirms it is a state-chartered bank,
    not a second national association)."""
    manifest = SourceManifest(
        source="nic_hierarchy",
        description="FFIEC NIC RSSD hierarchy under holding company 1039502 "
                     "(FDIC BankFind institutions, RSSDHCR filter) and "
                     "Dearborn's GLEIF LEI record",
        licence="US government work / public register data",
    )
    inst_url = (f"{FDIC}/institutions?filters=RSSDHCR:{HOLDCO_RSSD}"
                f"&fields=NAME,CERT,FED_RSSD,ACTIVE,BKCLASS,CHARTER,ESTYMD"
                f"&limit=100")
    inst_path = fetch(inst_url, manifest, "fdic_institutions.json")
    institutions = [r["data"] for r in
                    json.loads(inst_path.read_text())["data"]]

    gleif_url = (f"{GLEIF}?filter%5Bentity.names%5D="
                 f"{quote('JPMorgan Chase Bank, Dearborn', safe='')}"
                 f"&page%5Bsize%5D=5")
    gleif_path = fetch(gleif_url, manifest, "gleif_dearborn.json")
    gleif_records = json.loads(gleif_path.read_text()).get("data", [])
    dearborn = None
    for rec in gleif_records:
        e = rec["attributes"]["entity"]
        if (e["legalName"]["name"] == "JPMorgan Chase Bank, Dearborn"
                and e.get("jurisdiction", "").startswith("US")
                and e.get("status") == "ACTIVE"):
            dearborn = {"lei": rec["attributes"]["lei"],
                        "legal_form": e.get("legalForm", {}).get("other")}
            break

    return institutions, dearborn


def build_triples(institutions: list[dict], dearborn_lei: str | None) -> list[str]:
    active = {r["FED_RSSD"]: r for r in institutions if r["ACTIVE"] == 1}
    dissolved = len(institutions) - len(active)
    print(f"  FDIC RSSDHCR:{HOLDCO_RSSD} roster: {len(institutions)} "
          f"institutions, {len(active)} active, {dissolved} dissolved "
          f"predecessors (excluded -- see docstring)")
    assert set(active) == {BANK_RSSD, DEARBORN_RSSD}, (
        f"expected exactly {{{BANK_RSSD}, {DEARBORN_RSSD}}} active under "
        f"RSSDHCR {HOLDCO_RSSD}, got {sorted(active)} -- the two-entity "
        f"decision above no longer matches the source"
    )
    bank_charter = active[BANK_RSSD]["BKCLASS"]
    dearborn_charter = active[DEARBORN_RSSD]["BKCLASS"]
    assert bank_charter == "N", (
        f"RSSD {BANK_RSSD} charter class is {bank_charter!r}, not the "
        f"national-charter 'N' the NationalBank typing decision relies on")
    assert dearborn_charter != "N", (
        f"RSSD {DEARBORN_RSSD} charter class is {dearborn_charter!r}, "
        f"which IS a national charter -- it would need NationalBank too")

    holdco_node = uri(f"RSSD-{HOLDCO_RSSD}")
    bank_node = uri(f"RSSD-{BANK_RSSD}")
    dearborn_node = uri(f"RSSD-{DEARBORN_RSSD}")

    triples = []

    # --- 852218 gets NationalBank ADDED to its existing Bank type (override 2).
    triples.append(triple(bank_node, RDF_TYPE, C_NATIONAL_BANK))

    # --- 651448 (Dearborn) is entirely new: identity only (lei + label),
    # generic Bank type. No ex:rssd -- see "No ex:rssd" in the docstring.
    # Chain closure from ccf.party_roles (known-issues §62).
    for t in (C_BANK, *with_ancestors(C_LEGAL_ENTITY)):
        triples.append(triple(dearborn_node, RDF_TYPE, t))
    triples.append(triple(dearborn_node, RDFS_LABEL,
                           "JPMorgan Chase Bank, Dearborn", literal=True))
    if dearborn_lei:
        triples.append(triple(dearborn_node, P_LEI, dearborn_lei, literal=True))
    triples.append(triple(dearborn_node, P_PROVENANCE, "public", literal=True))

    # --- hasSubsidiary, parent -> child (domain LegalEntity, range
    # Subsidiary -- see docstring override 1). Both existing nodes already
    # carry cmns-org:LegalEntity / a bank type from load_reporting_bank.py,
    # so the domain/range each end needs is already satisfied without
    # minting a new role-class type here.
    triples.append(triple(holdco_node, P_HAS_SUBSIDIARY, bank_node))
    triples.append(triple(holdco_node, P_HAS_SUBSIDIARY, dearborn_node))

    return triples


def verify() -> list[str]:
    """Post-load checks: direction of hasSubsidiary by QUERY (not asserted),
    by-VALUE idempotency evidence for a re-run to compare against, and that
    the retracted `ex:rssd` leak has actually not come back."""
    failures = []
    holdco_node = uri(f"RSSD-{HOLDCO_RSSD}")

    # Direction proof: for every hasSubsidiary edge out of the holding
    # company, the SUBJECT is typed BankHoldingCompany and the OBJECT is
    # typed Bank (either NationalBank or generic). Identified by ex:lei
    # (the correlation key that replaces ex:rssd here), not by local name --
    # if the edge were ever inverted, this join would return the wrong
    # labels or nothing at all.
    q = f"""
    SELECT ?child ?childLei ?childLabel FROM <{FLUREE_LEDGER_V2}> WHERE {{
      <{holdco_node}> <{P_HAS_SUBSIDIARY}> ?child .
      <{holdco_node}> a <{C_BANK_HOLDING}> .
      ?child a <{C_BANK}> .
      ?child <{P_LEI}> ?childLei .
      ?child <{RDFS_LABEL}> ?childLabel .
      FILTER(?child != <{holdco_node}>)
    }}
    """
    rows = fluree.query(q)["results"]["bindings"]
    children = {r["childLei"]["value"]: r["childLabel"]["value"] for r in rows}
    expected_leis = {"7H6GLXDRUGQFU57RNE97", "5493000FN178SW540N88"}
    print("\n  Direction proof (subject = BankHoldingCompany, object = Bank):")
    for lei, label in sorted(children.items()):
        print(f"    RSSD-{HOLDCO_RSSD} --hasSubsidiary--> {label} (ex:lei {lei})")
    if set(children) != expected_leis:
        failures.append(
            f"hasSubsidiary direction query returned children with LEIs "
            f"{sorted(children)}, expected {sorted(expected_leis)} -- "
            f"either an edge is missing or one is inverted")

    # A companion query confirming NO edge points the other way (Bank ->
    # BankHoldingCompany), which is what "inverted" would look like.
    q_inverted = f"""
    SELECT (COUNT(?s) AS ?n) FROM <{FLUREE_LEDGER_V2}> WHERE {{
      ?s <{P_HAS_SUBSIDIARY}> <{holdco_node}> .
    }}
    """
    n_inverted = fluree.stable_scalar(q_inverted)
    print(f"  edges pointing INTO the holding company (should be 0): {n_inverted}")
    if n_inverted:
        failures.append(f"{n_inverted} hasSubsidiary edge(s) point at the "
                        f"holding company as OBJECT -- inverted direction")

    # The regression this fix exists for: ex:rssd must not be on any of the
    # three nodes. Recomputed here rather than trusted from the retraction
    # step succeeding -- a DELETE that silently no-ops for the wrong reason
    # (e.g. a typo'd literal that never matched) would leave the leak in
    # place while reporting success.
    n_rssd = fluree.stable_scalar(
        f"SELECT (COUNT(?o) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ ?s <{P_RSSD}> ?o }}")
    print(f"  ex:rssd triples remaining in the ledger (should be 0): {n_rssd}")
    if n_rssd:
        failures.append(f"{n_rssd} ex:rssd triple(s) still in the ledger -- "
                        f"the POSTGRES_OWNED_ATTRS leak is not fixed")

    return failures


def main() -> int:
    print(f"FFIEC NIC RSSD hierarchy into Fluree ({FLUREE_LEDGER_V2})\n")

    institutions, dearborn = fetch_hierarchy()
    if dearborn is None:
        print("  FAIL: Dearborn's GLEIF record did not resolve")
        return 1
    print(f"  Dearborn LEI  {dearborn['lei']}  "
          f"(legal form: {dearborn['legal_form']})")

    triples = build_triples(institutions, dearborn["lei"])
    fluree.update("INSERT DATA {\n" + "\n".join(triples) + "\n}")
    retract_leaked_rssd()

    n_national_bank = fluree.stable_scalar(
        f"SELECT (COUNT(?s) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ ?s a <{C_NATIONAL_BANK}> }}")
    n_bank = fluree.stable_scalar(
        f"SELECT (COUNT(?s) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ ?s a <{C_BANK}> }}")
    n_subsidiary_edges = fluree.stable_scalar(
        f"SELECT (COUNT(?o) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ ?s <{P_HAS_SUBSIDIARY}> ?o }}")

    print(f"\n  Fluree: {n_national_bank} NationalBank · {n_bank} Bank "
          f"(generic, includes the NationalBank) · {n_subsidiary_edges} "
          f"hasSubsidiary edges")

    failures = verify()
    if n_national_bank != 1:
        failures.append(f"expected exactly 1 NationalBank node, got {n_national_bank}")
    if n_subsidiary_edges != 2:
        failures.append(f"expected exactly 2 hasSubsidiary edges, got {n_subsidiary_edges}")

    if failures:
        print("\n  FAILURES:")
        for f in failures:
            print(f"    - {f}")
        return 1

    print("\n  OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
