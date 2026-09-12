"""`D-IMPL-331` — which of an observation's two instants a λ_c row decays against.

**The defect this closes, measured before the field existed.**
:meth:`ccf.assembly.worker.AssemblyWorker._stitch` sets a claim's
``observed_at`` to ingestion *always* — by design, and unchanged by this work —
and routes the source's own instant to ``valid_from``.
:meth:`ccf.products.debt_scorer.DebtScorer._observations` copied only the
first. So ``F`` measured *how long ago the fabric learned a claim*, which for a
fabric populated inside the run is zero for everything, and a declared λ_c
table could not move ``F`` at all. `cp-09` measured ``F = 1.000000`` on a serve
carrying three observations 65,100 seconds old against their own declared
86,400-second half-life (`CP09-F-06`).

**What this module holds.** That the basis SELECTS — the same observation and
the same table scoring differently under the two declarations — that a
``valid-from`` row refuses rather than falling back when the instant is absent,
and that **every table written before the field existed keeps its identity and
its figure**, which is the property that makes the change additive rather than
a generation boundary.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.artifacts import HalfLifeEntry, HalfLifeTable
from ccf.halflife.decay import (
    MissingDecayInstant,
    Observation,
    TemporalOrderError,
    decay_basis_of,
    freshness,
)

NOW = datetime(2026, 6, 17, 18, 5, tzinfo=timezone.utc)

#: The cp-09 measurement, kept as the case rather than a rounder one: 65,100
#: seconds against an 86,400-second half-life is the exact pair that scored
#: 1.000000 before this field existed.
ELAPSED = timedelta(seconds=65100)
HALF_LIFE = 86400


def entry(basis: str = "observed-at") -> HalfLifeEntry:
    return HalfLifeEntry(
        half_life_seconds=HALF_LIFE,
        decay_driver="daily-publication",
        supersession_event="next-publication",
        decay_basis=basis,
    )


def table(basis: str = "observed-at") -> HalfLifeTable:
    return HalfLifeTable(semver="1.0.0", entries={"fx": entry(basis)})


def score(observation: Observation, basis: str) -> Decimal:
    return freshness(
        observation, now=NOW, table=table(basis), risk_sensitivity=Decimal(1)
    )


def test_the_basis_selects_which_instant_decays() -> None:
    """THE REGRESSION. One observation, one table shape, two declarations.

    The observation is the shape the fabric actually produces: ingested now,
    observed by the source 65,100 seconds ago. Under ``observed-at`` it is
    perfectly fresh, which is the true answer to *how long ago did the fabric
    learn this*. Under ``valid-from`` it has decayed, which is the true answer
    to *how old is the observation*.

    **Asserted as an inequality and an ordering, not as a pinned figure.** The
    exact ratio is `relevance_ratio`'s to define; what this module is about is
    that the declaration reaches the computation at all.
    """
    observation = Observation(
        observation_type="fx", observed_at=NOW, valid_from=NOW - ELAPSED
    )

    at_ingestion = score(observation, "observed-at")
    at_source = score(observation, "valid-from")

    assert at_ingestion == Decimal(1), (
        "an observation the fabric learned at the decision instant is"
        " perfectly fresh on the ingestion basis; if this moved, the default"
        " basis is no longer reading `observed_at`"
    )
    assert at_source < at_ingestion, (
        "the declared basis did not reach the computation: the same"
        " observation scored the same under both declarations, which is the"
        " defect `D-IMPL-331` closes"
    )
    assert Decimal(0) < at_source < Decimal(1)


def test_a_valid_from_row_refuses_an_observation_that_carries_none() -> None:
    """No silent fallback, and the refusal is its own name.

    A fallback to ``observed_at`` here would report a perfectly fresh figure
    for exactly the observations a deployment declared ``valid-from`` *because*
    it cared about their real age — the failure mode inverted rather than
    fixed.
    """
    with pytest.raises(MissingDecayInstant) as refusal:
        score(Observation(observation_type="fx", observed_at=NOW), "valid-from")
    assert "valid-from" in str(refusal.value)
    assert "observed_at" in str(refusal.value), (
        "the refusal must name the instant it declined to fall back to, or a"
        " reader cannot tell it from a missing table row"
    )


def test_the_same_observation_without_valid_from_still_scores_on_the_default() -> None:
    """The other half of the pair: absence is only fatal under the declaration.

    Without this, the refusal above could be satisfied by a rule that refused
    every observation lacking a `valid_from`, which would break every existing
    deployment.
    """
    assert score(
        Observation(observation_type="fx", observed_at=NOW - ELAPSED), "observed-at"
    ) < Decimal(1)


def test_a_source_instant_after_the_decision_is_refused_in_temporal_order() -> None:
    """The future-dated guard holds on the SECOND instant too.

    The three standing refusals are documented as holding *"in both modes"*;
    they must hold on both bases as well, or declaring `valid-from` would be a
    way to smuggle a future-dated observation past a check that only ever
    looked at `observed_at`.
    """
    with pytest.raises(TemporalOrderError):
        score(
            Observation(
                observation_type="fx", observed_at=NOW,
                valid_from=NOW + timedelta(seconds=1),
            ),
            "valid-from",
        )


def test_a_naive_source_instant_is_refused_at_construction() -> None:
    """`D-IMPL-38` reaches the new field, at the boundary rather than at use."""
    with pytest.raises(ValueError, match="zone"):
        Observation(
            observation_type="fx", observed_at=NOW,
            valid_from=datetime(2026, 6, 17, 0, 0),  # noqa: DTZ001 — the subject
        )


def test_an_existing_table_keeps_its_identity() -> None:
    """The additive property, asserted on the hash rather than described.

    `decay_basis` is hash-transparent at `observed-at`
    (`D-IMPL-243` amendment 1), so a row written before the field existed and a
    row declaring the default explicitly are the SAME bytes. If this ever goes
    red, every stored λ_c artifact version in every adopter's registry has
    moved, and replay resolves nothing.
    """
    # ASSERTED ON THE RENDERED BYTES, not by comparing two objects that both
    # carry the field. The first draft of this test compared
    # `HalfLifeEntry(...)` against `entry("observed-at")` and PASSED with the
    # transparency mark removed — both objects hold the default, so both
    # rendered it and both hashed alike. What "an existing table keeps its
    # identity" actually means is that the field is ABSENT from the rendering
    # at its sentinel, which is what a pre-`D-IMPL-331` artifact's bytes look
    # like. Sabotage that found it: delete `json_schema_extra` from the field
    # and watch this go red.
    at_sentinel = canonical_bytes(entry("observed-at"))
    assert b"decay_basis" not in at_sentinel, (
        "`decay_basis` is rendered at its sentinel, so every λ_c artifact"
        " version in every adopter's registry has moved and replay resolves"
        " nothing. The field must be hash-transparent (`D-IMPL-243`)"
    )
    assert b"decay_basis" in canonical_bytes(entry("valid-from")), (
        "a non-default basis must be INSIDE the hash — `D-IMPL-243`'s rule is"
        " 'silence equals yesterday', not 'defaults never count'"
    )
    assert content_hash(entry("observed-at")) != content_hash(entry("valid-from"))


def test_an_observation_without_the_new_field_keeps_its_identity() -> None:
    """The same additive property on the observation itself."""
    at_sentinel = canonical_bytes(Observation(observation_type="fx", observed_at=NOW))
    assert b"valid_from" not in at_sentinel
    assert b"valid_from" in canonical_bytes(
        Observation(observation_type="fx", observed_at=NOW, valid_from=NOW)
    )


def test_the_default_basis_is_what_an_undeclared_row_answers() -> None:
    """`decay_basis_of` reads the declaration, and silence means yesterday."""
    assert decay_basis_of(table(), "fx") == "observed-at"
    assert decay_basis_of(table("valid-from"), "fx") == "valid-from"


@pytest.mark.parametrize("basis", ["observed-at", "valid-from"])
def test_the_standing_refusals_hold_on_both_bases(basis: str) -> None:
    """A non-positive sensitivity is refused before any basis is read."""
    with pytest.raises(ValueError, match="sensitivity"):
        freshness(
            Observation(
                observation_type="fx", observed_at=NOW, valid_from=NOW - ELAPSED
            ),
            now=NOW,
            table=table(basis),
            risk_sensitivity=Decimal(0),
        )
