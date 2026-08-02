---
phase: 13-examples-suite-upgrade
reviewed: 2026-08-02T00:00:00Z
depth: standard
files_reviewed: 23
files_reviewed_list:
  - examples/00-quickstart/README.md
  - examples/01-agent-basics/artifacts/halflife.yaml
  - examples/01-agent-basics/README.md
  - examples/01-agent-basics/run.py
  - examples/02-skilling/README.md
  - examples/03-harness-portability/README.md
  - examples/04-cross-process/README.md
  - examples/05-workflow-hitl/artifacts/hitl.yaml
  - examples/05-workflow-hitl/artifacts/tokens.yaml
  - examples/05-workflow-hitl/README.md
  - examples/05-workflow-hitl/run.py
  - examples/06-decision-replay/artifacts/hitl.yaml
  - examples/06-decision-replay/README.md
  - examples/06-decision-replay/run.py
  - examples/07-artifact-store-mcp/artifacts/controlplane.yaml
  - examples/07-artifact-store-mcp/artifacts/events.yaml
  - examples/07-artifact-store-mcp/artifacts/ontology.yaml
  - examples/07-artifact-store-mcp/artifacts/store_file.yaml
  - examples/07-artifact-store-mcp/artifacts/store_mcp.yaml
  - examples/07-artifact-store-mcp/README.md
  - examples/07-artifact-store-mcp/run.py
  - examples/08-e2e-demo/README.md
findings:
  critical: 0
  warning: 2
  info: 5
  total: 7
  fixed: 2
status: issues_found
fixed: [WR-01, WR-02]
---

# Phase 13: Code Review Report

**Reviewed:** 2026-08-02
**Depth:** standard
**Files Reviewed:** 23
**Status:** issues_found (no blockers — warnings and info only)

## Summary

Reviewed the Phase 13 examples-suite upgrade: seven README rewrites to the
seven-heading template, definition-artifact enrichments (halflife, hitl,
tokens, store configs), and driver changes in examples 01, 05, 06, and 07.

Verification performed beyond reading:

- **Runnability confirmed.** All four changed drivers were executed against
  the project venv and exit 0: `examples/01-agent-basics/run.py` (printed
  D_c `0.3555…`, signal `forced_llm`), `examples/05-workflow-hitl/run.py`,
  `examples/06-decision-replay/run.py`, `examples/07-artifact-store-mcp/run.py`
  (including the real MCP subprocess leg).
- **README claims cross-checked against artifacts and code.** Example 01's
  "≈0.356" D_c claim matches the actual computed value; the
  `forced_llm_threshold: "0.30"` / `risk_sensitivity: "1.2"` values the
  README cites exist in `agent.yaml`; the `role`/`excluded_entity_classes`
  expected keys exist in `controlplane.yaml`; example 06's `metering`-scope
  narrative matches `tokens.yaml`/`scope_mapping.yaml`.
