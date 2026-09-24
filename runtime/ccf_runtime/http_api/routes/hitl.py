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

**The D-IMPL-67 identity composition.** The verified
:class:`~ccf_runtime.mcp.auth.TokenGrant` arrives on
``request.state.token_grant`` and the audited submission's subject is
*derived* from it through
:func:`~ccf_runtime.identity_binding.principal_from_token_grant` — a
mechanism with no caller subject parameter, so the subject is what the
deployment verified, never what the caller typed. A body principal whose
``subject_id`` conflicts with the verified identity is a typed 403 refusal
that never touches the transport (D-IMPL-21).

**The tenant is the grant's, on both routes (``SEC-002``).**

* ``GET /queue`` had a ``tenant`` query parameter, which made *whose queue*
  a thing the caller typed. It is **deleted**: the tenant comes from
  :func:`~ccf_runtime.http_api.grants.tenant_from_request` and reading
  another tenant's queue is now unrepresentable rather than refused.
* ``POST /actions`` carries ``HitlActionSubmission.tenant``, which lives in
  ``src/ccf/hitl/`` and is not this module's to delete. So it is handled the
  way this file already handles the caller's *subject* claim: a value that
  disagrees with the verified grant is a typed 403 that never reaches the
  transport, and the value that travels onward is **derived** from the grant.
  The field being deleted at its own contract is recorded as owed work, not
  worked around here — a door that quietly rewrote a caller's tenant would be
  answering a question nobody asked.

**Tenant authorization is no longer asked here, and that is the change**
(``SEC-001``). Both routes used to call the bound authorizer inside their own
handlers, which meant the enforcement existed exactly where someone had
remembered to write it — two routes out of twenty-six. It now happens once,
for every route, in :class:`~ccf_runtime.http_api.gate.AuthorizationGate`,
before routing and before body validation. Nothing about these two routes'
posture is weaker for it: the gate asks the same authorizer with the same
door-declared action ids, which are now declared beside the handlers instead
of passed into the enforcement helper.

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
from ccf_runtime.authz.refusals import (
    ACTION_HITL_ACTION_SUBMIT,
    ACTION_HITL_QUEUE_READ,
)
from ccf_runtime.authz.route_declaration import ResourceBinding, authorizes
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.errors import (
    ERROR_SIGNED_BINDING_INVALID,
    ERROR_SIGNED_BINDING_REQUIRED,
    ERROR_SUBJECT_CONFLICT,
    ERROR_TENANT_UNAUTHORIZED,
    refusal_detail,
)
from ccf_runtime.http_api.grants import grant_from_request, tenant_from_request
from ccf_runtime.http_api.routes import _required_handle
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
    # The resource is the door itself: a queue read names no subject beyond
    # the tenant, and the tenant is the grant's rather than an axis a
    # deployment states patterns over.
    @authorizes(ACTION_HITL_QUEUE_READ, resource=ResourceBinding.route())
    def queue(request: Request) -> list[PendingHitlEvent]:
        # Narrowed once per body (D-IMPL-126 item (3)): a deployment that
        # routes no HITL traffic here wired no transport, which is a fault of
        # the deployment rather than of the caller — telling the caller they
        # are forbidden would misattribute it.
        transport = _required_handle(
            deps.hitl_transport,
            field="hitl_transport",
            routes="HITL queue view or action submission",
        )
        return list(transport.pending(tenant=tenant_from_request(request)))

    @router.post(
        "/actions",
        response_model=HitlActionReceipt,
        summary="HITL action submission — submit-only (D-IMPL-23/62)",
    )
    @authorizes(
        ACTION_HITL_ACTION_SUBMIT,
        resource=ResourceBinding.body("event_key"),
    )
    def act(
        submission: HitlActionSubmission, request: Request
    ) -> HitlActionReceipt:
        # One narrowing for this whole body — the three reads below share it
        # (D-IMPL-126 item (3)).
        transport = _required_handle(
            deps.hitl_transport,
            field="hitl_transport",
            routes="HITL queue view or action submission",
        )
        tenant = tenant_from_request(request)
        if submission.tenant != tenant:
            # `SEC-002`, in the shape this file already used for the subject
            # claim one block down: refuse the conflict rather than rewrite
            # it. A caller who names another tenant is told so; a caller who
            # names its own is not surprised by a value it did not send.
            raise HTTPException(
                status_code=403,
                detail=refusal_detail(
                    error_code=ERROR_TENANT_UNAUTHORIZED,
                    message=(
                        "the submission names a tenant other than the one the"
                        " verified grant acts for; the tenant is the grant's"
                        " and a door never takes it from the body (SEC-002)"
                    ),
                ),
            )
        grant = grant_from_request(request)
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
            # The tenant is set from the verified grant as well as checked
            # against it. The check above makes the two agree already, so this
            # rewrites nothing a caller would notice; what it buys is that the
            # value reaching the transport has ONE source even if the check
            # above is ever weakened, which is the property a later reader
            # needs and cannot get from a comparison alone.
            submission = submission.model_copy(
                update={"principal": derived, "tenant": tenant}
            )
        try:
            transport.submit(submission=submission)
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
        pending = transport.pending(tenant=submission.tenant)
        recorded = transport.submissions(tenant=submission.tenant)
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
