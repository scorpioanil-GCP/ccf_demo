# D-IMPL-353 — Authorization as a capability: unauthorized work is unrepresentable

**Status:** DESIGN, awaiting Dave's acceptance of THIS TEXT. **No implementation
until it is accepted.** Rewritten 2026-09-24 after Dave rejected the first
draft — a checklist design — with the ruling that a checklist does not ensure
success.

**Supersedes** the first draft of this file. Amends Tier 1 of the 2026-09-23
security remediation after the close panel (`D-IMPL-352`) rejected it.

---

## 0. The ruling this design answers

> *"The checklist design does not ensure success. Same shape as
> `StateWriteToken`: unauthorized work is unrepresentable, not 'missed a
> check.'"* — Dave, 2026-09-24

The first draft closed ten panel findings with ten repairs and a lint that
enumerated doors. Its correctness rested on the enumeration being complete. The
enumeration has been wrong three times in this remediation. A design whose
success depends on the author having found every door is not a design that
ensures anything.

This project already enforces one invariant the right way. Single-writer is not
a check; it is `StateWriteToken` (`src/ccf/controlplane/state.py::StateWriteToken`):

> *"Not constructible outside this module: the constructor demands the
> module-private sentinel, and `InMemoryStateStore.put` verifies the mint
> rather than trusting the type alone... This makes an unaudited write
> unrepresentable through the public write surface."*

Nobody checks whether a write was audited. An unaudited write cannot be
expressed. **Authorization gets the identical shape.**

---

## 1. The mechanism — four statements, and nothing else is the mechanism

### 1.1 `Authorized` is not constructible outside the gate module

A new type, `ccf_runtime.authz.capability.Authorized`, mirroring
`StateWriteToken` line for line:

- `__slots__`; a constructor that demands a **module-private sentinel** and
  raises otherwise; a `_minted` field set to that sentinel; a module-level
  `_verify(capability)` that checks the mint **by identity** (`is`), never by
  type — so a subclass that skips `__init__`, a `Mock`, an `object()`, or a
  duck-typed impostor is refused at the point of use.
- Fields, all frozen at mint: `tenant: str` (exactly one — see §1.3),
  `principal: str` (the verified `client_id`), `action: str` (the door-declared
  action id the decision was made for), `resource: str`, and `decision_id: str`
  (the audit event this capability is evidence of).
- **The only producer is the real token path.** Exactly two mint sites, both in
  the gate module: the HTTP `AuthorizationGate` after `TenantAuthorizerProtocol`
  returns *allowed*, and the MCP `TenantGuardedServer` wrapper at the same point.
  Nothing else in `src/`, `runtime/`, `examples/` or `tools/` may name the
  sentinel. A lint (§4) refuses a third mint site.

### 1.2 Every mutating handle and every tenant-read handle REQUIRES it

Not "checks it". *Requires it*, as a positional-or-keyword parameter with no
default, verified by identity on entry — exactly as `InMemoryStateStore.put`
requires and verifies the `StateWriteToken`.

The handles, with today's signature and the new one:

| handle | today | after |
|---|---|---|
| `ControlPlaneRegistry.register` / `register_typed` / `register_versioned` | `(key, artifact, ...)` | `(authorized, key, artifact, ...)` |
| `ControlPlaneStateStore.put` (both implementations) | `(record_class, key, record, token)` | `(authorized, record_class, key, record, token)` |
| `ArtifactStoreProtocol.put` (both implementations) | `(tenant_id, artifact_class, name, artifact, *, minted)` | `(authorized, artifact_class, name, artifact, *, minted)` — **`tenant_id` is deleted** |
| `WorkflowEngine.execute` / `resume` | `(workflow, *, execution_id, ...)` | `(authorized, workflow, *, execution_id, ...)` |
| `HITLTransportProtocol.submit` | `(*, submission)` | `(authorized, *, submission)` |
| `GrantLedger.request` / `revoke` | `(..., actor)` | `(authorized, ...)` — **`actor` is deleted**; the actor is `authorized.principal` |
| MCP `TenantGuardedServer` tool/resource bodies | receive raw arguments | receive `authorized` as their first argument, minted by the wrapper |
| the governed dereference (`govern_dereference`) and every tenant-scoped read | `(grant, ...)` | `(authorized, ...)` |

