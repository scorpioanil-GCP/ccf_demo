# Phase 16: Documentation Rewrite — The Deterministic Path & The Adoption Argument - Pattern Map

**Mapped:** 2026-08-13 (rewrite; supersedes the 2026-08-10 map)
**Tree state:** `main @ 6e95da0` — the `--no-ff` merge of `phase-15.6`
**Files in scope:** 14 file groups for the narrowed phase, 9 carried to 16.1
**Analogs found:** 13 / 14 in-scope (1 NO ANALOG); 0 dropped for absence

> **What this file is for.** `16-RESEARCH.md` (rewritten the same day) establishes
> *what* the narrowed Phase 16 builds and what it must not break. This file answers
> the one question it does not: **"which existing file does an executor open, and
> what does it copy?"** Every excerpt below was read out of the tree at `6e95da0`
> in this session. Nothing is carried forward unverified from the 2026-08-10
> version. Where nothing exists to copy, the entry says `NO ANALOG`.

---

## 0. Why this file was rewritten, and what changed

The 2026-08-10 map was written against the pre-15.5 surface and against the
full 21-plan Phase 16. Two things then happened: Phase 15.5 (2026-08-11) and
15.6 (2026-08-13) landed, and Dave narrowed the phase on 2026-08-13.

### 0.1 The narrowing — LOCKED, and it is what this map is scoped to

`16-RESEARCH.md` §*User Constraints*, R-1..R-4 (Dave, 2026-08-13):

- **R-1** — Phase 16 = the five shipped infrastructure plans (`16-01`, `16-03`,
  `16-04`, `16-06`, `16-21`) **plus one Hello CCF example**. Sections 2 and 3,
  the six-backend matrix, the terminal retirement of `examples/00`–`08` and the
  full adoption-argument treatment **defer to Phase 16.1** with criteria intact.
- **R-2** — one backend, `sqlite`, no DGX legs.
- **R-3** — the example ships with its Section-1 published pages.
- **R-4** — `DI-15.6-01(b)` is discharged in this phase.

**The ROADMAP entry (`.planning/ROADMAP.md:1155-1291`) still lists 21 plans and
still names the six-backend matrix in criterion 4.** That is `16-RESEARCH.md`
§7 Q-4, unresolved. This map is organized against the narrowing, with §5 holding
verified analog pointers for the nine deferred groups so 16.1's planner does not
re-derive them.

### 0.2 A finding I was asked to record that does **not** reproduce — REJECTED

I was told the previous map cited eleven `.py` paths that do not exist, eight of
them spelled `tests/test_*.py` where the file actually lives under
`tools/docs_tests/` or `tools/publish_scan_tests/`. **I grepped the file. It does
not.** The 2026-08-10 map spells all eight with their correct `tools/…` prefixes
at its lines 25-30, 243-245, 294, 341, 424, 463, 1211-1212 and 1281. There was no
`tests/` → `tools/` path rot to correct.

Recording it as rejected rather than silently dropping it, per CLAUDE.md §3.1:
*"record the ones you reject as rejected."* This project has produced three
reviews carrying confident false findings; an unverified finding acted on is
worse than no review.

**What was actually wrong with those eleven entries is different, and worse for a
planner:** *six of the eight files the map described as "new files to be created"
have since shipped.* An executor reading the old map would rebuild them.

| Old map called it | Reality at `6e95da0` |
|---|---|
| `tools/docs_tests/test_no_stale_example_paths.py` — new | **SHIPPED**, 308 lines (`16-04`) |
| `tools/docs_tests/test_gate_two_wording.py` — new, "composite, NO ANALOG" | **SHIPPED**, 304 lines (`16-04`) |
| `tools/docs_tests/test_advisory_discharge.py` — new | **SHIPPED**, 533 lines (`16-06`) |
| `tools/docs_tests/test_documented_commands_exist.py` — new | **SHIPPED**, 245 lines (`16-04`) |
| `tests/examples/test_spine_separation.py` — new | **SHIPPED** (`16-05`) |
| `tests/examples/test_section_one_is_agent_free.py` — new | **SHIPPED** (`16-05`) |
| `tools/docs_tests/test_adoption_argument.py` — new | still absent — **deferred to 16.1 with the adoption page (R-1)** |
| `tests/examples/test_backend_matrix.py` — new | still absent — **deferred to 16.1 with the matrix (R-1)** |

The old map's § *No Analog Found* row for *"a paragraph-scoped assertion over
`public/**/*.md`"* is likewise closed: `tools/docs_tests/_prose.py` (262 lines)
was extracted for exactly that, and its module docstring at `:5-12` cites this
document by name as the reason it exists. **That is now an analog, not a gap.**

### 0.3 The `tools/` CI-reachability fact — verified, and it is load-bearing

`pyproject.toml:142` is `testpaths = ["tests"]`. A bare `pytest` therefore never
reaches `tools/`. `Makefile:70` is `ci-core: lint typecheck test` and
`Makefile:81` is `ci: ci-core examples docs-strict` — **`make ci` reaches none of
the three gate-checker suites.** GitHub Actions reaches two of them, as separate
explicit steps:

- `.github/workflows/ci.yml:35` — `pytest tools/lints/tests -q`
- `.github/workflows/ci.yml:314` — `pytest tools/publish_scan_tests tools/docs_tests -q`

Measured this session:

```
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/ -q
→ 4 failed, 540 passed in 25.04s
```

**Every entry below that names a gate under `tools/` says so and says what it
implies for CI reachability.** Dave named `testpaths = ["tests"]` explicitly at
the 15.6 gate as *"the mechanism that let a red gate package survive a phase
boundary"* (`DI-15.6-01(b)`), and Phase 16 owns discharging it.

### 0.4 Surface changes confirmed against the code

