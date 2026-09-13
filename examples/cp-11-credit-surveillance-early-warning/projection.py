"""Π — the delta, the supersession filter, the composite and the bands.

[ADAPT] everything here. [MECHANISM] nothing.

**The composite warning score is NOT the freshness term, and the two are kept
apart on purpose.** `signal_weight.decay_days` drives the SCORE — how much a
signal still contributes to a judgement about this obligor. The SDK's λ_c drives
`F`, the Context Debt freshness term — how old the evidence behind the answer
is. They share arithmetic and answer different questions, and a product that let
them move together would report a debt figure that rose and fell with its own
finding.

Three things this module refuses to do, each because it was measured:

* **Accumulate a non-decaying class.** `8k_event` carries `decay_days IS NULL`.
  Read as *"contributes forever"*, 30 of 50 obligors breach the board band and
  the control is worthless. What ends an 8-K's relevance is a LATER FILING
  (§C.4 TRAP 1).
* **Read absence as zero.** A class the obligor has no evidence in is reported
  **absent**, never scored (`EWS-G13`). Tupperware has no trend deltas at all;
  that is not a stable balance sheet.
* **Consume an ambiguous name match.** 32 of the estate's 36 WARN matches are
  wrong at score ≈0.71. Only `resolved` contributes, and the withheld count is
  published (`EWS-G14`).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import acquisition
from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput
from ccf.projection.plan import Perspective, ProjectionOutput

#: Every class the product knows, so one the obligor has no evidence in can be
#: reported ABSENT rather than omitted. An omitted class and a zero-scoring
#: class look identical in a payload; only one of them is honest.
SIGNAL_CLASSES: tuple[str, ...] = (
    "8k_event", "adverse_media", "spread_widening", "trend_delta", "warn_notice",
)

#: The chain states, from `acquisition.Estate.chain_state`. Named here so the
#: payload's vocabulary is closed and a fourth value cannot appear silently.
CHAIN_STATES: tuple[str, ...] = ("current", "superseded", "not-participating")


def _renderable(value: Any) -> Any:
    """``value`` with every float rendered as a string, recursively.

    A payload rides the content address, and a float is not bit-stable across
    platforms — the canonicalizer refuses one by name. Rendering rather than
    dropping keeps the source reference readable; dropping it would lose the
    accession or the URL a reader follows.
    """
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, Mapping):
        return {str(k): _renderable(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_renderable(item) for item in value]
    return value


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


class CreditSurveillanceProjection:
    """What changed on this name since the prior observation, and does it matter."""

    def __init__(
        self, *, plan_id: str, required: tuple[str, ...], declared: Mapping[str, Any]
    ) -> None:
        self._plan_id = plan_id
        self._required = required
        self._declared = declared

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        """The SDK's own set, passed straight through.

        This deployment authors no operator set at all — so there is nothing to
        diverge from, and `D-IMPL-86`'s bind-time guard has nothing to refuse.
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
        del operator_outputs
        # THE VIEW IS READ, not ignored. The obligor and every signal reached
        # the graph through L2, so `view.entities` is what makes
        # `execution.touched_entities()` name this obligor — which is what the
        # `D-IMPL-334` gate reads on a later serve (`EWS-G25`). A projection
        # that took everything from the estate and nothing from the view would
        # leave the product depending on an entity the fabric never saw it
        # touch.
        # LOCATED BY ATTRIBUTE, never by a URI this module builds. L2 mints an
        # entity URI from the resolution rule's identity keys — measured, it is
        # `ews_obligor://<hash>` and not the `obligor://<lei>` a deployment
        # might assume. `D-IMPL-316`'s lesson: a constructed identity is not
        # the identity. It matters beyond tidiness here, because the
        # `D-IMPL-334` invalidation boundary is recorded against the URI THE
        # WRITER USED, and a product comparing against a different string would
        # never match one.
        anchor_uris = [
            record.claim.entity_uri
            for record in view.entities
            if record.claim.attributes.get("node_kind") == "obligor"
        ]
        estate: acquisition.Estate = self._declared["estate"]
        intent = str(self._declared["intent"])
        as_of = temporal_boundary.date()

        contributions = self._contributions(estate, as_of=as_of)
        composite = sum(
            (Decimal(c["contribution"]) for c in contributions), Decimal(0)
        )
        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                "role": perspective.role,
                "asked_at": temporal_boundary.isoformat(),
                "obligor": {
                    # Asserted against the VIEW, so the payload cannot name an
                    # obligor the graph never resolved.
                    "in_graph": bool(anchor_uris),
                    "entity_uri": anchor_uris[0] if anchor_uris else None,
                    "lei": estate.obligor.lei,
                    "label": estate.obligor.legal_name,
                    "sic": estate.obligor.sic,
                    # THE DIVISION, which is what the weights key on, and it is
                    # carried so a reader can see which row was used.
                    "sector": estate.obligor.sector,
                },
                "delta": self._delta(estate),
                "composite": self._composite(estate, composite, intent=intent),
                "contributing": contributions,
                "excluded": self._excluded(estate, as_of=as_of),
                "class_coverage": self._coverage(estate),
                "chain_states": self._chain_states(estate),
                "withheld": {
                    "ambiguous_warn_matches": estate.ambiguous_warn_matches,
                    "reason": (
                        "a name match below the resolution bar attributes another"
                        " company's event to this obligor; withheld rather than"
                        " consumed, and counted rather than silently dropped"
                    ),
                },
            },
        )

    # -- the delta -------------------------------------------------------

    def _delta(self, estate: acquisition.Estate) -> Mapping[str, Any]:
        """The window, and where its left edge came from.

        **On VALID TIME, not on ledger `t`** (`CP11-F-06`, §B.3). The ledger
        carries the whole signal population in one bulk load, so a ledger-point
        delta would return everything or nothing.
        """
        return {
            "basis": "valid-time",
            "from": str(estate.window_from),
            "to": str(estate.window_to),
            "anchor": (
                "prior-observation"
                if estate.prior_observation == estate.window_from
                else "requested"
            ),
            "prior_observation": (
                str(estate.prior_observation) if estate.prior_observation else None
            ),
            "signals_in_delta": len(estate.signals),
        }

    # -- the composite ---------------------------------------------------

    def _weight(
        self, estate: acquisition.Estate, signal: acquisition.Signal
    ) -> tuple[Decimal, int | None] | None:
        """The `(weight, decay_days)` row for this signal's class and sector."""
        key = (signal.signal_type, estate.obligor.sector)
        if key in estate.weights:
            return estate.weights[key]
        fallback = (signal.signal_type, "Unclassified")
        return estate.weights.get(fallback)

    def _contributions(
        self, estate: acquisition.Estate, *, as_of: date
    ) -> list[Mapping[str, Any]]:
        """Every signal that reaches the composite, with its whole derivation.

        `EWS-G17`: class, weight, age, decayed contribution and source, per
        signal. A composite that reports only its total cannot be audited.
        """
        rows: list[Mapping[str, Any]] = []
        for signal in estate.signals:
            if not estate.contributes(signal):
                continue
            row = self._weight(estate, signal)
            if row is None:
                continue
            weight, decay_days = row
            age = (as_of - signal.observed_at).days
            # `decay_days is None` is NOT "no contribution" and NOT "decays
            # instantly" — it is a class that does not decay at all. Its
            # retained relevance is 1 until something supersedes it.
            retained = (
                Decimal(1)
                if decay_days is None
                else Decimal(2) ** Decimal(-age / Decimal(decay_days))
            )
            rows.append({
                "signal_id": signal.signal_id,
                "signal_type": signal.signal_type,
                "item": signal.item,
                "observed_at": str(signal.observed_at),
                "age_days": age,
                "severity": _money(signal.severity),
                "weight": _money(weight),
                "decay_days": decay_days,
                "retained": _money(retained),
                "contribution": _money(weight * signal.severity * retained),
                "chain_state": estate.chain_state(signal),
                "provenance": signal.provenance,
                # THE SOURCE REFERENCE, RENDERED — never the raw JSONB.
                # Postgres hands back Python floats inside `source_ref`
                # (`trend_delta` carries `value` and `pct_change`), and a float
                # inside a payload raises `CanonicalizationError: float is not
                # canonically encodable`. It is the same defect cp-09 hit with
                # a float `debt_tolerance`: anything entering a content address
                # must be bit-stable, so numbers cross as strings.
                "source_ref": _renderable(signal.source_ref),
            })
        return rows

    def _composite(
        self, estate: acquisition.Estate, score: Decimal, *, intent: str
    ) -> Mapping[str, Any]:
        """The score, the band it reaches, and every band it did not."""
        bands = sorted(estate.thresholds.items(), key=lambda kv: kv[1])
        reached = [name for name, floor in bands if score >= floor]
        return {
            "score": _money(score),
            "intent": intent,
            "band": reached[-1] if reached else None,
            "escalates": bool(reached),
            # EVERY band and its floor, so a reader can see the distance to the
            # next one rather than only which side of one line this name is on.
            "bands": [
                {"intent": name, "floor": _money(floor), "reached": score >= floor}
                for name, floor in bands
            ],
            # WHAT THE ESTATE DECLARES, beside what this product uses. The
            # difference is a calibration decision (§C.4 TRAP 2) and a payload
            # showing only the value in force would hide that a decision was
            # taken at all.
            "estate_declared": {
                name: _money(floor)
                for name, floor in sorted(estate.estate_thresholds.items())
            },
            "calibration": (
                "illustrative: the estate's bands were calibrated against an"
                " accumulating reading of the non-decaying class that this"
                " product refuses; see CP-SPEC-011 §C.4 TRAP 2"
            ),
        }

    # -- what did NOT contribute, and why --------------------------------

    def _excluded(
        self, estate: acquisition.Estate, *, as_of: date
    ) -> list[Mapping[str, Any]]:
        """Every signal in the delta that did not reach the composite.

        `EWS-G18`, and it is load-bearing: *"why did this name not escalate"* is
        answered by what was left out, not by the total.
        """
        del as_of
        rows: list[Mapping[str, Any]] = []
        for signal in estate.signals:
            state = estate.chain_state(signal)
            if state == "superseded":
                rows.append({
                    "signal_id": signal.signal_id,
                    "signal_type": signal.signal_type,
                    "observed_at": str(signal.observed_at),
                    "reason": "superseded",
                    # ITS AGE IS REPORTED UNCHANGED (`EWS-G08`). It did not
                    # age out; a later filing replaced it, and saying "stale"
                    # would name the wrong mechanism.
                    "note": (
                        "a later filing replaced this one; its relevance ended"
                        " rather than decayed"
                    ),
                })
            elif self._weight(estate, signal) is None:
                rows.append({
                    "signal_id": signal.signal_id,
                    "signal_type": signal.signal_type,
                    "observed_at": str(signal.observed_at),
                    "reason": "no-weight-declared",
                    "note": (
                        "no weight row for this class in any sector; refused"
                        " rather than scored at an invented default"
                    ),
                })
        return rows

    # -- coverage and states ---------------------------------------------

    def _coverage(self, estate: acquisition.Estate) -> list[Mapping[str, Any]]:
        """Per class: present with a count, or **ABSENT**.

        `EWS-G13`. A class the obligor has no evidence in is not a zero. Scoring
        it as one would say *"we looked and found nothing concerning"* when the
        truth is *"we have nothing to look at"*.
        """
        counted = {name: 0 for name in SIGNAL_CLASSES}
        for signal in estate.signals:
            counted[signal.signal_type] = counted.get(signal.signal_type, 0) + 1
        return [
            {
                "signal_class": name,
                "state": "present" if counted.get(name) else "absent",
                "observations": counted.get(name, 0),
            }
            for name in SIGNAL_CLASSES
        ]

    def _chain_states(self, estate: acquisition.Estate) -> Mapping[str, Any]:
        """The three states and their counts — a PARTITION (`EWS-G28`).

        One state per signal, so the counts sum to the signal count. The two raw
        Fluree sets overlap and are deliberately not published: a reader adding
        `chained` and `current` would count every current signal twice.
        """
        counted = {state: 0 for state in CHAIN_STATES}
        for signal in estate.signals:
            counted[estate.chain_state(signal)] += 1
        return {
            "states": counted,
            "total": sum(counted.values()),
            "participating_classes": sorted(estate.supersession_participants),
            "note": (
                "declared, never inferred: a class absent from"
                " `supersession_participants` is never checked, and a signal the"
                " chain does not mirror is `not-participating` rather than"
                " `superseded` — absence is not supersession"
            ),
        }


def plan_class() -> type[CreditSurveillanceProjection]:
    return CreditSurveillanceProjection
