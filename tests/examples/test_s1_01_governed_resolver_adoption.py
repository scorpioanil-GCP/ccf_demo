"""What the SDK's own worked example meets when it tries the canonical path.

``24.10-04`` / ``R-03``, and this module **is** the row's result. ``D-IMPL-282``
(Dave, 2026-09-08) ruled ``s1-01`` open so that the question could be answered
by measurement rather than by opinion:

    *"If the SDK's own canonical worked example can move from a hand-built
    617-line governed spine to ``GovernedResolver`` with materially less
    plumbing, the surface has demonstrated usability. If it cannot, ``R-03``
    has earned escalation beyond docstrings."*

It cannot, and the four reasons are below. Each is a **seam the composition
does not have**, not a mistake in the example — which is why the instruction
that governs this module is Dave's next sentence:

    *"do not change s1-01's business behavior merely to make the resolver fit.
    If adopting ``GovernedResolver`` exposes a missing seam, preserve the
    evidence and classify it rather than working around the resolver."*

So nothing here works around anything. Each test states what **adoption would
require**, and a test whose seam is still absent carries ``xfail(strict=True)``
with its finding id — which makes the roster executable in both directions: it
fails today because the seam is absent, and it fails *loudly* — ``XPASS`` under
``strict`` — on the day a seam is added and the finding is not closed with it.
**A closed finding keeps its test, unmarked and otherwise unchanged**, so what
the SDK learned to do is asserted by the same words that recorded its absence.
Two are closed: ``24.10-F-07`` by ``24.11-01`` and ``24.10-F-06`` by
``24.11-02``.

The four findings
-----------------

``24.10-F-06`` — **CLOSED by ``24.11-02``; its test now runs unmarked.**
    ``GovernedResolver`` could not serve a product class whose operator set
    includes the **Similarity** category — one of the whitepaper's four. It
    called :func:`~ccf.deployment.build_operator_registry` with no
    ``similarity_index_version``, which that builder requires exactly when a
    similarity artifact is present (``D-IMPL-38``). There was no field on the
    class and no argument on the helper, and the registry is built inside
    ``__call__`` — so there was no deployment-side bridge at all, and **this
    one stopped adoption at step 4 of the composition's own nine**, before the
    graph was projected. The version is now a defaultless field on the
    resolver, supplied through :func:`build_governed_resolver`, and
    :func:`_wire` passes the deployment's own declared value like every other.
    The test below is unchanged except for the removal of its ``xfail``
    marker.

``24.10-F-07`` — **CLOSED by ``24.11-01``; its test now runs unmarked.**
    ``GovernedResolver`` did not seed the traversal from the request, and
    :mod:`ccf.replay.engine` does (``seeds=request_seeds(path.request)``). Two
    questions about two different companies therefore pinned **identically** to
    the graph — ``DI-15.5-07`` exactly, reproduced on the canonical path after
    ``D-IMPL-111`` limb (a) fixed it on the hand-built one — and any served
    product whose plan walks was replay-divergent by construction. The resolver
    now passes ``seeds=request_seeds(request)``. The test below is unchanged
    except for the removal of its ``xfail`` marker: what it asserted as absent
    it now asserts as present, in the same words.

``24.10-F-08``
    Three Track-B product members — ``obligation_in_force``,
    ``source_refresh_recency`` and ``debt_evidence`` — have no seam in the
    resolver's candidate construction. The measured consequence is not
    cosmetic: on ``s1-01``'s third declared question the served product says
    the deployment is obliged to do **nothing**, where the deployment's own
    ``artifacts/debt-profile.yaml`` binds that routing state to
    ``kyc/re-pull-registry-then-restate-with-debt-disclosed``. All three are
    inside the product's content address.

``24.10-F-09``
    The decision instant is collapsed into the graph boundary. ``expires_at``,
    the gate instant and ``recorded_at`` all derive from ``request.asked_at``,
    so a class that declares a distinct ``decision_instant`` — as ``s1-01``'s
    request contract does, as a **required** argument — finds nothing reads it.

The wall this harness used to bridge, and what deleted the bridge
-----------------------------------------------------------------

``24.10-F-06`` stopped the resolver before the other three were observable, so
until ``24.11-02`` this module's fixture monkeypatched
:func:`~ccf.deployment.build_operator_registry` to supply the deployment's own
declared ``similarity_index_version`` for the duration of a test — a
measurement device, never a proposal, and ``D-IMPL-282``'s *"No broader API
redesign is authorized up front"* is why it was never allowed to become one.

**The substitution is gone, and the SDK is why** (``D-IMPL-286``,
``D-IMPL-291`` (5)): the composition now carries that value itself, so
:func:`_wire` supplies it through the SDK's own argument, and the fixture —
still named :func:`bridged_resolver` for the bridge it no longer carries, on
the reasoning in its own docstring — wires nothing the SDK does not offer. A
workaround the SDK made unnecessary is **deleted**, not relocated; the three
tests behind it measure exactly what they measured, through a resolver no
longer standing on a substitution.

The contrasting half — that the hand-built spine gets every one of these right
— is already asserted in :mod:`tests.examples.test_s1_01_output`, unweakened
and un-quarantined by this same plan. This module is only the resolver's side.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
from collections.abc import Callable, Iterator
from typing import Any, NamedTuple

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_and_boot
from ccf.products.resolver import build_governed_resolver

pytestmark = pytest.mark.fluree

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE_DIR = REPO_ROOT / "examples" / "s1-01-hello-context-product"

#: The bare names the example's own modules find each other under. Shadowed for
#: the duration of the load for :mod:`tests.examples.test_s1_01_output`'s
#: reason: ``tests/deployment/`` is a package, so a bare ``import deployment``
#: inside this process resolves to the wrong tree.
SIBLING_MODULES = ("deployment", "report", "spine", "source_estate")

#: The manifest keys ``s1-01`` declares. Named here rather than discovered,
#: because a resolver's wiring is exactly a deployment naming its own keys —
#: which is what ``build_governed_resolver`` asks for and what this module is
#: measuring the cost of.
PRODUCT_CLASS_KEY = "product-class"
REQUEST_CONTRACT_KEY = "request-contract"
POLICY_BUNDLE_KEY = "policy-bundle"
OPERATOR_PARAMETER_KEYS = ("traversal", "temporal", "policy", "similarity")

#: The obligation ``artifacts/expected.yaml`` declares for the third question's
#: routing state, and the SDK sentinel a product carries when nothing set one.
EXPECTED_OBLIGATION_THIRD = "obligation_third_question"
NO_OBLIGATION = "ccf.no-obligation-in-force"


def _load_example() -> Any:
    """The example's driver module, loaded by path beside the test tree."""
    name = "s1_01_resolver_adoption_under_test"
    spec = importlib.util.spec_from_file_location(name, EXAMPLE_DIR / "run.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    shadowed = {
        sibling: sys.modules.pop(sibling)
        for sibling in SIBLING_MODULES
        if sibling in sys.modules
    }
    try:
        spec.loader.exec_module(module)
    finally:
        for sibling in SIBLING_MODULES:
            sys.modules.pop(sibling, None)
        sys.modules.update(shadowed)
    assert pathlib.Path(module.deployment.__file__).parent == EXAMPLE_DIR
    return module


