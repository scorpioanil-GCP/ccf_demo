# 378-44 — the stdio product door restores the previous login identity when it leaves

`D-IMPL-378`, lane `378g-b8s9`, item 9 of the owed rulings. Dave ruled on 2026-10-08 at 21:24 MST (recorded on `main`
at `f84786b5`), verbatim: *"b. Restore the previous login identity in finally; verify normal return, exception and
cancellation."* No SEC row changes here.

`ProductDoor.serve_stdio` sets the MCP library's login identity, `auth_context_var` in
`mcp.server.auth.middleware.auth_context`, to the identity its caller composed, just before the stdio server starts.
Stdio carries no authentication channel, so that one identity answers for every caller while the server runs. The
door never reset the variable, so once `serve_stdio` left, whether by returning, by an exception or by cancellation,
the calling code still ran as the stdio identity. Every SDK example calls it as its process's last act, so there the
leftover identity reached only the rest of that call's `with` block; a test that served stdio inside the pytest process
leaked it into the tests after it (found by lane `378f-d3b`, contained in the test layer by lane `378f-mfix`). The
door now keeps the token `set` returns and resets the variable in a `finally`.

Measured red at `7e1895f0` and green at `de6201a` by three tests, each run with a prior identity set before the call
and with none, each driving the real stdio transport (`FastMCP.run`, `anyio.run`, `mcp.server.stdio.stdio_server`
over in-memory standard streams) and reading the variable itself before, during and after the call:
`tests/mcp/test_stdio_door_restores_the_previous_identity.py::test_after_a_normal_return_the_previous_identity_is_restored`,
`tests/mcp/test_stdio_door_restores_the_previous_identity.py::test_after_an_exception_inside_the_transport_the_previous_identity_is_restored`
and
`tests/mcp/test_stdio_door_restores_the_previous_identity.py::test_after_cancellation_while_serving_the_previous_identity_is_restored`.
With the reset severed, all six cells fail again. The test-layer containment in
`tests/products/test_paved_road.py::test_the_stdio_door_reads_neither_door_url_and_advertises_only_reserved_addresses`
stays and is now redundant: removed, `tests/products/test_stdio_identity_is_contained_between_tests.py` still passes
at `de6201a` and fails at `7e1895f0`.

## ccf_runtime.mcp.product_door.ProductDoor

- Surface: ccf_runtime.mcp.product_door.ProductDoor
- Public surface: true
- Change type: behavior
- Before: `serve_stdio` set `auth_context_var` to the identity it was handed and left it set after it returned, raised or was cancelled, so after the call the caller's context still held the stdio identity.
- After: `serve_stdio` restores, in a `finally`, the login identity the caller's context held before the call, a prior identity or none, whichever way the call ends: a normal return, an exception raised inside the transport (it still propagates, unchanged), or cancellation (`asyncio.CancelledError` still propagates). While the server runs, the identity it was handed answers for every caller, as before, and a call without an identity is still refused with `StdioIdentityRequired` before anything is set.
- Why: Dave's ruling on item 9 (b) (`D-IMPL-378`, 2026-10-08 21:24 MST): "Restore the previous login identity in finally; verify normal return, exception and cancellation."
- Migration: none for a process that serves stdio as its last act, which is every SDK example. Code that relied on the stdio identity still being set after `serve_stdio` returned sets it itself.
