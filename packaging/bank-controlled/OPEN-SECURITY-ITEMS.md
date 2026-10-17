<!--
Copyright (c) 2026 David Castillo. All rights reserved.
Use, copying, modification, and distribution of the covered material
are governed by the CCF SDK Interim Software and Patent License
in the repository-root LICENSE.md and any controlling signed agreement.
Rights under that interim license begin only upon its execution
and are limited to its stated scope and term.
-->
# Open security items — for review and ordering

Status as of 2026-10-16 22:5x MST. Items 1–16 were measured against the delivered build
`01fc424d` (`main` at `8193c607` carried only documents after it). The replay-evidence
work on branch `replay-evidence-383` (`D-IMPL-383`) closed none of these items and
changed none of them. Item 3's cp-06C result was measured on branch `sec-020-parts-1-3`
(`76f5d338` before the fix, `0b57fa7e` after). **That fix is not in the delivered build
`01fc424d`: on the build the bank runs, the existence oracle item 3 describes is still
there.** Item 17 (SEC-030) was closed 2026-10-17 (`b8e19a1c`). Both fixes are on `main` since
`d5c98f45` and in a replacement CANDIDATE wheel built from it — `ccf_sdk-1.0.2.dev1608+gd5c98f45a`,
SHA-256 `fed7e86f2731b3e8e6593341af016fbd07ef99cdca0b6ffce8dd774e52d5ad65`, verified as installed
(`ccf_saves/ccf-sdk-replacement-candidate-2026-10-17/`) — which has NOT been delivered or deployed: the
bank's installation is still `01fc424d`, which contains neither.

This is the 16-item list shown to Dave on 2026-10-13 09:40 MST and sent to the
bank; the numbers are the ones the bank's answer uses. Item 17 (SEC-030) was added on
2026-10-16, after the list was sent, and numbered 17 so that 1–16 keep their meaning. Token estimates are left
out on purpose: Dave ruled them unvalidated (2026-10-13 03:53 MST).

## The bank's answer (2026-10-15 18:09 MST, relayed by Dave)

1. *"is there an alternative to SqlLite for CCF-SDK and can multiple
   applications share the same repository instead of individual SqlLite."*
   The replay part of this led to `D-IMPL-383`. Dave, 2026-10-16 15:05 MST, read the
   question as being about persisting replay records: *"so I think we are ok there."*
   Nothing has been built or ruled on several applications sharing one store.
2. *"They want a detailed breakdown of the SEC-02 issue more than what was
   presented to them."* Dave, 2026-10-16 14:37 MST: the bank means **SEC-020**
   (item 3 below). Addressed by `SEC-020-DECOMPOSITION.md` (beside this file), from a
   read-only measurement of the bank configuration: Part 4 has Dave's provisional ruling
   ("Ruling for now", 15:53). Parts 1–3 were since built and accepted for the tested cp-06C
   deployment only (item 3; Dave, 2026-10-16 22:36), and are not in the delivered build;
   Part 5 is parked. Nothing has been sent to the bank.

## A. Security register: 25 of 30 closed, 5 open

SEC-030 (item 17) was added 2026-10-16 and closed 2026-10-17 (`D-IMPL-388`). SEC-020 stays open SDK-wide; its Parts 1–3 are closed for the tested cp-06C deployment only (item 3).

