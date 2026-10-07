# 375-02 — SEC-021-U1: the LF leg declares a request-body limit and holds the body to it before `a2a-sdk` parses it

Row SEC-021, clause 2, carried as **SEC-021-U1** by `D-IMPL-370` (3). SEC-021
as worded: "on the LF leg the body is parsed before `max_message_bytes` is
consulted". Remedy: "Cap before buffering; move the size check ahead of
parsing." Clause 1, the receive queue, landed in `369-21`. The exploit tests are
`tests/peering/test_request_body_is_bounded_before_parsing.py`.

Measured before this entry, at `8fceec83`: `LfA2AWire.routes()` mounted
`a2a-sdk`'s JSON-RPC route as given, and its dispatcher
(`JsonRpcDispatcher.handle_requests`) begins with `await request.json()`. It
read and parsed the whole request body before this transport's `_accept`
consulted `max_message_bytes`. A body four times the declared limit was read in
full and parsed, and its carriage was queued. `max_pending` bounded how many
envelopes were queued, and `max_message_bytes` bounded one carried document,
but nothing bounded the bytes a request body could occupy before parsing.

**Which limit, and why there are two on this leg.** A first round held the
request body to `max_message_bytes`. Measured there: two identically
configured peers refused a document of exactly `max_message_bytes` (4,096
bytes) with `413`, because the JSON-RPC binding carries the document
base64-encoded inside a larger request; at a limit of 8,192 the largest
document that got through was 5,856 bytes. The ruling on that round is
mechanism parity with the typed-HTTP leg: the LF leg declares
`max_request_bytes` for the body, and `max_message_bytes` keeps bounding only
the decoded document. The SDK derives neither from the other.

**The typed-HTTP leg was measured with the same three shapes and has no
pre-parse gap.** `TypedHttpWire._handle_receive` refuses a declared length over
`max_request_bytes` without reading the body, and otherwise streams and counts
the body before it calls `model_validate_json`. Its body is the canonical
document itself, so that one limit is its document limit too. No change there;
the measurement is pinned in the same test module.

**What the bound does not do.** It is per request, so it does not limit the
bytes held across concurrent requests (the in-flight concern carried from the
`D-IMPL-369` close review, B5). It cannot bound what the ASGI server buffers
before it hands the application a message, nor what the server does with the
bytes the application never reads. Both are the deployment's server settings.

## ccf_runtime.peering.lf_a2a.LfA2AWire

- Surface: ccf_runtime.peering.lf_a2a.LfA2AWire
- Public surface: true
- Change type: reshaped
- Before: `(*, local_peer_id, agent_card, cards, http_client_factory, clock, rpc_path, max_message_bytes, max_pending)`. `routes()` mounted `a2a-sdk`'s JSON-RPC route as given, and its dispatcher read and parsed the whole request body before `_accept` consulted `max_message_bytes`, so a request body of any size was buffered and parsed.
- After: adds `max_request_bytes: int`, which is required, keyword-only, has no default, and must be positive (`ValueError` otherwise, in the typed leg's words). `routes()` wraps the JSON-RPC route's application in a request-body limit equal to `max_request_bytes`. A declared `Content-Length` over it is answered `413` before any of the body is read. Any other body is counted as it arrives, whether or not a length was declared, and answered `413` the moment the count exceeds the limit. Over the limit the dispatcher is never called; a body within it is handed on whole. `max_message_bytes` keeps bounding only the decoded document, in `_accept` after parsing, and the outbound document in `emit`. `routes()` raises `TypeError` rather than mount a JSON-RPC endpoint that is not a starlette `Route`, which the limit could not wrap.
- Why: SEC-021-U1, carried by `D-IMPL-370` (3): move the size check ahead of parsing. Mechanism parity with `TypedHttpWire`, which declares `max_request_bytes` and checks it before parsing. Holding the body to `max_message_bytes` instead refused documents that limit admits. Neither limit is derived from the other, because a framing allowance would be a hard-coded threshold.
- Migration: every constructor call must now pass `max_request_bytes`. Declare it large enough for the JSON-RPC request that carries a document of `max_message_bytes`: that request carries the document base64-encoded, about four thirds of its size, plus an envelope that depends on the deployment's own identifiers, so measure it. A body over `max_request_bytes` is answered `413`, which a sending peer sees as `PeerUnreachable` from `emit` or `emit_async`.
