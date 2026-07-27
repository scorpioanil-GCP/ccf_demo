---
phase: 06-phase-i-3-cross-process-harness-adapters
plan: 15
subsystem: harness
tags: [harness, portability, replay, conformance, XPRC-03]
requires:
  - "runtime/ccf_runtime/adapters/{claude_agent,adk,langgraph} (06-12/13/14)"
  - "src/ccf/harness/protocol.py (06-11)"
  - "src/ccf/replay/record.py HarnessTrace (06-11, D-25)"
provides:
  - "The harness-neutrality proof: one agent definition, three harnesses, equal governed replay records"
  - "build_harness_leg(param) — the three legs, drivable outside a parametrized fixture"
affects:
  - "tests/conformance/test_harness_adapter.py"
tech-stack:
  added: []
  patterns:
    - "Recover the delivered Context Product out of the harness-native carrier, then compare across harnesses — never against the value the test already holds"
    - "Build each harness's replay record from that harness's own run, so governed equality is an observation and not an identity"
key-files:
  created:
    - tests/conformance/test_harness_portability.py
  modified:
    - tests/conformance/test_harness_adapter.py
decisions:
  - "Reused the existing covenant_analytics.yaml and grants.yaml agent definitions rather than adding a fixture — 'one artifact, not three that agree' is stronger when it is literally the artifact the conformance suite already drives"
  - "The 'names no harness' check runs over the definitions' canonical bytes, not the YAML file text — the bytes are what the factory consumed"
metrics:
  duration: ~35m
  completed: 2026-07-27
---

# Phase 06 Plan 15: Harness Portability Proof Summary

One agent definition artifact, loaded once into one `Agent` object, executed
under all three D-IMPL-24 reference adapters, delivering byte-identical Context
Product bytes and producing replay records exactly equal on every governed
field with harness-attributable values isolated in `harness_trace` — and the
whole claim re-run for a second, distinct agent (D-23).

## What shipped

`tests/conformance/test_harness_portability.py` — 10 tests, all three harness
legs, `CCF_REQUIRE_HARNESSES=1` green.

- **Consumption.** The product is *recovered out of each harness-native
  carrier* by lifting JSON documents from the strings the adapter placed there
  (`json.JSONDecoder().raw_decode` from each `{`, keeping documents with a
  `schema_name` key). This handles all three carrier shapes without naming any
  of them: one adapter carries the product as its own string, one joins it into
  a single system prompt, one hands over a callable that will produce it. The
  three recovered byte-strings are compared **to each other**; they are also
  checked against what the fabric admitted.
- **Governed equality (D-18).** `_governed_fields()` canonically serializes the
  four governed dimensions, `tenant_id`, and dimension 3's `assembly_mode` and
  `model_version`, keyed by name so a divergence names itself. No `model_dump()`
  anywhere (T-06-90).
- **Not equal by construction.** Each harness's record is built from that
  harness's own pass through the seams: dimension 5's
  `product_content_address` comes from the product recovered from *that*
  adapter's carrier, dimension 4 from the agent's own conditioning, dimension
  3's harness block from a real execution through seam 4, and seam 3's emission
  is captured and compared separately.
- **Isolation.** `harness_trace` is excluded from the governed comparison and
  positively asserted: each names its own harness, none is `NO_HARNESS`, token
  counts are non-zero, and the three canonical serializations are all distinct.
- **Structural guards.** The governed / harness-attributable / metadata
  classification is asserted **exhaustive** over `DecisionReplayRecord` and
  `ModelVersionRecord`, so a future field cannot land in no bucket and be
  silently ungoverned. A live record is asserted to carry exactly five
  dimensions, counted by shape (fields whose value is a `CCFContract`), not by
  a field-count literal (T-06-89, INV-CH7-80).
- **Harness-free definition (CLAUDE.md §6.5).** Forbidden tokens are *derived*
  from the adapters' own `HARNESS_ID`s and the harness module names, minus a
  named generic-segment exclusion (`agent`, `sdk` — CCF's own vocabulary, so
  asserting their absence would assert something false rather than something
  strong). Both definitions are checked.
- **D-23.** The second agent's three records agree with each other and its
  governed field set differs from the first's, with `agent_definition_hash` and
  `grant_set_hash` proven distinct.

## Teeth, proven by mutation (not asserted)

| Mutation | Result |
|---|---|
| ADK adapter rewrites the delivered product bytes (same length, `acme-bank` → `acme-BANK`) | 3 failed — byte-identity fails, and the governed comparison fails **naming `content_generation_path`** |
| ADK adapter drops its harness trace (returns an empty `HarnessTrace()`) | 1 failed — the isolation test, on absence rather than on divergence |

Both adapters were restored; `git status` clean of adapter changes before
commit. A trace reporting *another* harness's identity is caught by the same
assertion class (`trace.harness_id == leg.harness_id`).

## Deviations from Plan

### [Rule 3 — Blocking] The legs were only reachable one at a time

