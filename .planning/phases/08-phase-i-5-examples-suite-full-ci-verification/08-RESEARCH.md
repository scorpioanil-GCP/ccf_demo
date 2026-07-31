# Phase 8: Phase I.5 — Examples Suite & Full CI Verification - Research

**Researched:** 2026-07-30
**Domain:** Packaging/demonstration of an already-built SDK — eight runnable examples, CI pipeline extension, hardening-wave closure, v0 gate
**Confidence:** HIGH (nearly everything verified against the live tree at `main` 510bd75)

## Summary

Phase 8 is almost entirely *packaging and demonstration of shipped mechanism*, not new
mechanism. The gate document for Phase I.4 (`docs/PHASE_I4_GATE.md` §5) states this
explicitly: examples 05/06's mechanism is "delivered and test-proven here … the examples
are packaging + demonstration." The tree at phase start is `main` (0a7c7b4→510bd75):
1315 passed / 0 skipped under `CCF_REQUIRE_HARNESSES=1`, mypy --strict clean (155 files),
`tools.lints --all` exit 0 `[VERIFIED: STATE.md + D-GATE-I.4.1 entry]`. `examples/` is
empty `[VERIFIED: ls]`. There is **no Makefile** and the existing `.github/workflows/ci.yml`
has two jobs (lint, test w/ Postgres service) — D-10's `make examples` targets and the
examples CI job are net-new `[VERIFIED: tree inspection]`.

The genuinely new code in this phase is small and enumerable: (1) the hardening wave
(D-14: R1 was-called assertion, fail-closed `isinstance(grant, TokenGrant)` branch, typed
refusal error-code constants, ADK `SequentialAgent` migration, D-IMPL-62 verb note,
key-mgmt doc note); (2) D-15 removal of `ccf hitl decide`; (3) D-16 signed-binding
composition at the authority path; (4) example 03's live-model legs — which need an
**Ollama-speaking `LLMClientProtocol`/transport leg**, the one place a genuinely new
integration exists (the SDK's `LLMClientProtocol` in `src/ccf/llm/__init__.py` is a bare
Protocol, 34 lines, no adapters shipped `[VERIFIED: grep]`); and (5) A3 discharge — replacing
the Claude harness adapter's hand-built `ResultMessage` seam-4 leg with real SDK-driven
execution (`runtime/ccf_runtime/adapters/claude_agent/adapter.py:362-385`).

**Primary recommendation:** Structure the phase as (Wave 0/1) hardening + CLI removal +
signed-binding composition, then examples 00→07 in dependency order with example 03 last
of the "hard three" (03/04/05), then CI/make/README/v0 packaging, then the Phase I gate
(`/gsd-review --phase Phase I --all` → triage → Dave → `D-GATE-I` → tag `v0.1.0`).
Add **zero new Python dependencies** — the live Ollama leg should use the already-pinned
`httpx==0.28.1` against Ollama's HTTP API rather than installing an `ollama` client package.

## User Constraints (from CONTEXT.md)

<user_constraints>

### Locked Decisions

**Example 03 — harness portability depth**
- **D-01:** All three harnesses (Claude Agent SDK, LangGraph, Google ADK) execute example 03.
- **D-02:** Real harness loop machinery in both modes: (a) always-on deterministic base leg —
  real loop code paths over scripted/no-model transports (07-13 pattern: real
  `ClaudeSDKClient` over a custom Transport, real ADK `Runner`), no network, no keys,
  byte-level assertions; plus (b) live-model legs. Discharges advisory A3 (Claude adapter's
  hand-built `ResultMessage` seam-4 leg) — not deferred again.
- **D-03:** Ollama (local, keyless) is the default live provider for all three harnesses;
  Anthropic is an additional gated job requiring `ANTHROPIC_API_KEY`. Two provider axes ×
  three harnesses when fully enabled.
- **D-04:** Under live models the equivalence assertion is structural (same Context Products
  consumed, five-dimension replay records structurally complete, effects through governed
  emission). Byte-equality only in the deterministic leg.

**Domain assignments (D-IMPL-52 rails)**
- **D-05:** Rails are Dave's; per-example assignment within them is planner discretion.
- **D-06:** ≥4 distinct domains across the 8 examples; a domain may serve two examples only
  if non-adjacent example numbers.
- **D-07:** Banking and property-intelligence are both permitted domains. The prohibition is
  Homecams code/config reuse — never the domain. Property-intelligence artifacts authored
  fresh; zero porting from `/home/parkave/homecams_v2`.
