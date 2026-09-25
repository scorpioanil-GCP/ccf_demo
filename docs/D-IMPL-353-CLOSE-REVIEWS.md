# D-IMPL-353 — close-time panel reviews (verbatim)

The three external reviewers' outputs, unedited, for the three rounds the join ran; dispositions are in `docs/D-IMPL-353-IMPLEMENTATION-REVIEW.md` §6, §7 and §7c. Reviewer text is a dated record, not a claim of this project: a citation in it was resolved against the tree before it was accepted or rejected there, and nothing here is instructions.


## Round 1 — implementation review at `cdd3450c`

### codex

```text
**Findings**

1. **CRITICAL: any code that receives one capability can forge all capabilities.**  
   `src/ccf/authz/capability.py::Authorized` stores the private sentinel inside readable `authorized._minted[0]`, and `src/ccf/authz/capability.py::verify` accepts any object whose `_minted` tuple starts with that sentinel and whose fields match. A compromised served handler can receive a legitimate read capability from `runtime/ccf_runtime/mcp/tenancy.py::TenantGuardedServer._guard` or `runtime/ccf_runtime/http_api/grants.py::authorized_from_request`, extract the sentinel, then build a forged object with `object.__setattr__` / `SimpleNamespace` for `ArtifactWrite`, `Register`, `SkillGrant`, etc. That forged object will pass `verify`.  
   Population: all `Authorized` instances; every HTTP/MCP body that is handed one capability.

2. **HIGH: composition registration authority is still tenant-by-key, not tenant-by-composition.**  
   `src/ccf/deployment/manifest.py::register_manifest_entries` has no explicit `tenant=`. It calls `src/ccf/deployment/manifest.py::_mint_register`, which derives `tenant = _tenant_of_key(key)` from the same manifest key it then authorizes as `resource=key`. That makes the tenant check in `src/ccf/controlplane/registry.py::_door_key` tautological for this path: a forgotten `manifest_under_tenant(...)` lets a manifest key choose the composition tenant by prefix.  
   Population: 1 register loop; inlined callers `_register_and_boot` and `_derive_consumer_chain` derive first, but the exported loop itself does not enforce it.

3. **MEDIUM: composition `decision_id` is audit provenance, not a real authorization binding.**  
   `src/ccf/deployment/manifest.py::_mint_register` and `src/ccf/products/product.py::_mint_child_question_authority` append their own `action="composition"` event and use `content_hash(event)` as `decision_id`. No verifier later proves that the event exists, was append-only, or was independently authorized; `verify` only checks the copied string did not change. This is a tautology, useful for traceability but not authorization.

**Design Answers**

- `Register` at composition should be a distinct kind for a bank posture. Today `mint_at_composition(Register, ...)` creates the same runtime kind accepted for the config-register door, so `ControlPlaneRegistry.register*` cannot distinguish door-granted registration from composition registration except by convention fields like principal/decision_id.

- I would not add composition-time skill grants. `src/ccf/products/product.py::GrantNotInForce` and `_derive_consumer_chain` are taking the safer position: skill grants change authority and should come through `src/ccf/skills/grants.py::GrantLedger.request` under `Authorized[SkillGrant]`.

- I found no new `None` / default / `Any` authority parameter in the inlined `src/` + `runtime/` snippets. The lint scope excluding examples/tools matters operationally if those examples are deployable, but I am not counting that as a new finding because your brief already records the examples/tools sentinel-scope gap.

**Sabotage Gap**

A severing I believe would not redden the listed controls: in `src/ccf/deployment/manifest.py::_mint_register`, delete the `registry.audit_log.append(...)` and pass `decision_id=key` or any constant into `mint_at_composition`. The lint still sees an allowed composition mint site, and `verify` only checks that the same `decision_id` string remains on the object.
```

### cursor

