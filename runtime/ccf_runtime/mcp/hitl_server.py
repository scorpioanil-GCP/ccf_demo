"""The HITL MCP transport — queues as Resources, human authority as Tools.

CLAUDE.md §8.2 (SDK-defined — an extension beyond the whitepaper, and it
says so); D-IMPL-20/21; D-IMPL-353 §2 P4/P6. **This is the D-IMPL-20 PRIMARY
authority channel**: MCP server endpoints exposing the HITL queues are the
Experience-Layer primary, and the action Tool on this surface is how a
human's decision returns through the typed queue. The notification/authority
separation the ruling draws holds here structurally: webhooks and every
other notification leg are notify-only — a notification can tell a human
something is pending, but the *action* flows back only through this
surface's Tool, and the binding it carries is minted by this door.

**The bodies receive the capability; they hold no authorizer (§2 P4).** Both
handlers take ``authorized`` as their first argument — an
``Authorized[HitlQueueRead]`` for the queue resource, an
``Authorized[HitlSubmit]`` for the action tool — minted by the
:class:`~ccf_runtime.mcp.tenancy.TenantGuardedServer` wrapper for the action
each registration declares, after the deployment's
:class:`~ccf_runtime.authz.protocol.TenantAuthorizerProtocol` returns
*allowed*, and stripped from the wire schema so a caller cannot supply one
(a caller-supplied object would die at the handle's
:func:`~ccf.authz.capability.verify` anyway). There is no ``authorizer``
parameter on either body and no early-return arm for an absent one — this
builder takes the authorizer, **required**, and hands it to the wrapper; the
bodies see only the capability. What the earlier per-body helper did — ask
an *optional* authorizer inside the body, when someone remembered to bind one
— is the D-IMPL-73 shape, and it is gone rather than made mandatory.

**The door mints the binding; the caller does not describe it (§2 P6).**
``submit_hitl_action`` used to take every
:class:`~ccf.hitl.principal.HumanPrincipalBinding` field as a tool argument
— ``subject_id``, ``identity_provider_ref``, ``method``, ``assurance_level``,
``session_ref``, ``action_time`` — compared the subject with the verified
identity, and passed the rest through. The tool now takes the
:class:`~ccf.hitl.transport.HitlActionRequest` field set and nothing else:
event key, action, the content hash of what the human saw, an optional
annotation, an optional detached signature. The binding is minted by
:func:`~ccf_runtime.identity_binding.principal_from_authorized` from
``authorized.principal``, the verified token's
:class:`~ccf.hitl.principal.AuthenticationClaims`
(:func:`~ccf_runtime.identity_binding.authentication_of_token`; a token that
carries none is refused with ``ERROR_AUTHENTICATION_UNATTESTED``), and the
injected ``clock`` — so a caller-typed step-up-MFA claim is unrepresentable
on this surface, and a naive action time can no longer be presented because
no action time can be presented.

**The D-22 scope of that claim.** What this module guarantees is the
*binding-by-construction* leg: no tool call reaches the deployment's action
route without a complete, door-minted binding. The *recording* obligation —
landing the completed action on Decision Replay dimension 2 — belongs to
the HITL primitives the deployment's injected route composes (the same
scoping as :mod:`ccf.hitl.transport`), and it is demonstrated across a real
process boundary by ``tests/crossproc/test_hitl_mcp.py``, not asserted here.

**What this server holds: two Protocol callables, a clock, nothing else.**
The queue view and the action route are injected; the server holds no HITL
primitive, no transport instance, no replay writer, no graph handle, and no
Control Plane handle — the same posture as every sibling MCP role, and the
role-separation suite greps this source to keep it that way (T-07-22).

**Tenancy is a URI segment, resolved per call** (INV-CH7-16; D-23), decided
against the verified grant by the wrapper (``SEC-018``) and thereafter read
only as ``authorized.tenant``: the per-tenant queue partitioning of the typed
transport carries through to this surface intact.

**Authenticated (D-26).** The verifier/settings pair is required, and
required together, per the artifact-server precedent — this is the surface
human authority crosses, and it is the last place an unauthenticated
configuration should be reachable.

Server name, bind address, token values, tenant identifiers, event
vocabulary, approver identities and the clock are all deployment values
supplied by the caller or carried on the wire. This module holds none of
them (CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from typing import Protocol, runtime_checkable

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

from ccf.authz.capability import Authorized, HitlQueueRead, HitlSubmit
from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf.hitl.identity_binding import SignedPrincipalBinding
from ccf.hitl.principal import AuthenticationClaims
from ccf.hitl.transport import (
    HitlActionSubmission,
    PendingHitlEvent,
    SignedBindingInvalidRefused,
    SignedBindingRequiredRefused,
)
from ccf_runtime.authz.protocol import TenantAuthorizerProtocol
from ccf_runtime.http_api.errors import (
    ERROR_SIGNED_BINDING_INVALID,
    ERROR_SIGNED_BINDING_REQUIRED,
    refusal_detail,
)
from ccf_runtime.identity_binding import (
    ERROR_AUTHENTICATION_UNATTESTED,
    AuthenticationUnattested,
    attested_authentication,
    authentication_of_token,
    principal_from_authorized,
)
from ccf_runtime.mcp.tenancy import TenantGuardedServer

__ccf_mode__ = "algorithmic"

__all__ = [
    "HITL_QUEUE_URI_SCHEME",
    "HITL_QUEUE_URI_TEMPLATE",
    "SUBMIT_HITL_ACTION_TOOL",
    "HitlActionRouteProtocol",
    "HitlQueueView",
    "HitlQueueViewProtocol",
    "UnverifiedCallerRefused",
    "build_hitl_server",
    "hitl_queue_uri",
]

#: The HITL queue scheme. Its own scheme, deliberately: a queue address is
#: neither a live product, a front-door product, nor an immutable artifact,
#: and a replay record must never confuse the four (the T-06-16 split,
#: extended to this role).
HITL_QUEUE_URI_SCHEME = "ccf-hitl-queue"

#: The templated resource this server registers: one segment, because one
#: fact addresses a queue — whose it is.
HITL_QUEUE_URI_TEMPLATE = f"{HITL_QUEUE_URI_SCHEME}://{{tenant}}"

#: Media type of the served queue view — canonical JSON.
QUEUE_MIME_TYPE = "application/json"

#: The one authority Tool. Its input schema is the
#: :class:`~ccf.hitl.transport.HitlActionRequest` field set — what only the
#: human can state — and no binding field (D-IMPL-353 §2 P6).
SUBMIT_HITL_ACTION_TOOL = "submit_hitl_action"


class UnverifiedCallerRefused(RuntimeError):
    """No verified access token was present for the in-flight tool call.

    The D-26 auth middleware and the tenancy wrapper should make this
    unreachable — the server is authenticated by construction — but the
    body refuses rather than trusts when the precondition fails: the
    authentication claims a binding is minted from are read off the verified
    token, and a token nobody verified attests nothing (D-IMPL-67 item 2;
    D-IMPL-353 §2 P6).
    """


class HitlQueueView(CCFContract):
    """One tenant's pending HITL events, as served on this surface.

    A read of the typed queue, never a consumption: the events remain
    pending — resolving one is the action Tool's business, through the
    deployment's route, under a door-minted binding.
    """

    tenant: str
    events: tuple[PendingHitlEvent, ...]


@runtime_checkable
class HitlQueueViewProtocol(Protocol):
    """Where this server reads one tenant's pending events.

    A Protocol over the served-view slice of
    :class:`~ccf.hitl.transport.HITLTransportProtocol` — ``view`` — taking
    the capability the wrapper minted: the deployment supplies a callable
    over its transport, and the server holds no primitive handle of its own
    (the 07-09 key link). Whose queue is read is ``authorized.tenant``.
    """

    def __call__(
        self, authorized: Authorized[HitlQueueRead]
    ) -> tuple[PendingHitlEvent, ...]:
        """The capability's tenant's pending events, oldest first, without consuming."""
        ...


@runtime_checkable
class HitlActionRouteProtocol(Protocol):
    """The deployment's authority route for one bound submission.

    The callable a deployment supplies here composes the HITL primitives —
    resolving the gate, auditing the outcome, landing the action on replay
    dimension 2 — none of which this module can reach itself, and each of
    which requires the ``Authorized[HitlSubmit]`` this door received, so the
    route takes it too. The submission it receives is complete by
    construction: its binding was minted by this door.
    """

    def __call__(
        self,
        authorized: Authorized[HitlSubmit],
        *,
        submission: HitlActionSubmission,
    ) -> str:
        """Route one bound action; return the canonical-JSON result verbatim."""
        ...


def hitl_queue_uri(*, tenant: str) -> str:
    """Render the queue URI for one tenant.

    Exists so the server, the client, and the tests all agree what the URI
    *is* rather than each formatting it — the egress precedent.
    """
    return f"{HITL_QUEUE_URI_SCHEME}://{tenant}"


def build_hitl_server(
    *,
    server_name: str,
    queue_view: HitlQueueViewProtocol,
    action_route: HitlActionRouteProtocol,
    token_verifier: TokenVerifier,
    auth_settings: AuthSettings,
    authorizer: TenantAuthorizerProtocol,
    clock: Callable[[], datetime],
) -> FastMCP:
    """Build the authenticated HITL server over the two injected seams.

    ``stateless_http=True`` is load-bearing rather than a tuning choice: it
    is what makes the client's session-per-call cheap (:mod:`ccf.mcp.client`,
    and the held-session bridge that deadlocks without it).
    ``json_response=True`` pairs with it.

    Both ``token_verifier`` and ``auth_settings`` are required, and required
    *together*, because ``FastMCP`` installs its authentication middleware
    only when both are present (D-26, the artifact-server precedent).

    Args:
        server_name: The name this server advertises. Deployment identity.
        queue_view: The deployment's served read of its typed HITL queue —
            ``transport.view`` under the capability the wrapper minted.
        action_route: The deployment's authority route — gate resolution,
            audit, and the dimension-2 replay landing all live behind it,
            under the same capability.
        token_verifier: Verifies presented bearer tokens
            (:mod:`ccf_runtime.mcp.auth` ships the reference implementation).
        auth_settings: Issuer, resource-server identity, required scopes —
            deployment values in their entirety.
        authorizer: The deployment's per-action authorizer. **Required, no
            default** (D-IMPL-353 §4): the wrapper mints each body's
            capability from its *allowed* decision, and a door whose
            authorizer could be absent is a door whose bodies could receive
            nothing.
        clock: The injected clock the action tool stamps ``action_time``
            from. **Required, no default**: an approval's time is the
            deployment's statement, never a wall clock read here and never
            a value the caller sends.

    Returns:
        A configured ``FastMCP``. Deliberately *not* started, and no bind
        address is chosen here — hosting is the deployment's decision
        (T-06-14).
    """
    door = TenantGuardedServer(
        FastMCP(
            server_name,
            stateless_http=True,
            json_response=True,
            token_verifier=token_verifier,
            auth=auth_settings,
        ),
        authorizer=authorizer,
    )
    server = door.fastmcp

    def _verified_authentication() -> AuthenticationClaims:
        """The verified token's authentication claims, or refuse.

        Read off ``get_access_token()`` — the same verified context the
        wrapper decided tenancy on (A1 spike verdict). A refusal for absent
        claims is the shared constant, rendered protocol-natively (D-08).
        """
        token = get_access_token()
        if token is None:
            raise UnverifiedCallerRefused(
                "no verified access token accompanies this tool call; the"
                " authority surface mints bindings from verified credentials"
                " only (D-IMPL-67; D-26; D-IMPL-353 §2 P6)"
            )
        try:
            return attested_authentication(authentication_of_token(token))
        except AuthenticationUnattested as error:
            raise ValueError(
                json.dumps(
                    refusal_detail(
                        error_code=ERROR_AUTHENTICATION_UNATTESTED,
                        message=str(error),
                    )
                )
            ) from error

    @door.resource(
        HITL_QUEUE_URI_TEMPLATE,
        subject=door.from_argument("tenant"),
        mutating=False,
        action=HitlQueueRead,
        resource=door.route(),
        mime_type=QUEUE_MIME_TYPE,
    )
    def hitl_queue(authorized: Authorized[HitlQueueRead], tenant: str) -> str:
        """Serve the capability's tenant's pending HITL events as canonical JSON.

        ``tenant`` is the wire segment the wrapper decided against the
        verified grant and minted the capability for; this body reads the
        tenant back off ``authorized`` and nothing else (D-IMPL-353 §1.3).
        """
        view = HitlQueueView(
            tenant=authorized.tenant, events=queue_view(authorized)
        )
        return canonical_bytes(view).decode("utf-8")

    @door.tool(
        name=SUBMIT_HITL_ACTION_TOOL,
        subject=door.from_argument("tenant"),
        mutating=True,
        action=HitlSubmit,
        resource=door.from_argument("event_key"),
    )
    def submit_hitl_action(
        authorized: Authorized[HitlSubmit],
        tenant: str,
        event_key: str,
        action: str,
        product_content_hash: str,
        annotation: str | None = None,
        signed_binding_signature: str | None = None,
        signed_binding_key_id: str | None = None,
    ) -> str:
        """Submit one human action under a door-minted principal binding.

        The input schema is what only the human can state (D-IMPL-353 §2
        P6): the event, the verdict, the content hash of what they saw, an
        optional annotation and an optional detached signature. No binding
        field is a parameter — ``subject_id``, ``identity_provider_ref``,
        ``method``, ``assurance_level``, ``session_ref`` and ``action_time``
        do not exist on this tool — so a caller cannot describe their own
        authentication. The binding is minted from ``authorized.principal``,
        the verified token's claims and the injected clock.

        Raises:
            UnverifiedCallerRefused: no verified access token in context.
            ValueError: the credential states no authentication context
                (``ERROR_AUTHENTICATION_UNATTESTED``), the signature pair is
                half-presented, or the transport refused the signed binding
                (``ERROR_SIGNED_BINDING_REQUIRED`` /
                ``ERROR_SIGNED_BINDING_INVALID``) — each carrying the one
                refusal-body shape (D-08).
        """
        authentication = _verified_authentication()
        derived = principal_from_authorized(
            authorized,
            authentication=authentication,
            action_time=clock(),
            product_content_hash=product_content_hash,
        )
        if (signed_binding_signature is None) != (signed_binding_key_id is None):
            raise ValueError(
                "signed_binding_signature and signed_binding_key_id are"
                " presented together or not at all (D-16; D-IMPL-21)"
            )
        signed_binding: SignedPrincipalBinding | None = None
        if signed_binding_signature is not None and signed_binding_key_id is not None:
            # The signature is over the binding THIS door minted — a signer
            # attests the server's statement of the action, not its own.
            signed_binding = SignedPrincipalBinding(
                binding=derived,
                signature=signed_binding_signature,
                key_id=signed_binding_key_id,
            )
        submission = HitlActionSubmission(
            event_key=event_key,
            action=action,
            principal=derived,
            annotation=annotation,
            signed_binding=signed_binding,
        )
        try:
            return action_route(authorized, submission=submission)
        except SignedBindingRequiredRefused as error:
            # D-16 door mapping (08-03): the MCP door carries the SAME
            # shared error-code constants as the HTTP door — single
            # source of truth, machine-attributable at both doors
            # (T-08-07b). The payload is the one refusal-body shape.
            raise ValueError(
                json.dumps(
                    refusal_detail(
                        error_code=ERROR_SIGNED_BINDING_REQUIRED,
                        message=str(error),
                    )
                )
            ) from error
        except SignedBindingInvalidRefused as error:
            raise ValueError(
                json.dumps(
                    refusal_detail(
                        error_code=ERROR_SIGNED_BINDING_INVALID,
                        message=str(error),
                    )
                )
            ) from error

    return server
