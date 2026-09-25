"""§9 controls for ``GrantLedger.request`` / ``revoke`` — D-IMPL-353 §1.2, §1.3, §1.5.

The ledger requires the kind for the transition it performs:
``Authorized[SkillGrant]`` to request, ``Authorized[SkillRevoke]`` to revoke —
``SkillGrant is not SkillRevoke``. The actor is ``authorized.principal``; the
grant hash a revoke acts on IS the capability's resource; the request binds
the capability's resource to the definition it was handed (§1.5f); every
state transition and the derived registration of the grant artifact write
under the capability's tenant.

Controls: wrong kind (a grant capability handed to ``revoke`` and the
reverse), fabrication, retargeting, the definition bind, the cross-tenant
revoke that finds nothing, and the positive that the audit actor is the
principal on every transition.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from ccf.agents.definitions import AGENT_DEFINITION, AgentDefinition
from ccf.authz.capability import (
    ArtifactWrite,
    CapabilityBypassError,
    Execute,
    Register,
)
from ccf.authz.capability import SkillGrant as SkillGrantKind
from ccf.authz.capability import SkillRevoke as SkillRevokeKind
from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.audit import AuditLog
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.controlplane.state import state_key
from ccf.skills.catalog import SKILL_CATALOG_ENTRY, SkillCatalog, SkillCatalogEntry
from ccf.skills.grants import (
    GRANT_STATE,
    GrantAuthorityMismatch,
    GrantLedger,
    GrantTransitionError,
    SkillGrant,
    skill_grant_key,
)
from skills.sinks import ScriptedApprovalSink
from tests.controlplane.capabilities import (
    RETARGETS,
    capability,
    fabrications,
    register_capability,
    retarget,
)
from tests.skills.authority import (
    definition_key,
    grant_capability,
    register_entry,
    revoke_capability,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking" / "skills"


def _load(name: str) -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load((FIXTURES / name).read_text())
    return loaded


class _World:
    """The auto-approve world from ``test_grants.py``, built once per test."""

    def __init__(self) -> None:
        fixture = _load("grants.yaml")
        tool = _load("covenant_metrics_tool.yaml")
        instant = datetime.fromisoformat(fixture["clock"]["start"])
        self.fixture = fixture
        self.audit = AuditLog()
        self.registry = ControlPlaneRegistry(clock=lambda: instant, audit_log=self.audit)
        for regime in fixture["policy_regimes"].values():
            artifact_class = declared_artifact_class(regime["class_id"])
            declared = parse_artifact(
                {"class_id": regime["class_id"], "semver": regime["semver"], "declaration": regime["declaration"]},
                artifact_class,
            )
            self.registry.register_typed(register_capability(regime["key"], Register), declared, artifact_class)
        for document in (tool["entry"], *tool["variants"].values(), *fixture["skills"].values()):
            entry = parse_artifact(document, SKILL_CATALOG_ENTRY)
            assert isinstance(entry, SkillCatalogEntry)
            assert isinstance(register_entry(self.registry, entry), str)
        self.ledger = GrantLedger(
            control_plane=self.registry,
            catalog=SkillCatalog(self.registry),
            sink=ScriptedApprovalSink(approve=True, approver_id=fixture["approval"]["approver_id"]),
            clock=lambda: instant,
        )
        self.actor: str = fixture["approval"]["requesting_actor"]

    def definition(self, which: str = "auto") -> AgentDefinition:
        parsed = parse_artifact(self.fixture["agents"][which], AGENT_DEFINITION)
        assert isinstance(parsed, AgentDefinition)
        return parsed

    def grant(self, which: str, definition: AgentDefinition) -> SkillGrant:
        return SkillGrant(agent_definition_hash=content_hash(definition), **self.fixture["grants"][which])

    def effective(self) -> tuple[AgentDefinition, SkillGrant, str]:
        definition = self.definition()
        grant = self.grant("metrics_tool", definition)
        outcome = self.ledger.request(grant_capability(definition, principal=self.actor), grant, definition=definition)
        assert outcome == content_hash(grant)
        return definition, grant, content_hash(grant)

    def nothing_happened(self, grant: SkillGrant) -> None:
        assert self.registry.versions(skill_grant_key(grant)) == ()
        assert self.registry.state_store.items(GRANT_STATE) == ()
        assert [e.action for e in self.audit.events() if e.action.startswith("grant")] == []


@pytest.fixture
def world() -> _World:
    return _World()


# --- positive ------------------------------------------------------------------------


class TestPositive:
    def test_a_request_writes_state_and_the_artifact_under_the_capabilitys_tenant(
        self, world: _World
    ) -> None:
        definition, grant, grant_hash = world.effective()
        key = state_key(tenant=definition.tenant, record_id=grant_hash)
        assert world.registry.state_store.get(GRANT_STATE, key) is not None
        assert world.registry.versions(skill_grant_key(grant)) != ()
        assert world.ledger.state(grant_hash) == "effective"

    def test_the_audit_actor_is_the_principal_on_every_transition(self, world: _World) -> None:
        definition = world.definition()
        grant = world.grant("metrics_tool", definition)
        world.ledger.request(grant_capability(definition, principal="officer-9"), grant, definition=definition)
        grant_events = [e for e in world.audit.events() if e.action.startswith("grant")]
        assert grant_events, "no grant transition was audited — the control is vacuous"
        assert {e.actor for e in grant_events} == {"officer-9"}

    def test_a_revoke_takes_the_hash_from_the_capability_and_the_actor_from_the_principal(
        self, world: _World
    ) -> None:
        definition, _, grant_hash = world.effective()
        world.ledger.revoke(revoke_capability(grant_hash, tenant=definition.tenant, principal="risk-2"))
        assert world.ledger.state(grant_hash) == "revoked"
        (revoked,) = [e for e in world.audit.events() if e.action == "grant_revoked"]
        assert revoked.actor == "risk-2"

    def test_the_handles_offer_no_actor_and_no_hash_parameter(self) -> None:
        import inspect

        request = inspect.signature(GrantLedger.request).parameters
        revoke = inspect.signature(GrantLedger.revoke).parameters
        assert list(request)[:2] == ["self", "authorized"] and "actor" not in request
        assert list(revoke) == ["self", "authorized"]


# --- §1.5f the definition bind, and §1.3 the tenant ----------------------------------------


class TestBind:
    def test_a_grant_capability_for_one_definition_does_not_cover_another(self, world: _World) -> None:
        auto, gated = world.definition("auto"), world.definition("gated")
        grant = world.grant("metrics_tool", gated)
        with pytest.raises(GrantAuthorityMismatch):
            world.ledger.request(grant_capability(auto), grant, definition=gated)
        world.nothing_happened(grant)

    def test_a_capability_for_another_tenant_does_not_cover_the_definition(self, world: _World) -> None:
        definition = world.definition()
        grant = world.grant("metrics_tool", definition)
        foreign = capability(SkillGrantKind, tenant="other-bank", resource=definition_key(definition))
        with pytest.raises(GrantAuthorityMismatch):
            world.ledger.request(foreign, grant, definition=definition)
        world.nothing_happened(grant)

    def test_a_revoke_capability_for_another_tenant_finds_nothing_to_revoke(self, world: _World) -> None:
        _, _, grant_hash = world.effective()
        with pytest.raises(GrantTransitionError):
            world.ledger.revoke(revoke_capability(grant_hash, tenant="other-bank"))
        assert world.ledger.state(grant_hash) == "effective"


# --- wrong kind ------------------------------------------------------------------------


class TestWrongKind:
    def test_a_grant_capability_does_not_revoke(self, world: _World) -> None:
        definition, _, grant_hash = world.effective()
        wrong = capability(SkillGrantKind, tenant=definition.tenant, resource=grant_hash)
        with pytest.raises(CapabilityBypassError, match="kind"):
            world.ledger.revoke(cast(Any, wrong))
        assert world.ledger.state(grant_hash) == "effective"

    def test_a_revoke_capability_does_not_grant(self, world: _World) -> None:
        definition = world.definition()
        grant = world.grant("metrics_tool", definition)
        wrong = capability(SkillRevokeKind, tenant=definition.tenant, resource=definition_key(definition))
        with pytest.raises(CapabilityBypassError, match="kind"):
            world.ledger.request(cast(Any, wrong), grant, definition=definition)
        world.nothing_happened(grant)

    @pytest.mark.parametrize("wrong", [Register, ArtifactWrite, Execute])
    def test_no_other_kind_grants(self, world: _World, wrong: type) -> None:
        definition = world.definition()
        grant = world.grant("metrics_tool", definition)
        with pytest.raises(CapabilityBypassError, match="kind"):
            world.ledger.request(
                cast(Any, capability(wrong, tenant=definition.tenant, resource=definition_key(definition))),
                grant,
                definition=definition,
            )
        world.nothing_happened(grant)


# --- fabrication ------------------------------------------------------------------------


class TestFabrication:
    @pytest.mark.parametrize(
        "label,fake",
        list(fabrications(SkillGrantKind, tenant="acme-bank", resource="acme-bank/ccf.agent-definition/treasury-analytics-auto")),
        ids=lambda v: v if isinstance(v, str) else "",
    )
    def test_every_fabrication_dies_at_verify_on_request(self, world: _World, label: str, fake: object) -> None:
        definition = world.definition()
        grant = world.grant("metrics_tool", definition)
        with pytest.raises(CapabilityBypassError):
            world.ledger.request(cast(Any, fake), grant, definition=definition)
        world.nothing_happened(grant)

    @pytest.mark.parametrize(
        "label,fake",
        list(fabrications(SkillRevokeKind, tenant="acme-bank", resource="0" * 64)),
        ids=lambda v: v if isinstance(v, str) else "",
    )
    def test_every_fabrication_dies_at_verify_on_revoke(self, world: _World, label: str, fake: object) -> None:
        _, _, grant_hash = world.effective()
        with pytest.raises(CapabilityBypassError):
            world.ledger.revoke(cast(Any, fake))
        assert world.ledger.state(grant_hash) == "effective"


# --- retargeting (§1.5g) -------------------------------------------------------------------


class TestRetargeting:
    @pytest.mark.parametrize("field", sorted(RETARGETS))
    def test_a_forced_retarget_grants_nothing(self, world: _World, field: str) -> None:
        definition = world.definition()
        grant = world.grant("metrics_tool", definition)
        cap = grant_capability(definition)
        retarget(cap, field, RETARGETS[field])
        with pytest.raises(CapabilityBypassError):
            world.ledger.request(cap, grant, definition=definition)
        world.nothing_happened(grant)

    def test_a_grant_kind_retargeted_to_revoke_revokes_nothing(self, world: _World) -> None:
        definition, _, grant_hash = world.effective()
        cap = capability(SkillGrantKind, tenant=definition.tenant, resource=grant_hash)
        retarget(cap, "kind", SkillRevokeKind)
        assert getattr(cap, "kind") is SkillRevokeKind  # the naive check WOULD pass
        with pytest.raises(CapabilityBypassError):
            world.ledger.revoke(cast(Any, cap))
        assert world.ledger.state(grant_hash) == "effective"
