---
phase: 15-sdk-ergonomics-the-integration-surface
plan: 20
subsystem: examples
tags: [ergonomics, artifacts, examples, mcp, external-consumer, schema-headers]
requires:
  - ccf.deployment.load_and_boot
  - ccf.deployment.build_operator_registry
  - ccf.controlplane.artifacts.DeclaredArtifact
  - ccf.controlplane.artifacts.ProductClassDeclaration
  - tools/check_schema_headers.py
  - tools/measure_examples.py
provides:
  - the last of the eight example rewrites
  - a mutation-proved zero-CCF-import guard
  - the eighth `docs/surface/examples/after/` example fragment set
affects:
  - examples/external/00-hello-context
  - tests/examples/test_ext00_hardening.py
tech-stack:
  added: []
  patterns:
    - one artifact class, one document
    - the deployment's parsed artifact set travels on the assembly result
    - a guard is verified to refuse, not only to pass
key-files:
  created:
    - examples/external/00-hello-context/artifacts/manifest.yaml
    - examples/external/00-hello-context/artifacts/resolution-spec.yaml
    - examples/external/00-hello-context/artifacts/policy-bundle.yaml
    - examples/external/00-hello-context/artifacts/operator-parameters-traversal.yaml
    - examples/external/00-hello-context/artifacts/operator-parameters-temporal.yaml
    - examples/external/00-hello-context/artifacts/operator-parameters-policy.yaml
    - examples/external/00-hello-context/artifacts/operator-parameters-similarity.yaml
    - examples/external/00-hello-context/artifacts/perspective.yaml
    - examples/external/00-hello-context/artifacts/product-class.yaml
    - examples/external/00-hello-context/artifacts/product-governance.yaml
    - examples/external/00-hello-context/artifacts/focus.yaml
    - examples/external/00-hello-context/artifacts/decision.yaml
    - examples/external/00-hello-context/artifacts/expected.yaml
    - tests/examples/test_ext00_serve_output.py
    - docs/surface-changes/15-20-external.md
    - docs/surface/examples/after/examples__external__00-hello-context__serve.json
    - docs/surface/examples/after/examples__external__00-hello-context__run.json
  modified:
    - examples/external/00-hello-context/serve.py
    - examples/external/00-hello-context/run.py
    - examples/external/00-hello-context/README.md
    - examples/external/00-hello-context/artifacts/events.yaml
    - examples/external/00-hello-context/artifacts/experience.yaml
    - examples/external/00-hello-context/artifacts/tokens.yaml
    - tests/examples/test_ext00_hardening.py
decisions:
  - "the Gate 2 tautology existed TWICE in this tree, not once: `serve.py` built its plan with `operators.keys()`, and `run.py`'s replay environment did the same — which would have reproduced the original decision's tautology inside the replay that exists to prove that decision"
  - "`run.py`'s 22 relocatable print lines CANNOT move: eight of its ten print calls are the PASS lines, and `test_ext00_hardening.py` — unmodifiable under this plan — asserts every one of PASS 1..8 appears in a real `run.py` run"
  - "the zero-CCF-import guard is now mutation-proved rather than trusted: it is exercised against copies of the three legs with a CCF import injected and must raise"
  - "`experience.yaml` is `role: register` (what a front door may advertise is a standing statement of what was in force) while `tokens.yaml` is `role: load` (credential material must never content-hash into the audit plane)"
  - "`test_ext00_hardening.py` had to change after all — two private loader helpers follow `experience.yaml` onto the DeclaredArtifact envelope. No assertion in that module changed"
  - "run.py's raw line count rose 766 -> 781 while its mechanical figure fell 36 -> 0; reported separately per D-12 and never summed"
metrics:
  duration: ~2h
  completed: 2026-08-05
---

# Phase 15 Plan 20: External-Consumer Example Rewrite Summary

The last rewrite target is over the streamlined surface, the external-consumption
claim is provably untouched — and the assertion that protects it is now known to
refuse rather than merely known to pass.

---

## The tree that had to be protected

This is the suite's only example whose *consumers* must keep zero CCF imports.
`client_bare.py`, `client_anthropic.py` and `client_adk.py` are EXAM-04's core
claim; only the fabric side was a target.

