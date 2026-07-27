---
phase: 06-phase-i-3-cross-process-harness-adapters
plan: 14
subsystem: harness-adapters
tags: [harness, google-adk, conformance, d-imp-24, single-writer, d-10]
requires:
  - "ccf.harness.protocol.HarnessAdapterProtocol (06-11) — the contract this implements"
  - "ccf.replay.record.HarnessTrace + NO_HARNESS (06-11) — the dimension-3 slot seam 4 writes"
  - "tests/conformance/test_harness_adapter.py (06-12, 06-13) — the suite this enters as a param"
  - "tests/agents/test_consumption_discipline.WRITE_SURFACE_NAMES (I.2) — imported, never redefined"
  - "D-IMPL-53 / 06-01 — the CINV-02 HARNESS_ADAPTER_MODULES carve-out"
  - "ccf.agents.agent.Agent (I.2) — the adapter's only fabric-side input"
provides:
  - "ccf_runtime.adapters.adk.AdkAdapter — the third reference adapter, completing D-IMPL-24"
  - "ccf_runtime.adapters.adk.ContextInjection — the non-interpolated seam-1 instruction provider"
  - "tests/conformance RefusalDriver + HarnessLeg.refusal — how D-10 (b) reaches each harness's own hook"
  - "tests/conformance test_effects_unsupported_is_inert_not_merely_declared — the four-part D-10 proof"
  - "tests/conformance substrate_digest — the shared L3 byte-comparison helper"
  - "tests/invariants/test_adapter_single_writer.py — the adapter leg of ROADMAP criterion 4"
affects:
  - "06-15 — three adapters now exist for the D-18 portability proof"
  - "06-16 — the gate rows for criterion 3 and criterion 4's adapter boundary are drafted from these tests"
tech-stack:
  added: ["google-adk==2.5.0 (installed into the shared venv from the existing pin; see deviation 1 for the full transitive effect)"]
  patterns:
    - "seam 1 binds a callable *object*, not a str, because ADK interpolates str instructions"
    - "seam 3 binds ADK's short-circuiting before_tool_callback, serialized from the same typed EffectRefusal capture_effect returns"
    - "seam 4 reads the Event stream an adapter-owned BaseAgent produced under a real Runner"
    - "per-harness refusal drivers in the leg, one shared inversion assertion in the suite"
key-files:
  created:
    - runtime/ccf_runtime/adapters/adk/__init__.py
    - runtime/ccf_runtime/adapters/adk/adapter.py
    - tests/invariants/test_adapter_single_writer.py
  modified:
    - tests/conformance/test_harness_adapter.py
    - tests/fixtures/banking/harnesses.yaml
decisions:
  - "No change to HarnessAdapterProtocol's surface was forced by the third harness either — the 06-11 translation bet now has three data points"
  - "Seam 1 binds a callable object rather than a str: ADK interpolates str instructions against session state, which would silently rewrite a product's canonical bytes"
  - "D-10 (b) needs each harness's own refusal hook, so HarnessLeg gained a fifth-and-sixth field rather than the suite gaining a harness branch"
  - "google-adk ships py.typed, so its mypy override is inert and this adapter's SDK-facing side is genuinely strict-checked — unlike the other two"
metrics:
  duration: ~65 min
  tasks: 3
  tests_added: 38
  completed: 2026-07-26
---

# Phase 06 Plan 14: Google ADK Reference Adapter Summary

**D-IMPL-24 is complete.** All three v0 harnesses — Claude Agent SDK, LangGraph,
Google ADK — now pass **one unchanged conformance suite as three params**, with
no shared assertion loosened for any of them. `effects: unsupported` is proven
inert on all three by a four-part assertion rather than accepted as a
declaration, and ROADMAP criterion 4 now has passing observables on all three of
its boundaries.

## The headline: the Protocol's third data point agreed, and the interesting one was seam 1

06-11 bet that every seam should be a **translation producing a harness-native
carrier**, not a callback registration. 06-13 called ADK "callback-shaped like
Claude, so the interesting case is already covered." That was right about the
*shape* and wrong about where the friction would be. **No Protocol surface
change was forced.** Two of ADK's four seams are literally callables the adapter
hands over for ADK to invoke — and a translation the adapter itself calls is
trivially also one it can hand over, so the shape absorbed it without a murmur.

The friction was somewhere nobody predicted:

> **ADK interpolates a `str` instruction against session state.** Binding a
> Context Product's canonical bytes as `LlmAgent.instruction` — the obvious
> reading of the plan's "or `.static_instruction`" — would hand the harness a
> template whose placeholders are the product's own JSON structure. That is a
> silent corruption of the exact bytes replay records, and it would not have
> shown up as an error.

