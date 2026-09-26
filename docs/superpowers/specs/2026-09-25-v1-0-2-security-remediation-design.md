# CCF SDK v1.0.2 — Security Remediation Design: the remaining HIGH findings

- **Date:** 2026-09-25
- **Status:** **ACCEPTED by Dave, 2026-09-25 18:06 MST, at `cb319661`**, recorded
  as `D-IMPL-356`. The reviewed sub-rulings A1–G10 are **locked** (§0.1); the
  wave-1 opening sheet is the next deliverable; no wave-2/3 implementation, no
  release or tag work, no new reconnaissance until it is presented.
- **Authority:** the security review of 2026-09-23
  (`/home/parkave/ccf_security_review_2026-09-23.md`, deliberately outside the
  repository); Dave's eight rulings and two locks of 2026-09-25 (§0);
  `D-IMPL-350` (Tier 0), `D-IMPL-351` (`archive/` and the standing
  "nothing has shipped" rule), `D-IMPL-352` (a panel per wave), `D-GATE-353`
  and `D-IMPL-354` (the capability seam), `D-IMPL-355` (the v1.0.1 release
  record).
- **Base:** `main` @ `a5b0f691` (v1.0.1 = `a4cf2fb7`, tree `b345b174`). Every
  `file:line` in this document was read on that tree. The review's own line
  numbers predate `D-IMPL-353` and are not reused.
- **Method:** on 2026-09-25, 32 read-only agents re-verified each open finding
  against `a5b0f691`: ten investigators, twenty adversarial refuters (a
  status-and-citations lens and a design-feasibility lens per finding), a
  synthesis and a completeness critic. Every status claim was attacked, every
  citation resolved by reading the line, and every retraction verified as hard
  as a finding (`D-IMPL-352`, rule 3). Where a refuter corrected an
  investigation with line-verified evidence, the correction is what this
  document says.

---

## 0. Rulings that shape this document (Dave, 2026-09-25)

| # | Question | Ruling |
|---|---|---|
| 1 | Scope | **(b)** the seven numbered HIGHs (`SEC-005`…`SEC-011`) plus the `SEC-001` residual plus the subject-shape root cause of `EX-01`. Adapters `TP-01`…`TP-05` are **not** 1.0.2 code: ledgered as **HIGH** with a decision entry in 1.0.2, implemented as the first 1.0.3 wave, after HITL. *"Do not ship 1.0.2 pretending a 'read-only' binding that dispatches every skill is Medium."* |
| 2 | Erasure (`SEC-009`) | **(a)** decision entry only. No substrate, no code. *"Panel the architecture before anyone touches L3."* |
| 3 | Time-bound posture | **(b)** no tenant window → refuse. No SDK default in `src/` (No-Hardcoding). One repair sitting after wave 2, `s1-01` style, **living reference trees only**. Frozen doors stay gap-ledger rows, not edits. |
| 4 | Compatibility | **Yes, past v1.0.1.** Workflow definition schema lane goes to `2.0.0`. The old signed-binding type is replaced, not deprecated in place. New replay fields are hash-transparent so pre-1.0.2 addresses still rehydrate. History is not rewritten. |
| 5 | Release mechanics | **(a)** single-source the runtime stamp from the tag (or a gate that fails when they differ). Tag text carries the security-review map. PyPI `ccf-sdk`: check whether the name is claimed before wave 1 closes; do not block the design on it. |
| 6 | Panel roster | **Confirmed:** per wave, **codex + cursor + gemini**. Fable is the executing model and is excluded (`D-GATE-21`). |
| 7 | Estate-gated examples | **(a)** read-only against `.76` at each wave close and at qualification. Ledger reds by node id. *"Census posture alone hid G-07 once already."* |
| 8 | Quorum | **(a)** single eligible approver, no self-approval, in 1.0.2. N-of-M is a claim-and-consume amendment; 1.0.3. |
| L1 | Lock | The `SEC-029` version stamp is **wave 1**, or ships in the same release as the clock (wave 2). Not "later". |
| L2 | Lock | The eight doors that `D-IMPL-353` left crashing at construction are **ledgered, not unfrozen**, in these waves. |

### 0.1 Acceptance and the locked rulings (Dave, 2026-09-25 18:06 MST; `D-IMPL-356`)

The architecture, the wave structure, the compatibility posture and the
reviewed sub-rulings A1–A5, B1–B5, C1–C6 with C1a, D1–D13, E1–E8, F1–F7 and
G1–G10 are accepted as each carries its recommendation below. **They are
locked now and are not reopened at each wave**; a wave's entry records them,
and one is reopened only when implementation produces evidence that directly
contradicts the accepted design. Dave named these in particular: `SEC-008`'s
write half is option (d) — the single writer refuses an envelope outside the
tenant-declared temporal window using the same policy artifact and the
injected fabric clock, never restamps evidence, and replay never ingests a
refused envelope; a populated `served_at` participates in record identity
while the absent sentinel preserves every pre-1.0.2 record unchanged; a
child's remaining validity is judged at the trusted fabric instant; refusal
identity must not depend on an unpinned wall-clock read; requester ≠ approver
unconditionally; trusted HITL keys are pinned by subject through policy; a
submission records the admitting policy version; a missing requester refuses;
signature freshness is directional; single approver only, quorum stays 1.0.3;
the subject floor is the 512-character ASCII allowlist as specified, both quote
characters excluded; a blank identity refuses; the `D-IMPL-347` seam-class
amendment is accepted as written; `SEC-029` version provenance ships in this
release; `D-IMPL-159` remains the named two-leg residual; no SDK default
temporal window; erasure is a decision and design entry with zero
implementation; the panel is codex + cursor + gemini; the estate-gated
examples run read-only at every wave close and at final qualification.

**One acceptance condition — the adapter HIGHs** (§7.1, §8.2, §8.4):
`TP-01`…`TP-05` stay a 1.0.3 implementation as designed, and the release
carries this condition verbatim: *"A TP-01…TP-05 finding may be deferred to
1.0.3, but an enabled path known to violate its security contract must not be
represented as a supported-safe 1.0.2 path merely because remediation is
deferred."* For each TP finding the 1.0.2 release record states exactly one of:
**supported and not affected by the finding**; **restricted or disabled from
the supported surface**; **known limitation explicitly outside the supported
1.0.2 contract**. This authorizes no adapter implementation in 1.0.2 and
creates no fourth code wave.

**Compatibility, restated as accepted:** insecure behavior is not preserved for
compatibility; historical replay bytes and addresses are never rewritten;
workflow-schema versioning (the `2.0.0` lane, declarative — the generation
boundary is `gate_routes`) and SDK release versioning are separate; `v1.0.2`
remains the working release name under the standing "nothing has shipped"
ruling, not to be reopened unless actual external distribution or dependency
evidence appears.

---

## 1. Scope

### 1.1 What v1.0.2 closes

Three build waves, one decision-only wave, one release:

| Wave | Findings | Character | Effort (D-IMPL-353 = XL, SEC-003 = S) |
|---|---|---|---|
| **1 — Declared, not assumed** | `SEC-001` residual · `SEC-007` · subject shape (`EX-01`/`EX-02` root cause) · `SEC-029` version stamp | a typed refusal by name at one mechanism site, interpreted from an artifact; clock-free; no replay-record shape change | M + S + M + S |
| **2 — The fabric clock** | `SEC-008` · `SEC-010` · `SEC-011` (Gate 3; Gate 2 recorded NOT-A-GAP) · `D-IMPL-159` bounded and carried · `SEC-019` rider | one injected clock read once, recorded beside the decision instant; two-sided Gate 3; a declared temporal bound | L |
| **3 — HITL** | `SEC-005` · `SEC-006` (single approver, no self-approval) | a signed claim set compared against the capability and the submission; a typed per-gate approval policy interpreted by mechanism | L |
| **4 — Erasure architecture** | `SEC-009` | decision entry and design document, panelled; **zero code** | design only |
| **Release** | qualification, tag `v1.0.2` | the `D-IMPL-355` form plus the estate-gated run and the version gate | — |

### 1.2 What v1.0.2 does not do, by name

- **No adapter code.** `TP-01`…`TP-05` are rated HIGH in a decision entry (§7.1) and are the first 1.0.3 wave.
- **No erasure code.** `SEC-009` gets its entry and its panel (§6); nothing touches the artifact store, the graph, or the replay engine under it.
- **No quorum, no role-based eligibility.** Single approver, principal-based eligibility, requester ≠ approver (§5.2). N-of-M needs the `D-IMPL-62`/WR-02 claim-and-consume amendment; roles need a version-pinned role source. Both 1.0.3.
- **No example edits.** Frozen specimens (`D-IMPL-261`) that go red under a wave become gap-ledger rows censused from the estate-gated run. The one repair sitting after wave 2 touches living reference trees only (§4.6).
- **No `archive/` fixes** (`D-IMPL-351`). Nine `archive/` callers of `run_gates(` go dead under wave 2's required argument; a published tutorial's `sign_principal_binding` run command breaks under wave 3. Both are recorded, neither is repaired there.
- **No stdio composition control.** The "one identity for every caller" transport class (`EX-03`, `EX-04`) is documented on the SDK door page in 1.0.2 and designed with the adapters in 1.0.3 (§7.3).
- **An L2 clock only as a refusal guard** (§4.3 item 8, D6): the single writer may read a clock to refuse an out-of-window envelope, never to stamp; replay never ingests. The paved-road ingestion stamp itself is carved out and named.
- **Mediums not taken:** `SEC-013`, `SEC-014`, `SEC-015`, `SEC-017`, `SEC-020`–`SEC-028`; `SEC-019` and `SEC-029` are taken. Each stays open in the map the tag carries (§8.4).

### 1.3 The roster, verified on `main` @ `a5b0f691`

| Finding | Status | What the tree says |
|---|---|---|
| `SEC-005` signed approvals | OPEN | The signed claim set is still the four `D-IMPL-21` fields (`src/ccf/hitl/principal.py:177-180`). The one shared verifier compares binding to binding only (`src/ccf/hitl/transport.py:321`) and never receives `authorized`. The verdict travels unsigned at both doors (`src/ccf/hitl/transport.py:352`, `:394`; `runtime/ccf_runtime/mcp/hitl_server.py:386`). `D-IMPL-353` narrowed the attacker to a bearer-session holder and blocked door replay only through `action_time` equality, which is also why the signed leg cannot work under a wall clock (`docs/surface-changes/353-06-the-approval-record-is-server-attested.md:488-494`, recorded as an unruled follow-up). |
| `SEC-006` approver eligibility | OPEN | No code reads `PendingHitlEvent.policy_ref`; `HitlPolicy` carries only `signed_binding_required` (`src/ccf/hitl/transport.py:229-230`); the starter principal is recorded nowhere; `InMemoryHitlTransport.submit` (`src/ccf/hitl/transport.py:840-850`) and the four `resolve`s check capability, principal match, hash and signature only; both engine authority joins are first-match `next(...)` (`runtime/ccf_runtime/workflow/engine.py:1037-1054`, `:1141-1152`). |
| `SEC-007` blank identity | OPEN | `src/ccf/assembly/worker.py` is byte-identical to v1.0.0: presence-only guard (`:346-348`), bare `str()` identity construction (`:361-363`), URI mint (`:366`), attribute twin (`:369`). `content_hash({"lei": str(None)}) == content_hash({"lei": "None"})` reproduces. Relationship claims are minted from resolved URIs (`:545-587`), so a null endpoint creates a false edge through the phantom node. No test feeds a null identity value. |
| `SEC-008` caller's clock as observation time | OPEN | `asked_at` is caller-supplied at all three doors with only a naive-offset refusal; the paved road requires `ingestion_timestamp == asked_at` (`src/ccf/signal/envelope.py:112`) and hands the caller's instant to acquisition as "the clock" (`src/ccf/products/product.py:813`); L2 writes `observed_at = ingestion_timestamp` (`src/ccf/assembly/worker.py:495`). `envelope.py` and `worker.py` are byte-identical to v1.0.0; `product.py` was changed by `D-IMPL-353` (three commits, all in v1.0.1), but the acquisition context still hands `request.asked_at` as `instant` (`:813`, formerly `:774`), re-read on `a5b0f691`. |
| `SEC-009` erasure | OPEN | Immutability rule and four-method Protocol intact (`src/ccf/artifacts/protocol.py:19-23`, `:573-641`); no delete/remove/erase verb on any served surface; `D-IMPL-50`/`D-IMPL-44` never built; `docs/DECISIONS.md:4641` already says it "needs its own decision entry before code"; the whitepaper commits against physical deletion (`docs/CCF_Whitepaper_1-2.md:2748`, `:3123`, `:3388`) and is silent on erasure. |
| `SEC-010` one instant, three controls | OPEN | Policy effectivity (`src/ccf/products/constraints.py:574-576`, `:1524-1536`), Gate 3's `now` (`src/ccf/products/resolver.py:2911` → `src/ccf/products/gates.py:1385-1386`), `expires_at` (`src/ccf/products/resolver.py:2681`/`:2795`), `recorded_at` (`:3106` served, `:3363` refusals), the debt scorer (`:2626-2631`), the composite mixing law (`:2704-2707`) and dimension-1 `graph_snapshot_at` (`:2364-2368`) all key off the caller's `asked_at` or a caller-typed decision instant (`:2064-2071`). |
| `SEC-011` gates that cannot fail | PARTIALLY CLOSED | **Gate 2:** ruled and shipped as assembly-path integrity (`D-IMPL-86` element 4 at `docs/DECISIONS.md:300`; `D-IMPL-300` at `:1843`); the failable pre-execution control is the binder at `src/ccf/products/resolver.py:2572`. Residue: `public/concepts/invariants.md:82-84` still advertises the forgery reading. **Gate 3:** OPEN. For `from_decision` classes `now < expires_at <= now + MAX_TTL` reduces to `0 < ttl <= MAX_TTL`, disclosed at `D-IMPL-340` (`:3829`) and never ruled. |
| `SEC-001` residual | OPEN | `WorkflowEngine.resume` reads only `authority.principal` (`runtime/ccf_runtime/workflow/engine.py:540`) and routes the caller's `decision` against the verdict-blind transition set (`:541-542`); `WorkflowDefinition` (`src/ccf/workflow/definitions.py:132-135`) carries nothing verdict-shaped. Pinned by `tests/workflow/test_engine.py:856-895` and the Hypothesis rule at `tests/workflow/test_engine_stateful.py:169-195`. |
| Subject shape | OPEN | `ProductRequest.subject: str` with no validator (`src/ccf/products/request.py:338`); `ArgumentDomain` has two shapes and no `pattern` (`:435-441`); `refuse_request` (`:1920`) never reads `subject`; the docstring at `:281-285` claims a shape validation that does not exist. Reachable splices on `main`: `examples/cp-16-abs-securitization-surveillance/acquisition.py:413` (subject → SPARQL IRI position at `:413`, after a parameter-bound relational read at `:403-410` and before the anchor-existence check at `:414`, so the splice fires whether or not the deal exists) and `examples/cp-04-canonical-corporate-family-tree/acquisition.py:332` (`lei` parameter → literal). `cp-17`'s splice (`EX-01`) sits behind an exact-match bound lookup (`:237-243`), so its practical reachability is lower than the report graded; the SDK-level finding keeps its HIGH. |
| `SEC-029` version stamp | OPEN, recurs | `pyproject.toml:7` `version = "0.1.0"`; `src/ccf/graph/registry.py:474-484` reads `importlib.metadata.version("ccf")` into `AdapterPin.version` (`:345`), which lands in **dimension 2** of every replay record as `graph_adapter_version` (`src/ccf/replay/record.py:663`). Every record written from an installed v1.0.x wheel says `0.1.0`. |
| `TP-01`…`TP-05` adapters | OPEN, unrated in the report | Adapters, `src/ccf/skills/dispatch.py` and `runtime/ccf_runtime/peering/typed_http.py` byte-identical to v1.0.0. `TP-01` reproduced socket-free with the vendor's own `_get_can_use_tool_shadowed_warning`; `TP-04` confirmed against google-adk 2.5.0; `TP-05` confirmed (`--system-prompt` on argv). Rated HIGH by ruling (§0, #1). |

**Closed and not re-chased:** `SEC-001` (Tier 0), `SEC-003`, `SEC-002`, `SEC-004`, `SEC-012`, `SEC-016`, `SEC-018` (Tier 1). `SEC-012`/`016`/`018` were re-verified closed on `main` during this recon (`runtime/ccf_runtime/http_api/routes/skill.py:27`, `:248-249`; `runtime/ccf_runtime/cli/credential.py`; `runtime/ccf_runtime/mcp/experience.py:87-90`).

---

## 2. Standing rules for every wave

These are the project's rules, restated because each has already been paid for once.

