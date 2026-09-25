"""Genuine HITL capabilities for tests — minted, never fabricated (D-IMPL-353).

The one way a test obtains an ``Authorized[HitlSubmit]`` or an
``Authorized[HitlQueueRead]``: through :func:`ccf.authz.capability.mint`
from an *allowed* :class:`~ccf.authz.decision.AuthzDecision` for
exactly the ``(tenant, principal, action, resource)`` the test is about. A
test that built the object any other way would be testing a fabrication —
which :func:`~ccf.authz.capability.verify` refuses on purpose — and a
helper that defaulted any of the four axes would be minting ambient authority.

Test vocabulary only where a caller does not say otherwise: the decision id
below names no real audit event.
"""

from __future__ import annotations

from ccf.authz.capability import (
    Authorized,
    HitlQueueRead,
    HitlSubmit,
    mint,
)
from ccf.authz.decision import AuthzDecision

__all__ = ["queue_read_capability", "submit_capability"]

#: The audit event these test capabilities claim to be evidence of.
TEST_DECISION_ID = "authz-decision-hitl-test"


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


def submit_capability(
    *,
    tenant: str,
    principal: str,
    event_key: str,
    decision_id: str = TEST_DECISION_ID,
) -> Authorized[HitlSubmit]:
    """A genuine ``Authorized[HitlSubmit]`` for ``event_key`` under ``tenant``."""
    return mint(
        HitlSubmit,
        decision=_allowed(
            action_id=HitlSubmit.action_id, tenant=tenant, resource=event_key
        ),
        principal=principal,
        decision_id=decision_id,
    )


def queue_read_capability(
    *,
    tenant: str,
    principal: str,
    resource: str = HitlQueueRead.action_id,
    decision_id: str = TEST_DECISION_ID,
) -> Authorized[HitlQueueRead]:
    """A genuine ``Authorized[HitlQueueRead]`` for ``tenant``'s queue.

    The resource defaults to the action id because a queue read acts on no
    subject beyond the tenant (``ResourceBinding.route()`` semantics at the
    HTTP door); a test that wants the wrong-resource control passes another.
    """
    return mint(
        HitlQueueRead,
        decision=_allowed(
            action_id=HitlQueueRead.action_id, tenant=tenant, resource=resource
        ),
        principal=principal,
        decision_id=decision_id,
    )
