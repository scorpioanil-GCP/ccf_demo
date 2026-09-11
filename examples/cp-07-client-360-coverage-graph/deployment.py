"""This deployment's own values — the other half of ``produce.py``.

[ADAPT] everything. [MECHANISM] nothing. Vocabulary, source access and
admission only (`D-IMPL-315`): no binder, no gates, no replay, no serve.

**How the graph is addressed lives HERE, never in Π.** Two identity facts cost
this build a silent empty graph before they were made explicit, and both stay
declared rather than assumed:

* **An LEI is an attribute used to RESOLVE a client, not the node's address.**
  `JJAX4X60DE65EYFOTY73` is the node `SuburbanPropanePartnersLP`.
* **A business id needs its declared kind prefix to become a node id.**
  Interaction `INT-00000` is the node `interaction-INT-00000`.

Π never has to guess either.

**Ingestion order is a contract.** Thin edge envelopes first, attributed node
claims last: the last claim at a URI wins and does not merge, so an edge
arriving after a node erases that node's attributes and the payload then serves
a banker with no name and no seniority, with nothing raised.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
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

LEI = "lei"
PRINCIPAL_SCOPE = "principal_scope"
SINCE = "since"
LIMIT = "limit"
INCLUDE_FAMILY = "include_family"
INCLUDE_NTK = "include_need_to_know"
KIND = "node_kind"


def config() -> Mapping[str, Any]:
    document: Mapping[str, Any] = yaml.safe_load(
        (HERE / "ccf_config.yaml").read_text(encoding="utf-8"))
    return document


def connection(*, root: Path) -> Mapping[str, str]:
    profile = yaml.safe_load((HERE / "backends.yaml").read_text(encoding="utf-8"))[
        "declaration"]["profiles"]["sqlite"]["settings"]["database_path"]
    return {"database_path": str(root / f"{profile['prefix']}{profile['suffix']}")}


def perspective() -> PerspectiveArtifact:
    return PerspectiveArtifact(semver="1.0.0", **dict(config()["default_perspective"]))


def request(*, lei: str | None, principal_scope: Sequence[str] | None,
            asked_at: datetime, since: str | None = None, limit: int | None = None,
            include_family: bool | None = None,
            include_need_to_know: bool | None = None) -> ProductRequest:
    """The question asked. A parameter the caller omitted stays omitted.

    **Including the anchor.** `lei` and `principal_scope` are `required` in the
    request contract, so a question missing either is one the CONTROL PLANE
    refuses — with the kind, the key and the replay record a governed refusal
    carries. This function therefore constructs the question as it was asked
    rather than validating it: a check here would be a second authority for a
    rule the Control Plane already owns, and the two would answer differently
    at exactly the moment it mattered (`D-IMPL-289`).
    """
    declared = config()["product_class"]
    parameters: dict[str, Any] = {}
    if lei is not None:
        parameters[LEI] = lei
    if principal_scope is not None:
        parameters[PRINCIPAL_SCOPE] = list(principal_scope)
    for name, value in ((SINCE, since), (LIMIT, limit),
                        (INCLUDE_FAMILY, include_family), (INCLUDE_NTK, include_need_to_know)):
        if value is not None:
            parameters[name] = value
    return ProductRequest(
        schema_name=declared["schema_name"], schema_version=declared["schema_version"],
        subject=lei or "", intent="meeting-prep", freshness="standard",
        asked_at=asked_at, parameters=parameters)


def effective(booted: BootedFabric, registry: ControlPlaneProtocol,
              asked: ProductRequest) -> Mapping[str, Any]:
    """What this ask is permitted to be, as governance derives it.

    The SDK's own public resolver. Acquisition needs the bounds because `since`
    and `limit` shape the READ — reading first and bounding after is the shape
    this product exists to refuse.
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
    return {} if outcome.refusal is not None else outcome.evidence.values()


