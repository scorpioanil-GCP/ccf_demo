---
phase: 08-phase-i-5-examples-suite-full-ci-verification
reviewed: 2026-07-31T00:00:00Z
depth: standard
files_reviewed: 93
files_reviewed_list:
  - Makefile
  - examples/00-quickstart/README.md
  - examples/00-quickstart/artifacts/controlplane.yaml
  - examples/00-quickstart/artifacts/events.yaml
  - examples/00-quickstart/artifacts/halflife.yaml
  - examples/00-quickstart/artifacts/ontology.yaml
  - examples/00-quickstart/run.py
  - examples/01-agent-basics/README.md
  - examples/01-agent-basics/artifacts/agent.yaml
  - examples/01-agent-basics/artifacts/analysis_output.yaml
  - examples/01-agent-basics/artifacts/controlplane.yaml
  - examples/01-agent-basics/artifacts/events.yaml
  - examples/01-agent-basics/artifacts/ontology.yaml
  - examples/01-agent-basics/artifacts/prompt.yaml
  - examples/01-agent-basics/run.py
  - examples/02-skilling/README.md
  - examples/02-skilling/artifacts/agent.yaml
  - examples/02-skilling/artifacts/controlplane.yaml
  - examples/02-skilling/artifacts/events.yaml
  - examples/02-skilling/artifacts/ontology.yaml
  - examples/02-skilling/artifacts/skills.yaml
  - examples/02-skilling/run.py
  - examples/03-harness-portability/README.md
  - examples/03-harness-portability/artifacts/agents/order_insights.yaml
  - examples/03-harness-portability/artifacts/controlplane.yaml
  - examples/03-harness-portability/artifacts/events.yaml
  - examples/03-harness-portability/artifacts/harnesses.yaml
  - examples/03-harness-portability/artifacts/live.yaml
  - examples/03-harness-portability/artifacts/ontology.yaml
  - examples/03-harness-portability/artifacts/prompt.yaml
  - examples/03-harness-portability/legs/__init__.py
  - examples/03-harness-portability/legs/deterministic.py
  - examples/03-harness-portability/legs/live.py
  - examples/03-harness-portability/legs/ollama_client.py
  - examples/03-harness-portability/run.py
  - examples/04-cross-process/README.md
  - examples/04-cross-process/artifacts/a2a.yaml
  - examples/04-cross-process/artifacts/agent.yaml
  - examples/04-cross-process/artifacts/controlplane.yaml
  - examples/04-cross-process/artifacts/events.yaml
  - examples/04-cross-process/artifacts/ontology.yaml
  - examples/04-cross-process/artifacts/prompt.yaml
  - examples/04-cross-process/producer_child.py
  - examples/04-cross-process/run.py
  - examples/05-workflow-hitl/README.md
  - examples/05-workflow-hitl/artifacts/agent.yaml
  - examples/05-workflow-hitl/artifacts/hitl.yaml
  - examples/05-workflow-hitl/artifacts/prompt.yaml
  - examples/05-workflow-hitl/artifacts/task.yaml
  - examples/05-workflow-hitl/artifacts/tokens.yaml
  - examples/05-workflow-hitl/artifacts/workflow.yaml
  - examples/05-workflow-hitl/run.py
  - examples/06-decision-replay/README.md
  - examples/06-decision-replay/artifacts/agent.yaml
  - examples/06-decision-replay/artifacts/controlplane.yaml
  - examples/06-decision-replay/artifacts/events.yaml
  - examples/06-decision-replay/artifacts/hitl.yaml
  - examples/06-decision-replay/artifacts/ontology.yaml
  - examples/06-decision-replay/artifacts/prompt.yaml
  - examples/06-decision-replay/artifacts/skills.yaml
  - examples/06-decision-replay/artifacts/task.yaml
  - examples/06-decision-replay/artifacts/tokens.yaml
  - examples/06-decision-replay/artifacts/workflow.yaml
  - examples/06-decision-replay/run.py
  - examples/07-artifact-store-mcp/README.md
  - examples/07-artifact-store-mcp/artifacts/controlplane.yaml
  - examples/07-artifact-store-mcp/artifacts/events.yaml
  - examples/07-artifact-store-mcp/artifacts/ontology.yaml
  - examples/07-artifact-store-mcp/artifacts/store_file.yaml
  - examples/07-artifact-store-mcp/artifacts/store_mcp.yaml
  - examples/07-artifact-store-mcp/mcp_store_child.py
  - examples/07-artifact-store-mcp/run.py
  - pyproject.toml
  - runtime/ccf_runtime/cli/commands/hitl.py
  - runtime/ccf_runtime/http_api/app.py
  - runtime/ccf_runtime/http_api/errors.py
  - runtime/ccf_runtime/http_api/routes/hitl.py
  - runtime/ccf_runtime/mcp/hitl_server.py
  - runtime/ccf_runtime/orchestration/adk/driver.py
  - src/ccf/hitl/transport.py
  - tests/cli/test_cli.py
  - tests/conformance/test_a3_discharge.py
  - tests/hitl/test_signed_binding_authority.py
  - tests/hitl/test_was_called_derivation.py
  - tests/http_api/test_auth_hardening.py
  - tests/http_api/test_hitl_door_identity.py
  - tests/http_api/test_signed_binding_door.py
  - tests/lints/test_examples_scope.py
  - tools/lints/__main__.py
  - tools/lints/allowlist.yaml
  - tools/lints/no_hardcoding.py
  - tools/lints/tests/test_no_hardcoding.py
  - tools/lints/tests/test_runner.py
