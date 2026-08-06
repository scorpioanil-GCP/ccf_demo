"""The quickstart's assertions, under a runner that can actually fail (D-09).

``examples/00-quickstart/run.py`` used to carry its own guarantee: eleven
``assert`` statements and six ``print`` summaries, checked by ``make example-00``
exiting zero. D-09 moves that guarantee here, because ``make examples`` proves a
spine *runs* and ``pytest`` proves it is *correct* — and a printed summary
nobody reads was never a guarantee at all.

Nothing is lost in the move. Each assertion below names the pre-rewrite line it
came from, so the "no loss of assertion coverage" claim is auditable against the
§1.3 baseline rather than merely stated:

===========================================  ==========================
pre-rewrite ``run.py`` line                   relocated to
===========================================  ==========================
:354 ``isinstance(gated, ServableProduct)``   the spine itself (a refusal
                                              now raises rather than being
                                              asserted away) **and**
                                              :func:`test_the_product_passed_all_three_gates`
:358 lineage == engine-resolved               :func:`test_lineage_strict_equality_holds`
:367 ``entity_count``                         :func:`test_the_served_payload_matches_the_declared_expectation`
:368 entity classes                           :func:`test_the_served_payload_matches_the_declared_expectation`
:371 relationship types                       :func:`test_the_served_payload_matches_the_declared_expectation`
:403 ``store.exists(...)``                    :func:`test_the_replay_record_is_in_the_store_content_addressed`
:406 address == ``content_hash(record)``      :func:`test_the_replay_record_is_in_the_store_content_addressed`
:410 ``restored == record``                   :func:`test_the_stored_record_round_trips_exactly`
:411 restored temporal boundary               :func:`test_the_record_carries_all_five_dimensions`
:412 policy binding versions                  :func:`test_the_record_carries_all_five_dimensions`
:416 ``model_version == "none"``              :func:`test_the_record_carries_all_five_dimensions`
:418 perspective role                         :func:`test_the_record_carries_all_five_dimensions`
:420 plan id                                  :func:`test_the_record_carries_all_five_dimensions`
:434 ``0 < retained <= 1``                    :func:`test_the_declared_observation_has_decayed_but_survives`
:437 print — tenant                           :func:`test_the_run_serves_the_tenant_and_class_the_artifacts_name`
:438 print — product schema name              :func:`test_the_run_serves_the_tenant_and_class_the_artifacts_name`
:439 print — entities served                  :func:`test_the_served_payload_matches_the_declared_expectation`
:440 print — operators invoked                :func:`test_every_declared_operator_actually_ran`
:441 print — replay record address            :func:`test_the_replay_record_is_in_the_store_content_addressed`
:443 print — freshness                        :func:`test_the_declared_observation_has_decayed_but_survives`
===========================================  ==========================

**Every domain expectation is read from an artifact, never inlined.** A value
this module authored would be the test agreeing with itself about what the
deployment's vocabulary says; read from ``expected.yaml``, the assertion is
against the deployment's own declaration. CINV-01 reaches ``tests/`` now
(D-IMPL-78) and would flag an inlined domain literal, but the discipline is the
point, not the lint.

The distinction that governs what stays a literal here: a **domain expectation**
comes from an artifact; an **SDK mechanism claim** — that a keyless deployment
records ``model_version: none``, that the replay reference is the record's own
content hash — is asserted directly, because it is a claim about the SDK rather
than about this deployment.

Two kinds of assertion, and the difference is worth stating
-----------------------------------------------------------

Reading expectations from artifacts produces two categories, and conflating
them is how a suite ends up claiming more than it checks:

* **Independent expectations.** ``expected.yaml`` declares what the *served
  product* should contain. Nothing in the pipeline derives those numbers from
  that file — they follow from the events, the ontology and the four operators
  — so changing either side alone makes the assertion fail. These are the
  correctness guarantees. Verified by mutation: changing ``entity_count`` or
  the relationship set breaks the suite.
* **Propagation checks.** The temporal boundary, the perspective role, the
  product's schema name and its required operator set are each read from an
  artifact by ``run.py`` *and* by this module, so the artifact is a single
  source and editing it moves both ends together. These assert that a declared
  value survives end to end into the served product and its replay record —
  which fails on a **wiring** fault, not on an artifact edit. Verified by
  mutation: re-introducing the ``operators.keys()`` shortcut, building the
  record from an undeclared perspective, or stamping a boundary the artifact
  does not name each break the suite.

Both belong here. Only the first is a statement about whether the fabric
computed the right answer, and this module does not claim otherwise.

The example is not a package, so it is loaded by file path with
``importlib.util`` — the pattern ``test_ext00_hardening.py`` established.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from datetime import datetime
from typing import Any

import pytest

from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import DeclaredArtifact, ProductClassDeclaration
from ccf.replay.record import DecisionReplayRecord

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "00-quickstart" / "run.py"


def _load_example() -> Any:
    """Load the example module by file path (the example dir is no package).

    The module is registered in ``sys.modules`` *before* execution: the example
    uses ``from __future__ import annotations``, so ``@dataclass`` resolves its
    field annotations by looking its own module up there, and a module absent
    from the table fails with an opaque ``AttributeError`` at class-definition
    time rather than anywhere near the cause.
    """
    name = "quickstart_under_test"
    spec = importlib.util.spec_from_file_location(name, EXAMPLE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def result(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """One run of the spine, shared across the module.

    Module-scoped deliberately: the spine is the unit under test, and running
    it once per assertion would say nothing extra while paying for a full boot
    each time.
    """
    root = tmp_path_factory.mktemp("quickstart")
    return _load_example().run(root=root)


def _declaration(result: Any, key: str) -> Any:
    """The deployment's own declaration under one manifest key.

    Reads through ``booted.artifacts``, so an expectation is sourced from the
    same parsed artifact the fabric ran against — not from a second read of the
    file, which could drift.
    """
    artifact = result.artifacts[key]
    assert isinstance(artifact, DeclaredArtifact), key
    return artifact.declaration


# --- the gates -------------------------------------------------------------


def test_the_product_passed_all_three_gates(result: Any) -> None:
    """Pre-rewrite :354. ``ServableProduct`` is not constructible outside
    ``run_gates``, so a served product IS the evidence the gates ran."""
    assert result.product is not None
    assert result.served.replay_ref is not None


def test_lineage_strict_equality_holds(result: Any) -> None:
    """Pre-rewrite :358. What the product claims ran is exactly what the engine
    resolved as having run (INV-CH7-47).

    Since design E2 (D-IMPL-86) the two operands trace to two documents: the
    claim to ``product-class.yaml`` through the product's lineage, the executed
    set to ``projection-requirements.yaml`` through the plan the engine ran.

    **A propagation check, and worth being exact about which one.** ``run_gates``
    has already compared these two values — that IS Gate 2 — and a
    ``ServableProduct`` is not constructible without it. What this adds is that
    the property survived onto the objects ``run()`` actually returns: it fails
    if the driver serves a product other than the one it gated, or reports a
    transcription other than the one it gated against.

    **What it does not catch, stated rather than implied.** It does not fire if
    the driver goes back to filling lineage from ``execution`` (post-gate review
    WR-03). Under that reversion both sides become
    ``execution.operators_invoked`` and this holds trivially. No other
    output-level assertion would see it either:
    ``refuse_operator_set_divergence`` forces the declared set, the plan's
    required set and the engine's invoked set equal before the engine runs, so
    by the time there is a product there is only one value to compare against
    itself. That reversion is guarded at the source level, over the driver's
    call shape (``tests/products/test_gate_two_call_shape.py``), because the
    output cannot show it.

    Nor does this prove the two documents were authored independently. A
    deployment that reads one artifact into the other collapses the binder
    upstream and this check with it — the residual D-IMPL-86 names and accepts.
    """
    assert result.product.lineage.operators_invoked == result.operators_invoked


def test_every_declared_operator_actually_ran(result: Any) -> None:
    """Pre-rewrite :440's print, as a check.

    The count alone was never the interesting fact. This asserts the stronger
    property the count was standing in for: the set the product class DECLARED
    it requires is exactly the set the engine RESOLVED.

    Before design E2 (D-IMPL-86) those two were the same value arriving by two
    paths — the declaration fed the plan, the plan fed the operator plan, and
    the engine returned ``frozenset(outputs)`` — so this could not fail. It can
    now: the executed set traces to ``projection-requirements.yaml`` and the
    declared set to ``product-class.yaml``, two documents an author can edit
    apart, held together by ``refuse_operator_set_divergence``.

    Still not proven here: that the two were authored rather than copied. A
    deployment that reads one document into the other collapses the binder, and
    this assertion goes back to comparing one value against itself with nothing
    in the output to show for it.
    """
    declared = result.artifacts["product-class"]
    assert isinstance(declared, ProductClassDeclaration)
    assert set(declared.required_operator_keys) == set(result.operators_invoked)


# --- the served product ----------------------------------------------------


def test_the_run_serves_the_tenant_and_class_the_artifacts_name(
    result: Any,
) -> None:
    """Pre-rewrite :437 and :438's prints, as checks against the artifacts."""
    declared = result.artifacts["product-class"]
    assert isinstance(declared, ProductClassDeclaration)
    assert result.product.schema_name == declared.schema_name
    assert result.product.schema_version == declared.schema_version
    assert result.product.tenant_id == result.tenant_id


