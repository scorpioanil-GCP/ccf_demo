---
phase: 06-phase-i-3-cross-process-harness-adapters
plan: 04
subsystem: cross-process MCP (client library, L6 egress server, cross-process test fixture)
tags: [mcp, egress, cross-process, xprc-01, d-01, d-17]
requires:
  - "06-02 (mypy covering /runtime; the pinned `mcp`/`uvicorn` dependencies)"
provides:
  - "ccf.mcp.client — the ONE shared MCP client library, including SyncMcpBridge"
  - "ccf.mcp.errors — typed failures separating absence from unreachability"
  - "ccf_runtime.mcp.egress — L6 FastMCP egress server under ccf-product://"
  - "tests/crossproc/conftest.py — THE shared cross-process fixture (D-17)"
affects:
  - "06-05 (MCP ArtifactStore: reuses SyncMcpBridge and the fixture)"
  - "06-06 (MCP ingress + `mcp` skill dispatch: reuses the client)"
  - "06-09, 06-10 (both A2A transports: reuse the fixture)"
tech-stack:
  added: ["mcp==1.28.1 (first real import in the repo)", "uvicorn==0.51.0 (explicit use)"]
  patterns: ["session-per-call against stateless_http", "child-bound ephemeral port + stdout readiness handshake"]
key-files:
  created:
    - src/ccf/mcp/__init__.py
    - src/ccf/mcp/client.py
    - src/ccf/mcp/errors.py
    - runtime/ccf_runtime/mcp/__init__.py
    - runtime/ccf_runtime/mcp/egress.py
    - tests/crossproc/__init__.py
    - tests/crossproc/conftest.py
    - tests/crossproc/servers/__init__.py
    - tests/crossproc/servers/mcp_egress_child.py
    - tests/crossproc/test_mcp_egress.py
  modified: []
decisions:
  - "The sync bridge lives in `ccf.mcp.client`, not in the ArtifactStore (research open question 3): `Agent.invoke_skill` needs the same bridge, so it is a shared concern."
  - "`McpResourceClient.resource_templates()` added beyond plan scope: the L6 egress surface is a *templated* resource, so `list_resources()` returns empty and discovery must read `list_resource_templates()`."
  - "Switched from the deprecated `streamablehttp_client` (as prototyped in research) to `streamable_http_client`, which mcp 1.28.1 now prefers."
  - "The child server and the parent test share one `build_servable_product` builder rather than each assembling the product, so the expected value cannot drift from the served one."
metrics:
  duration: ~50 min
  completed: 2026-07-26
---

# Phase 06 Plan 04: Cross-Process MCP Egress Slice Summary

A banking Context Product assembled through the full L1→L6 fabric in one OS
process is served as an MCP Resource under `ccf-product://` and read back
byte-identically by `ccf.mcp.client` in another, over real loopback HTTP, gated
by a stdout readiness handshake on an OS-assigned ephemeral port — with the
shared client library, the sync bridge, and the reusable cross-process fixture
that the rest of Phase I.3 builds on.

## What was built

**`ccf.mcp.errors`** — `McpClientError` base with `McpResourceAbsent` (also a
`KeyError`, mirroring `ArtifactNotFound`), `McpServerUnreachable` as the
deliberate fallback, and `McpTimeout` under it. The doctrine block restates the
artifacts-protocol argument (absence and outage demand opposite responses) and
forbids message string-matching: no parser and no `except McpError` handler
exists in the module to reach for.

**`ccf.mcp.client`** — `run_with_session()` opens transport + `ClientSession` +
`initialize()` inside one task per call and closes both on exit;
`SyncMcpBridge` owns one daemon event-loop thread and bounds every call with a
*required* `call_timeout_seconds` via `run_coroutine_threadsafe(...).result()`;
`McpResourceClient` offers async and sync halves of `read_text`,
`resource_uris`, and `resource_templates`. The docstring records, with its
reason, that the held-session/blocking-portal bridge deadlocks. `grep -c
start_blocking_portal` is 0 and no `anyio.from_thread` import exists.

**`ccf_runtime.mcp.egress`** — `build_egress_server(server_name=, resolver=)`
returns a `FastMCP(stateless_http=True, json_response=True)` registering the
templated resource `ccf-product://{tenant}/{product_class}/{version}` whose
handler returns `canonical_bytes(product)` decoded. Tenancy is a per-call URI
segment; the resolver seam trades only in `ServableProduct`. The module's source
contains no `GraphWriter`, no `GraphReader`, no `ccf.graph`, and no
`ccf-artifact://` — asserted both in the plan's acceptance check and in the test
suite.

