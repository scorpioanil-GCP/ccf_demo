---
phase: 17-client-access-ccf-client-and-the-transport-agnostic-first-ex
plan: 12
subsystem: client
tags: [binding-document, d-impl-141, amendment-a3, amendment-a4, no-hardcoding, narrowing-gate, sabotage-controls]

requires:
  - phase: 17-06
    provides: "`binding.yaml` and its loader in the rejected factory shape — the subject this plan reshapes"
  - phase: 17-11
    provides: "`ccf.products.debt_scorer.AssemblyDebtScorer` and `DeclaredFactor`, without which the fixture's own debt scorer could not be deleted"
provides:
  - "`binding.yaml` as a data document carrying exactly ONE `module:attribute` reference — `plan:`, the projection"
  - "A loader that refuses a second reference BY NAME *and* by SHAPE, so the exception cannot widen through a permitted key"
  - "`D-IMPL-141` RESOLVED: the rejection, the measurement that dissolved half of it, the surviving shape, and the mechanism holding it narrow"
  - "The Amendment A.4 criterion 3′ gate: exactly one Python module, defining exactly the one attribute `plan:` names"
  - "`InProcessAdapter` builds `GovernedResolver` itself — the composition `17-13` lifts into a helper"
  - "A surface-record allowance for a name born and buried inside one baseline window, derived from the record and independently checked"
affects: [17-13]

tech-stack:
  added: []
  patterns:
    - "A narrowing enforced twice — by key name and by value shape — because either check alone leaks"
    - "The permitted-exception set as a ONE-ELEMENT named constant, so widening it is a visible edit rather than a loosened condition"
    - "A gate written `!= 1` rather than `> 1`, with the ZERO case proven to fire"
    - "A module's public surface read by `ast` rather than by import, so the subject cannot influence the gate that measures it"
    - "A surface-record allowance DERIVED from the record's own two-directional claim rather than hand-listed, then checked against both surfaces"

key-files:
  created:
    - tests/client/fixtures/deployment/projection.py
    - docs/surface-changes/17-12-binding-document-data-only.md
  modified:
    - src/ccf/client/adapters/binding_document.py
    - src/ccf/client/adapters/inprocess.py
    - tests/client/test_binding_document.py
    - tests/client/fixtures/deployment/binding.yaml
    - tests/client/fixtures/deployment/scenario.yaml
    - tests/client/conftest.py
    - tests/client/test_inprocess_adapter.py
    - tests/client/conformance/test_the_suite_fires.py
    - tests/test_surface_completeness.py
    - tests/test_surface_shape_capture.py
    - tests/deployment/test_class_lookup.py
    - docs/DECISIONS.md
    - docs/SURFACE-CHANGES.md
    - docs/surface/v0.2-surface.json
    - docs/surface/examples/RETIREMENT-COUPLINGS.md
  deleted:
    - tests/client/fixtures/deployment/resolver.py

decisions:
  - "The narrowing is enforced BY NAME and BY SHAPE: RULED_OUT_KEYS names the rejected keys, looks_like_a_reference refuses a reference-shaped value in any data position. Key-name refusal cannot see a reference smuggled through a permitted key; shape refusal alone would let the rejected shape return under a new spelling"
  - "looks_like_a_reference checks *names a .py file*, not *contains a colon* — a declared `asked_at` carries three colons and is data"
  - "REFERENCE_KEYS is a one-element tuple so granting a second exception is an edit to a named constant a reviewer can see"
  - "`connection:` survives as DATA with a `{path: …}` form for root-relative settings, because sqlite's adapter contract requires `database_path` and the deployment root is not known until a client names it"
  - "`artifact_store` and `debt` are data keys the plan did not list, because the spec's claim that artifact_store is fabric-supplied is false and the debt scorer's C and S have no SDK default"
  - "`question.asked_at` is a fourth declared field, because `WireRequest.temporal_boundary` may be None and `ProductRequest.asked_at` is required — the SDK does not own it at this seam"
  - "The fixture module is renamed resolver.py → projection.py, because a projection-only module named `resolver` is the misdescription the ruling exists to remove"

metrics:
  duration: ~3 hours
  tasks: 3
  completed: 2026-08-16
---

# Phase 17 Plan 12: `binding.yaml` as a Data Document Summary

`binding.yaml` now carries data plus exactly one `<module>:<attribute>`
reference — `plan:`, the projection — and the loader refuses a second one **by
name and by shape**, with both refusals watched firing. `D-IMPL-141` is
RESOLVED, recording the rejection rather than the proposal. The client fixture's
deployment went from a 295-line module doing five things to a 127-line module
doing one, and a gate fails if that changes.

