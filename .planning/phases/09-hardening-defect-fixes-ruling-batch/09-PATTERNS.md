# Phase 9: Hardening — Defect Fixes & Ruling Batch - Pattern Map

**Mapped:** 2026-08-01
**Files analyzed:** 10 new/modified files
**Analogs found:** 9 / 10 (mini-cycle doc has a partial analog in DECISIONS.md format only)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `docs/` mini-cycle ruling document (new, name TBD by planner) | doc / Control Plane decision artifact | batch (six ruling items) | `docs/DECISIONS.md` D-IMPL entry format | role-match |
| `docs/DECISIONS.md` (modified — six new D-IMPL entries + D-GATE-9) | decision log | append-only | its own existing entries (D-IMPL-65..67 tail) | exact |
| `src/ccf/hitl/transport.py` (modified — lock + Protocol docstring contract) | service / Protocol + reference impl | CRUD (typed queue) | itself (self-modification) | exact |
| `tests/hitl/test_transport_concurrency.py` (new — hammer test) | test (stress) | event-driven (threaded mixed-op) | `tests/hitl/test_transport.py` (fixture helpers) | role-match |
| `runtime/ccf_runtime/orchestration/<common module>.py` (new — dispatch helper + error hierarchy; name at planner discretion, e.g. `_dispatch.py`/`errors.py`) | utility / shared runtime module | request-response (sync→coroutine bridge) | `runtime/ccf_runtime/orchestration/__init__.py` (module-docstring/lint conventions) + `SignedBinding*Refused` in `transport.py` (error style) | role-match |
| `runtime/ccf_runtime/orchestration/adk/driver.py` (modified) | adapter/driver | request-response | itself | exact |
| `runtime/ccf_runtime/orchestration/langgraph/driver.py` (modified) | adapter/driver | request-response | ADK driver (same `_outcomes` pattern) | exact |
| `runtime/ccf_runtime/orchestration/claude_agent/driver.py` (modified) | adapter/driver | request-response | ADK driver | exact |
| `tests/conformance/test_orchestration.py` (modified — typed-error + loop-safety parity cases) | test (conformance, parametrized) | request-response | itself (leg fixture infrastructure) | exact |
| D-14 hash manifest (one-time phase artifact) | tooling | batch (file hashing) | — (none; `sha256sum` over examples tree) | no analog |

## Pattern Assignments

### `src/ccf/hitl/transport.py` — WR-02 lock (service, CRUD)

**Analog:** itself — `src/ccf/hitl/transport.py:292-438` (`InMemoryHitlTransport`)

**Current unsynchronized state** (lines 324-337):
```python
def __init__(self, *, control_plane=None, hitl_policy_key=None,
             identity_provider=None, trusted_keys=None) -> None:
    self._pending: dict[str, deque[PendingHitlEvent]] = {}
    self._submissions: dict[str, list[HitlActionSubmission]] = {}
    ...
```
Add `self._lock = threading.Lock()` here; `threading` is stdlib, module is
tagged `__ccf_mode__ = "algorithmic"` (line 55) — lint-safe.

**Mutation sites to wrap in `with self._lock:`** (lines 405-438):
```python
def enqueue(self, *, event: PendingHitlEvent) -> None:
    self._pending.setdefault(event.tenant, deque()).append(event)

def dequeue(self, *, tenant: str) -> PendingHitlEvent | None:
    queue = self._pending.get(tenant)
    if not queue:
        return None
    return queue.popleft()          # check-then-pop race — one lock scope

def pending(self, *, tenant: str) -> tuple[PendingHitlEvent, ...]:
    return tuple(self._pending.get(tenant, ()))   # snapshot under lock

def submit(self, *, submission: HitlActionSubmission) -> None:
    if self._signed_binding_required():           # KEEP OUTSIDE the lock
        self._enforce_signed_binding(submission)  # KEEP OUTSIDE the lock
    self._submissions.setdefault(submission.tenant, []).append(submission)  # lock

def submissions(self, *, tenant: str) -> tuple[HitlActionSubmission, ...]:
    return tuple(self._submissions.get(tenant, ()))  # snapshot under lock
```
Critical: `_signed_binding_required()` (Control Plane `resolve_latest`, lines
339-359) and `_enforce_signed_binding()` (JWS verification, lines 361-403)
stay **outside** the lock (D-06 restructure rule; RESEARCH Pitfall 1). Only
queue mutations and snapshot reads take the lock. No method calls another
locked method today — plain `Lock` works with zero restructuring.

