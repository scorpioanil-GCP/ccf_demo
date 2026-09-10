"""The KYC/UBO example's assertions, under a runner that can actually fail.

``examples/s1-01-hello-context-product/run.py`` asserts nothing, and since
2026-08-13 it **prints its work**. Its assertions live here, and so do the
assertions on what it prints: the product's content address, the party
references in the answer, the two instants of the refresh window, and two ruled
absences. ``make example-s1-01`` exiting zero still proves only that the spine
*ran* — an assertion inside a driver only fails a build if someone remembers to
run the driver, which is why the assertions are here and not there.

**What the example answers.** *"Who ultimately owns Acme Corporation?"* — a
question whose answer appears in no record of any source system, because it is a
sum over ownership paths. That is why the assertions below are about
**aggregation across hops** rather than about lookup: a single-hop reading of the
same estate produces a different, wrong answer, and
:func:`test_the_answer_is_a_sum_over_paths_not_a_single_hop` is the test that
would go red if the projection regressed to one.

Two kinds of assertion, and the difference is worth stating
-----------------------------------------------------------

Reading expectations from artifacts produces two categories, and conflating them
is how a suite ends up claiming more than it checks:

* **Independent expectations.** ``artifacts/expected.yaml`` declares what the
  *served product* should contain. Nothing in the pipeline derives those numbers
  from that file — they follow from ``events.yaml``, ``resolution-spec.yaml`` and
  the four operator parameter sets — so changing either side alone makes the
  assertion fail. These are the correctness guarantees. Verified by mutation:
  changing ``entity_count``, the relationship set or a party's aggregate
  percentage breaks the suite.
* **Propagation checks.** The temporal boundary, the perspective role, the
  product's schema name, its assembly mode and the ownership threshold are each
  read from an artifact by the example *and* by this module, so the artifact is a
  single source and editing it moves both ends together. These assert that a
  declared value survives end to end into the served product and its replay
  record — which fails on a **wiring** fault, not on an artifact edit.

Both belong here. Only the first is a statement about whether the fabric
computed the right answer, and this module does not claim otherwise.

**Every domain expectation is read from an artifact, never inlined.** A value
this module authored would be the test agreeing with itself about what the
deployment's vocabulary says. ``tools/lints``' ``RULE_TREE_SCOPE`` covers
``tests`` (D-IMPL-78), so an inlined threshold here is the same No-Hardcoding
violation as one in a library module (CLAUDE.md §6.4) — but the discipline is the
point, not the lint. The expectations are reached through
``deployment.expectation()`` and the deployment's own ``KEY_*`` vocabulary, so
this module names no artifact key of its own.

The distinction that governs what stays a literal: a **domain expectation** comes
from an artifact; an **SDK mechanism claim** — that a keyless deployment records
``model_version: none``, that the replay reference is the record's own content
hash — is asserted directly, because it is a claim about the SDK rather than
about this deployment.

**This module moved from the always-on leg to the Fluree leg** (plan 16-05).
The example's ``artifacts/manifest.yaml`` now declares a networked substrate, so
every fixture below that boots a fabric requests the session-scoped
``fluree_url`` fixture: unset ``CCF_TEST_FLUREE_URL`` skips, and
``CCF_REQUIRE_FLUREE`` turns the skip into a failure. ``make leg-fluree`` is
what runs this module. Requesting the fixture IS the gate — ``pytestmark``
marks and does not skip — and the variable it reads is the same one the
deployment reads, so nothing here monkeypatches an environment.

What still covers this example on the always-on, network-free leg is the three
gates that need no substrate: ``test_section_one_is_agent_free.py`` (the AST
denylist), ``test_spine_separation.py`` (the spine/deployment split) and
``test_artifact_schema_headers.py`` (the artifact-header bijection) — plus the
two tests below that read modules and documents rather than graphs.

**Un-quarantined at ``24.10-04``.** Every test below carried
``xfail(strict=True)`` from ``24.7`` on one reason — *"frozen s1-01 spine.py
calls build_replay_record with no resolution state … un-quarantine and rerun
unchanged after D-GATE-24.7"*. ``D-GATE-24.7`` closed and the un-quarantine the
marker scheduled never happened, so the SDK's canonical worked example sat dark
for three phases while a strict xfail reported green. What the quarantine was
about was one call site and one required keyword-only argument
:func:`~ccf.replay.record.build_replay_record` grew at ``D-IMPL-264`` — the
third clause of ``D-IMPL-261``'s own test for when an example may change,
*"the SDK surface it legitimately consumes was deliberately changed"*. The
call site now states :class:`~ccf.replay.record.ResolutionNotApplicable`
positively, and **the 33 markers came off with no assertion touched**: the
whole diff at ``24.10-04`` is 132 deleted decorator lines and this paragraph.

The example is not a package, so it is loaded by file path with
``importlib.util`` — the pattern ``test_quickstart_output.py`` established.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import types
from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest
import yaml

from ccf.contracts.canonical import content_hash
from ccf.replay.record import NO_GRAPH_QUERIES, DecisionReplayRecord

#: The leg this module runs on. The marker selects it (`make leg-fluree`); the
#: `fluree_url` fixture request on each fabric-booting fixture is what actually
#: skips, so the two tests that need no substrate keep running everywhere.
pytestmark = pytest.mark.fluree

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE_DIR = REPO_ROOT / "examples" / "s1-01-hello-context-product"
EXAMPLE = EXAMPLE_DIR / "run.py"

#: The keys of the served payload. Structural names this deployment's projection
#: writes, read here the way ``test_quickstart_output.py`` reads its own — the
#: *values* behind them are what comes from an artifact.
PAYLOAD_ENTITY_COUNT = "entity_count"
PAYLOAD_ENTITY_CLASSES = "entity_classes"
PAYLOAD_ENTITY_COUNT_BY_CLASS = "entity_count_by_class"
PAYLOAD_RELATIONSHIP_TYPES = "relationship_types"
PAYLOAD_THRESHOLD = "beneficial_ownership_threshold_percent"
PAYLOAD_OWNERSHIP_BY_PARTY = "ownership_percent_by_party"
PAYLOAD_BENEFICIAL_OWNERS = "beneficial_owners"
PAYLOAD_SUBJECT = "subject_entity_ref"
PAYLOAD_ROLE = "role"

OWNER_PARTY_REF = "party_ref"
OWNER_PERCENT = "aggregate_ownership_percent"

#: The expectation document's own blocks.
EXPECTED_BOUNDARY_CASE = "boundary_case_party"
EXPECTED_SECOND_QUESTION = "second_question"
EXPECTED_THIRD_QUESTION = "third_question"
EXPECTED_NEWLY_VISIBLE = "newly_visible"
EXPECTED_DEBT_SIGNAL_FIRST = "debt_signal_first_question"
EXPECTED_DEBT_SIGNAL_THIRD = "debt_signal_third_question"
EXPECTED_DEBT_WEAK_FACTOR = "debt_weak_factor"
EXPECTED_OBLIGATION_FIRST = "obligation_first_question"
EXPECTED_OBLIGATION_THIRD = "obligation_third_question"

#: Every ``absent_by_*`` block is a witness: a reference the pipeline must have
#: removed, and the operator that removed it. Prefix-matched rather than listed,
#: so a witness added to ``expected.yaml`` is checked without editing this file.
ABSENCE_PREFIX = "absent_by_"

#: The bare names ``run.py`` imports its siblings under. Shadowed for the
#: duration of the load — see :func:`_load_example` — because ``deployment``
#: also names a package under ``tests/``.
SIBLING_MODULES = ("deployment", "report", "spine", "source_estate")


def _load_example() -> Any:
    """Load the example module by file path (the example dir is no package).

    The module is registered in ``sys.modules`` *before* execution: the example
    uses ``from __future__ import annotations``, so ``@dataclass`` resolves its
    field annotations by looking its own module up there, and a module absent
    from the table fails with an opaque ``AttributeError`` at class-definition
    time rather than anywhere near the cause.

    **The sibling names are shadowed for the duration of the load, and restored
    after.** ``run.py`` puts its own directory on ``sys.path`` and imports its
    two siblings by bare name — ``import deployment``, ``import spine`` — which
    is unambiguous for a user running the example, and ambiguous inside this
    process: ``tests/deployment/`` is a package with an ``__init__.py``, so by
    the time ``tests/examples`` is collected ``sys.modules["deployment"]``
    already holds the *test* package. A bare import then returns the cached
    module and the example fails with ``module 'deployment' has no attribute
    'KycDeployment'`` — a collision between two trees, not a fault in either.

    Evicting the names forces a fresh resolution through ``sys.path``, where
    ``run.py`` has just put the example directory first; restoring them
    afterwards leaves ``tests/deployment`` importable for every test collected
    after this one. The loaded driver keeps a direct reference to the example's
    own modules, so the restore costs it nothing.
    """
    name = "s1_01_under_test"
    spec = importlib.util.spec_from_file_location(name, EXAMPLE)
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

    # Loud rather than subtle: if a future change lets a same-named module from
    # another tree win, this fails here instead of as a puzzling AttributeError
    # on the first fixture that reaches for the deployment's vocabulary.
    assert pathlib.Path(module.deployment.__file__).parent == EXAMPLE_DIR, (
        f"the driver resolved `deployment` to {module.deployment.__file__},"
        f" not to the example's own module under {EXAMPLE_DIR}"
    )
    return module


@pytest.fixture(scope="module")
def example() -> Any:
    """The loaded driver, for reaching ``deployment``'s own vocabulary."""
    return _load_example()


