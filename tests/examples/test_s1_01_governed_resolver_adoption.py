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
**All four are now closed**: ``24.10-F-07`` by ``24.11-01``, ``24.10-F-06`` by
``24.11-02``/``24.11-02b``, ``24.10-F-08``'s obligation limb by ``24.11-03``,
and ``24.10-F-08``'s refresh limb together with ``24.10-F-09`` by
``D-IMPL-308``. Every test below runs unmarked, asserting as present what it
was written to assert as absent.

The four findings
-----------------

``24.10-F-06`` — **CLOSED in two parts, ``24.11-02`` then ``24.11-02b``.**
    ``GovernedResolver`` could not serve a product class whose operator set
    includes the **Similarity** category — one of the whitepaper's four. It
    called :func:`~ccf.deployment.build_operator_registry` with no
    ``similarity_index_version``, which that builder then required exactly when
    a similarity artifact was present (``D-IMPL-38``). There was no field on
    the class and no argument on the helper, and the registry is built inside
    ``__call__`` — so there was no deployment-side bridge at all, and **this
    one stopped adoption at step 4 of the composition's own nine**, before the
    graph was projected.

    ``24.11-02`` made the version a field on the resolver. Dave ruled that
    insufficient (``D-IMPL-292``): it fixed the propagation and left a
    decision-affecting semantic value in ungoverned deployment hands, which is
    a workaround relocated rather than discharged (``D-IMPL-289``).
    ``24.11-02b`` moved it to the declaration — ``index_version`` on
    ``operator-parameters-similarity.yaml`` — and **this deployment migrated
    onto that surface second, after the SDK refused its old document by
    name.** ``product-governance.yaml`` no longer declares it, and the
    ``deployment.py`` and ``spine.py`` code that ferried it is deleted.

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

``24.10-F-08`` — **obligation limb CLOSED at ``24.11-03``, refresh limb at
``D-IMPL-308``; ``debt_evidence`` remains out of scope.**
    Three Track-B product members — ``obligation_in_force``,
    ``source_refresh_recency`` and ``debt_evidence`` — had no seam in the
    resolver's candidate construction. The measured consequence was not
    cosmetic: on ``s1-01``'s third declared question the served product said
    the deployment was obliged to do **nothing**, where the deployment's own
    ``artifacts/debt-profile.yaml`` binds that routing state to
    ``kyc/re-pull-registry-then-restate-with-debt-disclosed``. All three are
    inside the product's content address, so none was an omission a deployment
    could repair afterwards. ``source_refresh_recency`` is now a required,
    deployment-owned argument. ``debt_evidence`` is untouched and stays open:
    ``D-IMPL-119`` limb 4's named precondition — a perspective-scoped view in
    the assembly path — is still unmet, and ``D-IMPL-308`` scoped it out.

``24.10-F-09`` — **CLOSED by ``D-IMPL-308``.**
    The decision instant was collapsed into the graph boundary. ``expires_at``,
    the gate instant and ``recorded_at`` all derived from ``request.asked_at``,
    so a class that declares a distinct ``decision_instant`` — as ``s1-01``'s
    request contract does, as a **required** argument — found nothing read it.
    The resolver now reads the argument the class names and binds the instant
    ONCE for all three. **Coincidence is allowed and collapse is not**: a class
    naming no such parameter passes ``None``, and every instant continues to
    derive from ``asked_at``.

The wall this harness used to bridge, and what deleted the bridge
-----------------------------------------------------------------

``24.10-F-06`` stopped the resolver before the other three were observable, so
until ``24.11-02`` this module's fixture monkeypatched
:func:`~ccf.deployment.build_operator_registry` to supply the deployment's own
declared ``similarity_index_version`` for the duration of a test — a
measurement device, never a proposal, and ``D-IMPL-282``'s *"No broader API
redesign is authorized up front"* is why it was never allowed to become one.

**The substitution is gone, and the SDK is why** (``D-IMPL-286``,
``D-IMPL-291`` (5), ``D-IMPL-292``): the deployment declares that value on its
similarity artifact and the builder reads it there, so :func:`_wire` supplies
**nothing at all** about the index — not a monkeypatch and not an argument.
The fixture is still named :func:`adopted_resolver` for the bridge it no
longer carries, on the reasoning in its own docstring. A workaround the SDK
made unnecessary is **deleted**, not relocated; the three tests behind it
measure exactly what they measured, through a resolver no longer standing on a
substitution.

