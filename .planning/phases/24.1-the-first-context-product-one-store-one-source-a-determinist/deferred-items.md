## From plan 24.1-03 (Wave 3) — out of scope, NOT fixed

- **`examples/s1-00-companies-over-revenue/backends.yaml` line 1 declares
  `$schema=../../../../docs/schemas/ccf.declared-artifact.json` — one level too
  deep.** The file sits at depth 2 under the repo root, so the correct prefix is
  `../../`. Measured: the declared path does **not** resolve; the same header at
  the correct depth does. Every `s1-01/artifacts/*.yaml` header is correct, so
  this is one file, not a convention.
  **Pre-existing at `phase-24.1-base` and unrelated to this plan's changes** —
  logged rather than fixed, per the scope boundary. It costs editor schema
  completion in that one file and nothing at runtime; no lint checks it.

---

## From plan 24.1-04 (Wave 4) — out of scope, NOT fixed

### `make ci` has been RED since Wave 3, and the subject is the `artifacts/` directory

**Found** while running `tests/examples` before committing Wave 4.

```
tests/examples/test_artifact_schema_headers.py::test_every_covered_artifact_directory_sits_under_an_example_root
FAILED — covered `artifacts/` directories whose parent is not an example root
         (no `run.py` beside them): cp-00-institutional-holders/artifacts
```

**Not caused by Wave 4, and measured rather than asserted:**

| Tree state | Result |
| --- | --- |
| `examples/cp-00-institutional-holders/artifacts/` **absent** — the `phase-24.1-base` state | **29 passed** |
| **Only** Wave 3's `assembly-recipe.yaml` present — the `bd57821` state, Wave 4's six files moved aside | **1 failed**, 29 passed |
| Wave 4's three further artifacts also present | **1 failed**, 29 passed — the same single failure, not a new one |

`git log --diff-filter=A -- examples/cp-00-institutional-holders/artifacts/`
names **`313d1c0`** — Wave 3, Task 3. The gate has been red from that commit.

**What the gate requires.** `tests/examples/test_artifact_schema_headers.py::bijection_violations`
holds a two-way bijection: every directory containing `artifacts/*.yaml` must
have `tests/examples/test_artifact_schema_headers.py::EXAMPLE_ROOT_MARKER` —
literally a file named `run.py` — directly beside it, and every such root must
have an `artifacts/`. `examples/s1-01-hello-context-product` satisfies it
(`run.py` + `spine.py` + `artifacts/`). `examples/s1-00-companies-over-revenue`
is outside the gate entirely: it has no `artifacts/` — its question document
lives under `scenario/`.

**`cp-00` mixes the two shapes**: `artifacts/` from `s1-01`, and
`produce.py` / `consume.py` / `deployment.py` from `s1-00`.

**Three resolutions, none of them Wave 4's to pick**, because each reaches into
a file list Wave 4 does not own:

1. **`cp-00` gains a thin `run.py` driver**, matching `s1-01`. Cheapest against
   the gate — but `24.1-05` already assigns the driver role to `consume.py`, so
   this renames that file or adds a second driver beside it. A Wave 5 decision.
2. **The artifacts move to `scenario/`**, the `s1-00` shape. Also cheap, but
   `examples/cp-00-institutional-holders/artifacts/assembly-recipe.yaml` is
   cited by path in the spec and in its own header, and the spec is Wave 3's
   committed deliverable.
3. **The marker set widens** beyond `run.py`. That edits a shipped gate, which
   `D-04` and criterion 16 both say this phase does not do.

**Recommendation, offered rather than taken:** option 1, decided by `24.1-05`
when it authors the driver — the only one that changes nothing already
committed and nothing in `src/` or `runtime/`.

**Criterion 19** requires `make ci` green **at the gate commit**, not at every
wave, so this is a phase-close blocker rather than a wave blocker. Recorded here
so it is not discovered at the gate.

### `python -m tools.lints --all` does not gate a citation whose FILE does not exist

Beside `D-42`'s recorded module-alone hole, a second limitation — **stated in
the tool's own source, so this is a bound on what green means and not a defect
report.** Measured, in both a YAML comment and a Python comment, seeded into
Wave 4's own files:

| Seeded citation | `--all` |
| --- | --- |
| `src/ccf/products/gates.py` + `::` + a fabricated symbol name — real file, symbol that does not exist | **rc=1**, named `cite03-node-id` |
| a path under `src/ccf/` that does not exist, + `::` + any symbol | **rc=0** |
| a real directory + a filename that does not exist, + `::` + any symbol | **rc=0** |

`tools/lints/citations.py::check_source` bumps an `unresolved_path` coverage
counter and continues, with the comment *"pointer, so it is unchecked rather
than a finding"* — a cited path may legitimately be an external pointer.

**Consequence a later wave must not forget:** a green `--all` proves the
SYMBOLS resolve in files that exist; it does not prove the FILE PATHS do. Wave 4
checked its own six files' paths with a separate instrument (13 `path::symbol`
citations, 12 resolving, 1 a deliberate forward reference to
`examples/cp-00-institutional-holders/deployment.py::connection` which `24.1-05`
creates). **Not proposed as SDK work** (`D-04`).

**A note on how this entry is written.** The three probes above are spelled as
descriptions rather than as literal citations. Spelling the fabricated one out
turned `--all` red on this very file — which is the rule working, and is itself
the positive control for the first row of the table.

---

## From plan 24.1-05 (Wave 5) — RECORDED, NOT CLOSED (`D-04`)

### The `make ci` gate Wave 4 recorded RED is now GREEN, and by option 1

`D-51` (Dave, 2026-08-26) ruled the resolution Wave 4 recommended: the printed
entry point is named `run.py`, beside `artifacts/`. Measured, unpiped:

| Tree state | `pytest tests/examples/test_artifact_schema_headers.py` |
| --- | --- |
| Wave 4's tree — `produce.py`, no `run.py` | **1 failed, 29 passed** |
| Wave 5's tree — `run.py` present | **30 passed** |

The gate was **not** widened and `artifacts/` was **not** renamed. `tests/examples`
as a whole moves from **484 passed + 1 failed** to **485 passed, 37 skipped**.

### FINDING 1 — a deployment's own operator has no path into the operator plan's registry

`D-48` says step 1's operator is *"registered through the open
`OperatorRegistry`"*. The **registry** is open — `register(operator)` takes any
conforming `Operator` and reads its category off the operator itself. The
**composition path in front of it is not.**

`src/ccf/deployment/operators.py::build_operator_registry` — the builder the
Mode 1 spine calls — dispatches on the *declared parameter artifact's type*
against four known SDK artifact classes and **raises `ValueError` for any type
it does not recognise**, with the message *"names no canonical operator
category; the builder does not guess which operator a deployment meant."* The
spine hands it the whole parameter mapping, so there is no argument, no
override and no second call by which a deployment's own operator reaches the
registry `ProjectionEngine` resolves the plan against.

| Reading | Result |
| --- | --- |
| **FIGURE** the builder handed the example-supplied `Operator` | **REFUSED** — `ValueError`, *"carries a `DominantSecurityResolution`, which names no canonical operator category"* |
| **FIGURE** the builder handed that operator's declared PARAMETER SET instead | **REFUSED** — same `ValueError`, naming `DominantSecurityParameters` |
| **CONTROL** the same builder over the two artifacts `ccf_config.yaml` declares | **registers 2 operators**, `policy.principal-subgraph` and `temporal.as-of-boundary` |
| **CONTROL** `OperatorRegistry.register` called directly with the same operator | **ACCEPTED**, key `traversal.dominant-security`, category `traversal` read off the operator |
| **CONTROL** an operator reporting a category outside the four | **REFUSED** by the registry — *"which is not one of the four canonical categories"* |

**Consequence, taken rather than worked around.** The operator is registered
into the deployment's **own** `OperatorRegistry` and applied at the layer the
specification places step 1 — the source boundary, L1 — and the served
product's `lineage.operators_invoked` still names exactly the two operators the
product class declares. Step 1's runtime witness stays
`payload_key_present: resolved_security`, which is what
`artifacts/assembly-recipe.yaml` already declared for it.