@pytest.fixture(scope="module")
def example() -> Any:
    return _load_example()


@pytest.fixture(scope="module")
def questions(example: Any) -> Any:
    """``s1-01``'s three declared questions — the controlled experiment."""
    return example.deployment.declared_questions()


def _wire(
    example: Any,
    *,
    root: pathlib.Path,
    question: Any,
) -> tuple[Any, Any, Any]:
    """Boot, populate, and build a governed resolver over ``s1-01``'s fabric.

    Population happens **here**, on the caller's side, because
    :class:`~ccf.products.resolver.GovernedResolver` says in its own docstring
    that it *"hands no envelope to the L1 writer"* — the deployment it is given
    is already booted and already populated. That part of the restructure is
    expected and costs the example nothing; it is not one of the findings.

    Returns:
        ``(booted, scenario, resolver)``. The caller closes ``booted``.
    """
    deployment = example.deployment
    registry = ControlPlaneRegistry()
    booted = load_and_boot(
        deployment.MANIFEST,
        registry=registry,
        connection=deployment.connection(root=root),
    )
    scenario = deployment.read(booted, question)
    for envelope in scenario.envelopes:
        booted.handle.worker.ingest(envelope)

    def plan_factory(*, required: tuple[str, ...], request: Any) -> Any:
        return deployment.UltimateBeneficialOwnershipPlan(
            plan_id=scenario.plan_id, required=required, scenario=scenario
        )

    def debt_scorer(*, view: Any, evidence: Any = None) -> Any:
        return scenario.debt(view)

    resolver = build_governed_resolver(
        fabric=booted,
        control_plane=registry,
        product_class_key=PRODUCT_CLASS_KEY,
        request_contract_key=REQUEST_CONTRACT_KEY,
        operator_parameter_keys=OPERATOR_PARAMETER_KEYS,
        policy_bundle_key=POLICY_BUNDLE_KEY,
        plan_factory=plan_factory,
        debt_scorer=debt_scorer,
        artifact_store=FileArtifactStore(root=root / scenario.artifact_store_dirname),
        replay_record_class=scenario.replay_record_class,
        query_pin_class=scenario.query_pin_class,
        max_ttl_seconds=scenario.max_ttl_seconds,
        product_ttl_seconds=_declared_product_ttl_seconds(scenario),
        # `24.11-02` / `24.10-F-06`. The deployment's OWN declared version,
        # read off the scenario — the same value `spine.py` hands
        # `build_operator_registry` on the hand-built path, reaching the
        # canonical composition through the SDK's own argument rather than
        # through a substitution this harness performs on the SDK's behalf.
        similarity_index_version=scenario.similarity_index_version,
    )
    return booted, scenario, resolver


