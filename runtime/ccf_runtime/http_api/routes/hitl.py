"""The ``hitl`` noun — queue views and actions (D-IMPL-20/23).

The queue view is a read of the typed transport; the action POST travels
the same authority path every HITL action travels
(:class:`~ccf.hitl.transport.HITLTransportProtocol`), which is why an
unattributed action is unrepresentable here: the submission contract
requires a complete :class:`~ccf.hitl.principal.HumanPrincipalBinding` by
type, and an extra or missing field dies at the boundary with 422
(audit-by-construction, CLAUDE.md §8.2).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from fastapi import APIRouter

from ccf.hitl.transport import HitlActionSubmission, PendingHitlEvent
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
        response_model=HitlActionSubmission,
        summary="HITL action (D-IMPL-23)",
    )
    def act(submission: HitlActionSubmission) -> HitlActionSubmission:
        deps.hitl_transport.submit(submission=submission)
        return submission

    return router
