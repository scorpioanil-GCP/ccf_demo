---
phase: 08-phase-i-5-examples-suite-full-ci-verification
plan: 11
subsystem: examples
tags: [examples, harness-portability, exam-04, live-legs, ollama, anthropic, d-03, d-04]
requires: [08-10]
provides:
  - "make example-03-live-ollama: all three harness legs against a live Ollama model, keyless local access (D-03) — recorded green locally"
  - "make example-03-live-anthropic: same legs gated on ANTHROPIC_API_KEY with refusal-on-absence"
  - "D-04 structural equivalence assertions: same product class/version/lineage identity, five-dimension records, governed emission — never byte-equal"
affects: [08-12 CI examples job, EXAM-04 completion]
tech-stack:
  added: []
  patterns:
    - "Claude live leg outcome (A): native endpoint — ClaudeAgentOptions.env ANTHROPIC_BASE_URL against Ollama's Anthropic-compatible /v1/messages, verified empirically before implementation"
    - "ADK live model via LLMRegistry BaseLlm registration for the configured model name; LangGraph via deployment-injected model callable over the carrier's own injected state"
    - "Runner safeguards: per-call timeout (env over artifact default), overall LiveBudget wall-clock bound, fast reachability pre-flight — every failure mode is a diagnostic exit 2"
key-files:
  created:
    - examples/03-harness-portability/artifacts/live.yaml
    - examples/03-harness-portability/legs/ollama_client.py
    - examples/03-harness-portability/legs/live.py
  modified:
    - examples/03-harness-portability/run.py
    - examples/03-harness-portability/README.md
decisions:
  - "Claude↔Ollama seam resolved as outcome (A) — native endpoint: claude-agent-sdk 0.2.128's subprocess transport merges ClaudeAgentOptions.env over the process environment, the CLI honours ANTHROPIC_BASE_URL, and Ollama 0.30.6 serves an Anthropic-compatible /v1/messages (probed empirically: real CLI session against local Ollama returned genuine per-model usage). No seam substitution, no new packages"
  - "Both live clients (Ollama native /api/chat, Anthropic REST /v1/messages) are thin httpx wrappers satisfying LLMClientProtocol structurally — no anthropic/ollama/litellm package anywhere; the Anthropic path uses the REST surface directly so examples/ imports no vendor SDK (CINV-02 discipline)"
  - "ADK live events verified to carry a custom BaseLlm's model_version and usage_metadata (probed at 2.5.0); the adapter's capture vehicle runs second in the same session so replay_trace gets both its declared sources in precedence"
metrics:
  duration: "~26 min"
  completed: "2026-07-31"
---

# Phase 08 Plan 11: Example 03 live legs (Ollama + Anthropic) Summary

EXAM-04 completed: the same one agent definition now runs under all three
harnesses against a live model — Ollama keyless by default, Anthropic
key-gated — with D-04 structural (never byte-equal) equivalence asserted,
zero new dependencies, and the Claude leg on the native model path.

## What was built

- **Task 1 (f267972):** `legs/ollama_client.py` — thin httpx client for
  Ollama's `POST /api/chat` behind `LLMClientProtocol` (base URL/model from
  `CCF_OLLAMA_BASE_URL`/`CCF_OLLAMA_MODEL` over `artifacts/live.yaml`
  defaults; keyless; generation capped by `runner.max_tokens`).
  `legs/live.py` — the three live legs: Claude on **outcome (A)** (native
  endpoint via `ClaudeAgentOptions.env`, real `ClaudeSDKClient` session,
  real CLI, bounded by `max_turns` + budget); ADK via `LLMRegistry`
  `BaseLlm` binding at 2.5.0 driving the adapter's real `LlmAgent` through
  a real `Runner`; LangGraph via an injected model callable consuming
  exactly the carrier's injected state, reported values through the
  adapter's real compiled graph. `AnthropicMessagesClient` (httpx REST,
  key from env, refusal when absent). Every live leg asserts all four
  adapter seams executed. `artifacts/live.yaml` carries every deployment
  value (endpoints, models, auth-token placeholder, timeouts, budget,
  max_turns/max_tokens, drive turn).
