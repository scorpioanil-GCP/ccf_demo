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
    RefuseUnbumpedChange,
)
from ccf.replay.record import NO_GRANTS_SET_HASH
from ccf.skills.catalog import SKILL_CATALOG_ENTRY, SkillCatalog, SkillCatalogEntry
from ccf.skills.catalog import SkillNotInCatalog
from ccf.skills.grants import (
    GRANT_STATE,
    SKILL_GRANT,
    ApprovalRejected,
    ApprovalSink,
    GovernanceUndeclared,
    GrantCollisionError,
    GrantLedger,
    GrantRefusal,
    GrantStateRecord,
    GrantTransitionError,
    PolicyRegimeUnresolvable,
    RequirementsExceedRegime,
    SkillGrant,
    SplitAuditPlaneError,
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

    def test_a_refused_cross_tenant_grant_never_enters_the_registry(
        self, world: _World
    ) -> None:
        """IN-04: registration is append-only, so a refusal that registered
        anyway would leave the inadmissible document resolvable forever under
        the *foreign* tenant's key namespace. The tenant check therefore runs
        before registration, not after."""
        definition = world.definition("auto")
        grant = world.grant("crosstenant", definition)
        key = skill_grant_key(grant)
        assert key.startswith(f"{grant.tenant}/")
        assert grant.tenant != definition.tenant

        refusal = world.ledger.request(
            grant, definition=definition, actor=world.actor
        )
        assert isinstance(refusal, TenantMismatch)

        # nothing under the foreign tenant's prefix, by any route
        assert world.registry.versions(key) == ()
        assert not any(
            registered_key.startswith(f"{grant.tenant}/")
            for registered_key in world.registry.keys_of_class(
                SKILL_GRANT.class_id
            )
        )
        # and no registration was audited for it
        assert not any(
            event.key == key and event.action.startswith("register")
            for event in world.audit.events()
        )
        # the refusal is still terminal and still audited
        assert world.ledger.state(content_hash(grant)) == "refused"

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


    def test_a_rejected_grant_can_be_re_issued_with_a_bumped_version(
        self, fixture: dict[str, Any], instant: datetime
    ) -> None:
        """WR-02: the documented remediation actually works.

        `GrantTransitionError` sends the caller to a new grant artifact, and
        a re-issued grant legitimately differs from the declined one in
        `artifact_version` alone. The D-05 empty-bump refusal must not close
        that path — otherwise the only retry is renaming the grant, minting a
        second Control Plane key for one request.
        """
        world = _World(fixture, instant, approve=False)
        definition = world.definition("gated")
        grant = world.grant("metrics_tool", definition)
        rejected = world.ledger.request(
            grant, definition=definition, actor=world.actor
        )
        assert isinstance(rejected, ApprovalRejected)
        assert world.ledger.state(content_hash(grant)) == "refused"

        major, minor, patch = (int(part) for part in grant.artifact_version.split("."))
        reissued = grant.model_copy(
            update={"artifact_version": f"{major}.{minor}.{patch + 1}"}
        )
        assert content_hash(reissued) != content_hash(grant)

        # The approver relents; the same request is submitted again.
        world.ledger = GrantLedger(
            control_plane=world.registry,
            catalog=world.catalog,
            audit=world.audit,
            sink=ScriptedApprovalSink(
                approve=True, approver_id=fixture["approval"]["approver_id"]
            ),
            clock=lambda: instant,
        )
        outcome = world.ledger.request(
            reissued, definition=definition, actor=world.actor
        )
        assert outcome == content_hash(reissued)
        assert world.ledger.state(content_hash(reissued)) == "effective"
        # One key, two registered versions — not a second key for one request.
        key = skill_grant_key(grant)
        assert skill_grant_key(reissued) == key
        assert set(world.registry.versions(key)) == {
            content_hash(grant),
            content_hash(reissued),
        }

    def test_an_unbumped_content_change_is_still_refused(
        self, world: _World
    ) -> None:
        """The re-issue allowance is not a licence to mutate content under a
        version already claimed: D-05's unbumped-change refusal still fires."""
        definition = world.definition("auto")
        grant = world.grant("metrics_tool", definition)
        assert isinstance(
            world.ledger.request(grant, definition=definition, actor=world.actor),
            str,
        )
        # Same artifact_version, different content, same key.
        divergent = grant.model_copy(update={"agent_definition_hash": "0" * 64})
        refusal = world.registry.register_versioned(
            skill_grant_key(divergent),
            divergent,
            SKILL_GRANT,
            actor=world.actor,
            reissuable=True,
        )
        assert isinstance(refusal, RefuseUnbumpedChange)


    def test_every_ledger_over_one_control_plane_agrees(
        self, fixture: dict[str, Any], instant: datetime
    ) -> None:
        """WR-05: grant state lives on the plane, so readers cannot diverge.

        Grant *artifacts* are immutable and register append-only; grant
        *state* is mutable until terminal and therefore lives on the Control
        Plane's state seam, per D-IMPL-27's mutability split and D-IMPL-18's
        ruling that such state sits on the Control Plane's storage seam.

        The property that matters is agreement: a ledger constructed after
        the fact reports the same effective set, the same per-agent
        ``grant_set_hash``, the same bound view, and the same state for a
        given hash. Before this fix the successor reported an empty set and
        the positive ``NO_GRANTS_SET_HASH`` claim while the registry held the
        grant and the log held its ``grant_effective`` event — so a
        replay-facing set identity was reproducible only on the instance that
        computed it, which is not what CLAUDE.md §6.2 asks of replay.
        """
        world = _World(fixture, instant)
        definition = world.definition("auto")
        grant = world.grant("metrics_tool", definition)
        assert isinstance(
            world.ledger.request(grant, definition=definition, actor=world.actor),
            str,
        )
        definition_hash = content_hash(definition)
        grant_hash = content_hash(grant)
        assert world.ledger.effective_hashes(definition_hash) == frozenset(
            {grant_hash}
        )

        # The artifact is in the registry and the transition is in the log.
        key = skill_grant_key(grant)
        assert world.registry.resolve(key, grant_hash) == grant
        assert "grant_effective" in [e.action for e in world.audit.events()]

        # A ledger built afterwards agrees on every replay-facing answer.
        successor = GrantLedger(
            control_plane=world.registry,
            catalog=world.catalog,
            audit=world.audit,
            sink=world.sink,
            clock=lambda: instant,
        )
        assert successor.effective_hashes(definition_hash) == frozenset(
            {grant_hash}
        )
        assert successor.grant_set_hash(
            definition_hash
        ) == world.ledger.grant_set_hash(definition_hash)
        assert successor.grant_set_hash(definition_hash) != NO_GRANTS_SET_HASH
        assert dict(successor.bound_view(definition_hash)) == dict(
            world.ledger.bound_view(definition_hash)
        )
        assert successor.state(grant_hash) == "effective"

    def test_a_revocation_on_one_ledger_is_seen_by_another(
        self, fixture: dict[str, Any], instant: datetime
    ) -> None:
        """Agreement holds across transitions, not only at first read.

        The seam would be worth little if readers agreed on the initial
        state and then drifted: a revocation through one ledger must be
        visible to every other over the same Control Plane, because that is
        what makes ``grant_set_hash`` answer "what was in force" rather than
        "what this instance was told".
        """
        world = _World(fixture, instant)
        definition = world.definition("auto")
        grant = world.grant("metrics_tool", definition)
        grant_hash = world.ledger.request(
            grant, definition=definition, actor=world.actor
        )
        assert isinstance(grant_hash, str)
        definition_hash = content_hash(definition)

        reader = GrantLedger(
            control_plane=world.registry,
            catalog=world.catalog,
            audit=world.audit,
            sink=world.sink,
            clock=lambda: instant,
        )
        before = reader.grant_set_hash(definition_hash)

        world.ledger.revoke(grant_hash, actor=world.actor)

        assert reader.state(grant_hash) == "revoked"
        assert reader.effective_hashes(definition_hash) == frozenset()
        assert reader.grant_set_hash(definition_hash) == NO_GRANTS_SET_HASH
        assert reader.grant_set_hash(definition_hash) != before

    def test_grant_state_is_addressed_on_the_control_plane_state_seam(
        self, fixture: dict[str, Any], instant: datetime
    ) -> None:
        """The state is on the seam, not on the ledger instance (D-IMPL-18/27).

        Pins the structural claim rather than only its consequence: an
        implementation that satisfied the agreement tests by, say, sharing a
        class-level cache between ledgers would pass those and still not be
        the ruled design.
        """
        world = _World(fixture, instant)
        definition = world.definition("auto")
        grant = world.grant("metrics_tool", definition)
        grant_hash = world.ledger.request(
            grant, definition=definition, actor=world.actor
        )
        assert isinstance(grant_hash, str)

        record = world.registry.state_store.get(GRANT_STATE, grant_hash)
        assert isinstance(record, GrantStateRecord)
        assert record.state == "effective"
        assert record.grant == grant

        # The ledger caches nothing of its own.
        assert not any(
            isinstance(value, dict) and grant_hash in value
            for value in vars(world.ledger).values()
        )


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


class TestSingularAuditPlane:
    """IN-03: the ledger cannot audit anywhere but its registry's own log."""

    def test_the_audit_log_defaults_to_the_registrys_own(
        self, fixture: dict[str, Any], instant: datetime
    ) -> None:
        world = _World(fixture, instant)
        ledger = GrantLedger(
            control_plane=world.registry,
            catalog=world.catalog,
            sink=world.sink,
            clock=lambda: instant,
        )
        definition = world.definition("auto")
        grant = world.grant("metrics_tool", definition)
        before = len(world.audit.events())
        result = ledger.request(
            grant, definition=definition, actor=world.actor
        )
        assert isinstance(result, str)
        # the transitions landed in the registry's log without being named
        assert len(world.audit.events()) > before
        assert any(
            event.action == "grant_effective"
            for event in world.audit.events()[before:]
        )

    def test_passing_the_registrys_own_log_is_still_accepted(
        self, fixture: dict[str, Any], instant: datetime
    ) -> None:
        """The parameter survives as an explicitness affordance."""
        world = _World(fixture, instant)
        GrantLedger(
            control_plane=world.registry,
            catalog=world.catalog,
            audit=world.registry.audit_log,
            sink=world.sink,
            clock=lambda: instant,
        )

    def test_a_foreign_audit_log_is_refused(
        self, fixture: dict[str, Any], instant: datetime
    ) -> None:
        world = _World(fixture, instant)
        with pytest.raises(SplitAuditPlaneError):
            GrantLedger(
                control_plane=world.registry,
                catalog=world.catalog,
                audit=AuditLog(),
                sink=world.sink,
                clock=lambda: instant,
            )


# --- the Protocol is runtime-checkable ----------------------------------------


def test_the_scripted_double_conforms_to_the_approval_sink_protocol(
    fixture: dict[str, Any],
) -> None:
    sink = ScriptedApprovalSink(
        approve=True, approver_id=fixture["approval"]["approver_id"]
    )
    assert isinstance(sink, ApprovalSink)