```text
# Panel review — D-IMPL-353 capability (Cursor) — HEAD claimed `cdd3450c` / branch `security-tier-0`

Reviewed as a bank security architect against the inlined subjects plus tree resolution of the cited symbols. Known items (SEC353-J-01, HITL stamp, etc.) were not re-derived. Counts name their population.

---

## Verdict

**Served-surface write path is largely closed** relative to SEC-001’s “optional guard” shape: mutating handles in the §1.2 table call `verify` / `verify_any`, and HTTP/MCP mint only after an allow.  

**The capability object is not a cryptographic proof.** `_SENTINEL` is process-global and readable from every minted instance; `verify` never requires `isinstance(..., Authorized)`. Under the brief’s own threat model (compromised example / in-process code holding one real capability), **arbitrary authority is forgeable**. That is the load-bearing residual. No M1–M22 severing tests it.

`★ Insight ─────────────────────────────────────`
Capability-as-proof only works if the mint secret never escapes the prover. Storing `_SENTINEL` inside every instance’s `_minted` tuple turns every legitimate allow into a master key for in-process forgers — the same class of defect as putting an HMAC key in the message.
`─────────────────────────────────────────────────`

---

## 1. Served surface → state-changing handle without `verify` for that tenant+action+resource

**Population examined:** HTTP routes under `runtime/ccf_runtime/http_api/routes/` + `/health` + generated docs; MCP servers wrapping `TenantGuardedServer`; workflow `execute`/`resume`; registry register paths; state `put`; artifact `put`; grant `request`/`revoke`; HITL `submit`.

**No confirmed wire path** was found where a remote caller reaches a **mutating** handle without a capability that passed `verify`/`verify_any` for that kind and resource, *assuming the capability object is genuine*. Writes go through:

| Surface | Handle | Verify site |
|---|---|---|
| HTTP/MCP mutating tools | registry / state / artifact / grants / engine / HITL | `registry._door_key` / `InMemoryStateStore.put` / `authorized_write_target` / `GrantLedger.request|revoke` / `WorkflowEngine.execute|resume` / `InMemoryHitlTransport.submit` |

**Adjacent (not Q1 — not state-changing, but bank-material):** after a gate allow, several **read** doors ignore `authorized.tenant` when naming data:

| Finding | Symbol | Issue |
|---|---|---|
| F-READ-01 | `runtime/ccf_runtime/http_api/routes/agent.py::declarations` | `keys_of_class(AGENT_DEFINITION.class_id)` — all tenants |
| F-READ-02 | `runtime/ccf_runtime/http_api/routes/skill.py::catalog` → `SkillCatalog.discover` | all catalog entries, no tenant filter |
| F-READ-03 | `runtime/ccf_runtime/http_api/routes/config.py::keys` | `keys_of_class(class_id)` — all tenants |
| F-READ-04 | `agent.py::declaration` / `versions`; `config.py::resolution` / `versions` | `resolve`/`versions` on caller `key`; **no** `_tenant_segment(key) == authorized.tenant` |

A hostile authenticated tenant whose scope mapping grants `agent.list` / `skill.catalog.read` / `config.keys.read` (or a wide resource pattern on read) gets **cross-tenant reconnaissance**. Writes still hit `_door_key` / factory tenant compare; reads do not.

**Not a Q1 bypass:** handler `key` vs gate resource dual-parse — gate requires a single query value (`AuthorizationGate._resource`); treated as defense-in-depth gap only (handlers should prefer `authorized.resource` exclusively).

---

## 2. Obtaining `Authorized` outside the two mint sites

**Confirmed forge (CRITICAL under compromised-deployment assumption):**

1. Obtain any genuine capability (one HTTP/MCP allow, or any composition mint).
2. Read `cap._minted[0]` — that **is** module `_SENTINEL` (`capability.py::Authorized.__init__` stores `(_SENTINEL, kind, tenant, principal, resource, decision_id)`).
3. Build any object with matching fields + that sentinel in `_minted`.
4. `verify` succeeds: it checks tuple shape, `minted[0] is _SENTINEL`, field equality, kind identity, resource equality — **never** `isinstance(authorized, Authorized)` (`capability.py::verify`).

Equivalent: `from ccf.authz.capability import _SENTINEL` at runtime. Docstring claims “not importable by name from anywhere that matters”; the only enforcement is the lint, and **`examples/` / `tools/` are outside `RULE_TREE_SCOPE`** (known residual — **it matters**).

**Resolved against tests:** `tests/authz/test_capability.py::TestFabrication` uses a **stub** sentinel and empty `__new__`; **zero** tests extract the real sentinel. Grep for `_minted[0]` / real-sentinel forge in `tests/`: empty.

**Does not work (rechecked):**
- Plain `Authorized(...)` without sentinel → `CapabilityBypassError`
- `Authorized.__new__` without real `_minted` → dies at `verify`
- Field retarget via `object.__setattr__` → dies on mint-tuple mismatch (`TestRetargeting`)
- Subclass of an `ActionKind` → different kind by identity
- Pickle across process → new `object()` identity ≠ `_SENTINEL` (expected fail-closed)

**Population for “two producers”:** `mint` call sites outside definer: `ccf_runtime.http_api.gate`, `ccf_runtime.mcp.tenancy` only (tree grep). `mint_at_composition` outside definer: `ccf.boot`, `ccf.deployment.manifest`, `ccf.products.product`, `ccf.products.resolver`, `ccf_runtime.mcp.product_door` — **not** `inprocess` / `cli.local` despite roster membership (see §354).

---

## 3. Caller-influenced tenant / key

| Status | Where | Notes |
|---|---|---|
| **Closed (writes)** | `registry._door_key`, state `put` tenant compare, artifact `WriteTarget(tenant_id=authorized.tenant)`, workflow factory tenant compare, grant `_require_covers`, HITL submit uses `authorized.tenant` | Resource/key from capability after verify |
| **Open (reads)** | F-READ-01..04 above | Effective tenant is embedded in caller-chosen key / unfiltered list |
| **By design (within tenant)** | `execution_id`, state `record_id`, HITL `event_key` | Caller chooses id; tenant namespace is capability’s |
| **Composition** | `namespaced_key` + `manifest_under_tenant` | Foreign prefix becomes `{resolved_tenant}/{foreign}/…` — confinement holds; `_door_key` check is **redundant for composition-minted pairs** (same string produced tenant+resource), **real for door-minted `Register`** |

**`register_manifest_entries` + explicit `tenant=`:** After `manifest_under_tenant`, minting from the key’s segment is consistent but not an independent policy check. An explicit `tenant=` on the register loop would make the binding non-circular and refuse keys whose segment ≠ deployment tenant before mint.

---

## 4. `None` / default / `Any` authority the lint misses

**Inside `src/` + `runtime/` (lint scope):**
- `authorized_from_request(..., kind: type[ActionKind] | None = None)` — param name `kind` ∉ `AUTHORITY_PARAM_NAMES`; return typed/cast `Authorized[Any]` (`grants.py`). Not a missing authorizer, but weakens the static tooth at the reader.
- `grant_from_request` → `TokenGrant | None` still on HITL path for authentication claims (principal still from capability).
- Documented residuals: dynamic `getattr` / `importlib`; `*args`/`**kwargs` — accepted.

**Outside lint scope — matters:**
- `examples/`, `tools/`: can import `_SENTINEL`, register raw FastMCP, pass weak authority. Combined with F-FORGE-01, a compromised example is a full forge kit.
- Tests helper `tests/composition.py::composition_register` is a third *logical* mint recipe (allowed for tests; not a served surface).

No surviving `authorizer: … | None = None` on `create_app` at HEAD (signature requires all five seams) — resolved.

---

## 5. Sabotage table — severing that would **not** redden

**Named severing (believed green against M1–M22 + current authz tests):**

> **S-FORGE:** From any genuine `Authorized`, copy `_minted[0]` into a `types.SimpleNamespace` (or `Authorized.__new__` + `object.__setattr__`) minted for a **different** `(kind, tenant, resource)`. Call any handle’s `verify`/`verify_any`.

- Lint: green (no source change in `src`/`runtime` required if done from `examples/` or a test that isn’t written).
- M4 only stubs a **wrong** sentinel; it does not extract the real one.
- M3/M5/M7–M13 assume wrong kind / missing verify / wrong resource — all defeated once the forge carries the real sentinel and matching fields.

**Second green severing:** add `from ccf.authz.capability import _SENTINEL` under `examples/` and forge there — rule 3 does not walk `examples/`.

---

## D-IMPL-354 questions (provisional design)

| Question | Ruling (conservative) |
|---|---|
| Distinct `CompositionRegister` kind? | **Yes.** Today `Register = ConfigRegister` (`capability.py`) — composition and door mint the **same kind identity**. A leaked composition cap is a door `config.register` wand by type. Separate `CompositionRegister` (not an alias), admitted only on the registry’s composition path / `REGISTER_KINDS` union, closes that. |
| `decision_id = content_hash(self-appended event)`? | **Attestation, not authorization.** Proves “this process logged a composition row,” not that an authorizer allowed anything. Reusing `decision_id` vocabulary will mislead bank auditors; rename or namespace (`composition_attestation_id`) and say so in the audit schema. |
| Seven-root roster? | **Wrong as stated.** `COMPOSITION_MINT_SITES` lists 7 + definer; tree shows **active** `mint_at_composition` callers: `boot`, `manifest`, `product`, `resolver`, `product_door` (5). **`ccf.client.adapters.inprocess` and `ccf_runtime.cli.local` are allow-listed but do not call it** (comments say local mints nothing). Dead allow-list entries are future silent mint sites — remove until they mint. |
| Paved road grants? | **Do not** add a third composition grant kind. “Grant through a governed door first” is the right bank posture (`GrantNotInForce`). |

---

## Finding table (actionable)

| ID | Sev | Claim | Symbol(s) | Control gap |
|---|---|---|---|---|
| **F-FORGE-01** | **CRITICAL** | Real sentinel extractable; `verify` accepts any object with that sentinel | `Authorized.__init__` (`_minted`), `verify` (no `isinstance`) | No test; not in M1–M22 |
| **F-SCOPE-01** | **HIGH** | `_SENTINEL` import / forge from `examples/`/`tools/` | lint `RULE_TREE_SCOPE`; capability docstring vs reality | Known unenforced scope — **material** |
| **F-READ-01..04** | **HIGH** | Cross-tenant CP enumeration/read after allow | `agent.declarations`, `skill.catalog`→`discover`, `config.keys`, resolve/versions routes | Tenant not applied to read |
| **F-KIND-01** | **MEDIUM** | Composition `Register` ≡ door `ConfigRegister` | `Register = ConfigRegister`, `COMPOSITION_KINDS` | Kind identity shared |
| **F-ROSTER-01** | **MEDIUM** | Dead composition mint allow-list entries | `COMPOSITION_MINT_SITES` vs grep of `mint_at_composition` | Lint won’t catch new mints there |
| **F-ATTEST-01** | **LOW/advisory** | Composition `decision_id` is self-hash | `_mint_register`, `_mint_child_question_authority` | Audit semantics |

**Q1 strict answer:** no additional **write** bypass found beyond forge-assisted verify (F-FORGE-01), which is Q2.  

**Q5 answer:** S-FORGE above.

---

## What I would require before calling Tier-0 closed for a bank

1. Stop storing `_SENTINEL` on the instance (MAC / HMAC over fields with a non-exportable process key, or capability as opaque handle id into a process-private table).
2. `verify`: require `type(authorized) is Authorized` (or sealed type) **in addition to** mint proof.
3. Tenant-filter every Control Plane list/resolve on the capability’s tenant (or require key segment == `authorized.tenant` before `resolve`).
4. Split `CompositionRegister` from `ConfigRegister`; shrink `COMPOSITION_MINT_SITES` to actual callers.
5. Add an explicit sabotage: real-sentinel extract → forge → every mutating handle must red.

Wire-only hostile tenant without in-process code execution is in much better shape than at d895d889; **compromised deployment is not**, until F-FORGE-01 is closed.
```

