"""SEC-021-U1 (``D-IMPL-370`` (3)): the LF A2A leg bounds a request body before
``a2a-sdk`` parses it.

SEC-021, as worded: "Unauthenticated A2A receive appends to an unbounded
``deque`` before any signature check; **on the LF leg the body is parsed before
``max_message_bytes`` is consulted**." Remedy: "Cap before buffering; move the
size check ahead of parsing." Clause 1, the queue, is closed and evidenced in
``test_receive_is_bounded_before_verification.py``. This module is clause 2,
which ``D-IMPL-370`` (3) carried as ``SEC-021-U1``.

Measured before this module, at ``8fceec83``: ``LfA2AWire.routes()`` mounted
``a2a-sdk``'s JSON-RPC route as given. Its
``JsonRpcDispatcher.handle_requests`` begins with ``await request.json()``,
which reads the whole body and parses it before this transport's ``_accept``
ever consults ``max_message_bytes``. A body of four times the declared limit
was read in full and parsed, and its carriage was queued.

The ruled remedy is a size-limiting layer in front of the dispatcher. (a) When
``Content-Length`` exceeds the limit, it answers 413 without reading the body.
(b) It counts the bytes as ``receive()`` yields them and answers 413 the moment
the count exceeds the limit, so the dispatcher never parses more than the
limit.

**Which limit: mechanism parity with the typed leg** (the ruling on the first
round, which held the body to ``max_message_bytes``). The JSON-RPC binding
carries the document base64-encoded inside the request, so a body held to the
document limit refused documents the document limit admits. The LF leg
therefore declares two limits, as the ruling sets them: ``max_request_bytes``,
required with no default, bounds the HTTP request body before parsing, and
``max_message_bytes`` keeps bounding only the decoded document, after parsing.
The SDK derives neither from the other.

How it is observed:

* The app is driven in-process through a raw ASGI ``receive``/``send`` pair,
  with no socket. The test therefore controls the declared length and the
  chunking, and it counts the body bytes the app pulls from the peer.
* ``JsonRpcDispatcher.handle_requests`` is instrumented before ``routes()``
  builds the route, and each entry records the body bytes delivered to it.
  Over the limit it must record nothing. The at-limit control is the positive
  control: it proves the instrument sees the dispatcher when the dispatcher is
  reached, so an empty record means "never reached", not "never watched".
* Every body is a well-formed JSON-RPC ``SendMessage`` carrying a
  garbage-signed envelope, padded with JSON whitespace to the exact length
  under test. On the unfixed tree the over-limit body is therefore not merely
  read but parsed, framed and queued, which is the defect at its worst.
* The over-limit cases declare a document limit larger than every body they
  send, so the only limit that can refuse those bodies before parsing is
  ``max_request_bytes``. A layer that held the body to ``max_message_bytes``
  would let them through. The exchange case runs the other way: a document of
  exactly ``max_message_bytes``, between two identically configured peers, is
  refused if the body is held to the document limit.
* The wire is built with ``max_request_bytes`` only when the constructor
  declares it (``_lf_wire``). On a tree whose constructor does not, the red is
  the behavior rather than a ``TypeError``, and each case that depends on the
  body limit then pins that the parameter was declared.

The typed-HTTP leg is measured here too, with the same three shapes, against
``SignedContextProduct.model_validate_json``. That leg streams and counts the
body itself before it parses, so it has no pre-parse gap, and its cases pass
on the unfixed tree as well. They pin that measurement; they do not claim a
red.
"""

from __future__ import annotations

import asyncio
import base64
import inspect
import json
import re
from collections.abc import Awaitable, Callable, Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml
from a2a.server.routes.jsonrpc_dispatcher import JsonRpcDispatcher
from a2a.types import Message, Part, Role, SendMessageRequest
from a2a.utils.constants import PROTOCOL_VERSION_CURRENT, VERSION_HEADER
from google.protobuf.json_format import MessageToDict
from starlette.applications import Starlette
from starlette.routing import Mount