**`tests/crossproc/`** — the shared fixture: `spawn_child_server()` context
manager plus a `child_server_port` fixture driven by *indirect parametrization*,
so 06-05/09/10 add a server by adding a child module rather than by editing the
fixture. Teardown is `terminate → wait(10) → kill` from a `finally`. The
empty-`readline()` case raises an `AssertionError` carrying the child's stderr,
and that hardening has its own test (a deliberately crashing child).

## Verification

| Check | Result |
|---|---|
| `pytest tests/crossproc -q` | 8 passed in 3.3 s |
| Full suite | **649 passed, 2 skipped** (baseline was 641/2; +8 new) |
| `mypy` | Success, 75 source files (baseline 70) |
| `tools.lints --all` | exit 0 |
| Orphaned children after the run | 0 (`ps` grep for the child returns nothing) |
| `grep -rn time.sleep tests/crossproc/` | nothing |

## Notes for waves 3-5 — first real `mcp` import

This plan was the first in the repo to actually import `mcp`. What was found:

1. **The `mcp` distribution was not installed in `/home/parkave/ccf_code/.venv`.**
   `pyproject.toml` pins `mcp`, `joserfc`, `a2a-sdk`, and `uvicorn` (added by
   06-02 and confirmed at its blocking human checkpoint) but the environment had
   only `uvicorn` and `httpx`. Installing the four pinned versions was required
   before anything could run; `pip check` reports no broken requirements
   afterwards. **Later waves should assume the venv is already correct now, but
   verify before debugging an ImportError.**
2. **No mypy friction at all.** `mcp==1.28.1` ships usable inline types;
   `mypy --strict` passed on the first run over both the client and the egress
   server with **no override needed** and no `type: ignore`. The A3 assumption
   (that the harness/a2a overrides are only "parses correctly") remains untested
   for `a2a`, `google.adk`, `langgraph`, and `claude_agent_sdk` — this plan
   exercised none of them.
3. **`streamablehttp_client` is deprecated** in 1.28.1 (emits a
   `DeprecationWarning` pointing at `streamable_http_client`). Research
   prototyped with the old name; the new one has the same 3-tuple yield and an
   added `http_client` keyword. Use the new name.
4. **`list_resources()` does not list templated resources.** A `FastMCP`
   `@server.resource("scheme://{a}/{b}")` registration appears only in
   `list_resource_templates()` (field `uriTemplate`); `list_resources()` returns
   an empty list. Any later plan asserting discovery of a templated artifact
   resource must read templates.
5. **The venv is shared across worktrees and the editable install points at the
   main repo.** `sys.meta_path`-appended editable finders lose to `PYTHONPATH`,
   so `PYTHONPATH=src:runtime` from inside the worktree is what makes the
   worktree's own code the one under test. Everything above was run that way.
6. **The MCP endpoint path is `/mcp`** on `streamable_http_app()`; the fixture's
   `loopback_url` assembles `http://127.0.0.1:{port}/mcp`.

## Deviations from Plan

### Auto-fixed / added

**1. [Rule 3 - Blocking] Installed the four already-pinned, already-approved dependencies**
- **Found during:** Task 1 setup
- **Issue:** `mcp`, `joserfc`, `a2a-sdk` were absent from the shared venv despite being pinned in `pyproject.toml`.
- **Fix:** `pip install` at exactly the pinned versions. Not a new dependency and not a package-legitimacy question — these are the versions the 06-02 blocking human checkpoint approved (threat T-06-SC), so no checkpoint was raised.
- **Files modified:** none (environment only)

**2. [Rule 2 - Missing functionality] `McpResourceClient.resource_templates()`**
- **Found during:** Task 3, when the discovery assertion failed
- **Issue:** The egress surface is templated, so `list_resources()` is empty and a consumer had no way to discover it.
- **Fix:** Added async + sync `resource_templates()`. Documented why the two listings stay separate.
- **Commit:** 294c45b

**3. [Rule 3 - Blocking] `tests/crossproc/servers/__init__.py`**
- Not in `files_modified`, but the parent imports the child module to reuse its builder, which needs the package.
- **Commit:** 294c45b

**4. [Rule 1 - Deprecation] `streamablehttp_client` → `streamable_http_client`**
- Research prototyped the deprecated alias; kept the suite warning-free.
- **Commit:** 294c45b

## Known Stubs

None. Every surface delivered is exercised end to end by the cross-process
suite.

## Threat Flags

None. No new security-relevant surface beyond the one the plan's threat model
already registers (the L6 egress listener), which binds only where the caller
says and is bound to loopback in the test.

## Self-Check: PASSED

- All ten created files present on disk.
- Commits `a2419fe`, `094e286`, `294c45b` present in `git log`.
- Suite, mypy, and lints all re-verified at the values in the table above.