@pytest.fixture(scope="module")
def result(
    example: Any, fluree_url: str, tmp_path_factory: pytest.TempPathFactory
) -> Any:
    """One run of the spine, shared across the module.

    Module-scoped deliberately: the spine is the unit under test, and running it
    once per assertion would say nothing extra while paying for a full boot each
    time.

    ``fluree_url`` is requested and not used: reaching this line is proof the
    environment the deployment reads is populated, and the deployment reads it
    itself through ``artifacts/backends.yaml``. Substituting a value here would
    be this module configuring the run it is meant to be observing.
    """
    del fluree_url
    return example.run(root=tmp_path_factory.mktemp("s1-01"))


@pytest.fixture(scope="module")
def expected(example: Any, result: Any) -> Any:
    """The deployment's own declaration of what the product should contain.

    Reached through ``deployment.expectation()`` rather than by re-reading the
    file, so the expectation is the same parsed artifact the fabric booted
    against and cannot drift from it.
    """
    return example.deployment.expectation(result.scenario.artifacts)


@pytest.fixture(scope="module")
def payload(result: Any) -> Any:
    return result.product.payload


# ---------------------------------------------------------------------------
# Preconditions — a vacuous pass is worse than a failure, because it is quiet.
# ---------------------------------------------------------------------------


def test_the_run_ingested_the_declared_signal(example: Any, result: Any) -> None:
    """Every assertion below is about what survived four operators. If nothing
    was ingested, they are all assertions about an empty graph."""
    ingested = example.deployment.envelope_count(result.scenario.envelopes)
    assert ingested > 0, "the run ingested no L1 envelopes"
    assert payload_is_populated(result.product.payload)


def payload_is_populated(payload: Any) -> bool:
    """The served payload names entities, classes and at least one party."""
    return bool(
        payload[PAYLOAD_ENTITY_COUNT]
        and payload[PAYLOAD_ENTITY_CLASSES]
        and payload[PAYLOAD_OWNERSHIP_BY_PARTY]
    )