| Claim | Verified at | Verdict |
|---|---|---|
| `ContextProductContract` gained three top-level members | `src/ccf/products/contract.py:673-676` — `debt_evidence`, `source_refresh_recency`, `obligation_in_force` (plus `debt` at `:672` from 15.5) | ✅ |
| `Observation` gained identity | `src/ccf/halflife/decay.py:188` — `subject: str = NO_SUBJECT_IDENTITY` | ✅ |
| `DebtAssessment` evidence carries a sentinel and no pointers | `examples/s1-01-hello-context-product/deployment.py:305-340` returns `NO_DEBT_EVIDENCE`, docstring quotes `D-IMPL-119` limb 3(b) verbatim | ✅ |
| Source refresh is a window publishing no source identity | `deployment.py:634-676` `_declared_refresh_window() -> SourceRefreshWindow` | ✅ |
| `DeploymentBinding` was deleted at `6b87a8f` | `git grep DeploymentBinding -- src/ runtime/ examples/` → **no hits**; `spine.py:123` declares one Protocol, `Scenario` | ✅ — the old map never cited it, so nothing to drop |
| The product content address has no in-tree literal in Phase-16 work | `examples/s1-01-hello-context-product/` pins none; `tests/examples/test_s1_01_output.py` computes both sides | ✅ — **no problem to manufacture** |
| Backend registration seam + Fluree adapter shipped | `src/ccf/graph/registry.py:624` `declared_names()`; `src/ccf/graph/backends/fluree.py` exists; `tests/conftest.py:229/234/237`; `pyproject.toml:148`; `Makefile:146/152/166` | ✅ — but **deferred to 16.1 by R-2**; see §5 |

### 0.5 Three claims in `16-RESEARCH.md` that do **not** reproduce

Recorded so a planner does not build on them.

1. **`ccf.deployment.__all__` has 16 names, not 17.** Research §2.4 says
   *"exports 17 names"*. Measured: `len(ccf.deployment.__all__) == 16`
   (`src/ccf/deployment/__init__.py:127-144`). The published page is **correct**
   — `public/reference/artifacts/deployment-manifest.md:19` says *"sixteen
   names"*. Do not "fix" the page to match the research.
2. **`public/concepts/pillars/data-context.md` has no line 133.** Research §3.2
   says it *"buries the SDK-ships-no-agents line at 133"*. The page is **105
   lines**. The G-01 opening defect *is* real and verified — line 4 reads *"how
   does an agent get at first-party records"* — but the buried-line evidence is
   Phase-14-era and the sentence now lives at
   `public/tutorial/adopters-guide.md:161` (*"It ships no agents at all"*) and
   `public/concepts/pillars/agent-types.md:61`.
3. **`tools/docs_tests/test_snippet_gate.py` is no longer mis-pointed.** The old
   map's terminal warning said two of its three tests fail at HEAD against a
   removed `[start:ontology]` marker. `test_snippet_gate.py:38-50` records that
   the constants were repointed to `[start:boot]` and the whole module passes.

---

## 1. File Classification — the narrowed phase

### Group A — new published pages (R-3)

| File to create | Role | Data flow | Closest analog in the tree today | Match |
|---|---|---|---|---|
| `public/tutorial/hello-ccf.md` | doc (tutorial) | snippet-include over a running example | `public/tutorial/adopters-guide.md` | **exact (form)** |
| `public/how-to/assemble-a-context-product.md` | doc (how-to) | numbered steps, marker + whole-artifact include pairs | `public/how-to/grant-and-revoke-a-skill.md` | **exact** |
| `public/concepts/context-graph-axes.md` | doc (concept) | promise / why / enforcement per axis | `public/concepts/invariants.md` (form only) | role-match — **content is NO ANALOG** |

### Group B — published pages to correct

