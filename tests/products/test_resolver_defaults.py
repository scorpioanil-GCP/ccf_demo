"""`17-13` — the reference debt scorer as the **default**, proven by its effect.

The 2026-08-16 spec's success criterion 4 asks for tests that prove the
reference implementation is *"actually used as a default — not merely that it
exists"*, and Risk 3 says why in the phase's own vocabulary:

    *"A default that nothing exercises is a check that stops checking without
    going red."*

So **nothing here inspects a constructor attribute.** ``resolver.debt_scorer is
not None`` is satisfied by any object at all, including one that reports a
confident number about a graph nobody read. Every assertion below reads a
:class:`~ccf.halflife.assessment.DebtAssessment` that came off a **served
product**, which is the only place the scorer's work is observable to anyone who
was not present at construction.

Two properties, and the second is the one that has teeth
---------------------------------------------------------
1. **The reference scorer produced the assessment** — the three
   :class:`~ccf.halflife.assessment.ScorerPin`\\ s on the served product name
   the SDK's own scorer ids and versions. This catches "the helper selected
   something else".
2. **The λ_c artifact reached the measurement** — two deployments differing in
   **nothing but their half-life table** produce different freshness figures,
   in the direction the shorter half-life predicts. This catches the subtler
   failure the first property cannot: a scorer that is correctly *selected*,
   correctly *pinned*, and reading none of the Control Plane material it was
   handed. A pin is a claim; a number that moves with its input is a
   measurement.

The shape every assertion here is written in
---------------------------------------------
Each is a **module-level function taking its subject as a parameter**, so a
sabotage control hands the *shipped* assertion a deliberately divergent subject
and is watched failing. An assertion re-written inside a control proves the copy
fires. The honest-subject test runs first, so no control's expectation of failure
is satisfied by a subject that never worked.

The deployment vocabulary is imported from
``tests/products/test_resolver_seam.py`` rather than restated. That module owns
the request contract, the product class and the two TTL figures the fixture
deployment is authored around, and a second copy is a second thing to keep in
step — the reason ``tests/deployment/conftest.py`` gives for owning the artifact
set in the first place. What this module adds is what debt needs and the seam
module never did: a ``λ_c`` table keyed by the entity class this deployment
actually produces, a second table that decays ten times faster, and a
:class:`~ccf.controlplane.artifacts.DebtProfile`.
"""

from __future__ import annotations

import dataclasses
import pathlib
from collections.abc import Callable, Iterator, Mapping
from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import BootedFabric, load_and_boot
from ccf.graph.protocols import GraphView
from ccf.halflife.assessment import (
    NO_SCORER_PINS,
    DebtAssessment,
    DebtFactors,
    ScorerPin,
)
from ccf.halflife.debt import (
    FRESHNESS_SCORER_ID,
    FRESHNESS_SCORER_VERSION,
    DebtSignal,
)
from ccf.products import resolver as resolver_module
from ccf.products.debt_scorer import (
    DECLARED_FACTOR_SCORER_ID,
    DECLARED_FACTOR_SCORER_VERSION,
)
from ccf.products.request import ProductRequest
from ccf.products.resolver import (
    DEBT_SCORER_INPUTS,
    GovernedResolver,
    ProductNotResolvable,
    build_governed_resolver,
)
from ccf.projection.plan import Perspective, ProjectionOutput
from ccf.replay.serve import ServedProduct

from tests.deployment.conftest import (
    ARTIFACT_SET,
    POLICY_BUNDLE_KEY,
    PRODUCT_CLASS_KEY,
    SIGNAL_BATCH_KEY,
    TENANT,
    TRAVERSAL_KEY,
    manifest_document,
    write_artifact,
)
from tests.products.test_resolver_seam import (
    ASKED_AT,
    MAX_TTL_SECONDS,
    PERSPECTIVE,
    PRODUCT_CLASS,
    PRODUCT_TTL_SECONDS,
    PRODUCT_VERSION,
    QUERY_PIN_CLASS,
    REPLAY_RECORD_CLASS,
    REQUEST_CONTRACT_CLASS_ID,
    REQUEST_CONTRACT_DOCUMENT,
    REQUEST_CONTRACT_KEY,
    THRESHOLD_PARAMETER,
)

# --- what this module adds to the fixture deployment ------------------------
#
# Test-side vocabulary, never SDK values (CINV-01).

