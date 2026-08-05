---
phase: 15-sdk-ergonomics-the-integration-surface
plan: 18
subsystem: examples
tags: [ergonomics, artifacts, examples, a2a, admission, re-domaining, schema-headers]
requires:
  - ccf.deployment.load_and_boot
  - ccf.deployment.build_operator_registry
  - tools/check_schema_headers.py
  - tools/measure_examples.py
  - docs/schemas/ccf.agent-definition.json
  - docs/schemas/ccf.prompt-artifact.json
provides:
  - the two-manifests-per-example pattern for cross-process deployments
  - cross-deployment agreement as a falsifiable assertion category
  - Phase 16's banking A2A/MCP worked instance
affects:
  - examples/04-cross-process
  - public/how-to/run-agents-cross-process.md
  - perf/suites/crossproc/conftest.py
tech-stack:
  added: []
  patterns:
    - one artifact class, one document
    - two deployments, two manifests, two Control Planes
    - documents that must agree across a trust boundary are authored twice, never shared
    - a trust-policy REQUEST is authorable; a trust policy is not, because it carries key material
key-files:
  created:
    - examples/04-cross-process/artifacts/producer-manifest.yaml
    - examples/04-cross-process/artifacts/consumer-manifest.yaml
    - examples/04-cross-process/artifacts/peering-trust.yaml
    - examples/04-cross-process/artifacts/producer-peering.yaml
    - examples/04-cross-process/artifacts/consumer-resolution-spec.yaml
    - tests/examples/test_cross_process_output.py
    - docs/surface-changes/15-18-example-04.md
    - docs/surface/examples/after/examples__04-cross-process__run.json
    - docs/surface/examples/after/examples__04-cross-process__producer_child.json
  modified:
    - examples/04-cross-process/run.py
    - examples/04-cross-process/producer_child.py
    - examples/04-cross-process/README.md
    - public/how-to/run-agents-cross-process.md
    - perf/suites/crossproc/conftest.py
decisions:
  - the consumer authors its own policy bundle, product class and TTL ceiling rather than reading the producer's — a shared document makes the entitlement check unfalsifiable (Dave, checkpoint Ruling 2)
  - the four domain-named Python identifier renames stay in commit two; the criterion's intent was no LOGIC change, and every .py hunk is a symmetric rename (Dave, checkpoint Ruling 1)
  - the unfalsifiable-agreement defect family is systemic, not incidental — 15-17 found the same shape in example 06 the same wave, and 15-21's audit should cite both
  - the consumer's federation entity rule becomes a `ccf.resolution-spec` at standard nesting, deleting the bespoke `_consumer_resolution_spec` translation
  - `peering-trust.yaml` is a trust-policy REQUEST, not a `ccf.peering-trust-policy`, because that class requires per-run key material
  - the banking scenario is the whitepaper's own §8.3 Pattern 4 exemplar (syndicated lending covenant cross-reference), not an invented one
  - three domain-named Python identifiers were renamed in commit two, a deliberate departure from the plan's "no .py line" criterion
metrics:
  duration: ~4h
  completed: 2026-08-04
---

# Phase 15 Plan 18: Example 04 Rewrite and Re-domaining Summary

The cross-process example now runs both legs over the streamlined surface —
mechanical wiring 143→13 lines in the producer and 53→13 in the consumer — and
its A2A trust boundary came out of the rewrite *stronger* than it went in,
because the entitlement check that used to compare two reads of one file now
compares two independently authored documents.

**Status: COMPLETE.** Task 3's blocking checkpoint was approved by Dave with two
explicit rulings, recorded below.

---

## The two commits

| # | Commit | What |
| --- | --- | --- |
| 1 | `368d028` | Surface rewrite. Property-intelligence domain vocabulary unchanged — the diff contains no domain rename. |
| 2 | `b464de8` | Re-domain to syndicated lending. No surface change — no new SDK call, no changed wiring, no altered assertion structure. |

---

## Checkpoint rulings (Task 3, Dave, 2026-08-04)

Verified independently by the coordinator before the ruling:
`git show 368d028 | grep -icE "covenant|syndicat|lending"` returns **0**;
commit two's `.py` hunks are symmetric renames (`producer_child.py` +8/-8,
`run.py` +4/-4, the test module +4/-4); the admission path is `gate.admit` →
`match AdmittedProduct` → `worker.ingest_admitted`, unshortened; `src/ccf/
deployment/` carries only docstring *mentions* of the `ccf.products.gates` ban
and no import, so D-15A's lint is untripped; and
`test_a_tampered_envelope_is_refused` explicitly rules out a test that would
also pass on an untampered envelope.

