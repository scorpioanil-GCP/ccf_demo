"""`D-IMPL-333` — freshness over a series is a property of its leading edge.

**The gap, measured before this existed.** `decay` says how fast an observation
ages and `decay_basis` says against which instant. Neither says **which
observations constitute the thing being scored**, and the reference scorer read
that as *every entity record in the view* — correct for a point-in-time
product, wrong in both available directions for any product that deliberately
carries history:

    two years of daily observations, λ_c one day, `curve`     ->  F = 0.007164
    the same rows under `supersede-only`                      ->  F = 1.000000

The first measures the archive's LENGTH. The second reports perfect freshness
however cold the leading edge went, because `supersede-only` changes each
observation's VALUE and never the SET that is averaged. Dave's framing, which is
the whole ruling: **age makes a current observation stale; age does not make
historical evidence stale.**
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.artifacts import HalfLifeEntry, HalfLifeTable
from ccf.halflife.debt import FreshnessScorer
from ccf.halflife.decay import (
    Observation,
    freshness_over_of,
    leading_edge,
    series_key_attribute_of,
)

NOW = datetime(2026, 8, 18, tzinfo=timezone.utc)
DAY = 86400


def entry(**over: object) -> HalfLifeEntry:
    return HalfLifeEntry(
        half_life_seconds=DAY, decay_driver="market-movement",
        supersession_event="next-observation", decay_basis="valid-from", **over,
    )


def table(**over: object) -> HalfLifeTable:
    return HalfLifeTable(semver="1.0.0", entries={"spread": entry(**over)})


def point(days_ago: int, series: str | None = None) -> Observation:
    """One observation, dated on the axis its row decays against."""
    return Observation(
        observation_type="spread", observed_at=NOW,
        valid_from=NOW - timedelta(days=days_ago), series=series,
        subject=f"spread://{series or 'x'}/{days_ago}",
    )


#: The cp-10 shape: a two-year daily series whose newest point is current.
SERIES = [point(d) for d in (0, 30, 90, 180, 365, 500, 600, 700, 729)]


def score(observations: list[Observation], **over: object) -> Decimal:
    selected = leading_edge(observations, table=table(**over), now=NOW)
    return FreshnessScorer(
        table=table(**over), risk_sensitivity=Decimal(1)
    ).score(selected, now=NOW)


def test_the_default_aggregation_is_unchanged_and_is_the_archive_s_length() -> None:
    """`series-mean` is what every table had, and it is kept exactly.

    Asserted as the FAILING case on purpose: this is the number that made a
    two-year migration product unservable, and it must still be reachable, or
    the ruling would have silently changed every existing deployment.
    """
    assert freshness_over_of(table(), "spread") == "series-mean"
    assert score(SERIES) < Decimal("0.2")


def test_leading_edge_scores_only_the_newest_member() -> None:
    """THE REGRESSION. The same rows, one declaration different.

    Nine observations spanning 729 days; the newest is at the decision instant.
    Under `leading-edge` the series is current, because the newest thing known
    about it is current.
    """
    assert score(SERIES, freshness_over="leading-edge") == Decimal(1)


def test_leading_edge_still_goes_stale_when_the_edge_does() -> None:
    """The other half, and it is what `supersede-only` could never say.

    A series whose newest member is 30 days old, against a one-day half-life,
    is stale — and the historical members behind it do not rescue it. Without
    this, `leading-edge` would be `supersede-only` by another name.
    """
    cold = [point(d) for d in (30, 90, 365, 729)]
    assert score(cold, freshness_over="leading-edge") < Decimal("0.001")


def test_the_edge_is_relative_to_the_decision_instant_not_the_wall_clock() -> None:
    """A replay at an earlier instant sees the edge that was leading THEN.

    Dave's precision, and it is what makes the figure reproducible: selecting
    the globally newest observation would let a later one leak into an earlier
    answer, and the same question would score differently depending on when it
    was asked.
    """
    earlier = NOW - timedelta(days=365)
    selected = leading_edge(SERIES, table=table(freshness_over="leading-edge"), now=earlier)
    assert len(selected) == 1
    assert selected[0].valid_from is not None
    assert selected[0].valid_from <= earlier, (
        "an observation later than the decision instant led the series, so an"
        " earlier replay can see something it could not have known"
    )
    assert selected[0].valid_from == NOW - timedelta(days=365)


def test_a_series_key_splits_one_type_into_independent_series() -> None:
    """One edge per declared series, not one per type.

    cp-10's case: two bonds of one obligor are two series, and each has its own
    leading edge. Without the key both collapse into one and the fresher bond
    hides the staler one.
    """
    two_bonds = [
        point(0, series="bond-a"), point(400, series="bond-a"),
        point(200, series="bond-b"), point(700, series="bond-b"),
    ]
    selected = leading_edge(
        two_bonds,
        table=table(freshness_over="leading-edge", series_key_attribute="instrument_id"),
        now=NOW,
    )
    assert {o.series for o in selected} == {"bond-a", "bond-b"}
    assert len(selected) == 2
    ages = {o.series: (NOW - o.valid_from).days for o in selected if o.valid_from}
    assert ages == {"bond-a": 0, "bond-b": 200}, (
        "each series must be led by its OWN newest member; a shared edge would"
        " let one bond's currency stand in for another's"
    )


def test_a_row_that_aggregates_by_mean_passes_through_untouched() -> None:
    """Mixed tables are the normal case, and the selector must not touch the rest."""
    mixed = HalfLifeTable(
        semver="1.0.0",
        entries={
            "spread": entry(freshness_over="leading-edge"),
            "grade": HalfLifeEntry(
                half_life_seconds=7776000, decay_driver="cycle",
                supersession_event="next", decay_basis="valid-from",
            ),
        },
    )
    grades = [
        Observation(observation_type="grade", observed_at=NOW,
                    valid_from=NOW - timedelta(days=d), subject=f"g{d}")
        for d in (10, 100, 400)
    ]
    selected = leading_edge([*SERIES, *grades], table=mixed, now=NOW)
    assert sum(1 for o in selected if o.observation_type == "grade") == 3
    assert sum(1 for o in selected if o.observation_type == "spread") == 1


def test_an_orphan_series_key_is_refused_at_construction() -> None:
    """A key nothing reads is a field that looks load-bearing and is not."""
    with pytest.raises(ValueError, match="leading-edge"):
        HalfLifeEntry(
            half_life_seconds=DAY, decay_driver="d", supersession_event="e",
            series_key_attribute="instrument_id",
        )


def test_an_existing_table_keeps_its_identity() -> None:
    """Both fields are omitted from the rendering at their sentinels."""
    rendered = canonical_bytes(entry())
    assert b"freshness_over" not in rendered
    assert b"series_key_attribute" not in rendered
    assert b"freshness_over" in canonical_bytes(entry(freshness_over="leading-edge"))
    assert series_key_attribute_of(table(), "spread") is None


def test_an_observation_without_a_series_keeps_its_identity() -> None:
    assert b"series" not in canonical_bytes(
        Observation(observation_type="spread", observed_at=NOW)
    )
    assert b"series" in canonical_bytes(
        Observation(observation_type="spread", observed_at=NOW, series="bond-a")
    )
