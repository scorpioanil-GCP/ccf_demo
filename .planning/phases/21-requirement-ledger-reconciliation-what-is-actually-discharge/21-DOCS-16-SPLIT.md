# Phase 16's eighteen `DOCS-` rows — the two-sided split

Phase 16 was a documentation-and-examples rewrite that executed sixteen plans
and was retired on 2026-08-17 at `D-IMPL-152` when its example surface was
rejected. **That ruling retired the approach, not the need** — `RETIRED.md`
says so in its own heading: *"THE PLAN SET IS RETIRED. THE OBLIGATIONS ARE NOT
DISCHARGED."* So the eighteen requirement rows the phase minted are not
automatically dead, and they are not automatically alive either. This document
sorts them by one test — **does the obligation this row states have a satisfied
referent in the tree as it stands today?** — and asks you to rule.

**The test is not "was the plan executed."** A plan in `abandoned/` is evidence
about history, never about today's tree. Eight of these rows were substantively
shipped by plans that ran *after* the phase's original stop, and by Phases 17,
18 and 20 that replaced it; the ledger never recorded any of it.

**The headline finding.** Ten rows are done. Three are genuinely not built and
belong on your work list. Five are split — a limb shipped and a limb did not.
**Exactly one limb, in one row, is orphaned** — and that is a real result, not
a thin one: an obligation about a *need* survives an approach's rejection, so
almost nothing here died with the phase. What did die is `DOCS-18`'s
no-fabric-change assertion, and it died because **you revoked it yourself** at
`D-IMPL-96`.

---

## The eighteen rows

| Id | The obligation, in one line | Side | Proposed verdict | Evidence in one line |
|---|---|---|---|---|
| DOCS-07 | The Phase 16 ruling package is recorded, with no source diff | A | **Complete** | `D-IMPL-94` at `docs/DECISIONS.md:352` records all five named components; `docs/surface/examples/ERGO-03-FROZEN.md` exists and `tests/examples/test_surface_audit.py` is gone, exactly as its `D-15` limb directed |
| DOCS-08 | Three gate-checker failures green; `make ci` composes the three gate suites | A | **Complete** | `Makefile:172` is `ci: ci-core examples docs-strict gate-tools` and `gate-tools` runs both gate suites; the docstring-leak and snippet-fixture failures are green and stay green under their own tests |
| DOCS-09 | KYC/UBO source estate with corp→corp ownership edges, never written to L3 | A | **Complete** | `examples/s1-01-hello-context-product/source_estate.py` and its artifact, with a gate per limb in `tests/examples/test_source_estate.py` including one that asserts the generator never touches the graph |
| DOCS-10 | Config-resolved backend **and** a six-backend `content_hash` CI matrix | A + B | **Partial** | Limb 1 ships at `examples/s1-00-companies-over-revenue/deployment.py::connection`; limb 2 does not exist — `backends.yaml` declares one profile and no test compares a served product across substrates |
| DOCS-11 | *Every* example separates spine from deployment via the canonical markers | A + B | **Partial** | The mechanism ships and is gated by `tests/examples/test_spine_separation.py`, but its scope is `SECTION_ONE_GLOB = "s1-*"` — two directories out of thirteen |
| DOCS-12 | Section 1 agent-free deterministic examples **plus** published pages | A + B | **Partial** | The examples ship and are gated by `tests/examples/test_section_one_is_agent_free.py`; no published page names a Section-1 example or teaches `assembly_mode` as a governance choice |
| DOCS-13 | Three external harness client legs importing nothing from `ccf`, **plus** pages | A + B | **Partial** | Phase 20 shipped all three legs and gates them harder than the row asks — `ccf` is refused by name, not merely absent; the published surface is one paragraph in a how-to |
| DOCS-14 | Section 3 — embedding CCF in a host app, agentic skills, plus pages | B | **Not built** | No `examples/s3-*` directory exists, no `example-s3-*` make target exists, and no published page states the governed-identity claim the row requires |
| DOCS-15 | An adoption-argument page naming RAG, hand-rolled assembly, semantic layers | B | **Not built** | No page under `public/` names any of the three alternatives; the grep returns nothing |
| DOCS-16 | Advisories A-1, A-2, A-3, A-8 discharged with positive per-advisory evidence | A | **Complete** | `tools/docs_tests/test_advisory_discharge.py` carries a named assertion per advisory plus a refusal control per advisory |
| DOCS-17 | `examples/00`–`08` and `external/00-hello-context` retired, pages re-cut | B | **Not built** | All ten directories are still in the tree; **you quarantined them deliberately** at `D-IMPL-145` limb 2 because removal costs re-cutting 102 snippet includes across 15 published pages |
| DOCS-18 | Phase close: no-fabric-change assertion, gate sweep, ledger matching the tree | A + B + C | **Partial** | Limb 1 is **orphaned** — `D-IMPL-96` withdrew criterion 10 and with it `D-13`'s exception and `gate_16.py`; limb 2 ships as `make ci`; limb 3 is what this phase is doing |
| DOCS-19 | The four `D-IMPL-126` consumption papercuts closed in the fabric | A | **Complete** | All four ship and each has its own gate — `from_declared`, the dual-channel refusal, the typed 503, and `X-CCF-Content-Address` |
| DOCS-20 | The MCP egress door carries a parameterised tool beside its resource | A | **Complete** | `runtime/ccf_runtime/mcp/egress.py` carries `PRODUCT_REQUEST_TOOL` behind an opt-in pair, with a seven-scenario parity matrix proving the tool is never the weaker path |
| DOCS-21 | Experience server handlers gated, or their ungated status pinned | A | **Complete** | Both limbs: `get_context` and `get_lineage` traverse the resource's own governance sequence, and the three tools that stay ungated are pinned by a named test whose inversion is the fix |
| DOCS-23 | One `ccf_config.yaml`, typed, schema-exported, unknown keys refused by name | A | **Complete** | `src/ccf/deployment/config.py` plus `docs/schemas/ccf.deployment-config.json`, with refusals that name one unknown key and that name two together in one message |
| DOCS-24 | Reserved sections derive their five fields; adopter-owned still state three | A | **Complete** | `_RESERVED_SECTIONS` drives the derivation, and the R-1 refusal family proves it does not over-reach into SDK-owned sections |
| DOCS-25 | Single-file and multi-file forms register at identical content addresses | A | **Complete** | `tests/deployment/test_config_equivalence.py` compares both forms pin for pin, with a perturbation control proving the comparison still discriminates |