#: The entity class ``tests/deployment``'s resolution spec produces. It is also
#: the ``λ_c`` vocabulary, which is the whole reason the reference scorer needs
#: no mapping table of its own — and the reason the stock fixture's
#: ``fixture-observation`` row is useless here.
ENTITY_CLASS = "account"

#: Two ``λ_c`` tables differing **only** in how fast one class decays. The pair
#: is what makes property 2 observable: a scorer that never opened the artifact
#: reports the same number for both.
HALF_LIFE_KEY = "fixture/half-life/account"
FAST_HALF_LIFE_KEY = "fixture/half-life/account-decays-faster"

#: The bands this fixture routes on. A profile, not a threshold the SDK chose.
DEBT_PROFILE_KEY = "fixture/debt-profile"

#: The two factors the SDK has no measurement for, as this deployment declares
#: them. ``1`` so freshness is the only factor that moves, which keeps property
#: 2's observation attributable.
DECLARED_COMPLETENESS = Decimal("1")
DECLARED_SEMANTIC_CONSISTENCY = Decimal("1")


def _half_life_document(seconds: int) -> dict[str, Any]:
    """A λ_c table declaring one decay rate for this deployment's one class."""
    return {
        "semver": "1.0.0",
        "entries": {
            ENTITY_CLASS: {
                "half_life_seconds": seconds,
                "decay_driver": "the fixture's nominal restatement cycle",
                "supersession_event": "a newer observation restating the row",
            }
        },
    }


DEBT_PROFILE_DOCUMENT: dict[str, Any] = {
    "semver": "1.0.0",
    "risk_sensitivity": "1",
    "forced_llm_threshold": "0.30",
    "fail_closed_threshold": "0.70",
}

#: ``key -> (filename, class_id, document)`` for what this module writes beside
#: the stock artifact set.
EXTRA_ARTIFACTS: tuple[tuple[str, str, str, dict[str, Any]], ...] = (
    (
        REQUEST_CONTRACT_KEY,
        "request-contract.yaml",
        REQUEST_CONTRACT_CLASS_ID,
        REQUEST_CONTRACT_DOCUMENT,
    ),
    (
        HALF_LIFE_KEY,
        "half-life-account.yaml",
        "ccf.half-life-table",
        _half_life_document(3600),
    ),
    (
        FAST_HALF_LIFE_KEY,
        "half-life-account-fast.yaml",
        "ccf.half-life-table",
        _half_life_document(360),
    ),
    (
        DEBT_PROFILE_KEY,
        "debt-profile.yaml",
        "ccf.debt-profile",
        DEBT_PROFILE_DOCUMENT,
    ),
)


# --- the deployment's Π -----------------------------------------------------


class _CountProjection:
    """Put the caller's number and the assembled count in the payload.

    Deliberately the smallest projection that still applies the caller's
    parameter, so nothing about the payload can influence what is measured:
    debt is scored over the **view**, not over what Π made of it.
    """

    def __init__(self, *, required: tuple[str, ...], request: ProductRequest) -> None:
        self._required = required
        self._request = request

    @property
    def plan_id(self) -> str:
        return PRODUCT_CLASS

    def required_operators(self) -> tuple[str, ...]:
        return self._required

    def invoke(
        self,
        *,
        view: GraphView,
        operator_outputs: Mapping[str, Any],
        perspective: Perspective,
        temporal_boundary: datetime,
    ) -> ProjectionOutput:
        return ProjectionOutput(
            plan_id=self.plan_id,
            payload={
                "threshold": str(self._request.parameters[THRESHOLD_PARAMETER]),
                "assembled": len(list(view.entities)),
            },
        )


def _plan_factory(
    *, required: tuple[str, ...], request: ProductRequest
) -> _CountProjection:
    return _CountProjection(required=required, request=request)


# --- scorers that are not the reference, for the controls -------------------


class _InertScorer:
    """A scorer that reports a confident number and names nobody.

    Accepts the reference's own constructor keywords so it can stand in for
    :class:`~ccf.products.debt_scorer.AssemblyDebtScorer` at the exact point the
    helper selects it — which is what makes the substitution a test of the
    *selection* rather than of a different input.
    """

    def __init__(self, **_ignored: Any) -> None:
        pass

    def __call__(self, *, view: GraphView) -> DebtAssessment:
        return DebtAssessment(
            debt=Decimal("0"),
            signal=DebtSignal.OK,
            factors=DebtFactors(
                freshness=Decimal("1"),
                completeness=Decimal("1"),
                semantic_consistency=Decimal("1"),
            ),
            scorers=NO_SCORER_PINS,
        )


