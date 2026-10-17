<!--
Copyright (c) 2026 David Castillo. All rights reserved.
Use, copying, modification, and distribution of the covered material
are governed by the CCF SDK Interim Software and Patent License
in the repository-root LICENSE.md and any controlling signed agreement.
Rights under that interim license begin only upon its execution
and are limited to its stated scope and term.
-->
# SEC-020 Parts 1–3 on cp-06-canonical — build brief

**Status, 2026-10-16.** PROPOSED for one build GO. Nothing is built. Branch
`sec-020-parts-1-3` at `638d54c8`. Asked for by Dave at 19:54 MST.

**Boundaries.**
- **Part 4 stays provisional:** the tenant is the enforced boundary, and
  `borrower_scope` is not an entitlement under the shared credential.
- **Part 5 stays parked.**
- **No SDK change:** `src/` and `runtime/` do not change. The only exception is
  option D1 (a2): one docstring sentence.
- **Estate:** reads only. Nothing is written to .76.
- **No release actions:** no merge, tag, upload or paid CI.
- **Sealed delivery untouched:** `01fc424d`, including `BANK-PACKET.md`, which
  is hashed in its manifest.
- **Kept:** per-question isolation and the D-IMPL-383 replay evidence.

**Shorthand.**
- **CP6:** `examples/cp-06-canonical-collateral-and-setoff-coverage/`
- **PB:** `packaging/bank-controlled/`
- **M:** the SEC-020 measurement, `ccf_saves/2026-10-16-383/sec020-measure/`,
  outside the repo. It is summarized in `PB/SEC-020-DECOMPOSITION.md`.
- **probes:** `ccf_saves/2026-10-16-383/sec020-brief/`. These are offline checks
  with no estate contact.

## 1. Baseline and files that change

**Baseline:** `638d54c8`. The measurement was taken on `5a3e9b9f`. Between the
two commits:
- CP6 and `runtime/` are unchanged.
- `src/` changed only under D-IMPL-385 (`resolver.py`, `product.py`,
  `child_resolver.py`, `composite.py`).
- `PB/verify.py` gained one allowlist entry.

Commit A re-measures the baseline anyway.

**The SDK already has the mechanism.**
- A declared `seam_refusals` binding
  (`src/ccf/controlplane/artifacts.py::SeamRefusalBinding`) is matched on the
  raised exception's exact `module.QualName`
  (`src/ccf/products/resolver.py::GovernedResolver._declared_seam_refusal`,
  :5983).
- A match becomes a governed `subject-unavailable` refusal
  (`::_refuse_declared_at_seam`, :6016-6019).
- CP6 already uses it for three unreachable-source cases
  (`ccf_config.yaml:57-66`).

