"""The deployment's half of `compliance.beneficial-ownership`.

[ADAPT] the vocabulary here to your own product. The three verbs the paved
road binds (`acquire`, `assess`, and the declared gate `ownership_gate`) live
here; the fabric's half is `produce.py`, which names none of this.

THE RESIDENCY ENVELOPE IS APPLIED AT THE ACQUISITION SEAM, from
`context.perspective` — the verified credential the door decided under, never
a request parameter. This is the pattern the adopter page
`public/how-to/condition-acquisition-on-the-verified-credential.md`
documents, written here against that page.

THE REVIEW QUEUE IS NOT IN THIS MODULE, AND THAT IS THE RULING
(`CP-SPEC-015` §F.4.1). `acquire`, `assess` and the gate run during
construction; enqueue happens afterwards, against a product that is already
complete, governed, assessed and immutable. Nothing here imports `ccf.hitl`.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, date, datetime, time
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
THRESHOLD = "threshold"
MIN_CONFIDENCE = "min_confidence"
MAX_DEPTH = "max_depth"

# The source names `ccf_environment.yaml` declares.
SOURCE_RELATIONAL = "relational"
SOURCE_GRAPH = "graph"
SOURCE_DOCUMENTS = "documents"
SOURCE_CREDENTIALS = "credentials"

SYSTEM = "cp-15-kyc-beneficial-ownership"
PLAN_ID = "cp-15.beneficial-ownership.v1"
DEFAULT_MAX_DEPTH = 6

NODE_MATCH_KEY = {
    "entity": "entity_node",
    "person": "person_node",
    "resolution": "resolution_node",
    "screening": "screening_node",
    "hop": "hop_node",
    "declaration": "declaration_node",
}
OBJECT_RULE = {
    "person": "person_object",
    "resolution": "resolution_object",
    "screening": "screening_object",
    "hop": "hop_object",
    "declaration": "declaration_object",
}
ENTITY_SUBJECT_RULE = "entity_subject"


def plan_id() -> str:
    """One plan for the three perspectives; Pi branches on the perspective."""
    return PLAN_ID


# =========================================================================
# ACQUIRE — the envelope from the credential, then edges first, nodes last
# =========================================================================


def acquire(context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
    effective = context.request.parameters
    as_of = _instant(effective[AS_OF])
    try:
        estate = acquisition.acquire(
            entity_id=context.request.subject,
            asked_at=context.request.asked_at,
            as_of=as_of,
            intent=context.request.intent,
            perspective=context.perspective.role,
            principal_id=context.perspective.principal_id,
            requested_threshold=_decimal(effective.get(THRESHOLD)),
            requested_confidence=_decimal(effective.get(MIN_CONFIDENCE)),
            max_depth=int(float(effective.get(MAX_DEPTH) or DEFAULT_MAX_DEPTH)),
            relational_settings=context.sources[SOURCE_RELATIONAL],
            graph_settings=context.sources[SOURCE_GRAPH],
            document_settings=context.sources[SOURCE_DOCUMENTS],
        )
    except acquisition.NoJurisdictionGrant as ungranted:
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(cause="unauthorized", detail=str(ungranted),
                                      error_code="no-jurisdiction-grant"),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from ungranted
    except acquisition.UnpricedIntent as unpriced:
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(cause="nonexistent", detail=str(unpriced),
                                      error_code="unpriced-intent"),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from unpriced
    except acquisition.FloorBreached as below:
        # Asking below a declared floor is asking for MORE than the credential
        # permits, so it is refused by name rather than silently raised to the
        # floor (`UBO-G07`).
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(cause="unauthorized", detail=str(below),
                                      error_code="floor-breached"),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from below
    return envelopes(estate, tenant_id=context.tenant_id, at=context.instant,
                     intent=context.request.intent)


def envelopes(
    estate: acquisition.Estate, *, tenant_id: str, at: datetime, intent: str
) -> tuple[SignalEnvelope, ...]:
    """The estate as dated claims — EDGES FIRST, ATTRIBUTED NODES LAST.

    A thin endpoint claim minted by an edge supersedes a richer claim at the
    same URI if it arrives after it (`D-IMPL-316`); the entity node, minted as
    an endpoint by every edge, is therefore written LAST of all.
    """
    if estate.empty:
        return ()
    assert estate.entity is not None
    entity_uri = f"{acquisition.vocabulary()['entity_uri_prefix']['entity']}{estate.entity_id}"
    edges = tuple(
        _edge(tenant_id=tenant_id, at=at, ordinal=ordinal, subject=entity_uri, record=record)
        for ordinal, record in enumerate(estate.records)
    )
    nodes = tuple(_node(tenant_id=tenant_id, at=at, record=record) for record in estate.records)
    entity = _entity(tenant_id=tenant_id, at=at, estate=estate, uri=entity_uri, intent=intent)
    return (*edges, *nodes, entity)


def _edge(*, tenant_id: str, at: datetime, ordinal: int, subject: str, record: acquisition.Record) -> SignalEnvelope:
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"edge/{record.edge_type}/{ordinal}",
        source=SourceIdentity(system_id=SYSTEM),
        ingestion_timestamp=at,
        observed_time=None,
        raw_payload={
            ENTITY_SUBJECT_RULE: subject,
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
        # Only the DECLARATION class is dated — it was filed on a day. Every
        # other class here is a standing state and carries no event date, which
        # is why each has `decay: supersede-only` rather than a curve
        # (`D-GATE-cp-18`).
        observed_time=_midnight(record.dated),
        raw_payload={
            NODE_MATCH_KEY[record.entity_class]: record.entity_uri,
            "entity_uri": record.entity_uri,
            **dict(record.attributes),
        },
    )


def _entity(
    *, tenant_id: str, at: datetime, estate: acquisition.Estate, uri: str, intent: str
) -> SignalEnvelope:
    assert estate.entity is not None and estate.floors is not None
    terms = acquisition.vocabulary()
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"node/{uri}",
        source=SourceIdentity(system_id=SYSTEM),
        ingestion_timestamp=at,
        observed_time=None,
        raw_payload={
            NODE_MATCH_KEY["entity"]: uri,
            "entity_uri": uri,
            **estate.entity,
            "classification": terms["classification"]["assignment"]["entity"],
            "intent": intent,
            # THE BOUNDS, on the claim, because the asking principal is
            # entitled to know what bound its own answer. The residency
            # entitlement and the WITHHELD COUNT are not here: a count of what
            # was withheld is itself disclosure (`UBO-G02`).
            "applicable_threshold": str(estate.applicable_threshold),
            "threshold_basis": estate.threshold_basis,
            "min_confidence": str(estate.min_confidence),
            "policy_version": estate.floors.policy_version,
            "refresh_state_json": json.dumps(dict(estate.refresh_state), sort_keys=True),
            "ledger_t": estate.ledger_t,
        },
    )


# =========================================================================
# ASSESS
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
# THE DECLARED GATE — `cp-15.ownership-holds`
# =========================================================================


def ownership_gate(*, candidate: ContextProductContract, evidence: object = None) -> str | None:
    """Residency · confidence · threshold · cycle honesty · shape.

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
            f" never the entity or the request (UBO-G14)"
        )

    # RESIDENCY CONTAINMENT. A person-restricted record may reach only a
    # perspective the estate entitles, and no member may state how many were
    # withheld — a count of what was withheld is itself disclosure.
    entitled = bool(payload.get("residency_entitlement", {}).get("sees_eu_person_data")) \
        if isinstance(payload.get("residency_entitlement"), dict) else None
    for member in ("ownership_chain", "reportable_owners", "sub_threshold_findings"):
        for item in payload.get(member) or ():
            if item.get("classification") == "person-restricted" and entitled is False:
                return (
                    f"member `{member}` carries a person-restricted record for a perspective the"
                    f" estate does not entitle; a person outside the entitlement is never"
                    f" materialized (UBO-G02)"
                )
    for key in payload:
        if "withheld" in key.lower():
            return (
                f"the payload names `{key}`; a count of what the residency envelope withheld is"
                f" itself disclosure and must not reach a consumer (UBO-G02)"
            )

    # CONFIDENCE DISCLOSURE. Every person served carries one.
    for item in payload.get("ownership_chain") or ():
        if item.get("resolution_confidence") in (None, ""):
            return (
                f"person {item.get('person_key')!r} is served with no resolution confidence;"
                f" a person resolved to an unknown degree is not served silently (UBO-G04)"
            )

    # THRESHOLD CORRECTNESS, both directions — WHEN an entity was served. A
    # computed-empty serve bound nothing, so requiring a threshold there would
    # turn the A6 comparator into a refusal and hand back the existence oracle
    # `UBO-G17` exists to close.
    threshold = payload.get("applicable_threshold")
    if payload.get("entity") is not None and threshold in (None, ""):
        return "the served product names no applicable threshold (UBO-G05)"
    if threshold in (None, ""):
        return None
    bound = Decimal(str(threshold))
    for item in payload.get("reportable_owners") or ():
        if Decimal(str(item.get("effective_pct", "0"))) < bound:
            return (
                f"person {item.get('person_key')!r} is reported at"
                f" {item.get('effective_pct')} against a threshold of {bound} (UBO-G05)"
            )
    for item in payload.get("sub_threshold_findings") or ():
        if Decimal(str(item.get("effective_pct", "0"))) >= bound:
            return (
                f"person {item.get('person_key')!r} is a sub-threshold finding at"
                f" {item.get('effective_pct')}, which is at or above the threshold {bound} (UBO-G05)"
            )

    # CYCLE HONESTY. The member is present, and nothing invents a cycle.
    cycles = payload.get("cycle_findings")
    if cycles is None:
        return (
            "the payload omits `cycle_findings`; the member is present and empty in this"
            " estate, and omitting it would make its absence informative (UBO-G19)"
        )
    for finding in cycles:
        if not finding.get("path"):
            return "a cycle finding carries no path; no cycle is invented (UBO-G19)"

    vocabulary = set(projection.CLASSIFICATION_VOCABULARY)
    for member in projection.LIST_MEMBERS:
        for item in payload.get(member) or ():
            classification = item.get("classification")
            if classification is not None and classification not in vocabulary:
                return (
                    f"member `{member}` carries classification {classification!r} outside the"
                    f" product's vocabulary"
                )
    return None


# --- helpers ------------------------------------------------------------------------


def _instant(value: Any) -> datetime:
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        raise ValueError(f"an instant must carry a zone; got {value!r}")
    return parsed.astimezone(UTC)


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


def _midnight(day: date | None) -> datetime | None:
    if day is None:
        return None
    return datetime.combine(day, time.min, tzinfo=UTC)


def credential_grants(sources: Mapping[str, Mapping[str, str]]) -> Mapping[str, str]:
    """Bearer credential -> `principal_id`, read from the environment by NAME."""
    return {token: principal_id for principal_id, token in sources[SOURCE_CREDENTIALS].items()}