**Classified per `D-08`: use-case agnostic.** Any deployment with an
example-scoped or domain-scoped operator meets this. **Per `D-10` a remedy would
be ADDITIVE** — a way to hand `build_operator_registry` (or the spine) already-
constructed operators alongside the artifact-derived ones — and would open no
new category: `OperatorCategory` stays the closed four. **NOT proposed as SDK
work here** (`D-04`); extension is a separate phase.

### FINDING 2 — `ContextAssemblerProtocol` has no return channel for a governed refusal

This codebase's stated posture is that a refusal is DATA:
`src/ccf/products/request.py::refuse_request` returns a
`src/ccf/products/request.py::ProductRequestViolation` rather than raising,
*"a verdict returned as a value cannot be swallowed by a bare `except`."*

`src/ccf/agents/assembler.py::ContextAssemblerProtocol.assemble` is typed to
return `src/ccf/agents/assembler.py::AssemblyOutcome` **and nothing else**. A
conforming assembler that receives a violation therefore has exactly one way to
report it: raise. Measured — `AssemblyOutcome`'s seven fields are `payload`,
`consultations`, `acquisitions`, `assembler_id`, `assembler_version`,
`skill_set_in_force`, `halflife_debt_profile` — **seven, and none can carry a
refusal.** The contract is `extra=forbid`, so a deployment cannot add one:
constructing it with the seven declared fields succeeds and adding an eighth
named `refusal` raises `ValidationError` naming that field.

The reference implementation does not meet this, and that is why the gap has not
surfaced: `src/ccf/agents/assembler.py::DeterministicAssembler` **holds** Π's
already-computed output, so a request that was never going to be answered has
already been refused somewhere else before it is constructed. An assembler that
actually runs the spine is the first thing to stand where the violation arrives.

`cp-00` raises `src/ccf/agents/errors.py::AssemblyRefused` and hands the typed
violation to its observer first, so the client still renders the refusal from
the value rather than from a message. **Classified `D-08` use-case agnostic**;
a remedy is `AssemblyOutcome | ProductRequestViolation` on the return, which is
**not** additive — it widens a Protocol's return type and every existing caller
would have to branch. **NOT proposed** (`D-04`).

### Spec residues this wave measured and did NOT edit

The specification is Wave 3's committed deliverable and **no plan in this phase
lists it in `files_modified`.** Four items, recorded so they are not discovered
at the gate:

1. **`D-52`'s residue.** `D-52` says the debt bands are confirmed and *"§E stops
   reading `[TBC]`."* Measured: §E.2 still reads *"This product's bands are
   `[TBC]` — §F, marker 16"*. `ccf_config.yaml` carries the confirmed values
   (`0.60` / `0.77`) with their arithmetic; the spec's sentence is stale.
   (25 `[TBC]` in the whole document, 3 inside §E; control token `ZZTBCZZ`: 0.)
2. **§F marker 13 is now MEASURED, and the spec says it is not.** §E.2 reads
   *"Measured value at the anchor: `[TBC]` — §F, marker 13. Not measured, and
   not guessed."* This wave measured it, from the shipped run:
   **C_attributes = 1748/1748 = 1**, C_match = 1633/1748 = 0.9342105…, and the
   delivered `C` equals their product. Controls: an attribute the resolution
   spec does not declare is carried by 0 rows; rows whose band is neither
   `strong` nor `weak`: 0.
3. **§D.2 step 1's SDK-mechanism cell still reads *"no SDK symbol"*.** `D-47`
   does not allow it. `artifacts/assembly-recipe.yaml`'s step 1 was corrected in
   this wave — the artifact is the thing a test reads, and it would otherwise
   have been false of the shipped code — but the prose table in §D.2 and the
   §D.3 paragraph that explains it were not touched. **They are owed the same
   correction and nobody owns the file.**
