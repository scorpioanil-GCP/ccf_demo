"""Pi for `risk.large-exposure` — one plan, three renderings, one calculation.

[ADAPT] the payload shape and the evaluation rule here. Pi reads the governed
view and nothing beside it.

FOUR THINGS ARE LOAD-BEARING (`CP-SPEC-021`, ruled 2026-09-21):

1. **The arithmetic consumes the NORMALIZED capital base**, and the raw source
   figure travels beside it with its unit and its authority. Getting this wrong
   is silent: on the unnormalized base a 25 % limit is ~$74 million and 42 of
   the estate's 60 facilities breach it single-handedly (`LEX-G06`, `LEX-G07`).
2. **A limit is a percentage of capital OR an absolute amount**, and the
   product names which. Regulation O's $500,000 is the second shape; a product
   that assumed the first could not express it (`LEX-G09`).
3. **Both internal limit authorities are served and the conflict is visible.**
   The relational register and the graph envelope genuinely disagree, and
   neither is presented as wrong; where a rule selects one, that rule is named
   (`LEX-G11`).
4. **The freshness asymmetry is disclosed, never fused.** Exposure is intraday
   and capital is quarterly. Nothing here ages one into the other or collapses
   them into a single timestamp (`LEX-G14`).

AND THE PROPOSAL IS AN ASSUMPTION. It is computed with and without, it is
labelled, and it cannot move Context Debt (`LEX-G16`, `LEX-G19`).
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

_DECLARED: Mapping[str, Any] = yaml.safe_load(PERSPECTIVES.read_text(encoding="utf-8"))["declaration"]
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


def members_for(perspective: str) -> set[str]:
    return set(COMMON_MEMBERS) | set(PERSPECTIVE_MEMBERS[perspective])


class LargeExposureProjection:
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
        groups = [r for r in view.entities if r.claim.entity_class == "group"]
        if len(groups) > 1:
            raise ValueError("the view holds more than one group; it was not written by one question")
        anchor = groups[0] if groups else None
        by_class: dict[str, list[Mapping[str, str]]] = {}
        for record in view.entities:
            by_class.setdefault(record.claim.entity_class, []).append(dict(record.claim.attributes))

        attributes = dict(anchor.claim.attributes) if anchor is not None else {}
        capital = _capital_base(attributes)
        regime = _regime_in_force(attributes, by_class)
        limits = _limits(by_class, capital)
        exposure = _aggregate_exposure(by_class, attributes)
        evaluation = _evaluate(exposure, limits, regime, attributes)

        payload: dict[str, Any] = {
            "perspective": role,
            "as_of": self._as_of,
            "intent": attributes.get("intent", ""),
            "group": None if anchor is None else _group_member(attributes),
            "members": _members(by_class),
            "member_count": attributes.get("member_count", "0" if anchor is None else ""),
            "capital_base": capital,
            "regime_in_force": regime,
            "limits": limits,
            "limit_authority_conflict": _authority_conflict(limits),
            "aggregate_exposure": exposure,
            "evaluation": evaluation,
            "freshness_asymmetry": _asymmetry(attributes, capital),
            "population_debt": _population_debt(view),
            "findings": _findings(by_class, attributes),
            "entities_in_view": len(view.entities),
            "edge_types_served": sorted({e.claim.relationship_type for e in view.relationships}),
        }
        for member in PERSPECTIVE_MEMBERS[role]:
            payload[member] = _role_member(member, by_class, attributes, exposure, limits,
                                           regime, evaluation, plan_id=self._plan_id)
        return ProjectionOutput(plan_id=self._plan_id, payload=payload)


# =========================================================================
# THE CAPITAL BASE — both figures, both units, its own date
# =========================================================================


def _capital_base(attributes: Mapping[str, str]) -> Mapping[str, Any]:
    """Raw and normalized, each with its unit, and the denominator's own date."""
    return {
        "raw_value": attributes.get("capital_raw_value", ""),
        "source_unit": attributes.get("capital_source_unit", ""),
        "normalized_value": attributes.get("capital_normalized_value", ""),
        "normalized_unit": attributes.get("capital_normalized_unit", ""),
        "unit_authority": attributes.get("capital_unit_authority", ""),
        "report_date": attributes.get("capital_report_date", ""),
        "age_days": attributes.get("capital_age_days", ""),
        "consumed_by_arithmetic": "normalized_value",
        "note": (
            "the source reports in thousands of dollars, which is the FFIEC Call Report"
            " convention and legitimate source semantics; the regulatory arithmetic consumes"
            " the normalized figure and the raw one is preserved"
        ),
    }


