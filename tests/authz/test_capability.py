"""The `Authorized` capability — D-IMPL-353 §1.5, every clause as a test.

Written before the module existed. The claims, each pinned to its clause:

* (a) a mint binds the authorizer's whole allowed decision; a refused decision
  mints nothing;
* (b) the action is the TYPE — `Authorized[ArtifactWrite]` is not
  `Authorized[ArtifactRead]` (the static tooth, measured by mypy in
  `test_capability_static.py`, not here);
* (c) `_verify` checks the mint AND the kind by identity (the runtime tooth);
* (f) the resource is bound — a write capability for X is not a write wand
  for Y;
* (g) the mint is OVER the fields — retargeting a genuine capability, by
  `setattr` or by `object.__setattr__`, dies at use exactly as fabrication does.

Fabrication and retargeting are separate test classes on purpose (Dave,
2026-09-24): a valid sentinel plus a reassigned kind must never confer new
authority, and that is a different failure from a stub sentinel.
"""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import Mock

import pytest

from ccf_runtime.authz.capability import (
    ActionKind,
    AgentDeclare,
    ArtifactRead,
    ArtifactWrite,
    Authorized,
    CapabilityBypassError,
    COMPOSITION_KINDS,
    Execute,
    HitlSubmit,
    Register,
    ReplayMint,
    kind_for_action,
    mint,
    mint_at_composition,
    verify,
)
from ccf_runtime.authz.protocol import AuthzDecision
from ccf_runtime.authz.refusals import (
    ACTION_ARTIFACT_READ,
    ACTION_ARTIFACT_WRITE,
    ACTION_WORKFLOW_INVOKE,
)

TENANT = "acme-bank"
PRINCIPAL = "officer-1"
RESOURCE_X = "ccf.prompt-artifact/underwriting-prompt"
RESOURCE_Y = "ccf.prompt-artifact/some-other-prompt"
DECISION = "authz-decision-0042"


def _decision(*, allowed: bool = True, action: str = ACTION_ARTIFACT_READ,
              resource: str = RESOURCE_X, tenant: str = TENANT) -> AuthzDecision:
    return AuthzDecision(
        allowed=allowed,
        matched_scope_pattern=tenant if allowed else None,
        matched_resource_pattern=resource if allowed else None,
        artifact_version="1.0.0",
        action_id=action,
        tenant=tenant,
        resource=resource,
    )


def _read() -> Authorized[ArtifactRead]:
    return mint(ArtifactRead, decision=_decision(), principal=PRINCIPAL, decision_id=DECISION)


def _write() -> Authorized[ArtifactWrite]:
    return mint(
        ArtifactWrite,
        decision=_decision(action=ACTION_ARTIFACT_WRITE),
        principal=PRINCIPAL,
        decision_id=DECISION,
    )


# --- (a) the mint binds the whole decision ------------------------------------


class TestMint:
    def test_a_genuine_capability_verifies_for_its_own_kind_and_resource(self) -> None:
        cap = _read()
        verify(cap, kind=ArtifactRead, resource=RESOURCE_X)  # no raise
        assert cap.tenant == TENANT
        assert cap.principal == PRINCIPAL
        assert cap.resource == RESOURCE_X
        assert cap.decision_id == DECISION
        assert cap.kind is ArtifactRead

    def test_a_refused_decision_mints_nothing(self) -> None:
        with pytest.raises(CapabilityBypassError, match="allowed"):
            mint(ArtifactRead, decision=_decision(allowed=False), principal=PRINCIPAL, decision_id=DECISION)

    def test_the_kind_must_agree_with_the_decisions_action(self) -> None:
        """A decision for artifact.read cannot be minted as ArtifactWrite —
        the kind is not chosen by the caller of mint(); it is the decision's."""
        with pytest.raises(CapabilityBypassError, match="action"):
            mint(ArtifactWrite, decision=_decision(action=ACTION_ARTIFACT_READ), principal=PRINCIPAL, decision_id=DECISION)

    def test_every_door_declared_action_has_a_kind_and_replay_mint_has_no_action(self) -> None:
        assert kind_for_action(ACTION_ARTIFACT_READ) is ArtifactRead
        assert kind_for_action(ACTION_ARTIFACT_WRITE) is ArtifactWrite
        assert kind_for_action(ACTION_WORKFLOW_INVOKE) is Execute
        # §2 P3: no door declares an action that mints ReplayMint.
        assert ReplayMint.action_id not in {
            k.action_id for k in (ArtifactRead, ArtifactWrite, Execute, HitlSubmit, Register)
        }
        with pytest.raises(CapabilityBypassError, match="no door"):
            kind_for_action(ReplayMint.action_id)