**Totals: ten Complete, five Partial, three Not built, zero wholly Orphaned —
with one orphaned limb inside `DOCS-18`.**

---

## DOCS-07 — the Phase 16 ruling package

**The obligation.** `D-IMPL-94` records the Mode 2 attachment point above
`serve()`, what `assembly_mode` describes, the criterion-10 carve-out, the
Gate-2 tripwire carry-forward with its two-limb bound, and the ERGO-03 freeze —
with no accompanying source diff.

**Side A.** The entry is at `docs/DECISIONS.md:352` and it carries every one of
the five named components. The ERGO-03 freeze is visible in the tree as well as
in the log: `docs/surface/examples/ERGO-03-FROZEN.md` exists and
`tests/examples/test_surface_audit.py` is absent, which is exactly the
disposition `D-15` directed — freeze the measurement, retire the running test.

**The wrinkle, stated rather than elided.** `D-IMPL-96` (`docs/DECISIONS.md:356`)
later revoked criterion 10 and with it the carve-out this row asks the package to
record. That does not unmake the row: its predicate is that the package **is
recorded**, and the record now includes its own withdrawal, which is the
append-only log working correctly.

**Proposed: `Complete`.** A process row — the rulings are themselves the
evidence, the same shape as `HARD-01`.

## DOCS-08 — the gate-checker repair and `make ci`'s composition

**The obligation.** Three pre-existing gate-checker failures are green, and
`make ci` composes `tools/lints/tests`, `tools/publish_scan_tests` and
`tools/docs_tests`, so its "full local reproduction of the always-on pipeline"
claim is true rather than aspirational.

**Side A, both limbs.** `Makefile:172` reads `ci: ci-core examples docs-strict
gate-tools`, and `gate-tools` runs `pytest tools/lints/tests -q` then `pytest
tools/publish_scan_tests tools/docs_tests -q`. All three suites are therefore in
`make ci`. The three failures are green and stay green under
`tools/publish_scan_tests/test_docstring_leaks.py::test_no_docstring_reproduces_whitepaper_body_text`
and `tools/docs_tests/test_snippet_gate.py::test_a_missing_snippet_file_fails_the_strict_build`.

