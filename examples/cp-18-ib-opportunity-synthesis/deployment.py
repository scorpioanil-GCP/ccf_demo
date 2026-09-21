"""The deployment's half of `cib.opportunity-synthesis`: claims, debt, one gate.

[ADAPT] the vocabulary here — the parameter names, the source names, the claim
builders — to your own product. The three verbs the paved road binds
(`acquire`, `assess`, and the declared gate `ranking_gate`) live here; the
fabric's half is `produce.py`, which names none of this.

THE PER-PERSPECTIVE ENVELOPE IS APPLIED AT THE ACQUISITION SEAM, from
`context.perspective` — the verified credential the door decided under, never
a request parameter. This is the pattern the adopter page
`public/how-to/condition-acquisition-on-the-verified-credential.md` documents,
written here against that page rather than against the prior trees' source
(`CP-SPEC-018` §G.2).

WHAT RIDES ON THE BANKER CLAIM, AND WHY. The weight vector, its version and
the per-type half-lives ride on the banker claim because the SNAPSHOT is what
replay re-executes over: a ranking served under one weight version must
reproduce under that version after the Control Plane has moved on, and the
only way that holds is for the vector to be inside the hash-bound fabric
rather than resolved afresh at replay time.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

import acquisition
import projection
from ccf.halflife.assessment import DebtAssessment
from ccf.products.contract import ContextProductContract
from ccf.products.debt_scorer import AssemblyDebtScorer, DeclaredFactor
from ccf.products.product import AcquisitionContext, AssessmentContext
from ccf.products.refusal import RESOLVED_BY_THE_RESOLVER, GovernedRefusalRaised, SubjectUnavailableRefusal
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

# The request parameters, by the names `ccf_config.yaml` declares.
AS_OF = "as_of"
SINCE = "since"
LIMIT = "limit"
SIGNAL_TYPES = "signal_types"

# The source names `ccf_environment.yaml` declares.
SOURCE_CONTROL_ROOM = "control_room"
SOURCE_RELATIONAL = "relational"
SOURCE_GRAPH = "graph"
SOURCE_DOCUMENTS = "documents"
SOURCE_CREDENTIALS = "credentials"

SYSTEM = "cp-18-ib-opportunity"
PLAN_ID = "cp-18.opportunity-synthesis.v1"
DEFAULT_SINCE_DAYS = 90

# Match keys — PRESENCE selects the resolution rule (`ccf_config.yaml`).
NODE_MATCH_KEY = {
    "banker": "banker_node",
    "prospect": "prospect_node",
    "signal": "signal_node",
    "standing_signal": "standing_signal_node",
    "note": "note_node",
    "passage": "passage_node",
}
OBJECT_RULE = {
    "prospect": "prospect_object",
    "signal": "signal_object",
    "standing_signal": "standing_signal_object",
    "note": "note_object",
    "passage": "passage_object",
}
BANKER_SUBJECT_RULE = "banker_subject"


def plan_id() -> str:
    """One plan for the three perspectives; Pi branches on the perspective."""
    return PLAN_ID


# =========================================================================
# ACQUIRE — the envelope from the credential, then edges first, nodes last
# =========================================================================


def acquire(context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
    effective = context.request.parameters
    as_of = _instant(effective[AS_OF])
    since = _instant(effective[SINCE]) if effective.get(SINCE) else as_of - timedelta(days=DEFAULT_SINCE_DAYS)
    requested = _signal_types(effective.get(SIGNAL_TYPES))
    try:
        estate = acquisition.acquire(
            banker_id=context.request.subject,
            asked_at=context.request.asked_at,
            as_of=as_of,
            since=since,
            perspective=context.perspective.role,
            requested_signal_types=requested,
            control_room_settings=context.sources[SOURCE_CONTROL_ROOM],
            relational_settings=context.sources[SOURCE_RELATIONAL],
            graph_settings=context.sources[SOURCE_GRAPH],
            document_settings=context.sources[SOURCE_DOCUMENTS],
        )
    except acquisition.NoPlanForPerspective as absent:
        # An entitled principal whose perspective the estate holds no plan for
        # is refused by name, as data, through the ONE recorder.
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(cause="unauthorized", detail=str(absent), error_code="no-projection-plan"),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from absent
    except acquisition.NoCoveragePortfolio as uncovered:
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(cause="nonexistent", detail=str(uncovered),
                                      error_code="no-coverage-portfolio"),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from uncovered
    except acquisition.SignalTypeOutsidePlan as outside:
        # Asking for a signal type the plan does not carry is asking for MORE
        # than the credential permits, so it is refused by name rather than
        # silently narrowed (`IBO-G14`).
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(cause="unauthorized", detail=str(outside),
                                      error_code="signal-type-outside-plan"),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from outside
    return envelopes(estate, tenant_id=context.tenant_id, at=context.instant)


def envelopes(estate: acquisition.Estate, *, tenant_id: str, at: datetime) -> tuple[SignalEnvelope, ...]:
    """The estate as dated claims — EDGES FIRST, ATTRIBUTED NODES LAST.

    A thin endpoint claim minted by an edge supersedes a richer claim at the
    same URI if it arrives after it (`D-IMPL-316`); the banker node, minted as
    an endpoint by every edge, is therefore written LAST of all.
    """
    if estate.empty:
        return ()
    assert estate.plan is not None and estate.banker is not None
    banker_uri = f"{acquisition.vocabulary()['entity_uri_prefix']['banker']}{estate.banker_id}"
    edges = tuple(
        _edge(tenant_id=tenant_id, at=at, ordinal=ordinal, subject=banker_uri, record=record)
        for ordinal, record in enumerate(estate.records)
    )
    nodes = tuple(_node(tenant_id=tenant_id, at=at, record=record) for record in estate.records)
    banker = _banker(tenant_id=tenant_id, at=at, estate=estate, uri=banker_uri)
    return (*edges, *nodes, banker)


def _edge(*, tenant_id: str, at: datetime, ordinal: int, subject: str, record: acquisition.Record) -> SignalEnvelope:
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"edge/{record.edge_type}/{ordinal}",
        source=SourceIdentity(system_id=SYSTEM),
        ingestion_timestamp=at,
        observed_time=None,
        raw_payload={
            BANKER_SUBJECT_RULE: subject,
            OBJECT_RULE[record.entity_class]: record.entity_uri,
            "subject_uri": subject,
            "object_uri": record.entity_uri,
            "predicate": record.edge_type,
        },
    )


def _node(*, tenant_id: str, at: datetime, record: acquisition.Record) -> SignalEnvelope:
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"node/{record.entity_uri}",
        source=SourceIdentity(system_id=SYSTEM),
        ingestion_timestamp=at,
        # The claim's own world date — the valid-time cut and, for the
        # `signal` class, the freshness basis (`decay_basis: valid-from`).
        observed_time=_midnight(record.dated),
        raw_payload={
            NODE_MATCH_KEY[record.entity_class]: record.entity_uri,
            "entity_uri": record.entity_uri,
            **dict(record.attributes),
        },
    )


def _banker(*, tenant_id: str, at: datetime, estate: acquisition.Estate, uri: str) -> SignalEnvelope:
    assert estate.plan is not None and estate.banker is not None and estate.weights is not None
    terms = acquisition.vocabulary()
    required = acquisition.required_classes(estate.plan, terms)
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"node/{uri}",
        source=SourceIdentity(system_id=SYSTEM),
        ingestion_timestamp=at,
        observed_time=None,
        raw_payload={
            NODE_MATCH_KEY["banker"]: uri,
            "entity_uri": uri,
            **estate.banker,
            "classification": terms["classification"]["assignment"]["banker"],
            "perspective_id": estate.plan.perspective_id,
            "plan_json": estate.plan.as_json(required_classes=required),
            # THE VECTOR AND ITS VERSION, in the hash-bound fabric so replay
            # reproduces the historical ranking from the snapshot.
            "weights_json": json.dumps(
                {
                    "weight_version": estate.weights.weight_version,
                    "weights": {k: str(v) for k, v in sorted(estate.weights.by_signal_type.items())},
                    "half_life_days": dict(sorted(estate.half_lives.items())),
                },
                sort_keys=True,
            ),
            "weight_version": estate.weights.weight_version,
            "portfolio_json": json.dumps(list(estate.portfolio)),
            "optional_context_json": json.dumps(dict(estate.optional_context), sort_keys=True),
            "ledger_t": estate.ledger_t,
        },
    )


# =========================================================================
# ASSESS — F from the SDK's scorer, C over the perspective's OWN required set
# =========================================================================


def assess(context: AssessmentContext) -> DebtAssessment:
    assert context.half_life is not None and context.profile is not None
    scorer = AssemblyDebtScorer(
        table=context.half_life,
        profile=context.profile,
        completeness=DeclaredFactor(value=projection.view_completeness(context.view)),
        semantic_consistency=DeclaredFactor(value=Decimal("1.0000")),
    )
    return scorer(view=context.view, evidence=context.evidence)


# =========================================================================
# THE DECLARED GATE — `cp-18.ranking-holds`
# =========================================================================


def ranking_gate(*, candidate: ContextProductContract, evidence: object = None) -> str | None:
    """Shape · portfolio containment · signal-type containment · version · explanation.

    Runs after the SDK's universal gates admitted the candidate and before the
    tolerance check; a string is a `ProductInvariantRefusal` by name.
    """
    del evidence
    payload = candidate.payload
    role = payload.get("perspective")
    if not isinstance(role, str) or role not in projection.PERSPECTIVE_MEMBERS:
        return f"the payload names perspective {role!r}, which `artifacts/perspectives.yaml` does not declare"
    expected = projection.members_for(role)
    if set(payload) != expected:
        return (
            f"the payload's member set differs from the declared shape for perspective `{role}`"
            f" ({sorted(set(payload) ^ expected)}); the shape is a function of the perspective,"
            f" never the banker or the request (IBO-G12)"
        )

    # The version that ranked this product must be named on it — WHEN a
    # banker was served. A computed-empty serve ranked nothing, so requiring a
    # version there would turn the A6 comparator into a refusal and hand back
    # the existence oracle `IBO-G16` exists to close.
    if payload.get("banker") is not None and not payload.get("weight_version"):
        return "the served product names no weight version; a ranking whose weights are unknown is not replayable (IBO-G05)"

    portfolio = set(payload.get("portfolio") or [])
    ranked = payload.get("ranked_opportunities") or ()
    admitted = set(payload.get("signal_types_admitted") or ())
    for row in ranked:
        lei = row.get("lei")
        if portfolio and lei not in portfolio:
            return (
                f"ranked opportunity {lei!r} is outside the banker's own coverage portfolio;"
                f" the candidate universe is the consumer's (IBO-G09)"
            )
        contributions = row.get("contributing_signals") or ()
        if not contributions:
            return (
                f"ranked opportunity {lei!r} carries no contributing signal; a ranking that"
                f" cannot justify itself is not served (IBO-G13)"
            )
        for contribution in contributions:
            if contribution.get("signal_type") not in admitted:
                return (
                    f"ranked opportunity {lei!r} rests on signal type"
                    f" {contribution.get('signal_type')!r}, which the perspective's plan does"
                    f" not admit (IBO-G14)"
                )

    # Optional context must be STATED, never silently absent (IBO-G17/G18).
    optional = payload.get("optional_context")
    if not isinstance(optional, dict) or "mnpi_wall_child" not in optional:
        return (
            "the payload does not state whether the optional MNPI wall context was"
            " contributed; a consumer must not have to assume the evidence base (IBO-G18)"
        )

    vocabulary = set(projection.CLASSIFICATION_VOCABULARY)
    for member in projection.LIST_MEMBERS:
        for item in payload.get(member) or ():
            classification = item.get("classification")
            if classification is not None and classification not in vocabulary:
                return (
                    f"member `{member}` carries classification {classification!r} outside the"
                    f" product's vocabulary (IBO-G02)"
                )
    return None


# --- helpers ------------------------------------------------------------------------


def _instant(value: Any) -> datetime:
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        raise ValueError(f"an instant must carry a zone; got {value!r}")
    return parsed.astimezone(UTC)


def _signal_types(value: Any) -> tuple[str, ...]:
    if value is None or value == "":
        return ()
    if isinstance(value, str):
        return tuple(part.strip() for part in value.split(",") if part.strip())
    return tuple(str(part) for part in value)


def _midnight(day: date | None) -> datetime | None:
    if day is None:
        return None
    return datetime.combine(day, time.min, tzinfo=UTC)


def credential_grants(sources: Mapping[str, Mapping[str, str]]) -> Mapping[str, str]:
    """Bearer credential -> `banker_id`, read from the environment by NAME."""
    return {token: banker_id for banker_id, token in sources[SOURCE_CREDENTIALS].items()}
