# Phase 4: Phase I.1 — Fabric Core - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-25
**Phase:** 4-Phase I.1 — Fabric Core
**Areas discussed:** Build sequencing, CI lint mechanics, Backend & infra logistics, Test strategy depth

---

## Build sequencing

| Option | Description | Selected |
|--------|-------------|----------|
| Vertical slice first | Thin L1→L6 path early, then widen | ✓ |
| Contracts first | All models/Protocols before behavior | |
| Layer-by-layer bottom-up | L1 complete, then L2, … | |

**Slice proof point:**

| Option | Description | Selected |
|--------|-------------|----------|
| Proto-quickstart | Private fixture precursor of examples/00 | ✓ |
| Pure test harness | pytest-only, no runnable demo | |
| Real examples/00 now | Pull Phase 8 scope forward | |

**Notes:** Dave conditioned acceptance: "NOT a 'hello world' — realistic
features that pressure-test the emerging SDK code."

**Plan organization:**

| Option | Description | Selected |
|--------|-------------|----------|
| By subsystem | One plan per DESIGN.md component cluster | ✓ |
| By fabric layer | One plan per L1–L6 layer | |
| You decide | Planner derives split | |

**Fixture domain:**

| Option | Description | Selected |
|--------|-------------|----------|
| Lock field-service now | Per CLAUDE.md §9 suggestion | |
| Abstract test domain | Synthetic entities | |
| (Free text) | Banking instead of field-service | ✓ |

**Notes:** Conflict with CLAUDE.md §9 surfaced; Dave resolved (free text):
"Create a mix of examples with the first one as a banking example. The
test suite will contain a horizontal flavor of examples." → §9 amendment
+ DECISIONS.md ruling required.

**Wave-1 front-loading:**

| Option | Description | Selected |
|--------|-------------|----------|
| Scaffold + slice-only contracts | Minimal front-load | ✓ |
| Scaffold + full contract layer | All contracts up front | |
| You decide | | |

---

## CI lint mechanics

| Option | Description | Selected |
|--------|-------------|----------|
| Custom AST checkers | In-repo, tested checkers | ✓ |
| Ruff/flake8 plugin | Packaged linter plugin | |
| Layered: import-linter + custom AST | Two tools | |

**Gating timing:** From first fabric commit ✓ (vs warn-first).
**No-Hardcoding precision:** Heuristics + versioned allowlist file ✓ (vs
strict structural rules only; vs you-decide).
**CI infra:** GitHub Actions ✓ (vs local-first; vs both from day one).

---

## Backend & infra logistics

**Postgres provisioning:** Testcontainers + CI service container ✓ (vs
docker-compose only; vs you-decide).
**Postgres timing:** After slice, within I.1 ✓ (vs parallel from start).
**MCP ArtifactStore:** Protocol+file in I.1, MCP impl in I.3 ✓ (vs both
in I.1; vs you-decide). Success criterion 4 amendment flagged.
**Chroma:** Include in I.1 ✓ (vs skip — recommendation was skip; Dave
granted the D-IMPL-03 budget).

---

## Test strategy depth

**Composition-preservation:** Property-based (Hypothesis) + banking
fixtures ✓ (vs fixtures only; vs you-decide).
**Discipline:** TDD on contracts/invariants ✓ (vs strict TDD everywhere;
vs tests-with + coverage gate).
**Backend parity:** Shared parametrized conformance suite ✓ (vs
per-backend suites; vs you-decide).
**Gate bar:** Per-invariant checklist green, no % coverage gate ✓ (vs
checklist + coverage floor; vs you-decide).

---

## Claude's Discretion

- No-Hardcoding heuristic set/thresholds (within allowlist mechanism).
- Slice contract subset, plan/wave counts, `/src` module layout.
- Banking fixture ontology specifics (values in artifacts, never code).

## Deferred Ideas

- MCP-backed ArtifactStore reference impl → I.3 (Phase 6).