**Protocol docstring pattern for the D-05 concurrency contract** — model on
the existing `HITLTransportProtocol` docstring (lines 254-269), which
explains what the Protocol omits and why, cites rulings inline
(`D-IMPL-20; CLAUDE.md §8.2`), and notes `runtime_checkable` semantics. Add
the thread-safety sentence to that docstring (D-08: docstring only, no
separate docs page), citing the new D-IMPL ruling number and CLAUDE.md §8.2.

### Shared driver module — dispatch helper + error hierarchy (utility)

**Analog A — error-hierarchy style:** `src/ccf/hitl/transport.py:132-157`
```python
class SignedBindingRequiredRefused(PermissionError):
    """Policy requires a signed principal binding and none was presented.

    SDK-defined (CLAUDE.md §8.2); the D-16 composition (08-CONTEXT),
    designed within the D-IMPL-21/63/67 contract envelope. Raised at the
    transport authority path when ... A distinct class from
    :class:`SignedBindingInvalidRefused` so the Experience-Layer doors can
    map absence and invalidity to their own error-code constants ...
    """
```
Copy the shape exactly: sibling classes subclassing a semantically apt
builtin, one-line summary, `SDK-defined (CLAUDE.md §X; D-IMPL-NN)` citation,
rationale for why the classes are distinct. Apply to
`WorkflowDriverError` / `SegmentNotExecutedError` / state-retrieval subclass
(D-10). RESEARCH open question 1: nothing under `tests/` catches `KeyError`
from drivers (verified grep — the only `KeyError` test expectations are the
ArtifactStore `ArtifactNotFound` case and a HitlPolicy no-KeyError test), so
a clean break (no `KeyError` co-subclassing) is safe within the parity
suite's rewrite.

**Analog B — module docstring/lint conventions:**
`runtime/ccf_runtime/orchestration/__init__.py` (lines 1-25):
```python
"""Orchestrator driver integrations — D-IMPL-60's module tree.

Each SDK's `OrchestrationProtocol` driver lives under
``ccf_runtime/orchestration/<sdk>/`` — **never** under
``ccf_runtime/adapters/<sdk>/``. ... the D-06 lint
(``tools/lints/orchestration_imports.py``) bans imports bidirectionally
between this tree and the adapters tree ...

Algorithmic package (CINV-03).
"""
from __future__ import annotations

__ccf_mode__ = "algorithmic"
```
The new shared module sits directly under `orchestration/` (D-12), imports
only stdlib (`asyncio`, `concurrent.futures`) — no harness SDK, so it can
carry `__ccf_mode__ = "algorithmic"` and stays green under the
`d06-orchestration-split` and harness-import lints. Docstring cites
CLAUDE.md §8.1 and the phase's D-IMPL numbers, marked SDK-defined.

**Dispatch helper core pattern** (from 09-RESEARCH.md Pattern 1, stdlib idiom):
```python
def run_coroutine_sync(coro, *, timeout: float | None = None):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)          # plain sync context
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result(timeout)
```
Anti-patterns (do not copy): `loop.run_until_complete` on the detected loop,
`nest_asyncio`, `run_coroutine_threadsafe` against the caller's loop.

### The three drivers — WR-03 sites (adapter/driver, request-response)

**Analog:** `runtime/ccf_runtime/orchestration/adk/driver.py` (349-line file, read in full)

**Primary defect — `persisted_state`** (lines 270-291):
```python
def persisted_state(self, *, workflow, execution_id):
    import asyncio
    tenant = workflow.definition.tenant
    session = asyncio.run(                      # <- WR-03: crashes in a running loop
        self._sessions.get_session(
            app_name=_APP_NAME, user_id=tenant,
            session_id=f"{tenant}/{execution_id}",
        )
    )
    if session is None:
        return ()
    return tuple(dict(session.state).values())
```
Replace `asyncio.run(...)` with the shared `run_coroutine_sync(...)`; wrap
retrieval failure in the typed state-retrieval error.

