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

from datetime import datetime
from typing import Protocol, runtime_checkable

from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_bytes
from ccf.hitl.principal import (
    ApproverIdentity,
    AuthenticationContext,
    HumanPrincipalBinding,
)
from ccf.hitl.transport import HitlActionSubmission, PendingHitlEvent

__ccf_mode__ = "algorithmic"

__all__ = [
    "HITL_QUEUE_URI_SCHEME",
    "HITL_QUEUE_URI_TEMPLATE",
    "SUBMIT_HITL_ACTION_TOOL",
    "HitlActionRouteProtocol",
    "HitlQueueView",
    "HitlQueueViewProtocol",
    "NaiveActionTimeRefused",
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
    ) -> str:
        """Submit one human action under a complete principal binding.

        Every ``HumanPrincipalBinding`` field is a required parameter of
        this tool — the input schema *is* the D-IMPL-21 field set, so a call
        missing any of them is refused by the tool boundary before a
        submission can exist, and a malformed value (a non-hash product
        identity, an unknown action, a naive action time) is refused by the
        typed contracts. Only a complete, validated submission reaches the
        deployment's authority route.

        Raises:
            NaiveActionTimeRefused: ``action_time`` carries no UTC offset.
        """
        parsed_time = datetime.fromisoformat(action_time)
        if parsed_time.tzinfo is None:
            raise NaiveActionTimeRefused(
                f"action_time {action_time!r} carries no UTC offset; an"
                " ambiguous instant cannot bind a human action (D-IMPL-38,"
                " D-IMPL-21)"
            )
        submission = HitlActionSubmission(
            event_key=event_key,
            tenant=tenant,
            action=action,
            principal=HumanPrincipalBinding(
                approver=ApproverIdentity(
                    subject_id=subject_id,
                    identity_provider_ref=identity_provider_ref,
                ),
                authentication=AuthenticationContext(
                    method=method,
                    assurance_level=assurance_level,
                    session_ref=session_ref,
                ),
                action_time=parsed_time,
                product_content_hash=product_content_hash,
            ),
            annotation=annotation,
        )
        return action_route(submission=submission)

    return server