### gemini

```text
Based on an architectural review of the D-IMPL-353 capability implementation (HEAD `cdd3450c`), here is the security architect's assessment of the served-surface claims.

### 1. Paths from served surface to state-changing handle bypassing `verify`
Every identified state-changing handle—including the `ControlPlaneRegistry` (register/typed/versioned), `InMemoryStateStore` (put), `ArtifactStore` (put via `authorized_write_target`), `GrantLedger` (request/revoke), and `WorkflowEngine` (execute/resume)—calls `verify` or `verify_any` as its first functional statement.
*   **The Disagreement Gap (Fail-Closed):** In `runtime/ccf_runtime/http_api/grants.py::authorized_from_request`, the reader re-verifies the stashed capability against the route's declared action. If the gate's matcher and the router's resolution disagree (Route A authorized but Route B reached), `claimed_kind is not expected` triggers a 403.
*   **Websocket/Lifespan Pass-through:** `AuthorizationGate` passes non-HTTP scopes unexamined. However, because handles require a capability to act, a websocket handler reaching a state-changing handle will fail at `verify` (as `request.state.authorized` will be missing or `None`), satisfying the requirement that no served surface acts without a capability.

### 2. Ways to obtain an `Authorized` other than mint sites
**FINDING (CRITICAL): Sentinel Leakage via `_minted` slot.**
The module-private `_SENTINEL` is used to prove the mint's integrity. While the lint (Rule 3) prevents naming or importing `_SENTINEL`, the sentinel's object identity is leaked through the `_minted` tuple on every genuine `Authorized` instance.
*   **The Bypass:** A hostile tenant with one valid capability can execute `sentinel = authorized._minted[0]`. They can then forge a capability for ANY tenant, resource, or action by using `object.__new__(Authorized)` and `object.__setattr__` to populate the slots and the `_minted` tuple with the stolen sentinel. Since `verify` checks the sentinel by identity (`minted[0] is not _SENTINEL`), the forgery is indistinguishable from a genuine mint.
*   **Symbol:** `src/ccf/authz/capability.py::Authorized` (the `_minted` slot).

### 3. Handle influence by caller-supplied values
**FINDING (HIGH): Caller-supplied key segments in Mechanism-Written classes.**
While the `tenant` is strictly capability-derived, several handles allow the "name" or "record_id" segment of a key to be influenced by caller-supplied values that are not part of the capability's `resource` binding.
*   **Workflow State:** In `runtime/ccf_runtime/workflow/engine.py::WorkflowEngine.execute`, the `execution_id` (a caller-supplied string) forms the record ID. The capability is bound to the `workflow.definition_key`, not the `execution_id`. A caller can influence the exact state key used (`tenant/workflow-state/{execution_id}`) despite the capability being for the definition.
*   **Derived Artifact Writes:** In `src/ccf/artifacts/protocol.py::authorized_write_target`, a `DerivedWrite` (used for mechanism classes like workflow traces) takes `artifact.name` from the payload. The capability (e.g., `Execute`) verifies against its own `resource` (the definition key), but the write target is determined by the caller-supplied name.
*   **Symbol:** `src/ccf/artifacts/protocol.py::authorized_write_target` (branch `if isinstance(artifact, DerivedWrite)`).

### 4. Surviving `None` / `Default` / `Any` parameters
**FINDING (LOW): `Authorized[Any]` return type in `authorized_from_request`.**
The lint (Rule 2) rigorously flags "kind-less" capability parameters (e.g., `Authorized[ActionKind]`), but `runtime/ccf_runtime/http_api/grants.py::authorized_from_request` returns `Authorized[Any]`.
*   **Risk:** This allows a handler to pick up a capability as a "wand" and pass it to multiple handles without mypy enforcing the kind at the handler level. While the handles' own `verify` calls (which use specific kinds) will catch a mismatch at runtime, the "static tooth" (§1.4) is softened at the reader seam.
*   **Symbol:** `runtime/ccf_runtime/http_api/grants.py::authorized_from_request`.

### 5. Sabotage Table Verification
**Severing:** Removal of the `principal` field check in `src/ccf/authz/capability.py::verify`.
```python
# Sabotage: remove this line
or getattr(authorized, "principal", None) != m_principal
```
**Rationale:** This severing would likely **NOT** be caught by many existing functional tests that focus on tenant/resource isolation. While `M16` (HITL approver principal) would turn red because HITL specifically reads `authorized.principal` to mint the binding, other handles (Registry, State Store) use the `principal` primarily for audit records. If the `repr` or audit logs are not asserted for the specific principal identity in the core isolation suite, a principal-retargeting sabotage could survive until an audit-integrity test is run.

### Summary for the Bank
The implementation is architecturally sound in its **enforcement** (the runtime teeth in handles are universal). However, the **sentinel leakage** via the `_minted` slot allows a motivated attacker who has obtained one capability to forge others, bypassing the authorizer entirely. Recommendation: `_SENTINEL` must be unreachable even via attribute access, or the `_minted` tuple must be protected from introspection (e.g., via a module-level weakmap or by making `_minted` a property that refuses access outside the `capability` module).
```


