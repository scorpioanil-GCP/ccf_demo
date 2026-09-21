"""The deployment's half of `cib.portfolio-early-warning`.

[ADAPT] the vocabulary here to your own product. The three verbs the paved road
binds (`acquire`, `assess`, and the declared gate `portfolio_gate`) live here.

TWO RULINGS ARE LOAD-BEARING IN THIS MODULE (`CP-SPEC-023` §F.4, 2026-09-21):

- **`Q1`** — population debt is the SDK's own combinator,
  `ccf.halflife.debt.compose_debt_factors`, applied to the MEMBERS' factors
  under the `D-IMPL-104` worst-factor rule: per-factor minimum strength across
  the population. Never `max(member D_c)`, never a re-implementation, never a
  second portfolio debt law. The combinator's contract is written for admitted
  *children*; calling it with members is the ruled reuse, and the naming is
  recorded as friction rather than repaired.
- **`Q2`** — the member list is canonicalized by the DEPLOYMENT before the
  effective request exists, because CP-23 knows its membership is semantically
  a set. `produce.book_question` is the one place that happens.

AND THE BOUNDARY: nothing here reads `limit_definition`, `bank_capital` or a
connection basis. Those are CP-21's regulatory large-exposure inputs, and
`PEW-G18` fails if this product's calculation touches them.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Any

import acquisition
import projection
from ccf.halflife.assessment import DebtAssessment
from ccf.halflife.debt import DebtFactors, compose_debt_factors
from ccf.products.contract import ContextProductContract
from ccf.products.debt_scorer import AssemblyDebtScorer, DeclaredFactor
from ccf.products.product import AcquisitionContext, AssessmentContext
from ccf.products.refusal import RESOLVED_BY_THE_RESOLVER, GovernedRefusalRaised, SubjectUnavailableRefusal
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

AS_OF = "as_of"
MEMBERS = "members"
SIGNAL_CLASSES = "signal_classes"
SEVERITY_FLOOR = "severity_floor"

SOURCE_RELATIONAL = "relational"
SOURCE_GRAPH = "graph"
SOURCE_CREDENTIALS = "credentials"

SYSTEM = "cp-23-portfolio-early-warning"
PLAN_ID = "cp-23.portfolio-early-warning.v1"

NODE_MATCH_KEY = {
    "book": "book_node", "member": "member_node", "facility": "facility_node",
    "covenant": "covenant_node", "signal_adverse_media": "adverse_media_node",
    "signal_8k_event": "eightk_node", "signal_trend_delta": "trend_node",
    "signal_spread_widening": "spread_node", "signal_warn_notice": "warn_node",
}
OBJECT_RULE = {
    "member": "member_object", "facility": "facility_object", "covenant": "covenant_object",
    "signal_adverse_media": "adverse_media_object", "signal_8k_event": "eightk_object",
    "signal_trend_delta": "trend_object", "signal_spread_widening": "spread_object",
    "signal_warn_notice": "warn_object",
}
BOOK_SUBJECT_RULE = "book_subject"


def plan_id() -> str:
    return PLAN_ID


# =========================================================================
# ACQUIRE
# =========================================================================


def acquire(context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
    effective = context.request.parameters
    as_of = _instant(effective[AS_OF])
    try:
        estate = acquisition.acquire(
            banker_id=context.request.subject,
            as_of=as_of,
            intent=context.request.intent,
            perspective=context.perspective.role,
            members=_as_list(effective.get(MEMBERS)),
            requested_classes=_as_list(effective.get(SIGNAL_CLASSES)),
            requested_floor=_decimal(effective.get(SEVERITY_FLOOR)),
            relational_settings=context.sources[SOURCE_RELATIONAL],
            graph_settings=context.sources[SOURCE_GRAPH],
        )
    except acquisition.NotInBook as outside:
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(cause="unauthorized", detail=str(outside),
                                      error_code="not-in-book"),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from outside
    except acquisition.FloorLowered as lowered:
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(cause="unauthorized", detail=str(lowered),
                                      error_code="severity-floor-lowered"),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from lowered
    except acquisition.UnknownRole as unknown:
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(cause="unauthorized", detail=str(unknown),
                                      error_code="role-not-declared"),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from unknown
    except acquisition.UnpricedIntent as unpriced:
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(cause="nonexistent", detail=str(unpriced),
                                      error_code="unpriced-intent"),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from unpriced
    return envelopes(estate, tenant_id=context.tenant_id, at=context.instant,
                     intent=context.request.intent, perspective=context.perspective.role,
                     as_of=str(effective[AS_OF]))


def envelopes(
    estate: acquisition.Estate, *, tenant_id: str, at: datetime, intent: str,
    perspective: str, as_of: str,
) -> tuple[SignalEnvelope, ...]:
    """EDGES FIRST, ATTRIBUTED NODES LAST (`D-IMPL-316`)."""
    if estate.empty:
        return ()
    assert estate.book is not None
    book_uri = f"{acquisition.vocabulary()['entity_uri_prefix']['book']}{estate.banker_id}"
    edges = tuple(
        _edge(tenant_id=tenant_id, at=at, ordinal=ordinal, subject=book_uri, record=record)
        for ordinal, record in enumerate(estate.records)
    )
    nodes = tuple(_node(tenant_id=tenant_id, at=at, record=record) for record in estate.records)
    book = _book(tenant_id=tenant_id, at=at, estate=estate, uri=book_uri,
                 intent=intent, perspective=perspective, as_of=as_of)
    return (*edges, *nodes, book)


def _edge(*, tenant_id: str, at: datetime, ordinal: int, subject: str, record: acquisition.Record) -> SignalEnvelope:
    return SignalEnvelope(
        tenant_id=tenant_id, envelope_id=f"edge/{record.edge_type}/{ordinal}",
        source=SourceIdentity(system_id=SYSTEM), ingestion_timestamp=at, observed_time=None,
        raw_payload={
            BOOK_SUBJECT_RULE: subject,
            OBJECT_RULE[record.entity_class]: record.entity_uri,
            "subject_uri": subject, "object_uri": record.entity_uri,
            "predicate": record.edge_type,
        },
    )


def _node(*, tenant_id: str, at: datetime, record: acquisition.Record) -> SignalEnvelope:
    return SignalEnvelope(
        tenant_id=tenant_id, envelope_id=f"node/{record.entity_uri}",
        source=SourceIdentity(system_id=SYSTEM), ingestion_timestamp=at,
        # TWO OBSERVATION TYPES (`D-IMPL-332`): membership and a facility's
        # terms are STANDING STATE and carry no day; a signal and a covenant
        # breach are DATED EVENTS and carry theirs.
        observed_time=_midnight(record.dated),
        raw_payload={
            NODE_MATCH_KEY[record.entity_class]: record.entity_uri,
            "entity_uri": record.entity_uri, **dict(record.attributes),
        },
    )


def _book(
    *, tenant_id: str, at: datetime, estate: acquisition.Estate, uri: str,
    intent: str, perspective: str, as_of: str,
) -> SignalEnvelope:
    assert estate.book is not None
    terms = acquisition.vocabulary()
    return SignalEnvelope(
        tenant_id=tenant_id, envelope_id=f"node/{uri}",
        source=SourceIdentity(system_id=SYSTEM), ingestion_timestamp=at, observed_time=None,
        raw_payload={
            NODE_MATCH_KEY["book"]: uri, "entity_uri": uri, **estate.book,
            "classification": terms["classification"]["assignment"]["book"],
            "intent": intent, "perspective": perspective, "as_of": as_of,
            "records_materialized": str(estate.records_materialized),
        },
    )


# =========================================================================
# ASSESS — `Q1`: the SDK's combinator, over MEMBERS
# =========================================================================


def assess(context: AssessmentContext) -> DebtAssessment:
    """The book's own factors, then the WORST FACTOR across its members.

    `Q1`, ruled 2026-09-21: use `ccf.halflife.debt.compose_debt_factors` — the
    SDK's `D-IMPL-104` rule, per-factor minimum strength — with the members as
    the composed sequence. Not `max(member D_c)`: collapsing each member to one
    number before composing loses *which* factor each was weak on, so a member
    weak only on freshness beside one weak only on completeness would read as
    one modest problem when in truth both are impaired.
    """
    assert context.half_life is not None and context.profile is not None
    scorer = AssemblyDebtScorer(
        table=context.half_life,
        profile=context.profile,
        completeness=DeclaredFactor(value=projection.view_completeness(context.view)),
        semantic_consistency=DeclaredFactor(value=Decimal("1.0000")),
    )
    assessment = scorer(view=context.view, evidence=context.evidence)
    members = projection.member_factors(context.view)
    if not members:
        return assessment
    composed = compose_debt_factors(assessment.factors, [factors for _, factors in members])
    return assessment.model_copy(update={"factors": composed, "debt": _debt_of(composed)})


def _debt_of(factors: DebtFactors) -> Decimal:
    from ccf.halflife.debt import context_debt  # noqa: PLC0415

    return context_debt(factors)


# =========================================================================
# THE DECLARED GATE — `cp-23.portfolio-holds`
# =========================================================================


def portfolio_gate(*, candidate: ContextProductContract, evidence: object = None) -> str | None:
    """Population grain · containment · worst factor · per-class freshness · boundary."""
    del evidence
    payload = candidate.payload
    role = payload.get("perspective")
    if not isinstance(role, str) or role not in projection.PERSPECTIVE_MEMBERS:
        return f"the payload names perspective {role!r}, which `artifacts/perspectives.yaml` does not declare"
    expected = projection.members_for(role)
    if set(payload) != expected:
        return (
            f"the payload's member set differs from the declared shape for role `{role}`"
            f" ({sorted(set(payload) ^ expected)}); the shape is a function of the perspective,"
            f" never of the book (PEW-G07)"
        )
    if payload.get("book") is None:
        return None

    # POPULATION GRAIN. The count is a served fact and agrees with the roster.
    population = payload.get("population") or []
    stated = str(payload.get("member_count", ""))
    if not stated or int(stated) != len(population):
        return (
            f"the payload states member_count {stated!r} against a population of"
            f" {len(population)}; the book's grain is a served fact (PEW-G03)"
        )
    if not population:
        return "the served book has no members; an empty population is refused rather than served (PEW-G03)"

    # CONTAINMENT. Every served member declares itself in the book.
    for member in population:
        if member.get("in_book") != "true":
            return (
                f"member {member.get('lei')!r} is served without declaring book membership;"
                f" a member outside the book is refused, never served (PEW-G02)"
            )

    # WORST FACTOR, AND UNDERSTANDABLE BY FACTOR (`Q1`).
    debt = payload.get("population_debt")
    if not isinstance(debt, Mapping):
        return "the payload carries no `population_debt` (PEW-G12)"
    for key in ("freshness", "completeness", "semantic_consistency", "rule"):
        if debt.get(key) in (None, ""):
            return f"`population_debt` states no {key!r} (PEW-G12)"
    if debt.get("rule") != "per-factor-minimum":
        return (
            f"`population_debt` names rule {debt.get('rule')!r}; the ruled law is the SDK's"
            f" per-factor minimum and no other portfolio debt law is invented (PEW-G12)"
        )
    weakest = debt.get("weakest_by_factor")
    if not isinstance(weakest, Mapping) or not weakest:
        return (
            "`population_debt` does not name which member each weak factor came from;"
            " population debt must be understandable BY FACTOR so a weak member cannot"
            " disappear behind a stronger aggregate (PEW-G12)"
        )

    # PER-CLASS FRESHNESS, never one book-wide timestamp.
    freshness = payload.get("signal_freshness_by_class")
    if not isinstance(freshness, list) or not freshness:
        return "the payload carries no per-class signal freshness (PEW-G09)"
    for row in freshness:
        if row.get("signal_class") in (None, "") or row.get("newest_observed_at") in (None, ""):
            return "a signal-freshness row names no class or no instant (PEW-G09)"
    for key in payload:
        if "book_freshness" in key or key == "portfolio_freshness_at":
            return (
                f"the payload names `{key}`; a single portfolio freshness timestamp would hide"
                f" a stale class behind a fresh one and is not minted (PEW-G09)"
            )

    # COVENANT HISTORY: present when the role sees it, and never dropped for
    # being currently quiet.
    if "covenant_history" in expected:
        history = payload.get("covenant_history")
        if history is None:
            return (
                "the payload omits `covenant_history`; zero active pressure is not absent"
                " history, and the member is served rather than dropped (PEW-G17)"
            )

    vocabulary = set(projection.CLASSIFICATION_VOCABULARY)
    rows: list[tuple[str, Any]] = [
        (member, item) for member in projection.LIST_MEMBERS for item in payload.get(member) or ()
    ]
    # The nested lists are reached BY NAME. Iterating their mapping would walk
    # its keys, which are strings and carry no classification.
    for member, key in projection.NESTED_LIST_MEMBERS.items():
        holder = payload.get(member)
        if isinstance(holder, Mapping):
            rows.extend((f"{member}.{key}", item) for item in holder.get(key) or ())
    for member, item in rows:
        if not isinstance(item, Mapping):
            return f"member `{member}` carries a non-record entry {item!r}"
        classification = item.get("classification")
        if classification is not None and classification not in vocabulary:
            return f"member `{member}` carries classification {classification!r} outside the vocabulary"
    return None


# --- helpers ------------------------------------------------------------------------


def _instant(value: Any) -> datetime:
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        raise ValueError(f"an instant must carry a zone; got {value!r}")
    return parsed.astimezone(UTC)


def _as_list(value: Any) -> tuple[str, ...]:
    if value is None or value == "":
        return ()
    if isinstance(value, str):
        raise ValueError("this parameter is declared an array; pass a list, not a string")
    return tuple(str(item) for item in value)


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


def _midnight(day: date | None) -> datetime | None:
    if day is None:
        return None
    return datetime.combine(day, time.min, tzinfo=UTC)


def credential_grants(sources: Mapping[str, Mapping[str, str]]) -> Mapping[str, str]:
    return {token: principal_id for principal_id, token in sources[SOURCE_CREDENTIALS].items()}
