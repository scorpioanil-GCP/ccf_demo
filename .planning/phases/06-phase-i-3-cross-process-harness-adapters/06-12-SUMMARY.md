---
phase: 06-phase-i-3-cross-process-harness-adapters
plan: 12
subsystem: harness-adapters
tags: [harness, claude-agent-sdk, conformance, skilling, replay, security]
requires:
  - "ccf.harness.protocol.HarnessAdapterProtocol (06-11) — the contract this implements"
  - "ccf.replay.record.HarnessTrace + NO_HARNESS (06-11) — the dimension-3 slot seam 4 writes"
  - "ccf.agents.prompts.render_instruction (06-11) — the render seam 1 consumes, never calls"
  - "D-IMPL-53 / 06-01 — the CINV-02 HARNESS_ADAPTER_MODULES carve-out"
  - "06-02 — mypy over /runtime, the `harness` marker, the three harness extras"
  - "ccf.agents.agent.Agent (I.2) — the adapter's only fabric-side input"
  - "ccf.skills.grants.GrantLedger / BoundSkillView (I.2) — live per-agent exposure"
provides:
  - "ccf_runtime.adapters.claude_agent.ClaudeAgentAdapter — the first reference adapter"
  - "ccf_runtime.adapters — the harness-import carve-out package root"
  - "tests/conformance/test_harness_adapter.py — the factory-parametrized four-seam suite"
  - "tests/conformance HarnessLeg shape — how 06-13/06-14 enter the suite"
  - "tests/conftest.harness_unavailable + CCF_REQUIRE_HARNESSES"
  - "tests/fixtures/banking/harnesses.yaml — per-harness drive values"
affects:
  - "06-13 (LangGraph) and 06-14 (Google ADK) — add one param each to `harness_leg`"
  - "06-15 — the D-18 portability proof compares governed fields, excludes harness_trace"
tech-stack:
  added: ["claude-agent-sdk==0.2.128 (installed into the shared venv; already pinned in pyproject)"]
  patterns:
    - "harness-native carriers returned as `object`, inspected by a generic carrier walk"
    - "per-seam agent, never a held agent — one adapter serves many principals (D-23)"
    - "capability as a factory argument so both branches of the capability space run"
    - "environment-required legs mirror the CCF_REQUIRE_POSTGRES shape exactly"
key-files:
  created:
    - runtime/ccf_runtime/adapters/__init__.py
    - runtime/ccf_runtime/adapters/claude_agent/__init__.py
    - runtime/ccf_runtime/adapters/claude_agent/adapter.py
    - tests/conformance/test_harness_adapter.py
    - tests/fixtures/banking/harnesses.yaml
  modified:
    - tests/conftest.py
decisions:
  - "No change to HarnessAdapterProtocol was forced — the real Claude surface agreed with 06-11 on all four seams"
  - "The adapter holds no fabric object at all, not even Agent; D-23 makes holding one impossible"
  - "SkillCatalogEntry declares neither a tool description nor an argument schema — surfaced as a gap, not closed by an adapter-authored guess"
  - "A single AdapterFactory callable cannot drive seam 4; the leg supplies a harness-native execution builder alongside it"
metrics:
  duration: ~55 min
  tasks: 3
  tests_added: 16
  completed: 2026-07-26
---

# Phase 06 Plan 12: Claude Agent SDK Reference Adapter Summary

The repository's first harness import is live, legal, and lint-green: a
four-seam `ClaudeAgentAdapter` under the D-IMPL-53 carve-out, exposing exactly
the agent's currently-bound skill-set as in-process MCP tools, proven per-agent
across two agents, with a 16-test conformance suite that drives the real
`claude-agent-sdk==0.2.128` and fails the run if anything opens a socket.

## The headline: the Protocol survived contact with a real SDK

D-07 built this adapter first so the real surface could force Protocol changes.
**It forced none.** Every 06-11 shaping decision held:

| 06-11 decision | What the real Claude surface did |
|---|---|
| Three seams return `object` | `inject_context` returns `ClaudeAgentOptions`; annotating that on the fabric would have made `/src` harness-shaped |
| Seams are translations, not callback registrations | The adapter *builds* a `can_use_tool` closure and hands it over on the carrier; it never registers itself into a loop |
| `expose_skills` returns names | Set equality against `agent.bound_skill_names` is a one-line structural assertion, exactly as intended |
| `effects` required, no default | Made the D-10 inert path a factory argument rather than an afterthought |
| `HarnessTrace` as a dimension-3 leaf | `ResultMessage` reports a model that is *not* the configured one; a shared field would have let the harness overwrite a governed claim |

**Caveat, unchanged from research A4:** Claude is the most callback-shaped of
the three, so this is the weakest of the three tests of the Protocol. 06-13
(LangGraph, which owns its own topology) remains the one likely to force
change. Zero changes here is evidence, not proof.

## The four seams, as bound

1. **Context injection** — `ClaudeAgentOptions.system_prompt` carries the
   already-rendered instructions plus each admitted product's *canonical
   bytes*, so what the harness sees is byte-identical to what replay records.
   The adapter resolves no URI and calls no renderer (T-06-64).
2. **Skill exposure** — `@tool` handlers closing over `Agent.invoke_skill`,
   assembled by `create_sdk_mcp_server`, bound via `mcp_servers`, with
   `allowed_tools` set to exactly `mcp__{server}__{skill}` for the bound set.
   Tools are built from `agent.bound_skill_names` and **never** from the
   catalog. Dispatch is re-resolved from the ledger view on every handler call,
   so a revocation between two harness turns takes effect on the second.
3. **Effect capture** — both declared capabilities implemented.
   `governed` routes through `Agent.emit_effect`; `unsupported` returns a typed
   `EffectRefusal` for every output *and* denies every tool at the permission
   hook, so the absence is conformance-verifiable rather than merely
   unimplemented (D-10).
4. **Replay hooks** — `ResultMessage` → `HarnessTrace`, reading only
   harness-reported values: `model_usage` keys (not the configured `model`),
   `session_id` as the trace reference, its own token counts. Unreported
   fields stay at `NO_HARNESS` rather than being guessed (T-06-63).

## What 06-13 and 06-14 inherit

**Adding a harness is one param.** `harness_leg` is parametrized `["claude-agent"]`
with the required `raise NotImplementedError(request.param)` tail. No test body
names an SDK type, imports one, or asserts on a carrier's concrete class.

**The leg carries more than an adapter factory.** The plan specified
`AdapterFactory = Callable[[capability], adapter]`, and that alias is kept — but
it cannot drive seam 4, whose input is a *harness-native execution result* by
definition. Each leg is therefore a `HarnessLeg` NamedTuple: `harness_id`,
`adapter` (the `AdapterFactory`), `execution` (builds that harness's own result
object), plus `reported_model` and `trace_id` so seam 4 compares against the
harness's values rather than anything CCF configured. **Fill in five fields, get
16 assertions.**

**Carrier inspection is generic.** `_carrier_values` / `_carrier_strings` walk
dataclass fields, `__dict__`, mappings, and sequences to depth 4. Verified
against `ClaudeAgentOptions`; it should reach an ADK `LlmAgent.instruction` and
a LangGraph state channel unchanged. If it does not for your harness, widen the
walk — do not add a harness-specific assertion branch.

### `claude_agent_sdk` type-stub friction: none, but read this

Assumption A3 (the mypy overrides are unexercised) is now half-tested. The
`claude_agent_sdk.*` override needed **no correction** — unlike `joserfc`'s
public-entry-point problem. `mypy` is clean over 83 files with the adapter in
scope.

**The consequence matters more than the absence of friction.** Because the
package ships no `py.typed` and the override sets `ignore_missing_imports`,
every SDK symbol is `Any` inside the adapter. So `mypy --strict` is checking the
adapter's *CCF-facing* signatures and essentially nothing on its SDK-facing
side. That is exactly the boundary the override's own comment claims is "closed
by CCF's own validation at the seam" — which is true only because the
conformance suite exercises those calls for real. **06-13 and 06-14: your
adapter's SDK-facing code is untyped in practice. The conformance leg is its
only check.** Two concrete traps this produced here:

- `ClaudeAgentOptions(...)` returns `Any`, so returning it directly from a
  method declared `-> object` trips `warn_return_any`. Assign to a
  locally-annotated `carrier: object` first.
- `@tool(...)`-decorated handlers are `Any`, so `_tools()` is
  `tuple[Any, ...]`. Do not fake a precise annotation over a vendor type mypy
  cannot see.

### Two docstring constraints that will cost you a rewrite if you miss them

- **Never name a fabric write surface, even in prose.** `tests/harness/test_protocol.py`
  scans source (not signatures) for `FabricHandle`, `GraphWriter`,
  `GraphReader`, `GraphStore`, `ControlPlaneRegistry`, `AssemblyWorker` —
  deliberately, because a name in a docstring is a surface someone considered
  handing over. This **conflicts with the older `runtime/ccf_runtime/cdc/adapter.py`
  convention**, whose "what this adapter cannot do" paragraph names
  ``GraphWriter`` and ``GraphReader`` explicitly. The 06-11 convention is the
  stricter one and wins. Write the paragraph as "no graph write handle, no
  graph read handle, no graph store, no fabric boot handle".
- **Do not write the algorithmic-mode tag's literal token anywhere**, including
  in a sentence explaining why you did not set it. The criterion is a
  `grep -c` for the token, not for an assignment.

## Deviations from Plan

**1. [Rule 3 — Blocking] `claude-agent-sdk` was not installed in the venv**
- **Found during:** Task 1 setup
- **Issue:** 06-RESEARCH.md's "Standard Stack (all three harnesses installed,
  no conflict)" is false of `/home/parkave/ccf_code/.venv`. `pip list` shows
  none of `claude-agent-sdk`, `langgraph`, `google-adk` — only the transitive
  `mcp`. The whole plan is unexecutable without it.
- **Fix:** Installed `claude-agent-sdk==0.2.128` — the **exact pin already
  declared** in the `claude-agent` extra of `pyproject.toml`, audited and
  confirmed at 06-02's blocking human checkpoint (T-06-SC). This is
  environment provisioning of an approved dependency, not package selection:
  no name was chosen, guessed, or substituted, and `pyproject.toml` is
  unchanged.
- **For 06-13 / 06-14:** you will hit the same wall. Install
  `langgraph==1.2.9` and `google-adk==2.5.0` respectively, from the pins
  already in `pyproject.toml`. The venv is **outside** the worktrees and shared,
  so the install persists. Note this also means the plan's "verify the skip by
  uninstalling" criterion cannot be run destructively against a shared venv —
  see deviation 6.

**2. [Rule 1 — Correction] The adapter holds no fabric object at all, not
"`Agent` and nothing else"**
- **Found during:** Task 1
- **Issue:** The plan's action says "The adapter's constructor takes `Agent`
  and its own configuration", and a must-have says "The adapter holds `Agent`
  and nothing else." That contradicts must-have 7 and the D-23 test, which
  require *two* agents bound through **the same adapter** to expose different
  tool sets. An adapter holding one agent cannot satisfy that, and every
  Protocol method already takes `agent` as a keyword argument anyway.
- **Fix:** The constructor takes deployment configuration only (`model`,
  `mcp_server_name`, `mcp_server_version`, `effects`); the agent arrives per
  seam call. This is **strictly stronger** than the criterion — the adapter
  holds *nothing* from the fabric — and it closes a real hazard: a held agent
  plus a passed agent is two answers to "whose skills are these", and a
  per-adapter cache of the held one would outlive a revocation (T-06-66).
- **Commit:** `a1eafad`

**3. [Rule 1 — Correction] `SkillCatalogEntry` declares neither a tool
description nor an argument schema; the plan's criterion assumes both**
- **Found during:** Task 1
- **Issue:** The plan says "Skill names, descriptions, and schemas come from
  the catalog entries; none is a literal" and "Let the SDK derive the JSON
  Schema from the declared input model". Against the actual contract
  (`src/ccf/skills/catalog.py`) there is **no `description` field and no
  declared input model** — an entry carries `name`, `tenant`, `skill_type`,
  a type-specific `binding` descriptor, and opaque `requirements`. Claude's
  `@tool` requires a description and a schema. Implementing the criterion
  literally would have meant inventing both in SDK code, which is the
  No-Hardcoding Rule firing.
