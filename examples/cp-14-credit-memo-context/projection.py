"""Π — the memo context this product serves, read off the graph view AND the admitted children.

[ADAPT] everything. [MECHANISM] the two Protocol members (`required_operators`
and `invoke`). Π is deployment code by construction (whitepaper §7.5).

**Two inputs, kept apart.** The obligor's identity is read off the GRAPH VIEW
the resolver hands in — the parent's own leg. Every section a memo prints
about the obligor's finances, family, exposure, collateral and covenants is
read off an ADMITTED CHILD'S CONTRACT, handed in through the `D-IMPL-339` view
(`build_with_children`), and never off a store: the parent consumes the
children's payloads and rebuilds none of them (`CMC-G27`).

**This slice's memo is a skeleton.** Each child section carries the child's
identity (class, lane, content address, producer's temporal boundary and
expiry) and a one-line summary read from its payload; the spec's section
templates, evidence references and benchmarks (§B.1, §D.2) are the parent's
product logic in later slices. A section whose child was not admitted is not
reachable here at all — a required child refuses the composite before Π runs
over children (`CMC-G18`).

**DECIMALS ARE SERVED AS TEXT.** A float is not bit-stable in a content address.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput
from ccf.products.contract import ContextProductContract
from ccf.projection.plan import Perspective, ProjectionOutput

CLASS_OBLIGOR = "obligor"
NOT_EVALUABLE = "NOT_EVALUABLE"


def _summary(product_class: str, contract: ContextProductContract) -> dict[str, Any]:
    """One line of what the child said, read off ITS payload — never re-derived."""
    payload = contract.payload
    if product_class == "credit-risk.spread":
        periods = payload.get("periods") or []
        return {
            "periods_served": len(periods),
            "latest_period_end": max((str(p.get("period_end", "")) for p in periods), default=NOT_EVALUABLE),
            "basis_applied": str((payload.get("obligor") or {}).get("basis_applied", NOT_EVALUABLE)),
        }
    return {"payload_members": sorted(str(key) for key in payload)}


class CreditMemoContextProjection:
    """The memo packet: the obligor, the decision frame, one section per required child."""

    def __init__(
        self,
        *,
        plan_id: str,
        required: tuple[str, ...],
        subject: str,
        memo_type: str,
        decision_instant: str,
        facility_id: str,
        children: Mapping[str, ContextProductContract] | None,
    ) -> None:
        self._plan_id = plan_id
        self._required = required
        self._subject = subject
        self._memo_type = memo_type
        self._decision_instant = decision_instant
        self._facility_id = facility_id
        self._children = children

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        return self._required

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        obligor: dict[str, Any] | None = None
        for record in view.entities:
            if record.claim.entity_class == CLASS_OBLIGOR:
                attributes = record.claim.attributes
                obligor = {
                    "lei": attributes.get("lei", ""),
                    "legal_name": attributes.get("legal_name", ""),
                    "legal_jurisdiction": attributes.get("legal_jurisdiction", ""),
                    "sic": attributes.get("sic", NOT_EVALUABLE),
                    "sic_description": attributes.get("sic_description", NOT_EVALUABLE),
                }
                break
        sections: dict[str, Any] = {}
        for product_class in sorted(self._children or {}):
            contract = self._children[product_class]  # type: ignore[index]
            sections[product_class] = {
                "child_schema_version": contract.schema_version,
                "child_tenant": contract.tenant_id,
                "child_temporal_boundary": contract.temporal_boundary.isoformat(),
                "child_expires_at": contract.expires_at.isoformat(),
                "summary": _summary(product_class, contract),
            }
        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                "obligor": obligor,
                "memo_type": self._memo_type,
                "decision_instant": self._decision_instant,
                "collateral_facility": self._facility_id,
                "children_asked_at": temporal_boundary.isoformat(),
                "sections": sections,
            },
        )
