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

import copy
import dataclasses
import pathlib
from tests.composition import no_erasures
from collections.abc import Callable, Iterator, Mapping
from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.erasure import ErasureConsultingStore
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
from ccf.products.contract import ContextProductContract
from ccf.products.debt_scorer import (
    DECLARED_FACTOR_SCORER_ID,
    DECLARED_FACTOR_SCORER_VERSION,
    ExecutionEvidence,
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
from tests.composition import declare_wide_temporal_boundary, declaring_store
from ccf.products.composite import ADMITTED_CHILD_CONTRACT_CLASS

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
HALF_LIFE_KEY = "tenant-fixture/half-life/account"
FAST_HALF_LIFE_KEY = "tenant-fixture/half-life/account-decays-faster"

#: The bands this fixture routes on. A profile, not a threshold the SDK chose.
DEBT_PROFILE_KEY = "tenant-fixture/debt-profile"

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

    def __call__(
        self, *, view: GraphView, evidence: ExecutionEvidence | None = None
    ) -> DebtAssessment:
        # `evidence` accepted and unread: 24.6-05 widened the seam
        # (`AssemblyDebtScorerProtocol`), and a stand-in that did not accept
        # the keyword would fail on the seam rather than on the selection this
        # class exists to test.
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


def _override_scorer(
    *, view: GraphView, evidence: ExecutionEvidence | None = None
) -> DebtAssessment:
    """A deployment's own scorer, pinning itself under its own identity.

    Accepts ``evidence`` and reads none: 24.6-05 widened the seam, and this
    scorer's subject is that the OVERRIDE was selected, not what it measured.
    """
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


def _boot(
    tmp_path: pathlib.Path,
    name: str,
    *,
    extra: tuple[tuple[str, str, str, dict[str, Any]], ...] = (),
    product_class: dict[str, Any] | None = None,
) -> Iterator[_Booted]:
    """Write the fixture deployment plus this module's artifacts, and boot it.

    ``extra`` appends artifacts beyond :data:`EXTRA_ARTIFACTS`, in the same
    ``key, filename, class_id, document`` shape. `24.10-01` needs a fabric
    carrying a `ccf.replay-binding` and a second one carrying two of them, and
    a parameter is cheaper than a second copy of this function that would then
    have to be kept in step with it.

    ``product_class`` replaces the fixture deployment's class document.
    `24.10-02` / `R-11` needs a deployment whose class DECLARES a runtime gate,
    so that the build-time refusal for a declared gate with no supplied
    callable has something to fire on. Same argument as ``extra``: a parameter
    rather than a second boot that would drift, and the shape is the one
    ``tests/products/test_resolver_seam.py::_boot`` already carries.
    """
    root = tmp_path / name
    root.mkdir()
    for key, filename, _class_id, _role, _registration, document in ARTIFACT_SET:
        if key == PRODUCT_CLASS_KEY and product_class is not None:
            document = product_class
        write_artifact(root, filename, document)
    for _key, filename, _class_id, document in (*EXTRA_ARTIFACTS, *extra):
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
            for key, filename, class_id, _document in (*EXTRA_ARTIFACTS, *extra)
        ),
    ]
    manifest = write_artifact(root, "manifest.yaml", body)
    control_plane = ControlPlaneRegistry()
    fabric = load_and_boot(
        manifest,
        registry=control_plane,
        connection={"database_path": str(root / "graph.sqlite3")},
    )
    # `D-IMPL-358` step 5 ruling 11: a deployment declaring no temporal boundary
    # refuses every question, so a fixture that means to serve declares one. Wide
    # on purpose — the window is not what these tests are about.
    declare_wide_temporal_boundary(control_plane, tenant_id=fabric.tenant_id)
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
            store=declaring_store(
                root / "artifacts",
                REPLAY_RECORD_CLASS,
                QUERY_PIN_CLASS,
                DECLARED_RECORD_CLASS,
                DECLARED_QUERY_PIN_CLASS,
                "fixture.explicit-replay-record",
                "fixture.explicit-graph-query",
                ADMITTED_CHILD_CONTRACT_CLASS,
            ),
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
        "erasure_index": no_erasures(),
        "product_class_key": PRODUCT_CLASS_KEY,
        "request_contract_key": REQUEST_CONTRACT_KEY,
        "operator_parameter_keys": (TRAVERSAL_KEY,),
        "policy_bundle_key": POLICY_BUNDLE_KEY,
        "plan_factory": _plan_factory,
        # `D-IMPL-358` step 5 section H, class 1. THE FABRIC CLOCK, pinned to
        # THIS MODULE'S OWN question instant — `ASKED_AT`, imported from the seam
        # module, not a new fixture time. Without it `served_at` is the real wall
        # clock while every question here is asked at a fictional instant, so a
        # product's expiry (which runs from the decision) lies months in the past
        # by the time Gate 3 compares it against the moment of service.
        #
        # One clock per composition, and it is the same instant the questions
        # name: that is what makes these tests about their own subjects rather
        # than about how far today is from March.
        "admission_clock": lambda: ASKED_AT,
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
    here.

    **The exclusions are named, and their presence is asserted** (re-derived at
    ``24.6-03``). Three optional parameters are not debt-scorer material:
    ``debt_scorer``, which is the alternative to the four rather than one of
    them, and the Authority layer's ``constraint_resolver`` and
    ``capabilities``, which the helper defaults from the deployment it was
    handed rather than from supplied material. Excluding them by a named tuple
    whose members must each *be* in the signature is what keeps the exclusion
    from silently widening: a typo would drop a name out of the comparison and
    leave this test green, so the typo is what fails instead.
    """
    import inspect

    not_debt_scorer_material = (
        "debt_scorer",
        # `D-IMPL-341`: the λ_c table key stated for the resolver when the
        # scorer is supplied — the resolver anchors an evidence-anchored expiry
        # on that table and pins it; it is not scorer material.
        "evidence_clock_key",
        "constraint_resolver",
        "capabilities",
        # `D-IMPL-336` Amendment 3, F0. How a deployment resolves, invokes and
        # admits the children a composite class declares — orchestration, not
        # debt-scorer material. Optional on THIS helper and required on the
        # resolver itself: the dataclass forbids defaults so a deployment
        # states its posture, while the helper keeps the non-composite default
        # every product shipped before the surface existed.
        "composite_children",
        # `24.10-01` / `R-12`. Four more optional parameters that are not
        # debt-scorer material: the three replay members the Control Plane's
        # `replay:` section can supply, and the root the declared
        # `store_dirname` is joined onto. They became optional under
        # `D-IMPL-282`'s *"no builder API break in 24.10"* — a call passing
        # them behaves exactly as it did — and they default from the
        # deployment's own declaration rather than from supplied material,
        # which is the same reason `constraint_resolver` and `capabilities`
        # are excluded.
        "artifact_store",
        "replay_record_class",
        "query_pin_class",
        "artifact_store_root",
        # `24.10-02` / `R-11`. An eighth, and it is not debt-scorer material
        # for a reason none of the others has: it has no reference
        # implementation and cannot have one. `debt_scorer` defaults to
        # machinery the SDK ships; `product_gate` is declared-versus-supplied,
        # and BOTH mismatches are refused at build time rather than defaulted
        # (`D-IMPL-282` option 1a). Its `None` default is what lets a class
        # declaring no gate call this helper exactly as it always did.
        "product_gate",
        # `24.11-02b` / `D-IMPL-292`. There is deliberately no ninth. `24.11-02`
        # added `similarity_index_version` here and Dave ruled it insufficient:
        # a corpus's version identity is decision-affecting operator
        # configuration, so it is declared on the similarity artifact and this
        # helper takes no argument for it. The exclusion roster shrinking is
        # the repair, not an omission from it.
        #
        # `D-IMPL-308`. A ninth, and it is not debt-scorer material for the
        # same reason `product_gate` is not: it is a DECLARATION about the
        # class rather than material a scorer consumes. `None` here means *this
        # class declares no decision instant distinct from its graph boundary*
        # — a positive statement the dataclass requires, which is why the field
        # behind it carries no default even though this parameter does.
        # `source_refresh_recency` is its sibling and is absent from this
        # roster because it defaults to `NO_SOURCE_REFRESH_RECENCY` rather than
        # to `None`, so the comparison below never sees it.
        "decision_instant_parameter",
        # Its sibling, and it lands here after all: `NO_SOURCE_REFRESH_RECENCY`
        # IS `None`, so the comparison below sees this parameter exactly as it
        # sees the other eight. Measured rather than assumed — the first draft
        # of this roster left it out on the belief that the sentinel was a
        # distinct object, and the guard said otherwise.
        "source_refresh_recency",
        # `D-IMPL-343` R-3a (`D-IMPL-292` applied): the two TTL figures became
        # optional so a deployment's declared `ttl:` binding can supply them —
        # a declaration, not scorer material, and held EQUAL to the call when
        # both speak. `refusal_recorder` and `acquisition` are the paved
        # road's two seams onto this helper: the ONE recorder a deployment
        # already holds, and the declared acquisition boundary (R-4). Each
        # defaults to the posture every earlier call had — the SDK's own
        # recorder, and no seam — not from supplied material.
        "max_ttl_seconds",
        "product_ttl_seconds",
        "refusal_recorder",
        "acquisition",
        # `PKG-F-08`. §7.10.4's Mode 2 footprint — what this deployment's
        # packaging stage did — and not debt-scorer material. The same shape
        # as `composite_children` above: optional on THIS helper so every
        # Mode 1 product shipped before the seam existed keeps building, and
        # REQUIRED on the resolver itself, because a default there made "no
        # packaging happened" and "nobody wired the seam" the same
        # construction.
        "packaging_trace",
    )
    parameters = inspect.signature(build_governed_resolver).parameters
    for name in not_debt_scorer_material:
        assert name in parameters, (
            f"{name!r} is excluded from this comparison but is not a parameter"
            " of the helper — an exclusion that names nothing silently widens"
            " what the comparison covers"
        )
        assert parameters[name].default is None, name

    optional = tuple(
        name
        for name, parameter in parameters.items()
        if parameter.default is None and name not in not_debt_scorer_material
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
            **_arguments(booted, half_life_key="tenant-fixture/nothing-is-here")
        )

    message = str(fired.value)
    assert "tenant-fixture/nothing-is-here" in message
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


def test_the_disclosure_reader_treats_only_a_missing_key_as_no_policy() -> None:
    """`(minimal, None)` means *no policy is registered* — and only that.

    Phase 24.6 close panel: the reader caught EVERY exception from the registry
    and answered `(minimal, None)`, so a registry that failed to read its policy
    would have been recorded as a tenant that registered none — a false
    provenance claim on replay dimension 5. Minimal is still the safe level; the
    claim about WHY is what must be true.
    """
    from ccf.controlplane.registry import ControlPlaneMissing
    from ccf.products.disclosure import DISCLOSURE_MINIMAL

    class _Missing:
        def resolve_latest(self, key: str) -> tuple[str, object]:
            raise ControlPlaneMissing(key)

    class _Broken:
        def resolve_latest(self, key: str) -> tuple[str, object]:
            raise RuntimeError("the registry's storage is unreachable")

    missing = resolver_module._disclosure_reader(_Missing())  # type: ignore[arg-type]
    assert missing(tenant="t", principal_id="p") == (DISCLOSURE_MINIMAL, None)

    broken = resolver_module._disclosure_reader(_Broken())  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="unreachable"):
        broken(tenant="t", principal_id="p")



# ---------------------------------------------------------------------------
# `24.10-01` / `R-12` — the Control Plane's replay binding, at the helper.
#
# `D-IMPL-282` `R-12` option 2a (Dave, 2026-09-08) rules the precedence:
#
#     explicit builder argument > Control Plane replay binding
#     > no binding/refusal according to existing availability semantics
#
# and *"Do not silently invent a replay backend when neither source provides
# one."* What is asserted below is the helper's own resolution and its refusal
# surface; `tests/deployment/test_replay_binding.py` carries the end-to-end
# evidence that a served product's record actually lands where the declaration
# said it would, which is the `D-06` bar this seam exists to clear.
# ---------------------------------------------------------------------------

#: The manifest key the fixture deployment declares its binding under, and the
#: three values it declares. Test-side vocabulary (CINV-01); the values are
#: shaped like cp-05's so the two modules read as the same subject.
REPLAY_BINDING_KEY = "tenant-fixture/replay-binding"
SECOND_REPLAY_BINDING_KEY = "tenant-fixture/replay-binding-also"
DECLARED_RECORD_CLASS = "fixture.declared-replay-record"
DECLARED_QUERY_PIN_CLASS = "fixture.declared-graph-query"
DECLARED_STORE_DIRNAME = "declared-artifacts-store"


def _replay_binding_document() -> dict[str, Any]:
    return {
        "semver": "1.0.0",
        "record_class": DECLARED_RECORD_CLASS,
        "query_pin_class": DECLARED_QUERY_PIN_CLASS,
        "store_dirname": DECLARED_STORE_DIRNAME,
    }


ONE_BINDING: tuple[tuple[str, str, str, dict[str, Any]], ...] = (
    (
        REPLAY_BINDING_KEY,
        "replay-binding.yaml",
        "ccf.replay-binding",
        _replay_binding_document(),
    ),
)

TWO_BINDINGS: tuple[tuple[str, str, str, dict[str, Any]], ...] = (
    *ONE_BINDING,
    (
        SECOND_REPLAY_BINDING_KEY,
        "replay-binding-also.yaml",
        "ccf.replay-binding",
        _replay_binding_document(),
    ),
)


@pytest.fixture()
def booted_with_binding(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """The same deployment, carrying one declared replay binding."""
    yield from _boot(tmp_path, "declared", extra=ONE_BINDING)


@pytest.fixture()
def booted_with_two_bindings(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """The same deployment, carrying two — the ambiguity the helper refuses."""
    yield from _boot(tmp_path, "ambiguous", extra=TWO_BINDINGS)


def _without_the_three(booted: _Booted, **overrides: Any) -> dict[str, Any]:
    """The data-only call with none of the three replay members supplied."""
    return _without(
        _arguments(booted, **overrides),
        "artifact_store",
        "replay_record_class",
        "query_pin_class",
    )


def test_the_declared_binding_supplies_every_member_the_call_omits(
    booted_with_binding: _Booted, tmp_path: pathlib.Path
) -> None:
    """The honest subject, first. Every refusal below expects a failure, and an
    expectation of failure is satisfied by a wiring that never worked."""
    root = tmp_path / "roots" / "declared"
    resolver = build_governed_resolver(
        **_without_the_three(booted_with_binding, artifact_store_root=root)
    )

    assert resolver.replay_record_class == DECLARED_RECORD_CLASS
    assert resolver.query_pin_class == DECLARED_QUERY_PIN_CLASS
    # SEC-009 ruling 2: the selected store is composed with the erasure consult.
    assert isinstance(resolver.artifact_store, ErasureConsultingStore)
    assert isinstance(resolver.artifact_store.inner, FileArtifactStore)
    assert resolver.artifact_store.inner.root == root / DECLARED_STORE_DIRNAME


def test_an_explicit_argument_beats_the_declaration_for_that_member_alone(
    booted_with_binding: _Booted, tmp_path: pathlib.Path
) -> None:
    """Precedence is per MEMBER, which is why the call is mixed.

    A call naming only `replay_record_class` takes the explicit record class
    and the declared query-pin class and store. A per-*call* precedence would
    satisfy the first assertion and fail the other two.
    """
    root = tmp_path / "roots" / "mixed"
    resolver = build_governed_resolver(
        **_without_the_three(booted_with_binding, artifact_store_root=root),
        replay_record_class="fixture.explicit-replay-record",
    )

    assert resolver.replay_record_class == "fixture.explicit-replay-record"
    assert resolver.query_pin_class == DECLARED_QUERY_PIN_CLASS
    # SEC-009 ruling 2: the selected store is composed with the erasure consult.
    assert isinstance(resolver.artifact_store, ErasureConsultingStore)
    assert isinstance(resolver.artifact_store.inner, FileArtifactStore)
    assert resolver.artifact_store.inner.root == root / DECLARED_STORE_DIRNAME


def test_a_call_supplying_all_three_is_unaffected_by_a_declaration(
    booted_with_binding: _Booted,
) -> None:
    """*"No builder API break in 24.10"* — the shipped call shape, measured.

    `ccf.client.adapters.inprocess` passes all three explicitly; so does every
    other test in this module. The declaration on the fabric must change none
    of them, and the store must be the OBJECT that was passed rather than one
    the helper built from a dirname.
    """
    resolver = build_governed_resolver(**_arguments(booted_with_binding))

    assert resolver.replay_record_class == REPLAY_RECORD_CLASS
    assert resolver.query_pin_class == QUERY_PIN_CLASS
    # SEC-009 ruling 2: the SUPPLIED store, composed with the erasure consult.
    assert resolver.artifact_store.inner is booted_with_binding.store


def test_neither_source_is_refused_naming_the_argument_and_the_section(
    booted: _Booted, tmp_path: pathlib.Path
) -> None:
    """`D-05` — *"Do not silently invent a replay backend."*

    The fabric carries no binding and the call names none of the three, so
    there is no source for any of them. Refused, and the message names both
    places the value could have come from: nobody reading it should have to
    guess whether the fix is an argument or a section.
    """
    with pytest.raises(TypeError) as refused:
        build_governed_resolver(
            **_without_the_three(booted, artifact_store_root=tmp_path)
        )

    message = str(refused.value)
    assert "replay_record_class" in message, message
    assert "replay" in message, message


def test_a_declared_store_with_no_root_is_refused_naming_both(
    booted_with_binding: _Booted,
) -> None:
    """A dirname is half a location. The other half is the caller's, and the
    SDK does not choose it — a root defaulted to the process's working
    directory would put a deployment's decision records wherever it happened
    to be started from."""
    with pytest.raises(TypeError) as refused:
        build_governed_resolver(**_without_the_three(booted_with_binding))

    message = str(refused.value)
    assert "artifact_store_root" in message, message
    assert "artifact_store" in message, message
    assert DECLARED_STORE_DIRNAME in message, message


def test_two_declared_bindings_are_refused_naming_every_key(
    booted_with_two_bindings: _Booted, tmp_path: pathlib.Path
) -> None:
    """Refusing beats picking — `_refuse_operator_set_divergence`'s posture.

    Only the deployment's author knows which of two declared bindings was
    meant, and picking the first would be a rule that silently changes behavior
    the day a second is registered.
    """
    with pytest.raises(TypeError) as refused:
        build_governed_resolver(
            **_without_the_three(
                booted_with_two_bindings, artifact_store_root=tmp_path
            )
        )

    message = str(refused.value)
    assert REPLAY_BINDING_KEY in message, message
    assert SECOND_REPLAY_BINDING_KEY in message, message


def test_two_declared_bindings_are_admitted_when_all_three_are_explicit(
    booted_with_two_bindings: _Booted,
) -> None:
    """The control on the ambiguity refusal: it fires on the RESOLUTION, not on
    the fabric. A deployment that declares two bindings and names all three
    arguments has asked nothing ambiguous, and refusing it would break a
    deployment that resolved its own ambiguity."""
    resolver = build_governed_resolver(**_arguments(booted_with_two_bindings))

    assert resolver.replay_record_class == REPLAY_RECORD_CLASS


# --- `R-11`: declared versus supplied, refused at build time -----------------
#
# Test-side vocabulary for the gate a class declares. `24.10-02` / `R-11`: the
# id and the lane are the DEPLOYMENT's, never the SDK's (CINV-01), so they are
# spelled here and nowhere in `src/`.

#: The fixture class's declared runtime invariant.
DECLARED_GATE_ID = "fixture.reconciliation-guard"
DECLARED_GATE_VERSION = "1.0.0"


def _product_class_declaring_a_gate() -> dict[str, Any]:
    """The fixture class document with a ``declared_product_gate`` block."""
    document = copy.deepcopy(
        next(doc for key, *_rest, doc in ARTIFACT_SET if key == PRODUCT_CLASS_KEY)
    )
    document["declared_product_gate"] = {
        "gate_id": DECLARED_GATE_ID,
        "gate_version": DECLARED_GATE_VERSION,
    }
    return document


@pytest.fixture()
def booted_declaring_a_gate(tmp_path: pathlib.Path) -> Iterator[_Booted]:
    """The same deployment, with the class DECLARING a runtime invariant."""
    yield from _boot(
        tmp_path, "declares-a-gate", product_class=_product_class_declaring_a_gate()
    )


def _admitting_gate(
    *,
    candidate: ContextProductContract,
    evidence: ExecutionEvidence | None = None,
) -> str | None:
    """A conforming gate that admits everything. Shape only; behavior is
    ``tests/products/test_runtime_product_gate.py``'s subject."""
    return None