**Bare-`KeyError` sites to convert to `SegmentNotExecutedError`:**
- ADK `driver.py:185` — `return self._outcomes[(tenant, execution_id)]`
- LangGraph `driver.py:111, 153, 164` — same `_outcomes[...]` pattern
- Claude Agent `driver.py:366` — `return self._outcomes[key]`

All three drivers already share the `(tenant, execution_id)`-keyed
`_outcomes: dict[tuple[str, str], CCFContract]` convention (ADK line 155) —
the fix pattern is identical per driver: `try/except KeyError: raise
SegmentNotExecutedError(...)` or `.get()` + explicit raise, importing from
the shared module.

**Docstring convention for the touched drivers** — ADK `driver.py:1-40`
shows the house style: module docstring opens with the class name and one
line of purpose, cites `CLAUDE.md §8.1; D-IMPL-17/60`, states authority
posture ("The CCF engine is authoritative for state and audit (T-07-33)"),
and ends noting the CINV-02 carve-out. Preserve; append loop-safety note
citing the new ruling.

### `tests/conformance/test_orchestration.py` — parity extension (test)

**Analog:** itself — extend, do not build new fixture infrastructure (D-13; RESEARCH Pattern 4).

**Leg parametrization to reuse** (lines 216-304):
```python
class OrchestrationLeg(NamedTuple):
    leg_id: str
    driver: DriverFactory
    positions: PositionProbe | None

ORCHESTRATION_PARAMS = ("in-sdk", "langgraph", "adk", "claude-agent")

def build_orchestration_leg(param: str) -> OrchestrationLeg:
    ...
    if param == "adk":
        harness_unavailable("google.adk", param)   # skip-vs-required machinery
        from ccf_runtime.orchestration.adk.driver import AdkWorkflowDriver
        ...

@pytest.fixture(params=ORCHESTRATION_PARAMS)
def leg(request): return build_orchestration_leg(request.param)
```
Note: `positions` is `None` for the in-sdk leg — loop-safety/typed-error
introspection tests must guard on `leg.positions is not None`, exactly as
`test_the_ccf_engine_stays_authoritative_for_suspended_state` (lines
451-477) does. Introspection method names differ per leg
(`persisted_state` / `checkpointed_values` / `session_transcript`) — the
`PositionProbe` closure already abstracts that; route new assertions through it.

**Shared-body drive helper to reuse** (lines 385-401):
```python
def _drive_to_terminal(leg, world, workflow, execution_id):
    driver = leg.driver(world.engine)
    suspended = asyncio.run(driver.start_execution(...))
    world.approve(suspended)
    outcome = asyncio.run(driver.resume_execution(..., decision="released"))
    return suspended, outcome
```
Loop-safety case D-13(c): call `leg.positions(...)` both from plain sync and
from inside an `asyncio.run(...)`-hosted coroutine (this is the test that
verifies RESEARCH assumption A1 about ADK `InMemorySessionService`
cross-loop reads).

**Fixture/world pattern** (lines 116-198): `World` builds registry + engine +
`InMemoryHitlTransport` + real `ApprovalGate` per leg from
`tests/fixtures/banking` YAML — reuse verbatim for typed-error cases (e.g.,
call `leg.positions` / driver introspection for a never-executed
`execution_id` and assert `pytest.raises(SegmentNotExecutedError)` per leg,
identical type across legs).

### `tests/hitl/test_transport_concurrency.py` — hammer (test, stress)

**Analog:** `tests/hitl/test_transport.py` (lines 1-60 read)

**Conventions to copy:**
```python
"""HITLTransportProtocol + in-memory reference impl (D-IMPL-20).
Written before the implementation per the TDD discipline. The claims pinned
here: ..."""
ACTION_TIME = datetime(2026, 7, 30, 12, 0, 0, tzinfo=UTC)

def _binding() -> HumanPrincipalBinding:
    return HumanPrincipalBinding.model_validate({... "product_content_hash":
        content_hash({"product": "seen"}), ...})

def _event(**mutations: Any) -> PendingHitlEvent:
    document = {"event_key": "acme-bank/approvals/1",
                "event_class": "approval-gate", "tenant": "acme-bank", ...}
```
Reuse the `_binding()` / `_event(**mutations)` builder helpers (import or
duplicate the small helpers per the sibling-file convention), tenant naming
(`acme-bank`), and claims-pinning module docstring. Hammer design per D-07 +
RESEARCH Pattern 3: barrier start, seeded random op mix over 2-3 tenants,
bounded per-thread work counts, `thread.join(timeout=...)` + `pytest.fail`
(no pytest-timeout — not installed), post-run invariants by unique
`event_key`. Two cases: unconfigured transport (main hammer) and a short
D-16-wired case (Control Plane path lock-ordering check).

