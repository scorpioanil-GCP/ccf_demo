# 353-03 — every `src/` handle REQUIRES the capability for its own action

`D-IMPL-353` §1.2, §1.3, §1.5 and §2 P3, Lane HANDLES. The registry, the state
store, the artifact store, the replay writers and the grant ledger each took
their tenant, their target and their actor **from the caller** — `key`,
`tenant_id`, `artifact_class`, `name`, `actor`. Under the ruling that closed
the first draft of the design (*"unauthorized work is unrepresentable, not
'missed a check'"*), each now takes an `Authorized[<its kind>]` as its first
parameter, with no default, calls `ccf.authz.capability.verify` before its
first real statement, and takes the tenant, the target and the audit actor from
the capability. The parameters that used to carry them are **deleted**, so
there is no second source: a write under another tenant is not refused, it
cannot be written down.

Every retired name below was introduced by
`350-04-governed-record-classes-are-not-client-writable.md`; the two fragments
pair as a short-lived surface — that fragment's `added`, this one's `removed`
— and the reader should read this one against it.

## The mechanism, in one paragraph

The frozen seam's `verify` takes exactly one kind and binds the capability's
resource by equality (§1.5c, f, g). Three of the five handles are legitimately
reached under more than one kind — the registry by three doors, the state store
by the engine and the ledger, the artifact store by a declaration's kinds — so
`ccf.controlplane.state.verify_any` selects, by identity, which permitted kind
the capability was minted for and hands that one to `verify`; a reassigned
`kind` still dies on the mint tuple. Where a handle acts on the resource the
authorizer decided on — the registry key, the client artifact target
`"<class>/<name>"` — the target IS `authorized.resource` and there is no
parameter for it. Where a handle performs a **derived write** — the engine's
state and trace for the run an `Execute` started, the ledger's grant artifact
and state for the definition a `SkillGrant` named, the replay writer's record
under a composition-minted `ReplayMint` — the decision could not name a record
that did not yet exist, so the mechanism supplies the record's identity within
the tenant (`record_id`, a `DerivedWrite`), the store derives the key under
`authorized.tenant`, and `verify` binds the capability's own resource; the
tenant is where the authority bites, and it bites structurally (§1.2, the
derived-writes clarification; §1.3).

## What did NOT change

- **Read paths.** `get`, `exists`, `resolve_uri`, `versions` on both stores;
  `resolve`, `resolve_latest`, `peek`, `versions`, `keys_of_class` on the
  registry; `get` and `items` on the state store. Reads stay governed at the
  delivery boundary (`D-IMPL-345`) and in Lane MCP2's `govern_dereference`.
- **Addressing, immutability and the naming index.** Identity is still
  `sha256(canonical_bytes(...))`; `@latest` is still refused by the shared
  parser; the index is still append-only; a replay record is still named by its
  snapshot id and a query pin by its content hash, so no recorded URI stops
  resolving.
- **The audited-write token.** `StateWriteToken` and `AuditedStateWriter`
  remain the D-20 closure; the capability is a second proof of a different
  fact and travels beside it, never instead of it.
- **The D-05 bump check, the class binding, and every registry refusal value.**
- **The state key's characters.** `{tenant}/{record_id}` is what the engine
  already wrote; the derivation moved into the store, the string did not move.

## Where this fragment departs from the design text, and why

- **The state put takes `record_id`.** §1.2's table says the key is derived from
  `authorized.tenant` and `authorized.resource`. For `Execute` the resource is
  the workflow *definition* key (`runtime/ccf_runtime/http_api/routes/workflow.py::build_router`
  binds `definition_key`), so every execution of one definition would share one
  key and the second would be refused as already existing; for `SkillGrant` the
  resource is the agent definition and the ledger keys by grant hash. The
  design's own derived-writes paragraph already says the key is *"derived from
  `authorized.tenant` and the execution id"*; this fragment implements that
  sentence: the tenant half cannot be supplied by a caller, the record's
  identity within it is the mechanism's.
- **`STATE_WRITE_KINDS` is four kinds, not two.** §1.2 names `Execute | Resume`;
  the grant ledger is the other state writer and holds `SkillGrant` /
  `SkillRevoke`.
- **`register_versioned` also admits `SkillGrant`, as a derived registration.**
  The ledger registers the grant artifact its `skill.grant` decision created;
  the key is derived from the capability's tenant, the declared class and the
  artifact's own `name` — `skill_grant_key(grant)` exactly — and a caller
  supplies none of it.
- **`ReplayMint` is per tenant.** `mint_at_composition` mints for one tenant;
  a multi-tenant deployment composes one `ReplayWriter` per tenant.

## Method reshapes the generated manifest does not carry

The manifest records a class's constructor shape and a function's signature.
These handles changed their **methods**, and the Protocols are not plain
classes, so they carry no section below; they are recorded here so an adopter
finds them.

| handle (`path.py::Symbol`) | before | after |
| --- | --- | --- |
| `src/ccf/controlplane/registry.py::ControlPlaneRegistry.register` and `ControlPlaneProtocol.register` | `(key, artifact, *, actor=None)` | `(authorized: RegisterAuthority, artifact)` — key = `authorized.resource`, actor = `authorized.principal`, the key's tenant segment must equal `authorized.tenant` |
| `src/ccf/controlplane/registry.py::ControlPlaneRegistry.register_typed` | `(key, artifact, artifact_class, *, actor=None)` | `(authorized: RegisterAuthority, artifact, artifact_class)` |
| `src/ccf/controlplane/registry.py::ControlPlaneRegistry.register_versioned` | `(key, artifact, artifact_class, *, actor=None, reissuable=False)` | `(authorized: DerivedRegisterAuthority, artifact, artifact_class, *, reissuable=False)` |
| `src/ccf/controlplane/state.py::ControlPlaneStateStore.put` and `InMemoryStateStore.put` | `(record_class, key, record, *, token)` | `(authorized: StateWriteAuthority, record_class, record, *, record_id, token)` — key = `state_key(authorized.tenant, record_id)`; a record declaring another `tenant` is refused |
| `src/ccf/controlplane/state.py::AuditedStateWriter.write` | `(record_class, key, record, *, event)` | `(authorized, record_class, record, *, record_id, event)` |
| `src/ccf/artifacts/protocol.py::ArtifactStoreProtocol.put`, `src/ccf/artifacts/file_store.py::FileArtifactStore.put`, `src/ccf/artifacts/mcp_store.py::McpArtifactStore.put` | `(*, tenant_id, artifact_class, name, artifact, minted=None)` | `(authorized: ArtifactWriteAuthority, artifact)` — first statement `authorized_write_target` |
| `src/ccf/replay/serve.py::QueryPinWriter` (added after the baseline by 15.2-08, so its constructor reshape shows under that entry) | `QueryPinWriter(*, store, artifact_class)`; `write_query_bytes(*, tenant_id, queries)` | `QueryPinWriter(*, authorized: Authorized[ReplayMint], store)`; `write_query_bytes(*, queries)`; `tenant_id` and `artifact_class` properties read from the capability |
| `src/ccf/skills/grants.py::GrantLedger.request` | `(grant, *, definition, actor)` | `(authorized: Authorized[SkillGrant], grant, *, definition)` — actor = `authorized.principal`; the resource is bound to `definition` |
| `src/ccf/skills/grants.py::GrantLedger.revoke` | `(grant_hash, *, actor)` | `(authorized: Authorized[SkillRevoke])` — the grant hash IS `authorized.resource` |

## ccf.artifacts.protocol.WriteKinds

- Surface: ccf.artifacts.protocol.WriteKinds
- Public surface: true
- Change type: added
- Before: absent — the store had a `GovernedRecordClasses` set and a separate token that said *this writer is mechanism*
- After: the deployment's declaration, bound to a store at construction with no default, of which artifact classes are **mechanism-written and under which action kinds** — `WriteKinds.declare({"ccf.replay-record": (ReplayMint,), "ccf.workflow-trace": (Execute, Resume)})`. `for_class(class_id)` answers the declared kinds or `(ArtifactWrite,)`; `is_declared`, `declared_classes` for introspection. A declaration refuses an id that is empty, untrimmed or carries `/` (the naming-key collision `350-04` measured), an empty kind set, a non-kind, and **`ArtifactWrite` itself**: the client kind is what an *undeclared* class requires, and a class a door and mechanism could both file under is the `SEC-004` naming lane reopened
- Why: §1.2 — *"the kind IS the mint"*. Which kind a write requires is looked up per class from a declaration; mechanism interprets it and names no class (CLAUDE.md §6.4)
- Migration: every store constructor now takes `write_kinds=`; a deployment declares its replay-record class and query-pin class under `ReplayMint` and its workflow-trace class under `(Execute, Resume)`. A store whose replay class is undeclared refuses the fabric's own writer at first use — wrong kind — which is the loud boot-time failure §3 asks `create_app` to surface

## ccf.artifacts.protocol.WriteKindsDeclarationError

- Surface: ccf.artifacts.protocol.WriteKindsDeclarationError
- Public surface: true
- Change type: added
- Before: absent (`GovernedClassDeclarationError` played the role for the retired declaration)
- After: raised at declaration — at boot, where an operator sees it — when a `WriteKinds` declaration could not be enforced. An `ArtifactStoreError`, never a `ValueError`, for the reason its predecessor was not one
- Why: §1.2
- Migration: none

## ccf.artifacts.protocol.DerivedWrite

- Surface: ccf.artifacts.protocol.DerivedWrite
- Public surface: true
- Change type: added
- Before: absent — a writer passed `artifact_class=` and `name=` to `put`
- After: the derived-write shape: `DerivedWrite(artifact_class=..., name=..., artifact=...)`, presented to `put` by the fabric's own mechanism (the replay writer naming a record by its snapshot id, the engine naming a trace by its execution id) when the capability authorized the action that produced the record rather than the record itself. The store files the **inner** artifact — the wrapper never reaches the substrate and never enters the content address — under the capability's tenant, after verifying the capability against the kinds declared for the class. Refused outright for a class that is not declared, so a door holding `ArtifactWrite` for one target cannot use it to file under another name
- Why: §1.2 (the derived-writes clarification): *"a state or trace write ... acts on an execution the decision started"*; the target did not exist when the decision was made, so the mechanism supplies it and the tenant stays the capability's
- Migration: `ReplayWriter` and `QueryPinWriter` build it internally; the engine's trace write and any other fabric writer of a declared class build one where they used to pass `artifact_class=` and `name=`

## ccf.artifacts.protocol.WriteTarget

- Surface: ccf.artifacts.protocol.WriteTarget
- Public surface: true
- Change type: added
- Before: absent
- After: the resolved `(tenant_id, artifact_class, name)` a verified write lands at, returned by `authorized_write_target` only. `tenant_id` is `authorized.tenant` and nothing else (§1.3)
- Why: a store's `put` should read `target = authorized_write_target(...)` and then act on the target and on nothing it was handed directly
- Migration: none for callers; implementers of `ArtifactStoreProtocol` use it as the first statement of their own `put`

## ccf.artifacts.protocol.ArtifactWriteAuthority

- Surface: ccf.artifacts.protocol.ArtifactWriteAuthority
- Public surface: true
- Change type: added
- Before: absent
- After: the static type of `put`'s first parameter — `Authorized[ArtifactWrite] | Authorized[ReplayMint] | Authorized[Execute] | Authorized[Resume]`, the kinds under which the client door and the SDK's own writers file artifacts. A handler holding any other kind is a `mypy --strict` error at the call; the runtime authority for a given class is the store's `WriteKinds`
- Why: §1.4, §1.5b — the static tooth
- Migration: a fabric writer of a declared class under a kind outside this union (a HITL action record under `HitlSubmit`, should Lane HITL-DOOR file one) widens the alias in one place

## ccf.artifacts.protocol.ArtifactWriteRefused

- Surface: ccf.artifacts.protocol.ArtifactWriteRefused
- Public surface: true
- Change type: added
- Before: absent (`GovernedWriteRefused` was the refusal for a client naming a governed class)
- After: raised **after** the capability is verified genuine — a fabricated, retargeted or wrong-kind capability dies in `verify` first — for the target shapes a genuine capability still cannot write: an addressed write whose resource is not `"<class>/<name>"`, or a `DerivedWrite` naming an undeclared class. Not an `ArtifactNotFound`, for `350-04`'s reason
- Why: §1.5f
- Migration: none

## ccf.artifacts.protocol.authorized_write_target

- Surface: ccf.artifacts.protocol.authorized_write_target
- Public surface: true
- Change type: added
- Before: absent (`held_writable_class` was the one shared check)
- After: the ONE function both shipped stores run first, before canonicalization, before the address is derived and before the substrate is touched: pure parsing of the target (from the `DerivedWrite` or from the capability's resource), then `verify_any` against the kinds the declaration names for that class, then the shape refusals. Returns the `WriteTarget` and the payload to canonicalize
- Why: §1.5c/f/g applied on the write path every transport reaches — *"the doors are not where the substrate is touched"*
- Migration: none for callers; implementers of `ArtifactStoreProtocol` call it as the first statement of `put`

## ccf.controlplane.registry.RegisterAuthority

- Surface: ccf.controlplane.registry.RegisterAuthority
- Public surface: true
- Change type: added
- Before: absent
- After: `Authorized[Register] | Authorized[AgentDeclare] | Authorized[SkillCatalogRegister]` — the static type of the door registration handles' first parameter (§1.2, the registry-union clarification: three doors register under three declared actions, and policy granularity is preserved)
- Why: §1.4, §1.5b
- Migration: none

## ccf.controlplane.registry.DerivedRegisterAuthority

- Surface: ccf.controlplane.registry.DerivedRegisterAuthority
- Public surface: true
- Change type: added
- Before: absent
- After: `RegisterAuthority | Authorized[SkillGrant]` — what `register_versioned` accepts: the door kinds, or the one derived kind
- Why: §1.2 — the ledger's grant artifact is a record the `skill.grant` decision created
- Migration: none

## ccf.controlplane.registry.REGISTER_KINDS

- Surface: ccf.controlplane.registry.REGISTER_KINDS
- Public surface: true
- Change type: added
- Before: absent
- After: `(Register, AgentDeclare, SkillCatalogRegister)` — the kinds under which a door registers; the handle verifies against whichever the capability was minted for and the key IS the capability's resource
- Why: §1.2
- Migration: none

## ccf.controlplane.registry.DERIVED_REGISTER_KINDS

- Surface: ccf.controlplane.registry.DERIVED_REGISTER_KINDS
- Public surface: true
- Change type: added
- Before: absent
- After: `(SkillGrant,)` — the kinds under which registration is a derived write, admitted by `register_versioned` alone, the key derived from the capability's tenant, the declared class and the artifact's own `name`
- Why: §1.2
- Migration: none

## ccf.controlplane.registry.CrossTenantKeyRefused

- Surface: ccf.controlplane.registry.CrossTenantKeyRefused
- Public surface: true
- Change type: added
- Before: absent — nothing compared a registration key's tenant to anything
- After: the ONE tenant comparison §1.3 places on the registry, inside the handle that holds the capability: the key's tenant segment (before the first `/`) must equal `authorized.tenant`; a key with no tenant segment fails the same way, as does a derived registration whose artifact claims another tenant or names no `name`. A `PermissionError`, raised and never returned, after `verify` has proven the capability genuine — the disagreement is the authorizer's mapping having allowed a cross-tenant resource, not a governance outcome
- Why: §1.3 — *"That is the one comparison, and it is inside the handle that holds the capability, not in a door that might forget"*
- Migration: every Control Plane key carries a tenant segment; bare keys (`"policy"`, a class id alone) are refused

## ccf.controlplane.state.STATE_WRITE_KINDS

- Surface: ccf.controlplane.state.STATE_WRITE_KINDS
- Public surface: true
- Change type: added
- Before: absent
- After: `(Execute, Resume, SkillGrant, SkillRevoke)` — the kinds whose handles write Control Plane state as a consequence of their action: the engine under the run's `Execute` / `Resume`, the ledger under the transition's `SkillGrant` / `SkillRevoke`
- Why: §1.2, the derived-writes rule; widened from the design's `Execute | Resume` because the ledger is the other state writer
- Migration: none

## ccf.controlplane.state.StateWriteAuthority

- Surface: ccf.controlplane.state.StateWriteAuthority
- Public surface: true
- Change type: added
- Before: absent
- After: the union type of `put`'s first parameter over `STATE_WRITE_KINDS`
- Why: §1.4, §1.5b
- Migration: none

## ccf.controlplane.state.verify_any

- Surface: ccf.controlplane.state.verify_any
- Public surface: true
- Change type: added
- Before: absent — the seam's `verify` takes one kind
- After: `verify_any(authorized, *, kinds, resource) -> type[ActionKind]`: selects, by identity, which of `kinds` the capability's current `kind` is and hands that one to `verify`, which proves the reading against the mint tuple; if the current kind is none of them, the first is passed so the failure is the wrong-kind diagnostic naming the kind actually minted. Used by the registry, the state store and the artifact store
- Why: three handles are legitimately reached under more than one kind and the seam is frozen; nothing is trusted from the read (§1.5g)
- Migration: none; a handle reached under one kind calls `verify` directly

## ccf.controlplane.state.state_key

- Surface: ccf.controlplane.state.state_key
- Public surface: true
- Change type: added
- Before: absent — each consumer spelled its own key (`f"{tenant}/{execution_id}"` in the engine; the bare grant hash in the ledger)
- After: `state_key(*, tenant, record_id) -> "{tenant}/{record_id}"`, derived by the store from the capability's tenant and the record's identity; injective because the tenant may not carry the separator. Readers derive the same key the same way
- Why: §1.3 — the tenant on the write is the capability's, so the key's tenant half cannot be caller-supplied
- Migration: the engine's `_key` and the ledger's reads use it; grant state is now keyed under its tenant, and `GrantLedger.state` scans the class for an unqualified hash

## ccf.controlplane.state.split_state_key

- Surface: ccf.controlplane.state.split_state_key
- Public surface: true
- Change type: added
- Before: absent
- After: the `(tenant, record_id)` a `state_key` was built from; refuses a key with no tenant segment
- Why: consumers folding over `items()` recover the record id without re-deriving the grammar
- Migration: none

## ccf.controlplane.state.STATE_KEY_SEPARATOR

- Surface: ccf.controlplane.state.STATE_KEY_SEPARATOR
- Public surface: true
- Change type: added
- Before: absent — `"/"` spelled inline in the engine
- After: named once
- Why: the reason a tenant may not contain it is a fact about the grammar
- Migration: none

## ccf.controlplane.state.StateKeyError

- Surface: ccf.controlplane.state.StateKeyError
- Public surface: true
- Change type: added
- Before: absent
- After: raised at derivation when a tenant is empty, untrimmed or carries the separator, or a record id is empty — a misconfiguration surfaced where the operator sees it
- Why: §1.3 — two tenants must not be able to share a key
- Migration: none

## ccf.controlplane.state.StateTenantMismatch

- Surface: ccf.controlplane.state.StateTenantMismatch
- Public surface: true
- Change type: added
- Before: absent
- After: raised before the dict is touched when a record that *declares* a `tenant` declares one other than the capability's; records stay otherwise opaque
- Why: §1.3, at Lane ENGINE's request on the join — the store files under the capability's tenant and a record may not name another
- Migration: none

## ccf.replay.serve.ReplayTenantMismatch

- Surface: ccf.replay.serve.ReplayTenantMismatch
- Public surface: true
- Change type: added
- Before: absent
- After: raised by `ReplayWriter.write_replay_record` and `QueryPinWriter.write_query_bytes` before the store is touched when the record or a query names a tenant other than the writer's capability's — a resolver wired to the wrong writer, a deployment defect, the `ProductRecordMismatch` posture
- Why: §1.3
- Migration: none

## ccf.skills.grants.GrantAuthorityMismatch

- Surface: ccf.skills.grants.GrantAuthorityMismatch
- Public surface: true
- Change type: added
- Before: absent
- After: raised by `GrantLedger.request` after `verify` when the capability does not cover the definition it was handed: the resource's tenant segment, the definition's tenant and the capability's tenant must be one tenant, and the resource must end in the definition's own name. A `PermissionError`, raised and never returned
- Why: §1.5f — *"where a handle is handed a target by an inner caller anyway, verify takes the target and refuses by identity of the resource string"*; the ledger cannot import the agent class id (a runtime cycle), so it binds the two segments it can
- Migration: none

## ccf.artifacts.protocol.GovernedRecordClasses

- Surface: ccf.artifacts.protocol.GovernedRecordClasses
- Public surface: true
- Change type: removed
- Before: the `350-04` declaration of which classes only mechanism may file under, defaulting to `NOTHING_GOVERNED`
- After: absent. `WriteKinds` carries the same declaration with the kind that writes each class, and has no default
- Why: §1.2 — *"the kind IS the mint"*; a default-open declaration is exactly what the design makes inexpressible
- Migration: `GovernedRecordClasses.declare("a", "b")` becomes `WriteKinds.declare({"a": (ReplayMint,), "b": (ReplayMint,)})`

## ccf.artifacts.protocol.NOTHING_GOVERNED

- Surface: ccf.artifacts.protocol.NOTHING_GOVERNED
- Public surface: true
- Change type: removed
- Before: the explicit empty declaration and both stores' default
- After: absent; `write_kinds` has no default
- Why: §1.2 — retired, not adapted
- Migration: declare the mechanism-written classes; a store that genuinely has none passes `WriteKinds.declare({})` and says so

## ccf.artifacts.protocol.GovernedWriteToken

- Surface: ccf.artifacts.protocol.GovernedWriteToken
- Public surface: true
- Change type: removed
- Before: the module-private-sentinel token that said *this write is the fabric's own*
- After: absent. The `ReplayMint` kind of `ccf.authz.capability.Authorized`, minted only by `mint_at_composition`, is that statement — with the tenant, the class and the deployment's `decision_id` bound to it
- Why: §2 P3 — *"`GovernedWriteHandle` and `minted=` are retired: the kind IS the mint"*
- Migration: none; its `ccf.contracts.guarded.GUARDED_TYPES` declaration retires with it (the join edits that census — the capability is the guarded type now)

## ccf.artifacts.protocol.GovernedWriteHandle

- Surface: ccf.artifacts.protocol.GovernedWriteHandle
- Public surface: true
- Change type: removed
- Before: an `ArtifactStoreProtocol` wrapper that attached the token to `put`
- After: absent. A writer holds its `Authorized[ReplayMint]` and passes it to `put` itself
- Why: §2 P3
- Migration: `ReplayWriter(store=GovernedWriteHandle(store), artifact_class=C)` becomes `ReplayWriter(authorized=mint_at_composition(tenant=..., principal=..., resource=C, decision_id=...), store=store)`

## ccf.artifacts.protocol.held_writable_class

- Surface: ccf.artifacts.protocol.held_writable_class
- Public surface: true
- Change type: removed
- Before: the one shared check every store's write path ran first
- After: absent; `authorized_write_target` is that first statement
- Why: §1.2
- Migration: implementers of `ArtifactStoreProtocol` call `authorized_write_target` where they called this

## ccf.artifacts.protocol.GovernedWriteRefused

- Surface: ccf.artifacts.protocol.GovernedWriteRefused
- Public surface: true
- Change type: removed
- Before: the typed refusal for a client write naming a governed class
- After: absent. That write now dies in `verify` as `CapabilityBypassError` (wrong kind: the class requires `ReplayMint`), before the store's own `ArtifactWriteRefused` is reached
- Why: §1.5d — *"reuse across actions is unrepresentable, not refused later"*
- Migration: a door that caught this catches `CapabilityBypassError`, which the gate lanes already translate

## ccf.artifacts.protocol.GovernedWriteForgery

- Surface: ccf.artifacts.protocol.GovernedWriteForgery
- Public surface: true
- Change type: removed
- Before: raised when something that was not a minted token was presented as one
- After: absent; a forged capability dies in `verify` as `CapabilityBypassError`
- Why: §1.1
- Migration: as above

## ccf.artifacts.protocol.GovernedClassDeclarationError

- Surface: ccf.artifacts.protocol.GovernedClassDeclarationError
- Public surface: true
- Change type: removed
- Before: the boot-time refusal of an unenforceable governed-class declaration
- After: absent; `WriteKindsDeclarationError` is its successor and refuses the same ids plus an empty kind set, a non-kind and `ArtifactWrite`
- Why: §1.2
- Migration: catch `WriteKindsDeclarationError`

## ccf.artifacts.file_store.FileArtifactStore

- Surface: ccf.artifacts.file_store.FileArtifactStore
- Public surface: true
- Change type: reshaped
- Before: `FileArtifactStore(*, root, governed=NOTHING_GOVERNED)`, a `governed` property, `put(*, tenant_id, artifact_class, name, artifact, minted=None)`
- After: `FileArtifactStore(*, root, write_kinds)` — required, keyword-only, no default — a `write_kinds` property, and `put(authorized, artifact)` whose first statement is `authorized_write_target`. A refused write leaves the substrate byte-for-byte as it was: no artifact file, no naming-index entry
- Why: §1.2, §1.3
- Migration: pass `write_kinds=WriteKinds.declare({...})`; call `put` with the capability and the artifact (or a `DerivedWrite`)

## ccf.artifacts.mcp_store.McpArtifactStore

- Surface: ccf.artifacts.mcp_store.McpArtifactStore
- Public surface: true
- Change type: reshaped
- Before: `McpArtifactStore(*, url, bridge, http_client_factory=None, governed=NOTHING_GOVERNED)`, a `governed` property, `put(*, tenant_id, artifact_class, name, artifact, minted=None)`
- After: `McpArtifactStore(*, url, bridge, write_kinds, http_client_factory=None)`, a `write_kinds` property, and `put(authorized, artifact)` which runs `authorized_write_target` **before the payload is encoded**, so a refused write never reaches the wire. What crosses the wire is the resolved target and the bytes; the capability never does — the server's wrapper mints its own for the caller it authenticated, and the server's store runs the identical check over its own declaration
- Why: §1.2 — the rule is the store's, so every transport inherits it
- Migration: as `FileArtifactStore`

## ccf.replay.serve.ReplayWriter

- Surface: ccf.replay.serve.ReplayWriter
- Public surface: true
- Change type: reshaped
- Before: `ReplayWriter(*, store, artifact_class)`; `write_replay_record(*, record)` put under `record.tenant_id`
- After: `ReplayWriter(*, authorized: Authorized[ReplayMint], store)` — verified at construction so a mis-wired composition root fails before any request; `tenant_id` and `artifact_class` properties read from the capability; `write_replay_record(*, record)` refuses a record naming another tenant (`ReplayTenantMismatch`) and files a `DerivedWrite` named by the snapshot id under the capability's tenant. One writer per tenant, by construction
- Why: §2 P3 — *"The fabric's own replay writer is handed a `ReplayMint` capability at composition by the deployment, not minted by a gate"*; §1.3
- Migration: the composition root calls `mint_at_composition(tenant=..., principal=..., resource=<record class>, decision_id=...)` once per governed class (and once more for `QueryPinWriter`'s class) and hands the result to the writer; the `artifact_class` argument is gone
