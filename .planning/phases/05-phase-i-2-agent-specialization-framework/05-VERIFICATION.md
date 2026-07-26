---
phase: 05-phase-i-2-agent-specialization-framework
verified: 2026-07-26T21:30:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 4/4
  scope: "Third pass — post-verification code (fba5b2a ControlPlaneStateStore/InMemoryStateStore; 46bef65..d450d64 IN-01..IN-06; e1a3bc4..8d38e6a WR-01..WR-05) was outside the second pass's verified scope"
  gaps_closed: []
  gaps_remaining: []
  regressions: []
  history:
    - pass: 1
      status: gaps_found
      score: 3/4
      note: "SC3 FAILED (CR-01 per-agent grant_set_hash + WR/IN cluster)"
    - pass: 2
      status: passed
      score: 4/4
      note: "SC3 closed by plans 05-08..05-10; verified 2026-07-26T18:00:00Z"
    - pass: 3
      status: passed
      score: 4/4
      note: "This pass — re-verified against the new ccf.controlplane.state and ccf.controlplane.resolution surfaces; no invariant weakened"
advisories:
  - id: ADV-01
    severity: warning
    item: "src/ccf/controlplane/state.py closes its docstring with 'Algorithmic module (CINV-03).' but carries no `__ccf_mode__ = \"algorithmic\"` dunder"
    evidence: "grep '__ccf_mode__' src/ccf/controlplane/*.py returns audit.py:35, artifacts.py:47, registry.py:58, resolution.py:35 — state.py absent. tools/lints/algorithmic.py:72 returns [] for untagged modules, so CINV-03 does not inspect this file."
    impact: "Low today — state.py imports only `typing`. But the documented claim is not backed by the enforcing mechanism, and a future import into this module would go unchecked."
    remedy: "Add `__ccf_mode__ = \"algorithmic\"` after the `from __future__` block, as every sibling controlplane module does."
  - id: ADV-02
    severity: info
    item: "Grant-transition auditing is paired-call convention, not a structural property of the state seam"
    evidence: "Every `_put_state` call in src/ccf/skills/grants.py (lines 752, 769, 787, 841, 846, 852, 871, 893) is immediately followed by a `_record(...)` audit append — verified call-site by call-site. But `ControlPlaneStateStore.put` itself neither audits nor requires an audit token."
    impact: "INV-CH7-71 holds in the shipped code but is a reviewable discipline rather than an unrepresentable-violation property. Same posture as before this pass; not a regression."
  - id: ADV-03
    severity: info
    item: "The AGNT-01 consumption allowlist is a direct-import check, not a transitive one"
    evidence: "tests/agents/test_consumption_discipline.py::_ccf_imports walks one module's AST. Transitive closure computed independently: `ccf.skills.grants` and `ccf.replay.record` reach ccf.graph.protocols, ccf.operators.*, ccf.projection.*, ccf.signal.envelope (type references for the five replay dimensions)."
    impact: "Pre-existing and inherent to the replay record's five-dimension typing — NOT introduced by IN-01. `ccf.controlplane.resolution`'s own closure is fabric-clean (see SC-notes)."
human_verification: []
---

# Phase 5: Phase I.2 — Agent Specialization Framework Verification Report (Pass 3)

**Phase Goal:** Agents are declared, versioned Control Plane artifacts produced exclusively by the Agent & Task Factory from the six shipped archetypes, specialized through the two governed channels
**Verified:** 2026-07-26T21:30:00Z
**Status:** passed
**Re-verification:** Yes — third pass. Passes 1 and 2 are preserved in `re_verification.history`. This pass exists because commits `e1a3bc4`..`da12052` added code (a new SDK surface, `ccf.controlplane.state`, plus `ccf.controlplane.resolution` and eleven review-finding fixes) that landed *after* pass 2's snapshot and was therefore never verified.

## Gate State — From My Own Run, Not From Claims

| Gate | Command | Result |
| --- | --- | --- |
| Test suite | `.venv/bin/python -m pytest -q -m "not postgres"` | **615 passed, 2 skipped, 12 deselected** in 15.14s (pass 2 saw 577 passed — +38 tests, no losses) |
| Strict typing | `.venv/bin/python -m mypy --strict src tools` | **Success: no issues found in 76 source files** (pass 2: 74 files) |
| Invariant lints | `.venv/bin/python -m tools.lints` | **exit 0**, no output |
| Debt markers | `grep -rn "TBD\|FIXME\|XXX" src/ tools/ tests/ --include=*.py` | **none** |

