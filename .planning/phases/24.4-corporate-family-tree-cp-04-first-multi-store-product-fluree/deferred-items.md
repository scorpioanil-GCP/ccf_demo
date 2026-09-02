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
line-anchored citation of `src/ccf/client/client.py::ProductClient.__init__` —
written in the forbidden `path.py` + line-number form — into
`examples/cp-04-corporate-family-tree/run.py` took the count to **1** and turned
the test RED, and removing it returned it to **0**.
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

## 7. Criterion 37's amended wording names the wrong LISTING — measured, and it needs Dave

**Found during:** plan `24.4-09`, task 1, driving the shipped door's enumeration
at an MCP client rather than reading it off the registration call.

**What was measured.** Against the shipped door, `resources/list` returns an
**EMPTY** list and `resources/templates/list` returns exactly
`ccf-product://{tenant}/{product_class}/{version}`. The reason is mechanical:
`runtime/ccf_runtime/mcp/egress.py::PRODUCT_URI_TEMPLATE` carries `{tenant}`,
`{product_class}` and `{version}` placeholders, so `FastMCP` registers it as a
resource **TEMPLATE** rather than as a concrete resource.

**Why this matters.** Criterion 37, as amended at Gate 1 (`D-IMPL-225`
amendment 1), asserts that the resource *"IS registered and enumerable in
`resources/list`"*. That names the listing the product does not appear in. The
SDK's own `tests/crossproc/test_mcp_egress.py` drives `read_resource` and
`call_tool` and **never enumerates either listing**, so the criterion's wording
was inferred from the `@server.resource` decorator rather than measured at a
client — the same class of thing the criterion was amended for the first time.

**What does NOT move.** The substance holds in full and `D-34` is unchanged: the
door advertises the resource's address shape to every client that enumerates,
cp-04 cannot omit it, `build_egress_server` still cannot be tool-only, and a read
still refuses with `ProductNotServable` and never a tree.
`tests/examples/test_cp_04_two_callers.py::listing_violations` asserts **both**
listings — the template must be there, `resources/list` must stay empty — so
neither the template disappearing nor a concrete entry appearing goes unseen,
whichever way the wording is eventually settled.

**Why it is out of scope here:** amending a criterion is Dave's, on the
`D-IMPL-222` amend-before-execute discipline. It is a **wording** correction to a
ruled criterion, not a change to what the door does, and nothing in this plan
proceeds on a reading of its own — the shipped check asserts the measured
behavior and the divergence is surfaced rather than absorbed.

**RULED 2026-09-01 — `D-IMPL-233` ruling 1. NO LONGER OPEN.** Dave: *"Amend. The
tree is: `resources/list` -> `[]`; `resources/templates/list` -> URI template;
read still `ProductNotServable`. Strike 'enumerable in `resources/list`.'
Shipped check that asserts both listings stays. `D-34` unchanged."* Criterion 37
is amended a second time in `.planning/ROADMAP.md` in the marked form. This item
is kept as the record of the measurement that produced the amendment; it is not
work owed.

## 8. `refuse_bound_payload` is not called on either of cp-04's two callers

**Found during:** plan `24.4-09`, task 1, reading
`runtime/ccf_runtime/mcp/egress.py::ProductResolverProtocol`'s own statement of
what a resolver must do.

**What it says.** *"A resolver that does not call `refuse_bound_payload` serves
an unvalidated payload against a schema its own class declared"* — the SDK ships
the comparison complete and no shipped door invokes it (`D-IMPL-113`,
`D-IMPL-121`), so it falls to the deployment's resolver.

**Measured:** `examples/cp-04-corporate-family-tree/produce.py` calls
`refuse_request` and never `refuse_bound_payload`. **Both callers are on
identical footing** — the in-process caller and the MCP door reach the same
`assemble_and_serve`, so the door is not the weaker path and this is not a
door-specific gap.

