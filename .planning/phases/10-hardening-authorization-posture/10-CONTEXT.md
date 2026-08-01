# Phase 10: Hardening — Authorization & Posture - Context

**Gathered:** 2026-08-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement the Phase-9 rulings exactly: every HITL door (HTTP and MCP) refuses
unauthorized tenants by default with a typed 403 (D-IMPL-68 — scope mapping as
a versioned Control Plane policy artifact, enforced at the doors); every
authorization decision lands in the audit record; the HITL primitives verify
HitlPolicy signed bindings on their resolution surfaces (D-IMPL-69); and
`create_app` emits a loud warning on the insecure default posture (D-IMPL-73 —
`CcfInsecureDefaultWarning` + log record, explicit acknowledgment kwarg, no
env var). Examples 05/06 demonstrate tenant authorization. Requirements:
HARD-04, HARD-05. No item is implemented other than per its ruling.

</domain>

<decisions>
## Implementation Decisions

### Scope-mapping artifact schema (HARD-04, sub-ruling D-IMPL-68 delegated to this phase)
- **D-01:** Tenant-pattern grammar is **exact match + trailing wildcard only**
  (`tenant-a`, `tenant-*` prefix glob). No regex, no mid-string globs.
  Deterministic and greppable; misconfiguration surface minimized.
- **D-02:** Action vocabulary comes from **door-declared action IDs** — each
  HTTP route / MCP tool declares its action identifier; the artifact's
  action-sets are matched against those strings. The SDK ships matching
  mechanism only and invents no scope vocabulary (HARD-04).
- **D-03:** The artifact is a **new dedicated typed class** (e.g.
  `ScopeMappingArtifact`), Pydantic `extra=forbid`, following the existing
  D-IMPL-28 definition-artifact pattern, registered and versioned like other
  Control Plane policy bundles. Not folded into HitlPolicy.
- **D-04:** Versioning uses the **same semver-lane pattern** as other Control
  Plane bundles; the audit record captures the exact artifact version string
  in force at decision time (allow or deny), per the D-IMPL-68 ruling text.

### Authorizer seam & placement (HARD-04)
- **D-05:** `TenantAuthorizerProtocol` and the shared reference interpreter
  both live in **runtime** (e.g. `runtime/ccf_runtime/authz/`), imported by
  both doors. `/src` core untouched — mirrors the D-IMPL-67 auth-hook seam.
- **D-06:** Doors take an **optional authorizer binding** with the same shape
  as the D-IMPL-67 auth hook. Auth bound + authorizer bound → enforce;
  authorizer unbound → the T-07-24 unauthenticated posture is unchanged
  (D-IMPL-68: "governs behavior only when auth is bound").
- **D-07:** The helper **re-resolves the scope-mapping artifact from the
  Control Plane per request** (no cache/TTL) — version changes take effect
  immediately and the exact version lands in the audit record. Matches the
  transport's per-submission HitlPolicy re-resolution posture.
- **D-08:** Refusals share **one refusal-constants module** consumed by both
  doors: the HTTP door renders the typed 403 JSON (errors.py constants
  pattern), the MCP door renders its protocol-native error carrying the same
  code/detail. One vocabulary, two renderings.

### Audit record shape (HARD-04)
- **D-09:** The authorization decision record carries the **full decision
  tuple**: principal/subject, tenant, action, decision (allow/deny), matched
  scope pattern (or none), artifact version, timestamp.
- **D-10:** **Both allows and denials are audited** — refusals are
  security-relevant events (audit-by-construction, CLAUDE.md §8.2).
- **D-11:** Authz decisions **extend the existing HITL audit path**
  (Decision Replay dimensions 2/4 extensions) — the authz record attaches to
  the HITL action it gated. No new replay dimension, no separate log surface.

### Gate verification surfaces (HARD-05, D-IMPL-69)
- **D-12:** Verification lands on **all human-action surfaces**:
  `ApprovalGate.resolve`, OverrideBoundary's override entry, ReviewQueue's
  release/decision path, ExceptionEscalation's human handoff. Close the
  class, not just the audited instance.
- **D-13:** **Both layers verify, idempotently** — transport `submit` and
  primitive resolve each verify independently (defense in depth; read-only
  check). No verified-marker plumbing between layers (a forgeable marker is
  a bypass vector).
