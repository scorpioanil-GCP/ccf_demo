# 391-01 (D-IMPL-391, 2026-10-17) — an approval counts only in the state store that paused the run

`D-IMPL-391`, SEC-001's residual (design 1.4), under Dave's six rulings of 2026-10-17
13:27 MST and his acceptance of the build brief at 15:25 MST
(`packaging/bank-controlled/SEC-001-AND-INDEX-RACE-BRIEF.md`, Part 1).

Before this, an approval was bound only to the content hash of the suspended
`WorkflowStateRecord`, which named no store, so two independent stores that suspended
the same execution at the same clock readings wrote byte-identical suspensions and one
approval counted in both (measured on `3f914416`: two passages on one approval).

## ccf.controlplane.state.STATE_STORE_IDENTITY_PATTERN

- Surface: ccf.controlplane.state.STATE_STORE_IDENTITY_PATTERN
- Public surface: true
- Change type: added
- Before: absent
- After: the shape a state store's identity must have: 64 lowercase hex characters (256 bits).
- Why: `D-IMPL-391`; `D-IMPL-378` decision 2 (b). The engine checks the shape; the conformance suite checks uniqueness and persistence.
- Migration: none.

## ccf.controlplane.state.StateStoreIdentityMissing

- Surface: ccf.controlplane.state.StateStoreIdentityMissing
- Public surface: true
- Change type: added
- Before: absent
- After: a `TypeError` raised by `state_store_identity_of` for a store with no well-formed identity; the workflow engine turns it into a `WorkflowWiringError` naming the identity rule.
- Why: decision 2 (b): *"Unsupported implementations refuse construction."*
- Migration: none.

## ccf.controlplane.state.state_store_identity_of

- Surface: ccf.controlplane.state.state_store_identity_of
- Public surface: true
- Change type: added
- Before: absent
- After: `state_store_identity_of(store) -> str` returns the store's identity or raises `StateStoreIdentityMissing`. It checks the shape only.
- Why: `D-IMPL-391`.
- Migration: none.

## ccf.controlplane.state.ConditionalStateStore

