"""``LfA2AWire`` — a **Peering transport** speaking Linux Foundation A2A.

The D-IMPL-14 **v0 default** implementation of
:class:`~ccf.peering.protocol.PeeringProtocol`. *Peering* is the category — a
governed, peer-symmetric context exchange between two fabrics that each have a
Control Plane of their own — and A2A is its reference transport rather than its
name (``D-IMPL-59`` parts 1 and 2, Dave, 2026-07-27). This module keeps the
protocol's own name for exactly that reason: renaming it "peering" would erase
the distinction the ruling exists to draw.

**This transport declares trust inputs and cannot manufacture admission**
(``D-IMPL-59`` part 4). It yields
:class:`~ccf.peering.protocol.InboundProduct` values — the peer the channel
observed and the signed bytes it carried, both *inputs* to a decision made
elsewhere — while :class:`~ccf.peering.admission.PeeringAdmissionGate` reaches
the verdict and constructs the value L2 accepts. Nothing in this module can
construct it, so this transport cannot conclude in its own favour.

SDK-defined extension (CLAUDE.md §7.2 — "A2A federation is first-class in v0"),
attaching to whitepaper §8.3 Pattern 4. D-IMPL-14 rules **Linux Foundation A2A**
as the v0 default wire; D-11 sequences it *second*, after
:mod:`ccf_runtime.peering.typed_http`, precisely so the abstraction, the Control
Plane admission gate, the identity primitives and the cross-process fixture were
all proven against a transport bound to no standard first. What lands here is
therefore a **substitution, not a redesign**: the same
:class:`~ccf.peering.protocol.PeeringProtocol`, the same unchanged consumer-side
assertions, a different wire underneath. CLAUDE.md §7.2 states the commitment
this module exists to demonstrate — *the Context Product Contract is the stable
layer; the wire is replaceable.*

**LF A2A's own machinery does LF A2A's job.** JSON-RPC dispatch, the task
lifecycle, event queues, Agent Card discovery and card resolution are the
``a2a-sdk``'s — :class:`a2a.server.request_handlers.DefaultRequestHandler`,
:func:`a2a.server.routes.create_jsonrpc_routes`,
:func:`a2a.server.routes.create_agent_card_routes`,
:class:`a2a.client.A2ACardResolver` and :class:`a2a.client.ClientFactory` are
used as given. Re-implementing any of them would forfeit exactly the interop
that is the reason for choosing LF A2A at all, and would make this module a
private protocol wearing a standard's name.

**Why protobuf stops at this module's edge (Pitfall 5, C4).** ``a2a-sdk`` 1.x is
protobuf-generated. A protobuf message has no Pydantic validation and no
``extra=forbid`` semantics: an unknown field is silently *preserved* rather than
refused, and a field a peer omits reads back as a type-default rather than as
absent. Treating such a message as the typed boundary would mean the fabric's
closed-world contract stopped at the process edge, and that "the product
validated" could be true of a message that had been quietly extended. So the
boundary sits above it: every generated type is constructed and consumed inside
this module, converted to and from the CCF contracts :mod:`ccf.peering.protocol`
declares, and **nothing in ``/src`` imports ``a2a`` at all**. What the fabric
trusts is CCF's own validation, run by the admission gate over the raw canonical
bytes — never a field a protobuf message happened to carry.

**The payload rides in ``Part.raw``, and that choice was measured** (research
assumption A2, resolved by prototype before this module was written; see the
SUMMARY for the recorded run). ``Part.raw`` is a protobuf ``bytes`` field and
survives both binary and JSON-RPC serialization byte for byte — verified over a
real signed banking product, whose detached-JWS signature still verified after
the round trip. ``Part.data`` was **rejected**: it is a
``google.protobuf.Value``, so its contents are re-modelled through Struct's JSON
value model, where integers become doubles, key order is not preserved, and byte
equality — and therefore the signature — does not survive. A transport that
mutated the payload would refuse the *genuine* product, which is why this is a
correctness question and not a taste one.

**What travels in ``Part.raw`` is the whole envelope, one canonical document.**
The bytes are :func:`ccf.contracts.canonical.canonical_bytes` of the
:class:`~ccf.peering.identity.SignedContextProduct`, whose ``payload`` member is
already base64url text. This is a **deviation from the plan's wording** (raw
product bytes, with the detached-JWS members carried beside them in
``Part.metadata``), taken for the reason 06-09 recorded and 06-07 established:
splitting the envelope would oblige this transport to base64url-encode the
payload member back into place on receipt, and nothing in this codebase
hand-rolls base64url — that is where verification bugs hide. Carried whole, the
product's own canonical bytes are never decoded, re-encoded or round-tripped
anywhere here; they cross as the same characters the producer signed. The A2
property being asserted is unaffected and is asserted directly: what goes into
``Part.raw`` comes out of ``Part.raw`` identical, and the signature over the
carried product still verifies.

**What this transport does not check.** It performs no admission check of any
kind. It does not verify a signature, does not read a trust policy, and does not
decide whether a peer may send what it sent. It hands what it received to its
caller, and the caller hands that to the Control Plane gate. D-12 rejected
putting the check inside a ``PeeringProtocol`` implementation: two transports ship
this phase and more may follow, and a per-transport check states the rule once
per wire — which lets a later wire state it differently, or omit it. Every check
the code below *does* perform is a framing check, named as such. This paragraph
is the only place in this file that names that gate at all.

**Agent Cards are discovery, never trust (T-06-55).** A card says where a peer
answers and which bindings it speaks. It does not say who the peer is as far as
admission is concerned: what binds a product to a principal is the detached-JWS
``kid`` resolved against the consuming tenant's trust-policy artifact. A spoofed
or malicious card can therefore misdirect a *carriage*, and cannot make an
unentitled product admissible.

**What this transport cannot do.** It holds no graph write handle, no graph
store, and no assembly worker. There is no constructor parameter, attribute,
method parameter, or return type here that is or names one, and this module
imports nothing from the L3 graph package or from L2. The honest claim (D-21) is
structural rather than absolute: what this module's declared surface offers is
an outbound message send and an inbound queue of
:class:`~ccf.peering.protocol.InboundProduct` values, and an ``InboundProduct`` is not
what L2 accepts. ``tests/invariants/test_peering_single_writer.py`` is what holds
that — by import scan, by identifier scan, and by attribute inspection of a
constructed instance, across every module this package discovers — rather than
this paragraph.

**Deployment values are the caller's.** The local Agent Card, the RPC route, the
peer base URLs, the HTTP client, the clock, the request deadline and the message
size ceiling are all supplied by the caller. This module holds no address, no
port, no scheme literal, no card identity and no default ceiling (CINV-01,
D-IMPL-38). Tenancy is a per-call argument carried on
:class:`~ccf.peering.protocol.PeerRef`, never a constructor field, on the
:class:`~ccf_runtime.peering.typed_http.TypedHttpWire` precedent.

**Both halves of the sync↔async seam are offered**, on the
:class:`~ccf.mcp.client.McpResourceClient` precedent: ``a2a-sdk``'s client is
async while the fabric core is synchronous (D-IMPL-04(b)), so :meth:`emit` is a
thin facade over :meth:`emit_async`. The facade owns the loop it runs on and
refuses to be called from inside a running one, rather than silently deadlocking
a caller who already had one.

Algorithmic module (CINV-03): framing, transport and typed conversion only.
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Callable, Iterator, Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

import httpx
from a2a.client import A2ACardResolver, Client, ClientConfig, ClientFactory
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    Message,
    Part,
    Role,
    SendMessageRequest,
)
from pydantic import ValidationError
from starlette.responses import Response
from starlette.routing import BaseRoute, Route
from starlette.status import HTTP_413_CONTENT_TOO_LARGE
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.types import Message as AsgiMessage

from ccf.peering.identity import SignatureMalformed, SignedContextProduct
from ccf.peering.protocol import EmitReceipt, InboundProduct, PeerRef
from ccf.contracts.canonical import canonical_bytes

from ccf_runtime.peering.typed_http import (
    MalformedWireMessage,
    PeerUnreachable,
    ReceiveQueueFull,
    WireTransportError,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "JSONRPC_BINDING",
    "PEER_ID_METADATA",
    "PEER_TENANT_METADATA",
    "SIGNED_PRODUCT_MEDIA_TYPE",
    "LfA2AWire",
    "PeerCardResolver",
    "UnsupportedCarriageOperation",
    "build_agent_card",
]

#: Media type stated on the carried :class:`a2a.types.Part`. Names *what was
#: sent* — a signed canonical Context Product — so a peer that was handed some
#: other CCF artifact refuses it at the frame rather than at the contract.
#: Deliberately the same string :mod:`ccf_runtime.peering.typed_http` uses: the
#: document is identical whichever wire carried it, which is the substitution
#: claim made concrete.
SIGNED_PRODUCT_MEDIA_TYPE = "application/ccf-signed-product+json"

#: The LF A2A protocol binding this transport speaks. JSON-RPC rather than gRPC
#: or REST because it is the binding ``a2a-sdk`` treats as the default and the
#: one reachable over the same ASGI host every other CCF surface already uses.
JSONRPC_BINDING = "JSONRPC"

#: Message-metadata key a sender states its own peer identifier under. Read as a
#: claim and nothing more: it selects which trust-policy entry the Control Plane
#: will read, and it proves nothing. What binds a product to a principal is the
#: signature, which this module never checks.
PEER_ID_METADATA = "ccf_peer_id"

#: Message-metadata key a sender states the federation tenant under. Also a
#: claim; the gate is tenant-scoped at construction and compares the *product's*
#: tenant against its own, so a lie here changes which gate refuses, never
#: whether one does.
PEER_TENANT_METADATA = "ccf_peer_tenant"

#: The oneof group ``Part``'s content alternatives live in. Named here because
#: reading a protobuf oneof by string is exactly the kind of generated-surface
#: detail that must not leak past this module.
_PART_CONTENT_ONEOF = "content"

#: The ``Part`` alternative carrying opaque bytes. See the module docstring for
#: why this and not ``data``.
_RAW_ALTERNATIVE = "raw"


@runtime_checkable
class PeerCardResolver(Protocol):
    """Where a peer's Agent Card is served, as far as *this* deployment knows.

    A seam rather than a field on :class:`~ccf.peering.protocol.PeerRef`, for the reason
    :class:`~ccf_runtime.peering.typed_http.PeerEndpointResolver` records: a
    ``PeerRef`` deliberately is not an address, because trust that keyed on where
    a message arrived from would key on the property an attacker most easily
    controls. Base URLs are deployment topology and change without the
    federation changing.

    Returning a *base* URL rather than an RPC endpoint is what lets
    :class:`a2a.client.A2ACardResolver` do the discovery it exists for: the card
    at the well-known path states the peer's real bindings and URLs, so this
    deployment does not have to encode another party's route table.

    ``runtime_checkable`` supports composition-root wiring checks; it verifies
    method presence only, so static conformance still rests on mypy.
    """

    def __call__(self, *, peer: PeerRef) -> str:
        """Return the base URL this deployment reaches ``peer``'s card at.

        Raises:
            PeerUnreachable: this deployment knows no base URL for that peer.
        """
        ...


def build_agent_card(
    *,
    name: str,
    version: str,
    description: str,
    rpc_url: str,
) -> AgentCard:
    """Build the local Agent Card from values the deployment supplies.

    A helper rather than a constant: an Agent Card is an identity-and-topology
    statement about one deployment, so every field in it is a deployment value
    and none of them may be a literal in library code (CINV-01). The helper
    exists so a caller does not have to import ``a2a``'s generated types to
    stand a peer up, which keeps the protobuf surface inside this module for
    ordinary callers as well as for ``/src``.

    The declared input and output modes are :data:`SIGNED_PRODUCT_MEDIA_TYPE`,
    because a CCF peer carries exactly one kind of document and a card that
    advertised more would be describing an agent this transport is not.

    Args:
        name: The peer's name on the card.
        version: The peer's declared version.
        description: The peer's card description.
        rpc_url: The absolute URL this deployment's JSON-RPC route is reachable
            at, as other peers will address it.
    """
    return AgentCard(
        name=name,
        version=version,
        description=description,
        supported_interfaces=[
            AgentInterface(protocol_binding=JSONRPC_BINDING, url=rpc_url)
        ],
        capabilities=AgentCapabilities(),
        default_input_modes=[SIGNED_PRODUCT_MEDIA_TYPE],
        default_output_modes=[SIGNED_PRODUCT_MEDIA_TYPE],
        skills=[],
    )


class UnsupportedCarriageOperation(WireTransportError):
    """A task-lifecycle operation this transport does not offer was requested.

    Typed into the transport hierarchy rather than raised bare, so a caller
    handling :class:`~ccf_runtime.peering.typed_http.WireTransportError` handles this
    too. Like every member of that hierarchy it is *not* a governance verdict: a
    governance verdict is a value the Control Plane returns.
    """


class _RequestBodyLimit:
    """Hold a request body to ``max_bytes`` before the app behind it reads any
    of it (SEC-021-U1, ``D-IMPL-370`` (3)).

    ``a2a-sdk``'s JSON-RPC dispatcher begins with ``await request.json()``,
    which reads the whole body and parses it before anything in this module
    runs. :meth:`LfA2AWire.routes` puts this layer in front of it on the route,
    so the dispatcher is never handed more than the limit:

    * a declared ``Content-Length`` over the limit is answered 413 before a
      byte of the body is read;
    * otherwise the body is read here and counted as ``receive()`` yields it,
      and it is answered 413 the moment the count exceeds the limit. A length
      is a claim a peer can understate, so the count is kept whether or not a
      length was declared;
    * a body within the limit is handed on whole, as one ``http.request``
      message, and every later ``receive()`` is the peer's own, so disconnect
      detection behind this layer is unchanged.

    Over the limit the app behind this layer is never called. The layer keeps
    at most the limit, and does not keep the message that crossed it. A peer
    that goes away before its body is complete is handed to nobody. The layer
    cannot bound what the ASGI server buffers before it hands a message over,
    nor what the server does with the bytes this layer never reads; those are
    the server's concern.

    The limit is per request. It does not bound how many requests are in
    flight at once, so the bytes held across concurrent requests can reach the
    limit times the number of requests the server admits.

    A framing check, like every other check in this module: it decides nothing
    about the peer, the signature or the trust policy.
    """

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self._app = app
        self._max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        if self._declared_over(scope):
            await self._refuse(scope, receive, send)
            return
        chunks: list[bytes] = []
        received = 0
        while True:
            message = await receive()
            if message["type"] != "http.request":
                # The peer disconnected before its body was complete. There is
                # no one to answer and nothing whole to hand on.
                return
            chunk: bytes = message.get("body", b"")
            received += len(chunk)
            if received > self._max_bytes:
                await self._refuse(scope, receive, send)
                return
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        await self._app(scope, _replayed(b"".join(chunks), receive), send)

    def _declared_over(self, scope: Scope) -> bool:
        """Whether any declared ``Content-Length`` exceeds the limit.

        Only an all-digit value is read, and anything else is left to the
        count, which is the authoritative check. A digit string longer than the
        limit's own digits is over without being converted, so no declared
        value is too long to compare.
        """
        ceiling = str(self._max_bytes)
        for name, value in scope.get("headers", ()):
            if name.lower() != b"content-length":
                continue
            digits = value.strip().lstrip(b"0") or b"0"
            if not digits.isdigit():
                continue
            if len(digits) > len(ceiling) or int(digits) > self._max_bytes:
                return True
        return False

    @staticmethod
    async def _refuse(scope: Scope, receive: Receive, send: Send) -> None:
        """Answer 413 Content Too Large, as the typed-HTTP leg does."""
        await Response(status_code=HTTP_413_CONTENT_TOO_LARGE)(scope, receive, send)


def _replayed(body: bytes, receive: Receive) -> Receive:
    """A ``receive`` that yields ``body`` once, whole, and then the peer's own."""
    delivered = False

    async def replay() -> AsgiMessage:
        nonlocal delivered
        if delivered:
            return await receive()
        delivered = True
        return {"type": "http.request", "body": body, "more_body": False}

    return replay


