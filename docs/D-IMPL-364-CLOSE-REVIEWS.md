# `D-IMPL-364` — SEC-008 / SEC-010 / SEC-011 twelve-clause repair: CLOSE PANEL reviews

**Subject: the SHIPPED TREE.** Candidate `beb0c717a0922b7478fec48242002ce7d3e38694` on branch
`repair-d-impl-364-clauses`, base `4f15a7f375cd0dd80da725b7a045fccc93e37207` (= `main` = `origin/main`
at review time, unchanged). Commits under review: `2553fc70` (RED — the twelve clauses' tests, no
production change) and `beb0c717` (GREEN — production, disclosure and assurance pages, one docs-test
hardening, one re-cite). Panel GO given by Dave on 2026-10-04 (14:08 MST): panel review only.

**Judged against** the per-row acceptance criteria recorded verbatim at `D-IMPL-364` in
`docs/DECISIONS.md`, with Dave's correction that SEC-008 A1 covers the bounded `asked_at`, the pinned
policy, the named refusals and zero seam invocations, while the single `served_at` clock read is
SEC-010 A1.

**Every reviewer and seat was told the SDK is destined for a BANK** and to be more conservative than
for ordinary code. No seat or reviewer connected to `192.168.4.76`.

**What this record does NOT do:** no merge, no tag, no release, no SEC closure. The two repairs it
records are docs: the two-cell register fix Dave authorized after reading the panel's report
(section 4.1) and the docs completion the two SEC-008 rulings call for (section 4.2). Neither is a
production behavior change. The ledger stays 9 of 29 and SEC-008, SEC-010 and SEC-011 stay OPEN;
the sequence is finish → verify → merge decision → separate closure decision.

## 1. The first sitting is SUPERSEDED: its payload was missing the rulings and the diff

The panel sat twice. The first sitting (before a GPU failure and reboot at ~14:40 MST) sent codex,
cursor and gemini a 525 KB inlined payload in which SECTION B (the `D-IMPL-364` and `D-IMPL-365`
ruling text) and SECTION C (the GREEN diff) each read `cat: ... No such file or directory` — the
builder's read of a not-yet-written file printed its error into the payload and the shell carried on.
The reviewers had been instructed to judge V5 "against the ruled criterion text in SECTION B" and Q10
against "the GREEN diff (SECTION C)".

- **cursor** listed both sections as "Unreviewed (not inlined)".
- **codex** did not mention the gap.
- **gemini** wrote "Q10. Checked SECTION C; no behavior changes beyond the intended seam map entry
  were found." The section was empty. Recorded as a fabricated claim of reading.

**The three first-sitting reviews are superseded by the second sitting's.** They are preserved
(section 10) for one finding they produced that is real — the `ReferencePolicyConstraintResolver`
docstring residue, carried below as advisory — and for the record of what each reviewer did when a
section was absent.

The second sitting (15:14–15:40 MST) used a corrected 606 KB / 9,783-line payload: the same SECTIONS
A and D–H, plus SECTION B (both rulings verbatim with their `docs/DECISIONS.md` line numbers), SECTION
C (the GREEN diff, numbered), and three known-finding briefs K8–K10 carrying the first sitting's
confirmed findings so that budget went to what was adjacent. Read-proof canaries passed on all three
CLIs over stdin before launch. The payload was checked for every announced section before launch.

## 2. Reviewer seats and evidence status

Two kinds of evidence are kept apart throughout: **INSPECTED** (the reviewer read the inlined source
or its worktree) and **INDEPENDENTLY EXECUTED** (the seat ran tests, probes or severings itself in its
own detached worktree at the pin and captured the output). "Reported" means evidence captured by the
author's session and not re-executed by that seat. Every executing seat printed `ccf.__file__` under
its own worktree before any result, and left its worktree byte-clean afterwards.

| seat | model / tool | subject | evidence | disposition | findings |
| --- | --- | --- | --- | --- | --- |
| **codex** (2nd sitting) | codex-cli 0.137.0, `gpt-5.5`, reasoning high, read-only sandbox | corrected payload on stdin | INSPECTED (177,177 tokens read) | SEC-008 PROCEED · SEC-010 **HOLD** · SEC-011 PROCEED | 1 BLOCKING (rejected by execution, section 3.2), 0 advisory |
| **cursor** (2nd sitting) | cursor-agent 2026.10.01, `--mode ask` | corrected payload on stdin | INSPECTED | PROCEED · PROCEED · PROCEED | 2 ADVISORY |
| **gemini** (2nd sitting) | gemini CLI, `GOOGLE_API_KEY` | corrected payload on stdin | INSPECTED | PROCEED · PROCEED · PROCEED | 0 (one false Q10 claim, section 8) |
| **reader** | Claude Opus 5 subagent, no session context | all 9,783 payload lines; read-only grep of a worktree at the pin | INSPECTED | PROCEED · PROCEED · **HOLD** | 2 BLOCKING (both confirmed), 7 ADVISORY |
| **accept** | Claude Opus 5 subagent | its own worktree at the pin | **INDEPENDENTLY EXECUTED** | all gates as reported | 0 |
| **sever** | Claude Opus 5 subagent | its own worktree at the pin; a copy of the author's driver with only its path changed | **INDEPENDENTLY EXECUTED** (17 severings + broad-suite and traceback reruns + 8 own probes) | — | 2 BLOCKING (the same two rows), 7 ADVISORY |
| **b1** | Claude Opus 5 subagent | its own worktree; AST walk over `src/` and `runtime/`; planted bypass shapes | INSPECTED + **INDEPENDENTLY EXECUTED** | — | 1 proposed BLOCKING (an owner question, section 9), 3 ADVISORY |
| **b3** | Claude Opus 5 subagent | its own worktree; an independent route probe and a map-entry sabotage | **INDEPENDENTLY EXECUTED** | — | 5 ADVISORY |
| **s010** | Claude Opus 5 subagent | its own worktree; real-route instrumentation of a composite serve; three severings | **INDEPENDENTLY EXECUTED** | — | 5 ADVISORY |
| **s011** | Claude Opus 5 subagent | its own worktree; sabotage of the binder, the consumer check and Gate 1; five register-audit mutations | **INDEPENDENTLY EXECUTED** | — | 1 BLOCKING (confirmed), 4 ADVISORY |
| **ratchet** | Claude Opus 5 subagent | worktrees at the pin and at the base | **INDEPENDENTLY EXECUTED** | — | 0 |

