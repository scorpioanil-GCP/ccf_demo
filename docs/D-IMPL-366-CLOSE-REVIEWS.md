# `D-IMPL-366` — SEC-006 repair candidate: CLOSE PANEL reviews

**Subject.** Candidate `149aba7f` on `repair-sec006-eligibility`; baseline `main` @ `a236e6ce`
(= `origin/main` at review time, unchanged). Ruling `D-IMPL-366` as amended (G1–G8 all (a); H1 (a),
H3 (a), the H2 requirement; the ordering amendment; carried test requirements (1)–(3)). Evidence
the panel judged: `docs/SEC-006-CANDIDATE-EVIDENCE.md` (§3 names the unruled implementer's choices).
Close-panel GO (Dave, 2026-10-05 06:07 MST): *"Independently run the 30 controls, required
severings, and SEC-001/SEC-005 preservation checks. Assess `HitlEventRevalidationRefused` and its
`hitl-event-revalidation-refused` / HTTP 409 mapping as unruled choices. Keep author-executed and
independent evidence separate; the implementer holds no reviewing seat. Record findings and stop.
No repair, merge, tag, release or closure."*

**Disposition of this record: HOLD.** One BLOCKING code-coverage finding (3.1) and two BLOCKING
documentation findings (3.2, 3.3), every one confirmed on the pinned tree by execution. Nothing is
repaired here; each is a decision or a fix for the owner to call. `SEC-006` stays OPEN; the ledger
stays 12 of 29; `docs/DECISIONS.md` is untouched.

## 1. The panel: seats and evidence status

Payload (209 KB, on stdin to each CLI; assembled with an integrity grep — no `No such file` line,
every announced section present): the brief with a read-proof token and a three-citation negative
control (G1/G2 resolve, G3 does not); SECTION B1 the ruling verbatim; B2 the adopted brief §4, §4b,
§4c, §5, §9, §10; C the `src/` + `runtime/` diff `a236e6ce..149aba7f`, line-numbered; D the
harness, the four control modules and the three fixtures, line-numbered; E the evidence report; F the
other changed files (tests, docs, public, `openapi.json`) by path only, named unreviewed. One build
defect, harmless: the brief carried no `SECTION A` heading, which cursor reported as "SECTION A not
present" while following its instructions in full.

| seat | model / tool | subject | evidence | disposition | findings |
| --- | --- | --- | --- | --- | --- |
| **codex** | codex-cli 0.137.0, `gpt-5.5`, reasoning high, read-only sandbox, stdin | the payload (77,316 tokens read) | INSPECTED; token present; negative control 3/3 | PROCEED | 0 |
| **cursor** | cursor-agent 2026.10.01, `--mode ask`, stdin | the payload | INSPECTED; token present; negative control 3/3 | PROCEED | 3 ADVISORY (all confirmed, 3.4) |
| **gemini** | gemini CLI, `GOOGLE_API_KEY`, stdin | the payload | INSPECTED; token present; negative control 3/3; **3 of 12 line citations point past the end of SECTION C** (section 5) | PROCEED | 0 |
| **controls** | Claude Opus subagent, no session context | its own worktree at the pin and a second at the baseline | **INDEPENDENTLY EXECUTED**: the 30 controls, the baseline reds, the four suite chunks, mypy, lints | all as reported, one accounting discrepancy (section 4) | 0 |
| **sever** | Claude Opus subagent | its own worktree; its OWN driver, derived from the ruling | **INDEPENDENTLY EXECUTED**: 15 required severings, the two individual missing-state removals, the two panel shapes, 8 own probes | 15/15 RED as named | 1 ADVISORY (3.4, the policy-less gate) |
| **preserve** | Claude Opus subagent | its own worktree; 11 sabotages | **INDEPENDENTLY EXECUTED**: SEC-001 and SEC-005 populations, sabotage-verified | — | **1 BLOCKING (3.1)**, 2 ADVISORY, 1 observation |
| **reader** | Claude Opus subagent | its own worktree, read-only; probes in scratch; one severing on an archive copy | INSPECTED + probes | **HOLD** (two docs findings) | **2 BLOCKING (docs; 3.2, 3.3)**, 7 ADVISORY |

The executing model (Claude Fable 5.1, the author of the candidate) held no reviewing seat. It
assembled the payload, created the seat worktrees, verified every finding and every rejection below
against the pinned tree by execution, and wrote this record. Its runs are labelled
**AUTHOR-EXECUTED** throughout and are never counted as independent-seat evidence; where a seat
reached the same result independently, the seat is named beside it.

## 2. The independent executions, in numbers

**Controls seat.** The 30 controls on the candidate: collected 30, passed 30, failed 0, errors 0.
The same four modules at the baseline (the eight new files copied into a baseline worktree):
collected 30, 5 passed, 25 failed, 0 errors — 8 BEHAVIORAL, 16 MISSING CONTRACT, and T5 red with
`TypeError: _register_covenant_closure() got an unexpected keyword argument 'as_shipped'`, because
the candidate's T5 calls a keyword the baseline helper lacks (section 4). Suites on the candidate:
(a) hitl/workflow/http_api/mcp/cli/conformance/crossproc **1638 passed**, 86 skipped; (b)
products…peering **2849 passed**, 28 skipped; (c) the remainder plus `tools/lints/tests` **4681
passed, 2 failed** — both reds PRE-EXISTING at the baseline, re-run there by the seat (the citation
ratchet's 365-entry list line-for-line identical on both trees; the venv version stamp); (d)
`tools/docs_tests` **320 passed**. `mypy` strict: 243 files, no issues. `tools.lints --all`: exit 0,
no output. Both worktrees clean afterwards.

**Sever seat** (own driver; 37 runs; every restore byte-identical by sha256; git status clean after
every run):

| severing | named control(s) | result |
| --- | --- | --- |
| S1 transport call removed | T1 ×4 | 4/4 RED (corroboration: 9 reds across the four modules) |
| HTTP mapping removed | T2 | RED (`ApproverNotEligible` escaped unmapped) |
| MCP mapping removed | T2b | RED |
| S2 primitive call removed | T3 | RED (the claim was taken) |
| S3 engine eligibility leg removed | T4 ×2 | 2/2 RED |
| S4 factory class check removed | T5 | RED |
| S5 `requested_by` not stamped at `_suspend` | T6 | RED |
| S6 empty set admitted | T7 | RED |
| R1 `requested_by` dropped from the event | T8 | RED (26 corroborating) |
| R2 stamps `None` | T9 | RED (6 corroborating) |
| R3 `resolve_latest` in the helper | T10 | RED |
| C 6a removed | T11 | RED |
| C nonce consumed before 6a | T14 | RED |
| M both missing-state guards removed together | T12 (i), T12 (ii) | 2/2 RED |
| M each guard removed alone (informational) | T12 (i) | green both times — the two guards overlap completely, as corrected requirement (2) allows |
| M `_recorded_gate_verdicts` narrowed | T12b | RED |
| panel shape 1: comparand widened to the unsigned binding subject | T1, T1b | no red, as the brief predicts; the seat's probe P7 shows `PrincipalMismatchRefused` fires first in both directions |
| panel shape 2: S1 removed, S3 kept | T4b, T6 | T4b green; T6 red at its door assertion only (line 320); **T6's final resumption is not reached and so is unmeasured under this severing** — the brief's "T6's resumption assertions still hold" is measured only up to the first resumption |

The seat's eight probes (all run against the unedited tree): a `@9.9.9` policy ref refuses as
"resolves to nothing"; **a routed gate with NO `gate_policies` entry constructs, its event carries
`policy_ref=None`, and it can never be approved — fail-closed at runtime only** (3.2); an
exception-escalation event whose requester equals the submitter is admitted unjudged (G6 (a)); a
missing-state approval plus an agreeing eligible approval resumes; a missing-state approval plus the
starter's own approval does not; a door submission while a primitive holds the claim — an ineligible
submitter is refused with state byte-identical, an eligible one is recorded `claimed` and pops the
primitive's claim (the carried "claim addressed, not held" residual, not new); a later policy
version registered as latest does not change the judgment against the pinned version; the
capability-principal/binding-subject mismatch refuses both ways.

**Preserve seat** (11 sabotages, each restored by sha256): SEC-001 population 88 passed; SEC-005
population 74 passed; the conflict refusal disabled → 7 reds (not vacuous); the transport's
attestation requirement disabled → 22 reds; the nonce single-use disabled → 4 reds; the primitive's
attestation check disabled → 1 red (`test_the_approval_gate_verifies_the_attestation_independently_of_the_transport`;
the three `test_gate_required_*` tests and the idempotency test stay green because the transport
re-verifies beneath the gate — pre-existing, observation O-1); nonce consumed before 6a → T11 and
T14 red; `_recorded_gate_verdicts` narrowed by missing state → 2 reds. **The hash term of
`_gate_authority` replaced by `True` → 0 reds across 1508 tests (3.1).** Eligibility swapped after
attestation at the transport → 0 reds (3.4). `_recorded_gate_verdicts` narrowed by the starter → 0
reds (3.4). With eligibility neutralized, the SEC-005 files' 49 tests all still pass and every
`pytest.raises` in them names a `SignedBinding*`-family type: no SEC-005 control is now produced by
eligibility.

**Reader seat**: with `check_approver_eligibility` neutralized at all three sites, the six affected
directories run 12 failed / 1496 passed and all 12 are SEC-006 controls — no existing control now
passes because of eligibility. Every test cited in the controls register's new table exists.

## 3. Findings — each verified against the pinned tree before being recorded

### 3.1 BLOCKING — the SEC-001 hash-binding control is vacuous on the candidate (preserve seat; AUTHOR-EXECUTED confirmation)

`tests/workflow/test_engine.py::test_a_submission_that_never_saw_this_suspension_is_not_authority`
records a verdict from principal `impostor` with a wrong `product_content_hash` and asserts the
resume refuses. In `_gate_authority` the hash term is the second conjunct and `eligible()` is the
last, so for the impostor the hash refuses first and eligibility is never reached — the ORDER is
not what makes the control vacuous. The two conditions OVERLAP for that fixture: `impostor` is not
in the typed fixture policy, so with the hash term severed the new `eligible()` conjunct still
excludes the submission and the test stays green. It passes for a reason it was not written to
prove. (Corrected 2026-10-05 08:09 MST on Dave's instruction; the first wording, taken from the
preserve seat's phrasing, inverted the order.) Measured by the seat and reproduced
AUTHOR-EXECUTED on the pinned tree: with `submission.principal.product_content_hash == suspension`
replaced by `True`, `tests/workflow/test_engine.py`, `tests/http_api/test_routes.py` and the SEC-006
engine module run **88 passed, 0 red** (the seat: 0 reds across 1508 tests in six directories). The
SEC-001 hash binding — one approval authorizes the suspension it actually saw — therefore has NO
control that reddens under its severing on this tree. `D-IMPL-366` item (3) required "the SEC-001
authority conditions re-run on the changed engine"; they ran green, and one of them no longer
measures its condition.

The shape of a fix was measured, not applied: a probe recording the same stale-hash verdict from an
ELIGIBLE non-starter (`officer-3`) passes on the candidate and **reddens** with the hash term severed
(AUTHOR-EXECUTED; the seat's three probes agree). The owner's choices: make the existing test's
impostor an eligible principal, or add a separate eligible-but-stale-hash control beside it. Either
is test-only. Not done here by instruction.

### 3.2 BLOCKING (documentation) — the fragment overclaims the factory, and a policy-less gate is undisclosed (reader seat; sever seat P2; AUTHOR-EXECUTED confirmation)

`docs/surface-changes/006-approver-eligibility-is-the-sdks.md`, entry
`ccf.workflow.factory.WorkflowFactory`, "Why: fail-closed at the factory, so a workflow whose gate
nothing can judge never constructs." False for a routed `hitl-gate` with NO `gate_policies` entry:
the factory's class check iterates `definition.gate_policies.items()` and such a gate is not in it.
AUTHOR-EXECUTED on the pinned tree: the two-gate workflow constructed with only `first-approval`
policed; its second gate's event carries `policy_ref=None`; an eligible approval of it is recorded;
`resume` refuses — the gate can never be passed. The runtime refusal is as ruled (no policy →
refuse); the construction is not covered by the ruling's §4 (5), which class-checks "each
`gate_policies` target". No migration line discloses that a workflow with a policy-less gate, which
resumed before the change (the reader seat's probe on an archived baseline: `WorkflowCompleted`), now
stalls at runtime. Two owner choices: refuse a routed `hitl-gate` with no policy at construction
(a design choice beyond the ruling), or disclose the behavior in the fragment and the dated notes.
Either way the fragment's "Why" sentence is wrong as written.

### 3.3 BLOCKING (documentation) — the migration instruction cannot be followed on a plane that holds the pre-change policy (reader seat; AUTHOR-EXECUTED confirmation)

The same fragment entry says "Migration: register the typed policy under the key the ref pins before
constructing", and the two dated notes point at `tests/fixtures/banking/approval_policies.yaml` as
"the shape". On a Control Plane that already holds the pre-change `DeclaredArtifact` policy under
that key — every deployment that followed the archived example — `register_typed` refuses:
AUTHOR-EXECUTED, `TypeError: key 'acme-bank/approval-policy/credit-officer' is already bound to
artifact class 'approval-policy'; refusing to rebind it to 'ccf.approval-policy'`. The suites only
succeed because every closure skips the declared entry (`without_approval_policies`). The real
migration path is a NEW key and a new workflow definition version that pins it, which also means
pre-change executions cannot resume under the old definition hash (consistent with G5 (a), but
unstated). The fragment and the two dated notes must say so.

### 3.4 ADVISORY — confirmed on the tree, carried

| # | finding | raised by | verification |
| --- | --- | --- | --- |
| A1 | `APPROVAL_GATE_EVENT_CLASS` (transport) and `GATE_EVENT_CLASS` (primitive) are the same string with nothing pinning them equal; if they drift, S1 silently stops judging and only the engine backstop remains | cursor 1; reader F9 | AUTHOR grep: no test references the transport constant; `approval_gate` could alias it since it already imports the transport |
| A2 | `AmbiguousPinnedVersionError` escapes `check_approver_eligibility` at all three sites untyped: the engine's `eligible()` catches only `ApproverNotEligible`, so `resume` raises instead of refusing through `_refuse` (no audited refusal); the doors have no mapping, so a 500 | cursor 2; reader F5 | AUTHOR probe: two contents declaring `1.0.0` under one key → `resume` raised `AmbiguousPinnedVersionError`; the bound transport's `submit` raised the same. Fail-closed; the helper's docstring declares the raise as "broken deployment wiring, surfaced rather than judged", the precedent `resolve_hitl_policy`'s `TypeError` is likewise unmapped |
| A3 | no control covers the doors' `hitl-event-revalidation-refused` mapping; removing either `except` arm reddens only the roster's constant assertion | cursor 3; reader 5(b) | AUTHOR grep: only `test_auth_hardening.py` names the code. Tied to U2 |
| A4 | G2 (a) — eligibility BEFORE attestation at the transport — is pinned by no control: swapping the two blocks reddens nothing across 1583 tests; no shipped control combines an ineligible approver with a bad attestation | preserve F-2 | seat-executed; AUTHOR reading: T1 uses an unsigned plain policy, so attestation never runs in it |
| A5 | the "`_recorded_gate_verdicts` is not narrowed" preservation is pinned only along the missing-state axis; narrowing it by the starter, or by stamped eligibility, reddens no conflict control | preserve F-3 | seat-executed |
| A6 | an engine-site eligibility refusal is audited and reported as "no approval for this suspension has returned" — an auditor cannot tell "nobody approved" from "the approval was refused for eligibility"; brief §4 (6) says the audit event carries the reason | reader F3 | AUTHOR reading: `eligible()` discards the `ApproverNotEligible` message |
| A7 | no control checks that the engine judges the RIGHT gate's policy: both two-gate fixture gates pin one policy and `credit-officer-11` is eligible under both fixture policies | reader F4 | AUTHOR-EXECUTED: `policy_ref = workflow.definition.gate_policies.get(gate)` replaced by the first policy → `tests/workflow tests/hitl tests/http_api tests/mcp tests/conformance` **1363 passed, 0 red** |
| A8 | the controls-register S1 row says "every HTTP and MCP action submission reaches `submit` with a bound plane", and the adopters-guide note says the door refuses before attestation; the SDK's own local composition (`runtime/ccf_runtime/cli/local.py:136`) builds `InMemoryHitlTransport()` UNBOUND, on which S1 never fires and only the engine refuses | reader F6 | AUTHOR grep confirms the unbound construction |
| A9 | H2's "never authority, whatever is enqueued later" holds for transports that stamp `event_state_at_submit`; a user-implemented transport that records `None` keeps the old hole (the unstamped leg admits `None` while the gate is pending, as ruled for pre-change records); the fragment's user-transport migration line does not say so | reader F7 | AUTHOR reading of `_gate_authority` |
| A10 | `ApprovalGate.resolve`'s `Raises` names `ApproverNotEligible` but not `HitlEventRevalidationRefused`, which reaches it through `transport.submit` when the claim changes hands between `remove` and `submit`; the escalation, override and review primitives likewise | reader F8 | AUTHOR grep: the name appears in none of the four primitives |
| A11 | the sever seat's P2 and the reader's F1 are the same shape; recorded once as 3.2 | sever; reader | — |
| O-1 | the primitive-level attestation check is pinned by exactly one control; the gate-required tests cannot tell which layer refused because the transport re-verifies beneath the gate — pre-existing, not caused by the candidate | preserve | seat-executed |

### 3.5 Rejected or re-scoped

None rejected. The controls seat's accounting discrepancy (section 4) is a labelling correction, not
a finding. No reviewer restated a §3 choice or a §7 residual as a defect.

## 4. Accounting corrections to the candidate's own evidence

- **"25 red: 9 BEHAVIORAL / 16 MISSING CONTRACT" at the baseline** was measured at `0bb6d4b5`, where
  T5 called the shared covenant closure as shipped. The candidate's T5 calls
  `_register_covenant_closure(plane, as_shipped=True)`; run against the BASELINE helper that keyword
  does not exist, so the controls seat measured 8 BEHAVIORAL, 16 MISSING CONTRACT and 1 `TypeError`.
  Both statements are true of their own trees; the evidence report's figure describes the red-test
  commit, not the candidate's test files against the baseline.
- **Panel shape 2** (S1 severed, S3 kept): the brief's "T6's resumption assertions still hold" is
  measured only up to T6's first resumption; the test stops at its door assertion (line 320) and its
  final resumption to `released` is not reached (sever seat).
- **Docs tests**: the seat counted 320 passed where the evidence said "319 + the retirement report";
  same population.

## 5. Reviewer accounting

All three CLIs returned the token, answered the negative control correctly (G1 yes, G2 yes, G3 no)
and dispositioned PROCEED. codex read 77,316 tokens and raised no finding; its "checked, not
defects" list matches the tree. cursor raised three advisories, all confirmed (A1–A3), and
correctly named SECTION F's files as unreviewed. gemini raised no finding; nine of its twelve
section-line citations resolve to the lines it describes, but **three (`C:1339` for
`_gate_authority`, `C:1332` and `C:1314` for the nonce and the revalidation) point past the end of
SECTION C (1,115 lines)** — the content claims are true of the tree, the citations are not; recorded
as a citation error in the pattern this host has measured before. The four Opus seats each proved
their interpreter imported their own worktree, left their worktrees clean, and labelled their
evidence as their own.

## 6. The unruled choices — the panel's assessment (for the owner's ruling)

**U1 — `HitlEventRevalidationRefused(ValueError)`, a sibling of `GateActionError`, not a
subclass.** All four reviewing seats recommend KEEP. codex: keep the ValueError family; consider a
shared base before a public release if callers are expected to catch one HITL refusal class. cursor:
keep; a subclass would need a cycle-free base module; `PermissionError` would collide with the
eligibility and attestation mappings. gemini: keep; it is a state/concurrency refusal, not an
authority one. reader: keep; no code in `src/` or `runtime/` catches `GateActionError`, so a sibling
breaks no caller; a shared base would merge two meanings for one catch convenience; subclassing
would make a primitive-specific error the transport's for other event classes too. Reader's addition:
the owner should confirm that "GateActionError-class" means ValueError-family and not
PermissionError (T11/T14 already assert that reading), and fix A10.

**U2 — `hitl-event-revalidation-refused` at HTTP 409 and in the MCP refusal body.** All four
recommend KEEP: 409 says "the target changed under you; re-read and retry"; a distinct code lets a
client know nothing was consumed (the nonce is reusable — T14); reusing a signed-binding code would
conflate nonce reuse with event movement; 403 reads as authority and discourages retry; 422 claims a
malformed request; unmapped is a 500 and not a door. Reader's additions: the owner ratifies it as a
public wire constant; the fragment gains one migration line — a retry can legitimately land as a 200
whose receipt carries `submission.event_state_at_submit == "missing"`, which is inert, so clients read
the receipt, not only the status; and A3 (no door control for the mapping) is closed once ruled.

## 7. What the owner is asked to rule or decide (nothing here is done)

1. **3.1** — the SEC-001 hash-binding control: make the impostor an eligible principal, or add an
   eligible-but-stale-hash control beside it (test-only; the shape is measured).
2. **3.2** — a routed gate with no `gate_policies` entry: refuse at construction (a design choice
   beyond `D-IMPL-366`), or disclose; and correct the fragment's "Why".
3. **3.3** — the migration text: a new key and a new definition version; pre-change executions do
   not resume.
4. **U1 and U2** — ratify or change the exception class and the wire code.
5. **A1–A10** — carry by name, or fold any into the repair the rulings above authorize.

## 8. Provenance of the raw material (withheld from the tree, available on request)

`~/.claude/projects/-home-parkave-ccf-code/panel-save-2026-10-05/panel366/`: the payload and its
section files, `launch-reviewers.sh`, `{codex,cursor,gemini}.{out,err,rc}`, and each Opus seat's
output directory (`seat-controls`, `seat-sever` with its own driver and 37 diffs, `seat-preserve`
with `sabm.py` and its diffs, `seat-reader` with its probes), plus the author's verification
probes (`probe_ambiguous_pin.py`, `author-f1-*.txt`, `author_f1_probe.py`).

## 9. RULINGS (Dave, 2026-10-05 06:52 MST) and the follow-on delta

ChatGPT inspected the record and the three holds against the candidate and drafted the
recommendation; Dave supplied the five rulings after receiving that review. Neither inspection
re-ran the seats or the severings. (Attribution corrected 2026-10-05 11:12 MST on Dave's
instruction; the earlier wording credited the inspection to Dave.) **(1)** 3.1 — add an eligible-but-stale-hash control BESIDE the existing one;
the impostor control keeps proving the ineligible path and the second proves the hash term.
**(2)** 3.2 — disclose the policy-less gate and correct the fragment's "never constructs" sentence;
a construction-time refusal is NOT widened into this repair and is CARRIED as a follow-on.
**(3)** 3.3 — correct the migration text: a typed policy is a new key and a new definition version;
pre-change executions do not resume. **(4)** U1 and U2 RATIFIED: `HitlEventRevalidationRefused`
stays a `ValueError` sibling; the wire code stays `hitl-event-revalidation-refused` at HTTP 409;
the fragment says a retry can return 200 with a missing-state receipt that authorizes nothing.
**(5)** A1–A10 carried by name, except A4 — the eligibility-before-attestation control is test-only
and belongs in this follow-on.

Follow-on GO: tests and docs only; no production change (a disclosure sentence in an existing
fragment is docs); no merge, no closure; stop for a check of the delta. The delta:
`tests/workflow/test_engine.py::test_an_eligible_approvers_stale_hash_verdict_is_not_authority`
(added beside the impostor control, which is unmodified);
`tests/hitl/test_sec006_eligibility_controls.py::test_t1d_eligibility_is_judged_before_attestation`;
the fragment's `WorkflowFactory` and `ApprovalPolicy` entries (disclosure + migration), its two
ratification notes and the retry sentence; the two dated notes; two controls-register rows and the
S4 row's disclosure; `docs/SURFACE-CHANGES.md` reassembled. Carried by name: a construction-time
refusal of a policy-less routed gate; A1, A2, A3, A5, A6, A7, A8, A9, A10; O-1.

## 10. The follow-on delta, independently verified — DISPOSITION (2026-10-05 08:14 MST)

**Correction first (Dave, 08:09 MST).** The first wording of 3.1 and of the new control's docstring
said eligibility refuses the impostor "before the hash term is consulted". That is backwards: in
`_gate_authority` the hash term is the second conjunct and `eligible()` the last, so for the
impostor the hash refuses first and eligibility is never reached. The control was vacuous for the
hash term by OVERLAP — with the hash severed, the eligibility conjunct still excluded the ineligible
impostor. Corrected in both places at `82e1bb76`; the record keeps the dated note.

**Independent verification (verify2 seat — Claude Opus subagent, no session context, its own
worktree at `82e1bb76`, interpreter proven to import that worktree, INDEPENDENTLY EXECUTED):**

| step | measured |
| --- | --- |
| the code against the corrected docstring | the conjunct order in `_gate_authority` is event key, hash, action, missing-state guard, stamped/unstamped leg, `eligible()` last — **matches the docstring**; `submit` runs snapshot → eligibility → `resolve_hitl_policy` → `enforce_attestation` → the 6a lock where the nonce is consumed — matches C2's claim |
| unsevered | C1, the impostor control, C2 and the plain T1: all PASSED |
| C1 severed (hash term → `True`, in `_gate_authority` only; `_recorded_gate_verdicts` untouched) | C1 **RED** (the stale-hash verdict was admitted); impostor **GREEN**; whole `test_engine.py`: 1 failed / 39 passed, C1 the only red; `tests/workflow` + `tests/hitl`: 1 failed / 339 passed, C1 the only red. Restored; sha256 equal; git status clean |
| C2 severed (the eligibility block moved after `enforce_attestation`) | C2 **RED** — "refused, but by `SignedBindingRequiredRefused` rather than `ApproverNotEligible`"; plain T1 **GREEN**; `tests/hitl` + `tests/workflow`: 1 failed / 339 passed, C2 the only red. Restored; sha256 equal; git status clean |
| the seat's own probes (6 passed) | C1: an eligible correct-hash verdict resumes (positive control); the impostor with the CORRECT hash is refused — eligibility alone; a stale eligible verdict is excluded, not blocking, when a correct one follows. C2: an eligible principal with a valid attestation is admitted and one nonce spent (the attestation genuinely verifies); the same valid attestation from an INELIGIBLE principal is refused `ApproverNotEligible` with nothing recorded and no nonce; an ELIGIBLE unsigned submission is refused `SignedBindingRequiredRefused` — attestation still runs once eligibility passes |
| full suites unsevered | `tests/hitl` + `tests/workflow`: 340 passed |

The seat's observation, recorded as the seat's: the eligibility-before-attestation order is
visible only through the refusal TYPE on an unsigned submission, which is what C2 asserts; C2's
no-nonce assertion is order-independent because the nonce is consumed only inside the 6a lock. The
seat did not re-measure the author's "0 red in 1508 tests" figure for the pre-follow-on severing;
its populations were 40 and 340, within which C1 was the only red.

**Disposition.** The three blocking findings of this record are addressed by the follow-on as
ruled: 3.1 by C1 (seat-verified red under its severing, the impostor control still proving the
ineligible path), 3.2 and 3.3 by the fragment, the two dated notes and the register (docs). A4 is
closed by C2 (seat-verified). U1 and U2 are ratified. Carried by name: a construction-time refusal
of a policy-less routed gate; A1, A2, A3, A5, A6, A7, A8, A9, A10; O-1. **Nothing is merged, tagged,
released or closed by this record; `SEC-006` stays OPEN and the ledger stays 12 of 29.** The branch
tip at this disposition: the commit this section lands in, parent `82e1bb76`.
