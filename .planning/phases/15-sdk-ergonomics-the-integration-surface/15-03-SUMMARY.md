---
phase: 15-sdk-ergonomics-the-integration-surface
plan: 03
subsystem: repo-tooling
tags: [ergo-03, audit, measurement, falsification]
status: paused-at-checkpoint
requires:
  - "15-01 (the surface: Makefile target and the committed manifest)"
provides:
  - "tools/measure_examples.py — AST measurement of the examples tree, with --check"
  - "docs/surface/examples/before/ — 24 per-file phase-start baseline fragments"
  - "tests/examples/test_surface_audit.py — the executable Criterion 1 audit + audit_report()"
  - "make measure-examples"
  - "Falsification verdicts for research assumptions A1, A3, A6"
affects:
  - "15-04 (A6 sizing), 15-07 (A1 sizing), 15-12 (A3 artifact churn), 15-21 (calls audit_report())"
tech-stack:
  added: []
  patterns:
    - "tools/dump_openapi.py template: exported serialize() + --check + REPO_ROOT-from-__file__"
    - "per-file fragments under docs/surface/ so parallel worktrees never collide"
key-files:
  created:
    - tools/measure_examples.py
    - tests/examples/test_surface_audit.py
    - docs/surface-changes/15-03-audit-baseline.md
    - docs/surface/examples/before/ (24 fragments)
  modified:
    - Makefile
decisions:
  - "Measured reg spans run ~1 line below 15-RESEARCH.md §1.3 per file; the research table counted the `registry = ControlPlaneRegistry()` construction line inside the registration cluster. Every other column reproduces exactly. Method kept as documented; see Reconciliation below."
metrics:
  tasks_completed: 3
  tasks_total: 4
  completed: 2026-08-04
---

# Phase 15 Plan 03: The Criterion 1 Surface Audit Baseline Summary

AST measurement of the examples tree committed as 24 per-file baseline fragments, with an
executable audit that pins achieved numbers and is structurally unable to conflate D-09's
relocated lines with removed lines — plus three falsification measurements that settle the
sizing of plans 15-04, 15-07, and 15-12.

**Status: paused at the Task 4 blocking checkpoint.** Tasks 1–3 are complete and committed.

## What was built

### Task 1 — `tools/measure_examples.py` and the before-baseline

Three AST passes per 15-RESEARCH.md §1 Method, producing per-file `raw`, `helpers`, `opblk`,
`boot`, `reg`, `mech`, `asserts`, `prints`, `imports`, plus the two headline keys the audit
turns on: `removable` (mechanical wiring, which rewrites delete) and `relocatable`
(`asserts + prints`, which D-09 merely moves to `tests/`). The module docstring states that
these two are never summed, and why: D-12's stated risk is a target hit by moving lines
rather than by removing work.

Category line-sets are made **disjoint** in the order `helpers`, `opblk`, `boot`, `reg`, so a
line inside two spans is never double-counted.

24 fragments written to `docs/surface/examples/before/`, one per Python module under
`examples/` — per-file rather than aggregate so the eight example-rewrite plans can each add
their own `after/` fragment in parallel worktrees without colliding.

`make measure-examples` added **after** the `surface:` target (present in the tree, so 15-01's
dependency was honored) with its own `.PHONY` entry.

**Tree totals:** `mechanical_before` **1,425**; `relocated_before` **737**.

### Reconciliation against 15-RESEARCH.md §1.2/§1.3

The quickstart fragment reproduces the research's §1.2 breakdown **exactly** on every column
but one:

| Key | Research §1.2 | Measured | Delta |
|---|---:|---:|---:|
| `raw` | 451 | 451 | 0 |
| `helpers` | 45 | 45 | 0 |
| `opblk` | 64 | 64 | 0 |
| `boot` | 8 | 8 | 0 |
| `reg` | 27 | 26 | −1 |
| **`removable` (`mech`)** | **144** | **143** | **−1** |
| `asserts` | 30 | 30 | 0 |
| `prints` | 10 | 10 | 0 |
| **`relocatable`** | **40** | **40** | **0** |
| `imports` | 54 | 54 | 0 |

Both figures are inside the plan's ±3 acceptance band. The single-line `reg` delta recurs on
seven files (research 1,435 mech tree-wide vs measured 1,425): the research table's
registration cluster included the `registry = ControlPlaneRegistry()` construction line, which
is not a `registry.register` / `parse_artifact` / `register_product_class` / `Perspective` /
`MaxTTL` call span and therefore falls outside the documented pass-3 definition. **The tool
was kept faithful to the documented Method rather than widened to reproduce the number** — the
whole point of ERGO-03 is that the phase-close figure is a re-measurement by this code, and
both ends of the audit now use the same definition. `relocatable` matches the research total
(737) exactly.

