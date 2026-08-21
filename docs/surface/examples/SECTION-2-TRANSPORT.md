# Section 2 client legs — the transport findings

**Status:** spike record, written to be read *before* plan 16-09 starts.
**Produced by:** plan 16-03 (wave 2), risk **R-4**'s mitigation — spike the two
missing harness legs early, against the **existing**
`examples/external/00-hello-context` server, so a transport surprise surfaces in
week one rather than in wave four.
**Measured:** 2026-08-10, on branch `phase-16`, against the shipped external
example with no network egress beyond loopback.
**Evidence:** `tests/examples/test_s2_client_transport_spike.py` (15 tests,
green), driving both legs as subprocesses against a live `serve.py`.

Everything below was **observed**, not reasoned about. Where a claim is an
inference rather than a measurement it says so.

---

## 1. The two questions plan 16-03 was asked

### Q1 — which LangGraph API reaches the node's tool surface?

**Answer: none is needed. The node reaches the tool surface itself.**

`docs/retired/16-external-consumers/client_langgraph.py::build_graph` uses
exactly three LangGraph/LangChain entry points, and no others — the file was
measured under `examples/` and moved to the retired path by Phase 20
(`H-13`, `docs/retired/16-external-consumers/README.md`), which also ships
the replacement,
`examples/hw1-harness-clients/client_langgraph.py::build_graph`, over
`mcp+stdio` rather than HTTP:

| API | Package | What it does here |
| --- | --- | --- |
| `langgraph.graph.StateGraph` (+ `START`, `END`) | `langgraph==1.2.9` | The two-node topology. LangGraph exposes no agent loop to hook, so the leg builds its own — the same structural fact `runtime/ccf_runtime/adapters/langgraph/adapter.py` records for the adapter side. |
| `langchain_core.tools.StructuredTool.from_function` | `langchain-core==1.5.1` | Binds one LangChain tool per advertised MCP tool, **by hand**. |
| `mcp.ClientSession` over `mcp.client.streamable_http.streamablehttp_client` | `mcp==1.28.1` | Driven *from inside* both nodes. Identical shape to `client_bare.py`'s `connect()`. |

The load-bearing detail, and the one worth knowing before writing the next leg:

> **`StructuredTool.from_function(args_schema=…)` accepts a raw JSON-Schema
> `dict`.** The MCP `tools/list` response carries `inputSchema` as exactly such a
> dict, so it goes straight onto the tool with no Pydantic model in between and
> no schema restated anywhere. Verified live: `tool.args` came back as the
> server's own `properties` block.

`coroutine=` (rather than `func=`) is the right constructor argument, because the
MCP call is async; `await tool.ainvoke({...})` then runs it from inside the node.

**No new dependency was installed, and none is needed.** RESEARCH's Package
Legitimacy Audit tags the third-party LangChain-to-MCP bridge package `[ASSUMED]`
and recommends against it. Hand-binding cost **fifteen lines**. Plan 16-09 should
not revisit this.

**Zero-dependency claim, measured:** `git diff -- pyproject.toml` is empty across
this plan's three commits.

### Q2 — can the Claude Agent SDK session be pointed at a replayed endpoint without a branch?

**Answer: yes — but the redirect lands one process further out than you expect,
and the replay server needs a shape `replay_server.py` does not have.**

This is the finding that changes 16-09's fixture design. Read the whole section.

---

## 2. The Claude Agent SDK transport, as it actually is

### 2.1 The SDK ships no MCP client, and speaks no HTTP to a model

`claude-agent-sdk==0.2.128` imports `mcp.types` and `mcp.server` — never
`mcp.client`. An **external** MCP server declared on
`ClaudeAgentOptions.mcp_servers` (`{"type": "http", "url": …, "headers": …}`) is
connected by the *Claude Code CLI*, not by the Python process. The SDK's
transport **is** that CLI.

Consequence: the `client_anthropic.py` posture — SDK reads `ANTHROPIC_BASE_URL`,
replay server answers — does not apply to the SDK. It applies to the CLI.

### 2.2 The CLI is bundled with the pip package

```
claude_agent_sdk/_bundled/claude   →  2.1.220 (Claude Code)
```

271 MB, shipped inside the wheel, found by `SubprocessCLITransport._find_bundled_cli()`
*before* any `PATH` search. **A CI runner that installs the `claude-agent` extra
already has the CLI.** No system dependency, no install step, no new package.

This is the fact that makes a keyless CI leg possible at all, and it was not
obvious from anything in the tree.

### 2.3 The redirect that works

Observed green, keyless and offline:

| Variable | Value in CI | Read by |
| --- | --- | --- |
| `ANTHROPIC_BASE_URL` | the replay server's origin | the bundled CLI |
| the vendor credential variable | any placeholder (`ANTHROPIC_AUTH_TOKEN=spike` was used) | the bundled CLI |

The leg itself reads **neither**. It carries no branch: live mode is the same
file with those variables unset. The `client_adk.py` / `client_anthropic.py`
posture holds verbatim — the only change is *who* honours the redirect.

### 2.4 What the CLI actually sends — four observations for the fixture design

Recorded by the spike's stand-in over a complete run:

```
HEAD /api/hello                                      → unrouted probe
POST /v1/messages   tools=[]                messages=1   → session-title turn
POST /v1/messages   tools=[3 CCF tools]     messages=1   → the tool turn
POST /v1/messages   tools=[3 CCF tools]     messages=3   → the final turn
```