**A named gap, the same one `DOCS-06` carries.** No test in this tree reads the
`ci` target's composition. If a later edit dropped a suite from `gate-tools`,
nothing would go red. That is a work-list item, not a defect in this row.

**Proposed: `Complete`.**

## DOCS-09 — the KYC/UBO source estate

**The obligation.** Corp→corp `hasOwnershipInterestIn` edges with per-edge
`ownershipPercent`, generated deterministically from a definition artifact,
written to the source estate and never to CCF's L3.

**Side A, limb for limb, each with its own gate.**
`examples/s1-01-hello-context-product/source_estate.py` reads
`examples/s1-01-hello-context-product/artifacts/source-estate.yaml`, and
`tests/examples/test_source_estate.py` asserts a depth-two ownership chain
exists, that every ownership edge carries its own percentage, that the generator
is deterministic, that it never touches the Context Graph, and that it refuses to
run without its artifact.

**One coupling worth knowing.** The evidence lives in
`examples/s1-01-hello-context-product`, which `CLNT-17`'s work list proposes
removing. Retiring that tree removes this row's demonstration.

**Proposed: `Complete`.**

## DOCS-10 — config-resolved backend and the six-backend matrix

**The obligation.** One example driver resolves its backend from a supplied
configuration artifact, and a CI matrix asserts `content_hash` equality of the
served Context Product across `sqlite`, `memory`, `postgres`, `neo4j`, `mongo`
and `fluree`.

**Limb 1 — side A.** `examples/s1-00-companies-over-revenue/deployment.py::connection`
takes the substrate name from `examples/s1-00-companies-over-revenue/ccf_config.yaml`'s
top-level `backend:` and the connection shape from
`examples/s1-00-companies-over-revenue/backends.yaml`. Its docstring says the
property outright: *"The only branch here is over the two value SOURCES this
example uses, never over a substrate name."* No credential is in either
document — only a variable's name.

**Limb 2 — side B, and here is the named absence.**
`examples/s1-00-companies-over-revenue/backends.yaml` declares exactly one
profile, `postgres`. `example-s1-00` is not in the `examples:` aggregate at
`Makefile:256` and appears in no job in `.github/workflows/ci.yml`. And no test
anywhere in `tests/` asserts `content_hash` equality of a served Context Product
across substrates — the four service containers in the CI test job belong to the
Phase 15.2/15.3 substrate differential suite, which compares *query answers*
across adapters, not a *served product* across backends.

**Proposed: `Partial`.**

## DOCS-11 — spine/deployment separation in every example

**The obligation.** Every example physically separates the CCF call spine from
deployment code into distinct modules carrying the canonical ordered marker set.

**Side A.** The mechanism ships and is gated hard:
`tests/examples/test_spine_separation.py` asserts exactly one module per example
carries the canonical regions, that the seven regions open in order, that every
opened region closes, and that the spine is silent — with refusal controls for
an example carrying no such module and for a second module carrying them.

**Side B — the named absence.** `SECTION_ONE_GLOB = "s1-*"`. The gate scans
`examples/s1-00-companies-over-revenue` and `examples/s1-01-hello-context-product`
and nothing else. Measured across the tree: no marker region is opened anywhere
in `examples/08-e2e-demo`, `examples/external/00-hello-context`,
`examples/hw1-companies-over-revenue` or `examples/hw1-harness-clients`, and
`examples/00-quickstart` carries one marker for the snippet gate rather than the
ordered set. The word in the row is *every*, and *every* is not true of the tree.

**Proposed: `Partial`.**

## DOCS-12 — Section 1's examples and its published pages

**The obligation.** Section 1 ships agent-free deterministic examples **and**
published pages teaching Context Products, the four Context Operator categories
and the six axes of `G(E, R, T, P, Π, L)`, introducing `assembly_mode:
algorithmic` as a governance choice with two siblings named.

**Side A — the examples limb.** `examples/s1-00-companies-over-revenue` and
`examples/s1-01-hello-context-product` ship. Agent-free is gated by
`tests/examples/test_section_one_is_agent_free.py`, which walks every Section-1
module for an agent-surface import and carries an injection control. Determinism
is gated by `tests/examples/test_s1_00_output.py`.

**Side B — the pages limb, with the absence named.** No page under `public/`
mentions `s1-00` or `s1-01`; the grep across the published tree returns zero.
The six axes appear once, at `public/concepts/pillars/data-context.md:42`, and
that is Phase 14's pillar page rather than a Section-1 teaching page.
`assembly_mode` appears once, in `public/concepts/replay-anatomy.md`, described
as a field of replay dimension 3 — **not** as a governance choice, and its two
siblings are named nowhere.