findings:
  critical: 0
  warning: 5
  info: 3
  total: 8
status: issues_found
---

# Phase 08: Code Review Report

**Reviewed:** 2026-07-31
**Depth:** standard
**Files Reviewed:** 93 (security-sensitive runtime/src files and example drivers read in full; artifacts and tests scanned for obvious defects per prioritization)
**Status:** issues_found

## Summary

Adversarial review of the phase 08 changes: HITL transport hardening (D-16 signed-binding enforcement), the HTTP/MCP/CLI HITL doors, the ADK orchestration driver, the CINV-01 lint tooling, and the eight-example suite with its subprocess drivers.

The core security composition is sound where it claims to be: the D-16 signed-binding path fails closed (refusals never touch the queue; missing verification machinery is a hard `RuntimeError`, not a skip), the derived-principal path on both doors is structurally unspoofable (`principal_from_token_grant` has no caller subject parameter, and `ApproverIdentity` carries only `subject_id` + `identity_provider_ref`, so the derived/signed-binding equality check at the transport is not a false-refusal trap), the non-TokenGrant stash fails closed, and the subprocess drivers in examples 04/07 use READY handshakes, ephemeral ports, process-group teardown with SIGTERM-then-SIGKILL, and generate key material at run time only. No hardcoded production secrets, no injection paths, no eval/shell usage were found.

What remains are authorization-scope gaps at the doors (tenant and scope are authenticated past, never authorized against), a thread-safety gap in the in-memory transport behind a threaded server, and smaller correctness/robustness defects listed below.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: Authenticated HITL doors perform no tenant or scope authorization

