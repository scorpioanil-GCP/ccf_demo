"""Shared harness for the SEC-006 approver-eligibility controls (`D-IMPL-366`).

RED-FIRST discipline, the `D-IMPL-363` shape: every ruled-but-absent surface is
reached INSIDE a test body and reported there, so a red is either a
**MISSING CONTRACT** (a ruled name or field the tree does not have yet — the
message names it and the ruling) or a **BEHAVIORAL** failure (the tree admits
what the ruling says it must refuse, or refuses what it must admit). Nothing
fails at import, collection or fixture setup.

Test vocabulary only (CINV-01): the subjects, keys and tenants here name no
real principal.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest

from ccf.authz.actions import ACTION_WORKFLOW_INVOKE, ACTION_WORKFLOW_RESUME
from ccf.authz.capability import Authorized, Execute, Resume, mint
from ccf.authz.decision import AuthzDecision
from ccf.controlplane.artifacts import declared_artifact_class, parse_artifact
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.hitl.principal import (
    ApproverIdentity,
    AuthenticationContext,
    HumanPrincipalBinding,
)
from ccf.hitl.transport import (
    HITL_POLICY,
    HitlActionSubmission,
    InMemoryHitlTransport,
    PendingHitlEvent,
)
from tests.composition import register_typed_at_composition
from tests.hitl.capabilities import submit_capability

__all__ = [
    "APPROVAL_POLICY_CLASS_ID",
    "ELIGIBILITY_CODE",
    "REFUSAL_TYPE",
    "RemoveSpy",
    "contract",
    "door_submission",
    "execute_as_principal",
    "expect_eligibility_refusal",
    "field",
    "plain_hitl_plane",
    "register_declared_policy",
    "register_typed_policy",
    "resume_as_principal",
    "submit_as",
    "transport_state",
]

APPROVAL_POLICY_CLASS_ID = "ccf.approval-policy"
ELIGIBILITY_CODE = "approver-not-eligible"
REFUSAL_TYPE = "ApproverNotEligible"
_MISSING = object()
_ACTION_TIME = datetime(2026, 7, 30, 9, 15, tzinfo=UTC)


def contract(module: str, name: str, *, ruling: str) -> Any:
    """The ruled name, or a MISSING CONTRACT failure that names it."""
    try:
        return getattr(importlib.import_module(module), name)
    except (ImportError, AttributeError):
        pytest.fail(
            f"MISSING CONTRACT: {module}.{name} ({ruling}) does not exist on this tree"
        )


def field(subject: Any, name: str, *, ruling: str) -> Any:
    """The ruled field's value, or a MISSING CONTRACT failure that names it."""
    value = getattr(subject, name, _MISSING)
    if value is _MISSING:
        pytest.fail(
            f"MISSING CONTRACT: {type(subject).__name__}.{name} ({ruling}) does not"
            " exist on this tree"
        )
    return value


def _pinned_uri(key: str) -> str:
    tenant, artifact_class, name = key.split("/")
    return f"ccf-artifact://{tenant}/{artifact_class}/{name}@1.0.0"


def register_declared_policy(
    plane: ControlPlaneRegistry, key: str, *, approver_role: str = "sec006-officer"
) -> str:
    """The PRE-change shape every fixture registers today: an UNTYPED
    ``DeclaredArtifact`` whose ``approver_role`` and ``quorum`` no code reads.
    Returns the pinned URI an event or a ``gate_policies`` entry names."""
    artifact_class = declared_artifact_class("approval-policy")
    declared = parse_artifact(
        {
            "class_id": "approval-policy",
            "semver": "1.0.0",
            "declaration": {"approver_role": approver_role, "quorum": "1"},
        },
        artifact_class,
    )
    register_typed_at_composition(plane, key, declared, artifact_class)
    return _pinned_uri(key)


def register_typed_policy(
    plane: ControlPlaneRegistry, key: str, *, eligible: frozenset[str]
) -> str:
    """The RULED shape (`D-IMPL-366` §4 (1), F1/F2/F3): a typed
    ``ccf.approval-policy`` with ``eligible_principals``, adopter-registered
    against its real contract. Returns the pinned URI."""
    approval_policy_class = contract(
        "ccf.hitl", "APPROVAL_POLICY", ruling="D-IMPL-366 §4 (1), SPEC F1"
    )
    policy = parse_artifact(
        {"semver": "1.0.0", "eligible_principals": sorted(eligible)},
        approval_policy_class,
    )
    register_typed_at_composition(plane, key, policy, approval_policy_class)
    return _pinned_uri(key)