def test_the_driver_loads_beside_a_same_named_module_from_another_tree() -> None:
    """The sibling-name collision, pinned so the loader's fix cannot rot.

    ``tests/deployment/`` is a package, so in a full-suite run
    ``sys.modules["deployment"]`` is already taken by the time this module is
    collected, and ``run.py``'s bare ``import deployment`` would otherwise
    return it. Running this file alone hides that entirely — which is how the
    collision reached a green targeted run and a red ``make ci-core``.

    A decoy is planted here so the case is exercised regardless of collection
    order, and the decoy is asserted to survive the load: shadowing the name
    must be temporary, or every test collected after this one loses
    ``tests/deployment``.
    """
    decoy = types.ModuleType("deployment")
    previous = sys.modules.get("deployment")
    sys.modules["deployment"] = decoy
    try:
        loaded = _load_example()
        assert pathlib.Path(loaded.deployment.__file__).parent == EXAMPLE_DIR
        assert sys.modules["deployment"] is decoy, (
            "the loader left the example's module shadowing the name it"
            " borrowed — later tests would import the wrong `deployment`"
        )
    finally:
        if previous is None:
            sys.modules.pop("deployment", None)
        else:
            sys.modules["deployment"] = previous


def test_the_expectation_document_declares_something(expected: Any) -> None:
    """An empty ``expected.yaml`` would make the comparisons below trivially
    true. It is the source of every domain expectation in this module, so its
    emptiness is checked rather than assumed."""
    assert expected[PAYLOAD_ENTITY_COUNT] > 0
    assert expected[PAYLOAD_BENEFICIAL_OWNERS]
    assert any(key.startswith(ABSENCE_PREFIX) for key in expected)


# ---------------------------------------------------------------------------
# The gates.
# ---------------------------------------------------------------------------


def test_the_product_passed_all_three_gates(result: Any) -> None:
    """``ServableProduct`` is not constructible outside ``run_gates``, so a
    served product IS the evidence the gates ran (INV-CH7-52)."""
    assert result.product is not None
    assert result.served.replay_ref is not None


def test_lineage_strict_equality_holds(result: Any) -> None:
    """What the product claims ran is exactly what the engine resolved
    (INV-CH7-47).

    **A propagation check, and worth being exact about which one.**
    ``run_gates`` has already compared these two values — that IS Gate 2 — and a
    ``ServableProduct`` is not constructible without it. What this adds is that
    the property survived onto the objects the spine actually returns: it fails
    if the driver serves a product other than the one it gated, or reports a
    transcription other than the one it gated against.
    """
    assert result.product.lineage.operators_invoked == result.operators_invoked


def test_every_declared_operator_actually_ran(result: Any) -> None:
    """The set the product class DECLARED it requires is exactly the set the
    engine RESOLVED, and all four canonical categories are in it.

    The executed set traces to ``projection-requirements.yaml`` and the declared
    set to ``product-class.yaml`` — two documents an author can edit apart, held
    together by ``refuse_operator_set_divergence``, which refuses a disagreement
    before the engine runs.

    **The caveat travels with the assertion (SURFACE-AUDIT A-4).** Still not
    proven here: that the two documents were *authored* rather than copied. A
    deployment that reads one into the other collapses the binder upstream and
    this check with it, and this assertion goes back to comparing one value
    against itself with nothing in the output to show for it — the residual
    D-IMPL-86 names and accepts. So this must never be promoted as a proof that
    the two sets are separately witnessed, and the binder must never be
    described as making dual authorship structural. It does not.
    """
    declared = result.scenario.product_class
    assert set(declared.required_operator_keys) == set(result.operators_invoked)
    assert len(result.operators_invoked) == len(set(result.operators_invoked))


@pytest.mark.parametrize(
    "category", ["traversal", "temporal", "policy", "similarity"]
)
def test_all_four_operator_categories_ran(result: Any, category: str) -> None:
    """The whitepaper's four canonical categories (§7.4), each represented.

    The category names are SDK mechanism — ``src/ccf/operators/categories.py``
    ships exactly these four — so they are written here rather than read from a
    deployment artifact. Which *key* each category is registered under is
    deployment vocabulary, and is not asserted.
    """
    assert any(
        key.startswith(f"{category}.") for key in result.operators_invoked
    ), f"no {category} operator in {sorted(result.operators_invoked)}"


# ---------------------------------------------------------------------------
# The served product.
# ---------------------------------------------------------------------------


def test_the_run_serves_the_tenant_and_class_the_artifacts_name(
    result: Any,
) -> None:
    """A propagation check on identity: schema name, lane and tenant."""
    declared = result.scenario.product_class
    assert result.product.schema_name == declared.schema_name
    assert result.product.schema_version == declared.schema_version
    assert result.product.tenant_id == result.tenant_id


def test_the_served_shape_matches_the_declared_expectation(
    expected: Any, payload: Any
) -> None:
    """What survived the four operators, against the deployment's declaration.

    An independent expectation: the counts follow from the events, the
    resolution spec and the operator parameters, and ``expected.yaml`` derives
    nothing from them.
    """
    assert payload[PAYLOAD_ENTITY_COUNT] == expected[PAYLOAD_ENTITY_COUNT], payload
    assert payload[PAYLOAD_ENTITY_CLASSES] == sorted(
        expected[PAYLOAD_ENTITY_CLASSES]
    ), payload
    assert (
        payload[PAYLOAD_ENTITY_COUNT_BY_CLASS]
        == expected[PAYLOAD_ENTITY_COUNT_BY_CLASS]
    ), payload
    assert payload[PAYLOAD_RELATIONSHIP_TYPES] == sorted(
        expected[PAYLOAD_RELATIONSHIP_TYPES]
    ), payload