| File to modify | Role | Why | Closest current-surface analog | Match |
|---|---|---|---|---|
| `public/concepts/pillars/data-context.md` | doc (concept) | G-01: opens agent-first at `:4` | `public/reference/artifacts/deployment-manifest.md` (the tree's most recent, post-15.4 reference prose) | role-match |
| `public/reference/protocols/context-products.md` | doc (reference) | 29 lines; prose names three gates only, no request contract / payload schema / entitlement / debt | `public/reference/artifacts/deployment-manifest.md` | **exact** |
| `public/reference/artifacts/product-registration.md` | doc (reference) | `RegisteredProductClass` gained eight fields in 15.5 | itself (structure is right, content is stale) | **exact** |
| `public/reference/protocols/halflife-and-debt.md` | doc (reference) | 18 lines, six `:::` directives, no `DebtAssessment`, no `SourceRefreshWindow`, no worked example | `public/reference/artifacts/control-plane-artifacts.md` (`:::` + worked-example shape) | **exact** |
| `public/reference/artifacts/control-plane-artifacts.md` | doc (reference) | needs `DebtProfile.signal_obligations` (15.6-08) | itself | **exact** |
| `mkdocs.yml` `nav:` | config | three new pages must be enumerated | `mkdocs.yml:113-166` | **exact** |

### Group C — gate and CI work (DOCS-08, `DI-15.6-01(b)`, A-3 floor)

| File to modify | Role | Data flow | Analog | Match |
|---|---|---|---|---|
| `tools/docs_tests/test_advisory_discharge.py` `A3_REQUIRED_TOKENS` | test (gate control) **— under `tools/`, NOT in `make ci`** | tuple-of-strings floor | itself, `:96-105` | **exact** |
| `Makefile` `ci:` composition | config | — | `Makefile:81` + `.github/workflows/ci.yml:35,314` | **exact** |
| `src/ccf/{deployment/binder,halflife/assessment,halflife/debt,products/composition,products/request}.py` module docstrings | source (docs only) | transform | each other; the rule is in `tools/publish_scan_tests/test_docstring_leaks.py:9-12` | **exact** |

### Group D — the example, if `16-05` Task 3 is re-scoped (Q-3, Dave's)

| File | Role | Data flow | Analog | Match |
|---|---|---|---|---|
| `examples/s1-01-hello-context-product/{spine,deployment}.py` | example code | request-response | **itself — it is the reference**; no better analog exists | n/a |

---

## 2. Pattern Assignments

### A1. `public/tutorial/hello-ccf.md` (new, tutorial)

**Analog:** `public/tutorial/adopters-guide.md:1-40`.

⚠ **Copy its form; do not edit the file.** It is 447 lines, includes from six
examples that retire in 16.1, and is `16-18`'s terminal-wave property.

The opening contract to restate — the *"nothing here is pasted"* promise is what
makes a docs page a gate rather than a claim (`adopters-guide.md:9-18`):

```markdown
Every block of code and every artifact on this page is **literal-included
from an example the CI pipeline runs**. Nothing here is pasted, so nothing
here can drift: if one of these sources moves, this page fails to build. Each
section names the one command that runs its example, so you can reproduce
what you are reading as you read it.

The through-line to keep in view: the code you see is thin, generic
machinery, and everything specific to a deployment lives in versioned
definition artifacts.
```

**The seven marker regions this page includes from are verified present** in
`examples/s1-01-hello-context-product/spine.py`, in order:

| marker | line |
|---|---|
| `boot` | `:295`–`:306` |
| `ingest` | `:331`–`:338` |
| `operators` | `:340`–`:359` |
| `project` | `:361`–`:395` |
| `gate` | `:397`–`:547` |
| `record` | `:549`–`:575` |
| `serve` | `:577`–`:603` |

`tests/examples/test_spine_separation.py` asserts both the ordering and the
closure — seven names and no eighth. Include form is
`--8<-- "examples/s1-01-hello-context-product/spine.py:boot"`;
`mkdocs.yml:95` sets `check_paths: true`, so a mistyped marker fails the strict
build rather than rendering an empty block.

**This page is the thing that turns two of the four red `tools/` tests green.**
`test_documented_commands_exist.py::test_every_composed_example_target_is_documented`
fails at HEAD with exactly one offender:

```
AssertionError: these example targets run in CI but no published page names them —
they are maintained, tested, and unfindable: example-s1-01
```

The gate reads `make <target>` **only from inline code spans and fenced blocks**,
never running prose (`test_documented_commands_exist.py:23-31` records the
measurement: 24 candidates with 7 false positives → 17 targets with none). So the
page must write the command as `` `make example-s1-01` `` or in a fenced `sh`
block. A sentence saying "run the s1-01 example" does not discharge it.

---

### A2. `public/how-to/assemble-a-context-product.md` (new, how-to)

**Analog:** `public/how-to/grant-and-revoke-a-skill.md` (126 lines) — the closest
structural match in the published tree, and the shape transfers whole.

The shape, verified section by section:

1. Intent paragraph (`:3-6`).
2. **"The single assertion worth carrying away"** (`:11-13`) — one sentence
   naming the property the page exists to establish.
3. Include-provenance line (`:15-16`): *"Everything below is literal-included
   from `examples/02-skilling`, which runs in CI on every commit."*
4. `## Before you start` (`:18`) with the run command in a fenced `sh` block
   (`:28-30`) and what exit 0 means (`:32-33`).
5. Numbered `## Step N — <verb>` sections, each pairing one whole-file YAML
   include with one marker include:

````markdown
```yaml
--8<-- "examples/02-skilling/artifacts/skill-catalog-enrollment-metrics.yaml"
```

The driver registers what the artifact declared. Note that registration binds
nothing — a catalog entry is an offer, not a capability:

```py
--8<-- "examples/02-skilling/run.py:skill-catalog"
```
````

6. `## What to change first` (`:109`) — naming the artifact an adopter edits
   first and what happens when they do.

**This is G-01's named gap** — the UAT found no how-to for deterministic Context
Product assembly. The step sequence is the spine's seven markers; the artifact
side is the nineteen documents under
`examples/s1-01-hello-context-product/artifacts/` (verified: `manifest.yaml`,
`product-class.yaml`, `product-governance.yaml`, `request-contract.yaml`,
`questions.yaml`, `projection-requirements.yaml`, `perspective.yaml`,
`policy-bundle.yaml`, `resolution-spec.yaml`, `half-life-table.yaml`,
`debt-profile.yaml`, `events.yaml`, `source-estate.yaml`, `ubo-question.yaml`,
`expected.yaml`, and four `operator-parameters-*.yaml`).

⚠ **Gate-2 wording is machine-enforced on this page.** See § *Shared Patterns →
The Gate-2 gate*.

---

### A3. `public/concepts/context-graph-axes.md` (new, concept)

**Analog (form only):** `public/concepts/invariants.md`. **Content: NO ANALOG** —
see § *No Analog Found*.

The per-item triple to reproduce (`invariants.md:12-33`):

```markdown
## Single writer to the graph

**The promise.** Exactly one component holds a write handle to the Context
Graph: L2 Context Assembly. Nothing else can write, under any circumstance.

**Why the architecture forces it.** Lineage is only trustworthy if every
assertion in the graph passed through the one place that stamps policy bindings
and resolves entities and time. ...

**How it is enforced.** The reader and writer are separate protocols, and the
writer handle is supplied by dependency injection at boot — a read-path
constructor is never given one, so a direct write is not merely forbidden but
unrepresentable. ...
```

Its framing sentence is the standard to hold each axis to (`:8-10`):

> *"An invariant with no named enforcement is an aspiration, and the SDK does not
> ship those."*

For a six-axes page the analogous discipline is: **each axis names its observable
surface in the shipped code**, not a definition. The spine gives six ready
anchors — `E`/`R` at `spine.py:344` (`reader.as_of`), `T` at `:345`
(`temporal_boundary`), `P` at `:449` (`booted.pins.version_for(policy_bundle_key)`),
`Π` at `:372-394` (`plan_class` → `ProjectionEngine.execute`), `L` at `:463-467`
(`ProductLineage`).

The page may embed a mermaid diagram the same way `invariants.md:31-33` does;
`public/diagrams/` sources are already allowlisted for include
(`tools/publish_scan.py:104-108` permits `public/`).

---

### B1. `public/concepts/pillars/data-context.md` (modify — the G-01 fix)

**The defect, verified at `:3-6`** — this is the page's *first sentence*:

```markdown
This pillar is where the fabric earns its name. It is the SDK's answer to a
single question: *how does an agent get at first-party records, third-party
feeds, and material produced by other agents — in a form that is typed, fresh
enough to act on, governed, and reconstructible afterwards?*
```

`D-12` closes this **by construction**: Section 1 is agent-free, so the opening
question becomes a question about *assembly*, not about an agent's access.

**What is already correct on the page and must survive the edit** — `:20-30`
already states derivation-not-storage, modelled decay, and single-writer, and
`:38-45` carries the L1–L6 table. The mermaid include at `:58-60` and the
artifact-store seam include at `:74-76` are live diagram couplings; moving them
breaks `tools/docs_tests/test_diagram_coverage.py`'s bijection (that gate is
**under `tools/`, so `make ci` will not catch it** — CI step `ci.yml:314` will).

