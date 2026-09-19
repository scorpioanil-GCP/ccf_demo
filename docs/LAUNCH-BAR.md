# Launch bar

**Behavioral baseline: `dc7e8177`** (`main`, post-`D-GATE-341`). `D-IMPL-304`, `D-IMPL-342`
and `D-IMPL-341` are closed; nothing here reopens them. This page decides what remains
*necessary* for launch. It builds nothing and runs nothing.

**Decided 2026-09-19** (the *Decided* column below; the rulings are recorded in
`docs/DECISIONS.md` under *LAUNCH SCOPE*). The bounded finish line is: finalize the supported
launch documentation → qualify one fixed release candidate → resolve or explicitly disposition
every failure → make the release decision. No additional SDK feature phase is authorized.

## The release objective

> Developers can publish, acquire, compose, and reconstruct governed Context Products through
> supported SDK interfaces with reasonable effort. Completing the full credit-memo application
> is not required.

Three distinctions govern every row below. **Optional example enrichment** is not an **SDK
guarantee still needing proof**. **Missing test coverage** is not **demonstrated incorrect
behavior**. And **a completed repair phase** is not **overall release readiness**: three phases
closed cleanly on `dc7e8177`, and that establishes the baseline's behavior, not the release's.
No item is marked deferrable merely because no current example triggers it; each is judged
against whether the supported contract above permits the condition.

## The table

| Remaining item | Proposed launch classification | Consequence for the supported SDK contract | Existing evidence / gap | Minimum action before tag | Decided |
|---|---|---|---|---|---|
| **Replay-environment friction** — a paved producer's replay proof is assembled by hand (`CP06C-F-01`; `D-GATE-342` residual 2) | **SDK guarantee needing proof of effort, not of correctness.** Reconstruction works; the objective's "reasonable effort" is the open question | "Reconstruct" is in the objective. Today it needs ~40 lines per producer: parse dimension 2's `request_resolution`, rebuild the operator registry through a private `_operator_parameters`, and restate the envelope — including `ttl_anchor_at`, which three environments omitted until told (design `D-IMPL-341` §12.7) | Four hand-built environments pass (cp-06-canonical, cp-13-canonical, CP-14 slice 4, the 341 suite's own). Gap: no supported seam; the recipe lives only in test files | **Ruling:** either a documented, supported reconstruction recipe with one adopter-facing example, or an explicit statement that replay proof is producer-side work at launch. Building a paved environment is a phase, not a tag prerequisite | **Ship a documented recipe and one adopter-facing example on the existing engine — no new seam.** Done: `public/how-to/reconstruct-a-governed-determination.md` over `examples/replay-a-governed-determination/replay.py`, run on both paths; the one private dependency is named |
| **`CP14-F-33` — exposure has no paved seam**; the low road is the escape hatch | **SDK guarantee needing a decision, not a repair.** "Publish … through supported interfaces" is met by the low road; the paved road cannot carry a post-traversal deterministic aggregation | Every producer with an aggregation between traversal and Π leaves the paved road for its whole spine (`D-IMPL-343` §C step 2 open). The supported contract is honest only if the low road is named as supported at launch | cp-05 serves through the low road and its door; CP-14 admits it as a child. Gap: the paved road's vocabulary has no home for L4 aggregation, and no ruling says which road is "supported" for that shape | **Ruling:** name both roads as supported at launch, with the paved road's exclusion stated in the adoption page, or hold the tag for a paved seam (a design cycle). Do not tag with the exclusion unstated | **Both routes supported.** The paved facade does not cover post-traversal aggregation; the supported path for that shape is lower-level governed assembly plus the standard door. No new paved seam before tag. Ordinary faults stay faults; `GovernedRefusalRaised` is the only handoff. Stated on the adoption page |
| **Covenant dual-TTL** (`CIF-G15`) — declared, deliberately unimplemented | **Optional example behavior, not an SDK guarantee.** Where "closed" ends and "live" begins is an operator's policy | None on the SDK: the TTL mechanism is proven elsewhere (`D-GATE-341`). The gate would give a closed as-of answer a longer window than a live one; its absence leaves cp-08's demonstration expiring at the wall clock, which its suite handles by asking on the booking day | `CP-SPEC-008` §G.3 records it as specified-not-built; the roster excludes it; `D-GATE-341` residual 6 carries it | **None before tag.** Keep it declared and unimplemented; it is not an SDK shortfall | **Out of launch scope.** Not presented as implemented |
| **Recorded residuals of 304 / 342 / 341** | **Mixed — see the split at right.** None is demonstrated incorrect behavior; all are recorded | *Coverage, not defects:* 342-1 (no cross-process malformed-door control), 342-2 (served-path question hold proven by tamper only), 341-4 (no test for a child-bound composite floor), 341-5 (unpinnable-clock guard has no reachable configuration). *Design limits under the contract:* 341-1 (scorer reduces at the view instant, anchor at the decision instant — divergent only for a class combining an evidence anchor with a decision-instant parameter; none shipped), 341-2 (replay's declared basis comes from the rehydrated declaration, not a pinned one), 341-3 (refusal records pin no half-life table). *Scope by ruling:* 342-3 (the legacy argument-bound child leg retains no question). *Demonstrated behavior, ruled out of scope:* 304 — on cp-05's low road a request-contract type mismatch is raised as an exception and reaches the door as a runtime failure, with no governed envelope and **no replay record**, because that road resolves the effective request before acquisition (`docs/D-IMPL-304-DESIGN.md`); acquisition ordering was ruled out of that migration's scope | `D-GATE-342` and `D-GATE-341` name each with its reason; two independent reviews confirmed the 341 set. Gap: 341-1 and 341-2 are conditions the supported contract *permits today only because nothing exercises them* — that is the one place this page must not wave a residual through | **Before tag:** state 341-1 and 341-2 as documented limitations of the replay/anchor contract in the adoption page (a sentence each), or rule them worth a control. The coverage items are backlog. 342-3 needs no action. 304 folds into decision 1: if the low road is a supported road at launch, its unrecorded pre-acquisition refusal must be stated as a limitation of that road | **Carried explicitly, no new controls.** All five 341 limitations and the 304 route limitation are stated on the adoption page as limitations; no existing evidence demonstrates a shipped-class divergence |
| **Seventeen unclaimed CP-14 gates** (`CP14-F-37`: 29 declared, 12 executing; reconciled by unique id — the finding had named sixteen and omitted `G04`) | **Split by the finding's own two kinds.** Seven are *optional memo enrichment* (`G05`, `G08`–`G12`, `G14`). **Ten** are *governed behavior not yet under test through CP-14* (`G01`, `G04`, `G06`, `G07`, `G13`, `G15`, `G16`, `G21`, `G24`, `G25`) | The objective excludes the full credit-memo application, so the enrichment seven have **no** consequence. The governed ten are SDK claims made through this consumer and are "missing coverage", not "demonstrated wrong". Per gate (`CP14-F-37`): five rest fully on SDK-level controls (`G01`, `G06`, `G13`, `G21`, `G15` in-process); two on example-level gates outside CP-14 (`G16`, `G15` cross-process); three are partial — the SDK mechanism is controlled, the CP-14-specific claim is not (`G04`, `G07`, `G25`); one has no SDK control at all (`G24`, the consumer's own projection guard) | Roster declares only the twelve executed; FINDINGS names all seventeen with the control behind each governed claim and none marked passed. The sixteen-versus-seventeen gap is closed: `G04` was the unnamed one, and it is governed | **Ruling:** confirm the enrichment seven are out of the launch bar. For the governed ten, decide whether the SDK-level controls already carrying each claim are the launch evidence or whether CP-14 must exercise them | **Enrichment seven are outside the launch objective. The governed claims rely on their existing SDK-level controls; no further implementation inside CP-14.** Applied to ten, not nine: the partial and uncovered halves (`G04`, `G07`, `G25`, `G24`) are exposed as CP-14 obligations open with the memo specification, which remains open |
| **Standing test failures** — three different epistemic states, kept apart | **Release-readiness question, not a repair-phase question** | A release cannot ship with an unexplained red or an unrun suite. The objective says nothing about which; the qualification step below does | *Observed at `dc7e8177`:* one failure, `tests/deployment/test_class_lookup.py::test_the_phases_fragments_claim_exactly_what_was_added` — a **fragment-claims** assertion, red at the merge base `f8c33898` too. *Recorded separately, not verified here by node id:* earlier closes cite "1 `test_class_lookup`"; whether that is the same fragment-claims assertion or a second, class-lookup failure was not established at `dc7e8177` and is not inferred. *Not rerun at `dc7e8177`:* `tests/http_api` (8 recorded red), `tests/test_surface_*` (4), `tools/lints/tests/test_runner.py` (3), `tests/invariants/test_no_obligation_vocabulary.py` (42), peering (1), the CLI suite, and every example tree outside the six producers and four memo slices that the 341 close ran. Their state at this baseline is **unknown**, not green and not red | **Before tag, no exceptions:** the full applicable run on a fixed candidate; every red dispositioned by node id as fixed, carried with a reason, or a stale instrument; every suite that could not execute named with why. The `make gate-tools` stop-at-first-failure trap (CLAUDE.md §3.1) means legs are run directly | **No tag with unexplained failures or unrun applicable suites.** One fixed candidate; a disposition for every failure by exact test identity. **Named-unexecutable records missing validation; it does not clear a required launch check** |

