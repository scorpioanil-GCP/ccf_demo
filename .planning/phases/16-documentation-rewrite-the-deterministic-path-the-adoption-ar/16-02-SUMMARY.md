---
phase: 16-documentation-rewrite-the-deterministic-path-the-adoption-ar
plan: "02"
subsystem: examples
status: paused-at-checkpoint
tags: [kyc-ubo, source-estate, no-hardcoding, single-writer, artifact-gate]
requires:
  - "16-01 (D-IMPL-94, approved by Dave 2026-08-10, authorises the phase scope)"
provides:
  - "examples/s1-01-hello-context-product/artifacts/source-estate.yaml — the whole KYC/UBO source-estate vocabulary, with a depth->=2 corp->corp ownership chain and per-edge ownershipPercent"
  - "examples/s1-01-hello-context-product/source_estate.py — a deterministic, vocabulary-free interpreter that materialises the estate as JSONL + SQLite"
  - "examples/s1-01-hello-context-product/run.py — a wave-2 minimal driver that makes the directory an example root (plan 16-05 replaces it at wave 3)"
  - "tests/examples/test_source_estate.py — the ten assertions the adoption argument rests on"
  - "tests/examples/test_artifact_schema_headers.py — artifact-directory coverage as a two-sided bijection that arms without a source edit"
  - "docs/surface/examples/FIBO-EXTENSION.md — the provenance record for the extension"
affects:
  - "16-05, 16-07 (replace run.py; read the materialised estate at L1; compare content_hash across substrates)"
  - "16-08, 16-09, 16-10, 16-11 (four wave-4 plans that create example directories in parallel and now need no edit to the coverage gate)"
tech-stack:
  added: []
  patterns:
    - "pure-interpreter generator (16-PATTERNS entry 16, modelled on examples/08-e2e-demo/generator.py)"
    - "two-sided bijection coverage gate (tools/docs_tests/test_diagram_coverage.py model)"
    - "domain values for tests live in the artifact, because tools/lints RULE_TREE_SCOPE covers tests/"
key-files:
  created:
    - examples/s1-01-hello-context-product/artifacts/source-estate.yaml
    - examples/s1-01-hello-context-product/source_estate.py
    - examples/s1-01-hello-context-product/run.py
    - tests/examples/test_source_estate.py
    - docs/surface/examples/FIBO-EXTENSION.md
  modified:
    - tests/examples/test_artifact_schema_headers.py
decisions:
  - "Per-edge ownershipPercent is written LAST in every relationship record, so each measured FIBO line returns verbatim or as a literal prefix and the additive check at the human checkpoint is a readable diff rather than a set comparison"
  - "Emission order is declared order, not seeded-shuffled; the seed drives observation times instead, which keeps it load-bearing without breaking the superset property"
  - "Two output shapes with two purposes: JSONL carries no field the shipped documents lack (what the DGX loaders read); SQLite carries the derived observed_at column (what L1 ingress reads)"
  - "The test module's domain values (threshold, subject entity, ownership relation, natural-person type) live in the artifact's teaching_properties block, because RULE_TREE_SCOPE covers tests/"
metrics:
  tasks_completed: 2
  tasks_total: 3
  tests_added: 10
  completed: 2026-08-10
---

# Phase 16 Plan 02: Extend the KYC/UBO Source Estate Summary

A depth-≥2 corporation ownership chain with per-edge percentages now exists in
an in-repo, deterministic, vocabulary-free source estate — so *"Who ultimately
owns Acme?"* has an answer that requires traversal and aggregation, and
always-on CI can read it without a network.

**Status: PAUSED at the blocking human-verify checkpoint (Task 3).** Tasks 1
and 2 are complete and committed. Task 3 loads the same extension into the four
live FIBO stores on the DGX, which Claude cannot do — no credentials are
present in this environment. **Nothing outside this repository has been
written.**

## What shipped

### Task 1 — the declared estate and the reshaped coverage gate (`c6e3ac0`)

`examples/s1-01-hello-context-product/artifacts/source-estate.yaml` declares the
whole KYC/UBO vocabulary as a `ccf.declared-artifact` envelope
(`class_id: fibo-kyc.source-estate`). It carries every measured record forward
unchanged and extends additively:

| | Shipped | Declared |
|---|---|---|
| Entities | 14 | 14 |
| Relationships | 11 | 16 |
| `isRelatedTo` | 6 | 6 |
| `hasControllingInterestIn` | 1 | 1 |
| `hasOwnershipInterestIn` | 4 | 9 |
| Ownership edges with their own `ownershipPercent` | 0 | 9 |
| Corporation → Corporation ownership edges | 0 | 4 |

