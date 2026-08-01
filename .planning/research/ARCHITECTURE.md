# Architecture Patterns — v0.2 Integration (Perf Battery, Docs Suite, Hardening)

**Domain:** CCF SDK v0.2 milestone — integrating new capabilities into the shipped v0.1 monorepo
**Researched:** 2026-07-31
**Confidence:** HIGH on integration points (read directly from the shipped tree, Makefile, DECISIONS.md, audit register); MEDIUM on tooling specifics (pytest-benchmark / mkdocs conventions from training data — verify versions at plan time)

## Existing Architecture (integration substrate)

- `src/ccf` — fabric + agents, mypy --strict, zero harness/runtime imports (lint-enforced)
- `runtime/ccf_runtime` — adapters, MCP, HTTP (`create_app`), CLI, orchestration drivers
- `tests/` — 1339 tests, `make test` runs full suite with `CCF_REQUIRE_HARNESSES=1`
- `examples/` — 8 examples, each a CI job leg via `make examples`
- `tools/lints` — CI invariants; `Makefile` is the single command surface (`ci: ci-core examples`, D-10), mirrored by `.github/workflows/ci.yml`; `live-legs.yml` is the opt-in precedent (workflow_dispatch + key-gated)
- `docs/` — whitepaper, phase deliverables, `security-notes.md`; no rendered docs toolchain yet

---

## (a) Performance Test Battery

### Where benchmarks live: top-level `perf/`, not `tests/benchmarks/`

**Recommendation: `perf/` as a sibling of `tests/` and `examples/`.** Rationale:

1. `make test` collects all of `tests/` under the always-on pipeline. Benchmarks inside `tests/` require permanent deselection machinery (markers + addopts) and one misconfiguration puts minutes of benchmark time — and timing flakiness — into the blocking suite. A separate tree makes exclusion structural, not configurational.
2. It parallels the `examples/` precedent: a first-class surface with its own Makefile family and its own CI job, invoked explicitly.
3. Baselines are committed artifacts; `perf/baselines/` beside `perf/suites/` keeps data next to the thing that produced it (same code-and-artifacts-side-by-side instinct as §9 examples).

Proposed layout (new):

```
perf/
  suites/
    test_micro_operators.py      # operator algebra, product validation gates, factory
    test_fabric_scale.py         # L1→L6 load/scale curves (graph size sweeps)
    test_crossproc_latency.py    # MCP egress + A2A round-trip (reuses tests/crossproc children)
    test_replay_at_scale.py      # replay resolution + byte-equality at N records
  baselines/
    <suite>.<runner-class>.json  # committed pytest-benchmark JSON
  thresholds.toml                # relative regression thresholds, per suite — config, not code
  conftest.py
```

**Tooling:** `pytest-benchmark` — JSON export, `--benchmark-compare`, and `--benchmark-compare-fail="mean:15%"`-style *relative* gates are exactly the committed-baseline-without-flaky-CI mechanism needed. (MEDIUM confidence on flag spellings; verify current pytest-benchmark docs at plan time.)

### Baselines and non-flaky comparison

- **Relative thresholds only.** Never assert absolute wall-clock. Compare current run vs committed baseline JSON with a percentage tolerance per suite (micro suites tolerate less, cross-process more — I/O jitter).
- **Baselines keyed by runner class.** A baseline captured on Dave's workstation is meaningless on a GitHub-hosted runner. Commit baselines per runner class (`local`, `gha-ubuntu-latest`); the compare step selects by an env var. Regenerating a baseline is a deliberate, reviewed commit (`make perf-baseline`), never automatic.
- **CI job: opt-in, modeled on `live-legs.yml`.** New `perf.yml` with `workflow_dispatch` + optional `schedule` (nightly). Never in the merge-blocking `ci.yml` path — a perf regression is a finding to triage, not a red build on an unrelated PR. Whether nightly schedule is on or dispatch-only: Dave's call (see D-IMPL list).

