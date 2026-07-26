---
phase: 05-phase-i-2-agent-specialization-framework
reviewed: 2026-07-26T00:00:00Z
depth: standard
files_reviewed: 50
files_reviewed_list:
  - docs/PHASE_I2_GATE.md
  - src/ccf/agents/agent.py
  - src/ccf/agents/archetypes.py
  - src/ccf/agents/composition.py
  - src/ccf/agents/definitions.py
  - src/ccf/agents/errors.py
  - src/ccf/agents/factory.py
  - src/ccf/agents/__init__.py
  - src/ccf/agents/prompts.py
  - src/ccf/controlplane/artifacts.py
  - src/ccf/controlplane/audit.py
  - src/ccf/controlplane/registry.py
  - src/ccf/replay/record.py
  - src/ccf/skills/catalog.py
  - src/ccf/skills/dispatch.py
  - src/ccf/skills/grants.py
  - src/ccf/skills/__init__.py
  - tests/agents/harness_double.py
  - tests/agents/test_agent.py
  - tests/agents/test_archetypes.py
  - tests/agents/test_composition.py
  - tests/agents/test_consumption_discipline.py
  - tests/agents/test_definitions.py
  - tests/agents/test_factory.py
  - tests/agents/test_prompts.py
  - tests/agents/test_schema_export.py
  - tests/conformance/test_approval_sink.py
  - tests/controlplane/test_hash_verified_bump.py
  - tests/controlplane/test_registry.py
  - tests/fixtures/banking/agents/covenant_analytics.yaml
  - tests/fixtures/banking/agents/deal_monitor_assembler.yaml
  - tests/fixtures/banking/prompts/covenant_summary.yaml
  - tests/fixtures/banking/skills/callables.py
  - tests/fixtures/banking/skills/covenant_metrics_tool.yaml
  - tests/fixtures/banking/skills/document_fetch_mcp.yaml
  - tests/fixtures/banking/skills/grants.yaml
  - tests/fixtures/banking/tasks/covenant_review_task.yaml
  - tests/integration/test_agent_slice.py
  - tests/integration/test_proto_quickstart.py
  - tests/invariants/test_replay_by_construction.py
  - tests/lints/conftest.py
  - tests/lints/test_cinv01c_behavioral.py
  - tests/replay/test_serve_writes_replay.py
  - tests/skills/__init__.py
  - tests/skills/sinks.py
  - tests/skills/test_catalog.py
  - tests/skills/test_dispatch.py
  - tests/skills/test_grants.py
  - tools/lints/no_hardcoding.py
findings:
  critical: 0
  warning: 5
  info: 6
  total: 11
status: issues_found
---

# Phase 5 (I.2): Code Review Report — Re-Review After Gap Closure

**Reviewed:** 2026-07-26
**Depth:** standard
**Files Reviewed:** 50
**Status:** issues_found

## Summary

Re-review after gap-closure plans 05-08/05-09/05-10. The prior review's findings are
verified closed: the D-07 grant-set hash is per-agent (CR-01), `grant_set_hash` is a
required argument with `FalseGrantClaimError` on false zero-grants claims (WR-01),
`TenantMismatch` refuses cross-tenant grants (WR-02), `BoundSkillView` is the only
admissible `bound_skills` type (WR-03), catalog resolution runs before ledger mutation
for the missing-entry case (WR-04), `GrantCollisionError` fires on double-effective
same-name grants (WR-05), the CINV-01c substring exemption is replaced by an exact-path
allowlist with import-alias tracking (WR-06), a shared `AuditLog` can be injected into
the registry (WR-07), `AmbiguousPinnedVersionError` + unaudited `peek` handle
declared-version matching (WR-08), and IN-03/IN-08 are fixed as described. Regression
tests exist for each and are well targeted.

However, the gap-closure changes themselves left new (or newly-visible) defects. The
most significant: the WR-04 "no wedged states" fix covers only the catalog-resolution
failure path — the grant state machine can still be permanently wedged in `requested`
or `pending-approval` by exceptions raised *after* state mutation (new WR-01 below);
and the state machine's own documented remediation ("issue a new grant artifact") is
blocked by the D-05 empty-bump refusal for a version-bump-only re-issue (new WR-02
below). No critical finding: none of these is a security vulnerability or data-loss
path, but the warnings below should be fixed or explicitly triaged before the gate.

## Warnings

### WR-01: Grant state machine can still wedge in `requested` / `pending-approval` — exception paths after state mutation

**File:** `src/ccf/skills/grants.py:603-663`
**Issue:** The prior WR-04 fix moved *catalog* resolution before state mutation, but two
other failure paths mutate state first and can then raise, leaving the grant permanently
wedged with no defined recovery transition (revoke is defined from `effective` only;
re-request raises `GrantTransitionError`):

