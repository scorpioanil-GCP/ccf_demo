---
phase: 06-phase-i-3-cross-process-harness-adapters
plan: 13
subsystem: harness-adapters
tags: [harness, langgraph, conformance, skilling, replay, topology]
requires:
  - "ccf.harness.protocol.HarnessAdapterProtocol (06-11) — the contract this implements"
  - "ccf.replay.record.HarnessTrace + NO_HARNESS (06-11) — the dimension-3 slot seam 4 writes"
  - "tests/conformance/test_harness_adapter.py (06-12) — the suite this enters as a param"
  - "tests/conftest.harness_unavailable + CCF_REQUIRE_HARNESSES (06-12)"
  - "D-IMPL-53 / 06-01 — the CINV-02 HARNESS_ADAPTER_MODULES carve-out"
  - "ccf.agents.agent.Agent (I.2) — the adapter's only fabric-side input"
provides:
  - "ccf_runtime.adapters.langgraph.LangGraphAdapter — the second reference adapter"
  - "ccf_runtime.adapters.langgraph.LangGraphCarrier — the topology-owning seam-1 carrier"
  - "tests/conformance test_seam_4_reads_what_the_harness_carried_not_what_the_adapter_held"
  - "tests/conformance ABSENT_HARNESS — a skip probe no extra can hollow out"
  - "tests/fixtures/banking/harnesses.yaml — the langgraph drive block"
affects:
  - "06-14 (Google ADK) — adds the third param; the suite shape is now proven twice"
  - "06-15 — two adapters now exist for the D-18 portability proof"
tech-stack:
  added: ["langgraph==1.2.9 (installed into the shared venv from the existing pin; pulls langchain-core==1.5.1)"]
  patterns:
    - "the seam-1 carrier is the compiled graph + initial state + run configuration"
    - "seam 3 called from inside an adapter-owned node — a translation used as a node body"
    - "seam 4 reads the run configuration a node captured, never the adapter's own fields"
    - "tool argument schemas inferred from a closure annotating the fabric-side signature"
key-files:
  created:
    - runtime/ccf_runtime/adapters/langgraph/__init__.py
    - runtime/ccf_runtime/adapters/langgraph/adapter.py
  modified:
    - src/ccf/harness/protocol.py
    - tests/conformance/test_harness_adapter.py
    - tests/fixtures/banking/harnesses.yaml
decisions:
  - "No change to HarnessAdapterProtocol's surface was forced by topology ownership — the A4 bet held, and the mechanism that makes it hold is now recorded in the module docstring"
  - "The seam-1 carrier is graph + state + config, because a state-channel value alone is not invocable"
  - "The tool argument schema is inferred from the closure's annotation rather than transcribed as a constant — same reasoning as 06-12, less authored surface"
  - "The absent-harness skip probes must not name a real harness; a leg's arrival was silently disarming them"
metrics:
  duration: ~50 min
  tasks: 3
  tests_added: 15
  completed: 2026-07-26
---

# Phase 06 Plan 13: LangGraph Reference Adapter Summary

The Protocol's highest-risk shaping decision has now met the harness it was
shaped for. A `LangGraphAdapter` that builds and compiles its own three-node
`StateGraph` passes the **unchanged** 06-12 conformance suite as a second
param, with real `StructuredTool`/`ToolNode` objects, a real `.invoke()`, and
no model — and it forced **no change to `HarnessAdapterProtocol`'s surface**.

## The headline: the A4 bet held, and here is why

Research assumption A4 said Claude is the most callback-shaped of the three, so
06-12's zero-Protocol-changes result was weak evidence; LangGraph — where the
adapter owns the topology — was the real test. It passed, and the reason is
mechanical rather than lucky:

> **Because every seam is a plain translation the adapter itself calls, a
> topology-owning adapter can call it from inside a node it built.** The
> LangGraph effect node is literally a call to `capture_effect`. A
> callback-shaped seam would have required the *harness* to call CCF — which is
> exactly the thing LangGraph has no loop to do.

Seam by seam, against a harness with no loop:

| Seam | 06-11's shape | What topology ownership actually needed |
|---|---|---|
| 1 `inject_context -> object` | harness-native carrier | The carrier is the **compiled graph + initial state + run config** — the three arguments `graph.invoke(state, config)` takes. `object` absorbed this without a murmur; any narrower annotation chosen against Claude would have broken here |
| 2 `expose_skills -> tuple[str, ...]` | names, not tool objects | Names read back off the real `ToolNode.tools_by_name`. Set equality against `bound_skill_names` is still one line |
| 3 `capture_effect` | a translation | Used **as a node body**. This is the cell that would have failed a callback-shaped Protocol |
| 4 `replay_trace(execution: object)` | harness-native execution result | The one genuine asymmetry — see below. Absorbed by `object`, but it changes what an adapter author should expect |

**The one asymmetry worth naming (and it is an adapter concern, not a Protocol
defect).** A topology-owning harness exposes its run configuration *only from
inside the topology*: a node receives `RunnableConfig`, the caller does not get
one back. So there is no vendor result object for seam 4 to translate. The
adapter captures the configuration in a node it owns, and the "execution
result" is the run's plain final state. 06-11's docstring predicted
"`RunnableConfig` plus final state", which is not observable; that claim is now
corrected in `protocol.py` rather than left to mislead 06-14.

**No harness identity anywhere.** No method or field on the Protocol names a
harness, and no implementation in `/src` branches on harness identity — the two
shapes are accommodated by the seams *being* translations, not by a conditional.
This was checked, not assumed: `grep -rn 'langgraph\|claude_agent_sdk\|google.adk' src/` is empty
and the two adapters share no branch.

## What the adapter is, concretely

Constructor takes deployment configuration only — `model`, `thread_id`,
`run_tags`, `effects` — and **holds no fabric object at all**, following 06-12's
correction. The agent arrives per seam call, which is what makes the D-23
two-agent case possible through one adapter instance.

The adapter-owned topology is three plain-function nodes,
`START → skills → effect → trace → END`:

- **`skills`** publishes the exposed tool names onto the state channel from the
  real `ToolNode`'s own registry.
- **`effect`** calls `capture_effect` and puts the returned typed value on a
  channel. It never writes; owning the topology does not widen what the nodes
  can reach, because they close over the same three `Agent` seams and nothing
  more.
- **`trace`** captures what the run configuration carried, which is the only
  place it is visible.

Every node is a plain function, so the graph runs end to end with no model and
no network — the suite's autouse socket guard covers this param unchanged.

**Tool argument schemas are inferred, not transcribed.** 06-12 hit the
`SkillCatalogEntry` gap (no description, no argument schema) and composed a
description from fields the entry carries plus a single hand-written schema
constant. This plan follows that precedent for the description **verbatim** (it
is a candidate `D-IMPL` for the phase gate, not an adapter's to settle
differently) but improves the schema half: `StructuredTool.from_function`
infers the schema from a closure annotated `arguments: dict[str, str]`, which
transcribes `Agent.invoke_skill`'s own `Mapping[str, str]`. Nothing about the
schema is authored. Verified: `args_schema.model_json_schema()` yields the
string-valued object 06-12 wrote by hand.

## Deviations from Plan

**1. [Rule 3 — Blocking] `langgraph` was not installed**
- **Found during:** setup. Exactly as 06-12 warned.
- **Fix:** installed `langgraph==1.2.9` — the **exact pin already declared** in
  the `langgraph` extra of `pyproject.toml` and audited at 06-02's blocking
  human checkpoint. No name chosen, guessed, or substituted; `pyproject.toml`
  is unchanged. It pulled `langchain-core==1.5.1` plus the checkpoint/prebuilt/
  sdk packages, all as research recorded.
- **Side effect worth flagging to 06-14 and the gate:** the resolver
  **downgraded `websockets` 16.1.1 → 15.0.1** in the shared venv to satisfy
  `langgraph-sdk`. The full suite is green after it (850 passed / 2 skipped),
  but this is a real change to a shared environment made by an install, and it
  is the kind of thing that shows up somewhere unrelated later.