- **Fix:** The description is *composed from fields the entry actually carries*
  — `f"{name}@{artifact_version} [{skill_type}]"` — with no adapter-authored
  prose about what any skill does. The schema is a single module constant
  transcribing the fabric-side signature (`Agent.invoke_skill` types
  `arguments` as `Mapping[str, str]`), i.e. an object of string-valued
  properties. Both carry docstrings stating the gap rather than papering it.
- **This is a real artifact-schema gap, not a Claude quirk.** ADK's
  `FunctionTool` and LangGraph's `StructuredTool` both want a description and
  an args schema too, so **06-13 and 06-14 will hit it identically** and all
  three adapters will be inventing the same missing field independently. It is
  a candidate `D-IMPL` (extend `SkillCatalogEntry` with an optional
  `description` and a declared argument schema) and should be raised at the
  phase gate rather than resolved unilaterally inside an adapter.
- **Commit:** `a1eafad`

**4. [Rule 3 — Blocking] `HarnessLeg` replaces the bare `AdapterFactory`
fixture**
- **Found during:** Task 2
- **Issue:** The plan specifies a fixture whose factory "takes the argument
  that lets the suite drive both branches of the capability space" — the effect
  capability. That works for seams 1–3, but **seam 4 takes a harness-native
  execution result**, and there is no harness-agnostic way to conjure one. A
  suite that constructed a `ResultMessage` inline would be the Claude-specific
  suite the plan explicitly warns against.
- **Fix:** The `AdapterFactory` alias is kept and is still
  `Callable[[EffectCapability], HarnessAdapterProtocol]`. The fixture yields a
  `HarnessLeg` NamedTuple carrying that factory plus an `execution` builder and
  the values that execution reports. The fixture tail is the required
  `raise NotImplementedError(request.param)`.
- **Commit:** `cbcd5d0`

**5. [Rule 2 — Hardening] The suite asserts its own guards**
- **Found during:** Task 2/3
- **Issue:** The plan asked for a network guard and for a test of the skip
  mechanism. A monkeypatch that silently failed to apply, or a
  `CCF_REQUIRE_HARNESSES` branch nobody executed, would leave the suite looking
  exactly as green as working ones — which is the T-06-71 failure mode itself.
- **Fix:** Three self-tests: the socket guard is asserted to raise on both
  `create_connection` and `socket.connect`; an absent harness is asserted to
  skip with a message naming the harness and the extra; the same call under
  `CCF_REQUIRE_HARNESSES=1` is asserted to raise `Failed`, not `Skipped`. The
  absent-harness cases use `langgraph`, which is genuinely not installed, so
  they exercise the real path rather than a mock.
- **Commit:** `cbcd5d0`

**6. [Scoping] Two acceptance criteria were verified by a different, safer
means**
- `"pytest -q -rs with claude-agent-sdk uninstalled shows a skip..."` — the venv
  is **shared with four concurrently-running sibling agents**; uninstalling a
  package from it, even temporarily, would break their runs. Verified instead
  by `test_an_absent_harness_skips_with_an_instruction_not_a_mystery`, which
  drives the identical code path against `langgraph` (genuinely absent) and
  asserts the message names both the harness and the extra. This is a
  permanent regression test rather than a one-off manual observation, so it is
  the better artifact regardless.
- `CCF_REQUIRE_HARNESSES=1 pytest ... fails (not skips) when it is not
  installed` — same substitution, same test, asserting `Failed` and
  `not isinstance(..., Skipped)`.

**7. [Rule 1 — Correction] Two Task-1 criteria conflicted with docstrings the
plan itself asked for**
- **Found during:** Task 1
- **Issue:** The plan asks for a "what this adapter cannot do" paragraph
  modelled on `cdc/adapter.py` (which names `GraphWriter`/`GraphReader`) and
  for a paragraph explaining the absent algorithmic-mode tag — while also
  requiring `'GraphWriter' not in source`, `'ccf.graph' not in source`, and
  `grep -c '__ccf_mode__' == 0`. Both paragraphs as written would have failed
  both criteria.