`harness_leg` is a parametrized fixture, which hands out one leg per test by
construction — and the portability claim is precisely about holding all three
at once. Extracted `build_harness_leg(param)` from the fixture body with **no
change to any leg**, and named `HARNESS_PARAMS` once so a harness that joins
the conformance bar joins this proof in the same commit.
Commit `531e485`. Existing suite: 48 passed, unchanged.

### Corrected acceptance criteria

Per `<plan_criteria_discipline>`, three criteria were false or weak against the
tree as it is. All three were corrected to the property they were reaching for:

1. **"`grep -c 'AgentFactory\|build_agent'` shows a single construction site"** —
   false: the new module never calls `AgentFactory`; `World` does, and the grep
   would return `0`. A source-text count also cannot distinguish a construction
   from a mention. **Implemented instead:** the same `Agent` *object* is passed
   to all three adapters, and every record's `agent_definition_hash` is asserted
   equal to that object's identity. That is the literal reading of "unmodified".
2. **"A test asserts the YAML contains none of `claude`, `adk`, `langgraph`"** —
   implemented over the definitions' **canonical bytes** rather than the file
   text (a comment in a fixture file is not something the agent carries), and
   with the token list **derived** from the adapters' declared harness ids and
   module names rather than authored, so a fourth adapter cannot arrive with a
   vendor name the test never heard of. The plan's four literals are asserted to
   be a subset of the derived set, so the derivation cannot silently shrink.
3. **`-k 'product or byte'` / `-k 'governed'` / `-k 'harness_trace or isolat'` /
   `-k 'two_agent or second_agent'` selectors** — verified each selects a
   non-empty set rather than passing by executing nothing (pytest exit 5):
   1 / 3 / 1 / 1 tests selected respectively. Test names were chosen to satisfy
   them without adding any redundant test.
4. **"`grep -c 'model_dump()'` is 0"** — this is the exact defect class the
   phase kept hitting: a source-text grep that cannot tell a violation from a
   *mention* of one. `grep -c` returns **1**, on the docstring sentence
   explaining why the comparison does not use `model_dump()`. The docstring was
   kept and the property verified structurally instead — an AST walk over the
   module finds **0** `model_dump` and **0** `model_dump_json` call nodes.

### Fixture reuse instead of a new artifact

`files_modified` listed `tests/fixtures/banking/agents`. No fixture was added:
the two definitions the conformance suite already drives are exactly the two
this proof needs, and reusing them makes "one artifact, not three that happen to
agree" literally true rather than newly arranged. `tests/fixtures/banking` is
unchanged.

## Limitations, stated plainly

- **`McpSkillRegistry` threading (open gap 1, 06-16 scope).** The proof does not
  invoke an `mcp`-transport skill through an `Agent`, so it neither depends on
  nor works around that gap. Seam 2 exposure and the adapters' catalog-entry
  introspection (`invoke_skill(name)` with no arguments) are exercised and work.
  The equivalence claim is **not** weakened to route around it — it simply does
  not reach that path.
- **`AdmittedProduct` binding (open gap 2, 06-16 scope).** Not touched. This
  proof is read-side and effect-capture-side; nothing here enters L3.
- **Scope of "equivalent".** D-18's split is what is proven: exact equality on
  the governed fields listed above plus the delivered product bytes and the
  seam-3 emission. It is *not* a claim that the three records are byte-identical
  in full — they must not be, and `harness_trace` is asserted to differ.
- **Dimensions 1 and 5's operator steps are fabric-side and identical by
  construction**, because it is the same fabric operation under each adapter —
  which is the point. The harness-sensitive governed values are
  `product_content_address` (from the recovered product) and dimension 4, and
  mutation 1 confirms the former is live.
- **`examples/03-harness-portability`** with its README remains Phase 8 scope
  (D-06). This is the I.3 precursor and ships as conformance so the claim is in
  CI from the wave it was made.

## Verification

| Check | Result |
|---|---|
| `CCF_REQUIRE_HARNESSES=1 pytest tests/conformance/test_harness_portability.py -q` | 10 passed |
| `CCF_REQUIRE_HARNESSES=1 pytest tests/conformance/test_harness_adapter.py -q` | 48 passed (unchanged by the refactor) |
| `pytest -q` (full suite) | **936 passed, 2 skipped** (baseline 926 + 10 new; zero regressions) |
| `python -m mypy` | Success: no issues in 99 source files |
| `python -m tools.lints --all` | exit 0 (CINV-02 green, not widened) |
| Harness imports in `/src` | none — the new module imports no harness SDK and names no harness SDK type |

## Commits

- `531e485` refactor(06-15): expose the harness legs outside the parametrized fixture
- `69d88f0` test(06-15): the harness-neutrality proof — one definition, three harnesses

## Self-Check: PASSED

- `tests/conformance/test_harness_portability.py` — FOUND
- `tests/conformance/test_harness_adapter.py` — FOUND
- commit `531e485` — FOUND
- commit `69d88f0` — FOUND