def _regime_in_force(
    attributes: Mapping[str, str], by_class: Mapping[str, list[Mapping[str, str]]]
) -> Mapping[str, Any]:
    """The selected regime, its rule form, its limit and its authority."""
    import json  # noqa: PLC0415

    selected = attributes.get("regime", "")
    row = next((r for r in by_class.get("regime", ()) if str(r.get("regime_id", "")) == selected), {})
    rule_form = str(attributes.get("rule_form", "") or row.get("rule_form", ""))
    capital = _decimal(attributes.get("capital_normalized_value")) or Decimal(0)
    if rule_form == "percentage-of-capital":
        pct = _decimal(attributes.get("limit_pct_of_capital")) or Decimal(0)
        limit_value = (capital * pct / Decimal(100)).quantize(Decimal("0.01"))
        basis = f"{pct}% of eligible capital"
    else:
        limit_value = _decimal(attributes.get("limit_absolute_usd")) or Decimal(0)
        basis = "an absolute amount, independent of capital"
    provisions = []
    for item in json.loads(row.get("cited_provisions", "[]") or "[]"):
        provisions.append({
            "passage_id": str(item.get("passage_id", "")),
            "document_id": str(item.get("document_id", "")),
            "resolved": str(bool(item.get("text"))).lower(),
            "quoted_text": " ".join(str(item.get("text", "")).split())[:400],
            # NO HASH. These passages carry none and one is not invented.
            "hash_available": "false",
        })
    return {
        "regime_id": selected,
        "label": attributes.get("regime_label", ""),
        "effective_from": attributes.get("regime_effective_from", ""),
        "effective_basis": basis,
        "rule_form": rule_form,
        "limit_value": str(limit_value),
        "limit_unit": "usd",
        "authority": row.get("label", "") or selected,
        "provisions": provisions,
        "provisions_cited": row.get("provisions_cited", "0"),
        "provisions_resolved": row.get("provisions_resolved", "0"),
    }


def _limits(
    by_class: Mapping[str, list[Mapping[str, str]]], capital: Mapping[str, Any]
) -> list[Mapping[str, Any]]:
    """Every limit authority, evaluated on the NORMALIZED base."""
    base = _decimal(capital.get("normalized_value")) or Decimal(0)
    rows: list[Mapping[str, Any]] = []
    for row in by_class.get("limit", ()):
        pct = _decimal(row.get("limit_pct_of_capital"))
        rows.append({
            "limit_id": str(row.get("limit_id", "")),
            "authority": str(row.get("authority", "")),
            "rule_form": "percentage-of-capital" if pct is not None else "absolute-amount",
            "limit_pct_of_capital": str(pct) if pct is not None else "",
            "limit_value": str((base * pct / Decimal(100)).quantize(Decimal("0.01"))) if pct is not None else "",
            "counts_guarantees": str(row.get("counts_guarantees", "")),
            "counts_undrawn": str(row.get("counts_undrawn", "")),
            "connection_basis": str(row.get("connection_basis", "")),
            "classification": str(row.get("classification", "")),
        })
    return sorted(rows, key=lambda r: (r["limit_id"], r["authority"]))


