# Qualification investigation — the 46 deferred nodes on `main @ eef849cc`

**Baseline:** `main @ eef849cc` (the first correction group merged; not revisited). **Rule recorded first:**
the one-shot attribution rule, `docs/DECISIONS.md` *RELEASE-QUALIFICATION RULE* (`078de397`).
**Population:** the 45 deferred nodes of `docs/QUALIFICATION-f0656746.md` plus the order-dependent
CP-14 node found at the merge qualification — 46, listed by exact id in the appendix.
**Scope of this pass:** investigation and disposition proposal only. No repair, no expected-failure
mark, no collection-order change, no process isolation, no product-behavior change.

Date: 2026-09-19.

---

## 1. Disposition table

| Root cause | Nodes | Intended invariant | Finding | Proposed disposition | Behavioral change? |
|---|---:|---|---|---|---|
| A — the no-obligation-vocabulary guard's exemption roster was not updated when two ruled SDK-mechanism `Literal` vocabularies shipped (D-IMPL-331 `DecayBasis`, D-IMPL-333 `FreshnessAggregation`); the guard is unchanged since before them | 42 | the SDK enumerates no *obligation* vocabulary (D-IMPL-117); mechanism enumerations pass through a ruling-cited by-name roster, the guard's documented review seam | both vocabularies are ruled SDK mechanism (each member names a scorer code path), exactly the `DecayMode` precedent already in the roster; the "`_GLOB_CHARACTERS`" message is misattributed, same cause | **stale test** — two roster entries citing D-IMPL-331/333; sabotage-proven in a scratch copy (five plants red, one removal red) | none |
| B — a whole-file byte pin on CLAUDE.md at the Phase 24.6 base, red since 24.6's own close commit; already ruled a proof-machinery defect (D-IMPL-269 (2), 270 (2)); the narrowed replacement was built on `phase-24.9` and never merged | 1 | Phase 24.6 did not add the four-layer invariant to CLAUDE.md's two seven-member invariant lists | thirteen CLAUDE.md revisions since the base, all Dave-attributed and contract-preserving; both protected lists byte-identical between the base and `main` | **stale pin / proof-machinery defect (ruled)** — port the two-list roster narrowing (D-IMPL-271 (4)(5)), delete the byte pin; not a re-pin | none |
| C — the unanchored-citation ratchet's population genuinely regrew: 0 on `main` through the 24.8 gate, 86 by the candidate, all written 2026-09-09..19 in eight design/review records and three living planning/spec files; 63 already stale | 1 | prose cites `path.py::Symbol`, never a line number (D-IMPL-114); the unverifiable population stays at 0 (D-IMPL-123) | scope and ceiling match the ruling; the sessions knew the convention; the `docs/D-IMPL-*.md` record class post-dates the exemption list and is unruled as living or dated | **documentation-evidence defect** + a class ruling: convert the 11 living sites; for the 75 record sites convert or historicity-mark; class exemption rejected (loses 169 checked citations); ceiling raise rejected | none |
| D — a whole-file hash pin on `src/ccf/contracts/claims.py`, moved by D-IMPL-332's ruled `valid_from` widening (two commits), entering `main` at the cp-09 gate merge without the constant | 1 | the merged federated lineage lives in the `AdmissionRecord`, never in `LineageEntry` (D-IMPL-58 reading (d)) | `LineageEntry` byte-identical with its four fields; the change cannot reach the admission path; the reading-(a) guard sits behind the hash and has been dark since 09-12 | **stale pin** — update the constant with provenance; move the semantic assertions ahead of the hash | none |
| E — the CP-14 isolation test reads the whole process's `sys.modules`; cp-05's non-restoring test loaders leave `assembler` cached and the CP-14 fixture's pop list omits that name | 1 | CP-14 imports or reconstructs no producer material (G23) | the consumer action loaded 39 modules, none from a producer tree — the invariant holds; the instrument reads another suite's state; five sibling walks share the shape | **test-isolation defect** — an import audit scoped to the consumer action with positive controls; no reorder, no `sys.modules` deletion, no isolation | none |

---

## 2. Findings by root cause

### A — `tests/invariants/test_no_obligation_vocabulary.py` (42 nodes)

