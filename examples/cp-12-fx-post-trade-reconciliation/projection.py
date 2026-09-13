"""Π — the alignment, the partition, the verdict and the decomposition.

[ADAPT] everything here. [MECHANISM] nothing.

Six things this module refuses to do, each because it was measured at Gate 1:

* **Expand to pairwise comparisons.** Three systems give three pairs, and every
  one of the 60 break trades partitions two-against-one — so counting pairs
  reports one divergence twice, exactly `2.00×`. The unit is the TRADE, and the
  payload exposes no countable list of system-pair breaks (TRAP 1).
* **Decompose across a non-zero interval shorter than the tick spacing.** The
  series is 5-minute and the observation gaps are frequently smaller; two
  DIFFERENT instants inside one bucket revalue identically and the timing
  component reads zero. Measured, that misclassifies 22 of 60. It returns
  `not-evaluable` instead (TRAP 2). A gap of exactly zero is excluded from that
  refusal and decomposed: identical instants leave no interval to resolve, so
  the zero is arithmetic rather than an artifact — see `_verdict`.
* **Compare latest state when amendment-0 was asked for.** 13 of 60 breaks are
  material at amendment 0 and immaterial at latest (TRAP 3, TRAP 6).
* **Revalue against a stale tick.** One break's nearest tick is 20 hours old and
  yields a −72.49-pip residual on a raw variance of 7.99 (TRAP 4).
* **Compare rates without pip normalisation.** USD/JPY quotes to 0.01 and the
  rest to 0.0001 (TRAP 5).
* **Invent a class it cannot evidence.** The vocabulary is exactly `timing`,
  `genuine`, `not-evaluable`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import acquisition
from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput
from ccf.projection.plan import Perspective, ProjectionOutput

#: The systems this product reconciles, in a fixed order so a payload is stable.
SYSTEMS: tuple[str, ...] = ("trading", "settlement", "risk")

#: THE CLOSED CLASSIFICATION VOCABULARY (§D.2 step 7), and exactly three.
#:
#: The article names `amendment-lag` and `revaluation-basis`; this estate
#: carries no labels for them, and a class the product cannot evidence is a
#: label it would be inventing (`FXR-G21`).
CLASSIFICATIONS: tuple[str, ...] = ("timing", "genuine", "not-evaluable")

#: What a `verdict` field may hold — the three classifications plus `no-break`.
#:
#: **`no-break` is NOT a fourth class of break.** It is the statement that there
#: is no break to classify: the systems agree inside the materiality threshold,
#: which §D.5 requires be served explicitly as `200` rather than as an omission
#: or an empty payload (`FXR-G15`). Keeping the two tuples apart is what lets
#: `FXR-G21` assert the classification vocabulary is three without `FXR-G15`
#: having to smuggle a fourth into it.
VERDICTS: tuple[str, ...] = (*CLASSIFICATIONS, "no-break")


def _money(value: Decimal, places: str = "0.0001") -> str:
    return str(value.quantize(Decimal(places), rounding=ROUND_HALF_UP))


def _seconds(value: float) -> str:
    """A duration as a canonically encodable string.

    ``timedelta.total_seconds()`` returns a **float**, and the SDK's
    canonicalizer refuses floats outright — they are not bit-stable across
    platforms, and this figure rides the content address. Milliseconds are
    enough: the tick series resolves to 300 s and the offsets are whole
    seconds, so nothing downstream reads past the decimal point.
    """
    return _money(Decimal(str(value)), "0.001")


class FXReconciliationProjection:
    """One verdict per trade, naming the divergent system."""

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
        """The SDK's own set, passed straight through."""
        return self._required

    def invoke(
        self, *, view: GraphView, operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective, temporal_boundary: datetime,
    ) -> ProjectionOutput:
        del operator_outputs
        estate: acquisition.Estate = self._declared["estate"]
        intent = str(self._declared["intent"])
        align = bool(self._declared["align_clocks"])
        threshold = self._threshold(estate, intent)
        in_view = {record.claim.entity_uri for record in view.entities}

        reconciliations = [
            self._reconcile(estate, trade, threshold=threshold, align=align)
            for trade in estate.trades
        ]
        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                "role": perspective.role,
                "asked_at": temporal_boundary.isoformat(),
                "comparison": {
                    # BOTH AXES, CARRIED. The caller's choice is visible in the
                    # answer, so nobody has to infer which question was asked.
                    "compare_at": estate.compare_at,
                    "align_clocks": align,
                    "materiality_pips": _money(threshold),
                    "intent": intent,
                    "tick_spacing_seconds": estate.tick_spacing_seconds,
                    # THE VOCABULARY, SERVED. A consumer reads the closed set
                    # off the answer instead of inferring it from the labels
                    # that happen to appear in this run — and `FXR-G21` reads
                    # it structurally instead of grepping source text, which is
                    # how cp-11's gate 20 went red against correct code.
                    "classification_vocabulary": list(CLASSIFICATIONS),
                },
                # ONE ENTRY PER TRADE. This is the unit, and the count of this
                # list is the count of observations the product makes.
                "reconciliations": reconciliations,
                "observations": len(reconciliations),
                "verdict_counts": self._counts(reconciliations),
                "absent_legs": self._absent_legs(estate),
                "graph": {"entities_in_view": len(in_view)},
            },
        )

    # -- the threshold ---------------------------------------------------

    def _threshold(self, estate: acquisition.Estate, intent: str) -> Decimal:
        override = self._declared.get("materiality_pips")
        if override is not None:
            return Decimal(str(override))
        try:
            return estate.thresholds[intent]
        except KeyError:
            raise KeyError(
                f"no materiality threshold declared for intent {intent!r};"
                " refused rather than defaulted, because a threshold nobody"
                " chose is a policy value invented at serve time"
            ) from None

    # -- one trade, one verdict -------------------------------------------

    def _reconcile(
        self, estate: acquisition.Estate, trade: acquisition.Trade, *,
        threshold: Decimal, align: bool,
    ) -> Mapping[str, Any]:
        pip = estate.pip(trade.pair)
        seen = {
            system: estate.at(trade.trade_id, system)
            for system in SYSTEMS
            if estate.at(trade.trade_id, system) is not None
        }
        values = self._values(seen, align=align)
        groups = self._partition(seen, pip=pip, threshold=threshold)
        divergent = self._divergent(groups)
        verdict, decomposition = self._verdict(
            estate, trade, seen, groups, divergent,
            pip=pip, threshold=threshold, align=align,
        )
        return {
            "trade_id": trade.trade_id,
            "pair": trade.pair,
            # A BAND, carried as a band. Nothing reconstructs a notional.
            "notional_band": trade.notional_band,
            "execution_ts": trade.execution_ts.isoformat(),
            "value_date": str(trade.value_date),
            "verdict": verdict,
            # Named where the partition is two-against-one; NULL where it is
            # three-way, because then no system is the odd one out and picking
            # one would be inventing a culprit.
            "divergent_system": divergent,
            "agreement_groups": [sorted(g) for g in groups],
            "systems": values,
            "decomposition": decomposition,
            # WHAT THE ESTATE DESIGNATED, beside what the product computed —
            # never instead of it. The designation is a sample, not the truth.
            "estate_designated_class": estate.designated.get(trade.trade_id),
        }

    def _values(
        self, seen: Mapping[str, acquisition.Observation], *, align: bool
    ) -> list[Mapping[str, Any]]:
        """Three instants per system, and never conflated (`FXR-G05`).

        `recorded_at` is what the system wrote, `clock_offset_seconds` is the
        correction THIS PRODUCT applies, and `corrected_at` is the result. The
        fabric's own temporal machinery sees only the first.
        """
        rows = []
        for system in SYSTEMS:
            o = seen.get(system)
            if o is None:
                continue
            rows.append({
                "system": system,
                "amendment_seq": o.amendment_seq,
                "value_rate": str(o.value_rate),
                "recorded_at": o.recorded_at.isoformat(),
                "clock_offset_seconds": o.clock_offset_seconds,
                "corrected_at": (
                    o.corrected_at.isoformat() if align else None
                ),
                "compared_at": (
                    o.corrected_at if align else o.recorded_at
                ).isoformat(),
            })
        return rows

    def _partition(
        self, seen: Mapping[str, acquisition.Observation], *,
        pip: Decimal, threshold: Decimal,
    ) -> list[set[str]]:
        """Systems grouped by agreement — the unit, and not the pair.

        Two systems are in one group when their values differ by less than the
        materiality threshold IN PIPS. The groups are the answer; pairwise
        differences are an explanation of them and never a peer.
        """
        groups: list[set[str]] = []
        anchors: list[Decimal] = []
        for system in SYSTEMS:
            o = seen.get(system)
            if o is None:
                continue
            for index, anchor in enumerate(anchors):
                if abs(o.value_rate - anchor) / pip < threshold:
                    groups[index].add(system)
                    break
            else:
                anchors.append(o.value_rate)
                groups.append({system})
        return groups

    def _divergent(self, groups: Sequence[set[str]]) -> str | None:
        """The one system out, where there is one.

        `None` for a clean trade AND for a three-way disagreement — two states
        the payload distinguishes by `verdict`, never by this field alone.
        """
        if len(groups) != 2:
            return None
        singles = [g for g in groups if len(g) == 1]
        return next(iter(singles[0])) if len(singles) == 1 else None

    def _verdict(
        self, estate: acquisition.Estate, trade: acquisition.Trade,
        seen: Mapping[str, acquisition.Observation],
        groups: Sequence[set[str]], divergent: str | None, *,
        pip: Decimal, threshold: Decimal, align: bool,
    ) -> tuple[str, Mapping[str, Any]]:
        if len(groups) <= 1:
            return "no-break", {"state": "no-break"}
        if divergent is None:
            return "not-evaluable", {
                "state": "not-evaluable",
                "reason": "three-way-disagreement",
                "note": (
                    "no system is isolated, so none is the odd one out;"
                    " nominating one would invent a culprit"
                ),
            }
        # The comparison the verdict rests on: the divergent system against ONE
        # member of the agreeing group. One comparison, not three — that is
        # TRAP 1 held to at the level of the arithmetic and not only the count.
        #
        # The peer is chosen by the canonical system order and NOT by set
        # iteration. `next(iter(some_set_of_str))` is not stable across
        # processes — Python salts string hashes per interpreter — so an
        # arbitrary pick would give the same trade different peers, different
        # instants, and a different content address on two runs of the same
        # question. Measured: `TRD-W12-0002` compared against `risk` on one run
        # and `trading` on the next. A `deterministic` determinism class (§D.4)
        # has to be true of the code, not declared of it.
        #
        # Any member is representative of the agreed VALUE — that is what being
        # in one agreement group means — so the choice is free, and a free
        # choice in a replayable product must still be a fixed one.
        agreeing = max(groups, key=len)
        other = min(agreeing, key=SYSTEMS.index)
        a, b = seen[divergent], seen[other]
        total = abs(a.value_rate - b.value_rate) / pip
        ia = a.corrected_at if align else a.recorded_at
        ib = b.corrected_at if align else b.recorded_at
        gap = abs((ia - ib).total_seconds())

        if gap == 0:
            # A ZERO-LENGTH INTERVAL IS NOT AN INTERVAL, and this case is the
            # product's strongest answer rather than an edge of TRAP 2.
            #
            # TRAP 2 refuses a decomposition across an interval the tick series
            # cannot resolve: two DIFFERENT instants inside one 5-minute bucket
            # revalue identically, so a zero timing component is an artifact of
            # the series' resolution. Two IDENTICAL instants are a different
            # fact. There is no interval, no market move to attribute, and the
            # timing component is zero by arithmetic — at no resolution, with no
            # tick series consulted at all, could it be anything else. The whole
            # variance is residual.
            #
            # Measured on this estate: the corrected gap is exactly 0 s on 20 of
            # the 60 break trades, and those 20 are exactly the 20 the estate
            # designates `genuine` — 20 of 20, with no other shape present.
            # Refusing them as `not-evaluable` would throw away the one case the
            # alignment model answers with certainty (§D.3 scenario 2).
            residual = total
            return (
                "genuine" if total >= threshold else "timing",
                {
                    "state": "evaluated",
                    "total_pips": _money(total, "0.01"),
                    "timing_attributable_pips": _money(Decimal(0), "0.01"),
                    "residual_pips": _money(residual, "0.01"),
                    "closes": True,
                    "compared_systems": [divergent, other],
                    "compared_gap_seconds": _seconds(gap),
                    "tick_spacing_seconds": estate.tick_spacing_seconds,
                    "tick_staleness_seconds": None,
                    "note": (
                        "both systems observed at the same true instant, so"
                        " there is no interval to decompose and no tick series"
                        " was consulted; the timing component is zero by"
                        " arithmetic rather than by revaluation"
                    ),
                },
            )

        ta, tb = estate.tick_at(trade.pair, ia), estate.tick_at(trade.pair, ib)
        if ta is None or tb is None:
            return "not-evaluable", self._not_evaluable(
                total, gap, "no-tick-at-or-before",
                "the rate series carries no observation at or before one of the"
                " compared instants, so the market's own move cannot be read",
            )
        stale = max((ia - ta.obs_ts).total_seconds(), (ib - tb.obs_ts).total_seconds())
        if stale > estate.tick_spacing_seconds * 2:
            # TRAP 4. Measured: one break's nearest tick is 20 hours old across
            # the weekend and yields −72.49 pips on a raw variance of 7.99.
            return "not-evaluable", self._not_evaluable(
                total, gap, "stale-tick",
                f"the nearest rate observation is {stale / 3600:.1f} h before the"
                " compared instant; revaluing against it produces a number with"
                " no meaning",
                stale_seconds=_seconds(stale),
            )
        if gap < estate.tick_spacing_seconds:
            # TRAP 2. Two instants inside one 5-minute bucket revalue
            # identically, so the timing component reads zero and the whole
            # variance looks genuine. Measured: 22 of 60 misclassify this way.
            return "not-evaluable", self._not_evaluable(
                total, gap, "interval-below-tick-spacing",
                f"the compared instants are {gap:.0f} s apart and the rate series"
                f" resolves to {estate.tick_spacing_seconds} s; the market's move"
                " between them is not observable, so no timing component can be"
                " attributed and a zero would be a claim rather than a measurement",
            )
        timing = abs(ta.rate - tb.rate) / pip
        residual = total - timing
        verdict = "genuine" if abs(residual) >= threshold else "timing"
        # ROUNDED SO THE THREE SERVED FIGURES ACTUALLY CLOSE.
        #
        # Quantizing all three independently does not close: measured,
        # `TRD-W12-0100` served `12.53 + -5.86` against a total of `6.68`,
        # because each of the three rounded its own way. The residual is by
        # definition the remainder, so it is taken as the remainder of the
        # numbers that are SERVED rather than of the numbers behind them — and
        # `closes` then states an arithmetic fact about the payload instead of
        # about intermediates the consumer cannot see.
        shown_total = _money(total, "0.01")
        shown_timing = _money(timing, "0.01")
        shown_residual = _money(
            Decimal(shown_total) - Decimal(shown_timing), "0.01"
        )
        return verdict, {
            "state": "evaluated",
            "total_pips": shown_total,
            "timing_attributable_pips": shown_timing,
            "residual_pips": shown_residual,
            # CLOSURE, asserted in the payload rather than left to the reader:
            # timing + residual must reconstruct total (`FXR-G09`).
            "closes": (
                Decimal(shown_timing) + Decimal(shown_residual)
                == Decimal(shown_total)
            ),
            "compared_systems": [divergent, other],
            "compared_gap_seconds": _seconds(gap),
            "tick_spacing_seconds": estate.tick_spacing_seconds,
            "tick_staleness_seconds": _seconds(stale),
        }

    def _not_evaluable(
        self, total: Decimal, gap: float, reason: str, note: str, **extra: Any
    ) -> Mapping[str, Any]:
        return {
            "state": "not-evaluable",
            "reason": reason,
            "note": note,
            "total_pips": _money(total, "0.01"),
            # NO timing and NO residual. A `not-evaluable` decomposition that
            # still reported a number would be the defect wearing a label.
            "timing_attributable_pips": None,
            "residual_pips": None,
            "compared_gap_seconds": _seconds(gap),
            **extra,
        }

    # -- summary ----------------------------------------------------------

    def _counts(self, rows: Sequence[Mapping[str, Any]]) -> Mapping[str, int]:
        counted = {name: 0 for name in VERDICTS}
        for row in rows:
            counted[row["verdict"]] += 1
        return counted

    def _absent_legs(self, estate: acquisition.Estate) -> Mapping[str, str]:
        """What this estate does not carry, reported ABSENT rather than empty.

        `settlesVia` and `netsWith` are not present with a count of zero: they
        are absent from the vocabulary. A predicate nothing asserts is not a
        predicate asserting nothing (`FXR-G18`).
        """
        del estate
        return {
            leg: "absent"
            for leg in (
                "settlement_instruction", "settlesVia", "netsWith",
                "iso20022", "settlement_cycle_conventions",
            )
        }


def plan_class() -> type[FXReconciliationProjection]:
    return FXReconciliationProjection
