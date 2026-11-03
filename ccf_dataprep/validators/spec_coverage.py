#!/usr/bin/env python3
"""The other half of the partition validator: each store holds what it OWNS.

`partition.py` opens by declaring its own goal as

    each store holds the slice it owns, AND NOTHING IT DOES NOT.

Only the second clause was ever built. Every check in that file runs in the
same direction -- it hunts for elements that leaked INTO a store, and it is
very good at that. Nothing anywhere asserted that an element the spec assigns
to a store is actually THERE. So an element in the wrong store is invisible to
it, and an element in NO store is equally invisible: both look like a clean
partition, because a missing thing cannot leak.

That is not hypothetical. `collateral-and-setoff-coverage` §C assigns

    | Lien priority and filing date | UCC-1 filing records | public | Fluree | R, T |

and lien priority has been sitting in `ccf_v2.collateral_pledge.priority` as
free text since Wave 9, with Fluree holding 95 unqualified collateral edges.
30/30 partition checks passed throughout, because nothing had leaked. Walking
the graph, a first lien and a second lien are indistinguishable -- which is
verbatim the counterfactual the product exists to refute:

    "A second-lien position recorded as 'secured' alongside a first-lien
     position recorded identically produces two facilities that look equally
     protected and are not."                       -- the spec's own §A

So this validator walks the §C Data Catalog of every registered product and
requires each row to be ACCOUNTED FOR. Four states, and a row must be in one:

    PROBE     a query against the named store that must return > 0
    COVERED   already asserted by a named check in conditions.py -- pointed at
              rather than duplicated, so the 148 existing gates stay the single
              writer for what they cover
    WAIVED    legitimately not loadable, with the reason recorded. A waiver is
              a claim about the SOURCE, never about our appetite for the work
    DEFERRED  a real gap, named, with the consequence spelled out. These FAIL

## Why unmapped products are loud rather than absent

The obvious way to build this is to add products to the manifest as they are
mapped. That would make the validator's own coverage the one thing it cannot
see -- 16 unmapped products would render as silence, and silence reads exactly
like success. It would be the same defect it exists to catch, one level up.

So `PRODUCTS` below lists every registered product, the manifest declares which
are mapped, and an unmapped product is reported with its row count and fails
the run. The number that matters is printed on the last line: rows accounted
for, out of rows in the catalog.

Exit code is non-zero while any row is DEFERRED, unmapped, or failing its
probe. This validator is expected to be RED until the catalog is complete.
That is the point of it; do not waive a row to clear it.

Run: uv run validators/spec_coverage.py
     uv run validators/spec_coverage.py --product collateral-and-setoff-coverage
"""

from __future__ import annotations

import argparse
import re
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ccf.config import EX, FLUREE_LEDGER_V2, PG_SCHEMA_V2, pg_connect

FIBO = "https://spec.edmcouncil.org/fibo/ontology/"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"

#: The vault's own copy of the specs. Read-only -- this repository never writes
#: into the vault; the exchange at ~/.agent-exchange/ is the only channel that
#: goes the other way. Read directly rather than over MCP because the §C tables
#: are the only part needed and the articles are large.
VAULT = Path("/home/parkave/obsidian-vault/wiki/context-products/content")

#: Every product registered in validators/conditions.py. Derived by hand rather
#: than by importing conditions.py, so that a product silently dropped from one
#: file does not silently vanish from the other too.
PRODUCTS = [
    "abs-securitization-surveillance",
    "aml-typology-match",
    "client-360-coverage-graph",
    "collateral-and-setoff-coverage",
    "corporate-family-tree",
    "counterparty-reference-snapshot",
    "covenant-cross-reference",
    "covenant-in-force-as-of",
    "credit-exposure-rollup",
    "credit-memo-context",
    "credit-surveillance-early-warning",
    "facility-terms-snapshot",
    "fx-post-trade-reconciliation",
    "ib-opportunity-synthesis",
    "kyc-refresh-beneficial-ownership",
    "large-exposure-rwa-concentration",
    "mnpi-wall-enforcement",
    "obligor-financial-spread",
    "rating-and-spread-migration",
    "syndicated-lending-co-lender",
    "treasury-liquidity-position",
]


# --------------------------------------------------------------------------
# reading the catalog
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class CatalogRow:
    """One row of a spec's §C Data Catalog, as the vault states it."""

    product: str
    element: str
    provenance: str
    provenance_class: str
    store: str
    g: str


def read_catalog(product: str) -> list[CatalogRow]:
    """Parse §C out of the spec. Fails loudly rather than returning [].

    An empty catalog would make a product trivially fully-covered, which is
    the failure mode this whole file exists to prevent, so a spec whose §C
    cannot be found raises instead.
    """
    path = VAULT / f"{product}.md"
    if not path.exists():
        raise RuntimeError(f"spec not found: {path}")
    md = path.read_text()
    m = re.search(r"^## C · Data Catalog\s*$(.*?)^## D ", md, re.S | re.M | re.I)
    if not m:
        raise RuntimeError(f"no §C Data Catalog section in {product}")

    rows: list[CatalogRow] = []
    lines = [
        line for line in m.group(1).splitlines()
        if line.startswith("|") and not re.match(r"^\|\s*-+", line)
    ]
    for line in lines[1:]:  # drop the header row
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        clean = lambda s: re.sub(r"\*\*|`|\[\[|\]\]", "", s).strip()  # noqa: E731
        rows.append(CatalogRow(
            product=product,
            element=clean(cells[0]),
            provenance=clean(cells[1]),
            provenance_class=clean(cells[2]),
            store=clean(cells[3]),
            g=clean(cells[4]),
        ))
    if not rows:
        raise RuntimeError(f"§C found but no rows parsed in {product}")
    return rows


# --------------------------------------------------------------------------
# probes
# --------------------------------------------------------------------------

def fluree_count(where: str) -> int:
    from ccf import fluree

    q = f"SELECT ?s ?x FROM <{FLUREE_LEDGER_V2}> WHERE {{ {where} }}"
    return len(fluree.query(q)["results"]["bindings"])


def fluree_predicate(iri: str) -> int:
    return fluree_count(f"?s <{iri}> ?x")


def fluree_instances(cls_iri: str) -> int:
    from ccf import fluree

    q = (f"SELECT ?s FROM <{FLUREE_LEDGER_V2}> "
         f"WHERE {{ ?s <{RDF_TYPE}> <{cls_iri}> }}")
    return len(fluree.query(q)["results"]["bindings"])


def fluree_declared(iri: str) -> int:
    """Declared as a schema node -- any triple with this IRI as subject."""
    from ccf import fluree

    q = f"SELECT ?p FROM <{FLUREE_LEDGER_V2}> WHERE {{ <{iri}> ?p ?o }}"
    return len(fluree.query(q)["results"]["bindings"])


def pg_count(sql: str) -> int:
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(sql.format(S=PG_SCHEMA_V2))
        row = cur.fetchone()
        return int(row[0]) if row else 0


# --------------------------------------------------------------------------
# manifest
# --------------------------------------------------------------------------

PROBE, COVERED, WAIVED, DEFERRED = "PROBE", "COVERED", "WAIVED", "DEFERRED"


@dataclass
class Mapping:
    """How one §C row is accounted for.

    `match` is a substring of the spec's element text. Substring rather than
    exact, because the vault patches §C prose in place and an exact match would
    turn a wording tweak upstream into a spurious failure here. It must still
    match exactly one row -- an ambiguous match is an error, not a warning,
    since a mapping silently covering the wrong row is the bug this validator
    is supposed to make impossible.
    """

    match: str
    state: str
    detail: str
    probe: Callable[[], int] | None = None

    #: A row that IS satisfied, but not on the spec's own terms. Set this
    #: whenever the estate delivered something narrower than, or substituted
    #: for, what §C asked -- and the narrowing was a ruling rather than a
    #: gap. It is rendered on its own lines under the row, in full, never
    #: folded into `detail`: `Outcome.render` truncates `detail` at 70
    #: characters, so a divergence recorded there is a divergence nobody
    #: reads. Recorded in a validator so it survives the SDD workspace,
    #: which is deleted at wave close.
    divergence: str | None = None


CONTRACTUAL_DEFINITION = f"{FIBO}FND/Agreements/Contracts/ContractualDefinition"


def dual_typed(ex_locals: tuple[str, ...]) -> int:
    """Nodes carrying the `ex:` role AND fibo ContractualDefinition, or 0.

    The vault corrected two specs on 2026-08-24 after this validator reported
    that their §C claimed "no FIBO term exists" for names that do. The
    correction is not just an IRI: it says assert `ContractualDefinition` AND
    the `ex:` role type TOGETHER, never one instead of the other, because FIBO
    models what a definition IS and the `ex:` type says which covenant it
    governs. Losing either half loses a different question.

    So this returns 0 the moment ANY node carries the `ex:` role without the
    FIBO class. A plain count of dual-typed nodes would sit at 206 of 207 and
    read as healthy.
    """
    from ccf import fluree

    total = 0
    for local in ex_locals:
        rows = fluree.query(
            f"SELECT ?s FROM <{FLUREE_LEDGER_V2}> WHERE {{ "
            f"?s <{RDF_TYPE}> <{EX}{local}> }} LIMIT 5000")["results"]["bindings"]
        both = fluree.query(
            f"SELECT ?s FROM <{FLUREE_LEDGER_V2}> WHERE {{ "
            f"?s <{RDF_TYPE}> <{EX}{local}> . "
            f"?s <{RDF_TYPE}> <{CONTRACTUAL_DEFINITION}> }} "
            f"LIMIT 5000")["results"]["bindings"]
        if len(rows) != len(both) or not rows:
            return 0
        total += len(rows)
    return total


COLLATERAL = [
    Mapping(
        "FIBO collateral, lien, and netting classes", PROBE,
        "Collateral / PhysicalCollateral / NonPhysicalCollateral declared as "
        "schema nodes in the ledger",
        lambda: min(
            fluree_declared(f"{FIBO}FBC/DebtAndEquities/Debt/Collateral"),
            fluree_declared(f"{FIBO}FBC/DebtAndEquities/Debt/PhysicalCollateral"),
            fluree_declared(f"{FIBO}FBC/DebtAndEquities/Debt/NonPhysicalCollateral"),
        ),
    ),
    Mapping(
        "FIBO deposit and investment account classes", PROBE,
        "DepositAccount and InvestmentAccount declared and populated",
        lambda: min(
            fluree_instances(
                f"{FIBO}FBC/ProductsAndServices/ClientsAndAccounts/DepositAccount"),
            fluree_instances(
                f"{FIBO}FBC/ProductsAndServices/ClientsAndAccounts/InvestmentAccount"),
        ),
    ),
    Mapping(
        "securedBy edges", PROBE,
        "facility -> asset, as fibo isCollateralizedBy",
        lambda: fluree_predicate(f"{FIBO}FBC/DebtAndEquities/Debt/isCollateralizedBy"),
    ),
    Mapping(
        "Lien filings", WAIVED,
        "UCC-1 filings are per-state, several charge, and coverage for this "
        "cast was never confirmed -- the spec's own §C flags this and names "
        "EX-10 collateral schedules as the fallback, which is what the "
        "securedBy row above is built from. A waiver about the SOURCE, not "
        "about the work: no secured-party / debtor / collateral-description "
        "triple is claimed anywhere in the estate.",
    ),
    # The vault SPLIT this row on 2026-08-24, into "Lien priority" and "Lien
    # filing date". It was one row, and this manifest carried a probe that
    # proved the priority half plus a paragraph saying the filing-date half
    # was not proven -- which is a comment, not a check. Two rows means the
    # unproven half now fails on its own line, which is what it should always
    # have done. `run_product` raised rather than silently re-matching, which
    # is the behaviour that surfaced the change at all.
    Mapping(
        "Lien priority", PROBE,
        "FIBO LenderLienPosition on the reified ex:CollateralPledge node -- "
        "the pledge is a node because priority belongs to the (facility, "
        "asset) PAIR, and two assets are each pledged to two facilities at "
        "different priorities",
        lambda: fluree_predicate(f"{EX}lienPosition"),
    ),
    Mapping(
        "Lien filing date", DEFERRED,
        "Not loaded, and it never was -- it comes from UCC-1, which the "
        "lien-filings row above waives on source grounds (per-state, several "
        "charge, coverage for this cast never confirmed). Until the vault "
        "split this row on 2026-08-24 it shared a line with lien priority, "
        "and the priority half greened both. `T` is claimed on it, so a "
        "consumer asking WHEN a lien was perfected -- which is what decides "
        "priority between competing secured parties -- gets nothing from a "
        "row the catalog shows as present.",
    ),
    Mapping(
        "Secured vs unsecured debt split", COVERED,
        "conditions.py -- collateral assets / facilities carrying collateral",
    ),
    Mapping(
        "Negative-pledge covenant presence", DEFERRED,
        "Spec assigns this to Fluree as `R`. Fluree holds five covenantType "
        "values (leverage, interest_coverage, fixed_charge_coverage, "
        "minimum_liquidity, secured_leverage) and negative_pledge is not among "
        "them; `fibo-fbc-dae-gty:NegativePledge` is bound in v2 but never "
        "materialized. The only evidence is document TEXT in Mongo, which "
        "cast_audit.py regexes for /negative\\s+pledge/. That counts a "
        "different quantity than §F asks for -- §F wants a negative-pledge "
        "covenant CONFLICTING WITH A PROPOSED NEW LIEN, and no such conflict "
        "is modelled. Consequence: the seed for covenant-cross-reference is "
        "absent, and a traversal for negative-pledge constraints returns "
        "empty against a graph that looks fully loaded.",
    ),
    Mapping(
        "pledgedBy edges", PROBE,
        "asset -> pledgor entity",
        lambda: fluree_predicate(f"{EX}pledgedBy"),
    ),
    Mapping(
        "Collateral asset descriptions and categories", COVERED,
        "conditions.py -- asset categories spanned (floor 4)",
    ),
    Mapping(
        "Collateral valuations and valuation dates", COVERED,
        "conditions.py -- valuation staleness spread, and the haircut flip",
    ),
    Mapping(
        "Deposit account balances", COVERED,
        "conditions.py -- deposit accounts (floor 20)",
    ),
    Mapping(
        "setOffAgainst and nettedUnder edges", PROBE,
        "both edge types present in the ledger",
        lambda: min(fluree_predicate(f"{EX}setOffAgainst"),
                    fluree_predicate(f"{EX}nettedUnder")),
    ),
    Mapping(
        "Haircut schedule by asset class", COVERED,
        "conditions.py -- covered gross, under-covered after haircuts",
    ),
    Mapping(
        "Set-off enforceability by jurisdiction", COVERED,
        "conditions.py -- set-off contractual but NOT enforceable (floor 4)",
    ),
    Mapping(
        "Shared-collateral case", PROBE,
        "assets securing more than one facility, counted IN FLUREE rather "
        "than in the Postgres pledge table conditions.py reads -- the spec "
        "assigns the shared case to Fluree, so proving it in Postgres would "
        "prove it in the wrong store",
        lambda: len([
            r for r in __import__("ccf.fluree", fromlist=["fluree"]).query(
                f"SELECT ?a (COUNT(?f) AS ?c) FROM <{FLUREE_LEDGER_V2}> WHERE "
                f"{{ ?f <{FIBO}FBC/DebtAndEquities/Debt/isCollateralizedBy> ?a }} "
                f"GROUP BY ?a HAVING (COUNT(?f) > 1)"
            )["results"]["bindings"]
        ]),
    ),
]



