# Deferred Items — Phase 24.4

Out-of-scope discoveries logged during execution. **Nothing here is fixed in
this phase**; each is recorded so it is a known item rather than a surprise.

## 1. `cp-01` and `cp-02`'s Postgres fixtures are not idempotent against a reused container

**Found during:** plan `24.4-04`, while running `make leg-postgres` repeatedly
against one long-lived `postgres:16` container.

**What happens:** `tests/examples/test_cp_01_output.py` and
`test_cp_02_output.py` seed into a FIXED schema (`ccf_v2`) whose SQL inserts
without first dropping. Six runs against the same container left
`ccf_v2.facility` holding six times the fixture's rows, and fourteen tests
across the two modules went red with figures that are exact multiples of the
declared ones (`360` facilities where `60` is declared).

**Why it is out of scope here:** CI starts a FRESH service container per job, so
the leg is green there and was green here the moment a fresh container was used
— verified: `141 passed, 1 skipped` on a clean `postgres:16`. Nothing in plan
`24.4-04` touches those modules, and `tests/examples/test_cp_04_census.py` is
immune by construction (it seeds a per-module schema from
`cp_04_seed.schema_for`, and passed unchanged against the polluted container).

**What it would take:** lead the two fixtures' SQL with
`DROP SCHEMA IF EXISTS ... CASCADE` or move them to per-module schemas, the way
`tests/examples/cp_04_seed.py` does. A decision for whoever owns those modules.

**RE-OBSERVED at plan `24.4-08`, and STILL OUT OF SCOPE.** Running the whole of
`tests/examples` against the same long-lived container gives **14 failed, 749
passed, 1 skipped** — nine in `test_cp_01_output.py` and five in
`test_cp_02_output.py`, all `psycopg.errors.CardinalityViolation: more than one
row returned by a subquery`. **Checked against the pre-phase tree rather than
assumed:** `git checkout 4c90904 -- .` reproduces the same failures in the same
database, so they are not this plan's. The container now holds **516** leftover
schemas from months of local runs. Nothing in plan `24.4-08` touches either
module, and every cp-04 module is immune by construction — per-module schemas
from `cp_04_seed.schema_for`.

## 2. `deployment._rotate` cannot change its input under the walk that calls it

**Found during:** plan `24.4-05`, while sabotaging the shipped rotation
convention. Replacing `_rotate`'s body with `return tuple(circuit)` — the whole
convention removed — left both roster assertions GREEN.

**What is true:** `detect_cycles`'s depth-first walk explores a neighbour only
when `neighbour > start`, so every circuit it closes is already entered at its
lexicographically smallest member. Measured on the committed fixture by spying
on `_rotate`: it is handed **two** circuits and **both** already start at their
minimum. It is a no-op on this estate, and on any estate that walk produces.

**Why this is not a defect:** the convention is a property of the OUTPUT, and
the output has it. `_rotate` is defensive: it makes the ordering true of the
function rather than true only as a consequence of the caller's pruning. Aimed
at something it can change — rotating to the LARGEST member instead — the
sabotage went RED on both roster assertions, so the rosters are genuinely
order-sensitive.

**Why it is out of scope here:** `deployment.py` belongs to plan `24.4-06` and
is not in plan `24.4-05`'s `files_modified`. The only thing worth changing is
`_rotate`'s docstring, which presents the rotation as the mechanism that makes
the roster order true rather than as a belt-and-braces restatement of it.

## 3. `tests/invariants/test_citation_coverage.py` is RED on `main` and was before this plan

**Found during:** plan `24.4-05`, running `tests/invariants` after committing.

**What happens:**
`test_the_unanchored_python_citation_population_cannot_regrow` fails with
**41** unanchored `path.py:LINE` citations against `D-IMPL-123`'s ceiling of
zero. `D-IMPL-114` rules that prose cites `path.py::Symbol`, because a line
anchor is wrong the moment code moves.

