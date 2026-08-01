---
phase: 10-hardening-authorization-posture
reviewed: 2026-08-01T00:00:00Z
depth: standard
files_reviewed: 41
files_reviewed_list:
  - examples/05-workflow-hitl/artifacts/scope_mapping.yaml
  - examples/05-workflow-hitl/artifacts/tokens.yaml
  - examples/05-workflow-hitl/README.md
  - examples/05-workflow-hitl/run.py
  - examples/06-decision-replay/artifacts/scope_mapping.yaml
  - examples/06-decision-replay/artifacts/tokens.yaml
  - examples/06-decision-replay/README.md
  - examples/06-decision-replay/run.py
  - runtime/ccf_runtime/authz/artifact.py
  - runtime/ccf_runtime/authz/__init__.py
  - runtime/ccf_runtime/authz/protocol.py
  - runtime/ccf_runtime/authz/refusals.py
  - runtime/ccf_runtime/cli/main.py
  - runtime/ccf_runtime/http_api/app.py
  - runtime/ccf_runtime/http_api/errors.py
  - runtime/ccf_runtime/http_api/routes/hitl.py
  - runtime/ccf_runtime/mcp/hitl_server.py
  - src/ccf/controlplane/audit.py
  - src/ccf/hitl/approval_gate.py
  - src/ccf/hitl/escalation.py
  - src/ccf/hitl/override.py
  - src/ccf/hitl/review_queue.py
  - src/ccf/hitl/transport.py
  - tests/authz/test_authz_audit.py
  - tests/authz/test_scope_mapping_artifact.py
  - tests/authz/test_tenant_authorizer.py
  - tests/cli/test_cli.py
  - tests/crossproc/test_fastmcp_resource_token_spike.py
  - tests/crossproc/test_mcp_tenant_authz.py
  - tests/hitl/test_approval_gate.py
  - tests/hitl/test_escalation.py
  - tests/hitl/test_override.py
  - tests/hitl/test_review_queue.py
  - tests/hitl/test_signed_binding_authority.py
  - tests/hitl/test_was_called_derivation.py
  - tests/http_api/conftest.py
  - tests/http_api/test_auth.py
  - tests/http_api/test_hitl_door_identity.py
  - tests/http_api/test_insecure_default_warning.py
  - tests/http_api/test_tenant_authz.py
findings:
  critical: 1
  warning: 6
  info: 5
  total: 12
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-08-01
**Depth:** standard
**Files Reviewed:** 41
**Status:** issues_found

## Summary

The HARD-04 authorization work is largely sound: the scope-mapping artifact
validates its grammar at registration, `ControlPlaneTenantAuthorizer` is
genuinely deny-by-default (unregistered mapping, absent scope, unmatched
tenant, and unmatched action each yield `allowed=False`, all confirmed by
tests), both doors carry the shared `ERROR_TENANT_UNAUTHORIZED` constant,
and both allow and deny outcomes are audited with the exact artifact
version. The insecure-default warning mechanism matches its ruling
(construction-time warning + once-only log record, single kwarg suppression
surface).

However, the phase's explicit thread-safety focus is not fully discharged.
The one Control Plane `AuditLog` — now written on **every request** by the
authorizer from FastAPI's threadpool — has an unsynchronized sequence-number
assignment, and the HITL primitives keep unsynchronized side-band state
(`_triggers`/`_originals`/`_items`) plus a non-atomic drain-and-requeue
consume that races against the very concurrent-door traffic the transport
Protocol's WR-02 contract anticipates. Several smaller correctness and
posture gaps are listed below.

## Critical Issues

### CR-01: `AuditLog.append` is not thread-safe, and Phase 10 puts it on every request path

**File:** `src/ccf/controlplane/audit.py:225-271`
**Issue:** `append()` computes `sequence=len(self._events)` and then
`self._events.append(event)` with no lock. Before Phase 10 the log was
written mainly from single-threaded composition paths; `ControlPlaneTenantAuthorizer.authorize()`
(`runtime/ccf_runtime/authz/protocol.py:174`) now appends **one event per
HTTP/MCP request**, and the HTTP HITL handlers are sync `def` routes that
FastAPI executes on a threadpool — so concurrent appends race by
construction in any real deployment. Two racing appends can both read the
same `len()` and produce **duplicate sequence numbers**, defeating the
documented contract ("Monotonic position in the log. Gaps are detectable")
and, since sequence collisions are indistinguishable from tampering or loss,
undermining the audit record the whole HARD-04 design leans on
(D-09/D-10/WR-07). The transport got a lock in Phase 9 for exactly this
concurrency mode; the audit log it feeds did not.
**Fix:**
```python
def __init__(self) -> None:
    self._events: list[AuditEvent] = []
    self._lock = threading.Lock()

def append(self, *, ...) -> AuditEvent:
    with self._lock:
        event = ...  # sequence=len(self._events)
        self._events.append(event)
        return event

def events(self) -> tuple[AuditEvent, ...]:
    with self._lock:
        return tuple(self._events)
```