A handle that today takes `tenant_id`, `tenant`, or `actor` from its caller
**loses that parameter**. The value is `authorized.tenant` /
`authorized.principal`. There is no second source.

### 1.3 The tenant on the write IS the capability's tenant

This is the sentence that makes Fable's cross-tenant write inexpressible rather
than refused.

- The engine does not compare `workflow.definition.tenant` with anything. It
  receives `authorized` for tenant X and files the execution under X. If the
  workflow artifact declares some other tenant, the *factory* refuses to
  construct a handle for it under this capability — one refusal, at
  construction, before any state exists — because `WorkflowFactory.construct`
  also takes `authorized` and checks the artifact's tenant against
  `authorized.tenant` once. After that there is no tenant anywhere in the
  engine except the capability's.
- The artifact store files under `authorized.tenant`. `ArtifactPutRequest`,
  `put_artifact`'s `tenant_id` argument, and the store's `tenant_id` parameter
  are all deleted.
- The registry's key is checked once, at `register`: its tenant segment must
  equal `authorized.tenant`. That is the *one* comparison, and it is inside the
  handle that holds the capability, not in a door that might forget.

**Why exactly one tenant per capability.** `TokenGrant.tenants` is a set — an
operator credential legitimately spans tenants (`SEC-018`, Lane MCP's
reasoning, kept). But a *decision* is about one tenant. The gate selects it
from the grant's set — the request names one and it is a member; or the grant
holds exactly one; otherwise **refuse as ambiguous, the gate does not pick** —
and mints a capability for that one tenant. Everything downstream sees one
tenant, and it is the authorized one.

### 1.4 A handler with no capability does not type-check

A route handler, an MCP body, or an engine driver that wants to register,
write, execute, submit or read tenant data must pass `authorized` to the handle.
It can obtain one only from the gate. A handler that skips the gate has nothing
to pass; the call is a `mypy --strict` error; the build fails.

**`mypy --strict` is therefore the primary lint.** Not a grep I wrote — the type
checker this project already runs on every commit.

---

## 2. What becomes inexpressible

Stated as consequences of §1, so a reader can check each against the mechanism
rather than trusting the list.

| panel finding | why it cannot be expressed under §1 |
|---|---|
| **P2** cross-tenant workflow invocation / agent declaration | the engine and registry have no tenant but `authorized.tenant`; the artifact's declared tenant is checked once at factory construction against the capability and never consulted again |
| **P1** the HTTP door refusing every real credential | there is one reader, `tenants_of_grant`, over the one field, `tenants`; `.tenant` and the test-only `TenantedTokenGrant` are deleted, so the fixture cannot pass a shape production never mints |
| **P3** the governed-class store guard inert by default | a client cannot reach `ArtifactStoreProtocol.put` without a capability; a capability's `action` is checked against the class's declared write action at the store — a `decision-replay-record` write needs `replay.mint`, which no door declares, so no served surface can mint one. `GovernedWriteHandle` is retired: the capability's action IS the mint |
| **P4** MCP HITL authorizer optional | the MCP body receives `authorized` from the wrapper or receives nothing; there is no `authorizer=None` arm because there is no `authorizer` parameter on the body |
| **P5** untenanted MCP artifact read by hash | `govern_dereference` requires `authorized`; the blob/meta resources go through it because there is no other way to call the store's read |
| **P6** caller-typed assurance on the approval record | `HumanPrincipalBinding` is minted by the door from `authorized` + the verified token's claims + the server clock; the body carries `product_content_hash` and `annotation` and nothing else — the assurance field is deleted from the request contract |
| **P9** raw registration behind the MCP wrapper | a raw-registered body has no `authorized` to pass to any handle; it cannot do anything, and §4's lint refuses the registration anyway |

Rule of reading: if a finding's closure is described here as a *check*, this
document has failed its own ruling and must be corrected.

---

## 3. Consequences kept from the first draft — as consequences, not mechanism

