"""The debt shape that travels to a consumer (D-IMPL-99/100/101/105).

Whitepaper §7.7 and ``docs/CCF_Whitepaper_1-2.md:2696`` — debt *"is a runtime
signal the agent must consume as a first-class decision input, not a log-line
to be read after the fact"*. ``tests/halflife/test_debt.py`` owns the
computation; this module owns the **shape on the wire**: what a consumer
receives, what an examiner can reconstruct from it, and the guards the module's
own docstrings forbid weakening.

The four rulings this module asserts, each named where it is asserted:

* **D-IMPL-99** — debt travels **per factor**, as the shipped
  :class:`~ccf.halflife.assessment.DebtAssessment`, never as a scalar: an
  examiner asking why a decision was escalated needs to see which of F/C/S
  collapsed.
* **D-IMPL-47** — the scorer *in force* is pinned beside the value it produced,
  so a factor is reproducible alongside the computation that produced it. The
  ruling committed to this pin; nothing built it until now.
* **D-IMPL-101** — **recency ships, salience defers.** No salience factor, no
  salience scorer and no salience producer exists, and this module asserts that
  rather than leaving a reader to confirm it by grep.
* **D-IMPL-105** — :func:`~ccf.halflife.debt.assess_debt` stays **pure over
  ``(factors, profile)``**. No entitlement, principal or grant argument joins
  it: under a per-principal debt figure a caller could infer *what they are not
  allowed to see* from the completeness number, and dissolving the coupling
  closes that channel by construction rather than by redaction.
"""

from __future__ import annotations

import ast
import inspect
import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.artifacts import DebtProfile, HalfLifeEntry, HalfLifeTable
from ccf.halflife import assessment as assessment_module
from ccf.halflife import debt as debt_module
from ccf.halflife.assessment import (
    NO_SCORER_PINS,
    DebtAssessment,
    DebtFactors,
    DebtSignal,
    ScorerPin,
)
from ccf.halflife.debt import (
    FRESHNESS_SCORER_ID,
    FRESHNESS_SCORER_VERSION,
    FreshnessScorer,
    assess_debt,
)

#: A semver lane, structurally. Used to classify module-level string constants
#: without naming any particular version.
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")

#: The SDK's own identifier namespace. A module-level string that is neither
#: this, a semver, nor the CINV-03 mode token is the warning sign CINV-01
#: points at: domain vocabulary in ``src/``.
_SDK_NAMESPACE = "ccf."

NOW = datetime(2026, 3, 15, 12, tzinfo=UTC)

HALFLIFE_DIR = Path(inspect.getsourcefile(debt_module) or "").resolve().parent


def _profile() -> DebtProfile:
    """A test-owned profile. Bands are deployment values, never SDK values."""
    return DebtProfile(
        semver="1.0.0",
        risk_sensitivity=Decimal("1.0"),
        forced_llm_threshold=Decimal("0.40"),
        fail_closed_threshold=Decimal("0.90"),
    )


def _factors(
    *,
    freshness: str = "0.80",
    completeness: str = "0.90",
    semantic_consistency: str = "1.0",
) -> DebtFactors:
    return DebtFactors(
        freshness=Decimal(freshness),
        completeness=Decimal(completeness),
        semantic_consistency=Decimal(semantic_consistency),
    )


def _scorer() -> FreshnessScorer:
    return FreshnessScorer(
        table=HalfLifeTable(
            semver="1.0.0",
            entries={
                "test.signal": HalfLifeEntry(
                    half_life_seconds=3600,
                    decay_driver="test.driver",
                    supersession_event="test.supersession",
                )
            },
        ),
        risk_sensitivity=Decimal("1.0"),
    )


# --- D-IMPL-99: per factor, and the factors travel with the answer ---------


def test_the_assessment_carries_the_three_factors_not_a_scalar() -> None:
    """The shape is per-factor by ruling (D-IMPL-99), asserted on the type."""
    assessed = assess_debt(_factors(), profile=_profile())

    assert assessed.factors == _factors()
    assert set(type(assessed.factors).model_fields) == {
        "freshness",
        "completeness",
        "semantic_consistency",
    }


def test_the_wire_shape_is_exactly_value_signal_factors_and_scorers() -> None:
    """Pinned explicitly, so a field added to the vessel is a decision.

    :class:`DebtAssessment` is carried on ``ContextProductContract`` under
    D-IMPL-100, which puts it inside the product's content address. A field
    that arrived here unnoticed would move every recorded address in the
    tree, so the field list is asserted rather than assumed.
    """
    assert set(DebtAssessment.model_fields) == {
        "debt",
        "signal",
        "factors",
        "scorers",
    }


# --- D-IMPL-47: the scorer in force, pinned beside the value ---------------