1. `_tier_1` → `_resolve_policy_regime` can raise `AmbiguousPinnedVersionError`
   (documented in its own docstring, line 456) *after* `self._states[grant_hash] =
   "requested"` (line 603). The grant is stuck in `requested` forever.
2. `self._sink.decide(grant)` (line 638) is arbitrary user/Protocol code. If it raises,
   the grant is stuck in `pending-approval` forever. Nothing in the `ApprovalSink`
   contract forbids raising, and the ledger does not guard the call.

This is the same defect class the prior WR-04 was raised for, incompletely closed. The
gate document's "no wedged `requested` grants" claim (PHASE_I2_GATE.md §3) is therefore
overstated.
**Fix:** Either resolve the policy regime *before* state mutation (mirroring the
catalog fix — regime resolution has no dependency on ledger state), or wrap the
post-mutation section so any exception records a refusal before re-raising:

```python
self._states[grant_hash] = "requested"
try:
    verdict = self._tier_1(grant, definition, entry)
    ...
    outcome = self._sink.decide(grant)
except Exception:
    self._states[grant_hash] = "refused"
    self._record(grant, "grant_refused", resolved=False, actor=actor)
    raise
```

### WR-02: Documented remediation "issue a new grant artifact" is blocked by the D-05 empty-bump refusal

**File:** `src/ccf/skills/grants.py:577-581` (interacting with `src/ccf/controlplane/registry.py:418-433`)
**Issue:** After a tier-2 rejection (approver says "not now"), the natural retry is a
re-issued grant. `GrantTransitionError` explicitly instructs: "a grant artifact is
single-use — issue a new grant artifact." But a re-issued grant with only
`artifact_version` bumped is byte-identical modulo the version field, so
`register_versioned`'s fingerprint check (which normalizes `artifact_version` before
hashing) returns `RefuseEmptyBump`, and `request()` returns that refusal before any
state is recorded. The only working retry path is to also change the grant's `name`
(or another content field), which is documented nowhere and creates a second Control
Plane key for what is conceptually the same grant. `tests/skills/test_grants.py` never
exercises re-request-after-rejection, so the dead end is untested and invisible.
**Fix:** Decide and document the intended retry semantics. Options: (a) exempt
`SKILL_GRANT` from the empty-bump refusal (a grant re-issue is a new *request*, not a
content revision); (b) register grants through `register_typed` (content-hash identity,
no bump check) since grants are single-use requests, not evolving documents; or (c)
amend the `GrantTransitionError` message and module docs to state that a re-issued
grant must differ in `name`. Add a regression test for the rejected-then-retried flow.

### WR-03: `SkillCatalog.resolve` audits phantom resolutions — the WR-08 defect in a sibling path

**File:** `src/ccf/skills/catalog.py:289-294`
**Issue:** Pinned resolution loops over every content version under the key and calls
`self._control_plane.resolve(key, content_version)` — an *audited* resolution — for
every probe, including versions that are not returned. The WR-08 gap closure
established (and `GrantLedger._resolve_policy_regime` / `factory._resolve_pinned`
implement) the discipline that declared-version probing goes through the unaudited
`peek`, with one audited `resolve` on the match, precisely because "auditing those
probes as resolutions would record reads that never happened"
(registry.py:474-476). Every `GrantLedger.request` and every `BoundSkillView` access
routes through this method, so the audit log accumulates `resolve` events for
artifacts nobody read.
**Fix:**

```python
for content_version in self._control_plane.versions(key):
    artifact = self._control_plane.peek(key, content_version)
    entry = SKILL_CATALOG_ENTRY.validate(artifact)
    if version in (entry.artifact_version, content_hash(entry)):
        self._control_plane.resolve(key, content_version)  # audit the real read
        return entry
```

### WR-04: CINV-01c static-alias hole — `A = module.Agent; A(...)` escapes the lint

**File:** `tools/lints/no_hardcoding.py:384-393`
**Issue:** Alias tracking handles `A = Agent` (Assign whose value is `ast.Name`) and
import aliases, but not an assignment whose value is an attribute access:
`import ccf.agents.agent as m` / `A = m.Agent` / `A(...)` yields zero findings — the
Assign's `node.value` is `ast.Attribute`, so `A` never enters `checked_names`, and the
call's `_called_name` returns `"A"`. This is a purely *static* one-line rename, which
contradicts the documented invariant that "the D-12 accepted residual stays *dynamic*
construction only" (module docstring; `tests/lints/test_cinv01c_behavioral.py:118-122`).
**Fix:** Extend the alias pass and add a behavioral fixture test:

```python
if isinstance(node, ast.Assign) and isinstance(node.value, ast.Attribute) \
        and node.value.attr in FACTORY_ONLY_NAMES:
    for target in node.targets:
        if isinstance(target, ast.Name):
            checked_names.add(target.id)
            aliases[target.id] = node.value.attr
```

### WR-05: `GrantLedger` state is volatile while grant artifacts are durable — a restart silently drops every effective grant

