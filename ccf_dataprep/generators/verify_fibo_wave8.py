#!/usr/bin/env python3
"""Wave 8 — verify the FIBO modules the remaining 14 specs need.

Wave 0 bound Loans, Guaranty, Syndication, Collateral, and Credit Events. Reading
the other 14 specs (see docs/spec-digest.md §3) surfaced seven further vocabulary
areas that are named by module and therefore not yet pinned to an IRI:

    securitization / tranche / trigger     abs-securitization-surveillance
    derivatives + FX instruments           fx-post-trade-reconciliation
    debt instruments / bonds               rating-and-spread-migration
    rates and indices                      treasury-liquidity-position
    natural person / beneficial owner      kyc-refresh-beneficial-ownership
    officer / director / employment        client-360-coverage-graph
    deposit account                        collateral-and-setoff-coverage, treasury

CLAUDE.md: "module membership does not pin an IRI." The Wave 0 pass proved that
concretely — three terms lived somewhere other than where the specs implied, and
`Covenant` turned out not to exist in FIBO at all. So this fetches the published
Production RDF, parses it, and reports the *actual* IRI and parent class for each
candidate term.

Module paths below are candidates, not assertions. A path that does not exist
prints [skip] and costs nothing; that is cheaper than guessing which are real.

Output: sources/screening/fibo_candidates_wave8.json + a printed report grouped
by the spec need each term serves.

Nothing is written to the binding table by this script — that edit is deliberate
and manual, per the extension protocol in CLAUDE.md.

Run: uv run generators/verify_fibo_wave8.py
"""

from __future__ import annotations

import json
from collections import defaultdict

import requests
from rdflib import OWL, RDF, RDFS, Graph, URIRef

from ccf.config import REPO_ROOT

BASE = "https://spec.edmcouncil.org/fibo/ontology/"

#: Candidate modules for the seven areas above. Wide net on purpose: a wrong path
#: is a [skip] line, a missing path is a term bound to nothing downstream.
MODULES = [
    # --- securitization / structured finance -------------------------------
    "SEC/Debt/AssetBackedSecurities",
    "SEC/Debt/StructuredFinance",
    "SEC/Debt/Securitization",
    "SEC/Securitization/Securitization",
    "SEC/Debt/DebtInstruments",
    "SEC/Debt/Bonds",
    "SEC/Debt/PoolsFundsAndREITs",
    # --- derivatives + FX ---------------------------------------------------
    "DER/DerivativesContracts/ContractualProducts",
    "DER/DerivativesContracts/Options",
    "DER/DerivativesContracts/Forwards",
    "DER/DerivativesContracts/Swaps",
    "DER/DerivativesContracts/Futures",
    "DER/RateDerivatives/RateDerivatives",
    "DER/CreditDerivatives/CreditDefaultSwaps",
    "DER/ForeignExchangeDerivatives/ForeignExchangeDerivatives",
    # --- rates, indices, FX reference ---------------------------------------
    "IND/InterestRates/InterestRates",
    "IND/ForeignExchange/ForeignExchange",
    "IND/MarketIndices/MarketIndices",
    "IND/Indicators/BusinessIndicators",
    "FBC/FinancialInstruments/FinancialInstruments",
    # --- accounts / deposits -------------------------------------------------
    "FBC/ProductsAndServices/ClientsAndAccounts",
    "FBC/ProductsAndServices/FinancialProductsAndServices",
    # --- people, ownership, control, roles -----------------------------------
    "FND/AgentsAndPeople/People",
    "FND/AgentsAndPeople/Agents",
    "FND/Parties/Parties",
    "FND/Parties/Roles",
    "FND/Organizations/FormalOrganizations",
    "FND/Law/LegalCapacity",
    "BE/LegalEntities/LegalPersons",
    "BE/LegalEntities/FormalBusinessOrganizations",
    "BE/Corporations/Corporations",
    "BE/OwnershipAndControl/Ownership",
    "BE/OwnershipAndControl/Control",
    "BE/OwnershipAndControl/ControlParties",
    "BE/OwnershipAndControl/CorporateControl",
    "BE/GovernmentEntities/GovernmentEntities",
]

#: Case-insensitive substrings marking a term as relevant to the seven areas.
WANTED = [
    # securitization
    "securiti", "tranche", "trigger", "assetbacked", "asset-backed", "poolof",
    "specialpurpose", "spv", "subordinat", "waterfall", "creditenhancement",
    # derivatives / FX
    "derivative", "swap", "forward", "future", "option", "notional",
    "foreignexchange", "currencypair", "exchangerate", "spot",
    # debt instruments
    "bond", "debtinstrument", "note", "coupon", "coupon", "coupo",
    # rates / indices
    "interestrate", "referencerate", "benchmark", "yieldcurve", "index",
    "indice", "floatingrate", "fixedrate",
    # accounts
    "depositaccount", "account", "deposit",
    # people / ownership / control / roles
    "naturalperson", "person", "beneficialowner", "beneficial", "owner",
    "control", "officer", "director", "employ", "role", "shareholder",
    "holdinginterest", "equityinterest",
    # trade / settlement (fx-post-trade)
    "trade", "settlement", "confirmation",
]

