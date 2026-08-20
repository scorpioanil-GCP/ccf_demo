---
phase: 19-the-client-seam-integrity-checks-must-be-able-to-fail-insert
verified: 2026-08-20T11:37:46Z
status: human_needed
score: 63/63 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: null
  previous_score: null
  note: "No prior 19-VERIFICATION.md existed; this is the initial verification."
human_verification:
  - test: >-
      Rule whether Phase 19 may take its D-GATE with NO Success Criteria section in its
      ROADMAP entry. `gsd-sdk query roadmap.get-phase 19` returns `success_criteria: []`.
      The phase was therefore verified against plan `must_haves` only — 63 truths across
      eight plans — with no phase-level contract above them.
    expected: >-
      Either a ruling that plan must_haves are a sufficient contract for an INSERTED
      phase, or a Success Criteria section added to the Phase 19 ROADMAP entry before
      the gate is logged.
    why_human: >-
      The verifier must not invent phase-level criteria retroactively and then verify
      against them. This is a gap in the gating apparatus, and closing it is a decision
      about what a gate means, not a code change.
  - test: >-
      Rule on two stale citations THIS PHASE introduced into `.planning/STATE.md` and
      that no gate can see. `.planning/STATE.md:15` cites `client.py:139-141` for the
      false-clock sentence (line 139-141 is now the `product_id` property) and
      `.planning/STATE.md:30` cites `client.py:196-201` for the `check_outcome` thesis
      paragraph (196-201 is now the `as_of` Args block). Both were accurate when written
      at planning time; `19-02`/`19-07` moved the code. The citation lint DROPS both,
      because `client.py` is an ambiguous basename — `resolve_cited` returns
      `(None, True)` and `tools/lints/citations.py` records `ambiguous_path` as
      UNCHECKED rather than as a finding. This is exactly the defect class the phase's
      own ROADMAP note named at `.planning/ROADMAP.md:1652`.
    expected: >-
      Either the two citations are re-anchored onto symbols per `D-IMPL-114`
      (`src/ccf/client/client.py::ask` / `::_result_from`), or the drift is accepted
      and recorded.
    why_human: >-
      `.planning/STATE.md` is a tracked planning artifact and editing it is a ruling
      about the phase record, not a mechanical fix. It also raises the wider question
      (16 citation sites across 8 ambiguous basenames are dropped tree-wide) of whether
      the lint should report ambiguous drops by name rather than only by count — which
      is a tooling scope decision, and `C-13` kept this phase narrow.
  - test: >-
      Rule whether `gsd-sdk query verify.key-links` is fixed or worked around. The verb
      double-escapes YAML backslashes and reports `Invalid regex pattern:
      door_answer\\(` for every key-link pattern containing an escaped paren, marking
      the link `verified: false` without ever running it. Six of this phase's twelve
      declared key links are unevaluated by the SDK for this reason.
    expected: >-
      A ruling on whether the GSD verb is repaired, or whether plan authors stop
      escaping parens in `key_links.pattern`.
    why_human: >-
      This is an SDK-external tool defect, outside the CCF repo, and a check that can
      never PASS is the inverse of the defect this phase exists to close. All six links
      were verified manually by grep and all six hold — the finding is about the
      apparatus, not about the phase.