- **D-08:** `examples/04-cross-process` carries property-intelligence (assembler → consumer
  across processes). Non-adjacent to banking at 00.
- **D-09:** Every example README carries a one-line domain rationale.

**CI shape & model access**
- **D-10:** GitHub Actions + local make targets running the same commands. Real
  `.github/workflows` pipeline: lints, `mypy --strict`, full suite, all 8 examples against
  reference backends, example 03's deterministic leg — on every push. `make examples` (and
  per-example documented commands) reproduce CI locally.
- **D-11:** Opt-in CI jobs, separate from always-on: Ollama live leg, Anthropic live leg
  (secret-gated), Postgres/Chroma substrate legs.
- **D-12:** Deterministic everywhere except example 03's live legs. Examples 00–02, 04–07
  run keyless and model-free via the injected LLM seam.
- **D-13:** Examples run on SQLite + file-backed ArtifactStore (07 swaps file→MCP, nothing
  else changes). Postgres/Chroma coverage stays in the test suite's dedicated legs.

**Carried obligations & v0 packaging**
- **D-14:** Dedicated hardening wave first: R1 was-called derivation assertions; fail-closed
  `isinstance(grant, TokenGrant)` branch (Codex); typed refusal error-code constants (Ollama
  MEDIUM); ADK `SequentialAgent` deprecation migration; D-IMPL-62 one-line verb status note;
  key-management documentation note. Examples-bind-auth / hardened-HITL-surface obligation
  absorbed into examples 05 and 06 (demonstrated, not just tested).
- **D-15:** `ccf hitl decide` is REMOVED in Phase 8 (not deprecated alias). v0 ships one
  verb: `submit`. Record removal in the decision log when executed.
- **D-16:** Signed-binding composition pulls INTO Phase 8 (N5/R2 residual): compose
  `SignedPrincipalBinding` requiredness at the authority path so non-repudiation is
  demonstrable, per planner design within D-IMPL-21/63/67's contracts.
- **D-17:** v0 declaration = git tag `v0.1.0` + pyproject version bump + top-level README
  (install + quickstart pointers) + `D-GATE-I` logged. No PyPI publish; repo stays private.

### Claude's Discretion
- Per-example domain picks for 01–03, 05–07 within D-06/D-07 rails.
- Example README structure beyond the D-09 rationale line (must cite whitepaper + CLAUDE.md
  sections per §9).
- Wave decomposition; how the hardening wave splits into plans.
- Actions runner topology (Ollama-in-Actions vs self-hosted vs live-leg-local-only) —
  planner researches and proposes; the deterministic pipeline runs on GitHub-hosted runners
  unconditionally.

### Deferred Ideas (OUT OF SCOPE)
- Perf baselines / benchmark harness — post-v0.
- `ccf replay explain` / workflow graph-export CLI verbs — post-v0.
- Homecams-on-SDK rebuild — post-v0 validation exercise (§9).
- PyPI publishing / wheels / CHANGELOG release motion — post-v0.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXAM-01 | `00-quickstart` — minimal fabric, one typed Context Product | Fabric surface fully shipped (D-GATE-I.1); banking fixture shapes in `tests/fixtures/banking/` (ontology, events, controlplane, halflife YAMLs) to mirror — not copy — as example artifacts |
| EXAM-02 | `01-agent-basics` — agent from archetype via artifact + factory, six axes | Agent Factory + `ccf-artifact://` resolution shipped (Phase 5); fixture agent/task/prompt artifacts under `tests/fixtures/banking/agents`, `prompts`, `tasks` show the artifact schema |
| EXAM-03 | `02-skilling` — grant/exercise/revoke; governance check; replay capture | GrantLedger, two-tier governance, `grant_*` audit actions shipped (05-06); replay skill-set capture active (CINV-04) |
| EXAM-04 | `03-harness-portability` — one agent definition under ≥2 (ruled: 3) harnesses, equivalence | Three adapters under `runtime/ccf_runtime/adapters/{adk,claude_agent,langgraph}`; deterministic transport patterns from 07-13 + `tests/conformance/`; A3 (Claude seam-4 `ResultMessage`) must be discharged here; live legs need an Ollama transport (see Standard Stack) |
| EXAM-05 | `04-cross-process` — assembler ↔ consumer via MCP egress + A2A w/ admission verification | `tests/crossproc/` already spawns real subprocesses over loopback with MCP + A2A + admission; property-intelligence artifacts authored fresh (D-07/D-08) |
| EXAM-06 | `05-workflow-hitl` — ApprovalGate + ExceptionEscalation, suspend/resume, replay-recorded action | Payment-release workflow fixtures + engine + gates shipped (Phase 7, gate rows 1–10); example MUST bind `auth=` (`BearerTokenAuth`) and demonstrate the hardened door (D-14, D-GATE-I.4.1 named obligation) |
| EXAM-07 | `06-decision-replay` — exact reproduction from ArtifactStore-resolved versions | `ReplayWriter` over `FileArtifactStore` already driven in crossproc fixtures (I.4 gate §5); D-IMPL-26 hybrid content-hash + versioned-URI addressing; never "latest" (factory refuses `@latest`, gate row 1) |
| EXAM-08 | `07-artifact-store-mcp` — swap file→MCP store, nothing else changes | MCP-backed ArtifactStore shipped Phase 6; conformance suite already parametrizes file vs MCP — the example is a config/wiring swap |
| EXAM-09 | All examples in CI, code + artifacts side by side, README each | New CI examples job + Makefile (D-10); README template per §9 + D-09; domain wording per D-IMPL-52 (supersedes "one coherent neutral domain") |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **No-Hardcoding Rule (§6.4) applies to `/examples`**: no prompt string literals, no
  inline agent/task/workflow definitions, no thresholds/routing constants in example code.
  Example code is thin and generic; artifacts carry everything specific. "An example whose
  code would still run meaningfully with its artifacts deleted has violated the rule."
