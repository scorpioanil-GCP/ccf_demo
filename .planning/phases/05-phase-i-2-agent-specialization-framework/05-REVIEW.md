---
phase: 05-phase-i-2-agent-specialization-framework
reviewed: 2026-07-26T00:00:00Z
depth: standard
files_reviewed: 48
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
  critical: 1
  warning: 8
  info: 8
  total: 17
status: issues_found
---

# Phase 5 (I.2 — Agent Specialization Framework): Code Review Report

**Reviewed:** 2026-07-26
**Depth:** standard
**Files Reviewed:** 48
**Status:** issues_found

## Summary

The I.2 slice is well-disciplined overall: the No-Hardcoding boundary genuinely holds (all
domain values in `tests/fixtures/banking/`), archetype/agent separation is real, the D-05
bump check and D-IMPL-19 composition rules match their rulings, and the test suite is
substantive rather than decorative. However, the grant machinery — the audit-critical
centerpiece of this phase — has a correctness defect in the D-07 grant-set identity
(ledger-wide, not per-agent), several governance seams that the mechanism does not actually
close (arbitrary `bound_skills` injection, cross-tenant grants, silent no-grants default in
dimension 4), a state-machine dead end, and holes in the CINV-01c lint that is designated
the "mechanism of record." None of these are caught by the current tests because every test
world holds exactly one agent, one tenant, and well-behaved callers.

## Critical Issues

### CR-01: `GrantLedger.grant_set_hash()` is ledger-wide, not per-agent — dimension 4 records the wrong in-force skill-set whenever more than one agent has grants

**File:** `src/ccf/skills/grants.py:585-603` (`effective_hashes`, `grant_set_hash`)
**Issue:** `effective_hashes()` collects **every** effective grant in the ledger regardless
of `agent_definition_hash`, and `grant_set_hash()` hashes over that set. But the value is
documented and consumed as *this agent's* in-force skill-set: `tests/integration/test_agent_slice.py:369`
passes `ledger.grant_set_hash()` into `agent.perspective_conditioning(...)`, which lands it
verbatim in replay dimension 4 as "the skill-set in force" for that agent (CLAUDE.md §6.2:
"a decision replays against the skills the agent actually had"). Contrast
`_effective_entries()` (line 605), which correctly filters by `agent_definition_hash` — the
binding view is per-agent, the identity hash is not. The moment a deployment runs two agents
against one ledger (the normal case — the ledger is the Control Plane grant machinery, not a
per-agent object), every decision's dimension-4 `grant_set_hash` includes other agents'
grants, and a grant to agent B changes the recorded skill-set identity of agent A's
decisions. That is incorrect replay data written by construction. All I.2 tests use one
agent per ledger, so the suite cannot see it.
**Fix:**
```python
def effective_hashes(self, agent_definition_hash: str | None = None) -> frozenset[str]:
    return frozenset(
        h for h, state in self._states.items()
        if state == "effective"
        and (agent_definition_hash is None
             or self._grants[h].agent_definition_hash == agent_definition_hash)
    )

def grant_set_hash(self, agent_definition_hash: str) -> str:
    active = self.effective_hashes(agent_definition_hash)
    return NO_GRANTS_SET_HASH if not active else grant_set_hash(active)
```
and update the call site in the slice test to pass `content_hash(definition)`. Add a
two-agent test asserting agent A's hash is unaffected by a grant to agent B.

## Warnings

### WR-01: `Agent.perspective_conditioning` defaults `grant_set_hash` to the positive "no-grants" claim — a skilled agent's caller who omits the argument records a *false* positive assertion

**File:** `src/ccf/agents/agent.py:290-312`
**Issue:** `grant_set_hash: str = NO_GRANTS_SET_HASH` means the API's path of least
resistance for an agent that *does* hold effective grants is to silently record "this
decision ran under zero grants" — a positive, wrong claim in the audit record, which is
worse than an absent field (the entire rationale for the sentinel, per `record.py:66-70`,
is that a positive claim is trustworthy). The gate package (docs/PHASE_I2_GATE.md row 6)
calls skill-set capture "by construction"; it is actually by caller discipline. Nothing
prevents `agent.perspective_conditioning(principal_id=p)` on a granted agent.
**Fix:** Make `grant_set_hash` a required keyword argument (callers of ungranted agents
pass `NO_GRANTS_SET_HASH` explicitly), or have the method refuse the default when
`self._bound_skills` is non-empty — the agent already knows, without re-deriving hashes,
that "no-grants" cannot be true.

