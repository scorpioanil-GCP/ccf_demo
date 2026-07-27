"""``TypedHttpWire`` — the first :class:`~ccf.a2a.wire.WireProtocol` (D-11).

SDK-defined extension (CLAUDE.md §7.2 — "A2A federation is first-class in v0"),
attaching to whitepaper §8.3 Pattern 4. D-IMPL-14 rules the v0 *default* wire
and commits the abstraction itself; this module is the abstraction's first
concrete implementation and deliberately depends on no wire standard at all.
Sequencing it first is what makes the abstraction, the Control Plane gate, the
identity primitives and the cross-process fixture provable independently of any
emergent standard — CLAUDE.md §7.2 puts it plainly: **the Context Product
Contract is the stable layer; the wire is replaceable.**

**What this transport is not.** It is not the fabric, and it is not a protocol
specification. It is an HTTP client leg and an ASGI receive endpoint over the
CCF types :mod:`ccf.a2a.wire` declares. Nothing about the shape below is
normative for federation between organisations; what is normative is the
signed, canonical Context Product it carries, which is identical whichever
transport carries it.

**What this transport does not check.** It performs no admission check of any
kind. It does not verify a signature, does not read a trust policy, and does
not decide whether a peer may send what it sent. It hands what it received to
its caller, and the caller hands that to the Control Plane gate
(:mod:`ccf.a2a.admission`). Putting the check inside a ``WireProtocol``
implementation was explicitly rejected by D-12: two transports ship this phase
and more may follow, and a per-transport check states the rule once per wire —
which lets a later wire state it differently, or omit it. The rule therefore
sits above all of them, and this module is handed no way to reach past it. This
paragraph is the only place in this file that names that gate's module at all;
every check the code below *does* perform is a framing check, named as such.

**What this transport cannot do.** It holds no graph write handle, no graph
store, and no assembly worker. There is no constructor parameter, attribute,
method parameter, or return type here that is or names one, and this module
imports nothing from the L3 graph package or from L2. The honest claim (D-21)
is the structural one rather than an absolute one: what this module's declared
surface offers is an outbound POST and an inbound queue of
:class:`~ccf.a2a.wire.InboundProduct` values, and an ``InboundProduct`` is not
what L2 accepts. ``tests/invariants/test_a2a_single_writer.py`` is what holds
that — by import scan, by identifier scan, and by attribute inspection of a
constructed instance — rather than this paragraph.

**Canonical bytes travel verbatim.** The body is the canonical serialization of
the :class:`~ccf.a2a.identity.SignedContextProduct` itself, whose ``payload``
member is already base64url text. The product's own canonical bytes are
therefore never decoded, re-encoded, re-serialized, or round-tripped through an
intermediate model anywhere in this module — they cross as the same characters
the producer signed. That is the whole reason the envelope is carried as one
document rather than split into a raw body plus header metadata: a split would
put this transport in the business of base64url, and the signature is made over
exactly those bytes.

**Deployment values are the caller's.** The peer endpoint, the bind address,
the port, the route path, the HTTP client and its timeouts, and the request-body
ceiling are all supplied by the caller. This module holds no address, no port,
no scheme literal and no default ceiling (CINV-01, D-IMPL-38). Tenancy is a
per-call argument carried on :class:`~ccf.a2a.wire.PeerRef`, never a
constructor field, on the :class:`~ccf_runtime.cdc.adapter.CDCSourceAdapter`
precedent: one transport serving a shared fabric must not be able to emit into
the wrong tenant by positional accident.

**The body ceiling here is defence in depth, not the rule.** The authoritative
ceiling is the Control Plane's ``InboundPayloadCeiling``, applied by the gate
against the declared payload member before anything canonicalizes it. This
module's limit exists so a hostile peer cannot make the *receiving process*
buffer an unbounded body before the gate ever sees a value, and it is stated as
a required constructor argument so no deployment gets one it did not choose.

Algorithmic module (CINV-03): framing, transport and typed conversion only.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterator
from datetime import datetime
from typing import Protocol, runtime_checkable

import httpx
from pydantic import ValidationError
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from ccf.a2a.identity import SignatureMalformed, SignedContextProduct
from ccf.a2a.wire import EmitReceipt, InboundProduct, PeerRef
from ccf.contracts.canonical import canonical_bytes

__ccf_mode__ = "algorithmic"

__all__ = [
    "PEER_ID_HEADER",
    "PEER_TENANT_HEADER",
    "SIGNED_PRODUCT_MEDIA_TYPE",
    "WIRE_MESSAGE_ID_HEADER",
    "MalformedWireMessage",
    "PeerEndpointResolver",
    "PeerUnreachable",
    "TypedHttpWire",
    "WireTransportError",
]

#: Media type of the carried document. Names *what was sent* — a signed
#: canonical Context Product — so a receiver that was handed some other CCF
#: artifact refuses it at the frame rather than at the contract.
SIGNED_PRODUCT_MEDIA_TYPE = "application/ccf-signed-product+json"

#: The header a sender states its own peer identifier under. Read as a claim
#: and nothing more: it selects which trust-policy entry the Control Plane will
#: read, and it proves nothing. What binds a product to a principal is the
#: signature, which this module never checks.
PEER_ID_HEADER = "ccf-peer-id"

#: The header a sender states the federation tenant under. Also a claim; the
#: gate is tenant-scoped at construction and compares the *product's* tenant
#: against its own, so a lie here changes which gate refuses, never whether one
#: does.
PEER_TENANT_HEADER = "ccf-peer-tenant"

#: The header the receiver returns its carriage identifier under. Minted by the
#: receiving side because that is the side that can say a carriage happened.
WIRE_MESSAGE_ID_HEADER = "ccf-wire-message-id"

#: What the receive endpoint answers with once a well-framed message is queued.
#: "Accepted", never "OK": this transport has taken custody of bytes and has
#: decided nothing about them.
_ACCEPTED_STATUS = 202

#: Answered when the frame itself is unusable — wrong media type, oversized
#: body, missing peer header, or a body that is not a signed product.
_MALFORMED_STATUS = 400

#: Answered when the declared or streamed body exceeds this transport's limit.
_TOO_LARGE_STATUS = 413


class WireTransportError(RuntimeError):
    """Base of the typed transport failures.

    Typed rather than bare because a caller's response differs per case: a peer
    that cannot be reached is an operational condition, whereas a peer that
    answered with something unusable is a federation-configuration condition. A
    caller that conflated them would page on a misconfiguration and retry a
    protocol mismatch forever.

    None of these is a governance verdict. A governance verdict is a value the
    Control Plane gate returns; a transport failure means no verdict was ever
    reached, and the two must not be reported through the same channel.
    """


class PeerUnreachable(WireTransportError):
    """The peer's endpoint could not be reached, or refused the carriage."""