Each of these falls out of §1 or is required to make §1 hold. None is a
separate safety mechanism.

- **Server-attested approval fields** (§2, P6): a consequence of the door
  minting the binding from the capability.
- **Deny audit contents**: `AuthzDecisionAuditEvent` carries `resource`,
  `matched_resource_pattern` and the failing axis, and the capability carries
  the `decision_id` of the *allow* — so every action is traceable to the
  decision that authorized it, and every refusal says what it refused.
- **MCP HITL authorizer required**: a consequence of the body having no
  authorizer parameter at all.
- **Artifact GET via governed dereference**: a consequence of there being no
  other read path.
- **`create_app` refuses mismatched wiring**: a recorder naming a replay class
  over a store with no declared write action for it, or a store declaring an
  action no door can mint — refused at boot in both directions.
- **Delete `.tenant` and `TenantedTokenGrant`**: a consequence of §1.3's single
  reader. The fixture mints real `TokenGrant`s through the real
  `FileTokenSource` or `StaticTokenSource`.
- **Acting tenant from the grant set only**: §1.3 verbatim.
- **`--local` stays suspended**: a local deployment that cannot mint a
  capability has nothing to hand its handles.

---

## 4. Still required beside `mypy` — the `None`-default lint

Types do not catch `authorized: Authorized | None = None`, nor
`authorized: object`, nor a call site passing `None  # type: ignore`. That
pattern **is** `D-IMPL-73`, and it is the pattern behind P4 and behind the
original finding. So one lint stays, narrowed to what the type checker cannot
see:

`tools/lints/authorization_invariant.py` refuses, in `runtime/` and `src/`:

1. any parameter annotated with an authority type — `Authorized`,
   `TenantAuthorizerProtocol`, `HttpAuthProtocol`, `TokenVerifier`,
   `TokenSourceProtocol` — that carries a default, `None` or otherwise;
2. any such parameter annotated `object`, `Any`, or a union with `None`;
3. any construction of `Authorized` outside `ccf_runtime.authz.capability`,
   and any reference to its sentinel outside that module;
4. any `@server.tool` / `@server.resource` registration outside the
   `TenantGuardedServer` wrapper.

**Fork-point red is the acceptance test.** Run this lint against `d895d889`. It
must report `create_app(deps, auth=None, authorizer=None, ...)` — `D-IMPL-73`'s
own signature. A lint that would not have caught the original defect is not the
lint, and the lint's own test asserts this by checking out the fork point.

---

## 5. The limit, named

**In-process code that already holds the registry, the state store, or the
artifact store can still write.** A caller with `ControlPlaneRegistry` in hand
can call `register(...)` — it needs an `Authorized`, and `_verify` refuses an
impostor, but it can also reach the underlying dict. That is the same limit
single-writer has, and `StateWriteToken`'s docstring states it:

> *"reflection and private-construction bypasses are lint- and CI-covered,
> never claimed impossible."*

**The claim this design makes is: no served surface can perform an unauthorized
operation.** HTTP, MCP (HTTP and stdio), the CLI's remote leg, and every
orchestration driver reach the fabric only through handles that require a
capability only the gate mints. In-process trust — code the deployment linked
into its own process — is the deployment's, as it is for single-writer.

A bank's reviewer should hear that sentence exactly as written, and the
`SECURITY.md` this remediation owes them says it.

---

## 6. The MCP round-trip — in this design, not set aside again

The first design workflow set the capability model aside because "the tenant
field cannot survive the round-trip through the MCP library's own token
object." That was wrong, and it cost an iteration. The round-trip is **four
lines and it is already landed on this branch**:

- `TokenGrant.tenants` → `tenant_claims(grant)` → `AccessToken.claims`
  (the library's own field; `mcp==1.28.1` `AccessToken` carries `claims`,
  `subject`, `resource` — measured);
- `get_access_token()` → `granted_tenants(token)` → `TokenGrant(...,
  tenants=...)` at the four reconstruction sites (`hitl_server.py` ×2,
  `product_door.py`, `product_entitlement.py::verified_grant`), all migrated.