def test_the_aggregate_ownership_answer_matches_the_declared_expectation(
    expected: Any, payload: Any
) -> None:
    """The answer itself, per party, against the deployment's declaration.

    An independent expectation, and the one that carries the example: these
    percentages are sums over ownership paths, and no record in the source
    estate states any of them.
    """
    assert (
        payload[PAYLOAD_OWNERSHIP_BY_PARTY] == expected[PAYLOAD_OWNERSHIP_BY_PARTY]
    ), payload

    served = [
        (owner[OWNER_PARTY_REF], owner[OWNER_PERCENT])
        for owner in payload[PAYLOAD_BENEFICIAL_OWNERS]
    ]
    declared = [
        (owner[OWNER_PARTY_REF], owner[OWNER_PERCENT])
        for owner in expected[PAYLOAD_BENEFICIAL_OWNERS]
    ]
    assert served == declared, payload


def test_the_answer_is_a_sum_over_paths_not_a_single_hop(
    expected: Any, payload: Any
) -> None:
    """The multi-hop property, asserted rather than assumed.

    ``expected.yaml`` names a ``boundary_case_party``: a natural person whose
    stake **one hop down** is exactly the regime's threshold, and whose interest
    in the *subject* three hops down is a fraction of a percent. A projection
    that read ownership one hop at a time would report her at the threshold and
    call her a beneficial owner. Aggregating across the chain puts her well
    below it and out of the answer.

    So this fails in exactly the case worth catching: a regression from
    aggregation-over-paths to lookup. The reported figure being strictly between
    zero and the threshold is the whole assertion — zero would mean the chain
    was not walked at all, and reaching the threshold would mean it was walked
    only once.
    """
    party = expected[EXPECTED_BOUNDARY_CASE]
    holdings = payload[PAYLOAD_OWNERSHIP_BY_PARTY]
    threshold = Decimal(payload[PAYLOAD_THRESHOLD])

    assert party in holdings, holdings
    reported = Decimal(holdings[party])
    assert Decimal(0) < reported < threshold, (
        f"{party} is reported at {reported}; a single-hop reading would put"
        f" her at the {threshold} threshold and wrongly in the answer"
    )
    assert party not in {
        owner[OWNER_PARTY_REF] for owner in payload[PAYLOAD_BENEFICIAL_OWNERS]
    }


def test_every_declared_absence_really_is_absent(
    expected: Any, payload: Any
) -> None:
    """Each ``absent_by_*`` witness names an operator and what it removed.

    If any of these references surfaces anywhere in the served payload, the
    operator named beside it in ``expected.yaml`` has stopped working — a
    jurisdiction-restricted party still visible, a below-floor screening
    candidate still ranked, an edge type the traversal was never given, or an
    observation that is not yet legally effective at the boundary.

    Checked against the serialized payload rather than against one field,
    because a witness can leak through any of them.
    """
    served = json.dumps(payload, sort_keys=True)
    witnesses = {
        reference
        for key, block in expected.items()
        if key.startswith(ABSENCE_PREFIX)
        for reference in block
    }
    assert witnesses, "expected.yaml declares no absences to check"

    leaked = sorted(reference for reference in witnesses if reference in served)
    assert not leaked, (
        f"references the pipeline was supposed to remove are in the served"
        f" product: {leaked}"
    )


def test_the_product_answers_the_question_the_caller_asked(
    result: Any, payload: Any
) -> None:
    """Propagation checks on the question, the role and the threshold.

    **The subject is checked against the REQUEST, not against an artifact**
    (plan ``15.5-13``). It used to be a Control Plane statement — a
    ``subject_entity_ref`` key in ``ubo-question.yaml`` — which is what made
    this product configurable rather than callable. It is now
    :attr:`ccf.products.request.ProductRequest.subject`, so this assertion is
    the one that fails if the fabric answers about a company other than the one
    it was asked about. The threshold stays a Control Plane statement, because
    what interest the regime treats as beneficial ownership genuinely is
    governance and not a caller's choice.

    Both instants are checked against the request for the same reason: the
    boundary is ``asked_at`` and the decision instant is the class-declared
    request parameter, so a product whose TTL ran from something else is a
    wiring fault.
    """
    scenario = result.scenario
    assert payload[PAYLOAD_SUBJECT] == scenario.request.subject
    assert result.product.temporal_boundary == scenario.request.asked_at
    assert payload[PAYLOAD_ROLE] == scenario.perspective.role
    assert Decimal(payload[PAYLOAD_THRESHOLD]) == scenario.threshold_percent
    assert result.product.plan_id == scenario.plan_id
    assert result.product.temporal_boundary == scenario.temporal_boundary
    assert result.product.expires_at == scenario.expires_at


# ---------------------------------------------------------------------------
# The replay record.
# ---------------------------------------------------------------------------


def test_the_replay_record_is_in_the_store_content_addressed(result: Any) -> None:
    """The address being the record's own content hash is an SDK mechanism
    claim, so it is computed here rather than read from an artifact."""
    address = result.served.replay_ref.content_address
    assert result.store.exists(content_address=address)
    assert address == content_hash(result.record)


def test_the_stored_record_round_trips_exactly(result: Any) -> None:
    """Not merely parseable — equal."""
    restored = DecisionReplayRecord.model_validate_json(
        result.store.get(content_address=result.served.replay_ref.content_address)
    )
    assert restored == result.record