def mongo_count(collection: str, query: dict | None = None) -> int:
    from ccf.config import mongo_db

    return mongo_db()[collection].count_documents(query or {})


def agreements_with_multiple_texts() -> int:
    """Agreements whose corpus texts govern from two or more distinct dates.

    Recomputed from `document` here rather than read off the generator's
    `versioned_agreement_count`, because a stored figure records what was true
    when the artifact was written. If the corpus were reloaded without the
    identity fields, the artifact would still say 5 and this returns 0.
    """
    from ccf.config import mongo_db

    rows = mongo_db()["document"].aggregate([
        {"$match": {"agreement_id": {"$exists": True},
                    "governs_from": {"$exists": True}}},
        {"$group": {"_id": "$agreement_id",
                    "dates": {"$addToSet": "$governs_from"}}},
        {"$match": {"dates.1": {"$exists": True}}},
        {"$count": "n"},
    ])
    return next((r["n"] for r in rows), 0)


CROSS_REFERENCE = [
    Mapping(
        "Credit agreement full text", PROBE,
        "documents whose text actually reads as a credit agreement. NOT "
        "`mongo_count(\"document\")`, which is what conditions.py's "
        "\"credit agreements as full text\" floor uses: unfiltered, it counts "
        "all 175 documents of every form (8-K, 10-K, 10-Q, 10-D, 424B5) and "
        "would clear a floor of 15 with zero credit agreements among them",
        lambda: mongo_count("document", {"text": {"$regex": "CREDIT AGREEMENT"}}),
    ),
    Mapping(
        "Amended-and-restated agreement text", PROBE,
        "AGREEMENTS holding two or more texts that govern from DIFFERENT "
        "dates -- the unit §F names, and the reason this is not a count of "
        "amendments. 18 of 25 credit agreements in the corpus carry an "
        "amendment marker, so an amendment count clears a floor of 3 six "
        "times over while demonstrating nothing: with only the amendment "
        "held, an `as_of` before its date resolves to no text at all. "
        "Identity comes from generators/link_agreement_versions_wave15.py, "
        "which reads the agreement's date out of the amendment's own recital "
        "rather than pairing on filer or accession -- PAYCHEX filed two "
        "amendments to two DIFFERENT agreements on one day, so both of those "
        "keys are wrong. Distinct from covenant-in-force-as-of's "
        "\"facilities with >= 1 amendment\" (floor 12): that counts "
        "FACILITIES carrying amendment events in Fluree, not agreement TEXT "
        "in Mongo.",
        lambda: agreements_with_multiple_texts(),
    ),
    Mapping(
        "10-K debt footnote text", PROBE, "10-K documents in the corpus",
        lambda: mongo_count("document", {"form": "10-K"}),
    ),
    Mapping(
        "Document structure", COVERED,
        "conditions.py -- structure-aligned passages (floor 2500)",
    ),
    Mapping(
        "Passage spans with character offsets", COVERED,
        "conditions.py -- structure-aligned passages carry offsets",
    ),
    Mapping(
        "Passage embeddings", COVERED,
        "conditions.py -- passages with embeddings (floor 2500)",
    ),
    Mapping(
        "Document classification and residency tags", COVERED,
        "conditions.py -- memoranda classification-tagged (floor 20)",
    ),
    Mapping(
        "definedBy · measuredBy · crossReferences edges", PROBE,
        "all three present; the smallest of the three is reported so one "
        "loaded predicate cannot green a three-part row",
        lambda: min(fluree_predicate(f"{EX}definedBy"),
                    fluree_predicate(f"{EX}measuredBy"),
                    fluree_predicate(f"{EX}crossReferences")),
    ),
    Mapping(
        "Covenant and definition entities with passage anchors", PROBE,
        "definition entities carrying documentId + offsets. Counts the "
        "DEFINITION half, which was the absent one; covenant entities were "
        "never in doubt",
        lambda: fluree_count(
            f"?s <{RDF_TYPE}> <{EX}CovenantDefinition> . "
            f"?s <{EX}documentId> ?x"),
    ),
    Mapping(
        "FIBO facility and contract classes", PROBE,
        "CreditFacility instances in the ledger",
        lambda: fluree_instances(f"{FIBO}FBC/DebtAndEquities/Debt/CreditFacility"),
    ),
    Mapping(
        "CovenantDefinition and DefinedTerm", PROBE,
        "SPLIT AND CORRECTED by the vault 2026-08-24, on this validator's "
        "report: §C said no FIBO term existed for these and one does. Every "
        "node must carry fibo-fnd-agr-ctr:ContractualDefinition AND its ex: "
        "role, never one instead of the other, so this returns 0 if a single "
        "node is missing the FIBO class rather than counting the ones that "
        "have it. 49 CovenantDefinition + 158 DefinedTerm",
        lambda: dual_typed(("CovenantDefinition", "DefinedTerm")),
    ),
    Mapping(
        "Covenant and the linking predicates", PROBE,
        "the genuinely ex:-only half of the old row -- ex:Covenant plus "
        "definedBy, crossReferences and unresolvedTerm. Smallest reported; "
        "unresolvedTerm is the floor at 2 and is meant to be small, it "
        "records terms a covenant cites that the defined-terms article does "
        "not define",
        lambda: min(fluree_instances(f"{EX}Covenant"),
                    fluree_predicate(f"{EX}definedBy"),
                    fluree_predicate(f"{EX}crossReferences"),
                    fluree_predicate(f"{EX}unresolvedTerm")),
    ),
    Mapping(
        "Covenant thresholds and test periods", PROBE,
        "ex:threshold assertions (test periods are ex:testFrequency)",
        lambda: fluree_predicate(f"{EX}threshold"),
    ),
    Mapping(
        "Internal credit-opinion memoranda", COVERED,
        "conditions.py -- internal credit memoranda (floor 20)",
    ),
    Mapping(
        "Corpus-scope entitlement rules", COVERED,
        "conditions.py -- memoranda classification-tagged, which is what "
        "corpus_scope gates on",
    ),
]

IN_FORCE = [
    Mapping(
        "FIBO facility, guaranty, and credit-event classes", PROBE,
        "DECLARED as schema nodes, which is what this row's `G` asks for — "
        "it reads `schema`, not `R`. The first cut probed for INSTANCES and "
        "failed on Guaranty, which is declared but has none (guarantees are "
        "carried by 9 Guarantor nodes and isGuarantorOf edges, and the "
        "instrument itself is never instantiated). A schema row is satisfied "
        "by the declaration; demanding instances of it would have reported a "
        "gap the catalog does not claim",
        lambda: min(
            fluree_declared(f"{FIBO}FBC/DebtAndEquities/Debt/CreditFacility"),
            fluree_declared(f"{FIBO}FBC/DebtAndEquities/Guaranty/Guaranty"),
            fluree_declared(
                f"{FIBO}FBC/DebtAndEquities/CreditEvents/CrossDefaultProvision"),
        ),
    ),
    Mapping(
        "CovenantDefinition", PROBE,
        "same correction as covenant-cross-reference: dual-typed "
        "ContractualDefinition + ex:CovenantDefinition, 0 if any node carries "
        "only one",
        lambda: dual_typed(("CovenantDefinition",)),
    ),
    Mapping(
        "Covenant, MeasurementPeriod, and the linking predicates", PROBE,
        "the ex:-only half -- Covenant, MeasurementPeriod, measuredBy, "
        "supersededBy. Correctly NOT dual-typed: ContractualDefinition "
        "describes a definition, and a covenant is not one",
        lambda: min(fluree_instances(f"{EX}Covenant"),
                    fluree_instances(f"{EX}MeasurementPeriod"),
                    fluree_predicate(f"{EX}measuredBy"),
                    fluree_predicate(f"{EX}supersededBy")),
    ),
    Mapping(
        "Covenant terms — type, threshold, test frequency", PROBE,
        "all three predicates present on covenant nodes",
        lambda: min(fluree_predicate(f"{EX}covenantType"),
                    fluree_predicate(f"{EX}threshold"),
                    fluree_predicate(f"{EX}testFrequency")),
    ),
    Mapping(
        "Covenant definitions — how the ratio is computed", PROBE,
        "ratio definitions extracted from the EX-10 defined-terms article, "
        "anchored to document offsets",
        lambda: fluree_instances(f"{EX}CovenantDefinition"),
    ),
    Mapping(
        "covenantOf · definedBy · measuredBy edges", PROBE,
        "all three present; smallest reported so covenantOf's 182 cannot "
        "green the row on its own, which is what a naive probe would have "
        "done while definedBy and measuredBy were at zero",
        lambda: min(fluree_predicate(f"{EX}covenantOf"),
                    fluree_predicate(f"{EX}definedBy"),
                    fluree_predicate(f"{EX}measuredBy")),
    ),
    Mapping(
        "Amendment events with effective dates", COVERED,
        "conditions.py -- facilities with >= 1 amendment (floor 12)",
    ),
    Mapping(
        "Amendment booking dates (assertion time)", COVERED,
        "conditions.py -- amendments with BOTH time axes (floor 12)",
    ),
    Mapping(
        "Covenant compliance statements", COVERED,
        "conditions.py -- past-breach-now-compliant covenants",
    ),
    Mapping(
        "Acceleration and breach events", COVERED,
        "conditions.py -- obligors with real 8-K Item 2.04 (floor 2)",
    ),
    Mapping(
        "Financial inputs for headroom evaluation", COVERED,
        "conditions.py -- past-breach-now-compliant needs headroom inputs",
    ),
    Mapping(
        "Breach-threshold and cure policy", COVERED,
        "conditions.py -- policy versions, distinct dates (floor 2)",
    ),
    Mapping(
        "Policy version history with effective dates", PROBE,
        "ex:PolicyVersion instances in the ledger",
        lambda: fluree_instances(f"{EX}PolicyVersion"),
    ),
    Mapping(
        "Drawdown events with timestamps", COVERED,
        "conditions.py -- drawdowns across amendment boundaries (floor 20)",
    ),
    Mapping(
        "Amendment with a lagged booking date", COVERED,
        "conditions.py -- engineered booking lags labelled (floor 3)",
    ),
]


