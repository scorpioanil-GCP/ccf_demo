---
phase: 16-documentation-rewrite-the-deterministic-path-the-adoption-ar
plan: 03
subsystem: examples
tags: [harness-neutrality, mcp, langgraph, claude-agent-sdk, transport-spike]
requires:
  - "examples/external/00-hello-context (read-only: serve.py, run.py, artifacts/)"
  - "runtime/ccf_runtime/mcp/experience.py (the Experience MCP door under test)"
  - "tools/lints (imported_module_names, submodule_import_names)"
provides:
  - "examples/s2-01-external-consumers/client_langgraph.py — the LangGraph client leg (RESEARCH F-2's NO-ANALOG gap, closed)"
  - "examples/s2-01-external-consumers/client_claude_agent.py — the Claude Agent SDK client leg"
  - "tests/examples/test_s2_client_transport_spike.py — the against-a-real-server proof (retired by 16-20)"
  - "docs/surface/examples/SECTION-2-TRANSPORT.md — the transport findings plan 16-09 reads first"
affects:
  - "16-09 (repoints both legs at the Section-2 fabric; must read the transport record before starting)"
  - "16-20 (retires the spike test)"
tech-stack:
  added: []
  patterns:
    - "LangGraph node drives mcp.ClientSession directly; MCP tools hand-bound as langchain_core StructuredTools from the server's own JSON Schema"
    - "Claude Agent SDK session binds the CCF door as a Streamable-HTTP MCP server; tools=[] + skills=[] + setting_sources=[] + strict_mcp_config=True make the CCF door the whole tool surface"
    - "Transport-level CI determinism for the Claude leg via the bundled Claude Code CLI's ANTHROPIC_BASE_URL — no branch in the leg"
    - "Zero-CCF import guard built on the shared lint helpers plus dynamic-import detection, with a parametrized four-spelling negative control"
key-files:
  created:
    - examples/s2-01-external-consumers/client_langgraph.py
    - examples/s2-01-external-consumers/client_claude_agent.py
    - tests/examples/test_s2_client_transport_spike.py
    - docs/surface/examples/SECTION-2-TRANSPORT.md
  modified: []
decisions:
  - "Took the zero-new-dependency path for LangGraph; the third-party LangChain-to-MCP bridge package was not installed and is not needed (hand-binding cost fifteen lines)."
  - "The Claude leg is model-driven with no CI/live branch; determinism comes from redirecting the bundled CLI's model API, which is the client_anthropic.py posture one process further out."
  - "Used tools.lints' imported_module_names ∪ submodule_import_names (the union tools/lints mandates for deny loops) rather than a fresh regex, and widened it with importlib.import_module detection."
metrics:
  duration: "~55 min"
  completed: 2026-08-10
  tasks: 3
  commits: 3
  files_created: 4
---

# Phase 16 Plan 03: Section-2 Client Transport Spike Summary

Both missing Section-2 harness legs now exist and are proven against a live CCF
Experience MCP server — a LangGraph node driving `mcp.ClientSession` with
hand-bound LangChain tools, and a Claude Agent SDK session whose entire tool
surface is the CCF door — with zero new dependencies and the transport findings
recorded for plan 16-09.

## What was built

| Task | Artifact | Commit |
| --- | --- | --- |
| 1 | `examples/s2-01-external-consumers/client_langgraph.py` | `33c0626` |
| 2 | `examples/s2-01-external-consumers/client_claude_agent.py` | `e531737` |
| 3 | `tests/examples/test_s2_client_transport_spike.py` + `docs/surface/examples/SECTION-2-TRANSPORT.md` | `8316fca` |

### Task 1 — the LangGraph leg

A two-node `StateGraph` (`discover` → `read`). Both nodes drive a real
`mcp.ClientSession` over `streamablehttp_client`; `discover` publishes the
server's advertised tool descriptors onto a typed state channel and `read` binds
each one as a `langchain_core.tools.StructuredTool` **by hand** and invokes it.
Imports are `langgraph`, `langchain_core`, `mcp` and the standard library —
nothing else. Endpoint and credential come from `CCF_MCP_URL` / `CCF_TOKEN`;
tool argument values arrive as `name=value` command-line arguments, so no other
CCF-prefixed identifier appears anywhere in the file. Carries all three
published marker regions (`mcp-connect`, `mcp-discover`, `mcp-resource`), no
CI/live branch, no `assert`, and one `print` — the `[label] body` line contract
`client_bare.py` publishes.

### Task 2 — the Claude Agent SDK leg

