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

### 1.2 Every mutating handle and every tenant-read handle REQUIRES the capability FOR ITS OWN ACTION

Not "checks it". *Requires it*, as a parameter with no default — and **not a
generic `Authorized`**. Each handle's parameter is the capability for the one
action that handle performs. See §1.5 for the binding; this table names the
handle, its action, and the signature before and after.

| handle | action type required | today | after |
|---|---|---|---|
| `ControlPlaneRegistry.register` / `register_typed` / `register_versioned` | `Authorized[Register]` | `(key, artifact, ...)` | `(authorized, artifact, ...)` — **`key` is `authorized.resource`** |
| `ControlPlaneStateStore.put` (both implementations) | `Authorized[StateWrite]` | `(record_class, key, record, token)` | `(authorized, record_class, record, token)` — **`key` is derived from `authorized.tenant` + `authorized.resource`** |
| `ArtifactStoreProtocol.put` (both implementations) | `Authorized[ArtifactWrite]` | `(tenant_id, artifact_class, name, artifact, *, minted)` | `(authorized, artifact)` — **`tenant_id`, `minted`, `artifact_class` and `name` are deleted**; class and name are `authorized.resource` (`"<class>/<name>"`, the same segments the naming key already uses) |
| `ArtifactStoreProtocol.get` / `govern_dereference` / every tenant-scoped read | `Authorized[ArtifactRead]` | `(grant, ...)` / `(content_address)` | `(authorized, ...)` |
| `WorkflowFactory.construct` | `Authorized[Execute]` or `Authorized[Resume]` | `(definition_key, definition_version)` | `(authorized, definition_version)` — **`definition_key` is `authorized.resource`** |
| `WorkflowEngine.execute` | `Authorized[Execute]` | `(workflow, *, execution_id, ...)` | `(authorized, workflow, *, execution_id, ...)` |
| `WorkflowEngine.resume` | `Authorized[Resume]` | `(workflow, *, execution_id, decision)` | `(authorized, workflow, *, execution_id, decision)` |
| `HITLTransportProtocol.submit` | `Authorized[HitlSubmit]` | `(*, submission)` | `(authorized, *, submission)` |
| `GrantLedger.request` / `revoke` | `Authorized[GrantMutate]` | `(..., actor)` | `(authorized, ...)` — **`actor` is deleted**; the actor is `authorized.principal` |
| MCP `TenantGuardedServer` tool/resource bodies | the body's declared action type | raw arguments | `authorized` as first argument, minted by the wrapper for that body's declared action |

Where a handle's target IS the resource the authorizer decided on — the
registry key, the workflow definition key, the state key — the handle **takes it
from the capability** and has no caller-supplied parameter for it. Where the
resource is a class of thing (an artifact class under a write action), the
handle acts on `authorized.resource` the same way. There is no second source for
tenant, principal, *or* resource.

The old handles table follows for the record of what each signature was:

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

### 1.5 THE BINDING CLAUSE — what a minted `Authorized` permits, and only that

*Added 2026-09-24 after ChatGPT's review question and Dave's ruling: "Authorized
that is only (tenant, principal) is ambient tenant authority. That is a new
defect, not a fix." As first written, §1.1 bound `action` at mint but §1.2 had
handles verify only the mint. This clause is the contract; §1.2 above is its
application.*

**(a) The mint binds the authorizer's whole decision.** A capability is minted
for exactly one `(tenant, principal, action, resource)` — the four values the
authorizer returned *allowed* for — plus the `decision_id` of that audit event.
Nothing is minted from a partial decision. The gate calls the authorizer once
per request with the door-declared action and the resolved resource, and mints
from that answer or refuses.

**(b) The action is part of the TYPE, not only a field.** `Authorized` is
generic over an action kind:

```python
class ActionKind: ...                    # marker; never instantiated
class ArtifactRead(ActionKind): ...
class ArtifactWrite(ActionKind): ...
class Register(ActionKind): ...
class StateWrite(ActionKind): ...
class Execute(ActionKind): ...
class Resume(ActionKind): ...
class HitlSubmit(ActionKind): ...
class GrantMutate(ActionKind): ...
# one subclass per door-declared action id; the existing ACTION_* strings
# become the .id of these kinds rather than free-standing constants

class Authorized(Generic[A]):            # A bound to ActionKind
    __slots__ = ("_minted", "kind", "tenant", "principal", "resource", "decision_id")
```