| File | Change |
|---|---|
| CP6 `acquisition.py` | **Two exception classes.**<br>• `_resolve_facility` (:253-257) raises `FacilityNotHeld` instead of `LookupError`.<br>• `acquire` takes `borrower_scope`. Right after the lookup, a named check, `_outside_requested_scope`, raises `FacilityOutsideRequestedScope`. That is before `_policy`, `_debtor_names`, the Fluree walks and `_enrich` (:501-521). |
| CP6 `deployment.py` | `acquire` passes the effective `borrower_scope` (:124-129).<br>Docstrings: :114-122 and :346-352. |
| CP6 `ccf_config.yaml` | Two `seam_refusals` bindings beside :57-66.<br>Comments: :50-56, :91-94 and :116-128.<br>**Unchanged:** `request_contract`, including "entitled to walk" (:189), so the advertised tool description does not move. |
| CP6 spec, `artifacts/gates.yaml` | Spec sections §0.4, §A.3, §B.2, §D.2, §G.1 and §G.3.<br>Gates: G20 restated; G25 and G26 added (D2). |
| CP6 `README.md`, `FINDINGS.md` | README: :124-129 and "What would fail".<br>New findings: CP06C-F-08 (the raise) and CP06C-F-09 (the duplicated admit rule, D3). |
| `tests/examples/test_cp_06_canonical_output.py` | G20 test rewritten (:856-883).<br>Added: the G26 test, the policy-step check and the F-09 expected failure.<br>The replay test is re-pointed (§5). |
| `tests/examples/test_cp_06_canonical_bank_door.py` (new) | Runs the real door: `launch.sh`, then the checks, then `verify.py`, then `stop.sh`. |
| PB `door_checks.py` (new) and `tests/examples/test_bank_door_compare.py` (new) | The comparator and timing judge, with their estate-free tests, which run in hosted CI.<br>A separate module is needed because `verify.py` reads `sys.argv` at import (:26). |
| PB `verify.py`, `question.yaml` | Three new default checks, plus opt-in `--timing` and `--population` flags.<br>The probe ids go in `question.yaml`. |
| Cross-references | One sentence each in `examples/cp-06-collateral-and-setoff-coverage/README.md:101-103` and `tests/examples/test_cp_06_output.py:413-419`. Both say cp-06C "already gives" `ttl-anchor-refusal`. |
| Records | `PB/OPEN-SECURITY-ITEMS.md` item 3, `PB/SEC-020-DECOMPOSITION.md` and `docs/DECISIONS.md`. |

## 2. Recommended implementation

### Why the example may change

**Part 1 is an example defect.**
- cp-06C's own contract says an unresolvable facility "is a refusal"
  (`ccf_config.yaml:181-184`).
- Dave's ruling CP14-F-21 requires a missing anchor to produce a governed
  refusal (`examples/cp-14-credit-memo-context/spec/CP-SPEC-014_Credit_Memo_Context.md:1654`).
  Its census named the identical raise in the older cp-06.
- D-IMPL-261 lets an objectively wrong example change, and D-IMPL-386 lifted
  the freeze.

**Part 2 is different.** It works around an SDK ordering, inside the example:
the SDK runs the policy step after acquisition.
- Dave's 19:54 scope authorizes it: remove the extra acquisition, with "no
  additional SDK remediation".
- It is in tension with the probe rule (D3).

### The change

In `acquisition.acquire`, right after the one facility lookup and on the same
connection:

| Case | Raises | Cause | Error code |
|---|---|---|---|
| No row | `FacilityNotHeld` | `nonexistent` | `facility-not-held` |
| A row whose `borrower_lei or facility_id` is not in `borrower_scope` | `FacilityOutsideRequestedScope` | `undisclosed` (D1) | `outside-requested-borrower-scope` |

**The check is the policy step's own rule.**
- Every node is stamped `borrower_lei or facility_id` (`deployment.py:196`).
- The policy filter admits a node by exact membership in `borrower_scope`
  (`src/ccf/operators/categories.py::PolicyFilter._admits`, :295).
- So the check refuses exactly the questions the policy step empties today,
  and no served answer is lost.

The messages name the facility, never the borrower's LEI.

### What the caller sees

The bank runs at the default disclosure level, `minimal`
(`src/ccf/products/disclosure.py`); neither CP6 nor PB overrides it. Both cases
return:
- `isError:false`;
- kind and reason `subject-unavailable`;
- one fixed sentence;
- `fields {cause, error_code}`, both `"undisclosed"`;
- a fresh replay reference.

**Evidence so far is offline only.** The probe is
`probes/drafter/seam_undisclosed.py`, re-run on `638d54c8` with identical
output.
- Once the replay digest is masked, the two disclosed answers are
  byte-identical.
- The records differ in cause, error code and detail.
- Both stop at the `acquisition` seam with 0 steps, and neither leaves a
  pending marker.

This stays offline evidence until R1 and R2 pass through the bank door.

### What the record keeps

Each case's true cause, error code and detail. A made-up id becomes a
finished, replayable decision. Today it leaves a pending marker, no record, and
a traceback in `door.err`.