A real `ClaudeSDKClient` session with the CCF Experience server bound as a
Streamable-HTTP MCP server on `ClaudeAgentOptions`. The harness owns the loop,
the MCP connection and the tool calls; the leg's `mcp` import is used for one
thing only — asking the server which tools it advertises, so `allowed_tools` is
the server's own answer rather than a list restated in code. Model, prompt, MCP
namespace, endpoint and token all arrive from the environment (No-Hardcoding,
CLAUDE.md §6.4). No `anthropic` import, no credential variable read, no CI/live
branch.

### Task 3 — the proof and the record

`tests/examples/test_s2_client_transport_spike.py` (15 tests, ~2.6 s) spawns the
shipped `examples/external/00-hello-context/serve.py` through that harness's own
`_spawn`/`_terminate` (so the READY handshake and kill-fallback exercised are the
real ones), drives both legs as subprocesses, and **parses** the returned Context
Product rather than grepping it — tenant, schema name, non-empty
`lineage.operators_invoked`, and `payload.entity_count > 0`.

`docs/surface/examples/SECTION-2-TRANSPORT.md` records nine findings with a
per-finding action for 16-09, plus an explicit "what this spike does not
establish" section.

## The transport findings (the deliverable that de-risks wave 4)

**Q1 — the LangGraph API used to reach the node's tool surface.** None is needed;
the node reaches it itself. Three entry points and no others:
`langgraph.graph.StateGraph`, `langchain_core.tools.StructuredTool.from_function`,
and `mcp.ClientSession` over `streamablehttp_client`. The load-bearing detail:
`StructuredTool.from_function(args_schema=…)` **accepts a raw JSON-Schema dict**,
which is exactly the shape MCP's `tools/list` returns as `inputSchema` — so no
schema is restated anywhere, and no bridge package is needed. `coroutine=` plus
`await tool.ainvoke(...)` is the async form.

**Q2 — can the Claude Agent SDK be pointed at a replayed endpoint without a
branch?** **Yes**, and the answer came with four surprises worth the spike:

1. **`claude-agent-sdk` ships no MCP client.** It imports `mcp.types` and
   `mcp.server`, never `mcp.client`. An external HTTP MCP server is connected by
   the *Claude Code CLI*, which is the SDK's transport. So the redirect that
   determinizes the leg is honoured one process further out than expected.
2. **The CLI is bundled inside the wheel** — `claude_agent_sdk/_bundled/claude`,
   version `2.1.220`, found before any `PATH` search. This is what makes a
   keyless CI leg possible at all: a runner installing the `claude-agent` extra
   already has it. Nothing in the tree said so.
3. **The CLI always sends `"stream": true`.** The shipped
   `examples/external/00-hello-context/replay_server.py` answers with
   `JSONResponse`, which the CLI will not accept. **16-09's replay server needs
   an SSE response path** — this is the one structural change to that file's
   shape, and the single most consequential finding for 16-09's fixture design.
   A worked frame sequence is `_sse()` in the spike test module.
4. **Three requests per run, one of them a session-title turn** carrying no
   tools, plus a `HEAD /api/hello` preflight against the base URL that the
   shipped replay server (POST-only routes) would answer 405 rather than with its
   intended loud diagnostic. The system prompt also carries the current date —
   harmless under `fingerprint()`'s existing reduction, and a reason not to
   "improve" that matcher into a body hash.

**Making the tool surface exactly CCF's.** Out of the box the model-facing tool
list carried **28 CLI built-ins** beside the three CCF tools, which would couple
every captured fixture's `tool_names` fingerprint to the CLI's built-in
inventory. Four settings together reduce it to exactly the CCF door:
`tools=[]`, `skills=[]`, `setting_sources=[]`, `strict_mcp_config=True`.
`allowed_tools` alone does not — it gates invocation, not advertisement.
`permission_mode="bypassPermissions"` was tried, is **not** needed, and was
deliberately left out.

**Cost:** the whole Claude leg — CLI start, MCP connect, three model turns, one
`get_context` call — runs in ≈0.8 s.

## No package was installed

`git diff -- pyproject.toml` is empty across all three commits. The
`[ASSUMED]`-tagged LangChain-to-MCP bridge package RESEARCH recommends against
was neither installed nor referenced; the leg binds tools by hand instead. The
package-installation gate was never approached, so no human checkpoint was
needed.

## Deviations from Plan

### Auto-fixed / adjusted

**1. [Rule 3 — Blocking] `.venv` is absent from the worktree**
- **Found during:** Task 3 verification
- **Issue:** `make lint` failed with `.venv/bin/python: not found` — parallel
  worktrees do not carry the gitignored virtualenv.