def test_the_record_carries_all_five_dimensions(result: Any) -> None:
    """Whitepaper §7.10.1, asserted against the stored bytes rather than the
    in-memory record, so this covers the round trip as well as the
    construction."""
    restored = DecisionReplayRecord.model_validate_json(
        result.store.get(content_address=result.served.replay_ref.content_address)
    )
    scenario = result.scenario

    # 1 — context fabric snapshot, at the boundary the deployment declared.
    assert restored.context_fabric_snapshot.temporal_boundary == (
        scenario.temporal_boundary
    )
    # 2 — policy bindings. **A SUBSET RELATION, NOT AN EQUALITY** (`D-IMPL-310`).
    #     The two accounts answer different questions: the product's lineage
    #     says which POLICY BUNDLE versions shaped this product, and dimension 2
    #     says which governed Control Plane bindings shaped the request and the
    #     determination. The second is the broader set, and the canonical path
    #     carries a binding the hand-composed spine never built — the version of
    #     the REQUEST CONTRACT, which governed what question could be asked and
    #     how its parameters were interpreted. That is better governance
    #     evidence, not migration drift, and it is not stuffed into
    #     `policy_bundle_versions` to restore a set equality that was only ever
    #     true because one spine populated both sides from one value.
    #
    #     Both limbs are checked against sources INDEPENDENT of the record, for
    #     the reason `operators_invoked` is: a test whose two sides come off the
    #     same object compares a value with itself.
    bound = {binding.key: binding.version for binding in restored.policy_bindings.bindings}

    #     (a) every policy-bundle version the PRODUCT carries is in the record,
    #         under the deployment's own key, at the same version.
    assert bound.get(scenario.policy_bundle_key) == _the_one_policy_version(result)

    #     (b) and the request contract that governed the question is bound too,
    #         at the version of the CONTRACT ITSELF — re-derived here the way
    #         the Control Plane mints a version (`content_hash`,
    #         `ccf.controlplane.registry`), off the contract `deployment.py`
    #         parsed for this run, so neither side of this comparison came from
    #         the record. `scenario.artifacts` holds a `DeclaredArtifact`
    #         WRAPPER whose hash is a different value; the version is the
    #         contract's own, which is why this reads `scenario.request_contract`
    #         rather than the manifest entry.
    assert bound.get(scenario.request_contract_artifact_key) == content_hash(
        scenario.request_contract
    )
    # 3 — model version. SDK mechanism: this deployment is keyless, and the
    #     assembly mode is the governance claim the product class authored
    #     (D-IMPL-94, Q-2 — the field describes how the SUBSTRATE was
    #     assembled).
    assert restored.model_version.model_version == "none"
    assert restored.model_version.assembly_mode == scenario.product_class.assembly_mode
    # 4 — perspective conditioning, from the perspective artifact.
    assert restored.perspective_conditioning.role == scenario.perspective.role
    # 5 — content generation path.
    assert restored.content_generation_path.plan_id == result.product.plan_id

    assert restored.recorded_at == scenario.now
    assert restored.tenant_id == result.tenant_id


def _the_one_policy_version(result: Any) -> str:
    """The single policy-bundle version the served product's lineage carries.

    Still exactly one, and that is a claim about the PRODUCT (`D-IMPL-310`):
    this deployment's state is assembled under one bundle. The record may bind
    more governed artifacts than that, and does.
    """
    versions = result.product.lineage.policy_bundle_versions
    assert len(versions) == 1, versions
    return next(iter(versions))


def test_the_record_is_written_before_the_product_is_delivered(
    result: Any,
) -> None:
    """There is no branch that reaches a served product without a recorded
    decision (INV-CH7-79): the reference the caller holds resolves in the store
    the run wrote, under the artifact class the deployment declared."""
    reference = result.served.replay_ref
    assert reference.artifact_class == result.scenario.replay_record_class
    assert reference.tenant_id == result.tenant_id
    assert result.store.exists(content_address=reference.content_address)


# ---------------------------------------------------------------------------
# Assemble, not aggregate — the three declared questions (plan 15.5-13).
#
# Every assertion below runs against `answers`, which asks all three questions
# `artifacts/questions.yaml` declares, each against its own fabric. The module
# fixture above stays a single run because the assertions above it are about one
# product; these are about the DIFFERENCES between products, which is a
# different claim and needs a different fixture.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def questions(example: Any) -> Any:
    """The declared questions, typed, as the driver builds them."""
    return example.deployment.declared_questions()


@pytest.fixture(scope="module")
def answers(
    example: Any,
    questions: Any,
    fluree_url: str,
    tmp_path_factory: pytest.TempPathFactory,
) -> Any:
    """One answered product per declared question, in declaration order."""
    del fluree_url  # Requested as the gate; see `result` above.
    return example.ask_all(
        root=tmp_path_factory.mktemp("s1-01-questions"), requests=questions
    )


def test_the_declared_questions_are_a_controlled_experiment(questions: Any) -> None:
    """A precondition, because every claim below is about a contrast.

    Two of the three share a subject and differ in instant; two share an instant
    and differ in subject. If a future edit collapsed that structure the
    assertions below would still pass while demonstrating nothing, which is the
    quiet failure this file exists to avoid.
    """
    assert len(questions) >= 3
    subjects = {question.subject for question in questions}
    instants = {question.asked_at for question in questions}
    assert len(subjects) > 1, "no two questions differ in subject"
    assert len(instants) > 1, "no two questions differ in instant"


def test_each_question_gets_its_own_graph(
    example: Any, fluree_url: str, tmp_path: pathlib.Path
) -> None:
    """**SDK-adjacent mechanism claim.** ``ask_all``'s isolation survived the
    substrate move.

    Three calls, ONE root, three different composed connections. The root being
    held constant is the whole assertion: it proves the isolating value is
    minted per call rather than derived from the caller's directory, which is
    what makes it work on a server two runs share. Before the move, a
    per-question temp directory isolated the ArtifactStore *and* the graph; now
    the directory isolates the store and the composed connection isolates the
    graph, and this is the half that would otherwise fail silently — two runs
    would answer correctly while having observed each other.
    """
    del fluree_url  # Requested as the gate; see `result` above.
    composed = [
        example.deployment.connection(root=tmp_path) for _ in range(3)
    ]
    distinct = {tuple(sorted(values.items())) for values in composed}
    assert len(distinct) == len(composed), (
        f"three connections composed for one root are not distinct: {composed}"
    )


def test_the_products_address_survives_a_different_graph_identity(
    result: Any, answers: Any
) -> None:
    """**SDK mechanism claim.** The graph's identity is not in the address.

    ``result`` and ``answers[0]`` are the same question asked twice, in two
    whole runs, against two graphs with different identities. The content
    address is byte-identical, which is what makes replay a property of the
    question and the Control Plane rather than of where the bytes happened to
    be stored. It would fail if a connection value leaked onto the product.
    """
    assert content_hash(result.product) == content_hash(answers[0].product)