### `make perf` under the D-10 single-command discipline

```
perf:          ## Full battery vs committed baseline, relative thresholds (opt-in; NOT in `make ci`)
perf-micro / perf-scale / perf-crossproc / perf-replay
perf-baseline: ## Regenerate committed baselines (deliberate, reviewed)
```

`make ci` stays exactly the always-on pipeline (D-10 text: "full local reproduction of the *always-on* pipeline"), so `perf` sits beside it the way live legs do. `perf.yml` invokes `make perf` — the mirror discipline holds.

**Mechanism-not-values note:** threshold percentages and sweep sizes are project QA calibration, not SDK domain values — but keep them in `perf/thresholds.toml`, not scattered as code constants, consistent with the house style.

---

## (b) Documentation Suite

### Where docs source lives

`docs/` is already the deliverables home; the rendered adopter suite should be a subtree, not a rival top-level:

```
docs/
  guide/                 # adopter's guide source (markdown)
    getting-started.md   # pip install → quickstart, mirroring examples/00
    concepts/            # pillars, fabric layers, archetype/agent, two channels
    how-to/              # declare an agent, grant a skill, bind a harness, swap stores
    security.md          # promotes/extends existing docs/security-notes.md; create_app posture, key management (D-GATE-I.4.1 carried obligation)
    deployment.md
    artifacts-reference.md  # definition-artifact schema reference (D-IMPL-28 schema, rendered)
  reference/             # generated API/Protocol reference (build output config, source = docstrings)
  mkdocs.yml (or equivalent — toolchain choice below)
```

### Docstring whitepaper citations → reference docs

Every public class already cites its whitepaper section (or CLAUDE.md § for SDK extensions) in its docstring — this is the asset. **mkdocstrings** (with mkdocs-material) renders those docstrings directly into the Protocol/API reference, so the citations flow to adopters with zero duplication. Two integration points:

1. A small build hook (or plain convention) that renders `§7.4`-style citations as links to anchors in the in-repo whitepaper markdown — nice-to-have, not gating.
2. A **docs-coverage lint** in `tools/lints/`: every public class in `src/ccf` and `runtime/ccf_runtime` has a docstring containing a citation token. This already holds informally (D-GATE-I fidelity spot check); making it a lint locks it, and it is cheap.

**OpenAPI polish:** add `make openapi` exporting the FastAPI app's spec to `docs/reference/openapi.json` as a build step; the docs build embeds it. Drift check: a test asserting exported spec == committed spec (or regenerate-in-build so there is no committed copy to drift).

### Does the docs build join ci.yml?

**Yes — a strict docs build is deterministic and fast, so it belongs in the always-on pipeline**: `make docs` (strict mode — broken cross-references and mkdocstrings import errors fail the build) added to `make ci` and a matching `docs` job in `ci.yml`. That amends the composition of `make ci`; D-10 is a Dave ruling, so log the amendment rather than silently extending it (see D-IMPL list). **Publishing** (GitHub Pages vs artifact-only) is a separate question — the repo is private and stays private — and needs Dave's ruling.

---

## (c) Hardening Intake

### WR-01 — Per-tenant authorization: at the door, not the transport

**Recommendation: the door.** Grounds:

- `InMemoryHitlTransport` lives in `/src` and is already tenant-*partitioned* (D-23) but deliberately identity-agnostic below the D-16 authority path. Authorization is a deployment concern bound to verified identity, and verified identity exists only at the doors (`request.state.token_grant` on HTTP per D-IMPL-67; the MCP server's verified token). Pushing `TokenGrant` into `/src` would leak a runtime auth contract into core.
- Precedent: D-IMPL-67 composed identity *derivation* at the doors; tenant authorization is the same seam, one check further.

**TokenGrant.scopes → queue partitions:** the SDK must not invent a scope vocabulary (CINV-01 / mechanism-not-values — `scopes` docstring already says "deployment vocabulary"). So the mechanism is: a door-level authorization hook — e.g. `TenantAuthorizerProtocol` with `authorizes(grant: TokenGrant, tenant: str) -> bool` — invoked by the HTTP HITL routes and the MCP HITL server before any transport touch, with a typed 403/refusal (reusing the `ERROR_*` constants pattern). What the SDK **cannot** decide alone: the mapping shape of a *reference* authorizer. A scope-string convention like `hitl:{tenant}` is an SDK-invented value; a deployment-supplied mapping artifact is a Control Plane surface. **Both readings are defensible → new D-IMPL, do not default** (options: (i) Protocol only + example-artifact mapping in examples 05/06, (ii) reference authorizer reading a deployment-registered Control Plane mapping, (iii) documented scope-naming convention).

### WR-02 — InMemoryHitlTransport synchronization

Straight defect fix, no D-IMPL needed. The transport Protocol is sync and the FastAPI door dispatches sync handlers onto a threadpool, so guard the queue mutation/read paths with `threading.Lock` (one lock per tenant partition, or a single lock — reference-impl contention is negligible; per-partition preserves the D-23 "tenants never interleave" story cleanly). Do **not** switch to asyncio primitives: the Protocol is sync and consumed from non-async contexts (CLI-local, tests). Add a threadpool-concurrency regression test.

### WR-03 — AdkWorkflowDriver robustness

Straight defect fix, no D-IMPL needed. Two items: (1) `persisted_state` must not call `asyncio.run` (explodes under a running loop) — either detect a running loop and refuse with a typed error directing callers to the async accessor, or snapshot state at segment boundaries so the sync property reads stored state; (2) bare `KeyError` on an unexecuted segment becomes a typed error (e.g., `SegmentNotExecutedError`) consistent with the typed-refusal doctrine. Conformance legs (unchanged shared bodies, D-IMPL-60) must stay green.

### ApprovalGate.resolve × signed_binding_required (D-IMPL-62 / D-16)

**This is a ruling, not a design task — flag it, don't decide it.** Current state: D-16 requiredness is enforced at the *transport authority path* (submit); D-IMPL-62 rules the HTTP/CLI door submit-only; but `ApprovalGate.resolve` is a direct in-process authority surface taking a `HumanPrincipalBinding` — when a policy declares `signed_binding_required`, the direct-resolve path does not consult it. Candidate shapes to present to Dave (each stays within existing contracts differently):

- **(a)** `resolve` gains an optional `signed_binding: SignedPrincipalBinding | None` parameter and, when the gate is constructed with a Control Plane + policy key (mirroring the transport's D-16 constructor quartet), re-resolves the policy per call and refuses an unsigned resolution under a requiring policy (typed refusal, replay-recorded).
- **(b)** direct `resolve` is deprecated as an authority surface when `signed_binding_required` is in force — authority flows only through transport-verified submissions (the MCP-channel wiring pattern); `resolve` refuses outright under a requiring policy.
- **(c)** status quo documented: `signed_binding_required` governs the transport door only; direct in-process resolve is composition-root-trusted by definition.

The audit already names this a "post-v0 D-IMPL candidate" — it becomes **D-IMPL-6x** in this milestone's Phase-D-mini-cycle intake.

### create_app auth-default warning

T-07-24 (default unauthenticated, `AUTH_POSTURE_SENTENCE`) is a Dave ruling and D-IMPL-67 explicitly did not reopen it. Adding a *loud adopter-facing warning* (a `warnings.warn`/log line at `create_app(auth=None)` construction + a prominent docs callout in `docs/guide/security.md`) is additive, but because it touches the ruled posture's DX, record Dave's confirmation in the same D-IMPL batch rather than shipping silently. The docs half is unambiguous v0.2 scope.

---

## Data Flow / Seam Changes

| Seam | Change | New or Modified |
|------|--------|-----------------|
| HTTP + MCP HITL doors | tenant-authorization check between identity derivation and transport submit | Modified (both doors), New Protocol |
| `src/ccf/hitl/transport.py` | internal locking; behavior/contract unchanged | Modified |
| `src/ccf/hitl/approval_gate.py` | per Dave's ruling only | Gated on D-IMPL |
| `runtime/.../orchestration/adk` driver | loop-safety + typed errors | Modified |
| Makefile / ci.yml | `perf*`, `docs`, `openapi` targets; `docs` joins always-on; `perf.yml` new workflow | Modified + New |
| `tools/lints` | docs-citation-coverage lint (optional but cheap) | New |
| `perf/`, `docs/guide/`, `docs/reference/` | new trees | New |

## Suggested Build Order

1. **Hardening defect fixes first** (WR-02, WR-03) — no rulings needed, they stabilize the surface everything else measures and documents.
2. **D-IMPL ruling batch to Dave** (list below) — gates WR-01, ApprovalGate composition, perf-job scheduling, docs toolchain/publishing, D-10 amendment. Batch them so Phase D mini-cycle runs once.
3. **WR-01 door authorization + ApprovalGate composition** per rulings; extend examples 05/06 to demonstrate tenant authorization (hardened-surface demonstrability precedent from D-IMPL-67 N2).
4. **Perf battery** — micro suite first (fast feedback), then scale/crossproc/replay; capture baselines last, after hardening changes land (baselines against the final surface).
5. **Docs suite** — toolchain + reference generation early (parallelizable with 3–4), adopter-guide *content* last so it documents the hardened surface and can cite measured performance.

## Items Requiring D-IMPL Rulings from Dave (do not default)

1. **WR-01 scope→tenant mapping shape** — Protocol-only vs Control-Plane mapping artifact vs scope-naming convention (SDK must not invent scope vocabulary).
2. **ApprovalGate.resolve × signed_binding_required** — shapes (a)/(b)/(c) above; already flagged by v0.1 review consensus as a D-IMPL candidate.
3. **Perf governance** — nightly schedule vs dispatch-only for `perf.yml`; which runner class(es) baselines bind to; per-suite threshold values (provisional-able, but they are committed gates so log them).
4. **Docs toolchain + publishing target** — mkdocs-material/mkdocstrings recommended; where a private repo's rendered docs live (Pages-private, artifact-only, none-for-v0.2).
5. **D-10 amendment** — `make docs` joining the always-on `make ci` composition (recommended yes; D-10 is a ruled decision so the extension is logged, not silent).
6. **create_app auth-default runtime warning** — additive to T-07-24 but touches a ruled posture; confirm.

## Anti-Patterns to Avoid

- **Benchmarks in the blocking suite** — timing assertions in `make test` will flake; keep `perf/` structurally outside collection.
- **Absolute-time assertions or auto-regenerated baselines** — both destroy the regression signal; baselines change only by deliberate commit.
- **Authorization in `/src` transport** — leaks runtime auth contracts into core; doors own identity and authorization.
- **Inventing scope strings or tenant mappings in SDK code** — CINV-01 violation; that is the D-IMPL above.
- **Hand-written API reference** — duplicates docstrings and drifts; generate from the citation-bearing docstrings that already exist.

## Sources

- `/home/parkave/ccf_code/.planning/PROJECT.md`, `.planning/v0.1-MILESTONE-AUDIT.md` (tech-debt register, WR-01..03)
- `/home/parkave/ccf_code/docs/DECISIONS.md` — D-IMPL-62/63/66/67, D-16/D-15 context rulings, D-GATE-I.4.1, D-GATE-I
- `/home/parkave/ccf_code/Makefile`, `.github/workflows/{ci.yml,live-legs.yml}` (D-10/D-11 wiring)
- `src/ccf/hitl/{transport.py,approval_gate.py}`, `runtime/ccf_runtime/mcp/auth.py` (TokenGrant, D-16 quartet, resolve signature) — read directly (HIGH)
- pytest-benchmark compare/threshold behavior; mkdocs-material + mkdocstrings — training data (MEDIUM; verify at plan time)