**2. [Rule 1 — Bug] Installing `langgraph` silently disarmed two of 06-12's own
guard tests**
- **Found during:** Task 3.
- **Issue:** 06-12 built `test_an_absent_harness_skips_...` and
  `test_an_absent_harness_fails_when_the_environment_requires_it` to drive the
  real skip path against `langgraph`, "which is genuinely not installed". The
  moment this plan installed it, both tests failed — and the alternative
  reading is worse: had they been written to skip rather than assert, they
  would have gone silently vacuous. **A probe that stops probing the moment a
  leg arrives is precisely the T-06-71 failure mode it exists to catch.**
- **Fix:** both now drive `ABSENT_HARNESS = "ccf_no_such_harness_sdk"` — a
  module name no extra will ever install. The assertions are unchanged in
  substance (message names the module, names `pip install -e`, offers
  `.[harnesses]`); only the probe moved. 06-14 will not have to touch them
  again.
- **This is a change to a pre-existing shared test body**, which Task 3
  forbids on principle. It is reported rather than smuggled: the change was
  forced by the environment, not by the Protocol or the adapter, and no
  assertion was weakened.

**3. [Scoping] `tests/fixtures/banking/harnesses.yaml` modified, outside
`files_modified`**
- **Found during:** Task 3.
- **Issue:** the plan lists four files, but 06-12's design puts every
  per-harness drive value (model ids, correlation identifiers, reported tokens)
  in a fixture file precisely so the suite does not assert against literals it
  authored. A `langgraph` block is unavoidable and is where it belongs.
- **Fix:** one additive block keyed by the new param name. No existing key
  touched — no merge hazard with the concurrent 06-09 agent, which is nowhere
  near these files.

**4. [Rule 1 — Correction] The D-23 acceptance criterion selected nothing**
- **Found during:** Task 3.
- **Issue:** the criterion is
  `pytest -k 'langgraph and (two_agent or multi)' -q` **passes**. The D-23 test
  06-12 wrote is `test_seam_2_is_per_agent_not_per_catalog`, which matches
  neither substring, so `-k` would have selected zero tests and pytest exits 5
  ("no tests ran") — the criterion could not pass against a correct tree, and
  would have tempted a reader to add a redundant second D-23 test to satisfy it.
- **Fix:** the existing test is **renamed** to
  `test_seam_2_is_per_agent_not_per_catalog_the_two_agent_case`. The body is
  byte-identical; the property under test did not move. `-k` now selects 1 test
  and it passes.

**5. [Rule 2 — Hardening] The added assertion is stronger than the plan asked
for, and is harness-agnostic**
- The plan asked for a "`RunnableConfig` propagation assertion" so
  `harness_trace` is "populated from something the harness actually carried
  rather than from a value the adapter already had". Written as a LangGraph
  assertion that would have been the harness-specific test body the suite's
  whole design forbids.
- **Fix:** `test_seam_4_reads_what_the_harness_carried_not_what_the_adapter_held`
  points the suite's existing generic carrier walk at the *execution result*:
  the trace reference and the reported model must be findable **inside** the
  object the harness produced, and the trace the adapter derives must agree.
  It names no SDK type, runs for both params, and for LangGraph it proves the
  values travelled through the harness's own run-configuration machinery into
  a real run's final state.
- **Mutation-verified:** replacing `model_version` with the adapter's own
  configured `model` fails this test *and* `test_seam_4_records_what_the_harness_reported`.

**6. [Note] No Protocol *surface* change was made, so Task 2's "record every
change with the requirement that forced it" has an empty list.** Three
docstring claims were corrected because contact with a topology-owning harness
falsified them (seam 1's carrier description, seam 4's execution-result
description, and the untested-bet framing of the module docstring). Those are
recorded above and in the commit. **No seam was downgraded from mandatory to
optional; no `D-IMPL-NN` stop was needed.**

## Verification

| Check | Baseline | Result |
|---|---|---|
| `pytest -q` | 835 passed / 2 skipped | **850 passed / 2 skipped** |
| `pytest tests/conformance/test_harness_adapter.py -q` | 16 passed (1 param) | **31 passed (2 params)** |
| `CCF_REQUIRE_HARNESSES=1 pytest tests/conformance -q` | 124 passed | **161 passed** |
| `pytest -k 'langgraph and (two_agent or multi)'` | — | **1 passed** |
| `mypy` | clean, 92 files | **clean, 94 files** |
| `tools.lints --all` (with a live `langgraph` import) | exit 0 | **exit 0** |
| adapter copied to `ccf_runtime/_probe_lg.py` | — | **`cinv02-harness` fires twice; probe removed** |
| `grep -c '__ccf_mode__' adapter.py` | — | **0** |
| forbidden-fabric-surface source scan of adapter | — | **clean** (also `ccf.graph`, `OrchestrationProtocol`) |
| over-exposure mutant (append an ungranted skill) | — | **3 seam-2 langgraph tests fail; restored** |
| configured-model mutant at seam 4 | — | **2 seam-4 langgraph tests fail; restored** |

