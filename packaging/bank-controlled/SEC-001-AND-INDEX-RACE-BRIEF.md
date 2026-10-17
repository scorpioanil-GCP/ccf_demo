<!--
Copyright (c) 2026 David Castillo. All rights reserved.
Use, copying, modification, and distribution of the covered material
are governed by the CCF SDK Interim Software and Patent License
in the repository-root LICENSE.md and any controlling signed agreement.
Rights under that interim license begin only upon its execution
and are limited to its stated scope and term.
-->
# SEC-001's residual (design 1.4) and the evidence name-index race: build brief

**Status, 2026-10-17 MST: PROPOSED for Grok's review. Nothing is built.** Dave, 13:27:
*"Write both fixes (SEC-001 residual under those six rulings, and the index race) into one build brief for
Grok. No code until the brief is accepted."*

- **Code baseline:** `main` at `3f914416`. The records this brief cites (register item 18, `D-IMPL-390`,
  `D-IMPL-391`) are on branch `sec001-residual-index-race`.
- **Register:** `OPEN-SECURITY-ITEMS.md` item 1 (SEC-001's residual, the last CRITICAL) and item 18 (the index
  race). **Decisions:** `D-IMPL-391` (SEC-001) and `D-IMPL-390` (the index race).
- **Evidence:** `ccf_saves/2026-10-17-sec001/`, outside the repository.
  - A five-agent research run, whose adversarial verifier confirmed 29 claims, narrowed 11 and refuted 1.
  - A two-agent check of this brief's first draft: 37 citations confirmed, 16 narrowed and 1 refuted, and 5
    blocking design findings, each tested by experiment (`verify-brief/proto/`).
  - Every correction is applied below.

## 0. The rulings this brief is built under

**Dave, 2026-10-17 13:27 MST, verbatim:**

- *"1(a): Restate B to match the October 10 ruling. Approval counts only in the store that paused the run.
  Pre-upgrade paused runs are refused by name, re-paused with an audit record, and need a fresh approval."*
- *"2(a): Stores labeled single-process get the graph store’s lock. A second process is refused by name."*
- *"3(a): Compare everything except the store ID and the fingerprints built from it. Those fingerprints must agree
  with each other."*
- *"4(a): Key the duplicate-request fix by the paused run’s fingerprint."*
- *"5(a): Qualified closure wording: “Closed for every store that meets the identity rules, checked by tests. A
  copied store must refuse to open. Does not reach the bank’s setup, which builds no approval queue.”"*
- *"6: Design 1.4 first, on its own."*
- On the three-issue cap: *"Add the index race as a fourth. Do not drop Gap 1, Gap 4, or CP06C-F-09."*

**The earlier rulings design 1.4 carries** (`docs/DECISIONS.md`):

- **:4820, 2026-10-09, decision 2 (b):** *"Bind approval events and closures to the suspending state store’s stable
  identity. It must survive restart and distinguish independent stores. Unsupported implementations refuse
  construction. One approval must authorize at most one passage."*
- **:4822, 2026-10-09 10:54 MST, on design 1.4:** *"Refuse runs paused before the upgrade, with an audited re-pause
  and a fresh approval. Do not show the store id on queued requests. A copied store must refuse, not “should.”"*
  That is DESIGN-2b's Q-2b-1 (a), Q-2b-2 (a) and Q-2b-3 (b).
- **:4824, 2026-10-09 16:38 MST:** Grok's text, adopted by Dave, on the duplicate-request item (d2ext P-1): *"(a) now.
  (c) with design 1.4, not in this batch."* So the disclosure came first, and the atomic enqueue joins design 1.4.

**Two readings stated, because the scoping message to Dave was wrong on both:**

- **The date.** "The October 10 ruling" in 1(a) is read as the 2026-10-09 10:54 MST entry (`:4822`). No 2026-10-10
  entry concerns paused runs. The scoping message gave the wrong date.
- **The build order.** The scoping message said designs 1.1–1.3 were unbuilt. They were built and merged on
  2026-10-12 (`e92d1c01`, merged by `b468cee4`). So what remained of the 10:54 order was "1.4, then 1.5", and ruling
  6 changes no order.

**The design itself** is `DESIGN-2b-store-identity.md` on `dl-378-record`
(`records/2026-10-09-d-impl-378-designs/designs/beta/`). Its prototype (`prototype-2b.patch`, applied by
`designs/beta/probes/edits_2b.py`) was measured green against `a539c215`. It is a starting point, not the build.

---

## Part 1 — SEC-001's residual

### 1.1 The residual, measured

**What is open.** The register's words are *"Separate processes sharing one approval store are not detected;
approval identity does not carry from one store to another."* The precise statement is the engine's own, in the
comment above the sharing refusals in `WorkflowEngine.__init__` (`runtime/ccf_runtime/workflow/engine.py:571-573`):
*"this check sees one Python process; independent shared stores behind one shared queue in different processes are
excluded by deployment configuration, not by this check."*

