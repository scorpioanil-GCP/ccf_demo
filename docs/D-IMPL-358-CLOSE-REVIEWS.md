# `D-IMPL-358` Wave 2 — CLOSE PANEL reviews (step 15)

**Subject: the SHIPPED TREE.** Behaviour candidate `9926f594e1c01b1edda368ad5efefe3c9024f85d`,
branch tip at panel time `c5ba6f1fca2601a8e964a1d717425762bcfbee4c`. Not the plans — a phase
whose plans were reviewed before execution does not get a second plan review at close
(CLAUDE.md §3.1), so this file is distinct from any pre-execution review and does not
replace one.

**The panel was told the SDK is destined for a BANK**, and told to be more conservative than
for ordinary code. It was also handed the seven already-accepted items with an instruction
not to re-derive them, so its budget went to what is *adjacent* — the discipline
`D-IMPL-352` requires and the reason Phase 15.4's panel found a lint hole that predated the
phase entirely.

## The payload was HAND-ASSEMBLED, and here is what it left out

`$HOME/.claude/get-shit-done/workflows/review.md` gathers `*-PLAN.md` / `*-CONTEXT.md` /
`*-RESEARCH.md` and asks for a *plan* review — correct before execution, wrong at close. So
the close-time payload was assembled by hand from the shipped subjects, which CLAUDE.md §3.1
calls conforming provided the omissions are named. It was **inlined, not referenced by path**,
because codex's sandbox on this host can fail in a way that exits 0 having read nothing;
inlining makes a silent sandbox failure unable to empty the review.

Inlined complete: `src/ccf/signal/envelope.py`, `src/ccf/controlplane/temporal_boundary.py`,
`tests/examples/estate_guard.py`. Inlined by symbol: `refuse_temporal_bound`,
`TemporalBoundRefusal`, `AssemblyWorker` (first 400 lines), `score_at`, `_require_aware`,
`applicable`, `resolve_effective_request`, and the three `_utc_now` seams. Plus a mechanical
inventory of all 12 clock call sites in `src/` and `runtime/` with context. Total 109 KB on
**stdin** (a single argv string caps at 128 KB and dies rc=126 with no output).

**NOT in the payload, and so NOT reviewed by the external panel:** the bulk of
`src/ccf/products/resolver.py` (5119 lines; only `_utc_now` and the inventory context went
in), `src/ccf/products/product.py` beyond `_utc_now`, `src/ccf/products/constraints.py`
beyond the three symbols, all of `src/ccf/replay/`, `src/ccf/peering/`,
`src/ccf/products/child_resolver.py`, `runtime/` beyond the inventory context, and every
example tree. Those surfaces were covered instead by the in-session depth pass below, which
read the tree directly. **The external panel's silence about a file is not evidence about
that file.**

## Reviewer status — counted only where citations resolve

| reviewer | invocation | status | verdict |
| --- | --- | --- | --- |
| **codex** 0.137.0 | `codex exec -` on stdin, API-key auth | **OK.** All four worker anchors resolved (`admit_entity_claim:622`, `admit_relationship_claim:638`, `ingest:678`, `ingest_admitted:776`) | HOLD |
| **cursor** 3.19.13 | `cursor-agent -p --mode ask` | **FAILED first** — rc=1, 322 bytes, workspace-trust prompt. Re-run from a scratch cwd with `-f` so it could not reach the repo. Then OK | PROCEED |
| **gemini** | stdin | **Ran, noisily** — stderr carries a `ModelNotFoundError` 404 for a retired routing model; the review itself is grounded | HOLD |
| **depth pass** (this model) | 7 adversarial agents + 1 completeness critic, read-only | 8/8 returned; 10 anchors spot-checked, 10 resolve; **no fabricated citation found** | HOLD ×1 ruling |

A canary probe (`reply with GRIFFIN`) was run against each CLI before the payload, so a
reviewer that reads nothing was distinguishable from one that reads and disagrees.

## Retractions — both REJECTED, verified as hard as findings

**Gemini retracted accepted item 3** (`served_at` is hoisted once), citing
`runtime/ccf_runtime/mcp/product_door.py::_compose`. **Rejected: the strings `served_at`
and `admission_clock` appear ZERO times in that file.** Those two clocks are passed to
`ControlPlaneTenantAuthorizer` and `ControlPlaneProductEntitlementSource`; they are
authorization and entitlement instants, not the serve record's.

**Gemini's debt-neutralization finding — REFUTED BY MEASUREMENT.** It claimed a future
`observed_time` becomes `valid_from`, and under a `decay_basis: valid-from` row the freshness
scorer reads a future instant, evaluating the claim as maximally fresh and neutralizing
Context Debt. Measured in process against the shipped `ccf.halflife.decay.freshness`:

| `valid_from` | result |
| --- | --- |
| = `now` | freshness 1 |
| 1 day past | `0.500000000000000000` — exactly one half-life |
| 10 years past | `0E-18` |
| **1 second FUTURE** | **REFUSED `TemporalOrderError`** |
| **10 years FUTURE** | **REFUSED `TemporalOrderError`** |

Plausible, confidently stated, and false. The decay path refuses a negative elapsed
(`src/ccf/halflife/decay.py::freshness`), so the consequence the finding rests on cannot occur.

## The three BLOCKING claims, all rejected