from ccf.contracts.canonical import canonical_bytes
from ccf.peering.identity import SignedContextProduct
from ccf.peering.protocol import EmitReceipt, PeerRef
from ccf_runtime.peering import lf_a2a
from ccf_runtime.peering.lf_a2a import (
    PEER_ID_METADATA,
    PEER_TENANT_METADATA,
    SIGNED_PRODUCT_MEDIA_TYPE,
    LfA2AWire,
    build_agent_card,
)
from ccf_runtime.peering.typed_http import (
    PEER_ID_HEADER,
    PEER_TENANT_HEADER,
    PeerUnreachable,
    TypedHttpWire,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "banking"
FEDERATION: dict[str, Any] = yaml.safe_load(
    (FIXTURES / "a2a.yaml").read_text(encoding="utf-8")
)
CONSUMER = FEDERATION["consumer"]
LF_A2A = FEDERATION["lf_a2a"]
SENDER_ID = FEDERATION["peers"]["first"]["peer_id"]

_TENANT = "tenant-under-test"
_INSTANT = datetime(2026, 3, 1, tzinfo=UTC)
_BASE = "http://receiver.invalid"

#: Body bytes per ASGI ``http.request`` message in the streamed cases. Small,
#: so the point at which a reader stops is observable to within one chunk.
CHUNK = 16

#: Room above the smallest well-formed body, so a body can be padded to exactly
#: the limit. A test parameter, not a recommendation.
_MARGIN = 64

#: How far past the limit the streamed bodies run. Far enough that "read the
#: whole body" and "stopped at the limit" cannot be confused.
_OVERRUN = 4

#: How long one in-process exchange may take before the test fails rather than
#: hangs.
_DEADLINE_SECONDS = 10.0

#: The JSON-RPC method a carriage is sent under, as ``a2a-sdk`` routes it.
_SEND_MESSAGE = "SendMessage"

#: What each LF case pins last: the body limit is a declared parameter.
_UNDECLARED = "LfA2AWire does not declare max_request_bytes"

#: The typed leg's refusal of a non-positive body limit, word for word. The
#: ruling gives the LF leg the same validation and the same wording.
_NON_POSITIVE_BODY_LIMIT = re.escape(
    "max_request_bytes must be positive; a zero body limit accepts nothing"
)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _garbage_envelope() -> SignedContextProduct:
    """A well-framed envelope whose signature verifies against nothing.

    The payload member is genuine base64url, so the carriage has a content
    address and frames cleanly; the protected header and the signature are not
    a JWS. Nothing on the receive path verifies either, which is the point.
    """
    payload = json.dumps({"carriage": "over-limit"}, sort_keys=True).encode("utf-8")
    return SignedContextProduct(
        payload=_b64url(payload),
        protected=_b64url(b"not-a-jws-header"),
        signature=_b64url(b"not-a-signature"),
    )


def _document_of_exactly(size: int) -> SignedContextProduct:
    """A garbage-signed envelope whose canonical bytes are exactly ``size`` long.

    The signature member verifies against nothing either way, so it is padded
    with base64url characters until the document is the size under test.
    """
    base = _garbage_envelope()
    shortfall = size - len(canonical_bytes(base))
    assert shortfall >= 0, f"{size} is smaller than the unpadded envelope"
    document = SignedContextProduct(
        payload=base.payload,
        protected=base.protected,
        signature=base.signature + "A" * shortfall,
    )
    assert len(canonical_bytes(document)) == size
    return document


def _jsonrpc_body() -> bytes:
    """The smallest well-formed JSON-RPC ``SendMessage`` carrying the envelope.

    Built from ``a2a-sdk``'s own generated types and protobuf's JSON mapping,
    the same way its client builds one, so the dispatcher accepts it as a
    genuine carriage when it is reached.
    """
    message = Message(
        message_id="carriage-under-test",
        role=Role.ROLE_USER,
        parts=[
            Part(
                raw=canonical_bytes(_garbage_envelope()),
                media_type=SIGNED_PRODUCT_MEDIA_TYPE,
            )
        ],
    )
    message.metadata.update(
        {PEER_ID_METADATA: SENDER_ID, PEER_TENANT_METADATA: _TENANT}
    )
    assert JsonRpcDispatcher.METHOD_TO_MODEL[_SEND_MESSAGE] is SendMessageRequest
    document = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": _SEND_MESSAGE,
        "params": MessageToDict(SendMessageRequest(message=message)),
    }
    return json.dumps(document).encode("utf-8")