- **Cross-references resolve.** All `make example-NN` targets (00–08) exist
  in the Makefile; `docs/demo-walkthrough.md` and
  `examples/07-artifact-store-mcp/mcp_store_child.py` exist; example 03's
  "all three D-IMPL-24 reference adapters" claim matches the RESOLVED
  D-IMPL-24 entry in `docs/DECISIONS.md` (it is not drift against
  CLAUDE.md's "open" listing — the decision log supersedes it).
- **No-Hardcoding spot check.** No prompt strings, thresholds, scopes,
  routing values, or domain vocabulary found in the changed `run.py` files;
  the `ScriptedAnalyst`/`NodeBindings`/`DeclaredDebt` stubs pull all content
  from artifacts. `_health_check`'s exception handling in example 07 is
  sound: `SyncMcpBridge`/MCP client wraps transport failures into
  `McpServerUnreachable` (verified in `src/ccf/mcp/client.py`).
- **Quick-scan patterns.** No `console.log`/`debugger`/`FIXME`/`XXX`/`HACK`
  in the reviewed files; no empty catch/except blocks; the one
  secret-pattern hit is IN-05 below (reviewed, accepted).

No BLOCKER-class defects found. Two warnings and five info items follow.

## Narrative Findings (AI reviewer)

### Warnings

#### WR-01: Variable shadowing — `boundary` rebound from `datetime` to `OverrideBoundary`

**File:** `examples/06-decision-replay/run.py:945` (original binding at line 573)
**Issue:** In `record()`, `boundary` is first the decision's temporal
boundary (`datetime`, line 573) and is used to build the operator chain,
the candidate product, and its lineage. At line 945 the same name is
rebound to the `OverrideBoundary[ShedDetermination]` instance. Any future
enrichment appended after line 945 that reaches for `boundary` as the
temporal instant (the natural name every sibling example uses for it) will
silently get an object of a completely different type — and given this
suite's stated workflow of incremental artifact/driver enrichment, code
being appended to this exact function is the expected change pattern.
**Fix:**
```python
override_boundary: OverrideBoundary[ShedDetermination] = OverrideBoundary(
    transport=transport, ...
)
proposed = override_boundary.propose(...)
resolution = override_boundary.resolve(...)
```
**resolution:** Fixed 2026-08-02 (commit 80bdf5f) — the `OverrideBoundary`
instance and its `propose`/`resolve` uses renamed to `override_boundary`;
the line-573 `datetime` binding untouched. `make example-06` and
`make lint` green.

#### WR-02: Magic index `mcp_refs[1]` couples the wire-fetch assertion to tuple position

**File:** `examples/07-artifact-store-mcp/run.py:532-534` (producer at lines 442-446)
**Issue:** `workload()` returns `(served.replay_ref, product_ref, bundle_ref)`
and `main()` fetches the product back over the wire via
`mcp_refs[1]`. Nothing ties index 1 to "the product" except the return
tuple's ordering three hundred lines away. If a fourth artifact class is
added to the workload (the README explicitly frames adding artifact
classes as the enrichment path), or the ordering changes, the assertion
would validate the wrong artifact — and because
`ContextProductContract.model_validate_json` would then fail with an
opaque validation error (or worse, a replay record that happens to parse),
the failure mode is confusing rather than self-diagnosing.
**Fix:** Return a named structure and index by name:
```python
return canonical_bytes(gated.product), {
    "replay_record": served.replay_ref,
    "product": product_ref,
    "policy_bundle": bundle_ref,
}
...
fresh.get(content_address=mcp_refs["product"].content_address)
```
**resolution:** Fixed 2026-08-02 (commit 4ef3148) — `workload()` now
returns `dict[str, ArtifactRef]` keyed by artifact role
(`replay_record`/`product`/`policy_bundle`); all assertion, retrieval,
and print sites in `main()` index by name. `make example-07` and
`make lint` green.

### Info

#### IN-01: Environment variables mutated and never restored

**File:** `examples/07-artifact-store-mcp/run.py:488, 505`
**Issue:** `os.environ[store_file["root_env"]]` and
`os.environ[store_mcp["endpoint_env"]]` are set and never deleted. After
`main()` returns, `CCF_EXAMPLE07_FILE_ROOT` points at a deleted temp
directory and the endpoint var at a dead port. Harmless as a standalone
script, but if the example is ever imported and driven by a test runner in
the same process (the CI suite runs all examples), stale env state leaks
across runs.
**Fix:** Wrap in `try/finally` with `os.environ.pop(...)`, or use a small
`contextlib` helper.

#### IN-02: Example 06 asserts only `entity_count` from the `expected:` block

**File:** `examples/06-decision-replay/run.py:717-718`
**Issue:** Siblings (00, 01, 07) assert `entity_classes` and
`relationship_types` from `expected:` in addition to `entity_count`;
example 06's record phase asserts only the count. The README's
"reviewed-regeneration" workflow tells users to update "entity classes,
relationship types, `entity_count`" — two of which the driver never
checks, so a user's stale `expected:` values there would pass silently.
**Fix:** Mirror the example-07 assertions on `entity_classes` and
`relationship_types`.

#### IN-03: Helper duplication across drivers with silent divergence

**Files:** `examples/01-agent-basics/run.py`, `examples/05-workflow-hitl/run.py`, `examples/06-decision-replay/run.py`, `examples/07-artifact-store-mcp/run.py`
**Issue:** `_load`, `_instant`, `_resolution_spec`, `_envelopes`,
`ArtifactTokenSource`, `DeclaredDebt`, `UnconsultedSink`, `_call`, and
`_ticking_clock` are copy-pasted across the four drivers. This is
consistent with the self-contained-example discipline, but the copies have
already begun to drift: `NodeBindings` in 05 carries `failing`/`ran`
support that 06's copy lacks, and 07's `_instant` dropped the explanatory
comment. Drift here is a maintenance hazard, not a defect — flagging so a
deliberate decision (shared `examples/_common` vs. accepted duplication)
is on record.
**Fix:** Record the decision; if duplication is the ruling, a one-line
"deliberately duplicated per example self-containment" comment atop each
helper block stops future reviewers from re-flagging it.

#### IN-04: Function-level `import hmac`

**File:** `examples/05-workflow-hitl/run.py:174`, `examples/06-decision-replay/run.py:380`
**Issue:** `import hmac` inside `grant_for()` runs on every request. Cheap
(module cache) but inconsistent with the module-level import style of
everything else in these files.
**Fix:** Move to the module import block.

#### IN-05: Secret-pattern hit in `store_mcp.yaml` — reviewed and accepted

**File:** `examples/07-artifact-store-mcp/artifacts/store_mcp.yaml:27`
**Issue:** `token: nordhaven-example07-dev-token` matches hardcoded-
credential scan patterns. Reviewed: it is a per-run synthetic credential
that authorizes only a temp directory, both sides read the same block by
design, the `.invalid` TLD guards the issuer/resource URLs, and the file's
header documents all of this. Recorded here so future quick-depth scans
have a disposition to cite rather than re-raising it.
**Fix:** None required. Optionally rename to something scanner-friendly
like `example_token` if CI secret scanning is added later.

---

_Reviewed: 2026-08-02_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
