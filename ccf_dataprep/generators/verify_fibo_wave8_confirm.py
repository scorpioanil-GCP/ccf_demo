#!/usr/bin/env python3
"""Wave 8 — confirm the exact terms proposed for the binding table.

`verify_fibo_wave8.py` casts a wide net over candidate modules to *discover*
terms. This script does the opposite: it takes the concrete list chosen for the
binding table and confirms each one against **published Production**, reporting
`ok` / `MISSING` per term. Only `ok` terms may enter `docs/ccf_dataprep_v2.md`.

Why both. The discovery pass fetches by guessed module path, so a wrong guess
looks identical to a missing term -- which is how `Tranche` was very nearly
recorded as "absent from FIBO" when it lives in `SEC/Debt/PoolBackedSecurities`.
An exhaustive grep over a clone found it; this pass proves the corrected path
resolves against the live endpoint the SDK will actually query.

It also re-checks the two **v1 starter properties** that this wave found do not
exist anywhere in FIBO, so the defect stays visible in CI-style output rather
than only in prose.

Run: uv run generators/verify_fibo_wave8_confirm.py
"""

from __future__ import annotations

import json

import requests
from rdflib import OWL, RDF, RDFS, Graph, URIRef

from ccf.config import REPO_ROOT

BASE = "https://spec.edmcouncil.org/fibo/ontology/"

