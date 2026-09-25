# 353-06 — the approval record is server-attested; the HITL handles require the capability for their own action

`D-IMPL-353` §2 P6 and §2 P4, Lane HITL-DOOR. The close panel (`D-IMPL-352`)
found that both HITL doors took the approver's *whole* principal binding from
the request — subject compared with the verified identity (D-IMPL-67),
identity provider, method, **assurance level**, session and action time passed
through verbatim — so a step-up-MFA claim was a thing the approver typed into
their own audit record (P6); and that the MCP HITL body asked an *optional*
authorizer, `if authorizer is None: return` (P4). Under the accepted design
the binding is **minted by the door** from three things no caller writes —
the capability's principal, the verified credential's authentication claims,
and the door's injected clock — and the transport handles **require** the
capability for exactly their action (§1.2): `submit` an
`Authorized[HitlSubmit]` for the event, the served queue view an
`Authorized[HitlQueueRead]`.

## What did NOT change, stated first

- **`HumanPrincipalBinding` is byte-identical in shape.** The four D-IMPL-21
  fields are what they were; what changed is *who writes them*.
- **The gate-authority logic in `ApprovalGate.resolve` is untouched beyond
  what `submit` forces.** TOCTOU guard, signed-binding enforcement, audit
  records, rollback on a refused submit — all as they were. The one addition
  is `verify` at entry (below), and the `tenant` keyword becoming
  `authorized.tenant`.
- **The in-process transport reads keep their tenant parameter.** `pending`,
  `submissions`, `remove`, `dequeue` and `enqueue` are unchanged: their
  callers — the four primitives and the workflow engine — hold
  `HitlSubmit`/`Execute`/`Resume` capabilities, not a queue-read one, and
  in-process trust is the deployment's (design §5). The served doors call
  `view` and `submit` and nothing else.
- **The D-16 signed-binding leg's mechanics are unchanged.**
  `sign_principal_binding`, `verify_principal_binding`, `enforce_signed_binding`
  and `HitlPolicy` are as they were. What a signer must sign changed — see THE
  LIMIT.
- **No workflow, agent or policy artifact schema changed.**
- **The `ccf hitl submit` verb's code is unchanged** — it posts the operator's
  document verbatim; the document's shape is what changed (Migration, below).

## ccf.hitl.principal.AuthenticationClaims

- Surface: ccf.hitl.principal.AuthenticationClaims
- Public surface: true
- Change type: added
- Before: absent — the identity-provider reference, method, assurance level
  and session reference on a binding had no source in the SDK's contracts
  other than whatever the request carried
- After: a `CCFContract` of exactly those four required fields: what the
  deployment's credential verifier states about HOW a bearer authenticated.
  Carried on the verified grant and, on the MCP transports, in
  `AccessToken.claims` under `AUTHENTICATION_CLAIM`
- Why: P6. The doors' ONLY source for those four values must be something the
  caller cannot author. A request body or tool argument naming an assurance
  level makes step-up MFA a thing the caller types into their own audit record
