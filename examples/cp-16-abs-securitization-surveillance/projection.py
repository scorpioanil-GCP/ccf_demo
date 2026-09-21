"""Pi for `cib.abs-surveillance` — one plan, three perspectives, four shapes.

[ADAPT] the payload shape and the evaluation rule here. Pi reads the governed
view and nothing beside it: the perspective it is handed, the claims in the
view, and the effective `as_of` the factory closed over. It never sees the
granularity entitlement table, the ceiling artifact, or a loan record the
envelope excluded — those never enter the fabric (`CP-SPEC-016` §D.3).

THE SHAPE IS A FUNCTION OF THE PERSPECTIVE AND THE EFFECTIVE GRANULARITY, and
of nothing else. A role whose ceiling is `deal` does not carry an empty
`cohort_performance`, because an empty member would read as *this deal has no
cohorts* rather than *you may not ask*.

ROUTE B (`CP-SPEC-016` §F.4). An in-force threshold with no filed prospectus
passage is SERVED, marked `anchored: false`, classified by what actually
sourced it, and named in `unanchored_thresholds`. Nothing here writes an empty
anchor field: the absence is stated, never encoded as a blank.

A FINDING IS NOT AN ABSENCE. A threshold defined as a formula has no numeric
distance, and that is reported as an uncomputable proximity naming its reason
— never as a distance of zero.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml
from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput
from ccf.projection.plan import Perspective, ProjectionOutput

HERE = Path(__file__).parent
PERSPECTIVES = HERE / "artifacts" / "perspectives.yaml"

_DECLARED: Mapping[str, Any] = yaml.safe_load(PERSPECTIVES.read_text(encoding="utf-8"))["declaration"]
COMMON_MEMBERS: tuple[str, ...] = tuple(_DECLARED["common_members"])
MEMBERS_BY_GRANULARITY: Mapping[str, tuple[str, ...]] = {
    name: tuple(members) for name, members in _DECLARED["members_by_granularity"].items()
}
PERSPECTIVE_CEILING: Mapping[str, str] = {
    name: str(spec["ceiling"]) for name, spec in _DECLARED["perspectives"].items()
}
PRINCIPAL_ID: Mapping[str, str] = {
    name: str(spec["principal_id"]) for name, spec in _DECLARED["perspectives"].items()
}
CLASSIFICATION_VOCABULARY: tuple[str, ...] = tuple(_DECLARED["classification_vocabulary"])
LIST_MEMBERS: tuple[str, ...] = tuple(_DECLARED["classified_list_members"])
GRANULARITY_ORDER: tuple[str, ...] = tuple(_DECLARED["granularity_order"])


def members_for(perspective: str, granularity: str) -> set[str]:
    """The declared member set for this perspective at this granularity."""
    del perspective  # the ceiling already decided which granularities are reachable
    return set(COMMON_MEMBERS) | set(MEMBERS_BY_GRANULARITY.get(granularity, ()))


class ABSSurveillanceProjection:
    """One `plan_id`; `invoke` branches on `perspective.role` and granularity."""

    def __init__(self, *, plan_id: str, required: tuple[str, ...], as_of: str) -> None:
        self._plan_id = plan_id
        self._required = required
        self._as_of = as_of

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        """The SDK's own set, passed straight through."""
        return self._required

    def invoke(
        self, *, view: GraphView, operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective, temporal_boundary: datetime,
    ) -> ProjectionOutput:
        del operator_outputs, temporal_boundary
        role = perspective.role
        if role not in PERSPECTIVE_CEILING:
            raise ValueError(f"perspective {role!r} is not declared in `artifacts/perspectives.yaml`")
        anchors = [record for record in view.entities if record.claim.entity_class == "deal"]
        if len(anchors) > 1:
            raise ValueError("the view holds more than one deal; it was not written by one question")
        anchor = anchors[0] if anchors else None
        by_class: dict[str, list[Mapping[str, str]]] = {}
        for record in view.entities:
            by_class.setdefault(record.claim.entity_class, []).append(dict(record.claim.attributes))

        attributes = dict(anchor.claim.attributes) if anchor is not None else {}
        effective = str(attributes.get("effective_granularity", ""))
        triggers = _triggers(by_class)
        cohorts = _cohorts(by_class)
        pool = _pool_performance(attributes, cohorts)

        payload: dict[str, Any] = {
            "perspective": role,
            "as_of": self._as_of,
            "intent": attributes.get("intent", ""),
            "deal": None if anchor is None else _deal_member(attributes),
            "requested_granularity": attributes.get("requested_granularity", ""),
            "effective_granularity": effective,
            "granularity_ceiling": attributes.get("granularity_ceiling", ""),
            "tranches": _tranches(by_class),
            "triggers": triggers,
            "trigger_proximity": _proximity(triggers, pool),
            # PRESENT AT EVERY GRANULARITY. Route B's second invariant is a
            # POSITIVE statement, so the member exists whether or not the
            # estate has anything to put in it.
            "unanchored_thresholds": [t for t in triggers if t.get("anchored") == "false"],
            "pool_performance": pool,
            "benchmark_comparison": _benchmark(by_class, pool),
            "repurchase_activity": _repurchase(by_class),
            "assembly_cost": _assembly_cost(attributes),
            "findings": _findings(triggers, by_class),
            "entities_in_view": len(view.entities),
            "edge_types_served": sorted({edge.claim.relationship_type for edge in view.relationships}),
        }
        for member in MEMBERS_BY_GRANULARITY.get(effective, ()):
            payload[member] = _granular_member(member, by_class)
        return ProjectionOutput(plan_id=self._plan_id, payload=payload)


