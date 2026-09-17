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
from ccf.contracts.canonical import content_hash
from ccf.products.contract import ContextProductContract
from ccf.projection.plan import Perspective, ProjectionOutput

CLASS_OBLIGOR = "obligor"
NOT_EVALUABLE = "NOT_EVALUABLE"


def _summary(product_class: str, contract: ContextProductContract) -> dict[str, Any]:
    """What the child said, read off ITS payload — never re-derived, never rebuilt.

    One block per class, each a handful of the child's own served members
    restated by name (`CMC-G27`): the memo prints what the producer
    determined and computes nothing the producer computed. A class this
    consumer has no reading for lists the child's payload members, so a
    later revision can see what it left unread.
    """
    payload = contract.payload
    if product_class == "credit-risk.spread":
        periods = payload.get("periods") or []
        return {
            "periods": len(periods),
            "latest_period_end": max((str(p.get("period_end", "")) for p in periods), default=NOT_EVALUABLE),
            "basis_applied": str((payload.get("obligor") or {}).get("basis_applied", NOT_EVALUABLE)),
        }
    if product_class == "reference.corporate-family":
        findings = payload.get("findings") or {}
        return {
            "depth_served": payload.get("depth_served", NOT_EVALUABLE),
            "entities": payload.get("node_count", NOT_EVALUABLE),
            "relationships": payload.get("relationship_count", NOT_EVALUABLE),
            "resolved": payload.get("resolved_count", NOT_EVALUABLE),
            "ownership_circuits": findings.get("cycles_found", NOT_EVALUABLE),
        }
    if product_class == "credit-risk.exposure-rollup":
        measures = payload.get("measures") or {}
        return {
            "limit_regime": payload.get("policy_version", NOT_EVALUABLE),
            "family_entities": (payload.get("family") or {}).get("nodes", NOT_EVALUABLE),
            "gross_committed": (measures.get("gross") or {}).get("committed", NOT_EVALUABLE),
            "adjusted_committed": (measures.get("adjusted") or {}).get("committed", NOT_EVALUABLE),
            "materiality": payload.get("threshold", NOT_EVALUABLE),
            "material_entities": len(payload.get("material") or []),
            "guarantee_paths_deduplicated": (payload.get("guarantee_dedup") or {}).get("cases", NOT_EVALUABLE),
        }
    if product_class == "credit-risk.collateral-coverage":
        coverage = payload.get("coverage") or {}
        return {
            "facility": payload.get("facility", NOT_EVALUABLE),
            "commitment": payload.get("commitment", NOT_EVALUABLE),
            "coverage_ratio": coverage.get("coverage_ratio", NOT_EVALUABLE),
            "collateral_after_haircuts": coverage.get("total", NOT_EVALUABLE),
            "setoff_value": coverage.get("setoff_value", NOT_EVALUABLE),
            "shortfall": coverage.get("shortfall", NOT_EVALUABLE),
            "assets": len(payload.get("assets") or []),
        }
    if product_class == "credit-risk.covenant-cross-reference":
        summary = payload.get("citation_summary") or {}
        return {
            "sources": (payload.get("traversal") or {}).get("sources", NOT_EVALUABLE),
            "chain_nodes": summary.get("chain_nodes", NOT_EVALUABLE),
            "checked_citations": summary.get("checked_citations", NOT_EVALUABLE),
            "explained_absences": summary.get("not_evidenced_total", NOT_EVALUABLE),
            "documents_in_force": (payload.get("governing_text") or {}).get("documents_in_force", NOT_EVALUABLE),
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
                # THE ADDRESS THE MEMO COMPOSED FROM — the admitted child's own
                # content address, so a reader can hold the composition to the
                # acquisition row by row (`CMC-G27`'s positive half).
                "child_content_address": content_hash(contract),
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
