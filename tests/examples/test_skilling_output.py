"""Example 02's assertions, under a runner that can actually fail (D-09).

``archive/examples/02-skilling/run.py`` used to carry its own guarantee: 60 ``assert``
statements and 8 ``print`` summaries, checked by ``make example-02`` exiting
zero. D-09 moves that guarantee here, because ``make examples`` proves a spine
*runs* and ``pytest`` proves it is *correct*.

**The audit-by-construction claims are the ones that had to survive this move
intact.** CLAUDE.md §6.2 commits that every skill grant and revocation is
audited and that the skill-set in force at decision time lands in replay
dimension 4. Those checks are :func:`test_every_grant_transition_was_audited`
and :func:`test_dimension_four_carries_the_skill_set_in_force`; they are the
reason this module exists rather than being optional.

Nothing is lost in the move. Each assertion below names the pre-rewrite line it
came from, so the "no loss of assertion coverage" claim is auditable:

=============================================  ==========================
pre-rewrite ``run.py`` line                     relocated to
=============================================  ==========================
:250 ``isinstance(definition, AgentDefinition)`` the spine (``AGENT_DEFINITION.validate``)
:255 ``isinstance(definition_version, str)``    the spine (a refusal now raises)
:362 ``isinstance(gated, ServableProduct)``     the spine (a refusal now raises) **and**
                                                :func:`test_the_product_passed_all_three_gates`
:364 ``entity_count``                           :func:`test_the_served_payload_matches_the_declared_expectation`
:374 ``isinstance(entry, SkillCatalogEntry)``   the spine (``SKILL_CATALOG_ENTRY.validate``)
:376 catalog registration returned a version    the spine (a refusal now raises)
:400 ``isinstance(agent, Agent)``               the spine (the factory returns one or raises)
:401 no skills bound before the grant           :func:`test_nothing_is_bound_before_the_grant`
:402 zero-grant hash before the grant           :func:`test_nothing_is_bound_before_the_grant`
:417 ``outcome == content_hash(permitted)``     :func:`test_the_permitted_grant_took_effect`
:418 ``state == "effective"``                   :func:`test_the_permitted_grant_took_effect`
:424 first two audited actions                  :func:`test_every_grant_transition_was_audited`
:426 in-force hash moved off zero               :func:`test_the_permitted_grant_took_effect`
:427 in-force hash == hash of the grant set     :func:`test_the_permitted_grant_took_effect`
:430 bound names after the grant                :func:`test_the_permitted_grant_took_effect`
:436 ``consumed is gated.product``              :func:`test_the_agent_consumed_the_product_its_contract_names`
:440 ``isinstance(invocation, SkillInvocation)`` the spine (``invoke_skill``'s return type)
:441 ``invocation.output``                      :func:`test_the_exercised_skill_returned_the_declared_output`
:478 ``restored == record``                     :func:`test_the_stored_record_round_trips_exactly`
:479 dimension-4 grant-set hash                 :func:`test_dimension_four_carries_the_skill_set_in_force`
:480 hash is not the zero-grant value           :func:`test_dimension_four_carries_the_skill_set_in_force`
:484 dimension-4 definition hash                :func:`test_dimension_four_carries_the_skill_set_in_force`
:498 ``isinstance(refusal, GrantRefusal)``      the spine (an admission now raises) **and**
                                                :func:`test_the_impermissible_grant_was_refused_by_tier_1`
:499 ``RequirementsExceedRegime``               :func:`test_the_impermissible_grant_was_refused_by_tier_1`
:500 ``refusal.excess_scopes``                  :func:`test_the_impermissible_grant_was_refused_by_tier_1`
:503 ``state == "refused"``                     :func:`test_the_impermissible_grant_was_refused_by_tier_1`
:509 ``refused_event.action``                   :func:`test_every_grant_transition_was_audited`
:510 ``refused_event.resolved is False``        :func:`test_every_grant_transition_was_audited`
:513 bound names unchanged by the refusal       :func:`test_the_refusal_bound_nothing`
:514 in-force hash unchanged by the refusal     :func:`test_the_refusal_bound_nothing`
:516 refused skill raises ``SkillNotBound``     :func:`test_the_refusal_bound_nothing`
:526 ``state == "revoked"``                     :func:`test_revocation_takes_effect_on_the_running_agent`
:532 the full audited action sequence           :func:`test_every_grant_transition_was_audited`
:539 in-force hash back to zero-grant           :func:`test_revocation_takes_effect_on_the_running_agent`
:542 bound names empty after revocation         :func:`test_revocation_takes_effect_on_the_running_agent`
:544 revoked skill raises ``SkillNotBound``     :func:`test_revocation_takes_effect_on_the_running_agent`
:552 ``agent.yaml`` bytes identical             :func:`test_the_agent_was_never_re_declared`
:555 definition hash unmoved                    :func:`test_the_agent_was_never_re_declared`
:556 one registered definition version          :func:`test_the_agent_was_never_re_declared`
:558 print — OK banner                          (nothing: a banner is not a claim)
:559 print — tenant                             :func:`test_the_run_serves_the_tenant_and_class_the_artifacts_name`
:560 print — agent name                         :func:`test_the_agent_was_never_re_declared`
:561 print — granted+exercised                  :func:`test_the_exercised_skill_returned_the_declared_output`
:562 print — refused skill                      :func:`test_the_impermissible_grant_was_refused_by_tier_1`
:563 print — excess scopes                      :func:`test_the_impermissible_grant_was_refused_by_tier_1`
:564 print — in-force hash                      :func:`test_dimension_four_carries_the_skill_set_in_force`
:565 print — definition byte-identical          :func:`test_the_agent_was_never_re_declared`
=============================================  ==========================

Two assertions are **new**, and are marked as such rather than smuggled in as
relocations: :func:`test_the_registry_holds_exactly_three_operators` and
:func:`test_lineage_strict_equality_holds`. The pre-rewrite file registered its
three operators by hand and built its plan from ``operators.keys()``, so there
was no declared side to compare against and nothing to relocate.

Two kinds of assertion, and the difference is worth stating
-----------------------------------------------------------

Every domain expectation is read from an artifact. That produces two categories
(the classification 15-13 established), and this module says which is which:

* **Independent expectations.** ``expected.yaml`` declares the served entity
  count and the operator count; ``skilling-scenario.yaml`` declares the excess
  scopes the refusal must name, the audited action sequence, and the dispatch
  output. Nothing in the pipeline derives those from those files — they follow
  from the events, the regime, the catalog and the ledger — so changing either
  side alone makes the assertion fail. These are the correctness guarantees.
* **Propagation checks.** The product's schema name, the granted skill's name
  and the required operator set are read from an artifact by ``run.py`` *and*
  by this module, so editing the artifact moves both ends together. They fail
  on a **wiring** fault, not on an artifact edit.

:func:`test_the_registry_holds_exactly_three_operators` is deliberately in the
first category: the count comes from ``expected.yaml``, which is not what
builds the registry — the manifest's artifact set is. A fourth operator
appearing by builder default is exactly what it catches.

The example is not a package, so it is loaded by file path with
``importlib.util``.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from typing import Any

import pytest

from ccf.agents.errors import SkillNotBound
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import DeclaredArtifact, ProductClassDeclaration
from ccf.replay.record import NO_GRANTS_SET_HASH, DecisionReplayRecord
from ccf.skills.grants import RequirementsExceedRegime, grant_set_hash

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "archive" / "examples" / "02-skilling" / "run.py"


def _load_example() -> Any:
    """Load the example module by file path (the example dir is no package).

    The module is registered in ``sys.modules`` *before* execution: the example
    uses ``from __future__ import annotations``, so ``@dataclass`` resolves its
    field annotations by looking its own module up there, and a module absent
    from the table fails with an opaque ``AttributeError`` at class-definition
    time rather than anywhere near the cause.
    """
    name = "skilling_under_test"
    spec = importlib.util.spec_from_file_location(name, EXAMPLE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def result(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """One run of the spine — the whole grant/exercise/refuse/revoke cycle."""
    root = tmp_path_factory.mktemp("skilling")
    return _load_example().run(root=root)


def _declaration(result: Any, key: str) -> Any:
    """The deployment's own declaration under one manifest key."""
    artifact = result.artifacts[key]
    assert isinstance(artifact, DeclaredArtifact), key
    return artifact.declaration