**Proposed: `Partial`.**

## DOCS-13 — Section 2's three harness legs and its published pages

**The obligation.** Section 2 ships external client legs for the Claude Agent
SDK, Google ADK and LangGraph that import nothing from `ccf`, asserted by an AST
matcher with a negative control and an exactly-three-harnesses assertion, plus
their published pages.

**Side A, and stronger than the row asked.** Phase 20 shipped
`examples/hw1-harness-clients/client_anthropic.py`,
`examples/hw1-harness-clients/client_adk.py` and
`examples/hw1-harness-clients/client_langgraph.py`. The purity check is an AST
matcher — `tests/examples/test_client_example_purity.py::check_example_purity`
walks every `ast.Import` and `ast.ImportFrom`, including imports deferred into a
function body — and `ccf` is **refused by name for this root in a branch checked
before the permitted-set test**, so widening the permitted set cannot admit it.
Three negative controls watch the matcher refuse a plain import, a from-import
and a deferred import. The three-harness count is held by
`tests/examples/test_hw1_harness_clients_readme.py::test_the_three_live_targets_exist_and_are_outside_the_always_on_list`,
with a control that goes red on a Makefile carrying two of the three.

**Side B — the named absence.** The published surface for this work is a single
paragraph at `public/how-to/run-agents-cross-process.md:197`. There is no
Section-2 page and no per-harness page anywhere under `public/`.

**Proposed: `Partial`.**

## DOCS-14 — Section 3

**The obligation.** Section 3 ships embedding CCF in a host application
(in-process, MCP egress, A2A admission, ArtifactStore swap) and developing
agentic skills within CCF, plus their published pages, stating plainly that SDK
agents are governed identity and are structurally barred from calling a model.

**Side B — the absence, named four ways.** No `examples/s3-*` directory exists;
the tracked example trees are `examples/00-quickstart` … `examples/08-e2e-demo`,
`examples/external/`, `examples/hw1-companies-over-revenue`,
`examples/hw1-harness-clients`, `examples/s1-00-companies-over-revenue` and
`examples/s1-01-hello-context-product`. `Makefile` carries no `example-s3-*`
target. No page under `public/` states the governed-identity claim — the grep for
the row's own phrasing returns zero. And the plan that was to build it is in
`.planning/phases/16-documentation-rewrite-the-deterministic-path-the-adoption-ar/abandoned/`.

**Why `Not built` and not `Orphaned`.** The substance the row names is in the
tree — `examples/04-cross-process` demonstrates cross-process and admission,
`examples/07-artifact-store-mcp` demonstrates the store swap,
`examples/02-skilling` demonstrates skilling. What is missing is a coherent
Section-3 surface and its pages. The need survives; only the approach was
rejected. This is the same call `21-03` made on `EXAM-02`, and the two rows are
coupled.

**Proposed: `Not built`.**

## DOCS-15 — the adoption-argument page

**The obligation.** An adoption-argument page names RAG over a vector store,
hand-rolled context assembly, and a semantic layer plus prompt templates, and
states what each lacks against cited shipped mechanism, with the UBO question as
its worked demonstration and the passage-anchor honesty caveat carried.

**Side B — the absence.** No page under `public/` names any of the three
alternatives; `grep -rln "RAG\|vector store\|semantic layer" public/` returns
nothing. Nor does any published page carry the UBO question — the grep for
*"ultimately owns"* across `public/` returns nothing either. The page does not
exist in any form.

**Proposed: `Not built`.**

## DOCS-16 — the four carried advisories

**The obligation.** Carried advisories A-1, A-2, A-3 and A-8 are discharged in
the published tree with positive per-advisory evidence rather than a green
build.

**Side A.** `tools/docs_tests/test_advisory_discharge.py` carries a named
assertion per advisory — the preferred day-one import documented and no
submodule import taught, the maintainer page published and naming its subject,
no documented boot signature disagreeing with the code, and A-8's both halves in
one paragraph. Each is paired with a control that mutates a copy of the real page
and asserts refusal, so the evidence is positive and non-vacuity is proven by
watching the gate fail rather than by a corpus floor. Failures report by advisory
id.

**Proposed: `Complete`.**

## DOCS-17 — retiring `examples/00`–`08` and `external/00-hello-context`

