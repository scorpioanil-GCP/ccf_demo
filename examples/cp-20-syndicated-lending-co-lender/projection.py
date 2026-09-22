"""Π — the role-conditioned view of the syndicate this product serves.

[ADAPT] everything. [MECHANISM] the Protocol members: `required_operators`,
`invoke`, and the `build_with_children` hook through which the ADMITTED child's
contract reaches the plan.

**Everything local is read off the GRAPH VIEW the resolver hands in**; the one
thing that is not is the admitted child's contract, which reaches the plan
through :meth:`CoLenderPlanFactory.build_with_children` after the admission
gate passed it. Those are the two — and only two — provenances a claim in this
payload can have, and every claim says which:

``local-reconstructible``
    assembled from our own stores, through our own operators, at our own
    ledger point. An examiner can rebuild it.
``remote-attested``
    admitted from a Context Product governed under ANOTHER TENANT. We hold the
    peer's answer, its content address and its replay reference — we do not
    hold its operator plan and cannot reconstruct it.

Conflating the two would let an unreconstructible claim inherit the
credibility of a reconstructible one, which is the failure a regulator would
probe. `CLD-G15` is the gate, and the marking is DERIVED from the child
contract's own tenant rather than authored.

**No point estimate is ever derived from a band** (`CLD-G13`). This projection
sums only figures the source stated exactly; a band-precision position
contributes its bounds to the disclosure and nothing at all to an arithmetic.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal

from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput
from ccf.products.composite import ChildContractView
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective, ProjectionOutput

import deployment

#: The three renderings, widest last. `CLD-G19` asserts the CONTAINMENT of
#: these key sets, never their sizes.
PROSPECTIVE = "prospective"
PARTICIPANT = "participant"
AGENT = "agent"

LOCAL = "local-reconstructible"
REMOTE = "remote-attested"


class CoLenderPositionPlan:
    """The syndicate, our position, and whatever the peer was willing to say."""

    def __init__(
        self,
        *,
        plan_id: str,
        required: tuple[str, ...],
        request: ProductRequest,
        children: ChildContractView | None,
        tenant_id: str,
        latency_bound_ms: int,
    ) -> None:
        self._plan_id = plan_id
        self._required = required
        self._request = request
        self._children = children
        self._tenant_id = tenant_id
        self._latency_bound_ms = latency_bound_ms

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        """The set the SDK supplied, returned unchanged."""
        return self._required

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        role = perspective.role
        facility = _one(view, deployment.FACILITY)
        participations = _all(view, deployment.MEMBER_LEI)
        thresholds = _all(view, deployment.CONSENT_PERCENT)
        envelopes = _all(view, deployment.REQUEST_SCOPE)

        members = sorted(
            (
                {
                    "lei": row[deployment.MEMBER_LEI] or None,
                    "label": row.get("member_label") or None,
                    "commitment_usd": _exact(row.get(deployment.COMMITMENT)),
                    "is_own_position": row.get(deployment.IS_OWN) == "true",
                    "provenance": LOCAL,
                }
                for row in participations
            ),
            key=lambda entry: (str(entry["lei"]), str(entry["commitment_usd"])),
        )
        own = next((row for row in members if row["is_own_position"]), None)
        filed = [row for row in members if not row["is_own_position"]]
        filed_total = _sum(row["commitment_usd"] for row in filed)

        federated = self._federated()
        consent = _consent(
            thresholds=thresholds, own=own, federated=federated, filed_total=filed_total
        )

        payload: dict[str, object] = {
            "role": role,
            "facility": {
                "facility_id": facility.get(deployment.FACILITY) if facility else None,
                "borrower_lei": (facility or {}).get("borrower_lei") or None,
                "commitment_amount": _exact((facility or {}).get("commitment_amount")),
                "syndicated": (facility or {}).get("syndicated") == "true",
                "provenance": LOCAL,
            },
            "syndicate": {"member_count": len(filed), "filed_total_usd": _str(filed_total)},
            "consent": consent,
            # WHETHER the boundary was crossed is told to every role: a reader
            # must never have to infer from an absent key that no peer was
            # asked. `include_federated` is part of the question's identity
            # (`CLD-G09`) and so is part of every answer.
            "federation": {
                "include_federated": _asked(self._request),
                "requested_class": deployment.CHILD_CLASS,
                "declared_latency_bound_ms": self._latency_bound_ms,
            },
            "findings": _findings(facility, filed_total),
        }

        if role in {PARTICIPANT, AGENT}:
            payload["syndicate"] = {
                **payload["syndicate"],  # type: ignore[dict-item]
                "members": filed,
            }
            payload["own_position"] = _own_position(participations)
            payload["federated_position"] = federated
            payload["divergence"] = _divergence(filed, federated)

        if role == AGENT:
            payload["envelopes"] = sorted(
                (
                    {
                        "counterparty_lei": row.get(deployment.COUNTERPARTY_LEI) or None,
                        # TWO SETS, parsed back apart. An implementation that
                        # served one for both would admit an out-of-scope ask.
                        "request_scope": _scope(row.get(deployment.REQUEST_SCOPE)),
                        "disclose_scope": _scope(row.get(deployment.DISCLOSE_SCOPE)),
                        "envelope_version": row.get("envelope_version") or None,
                        "valid_from": row.get("valid_from") or None,
                        "provenance": LOCAL,
                    }
                    for row in envelopes
                ),
                key=lambda entry: str(entry["counterparty_lei"]),
            )
            payload["consent_evidence"] = sorted(
                (
                    {
                        "consent_standard": row.get("consent_standard") or None,
                        "consent_percent": _exact(row.get(deployment.CONSENT_PERCENT)),
                        "amendment_type": row.get("amendment_type") or None,
                        "source_passage": row.get("source_passage") or None,
                        "provenance": LOCAL,
                    }
                    for row in thresholds
                ),
                key=lambda entry: str(entry["consent_standard"]),
            )

        return ProjectionOutput(plan_id=self._plan_id, payload=payload)

    def _federated(self) -> dict[str, object] | None:
        """The admitted child's position, marked REMOTE-ATTESTED.

        ``None`` when no child was admitted — because the caller did not ask
        across the boundary. A child the peer REFUSED never reaches here: the
        composite refuses first (`CLD-G07`).
        """
        if not self._children or deployment.CHILD_CLASS not in self._children:
            return None
        contract = self._children[deployment.CHILD_CLASS]
        payload: Mapping[str, object] = contract.payload  # type: ignore[assignment]
        positions = list(payload.get("positions", ()))  # type: ignore[arg-type]
        if not positions:
            return None
        position: Mapping[str, object] = positions[0]  # type: ignore[assignment]
        precision = str(position.get("precision", ""))
        served: dict[str, object] = {
            "counterparty": position.get("counterparty"),
            "precision": precision,
            "declared_ttl_seconds": position.get("declared_ttl_seconds"),
            "declared_latency_ms": position.get("declared_latency_ms"),
            "within_declared_latency_bound": _within(
                position.get("declared_latency_ms"), self._latency_bound_ms
            ),
            # DERIVED, not authored: the child was governed under a tenant that
            # is not ours, so its claims are attested rather than
            # reconstructible. `CLD-G15`.
            "provenance": REMOTE if contract.tenant_id != self._tenant_id else LOCAL,
            "producer_tenant": contract.tenant_id,
            "content_address": contract.content_address
            if hasattr(contract, "content_address")
            else None,
        }
        if precision == "band":
            # NO point estimate. The bounds travel; nothing derived from them
            # reaches an arithmetic anywhere in this payload (`CLD-G13`).
            served["band_low"] = position.get("band_low")
            served["band_high"] = position.get("band_high")
        else:
            served["share_usd"] = position.get("share_usd")
        return served


# ---------------------------------------------------------------------------
# Reading the view, and the arithmetic that is allowed over it.
# ---------------------------------------------------------------------------


def _rows(view: GraphView) -> list[Mapping[str, str]]:
    return [dict(record.claim.attributes) for record in view.entities]


def _all(view: GraphView, key: str) -> list[Mapping[str, str]]:
    return [row for row in _rows(view) if key in row]


def _one(view: GraphView, key: str) -> Mapping[str, str] | None:
    found = _all(view, key)
    return found[0] if found else None


def _exact(raw: object) -> str | None:
    """A source figure as an exact decimal STRING, or ``None`` where absent.

    Never ``0`` for an absent value: an absent commitment and a zero
    commitment are different claims about the world.
    """
    return None if raw is None or raw == "" else str(raw)


def _str(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _sum(values: object) -> Decimal | None:
    """Sum only the figures that are present and exact. ``None`` if none are."""
    found = [Decimal(str(value)) for value in values if value is not None]  # type: ignore[union-attr]
    return sum(found, Decimal(0)) if found else None


def _scope(raw: object) -> list[str]:
    text = "" if raw is None else str(raw)
    return [entry for entry in text.split(deployment.SCOPE_SEPARATOR) if entry]


def _asked(request: ProductRequest) -> bool:
    return str(request.parameters.get(deployment.INCLUDE_FEDERATED)).lower() == "true"


def _within(declared: object, bound_ms: int) -> bool | None:
    """Is the peer's DECLARED latency inside our bound? ``None`` if undeclared.

    A comparison of two declarations. Nothing here measures a wire, and no
    wall-clock timing appears in this payload (`CLD-G12`).
    """
    if declared is None or declared == "":
        return None
    return int(str(declared)) <= bound_ms


def _own_position(participations: list[Mapping[str, str]]) -> dict[str, object] | None:
    row = next(
        (entry for entry in participations if entry.get(deployment.IS_OWN) == "true"),
        None,
    )
    if row is None:
        return None
    return {
        "lei": row.get(deployment.MEMBER_LEI) or None,
        "label": row.get("member_label") or None,
        "commitment_usd": _exact(row.get(deployment.COMMITMENT)),
        "internal_rating": row.get("internal_rating") or None,
        "workout_posture": row.get("workout_posture") or None,
        "provenance": LOCAL,
    }


def _consent(
    *,
    thresholds: list[Mapping[str, str]],
    own: Mapping[str, object] | None,
    federated: Mapping[str, object] | None,
    filed_total: Decimal | None,
) -> dict[str, object]:
    """Is the filed consent standard reachable from the positions we actually know?

    The denominator is the FILED commitment schedule's own total, not the
    facility's `commitment_amount`: Required Lenders is a percentage of
    commitments held by lenders, which is what the schedule enumerates. The
    two disagree on this estate and the disagreement is served as a finding
    rather than resolved silently (`CLD-F-05`).

    **Each member counts once.** Our own position and the peer's are read from
    two different stores, but a member's commitment is one fact; summing the
    booked figure on top of the filed one would double count.
    """
    binding = next(
        (row for row in thresholds if row.get(deployment.CONSENT_PERCENT)), None
    )
    percent = (
        Decimal(binding[deployment.CONSENT_PERCENT]) if binding is not None else None
    )
    known: dict[str, Decimal] = {}
    if own is not None and own.get("commitment_usd") is not None:
        known[str(own["lei"])] = Decimal(str(own["commitment_usd"]))
    if federated is not None and federated.get("share_usd") is not None:
        # Only an EXACT position enters the arithmetic. A band contributes
        # nothing here — `CLD-G13`.
        known[str(federated["counterparty"])] = Decimal(str(federated["share_usd"]))
    held = sum(known.values(), Decimal(0)) if known else None
    coverage = (
        (held / filed_total * Decimal(100)).quantize(Decimal("0.0001"))
        if held is not None and filed_total
        else None
    )
    return {
        "consent_standard": binding.get("consent_standard") if binding else None,
        "consent_percent": _str(percent),
        "source_passage": binding.get("source_passage") if binding else None,
        "known_holders": sorted(known),
        "known_consent_usd": _str(held),
        "denominator_usd": _str(filed_total),
        "denominator_basis": "filed-commitment-schedule",
        "coverage_percent": _str(coverage),
        "reachable": None
        if coverage is None or percent is None
        else coverage >= percent,
    }


def _divergence(
    filed: list[Mapping[str, object]], federated: Mapping[str, object] | None
) -> dict[str, object] | None:
    """Filed commitment against the peer's own declared position.

    **Computed only where BOTH sides are exact** (`CLD-G14`). A band-precision
    position yields no divergence number, and neither does a member the filed
    schedule prices at nothing — an absent figure is not a zero.
    """
    if federated is None or federated.get("share_usd") is None:
        return None
    counterparty = str(federated["counterparty"])
    row = next(
        (entry for entry in filed if str(entry.get("lei")) == counterparty), None
    )
    if row is None or row.get("commitment_usd") is None:
        return None
    filed_amount = Decimal(str(row["commitment_usd"]))
    declared = Decimal(str(federated["share_usd"]))
    return {
        "counterparty": counterparty,
        "filed_commitment_usd": str(filed_amount),
        "peer_declared_usd": str(declared),
        "difference_usd": str(declared - filed_amount),
        "agrees": declared == filed_amount,
    }


def _findings(
    facility: Mapping[str, str] | None, filed_total: Decimal | None
) -> dict[str, object]:
    """What a reader must be told about this estate rather than left to infer."""
    stated = _exact((facility or {}).get("commitment_amount"))
    disagrees = (
        stated is not None
        and filed_total is not None
        and Decimal(stated) != filed_total
    )
    return {
        # BOTH authorities served, and the selection named — cp-21's pattern
        # for two sources that disagree. Neither is silently dropped.
        "commitment_authorities_disagree": disagrees,
        "facility_commitment_amount": stated,
        "filed_schedule_total": _str(filed_total),
        "denominator_selected": "filed-commitment-schedule",
    }