**File:** `runtime/ccf_runtime/http_api/routes/hitl.py:69, 77` and `runtime/ccf_runtime/mcp/hitl_server.py:244, 250`
**Issue:** When an auth hook is bound, any bearer whose token the source recognizes — regardless of `TokenGrant.scopes` and regardless of which tenant the grant belongs to — can (a) read **any** tenant's pending queue via `GET /hitl/queue?tenant=X`, and (b) submit actions against **any** tenant via `POST /hitl/actions` (the body's `tenant` field is never checked against the grant). The same holds on the MCP door: the queue Resource takes `tenant` as a URI segment and the `submit_hitl_action` tool takes `tenant` as a free parameter; the verified token pins the *subject*, never the tenant. `TokenGrant.scopes` is carried but never consulted on the HTTP door (`BearerTokenAuth` checks recognition only), so the `scopes: [hitl]` vocabulary the example 05 token table declares is decorative. The transport's D-23 "two tenants' queues never interleave" partitioning is thereby bypassable at both Experience-Layer doors by any authenticated caller. The documented D-22 posture sentence covers the *unauthenticated* default; once a deployment binds the hook, the natural reading is that authorization is in force, and it is not.
**Fix:** Either (a) extend `TokenGrant` with a tenant binding (or a tenant claim in the token table) and refuse tenant-mismatched queue reads and submissions with a typed 403 at both doors, and enforce `scopes` against a per-route required scope on the HTTP door as FastMCP already does via `required_scopes`; or (b) at minimum add an explicit, test-asserted posture sentence stating that the bound-hook mode authenticates but does not authorize tenant access, so the residual is recorded rather than implied away.

### WR-02: `InMemoryHitlTransport` is not thread-safe but is served by threaded FastAPI routes