#: product -> mappings. A product absent from here is UNMAPPED and fails.
# `counterparty-reference-snapshot` is THE ONLY PRODUCT SPEC ON
# spec-standard-v0-3. The vault re-authored it (spec's own §-note), collapsing
# §C from 10 rows to 4. This manifest was re-derived against that on
# 2026-08-28; before then it raised on its first mapping, and because the
# sweep runs alphabetically that one raise hid every product from `covenant-`
# onward. `test_every_manifest_still_resolves_against_its_live_spec` now fails
# on this drift by name instead of aborting the run.
#
# WHERE THE FOUR DROPPED ELEMENTS WENT -- none is "lost", and none was
# waived for convenience:
#   Internal obligor risk grade . out of scope by the spec's own sentence,
#       "Scope boundary: identity only -- no exposure, no grade, no
#       relationship". The element itself is real and still ours; it belongs
#       to `rating-and-spread-migration`, which names it. The measured gap
#       that used to live here is preserved in known-issues §55 rather than
#       deleted with the row.
#   Coverage RM assignment ..... same sentence, "no relationship".
#       `ccf_v2.coverage_assignment` is unaffected and is probed by
#       `client-360-coverage-graph`.
#   CIK ........................ not deleted, reassigned. Named by six other
#       specs; here it is subsumed by the surviving crosswalk row, whose
#       probe below still requires it.
#   SIC code ................... not deleted, reassigned -- `credit-memo-
#       context` and `obligor-financial-spread` name it.
#
# §F WARNING for anyone extending this block: v0.3 REPURPOSES §F from
# "Manufacture envelope" to "Source binding & readiness". Reading §F by
# letter across the catalog now returns two different sections. Match by
# NAME.
#: ISO 17442: 20 uppercase alphanumerics. Deliberately a SECOND copy of the
#: pattern in `conditions.py` -- these two modules do not import each other --
#: and `test_the_two_real_lei_definitions_agree` asserts the copies are equal
#: rather than trusting them to stay so.
_REAL_LEI = re.compile(r"[A-Z0-9]{20}")


def _same_place(a, b) -> bool:
    """Do two (country, city, region) triples name the same PLACE?

    NOT the same question as "do these strings differ", and the gap between
    the two is measurable: of the 69 entities whose headquarters differed from
    their legal domicile on a raw comparison, **4 differed only by case** --
    AMPHENOL CORP /DE/ carries `WILMINGTON` against `Wilmington`, and three
    others the same. Those are one address typed twice, not two addresses.

    A missing component is never equal to a present one: `None` folds to the
    empty string, which no real component matches, so a half-loaded row
    reports as a different place rather than quietly matching.
    """
    def norm(triple):
        return tuple((x or "").strip().casefold() for x in triple)
    return norm(a) == norm(b)


def _addresses_labelled(rows) -> int:
    """1 iff every REAL-LEI entity carries BOTH addresses. 0 otherwise.

    `rows` are `(lei, legal_address_country, hq_address_country)`.

    Inverted like `unresolved_graph_leis`, and for the same reason: a count of
    entities carrying both would have passed this row throughout the period
    when NO entity carried a headquarters address at all, on the strength of
    the legal one. The quantity that decides the row is the shortfall.

    THE EXCLUSION IS DERIVED, NOT LISTED. Entities without a real LEI are out
    of scope because GLEIF publishes addresses only for registered LEIs -- the
    three synthetic ABS deal trusts have no GLEIF record and never will. That
    is expressed as `_REAL_LEI` rather than as three hardcoded identifiers, so
    a fourth synthetic entity is excluded automatically and a real LEI can
    never be excluded by being added to a list nobody revisits.
    """
    seen_real = False
    for lei, legal, hq in rows:
        if not _REAL_LEI.fullmatch((lei or "").strip()):
            continue
        seen_real = True
        if not legal or not hq:
            return 0
    # An empty estate has no unlabelled addresses, which is not the same thing.
    return 1 if seen_real else 0


def both_addresses_present() -> int:
    """`_addresses_labelled` over the live estate."""
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei, legal_address_country, hq_address_country '
                    f'FROM "{PG_SCHEMA_V2}".legal_entity')
        return _addresses_labelled(cur.fetchall())


COUNTERPARTY = [
    Mapping(
        "LEI, legal name, jurisdiction", PROBE,
        "CLOSED Wave 20; this row was six of seven until 2026-08-28. Six "
        "attribute groups were always present -- 153 rows carry lei, "
        "legal_name, legal_jurisdiction, entity_status, registration_status "
        "and a non-empty legal_form together. The seventh is ADDRESSES, "
        "plural, and §B names which two: `headquarters and legal address`. "
        "The estate held ONE triple called address_*, WITH NOTHING RECORDING "
        "WHICH OF THE TWO IT WAS. That ambiguity was the worse half of the "
        "defect: a missing address returns nothing and the consumer notices, "
        "while an unlabelled one returns Wilmington, Delaware for a company "
        "run from Whippany, New Jersey. Renamed to legal_address_* (which is "
        "what it always was) and hq_address_* added and loaded -- 103 "
        "subsidiaries from sources/gleif_l1/subsidiaries_l1.json, 50 anchors "
        "fetched by generators/fetch_anchor_hq_wave20.py. The probe INVERTS "
        "THE SHORTFALL rather than counting: a count of entities carrying "
        "both would have passed throughout the period when none carried a "
        "headquarters address at all, on the strength of the legal one. "
        "Entities without a REAL LEI are excluded because GLEIF publishes "
        "addresses only for registered LEIs -- three synthetic ABS deal "
        "trusts, and the exclusion is DERIVED from the LEI form rather than "
        "listed, so a fourth is excluded automatically and a real LEI can "
        "never be excluded by a stale list. 65 of 153 name a genuinely "
        "different place, measured with case and whitespace normalised: a "
        "raw comparison says 69, but 4 of those differ only in case "
        "(AMPHENOL CORP /DE/ carries WILMINGTON against Wilmington) and are "
        "one address typed twice, not two addresses.",
        both_addresses_present,
    ),
    Mapping(
        "Internal client identity for no-LEI", COVERED,
        "CLOSED Wave 20; this row was ZERO until 2026-08-28 and THE OLD "
        "MANIFEST COULD NOT SEE IT. Its predecessor was marked COVERED "
        "against conditions.py's crosswalk floors, every one of which is an "
        "inner join on `lei` -- structurally incapable of reporting the "
        "absence of entities that have none, and reading a healthy 50 "
        "throughout. `ccf_v2.internal_client` now holds 30 privately-held "
        "middle-market borrowers with `lei IS NULL` and no SYN- placeholder "
        "(a placeholder would resolve and defeat §G's acceptance criterion), "
        "each with a matching `crosswalk` row carrying a NULL lei. A "
        "SEPARATE TABLE, not a nullable legal_entity.lei: that column is the "
        "primary key with 9 foreign keys on it, and §C's single-writer "
        "paragraph names the internal client master as a different "
        "authority. Provenance `synthetic — internal`, §C's stated class. "
        "conditions.py carries four delegates to "
        "validators/internal_client.py: population, clients resolving to "
        "name AND jurisdiction, clients reporting the LOWER freshness "
        "ceiling §D sets at months against 24h for LEI-registered, and -- "
        "the one that matters -- an assertion that the LEI-keyed join still "
        "sees ZERO of them, so the blindness that hid this gap is proven on "
        "every run rather than remembered.",
    ),
    Mapping(
        "Entitlement scope by jurisdiction", COVERED,
        "CLOSED Wave 20. `principal` carried side, perspective, sees_mnpi, "
        "sees_need_to_know and sees_eu_person_data and NO JURISDICTION AT "
        "ALL, so the count of principals cleared any floor while the "
        "condition -- DIFFERING jurisdiction visibility -- was not "
        "satisfiable by any query, and the Policy Operator §B binds "
        "(`Entitlement scope only -- JURISDICTION VISIBILITY per calling "
        "principal`) had nothing to filter on. `ccf_v2.principal_jurisdiction` "
        "now grants one row per (principal, prefix), provenance `synthetic "
        "— internal`. conditions.py carries three checks that all delegate "
        "to validators/entitlement.py and RECOMPUTE from "
        "legal_entity.legal_jurisdiction on every run -- distinct visible "
        "SETS (floor 3, ours: v0.3 states no figure, and the old wording "
        "came from the superseded Q019 §F), one entity visible to a named "
        "principal and not another, and every principal restricted so no "
        "unrestricted principal hides a no-op inside a passing check. "
        "COUNTS SETS, NOT SIZES: PRIN-KYC-004 and PRIN-TRD-003 each see 21 "
        "entities and share NONE of them, so the estate holds 4 distinct "
        "views and only 3 distinct sizes -- a gate comparing counts reports "
        "3 and is wrong.",
    ),
    Mapping(
        "internal client crosswalk", PROBE,
        "THE CROSSWALK IS THE PRODUCT, per §C's own correlation-key note. "
        "Requires lei, internal_client_id AND cik non-null on the same row, "
        "so the CIK the v0.3 rewrite stopped naming separately is still "
        "asserted here rather than quietly dropped with its row -- LEI -> "
        "CIK -> ticker is the join CLAUDE.md's settled decisions depend on, "
        "and six other specs name CIK. Floor behaviour is conditions.py's: "
        "crosswalk resolves LEI <-> internal (50) and crosswalk orphans "
        "inverted to 0.",
        lambda: pg_count(
            "SELECT count(*) FROM {S}.crosswalk WHERE lei IS NOT NULL "
            "AND internal_client_id IS NOT NULL AND cik IS NOT NULL"),
    ),
]


# --------------------------------------------------------------------------
# corporate-family-tree
# --------------------------------------------------------------------------

CMNS = "https://www.omg.org/spec/Commons/"
C_LEGAL_ENTITY = f"{CMNS}Organizations/LegalEntity"
_CC = f"{FIBO}BE/OwnershipAndControl/CorporateControl/"
P_OWNS = f"{FIBO}FND/OwnershipAndControl/Ownership/owns"
P_CONTROLS = f"{FIBO}FND/Relations/Relations/controls"
P_GLOBAL_ULTIMATE = f"{_CC}hasGlobalUltimateParent"
P_DOMESTIC_ULTIMATE = f"{_CC}hasDomesticUltimateParent"


def gleif_pairs(relationship_type: str) -> set[tuple[str, str]]:
    """GLEIF RR-CDF records as (child, parent) -- the orientation GLEIF states.

    Stripped on both ends. Some LEI columns in this estate are `CHAR(20)` and
    a trailing blank turns a genuine match into a miss, which would read here
    as a *correctly* oriented edge going missing -- the exact false alarm this
    probe would be worst at explaining.
    """
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT child_lei, parent_lei FROM {PG_SCHEMA_V2}"
            f".corporate_ownership_record WHERE relationship_type = %s",
            (relationship_type,))
        return {(c.strip(), p.strip()) for c, p in cur.fetchall()}


def fluree_lei_pairs(predicate: str) -> set[tuple[str, str]]:
    """(subject LEI, object LEI) for edges whose BOTH ends carry `ex:lei`.

    Restricted to LEI-bearing ends on purpose: those are the only edges GLEIF
    can adjudicate. Bridging stubs have no LEI and are out of scope here.
    """
    from ccf import fluree

    q = (f"SELECT ?sl ?ol FROM <{FLUREE_LEDGER_V2}> WHERE {{ "
         f"?s <{predicate}> ?o . ?s <{EX}lei> ?sl . ?o <{EX}lei> ?ol }} "
         f"LIMIT 5000")
    return {(b["sl"]["value"].strip(), b["ol"]["value"].strip())
            for b in fluree.query(q)["results"]["bindings"]}


def _oriented(edges: set[tuple[str, str]],
              gleif: set[tuple[str, str]],
              subject_is_child: bool) -> int:
    """Edges agreeing with GLEIF's direction, or 0 if ANY edge contradicts it.

    A COUNT CANNOT SEE AN ARROW. That is not a general observation -- it is
    known-issues §19.3, where all 139 ultimate-parent edges in this ledger
    pointed the wrong way for twelve waves while every registered condition
    passed, because each of them counted edges, hops or cycles and a reversed
    graph has exactly as many of all three. `corporate-family-tree` answers
    *who is the ultimate parent of X*; inverted, that traversal returns X's
    subsidiaries and reads as a perfectly healthy result.

    So this probe does not count edges, it compares ORIENTATION against the
    GLEIF records those edges were built from, and it is deliberately brittle:
    a single edge found in the contradicting direction returns 0 and fails the
    row. Partial re-inversion is the realistic regression -- a loader re-run
    over a subset -- and a probe that only asked "are some still right?" would
    pass straight through it.
    """
    forward = edges if subject_is_child else {(o, s) for s, o in edges}
    backward = {(o, s) for s, o in forward}
    if backward & gleif:
        return 0
    return len(forward & gleif)


def direct_parent_oriented() -> int:
    """`owns` runs parent -> child, so its SUBJECT must be the parent."""
    return _oriented(fluree_lei_pairs(P_OWNS),
                     gleif_pairs("IS_DIRECTLY_CONSOLIDATED_BY"),
                     subject_is_child=False)


def ultimate_parent_oriented() -> int:
    """`has*UltimateParent` runs child -> parent, so its SUBJECT is the child.

    Both FIBO properties are checked against the same GLEIF consolidation
    records. The domestic edges are derived rather than fetched -- the loader
    walks direct-parent within one country, GLEIF publishes global only -- so
    fewer of them match, but a derived edge is still bound by the direction of
    the property it is asserted on.
    """
    return _oriented(
        fluree_lei_pairs(P_GLOBAL_ULTIMATE) | fluree_lei_pairs(P_DOMESTIC_ULTIMATE),
        gleif_pairs("IS_ULTIMATELY_CONSOLIDATED_BY"),
        subject_is_child=True)


def all_graph_leis() -> set[str]:
    """Every `ex:lei` value in the ledger, whichever product loaded it.

    Not the population of any one product's row -- it spans the whole estate.
    Kept because `family_tree_leis` below has to be shown to be SMALLER than
    it, and an exclusion is only worth asserting against a set that provably
    contains the thing being excluded.
    """
    from ccf import fluree

    return {b["l"]["value"].strip() for b in fluree.query(
        f"SELECT ?s ?l FROM <{FLUREE_LEDGER_V2}> WHERE {{ ?s <{EX}lei> ?l }} "
        f"LIMIT 5000")["results"]["bindings"]}