**Prose analog for the rewrite:** `public/reference/artifacts/deployment-manifest.md`
is the tree's newest page written against the post-15.4 surface (created by
`16-06`) and is the right register — declarative, mechanism-first, with the
subtlety stated in full rather than gestured at. Its `:56-64` paragraph is the
model for saying a hard thing completely:

```markdown
The subtlety that has to be stated in full, because half of it misleads: a
`role: load` artifact **is** returned to the caller on `BootedFabric.artifacts`,
keyed by its manifest key, exactly as a `role: register` one is — **and** it is
still absent from `pins`, still absent from the Control Plane registry, and
still absent from replay dimension 2.
```

---

### B2. `public/reference/protocols/context-products.md` (modify — 29 lines, stale prose)

**The stale prose, verbatim at `:3-7`** — it frames the whole product surface as
the three gates and names nothing from 15.5/15.6:

```markdown
The Context Product Contract is the SDK's stable wire surface: everything that crosses a
process, a harness or an organizational boundary crosses as one of these. `CCFContract` is the
typed base every contract inherits. The gate surfaces below are the three validation gates a
product must clear before the delivery layer will serve it — an empty operator plan, a lineage
mismatch and a TTL breach are each a refusal, never a warning.
```

**What must be added, verified in the code** — `src/ccf/products/contract.py:664-676`:

```python
    schema_name: str
    schema_version: str
    plan_id: str
    tenant_id: str
    temporal_boundary: datetime
    expires_at: datetime
    ttl_anchor: TTLAnchor
    lineage: ProductLineage
    payload: Mapping[str, Any]
    debt: DebtAssessment | None = None
    debt_evidence: DebtEvidence = NO_DEBT_EVIDENCE
    source_refresh_recency: SourceRefreshRecency = NO_SOURCE_REFRESH_RECENCY
    obligation_in_force: ObligationInForce = NO_OBLIGATION_IN_FORCE
```

⚠ **Three prohibitions this page must respect, all ruled.**

1. **`debt_evidence` is a carrier holding a sentinel, not a feature.**
   `D-IMPL-119` limb 3(b) forbids populating it. The page must not describe a
   surface in which debt points at named observations today. The reasoning to
   cite is written in the tree at `deployment.py:305-340`.
2. **`source_refresh_recency` publishes no source identity and no count**
   (`D-IMPL-124` Shape B). The per-source map was deleted deliberately.
3. **There is no fourth gate.** `run_gates` is untouched; payload-schema
   conformity is checked at bind, not at a gate (`D-IMPL-102` limb 3).

**Structural analog:** the page's own existing cross-link discipline at `:15-19`
is correct and must be preserved verbatim in spirit — rendering
`RegisteredProductClass` on two pages gives one identifier two primary URLs,
which `strict: true` (`mkdocs.yml:22`) refuses.

---

### B3. `public/reference/protocols/halflife-and-debt.md` (modify — 18 lines)

**Analog:** `public/reference/artifacts/control-plane-artifacts.md` — the
`:::`-directives-then-`## Worked examples` shape, at `:11-43`:

```markdown
::: ccf.controlplane.artifacts.DeclaredArtifact

::: ccf.controlplane.artifacts.HalfLifeTable

## Worked examples

Each artifact class is its own document. A file is not an artifact: the two
calibrations below are separate classes with separate version lanes, so they
are separate documents, each validated closed-world against its own contract.

The half-life table:

```yaml
--8<-- "examples/00-quickstart/artifacts/half-life-table.yaml"
```
```

⚠ **The include target is a live coupling.** Both this page and
`product-registration.md` currently include from `examples/00-quickstart/artifacts/`.
`examples/00-quickstart` does **not** retire this phase (terminal retirement is
`16-18`, deferred to 16.1), so re-cutting at
`examples/s1-01-hello-context-product/artifacts/` is a choice, not an obligation
— but if a page is re-cut, `tools/docs_tests/test_no_stale_example_paths.py`
verifies both the include half and the running-prose half, and it is **under
`tools/`, not in `make ci`**.

**What the current page omits, verified:** it renders six symbols
(`Observation`, `effective_half_life`, `context_debt`, `DebtFactors`,
`DebtSignal`, `DebtFactorScorerProtocol` at `:8-18`) and names none of
`DebtAssessment`, `DebtEvidence`, `SourceRefreshWindow`, `ObligationInForce`, or
`Observation.subject` (`src/ccf/halflife/decay.py:188`).

---

### C1. `tools/docs_tests/test_advisory_discharge.py` — widening the A-3 floor

**Analog: itself.** The floor is one tuple, verified at `:96-105`:

```python
#: A-3's floor: the published tree must speak the vocabulary of the surface
#: that shipped in Phases 15.2–15.4. Every one of these was measured at **zero**
#: occurrences across `public/` when the audit was written.
A3_REQUIRED_TOKENS: tuple[str, ...] = (
    "load_and_boot",
    "backend",
    "ccf backends",
    "GraphQuery",
    "registry",
)
```

