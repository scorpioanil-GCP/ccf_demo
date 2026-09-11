"""`Π` for cp-08: the two-axis cut, and the exclusion record that explains it.

**THIS IS WHERE THE PRODUCT'S SUBJECT LIVES.** `as_of` bounded the read;
`known_as_of` is applied HERE, over admitted state, because the assertion-time
cut is a governed selection rather than a filter on a fetch — and because the
exclusion record cannot be written anywhere else. A deployment that dropped
un-booked amendments during acquisition would have nothing left to explain.

**THE TWO AXES ARE NAMED SEPARATELY IN THE OUTPUT, and that is the point.** An
amendment absent because it was not yet in force and an amendment absent
because the bank had not yet learned of it are different facts. A consumer that
cannot tell them apart has the single-timeline problem back in a new place, one
layer up.

**NO SUPERSESSION LOGIC.** The estate carries none (`D-IMPL-329`), so there is
none to implement. Covenants are served as context and labelled **unversioned**
(`CIF-G12`): this estate puts no assertion time on a covenant, so the terms a
facility bore on a past date are not recoverable and the payload says so rather
than letting a reader assume they were reconstructed.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

import yaml

from pathlib import Path

from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput
from ccf.projection.plan import Perspective, ProjectionOutput

HERE = Path(__file__).parent

#: The two axes, as the payload names them. Declared once so the gate and the
#: payload cannot drift apart.
AXIS_VALID_TIME = "valid-time"
AXIS_ASSERTION_TIME = "assertion-time"
AXIS_UNPLACEABLE = "unplaceable-on-assertion-axis"


def declaration() -> Mapping[str, Any]:
    """`Π`'s own declared values, from its artifact."""
    return yaml.safe_load(
        (HERE / "artifacts" / "projection.yaml").read_text(encoding="utf-8")
    )["declaration"]


class CovenantInForceProjection:
    """Which amendments bound the facility, and which of them were known."""

    def __init__(self, *, plan_id: str, required: tuple[str, ...],
                 declared: Mapping[str, Any], as_of: str,
                 known_as_of: str) -> None:
        self._plan_id = plan_id
        # The SDK-supplied operator set, held exactly as handed in. This
        # projection authors no operator set of its own.
        self._required = required
        self._declared = declared
        # BOTH INSTANTS AS GOVERNANCE RESOLVED THEM — the class's relative
        # defaults when the caller omitted them, the caller's values when
        # supplied. `GovernedResolver` hands the plan factory the EFFECTIVE
        # request, never the caller's raw parameters.
        self._as_of = as_of
        self._known_as_of = known_as_of

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        """The set the SDK supplied, returned unchanged."""
        return self._required

    def invoke(
        self, *, view: GraphView, operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective, temporal_boundary: datetime,
    ) -> ProjectionOutput:
        kind_of = lambda r: r.claim.attributes.get("kind")
        amendments = [r for r in view.entities if kind_of(r) == "amendment"]
        covenants = [r for r in view.entities if kind_of(r) == "covenant"]

        admitted: list[dict[str, Any]] = []
        excluded: list[dict[str, Any]] = []

        for record in sorted(amendments, key=lambda r: r.claim.entity_uri):
            attrs = record.claim.attributes
            amendment_id = attrs.get("amendment_id", "")
            valid_from = attrs.get("valid_from") or ""
            asserted_at = attrs.get("asserted_at") or ""
            entry = {
                "amendment_id": amendment_id,
                "amendment_number": attrs.get("amendment_number") or None,
                "valid_from": valid_from or None,
                "asserted_at": asserted_at or None,
                "booking_lag_days": attrs.get("booking_lag_days") or None,
            }

            # AXIS 1 — VALID TIME. Was it in force at `as_of`?
            if not valid_from or valid_from > self._as_of:
                excluded.append({**entry, "excluded_by": AXIS_VALID_TIME,
                                 "because": "not yet in force at as_of"})
                continue

            # AXIS 2 — ASSERTION TIME. Had the institution booked it by
            # `known_as_of`? An amendment with NO assertion time is not assumed
            # booked: 112 of 137 carry none, and defaulting would make every
            # booking lag vanish (`CP08-F-03`).
            if not asserted_at:
                excluded.append({
                    **entry, "excluded_by": AXIS_UNPLACEABLE,
                    "because": "the source carries no assertion time for this"
                               " amendment, so whether it was known cannot be"
                               " established either way",
                })
                continue
            if asserted_at > self._known_as_of:
                excluded.append({**entry, "excluded_by": AXIS_ASSERTION_TIME,
                                 "because": "in force, but not yet booked at"
                                            " known_as_of"})
                continue

            admitted.append(entry)

        payload = {
            # The two instants the answer was cut at, carried in the payload so
            # a reader never has to infer which question was asked.
            "window": {"as_of": self._as_of, "known_as_of": self._known_as_of},
            "amendments_in_force_and_known": admitted,
            # EVERY omission, with WHICH AXIS removed it. Not a log line.
            "amendments_excluded": excluded,
            "covenants": [
                {
                    "covenant_id": r.claim.attributes.get("covenant_id"),
                    "covenant_type": r.claim.attributes.get("covenant_type") or None,
                    "threshold": r.claim.attributes.get("threshold") or None,
                    "threshold_unit": r.claim.attributes.get("threshold_unit") or None,
                }
                for r in sorted(covenants, key=lambda r: r.claim.entity_uri)
            ],
            # `CIF-G12`. A PAYLOAD FIELD, not prose in a README: serving current
            # terms beside a historical amendment answer is the one place a
            # consumer could mistake this for a product that reconstructs
            # covenant state, and this estate cannot (`CP08-F-04`).
            "covenant_terms_are_unversioned": True,
            "covenant_terms_note": self._declared["unversioned_note"],
        }
        return ProjectionOutput(payload=payload, plan_id=self._plan_id)


def plan_class() -> type[CovenantInForceProjection]:
    """The plan type, for a test that asks the tree rather than a roster."""
    return CovenantInForceProjection