So seam 1 binds `ContextInjection`, ADK's callable form, which is not
interpolated. It is a **callable object rather than a closure** deliberately: a
closure seals its values in cell variables, where the suite's generic carrier
walk cannot see them, and "what the harness will be handed" would have stopped
being inspectable. A frozen dataclass with `__call__` is the same thing ADK
invokes and is walkable. The plan asked for a closure; this is the correction.

Seam by seam:

| Seam | Bound to | Note |
|---|---|---|
| 1 `inject_context` | `LlmAgent.instruction` as `ContextInjection`, plus the session state a `Runner` is seeded with | The `object` return type absorbed a carrier that is neither options nor a graph but an agent-plus-session pair |
| 2 `expose_skills` | `LlmAgent.tools=[FunctionTool(...)]`, one per bound skill | Schema **inferred** by ADK from the closure's `arguments: dict[str, str]` annotation, transcribing `Agent.invoke_skill`'s `Mapping[str, str]`. Nothing authored — 06-13's improvement carried forward |
| 3 `capture_effect` | `before_tool_callback`, whose truthy return short-circuits the tool | A genuine refusal hook, which is what gives D-10 (b) teeth on this leg |
| 4 `replay_trace` | The `Event` stream a real `Runner` yielded over an adapter-owned `BaseAgent` | ADK's own `Event.model_version` / `usage_metadata` first; failing those, what ADK's session machinery carried into the run |

**Zero LLM calls, and it is a real run.** The adapter ships `_EventCapture`, a
`BaseAgent` subclass whose `_run_async_impl` yields events — ADK's own sanctioned
way to run something that is not a model call. The conformance leg drives it
through a real `Runner` with `InMemorySessionService`, so seam 4's evidence is a
run rather than a hand-built result object. The autouse socket guard covers this
param unchanged.

## The D-10 proof, and why it needed a new leg field

D-10 asks for four things, and (b) — "the refusal actually fired" — is a claim
about **each harness's own hook**. No shared assertion can reach
`PermissionResultDeny`, a short-circuit response mapping, and a graph state
channel generically. Writing three harness-specific tests would have been the
harness-specific suite the whole design forbids.

So `HarnessLeg` gained a `refusal: RefusalDriver` field: the leg pokes its own
harness's hook and returns the harness-native refusal artifact, or `None` when
the harness permitted. The assertion stays shared **and is an inversion** — the
same hook must refuse under `unsupported` and *not* refuse under `governed`, so
an adapter that refuses unconditionally fails just as an adapter that refuses
never does.

`test_effects_unsupported_is_inert_not_merely_declared` asserts all four:

- **(a)** `HarnessCapabilities.model_fields["effects"].is_required()` — a
  declared value on a required field, not a default that a silent adapter could
  inherit a claim from.
- **(b)** the harness's own hook fired, and did not fire under `governed`.
- **(c)** a real booted fabric's L3 substrate is byte-identical across the drive,
  write-ahead log included.
- **(d)** nothing on the adapter's public surface is or names a write surface.

**Mutation-verified, both directions.** Deleting the `unsupported` branch from
ADK's before-tool gate — an adapter that declares `unsupported` and permits
anyway — fails on (b) with exactly that message. Giving
`HarnessCapabilities.effects` a default fails on (a). Both restored.

## ROADMAP criterion 4, adapter leg

`tests/invariants/test_adapter_single_writer.py`, parametrized over all three
harnesses so the claim is not proven for one and assumed for the others.

The **(a)** test has two halves on purpose. Capturing a real effect through each
harness seam leaves the substrate byte-identical; then the same effect's payload
*does* change it once handed to `worker.ingest`. Without the second half the test
would pass equally well against a fabric that could not be written at all —
green for want of a writable graph is the false observable this suite exists to
avoid.

**Scoping (D-21).** The module docstring states what each check reaches and no
further: an identifier scan over the files this repository ships, an attribute
check on three constructed instances, and one observed effect under one
deployment's configuration. It says explicitly that this covers neither
transitively reachable code, nor an adapter a deployment writes itself, nor
dynamically obtained attributes. Neither "no path" nor "by construction" appears
(grep-verified 0/0).

