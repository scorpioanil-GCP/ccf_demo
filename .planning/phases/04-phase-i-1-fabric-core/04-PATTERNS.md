# Phase 4: Phase I.1 — Fabric Core - Pattern Map

**Mapped:** 2026-07-25
**Files analyzed:** 30 planned files/modules
**Analogs found:** 0 / 30 (greenfield — verified: `/src`, `/runtime`, `/tests` empty; zero `.py` files in repo; no `.github/`, no `tools/`)

> **Greenfield statement.** This is the first implementation phase. There is
> no existing code in the repository to copy patterns from. The pattern
> sources for every file are therefore **documents, not code**:
> `04-RESEARCH.md` (concrete code examples + package layout),
> `docs/DESIGN.md` (contract-level signatures per component), and
> CLAUDE.md §11 conventions. Homecams (`/home/parkave/homecams_v2`) is
> pattern triangulation only — **never copy code from it** (CLAUDE.md §2.1).

## File Classification

Files from CONTEXT.md D-04/D-05 subsystem list and RESEARCH.md recommended
layout (layout itself is planner discretion within DESIGN.md names).

| New File/Module | Role | Data Flow | Analog | Pattern Source Instead |
|---|---|---|---|---|
| `src/ccf/contracts/` (base + SignalEnvelope + claim types) | model | transform | none | RESEARCH.md "Contract base" example; DESIGN.md §2A.2.1 |
| `src/ccf/signal/` (envelope, `SignalSourceProtocol`) | model/protocol | event-driven | none | DESIGN.md §2A.2.1–.2 |
| `src/ccf/assembly/` (AssemblyWorker, resolution, stitching, policy binding) | service | event-driven → CRUD | none | DESIGN.md §2A.3, §2A.5.4; RESEARCH.md Pattern 1 |
| `src/ccf/graph/` (ContextGraph, Reader/Writer Protocols) | model/protocol | CRUD | none | RESEARCH.md "Reader/writer Protocol split"; DESIGN.md §2A.5.1–.3 |
| `src/ccf/graph/backends/sqlite.py`, `postgres.py` | store impl | CRUD | none | RESEARCH.md "Idempotent upsert" SQL example; DESIGN.md §2A.5.2 |
| `src/ccf/operators/` (4 categories, registry, planner) | service | transform (pure read) | none | RESEARCH.md Pattern 3; DESIGN.md §2B.1 |
| `src/ccf/projection/` (ProjectionPlan Protocol, engine) | service/protocol | transform | none | DESIGN.md §2B.2 |
| `src/ccf/products/` (contract + three gates) | model/service | request-response | none | RESEARCH.md Pattern 4; DESIGN.md §2B.3 |
| `src/ccf/halflife/` (λ_c/D_c mechanism) | utility | transform | none | DESIGN.md §2B.4 (values from Control Plane ONLY) |
| `src/ccf/replay/` (5-dim record, engine, snapshots) | service | file-I/O | none | RESEARCH.md Pattern 5; DESIGN.md §2B.5 |
| `src/ccf/controlplane/` (versioned registry, audit) | service/config | CRUD (append-only) | none | DESIGN.md §7; RESEARCH.md Pitfall 5 (build EARLY) |
| `src/ccf/artifacts/` (Protocol + file-backed impl) | store impl | file-I/O | none | DESIGN.md §2B.5 / D-IMPL-26 (sha256 addressing) |
| `src/ccf/similarity/` (Protocol, sqlite-vec, chroma optional) | store impl | request-response | none | D-IMPL-03; chroma = optional extra |
| `src/ccf/boot.py` (composition root) | config | — | none | RESEARCH.md Pattern 1 (single-writer DI stack) |
| `runtime/ccf_runtime/` (CDC adapter, async) | adapter | streaming/event-driven | none | DESIGN.md §2A.4.1; fixture/file-fed, no Kafka dep |
| `tools/lints/` (CINV-01..03 checkers + allowlist.yaml) | utility | batch | none | RESEARCH.md Pattern 6 + "Import lint core" example |
| `tests/conformance/` (GraphStore, ArtifactStore, SimilarityIndex) | test | — | none | RESEARCH.md Pattern 2 (parametrized backend-factory fixture, D-16) |
| `tests/properties/test_composition.py` | test | — | none | RESEARCH.md "Composition-preservation property" example (D-14) |
| `tests/gates/`, `tests/replay/`, `tests/invariants/` | test | — | none | RESEARCH.md Validation Architecture table; TDD-first per D-15 |
| `tests/fixtures/banking/` (YAML ontology/events) | fixture artifacts | — | none | D-02/D-03; values in YAML only, never code |
| `pyproject.toml`, `.github/workflows/ci.yml` | config | — | none | RESEARCH.md Standard Stack + D-09/D-10 |
| Doc edits: `CLAUDE.md` §9, `docs/DECISIONS.md`, `.planning/ROADMAP.md` | docs | — | exact (existing files) | Follow existing D-IMPL entry format in `docs/DECISIONS.md` |

