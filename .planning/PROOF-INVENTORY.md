# Proof & Verification Infrastructure — Inventory

**Purpose.** Decide whether a Phase 24.9 (Proof & Verification Infrastructure) is
warranted before cp-05 begins as Phase 25 — and if so, how small it should be.

> **Phase 24.8 closes the SDK-semantic fallout from cp-04. This inventory determines
> whether a final Phase 24 proof-hardening phase is warranted before cp-05 begins as
> Phase 25.**

**Status.** Evidence and recommendations only. Read-only work: nothing was fixed,
no utility was added, no test was rewritten, no refactor was performed. Written on
branch `proof-inventory` off `main` at `daab6233` so `main` stays at the approved
`D-GATE-24.8` state.

**Occasion.** `D-IMPL-269`, Dave, 2026-09-06, verbatim: *"When semantics are ruled
before coding, mechanism risk collapses; verification machinery becomes the higher-risk
surface."* Across 24.8's five waves roughly ten defects surfaced and **every one was in
proof machinery; none was in the mechanism.**

---

## 1. Summary of findings

| # | Pattern | Instances | Same abstraction? | Recommendation |
|---|---|---|---|---|
| P-1 | Scratch-module sabotage harness | 46 sites / 40 files | **Yes** — identical five-step shape; one site already wrote the general form | **SHARE** |
| P-2 | `no_{sabotage,control}_edits_the_real_source_tree` guard | 14 modules | **Yes** — 10 byte-identical, 3 more identical to each other under a second name | **SHARE** (with P-1) |
| P-3 | Baseline / phase-base pinning | 1 broken; 2 sound | **No** — the sound ones answer a different question | **Targeted fix, not an instrument** |
| P-4 | Citation & prose sweeps | 3 | **Already shared** where it matters | **LEAVE DUPLICATED** |
| P-5 | Lint family (`tools/lints/`) | 8 checkers, 1 runner | Already centralized | **LEAVE — this is the model** |
| P-6 | AST / surface-delta checks | ~70 files | **Not established** | **NEEDS A READ before any verdict** |
| P-7 | Roster derivation | concentrated in `tools/` | Mostly already instrumented | **LEAVE DUPLICATED** |

**The headline:** the strongest case for 24.9 is **P-1 + P-2**, which are one finding.
The carry that prompted the question — `24.8-C-03` — turns out to be a **population of
one** and does *not* by itself justify a phase.

---

## 2. P-1 — the scratch-module sabotage harness  → **SHARE**

**Where it appears.** `importlib.util.spec_from_file_location` occurs **46 times across
40 test modules**. Named helpers include
`tests/operators/test_traversal_admission.py::_import_sabotaged_categories`,
`tests/mcp/test_egress_refusal_channels.py::_scratch_egress`,
and unnamed inline forms in `tests/products/test_disclosure.py`,
`tests/agents/test_assembler.py`, and others.

**What it proves.** That a guard in shipped source is load-bearing: corrupt the guard on
a *copy*, import the copy, and show the assertion goes RED. It is the project's answer to
"a test that passes proves nothing unless it can fail."

**What it treats as authoritative.** The real source file on disk, read at test time.
The mutation is expressed as a string edit against that text.

**Are the instances the same abstraction?** **Yes — measured, not assumed.** Four
implementations were read side by side and all follow one shape:

1. read the real source (`.read_text()` / `.decode("utf-8")`)
2. apply a string mutation (`source.replace(...)`)
3. write to `tmp_path / "<name>.py"`
4. `spec_from_file_location(name, path)`
5. exec and return the module

**The strongest evidence that this is one abstraction is that the project already found
it.** `tests/mcp/test_egress_refusal_channels.py::_scratch_egress` is written generically —
`_scratch_egress(tmp_path, *, mutate: Callable[[str], str], name: str)` — parameterizing
exactly the two things that vary. It was generalized locally and never promoted.