def _declared_product_ttl_seconds(scenario: Any) -> int:
    """The product lifetime this deployment authored, from its own artifact.

    Derived from the two instants the scenario already carries rather than
    re-read, so this harness names no number ``product-governance.yaml`` does
    not (CLAUDE.md §6.4).
    """
    return int((scenario.expires_at - scenario.now).total_seconds())


class Answered(NamedTuple):
    """One question put to the resolver, with what it takes to read it.

    ``store`` is the same file-backed store the resolver filed the record in,
    so dimension 5's pins are read back off what was persisted rather than off
    an object the test kept a reference to.
    """

    outcome: Any
    scenario: Any
    store: FileArtifactStore


@pytest.fixture
def bridged_resolver(
    example: Any, tmp_path: pathlib.Path
) -> Iterator[Callable[[Any], Answered]]:
    """The resolver as a deployment would actually wire it — nothing bridged.

    Until ``24.11-02`` this fixture monkeypatched
    :func:`~ccf.deployment.build_operator_registry` to supply the deployment's
    declared ``similarity_index_version``, because ``24.10-F-06`` stopped the
    resolver before the walls behind it were observable. **The substitution is
    gone, and the SDK is why**: :func:`build_governed_resolver` now takes that
    value and :class:`~ccf.products.resolver.GovernedResolver` carries it to
    the builder, so :func:`_wire` supplies it the way every other
    deployment-authored value here is supplied. ``D-IMPL-286``: the workaround
    is deleted **because the SDK made it unnecessary**, never relocated.

    **The name is now historical, and it is kept on purpose.** Two governance
    records cite this fixture by name as the place the substitution lived —
    ``D-IMPL-291`` (5) and the phase's own ROADMAP entry — and a rename would
    strand both while the row that renamed it is fenced out of the file that
    would have to be re-pointed. What the bridge *was* is why the three tests
    below could be written at all, so the name is left saying so until the
    citations move with it.
    """
    booted: list[Any] = []

    def answer(question: Any) -> Answered:
        root = tmp_path / f"q{len(booted)}"
        root.mkdir(parents=True, exist_ok=True)
        fabric, scenario, resolver = _wire(example, root=root, question=question)
        booted.append(fabric)
        outcome = resolver(
            tenant=fabric.tenant_id,
            product_class=scenario.product_class.schema_name,
            version=scenario.product_class.schema_version,
            perspective=scenario.perspective,
            request=question,
        )
        return Answered(
            outcome=outcome,
            scenario=scenario,
            store=FileArtifactStore(root=root / scenario.artifact_store_dirname),
        )

    try:
        yield answer
    finally:
        for fabric in booted:
            fabric.handle.close()


# ---------------------------------------------------------------------------
# 24.10-F-06 — CLOSED by `24.11-02`. The wall that stopped adoption outright.
# ---------------------------------------------------------------------------


def test_the_resolver_serves_a_class_whose_operators_include_similarity(
    example: Any, questions: Any, tmp_path: pathlib.Path
) -> None:
    """Adoption requires that the canonical composition serve all four categories.

    ``s1-01`` declares ``similarity.corpus-select`` in its product class's
    ``required_operator_keys`` and registers
    ``operator-parameters-similarity.yaml`` in its manifest, which is an
    ordinary thing for a deployment to do — the Similarity category is one of
    the four the whitepaper §7.4 commits to.
    """
    root = tmp_path / "adopted"
    root.mkdir()
    booted, scenario, resolver = _wire(example, root=root, question=questions[0])
    try:
        outcome = resolver(
            tenant=booted.tenant_id,
            product_class=scenario.product_class.schema_name,
            version=scenario.product_class.schema_version,
            perspective=scenario.perspective,
            request=questions[0],
        )
    finally:
        booted.handle.close()
    assert getattr(outcome, "product", None) is not None, (
        "the governed resolver returned no product for a class whose operator"
        " set includes the Similarity category"
    )


# ---------------------------------------------------------------------------
# 24.10-F-07 — the request does not seed the traversal (DI-15.5-07, again).
# ---------------------------------------------------------------------------