Every token is 15.2–15.4 vocabulary. The gate passes today over a tree that says
nothing about 15.5 or 15.6. **`16-06` discharged A-3 correctly against the surface
at its own HEAD; the surface then moved.** Widening the tuple is the whole edit.

**The measured vocabulary gap the widened floor should close** (research §3.3,
occurrences across all 43 pages of `public/`): `ProductRequest` **0**,
`refuse_request` **0**, `payload schema` **0**, `SourceRefreshWindow` **0**,
`ContextAssembler` **0**, `entitlement` 1, `DebtAssessment` 1, `assembler` 1.

**The module's own two shape conventions to preserve** (`:32-48`): a floor that
would rot silently is refused in favour of a run-time comparison against
`inspect.signature`, and non-vacuity is proven by an injecting control rather
than by a corpus floor. A widened tuple inherits neither property, so the
widening must come with its control — see § *Shared Patterns → Negative controls*.

⚠ **CI reachability.** This file is under `tools/docs_tests/`. `pyproject.toml:142`
(`testpaths = ["tests"]`) means `make ci` never runs it. Only
`.github/workflows/ci.yml:314` does.

---

### C2. `Makefile` — the `ci:` composition (DOCS-08, the option-(b) remedy)

**Analog:** the target as it stands, `Makefile:70` and `:81`:

```make
ci-core: lint typecheck test ## Mid-phase verification sweep — MUST stay green from Wave 1 onward

ci: ci-core examples docs-strict ## Full local reproduction of the always-on pipeline (D-10)
```

**The command string to compose in** is the one CI already runs, so the two stay
identical command-for-command (D-10). `.github/workflows/ci.yml:34-35`:

```yaml
      - name: Lint checker unit tests (CINV-01/02/03 + citations)
        run: pytest tools/lints/tests -q
```

and `ci.yml:313-314`:

```yaml
      - name: Docs-gate checker unit tests (publish scan + docs gates)
        run: pytest tools/publish_scan_tests tools/docs_tests -q
```

Both CI steps carry the same comment, and it is the sentence that documents the
hole (`ci.yml:307-310`):

```yaml
      # The docs checkers are the enforcement mechanism for the publish gate,
      # so they are themselves tested in CI. `pytest tests` in the test job does
      # not reach them (testpaths is the shipped suite and stops at `tests`);
      # run them here, before the gate they implement.
```

⚠ **The sequencing hazard, measured.** Composing all three suites into `make ci`
turns the *other* failures red inside `make ci`. At `6e95da0` there are four:

| Failing test | Owner |
|---|---|
| `tools/publish_scan_tests/test_docstring_leaks.py::test_no_docstring_reproduces_whitepaper_body_text` | **`DI-15.6-01(b)` — this phase (C3)** |
| `tools/docs_tests/test_documented_commands_exist.py::test_every_composed_example_target_is_documented` | closes as a side effect of **A1** |
| `tools/docs_tests/test_documented_commands_exist.py::test_the_gate_refuses_an_undocumented_composed_example` | same — it depends on the same corpus |
| `tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current` | `DI-15.6-02`, deferred to 16.1 |

So the residual after this phase's own work is **one row**, not three
(research assumption A3, now measured). This is research §7 Q-1's decision.

**Precedent for how a target legitimately joins `ci`** — `Makefile:76-80` records
that `docs-strict` joined *"never as a half-armed or dead target"*, which is the
standard the new composition must meet.

---

### C3. The five module-docstring leaks (`DI-15.6-01(b)`, the closure half)

**The gate that finds them** — `tools/publish_scan_tests/test_docstring_leaks.py`,
226 lines. Its rule is the one constraint on the fix (`:9-12`):

```python
Rewriting a docstring to pass this test must never mean deleting its
whitepaper section citation — CLAUDE.md §11 requires the citation, and trading
a leak for a fidelity defect is not a fix.
```

**Why it is not in a blocking gate, in the gate's own terms.** It walks *every*
docstring under `src/` and `runtime/` (`:30-43`, `DOCUMENTED_TREES = ("src", "runtime")`)
— module, class/function, PEP-258 attribute (`:46-53`) and `#:` runs. The three
scanners that *are* blocking read the published tree, the 26 committed JSON
schemas, and the built site (`Makefile:271-274`). **The two do not disagree about a
shared surface; they cover different surfaces, and the wider one does not block.**

**The five, reproduced this session:**

| File | Node | Hits | Module docstring spans |
|---|---|---|---|
| `src/ccf/deployment/binder.py` | `<module>` | 7 | lines 1–153 |
| `src/ccf/halflife/assessment.py` | `<module>` | 15 | lines 1–96 |
| `src/ccf/halflife/debt.py` | `<module>` | 14 | lines 1–68 |
| `src/ccf/products/composition.py` | `<module>` | 3 | lines 1–108 |
| `src/ccf/products/request.py` | `<module>` | 1 | lines 1–93 |

**What a leak actually looks like** — run through `scan_text` with
`whitepaper_shingles()` this session:

```
src/ccf/products/request.py:1 pub01-whitepaper-shingle reproduces whitepaper body text:
    'the difference between the verb aggregate and the verb assemble'
src/ccf/products/composition.py:1 pub01-whitepaper-shingle reproduces whitepaper body text:
    'refuses to assemble a product that silently mixes the two'
src/ccf/products/composition.py:1 pub01-whitepaper-shingle reproduces whitepaper body text:
    'temporal validation refuses to assemble a product that silently mixes'
```

⚠ **The `request.py` phrase is also in `spine.py:15`** — *"the difference between
the verb aggregate and the verb assemble"*. The gate does not scan `examples/`,
so it does not fire there, but a phase closing this leak in `src/` and leaving the
identical sentence in an example is closing half of it. Verify before deciding; it
may be in scope, it may be 16.1's.

