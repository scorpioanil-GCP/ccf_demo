"""The HITL MCP transport — queues as Resources, human authority as Tools.

CLAUDE.md §8.2 (SDK-defined — an extension beyond the whitepaper, and it
says so); D-IMPL-20/21. **This is the D-IMPL-20 PRIMARY authority channel**:
MCP server endpoints exposing the HITL queues are the Experience-Layer
primary, and the action Tools on this surface are how a human's decision
returns through the typed queue. The notification/authority separation the
ruling draws holds here structurally: webhooks and every other notification
leg are notify-only — a notification can tell a human something is pending,
but the *action* flows back only through this surface's Tools, each of which
requires the complete :class:`~ccf.hitl.principal.HumanPrincipalBinding`
field set in its input schema. An unbound action is therefore
unrepresentable through the MCP surface, exactly as it is unrepresentable
through the in-process typed contract — the MCP surface cannot bypass audit.

**The D-22 scope of that claim.** What this module guarantees is the
*binding-by-construction* leg: no tool call reaches the deployment's action
route without a complete, validated binding, because the tool signature
requires every field and the typed contracts refuse partial or malformed
values at the boundary. The *recording* obligation — landing the completed
action on Decision Replay dimension 2 — belongs to the HITL primitives the
deployment's injected route composes (the same scoping as
:mod:`ccf.hitl.transport`), and it is demonstrated across a real process
boundary by ``tests/crossproc/test_hitl_mcp.py``, not asserted here.

**What this server holds: two Protocol callables, nothing else.** The queue
view and the action route are injected; the server holds no HITL primitive,
no transport instance, no replay writer, no graph handle, and no Control
Plane handle — the same posture as every sibling MCP role, and the
role-separation suite greps this source to keep it that way (T-07-22).

**Tenancy is a URI segment, resolved per call** (INV-CH7-16; D-23): one
server over a shared deployment must not be able to show one tenant's
pending events to another by positional accident, and the per-tenant queue
partitioning of the typed transport carries through to this surface intact.

**The subject is the verified identity (D-IMPL-67 item 2).** The action
Tool binds the submission's subject to the server's *verified* token
identity through the shared derivation
(:func:`~ccf_runtime.identity_binding.principal_from_token_grant`): a
caller-typed ``subject_id`` is a claim that must match the verified
``client_id``, a conflicting claim is a typed refusal
(:class:`SubjectIdentityConflictRefused`), and an unverifiable call is
refused outright (:class:`UnverifiedCallerRefused`) — never trusted.

**Authenticated (D-26).** The verifier/settings pair is required, and
required together, per the artifact-server precedent — this is the surface
human authority crosses, and it is the last place an unauthenticated
configuration should be reachable.

Server name, bind address, token values, tenant identifiers, event
vocabulary, and approver identities are all deployment values supplied by
the caller or carried on the wire. This module holds none of them (CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Protocol, runtime_checkable

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf.hitl.identity_binding import SignedPrincipalBinding
from ccf.hitl.transport import (
    HitlActionSubmission,
    PendingHitlEvent,
    SignedBindingInvalidRefused,
    SignedBindingRequiredRefused,
)
from ccf_runtime.http_api.errors import (
    ERROR_SIGNED_BINDING_INVALID,
    ERROR_SIGNED_BINDING_REQUIRED,
    refusal_detail,
)
from ccf_runtime.identity_binding import principal_from_token_grant
from ccf_runtime.mcp.auth import TokenGrant

__ccf_mode__ = "algorithmic"

__all__ = [
    "HITL_QUEUE_URI_SCHEME",
    "HITL_QUEUE_URI_TEMPLATE",
    "SUBMIT_HITL_ACTION_TOOL",
    "HitlActionRouteProtocol",
    "HitlQueueView",
    "HitlQueueViewProtocol",
    "NaiveActionTimeRefused",
    "SubjectIdentityConflictRefused",
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

#: The one authority Tool. Its input schema requires every
#: ``HumanPrincipalBinding`` field; there is no reduced variant.
SUBMIT_HITL_ACTION_TOOL = "submit_hitl_action"


class NaiveActionTimeRefused(ValueError):
    """An action time without a UTC offset was presented to the authority tool.

    Refused at the boundary rather than passed on: the canonical serializer
    would refuse a naive datetime anyway (D-IMPL-38), and refusing it here
    keeps the ambiguity out of the submission before anything is routed —
    a replay must never have to guess which wall a human's clock hung on.
    """


class UnverifiedCallerRefused(RuntimeError):
    """No verified access token was present for the in-flight tool call.

    The D-26 auth middleware should make this unreachable — the server is
    authenticated by construction — but the tool refuses rather than trusts
    the caller's claim when the precondition fails (D-IMPL-67 item 2): a
    subject the deployment did not verify never binds a human action.
    """


class SubjectIdentityConflictRefused(ValueError):
    """The caller-typed ``subject_id`` conflicts with the verified identity.

    The audited subject is the server's verified token identity, never the
    caller's claim (D-IMPL-67; D-IMPL-21). The refusal names the conflict
    without echoing token values.
    """


class HitlQueueView(CCFContract):
    """One tenant's pending HITL events, as served on this surface.

    A read of the typed queue, never a consumption: the events remain
    pending — resolving one is the action Tool's business, through the
    deployment's route, under a complete binding.
    """

    tenant: str
    events: tuple[PendingHitlEvent, ...]


@runtime_checkable
class HitlQueueViewProtocol(Protocol):
    """Where this server reads one tenant's pending events.

    A Protocol over the queue-view slice of
    :class:`~ccf.hitl.transport.HITLTransportProtocol`: the deployment
    supplies a callable over its transport, and the server holds no
    primitive handle of its own (the 07-09 key link).
    """

    def __call__(self, *, tenant: str) -> tuple[PendingHitlEvent, ...]:
        """The tenant's pending events, oldest first, without consuming."""
        ...