A handle that performs an artifact write is typed `authorized:
Authorized[ArtifactWrite]`. A handle that resumes a workflow is typed
`authorized: Authorized[Resume]`. `Authorized[ArtifactRead]` is not assignable
to either. **That is the static tooth.** A handler holding a read capability
cannot pass it to a write handle without a `# type: ignore` — which §4's lint
refuses in `runtime/` and `src/`.

**(c) The handle verifies the kind by identity, beside the mint.** On entry,
every handle runs `_verify(authorized, kind=ArtifactWrite)`, which checks
**both** `authorized._minted is _SENTINEL` **and** `authorized.kind is
ArtifactWrite`. Identity, not `isinstance`, not `==`: a subclass, a `Mock`, an
`object()`, a capability with `kind` overwritten, or a genuine capability of
another kind all fail the same way at the same line. **That is the runtime
tooth.** It exists because types do not run: a `# type: ignore`, a call from
untyped code, a `cast`, or a dynamically built argument list all reach the
handle with whatever object they carry, and the handle must not trust the
annotation.

**(d) Reuse across actions is therefore unrepresentable, not refused later.**
There is no code path in which a read-minted capability *arrives at* a write
handle and is turned away by a policy lookup. It does not type-check, and if it
is forced through anyway it dies at `_verify` before the handle's first real
statement — the same place and the same way a fabricated one dies. No handle
contains an action check *after* that line, because after that line the action
is known to be its own.

**(e) The two teeth are two teeth.** Static enforcement means a *checked*
handler cannot omit or mis-type the capability — and only that. Runtime
enforcement means a fabricated capability, and a genuine capability of the
wrong kind, are rejected at use — and only that. Neither replaces the other. A
design claim that names only one of them is incomplete, and §9's controls test
each separately.

**(f) Resource follows tenant — the mint is kind + resource + tenant + principal,
not kind alone.** `Authorized[ArtifactWrite]` for artifact X is not a write wand
for artifact Y. The handle acts on `authorized.resource` as it acts on
`authorized.tenant`: **a handle that takes a target takes it only from
`authorized.resource`** and has no caller-supplied parameter for it — the
registry key, the artifact class and name, the workflow definition key, the state
key. Where a handle is handed a target by an inner caller anyway (a resolver
building an artifact from parts), `_verify` takes the target and refuses by
identity of the resource string, beside the kind and the mint, before the
handle's first statement. This is not a second authorization decision; it is
the same tooth as (c), applied to the resource axis.

**(g) The minted authorization is bound to its original values.** *Added
2026-09-24 on ChatGPT's acceptance condition: a valid sentinel plus a reassigned
`kind` must never confer new authority.* As (c) was first written, a genuine
`Authorized[ArtifactRead]` whose `kind` attribute was reassigned to the
legitimate `ArtifactWrite` identity would pass both checks — valid sentinel,
current kind is `ArtifactWrite`. So the fields are not merely set at mint; the
mint is **over** them:

- `_minted` is not the bare sentinel. It is an immutable tuple captured at mint:
  `(_SENTINEL, kind, tenant, principal, resource, decision_id)`.
- `_verify(authorized, kind=K)` checks `authorized._minted[0] is _SENTINEL`,
  then `authorized._minted[1] is K`, then that `authorized.kind is
  _minted[1]`, `authorized.tenant == _minted[2]`, `authorized.principal ==
  _minted[3]`, `authorized.resource == _minted[4]`, `authorized.decision_id ==
  _minted[5]`. **The current attributes are compared against what was minted,
  not trusted on their own.**
- `Authorized` additionally refuses attribute assignment after mint
  (`__setattr__`/`__delattr__` raise). That is defense in depth against a
  careless caller; it is not the mechanism. `object.__setattr__` bypasses it,
  and the mint tuple is what makes even that bypass die at `_verify`.