#: Report buckets — (label, matcher substrings), evaluated in order.
BUCKETS: list[tuple[str, tuple[str, ...]]] = [
    ("SECURITIZATION / TRANCHE", ("securiti", "tranche", "assetbacked",
                                  "asset-backed", "specialpurpose", "subordinat",
                                  "creditenhancement", "waterfall", "trigger")),
    ("DERIVATIVES / FX", ("derivative", "swap", "forward", "future", "option",
                          "notional", "foreignexchange", "currencypair",
                          "exchangerate", "spot")),
    ("DEBT INSTRUMENTS", ("bond", "debtinstrument", "coupon")),
    ("RATES / INDICES", ("interestrate", "referencerate", "benchmark",
                         "yieldcurve", "index", "indice", "floatingrate",
                         "fixedrate")),
    ("ACCOUNTS / DEPOSITS", ("depositaccount", "deposit", "account")),
    ("PERSON / BENEFICIAL OWNERSHIP", ("naturalperson", "person",
                                       "beneficialowner", "beneficial",
                                       "shareholder", "equityinterest",
                                       "holdinginterest", "owner")),
    ("OFFICER / DIRECTOR / ROLE", ("officer", "director", "employ", "role",
                                   "control")),
    ("TRADE / SETTLEMENT", ("trade", "settlement", "confirmation")),
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


def bucket_for(name: str) -> str | None:
    low = name.lower()
    for label, tokens in BUCKETS:
        if any(token in low for token in tokens):
            return label
    return None


def main() -> int:
    print("Wave 8 — fetching FIBO Production modules from spec.edmcouncil.org\n")

    classes: dict[str, dict] = {}
    properties: dict[str, dict] = {}
    fetched: list[str] = []

    for module in MODULES:
        graph = fetch_graph(module)
        if graph is None:
            continue
        fetched.append(module)

        for subj in graph.subjects(RDF.type, OWL.Class):
            if not isinstance(subj, URIRef):
                continue
            name = local_name(str(subj))
            if not interesting(name):
                continue
            classes[str(subj)] = {
                "iri": str(subj),
                "local_name": name,
                "label": next(
                    (str(o) for o in graph.objects(subj, RDFS.label)), ""
                ),
                "module": module,
                "subclass_of": [
                    str(o) for o in graph.objects(subj, RDFS.subClassOf)
                    if isinstance(o, URIRef)
                ],
            }

        for prop_type in (OWL.ObjectProperty, OWL.DatatypeProperty):
            for subj in graph.subjects(RDF.type, prop_type):
                if not isinstance(subj, URIRef):
                    continue
                name = local_name(str(subj))
                if not interesting(name):
                    continue
                properties[str(subj)] = {
                    "iri": str(subj),
                    "local_name": name,
                    "label": next(
                        (str(o) for o in graph.objects(subj, RDFS.label)), ""
                    ),
                    "module": module,
                    "kind": "ObjectProperty"
                    if prop_type == OWL.ObjectProperty
                    else "DatatypeProperty",
                    "domain": [
                        str(o) for o in graph.objects(subj, RDFS.domain)
                        if isinstance(o, URIRef)
                    ],
                    "range": [
                        str(o) for o in graph.objects(subj, RDFS.range)
                        if isinstance(o, URIRef)
                    ],
                }

    print(
        f"\n  {len(fetched)}/{len(MODULES)} modules fetched · "
        f"{len(classes)} candidate classes · {len(properties)} candidate properties\n"
    )

    out = REPO_ROOT / "sources" / "screening" / "fibo_candidates_wave8.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "source": "https://spec.edmcouncil.org/fibo/ontology/ (Production)",
                "wave": 8,
                "modules_attempted": MODULES,
                "modules_fetched": fetched,
                "classes": sorted(classes.values(), key=lambda c: c["local_name"]),
                "properties": sorted(
                    properties.values(), key=lambda p: p["local_name"]
                ),
            },
            indent=2,
        )
        + "\n"
    )
    print(f"  written: {out.relative_to(REPO_ROOT)}\n")

    cls_buckets: dict[str, list[dict]] = defaultdict(list)
    prop_buckets: dict[str, list[dict]] = defaultdict(list)
    for entry in classes.values():
        label = bucket_for(entry["local_name"])
        if label:
            cls_buckets[label].append(entry)
    for entry in properties.values():
        label = bucket_for(entry["local_name"])
        if label:
            prop_buckets[label].append(entry)

    for label, _ in BUCKETS:
        cls_entries = sorted(cls_buckets.get(label, []), key=lambda e: e["local_name"])
        prop_entries = sorted(prop_buckets.get(label, []), key=lambda e: e["local_name"])
        print(f"  === {label} — {len(cls_entries)} classes, {len(prop_entries)} properties ===")
        if not cls_entries and not prop_entries:
            print("      (nothing found — candidate for an ex: extension)")
        for entry in cls_entries:
            print(f"      C  {entry['local_name']:<38} {entry['module']}")
        for entry in prop_entries:
            print(f"      P  {entry['local_name']:<38} {entry['module']}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