#: The LF leg's body limit under test (``max_request_bytes``): the smallest
#: well-formed body plus room to pad it.
LF_LIMIT = len(_jsonrpc_body()) + _MARGIN

#: The document limit the LF cases declare by default (``max_message_bytes``).
#: Deliberately larger than every body they send, so the only limit that can
#: refuse an over-limit body before parsing is ``max_request_bytes``. Were the
#: body held to ``max_message_bytes`` instead, those bodies would pass it and be
#: parsed. A test configuration, not a recommendation: a deployment's document
#: limit sits below its body limit.
LF_DOCUMENT_LIMIT = 2 * _OVERRUN * LF_LIMIT

#: The typed leg's declared limit under test, on the same rule, for its own
#: body (the canonical envelope itself). Set as its ``max_request_bytes``.
TYPED_LIMIT = len(canonical_bytes(_garbage_envelope())) + _MARGIN

#: The exchange case's document limit (``max_message_bytes``), on both peers.
_EXCHANGE_DOCUMENT_LIMIT = 4096

#: The exchange case's body limit (``max_request_bytes``), on both peers: the
#: test's own declaration, large enough for the JSON-RPC request that carries a
#: document of ``_EXCHANGE_DOCUMENT_LIMIT`` bytes base64-encoded. The test
#: measures that request and asserts it fits, rather than trusting this number.
_EXCHANGE_REQUEST_LIMIT = 2 * _EXCHANGE_DOCUMENT_LIMIT


def _padded(document: bytes, length: int) -> bytes:
    """``document`` followed by JSON whitespace, ``length`` bytes in all.

    Trailing whitespace is legal JSON, so the padded body still parses: past
    the limit it is a body a reader *could* parse, which is what makes reading
    it a defect rather than a harmless failure.
    """
    assert length >= len(document)
    return document + b" " * (length - len(document))


def _chunks(body: bytes) -> list[bytes]:
    return [body[start : start + CHUNK] for start in range(0, len(body), CHUNK)]


# -- the in-process ASGI driver -----------------------------------------------


@dataclass(frozen=True)
class _Exchange:
    """One request driven through an ASGI app, as the peer saw it."""

    status: int
    #: Body bytes the app pulled from the peer through ``receive()``.
    pulled: int
    #: Body bytes the peer had to offer.
    offered: int
    #: The response body the app sent back.
    response: bytes


Headers = list[tuple[bytes, bytes]]


async def _post(
    app: Callable[..., Awaitable[None]],
    *,
    path: str,
    headers: Headers,
    chunks: Sequence[bytes],
) -> _Exchange:
    """POST ``chunks`` to ``path`` through ``app`` and count what it pulled.

    The peer side is played by ``receive``: it hands out one chunk per call,
    marking the last with ``more_body=False``, and once the body is exhausted it
    waits for the response to complete and then reports a disconnect, as an
    ASGI server does. Nothing here enforces ``Content-Length``, so an app that
    trusts the header over the bytes is observable.
    """
    pending = list(chunks)
    pulled = 0
    statuses: list[int] = []
    response: list[bytes] = []
    complete = asyncio.Event()

    async def receive() -> dict[str, Any]:
        nonlocal pulled
        if pending:
            chunk = pending.pop(0)
            pulled += len(chunk)
            return {"type": "http.request", "body": chunk, "more_body": bool(pending)}
        await complete.wait()
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        if message["type"] == "http.response.start":
            statuses.append(message["status"])
        elif message["type"] == "http.response.body":
            response.append(message.get("body", b""))
            if not message.get("more_body", False):
                complete.set()

    scope: dict[str, Any] = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "server": ("receiver.invalid", 80),
        "client": ("peer.invalid", 40000),
    }
    await asyncio.wait_for(app(scope, receive, send), timeout=_DEADLINE_SECONDS)
    assert statuses, "the app returned without sending a response"
    return _Exchange(
        status=statuses[0],
        pulled=pulled,
        offered=sum(len(c) for c in chunks),
        response=b"".join(response),
    )