### Task 2 — `tests/examples/test_surface_audit.py`

29 tests, passing with zero `after/` fragments present.

- **Assertion 1 (no silent regression)** — for every file with an `after/` fragment, the live
  measurement must equal the recorded numbers. Per D-12 there is no target; the achieved
  number is pinned. Files without an `after/` fragment are skipped, not failed.
- **Assertion 2 (baseline is real)** — every `before/` fragment names a file that still
  exists and slugifies back to its own filename; a vacuity test requires ≥20 fragments.
- **Assertion 3 (separate reporting)** — `audit_report()` returns `mechanical_before`,
  `mechanical_after`, `relocated_before`, `relocated_after`, a per-file breakdown, and the
  list of rewritten files. A test walks `audit_report`'s own AST and asserts no identifier or
  string key named `lines_saved` / `total_reduction` / `total_saved` exists; the forbidden set
  is assembled from parts so the test's source is not what trips its own scan. Plan 15-21
  calls this helper for the phase-close report.

Fragments are globbed, never enumerated, so rewrite plans add `after/` fragments without
touching this module.

### Task 3 — falsification of A1, A3, A6

No production code changed. `git status` confirms `tools/lints/__main__.py` is unmodified —
the A6 widening was applied by monkeypatching the module in a throwaway interpreter, so no
scratch edit ever reached the tree.

## Falsification results

### A1 — Pydantic coercion for `EntityResolutionSpec`: **CONFIRMED, with one caveat**

`EntityResolutionSpec.model_validate` on the D-03-stripped `00-quickstart/artifacts/ontology.yaml`
**succeeds with no custom validator**, and the result is `==` to the hand-marshalled
`_resolution_spec()` output:

- `entity_rules` — list of dicts coerced to `tuple[EntityResolutionRule, ...]`
- `identity_keys` / `attribute_keys` — lists coerced to `tuple`
- `relationship_rules` — coerced to `tuple[RelationshipResolutionRule, ...]`

**The caveat, and it is A3's finding wearing a different hat.** Stripping only D-03's three
keys (`tenant_id`, `classification_attribute_by_class`,
`similarity_corpus_attribute_by_class`) is **not sufficient** — validation fails first on the
two root-level version keys:

```
2 validation errors for EntityResolutionSpec
schema_version
  Extra inputs are not permitted [type=extra_forbidden, input_value='1.0.0', input_type=str]
artifact_version
  Extra inputs are not permitted [type=extra_forbidden, input_value='1.0.0', input_type=str]
```