**Mutation-verified, and the two halves catch different things.** A `GraphWriter`
identifier named in an adapter fails the source scan but *not* the attribute
scan (a class object's `type().__name__` is its metaclass). An instance obtained
via `getattr(module, "Boot" + "Token")` — deliberately unnameable to the source
scan — fails the attribute scan instead. Neither half subsumes the other, which
is why both are here.

**D-22: `ALLOWED_CCF_PREFIXES` is untouched, git-diff-verified, and asserted.**
No transitive-closure argument is owed because none was needed: that allowlist
scans `src/ccf/agents` only, and adapters live in `ccf_runtime.adapters`, which
it never reads. Research Pitfall 7's scenario did not arise.

## Deviations from Plan

**1. [Rule 3 — Blocking] `google-adk` was not installed, and its install
mutated shared pins**

- **Found during:** setup. Exactly as 06-12 and 06-13 warned.
- **Fix:** installed `google-adk==2.5.0` — the **exact pin already declared** in
  the `adk` extra of `pyproject.toml` and audited at 06-02's blocking human
  checkpoint. No name chosen, guessed, or substituted; `pyproject.toml` is
  unchanged.
- **Full transitive effect on the shared venv, as required:**
  - **Added:** `google-adk 2.5.0`, `google-genai 2.14.0`, `fastapi 0.140.0`,
    `Authlib 1.7.2`, `graphviz 0.21`, `watchdog 6.0.0`, `aiosqlite 0.22.1`,
    `tzlocal 5.4.4`.
  - **DOWNGRADED (this is the part that matters):** `opentelemetry-api`
    1.44.0 → **1.42.1**, `opentelemetry-sdk` 1.44.0 → **1.42.1**,
    `opentelemetry-semantic-conventions` 0.65b0 → **0.63b1**.
  - **`pip check` is now non-clean and was clean before:**
    `opentelemetry-exporter-otlp-proto-grpc 1.44.0 has requirement
    opentelemetry-sdk~=1.44.0, but you have opentelemetry-sdk 1.42.1.`
- **Impact assessed, not assumed.** The exporter arrives transitively under
  `chromadb` and this repository imports no `opentelemetry` symbol anywhere
  (`grep` over the tree returns one prose mention in a docstring). The full
  suite was re-run on the untouched base immediately after the install and
  reproduced the stated baseline **866 passed / 2 skipped exactly**, so nothing
  in the tree currently depends on the downgraded range. **This is still a real
  `pip check` regression in an environment shared with the concurrently-running
  06-10 agent, and it is a resolver conflict a CI image build would surface**
  — flagged here for the gate rather than absorbed.

**2. [Rule 1 — Correction] Seam 1 must not use ADK's `str` instruction form,
which the plan left open**

- **Found during:** Task 1.
- **Issue:** the plan says "`LlmAgent.instruction` or `.static_instruction`.
  Prefer the callable form". Preferring it is not enough — the `str` form is
  **wrong**, not merely less good: ADK interpolates a `str` instruction against
  session state, so a Context Product's canonical JSON would be treated as a
  template and silently rewritten. Replay records the pre-injection bytes; the
  harness would have seen different ones.
- **Fix:** the callable form only, as a callable *object* (`ContextInjection`)
  rather than a closure, so the values are inspectable by the suite's generic
  carrier walk. Recorded in the module docstring as the one asymmetry ADK
  contributes.

**3. [Rule 1 — Correction] `HarnessLeg` gained a field, so all three leg blocks
were edited**

- **Found during:** Task 2.
- **Issue:** D-10 (b) is unreachable from a shared assertion without a
  per-harness driver (see above). The plan's acceptance criterion
  "`git diff tests/conformance/test_harness_adapter.py` shows no edit inside a
  pre-existing shared assertion" is the right constraint and is **satisfied** —
  the complete list of removed lines is: three module-docstring lines, one
  `HarnessLeg`-docstring line, the fixture's `params=` line, the fixture's
  one-line docstring, and one `import` line. **No assertion body was touched.**
- **Reported plainly rather than worked around**, per the brief: adding a field
  to `HarnessLeg` does require touching the claude-agent and langgraph blocks,
  which is a change to code 06-12 and 06-13 wrote. It is additive, it added no
  branch to any test body, and no test body names an SDK type. **The suite
  absorbed a third harness with one param, one fixture block, and one new leg
  field — the "one param and one five-field `HarnessLeg`" claim needed a sixth
  field, and that is the honest correction.**

**4. [Rule 1 — Correction] The (c) half of the D-10 mutation criterion cannot
fire, and saying otherwise would overclaim**

- **Found during:** Task 2 mutation verification.
- **Issue:** the criterion reads "Making an `effects: unsupported` adapter
  silently permit the effect makes assertions **(b) and (c)** fail". (b) fails,
  verified. **(c) cannot fail from that mutation**, because the adapter has no
  route to L3 to take even when it permits — which is the whole point of seams 3
  and (d). A criterion that expected (c) to fail here would have tempted an
  implementer to wire a write path into an adapter to make it fail.
- **Fix:** the mutation was run and (b) is the assertion that fires, with the
  message naming D-10. (c) is retained because it is a true and independently
  valuable observation — it would fail against an adapter that *did* acquire a
  route — but it is not evidence about this mutant, and the SUMMARY says so
  rather than reporting a four-for-four that did not happen.

**5. [Rule 2 — Hardening] `google-adk` ships `py.typed`; the pyproject override
comment asserting otherwise is wrong**

- **Found during:** Task 1 mypy run.
- **Issue:** `pyproject.toml`'s `google.adk.*` override is documented as
  "google-adk 2.5.0 ships no py.typed marker". It does ship one
  (`site-packages/google/adk/py.typed`), so `ignore_missing_imports` is **inert**
  for this package and strict mypy resolves ADK's real types. This is the
  opposite of 06-12's finding for `claude-agent-sdk`, and it corrects research
  assumption A3 for this row.
- **Consequence, which is good news:** unlike the other two adapters, this one's
  SDK-facing side is **genuinely strict-checked** rather than silently `Any`.
  Two concrete effects: imports name leaf modules (`google.adk.tools.function_tool`)
  because the package root re-exports lazily and strict mypy rejects an implicit
  re-export; and `_effect_gate` returns an untyped callable on purpose, because
  ADK annotates its before-tool hook positionally while calling it by keyword.
- **`pyproject.toml` was not changed** (the brief forbids it, and the override is
  harmless-if-inert). The correction is recorded in the adapter's module
  docstring and here, for the gate.

**6. [Scoping] `tests/fixtures/banking/harnesses.yaml` modified, outside
`files_modified`**

- Same reasoning 06-13 recorded: per-harness drive values live in a fixture file
  precisely so the suite does not assert against literals it authored. One
  additive `adk:` block keyed by the new param name; no existing key touched, so
  no merge hazard with the concurrent 06-10 agent, which is nowhere near these
  files.

**7. [Note] The `before_model_callback` seam-4 source named in the plan was not
bound**

- The plan's seam-4 action names "`before_model_callback(LlmRequest)` for the
  model name". With no model configured — which D-09 requires — that callback
  **never fires**, so binding it would have shipped an untested code path whose
  only evidence would be that it exists. Seam 4 instead reads ADK's own
  `Event.model_version` and `Event.usage_metadata` (populated by a real model
  run, and checked by the type system) and falls back to what ADK's session
  machinery carried into the run. Both sources are the harness's; neither is
  read off the adapter's own fields, which
  `test_seam_4_reads_what_the_harness_carried_not_what_the_adapter_held`
  asserts for this param as for the other two.

## Verification

| Check | Baseline | Result |
|---|---|---|
| `pytest -q` | 866 passed / 2 skipped | **904 passed / 2 skipped** |
| `pytest -q` immediately after the adk install, before any edit | 866 / 2 | **866 / 2 — install caused no regression** |
| `CCF_REQUIRE_HARNESSES=1 pytest tests/conformance/test_harness_adapter.py -q` | 31 (2 params) | **48 (3 params)** |
| `--collect-only` param census | — | **15 `[adk]`, 15 `[claude-agent]`, 15 `[langgraph]`** |
| `pytest -k effects_unsupported` | — | **6 passed** (the D-10 proof + the seam-3 refusal, all params) |
| `pytest -k 'adk and (two_agent or multi)'` (D-23) | — | **1 passed** |
| `pytest tests/invariants -q` | — | **54 passed / 2 skipped** (boot, A2A, ArtifactStore, adapter) |
| `pytest tests/invariants/test_adapter_single_writer.py -q` | — | **21 passed across 3 harness params** |
| `mypy` | clean, 96 files | **clean, 98 files** |
| `tools.lints --all` (three live harness imports) | exit 0 | **exit 0** |
| adapter copied to `ccf_runtime/_probe_adk.py` | — | **`cinv02-harness` fires 4×; probe removed, exit 0** |
| `grep -c '__ccf_mode__' adk/adapter.py` | — | **0** |
| forbidden-fabric-surface source scan of adapter | — | **clean** (also `ccf.graph`, `OrchestrationProtocol`) |
| eager-import check (`'google.adk' not in sys.modules`) | — | **passes** |
| D-21 phrase grep on the invariant module | — | **`no path` 0, `by construction` 0** |
| `git diff tests/agents/test_consumption_discipline.py` | — | **empty (D-22)** |
| **mutant:** unsupported adapter permits anyway | — | **D-10 (b) fails with its own message; restored** |
| **mutant:** `effects` field defaulted | — | **D-10 (a) fails on `is_required()`; restored** |
| **mutant:** adapter names a write surface | — | **source scan fails for that param only; restored** |
| **mutant:** adapter holds an unnameable write-surface instance | — | **both attribute scans fail; restored** |

Four mutants, four caught, each by a different assertion.

## Threat Model Coverage

| Threat | Disposition | Where |
|---|---|---|
| T-06-79 (skill over-exposure through ADK's `FunctionTool` list) | mitigated | tools built from `bound_skill_names` only; names read back off the constructed tools; set equality + revocation round trip + the D-23 two-agent case, all passing for `[adk]` |
| T-06-80 (an adapter acquiring or exposing a graph write handle) | mitigated | identifier scan over every adapter source file + attribute scan over three constructed adapters, `WRITE_SURFACE_NAMES` imported; effects reach L3 only via `emit_effect` into L2, proven across all three harnesses; **both scan halves mutation-verified independently** |
| T-06-81 (`effects: unsupported` as an opt-out with better branding) | mitigated | the four-part proof, run for every param, with (b) driving each harness's own refusal hook and inverting it under `governed`; mutation-verified |
| T-06-82 (`google-adk`'s heavy tree loading in a non-ADK deployment) | mitigated | `ccf_runtime.adapters` imports no adapter eagerly, asserted by a `sys.modules` check; `tests/lints/test_extra_isolation.py` green |
| T-06-83 (`ALLOWED_CCF_PREFIXES` widened by precedent) | mitigated | untouched, git-diff-verified, and asserted by a test in the new module |
| T-06-84 (an invariant test claiming more than it checks) | mitigated | a "what they do not enforce" paragraph naming three specific gaps; forbidden phrases grep-verified absent |
| T-06-85 (the ADK leg reaching a real model) | mitigated | `BaseAgent` subclass driven by a real `Runner` with no model configured; the autouse socket guard covers this param and asserts itself |
| T-06-SC (package installs) | **see deviation 1** | no new package selected; the already-pinned, already-audited `google-adk==2.5.0` installed into the shared venv — **with a reported `pip check` regression** |

## Known Stubs

None. Every seam executes real SDK code paths and a real `Runner` really runs.
Two genuine incompletenesses, both surfaced rather than papered over:

1. The `SkillCatalogEntry` artifact gap (no declared description) — **now with a
   third adapter's independent evidence** that the field is missing. All three
   compose the same description from fields the entry carries. This remains a
   phase-gate `D-IMPL` candidate and was deliberately not settled here.
2. Seam 4's `before_model_callback` binding was not made, because it cannot fire
   without a model (deviation 7). The values it would have supplied are read
   from ADK's own event fields instead.

## Threat Flags

None. No new network endpoint, auth path, file-access pattern, or schema change
at a trust boundary. The adapter opens no socket and holds no credential.
`google-adk` pulls FastAPI transitively, but nothing in this plan constructs or
serves an application.

## Handoff to 06-15 / 06-16

- **Three adapters exist and are interchangeable at the Protocol.** The D-18
  portability comparison should exclude `harness_trace` and nothing else; the
  three legs report three different models and three different trace references
  precisely so a comparison that accidentally included them would fail.
- **For the gate:** deviation 1's `pip check` regression, deviation 5's incorrect
  `pyproject.toml` override comment, and the `SkillCatalogEntry` description /
  argument-schema gap are the three items this plan surfaced and did not settle.
- **`tests/conformance.substrate_digest` is now shared.** `tests/invariants`
  imports it. A fourth caller should import it too rather than write a third
  copy of the WAL-inclusive digest.

## Self-Check: PASSED

All five files present and carrying the changes:
`runtime/ccf_runtime/adapters/adk/__init__.py`,
`runtime/ccf_runtime/adapters/adk/adapter.py`,
`tests/conformance/test_harness_adapter.py`,
`tests/fixtures/banking/harnesses.yaml`,
`tests/invariants/test_adapter_single_writer.py`.
All three commits present: `1d470d0`, `85860c9`, `65fe53f`. `AdkAdapter` is
importable, structurally `isinstance`-conforms to `HarnessAdapterProtocol`, and
the `adk` param is collected (not skipped) under `CCF_REQUIRE_HARNESSES=1`.