# --- (c) the runtime tooth: kind by identity ----------------------------------


class TestWrongKind:
    @pytest.mark.parametrize("wrong", [ArtifactWrite, Execute, HitlSubmit, Register, ReplayMint])
    def test_a_read_capability_is_refused_by_every_other_kind(self, wrong: type) -> None:
        cap = _read()
        with pytest.raises(CapabilityBypassError, match="kind"):
            verify(cap, kind=wrong, resource=RESOURCE_X)

    def test_kind_is_checked_by_identity_not_subclass(self) -> None:
        class LooksLikeRead(ArtifactRead):
            pass

        cap = _read()
        with pytest.raises(CapabilityBypassError, match="kind"):
            verify(cap, kind=LooksLikeRead, resource=RESOURCE_X)


# --- (f) the resource is bound -------------------------------------------------


class TestWrongResource:
    def test_a_write_capability_for_x_is_not_a_write_wand_for_y(self) -> None:
        cap = _write()
        verify(cap, kind=ArtifactWrite, resource=RESOURCE_X)  # its own target: fine
        with pytest.raises(CapabilityBypassError, match="resource"):
            verify(cap, kind=ArtifactWrite, resource=RESOURCE_Y)


# --- fabrication: dies at use --------------------------------------------------


class TestFabrication:
    def test_the_sentinel_is_not_constructible_from_outside(self) -> None:
        with pytest.raises(CapabilityBypassError):
            Authorized(object(), kind=ArtifactRead, tenant=TENANT, principal=PRINCIPAL, resource=RESOURCE_X, decision_id=DECISION)

    def test_a_mock_dies_at_use(self) -> None:
        fake = Mock()
        fake.kind = ArtifactRead
        fake.tenant, fake.principal, fake.resource, fake.decision_id = TENANT, PRINCIPAL, RESOURCE_X, DECISION
        with pytest.raises(CapabilityBypassError):
            verify(fake, kind=ArtifactRead, resource=RESOURCE_X)

    def test_a_bare_object_dies_at_use(self) -> None:
        with pytest.raises(CapabilityBypassError):
            verify(object(), kind=ArtifactRead, resource=RESOURCE_X)

    def test_a_forged_mint_tuple_with_a_stub_sentinel_dies_at_use(self) -> None:
        """§9's 'mint from a stub sentinel' — the control the first sabotage
        pass proved MISSING. Dropping the sentinel identity check and
        accepting any 6-tuple left all 26 controls green, because none of them
        built an object with the RIGHT tuple shape and the WRONG sentinel. A
        forger who learns the shape does exactly this."""
        forged = Authorized.__new__(Authorized)
        stub_sentinel = object()
        object.__setattr__(forged, "kind", ArtifactWrite)
        object.__setattr__(forged, "tenant", TENANT)
        object.__setattr__(forged, "principal", PRINCIPAL)
        object.__setattr__(forged, "resource", RESOURCE_X)
        object.__setattr__(forged, "decision_id", DECISION)
        object.__setattr__(
            forged,
            "_minted",
            (stub_sentinel, ArtifactWrite, TENANT, PRINCIPAL, RESOURCE_X, DECISION),
        )
        # Every field agrees with its mint tuple; only the sentinel is wrong.
        with pytest.raises(CapabilityBypassError, match="genuine"):
            verify(forged, kind=ArtifactWrite, resource=RESOURCE_X)

    def test_a_subclass_skipping_init_dies_at_use(self) -> None:
        cap = Authorized.__new__(Authorized)
        with pytest.raises(CapabilityBypassError):
            verify(cap, kind=ArtifactRead, resource=RESOURCE_X)


# --- (g) retargeting: separate from fabrication, every field, both routes -----


