# 16-external-consumers — two orphaned Phase 16 client programs, retired

**Status:** historical record. Nothing here runs, nothing here is maintained,
and nothing in the tree imports it.
**Was:** `examples/s2-01-external-consumers/`, moved out of `examples/` by
Phase 20 under `H-13` (`.planning/phases/20-client-access-from-three-harnesses-adk-anthropic-agent-sdk-a/20-CONTEXT.md`).
**Retired by:** Phase 16's retirement — `docs/DECISIONS.md` **`D-IMPL-152`**
(Dave, 2026-08-17).
**Replaced by:** `examples/hw1-harness-clients/` — Phase 20's three-harness
trio, the canonical foreign-harness → MCP-door demonstration going forward.

## What this is

Two zero-CCF client programs, and nothing else. They arrived in wave 2 of
Phase 16 as a spike record's subject matter and never grew the rest of an
example around them:

| File | Harness | Shape |
| --- | --- | --- |
| `docs/retired/16-external-consumers/client_langgraph.py::build_graph` | `langgraph==1.2.9` + `langchain-core==1.5.1` | A two-node `StateGraph` whose nodes drive a raw `mcp.ClientSession` and bind each advertised MCP tool as a hand-written `StructuredTool` |
| `docs/retired/16-external-consumers/client_claude_agent.py::session_options` | `claude-agent-sdk==0.2.128` | A `ClaudeSDKClient` session whose entire tool surface is the CCF experience server, bound as a Streamable-HTTP MCP server on `ClaudeAgentOptions` |

There was **no README, no runner, no `make` target and no CI job** — the
condition `docs/DECISIONS.md` `D-IMPL-125` recorded in its own words:
*"two zero-CCF client files with no server, no README and no runner."* The
plan that was to finish the directory (`16-09`) was one of the fourteen
withdrawn when Phase 16 was retired.

## Why it is here rather than deleted

This repository's precedent for retiring things is deletion **plus a written
record** (`docs/surface/examples/ERGO-03-FROZEN.md` is the nearest analogue).
These two files are kept because they carry shapes Phase 20 inherited and a
reader may want to see where they came from:

- The **`StructuredTool`-wrapping-a-raw-`mcp`-session** topology, and the
  measurement behind it — that
  `StructuredTool.from_function(args_schema=<JSON Schema dict>)` accepts the
  MCP `inputSchema` mapping directly, so no schema is restated on the client
  side, and no third-party LangChain-to-MCP bridge package is needed. The
  spike record for that measurement is
  `docs/surface/examples/SECTION-2-TRANSPORT.md`.
- The **Claude Agent SDK's tool-surface withdrawal** — `tools=[]`,
  `skills=[]`, `setting_sources=[]`, `strict_mcp_config=True` — so the
  server's own allowlist is the whole of the boundary. Phase 20's
  `examples/hw1-harness-clients/client_anthropic.py::session_options` holds
  the same posture over `mcp+stdio`.

The record of what an earlier surface looked like is worth a directory nobody
maintains. It is not worth a directory that looks live in a listing of
`examples/`, which is why it moved.

## What it targets, and therefore what it is not

Both programs speak **streamable HTTP with a bearer token** against the
**pre-Phase-17 surface** — the `examples/external/00-hello-context` experience
server, reached through `CCF_MCP_URL` and `CCF_TOKEN` environment variables.
They predate `ccf.client`, the `mcp+stdio` adapter, the Phase 18.1
deployment-declares-its-server binding and the Phase 19 wire form.

So: **not runnable against the current door, not gated, not maintained.** Do
not adapt these files; read them, then write against
`examples/hw1-harness-clients/`.

## What retired it, and what replaces it

| | |
| --- | --- |
| Retired by | Phase 16's retirement, `docs/DECISIONS.md` `D-IMPL-152` (2026-08-17) — the plan set was withdrawn, including `16-09`, the plan that would have finished this directory |
| Moved by | Phase 20, `H-13`; destination ruled in `docs/DECISIONS.md` `D-IMPL-164` |
| Replaced by | `examples/hw1-harness-clients/` — one Google ADK client, one Anthropic Agent SDK client, one LangGraph client, all three reaching the Phase 18.1 `mcp+stdio` door on `examples/hw1-companies-over-revenue` and landing on one content address |

Nothing imports this directory. There is no `make` target naming it, no CI job
naming it, and no published snippet including from it — `mkdocs.yml` reads only
`public/`, so this document is unpublished by construction, and this tree sits
outside every entry in `tools/lints/__main__.py::RULE_TREE_SCOPE`, so no lint
fires on code nobody maintains.