**`D-IMPL-96` (Dave, 2026-08-10) revoked the "no fabric changed" wording**, so a
docstring rewrite in `src/` needs no carve-out and `D-13`'s exception is void
along with it. ROADMAP criterion 10 now reads *"changes to the fabric itself are
permitted and expected where this phase finds a defect."*

---

### D1. `examples/s1-01-hello-context-product/` (the reference; no better analog exists)

If `16-05` Task 3's checkpoint is re-scoped (research §7 Q-3, Dave's call), the
modules it reads are 615 + 811 lines and have changed under six plans since the
checkpoint was written.

**The `D-11` separation, stated in the file itself** — `spine.py:18-33`, and this
is the sentence any published page describing the split should quote rather than
paraphrase:

```python
**This file is the fabric's half of answering it.** [MECHANISM] The CCF call
spine — every line here is a fabric call an adopter must make. Which company,
at which instant, under which threshold, and which resolved class counts as a
natural person are none of its business.

[ADAPT] nothing. There is no domain vocabulary in this file: no entity class, no
source system, no identifier, no threshold, no policy version, no query and no
boundary. Everything specific to *this* deployment lives in ``deployment.py``
beside it, and in ``artifacts/*.yaml`` beside that.

That separation is the point of this example (phase 16 CONTEXT `D-11`). The
complaint it answers is a reader's, in a reader's words: *"I can't tell from
looking at the code which code is example code and which code is required by
the CCF."*
```

**`Scenario` is the only Protocol** (`spine.py:123`) and the two modules are held
together structurally (`:57-62`): *"``deployment.py`` imports nothing from this
module and this module imports nothing from it."* The `16-05-SUMMARY.md` claim of
two Protocols including `DeploymentBinding` is **false at HEAD** — that class was
deleted at `6b87a8f`.

**The assertion ban** (`spine.py:69-70`): *"This file asserts nothing and prints
nothing. Its assertions live in ``tests/examples/test_s1_01_output.py``."*

---

## 3. Shared Patterns

### The Gate-2 gate — applies to every page this phase writes

**Source:** `tools/docs_tests/test_gate_two_wording.py` (304 lines, shipped by
`16-04`). ⚠ **Under `tools/` — `make ci` does not run it; `ci.yml:314` does.**

This is a **standing** gate whose subject is pages that do not exist yet
(`:16-22`): *"A one-off sweep protects the tree it swept; a gate protects
everything written afterwards."*

Two assertions, deliberately different in shape (`:56-86`):

```python
GATE_TWO = re.compile(r"INV-CH7-47|lineage strict equality|\bGate 2\b", re.IGNORECASE)
CORRECTION = re.compile(r"assembly-path integrity", re.IGNORECASE)
CHARACTERIZES = re.compile(
    r"\b(?:verif(?:y|ies|ying)|establish(?:es|ing)?|prove[sd]?|proving"
    r"|witness(?:es|ing)?|confirm(?:s|ing)?|guarantee(?:s|ing)?"
    r"|attest(?:s|ing)?|demonstrat(?:e|es|ing))\b", re.IGNORECASE)
INDEPENDENCE = re.compile(r"\bindependent(?:ly)?\b", re.IGNORECASE)
```

**Practical rule for an author:** a paragraph that *characterizes* what Gate 2
verifies must contain the literal phrase **"assembly-path integrity"**, or state
the point in the negative with a word-bounded negation in the same *sentence*.
A bare enumeration of the three gates is exempt by design (`:37-43`) — two
paragraphs in `public/concepts/invariants.md` and
`public/concepts/replay-anatomy.md` rely on that exemption today.

**The canonical wording to copy, never paraphrase** — `spine.py:441-448`:

```python
        #    What Gate 2 then verifies is ASSEMBLY-PATH INTEGRITY: the claim
        #    transcribed into this Contract equals the engine's execution of the
        #    plan. The engine is a faithful TRANSCRIBER of the plan rather than
        #    an independent witness of it — it builds `operators_invoked` and
        #    `steps` in one loop over the same operator plan, so there is no
        #    return path where invoked != planned. Gate 2 therefore does not
        #    catch a producer misdeclaring. Authorable drift fails upstream
        #    instead, at the binder call in step 5.
```

**The already-published form**, `public/reference/artifacts/product-registration.md:25-28`:

> *"Gate 2 sits downstream of both and verifies assembly-path integrity — the
> engine transcribes the plan faithfully rather than witnessing it independently,
> so it cannot catch a misdeclaration (`D-IMPL-86`)."*

---

### Paragraph scoping — `_prose.py` is the shipped helper; do not re-derive it

**Source:** `tools/docs_tests/_prose.py` (262 lines). **This closes the old map's
`NO ANALOG` row.** Its docstring at `:5-12` cites that row by name.

`REPO_ROOT` resolves from the file, never the CWD (`:64`) — the WR-04 failure.
`PUBLIC_DIR` at `:68`. The API a new gate uses:

| Symbol | Line | What it gives you |
|---|---|---|
| `Paragraph` | `:83` | `text` (markup-stripped, **casing preserved**), `lineno`, `raw` (nothing stripped), `fenced`, `info` |
| `paragraphs(text)` | `:129` | every paragraph of one page, fences emitted whole |
| `sentence_at(text, offset)` | `:209` | the sentence carrying a match — scoping a qualification to the claim's own sentence |
| `published_pages(root=None)` | `:224` | every `.md` under `public/` |
| `iter_paragraphs(pages, *, prose_only=True)` | `:235` | `(page, paragraph)`, skipping fences for a *wording* gate and not for a *command* gate |
| `relative(path)` | `:252` | repo-relative POSIX for a failure message |

Three properties a new gate must not accidentally undo:

1. **Casing is preserved** (`:38-43`) — matching is case-insensitive at the call
   site; lowercasing the corpus makes it impossible to report an offending phrase
   as the page spells it.
2. **Fenced blocks are marked, not dropped** (`:45-49`) — a wording gate skips
   them, a command gate reads them.