**The obligation.** `examples/00`–`08` and `examples/external/00-hello-context`
are retired with every published page that sourced from them re-cut, proven by
standing gates for dangling includes, stale prose paths, Gate-2 wording and
documented commands.

**Side B, and the absence is a thing you can look at.** All ten directories are
in the tree today: `examples/00-quickstart`, `examples/01-agent-basics`,
`examples/02-skilling`, `examples/03-harness-portability`,
`examples/04-cross-process`, `examples/05-workflow-hitl`,
`examples/06-decision-replay`, `examples/07-artifact-store-mcp`,
`examples/08-e2e-demo` and `examples/external/00-hello-context`.

**The gates limb did ship**, and it guards a retirement that has not happened:
`tools/docs_tests/test_snippet_gate.py`,
`tools/docs_tests/test_no_stale_example_paths.py`,
`tools/docs_tests/test_gate_two_wording.py` and
`tools/docs_tests/test_documented_commands_exist.py` are all in the tree, as is
the coupling inventory at `docs/surface/examples/RETIREMENT-COUPLINGS.md`.

**This is not neglect — it is your own ruling.** `D-IMPL-145` limb 2
(`docs/DECISIONS.md:235`) quarantined the `00`–`08` group deliberately, because
removing it costs re-cutting the published pages that source from it, with no
replacement written. Re-measured today rather than carried from the ruling:
**111 references across 15 published pages, 102 of them snippet includes**, and
zero published references to the `s1-*` trees. The figures have not moved.

**Proposed: `Not built`** — coupled to `CLNT-17` and to `D-27`, and blocked on
the same undecided `00`–`08` half that plan `17-08` returned to you.

## DOCS-18 — the Phase 16 close

**The obligation.** The phase closes with a mechanical no-fabric-change
assertion carrying `D-13`'s single enumerated exception, a full gate sweep, and
a requirement ledger that matches the tree.

**This row splits three ways, and it is the only row with an orphaned limb.**

**Limb 1 — orphaned.** `D-IMPL-96` (`docs/DECISIONS.md:356`) revoked ROADMAP
Phase 16 criterion 10 outright, and in its own words *"with it the elaborate
machinery built to work around it: `D-13`'s single enumerated exception for
`ProductClassDeclaration`'s docstring, plan 16-19's `gate_16.py` allowlist… and
`D-14`'s two-limb bound."* Your stated reason was that the rule *"has been used
out of context."* Building this limb now would re-instate a rule you revoked.
The absence is visible: `tools/gates/` contains no module at all, only a stale
`__pycache__`.

**Limb 2 — side A.** The full gate sweep exists as `make ci`, which is
`DOCS-08`'s subject.

**Limb 3 — side B, in flight.** A requirement ledger that matches the tree is
exactly what this phase is doing; plans `21-06` and `21-07` close it.

**Proposed: `Partial`,** with limb 1 recorded as orphaned in the row's own text
so a later reader does not open it as work.

## DOCS-19 — the four `D-IMPL-126` consumption papercuts

**The obligation.** A `ProductRequestContract` reachable from a
manifest-returned `DeclaredArtifact` by one named call; `ServableProduct`
stating why it is unconstructible on both attribute channels while leaving
`hasattr` returning `False`; a product-only deployment constructing
`ApiDependencies` with three handles and getting a typed 503 naming the absent
field; and every canonical HTTP body publishing its own content address under
`X-CCF-Content-Address`.

**Side A, all four, each with its own gate.**
`src/ccf/products/request.py::from_declared`;
`src/ccf/products/gates.py::ServableProductNotAModel`, which derives from both
`GateBypassError` and `AttributeError` so `hasattr` degrades rather than
explodes; `runtime/ccf_runtime/http_api/errors.py::ERROR_ROUTE_HANDLE_ABSENT`
with the three-handle construction and the typed 503 asserted directly; and
`runtime/ccf_runtime/http_api/routes/__init__.py::CONTENT_ADDRESS_HEADER`,
asserted to equal the SHA-256 of the product body and to be absent from a
refusal.

**Proposed: `Complete`.**

## DOCS-20 — the parameterised MCP egress tool

**The obligation.** The MCP egress door carries a parameterised tool alongside
its unchanged resource.

