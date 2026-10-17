<!--
Copyright (c) 2026 David Castillo. All rights reserved.
Use, copying, modification, and distribution of the covered material
are governed by the CCF SDK Interim Software and Patent License
in the repository-root LICENSE.md and any controlling signed agreement.
Rights under that interim license begin only upon its execution
and are limited to its stated scope and term.
-->
# Findings — cp-06-canonical

Findings raised while building the canonical rung-6 successor on the paved producer
road (`CP-SPEC-006C`, Gate 1 approved 2026-09-16; the bounded build ruled GO the same
day). Classified under `docs/EXAMPLE-EVALUATION-CRITERIA.md` §B before any repair;
each says whether the behavior is legitimate SDK semantics or a mismatch, with the
basis stated. Findings are raised, not resolved: every one below is Dave's to rule on.
The close-report sections follow §K.

## 1 · SDK capability proven

| §D item | how this tree exercised it |
|---|---|
| define / assemble | two documents, four callables, two regions; both operators, Π, the three L6 gates and the product's own gate run on the road |
| preserve product identity | **the lane, measured** (`CSCC-G13`): both declared facilities at the CP-14 instant hash to the specimen's payloads, `d22b256e…` and `8e3e567b…`, zero field-level differences → `1.0.0` |
| calculate Context Debt correctly | `D_c = 1 − F·C·S` over the operator view with the booted λ_c table and profile; equal to the specimen's to the last digit |
| refuse correctly | the gate refuses a facility the view does not size; an unknown intent refuses on the declared set; wrong producer id and wrong tenant refuse independently at the consumer |
| replay and reconstruct | `replay()` reproduces the served bytes from the recorded snapshot and the dimension-2 effective request, with no acquisition object alive; the gate refusal reconstructs through `replay_refusal()` with no product rehydrated (`D-IMPL-344`) |
| local and remote boundaries | the CP-14-shaped question through the standard door in another process, admitted `provider-controls`; the door and the in-process run serve one address |
| identity confusion prevented | the expected producer identity and tenant come from the registration (`CSCC-G18`) |

## 2 · SDK friction observed (§E)

Measured with the counter `docs/PAVED-ROAD-LOC-REPORT.md` uses; "relocated" means the
work now happens in the SDK or a document, not that it vanished.

| measure | specimen (low road) | successor (paved) |
|---|---|---|
| plumbing lines (`produce.py` + `server/serve.py`) | 247 (97 + 150) | **63** (36 + 27) |
| domain lines (`deployment` / `acquisition` / `projection`) | 749 (236 / 325 / 188) | 679 (171 / 315 / 193) |
| `run.py` | 84 | 101 (a `--door` flag and refusal printing) |
| documents, physical / non-comment | 4 documents, 430 / 253 | 2 documents, 443 / 276 |
| distinct `ccf.` names imported | 32 | **18** |
| duplicated authorities | the perspective and the TTL stated in code and in documents; the door's principal restated in `door.yaml` | 0 measured — the perspective, the TTL, the door identity and the class lane are each stated once |

**Relocated, not eliminated:** the effective-request derivation (`deployment.effective`,
34 lines) and the ingest loop with its order assertion (`deployment.ingest`, 24 lines)
moved into the SDK; the door's 150 lines became `open_door`; `backends.yaml` and
`door.yaml` became `ccf_environment.yaml` and the `door:` section. Documents grew by
23 non-comment lines: `replay:`, `ttl:` and `door:` are declarations the specimen kept
in code or in a third document.

**Friction named, none worked around:**

