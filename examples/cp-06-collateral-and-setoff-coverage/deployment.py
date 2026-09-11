"""This deployment's own values — the other half of ``produce.py``.

[ADAPT] everything here. [MECHANISM] nothing.

``produce.py`` beside this file is CCF's calls and names none of the vocabulary
below. Delete ``ccf_config.yaml`` and nothing here has anything left to
interpret, which is the No-Hardcoding Rule (CLAUDE.md §6.4) being structural
rather than aspirational.

Boundaries are ruled (`D-IMPL-315`): vocabulary, source access and admission.
No binder, no gates, no replay record, no serve.

## The ingestion-order contract

Two kinds of envelope reach L2 from here: **edge** envelopes carrying two
endpoint references and a predicate and no attributes, and **node** envelopes
carrying one node's attributes.

**Edges are ingested FIRST and nodes LAST, and the order is load-bearing.**
The last claim at a URI wins and does not merge, so an edge envelope arriving
after a node envelope erases that node's attributes and the payload then serves
an asset with no valuation and no haircut. Nothing raises. Chronological
intuition says edges are learned later and should be ingested later; that
intuition is what erases the attributes. :func:`ingest` asserts the outcome so a
reorder fails where it happened.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

import acquisition
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import DebtProfile, HalfLifeTable, PerspectiveArtifact
from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.deployment import BootedFabric
from ccf.graph.protocols import GraphView
from ccf.halflife.assessment import DebtFactors
from ccf.halflife.debt import DebtAssessment, FreshnessScorer, assess_debt
from ccf.halflife.decay import Observation
from ccf.products.constraints import ReferencePolicyConstraintResolver
from ccf.products.provenance import ProvenanceSource
from ccf.products.request import ProductRequest, ProductRequestContract
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

HERE = Path(__file__).parent

FACILITY = "facility_id"
BORROWER_SCOPE = "borrower_scope"
APPLY_HAIRCUTS = "apply_haircuts"
INCLUDE_SETOFF = "include_setoff"
JURISDICTION_BASIS = "jurisdiction_basis"
SHARED_COLLATERAL = "shared_collateral"

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


def config() -> Mapping[str, Any]:
    document: Mapping[str, Any] = yaml.safe_load(
        (HERE / "ccf_config.yaml").read_text(encoding="utf-8"))
    return document


def connection(*, root: Path) -> Mapping[str, str]:
    """Where the FABRIC's own L3 lives for this run. Never a source store."""
    profile = yaml.safe_load((HERE / "backends.yaml").read_text(encoding="utf-8"))[
        "declaration"]["profiles"]["sqlite"]["settings"]["database_path"]
    return {"database_path": str(root / f"{profile['prefix']}{profile['suffix']}")}


def perspective() -> PerspectiveArtifact:
    return PerspectiveArtifact(semver="1.0.0", **dict(config()["default_perspective"]))


def request(*, facility_id: str | None, borrower_scope: Sequence[str] | None,
            asked_at: datetime, apply_haircuts: bool | None = None,
            include_setoff: bool | None = None,
            jurisdiction_basis: str | None = None,
            shared_collateral: str | None = None) -> ProductRequest:
    """The question asked. An argument, never an artifact.

    A parameter the caller did not supply is OMITTED rather than defaulted
    here, so the class default in `ccf_config.yaml` is what resolves. Restating
    a default in this function would make it a second authority for one value.

    **Including the anchor.** `facility_id` and `borrower_scope` are `required`
    in the request contract, so a question missing either is one the CONTROL
    PLANE refuses — with a kind from the SDK's own vocabulary, the keys that
    were missing, and a replay record. This function therefore constructs the
    question as it was ASKED rather than validating it: a check here would be a
    second authority for a rule the Control Plane already owns, and the two
    would answer differently at exactly the moment it mattered (`D-IMPL-289`).
    """
    declared = config()["product_class"]
    parameters: dict[str, Any] = {}
    if facility_id is not None:
        parameters[FACILITY] = facility_id
    if borrower_scope is not None:
        parameters[BORROWER_SCOPE] = list(borrower_scope)
    for name, value in ((APPLY_HAIRCUTS, apply_haircuts),
                        (INCLUDE_SETOFF, include_setoff),
                        (JURISDICTION_BASIS, jurisdiction_basis),
                        (SHARED_COLLATERAL, shared_collateral)):
        if value is not None:
            parameters[name] = value
    return ProductRequest(
        schema_name=declared["schema_name"], schema_version=declared["schema_version"],
        subject=facility_id or "", intent="lgd-assessment", freshness="standard",
        asked_at=asked_at, parameters=parameters)


