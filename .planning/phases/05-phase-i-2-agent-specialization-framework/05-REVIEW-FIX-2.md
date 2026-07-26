---
phase: 05-phase-i-2-agent-specialization-framework
fixed_at: 2026-07-26T00:00:00Z
review_path: .planning/phases/05-phase-i-2-agent-specialization-framework/05-REVIEW.md
iteration: 2
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 5 (I.2): Code Review Fix Report — Iteration 2

**Fixed at:** 2026-07-26
**Source review:** `.planning/phases/05-phase-i-2-agent-specialization-framework/05-REVIEW.md`
**Iteration:** 2 (scope: IN-01 … IN-06; `fix_scope: all`)
**Prior iteration:** `05-REVIEW-FIX.md` (WR-01 … WR-05)

**Summary:**
- Findings in scope: 6 (IN-01 … IN-06)
- Fixed: 6
- Skipped: 0
- Carried to prior iteration, verified closed, no change needed: 5 (WR-01 … WR-05)

**Verification gate, run before every commit:** `pytest` (614 passed, 2 skipped
— up from 606 at iteration 1's close, +8 regression tests), `mypy` strict (68
source files, clean), `python -m tools.lints` (exit 0). Where a fix could be
pinned by a failing test, the test was additionally confirmed to *fail* with
the fix reverted (`git stash push <src file>`), so nothing passes vacuously.

## Iteration 1 findings — verified closed, no change needed

| Finding | Commit | Status |
| --- | --- | --- |
| WR-01 grant state machine wedging | `e1a3bc4` | `no_change_needed` |
| WR-02 retry blocked by empty-bump refusal | `9b93763` | `no_change_needed` |
| WR-03 `SkillCatalog.resolve` phantom audits | `dad888e` | `no_change_needed` |
| WR-04 CINV-01c static attribute-alias hole | `50d3a08` | `no_change_needed` |
| WR-05 `GrantLedger` state volatility | `8d38e6a` | `no_change_needed` |

All five commits are present in the branch history and their regression tests
pass in the current tree. Not re-fixed.

## Fixed Issues

### IN-01: Duplicated pinned-resolution logic with divergent not-found semantics

**Files modified:** `src/ccf/controlplane/resolution.py` (new),
`src/ccf/controlplane/__init__.py`, `src/ccf/agents/factory.py`,
`src/ccf/skills/grants.py`, `tests/controlplane/test_resolution.py` (new),
`tests/agents/test_consumption_discipline.py`
**Commit:** `46bef65`

Took the reviewer's fix as specified: a shared
`resolve_pinned(control_plane, uri) -> object | None` in `ccf.controlplane`,
with each call site wrapping the miss. The `ControlPlaneResolution` Protocol
moved with it, since the helper needs to be typed against the read surface and
leaving the Protocol in `ccf.agents.factory` would have inverted the
dependency. Both names are still re-exported from `ccf.agents.factory` and
`ccf.agents`, so no public name moved.

The miss case is the whole reason the duplication existed, so it is the thing
the helper is deliberately *total* on: it returns `None`, and the two callers
apply their own contracts — the factory raises `AgentDefinitionError` (an
unfollowable ref is a broken definition), the ledger keeps `None` and lets
tier 1 return `PolicyRegimeUnresolvable` (an unresolvable regime is a
governance outcome). Collapsing those two readings together would have been
the obvious way to get this wrong.

Mechanism, not values (§11): the module holds no key vocabulary, no artifact
class, and no domain value — the `{tenant}/{class}/{name}` shape it derives is
carried in from the caller's URI.

`tests/agents/test_consumption_discipline.py` needed the new module added to
`ALLOWED_CCF_PREFIXES`. That allowlist is an architectural invariant (no path
from Agent to L1–L5), so the addition is reasoned in a comment rather than
waved through: `ccf.controlplane.resolution` is a read-only, exact-version
Control Plane surface reaching no fabric layer — the same tier as
`ccf.controlplane.registry`, already permitted.

Regression test pins the shared rule including the audit discipline that made
the duplication dangerous: probes go through `peek`, exactly one `resolve`
fires, on the content actually returned.