#: The identity a deployment's own scorer pins itself under. Test-side, and
#: deliberately unlike anything in ``ccf.reference.*``.
OVERRIDE_SCORER_ID = "fixture.deployment-owned-scorer"
OVERRIDE_SCORER_VERSION = "7.7.7"

#: The one figure the override reports, chosen so it cannot coincide with any
#: number the reference produces over this fixture.
OVERRIDE_FRESHNESS = Decimal("0.125")


def _override_scorer(*, view: GraphView) -> DebtAssessment:
    """A deployment's own scorer, pinning itself under its own identity."""
    return DebtAssessment(
        debt=Decimal(1) - OVERRIDE_FRESHNESS,
        signal=DebtSignal.FORCED_LLM,
        factors=DebtFactors(
            freshness=OVERRIDE_FRESHNESS,
            completeness=Decimal("1"),
            semantic_consistency=Decimal("1"),
        ),
        scorers=tuple(
            ScorerPin(
                factor=factor,
                scorer_id=OVERRIDE_SCORER_ID,
                scorer_version=OVERRIDE_SCORER_VERSION,
            )
            for factor in ("freshness", "completeness", "semantic_consistency")
        ),
    )


# --- THE ASSERTIONS. Every one takes its subject as a parameter. ------------


#: What the SDK's own scorers pin themselves as, factor by factor. Read off the
#: shipped constants rather than spelled here, so a version bump in ``src/``
#: cannot leave this module asserting an identity nothing carries any more.
REFERENCE_PINS: Mapping[str, tuple[str, str]] = {
    "freshness": (FRESHNESS_SCORER_ID, FRESHNESS_SCORER_VERSION),
    "completeness": (DECLARED_FACTOR_SCORER_ID, DECLARED_FACTOR_SCORER_VERSION),
    "semantic_consistency": (
        DECLARED_FACTOR_SCORER_ID,
        DECLARED_FACTOR_SCORER_VERSION,
    ),
}


def assert_the_reference_scorer_produced_the_assessment(
    assessment: DebtAssessment,
) -> None:
    """The three pins on a **served product** name the SDK's own scorers.

    Read off the produced assessment rather than off the resolver, because the
    resolver's field is satisfied by any callable and the pins are the only
    record of which one ran. The comparison is a **whole-mapping equality**, so
    an assessment carrying no pins at all fails as loudly as one naming a
    stranger — ``{} != {...}`` — which is the empty case a per-pin loop would
    pass silently.
    """
    observed = {
        pin.factor: (pin.scorer_id, pin.scorer_version)
        for pin in assessment.scorers
    }
    if observed != dict(REFERENCE_PINS):
        raise AssertionError(
            "the served product's debt was not produced by the SDK's reference"
            f" scorer: pins {observed} != {dict(REFERENCE_PINS)}. A resolver"
            " built through `build_governed_resolver` with no `debt_scorer` must"
            " select `ccf.products.debt_scorer.AssemblyDebtScorer`, and the pins"
            " are where that selection is observable to anyone who was not"
            " present at construction"
        )


def assert_the_half_life_artifact_reached_the_measurement(
    slower: DebtAssessment, faster: DebtAssessment
) -> None:
    """Freshness moves with the ``λ_c`` table, in the direction decay predicts.

    Two deployments identical in every respect but the half-life artifact their
    ``half_life_key`` names. A scorer that was selected, pinned and read
    **nothing** reports one number for both — which is exactly a check that
    stopped checking without going red, and is what a pin assertion alone
    cannot see.

    ``<`` rather than ``!=``: two different numbers could differ for any reason,
    and only the *ordering* is predicted by the artifact. A shorter half-life is
    more decay over the same age, so the faster table must report the staler
    view.
    """
    if not faster.factors.freshness < slower.factors.freshness:
        raise AssertionError(
            "the half-life artifact did not reach the measurement: the table"
            f" declaring the faster decay reported freshness"
            f" {faster.factors.freshness} and the slower one reported"
            f" {slower.factors.freshness}, and the faster must be the smaller."
            " Two deployments differing in nothing but their λ_c table must"
            " differ in F, or the scorer read no artifact"
        )