- Migration: a deployment's token source attaches one to each grant it mints
  (`TokenGrant.authentication`, Lane MCP's fragment). A credential without one
  cannot approve anything — the doors refuse rather than fill the blank

## ccf.hitl.principal.AUTHENTICATION_CLAIM

- Surface: ccf.hitl.principal.AUTHENTICATION_CLAIM
- Public surface: true
- Change type: added
- Before: absent
- After: `"ccf.authentication"` — where a verified caller's
  `AuthenticationClaims` travel inside the MCP library's `AccessToken.claims`;
  the sibling of `ccf_runtime.mcp.auth.TENANT_CLAIM`
- Why: the MCP door reads the claims off the verified token, and the token
  verifier writes them; one wire key, held beside the contract it carries,
  keeps the writer and the single reader
  (`runtime/ccf_runtime/identity_binding.py::authentication_of_token`) agreeing
- Migration: none for a caller — nothing on the wire can author this claim

## ccf.hitl.principal.validate_content_hash

- Surface: ccf.hitl.principal.validate_content_hash
- Public surface: true
- Change type: added
- Before: the lowercase-sha256 check lived only inside
  `HumanPrincipalBinding`'s private field validator
- After: a module function both `HumanPrincipalBinding` and the door-facing
  `HitlActionRequest` validate through
- Why: the request a human sends and the binding the door mints from it must
  agree about what a product identity looks like; one function cannot drift
  into two readings
- Migration: none

## ccf.hitl.transport.HitlActionRequest

- Surface: ccf.hitl.transport.HitlActionRequest
- Public surface: true
- Change type: added
- Before: absent — `POST /hitl/actions` took a `HitlActionSubmission`, binding
  included, and the MCP tool took every binding field as an argument
- After: the caller-facing half of the authority path: `event_key`, `action`,
  `product_content_hash` (validated), `annotation` and `signed_binding` — and
  nothing else. No `principal`, no `subject_id`, no `identity_provider_ref`,
  no `method`, no `assurance_level`, no `session_ref`, no `action_time`, no
  `tenant`. `extra=forbid` makes a body that still sends any of them a 422
- Why: P6 — what only the human can state is the event, the verdict, the hash
  of what they saw, a note, and (where policy requires it) a signature. A
  caller-typed step-up claim becomes unrepresentable, not refused
- Migration: an HTTP client or `ccf hitl submit` document drops the
  `principal` object and the `tenant` field and sends the five fields above.
  A document that still carries them is refused with 422 naming the field

## ccf.hitl.transport.PrincipalMismatchRefused

- Surface: ccf.hitl.transport.PrincipalMismatchRefused
- Public surface: true
- Change type: added
- Before: absent — the transport recorded whatever subject the submission's
  binding named
- After: a `PermissionError` raised by `submit` when the binding's
  `approver.subject_id` is not `authorized.principal`, before anything is
  recorded and before the claim is consumed
- Why: the recorded actor has ONE source — the principal the authorizer
  decided *allowed* for. Unreachable from the doors (they mint the binding from
  the capability); it exists for an in-process caller that built a binding for
  the wrong subject. Refused rather than rewritten because a signed binding
  covers the subject, and a transport that overwrote it would record a
  signature over someone else
- Migration: an in-process caller of `resolve`/`submit` mints its capability
  for the subject its binding names

## ccf.hitl.AuthenticationClaims

- Surface: ccf.hitl.AuthenticationClaims
- Public surface: true
- Change type: added
- Before: absent
- After: re-export of `ccf.hitl.principal.AuthenticationClaims`
- Why: the package surface mirrors the module surface, as it does for every
  other principal contract
- Migration: none

## ccf.hitl.AUTHENTICATION_CLAIM

- Surface: ccf.hitl.AUTHENTICATION_CLAIM
- Public surface: true
- Change type: added
- Before: absent
- After: re-export of `ccf.hitl.principal.AUTHENTICATION_CLAIM`
- Why: package surface mirrors module surface
- Migration: none

## ccf.hitl.HitlActionRequest

- Surface: ccf.hitl.HitlActionRequest
- Public surface: true
- Change type: added
- Before: absent
- After: re-export of `ccf.hitl.transport.HitlActionRequest`
- Why: package surface mirrors module surface
- Migration: none

## ccf.hitl.PrincipalMismatchRefused

- Surface: ccf.hitl.PrincipalMismatchRefused
- Public surface: true
- Change type: added
- Before: absent
- After: re-export of `ccf.hitl.transport.PrincipalMismatchRefused`
- Why: package surface mirrors module surface
- Migration: none

## ccf_runtime.identity_binding.principal_from_authorized

- Surface: ccf_runtime.identity_binding.principal_from_authorized
- Public surface: true
- Change type: added
- Before: absent — see `principal_from_token_grant`, removed below
- After: `(authorized: Authorized[HitlSubmit], *, authentication:
  AuthenticationClaims, action_time: datetime, product_content_hash: str) ->
  HumanPrincipalBinding`. The subject is `authorized.principal`; the four
  claim axes are copied verbatim from `authentication`; the time is the
  caller's injected clock reading; the hash is the one value the human states.
  There is no parameter for the subject and none for any claim axis
- Why: P6, as mechanism: a binding minted from what the door verified, with
  no slot a caller could write an audit fact into. Both doors call it and
  nothing else constructs a binding on a served path
- Migration: a composition that called `principal_from_token_grant(grant=...,
  assurance_level=..., ...)` now holds the capability the gate minted and the
  grant's `authentication`, and calls this with the door's clock

## ccf_runtime.identity_binding.attested_authentication

- Surface: ccf_runtime.identity_binding.attested_authentication
- Public surface: true
- Change type: added
- Before: absent
- After: `(claims: AuthenticationClaims | None) -> AuthenticationClaims` —
  returns the claims or raises `AuthenticationUnattested`; the one place
  "the verifier said nothing" becomes a refusal
- Why: both doors call it on what their reader returned, so the refusal's
  shape and prose are one thing that cannot drift between them (the D-16
  door-mapping pattern)
- Migration: none

## ccf_runtime.identity_binding.authentication_of_grant

- Surface: ccf_runtime.identity_binding.authentication_of_grant
- Public surface: true
- Change type: added
- Before: absent
- After: `(grant: TokenGrant) -> AuthenticationClaims | None` — the HTTP
  door's single read of the claims off the verified grant
- Why: one reader per stash, as `granted_tenants` is for the tenant claim.
  **Depends on `TokenGrant.authentication`, owed by Lane MCP** (their
  fragment); until it lands this function is the one `mypy --strict`
  `attr-defined` site in this lane
- Migration: none

## ccf_runtime.identity_binding.authentication_of_token

- Surface: ccf_runtime.identity_binding.authentication_of_token
- Public surface: true
- Change type: added
- Before: absent
- After: `(token: AccessToken) -> AuthenticationClaims | None` — the MCP
  door's single read of the claims off the verified token, under
  `AUTHENTICATION_CLAIM`; an absent or malformed claim reads as `None`
- Why: mirrors `ccf_runtime.mcp.auth.granted_tenants` — unparseable is not
  permissive, and `None` is refused by `attested_authentication`
- Migration: none

## ccf_runtime.identity_binding.AuthenticationUnattested

- Surface: ccf_runtime.identity_binding.AuthenticationUnattested
- Public surface: true
- Change type: added
- Before: absent
- After: a `PermissionError`: the verified credential states nothing about
  how its bearer authenticated, so no binding can be minted from it
- Why: a deployment posture rather than a caller fault — the token source
  decides what a grant carries — and refused rather than defaulted because
  the only alternative is the server inventing an assurance level
- Migration: mint credentials that carry `authentication` claims

## ccf_runtime.identity_binding.ERROR_AUTHENTICATION_UNATTESTED

- Surface: ccf_runtime.identity_binding.ERROR_AUTHENTICATION_UNATTESTED
- Public surface: true
- Change type: added
- Before: absent
- After: `"authentication-unattested"` — the error code both doors carry for
  `AuthenticationUnattested` (HTTP: 403 detail; MCP: the `ValueError` JSON
  payload)
- Why: raised here, once, and mapped by each door into its own shell. Lives
  beside the mechanism rather than in `ccf_runtime.http_api.errors`; moving
  it there is a one-line join item if the door-shared vocabulary is preferred
- Migration: none

## ccf_runtime.identity_binding.principal_from_token_grant

- Surface: ccf_runtime.identity_binding.principal_from_token_grant
- Public surface: true
- Change type: removed
- Before: `(grant, identity_provider_ref, method, assurance_level,
  session_ref, action_time, product_content_hash)` — the subject fixed to
  `grant.client_id`, every other axis of the binding taken from its caller
- After: gone. Replaced by `principal_from_authorized`
- Why: its signature IS the P6 hole. The doors passed those parameters through
  from the request, and a function that accepts a caller's assurance level
  cannot be made safe by asking its callers to be careful
- Migration: `principal_from_authorized` (above). `tests/http_api/test_auth.py`
  still imports the old name — a join item, not a compatibility shim

## ccf_runtime.mcp.hitl_server.NaiveActionTimeRefused

- Surface: ccf_runtime.mcp.hitl_server.NaiveActionTimeRefused
- Public surface: true
- Change type: removed
- Before: raised when the caller's `action_time` argument carried no UTC
  offset
- After: gone. `action_time` is not a tool argument; the door stamps it from
  the injected clock, and an injected clock that returned a naive instant is
  refused by the contract's own canonicalizer (D-IMPL-38) as before
- Why: a refusal for a value that can no longer be presented would be dead
  code carrying a live-looking name
- Migration: none for a caller. Two docstrings in
  `runtime/ccf_runtime/mcp/egress.py` cite it as precedent — prose only, a
  join nit

## ccf_runtime.mcp.hitl_server.SubjectIdentityConflictRefused

- Surface: ccf_runtime.mcp.hitl_server.SubjectIdentityConflictRefused
- Public surface: true
- Change type: removed
- Before: raised when the caller-typed `subject_id` argument did not match the
  verified token identity (D-IMPL-67 item 2)
- After: gone. There is no `subject_id` argument; the subject is
  `authorized.principal` and nothing can conflict with it
- Why: the conflict is unrepresentable, and a refusal for an unrepresentable
  input is the checklist shape the design rejects
- Migration: `tests/crossproc/test_hitl_mcp.py` imports it — a join item

## ccf_runtime.mcp.hitl_server.build_hitl_server

- Surface: ccf_runtime.mcp.hitl_server.build_hitl_server
- Public surface: true
- Change type: reshaped
- Before: `(*, server_name, queue_view, action_route, token_verifier,
  auth_settings, authorizer: TenantAuthorizerProtocol | None = None)`
- After: `(*, server_name, queue_view, action_route, token_verifier,
  auth_settings, authorizer: TenantAuthorizerProtocol, clock: Callable[[],
  datetime])` — the authorizer **required** and handed to the tenancy wrapper,
  which mints each body's capability from its decision; the clock **required**
  and the only source of `action_time`
- Why: P4 — `authorizer: ... | None = None` is `D-IMPL-73`'s signature and §4's
  lint refuses it; P6 — an approval's time is the deployment's statement, never
  a wall clock read in the body and never a value the caller sends
- Migration: every builder call passes `authorizer=` and `clock=`. In-tree:
  `tests/crossproc/servers/mcp_hitl_child.py`, `tests/crossproc/test_hitl_mcp.py`,
  `tests/crossproc/test_mcp_tenant_authz.py`,
  `tests/crossproc/test_fastmcp_resource_token_spike.py`,
  `tests/mcp/guarded_servers.py` — join items, listed in the lane report

## ccf.hitl.transport.HitlActionSubmission

- Surface: ccf.hitl.transport.HitlActionSubmission
- Public surface: true
- Change type: reshaped
- Before: `event_key, tenant, action, principal, annotation, signed_binding,
  answered_event_class, answered_workflow_state_ref`
- After: `tenant` **deleted**; `authorizing_decision_id: str | None`
  **added**, transport-stamped from `authorized.decision_id` on every submit
  and hash-transparent at its sentinel (CINV-06)
- Why: §1.3 — the tenant a record is filed under is the capability's, and a
  second source on the contract is a value a door could forget to compare;
  design §3 — every recorded human action names the decision that authorized
  it
- Migration: constructors drop `tenant=`. Consumers that matched on
  `submission.tenant` — the workflow engine's `_gate_authority` and
  `_escalation_authority` (`runtime/ccf_runtime/workflow/engine.py`) — read the
  tenant they already hold instead; a join item for Lane ENGINE

## ccf.hitl.HitlActionSubmission

- Surface: ccf.hitl.HitlActionSubmission
- Public surface: true
- Change type: reshaped
- Before: as the module entry
- After: as the module entry (re-export)
- Why: package surface mirrors module surface
- Migration: as the module entry

## ccf_runtime.mcp.hitl_server.HitlQueueViewProtocol

- Surface: ccf_runtime.mcp.hitl_server.HitlQueueViewProtocol
- Public surface: true
- Change type: reshaped
- Before: `__call__(self, *, tenant: str) -> tuple[PendingHitlEvent, ...]`
- After: `__call__(self, authorized: Authorized[HitlQueueRead]) ->
  tuple[PendingHitlEvent, ...]` — the deployment's callable is
  `transport.view` under the capability the wrapper minted
- Why: §1.2 — whose queue is read is `authorized.tenant`, not a parameter the
  server decides
- Migration: a deployment's queue view takes the capability and calls
  `transport.view(authorized)`

## ccf_runtime.mcp.hitl_server.HitlActionRouteProtocol

- Surface: ccf_runtime.mcp.hitl_server.HitlActionRouteProtocol
- Public surface: true
- Change type: reshaped
- Before: `__call__(self, *, submission) -> str`
- After: `__call__(self, authorized: Authorized[HitlSubmit], *, submission)
  -> str`
- Why: the route composes the primitives, each of which now requires the
  capability this door received
- Migration: a deployment's route takes the capability first and passes it to
  the primitive it resolves through

## runtime/ccf_runtime/http_api/routes/hitl.py

- Surface: runtime/ccf_runtime/http_api/routes/hitl.py
- Public surface: false
- Change type: behavior
- Before: `POST /hitl/actions` took a `HitlActionSubmission` — binding
  included — compared `submission.tenant` with the grant's tenant (403
  `ERROR_TENANT_UNAUTHORIZED`), compared `principal.approver.subject_id` with
  `grant.client_id` (403 `ERROR_SUBJECT_CONFLICT`), and derived the recorded
  binding through `principal_from_token_grant` with the body's identity
  provider, method, assurance level, session and action time passed through.
  `GET /hitl/queue` read `transport.pending(tenant=grant tenant)`