# =========================================================================
# THE EVALUATION
# =========================================================================


def _triggers(by_class: Mapping[str, list[Mapping[str, str]]]) -> list[Mapping[str, Any]]:
    """Every trigger definition IN FORCE, with its anchoring stated explicitly.

    An unanchored threshold carries `anchored: false` and NO anchor fields at
    all. Writing `anchor_passage_id: ""` would imply a passage that does not
    exist, which Route B forbids (`CP-SPEC-016` §F.4.0).

    The filed span arrives as its OWN class (`ABS-F-04`) and is joined here by
    `trigger_id`. A threshold whose `anchored` flag says true and for which no
    anchor claim reached the view is a contradiction the gate refuses rather
    than papers over.
    """
    anchors = {
        str(row.get("trigger_id", "")): row for row in by_class.get("anchor", ())
    }
    out: list[Mapping[str, Any]] = []
    for row in by_class.get("trigger", ()):
        anchored = str(row.get("anchored", "")).lower() == "true"
        item: dict[str, Any] = {
            "trigger_id": str(row.get("trigger_id", "")),
            "label": str(row.get("label", "")),
            "threshold_value": str(row.get("threshold_value", "")),
            "threshold_unit": str(row.get("threshold_unit", "")),
            "threshold_components": _components(row),
            "valid_from": str(row.get("valid_from", "")),
            "asserted_at": str(row.get("asserted_at", "")),
            "anchored": "true" if anchored else "false",
            "source_classification": str(row.get("source_classification", "")),
            "supersedes": str(row.get("supersedes", "")),
            "classification": str(row.get("classification", "")),
        }
        anchor = anchors.get(item["trigger_id"])
        if anchored and anchor is not None:
            item |= {
                "anchor_passage_id": str(anchor.get("anchor_passage_id", "")),
                "anchor_document_id": str(anchor.get("anchor_document_id", "")),
                "anchor_sha256": str(anchor.get("anchor_sha256", "")),
                "anchor_text": str(anchor.get("anchor_text", "")),
            }
        elif anchored:
            # The flag claims filed text that did not reach the view. Say so
            # rather than silently downgrading the flag.
            item["anchored"] = "contradicted"
        out.append(item)
    return sorted(out, key=lambda row: row["trigger_id"])


def _components(row: Mapping[str, str]) -> list[str]:
    """A two-component threshold keeps BOTH components (`ABS-G17`)."""
    raw = str(row.get("threshold_components", ""))
    return [part for part in raw.split(",") if part]


def _proximity(
    triggers: Sequence[Mapping[str, Any]], pool: Mapping[str, Any]
) -> list[Mapping[str, Any]]:
    """Distance to each threshold, in the unit the threshold is defined in.

    A threshold with no numeric value is UNCOMPUTABLE and says so; it is never
    reported as a distance of zero, which would read as *already breached*.
    """
    observed = _decimal(pool.get("delinquency_percent"))
    out: list[Mapping[str, Any]] = []
    for trigger in triggers:
        threshold = _decimal(trigger.get("threshold_value"))
        unit = str(trigger.get("threshold_unit", ""))
        item: dict[str, Any] = {
            "trigger_id": trigger["trigger_id"],
            "threshold_value": trigger.get("threshold_value", ""),
            "threshold_unit": unit,
            "anchored": trigger.get("anchored"),
            "classification": trigger.get("classification"),
        }
        if threshold is None:
            item["distance"] = None
            item["uncomputable_reason"] = (
                f"the threshold is defined as a formula in unit `{unit}` and carries no numeric"
                f" value; a distance is not invented"
            )
        elif unit != "percent_of_pool" or observed is None:
            item["distance"] = None
            item["uncomputable_reason"] = (
                f"this product observes `percent_of_pool` and the threshold is stated in"
                f" `{unit}`; the units are not silently reconciled"
            )
        else:
            item["observed"] = str(observed)
            item["distance"] = str(threshold - observed)
            item["breached"] = str(observed >= threshold).lower()
        out.append(item)
    return out