def family_tree_leis() -> set[str]:
    """LEI-bearing endpoints of the four family-tree predicates.

    THE POPULATION IS THE TRAVERSAL, NOT THE LEDGER. This probe used to draw
    from `all_graph_leis()`, which was the same set back when the ledger was
    essentially the family tree and is not remotely the same set now. Every
    later wave that loaded LEI-bearing entities of its own enlarged this row's
    denominator with entities that are not family-tree traversal results:
    measured 2026-08-28, 434 LEI-bearing nodes against 136 that any family
    edge actually touches. The 298 outside the family tree break down exactly:
    201 Wave 17 `SYN-AML-` parties, 39 Wave 18 syndicate members, 37 registry
    companies, 19 that carry `legal_entity` attributes but sit on no family
    edge, and 2 that resolve from no Postgres table at all
    (5493000FN178SW540N88, 549300LFK257DF2RVN05 -- a real but separate gap,
    logged rather than absorbed here because they are not this row's). The
    first three groups resolve from their own single writers exactly as the
    partition requires. The row sat red at 279 unresolved -- those 2 plus the
    201 AML parties plus the 76 syndicate/registry -- while every entity the
    family tree can actually reach resolved.

    So the denominator is derived from the edges, and the arms in
    `test_family_tree_probes.py` assert both that it excludes the AML parties
    and that it is strictly smaller than the ledger -- reverting this to a
    bare `?s ex:lei ?l` fails them.
    """
    leis: set[str] = set()
    for predicate in (P_OWNS, P_CONTROLS,
                      P_GLOBAL_ULTIMATE, P_DOMESTIC_ULTIMATE):
        for subject_lei, object_lei in fluree_lei_pairs(predicate):
            leis.add(subject_lei)
            leis.add(object_lei)
    return leis


def unresolved_graph_leis() -> int:
    """1 when every family-tree entity resolves, 0 when any does not.

    Inverted on purpose. The natural probe -- count entities whose LEI is in
    `legal_entity` -- returned 50 while 105 resolved to nothing, and would
    have reported this row healthy for twelve waves. The quantity that decides
    the row is the SHORTFALL, so that is what is measured; the 1/0 is only
    because a Mapping probe passes on > 0.

    `reporting_bank` is unioned in because two ledger entities legitimately
    resolve from there instead. Excluding them by hand would have made this
    probe carry a hardcoded pair of LEIs that nothing would ever revisit.

    NARROWING THE POPULATION MOVED THE VACUITY RISK, so note where it landed:
    `_all_resolve` returns 1 for an empty input, and the population now comes
    from family edges rather than from entities. The floor that makes that
    acceptable is therefore `conditions.py`'s "ownership graph edges (all
    predicates) >= 500", NOT its entity floor -- an estate that lost every
    ownership edge would empty this set and green the row, and the edge floor
    is the check that refuses to let that happen.
    """
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT lei FROM "{PG_SCHEMA_V2}".legal_entity '
                    f'UNION SELECT lei FROM "{PG_SCHEMA_V2}".reporting_bank '
                    f"WHERE lei IS NOT NULL")
        known = {r[0].strip() for r in cur.fetchall()}
    return _all_resolve(family_tree_leis(), known)


def _all_resolve(graph_leis: set[str], resolvable: set[str]) -> int:
    """Split out so the decision can be tested without a live estate."""
    return 0 if (graph_leis - resolvable) else 1


FAMILY_TREE = [
    Mapping(
        "FIBO ontology (T-Box)", PROBE,
        "the five Business Entities / Ownership & Control terms this product "
        "traverses, declared as schema nodes: cmns-org:LegalEntity, owns, "
        "controls, hasGlobalUltimateParent, hasDomesticUltimateParent. NOT "
        "the whole module: hasSubsidiary and isSubsidiaryOf are named in §B's "
        "contract and are declared nowhere. That absence is carried by the "
        "subsidiary-list row below rather than buried inside this min()",
        lambda: min(fluree_declared(t) for t in (
            C_LEGAL_ENTITY, P_OWNS, P_CONTROLS,
            P_GLOBAL_ULTIMATE, P_DOMESTIC_ULTIMATE)),
    ),
    Mapping(
        "Direct parent relationship", PROBE,
        "`owns` edges whose direction AGREES with the GLEIF "
        "IS_DIRECTLY_CONSOLIDATED_BY record they came from, and 0 if any "
        "single edge contradicts it. Not a count of edges -- see §19.3",
        direct_parent_oriented,
    ),
    Mapping(
        "Ultimate parent relationship", PROBE,
        "hasGlobalUltimateParent + hasDomesticUltimateParent, again by "
        "DIRECTION against GLEIF IS_ULTIMATELY_CONSOLIDATED_BY. This is the "
        "row §19.3 was found in: 139 edges, all inverted, all conditions green",
        ultimate_parent_oriented,
    ),
    Mapping(
        "Accounting consolidation basis", DEFERRED,
        "§C assigns this to Fluree as `R`, an EDGE PROPERTY, and Fluree's "
        "ownership edges carry no properties at all -- edge_triples() in "
        "load_fluree_wave3.py emits one bare triple per fact. The data is "
        "fetched and loaded: ccf_v2.corporate_ownership_record"
        ".relationship_type holds 140 IS_DIRECTLY_CONSOLIDATED_BY + 140 "
        "IS_ULTIMATELY_CONSOLIDATED_BY. UNBLOCKED 2026-08-24: the vault "
        "answered the note this validator raised and now says outright that "
        "the row REQUIRES A REIFIED EDGE, citing collateral-and-setoff's "
        "ex:CollateralPledge as the precedent -- a property of a pair needs a "
        "node. So this is no longer waiting on a decision, it is waiting on "
        "the load, and it closes together with the validity-dates row below, "
        "which needs the same node.",
    ),
    Mapping(
        "Relationship status", PROBE,
        "SPLIT OUT by the vault 2026-08-24 and REASSIGNED to Postgres, which "
        "is where it already was -- corporate_ownership_record"
        ".relationship_status, 280 of 280 populated. It shared a row with the "
        "validity dates and was failing on their behalf",
        lambda: pg_count(
            "SELECT count(*) FROM {S}.corporate_ownership_record "
            "WHERE relationship_status IS NOT NULL"),
    ),
    Mapping(
        "Relationship validity dates", DEFERRED,
        "THE SPEC'S REASON IS WRONG, AND IT MATTERS. §C now says "
        "`unpopulated at source`. It is populated, in a file this repository "
        "already holds: sources/gleif_l2/rr-golden-copy.csv.zip, retrieved "
        "2026-08-22, carries Relationship.Period.N.startDate / .endDate, and "
        "ALL 280 of our relationship records appear in it with a "
        "RELATIONSHIP_PERIOD start (measured 2026-08-24; 280 also carry an "
        "ACCOUNTING_PERIOD, which is the consolidation basis's own interval, "
        "and 84 a DOCUMENT_FILING_PERIOD). What is true is that the Wave 3 "
        "fetch took the relationship API, which returns parent, child, edge "
        "type and jurisdiction only, so the dates never reached Postgres -- "
        "period_start and period_end are 0 of 280. NOT WAIVED, precisely "
        "because a waiver is a claim about the SOURCE: the source has it. "
        "Blocked on the same reified edge as the consolidation basis above, "
        "and on §19.4 -- Fluree 4.1.4 corrupts xsd:date, so these must land "
        "as plain strings. The vault has been told.",
    ),
    Mapping(
        "Subsidiary list", PROBE,
        "CLOSED 2026-08-24, from both ends. The jurisdictions were loaded "
        "(loaders/load_stub_jurisdictions.py, from a source that had held "
        "them since Wave 3), and the vault REMOVED the ownership-percentage "
        "requirement after checking the rule: 17 CFR 229.601(b)(21)(i) "
        "requires name, jurisdiction and trade names, and does not require a "
        "percentage. The element is now `name and jurisdiction`, and this "
        "counts stubs carrying BOTH. 306 of 343 -- the other 37 were filed "
        "with the jurisdiction column blank, which is a fact about those "
        "filings, not a gap in the load.",
        lambda: fluree_count(
            f'?s <{EX}provenance> "synthetic — bridging" . '
            f"?s <http://www.w3.org/2000/01/rdf-schema#label> ?x . "
            f"?s <{EX}jurisdictionCode> ?j"),
    ),
    Mapping(
        "Stub entities for non-LEI subsidiaries", DEFERRED,
        "HALF DONE, and the other half is now specified. The vault moved this "
        "row to `Fluree + Postgres` on 2026-08-24 and named the identifier "
        "scheme the Postgres side needs: SYN-, already published in "
        "fibo-iri-binding and already in use for the ABS deal trusts. The "
        "Fluree half is loaded -- 343 nodes labelled `synthetic — bridging`, "
        "with 344 owns edges pointing at them. The Postgres half is not: "
        "ccf_v2.legal_entity holds no row for any of them, so a traversal "
        "returning a stub resolves a label and nothing else. This is now a "
        "load, not a question. Note the vault's schema warning, which this "
        "estate has already been bitten by: use VARCHAR(20), because CHAR(20) "
        "blank-pads a short synthetic id and returns the padding on read.",
    ),
    Mapping(
        "Entity attributes for traversal results", PROBE,
        "EVERY LEI-bearing graph entity now resolves. This row read 50 of 155 "
        "until 2026-08-24: 103 GLEIF subsidiaries had Level 2 fetched in "
        "Wave 3 (who owns whom) and Level 1 never (who they are), so a "
        "traversal returned entities whose Enrich step yielded nothing while "
        "the graph itself looked complete. generators/fetch_gleif_"
        "subsidiaries.py + loaders/load_gleif_subsidiaries.py close it; "
        "legal_entity 53 -> 156 rows. The probe COUNTS THE SHORTFALL AND "
        "INVERTS IT: it returns 1 only while nothing is unresolved, and 0 "
        "the moment anything is -- a plain count of resolvable entities "
        "would have passed at 50 of 155 too. (That sentence read the other "
        "way round until 2026-08-28 and said the probe was 0 when healthy, "
        "which is what the code has never done; a reader checking this "
        "row against a red run was told the assertion was inverted when "
        "it was not.) "
        "POPULATION, corrected the same day: the probe asks only about "
        "LEI-bearing endpoints of family-tree edges (136), not every "
        "ex:lei node in the ledger (434). The wider set pulled in Wave 17 "
        "AML parties, Wave 18 syndicate members and registry companies, "
        "which belong to other products and resolve from their own single "
        "writers; it held this row red at 279 unresolved while every "
        "family-tree entity resolved. "
        "Two LEI-bearing nodes are excluded and are not a gap: JPMorgan Chase "
        "Bank NA and JPMORGAN CHASE&CO resolve from ccf_v2.reporting_bank, "
        "which is their single writer, and copying them here to tidy one join "
        "would break that. NOTE the 662 nodes with no LEI at all -- 344 "
        "Exhibit 21 bridging stubs among them -- are still unresolvable, and "
        "that is the stub row above, not this one.",
        unresolved_graph_leis,
    ),
    Mapping(
        "Materiality threshold by intent", DEFERRED,
        "The only table of this name holds a DIFFERENT QUANTITY. §C wants an "
        "ownership-fraction threshold bound to a credit intent -- §D's worked "
        "call is `?intent=concentration-review&materiality=0.05`, and §B "
        "binds it into the policy envelope. ccf_v2.materiality_threshold has "
        "three rows keyed on the FX intents break-investigation / "
        "control-review / regulatory-report, and its column is "
        "`threshold_pips`: an FX post-trade tolerance in pips, not a fraction "
        "of ownership. bo_threshold.threshold_pct is a percentage but a "
        "beneficial-ownership one, keyed by jurisdiction and the KYC intents. "
        "A probe pointed at either table would go green on this row forever "
        "while the element stayed absent. Consequence: §D step 2 loads the "
        "materiality bound to `intent`, finds nothing to bind, and the "
        "Policy Operator filters nothing.",
    ),
    Mapping(
        "Consolidated total assets", PROBE,
        "XBRL companyfacts `Assets` in Postgres, the materiality denominator",
        lambda: pg_count(
            "SELECT count(*) FROM {S}.financial_fact WHERE tag = 'Assets'"),
    ),
    Mapping(
        "Cross-shareholding cycle", COVERED,
        "conditions.py -- cross-shareholding CYCLES present (floor 2), which "
        "counts distinct cycles rather than cycle members",
    ),
]


# --------------------------------------------------------------------------
# ib-opportunity-synthesis
# --------------------------------------------------------------------------

def sqlite_count(sql: str) -> int:
    import sqlite3

    from ccf.config import SQLITE_PATH

    with sqlite3.connect(SQLITE_PATH) as conn:
        row = conn.execute(sql).fetchone()
        return int(row[0]) if row else 0


