# 20261011-23 — a held review item is released through the standard review door

Dave, 2026-10-11 20:19 MST (the second bounded SDK round): *"Review release must use the authorized, target-bound
approval path."* Finding (round 3, cp-15 `UBO-G12`/`UBO-G13`): since `D-IMPL-353`, `ReviewQueue.release` takes an
`Authorized[HitlSubmit]` minted by a door's gate for exactly the event released, and the authenticated HITL door
(`build_hitl_server`) requires an authorizer over a scope mapping a deployment can neither register nor declare — so a
deployment holding a review queue had no supported way to let a human release an item.

What changed: `ccf_runtime.mcp.review_door.open_review_door` composes the standard HITL door over the deployment's
`ReviewQueue`. Over its own Control Plane it registers ONE scope mapping (an audited `composition` event and a
`CompositionRegister` for exactly that key) granting each deployment-stated scope the queue read and the action submit
for the deployment's tenant on exactly the event-key patterns the deployment states, and pins the authorizer at that
version. The action route sends `approve` to `ReviewQueue.release` and `reject` to `ReviewQueue.reject` with the
gate-minted capability and the door-minted binding; any other verdict is refused (`ReviewActionRefused`) before the
queue is touched. A release is therefore bound to its target three ways: the authorizer allowed this event key for
this credential's scope; the capability names this event key; the binding echoes this item's content hash.
`ccf_runtime.mcp.review_door` is added to the authorization lint's composition roots
(`tools/lints/authorization_invariant.py::COMPOSITION_MINT_SITES`) — it mints `CompositionRegister` for its one key,
as `product_door` does, and nothing else. Measured in `tests/mcp/test_review_door.py` over the real MCP door.

## ccf_runtime.mcp.review_door.open_review_door

- Surface: ccf_runtime.mcp.review_door.open_review_door
- Public surface: true
- Change type: added
- Before: absent — no supported way to release a held review item after D-IMPL-353
- After: `open_review_door(queue, *, tenant_id, token_verifier, reviewer_scopes, clock) -> ReviewDoor`; `reviewer_scopes` maps scope → review event-key patterns (D-01 grammar); an empty mapping or a scope with no pattern is refused
- Why: round 5 item 3; Dave 2026-10-11 20:19 MST. Red tests: `tests/mcp/test_review_door.py::test_an_authorized_reviewer_bound_to_the_item_releases_it`, `::test_a_reviewer_whose_scope_does_not_reach_the_item_is_refused`
- Migration: a deployment that called `ReviewQueue.release(tenant=..., principal=...)` releases through this door instead; the reviewer's binding is minted by the door from the verified credential's authentication claims

## ccf_runtime.mcp.review_door.ReviewDoor

- Surface: ccf_runtime.mcp.review_door.ReviewDoor
- Public surface: true
- Change type: added
- Before: absent
- After: the opened review door; `server(issuer_url=..., resource_server_url=...)` returns the unstarted standard HITL `FastMCP`; `control_plane` holds the scope mapping and every authorization decision's audit event
- Why: round 5 item 3
- Migration: none

## ccf_runtime.mcp.review_door.ReviewActionRefused

- Surface: ccf_runtime.mcp.review_door.ReviewActionRefused
- Public surface: true
- Change type: added
- Before: absent
- After: raised when a review action's verdict is neither `approve` nor `reject`, before the queue is touched
- Why: round 5 item 3
- Migration: none