- **Fix:** Both paragraphs rewritten in prose that makes the same claims
  without the identifiers. The criteria are the right ones — they enforce the
  06-11 source-scan convention — so the docstrings moved, not the criteria.
  Recorded above for 06-13/06-14 under "two docstring constraints".
- **Commit:** `a1eafad`

## Verification

| Check | Baseline | Result |
|---|---|---|
| `pytest -q` | 718 passed / 2 skipped | **734 passed / 2 skipped** |
| `pytest tests/conformance/test_harness_adapter.py -q` | — | **16 passed** |
| `CCF_REQUIRE_HARNESSES=1 pytest tests/conformance -q` | — | **124 passed** |
| `mypy` | clean, 80 files | **clean, 83 files** |
| `tools.lints --all` (with a live harness import) | exit 0 | **exit 0** |
| adapter relocated to `ccf_runtime/a2a/` | — | **`cinv02-harness` fires; restored** |
| `grep -c '__ccf_mode__' adapter.py` | — | **0** |
| forbidden-fabric-surface source scan of adapter | — | **clean** |
| over-exposure mutant (append an ungranted skill) | — | **3 seam-2 tests fail; restored** |

The over-exposure mutant is the one that matters: it is the T-06-66 defect in
its most plausible form, and the suite caught it in all three seam-2 tests
including the D-23 two-agent case.

## Threat Model Coverage

| Threat | Disposition | Where |
|---|---|---|
| T-06-66 (skill over-exposure) | mitigated | tools built from `bound_skill_names` only; `allowed_tools` set to exactly that; set equality + grant/revoke round trip + two-agent case; **mutation-verified** |
| T-06-67 (harness acquiring a write handle) | mitigated | adapter holds no fabric object; source scan over six forbidden names; carrier walk and `inspect.getmembers` scan against `WRITE_SURFACE_NAMES` (imported, not redefined) |
| T-06-68 (harness import escaping the carve-out) | mitigated | `cinv02-harness` green with a live import; re-verified by relocating the module and observing the failure |
| T-06-69 (harness overwriting governed replay fields) | mitigated | seam 4 writes only `HarnessTrace`; the with/without-trace record comparison asserts four dimensions and dimension 3's own two fields are byte-identical |
| T-06-70 (prompt literal / re-resolution in the adapter) | mitigated | seam 1 takes rendered strings; the module calls no renderer and resolves no URI; No-Hardcoding lint green |
| T-06-71 (all harness legs silently skipping) | mitigated | `CCF_REQUIRE_HARNESSES` mirrors `CCF_REQUIRE_POSTGRES`; the mechanism is asserted by two tests |
| T-06-72 (the suite reaching a real model) | mitigated | autouse socket guard, which asserts *itself*; no API key configured, no `claude` CLI invoked |
| T-06-SC (package installs) | see deviation 1 | no new package selected; the already-pinned, already-audited `claude-agent-sdk==0.2.128` installed into the shared venv |

## Known Stubs

None. Every seam executes real SDK code paths; nothing returns placeholder
data. The one genuine incompleteness — the uniform
`SKILL_ARGUMENT_SCHEMA` and the composed tool description — is a *gap in the
`SkillCatalogEntry` artifact schema*, documented at both sites and raised in
deviation 3 for a decision rather than silently stubbed.

## Threat Flags

None. No new network endpoint, auth path, file-access pattern, or schema
change at a trust boundary was introduced. The adapter opens no socket and
holds no credential; the in-process MCP server is exactly that — in-process.

## Self-Check: PASSED

All six files present. All three commits present: `a1eafad`, `9cc7a3f`,
`cbcd5d0`. `WRITE_SURFACE_NAMES` appears 4× and is imported, not redefined;
`CCF_REQUIRE_HARNESSES` appears in `tests/conftest.py`; the fixture tail is
`raise NotImplementedError(request.param)`.
