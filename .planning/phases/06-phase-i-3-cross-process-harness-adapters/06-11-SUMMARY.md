---
phase: 06-phase-i-3-cross-process-harness-adapters
plan: 11
subsystem: harness-seam
tags: [harness, protocol, replay, prompts, security, ssti]
requires:
  - "ccf.agents.agent.Agent (I.2) — the adapter's only fabric-side input"
  - "ccf.replay.record (I.1) — the five-dimension baseline being extended"
  - "ccf.agents.prompts (I.2) — the parse-only validators the render reuses"
  - "D-IMPL-53 / 06-01 — the CINV-02 carve-out that lets adapters exist at all"
provides:
  - "ccf.harness.protocol.HarnessAdapterProtocol — the contract 06-12/06-13/06-14 implement"
  - "ccf.harness.protocol.HarnessCapabilities — required effects declaration (D-10)"
  - "ccf.harness.protocol.EffectRefusal — typed refusal at the effect-capture seam"
  - "ccf.replay.record.HarnessTrace + NO_HARNESS/NO_HARNESS_TRACE — the dimension-3 slot"
  - "ccf.agents.prompts.render_instruction — the SDK's only render entry point"
  - "ccf.agents.errors.PromptRenderRefused"
affects:
  - "06-12 (Claude Agent SDK adapter), 06-13 (LangGraph), 06-14 (Google ADK) — all implement the Protocol"
  - "06-15 — the D-18 harness-neutrality proof compares governed fields and excludes harness_trace"
tech-stack:
  added: []
  patterns:
    - "Protocol in /src, implementations in /runtime (D-04)"
    - "positive sentinels over None/absence (MODE_1_MODEL_VERSION voice)"
    - "refusals as returned typed values, exceptions for misuse"
    - "jinja2 SandboxedEnvironment as the module's single environment idiom"
key-files:
  created:
    - src/ccf/harness/__init__.py
    - src/ccf/harness/protocol.py
    - tests/harness/__init__.py
    - tests/harness/test_protocol.py
    - tests/replay/test_harness_trace.py
    - tests/agents/test_prompt_render.py
  modified:
    - src/ccf/replay/record.py
    - src/ccf/replay/__init__.py
    - src/ccf/agents/prompts.py
    - src/ccf/agents/errors.py
    - docs/DECISIONS.md
decisions:
  - "D-IMPL-55 — harness-attributable replay fields extend dimension 3 as HarnessTrace; dimension 5 and a sixth block both rejected"
  - "Seams shaped as translations producing harness-native carriers, not callback registrations, so LangGraph's topology ownership fits"
  - "The parse-only validators moved onto the sandboxed environment too, leaving zero plain jinja2.Environment idioms in the module"
metrics:
  duration: ~50 min
  tasks: 3
  tests_added: 33
  completed: 2026-07-26
---

# Phase 06 Plan 11: Harness Seam Declaration Summary

The fabric side of the harness seam now exists and is harness-free: a four-seam
`HarnessAdapterProtocol` taking only `Agent`, a required `effects` capability
declaration, a `harness_trace` slot under replay dimension 3 that leaves the
five-dimension record intact and is logged as D-IMPL-55, and the SDK's first
`render(...)` — sandboxed, with a context that cannot admit a remote-influenced
value.

## The Protocol surface waves 3–5 implement against

This is the contract 06-12 (Claude Agent SDK), 06-13 (LangGraph), and 06-14
(Google ADK) must satisfy. `@runtime_checkable`, every method keyword-only after
`self`, every body `...`:

```python
@runtime_checkable
class HarnessAdapterProtocol(Protocol):
    def capabilities(self) -> HarnessCapabilities: ...

    def inject_context(
        self, *,
        agent: Agent,
        products: tuple[ContextProductContract, ...],
        instructions: tuple[str, ...],
    ) -> object: ...

    def expose_skills(self, *, agent: Agent) -> tuple[str, ...]: ...

    def capture_effect(
        self, *, agent: Agent, output: Mapping[str, Any]
    ) -> EmittedEffect | EffectRefusal: ...

    def replay_trace(self, *, execution: object) -> HarnessTrace: ...
```

Supporting contracts, both `CCFContract` (frozen, `extra=forbid`):

```python
EffectCapability = Literal["governed", "unsupported"]
EFFECT_CAPABILITIES: frozenset[str] = frozenset({"governed", "unsupported"})

class HarnessCapabilities(CCFContract):
    harness_id: str
    effects: EffectCapability      # required — no default (D-10)

class EffectRefusal(CCFContract):
    harness_id: str
    agent_definition_hash: str
    reason: str
```

Four notes adapter authors need before writing code:

1. **`Agent` is the only fabric-side input.** No fabric boot handle, Control
   Plane registry, or graph read/write handle appears on the surface — or
   anywhere in the module, which `tests/harness/test_protocol.py` pins by source
   scan against a six-name forbidden list (T-06-61).
2. **Three seams return `object` deliberately.** The harness-native carrier is
   harness-shaped by definition; a precise annotation here would make the fabric
   harness-shaped. The adapter narrows the type for itself under
   `ccf_runtime/adapters/<harness>/`.
