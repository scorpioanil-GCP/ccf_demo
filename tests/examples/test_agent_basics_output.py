"""Example 01's assertions, under a runner that can actually fail (D-09).

``examples/01-agent-basics/run.py`` used to carry its own guarantee: 38
``assert`` statements and 9 ``print`` summaries, checked by ``make example-01``
exiting zero. D-09 moves that guarantee here, because ``make examples`` proves a
spine *runs* and ``pytest`` proves it is *correct* — and a printed summary
nobody reads was never a guarantee at all.

Nothing is lost in the move. Each assertion below names the pre-rewrite line it
came from, so the "no loss of assertion coverage" claim is auditable:

=============================================  ==========================
pre-rewrite ``run.py`` line                     relocated to
=============================================  ==========================
:246 ``isinstance(prompt, PromptArtifact)``     the spine itself (``load_artifact``
                                                validates against the class, and a
                                                bad document raises there) **and**
                                                :func:`test_axis_6_binds_the_resolved_prompt_artifact`
:267 ``isinstance(definition, AgentDefinition)`` the spine (``AGENT_DEFINITION.validate``)
:272 ``isinstance(definition_version, str)``    the spine (a refusal now raises)
:407 ``isinstance(gated, ServableProduct)``     the spine (a refusal now raises) **and**
                                                :func:`test_the_product_passed_all_three_gates`
:410 ``entity_count``                           :func:`test_the_served_payload_matches_the_declared_expectation`
:411 entity classes                             :func:`test_the_served_payload_matches_the_declared_expectation`
:417 payload role == definition role            :func:`test_axis_3_conditions_the_served_payload_and_dimension_4`
:424 excluded entity classes                    :func:`test_axis_4_keeps_the_excluded_class_out_of_the_served_view`
:435 ``isinstance(agent, Agent)``               the spine (the factory returns one or raises)
:439 ``definition_hash``                        :func:`test_agent_identity_derives_from_the_definition_artifact`
:440 ``definition_uri``                         :func:`test_agent_identity_derives_from_the_definition_artifact`
:453 ``archetype_composition``                  :func:`test_axis_1_binds_the_declared_archetypes_in_order`
:454 component archetype ids                    :func:`test_axis_1_binds_the_declared_archetypes_in_order`
:459 ``consumed is gated.product``              :func:`test_axis_2_admits_the_served_product_under_the_declared_contract`
:466 schema name == contract's class            :func:`test_axis_2_admits_the_served_product_under_the_declared_contract`
:467 schema version                             :func:`test_axis_2_admits_the_served_product_under_the_declared_contract`
:473 ``conditioning.role``                      :func:`test_axis_3_conditions_the_served_payload_and_dimension_4`
:479 referenced keys carry versions             :func:`test_axes_4_and_5_resolve_through_the_control_plane`
:480 policy-regime ref semver                   :func:`test_axes_4_and_5_resolve_through_the_control_plane`
:483 debt-profile ref semver                    :func:`test_axes_4_and_5_resolve_through_the_control_plane`
:493 ``isinstance(resolved, PromptArtifact)``   :func:`test_axis_6_binds_the_resolved_prompt_artifact`
:494 declared parameters == binding             :func:`test_axis_6_binds_the_resolved_prompt_artifact`
:514 ``isinstance(profile, DebtProfile)``       the spine (``parse_artifact`` validates)
:518 ``isinstance(table, HalfLifeTable)``       the spine (the manifest's class does)
:540 ``assessment.signal``                      :func:`test_axis_5_debt_lands_in_the_reviewed_car_state`
:543 debt > forced-LLM threshold                :func:`test_axis_5_debt_lands_in_the_reviewed_car_state`
:544 debt <= fail-closed threshold              :func:`test_axis_5_debt_lands_in_the_reviewed_car_state`
:551 ``isinstance(analyst, LLMClientProtocol)`` :func:`test_the_scripted_analyst_satisfies_the_llm_seam`
:553 ``isinstance(effect, EmittedEffect)``      :func:`test_the_emitted_effect_carries_the_agent_identity`
:554 ``effect.agent_definition_hash``           :func:`test_the_emitted_effect_carries_the_agent_identity`
:555 ``effect.payload``                         :func:`test_the_emitted_effect_carries_the_agent_identity`
:583 ``restored == record``                     :func:`test_the_stored_record_round_trips_exactly`
:586 dimension-4 definition hash                :func:`test_dimension_four_carries_the_agent_in_force`
:589 dimension-4 definition URI                 :func:`test_dimension_four_carries_the_agent_in_force`
:592 URI ends with the artifact version         :func:`test_dimension_four_carries_the_agent_in_force`
:595 dimension-4 archetype composition          :func:`test_dimension_four_carries_the_agent_in_force`
:596 ``grant_set_hash``                          :func:`test_dimension_four_carries_the_agent_in_force`
:597 ``delegation_chain``                        :func:`test_dimension_four_carries_the_agent_in_force`
:602 print — OK banner                          (nothing: a banner is not a claim)
:603 print — tenant                             :func:`test_the_run_serves_the_tenant_and_class_the_artifacts_name`
:604 print — agent name                         :func:`test_agent_identity_derives_from_the_definition_artifact`
:605 print — agent version                      :func:`test_dimension_four_carries_the_agent_in_force`
:606 print — archetypes                         :func:`test_axis_1_binds_the_declared_archetypes_in_order`
:607 print — consumed product                   :func:`test_axis_2_admits_the_served_product_under_the_declared_contract`
:608 print — context debt D_c                   :func:`test_axis_5_debt_lands_in_the_reviewed_car_state`
:609 print — debt signal                        :func:`test_axis_5_debt_lands_in_the_reviewed_car_state`
:610 print — dim-4 definition hash              :func:`test_dimension_four_carries_the_agent_in_force`
=============================================  ==========================

Two assertions here are **new**, and are marked as such rather than smuggled in
as relocations: :func:`test_lineage_strict_equality_holds` and
:func:`test_every_declared_operator_actually_ran`. The pre-rewrite file had no
Gate 2 check because its plan was constructed from ``operators.keys()`` — the
tautology 15-13 fixed at its origin — so there was nothing to relocate.

Two kinds of assertion, and the difference is worth stating
-----------------------------------------------------------

Every domain expectation is read from an artifact, never inlined. That produces
two categories, and conflating them is how a suite ends up claiming more than it
checks (the classification 15-13 established):

* **Independent expectations.** ``expected.yaml`` declares what the *served
  product* should contain, and ``debt-evaluation.yaml`` declares which CAR state
  the assessment must land in. Nothing in the pipeline derives those from those
  files — they follow from the events, the resolution spec and the four
  operators — so changing either side alone makes the assertion fail. These are
  the correctness guarantees.
* **Propagation checks.** The perspective role, the product's schema name, the
  archetype list, the axis-2 contract and the required operator set are each
  read from an artifact by ``run.py`` *and* by this module, so the artifact is a
  single source and editing it moves both ends together. These assert that a
  declared value survives end to end into the served product, the constructed
  agent and the replay record — which fails on a **wiring** fault, not on an
  artifact edit.

:func:`test_every_declared_operator_actually_ran` is squarely in the second
category and its narrowness was worth naming: ``operators_invoked`` is
``frozenset(outputs)``, planned from ``plan.required_operators()``, which was
itself ``required_operator_keys``. Editing ``product-class.yaml`` alone moved
both ends. What it *did* catch is the ``operators.keys()`` shortcut coming back
— which is the regression that matters here, because that shortcut is what this
file used to do.

That caution was right, and design E2 (D-IMPL-86) closes the half of it that
could be closed. The two ends now trace to **two documents**: the executed set
to ``projection-requirements.yaml`` by way of the plan, the declared set to
``product-class.yaml`` by way of the product's lineage claim. Editing either
one alone no longer moves both — it makes them disagree, and
``refuse_operator_set_divergence`` refuses before the engine runs. So the
assertion is a correctness guarantee about the driver's wiring as well as a
propagation check.

The half that does not close, and is not claimed to: nothing here proves the
two documents were *authored* independently. A deployment that reads one into
the other collapses the binder and this assertion with it — the residual
D-IMPL-86 names and accepts, because no check can tell an authored literal from
a transcribed one.

The example is not a package, so it is loaded by file path with
``importlib.util``.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from typing import Any

import pytest

from ccf.agents.definitions import PromptArtifact
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import DeclaredArtifact, ProductClassDeclaration
from ccf.llm import LLMClientProtocol
from ccf.replay.record import NO_GRANTS_SET_HASH, DecisionReplayRecord

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "01-agent-basics" / "run.py"


def _load_example() -> Any:
    """Load the example module by file path (the example dir is no package).

    The module is registered in ``sys.modules`` *before* execution: the example
    uses ``from __future__ import annotations``, so ``@dataclass`` resolves its
    field annotations by looking its own module up there, and a module absent
    from the table fails with an opaque ``AttributeError`` at class-definition
    time rather than anywhere near the cause.
    """
    name = "agent_basics_under_test"
    spec = importlib.util.spec_from_file_location(name, EXAMPLE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def result(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """One run of the spine, shared across the module.

    Module-scoped deliberately: the spine is the unit under test, and running it
    once per assertion would say nothing extra while paying for a full boot and
    a full agent construction each time.
    """
    root = tmp_path_factory.mktemp("agent-basics")
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


def _restored(result: Any) -> DecisionReplayRecord:
    """The replay record as it came back out of the store."""
    return DecisionReplayRecord.model_validate_json(
        result.store.get(content_address=result.served.replay_ref.content_address)
    )


# --- the fabric underneath the agent ----------------------------------------


def test_the_product_passed_all_three_gates(result: Any) -> None:
    """Pre-rewrite :407. ``ServableProduct`` is not constructible outside
    ``run_gates``, so a served product IS the evidence the gates ran."""
    assert result.product is not None
    assert result.served.replay_ref is not None


def test_lineage_strict_equality_holds(result: Any) -> None:
    """**New.** What the product claims ran is exactly what the engine resolved
    (INV-CH7-47). The pre-rewrite file had no such check.

    Since design E2 the claim comes from ``product-class.yaml`` and the resolved
    set traces to ``projection-requirements.yaml``, so this compares two
    documents rather than one value against itself — see the module docstring
    for what that does and does not buy.
    """
    assert result.product.lineage.operators_invoked == result.operators_invoked


def test_every_declared_operator_actually_ran(result: Any) -> None:
    """**New**, and narrower than it looks — see the module docstring.

    The set the product class DECLARED it requires is the set the engine
    RESOLVED. This example uses all four canonical categories; the three-operator
    case is example 02's.

    Narrower, but no longer tautological: under design E2 the two sets are
    authored in two documents and the binder is what holds them together. The
    residual is authorship, not wiring.
    """
    declared = result.artifacts["product-class"]
    assert isinstance(declared, ProductClassDeclaration)
    assert set(declared.required_operator_keys) == set(result.operators_invoked)


def test_the_run_serves_the_tenant_and_class_the_artifacts_name(
    result: Any,
) -> None:
    """Pre-rewrite :603's print, as a check against the artifacts."""
    declared = result.artifacts["product-class"]
    assert isinstance(declared, ProductClassDeclaration)
    assert result.product.schema_name == declared.schema_name
    assert result.product.schema_version == declared.schema_version
    assert result.product.tenant_id == result.tenant_id