| Protected file | `git diff` |
| --- | --- |
| `client_bare.py` | empty |
| `client_anthropic.py` | empty |
| `client_adk.py` | empty |
| `replay_server.py` | empty |
| `fixtures/` | empty |

Empty diffs are necessary and not sufficient. Carried context asked
specifically that the zero-CCF-import assertion be verified to **fail when
violated** rather than trusted, and that turned out to be the right instinct to
act on: a static grep that matched nothing would be green forever, and nothing
in the tree had ever exercised the refusal path.

`test_the_zero_import_assertion_fails_when_a_leg_imports_ccf` now copies the
three legs to a temp directory, injects a CCF import into one, repoints
`_EXAMPLE_ROOT` at the copies, and requires the real function to raise. Both
import forms are parametrized, because the regex has to catch
`from ccf.boot import boot` and `import ccf_runtime` alike. Verified live
before the test was written: baseline passes, both injections are detected by
filename, the restored copies pass again.

The assertion in `run.py` is byte-unchanged.

---

## Two Gate 2 tautologies, not one

`serve.py` built its projection plan with `required=operators.keys()` — the
operator registry's own keys on both sides of lineage strict equality
(INV-CH7-47). That is the tautology 15-13's R6 tells every rewrite to fix, and
`product-class.yaml`'s `required_operator_keys` is now the authored declared
side.

**The same tautology existed a second time**, in `run.py`'s
`HelloReplayEnvironment.resolve_plan`:

```python
return fabric.CreditContextPlan(
    plan_id=declared["plan_id"], required=self._operators().keys()
)
```

Fixing only `serve.py` would have left the replica reproducing the original
decision's tautology *inside the replay that exists to prove that decision* —
structurally the same defect 15-17 found in the replay example, in a different
file. Both now read `required_operator_keys` off the artifact.

This is worth stating for 15-21's audit: the phase's running finding did not
gain a ninth instance here, but the sequencing that would have produced one is
visible. A rewrite plan that fixes the tautology only where the plan text names
it leaves the replay path carrying it.

---

## The relocatable figure did not move, and it could not

`run.py` carries 22 relocatable lines before and after. That is not an omission
and it is not a judgement call:

`tests/examples/test_ext00_hardening.py::test_the_d15_fallback_works_with_every_client_leg_deselected`
runs `run.py --legs ""` as a subprocess and asserts, in a loop, that each of
`PASS 1:` through `PASS 8:` appears in the output. That module is out of scope
for this plan and its acceptance criteria require it unmodified. Eight of
`run.py`'s ten `print` calls are therefore pinned by a test this plan may not
touch.

So the narration stays, and the *claims* behind it are asserted in
`tests/examples/test_ext00_serve_output.py` instead — which is what makes
`tests/` own the correctness even though the console output did not move.

`serve.py`'s single relocatable line is the `READY <port>` print. That is
process protocol between parent and child (the parent's blocking `readline()`
is the readiness gate), not narration, and it cannot move either.

What **did** relocate is `serve.py`'s 25-line fabric-side domain self-check,
which the AST measure never counted because it raised rather than asserted. It
is now three independent expectations in `tests/`, reading the new
`expected.yaml` — a document nothing in the serving path reads.

---

## The assertion this family should have had

The plan asked for one new assertion: that the served product's lineage and
replay record reach the client leg unchanged. Three tests carry it, and the
module states which of them is a genuinely independent statement rather than
implying independence it does not have.

| Test | Category | What would have to break |
| --- | --- | --- |
| `test_the_client_leg_read_the_product_the_deployment_declared` | **independent expectation** | any stage of `expected.yaml` -> L1–L6 -> MCP -> external agent stops producing what the deployment declared |
| `test_the_served_lineage_reaches_the_client_leg_unchanged` | wire fidelity | the surface re-serializes, reorders, truncates, or serves a lineage block from a different product than the one it assembled |
| `test_the_served_replay_record_reaches_the_client_leg_unchanged` | wire fidelity | the surface serves a stale or foreign record, or the record is not the one the delivery landed under |
| `test_the_client_leg_received_all_five_replay_dimensions` | SDK mechanism | the record loses a dimension — which `run.py` PASS 5's substring grep would not notice |