## Measured verification

| Gate | Result |
|---|---|
| `make ci-core` | **exit 0** — `3711 passed, 0 failed, 118 skipped` in 393.30s; `400 passed` lint tests; `144 passed` tools tests |
| `PYTHONPATH=src:runtime .venv/bin/python -m tools.lints --all` | **exit 0** |
| `make docs-strict` | **exit 0** |
| `make typecheck` | **exit 0** — clean over 209 source files |
| `make surface-changes` | wrote `docs/SURFACE-CHANGES.md`; fragment `docs/surface-changes/17-12-binding-document-data-only.md` present |
| `pytest tests/client -q` | `291 passed` |
| `pytest tests/client/test_binding_document.py -q` | `72 passed` |

The orchestrator's pre-dispatch baseline on `0838a9d` was `3661 passed / 118
skipped`. The delta is **+50**, all in `tests/client/test_binding_document.py`
(72 now, 22 before) and `tests/test_surface_completeness.py` (11 now, 8 before —
the three new controls).

> **Measured in a worktree.** Every number above was produced inside
> `/home/parkave/ccf_code/.claude/worktrees/agent-a6d7ef62edcd34c8b`.
> Tree-walking gates measured in a worktree are not evidence about the branch
> (`DEF-17-04`), and this plan added a tree-walking gate — the orchestrator
> should re-measure `make ci-core` after merge.

## The fixture, before and after — the number Amendment A.3 asked for

| File | Before (`0838a9d`) | After | What moved |
|---|---:|---:|---|
| `resolver.py` → `projection.py` | **295** | **127** | five responsibilities → one |
| `scenario.yaml` | 58 | 23 | five sections → one (`attributes`) |
| `binding.yaml` | 22 | 79 | three references → data + one reference |

`resolver.py` held a projection, a plan factory, a debt scorer, a connection
factory and a question factory. `projection.py` holds a projection. Its public
names are exactly `["build_projection"]` — the attribute `plan:` names — and
`assert_the_module_defines_only_the_named_reference` fails if a second arrives.

The deployment directory is now `ccf_config.yaml`, `binding.yaml`,
`scenario.yaml` and **exactly one** `.py` file. That is criterion 3′.

## The mechanism, and why it is two checks rather than one

Amendment A.4's load-bearing sentence is *"an exception with no mechanism
holding it narrow is not an exception; it is a precedent."* One check would have
been a precedent:

- **`RULED_OUT_KEYS`** refuses `resolver:` and `connection_factory:` **by name**,
  before the unknown-key check, with a message that says *ruled out* and cites
  the spec. Told merely *"not a binding-document key"*, an author of the
  rejected shape re-spells it.
- **`looks_like_a_reference`** refuses a `<module>:<attribute>`-shaped value in
  **any data position**, walking nested mappings and sequences and naming the
  dotted position. Key-name refusal **cannot see** a reference smuggled through
  `question.subject` or `operator_parameter_keys[0]` — keys the schema permits.

The predicate's shape is *names a `.py` file*, not *contains a colon*, and that
is not fastidiousness: `asked_at: "2026-03-02T12:00:00+00:00"` carries three
colons and is data. The narrow predicate is what makes the check usable.

`REFERENCE_KEYS` is a **one-element tuple**, asserted to be one element, so
granting a second exception is a visible edit to a named constant.

## Sabotage controls — every observed failure message, verbatim

Each control feeds a **divergent subject to the shipped assertion function**;
none re-implements an assertion. An honest-subject test
(`test_the_committed_fixture_satisfies_every_gate`) runs both gates against the
unmutated fixture first, so no control's expectation of failure is met by a
subject that never worked.

**The Amendment A.4 gate**

1. **`assert_one_python_module` — a SECOND module:**
   `the deployment at /tmp/…/deployment holds 2 Python modules ['projection.py', 'resolver.py'], not exactly one — Amendment A.3 grants this deployment one module, the projection, and grants it nothing else`
2. **`assert_one_python_module` — THE EMPTY CASE (zero matches):**
   `the deployment at /tmp/…/no-modules holds 0 Python modules [], not exactly one — …`
   This is the control that matters. The gate is written `!= 1`, not `> 1`; a
   *"no more than one"* count passes on zero, which is this phase's signature
   defect.
3. **`assert_the_module_defines_only_the_named_reference` — a SECOND public name
   (the count gate still passes, which is the whole point):**
   `/tmp/…/projection.py defines the public names ['build_projection', 'build_resolver'], not exactly ['build_projection'] — the one module a deployment may write exposes exactly the one attribute `plan:` names: no fewer, no more, and no other…`
4. **Same assertion — THE EMPTY MODULE:**
   `… defines the public names [], not exactly ['build_projection'] — …`
5. **Same assertion — document and module disagree:**
   `… defines the public names ['build_projection'], not exactly ['build_something_else'] — …`

**The narrowing refusals**

6. **RULED OUT by name — `resolver:`**
   ``/tmp/…/binding.yaml states `resolver`, which `D-IMPL-141` **ruled out** rather than never defined: `resolver` — the SDK builds the resolver itself from the data keys below — a deployment supplies the projection through `plan:` and nothing else. See `docs/superpowers/specs/2026-08-16-reference-plan-factory-and-debt-scorer.md` Amendment A``
7. **RULED OUT by name — `connection_factory:`** — same shape, naming *connection
   material is data under `connection:`, not a factory the loader imports and
   calls*.
8–12. **REFERENCE IN A DATA POSITION**, one control each for
   `product_class_key`, `question.subject`, `perspective.role`,
   `operator_parameter_keys[0]` and `connection.database_path`:
   ``` `question.subject: sneaky.py:build_resolver` in /tmp/…/binding.yaml is a `<module-path>:<attribute>` reference in a **data** position. This document carries exactly one reference, under `plan`, and it names this deployment's projection. Every other key is data — see … Amendment A.3, which grants the deployment one Python module and no second one```