def assert_an_explicit_scorer_replaced_the_reference(
    assessment: DebtAssessment,
) -> None:
    """The override path: the reference produced **none** of this assessment.

    Stated as an absence of the SDK's identities rather than as a presence of
    the deployment's, because "the override was honoured" and "the reference was
    not silently layered underneath it" are different claims and only the second
    is what the override path promises.
    """
    reference_ids = {identity for identity, _version in REFERENCE_PINS.values()}
    intruders = sorted(
        pin.factor for pin in assessment.scorers if pin.scorer_id in reference_ids
    )
    if intruders or not assessment.scorers:
        raise AssertionError(
            "an explicit `debt_scorer` did not replace the SDK's reference:"
            f" the served product's pins are"
            f" {[(pin.factor, pin.scorer_id) for pin in assessment.scorers]},"
            f" and the reference still accounts for {intruders}. An override"
            " replaces the reference entirely; a product carrying no pin at all"
            " names no producer for a number it delivers, which is the same"
            " failure seen from the other side"
        )


def assert_construction_is_refused(
    build: Callable[[], GovernedResolver], *, naming: tuple[str, ...]
) -> None:
    """Building a resolver this way must raise, and the message must say which.

    Takes the *attempt* as a parameter, so a control can hand it an attempt that
    succeeds and watch this assertion go red — the shape a ``pytest.raises``
    written inline cannot be sabotaged into.
    """
    try:
        build()
    except TypeError as refused:
        message = str(refused)
        unnamed = [name for name in naming if name not in message]
        if unnamed:
            raise AssertionError(
                f"the refusal does not name {unnamed} — an adopter told only"
                " that a construction is invalid has to guess which of four"
                f" values to supply. The message was: {message}"
            ) from refused
        return
    raise AssertionError(
        "the construction was accepted. A resolver built with no scorer and no"
        " material to build one has no way to measure `D_c`, so the only thing"
        " left for it to do is serve an unscored product — the failure the"
        " 2026-08-16 spec's Risk 3 names"
    )


# --- fixtures ---------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class _Booted:
    """A booted fixture deployment plus the pieces a resolver is wired from."""

    fabric: BootedFabric
    control_plane: ControlPlaneRegistry
    store: FileArtifactStore


def _boot(tmp_path: pathlib.Path, name: str) -> Iterator[_Booted]:
    """Write the fixture deployment plus this module's artifacts, and boot it."""
    root = tmp_path / name
    root.mkdir()
    for _key, filename, _class_id, _role, _registration, document in ARTIFACT_SET:
        write_artifact(root, filename, document)
    for _key, filename, _class_id, document in EXTRA_ARTIFACTS:
        write_artifact(root, filename, document)
    body = manifest_document()
    body["artifacts"] = [
        *body["artifacts"],
        *(
            {
                "path": filename,
                "key": key,
                "class_id": class_id,
                "role": "load" if key == REQUEST_CONTRACT_KEY else "register",
                "registration": "typed",
            }
            for key, filename, class_id, _document in EXTRA_ARTIFACTS
        ),
    ]
    manifest = write_artifact(root, "manifest.yaml", body)
    control_plane = ControlPlaneRegistry()
    fabric = load_and_boot(
        manifest,
        registry=control_plane,
        connection={"database_path": str(root / "graph.sqlite3")},
    )
    try:
        # The graph is **populated before a resolver exists**, and it has to be:
        # the manifest's signal batch is `role: load` (`D-IMPL-80`), so booting
        # parses the envelopes and writes none of them. An unpopulated graph
        # takes the scorer's empty-assembly branch, where every factor is zero
        # and no pin is carried — and this whole module would then be asserting
        # things about a view nothing was measured over.
        for envelope in fabric.artifacts[SIGNAL_BATCH_KEY].envelopes:
            fabric.handle.worker.ingest(envelope)
        yield _Booted(
            fabric=fabric,
            control_plane=control_plane,
            store=FileArtifactStore(root=root / "artifacts"),
        )
    finally:
        fabric.handle.close()