**Why it is out of scope here:** it would be a change to `produce.py`, which is
plan `24.4-07`'s file, and it moves what runs on the serving path for **both**
callers rather than only the one this plan adds. Whether cp-04's three validation
gates (`run_gates`) already discharge the intent, or whether the declared payload
schema wants its own comparison, is a question for whoever owns §D.7.

## 9. Through the MCP door, `AssemblyRefused` reaches a client as a server's PROSE

**Found during:** plan `24.4-09`, task 2, exercising the over-ceiling depth and
the declared-but-inert `as_of` against the shipped door.

**What happens.** `AssemblyRefused` is not in
`ccf.products.refusal.py::REFUSAL_KINDS`, so there is no envelope for it — the
gap §F.4 already records for `400 not_supported_at_tier`, met by four rungs in a
row. At the MCP surface the consequence sharpens: `FastMCP` wraps a raised tool
exception as `ToolError: Error executing tool <name>: <message>` and delivers it
`isError=True` with that prose prefix, so a client wanting the governed reason
has to **string-parse a server's wording**. Measured, the refusals arrive intact
and readable — `400 not_supported_at_tier …` and `400 max_depth=7 is outside the
declared bounds 1..6 … never clamped` — but as text rather than as a typed
verdict.

**Why it is out of scope here:** widening `REFUSAL_KINDS` is `src/` work and
criterion 49 forbids it in this phase. Recorded under the same `D-04` posture as
`D-26`..`D-36`: this phase pressure-tests the SDK and records the pressure.
Nothing is papered over — `server/compose.py`'s docstring states that the
refusal propagates and why, and the two-caller module asserts the refusals by
their declared text rather than by the fact that something raised.

## 10. `test_cp_01_output.py` and `test_cp_02_output.py` are RED on this host, pre-existing

**Found during:** plan `24.4-12`, running the whole `tests/examples/` tree once
to check that the new module does not disturb its siblings.

**Measured.** 14 failures — 6 in `tests/examples/test_cp_01_output.py` and 8 in
`tests/examples/test_cp_02_output.py`. **They are not this plan's**, and that is
measured rather than assumed: with `tests/examples/test_cp_04_seams.py` moved
out of the tree entirely, the same 14 fail in the same way.

The failure is a **shared-fixture collision**, the class this repository already
knows: `test_the_seeder_seeded` reports *"the fixture seeded 840 facilities,
expected 60"*, so the local `postgres:16` container is carrying accumulated rows
from earlier runs of a fixture whose schema is not per-module. It is the same
shape `tests/examples/cp_04_seed.py`'s docstring records at length — *"the schema
DDL leads with `DROP TABLE IF EXISTS ... CASCADE`, so the second seed does not
raise; it quietly rebuilds the first module's table underneath it"* — and it is
exactly why cp-04 names its ledger and schema per module.

**Why it is out of scope here.** It is in cp-01's and cp-02's fixtures, not in
anything this phase touches, and the SCOPE BOUNDARY rule for an executor is that
only defects DIRECTLY caused by the current task's changes are auto-fixed.
Whoever owns cp-01 and cp-02 should give those two the per-module schema
naming `cp_04_seed.py::schema_for` already provides.

**What it does NOT affect.** Every cp-04 module is green in two collection orders
(202 and 168 passed), and the fourteen failures are identical with and without
this plan's work.

## 11. The cp-04 documentation page cannot carry an `mkdocs.yml` nav entry — the measurement, moved here from `mkdocs.yml` by ruling

**Found during:** plan `24.4-13`, task 3, attempting the nav entry that plan's
own action text instructed. **MOVED HERE 2026-09-01** from a comment block in
`mkdocs.yml` by Dave's ruling 2 at `docs/DECISIONS.md::D-IMPL-233`.