The chain is designed so the answer is *interesting*, not merely present:

- **Jane Doe** crosses the 25% threshold on Acme **only** under aggregation —
  12.0% direct, plus 60.0% × 30.0% = 18.0% indirect, totalling 30.0%. No
  passage of any document states 30.0%.
- **Sarah Chen** reaches Acme in three hops for 1.125% — a chain that exists
  and lands nowhere near the threshold. Depth is not significance.
- **Hans Müller** reaches Acme in three hops across three jurisdictions for
  0.1%, giving the Policy axis real work. His Party record carries *no*
  percentage and his edge does, which is the cleanest witness for why FINDING
  F-1's entity-level field cannot express per-edge ownership.
- **John Smith** is 45.0% direct — the case retrieve-then-filter gets right,
  kept so the contrast is visible.

Sarah Chen stays at exactly `25.0`. Both planted near-duplicate pairs survive.
The ownership edges form a DAG, so traversal terminates.

`examples/s1-01-hello-context-product/run.py` is a minimal wave-2 driver whose
module docstring names plan 16-05 as its wave-3 **replacement** (not a
delete-then-recreate). It carries no check and no output.

`tests/examples/test_artifact_schema_headers.py` moves from a literal named
tuple asserted for exact equality to a **two-sided bijection**:

- an *example root* is a directory that directly contains `run.py` — verified
  against the tree, where that predicate returns exactly the directories that
  carry `artifacts/`, while "a directory under `examples/` containing a `.py`"
  returns 12 against 10 and would make the gate unbuildable;
- left side: every example root has a covered `artifacts/` directory;
- right side: every covered `artifacts/` directory sits under an example root;
- both directions reported by name;
- **per-directory non-vacuity** replaces the aggregate document floor;
- `PERMANENTLY_DEFERRED` stays a named set, unchanged.

Three controls run: the bijection refusing in **each** direction against a
synthetic tree; the two real `.py`-bearing non-example directories
(`examples/03-harness-portability/legs/`,
`examples/external/00-hello-context/fixtures/`) excluded, each degrading to a
*named skip* once its retirement wave has run; `fixtures/` excluded **as a
shape**, which keeps the rule true when 16-09 ships its own at wave 4; and a
scratch example collected without any source edit. The module docstring states
why the bijection does not reopen the Phase-15 silent-drop hole and names the
four other places a vanished example is caught.

Collected: **11** parametrized directory ids, including
`examples/s1-01-hello-context-product/artifacts`.

### Task 2 — the generator, the assertions, the provenance record (`61581cc`)

`source_estate.py` is a pure interpreter holding zero vocabulary — only
mechanism roles. It materialises two shapes with two purposes:

- **JSONL** in the shipped FIBO shape, in declared order, carrying **no field
  the shipped documents lack**. Measured: the entity stream is **byte-identical**
  to `mongo-entities.json`; **7 of 11** shipped relationship lines return
  verbatim and the other **4** return as the shipped line with
  `"ownershipPercent"` appended as the last key, so the shipped content is a
  literal prefix. That is what makes the checkpoint's "is it a superset?" check
  a `diff` a human can read.
- **SQLite** on `load_postgres.py`'s table shape plus an `observed_at` column —
  the only derived value, and the reason the SQLite file exists (L1 ingress in
  plan 16-05 needs an observation time; putting it in the JSONL would break the
  superset property).

Determinism: one `random.Random(seed + rng_offset)` per declared stream, every
timestamp derived from the declared epoch, never a clock read. Two runs into
two directories are **byte-identical**, verified.

`tests/examples/test_source_estate.py` — 10 tests, all passing:

| Test | States |
|---|---|
| `test_the_declared_estate_and_its_interpreter_are_both_present` | precondition |
| `test_the_generator_produced_a_non_empty_estate` | precondition (a vacuous pass is the failure mode) |
| `test_an_ownership_chain_of_depth_two_exists` | shortest path ≥ 2, naming intermediates |
| `test_every_ownership_edge_carries_its_own_percentage` | the F-1 remedy |
| `test_the_ultimate_beneficial_owner_requires_aggregation` | direct < 25.0 ≤ aggregate, aggregate ≠ direct |
| `test_the_boundary_case_percentage_is_frozen` | Sarah Chen at exactly 25.0 |
| `test_both_planted_near_duplicate_pairs_survive` | Similarity stays non-trivial |
| `test_the_generator_is_deterministic` | byte-identical across two runs |
| `test_the_generator_never_touches_the_context_graph` | AST check over `imported_module_names` **and** `submodule_import_names` (the CR-02 hole) |
| `test_the_generator_refuses_to_run_without_its_artifact` | CLAUDE.md §6.4 / C-2 |

