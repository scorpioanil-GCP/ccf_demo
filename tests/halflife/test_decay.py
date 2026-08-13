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
    """At **construction**, which is what this class has always documented.

    The attribute docstring has always read *"a naive instant is rejected"* and
    there was no validator until Phase 15.6's close; this test asserted the
    refusal at *computation* time, which is where it actually lived. A naive
    observation was therefore constructible, serialisable and storable — the
    deferral CLAUDE.md §11 refuses — and the citation
    `SourceRefreshWindow._the_instant_names_its_zone` makes to this field as
    the precedent it restates pointed at nothing.
    """
    name = _type_with_shortest_half_life(table)
    with pytest.raises(ValueError, match="zone"):
        Observation(
            observation_type=name,
            observed_at=datetime(2026, 3, 1, 9, 0, 0),
            subject=SUBJECT,
        )


def test_a_bare_epoch_observation_timestamp_is_refused(
    table: HalfLifeTable,
) -> None:
    """CR-01's correction, on the field that precedent cites.

    Pydantic's lax mode reads `1772359200` as a tz-aware UTC instant before any
    after-validator runs, so a rule stated only after validation passes on an
    input that named no zone at all. Same helper, same position, as
    `SourceRefreshWindow`.
    """
    name = _type_with_shortest_half_life(table)
    with pytest.raises(ValueError, match="bare number"):
        Observation(
            observation_type=name,
            observed_at=1772359200,  # type: ignore[arg-type]
            subject=SUBJECT,
        )


def test_the_computation_still_refuses_a_naive_instant_it_is_handed(
    table: HalfLifeTable,
) -> None:
    """The construction-time gate does not make `freshness`' own check dead.

    `model_construct` skips validation, and `now` is an argument no contract
    validates at all — so the computation is the only thing standing between an
    implicit zone and a freshness figure on both of those paths. Asserted so a
    later reader does not delete the check as redundant.
    """
    name = _type_with_shortest_half_life(table)
    unvalidated = Observation.model_construct(
        observation_type=name,
        observed_at=datetime(2026, 3, 1, 9, 0, 0),
        subject=SUBJECT,
    )

    assert unvalidated.observed_at.tzinfo is None
    with pytest.raises(ValueError, match="timezone-aware"):
        freshness(unvalidated, now=NOW, table=table, risk_sensitivity=Decimal(1))


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


def test_the_sentinel_is_sdk_namespaced() -> None:
    """The marker reads as SDK structure, not as a word from somebody's domain.

    Phase 15.6's close-time cross-AI panel found this sentinel spelled
    `"no-subject-identity"` — a bare phrase — while its sibling
    `ccf.halflife.assessment.NO_OBLIGATION_IN_FORCE` was `ccf.`-prefixed *and*
    said in its own comment why: so a deployment cannot collide with it by
    accident while reaching for an ordinary phrase. A deployment whose real
    opaque subject was spelled `no-subject-identity` produced an artifact
    indistinguishable from one with no subject at all, which is precisely what
    D-IMPL-120 exists to prevent — *"an omitted identity and a dropped one are
    not the same artifact."*

    `tests/halflife/test_debt_delivery.py::test_every_module_level_string_constant_is_structural`
    is the standing check; `decay.py` is added to its parametrization in the
    same commit as this test, which is why the defect survived plan `15.6-05`.
    """
    assert NO_SUBJECT_IDENTITY.startswith("ccf.")
    assert NO_SUBJECT_IDENTITY == "ccf.no-subject-identity"


@pytest.mark.parametrize(
    "blank", ["", "   ", "\t", "\n "], ids=["empty", "spaces", "tab", "newline"]
)
def test_a_blank_subject_is_refused(blank: str) -> None:
    """A blank identity names nothing while claiming to name something.

    `ccf.halflife.assessment.SignalObligation.obligation_ref`'s refusal,
    restated here for its reason. A blank is what a half-finished assembler edit
    leaves behind, and accepting it would make *recorded without an identity* —
    which `NO_SUBJECT_IDENTITY` already asserts, positively — and *recorded with
    an unnameable one* two spellings of one claim. Whitespace goes with the
    empty string because a subject of spaces is the empty string in a costume,
    and the value is inside the observation's canonical bytes either way.
    """
    with pytest.raises(ValueError, match="subject identity must be declared"):
        Observation(
            observation_type="a-declared-type", observed_at=NOW, subject=blank
        )


@pytest.mark.parametrize(
    "reserved",
    ["ccf.subject", "ccf.no-subject-identity-2", "ccf."],
    ids=["sdk-shaped", "near-miss-of-the-sentinel", "bare-prefix"],
)
def test_a_subject_in_the_sdk_namespace_is_refused(reserved: str) -> None:
    """`ccf.` is reserved, so nothing a deployment declares can live in it.

    This is the reservation limb, and it is what actually closes the
    impersonation channel the panel found. Namespacing the sentinel alone would
    make collision unlikely; reserving the namespace makes it **unavailable**,
    so a subject that could be mistaken for SDK structure is refused at the
    boundary rather than discovered by a reader who cannot tell the two apart.

    The tree already names this namespace as the SDK's own:
    `tests/halflife/test_debt_delivery.py::_SDK_NAMESPACE` is `"ccf."`, and
    `NO_OBLIGATION_IN_FORCE`'s comment states the discipline outright.
    """
    with pytest.raises(ValueError, match="reserved"):
        Observation(
            observation_type="a-declared-type", observed_at=NOW, subject=reserved
        )