def _grant_actions(result: Any) -> list[str]:
    """Every grant-lifecycle action on the one shared audit log, in order."""
    return [
        event.action
        for event in result.audit.events()
        if event.action.startswith("grant_")
    ]


# --- the fabric: three operators, not four ----------------------------------


def test_the_product_passed_all_three_gates(result: Any) -> None:
    """Pre-rewrite :362. ``ServableProduct`` is not constructible outside
    ``run_gates``, so a served product IS the evidence the gates ran."""
    assert result.product is not None
    assert result.served.replay_ref is not None


def test_the_registry_holds_exactly_three_operators(result: Any) -> None:
    """**New**, and the reason this example's fabric is shaped as it is.

    Which operators exist is per-deployment policy, expressed only by which
    artifacts the manifest names. The expected count is declared in
    ``expected.yaml`` — a file that plays no part in building the registry — so
    a fourth operator appearing by builder default fails here.
    """
    expected = _declaration(result, "expected")
    assert len(result.operator_keys) == expected["operator_count"]
    assert len(result.operators_invoked) == expected["operator_count"]


def test_lineage_strict_equality_holds(result: Any) -> None:
    """**New.** What the product claims ran is exactly what the engine resolved
    (INV-CH7-47). The pre-rewrite file had no such check.

    Since design E2 (D-IMPL-86) the two sides trace to two documents: the claim
    to ``product-class.yaml`` through the product's lineage, the resolved set to
    ``projection-requirements.yaml`` through the plan the engine ran.

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

    Nor does this prove the two documents were authored rather than one copied
    from the other. That collapses the binder upstream and this check with it —
    the residual D-IMPL-86 names and accepts.
    """
    assert result.product.lineage.operators_invoked == result.operators_invoked


