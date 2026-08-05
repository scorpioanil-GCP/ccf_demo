---
phase: 15-sdk-ergonomics-the-integration-surface
plan: 14
subsystem: examples
tags: [ergonomics, artifacts, examples, agents, skilling, schema-headers]
requires:
  - ccf.deployment.load_and_boot
  - ccf.deployment.build_operator_registry
  - ccf.controlplane.artifacts.load_artifact
  - ccf.controlplane.registry.ControlPlaneRegistry.register_versioned
  - tools/check_schema_headers.py
  - tools/dump_schemas.py
provides:
  - the second committed schema set — SDK-owned author-versioned classes
  - the worked three-operator deployment, expressed only by its artifact set
  - the two-registration-path pattern the remaining agent examples copy
affects:
  - examples/01-agent-basics
  - examples/02-skilling
  - docs/schemas/
  - public/tutorial/adopters-guide.md
  - public/reference/artifacts/
  - public/how-to/grant-and-revoke-a-skill.md
tech-stack:
  added: []
  patterns:
    - one artifact class, one document
    - author-versioned artifacts register outside the manifest (D-05 bump check)
    - the operator set is the manifest's artifact set, never a builder argument
key-files:
  created:
    - examples/01-agent-basics/artifacts/manifest.yaml (+19 typed documents)
    - examples/02-skilling/artifacts/manifest.yaml (+17 typed documents)
    - tests/examples/test_agent_basics_output.py
    - tests/examples/test_skilling_output.py
    - docs/surface-changes/15-14-examples-01-02.md
    - docs/schemas/ccf.agent-definition.json (+5 more author-versioned classes)
    - docs/surface/examples/after/examples__01-agent-basics__run.json
    - docs/surface/examples/after/examples__02-skilling__run.json
  modified:
    - examples/01-agent-basics/run.py
    - examples/02-skilling/run.py
    - examples/01-agent-basics/README.md
    - examples/02-skilling/README.md
    - tools/dump_schemas.py
    - tools/check_schema_headers.py
    - tests/cli/test_schema_export.py
    - public/tutorial/adopters-guide.md
decisions:
  - author-versioned SDK classes get committed schemas but stay out of SDK_ARTIFACT_CLASSES — a manifest must not register what needs the D-05 bump check
  - the agent's referenced axis-4/axis-5 artifacts DO go in the manifest; they are plain declared artifacts registered with register_typed
  - example 02's decision document sits outside its manifest because it supplies the injected clock, which the registry needs before load_and_boot runs
  - live ledger state is captured in the spine at the step that produced it, not read by the test after the run
metrics:
  duration: ~3h
  completed: 2026-08-04
---

# Phase 15 Plan 14: Examples 01 and 02 Rewrite Summary

Both agent-facing examples are now the call spine an adopter would write —
example 01's mechanical wiring 159 lines to 14, example 02's 118 to 13, and 153
relocatable assert/print lines to zero across the two — with the Gate 2
tautology fixed at both origins, the three-operator case working with no builder
special case, and the channel-2 governance demonstration intact.

---

## Measurement

| Figure | 01 before | 01 after | 02 before | 02 after |
| --- | ---: | ---: | ---: | ---: |
| raw lines | 619 | 481 | 571 | 544 |
| mechanical (`removable`) | 159 | 14 | 118 | 13 |
| relocatable (asserts + prints) | 85 | 0 | 68 | 0 |
| helpers | 41 | 0 | 40 | 0 |
| inline operator block | 64 | 0 | 38 | 0 |
| registration prologue | 46 | 14 | 32 | 13 |
| boot | 8 | 0 | 8 | 0 |

Removal and relocation are reported separately and never summed (D-12). The
raw-line figures move less than the mechanical ones because both files gained
substantial docstrings and both now return a result dataclass the tests read.

Artifact documents: example 01 went from 7 bundles to 20 typed documents,
example 02 from 5 to 18. That increase is what "one class, one document" costs
and what buys closed-world validation plus an honest `$schema` header per
document (15-13 R1).

Measurement ran as `make measure-examples ONLY=<example>` for each example
separately. `git diff --name-only --diff-filter=A docs/surface/examples/after/`
lists exactly two fragments, both slugified from this plan's own trees.

---

## Tasks completed

| Task | Commit | What |
| --- | --- | --- |
| 1 | `7e45c3c` | Example 01: artifacts reshaped, `run.py` to the spine, assertions relocated, plus the blocking schema-target fix |
| 2 | `7d604d4` | Example 02: same, with the three-operator registry and the channel-2 cycle; surface-change fragment covering both |

---

## What each example still demonstrates