- **CI lints are blocking, never report-only** (D-07 precedent); the CINV-01..03 lints must
  extend coverage to `/examples` (currently they cover src/runtime — verify `tools/lints`
  scope and widen).
- **Zero harness imports in `/src`** (CINV-02); example code lives in `/examples`, where
  harness imports are permitted (example 03 necessarily imports harness SDKs) — but confirm
  the lint's path scoping does not need an examples carve-out statement.
- **Phase gate protocol §3.1**: `/gsd-review --phase Phase I --all` → triage → present to
  Dave → `D-GATE-I` logged → merge `phase-i5` to `main --no-ff`. Cross-AI reviewer creds:
  `CODEX_API_KEY` (not `OPENAI_API_KEY`), `CURSOR_API_KEY`, from `/home/parkave/homecams_v2/.env`.
- **Branch:** `phase-i5` per CONTEXT.md (CLAUDE.md §2.2 pattern). Note `.planning/config.json`
  has `branching_strategy: "none"` — the project convention (phase branches) wins per
  established practice in phases 4–7.
- **Docstrings cite whitepaper sections**; example READMEs cite whitepaper + CLAUDE.md
  sections (§9).
- **Commit at deliverable boundaries**; no force-push to `main`; `main` far ahead of
  `origin/main` and Dave has not authorized a push `[VERIFIED: STATE.md]`.
- Every temptation to inline a definition = D-IMPL-28 artifacts (YAML + Pydantic v2 schemas
  + Jinja2 prompt URIs, already ruled and shipped).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Example runner code | `/examples/NN-*/` (thin scripts) | — | Adoption contract; never library code |
| Example domain values | `/examples/NN-*/artifacts/` (YAML/Jinja2) | — | No-Hardcoding Rule §6.4 |
| Hardening-wave fixes | `/src` (hitl, errors) + `/runtime` (http_api, orchestration/adk) | `/tests` | Mechanism changes; TDD like every prior wave |
| Ollama live-leg transport | `/examples/03-*/` (or `/runtime` if reusable) | — | Provider wiring is example/deployment scope; keep `/src` provider-free (see Open Question 2) |
| CI examples job + opt-in jobs | `.github/workflows/ci.yml` (+ possibly a second workflow file) | Makefile | D-10/D-11 |
| Make targets | `Makefile` (new, repo root) | — | Same commands as CI, locally |
| v0 packaging | `pyproject.toml` version, top-level `README.md`, git tag | `docs/DECISIONS.md` (D-GATE-I) | D-17 |

## Standard Stack