def test_every_declared_operator_actually_ran(result: Any) -> None:
    """**New**, and no longer only a propagation check.

    It was one: the declared side of Gate 2 and the engine's resolution moved
    together when ``product-class.yaml`` was edited, because both traced to that
    one document, so what it caught was the ``operators.keys()`` shortcut coming
    back. Design E2 (D-IMPL-86) splits the two — the declared set is authored in
    ``product-class.yaml``, the executed set in
    ``projection-requirements.yaml`` — so editing either alone now makes them
    disagree rather than move together, and
    ``refuse_operator_set_divergence`` refuses before the engine runs. Both
    documents name three keys here; this asserts they name the same three.

    The residual is authorship, not wiring: a deployment that reads one document
    into the other hands the binder one value twice, and this comparison goes
    back to being a value against itself with nothing in the output to show it.
    """
    declared = result.artifacts["product-class"]
    assert isinstance(declared, ProductClassDeclaration)
    assert set(declared.required_operator_keys) == set(result.operators_invoked)


def test_the_run_serves_the_tenant_and_class_the_artifacts_name(
    result: Any,
) -> None:
    """Pre-rewrite :559's print, as a check against the artifacts."""
    declared = result.artifacts["product-class"]
    assert isinstance(declared, ProductClassDeclaration)
    assert result.product.schema_name == declared.schema_name
    assert result.product.tenant_id == result.tenant_id


def test_the_served_payload_matches_the_declared_expectation(result: Any) -> None:
    """Pre-rewrite :364.

    An independent expectation: the restricted unblinded cohort and its
    ``enrolls_at`` edge are gone from the served view.
    """
    expected = _declaration(result, "expected")
    payload = result.product.payload
    assert payload["entity_count"] == expected["entity_count"], payload
    assert sorted({entry["entity_class"] for entry in payload["entities"]}) == sorted(
        expected["entity_classes"]
    ), payload


# --- channel 2: grant, exercise, refuse, revoke ------------------------------


def test_nothing_is_bound_before_the_grant(result: Any) -> None:
    """Pre-rewrite :401 and :402.

    Registration is discovery; a grant is capability. Three catalog entries are
    registered and none of them is bound until one is granted.
    """
    assert result.bound_before_grant == ()
    assert result.grant_set_hash_before_grant == NO_GRANTS_SET_HASH


def test_the_permitted_grant_took_effect(result: Any) -> None:
    """Pre-rewrite :417, :418, :426, :427 and :430.

    The ledger is live, so these states are read in the spine at the step that
    produced them: by the end of the run the grant has been revoked.

    The in-force identity is the hash of the *set* of effective grant hashes —
    recomputed here from the grant the ledger accepted, so this fails if the
    ledger's set and the grant it recorded ever disagree.
    """
    address = content_hash(result.permitted_grant)
    assert result.permitted_grant_outcome == address
    assert result.permitted_state_after_grant == "effective"
    assert result.grant_set_hash_in_force != NO_GRANTS_SET_HASH
    assert result.grant_set_hash_in_force == grant_set_hash(frozenset({address}))
    assert result.bound_after_grant == (result.permitted_grant.skill_name,)


def test_the_registered_but_ungranted_skill_stays_invisible(result: Any) -> None:
    """The catalog is wider than any one agent's bound set (§7.3 seam 2).

    Asserted by name from ``skilling-scenario.yaml`` rather than by count, so
    it still means something if the catalog grows.
    """
    scenario = _declaration(result, "skilling-scenario")
    assert scenario["never_granted_skill_name"] not in result.bound_after_grant


def test_the_agent_consumed_the_product_its_contract_names(result: Any) -> None:
    """Pre-rewrite :436. Axis 2 admission, not substitution."""
    assert result.consumed is result.product
    contract = result.definition.context_contract.consumes[0]
    assert result.product.schema_name == contract.product_class


def test_the_exercised_skill_returned_the_declared_output(result: Any) -> None:
    """Pre-rewrite :441 and :561's print.

    An independent expectation: ``skilling-scenario.yaml`` declares the full
    output, which is the callable's canned record merged with the typed
    dispatch arguments — so a dispatch that dropped its arguments fails here.
    """
    scenario = _declaration(result, "skilling-scenario")
    assert dict(result.invocation.output) == scenario["dispatch"]["expected_output"]


