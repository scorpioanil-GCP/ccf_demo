"""The deployment's half of `cib.abs-surveillance`.

[ADAPT] the vocabulary here to your own product. The three verbs the paved
road binds (`acquire`, `assess`, and the declared gate `surveillance_gate`)
live here; the fabric's half is `produce.py`, which names none of this.

THE GRANULARITY CEILING IS APPLIED AT THE ACQUISITION SEAM, from
`context.perspective` — the verified credential the door decided under, never
a request parameter. This is the pattern the adopter page
`public/how-to/condition-acquisition-on-the-verified-credential.md`
documents, written here against that page. `granularity` itself IS a request
parameter, because a caller can only ever ask for LESS than its ceiling; the
ceiling is the envelope input, because naming your own ceiling would be asking
for more than the credential permits.

ROUTE B IS LOAD-BEARING HERE (`CP-SPEC-016` §F.4, ruled 2026-09-21). An
in-force threshold with no filed prospectus passage is SERVED, marked
`anchored: false`, classified `engineered`, and named in a finding. The gate
below enforces BOTH halves of the split invariant, so neither can be satisfied
by the other.
"""

from __future__ import annotations

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
GRANULARITY = "granularity"
COHORTS = "cohorts"
TRIGGER_PROXIMITY = "trigger_proximity"
LOAN_SAMPLE = "loan_sample"

# The source names `ccf_environment.yaml` declares.
SOURCE_RELATIONAL = "relational"
SOURCE_GRAPH = "graph"
SOURCE_DOCUMENTS = "documents"
SOURCE_CREDENTIALS = "credentials"

SYSTEM = "cp-16-abs-surveillance"
PLAN_ID = "cp-16.abs-surveillance.v1"
DEFAULT_GRANULARITY = "tranche"

NODE_MATCH_KEY = {
    "deal": "deal_node",
    "tranche": "tranche_node",
    "trigger": "trigger_node",
    "anchor": "anchor_node",
    "cohort": "cohort_node",
    "loan": "loan_node",
    "benchmark": "benchmark_node",
    "repurchase": "repurchase_node",
}
OBJECT_RULE = {
    "tranche": "tranche_object",
    "trigger": "trigger_object",
    "anchor": "anchor_object",
    "cohort": "cohort_object",
    "loan": "loan_object",
    "benchmark": "benchmark_object",
    "repurchase": "repurchase_object",
}
DEAL_SUBJECT_RULE = "deal_subject"


def plan_id() -> str:
    """One plan for the three perspectives; Pi branches on the perspective."""
    return PLAN_ID


# =========================================================================
# ACQUIRE — the ceiling from the credential, then edges first, nodes last
# =========================================================================