**Example 01 — all six axes, each with a check that can fail.** The test module
has one test per axis: archetype composition in dimension 4 and on
`agent.components`; the context contract admitting the served product class;
the Π role reaching both the payload and the conditioning; the regime's excluded
class absent by name; the debt profile gating into the reviewed CAR state; the
prompt artifact resolving with exactly its declared parameters.

**Example 02 — channel-2 governance, unchanged in substance.** The grant, the
exercise, the tier-1 refusal naming its excess scopes, the revocation, the
audited five-action sequence on one log, and the dimension-4 grant-set hash
captured at the exercise step are all still there — now as tests that a runner
can fail. Two of them (`test_every_grant_transition_was_audited`,
`test_dimension_four_carries_the_skill_set_in_force`) are named in the module
docstring as the reason it exists: they are the CLAUDE.md §6.2
audit-by-construction commitments.

**The three-operator case needed no builder special case.** The manifest names
three operator-parameters documents, so the `parameters` mapping has three
entries and the registry holds three operators. No flag, no `None`, no disabled
operator, and `similarity_index_version` simply absent. Plan 15-11's design
holds.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Author-versioned SDK classes had no `$schema` target**

- **Found during:** Task 1
- **Issue:** Every `*.yaml` under an example's `artifacts/` must carry an honest
  header. `ccf.agent-definition`, `ccf.prompt-artifact` and
  `ccf.skill-catalog-entry` are SDK-owned but absent from
  `SDK_ARTIFACT_CLASSES`, so `dump_schemas.py` emitted no schema for them and
  `check_schema_headers.py` rejected any header naming them. They were
  unannotatable.
- **Why they are absent from that set, and must stay absent:** all three carry
  D-IMPL-28 two-field versioning and register through `register_versioned`,
  whose D-05 bump check holds the author's `artifact_version` claim against
  content identity. `load_and_boot` registers through `register_typed`, which
  does not run that check. Adding them to `SDK_ARTIFACT_CLASSES` would have made
  them manifest-addressable and silently dropped that governance — a fix worse
  than the problem.
- **Fix:** a second emitted set, `tools/dump_schemas.author_versioned_classes()`,
  committed as schemas without joining `SDK_ARTIFACT_CLASSES` — the same shape
  15-13 used for the `DeclaredArtifact` envelope. `check_schema_headers.py` now
  reads the union for both the header lookup **and** the envelope route's
  refusal, so an agent definition cannot annotate itself as deployment-authored
  and escape its own contract.
- **Why it lives in `tools/` and not `/src`:** it is a documentation-emission
  concern, and keeping it out of `src` makes it impossible to confuse with
  manifest addressability. It also avoids `ccf.deployment.classes` (tagged
  `algorithmic`, CINV-03) importing `ccf.agents`.
- **Membership is checkable, not editorial:**
  `test_every_author_versioned_class_has_a_committed_schema` asserts every
  member declares an `artifact_version` field and is absent from
  `SDK_ARTIFACT_CLASSES`.
- **Files modified:** `tools/dump_schemas.py`, `tools/check_schema_headers.py`,
  `tests/cli/test_schema_export.py`, six new `docs/schemas/*.json`
- **Commit:** `7e45c3c`

**2. [Rule 1 - Bug] Catalog registration refusals were being discarded**

- **Found during:** Task 2
- **Issue:** `SkillCatalog.register` returns `str | RegistrationRefusal`. The
  pre-rewrite file asserted the result was a `str`; dropping the assert without
  replacing it would have let a refused catalog entry pass silently and the
  example continue against an incomplete catalog.
- **Fix:** a `match` that raises on anything but a version string — stricter
  than the old `assert`, which vanished under `python -O`. The same shape covers
  the agent-definition registration and the impermissible-grant admission.
- **Files modified:** `examples/02-skilling/run.py`
- **Commit:** `7d604d4`

### Deliberate departures from the plan text

**The plan's `# no-schema: DeclaredArtifact` escape hatch was not used, because
it does not exist.** The plan text predates 15-13, which resolved this
differently: deployment-authored documents point their `$schema` at the
committed `ccf.declared-artifact` envelope and declare their own `class_id`.
The tooling's only actual escape hatch is `# ccf-schema: deferred(<plan>)`, and
**no document in either example uses it.** Every `*.yaml` in both directories
carries a real header.

**The agent's referenced axis-4/axis-5 artifacts moved INTO the manifest** —
the opposite direction from the definition and the prompt. They are plain
`DeclaredArtifact` envelopes registered with `register_typed`, which is exactly
what `load_and_boot` does, so the hand-written registration loop in both
examples had nothing the manifest could not do. Their manifest keys are the
long `{tenant}/{artifact_class}/{name}` strings the definitions' refs resolve
to, which makes the manifest and the definition two independent statements of
one key.