def test_the_impermissible_grant_was_refused_by_tier_1(result: Any) -> None:
    """Pre-rewrite :498, :499, :500, :503 and :562/:563's prints.

    Tier-1 governance is structural: the refusal is a typed returned value that
    NAMES the excess, and ``skilling-scenario.yaml`` declares which scopes that
    must be — an independent expectation, since the excess is computed from the
    catalog entry's requirements against the regime's envelope.
    """
    scenario = _declaration(result, "skilling-scenario")
    assert isinstance(result.refusal, RequirementsExceedRegime), result.refusal
    assert result.refusal.excess_scopes == frozenset(
        scenario["expected_excess"]["scopes"]
    )
    impermissible_name = scenario["grants"]["impermissible"]["skill_name"]
    assert impermissible_name not in result.bound_after_refusal


def test_the_refusal_bound_nothing(result: Any) -> None:
    """Pre-rewrite :513, :514 and :516.

    Nothing bound: the skill does not exist from the agent's surface, and the
    in-force set identity did not move. The ledger is live, so the
    ``SkillNotBound`` refusal is still observable after the run.
    """
    scenario = _declaration(result, "skilling-scenario")
    assert result.bound_after_refusal == result.bound_after_grant
    assert result.grant_set_hash_after_refusal == result.grant_set_hash_in_force
    with pytest.raises(SkillNotBound):
        result.agent.invoke_skill(scenario["grants"]["impermissible"]["skill_name"])


def test_revocation_takes_effect_on_the_running_agent(result: Any) -> None:
    """Pre-rewrite :526, :539, :542 and :544.

    The agent was constructed once and holds the ledger's live bound view, so
    revocation takes effect at invoke time — no re-declaration, no new agent.
    """
    assert result.permitted_state_after_revocation == "revoked"
    assert result.bound_after_revocation == ()
    assert result.grant_set_hash_after_revocation == NO_GRANTS_SET_HASH
    with pytest.raises(SkillNotBound):
        result.agent.invoke_skill(result.permitted_grant.skill_name)


def test_every_grant_transition_was_audited(result: Any) -> None:
    """Pre-rewrite :424, :509, :510 and :532 — the §6.2 audit commitment.

    An independent expectation: ``skilling-scenario.yaml`` declares the exact
    action sequence the cycle must produce, on the ONE shared audit log. A
    transition that stopped being recorded, or one recorded twice, fails here.
    """
    scenario = _declaration(result, "skilling-scenario")
    assert _grant_actions(result) == scenario["expected_grant_actions"]

    refused = [
        event
        for event in result.audit.events()
        if event.action == "grant_refused"
    ]
    assert len(refused) == 1
    assert refused[0].resolved is False


# --- replay: the skill-set in force ------------------------------------------


def test_the_stored_record_round_trips_exactly(result: Any) -> None:
    """Pre-rewrite :478. Not merely parseable — equal."""
    restored = DecisionReplayRecord.model_validate_json(
        result.store.get(content_address=result.served.replay_ref.content_address)
    )
    assert restored == result.record


def test_dimension_four_carries_the_skill_set_in_force(result: Any) -> None:
    """Pre-rewrite :479, :480, :484 and :564's print — the D-07 commitment.

    The record was built at the EXERCISE step, so it carries the grant-set hash
    that was in force then, not the empty one in force now. That is the whole
    claim: a decision replays against the skills the agent actually had.
    Asserted against the stored bytes, so the round trip is covered too.
    """
    restored = DecisionReplayRecord.model_validate_json(
        result.store.get(content_address=result.served.replay_ref.content_address)
    )
    dimension_four = restored.perspective_conditioning

    assert dimension_four.grant_set_hash == result.grant_set_hash_in_force
    assert dimension_four.grant_set_hash != NO_GRANTS_SET_HASH
    assert dimension_four.agent_definition_hash == result.definition_hash
    # And the agent has since been un-skilled — so a record that re-observed
    # the ledger at recording time would now disagree with this one.
    assert result.grant_set_hash_after_revocation == NO_GRANTS_SET_HASH


# --- the definition never changed --------------------------------------------


def test_the_agent_was_never_re_declared(result: Any) -> None:
    """Pre-rewrite :552, :555, :556 and :560/:565's prints.

    The §6.2 separation, stated three ways: the artifact's bytes, the identity
    derived from them, and the number of versions the Control Plane holds. A
    capability change that had required re-declaring the agent would move at
    least one of the three.
    """
    registration = _declaration(result, "agent-registration")
    assert result.definition_bytes_after == result.definition_bytes_before
    assert content_hash(result.definition) == result.definition_hash
    assert result.registry.versions(registration["agent_definition_key"]) == (
        result.definition_version,
    )