The register's second clause reads backwards. The defect is that an approval **does** count in another store;
design 1.4 makes it not count.

**Why.**

- The engine compares each verdict's `principal.product_content_hash` with `content_hash(record)` of the suspended
  record (`engine.py` around :1158, :1907 and :2042).
- That record names no store (`runtime/ccf_runtime/workflow/state.py::WorkflowStateRecord`).
- `src/ccf/controlplane/state.py::ConditionalStateStore` declares `scope`, `get_versioned` and `put_if`, and no
  identity.

So two independent stores that suspend the same execution at the same clock readings write byte-identical
suspensions, and one approval counts in both.

**Measured on `3f914416`** with test stand-ins that declare `scope = "shared"` (the SDK ships no shared store), in
one OS process, on deterministic test clocks:

| Shape | Result |
|---|---|
| Two independent shared stores behind one shared queue, one approval, both resumed | hashes identical; the step after the gate ran **2** times; 1 submission, 1 closure (`probes/code-reader/probe_residual_shapes.out`; re-run byte-identical) |
| B3a: store S1 approved but never resumed; a replacement S2 resumed | S2 **completed on S1's verdict**: 1 passage in the wrong store, 1 closure (`probes/run-B/probe_B.log:34`) |
| B3c, the control for B3a: S2's suspension one clock tick different | **0** passages; S2 refused "no approval for this suspension" (`probe_B.log:37`) |
| B3b: store replaced after S1 resumed, beside a surviving shared queue | **2** attributed passages on 1 approval, 1 closure (`probe_B.log:36`) |

**What it takes to reach the residual:** a deployment's own shared stores, and byte-identical suspensions. With real
wall clocks a collision is improbable, but it has not been measured. That bears on how the severity is worded, not on
the fix. The register is not relabeled; the item closes by mechanism.

**The bank's door builds no approval surface.** Measured at door open on `3f914416`, with no question served
(`probes/run-C-bank.out`, positive-controlled). The path is `launch.sh` → cp-06C `run.py --door` → `open_product`.

- **It constructs none of these:** a `WorkflowEngine`, an `InMemoryHitlTransport`, an `ApprovalGate`, an approval
  sink.
- **Its one `InMemoryStateStore`** is the registry default.
- **On the delivered `01fc424d`,** the same holds by code reading.
- **Item 1's bank column** (*"one engine, store and approval queue per instance"*) overstates the setup. It is
  corrected at closure (§1.7).

**Already in place, and kept:**

- the D-IMPL-378 gate closure and conditional write;
- the in-process sharing refusals of `b7ce351e`: `_TRANSPORT_STORES` and its binding check (`engine.py:180-212`),
  and the refusals in `WorkflowEngine.__init__`, pinned by `tests/workflow/test_engine_refuses_unsupported_sharing.py`.

### 1.2 The change

The design is DESIGN-2b §6, built as the October rulings shaped it. Item (f) is the new element that ruling 2(a)
adds.

**(a) The identity seam** (`src/ccf/controlplane/state.py`):

- **`ConditionalStateStore.identity`**, a new read-only Protocol member. Its docstring states the contract (DESIGN-2b
  §6.1):
  - 256 bits from a CSPRNG, written as 64 lowercase hex characters, minted once per substrate;
  - never configured, and never derived from a hostname, path or any value an operator types;
  - persisted with the records;
  - the same for every client object, in every process and across restarts;
  - different for an independent substrate;
  - minted per construction by a store whose records do not survive a restart.
- **The copy rule is a MUST** (10:54). A durable store records where its substrate lives, beside the identity (for a
  file or directory: device and inode). It refuses to open anywhere else until an operator deliberately re-mints,
  which voids in-flight approvals.
- **New:** `STATE_STORE_IDENTITY_PATTERN`; `StateStoreIdentityMissing` (a `TypeError`); and
  `state_store_identity_of(store) -> str`, the shape check. It checks the shape only. Uniqueness and persistence are
  what the conformance suite checks.
- **`InMemoryStateStore.__init__`** mints `secrets.token_hex(32)`, and the new `InMemoryStateStore.identity` returns
  it.

**(b) The record** (`runtime/ccf_runtime/workflow/state.py`):

- **`WorkflowStateRecord.state_store_identity: str | None`** is hash-transparent at `None` (the `started_by`
  pattern). A record written before the change keeps its content address.
- **`suspension_left_by`** copies the field. Without that, the D2 finisher's closure lookup misses and fails closed
  as "unclaimed". `ErasureDoor` reaches closures through `suspension_left_by` (`runtime/ccf_runtime/erasure/door.py`).