**Example 02's `decision.yaml` sits outside its manifest.** That deployment
injects its decision instant as the Control Plane registry's clock so the
audited grant lifecycle is reproducible, and the registry is a constructor
argument to `load_and_boot` — so the instants have to be read one line earlier.
It goes through the same `load_artifact` seam. Example 01 has no injected clock
and keeps its decision document in the manifest as `role: load`. Both files say
why.

**Four assertions in the test modules are marked `**New**` rather than
relocated:** lineage strict equality and declared-vs-resolved operators in each
example. Neither pre-rewrite file had a Gate 2 check, because both built their
plan from `operators.keys()` — the tautology this phase fixes — so there was
nothing to relocate. Marking them new rather than folding them into the
relocation map keeps the "no loss" audit honest in both directions.

**No plan-scoped fragment/`--report` subset test was written** (binding ruling
6). That assertion exists phase-wide.

---

## Verification

| Gate | Result |
| --- | --- |
| `make lint` | exit 0 |
| `make typecheck` | exit 0 — 169 files |
| `make test` | 1808 passed, 2 skipped |
| `make examples` | exit 0 — all ten |
| `make example-01`, `make example-02` | exit 0 |
| `make docs-strict` | exit 0 |
| `make schema-headers DIR=examples/01-agent-basics/artifacts` | exit 0 |
| `make schema-headers DIR=examples/02-skilling/artifacts` | exit 0 |
| `pytest tests/examples/test_agent_basics_output.py` | 17 passed |
| `pytest tests/examples/test_skilling_output.py` | 18 passed |
| `grep -c "assert " examples/0{1,2}/run.py` | 0 and 0 (was 38 and 37) |
| surface manifest + frozen baseline | untouched |

Mutation probes (throwaway, not committed), each confirming an assertion can
fail for the reason it names:

| Probe | Detected by |
| --- | --- |
| `expected.yaml` entity count 2 → 3 (ex. 01) | `test_the_served_payload_matches_the_declared_expectation` |
| `perspective.yaml` role rebound, definition left alone (ex. 01) | `test_axis_3_conditions_the_served_payload_and_dimension_4` |
| `expected.yaml` operator count 3 → 4 (ex. 02) | `test_the_registry_holds_exactly_three_operators` |
| `grant_revoked` dropped from the expected sequence (ex. 02) | `test_every_grant_transition_was_audited` |

The axis-3 probe is the one worth noting: it is a **propagation check**, and it
fired on a wiring fault (two documents that must name the same role disagreeing)
rather than on an artifact edit — which is exactly what the module docstring
claims for that category.

---

## Deferred Issues

One, logged to
`.planning/phases/15-sdk-ergonomics-the-integration-surface/deferred-items.md`:
the HTTP schema route and the `ccf schema export` verb enumerate
`SDK_ARTIFACT_CLASSES`, so they 404 for the six newly committed
author-versioned schemas. Not a defect — nothing serves a wrong schema — but a
consistency question about what that route's contract is. Widening a runtime
surface mid-wave, with two other plans writing concurrently, was out of scope.

---

## Note for plans 15-15 and later

**Example 03 (and any other example with an agent definition, prompt artifact
or skill catalog entry) now has committed schemas to point at.** The header is
an ordinary one:

```yaml
# yaml-language-server: $schema=../../../docs/schemas/ccf.agent-definition.json
```

Do **not** add these classes to `SDK_ARTIFACT_CLASSES` to make them
manifest-addressable — see auto-fix 1 above for why that would drop the D-05
bump check. Register them in adopter code through `register_versioned` and keep
their Control Plane keys in a small `role: load` registration artifact.

---

## Threat Flags

None. No new network endpoint, auth path, file-access pattern, or schema change
at a trust boundary. The one tooling change tightens a gate rather than
loosening it: the envelope route now refuses six more class ids than it did.

Against the plan's threat register: T-15-14-01 (grant/revocation capture lost in
the relocation) is closed by
`test_every_grant_transition_was_audited` and
`test_dimension_four_carries_the_skill_set_in_force`, both mutation-probed.
T-15-14-02 (a fourth operator by builder default) is closed by
`test_the_registry_holds_exactly_three_operators`, whose expected count comes
from a document that plays no part in building the registry. T-15-14-03 (agent
definitions changed by a marshalling rewrite) — both definitions' *content* is
unchanged; only the enclosing document shape moved, which the surface-change
fragment records per document. T-15-14-04 (a snippet bracketing deleted code) —
all 18 markers were re-pointed and every including page was read.

## Self-Check: PASSED

All files claimed above exist on disk; both commit hashes resolve in `git log`.
