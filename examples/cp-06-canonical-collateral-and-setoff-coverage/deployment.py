"""This deployment's own values — the other half of ``produce.py``.

[ADAPT] everything here. [MECHANISM] nothing.

``produce.py`` beside this file is CCF's calls and names none of the vocabulary
below. This file names all of it and makes no fabric call the spine does not.
Delete ``ccf_config.yaml`` and nothing here has anything left to interpret,
which is the No-Hardcoding Rule (CLAUDE.md §6.4) being structural rather than
aspirational.

**Its boundaries are ruled** (`D-IMPL-315`, `D-IMPL-343`): vocabulary, source
access, the envelopes, the debt reading and the product's own gate. No boot,
no effective-request derivation, no ingest loop, no binder, no record, no
serve — those are the paved road's.

## The ingestion-order contract, and why it is a contract

Two kinds of envelope reach L2 from here: **edge envelopes**, carrying two
endpoint references and a predicate and deliberately no attributes, and
**node envelopes**, carrying one node's attributes. **Edges are returned
FIRST and nodes LAST, and that order is load-bearing** (`D-IMPL-316`): a
claim carrying fewer attributes at the same URI supersedes the richer one
rather than merging into it, so an edge envelope arriving after a node
envelope erases that node's attributes and the payload then serves a node
with no valuation, no haircut and no category, with nothing raised. The
road ingests in the order this module returns.

## The commitment is fabric state (`CP-SPEC-006C` §0.1)

The specimen handed its Π the facility's commitment through a closure over
acquisition — a value the graph did not carry and replay could not
reconstruct from the snapshot. Here the facility node carries it as an
attribute (declared under ``resolution.entity_rules`` beside the others), Π
reads it off the governed view, and the product's own gate refuses a facility
the view does not know the size of. Nothing substitutes a zero.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

import acquisition
from ccf.graph.protocols import GraphView
from ccf.controlplane.artifacts import DebtProfile, HalfLifeTable
from ccf.halflife.assessment import DebtFactors
from ccf.halflife.debt import DebtAssessment, FreshnessScorer, Observation, assess_debt
from ccf.products.product import AcquisitionContext, AssessmentContext
from ccf.signal.envelope import SignalEnvelope, SourceIdentity
from projection import NOT_EVALUABLE

HERE = Path(__file__).parent

#: The request parameters this deployment reads by name — `CP-SPEC-006C` §B.2.
FACILITY = "facility_id"
BORROWER_SCOPE = "borrower_scope"
APPLY_HAIRCUTS = "apply_haircuts"
INCLUDE_SETOFF = "include_setoff"
JURISDICTION_BASIS = "jurisdiction_basis"
SHARED_COLLATERAL = "shared_collateral"

#: The two sources `ccf_environment.yaml` declares, by the names it declares.
SOURCE_GRAPH = "collateral_graph"
SOURCE_ATTRIBUTES = "collateral_attributes"

#: How a node's kind is carried through a `Mapping[str, str]` claim.
KIND = "node_kind"

#: Which λ_c class each collateral category decays under. The categories are
#: the source's; the classes are `ccf_config.yaml`'s. One mapping, here, so a
#: new category is a one-line edit rather than a search.
DECAY_CLASS_BY_CATEGORY = {
    "marketable_securities": "marketable_securities_valuation",
    "real_property": "real_property_appraisal",
    "receivables": "real_property_appraisal",
    "equipment": "real_property_appraisal",
    "inventory": "real_property_appraisal",
}

#: The plan identity prefix — this tree's own, never the specimen's (`CSCC-G16`).
PLAN_ID_PREFIX = "cp-06-canonical.collateral-coverage"


def config() -> Mapping[str, Any]:
    """The single deployment document, parsed — read here only for a value
    the paved road does not hand this module (the plan-id convention)."""
    document: Mapping[str, Any] = yaml.safe_load(
        (HERE / "ccf_config.yaml").read_text(encoding="utf-8")
    )
    return document


def plan_id(subject: str) -> str:
    """Π's identity for one facility. Recorded on the product and in replay."""
    return f"{PLAN_ID_PREFIX}/{subject}"


# ---------------------------------------------------------------------------
# acquire — read the two sources at the EFFECTIVE parameters; hand back claims.
# ---------------------------------------------------------------------------


