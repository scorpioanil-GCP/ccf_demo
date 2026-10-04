# `D-IMPL-363` — SEC-005 signed-claims / time-window repair: CLOSE PANEL reviews

**Subject: the SHIPPED TREE.** Candidate `448a6c423121dfe9dfc3f9824b1cc37d3d6e9ef6`
on branch `repair-sec005-attestation`, base `2ca6cad5c3f1102a933cbe3bb2a95b7d82095a88`
(= `main` = `origin/main` at review time, verified on GitHub by Dave). Commits under
review: `41160183` (RED acceptance tests at both doors), `5b0008d7` (deterministic door
clocks and the concurrent same-nonce controls, still RED), `bebfa5ad` (the core repair),
`448a6c42` (the rewritten suites, the T10–T13 controls, the surfaces, the three page notes,
docstring prose, the roster retirement). Close-panel GO given by Dave on 2026-10-03 for
this candidate only.

**Judged against** `D-IMPL-363` — the Wave 3 design locked at `D-IMPL-356` (E1–E8) with the
thirteen choices C1–C13 as ruled — and its criterion, the design's §9 item 9, verbatim:
*"A signature presented on another `event_key`, another tenant, the opposite verdict, past the
window, with a reused nonce (on the reference transport), post-dated beyond the declared skew,
or under a key not declared for its subject in the pinned policy refuses with
`signed-binding-mismatch` / `-stale` at both doors; a signed submission succeeds under a wall
clock on both doors (the 353-06 limit is closed); `HitlPolicy`'s key and version appear in
dimension 2."*

**Scope:** this leg only. `SEC-006` (approver eligibility: a requester field, any `policy_ref`
interpretation) stays a BOUNDARY by ruling (C2) and was excluded from every reviewer's brief.
**Every reviewer was told the SDK is destined for a BANK** and to be more conservative than for
ordinary code. Dave named five points the panel had to answer and six observations the authoring
lanes had reported; all eleven are answered in §5.

**What this record does NOT do:** no production edit, no merge, no tag, no release, no
`SEC-005` closure. Findings are recorded and verified; none is fixed here — including the stale
prose in production (CR-363-04, CR-363-12) and in a published fragment (CR-363-03), which stay
as they are until a repair is authorized. The merge is Dave's act.

## 1. Reviewer seats and evidence status

Two kinds of evidence are kept apart throughout: **INSPECTED** (the reviewer read the tree or
the inlined source) and **INDEPENDENTLY EXECUTED** (the reviewer ran the tests or probes itself
and captured the output). "Reported" means evidence captured by the author's session, not
re-executed by that reviewer.

| seat | model / tool | subject | evidence | disposition | findings |
| --- | --- | --- | --- | --- | --- |
| **codex** | codex-cli 0.137.0, API-key auth | inlined payload on stdin | INSPECTED (122,052 tokens read) | **PROCEED** | 3 ADVISORY |
| **cursor** | cursor 3.19.13 | inlined payload on stdin, from a scratch cwd | INSPECTED | **PROCEED** | 6 ADVISORY |
| **gemini** | gemini CLI 0.35.3, `GOOGLE_API_KEY` | inlined payload on stdin | INSPECTED | **PROCEED** | 1 ADVISORY |
| **independent executor** | Claude Opus 5 subagent, no session context | its own detached worktrees at the pin AND at the base | **INDEPENDENTLY EXECUTED** | `SUITES_PASS_AND_EVERY_SEVERING_DISCRIMINATES` | 3 anomalies, 4 observations |
| **independent adversarial review** | Claude Opus 5 subagent, no session context | its own detached worktree at the pin, full tree access | INSPECTED + **INDEPENDENTLY EXECUTED** (the suites, its own severings, eleven probes) | **PROCEED** | 8 ADVISORY |
| **refuters** | 16 × Claude Opus 5 subagents, two lenses per review finding | their own detached worktrees at the pin | INSPECTED + INDEPENDENTLY EXECUTED | per finding, §3 | — |

The executing model (Claude Fable 5.1, the author of the repair) is excluded from every seat
above; it assembled the payload, resolved every citation against the pinned tree, re-ran each
reviewer's reproducing command or grep itself (§3), reproduced the three substantive Opus
findings with its own severings, and wrote this record.

**Read-proof before any reply was counted.** A canary (`Reply with exactly the single word
KESTREL`) was sent to each CLI first; all three answered `KESTREL` (rc 0). The payload began
with a token (`OSPREY-005`) that a reply must repeat; all three replies carry it on their first
line. Every quoted line in every external finding was then resolved against the pinned tree by
`grep` (codex 3/3, cursor 6/6 — one across a hard line wrap, gemini 1/1); every Opus finding's
quote was resolved by two refuters independently (16/16 resolved; none fabricated). Two reviewer
*clearances* did not survive verification and are recorded as rejected in §3 (both gemini's);
three Opus findings were narrowed by their refuters and are recorded as narrowed.

### Exact invocations (all from a scratch directory outside the repository)

```
printenv CODEX_API_KEY | codex login --with-api-key
timeout 570 codex exec --skip-git-repo-check - < payload.txt      # rc 0, 56 s, 7,480 B
timeout 570 cursor agent -p --mode ask -f          < payload.txt      # rc 0, 10,716 B
timeout 570 gemini -p -                            < payload.txt      # rc 0, 61 s, 4,238 B
```

`CODEX_API_KEY`, `CURSOR_API_KEY` and `GOOGLE_API_KEY` were read from the untracked
`homecams_v2/.env`; nothing was committed from it. Gemini's stderr carried only the known
`Both GOOGLE_API_KEY and GEMINI_API_KEY are set` notice. Payloads went on **stdin** (a single
argv string caps at 128 KB). The Opus seats ran as a workflow of 18 subagents (executor,
review, 16 refuters), each in a detached `git worktree` under the session scratchpad, each
verifying `HEAD` equal to the pin and `git status --porcelain` empty before and after its work,
each verifying that `ccf` and `ccf_runtime` imported from inside its own worktree.

## 2. The payload was HAND-ASSEMBLED, and here is what it left out

The close-time payload was assembled by hand from the shipped subjects (CLAUDE.md §3.1 calls
this conforming provided the omissions are named) and **inlined with line numbers, not
referenced by path**, because codex's sandbox on this host can exit 0 having read nothing.
398,762 bytes / 7,205 lines, sha256 `4f1ab970…`, scanned for secrets (0 hits; the two `sk-`
substrings are `task-definition`).

Inlined: the four commit messages after the base; the full `D-IMPL-363` entry; **all of
`src/ccf/hitl/identity_binding.py` and `src/ccf/hitl/transport.py`**; the base..candidate diff
of the four primitives, `ccf.hitl.__init__`, `ccf.hitl.principal` and all of `runtime/` (both
doors, the error codes, the runtime identity module); the two door acceptance suites, the
verifier-level suite (`tests/hitl/test_signed_binding_authority.py`), the T10–T12 controls
(`tests/hitl/test_sec005_attestation_controls.py`), the nonce controls from
`tests/hitl/test_transport_concurrency.py` and the signed-path / T13 region of
`tests/workflow/test_engine.py`; the diffs of the roster lint and its two tests, the
hash-transparency roster, the reserved-code roster, the MCP door roster (C8), the HTTP door
suite (C10) and `tests/hitl/test_principal.py`; the surface fragment; the `public/` diff and
the two citation re-points; the `openapi.json` and `docs/schemas/` diffs; the author's
reported evidence (the severing matrix, the examples comparison, the archive assertion text).

**NOT in the payload, so NOT reviewed by the external panel (each named it as unreviewed):**
the four primitive suites' diffs (`tests/hitl/test_approval_gate.py`, `test_escalation.py`,
`test_override.py`, `test_review_queue.py`), the body of `runtime/ccf_runtime/cli/commands/hitl.py`,
`src/ccf/contracts/canonical.py`, `src/ccf/replay/`, the rest of `src/` and `runtime/`, every
example tree, and `docs/schemas` beyond the hitl-policy file. The external panel's silence
about those is not evidence about them. They were covered by the **independent adversarial
review**, which had full tree access and produced the two most substantive findings of this
panel from exactly that uninlined material (CR-363-09, CR-363-10).