class MalformedWireMessage(WireTransportError):
    """A message did not frame as a carried signed product.

    Raised on the receiving side for a body that is not a valid
    :class:`~ccf.a2a.identity.SignedContextProduct`, and on the sending side for
    a response that carried no identifier. Framing only — the signature over
    the payload is somebody else's question.
    """


@runtime_checkable
class PeerEndpointResolver(Protocol):
    """Where a peer is reachable, as far as *this* deployment is concerned.

    A seam rather than a field on :class:`~ccf.a2a.wire.PeerRef`, because a
    ``PeerRef`` deliberately is not an address: trust keys on identity, and an
    identity that embedded an endpoint would make trust a property of where a
    message arrived from. Endpoints are deployment topology and change without
    the federation changing, so they are resolved per emission by something the
    deployment supplies.

    ``runtime_checkable`` supports composition-root wiring checks; it verifies
    method presence only, so static conformance still rests on mypy.
    """

    def __call__(self, *, peer: PeerRef) -> str:
        """Return the URL this deployment reaches ``peer`` at.

        Raises:
            PeerUnreachable: this deployment knows no endpoint for that peer.
        """
        ...


class TypedHttpWire:
    """A :class:`~ccf.a2a.wire.WireProtocol` over plain typed HTTP (D-11).

    Symmetric by construction: one instance is both the client leg that emits
    and the owner of the receive endpoint that queues what arrives. A
    deployment that only sends never hosts :meth:`asgi_app`, and one that only
    receives never calls :meth:`emit`; neither case needs a second type.

    Args:
        local_peer_id: This deployment's own identifier on the wire, stated on
            every outbound message. Identity, never location — the same
            discipline :class:`~ccf.signal.envelope.SourceIdentity` applies to
            L1 sources. There is no tenant beside it: tenancy rides on the
            ``PeerRef`` passed to :meth:`emit`, keyword-only, so a shared
            transport cannot emit into the wrong tenant positionally.
        endpoints: How a peer identity becomes a URL for this deployment.
        http_client: The client the outbound leg uses. Injected rather than
            constructed, because timeouts, transport security, proxies and
            connection limits are deployment infrastructure and the SDK has no
            business choosing them (CLAUDE.md §13).
        clock: The receiving side's time source, injected. Nothing here reads a
            wall clock: the received instant lands in the carriage identifier,
            and a hidden clock would make that identifier untestable.
        receive_path: The route the endpoint is mounted at. A deployment value
            with no default — a library that picked a path would be picking a
            piece of a deployment's URL space.
        max_request_bytes: The largest body this endpoint will buffer. No
            default (D-IMPL-38): how large a legitimate federated product is, is
            something only the deployment knows, and a limit nobody chose is
            either an availability hole or an outage. See the module docstring
            for why this is defence in depth and not the authoritative ceiling.

    Raises:
        ValueError: ``max_request_bytes`` is not positive. A zero limit accepts
            nothing and is far more likely a mistake than a policy.
    """

    def __init__(
        self,
        *,
        local_peer_id: str,
        endpoints: PeerEndpointResolver,
        http_client: httpx.Client,
        clock: Callable[[], datetime],
        receive_path: str,
        max_request_bytes: int,
    ) -> None:
        if max_request_bytes <= 0:
            raise ValueError(
                "max_request_bytes must be positive; a zero body limit accepts"
                " nothing"
            )
        self._local_peer_id = local_peer_id
        self._endpoints = endpoints
        self._http_client = http_client
        self._clock = clock
        self._receive_path = receive_path
        self._max_request_bytes = max_request_bytes
        self._received: deque[InboundProduct] = deque()

    @property
    def local_peer_id(self) -> str:
        """This deployment's own identifier on the wire."""
        return self._local_peer_id

    @property
    def receive_path(self) -> str:
        """The route :meth:`asgi_app` mounts the endpoint at."""
        return self._receive_path

    # -- the client leg -----------------------------------------------------

    def emit(
        self, *, peer: PeerRef, signed: SignedContextProduct
    ) -> EmitReceipt:
        """Carry ``signed`` to ``peer``; see :meth:`ccf.a2a.wire.WireProtocol.emit`.

        The envelope is serialized canonically and sent as one document, so its
        ``payload`` member — which is the base64url of the bytes the producer
        signed — crosses as the same characters. Nothing here decodes it.

        The returned receipt acknowledges *transport only*. Whether the far
        side admitted the product is the far side's Control Plane decision,
        reached after this call returns, and this receipt says nothing about it.

        Raises:
            PeerUnreachable: no endpoint is known for ``peer``, the endpoint
                could not be reached, or it answered with a failure status.
            MalformedWireMessage: the peer accepted the carriage but returned
                no carriage identifier, so there is nothing to correlate on.
        """
        endpoint = self._endpoints(peer=peer)
        body = canonical_bytes(signed)
        try:
            response = self._http_client.post(
                endpoint,
                content=body,
                headers={
                    "content-type": SIGNED_PRODUCT_MEDIA_TYPE,
                    PEER_ID_HEADER: self._local_peer_id,
                    PEER_TENANT_HEADER: peer.tenant_id,
                },
            )
        except httpx.HTTPError as failure:
            raise PeerUnreachable(
                f"peer {peer.peer_id!r} could not be reached: {failure}"
            ) from failure
        if response.status_code != _ACCEPTED_STATUS:
            raise PeerUnreachable(
                f"peer {peer.peer_id!r} refused the carriage with status"
                f" {response.status_code}"
            )
        wire_message_id = response.headers.get(WIRE_MESSAGE_ID_HEADER)
        if not wire_message_id:
            raise MalformedWireMessage(
                f"peer {peer.peer_id!r} accepted the carriage without"
                f" returning a {WIRE_MESSAGE_ID_HEADER} identifier"
            )
        return EmitReceipt(
            peer=peer,
            content_address=signed.content_address(),
            wire_message_id=wire_message_id,
        )

    # -- the receiving leg --------------------------------------------------

    def receive(self) -> Iterator[InboundProduct]:
        """Yield and drain what this endpoint has queued, oldest first.

        Draining rather than peeking is what makes a second call return the
        *next* messages rather than the same ones again; a caller that handed
        the same product to the gate twice would audit two verdicts for one
        carriage.

        Nothing is dispatched anywhere. An implementation that delivered
        products somewhere would have to know where the fabric begins, and the
        whole point of D-12 is that a transport does not.
        """
        while self._received:
            yield self._received.popleft()

    def asgi_app(self) -> Starlette:
        """Build the ASGI application hosting this transport's endpoint.

        Deliberately *not* started, and no bind address is chosen here: hosting
        is the deployment's decision, and a library that picked an interface
        would be picking an exposure surface.
        """
        return Starlette(
            routes=[
                Route(
                    self._receive_path,
                    self._handle_receive,
                    methods=["POST"],
                )
            ]
        )

    async def _handle_receive(self, request: Request) -> Response:
        """Frame one inbound message and queue it, or refuse the frame.

        Four framing checks, and they are framing checks only — media type,
        body size, the declared peer header, and whether the body parses as a
        signed product. None of them inspects the signature, the trust policy,
        or the peer's entitlements; those belong to the Control Plane gate the
        caller runs over what :meth:`receive` yields (D-12).
        """
        media_type = request.headers.get("content-type", "")
        if media_type.split(";")[0].strip() != SIGNED_PRODUCT_MEDIA_TYPE:
            return Response(status_code=_MALFORMED_STATUS)

        declared_length = request.headers.get("content-length")
        if declared_length is not None and declared_length.isdigit():
            if int(declared_length) > self._max_request_bytes:
                return Response(status_code=_TOO_LARGE_STATUS)

        # Streamed and counted rather than `await request.body()`: a peer that
        # declares a small length and then sends more would otherwise be
        # buffered in full before anything looked at the size.
        chunks: list[bytes] = []
        received_bytes = 0
        async for chunk in request.stream():
            received_bytes += len(chunk)
            if received_bytes > self._max_request_bytes:
                return Response(status_code=_TOO_LARGE_STATUS)
            chunks.append(chunk)
        body = b"".join(chunks)

        peer_id = request.headers.get(PEER_ID_HEADER, "")
        tenant_id = request.headers.get(PEER_TENANT_HEADER, "")
        if not peer_id or not tenant_id:
            return Response(status_code=_MALFORMED_STATUS)

        try:
            signed = SignedContextProduct.model_validate_json(body)
        except ValidationError:
            return Response(status_code=_MALFORMED_STATUS)

        inbound = InboundProduct(
            observed_peer=PeerRef(tenant_id=tenant_id, peer_id=peer_id),
            signed=signed,
        )
        self._received.append(inbound)
        return Response(
            status_code=_ACCEPTED_STATUS,
            headers={
                WIRE_MESSAGE_ID_HEADER: self._carriage_id(
                    peer_id=peer_id, signed=signed
                )
            },
        )

    def _carriage_id(
        self, *, peer_id: str, signed: SignedContextProduct
    ) -> str:
        """Mint this carriage's identifier: who, when, and over what bytes.

        Derived rather than random so a receipt is reproducible from the
        message and the injected clock, and opaque to CCF by construction —
        nothing in the fabric interprets it.

        Raises:
            MalformedWireMessage: the queued envelope's payload member is not
                base64url, so it has no content address to name.
        """
        try:
            address = signed.content_address()
        except SignatureMalformed as failure:
            raise MalformedWireMessage(
                f"the message from {peer_id!r} carries no addressable payload:"
                f" {failure}"
            ) from failure
        return f"{peer_id}/{self._clock().isoformat()}/{address}"