#: module path -> local names expected in it, grouped by the need it serves.
PROPOSED: dict[str, dict[str, list[str]]] = {
    "OWNERSHIP / CONTROL (corrects the v1 starter defect)": {
        "FND/OwnershipAndControl/Ownership": [
            "Ownership", "owns", "isOwnedBy", "hasOwningParty", "hasOwnedAsset",
        ],
        "FND/OwnershipAndControl/Control": [
            "hasControllingParty", "isControllingPartyOf", "isControlledPartyOf",
        ],
        # controls / isControlledBy are DECLARED in FND/Relations/Relations and
        # merely *refined* (domain Party) by FND/OwnershipAndControl/Control.
        # Binding them under the Control namespace yields a 404 IRI -- the same
        # module-membership trap that produced the v1 defect this wave corrects.
        "FND/Relations/Relations": ["controls", "isControlledBy"],
        "BE/OwnershipAndControl/OwnershipParties": [
            "EntityOwnership", "hasOwningEntity", "hasOwnedEntity",
            "hasDirectOwnership", "hasInvestmentOwnership",
        ],
        "BE/OwnershipAndControl/CorporateControl": [
            "hasSubsidiary", "isSubsidiaryOf", "isParentCompanyOf",
            "hasGlobalUltimateParent", "hasDomesticUltimateParent",
            "isWhollyOwnedBy", "hasControllingAffiliate", "ControlledAffiliate",
        ],
    },
    "BENEFICIAL OWNERSHIP (kyc-refresh-beneficial-ownership)": {
        "BE/OwnershipAndControl/CorporateOwnership": [
            "BeneficialOwner", "BeneficialOwnership",
            "hasBeneficialOwner", "isBeneficialOwnerOf",
        ],
        "BE/OwnershipAndControl/CorporateControl": [
            "SignificantShareholder", "VotingShareholder",
        ],
    },
    "PERSON (kyc-refresh-beneficial-ownership)": {
        "FND/AgentsAndPeople/People": ["Person", "PersonName", "hasPersonName"],
        "BE/LegalEntities/LegalPersons": [
            "LegallyCompetentNaturalPerson", "SpecialPurposeVehicle",
        ],
    },
    "OFFICER / DIRECTOR / EMPLOYMENT (client-360-coverage-graph)": {
        "BE/OwnershipAndControl/Executives": [
            "CorporateOfficer", "ChiefExecutiveOfficer", "ChiefFinancialOfficer",
            "BoardOfDirectors", "hasCorporateOfficer", "isOfficerOf",
            "hasDirector", "isDirectorOf",
        ],
        "FND/Organizations/FormalOrganizations": [
            "Employee", "Employer", "Employment", "isEmployedBy", "employs",
        ],
    },
    "DEPOSIT ACCOUNTS (collateral-and-setoff, treasury-liquidity)": {
        "FBC/ProductsAndServices/ClientsAndAccounts": [
            "Account", "DepositAccount", "DemandDepositAccount",
            "TimeDepositAccount", "InvestmentAccount", "CertificateOfDeposit",
            "AccountHolder", "hasPrimaryAccountHolder",
        ],
    },
    "DEBT INSTRUMENTS / BONDS (rating-and-spread-migration)": {
        "FBC/FinancialInstruments/FinancialInstruments": [
            "DebtInstrument", "DerivativeInstrument", "Option", "Future",
            "SpotContract",
        ],
        "SEC/Debt/DebtInstruments": [
            "TradableDebtInstrument", "isSubordinated", "isSubordinatedTo",
        ],
        "SEC/Debt/Bonds": [
            "Bond", "CorporateBond", "FixedCouponBond", "VariableCouponBond",
            "ZeroCouponBond", "CallableBond", "ConvertibleBond",
            "FloatingRateNote", "TreasuryBond", "BondCoupon",
        ],
    },
    "RATES / FX REFERENCE (treasury-liquidity, fx-post-trade)": {
        "IND/InterestRates/InterestRates": [
            "InterestRateBenchmark", "ReferenceInterestRate",
            "InterestRateAuthority", "SpecificProviderInterestRateBenchmark",
        ],
        "IND/ForeignExchange/ForeignExchange": [
            "CurrencySpotRate", "CurrencyForwardRate", "QuotedExchangeRate",
            "ExchangeRateStructure", "hasQuotedExchangeRate",
        ],
    },
    "DERIVATIVES / SWAPS (fx-post-trade-reconciliation)": {
        "DER/DerivativesContracts/Swaps": [
            "Swap", "SwapLeg", "SwapParty", "SwapTerms", "SwapConfirmation",
            "UniqueSwapIdentifier", "SwapLifecycleEvent", "hasSwapIdentifier",
        ],
        "DER/RateDerivatives/RateDerivatives": [
            "ForwardRateAgreement", "InterestRateDerivativeInstrument",
            "ForeignExchangeRateObservable",
        ],
    },
    "TRADE / SETTLEMENT (fx-post-trade-reconciliation)": {
        "FBC/ProductsAndServices/FinancialProductsAndServices": [
            "Trade", "TradeIdentifier", "TradeLifecycle", "TradeLifecycleEvent",
            "TradeLifecycleStage", "SettlementTerms", "hasSettlementDate",
        ],
    },
    "SECURITIZATION / TRANCHE (abs-securitization-surveillance)": {
        "SEC/Debt/PoolBackedSecurities": [
            "Tranche", "AssetBackedSecurity", "PoolBackedSecurity",
            "StructuredFinanceInstrument", "AttachmentPoint", "DetachmentPoint",
            "DefaultRate", "PrepaymentSpeed", "WeightedAverageCoupon",
            "WeightedAverageLife", "WeightedAverageMaturity",
            "DebtPoolStatisticalMeasure", "hasAttachmentPoint",
            "hasDetachmentPoint",
        ],
        "SEC/Debt/CollateralizedDebtObligations": [
            "CollateralizedDebtObligation", "TriggerEvent", "TrancheType",
            "SeniorCDOTranche", "MezzanineCDOTranche", "SubordinatedMBSTranche",
            "specifiesTrigger", "hasTrancheType",
        ],
        "SEC/Debt/MortgageBackedSecurities": ["MortgageBackedSecurity"],
    },
    # Wave 15. Added here rather than only to the binding table because
    # `validators/binding_drift.py` draws its CLAIM_MISSING universe from this
    # script's output: a FIBO term bound after Wave 8 and never proposed here
    # is invisible to the mirror-drift sweep, however loaded it is. Both
    # individuals were on the vault's do-not-bind list until 2026-08-24,
    # recorded as "referenced but not declared" -- they are declared, as
    # owl:NamedIndividual, which the old type-filtered scan could not see.
    "LIEN POSITION (collateral-and-setoff-coverage)": {
        "LOAN/LoansGeneral/Loans": [
            "LenderLienPosition", "PrimaryLienPosition", "SubordinateLienPosition",
        ],
    },
}