## Round 2 — scoped re-review of the fixes at `81b6f1c7`

### codex

```text
**Findings**

1. **CRITICAL: the mint table is still reachable without naming it.**  
   `verify` is exported, and `verify.__globals__` exposes the module globals for `src/ccf/authz/capability.py`. An attacker can scan those values for the `weakref.WeakKeyDictionary` whose `.get(genuine)` matches the genuine cap’s `(kind, tenant, principal, resource, decision_id)`, then insert a forged exact-`Authorized` instance. No `_ISSUED`, `_issued`, or `_SENTINEL` name is needed.

   Minimal shape:

   ```python
   import weakref

   ledger = next(
       value
       for value in verify.__globals__.values()
       if isinstance(value, weakref.WeakKeyDictionary)
       and value.get(genuine) == (
           genuine.kind,
           genuine.tenant,
           genuine.principal,
           genuine.resource,
           genuine.decision_id,
       )
   )

   forged = Authorized.__new__(Authorized)
   object.__setattr__(forged, "kind", ArtifactWrite)
   object.__setattr__(forged, "tenant", TENANT)
   object.__setattr__(forged, "principal", PRINCIPAL)
   object.__setattr__(forged, "resource", RESOURCE_X)
   object.__setattr__(forged, "decision_id", DECISION)

   ledger[forged] = (ArtifactWrite, TENANT, PRINCIPAL, RESOURCE_X, DECISION)
   verify(forged, kind=ArtifactWrite, resource=RESOURCE_X)
   ```

   The break relies on `verify.__globals__`, `_ISSUED` being a mutable `weakref.WeakKeyDictionary`, `_issued(candidate)` accepting exact `Authorized`, and `verify` trusting the returned record after field comparison.

2. **HIGH: `skill.grant` still performs a Control Plane read without a tenant fence.**  
   `runtime/ccf_runtime/http_api/routes/skill.py::grant` resolves `body.definition_key` with `deps.control_plane.resolve(body.definition_key, body.definition_version)` and does not call `within_tenant(tenant=authorized.tenant, key=body.definition_key)`. It is protected by `@authorizes(... ResourceBinding.body("definition_key"))` and `authorized_from_request(..., kind=SkillGrantKind)`, so it is not the same unauthenticated read-list flaw, but it is still a read door naming Control Plane data without applying the capability tenant.

**Other Questions**

`Authorized.__reduce__` refusing pickle looks correct from the inlined source. I do not see a legitimate SDK path that must serialize a capability across multiprocessing, cache, or crossproc children. I re-read `Authorized.__reduce__`, `mint`, `mint_at_composition`, `authorized_from_request`, and `_derive_consumer_chain`; any path that pickles `QuestionBoundChildResolver(... authorized=...)` would be trying to serialize composition authority, which the capability model explicitly refuses.

The register-loop fix holds in the inlined path. `manifest_under_tenant` confines keys through `namespaced_key`, `_register_and_boot` applies that before registration, `register_manifest_entries(..., tenant=...)` requires the tenant, and `_mint_register` refuses when `_tenant_of_key(key) != tenant` before audit append or mint. I do not see a remaining manifest-authored way to choose a different composition tenant through that path.

For the two rejected severings: I re-read `_mint_register`, `register_manifest_entries`, and the summary’s `tests/deployment/test_manifest.py::test_every_registered_entry_is_preceded_by_its_own_composition_event` reference for the constant `decision_id` rejection. I re-read `verify`’s principal comparison and the summary’s `TestRetargeting[...principal]` / dereference retarget controls for the principal-field-check rejection. Both rejections are consistent with the candidate source.
```