**(c) The engine** (`runtime/ccf_runtime/workflow/engine.py`):

- **`WorkflowEngine.__init__`** runs `state_store_identity_of(store)` before the existing `isinstance` check. A
  missing or malformed identity becomes a `WorkflowWiringError` that names the identity rule, not the generic
  "is not a ConditionalStateStore". This is "Unsupported implementations refuse construction".
- **`WorkflowEngine._record`** stamps `state_store_identity` on every record it writes.
- **`WorkflowEngine._resume_claimed`,** right after the existing foreign-type check and before any status branch:
  - A record whose identity is another store's is refused by name: `WorkflowResumeRefused`, audited
    `resolved=False`, with the text *"written by a Control Plane state store other than this engine's"*.
  - A **`suspended`** record with no identity is refused by name, and the refusal names the migration.
  - Legacy records in other statuses keep today's handling (DESIGN-2b §6.3). That status-by-status handling was not
    prototyped; it is tested here for the first time.
  - `_recorded_gate_verdicts` is not narrowed (`D-IMPL-366` H2).
- **`WorkflowEngine._finish_start`** finishes only a start record whose identity is this store's, or `None`
  (DESIGN-2b §6.3). A start record that another store wrote is left unfinished, and `execute` refuses it as it does
  today ("already exists"). **`_remainder`** is unchanged.
- **`WorkflowEngine.rebind_legacy_suspension(authorized, workflow, *, execution_id)`** (new). It re-suspends one
  legacy `suspended` record under this store's identity through `_suspend`: a fenced write, the trace, and one new
  event under the **same event key**, audited `workflow_suspended`.
  - The old verdicts name the old hash and authorize nothing, so a fresh approval is required (ruling 1(a); decision
    8 (a): *"never manufacture approval"*).
  - **New against DESIGN-2b §6.5:** the rebind also retires the legacy request still pending under that key, through
    the transport's atomic `remove`, before it enqueues the rebound one, and audits the retirement.
  - **Why:** `ApprovalGate.resolve` takes the first pending event with the key (`src/ccf/hitl/approval_gate.py:340-346`).
    A legacy request left in front was measured to make the fresh approval fail with `GateResolutionRefused` (T-07-39)
    until someone acted on the stale one (`verify-brief/proto/out/e5_legacy_event_blocks_fresh_approval.out`). That is
    Grok question 3.

