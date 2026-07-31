# Phase 8: Phase I.5 — Examples Suite & Full CI Verification - Context

**Gathered:** 2026-07-30
**Status:** Ready for planning

<domain>
## Phase Boundary

The eight-example adoption contract (`examples/00-quickstart` through
`examples/07-artifact-store-mcp`, per CLAUDE.md §9) runs end-to-end in CI with
a single documented command each, against the reference backends; every
CI-enforced invariant is verified across `/src`, `/runtime`, and `/examples`;
the carried Phase 7 hardening obligations land; and the phase ends at the
Phase I gate (`/gsd-review --phase Phase I --all` → triage → Dave approval →
`D-GATE-I`) — the v0 declaration. Branch `phase-i5`.

**Superseded roadmap wording:** ROADMAP.md Phase 8 criterion 1 still says "one
coherent neutral domain (non-banking…)". That was replaced by **D-IMPL-52**
(Dave, 2026-07-25): a horizontal mix of domains, `00-quickstart` banking. The
gate verifies against the amended policy, not the stale sentence.

**Not in this phase:** the Homecams-on-SDK rebuild (post-v0, §9); PyPI
publishing (repo stays private); perf baselines and replay-explorer /
workflow-graph-export CLI ideas (post-v0 backlog); mobile/chat/web UX.

</domain>

<decisions>
## Implementation Decisions

### Example 03 — harness portability depth
- **D-01:** **All three harnesses** (Claude Agent SDK, LangGraph, Google ADK)
  execute example 03. The roadmap criterion's "two harnesses" is a floor, not
  a ceiling; D-IMPL-24 already named three example-03 variants.
- **D-02:** Loop depth is **real harness loop machinery** in both modes:
  (a) an always-on **deterministic base leg** — real loop code paths over
  scripted/no-model transports (the 07-13 orchestration pattern: real
  `ClaudeSDKClient` over a custom Transport, real ADK `Runner`), no network,
  no keys, byte-level assertions; plus (b) **live-model legs**. This
  discharges advisory **A3** (the Claude adapter's hand-built `ResultMessage`
  seam-4 leg) — two gates deferred it here; it is not deferred again.
- **D-03:** Live-leg provider mapping: **Ollama (local, keyless) is the
  default live provider for all three harnesses**; **Anthropic is an
  additional gated job** requiring `ANTHROPIC_API_KEY`. Fully enabled that is
  two provider axes × three harnesses.
- **D-04:** Under live models the equivalence assertion is **structural**:
  same Context Products consumed, five-dimension replay records structurally
  complete, effects captured through governed emission. Byte-equality
  assertions live only in the deterministic leg.

### Domain assignments (D-IMPL-52 rails)
- **D-05:** Constraint-based assignment: these rails are Dave's; per-example
  assignment within them is planner discretion.
- **D-06:** **≥4 distinct domains** across the 8 examples; a domain may serve
  two examples only if they are non-adjacent example numbers.
- **D-07:** **Banking and property-intelligence are both permitted example
  domains.** The prohibition is **Homecams code/config reuse — never the
  domain itself**. Any property-intelligence artifacts (ontology, fixtures,
  policy bundles, λ_c tables) are authored fresh under the No-Hardcoding Rule;
  zero porting from `/home/parkave/homecams_v2`.
- **D-08:** **`examples/04-cross-process` carries property-intelligence**
  (assembler agent producing situational Context Products in one process,
  consumer in another — mirrors Homecams' shape and proves the SDK covers that
  ground with none of its code). Non-adjacent to banking at 00.
- **D-09:** Every example README carries a **one-line domain rationale**: the
  domain, why it fits the mechanism demonstrated, and a pointer that all
  domain values live in definition artifacts.

### CI shape & model access
- **D-10:** **GitHub Actions + local make targets running the same
  commands.** A real `.github/workflows` pipeline: lints, `mypy --strict`,
  full test suite, all 8 examples against reference backends, and example
  03's deterministic leg — on every push. `make examples` (and per-example
  documented commands) reproduce CI locally.
- **D-11:** **Opt-in CI jobs**, separate from the always-on pipeline: the
  Ollama live leg, the Anthropic live leg (secret-gated), and the
  Postgres/Chroma substrate legs.
- **D-12:** **Deterministic everywhere except example 03's live legs.**
  Examples 00–02 and 04–07 run keyless and model-free via the injected LLM
  seam (Algorithmic ⇄ Semantic alternation holds either way).
- **D-13:** Examples run on **SQLite + file-backed ArtifactStore** (example
  07 swaps file-backed → MCP-backed per its charter, nothing else changes).
  Postgres/Chroma coverage remains in the test suite's dedicated legs, not in
  examples.

