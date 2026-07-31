# Phase 8: Phase I.5 — Examples Suite & Full CI Verification - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-30
**Phase:** 08-phase-i-5-examples-suite-full-ci-verification
**Areas discussed:** Example 03 portability depth, Domain assignments, CI shape & model access, Carried-obligations placement

---

## Example 03 portability depth

| Option | Description | Selected |
|--------|-------------|----------|
| All three harnesses | Criterion's "two" is a floor; matches D-IMPL-24 | ✓ |
| Two, third as stretch | Meet criterion with most-different pair | |
| Exactly two | Minimum, defer third post-v0 | |

| Option | Description | Selected |
|--------|-------------|----------|
| Real loop, no-model transport | Deterministic real-loop base only | |
| Real model calls, gated job | Adds live legs on top of the deterministic base | ✓ |
| Seam-level only | Push A3 a third time | |

| Option | Description | Selected |
|--------|-------------|----------|
| Structural equivalence | Governed surfaces asserted; no byte-equality under live models | ✓ |
| Replay-dim byte-equality where possible | dims 1/2/4 byte-equal | |
| Smoke only | Live legs prove run-through only | |

**Provider question:** options were Anthropic-for-all / native defaults / you-decide. **User free-text: "Anthropic and Ollama with local LLM"** — both providers.

| Option | Description | Selected |
|--------|-------------|----------|
| Ollama default, Anthropic gated | All 3 harnesses on local Ollama; Anthropic as gated extra job | ✓ |
| Anthropic for Claude SDK, Ollama for rest | Provider axis varies with harness axis | |
| All three on both providers, always | Six live legs every run | |

---

## Domain assignments

| Option | Description | Selected |
|--------|-------------|----------|
| User sets constraints, planner assigns | Rails from Dave, assignment by planner | ✓ |
| Pick them now | 7 picks in-discussion | |
| Full planner discretion | Only D-IMPL-52's rules | |

| Option | Description | Selected |
|--------|-------------|----------|
| ≥4 distinct, repeats OK non-adjacent | Balance authoring cost vs visible generality | ✓ |
| Every example distinct (8 domains) | Max proof, max cost | |
| 3 domains in blocks | Cheaper, weaker mix | |

**Include/exclude question:** **User free-text: "Banking and Property Intelligence is fine for examples but not for code reuse."** — both domains permitted; prohibition is Homecams code/config reuse only.

| Option | Description | Selected |
|--------|-------------|----------|
| 04-cross-process carries property-intelligence | Mirrors Homecams' assembler→consumer shape, zero ported code | ✓ |
| 06-decision-replay | Replay a prior PI decision | |
| Planner picks | Lowest fixture cost | |

| Option | Description | Selected |
|--------|-------------|----------|
| Domain rationale line in every README | Domain + why + values-in-artifacts pointer | ✓ |
| Domain label only | | |
| No convention | | |

---

## CI shape & model access

| Option | Description | Selected |
|--------|-------------|----------|
| GitHub Actions + local make | Real workflows + same commands locally; live/backends opt-in | ✓ |
| Local-only harness for v0 | Defer Actions | |
| GitHub Actions minimal | Lints+tests only in Actions | |

| Option | Description | Selected |
|--------|-------------|----------|
| Deterministic everywhere else | Only example 03 has live legs | ✓ |
| Live-capable everywhere, Ollama default | Every semantic stage live-capable | |
| You decide | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Examples on SQLite; backend legs in tests | Zero-infra examples; substrate coverage stays in test suite | ✓ |
| One example runs Postgres too | Opt-in variant on one example | |
| All examples dual-run | | |

---

## Carried-obligations placement

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated wave 1 + examples absorb the rest | Code items early; auth obligation into examples 05/06 | ✓ |
| Fold everything into example plans | | |
| Defer code items past v0 | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Keep decide through v0, remove v1 | | |
| Remove in Phase 8 | v0 ships one verb: submit | ✓ |
| Keep indefinitely | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Close v0 without deferred items | | |
| Pull signed-binding composition in | N5/R2 non-repudiation composition lands in Phase 8 | ✓ |
| Decide at planning | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Tag + version + README | v0.1.0 tag, pyproject bump, top-level README, D-GATE-I | ✓ |
| Gate log only | | |
| Full release motion | Wheels/CHANGELOG | |

---

## Deferred Ideas

- Perf baselines / benchmark harness — post-v0
- `ccf replay explain` / workflow graph-export verbs — post-v0
- Homecams-on-SDK rebuild — post-v0 (§9)
- PyPI publish / wheels / CHANGELOG — post-v0

## Claude's Discretion

- Per-example domain picks (01–03, 05–07) within rails
- README structure beyond the rationale line
- Wave decomposition of the hardening wave
- Actions runner topology for the Ollama live leg (research at planning)