**Measured, not assumed.** A detached worktree at `43a57bb` — the commit this
plan started from — reports the SAME **41**. The figure is unchanged at HEAD
after this plan's four commits, and neither
`tests/examples/test_cp_04_cycles.py` nor this file carries a citation of that
form (`grep -nE '\.py:[0-9]+'` over both returns nothing).

**A correction made inside this pass, recorded rather than smoothed.** The
first comparison was taken against `4c90904`, which the session's opening
snapshot named as HEAD. It is not: the real starting commit was `43a57bb`, and
`4c90904` predates the whole cp-04 example tree — so the worktree held none of
the twelve cp-04 files and answered **1** rather than 41. A before-figure read
against the wrong tree is exactly the source-substitution failure this rung's
own census guards against, and it is recorded here because the wrong figure was
plausible and would have survived re-checking.

**Where the 41 live:** thirty-eight in cp-04's own documents (the spec,
`ccf_config.yaml`, `gates.yaml`, `artifacts/assembly-recipe.yaml`,
`deployment.py`), one in `tests/examples/cp_04_seed.py`, one in
`tests/examples/test_cp_04_gates_declaration.py`, one in cp-03's spec.

**Why it is out of scope here:** every site belongs to a document another plan
owns, and plan `24.4-05` may not edit them. Phase 23's precedent is FIX BY
CONVERSION to the `path.py::Symbol` form, never by raising the ceiling.

**CLOSED, and the closure is MEASURED rather than reported.** The forty-one were
converted to the `path.py::Symbol` form by the Gate 1 FORM amendment and the
count is now **0** against the ceiling of 0. Re-measured at plan `24.4-08` by
calling `tests/invariants/test_citation_coverage.py::sweepable_citation_sites`
directly — the COUNT, not a pass — and **sabotaged**: planting one
`src/ccf/client/client.py:100` in `examples/cp-04-corporate-family-tree/run.py`
took it to **1** and turned the test RED, and removing it returned it to **0**.
A ratchet at zero that has never been watched leave zero is not evidence that it
runs.

## 5. `D-36` — the Traversal category expresses an undirected NEIGHBORHOOD, so a directed descendant walk has no SDK expression

**Found during:** plan `24.4-07`, while measuring what the L4 operator actually
serves at each depth rather than assuming it matched the deployment's own walk.

**What is true, read in the source and confirmed by running it.**
`src/ccf/operators/categories.py::TraversalNeighborhood.apply` builds its
adjacency from BOTH endpoints of every edge:

```
adjacency.setdefault(edge.claim.subject_uri, set()).add(edge.claim.object_uri)
adjacency.setdefault(edge.claim.object_uri, set()).add(edge.claim.subject_uri)
```

So the walk is an undirected typed *neighborhood* — exactly what its key
`traversal.typed-neighborhood` says — while a corporate family TREE is a
directed parent-to-child descendant walk. `GQ-10` types the walk on edges only
and says nothing about direction, so this is by design rather than a defect.

**Measured over the committed fixture.** From `SuperMicroComputerInc` the L4
operator serves **20 / 22 / 22** nodes at `max_depth` 1 / 2 / 3, where the
directed parent-to-child reach is **20 / 21 / 22**. The single divergent node is
`CycThornburyCapitalLtd`: cycle 1's closing edge `Thornbury -> Meridian` puts it
one UNDIRECTED hop from `CycMeridianHoldingsSa`, which the anchor reaches
directly, so the operator serves at depth 2 what the tree places at depth 3.

**No declared figure moves.** Criterion 11's `nodes_reached_by_depth`
(`20 / 21 / 22`) is a census figure over the 722 normalized edges and
re-derives exactly. Criteria 11 and 12 and the bundled demonstration are all
taken at the declared default of **3**, where the two agree at **22**. Nothing
in `24.4-MEASUREMENT.md` or `artifacts/expected.yaml` is contradicted.

