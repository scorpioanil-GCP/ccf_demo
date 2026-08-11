"""The KYC/UBO example's assertions, under a runner that can actually fail.

``examples/s1-01-hello-context-product/run.py`` asserts nothing and prints
nothing (phase 16 CONTEXT `D-09`). ``make example-s1-01`` exiting zero proves the
spine *ran*; this module proves it computed the right answer. A printed summary
nobody reads was never a guarantee, and an assertion inside a driver only fails
a build if someone remembers to run the driver.

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

from ccf.contracts.canonical import content_hash
from ccf.replay.record import DecisionReplayRecord

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

#: Every ``absent_by_*`` block is a witness: a reference the pipeline must have
#: removed, and the operator that removed it. Prefix-matched rather than listed,
#: so a witness added to ``expected.yaml`` is checked without editing this file.
ABSENCE_PREFIX = "absent_by_"

#: The bare names ``run.py`` imports its siblings under. Shadowed for the
#: duration of the load — see :func:`_load_example` — because ``deployment``
#: also names a package under ``tests/``.
SIBLING_MODULES = ("deployment", "spine", "source_estate")


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
def result(example: Any, tmp_path_factory: pytest.TempPathFactory) -> Any:
    """One run of the spine, shared across the module.

    Module-scoped deliberately: the spine is the unit under test, and running it
    once per assertion would say nothing extra while paying for a full boot each
    time.
    """
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
    # 2 — policy bindings. The record's binding and the product's lineage are
    #     built by two separate calls taking two different argument shapes, so
    #     this fails if either is wired to the wrong pin. It does NOT
    #     independently re-derive the version — the pin has one source, by
    #     design — and claiming otherwise would be the tautology this module
    #     exists to avoid.
    assert [binding.version for binding in restored.policy_bindings.bindings] == [
        _the_one_policy_version(result)
    ]
    assert [binding.key for binding in restored.policy_bindings.bindings] == [
        scenario.policy_bundle_key
    ]
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
    """The single policy-bundle version the served product's lineage carries."""
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
