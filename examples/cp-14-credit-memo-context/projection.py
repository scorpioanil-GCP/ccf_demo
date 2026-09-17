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


#: WHAT EACH SECTION PRINTS, AND WHICH MEMBER OF THE CHILD'S OWN PAYLOAD IT IS.
#:
#: One row per printed field: the path into the child's payload and the ONE
#: transformation applied — `value` (the member as served) or `count` (the
#: length of a served list). Nothing is computed from the child's figures:
#: a coverage ratio is the ratio the collateral producer served, and
#: `collateral_after_haircuts` is that producer's `coverage.collateral_value`,
#: NEVER its `coverage.total` (which is collateral plus set-off — the
#: distinction that product exists to preserve; corrected 2026-09-17 after the
#: delivered result mislabeled the total). A member the child legitimately
#: does not carry prints `NOT_EVALUABLE`; a wrong lookup here would print the
#: same word, which is why `tests/examples/test_cp_14_fourth_slice.py` holds
#: every row of this table to the retained child contract independently.
SECTION_FIELDS: Mapping[str, Mapping[str, tuple[tuple[str, ...], str]]] = {
    "credit-risk.spread": {
        "periods": (("periods",), "count"),
        "latest_filed_in_payload": (("latest_filed_in_payload",), "value"),
        "basis_applied": (("basis_applied",), "value"),
    },
    "reference.corporate-family": {
        "depth_served": (("depth_served",), "value"),
        "entities": (("node_count",), "value"),
        "relationships": (("relationship_count",), "value"),
        "resolved": (("resolved_count",), "value"),
        "ownership_circuits": (("findings", "cycles_found"), "value"),
    },
    "credit-risk.exposure-rollup": {
        "limit_regime": (("policy_version",), "value"),
        "family_entities": (("family", "nodes"), "value"),
        "gross_committed": (("measures", "gross", "committed"), "value"),
        "adjusted_committed": (("measures", "adjusted", "committed"), "value"),
        "materiality": (("threshold",), "value"),
        "material_entities": (("material",), "count"),
        "guarantee_paths_deduplicated": (("guarantee_dedup", "cases"), "value"),
    },
    "credit-risk.collateral-coverage": {
        "facility": (("facility",), "value"),
        "commitment": (("commitment",), "value"),
        "coverage_ratio": (("coverage", "coverage_ratio"), "value"),
        "collateral_after_haircuts": (("coverage", "collateral_value"), "value"),
        "setoff_value": (("coverage", "setoff_value"), "value"),
        "total_coverage": (("coverage", "total"), "value"),
        "shortfall": (("coverage", "shortfall"), "value"),
        "assets": (("assets",), "count"),
    },
    "credit-risk.covenant-cross-reference": {
        "sources": (("traversal", "sources"), "value"),
        "chain_nodes": (("citation_summary", "chain_nodes"), "value"),
        "checked_citations": (("citation_summary", "checked_citations"), "value"),
        "explained_absences": (("citation_summary", "not_evidenced_total"), "value"),
        "documents_in_force": (("governing_text", "documents_in_force"), "value"),
    },
}

_ABSENT = object()


def _member(payload: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    """The member at `path`, or `_ABSENT` — never a default the child did not serve."""
    node: Any = payload
    for key in path:
        if not isinstance(node, Mapping) or key not in node:
            return _ABSENT
        node = node[key]
    return node


def _summary(product_class: str, contract: ContextProductContract) -> dict[str, Any]:
    """What the child said, read off ITS payload by the table above — never re-derived.

    A member the child does not carry prints `NOT_EVALUABLE`. A class this
    consumer has no table for lists the child's payload members, so a later
    revision can see what it left unread.
    """
    payload = contract.payload
    fields = SECTION_FIELDS.get(product_class)
    if fields is None:
        return {"payload_members": sorted(str(key) for key in payload)}
    out: dict[str, Any] = {}
    for name, (path, transform) in fields.items():
        member = _member(payload, path)
        if member is _ABSENT:
            out[name] = NOT_EVALUABLE
        elif transform == "count":
            out[name] = len(member) if isinstance(member, (list, tuple)) else NOT_EVALUABLE
        else:
            out[name] = member
    return out


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