def _framed(
    base: Headers, *, framing: str, body: bytes, limit: int
) -> tuple[Headers, list[bytes]]:
    """Headers and chunks for one framing of ``body``.

    ``declared``: an honest ``Content-Length``, the body in one message.
    ``chunked``: no length at all, the body streamed in ``CHUNK``-byte messages.
    ``understated``: a ``Content-Length`` the limit admits, then more bytes than
    it declared, streamed. A length is a claim, and a peer can lie in it.
    """
    if framing == "declared":
        return base + [(b"content-length", str(len(body)).encode())], [body]
    if framing == "chunked":
        return base + [(b"transfer-encoding", b"chunked")], _chunks(body)
    if framing == "understated":
        return base + [(b"content-length", str(limit).encode())], _chunks(body)
    raise AssertionError(f"unknown framing {framing!r}")


# -- LF A2A leg ---------------------------------------------------------------

_LF_HEADERS: Headers = [
    (b"content-type", b"application/json"),
    (VERSION_HEADER.lower().encode("ascii"), PROTOCOL_VERSION_CURRENT.encode("ascii")),
]


@pytest.fixture
def dispatcher(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[int]]:
    """Record every entry into ``a2a-sdk``'s JSON-RPC dispatcher.

    Each entry appends the number of body bytes the dispatcher was handed. The
    patch is on the class, before any test builds its routes:
    ``create_jsonrpc_routes`` binds ``dispatcher.handle_requests`` when it builds
    the route, so a route built first would hold the unpatched method.
    """
    delivered: list[int] = []
    original = JsonRpcDispatcher.handle_requests

    async def recording(self: JsonRpcDispatcher, request: Any) -> Any:
        delivered.append(len(await request.body()))
        return await original(self, request)

    monkeypatch.setattr(JsonRpcDispatcher, "handle_requests", recording)
    yield delivered


def _lf_kwargs(**overrides: Any) -> dict[str, Any]:
    """An LF receiver's constructor arguments, the limits under test by default."""
    kwargs: dict[str, Any] = {
        "local_peer_id": CONSUMER["peer_id"],
        "agent_card": build_agent_card(
            name=LF_A2A["card"]["name"],
            version=LF_A2A["card"]["version"],
            description=LF_A2A["card"]["description"],
            rpc_url=_BASE + LF_A2A["rpc_path"],
        ),
        "cards": lambda *, peer: _BASE,
        "http_client_factory": httpx.AsyncClient,
        "clock": lambda: _INSTANT,
        "rpc_path": LF_A2A["rpc_path"],
        "max_request_bytes": LF_LIMIT,
        "max_message_bytes": LF_DOCUMENT_LIMIT,
        "max_pending": CONSUMER["max_pending"],
    }
    kwargs.update(overrides)
    return kwargs


def _lf_wire(**overrides: Any) -> tuple[LfA2AWire, bool]:
    """An LF wire, passing ``max_request_bytes`` only if the constructor declares it.

    Returns the wire and whether the body limit was declared. On a tree whose
    constructor does not declare it, the wire is built without it, so the red
    there is the behavior, not a ``TypeError`` that says nothing about it.
    """
    kwargs = _lf_kwargs(**overrides)
    declared = "max_request_bytes" in inspect.signature(LfA2AWire.__init__).parameters
    if not declared:
        del kwargs["max_request_bytes"]
    return LfA2AWire(**kwargs), declared