1. **`"stream": true` on every request — SSE is mandatory.**
   The shipped `examples/external/00-hello-context/replay_server.py` answers with
   `JSONResponse(recorded)`. **The CLI will not accept that.** 16-09's replay
   server needs a server-sent-event response path for this leg:
   `message_start` → `content_block_start` → `content_block_delta` →
   `content_block_stop` → `message_delta` → `message_stop`, with `tool_use`
   blocks carrying their arguments as an `input_json_delta` `partial_json`
   string. A worked, minimal implementation is `_sse()` in
   `tests/examples/test_s2_client_transport_spike.py` — copy its frame sequence,
   not its scripting.

2. **The CLI opens with a session-title turn that carries no tools.**
   Ordinal-per-path fixture matching still works, but the fixture set for this
   leg is **three** responses, one of which has nothing to do with the CCF
   conversation. `fingerprint()`'s anthropic reduction (`model`, sorted
   `tool_names`, `message_count`) distinguishes it from the two real turns, so
   the existing matcher needs no change — only more fixtures.

3. **The CLI probes its base URL with `HEAD /api/hello` before using it.**
   The spike answered 404 and the CLI proceeded. 16-09's replay server must
   route or tolerate non-`POST` methods on unknown paths; the shipped one
   registers `POST` only, so an unrouted `HEAD` currently produces a 405 rather
   than the loud, named 500 its D-03 discipline intends.

4. **The system prompt carries the current date.**
   `# currentDate\nToday's date is …` appears in the request body, so a
   body-hash fixture matcher would go red every midnight. The existing
   `fingerprint()` reduction does not read it and is therefore already immune —
   worth stating so nobody "improves" the matcher into a date dependency.

### 2.5 Making the harness's tool surface exactly CCF's

Out of the box the model-facing tool list carried **28 CLI built-ins** alongside
the three CCF tools (`Bash`, `Edit`, `Write`, `WebFetch`, `Task*`, …). Two
problems with that: it is not the claim Section 2 makes, and it couples every
captured fixture's `tool_names` fingerprint to the CLI's built-in inventory,
which changes between CLI versions.

Four `ClaudeAgentOptions` settings, together, reduce it to exactly the CCF door:

```python
tools=[]                 # withdraw every built-in tool
skills=[]                # withdraw ambient skills
setting_sources=[]       # withdraw user/project/local settings
strict_mcp_config=True   # refuse MCP servers this process did not name
```

Measured after: `tools=['mcp__ccf__get_context', 'mcp__ccf__get_lineage',
'mcp__ccf__get_replay_record']` and nothing else — asserted by
`test_the_claude_agent_leg_saw_only_ccf_tools`.

`allowed_tools` alone does **not** do this: it gates invocation, not
advertisement. `permission_mode="bypassPermissions"` was tried and is **not
needed** — `allowed_tools` suffices, and an example that teaches
`bypassPermissions` would be teaching the wrong thing for a governed-context SDK.

### 2.6 Run hygiene the CLI needs in CI

The CLI writes state and, unconstrained, would write it into the developer's
real `~/.claude`. The spike sets, per run:

```
HOME=<tmp>  CLAUDE_CONFIG_DIR=<tmp>/config
CLAUDE_AGENT_SDK_SKIP_VERSION_CHECK=1
DISABLE_TELEMETRY=1  DISABLE_ERROR_REPORTING=1
DISABLE_AUTOUPDATER=1  DISABLE_NON_ESSENTIAL_MODEL_CALLS=1
```

With those set, the only egress observed was to the two loopback ports.

**Cost:** the whole Claude leg — CLI start, MCP connect, three model turns, one
`get_context` call — runs in **≈0.8 s**. It is not a slow leg.

---

## 3. What plan 16-09 should do with this

| # | Finding | Action for 16-09 |
| --- | --- | --- |
| 1 | LangGraph needs no bridge package | Do not install one. Repoint the leg's arguments only; the shape is proven. |
| 2 | The CLI is bundled in the wheel | The `claude-agent` extra is the whole dependency. No system install, no new pin. |
| 3 | `ANTHROPIC_BASE_URL` determinizes the Claude leg with no branch | Keep the shipped posture; the leg needs no change for CI. |
| 4 | The CLI requires **SSE** | The Section-2 replay server needs an event-stream response path. This is the one structural change to `replay_server.py`'s shape. |
| 5 | Three fixtures per Claude run, one of them a title turn | Size the capture accordingly; keep `fingerprint()`'s reduction as it is. |
| 6 | `HEAD /api/hello` preflight | Route non-`POST` methods, or the probe takes a 405 instead of the intended diagnostic. |
| 7 | The date is in the request body | Do not widen `fingerprint()` to a body hash. |
| 8 | `tools=[] / skills=[] / setting_sources=[] / strict_mcp_config=True` | Keep all four on the leg; without them the fixtures bind to the CLI's built-in inventory. |
| 9 | The stand-in here is **scripted**, not captured | 16-09 still owes live-captured, diff-reviewed fixtures plus a schema guard. This spike deliberately did not capture any. |

## 4. What this spike does **not** establish

* **No fixture was captured.** The Claude leg's model side was scripted in the
  test module. Capturing and diff-reviewing real fixtures is 16-09's task, and
  nothing here substitutes for it.
* **No live model was reached.** Both legs ran entirely on loopback. The live
  path (`ANTHROPIC_BASE_URL` unset) is unexercised by this spike.
* **The legs point at the Section-1 fabric.** They read
  `examples/external/00-hello-context`'s credit-context product because that is
  the only Experience door that exists today. 16-09 repoints them.
* **Nothing about Google ADK changed.** `client_adk.py` was neither run nor
  modified here; the shipped external example is byte-untouched, asserted by
  `test_the_shipped_external_example_is_untouched`.