**Invariant.** `D-IMPL-117` (Dave, 2026-08-11): the SDK owes *no obligation vocabulary* — the words
that say what a debt signal obliges an operator to do (re-pull, escalate, accept supervised
synthesis) are deployment configuration, never enumerated in `src/` (CLAUDE.md §11 mechanism-not-
values, §6.4 No-Hardcoding). The guard's *predicate* is structural, by design: any closed set of
two or more string literals declared at module or class scope in `src/ccf/halflife/` or
`src/ccf/controlplane/artifacts.py`, as an Enum, a `Literal[...]` or a container. It cannot judge
meaning, so it carries a by-name roster, `EXEMPT_DECLARATIONS`, which its own comment calls *"the
review seam: a new closed set of strings in either scan root fails until someone adds it here
with a justification, which is a reviewable event rather than a silent one."* Seven SDK-mechanism
enumerations already sit in that roster with their rulings — `DecayMode` (24.5-L-22),
`ConstraintOperator` (D-IMPL-253), `RequestBindingSource` (D-IMPL-295), `DebtSignal`,
`DebtFactorName`, `ArtifactRole`, `RegistrationMode` — plus `_GLOB_CHARACTERS`.

**Finding.** Every one of the 42 nodes fails on one precondition: the tree declares an unexempted
vocabulary — `DecayBasis = Literal["observed-at", "valid-from"]` (`artifacts.py`, introduced by
`b2ba4e8b`, D-IMPL-331, 2026-09-11) and `FreshnessAggregation = Literal["series-mean",
"leading-edge"]` (`5c25048a`, D-IMPL-333, 2026-09-12). Both are named verbatim in their rulings
(`docs/DECISIONS.md` D-IMPL-331: *"`decay_basis: Literal["observed-at", "valid-from"]` … the
`decay` field's own shape"*; D-IMPL-333 spells the alias out) and each member names an SDK code
path the scorer branches on (`src/ccf/halflife/decay.py::decay_basis_of`,
`::freshness_over_of`); the deployment chooses which row takes which in its λ_c table. They are the
`DecayMode` case exactly. Neither commit ran or updated this module, so the review event the seam
exists to force never happened. The guard module itself is unchanged since `76de22ad`
(2026-09-09); applying today's guard to `artifacts.py` at each commit turns red first at
`b2ba4e8b`. The last node's message — *"the exemption stopped covering `_GLOB_CHARACTERS`"* — is
misattributed: `_GLOB_CHARACTERS` is seen and exempted; the third assertion is a whole-file
cleanliness check whose message is hard-coded, and it fails on the same two declarations. There is
no second cause. (The qualification report's §8.3 repeated that misattribution.)

**The smaller correct side.** Not (a), making the two fields opaque `str`: the scorer must still
branch on the two words, so the SDK would know them anyway, only without schema validation or a
load-time refusal of a misspelling, and no deployment can add a third `Observation` instant or a
third aggregation — D-IMPL-331 chose the typed shape for that reason. (b) is the guard's own
designed path: two entries in `EXEMPT_DECLARATIONS`, each citing its ruling, in the `DecayMode`
shape. Proven in a scratch copy: with the two entries the module is 51 passed; five planted
vocabularies (an `ObligationKind` Literal beside the exempted aliases, a signal-to-obligation
dict, a Literal field annotation, a `StrEnum` under `halflife/`, a tuple in `decay.py`) each turn
it red naming the plant; removing the `FreshnessAggregation` entry turns the real tree red naming
exactly `FreshnessAggregation (285)`. Not a broad allowlist (two names, two rulings), not an
expected-failure mark, no change to the predicate. Optional in the same edit: the third
assertion's message should say what it checks.

**Disposition:** stale test (maintenance at the guard's review seam). **Behavioral change:** none
— `src/` untouched; the measurement is restored. **Needs Dave:** confirm the two exemptions under
D-IMPL-331/333.

### B — `tests/invariants/test_determination_authority_disclosure_delivery.py::test_the_document_is_unchanged_since_the_phase_base[CLAUDE.md]` (1 node)

**Invariant.** Phase 24.6, criterion 27 (`D-IMPL-254`): the phase recorded Determination →
Authority → Disclosure → Delivery as SDK architecture in the resolver, refusal and door docstrings
and did **not** add it to CLAUDE.md's two seven-member architectural-invariant lists (the §3.1
Phase-D review bullet and the §16 bullet) — *"a revision for Dave to order."* What the phase must
prove is that it did not edit those lists. The module chose to prove it by pinning the **whole
file** at the phase base `1022ad59` (`PHASE_BASE`, `UNEDITED` at lines 101 and 106, a
`git diff --quiet` byte check), which its own docstring calls "stronger". That choice is the
defect: CLAUDE.md is Dave's charter and he revises it by no plan (§2).

**Finding.** The pin has been red since `4683f245` — Phase 24.6's **own close commit** (D-GATE-24.6,
2026-09-05, thirty-three lines added to §9). Thirteen commits have touched CLAUDE.md since the
base; every hunk sits in §9 (the examples charter, the estate rules, the illustrative-calibration
ruling `D-IMPL-323`, the "examples are probes" rule `D-IMPL-261`, the standing facts corrected by
`D-IMPL-330`), the §3.1 "green target is not evidence" block, the top-of-file loader note, and a
§11 insertion (vault exchange) — each commit message attributing the text to Dave's instruction or
to a ruling. Measured: the §16 architectural-invariant bullet and the §3.1 Phase-D bullet are
byte-identical between `1022ad59` and `main`; `D-IMPL-254` appears in CLAUDE.md at neither
revision; no `## N.` heading changed. **Every hunk is contract-preserving; the protected lists
never moved.** The pin fails on authorized revisions, exactly as a whole-file pin on a living
charter must.

**Already ruled.** `D-IMPL-269 (2)` (Dave): *"a defect in proof machinery created by 24.6 … carry it
by id [24.8-C-03] … not accepted as a permanent standing red."* `D-IMPL-270 (2)`: narrow the
claim; no fence-expiry framework. `D-IMPL-271 (4)(5)`: *"Narrow the CLAUDE.md pin to the two
seven-member architectural-invariant lists … detect addition, removal, duplication, or
substitution of an invariant, not whitespace"* and the same for the whitepaper sibling — recorded
only on `phase-24.9`'s copy of the decision log (`main` reserves the id). The narrowed instrument
was **built on `phase-24.9`** (`4d3b927c` the roster, `899255a1` deleting the byte pin, `f5fc1910`
the whitepaper sibling) and never merged: `D-IMPL-276` left that branch suspended and ungated. Its
roster, driven against today's CLAUDE.md in a scratch harness with the branch-only `tools.proof`
imports stubbed, is green on both lists; planting the four-layer arrow inside §16 turns it red
naming the addition; re-wrapping a line leaves it green.

**Smallest correct repair.** Not a re-pin (`"1022ad59"` → `"da531a49"` is one line, but it is the
raw-constant shape D-IMPL-269/270 rejected and it goes red again at Dave's next revision). Port the
ruled narrowing: the two-list roster with its anchors (no `tools.proof` dependency needed; the
sabotage controls can plant with `str.replace`), delete `PHASE_BASE`/`UNEDITED` and the byte-pin
test with its scratch-repository control, and narrow the whitepaper leg the same way so the
sibling does not carry the same lifetime bug. Provenance: `4683f245 … da531a49`; rulings
`D-IMPL-269 (2)`, `270 (2)`, `271 (4)(5)`.

**Disposition:** stale pin / proof-machinery defect (ruled). **Behavioral change:** none — the
test reads git and CLAUDE.md only. **Needs Dave:** (i) lift 24.9 plan-08's narrowing from the
suspended branch or re-implement it by hand on the repair branch; (ii) record `D-IMPL-271 (4)(5)`
on `main`'s decision log; (iii) narrow the whitepaper sibling now or leave it as the green byte
pin it is.

### C — `tests/invariants/test_citation_coverage.py::test_the_unanchored_python_citation_population_cannot_regrow` (1 node)

**Invariant.** `D-IMPL-114` (2026-08-11): prose cites `path.py::Symbol`, never a line number, because
a line anchor *"encodes a fact with a shorter half-life than the claim."* `D-IMPL-123`
(2026-08-12): the population of line-anchored `.py` citations that the citation checker declines
to verify for want of a quoted anchor is a coverage ratchet with ceiling **0** (set by plan
15.6-11 after sweeping the 100 that existed; `MAXIMUM_UNANCHORED_PY_CITATIONS = 0` since
`648eebfd`, 2026-08-13). The gate itself is green: unanchored sites are counted, not reported.
The ratchet applies the checker's own exemptions (`HISTORICAL_RECORDS`: the decision log, the
whitepaper, `docs/PHASE_*.md`, `.planning/phases/*`) and holds back the fragments the ruling named
(14, and the boundary test passes). Scope and constant match the ruling exactly; the instrument
is not stale.

**Finding — the population genuinely regrew.** Running the test's own population function on
extracted trees: **0** at every `main` gate through `daab6233` (D-GATE-24.8, 2026-09-06);
**1** at the 24.10/24.11 merge (`STATE.md`, 09-09); 10 after the example-modernization merge (the
`EXAMPLE-MODERNIZATION-LEDGER`); 20 after `D-GATE-337`; 80 after the CP-14 slice merge; **86 at
the qualification candidate**. All 86 were written 2026-09-09 to 09-19, and no source file,
test, tool or published page hosts one:

| host | sites | class |
|---|---:|---|
| `docs/D-IMPL-343-DESIGN.md` | 49 | design record |
| `docs/D-IMPL-304-DESIGN.md` | 11 | design record |
| `.planning/EXAMPLE-MODERNIZATION-LEDGER.md` | 8 | living planning record |
| `docs/D-IMPL-336-PANEL-REVIEW.md`, `-COMPLETION.md`, `-REMEDIATION-DISPOSITION.md` | 4 + 3 + 3 | review records |
| `docs/D-IMPL-340-DESIGN.md`, `D-IMPL-344-DESIGN.md`, `D-IMPL-341-DESIGN.md` | 2 + 2 + 1 | design records |
| `.planning/STATE.md` | 2 | living |
| `examples/cp-14-credit-memo-context/spec/CP-SPEC-014_…md` | 1 | specification |

**They are already rotting:** 63 of the 86 cite a line whose content has moved since the citing
commit (the 343 design cites line 1813 of `resolver.py` as `refuse_intent`; today that line is a
docstring fragment; the 304 design cites line 742 of `egress.py` as `_opaque_failure`; today it is blank).
The sessions knew the convention: the 341 design lists "the invariants citation ratchet" among
standing reds it left identical, and the 304 session converted one 343 citation to `::Symbol`
the same day its own design added eleven line citations. None of the 304/336/337/340/343/344
entries or gates mentions the ratchet.

**The class question underneath.** `HISTORICAL_RECORDS` was last edited 2026-08-06; the
`docs/D-IMPL-*.md` design-record class first appeared 2026-09-12 and now holds 13 files, 8 of
them offending. Those records pin a baseline SHA in their header ("every line reference below is
at that SHA") yet are edited in place afterwards (the 343 design six times, the 341 design seven),
so they fail the checker's own membership test for a dated record ("a file that may not be edited
to correct a citation"). Whether they are living documents under D-IMPL-114 or dated records is
unruled.

**Options, measured** (none changes SDK or product behavior; the requirement is not weakened by
any of the three proposed): **A** convert all 86 to `path.py::Symbol` — 70 sit inside a symbol
today; the 16 that do not (a blank or moved line, an import, a comment, a range wider than one
symbol) re-resolve from the citing commit, or fall back to a bare path as 15.6-11 did — population
0, 86 edits in 11 files. **B** add `docs/D-IMPL-*.md` to `HISTORICAL_RECORDS` — rejected: it
removes 83 unanchored sites at the cost of **169 currently checked `::Symbol` citations** in those
13 files (the 342 design alone: 66 of 66 verified today), a net loss of coverage, and the class
fails the dated-record test by practice. **C** split: convert the 11 living sites (LEDGER, STATE,
the CP-14 spec — the D-IMPL-123 precedent swept STATE.md as living) and, for the 75 design-record
sites, either convert (A) or mark each citing sentence with the checker's own historicity marker
(`at \`<sha>\``), which moves them to `historical` with no policy change and keeps the 169
checked. **D** raise the ceiling to 86 — the blind pin update the ruling refused; not proposed.
Adjacent and out of scope: the same files hold roughly 170 line-anchored `.py` citations in total
(57 dropped from the population only as ambiguous basenames); fixing the 86 does not fix those.

**Disposition:** documentation-evidence defect (86 citations against D-IMPL-114, 63 stale),
plus an accepted-limitation-needs-ruling on the design-record class. **Behavioral change:** none.
**Needs Dave:** (1) living or dated for `docs/D-IMPL-*.md` (→ convert 75, or historicity markers,
or the class exemption at its stated cost); (2) confirm the 11 living sites are converted; (3)
for the 16 sites with no covering symbol, re-resolve at the citing SHA or bare path.

### D — `tests/peering/test_admission_record.py` `::test_claims_py_is_unchanged_so_reading_a_cannot_creep_back_in` (1 node)

**Invariant.** `D-IMPL-58` (Dave, 2026-07-27), reading (d): the merged federated lineage of an
admitted peered product lives in an immutable `AdmissionRecord` at the admission boundary; reading
(a) — extending the graph's `LineageEntry` with the federated axes — must not creep back. The test
pins `src/ccf/contracts/claims.py` by whole-file sha256 (note: that path, not a peering module),
and its docstring pre-authorizes the benign case: *"either the change is unrelated and the
constant is updated in the same commit that justifies it, or reading (a) is creeping in."*

**Finding.** The pinned hash `70a3e8a2…` is the file at `78db8885` (2026-07-25). Exactly two
commits touched it since, both D-IMPL-332 (`59cfc0cd`, `da14c544`, 2026-09-11): `_TemporalClaim.valid_from`
widened from `datetime` to `datetime | None = None` and made hash-transparent, with a docstring
explaining the absence limb — named verbatim in the ruling (*"`_TemporalClaim.valid_from` widens
to `datetime | None = None`, hash-transparent"*) and in `docs/surface-changes/332-01-…`.
`LineageEntry` is byte-identical across all three versions and still has exactly its four fields
(`source`, `envelope_id`, `observed_at`, `passage_anchor`); no claim kind was added. On the peering
admission path `valid_from` is always populated (`AssemblyWorker.ingest_admitted` passes the
product's non-optional `temporal_boundary`), so the change cannot reach admission semantics. The
red entered `main` at `0d19599f` (the D-GATE-cp-09 merge), which recorded only the invariants reds;
the docstring's *"update the constant in the same commit"* was not followed. The qualification
report attributed this node to "the 341 closes"; the measured cause is D-IMPL-332 via that merge.

**Coverage gap, named.** The only assertions that exclude reading (a) are the ones after the hash
check inside this same test; with the hash red first, the D-IMPL-58 guard has been dark since
2026-09-12. No other test asserts `LineageEntry`'s field set. `tests/peering` with the pin
deselected: 98 passed.

**Smallest correct repair.** Update the constant to `58f97ac2…` with a provenance comment naming
`da14c544`, D-IMPL-332 and the fragment, and move the reading-(a) assertions ahead of the hash so
a future benign edit goes red on the hash while the semantic guard still executes.
**Disposition:** stale pin. **Behavioral change:** none. **Needs Dave:** none for the constant
(pre-authorized by the test's own docstring, the change being his closed D-IMPL-332); one question
whether to narrow the instrument from a whole-file pin to a `LineageEntry`-shape pin, since the
whole-file form goes red on every ruled edit to the claim classes.

### E — `tests/examples/test_cp_14_fourth_slice.py::test_the_consumer_imports_no_producer_and_rebuilds_no_child_material` (1 node)

**Invariant.** CP-14 itself must not import or reconstruct producer implementation material
(CP14 gate G23). The test has two halves: a source scan of the five CP-14 files for eleven
SDK-composition tokens and child-owned tables (order-independent, reads files), and a walk over
**every entry of the global `sys.modules`** asserting no module's origin lies under any of the six
producer trees (lines 701–704). The walk has no notion of *who* imported a module or *when*; it
measures process-global state accumulated by every earlier test in the session.

**Finding — test-isolation defect, not a consumer defect.** Measured attributably with a scratch
hook around the fixtures, in the failing order (the cp-05 output suite first): the CP-14 consumer
action (`produce.product` + three `opened.answer` calls with five producer doors live as
subprocesses) loaded **39 new modules, none under any producer tree** — all `httpx`/`httpcore`/
`h11`/`h2`/`trio` pulled lazily by the SDK's MCP client transport, plus two from pytest's tmpdir;
no `find_spec` request for `assembler`, `produce`, `deployment` or any producer-shaped name. The
module the walk finds, `examples/cp-05-credit-exposure-rollup/assembler.py`, was imported by
`tests/examples/test_cp_05_output.py` a minute earlier: cp-05's two frozen-specimen test loaders
insert their root at `sys.path[0]` and pop stale names but **never restore either** (lines 54–63;
`test_cp_05_mcp_door.py` 73–86), while every other example suite measured (cp-03c, cp-04c, cp-06c,
cp-13c, the exposure door, the spine tests) leaves nothing behind. The CP-14 `modules` fixture
(`test_cp_14_first_slice.py`, the `modules` fixture) swaps `acquisition`, `deployment`, `produce` and `projection` for
its own for the module's duration, so only a name **outside that pop list** can survive into the
walk — and `assembler` is the one. Confirmed by order: after `test_cp_05_mcp_door.py` (which leaks
only `deployment`) the node passes; after `test_cp_05_output.py` it fails on `assembler`.
Pass/fail is an accident of a four-name pop list. No shadowing occurred: cp-14 imports only its
own three modules and `ccf.*`, and nothing requested `assembler`; but a future `import assembler`
in cp-14 would silently bind cp-05's cached module — a latent hazard the proposed audit catches.

**Smallest correct repair (test module only).** Replace the global walk with an import audit
active only during the consumer action: record every import statement through `builtins.__import__`
(fires for cached modules too, which a key diff would miss) and every module newly loaded or
replaced under the same name (identity diff of `sys.modules`), stash the audit in the `both`
fixture's result, and assert no recorded origin lies under a producer tree. Positive controls
built in scratch with cp-05's `assembler` pre-cached exactly as the failing order leaves it (4
passed, no estate): a consumer importing only non-producer modules passes where the old walk
tripped; `import assembler` hitting the cache is caught; `importlib.import_module` from a producer
root is caught; pop-and-reimport under the same name is caught. **No positive control exists in
the module today** — G23's declared sabotage exercises the source-scan half only. Rejected, as
ruled: reordering tests (hides, does not measure), deleting `sys.modules` entries (destroys
another suite's state and passes for the wrong reason), xdist/fork isolation and resetting global
state (make the assertion vacuous).

**Same shape elsewhere, green by luck:** five sibling walks (`test_cp_14_first_slice.py`,
`_second_slice.py`, `_third_slice.py`, `test_cp_03_canonical_paved_consumer.py`,
`test_cp_03_canonical_cross_deployment.py`) and a name-suffix variant in
`tests/crossproc/test_d_impl_340_cross_deployment.py` — green only because the suites of the trees
they name happen to restore.

**Disposition:** test-isolation defect (measurement instrument). **Behavioral change:** none —
no `src/`, `runtime/` or `examples/cp-14-*` change; cp-05 and CP-14 produce the same outcomes in
both orders. **Needs Dave:** (1) repair the one test, or the whole class of six walks in the same
sitting; (2) whether cp-05's two frozen-specimen *test* loaders may gain restore semantics (a
hygiene change to a frozen specimen's tests under D-IMPL-261's "its test is wrong" carve-out — they
are untidy, not wrong); (3) whether the shared `modules` fixture adds `assembler` to its pop list
to close the latent shadowing hazard (weaker than, and independent of, the audit).

---

## 3. Repair package proposed for ruling

Every proposed repair restores a measurement; none changes SDK or product behavior; none is
an expected-failure mark, a collection-order change, a process isolation, or a broad allowlist.
Classification by the five kinds:

| kind | groups | nodes |
|---|---|---:|
| implementation defect | — | 0 |
| stale test / pin | A (roster maintenance at the review seam), B (ruled proof-machinery defect), D (hash pin) | 44 |
| test-isolation defect | E | 1 |
| documentation / evidence defect | C (86 citations against D-IMPL-114, 63 stale) | 1 |
| accepted limitation requiring explicit release ruling | C's record-class question (`docs/D-IMPL-*.md` living or dated) — decides *how* the 75 record sites are treated, not whether | (within C) |

**Rulings the package needs, in one batch:**

1. **A** — confirm `DecayBasis` and `FreshnessAggregation` as SDK-structure exemptions under
   D-IMPL-331/333 (the review event the two commits skipped).
2. **B** — lift the narrowed two-list roster from `phase-24.9` plan-08 (`4d3b927c`, `899255a1`,
   `f5fc1910`) or re-implement it by hand; record D-IMPL-271 (4)(5) on `main`'s log; narrow the
   whitepaper sibling now or leave it.
3. **C** — living or dated for `docs/D-IMPL-*.md`; confirm the 11 living sites convert; for the 16
   sites with no covering symbol, re-resolve at the citing SHA or bare path.
4. **D** — no ruling needed for the constant (pre-authorized by the test's docstring, the change
   being closed D-IMPL-332); one question whether to narrow the instrument to a
   `LineageEntry`-shape pin.
5. **E** — one test or all six walks; whether cp-05's frozen-specimen test loaders may gain restore
   semantics; whether the shared fixture adds `assembler` to its pop list.

Two records to correct in the same package, both mine: `docs/QUALIFICATION-f0656746.md` §8.3
attributes D to "the 341 closes" (measured: D-IMPL-332 via the cp-09 gate merge) and repeats A's
misattributed `_GLOB_CHARACTERS` message; and the qualification's "not yet established" for B is
now established (red on every commit since `4683f245`). Corrections are appended, not rewritten.

**After the rulings:** repairs on a branch, then the final checkpoint as sequenced — fresh
immutable candidate → single-invocation `make test` → applicable substrate and integration checks
→ release ruling.

---

## Appendix — the 46 nodes by exact id

### A — no-obligation-vocabulary guard (42)

- `tests/invariants/test_no_obligation_vocabulary.py::test_no_scanned_module_declares_an_obligation_vocabulary[src/ccf/controlplane/artifacts.py]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_ignores_obligation_words_in_prose`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[Annotated[...] wrapper around a Literal]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[Final[...] annotation wrapper]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[Mapping[str, str] annotation]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[PEP-604 union annotation]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[Sequence[Literal[...]] annotation with an empty value]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[a container of containers]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[a table as a class attribute]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[a table inside a try-block at module scope]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[a table inside an if-block at module scope]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[dict-builder, keyword form (no ast.Dict node exists in it at all)]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[dict-builder, positional form]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[dict-comprehension over a closed display]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[dict-display, keys (a vocabulary can live in either half)]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[dict-display, values (the single-agent injection \u2014 the mapping gap 3 IS)]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[frozenset-builder]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[frozenset[str] annotation]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[generator expression laundered through a builder]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[list-builder]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[list-comprehension over a closed display]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[list-display]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[literal-alias-of-obligation-names]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[literal-in-a-field-annotation (the DebtProfile spelling)]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[set-builder]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[set-comprehension over a closed display]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[set-display]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[strenum-of-obligation-names (Pitfall 4)]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[tuple-builder]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_guard_refuses_an_injected_obligation_vocabulary[tuple-display (the close-panel injection, verbatim)]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_shipped_tree_declares_no_obligation_vocabulary`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_table_shape_did_not_widen_into_a_ban_on_every_collection[__all__ names exports, which are code]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_table_shape_did_not_widen_into_a_ban_on_every_collection[a local inside a function body is not a declaration]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_table_shape_did_not_widen_into_a_ban_on_every_collection[a mapping inside a function body is still not a declaration]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_table_shape_did_not_widen_into_a_ban_on_every_collection[a mapping of references declares no strings at all]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_table_shape_did_not_widen_into_a_ban_on_every_collection[a mixed table is not a closed string vocabulary]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_table_shape_did_not_widen_into_a_ban_on_every_collection[a numeric mapping is cinv01b-numeric-table's job, in both halves]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_table_shape_did_not_widen_into_a_ban_on_every_collection[a numeric table is cinv01b-numeric-table's job]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_table_shape_did_not_widen_into_a_ban_on_every_collection[a one-entry mapping is a default in both halves, not a choice]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_table_shape_did_not_widen_into_a_ban_on_every_collection[a one-member field default is a default, not a choice]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_table_shape_did_not_widen_into_a_ban_on_every_collection[an empty mapping is not a vocabulary]`
- `tests/invariants/test_no_obligation_vocabulary.py::test_the_walk_sees_the_glob_table_the_exemption_covers`

### B — CLAUDE.md phase-base pin (1)

- `tests/invariants/test_determination_authority_disclosure_delivery.py::test_the_document_is_unchanged_since_the_phase_base[CLAUDE.md]`

### C — citation ratchet (1)

- `tests/invariants/test_citation_coverage.py::test_the_unanchored_python_citation_population_cannot_regrow`

### D — peering claims.py hash pin (1)

- `tests/peering/test_admission_record.py` `::test_claims_py_is_unchanged_so_reading_a_cannot_creep_back_in` — as named at commit `eef849cc`; the repair package renamed it `test_lineage_entry_holds_reading_d_so_reading_a_cannot_creep_back_in`

### E — CP-14 process-order isolation (1)

- `tests/examples/test_cp_14_fourth_slice.py::test_the_consumer_imports_no_producer_and_rebuilds_no_child_material`