def test_a_different_company_gets_a_different_answer(
    expected: Any, answers: Any
) -> None:
    """**Independent expectation.** The second question's answer follows from
    the events, the resolution spec and the operator parameters read from a
    different anchor; ``expected.yaml`` derives none of it.

    This is the claim the whole phase turns on. One product class, one graph,
    one ingest — and the answer to *"who ultimately owns this?"* is a different
    set of people with different percentages depending on which company was
    asked about. A precomputed aggregate cannot hold both.
    """
    declared = expected[EXPECTED_SECOND_QUESTION]
    payload = answers[1].product.payload

    assert payload[PAYLOAD_SUBJECT] == declared[PAYLOAD_SUBJECT]
    assert payload[PAYLOAD_ENTITY_COUNT] == declared[PAYLOAD_ENTITY_COUNT]
    assert (
        payload[PAYLOAD_OWNERSHIP_BY_PARTY] == declared[PAYLOAD_OWNERSHIP_BY_PARTY]
    ), payload
    assert _owners(payload) == _owners(declared), payload
    assert _owners(payload) != _owners(answers[0].product.payload), (
        "the first two questions returned the same beneficial owners; the"
        " subject is not reaching the projection"
    )


def test_the_same_company_at_a_later_instant_gets_a_different_answer(
    expected: Any, answers: Any
) -> None:
    """**Independent expectation.** The third question re-asks the first at a
    later boundary, against a graph nothing was added to in between.

    A share transfer recorded before 1 August and legally effective in September
    is invisible in the first answer and decisive in the third: a natural person
    who was not a beneficial owner becomes one. The fabric knew about the
    transfer the whole time — which is exactly why *"when are you asking?"* is
    part of the question and not part of the configuration.
    """
    declared = expected[EXPECTED_THIRD_QUESTION]
    first, third = answers[0].product, answers[2].product

    assert third.payload[PAYLOAD_SUBJECT] == first.payload[PAYLOAD_SUBJECT], (
        "questions 1 and 3 must share a subject, or this contrast is about two"
        " things at once"
    )
    assert third.temporal_boundary > first.temporal_boundary
    assert third.payload[PAYLOAD_ENTITY_COUNT] == declared[PAYLOAD_ENTITY_COUNT]
    assert (
        third.payload[PAYLOAD_OWNERSHIP_BY_PARTY]
        == declared[PAYLOAD_OWNERSHIP_BY_PARTY]
    ), third.payload
    assert _owners(third.payload) == _owners(declared), third.payload

    appeared = set(_owners(third.payload)) - set(_owners(first.payload))
    assert {reference for reference, _percent in appeared} == set(
        declared[EXPECTED_NEWLY_VISIBLE]
    ), (
        "the later boundary did not admit the party the expectation says it"
        " should; the temporal operator is not reading the request's instant"
    )


def test_every_pinned_query_resolves_to_the_bytes_it_names(answers: Any) -> None:
    """**SDK mechanism claim.** The record pins which questions were put to the
    graph, and every pin is resolvable.

    ``serve()`` persists the canonical query bytes BEFORE it appends the record,
    so no moment exists at which a recorded pin dangles (T-15.2-28). That
    mechanism shipped in plan 15.2-08 and this example is the reason it had
    never been exercised: ``serve()`` was called without a ``QueryPinWriter``,
    so the record pinned questions nothing could resolve.

    Computed here rather than read from an artifact because the pin being the
    query's own ``content_hash`` is a claim about the SDK, not about this
    deployment.
    """
    for answered in answers:
        pinned = answered.record.content_generation_path.graph_query_sequence
        assert pinned, "the record pins no graph query at all"
        assert pinned != NO_GRAPH_QUERIES
        for pin in pinned:
            assert answered.store.exists(content_address=pin), (
                f"pin {pin} names bytes the store does not hold"
            )


def test_a_later_instant_pins_a_different_question_to_the_graph(
    answers: Any,
) -> None:
    """**Independent expectation.** The pins distinguish the graph reads.

    Questions 1 and 3 differ only in when they were asked, and the boundary is
    inside the compiled query — so the pinned sequence differs. An auditor
    asking *"which question did this decision answer?"* gets a different answer
    for the two, from the record alone.

    **The two-subject guard, INVERTED (D-IMPL-111 limb (a)).** Until
    2026-08-11 this test carried the opposite assertion, because the property
    was the opposite: the subject entered only at Π, so questions 1 and 2
    compiled to the same graph query and pinned identically, and this file said
    so rather than claiming a property the mechanism did not have
    (``DI-15.5-07``). The request's subject now seeds the traversal, so the two
    pin **differently** — and the guard is kept, pointing the other way, so that
    a regression which put the anchor back inside Π alone would fail here
    loudly instead of quietly restoring a repudiation gap.

    The **first** pin is still shared. That segment carries the policy family
    and no walk, so there is nothing for an anchor to start in it (`GQ-03`) and
    the engine hands it no seeds. Asserting both halves is what makes this a
    statement about *where* the subject enters rather than a smoke test.
    """
    first, second, third = (
        answered.record.content_generation_path.graph_query_sequence
        for answered in answers[:3]
    )
    assert first != third, (
        "two boundaries produced the same pinned query sequence; the request's"
        " instant is not reaching the compiled query"
    )
    assert first != second, (
        "questions 1 and 2 pinned the same graph queries; the request's subject"
        " is not reaching the compiled query and the record cannot say which"
        " subject this decision was about (DI-15.5-07, D-IMPL-111 limb (a))"
    )
    assert first[0] == second[0], (
        "the non-walking segment's pin moved with the subject; seeds are"
        " reaching a segment that has no walk for them to start (`GQ-03`)"
    )