The executing model (Claude Fable 5.1, the author of the candidate) is excluded from every seat
above; it assembled the corrected payload, verified every finding and every rejection against the
pinned tree by execution (section 5), and wrote this record.

## 3. Findings — verified against the pinned tree before being recorded

### 3.1 BLOCKING — SEC-011 C2: two register rows cite a test that does not redden the control

C2 requires the register to map each control "to the path on which each can fail and the test that
reddens it", and the page's own first paragraph promises "which test turns red when it is removed".
Two of its ten rows did not:

1. **The binder row** cited
   `tests/products/test_gate_two_call_shape.py::test_the_tripwire_detects_the_shape_it_exists_to_refuse`
   and `tests/products/test_gate_two_call_shape.py::test_the_binder_tripwire_detects_a_projection_that_skips_it`,
   both AST tripwire meta-tests over synthesized source that never execute
   `src/ccf/deployment/binder.py::refuse_operator_set_divergence`. EXECUTED (s011 seat, sever seat,
   and the executing model): with the binder's comparison severed to never refuse, the two cited
   tests pass; `tests/deployment/test_binder.py::test_one_edited_operator_key_in_one_document_is_refused`,
   both parametrizations of `tests/deployment/test_binder.py::test_a_superset_and_a_subset_are_both_refused`,
   `tests/deployment/test_binder.py::test_a_plan_that_ignores_its_requirements_artifact_is_refused`
   and (broad run) `tests/products/test_resolver_seam.py::test_a_plan_contradicting_the_class_is_refused_before_it_is_executed`
   go red. Found by the s011 seat (sabotage), the reader (reading) and the sever seat (sabotage),
   independently. This is the row the register and the C1 passage use to say where Gate 2's real
   work is done.
2. **The `ttl-anchor-unresolvable` row** cited
   `tests/products/test_d_impl_341_ttl_anchor.py::test_c6_evidence_older_than_the_window_refuses_ttl_bounds_naming_the_anchored_expiry`,
   whose assertions are that the refusal kind is `ttl-refusal`, the reason is `GATE_TTL_BOUNDS`,
   and the kind is NOT `ttl-anchor-refusal` — a Gate 3 control, the same test the ruling lists as
   SEC-011 A1 evidence. EXECUTED (executing model; sever seat on one branch): with both
   `gate=GATE_TTL_ANCHOR` mint sites in `src/ccf/products/expiry.py::resolve_ttl_anchor` severed to
   the bounds token, the cited test passes and
   `tests/products/test_d_impl_341_ttl_anchor.py::test_c5_a_served_set_with_no_source_instant_refuses_by_its_own_reason`
   reddens. Found by the reader and the sever seat independently.

Disposition: **repaired on this branch under Dave's scoped GO** (section 4). The other eight rows were
confirmed to collect and pass; the consumer-side row was sabotage-checked (`src/ccf/agents/agent.py::Agent`'s
expiry check severed → its cited test red); the remaining rows were read, and each cited test asserts
its own token or refusal type.

### 3.2 REJECTED as blocking — codex: "the B3 control does not prove the parent hands its one `served_at` down"

Codex (second sitting) held SEC-010 because
`tests/products/test_d364_peered_child_served_at.py::test_a_peered_child_and_an_in_process_child_are_judged_at_the_same_served_at`
drives `src/ccf/products/child_resolver.py::GrantBoundChildResolver` directly with an injected
`admitted_at`, so it cannot by itself show that `src/ccf/products/resolver.py::GovernedResolver`
passes its single clock read into that parameter. The structural observation is accurate. It is not
a hole: on the tree the hop is the assignment `admitted_at = served_at` inside
`GovernedResolver.__call__`, passed to both child-resolver call shapes. EXECUTED by the executing
model: severing that assignment to `request.asked_at` reddens four recorded controls —
`tests/products/test_resolver_seam.py::test_o3_admission_is_judged_at_the_RUNTIME_clock_not_a_declared_instant`,
`tests/products/test_resolver_seam.py::test_step4_the_composite_window_is_the_same_instant_as_served_at`,
`tests/products/test_served_at_severings.py::test_V1_severing_hoist_reverted` and
`tests/products/test_served_at_severings.py::test_V4_severing_a_second_clock_read` — while the new
control stays green, exactly as codex predicted. EXECUTED by the s010 seat: a real
`GovernedResolver` composite serve with one in-process and one peered child through the real
`src/ccf/peering/admission.py::PeeringAdmissionGate` measured one clock read (12:09) and the same
12:09 handed to the peering gate, to the composite gate for both children, and recorded as
`served_at`. The sever seat's broad rerun of S3 also reddened
`tests/peering/test_admission_clock.py::test_the_peering_hop_passes_the_FABRIC_instant_and_not_the_question_s`.
Recorded as ADVISORY: the clause-control alone does not pin the parent hop; the s010 seat's
real-route instrumentation test is a candidate for promotion to a committed control.