- **D-14:** Primitives **reuse the existing refusal types**
  (`SignedBindingRequiredRefused` / `SignedBindingInvalidRefused`) per the
  D-IMPL-69 ruling text — no new subclasses.

### create_app warning + examples (HARD-05)
- **D-15:** D-IMPL-73 is fully ruled — implement exactly:
  `CcfInsecureDefaultWarning` (warnings.warn) + logging WARNING record, with
  an explicit acknowledgment kwarg as the single suppression surface. No
  environment variable.
- **D-16:** **Examples 05 and 06 are extended in place** with scope-mapping
  artifacts + authorizer binding, demonstrating one authorized and one
  refused path; READMEs updated. The D-14 (Phase 9) byte-identity manifest is
  deliberately re-baselined for these two examples only — a conscious,
  documented regeneration, not drift.

### Claude's Discretion
- Exact module/file names inside `runtime/ccf_runtime/authz/`, the artifact
  class name, and the kwarg name for the D-IMPL-73 acknowledgment — follow
  house naming conventions.
- Cross-door × cross-action test-matrix mechanics (parametrization shape),
  provided the matrix covers both doors × all door actions × allow/deny.
- TokenGrant scope-string format interpretation, consistent with D-IMPL-68's
  "tenant × action grammar never hardcoded" constraint.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Rulings (binding — implement exactly per these)
- `docs/DECISIONS.md` — D-IMPL-68 (WR-01 mapping shape), D-IMPL-69
  (ApprovalGate×D-16 composition), D-IMPL-73 (create_app warning); also
  D-IMPL-67 (auth hook seam), D-16 (signed bindings)
- `docs/09-ruling-batch-minicycle.md` — items 1, 2, 6: full options analysis
  and consequences behind the three rulings

### Project invariants
- `CLAUDE.md` §8.2 (HITL audit-by-construction), §8.3 (Experience doors),
  §11 (mechanism-not-values, No-Hardcoding), §6.4 (definition artifacts)

### Code surfaces this phase touches
- `runtime/ccf_runtime/http_api/app.py` — `create_app` (D-IMPL-73 target)
- `runtime/ccf_runtime/http_api/auth.py` + `errors.py` — D-IMPL-67 auth hook
  and typed-constants refusal pattern to mirror
- `src/ccf/hitl/transport.py` — D-16 verification pattern to reuse on
  primitive resolve paths (verification stays outside the Phase-9 lock)
- `src/ccf/hitl/primitives.py` — resolution surfaces gaining verification
- Prior phase context: `.planning/phases/09-hardening-defect-fixes-ruling-batch/09-CONTEXT.md`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- D-IMPL-67 auth-hook binding shape (`http_api/auth.py`, `TokenGrant`,
  `TokenSourceProtocol`): the authorizer binding mirrors this seam.
- `http_api/errors.py` typed-constants pattern: the 403 refusal reuses it;
  the shared refusal-constants module generalizes it across doors.
- Transport D-16 verification (`SignedBindingRequiredRefused` /
  `SignedBindingInvalidRefused`): same types raised from primitive resolve.

### Established Patterns
- Control Plane artifacts: Pydantic `extra=forbid`, semver lanes, registry
  resolution per request (HitlPolicy precedent).
- Phase 9's D-05/D-08: Protocol docstrings carry behavioral contracts; the
  transport stays a pure queue — authorization never sinks below the door
  trust boundary.

### Integration Points
- HTTP door routes and MCP server tool handlers (where identity is verified
  per D-IMPL-67) are the sole enforcement points.
- Audit path: the existing HITL audit record surface, extended with the
  authz decision tuple.

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond the rulings — the three D-IMPL entries and
the mini-cycle document are the definitive shape.

</specifics>

<deferred>
## Deferred Ideas

- Free-threaded-Python variant of the concurrency hammer (Phase 9 review
  carry-forward — advisory tech-debt, not Phase 10 scope).
- Typed-error compatibility note and Protocol thread-safety obligation for
  adopter docs — Phase 14 (from Phase 9 cross-AI review consensus).
- Per-call executor overhead in `run_coroutine_sync` — revisit with Phase 11
  measured data.

</deferred>

---

*Phase: 10-hardening-authorization-posture*
*Context gathered: 2026-08-01*