def test_two_subjects_pin_two_different_questions_to_the_graph(
    bridged_resolver: Callable[[Any], Answered], questions: Any
) -> None:
    """Adoption requires the record to say which subject a decision was about.

    The hand-built spine passes
    :func:`~ccf.products.request.request_seeds` to the engine and its own
    ``tests/examples/test_s1_01_output.py::
    test_a_later_instant_pins_a_different_question_to_the_graph`` asserts
    exactly this, unweakened. The resolver does not, so the pinned sequence
    cannot distinguish two companies — which is the repudiation gap
    ``D-IMPL-111`` limb (a) closed once already.
    """
    first = bridged_resolver(questions[0])
    second = bridged_resolver(questions[1])
    assert questions[0].subject != questions[1].subject
    first_pins = _query_pins(first)
    second_pins = _query_pins(second)
    assert first_pins, "the record pins no graph query at all"
    assert first_pins != second_pins, (
        "two questions about two different companies pinned the same graph"
        " query sequence; the record cannot say which subject this decision"
        " was about (DI-15.5-07, D-IMPL-111 limb (a))"
    )


def _query_pins(answered: Answered) -> tuple[str, ...]:
    """Dimension 5's pinned query sequence, read back off the PERSISTED record.

    Read out of the store rather than off an in-memory object, because the pins
    are what an auditor with the record and nothing else would see.
    """
    raw = answered.store.get(
        content_address=answered.outcome.replay_ref.content_address
    )
    document = json.loads(raw)
    path = document["content_generation_path"]
    return tuple(path["graph_query_sequence"])


# ---------------------------------------------------------------------------
# 24.10-F-08 — three product members with no seam.
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason=(
        "24.10-F-08: GovernedResolver's candidate construction has no seam for"
        " obligation_in_force, so a product served through it says the"
        " deployment is obliged to do nothing wherever its own debt profile"
        " binds an obligation to the routing state the assessment landed in."
        " The member is inside the product's content address"
    ),
)
def test_the_served_product_carries_the_obligation_the_deployment_declared(
    example: Any,
    bridged_resolver: Callable[[Any], Answered],
    questions: Any,
) -> None:
    """Adoption requires the delivered product to state what it obliges.

    ``s1-01``'s third question lands in ``forced_llm``, and
    ``artifacts/debt-profile.yaml`` binds that state to a named obligation the
    deployment authored. ``D-IMPL-112`` gap 3 put the member on the vessel so
    the obligation in force at decision time is inside the content address and
    replay reproduces it; a resolver that never sets it delivers the SDK's
    "no obligation" sentinel instead, which is a **wrong governance answer**
    rather than an absent nicety.
    """
    answered = bridged_resolver(questions[2])
    declared = example.deployment.expectation(answered.scenario.artifacts)[
        EXPECTED_OBLIGATION_THIRD
    ]
    assert declared != NO_OBLIGATION, "the fixture's own premise has moved"
    assert answered.outcome.product.obligation_in_force == declared


@pytest.mark.xfail(
    strict=True,
    reason=(
        "24.10-F-08: GovernedResolver's candidate construction has no seam for"
        " source_refresh_recency, so the declared window every consumer reads"
        " freshness from is None on the canonical path. Inside the content"
        " address (D-IMPL-112 gap 2, D-IMPL-118)"
    ),
)
def test_the_served_product_carries_the_declared_refresh_window(
    bridged_resolver: Callable[[Any], Answered], questions: Any
) -> None:
    """Adoption requires when the sources last published to reach the caller."""
    answered = bridged_resolver(questions[0])
    assert (
        answered.outcome.product.source_refresh_recency
        == answered.scenario.source_refresh_recency
    )


# ---------------------------------------------------------------------------
# 24.10-F-09 — the decision instant is collapsed into the graph boundary.
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason=(
        "24.10-F-09: GovernedResolver derives expires_at, the gate instant and"
        " recorded_at from request.asked_at, so a class declaring a distinct"
        " decision_instant — s1-01's request contract declares it REQUIRED —"
        " finds nothing reads it. The TTL runs from the wrong instant"
    ),
)
def test_the_ttl_runs_from_the_declared_decision_instant(
    bridged_resolver: Callable[[Any], Answered], questions: Any
) -> None:
    """Adoption requires the two instants to stay two.

    ``s1-01`` reads the graph as of ``asked_at`` and produces the answer at
    ``decision_instant``, five minutes later, and its ``expires_at`` runs from
    the second. The resolver has one instant and uses it for both.
    """
    answered = bridged_resolver(questions[0])
    scenario = answered.scenario
    assert scenario.now != scenario.request.asked_at, (
        "the fixture's own premise has moved: the deployment no longer"
        " declares a decision instant distinct from the graph boundary"
    )
    assert answered.outcome.product.expires_at == scenario.expires_at