@pytest.mark.parametrize(
    "impersonation",
    [
        " ccf.no-subject-identity",
        "ccf.no-subject-identity ",
        "\xa0ccf.no-subject-identity",
        "CCF.no-subject-identity",
        "Ccf.No-Subject-Identity",
        "​ccf.no-subject-identity",
        "ｃｃｆ．no-subject-identity",
    ],
    ids=[
        "leading space",
        "trailing space",
        "non-breaking space",
        "upper case",
        "mixed case",
        "zero-width space",
        "full-width compatibility form",
    ],
)
def test_a_marker_impersonation_that_renders_identically_is_refused(
    impersonation: str,
) -> None:
    """The reservation reads the value as a reader sees it, not as bytes.

    The refusal's own message says the offending value *"would be
    indistinguishable, to a reader, from a marker the fabric itself wrote"* —
    and Phase 15.6's single-agent review demonstrated by execution that the
    check compared raw bytes, so every spelling that renders identically and
    compares differently walked past it. A leading space renders invisibly in
    most consumers of a JSON product; so does a zero-width space; and case is
    not a distinction a reader draws in a marker.

    None of these is the sentinel — the carve-out is an exact comparison — so
    each is a deployment value wearing SDK structure's clothes, which is
    precisely what the reservation exists to make unavailable (D-IMPL-120).
    """
    with pytest.raises(ValueError, match="reserved"):
        Observation(
            observation_type="a-declared-type",
            observed_at=NOW,
            subject=impersonation,
        )


def test_a_subject_of_invisible_characters_is_blank_rather_than_declared() -> None:
    """A zero-width space is not an identity, for the whitespace reason.

    `str.strip()` does not remove U+200B, so before the reader-visible
    reduction a subject of nothing but zero-width spaces was *declared* — a
    value that names nothing while claiming to name something, which is the
    exact state the blank refusal exists to close.
    """
    with pytest.raises(ValueError, match="subject identity must be declared"):
        Observation(
            observation_type="a-declared-type",
            observed_at=NOW,
            subject="​​",
        )


def test_a_confusable_subject_is_accepted_and_the_limit_is_deliberate() -> None:
    """The reservation's stated boundary, asserted so it cannot drift silently.

    `сcf.something` with a Cyrillic `с` renders like the reserved namespace and
    is **accepted**: folding confusables needs a confusable table and a policy
    about which scripts a deployment may write, which is deployment knowledge
    the SDK does not hold (CLAUDE.md §11). The reduction closes the spellings
    that are mechanically identical to a reader, not every spelling that is
    visually similar to one — and that limit is documented on
    `_as_a_reader_sees_it` rather than left for a reader to discover.
    """
    confusable = "сcf.something"  # Cyrillic es, then "cf."

    observation = Observation(
        observation_type="a-declared-type", observed_at=NOW, subject=confusable
    )

    assert observation.subject == confusable
    assert confusable != "ccf.something"


def test_the_sentinel_itself_stays_admissible_and_round_trips() -> None:
    """The widening control, and the constraint that shapes this fix.

    The sentinel is this field's **own default**, so it is not the same case as
    `SignalObligation.obligation_ref` — where the sentinel lives on a different
    field and can therefore be refused outright. Here, refusing the sentinel
    spelling would make `Observation.model_validate(Observation(...).model_dump())`
    raise for every unpopulated observation, because `subject` is serialized
    whether or not it is populated (recorded in
    `docs/surface-changes/15.6-05-observation-identity.md`). A contract that
    cannot re-validate its own dump is not a stricter contract.

    So the reservation is over the **namespace**, with the sentinel carved out
    of it: `subject=NO_SUBJECT_IDENTITY` remains, in the words of the `15.6-05`
    fragment, *"the same value and the louder statement"*. A future re-narrowing
    to a flat refusal of the sentinel turns this test red rather than turning
    the round trip quietly impossible.
    """
    explicit = Observation(
        observation_type="a-declared-type",
        observed_at=NOW,
        subject=NO_SUBJECT_IDENTITY,
    )
    omitted = Observation(observation_type="a-declared-type", observed_at=NOW)

    assert explicit == omitted
    assert content_hash(explicit) == content_hash(omitted)
    assert Observation.model_validate(omitted.model_dump()) == omitted


def test_an_ordinary_deployment_subject_is_still_accepted_verbatim() -> None:
    """The other half of the widening control: this is not a format check.

    The SDK enumerates no identifier scheme and interprets nothing it is handed
    (D-IMPL-117, CLAUDE.md §11). Everything outside the reserved namespace is
    admitted exactly as written — including the now-ordinary phrase the sentinel
    used to be spelled with, which after namespacing carries no SDK meaning at
    all and is therefore a deployment's to use.
    """
    for value in ("no-subject-identity", "borrower://x", "0", " leading-space"):
        observation = Observation(
            observation_type="a-declared-type", observed_at=NOW, subject=value
        )
        assert observation.subject == value


def test_a_naive_timestamp_is_still_refused_on_a_subject_bearing_observation(
    table: HalfLifeTable,
) -> None:
    """The existing discipline is unchanged by the new field (D-IMPL-38).

    Moved to construction at Phase 15.6's close along with the refusal itself;
    what this case adds over its sibling is that the instant rule and the
    subject rule are independent — a naive instant is refused whether or not
    the observation carries an identity.
    """
    name = _type_with_shortest_half_life(table)
    with pytest.raises(ValueError, match="zone"):
        Observation(
            observation_type=name,
            observed_at=datetime(2026, 3, 1, 9, 0, 0),
            subject=SUBJECT,
        )


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
