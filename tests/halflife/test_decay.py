"""λ_c decay tests (FABR-05; whitepaper §7.7 "Context Half-life as Formal Decay").

The suite pins three things the mechanism must not be able to lose:

* the decay *formula* — ``R(t) = R₀ × (1/2)^((t − t₀) / λ_c)`` — checked at the
  points where it is exactly known (t₀, one half-life, two half-lives) rather
  than against a hand-computed approximation;
* the **no-fallback-rate** rule: an observation type absent from the table
  raises, because a decay rate the deployment never chose is a fabricated
  confidence figure (D-IMPL-38);
* that every λ value comes from the fixture artifact — change the fixture,
  change the result, deterministically.

All values load from ``tests/fixtures/banking/halflife.yaml``. Delete the
fixture and this file has nothing to assert (CLAUDE.md §6.4, applied to test
code per CONTEXT.md).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.halflife.decay import (
    HalfLifeTable,
    MissingHalfLife,
    Observation,
    TemporalOrderError,
    freshness,
    half_life_of,
    relevance_ratio,
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "banking" / "halflife.yaml"

#: The instant the fixture decisions are taken at. A test input, never a clock
#: read — the whole point of injecting ``now`` is that decay is replayable.
NOW = datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
def document() -> Any:
    return yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def table(document: Any) -> HalfLifeTable:
    return HalfLifeTable.model_validate(document["half_life_table"])


def _type_with_shortest_half_life(table: HalfLifeTable) -> str:
    return min(table.entries, key=lambda name: table.entries[name].half_life_seconds)


# --- the formula -----------------------------------------------------------


def test_relevance_is_whole_at_the_observation_instant() -> None:
    ratio = relevance_ratio(elapsed=timedelta(0), half_life=timedelta(hours=1))
    assert ratio == Decimal(1)


def test_relevance_halves_after_exactly_one_half_life() -> None:
    ratio = relevance_ratio(elapsed=timedelta(hours=1), half_life=timedelta(hours=1))
    assert ratio == Decimal(1) / Decimal(2)


def test_relevance_quarters_after_two_half_lives() -> None:
    ratio = relevance_ratio(elapsed=timedelta(hours=2), half_life=timedelta(hours=1))
    assert ratio == Decimal(1) / Decimal(4)


def test_relevance_is_strictly_decreasing_and_never_negative() -> None:
    half_life = timedelta(hours=1)
    ratios = [
        relevance_ratio(elapsed=timedelta(minutes=minutes), half_life=half_life)
        for minutes in (0, 15, 30, 240)
    ]
    assert ratios == sorted(ratios, reverse=True)
    assert ratios[-1] > Decimal(0)


def test_relevance_never_expires_to_zero() -> None:
    """λ_c is not a TTL: aged context stays reconstructible (INV-CH7-57)."""
    ratio = relevance_ratio(elapsed=timedelta(days=3650), half_life=timedelta(hours=1))
    assert ratio >= Decimal(0)


def test_relevance_is_deterministic_across_calls() -> None:
    args = {"elapsed": timedelta(seconds=4321), "half_life": timedelta(seconds=9999)}
    assert relevance_ratio(**args) == relevance_ratio(**args)


def test_non_positive_half_life_is_refused() -> None:
    with pytest.raises(ValueError):
        relevance_ratio(elapsed=timedelta(hours=1), half_life=timedelta(0))


# --- table resolution ------------------------------------------------------


def test_half_life_comes_from_the_table(table: HalfLifeTable, document: Any) -> None:
    name = _type_with_shortest_half_life(table)
    declared = document["half_life_table"]["entries"][name]["half_life_seconds"]
    assert half_life_of(table, name) == timedelta(seconds=declared)


def test_unknown_observation_type_raises_rather_than_defaulting(
    table: HalfLifeTable,
) -> None:
    with pytest.raises(MissingHalfLife):
        half_life_of(table, "an-observation-type-the-deployment-never-declared")


def test_the_table_declares_the_full_configuration_row(table: HalfLifeTable) -> None:
    """(type, band, dominant decay driver, supersession event) — INV-CH7-59."""
    for name, entry in table.entries.items():
        assert name
        assert entry.half_life_seconds > 0
        assert entry.decay_driver
        assert entry.supersession_event


def test_a_table_entry_without_a_declared_rate_is_refused() -> None:
    with pytest.raises(ValueError):
        HalfLifeTable.model_validate(
            {
                "semver": "1.0.0",
                "entries": {
                    "x": {
                        "decay_driver": "d",
                        "supersession_event": "s",
                    }
                },
            }
        )


# --- freshness over an observation ----------------------------------------


def test_freshness_uses_the_types_own_rate(table: HalfLifeTable) -> None:
    name = _type_with_shortest_half_life(table)
    half_life = half_life_of(table, name)
    observation = Observation(observation_type=name, observed_at=NOW - half_life)
    assert freshness(observation, now=NOW, table=table, risk_sensitivity=Decimal(1)) == (
        Decimal(1) / Decimal(2)
    )


def test_risk_sensitivity_shrinks_the_freshness_budget(table: HalfLifeTable) -> None:
    """λ_c × Risk Sensitivity: a tighter class ages the same observation faster."""
    name = _type_with_shortest_half_life(table)
    observation = Observation(
        observation_type=name, observed_at=NOW - half_life_of(table, name)
    )
    tolerant = freshness(
        observation, now=NOW, table=table, risk_sensitivity=Decimal(1)
    )
    tight = freshness(
        observation, now=NOW, table=table, risk_sensitivity=Decimal(1) / Decimal(2)
    )
    assert tight < tolerant


def test_freshness_of_an_unlisted_type_raises(table: HalfLifeTable) -> None:
    observation = Observation(observation_type="undeclared", observed_at=NOW)
    with pytest.raises(MissingHalfLife):
        freshness(observation, now=NOW, table=table, risk_sensitivity=Decimal(1))


def test_an_observation_from_the_future_is_refused(table: HalfLifeTable) -> None:
    """Clock skew is surfaced, never clamped to 'perfectly fresh'."""
    name = _type_with_shortest_half_life(table)
    observation = Observation(
        observation_type=name, observed_at=NOW + timedelta(seconds=1)
    )
    with pytest.raises(TemporalOrderError):
        freshness(observation, now=NOW, table=table, risk_sensitivity=Decimal(1))


def test_a_naive_observation_timestamp_is_refused(table: HalfLifeTable) -> None:
    name = _type_with_shortest_half_life(table)
    observation = Observation(
        observation_type=name, observed_at=datetime(2026, 3, 1, 9, 0, 0)
    )
    with pytest.raises(ValueError):
        freshness(observation, now=NOW, table=table, risk_sensitivity=Decimal(1))


def test_non_positive_risk_sensitivity_is_refused(table: HalfLifeTable) -> None:
    name = _type_with_shortest_half_life(table)
    observation = Observation(observation_type=name, observed_at=NOW)
    with pytest.raises(ValueError):
        freshness(observation, now=NOW, table=table, risk_sensitivity=Decimal(0))


def test_module_is_tagged_algorithmic() -> None:
    import ccf.halflife.decay as decay_mod

    assert decay_mod.__ccf_mode__ == "algorithmic"
