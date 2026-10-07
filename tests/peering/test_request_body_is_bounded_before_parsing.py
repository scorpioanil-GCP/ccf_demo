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
limit. The limit is the one this leg already declares, ``max_message_bytes``
(Q13's name on this leg for the typed leg's ``max_request_bytes``). There is no
new SDK default value.

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

The typed-HTTP leg is measured here too, with the same three shapes, against
``SignedContextProduct.model_validate_json``. That leg streams and counts the
body itself before it parses, so it has no pre-parse gap, and its cases pass
on the unfixed tree as well. They pin that measurement; they do not claim a
red.
"""

from __future__ import annotations

import asyncio
import base64
import json
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

from ccf.contracts.canonical import canonical_bytes
from ccf.peering.identity import SignedContextProduct
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


#: The LF leg's declared limit under test: the smallest well-formed body plus
#: room to pad it. Set as the wire's ``max_message_bytes``.
LF_LIMIT = len(_jsonrpc_body()) + _MARGIN

#: The typed leg's declared limit under test, on the same rule, for its own
#: body (the canonical envelope itself). Set as its ``max_request_bytes``.
TYPED_LIMIT = len(canonical_bytes(_garbage_envelope())) + _MARGIN


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
        elif message["type"] == "http.response.body" and not message.get(
            "more_body", False
        ):
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
        status=statuses[0], pulled=pulled, offered=sum(len(c) for c in chunks)
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


def _lf_receiver() -> tuple[LfA2AWire, Starlette]:
    """An LF receiver declaring ``LF_LIMIT``, mounted as a deployment mounts it."""
    wire = LfA2AWire(
        local_peer_id=CONSUMER["peer_id"],
        agent_card=build_agent_card(
            name=LF_A2A["card"]["name"],
            version=LF_A2A["card"]["version"],
            description=LF_A2A["card"]["description"],
            rpc_url=_BASE + LF_A2A["rpc_path"],
        ),
        cards=lambda *, peer: _BASE,
        http_client_factory=httpx.AsyncClient,
        clock=lambda: _INSTANT,
        rpc_path=LF_A2A["rpc_path"],
        max_message_bytes=LF_LIMIT,
        max_pending=CONSUMER["max_pending"],
    )
    return wire, Starlette(routes=list(wire.routes()))


def _assert_the_dispatcher_never_parsed_it(
    delivered: list[int], wire: LfA2AWire, offered: int
) -> None:
    assert delivered == [], (
        f"a2a-sdk's JSON-RPC dispatcher was handed {delivered} body bytes of a"
        f" {offered}-byte request against a {LF_LIMIT}-byte limit, and parsed"
        " them: nothing bounded the request body before parsing (SEC-021-U1)"
    )
    assert len(wire._received) == 0, (
        "the over-limit carriage was parsed, framed and queued"
    )


def test_lf_a2a_refuses_a_declared_length_over_the_limit_without_reading_it(
    dispatcher: list[int],
) -> None:
    """(a): a ``Content-Length`` one byte over the limit is refused on the header.

    What would fail here: the unfixed route, whose dispatcher reads and parses
    the body (the record shows it); a layer that reads the body before looking
    at the declared length (``pulled`` is non-zero); a refusal answered as
    anything but 413.
    """
    wire, app = _lf_receiver()
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


@pytest.mark.parametrize("framing", ["chunked", "understated"])
def test_lf_a2a_refuses_a_streamed_body_the_moment_it_crosses_the_limit(
    dispatcher: list[int], framing: str
) -> None:
    """(b): a body with no trustworthy length is counted as it arrives.

    ``chunked`` declares no length. ``understated`` declares a length the limit
    admits and then sends four times the limit, so a layer that trusted the
    header and skipped counting would let it through. In both cases the bytes
    must stop being read within one chunk of the limit.
    """
    wire, app = _lf_receiver()
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


@pytest.mark.parametrize("framing", ["declared", "chunked"])
def test_lf_a2a_hands_a_body_exactly_at_the_limit_to_the_dispatcher_whole(
    dispatcher: list[int], framing: str
) -> None:
    """Control: a body of exactly the limit is a carriage, not an overflow.

    It must reach the dispatcher whole and be queued. This is also the
    instrument's positive control: the record is non-empty when the dispatcher
    is reached, so an empty record above means it was not.
    """
    wire, app = _lf_receiver()
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