### IN-02: `Agent` constructor does not validate `identity.definition_uri` coherence

**Files modified:** `src/ccf/agents/agent.py`, `src/ccf/agents/factory.py`,
`tests/agents/test_agent.py`
**Commit:** `278560b`

Took the reviewer's first option (recompute and refuse) over the second
(narrow the docstring). Replay dimension 4 serializes this URI verbatim, so a
drifted annotation would describe a decision as having been made under an
artifact it was not — the docstring claim was the correct one and the code was
the part that was wrong.

Applied to the sibling `Task` path in `factory.py` as well. `Task` makes the
identical "must agree with `definition`" claim and had the identical gap; the
reviewer flagged only `Agent`, but fixing one and leaving the other is how the
IN-01 duplication problem starts.

Regression tests cover a drifted version *and* a foreign tenant in the URI —
the whole naming triple is checked, not just the version component. Both fail
with the check reverted.

### IN-03: WR-07 shared-audit-log wiring relies on caller discipline

**Files modified:** `src/ccf/skills/grants.py`, `src/ccf/skills/__init__.py`,
`tests/skills/test_grants.py`
**Commit:** `e797433`

Took both halves of the reviewer's suggestion rather than either alone:
`audit` now defaults to `control_plane.audit_log` *and* refuses any other log,
via the new typed `SplitAuditPlaneError`. Defaulting alone would have left the
foreign-log path open; refusing alone would have left the redundancy without
the convenience. The parameter survives only as an explicitness affordance for
callers that prefer to name what they are wiring — which every existing call
site does, so none of them changed.

The rationale is the invariant, not tidiness: the Control Plane *is* the audit
plane and there is one of it (INV-CH7-71, CLAUDE.md §10). A split plane
produces two partial journals and no complete one — a grant's registration in
one, its `grant_effective` transition in the other, neither able to answer
"what was in force" alone. WR-07 made the shared log *injectable*; this makes
it unavoidable.

### IN-04: Cross-tenant grant documents are permanently registered before the tenant check

**Files modified:** `src/ccf/skills/grants.py`, `tests/skills/test_grants.py`
**Commit:** `6737bac`
**Treated at warning-level care per instruction.**

The tenant-coherence check was extracted into `_tenant_mismatch` — pure,
mutating nothing and auditing nothing, *specifically* so it can run before
registration where the caller still has the option of writing nothing at all —
and moved from `_decide` to immediately after catalog resolution, ahead of
`register_versioned`.

Why this one has teeth: registration is append-only and irreversible. The
prior ordering meant a refused cross-tenant grant was nonetheless written
permanently under the **foreign** tenant's key namespace
(`other-bank/ccf.skill-grant/...`) and stayed resolvable there, in a Control
Plane the requesting deployment owns but that tenant prefix does not belong
to. A refusal that leaves a durable artifact behind is not a refusal.

Caller-visible behavior is deliberately unchanged: same typed
`TenantMismatch`, same terminal `refused` state, same audited refusal
(`resolved=False`). The existing WR-02 test passes untouched. What changes is
only that the Control Plane now keeps nothing it turned away. The terminal
`refused` state was kept rather than adopting the WR-04 "leave the ledger
untouched" shape, because a cross-tenant grant is inadmissible as a document
rather than blocked by a remediable condition — it is a decided outcome, not a
deferred one.

WR-01's no-wedged-states guarantee is preserved: the new path returns before
any state mutation reachable by an exception, and the post-mutation guard is
untouched.

Regression test asserts three independent things — the foreign key has no
versions, no key under the foreign tenant prefix exists in the grant class,
and no `register*` event was audited for it. It fails against the prior
ordering (the artifact was there).

### IN-05: `TaskFactory` class-checks agent steps but not skill steps

**Files modified:** `src/ccf/agents/factory.py`, `tests/agents/test_factory.py`
**Commit:** `5148f18`

Took the reviewer's stronger option (refuse SDK-owned non-skill classes) *and*
the weaker one (document the asymmetry), because the asymmetry is real and
survives the fix — documenting it is not redundant once it is narrowed.