- Surface: ccf.controlplane.state.ConditionalStateStore
- Public surface: true
- Change type: reshaped
- Before: `scope`, `get_versioned`, `put_if`.
- After: also `identity` (a read-only property): minted once per substrate from a CSPRNG, persisted with the records, the same for every client in every process and across restarts, different for an independent substrate, minted per construction by a store whose records do not survive a restart. The docstring adds two MUSTs: a copied durable store refuses to open until an operator re-mints its identity (which strands every run in flight: their records name the old identity and are refused as another store's); and a path-backed store declaring `scope = "process"` holds an exclusive SEC-013 lease from open to close, refuses a second holder with `WriterLeaseHeld` naming the lock and the rule (logged in the refused process only), releases it on close and on collection, and offers it as `writer_lease()`, which is not a Protocol member.
- Why: rulings 1(a) and 2(a); the 2026-10-09 10:54 MST ruling (*"A copied store must refuse, not 'should.'"*).
- Migration: a deployment's own state store adds `identity` (and, if it declares `"process"` and is path-backed, the lease and `writer_lease()`), and runs `tests/conformance/test_gate_closure_and_conditional_write.py` against itself. A store without a well-formed identity is now refused when a workflow engine is built over it.

## ccf.controlplane.state.InMemoryStateStore

- Surface: ccf.controlplane.state.InMemoryStateStore
- Public surface: true
- Change type: behavior
- Before: no identity; no `writer_lease`.
- After: `identity`, minted per construction (its records live in the object, so a new object is a new store); `writer_lease()` returns the `"process"` declaration (`ProcessScopedWriterLease`), exact because no other process can reach its memory.
- Why: `D-IMPL-391`.
- Migration: none.

## ccf.hitl.transport.HITLTransportProtocol

- Surface: ccf.hitl.transport.HITLTransportProtocol
- Public surface: true
- Change type: behavior
- Before: `enqueue` appended every event it was given.
- After: `enqueue` is atomic on `(tenant, event_key, product_content_hash)`: an event whose triple is already pending is not queued again; a claimed event is not pending, so the primitives' give-back still re-files it; an enqueue that appends still discards the key's claim. The docstring adds the single-process lease MUST for a path-backed transport declaring `"process"`. Supersedes DESIGN-2b §6.4 ("no change").
- Why: ruling 4(a); Dave, 15:25 MST: *"The same paused run's request is filed only once. Third-party transports must meet the contract."*
- Migration: a deployment's own transport makes `enqueue` check and append in one atomic step, and runs the conformance suite's enqueue cases.

## ccf.hitl.transport.InMemoryHitlTransport

- Surface: ccf.hitl.transport.InMemoryHitlTransport
- Public surface: true
- Change type: reshaped
- Before: `enqueue` appended duplicates; no `writer_lease`.
- After: `enqueue` meets the new contract under its existing lock; `writer_lease()` returns the `"process"` declaration.
- Why: `D-IMPL-391`.
- Migration: none.

## ccf.controlplane.audit.AuditAction

- Surface: ccf.controlplane.audit.AuditAction
- Public surface: true
- Change type: reshaped
- Before: no action for a retired approval request.
- After: adds `workflow_request_retired`, appended when `rebind_legacy_suspension` retires a pending pre-upgrade request.
- Why: Dave, 15:25 MST: *"The re-pause retires the legacy request before enqueueing the fresh one, and audits the retirement."*
- Migration: an audit consumer that switches on the action admits the new value.

## ccf_runtime.workflow.state.WorkflowStateRecord

- Surface: ccf_runtime.workflow.state.WorkflowStateRecord
- Public surface: true
- Change type: reshaped
- Before: no store field.
- After: `state_store_identity: str | None`, hash-transparent at `None`, stamped by the engine on every record; `suspension_left_by` carries it. It is served on `GET /workflow/execution` (the served record must keep hashing to the request's `product_content_hash`): it tells a `WorkflowStatusRead` holder whether two executions share a store, and it is not a credential. `openapi.json` is regenerated.
- Why: `D-IMPL-391` (DESIGN-2b §6.2, §8).
- Migration: none; a record written before the change keeps its content address.

## ccf_runtime.workflow.engine.WorkflowEngine

- Surface: ccf_runtime.workflow.engine.WorkflowEngine
- Public surface: true
- Change type: behavior
- Before: an approval counted in any store whose suspension hashed alike; no single-process lease requirement.
- After: construction refuses, by name, a state store with no well-formed identity (asked before the generic conditional-store check) and a `"process"` store or transport that offers no `writer_lease` (after the eligibility check, before any binding). Resume refuses, by name, a record another store wrote (*"written by a Control Plane state store other than this engine's"*) and a `suspended` record written before the identity existed (naming `rebind_legacy_suspension`). A retried start finishes only a start this store wrote or one with no identity, and never restores a pre-upgrade suspension. New `rebind_legacy_suspension(authorized, workflow, *, execution_id)` retires the pending pre-upgrade request (audited `workflow_request_retired`), then re-pauses the run under this store (audited `workflow_suspended`, one new request under the same key); a fresh approval is required.
- Why: ruling 1(a); decision 2 (b); Dave's answers of 15:25 MST.
- Migration: a durable store holding runs paused before this change rebinds each (`items(WORKFLOW_STATE)` lists them) and asks for a fresh approval. The SDK's own in-memory store keeps nothing across the upgrade restart, so it has none.

## ccf_runtime.erasure.ErasureDoor

- Surface: ccf_runtime.erasure.ErasureDoor
- Public surface: true
- Change type: behavior
- Before: `complete` filed the approval and appended its write-ahead index entries before the engine was asked to resume, so a run the engine refuses (paused before the store identity existed, or written by another store) left entries naming that approval, and every later completion was refused `approval-not-recorded`.
- After: `complete` refuses such a run `workflow-refused` before it files or appends anything; after `rebind_legacy_suspension` and a fresh signed approval the erasure completes.
- Why: `D-IMPL-391`; found by the independent review of the build.
- Migration: none.