### cursor

```text
`★ Insight ─────────────────────────────────────`
The F-FORGE fix closed “steal the sentinel off the instance.” It did **not** close “find the issuance table and write it.” In CPython, module-private is a naming convention, not a trust boundary — and this bank brief treats in-process forgery as in-scope.
`─────────────────────────────────────────────────`

## Verdict (round 2)

F-FORGE-01’s **instance-borne sentinel** path is closed as claimed. Under the **same in-process threat model** that made F-FORGE CRITICAL, I can still get `verify` to honor an object that never passed through `mint` / `mint_at_composition`. Register-loop and HTTP read-route fixes look solid; one composition-root residual still reads tenant off a key. Both round-1 rejections are **right** on the controls I re-read.

---

### 1. Break the fix? — **YES (residual CRITICAL)**

**Re-read:** `Authorized.__init__` writes `_ISSUED[self] = (...)`; `_issued` / `verify` only require exact type + table membership + field match (`src/ccf/authz/capability.py`).

**Break (no `mint` / `mint_at_composition`; no `_ISSUED` / `_issued` / `_SENTINEL` by name):**

```python
import sys
from ccf.authz.capability import Authorized, ArtifactWrite, verify

mod = sys.modules["ccf.authz.capability"]
issued = next(v for v in vars(mod).values() if type(v).__name__ == "WeakKeyDictionary")

forged = Authorized.__new__(Authorized)
for name, value in (
    ("kind", ArtifactWrite),
    ("tenant", "t"),
    ("principal", "p"),
    ("resource", "t/x"),
    ("decision_id", "d"),
):
    object.__setattr__(forged, name, value)
