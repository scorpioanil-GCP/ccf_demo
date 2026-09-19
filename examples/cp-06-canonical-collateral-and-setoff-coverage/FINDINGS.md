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
| `CP06C-F-05` | **Truthful timestamps expire the demonstration, and the class's window and anchor name different evidence.** With `expires_at` anchored on the freshest valuation and the product window one day (the deposit-balance half-life), `FAC-5B8418` (valued `2025-12-20`) is refused `ttl-refusal` / `ttl-bounds` at the CP-14 instant, `FAC-044206` (`2026-08-15`) likewise, and no facility on this estate serves after `2026-08-21`. The refusal is the correct answer under the declarations and is asserted as the intentional correction; the serving tests ask each facility on its valuation day as the positive control; CP-14's collateral slot is `ineligible` for the same reason and the memo for BGC serves at no instant. The precise mismatch: the window follows the DEPOSIT clock (a balance the estate does not date — `ccf_v2.deposit_account` carries no as-of column) while the anchor can only read the VALUATION clock (the one dated evidence), so the declaration as written mixes two cadences. Two honest resolutions, both rulings rather than this tree's call: declare `from_decision` (the fast-moving evidence carries no source instant; per-asset staleness stays in the payload), or keep the evidence anchor with a window matched to the valuation cadence under `D-IMPL-323`'s illustrative-calibration rule. Also measured: the frozen specimen — same anchor declared, no λ_c table the SDK can read — is refused `ttl-anchor-unresolvable` on every question since 341; its suites are quarantined `xfail(strict=True)` (`D-IMPL-261`), the specimen untouched, and `CSCC-G13` is held to the recorded payload addresses | 1 · product contract — a ruling owed | Open; raised to Dave 2026-09-18 |

## 3 · Launch blockers

None raised by this tree at Gate 1. `D-IMPL-341` (the expiry anchor) was inherited and
OPEN — `CSCC-G23` quarantined `xfail(strict=True)` evidence — until 2026-09-18, when the
SDK honored the declaration and this tree was migrated (`CP06C-F-04`); what that did
to the demonstration is `CP06C-F-05`, a product-contract ruling owed rather than a
launch blocker of the SDK.

## 4 · Backlog candidates (§I)

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

Restored tree after the sweep: 26 passed, 1 xfailed (`CSCC-G23`, as declared); the
(2026-09-18, after `D-IMPL-341`: 30 passed, 0 xfailed — `CSCC-G23` live, the
CP-14-instant refusals and the door's `ineligible` row asserted beside them.) The
specimen diff-empty. Not individually sabotaged: `G02`, `G03`, `G05`, `G07`, `G11`,
`G15`, `G17`, `G18`, `G21`, `G22` — each asserted, its described sabotage recorded on
the roster with `observed_red: null`.
