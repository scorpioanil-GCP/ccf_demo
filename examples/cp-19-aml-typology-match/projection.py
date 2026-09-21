"""Π for `compliance.aml-typology` — one plan, three perspective branches.

[ADAPT] the payload shape here. Π reads the governed view and nothing beside
it: the perspective it is handed, the claims in the view, and the effective
`as_of` the factory closed over. It never sees a SAR classification row, a
disposition rule set or another perspective's plan — those never enter the
fabric (`CP-SPEC-019` §D.3).

THE MEMBER SET IS A FUNCTION OF THE PERSPECTIVE, NEVER OF THE ALERT
(`ATM-G07`, `ATM-G08`): `artifacts/perspectives.yaml` declares which members
each perspective carries; Π emits exactly those, empty or not, for every
question — including the empty view an alert id with no row produces, served
with the same shape (`ATM-G14`).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
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
PERSPECTIVE_MEMBERS: Mapping[str, tuple[str, ...]] = {
    name: tuple(spec["members"]) for name, spec in _DECLARED["perspectives"].items()
}
SEES_SAR: Mapping[str, tuple[str, ...]] = {
    name: tuple(spec["sees_sar_classifications"]) for name, spec in _DECLARED["perspectives"].items()
}
DISPOSITION_BOUNDED_MEMBERS: tuple[str, ...] = tuple(_DECLARED["disposition_bounded_members"])
CLASSIFICATION_VOCABULARY: tuple[str, ...] = tuple(_DECLARED["classification_vocabulary"])
#: The members Π emits as LISTS of classified items — the gate's containment
#: walk. `policy_version_attribution` is a mapping and `disposition_candidates`
#: carries no classification, so neither is here.
LIST_MEMBERS: tuple[str, ...] = tuple(_DECLARED["classified_list_members"])


def members_for(perspective: str) -> set[str]:
    """The declared member set for `perspective` (the gate's authority)."""
    return set(COMMON_MEMBERS) | set(PERSPECTIVE_MEMBERS[perspective])


class AmlTypologyProjection:
    """One `plan_id`; `invoke` branches on `perspective.role`."""

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
        if role not in PERSPECTIVE_MEMBERS:
            raise ValueError(f"perspective {role!r} is not declared in `artifacts/perspectives.yaml`")
        alerts = [record for record in view.entities if record.claim.entity_class == "alert"]
        if len(alerts) > 1:
            raise ValueError("the view holds more than one alert; it was not written by one question")
        alert = alerts[0] if alerts else None
        by_class: dict[str, list[Mapping[str, str]]] = {}
        for record in view.entities:
            by_class.setdefault(record.claim.entity_class, []).append(dict(record.claim.attributes))

        attributes = dict(alert.claim.attributes) if alert is not None else {}
        permitted = json.loads(attributes.get("permitted_json", "[]")) if alert is not None else []
        payload: dict[str, Any] = {
            "perspective": role,
            "as_of": self._as_of,
            "posture": json.loads(attributes["posture_json"]) if attributes.get("posture_json") else None,
            "alert": None if alert is None else _alert_member(attributes),
            "permitted_dispositions": permitted,
            "edge_types_served": sorted({edge.claim.relationship_type for edge in view.relationships}),
            "entities_in_view": len(view.entities),
        }
        for member in PERSPECTIVE_MEMBERS[role]:
            payload[member] = _member(member, by_class, permitted=permitted, role=role)
        return ProjectionOutput(plan_id=self._plan_id, payload=payload)


def _member(
    member: str, by_class: Mapping[str, list[Mapping[str, str]]], *,
    permitted: list[str], role: str,
) -> Any:
    if member == "typology_matches":
        return _items(by_class.get("typology_match", ()), key="typology_id",
                      fields=("typology_id", "label", "confidence", "classification"))
    if member == "disposition_candidates":
        # GENERATED FROM THE PERMITTED SET ONLY. A disposition the posture
        # forbids is not generated and then filtered — it is never
        # constructed (`CP-SPEC-019` claim 2).
        return [{"disposition": name, "basis": "posture-permitted"} for name in permitted]
    if member == "sanctions_screening":
        return _items(by_class.get("screening_result", ()), key="person_key",
                      fields=("person_key", "listed_name", "score", "disposition", "classification"))
    if member == "counterparty_network":
        return _items([row for row in by_class.get("party", ()) if row.get("hops") != "0"],
                      key="party_id", fields=("party_id", "legal_name", "jurisdiction", "hops", "classification"))
    if member == "ownership_chain":
        return _items([row for row in by_class.get("party", ()) if row.get("hops") == "0"],
                      key="party_id", fields=("party_id", "legal_name", "jurisdiction", "party_kind", "classification"))
    if member == "prior_alert_lineage":
        return _items(by_class.get("prior_alert", ()), key="alert_id",
                      fields=("alert_id", "relation", "raised_at", "classification"))
    if member == "sar_filing_history":
        return _items(by_class.get("sar_record", ()), key="sar_id",
                      fields=("sar_id", "alert_id", "classification"))
    if member == "policy_version_attribution":
        return {"perspective": role, "advisories_read": len(by_class.get("advisory_passage", ()))}
    if member == "reasoning_trail":
        return _items(by_class.get("advisory_passage", ()), key="passage_id",
                      fields=("passage_id", "advisory_number", "document_id", "typology_id", "classification"))
    raise ValueError(f"member {member!r} is declared but Π emits nothing for it")


def _alert_member(attributes: Mapping[str, str]) -> Mapping[str, Any]:
    return {
        "alert_id": attributes.get("alert_id", ""),
        "subject_party": attributes.get("subject_party", ""),
        "raised_at": attributes.get("raised_at", ""),
        "trigger": attributes.get("trigger", ""),
        "case_id": attributes.get("case_id", ""),
    }


def _items(records: Any, *, key: str, fields: tuple[str, ...]) -> list[Mapping[str, str]]:
    rows = [{field: record.get(field, "") for field in fields} for record in records]
    return sorted(rows, key=lambda row: row[key])


# =========================================================================
# THE VIEW-SIDE DEBT READER — C over the perspective's own required classes
# =========================================================================


def view_completeness(view: GraphView) -> Decimal:
    """`C` = required classes present / required, from the alert's own plan.

    An empty view (no alert claim) reads 0: nothing admitted is a coverage
    shortfall. A class the perspective may not receive is not in its
    `C_required`.
    """
    alerts = [record for record in view.entities if record.claim.entity_class == "alert"]
    if not alerts:
        return Decimal("0.0000")
    plan = json.loads(alerts[0].claim.attributes["plan_json"])
    required = list(plan["required_classes"])
    if not required:
        return Decimal("1.0000")
    present = {record.claim.entity_class for record in view.entities}
    found = sum(1 for entity_class in required if entity_class in present)
    return (Decimal(found) / Decimal(len(required))).quantize(Decimal("0.0001"))