The two wire-fidelity tests compare byte-for-byte against a value **this test
process assembled for itself**, not against a value the server handed it. The
right-hand side is a second, independent execution of the same deterministic
slice; the left-hand side crossed a socket. Both ends still resolve from the
same artifacts, so an artifact edit moves both — the module says so plainly
instead of claiming a property it lacks.

All three were mutation-probed:

- pointing `lineage_provider` at a different object → the lineage test fails,
  and only it;
- editing `expected.yaml`'s `entity_count` → the fabric-side and the
  client-side independent expectations both fail, and only they.

---

## Measurement

| File | Figure | Before | After |
| --- | --- | ---: | ---: |
| `serve.py` | raw lines | 773 | 699 |
| | mechanical (`removable`) | 132 | 13 |
| | relocatable (asserts + prints) | 1 | 1 |
| | helpers | 41 | 0 |
| | inline operator block | 61 | 0 |
| | registration prologue | 22 | 13 |
| | boot | 8 | 0 |
| `run.py` | raw lines | 766 | 781 |
| | mechanical (`removable`) | 36 | 0 |
| | relocatable | 22 | 22 |
| | inline operator block | 22 | 0 |
| | registration prologue | 6 | 0 |
| | boot | 8 | 0 |

Removal and relocation are reported separately and never summed (D-12).

`run.py`'s +15 raw lines: the process-lifecycle block gained a nesting level so
the booted replica's handle closes in an outer `finally`, and four one-line
`fabric._load(...)` calls became typed reads off `booted.artifacts` with their
casts. What disappeared is the work — a hand-built operator registry and a
registration-prologue-plus-`boot` — not the lines.

Artifact documents went from 6 (four of them multi-class bundles) to 16 typed
documents (15 + manifest).

---

## Tasks completed

| Task | Commit | What |
| --- | --- | --- |
| 1 | `f2e77c5` | Reshape artifacts to 16 typed documents with a manifest; rewrite `serve.py` and `run.py`'s fabric wiring to `load_and_boot` + `build_operator_registry`; fix both Gate 2 tautologies; `after/` fragments |
| 2 | `73af8f2` | Relocate the fabric-side self-check and add the wire-fidelity and mutation-proof tests; README; surface-change fragment |

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `test_ext00_hardening.py` could not stay unmodified**

- **Found during:** Task 1
- **Issue:** Four tests in that module failed with `KeyError: 'tool_allowlist'`.
  Two private loader helpers read `tools` and `tool_allowlist` from the root of
  `experience.yaml`; the reshape this plan mandates moves them under
  `declaration:`, because the `DeclaredArtifact` envelope is the only honest
  `$schema` header available to a class the SDK does not own (15-13, R2). The
  plan's acceptance criterion "the existing `test_ext00_hardening.py` … is
  unmodified" and its own instruction to reshape the artifacts are not jointly
  satisfiable.
- **Fix:** Two loader helpers now index `doc["declaration"]`, each with a
  one-line comment naming the plan and the reason. **No assertion in that
  module changed**, and its `test_the_d15_fallback_works_with_every_client_leg_deselected`
  — the test that pins `run.py`'s PASS lines — is untouched.
- **Why not the alternative:** leaving `experience.yaml` root-shaped would have
  left it with no header the tree-wide 15-21 gate accepts, which is the
  anti-pattern this phase has refused seven times.
- **Files modified:** `tests/examples/test_ext00_hardening.py`
- **Commit:** `f2e77c5`

**2. [Rule 1 - Bug] `run.py`'s replay environment carried the Gate 2 tautology**

- **Found during:** Task 1
- **Issue:** `HelloReplayEnvironment.resolve_plan` built the replay-time plan
  with `required=self._operators().keys()`. The plan text names only `serve.py`
  as the tautology's site.
- **Fix:** reads `required_operator_keys` off the product-class artifact, with
  the reason in a comment.
- **Files modified:** `examples/external/00-hello-context/run.py`
- **Commit:** `f2e77c5`

**3. [Rule 1 - Bug] Stale counts in the README**

- **Found during:** Task 2
- **Issue:** The README twice said "six assertions" / "six PASS lines" for a
  harness that has produced eight since plan 13.1.