def acquire_for(booted: BootedFabric, registry: ControlPlaneProtocol,
                asked: ProductRequest) -> acquisition.Coverage:
    """Read both stores for the question, at the bound governance allowed.

    **A refused question is not read.** `effective` returns nothing when the
    Control Plane refuses, and this returns without touching either source
    store: the governed path issues that refusal moments from now, and
    acquisition neither pre-empts it nor pays for a read whose answer is never
    served. Falling back to the caller's raw parameters here would be worse than
    wasteful — it would run the read at bounds governance declined to grant.
    """
    values = effective(booted, registry, asked)
    if not values:
        return acquisition.nothing_acquired(str(asked.parameters.get(LEI, "")))
    return acquisition.acquire(
        lei=str(asked.parameters[LEI]),
        since=str(values[SINCE]), limit=int(values[LIMIT]),
        include_family=bool(values[INCLUDE_FAMILY]),
        include_need_to_know=bool(values[INCLUDE_NTK]))


# ---------------------------------------------------------------------------
# Domain facts -> fabric state.
# ---------------------------------------------------------------------------


def _node(node_ref: str, kind: str, scope: str, *, tenant_id: str, at: datetime,
          **attributes: Any) -> SignalEnvelope:
    """One node's attributes. ATTRIBUTED, therefore LAST.

    ``node_ref`` is the GRAPH's address — prefixed, or name-derived for a
    client. ``ref`` among the attributes is the BUSINESS id the source stores
    use. Keeping both means Π can report `BKR-014` while the graph is walked on
    `banker-BKR-014`, without either side guessing the other's spelling.
    """
    payload = {"node_ref": node_ref, "entity_ref": node_ref, "ref": node_ref,
               KIND: kind, "principal_scope": scope}
    payload.update({k: ("" if v is None else str(v)) for k, v in attributes.items()})
    return SignalEnvelope(
        tenant_id=tenant_id, envelope_id=f"node/{kind}/{node_ref}",
        source=SourceIdentity(system_id="coverage_graph"),
        ingestion_timestamp=at, observed_time=at, raw_payload=payload)


def _edge(subject: str, predicate: str, obj: str, *, tenant_id: str,
          at: datetime, ordinal: int) -> SignalEnvelope:
    """One typed edge, carrying NO attributes.

    .. warning::

       **Must reach L2 before the node envelope for either endpoint.** The last
       claim at a URI wins and does not merge, so an edge arriving after a node
       erases that node's attributes and the payload serves a banker with no
       name and no seniority — silently.
    """
    return SignalEnvelope(
        tenant_id=tenant_id, envelope_id=f"edge/{ordinal}",
        source=SourceIdentity(system_id="coverage_graph"),
        ingestion_timestamp=at, observed_time=at,
        raw_payload={"subject_ref": subject, "subject_uri": subject,
                     "object_ref": obj, "object_uri": obj, "predicate": predicate})




def _at(iso_date: str, now: datetime) -> datetime:
    """An ISO date from a source store, as an instant on the decision's clock.

    The source dates these facts to the DAY. Pinning the time of day to the
    decision instant keeps a same-day observation at age zero instead of
    silently ageing it by up to a day, which at a seven-day half-life is
    a tenth of the signal.
    """
    return datetime.combine(date.fromisoformat(iso_date), now.timetz())


def _prefixed(kind: str, business_id: str) -> str:
    """A business id under the graph's own addressing.

    Interaction `INT-00000` is the node `interaction-INT-00000`. The prefix is
    the SOURCE's, so it is declared in `artifacts/source-vocabulary.yaml` and
    read from there rather than written into this function. A node claim minted
    at the unprefixed id lands at a URI no edge points to, and the graph is then
    served with every node isolated and nothing raised — which is why
    :func:`ingest` asserts connectivity and not only kind.
    """
    prefixes = acquisition.vocabulary()["graph_leg"]["node_prefixes"]
    return f"{prefixes[kind]}{business_id}"