**Why it moved.** Dave: *"Delete the comment. A `grep -q cp-04` that passes on a
comment is an idle gate. cp-00-03 have no nav; `docs_dir` is `public/`; the page
is gitignored. Plan 13 verify must not require `mkdocs.yml` to mention cp-04.
README + `build_page.py` are the surface."* **The measurement is not disputed
and is not lost — only its home changed.** What was refused is keeping a record
in a place where it also SATISFIES a check: the token `cp-04` was present in
`mkdocs.yml` in both the compliant case (a real nav entry) and the violating
case (a comment saying why there is none), which is this phase's own named
defect class. `deferred-items.md` is read by a human and gates nothing, so the
same sentence here cannot pass anything.

**What was measured, on 2026-09-01, while delivering cp-04.** Adding

```
- Corporate Family Tree (cp-04): ../examples/…/page/cp-04.html
```

to the `Reference` nav makes `make docs-strict` ABORT:

```
WARNING - A reference to '../examples/…/page/cp-04.html' is included in the
'nav' configuration, which is not found in the documentation files.
Aborted with 1 warnings in strict mode!
```

**Why, mechanically.** `example_delivery.md` §10 says *"a new page under
`public/` must be added to the `mkdocs.yml` nav"* — the rule is **conditioned on
`public/`**, and `docs_dir: public` is the whole of what mkdocs reads (`D-01`,
publication is default-deny by existence). An example's companion page is
generated into `examples/cp-NN-<slug>/page/` and its render is **git-ignored**
(`.gitignore` excludes `examples/*/page/*.html`), so it sits outside the
documentation tree twice over. cp-00 through cp-03 carry no nav entry either,
and **no locked criterion ever asked for one.**

**Do not "fix" this by adding an entry.** It turns a green gate red and
publishes a link to a file a fresh clone does not have.

**Verified after the move, 2026-09-01:** `grep -c 'cp-04' mkdocs.yml` returns
**0** against a positive control of **1** for `docs_dir`, so the zero comes from
an instrument that fires; `make docs-strict` exits **0**; and `mkdocs.yml` is
**diff-empty** against the phase base `92761e0` — byte-identical to what it was
before this phase began — against a positive control showing `examples/` moved
**24** files in the same window.

**Whether the companion pages should ever be publishable is out of scope here.**
It would mean either rendering into `public/` or teaching `docs_dir` about a
second tree, and both are surface decisions for whoever owns
`example_delivery.md` §10.

---

## 12. `tests/products/test_gate_two_call_shape.py` is RED on `main` for cp-04, and was before this fix

**Found during:** plan `24.4-FIX-01`, task 1, taking the pre-work baseline.
**Out of scope, not fixed.** It is not caused by anything this fix touches and
closing it needs a ruling, not an edit.

**The measurement.** At `f4a5828` — the phase HEAD, before a character of this
fix existed, working tree clean — `.venv/bin/python -m pytest
tests/products/test_gate_two_call_shape.py -q` reports **4 failed, 113 passed**:

```
test_the_one_document_exemption_has_not_spread
test_every_projecting_example_body_names_the_binder[examples/cp-04-corporate-family-tree/produce.py-]
test_the_premise_detector_reads_the_shipped_tree_correctly
test_no_projecting_body_names_the_binder_without_binding_it[examples/cp-04-corporate-family-tree/produce.py-]
```

The message names the subject exactly. The tool prints a line anchor and
this record keeps it verbatim; the symbol it locates is
`examples/cp-04-corporate-family-tree/produce.py::_project`, and the anchor
below is reproduced as it stood at `7c2d6dd`:

> `examples/cp-04-corporate-family-tree/produce.py:410: _project() constructs or
> runs a projection plan without naming `refuse_operator_set_divergence`.`

**The same four, and only the same four, after this fix.** Recorded to a file
before the first edit and diffed after the last: byte-identical rosters, so this
plan added nothing to the population and removed nothing from it. Enumerated as
a **roster**, never as the count `4` (`D-13`) — a right count with a wrong member
audits clean forever, and this fix changed `_project`'s signature, which is
precisely the kind of edit that could have swapped one failure for another
without moving the total.