class _InboundExecutor(AgentExecutor):
    """The ``a2a-sdk`` executor that frames one inbound message and queues it.

    An :class:`a2a.server.agent_execution.AgentExecutor` is where the SDK hands
    control to the application, and for CCF the application-level act is
    deliberately tiny: frame the message, queue the envelope, acknowledge. There
    is no agent loop here and there is nothing for one to do — CLAUDE.md §7.3 is
    explicit that CCF does not ship a loop, and a transport is the last place one
    would belong.

    Refusals are raised rather than returned. The SDK turns an exception out of
    :meth:`execute` into a JSON-RPC error, which the sending peer sees as a
    failed carriage — the LF A2A analogue of the typed-HTTP leg's ``400``, and
    the same posture: a frame this deployment cannot read is not silently
    accepted.
    """

    def __init__(self, *, wire: LfA2AWire) -> None:
        self._wire = wire

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Frame the inbound message, queue it, and acknowledge the carriage."""
        message = context.message
        if message is None:
            raise MalformedWireMessage(
                "the carriage carried no message; there is nothing to frame"
            )
        inbound, carriage_id = self._wire._accept(message)
        self._wire._enqueue(inbound)
        await event_queue.enqueue_event(
            Message(
                message_id=carriage_id,
                role=Role.ROLE_AGENT,
                parts=[Part(text=carriage_id)],
            )
        )

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Refuse cancellation: a carriage is not a long-running task.

        This transport queues a received envelope synchronously inside
        :meth:`execute` and returns; by the time a cancellation could arrive
        there is nothing left to cancel, and pretending otherwise would leave a
        peer believing a delivered product had been withdrawn.
        """
        raise UnsupportedCarriageOperation(
            "an A2A carriage completes within the request; there is no"
            " long-running task to cancel"
        )