**Ruling 1 — the four identifier renames are accepted, and stay in commit two.**
Dave was offered both alternatives (move them into commit one, or revert them)
and chose to accept them where they are. The criterion's intent was *no logic
change in commit two*, and that holds: every `.py` hunk is a symmetric rename.
Leaving `SituationPlan` and `federated_entity_uris` in a syndicated-lending
example would have made the re-domaining cosmetic, with the old domain still
legible in exactly the code an adopter copies. The one asymmetric file,
`perf/suites/crossproc/conftest.py` (+8/-6), is comment-only — a reuse rationale
that still said "property-intelligence domain values" and would otherwise have
become a lie. Judged a correct call, not scope creep.

**Ruling 2 — the four extra consumer documents are accepted, and are the most
valuable thing in this plan.** See the next section, which the coordinator
directed me to state as a finding rather than as an unrequested addition.

Also accepted without change: the Gate-2 tautology I wrote, caught with my own
mutation probe, and fixed with the honest limit stated in the test docstring.

---

## Measurement

| Figure | producer_child.py before | after | run.py before | after |
| --- | ---: | ---: | ---: | ---: |
| mechanical (`removable`) | 143 | 13 | 53 | 13 |
| helpers | 41 | 0 | 25 | 0 |
| inline operator block | 62 | 0 | 0 | 0 |
| boot | 8 | 0 | 8 | 0 |
| registration prologue | 32 | 13 | 20 | 13 |
| relocatable (asserts + prints) | 14 | 1 | 68 | 1 |
| raw lines | 630 | 553 | 533 | 519 |

Removal and relocation are reported separately and never summed (D-12). The
one remaining `relocatable` line in each file is a `print`: the child's `READY`
handshake announcement and the parent's stderr passthrough on failure. Neither
is an assertion.

Artifact documents went from 5 bundles to 27 typed documents (25 manifest-named
across two manifests, plus the two author-versioned ones). Every one carries a
real `$schema` header — no `# no-schema:` escape hatch and no
`# ccf-schema: deferred(…)` marker in this directory.

---

## THE FINDING — the A2A entitlement check was unfalsifiable, and the reshape fixed it

The brief asked me to report if the streamlined surface made any load-bearing
demonstration harder to see. It did not. It did the opposite: it surfaced a
pre-existing defect in the example that exists to demonstrate A2A admission
verification, and fixing it is the most valuable thing in this plan (Ruling 2).

### The defect

Pre-rewrite, the consumer was "independently agreeing" with the producer **using
the producer's own document**. Both processes read one
`artifacts/controlplane.yaml`; `run.py` computed
`producer_policy_version = content_hash(control["policy_bundle"])`, registered
that same mapping as the consumer's own bundle, and asserted
`policy_version == producer_policy_version`. That compared two reads of one
file. It could not fail, and dropping the policy bundle from both sides would
have kept it green.

### The same defect family, one wave over

Plan 15-17 found the same shape in `examples/06-decision-replay`: lineage strict
equality comparing a value against itself, in both the original decision **and**
in the reproduction meant to prove it. Two independent instances in one wave is
systemic rather than incidental, and both share a cause worth naming: **neither
was visible until typed artifacts gave the declared side an authored source.**
While the declaration and the resolution came out of the same bundle read, no
amount of reading the assertion could tell you it was comparing a value with
itself. 15-21's audit should cite 15-17 and 15-18 together.

### The fix

The reshape gives producer and consumer **two manifests and two separate
documents** with identical content:

- `policy-bundle.yaml` / `consumer-policy-bundle.yaml`
- `product-class.yaml` / `consumer-product-class.yaml`
- `product-governance.yaml` / `consumer-product-governance.yaml`
- `producer-peering.yaml` / `peering-trust.yaml`

Each side now states, on its own authority, what it asserts or what it will
admit. Editing either alone makes the inbound product's asserted regime fall
outside the consumer's grant and **admission refuses**. Verified by mutation in
both directions (probes 1 and 2 below). This is a new assertion category the
test module names explicitly: *cross-deployment agreement checks*, distinct
from independent expectations and from propagation checks.

### Everything else about the boundary is untouched

Signing, inbound verification, the Control Plane admission check before
anything reaches L2, lineage set-union, and the tampered-envelope refusal are
the same calls in the same order. Two things got *stricter*:

- `gate.admit`'s result is discriminated with a `match` on `AdmittedProduct` /
  `GateRefusal` rather than `assert isinstance(...)`. An `assert` vanishes under
  `python -O`; a `match` whose non-admitted arm raises does not.