**File:** `src/ccf/skills/grants.py:399-400, 694-713`
**Issue:** IN-03 was fixed for the catalog on the principle "registry state is the
single store; no consumer keeps a volatile second index" — but the grant ledger is
exactly such a volatile second index: `_states`/`_grants` are per-instance dicts, while
the grant *artifacts* persist append-only in the registry. A second `GrantLedger` over
the same registry (or the same deployment after a process restart) sees zero effective
grants and `grant_set_hash(...) == NO_GRANTS_SET_HASH`, even though the registry holds
registered grants and `grant_effective` audit events with no subsequent
`grant_revoked`. Grant state is not reconstructible from the single store, and two
ledgers over one registry can disagree about what is in force. Nothing tests or
documents this asymmetry.
**Fix:** Minimum: document the volatility explicitly on `GrantLedger` (in-process,
single-instance, I.2 scope) and pin the intended semantics with a test. Better: derive
state from the `grant_*` audit-event journal / registry on construction, matching the
IN-03 discipline.

## Info

### IN-01: Duplicated pinned-resolution logic with divergent not-found semantics

**File:** `src/ccf/skills/grants.py:424-461`, `src/ccf/agents/factory.py:104-154`
**Issue:** `GrantLedger._resolve_policy_regime` is a near-verbatim copy of
`factory._resolve_pinned` (key derivation, hash fast-path, peek-probe loop, ambiguity
refusal), differing only in the miss case (`None` vs `AgentDefinitionError`). Two
copies of the WR-08 logic will drift.
**Fix:** Extract a shared `resolve_pinned(control_plane, uri) -> object | None` helper
(e.g., in `ccf.controlplane`) and wrap the miss case at each call site.

### IN-02: `Agent` constructor does not validate `identity.definition_uri` coherence

**File:** `src/ccf/agents/agent.py:164-199`
**Issue:** The constructor validates `definition_hash` and `archetype_composition`
against the definition but accepts any `definition_uri`, though the docstring says the
identity block "must agree with `definition`". A drifted URI annotation would be
serialized verbatim into replay dimension 4.
**Fix:** Recompute the expected URI via `artifact_uri(...)` from the definition and
refuse a mismatch, or narrow the docstring claim.

### IN-03: WR-07 shared-audit-log wiring relies on caller discipline

**File:** `src/ccf/skills/grants.py:385-398`
**Issue:** `GrantLedger` takes `audit` as an independent constructor argument; a caller
can pass a log different from `control_plane.audit_log`, silently splitting the
"singular audit plane" the WR-07 closure established. The parameter is redundant given
`ControlPlaneRegistry.audit_log` exists on the injected registry.
**Fix:** Default `audit` to `control_plane.audit_log` (or drop the parameter), or
refuse construction when `audit is not control_plane.audit_log` for the reference
registry type.

### IN-04: Cross-tenant grant documents are permanently registered before the tenant check

**File:** `src/ccf/skills/grants.py:597-625`
**Issue:** `register_versioned` runs before the tenant-coherence check, so a refused
cross-tenant grant is nonetheless appended forever (append-only) under the *foreign*
tenant's key namespace (`other-bank/ccf.skill-grant/...`) in this Control Plane. The
refusal is audited, but the artifact remains resolvable under a tenant prefix the
requesting deployment does not own.
**Fix:** Run the tenant check before registration (it needs only `grant`, `entry`,
`definition`, all already in hand), so an inadmissible cross-tenant document never
enters the registry.

### IN-05: `TaskFactory` class-checks agent steps but not skill steps

**File:** `src/ccf/agents/factory.py:445-468`
**Issue:** The IN-08 fix validates that an `agent` step's ref resolves to
`ccf.agent-definition`, but a `skill` step's ref is accepted whatever class it resolves
to (a prompt artifact, a debt profile). Partly forced — skill targets may be
deployment-declared classes — but the asymmetry is undocumented.
**Fix:** Document the asymmetry in the `construct` docstring, or refuse skill-step refs
that resolve to SDK-owned non-skill classes (`ccf.agent-definition`,
`ccf.prompt-artifact`, `ccf.task-definition`).

### IN-06: `local_callable` dispatch is artifact-driven arbitrary code execution — accepted risk, keep it visible

**File:** `src/ccf/skills/dispatch.py:78-107`
**Issue:** `importlib.import_module` + `getattr` on `callable_ref` executes arbitrary
module code at dispatch time. The T-05-18 trust posture (refs come only from registered
Control Plane artifacts inside the tenant trust boundary) is documented and accepted
for I.2; noted here so the I.3/I.4 threat model re-examines it once refs can arrive via
MCP/A2A artifact stores rather than in-repo fixtures.
**Fix:** Carry forward to the I.3 handoff threat-model item alongside the Jinja2 SSTI
note.

---

_Reviewed: 2026-07-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