@runtime_checkable
class HitlActionRouteProtocol(Protocol):
    """The deployment's authority route for one bound submission.

    The callable a deployment supplies here composes the HITL primitives —
    resolving the gate, auditing the outcome, landing the action on replay
    dimension 2 — none of which this module can reach itself. The submission
    it receives is complete by construction: the tool signature and the
    typed contracts refuse anything less before this seam is called.
    """

    def __call__(self, *, submission: HitlActionSubmission) -> str:
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
        queue_view: The deployment's read of its typed HITL queue.
        action_route: The deployment's authority route — gate resolution,
            audit, and the dimension-2 replay landing all live behind it.
        token_verifier: Verifies presented bearer tokens
            (:mod:`ccf_runtime.mcp.auth` ships the reference implementation).
        auth_settings: Issuer, resource-server identity, required scopes —
            deployment values in their entirety.

    Returns:
        A configured ``FastMCP``. Deliberately *not* started, and no bind
        address is chosen here — hosting is the deployment's decision
        (T-06-14).
    """
    server = FastMCP(
        server_name,
        stateless_http=True,
        json_response=True,
        token_verifier=token_verifier,
        auth=auth_settings,
    )

    @server.resource(HITL_QUEUE_URI_TEMPLATE, mime_type=QUEUE_MIME_TYPE)
    def hitl_queue(tenant: str) -> str:
        """Serve one tenant's pending HITL events as canonical JSON."""
        view = HitlQueueView(tenant=tenant, events=queue_view(tenant=tenant))
        return canonical_bytes(view).decode("utf-8")

    @server.tool(name=SUBMIT_HITL_ACTION_TOOL)
    def submit_hitl_action(
        tenant: str,
        event_key: str,
        action: str,
        subject_id: str,
        identity_provider_ref: str,
        method: str,
        assurance_level: str,
        session_ref: str,
        action_time: str,
        product_content_hash: str,
        annotation: str | None = None,
        signed_binding_signature: str | None = None,
        signed_binding_key_id: str | None = None,
    ) -> str:
        """Submit one human action under a verified principal binding.

        Every ``HumanPrincipalBinding`` field is a required parameter of
        this tool — the input schema *is* the D-IMPL-21 field set, so a call
        missing any of them is refused by the tool boundary before a
        submission can exist, and a malformed value (a non-hash product
        identity, an unknown action, a naive action time) is refused by the
        typed contracts.

        **The subject is the server's verified token identity, never the
        caller's claim (D-IMPL-67 item 2).** ``subject_id`` remains a
        required parameter — the D-IMPL-21 field-set input schema is
        preserved — but it is a *claim that must match*: a value conflicting
        with the verified identity is a typed refusal, and the binding that
        reaches the deployment's authority route is derived through
        :func:`~ccf_runtime.identity_binding.principal_from_token_grant`,
        which has no caller subject parameter.

        Raises:
            NaiveActionTimeRefused: ``action_time`` carries no UTC offset.
            UnverifiedCallerRefused: no verified access token in context.
            SubjectIdentityConflictRefused: ``subject_id`` conflicts with
                the verified token identity.
        """
        parsed_time = datetime.fromisoformat(action_time)
        if parsed_time.tzinfo is None:
            raise NaiveActionTimeRefused(
                f"action_time {action_time!r} carries no UTC offset; an"
                " ambiguous instant cannot bind a human action (D-IMPL-38,"
                " D-IMPL-21)"
            )
        token = get_access_token()
        if token is None:
            raise UnverifiedCallerRefused(
                "no verified access token accompanies this tool call; the"
                " authority surface binds subjects to verified identities"
                " only (D-IMPL-67; D-26)"
            )
        if subject_id != token.client_id:
            raise SubjectIdentityConflictRefused(
                "identity conflict: the claimed subject_id does not match"
                " the verified token identity; the audited subject is the"
                " server's verified identity, never the caller's claim"
                " (D-IMPL-67; D-IMPL-21)"
            )
        derived = principal_from_token_grant(
            grant=TokenGrant(
                client_id=token.client_id, scopes=tuple(token.scopes)
            ),
            identity_provider_ref=identity_provider_ref,
            method=method,
            assurance_level=assurance_level,
            session_ref=session_ref,
            action_time=parsed_time,
            product_content_hash=product_content_hash,
        )
        signed_binding: SignedPrincipalBinding | None = None
        if (signed_binding_signature is None) != (
            signed_binding_key_id is None
        ):
            raise ValueError(
                "signed_binding_signature and signed_binding_key_id are"
                " presented together or not at all (D-16; D-IMPL-21)"
            )
        if (
            signed_binding_signature is not None
            and signed_binding_key_id is not None
        ):
            signed_binding = SignedPrincipalBinding(
                binding=derived,
                signature=signed_binding_signature,
                key_id=signed_binding_key_id,
            )
        submission = HitlActionSubmission(
            event_key=event_key,
            tenant=tenant,
            action=action,
            principal=derived,
            annotation=annotation,
            signed_binding=signed_binding,
        )
        try:
            return action_route(submission=submission)
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