def test_the_served_payload_matches_the_declared_expectation(
    result: Any,
) -> None:
    """Pre-rewrite :367, :368, :371 and :439's print.

    Every expected value comes from ``expected.yaml``. The three together say
    that policy substituted the RESTRICTED mandate out along with the edge that
    would have leaked it by absence, and that similarity ranked the second
    account out — so this fails if any of the four operators stops working.
    """
    expected = _declaration(result, "expected")
    payload = result.product.payload

    assert payload["entity_count"] == expected["entity_count"], payload
    assert sorted({entry["entity_class"] for entry in payload["entities"]}) == sorted(
        expected["entity_classes"]
    ), payload
    assert payload["relationship_types"] == sorted(
        expected["relationship_types"]
    ), payload


# --- the replay record -----------------------------------------------------


def test_the_replay_record_is_in_the_store_content_addressed(
    result: Any,
) -> None:
    """Pre-rewrite :403, :406 and :441's print.

    The address being the record's own content hash is an SDK mechanism claim,
    so it is computed here rather than read from an artifact.
    """
    address = result.served.replay_ref.content_address
    assert result.store.exists(content_address=address)
    assert address == content_hash(result.record)


def test_the_stored_record_round_trips_exactly(result: Any) -> None:
    """Pre-rewrite :410. Not merely parseable — equal."""
    restored = DecisionReplayRecord.model_validate_json(
        result.store.get(content_address=result.served.replay_ref.content_address)
    )
    assert restored == result.record