**What it is about.** `D-IMPL-86` element (3) requires a projecting body to call
`ccf.deployment::refuse_operator_set_divergence` between plan construction and
`ProjectionEngine.execute`, because the product class's `required_operator_keys`
and the projection's own are two separately authored documents and the binder is
the only thing that holds them in agreement. cp-04's
`examples/cp-04-corporate-family-tree/produce.py::_project` calls neither the
binder nor qualifies for either declared exemption —
`RULED_ONE_DOCUMENT_DEPLOYMENTS` (the deployment registers no
`ccf.projection-requirements` AND the plan's `required=` reads the product
class's own claim) or `RULED_SDK_SUPPLIED_DEPLOYMENTS`.

**Why it is a ruling and not an edit.** cp-04's plan DOES take its `required=`
from the product class's own document — `_project` passes
`required=tuple(scenario.product_class.required_operator_keys)` — which is
exactly the shape the one-document exemption describes. So there are two
defensible closures and they are different decisions: **(a)** add cp-04 to
`RULED_ONE_DOCUMENT_DEPLOYMENTS`, which is Dave admitting a fifth product to a
ruled roster; or **(b)** call the binder in `_project` anyway, which makes it
compare a value against itself — the collapse `_binder_collapses` property (1)
refuses by name. Picking either without a ruling is choosing for him.

**Not this plan's to close, and deliberately not worked around.** Nothing in
`24.4-FIX-01` touches the binder, the exemption rosters or `required=`.

## 13. `CFT-G09` takes the subtree SIZE as an integer, so a swap of either resolving member is invisible to it

**Found during:** plan `24.4-FIX-02`, while measuring the reach of finding 5's
count-preserving member swap.

**What happens:** the swap replaced ONE served member's URI with another valid
node of this estate — the count unchanged at twenty-two — and **2 of 229 cp-04
tests went red**: the seams precondition this plan had just rewritten, and
`CFT-G16` through its pinned seal.
`tests/examples/test_cp_04_payload.py::test_cft_g09_a_node_with_no_lei_stays_in_the_tree_and_the_roster`
**stayed GREEN**, and the reason is structural rather than accidental. It passes
`subtree_size=int(census("anchor_subtree")["reachable_nodes"])` and a
`declared_roster` naming only the **twenty** members with no attribute row. The
member swapped was `SuperMicroComputerInc` — one of the **two** that resolve —
so all twenty declared names were still in the tree, the size was still
twenty-two, and the gate reported clean.

**Why it is out of scope here:** the close panel's four findings are all in
`tests/examples/test_cp_04_seams.py` and this is in
`tests/examples/test_cp_04_payload.py`. It is a pre-existing shape, not
something this plan's edits caused, and `CFT-G09`'s own declared claim — *"a
node carrying no LEI stays in the tree AND in the roster"* — is about the
twenty and is discharged as written. Widening it is a change to what the gate
claims, which is a decision rather than a repair.

**What it would take:** hand `unresolved_violations` the WHOLE subtree roster —
the union `examples/cp-04-corporate-family-tree/artifacts/expected.yaml`
already carries, which
`tests/examples/test_cp_04_seams.py::declared_subtree_roster` now assembles —
and compare it both ways instead of taking `subtree_size` as an integer. The
same edit that fixed finding 5, applied one gate over.

**Nothing was worked around.** `CFT-G09` is untouched by this plan.

## 14. What the product should DO when an estate carries a SHARED LEI — a ruling, not an edit

**Found during:** plan `24.4-FIX-03`, disposing close-panel finding 7 (codex).

**What is true, read in the source.**
`examples/cp-04-corporate-family-tree/deployment.py::resolve_anchor` issues
`SELECT ?s WHERE { ?s <lei> "…" }` with **no `ORDER BY`** and returns the FIRST
binding. Two graph nodes carrying one LEI would therefore make the anchor — and
with it the whole served family, its content address and its replay record —
depend on the store's row order, against a product whose own declaration says
`determinism_class: deterministic`.

**What was CLOSED here, and it is the check half only.** The estate property the
determinism rests on was stated in a COMMENT in
`artifacts/expected.yaml::census.lei_coverage` — *"1:1 — no node carries two, no
LEI is shared"* — and the precondition guarding it compared distinct LEI VALUES
against the declared NODE count, which a duplicate accompanied by an extra node
satisfies exactly. `tests/examples/test_cp_04_seams.py::lei_identity_violations`
now asserts both halves against the committed fixture, with four controls, and
the measurement is 181 LEI-bearing nodes / 181 distinct values / 0 nodes
carrying two / 0 values shared, over 748 insert nodes.

**Why the rest is out of scope here.** What the product should DO when an estate
DOES carry a shared LEI is a product-surface decision with at least three
defensible answers, and they are different decisions:

* **(a)** a **404** — the anchor is unresolvable rather than ambiguous, which
  reads *this company has no family* and is a claim about the world;
* **(b)** a **new refusal kind** — the honest verdict is *ambiguous anchor*, and
  `ccf.products.refusal.py::REFUSAL_KINDS` has no member for it. That is `src/`
  work, which criterion 49 forbids this phase, and it is the same gap deferred
  item 9 records for `AssemblyRefused`;
* **(c)** **serve the tree carrying a duplicate-identity finding** — which is
  what this product ALREADY does for the duplicate pair one hop out
  (`census.duplicate_entity_pair`, `CFT-G09`'s neighbour). It is the answer most
  consistent with the product's own subject and the largest change.

**Nothing was decided and nothing was worked around.** `resolve_anchor` is
untouched.

## 15. `refuse_stale_vocabulary_pointer`'s second condition cannot fail over its OWN source document

**Found during:** plan `24.4-FIX-03`, while BUILDING the control for close-panel
finding 9 — not by reading the function.

**What is true.** The function holds every document `ccf_config.yaml` names to
carrying all six family predicate IRIs. The set it looks for is
`examples/cp-04-corporate-family-tree/deployment.py::family_predicate_iris`,
which reads `SOURCE_VOCABULARY` — **the very document the fourth condition
requires to be among the named ones**. So for that document the second condition
compares a file against itself and is satisfied whatever the values are: a
scratch `source-vocabulary.yaml` declaring `iri: TBC` for all six passes, and
that is asserted rather than described by
`tests/examples/test_cp_04_traversal.py::test_the_vocabulary_pointer_cannot_fail_over_its_own_source_document`.

**What the check therefore does have.** Condition 1 (a pointer exists at all),
condition 3 (every named document exists), condition 4 (the interpreter's
document is among the named), and condition 2 **over any ADDITIONAL document the
config names** — which is exactly the shipped defect its docstring reproduces
(repointing the sentence at `assembly-recipe.yaml`). The value reading added by
finding 9's fix is what makes condition 2 mean *carries* rather than *mentions*
for those.

**Why it is out of scope here.** Making condition 2 non-circular for the primary
document requires a second, independent statement of the six IRIs to hold it
against — a second place for one fact, which
`artifacts/expected.yaml`'s own header refuses by name — or a decision that the
IRIs live somewhere other than the document the interpreter reads. Both are
surface decisions for whoever owns the artifact set.

## 16. `CFT-G01`'s recipe witness names a weaker property than the gate proves

**Found during:** plan `24.4-FIX-03`, disposing close-panel finding 10 (codex).

**The finding as filed was REJECTED and the residual is this.** Codex reported
that `CFT-G01` claims a *known* FIBO class while checking non-emptiness. It does
not: `tests/examples/test_cp_04_traversal.py::class_violations` asserts
MEMBERSHIP in `declared_class_vocabulary()` and carries two positive controls,
one refusing an untyped node and one refusing an off-ontology class — *"a check
that accepts any string measures presence"* — plus a vacuity control.

**What is real.** `artifacts/assembly-recipe.yaml` step 3's witness argument is
`every_returned_node_carries_a_non_empty_fibo_type_chain`. Non-empty is not
known, so the recipe's witness understates what the build proves.

**Why it is out of scope here.** Nothing executes a recipe witness —
`grep -rn` for that argument across the tree returns exactly one hit, the
declaration itself. That is `24.4-D-31`, which Phase 24.5 closes. It matters
*then* rather than now: a checker wired to that string would implement the
weaker property while `CFT-G01` proves the stronger one. Whether the witness is
renamed to match the gate, or the gate's statement is read down to the witness,
is a decision for the plan that builds the executor.

## 17. Close-panel advisories deferred by ruling at plan `24.4-FIX-05` — WR-02, WR-03, WR-04, WR-06

**Found during:** the 2026-09-01 close-panel review (`24.4-REVIEW.md`). Dave's
ruling scoped `24.4-FIX-05` to CR-01, CR-02, WR-05 and WR-01. The four warnings
below are **advisory, recorded and NOT fixed** — each named with why it is
deferred rather than worked in this fix.

**WR-02 — contract validation runs after the full two-store source read.**
`produce.py::assemble_and_serve` calls `read(...)` (the whole two-estate read,
both closed-world guards, the mint) BEFORE `refuse_request` and the
unsupported-parameter loop, while `ccf_config.yaml` and `produce.py`'s own inline
comment say the contract is *"Checked at the door, before either store is
opened, so a question this class does not answer costs nothing."* The order is
false as written. **Deferred:** the fix is a reorder of the spine (`produce.py`)
that moves what runs for BOTH callers, and it is an efficiency/wording
correction rather than a defect that takes anything down — out of the four
scoped fixes. A reorder here would also want its own equivalence check that the
two callers still agree, which belongs with whoever reworks the spine.

**WR-03 — `intent` is declared operative ("an unknown intent is a 400") and is
unimplemented; the caller's copy is discarded.** `refuse_request` checks only
`type: string`, so any `intent` serves, and `deployment.py::request` sets
`intent` from `question.yaml` unconditionally, so `ProductRequest.intent` is
always the artifact's value even when the caller's differs. **Deferred:** it is
the SAME class as CR-02 (a declared-operative-but-inert parameter) on a
different parameter, and it is not in this fix's scope. The two honest closures
— validate `intent` against a declared closed set and refuse unknowns, OR
rewrite the description to what is true and derive `intent` from the caller's
parameters — are the same shape CR-02 took for `debt_tolerance` and belong to
whoever owns the `intent` surface.

**WR-04 — the verified caller `client_id` does not reach the replay record.**
`serve.py::resolve_perspective` builds `Perspective(principal_id=grant.client_id,
…)` and `compose` forwards it, but `deployment.read` rebuilds the scenario
perspective from the registered artifact via `perspective(role)`, whose
`principal_id` is `ccf_config.yaml`'s `PRIN-COV-001`. Today the two coincide
because the minted token's `client_id` is that same string, so the role-axis
check cannot see it. **Deferred:** threading the full forwarded `Perspective`
through `produce` to `read` changes what the serving path records for BOTH
callers and reopens `DI-15.5-03` on the principal axis — a behavior change to the
spine beyond this fix, and it wants its own principal-axis assertion from the
door test.

**WR-06 — SQL identifiers interpolated without identifier quoting.**
`deployment.py::resolve_attributes` composes
`f'SELECT {projection} FROM "{resolved.schema}".{table} WHERE {key_column} =
ANY(%s)'`; `schema` is double-quoted but not escape-doubled, and `table`,
`key_column` and the served columns are interpolated bare. All sources are
deployment-controlled (env var + `source-vocabulary.yaml`), so this is **not
remotely injectable** — the key VALUES are correctly bound via `ANY(%s)`.
**Deferred:** it is adoption-template hardening (composing identifiers with
`psycopg.sql.Identifier`), valuable because adopters repoint the artifacts at
their own estates, but not a defect in the shipped deployment and outside this
fix's scope. The same pattern in `tests/examples/cp_04_seed.py` and the dump
tool is test-side and acceptable.