def ib_signal_count(signal_type: str) -> int:
    """OpportunitySignal nodes typed SIGNAL_TYPE, via the rdfs:label prefix
    `loaders/load_fluree_wave16.py` writes ("{signal_type} -- {lei} --
    {observed_at}"). `ex:signalType` is deliberately NOT asserted on these
    nodes -- it is Postgres-owned vocabulary (`signal_event.signal_type`,
    validators/partition.py's POSTGRES_OWNED_ATTRS) -- so the label prefix is
    the only handle. Existence only: current/in-window filtering is
    conditions.py's job (R3), not this probe's."""
    from ccf import fluree

    q = (f'SELECT ?s FROM <{FLUREE_LEDGER_V2}> WHERE {{ '
         f'?s <{RDF_TYPE}> <{EX}OpportunitySignal> . '
         f'?s <{RDFS_LABEL}> ?label . '
         f'FILTER(STRSTARTS(?label, "{signal_type} -- ")) }}')
    return len(fluree.query(q)["results"]["bindings"])


def merger_passage_count() -> int:
    """Passages anchored to a Wave 16 merger-proxy / S-4 document -- proves
    row 11 (passage spans), distinct from rows 2/5 which probe the documents
    themselves."""
    from ccf.config import mongo_db

    db = mongo_db()
    doc_ids = [d["_id"] for d in db["document"].find(
        {"doc_type": {"$in": ["merger_proxy", "registration_s4"]}}, {"_id": 1})]
    if not doc_ids:
        return 0
    return db["passage"].count_documents({"document_id": {"$in": doc_ids}})


IB_OPPORTUNITY = [
    Mapping(
        "M&A and material-agreement events", PROBE,
        "OpportunitySignal nodes typed ma_event_8k -- EDGAR 8-K Items "
        "1.01/2.01",
        lambda: ib_signal_count("ma_event_8k"),
    ),
    Mapping(
        "Merger proxies and deal terms", PROBE,
        "DEFM14A/PREM14A filings, doc_type=merger_proxy",
        lambda: mongo_count("document", {"doc_type": "merger_proxy"}),
    ),
    Mapping(
        "Activist and beneficial-ownership stakes", PROBE,
        "OpportunitySignal nodes typed activist_stake_13d -- SEC SC 13D/13G "
        "(R1: Fluree, never signal_event -- that table is a DIFFERENT "
        "product's, credit-surveillance-early-warning's)",
        lambda: ib_signal_count("activist_stake_13d"),
    ),
    Mapping(
        "Insider transaction activity", PROBE,
        "OpportunitySignal nodes typed insider_activity_form4 -- SEC Form 4",
        lambda: ib_signal_count("insider_activity_form4"),
    ),
    Mapping(
        "IPO and merger registration pipeline", DEFERRED,
        "HALF the row. §C names TWO form families -- S-1 AND S-4 -- and "
        "only S-4 is loaded (6 documents, doc_type=registration_s4). "
        "Probed 2026-08-24 across the 53 anchors: 43 S-1 filings exist "
        "across their lifetime and ZERO since 2023. The cast are "
        "established issuers -- already public, already reporting -- who "
        "do not file IPO registrations; that is a fact about the cast, not "
        "a gap in the fetch. Consequence: the S-1 half of this row cannot "
        "be populated from this cast without inventing a filing that was "
        "never made.",
    ),
    Mapping(
        "Institutional positioning", PROBE,
        "institutional_holder (SEC Form 13F, Wave 10) -- the source table "
        "institutional_positioning_13f signals are derived from",
        lambda: pg_count("SELECT count(*) FROM {S}.institutional_holder"),
    ),
    Mapping(
        "Debt maturity ladder", PROBE,
        "debt_instrument rows carrying Wave 16's own w16-i- prefix, "
        "extending the table Wave 11a owns -- a two-writer table, the same "
        "shape as deposit_account (Wave 9 + Wave 12)",
        lambda: pg_count(
            "SELECT count(*) FROM {S}.debt_instrument "
            "WHERE instrument_id LIKE 'w16-i-%'"),
    ),
    Mapping(
        "Spread trajectory", COVERED,
        "§C says so itself: 'inherited from [[rating-and-spread-migration]]' "
        "-- conditions.py's rating-and-spread-migration checks (observation "
        "dates; observation dates matched to a real published curve) "
        "already assert spread_observation, not duplicated here",
    ),
    Mapping(
        "Sector news and thematic signals", COVERED,
        "sector_news_gdelt signals derive straight from gdelt_mention "
        "(generators/generate_opportunity_signals.py), which conditions.py's "
        "credit-surveillance-early-warning 'GDELT mentions' check (floor "
        "200) already asserts -- no new Postgres row is written for this "
        "element",
    ),
    Mapping(
        "Government-contract revenue concentration", PROBE,
        "USASpending.gov awards resolved to a LEI",
        lambda: pg_count(
            "SELECT count(*) FROM {S}.gov_contract_concentration"),
    ),
    Mapping(
        "Passage spans on proxies and registrations", PROBE,
        "segmented passages anchored to a Wave 16 merger-proxy/S-4 document",
        merger_passage_count,
    ),
    Mapping(
        "Coverage portfolio and banker roster", COVERED,
        "§C says so itself: 'inherited from [[client-360-coverage-graph]]' "
        "-- conditions.py's client-360-coverage-graph 'synthetic bankers' "
        "check (floor 40) already asserts the banker/coverage_assignment "
        "tables Wave 10 created",
    ),
    Mapping(
        "Deal pipeline", PROBE,
        "mandate rows -- mandate_type and stage, both NOT NULL by "
        "constraint",
        lambda: pg_count("SELECT count(*) FROM {S}.mandate"),
    ),
    Mapping(
        "Client stated appetite and mandate history", PROBE,
        "mandate.stated_appetite -- the other half of the same table row 13 "
        "probes, checked separately so neither mapping silently covers for "
        "the other",
        lambda: pg_count(
            "SELECT count(*) FROM {S}.mandate "
            "WHERE stated_appetite IS NOT NULL"),
    ),
    Mapping(
        "Per-perspective ranking weights", COVERED,
        "conditions.py's ib-opportunity-synthesis 'weight-vector versions' "
        "check already asserts perspective_weight (floor 2 distinct "
        "weight_version)",
    ),
    Mapping(
        "ProjectionPlan per perspective", PROBE,
        "ib_projection_plan -- Wave 16's own table (Fix Round 1: never "
        "Wave 7's projection_plan, a different product's vocabulary)",
        lambda: pg_count("SELECT count(*) FROM {S}.ib_projection_plan"),
    ),
    Mapping(
        "Banker-local prospect notes", PROBE,
        "prospect_note rows carrying a banker_id -- the departmental "
        "spreadsheet notes this product adds",
        lambda: sqlite_count(
            "SELECT COUNT(*) FROM prospect_note WHERE banker_id IS NOT NULL"),
    ),
    Mapping(
        "Wall state and restricted list", COVERED,
        "§C says so itself: 'inherited from [[mnpi-wall-enforcement]]' -- "
        "conditions.py's mnpi-wall-enforcement checks already assert both "
        "halves: 'restricted list in the DEPARTMENTAL store' (SQLite) and "
        "'wall crossings with a recorded date' (Fluree)",
    ),
]


# --------------------------------------------------------------------------
# aml-typology-match
# --------------------------------------------------------------------------
#
# Confirmed Q019 form by section NAME before mapping a single row: the
# vault's §F heading reads "Manufacture envelope" (fetched 2026-08-25), not
# "Source binding & readiness" -- the v0.3 wording that would parse cleanly
# under a letter-only match while returning the wrong section.
#
# The self-review's own task index -- sanctions (existing, Task 5 index +
# Task 7), typology definitions (1-4), structural patterns (4, 13), filing
# posture (14), ownership and intermediaries (9), beneficial ownership (9),
# adverse media (existing gdelt_mention, mapped HERE), passage spans (3),
# parties (6, 7, 8), transactions (10, 11), alerts (12), network edges (13),
# SAR narratives (15), SAR classification (15), disposition rules (14),
# projection plans (16) -- names exactly the sixteen rows below; none is a
# genuine gap.

def advisory_passage_count() -> int:
    """Passages anchored to a Wave 17 FinCEN-advisory document -- proves
    row 8 (passage spans), distinct from row 2 which probes the advisory
    DOCUMENTS themselves. Same shape as merger_passage_count above."""
    from ccf.config import mongo_db

    db = mongo_db()
    doc_ids = [d["_id"] for d in db["document"].find(
        {"doc_type": "fincen_advisory"}, {"_id": 1})]
    if not doc_ids:
        return 0
    return db["passage"].count_documents({"document_id": {"$in": doc_ids}})


AML_TYPOLOGY = [
    Mapping(
        "Sanctions lists", PROBE,
        "sanctions_name rows -- Wave 13b's OFAC SDN + Consolidated fetch, "
        "reused whole; this product's own OFAC-band floor joins against it "
        "live and mints no new sanctions row",
        lambda: pg_count("SELECT count(*) FROM {S}.sanctions_name"),
    ),
    Mapping(
        "Typology definitions and narrative patterns", PROBE,
        "document rows carrying doc_type=fincen_advisory (Task 3 -- 4 "
        "FinCEN advisories fetched and segmented)",
        lambda: mongo_count("document", {"doc_type": "fincen_advisory"}),
    ),
    Mapping(
        "Typology structural patterns", PROBE,
        "Fluree nodes dual-typed Typology + TypologyPattern (Task 4 derives "
        "the 4 structural definitions, Task 13 loads them)",
        lambda: fluree_instances(f"{EX}TypologyPattern"),
        divergence=(
            "Two, both ruled rather than stumbled into, and both disclosed "
            "in the data itself as well as here. (1) SUBSTITUTION -- the "
            "spec's fourth typology is rapid_pass_through; FinCEN publishes "
            "no advisory on it, verified across all 194, so it was replaced "
            "with shell_company_ownership with Dave's approval. (2) "
            "ABSTRACTION -- that advisory (FIN-2017-A003) states the "
            "concealment mechanism through a RESIDENTIAL REAL ESTATE case, "
            "and this estate models no property register, so the pattern is "
            "extracted at the mechanism level with the asset class "
            "abstracted; the typology record carries the narrowing in its "
            "own abstracted_from_advisory field. Full record: "
            "docs/known-issues.md #29."),
    ),
    Mapping(
        "Regulatory filing posture and guidance history", PROBE,
        "Fluree FilingPosture nodes (Task 14 -- POST-2025-01, POST-2026-01)",
        lambda: fluree_instances(f"{EX}FilingPosture"),
    ),
    Mapping(
        "Corporate ownership and intermediary structures", PROBE,
        "ex:isIntermediaryFor edges -- Wave 13b's ICIJ-shaped offshore "
        "intermediary layer (generators/derive_icij_structure.py), reused "
        "whole per this row's own 'as pattern reference only'; this "
        "product mints no new intermediary row",
        lambda: fluree_predicate(f"{EX}isIntermediaryFor"),
    ),
    Mapping(
        "Beneficial ownership", PROBE,
        "aml_party.beneficial_owner_key rows bound to an EXISTING PSC-*/"
        "bo_chain owner (Task 9, reusing Wave 13b's beneficial-ownership "
        "graph per §C's own 'inherited from "
        "[[kyc-refresh-beneficial-ownership]]'); no conditions.py check "
        "asserts this column today, so PROBE rather than COVERED",
        lambda: pg_count(
            "SELECT count(*) FROM {S}.aml_party "
            "WHERE beneficial_owner_key IS NOT NULL"),
    ),
    Mapping(
        "Adverse media", PROBE,
        "gdelt_mention rows -- Wave 11b's existing GDELT fetch, reused "
        "whole; this product mints no new adverse-media row",
        lambda: pg_count("SELECT count(*) FROM {S}.gdelt_mention"),
    ),
    Mapping(
        "Passage spans on advisories and typology reports", PROBE,
        "segmented passages anchored to a Wave 17 fincen_advisory document",
        advisory_passage_count,
    ),
    Mapping(
        "All parties and entities under investigation", PROBE,
        "aml_party rows (Task 6 -- 201 invented parties, none real; "
        "CLAUDE.md rule 2)",
        lambda: pg_count("SELECT count(*) FROM {S}.aml_party"),
    ),
    Mapping(
        "All transactions", PROBE,
        "aml_transaction rows (Task 10 ordinary + Task 11 engineered, "
        "4,358 total)",
        lambda: pg_count("SELECT count(*) FROM {S}.aml_transaction"),
    ),
    Mapping(
        "Alert records and prior-alert history", PROBE,
        "aml_alert AND aml_alert_link both populated (Task 12) -- the "
        "MINIMUM of the two, so a loader that wrote alerts but no lineage "
        "row would not pass silently",
        lambda: min(
            pg_count("SELECT count(*) FROM {S}.aml_alert"),
            pg_count("SELECT count(*) FROM {S}.aml_alert_link")),
    ),
    Mapping(
        "transactedWith network edges", PROBE,
        "ex:transactedWith edges (Task 13 -- 7,736 directed rows over "
        "3,868 unordered pairs, all 4,358 transaction rows projected)",
        lambda: fluree_predicate(f"{EX}transactedWith"),
    ),
    Mapping(
        "SAR filing history and narratives", PROBE,
        "document rows carrying doc_type=sar_narrative (Task 15)",
        lambda: mongo_count("document", {"doc_type": "sar_narrative"}),
    ),
    Mapping(
        "SAR confidentiality classification", PROBE,
        "SQLite sar_classification rows (Task 15) -- the departmental-store "
        "reach this product's whole architecture rests on",
        lambda: sqlite_count("SELECT COUNT(*) FROM sar_classification"),
    ),
    Mapping(
        "Disposition rules by posture", PROBE,
        "Fluree DispositionRule nodes (Task 14 -- 16 rows, 4 typologies x "
        "2 dispositions x 2 postures)",
        lambda: fluree_instances(f"{EX}DispositionRule"),
    ),
    Mapping(
        "ProjectionPlan per perspective", PROBE,
        "aml_projection_plan rows (Task 16 -- l1/l2/examiner, 3 rows)",
        lambda: pg_count("SELECT count(*) FROM {S}.aml_projection_plan"),
    ),
]


