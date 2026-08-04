---
phase: 15-sdk-ergonomics-the-integration-surface
plan: 04
subsystem: repo-tooling
tags: [ergo-16, cinv-01, d-impl-78, lint-scope]
status: complete
requires:
  - "15-02 (the lint machinery: tools/lints/__main__.py, harness_imports.py)"
  - "15-03 (the A6 falsification and Dave's rule-refinement ruling)"
provides:
  - "CINV-01 (No-Hardcoding) runs over the tests/ tree"
  - "cinv01a-prompt-shape separates prompts from developer-facing diagnostics"
  - "ccf.agents.agent._validate_coherence — the constructor guard, extracted"
  - "tests/lints/test_tests_tree_scope.py — the scope pinned in both directions"
affects:
  - "D-09 (example CI assertions may now relocate into tests/ without escaping CINV-01)"
  - "every future plan adding a test module — inline domain literals under tests/ now fail CI"
tech-stack:
  added: []
  patterns:
    - "per-rule tree scoping stays the exemption surface — config, never an allowlist entry"
    - "a guard extracted from a constructor so tests can exercise it without bypassing the factory"
key-files:
  created:
    - tests/lints/test_tests_tree_scope.py
    - docs/surface-changes/15-04-lint-scope.md
  modified:
    - tools/lints/__main__.py
    - tools/lints/no_hardcoding.py
    - tools/lints/tests/test_no_hardcoding.py
    - src/ccf/agents/agent.py
    - tests/agents/test_agent.py
decisions:
  - "The two prose-diagnostic false positives are resolved by refining cinv01a-prompt-shape; zero allowlist entries were added (Dave, 2026-08-04 — binding)"
  - "The discriminator is two-sided: a toolchain marker classifies a literal as a diagnostic only if it does not also address a reader, so a prompt cannot escape by mentioning a filename"
  - "The genuine factory-bypass is fixed by extracting Agent.__init__'s coherence guard, not by allowlisting or by weakening cinv01c"
metrics:
  tasks_completed: 4
  tasks_total: 4
  completed: 2026-08-04
---

# Phase 15 Plan 04: CINV-01 Reaches the tests/ Tree Summary

The No-Hardcoding Rule now lints `tests/`, so D-09's relocated example assertions cannot
carry domain expectations out of a structural invariant's reach — and the prose-diagnostic
false positives that widening surfaced are gone by rule refinement, with zero allowlist
entries added.

**Status: complete.** All four tasks done, `make ci-core` green (1594 passed, 2 skipped).

## What was built

### The rule refinement (Dave's binding ruling)

`cinv01a-prompt-shape` scored "long English string literal", which cannot tell a system
instruction from a multi-sentence CI failure message. Two functions now separate the
categories on the distinction itself — *a prompt is a string sent to a model; a diagnostic
is a string shown to a developer*:

- **`is_developer_diagnostic(text)`** — true when the literal carries at least one
  `DIAGNOSTIC_MARKERS` signal **and** does not address a reader. Markers: a backticked span
  (`` `make openapi` ``), a repo-relative filename (`docs/surface/v0.2-surface.json`), a
  zero-argument callable reference (`create_app()`).
- **`addresses_a_reader(text)`** — a role-preamble opener, a second-person pronoun anywhere
  in the body, or template-brace density at `MIN_BRACES`.

Both halves are load-bearing, and the asymmetry is deliberate: without the markers any
impersonal prose would escape; without the reader test a prompt would escape by mentioning a
filename. A message that both names a `make` target *and* says "you" is still scored — a
false positive is rewordable, a false negative is a prompt in code.

The check runs before scoring, so the change is a strict narrowing over one category. It is
in the rule, so every future diagnostic message inherits it — which was the whole point of
Dave's ruling against two allowlist entries.

### The genuine finding