### 3.3 ADVISORY, carried (each confirmed on the tree)

**SEC-008**
- `error_code "temporal-write-refused"` appears in exactly one non-test file in the whole tree, the
  map `src/ccf/products/resolver.py::SDK_SEAM_REFUSALS`. It is not in
  `runtime/ccf_runtime/http_api/errors.py::refusal_detail`'s vocabulary, not in `openapi.json`
  (0 occurrences; no refusal schema on the product route), not on any published page, and no
  `docs/surface-changes/` fragment records the new conversion — whereas the first map entry was
  recorded by fragment `007-empty-identity-declaration-refused-by-name.md`. Pre-existing for
  `identity-refused`; the candidate added a second undisclosed code. **Discharged at `d136fdc5`**
  by fragment `364-01-temporal-write-refused-converts-at-the-seam.md` (section 4.2).
- `src/ccf/products/refusal.py::SubjectUnavailableRefusal`'s docstring says a shell below `full`
  carries `error_code` `None`; EXECUTED (b3 seat), it carries the string `"undisclosed"`.
  Pre-existing; that module is not in the GREEN diff.
- The B2/B3 controls assert by substring over the record's JSON string, not on the `fields.cause`
  and `fields.error_code` slots, and never on the consumer's shell at the default disclosure.
- The instant the guard judged against (`ingress_at`) is in the record only inside `detail` prose;
  the typed record holds `served_at` and `asked_at`. Two refused serves at the same clock values share
  one content-addressed replay reference (b3 seat, EXECUTED).
- Tripwire strength beyond K10 (b1 seat, EXECUTED; reader, INSPECTED):
  `tests/signal_layer/test_d364_writer_coverage.py::_site_ids` prefilters on the text `.ingest(`, so
  a file whose only call is spelled with a space before the parenthesis is skipped before the AST
  pass (Python parses it as a call); a `getattr(...)(...)` call is invisible; a call through the
  worker's private writer bypasses all four entry points and reddened none of 74 single-writer and
  lint controls; `tests/invariants/test_paved_road_writer_reach.py` scans `src/ccf` only. Positive
  controls (a multi-line or parenthesized call) reddened. All scratch files deleted, tree clean.
- `tests/signal_layer/test_d364_writer_coverage.py::_seam_order` compares text offsets, so a dead
  branch around the guard call leaves all nine d364 tests green; the two B3 behavioral controls
  redden (b1 seat, and the executing model's gutted-guard-body severing: 8 behavioral controls red,
  ordering tripwire green). The clause is met by the behavioral controls;
  `tests/signal_layer/test_d364_writer_coverage.py::B1_TRIPWIRE_SEVERINGS` points the clause at a
  test that does not bite on "guard disabled", and names one severing
  (`the-entry-point-roster-stays-exactly-four`) that neither the author nor the panel executed.
- `src/ccf/peering/admission.py` still says an admitted product "enters the graph only via
  `ingest_admitted`, through L2, exactly as before"; no composition root calls
  `AssemblyWorker.ingest_admitted`, so peered products are never written to L3 on this tree and
  "exactly as before" describes a route that does not exist. Misleading, not a false safety promise.
