"""§9 controls for ``ControlPlaneRegistry.register*`` — D-IMPL-353 §1.2, §1.3.

Three doors register under three declared actions — ``config.register``,
``agent.declare``, ``skill.catalog.register`` — so the handle accepts the
union and verifies against the kind the capability was MINTED for. **The key
is ``authorized.resource``**; there is no key parameter. The ONE tenant
comparison in the design (§1.3) lives here: the key's tenant segment must
equal ``authorized.tenant``.

The grant ledger's registration of the grant *artifact* is a derived write
(§1.2): the ``skill.grant`` decision named the agent definition, and the grant
artifact is a record that decision created. ``register_versioned`` therefore
also accepts ``Authorized[SkillGrant]``, deriving the key from the
capability's tenant, the declared class and the artifact's own ``name`` — no
caller-supplied key on that path either.

Controls, by clause: wrong kind (c), fabrication (§1.1), retargeting (g),
positive (each of the four kinds), and the tenant bind (§1.3). The static
tooth is measured by ``test_static_controls.py``.
"""

from __future__ import annotations

from typing import Any, cast

import pytest

from ccf.authz.capability import (
    ActionKind,
    AgentDeclare,
    ArtifactWrite,
    CapabilityBypassError,
    Execute,
    HitlSubmit,
    Register,
    SkillCatalogRegister,
    SkillGrant,
    SkillRevoke,
)
from ccf.contracts.base import CCFContract
from ccf.controlplane.artifact_base import ArtifactClass
from ccf.controlplane.registry import (
    DERIVED_REGISTER_KINDS,
    REGISTER_KINDS,
    ControlPlaneRegistry,
    CrossTenantKeyRefused,
)
from tests.controlplane.capabilities import (
    PRINCIPAL,
    RETARGETS,
    capability,
    fabrications,
    register_capability,
    retarget,
)

TENANT = "acme-bank"
KEY = f"{TENANT}/ccf.policy-bundle/underwriting"
FOREIGN_KEY = f"other-bank/ccf.policy-bundle/underwriting"


class _Named(CCFContract):
    """An author-versioned artifact that names itself — the derived-write shape."""

    artifact_version: str
    name: str
    tenant: str
    body: str


NAMED = ArtifactClass(class_id="test.named-artifact", contract=_Named)


def _named(*, tenant: str = TENANT, name: str = "grant-1", body: str = "x") -> _Named:
    return _Named(artifact_version="1.0.0", name=name, tenant=tenant, body=body)


def _nothing_registered(registry: ControlPlaneRegistry, *keys: str) -> None:
    """Through the UNAUDITED introspection surface, so the probe leaves no
    event behind and ``audit_events() == ()`` still measures the handle."""
    for key in keys:
        assert registry.versions(key) == ()
        assert registry.artifact_class_of(key) is None


# --- positive ---------------------------------------------------------------------


class TestPositive:
    def test_the_registering_kinds_are_the_three_doors_and_the_one_derived_writer(self) -> None:
        assert REGISTER_KINDS == (Register, AgentDeclare, SkillCatalogRegister)
        assert DERIVED_REGISTER_KINDS == (SkillGrant,)

    @pytest.mark.parametrize("kind", REGISTER_KINDS)
    def test_each_door_kind_registers_under_the_capabilitys_resource(
        self, kind: type[ActionKind]
    ) -> None:
        registry = ControlPlaneRegistry()
        version = registry.register(register_capability(KEY, kind), {"a": 1})
        assert registry.resolve(KEY, version) == {"a": 1}
        (event, *_) = registry.audit_events()
        assert (event.action, event.key, event.actor) == ("register", KEY, PRINCIPAL)

    def test_register_typed_and_versioned_take_the_key_from_the_capability_too(self) -> None:
        registry = ControlPlaneRegistry()
        typed = registry.register_typed(register_capability(KEY, Register), _named(), NAMED)
        assert registry.resolve(KEY, typed) == _named()
        bumped = _Named(artifact_version="1.1.0", name="grant-1", tenant=TENANT, body="y")
        versioned = registry.register_versioned(
            register_capability(KEY, AgentDeclare), bumped, NAMED
        )
        assert isinstance(versioned, str)
        assert registry.resolve(KEY, versioned) == bumped
        assert registry.versions(KEY) == (typed, versioned)

    def test_the_audit_actor_is_the_principal_and_nothing_a_caller_typed(self) -> None:
        registry = ControlPlaneRegistry()
        registry.register(
            register_capability(KEY, Register, principal="officer-7"), {"a": 1}
        )
        assert [e.actor for e in registry.audit_events()] == ["officer-7"]

    def test_a_derived_registration_derives_its_key_from_tenant_class_and_name(self) -> None:
        """The ledger's path: a ``SkillGrant`` for the agent definition
        registers the grant artifact under ``{tenant}/{class}/{artifact.name}``."""
        registry = ControlPlaneRegistry()
        definition_key = f"{TENANT}/ccf.agent-definition/analyst"
        authorized = capability(SkillGrant, tenant=TENANT, resource=definition_key)
        version = registry.register_versioned(authorized, _named(name="grant-1"), NAMED)
        assert isinstance(version, str)
        derived = f"{TENANT}/{NAMED.class_id}/grant-1"
        assert registry.resolve(derived, version) == _named(name="grant-1")
        _nothing_registered(registry, definition_key)


