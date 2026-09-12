"""Π — three signals, three clocks, and the disagreement between them.

[ADAPT] everything here. [MECHANISM] nothing.

Reads the graph view and nothing else. Opens no store and reads no clock:
`temporal_boundary` is the decision instant the SDK hands it, and every age and
lag below is measured against that.

## The three rules this module exists to hold

**1. THE INSTRUMENT IS THE PRIMARY OBSERVATION UNIT** (`CP-SPEC-010` §D.3,
`CP10-F-06`). A bond is what trades and what carries a spread. Episodes are
detected **per bond against that bond's own median**, and instruments are
**never averaged before detection**. Measured on this estate: averaging
Celanese's two bonds halves its peak from 233.2 bp to 131.1 and its multiple
from 8.0× to 4.5×, and erases that the concern is entirely at the short end.

**2. THE THREE SPREAD COMPONENTS ARE NEVER PRE-SUMMED** (`RSM-G07`). Only
`idiosyncratic_bp` is evidence about this obligor; `market_oas_bp` is what the
whole rating band is paying, and a widening there is a market move rather than
a deterioration.

**3. THE GRADE COMPARISON STAYS AT OBLIGOR LEVEL, and the asymmetry is
deliberate.** A grade assesses an *obligor*; a spread prices a *bond*. This
module does not invent a per-bond grade to make the units match, and it does
not derive a market band from the grade — a residual computed from a
grade-derived band could not disagree with the grade, which is the product's
whole subject (`RSM-G23`).
"""

from __future__ import annotations

import json
import statistics
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from ccf.graph.protocols import GraphView
from ccf.operators.base import OperatorOutput
from ccf.projection.plan import Perspective, ProjectionOutput

OBLIGOR_ID = "obligor_id"
NODE_KIND = "node_kind"
LABEL = "label"
PAYLOAD = "payload_json"

#: The basis the market leg is netted on. Named on every spread figure; see
#: `CP10-F-04` for why it cannot be improved without contaminating the signal.
STATIC_ISSUE_BAND = "static_issue_band"

#: The cycle triggers. Anything else is off-cycle — read off the trigger TEXT,
#: never inferred from spacing, because a review that merely falls near a peak
#: is not an off-cycle review (`TRAP 2`).
ON_CYCLE = frozenset({"quarterly review", "initial rating (window start)"})

#: WHAT EACH COMPONENT ACTUALLY IS, carried on every spread series (`RSM-G18`).
#: The vault's §C assumed FINRA TRACE for this leg; measured, the estate holds
#: none — instrument identifiers are `syn-i-*` and the issuer-specific figure is
#: a RESIDUAL, not an observed trade. A product that let a reader believe
#: otherwise would be misrepresenting its own evidence (`CP10-F-01`).
COMPONENT_PROVENANCE: Mapping[str, str] = {
    "benchmark_bp": "public — Treasury.gov / FRED",
    "market_oas_bp": "public — ICE BofA option-adjusted spread series on FRED",
    "idiosyncratic_bp": (
        "synthetic — engineered; the residual after the two public components"
        " on a static_issue_band basis. NOT an observed trade price."
    ),
}


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def _money(value: Decimal) -> str:
    """A figure as a STRING, never a float — the content address depends on it."""
    return format(value.quantize(Decimal("0.001")), "f")


