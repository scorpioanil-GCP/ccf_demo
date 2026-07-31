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

**The D-IMPL-67 identity composition.** When ``create_app`` binds an auth
hook, the verified :class:`~ccf_runtime.mcp.auth.TokenGrant` arrives on
``request.state.token_grant`` and the audited submission's subject is
*derived* from it through
:func:`~ccf_runtime.identity_binding.principal_from_token_grant` — a
mechanism with no caller subject parameter, so the subject is what the
deployment verified, never what the caller typed. A body principal whose
``subject_id`` conflicts with the verified identity is a typed 403 refusal
that never touches the transport (D-IMPL-21). When no hook is bound, the
recorded T-07-24 posture is unchanged: the submission travels as sent.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ccf.hitl.transport import (
    HitlActionReceipt,
    HitlActionSubmission,
    PendingHitlEvent,
    SignedBindingInvalidRefused,
    SignedBindingRequiredRefused,
)
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.errors import (
    ERROR_INVALID_GRANT,
    ERROR_SIGNED_BINDING_INVALID,
    ERROR_SIGNED_BINDING_REQUIRED,
    ERROR_SUBJECT_CONFLICT,
    refusal_detail,
)
from ccf_runtime.identity_binding import principal_from_token_grant
from ccf_runtime.mcp.auth import TokenGrant

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
    def act(
        submission: HitlActionSubmission, request: Request
    ) -> HitlActionReceipt:
        grant = getattr(request.state, "token_grant", None)
        if grant is not None and not isinstance(grant, TokenGrant):
            # Fail closed (Codex finding, 07-REVIEWS round 2): an object
            # that is not the verified TokenGrant type never falls
            # through to the caller-supplied principal.
            raise HTTPException(
                status_code=403,
                detail=refusal_detail(
                    error_code=ERROR_INVALID_GRANT,
                    message=(
                        "the stashed grant object is not a TokenGrant;"
                        " the door refuses rather than fall back to the"
                        " caller-supplied principal"
                    ),
                ),
            )
        if isinstance(grant, TokenGrant):
            if submission.principal.approver.subject_id != grant.client_id:
                raise HTTPException(
                    status_code=403,
                    detail=refusal_detail(
                        error_code=ERROR_SUBJECT_CONFLICT,
                        message=(
                            "identity conflict: the submission's principal"
                            " subject does not match the verified caller"
                            " identity; the audited subject is derived from"
                            " the verified grant, never the caller's claim"
                            " (D-IMPL-67; D-IMPL-21)"
                        ),
                    ),
                )
            derived = principal_from_token_grant(
                grant=grant,
                identity_provider_ref=(
                    submission.principal.approver.identity_provider_ref
                ),
                method=submission.principal.authentication.method,
                assurance_level=(
                    submission.principal.authentication.assurance_level
                ),
                session_ref=submission.principal.authentication.session_ref,
                action_time=submission.principal.action_time,
                product_content_hash=(
                    submission.principal.product_content_hash
                ),
            )
            submission = submission.model_copy(update={"principal": derived})
        try:
            deps.hitl_transport.submit(submission=submission)
        except SignedBindingRequiredRefused as error:
            # D-16 door mapping (08-03): the transport's typed refusal
            # surfaces as the shared error-code constant, never prose-only.
            raise HTTPException(
                status_code=403,
                detail=refusal_detail(
                    error_code=ERROR_SIGNED_BINDING_REQUIRED,
                    message=str(error),
                ),
            ) from error
        except SignedBindingInvalidRefused as error:
            raise HTTPException(
                status_code=403,
                detail=refusal_detail(
                    error_code=ERROR_SIGNED_BINDING_INVALID,
                    message=str(error),
                ),
            ) from error
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