4. **§F.3 names the database `parkavedb`**, while §0.4's capability-gate note
   says the document *"names no database."* One occurrence, in the
   source-binding section where estate binding legitimately lives, and it is
   neither a host, a port nor a credential — so it is an internal tension in the
   document's own wording rather than a hygiene breach. Sweep over
   `examples/cp-00-institutional-holders/`: `postgresql://` 0, `PGPASSWORD` 0,
   `password=` 0, `dsn:…@` 0, `CODEX_API_KEY` 0, host octets 0, against a
   `from_env` control returning 1 file.

---

## From plan 24.1-07 (Wave 7) — RECORDED, NOT CLOSED (`D-04`)

### FINDING 6 — nothing shipped checks any EXAMPLE for an LLM-client import, and it is TOOLING

**Classification, stated first because `D-05` reads the two lists differently:**
this is in the **TOOLING**, not on the SDK's own surface. It is the second
consecutive tooling finding (Wave 6's fifth was `_is_numeric_table`'s numeric
majority) and it does **not** add to the SDK-side drift signal `D-05` watches.

**Measured, with the instrument named.** `tools/lints/__main__.py::LINTED_TREES`
is `('src','runtime','examples','tests','archive')` — `examples` IS walked. But
`RULE_TREE_SCOPE` scopes each rule, and only `no-hardcoding` names `examples`:

| rule | scope |
| --- | --- |
| `no-hardcoding` | `('src','runtime','examples','tests','archive')` |
| `harness-imports` | `('src','runtime')` |
| **`algorithmic`** | **`('src','runtime')`** |
| `orchestration-imports` | `('src','runtime')` |
| `backend-imports` | `('src','runtime')` |
| `substrate-names` | `('src',)` |

**The control, because a scope table is a claim and not a reading.** An
`import anthropic` was appended to
`examples/cp-00-institutional-holders/produce.py` and `python -m tools.lints
--all` was run: **zero findings naming `anthropic`.** The file was restored
(`git status --short examples/` → 0 modified).

**A trap in that control, recorded because it nearly produced a false reading.**
`--all` is rc=**1** during Waves 7–9 for an unrelated reason — the deliberate
`DOCS-11` citation window this wave opened. **The exit code therefore proves
nothing here.** The valid instrument is the count of findings *naming
`anthropic`*, which is 0. A reader who checked rc alone would have concluded the
opposite of the truth.

**Why it is not simply a scope edit.** `algorithmic` keys off a module-level
`__ccf_mode__ = "algorithmic"` dunder that library modules opt into and example
code does not carry. Adding `examples` to its scope would change nothing until
examples were also tagged, and tagging them is a decision about what an example
IS. So the remedy is a design question, not a one-line widening — and editing a
shipped gate is what `D-04` and criterion 16 both forbid this phase.

**What this wave DID and DID NOT close.** `tests/examples/test_cp_00_is_algorithmic.py`
closes it for `cp-*` and for nothing else. Measured, both directions:

| tree | modules | the new gate |
| --- | --- | --- |
| `examples/cp-00-institutional-holders` | 4 | **COVERED** — a planted `import anthropic` gives **6 failed, 6 passed** |
| `examples/s1-00-companies-over-revenue` | 4 | not covered |
| `examples/s1-01-hello-context-product` | 5 | not covered — a planted `import anthropic` there leaves the gate at **12 passed** |
| `examples/hw1-companies-over-revenue` | 4 | not covered |
| `examples/hw1-harness-clients` | 5 | not covered |

**18 modules across four live example trees remain unchecked for an LLM-client
import by anything in the repository.** Widening `CONTEXT_PRODUCT_GLOB` to reach
them would be a retrofit of existing examples, which `D-07` forbids. Recorded so
it is a decision somebody makes rather than a gap somebody inherits.

**NOT proposed as SDK work** (`D-04`). Not a `D-55` "address as you go" item
either: it is not Protocol-shaped, it blocks no example from being honest, and
`cp-00` — the only tree this phase ships — now carries a recorded compensating
gate, which is exactly `D-56`'s third clause.

### An instrument error caught in-session, recorded because it produced a wrong number

Establishing the pre-edit baselines for `test_spine_separation.py` and
`test_section_one_is_agent_free.py`, the first attempt wrote
`git show 2f57f4f:<path>` into a scratch directory under `/tmp` and collected
from there. It reported **17** and **8** tests. Both modules resolve
`REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]`, so from `/tmp` the
examples tree did not exist, every glob matched nothing, and the parametrized
tests collected empty — a **smaller** number that looked entirely plausible.