## Warnings

### WR-01: HITL primitives' side-band state diverges from the transport — bare `KeyError` after authority-path mutation

**File:** `src/ccf/hitl/escalation.py:268,325,430`; `src/ccf/hitl/override.py:183,211,313`; `src/ccf/hitl/review_queue.py:210,238,382`
**Issue:** `ExceptionEscalation._triggers`, `OverrideBoundary._originals`,
and `ReviewQueue._items` are plain instance dicts keyed by
`(tenant, event_key)`, while the pending events live on the injected
transport. If `resolve()` runs on a different primitive instance than the
one that enqueued (process restart, second worker, any deployment where the
transport is shared/durable — the stated point of the transport Protocol),
the event is found pending on the transport but the dict `.pop()` raises a
**bare `KeyError`** — and it raises **after** `transport.submit()` and
`_consume()` have already recorded the human action and consumed the event.
State is mutated, then the resolution crashes untyped: no
`EscalationResolution`, no dimension-2 block, no `hitl_action` audit record
for a submission that *did* land on the authority path. The dicts are also
unsynchronized against concurrent resolves (no lock, unlike the transport).
**Fix:** Pop (or at least check) the side-band entry **before** touching the
transport, and surface absence as the typed `Unknown*EventError` ("broken
wiring") instead of `KeyError`; guard the dicts with a lock or fold this
state into the transport contract so the pending event carries it.

### WR-02: `_consume` drain-and-requeue is non-atomic — concurrent doors observe a partially drained queue and duplicate resolves double-submit

**File:** `src/ccf/hitl/approval_gate.py:363-378` (and the identical helpers in `escalation.py:451-461`, `override.py:335-345`, `review_queue.py:397-407`)
**Issue:** Consume is implemented as a loop of individual
`dequeue`/`enqueue` calls. Each call is individually locked by
`InMemoryHitlTransport`, but the sequence is not: while a resolve drains the
tenant queue, a concurrent `GET /hitl/queue` (or MCP queue read) sees an
empty or partially drained queue for events that are not resolved; a
concurrent `enqueue` interleaves into the drain and lands out of order; and
two concurrent `resolve()` calls for the same event both pass the
`pending()` existence check (a snapshot), both `submit()` — **two authority
submissions and two audit records for one human action** — before one of
them fails on the WR-01 `pop`. The Protocol's own WR-02 concurrency note
says the doors race by construction; the primitives built on it do not
honor that.
**Fix:** Add an atomic `remove(tenant, event_key)` (or compare-and-consume)
operation to the transport Protocol, implemented under the transport's lock,
and make resolve claim the event atomically *before* submitting.

### WR-03: D-01 grammar accepts a bare `*` (grant-every-tenant) and the empty-string pattern

**File:** `runtime/ccf_runtime/authz/artifact.py:75-89`
**Issue:** The validator only rejects `*` occurring in `pattern[:-1]`. The
pattern `"*"` passes (`"*"[:-1]` is `""`) and `tenant_pattern_matches("*", t)`
is `startswith("")` — true for **every tenant**. `""` also passes as an
exact match on the empty tenant. The module docstring and tests claim the
grammar admits "`'tenant-a'` and `'tenant-*'` shapes only," and the test
suite never exercises `"*"`. A one-character artifact typo silently becomes
an all-tenant grant on a security boundary whose selling point is that
malformed patterns are "refused at registration."
**Fix:** In `_patterns_satisfy_the_d01_grammar`, additionally reject empty
patterns and the bare `"*"` (require a non-empty literal prefix before the
trailing glob), or — if grant-all is intended — document and test it
explicitly as a deliberate shape.

### WR-04: A near-miss artifact under the mapping key aborts authorization with no audit record

**File:** `runtime/ccf_runtime/authz/protocol.py:147-153`
**Issue:** When the registered artifact is not a `ScopeMappingArtifact`,
`authorize()` raises `TypeError` **before** the audit append at line 174.
The module contract says "Every decision — allow and deny alike — appends
one `authz_decision` event"; on this path an authorization *attempt* by a
named principal against a named tenant leaves zero trace in the audit
plane, and the door surfaces a 500. The neighboring failure mode
(`ControlPlaneMissing`) is carefully audited as a deny; this one is not,
even though a misregistered mapping is exactly the misconfiguration window
in which an examiner would want the attempt log.
**Fix:** Audit the attempt (e.g., `resolved=False` with the resolved
version) before raising, or convert the near-miss into an audited deny and
log the wiring error separately.

### WR-05: Authorizer bound with auth unbound is silently inert — no counterpart to the D-IMPL-73 warning

**File:** `runtime/ccf_runtime/http_api/routes/hitl.py:115`, `runtime/ccf_runtime/http_api/app.py:117-156`
**Issue:** `_enforce_tenant_authz` returns immediately when `grant is None`,
so `create_app(deps, authorizer=...)` **without** `auth=` enforces nothing
— confirmed by `test_authorizer_bound_but_auth_unbound_is_inert`. This is
the ruled D-06 posture, but unlike the plain insecure default it is a
configuration in which the operator has *explicitly expressed intent to
authorize* and gets zero enforcement with zero signal: the
`CcfInsecureDefaultWarning` fires for `auth=None` generally, but nothing
distinguishes "you passed an authorizer that can never run." A deployment
that wires the scope mapping, registers the artifact, and forgets the auth
hook ships wide open while believing it is tenant-scoped.
**Fix:** In `create_app`, when `authorizer is not None and auth is None`,
raise or emit a dedicated warning (same pattern as
`CcfInsecureDefaultWarning`) naming the dead authorizer.

### WR-06: Hardcoded tenant literal (dead branch) in example 05 driver

**File:** `examples/05-workflow-hitl/run.py:325-328`
**Issue:** `_replay_execution` contains
`tenant_id="sterling-mutual" if "tenant" not in replay_doc else replay_doc["tenant"]`.
`main()` always sets `replay_doc["tenant"]`, so the `"sterling-mutual"`
literal is dead code — but it is a domain tenant value inline in example
code, which the file's own header ("Every domain value … is loaded from
`artifacts/*.yaml`") and the No-Hardcoding Rule (CLAUDE.md §6.4, CI-lint
enforced for `/examples`) both forbid. Example 06 has no equivalent.
**Fix:**
```python
view=GraphView(tenant_id=replay_doc["tenant"], as_of=boundary),
```
(and let a missing key fail loudly, as elsewhere in the driver).