With `schema_version` and `artifact_version` also removed, validation passes cleanly. So
**plan 15-07 needs no custom validator**, but the `ccf.resolution-spec` artifact class does
have to decide what the root version keys are: either the class grows the two-field versioning
per D-IMPL-28 (which the registry's D-05 bump check needs anyway — see A3), or the loader
strips them. That is a schema decision inside 15-07's existing scope, not a new task.

### A3 — are the root `schema_version` / `artifact_version` keys read? **DECORATION, in every case measured**

**YAML counts under `examples/`** (65 `.yaml` files total):

| Key | Files carrying it at the **root** |
|---|---:|
| `schema_version` | **36** |
| `artifact_version` | **37** |
| both | 36 |
| `artifact_version` only | 1 (`08-e2e-demo/artifacts/scenario.yaml`) |

Distribution by example: `external/00` 6, `07` 5, `01` 5, `08` 4, `04` 4, `00-quickstart` 4,
`06` 3, `03` 3, `02` 3.

**Code hits** for the two identifiers (`.py` files): `src` 88, `tests` 114, `examples` 35,
`runtime` 14, `perf` 6, `tools` 0 — 257 total. Every one classified:

- **Read by code — but only as a *nested* field on a typed artifact class.** Six classes
  declare `schema_version: str` (`skills/catalog.py`, `workflow/definitions.py`,
  `agents/definitions.py` ×2, `products/contract.py`, `skills/grants.py`), and
  `ControlPlaneRegistry.register` **requires** a string `artifact_version` on every validated
  declared artifact — it is load-bearing for D-05's hash-verified bump check
  (`registry.py:420-436`, which normalizes `artifact_version` before hashing so a bump alone
  does not read as a content change).
- **Decoration — every root-level occurrence in the example artifacts.** The documents whose
  version keys are genuinely consumed carry them **nested**, not at root: `agent.yaml` has
  zero root-level `schema_version` and puts both keys under `agent_definition:`;
  `prompt.yaml` likewise. Conversely all 37 root-key files are the hand-marshalled kinds —
  `ontology.yaml`, `events.yaml`, `controlplane.yaml`, `halflife.yaml`, `scenario.yaml`,
  `tokens.yaml`, `experience.yaml`, `a2a.yaml`, `store_*.yaml`, `product.yaml`,
  `analysis_output.yaml`.
- Every example-code read (`declared["schema_version"]`, `declared_class["schema_version"]`,
  `replay_doc["schema_version"]`) subscripts a **sub-document** (`control["product_class"]`,
  `hitl_doc["replay"]`), never the document root.

**Verdict: no `/src`, `/runtime`, or `/tests` code reads a root-level occurrence.** The
quickstart is the clean worked case — all four of its artifact YAMLs carry both root keys and
all eight occurrences are inert, proven by `EntityResolutionSpec` rejecting them outright.
Plan 15-07 and the example rewrites can therefore treat the ~37 root-level key pairs as
churnable, provided each new typed artifact class that *replaces* a hand-marshalled read
declares the two fields itself so the D-05 bump check keeps something to verify.

### A6 — widened No-Hardcoding lint over `tests/`: **3 findings**

Widening applied to **both** `LINTED_TREES` and `RULE_TREE_SCOPE["no-hardcoding"]` (the scope
entry alone is a no-op, as the plan notes, because `run()` iterates `LINTED_TREES` first).

**Exact count: 3.** Per-rule breakdown:

| Rule | Findings |
|---|---:|
| `cinv01a-prompt-shape` | 2 |
| `cinv01b-numeric-table` | **0** |
| `cinv01c-factory-bypass` | 1 |

The three, in full:

1. `tests/agents/test_agent.py:93` — `cinv01c-factory-bypass`. A test helper calls
   `Agent(**values)` directly. This is the one **genuine** finding: CLAUDE.md §6.4 says
   "Tests construct agents the same way, from fixture artifacts."
2. `tests/http_api/test_openapi.py:38` — `cinv01a-prompt-shape`. The `_DRIFT_MESSAGE`
   constant, a multi-sentence failure message naming `make openapi`. Prose-shaped, but a
   diagnostic string, not a prompt.
3. `tests/test_surface_drift.py:78` — `cinv01a-prompt-shape`. The same shape: the
   surface-drift failure message naming `make surface`.

No `cinv01b-numeric-table` findings at all, which is the surprising half of the result — the
1,548-test suite carries no numeric table the rule recognizes.

**Sizing verdict: 3 is far under the plan's "roughly under 30" threshold, so D-IMPL-78 lands
in plan 15-04 as scoped.** Two of the three are false positives of the same class (long
multi-sentence diagnostic messages, which the phase's own conventions actively encourage), so
15-04 will need either an allowlist entry per message or a refinement that distinguishes a
failure message from a prompt. That is a judgment call for the developer — see the checkpoint.

## Deviations from Plan

**None requiring a rule.** Two things worth naming:

1. The `reg` span definition was kept faithful to 15-RESEARCH.md §1 pass 3 rather than widened
   to reproduce the §1.3 number exactly; the −1-per-file consequence is documented above
   rather than silently absorbed, per the plan's own instruction.
2. A6's widening was done by in-process monkeypatch rather than by a scratch file edit, which
   satisfies the "no modification to `tools/lints/__main__.py`" criterion more strongly than a
   revert would.

## Surface impact

`tools/dump_surface.py --report` reports `added (0)`, `removed (0)`, `reshaped (0)` — as
expected, since `dump_surface.py` walks only `/src` and `/runtime` modules defining `__all__`.
Both entries in `docs/surface-changes/15-03-audit-baseline.md` are `Public surface: false`
(`tools/measure_examples.py` and `make measure-examples`), each carrying a single literal
token and `Change type: added`. The live manifest and the frozen baseline were not touched.

## Verification

- `PYTHONPATH=src:runtime .venv/bin/python tools/measure_examples.py --check` — exits 0
- `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/examples/test_surface_audit.py -q` — 29 passed
- `tests/test_surface_drift.py` — passes (no undocumented drift)
- `make lint` — clean
- `make typecheck` — Success, 162 source files
- Human checkpoint (Task 4) — **outstanding**

## Commits

| Task | Commit | Subject |
|---|---|---|
| 1 | `1a10643` | feat(15-03): measure the examples tree's mechanical surface (ERGO-03) |
| 2 | `da5bcdb` | test(15-03): make the Criterion 1 surface audit executable (ERGO-03) |
| 3 | this commit | docs(15-03): record the A1/A3/A6 falsification verdicts |