Re-measured with the base files placed at their real depth inside
`tests/examples/`: **22** and **16**. Those are the numbers this wave's deltas
are computed against, and the 17/8 reading is recorded rather than discarded
because it is the shape this project's counting errors keep taking — an
instrument that answers without firing.

---

## From plan 24.1-08 (Wave 8) — RECORDED, NOT CLOSED (`D-04`)

### FINDING 7 — criterion 9's dataset statements are gated by NOTHING that ships, and it is TOOLING

**Classification: TOOLING, not the SDK's surface** (`D-04`, `D-56`). It is a
gate that does not exist, in the repository's documentation-checking machinery.
It is **not** an SDK capability gap and must not enter the SDK-side list `D-05`
reads for drift — the same classification the fifth and sixth findings took, and
for the same reason.

`24-CONTEXT.md` `D-35` requires four statements on the README and on the
published page, beside the figures they qualify. This wave put them on both
documents and proved them present with a positive check plus a watched-RED
control per statement. **Nothing in the repository will notice if they are
deleted tomorrow.**

Measured, with the instrument shown to work in both directions:

| Probe | Result |
| --- | --- |
| `grep -rl 'fact about any real company' tools/ tests/` | **0 files** |
| `grep -rn 'D-35\|criterion 9\|educational nature' tools/ tests/` | **4 hits, none of them 24.1's criterion 9** — one is `VAC-05` criterion 9 (phase 21.1) in `tools/docs_tests/test_requirement_ledger.py`, three are Phase 20's `H-07` in `tests/examples/test_hw1_harness_clients_readme.py` |
| **CONTROL** — the same grep over the trees the statements DO live in | **3 files**: the README, the published page, and the specification |
| **CONTROL** — the same instrument over an unrelated concern that IS gated | **53 files** in `tools/`+`tests/` mention the No-Hardcoding Rule |
| **CONTROL** — neighbouring criteria of this phase | `criterion 2` **13 hits**, `criterion 5` **2**, `criterion 8` **2** — so this phase's criteria are reachable by that instrument, and criterion 9's zero is a measurement rather than an instrument failure |

**Why it was not closed in this wave.** A shipped gate on prose sentences is a
design question, not a one-line addition, and it has at least three unresolved
limbs: which documents it scopes to (every `cp-*` README? every page under
`public/` that names an `examples/` figure? both?); how it recognises a
statement without becoming a brittle string match on wording nobody may ever
improve; and whether the four statements are one obligation or four. `D-37`
also bounds THIS phase's proof machinery to one recipe artifact and one test
module, neither of which is this. Recorded so it is a decision somebody makes
rather than a gap somebody inherits.

**What stands in the meantime, stated so it is not mistaken for a gate.** The
wave-time guard lives in this session's scratch space and is **not committed**.
Its shape is written into this wave's SUMMARY so it can be rebuilt: five
patterns over whitespace-flattened text, an exactly-once assertion per pattern
(a statement present twice makes its own control unable to fire), and one
watched-RED control per pattern that deletes the sentence carrying it and
requires the same predicate to name **that** statement and only that one.

### Not a finding — an example-local coupling, resolved in-wave and named so it is not rediscovered

`examples/cp-00-institutional-holders/backends.yaml`'s remedy string, authored
before the README existed, tells an operator to *"see the example README's
'Before you run' section."* The Phase-13 template fixes **seven** `## ` heading
names and *Before you run* is not one of them; an eighth `## ` fails
`tests/examples/test_cp_readme_template.py::test_every_context_product_readme_matches_the_template`.

Resolved by writing *Before you run* as a `### ` **sub-heading** under
`## Run it`. The template predicate reads lines beginning `## ` only — its own
docstring says *"`### Foo` does not start with `## `, so sub-headings are out of
scope"* — so the remedy string now points at a section that exists, and the
template is satisfied rather than relaxed. Neither the artifact nor the gate was
edited.