### Carried obligations & v0 packaging
- **D-14:** **Dedicated hardening wave first, examples absorb the rest.**
  Wave-1 code items before example authoring: R1 was-called derivation
  assertions; the fail-closed `isinstance(grant, TokenGrant)` branch (Codex);
  typed refusal error-code constants (Ollama MEDIUM); ADK `SequentialAgent`
  deprecation migration; D-IMPL-62 one-line verb status note; key-management
  documentation note. The **examples-bind-auth / hardened-HITL-surface
  obligation is absorbed into the HITL-touching examples (05, 06)** where it
  is demonstrated, not just tested.
- **D-15:** **`ccf hitl decide` is REMOVED in Phase 8** (not kept as
  deprecated alias). v0 ships one verb: `submit`. Record the removal in the
  decision log when executed; docs and examples use `submit` exclusively.
- **D-16:** **Signed-binding composition pulls INTO Phase 8** (accelerating
  the N5/R2 residual): compose `SignedPrincipalBinding` requiredness at the
  authority path so non-repudiation is demonstrable, per planner design
  within D-IMPL-21/63/67's contracts. Perf baselines and CLI feature ideas
  stay post-v0.
- **D-17:** **v0 declaration = git tag `v0.1.0` + pyproject version bump +
  top-level README** (install + quickstart pointers into the examples) +
  `D-GATE-I` logged. No PyPI publish; repo stays private.

### Claude's Discretion
- Per-example domain picks for 01–03, 05–07 within the D-06/D-07 rails.
- Example README structure beyond the D-09 rationale line (must still cite
  whitepaper + CLAUDE.md sections per §9).
- Wave decomposition; how the hardening wave splits into plans.
- Actions runner topology (Ollama-in-Actions feasibility vs self-hosted
  runner vs live-leg-local-only) — planner researches and proposes; the
  requirement is that the deterministic pipeline runs on GitHub-hosted
  runners unconditionally.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `CLAUDE.md` §9 — the examples-suite charter (per-example scope, discipline,
  code-and-artifacts-side-by-side, README requirements) and §3.1 (Phase I
  review protocol ending in `D-GATE-I`).
- `.planning/ROADMAP.md` — Phase 8 section (criteria 2–5 verbatim; criterion
  1's domain wording superseded by D-IMPL-52).
- `docs/DECISIONS.md` — D-IMPL-52 (domain mix), D-IMPL-24/60 (three
  harnesses / three orchestrator legs), D-IMPL-62..67 (HITL identity and door
  composition contracts the examples must respect), D-GATE-I.4 and
  D-GATE-I.4.1 (the named Phase 8 obligations list), D-IMPL-09 (LLM access
  seam for live legs), D-IMPL-26/27 (artifact addressing for example 06's
  exact-version replay).
- `docs/PHASE_I4_GATE.md` — as-built state of every surface the examples
  exercise, incl. §8 addendum.
- `.planning/phases/07-phase-i-4-orchestration-hitl-experience/07-REVIEWS.md`
  — rounds 2–3 findings register (R1/R2/N5, fail-closed branch, error codes)
  that the hardening wave closes.
- `docs/CCF_Whitepaper_1-2.md` — cited per-example in READMEs per §9.

</canonical_refs>

<code_context>
## Reusable Assets

- **Banking fixtures** (`tests/fixtures/banking/`) — ontology, skills,
  grants, workflow YAMLs; example 00 may draw on the same *shape* but
  examples ship their own artifacts (examples are not test fixtures).
- **Deterministic harness transports** — 07-13's Claude custom-Transport and
  ADK `Runner` no-model patterns; `tests/conformance/test_orchestration.py`
  factory parametrization; the three adapters under
  `runtime/ccf_runtime/adapters/`.
- **Auth + identity surface** — `BearerTokenAuth` (`http_api/auth.py`),
  `principal_from_token_grant` (`identity_binding.py`),
  `SignedPrincipalBinding` (`src/ccf/hitl/identity_binding.py`), the composed
  doors (`routes/hitl.py`, `mcp/hitl_server.py`) — examples 05/06 bind these.
- **MCP-backed ArtifactStore** (Phase 6 deliverable) — example 07's swap
  target; conformance suite already parametrizes file vs MCP.
- **Local Ollama** at `http://localhost:11434` (currently serving
  `gpt-oss:120b-cloud`) — the default live-leg provider.
- Suite baseline at phase start: 1315 passed / 0 skipped, mypy --strict
  clean (155 files), `tools.lints --all` exit 0, on `main` (0a7c7b4).

</code_context>

<deferred>
## Deferred Ideas

- Perf baselines / benchmark harness (Ollama round-2 suggestion) — post-v0.
- `ccf replay explain` / workflow graph-export CLI verbs (Gemini round-2
  suggestions) — post-v0.
- Homecams-on-SDK rebuild — post-v0 validation exercise (§9).
- PyPI publishing / wheels / CHANGELOG release motion — post-v0.

</deferred>