### WR-02: No tenant-coherence check anywhere on the grant path — cross-tenant grants are admissible

**File:** `src/ccf/skills/grants.py:468-554` (`request`), `src/ccf/agents/agent.py:240-276` (`invoke_skill`)
**Issue:** `SkillGrant.tenant` is never compared to `definition.tenant`; the catalog entry
is resolved under `grant.tenant` (line 515-517), and tier 1 only does subset logic over
scopes/products. A grant with `tenant: other-bank` naming another tenant's catalog entry
binds cleanly to an `acme-bank` agent as long as the identifiers happen to be subsets.
`Agent.consume` enforces tenant isolation strictly (line 227-231); the skilling channel —
the channel that confers *capabilities* — enforces none. Given the SDK's multi-tenant
posture (compound `(tenant_id, entity_uri)` identity, per-tenant trust boundary), this is a
tenant-isolation gap in mechanism, not a deployment value.
**Fix:** In `GrantLedger.request`, refuse (as a `GrantTransitionError` — broken wiring, or a
typed tier-1 refusal) when `grant.tenant != definition.tenant`, and verify
`entry.tenant == definition.tenant` after catalog resolution.

### WR-03: `AgentFactory.construct(bound_skills=...)` accepts any mapping of any objects — the two-tier governance is structurally bypassable at the supported construction path

**File:** `src/ccf/agents/factory.py:212-280`, `src/ccf/agents/agent.py:240-276`
**Issue:** `bound_skills: Mapping[str, object]` is passed through unchecked. A caller can
hand the factory `{"anything": some_catalog_entry}` (or any object — introspection returns
it verbatim from `invoke_skill(name)`) and the agent will treat it as a bound capability,
with no grant artifact, no tier-1 check, no audit event, and no dimension-4 capture. The
CINV-01c lint guards `Agent(...)` construction, not this parameter, so this is the
legitimate front door defeating channel-2 governance silently. "Skills the agent has not
been granted do not exist" (CLAUDE.md §7.3 seam 2) holds only if the mapping came from
`GrantLedger.bound_view` — nothing enforces or even type-narrows that.
**Fix:** Type the parameter as the ledger view (accept `Mapping[str, SkillCatalogEntry]` at
minimum and validate entry types/tenants at construction), or better, accept
`(ledger: GrantLedger, ...)` / a dedicated `BoundSkillView` type whose only producer is the
ledger — the same capability-typing move `DeliveryCapability` already makes for replay.

### WR-04: `GrantLedger.request` wedges a grant in `requested` state when the catalog entry is missing, then reports it as "already decided"

**File:** `src/ccf/skills/grants.py:505-518, 491-497`
**Issue:** The sequence is: register artifact → set state `requested` → audit → **then**
`catalog.resolve(...)`, which raises `SkillNotInCatalog`. The exception propagates after
state mutation, leaving the grant permanently in `requested`: re-requesting the same grant
raises `GrantTransitionError` claiming it "was already decided ('requested')" — it was
never decided — and `revoke` is undefined from `requested`. A transient deployment error
(entry registered a minute later) permanently burns that grant's content hash; the operator
must author a new grant artifact and gets a misleading error explaining why. There is also
no audit record of the failure (`grant_requested` resolved=True is the last event), so the
audit plane says a request is pending that can never resolve.
**Fix:** Resolve the catalog entry *before* mutating `self._states`/`self._grants` (it needs
nothing from them), or catch the lookup failure, transition to `refused`/roll back, and
audit it. Also correct the `GrantTransitionError` message to distinguish "already seen"
from "already decided."

### WR-05: `_effective_entries` silently drops a grant when two effective grants bind the same `skill_name`