| # | Item | What it is | Severity | Reaches the bank's setup? | What closing it takes |
|---|---|---|---|---|---|
| 1 | SEC-001 (residual) | Separate processes sharing one approval store are not detected; approval identity does not carry from one store to another. | CRITICAL (main part fixed) | No: one engine, store and approval queue per instance. | Build the remainder of design 1.4; runs paused before the upgrade then need a fresh approval. |
| 2 | SEC-013 | Limits of the SQLite single-writer lock: a hard-link backup blocks every startup; a live database moved without a declared lock folder can admit a second writer and lose commits. | Not rated | As operating rules only; the setup creates the lock folder. | Verify option (C) (built 2026-10-08) and Dave's ruling on the disclosed limits. |
| 3 | **SEC-020** | A caller may be able to tell a withheld subject from one that does not exist. The 21 cases of the closing gate's pin-channel test that had failed (of its 364) pass on `01fc424d`. Still open in the register: three limitation blocks (D1 (a) 30/88, P6 24/44, E2 (ii) 82/82); the shared-owner check in a long-running service (16 (C), unbuilt, HIGH); a composite child's record that names the stand-in (HIGH, disclosed only); question stores reachable by a raw writer; the file-backed store's `get`, which does not re-hash; timing (one extra read per question, measured at one scale; write timing over the wire, disclosed, not measured). | Parts HIGH | **Yes, by a route the register did not list — measured 2026-10-16** through the bank's own `launch.sh` (one shared credential, minimal disclosure): an existing facility whose `borrower_scope` names another borrower gets one constant governed refusal with a replay reference, while a well-formed id that does not exist gets a tool error (`ccf-runtime-failure`) with no decision record and no replay reference when it reaches acquisition — 59/59 against 40/40 on branch commit `5a3e9b9f`, 10/10 against 10/10 on `01fc424d`. Timing separates them too (one fixed pair: medians 634 vs 211 ms on the branch, 561 vs 178 ms on `01fc424d`; one host). The server still logs each failure, and on the branch keeps a pending evidence marker naming the asked id. Cause: cp-06C raises an undeclared `LookupError` for an unknown facility, and fetches an existing one in full before its policy step empties the view. **Dave, 2026-10-16 15:53 MST, "Ruling for now": treat `borrower_scope` as not a real permission under the current shared-credential configuration.** It is a value the caller supplies; the caller-identity boundary is the one shared credential and its tenant grant (a tenant the grant does not carry got identical errors for one existing and one missing facility, measured on the branch). So what SEC-020 reveals here is whether a facility id exists. The reachable surface is Parts 1–3 of `SEC-020-DECOMPOSITION.md`; the identity work (section C) stays deferred. Measured not engaged for cp-06C: the P6 probe, 16 (C), the stand-in checks, the composite-child path, the population phase; the "one extra read" runs on every question that reaches acquisition, as a cost. The raw-writer and store-`get` gaps are not reachable through the door. Evidence: `ccf_saves/2026-10-16-383/sec020-measure/`. | **Parts 1–3 ACCEPTED AND CLOSED for the tested cp-06C deployment under the provisional Part 4 framing** (Dave, 2026-10-16 22:36 MST, adopting Grok's ruling): *"SEC-020 Parts 1–3: accepted and closed for the tested cp-06C deployment under the provisional Part 4 framing. The measured response comparisons pass and timing meets the agreed threshold. Residual timing, caller-selected borrower scope, Part 5 and identity work remain open. SEC-020 is not closed SDK-wide."* Built on branch `sec-020-parts-1-3` (`D-IMPL-387`, brief `SEC-020-PARTS-1-3-BRIEF.md`), measured through the bank's own `launch.sh` before (`76f5d338`) and after (`0b57fa7e`): an unknown facility and an out-of-scope one get one governed `subject-unavailable` answer, byte-identical apart from the replay digest and the echoed id, on the tool and the template route and on all 200 timed pairs; both are recorded decisions that replay. Timing by the rule fixed before the fix ran: bank pair +261 ms → −1.0 ms [−3.5, +1.0], population +252 ms → +1.0 ms [−1.3, +3.9], the A/A control valid. **Still open:** the residual timing (an existing facility's lookup returns one row, an unknown one none); caller-selected borrower scope (naming the right borrower still reveals existence — Part 4, provisional); Part 5; the identity work; every other product. The message leak found during the build is SEC-030. |
| 4 | SEC-027 | The `ccf-sdk` name is not reserved on PyPI. | Not rated | No runtime effect | Dave's upload of a placeholder (reverses "no PyPI upload"). |
| 5 | SEC-029 | No release tag, so the build carries a development version number (`1.0.2.dev1564+g01fc424d9`). | Not rated | Version string only | A tag (reverses "no tag"). |
| 17 | **SEC-030** (new, 2026-10-16) | An undeclared exception raised while a product acquires its data reaches the caller as its own message text. The MCP door maps only `ValueError`, `TypeError`, `LookupError` and `OSError` to its opaque `ccf-runtime-failure:<id>` (`runtime/ccf_runtime/mcp/egress.py`, the `except` in `_answer_question`); any other exception reaches the caller as raw text on both routes — the product tool as an `isError` result (*"Error executing tool request_context_product: …"*) and the address-form template as an `McpError` (*"Error creating resource from template: …"*). Found by deliberate break S4 of the SEC-020 build: with cp-06C's out-of-scope exception renamed so its binding no longer matched, the caller received *"facility 'FAC-5B8418' is outside the requested borrower_scope; …"* on both routes (`ccf_saves/2026-10-16-sec020/breaks/S4/`). | Not rated | Measured only through that break. Which real failure paths of a deployment reach it was not investigated (Dave, 2026-10-16 22:36: no fix or broader investigation this round). | **CLOSED 2026-10-17 for the protected MCP acquisition and resolution path — the resolver call and the answer's emission inside `_answer_question`, on the product tool and the address-form template. Entitlement failures (the step that runs before the resolver) and every other surface remain outside it: the standing product resource `ccf-product://{tenant}/{class}/{version}` (its handler has no fault clause; the standard door the bank uses does not register it, `build_egress_server` does by default), the HTTP API door, the experience and agent tools, and the HITL resources** (Dave, 00:44 MST: *"fix SEC-030"*; 01:14: *"Keep closure explicitly scoped"*; `D-IMPL-388`), on branch `sec-030-fix` (`b8e19a1c`), merged to `main` at `d5c98f45`; in the candidate wheel `1.0.2.dev1608+gd5c98f45a`, not in a delivered build. The fault clause in `_answer_question` now catches `Exception` and calls the unchanged `_opaque_failure`; the governed types are still caught around the resolver call first, `BaseException` still propagates, and the caller-input checks before the resolver are untouched. `tests/mcp/test_egress_unexpected_failure_is_opaque.py`: 11 red before, 13 green after, on both routes — five exception kinds cross only as `ccf-runtime-failure:<id>`, the same id is logged with the chain's types and frames, and the text reaches no log. Re-run through the bank's own `launch.sh` with SEC-020's break S4 applied: both routes answered `ccf-runtime-failure:<id>`, `logs/door.err` held the ids beside `FacilityOutsideTheRequestedScope` and no message text. |

## B. Other open items

| # | Item | What it is | Severity | Reaches the bank's setup? |
|---|---|---|---|---|
| 6 | SEC-009 erasure claim | Erasure design 1.3 is not independently verified. | Not rated | No (no artifact server) |
| 7 | Follow-up 1 | A late opposite approval verdict can stall an approval step permanently; it never lets one pass wrongly. Fixing it changes `D-IMPL-366` H2. | MEDIUM | No |
| 8 | Follow-up 2 | The same stall through an escalation filed under the approval step's key. | MEDIUM | No |
| 9 | Follow-up 6 | An erasure through the MCP-backed store never completes. | Functional, not a leak | No |
| 10 | Designs 1.5, 1.6 | Audit recovery and record authenticity: ruled 2026-10-09, not built. | Not rated | Not assessed |
| 11 | Early HTTP refusals | 401/403 answers made before the authorizer is asked leave no audit or replay record. | Not rated | No (no HTTP door) |
| 12 | Resource read without a request | Raises an error instead of returning a clean refusal. | Not rated | Not assessed |
| 13 | Decimal scale | 1.0 and 1.00 get different content addresses; deliberate under Dave's 2026-10-11 20:19 ruling 1. | Not rated | Not assessed |
| 14 | Follow-up 5 | No conformance test that a third-party approval transport checks eligibility; MCP "cannot verify" timing not measured. | Not rated | No |
| 15 | R-1, R-2, R-3 | Test-harness process-id reuse; the wrong message for an empty tenant id; a check that can never run. | LOW | No |
| 16 | Follow-ups 3, 4; MCP door argument | 27 stale docstrings; the 403 row in the authoring Standard v0.3; a request argument a model cannot work out. | Docs and usability | No |

## C. Deferred by ruling (Dave, 2026-10-12 22:44 and 2026-10-13 03:53 MST)

Follow-ups 7, 8 and 9. Dave named this group the one the bank is most likely to require fixed.

- An unauthorized ask about a restricted record gets the same answer as a record that does not exist.
- No disclosure level states only "not entitled to this information wall" for a named employee.
- The door judges the shared credential, not the employee an agent acts on behalf of.

## D. Not in the bank packet

143 smaller review residuals in `docs/D-IMPL-377-CLOSE-OUT.md` section 7h (34 tied
to SEC rows), last statused 2026-10-07.

## Sources

`packaging/bank-controlled/BANK-PACKET.md` section 5; `docs/DECISIONS.md`
(`D-IMPL-376` to `D-IMPL-383` and the 2026-10-11 to 2026-10-13 rulings);
`docs/D-IMPL-377-CLOSE-OUT.md` section 7h.