- `public/concepts/invariants.md` says the TTL gate's comparand is "read once per serve"; true of the
  comparand, but the paved road reads the clock twice (`served_at`, then `ingress_at` at the seam —
  the candidate's own control pins both reads), and finding 5 is carried by name.

**SEC-010**
- E1 residue (first sitting's codex and cursor; K8): `src/ccf/products/constraints.py::ReferencePolicyConstraintResolver`'s
  class docstring still reads "the Control Plane, read at ``asked_at``"; the
  `src/ccf/products/constraints.py::applicable` docstring and `Args` still name `asked_at`; the
  zone-less `TypeError` docstrings and the parameter name of
  `src/ccf/products/constraints.py::_require_aware` carry the old instant; one sentence in the
  module's superseded-reasoning block is unfinished. The ruled E1 text names only
  `src/ccf/products/constraints.py::PolicyConstraintResolver`'s `resolve` docstring, which is
  correct and whose severing reddens its control. The GREEN commit message's sentence "The
  superseded 'effectivity at asked_at' reading is gone" was therefore false at `beb0c717`; the clause
  was met, the message overclaimed. **Discharged at `d136fdc5`** (section 4.2): every listed site now
  says `served_at` for effectivity and keeps `request.asked_at` for the graph read.
- `tests/products/test_served_at_severings.py::test_severing_Peer_the_verdict_is_judged_at_the_callers_instant`'s
  docstring says the behavioral end-to-end control "does not exist and cannot yet"; the d364 module
  now is that control.
- With the peered hop severed, the persisted child row still records `child_admitted_at` =
  `served_at` while the peering gate judged at `asked_at` (two separate arguments in
  `GrantBoundChildResolver`), so dimension 5 could overstate the judging instant. Latent today.
- The paved road builds its child resolver with no peering gate, so on that route a peered child
  always refuses "this deployment binds no PeeringAdmissionGate"; the B3 control exercises the
  grant-bound route only.
- D1: both constraint ceilings sit above the ask, so the content address is the same whichever
  version replay resolves; under the replay→latest severing the address assertion passed and only the
  spy-based binding assertions reddened. The spy watches `src/ccf/replay/engine.py::replay`'s own
  Control Plane argument only; the replayed-`served_at` assertion compares the stored record with
  itself. Code reading closes it (the replay environment reads no clock and resolves no "latest").
  The test docstring says the effectivity severing "puts the EARLY artifact in force"; measured, the
  pins are empty.
- No resolver-level control exercises Gate 3's upper bound (`expires_at > served_at + MAX_TTL`) at
  `served_at`; it shares the one `now` comparand with the lower bound.
- Controls weaker than their clause (sever seat, EXECUTED, the shipped text satisfies each clause
  today): E1's control accepts a reworded docstring that says effectivity is judged at
  `request.asked_at`; C1's pin is one exact phrase and a paraphrased forgery claim stays green; C4's
  dated-marker regex accepts a bare `AMENDED` with no date.

**SEC-011**
- `tools/docs_tests/test_gate_assurance_surfaces.py::audit_register` harvests citations from the
  whole row, "resolves" by a function-name lookup rather than pytest collection, cannot tell a
  resolving citation from a reddening one (its own accepting control
  `tools/docs_tests/test_gate_assurance_surfaces.py::_GOOD_REGISTER` maps `source-attestation` to a
  TTL test and passes), and still substring-matches the two required non-token subjects in any row's
  prose. The S12/S13 hardening closed the named hole for gate tokens only. The two blocking rows
  above are instances of the citation-relevance shape already on the shipped page.
- `public/concepts/the-first-context-product.md` still says the second gate "holds the two to strict
  equality in both directions, so a declared operator that did not run and an operator that ran
  undeclared are both refusals", with no assembly-path qualifier.
- The `lineage-attributability` row says "Governed path, federated products" but its cited test calls
  `run_federated_gates` directly; the citation is genuine, the path column overstates.
- The ruling text at `D-IMPL-364` B1 places the binder at `src/ccf/products/resolver.py`; the symbol
  is defined at `src/ccf/deployment/binder.py::refuse_operator_set_divergence` and the register cites
  the right path. The ruling's citation is stale.
- The ttl, attributability, attestation, dependency and obligations rows were not sabotage-checked.

## 4. The two docs repairs this record carries

### 4.1 Two register citation cells (INDEPENDENTLY EXECUTED by the executing model, baseline → sever → restore)

Dave's scoped GO (2026-10-04, after the panel's report): "Repair GO for the two controls-register
citation cells only ... Verify each replacement against its actual production control with baseline →
sever → restore evidence. No production changes." Commit `4279d827` on `repair-d-impl-364-clauses`;
diff: `public/reference/controls-register.md` only, 2 insertions, 2 deletions.

- Binder row now cites `tests/products/test_resolver_seam.py::test_a_plan_contradicting_the_class_is_refused_before_it_is_executed`
  (the governed path: the resolver calls the binder before the plan executes) and
  `tests/deployment/test_binder.py::test_one_edited_operator_key_in_one_document_is_refused`.
- `ttl-anchor-unresolvable` row now cites
  `tests/products/test_d_impl_341_ttl_anchor.py::test_c5_a_served_set_with_no_source_instant_refuses_by_its_own_reason`.

Driver: a byte-exact edit, `__pycache__` purged, `python -B`, `-p no:cacheprovider`, bytes restored
and sha256 asserted; `git checkout` never used. Interpreter `qual-a4cf2fb7/.venv`.

| step | targets | result |
| --- | --- | --- |
| baseline | c5, c6, the two new binder citations, the two old binder citations, the register docs test | 24 passed |
| binder severed (`if claimed == required:` → `if True:`) | the two NEW binder citations | **2 failed** (both) |
| binder severed | the two OLD binder citations | 2 passed (the defect, reproduced) |
| restore | `src/ccf/deployment/binder.py` | sha256 equal |
| anchor mint severed (both `gate=GATE_TTL_ANCHOR` sites → the bounds token) | the NEW anchor citation (c5) | **1 failed** |
| anchor mint severed | the OLD anchor citation (c6) | 1 passed (the defect, reproduced) |
| restore | `src/ccf/products/expiry.py` | sha256 equal |
| restored baseline | the same 24 nodes | 24 passed |
| `git status --short` | | exactly `M public/reference/controls-register.md` |

Gates on the edited tree: `tools.lints --all` rc 0 (`--report`: 5,116 citations matched, 3,751
checked and passing, 0 findings); `mkdocs build --strict` clean; the citation ratchet at 365,
unchanged. No replacement needed a new test; the gap the GO anticipated did not arise.

### 4.2 The docs completion the two SEC-008 rulings call for (`d136fdc5`)

Dave's instruction (2026-10-04, 17:17 MST): correct the stale `asked_at` descriptions, record the two
existing rulings, complete the disclosures they require, verify, commit, push. No behavior change.
Diff: nine files, docstrings and prose only — no code line changed (checked by diffing the production
hunks for any non-prose line).

- **SEC-010 E1 residue corrected**, in `src/ccf/products/constraints.py` only: the
  `src/ccf/products/constraints.py::applicable` docstring's window sentence, its `Args` entry and its
  `Raises` entry now name `served_at`; the
  `src/ccf/products/constraints.py::ReferencePolicyConstraintResolver` class docstring reads "the
  Control Plane in force at ``served_at``" and its `resolve` `Raises` names `served_at` for the
  effectivity conflict and both instants for the zone-less `TypeError`; one truncated sentence in the
  module's superseded-reasoning block is completed. At every site the distinction is kept: effectivity
  at `served_at`, the graph read at `request.asked_at`. Line-count-neutral.
- **SEC-008 B1 disclosure** (the ruling: the low road is outside B1, the guard there is the
  adopter's): `src/ccf/assembly/worker.py::AssemblyWorker`'s `ingest` docstring now tells a direct
  caller that the method judges no instant and reads no clock, that its one governed caller runs
  `src/ccf/signal/envelope.py::IngressTemporalBound`'s `refuse_outside_window` first, and that a
  low-road composition root composes that guard itself or accepts an unrefused out-of-window write;
  the same statement at `src/ccf/deployment/manifest.py::load_and_boot`, in the module docstrings of
  `runtime/ccf_runtime/cdc/adapter.py::CDCSourceAdapter` and
  `src/ccf/signal/mcp_source.py::MCPSourceAdapter` (both stamp their own clock, so they can only
  ingest on the low road), in `runtime/ccf_runtime/mcp/product_door.py::ProductDoor`'s low-road
  sentence, and in `src/ccf/products/product.py`'s module docstring.
- **SEC-008 B2 disclosure** (the ruling: the 404 mapping stays):
  `docs/surface-changes/364-01-temporal-write-refused-converts-at-the-seam.md` records the
  `src/ccf/products/resolver.py::SDK_SEAM_REFUSALS` entry as a `behavior` change (`Public surface:
  false` — the map is not a manifest name): cause `nonexistent`, code `temporal-write-refused`, kind
  `subject-unavailable`, 404 at every disclosure level, what `minimal`, `reasoned` and `full` show,
  the replay record as the place the true reason lives, the migration note for a consumer keying on
  `cause`, and the ruling. `docs/SURFACE-CHANGES.md` re-assembled; the assembler's `--check` rc 0.
- **One re-cite:** the product door's docstring grew by three lines, which moved a line-anchored
  citation in the dated design spec (`ProductDoor.serve_stdio`) off its lines — a `cite02` finding.
  Re-cited by symbol, as `beb0c717` did for `docs/D-IMPL-304-DESIGN.md`.

Verification at `d136fdc5` (INDEPENDENTLY EXECUTED by the executing model): `tools.lints --all` rc 0
(5,185 citations matched, 3,820 checked and passing, 0 findings); `mypy src runtime` clean, 242
files; `tools/dump_surface.py --report` 0/0/0 and `--check` rc 0; `mkdocs build --strict` clean;
`tests/products signal_layer replay gates peering controlplane assembly agents contracts deployment`
3,098 passed, 4 skipped, 0 failed; `tools/docs_tests` + surface drift, completeness, shape-capture,
obligation-vocabulary and citation-coverage 428 passed with the two standing reds (the retirement
sweep; the citation ratchet `365 <= 0`, population unchanged). Documentation consistency: every
remaining `asked_at` in `constraints.py` names the graph read, the request field, the superseded
reasoning quoted as such, or the relative-defaults anchor — none states effectivity at `asked_at`
as current.

## 5. Independent execution — the owner's five verification items

| item | verdict | by whom, how |
| --- | --- | --- |
| V1 SEC-008 B1 (writer coverage) | VERIFIED for `src/` + `runtime/` static call sites; **the clause's scope needs a ruling** (section 9) | b1 seat: AST walk, `.ingest` referenced only at `src/ccf/products/product.py::OpenedProduct`'s acquisition seam, `.worker` read only there and set only in `src/ccf/boot.py::FabricHandle`, zero references to the other three entry points outside `src/ccf/assembly/worker.py::AssemblyWorker`; tripwire 9 passed; planted bypasses as in 3.3 |
| V2 SEC-008 B3 (real route) | VERIFIED by execution | b3 seat: with the map entry deleted, a raw `src/ccf/signal/envelope.py::TemporalWriteRefused` escapes `OpenedProduct.answer`; with it present, a `RefusalEnvelope` whose record carries cause `nonexistent` and code `temporal-write-refused`; writer calls 0, all five graph tables 0 rows; a still clock serves and writes once (positive control); a second question refuses identically |
| V3 SEC-010 B3 (peered child) | VERIFIED by execution; codex's hold rejected (3.2) | s010 seat real-route instrumentation; executing model's hop severing |
| V4 SEC-010 D1 (replay address and bindings) | VERIFIED | s010 seat: all six elements asserted including the temporal-boundary binding pinned once and resolved at its recorded version; non-vacuous under three severings (replay→latest red; LATER registration removed → the both-halves assertion fires; effectivity→`asked_at` red) |
| V5 SEC-011 C1–C4 | C1, C3, C4 VERIFIED; C2 NOT VERIFIED at `beb0c717` (3.1), repaired at `4279d827` (4) | s011 seat: `required_operator_keys` `min_length=1` on both `src/ccf/controlplane/artifacts.py::ProductClassDeclaration` and `src/ccf/controlplane/artifacts.py::ProjectionRequirements`, an empty set refused at validation by execution, the cited Gate 1 control reddens under a Gate 1 sabotage; the 358-05 body verbatim against the base with the dated amendment heading |

Gates at `beb0c717` (accept seat, INDEPENDENTLY EXECUTED; every figure equals the author's reported
evidence): the eight clause files 137 passed / 0 failed / 0 errors / 0 skipped; `tests/products
signal_layer replay gates peering controlplane assembly agents contracts` 2,752 passed, 4 skipped
(estate- and container-gated legs no seat may run); `tools/docs_tests` + surface gates 399 passed,
1 failed — `tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current`, standing
on `main`; `tools.lints --all` rc 0 with 0 findings on `--report`; `mypy src runtime` clean, 242
files; `tools/dump_surface.py --report` 0/0/0 and `--check` rc 0; `mkdocs build --strict` clean.
Not run: `tests/test_version_stamp.py` (standing red), `tests/examples`, `tests/hitl`,
`tools/lints/tests`, `tools/product_gates_tests`.

**The citation ratchet is a standing failure, not a passing gate** (ratchet seat, INDEPENDENTLY
EXECUTED in both trees): `tests/invariants/test_citation_coverage.py::test_the_unanchored_python_citation_population_cannot_regrow`
fails `assert 365 <= 0` at the base and at the candidate; the 365 sites are byte-identical between
the two logs; `tools.lints --citations` rc 0 in both. The candidate adds 0 line-anchored `.py:N`
citations (55 added lines in `path::Symbol` form) and re-cites two stale anchors in
`docs/D-IMPL-304-DESIGN.md` by symbol; both resolve.

## 6. Severings S1–S17 — the author's run and the panel's rerun (sever seat, INDEPENDENTLY EXECUTED)

Seventeen severings, each one byte-exact edit, run against the targeted suites by a copy of the
author's driver with only its worktree path changed. Baseline 94 passed before and after. Every
failed-node set equals the author's final-pass set (17 of 17, compared programmatically). Every red
was an `AssertionError`, never an import or collection error. Verdicts: (a) the failing control proves
the clause for S1–S10, S12–S15 and S17; (c) green is correct for S11 (the invariants page's courtesy
link to the register is not a C1 element; C1 is about the passage's reading and S14 covers
publication) and S16 (the criterion accepts either dated marker and "true at step 5" remained). No
severing earned (d). The targeted suites hid corroborating reds for three of the five production
severings and hid no contradiction — against the broad suite (2,141 passed, 4 skipped at baseline),
S3 also reddened the peering-hop control and the Peer severing meta-test, S4 also reddened
`tests/replay/test_engine_rehydration.py::test_the_replay_path_never_resolves_latest`, S5 also
reddened `tests/products/test_policy_constraint_resolver.py::test_E1_a_constraint_effective_after_asked_at_but_before_served_at_applies`.
Two (d)-class holes the campaign did not run are the two blocking rows of section 3.1 (re-citing a
row to a resolving but unrelated test stays green) and the prefilter shape of section 3.3.

## 7. Checked, not defects — consolidated

- Cursor's "gut the guard body, keep the call order": the ordering tripwire stays green as predicted,
  and eight behavioral controls go red (EXECUTED by the executing model); the guard is load-bearing.
- Q1 cause honesty: a decision for Dave, not a defect finding (section 9.2).
- Q2–Q3 (other write-handle shapes): the only exposures in `src/` and `runtime/` are
  `src/ccf/boot.py::FabricHandle` and the paved road's own read of it; no runtime composition root
  extracts the worker; the adapters, CLI, HTTP door, MCP door, workflow engine and peering modules hold
  no graph write handle (b1 seat, AST walk).
- Q4–Q5: one clock read per serve on the real composite route; replay reads no clock and resolves no
  "latest" (s010 seat; `src/ccf/replay/engine.py::replay`).
- Q7: "self-satisfying on the governed path" is ruled; `ttl-anchor-unresolvable` is minted in
  `src/ccf/products/expiry.py::resolve_ttl_anchor` and nowhere in either gate runner.
- Q8: no page under `public/` claims Gate 2 catches a forged lineage; the residual over-claim in
  `the-first-context-product.md` is the "both directions" sentence (3.3).
- Q9: every import-based severing reddened, so the edited tree was imported; the greens are file-read
  subjects resolved from `__file__`; a false red would need a failed restore, which the sha256
  assertion covers.
- Q10: the one behavior change in the GREEN diff is the seam-map entry. The hoisted clock read gemini
  named as "the intended behavior change" (both sittings) is not in the GREEN diff.
- The `src/ccf/contracts/guarded.py::GUARDED_TYPES` roster that names `ingest_admitted` is a
  guarded-type boundary declaration, data consumed by guard-coverage checks; it invokes nothing.

## 8. Reviewer accounting

| reviewer, sitting | blocking claimed | outcome | errors |
| --- | --- | --- | --- |
| codex, first | E1 residue (BLOCKING) | real on the tree; outside the ruled E1 text → ADVISORY | none |
| codex, second | SEC-010 B3 parent hop (BLOCKING) | accurate observation; rejected as blocking by execution → ADVISORY | none |
| cursor, first | none | 4 advisories, all confirmed | none; disclosed the missing sections |
| cursor, second | none | gutted-guard finding checked by execution: not a defect; cause-only consumers folded into 9.2 | none |
| gemini, first | none | claimed "all superseded reasoning is historical" (false); cited a `gates.py` line for text not there; claimed to have checked an empty SECTION C | three |
| gemini, second | none | named a hoist absent from the GREEN diff as the intended behavior change | one |
| reader seat | two register rows (BLOCKING) | both confirmed by execution | none |

Three reviewers agreeing is not evidence; every verdict in this record rests on a seat's or the
executing model's execution.

## 9. SEC-008 dispositions — RULED (Dave, 2026-10-04), with the panel's presentation preserved

The panel presented two choices. Dave's reply (17:17 MST, relayed verbatim): *"My previous
recommendation reopened rulings you had already made. Withdraw it. The low road is outside B1, and
the 404 stays."* Both are therefore recorded as **existing rulings**, not new ones — they follow
`D-IMPL-358` ruling 2 (the worker owns no clock; the guard is a caller guard) and `D-IMPL-364`
choice 1 as ruled. Neither is reopened here. The presentation that led to them is kept below as the
history of the decision, headed as presented.

### 9.1 SEC-008 B1 — RULED: the low road is OUTSIDE B1's scope

**Disposition (2026-10-04).** B1 is met as built on `beb0c717`: the four writer entry points are
guarded, or structurally unreachable, from every supported governed ingress, where "supported
governed ingress" means the paved road and the SDK-owned doors onto it. A composition that calls the
writer itself is on the low road, and the temporal guard there is the adopter's to compose. The
obligation that followed — saying so where a low-road adopter will read it — is discharged at
`d136fdc5` (section 4.2). SEC-008 stays OPEN pending the merge decision and the separate closure
decision.

**As presented (history):** *is the documented low road a "supported governed ingress"?*

The b1 seat found no path in `src/` or `runtime/` that reaches the writer unguarded. The absence of
SDK-owned callers is not treated here as proof that documented adopter ingress is excluded. The SDK's
own text documents a route where adopter code calls the writer directly and nothing composes a
guard. The exact contracts, each READ on the pinned tree:

- `src/ccf/deployment/manifest.py::load_and_boot` (docstring): "the adopter ingests from
  ``booted.artifacts[<signal-batch-key>].envelopes`` through ``booted.handle.worker``, builds a view
  from ``booted.handle.reader``".
- `src/ccf/products/resolver.py::AcquisitionSeamProtocol` (docstring): "The callable is the
  deployment's composition root — the paved road's OpenedProduct, or a hand-composed spine — and it is
  that root that reads a source and ingests through L2's one writer." The protocol is structural; any
  callable is accepted.
- `src/ccf/products/product.py` (module docstring): "The low road stays the low road (Dave: *'Do not
  make the paved road the only road.'*)."
- `src/ccf/signal/envelope.py::refuse_foreign_envelope` (docstring): "A source that must stamp its
  own ingestion instant is a long-lived fabric and composes on the low road, where no per-question
  boundary exists."
- `runtime/ccf_runtime/cdc/adapter.py::CDCSourceAdapter` (module docstring): "Envelopes go to the
  caller, the caller hands them to the L2 AssemblyWorker, and that is the only route into L3". The
  adapter stamps `ingestion_timestamp` from its own clock, which the paved road's foreign-envelope
  check refuses unless it equals `asked_at`, so the CDC reference ingress can only ingest on the low
  road. `src/ccf/signal/mcp_source.py::MCPSourceAdapter` documents the same route and the same stamp.
- `src/ccf/peering/admission.py::PeeringAdmissionGate` (module docstring): "The envelope-based
  `ingest` is unchanged and continues to serve CDC and MCP ingress".
- `runtime/ccf_runtime/mcp/product_door.py::ProductDoor` (module docstring): "a deployment composed by
  hand on the low road (an hw1-shaped long-lived fabric with its own resolver) reaches the same door".
- `docs/surface-changes/358-08-temporal-write-guard.md` (Migration): "the paved road composes it
  automatically at `OpenedProduct._acquisition_seam`. A deployment in its own path composes one at its
  own composition root" — the only sentence on the tree that assigns the guard responsibility to the
  adopter, and it is optional: `src/ccf/signal/envelope.py::IngressTemporalBound` is exported and
  nothing requires it.
- `src/ccf/assembly/worker.py::AssemblyWorker`'s `ingest` docstring was not changed by the candidate
  and says nothing to a direct caller about the guard; the three other entry points' docstrings now
  say "outside the supported ingress surface".

What `beb0c717` proves: the four entry points are unreachable, or guarded, from every SDK-owned call
site. What it does not prove: that a bank which wires CDC exactly as the adapter's docstring says has
any temporal guard between its envelopes and L3. The ruling asked for:

- **Option A — the low road is outside B1's scope.** B1 is MET as built. The obligation that remains
  is documentation: `load_and_boot`, the two L1 source adapters and the product door's low-road
  sentence should state that no temporal guard runs there and that the adopter's ingest loop composes
  `IngressTemporalBound` at its root, and `ingest`'s own docstring should say so to a direct caller.
- **Option B — the low road is inside B1's scope.** B1 is UNMET: a guard must be required at the
  low-road composition (not inside the worker, which stays tenant-free and clock-free by the K1
  ruling). That is a design question and a repair cycle of its own.

(The presentation ended here. Option A was the existing ruling; the obligation it named is the
disclosure at `d136fdc5`.)

### 9.2 SEC-008 B2 — RULED: the 404 mapping STAYS

**Disposition (2026-10-04).** The seam map's binding of `TemporalWriteRefused` to a
`SubjectUnavailableRefusal` with cause `nonexistent` and code `temporal-write-refused` stands, and so
does the door's 404 for that kind at every disclosure level: the status is taken from the disclosed
kind so that no status tells a principal whether a subject exists, the record carries the true code,
and the question-outside-the-window refusal (`TemporalBoundRefusal`, 400) remains a different fact.
The obligation that followed — a surface-change fragment stating the code and its public meaning —
is discharged at `d136fdc5` (section 4.2).

**As presented (history):** *the write refusal's public meaning.*

The map entry `src/ccf/products/resolver.py::SDK_SEAM_REFUSALS` binds
`src/ccf/signal/envelope.py::TemporalWriteRefused` to a `SubjectUnavailableRefusal` with
`cause="nonexistent"` and `error_code="temporal-write-refused"`, as the author's choice under Dave's
choice 1 ("Add TemporalWriteRefused to SDK_SEAM_REFUSALS for governed serves"), which named neither
the cause nor the kind. The existing contract, each READ:

- `src/ccf/products/contract.py::RefusalCause` is `Literal["nonexistent", "unauthorized", "undisclosed"]`
  (closed). The map comment reads the cause as "the fabric holds no admissible observation for this
  question at this instant — the same reading IdentityRefused carries".
- `src/ccf/products/refusal.py::REFUSAL_KINDS` maps `SubjectUnavailableRefusal` to kind
  `subject-unavailable`; `runtime/ccf_runtime/http_api/refusal_status.py::_STATUS_BY_TYPE` maps that
  type to `STATUS_UNAVAILABLE` (404) and the module explains "subject-unavailable is 404 at every
  level" because the mapping is taken from the disclosed kind so that an unauthorized principal is not
  told the subject exists.
- `src/ccf/products/refusal.py::TemporalBoundRefusal` — the A1 refusal for a question outside the
  tenant's window — has the closed reasons `temporal-boundary-undeclared`,
  `asked-at-outside-temporal-bound` and `decision-instant-outside-temporal-bound`, and the status table
  maps it to `STATUS_REQUEST` (400). The write refusal's own detail text begins
  "asked-at-outside-temporal-bound", the same reason A1 uses for the same breach.
- EXECUTED (b3 seat, `src/ccf/products/disclosure.py::disclose` at all three levels): at `minimal`
  (the default) and `reasoned` the delivered shell reads "the requested subject is not available to
  this principal under this product" with `cause` and `error_code` both `"undisclosed"`; only `full`
  shows `nonexistent` / `temporal-write-refused`. Neither door schema declares the code.

So a serve whose resolution lets `ingress_at` drift past the window reads to a consumer as a
not-found or entitlement condition, with a 404, while the identical breach judged at the request
reads as a temporal-bound refusal with a 400. The smallest compatible mappings:

- **Option A — keep the shipped mapping** and record the choice. Consistent with `IdentityRefused`,
  suppression-safe (404 leaks nothing), the record carries the true code. Obligation: a surface-change
  fragment and the door vocabulary so the code is disclosed somewhere a consumer can read it.
- **Option B — bind to the temporal-bound shape.** Convert at the seam to a `TemporalBoundRefusal`
  with reason `asked-at-outside-temporal-bound` (400), matching A1 for the same fact. One map entry's
  target type changes; `SeamRefusalBinding` (`src/ccf/controlplane/artifacts.py::SeamRefusalBinding`)
  today carries a cause and a code for a `SubjectUnavailableRefusal` only, so this is a small contract
  change and a repair cycle, with the suppression question (does a 400 tell a principal anything about
  the subject?) answered in the entry.

(The presentation ended here. Option A was the existing ruling; the obligation it named is the
fragment at `d136fdc5`.)

### 9.3 SEC-010 closure — still OPEN

The panel finds A1, B2, B3 (behavioral), C1, D1 and E1 pass on `beb0c717`; the E1 residue is
corrected at `d136fdc5`. The ruling at `D-IMPL-364` lets SEC-010
close independently once those pass; this record preserves the PROCEED as review evidence for a
separate closure decision after the reviewed changes are merged. Nothing is closed here.

## 10. Provenance of the raw material (withheld from the tree, available on request)

Every artifact of both sittings is kept at
`~/.claude/projects/-home-parkave-ccf-code/panel-save-2026-10-04/`: `panel5/` holds the first
sitting's defective payload and its three superseded reviews with their exit codes; `panel6/` holds
the corrected payload, the three second-sitting reviews (`codex.out`, `cursor.out`, `gemini.out`, with
`.err` and `.rc`), each seat's outputs, probes, severing reports and logs (`seat-*/`), the executing
model's saved originals and the register-fix evidence log, and the panel's working report. The raw
reviewer outputs cite line numbers that are correct at `beb0c717` and will go stale, which is why they
are not copied into the tree; this record cites by symbol.