## Goal Achievement

### Observable Truths (ROADMAP Phase 5 Success Criteria)

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Unified Agent base + six archetypes in `/src`, no agent instances/prompts/domain values in library code; composition per D-IMPL-11/19 | ✓ VERIFIED (no regression) | `git diff ed132c5..HEAD` touches neither `archetypes.py` nor `composition.py`. Pass-2 evidence stands; lint suite exit 0 re-run. |
| 2 | Agent & Task Factory constructs only from definition artifacts (D-IMPL-28); no supported bypass path; lint rejects bypass and prompt literals | ✓ VERIFIED (strengthened) | Factory changed substantially (172 lines) but only additively-restrictive. IN-01: both pinned-resolution copies replaced by the single `resolve_pinned` helper — `grep resolve_pinned` shows `factory.py:101` and `grants.py:571` as the only implementations' consumers, and `grep -c "peek("` is **0** in both modules, so no residual duplicate scan survived. IN-02: `Agent.__init__` now rejects an `identity.definition_uri` that does not equal the URI derived from the definition's own naming triple (`agent.py:186-201`), with the same rule on `Task` (`factory.py:332`). IN-05: task skill-steps class-checked against a negative rule (`factory.py:462-469`). |
| 3 | Skill catalog registration/discovery/grant/revoke; tier-1 refusal; every grant/revocation and the skill-set in force land in replay | ✓ VERIFIED (re-verified against the new state seam — see §"Skill-set-in-force under the state seam") | `grant_set_hash(agent_definition_hash)` (`grants.py:929`) → `effective_hashes` (`grants.py:909`) → `_records()` (`grants.py:521`) → `self._state_store.items(GRANT_STATE)`. The ledger holds no grant dict of its own. Cross-instance agreement is pinned by three non-vacuous tests (below). |
| 4 | All six specialization axes expressible in the definition artifact and versioned; axis change ⇒ new agent version visible in replay | ✓ VERIFIED (no regression) | `definitions.py` unchanged since pass 2. IN-02 tightens the replay-facing `definition_uri` annotation that dimension 4 serializes verbatim, which strengthens rather than weakens the "visible in replay" half of this criterion. |

**Score:** 4/4 truths verified

## Targeted Concern 1 — Does `ccf.controlplane.state` weaken a named invariant?

**Single-writer (CLAUDE.md §10): NOT weakened.** `state.py` has exactly one import — `from typing import Protocol, runtime_checkable`. It reaches no graph store, no L2 writer, no boot token. It is an opaque `dict[tuple[str, str], object]` keyed by `(record_class, key)`. It cannot become a second writer to L3 because it has no handle to L3 and no way to acquire one. The registry exposes it as a read-only property (`registry.py:239`), so a consumer gets the store, never a graph handle.

**Control-Plane-as-audit-plane (INV-CH7-71): held, by paired-call discipline.** I checked every state transition individually rather than trusting the module docstring. All eight `_put_state` call sites in `grants.py` (752, 769, 787, 841, 846, 852, 871, 893) are immediately followed by a `_record(...)` audit append with a matching action — including the WR-01 exception guard (`grants.py:786-788`), which settles a failed grant in terminal `refused` **and** audits it before re-raising. `SplitAuditPlaneError` (`grants.py:132`) makes a ledger and a registry over two different audit logs unconstructable, so the sequence stays singular. Recorded as ADV-02 that this is discipline rather than an unrepresentable-violation property — unchanged posture from pass 2, not a regression.

**Mechanism-not-values (CINV-01): held.** `state.py` holds no consumer vocabulary. It defines no grant state, no workflow state, no record schema — `get`/`put`/`items` take and return `object`. The vocabulary lives with its machine: `GRANT_STATE = "ccf.skill-grant-state"` is declared in `grants.py:108`, and `GrantStateRecord` is a grants-module type. `grants.py:501-507` raises `GrantTransitionError` if the store returns anything other than a `GrantStateRecord` under that class, so the opacity is enforced at the consumer boundary rather than assumed.

**Reference impl ships with the Protocol (CLAUDE.md §11): held.** `InMemoryStateStore` (`state.py:88`) satisfies `runtime_checkable` `ControlPlaneStateStore`, asserted at `tests/controlplane/test_state.py:21`, and is the default when none is injected (`registry.py:234-236`).

## Targeted Concern 2 — Did IN-01 weaken the AGNT-01 allowlist?