3. **Seams are translations, not callback registrations.** Claude and ADK expose
   callbacks into a loop they own; LangGraph has no loop to hook — the adapter
   builds the graph. A callback-shaped Protocol would have fit two of three and
   forced the LangGraph adapter to fake a loop. This was the single highest-risk
   shaping decision in the plan and it was made against the research
   Four-Seam Binding Matrix cell by cell.
4. **`expose_skills` returns names, not tool objects.** That is what lets the
   conformance suite compare against `agent.bound_skill_names` structurally
   rather than by reading adapter code (T-02-27).

**Do not** set `__ccf_mode__ = "algorithmic"` on adapter modules. They bind a
harness that reaches a model, which makes them the semantic boundary. The
Protocol module itself does carry the tag, and imports no harness and no LLM
client.

## Replay dimension 3 (D-25 / D-IMPL-55)

`HarnessTrace` hangs off `ModelVersionRecord` with six fields — `harness_id`,
`model_version`, `trace_provider`, `trace_id`, `input_tokens`, `output_tokens` —
each defaulted to a positive sentinel. `NO_HARNESS = "no-harness"` and the
whole-block `NO_HARNESS_TRACE` are in the `MODE_1_MODEL_VERSION` voice, so an
absent trace and a *dropped* trace are not the same artifact (T-06-63).

`build_replay_record` gained `harness_trace: HarnessTrace | None = None`,
threaded exactly as `agent_conditioning` is, and recorded verbatim.
`DecisionReplayRecord` gained no sixth field (INV-CH7-80).

The harness reports its own `model_version` *inside* the block; dimension 3's
own `assembly_mode` and `model_version` stay governed fields the fabric alone
writes, pinned by
`test_a_harness_trace_cannot_overwrite_a_governed_field` (T-06-62).

For 06-15's D-18 comparison: compare `context_fabric_snapshot`,
`policy_bindings`, `perspective_conditioning`, `content_generation_path`, and
`model_version.{assembly_mode,model_version}` for exact equality across the
three adapters; exclude `model_version.harness_trace`.

## The render (T-06-60)

`render_instruction(*, binding, artifact, parameter_values)` is the SDK's only
render entry point. Two controls, both structural:

- **`jinja2.sandbox.SandboxedEnvironment`**, and the parse-only validators were
  moved onto it too, so `grep -c 'jinja2.Environment(' src/ccf/agents/prompts.py`
  is **0** and there is no plain environment left in the module for a later edit
  to reach for.
- **The context is built only from the pinned parameters**, enforced by
  signature shape: keyword-only, no `**kwargs`, no `context` argument, `str`
  values, and keys that must equal `binding.parameters` exactly in both
  directions. Surplus is refused rather than dropped (a silently-ignored key is
  what a widened context looks like from outside); missing is refused rather
  than defaulted (D-IMPL-38).

**Verified by inversion:** replacing `SandboxedEnvironment` with `Environment`
makes 5 tests fail, including all four attribute-traversal escape cases. The
control is real, not decorative. `prompts.py`'s stale "there is no `render` call
in this module or anywhere in `/src`" claim is gone, replaced with the scoped
D-21 statement of what the two controls actually enforce, plus the
do-not-re-resolve-prompt-artifacts paragraph addressed to 06-12..06-14 (T-06-64).

## Deviations from Plan

**1. [Rule 3 — Blocking] Tasks 1 and 2 executed in the order 2 → 1 → 3**
- **Found during:** Task 1 setup
- **Issue:** Task 1's `replay_trace` seam returns `HarnessTrace`, which Task 2
  creates. Task 1 could not be committed green before Task 2 landed.
- **Fix:** Executed Task 2 first. No content changed; the three commits are
  atomic and each is independently green.
- **Commits:** `1367445`, `5ef5c9a`, `467199f`

**2. [Rule 1 — Bug] The plan's `len(DecisionReplayRecord.model_fields) == 5`
acceptance criterion is false against existing code**
- **Found during:** Task 2
- **Issue:** The record carries `tenant_id` and `recorded_at` as record-level
  metadata alongside its five dimensions, so `model_fields` was **7** before this
  plan and would have been 7 after a correct implementation. The criterion (and
  the identical `<verify>` command) would have failed on a correct change and
  passed only on a wrong one — it tested the wrong property.
- **Fix:** `test_the_record_still_has_exactly_five_dimensions` asserts the actual
  INV-CH7-80 claim: the dimension field names equal a named `FIVE_DIMENSIONS` set,
  `harness_trace` is absent from `DecisionReplayRecord` and present on
  `ModelVersionRecord`. The reasoning is recorded in D-IMPL-55 so the next reader
  does not re-derive it.
- **Commit:** `1367445`

**3. [Rule 3 — Blocking] `src/ccf/agents/errors.py` modified, outside
`files_modified`**
- **Found during:** Task 3
- **Issue:** The render needs a typed refusal, and the codebase keeps agent error
  types in `errors.py`. Reusing `PromptValidationError` would have conflated
  "this artifact is inadmissible" (load time) with "this render was refused"
  (a security event at decision time, on remote-influenced input).