### Rejected

- **Return `nothing_acquired` for both cases.** It would not serve: by code
  reading, the TTL-anchor gate refuses first, even with
  `borrower_scope=[facility_id]`. But it has three faults:
  - it writes a facility claim for an id no source holds;
  - its reason, `ttl-anchor-unresolvable`, is a by-product, not the real reason;
  - the record can no longer tell the two cases apart. That breaks D-IMPL-253
    Q27: "Don't destroy audit truth".
- **Declare only the not-found case.** Its answer would still differ from
  today's out-of-scope `ttl-anchor-refusal` (probe [2]).
- **The SDK's early policy.** It is keyed on subject and principal, not on a
  request parameter, and it would pull in Part 4 and Part 5 machinery.
- **Put the scope test in the SQL.** Both cases would return 0 rows, so the
  record loses the distinction. This is held as the pre-named next step if the
  timing test fails.

### What is lost or changed

- **The out-of-scope answer changes.** Today it is `ttl-anchor-refusal`, after
  projection. After the fix it is `subject-unavailable`, at acquisition.
- **A trade.** Ten facilities are refused `ttl-anchor-refusal` even under their
  own borrower.
  - Today, their out-of-scope answer is byte-identical to that refusal, so
    guessing their borrower teaches nothing. After the fix, the two answers
    differ.
  - The other 50 facilities already reveal the relationship: 46 are served, 3
    are refused `ttl-bounds`, and 1 is refused by the over-allocation guard
    (`M/raw/sweep.jsonl`).
  - **Net:** the existence oracle for unknown ids closes, and the
    borrower-relationship oracle grows from 50 facilities to 60.
- **Policy-denial coverage moves.** The policy operator's denial no longer runs
  on cp-06C's real path. A patched in-process check keeps it covered (§5).
- **Composite children change (by code reading).** For cp-14 and sk-01
  (`src/ccf/products/child_resolver.py:715-763`):
  - an out-of-scope child becomes `ineligible` with `subject-unavailable`;
  - an unknown child becomes `ineligible` instead of a runtime failure.

  Their tests run in §6.
- **More permanent records.** Every made-up id now leaves a permanent record of
  about 0.1 MB, because nothing deletes evidence (`launch.sh:32-35`). Each
  default `verify.py` run adds 4.
- **The admit rule lives in two places:** the config and the acquisition code.
  Break S6 guards the copy, and F-09 records it.

### Residuals

- **Part 4.** `borrower_scope` is caller-supplied and has no size limit. A
  caller who names the right borrower, or all 22, still learns that a facility
  exists. The tool description still says "entitled to walk" (:189);
  rewording it is Part 4 work.
- **The record keeps the distinction, by design.**
  - The bank door exposes no record handle (`M/raw/verify.out`).
  - A tenant granted read-back of this class could read the record. The
    class's `subject_withholding: never` setting permits that grant
    (`src/ccf/products/contract.py:300-309`).
  - No CP6 or PB file makes that grant.
- **Timing.**
  - An existing facility's lookup returns one joined row; an unknown id
    returns none.
  - Whether `facility_id` is indexed is unverified. One read-only catalog query
    in §6 answers it.
  - §4 states what the test can and cannot detect.
- **Where it was measured:** one host, with the door on loopback, sources over
  the LAN, the demonstration estate, and no concurrent load. JSON-RPC ids and
  HTTP framing are not compared.
- **Absence is assumed.** `verify.py` cannot prove the made-up ids are absent
  from a bank's estate, so it prints that assumption.
- **Coverage is cp-06C only.** The decomposition's standard gate for every
  shipped product is not in this round.
- **Hosted CI skips the estate tests,** because nothing under `.github/` sets
  `CCF_CP_06C_*`. The evidence comes from local runs.

## 3. Masking in comparisons

`door_checks.compare(a, b)` returns a verdict for any input, including error
shapes: PASS, or FAIL naming the field. It never raises.
- It compares the raw text and the whole result, without re-serializing or
  sorting.