- **Fix:** Symlinked `.venv` → the main checkout's virtualenv inside the
  worktree. `.venv` is in `.gitignore` (line 15), so `git status` stays clean and
  nothing was committed. `make lint` then exits 0.
- **Files modified:** none tracked.

**2. [Rule 2 — Correctness] The Claude drive moved into a module-scoped fixture**
- **Found during:** Task 3
- **Issue:** As first written, `test_the_claude_agent_leg_saw_only_ccf_tools`
  read the stand-in's recorded requests left behind by the preceding test. That
  is an inter-test ordering dependency: selected alone (`-k saw_only`) it would
  have passed over an empty list or failed for the wrong reason.
- **Fix:** Both Claude assertions now consume one module-scoped `claude_leg_run`
  fixture (the `bare_leg_output` shape in `test_ext00_serve_output.py`), so
  either test selected alone still drives the leg. Verified: `-k saw_only` runs
  green on its own.
- **Commit:** `8316fca`

### Deliberate reading of a plan instruction

**3. Zero-CCF guard helper choice.** The plan names `imported_module_names`
**and** `submodule_import_names`. `tools/lints/__init__.py` documents their union
as `reached_module_names` and states (finding F0) that *every* deny loop in the
package must read the union rather than the first helper alone. The guard
therefore computes exactly that union from the two named helpers —
`set(imported_module_names(node)) | set(submodule_import_names(node))` — which is
literally what the plan asked for and structurally what the lint package
mandates. It is then widened further with `importlib.import_module` /
`__import__` literal-argument detection, because a dynamic import binds `ccf`
just as surely and neither helper can see it. All three widenings are proven by
the parametrized negative control (four spellings × two legs = eight cases), each
asserting the guard **raises**.

### Marker placement note

`client_claude_agent.py` carries `mcp-connect`, `mcp-discover` and `mcp-resource`,
but `mcp-resource` wraps the block where the Context Product arrives **off the
harness's message stream** rather than off a `read_resource` call — that leg
never fetches the product itself, which is the whole point of it. The plan
anticipated this ("the same three marker names **where the structure supports
them**"); recorded here so 16-09 does not read the marker as a claim about
`read_resource`.

## Authentication gates

None. Both legs and the spike test run keyless: the LangGraph leg reaches no
model at all, and the Claude leg's model API is redirected to an in-module
loopback stand-in with a placeholder credential. No network egress beyond the two
loopback ports was observed.

## Verification

| Check | Result |
| --- | --- |
| `pytest tests/examples/test_s2_client_transport_spike.py -q` | 15 passed in 2.6 s |
| `pytest tests/examples/ -q` (whole family, for interaction) | 271 passed in 64.7 s |
| `make lint` (`tools.lints --all`) | exit 0 |
| `git diff -- pyproject.toml` | empty |
| `git status --porcelain examples/external/00-hello-context/` | empty |
| `git diff --stat -- src/ runtime/` | empty |
| AST zero-CCF check, both legs | exit 0 |
| `py_compile`, both legs | exit 0 |
| `grep -c "^from claude_agent_sdk\|^import claude_agent_sdk"` on the Claude leg | 1 |
| `grep -c "^from anthropic\|^import anthropic"` on the Claude leg | 0 |
| `grep -nE "if .*(CI\|LIVE\|MODE)"` on both legs | no match |
| `grep -c "ANTHROPIC_API_KEY\|GOOGLE_API_KEY"` on both legs | 0 |
| Marker regions in the LangGraph leg (3 start + 3 end) | 6 |

## Known Stubs

None. Both legs are production shape; plan 16-09 repoints their arguments at the
new fabric and does not restructure them. The spike test module is explicitly
labelled a spike in its own docstring and is retired by plan 16-20 — that is
scheduled scope, not a stub.

## Threat Flags

None. The plan's threat register covers the surface this work introduces, and
nothing here widened it: no new dependency (T-16-03-SC), no credential literal
(T-16-03-01), no token or credentialled URL on stdout (T-16-03-02), no write into
the shipped external example (T-16-03-04, asserted by
`test_the_shipped_external_example_is_untouched`).

One security posture worth naming for the record rather than as a flag: the
Claude leg deliberately does **not** set `permission_mode="bypassPermissions"`.
It was tried, found unnecessary, and left out, because an example that teaches
permission bypass would be teaching the wrong thing for a governed-context SDK.

## Self-Check: PASSED

All four created files exist on disk and all three commits are present in
`git log`.