**How it has failed in practice.**
- **24.8 plan 06:** an AST sabotage *failed to fire* because it planted only a comment.
  Caught by its own control.
- **24.8 plan 05:** a lint sabotage **masked 91 of its own failures** because the inserted
  line contained the token being searched for. The instrument reported a red for the wrong
  reason and would have passed a source review.
- **24.8 plan 02:** a sabotage was written unconditionally and could not red the instrument
  it targeted; caught at plan-check and made conditional.

These are not exotic. They are the same failure — *the sabotage did not actually corrupt
the thing under test* — and a shared harness is where a "prove the mutation changed the
source" assertion would live once instead of forty times.

**Gained by centralizing.** One place to assert the mutation actually applied (`mutated
!= source`), one place to assert the scratch copy is outside the repo tree, one place to
name the module deterministically, and a test suite for the harness itself. The three
failures above are all preventable by one guard inside a shared helper.

**Lost or obscured by centralizing.** The mutation *content* is domain-specific and must
stay at the call site — a shared harness that tried to own the mutation would hide the
very thing a reader needs to see. There is also a real risk of over-abstraction: the
40 sites differ in whether they mutate bytes or text, whether they need one scratch module
or several, and whether the module is imported once or per-parametrization. **A shared
harness must take the mutation as a callable and own only the mechanics** — which is
precisely what `_scratch_egress` already does.

**Recommendation: SHARE.** Promote the `_scratch_egress` shape to a single tested helper.
Do not rewrite the 40 call sites in one phase; migrating them is optional and can be
incremental.

---

## 3. P-2 — the "no sabotage edits the real source tree" guard  → **SHARE (with P-1)**

**Where it appears.** Fourteen modules, under **two different names**:

- `test_no_sabotage_edits_the_real_source_tree` — **10 modules**, and after whitespace and
  comment normalization **all ten hash identically** (`b5bc7078`):
  `tests/agents/test_assembler.py`, `tests/authz/test_delivery_boundary.py`,
  `tests/invariants/test_delivery_boundary_replay.py`,
  `tests/mcp/test_egress_refusal_channels.py`,
  `tests/mcp/test_experience_refusal_channels.py`, `tests/products/test_disclosure.py`,
  `tests/products/test_empty_operator_halves.py`,
  `tests/products/test_evidence_derived_debt.py`,
  `tests/products/test_policy_constraint_resolver.py`,
  `tests/products/test_policy_constraints.py`
- `test_no_control_edits_the_real_source_tree` — **4 modules**, three of which hash
  identically to each other (`5fd4000e`): `tests/products/test_refusal_envelope.py`,
  `tests/conformance/test_operator_tier_differential.py`,
  `tests/operators/test_traversal_admission.py`; the fourth,
  `tests/invariants/test_present_tense_sweep.py`, differs (`c6c8cf20`).

**What it proves.** That the sabotage machinery never wrote to the working tree.

**How it has failed in practice.** It has not failed as an assertion. **Its failure mode
is the naming split.** A grep for either spelling finds only part of the population —
10 of 14, or 4 of 14. This is the roster-derivation hazard the phase kept hitting, sitting
inside the proof estate itself: any future audit that asks "does every sabotage module
carry this guard?" will get a confident, wrong answer unless it happens to know both names.

**Gained by centralizing.** One name, one implementation, and a population that can be
enumerated correctly by a single query. This is the cheapest item in the inventory and the
one with the clearest defect.

**Lost by centralizing.** Almost nothing. The guard has no site-specific content — it is
byte-identical ten times over.

**Recommendation: SHARE, together with P-1.** They are one finding: the harness and the
guard that proves the harness behaved.

---

## 4. P-3 — baseline / phase-base pinning  → **TARGETED FIX, NOT AN INSTRUMENT**

This is `24.8-C-03`, and the evidence changes the shape of the fix.