- **Fix:** corrected to eight while the surrounding sections were being
  rewritten.
- **Files modified:** `examples/external/00-hello-context/README.md`
- **Commit:** `73af8f2`

### Deliberate departures from the plan text

**The plan's acceptance criterion for `run.py`'s diff is stale.** It requires
the diff to "touch only the `_operators` method and the boot call". The same
plan mandates reshaping the artifact set, and `run.py` read four of those
documents through `serve.py`'s private `_load`/`_instant`/`_resolution_spec`/
`_envelopes` helpers — every one of which the reshape deletes. Those reads
necessarily changed. What the criterion was protecting did hold and was
verified: the zero-CCF-import assertion block is byte-identical, and so are
`_assert_bad_token_refused`, `_assert_seven_heading_readme`, `README_HEADINGS`,
`_spawn`, `_terminate`, `_run_leg`, `_mcp_call_text`, `_mcp_probe` and
`_leg_environments`.

**`public/tutorial/adopters-guide.md` is unchanged.** The plan lists it in
`files_modified`. Its only includes from this tree name `client_bare.py`
snippet markers (`mcp-connect`, `mcp-discover`, `mcp-resource`), and this plan
may not touch that file. There are no snippet markers in `serve.py` or `run.py`
at all. `make docs-strict` is green.

**No `# no-schema: DeclaredArtifact` escape hatch and no deferral marker.**
All sixteen documents name a committed schema under `docs/schemas/` — thirteen
via the envelope, three via their SDK class. The marker the plan offers does not
exist in the tooling anyway (15-17 recorded the same).

**No plan-scoped `--report` subset test**, per the phase-wide ruling.
`tools/dump_surface.py --report` reports the accumulated set since 15-01; this
plan adds no public Python surface, so every fragment entry is
`Public surface: false`.

---

## Threat Flags

None. No new network endpoint, auth path, file-access pattern, or schema change
at a trust boundary. The register's five mitigations all hold:

| Threat ID | Disposition | Where it landed |
| --- | --- | --- |
| T-15-20-01 (a CCF import leaking into a client leg) | mitigated | `git diff` empty on all three legs; the grep assertion unmodified AND mutation-proved to refuse |
| T-15-20-02 (the server-side tool allowlist weakened) | mitigated | `build_experience_server`'s call site, the allowlist, `validate_tool_names` and `validate_agent_exposure` are unchanged in behaviour; `run.py` PASS 7 and the four hardening tests still pass |
| T-15-20-03 (lineage or replay content changing on the wire) | mitigated | Two new tests assert byte equality against an independently recomputed fabric-side value; mutation-probed |
| T-15-20-04 (fixture machinery altered so a replay comparison passes) | mitigated | `replay_server.py` and `fixtures/` asserted byte-unchanged by empty `git diff` |
| T-15-20-SC (package installs) | mitigated | No package installs in this plan |

One posture note rather than a flag: `tokens.yaml` stays `role: load`
deliberately, so no synthetic credential material is content-hashed into
Control Plane state or into Decision Replay dimension 2.

---

## Verification

| Gate | Result |
| --- | --- |
| `make lint` | exit 0 |
| `make typecheck` | exit 0 — 169 files |
| `pytest tests` | 1960 passed, 2 skipped |
| `make examples` | exit 0 — all ten |
| `make example-ext-00` | exit 0 — PASS 1 through PASS 8 |
| `make docs-strict` | exit 0 |
| `make schema-headers` (tree-wide) | exit 0 — 10 directories |
| `pytest tests/examples/test_ext00_serve_output.py` | 15 passed |
| surface manifest + frozen baseline | untouched (0 files) |

Test count moved 1945 → 1960 (+15).

Mutation probes (throwaway, not committed):

- `lineage_provider` repointed at the replay record: fails
  `test_the_served_lineage_reaches_the_client_leg_unchanged` and only it.
- `expected.yaml` `entity_count: 4 -> 5`: fails both the fabric-side and the
  client-side independent expectations, and only those two.
- A CCF import injected into a copied client leg: `_assert_zero_ccf_imports`
  raises, naming the file, for both `from ccf …` and `import ccf_runtime`.

## Self-Check: PASSED

All files claimed above exist on disk; both commit hashes resolve in `git log`.