- **Fix:** Added `PromptRenderRefused`. Additive only; no existing error changed.
- **Commit:** `467199f`

**4. [Rule 2 — Hardening] The parse-only validators moved onto the sandbox**
- **Found during:** Task 3
- **Issue:** The plan required `grep -c 'jinja2.Environment(' … == 0`, but
  `_template_parameters` legitimately used a plain `Environment` for
  `.parse()`. Leaving it would have failed the criterion and, more importantly,
  left two environment idioms in one module where a later edit could reach for
  the wrong one.
- **Fix:** One `_sandbox()` helper, used by both paths. Parsing under a sandboxed
  environment is equivalent for `parse()`/`find_undeclared_variables()` — all 133
  `tests/agents` tests pass unchanged.
- **Commit:** `467199f`

**5. [Scoping — D-21] The byte-identity claim was narrowed to what it can earn**
- **Found during:** Task 2
- **Issue:** The plan's must-have said passing `harness_trace=None` "reproduces
  the pre-change record byte for byte". That is not literally achievable —
  `canonical_bytes` walks every `model_field`, so a new field with a default
  necessarily adds one key.
- **Fix:** The claim is stated at its real scope and tested at that scope: the
  literal in `PRE_CHANGE_CANONICAL` was captured by **actually executing** the
  pre-change `build_replay_record` (from `git show HEAD:src/ccf/replay/record.py`),
  and the test asserts the post-change bytes minus the one new `harness_trace`
  key equal it exactly. Separately, passing `None` is asserted byte-identical to
  omitting the argument. Recorded in D-IMPL-55.
- **Commit:** `1367445`

## D-22 / consumption-discipline note

**This plan widens no `ALLOWED_CCF_PREFIXES` entry and owes no
transitive-closure argument.** The dependency runs seam → agent: `ccf.harness`
imports `ccf.agents.agent`, and `ccf.agents` imports nothing from `ccf.harness`.
`ccf.harness` therefore never enters the import closure
`tests/agents/test_consumption_discipline.py` scans, so that check is untouched.
Pinned by `test_agents_does_not_import_the_harness_package`. The `Agent`
isolation claim is stated throughout as **direct-import-checked**, never as
"provably no path" or "by construction".

## Verification

| Check | Baseline | Result |
|---|---|---|
| `pytest -q` | 641 passed / 2 skipped | **674 passed / 2 skipped** |
| `mypy` | clean, 70 files | **clean, 72 files** |
| `tools.lints --all` | exit 0 | **exit 0** |
| `grep -rn 'langgraph\|google.adk\|claude_agent_sdk' src/` | — | **no matches** |
| `grep -c SandboxedEnvironment src/ccf/agents/prompts.py` | — | **3** |
| `grep -c 'jinja2.Environment(' src/ccf/agents/prompts.py` | — | **0** |
| Sandbox removal → SSTI tests fail | — | **5 failures, restored** |

Note for the next runner: the venv lives at `/home/parkave/ccf_code/.venv` (not
inside the worktree) and its editable install points at the **main** repo, so
worktree runs need
`PYTHONPATH=<worktree>/src:<worktree>/runtime`.

## Threat Model Coverage

All six registered threats mitigated as planned; no new surface found.

| Threat | Disposition | Where |
|---|---|---|
| T-06-60 (SSTI at the first render) | mitigated | sandbox + shape-enforced context; inversion-verified |
| T-06-61 (adapter reaching L1–L5) | mitigated | `Agent`-only surface; source scan over six forbidden names |
| T-06-62 (harness overwriting governed fields) | mitigated | named leaf block; five dimensions asserted |
| T-06-63 (dropped vs absent trace) | mitigated | `NO_HARNESS` / `NO_HARNESS_TRACE` positive sentinels |
| T-06-64 (prompt re-resolution in the adapter) | mitigated | docstring rule + determinism test; the seam takes values, not URIs |
| T-06-65 (seam claims degrading into convention) | mitigated | claims scoped to enforcement (D-21); `effects` required |
| T-06-SC (package installs) | n/a | no new dependency; `jinja2` already present |

## Handoff to 06-12 / 06-13 / 06-14

- Implement `HarnessAdapterProtocol` under `runtime/ccf_runtime/adapters/<harness>/`
  — the only path the D-IMPL-53 lint carve-out admits.
- Declare `effects` explicitly. If `unsupported`, D-10 requires the conformance
  suite to drive an effect path and prove it inert; declaring is half the job.
- Consume `agent.instruction_artifact(uri)` and `render_instruction(...)`. Do not
  re-resolve prompt artifacts.
- Write only `HarnessTrace` from `replay_trace`; leave undetermined fields at
  `NO_HARNESS`.
- Per D-07 the plan-level ordering note stands: hardening the Protocol against
  LangGraph as well as Claude before locking the conformance suite would reduce
  rework (research A4). The `object`-returning carrier and the
  translation-not-callback shape were chosen with that asymmetry in mind, but it
  is untested against a real SDK until 06-12 lands.

## Self-Check: PASSED

All six created files exist; all five modified files carry the changes. All
three commits present: `1367445`, `5ef5c9a`, `467199f`.
