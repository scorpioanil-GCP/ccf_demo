# 20261011-14 — on the MCP product tool, a class no scope mapping names reads as an unentitled caller's refusal

Dave, 2026-10-11 21:19 MST, verbatim *"Do (a)"*, on finding R5-CP17-F01 (cp-17 MWE-G14): an ENTITLED caller asking
`request_context_product` for a product class no scope mapping names was denied at the mapping's resource axis as a
tool error naming the class (`tenant-unauthorized`), while an unentitled caller asking for a real class received the
governed minimal `subject-unavailable` shell. The difference answered "does this class exist?".

What changed: the authorizer's deny on the SDK product door's request tool is recorded by
`govern_scope_denial` through the same recorder and the same emission site as an entitlement denial — internal truth
`SubjectUnavailableRefusal(cause="unauthorized", error_code="tenant-unauthorized", detail=<the guard's statement>)`
on the record only — so the reply is the shell Disclosure decides for that principal, identical in every member of the complete public reply — `isError`, every content item, `structuredContent`, `meta` — but the per-answer record reference and the echo of the caller's own question (its class, its instant). The authorizer's deny event stays on the audit log unchanged (resource axis). The deny is still decided and audited
by the authorizer; no capability is minted and nothing is read. The tenant floor (SEC-018), the roster (SEC-017) and
the opaque directory refusal run first and are unchanged. Measured and NOT changed here (carried, for a decision): the HTTP door answers the same deny `403 request-unauthorized` (constant text, no class name) where an unentitled caller gets `404` and the `subject-unavailable` shell — a status-level oracle; the gate is ASGI middleware holding no recorder, so closing it means a governed deny renderer at the gate. The standing product resource (not exposed by the standard door) keeps its tool error.

## ccf_runtime.authz.delivery_boundary.govern_scope_denial

- Surface: ccf_runtime.authz.delivery_boundary.govern_scope_denial
- Public surface: true
- Change type: added
- Before: absent
- After: records a scope-mapping deny on a product read as the boundary's governed `subject-unavailable` refusal and returns the disclosed shell
- Why: R5-CP17-F01; Dave 2026-10-11 21:19 MST "Do (a)". Red test: `tests/mcp/test_undeclared_class_reads_as_unentitled.py::test_an_undeclared_class_and_an_unentitled_caller_get_one_reply`
- Migration: none

## ccf_runtime.mcp.tenancy.TenantGuardedServer.tool

- Surface: ccf_runtime.mcp.tenancy.TenantGuardedServer.tool
- Public surface: false
- Change type: reshaped
- Before: an authorizer deny always raised `ActionUnauthorizedRefused` (a `tenant-unauthorized` tool error)
- After: takes `on_denied: Callable[..., Any] | None = None`; when given, an authorizer deny is answered by `on_denied(grant=, tenant=, arguments=, denial=)` with no capability minted; `None` keeps the tool error
- Why: R5-CP17-F01; the product door answers its deny the governed way
- Migration: none

## ccf_runtime.mcp.egress.build_egress_server

- Surface: ccf_runtime.mcp.egress.build_egress_server
- Public surface: true
- Change type: behavior
- Before: `request_context_product` for a class outside the scope mapping returned a tool error naming the class
- After: it returns the governed refusal outcome (`isError` false), recorded, indistinguishable from an unentitled caller's
- Why: R5-CP17-F01; Dave 2026-10-11 21:19 MST "Do (a)". Red test as above; `tests/mcp/test_stdio_door_addresses.py` amended to the ruled behavior
- Migration: a client that read the `tenant-unauthorized` tool error for an unknown class reads a `subject-unavailable` refusal