def test_the_delivered_product_carries_its_debt(expected: Any, answers: Any) -> None:
    """**Propagation check.** D_c rides the vessel and reaches the caller.

    Debt *"is a runtime signal the agent must consume as a first-class decision
    input, not a log-line to be read after the fact"* — so this fails on a
    wiring fault: a product served with ``debt=None`` is a product whose
    consumer has no way to know how much to trust it (D-IMPL-100).
    """
    for answered in answers:
        assessment = answered.product.debt
        assert assessment is not None, "the served product carries no debt"
        assert Decimal(0) <= assessment.debt <= Decimal(1)
        assert assessment.scorers, "no scorer is pinned beside the factor it produced"

    assert answers[0].product.debt.signal.value == (
        expected[EXPECTED_DEBT_SIGNAL_FIRST]
    )


def test_the_debt_figure_is_measured_and_not_constant(
    expected: Any, answers: Any
) -> None:
    """**Independent expectation.** Stale constituent data reads as more debt.

    Questions 1 and 3 assemble against the same graph and differ only in when
    they were asked. Six weeks of decay against the λ_c table drives freshness
    down and D_c up, far enough to cross this deployment's Forced-LLM band — so
    the CAR routing state on the delivered product is a measurement, not a
    constant. Nothing in ``expected.yaml`` supplies the figures; it declares
    only which band its own calibration should route each to.

    The last assertion is the one a KYC analyst needs: the assessment says
    WHICH dimension is weak, not only how weak (D-IMPL-99). Freshness moves;
    completeness and semantic consistency do not.
    """
    fresh, stale = answers[0].product.debt, answers[2].product.debt

    assert stale.debt > fresh.debt, (
        f"the later question measured no more debt ({stale.debt}) than the"
        f" earlier one ({fresh.debt}); the figure is not measured"
    )
    assert fresh.signal.value == expected[EXPECTED_DEBT_SIGNAL_FIRST]
    assert stale.signal.value == expected[EXPECTED_DEBT_SIGNAL_THIRD]

    weak = expected[EXPECTED_DEBT_WEAK_FACTOR]
    assert getattr(stale.factors, weak) < getattr(fresh.factors, weak)
    unchanged = [
        factor
        for factor in ("freshness", "completeness", "semantic_consistency")
        if factor != weak
    ]
    for factor in unchanged:
        assert getattr(stale.factors, factor) == getattr(fresh.factors, factor), (
            f"{factor} moved as well as {weak}; the contrast no longer isolates"
            " a single dimension"
        )


def test_the_routing_state_carries_what_this_deployment_says_it_obliges(
    expected: Any, answers: Any
) -> None:
    """**The demonstration of `D-IMPL-112` gap 3, and the closing of it.**

    Before this, a consumer shown `signal: forced_llm` learned that the fabric
    had escalated and nothing about what escalation *required of them* —
    `15.6-RESEARCH.md` § B4 measured `FORCED_LLM` as produced at one site and
    consumed at none. Now the delivered product answers, in the deployment's
    own words, and the fabric still takes no action on it.

    Both halves are asserted because either alone is misleading. Question 1
    routes to `ok`, which `artifacts/debt-profile.yaml` deliberately leaves
    unbound, so its product carries the SDK's named sentinel: a partly-bound
    calibration is legal and an unbound state is a positive claim rather than a
    silence (`D-IMPL-38`). Question 3 routes to `forced_llm` six weeks later
    against the same graph, and carries the obligation the artifact declares.

    The last assertion is the one that matters for CLAUDE.md §11: the obligation
    the consumer reads is byte-identical to the string in the artifact, so no
    part of it came from CCF. The SDK supplied the binding and the carrying;
    the deployment supplied every word.
    """
    fresh, stale = answers[0], answers[2]

    assert fresh.product.debt.signal.value == expected[EXPECTED_DEBT_SIGNAL_FIRST]
    assert fresh.product.obligation_in_force == expected[EXPECTED_OBLIGATION_FIRST]

    assert stale.product.debt.signal.value == expected[EXPECTED_DEBT_SIGNAL_THIRD]
    assert stale.product.obligation_in_force == expected[EXPECTED_OBLIGATION_THIRD]
    assert stale.product.obligation_in_force != fresh.product.obligation_in_force

    declared = yaml.safe_load(
        (EXAMPLE_DIR / "artifacts" / "debt-profile.yaml").read_text(
            encoding="utf-8"
        )
    )
    bound = {
        entry["signal"]: entry["obligation_ref"]
        for entry in declared["signal_obligations"]
    }
    assert bound[expected[EXPECTED_DEBT_SIGNAL_THIRD]] == (
        stale.product.obligation_in_force
    ), (
        "the delivered obligation is not the artifact's — some part of it came"
        " from somewhere other than this deployment's Control Plane"
    )
    assert expected[EXPECTED_DEBT_SIGNAL_FIRST] not in bound


def test_the_obligation_in_force_is_pinned_into_the_replay_record(
    expected: Any, answers: Any
) -> None:
    """Dimension 5 records the obligation, so a rebinding cannot rewrite it.

    The audit question is *"what was this decision obliged to do?"*, and the
    only defensible answer resolves the binding in force **then**. The record
    carries it rather than pointing at the profile, which is what makes the
    answer survive `artifacts/debt-profile.yaml` being edited tomorrow —
    `D-IMPL-26`: replay resolves exact versions, never "latest".
    """
    for answered in answers:
        path = answered.record.content_generation_path
        assert path.obligation_in_force == answered.product.obligation_in_force

    assert answers[2].record.content_generation_path.obligation_in_force == (
        expected[EXPECTED_OBLIGATION_THIRD]
    )


# ---------------------------------------------------------------------------
# The printed report (Dave's ruling, 2026-08-13 — the example prints its work).
#
# Anchored values only. **No assertion here matches a heading's prose, a
# sentence or a phrasing**: the six section-heading tokens are the sole
# exception and are asserted as literal tokens, because they are the contract
# between the renderer and anyone reading its output. Everything else is a value
# computed independently on this side — which is what makes a report showing a
# stale address, a dropped near-miss or a ruled-absent pointer go red.
# ---------------------------------------------------------------------------