gaps: []
deferred:
  - truth: >-
      `as_of=None` questions: a transport that alters only the door's `asked_at` is
      UNDETECTED (`C-18`'s declared residual).
    addressed_in: "A later phase, per `D-IMPL-159`"
    evidence: >-
      `D-IMPL-159` records the client-side clock read as an OPEN deferred defect, not
      accepted risk, and names the fix (move `as_of=None` resolution producer-side into
      `runtime/`). Verified NOT closed: this phase asserts the residual as a passing
      measurement rather than papering it over — see
      `tests/client/conformance/test_a_crossed_question_is_caught_on_one_transport.py::test_an_absent_boundary_leaves_the_moved_instant_undetectable`.
  - truth: "`A5` — stdio auth is impersonation rather than verification."
    addressed_in: "Not this phase; carried forward unclosed from Phase 18"
    evidence: >-
      `18-CLOSE-REVIEWS.md`'s appended close note states `A5 IS STILL OPEN and was not
      touched by Phase 19`, and `19-CONTEXT.md` puts it explicitly out of scope.
---

# Phase 19: The Client-Seam Integrity Checks Must Be Able to Fail — Verification Report

**Phase Goal:** make the two client-seam integrity checks *capable of failing* when a
transport answers the wrong question or alters a vessel in transit. They could not, on
either shipped adapter.

**Verified:** 2026-08-20T11:37:46Z at `920c171` on `main`
**Status:** human_needed (63/63 truths verified; 3 items escalated to Dave)
**Re-verification:** No — initial verification
**Working tree:** clean at start and clean at finish; `git status --porcelain` empty
both times. No foreign uncommitted state was found.

---

## 0. How this phase was verified, and why it is not the usual way

This phase exists because two checks were GREEN for the entire life of the client while
being structurally incapable of failing. **A passing suite is therefore not evidence
here.** The full suite is green (`3981 passed, 118 skipped`, exit 0) and that fact
carries almost no weight in this report.

What carries weight is that **ten distinct properties were deliberately broken in an
out-of-tree copy of the repository and the corresponding controls were watched turning
red.** The tracked tree was never edited. Sabotage ran against
`rsync`-copied source under `PYTHONPATH=.:src:runtime` from the scratch directory, with
the project venv interpreter. Each mutation was anchor-checked (refuse if the anchor
does not occur exactly once), applied, tested, and reverted.

| # | Property broken | Where | Controls that went RED | Verdict |
|---|-----------------|-------|------------------------|---------|
| S1 | `check_outcome`'s echo comparison disabled (`if False and outcome.request != sent`) | `src/ccf/client/codec.py` | 9 — both single-transport crossed-question legs, both conformance `test_a_crossed_echo_is_caught`, 5 codec controls | OBSERVED FAILING |
| S2 | `verify_content_address`'s digest comparison disabled | `src/ccf/client/codec.py` | 7 — both single-transport altered-vessel legs, both conformance `test_an_altered_vessel_is_caught`, 3 codec controls | OBSERVED FAILING |
| S3 | `C-02` violated — the echo made to carry the *resolved* instant instead of `None` as asked | `src/ccf/products/door.py::door_answer` | 7 — `assert_decision_instant_is_auditable` on both subjects, its own suite-fires control, the `C-18` residual measurement, 3 door controls | OBSERVED FAILING |
| S4 | `C-18` temporal cross-check removed at the MCP door | `runtime/ccf_runtime/mcp/egress.py` | 2 — `test_a_door_answering_at_another_instant_is_caught_when_the_boundary_is_concrete`, `test_a_concrete_boundary_disagreeing_with_asked_at_is_refused_by_name` | OBSERVED FAILING |
| S5a | `product_class` cross-check removed at the MCP door | `runtime/ccf_runtime/mcp/egress.py` | 1 — `test_an_encoded_question_naming_another_class_is_refused_by_name` | OBSERVED FAILING |
| S5b | `parameters` cross-check removed at the MCP door | `runtime/ccf_runtime/mcp/egress.py` | 1 — `test_an_encoded_question_declaring_other_parameters_is_refused_by_name` | OBSERVED FAILING |
| S6a | An adapter constructs `WireOutcome(...)` via an import-resolved local name | `src/ccf/client/adapters/inprocess.py` | 2 — `test_no_adapter_constructs_the_outcome`, `test_the_outcome_scan_reads_every_adapter_module` | OBSERVED FAILING |
| S6b | An adapter constructs `ccf.products.door.DoorOutcome(...)` in attribute-call form | `src/ccf/client/adapters/mcp_stdio.py` | same 2 | OBSERVED FAILING |
| S7 | HTTP door stops publishing the request echo (`asked=` dropped) | `runtime/ccf_runtime/http_api/routes/product.py` | 4 — 3 echo-header legs plus the absence-assertion control | OBSERVED FAILING |
| S8 | Echo header published EMPTY rather than ABSENT when no question was posed | `runtime/ccf_runtime/http_api/routes/__init__.py` | 1 — `test_a_caller_who_posed_no_question_gets_no_echo_header` | OBSERVED FAILING |
| S9 | `_parameters_survive_the_wire` neutered | `src/ccf/products/door.py` | 5 — the four parameterized refusal legs plus the nested-value leg | OBSERVED FAILING |
| S10 | Echo comparison moved AFTER the refusal branch (`C-04` ordering) | `src/ccf/client/codec.py` | 2 — the refused-half echo leg and the ordering guard, the latter refusing to pass on a scan that located nothing | OBSERVED FAILING |

Four further properties were probed **directly, in-process**, rather than by mutation:

| Probe | Method | Result |
|-------|--------|--------|
| The `C-17` gate refuses a walk that read nothing | `assert_no_adapter_constructs_the_outcome([empty_tmpdir])` | RAISES — *"the scan read no modules … so it proved nothing"* |
| The `C-17` gate refuses an unresolvable root | `count_outcome_construction_sites([/nope])` | RAISES — *"is not a directory, so scanning it would silently contribute nothing"* |
| The `C-17` gate refuses an unparsable file | a syntactically invalid `.py` under a `tmp_path` root | RAISES — *"could not be parsed … a file that is skipped is a file that is not checked"* |
| The conformance legs' witness-type limb **can actually fail** (`19-04` must-have) | a synthetic `AdapterSubject` whose `connect` returns a different type on the `-witness` root, handed to `suite.assert_a_crossed_echo_is_caught` | RAISES — *"`inprocess` built a `InProcessAdapter` and then a `_Clone` from the same factory over two roots"* |

**Controls I could not make fail: none.** Every control this phase added or claimed was
either watched red under sabotage or exercised directly to a raise.

**What I only read and did not break:** the prose amendments (`19-07`), the decision-log
entries (`19-08`), and the surface-change fragments. Those are documents; a sabotage of
a document proves nothing a reading does not. Each was read in full against the tree and
each claim it makes about the code was checked against the code.

---

## 1. The residual that must stay open — verified OPEN, not closed

`C-18` declares that when `as_of=None` the client resolves the clock (`C-15`), so the
instant crosses the wire once and a transport altering `asked_at` alone is **undetected**.
I searched for any shipped prose claiming detection past that line. **There is none.**

- `src/ccf/client/codec.py` module docstring enumerates **four** undetected cases and
  case 4 is verbatim the `as_of=None` residual, with the other half of the axis held
  ("a **concrete** `as_of` crosses twice … refuses a disagreement by name").
- `src/ccf/client/client.py::ask` names the deferred defect and says *"no fix is promised
  in this phase."*
- `docs/DECISIONS.md` `D-IMPL-159` — *"RESOLVED as a deferral; the underlying defect is
  **OPEN**, not accepted."*
- `18-CLOSE-REVIEWS.md`'s appended close note repeats the same four cases and says the
  residual *"is recorded as **open** in `D-IMPL-159`."*
- `19-01-PLAN.md`'s `T-19-01` row states the unmitigated path explicitly.
- Tree-wide sweep of `public/`, `README.md`, `docs/*.md`, `docs/surface/` for
  "altered in transit" / "different question" / "tamper": **no overclaim found.**

The residual is asserted as a **passing measurement** rather than a caveat —
`test_an_absent_boundary_leaves_the_moved_instant_undetectable` asserts that the same
hostile adapter, asked with `as_of=None`, is served, that the echo carries `None`, and
that `graph_snapshot_at` equals the instant the transport substituted. Under sabotage S3
that test goes red, so it is not a test that passes by accident.

---

## 2. Goal Achievement — Observable Truths

63 truths across eight plans. ROADMAP Success Criteria: **none exist** (see §6).

### 19-01 — one outcome shape, the echo, the producer-claimed address

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1.1 | Exactly ONE outcome shape; `WireOutcome` is an alias of `DoorOutcome` (`C-06`) | VERIFIED | `src/ccf/client/wire.py:113` `WireOutcome = DoorOutcome`; `door.py` defines it; no transcoding step remains |
| 1.2 | The outcome carries the question the door parsed, at outcome level, on answer AND refusal (`C-01`,`C-03`,`C-04`) | VERIFIED | `DoorOutcome.request: WireRequest`; `door_answer` sets `request=echo` on both branches; S10 proves the comparison covers the refusal half |
| 1.3 | Content address computed by the PRODUCER from the same `canonical_bytes` call | VERIFIED | `door_answer` lines: `vessel = canonical_bytes(answer.product)` then `content_address=hashlib.sha256(vessel).hexdigest()` and `product_json=vessel.decode(...)` — one serialization. S2 proves the consumer's recomputation is live |
| 1.4 | Echo is as-asked on the temporal axis; the door's resolved instant never leaks in (`C-02`,`C-15`) | VERIFIED | S3: forcing the resolved instant into the echo turns 7 controls red |
| 1.5 | `PRODUCT_REQUEST_TOOL` takes the encoded `WireRequest` as a REQUIRED argument, no deprecation window (`C-16`) | VERIFIED | `egress.py:538` `request: str,` — positional, before the defaulted `parameters`; no optional/fallback path exists |
| 1.6 | The MCP door REFUSES a call whose encoded request disagrees on `product_class`, on `parameters`, AND on the temporal axis when `temporal_boundary is not None` | VERIFIED | Three named raises at `egress.py:834/843/852`; S4, S5a, S5b each turn the corresponding control red |
| 1.7 | The impossible axis is NAMED rather than papered over; `19-07`/`19-08` carry it into the claim and the log | VERIFIED | §1 above |
| 1.8 | `assert_decision_instant_is_auditable` stays green over `mcp+stdio` (`P5`) | VERIFIED | Green in the full run; S3 proves it live rather than vacuous |

### 19-02 — the seam carries bytes

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 2.1 | `TransportAdapter.ask(request: WireRequest) -> bytes` — the object return is gone by type change | VERIFIED | `wire.py:145` signature; both adapters return `bytes`; `mypy --strict` clean over 211 files |
| 2.2 | `ProductClient.ask` calls `decode_outcome` on adapter bytes — `CLNT-08` stops being a claim about an unshipped function | VERIFIED | `client.py:228-230` `decode_outcome(self._adapter.ask(request), sent=request)`; S1/S2 prove both checks now reachable through a real client |
| 2.3 | `decode_outcome` carries the parsed vessel out — no second contract validation, no second decode path (`D-12`) | VERIFIED | `codec.py:387` `class DecodedOutcome`, `:468` `return DecodedOutcome(outcome=outcome, vessel=vessel)`; `_result_from` reads `decoded.vessel` and parses nothing |
| 2.4 | `McpStdioAdapter._decode` is DELETED | VERIFIED | `grep -n "_decode" src/ccf/client/adapters/mcp_stdio.py` → no definition; `ask` returns `asyncio.run(...).encode("utf-8")` |
| 2.5 | In-process is a degenerate wire in BOTH directions (`C-07`) | VERIFIED | `inprocess.ask` passes `canonical_bytes(request).decode("utf-8")` **text** to `_door`, which calls `door_question(asked_json)`. S1 turns the in-process crossed-question leg red, which is only possible if the door echoed what it parsed off the encoded question |
| 2.6 | Two extra in-process serializations accepted, no benchmark owed (`C-14`) | VERIFIED | Reasoning recorded at `inprocess._door` docstring and ratified in `D-IMPL-160` |
| 2.7 | No compatibility shim — no `ask` accepting either bytes or an object | VERIFIED | Single signature, no overload, no `isinstance` branch anywhere on the seam |
| 2.8 | The clock read does NOT move; the encoded `WireRequest` carries `temporal_boundary=None` (`C-15`,`C-13`) | VERIFIED | `inprocess.py:402` and `mcp_stdio.py:251` both still `request.temporal_boundary or datetime.now(UTC)`, with `asked_at` a separate argument |
| 2.9 | `Result` constructed in exactly one place; `check_outcome` still runs before the refusal branch | VERIFIED | One `Result(` construction in `_result_from`; `CLNT-06` scan green; S10 proves the ordering guard live |

### 19-03 — single-transport falsification

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 3.1 | A crossed question is caught by ONE client, ONE adapter, ONE deployment — no second subject in the assertion | VERIFIED | `test_a_crossed_question_is_caught_over_the_in_process_transport` and `..._over_the_mcp_transport` each construct one `ProductClient` over one hostile subclass; `_NOTHING` sentinel proves no `Result` was produced |
| 3.2 | True on BOTH shipped transports, as two independent single-transport proofs | VERIFIED | Two separate test functions, never one two-subject proof |
| 3.3 | An altered vessel is caught by one client on one adapter, and separately by `decode_outcome` with no transport | VERIFIED | `test_an_altered_vessel_is_caught_over_the_{in_process,mcp}_transport` plus `tests/client/test_codec.py` byte-sabotage legs; S2 turns all of them red |
| 3.4 | Tampered bytes stay WELL-FORMED and CONTRACT-VALID (discrimination guard) | VERIFIED | `_alter_the_vessel` inserts one space inside the vessel's opening brace and re-encodes through the shipped encoder; the tests assert JSON-validity and contract-validity separately |
| 3.5 | Every sabotage carries a vacuity guard — the honest subject does not raise | VERIFIED | `test_control_the_assertion_fails_when_it_is_handed_an_honest_adapter`, `test_the_unmutated_adapter_serves_the_same_concrete_question`, `test_control_the_vessel_assertion_fails_...` |
| 3.6 | The echo comparison runs BEFORE the refusal branch, ASSERTED rather than assumed | VERIFIED | `test_the_shipped_decoder_compares_the_echo_before_it_returns_a_refusal`; S10 turns it red AND its message shows it refuses to pass on a scan that located nothing |
| 3.7 | `_parameters_survive_the_wire` is demonstrably what prevents a FALSE failure (`P4`) | VERIFIED | `test_the_parameter_guard_is_what_prevents_a_false_wire_failure` bypasses the validator with `model_construct` and observes a `TransportError` on a healthy wire, with an admitted-spelling vacuity twin. S9 separately proves the validator itself live (5 legs red) |
| 3.8 | `C-18` exercised by a control that alters `asked_at` ALONE, and the residual asserted as a measurement | VERIFIED | `_McpMovesTheDoorsInstant` overrides `_call`, not `ask` — the encoded request is byte-identical. S4 turns the concrete leg red; §1 covers the residual |

### 19-04 — the `C-12` conformance obligation

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 4.1 | Every registered subject is wrapped in a byte-corrupting decorator and must raise | VERIFIED | `suite.assert_a_crossed_echo_is_caught` / `assert_an_altered_vessel_is_caught` wrap `subject.connect(...)` in `_Tampering`; S1/S2 turn both legs red on both subjects |
| 4.2 | The decorator is GENERIC and transport-blind; an adapter author writes nothing and cannot opt out | VERIFIED | `_Tampering.ask` is `return self._edit(self._inner.ask(request))` — it knows only that bytes crossed. The decorator lives in `suite.py`, applied by the suite, not by any binding module |
| 4.3 | Each leg asserts PER SUBJECT; a suite with one subject is still non-vacuous | VERIFIED | Both legs are `for subject in subjects:` loops with no cross-subject comparison |
| 4.4 | Each leg carries its vacuity guard — the untampered subject does not raise | VERIFIED | Third limb of each leg, with its own named `AssertionError` |
| 4.5 | Each leg asserts the EXACT `D-10` type — `type(caught) is TransportError` | VERIFIED | `caught_the_wire_failure_itself = type(caught) is TransportError`, spelled as a named boolean in both legs |
| 4.6 | The stand-in for the same-type check is something that can actually FAIL, and where no stand-in exists the limit is stated | VERIFIED | Probed directly: a synthetic subject whose `connect` returns a different type on the `-witness` root makes the leg raise by name. The docstring states the check is *weaker* than `assert_wire_failure_parity`'s and why, rather than glossing it |
| 4.7 | Each new leg has a control in `test_the_suite_fires.py` handing it an HONEST subject | VERIFIED | `test_the_suite_fires.py:896` and `:922`, via `_reversing_subject` which re-applies the shipped involutive edit |
| 4.8 | `suite.py` still names no transport, no product id and no parameter | VERIFIED | Neutrality test green; `_cross_the_echo` derives the crossed class name by suffixing the echo already on the wire — no vocabulary enters |
| 4.9 | `assert_decision_instant_is_auditable` stays green over both subjects (`P5`) | VERIFIED | Green; S3 proves it live |
| 4.10 | Adding legs is not in tension with `D-GATE-18`'s zero-diff claim | VERIFIED | Reasoning recorded in `C-12` and in the `19-02` fragment; the zero-diff claim was about binding a new *adapter*, and binding a new adapter still touches no suite file |
| — | Collected count 8 → 10 per module | VERIFIED | `--collect-only` reports 20 across the two conformance modules |

### 19-05 — the `C-17` AST gate

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 5.1 | No module under `src/ccf/client/adapters/` constructs the outcome by EITHER counted shape, proven by a RED check | VERIFIED | S6a (import-resolved name) and S6b (`….DoorOutcome(...)` attribute call) each turn `test_no_adapter_constructs_the_outcome` red |
| 5.2 | The gate NAMES WHAT IT CANNOT REACH in its own docstring: `getattr` dispatch and decode/`model_copy`/re-encode RE-LABELLING | VERIFIED | Both named in `count_outcome_construction_sites`'s *"Not detectable, and named rather than pretended away"* block, with the honest admission that this phase's own `19-03`/`19-04` controls use the second idiom |
| 5.3 | The gate mirrors `CLNT-06`'s pattern: roots as a parameter, a count for EVERY module including zeros, refuses an unresolvable root or unparsable file | VERIFIED | Probed directly — all three refusals fire; a real scan reports `{4 modules: 0,0,0,0}` |
| 5.4 | The gate carries its own named sabotage control, in the same plan | VERIFIED | `tmp_path`-tree controls at `test_surface.py:884` and following, plus two extra weakened-walk controls the SUMMARY records as beyond plan |
| 5.5 | ONE assertion over ONE directory, not the general obligations gate `C-13` rejected | VERIFIED | `ADAPTER_ROOTS` is `src/ccf/client/adapters/` alone; no framework |
| 5.6 | The shipped assertion refuses a walk that read nothing at all | VERIFIED | Probed directly — `assert_no_adapter_constructs_the_outcome([empty])` raises before any ceiling is applied |

### 19-06 — the HTTP door

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 6.1 | The HTTP door is RECONCILED, not converted: body stays the vessel, echo joins the `X-CCF-*` siblings | VERIFIED | `REQUEST_ECHO_HEADER = "X-CCF-Request-Echo"` beside `CONTENT_ADDRESS_HEADER` and `REPLAY_REF_HEADER`; body is `canonical_bytes(payload)` unchanged |
| 6.2 | `D-IMPL-126` and `canonical_response`'s ruling stand VERBATIM; the four `ETag` reasons not restated, not amended | VERIFIED | `19-07`'s SUMMARY records `git diff` for `routes/__init__.py` as EMPTY at that plan; `test_the_etag_alternative_is_ruled_against_in_writing` green |
| 6.3 | The header is ABSENT, never empty, when the caller posed no question | VERIFIED | `if asked is not None:` guard; S8 (empty rather than absent) turns `test_a_caller_who_posed_no_question_gets_no_echo_header` red |
| 6.4 | `canonical_response` still serializes the payload exactly ONCE; the echo is an independent serialization of a different object | VERIFIED | `body = canonical_bytes(payload)` once; the echo is `canonical_bytes(asked)` of a different object |
| 6.5 | Coverage stated honestly: NO HTTP client adapter, so PRODUCER-SIDE only, nothing claims client-side coverage | VERIFIED | `_echo`'s docstring states the echo is built from the one `asked` the route parsed, and that `C-18`'s cross-check *"has no subject here — a cross-check would compare a value with itself. Its absence is a measurement, not an exemption."* |
| 6.6 | Every new assertion carries a named sabotage control | VERIFIED | Presence: `test_the_echo_comparison_fails_against_a_different_question`. Absence: `test_the_absence_assertion_fails_when_a_question_was_posed`. S7/S8 turn both families red |

### 19-07 — making the prose true

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 7.1 | `D-GATE-18`'s standing prose constraint is REPLACED BY A NARROWER TRUE SENTENCE, not lifted (`C-10`) | VERIFIED | `codec.py` module docstring: five named detected conditions, then *"`D-GATE-18`'s standing prose constraint is replaced by the paragraphs above, not lifted"* |
| 7.2 | The claim states what it does NOT detect; signing out of scope; NO signature member reserved on the wire | VERIFIED | Four undetected cases enumerated; `DoorOutcome` has exactly five members and none is a signature |
| 7.3 | `C-18`'s temporal residual is in the NAMED UNDETECTED LIST, with the concrete-`as_of` half held | VERIFIED | Undetected case 4, verbatim, with the concrete half stated in the same paragraph. See §1 |
| 7.4 | Every corrected paragraph is AMENDED, never deleted | VERIFIED | Read in full: `codec.py` keeps the pre-Phase-19 B0 measurement above the correction; `verify_content_address` and `check_outcome` both keep their inert-state paragraphs and append *"Corrected in Phase 19, and the paragraph above is kept as the record of what was measured"* |
| 7.5 | `ProductClient.ask`'s false sentence amended to a TRUE one; the clock did not move; the defect recorded for a later phase | VERIFIED | The false clause is quoted verbatim inside the correction and labelled false; `D-IMPL-159` records the deferral as OPEN |
| 7.6 | The surface manifest is regenerated and a correctly-named `19-NN-*.md` fragment names EVERY moved module | VERIFIED (artifact path substituted — see §4) | `make surface` and `make surface-changes` both regenerate BYTE-IDENTICAL output (`git status --porcelain` empty after each). Three correctly-named fragments exist: `19-01-…`, `19-02-…`, `19-06-…` |
| 7.7 | `consume.py` stays inside its declared line budget and the AST purity gate stays green | VERIFIED | 79 lines; `tests/examples/test_client_example_budget.py` and `test_client_example_purity.py` green in the full run |

### 19-08 — ratification

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 8.1 | `C-01`..`C-18` ratified as `D-IMPL` entries, `C-18` included | VERIFIED | `D-IMPL-156` — *"Phase 19's decision set (`C-01` … `C-18`) is RATIFIED"* |
| 8.2 | The `C-05`/`C-08` seam change recorded as an AMENDMENT to the spec's `D-11` | VERIFIED | `D-IMPL-157`; `docs/superpowers/specs/2026-08-15-ccf-client-design.md:450` **Amendment 2** |
| 8.3 | ONE `D-IMPL` rules BOTH wire-compat breaks, no deprecation window | VERIFIED | `D-IMPL-158` — *"BOTH of Phase 19's wire-compatibility breaks, ruled in one entry with NO deprecation window; and the door's three-axis cross-check"* |
| 8.4 | `C-15`'s deferred clock defect is its OWN entry for a later phase, explicitly not fixed here | VERIFIED | `D-IMPL-159`, marked OPEN |
| 8.5 | `C-18` ruled in the SAME entry that defers the clock, in BOTH directions | VERIFIED | `D-IMPL-159`'s *"THE COST OF THE DEFERRAL, STATED SO IT CAN BE PRICED (`C-18`)"* block gives both halves in the same breath |
| 8.6 | `C-14`'s accepted serialization cost recorded WITH reasoning, no benchmark owed | VERIFIED | `D-IMPL-160` |
| 8.7 | `REQUIREMENTS.md` `CLNT-05` AMENDED — old text kept, new `-> bytes` stated, amending decision named | VERIFIED | `.planning/REQUIREMENTS.md:201` keeps the `-> WireOutcome` sentence and appends *"AMENDED 2026-08-20 by `D-IMPL-157`"* with `-> bytes` |
| 8.8 | The client design spec gains **Amendment 2** in Amendment 1's style, appended, not an edit of §5 | VERIFIED | `:450` `# Amendment 2 — 2026-08-19 (the client-seam integrity repair)` at end of file |
| 8.9 | `18-CLOSE-REVIEWS.md`'s `B0` marked closed BY APPENDING; `A5` explicitly left open | VERIFIED | The `⚠ STATUS: DEFERRED` line is untouched; the close note is appended below it; *"`A5` IS STILL OPEN and was not touched by Phase 19"* plus *"The other nine carried advisories … remain open. A closed `B0` at the top of this file is not a closed file."* |

**Score: 63/63 truths verified.**

---

## 3. The phase's own success sentence, discharged

> *"A control that answers a different question must be caught by a **single-transport**
> client, not only by the cross-adapter parity diff."*

Discharged, and independently falsified. `test_a_crossed_question_is_caught_over_the_in_process_transport`
and `..._over_the_mcp_transport` each construct exactly one `ProductClient` over one
hostile subclass of one shipped adapter against one provisioned deployment. Neither
assertion mentions a second subject. Under S1 both go red; under S2 the two altered-vessel
twins go red. Parity is nowhere in the proof.

---

## 4. Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/ccf/products/door.py` | `WireRequest`, merged `DoorOutcome`, `door_question`, `door_answer` | VERIFIED | 665 lines; all four present; `__ccf_mode__ = "algorithmic"` intact, no clock read |
| `src/ccf/client/wire.py` | re-exports + `WireOutcome = DoorOutcome`; `__all__` unchanged | VERIFIED | `__all__ = ["TransportAdapter", "WireOutcome", "WireRequest"]` |
| `runtime/ccf_runtime/mcp/egress.py` | required `request` arg, three-axis cross-check, single `door_answer` emission | VERIFIED | One `door_answer(` return; three named raises; no residual `DoorOutcome(` construction |
| `tests/products/test_door_answer.py` | unit proofs with named sabotage controls | VERIFIED | Present; three of its legs go red under S3 |
| `src/ccf/client/codec.py` | `DecodedOutcome`, narrower true claim | VERIFIED | Both present |
| `src/ccf/client/client.py` | `ask` routing through `decode_outcome` | VERIFIED | line 228-230 |
| `src/ccf/client/adapters/inprocess.py` | `_door` taking text; `_encode` deleted | VERIFIED | `_door(asked_json: str, ...)`; no `_encode` |
| `src/ccf/client/adapters/mcp_stdio.py` | `.encode("utf-8")` return; `_decode` deleted | VERIFIED | Both |
| `tests/client/conformance/test_a_crossed_question_is_caught_on_one_transport.py` | the phase's own controls | VERIFIED | 8 tests, incl. the `C-18` residual measurement |
| `tests/client/test_codec.py` | byte sabotage, refused-half echo, ordering, `P4` | VERIFIED | All four families present and each observed red under the matching sabotage |
| `tests/client/conformance/suite.py` | `_Tampering`, two legs, both in `__all__` | VERIFIED | `test_every_exported_leg_has_a_control_here` holds `__all__` to `LEG_CALLS` |
| `tests/client/conformance/test_{inprocess,mcp}_conformance.py` | two new call lines each; 8→10 | VERIFIED | 20 collected |
| `tests/client/conformance/test_the_suite_fires.py` | a control per new leg | VERIFIED | Lines 896, 922; both new legs in `LEG_CALLS` |
| `tests/client/test_surface.py` | `count_outcome_construction_sites` + assertion + control | VERIFIED | All three; the gate observed failing twice and refusing three vacuous inputs |
| `runtime/ccf_runtime/http_api/routes/__init__.py` | `REQUEST_ECHO_HEADER`, `asked` kwarg | VERIFIED | `:98`, `:166` |
| `runtime/ccf_runtime/http_api/routes/product.py` | route passes the echo; passes nothing on `None` | VERIFIED | `:213` `echo = _echo(asked) if asked is not None else None`; `:229` |
| `docs/surface-changes/19-01-one-wire-shape-and-a-bytes-seam.md` | seven-field fragment | **SUBSTITUTED** | This exact filename does **not** exist. Three correctly-named fragments do: `19-01-one-outcome-shape-and-the-encoded-question.md`, `19-02-the-adapter-seam-carries-bytes.md`, `19-06-the-http-door-publishes-the-question.md`. `19-07-SUMMARY.md` §5 records the substitution explicitly (*"the fragment was not created and the substitution is recorded"*). The underlying truth (7.6) is satisfied: both `make surface` and `make surface-changes` regenerate byte-identical output, so no surface drift is unrecorded. **Not a gap** — the plan's artifact path was a prediction, not a contract |
| `docs/surface/v0.2-surface.json` | regenerated by `make surface`, never hand-edited | VERIFIED | Regenerating produces an empty diff |
| `docs/DECISIONS.md` | five/six appended `D-IMPL` entries | VERIFIED | `D-IMPL-156`…`161` — six, one more than the plan predicted (`D-IMPL-161` records the on-`main` divergence) |
| `.planning/REQUIREMENTS.md` | `CLNT-05` amended | VERIFIED | line 201 |
| `docs/superpowers/specs/2026-08-15-ccf-client-design.md` | Amendment 2 | VERIFIED | line 450 |

---

## 5. Key Link Verification

`gsd-sdk query verify.key-links` could not evaluate 6 of the 12 declared links (see §6,
apparatus finding 2). **All twelve were verified manually.**

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `runtime/…/mcp/egress.py` | `ccf.products.door.door_answer` | the tool's single return | WIRED (manual) | `egress.py:907` `return door_answer(` — SDK reported `Invalid regex pattern` |
| `src/ccf/client/adapters/mcp_stdio.py` | `PRODUCT_REQUEST_TOOL` arguments | encoded `WireRequest` as a tool arg | WIRED (manual) | `:240` `"request": canonical_bytes(request).decode("utf-8")` |
| `src/ccf/client/wire.py` | `ccf.products.door` | re-export of the one shape | WIRED (manual) | `:91` |
| `src/ccf/client/client.py` | `codec.decode_outcome` | the one call in `ask` | WIRED (manual) | `:229` |
| `src/ccf/client/adapters/inprocess.py` | `door.door_question` | the producer half parsing the question | WIRED (manual) | `:456` |
| `tests/…/test_a_crossed_question…py` | `ProductClient.ask` | real client + hostile subclass | WIRED (manual) | 3 × `pytest.raises(TransportError` |
| `tests/client/test_codec.py` | `codec.decode_outcome` | tampered bytes to the shipped decoder | WIRED (manual) | 13 call sites |
| `tests/…/conformance/suite.py` | `codec.encode_outcome` | decorator re-encodes through the shipped encoder | WIRED | SDK-verified |
| `tests/…/test_mcp_conformance.py` | `suite.py` | two new legs over the existing SUBJECTS tuple | WIRED | SDK-verified |
| `tests/client/test_surface.py` | `src/ccf/client/adapters/` | AST walk | WIRED | SDK-verified |
| `runtime/…/routes/product.py` | `canonical_response` | producer-side echo | WIRED (manual) | `:229` `canonical_response(answer.product, replay_ref=replay_ref, asked=echo)` |
| `.planning/REQUIREMENTS.md` → `docs/DECISIONS.md` and spec → `docs/DECISIONS.md` | | | WIRED | SDK-verified |

---

## 6. Requirements Coverage

`.planning/REQUIREMENTS.md` maps **no** requirement ID to Phase 19. The ROADMAP entry
says *"**Requirements:** carries Phase 18's `B0`."* There are therefore **no orphaned
requirements** for this phase. The IDs below are the ones the eight plans self-declared.

| Requirement | Source Plans | Status | Evidence |
|-------------|--------------|--------|----------|
| `CLNT-05` (one transport seam) | 19-01, 19-02, 19-07, 19-08 | SATISFIED (amended) | Seam retyped to `-> bytes`; the requirement text amended in place naming `D-IMPL-157` |
| `CLNT-06` (`Result` in exactly one decoder) | 19-02, 19-05 | SATISFIED | One construction site; the existing `count_result_construction_sites` gate green; the new `C-17` gate mirrors it without sharing code |
| `CLNT-08` (`decode(encode(x)) == x`; in-process a true degenerate wire) | 19-01, 19-02, 19-07 | SATISFIED | `decode_outcome` now has a shipped call site; in-process is degenerate in both directions (S1 proves it) |
| `CLNT-11` (one parameterized conformance suite) | 19-02, 19-03, 19-04 | SATISFIED | Two new legs bound over the existing SUBJECTS tuple, per-subject, 20 collected |
| `CLNT-12` (every gate carries a named sabotage control) | 19-01…19-06, 19-08 | SATISFIED | Every new gate in this phase was watched failing (§0). This is the requirement pointed at itself and it held |
| `CLNT-14` (AST purity + budget gates) | 19-07 | SATISFIED | `consume.py` 79 lines; both gates green |
| `CLNT-15` (MCP door carries parameters, emits canonical refusal, ships on the suite) | 19-01, 19-02, 19-03, 19-04 | SATISFIED | MCP subject passes all 10 conformance legs incl. both tamper legs over a real child process |

---

## 7. Gates and Behavioural Spot-Checks

| Check | Command | Result | Status |
|-------|---------|--------|--------|
| Full suite | `pytest tests -q` | `3981 passed, 118 skipped in 649s`, exit 0 | PASS |
| Type check | `python -m mypy` (`files = ["src","runtime"]`) | `Success: no issues found in 211 source files` | PASS |
| CCF invariant lints | `python -m tools.lints --all` | exit 0, no findings | PASS |
| Tools gates | `make gate-tools` | 400 + 154 passed | PASS |
| Surface manifest drift | `python tools/dump_surface.py` then `git status` | empty diff | PASS |
| Surface-changes drift | `make surface-changes` then `git status` | empty diff | PASS |
| Citation lint coverage | `python -m tools.lints --citations --report` | 993 matched, 573 checked, **0 findings**, 378 UNCHECKED | PASS with caveat — see §8 |
| Conformance leg count | `pytest …conformance --collect-only` | 20 (10 per subject) | PASS |

No probes of the `scripts/*/tests/probe-*.sh` shape exist in this repository and no plan
declares one; probe execution is N/A for this phase.

---

## 8. Findings

### WARNING F-1 — the phase has no ROADMAP Success Criteria (apparatus gap)

`gsd-sdk query roadmap.get-phase 19` returns `success_criteria: []`. The Phase 19
ROADMAP section carries a **Goal**, a *"Why this phase exists"*, a *"The defect,
measured"*, a *"Scope, at least"* list and a standing constraint — but no Success
Criteria section. There is therefore no phase-level contract above the plans'
`must_haves`. This report deliberately did **not** invent criteria retroactively.

Secondary artefact of the same gap: the SDK's parsed `goal` is truncated at the first
line break — `"make the two client-seam integrity checks *capable of failing* when a
transport"` — losing the operative clause.

### WARNING F-2 — `gsd-sdk query verify.key-links` cannot evaluate escaped patterns

The verb reports `Invalid regex pattern: door_answer\\(` and marks the link
`verified: false`. The YAML `\\(` reaches the regex compiler as a literal double
backslash. Every key-link pattern in this phase containing an escaped paren — six of
twelve — is reported as unverified without ever being run. This is the inverse of the
defect the phase closes: **a check that can never pass**. All six were verified manually
and all six hold. No truth is affected; the finding is about the gating apparatus.

### WARNING F-3 — two stale citations this phase introduced, invisible to the citation lint

`.planning/STATE.md:15` cites `` `client.py:139-141` `` for *"the false … sentence"*;
`client.py:139-141` is now the `product_id` property.
`.planning/STATE.md:30` cites `` `client.py:196-201` `` for *"the paragraph … that states
the phase's own thesis"*; `client.py:196-201` is now the `as_of` `Args:` block.

Both were accurate when written at planning time. `19-02` and `19-07` moved the code.
The citation lint **drops both**, because `client.py` resolves to two candidates
(`src/ccf/client/client.py`, `src/ccf/mcp/client.py`) and `resolve_cited` returns
`(None, True)`, which `check_source` records as `ambiguous_path` — *"ambiguity is never a
finding."*

This is precisely the class the phase named at `.planning/ROADMAP.md:1652`:
*"`client.py` is an **ambiguous basename**, so the citation lint DROPPED the old pointer
rather than checking it, which is why a stale number survived three phases with every
gate green."* `19-08` fixed the ROADMAP instance and `19-02` re-anchored two *fully
qualified* STATE.md symbol citations (`8020d67`) — these two bare-basename **line**
citations were left, and the phase's own edits then made them stale.

**Adjacency sweep, as requested.** I enumerated every citation the lint drops as
ambiguous: **8 distinct basenames, 16 citation sites** — `agent.py`, `client.py`,
`config.py`, `deployment.py`, `product.py`, `replay.py`, `serve.py`, `test_dispatch.py`.
I resolved and checked each by hand:

- `agent.py:74`, `config.py:98`, `replay.py:47`, `replay.py:65`
  (cited in `routes/__init__.py:227-228`) — **all four still resolve correctly** to a
  `canonical_response(` call. `19-07`'s SUMMARY records re-counting them against the
  tree, and that re-count was honest.
- `product.py:330` (cited at `tests/mcp/test_egress_parameters.py:13`) — **stale**: line
  330 is now a docstring line, not the `parameters={}` hard-wiring it names. This
  predates Phase 19 and describes a defect already repaired; **informational, not this
  phase's drift.**
- The remainder are symbol (`::`) citations with no line number, unaffected by drift.

**So the hole is real and structural, but Phase 19 introduced exactly two new stale
citations through it, both in `.planning/STATE.md`.** `C-13` kept this phase narrow, so
fixing the lint was correctly out of scope; whether the two citations are re-anchored is
a ruling for Dave (escalated).

### INFO F-4 — each door cross-check has exactly one tripwire

`egress.py`'s `product_class` and `parameters` cross-checks are each guarded by exactly
one test (S5a and S5b each turned exactly one test red). The temporal axis has two. Not a
defect — the refusals are also covered structurally by the client-side echo comparison —
but deleting either test would leave that door-side refusal unwatched.

### INFO F-5 — no debt markers, no stubs

`TBD` / `FIXME` / `XXX` across all 53 files this phase modified: **zero** (the one
`grep` hit is a `docs/DECISIONS.md` historical entry *quoting* the absence of them). No
`TODO` / `HACK` / `PLACEHOLDER` in source; the only hit is the pre-existing
`TENANT_PLACEHOLDER` constant name in the generated surface manifest.

### INFO F-6 — `D-IMPL-161` self-reports a project-law divergence

The phase landed directly on `main` with no phase branch, which diverges from
CLAUDE.md §2.2. `D-IMPL-161` records Dave's ruling of 2026-08-19 that the work stays on
`main`, states the reasons, and explicitly declines to amend CLAUDE.md. Recorded here so
the gate reviewer sees it; not a verification finding.

---

## 9. Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `.planning/STATE.md` | 15 | stale line citation, undetectable by the lint | WARNING | F-3 |
| `.planning/STATE.md` | 30 | stale line citation, undetectable by the lint | WARNING | F-3 |
| `tests/mcp/test_egress_parameters.py` | 13 | stale `product.py:330` citation (pre-existing) | INFO | F-3 |

No stubs, no empty implementations, no debt markers, no unwired artifacts.

---

## 10. Gaps Summary

**No must-have failed.** The phase goal is achieved and I established it the hard way:
ten properties broken out-of-tree, ten sets of controls watched turning red; four further
properties probed to a raise directly. Every control this phase claimed can fail, does
fail when its property is broken, and is discriminated by its own wording and by exact
exception type. The `C-18` residual is verified **open** rather than closed, and I found
no shipped prose claiming detection past it.

Three items are escalated to Dave rather than resolved here, because each is a decision
rather than a defect I can fix inside a verification pass: the absent ROADMAP Success
Criteria (F-1), the two stale `.planning/STATE.md` citations this phase introduced through
a lint hole it documented but could not close under `C-13` (F-3), and the `verify.key-links`
verb that can never pass (F-2).

The tree was left byte-identical to `920c171`.

---

*Verified: 2026-08-20T11:37:46Z*
*Verifier: Claude (gsd-verifier), goal-backward, FORCE stance*
