"""The two-tier grant machinery (CLAUDE.md §6.2 channel 2; D-IMPL-29; AGNT-03).

What this suite holds `src/ccf/skills/grants.py` to:

* **Tier 1 is non-waivable and structural** — a grant whose declared
  requirements are not a subset of the agent's policy-regime allowances and
  context contract is refused with a *returned* typed refusal naming the
  excess identifiers; an agent whose policy regime is missing, unresolvable,
  or ungoverned cannot be granted anything (no silent defaults, D-IMPL-38).
* **The full state machine runs behind the ApprovalSink Protocol** —
  requested → pending-approval → effective/refused, plus revoked — with the
  tier-2 requirement coming from the policy regime artifact, never code
  (D-09; D-IMPL-29).
* **Every transition is audited** through the injected AuditLog with the
  injected clock (D-09; T-05-16), refusals included (``resolved=False``).
* **The in-force skill-set has the D-07 identity** —
  ``content_hash(frozenset(active grant hashes))`` — deterministic across
  arrival orders, restored by revocation, and never an epoch counter; the
  agent's definition hash is unchanged across grants (channel separation).

All identifiers, allowances, and grant values live in
``tests/fixtures/banking/skills/grants.yaml`` (§6.4).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.agents.definitions import AGENT_DEFINITION, AgentDefinition
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.audit import AuditLog
from ccf.controlplane.registry import (
    AmbiguousPinnedVersionError,
    ControlPlaneRegistry,
)
from ccf.replay.record import NO_GRANTS_SET_HASH
from ccf.skills.catalog import SKILL_CATALOG_ENTRY, SkillCatalog, SkillCatalogEntry
from ccf.skills.catalog import SkillNotInCatalog
from ccf.skills.grants import (
    SKILL_GRANT,
    ApprovalRejected,
    ApprovalSink,
    GovernanceUndeclared,
    GrantCollisionError,
    GrantLedger,
    GrantRefusal,
    GrantTransitionError,
    PolicyRegimeUnresolvable,
    RequirementsExceedRegime,
    SkillGrant,
    TenantMismatch,
    grant_set_hash,
    skill_grant_key,
)
from skills.sinks import RaisingApprovalSink, ScriptedApprovalSink

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking" / "skills"


def _grants_fixture() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load((FIXTURES / "grants.yaml").read_text())
    return loaded


def _tool_fixture() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "covenant_metrics_tool.yaml").read_text()
    )
    return loaded


@pytest.fixture(scope="module")
def fixture() -> dict[str, Any]:
    return _grants_fixture()


@pytest.fixture
def instant(fixture: dict[str, Any]) -> datetime:
    return datetime.fromisoformat(fixture["clock"]["start"])


class _World:
    """One registry + catalog + audit log + ledger, built from fixtures."""

    def __init__(
        self,
        fixture: dict[str, Any],
        instant: datetime,
        *,
        approve: bool = True,
    ) -> None:
        self.fixture = fixture
        # One shared AuditLog between registry and ledger (WR-07): the
        # Control Plane is the audit plane, singular (whitepaper §7.8.2).
        self.audit = AuditLog()
        self.registry = ControlPlaneRegistry(
            clock=lambda: instant, audit_log=self.audit
        )
        self.catalog = SkillCatalog(self.registry)
        self.sink = ScriptedApprovalSink(
            approve=approve, approver_id=fixture["approval"]["approver_id"]
        )
        for regime in fixture["policy_regimes"].values():
            artifact_class = declared_artifact_class(regime["class_id"])
            declared = parse_artifact(
                {
                    "class_id": regime["class_id"],
                    "semver": regime["semver"],
                    "declaration": regime["declaration"],
                },
                artifact_class,
            )
            self.registry.register_typed(regime["key"], declared, artifact_class)
        tool = _tool_fixture()
        for document in (
            tool["entry"],
            *tool["variants"].values(),
            *fixture["skills"].values(),
        ):
            entry = parse_artifact(document, SKILL_CATALOG_ENTRY)
            assert isinstance(entry, SkillCatalogEntry)
            outcome = self.catalog.register(entry)
            assert isinstance(outcome, str)
        self.ledger = GrantLedger(
            control_plane=self.registry,
            catalog=self.catalog,
            audit=self.audit,
            sink=self.sink,
            clock=lambda: instant,
        )
        self.actor: str = fixture["approval"]["requesting_actor"]

    def definition(self, which: str) -> AgentDefinition:
        parsed = parse_artifact(self.fixture["agents"][which], AGENT_DEFINITION)
        assert isinstance(parsed, AgentDefinition)
        return parsed

    def grant(self, which: str, definition: AgentDefinition) -> SkillGrant:
        return SkillGrant(
            agent_definition_hash=content_hash(definition),
            **self.fixture["grants"][which],
        )


@pytest.fixture
def world(fixture: dict[str, Any], instant: datetime) -> _World:
    return _World(fixture, instant)


@pytest.fixture
def rejecting_world(fixture: dict[str, Any], instant: datetime) -> _World:
    return _World(fixture, instant, approve=False)


# --- the grant artifact -----------------------------------------------------


class TestGrantArtifact:
    def test_a_grant_registers_via_the_control_plane_and_hash_is_identity(
        self, world: _World
    ) -> None:
        """The grant is a versioned Control Plane artifact (D-IMPL-12/26)."""
        definition = world.definition("auto")
        grant = world.grant("metrics_tool", definition)
        outcome = world.ledger.request(grant, definition=definition, actor=world.actor)
        assert outcome == content_hash(grant)
        key = skill_grant_key(grant)
        stored = world.registry.resolve(key, content_hash(grant))
        assert stored == grant
        assert world.registry.artifact_class_of(key) == SKILL_GRANT.class_id

    def test_a_grant_references_the_catalog_entry_by_pinned_version(
        self, world: _World
    ) -> None:
        definition = world.definition("auto")
        grant = world.grant("metrics_tool", definition)
        entry = world.catalog.resolve(grant.tenant, grant.skill_name, grant.skill_version)
        assert entry.name == grant.skill_name


# --- tier 1: non-waivable policy-compatibility check -------------------------


class TestTierOne:
    def test_excess_scopes_are_refused_naming_the_excess_identifiers(
        self, world: _World
    ) -> None:
        definition = world.definition("auto")
        grant = world.grant("writeback", definition)
        refusal = world.ledger.request(grant, definition=definition, actor=world.actor)
        assert isinstance(refusal, RequirementsExceedRegime)
        assert refusal.excess_scopes == frozenset(
            world.fixture["expected_excess"]["scopes"]
        )
        assert refusal.excess_context_products == frozenset()
        assert world.ledger.state(content_hash(grant)) == "refused"

    def test_excess_context_products_are_refused_naming_the_excess(
        self, world: _World
    ) -> None:
        definition = world.definition("auto")
        grant = world.grant("offcontract", definition)
        refusal = world.ledger.request(grant, definition=definition, actor=world.actor)
        assert isinstance(refusal, RequirementsExceedRegime)
        assert refusal.excess_context_products == frozenset(
            world.fixture["expected_excess"]["context_products"]
        )
        assert refusal.excess_scopes == frozenset()

    def test_a_missing_policy_regime_refuses_rather_than_defaults(
        self, world: _World
    ) -> None:
        """No silent defaults (D-IMPL-38): unresolvable regime → refusal."""
        definition = world.definition("unresolvable")
        grant = world.grant("metrics_tool", definition)
        refusal = world.ledger.request(grant, definition=definition, actor=world.actor)
        assert isinstance(refusal, PolicyRegimeUnresolvable)
        assert definition.policy_regime.ref in refusal.detail or refusal.ref

    def test_a_regime_without_skill_governance_refuses(self, world: _World) -> None:
        definition = world.definition("ungoverned")
        grant = world.grant("metrics_tool", definition)
        refusal = world.ledger.request(grant, definition=definition, actor=world.actor)
        assert isinstance(refusal, GovernanceUndeclared)

    def test_a_tier_1_refusal_is_a_returned_contract_value(
        self, world: _World
    ) -> None:
        """GateRefusal discipline: a bad grant is data, not control flow."""
        definition = world.definition("auto")
        grant = world.grant("writeback", definition)
        refusal = world.ledger.request(grant, definition=definition, actor=world.actor)
        assert isinstance(refusal, GrantRefusal)
        assert isinstance(refusal, CCFContract)

    def test_tier_1_refuses_before_tier_2_is_ever_consulted(
        self, world: _World
    ) -> None:
        """Tier 1 always runs first: the sink never sees a tier-1 failure."""
        definition = world.definition("gated")
        grant = world.grant("writeback", definition)
        refusal = world.ledger.request(grant, definition=definition, actor=world.actor)
        assert isinstance(refusal, RequirementsExceedRegime)
        assert world.sink.decided == []


# --- the state machine behind the ApprovalSink -------------------------------


class TestStateMachine:
    def test_an_auto_regime_goes_requested_to_effective_without_the_sink(
        self, world: _World
    ) -> None:
        definition = world.definition("auto")
        grant = world.grant("metrics_tool", definition)
        outcome = world.ledger.request(grant, definition=definition, actor=world.actor)
        assert isinstance(outcome, str)
        assert world.ledger.state(content_hash(grant)) == "effective"
        assert world.sink.decided == []

    def test_a_gated_regime_suspends_on_the_sink_then_becomes_effective(
        self, world: _World
    ) -> None:
        definition = world.definition("gated")
        grant = world.grant("metrics_tool", definition)
        outcome = world.ledger.request(grant, definition=definition, actor=world.actor)
        assert isinstance(outcome, str)
        assert world.ledger.state(content_hash(grant)) == "effective"
        assert world.sink.decided == [grant]
        actions = [event.action for event in world.audit.events()]
        assert "grant_pending_approval" in actions
        assert actions.index("grant_pending_approval") < actions.index(
            "grant_effective"
        )

    def test_a_sink_rejection_refuses_the_grant(
        self, rejecting_world: _World
    ) -> None:
        world = rejecting_world
        definition = world.definition("gated")
        grant = world.grant("metrics_tool", definition)
        refusal = world.ledger.request(grant, definition=definition, actor=world.actor)
        assert isinstance(refusal, ApprovalRejected)
        assert refusal.approver_id == world.fixture["approval"]["approver_id"]
        assert world.ledger.state(content_hash(grant)) == "refused"

    def test_an_effective_grant_can_be_revoked(self, world: _World) -> None:
        definition = world.definition("auto")
        grant = world.grant("metrics_tool", definition)
        world.ledger.request(grant, definition=definition, actor=world.actor)
        world.ledger.revoke(content_hash(grant), actor=world.actor)
        assert world.ledger.state(content_hash(grant)) == "revoked"

    def test_revoking_a_non_effective_grant_raises_the_typed_error(
        self, world: _World
    ) -> None:
        definition = world.definition("auto")
        grant = world.grant("writeback", definition)
        world.ledger.request(grant, definition=definition, actor=world.actor)
        with pytest.raises(GrantTransitionError):
            world.ledger.revoke(content_hash(grant), actor=world.actor)

    def test_revoking_an_unknown_grant_raises_the_typed_error(
        self, world: _World
    ) -> None:
        with pytest.raises(GrantTransitionError):
            world.ledger.revoke("never-requested", actor=world.actor)

    def test_re_requesting_a_decided_grant_raises_the_typed_error(
        self, world: _World
    ) -> None:
        definition = world.definition("auto")
        grant = world.grant("metrics_tool", definition)
        world.ledger.request(grant, definition=definition, actor=world.actor)
        with pytest.raises(GrantTransitionError):
            world.ledger.request(grant, definition=definition, actor=world.actor)


# --- audit: every transition, injected clock (D-09; T-05-16) -----------------


class TestAudit:
    def test_every_transition_lands_in_the_audit_log_with_the_injected_clock(
        self, world: _World, instant: datetime
    ) -> None:
        definition = world.definition("gated")
        grant = world.grant("metrics_tool", definition)
        world.ledger.request(grant, definition=definition, actor=world.actor)
        world.ledger.revoke(content_hash(grant), actor=world.actor)
        # The log is shared with the registry (WR-07), so grant lifecycle
        # events are filtered out of the single unified sequence here.
        events = [
            event
            for event in world.audit.events()
            if event.action.startswith("grant_")
        ]
        assert [event.action for event in events] == [
            "grant_requested",
            "grant_pending_approval",
            "grant_effective",
            "grant_revoked",
        ]
        sequences = [event.sequence for event in events]
        assert sequences == sorted(sequences)
        assert len(set(sequences)) == len(sequences)
        for event in events:
            assert event.occurred_at == instant
            assert event.key == skill_grant_key(grant)
            assert event.version == content_hash(grant)
            assert event.artifact_class == SKILL_GRANT.class_id
        assert events[0].actor == world.actor
        assert events[2].actor == world.fixture["approval"]["approver_id"]

    def test_a_tier_1_refusal_is_audited_as_unresolved(self, world: _World) -> None:
        definition = world.definition("auto")
        grant = world.grant("writeback", definition)
        world.ledger.request(grant, definition=definition, actor=world.actor)
        events = [
            event
            for event in world.audit.events()
            if event.action.startswith("grant_")
        ]
        assert [event.action for event in events] == [
            "grant_requested",
            "grant_refused",
        ]
        assert events[-1].resolved is False

    def test_a_sink_rejection_is_audited_with_the_approver_as_actor(
        self, rejecting_world: _World
    ) -> None:
        world = rejecting_world
        definition = world.definition("gated")
        grant = world.grant("metrics_tool", definition)
        world.ledger.request(grant, definition=definition, actor=world.actor)
        refused = world.audit.events()[-1]
        assert refused.action == "grant_refused"
        assert refused.resolved is False
        assert refused.actor == world.fixture["approval"]["approver_id"]

    def test_registry_and_grant_lifecycle_share_one_audit_sequence(
        self, world: _World
    ) -> None:
        """WR-07: one log, one sequence, one clock — the grant artifact's
        registration event and its lifecycle events land in the SAME
        AuditLog with monotonic sequence numbers (whitepaper §7.8.2: the
        Control Plane is the audit plane, singular)."""
        definition = world.definition("auto")
        grant = world.grant("metrics_tool", definition)
        outcome = world.ledger.request(
            grant, definition=definition, actor=world.actor
        )
        assert isinstance(outcome, str)
        # Literally one log: the registry's view IS the ledger's view.
        events = world.audit.events()
        assert world.registry.audit_events() == events
        assert world.registry.audit_log is world.audit
        actions = [event.action for event in events]
        registration_index = next(
            index
            for index, event in enumerate(events)
            if event.action == "register_versioned"
            and event.key == skill_grant_key(grant)
        )
        assert "grant_requested" in actions
        assert "grant_effective" in actions
        # Registration precedes the lifecycle it enables, in one sequence.
        assert registration_index < actions.index("grant_requested")
        assert actions.index("grant_requested") < actions.index(
            "grant_effective"
        )
        assert [event.sequence for event in events] == list(range(len(events)))


# --- the D-07 grant-set hash --------------------------------------------------


class TestGrantSetHash:
    def test_the_module_function_is_exactly_content_hash_over_the_frozenset(
        self, world: _World
    ) -> None:
        definition = world.definition("auto")
        hashes = frozenset(
            {
                content_hash(world.grant("metrics_tool", definition)),
                content_hash(world.grant("metrics_local", definition)),
            }
        )
        assert grant_set_hash(hashes) == content_hash(hashes)

    def test_the_hash_is_deterministic_across_arrival_orders(
        self, fixture: dict[str, Any], instant: datetime
    ) -> None:
        """Frozenset semantics, never insertion order (RESEARCH Pitfall 3)."""
        one = _World(fixture, instant)
        two = _World(fixture, instant)
        definition = one.definition("auto")
        for world, order in ((one, ("metrics_tool", "metrics_local")),
                             (two, ("metrics_local", "metrics_tool"))):
            for which in order:
                grant = world.grant(which, definition)
                assert isinstance(
                    world.ledger.request(
                        grant, definition=definition, actor=world.actor
                    ),
                    str,
                )
        assert one.ledger.grant_set_hash(
            content_hash(definition)
        ) == two.ledger.grant_set_hash(content_hash(definition))

    def test_revocation_restores_the_prior_hash(self, world: _World) -> None:
        definition = world.definition("auto")
        agent_hash = content_hash(definition)
        first = world.grant("metrics_tool", definition)
        world.ledger.request(first, definition=definition, actor=world.actor)
        before = world.ledger.grant_set_hash(agent_hash)
        second = world.grant("metrics_local", definition)
        world.ledger.request(second, definition=definition, actor=world.actor)
        assert world.ledger.grant_set_hash(agent_hash) != before
        world.ledger.revoke(content_hash(second), actor=world.actor)
        assert world.ledger.grant_set_hash(agent_hash) == before

    def test_no_grants_in_force_is_the_positive_sentinel(
        self, world: _World
    ) -> None:
        definition = world.definition("auto")
        assert (
            world.ledger.grant_set_hash(content_hash(definition))
            == NO_GRANTS_SET_HASH
        )

    def test_grant_set_hash_is_per_agent_across_two_agents(
        self, world: _World
    ) -> None:
        """CR-01 regression: two agents share one ledger; a grant to agent B
        never moves agent A's D-07 grant-set hash — dimension 4 records the
        skills *this* agent actually had (CLAUDE.md §6.2)."""
        agent_a = world.definition("auto")
        agent_b = world.definition("gated")
        hash_a = content_hash(agent_a)
        hash_b = content_hash(agent_b)

        grant_b = world.grant("metrics_tool", agent_b)
        outcome = world.ledger.request(
            grant_b, definition=agent_b, actor=world.actor
        )
        assert isinstance(outcome, str)
        assert world.ledger.grant_set_hash(hash_a) == NO_GRANTS_SET_HASH
        b_after_own_grant = world.ledger.grant_set_hash(hash_b)
        assert b_after_own_grant != NO_GRANTS_SET_HASH

        grant_a = world.grant("metrics_local", agent_a)
        outcome = world.ledger.request(
            grant_a, definition=agent_a, actor=world.actor
        )
        assert isinstance(outcome, str)
        assert world.ledger.grant_set_hash(hash_b) == b_after_own_grant
        assert world.ledger.grant_set_hash(hash_a) == grant_set_hash(
            frozenset({content_hash(grant_a)})
        )
        assert world.ledger.effective_hashes(hash_a) == frozenset(
            {content_hash(grant_a)}
        )
        assert world.ledger.effective_hashes() == frozenset(
            {content_hash(grant_a), content_hash(grant_b)}
        )

    def test_the_agent_definition_hash_is_unchanged_across_grants(
        self, world: _World
    ) -> None:
        """Channel separation (D-07): skilling never touches agent identity —
        no epoch counter, no version bump."""
        definition = world.definition("auto")
        before = content_hash(definition)
        for which in ("metrics_tool", "metrics_local"):
            grant = world.grant(which, definition)
            world.ledger.request(grant, definition=definition, actor=world.actor)
        world.ledger.revoke(
            content_hash(world.grant("metrics_local", definition)), actor=world.actor
        )
        assert content_hash(definition) == before


# --- governance seams: WR-02 / WR-04 / WR-05 ----------------------------------


class TestGovernanceSeams:
    def test_a_missing_catalog_entry_leaves_no_wedged_state(
        self, world: _World
    ) -> None:
        """WR-04: resolve-before-mutate — a SkillNotInCatalog failure leaves
        the ledger untouched, is audited, and the same grant content hash
        succeeds once the entry exists."""
        definition = world.definition("auto")
        grant = world.grant("latecomer", definition)
        with pytest.raises(SkillNotInCatalog):
            world.ledger.request(grant, definition=definition, actor=world.actor)
        with pytest.raises(KeyError):
            world.ledger.state(content_hash(grant))
        failed = world.audit.events()[-1]
        assert failed.action == "grant_refused"
        assert failed.resolved is False
        assert failed.key == skill_grant_key(grant)

        entry = parse_artifact(
            world.fixture["late_skills"]["latecomer"], SKILL_CATALOG_ENTRY
        )
        assert isinstance(entry, SkillCatalogEntry)
        registered = world.catalog.register(entry)
        assert isinstance(registered, str)
        outcome = world.ledger.request(
            grant, definition=definition, actor=world.actor
        )
        assert outcome == content_hash(grant)
        assert world.ledger.state(content_hash(grant)) == "effective"

    def test_a_cross_tenant_grant_is_refused(self, world: _World) -> None:
        """WR-02: a grant whose tenant differs from the agent definition's
        tenant is inadmissible — a typed, audited tier-1-style refusal."""
        definition = world.definition("auto")
        grant = world.grant("crosstenant", definition)
        refusal = world.ledger.request(
            grant, definition=definition, actor=world.actor
        )
        assert isinstance(refusal, TenantMismatch)
        assert refusal.grant_tenant == grant.tenant
        assert refusal.definition_tenant == definition.tenant
        assert refusal.grant_tenant != refusal.definition_tenant
        assert world.ledger.state(content_hash(grant)) == "refused"
        refused = world.audit.events()[-1]
        assert refused.action == "grant_refused"
        assert refused.resolved is False

    def test_two_effective_same_skill_name_grants_raise_the_typed_error(
        self, world: _World
    ) -> None:
        """WR-05: a same-name double-effective state is a governance-state
        defect — GrantCollisionError naming the skill and both hashes,
        never a silent hash-lottery."""
        definition = world.definition("auto")
        first = world.grant("metrics_tool", definition)
        second = world.grant("metrics_upgrade", definition)
        for grant in (first, second):
            outcome = world.ledger.request(
                grant, definition=definition, actor=world.actor
            )
            assert isinstance(outcome, str)
        view = world.ledger.bound_view(content_hash(definition))
        with pytest.raises(GrantCollisionError) as excinfo:
            len(view)
        assert excinfo.value.skill_name == first.skill_name
        assert {excinfo.value.first_hash, excinfo.value.second_hash} == {
            content_hash(first),
            content_hash(second),
        }
        world.ledger.revoke(content_hash(first), actor=world.actor)
        assert set(view) == {second.skill_name}


# --- WR-01: no path leaves a grant wedged -------------------------------------


class TestNoWedgedStates:
    """Every post-mutation failure path settles the grant in a terminal state.

    `requested` and `pending-approval` are transient by construction: the
    machine defines no exit from either (revocation is defined from
    `effective` only), so a grant stranded in one of them is unrecoverable
    governance state. The guard in ``GrantLedger.request`` must therefore
    hold for exceptions raised *after* the first state mutation, not only for
    the catalog-resolution failure the earlier fix covered.
    """

    def test_a_raising_approval_sink_refuses_rather_than_wedging(
        self, fixture: dict[str, Any], instant: datetime
    ) -> None:
        """The sink is arbitrary Protocol code and may raise; the ledger must
        not be left holding a `pending-approval` grant it can never settle."""
        world = _World(fixture, instant)
        error = RuntimeError("the approval queue is unreachable")
        # A ledger over the same registry, catalog, and audit log, decided by
        # a sink that raises — everything injected, nothing patched.
        world.ledger = GrantLedger(
            control_plane=world.registry,
            catalog=world.catalog,
            audit=world.audit,
            sink=RaisingApprovalSink(error),
            clock=lambda: instant,
        )
        definition = world.definition("gated")
        grant = world.grant("metrics_tool", definition)

        with pytest.raises(RuntimeError) as excinfo:
            world.ledger.request(grant, definition=definition, actor=world.actor)
        assert excinfo.value is error  # re-raised unchanged, never swallowed

        assert world.ledger.state(content_hash(grant)) == "refused"
        refused = world.audit.events()[-1]
        assert refused.action == "grant_refused"
        assert refused.resolved is False
        assert refused.key == skill_grant_key(grant)
        # The terminal state is real: the grant confers nothing and does not
        # move this agent's D-07 set identity.
        assert world.ledger.effective_hashes(content_hash(definition)) == frozenset()
        assert world.ledger.grant_set_hash(content_hash(definition)) == (
            NO_GRANTS_SET_HASH
        )

    def test_an_ambiguous_policy_regime_refuses_rather_than_wedging(
        self, fixture: dict[str, Any], instant: datetime
    ) -> None:
        """`_resolve_policy_regime` raises AmbiguousPinnedVersionError from
        inside tier 1 — after the `requested` mutation. The grant must end
        `refused`, not stranded in `requested`."""
        world = _World(fixture, instant)
        regime = fixture["policy_regimes"]["auto"]
        artifact_class = declared_artifact_class(regime["class_id"])
        # A second content under the same key declaring the same semver: two
        # candidate governance inputs for one pinned ref.
        rival_declaration = dict(regime["declaration"])
        rival_declaration["ccf_test_disambiguator"] = "rival"
        rival = parse_artifact(
            {
                "class_id": regime["class_id"],
                "semver": regime["semver"],
                "declaration": rival_declaration,
            },
            artifact_class,
        )
        world.registry.register_typed(regime["key"], rival, artifact_class)

        definition = world.definition("auto")
        grant = world.grant("metrics_tool", definition)
        with pytest.raises(AmbiguousPinnedVersionError):
            world.ledger.request(grant, definition=definition, actor=world.actor)

        assert world.ledger.state(content_hash(grant)) == "refused"
        refused = world.audit.events()[-1]
        assert refused.action == "grant_refused"
        assert refused.resolved is False


# --- the Protocol is runtime-checkable ----------------------------------------


def test_the_scripted_double_conforms_to_the_approval_sink_protocol(
    fixture: dict[str, Any],
) -> None:
    sink = ScriptedApprovalSink(
        approve=True, approver_id=fixture["approval"]["approver_id"]
    )
    assert isinstance(sink, ApprovalSink)