def envelopes(coverage: acquisition.Coverage, *, tenant_id: str,
              at: datetime) -> tuple[list[SignalEnvelope], list[SignalEnvelope]]:
    """Every edge, then every node. Two lists so the ORDER is visible.

    Node refs are the GRAPH's addresses, never the business ids: the client is
    its name-derived node, everything else carries its kind prefix.
    """
    scope = coverage.lei
    edges: list[SignalEnvelope] = []
    nodes: list[SignalEnvelope] = []

    for subject, predicate, obj in coverage.edges:
        edges.append(_edge(subject, predicate, obj, tenant_id=tenant_id, at=at,
                           ordinal=len(edges)))

    for lei, node_ref in sorted(coverage.client_nodes.items()):
        nodes.append(_node(
            node_ref, "client", scope, tenant_id=tenant_id, at=at,
            label=coverage.client_name if lei == coverage.lei else lei,
            ref=lei, provenance="ccf_v2.legal_entity"))
    for person in coverage.people:
        nodes.append(_node(
            _prefixed("person", person.person_key), "person", scope,
            tenant_id=tenant_id, at=at, ref=person.person_key,
            label=person.display_name, role=person.role,
            officer_title=person.officer_title,
            appointment_date=person.appointment_date,
            provenance="ccf_v2.person_role"))
    for banker in coverage.bankers:
        nodes.append(_node(
            _prefixed("banker", banker.banker_id), "banker", scope,
            tenant_id=tenant_id, at=at, ref=banker.banker_id,
            label=banker.full_name, role=banker.role, seniority=banker.seniority,
            desk=banker.desk, is_primary=str(banker.is_primary).lower(),
            provenance="ccf_v2.banker"))
    for deal in coverage.deals:
        nodes.append(_node(
            _prefixed("deal", deal.deal_id), "deal", scope, tenant_id=tenant_id,
            at=at, ref=deal.deal_id, label=deal.deal_id,
            deal_type=deal.deal_type, stage=deal.stage,
            opened_date=deal.opened_date,
            mnpi_bearing=str(deal.mnpi_bearing).lower(),
            provenance="ccf_v2.deal"))
    for interaction in coverage.interactions:
        nodes.append(_node(
            _prefixed("interaction", interaction.interaction_id), "interaction",
            scope, tenant_id=tenant_id, at=at, ref=interaction.interaction_id,
            interaction_type=interaction.interaction_type,
            interaction_date=interaction.interaction_date,
            channel=interaction.channel,
            need_to_know=str(interaction.need_to_know).lower(),
            mnpi_bearing=str(interaction.mnpi_bearing).lower(),
            label=interaction.subject, provenance="ccf_v2.interaction"))
    return edges, nodes


