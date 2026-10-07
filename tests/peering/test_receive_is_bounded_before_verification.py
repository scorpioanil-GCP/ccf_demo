"""SEC-021: an unauthenticated A2A receive buffer is bounded, and overflow
refuses the newcomer while the queued messages survive intact and in order.

Both Peering transports queue what arrives **before any signature check** —
that is by design (D-12: the transport frames, the Control Plane gate decides),
so the queue is reachable by anyone who can reach the endpoint. Without a bound
a hostile sender grows the receiving process's memory without limit.

The ruled behavior (Q13 and ``D-IMPL-369``), which each assertion below is
drafted against:

* a required keyword-only ``max_pending`` on both constructors, no SDK default;
* when the queue already holds ``max_pending`` messages the newcomer is refused
  **by name** with a typed refusal that is not a framing failure;
* the queued messages are **preserved, in order** — a ``deque(maxlen=N)`` that
  evicts the oldest is non-conforming, and the order assertion is what catches
  it (an evicting buffer would pass a length assertion);
* the cap check sits immediately before the append — an append-then-check
  buffer would momentarily hold ``N + 1``, and the length assertion catches it.

Every envelope sent here is well framed and carries a **garbage signature**:
the point is that nothing on the receive path verifies anything, so an
attacker needs no key to fill the queue. In-process over
``httpx.ASGITransport`` — no port is bound and no peer process is spawned.

The receiver is built through :func:`_declared_cap`: when the constructor does
not yet take ``max_pending`` (the unfixed tree) it is built without one, so the
red this test shows on that tree is the queue growing past ``N`` — the defect
itself — rather than a ``TypeError`` that says nothing about it. The final
assertion of each case then pins that the cap was actually declared.
"""

from __future__ import annotations

import asyncio
import base64
import inspect
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml
from starlette.applications import Starlette