### Core — no new runtime dependencies recommended

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| (entire pinned set) | per `pyproject.toml` | Everything the examples exercise | [VERIFIED: pyproject.toml on main] — pydantic 2.13.4, mcp 1.28.1, a2a-sdk 1.1.2, fastapi 0.140.0, httpx 0.28.1, uvicorn 0.51.0, joserfc 1.7.4, etc. |
| google-adk | 2.5.0 (extra `adk`) | Example 03 ADK leg | [VERIFIED] — note `SequentialAgent` deprecation migration is D-14 scope |
| claude-agent-sdk | 0.2.128 (extra `claude-agent`) | Example 03 Claude leg + A3 discharge | [VERIFIED] |
| langgraph | 1.2.9 (extra `langgraph`) | Example 03 LangGraph leg | [VERIFIED] |
| `make` (GNU) | system | D-10 local targets | [VERIFIED: standard on ubuntu runners + dev box] |

**Ollama access:** use the already-pinned `httpx` against Ollama's native HTTP API
(`POST /api/chat` at `http://localhost:11434`) behind the existing `LLMClientProtocol` /
harness-specific model bindings — do **not** add the `ollama` PyPI client or
`langchain-ollama` unless a harness leg genuinely cannot be pointed at Ollama otherwise.
Harness-native routes exist: LangGraph accepts any model callable; ADK supports
LiteLLM-style model strings but that would add a dependency — prefer wiring each harness's
model seam to a thin httpx-backed client authored in the example (thin code, provider URL
from environment/config, not a constant). `[ASSUMED]` — per-harness live-model binding
specifics need verification at plan time against each SDK's docs (see Open Question 2).

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx→Ollama native API | `ollama` PyPI package | New dependency + slop-audit burden for a thin HTTP wrapper we already have the client for |
| One workflow file | Separate `examples.yml`, `live.yml` workflows | Separate files make D-11's opt-in jobs (`workflow_dispatch` / secret-gated) cleaner; recommend: keep `ci.yml`, add an `examples` job to it, add `live-legs.yml` with `workflow_dispatch` + `if: secrets` gating |

## Package Legitimacy Audit

**No new packages are recommended for installation in this phase.** All examples run on
the existing pinned dependency set (audited in 04/06/07-RESEARCH per the gate documents).
slopcheck was therefore not run. If the planner elects to add an Ollama client package
after all (against the recommendation above), that install must be gated behind a
`checkpoint:human-verify` task and slopcheck-audited first.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture (per example, and CI)

```
developer / CI
   │  make examples  /  make example-NN  (one documented command each)
   ▼
examples/NN-name/
   ├── run.py (or run.sh)      thin generic driver
   ├── artifacts/              agent/task/workflow/policy/ontology/prompt YAML+Jinja2
   ├── README.md               what/why, whitepaper+CLAUDE.md citations, D-09 rationale
   └── (03 only) legs/         deterministic transports + live-leg wiring
        │
        ▼
   ccf / ccf_runtime (installed, unmodified)  ── SQLite + FileArtifactStore (D-13)
        │                                        (07 swaps → MCP ArtifactStore)
        ▼
   assertions in the example itself (exit 0 = demonstrated; CI treats nonzero as red)
```

CI: existing `lint` + `test` jobs unchanged; new always-on `examples` job runs
`make examples` (00–07 + 03 deterministic leg); opt-in jobs (`workflow_dispatch` and/or
secret-gated): `examples-live-ollama`, `examples-live-anthropic`, existing
postgres/chroma legs stay in `test`.

### Pattern 1: Examples are asserted programs, not demos
**What:** Each `run.py` ends in explicit assertions (byte-equality where deterministic,
structural under live models per D-04) and exits nonzero on failure — CI needs no
per-example test harness; "a broken example is a broken build" (§9).
**Source:** CLAUDE.md §9 discipline + I.4 gate's exit-code precedent (CLI 0/1/2).

### Pattern 2: Mirror fixture shapes, never copy fixtures
**What:** `tests/fixtures/banking/` (ontology.yaml, events.yaml, controlplane.yaml,
halflife.yaml, agents/, prompts/, skills/, tasks/, workflows/, hitl.yaml, a2a.yaml,
harnesses.yaml `[VERIFIED: ls]`) shows every artifact schema the factories accept. Example 00
"may draw on the same shape but examples ship their own artifacts" (CONTEXT.md). Author
fresh YAML per example domain; the schemas (D-IMPL-28) are the reusable part.