- After: the body is `HitlActionRequest`. The handler reads the capability the
  gate minted (`request.state.authorized`, narrowed to `HitlSubmit`), the
  verified grant's `authentication` claims (403
  `ERROR_AUTHENTICATION_UNATTESTED` when absent) and the bundle's injected
  `clock`, mints the binding through `principal_from_authorized`, and calls
  `transport.submit(authorized, submission=...)`. The receipt's `submission`
  is the RECORDED copy the transport returned. `GET /hitl/queue` calls
  `transport.view(authorized)` under `HitlQueueRead`. Neither route calls
  `tenant_from_request` any more. Both routes declare their action as the
  kind's own `action_id`, so the declared action and the kind the handler asks
  for are one symbol
- Why: P6 and §1.2. The two 403 refusals are gone because the things they
  refused are unrepresentable
- Migration: an HTTP client sends the five `HitlActionRequest` fields. The
  bundle grows `ApiDependencies.clock` (owed at the join — this lane codes
  against it; without it the route module type-checks red at one line and the
  route refuses with the typed 503 for an absent handle)

## runtime/ccf_runtime/mcp/hitl_server.py

- Surface: runtime/ccf_runtime/mcp/hitl_server.py
- Public surface: false
- Change type: behavior
- Before: `submit_hitl_action(tenant, event_key, action, subject_id,
  identity_provider_ref, method, assurance_level, session_ref, action_time,
  product_content_hash, annotation=None, signed_binding_signature=None,
  signed_binding_key_id=None)`; `hitl_queue(tenant)`; a per-body
  `_enforce_tenant_authz` helper asked an optional authorizer and returned
  early when none was bound