## What was decided, and what remains

The five decisions above are ruled (the *Decided* column). What remains is not a decision but a
step: the qualification checkpoint, separately authorized.

One ruling was applied to a corrected count. The finding's "nine governed" undercounted by one;
the omitted gate is governed, and the ruling — rely on existing SDK-level controls, no further
implementation inside CP-14 — is applied to ten. Where a gate's CP-14-specific half has no
control it is exposed in `CP14-F-37` rather than marked covered; those halves are CP-14
obligations, open with the memo specification, and not SDK launch checks.

## The qualification checkpoint — prepared, not executed

The separately authorized qualification run covers **one immutable candidate** — one SHA, no
further behavioral commits — and classifies **every result by node id**. The rules it runs under:

- **A failure requires either a fix or an explicitly accepted expected-failure disposition.**
  Neither is inferred from an earlier record.
- **An unavailable environment is recorded as *not executed*, never as green.** Named-unexecutable
  records missing validation; it does not automatically clear a required launch check.
- **A required launch check needs execution or an explicit scope decision before tagging.** There
  is no third state.
- **Reconcile fragment-claims and class-lookup first.** The observed failure is a fragment-claims
  assertion in the class-lookup module; whether an earlier "class-lookup" mention is the same node
  id or a second failure is established at the start of qualification, and neither is
  pre-classified as harmless because it predates these repairs.
- **Legs run directly**, never through a composed target that stops at its first red; the estate
  suites run against `.76`, reading only.

A green scoped package on `dc7e8177` is the baseline for that step, not a substitute for it.