# --- §1.3 the ONE tenant comparison ---------------------------------------------


class TestTenantBind:
    @pytest.mark.parametrize("kind", REGISTER_KINDS)
    def test_a_key_whose_tenant_segment_is_not_the_capabilitys_is_refused(
        self, kind: type[ActionKind]
    ) -> None:
        """The gate agreed to ``other-bank/...`` for a principal acting as
        ``acme-bank``: the handle is where that disagreement is caught, once."""
        registry = ControlPlaneRegistry()
        authorized = capability(kind, tenant=TENANT, resource=FOREIGN_KEY)
        with pytest.raises(CrossTenantKeyRefused):
            registry.register(authorized, {"a": 1})
        _nothing_registered(registry, FOREIGN_KEY, KEY)
        assert registry.audit_events() == ()

    def test_a_key_with_no_tenant_segment_is_refused(self) -> None:
        registry = ControlPlaneRegistry()
        with pytest.raises(CrossTenantKeyRefused):
            registry.register(capability(Register, tenant=TENANT, resource="policy"), {"a": 1})
        _nothing_registered(registry, "policy")

    def test_a_derived_registration_refuses_an_artifact_claiming_another_tenant(self) -> None:
        registry = ControlPlaneRegistry()
        authorized = capability(
            SkillGrant, tenant=TENANT, resource=f"{TENANT}/ccf.agent-definition/analyst"
        )
        with pytest.raises(CrossTenantKeyRefused):
            registry.register_versioned(authorized, _named(tenant="other-bank"), NAMED)
        _nothing_registered(registry, f"other-bank/{NAMED.class_id}/grant-1", f"{TENANT}/{NAMED.class_id}/grant-1")

    def test_the_handles_offer_no_key_parameter(self) -> None:
        import inspect

        for method in (
            ControlPlaneRegistry.register,
            ControlPlaneRegistry.register_typed,
            ControlPlaneRegistry.register_versioned,
        ):
            params = inspect.signature(method).parameters
            assert list(params)[:2] == ["self", "authorized"]
            assert "key" not in params
            assert "actor" not in params
            assert params["authorized"].default is inspect.Parameter.empty


# --- wrong kind -------------------------------------------------------------------


class TestWrongKind:
    @pytest.mark.parametrize("wrong", [ArtifactWrite, Execute, HitlSubmit, SkillRevoke])
    def test_a_non_registering_kind_dies_at_verify(self, wrong: type[ActionKind]) -> None:
        registry = ControlPlaneRegistry()
        authorized = cast(Any, capability(wrong, tenant=TENANT, resource=KEY))
        with pytest.raises(CapabilityBypassError, match="kind"):
            registry.register(authorized, {"a": 1})
        with pytest.raises(CapabilityBypassError, match="kind"):
            registry.register_typed(authorized, _named(), NAMED)
        with pytest.raises(CapabilityBypassError, match="kind"):
            registry.register_versioned(authorized, _named(), NAMED)
        _nothing_registered(registry, KEY)
        assert registry.audit_events() == ()

    def test_the_derived_kind_cannot_use_the_door_paths(self) -> None:
        """``SkillGrant`` is admitted by ``register_versioned`` alone — the
        author-versioned path the ledger uses — never by the untyped or typed
        registration a door reaches."""
        registry = ControlPlaneRegistry()
        authorized = capability(SkillGrant, tenant=TENANT, resource=KEY)
        with pytest.raises(CapabilityBypassError, match="kind"):
            registry.register(cast(Any, authorized), {"a": 1})
        with pytest.raises(CapabilityBypassError, match="kind"):
            registry.register_typed(cast(Any, authorized), _named(), NAMED)
        _nothing_registered(registry, KEY)

    def test_the_kind_is_checked_by_identity_not_by_subclass(self) -> None:
        class LooksLikeRegister(Register):
            pass

        registry = ControlPlaneRegistry()
        with pytest.raises(CapabilityBypassError):
            registry.register(
                cast(Any, capability(LooksLikeRegister, tenant=TENANT, resource=KEY)), {"a": 1}
            )
        _nothing_registered(registry, KEY)