issued[forged] = (ArtifactWrite, "t", "p", "t/x", "d")
verify(forged, kind=ArtifactWrite, resource="t/x")  # honors
```

A genuine capability is **not** required. Holding one only helps alternate discovery (`gc.get_referrers` → weakref / table), same end state.

| Vector | Outcome |
| --- | --- |
| Steal sentinel from instance slots | **Dead** — no `_minted`; slots are public fields + `__weakref__` |
| `Authorized.__new__` + fake `_minted` | **Dead** — table, not attribute |
| Subclass / wrong type | **Dead** — `type(candidate) is not Authorized` |
| `copy` / `pickle` / `__reduce__` | **Dead** — raises; clone not in table |
| `__class__` games | **Dead** without a table insert |
| Id reuse after GC | **Dead** — `WeakKeyDictionary` drops dead keys |
| Thread races on the dict | **Not** a clean forgery for never-minted ids |
| Walk `vars(module)` / `gc.get_referrers` | **Live** — insert into the only `WeakKeyDictionary` |
| Name `_ISSUED` from `examples/` / `tests/` | **Also live** — lint scope is `src/` + `runtime/` only (`RULE_TREE_SCOPE`); **not** the only path |

**Scope note (honest):** the module docstring already admits in-process holders of stores can bypass. Round 1 still graded instance-sentinel theft CRITICAL under that brief. This residual is the same class with a different handle: **issuance is now a writable module global discoverable by type.**

`★ Insight ─────────────────────────────────────`
Moving the mint record off the object stops “read one cap → forge another.” It does not stop “import the definer → write the ledger.” Closing that needs a non-enumerable issuer (closure/C-api) or an explicit “in-process = out of threat model” ruling.
`─────────────────────────────────────────────────`

---

### 2. Is `__reduce__` refusing pickle a problem for a legitimate SDK path?

**No path named in this tree.**

Re-read: crossproc MCP children are **fresh processes** that mint locally (`tests/crossproc/servers/*`); they do not unpickle `Authorized` from a parent. No `pickle` / `multiprocessing` of capabilities under `runtime/` or `src/ccf`. Caching is artifacts/products, not capabilities.

Refusing pickle matches §1.5g (“re-decided, never duplicated”). A future worker pool that tried to ship `Authorized` across processes would have to re-mint at the gate — by design.

---

### 3. Register loop — remaining way for the manifest to choose composition tenant?

**Production paved path (`_register_and_boot` / `_derive_consumer_chain`): no.**

Re-read:

- `manifest_under_tenant` → `namespaced_key` **confines** (`other/…` → `{resolved}/other/…`), does not honor the author’s prefix as tenant (`test_a_manifest_key_under_another_prefix_is_confined_to_the_deployments_tenant`).
- `_mint_register(..., tenant=)` refuses `segment != tenant` **before** append/mint.
- Loader passes the **same** `resolved_tenant` into placement and the loop.

Disagreement is refused, not silent: place under A, register with `tenant=B` → `CrossTenantKeyRefused` (control test).

**Residuals (same anti-pattern class, not the fixed loop):**

| Site | Behavior |
| --- | --- |
| `ccf.products.resolver._mint_register_at_composition` | Still does `tenant, _, _ = key.partition("/")` then mints for that tenant (lines ~1144–1158). Callers pass `declaration.max_ttl_key` / `request_contract_key` from the fabric — usually already under `fabric.tenant_id`, but this is again “tenant read off the key.” |
| `tests/composition.composition_register` | Same pattern (test-only). |
| `examples/cp-20-…/deployment.py:429` | Calls `register_manifest_entries(..., only=wanted)` **without** `tenant=` — TypeError against the new signature, not a bypass. |

Manifest text alone cannot pick the composition tenant on the fixed loop; a composition root that still derives tenant from key can.

---

### 4. Read doors still naming Control Plane data without the capability’s tenant?

**HTTP config / agent / skill catalog list+keyed reads: fixed as claimed.**

Re-read: `within_tenant` / tenant filter on:

- `config.keys` / `versions` / `resolution`
- `agent.declarations` / `declaration` / `versions`
- `skill.catalog` (`entry.tenant == authorized.tenant`)

MCP agent list uses `authorized.tenant` (`experience.list_agents`). No MCP `keys_of_class` twin for config found.

**Defense-in-depth gap (not the F-READ list oracle):**

- `runtime/ccf_runtime/http_api/routes/skill.py::grant` — `deps.control_plane.resolve(body.definition_key, …)` with **no** `within_tenant`. Under normal gate wiring, `authorized.resource` **is** that key (`ResourceBinding.body("definition_key")`), and the ledger re-binds §1.5f. So this is not “list every tenant after allow”; it is resolve-before-ledger without a local tenant predicate. **Not** a standing F-READ reopen unless body and minted resource can diverge.

No other HTTP/MCP Control Plane **enumeration** door found that still lists foreign tenants after allow.

---

### 5. Rejections — verified?

**Yes.**

| Claim | What I re-read | Why the rejection holds |
| --- | --- | --- |
| Constant composition `decision_id` is not a free green severing | `tests/deployment/test_manifest.py::test_every_registered_entry_is_preceded_by_its_own_composition_event` | Asserts **per pin**: first audit event for that key is `action=="composition"`, `actor==COMPOSITION_PRINCIPAL`, `version=="config.register"`, then a `register_*`. A sabotage that collapses/skips those composition appends (what M23 measured) reddens this. Note: a surgical `decision_id="fixed"` **while still appending per key** would not by itself trip *this* assertion — the join’s measured M23 was not “attestation unused for authz,” it was “composition attestation sequencing broken.” Panel’s D-IMPL-354 point (attestation ≠ authorization) can stand without calling that severing green. |
| Dropping the `principal` field check | `tests/authz/test_capability.py::TestRetargeting` (`FIELDS` includes `"principal"`; forced `object.__setattr__` then `verify` must raise); handle suites parametrize `RETARGETS` including `"principal"` (`tests/controlplane/capabilities.py`, registry/grants/state/artifact `TestRetargeting`) | Dropping principal from the mint-tuple compare leaves those controls green → **false** green severing. Rejection correct. |

---

## Findings table (this round)

| Sev | ID | Finding |
| --- | --- | --- |
| **CRITICAL** | F-FORGE-02 | Issuance table is module-global and writable; `verify` honors `Authorized.__new__` + insert without `mint`/`mint_at_composition`. No private-name required. |
| HIGH | F-COMP-01 | `resolver._mint_register_at_composition` still mints tenant from key segment (pre-fix register-loop shape). |
| Advisory | F-READ-05 | `skill.grant` resolves `definition_key` without `within_tenant` (ledger still binds resource). |
| — | — | Pickle refuse: no legitimate SDK path broken. |
| — | — | HTTP F-READ-01..04 fix: holds on re-read. |
| — | — | Register-loop `tenant=` fix: holds on paved path. |

**Bottom line for Dave:** round-1 fixes for sentinel-on-instance, register-loop tenant tautology, and HTTP cross-tenant reads are real. Do **not** close F-FORGE under the bank in-process brief until the issuance table is not attacker-writable (or that brief is explicitly narrowed).
```

### gemini

```text
This scoped re-review of the `security-tier-0` branch (HEAD `81b6f1c7`) evaluates the fixes for the Round 1 findings and addresses the specific questions regarding the capability system and the registration/read routes.

### 1. Breaking the Fix (In-process Elevation)
The fix for **F-FORGE-01** (moving the mint record to `_ISSUED`) is robust against attribute mutation and `__class__` reassignment because `verify` checks the instance's attributes against the module-private `_ISSUED` record keyed by identity. However, an in-process attacker (e.g., a malicious handler) can obtain a "genuine" capability without calling `mint` by exploiting Python's introspection:

*   **The Break:** Access the `_SENTINEL` through the `Authorized` constructor's globals:
    ```python
    # Bypasses the lint because it names no private symbols as strings or attributes
    sentinel = [v for k, v in Authorized.__init__.__globals__.items() if k.endswith('SENTINEL')][0]
    fake_cap = Authorized(sentinel, kind=ArtifactWrite, tenant=TENANT, principal=PRINCIPAL, resource=RESOURCE, decision_id=DECISION)
    # verify(fake_cap) now passes because the constructor successfully added it to _ISSUED.
    ```
*   **Result:** This fulfills the goal of obtaining a verified object without `mint` having run for it. It bypasses the gate's decision logic while satisfying the "runtime tooth." This is a known limit for in-process code, as stated in `capability.py`: *"In-process code... can reach their internals."*

### 2. `__reduce__` and Pickling Problems
`__reduce__` refusing serialization is a problem for **handler-level parallelization** using the `multiprocessing` module. 
*   **The Path:** If a handler (e.g., an orchestration task) spawns a subprocess to perform a long-running authorized write and attempts to pass the `Authorized[ArtifactWrite]` capability via process arguments, it will fail.
*   **Context:** While **MCP crossproc** children are safe (as they "re-decide" and re-mint via the wrapper on the child side), purely internal worker processes that rely on inheriting or receiving the parent's capability are blocked. This aligns with the "re-decided, never duplicated" philosophy (§1.5g) but imposes a technical constraint on SDK consumers.

### 3. Register Loop and Manifest Tenant Selection
There is no remaining way for a manifest to choose its composition tenant or for the loop to disagree with the loader's placement.
*   **Reasoning:** `manifest_under_tenant` uses `namespaced_key` to force every artifact key under the `resolved_tenant`. Even if a manifest names `other-tenant/key`, `namespaced_key` prepends the victim tenant (e.g., `victim/other-tenant/key`). 
*   **The Guard:** `_mint_register` checks `_tenant_of_key(key) == tenant`. Since the loader supplies the `tenant` and has already confined the keys, the manifest is effectively jailed. The loop's refusal is the final guard ensuring the composition root only mints for its own identity.

### 4. Read Routes and Tenant Isolation
No read doors (HTTP or MCP) were found that name Control Plane data without the capability's tenant.
*   **Symbols:** The routers in `agent.py`, `config.py`, and `skill.py` all rigorously apply `within_tenant` using `authorized.tenant`. 
*   **Isolation:** A read request for a foreign tenant's key (e.g., `/config/resolution?key=other/k`) is met with `absent(key, version)`, returning a 404 byte-identical to a non-existent key. This prevents existence oracles and cross-tenant reconnaissance (fixing **F-READ-01..04**).

### 5. Verification of Rejections
The two rejections in the prompt are correct based on the inlined source:
*   **Gemini (drop principal check):** Rejecting this was correct. If `verify` stopped checking the `principal` field, a capability minted for `Principal A` could be retargeted to `Principal B` via `object.__setattr__` without the record-mismatch being caught. This is verified by the reddening of `TestRetargeting[...principal]`.
*   **Codex (constant decision_id):** Rejecting this was correct. Using a constant `decision_id` for composition breaks the audit link between a specific registration and its unique composition event in the audit log. The reddening of `test_every_registered_entry_is_preceded_by_its_own_composition_event` (M23) confirms this dependency.
```


## Final round — Dave's one question at `e385df29`

### codex

```text
No panel finding.

I do **not** find a governed served route that reaches a protected handle with an absent, wrong-kind, wrong-resource, or wrong-tenant capability.

What I re-read:

- HTTP mint path: `AuthorizationGate.__call__` authenticates, selects tenant via `acting_tenant`, resolves the declared route resource via `_resource`, authorizes exactly `(tenant, action_id, resource)`, rejects unmintable decisions, then calls `mint(kind_for_action(action_id), ...)`.
- HTTP handler pickup: `authorized_from_request` verifies the stashed object with `verify`, checks the endpoint’s `@authorizes(...)` action via `route_authorization`, and all inlined routes request the concrete kind.
- MCP path: `TenantGuardedServer._guard` selects tenant via `_select_tenant`, reads the declared resource, authorizes exactly that tuple, rejects unmintable decisions, then mints and passes `authorized` as the first body argument.
- Protected handles re-check: `WorkflowEngine.execute`, `WorkflowEngine.resume`, `GrantLedger.request`, `GrantLedger.revoke`, `ControlPlaneRegistry.register*`, `InMemoryStateStore.put`, `authorized_write_target`, and `govern_dereference` all verify the capability before mutation/read authority is spent.
- Tenant/resource binding: registry writes use `_door_key`; workflow routes construct from `authorized.resource`; grant request uses `_require_covers`; dereference verifies against `reference.reference`; artifact writes derive target from the verified capability.

Ruled/non-findings I did not count:

- Same-interpreter private table/sentinel attacks are outside threat model per `capability.py`.
- The composition key grammar residual remains exactly that; I did not retune `_mint_register_at_composition`.
- `CompositionRegister` is now distinct and only minted through `mint_at_composition`; served doors cannot mint it because `kind_for_action` refuses `CompositionRegister.action_id`.
- `authorized_from_request`’s kind-less overload is a residual, but the inlined served HTTP routes use concrete `kind=...`.

So my answer to the one question is: **not found in the inlined source**.
```

### cursor

```text
## Verdict

**CLEAR on the one question** at `security-tier-0` @ **e385df293c6f4e3e0304ca4df3c98af9c12bbc23**.

I did not find a governed served route that reaches a §1.2 protected handle (`verify` / `verify_any` gate) with the capability **ABSENT**, **WRONG KIND**, **WRONG RESOURCE**, or **WRONG TENANT** at that handle.

`★ Insight ─────────────────────────────────────`
D-IMPL-353’s bank claim is not “every Python call is capability-checked.” It is narrower: **HTTP gate + MCP `TenantGuardedServer` are the only mint sites**, and **mutating / evidence handles refuse to run without a mint for that exact kind + resource (+ tenant on the capability)**. Reads that never take `Authorized` (registry `resolve`, state `get`) are door-filtered, not handle-verified.
`─────────────────────────────────────────────────`

---

## Already ruled (reported, not re-derived)

| Item | Disposition |
|---|---|
| In-process introspection (`verify.__globals__`, `gc`, `sys.modules`, replace `verify`) | Threat-model limit (Dave 2026-09-25) — not a finding |
| Composition key grammar / `max_ttl_key` | Named residual R1 — not retuned |
| Lint scope excludes `examples/` / `tools/` | R3 |
| FastMCP drops unknown wire args | SEC353-J-01 |
| `producer-unavailable` row vocabulary | SEC353-J-02 |
| `authorized_from_request` kind-less overload | R6; no production route uses it (only tests) |
| `open_product(approval_sink=)` | R7 vestigial |

---

## Fixes from prior rounds — re-read and holding

**`CompositionRegister` distinct from door `Register`**

- `CompositionRegister` / `kind_for_action` refuse door mint of `composition.register`
- `COMPOSITION_KINDS = (ReplayMint, CompositionRegister)`; `mint_at_composition` refuses door kinds
- Registry `REGISTER_KINDS` admits both by identity; composition roots (`manifest._mint_register`, `boot._mint_invalidation_register`, `resolver._mint_register_at_composition`, `product_door._registration`) mint `CompositionRegister` only

**Skill-grant foreign definition key**

- `skill.py::grant` runs `within_tenant` **before** `control_plane.resolve`; foreign key → same absent 404 as missing

---

## What was walked (capability at the handle)

| Surface | Mint | Handle check |
|---|---|---|
| HTTP mutating (agent/config/skill/artifact/workflow/HITL) | `AuthorizationGate` → `mint` | Registry / catalog / ledger / store / engine / transport `verify` / `verify_any` on capability resource |
| HTTP evidence (artifact get, replay) | Gate | `govern_dereference` → `verify_any` vs `reference.reference` |
| MCP tools/resources | `TenantGuardedServer._guard` → `mint` | Same pattern; HITL submit binds `submission.event_key` |
| Workflow execute/resume | Gate `Execute`/`Resume` | `verify` vs `workflow.definition_key`; factory resolves `authorized.resource` |
| State / artifact writes | Derived from door kinds | `STATE_WRITE_KINDS` / `authorized_write_target` |
| Composition boot paths | `mint_at_composition` only | Not served callers; lint `COMPOSITION_MINT_SITES` |

`★ Insight ─────────────────────────────────────`
Where the design is tightest, the door **stops being a second source**: workflow invoke/resume `assert authorized.resource == body.definition_key`, product retrieve asserts `product_class`, and registry/catalog/HITL submit take the target **only from the capability**. Where it is looser (agent/config keyed GETs, workflow status), the gate still minted from the same request line; the handler filters by `authorized.tenant` but resolves the FastAPI-bound `key` / `execution_id`.
`─────────────────────────────────────────────────`

---

## Candidates considered and retracted

**1. Agent/config keyed GET uses `key` not `authorized.resource`**  
Re-read: `agent.py::declaration` / `config.py::resolution` + gate `_resource` QUERY (exactly one value). Under the gate there is no demonstrated wire split between mint resource and handler `key`. `control_plane.resolve` is not a capability-typed §1.2 handle. **Not a finding** — defense-in-depth residual only (no `assert key == authorized.resource`).

**2. `experience.get_replay_record` does `del authorized` then `replay_seam()`**  
Re-read: `AgentInvokerProtocol` / replay reader Protocols are **deployment seams by design**; they are not `govern_dereference`. HTTP replay still binds address → `govern_dereference`. **Not a capability-handle bypass** under the framed question (ruling owed elsewhere: coarse `resource_route()` vs address-bound HTTP).

**3. `invoke_agent` uses `ACTION_WORKFLOW_INVOKE` and drops `Authorized[Execute]`**  
Re-read: documented HANDOFF; invoker Protocol takes no capability. Does not reach `WorkflowEngine.execute` through SDK wiring. **Not a finding** against §1.2 engine handle.

**4. Product doors call `govern_entitlement(grant=…)` without passing `ProductRetrieve`**  
Re-read: no `verify(…, ProductRetrieve)` handle exists in `src/`; product retrieve is door-mint + entitlement plane. Capability tenant/resource still constrain the door’s inputs. **Not the framed bypass.**

---

## Residuals (do not re-open as this panel’s CRITICAL)

- Composition `max_ttl_key` grammar (R1)
- In-process forge via interpreter (R2)
- Lint / FastMCP / producer vocabulary / kind-less overload / vestigial `approval_sink`
- Optional harden: bind keyed HTTP reads and workflow status to `authorized.resource` explicitly

---

## Bank-posture bottom line

For served HTTP and MCP surfaces at this SHA: mint is total at the two sites; protected handles fail closed on absent/wrong kind/resource; composition cannot mint door `ConfigRegister`; skill-grant no longer oracle-resolves foreign keys. **No new bypass of the stated claim.**
```

### gemini

```text
The bypass is located in **`src/ccf/artifacts/protocol.py::authorized_write_target`**, where a governed served route reaching the **`ArtifactStore.put`** handle can perform an unauthorized write to a resource other than the one minted in its capability by using the **`DerivedWrite`** payload.

### The Bypass: `DerivedWrite` resource mismatch
In the addressed write path (the standard `ArtifactWrite` route), the store extracts the `artifact_class` and `name` from the capability's resource string. However, if the payload is a `DerivedWrite` object, the store extracts the target class and name **from the artifact itself** (the user-supplied body) while continuing to verify the capability against its own `resource` string.

```python
# src/ccf/artifacts/protocol.py

def authorized_write_target(
    authorized: ArtifactWriteAuthority, artifact: object, *, write_kinds: WriteKinds
) -> tuple[WriteTarget, object]:
    # ...
    resource = getattr(authorized, "resource", "")
    if isinstance(artifact, DerivedWrite):
        # [BYPASS] The target class and name are taken from the CALLER'S object...
        artifact_class, name, payload = artifact.artifact_class, artifact.name, artifact.artifact
        derived = True
    else:
        # ... whereas addressed writes take them from the capability's resource.
        artifact_class, _, name = resource.partition(NAME_SEGMENT_SEPARATOR)
        payload = artifact
        derived = False
    
    # [BYPASS] The capability is verified against its OWN resource (tautology), 
    # NOT against the class/name extracted from the DerivedWrite above.
    kinds = write_kinds.for_class(artifact_class) if artifact_class else (ArtifactWrite,)
    verify_any(authorized, kinds=kinds, resource=resource)
```

If a mechanism-written class (one where `write_kinds.is_declared(artifact_class)` is true) admits the `ArtifactWrite` kind in its `kinds` set, a caller with an `ArtifactWrite` capability for any resource `classA/nameA` (granted by the gate) can present a `DerivedWrite` naming `classB/nameB`. `verify_any` will prove the capability is genuine for `classA/nameA`, but the handle will return a `WriteTarget` for `classB/nameB`. Reaching the **`ArtifactStore.put`** handle without a valid authorization mint for the exact **resource** being written violates the **D-IMPL-353 §1.2** and **§1.5f** invariants.

### Comparison to safe derived paths
- **`src/ccf/controlplane/registry.py::register_versioned`**: This handle correctly narrows the derived path to the `SkillGrant` kind only (which no door can obtain for an arbitrary key) and relies on the `GrantLedger` to have previously bound the capability's resource (the agent definition) to the definition object before deriving the grant's own key.
- **`WorkflowStatusRead`**: While the handler uses `execution_id` from the query string to build the state key, the `authorized_from_request` read in **`grants.py`** combined with the gate's resource extraction ensures that the capability and the parameter both originate from the same wire value.

The **`ArtifactWrite`** door in **`runtime/ccf_runtime/http_api/routes/artifact.py`** is the governed served route that exposes this discrepancy by passing the `body.artifact` directly to the store.
```