3. **`raw` vs `text`** — `test_no_stale_example_paths.py:50-53` records the one
   gate that wants `raw`: a path in prose is almost always an inline code span,
   and `text` strips code spans by design, so scanning `text` "would find
   approximately nothing and report green forever."

**The warning sign, in the module's own words** (`:33-36`): *"A plan step spelled
``grep -rn "<phrase>" public/`` is the thing this module exists to remove."*

---

### Negative controls — apply to every gate this phase widens

**Sources, both verified:**
- `tools/docs_tests/test_openapi_drift_control.py:50-74` — both polarities on
  every run, victim chosen as *whichever path sorts first, never a literal
  endpoint name*, so route churn cannot turn the control into a no-op.
- `tools/docs_tests/test_documented_commands_exist.py::test_the_gate_refuses_an_undocumented_composed_example`
  — mutates the Makefile text **in memory rather than on disk**.

**Apply to:** the widened `A3_REQUIRED_TOKENS`. A widened matcher with an
unwidened control is a widening nobody proved.

---

### Vacuous-pass preconditions

**Source:** `tools/publish_scan_tests/test_docstring_leaks.py:25-28`, and
`tools/docs_tests/_prose.py:59-63` carries the same finding:

```python
#: The repo root, resolved from this file rather than from the process CWD:
#: a CWD-relative walk yields zero files off-root and turns the gate below
#: into a test that passes over nothing (WR-04).
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
```

Any new gate module opens with that line and carries a
`test_the_walk_does_not_depend_on_the_process_cwd` companion.

---

### Publication mechanics — the four facts every new page is subject to

All verified in `mkdocs.yml` and `Makefile`:

| Fact | Where |
|---|---|
| `docs_dir: public` — publication is **default-deny by existence** | `mkdocs.yml:17` |
| `strict: true` — any warning is fatal, even without `--strict` on the CLI | `mkdocs.yml:22` |
| `check_paths: true` — a mistyped snippet target fails the build instead of rendering empty | `mkdocs.yml:95` |
| nav enumerates every path explicitly, **no globs**; `validation.nav.omitted_files: warn` + strict means a page absent from nav fails the build | `mkdocs.yml:38-39`, `:113-166` |

`make docs-strict` is four steps (`Makefile:271-274`), and it is in `make ci`
(`Makefile:81`) per `D-IMPL-72`:

```make
docs-strict: ## Blocking docs gate: pre-build scan + schema scan + strict build + site scan (D-IMPL-72, D-02, DCD-11)
	$(ENV_DOCS) $(PYTHON) tools/publish_scan.py --pre-build
	$(ENV_DOCS) $(PYTHON) tools/publish_scan.py docs/schemas
	$(ENV_DOCS) $(PYTHON) -m mkdocs build --strict
	$(ENV_DOCS) $(PYTHON) tools/publish_scan.py site
```

Snippet includes are a **positive allowlist** (`tools/publish_scan.py:104-112`) —
`examples/`, `public/`, `perf/baselines/`, plus the single file `openapi.json`.

**Nav entry form to copy** (`mkdocs.yml:118-121`):

```yaml
  - How-to:
      # D-17 placement: the security and deployment notes lead the How-to
      # section.
      - Manage keys and secrets: how-to/security-and-deployment.md
      - Grant and revoke a skill: how-to/grant-and-revoke-a-skill.md
```

⚠ `mkdocs.yml:109-112` carries a **hand-maintained count** — *"it lists 42 pages
… for the 43 markdown files under `public/`."* Three new pages make it 45 / 46.
The comment is prose, so nothing fails if it is not updated; that is precisely
why it rots.

---

### The day-1 import convention (A-1), already gated

**Source:** `public/reference/artifacts/deployment-manifest.md:11-25`; enforced by
`tools/docs_tests/test_advisory_discharge.py:83-84`:

```python
PREFERRED_IMPORT = "from ccf.deployment import"
SUBMODULE_IMPORT = re.compile(r"from\s+ccf\.deployment\.[A-Za-z_][A-Za-z0-9_]*\s+import")
```

Every new page writes `from ccf.deployment import X`. **No page anywhere may
write `from ccf.deployment.<submodule> import`.** `spine.py:64-67` states the
same rule for example code and `:90-95` obeys it.

---

## 4. No Analog Found

| File / pattern | Role | Nearest partial | Why it is not an analog |
|---|---|---|---|
| `public/concepts/context-graph-axes.md` — **the content** | doc (concept) | `public/concepts/invariants.md` (promise / why / enforcement triple, 175 lines) | The *form* transfers. The *content* does not exist anywhere: `public/concepts/whitepaper-index.md` carries the axes only as a table row, and a grep for "six axes" across `public/` returns hits about the six **specialization axes of an agent**, which is a different six. This is genuinely new writing. The observable-surface anchors in `spine.py` (entry A3) are the material to write from. |

**That is the only one.** Everything else the previous map listed as NO ANALOG has
either shipped (`_prose.py`, the Gate-2 gate) or deferred to 16.1 with the work
it belonged to (the adoption-argument page, `client_langgraph.py`, `gate_16.py`).

---

## 5. Deferred to Phase 16.1 — verified analog pointers, so 16.1 need not re-derive

R-1 defers these. Pointers verified this session; excerpts deliberately omitted
because the surface will move again before 16.1 plans.