Judged independently, not on the author's rationale. I computed the full transitive `ccf.*` import closure of each allowlisted prefix and tested it against the forbidden fabric set (`ccf.graph`, `ccf.assembly`, `ccf.signal`, `ccf.operators`, `ccf.projection`, `ccf.halflife`, `ccf.similarity`, `ccf.llm`, `ccf.boot`):

| Allowlisted prefix | Fabric modules reachable transitively |
| --- | --- |
| `ccf.controlplane.resolution` **(the widening)** | **clean** |
| `ccf.controlplane.state` | clean |
| `ccf.controlplane.registry` | clean |
| `ccf.skills.catalog` / `ccf.skills.dispatch` | clean |
| `ccf.products.contract` | clean |
| `ccf.skills.grants` | ccf.graph.protocols, ccf.operators.*, ccf.projection.*, ccf.signal.envelope — **via `ccf.replay.record` only** |
| `ccf.replay.record` | same set (the five replay dimensions are typed against them) |

**Verdict: the widening admits nothing new.** `resolution.py`'s entire `ccf` import surface is `ccf.artifacts.protocol` (for `parse_artifact_uri`) and `ccf.controlplane.registry` (for two error types) — both already on the allowlist before this change, and both fabric-clean. Adding `ccf.controlplane.resolution` is closed under the pre-existing allowlist: no reachable module became reachable that was not already. The `ControlPlaneResolution` Protocol it exports is read-only and exact-version by construction (`resolve` / `versions` / `peek` / `artifact_class_of` — no register, no "latest"). The AGNT-01 "no path from Agent to L1–L5" invariant is not weakened.

Separately noted as ADV-03 (info, pre-existing): the allowlist test is a *direct*-import check, so the `ccf.replay.record` → fabric-types edge is not something it would have caught either way. That is inherent to the replay record needing to type its graph-snapshot and operator-plan dimensions, and it predates this pass.

## Targeted Concern 3 — Skill-set-in-force replay capture under the state seam

The chain is genuinely rooted in the Control Plane, not in instance state:

`GrantLedger.__init__` binds `self._state_store = control_plane.state_store` (`grants.py:492`) — it allocates no store of its own. `grant_set_hash(agent_definition_hash)` (929) → `effective_hashes(agent_definition_hash)` (909, filtering `record.grant.agent_definition_hash`) → `_records()` (521) → `self._state_store.items(GRANT_STATE)`. `BoundSkillView` resolves at access time through `_effective_entries` (947), which reads the same seam.

**The coverage is not vacuous.** I checked whether the tests would pass against the *pre-fix* instance-state implementation. They would not:

- `test_every_ledger_over_one_control_plane_agrees` (`test_grants.py:718`) constructs a **second** `GrantLedger` over the same registry after a grant is effective, and asserts the successor reports the same `effective_hashes`, the same `grant_set_hash`, `!= NO_GRANTS_SET_HASH`, the same `bound_view`, and state `effective`. Against instance-held state the successor returns the empty set and the positive zero-grants claim — the test fails.
- `test_a_revocation_on_one_ledger_is_seen_by_another` (`test_grants.py:774`) proves agreement survives a *transition*, not just first read: a revocation through ledger A flips ledger B's `grant_set_hash` to `NO_GRANTS_SET_HASH`. Against instance state B never sees it.
- `test_grant_state_is_addressed_on_the_control_plane_state_seam` (`test_grants.py:806`) pins the structural claim rather than only its consequence — it reads `registry.state_store.get(GRANT_STATE, grant_hash)` directly and asserts `not any(isinstance(v, dict) and grant_hash in v for v in vars(ledger).values())`, which is exactly the "shared class-level cache would also pass the agreement tests" hole, closed deliberately.

The false-claim guard survives: `FalseGrantClaimError` still fires at `agent.py:362` on a zero-grants claim with non-empty bound skills, and `perspective_conditioning` still requires `grant_set_hash` with no default.