13. **Unknown key by name** — enumerates all fifteen keys with their kinds.
14. **Containment, rooted connection path:**
    `` `connection.database_path.path: ../elsewhere.sqlite3` in /tmp/…/binding.yaml names a path outside the deployment root — …``
15. **Zone-less `asked_at`:**
    `` `question.asked_at: 2026-03-02T12:00:00` in /tmp/…/binding.yaml states no time zone — a zone-less instant is a silent default (`D-IMPL-38`), and which zone it silently meant is the difference between two different answers``

**The surface-record allowance** (added under deviation 8 below), three controls
against `assert_short_lived_names_are_absent_from_both_sides`: a name still live,
a name older than the frozen baseline, and **the empty set** (which must pass
while admitting nothing — asserted rather than left to inference).

## Deviations from Plan

### 1. [Rule 3 - Blocking] The plan's `files_modified` omitted the adapter that consumes the document

- **Found during:** Task 1.
- **Issue:** removing `resolver:` and `question:` from the schema leaves
  `~ccf.client.adapters.inprocess._boot` with nothing to call. There is no
  partial version of this change — either the loader keeps the rejected keys, or
  the SDK builds the resolver.
- **Resolution:** `_boot` now constructs `GovernedResolver` from the document's
  data, and `ask` assembles the typed `ProductRequest` per question. The
  composition is documented at the seam as **the thing `17-13` is expected to
  lift into `build_governed_resolver(...)`**, so a second transport does not grow
  a second copy of it.
- **Commit:** `4deb099`

### 2. [Measurement — the spec is wrong] `artifact_store` is not fabric-supplied

- **The spec says** (§1 table): *"The booted fabric | 3 | `fabric`,
  `control_plane`, `artifact_store`."*
- **Measured:** `~ccf.deployment.BootedFabric` carries `handle`, `pins`,
  `tenant_id`, `artifacts` and `survivor_cap`. There is no artifact store on it.
  The pre-conversion fixture constructed its own
  `FileArtifactStore(root=HERE / scenario["storage"]["artifact_store_dirname"])`.
- **Resolution:** `artifact_store:` is a **data key** naming a path, contained
  against the root. The adapter selects the shipped file-backed reference
  (CLAUDE.md §7.4) because a *path* is what a file-backed store takes; a
  deployment on another substrate is `17-13`'s helper, and the docstring says so.
- **Consequence for the record:** the spec's *"eight data keys"* is **ten** as
  built — the eight, plus `artifact_store`, plus the `debt` block.

### 3. [Measurement — the spec is half-wrong] `asked_at` is not owned by the SDK at this seam

- **The spec says** (§3): *"`asked_at` is a `datetime` the SDK already owns
  through `as_of` (`D-04`)."*
- **Measured:** true when the caller names a boundary; false otherwise.
  `~ccf.client.wire.WireRequest.temporal_boundary` is `datetime | None`, and
  `~ccf.products.request.ProductRequest.asked_at` is required. `None` means
  *the server's decision instant*, and whose clock and what default is the
  producer's decision — which is exactly why the rejected proposal wanted a
  factory for it. It does not need a factory; it needs a **value**.