- After: `submit_hitl_action(authorized: Authorized[HitlSubmit], tenant,
  event_key, action, product_content_hash, annotation=None,
  signed_binding_signature=None, signed_binding_key_id=None)` and
  `hitl_queue(authorized: Authorized[HitlQueueRead], tenant)`. Each body
  receives its capability from the tenancy wrapper as its first argument —
  stripped from the wire schema, minted for the action each registration
  declares (`action=HitlSubmit, resource=door.from_argument("event_key")`;
  `action=HitlQueueRead, resource=door.route()`) — and holds no authorizer.
  The binding is minted from `authorized.principal`, the verified token's
  claims (`ValueError` carrying `ERROR_AUTHENTICATION_UNATTESTED` when absent)
  and the injected `clock`. The route receives `(authorized, *, submission)`
- Why: P4 and P6
- Migration: the wrapper wiring — `TenantGuardedServer` taking the authorizer,
  `tool`/`resource` taking `action=`/`resource=`, the guard minting and
  injecting — is Lane MCP's and is a join item; this module codes against it

## METHOD RESHAPES THE MANIFEST DOES NOT CAPTURE — recorded here, not claimed

`D-IMPL-122` descoped the multi-method Protocols and the classes whose public
contract is a method set: the surface manifest records them shapeless, so a
method reshape under their fqn is not a claim the completeness gate can check
(it refuses a `reshaped` claim for a name it does not carry). They are
recorded as prose so the join has them; each is real and each has a test.