Retargeting a genuine capability — to another kind, tenant, principal,
resource, or decision — is therefore rejected at use by the same line and in
the same way as fabrication. §9 tests retargeting separately from fabrication,
on every field, by both `setattr` and `object.__setattr__`.

---

## 2. What becomes inexpressible

Stated as consequences of §1, so a reader can check each against the mechanism
rather than trusting the list.

| panel finding | why it cannot be expressed under §1 |
|---|---|
| **P2** cross-tenant workflow invocation / agent declaration | the engine and registry have no tenant but `authorized.tenant`; the artifact's declared tenant is checked once at factory construction against the capability and never consulted again |
| **P1** the HTTP door refusing every real credential | there is one reader, `tenants_of_grant`, over the one field, `tenants`; `.tenant` and the test-only `TenantedTokenGrant` are deleted, so the fixture cannot pass a shape production never mints |
| **P3** the governed-class store guard inert by default | `ArtifactStoreProtocol.put` requires `Authorized[ArtifactWrite]`; writing a governed record class requires `Authorized[ReplayMint]`, a distinct kind (§1.5b) that **no door declares an action for**, so no served surface can obtain one. The fabric's own replay writer is handed a `ReplayMint` capability at composition by the deployment, not minted by a gate. `GovernedWriteHandle` and `minted=` are retired: the kind IS the mint |
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
5. **The binding controls (§1.5), committed and named:**
   - **Negative control — wrong kind.** Mint a genuine `Authorized[ArtifactRead]`
     for artifact X under tenant A through the real gate. Pass that object to
     `ArtifactStoreProtocol.put`, `HITLTransportProtocol.submit`,
     `WorkflowEngine.execute` and `ControlPlaneRegistry.register`. Each must
     fail **twice, separately measured**: (i) `mypy --strict` reports an
     incompatible argument type on the committed source — the control file
     carries no `# type: ignore`; (ii) with the type error forced past via a
     `cast` in a second, quarantined file, `_verify` raises at use before any
     state changes, and the test asserts nothing was written under tenant A.
   - **Negative control — wrong resource, right kind.** Mint a genuine
     `Authorized[ArtifactWrite]` for artifact X under tenant A. Force a put of
     artifact Y through it (the store has no `name` parameter, so this means a
     resolver-side construction that hands `_verify` a target other than
     `authorized.resource`). `_verify` dies; the test asserts nothing exists
     under tenant A at Y's address and nothing at X's either.
   - **Positive control — right kind.** Mint `Authorized[ArtifactWrite]` for
     that exact action and resource under tenant A; `put` runs, files under
     `authorized.tenant` only, and the resulting audit event carries the
     capability's `decision_id`.
   - **Fabrication controls.** A stub sentinel, a `Mock`, an `object()`, and a
     subclass skipping `__init__` — each dies at `_verify` on every handle in
     §1.2.
   - **Retargeting controls (§1.5g) — separate from fabrication.** Mint a
     genuine `Authorized[ArtifactRead]` for X under tenant A through the real
     gate. For each of `kind`, `tenant`, `principal`, `resource`,
     `decision_id`: attempt reassignment by plain `setattr` (must raise) and by
     `object.__setattr__` (bypasses the guard). After the bypass, the
     capability must be **unusable for the write** and **unusable for its
     original read** — `_verify` rejects on every handle, and nothing is read or
     written under A or under the retargeted tenant.
6. Sabotage on the merged tree, each guard severed alone — and the severings
   include: *remove the kind check from `_verify` (mint check alone)*, *make
   `Authorized` non-generic*, *mint from a stub sentinel*, *restore `tenant_id`
   on `put`*, *restore `.tenant` on the grant*, *reinstate
   `TenantedTokenGrant`*, *drop the resource bind from `_verify`*, *compare the
   current `kind` instead of the minted one*. Each must
   redden a named test — and two severings prove the teeth are two: dropping the
   **kind** check alone reddens the wrong-kind control's runtime half and leaves
   its static half green; dropping the **resource** bind alone reddens the
   wrong-resource control's runtime half.
7. The panel accepts, or names what it rejects, and every finding is verified
   against the tree before it is recorded.

---

**Next free decision id after this: `D-IMPL-354`.**