## Pattern Assignments

No code analogs exist. For each file, the planner should embed the
RESEARCH.md code example verbatim as the seed pattern. Key excerpts
(all from `.planning/phases/04-phase-i-1-fabric-core/04-RESEARCH.md`,
"Code Examples" and "Architecture Patterns" sections):

### All contract files — Pydantic base (RESEARCH.md lines ~312-318)
```python
from pydantic import BaseModel, ConfigDict

class CCFContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
```
Every public class docstring cites its whitepaper section (CLAUDE.md §11);
SDK extensions cite CLAUDE.md and are marked **SDK-defined**.

### `src/ccf/graph/` — reader/writer Protocol split (RESEARCH.md ~lines 321-331)
```python
from typing import Protocol

class GraphReader(Protocol):
    def as_of(self, *, tenant_id: str, at: datetime) -> "GraphView": ...

class GraphWriter(Protocol):  # module import-linted to ccf.assembly + ccf.boot
    def upsert_entity(self, *, tenant_id: str, entity: EntityClaim,
                      lineage: LineageEntry) -> UpsertResult: ...
```

### `src/ccf/graph/backends/*` — idempotent upsert, one semantic two dialects
```sql
INSERT INTO entities (tenant_id, entity_uri, ...)
VALUES (?, ?, ...)
ON CONFLICT (tenant_id, entity_uri) DO UPDATE SET ...;
-- lineage: separate append-only table; INSERT OR IGNORE on full-entry identity
```
Parameterized queries only (never f-string SQL). No UPDATE of claim
content, no DELETE — supersession rows only.

### `tests/properties/` — composition-preservation harness
```python
@given(graph=banking_graph_states())
@settings(deadline=None)
def test_composition_preservation(graph, pair):
    a, b = pair
    assert canonical_bytes(compose(a, b)(graph)) == canonical_bytes(a(b(graph)))
```
Prerequisite: build the ONE canonical JSON serializer (sorted keys/sets,
RFC3339 UTC, no floats, sha256 identity) in the slice — composition tests,
D-IMPL-26 addressing, and replay hashes all depend on it.

### `tools/lints/` — AST import lint core (RESEARCH.md ~lines 358-377)
Stdlib `ast` walker with deny-list (`google.adk`, `langgraph`,
`claude_agent_sdk`) plus `GraphWriter`-module restriction to
`ccf.assembly`/`ccf.boot`. Allowlist file `tools/lints/allowlist.yaml`
entries: `{file, rule, fingerprint, reason, reviewer}`. Each checker
unit-tested with violating and clean fixture snippets (D-06).

### Doc-edit files — the only true analogs in the repo
- `docs/DECISIONS.md` — copy the existing D-IMPL entry format (ID, ruling,
  date, approver, originating section) for the new D-03 banking-domain
  ruling.
- `.planning/phases/0{1,2,3}-*` — reuse the established multi-plan wave
  structure for Phase 4 plans.

## Shared Patterns

### Whitepaper-citation docstrings
**Apply to:** every public class in `/src` and `/runtime`.
Cite `docs/CCF_Whitepaper_1-2.md` section (or CLAUDE.md §N + "SDK-defined").

### Injected clock / temporal boundary
**Apply to:** operators, gates, replay. Never `datetime.now()` inside
mechanism — `now` is an explicit input (determinism + Hypothesis).

### kw-only `tenant_id` on every execute call
**Apply to:** all graph/operator/product surfaces (D-IMPL-05); no
untenanted path.

### Single test boot fixture
**Apply to:** all tests needing a writer — one `fabric_boot` pytest
fixture running the real composition root against temp SQLite. No
bypass constructors, no test-only writers.

### No-Hardcoding
**Apply to:** `/src`, `/runtime`, `/examples`, and fixture *code*. All
values (λ_c tables, thresholds, ontology, MAX_TTL) live in YAML/Control
Plane artifacts. Sync-only in fabric core; async only in `ccf-runtime`
ingestion adapters.

## No Analog Found

All 30 code files — the repository contains no code. Planner must use
RESEARCH.md patterns (above) and DESIGN.md §2A/§2B/§7/§9 contract
signatures as the sole pattern sources. Do not port from Homecams.

## Metadata

**Analog search scope:** entire repo (`find -name "*.py"` → 0 results);
`/src`, `/runtime`, `/tests` verified empty; docs and `.planning` phases
inspected for convention analogs.
**Pattern extraction date:** 2026-07-25