def test_the_served_payload_matches_the_declared_expectation(result: Any) -> None:
    """Pre-rewrite :410 and :411.

    An independent expectation: ``expected.yaml`` says what the served view
    should hold, and nothing derives it from that file. It fails if policy stops
    substituting the restricted site out, or if similarity stops ranking the
    second work order out.
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


# --- archetype vs agent (§6.1) ----------------------------------------------


def test_agent_identity_derives_from_the_definition_artifact(result: Any) -> None:
    """Pre-rewrite :439, :440 and :604's print.

    Identity is a function of the artifact and of nothing in code — the whole
    content of the archetype/agent separation.
    """
    definition = result.definition
    assert result.agent.identity.definition_hash == content_hash(definition)
    assert result.agent.identity.definition_uri.endswith(
        f"/{definition.name}@{definition.artifact_version}"
    )
    assert definition.tenant in result.agent.identity.definition_uri


# --- the six specialization axes (§6.2 channel 1) ---------------------------


def test_axis_1_binds_the_declared_archetypes_in_order(result: Any) -> None:
    """Pre-rewrite :453, :454 and :606's print. Order is D-IMPL-19."""
    declared = tuple(result.definition.archetypes)
    assert result.agent.identity.archetype_composition == declared
    assert tuple(c.archetype_id for c in result.agent.components) == declared


