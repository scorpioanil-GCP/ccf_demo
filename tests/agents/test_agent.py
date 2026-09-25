"""The concrete final ``Agent`` — identity, seams, no loop, no token.

Written before the implementation per the TDD discipline (CLAUDE.md §6.1,
§7.3; D-IMPL-11/D-12). The claims pinned here:

* ``Agent`` exposes an identity block (definition content hash, versioned URI,
  archetype composition) and exactly three fabric seams — consume a typed
  Context Product, invoke a bound skill by name, emit an effect as a returned
  typed value — and **no reasoning loop of any kind**.
* The constructor validates its inputs against the definition (identity =
  content hash, composition = declared archetypes) but remains a normal public
  class: no construction token exists (D-12 — deliberate divergence from the
  I.1 ``_GATE_TOKEN`` pattern).

**Every agent here is built by the Agent Factory from the banking fixture
artifacts** (CLAUDE.md §6.4 — "Tests construct agents the same way, from
fixture artifacts"). The constructor's coherence guard is still unit-tested
on deliberately-corrupted inputs, but through
``ccf.agents.agent._validate_coherence`` — the guard extracted for exactly
this purpose — rather than by calling ``Agent(...)`` with a corrupted
identity. Before plan 15-04 this module bypassed the factory in a helper;
D-IMPL-78 widened CINV-01 over ``tests/``, which surfaced that bypass as the
one genuine finding, and it is fixed here rather than allowlisted.

All axis values live in the banking fixture YAML, none in this module
(No-Hardcoding Rule, §6.4).
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.agents.agent import (
    Agent,
    AgentIdentity,
    EmittedEffect,
    _validate_coherence,
    _validated_bound_skills,
)
from ccf.agents.archetypes import ARCHETYPES, ArchetypeComponent
from ccf.agents.definitions import (
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    AgentDefinition,
)
from ccf.agents.factory import AgentFactory
from ccf.agents.errors import (
    AgentConstructionError,
    ConsumptionRefused,
    SkillNotBound,
)
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.contract import ContextProductContract, ProductLineage
from ccf.replay.record import NO_GRANTS_SET_HASH, PerspectiveConditioning
from tests.controlplane.composition import compose_register_typed, compose_register_versioned

FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "banking"
    / "agents"
    / "covenant_analytics.yaml"
)

PROMPT_FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "banking"
    / "prompts"
    / "covenant_summary.yaml"
)


def _definition() -> AgentDefinition:
    loaded = yaml.safe_load(FIXTURE.read_text())
    definition = parse_artifact(loaded["agent_definition"], AGENT_DEFINITION)
    assert isinstance(definition, AgentDefinition)
    return definition


def _identity(definition: AgentDefinition, **overrides: Any) -> AgentIdentity:
    values: dict[str, Any] = {
        "definition_hash": content_hash(definition),
        "definition_uri": (
            f"ccf-artifact://{definition.tenant}/{AGENT_DEFINITION.class_id}/"
            f"{definition.name}@{definition.artifact_version}"
        ),
        "archetype_composition": definition.archetypes,
    }
    values.update(overrides)
    return AgentIdentity(**values)


def _components(
    definition: AgentDefinition,
) -> tuple[ArchetypeComponent, ...]:
    return tuple(ARCHETYPES[identifier] for identifier in definition.archetypes)


def _registry() -> ControlPlaneRegistry:
    """A Control Plane holding every artifact the fixture definition names."""
    plane = ControlPlaneRegistry()
    prompt_fixture = yaml.safe_load(PROMPT_FIXTURE.read_text())
    prompt = parse_artifact(prompt_fixture["prompt_artifact"], PROMPT_ARTIFACT)
    compose_register_typed(plane,
        prompt_fixture["keys"]["prompt_artifact"], prompt, PROMPT_ARTIFACT
    )
    for reference in yaml.safe_load(FIXTURE.read_text())["referenced_artifacts"].values():
        artifact_class = declared_artifact_class(reference["class_id"])
        declared = parse_artifact(
            {
                "class_id": reference["class_id"],
                "semver": reference["semver"],
                "declaration": reference["declaration"],
            },
            artifact_class,
        )
        compose_register_typed(plane, reference["key"], declared, artifact_class)
    return plane


def _agent() -> Agent:
    """One agent, built the supported way: factory, fixture artifacts, no bypass."""
    registry = _registry()
    definition = _definition()
    key = f"{definition.tenant}/{AGENT_DEFINITION.class_id}/{definition.name}"
    version = compose_register_versioned(registry, key, definition, AGENT_DEFINITION)
    assert isinstance(version, str)
    return AgentFactory(control_plane=registry).construct(
        definition_key=key, definition_version=version
    )


def _product(definition: AgentDefinition, *, expires_at: datetime) -> ContextProductContract:
    consumed = definition.context_contract.consumes[0]
    boundary = datetime(2026, 3, 31, tzinfo=UTC)
    return ContextProductContract(
        schema_name=consumed.product_class,
        schema_version=consumed.schema_version,
        plan_id="unit-test-plan",
        tenant_id=definition.tenant,
        temporal_boundary=boundary,
        expires_at=expires_at,
        ttl_anchor="from_decision",
        lineage=ProductLineage(
            operators_invoked=frozenset({"operator.unit"}),
            policy_bundle_versions=frozenset({"unit"}),
            graph_snapshot_at=boundary,
        ),
        payload={},
    )


# --- identity and construction validation ------------------------------------


def test_a_matching_identity_block_constructs() -> None:
    agent = _agent()
    definition = _definition()
    assert agent.identity.definition_hash == content_hash(definition)
    assert agent.identity.archetype_composition == definition.archetypes


def _refuses(**overrides: Any) -> None:
    """Assert the constructor's coherence guard refuses a corrupted input.

    Driven through ``_validate_coherence`` rather than through ``Agent(...)``:
    the factory derives identity from the definition, so a mismatch cannot be
    expressed factory-side, and bypassing the factory to express it is exactly
    what CINV-01c refuses (CLAUDE.md §6.4).
    """
    definition = _definition()
    values: dict[str, Any] = {
        "identity": _identity(definition),
        "components": _components(definition),
    }
    values.update(overrides)
    with pytest.raises(AgentConstructionError):
        _validate_coherence(definition, values["identity"], values["components"])


def test_the_guard_accepts_the_coherent_inputs_the_factory_produces() -> None:
    """Vacuity guard: the corruption tests below must fail for their reason."""
    definition = _definition()
    _validate_coherence(definition, _identity(definition), _components(definition))


def test_a_mismatched_definition_hash_is_refused() -> None:
    definition = _definition()
    _refuses(identity=_identity(definition, definition_hash="0" * 64))


def test_a_mismatched_archetype_composition_is_refused() -> None:
    definition = _definition()
    _refuses(
        identity=_identity(definition, archetype_composition=("context_assembly",))
    )


def test_a_drifted_definition_uri_is_refused() -> None:
    """IN-02: the URI annotation replay serializes must name the definition."""
    definition = _definition()
    drifted = (
        f"ccf-artifact://{definition.tenant}/{AGENT_DEFINITION.class_id}/"
        f"{definition.name}@99.99.99"
    )
    _refuses(identity=_identity(definition, definition_uri=drifted))


def test_a_foreign_tenant_in_the_definition_uri_is_refused() -> None:
    """IN-02: every component of the naming triple is checked, not just the version."""
    definition = _definition()
    foreign = (
        f"ccf-artifact://other-bank/{AGENT_DEFINITION.class_id}/"
        f"{definition.name}@{definition.artifact_version}"
    )
    _refuses(identity=_identity(definition, definition_uri=foreign))


def test_components_must_match_the_declared_composition() -> None:
    _refuses(components=())


def test_no_construction_token_exists() -> None:
    """D-12: `Agent` is a normal public class; lint is the no-bypass mechanism."""
    parameters = inspect.signature(Agent.__init__).parameters
    assert not any("token" in name for name in parameters)


# --- no loop ------------------------------------------------------------------


def test_the_agent_has_no_reasoning_loop_surface() -> None:
    """CLAUDE.md §7.3: the loop belongs to the harness, never to CCF."""
    agent = _agent()
    for name in ("run", "loop", "step", "plan"):
        assert not hasattr(agent, name)


# --- the three fabric seams -----------------------------------------------------


def test_consume_admits_a_contracted_unexpired_product() -> None:
    definition = _definition()
    now = datetime(2026, 4, 1, tzinfo=UTC)
    product = _product(definition, expires_at=now + timedelta(hours=1))
    assert _agent().consume(product, now=now) is product


def test_consume_refuses_a_product_outside_the_context_contract() -> None:
    definition = _definition()
    now = datetime(2026, 4, 1, tzinfo=UTC)
    product = _product(definition, expires_at=now + timedelta(hours=1))
    stranger = product.model_copy(update={"schema_name": "unrelated.product"})
    with pytest.raises(ConsumptionRefused):
        _agent().consume(stranger, now=now)


def test_consume_refuses_an_expired_product_rather_than_degrading() -> None:
    """INV-CH6-05: a TTL-expired product is contract-invalid, not stale."""
    definition = _definition()
    now = datetime(2026, 4, 1, tzinfo=UTC)
    product = _product(definition, expires_at=now - timedelta(seconds=1))
    with pytest.raises(ConsumptionRefused):
        _agent().consume(product, now=now)


def test_invoking_an_unbound_skill_raises_the_typed_error() -> None:
    with pytest.raises(SkillNotBound):
        _agent().invoke_skill("summarize-covenants")
    assert issubclass(SkillNotBound, KeyError)


def test_emitted_effects_are_returned_typed_values() -> None:
    """Single-writer (§10): emission is a value, never a graph write."""
    agent = _agent()
    effect = agent.emit_effect({"finding": "covenant-headroom-narrowing"})
    assert isinstance(effect, EmittedEffect)
    assert effect.agent_definition_hash == agent.identity.definition_hash
    assert effect.payload == {"finding": "covenant-headroom-narrowing"}


# --- dimension-4 serialization (D-06) -------------------------------------------


def test_perspective_conditioning_is_derived_from_construction_time_identity() -> None:
    agent = _agent()
    definition = _definition()
    conditioning = agent.perspective_conditioning(
        principal_id="analyst-4471", grant_set_hash=NO_GRANTS_SET_HASH
    )
    assert isinstance(conditioning, PerspectiveConditioning)
    assert conditioning.principal_id == "analyst-4471"
    assert conditioning.role == definition.perspective.role
    assert conditioning.agent_definition_hash == content_hash(definition)
    assert conditioning.agent_definition_uri == agent.identity.definition_uri
    assert conditioning.archetype_composition == definition.archetypes
    assert conditioning.grant_set_hash == NO_GRANTS_SET_HASH
    assert conditioning.delegation_chain == ("analyst-4471",)


def test_perspective_conditioning_requires_an_explicit_grant_set_hash() -> None:
    """WR-01: the grant-set claim is stated, never defaulted — a defaulted
    zero-grants claim on a skilled agent would be a false positive record."""
    with pytest.raises(TypeError):
        _agent().perspective_conditioning(  # type: ignore[call-arg]
            principal_id="analyst-4471"
        )


def test_a_raw_mapping_is_refused_at_the_bound_skills_seam() -> None:
    """WR-03: only the grant ledger's BoundSkillView is admissible —
    capabilities reach an agent through governed grants exclusively.

    Driven through the seam's own validator for the same reason the coherence
    corruptions are: the factory passes the grant ledger's view, so a raw
    mapping can only reach the constructor by bypassing it (CLAUDE.md §6.4).
    """
    with pytest.raises(AgentConstructionError):
        _validated_bound_skills({"summarize-covenants": object()})