class LfA2AWire:
    """A :class:`~ccf.peering.protocol.PeeringProtocol` over Linux Foundation
    A2A (D-IMPL-14).

    Symmetric by construction, on the
    :class:`~ccf_runtime.peering.typed_http.TypedHttpWire` precedent: one instance is
    both the client leg that emits and the owner of the JSON-RPC routes that
    queue what arrives. A deployment that only sends never mounts :meth:`routes`,
    and one that only receives never calls :meth:`emit`; neither case needs a
    second type.

    Args:
        local_peer_id: This deployment's own identifier on the wire, stated on
            every outbound message. Identity, never location. There is no tenant
            beside it: tenancy rides on the ``PeerRef`` passed to :meth:`emit`,
            keyword-only, so a shared transport cannot emit into the wrong tenant
            positionally.
        agent_card: This deployment's card, built by the caller — see
            :func:`build_agent_card`. Every field on it is a deployment value.
        cards: How a peer identity becomes the base URL its card is served at.
        http_client_factory: Builds the ``httpx.AsyncClient`` each emission runs
            on. A factory rather than a client because an ``AsyncClient`` binds
            to the event loop it was created on, and :meth:`emit` owns a fresh
            loop per call; injected rather than constructed because timeouts,
            transport security, proxies and connection limits are deployment
            infrastructure and the SDK has no business choosing them
            (CLAUDE.md §13).
        clock: The receiving side's time source, injected. Nothing here reads a
            wall clock: the received instant lands in the carriage identifier,
            and a hidden clock would make that identifier untestable.
        rpc_path: The route the JSON-RPC endpoint is mounted at. A deployment
            value with no default — a library that picked a path would be picking
            a piece of a deployment's URL space.
        max_message_bytes: The largest request body this endpoint will read,
            and so also the largest carried document it will accept. No
            default (D-IMPL-38): how large a legitimate federated product is,
            is something only the deployment knows, and a limit nobody chose is
            either an availability hole or an outage. It is applied twice. On
            the JSON-RPC route it bounds the whole request body before
            ``a2a-sdk`` reads it (SEC-021-U1, ``D-IMPL-370`` (3); see
            :meth:`routes`), and in :meth:`_accept` it bounds the carried
            document. The JSON-RPC binding carries the document base64-encoded
            inside the request, so the body limit is the tighter of the two:
            the largest document a peer can deliver is about three quarters of
            this value, less the JSON-RPC envelope around it. :meth:`emit`
            checks only the document, so a sender declaring the same value can
            emit a document this endpoint answers 413, which the sender sees as
            :class:`~ccf_runtime.peering.typed_http.PeerUnreachable`. Defense
            in depth, not the rule — the authoritative ceiling is the Control
            Plane's, applied by the gate before anything canonicalizes.
        max_pending: The most received messages this endpoint will hold before
            :meth:`receive` drains them (SEC-021, ``D-IMPL-369``). Required,
            keyword-only, no default (Q13; D-IMPL-38): a buffer size is a
            deployment's capacity decision. At the bound the newcomer is refused
            with :class:`~ccf_runtime.peering.typed_http.ReceiveQueueFull`, which
            ``a2a-sdk`` returns to the sending peer as a JSON-RPC error, and the
            queued messages are preserved in order; nothing is evicted.

    Raises:
        ValueError: ``max_message_bytes`` or ``max_pending`` is not positive. A
            zero limit accepts nothing and is far more likely a mistake than a
            policy.
    """

    def __init__(
        self,
        *,
        local_peer_id: str,
        agent_card: AgentCard,
        cards: PeerCardResolver,
        http_client_factory: Callable[[], httpx.AsyncClient],
        clock: Callable[[], datetime],
        rpc_path: str,
        max_message_bytes: int,
        max_pending: int,
    ) -> None:
        if max_message_bytes <= 0:
            raise ValueError(
                "max_message_bytes must be positive; a zero message limit"
                " accepts nothing"
            )
        if max_pending <= 0:
            raise ValueError(
                "max_pending must be positive; a zero queue bound accepts"
                " nothing"
            )
        self._local_peer_id = local_peer_id
        self._agent_card = agent_card
        self._cards = cards
        self._http_client_factory = http_client_factory
        self._clock = clock
        self._rpc_path = rpc_path
        self._max_message_bytes = max_message_bytes
        self._max_pending = max_pending
        self._received: deque[InboundProduct] = deque()

    @property
    def local_peer_id(self) -> str:
        """This deployment's own identifier on the wire."""
        return self._local_peer_id

    @property
    def rpc_path(self) -> str:
        """The route :meth:`routes` mounts the JSON-RPC endpoint at."""
        return self._rpc_path

    @property
    def agent_card(self) -> AgentCard:
        """This deployment's Agent Card, as the caller supplied it."""
        return self._agent_card

    # -- the client leg -----------------------------------------------------

    def emit(
        self, *, peer: PeerRef, signed: SignedContextProduct
    ) -> EmitReceipt:
        """Carry ``signed`` to ``peer``.

        See :meth:`ccf.peering.protocol.PeeringProtocol.emit`.

        The synchronous facade over :meth:`emit_async`, offered because the
        fabric core is synchronous (D-IMPL-04(b)) while ``a2a-sdk``'s client is
        not. It owns the loop it runs on rather than borrowing one.

        Raises:
            PeerUnreachable: no base URL is known for ``peer``, the peer's card
                could not be resolved, the peer could not be reached, or it
                answered with a protocol error.
            MalformedWireMessage: the peer accepted the carriage but returned no
                carriage identifier, so there is nothing to correlate on.
            RuntimeError: called from inside a running event loop. Refused
                rather than worked around: an async caller has
                :meth:`emit_async`, and quietly nesting loops is how a transport
                deadlocks a host.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.emit_async(peer=peer, signed=signed))
        raise RuntimeError(
            "LfA2AWire.emit was called from a running event loop; use"
            " emit_async, which is the same carriage without a nested loop"
        )

    async def emit_async(
        self, *, peer: PeerRef, signed: SignedContextProduct
    ) -> EmitReceipt:
        """Carry ``signed`` to ``peer`` over LF A2A and return the receipt.

        Discovery, then carriage: the peer's base URL resolves through
        :class:`PeerCardResolver`, :class:`a2a.client.A2ACardResolver` fetches
        the peer's real card from it, and :class:`a2a.client.ClientFactory`
        builds the client the card's declared binding calls for. None of that is
        re-implemented here, which is the whole reason for choosing a standard
        with an SDK.

        The envelope is serialized canonically once and placed in a single
        ``Part.raw``, so its ``payload`` member — the base64url of the bytes the
        producer signed — crosses as the same characters. Nothing here decodes
        it.

        The returned receipt acknowledges *transport only*. Whether the far side
        admitted the product is the far side's Control Plane decision, reached
        after this call returns, and this receipt says nothing about it.

        Raises:
            PeerUnreachable: see :meth:`emit`.
            MalformedWireMessage: see :meth:`emit`.
        """
        base_url = self._cards(peer=peer)
        body = canonical_bytes(signed)
        if len(body) > self._max_message_bytes:
            raise MalformedWireMessage(
                f"the envelope for peer {peer.peer_id!r} is {len(body)} bytes,"
                f" over this transport's {self._max_message_bytes}-byte limit"
            )
        message = Message(
            message_id=self._carriage_id(peer_id=self._local_peer_id, signed=signed),
            role=Role.ROLE_USER,
            parts=[Part(raw=body, media_type=SIGNED_PRODUCT_MEDIA_TYPE)],
        )
        message.metadata.update(
            {
                PEER_ID_METADATA: self._local_peer_id,
                PEER_TENANT_METADATA: peer.tenant_id,
            }
        )

        async with self._http_client_factory() as http_client:
            card = await self._resolve_card(
                peer=peer, base_url=base_url, http_client=http_client
            )
            client = ClientFactory(
                ClientConfig(
                    httpx_client=http_client,
                    streaming=False,
                    supported_protocol_bindings=[JSONRPC_BINDING],
                )
            ).create(card)
            try:
                wire_message_id = await self._send(
                    client=client, peer=peer, message=message
                )
            finally:
                await client.close()

        return EmitReceipt(
            peer=peer,
            content_address=signed.content_address(),
            wire_message_id=wire_message_id,
        )

    async def _resolve_card(
        self, *, peer: PeerRef, base_url: str, http_client: httpx.AsyncClient
    ) -> AgentCard:
        """Fetch ``peer``'s Agent Card from its well-known path.

        Discovery, not trust (T-06-55): the card states where and how the peer
        answers, and nothing this transport reads from it can make an unentitled
        product admissible. The gate resolves the signing key from the
        consuming tenant's trust-policy artifact by the ``kid`` inside the
        signature, which no card contributes to.

        Raises:
            PeerUnreachable: the card could not be fetched or did not parse.
        """
        resolver = A2ACardResolver(httpx_client=http_client, base_url=base_url)
        try:
            return await resolver.get_agent_card()
        except Exception as failure:  # noqa: BLE001 - see below
            # Deliberately broad: `a2a-sdk` surfaces card-resolution failures as
            # its own error type, `httpx` transport errors, and validation
            # errors, and a caller's response to all three is identical — this
            # peer cannot be reached right now. Narrowing here would mean
            # tracking a vendor's exception taxonomy in CCF's transport
            # hierarchy, and a miss would surface as an untyped crash rather
            # than as the operational condition it is.
            raise PeerUnreachable(
                f"peer {peer.peer_id!r}'s agent card could not be resolved at"
                f" {base_url!r}: {failure}"
            ) from failure

    async def _send(
        self, *, client: Client, peer: PeerRef, message: Message
    ) -> str:
        """Send one message and return the peer's carriage identifier.

        Raises:
            PeerUnreachable: the peer could not be reached or answered with a
                protocol error — which, on this wire, is what a refused frame
                looks like from the sending side.
            MalformedWireMessage: the peer accepted the carriage without
                returning an identifier.
        """
        request = SendMessageRequest(message=message)
        try:
            responses = [
                response async for response in client.send_message(request)
            ]
        except Exception as failure:  # noqa: BLE001 - see _resolve_card
            raise PeerUnreachable(
                f"peer {peer.peer_id!r} refused the carriage: {failure}"
            ) from failure
        for response in responses:
            if response.WhichOneof("payload") != "message":
                continue
            identifier = response.message.message_id
            if identifier:
                return str(identifier)
        raise MalformedWireMessage(
            f"peer {peer.peer_id!r} accepted the carriage without returning a"
            " carriage identifier"
        )

    # -- the receiving leg --------------------------------------------------

    def receive(self) -> Iterator[InboundProduct]:
        """Yield and drain what this endpoint has queued, oldest first.

        Draining rather than peeking is what makes a second call return the
        *next* messages rather than the same ones again; a caller that handed the
        same product to the gate twice would audit two verdicts for one carriage.

        Nothing is dispatched anywhere. An implementation that delivered products
        somewhere would have to know where the fabric begins, and the whole point
        of D-12 is that a transport does not.
        """
        while self._received:
            yield self._received.popleft()

    def routes(self) -> Sequence[BaseRoute]:
        """Build the JSON-RPC and Agent Card routes for this transport.

        Routes rather than a started server, and no bind address chosen here:
        hosting is the deployment's decision, and a library that picked an
        interface would be picking an exposure surface. Both route sets come
        from ``a2a-sdk`` — this module composes them and writes none of them.

        **The JSON-RPC route reads at most ``max_message_bytes`` of a request
        body before ``a2a-sdk`` parses it** (SEC-021-U1, ``D-IMPL-370`` (3)).
        Its dispatcher reads and parses the whole body before :meth:`_accept`
        runs, so the route's application is wrapped in a body limit. This is
        the same composition Starlette's own per-route ``middleware=`` performs.
        A declared ``Content-Length`` over the limit is answered 413 without
        the body being read. A body is otherwise counted as it arrives and
        answered 413 the moment the count crosses the limit. Over the limit the
        dispatcher is never called. The Agent Card routes answer ``GET`` and
        read no body, so they are mounted as given.

        Raises:
            TypeError: ``a2a-sdk`` built its JSON-RPC endpoint as something
                other than a :class:`starlette.routing.Route`, so this
                transport cannot put the limit in front of it. Refused rather
                than mounted unbounded.
        """
        handler = DefaultRequestHandler(
            agent_executor=_InboundExecutor(wire=self),
            task_store=InMemoryTaskStore(),
            agent_card=self._agent_card,
        )
        # Typed as the base class on purpose: the check in `_bounded` guards
        # against a vendor change at run time, and must not read as unreachable.
        jsonrpc: Sequence[BaseRoute] = create_jsonrpc_routes(handler, self._rpc_path)
        return [
            *create_agent_card_routes(self._agent_card),
            *(self._bounded(route) for route in jsonrpc),
        ]

    def _bounded(self, route: BaseRoute) -> Route:
        """Put the request-body limit in front of one ``a2a-sdk`` JSON-RPC route.

        The route's own application is wrapped in place, so whatever
        ``a2a-sdk`` composed on the route stays behind the limit.

        Raises:
            TypeError: see :meth:`routes`.
        """
        if not isinstance(route, Route):
            raise TypeError(
                f"a2a-sdk built its JSON-RPC endpoint as a {type(route).__name__},"
                " not a starlette Route, so its request body cannot be held to"
                " max_message_bytes before it is parsed; refusing to mount it"
                " unbounded (SEC-021-U1)"
            )
        route.app = _RequestBodyLimit(route.app, max_bytes=self._max_message_bytes)
        return route

    def _enqueue(self, inbound: InboundProduct) -> None:
        """Queue one framed envelope for :meth:`receive` to yield, or refuse it.

        Called only after :meth:`_accept` has framed the message and minted its
        carriage identifier. The bound is checked immediately before the
        append, so the queue never holds more than ``max_pending`` even
        momentarily, and a full queue refuses the *newcomer*: the messages
        already queued are neither evicted nor reordered (SEC-021,
        ``D-IMPL-369``).

        Raises:
            ReceiveQueueFull: the queue already holds ``max_pending`` messages.
        """
        if len(self._received) >= self._max_pending:
            raise ReceiveQueueFull.at_bound(
                held=len(self._received),
                bound=self._max_pending,
                peer_id=inbound.observed_peer.peer_id,
            )
        self._received.append(inbound)

    def _accept(self, message: Message) -> tuple[InboundProduct, str]:
        """Frame one inbound message, or refuse the frame.

        Four framing checks, and they are framing checks only — the part's
        content alternative and media type, the carried size, the declared peer
        metadata, and whether the bytes parse as a signed product. None of them
        inspects the signature, the trust policy, or the peer's entitlements;
        those belong to the Control Plane gate the caller runs over what
        :meth:`receive` yields (D-12).

        Raises:
            MalformedWireMessage: the message is not one carried signed product
                the size limit admits.
        """
        body = self._carried_bytes(message)
        metadata = dict(message.metadata)
        peer_id = metadata.get(PEER_ID_METADATA)
        tenant_id = metadata.get(PEER_TENANT_METADATA)
        if not isinstance(peer_id, str) or not peer_id:
            raise MalformedWireMessage(
                f"the carriage declares no {PEER_ID_METADATA}"
            )
        if not isinstance(tenant_id, str) or not tenant_id:
            raise MalformedWireMessage(
                f"the carriage declares no {PEER_TENANT_METADATA}"
            )
        try:
            signed = SignedContextProduct.model_validate_json(body)
        except ValidationError as failure:
            raise MalformedWireMessage(
                f"the carriage from {peer_id!r} does not parse as a signed"
                f" context product: {failure}"
            ) from failure
        inbound = InboundProduct(
            observed_peer=PeerRef(tenant_id=tenant_id, peer_id=peer_id),
            signed=signed,
        )
        return inbound, self._carriage_id(peer_id=peer_id, signed=signed)

    def _carried_bytes(self, message: Message) -> bytes:
        """Return the one carried document's bytes, or refuse the frame.

        Exactly one part is expected, and it must be the ``raw`` alternative at
        the declared media type. A message carrying several parts, or a text or
        structured part, is not a CCF carriage — and in particular a ``data``
        part is refused outright rather than coerced, because Struct's JSON value
        model does not preserve the bytes a signature was made over.

        Raises:
            MalformedWireMessage: the message does not carry exactly one
                admissible raw part within the size limit.
        """
        parts = list(message.parts)
        if len(parts) != 1:
            raise MalformedWireMessage(
                f"a carriage carries exactly one part; this one carried"
                f" {len(parts)}"
            )
        part = parts[0]
        if part.WhichOneof(_PART_CONTENT_ONEOF) != _RAW_ALTERNATIVE:
            raise MalformedWireMessage(
                "a carriage carries its envelope as raw bytes; this one carried"
                f" {part.WhichOneof(_PART_CONTENT_ONEOF)!r}"
            )
        if part.media_type != SIGNED_PRODUCT_MEDIA_TYPE:
            raise MalformedWireMessage(
                f"a carriage declares {SIGNED_PRODUCT_MEDIA_TYPE!r}; this one"
                f" declared {part.media_type!r}"
            )
        if len(part.raw) > self._max_message_bytes:
            raise MalformedWireMessage(
                f"the carried envelope is {len(part.raw)} bytes, over this"
                f" transport's {self._max_message_bytes}-byte limit"
            )
        return bytes(part.raw)

    def _carriage_id(
        self, *, peer_id: str, signed: SignedContextProduct
    ) -> str:
        """Mint this carriage's identifier: who, when, and over what bytes.

        Derived rather than random so a receipt is reproducible from the message
        and the injected clock, and opaque to CCF by construction — nothing in
        the fabric interprets it.

        Raises:
            MalformedWireMessage: the envelope's payload member is not base64url,
                so it has no content address to name.
        """
        try:
            address = signed.content_address()
        except SignatureMalformed as failure:
            raise MalformedWireMessage(
                f"the message from {peer_id!r} carries no addressable payload:"
                f" {failure}"
            ) from failure
        return f"{peer_id}/{self._clock().isoformat()}/{address}"