def test_axis_2_admits_the_served_product_under_the_declared_contract(
    result: Any,
) -> None:
    """Pre-rewrite :459, :466, :467 and :607's print.

    The contract admission is the point: the class the definition declares it
    consumes is the class the fabric served, so ``consume`` returns the product
    itself rather than a substitute.
    """
    contract = result.definition.context_contract.consumes[0]
    assert result.consumed is result.product
    assert result.product.schema_name == contract.product_class
    assert result.product.schema_version == contract.schema_version


def test_axis_3_conditions_the_served_payload_and_dimension_4(result: Any) -> None:
    """Pre-rewrite :417 and :473.

    The definition's Π role reaches two independent places — the projected
    payload (through the perspective artifact the engine ran under) and the
    agent's dimension-4 conditioning. Rebinding one and not the other fails
    here.
    """
    role = result.definition.perspective.role
    assert result.product.payload["role"] == role
    assert result.conditioning.role == role
    assert _declaration(result, "expected")["role"] == role


def test_axis_4_keeps_the_excluded_class_out_of_the_served_view(
    result: Any,
) -> None:
    """Pre-rewrite :424. Exclusion asserted by name, not by count."""
    expected = _declaration(result, "expected")
    served = {entry["entity_class"] for entry in result.product.payload["entities"]}
    assert not (served & set(expected["excluded_entity_classes"])), served


