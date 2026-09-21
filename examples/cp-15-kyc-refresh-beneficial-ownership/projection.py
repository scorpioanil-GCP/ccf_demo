"""Pi for `compliance.beneficial-ownership` — one plan, three perspectives.

[ADAPT] the payload shape and the evaluation rule here. Pi reads the governed
view and nothing beside it: the perspective it is handed, the claims in the
view, and the effective `as_of` the factory closed over. It never sees the
principal register, the jurisdiction grants or a person the envelope excluded
— those never enter the fabric (`CP-SPEC-015` §D.3).

A FINDING IS NOT AN ABSENCE. A person below the reporting threshold, a
resolution below the confidence floor, and a sanctions hit in the review band
are all kept INSIDE the product as findings. The vault specification's own
words: *a low-confidence match is a finding, not an absence.* What happens to
a finding afterwards — referral to a human — is `review.py`'s, and it happens
after this product is complete and immutable.

THE CYCLE MEMBER IS PRESENT AND EMPTY, honestly. No ownership cycles exist in
this estate (measured; `CP-SPEC-015` §0.3), Dave ruled *do not engineer* them,
and the member is served rather than omitted so its absence is a stated fact
rather than an inference (`UBO-G19`).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
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
PRINCIPAL_ID: Mapping[str, str] = {
    name: str(spec["principal_id"]) for name, spec in _DECLARED["perspectives"].items()
}
CLASSIFICATION_VOCABULARY: tuple[str, ...] = tuple(_DECLARED["classification_vocabulary"])
LIST_MEMBERS: tuple[str, ...] = tuple(_DECLARED["classified_list_members"])


def members_for(perspective: str) -> set[str]:
    """The declared member set for `perspective` (the gate's authority)."""
    return set(COMMON_MEMBERS) | set(PERSPECTIVE_MEMBERS[perspective])


class BeneficialOwnershipProjection:
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
        anchors = [record for record in view.entities if record.claim.entity_class == "entity"]
        if len(anchors) > 1:
            raise ValueError("the view holds more than one anchor; it was not written by one question")
        anchor = anchors[0] if anchors else None
        by_class: dict[str, list[Mapping[str, str]]] = {}
        for record in view.entities:
            by_class.setdefault(record.claim.entity_class, []).append(dict(record.claim.attributes))

        attributes = dict(anchor.claim.attributes) if anchor is not None else {}
        threshold = Decimal(attributes["applicable_threshold"]) if attributes.get("applicable_threshold") else None
        floor = Decimal(attributes["min_confidence"]) if attributes.get("min_confidence") else None
        chain = _chain(by_class, floor=floor)

        payload: dict[str, Any] = {
            "perspective": role,
            "as_of": self._as_of,
            "intent": attributes.get("intent", ""),
            "entity": None if anchor is None else _entity_member(attributes),
            "applicable_threshold": "" if threshold is None else str(threshold),
            "min_confidence": "" if floor is None else str(floor),
            "ownership_chain": chain,
            "reportable_owners": [p for p in chain if threshold is not None
                                  and Decimal(p["effective_pct"]) >= threshold],
            "sub_threshold_findings": [p for p in chain if threshold is not None
                                       and Decimal(p["effective_pct"]) < threshold],
            "resolution_findings": _resolution_findings(by_class, floor=floor),
            "sanctions_findings": _items(by_class.get("screening", ()), key="entry_id",
                                         fields=("person_key", "entry_id", "listed_name", "score",
                                                 "disposition", "in_review_band", "classification")),
            # PRESENT AND EMPTY, and that is the whole point (`UBO-G19`).
            "cycle_findings": _cycle_findings(by_class),
            "refresh_state": json.loads(attributes["refresh_state_json"]) if attributes.get("refresh_state_json")
            else {"available": False, "reason": "no anchor"},
            "review_submissions": [],
            "entities_in_view": len(view.entities),
            "edge_types_served": sorted({edge.claim.relationship_type for edge in view.relationships}),
        }
        for member in PERSPECTIVE_MEMBERS[role]:
            payload[member] = _member(member, by_class, role=role, attributes=attributes)
        return ProjectionOutput(plan_id=self._plan_id, payload=payload)


# =========================================================================
# THE EVALUATION — a finding is kept, never dropped
# =========================================================================


def _chain(by_class: Mapping[str, list[Mapping[str, str]]], *, floor: Decimal | None) -> list[Mapping[str, Any]]:
    """The persons the envelope admitted, each with its resolution confidence.

    **Every person carries a confidence** (`UBO-G04`). Where the estate holds
    several crosswalk rows for one person the STRONGEST is carried, because
    that is the resolution the system of record stands behind; the weaker rows
    remain visible as resolution findings.
    """
    best: dict[str, Decimal] = {}
    band: dict[str, str] = {}
    for row in by_class.get("resolution", ()):
        key = str(row.get("person_key", ""))
        score = Decimal(str(row.get("match_score", "0")))
        if key and score > best.get(key, Decimal(-1)):
            best[key] = score
            band[key] = str(row.get("match_band", ""))
    out: list[Mapping[str, Any]] = []
    for person in by_class.get("person", ()):
        key = str(person.get("person_key", ""))
        confidence = best.get(key)
        out.append({
            "person_key": key,
            "nationality": str(person.get("nationality", "")),
            "country_of_residence": str(person.get("country_of_residence", "")),
            "effective_pct": str(person.get("effective_pct", "0")),
            "depth": str(person.get("depth", "")),
            # Carried, never recomputed (`CP-SPEC-015` §F.4). Where the estate
            # holds no crosswalk row the confidence is stated as unresolved
            # rather than defaulted to a number nobody asserted.
            "resolution_confidence": str(confidence) if confidence is not None else "unresolved",
            "resolution_band": band.get(key, "none"),
            "below_confidence_floor": str(
                floor is not None and confidence is not None and confidence < floor
            ).lower(),
            "classification": str(person.get("classification", "")),
        })
    return sorted(out, key=lambda row: (-Decimal(row["effective_pct"]), row["person_key"]))


def _resolution_findings(
    by_class: Mapping[str, list[Mapping[str, str]]], *, floor: Decimal | None
) -> list[Mapping[str, Any]]:
    """Every resolution the estate holds, with the ones below the floor named.

    A resolution below the floor is a FINDING, not an absence — it stays in
    the product and is referred, rather than being dropped so the product
    looks cleaner than the evidence.
    """
    rows = []
    for row in by_class.get("resolution", ()):
        score = Decimal(str(row.get("match_score", "0")))
        rows.append({
            "person_key": str(row.get("person_key", "")),
            "source_system": str(row.get("source_system", "")),
            "source_name": str(row.get("source_name", "")),
            "match_score": str(score),
            "match_band": str(row.get("match_band", "")),
            "below_floor": str(floor is not None and score < floor).lower(),
            "classification": str(row.get("classification", "")),
        })
    return sorted(rows, key=lambda row: (row["person_key"], row["source_system"]))


def _cycle_findings(by_class: Mapping[str, list[Mapping[str, str]]]) -> list[Mapping[str, Any]]:
    """Any ownership hop that revisits a node earlier in the same chain.

    **Computed, not assumed.** The member is empty in this estate because no
    chain revisits a node (measured 2026-09-21), and it is computed here
    rather than hard-coded to `[]` so that an estate which later contained a
    cycle would surface it without a code change — and so that the emptiness
    is a MEASUREMENT of the served view rather than a constant.
    """
    seen: dict[str, int] = {}
    findings: list[Mapping[str, Any]] = []
    hops = sorted(by_class.get("hop", ()), key=lambda h: int(h.get("hop_index", 0)))
    path: list[str] = []
    for hop in hops:
        owner, owned = str(hop.get("owner_id", "")), str(hop.get("owned_id", ""))
        if not path:
            path.append(owner)
            seen[owner] = 0
        path.append(owned)
        if owned in seen:
            findings.append({
                "revisited": owned,
                "at_hop": str(hop.get("hop_index", "")),
                "path": " -> ".join(path),
                "contribution_capped_at_first_revisit": "true",
            })
        seen.setdefault(owned, len(path) - 1)
    return findings


def _member(
    member: str, by_class: Mapping[str, list[Mapping[str, str]]], *,
    role: str, attributes: Mapping[str, str],
) -> Any:
    if member == "document_declarations":
        return _items(by_class.get("declaration", ()), key="document_id",
                      fields=("document_id", "kind", "declared_pct", "computed_pct",
                              "contradicts", "classification"))
    if member == "residency_entitlement":
        # The perspective's OWN entitlement, stated so a consumer knows which
        # evidence base it holds. It states WHAT the perspective may see, never
        # how many records were withheld from it.
        return {
            "perspective": role,
            "sees_eu_person_data": role == "kyc-analyst",
            "policy_version": attributes.get("policy_version", ""),
        }
    raise ValueError(f"member {member!r} is declared but Pi emits nothing for it")


def _entity_member(attributes: Mapping[str, str]) -> Mapping[str, Any]:
    return {
        "entity_id": attributes.get("entity_id", ""),
        "entity_kind": attributes.get("entity_kind", ""),
        "chain_id": attributes.get("chain_id", ""),
        "depth": attributes.get("depth", ""),
        "jurisdiction_path": attributes.get("jurisdiction_path", ""),
        "crosses_jurisdictions": attributes.get("crosses_jurisdictions", ""),
        "threshold_basis": attributes.get("threshold_basis", ""),
    }


def _items(records: Any, *, key: str, fields: Sequence[str]) -> list[Mapping[str, str]]:
    rows = [{field: str(record.get(field, "")) for field in fields} for record in records]
    return sorted(rows, key=lambda row: row[key])


# =========================================================================
# THE VIEW-SIDE DEBT READER
# =========================================================================


def view_completeness(view: GraphView) -> Decimal:
    """`C` = required classes present / required.

    An empty view (no anchor claim) reads 0. A class the residency envelope
    excluded is still REQUIRED — the product is genuinely less complete for a
    principal who may not see it, and saying otherwise would hide the cost of
    the entitlement rather than measure it.
    """
    import acquisition  # noqa: PLC0415

    anchors = [record for record in view.entities if record.claim.entity_class == "entity"]
    if not anchors:
        return Decimal("0.0000")
    required = acquisition.required_classes()
    present = {record.claim.entity_class for record in view.entities}
    found = sum(1 for entity_class in required if entity_class in present)
    return (Decimal(found) / Decimal(len(required))).quantize(Decimal("0.0001"))
