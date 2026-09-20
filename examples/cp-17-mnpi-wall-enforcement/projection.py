"""Π for `cib.mnpi-wall` — one plan, three role branches, and the view-side debt reader.

[ADAPT] the payload shape here. Π reads the governed view and nothing beside
it (`CP13C-F-01`): the perspective it is handed, the claims in the view, and
the effective `known_as_of` the factory closed over. It never sees a wall
crossing, a restriction row or another principal's plan — those never enter
the fabric (`CP-SPEC-017` §D.3 step 1.7).

THE MEMBER SET IS A FUNCTION OF THE ROLE, NEVER OF THE SUBJECT (`MWE-G04`):
`artifacts/perspectives.yaml` declares which list members each role carries;
Π emits exactly those, empty or not, for every question — including the
empty view a subject with no issuer row produces, which is served with the
same shape (`MWE-G16`).
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
MEMBER_BY_CLASS: Mapping[str, str] = dict(_DECLARED["member_by_class"])
ROLE_MEMBERS: Mapping[str, tuple[str, ...]] = {
    role: tuple(spec["members"]) for role, spec in _DECLARED["roles"].items()
}
LIST_MEMBERS: tuple[str, ...] = tuple(sorted(set(MEMBER_BY_CLASS.values())))
CLASSIFICATION_BOUNDED_MEMBERS: tuple[str, ...] = tuple(_DECLARED["classification_bounded_members"])
_VOCABULARY: Mapping[str, Any] = yaml.safe_load((HERE / "artifacts" / "source-vocabulary.yaml").read_text(encoding="utf-8"))["declaration"]
CLASSIFICATION_VOCABULARY: tuple[str, ...] = tuple(_VOCABULARY["classification"]["vocabulary"])
CLASS_BY_MEMBER: Mapping[str, str] = {member: entity_class for entity_class, member in MEMBER_BY_CLASS.items()}


def members_for(role: str) -> set[str]:
    """The declared member set for `role` (the gate's authority, `MWE-G04`)."""
    return set(COMMON_MEMBERS) | set(ROLE_MEMBERS[role])


class MnpiWallProjection:
    """One `plan_id`; `invoke` branches on `perspective.role`."""

    def __init__(self, *, plan_id: str, required: tuple[str, ...], known_as_of: str) -> None:
        self._plan_id = plan_id
        self._required = required
        self._known_as_of = known_as_of

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
        if role not in ROLE_MEMBERS:
            raise ValueError(f"role {role!r} is not declared in `artifacts/perspectives.yaml`")
        issuers = [record for record in view.entities if record.claim.entity_class == "issuer"]
        if len(issuers) > 1:
            raise ValueError("the view holds more than one issuer; it was not written by one question")
        issuer = issuers[0] if issuers else None
        by_class: dict[str, list[Mapping[str, str]]] = {}
        for record in view.entities:
            by_class.setdefault(record.claim.entity_class, []).append(dict(record.claim.attributes))
        payload: dict[str, Any] = {
            "role": role,
            "known_as_of": self._known_as_of,
            "plan": None if issuer is None else json.loads(issuer.claim.attributes["plan_json"]),
            "issuer": None if issuer is None else _issuer_member(issuer.claim.attributes),
            "family": _items(by_class.get("family_member", ()), key="lei", fields=("lei", "legal_name", "relation", "classification")),
            "edge_types_served": sorted({edge.claim.relationship_type for edge in view.relationships}),
            "entities_in_view": len(view.entities),
        }
        for member in ROLE_MEMBERS[role]:
            entity_class = CLASS_BY_MEMBER[member]
            payload[member] = _items(by_class.get(entity_class, ()), key=_KEY_BY_CLASS[entity_class],
                                     fields=_FIELDS_BY_CLASS[entity_class])
        return ProjectionOutput(plan_id=self._plan_id, payload=payload)


_KEY_BY_CLASS = {
    "deal_engagement": "deal_id",
    "interaction": "interaction_id",
    "research_note": "note_id",
    "position": "position_id",
    "family_member": "lei",
}
_FIELDS_BY_CLASS = {
    "deal_engagement": ("deal_id", "deal_type", "stage", "opened_date", "classification"),
    "interaction": ("interaction_id", "interaction_type", "interaction_date", "deal_id", "classification"),
    "research_note": ("note_id", "title", "authored_date", "status", "classification", "content_hash"),
    "position": ("position_id", "book", "quantity", "as_of", "classification"),
    "family_member": ("lei", "legal_name", "relation", "classification"),
}


def _issuer_member(attributes: Mapping[str, str]) -> Mapping[str, Any]:
    disclosure = attributes.get("reg_fd_disclosure_json", "null")
    return {
        "lei": attributes.get("lei", ""),
        "legal_name": attributes.get("legal_name", ""),
        # Non-governing context by ruling: never a filter, never an admission rule.
        "legal_jurisdiction": attributes.get("legal_jurisdiction", ""),
        "entity_status": attributes.get("entity_status", ""),
        "reg_fd_disclosure": json.loads(disclosure) if disclosure else None,
        "ledger_t": attributes.get("ledger_t", "unreported"),
    }


def _items(records: Any, *, key: str, fields: tuple[str, ...]) -> list[Mapping[str, str]]:
    rows = [{field: record.get(field, "") for field in fields} for record in records]
    return sorted(rows, key=lambda row: row[key])


# =========================================================================
# THE VIEW-SIDE DEBT READER — C over the principal's own required classes
# =========================================================================


def view_completeness(view: GraphView) -> Decimal:
    """`C` = required classes present ÷ required, from the issuer's own plan.

    An empty view (no issuer claim) reads 0: nothing admitted is a coverage
    shortfall (`CP13C-F-05` b). A class the principal may not receive is not
    in its `C_required` (`D-IMPL-105`, `MWE-G20`).
    """
    issuers = [record for record in view.entities if record.claim.entity_class == "issuer"]
    if not issuers:
        return Decimal("0.0000")
    plan = json.loads(issuers[0].claim.attributes["plan_json"])
    required = list(plan["required_classes"])
    if not required:
        return Decimal("1.0000")
    present = {record.claim.entity_class for record in view.entities}
    found = sum(1 for entity_class in required if entity_class in present)
    return (Decimal(found) / Decimal(len(required))).quantize(Decimal("0.0001"))