# --------------------------------------------------------------------------
# syndicated-lending-co-lender (Wave 18)
# --------------------------------------------------------------------------

def peer_count(sql: str) -> int:
    """A count from the CO-LENDER's Postgres. `{P}` is its schema.

    Read-only, through `ccf.config.co_lender_pg_connect` -- the same guarded
    entry point the loaders and `validators/syndicate.py` use, never a
    connection assembled here.
    """
    from ccf.config import CO_LENDER_PG_SCHEMA, co_lender_pg_connect

    with co_lender_pg_connect() as conn, conn.cursor() as cur:
        cur.execute(sql.format(P=CO_LENDER_PG_SCHEMA))
        row = cur.fetchone()
        return int(row[0]) if row else 0


def peer_ledger_count(where: str) -> int:
    from ccf import fluree
    from ccf.config import CO_LENDER_FLUREE_LEDGER

    q = (f"SELECT ?s FROM <{CO_LENDER_FLUREE_LEDGER}> WHERE {{ {where} }}")
    return len(fluree.co_lender_query(q)["results"]["bindings"])


def wave18_passage_count() -> int:
    """Passages anchored to a Wave 18 credit agreement. Same shape as
    `advisory_passage_count` above, but keyed on the document's own
    `document_id` field rather than `_id`, because that is what the Wave 18
    loader writes into `passage.document_id`."""
    from ccf.config import mongo_db

    db = mongo_db()
    ids = [d["document_id"] for d in db["document"].find(
        {"doc_type": "credit_agreement_wave18"}, {"document_id": 1})]
    if not ids:
        return 0
    return db["passage"].count_documents({"document_id": {"$in": ids}})


SYNDICATED_CO_LENDER = [
    Mapping(
        "Syndicate composition", PROBE,
        "ex:SyndicateParticipation nodes carrying ex:commitmentUsd -- the "
        "reified (member, facility, amount, filed offset) fact Task 8 loads "
        "from the parsed Commitment Schedules. This row has TWO facets, "
        "lender NAMES and COMMITMENTS; the probe is the commitment half "
        "(the generator's `member_commitment`), and the name half is the "
        "45 FinanceSyndicateMember nodes the commitments hang off",
        lambda: fluree_predicate(f"{EX}commitmentUsd"),
        divergence=(
            "The lender NAMES and the per-lender COMMITMENTS are both filed "
            "and both loaded, which is what this row asks for. What the "
            "estate cannot offer is the schedule as a reconciled whole: not "
            "one of the twelve facilities' parsed shares sums to "
            "`ccf_v2.facility.commitment_amount` -- best 4.0% off, worst "
            "3391% -- for four legitimate filing-side reasons (unattributed "
            "placeholder rows, amendment exhibits listing only INCREMENTAL "
            "commitments, tranche captions spanning two tranches, and one "
            "Wave 4 facility total that is itself wrong). A consumer summing "
            "the shares will not arrive at the facility size. Measured and "
            "recorded in full: docs/known-issues.md §32 and §34."),
    ),
    Mapping(
        "Administrative agent identity", PROBE,
        "ex:administeredBy edges -- every one of the twelve syndicated "
        "facilities names its agent, resolving to 4 distinct institutions",
        lambda: fluree_predicate(f"{EX}administeredBy"),
    ),
    Mapping(
        "Voting thresholds", PROBE,
        "BOTH halves, as the MINIMUM of the two: the filed article text in "
        "MongoDB (`L`, Task 11) and the ex:AmendmentThreshold nodes derived "
        "from it in Fluree (`R`, Task 11b). §C assigns this row to two "
        "stores, and a probe of either alone would green a half-loaded row",
        lambda: min(
            mongo_count("passage", {"passage_kind": "voting_threshold"}),
            fluree_instances(f"{EX}AmendmentThreshold"),
        ),
    ),
    Mapping(
        "Assignment and transfer", PROBE,
        "passages with passage_kind=assignment_provision, one per Wave 18 "
        "credit agreement (Task 11)",
        lambda: mongo_count("passage", {"passage_kind": "assignment_provision"}),
    ),
    Mapping(
        "Amendment events and effective dates", PROBE,
        "ex:AmendmentEvent nodes carrying ex:effectiveDate (Task 9), each "
        "citing the filed offset its date was read from",
        lambda: fluree_predicate(f"{EX}effectiveDate"),
        divergence=(
            "ONE OF THE TWO NAMED SOURCES. §C says '8-K **Item 1.01**; "
            "amended EX-10'; every one of the six events was read from the "
            "amended EX-10 exhibit itself and no 8-K was fetched. The "
            "effective date and the amended facility are therefore filed and "
            "cited, but the ANNOUNCEMENT date -- when the borrower told the "
            "market, which is the gap an 8-K/EX-10 pair makes visible and "
            "which `T` on this row implies -- is not in the estate. Nothing "
            "here demonstrates a booking lag between announcement and "
            "effectiveness for a syndicated amendment."),
    ),
    Mapping(
        "Co-lender institution identities", PROBE,
        "syndicate_member rows carrying a real public identifier -- a GLEIF "
        "LEI or an FFIEC NIC RSSD (Tasks 3 and 5)",
        lambda: pg_count("SELECT count(*) FROM {S}.syndicate_member "
                         "WHERE lei IS NOT NULL OR rssd IS NOT NULL"),
        divergence=(
            "§C names BOTH identifier systems on this row; the estate has "
            "both for only 16 of the 45 members. 40 carry a real GLEIF LEI; "
            "16 of those also resolve to an FFIEC NIC RSSD, which exists "
            "only for US-supervised depository institutions and so cannot "
            "exist for the foreign banks and the credit funds in the "
            "syndicates; and 5 members are name-only, identified from the "
            "filed lender string with no LEI at all. A join keyed on RSSD "
            "reaches a third of the syndicate."),
    ),
    Mapping(
        "Co-lender financial condition", PROBE,
        "member_call_report rows -- FFIEC Call Report tier 1 capital, total "
        "assets and total equity per reporting member (Task 3)",
        lambda: pg_count("SELECT count(*) FROM {S}.member_call_report"),
        divergence=(
            "Bounded by the RSSD gap on the row above, and bounded there for "
            "a reason that is about the SOURCE, not the work: a Call Report "
            "exists only for a US-supervised depository institution. The 16 "
            "rows cover the 16 members that have an RSSD. The remaining 29 "
            "members -- foreign banks, credit funds -- file no Call Report "
            "anywhere, so no fetch would produce one."),
    ),
    Mapping(
        "Syndicated-market context", PROBE,
        "the Shared National Credit Program annual report, fetched from the "
        "OCC and segmented into MongoDB as doc_type=snc_annual_report "
        "(Task 12)",
        lambda: mongo_count("document", {"doc_type": "snc_annual_report"}),
        divergence=(
            "THE FORMAT CHANGED FOR THE 2025 CYCLE. The attachment the "
            "agencies publish is now CHARTS ONLY -- 12 pages of exhibits -- "
            "and the qualitative narrative every prior edition carried "
            "(commitment volume commentary, the special-mention and "
            "classified discussion, leveraged-lending observations) moved to "
            "a separate press release that was not fetched. It is the right "
            "document from the right period and it satisfies this row's "
            "'for market context' purpose, but a consumer reaching for "
            "supervisory PROSE about the syndicated market will not find it "
            "here. Recorded in docs/known-issues.md §37."),
    ),
    Mapping(
        "Passage spans on agreement text", PROBE,
        "passages anchored to a Wave 18 credit agreement, each carrying "
        "start/end offsets into the stored text (Task 11)",
        wave18_passage_count,
        divergence=(
            "OFFSETS YES, EMBEDDINGS NO. These 12 passages carry the span "
            "offsets §C asks for and are resolvable against the stored "
            "document text -- `validators/syndicate.py`'s floor 1 "
            "re-extracts each filing and lands on them. They carry no "
            "`embedding` field: 37,305 of the estate's 37,389 passages do, "
            "and these 12 are among the 84 that do not (the other 72 are "
            "Wave 17's FinCEN-advisory passages -- known-issues §42, a "
            "separate gap this row does not own). Nothing in this product's "
            "§D needs a Similarity operator, so it is not a gap for THIS "
            "product -- but a corpus-wide vector search will silently skip "
            "every syndicated-agreement passage. Recorded in "
            "docs/known-issues.md §38."),
    ),
    Mapping(
        "Own position, rating, and workout posture", PROBE,
        "own_position rows -- our share, internal rating and workout posture "
        "per facility (Task 7), the internal half the peer never sees",
        lambda: pg_count("SELECT count(*) FROM {S}.own_position"),
        divergence=(
            "Five of the twelve syndicated facilities. The five are the ones "
            "the peer also holds a position in, which is what makes the "
            "divergence indicator of §D step 7 computable at all; a position "
            "on a facility no peer discloses would compare against nothing. "
            "A consumer asking for our position on the other seven gets "
            "nothing, and the catalog row does not say so."),
    ),
    Mapping(
        "votesOn edges", PROBE,
        "BOTH edge families, as the MINIMUM: syndicate membership "
        "(`cmns-col:isMemberOf`, 64 edges) and ex:votesOn (18). The "
        "generator's `amendment_vote_posture` is a sub-facet of this row "
        "and is deliberately NOT probed here: 18 ex:votePosture literals "
        "exist, but a COUNT of them proves nothing this row needs -- what "
        "matters is that they DIFFER, which conditions.py's `vote postures "
        "diverge` delegate recomputes live, and that they stay on the "
        "member node, which partition.py's member allowlist pins",
        lambda: min(
            fluree_predicate(
                "https://www.omg.org/spec/Commons/Collections/isMemberOf"),
            fluree_predicate(f"{EX}votesOn"),
        ),
        divergence=(
            "`ex:participatesIn` IS NOT MINTED, deliberately, and the row's "
            "first name therefore matches nothing in the ledger. Task 4 "
            "found that FIBO already carries the relation: "
            "`fibo-sec-dbt-dln:FinanceSyndicateMember` declares "
            "`cmns-col:isMemberOf allValuesFrom FinanceSyndicate`, and "
            "`fibo-be-fct-fct:Syndicate` independently declares the inverse "
            "`cmns-col:hasMember`. Minting an `ex:` synonym beside a bound "
            "FIBO property is the shadowing this estate refuses elsewhere. "
            "The commitment SHARE that a `participatesIn` edge attribute "
            "would have carried lives on the reified "
            "`ex:SyndicateParticipation` node instead -- a plain triple "
            "cannot carry an amount and its filed offset. Full argument and "
            "IRI in docs/ccf_dataprep_v2.md's Wave 18 binding block."),
    ),
    Mapping(
        "Bilateral disclosure envelopes", PROBE,
        "ex:DisclosureEnvelope nodes, each versioned and bound to one "
        "counterparty (Task 10). The ASYMMETRY of their scope sets is a "
        "condition, not a count -- conditions.py delegates it to "
        "validators/syndicate.py's envelopes_are_asymmetric",
        lambda: fluree_instances(f"{EX}DisclosureEnvelope"),
    ),
    Mapping(
        "Competition-law constraint rules", PROBE,
        "competition_law_rule rows -- the internal legal register the Policy "
        "Operator reads alongside the envelope (Task 7)",
        lambda: pg_count("SELECT count(*) FROM {S}.competition_law_rule"),
    ),
    Mapping(
        "Syndicate-desk local position tracker", PROBE,
        "SQLite syndicate_desk_tracker rows (Task 13) -- the departmental "
        "reach §D step 6 requires, and the only store this element is in",
        lambda: sqlite_count("SELECT COUNT(*) FROM syndicate_desk_tracker"),
    ),
    Mapping(
        "ProjectionPlan per perspective", PROBE,
        "syndicate_projection_plan rows (Task 15) -- agent / existing "
        "participant / prospective participant, the three perspectives §D "
        "step 3 distinguishes",
        lambda: pg_count("SELECT count(*) FROM {S}.syndicate_projection_plan"),
    ),
    Mapping(
        "Simulated peer fabric", PROBE,
        "the co-lender instance, as the MINIMUM of three independent reads "
        "of it: peer positions, peer product declarations, and counterparty "
        "identity nodes on the peer's own ledger (Tasks 14 and 15). A "
        "minimum, because a 'second CCF instance' that held positions but "
        "published no product, or published products but declared no "
        "identity, is not the thing §F asks for",
        lambda: min(
            peer_count("SELECT count(*) FROM {P}.peer_position"),
            peer_count("SELECT count(*) FROM {P}.peer_product_declaration"),
            peer_ledger_count(f"?s <{EX}lei> ?lei"),
        ),
        divergence=(
            "A TWO-STORE INSTANCE, not a mirror of ours. The peer runs its "
            "own Postgres schema and its own Fluree ledger, on a database "
            "and a ledger distinct from ours and guarded by "
            "`ccf.config.assert_distinct_fabrics()`. It provisions no "
            "SQLite, and its MongoDB database exists but holds zero "
            "collections -- so the peer contributes no document, no passage "
            "and no departmental element to anything. That is enough for "
            "what §F asks (position data plus one product under an "
            "envelope) and it is less than 'a second CCF instance' reads "
            "like. It also means `validators/syndicate.py`'s lineage floor "
            "derives its element population from two stores on our side "
            "having no counterpart at all on the peer's."),
    ),
]