The contrasting half — that the hand-built spine gets every one of these right
— is already asserted in :mod:`tests.examples.test_s1_01_output`, unweakened
and un-quarantined by this same plan. This module is only the resolver's side.
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import sys
from tests.composition import declared_erasure_trust, no_erasures
from datetime import datetime, timedelta
from collections.abc import Callable, Iterator
from typing import Any, NamedTuple

import pytest

from ccf.artifacts.file_store import FileArtifactStore
from ccf.artifacts.protocol import WriteKinds
from ccf.authz.capability import ReplayMint
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry, namespaced_key
from ccf.deployment import load_and_boot
from ccf.products.composite import ADMITTED_CHILD_CONTRACT_CLASS
from ccf.products.resolver import build_governed_resolver
from ccf.replay.record import DecisionReplayRecord

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
#: `24.11-03` / `24.10-F-08`: the key `artifacts/manifest.yaml` already
#: declares this deployment's D_c bands under. Naming it is the whole of
#: wiring the obligation seam — the binding is authored in
#: `artifacts/debt-profile.yaml`, and the resolver reads it from there.
DEBT_PROFILE_KEY = "debt-profile"
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


def _evidence_store(root: pathlib.Path, scenario: Any) -> FileArtifactStore:
    """The deployment's evidence store, declared the way its own spine declares it.

    D-IMPL-353 §1.2: the store carries the deployment's statement of which
    artifact classes its mechanism writes and under which kind — the two
    replay classes ``product-governance.yaml`` names and the SDK's
    admitted-child class, all ``ReplayMint``. The same declaration serves the
    reader that opens the record back, so what this module reads is filed
    under the lanes the deployment declared.
    """
    return FileArtifactStore(
        root=root / scenario.artifact_store_dirname,
        write_kinds=WriteKinds.declare(
            {
                scenario.replay_record_class: (ReplayMint,),
                scenario.query_pin_class: (ReplayMint,),
                ADMITTED_CHILD_CONTRACT_CLASS: (ReplayMint,),
            }
        ),
    )


