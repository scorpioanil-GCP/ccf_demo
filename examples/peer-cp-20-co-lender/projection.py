"""Π — what the co-lender is willing to say about its own position.

[ADAPT] everything. [MECHANISM] the two Protocol members: `required_operators`
and `invoke`.

**Everything served here is read off the GRAPH VIEW the resolver hands in** —
not off the acquisition result. The two legs' facts became fabric state at L2
and were shaped by the policy envelope at L4; what survives is what a consumer
is told. Reading around the view would serve the position the policy operator
removed, which is the whole control this product turns on.

**A band NEVER becomes a number** (`CLD-G13`, and `Q1`'s recast). Where the
member discloses at ``band`` precision the payload carries ``band_low`` and
``band_high`` and the key ``share_usd`` is **absent** — not null, not zero, not
a midpoint. The absence is the honest shape: a point estimate derived from a
band is a figure nobody disclosed, and serving one would let a downstream sum
treat a policy choice as a measurement.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput
from ccf.projection.plan import Perspective, ProjectionOutput

import deployment

#: The precision literal that forbids a point estimate. The vocabulary document
#: is the authority; this is the name the projection compares against.
BAND = "band"
EXACT = "exact"


class CoLenderPositionProjection:
    """The peer's position at the precision the peer discloses at."""

    def __init__(self, *, plan_id: str, required: tuple[str, ...]) -> None:
        self._plan_id = plan_id
        self._required = required

    @property
    def plan_id(self) -> str:
        """This plan's identity, as the engine pins it into replay."""
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        """The set the SDK supplied, returned unchanged.

        This deployment authors no operator set at all — `D-IMPL-137` row C's
        demand, and the reason `produce.plan_factory` is a NAMED function.
        """
        return self._required

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        """Shape the admitted position into what a co-lender is told."""
        positions = [
            record
            for record in view.entities
            if deployment.FACILITY in record.claim.attributes
        ]
        members = [
            record
            for record in view.entities
            if "lei" in record.claim.attributes
            and deployment.FACILITY not in record.claim.attributes
        ]

        served = [_position(record) for record in positions]
        served.sort(key=lambda entry: str(entry["position_uri"]))

        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                "role": perspective.role,
                "position_count": len(served),
                "positions": served,
                "counterparties": sorted(
                    (
                        {
                            "uri": record.claim.entity_uri,
                            "lei": record.claim.attributes.get("lei"),
                            "label": record.claim.attributes.get("label") or None,
                            "precision": record.claim.attributes.get(
                                deployment.PRECISION
                            ),
                            "provenance": record.claim.attributes.get("provenance")
                            or None,
                        }
                        for record in members
                    ),
                    key=lambda entry: str(entry["uri"]),
                ),
                "relationship_count": len(list(view.relationships)),
            },
        )


def _position(record: object) -> dict[str, object]:
    """One admitted position, at its declared precision and no finer."""
    attributes: Mapping[str, str] = record.claim.attributes  # type: ignore[attr-defined]
    precision = attributes.get(deployment.PRECISION, "")
    served: dict[str, object] = {
        "position_uri": record.claim.entity_uri,  # type: ignore[attr-defined]
        "counterparty": attributes.get(deployment.COUNTERPARTY),
        "facility_id": attributes.get(deployment.FACILITY),
        "precision": precision,
        "as_of": attributes.get(deployment.POSITION_AS_OF),
        "internal_rating": attributes.get("internal_rating") or None,
        "workout_posture": attributes.get("workout_posture") or None,
        "provenance": attributes.get("provenance") or None,
        # The peer's DECLARED terms, served so the consumer compares against a
        # declaration rather than against a measurement it took itself.
        "declared_ttl_seconds": _number(attributes.get(deployment.DECLARED_TTL)),
        "declared_latency_ms": _number(attributes.get(deployment.DECLARED_LATENCY)),
    }
    if precision == BAND:
        # NO `share_usd` KEY AT ALL. Absent rather than null: a null invites a
        # reader to supply a default, and `CLD-G13` forbids any point estimate
        # derived from a band.
        served["band_low"] = _number(attributes.get(deployment.BAND_LOW))
        served["band_high"] = _number(attributes.get(deployment.BAND_HIGH))
    else:
        served["share_usd"] = _number(attributes.get(deployment.SHARE))
    return served


def _number(raw: str | None) -> str | None:
    """A source figure as an exact decimal STRING, or ``None`` where absent.

    A string rather than a float: these are money, and a binary float is not
    the number the source holds. An empty attribute is an absent figure and
    becomes ``None`` — never ``0``.
    """
    return None if raw is None or raw == "" else str(raw)