def ingest(booted: BootedFabric, coverage: acquisition.Coverage, *,
           at: datetime) -> None:
    """Write the admitted coverage graph into L3 through the ONE write handle.

    `booted.handle.worker` is the only write handle to L3 anywhere in this
    process (single-writer, CLAUDE.md §10).

    **Edges first, nodes last** — asserted rather than trusted, because a node
    whose attributes were erased is served silently.
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
            f"{len(bare)} of {len(view.entities)} admitted nodes carry no kind"
            " after ingestion. Either the ingestion-order contract was violated"
            " — an endpoint-only claim arriving after a node's own claim and"
            " superseding it — or a node was minted at an address no edge uses."
            f" First: {sorted(bare)[0]!r}")


def debt(view: GraphView) -> DebtAssessment:
    """D_c over the evidence the fabric ADMITTED — never the truncation ratio.

    **Truncation is deliberately not a debt input.** A bounded read is a
    deliberate, disclosed act with a known edge, and the product carries that
    edge as its own fact (`evidence_boundary`, §D.3). Scoring *40 omitted of
    240* as debt would fuse two different statements — *"we chose to read this
    much"* and *"what we read is incomplete"* — and the second is the only one
    `D_c` is defined to carry (§7.7.4).

    **Completeness** is §E's own definition: the share of parties the walk
    admitted that the enrich leg actually resolved. A `participatedIn` edge
    naming a person no roster query returned is evidence the fabric holds and
    cannot use — and that IS incompleteness, independent of the bound, and it
    moves.

    **Freshness reads RECENCY, not history depth.** §E says *"F from
    interaction recency"*, and the observation supplied per party is that
    party's MOST RECENT contact — never one observation per historical
    interaction. The distinction decides the number: a relationship refreshed
    last week is current whether it has two meetings behind it or two hundred,
    and feeding every archived meeting into the scorer would measure how long
    the file is rather than how current the picture is.

    Two of §E's four classes are sourced here, and the other two are named
    rather than faked: `relationship_strength` is DERIVED from the interactions
    beneath it, so scoring it separately would count one signal twice, and
    `coverage_assignment` carries no assignment date in the source.
    """
    entities = list(view.entities)
    by_kind: dict[str, list[Any]] = {}
    ref_of: dict[str, str] = {}
    for record in entities:
        attributes = record.claim.attributes
        ref_of[record.claim.entity_uri] = attributes.get("ref", record.claim.entity_uri)
        by_kind.setdefault(attributes.get(KIND, ""), []).append(record)

    dated = {
        record.claim.entity_uri: str(record.claim.attributes["interaction_date"])
        for record in by_kind.get("interaction", [])
        if record.claim.attributes.get("interaction_date")
    }

    # Every party the WALK admitted, against the parties the ENRICH leg
    # resolved — §E's completeness, measured on the admitted graph.
    walked: dict[str, list[str]] = {}
    for record in view.relationships:
        if record.claim.relationship_type != "participatedIn":
            continue
        walked.setdefault(record.claim.subject_uri, []).append(
            dated.get(record.claim.object_uri, ""))
    resolved = {r.claim.entity_uri for r in
                (*by_kind.get("person", ()), *by_kind.get("banker", ()))}
    completeness = (
        Decimal(len(set(walked) & resolved)) / Decimal(len(walked))
        if walked else Decimal(1))

    now = view.as_of
    observations = [
        Observation(observation_type="interaction_record",
                    observed_at=_at(max(d for d in dates if d), now),
                    subject=uri)
        for uri, dates in sorted(walked.items()) if any(dates)
    ]
    observations += [
        Observation(observation_type="officer_roster",
                    observed_at=_at(str(r.claim.attributes["appointment_date"]), now),
                    subject=r.claim.entity_uri)
        for r in by_kind.get("person", [])
        if r.claim.attributes.get("appointment_date")
    ]

    profile = DebtProfile.model_validate({"semver": "1.0.0", **config()["debt_profile"]})
    table = HalfLifeTable.model_validate(
        {"semver": "1.0.0", "entries": config()["half_life"]})
    scorer = FreshnessScorer(table=table, risk_sensitivity=profile.risk_sensitivity)

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
        return f"cp-07.client-360/{self.coverage.lei}"

    @property
    def max_ttl_seconds(self) -> int:
        """The class ceiling — §B's 12 hours."""
        return int(timedelta(hours=12).total_seconds())

    @property
    def product_ttl_seconds(self) -> int:
        """The fastest-moving signal, or the class ceiling — whichever is shorter.

        **On this rung the CEILING binds, and that inverts every rung before
        it.** cp-02, cp-04 and cp-06 all serve at a TTL the DATA sets: a filed
        document or a valuation decays faster than any ceiling anyone would
        declare, so λ_c is what expires the product. Here every declared
        λ_c is slower than §B's 12 hours — the slowest is an officer roster at
        a year — because the question is about the BANK'S OWN current posture
        rather than about a document's age, and `ttl_anchor: from_decision`
        says so at registration.

        A product whose evidence decays slowly can still owe a short answer.
        Taking the minimum rather than the λ_c makes that explicit instead of
        letting a 7-day expiry sail past a 12-hour obligation, and it is why
        the SDK's TTL-bounds gate refuses the other way round.
        """
        return min(
            int(config()["half_life"]["interaction_record"]["half_life_seconds"]),
            self.max_ttl_seconds,
        )