| Deferred work | Analog verified to exist at `6e95da0` | Note |
|---|---|---|
| Six-backend matrix (`16-07`, criterion 4) | `tests/conftest.py` — `fluree_url` fixture at `:237`, `FLUREE_URL_ENV = "CCF_TEST_FLUREE_URL"` at `:229`, `FLUREE_REQUIRED_ENV = "CCF_REQUIRE_FLUREE"` at `:234`; `pyproject.toml:148` registers the `fluree` marker; `Makefile:146` `CCF_TEST_FLUREE_URL ?=`, `:152` `legs:`, `:166` `leg-fluree:` | The skip-vs-fail posture (`CCF_REQUIRE_*` turns an unreachable server from a skip into a failure) is the pattern; `conftest.py:232-234` states the reason |
| Backend selection without a cascade | `src/ccf/graph/registry.py:624` `declared_names()` | Selection stays manifest → registry lookup. `examples/s1-01-…/artifacts/manifest.yaml` declares the backend as a **kind** only; the connection value is caller-supplied at boot |
| `tools/docs_tests/test_adoption_argument.py` | `tools/docs_tests/test_openapi_drift_control.py` (74 lines) for the both-polarities control; `_prose.py` for the corpus | Depends on the adoption page, deferred with it |
| `tests/examples/test_backend_matrix.py` | `tests/conformance/` + `tests/conftest.py` | ⚠ **`16-07`'s byte-identity claim now rests on `debt` (a 28-digit `Decimal` computed off `execution.view`) being substrate-stable. Nobody has measured it.** A task, not an assumption |
| Terminal retirement of `examples/00`–`08` | `tools/retirement_sweep.py`; `tools/docs_tests/test_retirement_sweep.py` | `test_snippet_gate.py:50-52` records that plan `16-18` repoints **both** its constants at the Section-1 spine when `examples/00-quickstart` retires |
| `client_langgraph.py`, Section-2 legs | `examples/external/00-hello-context/client_{bare,adk,anthropic}.py` | `client_langgraph.py` had NO ANALOG at the last mapping; the transport spike shipped as `tests/examples/test_s2_client_transport_spike.py` (`16-03`) and should be re-read before 16.1 concludes the gap stands |
| `make gate-16` / `tools/gates/gate_16.py` | **git history only** — `git show 50e79e7:Makefile`, `git show d364b65^:tools/gates/gate_15_3.py` | `16-19`'s `gate_16.py` allowlist is **revoked machinery** — `D-IMPL-96` void'd the `git diff --stat -- src/ runtime/` assertions in `16-12`, `16-18` and `16-19` |
| FIBO DGX loading (`16-02` Task 3) | `/home/parkave/fluree/examples/fibo/load_{neo4j,postgres,mongo}.py` (out of repo) | Not a Hello CCF dependency (research §0c). ⚠ `192.168.4.76` must not enter the repo as a `.py` literal |
| `DI-15.6-02` retirement-report row | `tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current` (red at HEAD) | One data line plus a report regeneration |

---

## 6. Possible defects worth a ruling

Surfaced by verification, not designed. None is acted on here.

1. **The `pyproject.toml:142` coverage hole is wider than `docs_tests` +
   `publish_scan_tests`.** `tools/lints/tests` (9 modules) is also outside
   `make ci` and is the enforcement mechanism for three CI-named invariants
   (`ci.yml:30-35` says so explicitly). Composing only two of the three suites
   leaves the lint checkers in the same hole `DI-15.6-01(b)` names.
2. **`spine.py:15` reproduces the same whitepaper shingle as
   `src/ccf/products/request.py`** — *"the difference between the verb aggregate
   and the verb assemble."* `test_docstring_leaks.py` scans only `src/` and
   `runtime/` (`:31`), so `examples/` is unscanned. Closing the leak in `src/`
   while an example ships the identical sentence, and while `docs-strict`'s site
   scan may or may not reach it through a snippet include, is half a closure.
   **Verify which pages include that region before deciding.**
3. **`mkdocs.yml:109-112`'s page count is hand-maintained prose.** Three new pages
   make it wrong and nothing fails. Same defect class as A-3.
4. **`16-RESEARCH.md` §2.4 says `ccf.deployment` exports 17 names; it exports 16**
   (`src/ccf/deployment/__init__.py:127-144`, confirmed by import). The published
   page is right and the research is wrong. Worth correcting in the research
   before a plan "fixes" the page.
5. **`16-05-SUMMARY.md` states a fact that is false at HEAD** — that `spine.py`
   and `deployment.py` are held together by two Protocols including
   `DeploymentBinding`. That class was deleted at `6b87a8f`. A SUMMARY is a phase
   record; someone should decide whether it is amended or annotated.

---

## Metadata

**Analog search scope:** `public/` (43 pages, all enumerated),
`tools/docs_tests/` (11 modules), `tools/publish_scan_tests/` (3),
`tools/lints/`, `tools/publish_scan.py`, `tests/examples/` (21 modules),
`tests/conftest.py`, `examples/s1-01-hello-context-product/` (4 modules,
19 artifacts, README), `src/ccf/products/contract.py`,
`src/ccf/halflife/decay.py`, `src/ccf/deployment/__init__.py`,
`src/ccf/graph/registry.py`, `mkdocs.yml`, `Makefile`, `pyproject.toml`,
`.github/workflows/ci.yml`, `docs/DECISIONS.md`, `.planning/ROADMAP.md`.

**Executed this session:** `pytest tools/ -q` (4 failed / 540 passed);
`pytest tools/docs_tests/test_documented_commands_exist.py -q`;
`python -c "import ccf.deployment; len(__all__)"`;
`scan_text` + `whitepaper_shingles` over the five leaking module docstrings;
`ast.parse` for each leaking docstring's extent;
`git grep DeploymentBinding -- src/ runtime/ examples/` (no hits);
`grep` over `16-PATTERNS.md` for the alleged `tests/test_*.py` citations (no hits).

**Cited paths verified to exist:** 47.
**Corrected:** 8 (six "to be created" files that had shipped; the `_prose.py`
NO-ANALOG row; the `test_snippet_gate.py` mis-pointing warning).
**Dropped as having no current analog:** 0 — the deferred entries moved to §5
with verified pointers rather than being deleted.
**Findings rejected as non-reproducing:** 1 (the `tests/` → `tools/` path rot),
plus 3 corrections to `16-RESEARCH.md` recorded in §0.5.

**Pattern extraction date:** 2026-08-13
**Tree state:** `6e95da0`