### Required Artifacts (new/changed since pass 2)

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `src/ccf/controlplane/state.py` | ControlPlaneStateStore Protocol + InMemoryStateStore (D-IMPL-18/27) | ✓ VERIFIED | 117 lines, substantive, wired via `registry.py:234`, consumed by `grants.py:492`. Zero fabric imports. ADV-01: missing `__ccf_mode__` dunder despite the docstring's CINV-03 claim. |
| `src/ccf/controlplane/resolution.py` | Single pinned-resolution rule (IN-01) | ✓ VERIFIED | 126 lines; sole implementation, both call sites converted, zero residual `peek(` scans in factory/grants; dedicated suite `tests/controlplane/test_resolution.py` (141 lines) covers hit / declared-version scan / ambiguity refusal / miss. |
| `src/ccf/skills/grants.py` | State on the seam; SplitAuditPlaneError; pre-registration tenant check | ✓ VERIFIED | +383 lines. IN-04 confirmed: `_tenant_mismatch` is a pure verdict run *before* `register_versioned` (`grants.py:749-754`), so a cross-tenant grant is never written into the append-only registry. |
| `src/ccf/agents/agent.py` | definition_uri coherence (IN-02) | ✓ VERIFIED | Additively restrictive; FalseGrantClaimError intact. |
| `src/ccf/agents/factory.py` | Shared helper; task skill-step class rule (IN-05) | ✓ VERIFIED | Sole `Agent(...)` construction path preserved; lint exit 0. |
| `tests/controlplane/test_state.py` | Seam contract + registry injection + isolation | ✓ VERIFIED | 104 lines incl. `runtime_checkable` conformance, key-sorted `items` determinism, and two-registry isolation (`:91-92`). |

### Key Link Verification

| From | To | Via | Status |
| --- | --- | --- | --- |
| `ControlPlaneRegistry` | `ControlPlaneStateStore` | injected ctor arg, default `InMemoryStateStore`, read-only property | ✓ WIRED |
| `GrantLedger` | `registry.state_store` | `_record_for` / `_put_state` / `_records` — no instance cache | ✓ WIRED |
| `grant_set_hash` (replay dim 4) | Control Plane state | `effective_hashes` → `_records` → `state_store.items` | ✓ WIRED — data flows (Level 4), proven by the successor-ledger test |
| `agents/factory.py` + `skills/grants.py` | `controlplane/resolution.resolve_pinned` | one helper, two call sites, zero duplicates | ✓ WIRED |
| `Agent.__init__` | `artifact_uri(definition triple)` | `definition_uri` equality refusal | ✓ WIRED |

### Requirements Coverage

| Requirement | Status | Evidence |
| --- | --- | --- |
| AGNT-01 (Agent base + six archetypes) | ✓ SATISFIED | SC1; allowlist widening independently proven non-weakening |
| AGNT-02 (Factory + D-IMPL-28 + No-Hardcoding CI) | ✓ SATISFIED | SC2 + SC4; lints exit 0 |
| AGNT-03 (Skill catalog + governed grant/revoke + replay capture) | ✓ SATISFIED | SC3 re-verified against the state seam with non-vacuous cross-instance coverage |

No orphaned requirements.

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
| --- | --- | --- | --- |
| `src/ccf/controlplane/state.py` | Docstring asserts "Algorithmic module (CINV-03)" with no `__ccf_mode__` tag | ⚠️ Warning (ADV-01) | CINV-03 does not inspect the file. No live exposure (only `typing` imported); fix is one line. |

No blockers. No debt markers anywhere in `src/`, `tools/`, `tests/`.

### Human Verification Required

None. Every criterion in this phase is programmatically verifiable and was verified programmatically; no plan carried deferred `<human-check>` blocks.

### Gaps Summary

No gaps. The post-pass-2 code was verified on its own terms rather than on `05-REVIEW-FIX-2.md`'s account of itself. The new `ccf.controlplane.state` seam adds a Protocol-plus-reference-impl surface that imports nothing, holds no consumer vocabulary, and cannot reach L3 — it weakens neither single-writer nor CINV-01, and it strengthens the §6.2 skill-set-in-force property by making two ledgers over one Control Plane unable to disagree, a property pinned by tests that provably fail against the prior implementation. The IN-01 allowlist widening is closed under the pre-existing allowlist: `ccf.controlplane.resolution`'s transitive closure is fabric-clean, so AGNT-01 is intact. One warning-level advisory (ADV-01, a one-line missing lint tag) is carried to §3.1 triage as advisory, not blocking.

Gates re-run independently: 615 passed / 2 declared skips, mypy --strict clean across 76 files, `tools.lints` exit 0.

Phase goal achieved. The D-GATE-I.2 package remains ready to present to Dave per CLAUDE.md §3.1 (approval authority is Dave's alone).

---

_Verified: 2026-07-26T21:30:00Z_
_Verifier: Claude (gsd-verifier), pass 3_