| id | finding | class | disposition |
|---|---|---|---|
| `CP06C-F-01` | **A replay environment for a paved product is assembled by hand.** Rebuilding Π at replay needs the EFFECTIVE parameters; the record carries them on dimension 2 as `request_resolution`, a canonical JSON string a consumer must parse into an `EffectiveRequest` and fold onto the asked request; the operator registry needs `build_governed_resolver(**opened.build_arguments(fabric))` and a private `_operator_parameters`; the envelope needs the deployment's TTL and anchor restated from the documents. ~40 lines of test code that every paved producer's replay proof would write again (§E "custom adapter or glue code") | 3 · post-launch enhancement, §I record below | recorded; the proof is written by hand here |
| `CP06C-F-02` | **The road hands Π the effective request and nothing from the side.** The specimen's Π closed over two acquisition values; the road offers no seam for that, and the honest shape turned out to be fabric state (the commitment on the facility node, `CSCC-G14`). Recorded as the measurement Dave asked for: for this graph-backed product it is the correct shape, not friction, and not a general rule that every input becomes a graph attribute | not a finding against the SDK | the ruling of 2026-09-16 stands |
| `CP06C-F-03` | **The specimen serves a coverage of zero over an empty view.** A scope the caller does not hold yields an empty graph; the low-road specimen serves `assets: []`, `coverage_ratio: 0` — a redacted answer that reads as an uncovered facility. The successor refuses through its declared gate (`CSCC-G20`). A behavior difference between two shipped producers of one product, disclosed in `CP-SPEC-006C` §G.3 | 4 · specimen-design limitation (the specimen is frozen, `D-IMPL-261`) | disclosed; the specimen is not edited |
| `CP06C-F-04` | **The specimen's freshness read a stored age, not the valuation date.** `deployment.debt` aged each asset by `now - valuation_age_days`, and `valuation_age_days` is a STORED column: `valuation_date + valuation_age_days` resolves to two dates on the whole table (`2026-08-17`, `2026-08-22` — the estate's load dates), so the count equals the valuation's real age only on the day it was loaded and drifts one day per day after. At the CP-14 instant the CP-14 facility's asset read 240 days old against a real 261. `D-IMPL-341` made the valuation date the claim's own `valid_from` (`deployment._valuation_instant`), `F` reads it, and the anchor reads the same instant (`CSCC-G23`). Measured: `F` 0.609 (real) against 0.634 (stored) at the CP-14 instant | 2 · example (a scorer aging from the wrong clock) — closed here 2026-09-18 | Closed; the specimen keeps the stored age (`D-IMPL-261`) |
| `CP06C-F-05` | **Truthful timestamps expire the demonstration, and the class's window and anchor name different evidence.** With `expires_at` anchored on the freshest valuation and the product window one day (the deposit-balance half-life), `FAC-5B8418` (valued `2025-12-20`) is refused `ttl-refusal` / `ttl-bounds` at the CP-14 instant, `FAC-044206` (`2026-08-15`) likewise, and no facility on this estate serves after `2026-08-21`. The refusal is the correct answer under the declarations and is asserted as the intentional correction; the serving tests ask each facility on its valuation day as the positive control; CP-14's collateral slot is `ineligible` for the same reason and the memo for BGC serves at no instant. The precise mismatch: the window follows the DEPOSIT clock (a balance the estate does not date — `ccf_v2.deposit_account` carries no as-of column) while the anchor can only read the VALUATION clock (the one dated evidence), so the declaration as written mixes two cadences. Two honest resolutions, both rulings rather than this tree's call: declare `from_decision` (the fast-moving evidence carries no source instant; per-asset staleness stays in the payload), or keep the evidence anchor with a window matched to the valuation cadence under `D-IMPL-323`'s illustrative-calibration rule. Also measured: the frozen specimen — same anchor declared, no λ_c table the SDK can read — is refused `ttl-anchor-unresolvable` on every question since 341; its suites are quarantined `xfail(strict=True)` (`D-IMPL-261`), the specimen untouched, and `CSCC-G13` is held to the recorded payload addresses | 1 · product contract | **RULED and APPLIED 2026-09-18 (Dave):** keep evidence anchoring; align the window with the valuation cadence. `ttl.product_ttl_seconds` and `ttl.max_ttl_seconds` are now `half_life.real_property_appraisal` (31536000 s, ~365 days) from 86400 s, declared illustrative under `D-IMPL-323` with the deposit limitation stated at every site. Measured after: 47 of 50 collateralized facilities serve at the CP-14 instant, 3 refuse `ttl-bounds`, both demonstrations serve, and the ten CP-14 memo quarantines converted to passing tests. The window makes NO claim about the undated deposit balances |
| `CP06C-F-06` | **An unreachable source escapes `OpenedProduct.answer` as the driver's own error.** Measured 2026-10-15 and again 2026-10-16 (the `D-IMPL-383` acceptance run's positive control): with the attribute leg pointed at an address nothing listens on, `answer` raises `psycopg.OperationalError` out of this tree's `acquisition.acquire` rather than returning a governed refusal; the restarted-service test (`tests/examples/test_cp_06_canonical_replay_after_restart.py`) catches the raw driver error to make its offline proof. The question also leaves a graph and a pending marker in the evidence root, which `incomplete()` reports | SDK gap — **CLOSED 2026-10-16** (Dave, 12:11, option B). **The row's first diagnosis was wrong, and is corrected rather than erased:** the paved road HAS the seam — a class may declare exception types in `product_class.seam_refusals` (`D-IMPL-347` B2), measured to turn an outage into a recorded, replayable refusal — and an undeclared one propagating is the ruled behavior (`PKG-F-03`). The real gap: every declared exception could only be refused as `subject-unavailable`, *"the requested subject is not available to this principal"*, false for an outage | The SDK adds the `source-unavailable` refusal kind, minted from `cause: source-unavailable` (its own sentence, `detail` withheld below `full`, HTTP 409). This tree declares its two legs' connection errors (`psycopg.OperationalError`, `httpx.ConnectError`, `httpx.ConnectTimeout`) in `ccf_config.yaml`. Measured: with both legs unreachable a question is a recorded `source-unavailable` refusal that replays, and nothing is left incomplete; with the declaration removed it is the raw `psycopg.OperationalError` again |
| `CP06C-F-07` | **Opening a product to inspect or replay retained evidence demands every source setting.** `decisions`, `why` and `replay` (`server/serve.py`, 2026-10-16) never read a source — measured: every retained decision replays identically with both sources pointed at an address nothing listens on and the ledger and schema names wrong — yet `open_product` refuses unless all four source variables are set, so an auditor without database credentials cannot run them | SDK friction (open for answering and for replaying are one call) — **CLOSED 2026-10-16** (Dave, 10:23: *"fix it"*) | `open_product(..., read_sources=False)` resolves no source setting; such an opening answers nothing (`SourcesNotRead`, before anything is minted or recorded) and the acquisition seam reads the settings only when it runs, so replay needs none. The three commands open that way: measured, all run in an environment holding no `CCF_CP_06C_*` variable |
| `CP06C-F-08` | **An unknown facility raised instead of refusing, and the answer told a caller whether a facility existed** (SEC-020, measured 2026-10-16 through the bank's own door on `5a3e9b9f` and the delivered `01fc424d`). `acquisition._resolve_facility` raised an undeclared `LookupError`, which the door turned into an opaque `ccf-runtime-failure` with no record, while an existing facility outside the stated `borrower_scope` was read in full — collateral, set-off, register — and then refused `ttl-anchor-refusal` over the empty view: 59 of 59 out-of-scope facilities against 40 of 40 absent ids, medians 634 ms against 211 ms. The tree contradicted its own contract ("an unresolvable facility is a refusal", `ccf_config.yaml`) and Dave's `CP14-F-21` ruling | 4 · the example's own design — the SDK had the seam (`D-IMPL-347` B2; `CP06C-F-06` is the precedent). Fixing it by adding a governed binding is allowed under `D-IMPL-261` and `CP14-F-21`; §B.4's "never fixed by tuning governed values" is read as aimed at data limitations (Dave, D2, 2026-10-16 21:32) | **CLOSED 2026-10-16** (SEC-020 Parts 1-3 GO). One lookup decides: `acquisition.FacilityNotHeld` (cause `nonexistent`, code `facility-not-held`) and `acquisition.FacilityOutsideRequestedScope` (cause `undisclosed`, code `outside-requested-borrower-scope` — Dave's D1: no permission claimed) are declared `seam_refusals`; both are one `subject-unavailable` answer through the bank door (`CSCC-G25`), both make one source call (`CSCC-G26`), and an out-of-scope ask is refused at acquisition (`CSCC-G20`, restated). **The trade, accepted (D2):** ten facilities refused `ttl-anchor-refusal` under their own borrower used to look identical to an out-of-scope ask; now they do not, so the borrower-relationship oracle grows from 50 facilities to 60 while the existence oracle for unknown ids closes |
| `CP06C-F-09` | **The scope rule is stated twice, because the SDK applies the policy step only after acquisition.** `policy.principal-subgraph` admits a node by exact membership of its `borrower_scope` stamp in the request's `borrower_scope`, but it runs over L3 after every source was read; nothing the SDK offers lets that declared rule stop the reads. Removing the extra acquisition (SEC-020 Part 2) therefore meant restating the rule in `acquisition._outside_requested_scope` (`scope_stamp` keeps the stamp one definition; the membership rule is still two). The SDK's early policy decides only from subject, principal and role lists and cannot express a request-parameter scope | 2 · **candidate launch ergonomics blocker — RAISED, not ruled a blocker** (Dave, D3, 2026-10-16 21:32: *"raise it as a candidate SDK ease-of-use blocker, not a silent backlog item … Do not fix it in this round."*). §C step 1: yes; step 2: yes — §B.2's own example, "a value that must be stated in two authorities that can drift apart"; the §I record is in §4 | Kept visible: `test_the_policy_step_alone_keeps_an_out_of_scope_facility_from_being_read` is `xfail(strict=True)` and goes green — and strict-fails — the day the SDK applies policy before acquisition; the example's check is then deleted, not moved. Break S6 (the check admits any scope) is the guard on the copy meanwhile |
| `CP06C-F-10` | **The SDK's own sentence about `undisclosed` is now incomplete, and it has no cause for "outside the caller's stated scope".** `src/ccf/products/refusal.py::SubjectUnavailableRefusal` says `undisclosed` is recorded as a determination "in two places only" (the two SDK constants); a declared seam binding with `cause: undisclosed` — this tree's out-of-scope refusal — is a third. `undisclosed` is the nearest true value: `unauthorized` would record an entitlement claim the Part 4 ruling says is untrue, `nonexistent` is false for a facility that exists | 3 · post-launch enhancement (documentation, and a possible cause value) | Recorded; `src/` is not edited (Dave's GO: "No SDK change beyond the optional docstring" — option (a1) taken, leave it and log it) |

## 3 · Launch blockers

None ruled. `CP06C-F-09` is RAISED as a candidate launch ergonomics blocker (Dave's D3,
2026-10-16) and is not a blocker until ruled one; its §I record is in §4.

None raised by this tree at Gate 1. `D-IMPL-341` (the expiry anchor) was inherited and
OPEN — `CSCC-G23` quarantined `xfail(strict=True)` evidence — until 2026-09-18, when the
SDK honored the declaration, this tree was migrated (`CP06C-F-04`) and the window was
recalibrated to the valuation cadence on Dave's ruling (`CP06C-F-05`). Both gates are
live, `CSCC-G24` was added as the calibration's own negative control, and nothing is
carried open here.

## 4 · Backlog candidates (§I)

**Policy that can stop acquisition — `CP06C-F-09`, an UNRULED candidate launch ergonomics
blocker** (Dave's D3, 2026-10-16). *capability:* the SDK applies a product's declared
request-bound policy envelope before acquisition reads any source — or hands acquisition
an admit predicate derived from that same declaration — so a request whose scope admits
nothing is refused before any read, with the rule stated once. *evidence:* `CP06C-F-09`
(this tree, SEC-020 Part 2): an out-of-scope ask made seven source reads after the facility
lookup — the policy and enforceability tables, the debtor crosswalk, three graph walks, the
ledger watermark and the enrichment — and its answer took a median 634 ms against an
unknown id's 211 ms (measured 2026-10-16 through the bank's own door). One rung; no other
rung was checked (§H). *current supported path:* restate the admit rule in acquisition and
raise a declared seam refusal (this tree, ~25 lines and a strict expected failure); the
SDK's early policy cannot express a request-parameter scope. *friction:* one rule in two
authorities — the operator declaration and the acquisition code — kept aligned by a shared
stamp function and a break that proves the copy is guarded; nothing in the SDK says the
policy step runs after acquisition. *adoption impact:* every product whose policy envelope
depends on a request parameter and whose sources are costly to read, or whose answer
timing must not reveal what exists. *launch necessity:* §C step 1 yes — nothing
inadmissible reaches the view; step 2 yes — §B.2's own example, and the alternative leaks
existence by timing; raised for a ruling, not a blocker until ruled one. *scope/risk:* the
resolver's phase order or a policy-derived acquisition predicate, at every paved
product's acquisition seam; risk to products whose acquisition legitimately needs more
than the admitted subgraph. *recommended release:* before launch if ruled a blocker;
otherwise when a second product needs request-scoped policy ahead of its source reads.

**The `undisclosed` sentence and a scope cause — `CP06C-F-10`.** *capability:* the
`SubjectUnavailableRefusal` documentation names every way `undisclosed` is recorded,
including a declared seam binding, and the SDK decides whether "outside the caller's stated
scope" deserves its own cause. *evidence:* `CP06C-F-10`. *current supported path:* cause
`undisclosed` plus a specific `error_code`, which keeps the record's truth. *friction:* a
reader of the SDK docstring is told something no longer complete. *adoption impact:* every
product with a caller-stated scope. *launch necessity:* §C step 1 yes; step 2 no. *scope/
risk:* one docstring, optionally one cause value; none to the served path. *recommended
release:* with the next SDK documentation pass.

**A reference replay environment for paved products.** *capability:* an SDK-supplied
`ReplayEnvironment` derived from an opened product's two documents — Π from the recorded
effective request, the operators from the recorded pins, the envelope from the declared
TTL and anchor — so a paved producer's replay proof is one call. *evidence:* `CP06C-F-01`
(this tree); `tests/products/test_d_impl_339_child_contract_view.py::_FreshEnvironment`
and `tests/examples/test_cp_06_canonical_output.py::_FreshEnvironment` are the same ~40
lines twice. *current supported path:* hand-assemble as above. *friction:* one private
attribute, one canonical-string parse, three restated declarations. *adoption impact:*
every producer that proves replay. *launch necessity:* §C step 1 yes (replay itself
works; the environment is assembly), step 2 candidate — a third copy is the case for
generalization (§H). *scope/risk:* a builder over `OpenedProduct`; none to the served
path. *recommended release:* when the third paved producer proves replay.

## 5 · Estate / example limitations

The estate's `valuation_age_days` is a recorded column, not a value computed from the
instant: BGC's receivable is dated 2025-12-20 and aged 240 days by the estate; the debt
decays that age from the decision instant. The register covers Florida only and does
not name the facility (`D-IMPL-321`); lien priority is an authoritative input on the
reified pledge. Both are the specimen's limitations, inherited unchanged.

## 6 · Product result

At `2026-09-07T12:00:00+00:00`, class defaults: BGC Group's `FAC-5B8418` is covered
5.4972 × over a 40,000,000 commitment — 9,371,046 collateral after haircuts and
210,518,931 enforceable set-off, four accounts excluded as unenforceable, one receivable
aged 240 days, `D_c` 0.3660 `ok`. Avis's `FAC-044206`: 1.0890 ×, one shared asset
allocated senior, `D_c` 0.3769. A consumer can rely on: the two legs reported
separately, the priority per (facility, asset), the valuation date per asset, the
released liens the register reports. A consumer cannot rely on: the served `expires_at`
as a freshness claim (`D-IMPL-341`), and legal UCC priority (`D-IMPL-321`).

**Since SEC-020 (2026-10-16):** an unknown facility and a facility outside the stated
borrower scope get one governed `subject-unavailable` answer through the bank's own door,
each a recorded decision that replays; a consumer cannot use this product to learn whether
a facility exists unless it names the facility's own borrower (the scope is the caller's
statement, not a permission — SEC-020 Part 4, provisional). An existing facility's lookup
still returns one row where an unknown one returns none; `verify.py --timing` reports what
that costs against a rule fixed before the fix ran.

## Sabotage record

Run by hand on the candidate after the build, restored by copy and verified with `cmp`
before commit; the roster's `observed_red` names the ones that ran.

| sabotage | applied to | red | green |
|---|---|---|---|
| S01 — the haircut applied as a premium | `projection.py` | `CSCC-G01`; `G13` (the payload moved) | the other 23 |
| S04 — pro-rata collapsed onto priority | `projection.py` | `CSCC-G04` | the other 25 |
| S09 — fabric URIs served | `projection.py` | `CSCC-G09`; `G04`, `G08`, `G13` | the other 21 |
| S14 — the commitment from a constant, not the view | `projection.py` | **`CSCC-G14`**; `G06`, `G13` (a wrong commitment mis-covers MasTec and moves the payload) | the other 22 — including the AST half of `G14`, which is why the behavioral half exists |
| S13 — one payload member renamed | `projection.py` | `CSCC-G13`; the gate then raises on the missing member, so every serve errors | — |
| S19 — the discovery set removed (the specimen's shape) | `ccf_config.yaml` | `CSCC-G19` alone | the other 25 |
| S20 — the gate lets a missing commitment through | `deployment.py` | `CSCC-G20`, `G10`, the `D-IMPL-344` reconstruction | the other 23 |
| S12 — a `door.yaml` naming a script path added | `server/` | `CSCC-G12` alone | the other 25 |
| S16 — one specimen file edited | the specimen's README | `CSCC-G16` alone | the other 25 |
| S17 — the SDK's S1: `resolve_ttl_anchor` returns the decision instant (2026-09-18, `D-IMPL-341` validation pass) | `src/ccf/products/expiry.py` | `CSCC-G23`; the two CP-14-instant refusal controls (the coverage serves again, decision-anchored) | the other 27 |

**SEC-020 Parts 1-3 (2026-10-16),** each on its own throwaway worktree and commit, never
pushed, `__pycache__` purged, `python -B`; every red below is an assertion, never an error.
Candidate `0b57fa7e`. "Door" is `test_cp_06_canonical_bank_door.py` through the bank's own
`launch.sh`; "timing" is `verify.py --timing` by the rule fixed before the fix ran.

| break | applied to | red | green |
|---|---|---|---|
| S1 — the undeclared `LookupError` restored | `acquisition.py` | `CSCC-G20`; `CSCC-G25` (tool: `isError`; template: result vs error); the replay check; `verify.py` | the served control; `G26`; the policy-step check; the own-borrower control |
| S2 — the scope check moved after the walks and the enrichment | `acquisition.py` | **`CSCC-G26` alone**; timing T1 at **+34.7 ms** (control valid) | the door, 5 of 5 — the bytes cannot see Part 2 |
| S3 — `refusal.kind` added to the mask | `door_checks.py` | the comparator's `refusal.kind` case | the other 49 |
| S4 — the out-of-scope class renamed, its binding not | `acquisition.py` | `CSCC-G20`; `CSCC-G25` both routes; the replay check; `verify.py` | the served control. **Also showed an adjacent runtime finding**: the undeclared exception's own message reached the caller on both routes — recorded as **SEC-030** (`packaging/bank-controlled/OPEN-SECURITY-ITEMS.md`), open, not fixed |
| S5 — +40 ms on the out-of-scope branch | `acquisition.py` | timing T1 at **+41.2 ms** | the door, 5 of 5; every timed pair's bytes identical |
| S5 — +20 ms (characterization only) | `acquisition.py` | timing T1 at +21.4 ms | — |
| S6 — the scope check admits any scope | `acquisition.py` | `CSCC-G20`, `CSCC-G26`, `CSCC-G25` both routes, the replay check, `verify.py` | the served control; the policy-step check |
| S7 — one error code for both bindings | `ccf_config.yaml` | **`CSCC-G20` alone** | the door, 5 of 5 (codes are withheld at `minimal`) |
| S8 — the borrower's LEI in the message | `acquisition.py` | **`CSCC-G20` alone** | the door, 5 of 5 (the detail is withheld at `minimal`) |
| S9 — either half of the timing rule dropped | `door_checks.py` | the matching judge case (`proportion-0.8-only` / `median-25-only`) | the other 49 |

Restored tree after the sweep: 26 passed, 1 xfailed (`CSCC-G23`, as declared); the
(2026-09-18, after `D-IMPL-341` and the calibration ruling: 29 passed, 0 xfailed —
`CSCC-G23` live at the CP-14 instant, `CSCC-G24` holding the expiry refusal on a
facility whose evidence really did outlive the window, and the consumer's `ineligible`
crossing asserted on that same subject.) The
specimen diff-empty. Not individually sabotaged: `G02`, `G03`, `G05`, `G07`, `G11`,
`G15`, `G17`, `G18`, `G21`, `G22` — each asserted, its described sabotage recorded on
the roster with `observed_red: null`.