**(d) Nothing new on queued requests.** `PendingHitlEvent` and `GateClosure` gain no field (10:54: *"Do not show the
store id on queued requests"*). The identity travels inside `product_content_hash`, which every event, submission,
closure and passage name already carries.

**(e) The duplicate-request fix** (ruling 4(a)):

- **The defect.** A slow suspension, or a recovery overlapping another recovery, can file the same approval request
  twice. The gate still opens once. This is pinned as a residual at
  `tests/workflow/test_restore_missing_approval_request.py:543`, in both overlap shapes.
- **The new contract of `HITLTransportProtocol.enqueue`:**
  - **Absent means no pending event** with the same `(tenant, event_key, product_content_hash)`. An outstanding
    claim does not count.
  - An enqueue that appends still discards the `(tenant, event_key)` claim, as it does today.
  - The check and the append are one atomic step.
  - Because the key is the paused run's fingerprint, it already carries the store identity, so nothing is shown.
- **Why "absent" is defined that way.** Measured by emulation: this reading turns only the two `:543`
  parametrizations red, which is intended (`tests/workflow`, `tests/hitl` and `tests/conformance`: 827 passed;
  `tests/http_api` plus `tests/mcp`: 1,058 passed). A reading that also counted claims broke 6 tests, including the
  primitives' give-back (`approval_gate.py:431`) and `tests/workflow/test_sec006_engine_controls.py:417`.
- **The implementation.** `InMemoryHitlTransport.enqueue` makes the check under its existing lock, and
  `WorkflowEngine._restore_request` relies on the contract.
- **This supersedes DESIGN-2b §6.4 ("HITLTransportProtocol — no change"):** a third-party transport must now make
  `enqueue` atomic on that key.
- **The `:543` pin** is rewritten to assert one request, as its header (`:534-539`) requires; it is never deleted.
  `:597` (two transports over one store) stays a disclosed limit.

**(f) The single-process lease** (ruling 2(a)). It uses the graph store's SEC-013 lease types, unchanged:
`src/ccf/graph/protocols.py::WriterLease`, `ProcessScopedWriterLease` and `WriterLeaseHeld`, and
`src/ccf/graph/leases.py::LockFileWriterLease`.

- **What `LockFileWriterLease` is:** an exclusive, non-blocking `flock`. It is refused to a second open file
  description, in another process or in this one (`leases.py:329-331`; measured, E1a), and the kernel drops it when
  the holder dies.
- **The lease is taken at open, by the implementation.** That way a second process can neither submit a verdict nor
  read in-flight state, which Dave's 11:28 criterion A requires; a lease taken only at engine construction would let
  a door-only process through. Both Protocol docstrings gain a MUST: a path-backed implementation declaring
  `scope = "process"` holds an exclusive SEC-013 lease on its substrate from open to close.
  - It refuses to open while another holder has the lease, raising `WriterLeaseHeld`, which names the lock and the
    rule.
  - The lock lives **inside the substrate's directory**, so it moves with the data. A file substrate may instead key
    it on device and inode in a declared directory, as the graph's SQLite store does
    (`src/ccf/graph/backends/sqlite.py`, the declared-directory lease, `lock_directory_writer_lease`).
  - It releases the lease on close, and on object death (`weakref.finalize`). `LockFileWriterLease` never releases
    itself: a dropped lease was measured to stay held after `gc` (E1b).
- **It is not a Protocol member.** It follows the `bind_approver_eligibility` pattern
  (`src/ccf/hitl/transport.py:1013`: *"The method is not a member of this Protocol"*). Both Protocols are
  runtime-checkable; as a member it would refuse every third-party `"shared"` implementation without it, with the
  generic message, and it would break a pinned eligibility test (both measured, E4).
  - For a store or queue declaring `"process"`, `WorkflowEngine.__init__` requires a callable `writer_lease`; one
    without it is refused by name.
  - That check comes after the existing eligibility check (`engine.py:590-600`) and before any binding, so a refused
    construction still binds nothing.
  - `InMemoryStateStore.writer_lease()` and `InMemoryHitlTransport.writer_lease()` return `ProcessScopedWriterLease`.
    This is exact, because no other process can reach their memory.
- **`"shared"` stores and queues take no lease.** They are multi-process by declaration, which is the supported mode
  (`public/how-to/security-and-deployment.md` §4.13, `:2461`). Design 1.4's identity makes them safe.
- **The shipped `--local` composition** (`runtime/ccf_runtime/cli/local.py::build_local_dependencies`) builds an
  in-memory store and queue and a `FileArtifactStore` at `root/artifacts`. Two `--local` processes on one root keep
  separate approval state in memory and share only the artifact store; Part 2 makes that store safe. It is not
  locked by this change, and the record says so.

### 1.3 The acceptance criteria, as ruled

**A: a second process on a single-process store is refused** (ruling 2(a), with Dave's 11:28 wording). The SDK
ships no path-backed approval store, so A is proved on a **path-backed test stand-in pair**, in real OS processes.

- **The pair:**
  - a `"process"` `ConditionalStateStore` at `P/state/`;
  - a `"process"` HITL transport at `P/queue/`. It implements the whole Protocol plus `bind_approver_eligibility`,
    with durable submissions and closures, and `close_gate` atomic with `submit`.
  - Each holds its own lock inside its own directory, so process 1's store and queue do not refuse each other.
- **The test:**
  1. Process 1 opens the pair at P, builds an engine, suspends a run and records a verdict.
  2. While process 1 lives, process 2's attempt to open the store or the queue at P raises `WriterLeaseHeld`, which
     names the lock, before any record is read. So process 2 can neither submit a verdict nor read process 1's
     in-flight state. The refusal is recorded as a log record in the refused process (Grok question 1).
  3. After process 1 exits cleanly, a new process opens P, builds an engine and resumes the suspended run. The
     verdict is visible, because both halves are durable.
- **An in-process control:** process 1 admits its own store-and-queue pair. Dropping both objects and collecting
  them frees P, so new objects at P are admitted; a second *live* object at P stays refused.
- **The SDK's in-memory store and queue** return the disclosure lease, and the record says no other process can
  reach them.

**B: an approval counts only in the store that paused the run** (ruling 1(a); replaces B as first written):

- **B1.** Two independent shared stand-in stores behind one shared queue, the same execution id, and one approval on
  A's event. Both resume.
  - A passes.
  - B is refused *"no approval for this suspension has returned through the HITL authority path"*. That is asserted
    positively, as the cause.
  - The step after the gate ran once, and one attributed `workflow_resumed` row and one closure name A's suspension.
- **B2 (the B3a shape).** A is approved and never resumed, and a replacement store B resumes: B is refused.
- **B3 (the B3b shape).** A store is replaced after A resumed, beside a surviving queue: at most one passage on one
  approval.
- **B4.** The same durable pair, reopened after a clean shutdown by another OS process, keeps its identity and its
  verdicts in force, and the run resumes.
- **B5.** A suspended record that another store wrote, placed in this store, is refused by name.
- **B6.** A pre-upgrade `suspended` record with no identity and a recorded approval:
  1. Its resume is refused by name, and the refusal names the migration.
  2. `rebind_legacy_suspension` re-pauses it under the same event key, with an audited `workflow_suspended` row.
  3. The old verdict authorizes nothing.
  4. One fresh approval releases exactly one passage.
- **B7.** A pre-upgrade `suspended` record whose request is still pending, with no approval. After the rebind, a
  fresh approval through the real `ApprovalGate` succeeds, and the legacy request's retirement is audited.

**C: the one-instance cycle is unchanged** (ruling 3(a)). One process, one store and one queue run ask → suspend →
verdict → resume.

- **The probe is extended first.** It is `probes/measure/deploy.py`, outside the repository. It now threads the
  verdict's HITL block into the replay record's dimension 2, so the replay of an approval-related decision is
  compared. On `3f914416` that dimension read `no-hitl-actions`.
- **The baseline is re-taken** after Part 2's commits and before Part 1's code. Part 2 adds `.artifact-names.lock`
  to the artifact root, which the probe lists, and that file is not a 3(a) fingerprint.
- **Compared exactly:** every field of every audit row, every refusal (none new), every verdict, every closure, the
  artifact-root listing and the replay record, except for the masked values.
- **Masked:** the store identity, and the values built from it. That is the suspension hash wherever it appears:
  - the event's `product_content_hash`;
  - the submission's `principal.product_content_hash`;
  - the closure's `product_content_hash`;
  - the `hitl_action` audit row's `version`;
  - both occurrences inside the verdict's serialized `hitl_actions_block`, which is parsed to mask them.

  It is also the closure's passage name and the state record's hash. The wall-clock `occurred_at` on the
  composition audit rows is masked, as it already was.
- **Agreement inside the run:** all of the suspension-hash occurrences above are equal, and the closure's passage
  recomputed from the suspension hash, the authority and the action equals the recorded one. A perturbed closure
  must be detected.

C is a guard: it cannot fail before the change. The bank's path has no approval cycle to compare, so its claim rests
on `run-C-bank.out`, re-run on the fix.

**D: negative cases:**

- **D1.** Two processes on distinct paths both succeed. This is a guard.
- **D2.** A holder killed with SIGKILL does not leave P locked: the next process opens P. A positive control asserts
  that process 2 is refused while process 1 lives, which is what makes D2 red on `3f914416`, where nothing refuses.

### 1.4 Red-first tests

**Every red must fail on an assertion,** never on `AttributeError`, `NameError` or a validation error. New members
are probed with `getattr`, and B6's first assertion is the refusal, made before `rebind_legacy_suspension` is called.

New file **`tests/workflow/test_approval_binds_the_suspending_store.py`**. DESIGN-2b §7's named test is **not**
reused as written: its composition, two `InMemoryStateStore`s over one `InMemoryHitlTransport`, has been refused at
construction since `b7ce351e`, and a construction error is not a red. These tests run over the shared doubles
`SharedStore` and `SharedTransport` (`tests/workflow/test_engine_refuses_unsupported_seams.py:67-76`).

| Test | Red on `3f914416` because |
|---|---|
| B1 | the hashes are identical and the step runs twice |
| B2 (B3a) | B completes on A's verdict |
| B3 (B3b) | 2 passages (the probe's version: `probes/redbefore/test_sec001_residual_acceptance.py`) |
| B5 | the record is identical, so B passes on A's approval |
| B6, B7 | the resume is not refused; the old approval releases it |
| construction, missing **and** malformed identity (63 hex), in `test_engine_refuses_unsupported_seams.py` | construction is admitted. The test asserts the identity-rule text, so the generic `isinstance` message cannot satisfy it |
| identity conformance (`tests/conformance/test_gate_closure_and_conditional_write.py`) | `getattr(store, "identity", None)` is `None`. Cases: two clients share one identity; independent substrates differ; a reopened durable stand-in keeps it; the shape is right; a copied durable stand-in refuses to open (the MUST) |
| 2 (c), engine level: exactly one request, in both `:543` overlap shapes | two identical requests are filed (prototyped: 2 failed, 5 of 5) |
| 2 (c), transport level, in `tests/hitl` or `tests/conformance`: two threads enqueue one identical event, with a `threading.Barrier(timeout)` on the pending read between the check and the append | two identical requests are queued (prototyped: FAIL 5 of 5) |
| A, D2 and the in-process lease control: `tests/workflow/test_approval_store_lease_across_processes.py` | process 2 opens and runs while process 1 holds P |

**Guards that pass on `3f914416`:** C, D1, and B4's resume after a reopen. B4's identity assertion is new.

### 1.5 Severings (each must redden its test, on an assertion)

Each severing is applied as a source edit in a fresh `python -B` process, with `__pycache__` purged. Its anchor must
match exactly once. The original bytes are restored from a saved copy and the sha256 is checked. A severing that
errors, rather than failing an assertion, is invalid and is redone.

- **S1:** every store reports `"0" * 64`. B1, B2, B3 and B5 go red.
- **S2:** `InMemoryStateStore` mints once per class, not per object. B3 goes red.
- **S3:** the foreign-identity comparison in `_resume_claimed` is deleted. B5 goes red.
- **S4:** `suspension_left_by` drops the field. The D2 finisher's pins go red.
- **S5:** the explicit identity check is removed from `__init__`. The construction test goes red on both cases: the
  malformed identity is admitted, and the missing one gets the generic message.
- **S6:** the legacy branch silently adopts a record (Q-2b-1 (c)). B6 goes red.
- **S7:** `rebind_legacy_suspension` keeps the old binding. B6 goes red.
- **S8:** `enqueue`'s absence check moves outside the transport lock. The **transport-level** 2 (c) test goes red;
  prototyped, FAIL 5 of 5. The engine-level test cannot see this, because its hold point is before the transport's
  code runs (`test_restore_missing_approval_request.py:209-221`).
- **S9:** the stand-in's lease is skipped at open. A and D2 go red.
- **S10:** the stand-in's copy detection is disabled. The copy-MUST conformance case goes red.
- **S11:** the rebind leaves the legacy request pending. B7 goes red (`GateResolutionRefused`).
- **S12:** the lease registry's `weakref.finalize` is removed. The in-process lease control goes red.

### 1.6 Must not change

- **The main SEC-001 fix and the D-IMPL-378 closure.** Every `b7ce351e` refusal stays.
- **These pins stay green:**
  - `tests/workflow/test_engine_refuses_unsupported_sharing.py` (all 6);
  - `tests/workflow/test_approval_gate_limits.py:504`;
  - `tests/http_api/test_approval_gate_limits_door.py:297`;
  - `tests/workflow/test_sec006_engine_controls.py`, at `:389` and `:417` (a missing-state submission is not
    authority) and `:449` (a missing-state verdict still counts as a conflict; not narrowed, `D-IMPL-366` H2);
  - `tests/workflow/test_conflict_population_eligibility.py:186-196`. It is unaffected, because `writer_lease` is not
    a Protocol member and its check comes after the eligibility check.
- **One fixture changes:** `tests/workflow/test_approval_gate_limits.py::SharedBackingStore`, so that all clients of
  one backing return one identity (DESIGN-2b §10).
  - That figure was measured at `a539c215`. Since then, 33 commits (5 of them merges) have touched `tests/workflow`,
    `tests/http_api`, `tests/hitl` and `tests/conformance`, and 75 have touched all the trees DESIGN-2b measured.
  - So the blast radius is re-measured before the build and reported.
- **Untouched:**
  - follow-ups 7–9 (door entitlement and on-behalf-of identity), which stay deferred under the 2026-10-12 22:44 MST
    ruling (`docs/DECISIONS.md:4924`). "Identity" there is a different thing;
  - every door, product and replay surface outside the approval path;
  - `FileArtifactStore`, except for Part 2;
  - the sealed delivery `01fc424d`, and `BANK-PACKET.md` and `RELEASE-NOTES.md`, which describe it.
- **One served-surface change, already disclosed by the design** (DESIGN-2b §8): the identity is served on
  `GET /workflow/execution`, because the served record must keep hashing to the event's `product_content_hash`. It
  tells a `WorkflowStatusRead` holder whether two executions share a store; it is not a credential. The committed
  `openapi.json` is regenerated.

### 1.7 Records at closure

- **`D-IMPL-391`** and **item 1 of `OPEN-SECURITY-ITEMS.md`**, in ruling 5(a)'s words: *"Closed for every store that
  meets the identity rules, checked by tests. A copied store must refuse to open. Does not reach the bank’s setup,
  which builds no approval queue."* Item 1's bank column is corrected to match.
- **`public/how-to/security-and-deployment.md` §4.13** gains:
  - the bullet DESIGN-2b §6.7 specifies;
  - the single-process lease MUST;
  - the enqueue contract;
  - the rebind's retirement of a legacy request.

  Today that section states the multi-process mode (`:2461`) without the residual.
- **`public/reference/controls-register.md`** gains three rows: "the suspension names its store", "a store without a
  stable identity is refused", and "a second process on a single-process store is refused".
- **A surface fragment** whose name starts with a digit. Then regenerate `docs/SURFACE-CHANGES.md` (with
  `tools/assemble_surface_changes.py`), `openapi.json` and `docs/surface/v0.2-surface.json`.

### 1.8 Limits that stay disclosed

- **Copies a store cannot detect.** A store that cannot detect a copy (a network service, a VM snapshot) cannot meet
  the MUST, and so does not conform.
- **Shape, not uniqueness.** The engine checks the identity's shape, never its uniqueness or persistence. The
  conformance suite is the bar a deployment runs against its own store.
- **The lease's limits.**
  - It carries SEC-013's `flock` limits: one host, and a local filesystem with real `flock` semantics.
  - The engine checks that a single-process implementation offers a lease, not that it takes one at open. That
    obligation is the MUST, proved by the conformance tests.
- **Two independent stores that suspend the same execution id** put two events under one key, and each needs its own
  approval.
- **In-memory state is still lost at a restart.** This change makes the loss safe; it does not make it durable.
- **Design 1.5** (audit-row recovery, register item 10) was labeled part of SEC-001's audit by the October 9 panel. It
  depends on 1.4 and stays open.

---

## Part 2 — The evidence name-index race (`D-IMPL-390`, register item 18)

### 2.1 The defect, measured

`src/ccf/artifacts/file_store.py::FileArtifactStore.put` calls `_register_name` on every write.

- `_register_name` reads `.artifact-names.json`, appends the address under its name, and calls `_write_index`.
- `_write_index` replaces the whole file through a staging file named only by process id (`:261-267`).
- Nothing makes that sequence exclusive, across processes or between threads of one process.
- The artifact file's own staging name (`put`, `:395`) is also per process, so two threads putting the **same**
  artifact share it. `_write_private` opens without `O_EXCL` (`:182`).
- The file is unchanged since the delivered `01fc424d`.

**Measured on `3f914416`:**

- **By chance, two processes** (`probes/measure/probe_A.py::a3_concurrent_writers`): 40 workflow cycles each into
  one store root, after which every one of 80 names should hold 2 versions. In 2 of 4 runs, two names each lost a
  version (`run-A3-3`: `pa-3`, `pb-7`; `run-A3-4`: `pb-16`, `pb-7`). Both distinct artifact files were present; the
  loss was in the index.
- **Forced interleaving** (`verify-brief/proto/race_tests.py`, the unmodified tree):

| Shape | Result on the unmodified tree |
|---|---|
| Two threads, distinct names | a name lost in 10 of 10 runs; in 8 of 10 one `put` also raised `FileNotFoundError` on the shared index staging file |
| Two OS processes, distinct names | a name lost in 8 of 8 runs |
| Two threads, the same artifact | one `put` raised `FileNotFoundError` in 10 of 10 runs |

**Reach:** the bank's door builds one `FileArtifactStore` for its replay evidence (`probes/run-C-bank.out`). Whether
that door ever writes concurrently was not measured. Two `--local` processes on one root share one.

### 2.2 The change

**The SDK's own precedent:** `src/ccf/erasure/index.py::FileErasureIndex` already makes its read-check-append
exclusive across processes, with `fcntl.flock(LOCK_EX)` (`:427-433`).

- **The index update becomes exclusive.** `_register_name` opens a lock file in the store root
  (`.artifact-names.lock`; `O_RDWR | O_CREAT | O_NOFOLLOW | O_CLOEXEC`). It sets the mode with `os.fchmod(fd, 0o600)`,
  as `_write_private` does (SEC-014: a mode requested through `os.open` alone comes out wrong under a restrictive
  umask). It then takes a blocking `flock(LOCK_EX)` for the read, the append and the replace, and closes the
  descriptor in `finally`.
- **One mechanism for processes and threads.** The descriptor is opened per acquisition, so the one `flock` excludes
  other processes and other threads of this process. Measured on this host (ext4, E1a): two threads, each with its
  own descriptor, never overlapped in 5 of 5 runs, and the control that shared one descriptor overlapped in 5 of 5.
  No `threading.Lock` is added: it would be redundant, and no test could redden it on its own.
- **The artifact file's staging name becomes unique per writer** (`:395`), as
  `src/ccf/replay/evidence.py::_durable_write` already does with `uuid4`.
  - This goes beyond the literal instruction ("around the name-index update"). It is the same defect class in the
    same store, with its own test.
  - The index's staging name stays as it is: under the lock it is safe, and no test could redden a change to it.
- **Unchanged:**
  - the index's format and bytes;
  - content addressing;
  - the append-only rule;
  - readers (`_read_index` still reads a whole file, because the replace is atomic);
  - the store's other file modes.

**Prototyped outside the repository** (`verify-brief/proto/file_store_fixed.py`, `fix.diff`):

- all three shapes pass in 10 of 10 runs, with no hang;
- `tests/artifacts`: 59 passed, both with and without the fix;
- `tests/replay` plus `tests/erasure`: 481 passed and 1 skipped, both ways;
- leaving out the `fchmod` reddens the existing
  `tests/artifacts/test_file_store_modes.py::test_modes_are_exact_under_a_umask_that_strips_owner_bits`.

### 2.3 Red-first tests: `tests/artifacts/test_file_store_concurrent_writers.py`

**The gating tests force the interleaving.** A rendezvous sits between the index read and its write: a
`threading.Barrier` with a timeout in-process, and a file-based barrier across processes.

- **Without the lock,** both writers read the same index, and one entry is lost every time.
- **With the lock,** the second writer cannot reach its read. The barrier times out, the first writer proceeds, and
  nothing is lost.
- **How the tests are written:**
  - each test asserts both that no writer raised and that every name holds its version;
  - the wrapper catches `BrokenBarrierError`, which both writers receive on the green path;
  - threads are daemon threads, with join timeouts, so a lock regression cannot hang the suite.

| Test | Red on `3f914416` (prototyped) |
|---|---|
| two threads, one store object, distinct names | a name lost, and usually a raised `put` too: 10 of 10 |
| two OS processes, one root, distinct names | a name lost: 8 of 8 |
| two threads, the same artifact, rendezvous after staging | a `put` raised `FileNotFoundError`: 10 of 10 |

**Supplementary, not a gate:** the by-chance two-process shape, made estate-free, at volume, reported as a count.

### 2.4 Severings (prototyped, 5 runs each)

- **S-I1:** remove the `flock`. Both index tests go red, and the same-artifact test stays green.
- **S-I2:** take the lock after the read. Both index tests go red.
- **S-I3:** restore per-process artifact staging names. The same-artifact test goes red, and the index tests stay
  green.

### 2.5 Questions on Part 2

- **I-1, waiting.**
  - (a) [recommended] A blocking `LOCK_EX` with no timeout, as `FileErasureIndex` does. The hold is one small read
    and write, and the kernel releases the lock if the holder dies.
  - (b) A bounded wait that raises a named error.
- **I-2, filesystems without real `flock`.**
  - (a) [recommended] Disclose the limit in the store's docstring, as SEC-013 does.
  - (b) Refuse to open on a filesystem the SDK does not trust (`src/ccf/graph/leases.py` keeps that list). That
    could break an existing evidence folder on a network mount.

---

## Part 3 — Sequencing and verification

**Order:**

1. Part 2 is small and touches only `src/ccf/artifacts/file_store.py` and its tests, so its commits land first.
2. C's baseline is then re-taken.
3. Then design 1.4, on its own (ruling 6), with (e) and (f) inside it.
4. The two parts share only the records files: `docs/DECISIONS.md` and `OPEN-SECURITY-ITEMS.md`.

**Per part:**

1. red tests committed first;
2. then the fix;
3. then the severings;
4. then regression on every tree that reaches the change:
   - `tests/workflow`, `tests/hitl`, `tests/conformance`, `tests/http_api`, `tests/controlplane` and
     `tests/erasure`;
   - `tests/cli`, `tests/skills`, `tests/invariants/test_state_seam_closure.py` and
     `tests/crossproc/test_hitl_mcp.py`;
   - `tests/artifacts`, `tests/replay`, `tests/products`, `tests/examples` and `tests/mcp`;
5. then the gates: `tools/lints/tests`, `tools/docs_tests`, `tools.lints --all`, `mypy` and the surface gates.

**How every run is made:**

- `PYTHONPATH` is pinned to the worktree, for the test process and every subprocess;
- estate variables are stripped;
- the examples run against the local Fluree, and the `.76` estate stays read-only;
- for Part 2, the cp-06C door tests are also re-run through the bank's own `launch.sh`.

**Not done:** merge, wheel, tag, upload or paid CI. The sealed delivery does not change until both fixes are ready
for a wheel (Dave, 13:13).

### Questions for Grok

1. **"Recorded."** Dave's 11:28 criterion A asks for "a named, recorded error". This brief reads "recorded" as: the
   refusal is a named exception raised at open, and it is logged by the refused process. It is not an audit row,
   because a refused process must not write into the stores it was refused, and a non-blocking `flock` never tells
   the holder that someone tried. Is that reading acceptable, or does Dave need to rule?
2. **(f), the lease's placement and scope.** The lease is taken at open by the implementation, is required (as a
   method) of `"process"` implementations only, and covers both the state store and the queue. The ruling's words are
   "Stores labeled single-process". Is extending the lease to the queue right?
3. **(c), retiring the legacy request.** The rebind retires a legacy request still pending under the key. This
   departs from DESIGN-2b §6.5, where it stays listed until an operator removes it. The alternative is to disclose the
   operator step and leave the request.
4. **(e), the contract change.** `enqueue` becomes enqueue-if-absent, on pending events only, superseding DESIGN-2b
   §6.4.
5. **Part 2:** I-1 and I-2 above.