**The population of the defect is ONE.** Exactly one module asserts "unchanged since a
pinned base": `tests/invariants/test_determination_authority_disclosure_delivery.py`
(`PHASE_BASE = "1022ad59"`, line 101; the assertion at line 467). No other module in
`tests/` or `tools/` uses `git diff --quiet <pinned-base>` as a permanence claim. It is
gating — carries no skip or xfail mark.

**The better storage convention already exists, twice, and predates the defect.**
`tools/docs_tests/test_requirement_ledger.py` and
`tests/examples/test_cp_04_phase_record.py` both externalize the base into a committed
`NN-BASE-COMMIT.txt`, with an `UNRESOLVABLE_BASE` sentinel and validation that the value
is a full 40-character SHA. The Phase 21 docstring states the reasoning explicitly:
*"Pinned in a file rather than resolved at close time from a branch name, because a base
that does not resolve makes an 'is empty' assertion vacuous rather than failing it"* and
*"a bare SHA in the source has nowhere to put the paragraph."* That module further
validates the pin is resolvable, an ancestor of HEAD, and a **strict descendant** of the
base — *"because a ceiling at or before the base makes the window empty and every
assertion built on it vacuously green forever."*

**But moving the constant would not fix this defect.** Read the failing test's own
docstring and the real problem is **lifetime, not storage**:

- Its scope is named in its module docstring: *"`24.6-11` Task 2; criterion 27."*
- Its claim is a **phase-scoped fence** — "24.6 must not edit `CLAUDE.md`, because the
  revision is Dave's to order."
- Its author chose whole-file identity *deliberately*: *"A diff against the phase base
  says both, and says them about the whole file rather than about the lists — which is
  stronger and is what the criterion asks for."*

That reasoning is correct **inside 24.6's window** and wrong the moment the window closes.
A whole-file identity claim against a living governance document has no expiry. The trigger
proves it: `CLAUDE.md` last moved at `4683f245` — **24.6's own close commit**. The fence
was violated by the very phase it was fencing, at the moment that phase ended.

**So the defect is a category error about lifetime:** a phase-scoped fence encoded as an
unconditional standing invariant, against a document expected to change under normal
governance. Dave's lesson names it exactly — *"if the thing being pinned is legitimately
mutable project governance, a raw constant may be the wrong proof mechanism."*

**Three candidate fixes**, for a ruling rather than my choice:

1. **Retire it.** The fence's phase is over and its work is done. Cheapest; leaves nothing
   guarding `CLAUDE.md` against an unintended edit — which may be correct, since no other
   document carries such a guard.
2. **Narrow the claim** to what criterion 27 actually cared about — that the invariant
   lists gained `D-IMPL-254` only when Dave ordered it — so the assertion survives
   unrelated `CLAUDE.md` edits. Preserves intent; costs a more careful assertion.
3. **Give phase-scoped fences an explicit expiry**, so an assertion true only inside a
   phase retires at its gate instead of outliving it.

Option 3 is the only one that generalizes — but **on the evidence there is nothing to
generalize to**: the population is one. Adopting it would be building a mechanism for a
class with a single member.

**Gained by centralizing.** Little, at a population of one.
**Lost by centralizing.** Real risk of inventing a "fence lifetime" framework that the
tree does not need — the exact over-verification the lesson warns against.

**Recommendation: TARGETED FIX.** Choose option 1 or 2, apply it once, and record the
lesson in prose rather than in machinery. **This carry alone does not justify a phase.**

---

## 5. P-4 — citation and prose sweeps  → **LEAVE DUPLICATED**

**Where it appears.** `tests/invariants/test_citation_coverage.py`,
`tests/invariants/test_present_tense_sweep.py`, `tools/retirement_sweep.py`, and the
underlying `tools/lints/citations.py`.

**This one reversed my expectation, and the measurement is why.** These look like three
tree-walkers doing the same thing. They are not:

- `test_citation_coverage.py` **imports from `tools.lints.citations`** — it does not
  reimplement the scan. It is a *coverage ratchet layered on the existing lint*, asking a
  different question (how many citations the checker declines to check) from the lint
  (do the anchored ones resolve).
- `tools/retirement_sweep.py` **imports from `tools.lints`** and reuses
  `tools.publish_scan.SKIP_DIRS`.
- `test_present_tense_sweep.py` rolls its own `rglob`, but over **example rung
  directories** — a different subject with different inclusion rules.

**Are the instances the same abstraction? No.** Two of the three already share the parts
worth sharing, and the third has a genuinely different subject. This is the case where
apparent repetition is one abstraction firing at different layers, and consolidating it
would obscure rather than clarify.

**Recommendation: LEAVE DUPLICATED.** Recommending consolidation here would be wrong.

---

## 6. P-5 — the lint family  → **LEAVE. It is the model.**

`tools/lints/` holds eight checkers (`algorithmic`, `backend_imports`, `citations`,
`harness_imports`, `hash_transparent_key`, `no_hardcoding`, `orchestration_imports`,
`substrate_names`) behind one runner (`__main__.py`), with one exit code, a shared
`allowlist.yaml`, a committed base roster, a shared `format_finding`, and its own test
suite at `tools/lints/tests/`.

**This is the existence proof that consolidation works in this repo** — and the standard
any shared proof instrument from P-1/P-2 should be held to: one runner, one signal, its
own tests. It also means 24.9, if it happens, has a template rather than a design problem.

**Recommendation: LEAVE UNCHANGED.** Cite it as the target shape.

---

## 7. P-6 — AST / surface-delta checks  → **NEEDS A READ BEFORE ANY VERDICT**

`ast` is used in roughly 70 files across `tests/` and `tools/`. I did **not** establish
whether these are one abstraction, and I am not going to guess.

What is visible without that read: the uses are heterogeneous in *question* — import-graph
checks (`harness_imports`, `backend_imports`, `src_does_not_import_runtime`), call-shape
checks (`test_gate_two_call_shape`), definition-delta checks (24.8 plan 06's 29-definition
comparison), and docstring/prose extraction (`publish_scan`). Those are different questions
over the same parser, which is the P-4 shape, not the P-1 shape.

**Recommendation: NEEDS A READ.** If 24.9 happens, inventorying this is a task *inside* it,
not a precondition. If 24.9 does not happen, this stays unmeasured — which is an acceptable
outcome, because nothing here has failed in practice.

---

## 8. P-7 — roster derivation  → **LEAVE DUPLICATED**

Roster and set-comparison work is concentrated in `tools/check_product_gates.py` and
`tools/retirement_sweep.py`, each of which already has a dedicated test suite
(`tools/product_gates_tests/`, `tools/docs_tests/test_retirement_sweep.py`).

The roster failures this phase suffered were **not** in that instrumented code. They were
in *ad hoc* rosters built inside plans and briefs: the postgres/fluree 49-id overlap that
would have manufactured 46 false regressions, the citation census correct for one tree and
briefed against another, and the two-name guard split at P-2. Those are **process failures
in how a roster is specified and handed on**, not missing library code — and no shared
utility would have caught any of them.

**Recommendation: LEAVE DUPLICATED.** The lesson here is procedural (state the conditions a
number was measured under whenever it crosses an agent boundary), not structural. Building
a "roster utility" would answer a question nobody failed at.

---

## 9. The carries — belongs / does not belong

