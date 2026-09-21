"""Pi for `cib.portfolio-what-if` — one plan, three roles, one population.

[ADAPT] the payload shape and the evaluation rule here. Pi reads the governed
view and nothing beside it.

THE ANSWER IS CONDITIONAL, AND SAYS SO. Every measure here is either OBSERVED
(and carries the claim it came from) or DERIVED under a stated assumption (and
carries `basis: scenario` plus the assumption that produced it). A reader can
never mistake one for the other (`CP-SPEC-024` §D.3, ruled 2026-09-21).

THE GOVERNING RULE, which this module must not violate:

    Observed evidence determines Context Debt. Scenario assumptions determine
    scenario-derived outputs. Scenario assumptions are NEVER evidence.

A SCENARIO DOES NOT REFRESH ITS FACTUAL INPUTS. A -10% shift on a 320-day-old
appraisal yields a STRESSED STALE valuation, and every derived figure carries
the observation's own instant and age so the staleness is visible rather than
lost in the arithmetic. Nothing here recomputes an instant (`WIF-G11`,
`WIF-G12`).

NO MODEL. Each impact is arithmetic over an observed value, a declared
sensitivity and a stated assumption. Nothing is fitted or predicted.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml
from ccf.graph.protocols import GraphView
from ccf.halflife.debt import DebtFactors
from ccf.operators.base import OperatorOutput
from ccf.projection.plan import Perspective, ProjectionOutput

HERE = Path(__file__).parent
PERSPECTIVES = HERE / "artifacts" / "perspectives.yaml"
SENSITIVITIES = HERE / "artifacts" / "sensitivities.yaml"

_DECLARED: Mapping[str, Any] = yaml.safe_load(PERSPECTIVES.read_text(encoding="utf-8"))["declaration"]
_SENS: Mapping[str, Any] = yaml.safe_load(SENSITIVITIES.read_text(encoding="utf-8"))["declaration"]

COMMON_MEMBERS: tuple[str, ...] = tuple(_DECLARED["common_members"])
PERSPECTIVE_MEMBERS: Mapping[str, tuple[str, ...]] = {
    name: tuple(spec.get("members", ()) or ()) for name, spec in _DECLARED["perspectives"].items()
}
PRINCIPAL_ID: Mapping[str, str] = {
    name: str(spec["principal_id"]) for name, spec in _DECLARED["perspectives"].items()
}
CLASSIFICATION_VOCABULARY: tuple[str, ...] = tuple(_DECLARED["classification_vocabulary"])
LIST_MEMBERS: tuple[str, ...] = tuple(_DECLARED["classified_list_members"])
NESTED_LIST_MEMBERS: Mapping[str, str] = dict(_DECLARED["nested_classified_lists"])
BASIS_POINT = Decimal(str(_SENS["basis_point"]))

#: The `collateral` class's declared half-life, read from the Control Plane
#: document rather than restated here — the curve is the deployment's
#: declaration, never this module's constant.
_COLLATERAL_HALF_LIFE_SECONDS: int = int(
    yaml.safe_load((HERE / "ccf_config.yaml").read_text(encoding="utf-8"))
    ["half_life"]["collateral"]["half_life_seconds"]
)


def members_for(perspective: str) -> set[str]:
    return set(COMMON_MEMBERS) | set(PERSPECTIVE_MEMBERS[perspective])


class WhatIfProjection:
    """One `plan_id`; `invoke` branches on `perspective.role`."""

    def __init__(self, *, plan_id: str, required: tuple[str, ...], as_of: str) -> None:
        self._plan_id, self._required, self._as_of = plan_id, required, as_of

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        return self._required

    def invoke(
        self, *, view: GraphView, operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective, temporal_boundary: datetime,
    ) -> ProjectionOutput:
        del operator_outputs, temporal_boundary
        role = perspective.role
        if role not in PERSPECTIVE_MEMBERS:
            raise ValueError(f"perspective {role!r} is not declared in `artifacts/perspectives.yaml`")
        books = [r for r in view.entities if r.claim.entity_class == "book"]
        if len(books) > 1:
            raise ValueError("the view holds more than one book; it was not written by one question")
        anchor = books[0] if books else None
        by_class: dict[str, list[Mapping[str, str]]] = {}
        for record in view.entities:
            by_class.setdefault(record.claim.entity_class, []).append(dict(record.claim.attributes))

        attributes = dict(anchor.claim.attributes) if anchor is not None else {}
        population = _population(by_class)
        facilities = by_class.get("facility", [])

        scenario = _scenario(attributes)
        observed = _observed_state(attributes, by_class)
        facilities = by_class.get("facility", [])

        payload: dict[str, Any] = {
            "perspective": role,
            "as_of": self._as_of,
            "intent": attributes.get("intent", ""),
            "book": None if anchor is None else _book_member(attributes),
            # THE ASSUMPTIONS, LABELLED AS ASSUMPTIONS. Echoed so the answer
            # states its own condition; the authoritative record of them is the
            # effective request, not this echo.
            "scenario": scenario,
            "population": population,
            "member_count": attributes.get("member_count", "0" if anchor is None else ""),
            "observed_state": observed,
            "interest_impact": _interest_impact(facilities, population, observed, scenario),
            "population_debt": _population_debt(view),
            "findings": _findings(by_class, population, facilities),
            "entities_in_view": len(view.entities),
            "edge_types_served": sorted({e.claim.relationship_type for e in view.relationships}),
        }
        for member in PERSPECTIVE_MEMBERS[role]:
            payload[member] = _role_member(member, by_class, population, facilities,
                                           scenario=scenario, attributes=attributes)
        return ProjectionOutput(plan_id=self._plan_id, payload=payload)


# =========================================================================
# THE SEPARATION — what was assumed, and what was observed
# =========================================================================


def _scenario(attributes: Mapping[str, str]) -> Mapping[str, Any]:
    """The bound assumptions, in canonical units, labelled `assumption`.

    **No source lineage, and that is the point.** An assumption did not come
    from anywhere in the world; pretending otherwise is exactly the confusion
    this rung exists to prevent (`WIF-G07`).
    """
    return {
        "basis": "assumption",
        "units": "basis_points",
        "rate_shift_bp": attributes.get("rate_shift_bp", "0"),
        "collateral_shift_bp": attributes.get("collateral_shift_bp", "0"),
        "collateral_class": attributes.get("collateral_class", ""),
        "horizon_months": attributes.get("horizon_months", ""),
        "sensitivity_version": attributes.get("sensitivity_version", ""),
        "note": (
            "these are hypothetical inputs supplied by the caller, not observations;"
            " they carry no source lineage and do not affect Context Debt"
        ),
    }


def _observed_state(
    attributes: Mapping[str, str], by_class: Mapping[str, list[Mapping[str, str]]]
) -> Mapping[str, Any]:
    """The facts the scenario is applied TO, each with its own instant."""
    rates = by_class.get("rate", [])
    collateral = by_class.get("collateral", [])
    ages = [int(str(row.get("valuation_age_days", "0")) or 0) for row in collateral]
    return {
        "basis": "observed",
        "base_rate_series": attributes.get("base_rate_series", ""),
        "base_rate_pct": attributes.get("base_rate_pct", ""),
        "base_rate_observed_at": attributes.get("base_rate_observed_at", ""),
        "base_rate_claims": str(len(rates)),
        "collateral_assets": str(len(collateral)),
        # THE STALENESS OF THE EVIDENCE, stated before anything is stressed.
        "collateral_age_days_min": str(min(ages)) if ages else "",
        "collateral_age_days_max": str(max(ages)) if ages else "",
    }


# =========================================================================
# LIMB 1 — interest cost and headroom
# =========================================================================


def _interest_impact(
    facilities: Sequence[Mapping[str, str]], population: Sequence[Mapping[str, str]],
    observed: Mapping[str, Any], scenario: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    """Incremental interest on the DRAWN balance at the shifted rate.

    Observed: the drawn balance and the base rate. Assumed: the shift. Derived:
    the shifted rate and the incremental cost — and both say so.
    """
    base = _decimal(observed.get("base_rate_pct"))
    shift_bp = _decimal(scenario.get("rate_shift_bp")) or Decimal(0)
    horizon = _decimal(scenario.get("horizon_months")) or Decimal(12)
    shifted = None if base is None else base + (shift_bp * BASIS_POINT * Decimal(100))

    by_member: dict[str, dict[str, Decimal]] = {}
    for facility in facilities:
        lei = str(facility.get("lei", ""))
        entry = by_member.setdefault(lei, {"commitment": Decimal(0), "drawn": Decimal(0)})
        entry["commitment"] += _decimal(facility.get("commitment_amount")) or Decimal(0)
        entry["drawn"] += _decimal(facility.get("drawn_amount")) or Decimal(0)

    rows: list[Mapping[str, Any]] = []
    for member in population:
        lei = str(member.get("lei", ""))
        entry = by_member.get(lei)
        if entry is None:
            continue
        drawn, commitment = entry["drawn"], entry["commitment"]
        incremental = (drawn * shift_bp * BASIS_POINT * horizon / Decimal(12)).quantize(Decimal("0.01"))
        rows.append({
            "lei": lei,
            # OBSERVED, beside the derived (`WIF-G08`).
            "drawn_amount": str(drawn),
            "commitment_amount": str(commitment),
            "observed_rate_pct": str(base) if base is not None else "",
            "observed_rate_at": str(observed.get("base_rate_observed_at", "")),
            # DERIVED, and labelled.
            "shifted_rate_pct": str(shifted) if shifted is not None else "",
            "incremental_interest": str(incremental),
            "headroom_after": str(commitment - drawn - incremental),
            "basis": "scenario",
            "from_assumption": "rate_shift_bp",
            "classification": "internal",
        })
    return sorted(rows, key=lambda row: row["lei"])


# =========================================================================
# LIMB 2 — secured coverage, and STALE STAYS STALE
# =========================================================================


def _collateral_impact(
    by_class: Mapping[str, list[Mapping[str, str]]], scenario: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    """Stressed collateral value — with the observation's own instant and age.

    **A scenario does not refresh its factual inputs** (ruled 2026-09-21). The
    shift applies ONLY to the named class; every other class is served
    unchanged and says so. The estate's haircut is never altered.
    """
    shift_bp = _decimal(scenario.get("collateral_shift_bp")) or Decimal(0)
    stressed_class = str(scenario.get("collateral_class", "") or "")
    rows: list[Mapping[str, Any]] = []
    for asset in by_class.get("collateral", ()):
        category = str(asset.get("category", ""))
        applies = (category == stressed_class)
        valuation = _decimal(asset.get("valuation")) or Decimal(0)
        haircut = _decimal(asset.get("haircut")) or Decimal(0)
        factor = (Decimal(1) + shift_bp * BASIS_POINT) if applies else Decimal(1)
        stressed = (valuation * factor).quantize(Decimal("0.01"))
        rows.append({
            "asset_id": str(asset.get("asset_id", "")),
            "lei": str(asset.get("lei", "")),
            "category": category,
            # OBSERVED — value, instant and age, carried verbatim.
            "observed_valuation": str(valuation),
            "observed_at": str(asset.get("valuation_date", "")),
            "observed_age_days": str(asset.get("valuation_age_days", "")),
            "haircut": str(haircut),
            # DERIVED — and it used EXACTLY the observed instant above. No
            # arithmetic moves an observed instant (`WIF-G12`).
            "valuation_instant_used": str(asset.get("valuation_date", "")),
            "stressed_valuation": str(stressed),
            "stressed_secured_value": str((stressed * (Decimal(1) - haircut)).quantize(Decimal("0.01"))),
            "shift_applied": str(applies).lower(),
            "basis": "scenario",
            "from_assumption": "collateral_shift_bp" if applies else "none-this-class-unshifted",
            "classification": "internal",
        })
    return sorted(rows, key=lambda row: row["asset_id"])


# =========================================================================
# LIMB 3 — the portfolio roll-up
# =========================================================================


def _coverage_rollup(
    by_class: Mapping[str, list[Mapping[str, str]]], population: Sequence[Mapping[str, str]],
    facilities: Sequence[Mapping[str, str]], scenario: Mapping[str, Any],
    attributes: Mapping[str, str],
) -> Mapping[str, Any]:
    """Which members fall below the declared coverage floor once stressed.

    **Names WHICH members, never only how many** (`WIF-G14`).
    """
    floor_bp = _decimal(attributes.get("coverage_floor_bp")) or Decimal(10000)
    floor = floor_bp * BASIS_POINT
    impacts = _collateral_impact(by_class, scenario)
    secured: dict[str, Decimal] = {}
    for row in impacts:
        lei = str(row["lei"])
        secured[lei] = secured.get(lei, Decimal(0)) + (_decimal(row["stressed_secured_value"]) or Decimal(0))
    drawn: dict[str, Decimal] = {}
    for facility in facilities:
        lei = str(facility.get("lei", ""))
        drawn[lei] = drawn.get(lei, Decimal(0)) + (_decimal(facility.get("drawn_amount")) or Decimal(0))

    members: list[Mapping[str, Any]] = []
    for member in population:
        lei = str(member.get("lei", ""))
        owed, cover = drawn.get(lei, Decimal(0)), secured.get(lei, Decimal(0))
        if not owed:
            continue
        ratio = (cover / owed).quantize(Decimal("0.0001"))
        members.append({
            "lei": lei,
            "drawn_amount": str(owed),
            "stressed_secured_value": str(cover),
            "coverage_ratio": str(ratio),
            "below_floor": str(ratio < floor).lower(),
            "basis": "scenario",
            "from_assumption": "collateral_shift_bp",
            "classification": "internal",
        })
    below = [row for row in members if row["below_floor"] == "true"]
    return {
        "basis": "scenario",
        "floor_bp": str(floor_bp),
        "floor_ratio": str(floor),
        "members_evaluated": str(len(members)),
        "members_below_floor": str(len(below)),
        # THE NAMES, not just the count.
        "below_floor_leis": sorted(row["lei"] for row in below),
        "members": sorted(members, key=lambda row: row["lei"]),
    }


def _role_member(
    member: str, by_class: Mapping[str, list[Mapping[str, str]]],
    population: Sequence[Mapping[str, str]], facilities: Sequence[Mapping[str, str]],
    *, scenario: Mapping[str, Any], attributes: Mapping[str, str],
) -> Any:
    if member == "collateral_impact":
        return _collateral_impact(by_class, scenario)
    if member == "coverage_rollup":
        return _coverage_rollup(by_class, population, facilities, scenario, attributes)
    raise ValueError(f"member {member!r} is declared but Pi emits nothing for it")


# =========================================================================
# THE POPULATION AND ITS MEASURES
# =========================================================================


def _population(by_class: Mapping[str, list[Mapping[str, str]]]) -> list[Mapping[str, str]]:
    return _items(by_class.get("member", ()), key="lei",
                  fields=("lei", "legal_name", "sic", "sic_description", "in_book",
                          "is_primary", "assigned_date", "classification"))






def member_factors(view: GraphView) -> list[tuple[str, DebtFactors]]:
    """One `DebtFactors` per member — the sequence the SDK combinator composes.

    **Built from OBSERVED evidence only**, which is why two scenarios over one
    instant give identical debt (`WIF-G13`).

    FRESHNESS is the AGE of the member's observed collateral, so a
    320-day-old appraisal genuinely lowers it — the staleness the scenario
    cannot refresh shows up here rather than being hidden by the arithmetic.
    COMPLETENESS is which evidence classes the member carries. They measure
    different things and are kept apart.
    """
    members = [r for r in view.entities if r.claim.entity_class == "member"]
    if not members:
        return []
    ages: dict[str, int] = {}
    for record in view.entities:
        if record.claim.entity_class == "collateral":
            lei = str(record.claim.attributes.get("lei", ""))
            age = int(str(record.claim.attributes.get("valuation_age_days", "0")) or 0)
            ages[lei] = max(ages.get(lei, 0), age)
    with_facility = {
        str(r.claim.attributes.get("lei", "")) for r in view.entities
        if r.claim.entity_class == "facility"
    }
    # DECAY ON THE DECLARED HALF-LIFE, not on a horizon this module invents.
    # `ccf_config.yaml` declares the `collateral` class's λ_c, so the curve a
    # member's freshness follows is the Control Plane's and not Pi's.
    half_life_days = Decimal(_COLLATERAL_HALF_LIFE_SECONDS) / Decimal(86400)
    out: list[tuple[str, DebtFactors]] = []
    for record in members:
        lei = str(record.claim.attributes.get("lei", ""))
        # No collateral observation is an absence of EVIDENCE, not a stale
        # one; it lands on completeness, never on freshness.
        oldest = ages.get(lei)
        freshness = (
            Decimal(1) if oldest is None
            else Decimal(2) ** (-(Decimal(oldest) / half_life_days))
        )
        completeness = Decimal("1.0") if lei in with_facility else Decimal("0.6")
        if oldest is None:
            completeness = completeness * Decimal("0.8")
        out.append((lei, DebtFactors(
            freshness=_clamp(freshness), completeness=_clamp(completeness),
            semantic_consistency=Decimal("1.0"),
        )))
    return out


def _population_debt(view: GraphView) -> Mapping[str, Any]:
    """The composed factors, and WHICH member each weak factor came from.

    `Q1`, ruled: the law is the SDK's `compose_debt_factors` — per-factor
    minimum strength — and the payload must make it **understandable by
    factor**, so a weak member cannot disappear behind a stronger aggregate.
    """
    from ccf.halflife.debt import compose_debt_factors, context_debt  # noqa: PLC0415

    members = member_factors(view)
    if not members:
        return {"rule": "per-factor-minimum", "members": "0",
                "freshness": "1", "completeness": "1", "semantic_consistency": "1",
                "debt": "0", "weakest_by_factor": {}}
    own = DebtFactors(freshness=Decimal("1.0"), completeness=Decimal("1.0"),
                      semantic_consistency=Decimal("1.0"))
    composed = compose_debt_factors(own, [factors for _, factors in members])
    weakest = {
        factor: min(members, key=lambda pair: getattr(pair[1], factor))[0]
        for factor in ("freshness", "completeness", "semantic_consistency")
    }
    return {
        "rule": "per-factor-minimum",
        "rule_authority": "D-IMPL-104",
        "members": str(len(members)),
        "freshness": str(composed.freshness),
        "completeness": str(composed.completeness),
        "semantic_consistency": str(composed.semantic_consistency),
        "debt": str(context_debt(composed)),
        # NOT `max(member D_c)`. The alternative law is served beside the ruled
        # one so a reader can compare them — and on THIS estate the two
        # coincide, because the member weakest on freshness also sits at the
        # completeness floor. That the difference is real is proved by a
        # positive control rather than by the book (`WIF-F-01`).
        "max_member_debt": str(max(context_debt(f) for _, f in members)),
        "weakest_by_factor": weakest,
    }






def _findings(
    by_class: Mapping[str, list[Mapping[str, str]]],
    population: Sequence[Mapping[str, str]], facilities: Sequence[Mapping[str, str]],
) -> list[Mapping[str, str]]:
    """What the product could not do, named — never dropped and never faked."""
    findings: list[Mapping[str, str]] = []
    covered = {str(f.get("lei", "")) for f in facilities}
    uncovered = [str(m.get("lei", "")) for m in population if str(m.get("lei", "")) not in covered]
    if uncovered:
        findings.append({
            "finding": "members-without-a-facility",
            "detail": (
                f"{len(uncovered)} of {len(population)} members carry no facility, so no interest"
                f" impact is computed for them; they remain members"
            ),
        })
    stale = [
        row for row in by_class.get("collateral", ())
        if int(str(row.get("valuation_age_days", "0")) or 0) > 180
    ]
    if stale:
        findings.append({
            "finding": "stressed-stale-valuations",
            "detail": (
                f"{len(stale)} collateral observation(s) are over 180 days old. A scenario does"
                f" not refresh a factual input, so these yield STRESSED STALE valuations and"
                f" their age travels with every derived figure"
            ),
        })
    if not by_class.get("collateral"):
        findings.append({
            "finding": "no-observed-collateral",
            "detail": "no member of this population has a collateral valuation at this instant",
        })
    return sorted(findings, key=lambda row: row["finding"])


def _book_member(attributes: Mapping[str, str]) -> Mapping[str, Any]:
    return {
        "banker_id": attributes.get("banker_id", ""),
        "banker_name": attributes.get("banker_name", ""),
        "banker_role": attributes.get("banker_role", ""),
        "banker_desk": attributes.get("banker_desk", ""),
        "member_digest": attributes.get("member_digest", ""),
        "members_requested": attributes.get("members_requested", ""),
        "book_member_total": attributes.get("book_member_total", ""),
        "book_roster_total": attributes.get("book_roster_total", ""),
        "facility_covered_count": attributes.get("facility_covered_count", ""),
        "coverage_floor_bp": attributes.get("coverage_floor_bp", ""),
        "sensitivity_version": attributes.get("sensitivity_version", ""),
        "records_materialized": attributes.get("records_materialized", ""),
    }


# --- helpers ------------------------------------------------------------------------


def _items(records: Any, *, key: str, fields: Sequence[str]) -> list[Mapping[str, str]]:
    rows = [{f: str(r.get(f, "")) for f in fields} for r in records]
    return sorted(rows, key=lambda row: row[key])


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, ArithmeticError):
        return None


def _pct(part: Decimal, whole: Decimal) -> Decimal:
    if not whole:
        return Decimal("0.00")
    return (Decimal(100) * part / whole).quantize(Decimal("0.01"))


def _clamp(value: Decimal) -> Decimal:
    return max(Decimal("0"), min(Decimal("1"), value)).quantize(Decimal("0.0001"))


def _instant(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    from datetime import UTC  # noqa: PLC0415

    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def view_completeness(view: GraphView) -> Decimal:
    """`C` = required classes present / required, TIMES the share of the book seen.

    A MEMBER THE ROLE EXCLUDED STILL COUNTS (`WIF-G13`, `CP-SPEC-024` §E.2) —
    but a member the CALLER narrowed away does not, because narrowing your own
    question denies you nothing. `book_member_total` is therefore the scope
    after the caller's narrowing and before the role's.
    The book genuinely is less complete for a role that may not see part of it,
    and letting the narrowed role reach completeness 1.0 would make the
    entitlement look free — the cost-hiding rungs 15 and 16 ruled against.
    """
    import acquisition  # noqa: PLC0415

    books = [r for r in view.entities if r.claim.entity_class == "book"]
    if not books:
        return Decimal("0.0000")
    required = acquisition.required_classes()
    present = {r.claim.entity_class for r in view.entities}
    found = sum(1 for entity_class in required if entity_class in present)
    by_class = Decimal(found) / Decimal(len(required))

    attributes = books[0].claim.attributes
    total = _decimal(attributes.get("book_member_total")) or Decimal(0)
    seen = _decimal(attributes.get("member_count")) or Decimal(0)
    share = (seen / total) if total else Decimal(1)
    return (by_class * share).quantize(Decimal("0.0001"))