def acquire(context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
    effective = context.request.parameters
    as_of = _instant(effective[AS_OF])
    try:
        estate = acquisition.acquire(
            deal_id=context.request.subject,
            asked_at=context.request.asked_at,
            as_of=as_of,
            intent=context.request.intent,
            perspective=context.perspective.role,
            requested_granularity=str(effective.get(GRANULARITY) or DEFAULT_GRANULARITY),
            cohorts=_as_list(effective.get(COHORTS)),
            loan_sample=int(float(effective.get(LOAN_SAMPLE) or 0)),
            relational_settings=context.sources[SOURCE_RELATIONAL],
            graph_settings=context.sources[SOURCE_GRAPH],
            document_settings=context.sources[SOURCE_DOCUMENTS],
        )
    except acquisition.CeilingExceeded as above:
        # THE CEILING REFUSES; IT NEVER NARROWS (`D-IMPL-251`, `ABS-G09`). The
        # bound travels with the refusal so the caller can see what it may ask.
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(cause="unauthorized", detail=str(above),
                                      error_code="not-in-allowed-set"),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from above
    except acquisition.UnknownGranularity as unknown:
        # A DIFFERENT KIND OF REFUSAL: the value is not a meaningful question of
        # this class at all, which is the request contract's business and not
        # policy's (`D-IMPL-259`, `ABS-G08`).
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(cause="nonexistent", detail=str(unknown),
                                      error_code="granularity-not-in-domain"),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from unknown
    except acquisition.UnboundedLoanRequest as unbounded:
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(cause="unauthorized", detail=str(unbounded),
                                      error_code="unbounded-loan-request"),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from unbounded
    except acquisition.UnpricedIntent as unpriced:
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(cause="nonexistent", detail=str(unpriced),
                                      error_code="unpriced-intent"),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from unpriced
    return envelopes(estate, tenant_id=context.tenant_id, at=context.instant,
                     intent=context.request.intent)


def envelopes(
    estate: acquisition.Estate, *, tenant_id: str, at: datetime, intent: str
) -> tuple[SignalEnvelope, ...]:
    """The estate as dated claims — EDGES FIRST, ATTRIBUTED NODES LAST.

    A thin endpoint claim minted by an edge supersedes a richer claim at the
    same URI if it arrives after it (`D-IMPL-316`); the deal node, minted as an
    endpoint by every edge, is therefore written LAST of all.
    """
    if estate.empty:
        return ()
    assert estate.deal is not None
    deal_uri = f"{acquisition.vocabulary()['entity_uri_prefix']['deal']}{estate.deal_id}"
    edges = tuple(
        _edge(tenant_id=tenant_id, at=at, ordinal=ordinal, subject=deal_uri, record=record)
        for ordinal, record in enumerate(estate.records)
    )
    nodes = tuple(_node(tenant_id=tenant_id, at=at, record=record) for record in estate.records)
    deal = _deal(tenant_id=tenant_id, at=at, estate=estate, uri=deal_uri, intent=intent)
    return (*edges, *nodes, deal)


def _edge(*, tenant_id: str, at: datetime, ordinal: int, subject: str, record: acquisition.Record) -> SignalEnvelope:
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"edge/{record.edge_type}/{ordinal}",
        source=SourceIdentity(system_id=SYSTEM),
        ingestion_timestamp=at,
        observed_time=None,
        raw_payload={
            DEAL_SUBJECT_RULE: subject,
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
        # TWO OBSERVATION TYPES (`D-IMPL-332`). A cohort's month, a loan's
        # reporting period, a benchmark's period and a filing's date are DATED
        # EVENTS and carry their day. A tranche and a trigger definition are
        # STANDING STATE and carry none — which is why those classes declare
        # `decay: supersede-only` rather than a curve.
        observed_time=_midnight(record.dated),
        raw_payload={
            NODE_MATCH_KEY[record.entity_class]: record.entity_uri,
            "entity_uri": record.entity_uri,
            **dict(record.attributes),
        },
    )


def _deal(
    *, tenant_id: str, at: datetime, estate: acquisition.Estate, uri: str, intent: str
) -> SignalEnvelope:
    assert estate.deal is not None and estate.ceiling is not None
    terms = acquisition.vocabulary()
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=f"node/{uri}",
        source=SourceIdentity(system_id=SYSTEM),
        ingestion_timestamp=at,
        observed_time=None,
        raw_payload={
            NODE_MATCH_KEY["deal"]: uri,
            "entity_uri": uri,
            **estate.deal,
            "classification": terms["classification"]["assignment"]["deal"],
            "intent": intent,
            # THE BOUNDS, on the claim, because the asking principal is
            # entitled to know what bound its own answer — and `ABS-G10` reads
            # `granularity_ceiling` back against the constraint that was
            # actually resolved.
            "requested_granularity": estate.requested_granularity,
            "effective_granularity": estate.effective_granularity,
            "granularity_ceiling": estate.ceiling.ceiling,
            "ceiling_authority": estate.ceiling.authority,
            "ceiling_source": str(estate.ceiling.estate_value or "unstated"),
            # WHAT THE ASSEMBLY ACTUALLY TOUCHED. Measured, never declared.
            "records_materialized": str(estate.records_materialized),
            "records_scanned": str(estate.records_scanned),
            "blocks_scanned": str(estate.blocks_scanned),
            "cost_band": _cost_band(estate),
            "ledger_t": estate.ledger_t,
        },
    )