**Side A.** `runtime/ccf_runtime/mcp/egress.py` exposes `PRODUCT_REQUEST_TOOL`
behind an opt-in pair that must be supplied together or not at all. The strong
gate is not that the tool exists but that it is never the weaker path: a parity
matrix runs all seven governance scenarios through both the tool and the
resource and asserts they decide alike, the tool takes no caller-supplied
address, a tokenless call never reaches the entitlement check, and two questions
reach two content addresses — which is what refutes the reading that a Context
Product is precalculated.

**Proposed: `Complete`.**

## DOCS-21 — the Experience server's client-parameterised handlers

**The obligation.** The Experience MCP server's client-parameterised handlers
are gated, **or** their ungated status is pinned.

**Side A, and both limbs are satisfied rather than one.**
`runtime/ccf_runtime/mcp/experience.py` routes `get_context` and `get_lineage`
through the same `verified_grant()` → `entitled_perspective(...)` sequence the
`context_product` resource beside them uses — imported rather than re-declared —
and the authorized perspective is asserted arriving at the provider by value.
The three tools an entitlement cannot honestly decide ship authenticated, with
their ungated status pinned by a test named for the gap, whose inversion is the
signature of the fix.

**Proposed: `Complete`.**

## DOCS-23 — the single-file authoring document

**The obligation.** A single `ccf_config.yaml` is a typed, schema-exported
authoring document whose unknown top-level keys are refused by name.

**Side A.** `src/ccf/deployment/config.py` carries the typed document,
`docs/schemas/ccf.deployment-config.json` is the exported schema held
byte-for-byte against what the class emits, and the refusal is by name in both
the single-key and multi-key cases — one unknown key is named alongside the
reserved names, and two are named together in one message rather than one at a
time.

**Proposed: `Complete`.**

## DOCS-24 — the reserved-section derivation

**The obligation.** Reserved sections derive `path`, `key`, `class_id`, `role`
and `registration` for `ccf.*` classes, while adopter-owned sections still state
`class_id`, `role` and `registration`.

**Side A.** `src/ccf/deployment/config.py`'s `_RESERVED_SECTIONS` table drives
the derivation, and the check that matters is that it does **not** over-reach:
the R-1 refusal family asserts an adopter-owned section missing all three fields
is refused with only the missing fields named, that SDK-owned sections still
derive silently, and that a positive and a negative case in one document behave
independently. Every derived path is the literal config filename, and an override
contradicting an SDK-fixed role or path is refused.

**Proposed: `Complete`.**

## DOCS-25 — boot equivalence across the two authoring forms

**The obligation.** A deployment authored in the single-file form registers
artifacts at identical content addresses to the same deployment authored across
files, and every existing multi-file deployment is unchanged.

**Side A.** `tests/deployment/test_config_equivalence.py` boots both forms and
compares the resolved pins entry for entry in manifest order and the artifacts
alongside them — and it carries a perturbation control proving the comparison
still discriminates, so a comparison that had quietly stopped comparing fails
here rather than passing over everything. The multi-file limb is held by the
eight `hw1` documents registering at identical content addresses in both forms.

**Proposed: `Complete`.**

---

## What you are being asked to rule on

1. **Accept the ten `Complete` verdicts** — `DOCS-07`, `-08`, `-09`, `-16`,
   `-19`, `-20`, `-21`, `-23`, `-24`, `-25` — each backed by a citation you can
   follow.
2. **Accept the five `Partial` verdicts** — `DOCS-10`, `-11`, `-12`, `-13`,
   `-18` — each naming which limb shipped and which did not.
3. **`DOCS-18` limb 1 is orphaned by your own `D-IMPL-96`.** Confirm it stays
   closed rather than re-opened.
4. **`DOCS-17` is blocked on you, not on us.** Plan `17-08` returned the
   `00`–`08` half of `D-27` undecided and `D-IMPL-145` quarantined it. The cost
   is 102 snippet includes across 15 published pages. Rule the disposition.
5. **`DOCS-14`, `DOCS-15` and `DOCS-17` go on the work list.** Confirm, and say
   whether `DOCS-14` keeps the `s3-` naming at all — the section scheme was
   Phase 16's, and Phase 16 is not resumable.
6. **The published-pages limb is the common thread across `DOCS-12`, `-13`,
   `-14` and `-15`.** Four rows are short by the same thing: a documentation
   surface for the examples that actually shipped. Rule whether that is one
   piece of work or four.
7. **Nothing here was flipped without evidence, dropped, retired or built.**
   All eighteen ids stay in both ledger channels.