class TestRetargeting:
    FIELDS = ("kind", "tenant", "principal", "resource", "decision_id")
    RETARGET = {
        "kind": ArtifactWrite,
        "tenant": "other-bank",
        "principal": "impostor",
        "resource": RESOURCE_Y,
        "decision_id": "authz-decision-9999",
    }

    @pytest.mark.parametrize("field", FIELDS)
    def test_plain_assignment_is_refused_after_mint(self, field: str) -> None:
        cap = _read()
        with pytest.raises((CapabilityBypassError, AttributeError)):
            setattr(cap, field, self.RETARGET[field])
        verify(cap, kind=ArtifactRead, resource=RESOURCE_X)  # untouched, still good

    @pytest.mark.parametrize("field", FIELDS)
    def test_a_forced_retarget_makes_the_capability_unusable_for_anything(self, field: str) -> None:
        """object.__setattr__ bypasses the assignment guard. The mint tuple is
        what makes the result die: the current field no longer matches what
        was minted, so it is unusable for the NEW authority AND for the OLD."""
        cap = _read()
        object.__setattr__(cap, field, self.RETARGET[field])
        # Not usable as what it was retargeted to:
        if field == "kind":
            with pytest.raises(CapabilityBypassError):
                verify(cap, kind=ArtifactWrite, resource=RESOURCE_X)
        if field == "resource":
            with pytest.raises(CapabilityBypassError):
                verify(cap, kind=ArtifactRead, resource=RESOURCE_Y)
        # And not usable as what it was:
        with pytest.raises(CapabilityBypassError):
            verify(cap, kind=ArtifactRead, resource=RESOURCE_X)

    def test_a_reassigned_kind_with_a_valid_sentinel_confers_no_new_authority(self) -> None:
        """ChatGPT's exact case: valid sentinel + kind reassigned to the
        legitimate ArtifactWrite identity. Both naive checks would pass."""
        cap = _read()
        object.__setattr__(cap, "kind", ArtifactWrite)
        # `cast(object, ...)`: mypy correctly proves `cap.kind is ArtifactWrite`
        # unreachable for an Authorized[ArtifactRead] — that IS the static
        # tooth. This is the RUNTIME half, deliberately doing what the types
        # forbid, so the assertion is made through `object` (§9: the runtime
        # controls are the quarantined, cast-based ones).
        retargeted = cast(object, cap)
        assert getattr(retargeted, "kind") is ArtifactWrite  # the naive check WOULD pass
        with pytest.raises(CapabilityBypassError):
            verify(retargeted, kind=ArtifactWrite, resource=RESOURCE_X)


# --- D-IMPL-354 (PROPOSED): the composition kinds, and nothing else ---------


class TestMintAtComposition:
    def test_replay_mint_at_composition_verifies_for_its_evidence_class(self) -> None:
        cap = mint_at_composition(
            ReplayMint, tenant=TENANT, principal=PRINCIPAL, resource="ccf.decision-replay", decision_id=DECISION
        )
        verify(cap, kind=ReplayMint, resource="ccf.decision-replay")  # no raise
        assert cap.kind is ReplayMint and cap.tenant == TENANT

    def test_register_at_composition_is_bound_to_one_key(self) -> None:
        cap = mint_at_composition(
            Register, tenant=TENANT, principal=PRINCIPAL, resource=f"{TENANT}/policy/bundle", decision_id=DECISION
        )
        verify(cap, kind=Register, resource=f"{TENANT}/policy/bundle")  # no raise
        with pytest.raises(CapabilityBypassError):
            verify(cap, kind=Register, resource=f"{TENANT}/policy/other")
        # and it is Register, not any other registration kind
        with pytest.raises(CapabilityBypassError):
            verify(cap, kind=AgentDeclare, resource=f"{TENANT}/policy/bundle")

    @pytest.mark.parametrize("door_kind", [ArtifactWrite, HitlSubmit, Execute, AgentDeclare, ArtifactRead])
    def test_a_door_kind_cannot_be_minted_at_composition(self, door_kind: Any) -> None:
        # `Any` on purpose: the static tooth for this is the committed control
        # in static_controls/composition_kind.py; this is the runtime tooth.
        with pytest.raises(CapabilityBypassError, match="composition kind"):
            mint_at_composition(
                door_kind, tenant=TENANT, principal=PRINCIPAL, resource="x", decision_id=DECISION
            )

    def test_the_composition_kinds_are_exactly_two(self) -> None:
        assert COMPOSITION_KINDS == (ReplayMint, Register)