### Ruling-batch document + DECISIONS.md entries (docs)

**Analog:** `docs/DECISIONS.md` existing D-IMPL entries (tail read; D-IMPL-65/66/67 + D-GATE-I.4.1)

**Entry shape to copy** (verbatim structure from D-IMPL-66/67):
```
**D-IMPL-NN — <title>.** RESOLVED — **<ruling summary>. <date>. Approver:
Dave.** <surfacing context, preserved>. <question as put to Dave>.
<accepted consequences (a)/(b)/(c)>. <what is explicitly NOT reopened>.
Originates: <CLAUDE.md §, prior D-IMPL numbers, source doc>.
```
Discipline observed in the log: new-number-not-amend (D-IMPL-66 explicitly
"supersedes the scheduling, not the substance"); D-GATE entries record
scope, delivered items, verification numbers, review rounds, and merge
messaging. **Next free number: D-IMPL-68** (log tail ends at D-IMPL-67 plus
the Phase-8 context ruling D-15 and D-GATE-I.4.1) — planner confirms by
reading the full tail at plan time. The Phase-8 "D-10" being amended in
ruling item 5 is the `make ci` composition note at Makefile lines 37-41
(`ci: ci-core examples`) — keep the two D-10 namespaces straight.

The mini-cycle document itself (per-item context / 2-3 options with
consequences / recommendation) mirrors the same per-entry fields, pre-ruling;
ruling seeds are already drafted in 09-RESEARCH.md "Ruling-Batch Item
Research Seeds" 1-6.

## Shared Patterns

### Ruling citations in docstrings
**Source:** every public class in `src/ccf/hitl/transport.py` and the driver modules
**Apply to:** all touched/new code
Docstrings cite the governing ruling inline — `(D-IMPL-20; CLAUDE.md §8.2)` —
and mark SDK extensions "SDK-defined". New errors, the dispatch helper, and
the docstring concurrency contract all cite the Phase 9 D-IMPL numbers once assigned.

### `__ccf_mode__` tagging + lint survival
**Source:** `transport.py:55`, `orchestration/__init__.py`
**Apply to:** the new shared module and the modified transport
`__ccf_mode__ = "algorithmic"`, `from __future__ import annotations`,
explicit `__all__`. Verify per task with `make ci-core`
(mypy --strict + `tools.lints --all` + tests).

### Typed refusal/error siblings
**Source:** `SignedBindingRequiredRefused` / `SignedBindingInvalidRefused` (`transport.py:132-157`)
**Apply to:** the driver error hierarchy (D-10)
Distinct sibling classes per failure meaning, so consumers can map each to
its own handling — never one class with a mode flag.

### Keyword-only typed method signatures
**Source:** `HITLTransportProtocol` methods (`transport.py:271-289`); enforced structurally by
`test_the_protocol_methods_are_keyword_only_and_typed` (`test_orchestration.py:362-379`)
**Apply to:** the dispatch helper's public surface and any new driver methods.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| D-14 hash manifest / pre-post check | phase tooling | batch | No hashing tooling exists. Note: there are **no `expected*` output files** under `examples/` — each `run.py` self-asserts against its `artifacts/*.yaml` and exits nonzero on failure (e.g., `examples/00-quickstart/run.py:342-355`). The D-14 "expected-output files" are therefore the examples' `run.py` + `artifacts/` trees; planner should hash those (`sha256sum` recursively per example dir) and rely on `make examples` (Makefile lines 43-67, part of `make ci`) for behavioral byte-identity. This resolves RESEARCH open question 4. |

## Metadata

**Analog search scope:** `src/ccf/hitl/`, `runtime/ccf_runtime/orchestration/` (all four subtrees), `tests/hitl/`, `tests/conformance/`, `docs/DECISIONS.md`, `Makefile`, `examples/`
**Files scanned:** ~15 (5 read in full or in targeted ranges)
**Pattern extraction date:** 2026-08-01
