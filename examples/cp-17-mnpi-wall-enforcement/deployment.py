"""The deployment's half of `cib.mnpi-wall`: what the road hands it, turned into claims.

[ADAPT] the vocabulary here — the parameter names, the source names, the
claim builders — to your own product. The three verbs the paved road binds
(`acquire`, `assess`, and the declared gate `wall_gate`) live here; the
fabric's half is `produce.py`, which names none of this.

THE PER-PRINCIPAL ENVELOPE IS APPLIED HERE, from `context.perspective`, the
verified credential the door decided under — never from a request parameter
(`CP-SPEC-017` §D.3 step 1; the A2 measurement, `CP17-F-01`). The envelope's
inputs — the crossing that keyed the wall, the restriction in force — are
consumed at this seam and are NOT emitted as claims for any principal
(§D.3 step 1.7, ruled). The principal's own plan IS emitted, on the issuer
claim, because the principal is entitled to it and `assess` and the gate
read it off the view.
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
KNOWN_AS_OF = "known_as_of"
DEBT_TOLERANCE = "debt_tolerance"

# The source names `ccf_environment.yaml` declares.
SOURCE_CONTROL_ROOM = "control_room"
SOURCE_RELATIONAL = "relational"
SOURCE_GRAPH = "graph"
SOURCE_DOCUMENTS = "documents"
SOURCE_CREDENTIALS = "credentials"

SYSTEM = "cp-17-mnpi-wall"
PLAN_ID = "cp-17.mnpi-wall.v1"

# Match keys — PRESENCE selects the resolution rule (`ccf_config.yaml`).
NODE_MATCH_KEY = {
    "issuer": "issuer_node",
    "family_member": "family_node",
    "deal_engagement": "deal_node",
    "interaction": "interaction_node",
    "research_note": "research_node",
    "position": "position_node",
}
OBJECT_RULE = {
    "family_member": "family_object",
    "deal_engagement": "deal_object",
    "interaction": "interaction_object",
    "research_note": "research_object",
    "position": "position_object",
}
ISSUER_SUBJECT_RULE = "issuer_subject"


def plan_id() -> str:
    """One plan for the three roles (`MWE-G13`); Π branches on the role."""
    return PLAN_ID


# =========================================================================
# ACQUIRE — the envelope from the credential, then edges first, nodes last
# =========================================================================


def acquire(context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
    effective = context.request.parameters
    known_as_of = _instant(effective[KNOWN_AS_OF])
    try:
        estate = acquisition.acquire(
            lei=context.request.subject,
            asked_at=context.request.asked_at,
            known_as_of=known_as_of,
            principal_id=context.perspective.principal_id,
            control_room_settings=context.sources[SOURCE_CONTROL_ROOM],
            relational_settings=context.sources[SOURCE_RELATIONAL],
            graph_settings=context.sources[SOURCE_GRAPH],
            document_settings=context.sources[SOURCE_DOCUMENTS],
        )
    except acquisition.NoPlanForPrincipal as absent:
        # An entitled principal the estate has no plan for is refused by name,
        # as data, through the ONE recorder — never as a runtime failure.
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(cause="unauthorized", detail=str(absent), error_code="no-projection-plan"),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from absent
    return envelopes(estate, tenant_id=context.tenant_id, at=context.instant)


def envelopes(estate: acquisition.Estate, *, tenant_id: str, at: datetime) -> tuple[SignalEnvelope, ...]:
    """The estate as dated claims — EDGES FIRST, ATTRIBUTED NODES LAST.

    A thin endpoint claim minted by an edge supersedes a richer claim at the
    same URI if it arrives after it (`D-IMPL-316`); the issuer node, minted
    as an endpoint by every edge, is therefore written LAST of all.
    """
    if estate.empty:
        return ()
    assert estate.plan is not None and estate.issuer is not None
    issuer_uri = f"{acquisition.vocabulary()['entity_uri_prefix']['issuer']}{estate.lei}"
    edges = tuple(
        _edge(tenant_id=tenant_id, at=at, ordinal=ordinal, subject=issuer_uri, record=record)
        for ordinal, record in enumerate(estate.records)
    )
    nodes = tuple(_node(tenant_id=tenant_id, at=at, record=record) for record in estate.records)
    issuer = _issuer(tenant_id=tenant_id, at=at, estate=estate, uri=issuer_uri)
    return (*edges, *nodes, issuer)


def _edge(*, tenant_id: str, at: datetime, ordinal: int, subject: str, record: acquisition.Record) -> SignalEnvelope:
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"edge/{record.edge_type}/{ordinal}",
        source=SourceIdentity(system_id=SYSTEM),
        ingestion_timestamp=at,
        observed_time=None,
        raw_payload={
            ISSUER_SUBJECT_RULE: subject,
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
        # `position` class, the freshness basis (`decay_basis: valid-from`).
        observed_time=_midnight(record.dated),
        raw_payload={
            NODE_MATCH_KEY[record.entity_class]: record.entity_uri,
            "entity_uri": record.entity_uri,
            **dict(record.attributes),
        },
    )


def _issuer(*, tenant_id: str, at: datetime, estate: acquisition.Estate, uri: str) -> SignalEnvelope:
    assert estate.plan is not None and estate.issuer is not None
    terms = acquisition.vocabulary()
    required = acquisition.required_classes(estate.plan, terms)
    reg_fd = "null" if estate.reg_fd is None else json.dumps(
        {**dict(estate.reg_fd), "classification": terms["classification"]["assignment"]["issuer"]}, sort_keys=True,
    )
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"node/{uri}",
        source=SourceIdentity(system_id=SYSTEM),
        ingestion_timestamp=at,
        observed_time=None,
        raw_payload={
            NODE_MATCH_KEY["issuer"]: uri,
            "entity_uri": uri,
            **estate.issuer,
            "classification": terms["classification"]["assignment"]["issuer"],
            "reg_fd_disclosure_json": reg_fd,
            "plan_json": estate.plan.as_json(required_classes=required),
            "ledger_t": estate.ledger_t,
        },
    )


# =========================================================================
# ASSESS — F from the SDK's scorer, C over the principal's OWN required set
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
# THE DECLARED GATE — `cp-17.wall-holds`: three predicates, one slot
# =========================================================================


def wall_gate(*, candidate: ContextProductContract, evidence: object = None) -> str | None:
    """Vocabulary containment · classification containment · role-constant shape.

    Runs after the SDK's universal gates admitted the candidate and before the
    tolerance check; a string is a `ProductInvariantRefusal` by name.
    """
    del evidence
    payload = candidate.payload
    role = payload.get("role")
    if not isinstance(role, str) or role not in projection.ROLE_MEMBERS:
        return f"the payload names role {role!r}, which `artifacts/perspectives.yaml` does not declare"
    expected = projection.members_for(role)
    if set(payload) != expected:
        return (
            f"the payload's member set differs from the declared shape for role `{role}`"
            f" ({sorted(set(payload) ^ expected)}); the shape is a function of the role, never the subject (MWE-G04)"
        )
    plan = payload.get("plan")
    if plan is None:
        return None  # the empty view: nothing served, nothing to contain
    served_types = set(payload.get("edge_types_served") or ())
    permitted_types = set(plan["permitted_edge_types"])
    if not served_types <= permitted_types:
        return (
            f"served edge types {sorted(served_types - permitted_types)} fall outside the principal's"
            f" permitted vocabulary — the wall does not hold (MWE-G03)"
        )
    permitted_classes = set(plan["permitted_classifications"])
    vocabulary = set(projection.CLASSIFICATION_VOCABULARY)
    for member in projection.LIST_MEMBERS:
        bounded = member in projection.CLASSIFICATION_BOUNDED_MEMBERS
        for item in payload.get(member) or ():
            classification = item.get("classification")
            if classification not in vocabulary or (bounded and classification not in permitted_classes):
                return (
                    f"member `{member}` carries classification {classification!r} outside the"
                    f" principal's permitted set — the wall does not hold (MWE-G02)"
                )
    return None


# --- helpers ------------------------------------------------------------------------


def _instant(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        raise ValueError(f"`{KNOWN_AS_OF}` must carry a zone; got {value!r}")
    return parsed.astimezone(UTC)


def _midnight(day: date | None) -> datetime | None:
    if day is None:
        return None
    return datetime.combine(day, time.min, tzinfo=UTC)


def credential_grants(sources: Mapping[str, Mapping[str, str]]) -> Mapping[str, str]:
    """Bearer credential → `principal_id`, read from the environment by NAME."""
    return {token: principal_id for principal_id, token in sources[SOURCE_CREDENTIALS].items()}
