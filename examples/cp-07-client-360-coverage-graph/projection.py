"""Π — the bank's relationship graph with one client, conditioned for coverage.

[ADAPT] everything. [MECHANISM] the two Protocol members.

**Π reads the admitted graph and nothing else.** No backend lookup happens
here. If a fact is not in the `GraphView` the resolver handed in, it does not
enter the score — which is what makes the score replayable from the snapshot
rather than from whatever the source happened to hold at read time.

## Relationship strength

Deterministic arithmetic over policy-versioned weights: how many interactions
reached a banker–client pair, how recently, and how senior the banker is. No
model is in the path, which is the claim `assembly_mode: algorithmic` makes at
registration time.

## Coverage gaps — the insight, not a by-product

A client-side officer whose strongest bank-side relationship is absent or weak.
**This is what a CRM field cannot contain**: *"who covers this client?"* is a
field; *"whom has nobody met?"* is a path, and it is only answerable once the
interaction graph and the officer roster are in the same frame.

## Truncation is a product fact, not a debt input

The payload states what was admitted, what existed, and that the acquisition
boundary cut the evidence. **It is deliberately NOT folded into `D_c`.** A
bounded read is a deliberate act with a known edge; Context Debt measures
something else — how complete the evidence *that was admitted* actually is. A
graph can be populated and still be incomplete, and a consumer needs to be told
both what the fabric knows and where the boundary fell.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput
from ccf.projection.plan import Perspective, ProjectionOutput

HERE = Path(__file__).parent
KIND = "node_kind"


def declaration() -> Mapping[str, Any]:
    document: Mapping[str, Any] = yaml.safe_load(
        (HERE / "artifacts" / "projection.yaml").read_text(encoding="utf-8"))
    return document["declaration"]


class ClientCoverageProjection:
    """Who knows whom, how strongly, and where nobody does."""

    def __init__(self, *, plan_id: str, required: tuple[str, ...],
                 declared: Mapping[str, Any], anchor: str, client_name: str | None,
                 truncated: bool, admitted: int, available: int,
                 withheld_need_to_know: int, since: str, limit: int) -> None:
        self._plan_id = plan_id
        self._required = required
        self._declared = declared
        self._anchor = anchor
        self._client_name = client_name
        # The acquisition boundary, carried as fact rather than inferred.
        self._truncated = truncated
        self._admitted = admitted
        self._available = available
        self._withheld = withheld_need_to_know
        self._since = since
        self._limit = limit

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        return self._required

    def _seniority(self, rank: str | None) -> Decimal:
        ranks = self._declared["strength"]["seniority_rank"]
        return Decimal(str(ranks.get((rank or "").lower().replace(" ", "_"), "0.2")))

    def invoke(self, *, view: GraphView, operator_outputs: Mapping[str, OperatorOutput],
               perspective: Perspective, temporal_boundary: datetime) -> ProjectionOutput:
        strength_cfg = self._declared["strength"]
        gap_cfg = self._declared["gap"]

        by_kind: dict[str, list[Any]] = {}
        ref_of: dict[str, str] = {}
        for record in view.entities:
            attributes = record.claim.attributes
            ref_of[record.claim.entity_uri] = attributes.get("ref", record.claim.entity_uri)
            by_kind.setdefault(attributes.get(KIND, ""), []).append(record)

        interactions = {
            ref_of[r.claim.entity_uri]: r.claim.attributes
            for r in by_kind.get("interaction", [])
        }

        # Who took part in what, from the ADMITTED edges only.
        took_part: dict[str, set[str]] = {}
        covers: set[str] = set()
        employs: dict[str, str] = {}
        for record in view.relationships:
            subject = ref_of.get(record.claim.subject_uri, "")
            obj = ref_of.get(record.claim.object_uri, "")
            kind = record.claim.relationship_type
            if kind == "participatedIn":
                took_part.setdefault(subject, set()).add(obj)
            elif kind == "coversClient":
                covers.add(subject)
            elif kind == "employedBy":
                employs[subject] = obj

        horizon = int(strength_cfg["recency_horizon_days"])

        def _score(party_ref: str, seniority: str | None) -> tuple[Decimal, int, str | None]:
            """Strength, interaction count, and the most recent date — from the graph."""
            reached = [
                interactions[i] for i in took_part.get(party_ref, ())
                if i in interactions
            ]
            if not reached:
                return Decimal(0), 0, None
            dates = sorted(
                (a.get("interaction_date") for a in reached if a.get("interaction_date")),
                reverse=True)
            latest = dates[0] if dates else None
            # Frequency saturates: the tenth meeting says less than the second.
            frequency = min(Decimal(len(reached)) / Decimal(10), Decimal(1))
            recency = Decimal(0)
            if latest:
                age = (temporal_boundary.date() - datetime.fromisoformat(latest).date()).days
                recency = max(Decimal(0), Decimal(1) - Decimal(age) / Decimal(horizon))
            score = (
                Decimal(str(strength_cfg["frequency_weight"])) * frequency
                + Decimal(str(strength_cfg["recency_weight"])) * recency
                + Decimal(str(strength_cfg["seniority_weight"])) * self._seniority(seniority)
            )
            return score, len(reached), latest

        bankers = []
        for record in sorted(by_kind.get("banker", []), key=lambda r: r.claim.entity_uri):
            attributes = record.claim.attributes
            ref = ref_of[record.claim.entity_uri]
            score, count, latest = _score(ref, attributes.get("seniority"))
            bankers.append({
                "banker": ref, "name": attributes.get("label") or None,
                "role": attributes.get("role") or None,
                "seniority": attributes.get("seniority") or None,
                "desk": attributes.get("desk") or None,
                "covers_client": ref in covers,
                "interactions": count,
                "most_recent": latest,
                "relationship_strength": str(round(score, 4)),
            })
        bankers.sort(key=lambda b: Decimal(b["relationship_strength"]), reverse=True)

        # WHICH DEALS THE ADMITTED INTERACTIONS CONCERN. Read off the graph,
        # like everything else here — a deal the bound cut out is simply absent,
        # and `edge_types_present` is what tells the consumer so.
        discussed: dict[str, set[str]] = {}
        for record in view.relationships:
            if record.claim.relationship_type == "relatedToDeal":
                discussed.setdefault(ref_of.get(record.claim.object_uri, ""), set()).add(
                    ref_of.get(record.claim.subject_uri, ""))
        deals = [
            {
                "deal": ref_of[record.claim.entity_uri],
                "deal_type": record.claim.attributes.get("deal_type") or None,
                "stage": record.claim.attributes.get("stage") or None,
                "opened": record.claim.attributes.get("opened_date") or None,
                "interactions": len(discussed.get(ref_of[record.claim.entity_uri], ())),
            }
            for record in sorted(by_kind.get("deal", []),
                                 key=lambda r: r.claim.entity_uri)
        ]

        weak_at = Decimal(str(gap_cfg["weak_at_or_below"]))
        material = {r.lower() for r in gap_cfg["material_roles"]}

        people, gaps = [], []
        for record in sorted(by_kind.get("person", []), key=lambda r: r.claim.entity_uri):
            attributes = record.claim.attributes
            ref = ref_of[record.claim.entity_uri]
            # An officer's strength is the best bank-side relationship reaching
            # any interaction they took part in.
            shared = took_part.get(ref, set())
            best = Decimal(0)
            met_by: list[str] = []
            for banker in bankers:
                overlap = shared & took_part.get(banker["banker"], set())
                if overlap:
                    met_by.append(banker["banker"])
                    best = max(best, Decimal(banker["relationship_strength"]))
            role = attributes.get("role") or attributes.get("officer_title") or ""
            entry = {
                "person": ref, "name": attributes.get("label") or None,
                "role": role or None,
                "officer_title": attributes.get("officer_title") or None,
                "met_by": sorted(met_by),
                "best_relationship_strength": str(round(best, 4)),
            }
            people.append(entry)
            if best <= weak_at:
                gaps.append({
                    **entry,
                    "gap_kind": "never-met" if not met_by else "weak",
                    # Materiality is declared, not judged here.
                    "material": any(m in role.lower() for m in material),
                })

        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                "role": perspective.role,
                "client": {"lei": self._anchor, "name": self._client_name},
                "window": {"since": self._since, "limit": self._limit},
                # THE ACQUISITION BOUNDARY, as a first-class product fact.
                "evidence_boundary": {
                    "interactions_admitted": self._admitted,
                    "interactions_available": self._available,
                    "truncated": self._truncated,
                    "withheld_need_to_know": self._withheld,
                    "note": self._declared["truncation"]["disclosure_note"],
                },
                "bankers": bankers,
                "people": people,
                # §C's fourth edge, and the reason it is served rather than
                # counted: which deals the admitted interactions concern is
                # part of the coverage picture, and on this estate one anchor
                # carries the edge and another does not.
                "deals": deals,
                "findings": {
                    "coverage_gaps": len(gaps),
                    "material_coverage_gaps": sum(1 for g in gaps if g["material"]),
                    "never_met": sum(1 for g in gaps if g["gap_kind"] == "never-met"),
                    "bankers_covering": sum(1 for b in bankers if b["covers_client"]),
                    "edge_types_present": sorted(
                        {r.claim.relationship_type for r in view.relationships}),
                    "gaps": gaps,
                },
            },
        )


def plan_class() -> type[ClientCoverageProjection]:
    return ClientCoverageProjection