- It does not reuse the measurement's normalizer (`M/scripts/analyze.py`),
  which masked whole parameter blocks and key order.

**May be masked.** Each value is checked first, then replaced by exact
substitution.
1. **The 64-hex replay digest.**
   - It appears 4 times per copy: in `replay_ref` and in
     `refusal.replay_reference`, each written `<h>@<h>`.
   - It is masked only if all four are equal and both addresses match
     `ccf-artifact://<tenant>/ccf.replay-record/<h>@<h>`.
2. **The asked facility id, where it echoes the caller's input.** It appears
   in `answered.subject`, `request.parameters.facility_id` and
   `refusal.request.parameters.facility_id`.
   - It is masked only if each equals the id sent and the id appears exactly 3
     times per copy.
   - **Tool route:** two copies, `content[0].text` and
     `structuredContent.result`, which must be byte-equal.
   - **Template route:** one copy.
   - The two probe ids have the same length.
3. **Template route only: `contents[0].uri`.** It is masked only if it equals
   the requested address.

**Never masked:**
- `isError`, and on the template route, whether a result or an error came back;
- refusal `kind`, `reason`, `detail`, `disclosure`, `key`, and `fields` (keys
  and values);
- `policy_bindings` and `pre_assembly_lineage`;
- `content_address`, `product_json` and `producer`;
- `product_id`, `product_version` and `temporal_boundary`;
- `intent`, `freshness`, `asked_at` and `borrower_scope`;
- the key set and key order, and the text length;
- each content item's count, type, annotations and meta;
- whether `structuredContent` is present, and its shape;
- `mimeType`;
- whether a replay reference is present.

## 4. Timing method and threshold (fixed before any post-fix run)

**Method.**
- `door_checks.py` collects and judges the timings; `verify.py --timing` drives
  it.
- One MCP session, with `perf_counter` around each call. Each row keeps the
  elapsed time and the §3 signature.
- n = 100 pairs, after 2 warm-up pairs that are discarded. The order of the
  two arms alternates.

**Pairs.** The ids live in `question.yaml`.
- **T1, the bank pair:** FAC-5B8418 under `[529900E95812SYWMCE44]`, which is
  out of scope, against absent FAC-01A702 under the same scope.
- **T2, the whole population (with `--population`):** the 59 facilities not
  under `2549001IGRCG4F0RLD36`, against the 40 absent ids, under that scope.
  Ids are reused in rotation.
- **T0, the A/A control:** absent FAC-01A702 against absent FAC-0D0E2D, under
  T1's scope. Both arms reach the PostgreSQL lookup, before and after the fix.

**Rule.** For each pair, d = (existing arm's time) − (unknown arm's time).
- **PASS** for T1, and separately for T2, needs both:
  - 0.35 ≤ P(d>0) + ½P(d=0) ≤ 0.65;
  - |median d| ≤ 15 ms.

  A bootstrap 95% interval is reported.
- **Validity.** A run is valid only if T0 passes the same rule in the same
  session, with no transport or runtime failures.
  - Otherwise the run is INVALID and is rerun once. Two INVALID runs are
    reported as "don't know", never as a pass.
  - An INVALID run's T1 and T2 numbers are still reported.
- **Signatures.** After the fix, if any T1 or T2 pair's two answers have
  different §3 signatures, that is a **Part 1 FAIL**, naming the facility and
  the field.
- **Red before.** On Commit A, T1 and T2 must FAIL and T0 must PASS.
  Otherwise the instrument is suspect, and work stops.
- **Frozen inputs.**
  - Record the sha256 of `door_checks.py`, `verify.py` and `question.yaml`
    before Commit A's timing run.
  - Commit B touches none of these files.
  - The hashes are re-checked before judging.
- **No widening.** A FAIL goes to Dave with its numbers.