- **`ccf.hitl.approval_gate.ApprovalGate.resolve`** (and the `ccf.hitl`
  re-export): `resolve(self, *, tenant, event_key, action, principal,
  annotation=None, signed_binding=None)` →
  `resolve(self, authorized: Authorized[HitlSubmit], *, event_key, action,
  principal, annotation=None, signed_binding=None)`. `verify` for `HitlSubmit`
  on `event_key` is the first statement; the tenant is `authorized.tenant`;
  the submit presents `authorized`. Why: what the `submit` signature forces,
  plus one line — the resolver claims the event (`remove`) and can audit
  (`resolved=False` on a hash mismatch) BEFORE it submits, so a capability
  that would die at the transport must die before the queue is touched
  (`tests/hitl/test_approval_gate.py::test_a_queue_read_capability_dies_at_the_primitive_before_anything_is_touched`).
  Migration: `gate.resolve(tenant=t, event_key=k, ...)` becomes
  `gate.resolve(<Authorized[HitlSubmit] for k under t>, event_key=k, ...)`;
  in-tree callers outside this lane — `tests/workflow/test_engine.py`,
  `tests/workflow/test_slice.py`, `tests/workflow/test_exception_paths.py`,
  `tests/crossproc/servers/mcp_hitl_child.py` — are join items.