@pytest.fixture()
def booted(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """One booted deployment carrying both λ_c tables and the debt profile."""
    yield from _boot(tmp_path, "deployment")


# --- driving the seam -------------------------------------------------------


def _arguments(booted: _Booted, **overrides: Any) -> dict[str, Any]:
    """The data-only call: every value the helper needs, and no scorer."""
    arguments: dict[str, Any] = {
        "fabric": booted.fabric,
        "control_plane": booted.control_plane,
        "product_class_key": PRODUCT_CLASS_KEY,
        "request_contract_key": REQUEST_CONTRACT_KEY,
        "operator_parameter_keys": (TRAVERSAL_KEY,),
        "policy_bundle_key": POLICY_BUNDLE_KEY,
        "plan_factory": _plan_factory,
        "artifact_store": booted.store,
        "replay_record_class": REPLAY_RECORD_CLASS,
        "query_pin_class": QUERY_PIN_CLASS,
        "max_ttl_seconds": MAX_TTL_SECONDS,
        "product_ttl_seconds": PRODUCT_TTL_SECONDS,
        "half_life_key": HALF_LIFE_KEY,
        "debt_profile_key": DEBT_PROFILE_KEY,
        "declared_completeness": DECLARED_COMPLETENESS,
        "declared_semantic_consistency": DECLARED_SEMANTIC_CONSISTENCY,
    }
    arguments.update(overrides)
    return arguments


def _without(arguments: Mapping[str, Any], *names: str) -> dict[str, Any]:
    return {key: value for key, value in arguments.items() if key not in names}


def _served(resolver: GovernedResolver) -> ServedProduct:
    """Ask one answerable question and insist on a served product."""
    outcome = resolver(
        tenant=TENANT,
        product_class=PRODUCT_CLASS,
        version=PRODUCT_VERSION,
        perspective=PERSPECTIVE,
        request=ProductRequest(
            schema_name=PRODUCT_CLASS,
            schema_version=PRODUCT_VERSION,
            subject="acct-1",
            intent="fixture-intent",
            freshness="fixture-freshness",
            asked_at=ASKED_AT,
            parameters={THRESHOLD_PARAMETER: 1000},
        ),
    )
    assert isinstance(outcome, ServedProduct), outcome
    return outcome


def _assessment(booted: _Booted, **overrides: Any) -> DebtAssessment:
    """The debt a served product carries, built through the shipped helper."""
    return _served(
        build_governed_resolver(**_arguments(booted, **overrides))
    ).product.debt


# ---------------------------------------------------------------------------
# The honest subject, first — every control below expects a failure, and an
# expectation of failure is satisfied by a fixture that never worked.
# ---------------------------------------------------------------------------


def test_the_data_only_construction_satisfies_every_assertion(
    booted: _Booted, tmp_path: pathlib.Path
) -> None:
    """No `debt_scorer` passed, and the SDK's reference produced the number."""
    slower = _assessment(booted)

    assert_the_reference_scorer_produced_the_assessment(slower)

    for faster in _second_deployment(tmp_path, half_life_key=FAST_HALF_LIFE_KEY):
        assert_the_half_life_artifact_reached_the_measurement(slower, faster)

    assert_an_explicit_scorer_replaced_the_reference(
        _assessment(
            booted,
            **_scorer_only(),
        )
    )
    assert_construction_is_refused(
        lambda: build_governed_resolver(
            **_without(_arguments(booted), *DEBT_SCORER_INPUTS)
        ),
        naming=DEBT_SCORER_INPUTS,
    )


def _scorer_only() -> dict[str, Any]:
    """The override call: a scorer, and none of the four data inputs."""
    return {
        "debt_scorer": _override_scorer,
        **dict.fromkeys(DEBT_SCORER_INPUTS, None),
    }


def _second_deployment(
    tmp_path: pathlib.Path, **overrides: Any
) -> Iterator[DebtAssessment]:
    """A second, separately-booted deployment's assessment.

    Separate because the single-writer invariant makes one graph one fabric —
    the two λ_c tables live in one manifest, but a resolver is built per fabric
    and the comparison needs two answers, not one fabric asked twice.
    """
    for second in _boot(tmp_path, "second-deployment"):
        yield _assessment(second, **overrides)


# ---------------------------------------------------------------------------
# Property 1 — the reference is what a data-only construction selects.
# ---------------------------------------------------------------------------


def test_the_default_is_selected_when_no_scorer_is_passed(booted: _Booted) -> None:
    """The effect, not the attribute: the served product names its producers."""
    assessment = _assessment(booted)

    assert_the_reference_scorer_produced_the_assessment(assessment)


def test_the_default_reports_a_measured_number_rather_than_a_placeholder(
    booted: _Booted,
) -> None:
    """The reference actually computed: F is neither 0 nor 1 over this fixture.

    The fixture's one row is observed exactly one half-life before the question
    is asked, so a scorer honouring the artifact reports the midpoint. Asserted
    because both endpoints are what a scorer that did nothing would report — 1
    for "assume fresh", 0 for the empty-assembly branch — and either would
    satisfy a test that only checked the pins.
    """
    assessment = _assessment(booted)

    assert assessment.factors.freshness == Decimal("0.5"), assessment
    assert assessment.factors.completeness == DECLARED_COMPLETENESS
    assert assessment.factors.semantic_consistency == DECLARED_SEMANTIC_CONSISTENCY
    assert assessment.debt == Decimal("0.5")


def test_the_selection_control_fires_when_the_default_is_made_inert(
    booted: _Booted, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CONTROL — the helper selects something inert, and the assertion goes red.

    The substitution is made at the **name the helper reaches for**, so this
    tests the selection rather than a different input: an
    ``AssemblyDebtScorer`` that answers without pinning anyone is precisely what
    "the default silently stopped being wired" looks like from the outside.
    """
    monkeypatch.setattr(resolver_module, "AssemblyDebtScorer", _InertScorer)

    assessment = _assessment(booted)

    with pytest.raises(AssertionError) as fired:
        assert_the_reference_scorer_produced_the_assessment(assessment)

    assert "not produced by the SDK's reference scorer" in str(fired.value)


def test_the_selection_control_fires_on_an_assessment_with_no_pins() -> None:
    """CONTROL — **the empty case**. ``{}`` must fail, not iterate over nothing."""
    with pytest.raises(AssertionError) as fired:
        assert_the_reference_scorer_produced_the_assessment(
            DebtAssessment(
                debt=Decimal("0"),
                signal=DebtSignal.OK,
                factors=DebtFactors(
                    freshness=Decimal("1"),
                    completeness=Decimal("1"),
                    semantic_consistency=Decimal("1"),
                ),
                scorers=NO_SCORER_PINS,
            )
        )

    assert "pins {}" in str(fired.value)


def test_the_selection_control_fires_on_a_stale_pinned_version(
    booted: _Booted,
) -> None:
    """CONTROL — right scorer ids, wrong versions. `D-IMPL-47`'s actual point.

    A replay resolving a scorer at a version the decision did not use re-derives
    the number under a different computation and presents it as the one in
    force. So the version is compared, not merely the id.
    """
    honest = _assessment(booted)
    restamped = honest.model_copy(
        update={
            "scorers": tuple(
                pin.model_copy(update={"scorer_version": "9.9.9"})
                for pin in honest.scorers
            )
        }
    )

    with pytest.raises(AssertionError) as fired:
        assert_the_reference_scorer_produced_the_assessment(restamped)

    assert "9.9.9" in str(fired.value)


# ---------------------------------------------------------------------------
# Property 2 — the Control Plane artifact reaches the number.
# ---------------------------------------------------------------------------


def test_the_half_life_artifact_moves_the_freshness_the_product_carries(
    booted: _Booted, tmp_path: pathlib.Path
) -> None:
    """Two deployments, one difference: which λ_c table `half_life_key` names."""
    slower = _assessment(booted)

    for faster in _second_deployment(tmp_path, half_life_key=FAST_HALF_LIFE_KEY):
        assert_the_half_life_artifact_reached_the_measurement(slower, faster)
        assert faster.factors.freshness < Decimal("0.01"), faster


def test_the_half_life_control_fires_on_two_identical_numbers(
    booted: _Booted,
) -> None:
    """CONTROL — a scorer that read no artifact reports one number twice.

    The divergent subject here is a **pair that does not diverge**, which is
    what the failure actually looks like: the assertion is handed the same
    honest assessment on both sides.
    """
    honest = _assessment(booted)

    with pytest.raises(AssertionError) as fired:
        assert_the_half_life_artifact_reached_the_measurement(honest, honest)

    assert "did not reach the measurement" in str(fired.value)


def test_the_half_life_control_fires_when_the_ordering_inverts(
    booted: _Booted, tmp_path: pathlib.Path
) -> None:
    """CONTROL — two different numbers in the wrong order still fail.

    Without this, ``!=`` would have been enough and the assertion would pass on
    a scorer whose freshness moved for a reason having nothing to do with decay.
    """
    slower = _assessment(booted)

    for faster in _second_deployment(tmp_path, half_life_key=FAST_HALF_LIFE_KEY):
        with pytest.raises(AssertionError) as fired:
            assert_the_half_life_artifact_reached_the_measurement(faster, slower)

        assert "must be the smaller" in str(fired.value)


# ---------------------------------------------------------------------------
# The override path — the default is a default, not a fixture.
# ---------------------------------------------------------------------------


def test_an_explicit_scorer_overrides_the_default(booted: _Booted) -> None:
    """A deployment's own scorer produces the number, and pins itself for it."""
    assessment = _assessment(booted, **_scorer_only())

    assert_an_explicit_scorer_replaced_the_reference(assessment)
    assert assessment.factors.freshness == OVERRIDE_FRESHNESS
    assert {pin.scorer_id for pin in assessment.scorers} == {OVERRIDE_SCORER_ID}


def test_the_override_and_the_default_produce_different_products(
    booted: _Booted, tmp_path: pathlib.Path
) -> None:
    """The two paths are distinguishable **on the wire**, not just in a pin.

    Debt rides inside the served vessel, so a scorer substitution moves the
    product's content address. That is what makes "which scorer was in force"
    an auditable fact about a delivered product rather than a fact about a
    process nobody recorded.
    """
    from ccf.contracts.canonical import content_hash

    default = _served(build_governed_resolver(**_arguments(booted)))

    for second in _boot(tmp_path, "second-deployment"):
        override = _served(
            build_governed_resolver(**_arguments(second, **_scorer_only()))
        )

        assert content_hash(default.product) != content_hash(override.product)


def test_the_override_control_fires_on_a_reference_produced_assessment(
    booted: _Booted,
) -> None:
    """CONTROL — the override assertion handed a default-produced subject."""
    with pytest.raises(AssertionError) as fired:
        assert_an_explicit_scorer_replaced_the_reference(_assessment(booted))

    assert "did not replace the SDK's reference" in str(fired.value)


def test_the_override_control_fires_on_an_unpinned_assessment() -> None:
    """CONTROL — **the empty case** for the override half.

    An override honoured but pinning nobody is not the property the override
    path promises: the product would deliver a number whose producer no replay
    can name.
    """
    with pytest.raises(AssertionError) as fired:
        assert_an_explicit_scorer_replaced_the_reference(
            DebtAssessment(
                debt=Decimal("0"),
                signal=DebtSignal.OK,
                factors=DebtFactors(
                    freshness=Decimal("1"),
                    completeness=Decimal("1"),
                    semantic_consistency=Decimal("1"),
                ),
                scorers=NO_SCORER_PINS,
            )
        )

    assert "names no producer" in str(fired.value)


# ---------------------------------------------------------------------------
# The two refused argument shapes.
# ---------------------------------------------------------------------------


def test_no_scorer_and_no_material_is_refused_rather_than_defaulted(
    booted: _Booted,
) -> None:
    """The load-bearing refusal: no silent unscored product.

    This is the negative half of the whole plan. A helper that accepted this
    call would have to serve a product with no measured debt, and a consumer
    reading ``result.debt`` would have no way to tell that from a measurement.
    """
    assert_construction_is_refused(
        lambda: build_governed_resolver(
            **_without(_arguments(booted), *DEBT_SCORER_INPUTS)
        ),
        naming=DEBT_SCORER_INPUTS,
    )


@pytest.mark.parametrize("omitted", DEBT_SCORER_INPUTS)
def test_omitting_any_one_of_the_four_is_refused_and_names_it(
    booted: _Booted, omitted: str
) -> None:
    """Partial material is refused too, and the message names what is missing.

    Parameterized over the shipped tuple, so a fifth input added to the
    reference scorer gets its own control the day it is declared rather than
    the day somebody remembers.
    """
    assert_construction_is_refused(
        lambda: build_governed_resolver(**_without(_arguments(booted), omitted)),
        naming=(omitted,),
    )


def test_supplying_both_a_scorer_and_the_material_is_refused(
    booted: _Booted,
) -> None:
    """Silently ignoring four supplied arguments is how wiring lies.

    A deployment that passed a λ_c key **and** a scorer would otherwise believe
    the key was in force. It is not, and it never could be — an explicit scorer
    replaces the reference entirely.
    """
    assert_construction_is_refused(
        lambda: build_governed_resolver(
            **_arguments(booted, debt_scorer=_override_scorer)
        ),
        naming=("half_life_key", "debt_scorer"),
    )


def test_the_named_inputs_are_this_helper_s_own_optional_parameters() -> None:
    """`DEBT_SCORER_INPUTS` and the signature are held to each other, both ways.

    The constant is what both refusal messages enumerate and what the controls
    above parameterize over, and the helper indexes a name-keyed mapping with
    it. A name added to the signature and not to the constant would be a value
    no refusal mentions and no control covers; a name in the constant and not in
    the signature would raise a ``KeyError`` inside the helper. Neither is
    something a reader would notice, so it is asserted rather than intended.

    ``Ellipsis`` is not used as the sentinel: the check is *"defaults to
    ``None``"*, which is exactly the property that makes an argument optional
    here, and ``debt_scorer`` is excluded by name because it is the alternative
    to the four rather than one of them.
    """
    import inspect

    optional = tuple(
        name
        for name, parameter in inspect.signature(
            build_governed_resolver
        ).parameters.items()
        if parameter.default is None and name != "debt_scorer"
    )

    assert optional == DEBT_SCORER_INPUTS, (
        "`DEBT_SCORER_INPUTS` and `build_governed_resolver`'s optional"
        f" parameters have come apart — the signature offers {optional} and the"
        f" constant names {DEBT_SCORER_INPUTS}"
    )


def test_the_refusal_control_fires_on_a_construction_that_succeeds(
    booted: _Booted,
) -> None:
    """CONTROL — the refusal assertion handed an attempt that does not raise."""
    with pytest.raises(AssertionError) as fired:
        assert_construction_is_refused(
            lambda: build_governed_resolver(**_arguments(booted)),
            naming=DEBT_SCORER_INPUTS,
        )

    assert "the construction was accepted" in str(fired.value)


def test_the_refusal_control_fires_on_a_message_that_names_nothing(
    booted: _Booted,
) -> None:
    """CONTROL — a refusal that raises but says nothing useful still fails.

    An adopter told only *"invalid construction"* has to guess which of four
    values to supply, so the message content is part of the contract rather
    than decoration.
    """

    def _mute() -> GovernedResolver:
        raise TypeError("no.")

    with pytest.raises(AssertionError) as fired:
        assert_construction_is_refused(_mute, naming=DEBT_SCORER_INPUTS)

    assert "does not name" in str(fired.value)


# ---------------------------------------------------------------------------
# THE UNRESOLVABLE CASE — a key that names nothing, and one that names the
# wrong class. Both are broken deployments and both must say so.
# ---------------------------------------------------------------------------


def test_a_half_life_key_naming_no_artifact_is_refused_naming_both_sides(
    booted: _Booted,
) -> None:
    """A key is a string, and a mistyped one must not surface three frames on."""
    with pytest.raises(ProductNotResolvable) as fired:
        build_governed_resolver(
            **_arguments(booted, half_life_key="fixture/nothing-is-here")
        )

    message = str(fired.value)
    assert "fixture/nothing-is-here" in message
    assert HALF_LIFE_KEY in message, "the refusal does not list what is declared"


def test_a_debt_profile_key_naming_another_class_is_refused(
    booted: _Booted,
) -> None:
    """The narrowing, not merely the presence check.

    A key that resolves to *an* artifact of the wrong class is the mistake a
    presence check cannot see, and it would otherwise fail inside the scorer
    with a message about a missing attribute.
    """
    with pytest.raises(ProductNotResolvable) as fired:
        build_governed_resolver(
            **_arguments(booted, debt_profile_key=HALF_LIFE_KEY)
        )

    message = str(fired.value)
    assert "HalfLifeTable" in message
    assert "DebtProfile" in message


def test_the_reference_refuses_an_entity_class_with_no_declared_half_life(
    booted: _Booted,
) -> None:
    """A λ_c table that does not cover what was assembled fails loudly.

    ``INV-CH7-58``: substituting a rate would report a freshness figure the
    deployment never calibrated. Asserted **through the resolver**, because a
    default that turned a missing calibration into a plausible number is the
    same defect class as one nothing exercises.
    """
    from ccf.halflife.decay import MissingHalfLife

    with pytest.raises(MissingHalfLife):
        _assessment(
            booted,
            half_life_key=_uncalibrated_key(booted),
        )


def _uncalibrated_key(booted: _Booted) -> str:
    """The stock fixture's λ_c table, which declares no row for `account`.

    Reached off the booted fabric rather than spelled, so this control keeps
    naming a genuinely uncalibrated table even if the stock fixture's own
    vocabulary is renamed.
    """
    from ccf.controlplane.artifacts import HalfLifeTable

    for key, artifact in booted.fabric.artifacts.items():
        if isinstance(artifact, HalfLifeTable) and ENTITY_CLASS not in artifact.entries:
            return key
    raise AssertionError(
        "every λ_c table on the fixture fabric now covers"
        f" {ENTITY_CLASS!r}, so this control has nothing uncalibrated to point"
        " at and would pass while proving nothing"
    )