**Resolution.** These figures come from offline resampling of the measured
unknown-id arms, across 4 pools (`probes/drafter/recalibrate.out`).

| True difference | Chance the rule reports FAIL |
|---|---|
| 0 ms | 0–1% |
| +10 ms | 18–32% |
| +20 ms | 87–95% |
| +30 ms | 100% |

The resampling ignores drift and the record write that the fix adds. If either
T0 arm's interquartile range exceeds 58 ms, the report says these figures do
not apply.

**Report wording:** "With n=100 interleaved pairs on this host, the median
paired difference was X ms [CI] and P(existing slower) was Y, inside the band
fixed beforehand. The test catches a steady 30 ms difference and misses most
10 ms ones. It does not show the difference is zero: an existing facility
still costs one returned row."

## 5. Tests, control and deliberate breaks

### Sequence and instances

`launch.sh` refuses modified tracked files (:40), so every state that is run
is a local commit.
- **Commit A:** the spec, gates and tests, plus `door_checks.py`, `verify.py`
  and `question.yaml`. CP6's code and config stay as at `638d54c8`. This
  gives the red-before results.
- **Commit B:** CP6's code, config, README and FINDINGS. This gives the
  green-after results.

**Instance roots** go under `ccf_saves/<date>-sec020/` and are kept until Dave
rules. After each `stop.sh`:
- wait for the process to exit, because `stop.sh:6` does not wait;
- assert that `run/commit` is the commit under test;
- delete `secrets/instance.env`.

**Probe pair.**
- **W:** FAC-5B8418 under FAC-044206's borrower, `[529900E95812SYWMCE44]`. It
  exists and is out of scope.
- **A:** FAC-01A702, measured absent.

### Red tests

Each fails on `638d54c8` on an assertion, never on an error.

| Test | Asserts | Fails today because |
|---|---|---|
| R1 (G25, tool route) | `compare(W, A)` returns PASS | `isError` differs |
| R2 (G25, template route) | the same | one side is a result, the other an error |
| R3 | Both answers are governed refusals: `isError:false`, `subject-unavailable`, and a replay reference.<br>After `stop.sh`, `serve.py decisions` lists both and `serve.py replay` reproduces both.<br>No pending marker names A. | A has no record |
| R4 | `verify.py` exits 0 with its 3 new lines passing. It now guards each check, so on Commit A it reports failures instead of crashing. | the 3 new checks fail |
| R5 (G26, in-process, estate) | For W and A, `_resolve_facility` runs once, and `_policy`, `_debtor_names`, `_walk_*`, `watermark` and `_enrich` never run (counted with `sys.setprofile`). | W runs all of them |
| R6 (G20, real path) | The out-of-scope ask is refused `subject-unavailable` at acquisition, with 0 steps.<br>Its record's code is `outside-requested-borrower-scope`, against A's `facility-not-held`.<br>The detail contains no LEI. | today it is `ttl-anchor-refusal`, after projection |

### Kept executable

- **Policy-step check (passes).** With `_outside_requested_scope` patched to
  admit everything, today's G20 assertions still hold: an empty view, steps
  that ran, and `ttl-anchor-refusal`.
- **F-09 (strict expected failure).** Under the same patch, it asserts that the
  policy step alone stops the Fluree walks and the enrichment. It stays red as
  long as the SDK runs policy after acquisition.
- **The replay test** moves to `NO_COMMITMENT_FACILITY`, whose refusal still
  comes after projection. Commit A confirms its `rehydrated == 0` assertion.

### Controls

- **C1: a permitted request still serves.** This is `verify.py`'s question,
  FAC-5B8418 under its own borrower (`question.yaml`), and it must be served
  before and after the fix. If C1 fails, R1–R4 and the new `verify.py` lines
  report "FAIL: precondition not met", never PASS.
- **C2: the check does not refuse too much.** FAC-08D5BB under its own borrower
  stays `ttl-anchor-refusal` (measured, `M/raw/sweep.jsonl`).