def test_a_declared_gate_with_no_supplied_callable_is_refused(
    booted_declaring_a_gate: _Booted,
) -> None:
    """The half that matters (`D-IMPL-282` `R-11`; threat `T-24.10-02-02`).

    *"A default that nothing exercises is a check that stops checking without
    going red."* A class whose document declares a gate, built through the
    shipped helper with no callable, must not yield a resolver: an audit
    reading that declaration would report an invariant in force that had never
    run once, which is repudiation dressed as governance.

    The message names the class key, the declared id and the argument — the
    adopter has three places to look and only one of them is wrong.
    """
    with pytest.raises(TypeError) as refused:
        build_governed_resolver(**_arguments(booted_declaring_a_gate))

    message = str(refused.value)
    assert PRODUCT_CLASS_KEY in message, message
    assert DECLARED_GATE_ID in message, message
    assert DECLARED_GATE_VERSION in message, message
    assert "product_gate" in message, message


def test_a_supplied_callable_against_a_class_declaring_none_is_refused(
    booted: _Booted,
) -> None:
    """The other half (threat `T-24.10-02-01`).

    Refused rather than ignored: a deployment predicate running inside the
    determination path with no declared identity is a check the SDK could not
    name in a refusal record, so `D-14`'s *"which gate produced the refusal"*
    would have no answer. The stock fixture class declares no gate, which is
    what makes this the mirror of the test above rather than a second spelling
    of it.
    """
    with pytest.raises(TypeError) as refused:
        build_governed_resolver(
            **_arguments(booted, product_gate=_admitting_gate)
        )

    message = str(refused.value)
    assert PRODUCT_CLASS_KEY in message, message
    assert "declared_product_gate" in message, message


def test_a_declaring_class_with_its_callable_supplied_builds(
    booted_declaring_a_gate: _Booted,
) -> None:
    """The control on both refusals: the agreeing pair is admitted.

    Without it, a helper that refused every call carrying a gate — or every
    class declaring one — would satisfy the two refusal tests above. It also
    asserts what the resolver was given, so a helper that accepted the argument
    and dropped it on the floor fails here rather than in a behavior test three
    modules away.
    """
    resolver = build_governed_resolver(
        **_arguments(booted_declaring_a_gate, product_gate=_admitting_gate)
    )

    assert resolver.product_gate is _admitting_gate


def test_a_class_declaring_no_gate_and_a_call_naming_none_is_unaffected(
    booted: _Booted,
) -> None:
    """The compatibility control: every call written before `R-11` is untouched.

    `D-IMPL-282`'s *"no builder API break in 24.10"* applies here as it does to
    `R-12`. The stock deployment declares no gate and the stock call names no
    `product_gate`, and it builds a resolver whose gate is the positive `None`.
    """
    resolver = build_governed_resolver(**_arguments(booted))

    assert resolver.product_gate is None