1. **Sequence per wave:** the wave's `D-IMPL` entry records the locked rulings (§0.1; reopened only on contradicting implementation evidence) → build in worktrees → red-when-fixed tests rewritten (never deleted) → sabotage on the merged tree (a named severing per guard, each reddening a named test) → the estate-gated example run, read-only against `.76` (§8.3) → the cross-AI panel → every finding and every retraction verified against the tree → blocking findings fixed in-wave → STOP for Dave. A wave is closed by Dave's ruling and a `D-GATE` line, never by execution completing.
2. **The panel is codex + cursor + gemini** (§0, #6), briefed with the known findings and told not to re-derive them, told the SDK is destined for a **bank**, with the source **inlined on stdin** in bundles of at most ~150 KB each (a single argv string caps at 131,072 bytes and all three CLIs then exit 0 having read nothing). Each wave's phase record names its bundles and their exclusions. Wave 1's named ranges measure 53,530 bytes and fit in one bundle; waves 2 and 3 do not and are split (§4.9, §5.3).
3. **"Nothing has shipped" governs** (`D-IMPL-351`, `docs/DECISIONS.md:4647`, restated by Dave past v1.0.1 in §0 #4): a remedy argued down because a change would move a hash, break a fixture or alter a committed expectation is re-argued without that premise. Security defaults are generation boundaries (`HASH_TRANSPARENT_KEY: False`), not hash-transparent silence, **except** where a stated reason makes silence safe, and each such field names its reason at its site: `served_at` (Dave, §0 #4: pre-1.0.2 addresses rehydrate; a populated value is addressed), `pattern`/`subject_domain` (the floor governs silence, §3.3), `attestation` (an unsigned submission is refused wherever signing is required, §5.1), `hitl_policy_ref` (§5.1), `started_by`/`requested_by` (an absent requester is refused at resolution, §5.2). A field marked `True` by silence is a defect.
4. **A guard whose applicability the caller supplies is not a guard** (`D-IMPL-350`, `docs/DECISIONS.md:4617`). Every comparand in this document is taken from what the fabric recorded or what an artifact declares, never from what the caller presents.
5. **Examples are probes, not repair targets** (`D-IMPL-261`). A red example is an SDK finding or a gap-ledger row. The eight doors `D-IMPL-353` left crashing are ledgered in wave 1 (§7.2) and are not unfrozen (§0, L2).
6. **Decision ids are allocated in this document (§10), provisionally.** Every parallel investigation read "next free id `D-IMPL-356`" and claimed it; the planner allocates, the investigations do not.
7. **Read `docs/EXAMPLE-EVALUATION-CRITERIA.md` in full** in any session that touches an example, including the wave-2 repair sitting and every gap-ledger row.
8. **Three states, never two.** Every count that reaches Dave, a commit message or a decision entry names what ran: `passed`, `failed`, `errors` and `skipped` are four numbers; "collected" is none of them.

---

## 3. Wave 1 — Declared, not assumed

Four items, three disjoint modules plus release plumbing, one panel. None reads
a clock; none changes a replay-record shape. The panel brief for the wave is
one sentence: *silence must not mean unconstrained* (`D-IMPL-350`, `D-IMPL-351`).

### 3.1 `SEC-001` residual — the verdict binds the target

**Defect.** A gate-suspended workflow resumes only on a recorded human action
(Tier 0), but the recorded verdict is never compared to the route taken. The
caller's `decision` string is checked against the declared transitions
(`runtime/ccf_runtime/workflow/engine.py:541-542`) and nothing else, so a recorded `reject` still resumes down
the approving branch. `D-IMPL-350` named the limit and its reason: no artifact
declares which target a verdict may take, and deriving one in `src/` would be
the No-Hardcoding defect. The three gate-bearing fixtures prove the point with
three different target vocabularies — `{approved, rejected}`, `{released,
rejected}`, `{accepted, declined}` — so the mapping cannot live in code.

**Design.**

1. **`gate_routes` on `WorkflowDefinition`** (`src/ccf/workflow/definitions.py`):
   `Mapping[str, Mapping[str, str]]`, gate step name → `{verdict → target}`,
   verdict keys drawn from `GATE_ACTIONS` (`src/ccf/hitl/approval_gate.py:114`,
   the SDK's mechanism vocabulary `{approve, reject}`, importable into
   `definitions.py` without a cycle). Default `{}`,
   `json_schema_extra={HASH_TRANSPARENT_KEY: False}`: a **generation boundary**,
   the consequence `D-IMPL-351(a)` records for security fields (a document lacking it is
   an earlier generation; an undeclared gate is REFUSED). Placement on the
   wrapper is the one `D-IMPL-351` item 2 already presupposes (it counts three
   gate-bearing workflow documents for the migration) and is consistent with
   D-11/D-12 (the wrapper "adds ONLY routing"; a `hitl-gate` step carries no
   behavior).
2. **Local validators** (the `src/ccf/workflow/definitions.py:171-290` pattern, beside
   `_bindings_key_declared_nonterminal_nodes` at `:261`): every key names a
   declared non-terminal node; every inner key is in `GATE_ACTIONS`; every inner
   value is a transition target declared from that gate.
3. **Factory semantic check** (`src/ccf/workflow/factory.py:348-359`, the loop
   that already walks `gate_policies` against the resolved task): every
   **routed** `hitl-gate` step (one the wrapper routes to — `src/ccf/workflow/factory.py:338`
   checks wrapper→task only, so the check is scoped the same way) must carry a
   map covering **every** `GATE_ACTIONS` verdict, else `WorkflowConstructionError`.
4. **Engine:** after the existing declared-target check (so
   `tests/http_api/test_routes.py:650`'s "declared transition" reason keeps its
   subject), `resume` refuses through `_refuse` (`runtime/ccf_runtime/workflow/engine.py::WorkflowEngine._refuse`) when
   `decision != gate_routes[gate][authority.action]`. The reason names **neither**
   the verdict nor the expected target. `decision` stays a required double-entry
   in 1.0.2 (A3(a)); removing it is the seam-clean shape and is
   recorded for a later wave because it changes five public surfaces
   (`OrchestrationProtocol`, four drivers, HTTP body/OpenAPI, CLI verb, harness
   tool schema).
5. **Conflicting verdicts refuse.** `InMemoryHitlTransport.submit` appends every
   verified submission (`src/ccf/hitl/transport.py:865`), `submissions()` is oldest-first
   (`:868-871`), the submit-only door (`D-IMPL-62`) leaves the event pending, and
   `_gate_authority` takes `next(...)` (`runtime/ccf_runtime/workflow/engine.py:1037-1054`) — so two officers'
   conflicting verdicts on one suspension route first-writer-wins today, and the
   binding makes that load-bearing. `_gate_authority` refuses (typed, through
   `_refuse`, naming no verdict) when the qualifying submissions for one
   suspension carry more than one distinct `GATE_ACTIONS` verdict — computed
   over eligibility-filtered submissions once wave 3 lands (an ineligible
   principal's verdict never counts), over every capability-qualified
   submission until then. Red test:
   record `reject` then `approve` through `POST /hitl/actions`, resume, assert
   refusal; severing control.
6. **Scope:** the approval-gate branch only. The escalation sibling
   (`runtime/ccf_runtime/workflow/engine.py:1083-1087`: either `ESCALATION_ACTIONS` verdict releases the hold
   and the node retries) is the same class at lower severity, is unpinned at the
   engine level, and is logged as its own row with a pin test (§7.4). The
   no-escalation exception branch (`runtime/ccf_runtime/workflow/engine.py:614-634`, ruled by design) is named
   so it is not mistaken for the sibling.
7. **Lane:** the three migrated documents
   (`tests/fixtures/banking/workflows/covenant_review_workflow.yaml`,
   `payment_release_workflow.yaml`, `perf/synth/artifacts/workflow.yaml`) declare
   `schema_version: "2.0.0"` (§0, #4).
8. **Published pages:** `public/how-to/compose-a-workflow-with-hitl.md:138`
   ("the decision string names the route") gains the agreement clause rather
   than a retraction (the sentence stays literally true under A3(a)).
   `public/reference/artifacts/workflow-definitions.md:18` transcludes
   `archive/examples/05-workflow-hitl/artifacts/workflow-definition.yaml`, which
   now fails the factory: it gets a dated "pre-`gate_routes` shape" note;
   replacing the 102 `--8<--` transclusion directives across 15 public pages (`D-IMPL-351`'s 123 counted every line mentioning `archive/`) is the documentation project `D-IMPL-351`
   scoped separately.

**Rulings inside the wave-1 entry (recommendation marked).**

| # | Question | Options | Recommendation |
|---|---|---|---|
| A1 | Where the map lives | (a) `gate_routes` on `WorkflowDefinition` · (d) a verdict label on the `WorkflowTransition` edge (`src/ccf/workflow/definitions.py:80-89`; the engine permits multi-successor only at a gate, `runtime/ccf_runtime/workflow/engine.py:724-731`, so the label would dissolve the values∈targets cross-check) | **(a)**, with (d) considered on the record |
| A2 | Hash posture and undeclared posture | (a) `False` + factory refuses an undeclared routed gate (the consequence `D-IMPL-351(a)` records) · (b) required field, no default · (c) `True`, silence = unconstrained | **(a)** |
| A3 | Does `decision` remain an input | (a) double-entry, mismatch refused naming neither · (b) removed (own wave, own panel) | **(a)** for 1.0.2; (b) recorded |
| A4 | Conflicting verdicts | refuse on >1 distinct verdict · route only on a gate-stamped leg (a `D-IMPL-62` amendment) | **refuse** |
| A5 | Scope | gate branch only + escalation row · both now · escalation verdict is not routing | **gate branch only** |

**Blast radius, measured.** 12 test/tool/perf modules import `WorkflowEngine`;
37 `.resume(` sites in 6 test files; exactly 2 pin the defect. Every test that
constructs the three fixtures is red at the factory until the YAML migration
lands (fixed by data, not by test edits): `tests/workflow/*`,
`tests/http_api/conftest.py` (hence `test_routes.py:573/606/631` and
`tests/cli/test_cli.py::test_workflow_invoke_status_resume`),
`tests/conformance/test_orchestration.py`, `perf/suites/micro/test_factory.py`.
The archived `05-workflow-hitl` document still parses (`gate_routes` defaults
to `{}`) and is refused only by the factory, which no gate runs over `archive/`
(`tools/check_schema_headers.py:155-156` validates by `model_validate` and stays
green); it is noted under `D-IMPL-351`, not ledgered as a red the instrument
will not observe. `docs/schemas/ccf.workflow-definition.json` is regenerated
(`make schemas`, `Makefile:941`) and `tests/cli/test_schema_export.py:124`/`:130`
are red until then; the `2.0.0` lane is declarative (`schema_version` is
semver-validated only, `src/ccf/workflow/definitions.py:103-109`) — the
generation boundary is `gate_routes` itself. Public surfaces otherwise
byte-stable. Live examples: zero.

**Red when fixed.** `tests/workflow/test_engine.py::test_a_recorded_rejection_cannot_be_routed_down_the_approving_branch` (A3 step 1 renames it from `test_a_rejection_authorizes_resumption_but_does_not_bind_the_target`; the line spans below are the pre-fix file's)
(`:856-895`, incl. `resumed[0].actor == "officer-2"` at `:895` — the refusal
audits `actor=None`); `tests/workflow/test_engine_stateful.py:169-195` (the rule
draws `"rejected"` after an always-approve `_resolve_gate`; rewrite so it draws
the verdict and derives the decision from `gate_routes`). Ordering-sensitive:
`tests/http_api/test_routes.py:650`. Constraints to keep green:
`tests/workflow/test_engine.py:793-823` and `tests/http_api/test_routes.py:606-630` (no enumeration).

**Sabotage.** Remove the route compare → the rewritten pin reddens. Remove the
conflict refusal → its test reddens. Reinstate target enumeration in the new
reason → the non-enumeration tests redden. Move the new check ahead of the
declared-target check → `tests/http_api/test_routes.py:650` reddens.

### 3.2 `SEC-007` — an identity component is admissible or refused, by name

**Defect.** The partial-identity guard tests key presence only
(`src/ccf/assembly/worker.py:346`); the identity is then rendered with bare `str()` (`:361-363`)
and hashed (`:366`). `None` renders as `"None"`, so every null-identity record
mints one phantom node; because relationship claims are minted from resolved
URIs (`:545-587`), real entities gain false parent/guarantor edges through it,
and two null endpoints in one envelope drop silently at the self-loop skip
(`:568`). The same `str()` also **splits** identities (`Decimal('1.5')` vs
`'1.50'`, `1` vs `1.0`). CDC (`runtime/ccf_runtime/cdc/envelope_map.py:258`) and
the federated door (`src/ccf/assembly/worker.py:684-701`, `relabelled[local] = value` at `:701`)
relay nulls verbatim to the same mint.

**Design.**

1. At the single mint site, after the presence check: refuse `None`, an
   empty or whitespace-only string, `bool`, `float` (**named explicitly** —
   `str()` runs before `content_hash`, so canonical's float refusal at
   `src/ccf/contracts/canonical.py:363-364` never sees it), `Mapping`, non-`str`
   `Sequence`, and `bytes`. Raise a public `IdentityRefused(ValueError)`
   (exported in `worker.py`'s `__all__`) naming envelope id, entity class,
   declared key, source field and reason.
2. `int` and `Decimal` are coerced by an explicit positional-string branch (the
   documented form of what `str()` does today), so **every existing URI stays
   byte-identical** (`D-IMPL-316`, `docs/DECISIONS.md:2383`: the global
   content-hash semantics are not retuned). The entry states that this also
   preserves the `'1.5'`/`'1.50'` split; typed hashing is the stricter option
   and is recorded as declined.
3. **The canonical path records the refusal.** `D-IMPL-347` B2 declared seam
   refusals (`src/ccf/products/resolver.py:2331-2341`, `:3197-3216`, matched by exact
   `module.QualName`) are the recording seam. There is no default map to
   declare into: `seam_refusals` is a field of the deployment-authored
   `ProductClassDeclaration` (`src/ccf/controlplane/artifacts.py:1556-1561`,
   default `()`, "nothing converts by default"), zero example declarations
   carry one, and the binder lets a deployment narrow the class's map, never
   widen it (`src/ccf/deployment/binder.py:329-335`). So this **amends
   `D-IMPL-347` B2** for one case and says so: an SDK-owned seam class raised
   by SDK mechanism — `ccf.assembly.worker.IdentityRefused` is the first — is
   converted by mechanism regardless of declaration, because the SDK does know
   what it means (a record whose identity cannot be minted names no entity:
   `RefusalCause` `nonexistent`, `src/ccf/products/contract.py:306`);
   deployment-declared types keep B2's posture. Without that, an undeclared
   `IdentityRefused` reaches the HTTP route as a 500
   (`runtime/ccf_runtime/http_api/routes/product.py:346-353` catches only the
   governed classes) on all 16 paved-road trees. `src/ccf/controlplane/artifacts.py:1556-1561` and
   `src/ccf/deployment/binder.py:329-335` join wave 1's touched files and payload.
4. **Partial admission is stated, not fixed.** The paved road ingests every
   acquired envelope in a loop, one transaction per claim
   (`src/ccf/products/product.py:815-817`; `src/ccf/graph/backends/fluree_write.py:609-610`), so a
   refused envelope leaves its predecessors written for the next request. That
   is an L2 transaction-boundary question and a named residual (§7.4).
5. **Document at the rule** that a `*_ref: True` presence-flag match key (the
   SDK's own idiom; 24 rules across `examples/`, `tests/` and `perf/` YAML —
   9/12/3, `archive/` excluded — declare `match_key ∈ identity_keys`, 0 declare
   a bool) cannot double as an identity key.
6. **Negative control** (none exists today): ingest two null-identity envelopes
   through `AssemblyWorker.ingest`, assert entity count **and** relationships.
   The test seam is in place (`tests/assembly/test_worker.py:41` helper; the
   `:877-896` shape).
7. **Plugin strategies are out of scope.** One stub strategy exists, in tests
   (`tests/assembly/test_worker.py:655`); `D-IMPL-354(1)`'s in-process ruling is scoped to the
   capability seam and is **not** read as pre-ruling this — the decision is made
   here on its own merits: the shipped strategy is fixed; carrying identity
   components on `ResolvedEntity` for cooperating plugins is declined.

**Rulings inside the wave-1 entry.**

| # | Question | Options | Recommendation |
|---|---|---|---|
| B1 | Refusal set | `None` only · + empty/whitespace · + bool + float + non-scalar | **widest** |
| B2 | Coercion of `int`/`Decimal` | positional-string (URIs stable; keeps the `1.5`/`1.50` split) · canonical typed (moves every int-identity URI; crosses `D-IMPL-316`) · positional-string plus trailing-zero normalization for `Decimal` only (zero measured population moves) | **positional-string**; (c) if Dave wants the split closed |
| B3 | Semantics on the canonical path | raise, undeclared (HTTP 500 today) · record-and-continue (no L2 audit seam) · raise, and the SDK converts its own seam class by mechanism (amends `D-IMPL-347` B2 for SDK-raised seam classes only) · raise, and every deployment declares it (zero do today; 16 paved-road trees 500) | **raise + mechanism conversion**, cause `nonexistent` (`src/ccf/products/contract.py:306`); the B2 amendment named in the entry |
| B4 | Attribute twin (`src/ccf/assembly/worker.py:369`, null attribute → `"None"`) | omit (absent-not-null, `cp-01`'s posture) · leave · refuse | **omit**, after measuring the null-attribute population (95 `or ""` sites in 32 files across 21 example trees — `grep -rn 'or ""' --include='*.py' examples` — already pre-empt it; CDC rows are the reachable source) |
| B5 | Write-path generation change vs `docs/DESIGN.md` §2A.5.4 / `D-IMPL-44` re-hydration | dispose under the `D-IMPL-243` precedent | **dispose** |

**Blast radius, measured.** 0 existing tests feed a null/empty/non-scalar
identity; 32 test files / 75 call sites invoke `.ingest(` or
`.resolve(envelope=` and stay green (valid identities hash identically); 0
example reds predicted (fixture scan: 0 nulls on declared identity keys).
Bookkeeping: `__all__`, `docs/surface/v0.2-surface.json`, a
`docs/surface-changes/` fragment.

**Red when fixed.** None exists; the negative control is the new pin.
**Sabotage.** Re-enable bare `str()` → the control reddens on entity count;
skip the relationship assertion → the control must still redden on the false
edge (the second assertion is the one that proves the wider defect).

### 3.3 Subject shape — a mechanism floor, and a declared grammar

**Defect.** `ProductRequest.subject` has no shape, `ArgumentDomain` offers only
numeric bounds and enumerated members (`D-IMPL-264` D-03: "exactly one domain
shape"), no door or resolver validates `subject`, and `refuse_payload` checks
only `isinstance(value, str)` for `type: string` parameters
(`src/ccf/products/payload.py:176`). Every acquisition must therefore hand-roll
a guard; of three canonical multi-store trees one does (`cp-14`'s `_IRI`,
`examples/cp-14-credit-memo-context/acquisition.py:143`) and two do not. The SDK's six graph backends never splice seeds — in-memory intersection
with the survivor set (memory via `ccf.graph.fallback`, fluree, mongo, and
neo4j, which then binds the result as `$starts`) or a bound `_in_clause`
(sqlite, postgres) — which settles
the classification: this is an **SDK-forced pattern**, not an SDK splice, and
the mechanism it lacks is a shape.

**Design — two layers, two placements.**

1. **The mechanism floor** (undeclared state = the floor, never unconstrained):
   a bounded length and an **allowlist** grammar —
   `^[A-Za-z0-9][A-Za-z0-9:/._~@+=-]{0,511}$` (512 characters, ASCII, so
   bytes and characters coincide; the longest subject measured in the tree is
   an IRI under 40) — what the fabric can place in a
   URL path segment (whitepaper §6.3's `{counterparty-id}` slot,
   `docs/CCF_Whitepaper_1-2.md:1465`), a SPARQL IRI position and a quoted
   literal. An allowlist, not a denylist, because a denylist that admitted `'`
   would leave a single-quoted literal splice open; this grammar excludes both
   quote characters, `%`, `;`, `#`, whitespace, control characters and every
   bracket, and every subject literal measured in the tree passes it. It is a **compiled mechanism constant in the register of
   `CANONICAL_DECIMAL`** (`src/ccf/products/request.py:1847`) and `MAX_REFERENCE_BYTES`
   (`SEC-003`), versioned by name (`SUBJECT_FLOOR_V1`); a change is a new name.
   It is judged in `GovernedResolver.__call__` **beside `refuse_intent`
   (`src/ccf/products/resolver.py:2203`), before the overridable `constraint_resolver` seam
   (`:2235`)**, so every canonical request passes it and a `PolicyConstraintResolver`
   override cannot remove it (`D-IMPL-121` intact: doors forward verbatim, the
   resolver judges). It applies to `subject` **and to every `type: string`
   parameter**, or the claim to close the parameter splices is withdrawn; the
   floor is applied, so the claim stands. The verdict is recorded through the
   same `_record_refusal` path (`src/ccf/products/resolver.py:3320`), as a governed
   `ProductRequestViolation` with one new reason appended **last** to
   `ProductRequestViolationReason` (`src/ccf/products/request.py::ProductRequestViolationReason`; the roster pin at
   `tests/products/test_request_contract.py:1011-1016` is rewritten to ten
   members). The violation names the field (`subject` or the argument) and the
   floor's version name in `detail`, which pins the floor on the record.
2. **The declared grammar:** `ArgumentDomain.pattern` as a **third exclusive
   shape** — an **amendment** to `D-IMPL-264` D-03 (`docs/DECISIONS.md:742`),
   said so in the entry — plus `ProductRequestContract.subject_domain:
   ArgumentDomain | None` (members-shape and pattern-shape legal; numeric
   refused). Judged inside `refuse_request` (`src/ccf/products/request.py::refuse_request`) through the one
   membership judgment (`ArgumentDomain.refuses` / `_refuse_domain`,
   `:348-516`, `:1768-1841`). A declared pattern **cannot widen past the floor**.
   Compiled with `re.fullmatch` at construction; a non-compiling pattern is
   refused by name. Advertised on the rendered JSON Schema exactly as `enum` is
   (`src/ccf/products/request_schema.py:91` and the planted-key tuple at
   `tests/products/test_request_schema_render.py:291` change together).
   `subject_domain` and `pattern` are hash-transparent `True`: the floor is what
   makes silence safe, so no committed request contract's address moves.
3. **Disclosure:** a shape verdict is a conformity fact about the caller's own
   text, judged pre-anchor, so it is distinguishable from
   nonexistent/unauthorized (`D-IMPL-253` Q27 protects existence, which a
   pre-anchor check cannot reveal). The pattern text lives in `detail`,
   withheld at minimal disclosure (`tests/products/test_disclosure.py:724-727`,
   `:798-801` are the controls that prove the placement; extend, do not touch).
4. **Docstring** at `src/ccf/products/request.py:281-285` corrected: the SDK now does validate
   the shape.
5. **Pre-ruling probe.** Before Dave rules C1a (the grammar and the length), a read-only probe
   runs every example's subject and parameter values (including the
   env-sourced ones, against `.76`) through the proposed floor and reports which
   would refuse. Measured today on literals: zero fail.
6. **Both subject residuals are cited, not conflated:** `D-IMPL-128` limb 2
   already holds the client-chosen subject as a named residual; this entry
   closes the *shape* half only. The floor is necessary, not sufficient: an
   adopter who concatenates instead of binding can still be broken by text
   inside the grammar. The tag map says "shape half", never
   "injection-complete".
7. **stdio half:** not code in 1.0.2 (§7.3). The SDK door page discloses that
   `ProductDoor.serve_stdio` (`runtime/ccf_runtime/mcp/product_door.py:240-268`)
   serves one pre-set identity for every caller (`public/` has zero mentions
   today).

**Rulings inside the wave-1 entry.**

| # | Question | Options | Recommendation |
|---|---|---|---|
| C1 | Undeclared subject shape | unjudged (intent idiom) · **SDK floor** · mandatory declaration at registration | **floor** |
| C1a | The floor's grammar and length | the allowlist in item 1 with 512 · a wider character set · a shorter or longer bound | **as written**, with the probe result attached to the ruling |
| C2 | Floor placement | beside `refuse_intent` before the overridable seam · inside `refuse_request` (bypassed by an override) · a `ProductRequest` validator (transport error, no record) | **beside `refuse_intent`** |
| C3 | Parameters | floor for every `type: string` argument · subject only | **every string argument** |
| C4 | Declared grammar | `pattern` as third `ArgumentDomain` shape + `subject_domain` (amends D-03) · a separate `SubjectShape` type · on `ProductDiscovery` | **third shape** |
| C5 | Hash posture of the new fields | `True` given the floor · `False` generation boundary | **`True`** (only because C1 = floor) |
| C6 | `EX-01` regrade | keep HIGH · regrade `cp-17` to MEDIUM and name `cp-16` as the reachable HIGH exemplar | **regrade**, recorded as a verified retraction |

**Blast radius, measured.** 38 `ArgumentDomain(` sites in 4 test files, 17
`argument_domains=` in 4, 21 `ProductRequestContract(` in 16, 37
`ProductRequest(` in 28 — all green (new fields default). Red:
`tests/products/test_request_contract.py:1011-1016` (roster pin); `test_request_schema_render.py`
(9 tests gain `pattern`); `tests/products/test_disclosure.py:231` stays green here (the subject floor
reuses `ProductRequestViolation` and introduces no class; wave 2's
`TemporalBoundRefusal` does, §4.3 item 5);
`cinv06-hash-transparent-key` until the new fields declare their key;
`tools/dump_surface.py --check` until regenerated with a fragment. Subject
forwarding sites (all verbatim, unaffected): `src/ccf/products/child_resolver.py:771`,
`src/ccf/products/composite.py:1395`, `src/ccf/products/door.py:785`, `src/ccf/skills/dispatch.py:356/377/1076`,
`src/ccf/client/adapters/mcp_stdio.py:241`, `runtime/ccf_runtime/mcp/egress.py:1748`.
Examples: `cp-16` and `cp-04-canonical` keep their splices (frozen); their
env-sourced values are measured by the probe.

**Sabotage.** Remove the floor → a subject carrying `"` reaches the
acquisition seam (control asserts refusal before `refuse_intent`'s successor).
Route the floor through the overridable seam → a stub `PolicyConstraintResolver`
skips it (control asserts the floor fires under an override). Let a declared
pattern widen past the floor → control reddens.

### 3.4 `SEC-029` — the version stamp is the tag's, and the tag carries the map

**Defect.** `version = "0.1.0"` (`pyproject.toml:7`) is read at runtime
(`src/ccf/graph/registry.py:474-484`) into `AdapterPin.version` (`:345`) and
written into dimension 2 of every replay record as `graph_adapter_version`
(`src/ccf/replay/record.py:663`). A bank correlating a record to a release or a
CVE cannot. v1.0.0 and v1.0.1 both shipped it.

**Design.**

1. **Single source:** `dynamic = ["version"]` with `setuptools_scm` deriving the
   version from the git tag at build time. A build from the detached
   qualification worktree at `v1.0.2` yields exactly `1.0.2`; a dev tree yields
   a `1.0.2.devN+g…` string, which is the correct thing for a record produced by
   unreleased code to say.
2. **Belt:** the qualification recipe asserts, in the fresh worktree's venv,
   `importlib.metadata.version(SDK_DISTRIBUTION) == tag.lstrip("v")` before the
   TAG GO, and a CI job on `v*` tags fails when they differ.
3. **`SEC-027` coupling.** `SDK_DISTRIBUTION = "ccf"` (`src/ccf/graph/registry.py:188`) is
   the name `importlib.metadata` reads. **Measured 2026-09-25:** `pypi.org/pypi/ccf-sdk/json`
   returns 404 (unclaimed); `pypi.org/pypi/ccf/json` is Microsoft's
   Confidential Consortium Framework tooling at 7.0.17 (`CCF-Sec@microsoft.com`).
   Claiming `ccf-sdk` is Dave's outward-facing action (§0 #5). If it is claimed
   before wave 1 closes, the distribution is renamed in the same wave —
   `pyproject.toml` `name`, `SDK_DISTRIBUTION`, the qualification venv recipe —
   or the runtime stamp breaks at the rename. If it is not, the rename is a
   named carry and the stamp ships under `ccf`.
4. **Tag text:** the annotated `v1.0.2` tag carries the security-review map
   (§8.4): every `SEC` id with its status and the `D-IMPL` that closed it; the
   `TP` and `EX` rows; what is carried.

**Blast radius.** Build tooling only; no test reads the version. The
qualification recipe (§8) gains one assertion.

### 3.5 Bookkeeping landed in wave 1

- **`SEC353-G-09`** in `docs/D-IMPL-353-EXAMPLES-GAP-LEDGER.md`: eight frozen
  custom doors — `examples/cp-15-kyc-refresh-beneficial-ownership/server/serve.py:128`,
  `examples/cp-16-abs-securitization-surveillance/server/serve.py:121`,
  `examples/cp-17-mnpi-wall-enforcement/server/serve.py:109`,
  `examples/cp-18-ib-opportunity-synthesis/server/serve.py:121`,
  `examples/cp-19-aml-typology-match/server/serve.py:135`,
  `examples/cp-21-large-exposure/server/serve.py:123`,
  `examples/cp-23-portfolio-early-warning/server/serve.py:119`,
  `examples/cp-24-portfolio-what-if/server/serve.py:119` — call `open_door(token_verifier=…)`, a keyword
  `ba946df1` removed (`runtime/ccf_runtime/mcp/product_door.py:320-327` takes `environ`,
  `perspective_resolver`, `entitlement_source`). All eight raise `TypeError` at
  construction, are reverted by ruling, estate-gated (never run for v1.0.1) and
  unledgered. Zero examples use the migration target `open_door_with_verifier`.
  Ledgered; not unfrozen (§0, L2).
- **`D-IMPL-361`** (§7.1): the adapter findings rated HIGH, chartering the
  first 1.0.3 wave.

### 3.6 Wave-1 close

- **Estate-gated run** (§8.3) at the wave base and at close; every red by node
  id, classified (pre-existing / new / ledgered).
- **Panel payload** (one stdin bundle, ~54 KB of named ranges):
  `src/ccf/workflow/definitions.py` (whole),
  `runtime/ccf_runtime/workflow/engine.py:500-560` and `:930-1060`,
  `src/ccf/assembly/worker.py:300-400`, `src/ccf/products/request.py:230-520`
  and `:1900-2000`, `src/ccf/products/resolver.py:2190-2290`,
  `src/ccf/controlplane/artifacts.py:1550-1565`, `src/ccf/deployment/binder.py:325-338`,
  the diff, the new tests, and the brief.
- **Known findings briefed:** the four items above; the escalation sibling;
  the partial-admission residual; `cp-16`/`cp-04-canonical` splices as frozen
  evidence.

---

## 4. Wave 2 — The fabric clock

One injected clock, read once per serve, recorded **beside** the decision
instant and never in place of it. It is the wave with the largest ruling load
and the only one that touches the replay record, so it has its own panel with
the replay engine inlined.

### 4.1 The defect in one paragraph

The served path reads no clock. Every instant the resolver uses derives from
the caller's `asked_at` or from a caller-typed decision-instant parameter
(`src/ccf/products/resolver.py:2064-2071`): the as-of read (`:2344`), dimension-1
`graph_snapshot_at` (`:2364-2368`), the debt scorer (`:2626-2631`), the TTL
anchor (`:2681`), Gate 3's `now` (`:2911`), the composite mixing law
(`:2704-2707`) and the record's `recorded_at` (`:3106` served; `:3363`
refusals). That is what makes two runs of one question record at one instant
(`tests/products/test_delivery_determinism.py:260-269`) — and what makes every
one of those controls the attacker's. Policy effectivity is evaluated at
`asked_at` (`src/ccf/products/constraints.py:574-576`, `:1524-1536`) by an explicit ruling
(`D-IMPL-253` Q6: *"asked_at, absolutely — otherwise replay of the same
historical decision can resolve a different policy"*). For `from_decision`
classes Gate 3 reduces to `0 < ttl <= MAX_TTL`. Back-dating a question
resurrects an older policy regime and lowers Context Debt; forward-dating mints
validity past `MAX_TTL`; and the record replays perfectly because every
component agreed on the caller's clock.

### 4.2 What the replay engine holds, verified (the constraints on any fix)

1. `src/ccf/replay/engine.py:78`: *"Nothing here reads a clock, and nothing
   here resolves latest."* Replay never invokes `GovernedResolver`
   (`src/ccf/replay/engine.py:1417-1440` drives `ProjectionEngine` over a `SnapshotReader`
   directly), never runs gates (`D-IMPL-344` R-2; `grep run_gates src/ccf/replay`
   is empty), never re-verifies a HITL signature. **Anything placed inside
   `GovernedResolver.__call__` is replay-exempt by construction.**
2. `recorded_at` is overloaded four ways: for a `from_decision` record
   `_hold_ttl_anchor` raises `ReplayDivergence` unless `ttl_anchor_at ==
   record.recorded_at` (`src/ccf/replay/engine.py:1220-1226`); for `from_entity_freshness` the
   anchor is re-derived at `decided_at=record.recorded_at` (`:1244`;
   `src/ccf/products/expiry.py:225/:229`); for every resolver refusal
   (`product=None`) the snapshot `temporal_boundary` **is** `recorded_at`
   (`src/ccf/replay/record.py:2003-2005`), hashed into `graph_snapshot_id` (`:506-510`), and
   `replay_refusal` re-executes at it (`src/ccf/replay/engine.py:1057`). **`recorded_at` is
   not a free slot.** Redefining it as the wall clock makes every new
   decision-anchored serve fail its own replay and moves every refusal's
   dimension-1 identity.
3. Dimension 5 already carries the request's `asked_at` beside `recorded_at`
   ("the record says both rather than one twice", `src/ccf/products/resolver.py:3103-3106`).
4. The precedent for a recorded clock reading exists and is ruled: O3's
   `admitted_at = self.admission_clock()` (`src/ccf/products/resolver.py:2395`; `D-IMPL-336`,
   `docs/DECISIONS.md:3391`: *"from the trusted runtime clock boundary … never
   from decided_at, a historical asked_at, or any request-supplied timestamp …
   injectable for deterministic tests … preserve admission time in replay"*),
   recorded inside a dimension (`child_admitted_at`, `src/ccf/replay/record.py:1117`) and
   never re-derived or compared by replay.
5. Additive record members follow the hash-transparent-at-sentinel discipline
   (`src/ccf/replay/record.py:466`, `:666`, `:777-789`, `:819`, `:883`, `:1459-1466`;
   `tools/lints/hash_transparent_key.py`, CINV-06). Every prior extension went
   **inside** a dimension because nine tests pin the top-level record shape
   (`tests/conformance/test_harness_portability.py:733` et al.).
6. Whitepaper §7.10 (`docs/CCF_Whitepaper_1-2.md:3255-3263`) defines the record
   around one decision time `t`; `D-IMPL-253` Q23 forbids wall-clock time in
   addressed content (amended by this wave for `served_at` alone, item 4); Q13 (`src/ccf/replay/serve.py:455-457`) forbids
   second-class replay for refusals. The whitepaper's TTL invariant (`:3050`)
   is two-sided at assembly time.
7. The federated leg is **already** at the fabric clock: a peered composite
   child runs Gate 3 at `now=admitted_at` (`src/ccf/products/child_resolver.py:467`;
   `src/ccf/peering/admission.py:898-903` reads no clock). Today one composite
   serve runs Gate 3 at two different clocks (parent at `decided_at`, peered
   child at `admitted_at`). The consumer side already judges expiry at an
   injected `now` (`src/ccf/agents/agent.py:349`, `ConsumptionRefused`).

### 4.3 Design

1. **One read.** `served_at = self.admission_clock()` once at
   `GovernedResolver.__call__` entry (`src/ccf/products/resolver.py:2073`), hoisted out of the
   composite branch (`:2387-2395`, where it is read only `if registered.requires:`);
   `admitted_at := served_at`, so the composite window is unchanged and O3's
   read-once control (`tests/products/test_resolver_seam.py:2830`) stays the
   control. `admission_clock` already exists (`:1957`; default `_utc_now` at
   `:1583`; wired at `build_governed_resolver` `:3958`; `open_product(clock=)` →
   `"admission_clock": self._clock`, `src/ccf/products/product.py:844`/`:602`). **No second
   clock anywhere.** Every door — HTTP, MCP tool and resource, the in-process
   door (`src/ccf/products/door.py`, algorithmic, zero `runtime` imports, which
   never crosses the runtime delivery boundary) — and every composite child
   passes through `__call__`.
2. **Gate 3 is two-sided at `served_at`:** `served_at < expires_at <=
   served_at + MAX_TTL` (`src/ccf/products/gates.py:1385-1386`; `MAX_TTL` from
   `product_class.max_ttl_key`, `:1376-1378`). `expires_at`, `ttl_anchor_at` and
   `temporal_boundary` — the addressed content — are untouched (Q23 is amended
   only in that `served_at` joins addressed content, item 4). A
   one-sided lower bound would leave forward-dating able to mint validity past
   `MAX_TTL`; the whitepaper invariant is two-sided. This **amends the
   `D-IMPL-308` reading that Gate 3 runs at the decision instant**
   (`src/ccf/products/resolver.py:2908-2911`: "within bounds OF THE MOMENT IT WAS
   DECIDED … (`D-IMPL-308`)"), and the entry says so; `D-IMPL-308`'s fence — the
   decision instant is never collapsed onto the graph boundary — is untouched,
   because `served_at` is a third instant. `served_at` is a
   **required** argument on `run_gates` and `run_federated_gates` (§2, rule 4:
   a keyword-only `None`-passes default is the caller-supplied-applicability
   shape). The federated leg passes `admitted_at` as it already does. The
   threat-model boundary is stated in the entry: the fabric clock is a control
   on the **governed served surfaces**, where `GovernedResolver` alone supplies
   `served_at`; a direct caller of `run_gates` — a frozen `produce.py`, an
   adopter's own runner — is in-process code outside the model (`D-IMPL-354`
   ruling 1), and the required argument stops `None`-passes there, not a
   caller-typed instant.
   `TTLRefusal` gains `served_at` (the fields pin at
   `tests/products/test_refusal_envelope.py:431` is rewritten by design); the
   check stays under the existing `GATE_TTL_BOUNDS` token, so the token census
   at `tests/products/test_structural_gates.py:1103` — an AST walk for `GATE_*`
   names that reddens only on a new token — is unchanged (D13). The
   declared-window well-formedness the old gate reduced to (`0 < product_ttl
   <= MAX_TTL`) is retained as an explicit declaration-time check so nothing the
   old gate enforced by accident is lost silently.
3. **Policy effectivity at `served_at`** — an amendment to `D-IMPL-253` Q6,
   presented as a **bitemporal amendment of the record with a named field**
   (dimension 1 as-of `asked_at`; dimension 2 in-force-at `served_at`), not as a
   reinterpretation of `recorded_at` (`D-IMPL-308`, `docs/DECISIONS.md:2122-2126`:
   *"Coincidence is allowed; collapse is not … do not redesign temporal
   semantics generally"*). `PolicyConstraintResolver.resolve(...)`
   (`src/ccf/products/constraints.py:1395-1415`) gains an explicit instant keyword; the reference
   resolver evaluates `constraints_in_force(at=served_at)`; the pure functions
   keep their instant parameter (their 20 keyword call sites in the constraint
   tests are untouched). One instant keyword flows through `resolve` →
   `applicable` → `_in_window`, so no call site is left on `request.asked_at`
   (a split-brain effectivity is the failure the control tests for), and the
   "never a clock" docstring at `src/ccf/products/constraints.py:1404` is
   rewritten in the same change. `D-IMPL-308` (the decision instant is never
   collapsed onto the graph boundary) is untouched by this: `served_at` is a
   third instant, and neither of the other two is substituted for it. Q6's reason survives: replay resolves the pinned
   `(key, version)` bindings from dimension 2 and never re-evaluates
   effectivity. A constraint in force **now** applies to any question asked
   **now**, whatever instant it asks as-of.
4. **The record.** `served_at` is a **new member inside `ContentGenerationPath`**
   (dimension 5), `json_schema_extra={HASH_TRANSPARENT_KEY: True}` at `None`
   (§0, #4: pre-1.0.2 addresses rehydrate unchanged; CINV-06 satisfied).
   `recorded_at` is **untouched** on both paths — `decided_at` on the served
   path (`src/ccf/products/resolver.py:3106`), `request.asked_at` on every
   refusal path (`:3363`), which is what keeps a refusal's dimension-1 boundary
   on the question's instant — so `src/ccf/replay/engine.py:1220-1226`, `:1244`
   and `src/ccf/replay/record.py:2003-2005` are untouched. The
   refusal path passes the snapshot boundary **explicitly** from
   `request.asked_at` (the only conflation site is `src/ccf/replay/record.py:2003-2005`), so a
   governed refusal's dimension-1 `graph_snapshot_id` and its `replay_refusal`
   re-execution stay on the question's instant whatever else stamps the record.
   The door refusal branch at `runtime/ccf_runtime/authz/delivery_boundary.py:506`
   reads `recorded_at=asked_at if asked_at is not None else determined_at`:
   the `asked_at` arm keeps the question's instant and carries `determined_at`
   beside it (`ResourceRequestIdentity.determined_at` exists at
   `:403`/`:500`/`:658`); the `else` arm — reachable only from the MCP resource
   path that passes `asked_at=None` by design
   (`runtime/ccf_runtime/mcp/egress.py:1095-1110`) and an axis-less HTTP GET —
   is the ruled resource-form instant (`D-IMPL-256` (1)) and is retained and
   named, not redesigned here. A positive control is added in
   `tests/authz/test_delivery_boundary.py`: `govern_raised_refusal` with an
   `asked_at` one day before `DETERMINED_AT` asserts `record.recorded_at ==
   asked_at`, the carried `determined_at == DETERMINED_AT`, and `served_at`
   once threaded; severing the carry reddens it. The module's one-clock AST
   test (`:793-820`) is unaffected because the bound lives in the resolver,
   not there.
   **Hash-transparent means the sentinel, not the value** (`D-IMPL-243`,
   `docs/DECISIONS.md:649`; `src/ccf/replay/engine.py:379`: "only the `None`
   sentinel is hash-transparent"): every pre-1.0.2 record, whose `served_at` is
   `None`, rehydrates to its recorded address unchanged — Dave's ruling — and
   every new record's populated `served_at` is rendered into the address, so
   **two serves of one question are two records**. That is the audit reading a
   bank wants (which determination, produced when), and it is the posture O3
   already chose for `child_admitted_at` (`src/ccf/replay/record.py:1117-1119`,
   a generation boundary). Every "same determination twice" assertion therefore
   runs under a pinned clock, which is what proves the clock is the only
   difference. This **amends `D-IMPL-253` Q23** ("avoid wall-clock time in
   addressed content") for this one member, and Amendment 3(3)'s end-to-end
   property, which becomes: same request + same governed state + same
   `asked_at` + same `served_at` (a pinned clock) → same determination and the
   same address; the entry names both. The rule applies to **every** refusal
   recorder call, including
   the door's own address refusal, which today stamps
   `recorded_at=self._clock()` (`src/ccf/products/product.py:746-749`) and so
   lets a wall clock into that refusal's dimension-1 identity: it passes
   `request.asked_at` as the boundary and carries the clock reading as
   `served_at`.
5. **The temporal bound is an artifact.** `TemporalBoundaryPolicy`, a
   per-tenant Control Plane artifact in `EligibilityEvidencePolicy`'s shape
   (`src/ccf/peering/eligibility.py:255-300`): `max_past_seconds` and
   `permitted_clock_skew_seconds`, applied to `asked_at` **and** to a declared
   decision instant, relative to `served_at`. **Both** bounds: a bank asks
   as-of the trade date, and a back-dated question also evades every constraint
   added since. **Refuse when undeclared**, by name, the `eligibility-bound-undeclared`
   precedent (`src/ccf/peering/eligibility.py:440-468`) — no SDK number (§0, #3; CINV-01).
   Checked in `GovernedResolver` **before the graph read**, so HTTP, MCP,
   in-process and every composite child are covered by one check and replay is
   exempt by construction. Coverage of a composition is by inheritance: every
   child — in-process, MCP or peered — is asked at the parent's bounded
   `asked_at` (`src/ccf/products/child_resolver.py:164`, `:241`, `:277`, `:458`);
   the peered leg's admission and Gate 3 run at the fabric's `admitted_at` as
   today (`:463-468`, `:554-585`); a peer producer applies its own tenant's
   bound to the same instant. A control asserts that a child cannot be asked at
   any other instant and that an admitted child's answered question echoes the
   inherited one. Placement, precisely: after `effective_request` is built
   (`src/ccf/products/resolver.py:2307-2309`) and **before the acquisition
   seam** (`:2311`), so an out-of-bound question invokes the seam zero times,
   reads no source and ingests nothing (the `D-IMPL-343` R-4 invariant written
   on that seam — a refused request never reaches it — holds). The vehicle is
   **one new refusal contract**, `TemporalBoundRefusal` (kind
   `temporal-bound-refusal`), whose closed `reason` Literal is
   `temporal-bound-undeclared`, `asked-at-outside-temporal-bound`,
   `decision-instant-outside-temporal-bound`; it is registered in
   `REFUSAL_KINDS` (`src/ccf/products/refusal.py:555`) and
   `_PRE_ASSEMBLY_REFUSALS` (`:789-797`), with its `EXTERNAL_STATEMENTS` /
   `PERMITTED_AT_MINIMAL` entries (`src/ccf/products/disclosure.py:192`, `:329`),
   its HTTP status in `runtime/ccf_runtime/http_api/refusal_status.py` and the
   MCP mapping (D-16 parity) — a governed refusal with a replay record, not a
   request-shape 400 (`ProductRequestViolation` and `ConstraintRefusal` are both
   400 with closed reason rosters). **The dimension-2 pin is a record-builder
   change, not a precedent:** `EligibilityEvidencePolicy` is *not* pinned today
   — `src/ccf/peering/eligibility.py:425-431` resolves it latest and discards
   the version, and no `PolicyBinding` is minted for it anywhere. This wave
   resolves the tenant's `TemporalBoundaryPolicy` once per serve, keeps the
   returned version, and appends `PolicyBinding(key, version)` to the served
   tuple (`src/ccf/products/resolver.py:3090-3100`) and to every
   `_record_refusal` call's `policy_bindings` (`:3360-3375`) — the same builder
   change §5.1 item 4 makes for `HitlPolicy`; that builder site is the sever
   site for the §4.9 sabotage. `EligibilityEvidencePolicy`'s own unpinned
   resolution is the same defect class and is a §7.4 row.
6. **`D-IMPL-308` is scoped, not reversed.** The `decision_instant_parameter`
   fallback to `asked_at` when a class declares none (`src/ccf/products/resolver.py:2064-2068`;
   only `s1-01`, `cp-14` and `cp-20` declare one) is kept. The declared instant
   is parsed today unbounded and without a UTC check (`:2069-2071`); it gains
   the same awareness check the doors apply to `asked_at`
   (`runtime/ccf_runtime/mcp/egress.py:418-434`) and is held to the temporal
   bound. Once Gate 3 is two-sided at `served_at`, `product_ttl` and `MAX_TTL`
   already confine the decision instant to `[served_at − ttl, served_at +
   MAX_TTL − ttl]`; the bound is the declared, auditable narrowing on top. A
   legitimate historical reconstruction is served only inside the declared
   window; outside it, the answer is a replay of the recorded decision or a
   governed refusal naming the bound.
7. **`D-IMPL-159` stays a named residual; the clients' default is not moved
   in 1.0.2.** `docs/DECISIONS.md:492` holds the fabric-clock question OPEN
   ("resolved as a deferral; the underlying defect is OPEN"). Moving the
   clients' `None → datetime.now(UTC)` default
   (`src/ccf/client/adapters/inprocess.py:427`,
   `src/ccf/client/adapters/mcp_stdio.py:251`) producer-side is a contract
   change on two legs, measured by both reviews: the MCP egress tool requires
   `asked_at` by ruling (`D-IMPL-158` BREAK 1, `docs/DECISIONS.md:490`;
   `runtime/ccf_runtime/mcp/egress.py:418-434`, `:1336-1343`), so the stdio
   client resolves it client-side because the wire cannot carry a deferral;
   and the in-process adapter builds `ProductRequest(asked_at=…)` before it
   calls the resolver (`src/ccf/client/adapters/inprocess.py:451-499`) while
   `ProductRequest.asked_at` is required (`src/ccf/products/request.py:341`), so
   a deferral would need a request sentinel and a route back to the door's
   `AnsweredQuestion` echo, and a read anywhere but inside `__call__` would be
   a second clock read. What 1.0.2 does instead: the client's instant, however
   chosen, is judged by the tenant's temporal bound at the resolver (item 5) —
   the control `D-IMPL-159`'s deferral lacked; the HTTP door keeps its
   400-incomplete for an absent `asked_at`
   (`runtime/ccf_runtime/http_api/routes/product.py:731-741`, `D-IMPL-98`); the
   MCP door keeps its required axis; `D-IMPL-159`'s own control
   (`tests/client/conformance/test_a_crossed_question_is_caught_on_one_transport.py::test_an_absent_boundary_leaves_the_moved_instant_undetectable`)
   stays green as the pin. A producer-side deferral — `asked_at := served_at`
   inside `__call__`, carried by a request sentinel, with the `D-IMPL-158`
   amendment the MCP tool would need — is a §7.4 row. `D-IMPL-159`'s "in
   `runtime/`" placement clause is already superseded by O3's injected
   `admission_clock` seam in the algorithmic resolver (`D-IMPL-336`,
   `docs/DECISIONS.md:3391`; the read is injected at composition, not ambient),
   and the entry says so.
8. **`SEC-008`'s write half is carved out and named.** The acquisition seam
   stamps `ingestion_timestamp = asked_at` (`src/ccf/products/product.py:813`/`:816`;
   `src/ccf/signal/envelope.py:112`; `src/ccf/assembly/worker.py:495`) **because** the as-of reader cuts on
   `observed_at <= at` (`src/ccf/graph/fallback.py:59`; `src/ccf/graph/reader.py:117`).
   Measured: every stamping example boots a per-run scratch substrate
   (`src/ccf/products/product.py:778-787` mints a uuid-named fabric per question), so the
   persistent "time bomb" has zero shipped instances on the paved road; it is a
   mechanism exposure of the low road (`AssemblyWorker.ingest` and
   `ingest_admitted(ingested_at=…)`, `src/ccf/assembly/worker.py::ingest_admitted`, a second
   caller-stamped write path). In 1.0.2: the stamp stays as the documented
   per-question-fabric convention; the `AcquisitionContext.instant` docstring
   (`src/ccf/products/product.py:243-246`, "the clock") is corrected to "the bounded as-of
   boundary", and three further invariants the change falsifies are rewritten
   in the same diff — `src/ccf/products/resolver.py:1966-1969` ("nothing in the
   path reads a clock"), the `__call__` docstring at `:2103-2106`, and the
   `run_gates(...)` docstring example at `src/ccf/projection/engine.py:396-402`
   (which gains `served_at`); `src/ccf/products/gates.py:74-76` stays true;
   `served_at` lands on the record; and **two follow-on entries are
   opened in the same sitting** so `SEC-008` is not silently half-closed: a
   bitemporal as-of read (valid-time `asked_at`, transaction-time `served_at`;
   INV-CH7-03/14 territory) and an opt-in L2 clock guard on `ingest` /
   `ingest_admitted` for long-lived fabrics. The exposure, stated
   precisely: the SDK's own ingress adapters stamp from an injected clock that
   defaults to the wall clock (`runtime/ccf_runtime/cdc/adapter.py:104`;
   `src/ccf/signal/acquisition.py:145`; `src/ccf/signal/mcp_source.py:112`), so
   the caller-controlled write stamp exists only where a deployment authors
   envelopes itself into a long-lived fabric (32 example files do, on the low
   road) or calls `ingest_admitted(ingested_at=…)`. **Option (d), now
   recommended after the external panel:** ship the L2 guard in this wave —
   `AssemblyWorker.ingest` and `ingest_admitted` refuse an envelope whose
   `ingestion_timestamp` lies outside the same `TemporalBoundaryPolicy` window
   around an injected clock; the paved road's per-question stamp is inside the
   window by construction (its `asked_at` already passed the bound); replay
   never ingests and `D-IMPL-44` re-hydration is not built, so nothing
   replayable reads the clock; the writer reads a clock only to **refuse**,
   never to stamp. Under (d) the bitemporal read is the one follow-on row;
   under (a) the L2 guard is a second row and the tag text says the write half
   is **open and carried** — never "bounded", because nothing bounds it.
9. **Context Debt** (`src/ccf/products/resolver.py:2626-2631`; `src/ccf/products/product.py:361-373`) is a fact
   about evidence freshness **at the decision instant** and stays there; the
   temporal bound caps how far a caller can move that instant. Named as the
   fourth control on the same instant; recommended under D8, not slipped.
   **The composite mixing law is different**: how much validity a child has
   LEFT "is a fact about now, not about the parent's evidence"
   (`src/ccf/products/resolver.py:2704-2707`, the comment's own words), yet it is
   evaluated at `decided_at` (`src/ccf/products/composite.py:2120-2124`,
   `evaluated_at=decided_at`). With the bound permitting a two-hour look-back, a
   caller asking as-of `served_at − 2h` makes a child with thirty minutes left
   read as having two and a half hours, so a composite that breaches its
   validity floor at the fabric's serve instant is still served while its
   absolute `expires_at` passes the two-sided gate. **The mixing law moves to
   `served_at`** in this wave (`refuse_mixing(..., evaluated_at=served_at)`);
   `ttl_anchor_at` is untouched.
10. **The in-process composite child** runs its Gate 3 at `served_at` like the
    parent; the asymmetry with the peered leg (already at `admitted_at`)
    closes because both are now the same read.

### 4.4 Rulings inside the wave-2 entry

| # | Question | Options | Recommendation |
|---|---|---|---|
| D1 | Policy effectivity instant (amend `D-IMPL-253` Q6) | (a) `served_at`, `asked_at` is the as-of read · (b) keep Q6, rely on the bound · (c) both must admit | **(a)** as a bitemporal amendment with a named field |
| D2 | Where the fabric's instant lands | (a) `served_at` inside `ContentGenerationPath`, hash-transparent at `None`; `recorded_at` unchanged; refusal boundary explicit from `asked_at` · (b) `recorded_at := served_at` (refuted: breaks the anchor hold, moves refusal identity) | **(a)**; the `None` sentinel keeps pre-1.0.2 addresses, a populated value is addressed (two serves = two records) |
| D3 | Gate 3 comparand and `served_at` posture | two-sided at `served_at`, **required** on the gate runners (74 `tests/` call sites rewritten, 3 `src/` runners and 1 perf conftest; 9 `archive/` callers go dead; 5 frozen `cp-00..04 produce.py` become rows), with the threat-model boundary stated · keyword-only `None`-passes | **required, boundary stated** |
| D4 | The no-parameter majority (`D-IMPL-308`'s fallback is kept; its Gate-3-at-decision reading is amended under D3) | keep the fallback + two-sided gate + bound · default the decision instant to the fabric clock (a `D-IMPL-308` revision) | **keep** |
| D5 | Temporal bound artifact | per-tenant, both bounds, refuse-when-undeclared, checked in the resolver, governed refusal, pinned on dim 2 · undeclared = unbounded · SDK default | **per-tenant, refuse** (ruled §0 #3) |
| D6 | `SEC-008` write half | (a) carve out + two follow-on rows; the write half recorded OPEN · (b) stamp at `served_at` and change the reader's cut in the same wave · (c) stamp at `served_at`, keep the cut (every historical paved-road read returns nothing) · (d) carve out the stamp, ship the L2 refusal guard on the same policy with an injected clock | **(d)**; all three external reviewers read (a) as under-remediation for a bank; (a) only if Dave rules an L2 clock out |
| D7 | `D-IMPL-159` | stays a named residual: both client adapters keep their client-side default, now bounded at the resolver by item 5; the producer-side deferral (a request sentinel resolved to `served_at` inside `__call__`, plus the `D-IMPL-158` amendment for the MCP tool) is a §7.4 row · reopen now (the two-leg contract change inside a security wave) | **residual, bounded**; the row carries the deferral |
| D8 | Context Debt and the composite mixing law | debt at the decision instant + bound, mixing at `served_at` · both at `served_at` · both at the decision instant (leaves the mixing floor caller-applicable) | **debt at the decision instant, mixing at `served_at`** |
| D9 | Hand-over freshness ownership | producer serve (Gate 3) · consumer consume (`src/ccf/agents/agent.py:349`) · both, named in the controls register | **both, named** |
| D10 | `SEC-011` Gate 2 | (a) NOT-A-GAP under `D-IMPL-86`/`300`; fix `public/concepts/invariants.md:82-84`; ship the controls register · (b) promote the binder's bare `ValueError` to a governed refusal (contradicts `D-IMPL-253` Q15) · (c) reopen `D-IMPL-86` | **(a)** |
| D11 | `SEC-019` rider (amends `D-IMPL-253` Q5's realization) | a bounding constraint (`maximum`/`minimum`/`allowed_set`) on a parameter with no value and no declared default is a `required-absent` refusal; `required` stays the explicit form; `preferred` stays non-refusing · keep the skip | **refusal** |
| D13 | Gate 3's token | stays under `GATE_TTL_BOUNDS` (the roster and the `:1103` census unchanged; only the `:431` fields pin reddens) · a new serve-time token (a `D-IMPL-238` roster amendment; `:1103` reddens) | **stays under `GATE_TTL_BOUNDS`** |
| D12 | Example disposition | gap-ledger rows first, one repair sitting for living reference trees (ruled §0 #3) — **roster of "living reference trees" confirmed at the sitting** (candidates: `s1-00`, `s1-01`, `hw1-companies-over-revenue`, `hw1-harness-clients`) | **as ruled** |

### 4.5 Replay determinism, stated once

What is recorded: `served_at` (dimension 5, transparent only at its `None`
sentinel, addressed once populated) and the `TemporalBoundaryPolicy`
key+version (dimension 2, minted by the record builder). What is held:
`recorded_at` (`decided_at` served, `asked_at` refused), `ttl_anchor_at`, `expires_at`, `graph_snapshot_at` and
the refusal's `temporal_boundary` — none moves. What replay does: resolves the
pinned bindings, re-executes the projection at `snapshot.temporal_boundary`,
rehydrates `expires_at` from the recorded anchor, compares content addresses
(`src/ccf/replay/engine.py:862-955`; `src/ccf/replay/environment.py:156-190`). What replay does not do: read
a clock, run a gate, evaluate effectivity, or cross `GovernedResolver`. A
`served_at` that is **carried** is therefore reproducible; a `served_at` that
were **re-derived** would not be, which is why the sabotage that proves the
design is a second clock read in the resolver, not anything in replay. Two
serves of one question at two instants are two records with two addresses (a
populated `served_at` is rendered; only the `None` sentinel is transparent); every "same determination twice" assertion runs under a pinned
clock so it proves the clock is the only difference.

### 4.6 Example disposition and the repair sitting

Under refuse-when-undeclared, every example tree that declares no
`TemporalBoundaryPolicy` refuses, and every `from_decision` tree with a pinned
historical instant is also expired at a wall clock. Measured by grep, not by
run: 19 pinned `asked_at` literals across 17 trees (from `2024-03-29`,
`cp-03-obligor-financial-spread`, to `2026-09-15`, `s1-01`), plus
`examples/hw1-companies-over-revenue/deployment/binding.yaml:45` and
`examples/hw1-harness-clients/runner/question.yaml:71`; about 25 trees. The
five frozen `cp-00..04 produce.py` direct `run_gates(` callers go red on the
required argument. **All become gap-ledger rows** (`SEC010-G-NN`, the
`SEC353-G` shape), censused by node id from the estate-gated run at the wave
base and at close. **Then one repair sitting**, `s1-01` style
(`D-IMPL-355` option B), for the living reference trees only: declare the
policy under the deployment's tenant, pin the clock where the tree pins its
question, re-run on an empty Fluree and against `.76`. The roster is Dave's at
the sitting; the frozen family stays rows.

### 4.7 `SEC-011` Gate 2 — NOT-A-GAP, with the residue closed

`D-IMPL-86` element 4 ruled Gate 2 "claim-versus-execution, i.e.
assembly-path integrity, documented as such"; `D-IMPL-300` made the failable
pre-execution control SDK mechanism (`refuse_operator_set_divergence`, called
at `src/ccf/products/resolver.py:2572`, comparing the class declaration against the
projection's own requirements artifact — the review's stated remedy). Three
reviewers established that an independent engine witness cannot exist. What
remains is an assurance inconsistency: `public/concepts/invariants.md:82-84`
advertises the forgery reading while `public/tutorial/adopters-guide.md:125`
discloses assembly-path integrity, and the binder raises a bare `ValueError`
outside every `try` (`D-IMPL-253` Q15: configuration failures raise). Wave 2
ships: the page fix; and a **controls register** (under `public/reference`)
mapping each gate token (`src/ccf/products/gates.py:218-248`), the binder, and the consumer-side
expiry (`src/ccf/agents/agent.py:349`) to the path on which it can fail and the test that reds
it — so a bank's assurance reviewer is pointed at the control that actually
fails, not at one that cannot.

### 4.8 `SEC-019` rider

`src/ccf/products/constraints.py:1092-1093` (`if key not in effective: continue`) and
`src/ccf/products/gates.py:966-967` (`if tolerance is None: return None`) skip a policy
`maximum` on `debt_tolerance` when the caller omits the parameter and no
default exists — served at any debt. Same files, same reviewer, same defect
class as `D-IMPL-350` names. Recommended under D11: an absent constrained
parameter is a refusal, not a skip. This amends the realization of
`D-IMPL-253` Q5, under which only `required` refuses absence
(`src/ccf/products/constraints.py:171-178`, `:1077-1093`); the entry says so,
`required` stays the explicit form, and `preferred` stays non-refusing.

### 4.9 Blast radius, red-when-fixed, sabotage, close

**Blast radius, measured.** The door-test files that send a literal-year
`asked_at` through a door with a default or arbitrary door clock — 17 files /
315 test functions by `grep -rln 'asked_at.*20[0-9][0-9]-[0-9][0-9]\|ASKED_AT\s*=.*datetime(20\|asked_at=datetime(20' tests/http_api tests/mcp tests/client tests/products tests/authz tests/replay`
(files) and those files' `def test_` count (functions), re-run at the wave
open (e.g. `tests/mcp/test_egress_parameters.py:182`, `tests/products/paved_fixture.py:92`);
each declares the bound in its fixture registry and pins the door clock inside
the window — rewrite, never delete. 49 test files construct governed resolvers
(`build_governed_resolver` / `GovernedResolver(` / `open_product(`); at least
12 pin the clock (5 by `admission_clock=`, 7 more by `open_product(... clock=)`
including dict-splat forms — e.g. `tests/products/test_paved_road.py:167`,
`tests/examples/test_door_cp_05_exposure.py:153`); the other 37 are
clock-independent today only because the non-composite path reads no clock.
74 `run_gates(`/`run_federated_gates(` call sites in 24 files **under `tests/`**
(`tests/gates/test_product_gates.py` has 11 calling tests, `test_federated_gates.py`
8; the four product-gates tests at `:304/:320/:340/:352` and the federated
signature test at `:257-261` stay green); 3 in `src/`, rewritten with the gate
(`src/ccf/products/resolver.py:2879`, `src/ccf/projection/engine.py:396`,
`src/ccf/peering/admission.py:1256`) plus the docstring example at
`src/ccf/deployment/__init__.py:74`; the 5 frozen `produce.py` runners under `examples/cp-00…cp-04*`; 9
`archive/` callers (no fixes, `D-IMPL-351`); and `perf/suites/replay/conftest.py:261`
(an opt-in battery outside `ci`, so its red is silent — named). 16 example
trees call `open_product(`, 12 call `build_governed_resolver(`. Union of files
naming the changed symbols: 49.

**Red when fixed (rewrite, never delete).**
- `tests/products/test_resolver_seam.py::test_o3_a_non_composite_never_reads_the_admission_clock`
  (def at `:2861`, `assert reads == []` at `:2881`) → exactly one read.
- `::test_an_answerable_question_yields_a_served_product` (`:933`; `recorded_at
  == ASKED_AT` at `:946` **stays true** under D2(a); Gate 3 red at a wall clock
  until the fixture pins the clock).
- `::test_the_ttl_and_the_record_run_from_the_declared_decision_instant`
  (`:1059`) and `::test_a_class_declaring_no_decision_instant_still_runs_from_asked_at`
  (`:1103`) — pin the clock; the `recorded_at` assertions stay true.
- `tests/products/test_delivery_determinism.py::test_a_fulfilled_product_is_the_same_determination_twice`
  (`:467`), `::test_a_subject_unavailable_refusal_is_the_same_determination_twice`
  (`:830`) and `:486` (record address) — under a pinned clock.
- `tests/products/test_delivery_determinism.py::test_moving_asked_at_across_the_effectivity_boundary_changes_the_determination`
  (`:937`; the self-declared `D-IMPL-253` Q6 control) — rewrite so the two
  asks share one `asked_at` and pin two `served_at` values either side of
  `BOUNDARY`, asserting the policy and its pin move with `served_at` and not
  with `asked_at`; it becomes the positive control for §9 criterion 7.
- `tests/replay/test_refusal_replay_record.py:706/:725` (refusal
  record-address equality) — pinned clock.
- `tests/products/test_d_impl_341_ttl_anchor.py::test_c6_evidence_older_than_the_window_refuses_ttl_bounds_naming_the_anchored_expiry` (`:244`; the
  refusal's `now` is `ASKED_AT` at `:254` — `TTLRefusal` gains `served_at`;
  keep `now` as the decision instant) and `::test_c7…` (`:174`;
  `ttl_anchor_at == ASKED_AT == record.recorded_at` at `:182` **stays true**),
  `:352`, `:515`, `:559`.
- `tests/products/test_policy_constraint_resolver.py:403/:421/:443` — pass the
  serve instant explicitly; the documented property holds for `served_at`.
- `tests/products/test_refusal_envelope.py:431` (`TTLRefusal` fields) — by
  design; `tests/products/test_structural_gates.py:1103` stays green (no new
  token, D13).
- `tests/gates/test_product_gates.py` (11 calling tests of 15),
  `tests/gates/test_federated_gates.py` (8 of 9), `tests/examples/test_gate_two_divergence.py:261`,
  `tests/products/test_gate_independence.py:216` — the required argument.
- `tests/examples/test_s1_01_output.py::test_the_recorded_boundary_is_data_and_not_a_clock_read`
  (`:1170`; `record.recorded_at == scenario.now` at `:1181` **stays true**;
  the serve refuses as expired until the repair sitting) and
  `tests/examples/test_cp_04_canonical_output.py:216` — rows first.
- The refusal-kind pins, red by design for `TemporalBoundRefusal`:
  `tests/products/test_disclosure.py:231-232` (`EXTERNAL_STATEMENTS` /
  `PERMITTED_AT_MINIMAL` set-equality), `tests/http_api/test_product_refusal_statuses.py:204-205`
  (`STATUS_BY_KIND` set-equality), and `tests/products/test_refusal_envelope.py:1164-1176`,
  which demands a `test_envelope_for_temporal_bound_refusal` by exact name.
- Controls that must **stay green** and prove the design:
  `tests/http_api/test_product_refusal_statuses.py::test_the_route_reads_no_clock`
  (`:833`), `tests/products/test_request_contract.py::test_the_request_module_reads_no_clock`
  (`:210`), `tests/authz/test_delivery_boundary.py:793-820` (one clock in that
  module), `tests/products/test_resolver_seam.py:2830` (composite read-once).

**Sabotage.** A second clock read in the resolver → the exactly-once control
reddens. Make Gate 3 one-sided → the forward-dating control reddens (a
`from_decision` product whose declared instant is one day ahead passes a
one-sided gate and must refuse a two-sided one). Drop the policy pin from
dimension 2 → the replay test that states the admitting window reddens. Pass
`served_at` into the refusal's snapshot boundary → the refusal replay
diverges. Read the bound at the doors instead of the resolver → the in-process
door control and the composite-child control redden. Move the bound after
the acquisition seam → the zero-seam-invocation control reddens. Drop the
`PolicyBinding` from the record builder → the replay test that states the
admitting window reddens.

**Panel payload** (two stdin bundles): (1) `src/ccf/products/resolver.py`
(`__call__` region, `_decision_instant`, the record builders), `gates.py`,
`src/ccf/products/constraints.py:540-600` and `:1380-1545`, the new artifact class and refusal
contract (`src/ccf/products/refusal.py:540-600`, `:780-800`; `src/ccf/products/disclosure.py:180-200`, `:320-335`;
`runtime/ccf_runtime/http_api/refusal_status.py`), the diff and new tests; (2) `src/ccf/replay/engine.py:1180-1260` and `:1400-1445`,
`src/ccf/replay/record.py:1440-1490`, `:1995-2030`, `:500-515`, `src/ccf/products/child_resolver.py:440-480`,
`runtime/ccf_runtime/authz/delivery_boundary.py:280-320` and `:490-520`, `expiry.py`, plus the brief.
**Known findings briefed:** the four uses of `recorded_at` in §4.2; the
carve-out in §4.3 item 8; the refuse-when-undeclared example reds as rows;
prose drift at the three named docstrings.

---

## 5. Wave 3 — HITL: the signed claim set and approver eligibility

One neighbourhood (`src/ccf/hitl/*`, both HITL doors, the engine's authority
joins, the HITL policy artifacts), one adversary model (a bearer-session holder,
or an eligible-but-wrong officer, at a bank gate), one panel with the
cross-process reference root inlined. Depends on wave 1's conflicting-verdict
refusal in `_gate_authority` (the eligibility predicate layers on the same
join; the second touch is named) and on the one-clock rule wave 2's entry
states (the freshness window compares against the **recorded** door-minted
instant, never a verifier clock). It needs none of wave 2's code, so it is
sequenced after wave 2 for panel load, not as a prerequisite.

### 5.1 `SEC-005` — the signature binds the gate, the tenant, the verdict, the subject and the time

**Defect.** The signed payload is `canonical_bytes(binding)` over the
four-field `HumanPrincipalBinding` (`src/ccf/hitl/principal.py:177-180`; `src/ccf/hitl/identity_binding.py:113`),
with no protected-header assertions; the one verifier's only post-signature
check is `verified != submission.principal` (`src/ccf/hitl/transport.py:321`) and it does not
receive `authorized`; the verdict (`HitlActionRequest.action`, `src/ccf/hitl/transport.py:352`;
`HitlActionSubmission.action`, `:394`) sits beside the signature, outside it.
One signature verifies identically for `approve` and `reject`, on any event
with the same product hash, in any tenant the presenter holds a capability
for. **Wider than the report:** `trusted_keys` is a flat `kid → JWK` map and
`verify` selects by `kid` alone (`src/ccf/peering/identity.py:581`); nothing
binds a key to `approver.subject_id`, so any trusted HITL key signs as any
approver. What `D-IMPL-353` closed is the subject axis at submit
(`src/ccf/hitl/transport.py:841-848`, `PrincipalMismatchRefused`); what it created is *the
limit*: the doors mint `action_time=clock()` (`runtime/ccf_runtime/http_api/routes/hitl.py:163`;
`runtime/ccf_runtime/mcp/hitl_server.py:367`) and the signature must equal the door-minted binding, so
a production signer must predict the server's clock reading — the signed leg
works only under a deterministic injected clock, which is exactly the posture
every door test uses (`tests/http_api/test_signed_binding_door.py:67`;
`tests/mcp/test_hitl_server_door.py:128`). Recorded as an unruled follow-up in
`docs/surface-changes/353-06-…md:488-494` and nowhere in `DECISIONS.md`.

**Design.**

1. **A distinct signed claim set.** `HitlActionClaims{tenant, event_key,
   action, product_content_hash, subject_id, issued_at, nonce}` (a
   `CCFContract`, `extra=forbid`) — what the human states and what the door
   will hold it to — signed as a detached JWS through the existing `D-IMPL-15`
   provider, as `SignedHitlAction{claims, signature, key_id}`. It **replaces**
   `SignedPrincipalBinding` (§0, #4: replaced, not deprecated in place) as the
   `attestation` field on `HitlActionRequest` and `HitlActionSubmission`
   (renamed from `signed_binding`; hash-transparent at `None` so unsigned
   submissions are unchanged; the rename takes the old name out of
   `tools/lints/hash_transparent_base_roster.json:71` and CINV-06 requires the
   new field's declaration — by design, not a roster edit).
   `HumanPrincipalBinding` stays four fields and door-minted. This is an
   **amendment to `D-IMPL-21`** reference implementation #2 ("a JWS-signed
   *binding*", `docs/DECISIONS.md:31`) and to `D-IMPL-353` §1.2/§1.3 ("no
   second source for tenant/principal/resource" — the claims are compared
   against the capability, never used in its place); the entry says so.
2. **The verifier takes the capability and reads no clock.**
   `enforce_signed_binding(authorized, submission, *, identity_provider,
   trusted_keys, policy)` compares, after signature verification:
   `claims.tenant == authorized.tenant`; `claims.event_key == authorized.resource`;
   `claims.subject_id == authorized.principal == submission.principal.approver.subject_id`;
   `claims.action == submission.action`;
   `claims.product_content_hash == submission.principal.product_content_hash`;
   and, **directionally**, `claims.issued_at <= submission.principal.action_time
   + policy.permitted_clock_skew_seconds` and `submission.principal.action_time
   − claims.issued_at <= policy.signature_max_age_seconds` (an absolute delta
   would admit a claim issued after the door recorded the action). The window compares against the
   **recorded, door-minted `action_time`** (already read once from
   `deps.clock` / the MCP clock), so the check is a pure function of the
   recorded submission plus the pinned policy: `D-IMPL-69` idempotent double
   verification holds at all five sites (`src/ccf/hitl/transport.py:849-850`;
   `src/ccf/hitl/approval_gate.py:367`; `src/ccf/hitl/escalation.py:479`; `src/ccf/hitl/override.py:351`;
   `src/ccf/hitl/review_queue.py:418`), the transport site — which has no clock — verifies
   identically, and replay can re-verify. A verifier-side clock read would be
   an unrecorded input and is refused by design.
3. **`action_time` leaves the signed set.** The signer states `issued_at`;
   the door stamps `action_time` separately. This is the "signed statement
   that excludes `action_time`" the 353-06 fragment names, and it closes the
   limit: the client signs what it can see from the served queue view
   (`PendingHitlEvent`: `event_key`, `tenant`, `product_content_hash`;
   `src/ccf/hitl/transport.py:122-138`) plus its own action, subject, `issued_at` and nonce.
4. **`HitlPolicy.signature_max_age_seconds` and `permitted_clock_skew_seconds`**
   are **required** whenever `signed_binding_required` is true; unset + required refuses as broken
   wiring (the `src/ccf/hitl/transport.py:267-270` `TypeError` precedent). No SDK default
   (CINV-01). `docs/schemas/ccf.hitl-policy.json` regenerated. **`HitlPolicy`'s
   key and version are pinned into dimension 2's `policy_bindings`** (today
   zero references to it in `src/ccf/replay` or the workflow engine) — a
   record-builder change, because a policy parameter that decides admission
   must be replayable (whitepaper §7.10). **The trusted keys move into the
   pinned policy:** `HitlPolicy.trusted_keys` maps each approver subject to the
   public JWKs that may sign for it, so one pin covers keys, subjects and
   window, and replay re-verifies against the set in force (today
   `trusted_keys` is a raw map handed to the verifier,
   `src/ccf/hitl/transport.py:276-281`, pinned nowhere). **The submission carries
   the policy that admitted it:** `HitlActionSubmission.hitl_policy_ref`
   (pinned `key@version`, hash-transparent at `None`), stamped by
   `transport.submit` when a Control Plane is bound, so the submit-only door's
   recorded submission — which the engine's join consumes later — says which
   window decided its admission. The pin makes replay honest; it does not make
   admission immutable: the policy is still resolved latest at submit
   (`src/ccf/hitl/transport.py:266`), and a bearer able to register artifacts
   can widen the window before signing — the `SEC-002`-class row in §7.4, not
   closed here.
5. **Nonce.** A **seen-nonce set** keyed `(tenant, event_key, nonce)` beside
   the claim table on `InMemoryHitlTransport`, retained for the transport's
   lifetime. The claim table itself cannot carry it: `_claims` is written only
   by `remove` (`src/ccf/hitl/transport.py:765`), consumed by the first
   `submit` for the pair (`:852-853`), and never sees the submit-only door,
   which calls `submit` with no `remove`
   (`runtime/ccf_runtime/http_api/routes/hitl.py:170`). Because the submit-only door (`D-IMPL-62`) leaves
   the event pending and records N submissions (`src/ccf/hitl/transport.py:865`), "an event
   resolves once" bounds resolutions, not recorded submissions; the reference
   transport enforces single-use, a user-implemented transport stays as
   replayable as today until `HITLTransportProtocol` gains a seen-nonce or the
   claim-token residual (`src/ccf/hitl/transport.py:815-829`) lands as the `D-IMPL-62`
   amendment. **Named residual, own entry, 1.0.3** (§7.4). In the reference
   stack a restart loses pending events and submissions together
   (`src/ccf/hitl/transport.py:670-671`), so a replayed attestation after a
   restart matches no suspension; single-use that survives a restart on a
   durable transport is exactly what the Protocol amendment adds.
6. **Subject ↔ key binding.** Each entry of the pinned per-subject map (item
   4) declares the subject its key may sign for; the verifier refuses a `kid`
   whose declared subject ≠ `claims.subject_id`. Closes the wider hole
   with no second JOSE surface (the `IdentityProvider.sign(assertions=)` seam
   at `src/ccf/peering/identity.py:365` is a signed **carrier** only — `verify` compares no
   assertion — so claims live in the signed body, not the header).
7. **Codes.** `signed-binding-mismatch` (claim ≠ capability/request) and
   `signed-binding-stale` (window/nonce) beside the existing two, mapped at
   both doors (D-16 parity). `tests/http_api/test_auth_hardening.py:236`
   builds its set from five imported constants and asserts `len == 5`; it
   cannot self-redden and is **extended by hand**.
8. **One `HitlSubmit` kind.** The verdict is bound by the signature and
   compared to `submission.action`; per-verdict kinds are four-eyes machinery
   and wait for quorum (1.0.3).
9. **The CLI door is unsigned-only in 1.0.2** and the door page says so:
   `runtime/ccf_runtime/cli/commands/hitl.py` posts the document verbatim and
   has no signing; under `signed_binding_required: true` it is refused
   unconditionally today. Adding attestation arguments is a `D-IMPL-22` item.
10. **The cross-process reference root** (`tests/crossproc/servers/mcp_hitl_child.py:291-297`)
    drives `gate.resolve` with no attestation; the route Protocol carries the
    attestation by type so a signed submission at that door is not dropped.
    The MCP door today signs the binding it minted
    (`runtime/ccf_runtime/mcp/hitl_server.py:377-378`); it, the HTTP door and
    the reference root are all in the red-when-fixed set — shipping one door
    under the new shape and leaving another on the old one is the failure the
    panel is briefed to look for.
11. **Dimension 2 bytes change** for every resolution whose event carries
    `requested_by` (every engine-suspended gate, §5.2 item 4), for every
    submission stamped with `hitl_policy_ref`, and for every signed submission
    — `HitlActionRecord` embeds the whole event and submission
    (`src/ccf/hitl/approval_gate.py:160-173`) and a populated hash-transparent
    member is rendered; unchanged only for events enqueued without the field
    on an unbound transport (`cp-15`'s product record, the unbound `hitl.yaml`
    readers). The primitive enqueue sites (`submit_for_review` and its
    siblings) take the requester as an explicit argument from their caller's
    `authorized.principal`. Any golden
    record carrying a signed submission regenerates under the ruling, never by
    re-pin.
12. **Published pages.** `public/tutorial/adopters-guide.md:282` instructs
    adopters to run `sign_principal_binding` from an archived example
    (`archive/examples/05-workflow-hitl/run.py:98`); `D-IMPL-351` forbids fixing
    `archive/`, so the tutorial gets a dated note and the reference snippet is
    re-pointed at an in-tree fixture; `public/how-to/security-and-deployment.md:53-66`
    is updated to the claim-set shape.

**Rulings inside the wave-3 entry.**

| # | Question | Options | Recommendation |
|---|---|---|---|
| E1 | The signed object | widen `HumanPrincipalBinding` (A) · **distinct claims + `SignedHitlAction` (B)** · two-phase challenge door (C; new action kind; reopens `D-IMPL-62`) | **B** |
| E2 | `action_time` | stays signed (signer predicts the clock) · **`issued_at` windowed against the recorded `action_time`, no verifier clock** · a verifier clock (refuted) | **`issued_at` + window** |
| E3 | The window | `signature_max_age_seconds` + `permitted_clock_skew_seconds`, both required, no defaults, directional, pinned on dim 2 with the per-subject trusted keys · SDK default · no window (nonce only) | **required, directional, pinned** |
| E4 | Nonce | a seen-nonce set on the reference transport now + the Protocol amendment as its own entry · seen-nonce on the Protocol now (user transports change) · claim-token now | **reference transport now, Protocol 1.0.3** |
| E5 | Subject ↔ key | a per-subject trusted-key map inside the pinned `HitlPolicy` · a separate subject→kid registry · leave (any key signs as any approver) | **per-subject map in the pinned policy** |
| E6 | Codes | fold under `signed-binding-invalid` · **two new codes** | **two codes** |
| E7 | Kinds | one `HitlSubmit` · per-verdict kinds now | **one** |
| E8 | CLI door | unsigned-only, stated · attestation args now | **stated** |

**Blast radius, measured.** 14 test files under `tests/` match
`signed_binding|SignedPrincipalBinding|sign_principal_binding|verify_principal_binding`:
11 are rewritten — `tests/hitl/test_identity_binding.py` (4 of 4 tests), `test_signed_binding_authority.py`
(16 of 16; add the negatives: same signature on another `event_key`, another
tenant, opposite verdict, stale `issued_at`, reused nonce, wrong key for the
subject), `tests/http_api/test_signed_binding_door.py` (5), the four primitive
suites (3 signed tests each = 12: `test_approval_gate.py:303/339/368`,
`test_escalation.py:394/432/464`, `test_override.py:320/355/384`,
`test_review_queue.py:337/369/396`), `tests/hitl/test_transport_concurrency.py::test_d16_wired_submit_path_hammers_without_lock_ordering_issues`
(`:289`; asserts `entry.signed_binding == signed` at `:367`),
`tests/mcp/test_hitl_server_door.py:156-183` (tool argument names),
`tests/crossproc/test_mcp_tenant_authz.py:574` (body literal),
`tests/contracts/test_hash_transparency.py:350`; 1 is the code-roster test
extended by hand (`tests/http_api/test_auth_hardening.py:236`, item 7); and 2
are `archived`-marked modules — `tests/examples/test_workflow_hitl_output.py:164`
and `tests/examples/test_decision_replay_output.py:156` — that import
`verify_principal_binding` at module level **before** their `pytestmark`
line, so once `SignedPrincipalBinding`, `sign_principal_binding` and
`verify_principal_binding` are removed (they are: replaced, not deprecated)
those modules become collection errors in the default run (deselection runs
after collection, `tests/conftest.py:566-570`). Their imports are made lazy
inside the test bodies — a `tests/` edit, not an `archive/` fix — and the
archived programs they drive stay under `D-IMPL-351`. Schema drift gates:
`tests/cli/test_schema_export.py:124` and `:130`. Surface: `openapi.json` (4
references), `docs/surface/v0.2-surface.json` (12), the frozen baseline (10),
a fragment. Preserve `tests/http_api/test_signed_binding_door.py:297` as the control that
assurance is not a signable claim.

**Sabotage.** The two objects on the wire — the door-minted binding and the
client's attestation — agree **by comparison, not by inspection**: each compare
in item 2 is severed one at a time and each severing reddens its own named
negative. Remove the subject↔key check → the wrong-key negative reddens. Read a
clock in the verifier → the double-verification idempotency test and the
transport-site test redden.

### 5.2 `SEC-006` — who may approve is declared, pinned and enforced

**Defect.** `PendingHitlEvent.policy_ref` is carried (`src/ccf/hitl/transport.py:138`,
validator `:151-158`), set by four enqueue writers (`runtime/ccf_runtime/workflow/engine.py:788`;
`src/ccf/hitl/escalation.py:341`; `src/ccf/hitl/override.py:218`; `src/ccf/hitl/review_queue.py:245`) and read by no
code. The per-gate `approval-policy` the public how-to promises ("who may
approve … the approver role and the quorum") is an uninterpreted
`DeclaredArtifact` envelope. Nothing records who started an execution. Any
principal permitted to submit approves any event in that tenant, including a
request they raised. **Wider:** `_escalation_authority`
(`runtime/ccf_runtime/workflow/engine.py:1141-1152`) is a second unguarded first-match join;
`ExceptionEscalation`'s "designated role" (`src/ccf/hitl/escalation.py:23-26`) is never
enforced — seven consumption points, not six. And no cross-action exclusivity
exists: one principal may hold `Execute`, `HitlSubmit` and `Resume` and start,
approve and resume an execution alone.

**Design.**

1. **`ApprovalPolicy`** (`ccf.approval-policy`), a typed SDK class in
   `ccf.hitl`: `semver`, `eligible_principals: frozenset[str]`. **No
   `self_approval_permitted` switch, no `quorum` field and no `eligible_roles`
   field in 1.0.2** — requester ≠ approver is unconditional whenever a policy is
   bound (Dave: *no self-approval*; a policy-author switch on a ruled control is
   the caller-supplied-applicability shape), and a field nothing enforces is
   documentation, not control (Dave, on `cp-08`'s unread λ_c). Registered the
   way `ccf.hitl-policy` is — adopter-registered against the real contract,
   deliberately **not** manifest-addressable
   (`src/ccf/deployment/classes.py:64`, `:71-74`) — unless Dave rules it
   addressable. It is the artifact `gate_policies` already names and
   `_suspend` already pins onto the event (`runtime/ccf_runtime/workflow/engine.py:788`), so the posture that
   governed an approval is replayable (the deployment-wide `HitlPolicy` is
   `resolve_latest` per call, `src/ccf/hitl/transport.py:266`, and would not be).
2. **One shared helper**, `check_approver_eligibility(*, policy_ref,
   requested_by, submission, control_plane)`, beside `signed_binding_required`
   (the `D-IMPL-69` shared-helper pattern) — the transport and the primitives
   pass `event.policy_ref` / `event.requested_by`; the engine, whose
   `_gate_authority` holds no event (the primitive's atomic `remove` consumed
   it), passes `workflow.definition.gate_policies.get(gate)` and
   `record.started_by` — **dispatched on the event class** (`event.event_class`
   at the transport and primitives; the gate class at the engine): the
   approval-gate class only in 1.0.2. It resolves the policy ref through
   `resolve_pinned` (`src/ccf/controlplane/resolution.py:69`, as the factory
   already does), then refuses — typed `ApproverNotEligible`, non-enumerating —
   when `submission.principal.approver.subject_id ∉ eligible_principals`, when
   it equals `event.requested_by`, **or when `event.requested_by` is absent** on
   a bound approval-gate event (an unset requester would let the real starter
   approve; the same fail-closed posture as a missing `policy_ref`, item 3).
   Invoked at `InMemoryHitlTransport.submit` (the served doors' only path), the
   four primitives' `resolve`, and `_gate_authority`. `_escalation_authority`
   and the escalation primitive's routing artifact are of another class and are
   **logged as the named follow-on** with a pin test (§7.4), unless Dave rules
   them in.
3. **Fail-closed at both ends.** The factory refuses a **routed** `hitl-gate`
   step whose `gate_policies` target is not a `ccf.approval-policy` (a new
   class check beside the existing kind check and `_resolve_bound_ref` at
   `src/ccf/workflow/factory.py:348-359`, which today resolves the ref without
   checking its class; it mirrors the `artifact_class_of` check on the task
   ref at `:313-319`). At runtime, when a Control
   Plane is bound and an approval-gate event carries no, an unresolvable, or a
   wrong-class `policy_ref`, the helper refuses (the near-miss `TypeError`
   precedent at `src/ccf/hitl/transport.py:267-270`). Unbound (no Control Plane) keeps the
   pre-composition posture, as `D-IMPL-69` does for signed bindings.
4. **The requester is the starter.** `started_by` on `WorkflowStateRecord`
   (`runtime/ccf_runtime/workflow/state.py:103`; hash-transparent), stamped
   from the `Execute` principal, copied to `requested_by` on
   `PendingHitlEvent` at every suspension (the four enqueue sites:
   `runtime/ccf_runtime/workflow/engine.py:782-789`; `src/ccf/hitl/override.py:212`; `src/ccf/hitl/review_queue.py:239`;
   `src/ccf/hitl/escalation.py:335`). The **resumer** is a third identity — on a second
   gate `authorized.principal` at `_suspend` is the `Resume` holder
   (`runtime/ccf_runtime/workflow/engine.py:751-753`) — named in the entry but not constrained in 1.0.2.
5. **Codes:** `approver-not-eligible`, distinct, the message naming no
   eligible principal; the audit event carries the reason, the wire does not.
6. **Quorum is 1 and says so.** N-of-M cannot be reached through any
   primitive: every `resolve` atomically claims and removes the event under the
   ruled WR-02 contract (`src/ccf/hitl/approval_gate.py:372`; `src/ccf/hitl/escalation.py:484`;
   `src/ccf/hitl/override.py:356`; `src/ccf/hitl/review_queue.py:423`; `src/ccf/hitl/transport.py:546-570`), the engine
   assigns the change to a `D-IMPL-62` amendment (`runtime/ccf_runtime/workflow/engine.py:1004-1013`), and a
   quorum met only via the submit-only door would open a gate with no
   dimension-2 record of any approval. **1.0.3** (§0, #8).
7. **Roles are deferred to their own entry.** The role-source precedent
   (`ProductEntitlementSource`, `runtime/ccf_runtime/authz/product_entitlement.py:385`)
   resolves latest per call and the record pins no role-source version, so
   replay could not state the membership in force. Either a hash-transparent
   role-source pin lands with roles, or roles wait; they wait.
8. **`HitlPolicy` pin-at-composition** (a bearer able to register artifacts
   can re-issue the policy governing its own approvals) is `SEC-002`-class and
   is logged as its own entry (§7.4), not slipped into this wave.

**Rulings inside the wave-3 entry.**

| # | Question | Options | Recommendation |
|---|---|---|---|
| F1 | Where eligibility lives | typed per-gate `ccf.approval-policy`, registered like `ccf.hitl-policy` · fields on the deployment-wide `HitlPolicy` (unpinned) · interpret the untyped envelope's keys | **typed per-gate** |
| F2 | Manifest-addressable | no (the `ccf.hitl-policy` precedent) · yes (a new addressability ruling) | **no** |
| F3 | Axes in 1.0.2 | `eligible_principals` + requester≠approver · + roles via a Protocol source with a version pin · roles as an `AuthenticationClaims` axis | **principals + requester≠approver** |
| F4 | Dispatch | approval gates only; escalation join as a row · rule escalation in now | **approval gates only** |
| F5 | Posture when bound and policy-less, or requester-less | fail-closed at factory **and** runtime, including an absent `requested_by` · factory only · admit | **both, incl. absent requester** |
| F6 | Requester | starter (`started_by`) · the principal that reached the gate · starter plus every prior human actor | **starter** |
| F7 | Codes | distinct non-enumerating · reuse `principal-not-entitled` · byte-identical to the signed-binding refusal | **distinct** |

**Blast radius, measured, under `tests/`.** 7 test files bind the transport
to a Control Plane (AST: `InMemoryHitlTransport(control_plane=)` — the four
primitive suites, `test_signed_binding_authority.py`,
`test_transport_concurrency.py`, `tests/http_api/test_signed_binding_door.py`)
and go red at the transport helper: the primitive suites' events carry an
unregistered `acme-bank/approval-policy/credit-officer@1.0.0` ref
(`tests/fixtures/banking/hitl.yaml:41`; `tests/hitl/test_approval_gate.py:262-276`),
while `tests/hitl/test_signed_binding_authority.py:498-504` and the door file build
events with no `policy_ref` at all — the "no policy_ref" negatives. 6 more
(the two door-identity files, four workflow files, `test_trace_class_declared`)
construct an unbound transport and go red only at the factory class check and
`_gate_authority`, never at the transport site;
`tests/http_api/test_hitl_door_identity.py:305/:356` sit behind an unbound
conftest transport (`tests/http_api/conftest.py:340`) and are bound in the
fixture before they can redden. Under fail-closed all are rewritten to
register a typed policy. 9 files name `approval-policy` (the ninth is
comment-only; `archive/`, docs, public, perf and `.planning` carry 19 more
that do not change). Workflow fixtures' `class_id: approval-policy`
`DeclaredArtifact` registrations become typed registrations
(`tests/workflow/test_engine.py:127-139` `_register_declared`). 18
`PendingHitlEvent(` sites in 12 files (23 in 17 tree-wide) stay constructible
(the field is additive and hash-transparent); a bound approval-gate event
enqueued without `requested_by` now refuses at resolution, so the bound-plane
fixtures set it.

**Red when fixed (rewrite, never delete).**
`tests/hitl/test_approval_gate.py::test_gate_required_and_valid_binding_passes_both_layers`
and its unsigned/tampered siblings (bound plane, unregistered policy ref);
`tests/hitl/test_transport_concurrency.py::test_d16_wired_submit_path_hammers_without_lock_ordering_issues`;
`tests/workflow/test_engine.py::test_reaching_a_hitl_gate_suspends_with_a_typed_handle`
(`:487-507`) and every test through `_register_declared`;
`tests/workflow/test_engine.py::test_a_substituted_handle_cannot_turn_a_gate_into_an_ordinary_node`
(`:954`; sets `gate_policies = {}` at `:1002` — the factory now refuses
earlier; assert the earlier refusal); the policy-less idempotency tests
(`tests/hitl/test_signed_binding_authority.py:468`, `:538`) under fail-closed;
`tests/http_api/test_hitl_door_identity.py:305`, `:356` only once their
conftest transport is bound.
New negatives: a requester approving its own request; an ineligible principal;
a routed gate with no policy at construction.

**Sabotage.** Remove the eligibility call at any one of the six sites → the
site's negative reddens (each site has its own). Remove the factory class check
→ the construction negative reddens. Stamp `requested_by` from the resumer →
the self-approval negative on a second gate reddens. Re-run the four `SEC-001`
authority conditions on the merged tree: the join's per-submission predicate
(`runtime/ccf_runtime/workflow/engine.py:1037-1049`) is kept intact and eligibility refuses **inside** it, before the conflict count (§3.1 item 5). Severing the transport-site call reddens one of the 7 bound files, never one of the 6 unbound ones.

### 5.3 Wave-3 close

- Estate-gated run at base and close; `cp-15` (the HITL-composed rung) is the
  example most likely to move — ledger by node id.
- **Panel payload** (two stdin bundles, ~192 KB of HITL neighbourhood):
  (1) `src/ccf/hitl/{principal,identity_binding,transport,approval_gate}.py`,
  the new claims/policy contracts, `runtime/ccf_runtime/http_api/routes/hitl.py`,
  `runtime/ccf_runtime/mcp/hitl_server.py`; (2) `escalation.py`, `override.py`,
  `review_queue.py`, `runtime/ccf_runtime/workflow/engine.py:740-800` and
  `:930-1160`, `src/ccf/workflow/factory.py:330-370`, `tests/crossproc/servers/mcp_hitl_child.py`,
  the record-builder diff, the new tests, the brief.
- **Known findings briefed:** the seven consumption points; the wider
  subject↔key hole; the submit-only door's N submissions; the resumer as a
  third identity; the escalation join as a row.

---

## 6. Wave 4 — The erasure architecture (`SEC-009`): a decision entry and a panelled design, no code

**Why an entry first.** The immutability rule at `src/ccf/artifacts/protocol.py:19-23` says an
implementation "must never offer" an update or delete; the whitepaper commits
to logical supersession, not physical deletion (`docs/CCF_Whitepaper_1-2.md:2748`,
`:3123`) and to permanent full-fidelity retention for significant decisions
(`:3388`); it is silent on erasure. `docs/DECISIONS.md:4641` already records
that `SEC-009` "needs its own decision entry before code". Per CLAUDE.md §15 a
whitepaper-silent, whitepaper-contradicting question is a `D-IMPL` entry and a
stop. Dave's ruling (§0, #2): entry only; **panel the architecture before
anyone touches L3**.

**Deliverables.** `docs/D-IMPL-360-ERASURE-DESIGN.md` (the design) and the
`D-IMPL-360` entry, reviewed by the codex + cursor + gemini panel as a
**pre-execution design review** (the conforming shape under CLAUDE.md §3.1 when
nothing has shipped), briefed that the SDK is destined for a bank whose privacy
office will test whether bytes are destroyed. Zero code.

**The axes the entry rules, with the recommendation each carries into the
design document.**

| # | Axis | Recommendation (from the verified recon) |
|---|---|---|
| G1 | What a "subject" is | **Deployment-declared** subject classes and key paths beside `WriteKinds` (`src/ccf/artifacts/protocol.py:252-358`; mechanism only, no SDK roster — a fixed roster is the No-Hardcoding defect). |
| G2 | Replay inputs vs retained content | **Split them.** `principal_id`/`role` (`src/ccf/replay/engine.py:1425-1428` rebuilds `Perspective` from them), the request (`src/ccf/replay/engine.py:1439`; erasing it would *silently replay a different question under the decision's id*, `D-IMPL-111`), `touched_entities` (`src/ccf/replay/record.py:462`) and the approver's `subject_id` are **replay inputs** — retention-exempt or pseudonymized at write (GDPR Art. 17(3)(b) for audit actors). Admitted child contracts, child questions and annotations are **retained content** — erasable. |
| G3 | The erasure fact | An **immutable `ccf.erasure-record`** artifact class declared under `WriteKinds`, written by mechanism through `put` (the `DerivedWrite` shape, `src/ccf/replay/serve.py:264-272`): retention reason — the structural field `D-IMPL-50` ruled and never built (§1.3; nothing of it is in the tree), so the erasure record's reason vocabulary is `D-IMPL-360`'s to declare as a deployment-declared closed set under G1's rule, or `D-IMPL-50`'s lifecycle lands first under G10 — actor, `erased_at` from the injected clock, legal basis, addresses. **Never** a state-store register as authority — `ControlPlaneStateStore` is "deliberately not append-only" (`src/ccf/controlplane/state.py:278-281`) with an in-memory audit log, so erasure there is reversible and replay would read an unversioned mutable input. |
| G4 | Where the consult sits | **At the substrate read**, not the doors: eight in-process `store.get` sites bypass a door-only consult (`src/ccf/replay/engine.py:586`, `:677`, `:831`, `:1311`; `src/ccf/products/product.py:551`; `src/ccf/products/child_resolver.py:519`; `runtime/ccf_runtime/authz/delivery_boundary.py:1182`; `runtime/ccf_runtime/mcp/artifact_server.py:421`). |
| G5 | The served reading | **Disclosure-governed** through the existing `Disclosure` layer and `govern_dereference`: absent at minimal, erased-with-reason at higher levels, **always positive in replay** — at the child-question site and the request-seeds site (`src/ccf/replay/engine.py:1439`) as a refusal distinct from "never carried a request". |
| G6 | Authority | A new door kind `artifact.erase` (beside `artifact.write`, `src/ccf/authz/actions.py:64`) minted at gate/wrapper only, **behind a policy-configurable `ApprovalGate`** with the approver in the record — an irreversible Control Plane action of a revoke's weight. Never composition-minted. |
| G7 | Legal hold and severity-exempt records | **Per-class Control Plane policy, default refuse**, with a structural retention-reason field (INV-CH7-89) — the refusal is the audit answer a regulator asks for. |
| G8 | The graph | **Outside the 1.0.2 contract, named** (the `D-IMPL-355` form): six backends, five persistent, only Fluree append-only (`src/ccf/graph/backends/fluree_write.py:403-428` emits retracts that remain in history); `PolicyFilter` reads attribute plaintext (`src/ccf/operators/categories.py:280`), so attribute-level encryption would fail it closed; `cp-15` puts natural-person KYC data in the graph. CDC turns an upstream DELETE into a permanently retained before-image (`runtime/ccf_runtime/cdc/envelope_map.py:19-22`, `:158-161`): a retention event, not an erasure signal — recommended, to be ruled at G8. The file store's append-only `.artifact-names.json` (`src/ccf/artifacts/file_store.py:66`, `:140-150`) is inventoried. |
| G9 | Rulings this amends | `D-IMPL-27`'s explicit class list (`docs/DECISIONS.md:37` routes replay records and Context Products at rest through the ArtifactStore) for whatever leaves the store; key custody, if crypto-shredding is ever ruled for the graph, on the existing `SigningKeySource` / `FileBackedKeySource` seam (`src/ccf/peering/identity.py:315`, `:410`), never a second key provider; a durable state store is a `D-IMPL-18` deliverable, not a side effect. |
| G10 | Sequencing | The entry and the design in 1.0.2; the substrate (erasure record class, the door kind, the substrate consult, the ApprovalGate) as its own panelled phase after 1.0.2; payload separation for artifacts and any graph erasure as later phases; and the honest statement that until bytes are destroyed nothing here satisfies Art. 17 destruction. |

Wave 4 changes no example-reachable code; the estate-gated run is not repeated
at its close, and its panel reviews the design as prose.

**Red when fixed, for the later code phase, recorded now so it is not
re-derived:** `tests/conformance/test_artifactstore.py::test_the_store_offers_no_mutation_or_removal_surface`
(`:280-285`) must keep asserting the artifact store has no removal verb while
the erasure record and the consult live beside it; the seven stub stores
implementing `resolve_uri` fail `mypy --strict` if the Protocol gains a method;
the golden record fixture (`tests/replay/test_golden_13bd250.py`) regenerates
only under a ruling.

---

## 7. Ledgered in 1.0.2, not built

### 7.1 `D-IMPL-361` — the harness-adapter findings are HIGH; the first 1.0.3 wave

**Ruling (Dave, §0 #1):** `TP-01`…`TP-05` are rated **HIGH** in the ledger.
The recon's own severities are recorded beside the ruling so the reasoning is
auditable, not so it competes with it: `TP-01` HIGH (a "read-only" binding
dispatches every skill; the vendor now documents and warns about exactly this
shadowing), `TP-02` HIGH (the fabric's entire environment reaches the `claude`
subprocess; `options.env` merges **over** the inherited environment and
cannot subtract), `TP-03` HIGH (a `peering` skill rendered as a harness tool
hands unadmitted peer products to the model and drains the queue the real
admission gate reads — the only one of the five that bypasses a structural
CLAUDE.md §7.2 commitment), `TP-04` MEDIUM (the ADK leg drops every
model-supplied argument and audits `{}`; a non-functional leg in a tagged
release), `TP-05` MEDIUM on an isolated host and HIGH wherever argv is
centrally audited — the bank case.

**Verified facts that shape the 1.0.3 wave, recorded now.** (a) The vendor
routes CLI `tools/call` straight to the in-process handler with no
Python-side permission check (`claude_agent_sdk/_internal/query.py:499-511` (vendor, claude-agent-sdk 0.2.128 in the pinned venv),
`:679-688`): `allowed_tools`, `can_use_tool` and a `PreToolUse` hook are all
enforced by the semi-trusted CLI, so the **only adapter-owned control on the
Claude leg is inside the in-process handler**
(`runtime/ccf_runtime/adapters/claude_agent/adapter.py:196-202`); CLI-side
gates are defense in depth. (b) The conformance suite is green on `TP-01` and
`TP-04` only because the refusal drivers call the gate function directly with
`args={}` (`tests/conformance/test_harness_adapter.py:483-495`) — a false green
that becomes the red-when-fixed inversion. (c) Refusing a `peering` tool-style
call in `Agent.invoke_skill` is **foreclosed** by Dave's 2026-07-27 ruling
(`src/ccf/agents/agent.py:387-401`; `src/ccf/agents/factory.py:276-286`; PHASE_I3_GATE row 19)
and would redden `tests/integration/test_agent_slice.py:534/563/583`; the
seam is `render_tool_surface` (`src/ccf/skills/toolsurface.py:68-91`), which
already refuses `procedure` by type (`D-IMPL-56`) — widening it to `peering`
and `mcp_product` fixes `TP-03` **and** a live crash (no adapter catches
`ProcedureHasNoToolSurface`, so a bound `procedure` skill makes `_tools()`
raise on all three legs today). (d) `TP-02`'s options half is S and
vendor-public (`tools=[]`, `skills=[]`, `setting_sources=[]`,
`strict_mcp_config=True`, `cwd`, `max_turns`); its env half rides on a
private vendor module (`SubprocessCLITransport`) and is a ruling — one the
in-tree precedent cuts against: `hw1`'s three clients pass `env=dict(os.environ)`
deliberately with a recorded reason (`examples/hw1-harness-clients/client_anthropic.py:160`:
"a child handed a trimmed environment has already cost this repository one
defect"; `examples/hw1-harness-clients/client_adk.py:160`; `examples/hw1-harness-clients/client_langgraph.py:131`). (e) `TP-04`
and `D-IMPL-353` residual R4 (`SEC353-J-01`, FastMCP drops unknown wire
arguments) are one defect class and get one rule. (f) `TP-05`'s file-form
prompt (`--system-prompt-file`, present in the bundled CLI) changes what the
harness-portability probe walks (`tests/conformance/test_harness_portability.py:239-262`,
`:464`; 15 nodes). (g) `D-IMPL-25`'s "required iff the bound agent has a
non-empty skill-set" must be re-read as "non-empty **exposable** skill-set".

**The 1.0.2 release condition on these findings (Dave, `D-IMPL-356`).** *"A
TP-01…TP-05 finding may be deferred to 1.0.3, but an enabled path known to
violate its security contract must not be represented as a supported-safe
1.0.2 path merely because remediation is deferred."* The 1.0.2 release record
(§8.2) states, for each of the five, exactly one of: **supported and not
affected**; **restricted or disabled from the supported surface**; **known
limitation explicitly outside the supported 1.0.2 contract**. The
determination is made at qualification against the shipped adapters, not
assumed here; a finding whose enabled path still violates its contract cannot
take the first status.

**The 1.0.3 ruling sheet** (not ruled here): the `D-IMPL-25` reading of
`effects: unsupported` (no dispatch and no write-back, recommended); the
harness-exposable roster `{tool, mcp, local_callable}`; the env control
(deployment obligation vs private-module transport subclass vs vendor
request); `TP-05` delivery (file-form prompt, 0600, carrier-owned directory,
recommended); the unknown-arguments rule (declared pass, undeclared refused,
on ADK and FastMCP); required vs defaulted `cwd`/`max_turns`/`environ`
kwargs (`public/how-to/bind-a-harness-adapter.md:30` runs `archive-03`'s
constructors and goes non-runnable under required kwargs — a dated note under
`D-IMPL-351`, not a fix); and the stdio composition control (§7.3). Zero example reds predicted
(`grep` over `examples/` for the adapter symbols returns nothing).

### 7.2 `SEC353-G-09` — the eight crashed doors

Written in wave 1 (§3.5). Not unfrozen (§0, L2).

### 7.3 The "one identity for every caller" transports (`EX-03`, `EX-04`)

`ProductDoor.serve_stdio` pre-sets one identity for every caller
(`runtime/ccf_runtime/mcp/product_door.py:240-268`); the only reachable multi-principal stdio
composition on `main` is the SDK's own `open_door_with_verifier(...).serve_stdio()`
(`:384-421` → `_compose` `:486-500`), which no shipped example uses; `serve_loopback`
over the same composition is the legitimate multi-principal transport
(`:34-35`). There is no Protocol-conforming way to count a verifier's
principals (`TokenVerifier` is FastMCP's Protocol, `runtime/ccf_runtime/mcp/auth.py:274`;
`TokenSourceProtocol` has only `grant_for`, `:205`). In 1.0.2 the SDK door page
discloses the posture (§3.3 item 7). The control — a `TokenSourceProtocol`
enumeration member with a by-name refusal bound in `serve_stdio` only, or
removing `serve_stdio` from `ProductDoor` so adopters compose
`ambient_stdio_identity` at the call site as `hw1` does — is designed with the
adapters in 1.0.3, because it is the same boundary class. `cp-22`'s
plain-HTTP A2A server with a fixed principal (`examples/cp-22-agent-internal-assembly/agent_b.py:297-317`,
`:157`) is the frozen exemplar.

### 7.4 Rows opened by these waves (each its own entry or ledger row; none is code in 1.0.2)

| Row | Opened by | What it is |
|---|---|---|
| Escalation verdict→retry sibling | §3.1 | `runtime/ccf_runtime/workflow/engine.py:1083-1087`; unpinned at the engine level; needs a pin test and a ruling on what a rejected escalation routes to. |
| Removing `decision` from `resume` | §3.1 | The seam-clean shape A3(b); five public surfaces; own wave, own panel. |
| L2 partial admission | §3.2 | One transaction per claim; a refused envelope leaves its predecessors written. |
| Bitemporal as-of read | §4.3 (8) | Valid-time `asked_at`, transaction-time `served_at`; INV-CH7-03/14. |
| L2 clock guard (only if D6 is ruled (a)) | §4.3 (8) | `ingest` / `ingest_admitted` for long-lived fabrics; replay/re-hydration exempt by construction. Ships in wave 2 under (d). |
| `served_at` always-omitted posture | §4.3 (4) | Decided: addressed once populated. An always-omitted audit carrier would need a `D-IMPL-243` amendment (exactly three key states exist); revisit only if the qualification census argues for it. |
| `HITLTransportProtocol` nonce / claim token | §5.1 (5) | The `D-IMPL-62` amendment; user transports. |
| CLI attestation arguments | §5.1 (9) | `D-IMPL-22`. |
| `_escalation_authority` eligibility | §5.2 (2) | The second unguarded join; the escalation routing artifact's class. |
| Quorum (N-of-M) | §5.2 (6) | The WR-02 claim-and-consume amendment; 1.0.3 (§0, #8). |
| Role-based eligibility | §5.2 (7) | Needs a version-pinned role source on the record. |
| `HitlPolicy` pin-at-composition | §5.2 (8) | `SEC-002`-class. |
| Per-verdict `HitlSubmit` kinds | §5.1 (8) | Four-eyes machinery; with quorum. |
| The resumer as a constrained identity | §5.2 (4) | Named, not constrained. |
| Cross-action exclusivity | §5.2 defect | One principal holding `Execute` + `HitlSubmit` + `Resume`; a scope-mapping question. |
| `ccf` → `ccf-sdk` distribution rename | §3.4 (3) | If the PyPI name is claimed after wave 1. |
| Producer-side `asked_at` deferral | §4.3 (7) | `asked_at := served_at` inside `__call__` via a request sentinel; needs the `D-IMPL-158` amendment for the MCP tool; `D-IMPL-159`'s own control stays the pin. |
| `EligibilityEvidencePolicy` unpinned | §4.3 (5) | Resolved latest with the version discarded (`src/ccf/peering/eligibility.py:425-431`); the same class as the `HitlPolicy` pin; own entry, or fixed on the peered-child path in wave 2. |
| `D-IMPL-50` retention lifecycle | §6 | Ruled, never built; the erasure record's reason vocabulary depends on it or supersedes it (G3). |
| Workflow-definition hash on the replay record | §3.1 | Only `agent_definition_hash` is carried (`src/ccf/replay/record.py:877`); the definition hash lands on the audit event only (`runtime/ccf_runtime/workflow/engine.py:1228`), so "which artifact routed this rejection" is not answerable from replay alone. |
| Durable L2 refusal recording on the CDC / federated / ingest doors | §3.2 | The canonical path records `IdentityRefused`; the other ingress doors raise it unrecorded. |
| Audit-log persistence of approver identities | §6 | In process memory today (`src/ccf/controlplane/audit.py:286-288`); `D-IMPL-18`-adjacent. |
| `SEC-022` A2A replay (iat / jti / nonce) | §5.1 | Shares the `SEC-005` claim-set template (signed statement + `issued_at` + nonce + window against a recorded instant); its own row after wave 3. |
| Carried from `D-IMPL-353` | `D-IMPL-355` | R1–R5, R7–R10; `SEC353-G-01`…`G-08`; `D-IMPL-354` readings (A)/(B)/(C); `D-IMPL-348`. |

---

## 8. Release mechanics

### 8.1 The form (`D-IMPL-355`, repeated exactly, with the branch strategy stated)

0. **Branch strategy.** Each wave's `D-GATE-357` / `-358` / `-359` merges its
   wave branch `--no-ff` into `main` (CLAUDE.md §2.2), so the estate-gated
   run, the sabotage and the panel of every wave read the merged tree, and
   each wave's base is `main` at the previous gate. `D-GATE-360` (the erasure
   entry and its design review) closes **before** step 1 begins, so the tagged
   tree carries `D-IMPL-360`.
1. After `D-GATE-360`, qualify `main` in a **fresh detached worktree** with
   its own venv (the demo adapter installed; extras alone fake 40 nodes);
   verify the tree hash equals the freeze hash before and after every phase.
   Red → RELEASE HOLD, narrow repair ruled by Dave on a repair branch, and the
   repair is never a frozen-family edit.
2. MERGE GO, **only for a HOLD repair branch**: `--no-ff` into `main`; the
   merge tree verified equal to the candidate tree before the push. With no
   hold, step 1's `main` is the candidate.
3. Fresh qualification of the candidate → RELEASE GO → TAG GO. Annotated
   tag `v1.0.2`. `v1.0.0` and `v1.0.1` are not moved; nothing is retagged;
   history is not rewritten.
4. Evidence filed **after** the tag under `qualification/<sha>/` (README,
   `evidence.tar.gz`, any hold record), not in the release tree.

### 8.2 The board of record

Everything v1.0.1's board carried (`qualification/a4cf2fb7/README.md`): the
focused suites; every named severing observed RED on its named control and
restored byte-for-byte; canonical `make test` in the census posture with
`passed` / `failed` / `errors` / `skipped` / `xfailed` as four numbers plus the
exact failing node-id census; typecheck; lint; public-surface `--check` twice;
product gates (trees / declared / executing); docs-strict, schema drift,
assembler, docs tests, publish-scan; replay suite, DR-01, DR-02; the five live
legs (Fluree on an empty instance, Mongo, Neo4j, Postgres, the CP-03 live
prerequisite); curated-estate watermarks before and after, zero movement.
**Plus, new for 1.0.2:**

- **The estate-gated run** (§8.3), at each wave close and at qualification.
- **The version gate** (§3.4): `importlib.metadata.version(SDK_DISTRIBUTION)`
  in the qualification venv equals `1.0.2`; a freshly built wheel's metadata
  says `1.0.2`; a record produced in that venv carries `graph_adapter_version
  == "1.0.2"`.
- **Per-wave panel dispositions** (three waves plus the erasure design
  review), each finding and each retraction verified against the tree, in
  `docs/V1.0.2-CLOSE-REVIEWS.md`.
- **The adapter status table** (`D-IMPL-356`): one row per `TP-01`…`TP-05`
  stating *supported and not affected* / *restricted or disabled from the
  supported surface* / *known limitation outside the supported 1.0.2
  contract*, with the evidence for the row; no enabled path known to violate
  its security contract is represented as supported-safe.

### 8.3 The estate-gated example nodes

v1.0.1's canonical run skipped **660** example nodes by design (no
`CCF_TEST_*`, no `CCF_CP_*`): they did not pass; they were not run. Wave 2
predicts about 25 example trees red and wave 1 ledgers 8 doors already red;
none of that is observable without the estate. So, per Dave (§0, #7): at each
wave base, each wave close and at qualification, export the `ccf_dataprep`
connection material against the **v2 namespaces** (`fibo-v2` / `ccf_v2` /
`fibo_v2` on `192.168.4.76` — never the `.env`'s v1 names) and run them
**read-only**; any seed goes to the `CCF_TEST_*` local containers and
`estate_guard` refuses curated hosts. Every red is ledgered by node id and
classified: pre-existing at the wave base / new under the wave / already
ledgered. A red that is new under a wave is an SDK finding or a row before it
is anything else (`D-IMPL-261`). The watermarks are recorded before and after
every run.

### 8.4 The tag text

The annotated `v1.0.2` tag carries the **security-review map**, which v1.0.1's
tag did not:

- Closed in 1.0.2, by entry, each with its residual named where one exists:
  `SEC-001` residual (`D-IMPL-357`); `SEC-007` (`D-IMPL-357`); `EX-01`/`EX-02`
  root cause, **the shape half** (`D-IMPL-357`; the floor is necessary, not
  sufficient, for an adopter who concatenates); `SEC-029` (`D-IMPL-357`);
  `SEC-010` (`D-IMPL-358`); `SEC-011` Gate 3 (`D-IMPL-358`), with Gate 2
  recorded NOT-A-GAP as **assembly-path integrity, not an independent forgery
  witness** (`D-IMPL-86`/`300`); `SEC-019` (`D-IMPL-358`); `SEC-008`
  (`D-IMPL-358`): the served/audit half closed, the write half closed for
  governed ingress and deployment-authored envelopes under D6 (d) — or, under
  D6 (a), **OPEN and carried**, never "bounded"; `SEC-005` (`D-IMPL-359`),
  single-use that survives a restart on a user transport carried as the
  `D-IMPL-62` amendment; `SEC-006` (`D-IMPL-359`) as **single eligible
  approver and no self-approval** — not a four-eyes regime: N-of-M, roles, the
  escalation join and cross-action exclusivity are carried.
- Closed before 1.0.2: `SEC-001`, `SEC-003` (`D-IMPL-350`); `SEC-002`,
  `SEC-004`, `SEC-012`, `SEC-016`, `SEC-018` (`D-GATE-353`).
- Entered, not built: `SEC-009` (`D-IMPL-360`); `TP-01`…`TP-05` rated HIGH
  (`D-IMPL-361`), each carrying its `D-IMPL-356` status — supported and not
  affected / restricted or disabled / known limitation outside the supported
  1.0.2 contract — and none represented as supported-safe while its enabled
  path violates its contract.
- Open: `SEC-013`, `SEC-014`, `SEC-015`, `SEC-017`, `SEC-020`–`SEC-028`
  (`SEC-027` being Dave's PyPI action); quorum, roles, the rows in §7.4; `EX-03`, `EX-04`,
  `EX-07`–`EX-10`; `SEC353-G-01`…`G-09`; the `D-IMPL-353` residuals.
- The threat model sentence from v1.0.1 (governed served surfaces; in-process
  Python outside), unchanged.

---

## 9. Success criteria (each verifiable; each is a test, a gate, or a record)

1. A recorded `reject` cannot resume down a non-rejected route: the rewritten
   pin asserts `WorkflowResumeRefused` with the gate still suspended and audit
   `actor=None`; severing the compare reddens it. Two conflicting verdicts on
   one suspension refuse through `POST /hitl/actions` + `POST /workflow/resumptions`.
2. Two null-identity envelopes through `AssemblyWorker.ingest` produce two
   `IdentityRefused` and zero entities **and** zero relationships; the paved
   road records the refusal as a governed determination with a replay record.
3. A subject carrying `"` or `'`, a 513-character subject, and a `type: string` argument carrying `<` each refuse
   as a governed `ProductRequestViolation` at the in-process, MCP and HTTP
   doors before any acquisition runs, with a replay record; a
   `PolicyConstraintResolver` override does not remove it; a declared
   `pattern` cannot widen past the floor.
4. In the qualification venv, `importlib.metadata.version(SDK_DISTRIBUTION)
   == "1.0.2"` and a freshly served record's `graph_adapter_version == "1.0.2"`;
   the tag text carries §8.4.
5. `GovernedResolver.__call__` reads its clock **exactly once** per serve
   (AST or spy control) on the non-composite and composite paths; Gate 3
   refuses a product with `expires_at <= served_at` **and** one with
   `expires_at > served_at + MAX_TTL`; a peered child and an in-process child
   are judged at the same instant; the composite mixing law judges remaining
   validity at `served_at`.
6. A question outside the tenant's declared temporal bound refuses by name
   with a replay record; a tenant with no bound refuses by name; the admitting
   bound's key and version appear in dimension 2 (minted by the record
   builder; severing the builder site reddens the replay test); an out-of-bound
   question invokes the acquisition seam zero times; under D6 (d), an envelope
   stamped outside the window is refused at L2 and the paved road's
   per-question stamp is not.
7. A constraint effective after `asked_at` but before `served_at` applies to
   the served product (the rewritten Q6 control at
   `tests/products/test_delivery_determinism.py:937`); replay of that record
   reproduces its address and its bindings.
8. Every pre-1.0.2 golden record (`tests/replay/fixtures/golden_13bd250`)
   rehydrates to its recorded address unchanged.
9. A signature presented on another `event_key`, another tenant, the opposite
   verdict, past the window, with a reused nonce (on the reference transport),
   post-dated beyond the declared skew, or under a key not declared for its
   subject in the pinned policy refuses with `signed-binding-mismatch` / `-stale` at both
   doors; a signed submission succeeds under a **wall clock** on both doors
   (the 353-06 limit is closed); `HitlPolicy`'s key and version appear in
   dimension 2.
10. A requester's own approval refuses; a principal outside
    `eligible_principals` refuses; a routed gate with no `ccf.approval-policy`
    refuses at construction; a bound gate whose `policy_ref` does not resolve
    refuses at runtime; a bound approval-gate event with no recorded requester
    refuses; the four `SEC-001` authority conditions still hold on the merged
    tree.
11. Each of waves 1–3 closed with a codex + cursor + gemini panel on inlined
    source; every finding and retraction verified against the tree; zero
    unverified findings acted on; the erasure design reviewed by the same
    panel before any code exists.
12. The estate-gated nodes executed at each wave close and at qualification;
    every red carries a ledger row by node id with its classification; the
    curated estate's watermarks unchanged.
13. `D-IMPL-360` ruled on all ten axes; zero code under it in the tree.
14. `D-IMPL-361` rates `TP-01`…`TP-05` HIGH and names the 1.0.3 ruling sheet;
    the release record carries the adapter status table (§8.2) with one of the
    three `D-IMPL-356` statuses per finding, evidenced at qualification.

---

## 10. Decision ids (provisional; the planner allocates at entry-writing time)

| Id | Entry |
|---|---|
| `D-IMPL-356` | **Written 2026-09-25:** this document accepted at `cb319661`; the eight rulings and two locks of §0; A1–G10 locked; the adapter release condition; the compatibility restatement. |
| `D-IMPL-357` | Wave 1: §A verdict→target (A1–A5), §B identity admissibility (B1–B5, amending `D-IMPL-347` B2 for SDK-raised seam classes), §C request-value shape (C1–C6 incl. C1a, amending `D-IMPL-264` D-03), §D version stamp and tag map. |
| `D-IMPL-358` | Wave 2: the fabric clock (D1–D13), amending `D-IMPL-253` Q6, Q23 and Amendment 3(3) (`served_at` is addressed content), Q5's realization (D11), and the `D-IMPL-308` Gate-3-at-decision reading (D3) while keeping its fallback (D4); carrying `D-IMPL-159` as a bounded residual (D7); recording `SEC-011` Gate 2 NOT-A-GAP; the `SEC-019` rider; the `SEC-008` follow-on rows. |
| `D-IMPL-359` | Wave 3: the HITL claim set (E1–E8), amending `D-IMPL-21` #2 and `D-IMPL-353` §1.2/§1.3; approver eligibility (F1–F7). |
| `D-IMPL-360` | `SEC-009` erasure architecture (G1–G10); design at `docs/D-IMPL-360-ERASURE-DESIGN.md`; no code. |
| `D-IMPL-361` | Adapters `TP-01`…`TP-05` rated HIGH; the first 1.0.3 wave and its ruling sheet; the stdio composition control. |
| `D-GATE-357` / `-358` / `-359` / `-360` | Each wave's close by Dave. |
| `D-IMPL-362` | The v1.0.2 release record (the `D-IMPL-355` form). |

Ids from `D-IMPL-363` are free. Rows in §7.4 are minted when opened.

---

## 11. What this document does not decide

- The per-wave sub-rulings (A1–A5, B1–B5, C1–C6 with C1a, D1–D13, E1–E8,
  F1–F7, G1–G10). Each carries a recommendation; each is Dave's at the wave's
  opening, or at acceptance of this document if he rules them here.
- The roster of "living reference trees" for the wave-2 repair sitting (D12).
- Whether `ccf-sdk` on PyPI is claimed (§3.4 item 3) — a check, not a design.
- The 1.0.3 ruling sheet (§7.1) and the rows in §7.4.
- Anything in §1.2.

*Written 2026-09-25 from the 32-agent recon of `main` @ `a5b0f691`; every
citation resolved on that tree. Superseded line numbers are a defect in this
document, not in the finding.*