def acquire(context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
    """Open both sources for the facility the effective request names; return every claim.

    ``include_setoff`` is the EFFECTIVE value — the class default where the
    caller omitted it, the caller's value where it is in bounds — handed here
    by the resolver through the declared seam (`D-IMPL-343` R-4), so the
    deposits a refused request never gets to see are never read and never
    enter the debt denominator. A refused request never reaches this
    function, by the seam's ordering rather than by a check here.
    """
    effective = context.request.parameters
    coverage = acquisition.acquire(
        facility_id=str(effective[FACILITY]),
        include_setoff=bool(effective[INCLUDE_SETOFF]),
        graph=context.sources[SOURCE_GRAPH],
        attributes=context.sources[SOURCE_ATTRIBUTES],
    )
    return envelopes(coverage, tenant_id=context.tenant_id, at=context.instant)


# ---------------------------------------------------------------------------
# From a read to fabric state — one envelope per dated claim.
# ---------------------------------------------------------------------------


def _pledge_ref(pledge: acquisition.Pledge) -> str:
    """The reified pledge's identity — the PAIR, never either endpoint."""
    return f"PLEDGE~{pledge.facility_id}~{pledge.asset_id}"


def _node(entity_ref: str, kind: str, scope: str, *, tenant_id: str,
          at: datetime, **attributes: Any) -> SignalEnvelope:
    """One node's attributes, under the fabric's own vocabulary.

    ATTRIBUTED, therefore LAST. See the module docstring: this claim is the one
    that must survive, and it only survives if nothing thin arrives after it.
    """
    payload = {"node_ref": entity_ref, "entity_ref": entity_ref,
               "ref": entity_ref, KIND: kind, "borrower_scope": scope}
    payload.update({k: ("" if v is None else str(v)) for k, v in attributes.items()})
    return SignalEnvelope(
        tenant_id=tenant_id, envelope_id=f"node/{kind}/{entity_ref}",
        source=SourceIdentity(system_id="collateral_graph"),
        ingestion_timestamp=at, observed_time=at, raw_payload=payload)


def _edge(subject: str, predicate: str, obj: str, *, tenant_id: str,
          at: datetime, ordinal: int) -> SignalEnvelope:
    """One typed edge, carrying NO attributes. Must precede either endpoint's node."""
    return SignalEnvelope(
        tenant_id=tenant_id, envelope_id=f"edge/{ordinal}",
        source=SourceIdentity(system_id="collateral_graph"),
        ingestion_timestamp=at, observed_time=at,
        raw_payload={"subject_ref": subject, "subject_uri": subject,
                     "object_ref": obj, "object_uri": obj, "predicate": predicate})


def envelopes(coverage: acquisition.Coverage, *, tenant_id: str,
              at: datetime) -> tuple[SignalEnvelope, ...]:
    """Every edge, then every node — one tuple, in the order the road ingests."""
    scope = coverage.borrower_lei or coverage.facility_id
    edges: list[SignalEnvelope] = []
    nodes: list[SignalEnvelope] = []

    def edge(s: str, p: str, o: str) -> None:
        edges.append(_edge(s, p, o, tenant_id=tenant_id, at=at, ordinal=len(edges)))

    all_pledges = [*coverage.pledges,
                   *(p for shared in coverage.sharing.values() for p in shared)]
    for pledge in all_pledges:
        edge(pledge.facility_id, "securedBy", pledge.asset_id)
        edge(_pledge_ref(pledge), "pledgedFacility", pledge.facility_id)
        edge(_pledge_ref(pledge), "pledgedAsset", pledge.asset_id)
    for deposit in coverage.deposits:
        edge(deposit.account_id, coverage.reached_by.get(deposit.account_id,
                                                         "setOffAgainst"),
             coverage.facility_id)
    for filing in coverage.filings:
        edge(coverage.facility_id, "amendedBy", filing.filing_number)

    # THE ANCHOR'S OWN NODE CARRIES ITS COMMITMENT — the one attribute this
    # successor adds to the specimen's graph (`CSCC-G14`). A facility the
    # source does not know the size of carries an empty commitment, which Π
    # reports as absent and the gate refuses.
    nodes.append(_node(coverage.facility_id, "facility", scope, tenant_id=tenant_id,
                       at=at, label=coverage.borrower_name,
                       commitment=coverage.commitment,
                       provenance="ccf_v2.facility"))
    for facility in coverage.sharing:
        nodes.append(_node(facility, "facility", scope, tenant_id=tenant_id, at=at,
                           label="sharing facility", provenance="ccf_v2.facility"))
    for pledge in all_pledges:
        nodes.append(_node(
            _pledge_ref(pledge), "pledge", scope, tenant_id=tenant_id, at=at,
            label=f"{pledge.facility_id} / {pledge.asset_id}",
            lien_position=pledge.lien_position,
            provenance="fibo-v2 ex:CollateralPledge"))
    positions = {p.asset_id: p.lien_position for p in coverage.pledges}
    for asset_id, asset in sorted(coverage.assets.items()):
        nodes.append(_node(
            asset_id, "asset", scope, tenant_id=tenant_id, at=at,
            label=asset.description, category=asset.category,
            valuation=asset.valuation, valuation_date=asset.valuation_date,
            valuation_age_days=asset.valuation_age_days, haircut=asset.haircut,
            lien_position=positions.get(asset_id), provenance=asset.provenance))
    for deposit in coverage.deposits:
        nodes.append(_node(
            deposit.account_id, "deposit", scope, tenant_id=tenant_id, at=at,
            balance=deposit.balance, currency=deposit.currency,
            jurisdiction=deposit.jurisdiction,
            setoff_contractual=str(deposit.setoff_contractual).lower(),
            setoff_enforceable=str(deposit.setoff_enforceable).lower(),
            provenance="ccf_v2.deposit_account"))
    for filing in coverage.filings:
        nodes.append(_node(
            filing.filing_number, "ucc_filing", scope, tenant_id=tenant_id, at=at,
            filing_number=filing.filing_number, filed_on=filing.filed_on,
            lapses_on=filing.lapses_on, filing_status=filing.filing_status,
            debtor_of_record=filing.debtor_of_record,
            amendment_action=" | ".join(a for a, _ in filing.amendments),
            label=f"terminated {filing.terminated_on}" if filing.terminated_on
            else "in force", provenance="ucc/fl-registry"))
    return (*edges, *nodes)


# ---------------------------------------------------------------------------
# assess — D_c over what the fabric actually holds for this determination.
# ---------------------------------------------------------------------------


def assess(context: AssessmentContext) -> DebtAssessment:
    """`D_c` over the operator view, with the BOOTED λ_c table and profile.

    The table and the D_c bands are the artifacts the paved road hands here —
    the exact documents the pins record, never a second parse of the config —
    and the instant is the resolver's own decision instant, which for this
    class (declaring none apart) is the asked instant.
    """
    assert context.half_life is not None and context.profile is not None
    return debt(context.view, now=context.decided_at, half_life=context.half_life,
                profile=context.profile)


def debt(view: GraphView, *, now: datetime, half_life: HalfLifeTable,
         profile: DebtProfile) -> DebtAssessment:
    """The specimen's method, unchanged in substance: freshness is the factor that moves.

    §E's valuation spread is one day against one year inside a single
    product, so a real-property appraisal and a marketable-securities mark
    decay under different curves. The SDK's own `FreshnessScorer` reads the
    declared λ_c table; this deployment supplies the observations and their
    classes and computes no curve of its own. Completeness is the share of
    pledged assets the attribute leg priced — a pledge whose asset has no
    valuation cannot contribute coverage, and counting it as covered is the
    failure this product exists to surface.
    """
    entities = list(view.entities)
    assets = [r for r in entities if r.claim.attributes.get(KIND) == "asset"]
    observations = [
        Observation(
            observation_type=DECAY_CLASS_BY_CATEGORY.get(
                r.claim.attributes.get("category", ""), "real_property_appraisal"),
            observed_at=now - timedelta(
                days=int(r.claim.attributes.get("valuation_age_days") or 0)),
            subject=r.claim.entity_uri)
        for r in assets
    ]
    scorer = FreshnessScorer(table=half_life, risk_sensitivity=profile.risk_sensitivity)
    priced = [r for r in assets if r.claim.attributes.get("valuation")]
    completeness = (Decimal(len(priced)) / Decimal(len(assets))
                    if assets else Decimal(1))
    return assess_debt(
        DebtFactors(
            freshness=scorer.score(observations, now=now) if observations else Decimal(1),
            completeness=completeness,
            semantic_consistency=Decimal(1),
        ),
        profile=profile,
    )


# ---------------------------------------------------------------------------
# gate — the product's own declared gate: `cp-06-canonical.over-allocation-guard`.
# ---------------------------------------------------------------------------

NO_COMMITMENT = (
    "no facility commitment in the admitted view: the anchor resolved to nothing"
    " this principal may see, or the facility record carries no commitment"
)


def coverage_gate(*, candidate: Any, evidence: object = None) -> str | None:
    """Two refusals in one governed verdict, stamped with the declared gate identity.

    * **no commitment** — Π found no facility node for the anchor in the
      admitted view, or one with no commitment. The anchor resolved to
      nothing, to a facility the source does not size, or to one the policy
      envelope suppressed (a scope the caller does not hold yields an EMPTY
      graph, never a redacted one); the text is the same for all three.
    * **over-allocation** — §D's fourth validation gate: the sum of
      allocations against any single asset must not exceed its haircut value.
      Π computes the breach; this gate decides what it means, which is why the
      finding is data and this is a verdict.
    """
    payload = candidate.payload
    if payload["commitment"] is None or payload["coverage"]["coverage_ratio"] == NOT_EVALUABLE:
        return NO_COMMITMENT
    over = payload["findings"]["over_allocated_assets"]
    if over:
        return (
            f"over-allocation: {len(over)} asset(s) allocated beyond their"
            f" haircut value, first {over[0]['uri']!r}"
            f" ({over[0]['allocated']} > {over[0]['haircut_value']})"
        )
    return None
