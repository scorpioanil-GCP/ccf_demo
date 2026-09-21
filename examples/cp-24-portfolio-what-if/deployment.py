"""The deployment's half of `cib.portfolio-what-if`.

[ADAPT] the vocabulary here to your own product. The three verbs the paved road
binds (`acquire`, `assess`, and the declared gate `portfolio_gate`) live here.

THE GOVERNING RULE IS LOAD-BEARING IN THIS MODULE (`CP-SPEC-024` §D.3, ruled
2026-09-21):

    Observed evidence determines Context Debt. Scenario assumptions determine
    scenario-derived outputs. Scenario assumptions are NEVER evidence.

So `acquire` below binds the scenario and passes it to acquisition for
VALIDATION and for the book claim's echo only — no scenario magnitude is minted
onto any other claim, and `assess` never sees it. Two different scenarios over
one instant therefore produce identical `D_c` (`WIF-G13`).

AND TWO RULINGS:

- **`Q1`** — scenario magnitudes are INTEGERS IN CANONICAL UNITS (basis
  points). A noncanonical fractional form is REFUSED, never coerced; the
  `Decimal` conversion happens inside the arithmetic and never on a wire.
- **`Q2`** — CP-24 is a SIBLING of rung 23, not a composite over it. The
  population reader is rung 23's, written a second time; that duplication is a
  friction MEASUREMENT and no abstraction is pre-authorized.

And, unchanged from rung 23:

- population debt is the SDK's own combinator,
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
`WIF-G17` fails if this product's calculation touches them.
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
SCENARIO = "scenario"
COVERAGE_FLOOR = "coverage_floor_bp"

SOURCE_RELATIONAL = "relational"
SOURCE_GRAPH = "graph"
SOURCE_CREDENTIALS = "credentials"

SYSTEM = "cp-24-portfolio-what-if"
PLAN_ID = "cp-24.portfolio-what-if.v1"

NODE_MATCH_KEY = {
    "book": "book_node", "member": "member_node", "facility": "facility_node",
    "collateral": "collateral_node", "rate": "rate_node",
}
OBJECT_RULE = {
    "member": "member_object", "facility": "facility_object",
    "collateral": "collateral_object", "rate": "rate_object",
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
            scenario=acquisition.bind_scenario(_as_mapping(effective.get(SCENARIO))),
            requested_floor=_decimal(effective.get(COVERAGE_FLOOR)),
            relational_settings=context.sources[SOURCE_RELATIONAL],
            graph_settings=context.sources[SOURCE_GRAPH],
        )
    except acquisition.NotInBook as outside:
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(cause="unauthorized", detail=str(outside),
                                      error_code="not-in-book"),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from outside
    except acquisition.NoncanonicalMagnitude as noncanonical:
        # REFUSED, NEVER COERCED (`Q1`, `WIF-G04`). Rounding a float here would
        # produce an address nobody could reproduce.
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(cause="nonexistent", detail=str(noncanonical),
                                      error_code="noncanonical-magnitude"),
            resolution=RESOLVED_BY_THE_RESOLVER,
        ) from noncanonical
    except acquisition.ScenarioOutOfBounds as outside:
        raise GovernedRefusalRaised(
            SubjectUnavailableRefusal(cause="nonexistent", detail=str(outside),
                                      error_code="scenario-out-of-bounds"),
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
# THE DECLARED GATE — `cp-24.portfolio-holds`
# =========================================================================


def what_if_gate(*, candidate: ContextProductContract, evidence: object = None) -> str | None:
    """Population grain · the fact/hypothetical separation · stale-stays-stale."""
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
            f" never of the book or the scenario"
        )
    if payload.get("book") is None:
        return None

    population = payload.get("population") or []
    stated = str(payload.get("member_count", ""))
    if not stated or int(stated) != len(population):
        return (
            f"the payload states member_count {stated!r} against a population of"
            f" {len(population)}; the book's grain is a served fact"
        )
    for member in population:
        if member.get("in_book") != "true":
            return f"member {member.get('lei')!r} is served without declaring book membership"

    # THE ASSUMPTIONS ARE ECHOED, AND LABELLED AS ASSUMPTIONS.
    scenario = payload.get("scenario")
    if not isinstance(scenario, Mapping):
        return "the payload carries no `scenario`; a conditional answer states its condition (WIF-G07)"
    for key in ("rate_shift_bp", "collateral_shift_bp", "basis"):
        if scenario.get(key) in (None, ""):
            return f"`scenario` states no {key!r} (WIF-G07)"
    if scenario.get("basis") != "assumption":
        return (
            f"`scenario` names basis {scenario.get('basis')!r}; the assumptions are not evidence"
            f" and must say so (WIF-G07)"
        )

    # EVERY DERIVED MEASURE NAMES ITS BASIS AND THE ASSUMPTION THAT MADE IT.
    for member_name in ("interest_impact", "collateral_impact"):
        for item in payload.get(member_name) or ():
            if item.get("basis") != "scenario":
                return (
                    f"`{member_name}` carries a measure with basis {item.get('basis')!r};"
                    f" every scenario-derived measure is labelled `scenario` (WIF-G07)"
                )
            if not item.get("from_assumption"):
                return (
                    f"`{member_name}` carries a derived measure naming no assumption;"
                    f" a hypothetical must say which assumption produced it (WIF-G07)"
                )

    # OBSERVED BESIDE DERIVED — never a stressed figure alone.
    for item in payload.get("interest_impact") or ():
        for key in ("observed_rate_pct", "shifted_rate_pct", "drawn_amount"):
            if item.get(key) in (None, ""):
                return f"`interest_impact` states no {key!r}; a stressed figure is served beside its observed one (WIF-G08)"

    # STALE STAYS STALE. Ruled load-bearing: arithmetic resets nothing.
    for item in payload.get("collateral_impact") or ():
        for key in ("observed_valuation", "observed_at", "observed_age_days", "stressed_valuation"):
            if item.get(key) in (None, ""):
                return (
                    f"`collateral_impact` states no {key!r}; a scenario does not refresh its"
                    f" factual inputs and the observation's instant and age travel with the"
                    f" derived figure (WIF-G11)"
                )
        if item.get("observed_at") != item.get("valuation_instant_used"):
            return (
                f"`collateral_impact` used instant {item.get('valuation_instant_used')!r} against"
                f" an observation at {item.get('observed_at')!r}; arithmetic does not move an"
                f" observed instant (WIF-G12)"
            )

    # THE BASE RATE IS OBSERVED; THE SHIFTED RATE IS DERIVED FROM IT.
    observed = payload.get("observed_state")
    if not isinstance(observed, Mapping) or observed.get("base_rate_observed_at") in (None, ""):
        return "the payload carries no observed base rate with its instant (WIF-G09)"

    debt = payload.get("population_debt")
    if not isinstance(debt, Mapping) or debt.get("rule") != "per-factor-minimum":
        return "`population_debt` does not name the ruled per-factor-minimum law (WIF-G13)"
    if any(key.startswith("scenario") for key in debt):
        return (
            "`population_debt` names a scenario input; observed evidence determines debt and"
            " assumptions never do (WIF-G13)"
        )

    if "coverage_rollup" in expected:
        rollup = payload.get("coverage_rollup")
        if not isinstance(rollup, Mapping) or rollup.get("members") is None:
            return "the coverage roll-up names no members; a bare count is not the roll-up (WIF-G14)"

    vocabulary = set(projection.CLASSIFICATION_VOCABULARY)
    rows: list[tuple[str, Any]] = [
        (m, item) for m in projection.LIST_MEMBERS for item in payload.get(m) or ()
    ]
    for member_name, key in projection.NESTED_LIST_MEMBERS.items():
        holder = payload.get(member_name)
        if isinstance(holder, Mapping):
            rows.extend((f"{member_name}.{key}", item) for item in holder.get(key) or ())
    for member_name, item in rows:
        if not isinstance(item, Mapping):
            return f"member `{member_name}` carries a non-record entry {item!r}"
        classification = item.get("classification")
        if classification is not None and classification not in vocabulary:
            return f"member `{member_name}` carries classification {classification!r} outside the vocabulary"
    return None


# --- helpers ------------------------------------------------------------------------


def _instant(value: Any) -> datetime:
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        raise ValueError(f"an instant must carry a zone; got {value!r}")
    return parsed.astimezone(UTC)


def _as_mapping(value: Any) -> Mapping[str, Any]:
    """`scenario` is declared an OBJECT and is passed as a mapping."""
    if value is None or value == "":
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("`scenario` is declared an object; pass a mapping, not a scalar")
    return value


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