def _lf_receiver(**overrides: Any) -> tuple[LfA2AWire, Starlette, bool]:
    """An LF receiver, mounted as a deployment mounts it."""
    wire, declared = _lf_wire(**overrides)
    return wire, Starlette(routes=list(wire.routes())), declared


def _assert_the_dispatcher_never_parsed_it(
    delivered: list[int], wire: LfA2AWire, offered: int
) -> None:
    assert delivered == [], (
        f"a2a-sdk's JSON-RPC dispatcher was handed {delivered} body bytes of a"
        f" {offered}-byte request against a {LF_LIMIT}-byte max_request_bytes,"
        " and parsed them: the request body was not held to max_request_bytes"
        " before parsing (SEC-021-U1)"
    )
    assert len(wire._received) == 0, (
        "the over-limit carriage was parsed, framed and queued"
    )


def test_lf_a2a_refuses_a_declared_length_over_the_limit_without_reading_it(
    dispatcher: list[int],
) -> None:
    """(a): a ``Content-Length`` one byte over the body limit is refused on the header.

    What would fail here: the unfixed route, whose dispatcher reads and parses
    the body (the record shows it); a body held to ``max_message_bytes``, which
    this case sets above every body it sends; a layer that reads the body
    before looking at the declared length (``pulled`` is non-zero); a refusal
    answered as anything but 413.
    """
    wire, app, declared = _lf_receiver()
    body = _padded(_jsonrpc_body(), LF_LIMIT + 1)
    headers, chunks = _framed(
        _LF_HEADERS, framing="declared", body=body, limit=LF_LIMIT
    )

    exchange = asyncio.run(
        _post(app, path=LF_A2A["rpc_path"], headers=headers, chunks=chunks)
    )

    _assert_the_dispatcher_never_parsed_it(dispatcher, wire, exchange.offered)
    assert exchange.status == 413, (
        f"an over-limit declared length was answered {exchange.status}, not 413"
    )
    assert exchange.pulled == 0, (
        f"{exchange.pulled} body bytes were read although the declared length"
        f" ({exchange.offered}) already exceeded the {LF_LIMIT}-byte limit"
    )
    assert declared, _UNDECLARED


@pytest.mark.parametrize("framing", ["chunked", "understated"])
def test_lf_a2a_refuses_a_streamed_body_the_moment_it_crosses_the_limit(
    dispatcher: list[int], framing: str
) -> None:
    """(b): a body with no trustworthy length is counted as it arrives.

    ``chunked`` declares no length. ``understated`` declares a length the limit
    admits and then sends four times the limit, so a layer that trusted the
    header and skipped counting would let it through. In both cases the bytes
    must stop being read within one chunk of ``max_request_bytes``.
    """
    wire, app, declared = _lf_receiver()
    body = _padded(_jsonrpc_body(), _OVERRUN * LF_LIMIT)
    headers, chunks = _framed(_LF_HEADERS, framing=framing, body=body, limit=LF_LIMIT)

    exchange = asyncio.run(
        _post(app, path=LF_A2A["rpc_path"], headers=headers, chunks=chunks)
    )

    _assert_the_dispatcher_never_parsed_it(dispatcher, wire, exchange.offered)
    assert exchange.status == 413, (
        f"an over-limit {framing} body was answered {exchange.status}, not 413"
    )
    assert exchange.pulled <= LF_LIMIT + CHUNK, (
        f"{exchange.pulled} of {exchange.offered} body bytes were read against a"
        f" {LF_LIMIT}-byte limit: reading did not stop when the count crossed it"
    )
    assert declared, _UNDECLARED