# --------------------------------------------------------------------------
# large-exposure-rwa-concentration (Wave 19) -- the capstone
# --------------------------------------------------------------------------

def reg_o_narrowing_text() -> str:
    """Read the ONE authoritative sentence live from the loader that wrote
    it, rather than transcribing a second copy here. `loaders/
    load_regime_mongo.py::REG_O_NARROWING` is Task 10's own text, verified
    citation-by-citation against the fetched passages
    (`_verify_reg_o_citations`, made a permanent guard after Task 10's
    review found the FIRST version cited a cross-reference provision for a
    figure that provision's own text does not contain). Importing it means
    this manifest's divergence string can never say something different
    from what the loader actually asserts -- the two cannot drift apart
    the way two independently-typed copies of the same sentence always can.
    """
    from loaders.load_regime_mongo import REG_O_NARROWING

    return REG_O_NARROWING


def le_examiner_plan_full() -> int:
    """The examiner `large_exposure_projection_plan` row carrying BOTH
    `carries_methodology` and `carries_replay_attribution` TRUE -- §F's own
    words ("the examiner rendering carrying full methodology and replay
    attribution"), not merely three rows existing. Task 15's own review
    flagged these two columns as loaded into `Context` but read by no
    floor; this probe and `validators/conditions.py`'s matching direct
    count are what close that gap, not a new column."""
    return pg_count(
        "SELECT count(*) FROM {S}.large_exposure_projection_plan "
        "WHERE perspective = 'examiner' "
        "AND carries_methodology AND carries_replay_attribution")


LARGE_EXPOSURE = [
    Mapping(
        "Bank capital and exposure schedules", PROBE,
        "bank_capital rows -- real FDIC BankFind Call Report figures for "
        "the reporting bank, unit-converted and cross-checked against the "
        "filed tier1/RWA ratio at load time (Task 1)",
        lambda: pg_count("SELECT count(*) FROM {S}.bank_capital"),
    ),
    Mapping(
        "Advanced-approaches capital detail", DEFERRED,
        "FFIEC 101 was never fetched. What is loaded for this reporting "
        "bank -- Task 1's `bank_capital` -- is FFIEC Call Report Schedules "
        "RC-C/RC-R, bank-LEVEL FDIC BankFind data; FFIEC 101 (Regulatory "
        "Capital Reporting for Institutions Subject to the Advanced Capital "
        "Adequacy Framework) is filed at the CONSOLIDATED holding-company "
        "level, on a FR Y-9C capital base this estate also never loads. "
        "There is no holding-company-level advanced-approaches chain here "
        "for a Schedule A/RWA-detail row to attach to. Consequence: a "
        "request for advanced-approaches RWA density or an internal-models "
        "capital breakdown returns nothing -- every RWA figure in the "
        "estate (`bank_capital.risk_weighted_assets`) is the standardized, "
        "bank-level number.",
    ),
    Mapping(
        "Bank holding structure", PROBE,
        "fibo-be-oac-cctl:hasSubsidiary edges among the reporting bank's "
        "own Fluree nodes (Task 5) -- 852218 and 651448 under the holding "
        "company, keyed by lei/hasSubsidiary rather than a materialized "
        "RSSD literal on the node (ex:rssd was REMOVED from these nodes "
        "after a Task 5 regression; single-writer discipline resolves rssd "
        "from Postgres's reporting_bank instead)",
        lambda: fluree_predicate(
            f"{FIBO}BE/OwnershipAndControl/CorporateControl/hasSubsidiary"),
    ),
    Mapping(
        "Regime rule text", PROBE,
        "`doc_type: regime_text` MongoDB documents -- 31 documents / 464 "
        "passages across PRA Rulebook, CRR and Regulation O (12 CFR 215), "
        "each RegimeVersion's citesProvision resolving to one of these",
        lambda: mongo_count("document", {"doc_type": "regime_text"}),
        divergence=reg_o_narrowing_text(),
    ),
    Mapping(
        "Connected-counterparty definitions", PROBE,
        "BOTH halves, as the MINIMUM of the two: the regime text itself "
        "(`doc_type: regime_text` in MongoDB, `L`) and the operational "
        "edges it grounds (`ex:connectedTo`, 184 edges over 26 control "
        "components, `R`) -- §C assigns this row to two stores, and a "
        "probe of either alone would green a half-loaded row",
        lambda: min(
            mongo_count("document", {"doc_type": "regime_text"}),
            fluree_predicate(f"{EX}connectedTo"),
        ),
    ),
    Mapping(
        "Passage spans on regime text", PROBE,
        "passages carrying a `regime` field in {reg-o, crr, pra}, each "
        "resolvable to a start/end offset into its stored document text "
        "(Task 4, fix round 1 repaired a roman-numeral sub-marker bug that "
        "had duplicated 78 reg-o provision labels)",
        lambda: mongo_count("passage", {"regime": {"$in":
                                                    ["reg-o", "crr", "pra"]}}),
    ),
    Mapping(
        "Corporate family and control edges", COVERED,
        "§C says so itself: 'inherited from [[corporate-family-tree]]' -- "
        "conditions.py's corporate-family-tree checks (ownership graph "
        "edges, cross-shareholding cycles) already assert this population, "
        "not duplicated here",
    ),
    Mapping(
        "Beneficial ownership", COVERED,
        "§C says so itself: 'inherited from "
        "[[kyc-refresh-beneficial-ownership]]' -- conditions.py's "
        "kyc-refresh-beneficial-ownership checks already assert the "
        "ownership declarations this row names",
    ),
    Mapping(
        "Exposure by facility and obligor", COVERED,
        "§C says so itself: 'inherited from [[credit-exposure-rollup]]' -- "
        "conditions.py's credit-exposure-rollup checks already assert the "
        "facility/exposure population this row names",
    ),
    Mapping(
        "Collateral and mitigation", COVERED,
        "§C says so itself: 'inherited from "
        "[[collateral-and-setoff-coverage]]' -- conditions.py's "
        "collateral-and-setoff-coverage checks already assert the "
        "collateral population; validators/large_exposure.py's floors 4/5 "
        "recompute POST-HAIRCUT collateral from it live rather than "
        "reading a stored mitigation figure",
    ),
    Mapping(
        "Insider and related-party designations", PROBE,
        "ex:InsiderDesignation node carrying two designatedPerson targets "
        "(Task 8) -- the invented insider (CLAUDE.md rule 3: a real DEF "
        "14A names a real living person, so the person here is synthetic "
        "— engineered) and Digital Turbine, Inc. as the real related "
        "interest, citing a real 2026 JPMorgan proxy sentence naming "
        "Regulation O as the compliance regime",
        lambda: fluree_instances(f"{EX}InsiderDesignation"),
    ),
    Mapping(
        "economicallyDependentOn edges", PROBE,
        "4 ex:economicallyDependentOn edges (Task 7), each carrying "
        "assertedBy/assertedOn/dependencyBasis -- control-basis grouping "
        "alone misses every one of them (26 components -> 23 once the "
        "'both' connection_basis is applied)",
        lambda: fluree_predicate(f"{EX}economicallyDependentOn"),
    ),
    Mapping(
        "Internal limit envelope and sub-limits", PROBE,
        "the one ex:LimitEnvelope node (Task 9) -- the internal 5.0% "
        "appetite, re-derived independently at load time against both the "
        "largest control group (5.4148%) and the Vertiv/TransDigm "
        "dependency-edge band (4.936%, 7.602%]",
        lambda: fluree_instances(f"{EX}LimitEnvelope"),
    ),
    Mapping(
        "Regime version history with effective dates", PROBE,
        "3 ex:RegimeVersion nodes (Task 9) -- CRR from 2014-01-01, PRA "
        "taking over UK large exposures from 2022-01-01 (assimilated CRR "
        "articles omitted the same day), Reg O from 2026-01-01 -- each "
        "required by the loader's own assert_regime_anchoring to carry "
        ">= 1 citesProvision resolving to a live passage",
        lambda: fluree_instances(f"{EX}RegimeVersion"),
    ),
    Mapping(
        "Methodology documentation", PROBE,
        "2 `doc_type: methodology` MongoDB documents (Task 10) -- "
        "concentration methodology and replay-attribution methodology, "
        "both synthetic — internal, both CITING the regime_text passages "
        "above by passage_id rather than restating their text",
        lambda: mongo_count("document", {"doc_type": "methodology"}),
    ),
    Mapping(
        "Risk-department limit workbook", PROBE,
        "SQLite `large_exposure_limit_workbook` rows (Task 11) -- NOT "
        "`risk_limit_workbook`, an unrelated Wave 7 table with 16 rows and "
        "an incompatible schema the brief's literal name collided with; "
        "every note read at review and confirmed to disclaim a regulatory "
        "breach explicitly rather than assert one",
        lambda: sqlite_count(
            "SELECT COUNT(*) FROM large_exposure_limit_workbook"),
    ),
    Mapping(
        "ProjectionPlan per perspective", PROBE,
        "3 large_exposure_projection_plan rows (Task 12), pairwise "
        "DISTINCT elements_included sets (conditions.py's own delegated "
        "floor recomputes the distinctness live) -- this probe is the "
        "narrower claim that the EXAMINER row specifically carries full "
        "methodology and replay attribution, the words §F actually uses",
        le_examiner_plan_full,
    ),
]


# --------------------------------------------------------------------------
# mnpi-wall-enforcement (Wave 7) -- probes
#
# Every probe below is scoped to the population the ROW names, not to the
# table the row happens to live in. A count of "all EDGAR filings" or "all
# research notes" would pass whatever happened to this product's ten issuers,
# which is the defect this file exists to catch.
# --------------------------------------------------------------------------

def mnpi_issuer_leis() -> list[str]:
    """The issuers this product is actually about -- derived, never listed.

    Wave 7 built the layer around whichever entities `deal` carries, so the
    issuer set is a fact of the estate rather than a constant here. Hard-coding
    ten LEIs would keep passing after a reload moved them.
    """
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT DISTINCT lei FROM "{PG_SCHEMA_V2}".deal')
        return [r[0] for r in cur.fetchall()]


def mnpi_edgar_filings() -> int:
    """10-K / 10-Q / 8-K documents FOR THIS PRODUCT'S ISSUERS.

    Â§C sources this row from EDGAR and assigns it to MongoDB as `L`. The form
    lives under `form`, NOT `doc_type` -- `doc_type` is null on all 178 EDGAR
    documents, so a probe keyed on it returns zero while the filings sit right
    there. Measured 2026-09-20: 145 filings estate-wide, 37 for these issuers.
    """
    from ccf.config import mongo_db

    return mongo_db(write=False)["document"].count_documents({
        "form": {"$in": ["10-K", "10-Q", "8-K"]},
        "lei": {"$in": mnpi_issuer_leis()},
    })


def mnpi_research_both_states() -> int:
    """The SMALLER of (published, draft) research-note counts.

    Â§C's row is "Research notes, published and draft" -- both states, and the
    product's whole demonstration is that one principal sees one state and not
    the other. A plain count of 42 notes would stay green if every draft were
    published tomorrow, which would silently destroy the demonstration. Taking
    the minimum makes the probe fall to zero the moment either state empties.
    """
    from ccf.config import mongo_db

    notes = mongo_db(write=False)["research_note"]
    return min(notes.count_documents({"status": "published"}),
               notes.count_documents({"status": "draft"}))


def mnpi_classified_documents() -> int:
    """Documents carrying a classification, across the MongoDB collections
    Â§C's `P` row covers. The MNPI-tag half of that row is recorded as a
    divergence below -- it is real, and it is not in MongoDB."""
    from ccf.config import mongo_db

    db = mongo_db(write=False)
    has = {"classification": {"$exists": True, "$ne": None}}
    return sum(db[c].count_documents(has)
               for c in ("document", "research_note", "memorandum"))