def effective(booted: BootedFabric, registry: ControlPlaneProtocol,
              asked: ProductRequest) -> Mapping[str, Any]:
    """What this ask is permitted to be, as GOVERNANCE derives it.

    The SDK's own public resolver — the same one `GovernedResolver` uses,
    reading the same Control Plane at the same `asked_at` — so the values here
    are the values the governed path independently resolves moments later.

    **Acquisition needs them** because `include_setoff` widens `R`: a read
    taken before governance would fetch deposits a refused request never gets
    to see, and would put them in the debt denominator. This is acquire doing
    its job, not a second policy: nothing is written onto a Control Plane
    declaration.
    """
    declared = ProductRequestContract.from_declared(
        booted.artifacts.get("request_contract"))
    source = ProvenanceSource(kind="artifact", identity="request_contract",
                              version=content_hash(declared))
    outcome = ReferencePolicyConstraintResolver(
        control_plane=registry, entitlement_key=None
    ).resolve(
        product_class=asked.schema_name, request=asked, declared=declared,
        declared_source=source, perspective=perspective(), intent=asked.intent,
        tenant=booted.tenant_id, capabilities=(),
        class_defaults=declared.defaults, class_source=source)
    if outcome.refusal is not None:
        # The governed path issues the refusal moments from now; acquisition
        # neither pre-empts it nor pays for a read whose answer is not served.
        return {}
    return outcome.evidence.values()


def acquire_for(booted: BootedFabric, registry: ControlPlaneProtocol,
                asked: ProductRequest) -> acquisition.Coverage:
    """Read both stores for the question, at the scope governance allowed.

    **A refused question is not read.** `effective` returns nothing when the
    Control Plane refuses, and this returns without touching either source
    store: the governed path issues that refusal moments from now, and
    acquisition neither pre-empts it nor pays for a read whose answer is never
    served.
    """
    values = effective(booted, registry, asked)
    if not values:
        return acquisition.nothing_acquired(str(asked.parameters.get(FACILITY, "")))
    return acquisition.acquire(
        facility_id=str(asked.parameters[FACILITY]),
        include_setoff=bool(values.get(INCLUDE_SETOFF, False)))


# ---------------------------------------------------------------------------
# Domain facts -> fabric state.
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
    """One typed edge, carrying NO attributes.

    .. warning::

       **Must reach L2 BEFORE the node envelope for either endpoint.** It
       resolves both endpoints and has no attributes to give them, so the claim
       it mints is thin, and the last claim at a URI wins rather than merging.
       Ingest this after a node envelope and that node is served with no
       valuation, no haircut and no category, with nothing raised.
    """
    return SignalEnvelope(
        tenant_id=tenant_id, envelope_id=f"edge/{ordinal}",
        source=SourceIdentity(system_id="collateral_graph"),
        ingestion_timestamp=at, observed_time=at,
        raw_payload={"subject_ref": subject, "subject_uri": subject,
                     "object_ref": obj, "object_uri": obj, "predicate": predicate})


def envelopes(coverage: acquisition.Coverage, *, tenant_id: str,
              at: datetime) -> tuple[list[SignalEnvelope], list[SignalEnvelope]]:
    """Every edge, then every node. Returned as two lists so the ORDER is visible."""
    scope = coverage.borrower_lei or coverage.facility_id
    edges: list[SignalEnvelope] = []
    nodes: list[SignalEnvelope] = []

    def edge(s: str, p: str, o: str) -> None:
        edges.append(_edge(s, p, o, tenant_id=tenant_id, at=at, ordinal=len(edges)))

    # EVERY pledge, the anchor's and the sharing facilities', as a REIFIED
    # node — mirroring `ex:CollateralPledge` in the source, and for the same
    # reason: priority belongs to the (facility, asset) PAIR. Hanging it on the
    # asset would carry only the anchor's position and silently rank every
    # other claimant as unknown, which makes a subordinate holder look senior.
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

    nodes.append(_node(coverage.facility_id, "facility", scope, tenant_id=tenant_id,
                       at=at, label=coverage.borrower_name,
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
            # The register's own words, as filed. An amendment's action is a
            # LIST — two carry two actions each — so the terminating date is
            # derived from the list rather than from a scalar field.
            amendment_action=" | ".join(a for a, _ in filing.amendments),
            label=f"terminated {filing.terminated_on}" if filing.terminated_on
            else "in force", provenance="ucc/fl-registry"))
    return edges, nodes