- **Corroborated on the tree:** `examples/s1-01-hello-context-product/artifacts/questions.yaml`
  already carries `asked_at` per question, as data, in a Control Plane artifact.
- **Resolution:** `question:` carries a fourth field, `asked_at`, refused unless
  it is a **zoned** ISO 8601 instant (`D-IMPL-38` — a zone-less instant is a
  silent default).

### 4. [Measurement] `connection:` could not simply be removed

- **The plan says:** *"`connection` is removed as a `module:attribute`
  reference; if connection material is needed it is data or it is absent"* — but
  its permitted-key list omits `connection` entirely.
- **Measured:** `src/ccf/graph/backends/sqlite_write.py::SqliteBackendConfig`
  declares `database_path` **required**, and the fixture's value must be an
  absolute path under a root that is not known until a client names it.
  `connection` is therefore neither absent nor expressible as a flat literal.
- **Resolution:** `connection:` is an optional **data mapping** whose values are
  scalars carried verbatim, or a single-key `{path: …}` resolved against the root
  and contained. The SDK still learns no adapter's vocabulary — the *names* are
  the deployment's, this loader reads none of them, and the composed mapping is
  validated by the adapter's own contract at preflight, exactly as before.

### 5. [Ordering — 17-13 is pre-empted in one narrow place] the `debt:` block

- **Issue:** the plan requires deleting the fixture's debt scorer *and* requires
  `tests/client` to pass, but `17-11` measured that
  `~ccf.products.debt_scorer.AssemblyDebtScorer` takes `C` and `S` as
  `DebtFactorScorerProtocol` implementations with **no defaults**, and
  `GovernedResolver.debt_scorer` has no default either (`17-11` deliberately left
  that to `17-13`).
- **Resolution:** `binding.yaml` carries a `debt:` block — the λ_c and profile
  Control Plane keys, plus the `C` and `S` this deployment **declares**. The
  values reach replay through `DeclaredFactor`'s own scorer pin (`D-IMPL-47`), so
  an examiner can tell an assertion from a measurement. A library default would
  have been `D-IMPL-38`'s *a value nobody chose* landing inside a delivered
  product's content address.
- **Flagged for `17-13`:** wiring the reference scorer as a **default** on
  `GovernedResolver` (or the helper) may make part or all of `debt:` optional.
  That is `17-13`'s call, not this plan's; nothing here forecloses it.

### 6. [Collision check the orchestrator asked for] `17-11`'s false-reason finding is discharged, not colliding

- **The question:** `17-11` found that
  `tests/client/fixtures/deployment/resolver.py::_debt_scorer` carried a **false
  stated reason** — *"a scorer cannot see the question's `asked_at`"* — when
  `GraphView.as_of` carries it. `17-11` left it, noting `17-13` would delete the
  file.
- **Measured:** the file is deleted **here**, in `17-12`, and the false claim
  goes with it. Nothing in `projection.py` restates it. There is no collision:
  `17-13`'s remaining work is the *default* on `GovernedResolver` and the
  end-to-end proof, neither of which touches this file.

### 7. [Rule 1 - Naming] `resolver.py` → `projection.py`

The plan's file list named `tests/client/fixtures/deployment/resolver.py`.
Keeping that name for a module that holds only a projection would preserve the
exact misdescription this ruling exists to remove — and the sabotage control in
`tests/client/conformance/test_the_suite_fires.py` spelled the filename, which
would have silently stopped matching. That control now resolves the module
through `binding.yaml`'s `plan:` reference, so it cannot.

### 8. [Rule 2 - Correctness] Three surface gates could not express a name born and buried in one window

- **Found during:** the first full `make test`.
- **Issue:** `ResolverCall`, `QuestionFactoryProtocol`, `REQUIRED_KEYS` and
  `conforming_resolver` were **added by `17-06` and removed by `17-12`**, both
  after the v0.2 baseline was frozen. Such a name is in **neither** side of
  `diff(baseline, live)`, so an honest and complete record failed in both
  directions:
  `17-06-inprocess-adapter.md claims 'added' for …REQUIRED_KEYS but the manifest does not show this name at all.`