# --- the derived path has its own tooth ------------------------------------------------


class TestDerivedPath:
    """``register_versioned`` under ``SkillGrant`` verifies before it derives a
    key. Sabotage S5 (dropping that ``verify_any`` alone) reddened nothing in
    the first pass — the fabrication and retargeting controls above all mint
    door kinds and so travel the door path. These travel the derived one."""

    DEFINITION_KEY = f"{TENANT}/ccf.agent-definition/analyst"
    DERIVED_KEY = f"{TENANT}/{NAMED.class_id}/grant-1"

    @pytest.mark.parametrize(
        "label,fake",
        list(fabrications(SkillGrant, tenant=TENANT, resource=f"{TENANT}/ccf.agent-definition/analyst")),
        ids=lambda v: v if isinstance(v, str) else "",
    )
    def test_a_fabricated_grant_capability_dies_on_the_derived_path(
        self, label: str, fake: object
    ) -> None:
        registry = ControlPlaneRegistry()
        with pytest.raises(CapabilityBypassError):
            registry.register_versioned(cast(Any, fake), _named(name="grant-1"), NAMED)
        _nothing_registered(registry, self.DERIVED_KEY, self.DEFINITION_KEY)
        assert registry.audit_events() == ()

    @pytest.mark.parametrize("field", sorted(RETARGETS))
    def test_a_retargeted_grant_capability_registers_nothing_on_the_derived_path(
        self, field: str
    ) -> None:
        registry = ControlPlaneRegistry()
        cap = capability(SkillGrant, tenant=TENANT, resource=self.DEFINITION_KEY)
        retarget(cap, field, RETARGETS[field])
        with pytest.raises(CapabilityBypassError):
            registry.register_versioned(cap, _named(name="grant-1"), NAMED)
        _nothing_registered(registry, self.DERIVED_KEY, f"other-bank/{NAMED.class_id}/grant-1")

    def test_a_kind_retargeted_to_skill_grant_confers_no_derived_registration(self) -> None:
        registry = ControlPlaneRegistry()
        cap = capability(ArtifactWrite, tenant=TENANT, resource=self.DEFINITION_KEY)
        retarget(cap, "kind", SkillGrant)
        assert getattr(cap, "kind") is SkillGrant  # selects the derived path; the naive check WOULD pass
        with pytest.raises(CapabilityBypassError):
            registry.register_versioned(cast(Any, cap), _named(name="grant-1"), NAMED)
        _nothing_registered(registry, self.DERIVED_KEY)


# --- fabrication ------------------------------------------------------------------


class TestFabrication:
    @pytest.mark.parametrize(
        "label,fake",
        list(fabrications(Register, tenant=TENANT, resource=KEY)),
        ids=lambda v: v if isinstance(v, str) else "",
    )
    def test_every_fabrication_dies_at_verify_on_every_registration_path(
        self, label: str, fake: object
    ) -> None:
        registry = ControlPlaneRegistry()
        with pytest.raises(CapabilityBypassError):
            registry.register(cast(Any, fake), {"a": 1})
        with pytest.raises(CapabilityBypassError):
            registry.register_typed(cast(Any, fake), _named(), NAMED)
        with pytest.raises(CapabilityBypassError):
            registry.register_versioned(cast(Any, fake), _named(), NAMED)
        _nothing_registered(registry, KEY)
        assert registry.audit_events() == ()


# --- retargeting (§1.5g) ------------------------------------------------------------


class TestRetargeting:
    @pytest.mark.parametrize("field", sorted(RETARGETS))
    def test_a_forced_retarget_registers_nothing_under_either_target(self, field: str) -> None:
        registry = ControlPlaneRegistry()
        cap = register_capability(KEY, Register)
        retarget(cap, field, RETARGETS[field])
        with pytest.raises(CapabilityBypassError):
            registry.register(cap, {"a": 1})
        _nothing_registered(registry, KEY, str(RETARGETS["resource"]))

    def test_a_kind_retargeted_to_register_confers_nothing(self) -> None:
        registry = ControlPlaneRegistry()
        cap = capability(ArtifactWrite, tenant=TENANT, resource=KEY)
        retarget(cap, "kind", Register)
        assert getattr(cap, "kind") is Register  # the naive check WOULD pass
        with pytest.raises(CapabilityBypassError):
            registry.register(cast(Any, cap), {"a": 1})
        _nothing_registered(registry, KEY)