def test_the_record_carries_all_five_dimensions(result: Any) -> None:
    """Pre-rewrite :411, :412, :416, :418, :420 (whitepaper §7.10.1).

    Asserted against the stored bytes rather than the in-memory record, so this
    covers the round trip as well as the construction.
    """
    restored = DecisionReplayRecord.model_validate_json(
        result.store.get(content_address=result.served.replay_ref.content_address)
    )
    decision = _declaration(result, "decision")
    perspective = result.artifacts["perspective"]

    # 1 — context fabric snapshot, at the boundary the deployment declared.
    assert restored.context_fabric_snapshot.temporal_boundary == (
        datetime.fromisoformat(decision["temporal_boundary"])
    )
    # 2 — policy bindings. The record's binding and the product's lineage are
    #     built by two separate calls taking two different argument shapes
    #     (`PolicyBinding(key=, version=)` against a bare version set), so this
    #     fails if either is wired to the wrong pin. It does NOT independently
    #     re-derive the version — the pin has one source, by design (D-06 keeps
    #     the selection in adopter hands), and claiming otherwise would be the
    #     tautology this module exists to avoid.
    assert [binding.version for binding in restored.policy_bindings.bindings] == [
        _the_one_policy_version(result)
    ]
    # 3 — model version. SDK mechanism: this deployment is keyless.
    assert restored.model_version.model_version == "none"
    # 4 — perspective conditioning, from the perspective artifact.
    assert restored.perspective_conditioning.role == perspective.role
    # 5 — content generation path.
    assert restored.content_generation_path.plan_id == result.product.plan_id


def _the_one_policy_version(result: Any) -> str:
    """The single policy-bundle version the served product's lineage carries."""
    versions = result.product.lineage.policy_bundle_versions
    assert len(versions) == 1, versions
    return next(iter(versions))


# --- λ_c -------------------------------------------------------------------


def test_the_declared_observation_has_decayed_but_survives(result: Any) -> None:
    """Pre-rewrite :434 and :443's print.

    Strictly between the bounds in both directions: zero would mean the
    observation had fully decayed and one would mean no time had passed, and
    the declared observation is dated before the decision instant.
    """
    assert 0 < result.retained_freshness < 1, result.retained_freshness