@pytest.mark.parametrize("framing", ["declared", "chunked"])
def test_lf_a2a_hands_a_body_exactly_at_the_limit_to_the_dispatcher_whole(
    dispatcher: list[int], framing: str
) -> None:
    """Control: a body of exactly the limit is a carriage, not an overflow.

    It must reach the dispatcher whole and be queued. This is also the
    instrument's positive control: the record is non-empty when the dispatcher
    is reached, so an empty record above means it was not. A control passes on
    any tree, so it does not pin the declaration; the signature case does.
    """
    wire, app, _ = _lf_receiver()
    body = _padded(_jsonrpc_body(), LF_LIMIT)
    headers, chunks = _framed(_LF_HEADERS, framing=framing, body=body, limit=LF_LIMIT)

    exchange = asyncio.run(
        _post(app, path=LF_A2A["rpc_path"], headers=headers, chunks=chunks)
    )

    assert exchange.status == 200, (
        f"a body exactly at the {LF_LIMIT}-byte limit was answered"
        f" {exchange.status}; the limit is inclusive"
    )
    assert dispatcher == [LF_LIMIT], (
        f"the dispatcher was handed {dispatcher}, not the whole {LF_LIMIT}-byte body"
    )
    assert len(wire._received) == 1, "the at-limit carriage was not queued"


def test_lf_a2a_still_refuses_a_document_over_max_message_bytes_after_parsing(
    dispatcher: list[int],
) -> None:
    """``max_message_bytes`` keeps bounding the decoded document, after parsing.

    The body is within ``max_request_bytes`` and must reach the dispatcher
    whole. The document inside it is one byte over ``max_message_bytes``, so
    ``_accept`` refuses it as a frame: a JSON-RPC error naming the limit, and
    nothing queued. A body held to the document limit would never reach the
    dispatcher at all, which is what this case fails on there.
    """
    document = canonical_bytes(_garbage_envelope())
    document_limit = len(document) - 1
    wire, app, declared = _lf_receiver(max_message_bytes=document_limit)
    body = _jsonrpc_body()
    headers, chunks = _framed(_LF_HEADERS, framing="declared", body=body, limit=LF_LIMIT)

    exchange = asyncio.run(
        _post(app, path=LF_A2A["rpc_path"], headers=headers, chunks=chunks)
    )

    assert dispatcher == [len(body)], (
        f"a {len(body)}-byte request, within the {LF_LIMIT}-byte"
        f" max_request_bytes, did not reach the dispatcher whole (record"
        f" {dispatcher}, answered {exchange.status}): the request body was held"
        f" to the {document_limit}-byte document limit instead"
    )
    assert len(wire._received) == 0, (
        "a document over max_message_bytes was framed and queued"
    )
    limit_text = f"over this transport's {document_limit}-byte limit"
    assert limit_text.encode("utf-8") in exchange.response, (
        f"the refusal does not name the document limit: {exchange.response!r}"
    )
    assert declared, _UNDECLARED


def _recording_declared_lengths(
    app: Callable[..., Awaitable[None]], *, path: str, lengths: list[int]
) -> Callable[..., Awaitable[None]]:
    """Wrap ``app`` to record the declared length of every POST to ``path``."""

    async def recording(scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] == "http" and scope["method"] == "POST" and scope["path"] == path:
            for name, value in scope["headers"]:
                if name == b"content-length":
                    lengths.append(int(value))
        await app(scope, receive, send)

    return recording