**File:** `src/ccf/hitl/transport.py:332-438`; consumed at `runtime/ccf_runtime/http_api/routes/hitl.py:69-159`
**Issue:** The transport's `_pending` dict-of-deques and `_submissions` dict-of-lists are mutated with no synchronization. The HTTP routes (`def queue`, `def act`) are synchronous, so FastAPI runs them on a threadpool — concurrent `enqueue`/`dequeue`/`submit` calls race on `dict.setdefault` + container mutation, and the receipt's disposition fields (`event_pending`, `submissions_for_event`, lines 147-159 of the route) are computed from two separate reads after the write, so under concurrent submits the receipt can report a state that never existed. CPython's GIL makes most single operations atomic, but `pending()`'s `tuple(deque)` iteration concurrent with `popleft()`/`append()` can raise `RuntimeError: deque mutated during iteration`.
**Fix:** Add a `threading.Lock` around the mutating and snapshot methods of `InMemoryHitlTransport` (reference implementation or not, it is wired behind a threaded server by the SDK's own example 05), and compute the receipt's two disposition reads under one lock acquisition or accept-and-document the non-atomicity.

### WR-03: `AdkWorkflowDriver.persisted_state` calls `asyncio.run` and `_run` can `KeyError` on a swallowed segment

**File:** `runtime/ccf_runtime/orchestration/adk/driver.py:281, 185`
**Issue:** Two robustness defects. (1) `persisted_state` uses `asyncio.run(...)` internally; called from any context with a running event loop (an async test, or any caller already inside the driver's own async surface) it raises `RuntimeError: asyncio.run() cannot be called from a running event loop`. The rest of the class is async; this one method is sync-over-async. (2) `_run` line 185 returns `self._outcomes[(tenant, execution_id)]` unconditionally after draining the runner. If ADK ever completes the run without executing `_EngineSegment._run_async_impl` (topology error, ADK swallowing the sub-agent), this surfaces as a bare `KeyError` on a tuple key — an undiagnosable failure mode. Worse, on a *repeat* execution id the stale outcome from a prior run would be returned silently instead.
**Fix:** (1) Make `persisted_state` `async` (callers `await` it), or document/guard the no-running-loop precondition. (2) Replace the bare lookup with `self._outcomes.pop(key, None)` plus an explicit `RuntimeError("ADK run completed without the engine segment executing for {key}")` when absent — popping also prevents stale-outcome reuse across runs.

### WR-04: Hot busy-wait with no timeout on consumer-endpoint startup in example 04

**File:** `examples/04-cross-process/run.py:308-312`
**Issue:** `while not server.started: if not thread.is_alive(): raise ...` spins at 100% CPU with no sleep and no deadline. If uvicorn's startup blocks without failing (thread alive, `started` never set — e.g., a lifespan hang), the driver hangs forever, and even in the normal case it burns a core during startup. The sibling child processes got this right (`await anyio.sleep(0.005)` poll in `producer_child.py:611` and `mcp_store_child.py:123`); the parent side did not.
**Fix:**
```python
deadline = time.monotonic() + TERMINATE_TIMEOUT_SECONDS
while not server.started:
    if not thread.is_alive():
        raise AssertionError("the consumer endpoint failed to start")
    if time.monotonic() > deadline:
        raise AssertionError("the consumer endpoint did not start in time")
    time.sleep(0.005)
```

### WR-05: MCP door refusals travel as JSON-in-`ValueError`-message; malformed inputs bypass the error-code contract

**File:** `runtime/ccf_runtime/mcp/hitl_server.py:289, 353-369`
**Issue:** The 08-03 door mapping raises `ValueError(json.dumps(refusal_detail(...)))` — the machine-readable contract (`error_code`) is embedded inside a generic exception's message string, which MCP serializes as tool-error prose. A client must know to JSON-parse the message text of a `ValueError` to recover the code, which is exactly the "parse refusal prose" pattern the shared constants exist to end; nothing type-distinguishes this refusal from any other `ValueError` the tool body can raise. And it *can* raise others without the shape: `datetime.fromisoformat(action_time)` at line 289 raises a raw `ValueError` for malformed input, and the paired signed-binding-parameter check at line 325 raises a plain-prose `ValueError` — so a client keying on the refusal-body shape gets three incompatible error surfaces from one tool.
**Fix:** Wrap all deliberate refusals in one helper that emits the `refusal_detail` shape (and catch `fromisoformat` failures to re-raise through it with a named code, e.g. `malformed-action-time`), so every refusal leaving this tool carries `error_code` uniformly; document that the MCP transport carries it as the tool-error content.

## Info

### IN-01: Lint finding parser assumes space-free, colon-terminal-line paths

**File:** `tools/lints/no_hardcoding.py:209-213, 446`
**Issue:** `apply_allowlist` recovers `file` and `rule` by `finding.split(" ", 2)` / `rsplit(":", 1)` — a repository path containing a space mis-parses the rule field and silently defeats allowlist matching (a reviewed exception stops applying); the sort key at line 446 (`int(f.split(":", 1)[1]...)`) raises on Windows drive-letter paths. Low likelihood in this repo, but the allowlist is a security-adjacent surface and a silent mis-parse re-opens findings the reviewer already triaged — or worse, never suppresses when it should, which fails loud; the mis-parse direction here fails loud, so Info.
**Fix:** Emit findings as structured tuples (path, line, rule, message, fp) internally and format only at print time.

### IN-02: Static bearer tokens committed in example artifacts

**File:** `examples/05-workflow-hitl/artifacts/tokens.yaml:15-21`, `examples/06-decision-replay/artifacts/tokens.yaml`, `examples/07-artifact-store-mcp/artifacts/store_mcp.yaml:24`
**Issue:** Bearer-token values (`sm-disbursement-token-2026`, `nordhaven-example07-dev-token`) are committed to the repository. Both files carry explicit "synthetic, never production" comments and the T-08-20 acceptance marker, and the tokens authorize only per-run temporary state — recorded here so the acceptance is visible in the review record, not as a defect to fix.
**Fix:** None required; keep the synthetic-token disclaimers if these files are ever templated for real deployments.

### IN-03: `AdkWorkflowDriver._outcomes` retains every execution's outcome for the driver's lifetime

**File:** `runtime/ccf_runtime/orchestration/adk/driver.py:155, 207, 244`
**Issue:** Outcomes keyed by `(tenant, execution_id)` are inserted and never removed. Beyond growth (out of v1 scope), retention is a *correctness* hazard in combination with WR-03: a stale `WorkflowSuspended` for a reused execution id makes `_suspended()` report suspension for a run that never re-executed.
**Fix:** Pop the outcome in `_run` when returning it (see WR-03 fix), which resolves both.

---

_Reviewed: 2026-07-31_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