| Carry | Verdict | Reason |
|---|---|---|
| **`24.8-C-03`** — the `CLAUDE.md` `PHASE_BASE` pin | **BELONGS** — but see below | Squarely proof machinery, inside the natural fence (`tests/invariants/`, no `src/`). It is the phase's anchor item. **However its population is one**, so it is a targeted fix, not an instrument programme. |
| **`24.8-C-02`** — stale `protocols.py` module-docstring version claim | **DOES NOT BELONG** | Two independent reasons. (i) *Subject:* it is a documentation / API-surface accuracy claim about the SDK's public contracts — not a statement about how we prove anything. (ii) *Fence:* fixing it requires editing `src/ccf/graph/protocols.py`, which the proposed 24.9 fence closes by default. Admitting it would either breach the fence or force the fence open for one docstring. It should wait for the next phase that legitimately owns that module. |
| **`24.8-C-01`** — unresolved-reference observability | **DOES NOT BELONG** | It is an SDK *feature* deferred by design ruling (`D-IMPL-267`), constrained by 24.8's criteria 9 and 20 which require exclusion to stay silent and forbid partial implementation. It is not proof machinery in any sense. Admitting it would make 24.9 a generic debt bucket, which Dave explicitly ruled out. |

---

## 10. Does 24.9 deserve to exist?

**The case for.** P-1 and P-2 are a real, measured population: one abstraction rebuilt
across 40 modules, with a companion guard duplicated 14 times under two names and three
implementations. Three distinct sabotage failures in 24.8 alone are of the kind a shared,
tested harness would have prevented — most sharply plan 05's sabotage that masked 91 of its
own failures. The naming split in P-2 is actively producing wrong answers to roster
questions *inside the proof estate*. And `tools/lints/` proves consolidation succeeds here.

**The case against, stated honestly.** `24.8-C-03` — the carry that prompted the question —
is a population of **one**, and the better storage convention already exists twice, so it
needs a fix, not a phase. P-4, P-5 and P-7 all came back **leave alone**, two of them
against my initial expectation. P-6 is unmeasured. So of seven patterns examined, **one
finding (P-1 + P-2) carries the phase**, and it would be honest to say the phase is that
one finding plus a one-line fix.

**The risk specific to this phase.** 24.9 would be a phase whose entire subject is
verification machinery, undertaken because verification machinery is where defects land.
Every instrument it builds is itself novel proof code — the highest-risk category this
project has. A 24.9 that ships a shared harness plus its own test suite is squarely
Dave's *"a smaller number of proof instruments, simple, reusable, and themselves testable."*
A 24.9 that inventories all 70 AST sites and designs a fence-lifetime framework is the
proof-of-proof tail the panel ruling declined.

**My recommendation.** A 24.9 is warranted, but only at roughly this size:

1. Fix `24.8-C-03` — one module, option 1 or 2 above, by ruling.
2. Promote the `_scratch_egress` shape to one tested sabotage harness, with the
   "the mutation actually applied" guard the three 24.8 failures needed.
3. Unify the P-2 guard under one name and one implementation, and enumerate the full
   14-module population once so the naming split cannot recur.
4. Migrate call sites **only opportunistically**. Do not rewrite 40 modules.

Explicitly out: P-4, P-5, P-7, `24.8-C-02`, `24.8-C-01`, and any new framework. P-6 is a
task inside the phase if it is cheap, and dropped if it is not.

If that is too small to be a phase, the alternative is defensible: do items 1–3 as a
tooling chore off `main`, and open **Phase 25 — cp-05** directly.

---

## 11. What this inventory did not measure

Stated so nothing here is mistaken for a complete audit.

- **P-6 (AST / surface-delta, ~70 files)** — not read. No verdict offered.
- **The 235 `test_control_*` / `test_the_control_*` tests** — counted, not classified.
  Whether they are a coherent family or an incidental naming convention is unmeasured.
- **`tests/` outside the sabotage and baseline families** — roughly 6,957 lines in
  `tests/invariants/` alone were surveyed by structure, not read.
- **24.7's proof machinery specifically** — its findings were taken from the phase records
  rather than re-derived from its test modules.
- **Whether any shared harness would actually have caught each of the three 24.8 sabotage
  failures** — argued from the failure descriptions, not demonstrated by construction.
  If 24.9 happens, that demonstration is the first thing worth doing, because it is the
  claim the phase rests on.
