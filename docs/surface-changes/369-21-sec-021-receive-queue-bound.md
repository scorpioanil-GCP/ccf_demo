# 369-21 — SEC-021: the Peering receive queue is bounded, and overflow refuses the newcomer

`D-IMPL-369` (and `D-IMPL-368`), row SEC-021, ruling Q13 of
`docs/superpowers/specs/2026-10-05-remaining-rows-rulings-batch.md`. Measured
before this entry: both Peering transports held their received messages in an
unbounded `deque` and appended **before any signature check** (by design: the
transport frames and the Control Plane gate decides, D-12). So anyone who could
reach the endpoint could grow the receiving process's memory without limit
using well-framed envelopes carrying garbage signatures. The exploit test is
`tests/peering/test_receive_is_bounded_before_verification.py`.

**The overflow behavior, ruled (`D-IMPL-369`): the newcomer is refused by name,
and the queued messages are preserved intact and in order.** Nothing is
evicted. A `deque(maxlen=N)` that drops the oldest is non-conforming, because it
would let an unauthenticated sender displace carriages a genuine peer had
already delivered.

## ccf_runtime.peering.typed_http.ReceiveQueueFull

- Surface: ccf_runtime.peering.typed_http.ReceiveQueueFull
- Public surface: true
- Change type: added
- Before: absent. A full queue was not a reachable condition, because the queue had no bound.
- After: a `WireTransportError` subclass, not a `MalformedWireMessage`, raised when a receive queue already holds `max_pending` messages. `ReceiveQueueFull.at_bound` builds it with its own name at the head of the message, because on the LF A2A leg `a2a-sdk` carries only the message text to the sending peer.
- Why: SEC-021. A full queue is a capacity condition of the receiver, not a verdict on the frame, so it must not share a type with a framing failure. A caller that treated it as a protocol mismatch would stop retrying a carriage that will succeed once the receiver drains.
- Migration: none for a caller that does not host a receive endpoint.

## ccf_runtime.peering.typed_http.TypedHttpWire

- Surface: ccf_runtime.peering.typed_http.TypedHttpWire
- Public surface: true
- Change type: reshaped
- Before: `(*, local_peer_id, endpoints, http_client, clock, receive_path, max_request_bytes)`. The receive queue was unbounded. The endpoint appended the inbound message and then minted the carriage identifier, so a payload that was not base64url was queued and answered `500`.
- After: adds `max_pending: int`, which is required, keyword-only, has no default, and must be positive (`ValueError` otherwise). The endpoint mints the carriage identifier first and answers `400` for a payload that cannot be named; such a payload is never queued. It then checks the bound immediately before the append. At the bound it answers `503`, with a plain-text body naming `ReceiveQueueFull`, and the queued messages stay intact and in order.
- Why: SEC-021 and Q13. A buffer size is a deployment's capacity decision, so the SDK ships no default (D-IMPL-38, D-IMPL-356).
- Migration: every constructor call must now pass `max_pending`. A sending peer sees the `503` as `PeerUnreachable` from `emit` and may retry once the receiver drains.

## ccf_runtime.peering.lf_a2a.LfA2AWire

- Surface: ccf_runtime.peering.lf_a2a.LfA2AWire
- Public surface: true
- Change type: reshaped
- Before: `(*, local_peer_id, agent_card, cards, http_client_factory, clock, rpc_path, max_message_bytes)`. The receive queue was unbounded.
- After: adds `max_pending: int`, which is required, keyword-only, has no default, and must be positive (`ValueError` otherwise). `_enqueue` checks the bound immediately before the append and raises `ReceiveQueueFull` at the bound. `a2a-sdk` returns that to the sending peer as a JSON-RPC error whose message begins `ReceiveQueueFull:`, and the queued messages stay intact and in order.
- Why: SEC-021 and Q13, as for `TypedHttpWire`.
- Migration: every constructor call must now pass `max_pending`. A sending peer sees the refusal as `PeerUnreachable` from `emit` / `emit_async`. Not covered here, and escalated separately: `a2a-sdk`'s JSON-RPC dispatcher reads the request body before this transport's checks run, so `max_message_bytes` bounds the carried envelope, not the bytes the process buffers.