- **Absence:** one keyed, read-only SELECT confirms that FAC-01A702 and
  FAC-0D0E2D are absent.
- **Existing tests stay green:** G10, expired-child, evidence_dir,
  replay_after_restart, sk-01 E3, dr-02, the cp-14 slices and `LANE_BASELINE`.

### Estate-free unit tests (run in hosted CI)

**Comparator.**
- PASS when only masked values differ.
- FAIL, naming the field, when:
  - any never-masked field changes;
  - an id count is wrong;
  - the two copies differ;
  - a replay reference is missing on one side;
  - keys are reordered.
- FAIL without raising on today's measured shapes
  (`M/raw/pair_a_full_bytes.json` and `template_pair.json`).

**Timing judge.**

| Input | Expected verdict |
|---|---|
| +0 ms | PASS |
| ±40 ms | FAIL |
| proportion in band, median 25 ms | FAIL |
| median within 15 ms, proportion about 0.8 | FAIL |
| T0 failing | INVALID |

### Deliberate breaks

- Each break runs on its own throwaway worktree and commit, and is never
  pushed.
- `__pycache__` is purged first, and everything runs under `python -B`.
- A break that ends in an AttributeError or a NameError is invalid and is
  redone.

| Break | Change | Must happen |
|---|---|---|
| S1 (G25) | Restore the `LookupError`. | R1–R4 go red; C1 stays green. |
| S2 (G26) | Move the scope check after the walks and `_enrich`. | R5 goes red and T1 FAILs. R1–R4 stay green, which shows the byte checks alone cannot see Part 2. |
| S3 | Add `refusal.kind` to the mask. | The comparator tests go red. |
| S4 | Rename the out-of-scope class but not its binding. | R1, R3 and R4 go red. |
| S5 | Add a 40 ms delay to the out-of-scope branch. | T1 FAILs while the bytes still PASS. |
| S6 (G20) | Make the scope check admit any scope. | R1 and R6 go red. |
| S7 | Give both bindings one error code. | R6 goes red. |
| S8 | Put the borrower's LEI in the message. | R6 goes red. |
| S9 | Drop either half of the timing rule. | The matching judge test goes red. |

## 6. Bounded verification plan and cost

1. **Commit A.** Expected results:
   - the comparator and judge tests are green;
   - R1–R6 are red;
   - C1, C2 and the policy-step check are green;
   - F-09 fails as expected;
   - `verify.py` reports 18 passed and 3 failed. A clean 18-of-18 run on this
     branch has not been shown yet (`M/MEASUREMENT.md`), and this run
     establishes it;
   - timing: T1 and T2 FAIL, and T0 PASSES.

   Then record the three hashes, and run one read-only catalog query for a
   `facility_id` index.
2. **Commit B.** Repeat the same runs. All are expected green, with `verify.py`
   at 21 of 21. Timing is judged per §4.
3. **Breaks S1–S9,** one worktree each. The S2 and S5 runs time T1 and T0 only.
4. **Regression runs:**
   - the CP6 test modules and `test_cp_06_output.py`;
   - the cp-14 slices, sk-01 (offline and against the estate) and dr-02;
   - `tools/product_gates_tests` and `make product-gates`, run directly;
   - `tools/lints/tests`, the docs tests and `make typecheck`.
5. **Report.** For each run, give passed, failed and errors as three separate
   numbers, and name what each covered. Report timing in §4's wording.

**Rules.**
- Every command runs under `env -i` with an allowlist. That strips `PG*`,
  `FLUREE_*`, `MONGO_*`, `NEO4J_*` and `CO_LENDER_*`.
- Gates run with pipefail and write their output to a file.
- Estate access is reads only: Fluree `fibo-v2` and PostgreSQL `ccf_v2`.