1. **codex + gemini: `AssemblyWorker`'s write surface / `ingest_admitted` admits an undeclared
   policy.** `ingest_admitted` has **zero production callers** — the `src/` matches are a
   guarded-provenance registry string (the module-level registry in `src/ccf/contracts/guarded.py`) and docstrings;
   actual callers are tests plus `archive/` (excluded, `D-IMPL-351`). `tests/crossproc/test_peering_exchange.py::test_an_admitted_product_reaches_l3_only_through_the_assembly_worker`
   already pins the caller set. Both findings rest on a caller that does not exist, which the
   GO forbade inventing. **Non-blocking.**
2. **gemini: the MCP door restamps `served_at`.** Rejected as above.
3. **`admit_relationship_claim` called directly by cp-04 and cp-05 — to a curated host?** No.
   cp-04 declares `backend: sqlite` ("the fabric's own L3, not a source") and its
   `connection(root=…)` composes a fresh per-run path under a `TemporaryDirectory`. The
   curated estate is reached only as a read-only source. **Non-blocking.**

## The finding that WAS blocking by the letter, and its ruling

**The curated-estate write fence existed only inside pytest.** Measured: the symbols
`refuse_to_write_the_curated_estate` and `CCF_CURATED_ESTATE_HOSTS` appeared in **zero** files
under `src/`, `runtime/`, `examples/`, `tools/` or the `Makefile`, while `make example-s1-01`
(permanent Fluree transactions) and `make example-s1-00` (DDL plus rows) took their write
destination from an operator-exported `CCF_TEST_*` value that `?=` lets win, with no fence on
the path. That is the accident shape that left 27 permanent `ccf:cp04-*` ledgers and 134
permanent transactions on the curated server; Fluree is append-only, so each is forever.
Pre-existing rather than Wave-2-introduced. Characterised from code; **`.76` was never
contacted.**

**Dave's ruling, 2026-10-01:** *"the curated-estate fence is NOT deliberately pytest-scoped.
'Nothing seeds .76, ever' governs. `make example-s1-00` and `make example-s1-01` must refuse a
parsed curated host before they transact. Same parser as the pytest fence: host-level, both
Postgres forms, Mongo, fail closed, no port rule."* Implemented at `tools/estate_fence.py`
with the Makefile gate; see that module and the step-15 section of the Wave 2 handoff.

## Non-blocking findings, CARRIED by ruling

| # | finding | anchor |
| --- | --- | --- |
| 1 | The only real clock detector's scope and the clock sites are **disjoint sets** — it sweeps 11 already-clock-free files; swept tree-wide it flags 10 clock-bearing modules. `tools/lints` registers 10 checkers and the string `clock` appears 0 times in it. "No `datetime.now` in the worker" is convention, not enforcement | `tests/peering/test_admission_clock.py::_ambient_clock_calls` |
| 2 | `__ccf_mode__ = "algorithmic"` is carried by 9 of the 10 clock-reading modules while the lint enforcing it only forbids LLM imports, so the marker reads as a determinism claim it does not make | `tools/lints/algorithmic.py` |
| 3 | `TemporalWriteRefused` is absent from `SDK_SEAM_REFUSALS`, so the step-8 ingress refusal escapes with **no replay record** — against audit-by-construction. Three reviewers converged independently | `src/ccf/products/resolver.py::SDK_SEAM_REFUSALS` |
| 4 | The step-8 guard governs **zero writes in the shipped example suite**: the 16 trees calling `open_product` and the 18 writing to L2 are disjoint, and `acquisition=` appears in zero example files | `src/ccf/products/product.py::OpenedProduct` |
| 5 | **Two fabric instants per serve.** `product.py::build_arguments` passes `self._clock` as `admission_clock`; `product.py::_acquisition_seam` reads the same clock again as `ingress_at`. `served_at` is still read once — accepted item 3 stands — but the write guard judges the LATER instant, so the paved-road "unreachable" claim is conditional rather than absolute | `src/ccf/products/product.py::_acquisition_seam` |
| 6 | The fence's `_normalize_host` accepts four alternate spellings of the curated address (decimal, dotted-octal, v4-mapped IPv6, trailing dot). The trailing-dot form is accident-shaped and does **not** fail closed | `tests/examples/estate_guard.py::_normalize_host` |
| 7 | The **peered-child branch of the composite resolver has never executed** — zero behavioural coverage, measured by coverage run. This is the missing Peer proof, named | `src/ccf/products/child_resolver.py` |
| 8 | `PolicyConstraintResolver`'s docstring still tells implementors to evaluate effectivity at `request.asked_at` and never documents the now-required `served_at`. Narrowed by the critic: `served_at` is a required keyword, so an omitting implementor gets a loud `TypeError`, not a silent bypass. Prose defect | `src/ccf/products/constraints.py::PolicyConstraintResolver` |
| 9 | **Found by RUNNING the new gate, not by reading it:** the fence's `_redacted` masks the URI password form (`://u:pw@`) and **not** the libpq keyword form, so a refusal on `host=… password=…` printed the credential verbatim. Masked in `tools/estate_fence.py::_scrub` for the new gate; the gap still stands for the pytest fence, whose repair was not authorised in this sitting | `tests/examples/estate_guard.py::_redacted` |

Items 1–8 are carried by Dave's ruling of 2026-10-01 (*"Those stay carried"*). Item 9 is new
and is carried on the same basis: the pytest fence's own repair was not authorised.

## Verdict

**HOLD on step 16.** No Wave-2-introduced blocker exists in the shipped tree at `9926f594`:
nothing admits an undeclared temporal policy, nothing restamps `served_at`, and no writer
path's parsed destination can be a curated host once the step-15 gate is in place. Step 16
(`D-GATE-358`) remains unstarted and needs its own GO.