Every domain value those tests need is read from the artifact's
`teaching_properties` and `field_roles` blocks — none is written as a test
constant, because `tools/lints`' `RULE_TREE_SCOPE` covers `tests/` as well as
`examples/`.

`docs/surface/examples/FIBO-EXTENSION.md` records what F-1 found, what was
added, the measured before/after table, and — explicitly — what the extension
does **not** claim: it is synthetic ownership structure layered onto a real
FIBO shape, not a corporate registry, not a compliance artifact, not CCF's
Context Graph, and it makes no claim about the four DGX stores.

## Measured: the jurisdiction count

**Four distinct `jurisdiction` values exist in the shipped entity records:**
`US-DE`, `US-NY`, `DE`, `GB`. `16-RESEARCH.md` Assumption A2 recorded only
three as directly observed and flagged CONTEXT's fourth (`GB`) as unread — the
fourth is **Omega Securities' `GB`**, which the research pass missed.
**D-03's "four jurisdictions" claim stands as written and needs no downstream
correction.** Nothing was added to reach four.

## Verification

| Check | Result |
|---|---|
| `pytest tests/examples/test_source_estate.py tests/examples/test_artifact_schema_headers.py -q` | 34 passed |
| `python examples/s1-01-hello-context-product/run.py` | exit 0 |
| `python -m tools.lints --all` | exit 0 |
| `git grep -n "192.168.4.76" -- examples/ public/ src/ runtime/` | no hits |
| `git diff --stat -- src/ runtime/` | empty |
| `grep -ci "password\|dsn\|bearer" .../source-estate.yaml` | 0 |
| `grep -c "EXPECTED_ARTIFACT_DIRECTORIES" .../test_artifact_schema_headers.py` | 0 |
| `grep -c "len(documents) >= 100" .../test_artifact_schema_headers.py` | 0 |
| `grep -n "assert \|print(" .../run.py` | no hits |
| `grep -n "assert\|print(" .../source_estate.py` | no hits |

## Deviations from Plan

None affecting scope. Two judgement calls inside the plan's latitude, both
recorded above under `decisions`:

1. **Emission order is declared order, and the seed drives observation times
   rather than row order.** The plan's `08-e2e-demo` reference uses a seeded
   RNG for row interleaving, but that generator produces *noise*; here the
   estate is fully declared, and shuffling would have turned the human
   checkpoint's superset check into a set comparison on live data. The seed
   stays load-bearing because it drives the observation timeline the SQLite
   estate carries.
2. **Per-edge `ownershipPercent` is the last key in every relationship
   record**, so the shipped content is a literal prefix of the extended line
   (threat T-16-02-02's "verified before any loader runs" is then a `diff`).

## Pre-existing failures outside this plan's scope

Three test failures exist at this tree and are **not** caused by this plan.
Each is already owned by a named plan in this phase, so they are recorded here
rather than added to the shared `deferred-items.md` (which three sibling agents
are executing against concurrently):

| Failure | Owner |
|---|---|
| `tools/docs_tests/test_snippet_gate.py::test_a_deleted_section_marker_fails_the_strict_build` | plan **16-04** (the `[start:ontology]` marker no longer exists in `examples/00-quickstart/run.py`) |
| `tools/docs_tests/test_snippet_gate.py::test_the_unmodified_source_builds_clean` | plan **16-04**, same cause |
| `tools/publish_scan_tests/test_docstring_leaks.py::test_no_docstring_reproduces_whitepaper_body_text` | plan **16-19** (`ProductClassDeclaration`'s docstring; carve-out ruled by **D-13**) |

## Threat Flags

None. No new network endpoint, auth path, file-access pattern or trust-boundary
schema change. Every disposition in the plan's threat register is discharged in
tree by the checks tabled above, except **T-16-02-02**'s live-store half, which
is the checkpoint's.

## Blocked: Task 3 (checkpoint, `gate="blocking"`)

**State of the four live stores: NOT WRITTEN. Nothing outside this repository
has been touched.**

`NEO4J_PASSWORD` and `PGPASSWORD` for `192.168.4.76` are not present in this
environment (`16-RESEARCH.md` § Environment Availability), and the four ports
being open is not the same as being able to write. The out-of-tree JSONL files
at `/home/parkave/fluree/examples/fibo/` are also **unmodified** — this plan
wrote only in-repo files.

What the operator must do is quoted in the structured checkpoint report
returned to the orchestrator, and in the plan at
`16-02-PLAN.md` lines 419–462.

## Self-Check: PASSED

All six declared files exist on disk. Both commits (`c6e3ac0`, `61581cc`) are
present in `git log`.
