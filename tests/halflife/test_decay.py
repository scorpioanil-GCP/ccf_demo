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

from ccf.contracts.canonical import content_hash
from ccf.halflife.decay import (
    NO_SUBJECT_IDENTITY,
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

#: A subject identity owned by this test module and by nothing else. The value
#: is **deployment-side**: the SDK enumerates no identifier scheme, requires no
#: entity URI, claim id or document id, and never interprets what it is handed
#: (D-IMPL-117, CLAUDE.md §11). This particular spelling is a test fixture, so
#: the suite's identities are visibly chosen here rather than implied by the
#: type (CINV-01's scope reaches ``tests/``).
SUBJECT = "test-subject-alpha"

#: A second, distinct deployment-side identity, for the assertions that need two
#: observations to differ in the identity and in nothing else. Same discipline:
#: a test-owned value, no SDK vocabulary.
OTHER_SUBJECT = "test-subject-beta"


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
    observation = Observation(
        observation_type=name, observed_at=NOW - half_life, subject=SUBJECT
    )
    assert freshness(observation, now=NOW, table=table, risk_sensitivity=Decimal(1)) == (
        Decimal(1) / Decimal(2)
    )


def test_risk_sensitivity_shrinks_the_freshness_budget(table: HalfLifeTable) -> None:
    """λ_c × Risk Sensitivity: a tighter class ages the same observation faster."""
    name = _type_with_shortest_half_life(table)
    observation = Observation(
        observation_type=name,
        observed_at=NOW - half_life_of(table, name),
        subject=SUBJECT,
    )
    tolerant = freshness(
        observation, now=NOW, table=table, risk_sensitivity=Decimal(1)
    )
    tight = freshness(
        observation, now=NOW, table=table, risk_sensitivity=Decimal(1) / Decimal(2)
    )
    assert tight < tolerant


def test_freshness_of_an_unlisted_type_raises(table: HalfLifeTable) -> None:
    observation = Observation(
        observation_type="undeclared", observed_at=NOW, subject=SUBJECT
    )
    with pytest.raises(MissingHalfLife):
        freshness(observation, now=NOW, table=table, risk_sensitivity=Decimal(1))


def test_an_observation_from_the_future_is_refused(table: HalfLifeTable) -> None:
    """Clock skew is surfaced, never clamped to 'perfectly fresh'."""
    name = _type_with_shortest_half_life(table)
    observation = Observation(
        observation_type=name,
        observed_at=NOW + timedelta(seconds=1),
        subject=SUBJECT,
    )
    with pytest.raises(TemporalOrderError):
        freshness(observation, now=NOW, table=table, risk_sensitivity=Decimal(1))


def test_a_naive_observation_timestamp_is_refused(table: HalfLifeTable) -> None:
    name = _type_with_shortest_half_life(table)
    observation = Observation(
        observation_type=name,
        observed_at=datetime(2026, 3, 1, 9, 0, 0),
        subject=SUBJECT,
    )
    with pytest.raises(ValueError):
        freshness(observation, now=NOW, table=table, risk_sensitivity=Decimal(1))


def test_non_positive_risk_sensitivity_is_refused(table: HalfLifeTable) -> None:
    name = _type_with_shortest_half_life(table)
    observation = Observation(
        observation_type=name, observed_at=NOW, subject=SUBJECT
    )
    with pytest.raises(ValueError):
        freshness(observation, now=NOW, table=table, risk_sensitivity=Decimal(0))


def test_module_is_tagged_algorithmic() -> None:
    import ccf.halflife.decay as decay_mod

    assert decay_mod.__ccf_mode__ == "algorithmic"


# --- the subject identity (D-IMPL-120, D-IMPL-117) -------------------------


def test_a_subject_identity_round_trips_unchanged() -> None:
    """The SDK carries the deployment's identity verbatim and interprets none
    of it: what went in comes back out, through validation and dumping alike."""
    observation = Observation(
        observation_type="a-declared-type", observed_at=NOW, subject=SUBJECT
    )
    assert observation.subject == SUBJECT

    dumped = observation.model_dump()
    assert dumped["subject"] == SUBJECT
    assert Observation.model_validate(dumped) == observation


def test_an_observation_without_a_subject_carries_the_positive_sentinel() -> None:
    """D-IMPL-120 ruled the identity **optional** — ``qc-optional`` — and
    D-IMPL-38 rules out expressing the absence as ``None``.

    The absent value is a named positive assertion: *this observation was
    recorded without a subject identity*. An identity somebody dropped and one
    that was never available would otherwise be the same artifact, which is the
    repudiation failure mode every sentinel in this fabric closes.
    """
    observation = Observation(observation_type="a-declared-type", observed_at=NOW)
    assert observation.subject == NO_SUBJECT_IDENTITY
    assert observation.subject is not None
    assert Observation.model_fields["subject"].is_required() is False


def test_a_two_key_observation_mapping_still_validates() -> None:
    """The measured consequence of ``qc-optional``, asserted rather than
    described: the three shipped example artifacts carry exactly the two keys
    they carried before this field existed, and they must keep validating."""
    validated = Observation.model_validate(
        {"observation_type": "a-declared-type", "observed_at": "2026-03-01T10:00:00Z"}
    )
    assert validated.subject == NO_SUBJECT_IDENTITY


def test_two_observations_differing_only_in_subject_are_distinct() -> None:
    """The property a downstream evidence pointer depends on.

    If the identity did not reach the canonical bytes, a pointer *to* an
    observation could not distinguish the thing it points at from a different
    one, and the join key would exist on the type without existing in any
    address.
    """
    one = Observation(
        observation_type="a-declared-type", observed_at=NOW, subject=SUBJECT
    )
    other = Observation(
        observation_type="a-declared-type", observed_at=NOW, subject=OTHER_SUBJECT
    )
    assert one != other
    assert content_hash(one) != content_hash(other)


def test_an_unpopulated_subject_hashes_differently_from_a_populated_one() -> None:
    """The sentinel is inside the canonical bytes too, so *no identity* is a
    distinguishable state rather than an invisible one."""
    absent = Observation(observation_type="a-declared-type", observed_at=NOW)
    present = Observation(
        observation_type="a-declared-type", observed_at=NOW, subject=SUBJECT
    )
    assert content_hash(absent) != content_hash(present)


def test_a_naive_timestamp_is_still_refused_on_a_subject_bearing_observation(
    table: HalfLifeTable,
) -> None:
    """The existing discipline is unchanged by the new field (D-IMPL-38)."""
    name = _type_with_shortest_half_life(table)
    observation = Observation(
        observation_type=name,
        observed_at=datetime(2026, 3, 1, 9, 0, 0),
        subject=SUBJECT,
    )
    with pytest.raises(ValueError):
        freshness(observation, now=NOW, table=table, risk_sensitivity=Decimal(1))


def test_freshness_ignores_the_subject_entirely(table: HalfLifeTable) -> None:
    """The identity is **carried, not consumed**: decay reads the type and the
    instant, exactly as whitepaper §7.7 binds λ_c, and nothing else."""
    name = _type_with_shortest_half_life(table)
    observed_at = NOW - half_life_of(table, name)
    figures = {
        freshness(
            Observation(
                observation_type=name, observed_at=observed_at, subject=subject
            ),
            now=NOW,
            table=table,
            risk_sensitivity=Decimal(1),
        )
        for subject in (SUBJECT, OTHER_SUBJECT)
    } | {
        freshness(
            Observation(observation_type=name, observed_at=observed_at),
            now=NOW,
            table=table,
            risk_sensitivity=Decimal(1),
        )
    }
    assert figures == {Decimal(1) / Decimal(2)}