- **`ccf.hitl.escalation.ExceptionEscalation.resolve`**: the same reshape,
  exactly; `escalate` is unchanged.
- **`ccf.hitl.override.OverrideBoundary.resolve`**: `resolve(self, *, tenant,
  event_key, principal, override=None, ...)` → `resolve(self, authorized, *,
  event_key, principal, override=None, ...)`; `propose` is unchanged.
- **`ccf.hitl.review_queue.ReviewQueue.release` / `.reject`**: `(self, *,
  tenant, event_key, principal, ...)` → `(self, authorized, *, event_key,
  principal, ...)`; `submit_for_review` and `items` are unchanged.
- **`ccf.hitl.transport.HITLTransportProtocol`** (and the `ccf.hitl`
  re-export): `submit(self, *, submission) -> None` →
  `submit(self, authorized: Authorized[HitlSubmit], *, submission) ->
  HitlActionSubmission` — verified by `ccf.authz.capability.verify` for
  `HitlSubmit` on `submission.event_key` before its first real statement,
  filed under `authorized.tenant`, returning the recorded (stamped) copy; and a
  NEW method `view(self, authorized: Authorized[HitlQueueRead]) ->
  tuple[PendingHitlEvent, ...]` — the served read, verified for `HitlQueueRead`
  on the queue-read action id, of `authorized.tenant`'s queue. Why: §1.2 — the
  authority path and the served read require the capability for their own
  action; a handler holding neither has nothing to pass and does not
  type-check (§1.4, `tests/hitl/test_capability_static.py`). Migration: a
  conforming implementation adds `view` and takes `authorized` first on
  `submit`; callers present the capability the gate minted.