def _wire(
    example: Any,
    *,
    root: pathlib.Path,
    question: Any,
    service_instant: Any = None,
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

    # The keys this module names are the deployment's bare section names; the
    # fabric holds them placed under its tenant (D-IMPL-353 §1.3), so the
    # resolver is handed the placed keys through the one derivation.
    def placed(key: str) -> str:
        return namespaced_key(tenant=booted.tenant_id, key=key)

    resolver = build_governed_resolver(
        fabric=booted,
        control_plane=registry,
        erasure_trust=declared_erasure_trust(),
        erasure_index=no_erasures(),
        product_class_key=placed(PRODUCT_CLASS_KEY),
        request_contract_key=placed(REQUEST_CONTRACT_KEY),
        operator_parameter_keys=tuple(placed(key) for key in OPERATOR_PARAMETER_KEYS),
        policy_bundle_key=placed(POLICY_BUNDLE_KEY),
        # `24.11-03` / `24.10-F-08`: this deployment declares its bands AND
        # supplies its own scorer, which are two different seams — the scorer
        # is behavior, the profile is a declaration. Naming the key is what
        # lets the resolver carry the obligation the profile binds; nothing
        # about the scorer changes, and no value is restated here.
        debt_profile_key=placed(DEBT_PROFILE_KEY),
        plan_factory=plan_factory,
        debt_scorer=debt_scorer,
        artifact_store=_evidence_store(root, scenario),
        replay_record_class=scenario.replay_record_class,
        query_pin_class=scenario.query_pin_class,
        max_ttl_seconds=scenario.max_ttl_seconds,
        product_ttl_seconds=_declared_product_ttl_seconds(scenario),
        # `D-IMPL-308` / `24.10-F-09`: this class declares a decision instant
        # distinct from its graph boundary, and naming the argument is the
        # whole of the wiring — the value travels on the request.
        decision_instant_parameter=scenario.decision_instant_parameter,
        # `D-IMPL-308` / `24.10-F-08`: when this estate's sources last
        # published. Declared, because no operator can observe it.
        source_refresh_recency=scenario.source_refresh_recency,
        # `D-IMPL-358` step 13. The trusted SERVE instant for this demonstration
        # period, when the caller composed one -- Gate 3's comparand and the
        # temporal bound's. Passed only when supplied, so the SDK's process clock
        # stands for a deployment answering live questions and this module invents
        # no default. It arrives as an ARGUMENT and is never read off `question`:
        # a serve instant taken from caller input would let the question move the
        # fabric's clock.
        **(
            {"admission_clock": lambda: service_instant}
            if service_instant is not None
            else {}
        ),
        # `24.11-02b` / `D-IMPL-292`. Nothing here says anything about a
        # similarity index, and that is the point: the deployment declares
        # `index_version` on `operator-parameters-similarity.yaml`, which
        # `operator_parameter_keys` above already names. `24.11-02` passed it
        # as an argument here; the argument is gone from the SDK because the
        # declaration is the authority.
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
def adopted_resolver(
    example: Any, tmp_path: pathlib.Path
) -> Iterator[Callable[..., Answered]]:
    """The resolver as a deployment would actually wire it — nothing bridged.

    Until ``24.11-02`` this fixture monkeypatched
    :func:`~ccf.deployment.build_operator_registry` to supply the deployment's
    declared ``similarity_index_version``, because ``24.10-F-06`` stopped the
    resolver before the walls behind it were observable. **The substitution is
    gone, and the SDK is why** (``D-IMPL-286``). ``24.11-02`` replaced it with
    an argument; ``24.11-02b`` removed the argument too (``D-IMPL-292``), so
    :func:`_wire` now says nothing about the index at all — the deployment
    declares ``index_version`` on its similarity artifact, and naming that
    artifact in ``operator_parameter_keys`` is the whole of the wiring. The
    workaround is deleted **because the SDK made it unnecessary**, never
    relocated, and the second removal is what kept it from surviving as
    caller-side plumbing.

    **The name is now historical, and it is kept on purpose.** Two governance
    records cite this fixture by name as the place the substitution lived —
    ``D-IMPL-291`` (5) and the phase's own ROADMAP entry — and a rename would
    strand both while the row that renamed it is fenced out of the file that
    would have to be re-pointed. What the bridge *was* is why the three tests
    below could be written at all, so the name is left saying so until the
    citations move with it.
    """
    booted: list[Any] = []
    # `D-IMPL-358` step 13. The harness's own pairing of a DECLARED question with
    # the DEMONSTRATION PERIOD the questions document declares for it. Read once,
    # here, so the lookup below selects among instants the DOCUMENT states and
    # never computes one from a request's fields -- the clock is composition state.
    # A question that is not one of the declared three matches nothing and is
    # served on the process clock, which is the honest answer for an ad-hoc
    # question and stays visible as a `ttl-refusal`.
    declared_questions = example.deployment.declared_questions()
    declared_instants = example.deployment.declared_service_instants()

    def answer(question: Any, *, service_instant: Any = None) -> Answered:
        if service_instant is None:
            for candidate, instant in zip(
                declared_questions, declared_instants, strict=True
            ):
                if candidate == question:
                    service_instant = instant
                    break
        root = tmp_path / f"q{len(booted)}"
        root.mkdir(parents=True, exist_ok=True)
        # The deployment declares this root as its writer-lease lock directory,
        # which PC3 refuses if group- or world-writable (`D-IMPL-374`); set
        # owner-only explicitly, because `mkdir`'s mode passes through the umask.
        os.chmod(root, 0o700)
        fabric, scenario, resolver = _wire(
            example, root=root, question=question, service_instant=service_instant
        )
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
            store=_evidence_store(root, scenario),
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
    # The deployment's writer-lease lock directory: owner-only whatever the
    # umask (PC3, `D-IMPL-374`), as `run.py`'s `ask_all` makes it.
    os.chmod(root, 0o700)
    booted, scenario, resolver = _wire(
        example,
        root=root,
        question=questions[0],
        # The first declared question's own declared period (`D-IMPL-358` step 13).
        service_instant=example.deployment.declared_service_instants()[0],
    )
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
    adopted_resolver: Callable[[Any], Answered], questions: Any
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
    first = adopted_resolver(questions[0])
    second = adopted_resolver(questions[1])
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


def test_the_served_product_carries_the_obligation_the_deployment_declared(
    example: Any,
    adopted_resolver: Callable[[Any], Answered],
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

    **Un-quarantined at ``24.11-03``, unchanged.** No assertion was weakened
    and no expected value moved: it carried ``xfail(strict=True)`` for
    ``24.10-F-08`` and XPASSed the moment the seam landed, which is the whole
    reason the finding was left executable rather than only written down.
    """
    answered = adopted_resolver(questions[2])
    declared = example.deployment.expectation(answered.scenario)[
        EXPECTED_OBLIGATION_THIRD
    ]
    assert declared != NO_OBLIGATION, "the fixture's own premise has moved"
    assert answered.outcome.product.obligation_in_force == declared


def test_the_served_product_carries_the_declared_refresh_window(
    adopted_resolver: Callable[[Any], Answered], questions: Any
) -> None:
    """Adoption requires when the sources last published to reach the caller."""
    answered = adopted_resolver(questions[0])
    assert (
        answered.outcome.product.source_refresh_recency
        == answered.scenario.source_refresh_recency
    )


# ---------------------------------------------------------------------------
# 24.10-F-09 — the decision instant is collapsed into the graph boundary.
# ---------------------------------------------------------------------------


def test_the_ttl_runs_from_the_declared_decision_instant(
    adopted_resolver: Callable[[Any], Answered], questions: Any
) -> None:
    """Adoption requires the two instants to stay two.

    ``s1-01`` reads the graph as of ``asked_at`` and produces the answer at
    ``decision_instant``, five minutes later, and its ``expires_at`` runs from
    the second. The resolver has one instant and uses it for both.
    """
    answered = adopted_resolver(questions[0])
    scenario = answered.scenario
    assert scenario.now != scenario.request.asked_at, (
        "the fixture's own premise has moved: the deployment no longer"
        " declares a decision instant distinct from the graph boundary"
    )
    assert answered.outcome.product.expires_at == scenario.expires_at


# ---------------------------------------------------------------------------
# MOD-05 / D-IMPL-309 — the ambient ledger head is not part of the answer.
# ---------------------------------------------------------------------------


def test_two_ambient_ledger_heads_serve_one_content_address(
    adopted_resolver: Callable[[Any], Answered], questions: Any
) -> None:
    """`MOD-05`'s measurement, asked of the canonical path and answered.

    Two whole runs of the identical question. The fixture boots and populates
    a fresh fabric per call, so the two runs read the store at two different
    heads — which is precisely the ambient movement `MOD-05` measured, and it
    happens here for a reason that has nothing to do with the question asked.

    Before ``D-IMPL-309`` this returned two addresses, and the diff was one
    field::

        DIFFER store_snapshot_pin
           run1: {'substrate': 'fluree', 'pin': '74342'}
           run2: {'substrate': 'fluree', 'pin': '74409'}

    ``GovernedResolver`` set ``store_snapshot_pin=execution.store_snapshot_pin``
    inside ``ProductLineage``, inside the sealed product, inside the content
    address — so a head advancing for unrelated reasons made the same question
    a different answer. The head is now execution provenance: recorded on
    replay dimension 1, absent from the vessel.

    This is the canonical-path twin of the hand-composed spine's own
    ``tests/examples/test_s1_01_output.py::
    test_the_products_address_survives_a_different_graph_identity``, whose
    words this ruling makes true of both spines: *"the content address is
    byte-identical, which is what makes replay a property of the question and
    the Control Plane rather than of where the bytes happened to be stored."*
    """
    runs = [adopted_resolver(questions[0]), adopted_resolver(questions[0])]
    addresses: list[str] = []
    heads: list[Any] = []
    for answered in runs:
        product = getattr(answered.outcome, "product", None)
        assert product is not None, "the governed resolver served no product"
        addresses.append(content_hash(product))
        record = DecisionReplayRecord.model_validate_json(
            answered.store.get(
                content_address=answered.outcome.replay_ref.content_address
            )
        )
        heads.append(record.context_fabric_snapshot.store_snapshot_pin)

    # The head is still recorded, per execution, and the two runs genuinely
    # read different ones. Without this the equality below would be the
    # equality of two runs that happened to share a head, which would prove
    # nothing about ambient movement at all.
    assert heads[0] != heads[1], (
        "the two runs read the same store head, so this test did not measure"
        f" ambient movement ({heads[0]!r} both times)"
    )
    # And the answer is one answer.
    assert addresses[0] == addresses[1], (
        "the same governed question served two content addresses across two"
        f" ambient ledger heads ({heads[0]!r} then {heads[1]!r}) — `MOD-05`"
        " has regressed and `D-IMPL-309` is not in force"
    )


# ---------------------------------------------------------------------------
# `D-IMPL-358` step 13 — the LATER-SERVICE control. Three service instants on ONE
# question, so that a green suite cannot rest on the decision instant and the
# service instant happening to coincide.
# ---------------------------------------------------------------------------


def test_service_after_expiry_is_REFUSED_while_service_inside_the_window_is_SERVED(
    example: Any, questions: Any, adopted_resolver: Any
) -> None:
    """Gate 3 stays at `served_at`, and this is the proof that it bites.

    The simulation clock that makes the three declared questions answerable pins
    the serve instant to each question's declared demonstration period, which for
    question 1 is the SAME instant as its decision instant. That coincidence is
    convenient and it is also a hazard: every TTL assertion in this module would
    pass just as well against a gate that compared nothing at all. So this control
    moves the serve instant alone -- the question, the TTL duration, the temporal
    policy and the expected answer are all untouched -- and asserts the ordering
    the gate is supposed to enforce.

    Question 1 decides at 2026-08-01T00:05:00Z. `product-governance.yaml` declares
    `product_ttl_seconds: 600`, so the product expires at 00:15:00Z, and
    `max_ttl_seconds: 1200` puts the ceiling at 00:25:00Z.

    | serve instant | expected | why |
    | --- | --- | --- |
    | 00:05:00Z | SERVED | the declared period; decision and service coincide |
    | 00:10:00Z | SERVED | strictly AFTER the decision instant, still inside TTL |
    | 00:20:00Z | REFUSED | past expiry: `served_at < expires_at` fails |

    The middle row is the one that makes the other two mean something: it shows the
    product is servable at an instant that is NOT its decision instant, so the first
    row is not passing by coincidence. The third shows expiry is still enforced
    against the serve instant, which is exactly what step 5 section H moved it to.

    Nothing here anchors expiry to the serve instant. Expiry remains
    decision-anchored -- `test_the_ttl_runs_from_the_declared_decision_instant`
    above asserts that, and it is deliberately left as it was.
    """
    question = questions[0]
    decided_at = datetime.fromisoformat(
        question.parameters[example.deployment.PARAM_DECISION_INSTANT]
    )
    # Offsets, not absolute instants: the two probes below are asserted to straddle
    # the DECLARED expiry, so they move with `product-governance.yaml` instead of
    # pinning a number this test invented.
    inside = decided_at + timedelta(seconds=300)
    after_expiry = decided_at + timedelta(seconds=900)

    at_period = adopted_resolver(question)
    assert getattr(at_period.outcome, "product", None) is not None, (
        f"the declared period does not serve: {at_period.outcome!r} — the control"
        " below cannot be read against a broken baseline"
    )
    scenario = at_period.scenario
    # Expiry is anchored to the DECISION instant, stated directly rather than
    # through an identity that would hold whatever the values were.
    assert scenario.now == decided_at, (
        f"the scenario decides at {scenario.now.isoformat()}, not at the question's"
        f" declared {decided_at.isoformat()}"
    )
    assert scenario.expires_at > scenario.now, scenario.expires_at
    assert inside < scenario.expires_at < after_expiry, (
        "this control's two probe instants no longer straddle expiry"
        f" ({scenario.expires_at.isoformat()}), so it would prove nothing"
    )

    served_later = adopted_resolver(question, service_instant=inside)
    assert getattr(served_later.outcome, "product", None) is not None, (
        "a product served STRICTLY AFTER its decision instant and inside its TTL"
        f" was refused: {served_later.outcome!r}. Gate 3 is not admitting a live"
        " serve, so every other TTL assertion here is passing on a coincidence"
    )

    expired = adopted_resolver(question, service_instant=after_expiry)
    assert getattr(expired.outcome, "product", None) is None, (
        "a product served AFTER its expiry was still served — Gate 3 is no longer"
        " judging expiry against the serve instant"
    )
    assert expired.outcome.kind == "ttl-refusal", expired.outcome
    assert expired.outcome.reason == "ttl-bounds", expired.outcome