def test_the_reference_freshness_scorer_pins_its_own_identity() -> None:
    """A factor value is only reproducible alongside what produced it."""
    pin = ScorerPin.of(_scorer(), factor="freshness")

    assert pin.factor == "freshness"
    assert pin.scorer_id == FRESHNESS_SCORER_ID
    assert pin.scorer_version == FRESHNESS_SCORER_VERSION


def test_the_assessment_carries_the_scorers_in_force() -> None:
    """D-IMPL-47's pin, closed: the scorer travels with the assessment."""
    pin = ScorerPin.of(_scorer(), factor="freshness")

    assessed = assess_debt(_factors(), profile=_profile(), scorers=(pin,))

    assert assessed.scorers == (pin,)


def test_an_unpinned_assessment_carries_the_positive_no_scorers_sentinel() -> None:
    """The ``NO_GRAPH_QUERIES`` voice: an absence stated, never inferred.

    Only F has an SDK reference scorer; C and S are caller-supplied until
    their scorers ship. An assessment that pinned nothing *asserts* that its
    factors were supplied rather than produced by a declared scorer, which is
    a different statement from a pin somebody dropped.
    """
    assessed = assess_debt(_factors(), profile=_profile())

    assert assessed.scorers == NO_SCORER_PINS
    assert NO_SCORER_PINS == ()


def test_pins_are_stored_in_one_canonical_order() -> None:
    """Declaration order is not a fact about the decision.

    The ``graph_secret_refs`` precedent: two assessments that pinned the same
    scorers in different order must reach the same content address, or a
    replay comparison would report a difference where there is none — and
    this value is inside the product's address under D-IMPL-100.
    """
    freshness = ScorerPin(
        factor="freshness", scorer_id="ccf.a", scorer_version="1.0.0"
    )
    completeness = ScorerPin(
        factor="completeness", scorer_id="ccf.b", scorer_version="1.0.0"
    )

    one = assess_debt(
        _factors(), profile=_profile(), scorers=(freshness, completeness)
    )
    other = assess_debt(
        _factors(), profile=_profile(), scorers=(completeness, freshness)
    )

    assert one.scorers == other.scorers
    assert content_hash(one) == content_hash(other)


def test_two_scorers_for_one_factor_are_refused() -> None:
    """One computation produced the value; two pins cannot both be it."""
    with pytest.raises(ValidationError, match="factor"):
        DebtAssessment(
            debt=Decimal("0.1"),
            signal=DebtSignal.OK,
            factors=_factors(),
            scorers=(
                ScorerPin(
                    factor="freshness", scorer_id="ccf.a", scorer_version="1.0.0"
                ),
                ScorerPin(
                    factor="freshness", scorer_id="ccf.b", scorer_version="1.0.0"
                ),
            ),
        )


def test_the_pins_do_not_participate_in_the_computation() -> None:
    """A pin records what ran; it never changes what the answer is."""
    unpinned = assess_debt(_factors(), profile=_profile())
    pinned = assess_debt(
        _factors(),
        profile=_profile(),
        scorers=(
            ScorerPin(
                factor="freshness", scorer_id="ccf.a", scorer_version="1.0.0"
            ),
        ),
    )

    assert pinned.debt == unpinned.debt
    assert pinned.signal == unpinned.signal


# --- T-15.5-48: Decimal, never float --------------------------------------


@pytest.mark.parametrize(
    "factor", ["freshness", "completeness", "semantic_consistency"]
)
def test_a_float_factor_is_refused_at_construction(factor: str) -> None:
    """These values reach the replay record, and floats are not bit-stable.

    Coercion would be worse than refusal: ``0.8`` silently becoming a Decimal
    produces a plausible number whose provenance is a platform-dependent
    binary expansion, and the product content address carrying it would then
    depend on where the product was assembled.
    """
    values: dict[str, object] = {
        "freshness": Decimal("1"),
        "completeness": Decimal("1"),
        "semantic_consistency": Decimal("1"),
    }
    values[factor] = 0.8

    with pytest.raises(ValidationError, match="Decimal"):
        DebtFactors(**values)  # type: ignore[arg-type]


def test_a_float_debt_value_is_refused_at_construction() -> None:
    with pytest.raises(ValidationError, match="Decimal"):
        DebtAssessment(
            debt=0.42,  # type: ignore[arg-type]
            signal=DebtSignal.OK,
            factors=_factors(),
        )


def test_the_assessment_round_trips_through_its_canonical_bytes() -> None:
    """Replay resolves canonical bytes and re-validates them (D-IMPL-89).

    The float refusal must not make an honest record unreadable: Decimals are
    canonicalized to positional-notation **strings**, so re-validation never
    presents a float to the guard.
    """
    assessed = assess_debt(
        _factors(),
        profile=_profile(),
        scorers=(ScorerPin.of(_scorer(), factor="freshness"),),
    )

    revalidated = DebtAssessment.model_validate_json(canonical_bytes(assessed))

    assert revalidated == assessed
    assert content_hash(revalidated) == content_hash(assessed)


