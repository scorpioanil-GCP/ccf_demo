"""The ``hitl`` noun — queue views and submit-only actions (D-IMPL-20/23/62).

The queue view is a read of the typed transport; the action POST travels
the same authority path every HITL action travels
(:class:`~ccf.hitl.transport.HITLTransportProtocol`), which is why an
unattributed action is unrepresentable here: the submission contract
requires a complete :class:`~ccf.hitl.principal.HumanPrincipalBinding` by
type, and an extra or missing field dies at the boundary with 422
(audit-by-construction, CLAUDE.md §8.2).

**The action door is submit-only by ruling (D-IMPL-62):** the POST
enqueues the submission on the typed transport and effects no state
transition and no authority action by itself — the owning primitive
resolves it (the MCP channel is D-IMPL-20's primary authority channel).
The response is the :class:`~ccf.hitl.transport.HitlActionReceipt`, whose
``status`` is type-closed to ``"submitted"`` and whose disposition fields
carry real queue state.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from fastapi import APIRouter

from ccf.hitl.transport import (
    HitlActionReceipt,
    HitlActionSubmission,
    PendingHitlEvent,
)
from ccf_runtime.http_api.dependencies import ApiDependencies

__ccf_mode__ = "algorithmic"

__all__ = ["build_router"]


def build_router(deps: ApiDependencies) -> APIRouter:
    """The hitl router over the injected typed transport."""
    router = APIRouter()

    @router.get(
        "/queue",
        response_model=list[PendingHitlEvent],
        summary="HITL queue view (D-IMPL-23)",
    )
    def queue(tenant: str) -> list[PendingHitlEvent]:
        return list(deps.hitl_transport.pending(tenant=tenant))

    @router.post(
        "/actions",
        response_model=HitlActionReceipt,
        summary="HITL action submission — submit-only (D-IMPL-23/62)",
    )
    def act(submission: HitlActionSubmission) -> HitlActionReceipt:
        deps.hitl_transport.submit(submission=submission)
        pending = deps.hitl_transport.pending(tenant=submission.tenant)
        recorded = deps.hitl_transport.submissions(tenant=submission.tenant)
        return HitlActionReceipt(
            status="submitted",
            submission=submission,
            event_pending=any(
                event.event_key == submission.event_key for event in pending
            ),
            submissions_for_event=sum(
                1
                for item in recorded
                if item.event_key == submission.event_key
            ),
        )

    return router