class RatingSpreadMigrationProjection:
    """The migration as three series, plus the episodes where they disagree."""

    def __init__(
        self, *, plan_id: str, required: tuple[str, ...],
        declared: Mapping[str, Any],
    ) -> None:
        self._plan_id = plan_id
        # The SDK-supplied operator set, held exactly as handed in. This
        # projection authors no operator set and has none to author.
        self._required = required
        self._declared = declared

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        return self._required

    def invoke(
        self, *, view: GraphView, operator_outputs: Mapping[str, OperatorOutput],
        perspective: Perspective, temporal_boundary: datetime,
    ) -> ProjectionOutput:
        by_kind: dict[str, list[Mapping[str, Any]]] = {}
        for record in view.entities:
            attributes = record.claim.attributes
            kind = attributes.get(NODE_KIND)
            if not kind:
                continue
            by_kind.setdefault(kind, []).append(
                {"uri": record.claim.entity_uri,
                 "label": attributes.get(LABEL),
                 **json.loads(attributes.get(PAYLOAD) or "{}")}
            )

        obligor = (by_kind.get("obligor") or [{}])[0]
        instruments = sorted(
            by_kind.get("instrument", []), key=lambda e: str(e.get("instrument_id"))
        )
        spreads = by_kind.get("spread", [])
        grades = sorted(
            by_kind.get("grade", []), key=lambda e: str(e.get("valid_from"))
        )

        multiple = _d(self._declared.get("divergence_multiple", 2))
        granularity = str(self._declared.get("granularity", "weekly"))

        per_bond = self._per_bond(instruments, spreads)
        episodes = self._episodes(per_bond, grades, multiple=multiple)

        return ProjectionOutput(
            plan_id=self._plan_id,
            payload={
                "role": perspective.role,
                "asked_at": temporal_boundary.isoformat(),
                "obligor": {
                    "lei": obligor.get("lei"),
                    "label": obligor.get("label"),
                },
                "benchmark_basis": STATIC_ISSUE_BAND,
                "spread_series": [
                    self._series(bond, granularity=granularity)
                    for bond in per_bond
                ],
                # A DERIVED SUMMARY, and it never travels alone (`RSM-G24`).
                "obligor_spread_summary": self._summary(per_bond),
                "grade_series": self._grades(grades),
                "episodes": episodes,
                "series_register": self._register(per_bond, grades, granularity),
                "band_migration": self._band_migration(instruments, grades),
            },
        )

    # -- the unit ---------------------------------------------------------

    def _per_bond(
        self, instruments: Sequence[Mapping[str, Any]],
        spreads: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        """One entry per bond, with its own series. **Nothing is averaged here.**"""
        points: dict[str, list[Mapping[str, Any]]] = {}
        for point in spreads:
            points.setdefault(str(point.get("instrument_id")), []).append(point)
        bonds = []
        for instrument in instruments:
            iid = str(instrument.get("instrument_id"))
            series = sorted(points.get(iid, []), key=lambda p: str(p.get("obs_date")))
            if not series:
                continue
            idio = [_d(p["idiosyncratic_bp"]) for p in series]
            bonds.append(
                {
                    "instrument_id": iid,
                    "issue_band": instrument.get("issue_band"),
                    "tenor_years": instrument.get("tenor_years"),
                    "maturity": instrument.get("maturity"),
                    "series": series,
                    "median": statistics.median(idio),
                    "peak": max(idio),
                    "peak_date": max(series, key=lambda p: _d(p["idiosyncratic_bp"]))["obs_date"],
                }
            )
        return bonds

    def _series(self, bond: Mapping[str, Any], *, granularity: str) -> Mapping[str, Any]:
        """One bond's three-component series, resampled and never pre-summed."""
        sampled = _resample(bond["series"], granularity)
        return {
            "instrument_id": bond["instrument_id"],
            "issue_band": bond["issue_band"],
            "tenor_years": bond["tenor_years"],
            "benchmark_basis": STATIC_ISSUE_BAND,
            "native_cadence": "daily",
            "resampled_cadence": granularity,
            "observations": len(bond["series"]),
            "median_idiosyncratic_bp": _money(bond["median"]),
            # WHAT EACH NUMBER IS, beside the numbers (`RSM-G18`).
            "component_provenance": dict(COMPONENT_PROVENANCE),
            "points": [
                {
                    "obs_date": str(p["obs_date"]),
                    # THREE COMPONENTS, SEPARATELY. Summing them here would
                    # destroy the product's subject (`RSM-G07`).
                    "benchmark_bp": _money(_d(p["benchmark_bp"])),
                    "market_oas_bp": _money(_d(p["market_oas_bp"])),
                    "idiosyncratic_bp": _money(_d(p["idiosyncratic_bp"])),
                }
                for p in sampled
            ],
        }

    def _summary(self, bonds: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
        """The obligor-level figure — **with its dispersion, always** (`RSM-G24`).

        Served as a convenience and labeled as one. Where an obligor has more
        than one instrument the per-bond values it was computed from ride
        beside it, so a reader can see whether the summary describes a bond or
        no bond at all. Measured on this estate: 5,267 (obligor, date) pairs
        carry one bond at more than twice the other.
        """
        if not bonds:
            return None
        medians = [b["median"] for b in bonds]
        blended = sum(medians, Decimal(0)) / Decimal(len(medians))
        return {
            "kind": "derived-summary",
            "basis": "mean of per-bond medians",
            "blended_median_idiosyncratic_bp": _money(blended),
            "instrument_count": len(bonds),
            # THE DISPERSION. Without it the summary reads as an observation.
            "dispersion": {
                "per_bond_median_bp": {
                    str(b["instrument_id"]): _money(b["median"]) for b in bonds
                },
                "per_bond_peak_bp": {
                    str(b["instrument_id"]): _money(b["peak"]) for b in bonds
                },
                "max_over_min_peak": (
                    _money(max(b["peak"] for b in bonds) / min(b["peak"] for b in bonds))
                    if len(bonds) > 1 and min(b["peak"] for b in bonds) > 0 else None
                ),
            },
            "caution": (
                "a mean over instruments that may be pricing different things;"
                " episodes are detected per bond and never on this figure"
            ),
        }

    # -- the disagreement -------------------------------------------------

    def _episodes(
        self, bonds: Sequence[Mapping[str, Any]],
        grades: Sequence[Mapping[str, Any]], *, multiple: Decimal,
    ) -> list[Mapping[str, Any]]:
        """Every bond whose peak reached `multiple` × its own median.

        The grade compared is the **obligor's**, in force on the peak date —
        not the current grade, and not a per-bond grade this product would have
        had to invent (`RSM-G10`).
        """
        found = []
        for bond in bonds:
            if bond["median"] <= 0 or bond["peak"] < multiple * bond["median"]:
                continue
            peak_date = date.fromisoformat(str(bond["peak_date"]))
            in_force = _in_force(grades, peak_date)
            found.append(
                {
                    "instrument_id": bond["instrument_id"],
                    "tenor_years": bond["tenor_years"],
                    "peak_idiosyncratic_bp": _money(bond["peak"]),
                    "own_median_bp": _money(bond["median"]),
                    "multiple_of_own_median": _money(bond["peak"] / bond["median"]),
                    "peak_date": str(peak_date),
                    "benchmark_basis": STATIC_ISSUE_BAND,
                    "grade_in_force_at_peak": (
                        in_force.get("grade") if in_force else None
                    ),
                    "grade_evaluable": in_force is not None,
                    "confirmation": _confirmation(grades, peak_date, in_force),
                }
            )
        return sorted(found, key=lambda e: str(e["instrument_id"]))

    def _grades(self, grades: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
        """The grade series, on BOTH clocks, with the supersession chain."""
        return [
            {
                "grade": g.get("grade"),
                "valid_from": g.get("valid_from"),
                "valid_to": g.get("valid_to"),
                "asserted_at": g.get("asserted_at"),
                "booking_lag_days": _lag(g),
                "trigger": g.get("trigger"),
                "off_cycle": str(g.get("trigger")) not in ON_CYCLE,
                "superseded_by": g.get("superseded_by"),
                "scale_version": g.get("scale_version"),
                "provenance": "synthetic — internal",
            }
            for g in grades
        ]

    def _register(
        self, bonds: Sequence[Mapping[str, Any]],
        grades: Sequence[Mapping[str, Any]], granularity: str,
    ) -> list[Mapping[str, Any]]:
        """Every series with its OWN cadence and window (`RSM-G14`).

        A single product-level freshness figure over a daily spread and a
        quarterly grade would be actively misleading — the spread between them
        is ninety-fold.
        """
        rows: list[Mapping[str, Any]] = []
        for bond in bonds:
            series = bond["series"]
            rows.append(
                {
                    "series": f"idiosyncratic_spread:{bond['instrument_id']}",
                    "unit": "instrument",
                    "native_cadence": "daily",
                    "resampled_cadence": granularity,
                    "window_from": str(series[0]["obs_date"]),
                    "window_to": str(series[-1]["obs_date"]),
                    "observations": len(series),
                }
            )
        if grades:
            rows.append(
                {
                    "series": "internal_grade",
                    "unit": "obligor",
                    "native_cadence": "quarterly-with-off-cycle",
                    "resampled_cadence": "none — a grade is a step function",
                    "window_from": str(grades[0].get("valid_from")),
                    "window_to": str(grades[-1].get("valid_from")),
                    "observations": len(grades),
                }
            )
        return rows

    def _band_migration(
        self, instruments: Sequence[Mapping[str, Any]],
        grades: Sequence[Mapping[str, Any]],
    ) -> Mapping[str, Any]:
        """Whether the obligor has left the band its bonds were issued into.

        **Reported, never corrected** (`CP10-F-04`, `RSM-G23`). Deriving a
        replacement band from the internal grade would make the market leg a
        function of the grade the divergence is measured against, and a
        residual computed that way could not disagree with the grade.
        """
        issue_bands = sorted({str(i.get("issue_band")) for i in instruments})
        current = grades[-1] if grades else None
        current_band = current.get("band") if current else None
        migrated = bool(current_band) and current_band not in issue_bands
        return {
            "basis": STATIC_ISSUE_BAND,
            "issue_bands": issue_bands,
            "current_grade_band": current_band,
            "has_migrated_out_of_issue_band": migrated,
            "effect_on_residual": (
                "the market component is netted on the issue band, so the"
                " residual is less precise for this obligor and its direction"
                " of error is knowable from which band is wider"
                if migrated else "none — the obligor is still in its issue band"
            ),
            "note": (
                "no band is inferred from the internal grade; see CP10-F-04"
            ),
        }


def _resample(
    series: Sequence[Mapping[str, Any]], granularity: str
) -> list[Mapping[str, Any]]:
    """Take the LAST observation in each bucket. **Never interpolate.**

    Interpolation would invent observations that were never made, and across a
    grade change it would invent intermediate grades that never existed
    (`RSM-G12`). Taking a real observation per bucket keeps every point in the
    output a point that actually occurred.
    """
    if granularity == "daily":
        return list(series)
    width = {"weekly": 7, "monthly": 30}.get(granularity)
    if width is None:
        return list(series)
    buckets: dict[int, Mapping[str, Any]] = {}
    for point in series:
        key = date.fromisoformat(str(point["obs_date"])).toordinal() // width
        buckets[key] = point          # last in bucket wins; all are real
    return [buckets[k] for k in sorted(buckets)]


def _in_force(
    grades: Sequence[Mapping[str, Any]], at: date
) -> Mapping[str, Any] | None:
    """The grade in force on `at`, or `None` when the obligor is not rated."""
    standing = None
    for grade in grades:
        if date.fromisoformat(str(grade.get("valid_from"))) <= at:
            standing = grade
    return standing


def _lag(grade: Mapping[str, Any]) -> int | None:
    valid_from, asserted = grade.get("valid_from"), grade.get("asserted_at")
    if not valid_from or not asserted:
        return None
    return (date.fromisoformat(str(asserted)) - date.fromisoformat(str(valid_from))).days


def _confirmation(
    grades: Sequence[Mapping[str, Any]], peak_date: date,
    in_force: Mapping[str, Any] | None,
) -> Mapping[str, Any] | None:
    """The first grade change AFTER the peak — with all three tests separate.

    **A confirmation is later, a downgrade, AND off-cycle** (`RSM-G11`). Each is
    reported on its own, because temporal proximity alone is not confirmation:
    quarterly reviews land every ~90 days, so some review is near any date.
    Measured on this estate, fifteen bond-level episodes have five nearby
    changes and exactly ONE that is both a downgrade and off-cycle.
    """
    if in_force is None:
        # NOT RATED AT THE PEAK. A distinct state from "rated and never moved",
        # and the two are reported separately rather than both as an absence
        # (found at Gate 2 — `CP10-F-08`).
        return {
            "outcome": "not-evaluable",
            "confirms": False,
            "why": "the obligor carried no grade in force on the peak date",
        }
    was = str(in_force.get("grade"))
    was_notch = in_force.get("notch")
    for grade in grades:
        when = date.fromisoformat(str(grade.get("valid_from")))
        if when <= peak_date or str(grade.get("grade")) == was:
            continue
        notch = grade.get("notch")
        downgrade = (
            None if notch is None or was_notch is None else int(notch) > int(was_notch)
        )
        off_cycle = str(grade.get("trigger")) not in ON_CYCLE
        return {
            "outcome": "changed",
            "from_grade": was,
            "to_grade": grade.get("grade"),
            "effective": str(when),
            "lag_days": (when - peak_date).days,
            # THREE TESTS, EACH REPORTED ON ITS OWN (`RSM-G11`). A reader can
            # see which one failed; `confirms` alone would not say.
            "is_later": True,
            "is_downgrade": downgrade,
            "is_off_cycle": off_cycle,
            "trigger": grade.get("trigger"),
            "confirms": bool(downgrade) and off_cycle,
        }
    # THE STANDING DISAGREEMENT. The obligor was rated throughout and the
    # grade NEVER MOVED after the peak — which is `CP-SPEC-010` §D.4
    # scenario 2, a finding in its own right rather than missing data. An
    # earlier revision returned `None` here, identical to "not rated", and the
    # product could not express the scenario it declares (`CP10-F-08`).
    return {
        "outcome": "unchanged",
        "confirms": False,
        "grade_in_force_throughout": was,
        "reviews_after_peak": sum(
            1 for g in grades
            if date.fromisoformat(str(g.get("valid_from"))) > peak_date
        ),
        "why": (
            "the obligor was rated at the peak and the grade did not change"
            " afterward — two assessments that never reconciled, not an"
            " absence of evidence"
        ),
    }


def plan_class() -> type[RatingSpreadMigrationProjection]:
    return RatingSpreadMigrationProjection
