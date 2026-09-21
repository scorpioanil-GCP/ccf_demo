"""Pi for `cib.opportunity-synthesis` — one plan, three perspective branches,
and the ranking that makes the perspective a dimension of the PRODUCT.

[ADAPT] the payload shape and the scoring rule here. Pi reads the governed
view and nothing beside it: the perspective it is handed, the claims in the
view, and the effective `as_of` the factory closed over. It never sees another
banker's notes, another perspective's weights, or the restricted-list rows —
those never enter the fabric (`CP-SPEC-018` §D.3).

THE RANKING IS ARITHMETIC OVER A POLICY-VERSIONED WEIGHT VECTOR. No inference,
no LLM, no ordering that cannot be re-derived. Each admitted signal
contributes its weight decayed by its own half-life against `as_of`; the
contributions are summed and the ordering is truncated. Both the vector and
its version ride on the banker claim, so replay re-executing over the recorded
snapshot reproduces the HISTORICAL ranking even after the Control Plane has
moved to a later version (`IBO-G06`).

THE MEMBER SET IS A FUNCTION OF THE PERSPECTIVE, NEVER OF THE BANKER OR THE
REQUEST (`IBO-G12`). `artifacts/perspectives.yaml` declares which members each
perspective carries; Pi emits exactly those, empty or not.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import date, datetime
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
PERSPECTIVE_ID: Mapping[str, str] = {
    name: str(spec["perspective_id"]) for name, spec in _DECLARED["perspectives"].items()
}
CLASSIFICATION_VOCABULARY: tuple[str, ...] = tuple(_DECLARED["classification_vocabulary"])
LIST_MEMBERS: tuple[str, ...] = tuple(_DECLARED["classified_list_members"])

#: The default number of ranked rows served when the caller states none.
DEFAULT_LIMIT = 20
#: The classification a banker-local note carries. A note may encode what the
#: banker knows privately, so a RESTRICTED prospect's ranking is computed
#: without one — the restriction bounds the evidence admitted for it rather
#: than removing the prospect (`IBO-G08`, Dave's ruling of 2026-09-21).
BANKER_LOCAL = "banker-local"


def members_for(perspective: str) -> set[str]:
    """The declared member set for `perspective` (the gate's authority)."""
    return set(COMMON_MEMBERS) | set(PERSPECTIVE_MEMBERS[perspective])


class OpportunitySynthesisProjection:
    """One `plan_id`; `invoke` branches on `perspective.role`."""

    def __init__(self, *, plan_id: str, required: tuple[str, ...], as_of: str, limit: int) -> None:
        self._plan_id = plan_id
        self._required = required
        self._as_of = as_of
        self._limit = limit

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
        bankers = [record for record in view.entities if record.claim.entity_class == "banker"]
        if len(bankers) > 1:
            raise ValueError("the view holds more than one banker; it was not written by one question")
        banker = bankers[0] if bankers else None
        by_class: dict[str, list[Mapping[str, str]]] = {}
        for record in view.entities:
            by_class.setdefault(record.claim.entity_class, []).append(dict(record.claim.attributes))

        attributes = dict(banker.claim.attributes) if banker is not None else {}
        vector = json.loads(attributes["weights_json"]) if attributes.get("weights_json") else {}
        plan = json.loads(attributes["plan_json"]) if attributes.get("plan_json") else {}
        portfolio = json.loads(attributes["portfolio_json"]) if attributes.get("portfolio_json") else []
        optional = json.loads(attributes["optional_context_json"]) if attributes.get("optional_context_json") else {}
        ranked = _rank(
            by_class, vector=vector, as_of=self._as_of, limit=self._limit,
            admitted=tuple(plan.get("permitted_signal_types") or ()),
        )

        payload: dict[str, Any] = {
            "perspective": role,
            "as_of": self._as_of,
            "weight_version": str(vector.get("weight_version", "")),
            "banker": None if banker is None else _banker_member(attributes),
            "portfolio": portfolio,
            "portfolio_size": len(portfolio),
            "candidates_considered": len(by_class.get("prospect", ())),
            "ranked_opportunities": ranked,
            "signal_types_admitted": sorted(
                {str(s.get("signal_type", "")) for s in by_class.get("signal", ())}
                | {str(s.get("signal_type", "")) for s in by_class.get("standing_signal", ())}
                | {str(n.get("signal_type", "")) for n in by_class.get("note", ())}
                - {""}
            ),
            # STATED, never silently absent. With the CP-17 child count at
            # zero by ruling, EVERY row rests on the narrower evidence base and
            # the product says so rather than letting a consumer assume
            # otherwise (`IBO-G17`, `IBO-G18`).
            "optional_context": optional or {
                "mnpi_wall_child": "absent", "child_count": 0, "reason": "not-composed",
            },
            "edge_types_served": sorted({edge.claim.relationship_type for edge in view.relationships}),
            "entities_in_view": len(view.entities),
        }
        for member in PERSPECTIVE_MEMBERS[role]:
            payload[member] = _member(member, by_class, ranked=ranked, role=role, vector=vector)
        return ProjectionOutput(plan_id=self._plan_id, payload=payload)


# =========================================================================
# THE RANK — the deployment's own arithmetic, deliberately not an operator
# =========================================================================


def _rank(
    by_class: Mapping[str, list[Mapping[str, str]]], *, vector: Mapping[str, Any],
    as_of: str, limit: int, admitted: Sequence[str],
) -> list[Mapping[str, Any]]:
    """Score every candidate under the perspective's weights, and order them.

    A restricted prospect REMAINS a candidate; what its restriction bounds is
    the evidence admitted for it — no banker-local note contributes to a
    restricted prospect's score, because a private note may encode exactly
    what the restriction exists to contain.
    """
    weights = {key: Decimal(str(value)) for key, value in (vector.get("weights") or {}).items()}
    half_lives = {key: int(value) for key, value in (vector.get("half_life_days") or {}).items()}
    instant = _as_date(as_of)
    permitted = set(admitted)

    evidence: dict[str, list[Mapping[str, Any]]] = {}
    # STANDING signals first — undated, and they do not decay in the window.
    for standing in by_class.get("standing_signal", ()):
        lei = str(standing.get("lei", ""))
        signal_type = str(standing.get("signal_type", ""))
        if not lei or signal_type not in permitted:
            continue
        evidence.setdefault(lei, []).append({
            "signal_type": signal_type,
            "observed_on": "",
            "detail": str(standing.get("detail", "")),
            "classification": str(standing.get("classification", "")),
        })
    for signal in by_class.get("signal", ()):
        lei = str(signal.get("lei", ""))
        signal_type = str(signal.get("signal_type", ""))
        if not lei or signal_type not in permitted:
            continue
        evidence.setdefault(lei, []).append({
            "signal_type": signal_type,
            "observed_on": str(signal.get("observed_on", "")),
            "detail": str(signal.get("detail", "")),
            "classification": str(signal.get("classification", "")),
        })

    restricted = {
        str(row.get("lei", "")): str(row.get("restriction_type", ""))
        for row in by_class.get("prospect", ()) if row.get("restriction_type")
    }
    for note in by_class.get("note", ()):
        lei = str(note.get("lei", ""))
        if not lei or lei in restricted:
            continue  # the bound: a restricted prospect is ranked WITHOUT local notes
        signal_type = str(note.get("signal_type") or "banker_local_note")
        if signal_type not in permitted:
            continue
        evidence.setdefault(lei, []).append({
            "signal_type": signal_type,
            "observed_on": str(note.get("created_at", "")) or as_of[:10],
            "detail": f"note {note.get('note_id', '')} materiality={note.get('materiality', '')}",
            "classification": BANKER_LOCAL,
        })

    scored: list[Mapping[str, Any]] = []
    for prospect in by_class.get("prospect", ()):
        lei = str(prospect.get("lei", ""))
        contributions: list[Mapping[str, Any]] = []
        total = Decimal(0)
        for item in evidence.get(lei, ()):
            weight = weights.get(item["signal_type"])
            half_life = half_lives.get(item["signal_type"])
            if weight is None or half_life is None:
                continue
            observed = _as_date(item["observed_on"])
            if observed is None:
                # A STANDING signal — a maturity wall, say. It states a state
                # of the world at the decision instant rather than an event on
                # a day, so it does not decay inside the window: what decays is
                # a news event, not a repayment obligation.
                age, decay = 0, Decimal(1)
            else:
                age = abs((instant - observed).days) if instant is not None else 0
                decay = Decimal(2) ** Decimal(-age / half_life) if half_life else Decimal(1)
            contribution = (weight * decay).quantize(Decimal("0.000001"))
            total += contribution
            contributions.append({**item, "weight": str(weight), "age_days": age,
                                  "contribution": str(contribution)})
        if not contributions:
            continue  # a candidate with no evidence is not a ranked opportunity
        contributions.sort(key=lambda c: (-Decimal(c["contribution"]), c["signal_type"]))
        scored.append({
            "lei": lei,
            "legal_name": str(prospect.get("legal_name", "")),
            "score": str(total.quantize(Decimal("0.000001"))),
            "classification": str(prospect.get("classification", "")),
            "restriction_type": restricted.get(lei, ""),
            "mnpi_bearing": str(prospect.get("mnpi_bearing", "false")),
            "stated_appetite": str(prospect.get("stated_appetite", "")),
            "contributing_signals": contributions[:6],
            # Stated per row, because the evidence base is per row.
            "optional_context_contributed": False,
        })
    scored.sort(key=lambda row: (-Decimal(row["score"]), row["lei"]))
    return [{**row, "rank": index + 1} for index, row in enumerate(scored[:limit])]


def _member(
    member: str, by_class: Mapping[str, list[Mapping[str, str]]], *,
    ranked: Sequence[Mapping[str, Any]], role: str, vector: Mapping[str, Any],
) -> Any:
    if member == "catalyst_evidence":
        return _items([s for s in by_class.get("signal", ())
                       if str(s.get("signal_type")) in {"ma_event_8k", "activist_stake_13d", "insider_activity_form4"}],
                      key="signal_id", fields=("signal_id", "lei", "signal_type", "observed_on", "classification"))
    if member == "maturity_ladder":
        walls = [{**s, "observed_on": str(s.get("effective_on", ""))}
                 for s in by_class.get("standing_signal", ())
                 if str(s.get("signal_type")) == "maturity_wall"]
        spreads = [s for s in by_class.get("signal", ())
                   if str(s.get("signal_type")) == "spread_trajectory"]
        return _items([*walls, *spreads], key="signal_id",
                      fields=("signal_id", "lei", "signal_type", "observed_on", "detail", "classification"))
    if member == "peer_positioning":
        return _items([s for s in by_class.get("signal", ())
                       if str(s.get("signal_type")) in {"sector_news_gdelt", "institutional_positioning_13f",
                                                        "gov_revenue_concentration"}],
                      key="signal_id", fields=("signal_id", "lei", "signal_type", "observed_on", "classification"))
    if member == "local_note_attribution":
        # The banker's OWN notes, and which ranked rows they reached.
        reached = {row["lei"] for row in ranked
                   for c in row["contributing_signals"] if c["classification"] == BANKER_LOCAL}
        return _items([{**n, "reached_ranking": "true" if str(n.get("lei")) in reached else "false"}
                       for n in by_class.get("note", ())],
                      key="note_id",
                      fields=("note_id", "lei", "signal_type", "materiality", "rank_changing",
                              "reached_ranking", "classification"))
    if member == "policy_version_attribution":
        return {
            "perspective": role,
            "weight_version": str(vector.get("weight_version", "")),
            "signal_types_priced": len(vector.get("weights") or {}),
            "passages_read": len(by_class.get("passage", ())),
        }
    raise ValueError(f"member {member!r} is declared but Pi emits nothing for it")


def _banker_member(attributes: Mapping[str, str]) -> Mapping[str, Any]:
    return {
        "banker_id": attributes.get("banker_id", ""),
        "full_name": attributes.get("full_name", ""),
        "role": attributes.get("role", ""),
        "desk": attributes.get("desk", ""),
        "perspective_id": attributes.get("perspective_id", ""),
    }


def _items(records: Any, *, key: str, fields: tuple[str, ...]) -> list[Mapping[str, str]]:
    rows = [{field: str(record.get(field, "")) for field in fields} for record in records]
    return sorted(rows, key=lambda row: row[key])


def _as_date(value: str) -> date | None:
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


# =========================================================================
# THE VIEW-SIDE DEBT READER — C over the perspective's own required classes
# =========================================================================


def view_completeness(view: GraphView) -> Decimal:
    """`C` = required classes present / required, from the banker's own plan.

    An empty view (no banker claim) reads 0: nothing admitted is a coverage
    shortfall.
    """
    bankers = [record for record in view.entities if record.claim.entity_class == "banker"]
    if not bankers:
        return Decimal("0.0000")
    plan = json.loads(bankers[0].claim.attributes["plan_json"])
    required = list(plan["required_classes"])
    if not required:
        return Decimal("1.0000")
    present = {record.claim.entity_class for record in view.entities}
    found = sum(1 for entity_class in required if entity_class in present)
    return (Decimal(found) / Decimal(len(required))).quantize(Decimal("0.0001"))
