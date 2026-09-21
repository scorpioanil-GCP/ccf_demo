"""Pi for `cib.portfolio-early-warning` — one plan, three roles, one population.

[ADAPT] the payload shape and the evaluation rule here. Pi reads the governed
view and nothing beside it.

THE ANSWER IS A PROPERTY OF A POPULATION (`CP-SPEC-023` §0.2a). The measures
are set properties — utilization across the book's facilities, a tiered signal
census, concentration by name and sector, and a debt that is the WORST FACTOR
across members rather than an average.

PER-CLASS FRESHNESS IS NEVER AVERAGED (ruled 2026-09-21). Each of the five
signal classes carries its own newest observation and its own age, so a reader
can see WHICH class is weak. No single portfolio freshness timestamp is minted;
an average would let a fresh class hide a stale one.
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
TIERS = HERE / "artifacts" / "severity-tiers.yaml"

_DECLARED: Mapping[str, Any] = yaml.safe_load(PERSPECTIVES.read_text(encoding="utf-8"))["declaration"]
_TIERS: Mapping[str, Any] = yaml.safe_load(TIERS.read_text(encoding="utf-8"))["declaration"]

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
SIGNAL_PREFIX = "signal_"


def members_for(perspective: str) -> set[str]:
    return set(COMMON_MEMBERS) | set(PERSPECTIVE_MEMBERS[perspective])


class PortfolioProjection:
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
        signals = _signals(by_class)

        payload: dict[str, Any] = {
            "perspective": role,
            "as_of": self._as_of,
            "intent": attributes.get("intent", ""),
            "book": None if anchor is None else _book_member(attributes),
            "population": population,
            "member_count": attributes.get("member_count", "0" if anchor is None else ""),
            "utilization": _utilization(facilities, population),
            "early_warning": _early_warning(signals),
            "signal_freshness_by_class": _freshness_by_class(signals, as_of=self._as_of),
            "population_debt": _population_debt(view),
            "findings": _findings(by_class, population, facilities),
            "entities_in_view": len(view.entities),
            "edge_types_served": sorted({e.claim.relationship_type for e in view.relationships}),
        }
        for member in PERSPECTIVE_MEMBERS[role]:
            payload[member] = _role_member(member, by_class, population, facilities)
        return ProjectionOutput(plan_id=self._plan_id, payload=payload)


# =========================================================================
# THE POPULATION AND ITS MEASURES
# =========================================================================


def _population(by_class: Mapping[str, list[Mapping[str, str]]]) -> list[Mapping[str, str]]:
    return _items(by_class.get("member", ()), key="lei",
                  fields=("lei", "legal_name", "sic", "sic_description", "in_book",
                          "is_primary", "assigned_date", "classification"))


def _utilization(
    facilities: Sequence[Mapping[str, str]], population: Sequence[Mapping[str, str]]
) -> list[Mapping[str, Any]]:
    """Per member: commitment, drawn, headroom and utilization.

    A facility with NO drawdown row is zero utilization WITH its drawdown
    count, so zero-because-undrawn and zero-because-unobserved stay
    distinguishable (`PEW-G15`). A member with no facility keeps its row with
    `has_facility: false` rather than being dropped (`PEW-G16`).
    """
    by_member: dict[str, dict[str, Any]] = {}
    for facility in facilities:
        lei = str(facility.get("lei", ""))
        entry = by_member.setdefault(lei, {
            "lei": lei, "facility_count": 0, "commitment": Decimal(0),
            "drawn": Decimal(0), "drawdown_count": 0,
        })
        entry["facility_count"] += 1
        entry["commitment"] += _decimal(facility.get("commitment_amount")) or Decimal(0)
        entry["drawn"] += _decimal(facility.get("drawn_amount")) or Decimal(0)
        entry["drawdown_count"] += int(str(facility.get("drawdown_count", "0")) or 0)

    rows: list[Mapping[str, Any]] = []
    for member in population:
        lei = str(member.get("lei", ""))
        entry = by_member.get(lei)
        if entry is None:
            rows.append({"lei": lei, "has_facility": "false", "facility_count": "0",
                         "commitment": "0", "drawn": "0", "headroom": "0",
                         "utilization_pct": "", "drawdown_count": "0",
                         "classification": "internal"})
            continue
        commitment, drawn = entry["commitment"], entry["drawn"]
        rows.append({
            "lei": lei, "has_facility": "true",
            "facility_count": str(entry["facility_count"]),
            "commitment": str(commitment), "drawn": str(drawn),
            "headroom": str(commitment - drawn),
            "utilization_pct": str(_pct(drawn, commitment)),
            "drawdown_count": str(entry["drawdown_count"]),
            "classification": "internal",
        })
    return sorted(rows, key=lambda row: row["lei"])


def _signals(by_class: Mapping[str, list[Mapping[str, str]]]) -> Mapping[str, list[Mapping[str, str]]]:
    return {name: rows for name, rows in by_class.items() if name.startswith(SIGNAL_PREFIX)}


def _early_warning(signals: Mapping[str, list[Mapping[str, str]]]) -> list[Mapping[str, Any]]:
    """The tiered census — every signal placed in a tier the ARTIFACT declares."""
    tiers = sorted(
        ({"tier": str(t["tier"]), "label": str(t["label"]),
          "minimum": Decimal(str(t["minimum_severity"]))} for t in _TIERS["tiers"]),
        key=lambda t: -t["minimum"],
    )
    version = str(yaml.safe_load(TIERS.read_text(encoding="utf-8"))["semver"])
    out: list[Mapping[str, Any]] = []
    for entity_class, rows in sorted(signals.items()):
        for row in rows:
            severity = _decimal(row.get("severity")) or Decimal(0)
            tier = next((t for t in tiers if severity >= t["minimum"]), tiers[-1])
            out.append({
                "signal_id": str(row.get("signal_id", "")),
                "lei": str(row.get("lei", "")),
                "signal_class": entity_class,
                "signal_type": str(row.get("signal_type", "")),
                "severity": str(severity),
                "observed_at": str(row.get("observed_at", "")),
                "tier": tier["tier"], "tier_label": tier["label"],
                # THE ARTIFACT THAT TIERED IT, so no tier is hard-coded.
                "tier_policy_version": version,
                "classification": str(row.get("classification", "")),
            })
    return sorted(out, key=lambda row: (row["tier"], row["lei"], row["signal_id"]))


def _freshness_by_class(
    signals: Mapping[str, list[Mapping[str, str]]], *, as_of: str
) -> list[Mapping[str, Any]]:
    """PER CLASS — never one book-wide number (`PEW-G09`).

    Each class reports its own newest observation, its own age and how many
    members it covers, so a reader can see *which* class is weak. An average
    would let a 12-day class hide a 53-day one.
    """
    cut = _instant(as_of)
    out: list[Mapping[str, Any]] = []
    for entity_class, rows in sorted(signals.items()):
        instants = [_instant(str(row.get("observed_at", ""))) for row in rows]
        instants = [i for i in instants if i is not None]
        if not instants:
            continue
        newest = max(instants)
        out.append({
            "signal_class": entity_class,
            "observations": str(len(rows)),
            "members_covered": str(len({str(row.get("lei", "")) for row in rows})),
            "newest_observed_at": newest.isoformat(),
            "age_days": str((cut - newest).days) if cut is not None else "",
        })
    # WEAKEST FIRST, so the stale class is the first thing a reader meets.
    return sorted(out, key=lambda row: -int(row["age_days"] or 0))


def member_factors(view: GraphView) -> list[tuple[str, DebtFactors]]:
    """One `DebtFactors` per member — the sequence `Q1`'s combinator composes.

    A member's freshness is the share of the book's declared signal classes it
    actually carries; its completeness the share of the required per-member
    limbs it has. Both are strengths in [0,1], as `DebtFactors` requires.
    """
    members = [r for r in view.entities if r.claim.entity_class == "member"]
    if not members:
        return []
    classes = sorted({
        r.claim.entity_class for r in view.entities
        if r.claim.entity_class.startswith(SIGNAL_PREFIX)
    })
    by_member_class: dict[str, set[str]] = {}
    for record in view.entities:
        if record.claim.entity_class.startswith(SIGNAL_PREFIX):
            lei = str(record.claim.attributes.get("lei", ""))
            by_member_class.setdefault(lei, set()).add(record.claim.entity_class)
    with_facility = {
        str(r.claim.attributes.get("lei", "")) for r in view.entities
        if r.claim.entity_class == "facility"
    }
    out: list[tuple[str, DebtFactors]] = []
    for record in members:
        lei = str(record.claim.attributes.get("lei", ""))
        covered = len(by_member_class.get(lei, set()))
        freshness = (Decimal(covered) / Decimal(len(classes))) if classes else Decimal(1)
        completeness = Decimal("1.0") if lei in with_facility else Decimal("0.5")
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
        # positive control rather than by the book (`PEW-F-01`).
        "max_member_debt": str(max(context_debt(f) for _, f in members)),
        "weakest_by_factor": weakest,
    }


def _role_member(
    member: str, by_class: Mapping[str, list[Mapping[str, str]]],
    population: Sequence[Mapping[str, str]], facilities: Sequence[Mapping[str, str]],
) -> Any:
    if member == "covenant_history":
        return _covenant_history(by_class)
    if member == "concentration":
        return _concentration(population, facilities)
    raise ValueError(f"member {member!r} is declared but Pi emits nothing for it")


def _covenant_history(by_class: Mapping[str, list[Mapping[str, str]]]) -> Mapping[str, Any]:
    """Active AND historical — zero current state is not absent history.

    Ruled 2026-09-21: the member is never dropped for being currently quiet.
    """
    rows = _items(by_class.get("covenant", ()), key="facility_id",
                  fields=("facility_id", "lei", "covenant_type", "breach_date",
                          "observed_value", "threshold_at_breach", "cured_date",
                          "compliant_today", "classification"))
    active = [row for row in rows if row["compliant_today"] != "true"]
    return {
        "active_breaches": str(len(active)),
        "historical_breaches": str(len(rows)),
        "cured_breaches": str(len([r for r in rows if r["cured_date"]])),
        "breaches": rows,
        "note": (
            "zero active breaches is not an absence of covenant history; every recorded"
            " breach is served with its cure state"
        ),
    }


def _concentration(
    population: Sequence[Mapping[str, str]], facilities: Sequence[Mapping[str, str]]
) -> Mapping[str, Any]:
    """Book concentration against CP-23's OWN declared threshold.

    **NOT CP-21's regulatory large exposure.** Nothing here reads
    `limit_definition`, `bank_capital` or a connection basis; the basis is
    committed exposure within this book and the thresholds are
    `artifacts/severity-tiers.yaml` (`PEW-G18`).
    """
    declared = _TIERS["concentration"]
    single = Decimal(str(declared["single_name_threshold_pct"]))
    sector_threshold = Decimal(str(declared["sector_threshold_pct"]))
    sic_by_lei = {str(m.get("lei", "")): str(m.get("sic_description", "") or "unclassified")
                  for m in population}
    by_name: dict[str, Decimal] = {}
    for facility in facilities:
        lei = str(facility.get("lei", ""))
        by_name[lei] = by_name.get(lei, Decimal(0)) + (_decimal(facility.get("commitment_amount")) or Decimal(0))
    total = sum(by_name.values(), Decimal(0))
    by_sector: dict[str, Decimal] = {}
    for lei, amount in by_name.items():
        sector = sic_by_lei.get(lei, "unclassified")
        by_sector[sector] = by_sector.get(sector, Decimal(0)) + amount

    names = sorted(
        ({"lei": lei, "committed": str(amount), "share_pct": str(_pct(amount, total)),
          "over_threshold": str(_pct(amount, total) >= single).lower(),
          "classification": "internal"} for lei, amount in by_name.items()),
        key=lambda row: -Decimal(row["share_pct"] or 0),
    )
    sectors = sorted(
        ({"sector": sector, "committed": str(amount), "share_pct": str(_pct(amount, total)),
          "over_threshold": str(_pct(amount, total) >= sector_threshold).lower()}
         for sector, amount in by_sector.items()),
        key=lambda row: -Decimal(row["share_pct"] or 0),
    )
    return {
        "basis": str(declared["basis"]),
        "threshold_authority": "cp-23.severity-tiers",
        "single_name_threshold_pct": str(single),
        "sector_threshold_pct": str(sector_threshold),
        "total_committed": str(total),
        "by_name": names,
        "by_sector": sectors,
        "names_over_threshold": str(len([r for r in names if r["over_threshold"] == "true"])),
    }


def _findings(
    by_class: Mapping[str, list[Mapping[str, str]]],
    population: Sequence[Mapping[str, str]], facilities: Sequence[Mapping[str, str]],
) -> list[Mapping[str, str]]:
    findings: list[Mapping[str, str]] = []
    covered = {str(f.get("lei", "")) for f in facilities}
    uncovered = [str(m.get("lei", "")) for m in population if str(m.get("lei", "")) not in covered]
    if uncovered:
        findings.append({
            "finding": "members-without-a-facility",
            "detail": (
                f"{len(uncovered)} of {len(population)} members carry no facility; they remain"
                f" members and their signals count, so the book's utilization is not mistaken"
                f" for the whole book"
            ),
        })
    if not by_class.get("covenant"):
        findings.append({
            "finding": "no-covenant-history-in-population",
            "detail": "no member of this population has a recorded covenant breach at this instant",
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
        "severity_floor": attributes.get("severity_floor", ""),
        "tier_policy_version": attributes.get("tier_policy_version", ""),
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

    A MEMBER THE ROLE EXCLUDED STILL COUNTS (`PEW-G13`, `CP-SPEC-023` §E.2) —
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