def _pool_performance(
    attributes: Mapping[str, str], cohorts: Sequence[Mapping[str, Any]]
) -> Mapping[str, Any]:
    """The deal's own filed state, plus the cohort roll-up where it was served."""
    performance: dict[str, Any] = {
        "period": attributes.get("period", ""),
        "pool_balance": attributes.get("pool_balance", ""),
        "note_balance": attributes.get("note_balance", ""),
        "delinquency_percent": attributes.get("published_delinquency_percent", ""),
        "cumulative_net_loss_percent": attributes.get("cumulative_net_loss_percent", ""),
        "receivable_count": attributes.get("receivable_count", ""),
        "oc_amount": attributes.get("oc_amount", ""),
        "oc_target": attributes.get("oc_target", ""),
        # THE FILED TRIGGER, kept apart from the IN-FORCE one. The servicer
        # report publishes the ORIGINAL threshold in every period of this
        # estate, so at an instant after the amendment the filed figure and the
        # ledger's in-force definition disagree — and the product states both
        # rather than silently preferring one (`ABS-F-03`).
        "published_delinquency_trigger": attributes.get("published_delinquency_trigger", ""),
        "published_trigger_occurred": attributes.get("published_trigger_occurred", ""),
    }
    if cohorts:
        performance["cohort_count"] = str(len(cohorts))
        performance["cohort_loan_count"] = str(
            sum(int(str(row.get("loan_count", "0")) or 0) for row in cohorts)
        )
    return performance


def _cohorts(by_class: Mapping[str, list[Mapping[str, str]]]) -> list[Mapping[str, Any]]:
    return _items(by_class.get("cohort", ()), key="credit_band",
                  fields=("credit_band", "period", "loan_count", "pool_balance",
                          "delinquent_60_plus_balance", "delinquency_percent",
                          "chargedoff_amount", "recovered_amount",
                          "weighted_average_coupon_percent", "classification"))


def _tranches(by_class: Mapping[str, list[Mapping[str, str]]]) -> list[Mapping[str, Any]]:
    rows = _items(by_class.get("tranche", ()), key="tranche_id",
                  fields=("tranche_id", "class_name", "seniority_rank", "cusip",
                          "interest_rate", "interest_rate_basis", "classification"))
    # SENIORITY IS THE ORDER, and it is read off the served claims rather than
    # assumed from the class name (`ABS-G02`).
    return sorted(rows, key=lambda row: (int(row["seniority_rank"] or 0), row["tranche_id"]))


def _benchmark(
    by_class: Mapping[str, list[Mapping[str, str]]], pool: Mapping[str, Any]
) -> Mapping[str, Any]:
    rows = _items(by_class.get("benchmark", ()), key="period",
                  fields=("asset_class", "vintage", "period", "credit_tiers", "deal_count",
                          "pool_balance", "delinquency_percent", "period_chargeoff_percent",
                          "classification"))
    if not rows:
        return {"available": False, "reason": "no vintage benchmark for this period"}
    benchmark = rows[0]
    observed = _decimal(pool.get("delinquency_percent"))
    peer = _decimal(benchmark.get("delinquency_percent"))
    comparison: dict[str, Any] = {"available": True, **benchmark}
    if observed is not None and peer is not None:
        comparison["delinquency_vs_vintage"] = str(observed - peer)
    return comparison


def _repurchase(by_class: Mapping[str, list[Mapping[str, str]]]) -> list[Mapping[str, Any]]:
    """The depositor's filings, with per-deal attribution stated as absent.

    ABS-15G is filed per depositor, not per trust. A deal with no repurchases
    has no filing of its own to be absent, so no join is invented and the
    absence of attribution is a stated fact (`ABS-G18`).
    """
    return _items(by_class.get("repurchase", ()), key="repurchase_id",
                  fields=("repurchase_id", "depositor_cik", "form", "accession",
                          "filed_date", "deal_attributed", "note", "classification"))


def _assembly_cost(attributes: Mapping[str, str]) -> Mapping[str, Any]:
    """What this question cost, so an agent can reason about asking for more.

    Blocks and records, never time. The two record figures are NOT the same
    question: `records_scanned` is what the statements touched, and
    `records_materialized` is what became claims. A representative sample makes
    the second small while leaving the first large, and that is the honest
    shape of sampling rather than a defect (`ABS-F-01`).
    """
    band = attributes.get("cost_band", "")
    return {
        "records_materialized": attributes.get("records_materialized", ""),
        "records_scanned": attributes.get("records_scanned", ""),
        "blocks_scanned": attributes.get("blocks_scanned", ""),
        "cost_band": band,
        "next_level_down": _next_level(attributes.get("effective_granularity", "")),
        "note": (
            "cost is stated in blocks and records, never in time: on this estate one"
            " granularity's median ran from 0.148 ms to 205.871 ms across six runs on identical"
            " data while its block count never moved"
        ),
    }