def _authority_conflict(limits: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    """Where two authorities price the same limit differently, SAY SO.

    Ruled 2026-09-21: preserve the disagreement, do not silently choose, and
    where a rule selects one, name the rule rather than calling the other
    wrong.
    """
    by_id: dict[str, list[Mapping[str, Any]]] = {}
    for row in limits:
        by_id.setdefault(row["limit_id"], []).append(row)
    for limit_id, rows in sorted(by_id.items()):
        values = {r["limit_pct_of_capital"] for r in rows if r["limit_pct_of_capital"]}
        if len(values) > 1:
            return {
                "limit_id": limit_id,
                "authorities": [
                    {"authority": r["authority"], "limit_pct_of_capital": r["limit_pct_of_capital"],
                     "limit_value": r["limit_value"]}
                    for r in sorted(rows, key=lambda r: r["authority"])
                ],
                # THE RULE, NAMED. The other source is not wrong; it is a
                # different authority, and this is which one binds here.
                "selected_by_rule": "most-conservative-internal-authority-binds",
                "selected_authority": min(
                    (r for r in rows if r["limit_pct_of_capital"]),
                    key=lambda r: Decimal(r["limit_pct_of_capital"]),
                )["authority"],
                "note": (
                    "both authorities are served; the conservative one binds for this"
                    " determination by the named rule, and neither is presented as incorrect"
                ),
            }
    return None


# =========================================================================
# EXPOSURE AND EVALUATION
# =========================================================================


def _members(by_class: Mapping[str, list[Mapping[str, str]]]) -> list[Mapping[str, str]]:
    return _items(by_class.get("member", ()), key="legal_name",
                  fields=("lei", "legal_name", "is_anchor", "in_group", "admitted_by",
                          "lei_registered", "dependency_basis", "dependency_provenance",
                          "classification"))


def _aggregate_exposure(
    by_class: Mapping[str, list[Mapping[str, str]]], attributes: Mapping[str, str]
) -> Mapping[str, Any]:
    """Sum across the DERIVED group, per member and in total."""
    by_member: dict[str, dict[str, Decimal]] = {}
    for row in by_class.get("exposure", ()):
        lei = str(row.get("lei", ""))
        entry = by_member.setdefault(lei, {"commitment": Decimal(0), "drawn": Decimal(0),
                                           "undrawn": Decimal(0), "facilities": Decimal(0)})
        entry["commitment"] += _decimal(row.get("commitment_amount")) or Decimal(0)
        entry["drawn"] += _decimal(row.get("drawn_amount")) or Decimal(0)
        entry["undrawn"] += _decimal(row.get("undrawn_amount")) or Decimal(0)
        entry["facilities"] += 1
    rows = [
        {"lei": lei, "facilities": str(int(v["facilities"])), "commitment": str(v["commitment"]),
         "drawn": str(v["drawn"]), "undrawn": str(v["undrawn"]), "classification": "internal"}
        for lei, v in sorted(by_member.items())
    ]
    total = sum((v["commitment"] for v in by_member.values()), Decimal(0))
    return {
        "basis": "observed",
        "connection_basis": attributes.get("connection_basis", ""),
        # THE GUARANTEE LEGS, BOTH WAYS ROUND. In this estate the received leg
        # is empty for every measured group, and the product says so rather
        # than folding a zero into a netted total (`LEX-G13`, `LEX-G15`).
        "guarantees_given": attributes.get("guarantees_given", "0"),
        "guarantee_cover_given": attributes.get("guarantee_cover_given", "0"),
        "guarantees_received_resolvable": attributes.get("guarantees_received_resolvable", "0"),
        "guarantee_cover_received": attributes.get("guarantee_cover_received", "0"),
        "members_with_exposure": str(len(by_member)),
        "total_commitment": str(total),
        "total_drawn": str(sum((v["drawn"] for v in by_member.values()), Decimal(0))),
        "total_undrawn": str(sum((v["undrawn"] for v in by_member.values()), Decimal(0))),
        "by_member": rows,
    }


def _evaluate(
    exposure: Mapping[str, Any], limits: Sequence[Mapping[str, Any]],
    regime: Mapping[str, Any], attributes: Mapping[str, str],
) -> Mapping[str, Any]:
    """Headroom, utilisation, which limit binds first, and the proposal's effect.

    THE COUNTING RULES ARE NOT DECORATION (`LEX-G13`). Each limit is evaluated
    against the measure ITS OWN rule admits: a limit that does not count
    undrawn commitment is evaluated on drawn balances, and one that counts
    guarantees adds the cover this group has written. Two limits over one group
    therefore legitimately see two different exposure numbers.

    AND MITIGATION IS A CALLER CHOICE THAT MOVES THE ANSWER (`LEX-G15`).
    Measured on this estate: the engineered $59.4bn proposal is $60.5 MILLION
    over the $73.940bn limit gross, and fits with the undrawn relief
    recognized. Which mitigation component actually applied is named, never
    presented as one netted figure.
    """
    commitment = _decimal(exposure.get("total_commitment")) or Decimal(0)
    drawn = _decimal(exposure.get("total_drawn")) or Decimal(0)
    undrawn = _decimal(exposure.get("total_undrawn")) or Decimal(0)
    guarantee_cover = _decimal(exposure.get("guarantee_cover_given")) or Decimal(0)
    mitigating = str(attributes.get("apply_mitigation", "")) == "true"
    proposal = _decimal(attributes.get("proposal_commitment_usd"))

    def measure(row: Mapping[str, Any]) -> tuple[Decimal, list[str]]:
        """The exposure THIS limit counts, and why."""
        counts_undrawn = str(row.get("counts_undrawn", "")) != "false"
        counts_guarantees = str(row.get("counts_guarantees", "")) == "true"
        applied: list[str] = []
        amount = commitment if counts_undrawn else drawn
        if not counts_undrawn:
            applied.append("undrawn-excluded-by-counting-rule")
        if counts_guarantees and guarantee_cover:
            amount += guarantee_cover
            applied.append("guarantees-given-counted")
        # THE RELIEF APPLIES ONCE. A limit that already excludes undrawn
        # commitment cannot also be relieved of it.
        if mitigating and counts_undrawn and undrawn:
            amount -= undrawn
            applied.append("undrawn-relief-recognized")
        return amount, applied

    candidates: list[dict[str, Any]] = []
    for row in limits:
        value = _decimal(row.get("limit_value"))
        if value is None:
            continue
        candidates.append({"limit_id": row["limit_id"], "authority": row["authority"],
                           "rule_form": row["rule_form"], "limit_value": value, "row": row})
    regime_value = _decimal(regime.get("limit_value"))
    if regime_value is not None:
        candidates.append({
            "limit_id": regime["regime_id"], "authority": regime["authority"],
            "rule_form": regime["rule_form"], "limit_value": regime_value,
            # The regime's own counting rule is the regulatory register's.
            "row": next((r for r in limits if r["limit_id"] == "regulatory-large-exposure"), {}),
        })

    def against(increment: Decimal) -> list[Mapping[str, Any]]:
        rows: list[Mapping[str, Any]] = []
        for c in candidates:
            amount, applied = measure(c["row"])
            amount += increment
            limit_value = c["limit_value"]
            rows.append({
                "limit_id": c["limit_id"], "authority": c["authority"],
                "rule_form": c["rule_form"], "limit_value": str(limit_value),
                "exposure_counted": str(amount),
                "counting_rules_applied": applied,
                "headroom": str(limit_value - amount),
                "utilisation_pct": str((amount / limit_value * Decimal(100)).quantize(Decimal("0.01")))
                if limit_value else "",
                "breached": str(amount > limit_value).lower(),
            })
        return sorted(rows, key=lambda r: (r["limit_id"], r["authority"]))

    without = against(Decimal(0))
    # WHICH LIMIT BINDS FIRST is the one with the least headroom, NOT the
    # smallest limit — a limit's counting rule can make a larger limit the
    # tighter one (`LEX-G12`).
    binds = min(without, key=lambda r: Decimal(r["headroom"]), default=None)
    result: dict[str, Any] = {
        "basis": "observed",
        "mitigation_applied": str(mitigating).lower(),
        "mitigation_components_available": {
            "undrawn_relief": str(undrawn),
            "guarantee_cover_received": str(
                _decimal(exposure.get("guarantee_cover_received")) or Decimal(0)),
        },
        "without_proposal": without,
        "binding_limit_id": binds["limit_id"] if binds else "",
        "binding_limit_authority": binds["authority"] if binds else "",
        "binding_limit_value": binds["limit_value"] if binds else "",
        "binding_limit_headroom": binds["headroom"] if binds else "",
        "breached_without_proposal": str(any(r["breached"] == "true" for r in without)).lower(),
    }
    if proposal is not None:
        with_proposal = against(proposal)
        regulatory = next(
            (r for r in with_proposal if r["limit_id"] == regime.get("regime_id")), None)
        result |= {
            "proposal_commitment": str(proposal),
            "proposal_basis": "assumption",
            "with_proposal": with_proposal,
            "breached_with_proposal": str(
                any(r["breached"] == "true" for r in with_proposal)).lower(),
            # THE REGIME'S OWN VERDICT, separately from the internal envelope's
            # — this is the one the estate's engineered rows are labelled
            # against (`LEX-G06`).
            "regulatory_outcome": (
                "" if regulatory is None
                else ("breaches" if regulatory["breached"] == "true" else "fits")
            ),
            "regulatory_exposure_counted": "" if regulatory is None else regulatory["exposure_counted"],
            "regulatory_limit_value": "" if regulatory is None else regulatory["limit_value"],
        }
    return result


def _asymmetry(attributes: Mapping[str, str], capital: Mapping[str, Any]) -> Mapping[str, Any]:
    """The two clocks, stated side by side and NEVER fused."""
    return {
        "exposure_instant": attributes.get("exposure_instant", ""),
        "exposure_cadence": "intraday",
        "capital_report_date": capital.get("report_date", ""),
        "capital_cadence": "quarterly",
        "capital_age_days": capital.get("age_days", ""),
        "resolved": "false",
        "note": (
            "exposure and the capital base do not share a clock. Neither is aged into the"
            " other and no combined freshness timestamp is minted; the gap is disclosed"
            " because it is a property of regulatory reporting, not a modelling flaw"
        ),
    }


def _role_member(
    member: str, by_class: Mapping[str, list[Mapping[str, str]]], attributes: Mapping[str, str],
    exposure: Mapping[str, Any], limits: Sequence[Mapping[str, Any]],
    regime: Mapping[str, Any], evaluation: Mapping[str, Any], *, plan_id: str,
) -> Any:
    if member == "proposal_effect":
        return {
            "basis": "assumption",
            "stated": str("with_proposal" in evaluation).lower(),
            "with_proposal": evaluation.get("with_proposal", []),
            "without_proposal": evaluation.get("without_proposal", []),
            "note": "a proposal is a hypothetical; it does not affect Context Debt",
        }
    if member == "concentration_view":
        total = _decimal(exposure.get("total_commitment")) or Decimal(1)
        return {
            "total_commitment": str(total),
            "by_member": [
                {**row, "share_pct": str((_decimal(row["commitment"]) or Decimal(0))
                                         / total * Decimal(100)).__str__()[:8]}
                for row in exposure.get("by_member", [])
            ],
        }
    if member == "methodology":
        return {
            "counting_rules": [
                {"limit_id": r["limit_id"], "authority": r["authority"],
                 "counts_guarantees": r["counts_guarantees"], "counts_undrawn": r["counts_undrawn"],
                 "connection_basis": r["connection_basis"]}
                for r in limits
            ],
            "capital_normalization": {
                "source_unit": attributes.get("capital_source_unit", ""),
                "normalized_unit": attributes.get("capital_normalized_unit", ""),
                "authority": attributes.get("capital_unit_authority", ""),
            },
            "group_derivation": {
                "connection_basis": attributes.get("connection_basis", ""),
                "derived": "true",
                "note": "the group is computed from edges at the ledger point, not read from a registry",
            },
        }
    if member == "replay_attribution":
        ledger_t = str(attributes.get("ledger_t", "") or "unreported")
        return {
            "plan_id": plan_id,
            "regime_id": regime.get("regime_id", ""),
            "regime_effective_from": regime.get("effective_from", ""),
            "connection_basis": attributes.get("connection_basis", ""),
            "capital_report_date": attributes.get("capital_report_date", ""),
            "determination_instant": attributes.get("exposure_instant", ""),
            # THE LEDGER POINT, AND WHETHER IT COULD BE RESOLVED AT ALL.
            # Measured 2026-09-21: this Fluree deployment emits no `x-fdb-t`
            # header on its SPARQL endpoint and exposes no route returning the
            # ledger `t`, so the group's derivation point is NOT recoverable
            # from this estate. It is reported as `unreported` with the fact
            # stated, never as a minted number — an invented `t` would make
            # replay look reconstructible when it is not (`LEX-F-04`).
            "ledger_t": ledger_t,
            "ledger_point_resolvable": str(ledger_t != "unreported").lower(),
        }
    raise ValueError(f"member {member!r} is declared but Pi emits nothing for it")


def _findings(
    by_class: Mapping[str, list[Mapping[str, str]]], attributes: Mapping[str, str]
) -> list[Mapping[str, str]]:
    import json  # noqa: PLC0415

    # WHAT ACQUISITION MEASURED, CARRIED THROUGH. The disagreement between the
    # two internal limit authorities and the unmeasurable guarantee cover are
    # both found at the source seam; serving them here is what makes them
    # visible to a reader rather than to a log.
    findings: list[Mapping[str, str]] = [
        {"finding": str(row.get("finding", "")), "detail": str(row.get("detail", ""))}
        for row in json.loads(attributes.get("acquisition_findings", "[]") or "[]")
    ]
    unregistered = [m for m in by_class.get("member", ()) if m.get("lei_registered") == "false"]
    if unregistered:
        findings.append({
            "finding": "group-extends-beyond-the-lei-registered-set",
            "detail": (
                f"{len(unregistered)} group member(s) carry no LEI in this estate, so no exposure"
                f" is measurable for them. They remain members: dropping them would shrink the"
                f" group and understate the denominator"
            ),
        })
    dependent = [m for m in by_class.get("member", ()) if m.get("admitted_by") == "economic-dependency"]
    if dependent:
        findings.append({
            "finding": "members-admitted-by-economic-dependency",
            "detail": (
                f"{len(dependent)} member(s) enter this group by economic dependency rather than"
                f" control. Those edges are a judgment, carry a stated basis and are marked"
                f" synthetic — a control-only basis would omit them"
            ),
        })
    return sorted(findings, key=lambda row: row["finding"])


def _group_member(attributes: Mapping[str, str]) -> Mapping[str, Any]:
    return {
        "anchor_lei": attributes.get("anchor_lei", ""),
        "connection_basis": attributes.get("connection_basis", ""),
        "member_count": attributes.get("member_count", ""),
        "members_lei_registered": attributes.get("members_lei_registered", ""),
        # DERIVED, and the gate asserts it. This group is the transitive
        # closure of the admitted edges at `ledger_t`, never a stored roster.
        "derived": "true",
        "proposal_stated": str(bool(attributes.get("proposal_commitment_usd"))).lower(),
        "ledger_t": attributes.get("ledger_t", ""),
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


def _clamp(value: Decimal) -> Decimal:
    return max(Decimal("0"), min(Decimal("1"), value)).quantize(Decimal("0.0001"))


def member_factors(view: GraphView) -> list[tuple[str, DebtFactors]]:
    """One `DebtFactors` per group member — OBSERVED evidence only.

    No proposal value reaches here, which is why two proposals over one instant
    and group give identical debt (`LEX-G19`).
    """
    members = [r for r in view.entities if r.claim.entity_class == "member"]
    if not members:
        return []
    with_exposure = {
        str(r.claim.attributes.get("lei", "")) for r in view.entities
        if r.claim.entity_class == "exposure"
    }
    out: list[tuple[str, DebtFactors]] = []
    for record in members:
        attributes = record.claim.attributes
        key = str(attributes.get("lei", "")) or str(attributes.get("legal_name", ""))
        registered = str(attributes.get("lei_registered", "")) == "true"
        measurable = key in with_exposure
        out.append((key, DebtFactors(
            freshness=Decimal("1.0"),
            # A member with no LEI, or no measurable exposure, is genuinely
            # less complete evidence for a limit calculation.
            completeness=_clamp(Decimal("1.0") if measurable else
                                (Decimal("0.7") if registered else Decimal("0.4"))),
            semantic_consistency=Decimal("1.0"),
        )))
    return out


def _population_debt(view: GraphView) -> Mapping[str, Any]:
    from ccf.halflife.debt import compose_debt_factors, context_debt  # noqa: PLC0415

    members = member_factors(view)
    if not members:
        return {"rule": "per-factor-minimum", "members": "0", "freshness": "1",
                "completeness": "1", "semantic_consistency": "1", "debt": "0",
                "weakest_by_factor": {}}
    own = DebtFactors(freshness=Decimal("1.0"), completeness=Decimal("1.0"),
                      semantic_consistency=Decimal("1.0"))
    composed = compose_debt_factors(own, [f for _, f in members])
    return {
        "rule": "per-factor-minimum",
        "rule_authority": "D-IMPL-104",
        "members": str(len(members)),
        "freshness": str(composed.freshness),
        "completeness": str(composed.completeness),
        "semantic_consistency": str(composed.semantic_consistency),
        "debt": str(context_debt(composed)),
        "weakest_by_factor": {
            factor: min(members, key=lambda pair: getattr(pair[1], factor))[0]
            for factor in ("freshness", "completeness", "semantic_consistency")
        },
    }


def view_completeness(view: GraphView) -> Decimal:
    """`C` = required classes present / required."""
    import acquisition  # noqa: PLC0415

    if not [r for r in view.entities if r.claim.entity_class == "group"]:
        return Decimal("0.0000")
    required = acquisition.required_classes()
    present = {r.claim.entity_class for r in view.entities}
    return (Decimal(sum(1 for c in required if c in present))
            / Decimal(len(required))).quantize(Decimal("0.0001"))