**Size.**
- **Timed questions: about 2,450.**
  - 612 each on Commits A and B.
  - 408 each for S2, S5 at +40 ms, and S5 at +20 ms, which is reported as a
    characterization only.
  - Every one reaches the PostgreSQL lookup on .76.
- **Byte checks:** a few dozen questions.
- **Disk:** about 250 MB of local evidence.

**Cost: $0. No paid run is proposed.**
- Hosted CI would skip the estate checks, and merging is out of scope.
- Pushes for Grok carry `[skip ci]`, because CI runs on every branch push
  (`.github/workflows/ci.yml:10-12`).
- For reference, the last full hosted run took about 76 billed minutes, about
  $0.61 (`PB/BANK-PACKET.md:253-254`).

## 7. Decisions for Dave (bundled)

**D1. The cause recorded for an out-of-scope refusal.** The caller sees
identical bytes whichever option is chosen. Only the record, and the answer at
the `full` disclosure level, differ.
- **(a) Recommended: `undisclosed`, with error code
  `outside-requested-borrower-scope`.**
  - It makes no entitlement claim.
  - The error code keeps the audit truth.
  - **Side effect:** the docstring of
    `src/ccf/products/refusal.py::SubjectUnavailableRefusal` says `undisclosed`
    is recorded "in two places only" (:280-284). That becomes incomplete. Two
    ways to handle it:
    - **(a1) Recommended:** leave `src/` alone, and log the sentence as a
      finding.
    - **(a2):** correct that one sentence. It would be the only `src/` change.
- **(b) `unauthorized`.** The SDK defines it as "a subject the principal may
  not receive" (:275-276). That is an entitlement claim, and the Part 4 ruling
  says it is not true.
- **(c) `nonexistent` for both cases.** This is false for a facility that
  exists.

**D2. Approve the spec and gate changes with this GO.** Specs come before code,
and each gate cites one spec clause (D-IMPL-326).
- **G20, restated:** on the real path, an out-of-scope ask is refused
  `subject-unavailable` at acquisition. With that check bypassed, the policy
  step still empties the view.
- **G25, new:** an unknown facility and an out-of-scope one get identical
  answers through the bank door, on both routes, and the record keeps the
  distinction.
- **G26, new:** an out-of-scope ask makes the same source calls as an unknown
  id. The one row an existing facility returns is stated as a residual.
- **Accept the 10-facility trade** (§2).
- **Confirm one reading.** CP06C-F-08 is the example's own defect (criteria
  §B.4). §B.4's "never 'fixed' by tuning … the example's governed values"
  (`docs/EXAMPLE-EVALUATION-CRITERIA.md:110-121`) is aimed at data
  limitations, not at an example that breaks its own contract. So adding the
  binding is allowed under D-IMPL-261 and CP14-F-21.
- **Recommended: approve with the GO.** The alternative is a spec-only round
  first.

**D3. CP06C-F-09, the SDK side of Part 2.**
- **The tension.** The SDK runs policy after acquisition, so removing the extra
  acquisition means restating the admit rule in example code. That is in
  tension with the probe rule (kept by D-IMPL-386), D-IMPL-289 and D-IMPL-292
  (6).
- **The choice is classification, not whether to build.** Every example-side
  way to make the two answers match either restates the rule or gives up audit
  truth (§2, Rejected).
- **(a) Recommended: a candidate launch-ergonomics blocker (§B.2).** "A value
  that must be stated in two authorities that can drift apart" is §B.2's own
  example (criteria :92-93). It is not a blocker until you rule it one. If you
  do, an SDK cycle follows this round, and the example's check is then
  deleted, not moved.
- **(b) Backlog (§B.3).**
- **Either way,** the F-09 expected failure keeps the gap executable. If F-09
  is ruled an in-scope SDK issue, it counts toward the three-issue cap; the
  current open count is not verified here.

**One default chosen; say if you disagree.** `--timing` ships in `verify.py`,
off by default. Each run adds about 400 questions and about 40 MB of permanent
evidence on the bank's instance.