- **`ccf.hitl.transport.InMemoryHitlTransport`** (and the `ccf.hitl`
  re-export): the reference implementation of the reshaped Protocol; `submit`
  additionally raises `PrincipalMismatchRefused` when the binding's subject is
  not `authorized.principal`, after `verify` and before the policy is resolved
  or the lock is taken (`tests/hitl/test_transport_capability.py`).

## THE LIMIT, STATED

- **The signed-binding leg now attests the server's statement.** A
  `SignedPrincipalBinding` verifies against the binding the DOOR mints —
  subject, claims and `action_time` included — so a production signer must
  sign what the server will mint, which means knowing the clock reading in
  advance. With a deterministic injected clock (as in every test here) that is
  exact; with a wall clock it is not. Either a two-phase door (mint → sign →
  submit) or a signed statement that excludes `action_time` closes it; neither
  is in this lane's remit and neither was ruled. Recorded as a D-16 follow-up
  in the lane report. What the leg DOES prove today is stronger than before: a
  signature over a higher assurance than the verifier stated is *invalid*
  (`tests/http_api/test_signed_binding_door.py::test_http_a_signed_binding_over_a_higher_assurance_than_the_tokens_is_invalid`)
- **In-process reads keep their tenant parameter** (What did NOT change). A
  door author who calls `transport.pending(tenant=...)` instead of
  `transport.view(authorized)` has reached inside the process; that is design
  §5's limit, stated, not a served-surface hole
- **On the served path the MCP body's `authorized.principal` and the token's
  `client_id` are the same value by construction**, so a severing that swapped
  one for the other reddens nothing there. The guard for a caller that mints
  for one subject and binds another is the transport's
  `PrincipalMismatchRefused`, measured at the transport

## Regression evidence

Every count below names its population and was measured with the four
handoffs applied locally as a measurement patch (`lane353-hitl-door-HANDOFFS.patch`
in the lane report — the gate stashing `authorized`, `TokenGrant.authentication`,
the wrapper minting, `ApiDependencies.clock`), because the doors cannot open
without the seams other lanes own. Every pytest invocation ran as
`PYTHONPATH=src:runtime` from the lane worktree — the bare form imports
`main`'s tree through the editable install and measures nothing about this
lane (coordinator, 2026-09-24); the probe was run and printed the worktree.

