"""Π — the packaged memo, read off the view the Policy operator admitted.

[ADAPT] the payload shape. [MECHANISM] the two Protocol members,
`required_operators` and `invoke`.

**Nothing semantic happens here, and that is the point.** The model ran at the
acquisition seam; by the time this executes, the prose is a claim like any
other and this projection assembles it exactly as a projection over ledger
rows would. That ordering is what lets the three validation gates and the
product's own smoothing gate judge the model's output — a projection that
called a model would be producing content nothing downstream could gate.

**Sections this principal may not see never arrive.** The Policy operator
admits on each section's `audience` before the view is built, so an excluded
section is absent from `view.entities` rather than filtered out of a payload
here. Filtering afterwards would mean the section was materialized first, and
a materialized-then-dropped section is a section that existed.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput
from ccf.projection.plan import Perspective, ProjectionOutput

__all__ = ["PackagedMemoProjection", "plan_class"]

#: The entity class a packaged section occupies in the view.
SECTION = "memo_section"

#: The entity class the memo node occupies.
MEMO = "packaged_memo"


class PackagedMemoProjection:
    """The banker-facing memo, and the substrate identity that backs it."""

    def __init__(
        self,
        *,
        plan_id: str,
        required: tuple[str, ...],
        anchor: str,
    ) -> None:
        self._plan_id = plan_id
        # The SDK-supplied operator set, held exactly as handed in. This
        # projection authors no operator set of its own (`D-IMPL-141`).
        self._required = required
        self._anchor = anchor

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
        sections = sorted(
            (dict(record.claim.attributes) for record in view.entities),
            key=lambda section: str(section.get("heading", "")),
        )
        if not sections:
            # No section survived admission. Reported as absent rather than
            # served empty: an empty memo reads as "nothing to report", which
            # is a claim this product did not make. The gate refuses it.
            return ProjectionOutput(
                plan_id=self._plan_id,
                payload={"facility_id": self._anchor, "sections": []},
            )

        # THE IDENTITY IS READ OFF THE SECTIONS, not off a separate node.
        # Every section carries the same packaging identity and the same
        # substrate address, which is what makes a section self-describing
        # when it travels alone.
        first = sections[0]
        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                "facility_id": first.get("facility_id") or self._anchor,
                # THE SUBSTRATE, NAMED ON THE PRODUCT ITSELF. A reader holding
                # this memo can fetch the exact product it renders and check
                # any sentence against it — which is what makes the packaged
                # form a derivative VIEW rather than a replacement.
                "packaged_from": {
                    "content_address": first.get("derived_from"),
                    "expires_at": first.get("upstream_expires_at") or None,
                    "debt": first.get("upstream_debt") or None,
                    "disposition": first.get("upstream_disposition") or None,
                },
                # §7.10.4's four pinned rendering primitives, on the payload as
                # well as on dimension 3 — a reader of the memo should not have
                # to fetch a replay record to learn what wrote it.
                "packaged_by": {
                    "model": first.get("packaging_model"),
                    "temperature": first.get("packaging_temperature"),
                    "prompt_artifact_uri": first.get("packaging_prompt_uri"),
                    "prompt_artifact_hash": first.get("packaging_prompt_hash"),
                },
                "sections": [
                    {
                        "heading": section.get("heading"),
                        "audience": section.get("audience"),
                        "prose": section.get("prose"),
                        "derived_from": section.get("derived_from"),
                        "figures_cited": _figures(section.get("figures_cited")),
                    }
                    for section in sections
                ],
            },
        )


def _figures(raw: object) -> tuple[str, ...]:
    """The declared citations, parsed back into a set of values.

    Claim attributes are flat strings, so the list is carried under one
    separator and parsed back here — never merged into a single blob, because
    the smoothing gate checks membership and a blob has no members.
    """
    if not raw:
        return ()
    return tuple(part for part in str(raw).split("|") if part)


def plan_class() -> type[PackagedMemoProjection]:
    """The projection class, by name, for the paved road's plan factory."""
    return PackagedMemoProjection