#: Terms recorded in the v1 starter binding table that this wave found do not
#: exist. Re-checked here so the defect is machine-visible, not only narrative.
#: (v1 IRI tail, module that would declare the term today if it existed).
#:
#: The second element matters. Until 2026-08-23 this was a bare list and the
#: check reported CONFIRMED ABSENT for both -- without ever looking, because
#: the cache line it used discarded the fetched graph. When that was fixed the
#: modules turned out to 404: `BE/OwnershipAndControl` is not a FIBO path at
#: all. So a module-level 404 is conclusive for the v1 IRI (it cannot resolve
#: to anything) but says nothing about whether the NAME was simply relocated,
#: which is the failure that would matter. Hence the cross-check module: the
#: real ownership/control home is under FND. Measured 2026-08-23 -- neither
#: name is declared there either, so the v1 conclusion stands on evidence now
#: rather than on a check that could not fail.
KNOWN_BAD = [
    ("BE/OwnershipAndControl/Ownership/hasOwnershipInterestIn",
     "FND/OwnershipAndControl/Ownership"),
    ("BE/OwnershipAndControl/Control/hasControllingInterestIn",
     "FND/OwnershipAndControl/Control"),
]

#: Checked during this wave and NOT found, so deliberately absent from PROPOSED.
#: Recorded rather than dropped silently -- a later wave should not re-litigate
#: them without re-running the check.
REJECTED = {
    "BE/OwnershipAndControl/LegalPersons/LegalPerson":
        "no such class; the module declares CharteredLegalPerson and "
        "LegallyCompetentNaturalPerson but no bare LegalPerson",
    "IND/InterestRates/InterestRates/FloatingInterestRate":
        "not in IND/InterestRates; use ReferenceInterestRate or "
        "SEC/Debt/Bonds/FloatingRateNote depending on what is meant",
}


def fetch(module: str) -> Graph | None:
    try:
        resp = requests.get(
            f"{BASE}{module}.rdf",
            headers={"Accept": "application/rdf+xml"},
            timeout=45,
        )
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        print(f"  [MODULE FAIL] {module}: {type(exc).__name__} {str(exc)[:50]}")
        return None
    graph = Graph()
    try:
        graph.parse(data=resp.content, format="xml")
    except Exception as exc:  # noqa: BLE001
        print(f"  [PARSE FAIL] {module}: {str(exc)[:60]}")
        return None
    return graph


def scan(
    graph: Graph, kinds: dict[str, str], labels: dict[str, str]
) -> set[str]:
    """Every term the module DECLARES, without filtering by element type.

    The rdflib analogue of the custodian's grep test: a term is declared iff it
    is the subject of at least one triple here, which is what `rdf:about=` on a
    node element produces. Referenced-but-not-declared terms appear only as
    `rdf:resource` objects and so are correctly excluded.

    This deliberately does NOT enumerate by `owl:Class` / `owl:ObjectProperty`
    / `owl:DatatypeProperty`, which is what it used to do. FIBO models
    enumerations as a classifier class plus `owl:NamedIndividual` values --
    `LenderLienPosition` is the class, `PrimaryLienPosition` and
    `SubordinateLienPosition` are its two individuals. A type-filtered scan
    reports MISSING for every individual in FIBO: measured 2026-08-23 against
    `LOAN/LoansGeneral/Loans`, the old filter found `LenderLienPosition` and
    reported both individuals absent, though all three are declared. That
    manufactures absences at the same rate the HTTP-200 method manufactured
    presences, in the opposite direction.

    `kinds` therefore records the types actually observed rather than the one
    bucket the term was found in, so an unexpected kind is visible in the
    report instead of being silently normalised away.
    """
    subjects: set[str] = set()
    for subj in set(graph.subjects(None, None)):
        if not isinstance(subj, URIRef):
            continue
        iri = str(subj)
        subjects.add(iri)
        observed = sorted(
            str(o).rsplit("#", 1)[-1].rsplit("/", 1)[-1]
            for o in graph.objects(subj, RDF.type)
        )
        # NamedIndividual rides alongside the classifier type and says nothing
        # on its own; keep both so the report shows what the term really is.
        if observed:
            kinds[iri] = "+".join(observed)
        lab = next((str(o) for o in graph.objects(subj, RDFS.label)), "")
        if lab:
            labels[iri] = lab
    return subjects