- **Owned population with the patch: 222 passed, 0 failed** — `tests/hitl`
  (all 15 files, 154 tests), `tests/http_api/test_hitl_door_identity.py` (15),
  `tests/http_api/test_signed_binding_door.py` (5),
  `tests/mcp/test_hitl_server_door.py` (6), plus the frozen seam's own
  `tests/authz/test_capability.py`, `tests/authz/test_capability_static.py` and
  `tests/invariants/test_src_does_not_import_runtime.py` (42, per the
  coordinator's relocation check).
- **The same four door files WITHOUT the patch: 1 passed, 12 failed, 17
  errors** (30 tests) — every red one of two seams: `ApiDependencies.__init__()
  got an unexpected keyword argument 'clock'` (×16) and `TokenGrant` refusing
  `authentication` (×12). Red for the right reason, by name.
- **`tests/hitl` before any edit: 127 passed** across the then-population
  (`tests/hitl` + the two `tests/http_api` files); after the contract change and
  before the transport tests were migrated the unmigrated `test_transport.py`
  was the only red (9 failed, 133 passed), on `extra_forbidden: tenant`.
- **§9 controls, each a named test in
  `tests/hitl/test_transport_capability.py`:** wrong kind at `submit` and at
  `view`; wrong resource at both; the positive control (actor is
  `authorized.principal`, filed under `authorized.tenant`, stamped with
  `authorized.decision_id`); four fabrications at both handles; a retarget;
  the principal mismatch; a caller-authored decision id discarded; no `tenant`
  field. The static tooth: `tests/hitl/test_capability_static.py` runs
  `mypy --strict` on `tests/hitl/static_controls/wrong_kind_hitl.py` and
  asserts both wrong-kind calls are incompatible-argument errors.
- **`mypy --strict` over the nine source files this lane touched: clean with
  the patch.** Without it, exactly two `attr-defined` errors, both at named
  handoff reads: `runtime/ccf_runtime/identity_binding.py::authentication_of_grant`
  (`TokenGrant.authentication`) and the `deps.clock` read in
  `runtime/ccf_runtime/http_api/routes/hitl.py::build_router`.
- **`python -m tools.lints --all`: rc 0**, after re-resolving one stale
  `::_enforce_tenant_authz` node-id citation in
  `docs/surface-changes/16-24-experience-door-entitlement.md` that this lane's
  deletion had orphaned.

## Sabotage verification

Each guard severed ALONE in the lane tree (patch applied), the named files
run, the file restored from the bytes read before severing. Baseline for every
population was 0 red. **Ten severings, ten reddened; none reddened nothing.**

| severing | population | red after | the tests that went red |
|---|---|---|---|
| S1 the HTTP door reads `assurance_level` from the BODY again | `test_hitl_door_identity.py` (15) | 2 | the `[assurance_level-aal3]` 422 case; `test_the_assurance_recorded_is_the_tokens_and_a_caller_cannot_raise_it` |
| S2 drop `verify()` in `InMemoryHitlTransport.submit` | `test_transport_capability.py` + `test_capability_static.py` (19) | 7 | wrong kind, wrong resource, retarget, all four fabrications at `submit` — **the 3 static tests stayed green: the two teeth are two** |
| S3 drop the principal-match refusal | `test_transport_capability.py` (16) | 1 | `test_a_binding_over_another_subject_than_the_principal_binds_nothing` |
| S4 stamp `authorizing_decision_id` from the caller's submission | `test_transport_capability.py` + `test_transport.py` (37) | 3 | caller-authored id discarded; the positive control; the transport equality test |
| S5 drop `verify()` in `InMemoryHitlTransport.view` | `test_transport_capability.py` (16) | 6 | wrong kind at view, wrong resource at view, all four fabrications at `view` |
| S6 HTTP door stamps `action_time` from the wall clock | identity + signed-binding + was-called (24) | 3 | `action_time == clock` control; the was-called `action_time` kwarg; the valid signed submission (signature no longer covers what the door minted) |
| S7 `attested_authentication` fills the blank instead of refusing | identity + MCP door + `test_principal_from_authorized.py` (26) | 3 | the unattested control at each of the three sites |
| S8 drop `verify()` at `ApprovalGate.resolve` (transport's still stands) | `test_approval_gate.py` (13) | 2 | both primitive controls — the decoy second event turns "claimed before the capability died, given back at the tail" into a visible reorder |
| S9 MCP door stamps `action_time` from the wall clock | MCP door + was-called (10) | 2 | `test_p6_the_binding_is_minted_from_capability_claims_and_clock`; `test_mcp_door_invokes_the_mint` |
| S10 restore a `tenant` field on `HitlActionSubmission` | `test_transport_capability.py` (16) | 1 | `test_the_submission_contract_carries_no_tenant_field` |

S8 is the one worth a sentence: on the first pass its two controls could not
have distinguished the primitive's `verify` from the transport's, because a
single pending event removed and re-enqueued at the tail is indistinguishable
from one never touched. The decoy event is what makes the claim-before-verify
observable. A severing that reddens nothing is a missing control, and that
one was found before it was reported as green.
