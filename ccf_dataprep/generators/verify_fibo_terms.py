#!/usr/bin/env python3
"""Wave 0 — verify FIBO Loans-module IRIs against the EDM Council source.

CLAUDE.md: "module membership does not pin an IRI." Binding a term because a
module name looks right is how the two projects drift, and the resulting data
validates locally while being unconsumable downstream.

So this fetches the published Production ontology files, parses them, and
reports the *actual* IRI for each term the specs require — plus its parent
class, so the subclass chain can be recorded honestly.

Terms needed for Waves 4-5 (facility-terms-snapshot, covenant-in-force-as-of,
covenant-cross-reference):

    CreditFacility, Loan, LoanContract, Covenant, Guarantee, cross-default,
    syndicate participation, and the object properties joining them.

Output: sources/screening/fibo_candidates.json + a printed report.
Nothing is written to the binding table by this script — that edit is
deliberate and manual, per the extension protocol.

Run: uv run generators/verify_fibo_terms.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict

import requests
from rdflib import OWL, RDF, RDFS, Graph, URIRef

from ccf.config import REPO_ROOT

BASE = "https://spec.edmcouncil.org/fibo/ontology/"

#: Modules plausibly carrying the loan, facility, covenant, and guarantee
#: vocabulary. Fetched and indexed; membership is then *verified*, not assumed.
MODULES = [
    "LOAN/LoansGeneral/Loans",
    "LOAN/LoansGeneral/LoanRestructuring",
    "LOAN/SpecificLoans/CreditCardLoans",
    "LOAN/RealEstateLoans/RealEstateLoansGeneral",
    "FBC/ProductsAndServices/FinancialProductsAndServices",
    "FBC/ProductsAndServices/ClientsAndAccounts",
    "FBC/DebtAndEquities/Debt",
    "FBC/DebtAndEquities/CreditEvents",
    "FND/Agreements/Contracts",
    "FND/Agreements/Agreements",
    "SEC/Debt/DebtInstruments",
    "SEC/Securities/SecuritiesIssuance",
    "DER/DerivativesContracts/ContractualProducts",
]

#: Case-insensitive substrings that mark a term as interesting for these specs.
WANTED = [
    "facility", "covenant", "guarant", "crossdefault", "cross-default",
    "default", "syndicat", "loan", "creditagreement", "collateral",
    "lien", "setoff", "set-off", "netting", "tranche", "commitment",
    "amendment", "borrower", "lender", "principal", "maturity",
]


def fetch_graph(module: str) -> Graph | None:
    url = f"{BASE}{module}.rdf"
    try:
        resp = requests.get(
            url, headers={"Accept": "application/rdf+xml"}, timeout=45
        )
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        print(f"  [skip] {module}: {type(exc).__name__} {str(exc)[:50]}")
        return None
    graph = Graph()
    try:
        graph.parse(data=resp.content, format="xml")
    except Exception as exc:  # noqa: BLE001
        print(f"  [parse fail] {module}: {str(exc)[:60]}")
        return None
    print(f"  [ok]   {module}: {len(graph)} triples")
    return graph


def local_name(iri: str) -> str:
    for sep in ("#", "/"):
        if sep in iri:
            tail = iri.rsplit(sep, 1)[-1]
            if tail:
                return tail
    return iri


def interesting(name: str) -> bool:
    low = name.lower()
    return any(token in low for token in WANTED)


def main() -> int:
    print("Fetching FIBO Production modules from spec.edmcouncil.org\n")

    classes: dict[str, dict] = {}
    properties: dict[str, dict] = {}
    module_of: dict[str, str] = {}

    for module in MODULES:
        graph = fetch_graph(module)
        if graph is None:
            continue

        for subj in graph.subjects(RDF.type, OWL.Class):
            if not isinstance(subj, URIRef):
                continue
            name = local_name(str(subj))
            if not interesting(name):
                continue
            parents = [
                str(o) for o in graph.objects(subj, RDFS.subClassOf)
                if isinstance(o, URIRef)
            ]
            labels = [str(o) for o in graph.objects(subj, RDFS.label)]
            classes[str(subj)] = {
                "iri": str(subj),
                "local_name": name,
                "label": labels[0] if labels else "",
                "module": module,
                "subclass_of": parents,
            }
            module_of[str(subj)] = module

        for prop_type in (OWL.ObjectProperty, OWL.DatatypeProperty):
            for subj in graph.subjects(RDF.type, prop_type):
                if not isinstance(subj, URIRef):
                    continue
                name = local_name(str(subj))
                if not interesting(name):
                    continue
                labels = [str(o) for o in graph.objects(subj, RDFS.label)]
                domains = [
                    str(o) for o in graph.objects(subj, RDFS.domain)
                    if isinstance(o, URIRef)
                ]
                ranges = [
                    str(o) for o in graph.objects(subj, RDFS.range)
                    if isinstance(o, URIRef)
                ]
                properties[str(subj)] = {
                    "iri": str(subj),
                    "local_name": name,
                    "label": labels[0] if labels else "",
                    "module": module,
                    "kind": "ObjectProperty"
                    if prop_type == OWL.ObjectProperty
                    else "DatatypeProperty",
                    "domain": domains,
                    "range": ranges,
                }

    print(f"\n  {len(classes)} candidate classes, {len(properties)} candidate properties\n")

    out = REPO_ROOT / "sources" / "screening" / "fibo_candidates.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "source": "https://spec.edmcouncil.org/fibo/ontology/ (Production)",
                "modules_fetched": MODULES,
                "classes": sorted(classes.values(), key=lambda c: c["local_name"]),
                "properties": sorted(properties.values(), key=lambda p: p["local_name"]),
            },
            indent=2,
        )
        + "\n"
    )
    print(f"  written: {out.relative_to(REPO_ROOT)}\n")

    # Report grouped by the spec need they serve.
    buckets: dict[str, list[dict]] = defaultdict(list)
    for entry in classes.values():
        low = entry["local_name"].lower()
        if "facility" in low or "commitment" in low:
            buckets["FACILITY"].append(entry)
        elif "covenant" in low:
            buckets["COVENANT"].append(entry)
        elif "guarant" in low:
            buckets["GUARANTEE"].append(entry)
        elif "default" in low:
            buckets["DEFAULT / CROSS-DEFAULT"].append(entry)
        elif "syndicat" in low:
            buckets["SYNDICATE"].append(entry)
        elif "collateral" in low or "lien" in low or "netting" in low or "setoff" in low:
            buckets["COLLATERAL / SET-OFF"].append(entry)
        elif "loan" in low or "creditagreement" in low:
            buckets["LOAN"].append(entry)

    for bucket in ["FACILITY", "COVENANT", "GUARANTEE", "DEFAULT / CROSS-DEFAULT",
                   "SYNDICATE", "COLLATERAL / SET-OFF", "LOAN"]:
        entries = buckets.get(bucket, [])
        print(f"  === {bucket} ({len(entries)}) ===")
        if not entries:
            print("      NONE FOUND in fetched modules")
        for e in sorted(entries, key=lambda x: x["local_name"])[:12]:
            print(f"      {e['local_name']}")
            print(f"        {e['iri']}")
        print()

    print("  === OBJECT PROPERTIES (top 25) ===")
    objprops = [p for p in properties.values() if p["kind"] == "ObjectProperty"]
    for p in sorted(objprops, key=lambda x: x["local_name"])[:25]:
        print(f"      {p['local_name']}")
        print(f"        {p['iri']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