- The admission path is now the only thing between the wire and
  `worker.ingest_admitted`; there is no wiring helper anywhere near it.
  `ccf.deployment` may not even import `ccf.products.gates`
  (`cinv02-deployment-gates`), so no helper could have shortened it.

### The disjointness guard the union assertion needed

`consumer-lineage.yaml`'s operators are deliberately disjoint from the
producer's. The relocated test now **asserts that disjointness first**, then
asserts the union. Without the first assertion, a merged lineage produced by
*replacement* would satisfy the union assertion whenever the sets overlapped.
Probe 3 confirms it fires.

---

## Mutation probes — what was injected, what caught it

Ten faults injected (throwaway, not committed). Ten caught.

| # | Injected fault | Caught by |
| --- | --- | --- |
| 1 | `jurisdiction: GB` → `FR` in `consumer-policy-bundle.yaml` only | admission refused at `peering-policy-binding`; the spine's non-admitted arm raised |
| 2 | same edit in `policy-bundle.yaml` only | same refusal, from the other side |
| 3 | consumer lineage operator changed to overlap the producer's | `test_inbound_lineage_extends_by_set_union_and_never_replaces` (the disjointness guard) |
| 4 | `_tampered` returns the genuine payload — an **untampered** second envelope | the spine's "ADMITTED a tampered envelope" arm raised |
| 5 | `required=operators.keys()` **plus** a dropped key from `product-class.yaml` | `test_every_declared_operator_actually_ran` |
| 6 | a fifth operator key added to `consumer-product-class.yaml` only | `test_the_consumer_admits_only_a_product_carrying_its_declared_operators` |
| 7 | `entity_count: 4` → `5` in `expected.yaml` | `test_the_producer_payload_matches_the_declared_expectation` |
| 8 | `worker.ingest_admitted` call replaced with a no-op | `test_the_admitted_product_reached_l3_only_through_l2` (graph digest unmoved) |
| 9 | `producer_hash` changed in `peering-trust.yaml` only | admission refused at `ccf_producer` |
| 10 | `product-class.yaml`'s `$schema` repointed at `ccf.perspective.json` | `make schema-headers` — eight validation errors, exit 2 |

Probes 1, 2 and 4 were re-run after the re-domaining commit and still fire, so
the boundary survived the vocabulary change.

**Probe 5 is the one worth dwelling on.** My first version of
`test_every_declared_operator_actually_ran` compared
`assembled.operators_invoked` against
`assembled.servable.product.lineage.operators_invoked` — the *same value*. It
passed the probe. That is precisely the anti-pattern this phase has hit six
times, and I caught it only because I ran the probe. The fixed assertion reads
`required_operator_keys` off the artifact and compares it to what the engine
resolved, and the test docstring states plainly that **editing the artifact
alone is still not detected** (both ends move together — 15-13 R6). The
independent dimension comes from the *consumer's* declaration instead, which no
producer-side code reads: `test_the_consumer_admits_only_a_product_carrying_its_declared_operators`.

---

## Deviations from Plan

### [Rule 3 — Blocking] `perf/suites/crossproc/conftest.py` reads this example's artifacts

- **Found during:** Task 1, by the full test suite —
  `tests/perf_smoke/test_smoke.py::test_suite_runs_untimed[crossproc]` failed
  with `FileNotFoundError: .../artifacts/ontology.yaml`.
- **Why in scope:** directly caused by this task's changes; the perf fixture
  spawns example 04's child and reads its artifacts to address the two
  surfaces.
- **Fix:** repointed the four `_load` calls at the typed documents
  (`producer-manifest.yaml`, `product-class.yaml`, `producer-peering.yaml`,
  `peering-trust.yaml`, `decision.yaml`). No timing logic touched.
- **Commit:** `368d028`

### Deliberate departures, each reasoned

**1. The how-to page's include was repointed in commit one, not two.**
The plan lists `public/how-to/run-agents-cross-process.md` under Task 2, but
`a2a.yaml` ceases to exist in commit one and `make docs-strict` goes red on a
missing snippet. The include repoint and the prose that had become false landed
in commit one; the domain prose landed in commit two.

**2. Three Python identifiers renamed in commit two.** `SituationPlan` →
`CovenantSlicePlan`, `AssembledSituation` → `AssembledCovenantSlice`,
`build_situation_product` → `build_covenant_slice_product`, plus the result
field `federated_entity_uris` → `contribution_uris`. The plan's acceptance
criterion says commit two touches "no `.py` logic line"; these are renames, not
logic, and no logic line changed. Leaving "situation" in a banking example
would itself be a re-domaining defect. The test module's only commit-two edits
are the matching rename and one docstring noun. **Disclosed at the checkpoint
and accepted — Ruling 1.**

