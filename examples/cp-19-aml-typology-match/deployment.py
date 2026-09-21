"""The deployment's half of `compliance.aml-typology`: claims, debt, one gate.

[ADAPT] the vocabulary here — the parameter names, the source names, the claim
builders — to your own product. The three verbs the paved road binds
(`acquire`, `assess`, and the declared gate `dispositions_gate`) live here;
the fabric's half is `produce.py`, which names none of this.

THE PER-PERSPECTIVE ENVELOPE IS APPLIED AT THE ACQUISITION SEAM, from
`context.perspective` — the verified credential the door decided under, never
a request parameter (`CP-SPEC-019` §D.3; the A2 measurement, third writing).
The envelope's inputs — the SAR classification rows, the disposition rule set,
the residency constraint — are consumed at that seam and are NOT emitted as
claims. The permitted disposition set IS emitted, on the alert claim, because
the perspective is entitled to it and both `assess` and the gate read it off
the view.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any

import acquisition
import projection
from ccf.products.contract import ContextProductContract
from ccf.products.debt_scorer import AssemblyDebtScorer, DeclaredFactor
from ccf.products.product import AcquisitionContext, AssessmentContext
from ccf.products.refusal import RESOLVED_BY_THE_RESOLVER, GovernedRefusalRaised, SubjectUnavailableRefusal
from ccf.halflife.assessment import DebtAssessment
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

# The request parameters, by the names `ccf_config.yaml` declares.
AS_OF = "as_of"
NETWORK_DEPTH = "network_depth"

# The source names `ccf_environment.yaml` declares.
SOURCE_CONTROL_ROOM = "control_room"
SOURCE_RELATIONAL = "relational"
SOURCE_GRAPH = "graph"
SOURCE_DOCUMENTS = "documents"
SOURCE_CREDENTIALS = "credentials"

SYSTEM = "cp-19-aml-typology"
PLAN_ID = "cp-19.aml-typology.v1"

# Match keys — PRESENCE selects the resolution rule (`ccf_config.yaml`).
NODE_MATCH_KEY = {
    "alert": "alert_node",
    "party": "party_node",
    "transaction": "transaction_node",
    "typology_match": "typology_node",
    "advisory_passage": "advisory_node",
    "prior_alert": "prior_alert_node",
    "sar_record": "sar_node",
    "screening_result": "screening_node",
}
OBJECT_RULE = {
    "party": "party_object",
    "transaction": "transaction_object",
    "typology_match": "typology_object",
    "advisory_passage": "advisory_object",
    "prior_alert": "prior_alert_object",
    "sar_record": "sar_object",
    "screening_result": "screening_object",
}
ALERT_SUBJECT_RULE = "alert_subject"


def plan_id() -> str:
    """One plan for the three perspectives; Π branches on the perspective."""
    return PLAN_ID


# =========================================================================
# ACQUIRE — the envelope from the credential, then edges first, nodes last
# =========================================================================


def acquire(context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
    effective = context.request.parameters
    as_of = _instant(effective[AS_OF])
    depth = int(float(effective.get(NETWORK_DEPTH, 2) or 2))
    try:
        estate = acquisition.acquire(
            alert_id=context.request.subject,
            asked_at=context.request.asked_at,
            as_of=as_of,
            network_depth=depth,
            perspective=context.perspective.role,
            control_room_settings=context.sources[SOURCE_CONTROL_ROOM],
            relational_settings=context.sources[SOURCE_RELATIONAL],
            graph_settings=context.sources[SOURCE_GRAPH],
            document_settings=context.sources[SOURCE_DOCUMENTS],
        )
    except acquisition.NoPlanForPerspective as absent:
        # An entitled principal whose perspective the estate holds no plan for
        # is refused by name, as data, through the ONE recorder — never as a
        # runtime failure.
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(cause="unauthorized", detail=str(absent), error_code="no-projection-plan"),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from absent
    return envelopes(estate, tenant_id=context.tenant_id, at=context.instant)


def envelopes(estate: acquisition.Estate, *, tenant_id: str, at: datetime) -> tuple[SignalEnvelope, ...]:
    """The estate as dated claims — EDGES FIRST, ATTRIBUTED NODES LAST.

    A thin endpoint claim minted by an edge supersedes a richer claim at the
    same URI if it arrives after it (`D-IMPL-316`); the alert node, minted as
    an endpoint by every edge, is therefore written LAST of all.
    """
    if estate.empty:
        return ()
    assert estate.plan is not None and estate.alert is not None
    alert_uri = f"{acquisition.vocabulary()['entity_uri_prefix']['alert']}{estate.alert_id}"
    edges = tuple(
        _edge(tenant_id=tenant_id, at=at, ordinal=ordinal, subject=alert_uri, record=record)
        for ordinal, record in enumerate(estate.records)
    )
    nodes = tuple(_node(tenant_id=tenant_id, at=at, record=record) for record in estate.records)
    alert = _alert(tenant_id=tenant_id, at=at, estate=estate, uri=alert_uri)
    return (*edges, *nodes, alert)


def _edge(*, tenant_id: str, at: datetime, ordinal: int, subject: str, record: acquisition.Record) -> SignalEnvelope:
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"edge/{record.edge_type}/{ordinal}",
        source=SourceIdentity(system_id=SYSTEM),
        ingestion_timestamp=at,
        observed_time=None,
        raw_payload={
            ALERT_SUBJECT_RULE: subject,
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
        # `transaction` class, the freshness basis (`decay_basis: valid-from`).
        observed_time=_midnight(record.dated),
        raw_payload={
            NODE_MATCH_KEY[record.entity_class]: record.entity_uri,
            "entity_uri": record.entity_uri,
            **dict(record.attributes),
        },
    )


def _alert(*, tenant_id: str, at: datetime, estate: acquisition.Estate, uri: str) -> SignalEnvelope:
    assert estate.plan is not None and estate.alert is not None
    terms = acquisition.vocabulary()
    required = acquisition.required_classes(estate.plan, terms)
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"node/{uri}",
        source=SourceIdentity(system_id=SYSTEM),
        ingestion_timestamp=at,
        observed_time=None,
        raw_payload={
            NODE_MATCH_KEY["alert"]: uri,
            "entity_uri": uri,
            **estate.alert,
            "classification": terms["classification"]["assignment"]["alert"],
            "plan_json": estate.plan.as_json(required_classes=required),
            # THE BOUND, on the claim, because the perspective is entitled to
            # know what it may propose. The rule SET that produced it is not.
            "permitted_json": json.dumps(list(estate.permitted)),
            "posture_json": estate.posture.as_json() if estate.posture is not None else "",
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
# THE DECLARED GATE — `cp-19.dispositions-hold`: three predicates, one slot
# =========================================================================


def dispositions_gate(*, candidate: ContextProductContract, evidence: object = None) -> str | None:
    """Disposition containment · classification containment · shape by perspective.

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
            f" never the alert (ATM-G07)"
        )
    permitted = set(payload.get("permitted_dispositions") or ())
    for member in projection.DISPOSITION_BOUNDED_MEMBERS:
        for item in payload.get(member) or ():
            proposed = item.get("disposition")
            if proposed not in permitted:
                return (
                    f"member `{member}` proposes disposition {proposed!r}, which the posture in force"
                    f" does not permit — a forbidden disposition must never be generated (ATM-G03)"
                )
    vocabulary = set(projection.CLASSIFICATION_VOCABULARY)
    seen_sar = {
        item.get("classification")
        for item in payload.get("sar_filing_history") or ()
    }
    allowed_sar = {f"sar-{name}" for name in projection.SEES_SAR[role]}
    if not seen_sar <= allowed_sar:
        return (
            f"perspective `{role}` carries SAR classifications {sorted(seen_sar - allowed_sar)},"
            f" which its declared visibility does not include — the existence of a SAR is"
            f" itself restricted (ATM-G09)"
        )
    for member in projection.LIST_MEMBERS:
        for item in payload.get(member) or ():
            classification = item.get("classification")
            if classification is not None and classification not in vocabulary:
                return (
                    f"member `{member}` carries classification {classification!r} outside the"
                    f" product's vocabulary (ATM-G02)"
                )
    return None


# --- helpers ------------------------------------------------------------------------


def _instant(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        raise ValueError(f"`{AS_OF}` must carry a zone; got {value!r}")
    return parsed.astimezone(UTC)


def _midnight(day: date | None) -> datetime | None:
    if day is None:
        return None
    return datetime.combine(day, time.min, tzinfo=UTC)


def credential_grants(sources: Mapping[str, Mapping[str, str]]) -> Mapping[str, str]:
    """Bearer credential -> `principal_id`, read from the environment by NAME."""
    return {token: principal_id for principal_id, token in sources[SOURCE_CREDENTIALS].items()}