### Pattern 3: Deterministic harness legs via the 07-13 transports
**What:** Example 03's base leg reuses the proven patterns: real `ClaudeSDKClient` over the
SDK's public custom `Transport` with a scripted in-process wire; real ADK `Runner` with a
no-model agent; LangGraph graph with injected callables. See
`tests/conformance/test_orchestration.py` (25/25, factory-parametrized, zero shared-body
edits) and the 07-13 SUMMARY. `[VERIFIED: I.4 gate rows 12–13]`
**A3 discharge:** the *adapter's* seam-4 `execution()` currently accepts a hand-built
`ResultMessage` (`adapters/claude_agent/adapter.py:385 isinstance` check). Discharge =
example 03 (and/or a supporting test) drives a real SDK-produced `ResultMessage` through
seam 4 — the orchestration leg's real-session machinery shows how, but A3 lives on the
harness-adapter seam, a different surface `[VERIFIED: I.4 gate §5]`.

### Pattern 4: Domain assignment proposal (planner discretion within D-06/D-07)
A defensible assignment satisfying ≥4 domains, no adjacent repeats:
00 banking (locked) · 01 field-service/logistics · 02 healthcare-adjacent clinical-trials
ops or publishing · 03 logistics or e-commerce · 04 property-intelligence (locked) ·
05 banking (non-adjacent to 00? — 05 vs 00 are non-adjacent, permitted; banking fits HITL
approval realism) · 06 same decision replayed → must share 05's domain *artifacts*? No —
06 can replay its own prior decision; pick a distinct domain (e.g., energy/grid ops) ·
07 any (store swap is domain-light; reuse a prior non-adjacent domain). Planner finalizes;
each README carries the D-09 rationale line. `[ASSUMED: proposal only]`