`tests/agents/test_agent.py` had a helper calling `Agent(**values)` directly. Its
justification was real (it unit-tests the constructor's own validation) but the fix is
structural, not an exemption: `Agent.__init__`'s coherence check is extracted as
`ccf.agents.agent._validate_coherence(definition, identity, components)`. The corruption
tests now drive that guard — plus `_validated_bound_skills` for the WR-03 seam — while the
positive-path helper builds through `AgentFactory` from the banking fixture, registering the
referenced artifacts in a `ControlPlaneRegistry`. A vacuity test asserts the coherent inputs
pass, so the six corruption tests fail for their stated reason. Module-private, so no
manifest entry: `__all__` is unchanged.

### The widening — two edits, not one

`run()` iterates `LINTED_TREES` and *then* filters by `RULE_TREE_SCOPE`, so the scope entry
alone is a no-op. Both gained `"tests"`. `harness-imports`, `algorithmic`, and
`orchestration-imports` were confirmed still `("src", "runtime")` — test modules exercising
the harness adapters import harness SDKs, and CLAUDE.md §7.3 words CINV-02 over core. The
`RULE_TREE_SCOPE` comment block names D-IMPL-78 and states the D-09 reason in the same voice
as the existing `/examples` rationale.

## The rule refinement, proven in both directions

Dave required empirical proof in both directions, not just on the strings the refinement was
asked to clear.

**Negative direction — the two named sites are clean:**

| Site | Before | After |
|---|---|---|
| `tests/http_api/test_openapi.py:38` (`make openapi` drift message) | `cinv01a-prompt-shape` | CLEAN |
| `tests/test_surface_drift.py:78` (`make surface` drift message) | `cinv01a-prompt-shape` | CLEAN |

**Positive direction — a would-be prompt still fires**, including one wearing every
diagnostic marker at once:

| Literal | Verdict |
|---|---|
| `"You are a diligent credit analyst. Always ground every claim… Never speculate…"` | **FIRES** |
| `"You are a covenant analyst. Read the `make report` output from docs/policy.yaml and call render()… Never speculate beyond the evidence you are given…"` | **FIRES** |
| The `openapi.json` / `create_app()` / `make openapi` drift message | clean |

The second row is the one that matters: backtick command, repo path, and `callable()` all
present, and the rule still refuses it because it addresses a reader. Pinned as
`test_a_prompt_wearing_diagnostic_markers_is_still_flagged`.

**The genuine finding still fires:** `tests/agents/test_agent.py:93 cinv01c-factory-bypass`
was confirmed still reported after the refinement, before being fixed properly in Task 2.

**One non-regression checked and cleared.** A brace-template prompt with no second-person
address (`"Summarize covenant headroom for {entity} as of {as_of} under {policy_bundle}…"`)
reads clean — but `is_developer_diagnostic` returns `False` for it (braces make it address a
reader), so the refinement is not the cause: it scores 1 under the pre-existing four-signal
scoring, exactly as it did before this plan. That is a property of the scoring thresholds,
untouched here, and noted rather than silently absorbed.

## Allowlist entries added

**None.** `tools/lints/allowlist.yaml` is byte-identical to its pre-plan state — the file
does not appear in any of this plan's four commits. This is the ruling's central
requirement and is stated here as the auditable claim it is.

## Deviations from Plan

### 1. [Ruling supersedes plan text] Allowlist path not taken

The PLAN.md Task 1 action text said to "use `tools/lints/allowlist.yaml` only where a finding
is genuinely a false positive, and record each allowlist entry in the plan summary." Dave's
2026-08-04 checkpoint ruling, recorded in `15-03-SUMMARY.md` and re-stated in this executor's
binding brief, overrides that for the two `cinv01a` false positives specifically: rule
refinement, no allowlist entries. The ruling is later than the plan and explicitly binding.
Zero entries added.

### 2. [Rule 3 - Blocking] Task ordering inverted

The plan ordered the widening first (Task 1) and the tests second. Executed in the order
refinement → genuine-finding fix → widening → directional tests, so that the widening commit
lands green rather than landing three findings and removing them afterwards. Every commit in
this plan passes `python -m tools.lints --all` at that commit.

### 3. [Rule 2 - Missing critical functionality] Two files added to `files_modified`

The plan's `files_modified` listed only `tools/lints/__main__.py`, the new test module, and
the doc fragment. Fixing the two findings as ruled necessarily reaches further:

- `tools/lints/no_hardcoding.py` + `tools/lints/tests/test_no_hardcoding.py` — the rule
  refinement itself and its unit tests. Unavoidable: the ruling *is* a change to this rule.
- `src/ccf/agents/agent.py` + `tests/agents/test_agent.py` — the factory-bypass fix. The
  guard extraction is the only way to keep the constructor's validation covered without a
  bypass the widened lint now catches.

None of these are files owned by the parallel plans 15-05 (`src/ccf/controlplane/artifacts.py`)
or 15-06 (`src/ccf/deployment/`).

## Surface impact

`tools/dump_surface.py --report` reports `added (0)`, `removed (0)`, `reshaped (0)`. The live
manifest `docs/surface/v0.2-surface.json` and the frozen baseline
`docs/surface/v0.2-surface-baseline.json` were **not touched**, and `make surface` was not
run. `_validate_coherence` is module-private, so `ccf.agents.agent.__all__` is unchanged.

`docs/surface-changes/15-04-lint-scope.md` carries two entries, both
`Public surface: false`, both `Change type: reshaped`, with fully-qualified `Surface` values
`tools/lints/__main__.py` and `tools/lints/no_hardcoding.py` — neither can appear in a
manifest diff, since `dump_surface.py` walks only `/src` and `/runtime` modules defining
`__all__`.

## Verification

- `.venv/bin/python -m tools.lints --all` — exit 0, with `tests/` in scope
- `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/lints/ -q` — 49 passed
- `PYTHONPATH=src:runtime .venv/bin/python -m pytest tools/lints/tests -q` — 24 passed
- `tools/dump_surface.py --report` — 0/0/0; `tests/test_surface_drift.py` passes
- `make ci-core` — **1594 passed, 2 skipped**; mypy `Success: no issues found in 162 source files`

## Known Stubs

None.

## Threat Flags

None. No new network, auth, file-access, or schema surface — the plan changes a CI lint's
scope and one rule's discriminator, and extracts an existing in-process guard.

## Commits

| Task | Commit | Subject |
|---|---|---|
| 1 | `dcbe751` | fix(15-04): separate prompts from developer diagnostics in CINV-01a |
| 2 | `ab3ef42` | fix(15-04): construct agents through the factory in test_agent.py |
| 3 | `add80fa` | feat(15-04): widen CINV-01 over the tests/ tree (D-IMPL-78, ERGO-16) |
| 4 | `061d496` | test(15-04): pin the tests/ lint scope in both directions |