def test_identically_configured_lf_peers_exchange_a_document_of_exactly_max_message_bytes() -> None:
    """The ruling's case: the body limit is ``max_request_bytes``, not the document's.

    Both peers declare the same ``max_message_bytes`` and the same
    ``max_request_bytes``, the latter large enough for the encoded request. The
    sender emits a document of exactly ``max_message_bytes``, which its own
    check admits. The request carrying it is the document base64-encoded inside
    JSON-RPC, and so larger than the document. A receiver that held the body to
    ``max_message_bytes`` answers 413, and the sender sees ``PeerUnreachable``:
    the shrink. A receiver that holds it to ``max_request_bytes`` accepts it,
    and the document is still within ``max_message_bytes`` after parsing.
    """
    holder: dict[str, Any] = {}
    lengths: list[int] = []

    def factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=holder["app"]), base_url=_BASE
        )

    configuration: dict[str, Any] = {
        "max_message_bytes": _EXCHANGE_DOCUMENT_LIMIT,
        "max_request_bytes": _EXCHANGE_REQUEST_LIMIT,
        "http_client_factory": factory,
    }
    receiver, declared = _lf_wire(**configuration)
    sender, _ = _lf_wire(**configuration)
    holder["app"] = _recording_declared_lengths(
        Starlette(routes=list(receiver.routes())),
        path=LF_A2A["rpc_path"],
        lengths=lengths,
    )
    document = _document_of_exactly(_EXCHANGE_DOCUMENT_LIMIT)
    peer = PeerRef(tenant_id=_TENANT, peer_id=CONSUMER["peer_id"])

    async def exchange() -> EmitReceipt | PeerUnreachable:
        try:
            return await sender.emit_async(peer=peer, signed=document)
        except PeerUnreachable as refusal:
            return refusal

    outcome = asyncio.run(exchange())

    assert not isinstance(outcome, PeerUnreachable), (
        f"a document of exactly max_message_bytes ({_EXCHANGE_DOCUMENT_LIMIT}"
        " bytes), sent between two identically configured LF peers, was"
        f" refused: {outcome}. The request carrying it declared {lengths} bytes:"
        " the document travels base64-encoded inside JSON-RPC, so a body held"
        " to the document limit refuses a document that limit admits"
    )
    assert outcome.content_address == document.content_address()
    assert [item.signed.content_address() for item in receiver.receive()] == [
        document.content_address()
    ]
    assert len(lengths) == 1, lengths
    assert _EXCHANGE_DOCUMENT_LIMIT < lengths[0] <= _EXCHANGE_REQUEST_LIMIT, (
        f"the request carrying the document declared {lengths[0]} bytes. The"
        " case needs it over the document limit, so the shrink it guards"
        " against is real, and within the declared max_request_bytes"
    )
    assert declared, _UNDECLARED


def test_lf_a2a_refuses_to_mount_a_jsonrpc_endpoint_it_cannot_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail closed: an endpoint the limit cannot wrap is refused, not mounted.

    The limit wraps a :class:`starlette.routing.Route`. Were a later
    ``a2a-sdk`` to build its JSON-RPC endpoint some other way, mounting it as
    given would reopen SEC-021-U1 with nothing to show for it, so
    ``routes()`` refuses at the deployment's composition root instead.
    """
    real = lf_a2a.create_jsonrpc_routes

    def as_a_mount(handler: Any, rpc_url: str, *args: Any, **kwargs: Any) -> list[Any]:
        return [Mount(rpc_url, app=Starlette(routes=real(handler, rpc_url, *args, **kwargs)))]

    monkeypatch.setattr(lf_a2a, "create_jsonrpc_routes", as_a_mount)

    wire, _ = _lf_wire()
    with pytest.raises(TypeError, match="SEC-021-U1"):
        wire.routes()


# -- both legs: the body limit is declared alike ------------------------------


@pytest.mark.parametrize("cls", [TypedHttpWire, LfA2AWire])
def test_max_request_bytes_is_required_keyword_only_with_no_default(cls: type) -> None:
    """Parity: both legs declare the body limit, required, with no SDK default."""
    parameter = inspect.signature(cls.__init__).parameters.get("max_request_bytes")
    assert parameter is not None, f"{cls.__name__} declares no max_request_bytes"
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Parameter.empty


@pytest.mark.parametrize("value", [0, -1])
@pytest.mark.parametrize("leg", ["typed", "lf"])
def test_a_non_positive_max_request_bytes_is_refused_alike_on_both_legs(
    leg: str, value: int
) -> None:
    """Parity: the same validation, in the typed leg's own words."""
    with httpx.Client() as client, pytest.raises(
        ValueError, match=f"^{_NON_POSITIVE_BODY_LIMIT}$"
    ):
        if leg == "typed":
            TypedHttpWire(
                local_peer_id=CONSUMER["peer_id"],
                endpoints=lambda *, peer: "",
                http_client=client,
                clock=lambda: _INSTANT,
                receive_path=CONSUMER["receive_path"],
                max_request_bytes=value,
                max_pending=CONSUMER["max_pending"],
            )
        else:
            LfA2AWire(**_lf_kwargs(max_request_bytes=value))