**What plan `24.4-07` did about it.** Recorded, not absorbed. `projection.py`
serves the node set the OPERATOR returned — never re-walked and never
re-filtered, because a projection that reapplied the depth bound would make the
operator decorative and hide this — and carries each member's TRUE directed
generation, read at the declared ceiling so the map is total.
`FamilyScenario.depth_by_node` carried a claim that the two were "a second
computation of the same number"; that claim was FALSE when measured and is
corrected in place.

**Why it is out of scope here:** criterion 49 forbids modifying `src/`, and this
is the same class as `D-33` — a property the SDK's operator vocabulary cannot
express — which plan `24.4-14` records rather than closes.

**What it would take:** a direction-aware traverse family, or a deployment
operator registered through `build_operator_registry(deployment_operators=...)`.
Both are `src/` or design decisions, and neither belongs to this phase.

## 6. §E.2's `S` routing for absent attribute rows cannot be implemented at the declared numbers

**Found during:** plan `24.4-07`, computing `D_c` for the first time on this rung.

**The conflict, arithmetically.** Spec §E.2's per-component table routes
*"attribute resolution for a given node"* to **`S`** with the behavior
*"serve with a null resolution and elevated `D_c`"*. Twenty of the SMCI
subtree's twenty-two members hold no `ccf_v2.legal_entity` row, so folding
attribute coverage into `S` multiplicatively gives `S = 2/22` and
`D_c = 1 - (1 x 1 x 0.0909) ~= 0.909` against `question.yaml`'s declared
`debt_tolerance` of `0.25`. The product would refuse **409** and never serve the
tree that criteria 12 and 33 and gate `CFT-G09` exist to protect — the same
population the struck nine-jurisdiction envelope deleted, reached by a different
road. The table's own instruction is SERVE.

**Why no weight was invented.** §E.2 states *"Per-component weights:
`[TBC — this build]`"* and `question.yaml` marks `debt_tolerance` itself
`[TBC — product owner]`. There is no declared value to apply, and choosing one
would be choosing the number that decides whether this product's headline
demonstration exists.

**What was shipped instead.** Every factor is measured against the whitepaper's
own definitions with no invented constant — `F` over the REQUIRED signal classes,
`C = 1` over §E.2's fail-closed elements (the whitepaper defines `C` as *"the
fraction of REQUIRED fields actually populated"*, and §E.2 declares the attribute
row *"may be absent: yes, and usually"*), and `S` from the duplicate-identity
finding, which is a real two-node disagreement about one company. Measured:
`D_c = 0.0909`, signal `ok`. The 20-of-22 shortfall is served AS DATA — the
`unresolved_jurisdiction` finding with its roster, and `attributes: null` on each
member — rather than folded into a scalar nobody chose. **`606 of 748` is not a
defect report; it is the answer.**

**What it would take:** a ruling. Either §E.2's `S` routing for attribute
absence is amended, or `debt_tolerance` moves off `0.25`, or the per-component
weights are declared. `produce.py::measure_debt`'s docstring carries the same
account beside the code.

**RULED AND CLOSED 2026-09-01 (Dave, `D-IMPL-230`) — SERVE.** §E.2 is filled
with the measured factor table at §E.2.1 and `debt_tolerance` stays `"0.25"`.
**No weight was invented, and §F.2 row 15 is answered by there being none:** the
declared model is multiplicative and `ccf.halflife.debt::assess_debt` takes
`(factors, profile)` and applies no weight term. Dave named both wrong answers —
*"Don't raise tolerance to 0.95 and don't pretend 0.909 is the whitepaper
number."* The §E.2 table row for attribute resolution now says what the build
does: `S` in principle, **not folded into `S` here**, served as the
`unresolved_jurisdiction` roster instead.

**And the gate is MOVEMENT, not the number.** `tests/examples/test_cp_04_debt.py`
asserts that `D_c` moves in the direction each estate change implies, beside the
twenty-member roster, and that the ATTRIBUTE boundary moves the roster and NOT
the debt — which is the assertion that would go red if anyone quietly folded
attribute coverage back into `S`. Five sabotages were applied and each observed
RED. **No new gate id was minted:** the roster's home is `CFT-G09`.
