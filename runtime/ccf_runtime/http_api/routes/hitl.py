"""The ``hitl`` noun — queue views and submit-only actions (D-IMPL-20/23/62; D-IMPL-353 §2 P6).

The queue view is a read of the typed transport; the action POST travels
the same authority path every HITL action travels
(:class:`~ccf.hitl.transport.HITLTransportProtocol`). Both are handles that
**require the capability for their own action** (D-IMPL-353 §1.2):
``transport.view`` takes the ``Authorized[HitlQueueRead]`` and
``transport.submit`` the ``Authorized[HitlSubmit]`` the gate minted for this
request, and a handler holding neither has nothing to pass — the call does
not type-check (§1.4).

**The door mints the binding; the caller does not describe it (§2 P6).**
``POST /actions`` used to take a complete
:class:`~ccf.hitl.principal.HumanPrincipalBinding` in the body, compare its
subject with the verified identity, and pass everything else — identity
provider, method, **assurance level**, session, action time — through to
the audit record verbatim. That made step-up MFA a thing the approver typed.
The body is now :class:`~ccf.hitl.transport.HitlActionRequest` — event key,
action, the content hash of what the human saw, an optional annotation, an
optional ``attestation`` (`D-IMPL-363`), and nothing else (``extra=forbid``: a body that
still sends ``assurance_level`` is a 422). The binding is minted here by
:func:`~ccf_runtime.identity_binding.principal_from_authorized` from:

* ``authorized.principal`` — the subject;
* the verified grant's :class:`~ccf.hitl.principal.AuthenticationClaims` —
  identity provider, method, assurance level, session, verbatim
  (:func:`~ccf_runtime.identity_binding.authentication_of_grant`); a grant
  that states none is refused with ``ERROR_AUTHENTICATION_UNATTESTED``;
* ``deps.clock()`` — the deployment's injected clock; never the body, never
  a wall clock read in this handler.

So there is no subject to conflict, no tenant to compare
(``HitlActionSubmission`` has no tenant field — §1.3; the transport files
under ``authorized.tenant``), and no assurance level to trust. The
``ERROR_SUBJECT_CONFLICT`` and ``SEC-002`` tenant refusals this module used
to raise are gone because the things they refused are unrepresentable.

**The action door is submit-only by ruling (D-IMPL-62):** the POST enqueues
the submission on the typed transport and effects no state transition and
no authority action by itself — the owning primitive resolves it. The
response is the :class:`~ccf.hitl.transport.HitlActionReceipt`, whose
``status`` is type-closed to ``"submitted"``, whose ``submission`` is the
**recorded** copy the transport returned (stamps included), and whose
disposition fields carry real queue state.

**Tenant authorization is asked once, for every route, in
:class:`~ccf_runtime.http_api.gate.AuthorizationGate`** (``SEC-001``), which
mints the capability these handlers read back. Nothing here decides.

Algorithmic module (CINV-03).
"""

from __future__ import annotations


from fastapi import APIRouter, HTTPException, Request

from ccf.authz.capability import (
    Authorized,
    HitlQueueRead,
    HitlSubmit,
)
from ccf.hitl.transport import (
    ApproverNotEligible,
    HitlActionReceipt,
    HitlActionRequest,
    HitlActionSubmission,
    HitlEventRevalidationRefused,
    HitlGateClosed,
    PendingHitlEvent,
    SignedBindingInvalidRefused,
    SignedBindingMismatchRefused,
    SignedBindingRequiredRefused,
    SignedBindingStaleRefused,
)
from ccf_runtime.authz.route_declaration import ResourceBinding, authorizes
from ccf_runtime.http_api.dependencies import ApiDependencies
from ccf_runtime.http_api.errors import (
    ERROR_APPROVER_NOT_ELIGIBLE,
    ERROR_HITL_EVENT_REVALIDATION_REFUSED,
    ERROR_HITL_GATE_CLOSED,
    ERROR_SIGNED_BINDING_INVALID,
    ERROR_SIGNED_BINDING_MISMATCH,
    ERROR_SIGNED_BINDING_REQUIRED,
    ERROR_SIGNED_BINDING_STALE,
    refusal_detail,
)
from ccf_runtime.http_api.grants import authorized_from_request, grant_from_request
from ccf_runtime.http_api.routes import _required_handle
from ccf_runtime.identity_binding import (
    ERROR_AUTHENTICATION_UNATTESTED,
    AuthenticationUnattested,
    attested_authentication,
    authentication_of_grant,
    principal_from_authorized,
)

__ccf_mode__ = "algorithmic"

__all__ = ["build_router"]