def test_axes_4_and_5_resolve_through_the_control_plane(result: Any) -> None:
    """Pre-rewrite :479, :480 and :483.

    Both refs resolving at their pinned versions is already proved by the agent
    existing — ``AgentFactory.construct`` refuses an unresolvable ref before it
    returns. What this adds is that the keys the manifest registered are the
    keys the refs name, and at the semver the referenced documents declare.
    """
    registration = _declaration(result, "agent-registration")
    definition = result.definition
    for key in (
        registration["policy_regime_key"],
        registration["halflife_debt_profile_key"],
    ):
        assert result.registry.versions(key), key

    regime = result.artifacts[registration["policy_regime_key"]]
    profile = result.artifacts[registration["halflife_debt_profile_key"]]
    assert definition.policy_regime.ref.endswith(
        f"{registration['policy_regime_key']}@{regime.semver}"
    )
    assert definition.halflife_debt_profile.ref.endswith(
        f"{registration['halflife_debt_profile_key']}@{profile.semver}"
    )


def test_axis_5_debt_lands_in_the_reviewed_car_state(result: Any) -> None:
    """Pre-rewrite :540, :543, :544 and :608/:609's prints.

    An independent expectation: ``debt-evaluation.yaml`` declares the reviewed
    CAR routing state, and the assessed D_c is computed from the observations,
    the λ_c table and the agent's own axis-5 thresholds. Ageing an observation
    or moving a threshold breaks it.
    """
    evaluation = _declaration(result, "debt-evaluation")
    assert result.assessment.signal.value == evaluation["expected_signal"]
    assert result.assessment.debt > result.profile.forced_llm_threshold
    assert result.assessment.debt <= result.profile.fail_closed_threshold


def test_axis_6_binds_the_resolved_prompt_artifact(result: Any) -> None:
    """Pre-rewrite :246, :493 and :494.

    The binding names a prompt by versioned URI and the agent carries the
    resolved artifact; the parameter sets must agree exactly (D-13 parse-only
    validation).
    """
    binding = result.definition.instruction_bindings[0]
    resolved = result.agent.instruction_artifact(binding.prompt)
    assert isinstance(resolved, PromptArtifact)
    assert frozenset(resolved.declared_parameters) == frozenset(binding.parameters)


# --- the analytic step ------------------------------------------------------


def test_the_scripted_analyst_satisfies_the_llm_seam(result: Any) -> None:
    """Pre-rewrite :551. An SDK mechanism claim: the stub is structurally a
    conforming client, which is what makes the seam a seam rather than a
    special case."""
    assert isinstance(result.analyst, LLMClientProtocol)


def test_the_emitted_effect_carries_the_agent_identity(result: Any) -> None:
    """Pre-rewrite :553, :554 and :555.

    A governed effect is attributable: it carries the definition hash of the
    agent that emitted it, and its payload is the artifact's own record.
    """
    outputs = _declaration(result, "analysis-output")["outputs"]
    assert result.effect.agent_definition_hash == result.agent.identity.definition_hash
    assert result.effect.payload == outputs[0]


# --- replay -----------------------------------------------------------------


def test_the_stored_record_round_trips_exactly(result: Any) -> None:
    """Pre-rewrite :583. Not merely parseable — equal."""
    assert _restored(result) == result.record


def test_dimension_four_carries_the_agent_in_force(result: Any) -> None:
    """Pre-rewrite :586, :589, :592, :595, :596, :597 and :605/:610's prints.

    Asserted against the stored bytes rather than the in-memory record, so this
    covers the round trip as well as the construction. This is the D-06 claim
    the example exists to make: *which agent, which version, which composition,
    which grants* is answerable from the record alone.
    """
    definition = result.definition
    dimension_four = _restored(result).perspective_conditioning

    assert dimension_four.agent_definition_hash == content_hash(definition)
    assert dimension_four.agent_definition_uri == result.agent.identity.definition_uri
    assert dimension_four.agent_definition_uri.endswith(
        "@" + definition.artifact_version
    )
    assert dimension_four.archetype_composition == tuple(definition.archetypes)
    # SDK mechanism claim: this agent was never skilled, and a zero-grant claim
    # is recorded positively rather than by omission (WR-01).
    assert dimension_four.grant_set_hash == NO_GRANTS_SET_HASH
    perspective = result.artifacts["perspective"]
    assert dimension_four.delegation_chain == (perspective.principal_id,)
