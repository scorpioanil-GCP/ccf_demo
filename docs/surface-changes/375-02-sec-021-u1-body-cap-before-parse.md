# 375-02 — SEC-021-U1: the LF leg bounds a request body before `a2a-sdk` parses it

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

**The typed-HTTP leg was measured with the same three shapes and has no
pre-parse gap.** `TypedHttpWire._handle_receive` refuses a declared length over
`max_request_bytes` without reading the body, and otherwise streams and counts
the body before it calls `model_validate_json`. No change there; the
measurement is pinned in the same test module.

**What the bound does not do.** It is per request, so it does not limit the
bytes held across concurrent requests (the in-flight concern carried from the
`D-IMPL-369` close review, B5). It cannot bound what the ASGI server buffers
before it hands the application a message, nor what the server does with the
bytes the application never reads. Both are the deployment's server settings.

## ccf_runtime.peering.lf_a2a.LfA2AWire

- Surface: ccf_runtime.peering.lf_a2a.LfA2AWire
- Public surface: true
- Change type: behavior
- Before: `routes()` mounted `a2a-sdk`'s JSON-RPC route as given. Its dispatcher read and parsed the whole request body before `_accept` consulted `max_message_bytes`, so a request body of any size was buffered and parsed.
- After: `routes()` wraps the JSON-RPC route's application in a request-body limit equal to `max_message_bytes`. A declared `Content-Length` over the limit is answered `413` before any of the body is read. Any other body is counted as it arrives, whether or not a length was declared, and answered `413` the moment the count exceeds the limit. Over the limit the dispatcher is never called; a body within the limit is handed on whole. `routes()` raises `TypeError` rather than mount a JSON-RPC endpoint that is not a starlette `Route`, which the limit could not wrap. The constructor signature is unchanged.
- Why: SEC-021-U1, carried by `D-IMPL-370` (3): move the size check ahead of parsing. The limit is the one this leg already declares, `max_message_bytes` (Q13's name on this leg for the typed leg's `max_request_bytes`), so the SDK adds no parameter and no default value.
- Migration: none for the constructor. The JSON-RPC binding carries the document base64-encoded inside the request, so the largest document this endpoint accepts is now about three quarters of `max_message_bytes`, less the JSON-RPC envelope (measured: 5,856 bytes at a limit of 8,192). A deployment that carries documents near its limit must raise `max_message_bytes` to cover the encoded request. `emit` checks only the document, so a sender declaring the same value can emit a document the receiver answers `413`; `emit` and `emit_async` raise `PeerUnreachable` for it.