**File:** `src/ccf/skills/grants.py:605-616`
**Issue:** Entries are keyed by `grant.skill_name`; iteration order is `sorted(grant hashes)`
— deterministic but semantically arbitrary. Two effective grants for the same agent naming
the same skill at different versions (the documented upgrade flow: "upgrading a skill is a
new entry version and a new grant") resolve to whichever grant's hash sorts last, silently.
During an upgrade window (new grant effective, old not yet revoked) the bound version is
hash-lottery, and the dimension-4 grant-set hash includes both while dispatch uses one.
**Fix:** Detect the collision and raise a typed error (two effective grants for one
skill name on one agent is a governance-state defect), or define last-granted-wins by
ledger order and record the shadowing as a typed fact.

### WR-06: CINV-01c lint has static holes: `from x import Agent as A` bypass, and the `"factory"` path marker exempts any module that puts "factory" anywhere in its path

**File:** `tools/lints/no_hardcoding.py:82-84, 275, 349-379`
**Issue:** D-12 makes this lint "the no-bypass mechanism of record," with *dynamic*
construction the only accepted residual. Two purely static bypasses exist: (1) alias
tracking covers only module-level `A = Agent` assignments; `from ccf.agents.agent import
Agent as A` followed by `A(...)` is invisible (`_called_name` sees `A`, the `ast.Assign`
scan never sees the import) — that is a one-line static rename, exactly the hole the alias
extension claims to close. (2) `in_factory_module` is `"factory" in path-or-module-name`
(substring, lowered), so `my_factory_helpers.py`, anything under a `factories/` directory,
or a module literally named `bypass_factory.py` is fully exempt from the rule —
`tests/lints/test_cinv01c_behavioral.py:59-64` demonstrates the exemption fires on the name
alone. The mechanism of record is narrower than its ruling.
**Fix:** Track `ast.ImportFrom`/`ast.Import` aliases of `Agent`/`Task` into `checked_names`;
replace the substring marker with an explicit allowlist of factory module paths
(`src/ccf/agents/factory.py`), which is one line and cannot be satisfied by naming.

### WR-07: Grant lifecycle audit events and Control Plane audit events live in two disjoint logs with independent sequences

**File:** `src/ccf/skills/grants.py:326-361`, `src/ccf/controlplane/registry.py:177-203`
**Issue:** `ControlPlaneRegistry` constructs its own private `AuditLog`; `GrantLedger` takes
a second, injected one. A single `request()` therefore writes its `register_versioned`
event into the registry's log and its `grant_requested`/`grant_effective` events into the
ledger's log, with unrelated sequence numbers and (in principle) different clocks — the
tests inject the same instant into both, masking it. Whitepaper §7.8.2 says the Control
Plane *is* the audit plane, singular: an examiner reading `registry.audit_events()` sees a
grant artifact registered and no lifecycle; one reading the ledger log sees transitions with
no registration. The gate package (row 7: "through the one existing AuditLog") describes a
property the code does not have.
**Fix:** Have `ControlPlaneRegistry` accept an injected `AuditLog` (defaulting to a fresh
one) and pass the same instance to `GrantLedger` at composition time — one log, one
sequence, one clock; or expose the registry's log so the ledger writes into it.

### WR-08: Pinned resolution is ambiguous for `register_typed`-path artifacts — the same declared semver can name two different contents, and `_resolve_pinned` silently returns the oldest

**File:** `src/ccf/agents/factory.py:92-127`, `src/ccf/skills/grants.py:365-386`, `src/ccf/controlplane/registry.py:229-277`
**Issue:** The D-05 bump check applies only to `register_versioned`. Policy bundles, debt
profiles, and every `DeclaredArtifact` register through `register_typed`, which happily
appends two different contents both declaring `semver: "1.1.0"` under one key. Both
`_resolve_pinned` and `_resolve_policy_regime` match the URI version against each
registered artifact's declared `semver` in oldest-first order and return the **first**
match — so a "pinned" `ccf-artifact://...@1.1.0` ref resolves to different content
depending on registration history, silently. That is exactly the moving-target shape
D-IMPL-26 exists to forbid, on the axis-4/axis-5 refs that gate tier-1 governance. (Side
effect of the same loop: every non-matching probe emits a resolved=True `resolve` audit
event, so the audit log records reads of versions the factory only probed.)
**Fix:** On a declared-version match, continue scanning and raise a typed ambiguity error if
a second content matches the same declared version; longer-term, route declared artifacts
through a bump-checked path or resolve by content hash internally.

## Info

### IN-01: `docs/PHASE_I2_GATE.md` overstates two mechanisms

**File:** `docs/PHASE_I2_GATE.md:78-79`
**Issue:** Row 6 ("skill-set capture ... by construction") is caller-discipline (WR-01), and
row 7 ("the one existing AuditLog") is two logs (WR-07). Gate prose should match mechanism.
**Fix:** Reword after fixing, or fix the mechanisms.

### IN-02: Stale `pragma: no cover` in the harness double

**File:** `tests/agents/harness_double.py:52`
**Issue:** The `else` branch ("unreachable until grants land (05-05)") is now reachable —
grants landed; `invoke_skill(name)` on a granted name returns the entry and sets
`unbound = None`. The comment documents a state two waves old.
**Fix:** Update the comment; consider a granted-path drive assertion.

### IN-03: `SkillCatalog.discover` reads a per-instance `_keys` index, not registry state

**File:** `src/ccf/skills/catalog.py:229-268`
**Issue:** A second `SkillCatalog` over the same registry (or any restart) discovers
nothing, despite the class docstring's "never a second store" claim — the membership index
is exactly a second store, and it is volatile.
**Fix:** Derive discovery from the registry (e.g., keys whose bound class is
`SKILL_CATALOG_ENTRY.class_id` via `artifact_class_of`), or document the limitation.

### IN-04: `register_versioned` bump history is blind to prior `register_typed` content under the same key

**File:** `src/ccf/controlplane/registry.py:339-387`
**Issue:** `_bumps` is populated only by the versioned path; content previously stored via
`register_typed` under the same key never participates in the four-outcome table, so a
"changed content, unchanged version" drift across the mixed paths is not refused.
**Fix:** Refuse `register_versioned` on a key that already has non-bump-tracked versions, or
seed `_bumps` from existing versions' declared fields.

### IN-05: CINV-01a exempts any string containing `://`

**File:** `tools/lints/no_hardcoding.py:197-207` (`_is_prose_candidate`)
**Issue:** A prompt-shaped literal that embeds any URL (`"You are ... see https://..."`)
skips scoring entirely. Prompts routinely contain URLs.
**Fix:** Only skip when the *whole* stripped string is a URI (no spaces already handles most
of that case; drop the substring check or require `stripped.startswith`).

### IN-06: `ALLOWED_CCF_PREFIXES` matches on raw `startswith` without a module-boundary dot

**File:** `tests/agents/test_consumption_discipline.py:53-66, 107`
**Issue:** `"ccf.contractsx"` or `"ccf.productsomething"` would pass the allowlist guard.
Theoretical today, but the guard is load-bearing for invariant row 9.
**Fix:** Compare against `prefix` == module or `module.startswith(prefix + ".")`.

### IN-07: `tests/agents/test_agent.py` constructs `Agent` directly, outside the lint's tree and contrary to CLAUDE.md §6.4's "tests construct agents the same way"

**File:** `tests/agents/test_agent.py:83-93`
**Issue:** The divergence is acknowledged in the module docstring (constructor-validation
unit tests need direct construction, and the lint scopes to `/src`, `/runtime`,
`/examples`), but CLAUDE.md §6.4 states tests use the factory from fixture artifacts. This
is a documented rule deviation that should be recorded as such (advisory triage / gate
note) rather than left implicit in a test docstring.
**Fix:** Note the scoping decision in the gate package or DECISIONS advisory carry-forward.

### IN-08: `TaskFactory` resolves step refs for existence but never validates the resolved artifact against the step kind

**File:** `src/ccf/agents/factory.py:415-420`
**Issue:** An `agent` step whose ref resolves to a debt profile (or any registered artifact)
constructs cleanly; the mismatch surfaces only in I.4 when execution lands. Cheap to catch
now: the Control Plane already knows each key's bound artifact class.
**Fix:** For `agent` steps, assert `artifact_class_of(key) == AGENT_DEFINITION.class_id`
(and similarly if/when skills gain a canonical class), refusing with `AgentDefinitionError`.

---

_Reviewed: 2026-07-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