## Info

### IN-01: `_consume` and `_record` duplicated verbatim across all four HITL primitives

**File:** `src/ccf/hitl/approval_gate.py:363-391`, `escalation.py:451-479`, `override.py:335-363`, `review_queue.py:397-425`
**Issue:** Four byte-similar copies of the drain-and-requeue consume and the
`hitl_action` audit append. Any fix to WR-02 must be applied four times.
**Fix:** Extract a shared helper (module-level function or small mixin) in
`ccf.hitl` — the same "shared implementation, no trust marker" pattern
already used for `enforce_signed_binding`.

### IN-02: Refusal-check ordering differs between the two doors

**File:** `runtime/ccf_runtime/http_api/routes/hitl.py:155-175` vs `runtime/ccf_runtime/mcp/hitl_server.py:358-381`
**Issue:** The HTTP door enforces tenant authz **before** the
subject-conflict check; the MCP tool checks naive-time and subject-conflict
**before** tenant authz. Consequence: for the same bad request the two
doors return different refusal codes, and the HTTP door writes an
`authz_decision` audit event for requests the MCP door would refuse
pre-authz — the per-door audit trails diverge for identical inputs, which
weakens the D-08 "one vocabulary, two renderings" story at the margins.
**Fix:** Pick one order (identity verification first is the safer
convention) and apply it at both doors.

### IN-03: `HitlActionReceipt` disposition built from two non-atomic transport reads

**File:** `runtime/ccf_runtime/http_api/routes/hitl.py:212-225`
**Issue:** `pending(...)` and `submissions(...)` are two separate locked
snapshots; under concurrent traffic the receipt's `event_pending` and
`submissions_for_event` can describe two different queue states. Harmless
for the receipt's advertised "honest disposition" purpose, but worth a
comment or a combined snapshot if the receipt is ever load-bearing.
**Fix:** Take both reads from one transport-level snapshot, or document the
best-effort nature on `HitlActionReceipt`.

### IN-04: The audit tuple records the matched tenant pattern but not the granting scope

**File:** `runtime/ccf_runtime/authz/protocol.py:155-184`
**Issue:** When a grant carries several mapped scopes, the allow is audited
with `authz_matched_pattern` but nothing identifies **which scope** granted
it (iteration order of `artifact.scopes` decides). This matches the D-09
tuple as specified, but a forensic reader cannot answer "which scope did
this allow travel on" from the log alone.
**Fix:** Consider adding `authz_matched_scope` to
`AuthzDecisionAuditEvent` in a future audit-contract rev (additive,
byte-stable for existing events per the A2 pattern).

### IN-05: MCP deny renderings use two different exception shapes

**File:** `runtime/ccf_runtime/mcp/hitl_server.py:280-307`
**Issue:** A tenant-authz deny is a `ValueError` whose message is the JSON
refusal body, but `UnverifiedCallerRefused` (raised on the same
`_enforce_tenant_authz` path when the token is absent) is a plain-prose
`RuntimeError`. The D-26 middleware should make the latter unreachable,
but if it ever fires, the client sees an unstructured protocol error rather
than the one refusal-body shape.
**Fix:** Render `UnverifiedCallerRefused` with the same
`json.dumps(refusal_detail(...))` payload (a dedicated error-code constant
would keep the "never parse prose" property).

---

_Reviewed: 2026-08-01_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