def plain_hitl_plane(
    plane: ControlPlaneRegistry, *, key: str = "acme-bank/hitl/sec006-plain-policy"
) -> str:
    """A bound Control Plane whose HITL policy requires no signature — so the
    only new judgment on the served path is eligibility. Returns the key."""
    policy = parse_artifact(
        {"semver": "1.0.0", "signed_binding_required": False}, HITL_POLICY
    )
    register_typed_at_composition(plane, key, policy, HITL_POLICY)
    return key


def door_submission(
    event: PendingHitlEvent, *, subject_id: str, action: str = "approve"
) -> HitlActionSubmission:
    """A submit-only (door-shaped) submission: no primitive, no claim."""
    return HitlActionSubmission(
        event_key=event.event_key,
        action=action,
        principal=HumanPrincipalBinding(
            verdict=action,
            approver=ApproverIdentity(
                subject_id=subject_id, identity_provider_ref="acme-bank/idp/okta"
            ),
            authentication=AuthenticationContext(
                method="oidc", assurance_level="aal2", session_ref=f"session-{subject_id}"
            ),
            action_time=_ACTION_TIME,
            product_content_hash=event.product_content_hash,
        ),
    )


def submit_as(
    transport: InMemoryHitlTransport,
    event: PendingHitlEvent,
    *,
    subject_id: str,
    action: str = "approve",
) -> HitlActionSubmission:
    return transport.submit(
        submit_capability(
            tenant=event.tenant, principal=subject_id, event_key=event.event_key
        ),
        submission=door_submission(event, subject_id=subject_id, action=action),
    )


def expect_eligibility_refusal(call: Callable[[], Any], *, site: str) -> BaseException:
    """Run ``call``; it must refuse with the ruled typed refusal (G3 (a))."""
    try:
        outcome = call()
    except PermissionError as error:
        if type(error).__name__ != REFUSAL_TYPE:
            pytest.fail(
                f"{site}: refused, but by {type(error).__name__} rather than"
                f" {REFUSAL_TYPE} (D-IMPL-366 G3 (a)): {error}"
            )
        return error
    pytest.fail(
        f"BEHAVIORAL: {site} ADMITTED a submission that approver eligibility must"
        f" refuse (D-IMPL-366); outcome: {outcome!r}"[:600]
    )


class RemoveSpy(InMemoryHitlTransport):
    """The real reference transport, recording every ``remove`` (the atomic
    claim) so a primitive-site control can prove the claim was never taken."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.remove_calls: list[tuple[str, str]] = []

    def remove(self, *, tenant: str, event_key: str) -> PendingHitlEvent | None:
        self.remove_calls.append((tenant, event_key))
        return super().remove(tenant=tenant, event_key=event_key)


def transport_state(transport: InMemoryHitlTransport) -> dict[str, Any]:
    """The reference transport's whole mutable state, as comparable values.

    Read through the transport's own members — the subject of the no-mutation
    invariant (`D-IMPL-366`: a refused submission introduces no state
    mutations) is exactly this state, so the control reads it directly.
    """
    return {
        "pending": {t: tuple(q) for t, q in transport._pending.items()},
        "submissions": {t: tuple(s) for t, s in transport._submissions.items()},
        "claims": dict(transport._claims),
        "nonces": frozenset(transport._seen_nonces),
    }


def _allowed(*, action_id: str, tenant: str, resource: str) -> AuthzDecision:
    return AuthzDecision(
        allowed=True,
        matched_scope_pattern=tenant,
        matched_resource_pattern=resource,
        artifact_version="1.0.0",
        action_id=action_id,
        tenant=tenant,
        resource=resource,
    )


def execute_as_principal(
    *, tenant: str, resource: str, principal: str
) -> Authorized[Execute]:
    """A genuine ``Execute`` capability for a NAMED principal — the starter."""
    return mint(
        Execute,
        decision=_allowed(action_id=ACTION_WORKFLOW_INVOKE, tenant=tenant, resource=resource),
        principal=principal,
        decision_id=f"authz-decision-execute-{principal}",
    )


def resume_as_principal(
    *, tenant: str, resource: str, principal: str
) -> Authorized[Resume]:
    """A genuine ``Resume`` capability for a NAMED principal — the resumer."""
    return mint(
        Resume,
        decision=_allowed(action_id=ACTION_WORKFLOW_RESUME, tenant=tenant, resource=resource),
        principal=principal,
        decision_id=f"authz-decision-resume-{principal}",
    )