# --- the guards the module's own docstrings forbid weakening ---------------


def test_an_empty_observation_sequence_still_raises() -> None:
    """The source-outage laundering guard, unchanged (T-15.5-47).

    Letting an empty assembly enter as perfect freshness would launder a
    source outage into a low-debt reading — the precise failure the
    fail-closed posture exists to prevent.
    """
    with pytest.raises(ValueError, match="zero observations"):
        _scorer().score((), now=NOW)


def test_no_weighted_additive_combinator_was_introduced() -> None:
    """``context_debt``'s docstring forecloses the weighted-additive form.

    The whitepaper's own worked example — 0.955 multiplicative against 0.23
    additive on identical context — is the argument, and the masking is what
    makes the additive form indefensible under an examiner's reading. The
    check is on ``weight`` rather than on ``sum(``: the shipped mean of
    per-observation decay ratios in :class:`FreshnessScorer` is an aggregation
    *within* F, not a combinator across F/C/S.
    """
    for module in (debt_module, assessment_module):
        source = inspect.getsource(module)
        assert "weight" not in source, module.__name__

    assert "*" in inspect.getsource(debt_module.context_debt)
    assert "+" not in inspect.getsource(debt_module.context_debt)


# --- D-IMPL-105: pure over (factors, profile) ------------------------------


def test_assess_debt_takes_no_principal_or_entitlement_argument() -> None:
    """The inference channel D-IMPL-105 forecloses, asserted structurally.

    Under a per-principal debt figure the completeness number **moves when a
    source is withheld**, so a caller can infer what they are not allowed to
    see from the debt they are shown — an oracle over the entitlement
    configuration, reachable with ordinary delivery access and no privileged
    read. A refused consultation is simply not part of ``C_required`` for that
    principal, so there is no per-principal figure to differ and nothing to
    difference.
    """
    parameters = inspect.signature(assess_debt).parameters

    assert set(parameters) == {"factors", "profile", "scorers"}
    assert parameters["profile"].kind.name == "KEYWORD_ONLY"
    assert parameters["scorers"].kind.name == "KEYWORD_ONLY"
    assert parameters["scorers"].default == NO_SCORER_PINS


# --- D-IMPL-101: recency ships, salience defers ---------------------------


def test_no_salience_factor_or_scorer_exists() -> None:
    """Salience defers to Phase 17; nothing for it lands in this phase.

    ``15.5-01`` measured salience as having **no producer anywhere** in
    ``src/`` or ``runtime/``, and D-IMPL-101 ruled option (d) on that
    measurement. Correct work here must not quietly build one.
    """
    for module_path in sorted(HALFLIFE_DIR.glob("*.py")):
        assert (
            "salience" not in module_path.read_text(encoding="utf-8").lower()
        ), module_path.name


# --- CINV-01: no domain vocabulary, which the numeric-table lint misses ----


def _module_level_strings(module_path: Path) -> dict[str, str]:
    """Every module-level ``NAME = "literal"`` in ``module_path``."""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    found: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not isinstance(node.value, ast.Constant) or not isinstance(
            node.value.value, str
        ):
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                found[target.id] = node.value.value
    return found


@pytest.mark.parametrize("module", ["debt.py", "assessment.py"])
def test_every_module_level_string_constant_is_structural(module: str) -> None:
    """``cinv01b-numeric-table`` catches a numeric map and nothing else.

    It does **not** catch a module-level tuple of strings, so the lint will
    not save this module: the warning sign is any string literal in ``src/``
    that a banker would recognize. Each constant here must be an SDK-namespaced
    identifier, a semver lane, or the CINV-03 mode token — nothing else.
    """
    for name, value in _module_level_strings(HALFLIFE_DIR / module).items():
        assert (
            value.startswith(_SDK_NAMESPACE)
            or bool(_SEMVER.match(value))
            or value == "algorithmic"
        ), f"{module}:{name} = {value!r} is not a structural identifier"


@pytest.mark.parametrize("module", ["debt.py", "assessment.py"])
def test_no_module_level_collection_of_string_literals_exists(
    module: str,
) -> None:
    """The shape the numeric-table lint cannot see, refused here instead.

    ``__all__`` is the one legitimate module-level string collection — it
    names this module's own exports, which are code, not values.
    """
    tree = ast.parse((HALFLIFE_DIR / module).read_text(encoding="utf-8"))

    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        names = {t.id for t in targets if isinstance(t, ast.Name)}
        if names == {"__all__"}:
            continue
        if not isinstance(node.value, (ast.Tuple, ast.List, ast.Set)):
            continue
        assert not any(
            isinstance(element, ast.Constant) and isinstance(element.value, str)
            for element in node.value.elts
        ), f"{module}: {names} is a module-level collection of string literals"