MNPI_WALL = [
    Mapping(
        "Issuer entity and family", PROBE,
        "deal issuers that RESOLVE through the internal<->LEI crosswalk -- "
        "§C inherits this row from corporate-family-tree, so the claim is "
        "not that entities exist but that this product's issuers join to "
        "them; falls to zero if the crosswalk stops covering them",
        lambda: pg_count(
            "SELECT count(*) FROM (SELECT DISTINCT d.lei FROM {S}.deal d "
            "JOIN {S}.crosswalk x ON x.lei = d.lei) t"),
    ),
    Mapping(
        "Public filings and narrative text", PROBE,
        "10-K/10-Q/8-K documents in MongoDB FOR THIS PRODUCT'S ISSUERS "
        "(37 of 145 estate-wide) -- keyed on `form`, because `doc_type` is "
        "null on every EDGAR document",
        mnpi_edgar_filings,
    ),
    Mapping(
        "Regulation FD disclosure events", PROBE,
        "ex:RegFDEvent nodes -- REGFD-000, the catalog's only WIDENING "
        "supersession trigger",
        lambda: fluree_instances(f"{EX}RegFDEvent"),
        divergence=(
            "TWO ways, both load-bearing for anyone building against this "
            "row. (1) PROVENANCE: §C calls this row `public`, sourced from "
            "8-K Item 7.01 and Reg FD filings. The node is `synthetic -- "
            "internal`: Wave 7's generator invented it, picking whichever "
            "issuer sorts first and a date 45 days before the run. No filing "
            "underlies it. (2) IT DESIGNATES NOTHING. The event names an "
            "issuer and an instant and no content whatsoever -- zero incoming "
            "edges in Fluree, zero literals mentioning it, no Postgres column "
            "referencing it, each measured with a positive control on "
            "2026-09-20. The loader drops even the generator's prose "
            "description, so nothing identifying disclosed material has ever "
            "been in a store. A consumer must therefore treat the event as a "
            "dated flag on the issuer, NOT as a release of identified "
            "records. Full measurement: contrib/ccf-dataprep/"
            "cp-17-regfd-000-designates-nothing-outcome-b.md."),
    ),
    Mapping(
        "Insider transaction and blackout windows", DEFERRED,
        "HALF the row, and the missing half is the one the product needs. "
        "Form 4 insider transactions exist as 319 ex:OpportunitySignal nodes "
        "labelled insider_activity_form4 (Wave 16), NOT as the Fluree `T` "
        "element §C describes. Issuer BLACKOUT WINDOWS do not exist at all: "
        "no Fluree type or predicate carries one. (ex:InsiderDesignation is "
        "a Regulation O related-persons designation from Wave 19, a lending "
        "restriction -- not a trading blackout, and not this row.) Nothing "
        "in the estate answers 'was this issuer in a blackout on date X'.",
    ),
    Mapping(
        "Public market data", DEFERRED,
        "NO ISSUER-LEVEL MARKET DATA EXISTS. §C wants FINRA TRACE and public "
        "price sources per issuer, as `E`,`T`. The three market tables in "
        "ccf_v2 are all macro-level and NONE carries an `lei` column: "
        "market_oas_series is rating-band OAS from FRED (3,930 rows), "
        "intraday_tick is the Treasury curve by tenor (11,700), "
        "fx_intraday_tick is currency pairs. Control: 25 other ccf_v2 tables "
        "do carry `lei`, so the column's absence here is a fact about these "
        "three tables, not about how they were inspected. A trader "
        "perspective therefore has no per-issuer price series to project.",
    ),
    Mapping(
        "Adverse media and public news", PROBE,
        "gdelt_mention rows FOR THIS PRODUCT'S ISSUERS (699 of 951 "
        "estate-wide) -- Wave 11b's GDELT fetch, reused whole; this product "
        "mints no adverse-media row of its own",
        lambda: pg_count(
            "SELECT count(*) FROM {S}.gdelt_mention g "
            "JOIN {S}.deal d ON d.lei = g.lei"),
    ),
    Mapping(
        "Wall state assertions", PROBE,
        "ex:WallCrossing nodes -- 4, of which WALL-000 carries the "
        "engineered nine-day recording lag (validFrom 2026-03-07, "
        "assertedAt 2026-03-16) that makes the bitemporal `as_of` "
        "reconstruction demonstrable; the other three lag 0-1 days",
        lambda: fluree_instances(f"{EX}WallCrossing"),
    ),
    Mapping(
        "Deal pipeline and engagement records", PROBE,
        "deal rows (32 over 10 issuers) -- the pipeline itself; "
        "conditions.py separately floors the MNPI-tagged SUBSET at 10, "
        "which is a different quantity and does not stand in for this row",
        lambda: pg_count("SELECT count(*) FROM {S}.deal"),
    ),
    Mapping(
        "MNPI-bearing interaction records", PROBE,
        "interaction rows WITH mnpi_bearing true (18) -- the flagged subset, "
        "not the table; a count of all interactions would stay green if "
        "every MNPI flag were cleared",
        lambda: pg_count(
            "SELECT count(*) FROM {S}.interaction WHERE mnpi_bearing"),
    ),
    Mapping(
        "Research notes, published and draft", PROBE,
        "the SMALLER of the published (33) and draft (9) counts, so the "
        "probe fails if either STATE empties -- §C names both, and the "
        "product turns on one principal seeing one and not the other",
        mnpi_research_both_states,
        divergence=(
            "No issuer holds BOTH a draft and a published note. Measured "
            "2026-09-20: 42 notes over 10 issuers, two of them draft-only "
            "(Charter, 5; 5299001XWB5V3B5IPN93, 4) and the other eight "
            "published-only. The row is satisfied -- both states exist in the "
            "corpus -- but §F's '>= 1 case where restricted documents would "
            "have altered similarity ranking' is NOT reachable on any single "
            "issuer, because no issuer has a restricted note that could have "
            "competed with its own published ones. On SP Plus, the product's "
            "own worked issuer, that ranking difference is zero BY "
            "CONSTRUCTION rather than by measurement."),
    ),
    Mapping(
        "Research embargo windows", PROBE,
        "ex:EmbargoWindow nodes (9) -- one per embargoed draft, every "
        "window now expired and every note still `draft`, so the "
        "embargo-expiry supersession trigger is declared but not observable",
        lambda: fluree_instances(f"{EX}EmbargoWindow"),
    ),
    Mapping(
        "Trading positions", PROBE,
        "position rows (10, one per issuer) -- the trader perspective's `E` "
        "element",
        lambda: pg_count("SELECT count(*) FROM {S}.position"),
    ),
    Mapping(
        "Control-room restricted list", COVERED,
        "conditions.py floors this at 3 in the DEPARTMENTAL store "
        "(mnpi-wall-enforcement / 'restricted list in the DEPARTMENTAL "
        "store'); 4 SQLite restricted_list rows, none removed",
    ),
    Mapping(
        "ProjectionPlan definitions per perspective", COVERED,
        "conditions.py floors this at 3 ('test principals with "
        "ProjectionPlans'); 3 projection_plan rows, one per perspective",
    ),
    Mapping(
        "Document classification and MNPI tags", PROBE,
        "documents carrying a classification across document, research_note "
        "and memorandum (282 on 2026-09-20: 200 documents, 42 research "
        "notes, 40 memoranda) -- the classification half of the row",
        mnpi_classified_documents,
        divergence=(
            "HALF this row is in a different store, and deliberately so. "
            "§C assigns 'Document classification and MNPI tags' to MongoDB "
            "as `P`. Classification is there. MNPI TAGS ARE NOT: no MongoDB "
            "collection carries an mnpi field at all. The tagging lives in "
            "Postgres, on deal.mnpi_bearing (11 of 32) and "
            "interaction.mnpi_bearing (18) -- which is where single-writer "
            "discipline puts it, since both are Postgres-owned row "
            "attributes. Duplicating them into MongoDB to satisfy the row "
            "literally would violate the partition rule this validator's "
            "sibling enforces. A consumer resolving MNPI status must join to "
            "Postgres, not read a Mongo field."),
    ),
]


MANIFEST: dict[str, list[Mapping]] = {
    "aml-typology-match": AML_TYPOLOGY,
    "collateral-and-setoff-coverage": COLLATERAL,
    "corporate-family-tree": FAMILY_TREE,
    "counterparty-reference-snapshot": COUNTERPARTY,
    "covenant-cross-reference": CROSS_REFERENCE,
    "covenant-in-force-as-of": IN_FORCE,
    "ib-opportunity-synthesis": IB_OPPORTUNITY,
    "large-exposure-rwa-concentration": LARGE_EXPOSURE,
    "mnpi-wall-enforcement": MNPI_WALL,
    "syndicated-lending-co-lender": SYNDICATED_CO_LENDER,
}


# --------------------------------------------------------------------------
# running
# --------------------------------------------------------------------------

@dataclass
class Outcome:
    product: str
    element: str
    store: str
    state: str
    ok: bool
    detail: str
    divergence: str | None = None

    def render(self) -> str:
        mark = {
            PROBE: "PASS" if self.ok else "FAIL",
            COVERED: "COVER",
            WAIVED: "WAIVE",
            DEFERRED: "GAP",
        }[self.state]
        line = (f"  [{mark:<5}] {self.store:<9} {self.element[:52]:<52} "
                f"{self.detail[:70]}")
        if not self.divergence:
            return line
        body = textwrap.fill(" ".join(self.divergence.split()), width=94,
                             initial_indent=" " * 12,
                             subsequent_indent=" " * 12)
        return f"{line}\n{' ' * 12}SATISFIED WITH DIVERGENCE:\n{body}"


def run_product(product: str) -> tuple[list[Outcome], list[CatalogRow]]:
    """Returns (outcomes, unaccounted rows)."""
    rows = read_catalog(product)
    mappings = MANIFEST.get(product)
    if mappings is None:
        return [], rows

    outcomes: list[Outcome] = []
    used: set[int] = set()

    for mp in mappings:
        # CASE-INSENSITIVE, for the same reason the match is a substring at
        # all: the vault patches §C prose in place, and a capitalisation
        # tweak upstream should not read here as a missing element.
        #
        # It is NOT a licence to stop reading the spec. Case-insensitive
        # matching hides semantic drift -- a row whose NAME survived while
        # its MEANING moved still matches, and matches silently. So the
        # ambiguity guard below stays an error rather than a warning, and
        # any row whose sense has shifted is recorded as a `divergence`
        # rather than mapped quietly. (known-issues §22 fixed the same
        # case-sensitivity on the §C HEADING match; this is the row half.)
        needle = mp.match.casefold()
        hits = [i for i, r in enumerate(rows) if needle in r.element.casefold()]
        if len(hits) != 1:
            raise RuntimeError(
                f"{product}: mapping {mp.match!r} matched {len(hits)} catalog "
                f"rows, expected exactly 1. The spec's §C wording has moved "
                f"under this manifest -- re-read it before adjusting the match."
            )
        idx = hits[0]
        if idx in used:
            raise RuntimeError(f"{product}: two mappings claim row {idx}")
        used.add(idx)
        row = rows[idx]

        if mp.state == PROBE:
            assert mp.probe is not None
            n = mp.probe()
            ok = n > 0
            detail = f"{n} found — {mp.detail}" if ok else f"ZERO — {mp.detail}"
        elif mp.state == DEFERRED:
            ok, detail = False, mp.detail
        else:
            ok, detail = True, mp.detail

        outcomes.append(Outcome(product, row.element, row.store, mp.state, ok,
                                detail, mp.divergence))

    unaccounted = [r for i, r in enumerate(rows) if i not in used]
    return outcomes, unaccounted


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--product", help="run one product only")
    args = ap.parse_args()

    products = [args.product] if args.product else PRODUCTS
    if args.product and args.product not in PRODUCTS:
        print(f"unknown product: {args.product}")
        return 2

    print("SPEC COVERAGE — asserts each store holds the elements its §C names")
    print(f"  catalog source: {VAULT}\n")

    all_out: list[Outcome] = []
    unmapped: list[tuple[str, int]] = []
    unaccounted_total = 0
    catalog_total = 0

    for product in products:
        rows = read_catalog(product)
        catalog_total += len(rows)
        outcomes, unaccounted = run_product(product)

        if product not in MANIFEST:
            unmapped.append((product, len(rows)))
            continue

        print(f"  {product}")
        for o in outcomes:
            print(o.render())
        for r in unaccounted:
            print(f"  [UNMAP]  {r.store:<9} {r.element[:52]:<52} "
                  f"no mapping — catalog row is unaccounted for")
        unaccounted_total += len(unaccounted)
        all_out += outcomes
        print()

    if unmapped:
        print("  NOT YET MAPPED — these products' catalog rows are unchecked\n")
        for product, n in unmapped:
            print(f"  [UNMAP]  {product:<44} {n} catalog rows")
        print()

    probes = [o for o in all_out if o.state == PROBE]
    failed = [o for o in probes if not o.ok]
    gaps = [o for o in all_out if o.state == DEFERRED]
    waived = [o for o in all_out if o.state == WAIVED]
    covered = [o for o in all_out if o.state == COVERED]
    unmapped_rows = sum(n for _, n in unmapped)

    print(f"  {len(all_out)} of {catalog_total} catalog rows accounted for "
          f"({len(probes) - len(failed)} probed clean · {len(covered)} covered "
          f"by conditions.py · {len(waived)} waived · {len(gaps)} deferred)")
    if unmapped_rows or unaccounted_total:
        print(f"  {unmapped_rows + unaccounted_total} rows UNCHECKED "
              f"({unmapped_rows} in unmapped products, "
              f"{unaccounted_total} unmapped rows in mapped products)")

    if failed:
        print("\n  A failed probe means the element is NOT in the store its "
              "spec assigns it to.")
        print("  Establish which store owns it before touching the probe.")
    if gaps:
        print("\n  A GAP is a real, named absence. Do not waive one to clear "
              "this run —")
        print("  a waiver is a claim about the source, never about appetite "
              "for the work.")

    bad = bool(failed or gaps or unmapped_rows or unaccounted_total)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