def build_router(deps: ApiDependencies) -> APIRouter:
    """The hitl router over the injected typed transport and clock."""
    router = APIRouter()

    @router.get(
        "/queue",
        response_model=list[PendingHitlEvent],
        summary="HITL queue view (D-IMPL-23)",
    )
    # The resource is the door itself: a queue read names no subject beyond
    # the tenant, and the tenant is the capability's rather than an axis a
    # deployment states patterns over. The declared action id and the kind
    # the handler asks for are the same symbol, so they cannot drift.
    @authorizes(HitlQueueRead.action_id, resource=ResourceBinding.route())
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
        authorized = authorized_from_request(request, kind=HitlQueueRead)
        return list(transport.view(authorized))

    @router.post(
        "/actions",
        response_model=HitlActionReceipt,
        summary="HITL action submission — submit-only (D-IMPL-23/62)",
    )
    @authorizes(
        HitlSubmit.action_id,
        resource=ResourceBinding.body("event_key"),
    )
    def act(body: HitlActionRequest, request: Request) -> HitlActionReceipt:
        transport = _required_handle(
            deps.hitl_transport,
            field="hitl_transport",
            routes="HITL queue view or action submission",
        )
        # The clock is a handle like the transport: the action time on an
        # approval is the deployment's injected clock reading, and a
        # deployment that routes no HITL traffic here wired none.
        clock = _required_handle(
            deps.clock, field="clock", routes="HITL action submission"
        )
        authorized = authorized_from_request(request, kind=HitlSubmit)
        grant = grant_from_request(request)
        try:
            authentication = attested_authentication(
                None if grant is None else authentication_of_grant(grant)
            )
        except AuthenticationUnattested as error:
            raise HTTPException(
                status_code=403,
                detail=refusal_detail(
                    error_code=ERROR_AUTHENTICATION_UNATTESTED,
                    message=str(error),
                ),
            ) from error
        submission = HitlActionSubmission(
            event_key=body.event_key,
            action=body.action,
            # Minted, not received: subject from the capability, claims from
            # the verified grant, time from the injected clock (§2 P6).
            principal=principal_from_authorized(
                authorized,
                authentication=authentication,
                action_time=clock(),
                product_content_hash=body.product_content_hash,
                # SEC-005: the verdict is bound INTO the signed claims, from
                # the same request field the submission carries, so a
                # signature cannot later authorize a different decision.
                action=body.action,
            ),
            annotation=body.annotation,
            attestation=body.attestation,
        )
        try:
            recorded = transport.submit(authorized, submission=submission)
        except ApproverNotEligible as error:
            # SEC-006 (D-IMPL-366 G3 (a)): a distinct 403 code; the message is
            # the transport's non-enumerating one, so the wire names no
            # eligible principal.
            raise HTTPException(
                status_code=403,
                detail=refusal_detail(
                    error_code=ERROR_APPROVER_NOT_ELIGIBLE,
                    message=str(error),
                ),
            ) from error
        except HitlEventRevalidationRefused as error:
            raise HTTPException(
                status_code=409,
                detail=refusal_detail(
                    error_code=ERROR_HITL_EVENT_REVALIDATION_REFUSED,
                    message=str(error),
                ),
            ) from error
        except HitlGateClosed as error:
            # D-IMPL-378: the gate this verdict names was already decided; the
            # verdict is refused, nothing is recorded, and the 409 says so.
            raise HTTPException(
                status_code=409,
                detail=refusal_detail(
                    error_code=ERROR_HITL_GATE_CLOSED,
                    message=str(error),
                ),
            ) from error
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
        except SignedBindingMismatchRefused as error:
            # `D-IMPL-363` E6: a verified attestation whose signed claims
            # disagree with the capability, the request or the minted binding.
            raise HTTPException(
                status_code=403,
                detail=refusal_detail(
                    error_code=ERROR_SIGNED_BINDING_MISMATCH,
                    message=str(error),
                ),
            ) from error
        except SignedBindingStaleRefused as error:
            # `D-IMPL-363` E3 / E4: outside the window, or a reused nonce.
            raise HTTPException(
                status_code=403,
                detail=refusal_detail(
                    error_code=ERROR_SIGNED_BINDING_STALE,
                    message=str(error),
                ),
            ) from error
        # Disposition from the capability's tenant — the one the record was
        # filed under — never from anything the caller sent.
        tenant = authorized.tenant
        pending = transport.pending(tenant=tenant)
        recorded_all = transport.submissions(tenant=tenant)
        return HitlActionReceipt(
            status="submitted",
            submission=recorded,
            event_pending=any(
                event.event_key == recorded.event_key for event in pending
            ),
            submissions_for_event=sum(
                1 for item in recorded_all if item.event_key == recorded.event_key
            ),
        )

    return router