# -- typed-HTTP leg: the measurement, pinned ----------------------------------

_TYPED_PATH = CONSUMER["receive_path"]

_TYPED_HEADERS: Headers = [
    (b"content-type", SIGNED_PRODUCT_MEDIA_TYPE.encode("ascii")),
    (PEER_ID_HEADER.lower().encode("ascii"), SENDER_ID.encode("ascii")),
    (PEER_TENANT_HEADER.lower().encode("ascii"), _TENANT.encode("ascii")),
]


@pytest.fixture
def typed_parser(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[int]]:
    """Record every parse of a signed product, with the bytes it was handed."""
    parsed: list[int] = []
    original = SignedContextProduct.model_validate_json

    def recording(
        cls: type[SignedContextProduct], json_data: Any, *args: Any, **kwargs: Any
    ) -> SignedContextProduct:
        parsed.append(len(json_data))
        return original(json_data, *args, **kwargs)

    monkeypatch.setattr(
        SignedContextProduct, "model_validate_json", classmethod(recording)
    )
    yield parsed


def _typed_receiver() -> tuple[TypedHttpWire, httpx.Client]:
    client = httpx.Client()
    wire = TypedHttpWire(
        local_peer_id=CONSUMER["peer_id"],
        endpoints=lambda *, peer: "",
        http_client=client,
        clock=lambda: _INSTANT,
        receive_path=_TYPED_PATH,
        max_request_bytes=TYPED_LIMIT,
        max_pending=CONSUMER["max_pending"],
    )
    return wire, client


@pytest.mark.parametrize("framing", ["declared", "chunked", "understated"])
def test_typed_http_refuses_an_over_limit_body_before_it_parses(
    typed_parser: list[int], framing: str
) -> None:
    """The typed leg has no pre-parse gap: it counts before it parses.

    ``TypedHttpWire._handle_receive`` checks the declared length, then streams
    and counts, and calls ``model_validate_json`` only on a body within
    ``max_request_bytes``. Green before and after the LF fix; a regression
    here would be the same defect arriving on the other leg.
    """
    wire, client = _typed_receiver()
    with client:
        body = _padded(canonical_bytes(_garbage_envelope()), _OVERRUN * TYPED_LIMIT)
        if framing == "declared":
            body = body[: TYPED_LIMIT + 1]
        headers, chunks = _framed(
            _TYPED_HEADERS, framing=framing, body=body, limit=TYPED_LIMIT
        )
        exchange = asyncio.run(
            _post(wire.asgi_app(), path=_TYPED_PATH, headers=headers, chunks=chunks)
        )

    assert typed_parser == [], (
        f"the typed leg parsed {typed_parser} bytes of an over-limit body"
    )
    assert len(wire._received) == 0
    assert exchange.status == 413
    if framing == "declared":
        assert exchange.pulled == 0
    else:
        assert exchange.pulled <= TYPED_LIMIT + CHUNK


@pytest.mark.parametrize("framing", ["declared", "chunked"])
def test_typed_http_parses_a_body_exactly_at_the_limit(
    typed_parser: list[int], framing: str
) -> None:
    """Control for the typed measurement, and its instrument's positive control."""
    wire, client = _typed_receiver()
    with client:
        body = _padded(canonical_bytes(_garbage_envelope()), TYPED_LIMIT)
        headers, chunks = _framed(
            _TYPED_HEADERS, framing=framing, body=body, limit=TYPED_LIMIT
        )
        exchange = asyncio.run(
            _post(wire.asgi_app(), path=_TYPED_PATH, headers=headers, chunks=chunks)
        )

    assert exchange.status == 202
    assert typed_parser == [TYPED_LIMIT]
    assert len(wire._received) == 1