A skill step genuinely cannot be held to one class id: its target may be a
deployment-declared class the SDK has no name for, and holding it to
`ccf.skill-catalog-entry` would close that extension point. So the check is
*negative* rather than an equality: SDK-owned classes (the `ccf.` prefix)
other than the skill catalog entry are refused, since an agent definition or
prompt artifact is never a skill target and its appearance there is miswiring.
Everything else, including every deployment-declared class, passes untouched.
Using the namespace prefix rather than enumerating the SDK's own classes keeps
the rule from needing an edit every time a class is added.

Two regression tests, in both directions — a skill step pointed at an agent
definition is refused (fails without the fix), and the fixture's
deployment-declared skill target still constructs, which pins that the check
has not over-fired and closed the extension point it was written to preserve.

### IN-06: `local_callable` dispatch is artifact-driven arbitrary code execution

**Files modified:** `docs/PHASE_I2_GATE.md`, `src/ccf/skills/dispatch.py`
**Commit:** `d450d64`
**Status:** recorded as an accepted-risk carry-forward. **No dispatch
semantics were changed**, per instruction.

Recorded in `PHASE_I2_GATE.md` §5 as an I.3 threat-model handoff item
immediately alongside the Jinja2 SSTI note, and cross-referenced from a new
`_invoke_local_callable` docstring so the code and the deferral cannot drift
apart.

The framing the note insists on: the T-05-18 trust posture is a *precondition
on the input* (a `callable_ref` arrives only from a Control Plane artifact
registered inside the tenant trust boundary — in I.2, an in-repo fixture), not
a property of the dispatch path. **I.3 invalidates that precondition rather
than inheriting it**: once artifacts arrive over MCP artifact stores or A2A
federation (CLAUDE.md §7.2/§7.4), a `callable_ref` is remote-influenced input
and this is a remote code execution path. Three candidate controls are named
so the I.3 decision is scoped rather than rediscovered: an import allowlist, a
registered-callable indirection removing free-form module paths, or a Control
Plane admission check on `callable_ref` provenance.

## Invariant Check

No fix touched the **No-Hardcoding Rule** (§6.4): no prompt, agent definition,
task graph, threshold, approval rule, or skill grant entered code. The two new
code-level constants are mechanism, not values — `SDK_ARTIFACT_CLASS_PREFIX`
is the SDK's own namespace marker (how a deployment-declared class is told
apart from an SDK one), and `GOVERNANCE_FIELD`-style envelope naming was not
touched. Every test value still comes from `tests/fixtures/banking/`.

**Harness neutrality** (§7.3): no harness import added anywhere; the new
`ccf.controlplane.resolution` module imports only `ccf.artifacts.protocol` and
`ccf.controlplane.registry`. The `/src` import lint is green.

**Single-writer** (§10): no new write handle to L3. IN-04 *removes* a write
(the foreign-tenant registration) and adds none.

**Audit / replay-by-construction** (§6.2, §8.2): three of the six fixes
strengthen this plane rather than merely preserving it. IN-01 propagates the
WR-08 "probes are not resolutions" discipline into the one place it can no
longer drift from. IN-03 makes the singular audit plane structural instead of
conventional. IN-02 stops a drifted URI annotation from reaching replay
dimension 4. IN-04 keeps the refusal audit while removing the artifact.

**Architectural consumption discipline** (AGNT-01): the one allowlist widening
(`ccf.controlplane.resolution`) is reasoned in place and opens no path from
Agent to L1–L5.

## Nothing requiring a D-IMPL ruling

Every finding in this iteration was closable within existing rulings; none
needed a decision from Dave, and none was guessed at. For contrast, iteration
1's WR-05 *was* held at the reviewer's stated minimum precisely because
closing it fully would have preempted D-IMPL-18 and D-IMPL-27 — that boundary
is unchanged and still carried in `PHASE_I2_GATE.md` §5 as an I.4 item.

IN-06 is the one finding deferred by design rather than by decision-gap: it is
an accepted risk with a named re-examination point (I.3), not an open
question.

---

_Fixed: 2026-07-26_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