from ccf.contracts.canonical import canonical_bytes
from ccf.peering.identity import SignedContextProduct
from ccf.peering.protocol import PeerRef
from ccf_runtime.peering import typed_http
from ccf_runtime.peering.lf_a2a import LfA2AWire, build_agent_card
from ccf_runtime.peering.typed_http import (
    PEER_ID_HEADER,
    PEER_TENANT_HEADER,
    SIGNED_PRODUCT_MEDIA_TYPE,
    WIRE_MESSAGE_ID_HEADER,
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

#: The queue bound under test. A test parameter, deliberately small so ``N + 1``
#: carriages are cheap; the fixture's own value is a deployment's statement and
#: is exercised by the cross-process suite.
N = 3

#: The injected receive instant. Fixed so carriage identifiers are reproducible
#: from the envelope alone, which is what the order comparison relies on.
_INSTANT = datetime(2026, 3, 1, tzinfo=UTC)

#: The base URL the in-process receiver answers at. Never resolved by DNS: the
#: ASGI transport routes every request to the app it wraps.
_BASE = "http://receiver.invalid"

#: The refusal's name as the ruling requires it to be visible to the sender.
_REFUSAL_NAME = "ReceiveQueueFull"


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _garbage_envelope(index: int) -> SignedContextProduct:
    """A well-framed envelope whose signature verifies against nothing.

    The payload member is genuine base64url (so the carriage has a content
    address and the frame is well formed); the protected header and signature
    are not a JWS at all. Distinct per ``index`` so each carriage identifier is
    distinct and order is observable.
    """
    payload = json.dumps({"carriage": index}, sort_keys=True).encode("utf-8")
    return SignedContextProduct(
        payload=_b64url(payload),
        protected=_b64url(b"not-a-jws-header"),
        signature=_b64url(b"not-a-signature-%d" % index),
    )


def _declared_cap(cls: type, **kwargs: Any) -> tuple[Any, bool]:
    """Build ``cls`` with ``max_pending=N`` when the constructor declares it.

    Returns the instance and whether the cap was declared. On the unfixed tree
    the constructor has no such parameter, so the instance is built without it
    and the queue-length assertion — not a ``TypeError`` — is what goes red.
    """
    declared = "max_pending" in inspect.signature(cls.__init__).parameters
    if declared:
        kwargs["max_pending"] = N
    return cls(**kwargs), declared


def _queued_ids(wire: Any) -> list[str]:
    """The carriage identifiers of what ``wire`` holds, oldest first, unread."""
    return [
        f"{item.observed_peer.peer_id}/{_INSTANT.isoformat()}/"
        f"{item.signed.content_address()}"
        for item in list(wire._received)
    ]


# -- typed-HTTP leg -----------------------------------------------------------


def test_typed_http_receive_queue_is_bounded_and_preserves_order() -> None:
    """Typed leg: ``N + 1`` garbage-signed carriages against ``max_pending=N``.

    What would fail here: an unbounded queue (length ``N + 1``); an evicting
    ``deque(maxlen=N)`` (the first carriage gone, order assertion red); a
    cap checked after the append (length ``N + 1`` at the moment of refusal);
    a refusal answered as ``202`` or as a framing ``400``.
    """
    with httpx.Client() as unused_client:
        wire, declared = _declared_cap(
            TypedHttpWire,
            local_peer_id=CONSUMER["peer_id"],
            endpoints=lambda *, peer: "",
            http_client=unused_client,
            clock=lambda: _INSTANT,
            receive_path=CONSUMER["receive_path"],
            max_request_bytes=CONSUMER["max_request_bytes"],
        )
        app: Starlette = wire.asgi_app()

        async def carry_all() -> list[httpx.Response]:
            transport = httpx.ASGITransport(app=app)
            responses: list[httpx.Response] = []
            async with httpx.AsyncClient(transport=transport, base_url=_BASE) as client:
                for index in range(N + 1):
                    responses.append(
                        await client.post(
                            CONSUMER["receive_path"],
                            content=canonical_bytes(_garbage_envelope(index)),
                            headers={
                                "content-type": SIGNED_PRODUCT_MEDIA_TYPE,
                                PEER_ID_HEADER: SENDER_ID,
                                PEER_TENANT_HEADER: "tenant-under-test",
                            },
                        )
                    )
                    assert len(wire._received) <= N, (
                        f"the unauthenticated receive queue holds"
                        f" {len(wire._received)} messages after carriage"
                        f" {index + 1}, over the bound of {N}: nothing verified"
                        " a signature and the queue still grew"
                    )
            return responses

        responses = asyncio.run(carry_all())

    accepted = responses[:N]
    newcomer = responses[N]
    assert [r.status_code for r in accepted] == [202] * N
    accepted_ids = [r.headers[WIRE_MESSAGE_ID_HEADER] for r in accepted]

    # Order before refusal: an evicting buffer refuses nobody, and the first
    # thing it gets wrong is which N it kept.
    assert _queued_ids(wire) == accepted_ids, (
        "the queued carriages are not the first N, in order — an evicting"
        " buffer drops the oldest to admit the newcomer"
    )
    assert newcomer.status_code in (429, 503), (
        f"the carriage over the bound was answered {newcomer.status_code};"
        " the ruling refuses it as a capacity condition (429/503), not as"
        " accepted and not as a framing failure"
    )
    assert _REFUSAL_NAME in newcomer.text, (
        f"the refusal is not named: body {newcomer.text!r}"
    )
    assert WIRE_MESSAGE_ID_HEADER not in newcomer.headers
    drained = list(wire.receive())
    assert [d.signed.content_address() for d in drained] == [
        _garbage_envelope(i).content_address() for i in range(N)
    ]
    assert declared, "TypedHttpWire does not declare a max_pending bound"


def test_typed_http_queues_nothing_it_cannot_name() -> None:
    """Typed leg: a non-base64url payload is refused as a frame, never queued.

    The carriage identifier is minted from the payload's content address; minting
    it after the append queued a message it then could not acknowledge (answered
    ``500``). The fix orders carriage id, cap check, then append.
    """
    with httpx.Client() as unused_client:
        wire, _ = _declared_cap(
            TypedHttpWire,
            local_peer_id=CONSUMER["peer_id"],
            endpoints=lambda *, peer: "",
            http_client=unused_client,
            clock=lambda: _INSTANT,
            receive_path=CONSUMER["receive_path"],
            max_request_bytes=CONSUMER["max_request_bytes"],
        )
        bad = SignedContextProduct(
            # Not ASCII, so not base64url under any decoder leniency: the
            # payload has no content address and the carriage cannot be named.
            payload="\u00e9t\u00e9",
            protected=_b64url(b"x"),
            signature=_b64url(b"y"),
        )

        async def carry() -> httpx.Response:
            transport = httpx.ASGITransport(app=wire.asgi_app(), raise_app_exceptions=False)
            async with httpx.AsyncClient(transport=transport, base_url=_BASE) as client:
                return await client.post(
                    CONSUMER["receive_path"],
                    content=canonical_bytes(bad),
                    headers={
                        "content-type": SIGNED_PRODUCT_MEDIA_TYPE,
                        PEER_ID_HEADER: SENDER_ID,
                        PEER_TENANT_HEADER: "tenant-under-test",
                    },
                )

        response = asyncio.run(carry())

    assert len(wire._received) == 0, (
        "a carriage with no content address was queued before its identifier"
        " was minted"
    )
    assert response.status_code == 400


# -- LF A2A leg ---------------------------------------------------------------


def _lf_wire(http_client_factory: Callable[[], httpx.AsyncClient]) -> tuple[LfA2AWire, bool]:
    wire, declared = _declared_cap(
        LfA2AWire,
        local_peer_id=CONSUMER["peer_id"],
        agent_card=build_agent_card(
            name=LF_A2A["card"]["name"],
            version=LF_A2A["card"]["version"],
            description=LF_A2A["card"]["description"],
            rpc_url=_BASE + LF_A2A["rpc_path"],
        ),
        cards=lambda *, peer: _BASE,
        http_client_factory=http_client_factory,
        clock=lambda: _INSTANT,
        rpc_path=LF_A2A["rpc_path"],
        max_request_bytes=CONSUMER["max_request_bytes"],
        max_message_bytes=CONSUMER["max_request_bytes"],
    )
    return wire, declared


def test_lf_a2a_receive_queue_is_bounded_and_preserves_order() -> None:
    """LF leg: ``N + 1`` garbage-signed carriages against ``max_pending=N``.

    The sender is a second ``LfA2AWire`` driving ``a2a-sdk``'s own client and
    JSON-RPC routes, so the refusal is observed exactly as a peer would see it.
    """
    holder: dict[str, Starlette] = {}

    def factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=holder["app"]), base_url=_BASE
        )

    receiver, declared = _lf_wire(factory)
    holder["app"] = Starlette(routes=list(receiver.routes()))
    sender, _ = _lf_wire(factory)
    peer = PeerRef(tenant_id="tenant-under-test", peer_id=CONSUMER["peer_id"])

    async def carry_all() -> tuple[list[str], BaseException | None]:
        ids: list[str] = []
        refusal: BaseException | None = None
        for index in range(N + 1):
            try:
                receipt = await sender.emit_async(
                    peer=peer, signed=_garbage_envelope(index)
                )
                ids.append(receipt.wire_message_id)
            except PeerUnreachable as failure:
                refusal = failure
            assert len(receiver._received) <= N, (
                f"the unauthenticated receive queue holds"
                f" {len(receiver._received)} messages after carriage"
                f" {index + 1}, over the bound of {N}: nothing verified a"
                " signature and the queue still grew"
            )
        return ids, refusal

    accepted_ids, refusal = asyncio.run(carry_all())

    # Order before refusal, as on the typed leg.
    assert _queued_ids(receiver) == accepted_ids[:N], (
        "the queued carriages are not the first N, in order — an evicting"
        " buffer drops the oldest to admit the newcomer"
    )
    assert len(accepted_ids) == N
    assert refusal is not None, "the carriage over the bound was accepted"
    assert _REFUSAL_NAME in str(refusal), (
        f"the refusal is not named: {refusal!r}"
    )
    drained = list(receiver.receive())
    assert [d.signed.content_address() for d in drained] == [
        _garbage_envelope(i).content_address() for i in range(N)
    ]
    assert declared, "LfA2AWire does not declare a max_pending bound"


@pytest.mark.parametrize("cls", [TypedHttpWire, LfA2AWire])
def test_max_pending_is_required_keyword_only_with_no_default(cls: type) -> None:
    """Q13: no SDK default — a buffer size is the deployment's decision."""
    parameter = inspect.signature(cls.__init__).parameters.get("max_pending")
    assert parameter is not None, f"{cls.__name__} declares no max_pending"
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Parameter.empty


def test_the_refusal_is_typed_and_is_not_a_framing_failure() -> None:
    """The overflow refusal is its own type, not ``MalformedWireMessage``."""
    refusal = getattr(typed_http, _REFUSAL_NAME, None)
    assert isinstance(refusal, type), f"no {_REFUSAL_NAME} in typed_http"
    assert issubclass(refusal, typed_http.WireTransportError)
    assert not issubclass(refusal, typed_http.MalformedWireMessage)
