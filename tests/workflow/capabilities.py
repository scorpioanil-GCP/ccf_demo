"""Capabilities for the workflow tests — minted the only way there is (D-IMPL-353 §1.1).

No test here constructs ``Authorized`` and none names the sentinel: every
capability comes from :func:`ccf.authz.capability.mint` over an
*allowed* :class:`~ccf.authz.decision.AuthzDecision`, exactly as the
HTTP gate and the MCP wrapper mint one. What a test chooses is the DECISION —
tenant, action, resource — and that choice is the point of P2: a decision for
tenant B on tenant A's workflow key is a real thing a scope mapping can say,
and the engine must be unable to turn it into state under A.
"""

from __future__ import annotations

from ccf.workflow.factory import Workflow
from ccf.authz.actions import ACTION_WORKFLOW_INVOKE, ACTION_WORKFLOW_RESUME
from ccf.authz.capability import Authorized, Execute, Resume, mint
from ccf.authz.decision import AuthzDecision

__all__ = [
    "PRINCIPAL",
    "decision",
    "execute_as",
    "execute_capability",
    "resume_as",
    "resume_capability",
]

#: The verified client id every workflow-test decision is made for.
PRINCIPAL = "workflow-tests"


def decision(
    *, tenant: str, action: str, resource: str, allowed: bool = True
) -> AuthzDecision:
    """One authorizer verdict, complete enough to mint from."""
    return AuthzDecision(
        allowed=allowed,
        matched_scope_pattern=tenant if allowed else None,
        matched_resource_pattern=resource if allowed else None,
        artifact_version="1.0.0",
        action_id=action,
        tenant=tenant,
        resource=resource,
    )


def execute_capability(
    *, tenant: str, resource: str, decision_id: str = "authz-decision-execute"
) -> Authorized[Execute]:
    """``Authorized[Execute]`` for ``tenant`` on the workflow key ``resource``."""
    return mint(
        Execute,
        decision=decision(
            tenant=tenant, action=ACTION_WORKFLOW_INVOKE, resource=resource
        ),
        principal=PRINCIPAL,
        decision_id=decision_id,
    )


def resume_capability(
    *, tenant: str, resource: str, decision_id: str = "authz-decision-resume"
) -> Authorized[Resume]:
    """``Authorized[Resume]`` for ``tenant`` on the workflow key ``resource``."""
    return mint(
        Resume,
        decision=decision(
            tenant=tenant, action=ACTION_WORKFLOW_RESUME, resource=resource
        ),
        principal=PRINCIPAL,
        decision_id=decision_id,
    )


def execute_as(workflow: Workflow) -> Authorized[Execute]:
    """The ``Execute`` capability a caller acting AS the definition's declared
    tenant holds for this handle's key — what the served path mints for the
    ordinary case. The tests choose to act as that tenant; the engine reads
    the tenant from the capability, never from the handle."""
    return execute_capability(
        tenant=workflow.definition.tenant, resource=workflow.definition_key
    )


def resume_as(workflow: Workflow) -> Authorized[Resume]:
    """The ``Resume`` counterpart of :func:`execute_as`."""
    return resume_capability(
        tenant=workflow.definition.tenant, resource=workflow.definition_key
    )