def _cost_band(estate: acquisition.Estate) -> str:
    """Which side of the only step that costs anything this question sits on.

    The estate's own curve says the three aggregate rungs are indistinguishable
    in block terms and that `loan` is orders of magnitude away, so the band is a
    RELATION rather than a number — and stays true at any pool size
    (`CP-SPEC-016` §A.2, `ABS-G15`).
    """
    return "loan-scale" if estate.effective_granularity == "loan" else "aggregate-scale"


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
# THE DECLARED GATE — `cp-16.surveillance-holds`
# =========================================================================


def surveillance_gate(*, candidate: ContextProductContract, evidence: object = None) -> str | None:
    """Ceiling · the two anchoring invariants · cost honesty · shape.

    Runs after the SDK's universal gates admitted the candidate and before the
    tolerance check; a string is a `ProductInvariantRefusal` by name.
    """
    del evidence
    payload = candidate.payload
    role = payload.get("perspective")
    if not isinstance(role, str) or role not in projection.PERSPECTIVE_CEILING:
        return f"the payload names perspective {role!r}, which `artifacts/perspectives.yaml` does not declare"

    effective = payload.get("effective_granularity")
    if payload.get("deal") is not None and not effective:
        return "the served product names no effective granularity (ABS-G10)"
    expected = projection.members_for(role, str(effective or ""))
    if set(payload) != expected:
        return (
            f"the payload's member set differs from the declared shape for perspective `{role}`"
            f" at granularity `{effective}` ({sorted(set(payload) ^ expected)}); the shape is a"
            f" function of the perspective and the effective granularity, never the deal (ABS-G12)"
        )

    # THE CEILING. Stated, equal to the role's declared ceiling, and never
    # exceeded by what was served. A computed-empty serve bound nothing.
    if payload.get("deal") is None:
        return None
    ceiling = payload.get("granularity_ceiling")
    declared = projection.PERSPECTIVE_CEILING[role]
    if ceiling != declared:
        return (
            f"the payload states ceiling {ceiling!r} for role `{role}`, but the resolved"
            f" constraint is {declared!r}; a stated ceiling that is not the resolved one is a"
            f" claim about policy the policy did not make (ABS-G10)"
        )
    order = list(acquisition.granularity_order())
    if str(effective) not in order:
        return f"the payload states effective granularity {effective!r}, outside the declared domain"
    if order.index(str(effective)) > order.index(str(ceiling)):
        return (
            f"the product served granularity `{effective}` above the ceiling `{ceiling}` for role"
            f" `{role}` (ABS-G09)"
        )

    # ANCHORING INVARIANT 1 — every PUBLICLY SOURCED threshold carries a
    # prospectus passage anchor.
    unanchored_seen: list[str] = []
    for item in payload.get("triggers") or ():
        anchored = str(item.get("anchored", "")).lower() == "true"
        classification = item.get("source_classification")
        if classification == "public" and not anchored:
            return (
                f"threshold {item.get('trigger_id')!r} is classified `public` and carries no"
                f" prospectus passage anchor; a publicly sourced threshold a committee cannot be"
                f" shown the text for is not served silently (ABS-G06)"
            )
        if anchored and not item.get("anchor_sha256"):
            return (
                f"threshold {item.get('trigger_id')!r} claims an anchor with no stored hash;"
                f" an anchor that cannot be re-hashed is not evidence (ABS-G06)"
            )
        if not anchored:
            unanchored_seen.append(str(item.get("trigger_id")))
            # NOTHING MAY IMPLY A PASSAGE EXISTS (`CP-SPEC-016` §F.4.0).
            for key in ("anchor_id", "anchor_text", "anchor_passage_id",
                        "anchor_document_id", "anchor_sha256"):
                if key in item:
                    return (
                        f"threshold {item.get('trigger_id')!r} is unanchored but carries `{key}`;"
                        f" an absent prospectus passage is stated, never encoded as a blank"
                        f" (ABS-G07)"
                    )

    # ANCHORING INVARIANT 2 — every threshold WITHOUT a public anchor is named.
    named = {str(item.get("trigger_id")) for item in payload.get("unanchored_thresholds") or ()}
    if set(unanchored_seen) != named:
        return (
            f"the product serves unanchored thresholds {sorted(unanchored_seen)} but names"
            f" {sorted(named)} in `unanchored_thresholds`; every threshold without a public"
            f" anchor is explicitly named as unanchored (ABS-G07)"
        )
    for item in payload.get("unanchored_thresholds") or ():
        if item.get("source_classification") == "public":
            return (
                f"threshold {item.get('trigger_id')!r} is named unanchored while classified"
                f" `public`; an unanchored threshold is classified by what actually sourced it"
                f" (ABS-G07)"
            )

    # PROXIMITY HONESTY. A threshold that is a formula is a finding, never a 0.
    for item in payload.get("trigger_proximity") or ():
        if item.get("distance") in (None, "") and not item.get("uncomputable_reason"):
            return (
                f"threshold {item.get('trigger_id')!r} has no distance and no reason;"
                f" an uncomputable proximity is named, never reported as zero (ABS-G16)"
            )

    # COST HONESTY. What the assembly touched is measured, and `loan` is the
    # only granularity that may sit on the loan-scale side.
    cost = payload.get("assembly_cost")
    if not isinstance(cost, Mapping):
        return "the payload carries no `assembly_cost`; what a question cost is part of the answer (ABS-G15)"
    for key in ("records_materialized", "records_scanned", "blocks_scanned", "cost_band"):
        if cost.get(key) in (None, ""):
            return f"`assembly_cost` states no {key!r} (ABS-G15)"
    if "milliseconds" in cost or "elapsed_ms" in cost:
        return (
            "`assembly_cost` reports a time; the estate's own runs put one granularity's median"
            " between 0.148 ms and 205.871 ms on identical data while its block count never"
            " moved, so time is not a cost statement here (ABS-G15)"
        )
    band = cost.get("cost_band")
    if (band == "loan-scale") != (str(effective) == "loan"):
        return (
            f"`assembly_cost` reports band {band!r} at granularity {effective!r}; the only step"
            f" that changes cost materially is loan-or-not (ABS-G15)"
        )
    materialized = int(str(cost.get("records_materialized") or 0))
    if materialized > acquisition.MAX_LOAN_SAMPLE + 200:
        return (
            f"the assembly materialized {materialized} records; this product does not"
            f" materialize its source population to answer a question about it (ABS-G13)"
        )

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


def _as_list(value: Any) -> tuple[str, ...]:
    """`cohorts` is declared an ARRAY and is passed as a list, never a string.

    A comma-joined string is refused by the SDK as a type mismatch, which is
    the right behavior and was measured on rung 18; this helper accepts only
    what the declaration allows.
    """
    if value is None or value == "":
        return ()
    if isinstance(value, str):
        raise ValueError(
            "`cohorts` is declared an array; pass a list of credit bands, not a string"
        )
    return tuple(str(item) for item in value)


def _midnight(day: date | None) -> datetime | None:
    if day is None:
        return None
    return datetime.combine(day, time.min, tzinfo=UTC)


def credential_grants(sources: Mapping[str, Mapping[str, str]]) -> Mapping[str, str]:
    """Bearer credential -> `principal_id`, read from the environment by NAME."""
    return {token: principal_id for principal_id, token in sources[SOURCE_CREDENTIALS].items()}