def _next_level(effective: str) -> Mapping[str, str]:
    """What asking for one more level of detail would mean, stated relationally."""
    if effective not in GRANULARITY_ORDER:
        return {"granularity": "", "consequence": ""}
    index = GRANULARITY_ORDER.index(effective)
    if index + 1 >= len(GRANULARITY_ORDER):
        return {"granularity": "", "consequence": "this is the finest granularity this product serves"}
    nxt = GRANULARITY_ORDER[index + 1]
    if nxt == "loan":
        return {
            "granularity": nxt,
            "consequence": (
                "loan-scale: the only step that changes cost materially, and the step the"
                " privacy ceiling sits on. It requires a positive `loan_sample`, and the"
                " four borrower attributes the estate restricts are not served at any sample size"
            ),
        }
    return {
        "granularity": nxt,
        "consequence": "aggregate-scale: indistinguishable in block terms from this level",
    }


def _findings(
    triggers: Sequence[Mapping[str, Any]], by_class: Mapping[str, list[Mapping[str, str]]]
) -> list[Mapping[str, str]]:
    """What the product could not do, named — never dropped and never faked."""
    findings: list[Mapping[str, str]] = []
    for trigger in triggers:
        if trigger.get("anchored") == "false":
            findings.append({
                "finding": "threshold-has-no-public-anchor",
                "subject": trigger["trigger_id"],
                "detail": (
                    "this threshold is in force at the requested instant and carries no filed"
                    " prospectus passage; it is served unanchored rather than refused or dropped,"
                    " and no prospectus text is minted for it"
                ),
            })
        if not trigger.get("threshold_value"):
            findings.append({
                "finding": "threshold-is-not-a-number",
                "subject": trigger["trigger_id"],
                "detail": (
                    f"the threshold is defined as a formula in unit"
                    f" `{trigger.get('threshold_unit', '')}`; proximity is uncomputable and is"
                    f" not reported as zero"
                ),
            })
    if by_class.get("repurchase"):
        findings.append({
            "finding": "repurchase-activity-is-depositor-scoped",
            "subject": "abs-15g",
            "detail": (
                "ABS-15G is filed per depositor, not per trust, so these filings cover the whole"
                " shelf. A deal with no repurchases has no filing of its own to be absent, and no"
                " per-deal join is invented"
            ),
        })
    return sorted(findings, key=lambda row: (row["finding"], row["subject"]))


def _granular_member(member: str, by_class: Mapping[str, list[Mapping[str, str]]]) -> Any:
    if member == "cohort_performance":
        return _cohorts(by_class)
    if member == "loan_sample_detail":
        return _items(by_class.get("loan", ()), key="asset_number",
                      fields=("asset_number", "period", "reporting_period_ending_date",
                              "original_loan_amount",
                              "reporting_period_actual_end_balance_amount",
                              "current_delinquency_status", "chargedoff_principal_amount",
                              "recovered_amount", "classification"))
    raise ValueError(f"member {member!r} is declared but Pi emits nothing for it")


def _deal_member(attributes: Mapping[str, str]) -> Mapping[str, Any]:
    return {
        "deal_id": attributes.get("deal_id", ""),
        "legal_name": attributes.get("legal_name", ""),
        "cik": attributes.get("cik", ""),
        "depositor_cik": attributes.get("depositor_cik", ""),
        "credit_tier": attributes.get("credit_tier", ""),
        "vintage": attributes.get("vintage", ""),
        "servicer": attributes.get("servicer", ""),
        "period": attributes.get("period", ""),
    }


def _items(records: Any, *, key: str, fields: Sequence[str]) -> list[Mapping[str, str]]:
    rows = [{field: str(record.get(field, "")) for field in fields} for record in records]
    return sorted(rows, key=lambda row: row[key])


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, ArithmeticError):
        return None


# =========================================================================
# THE VIEW-SIDE DEBT READER
# =========================================================================


def view_completeness(view: GraphView) -> Decimal:
    """`C` = required classes present / required.

    An empty view (no deal claim) reads 0. A class the GRANULARITY CEILING
    excluded is still REQUIRED — the product genuinely is less complete for a
    principal who may not ask for it, and saying otherwise would hide the cost
    of the entitlement rather than measure it.
    """
    import acquisition  # noqa: PLC0415

    anchors = [record for record in view.entities if record.claim.entity_class == "deal"]
    if not anchors:
        return Decimal("0.0000")
    required = acquisition.required_classes()
    present = {record.claim.entity_class for record in view.entities}
    found = sum(1 for entity_class in required if entity_class in present)
    return (Decimal(found) / Decimal(len(required))).quantize(Decimal("0.0001"))