- **Task 2 (bad8ea0):** `run.py` refactored around a shared `_decision()`
  bundle (fabric boot → gated product → one agent → pinned instructions →
  record builder) used by both modes; `_live(provider)` drives the legs
  and asserts D-04 structurally: same product class, version, and lineage
  identity recovered out of each carrier; five typed dimensions per record
  with agent conditioning equal and `model_version.harness_trace` being
  this leg's own live trace; one governed emission. Exit 2 with actionable
  diagnostics for unreachable provider, absent key, or breached budget
  (`ProviderUnavailable`, `LiveBudgetExceeded`, httpx errors, SDK CLI
  errors). README finalized: both modes, the three commands, provider env
  vars, the explicit D-04 equivalence-strength distinction, citations, D-09
  rationale, and the cloud-relay locality note (RESEARCH Pitfall 2).

## Claude/Ollama decision-table outcome: (A) — native endpoint

Evaluated at execution time against the installed SDK (0.2.128) and a live
probe before any code was written: Ollama 0.30.6 answers Anthropic-shaped
`POST /v1/messages` and a real `claude` CLI session pointed at it via
`ANTHROPIC_BASE_URL` completed with genuine per-model usage
(`modelUsage: {"qwen3-vl:8b": ...}`). The live Claude leg therefore keeps
the real harness loop AND the native model path — no seam substitution
(outcome B unnecessary), no stop (outcome C not reached), and zero new
packages (`git diff pyproject.toml` empty).

## Recorded manual live-ollama run (08-VALIDATION.md Manual-Only)

`make example-03-live-ollama` against local Ollama, 2026-07-31: **exit 0**.

```
examples/03-harness-portability: OK (live, ollama)
  provider              ollama (qwen3-vl:8b)
  legs                  ['claude-agent-sdk', 'google-adk', 'langgraph']
  reported models       qwen3-vl:8b, qwen3-vl:8b, qwen3-vl:8b
  token accounting      199027/3998, 508/512, 492/512
```

All three legs ran the same live local model through their own native
seams; structural assertions held. (`qwen3-vl:8b` is locally pulled — not
a `*-cloud` relay model.)

## Deviations from Plan

**1. [Rule 3 - Blocking] Fast reachability pre-flight added to the Ollama path**
- **Found during:** Task 2 (unreachable-provider acceptance test)
- **Issue:** With Ollama down, the first live leg is the Claude CLI, which
  retries against the dead `ANTHROPIC_BASE_URL` until the overall budget
  (900s) elapses — the exit-2 path worked but was not prompt.
- **Fix:** `OllamaChatClient.probe()` (GET `/api/tags`, bounded by the
  per-call timeout capped at 10s) runs in `resolve_provider` before any
  leg starts; unreachable now exits 2 in under a second.
- **Files modified:** legs/ollama_client.py, legs/live.py
- **Commit:** bad8ea0

## Verification

- `make example-03` exit 0 after the run.py refactor — deterministic leg
  unchanged (product bytes identical ×3, 7 governed fields equal ×3,
  3 distinct traces)
- `make example-03-live-ollama` exit 0 (recorded above); with
  `CCF_OLLAMA_BASE_URL=http://127.0.0.1:9` exits 2 with the
  start-the-provider diagnostic
- `make example-03-live-anthropic` without `ANTHROPIC_API_KEY` exits 2
  with the export-the-key refusal (key never stored/logged — T-08-26)
- `make lint` exit 0; `make typecheck` clean (156 files)
- `grep -rn "11434\|api_key\s*=\s*[\"']" examples/03-harness-portability/legs/`
  empty; `grep -rn "^import anthropic\|^from anthropic" examples/` empty;
  `git diff pyproject.toml` empty (zero new packages)

## Known Stubs

None — `--mode live` is fully wired for both providers; the flag surface
08-10 stubbed is now complete.

## Threat Flags

None new — T-08-26 held (key env-only, sent as a header, never a literal,
never printed), T-08-27 held (live model output reaches nothing but the
governed `capture_effect` → `emit_effect` path and the seam-4 trace; the
product-contract gates are upstream of every leg), T-08-SC held (zero
packages added).

## Self-Check: PASSED