**3. A note added to the surface-change fragment in commit two.** Every
`Before:` clause in `docs/surface-changes/15-18-example-04.md` quotes the
pre-rewrite property-intelligence names, which would read as stale after the
re-domaining. One paragraph explains that the `Before:` names are deliberately
left as they were, because the fragment is a record of what an adopter migrates
*from*. The re-domaining itself is not logged there, per the plan.

**4. The consumer got five documents the plan named only one of.** The plan
asked for the consumer's own `ccf.resolution-spec`; it also has its own policy
bundle, product class, product governance and decision instant. This is not an
addition to scope — it is the fix for the defect described under THE FINDING
above, and it is what Ruling 2 accepts. Those four are exactly the values the
admission check compares across the trust boundary, and sharing them left the
check unfalsifiable. `consumer-decision.yaml` exists for a smaller reason worth
stating separately: a consumer reading the producer's clock would take freshness
from the party whose freshness it is checking.

**5. `producer-peering.yaml` split out of the consumer's trust document.** The
pre-rewrite `a2a.yaml` held both sides' peering values and both processes read
it. Splitting it means the producer's asserted identity and the consumer's
entitlement are two statements; probe 9 is only possible because of the split.

### Nothing re-domained outside this example

`git diff --name-only HEAD~1 -- examples/ | grep -v 04-cross-process` is empty
for commit two. D-IMPL-52's horizontal domain mix stands.

---

## The banking scenario, and where it comes from

Syndicated lending covenant cross-reference is the whitepaper's own canonical
Pattern 4 Wholesale exemplar (`docs/CCF_Whitepaper_1-2.md` §8.3 Pattern 4, and
the Mode 3 assembly at §7.6 that composes against it). It was chosen because it
already has this example's shape rather than because the example could be bent
to fit it: the covenant package is partitioned across the syndicate under
confidentiality terms, so no single party's fabric holds the whole graph in
trust-clean form, and the boundary the product crosses is
**cross-organizational rather than merely cross-process** — which is the
distinction Pattern 4 exists to name.

Mapping: producer = lead arranger (`harborline-syndications`, peer
`harborline-lead-arranger`); consumer = participant bank (peer
`hollis-participant-bank`); product class
`harborline-syndications.syndicated-covenant-context`, after the whitepaper's
own `SyndicatedCovenantContext`. Entity classes: `facility`, `covenant`,
`compliance_certificate`, `borrower_disclosure`. The restricted class the
policy operator substitutes out is a material-adverse-change notice — the
confidentiality envelope the whitepaper describes, made mechanical.

---

## Verification

| Gate | Result |
| --- | --- |
| `make lint` | exit 0 |
| `.venv/bin/python -m tools.lints --all` | exit 0 |
| `make typecheck` | exit 0 — 169 files |
| `pytest tests` | 1872 passed, 2 skipped |
| `make examples` | exit 0 — all ten |
| `make example-04` | exit 0 |
| `make docs-strict` | exit 0 |
| `make schema-headers DIR=examples/04-cross-process/artifacts` | exit 0 |
| `pytest tests/examples/test_cross_process_output.py` | 19 passed |
| `grep -cE "^def _(load\|instant\|resolution_spec\|consumer_resolution_spec\|envelopes)"` | 0 in both files |
| surface manifest + frozen baseline | untouched; `make surface` never run |
| `after/` fragments | both slugify from `examples/04-cross-process/`; measured with `ONLY=`; no other example's fragment touched |
| commit-one diff | no domain rename |
| commit-two diff | no SDK call, no wiring change, no assertion-structure change |

Snippet markers: nine in `run.py` (`boot` is new; the other eight are
re-pointed in place). Every including section of
`public/how-to/run-agents-cross-process.md` was opened and read against its new
target — four prose passages had become false after the assertions moved to
`tests/` and were corrected, and the `artifacts/a2a.yaml` literal include was
repointed at `artifacts/peering-trust.yaml`.

---

## Threat Flags

None. No new network endpoint, auth path, file-access pattern, or schema change
at a trust boundary. The trust boundary this example carries is unchanged in
mechanism and strictly harder to fake in configuration: four documents that
previously agreed by construction now have to agree on purpose.

## Self-Check: PASSED

All files claimed above exist on disk; both commit hashes resolve in `git log`.