The brief listed what is **known and ruled** and forbade re-deriving it (K1–K8: the C1(a)
three-way compare; the SEC-006 boundary; the one trust source; the nonce contract; the names;
the unsigned CLI door; the fixture rule; the reported run counts and severing matrix) and put
the owner's five points, the six observations and ten adjacent questions (replay at the pinned
version; policy flips between verify and record; nonce burn and growth; a `kid` under two
subjects; window boundary semantics; the action vocabulary; discriminating power; document
accuracy; hash transparency; removed-API references).

## 3. Findings — verified against the pinned tree before being recorded

Every finding below was raised by at least one seat, its quoted line resolved against the
pinned tree, and its claim re-checked by the author (and, where marked, independently by the
refuters or reproduced by the author's own severing). Severity per CLAUDE.md §3.1. **No seat
raised a BLOCKING finding, and no refuter escalated one.** Fourteen ADVISORY findings are
carried; the three that most deserve Dave's attention are CR-363-09, CR-363-10 and CR-363-04.

### CR-363-01 — ADVISORY, CONFIRMED (RUN). A non-Python signer is told the function, not the bytes

Raised by codex (1), cursor (6) and the Opus review (OP-F-03, confirmed 2/2).
`src/ccf/hitl/identity_binding.py::sign_hitl_action` signs `canonical_bytes(claims)` and
`verify_hitl_action` recomputes them from the parsed claims — the rule of
`src/ccf/contracts/canonical.py::canonical_bytes`: RFC3339 **UTC at fixed microsecond
precision**, naive refused, sorted keys. The review measured the typed path sound: an
`issued_at` in UTC with microseconds, at a `+05:00` offset, or with zero microseconds
round-trips through `model_dump(mode="json")`, `model_dump_json()`, `model_validate` and
`model_validate_json` to identical canonical bytes, and `verify_hitl_action` admits every
re-parsed object. It also measured the gap: a signer that signs its own JSON with `issued_at`
rendered `2026-07-30T12:00:00Z` or `2026-07-30T17:00:00.000000+05:00` — both valid RFC3339 for
the same instant — is refused `signed-binding-invalid` at BOTH doors. That is fail-closed, so
nothing is admitted; but the rule is published nowhere an integrator reads: `openapi.json`
advertises `issued_at` as `format: date-time`, `public/how-to/security-and-deployment.md` §1.2
says "a detached JWS over the claims' canonical bytes", the fragment says "over
`canonical_bytes(claims)`", and no `public/` page mentions microseconds. Disposition: a
disclosure gap on an adopter-facing surface — ADVISORY, carried. The repair is one stated rule
on the door page and in the fragment (and, optionally, a `description` on the OpenAPI member).

### CR-363-02 — ADVISORY, CONFIRMED (RUN); one sub-claim STRUCK. The MCP tool advertises an unconstrained `attestation` object

Raised by codex (2), gemini (1), cursor (3) and the Opus review (OP-F-04) — the authoring
lanes' O4. `runtime/ccf_runtime/mcp/hitl_server.py::build_hitl_server` types the tool
parameter `attestation: dict[str, Any] | None`, so the advertised JSON Schema is
`{"anyOf": [{"type": "object", "additionalProperties": true}, {"type": "null"}]}` with zero
declared properties, while the HTTP body publishes the full typed `SignedHitlAction` with
`HitlActionClaims` at `additionalProperties: false`. The review drove five structural inputs
through the tool (a list, a string, `{}`, a dict missing `key_id`, valid claims plus one extra
field): every one refuses `signed-binding-invalid` with zero submissions recorded — **no
admission**. **Struck by the refuters (and by the author):** the review's sub-claim that "the
advertised schema is never exercised by any test" is FALSE —
`tests/mcp/test_hitl_server_door.py::test_the_tool_schema_carries_no_binding_field_and_no_capability`
reads the advertised `tool.parameters`, asserts the exact property set including `attestation`,
and asserts the loose arm as the recorded join residual `SEC353-J-01` (FastMCP's argument
model); the refuter severed the parameter and that test reddened. One refuter further held the
finding refuted as reporting C12(a)'s ruled shape; the other held the declared-contract gap
real. Disposition: the gap between what is DECLARED and what is ACCEPTED compounds a residual
already on record; ADVISORY, carried with `SEC353-J-01`.

### CR-363-03 — ADVISORY, CONFIRMED (TREE). One fragment sentence reads as a production replay re-verifier

Raised by codex (3); the Opus review reached the same reading under Q1.
`docs/surface-changes/005-the-signed-claim-set-and-the-time-window.md` says the verifier reads
no clock *"so the transport site, a primitive site and a replay re-verify identically"* (the
quote spans a hard wrap). The intent — a clock-free verifier makes identical re-verification
*possible* — is true; but no production path re-verifies a recorded attestation: the callers
of `enforce_attestation` in `src/` and `runtime/` are `InMemoryHitlTransport.submit` and the
four primitives only; nothing under `src/ccf/replay/` touches it, and `resolve_pinned` is
used by the workflow, agent and skill factories, never for a `HitlPolicy`. Control
`tests/hitl/test_sec005_attestation_controls.py::test_t12_replay_re_verification_reproduces_the_admission`
resolves the policy AT the recorded version (`ControlPlaneProtocol.resolve(key, version)`
from the `key@version` the record carries) and calls the verifier itself — it proves the
recorded data SUFFICES, not that the SDK performs it. The criterion's last clause requires the
key and version in dimension 2, not a replay service; codex, cursor and the review all read it
that way, and the review judged a pinned-version re-verifier correctly out of this wave.
Disposition: a wording overclaim in a published fragment — ADVISORY, carried; not edited
during review.

### CR-363-04 — ADVISORY, CONFIRMED (RUN). The `HitlPolicy` docstring's example is now a document the parser refuses

Raised by cursor (1). `src/ccf/hitl/transport.py::HitlPolicy`'s class docstring still offers
*"a document like ``{semver: "1.0.0", signed_binding_required: true}`` registered under the
deployment's chosen HITL-policy key"* as the shape behind the documented surface, and the
regenerated `docs/schemas/ccf.hitl-policy.json` carries that docstring as its `description`.
Under this candidate the model validator on `HitlPolicy` refuses exactly that document at parse
(pinned by
`tests/hitl/test_signed_binding_authority.py::test_a_required_policy_without_its_window_or_keys_is_refused_at_parse`).
An adopter who copies the example gets a validator error. This is stale prose the author's own
sweep missed (it grepped for the removed names, not for the example). Disposition: production
docstring + a generated artifact; ADVISORY, carried; **not fixed during review** by Dave's
instruction. The repair is one sentence plus a `tools/dump_schemas.py` re-run.
**REPAIRED on the branch at `b446e24f` under the post-panel repair GO — §9.**

### CR-363-05 — ADVISORY, CONFIRMED (RUN). The two doors answer a malformed attestation with different codes

Raised by cursor (2); codex, gemini and the review answered P5 the same way — the authoring
lanes' O3. The HTTP door refuses an attestation whose claims carry an undeclared field at
FastAPI body validation (`422`, `extra_forbidden`, `loc` ending at the field); the MCP door
refuses it inside the tool with `signed-binding-invalid`; a malformed signature (`""`, `abc`,
`..`) refuses `403 signed-binding-invalid` at HTTP. Neither admits anything and neither reaches
the verifier; the asymmetry is in the taxonomy a client sees. Pinned at both doors by
`tests/http_api/test_signed_binding_door.py::test_http_a_client_cannot_state_assurance_in_the_claims_or_the_body`
and the MCP door suite. Disposition: ADVISORY, carried; a uniform malformed-attestation code
is a door-taxonomy question for its own entry.

### CR-363-06 — ADVISORY, CONFIRMED (TREE). One `-stale` code for three conditions; mismatch fields only in the message

Raised by cursor (4) — the authoring lanes' O2. `SignedBindingStaleRefused` is raised for an
expired `issued_at`, a post-dated one, and a reused nonce; the doors map all three to
`signed-binding-stale`. `SignedBindingMismatchRefused` embeds the list of disagreeing fields in
its message and carries no typed discriminator. E6 reserved exactly the two codes (ruled); the
messages do distinguish the cases (`expired`, `post-dated`, `already presented`; the field
list), and the review notes that collapsing them in the code denies a prober a
replay-vs-clock oracle. A SOC that routes "clock skew" apart from "replayed nonce" has only
message text to do it with. Disposition: diagnostics, not enforcement — ADVISORY, carried.

### CR-363-07 — ADVISORY, CONFIRMED (RUN). The reference transport's seen-nonce set grows for its lifetime

Raised by cursor (5); measured by the review (500 admissions grew the set from 2 to 502; no
evict/prune API). `InMemoryHitlTransport.__init__` declares `_seen_nonces` with the comment
*"Retained for the transport's lifetime; a user-implemented transport stays as replayable as
before until the Protocol amendment (1.0.3, its own entry)"* (quote resolved across a wrap).
It is the in-process reference implementation, the growth is documented in place, and the
Protocol amendment is deferred by the ruling's own text. Disposition: ADVISORY, carried with
the 1.0.3 amendment.

### CR-363-08 — ADVISORY (test coverage). The product-hash compare is pinned at the verifier level only

Raised by codex under Q7 and by the executor (observation 5). Severing the
`product_content_hash` compare in `enforce_attestation` reddens exactly one control,
`tests/hitl/test_signed_binding_authority.py::test_verifier_refuses_an_attestation_over_another_product_hash`,
and no door-level test (the two door rosters carry controls for exactly the seven axes §9
item 9 names at the doors, plus the wall-clock positive). §9 item 9 names no product-hash
clause; at a door the minted binding's hash is the body's, so a claim over a different hash is
exactly what the verifier compare catches; the enforcement is proven by the severing.
Disposition: ADVISORY, carried; a door-level sibling at each door is test-only.

### CR-363-09 — ADVISORY, CONFIRMED (RUN, reproduced by the author). Three of the four primitives' OWN verification is undiscriminated

Raised by the Opus review (OP-F-01), confirmed 2/2 by refuters who re-ran the severings in
their own worktrees, and **reproduced by the author**: disabling the
`if resolved_policy is not None and resolved_policy[1].signed_binding_required:` branch in
`src/ccf/hitl/escalation.py::ExceptionEscalation` or in
`src/ccf/hitl/review_queue.py::ReviewQueue` leaves `tests/hitl tests/http_api tests/mcp
tests/workflow/test_engine.py` at **876 passed**; disabling the same branch in
`src/ccf/hitl/approval_gate.py::ApprovalGate` reddens exactly
`tests/workflow/test_engine.py::test_the_approval_gate_verifies_the_attestation_independently_of_the_transport`
(the gate-independence control this wave added, whose docstring says why T13 cannot do the
job). The review also severed `OverrideBoundary` with the same result. Every signed test in the
three primitive suites binds the transport too, so the transport's refusal at submit masks
whether the primitive verified at all. The review demonstrated the consequence: with an
unbound transport and a policy-bound `ReviewQueue`, the shipped tree refuses
`SignedBindingRequiredRefused` and the event stays pending, while the severed tree ADMITS an
unsigned release and records `attestation: None`. Double verification (D-IMPL-69) is REAL at
the pin — the production code verifies at both layers — but for three primitives nothing pins
it. Disposition: ADVISORY (no invariant is violated at HEAD; a test-coverage gap that a later
"drop the duplicate read" refactor would walk through unnoticed); carried; the repair is three
test-only siblings of the gate's control, one per primitive.
**REPAIRED on the branch at `b446e24f` under the post-panel repair GO — §9.**

### CR-363-10 — ADVISORY, CONFIRMED (RUN, reproduced by the author). A tenth verifier condition is pinned by nothing: the protected header's `kid` against the claimed `key_id`

Raised by the Opus review (OP-F-02), confirmed 2/2, **reproduced by the author**: disabling
`if declared_key_id != signed.key_id:` in `src/ccf/hitl/identity_binding.py::verify_hitl_action`
leaves the same 876 tests green. The check is load-bearing: `enforce_attestation` tests the
CLAIMED `signed.key_id` against the policy's per-subject map, while the provider verifies the
signature under the key named by the PROTECTED HEADER's `kid`; this comparison is what ties
the two together. With two keys declared for one approver (routine during rotation), a holder
of kid-B who signs and presents `key_id: kid-A` is refused at the pin and would be ADMITTED
without this check — with the dimension-2 block attributing the signature to a key that did not
make it. The subject attribution stays right (both keys are the same approver's), the key
attribution becomes a lie. Disposition: ADVISORY (the shipped tree refuses it; the gap is that
no test would notice its loss); carried; the repair is one verifier-level negative and, where a
second key per subject is cheap, one at each door.
**REPAIRED on the branch at `b446e24f` under the post-panel repair GO (the verifier-level
negative; the door siblings carried) — §9.**

### CR-363-11 — ADVISORY, NARROWED. "The CLI door is unsigned-only" needs its next clause to be read

Raised by the Opus review (OP-F-05) and under its Q10; refuters split. The mechanics are true
and were measured end to end: `runtime/ccf_runtime/cli/commands/hitl.py::_submit` posts the
document file verbatim, so a hand-built file that carries an `attestation` reaches the HTTP
door signed and is verified there. The review inferred that the headline *"The CLI door is
unsigned-only (E8)"* on the door page and in the fragment is therefore false. The correctness
refuter rejected the inference: the phrase is the ruling's own (E8: *"the CLI door is
unsigned-only in 1.0.2 and the door page says so"*), and the clause that follows it on both
surfaces — *"posts the action document verbatim and has no signing of its own; a document that
carries no `attestation` is refused under `signed_binding_required: true`"* — discloses exactly
the pass-through. Disposition: the ruled wording stands; the risk the review names (a
deployment review concluding the CLI path is inert and leaving it out of the signing-key
inventory) is real enough for one more sentence on the door page — "a document that already
carries an attestation is forwarded unchanged and verified at the HTTP door"; ADVISORY,
carried as wording.

### CR-363-12 — ADVISORY, CONFIRMED (TREE, reproduced by the author). Four dead imports left by the `trusted_keys` removal

Raised by the Opus review (OP-F-07), confirmed 2/2. `JsonWebKey` and `Mapping` each occur
exactly once in each of `src/ccf/hitl/approval_gate.py`, `escalation.py`, `override.py` and
`review_queue.py` — the import line; their only use was the removed constructor parameter.
mypy and the lints do not name unused imports and the Makefile runs no ruff/flake8 check.
Cosmetic in itself; for an auditor tracing C6(a)'s "one trust source, no constructor fallback",
a stale `JsonWebKey` import on four HITL primitives reads as if key material still enters
them. Disposition: ADVISORY, carried; not fixed during review.

### CR-363-13 — ADVISORY, CONFIRMED (RUN). Two reason changes behind identical archived node ids are disclosed in the commit, not on the published surfaces

Raised by the Opus review (OP-F-08, confirmed 2/2) and the executor (anomalies 1 and 2),
answering the owner's P4. (a) The two archive parametrizations of
`tests/examples/test_artifact_schema_headers.py::test_every_artifact_directory_passes_the_header_check`
are red at the base for ONE document each (`scope-mapping.yaml`) and at the pin for TWO: the
new `HitlPolicy` cross-field validator now refuses
`archive/examples/05-workflow-hitl/artifacts/hitl-policy.yaml` and its `06-decision-replay`
twin (`signed_binding_required: true` without the window and keys). (b) Under
`--run-archived`, the 71 archived nodes of `tests/examples/test_decision_replay_output.py` and
`test_workflow_hitl_output.py` error at setup on both sides with identical rosters, but for a
different reason: `KeyError: 'events'` at the base, `ImportError: sign_principal_binding` at
the pin — the archived programs import the removed name. Both are consistent with
`D-IMPL-351` (the archive is not repaired) and both are stated in the candidate's commit
message, so "the same 29 failing node ids as `main`" is honest as a set claim and the commit
record is complete. What no published surface says is that two in-tree `ccf.hitl-policy`
documents now fail REGISTRATION (the pages say only that the programs no longer import).
Disposition: ADVISORY, carried; one sentence in the fragment's `HitlPolicy` migration bullet.

### CR-363-14 — ADVISORY (prose). The in-body-import comment in the archived example suites claims a visibility the deferral does not buy

Raised by the executor (anomaly 3). The comment above the deferred import in
`tests/examples/test_decision_replay_output.py` says the module-level import would be a
collection error and that "deferred here, the module collects and the gap stays visible as a
failing archived assertion rather than an invisible one." Measured: under a default run the
module is DESELECTED (`71 deselected`), so nothing is visible; under `--run-archived` every
node errors at SETUP on the archived program's own import of the removed name, so the
assertions never run either way. The deferral buys collection, which was its instruction, not
visibility. Disposition: ADVISORY, carried; a comment rewrite.

### Rejected or corrected reviewer statements

- **gemini, P3 clearance — REJECTED.** Gemini wrote that non-Python signers "are instructed in
  the updated `security-and-deployment.md` to sign the canonical bytes." The page says "a
  detached JWS over the claims' canonical bytes" and defines nothing; CR-363-01 stands, with
  the review's RUN evidence.
- **gemini, P4 clearance — UNSUPPORTED, replaced by measurement.** Gemini wrote "no non-archive
  artifact in the tree is broken by the new policy validation" without having the artifacts
  (they were not inlined). Measured by the author and independently by the review: a tree-wide
  grep for `signed_binding_required: true` outside `archive/` hits only tests (which state the
  window), prose, the schema description and the docstring example of CR-363-04; no artifact
  document under `examples/` references `signed_binding_required` at all. The only policy
  documents the new validator refuses are the two archived ones (CR-363-13).
- **gemini, Q1 — accurate about the test, incomplete about production.** T12 does resolve the
  pinned version from the recorded `hitl_policy_ref`; codex, cursor and the review add that no
  production replay path does (CR-363-03).
- **Opus review OP-F-04, one sub-claim — STRUCK** (the advertised MCP schema IS pinned by a
  test; CR-363-02).
- **Opus review OP-F-05, the inference — REJECTED; the mechanics — kept** (CR-363-11).
- **Opus review OP-F-06 — NOT A DEFECT of this candidate; recorded under P2.** The review
  measured that `tools.lints --all` stays silent when a keyless field reusing the retired
  qualified name `HitlActionSubmission.signed_binding` returns, because the lint's suppression
  set is the measured roster file and that name is in it. Its reproduce-refuter confirmed the
  measurement; its correctness-refuter refuted the finding as a candidate defect: the roster
  file is byte-identical base→candidate, the base ALREADY carried that name keyless and
  lint-silent (`signed_binding: SignedPrincipalBinding | None = None`, no key), and the
  candidate ADDED the two roster tests that turn the name's return red. The split in the gate
  (lint for new names, roster tests for a retired name's return) is `D-IMPL-243`'s ruled
  design, stated in `tools/lints/base_roster.py`. Optional polish, not a finding: the lint
  could subtract `RETIRED_BY_RULING` from the roster it loads, making a returned retired name
  "new since base" to the lint itself.

### Retractions

None. No reviewer produced a verbatim quotation contradicting K1–K8.

## 4. Independent execution — exact commands and results (INDEPENDENTLY EXECUTED by the Opus 5 executor, in its own worktrees)

Worktrees: a detached checkout of `448a6c42` under the session scratchpad (`exec-448a6c42`)
and a second at the base `2ca6cad5` (`base-2ca6cad5`); `git rev-parse HEAD` verified equal to
the pin / the base and `git status --porcelain` empty before and after; `ccf` and
`ccf_runtime` verified to import from inside each worktree.

Interpreter and environment for every command below:
`PYTHONPATH=.:src:runtime:tests /home/parkave/ccf_wt/qual-a4cf2fb7/.venv/bin/python -B`,
pytest with `-p no:cacheprovider -q -rA --tb=short`, `__pycache__` purged under `src/`,
`runtime/` and `tests/` before every run that followed an edit.

1. **Baseline** on the five attestation suites (`tests/http_api/test_sec005_attestation_door.py`,
   `tests/mcp/test_sec005_attestation_door.py`, `tests/hitl/test_signed_binding_authority.py`,
   `tests/hitl/test_sec005_attestation_controls.py`, `tests/hitl/test_transport_concurrency.py`):
   **57 passed**, of which **20** are the door acceptance tests (11 HTTP, 9 MCP).
2. **Nine severings, one at a time, with the executor's OWN driver** (original bytes saved and
   hashed; occurrence count asserted **1** before each write; bytes restored and sha256
   re-verified equal after each). Reds, each named for the comparison it severed:
   S1 tenant **3** (verifier, HTTP, MCP); S2 event_key **3**; S3 subject, both legs **3**
   (all in-process — the doors bind the subject through the capability and the key map before
   the compare); S4 action/verdict **3**; S5 product hash **1** (verifier only, CR-363-08);
   S6 key not declared for the subject **3**; S7 post-dated **3**; S8 expired **3** (S7 and S8
   disjoint — the window is directional in the tests as in the code); S9 nonce reuse **5**
   (the transport race control, and the reuse + concurrent controls at each door). Every
   severing discriminates; the sets are identical to the author's reported matrix.
3. **Final restore:** sha256 equal; `git status --porcelain` empty; the five suites **57 passed**.
4. **Wider (pin):** `tests/hitl tests/http_api tests/mcp` **837 passed**;
   `tests/test_surface_drift.py tests/test_surface_completeness.py` **26 passed**;
   `tools.lints --all` **rc 0** with zero output — positively controlled: a weak prose literal
   planted in `src/` left rc 0 (below the prompt-shape threshold), a prompt-shaped literal
   produced rc 1 with a CINV-01 finding; both plants restored from saved bytes.
5. **Examples comparison (pin vs base):** the ten `tests/examples` modules that fail at the pin
   fail at the base: **29 failed / 29 failed**, sorted node-id sets identical, both set
   differences empty. The two archive schema-header parametrizations' assertion text differs
   as CR-363-13(a) records; the 71 archived nodes' setup error differs as CR-363-13(b) records.
6. **Removed-API references (pin):** 15 hits in 7 files, every one an absence statement or a
   dated note (the `identity_binding` module docstring; the three page notes; the fragment;
   the two citation re-points); none live. `grep` for the definitions of the four removed names
   returns nothing.
7. **Anomalies:** the two reason changes (CR-363-13), the comment (CR-363-14), and two
   observations folded into §5/§6 (T10 asserts `version` by truthiness and the exact pin is
   asserted in the authority suite; S3's three reds include two generically named controls
   whose bodies the executor read and confirmed pin the subject compare).

The **independent adversarial review** repeated the baseline and its own severing shape in its
worktree (`tests/hitl tests/http_api tests/mcp tests/contracts tests/replay` **1124 passed,
1 skipped** — the Fluree snapshot pin, no network; `tests/workflow tests/crossproc tests/cli`
**400 passed**; the tool suites `tools/lints/tests` 601, `tools/product_gates_tests` 48,
`tools/publish_scan_tests` 53 passed; `tools/docs_tests` 301 passed and the one standing red,
`tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current`, confirmed
failing identically at the base), and additionally severed thirteen conditions of its own
choosing — finding the two undiscriminated ones recorded as CR-363-09 and CR-363-10, and two
undiscriminated-but-harmless ones recorded in §6.

## 5. The owner's five points and the six observations, answered

- **P1 — `hitl_policy_ref` and dimension 2: SATISFIED (all seats; RUN by the review).**
  `InMemoryHitlTransport.submit` stamps `hitl_policy_ref = HitlPolicy.pinned_ref(key=, version=)`
  on the recorded copy from the SAME `resolve_hitl_policy` tuple that feeds the verifier; the
  primitives build `src/ccf/hitl/approval_gate.py::HitlActionRecord` from that recorded
  submission and serialize it into `hitl_actions_block`;
  `src/ccf/replay/record.py::build_replay_record` lands it verbatim in
  `PolicyBindingsSnapshot.hitl_actions`. The review drove one attested gate resolution and
  printed the block: the ref `acme-bank/hitl/attestation-policy@c91da308…` and the full
  attestation travel in dimension 2. The version is the Control Plane's version identifier —
  `ControlPlaneRegistry.register` sets it to the artifact's content address (the review measured
  `registry.versions(key) == (content_hash(policy),)` while the policy's semver was `2.7.3`) —
  which is the right replay identity: it names the exact document that judged the action, and
  `ControlPlaneProtocol.resolve(key, version)` reproduces it. Nothing the clause requires is
  absent. (O1: not a defect; disclosed in the fragment.) Noted by the executor: control T10
  asserts the recorded `version` by truthiness; the exact `key@version` equality is asserted in
  `tests/hitl/test_signed_binding_authority.py`, so the clause is pinned by two tests rather
  than by T10 alone.
- **P2 — roster retirement preserves lint strength: YES at the gate; the lint binary alone
  never caught a retired name's return (probed by the review, confirmed by two refuters).**
  `tools/lints/base_roster.py::RETIRED_BY_RULING` is read by both roster tests:
  `tools/lints/tests/test_base_roster.py::test_every_roster_name_is_still_a_defaulted_field_at_head`
  subtracts it, and `test_every_retired_name_was_in_the_roster_and_is_gone_at_head` requires each
  retired name to be IN the measured roster AND ABSENT at HEAD. Probe A (re-add a keyless
  `signed_binding` to `HitlActionSubmission`): `tools.lints --all` stays silent — the name is in
  the measured roster file, which is byte-identical base→candidate, and the base ALREADY had
  that keyless field lint-silent — and the two roster tests go red (2 failed). Probe B (a
  brand-new keyless field on `HitlPolicy`): the lint names it, rc 1. The keyless-roster control
  keeps its exact-set assertions over the live roster. Net: one test became two and both drift
  directions are red; no defaulted-field change the gate caught before is missed now. The
  optional polish (the lint subtracting `RETIRED_BY_RULING` from its suppression set) is in §3.
- **P3 — canonicalization across wire and typed claims: CORRECT BY CONSTRUCTION for an SDK
  signer (RUN); a DISCLOSURE GAP for others (CR-363-01).** The review's probe: three `issued_at`
  renderings, four serialization round trips, identical canonical bytes every time and
  `verify_hitl_action` admitting each; and two valid RFC3339 renderings of the same instant,
  signed as wire JSON, refused `signed-binding-invalid` at both doors. The rule is stated only
  in `src/ccf/contracts/canonical.py`.
- **P4 — the archived examples' added failure reason: HONEST AS A SET CLAIM AND IN THE
  COMMIT; UNDER-DISCLOSED ON THE PUBLISHED SURFACES (CR-363-13).** Reproduced independently by
  the executor and the review on both trees; no non-archive artifact document is affected
  (measured twice, §3). The migration (three more members or refusal at registration) is in
  the fragment's `HitlPolicy` entry and on the door page. (O6: same.)
- **P5 — malformed attestations and the MCP schema: TWO ADVISORIES, NO ADMISSION (CR-363-05,
  CR-363-02).** Neither door admits a malformed attestation; the HTTP door refuses at body
  validation with `422` naming the field, the MCP door inside the tool with
  `signed-binding-invalid` for every structural error; the MCP parameter's advertised schema
  is unconstrained while the HTTP contract is typed. The asymmetry leaks nothing a FastAPI
  boundary does not already say and admits nothing. (O3, O4: the same two advisories.)
- **O2 — one code, message-only field names:** CR-363-06, ADVISORY.
- **O5 — double verification with both layers bound: REAL in production, PINNED for the gate
  only (CR-363-09).** When a gate and the transport are both bound, both call
  `enforce_attestation`; the transport's refusal at submit is what an outside observer sees
  first, which is why the gate-independence control binds the gate alone and proves its own
  verification refuses — and why the same control is owed to the other three primitives. The
  nonce is consumed once, by the transport, by design (E4): a verifier that burned it would
  break idempotent double verification (D-IMPL-69).

## 6. Checked, not defects — consolidated across the seats

- **Replay at the pinned version (Q1):** `ControlPlaneProtocol.resolve(key, version)` exists
  and T12 uses it from the recorded ref; `resolve_hitl_policy` resolves latest for ADMISSION,
  which is correct; there is no production replay re-verifier and the criterion does not ask
  for one (codex, cursor, review; CR-363-03 is the wording).
- **Policy flips between sites (Q2):** `submit` resolves ONCE and the single tuple feeds both
  the stamp and the verifier, so the recorded ref always names the policy that judged the
  recording; across the primitive/transport seam two resolutions can see two versions, and
  every interleaving is fail-closed or consistent — admitted only if both admit, recorded under
  the transport's (review, by reading; codex, cursor).
- **Nonce burn and race (Q3):** after the insert inside the lock the remaining statements
  (`pop`, `model_copy`, `append`) cannot raise, so no refusal burns a nonce and lands nothing;
  the same nonce with different signed claims for the same event is refused; the same nonce on
  a different `event_key` is admitted — C11(a)'s per-`(tenant, event_key)` scope as ruled;
  two racing presentations cannot both land (review, RUN; the concurrent controls at both
  doors and at the transport). Growth is CR-363-07.
- **A `kid` declared under two subjects (Q4):** the verifier offers only
  `keys_for(claims.subject_id)`, so a shared `kid` passes the key check for either subject and
  it is the subject compare that refuses a claim for the other; at a door the binding is minted
  from `authorized.principal`, so the two legs of that compare are one condition, and
  in-process `submit`'s `PrincipalMismatchRefused` (checked before the policy is resolved)
  makes them transitively equivalent — which is why the review's severing of EITHER leg alone
  reddened nothing and the author's S3 severed both. Residual the review names: a user
  transport calling the public `enforce_attestation` without that principal check needs both
  legs, and both are there (review, RUN).
- **The detached-JWS shape guard in `verify_hitl_action` (review, RUN):** severing it reddens
  nothing because every malformed signature still refuses `signed-binding-invalid` downstream
  (the provider's own contract validation raises, and the verifier's `except` arm catches it);
  defense in depth with no behavior delta.
- **Window boundaries (Q5):** `ahead > skew` and `behind > max_age` — equality is admitted on
  both edges, measured at exactly 300 s / 60 s and at `skew=0`; a not-required policy may
  omit the window; flipping it to required without the three members is refused at parse, i.e.
  at registration (review, RUN; codex, cursor).
- **Action vocabulary (Q6):** `HITL_ACTIONS = {approve, reject, override, annotate}` covers
  `GATE_ACTIONS` and `ESCALATION_ACTIONS` (`{approve, reject}`) and the override/review
  derived actions; the three-way compare refuses a presented X whose binding verdict differs,
  and the review severed each leg separately and watched a distinct control redden.
- **Discriminating power (Q7):** every §9 item 9 clause is pinned by one verifier-level
  control and one control at EACH door where the clause is reachable at a door; the nonce by
  the transport race control and two controls at each door; subject by three in-process
  controls; product hash by one verifier-level control (CR-363-08). The review's hunt for a
  tenth undiscriminated condition found two that matter (CR-363-09, CR-363-10) and two that
  do not (this section). The wall-clock positive passes at both doors under `datetime.now(UTC)`.
- **Documents against the tree (Q8):** the review compared every `After:` shape line in the
  fragment with `inspect.signature` for fourteen signatures (the verifier, the resolver, the
  signer, the four constructors, the resolve/release/reject methods) — all exact, keyword-only
  markers, defaults and return types included; the refusal ORDER in the fragment's verifier
  bullet matches the code; `openapi.json` and the hitl-policy schema carry what the fragment
  says they carry; the three page notes are dated and cite `D-IMPL-363` and `D-IMPL-351`.
  The sentences found untrue of the tree are CR-363-03 and CR-363-04; the clause needing its
  next clause is CR-363-11.
- **Hash transparency (Q9):** `HitlPolicy()` hashes equal to `HitlPolicy(...=None)` for all
  three members; a submission without `attestation` equals one with `attestation=None`, and
  likewise `hitl_policy_ref`; a POPULATED attestation changes the submission's address, two
  attestations differing only in the nonce differ, and a populated ref changes it — correct in
  both directions (review, RUN); `tests/contracts/test_hash_transparency.py`'s exact-set
  roster passes against the tree.
- **Removed API (Q10):** absent from live `src/`, `runtime/`, `public/` (non-archive),
  `docs/schemas`, `openapi.json` and the manifest; the only mentions are the module docstring
  that says the names are gone and the dated page notes (executor, review); mypy clean on 242
  files; the CLI door signs nothing (E8; CR-363-11 for the wording).
- **Scope discipline:** no seat reported on `SEC-006`; no requester field and no `policy_ref`
  interpretation appear in any diff line.

## 7. Disposition

All four reviewing seats returned **PROCEED** and the independent executor returned
`SUITES_PASS_AND_EVERY_SEVERING_DISCRIMINATES`. Verified findings: **fourteen ADVISORY
carried (CR-363-01 … CR-363-14)**, of which eleven are documentation, diagnostics or
reference-implementation posture, and three are test-coverage gaps in the candidate's own
proof machinery that a later refactor could walk through unnoticed — CR-363-09 (three
primitives' own verification undiscriminated), CR-363-10 (the header-`kid` check unpinned) and
CR-363-08 (the product-hash compare pinned at the verifier only); plus one optional polish
item on the lint's suppression set (§3, OP-F-06). **No BLOCKING finding.** No retractions.
Two gemini clearances were rejected; one Opus sub-claim was struck, one Opus inference
rejected, one Opus finding re-classed as not a defect of this candidate. **After the panel, Dave gave a repair GO
limited to CR-363-04, CR-363-09 and CR-363-10; §9 records that delta (`b446e24f`), its
severing proof, its focused independent review, and one further advisory it raised
(CR-363-15).** Nothing in this record merges, tags, releases, or closes `SEC-005`; the
identifier's row stays OPEN and the merge decision is Dave's. The suite counts and the
severing results in this record remain reported evidence to Dave; the ones he can re-run are
the executor's commands in §4 and the Opus seat's in §9.

## 8. Provenance of the raw material (withheld from the tree, available on request)

Kept in the session scratchpad and delivered to Dave as files: `payload.txt` (sha256
`4f1ab970…`), `codex.out` (`6131426a…`), `cursor.out` (`2c1d5509…`), `gemini.out`
(`f4b24744…`), the three canary outputs, the author's severing driver and its JSON report, the
executor's saved bytes and hashes, the review's eleven probe scripts, the workflow journal with
all eighteen subagents' structured returns, and the author's own verification outputs. They
are not committed because they carry hundreds of line-number citations that would move the
citation-coverage population; this record cites by `path::Symbol` only.

## 9. Post-panel repair delta — CR-363-09, CR-363-10, CR-363-04 (repair GO, 2026-10-03)

**The GO**, verbatim: *"Repair GO limited to CR-363-09, CR-363-10, and CR-363-04 on
repair-sec005-attestation. Test additions plus the policy docstring/schema correction only; no
enforcement changes. Prove each new control discriminates by severing its guard individually,
restore byte-for-byte, and rerun green. Update the review record with exact evidence and
obtain focused independent review of the delta. Commit, push, and stop. Carry the other
advisories. No merge, tag, release, or SEC-005 closure."*

**The delta:** one commit, `b446e24ff048ea0be7ac5fdc7a95cae77e5ec9a9` on top of this
record's `ff120b46`, six files. Production changes only in prose: the `HitlPolicy` class
docstring in `src/ccf/hitl/transport.py` and its regeneration into
`docs/schemas/ccf.hitl-policy.json` by `tools/dump_schemas.py`; `openapi.json` is unchanged by
regeneration. Four test files gain one control each. **The other eleven advisories
(CR-363-01, -02, -03, -05, -06, -07, -08, -11, -12, -13, -14) are carried unchanged.**

### What was added

- **CR-363-09 →** `tests/hitl/test_escalation.py::test_escalation_verifies_the_attestation_independently_of_the_transport`,
  `tests/hitl/test_override.py::test_override_verifies_the_attestation_independently_of_the_transport`,
  `tests/hitl/test_review_queue.py::test_review_queue_verifies_the_attestation_independently_of_the_transport`.
  Each binds the primitive to the ruled policy over a transport constructed bound to NO
  Control Plane (`InMemoryHitlTransport()` — it resolves no policy and verifies nothing), so
  whatever refuses is the primitive's own `enforce_attestation`: an unsigned action refuses
  `SignedBindingRequiredRefused`; a genuine signature over the OTHER action (escalation
  `reject` against a presented `approve`; override `override` against the derived `approve`;
  review queue `reject` against the derived `approve`) refuses `SignedBindingMismatchRefused`;
  after both refusals the event is still pending and nothing is recorded; the honest attestation
  is then admitted and recorded with `hitl_policy_ref` `None` — the right expectation for a
  transport that resolved nothing. Siblings of the `ApprovalGate` control in
  `tests/workflow/test_engine.py`, which is untouched.
- **CR-363-10 →** `tests/hitl/test_signed_binding_authority.py::test_verifier_refuses_an_attestation_whose_key_id_is_not_the_signing_kid`.
  Two keys are declared for ONE approver (the rotation shape, so neither the key-declared check
  nor the signature check can be what refuses); a signature made with the rotation key and
  presented with `key_id` naming the other key is refused — `verify_hitl_action` names the
  disagreement (`declares kid`) and `enforce_attestation` refuses `SignedBindingInvalidRefused`
  before any claim is compared; the same signature honestly labelled is admitted, so the
  refusal is the comparison's, not the key map's.
- **CR-363-04 →** the `HitlPolicy` docstring now gives the not-required minimal document and
  the full required shape (window + per-subject keys), cites the finding, and the schema
  description is that docstring regenerated. The stale example occurs nowhere in the tree.

### Proved by severing (the author; reported evidence)

Each guard disabled alone — production bytes saved, one occurrence asserted, `__pycache__`
purged, `tests/hitl tests/http_api tests/mcp tests/workflow/test_engine.py` run under `-B`,
bytes restored, sha256 equal — baseline **880 passed**:

| severed guard | red | the one red test |
| --- | --- | --- |
| escalation's own enforcement branch | 1 | `test_escalation_verifies_the_attestation_independently_of_the_transport` |
| override's own enforcement branch | 1 | `test_override_verifies_the_attestation_independently_of_the_transport` |
| review queue's own enforcement branch | 1 | `test_review_queue_verifies_the_attestation_independently_of_the_transport` |
| `declared_key_id != signed.key_id` in `verify_hitl_action` | 1 | `test_verifier_refuses_an_attestation_whose_key_id_is_not_the_signing_kid` |

Restored: **880 passed**. `tools.lints --all` rc 0; `tests/cli/test_schema_export.py` and the
OpenAPI drift control green; mypy clean on 242 files; no `xfail`, `skip`, `sleep` or wall-clock
read in the four test files; no assertion weakened or removed; no roster turned into a count.

### Focused independent review of the delta

| seat | subject | evidence | disposition | findings |
| --- | --- | --- | --- | --- |
| **codex** (codex-cli 0.137.0) | the whole delta diff inlined on stdin, with the gate control and `verify_hitl_action` for reference; token `MERLIN-363` carried | INSPECTED | **PROCEED** | 0 — R1–R6 each cleared |
| **independent reviewer-executor** (Claude Opus 5 subagent, no session context) | its own detached worktree at `b446e24f` | INSPECTED + **INDEPENDENTLY EXECUTED** (baseline, the four severings with its own driver, the docstring probe) | **PROCEED** | 2 ADVISORY, both confirmed by a refuter |
| **refuters** (2 × Claude Opus 5 subagents) | their own detached worktrees at `b446e24f` | INSPECTED + INDEPENDENTLY EXECUTED | per finding, below | — |

**What the Opus seat established (RUN, in its worktree, HEAD verified equal to `b446e24f`,
status empty before and after):**

- **No behavior change in production — proved, not inspected.** Parsing both versions of
  `src/ccf/hitl/transport.py` and normalizing every docstring to a constant gives IDENTICAL
  ASTs; the four test files carry zero deletion lines; `tools/dump_schemas.py` leaves the
  worktree clean and the committed schema `description` compares EQUAL to the shipped
  docstring (1,470 characters). `tools.lints --all` rc 0; `tests/cli/test_schema_export.py`
  49 passed.
- **Baseline** on `tests/hitl tests/http_api tests/mcp tests/workflow/test_engine.py`:
  **880 passed** (880 `PASSED` lines under `-rA`; imports resolved inside its worktree).
- **The four severings, its own driver, one occurrence asserted each, bytes restored, sha256
  equal (`00d0cc88…`, `066340be…`, `f8eaa5c9…`, `331cda50…`):** the escalation branch →
  `1 failed, 879 passed`, exactly the escalation control; override → exactly the override
  control; review queue → exactly the review-queue control; the `declared_key_id !=
  signed.key_id` comparison → exactly the kid-vs-`key_id` negative. Deviation recorded: the
  brief wrote the fourth target at four spaces of indentation and the tree carries it at
  eight (inside a `try:`); the seat severed the real line. (The author's own driver matched
  the same line by substring and reddened the same test.)
- **The docstring probe:** the corrected not-required example parses; the corrected required
  example parses with a real P-256 public JWK and `keys_for` returns its kid; the OLD example
  `{semver: "1.0.0", signed_binding_required: true}` is refused with the validator's own
  message — so CR-363-04 was real at `ff120b46` and is gone at `b446e24f`.
- **Cleared:** the three transports are bound to nothing, so the refusals can only be the
  primitives' own (corroborated by the severings); `hitl_policy_ref is None` is the sharper
  expectation for an unbound transport; the kid-vs-`key_id` negative isolates the comparison
  (`match="declares kid"` is load-bearing, and the honest positive control pins the key map);
  a door-level sibling for CR-363-10 was NOT owed by the GO (a second key per door fixture is
  not cheap at either door) and is carried as test-only backlog beside CR-363-08; no
  weakened, deleted or count-ified assertion, no `xfail`/`skip`/`sleep`/wall-clock read; the
  corrected docstring is a template with placeholders, not a code constant (CINV-01).

**Its two findings, both ADVISORY, both confirmed by a refuter in its own worktree:**

- **P3-F-01 — the record at `b446e24f` still dispositions the three findings as carried /
  not fixed.** True at that pin by construction: the GO sequences the record update after
  the focused review, and this section IS that update, committed on the same branch
  immediately after. **Discharged by this commit.**
- **P3-F-02 — the three siblings' positive control is a DIFFERENT attestation.** The gate
  control they mirror mints ONE attestation over `reject`, refuses it when presented as
  `approve`, then re-presents THE SAME signed object honestly — which is what lets it say the
  refusal was the verdict and not the wiring. The three new siblings mint a second attestation
  (another action, another nonce) for their positive leg, so that leg shows an honest
  attestation is admitted but does not by itself isolate the verdict swap as the cause of the
  mismatch refusal. The severings prove each primitive's own enforcement is load-bearing; the
  isolation of the mismatch leg is the weaker half. **Carried as CR-363-15 (ADVISORY, test
  polish): re-present the same swapped attestation honestly** — `reject` to the escalation,
  `override` with a substitute to the boundary, `reject` to the queue — **rather than minting
  a second one.** Not changed here: the delta under review is the delta that was reviewed.


### Disposition of the three findings after the delta

- **CR-363-09 — REPAIRED on the branch at `b446e24f`**, test-only; the three primitives' own
  verification is now discriminated exactly as the gate's was.
- **CR-363-10 — REPAIRED on the branch at `b446e24f`**, test-only, at the verifier level
  (the GO asked for "a negative test"; a door-level sibling needs a second key per door
  fixture and is not owed by the GO — the Opus seat read the GO the same way and carries the door siblings as test-only backlog beside CR-363-08).
- **CR-363-04 — REPAIRED on the branch at `b446e24f`**, prose only, schema regenerated.

Nothing here merges, tags, releases, or closes `SEC-005`; the row stays OPEN and the merge
decision is Dave's.