#: The six headings ``report.py`` promises. Literals rather than a reach into
#: the renderer's own constants — importing them would be the test agreeing
#: with itself about what it is checking.
REPORT_HEADINGS = (
    "QUESTION",
    "WHAT WAS ASSEMBLED",
    "WHAT THE FABRIC DID",
    "THE ANSWER",
    "WHAT TRAVELS WITH THE ANSWER",
)


@pytest.fixture(scope="module")
def rendered(example: Any, result: Any) -> str:
    """One question's report, as text. The renderer prints nothing itself."""
    return str(example.report.render(result, index=1, total=1))


@pytest.fixture(scope="module")
def rendered_contrast(example: Any, answers: Any) -> str:
    """The closing contrast across the three declared questions."""
    return str(example.report.render_contrast(answers))


def test_the_report_opens_the_sections_it_promises(rendered: str) -> None:
    """The heading tokens, and only the tokens."""
    for heading in REPORT_HEADINGS:
        assert heading in rendered, heading


def test_the_report_carries_the_products_own_content_address(
    result: Any, rendered: str
) -> None:
    """**Propagation check.** The address shown is this product's.

    Computed independently on this side, so a report rendering a cached or
    stale address — the one failure a reader could not possibly catch by
    eye — fails here instead.
    """
    assert content_hash(result.product) in rendered


def test_the_report_names_every_party_in_the_answer_and_the_near_miss(
    expected: Any, payload: Any, rendered: str
) -> None:
    """**Independent expectation.** Nobody in the answer is dropped, and
    neither is the party the threshold removed.

    The near-miss is the line that shows the threshold doing work. A report
    that printed only the owners would read as a lookup, which is the thing
    this example exists to contrast against.
    """
    for owner in payload[PAYLOAD_BENEFICIAL_OWNERS]:
        assert owner[OWNER_PARTY_REF] in rendered, owner
    assert expected[EXPECTED_BOUNDARY_CASE] in rendered


def test_the_report_shows_the_refresh_window_and_names_no_source(
    example: Any, result: Any, rendered: str
) -> None:
    """**The D-IMPL-124 assertion, stated as an absence.**

    The window's two instants are shown; not one of the per-source references
    ``product-governance.yaml`` declares reaches the terminal. The report is a
    disclosure surface, and the boundary the deployment drew upstream has to
    hold at the point a human reads it.
    """
    window = result.product.source_refresh_recency
    assert str(window.oldest_source_refresh_at) in rendered
    assert str(window.newest_source_refresh_at) in rendered

    deployment = example.deployment
    governance = result.scenario.artifacts[
        deployment.KEY_PRODUCT_GOVERNANCE
    ].declaration
    declared = [
        entry[deployment.GOVERNANCE_SOURCE_REF]
        for entry in governance[deployment.GOVERNANCE_SOURCE_REFRESH_RECENCY]
    ]
    assert declared, "the governance document declares no source to check for"
    leaked = [reference for reference in declared if reference in rendered]
    assert not leaked, f"the report names upstream sources: {leaked}"


def test_the_report_invents_no_debt_evidence_pointer(
    result: Any, rendered: str
) -> None:
    """**The D-IMPL-119 limb 3(b) assertion.**

    Every entity URI the assembly touched is checked for absence from the
    rendered text. The ruling omits evidence pointers entirely for now, and
    limb 4 refuses a handle that is merely encoded — so a report that helpfully
    printed one, or anything derived from one, would put back exactly what the
    ruling removed.

    ``touched_entities`` is dimension 1's own record of what the assembly saw,
    which is why it is the set checked rather than a re-derivation.
    """
    touched = result.record.context_fabric_snapshot.touched_entities
    assert touched, "the record names no touched entity, so this checks nothing"
    leaked = [uri for uri in touched if uri in rendered]
    assert not leaked, f"the report carries entity URIs from the view: {leaked}"


def test_the_contrast_shows_three_distinct_addresses(
    answers: Any, rendered_contrast: str
) -> None:
    """**The controlled experiment, in the output.** Three questions, three
    addresses, each separately replayable — and every one of them printed."""
    addresses = {content_hash(answered.product) for answered in answers}
    assert len(addresses) == len(answers)
    for address in addresses:
        assert address in rendered_contrast, address
    assert "WHAT THE THREE QUESTIONS SHOW" in rendered_contrast


def test_the_renderers_return_text_and_print_nothing(
    example: Any, result: Any, answers: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Purity, asserted rather than assumed.

    ``run.py`` prints; ``report.py`` returns. That split is what lets every
    assertion above read the text without a capture fixture, and it is what
    keeps ``--quiet`` a single branch in the driver rather than a mode the
    renderer has to know about.
    """
    capsys.readouterr()
    one = example.report.render(result, index=1, total=1)
    both = example.report.render_contrast(answers)
    captured = capsys.readouterr()

    assert isinstance(one, str) and one
    assert isinstance(both, str) and both
    assert captured.out == "" and captured.err == ""


def _owners(payload: Any) -> list[tuple[str, str]]:
    """``(party_ref, aggregate_percent)`` pairs, in served order."""
    return [
        (owner[OWNER_PARTY_REF], owner[OWNER_PERCENT])
        for owner in payload[PAYLOAD_BENEFICIAL_OWNERS]
    ]


def test_the_recorded_boundary_is_data_and_not_a_clock_read(result: Any) -> None:
    """The decision instant and the boundary are authored values.

    A fabric that stamped ``datetime.now()`` anywhere in this path would produce
    a record that cannot be replayed bit for bit, and the failure would be
    invisible in a single run. Both instants are compared against the artifact
    that declares them.
    """
    scenario = result.scenario
    assert isinstance(scenario.temporal_boundary, datetime)
    assert scenario.temporal_boundary < scenario.now < scenario.expires_at
    assert result.record.recorded_at == scenario.now