### Anti-Patterns to Avoid
- **Example code that would run with artifacts deleted** — §6.4 violation, explicit test in §9.
- **Copying test fixtures into examples/** — CONTEXT.md forbids; and D-04 (Phase 7) kept
  `examples/` untouched precisely to keep proofs as fixtures and examples as fresh authoring.
- **Porting anything from `/home/parkave/homecams_v2`** for example 04 — domain permitted,
  code/config reuse forbidden (D-07).
- **Making the examples CI job `continue-on-error`** — the D-07 (Phase 4) precedent: a
  non-blocking step hiding a gap is worse than the gap.
- **Byte-equality assertions in live legs** — D-04 restricts them to the deterministic leg.
- **A `latest` reference anywhere in example 06** — the factory refuses `@latest` (gate row 1);
  replay resolves exact versions (D-IMPL-26).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-process spawn/loopback wiring (ex. 04) | New subprocess plumbing | Patterns in `tests/crossproc/` (real subprocesses, ephemeral ports via uvicorn `sockets=[...]`) | Proven under the crossproc marker; admission verification already driven there |
| Ollama chat client | New HTTP client abstraction | `httpx` (pinned) against `/api/chat` | One pinned client already in the tree |
| Example test harness | pytest wrappers per example | Exit-code assertions inside each example + one CI step | §9: examples ARE the check |
| OpenAPI/docs for README | Hand-written API tables | Point at the generated OpenAPI + `ccf` CLI help | Spec-drift hand-roll |
| Store-swap logic (ex. 07) | Conditional store code | The existing conformance parametrization pattern (file vs MCP) — swap is pure wiring/config | ArtifactStoreProtocol is the seam |

## Common Pitfalls

### Pitfall 1: Lint scope gap over `/examples`
CINV-01 (No-Hardcoding) is CLAUDE.md-mandated for `/examples` too, but `tools.lints` was
built when `examples/` was empty. **Verify and extend lint path coverage to `examples/`**
early (and decide the CINV-02 posture: harness imports are *legitimate* in example 03 code —
the lint must not fire there, or must scope to `/src` only as it does today). Warning sign:
lints stay green while an example inlines a prompt. `[VERIFIED: examples/ empty; lint scope needs inspection at plan time]`

### Pitfall 2: The local Ollama is a cloud-proxied model
`http://localhost:11434` currently serves `gpt-oss:120b-cloud` with
`remote_host: https://ollama.com:443` `[VERIFIED: live probe]` — i.e., "local, keyless"
Ollama here actually relays to Ollama's cloud. That's fine for a dev live leg (still
keyless from the client), but (a) it is *not* offline, and (b) it will not exist on a
GitHub-hosted runner. For Ollama-in-Actions, a genuinely local small model (e.g.,
`qwen3:0.6b`-class) must be pulled in-job; ubuntu-latest runners are CPU-only with ~16GB
RAM, so only small models are feasible and runs are slow `[ASSUMED — verify model pull
size/time in a spike]`. Recommendation to carry into the plan: **deterministic pipeline on
GitHub-hosted runners unconditionally (required); Ollama live leg as `workflow_dispatch`
opt-in that installs Ollama and pulls a small model, with a documented local-run path as
the primary way to exercise it; Anthropic leg secret-gated with
`if: ${{ secrets.ANTHROPIC_API_KEY }}`-style guard.** This satisfies the D-10/D-11 letter
without a self-hosted runner.

### Pitfall 3: Example 05/06 must *bind auth*, not just run
D-GATE-I.4.1 names the obligation: "examples bind `auth=` and demonstrate the hardened
surface." A workflow-HITL example that uses the unauthenticated default posture silently
regresses the R4/N2 remainder. The example must construct `create_app(auth=BearerTokenAuth(...))`
(or the MCP door), submit with a verified `TokenGrant`, and show the audited principal
derived via `principal_from_token_grant` — plus D-16's composed `SignedPrincipalBinding`
requiredness at the authority path.

### Pitfall 4: D-15 removal ripples
Removing `ccf hitl decide` touches: CLI arg parsing, `tests/cli/test_cli.py` (the
deprecation test from 07-19 flips to an absence test), any docs/gate references, and the
DECISIONS.md log entry ("record the removal in the decision log when executed"). Grep for
`decide` across the tree before declaring done.

### Pitfall 5: ADK `SequentialAgent` migration scope
Only `runtime/ccf_runtime/orchestration/adk/driver.py` uses it `[VERIFIED: grep]`. The
deferred-items note says migration is mechanical ("sub-agents are plain `BaseAgent`
subclasses") but it was deferred "to the next pin bump" — D-14 pulls it in *without* a pin
bump, meaning migrate to ADK 2.5.0's non-deprecated API (`Workflow` replacement was "cannot
yet be…" per the note — read the full deferred-items entry; if the replacement API is
unusable at 2.5.0, the honest outcome may be suppressing/pinning the deprecation with a
recorded rationale rather than a broken migration). `[ASSUMED — verify ADK 2.5.0 surface at plan time]`

### Pitfall 6: Version bump + tag ordering at the gate
D-17's `v0.1.0` tag comes *after* Dave approves and `D-GATE-I` is logged and `phase-i5`
merges — tagging the phase branch pre-approval would violate §3.1's ordering. pyproject is
currently `0.1.0.dev0` `[VERIFIED]`; bump to `0.1.0` in the packaging plan, tag on `main`
post-merge.

### Pitfall 7: Editable-install staleness
The I.4 gate notes `pip install -e .` was deferred from a shared-venv worktree; `.venv/bin/ccf`
may be stale/absent. Examples that shell out to `ccf` should either re-install editable at
phase start or invoke `python -m ccf_runtime.cli.main` — pick one and make the Makefile do it.

## Runtime State Inventory

Not a rename/refactor phase in the migration sense, but two removal/migration items exist:

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| CLI verbs | `ccf hitl decide` (deprecated alias from 07-19) | D-15: remove; flip deprecation test; DECISIONS.md entry |
| Deprecated API use | ADK `SequentialAgent` in `orchestration/adk/driver.py` | D-14 migration (see Pitfall 5) |
| Stored data / services / OS state / secrets | None — verified: examples are new; no datastore renames; CI secrets (`ANTHROPIC_API_KEY`) are *added*, never renamed | none |
| Build artifacts | `ccf.egg-info` at repo root; possibly stale editable install | reinstall `pip install -e ".[dev]"` at phase start |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python venv `.venv` | everything | ✓ | 3.12 | — |
| All three harness extras | example 03 | ✓ (dev extra composes them; 1315-suite ran `CCF_REQUIRE_HARNESSES=1`) | adk 2.5.0 / claude-agent-sdk 0.2.128 / langgraph 1.2.9 | — |
| Ollama local | 03 live leg (default provider) | ✓ | serving `gpt-oss:120b-cloud` (cloud-relayed — Pitfall 2) | local small model pull; or Anthropic leg |
| `ANTHROPIC_API_KEY` | 03 Anthropic leg | unknown at research time | — | leg is opt-in by design (D-03) |
| GitHub Actions | D-10 pipeline | ✓ (ci.yml exists, repo on GitHub) | — | note: `main` ahead of `origin/main`, push unauthorized — CI verification on the phase branch requires Dave to authorize pushes, or CI-equivalence is proven locally via the make targets until then (**flag for planner**) |
| `make` | D-10 | ✓ (linux) | — | — |
| Codex/Cursor CLIs + keys | §3.1 gate review | ✓ per memory (keys in homecams .env) | — | — |
| Postgres/Chroma | test-suite legs only (D-13: not in examples) | CI service container / extras | — | — |

**Missing dependencies with no fallback:** none blocking. The push-authorization question
is the one real environmental gate on "runs in CI" evidence — surface it to Dave early.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + hypothesis 6.161.5 (pinned dev extras) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]`, testpaths `["tests"]` |
| Quick run command | `pytest tests -q -m "not postgres and not chroma"` |
| Full suite command | `CCF_REQUIRE_HARNESSES=1 PYTHONPATH=src:runtime .venv/bin/python -m pytest -q && .venv/bin/python -m mypy && PYTHONPATH=src:runtime .venv/bin/python -m tools.lints --all` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXAM-01..08 | each example runs, asserts, exits 0 | e2e (the example IS the test) | `make example-00` … `make example-07` | ❌ Wave-per-example |
| EXAM-04 (deterministic leg) | 3-harness byte-level equivalence | e2e | `make example-03` (deterministic) | ❌ |
| EXAM-04 (live legs) | structural equivalence, Ollama/Anthropic | e2e, opt-in | `make example-03-live-ollama` / `-anthropic` | ❌ manual/opt-in — justified: model access (D-11) |
| EXAM-09 | CI green incl. examples job | CI | push → Actions (or local `make ci`) | ❌ ci.yml edit |
| D-14 hardening items | R1 was-called; fail-closed branch; error codes | unit | `pytest tests/http_api tests/hitl tests/cli -q` | partially ✅ (tests exist to extend) |
| D-15 | `decide` absent | unit | `pytest tests/cli -q` | ✅ flip existing deprecation test |
| D-16 | signed-binding required at authority path | unit/integration | `pytest tests/hitl -q` | ❌ new tests, TDD |
| CINV-01..03 over examples | lints cover `/examples` | lint | `python -m tools.lints --all` | ⚠ verify scope; extend |
| Gate | full sweep + `/gsd-review --phase Phase I --all` | phase gate | commands above | protocol |

### Sampling Rate
- **Per task commit:** quick suite + `tools.lints --all`
- **Per wave merge:** full sweep (harnesses mandatory, mypy, lints) + `make examples` for
  examples built so far
- **Phase gate:** full sweep + all 8 examples + deterministic 03 leg green before `/gsd-review`

### Wave 0 Gaps
- [ ] `Makefile` with `examples`, `example-NN`, `ci` targets (D-10)
- [ ] `tools/lints` scope check/extension over `examples/`
- [ ] `.github/workflows` examples job + opt-in live workflow
- [ ] `pip install -e ".[dev]"` refresh (stale editable install)

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (examples 05/06) | `BearerTokenAuth` + `TokenGrant` (shipped, D-GATE-I.4.1) — examples bind it, never invent auth |
| V3 Session Management | no (stateless bearer posture) | — |
| V4 Access Control | yes | Policy regimes / grant governance (shipped); demonstrated in example 02 |
| V5 Input Validation | yes | Pydantic v2 `extra=forbid` at every boundary (project invariant) |
| V6 Cryptography | yes (D-16) | `SignedPrincipalBinding` on joserfc JWS (D-IMPL-15 machinery) — never hand-roll signing |

### Known Threat Patterns for this phase
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Principal spoofing at HITL doors | Spoofing | `principal_from_token_grant` + typed 403 on subject conflict (shipped); D-16 adds signed-binding requiredness |
| Secrets in tree (Anthropic key, review keys) | Info disclosure | CI secrets only; keys sourced at runtime from homecams `.env`, never committed (I.4 gate §1.2 discipline) |
| Fail-open on non-`TokenGrant` grant object | Elevation | D-14 fail-closed branch (Codex finding) — 403/500, never fall back to caller principal |
| Refusal-string parsing fragility | — | D-14 typed error-code constants |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| "One coherent neutral domain" (§9 pre-amendment, ROADMAP crit. 1, EXAM-09 wording) | D-IMPL-52 horizontal mix, 00 banking | 2026-07-25 | Gate verifies against amended policy; REQUIREMENTS.md EXAM-09's "one coherent neutral domain" tail is stale wording — verify against D-IMPL-52, don't implement it |
| `ccf hitl decide` (then deprecated alias) | `submit` only | D-15, this phase | removal + log entry |
| ADK `SequentialAgent` | non-deprecated ADK API | D-14, this phase | driver migration |
| Caller-supplied principals | grant-derived when auth bound (D-IMPL-67) + D-16 signed-binding composition | 7.1/7.2 → this phase | examples demonstrate the hardened path |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Each harness's model seam can be pointed at Ollama via a thin httpx client without new deps | Standard Stack | May need `litellm`/`langchain-ollama`/`ollama` pkgs → slopcheck + checkpoint gate before install |
| A2 | Small-model Ollama is feasible on GitHub-hosted runners (CPU, ~16GB) for an opt-in job | Pitfall 2 | Live leg becomes local-only/self-hosted — CONTEXT explicitly allows planner to propose this |
| A3 | ADK 2.5.0 offers a usable non-deprecated replacement for `SequentialAgent` | Pitfall 5 | Recorded-rationale deferral of the migration instead |
| A4 | Domain-assignment proposal (Pattern 4) is acceptable within D-06/D-07 | Patterns | Planner reassigns; rails unchanged |
| A5 | Pushing `phase-i5` to origin for real Actions runs will be authorized | Environment | CI evidence proven via local `make ci` equivalence until authorized |

## Open Questions

1. **Push authorization for CI evidence.** D-10 requires a real Actions pipeline running on
   every push, but `main` is ahead of `origin/main` and Dave hasn't authorized pushes.
   Recommendation: raise at plan presentation; interim evidence = local make-target parity.
2. **Where does the Ollama client live?** `/examples/03` keeps `/src`/`/runtime`
   provider-free (cleanest vs. general-purposeness); but if both live legs share it, a small
   `runtime` helper behind `LLMClientProtocol` may be justified. Recommendation: author it
   in example 03's directory first; promote only if a second consumer appears.
3. **CINV-02 posture for `/examples`.** Harness imports are required in example 03. The lint
   currently guards `/src` (+ runtime carve-outs). Recommendation: examples are exempt from
   CINV-02 by design (CLAUDE.md limits the invariant to core), but CINV-01 must extend to
   examples — state both explicitly in the lint config and its tests.
4. **D-16 design shape.** "Compose `SignedPrincipalBinding` requiredness at the authority
   path" is planner-designed within D-IMPL-21/63/67 contracts. The likely seam: transport
   enqueue/resolve accepts an optional-but-policy-requirable signed binding; when the policy
   (Control Plane value, never a code constant) requires it, an unsigned submission is a
   typed refusal. Needs a small design note in the plan, not a new D-IMPL (it accelerates a
   named residual) — unless the contract question exceeds those rulings, then D-IMPL entry + stop.

## Sources

### Primary (HIGH confidence — live tree/docs verified this session)
- `docs/PHASE_I4_GATE.md` (full read) — as-built surface, §5 handoff, A3, D-IMPL-62..67
- `.planning/phases/08-.../08-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md`
- `docs/DECISIONS.md` — D-IMPL-52, D-IMPL-66/67, D-GATE-I.4.1 (grep-verified excerpts)
- `pyproject.toml`, `.github/workflows/ci.yml`, `tools/`, `tests/fixtures/banking/`,
  `runtime/ccf_runtime/{adapters,orchestration}`, `src/ccf/llm/__init__.py` (inspected)
- `.planning/phases/07-.../07-REVIEWS.md` — R1/R2/N5, fail-closed branch, error-code findings
- Live probe: `curl http://localhost:11434/api/tags`

### Secondary (MEDIUM)
- `deferred-items.md` (Phase 7) — SequentialAgent note

### Tertiary (LOW — flagged [ASSUMED])
- Ollama-in-Actions feasibility; harness live-model binding surfaces (verify at plan time
  via Context7/official docs for google-adk, claude-agent-sdk, langgraph)

## Metadata

**Confidence breakdown:**
- Shipped-surface inventory: HIGH — read from the gate doc + tree, not assumed
- Examples structure/discipline: HIGH — CLAUDE.md §9 + CONTEXT.md are prescriptive
- Live-leg wiring (Ollama × 3 harnesses): MEDIUM-LOW — the only genuinely novel integration; A1/A2 flagged
- Hardening-wave items: HIGH — each traced to a named review finding with file/line anchors

**Research date:** 2026-07-30
**Valid until:** ~2026-08-30 (internal surfaces stable; harness SDK pins frozen)