Two mutants, both caught. The seam-4 one is the mutation 06-12 could not run
because it had only one harness reporting one model.

## Threat Model Coverage

| Threat | Disposition | Where |
|---|---|---|
| T-06-73 (skill over-exposure through `ToolNode`) | mitigated | the tool node is built from `bound_skill_names` only; names read back off the harness's own registry; set equality + revocation round trip + the D-23 two-agent case; **mutation-verified** |
| T-06-74 (an adapter-owned node writing to L3) | mitigated | the effect node returns the value `capture_effect` produced onto a state channel; the adapter holds no fabric object; source scan over the six forbidden names; `WRITE_SURFACE_NAMES` walk of the carrier and of the adapter's members |
| T-06-75 (a harness import escaping the carve-out) | mitigated | `cinv02-harness` green with a live import; re-verified by copying the module out of the carve-out and observing two findings |
| T-06-76 (conflating the harness seam with the orchestration seam) | mitigated | the D-IMPL-17 disambiguation is a named paragraph in the module docstring, stating Phase I.4 orchestration as out of scope; the `OrchestrationProtocol` identifier appears nowhere in the module, so the grep is 0 globally rather than 0-outside-a-paragraph |
| T-06-77 (a Protocol relaxed to fit one harness) | mitigated | no seam downgraded, no surface change, both params green before this plan closed; the docstring now records *why* both shapes fit, so a later edit cannot undo it by accident |
| T-06-78 (the LangGraph leg reaching a real model) | mitigated | plain-function nodes, no model configured, no chat model constructed; the autouse socket guard covers this param and asserts itself |
| T-06-SC (package installs) | see deviation 1 | no new package selected; the already-pinned, already-audited `langgraph==1.2.9` installed into the shared venv |

## Known Stubs

None. Every seam executes real SDK code paths and the graph really runs. The
one genuine incompleteness remains the `SkillCatalogEntry` artifact gap 06-12
surfaced (no declared description); this adapter follows that precedent rather
than settling it, and it stays a phase-gate `D-IMPL` candidate — now with a
second adapter's independent evidence that the field is missing. The argument
schema half of the gap is closed here by inference from the fabric-side
signature, which 06-14 should prefer over a hand-written constant if ADK's
`FunctionTool` allows it (research says it introspects the signature, so it
should).

## Threat Flags

None. No new network endpoint, auth path, file-access pattern, or schema change
at a trust boundary. The adapter opens no socket and holds no credential.

## Handoff to 06-14

- Add one param and one five-field `HarnessLeg`. **The suite absorbed a second
  harness with zero shared-assertion edits**, which is now demonstrated rather
  than claimed — the only test-body change this plan made was forced by an
  install, not by the suite's shape (deviation 2).
- The `_carrier_values` walk reached a compiled `StateGraph` carrier and a
  LangGraph run's final state without widening. It should reach an ADK
  `LlmAgent.instruction` too.
- Your `execution()` builder can construct a `World()` and drive the real
  runtime — the LangGraph leg does, and that is what makes seam 4's evidence
  a real run rather than a hand-built result object. Prefer it if ADK's
  `Runner` allows it with no model (research says it does).
- `google-adk==2.5.0` is not installed either. Install it from the existing
  pin; watch what the resolver does to shared pins (deviation 1).

## Self-Check: PASSED

All five files present and carrying the changes. All three commits present:
`c535386`, `1c5ef3e`, `ca691fe`. `LangGraphAdapter` is importable,
structurally `isinstance`-conforms to `HarnessAdapterProtocol`, and the
`langgraph` param is collected (not skipped) under `CCF_REQUIRE_HARNESSES=1`.