- **Fix, and its shape:** the allowance is **derived from the record**, never
  listed — a name qualifies only when the log carries *both* directions for it,
  so the pair of claims is the evidence and there is no list to rot or to edit
  into silence. And it is **checked**, not muted:
  `assert_short_lived_names_are_absent_from_both_sides` requires each admitted
  name to be genuinely absent from the frozen baseline **and** from the live
  surface, so a `removed` claimed for a live name — or an `added` for one older
  than the baseline — fails there instead of two wrong entries cancelling out.
  Three controls, including the empty case, are recorded above.
- **Commit:** `bf91317`

### 9. [Bookkeeping] `RETIREMENT-COUPLINGS.md` and the surface manifest

`gate-tools` went red on `test_the_committed_report_is_current`: four coupling
rows naming `examples/s1-00-companies-over-revenue` disappeared with the
docstring rewrite and the deleted fixture. Re-measured with
`tools/retirement_sweep.py --report`: **230 rows across 71 files** (was 234/74).
`make surface` regenerated `docs/surface/v0.2-surface.json`, as `17-04`, `17-05`
and `17-06` each did in this phase. **Commit:** `d5fef6e`

### 10. [Standing hazard, newly measured — worth carrying forward]

**The editable install resolves `ccf` to the MAIN checkout, not the worktree.**
`.venv` is a symlink to `/home/parkave/ccf_code/.venv`, whose editable install
maps `ccf` to `/home/parkave/ccf_code/src`. A bare
`.venv/bin/python -c "import ccf…"` inside a worktree **measures the wrong
tree** — observed directly: the first smoke test of the new loader reported the
*old* module's refusal message. Every measurement in this summary carries
`PYTHONPATH=src:runtime`, which the Makefile sets as `ENV`.

**`make … 2>&1 | tail -N` reports `tail`'s exit code, not `make`'s.** The first
full-suite run was reported by the background wrapper as *"exit code 0"* while
`make` had in fact printed `Error 1` with three failures. Every gate result above
was taken from an explicit `echo "EXIT=$?"` on the unpiped command.

## What this plan deliberately did not do

- **No default on `GovernedResolver`.** Its `debt_scorer` and `plan_factory`
  fields are still required with no default. Wiring the reference scorer as a
  default is `17-13`'s work and its success criterion.
- **No `ProjectionPlanFactory` reference implementation, and no pass-through
  plan.** Amendment A.2 ruled one impossible as scoped and the pass-through was
  withdrawn during that exchange; `D-IMPL-141`'s rewrite records both so neither
  is re-proposed.
- **No second `module:attribute` reference, anywhere.** `REFERENCE_KEYS` has one
  element and a test asserts it.
- **No `build_governed_resolver(...)` helper.** The composition lives in the
  in-process adapter because there is exactly one transport today; the seam
  names `17-13` as its intended home.

## Known Stubs

None. The loader, the narrowing, the gate and the fixture conversion are
complete for the ruling they implement. The `debt:` block is a shipped
mechanism — a stated assumption with an identity in replay — not a placeholder,
though `17-13` may relocate it.

## Threat Flags

None. This plan adds no network endpoint, no auth path and no schema at a trust
boundary. It **narrows** an existing file-access surface: the trust posture
`T-17-19` accepted (loading a reference executes deployment Python) now applies
to exactly **one** reference rather than three, containment now covers
`artifact_store` and the rooted `connection` form as well as `config`, and a
reference-shaped value can no longer enter through a data key.

## Self-Check: PASSED

Files claimed created, verified present:

- `tests/client/fixtures/deployment/projection.py` — FOUND
- `docs/surface-changes/17-12-binding-document-data-only.md` — FOUND

File claimed deleted, verified absent:

- `tests/client/fixtures/deployment/resolver.py` — ABSENT

Commits claimed, verified in `git log`:

- `4deb099` — FOUND (`feat(17-12): binding.yaml is data, with one named exception`)
- `02d3208` — FOUND (`test(17-12): the fixture is data plus one projection, with the gate watched firing`)
- `fa52262` — FOUND (`docs(17-12): D-IMPL-141 is RESOLVED — the rejection, and what replaced it`)
- `e6596cf` — FOUND (`docs(17-12): surface-change fragment for the data-only binding document`)
- `0d381b3` — FOUND (`test(17-12): the responsibility gate's message covers all three ways it fires`)
- `bf91317` — FOUND (`fix(17-12): the surface record can now express a name born and buried in one window`)
- `d5fef6e` — FOUND (`chore(17-12): re-measure RETIREMENT-COUPLINGS after the fixture conversion`)

No modification to `.planning/STATE.md` or `.planning/ROADMAP.md`
(`git diff --name-only 0838a9d..HEAD` shows neither); no `state.*` or
`roadmap.*` SDK writer was invoked.
