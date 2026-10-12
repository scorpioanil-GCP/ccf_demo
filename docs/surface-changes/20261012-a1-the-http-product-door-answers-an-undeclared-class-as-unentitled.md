# 20261012-a1 — on the HTTP product door, a class no scope mapping names reads as an unentitled caller's refusal

Finding R5-CP17-F01 (Dave, 2026-10-11 21:19 MST, verbatim *"Do (a)"*; acceptance 21:44: compare the complete public
refusal response, keep truthful audit events) carried from the MCP door (fragment 20261011-14) to the HTTP door, where
it was recorded as measured and open: the gate answered the authorizer's deny `403 request-unauthorized`, while an
unentitled caller asking for a real class got `404` and the governed `subject-unavailable` shell — a status that said
whether the class exists (`packaging/bank-controlled/BANK-PACKET.md` section 5).

What changed: a route may declare that it answers the AUTHORIZER's deny itself. The product route does. On a deny
there, the gate still decides and the authorizer still audits the deny (resource axis for an undeclared class); the
gate mints no capability and hands the route a `GateDenial` (grant, tenant, the deny's statement) instead of answering
`403`. The route runs the same request-shape checks it runs for every caller, then records the deny with
`govern_scope_denial` through the same recorder and emission site as an entitlement denial — internal truth
`SubjectUnavailableRefusal(cause="unauthorized", error_code="tenant-unauthorized", detail=<the gate's statement>)` on the
record only. The reply is identical to an unentitled caller's in status, headers and the whole JSON body but for the
per-answer record reference and the echo of the caller's own class. Authentication, the tenant floor, an unreadable
resource, the roster (SEC-017) and an unmintable allow still refuse at the gate, unchanged; every other route keeps the
gate's `403`. Red test: `tests/http_api/test_undeclared_class_reads_as_unentitled_http.py`.

## ccf_runtime.http_api.grants.GateDenial

- Surface: ccf_runtime.http_api.grants.GateDenial
- Public surface: true
- Change type: added
- Before: absent
- After: the authorizer's deny the gate hands to a route that answers its own — the verified grant, the selected tenant and the deny's internal statement; it carries no capability
- Why: R5-CP17-F01 on the HTTP door; the product route records the deny as the governed refusal an unentitled caller gets
- Migration: none

## ccf_runtime.http_api.grants.denial_from_request

- Surface: ccf_runtime.http_api.grants.denial_from_request
- Public surface: true
- Change type: added
- Before: absent
- After: returns the gate's `GateDenial` for this request, or `None` when the gate allowed it; refuses `403 no-capability` for a stashed object that is not a `GateDenial` or a deny handed to a route that does not declare it answers one
- Why: R5-CP17-F01; the one reader of the deny, beside `authorized_from_request`
- Migration: none

## ccf_runtime.authz.route_declaration.RouteAuthorization

- Surface: ccf_runtime.authz.route_declaration.RouteAuthorization
- Public surface: true
- Change type: reshaped
- Before: `action_id`, `resource`, `products`
- After: adds `answers_denial: bool = False` — whether the route answers the authorizer's deny itself as a governed refusal
- Why: R5-CP17-F01; the declaration is where a route states how its deny is answered, so the gate reads it rather than a path
- Migration: none; the default keeps the gate's `403`

## ccf_runtime.authz.route_declaration.authorizes

- Surface: ccf_runtime.authz.route_declaration.authorizes
- Public surface: true
- Change type: reshaped
- Before: `authorizes(action_id, *, resource, products=None)`
- After: `authorizes(action_id, *, resource, products=None, answers_denial=False)`
- Why: R5-CP17-F01; the product route passes `answers_denial=True`
- Migration: none

## ccf_runtime.http_api.app.create_app

- Surface: ccf_runtime.http_api.app.create_app
- Public surface: true
- Change type: behavior
- Before: `GET /product/{tenant}/{product_class}/{version}` answered an authorizer deny (a class the scope mapping names nowhere, or a credential whose scope lacks the product action) `403 request-unauthorized`
- After: it answers that deny as the recorded governed refusal — `404 subject-unavailable` at minimal disclosure — indistinguishable from an unentitled caller's refusal of a real class; the deny stays on the audit log and its reason (`tenant-unauthorized`) is on the replay record only
- Why: R5-CP17-F01; Dave 2026-10-11 21:19 MST "Do (a)". Red test: `tests/http_api/test_undeclared_class_reads_as_unentitled_http.py::test_an_undeclared_class_and_an_unentitled_caller_get_one_reply_over_http`
- Migration: a client that read `403 request-unauthorized` from the product route for an unknown class, or for a credential lacking the product action, reads the `subject-unavailable` refusal (the `403` stays for authentication, tenant, roster and every other route)