def main() -> int:
    print("Wave 8 — confirming proposed bindings against published Production\n")

    confirmed: list[dict] = []
    missing: list[dict] = []
    module_cache: dict[str, set[str]] = {}
    kinds: dict[str, str] = {}
    labels: dict[str, str] = {}

    for need, modules in PROPOSED.items():
        print(f"  === {need} ===")
        for module, names in modules.items():
            if module not in module_cache:
                graph = fetch(module)
                if graph is None:
                    module_cache[module] = set()
                else:
                    module_cache[module] = scan(graph, kinds, labels)
            present = module_cache[module]

            for name in names:
                iri = f"{BASE}{module}/{name}"
                record = {
                    "local_name": name,
                    "module": module,
                    "iri": iri,
                    "kind": kinds.get(iri, ""),
                    "label": labels.get(iri, ""),
                    "need": need,
                }
                if iri in present:
                    confirmed.append(record)
                    print(f"      ok      {name:<42} {kinds.get(iri, '')}")
                else:
                    missing.append(record)
                    print(f"      MISSING {name:<42} {module}")
        print()

    print("  === v1 STARTER TABLE — terms this wave found do not exist ===")
    for tail, elsewhere in KNOWN_BAD:
        module, name = tail.rsplit("/", 1)
        iri = f"{BASE}{tail}"

        if module not in module_cache:
            graph = fetch(module)
            module_cache[module] = (
                scan(graph, kinds, labels) if graph is not None else None
            )
        here = module_cache[module]

        # Cross-check: absent from its own module is only half the claim if the
        # term was relocated. Look where it would live today.
        if elsewhere not in module_cache:
            graph = fetch(elsewhere)
            module_cache[elsewhere] = (
                scan(graph, kinds, labels) if graph is not None else None
            )
        there = module_cache[elsewhere]

        if there is None:
            # Cannot distinguish "not there" from "could not look" -- the
            # `Tranche` trap. Refuse to conclude.
            status = "UNVERIFIED"
            note = f"cross-check module {elsewhere} unreachable"
        elif any(s.rsplit("/", 1)[-1] == name for s in there):
            status = "RELOCATED?!"
            note = f"declared in {elsewhere}"
        elif here is None:
            # The v1 IRI's own module does not resolve, so the IRI cannot name
            # anything -- conclusive for the IRI, and the name is not in its
            # modern home either.
            status = "CONFIRMED ABSENT"
            note = f"module 404; name also absent from {elsewhere}"
        elif iri in here:
            status = "STILL PRESENT?!"
            note = "declared in its own module"
        else:
            status = "CONFIRMED ABSENT"
            note = f"absent from own module and from {elsewhere}"
        print(f"      {status:<17} {tail}  [{note}]")
    print()

    out = REPO_ROOT / "sources" / "screening" / "fibo_wave8_confirmed.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "source": f"{BASE} (Production)",
                "wave": 8,
                "confirmed": confirmed,
                "missing": missing,
                "rejected": REJECTED,
                "v1_starter_absent": KNOWN_BAD,
            },
            indent=2,
        )
        + "\n"
    )

    print(f"  {len(confirmed)} confirmed · {len(missing)} missing")
    print(f"  written: {out.relative_to(REPO_ROOT)}\n")
    if missing:
        print("  Terms reported MISSING must NOT enter the binding table.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
