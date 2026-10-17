# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Π — the facility collateral brief, read off the graph view AND the admitted child.

[ADAPT] everything. [MECHANISM] the two Protocol members (`required_operators`
and `invoke`). Π is deployment code by construction (whitepaper §7.5).

**Two inputs, kept apart.** The obligor's identity is read off the GRAPH VIEW —
the parent's own leg. The collateral section is read off the ADMITTED CHILD'S
CONTRACT, handed in through ``build_with_children`` (`D-IMPL-339`), and never off
a store. Which members of the CHILD's payload are printed is declared in
``artifacts/projection.yaml``; nothing is computed from the child's figures.
The obligor block names its three attribute keys directly — the same names
``ccf_config.yaml``'s ``resolution`` declares (FINDINGS.md §E) — and prints the
declared ``not_evaluable`` word for an attribute the fabric does not carry (a
null in the estate is omitted, `D-IMPL-357` B4).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from ccf.contracts.canonical import content_hash
from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput
from ccf.products.contract import ContextProductContract
from ccf.projection.plan import Perspective, ProjectionOutput

HERE = Path(__file__).parent


def declared() -> Mapping[str, Any]:
    """Π's declared values (``artifacts/projection.yaml``)."""
    document: Mapping[str, Any] = yaml.safe_load((HERE / "artifacts" / "projection.yaml").read_text(encoding="utf-8"))
    return document["declaration"]


_ABSENT = object()


def _member(payload: Mapping[str, Any], path: list[str]) -> Any:
    """The member at ``path``, or ``_ABSENT`` — never a default the child did not serve."""
    node: Any = payload
    for key in path:
        if not isinstance(node, Mapping) or key not in node:
            return _ABSENT
        node = node[key]
    return node


class FacilityCollateralBriefProjection:
    """The brief: the obligor, the facility, and the admitted child's own figures."""

    def __init__(
        self,
        *,
        plan_id: str,
        required: tuple[str, ...],
        facility_id: str,
        children: Mapping[str, ContextProductContract] | None,
    ) -> None:
        self._plan_id = plan_id
        self._required = required
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
        values = declared()
        obligor: dict[str, Any] | None = None
        for record in view.entities:
            if record.claim.entity_class == values["obligor_class"]:
                attributes = record.claim.attributes
                obligor = {
                    key: attributes.get(key, values["not_evaluable"])
                    for key in ("lei", "legal_name", "legal_jurisdiction")
                }
                break
        sections: dict[str, Any] = {}
        for product_class in sorted(self._children or {}):
            contract = self._children[product_class]  # type: ignore[index]
            summary: dict[str, Any] = {}
            for name, path in values["child_fields"].items():
                member = _member(contract.payload, list(path))
                summary[name] = values["not_evaluable"] if member is _ABSENT else member
            sections[product_class] = {
                # The admitted child's own content address, so a reader can hold
                # the brief to the child row of the decision record.
                "child_content_address": content_hash(contract),
                "child_schema_version": contract.schema_version,
                "child_tenant": contract.tenant_id,
                "child_expires_at": contract.expires_at.isoformat(),
                "summary": summary,
            }
        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                "obligor": obligor,
                "facility": self._facility_id,
                "child_asked_at": temporal_boundary.isoformat(),
                "sections": sections,
            },
        )