def ingest(booted: BootedFabric, coverage: acquisition.Coverage, *,
           at: datetime) -> None:
    """Write the coverage subgraph into L3 through the ONE write handle.

    `booted.handle.worker` is the only write handle to L3 anywhere in this
    process (single-writer, CLAUDE.md §10).

    **Edges first, nodes last** — the module docstring's contract, asserted
    rather than trusted, because a node whose attributes were erased is served
    silently.
    """
    edges, nodes = envelopes(coverage, tenant_id=booted.tenant_id, at=at)
    worker = booted.handle.worker
    for envelope in edges:
        worker.ingest(envelope)
    for envelope in nodes:
        worker.ingest(envelope)

    view = booted.handle.reader.as_of(tenant_id=booted.tenant_id, at=at)
    bare = [r.claim.entity_uri for r in view.entities
            if not r.claim.attributes.get(KIND)]
    if bare:
        raise AssertionError(
            f"{len(bare)} of {len(view.entities)} admitted nodes carry no kind after"
            " ingestion. The ingestion-order contract was violated: an"
            " endpoint-only claim arrived after a node's own claim and superseded"
            f" it. First: {sorted(bare)[0]!r}")


def debt(view: GraphView) -> DebtAssessment:
    """D_c over what the fabric actually holds for this determination.

    **Freshness is the factor that moves**, and it moves for a reason this
    product is built around: §E's valuation spread is one day against one year
    inside a single product, so a real-property appraisal and a marketable-
    securities mark decay under different curves. The SDK's own
    `FreshnessScorer` reads the declared λ_c table; this deployment supplies
    the observations and their classes and computes no curve of its own.

    Completeness is the share of pledged assets the attribute leg priced —
    a pledge whose asset has no valuation cannot contribute coverage, and
    counting it as covered is the failure this product exists to surface.
    """
    entities = list(view.entities)
    assets = [r for r in entities if r.claim.attributes.get(KIND) == "asset"]
    now = view.as_of

    observations = [
        Observation(
            observation_type=DECAY_CLASS_BY_CATEGORY.get(
                r.claim.attributes.get("category", ""), "real_property_appraisal"),
            observed_at=now - timedelta(
                days=int(r.claim.attributes.get("valuation_age_days") or 0)),
            subject=r.claim.entity_uri)
        for r in assets
    ]
    profile = DebtProfile.model_validate({"semver": "1.0.0", **config()["debt_profile"]})
    table = HalfLifeTable.model_validate({"semver": "1.0.0", "entries": config()["half_life"]})
    scorer = FreshnessScorer(table=table, risk_sensitivity=profile.risk_sensitivity)

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


@dataclass(frozen=True)
class CoverageScenario:
    """What one run needs — satisfies ``produce.Scenario`` structurally."""

    coverage: acquisition.Coverage
    asked: ProductRequest

    @property
    def product_class_key(self) -> str:
        return "product_class"

    @property
    def request_contract_key(self) -> str:
        return "request_contract"

    @property
    def policy_bundle_key(self) -> str:
        return "policy"

    @property
    def operator_parameter_keys(self) -> tuple[str, ...]:
        return tuple(config()["operators"])

    @property
    def plan_id(self) -> str:
        return f"cp-06.collateral-coverage/{self.coverage.facility_id}"

    @property
    def max_ttl_seconds(self) -> int:
        """The class ceiling — §B's 24 hours."""
        return int(timedelta(hours=24).total_seconds())

    @property
    def product_ttl_seconds(self) -> int:
        """Daily, following the fastest-moving evidence the payload carries."""
        return int(config()["half_life"]["deposit_balance"]["half_life_seconds"])