The MCP wrapper mints `Authorized` from exactly that reconstructed grant. Nothing
about the library stands in the way, and the design does not discuss it further.

---

## 7. Unchanged rulings

- **`SEC-005` / `SEC-006` stay out** (verdict signing; approver eligibility and
  four-eyes). Tier 2, different mechanisms. The capability makes four-eyes
  *representable* — a second `Authorized` for `hitl.approve` from a different
  principal — which is the precondition Tier 2 needs.
- **The eight edited example servers are reverted** (`cp-16/17/18/19/21/23/24`
  and `hw1`'s tenancy edit stays, since hw1 is not a frozen `cp-*` specimen and
  the edit is what `D-IMPL-261`'s exception clause permits). A gap-ledger entry
  records that the seven do not build under Tier 1 — evidence that a real
  deployment needs a scope mapping the examples never declared.
- **`D-IMPL-348` (the v1.0.0 release) is untouched.** No re-tag, no rewrite of
  the release record; the remediation lands on `security-tier-0` and merges to
  `main` under its own gate.
- **The panel runs after the capability ships, not after a green board.** A
  green suite was the state in which the HTTP door was unopenable. The panel is
  briefed on the capability as the mechanism and asked, specifically, to find a
  served surface that reaches a handle without it.

---

## 8. Effort and lanes

The blast radius is every mutating handle signature — the same radius
`StateWriteToken` had. Nothing has shipped; nothing external breaks.

| lane | scope | h | owns |
|---|---|---|---|
| **capability + gate** | §1.1, the HTTP gate mint, `tenants_of_grant`, delete `.tenant`/subclass | 8 | `authz/`, `http_api/gate.py`, `tests/http_api/gate_fixtures.py` |
| **handles** | §1.2 signatures on registry, state store, artifact store, grant ledger; delete `tenant_id`/`actor` | 10 | `src/ccf/controlplane/`, `src/ccf/artifacts/`, `src/ccf/skills/grants.py` |
| **engine + factory** | §1.3 for `execute`/`resume`/`construct` | 5 | `workflow/`, `src/ccf/workflow/factory.py` |
| **MCP** | the wrapper mint, bodies take `authorized`, governed dereference on blob/meta | 6 | `mcp/` |
| **HITL door** | §2 P6 — binding minted from capability + claims + clock | 4 | `routes/hitl.py`, `mcp/hitl_server.py`, `identity_binding.py`, `src/ccf/hitl/principal.py` |
| **lint** | §4, with the fork-point acceptance test | 5 | `tools/lints/` — **depends on nothing; starts first** |
| **examples + ledger** | §7 revert + gap entry | 1 | seven `serve.py`, `docs/` |
| **join** | regenerate once, sabotage the merged tree, **panel** | 8 | — |

**~47h; ~16h wall-clock across seven lanes.** Lane ownership is disjoint; the
one contested file (`gate_fixtures.py`) belongs to the capability lane.

---

## 9. What "accepted" means for this text, and "done" for the work

**Accepted** means Dave agrees §1 is the mechanism and §2 follows from it. Any
finding whose closure in §2 reads as a *check* is a defect in this document.

**Done** means:

1. A `TokenGrant` minted through the **real** `FileTokenSource` opens the HTTP
   door and the MCP door. No subclass exists to fake it.
2. Fable's two reproductions exist as tests. They do not assert a 403; they
   assert that **the call cannot be constructed** — the factory refuses the
   handle, and no state exists under the other tenant.
3. `mypy --strict` fails on a handler that reaches any handle in §1.2 without
   `authorized`. Demonstrated by a committed negative control that is
   `# type: ignore`-free and red.
4. The lint is **red at `d895d889`** and green at the tip.
5. Sabotage on the merged tree, each guard severed alone — and the severings
   include: *mint `Authorized` from a stub sentinel*, *pass a `Mock` as
   `authorized`*, *restore `tenant_id` on `put`*, *restore `.tenant` on the
   grant*, *reinstate `TenantedTokenGrant`*. Each must redden a named test.
6. The panel accepts, or names what it rejects, and every finding is verified
   against the tree before it is recorded.

---

**Next free decision id after this: `D-IMPL-354`.**
