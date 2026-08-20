# Phase 20: Client Access from Three Harnesses — Research

**Researched:** 2026-08-20
**Domain:** Foreign-harness MCP clients (Google ADK / Claude Agent SDK / LangGraph) over `mcp+stdio`
**Confidence:** HIGH on Q3 legs 1 and 3, Q4, Q5, Q6 (all measured); MEDIUM on Q3 leg 2 (contingent on orchestrator Q1); MEDIUM on Q7 (recommendation, not measurement)

<user_constraints>
## User Constraints (from `20-CONTEXT.md`)

### Locked decisions — H-01..H-14, RULED, not re-openable

- **H-01** The pre-spawned-endpoint premise is rejected as physically impossible. Every
  installed harness takes `command + args` and spawns the child itself.
- **H-02** The runner may import `ccf`; it resolves the deployment root → `binding.yaml`'s
  `server:` key → an opaque `command + args` pair, seeds for CI, and invokes each client
  with that pair. Each client imports its harness, an MCP client and stdlib, and **nothing
  from `ccf`**.
- **H-03** The runner hands the pair over via **`argv`**, as explicit flags. Rejected: a
  single env var; a runner-generated `.mcp.json`.
- **H-04** A declared **scenario document** ships in the new directory, and `D-32` is
  narrowed on the record: it governs producer *output* (a committed store, a populated
  graph), not a declared *input* document a fabric-side runner interprets. The narrowing
  must be recorded as its own `D-IMPL` entry.
- **H-05** The CI subject is a **seeded temporary copy**, never the tracked tree. Seed,
  **close the writer**, spawn the door against the copy, run `consume.py` against the same
  copy for criterion 4's reference address.
- **H-06** The default path is "the harness invokes the registered tool", **no model**.
- **H-07** Leg 2 runs the real `claude` CLI against a replayed model; the asymmetry —
  *who holds the MCP session* — is written into the README rather than smoothed over.
- **H-08** The replay harness is **copied** for leg 2 only.
- **H-09** `--live` means one thing across all three legs: point at a real populated
  deployment. For leg 2 it additionally drops the replay.
- **H-10** The directory is `examples/hw1-harness-clients/`.
- **H-11** The example root holds only the three `client_*.py`; the runner lives in a
  subdirectory.
- **H-12** Client purity is gated by **extending** `tests/examples/test_client_example_purity.py`.
  **No rule is weakened to accommodate a file.** The new coverage carries a named sabotage
  control in the same plan.
- **H-13** `examples/s2-01-external-consumers/` moves **out of `examples/` entirely**.
- **H-14** `examples/external/00-hello-context/` stays CI-green and is marked historical
  in its README.

**Plus:** the **ten ROADMAP Success Criteria are closed** and are not expanded during
planning (Dave, 2026-08-20). **No new SDK mechanism** — a diff touching any file under
`src/ccf/client/` is a blocking review event. `.venv/bin/python` always. No `state.*` or
`roadmap.*` SDK writer.

### Claude's discretion (this research recommends; planning decides)

- Filename, location, schema and row count of the declared scenario document (`H-04`)
  → recommended in **Q4**
- The runner subdirectory name (`H-11`) → recommended `runner/`
- The retired-material destination path (`H-13`) → recommended in **Q6**
- One seeded copy per leg vs sequential against one (`H-05`) → recommended in **Q4**
- The precise `argv` flag names (`H-03`)
- Which `CLNT-NN` numbers are minted and their wording → recommended in **Q7**

### Deferred — OUT OF SCOPE, do not research or plan

- A model-driven leg for ADK and LangGraph
- A fourth harness
- `HarnessAdapterProtocol` work (`D-IMPL-24`/`D-IMPL-25`) — producer-side
- Retiring `examples/external/00-hello-context/` entirely
- A repository-wide retired-material convention
</user_constraints>

## Summary

**The two blocking questions are both answered YES, and neither triggers a stop.**

- **Q1 — the `claude` CLI drives offline in CI with no additional setup.** `claude-agent-sdk==0.2.128`
  ships the CLI *inside its wheel* (`_bundled/claude`, hash-declared in RECORD), CI already
  installs it via `.[dev]`, and `tests/examples/test_s2_client_transport_spike.py` is a green
  in-tree proof of the offline recipe (`15 passed`, measured). `H-07` stands.
- **Q2 — a zero-`ccf` client can build the encoded `WireRequest` with `json.dumps` alone.**
  Proven end to end against the live door: hand-built string accepted, product served,
  content address `b2c2f9a4…` returned. Criterion 5 and criteria 1–3 are compatible.

Two of the three legs were **executed against a live stdio MCP server during this
research** and both work with no model, no runner and no agent loop. ADK's
`McpToolset.get_tools()` → `tool.run_async(args=..., tool_context=None)` returns the
MCP result dict directly; LangGraph's `StructuredTool` wrapped around a raw
`mcp.client.stdio.stdio_client` session inside a two-edge `StateGraph` returns the
tool's text. Neither needs a dependency this repo does not already have.

**One measurement contradicts a ruling's stated mechanics.** `H-12` says adding the
new root to `CLIENT_EXAMPLE_ROOTS` "gates the three clients untouched". It does not:
`_permitted()` admits **only stdlib and `ccf.client`**
(`tests/examples/test_client_example_purity.py:110-115`), so the shipped assertion
would go red on `import google.adk`, `import mcp`, `import langgraph`. `H-12`'s
*intent* (extend that module, do not weaken the structural rule) survives intact —
but the permitted set must become a per-root parameter, and that is a design item the
planner must carry, not a line of glue. Details in Q5.

**Primary recommendation:** three sibling `client_*.py` at
`examples/hw1-harness-clients/`, each `asyncio.run(main())` over its harness's own
stdio params, taking `--server-command` / `--server-arg` / question flags on argv;
a `runner/` subdirectory holding `run.py` (imports `ccf`, structurally outside
`reader_visible_modules`); and a `check_example_purity(root, permitted=...)`
signature change so the gate can express "stdlib + these harnesses, and never `ccf`".

---

## Q1 — claude CLI offline drivability

**VERDICT: DRIVABLE OFFLINE IN CI, WITH NO ADDITIONAL CI SETUP.** `H-07`'s default
path for leg 2 stands. The `D-IMPL-NN`-and-stop branch that `20-CONTEXT.md`'s
`## Risk flagged for research` reserved is **not** taken.

The risk was framed as "the `claude` CLI is not a Python package, cannot be pinned in
`pyproject.toml`, and has no install step in `ci.yml` today." **The first clause is
false for this SDK version, which makes the other two moot.**

**`claude-agent-sdk==0.2.128` ships the CLI binary inside its own wheel.**

- `claude_agent_sdk/_internal/transport/subprocess_cli.py:235-248` — `_find_bundled_cli()`
  resolves `claude_agent_sdk/_bundled/claude` and returns it as the CLI path.
- The binary is present and executable: `.venv/lib/python3.12/site-packages/claude_agent_sdk/_bundled/claude`,
  271,825,824 bytes, `ELF 64-bit LSB executable, ARM aarch64`.
- It is wheel content, not a post-install download, and is hash-declared:
  `claude_agent_sdk-0.2.128.dist-info/RECORD:16` carries
  `claude_agent_sdk/_bundled/claude,sha256=FZ5KUdeW878UZ3V3EA9--4RWEbHOrwwwy9jUZQ2UIYU,271825824`.
  (The `_bundled/.gitignore` reads "downloaded during build" — that is the SDK's *build*,
  not the consumer's install.)
- The wheel is platform-tagged: `dist-info/WHEEL` → `Tag: py3-none-manylinux_2_17_aarch64`.
  So the publisher ships one wheel per platform, each carrying the matching binary; CI's
  `ubuntu-latest` x86_64 resolves the x86_64 wheel.

**It already reaches CI by the existing install step.** `pyproject.toml` `dev` includes
`ccf[harnesses]` → `claude-agent = ["claude-agent-sdk==0.2.128"]` (`pyproject.toml:88,98`),
and every CI job runs `python -m pip install -e ".[dev]"` (`.github/workflows/ci.yml:28,166,272,311`).
The CLI is therefore already installed in CI today, pinned, by version, as a normal
dependency. **No node step, no install script, no PATH assumption, nothing to add.**

**There is an existing, green, in-tree proof that it drives fully offline.**
`tests/examples/test_s2_client_transport_spike.py` runs the real CLI against a scripted
model over loopback. Measured here: `15 passed in 4.60s`.

Its offline recipe (`tests/examples/test_s2_client_transport_spike.py:590-611`) is the one
Phase 20 leg 2 should inherit verbatim:

    ANTHROPIC_BASE_URL   = <loopback replay/scripted server>
    ANTHROPIC_AUTH_TOKEN = "spike"          # non-empty; never validated offline
    HOME                 = <tmp dir>        # CLI state out of the developer's home
    CLAUDE_CONFIG_DIR    = <tmp>/config
    CLAUDE_AGENT_SDK_SKIP_VERSION_CHECK = 1
    DISABLE_TELEMETRY = 1 / DISABLE_ERROR_REPORTING = 1
    DISABLE_AUTOUPDATER = 1 / DISABLE_NON_ESSENTIAL_MODEL_CALLS = 1

Those four `DISABLE_*` vars plus the version-check skip are precisely the answer to the
open worry about "auth, version, telemetry or statsig handshakes the replay server would
also have to answer": **the CLI is configurable into asking for none of them**, and the
scripted server in that spike answers only the Messages API.

**Falsification performed.** Removing `claude` from `PATH` did *not* turn the spike red —
but that proves nothing, because `_find_cli()` (`subprocess_cli.py:150-211`) falls back to
a hard-coded location list including `~/.local/bin/claude`, and this host has two other
`claude` installs (`/home/parkave/.local/bin/claude`, native ELF aarch64 2.1.235; and
`~/.nvm/versions/node/v24.13.1/bin/claude`). With **both** stripped from `PATH` the suite
still passed `15 passed in 4.64s`, and since the leg's own env sets `HOME` to a temp dir,
the home-relative fallbacks cannot have hit either — leaving the bundled binary as the
only source. That is the positive evidence that the bundled path is live and sufficient.

### Residual limits — stated, not smoothed

1. **UNVERIFIED: that the x86_64 wheel for 0.2.128 bundles the binary.** Cannot be checked
   from here (no network guarantee, and CI status needs a token this session lacks). It is
   strongly implied — platform-tagged wheels exist precisely to carry per-platform payloads,
   and this dependency has been in CI's `dev` install for phases. **Recommended cheap
   confirmation before leg 2's plan is executed:** have Dave run one CI job, or
   `pip download claude-agent-sdk==0.2.128 --platform manylinux_2_17_x86_64 --no-deps` and
   check the wheel for `_bundled/claude`.
2. **The spike's MCP transport is HTTP, not `mcp+stdio`.** The offline-model recipe transfers;
   the transport does not. Leg 2 is the first Claude-SDK client in this tree to bind an
   `mcp+stdio` door (`McpStdioServerConfig`, `claude_agent_sdk/types.py`).
3. **The spike is the single live coupling `H-13` breaks** (`LEG_DIR`,
   `test_s2_client_transport_spike.py:68` → `examples/s2-01-external-consumers`). Its env
   recipe must be extracted into the new example **before** that directory moves, or the
   move deletes the only worked offline recipe in the tree. Sequencing consequence: leg 2's
   plan lands before the retirement plan, or the retirement plan carries the extraction.
4. **271 MB per install** is a real CI cost already being paid; it is not new to this phase.

## Q2 — The zero-CCF tool argument

**VERDICT: YES — a client importing nothing from `ccf` can build the tool argument with
`json.dumps` alone.** Criterion 5 (zero `ccf` imports) and criteria 1–3 (register, call,
print) are compatible. **Proven end to end against the live door, not reasoned about.**

### What the door publishes

Measured by listing tools on a real `mcp+stdio` session against
`examples/hw1-companies-over-revenue` (`.venv/bin/python server/serve.py <deployment>`):

    tool: request_context_product
    required: tenant, product_class, version, request, subject, intent, freshness, asked_at
    optional: parameters (object, default {})
    request: {"type": "string", "title": "Request"}      # ← opaque
    resources: []                                         # none exposed on this door

Definition: `runtime/ccf_runtime/mcp/egress.py:531-546` (`@server.tool`, handler
`request_context_product`). `request: str` is `C-16`'s required encoded `WireRequest`.

### The encoding is stdlib-reproducible

`WireRequest` has **three** fields — `product_id: str`, `parameters: Mapping[str, Any]`,
`temporal_boundary: datetime | None` (`src/ccf/products/door.py:198-200`).

Canonical form is plain JSON with sorted keys and compact separators
(`src/ccf/contracts/canonical.py:184-191`):

    json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)

with `datetime` rendered as RFC3339 UTC (`canonical.py:123-129`). A client needs no CCF
code to produce that — and in fact needs no byte-exactness either, because the door
*parses* the string (`door_question`) rather than comparing bytes.

### The literal call a client makes — executed, and it served

    wire = json.dumps({"product_id": "hw1.companies-over-revenue",
                       "parameters": {"revenue_threshold": 1000000000},
                       "temporal_boundary": None},
                      sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    # -> {"parameters":{"revenue_threshold":1000000000},"product_id":"hw1.companies-over-revenue","temporal_boundary":null}

    await session.call_tool("request_context_product", {
        "tenant": "hw1-demo", "product_class": "hw1.companies-over-revenue",
        "version": "1.0.0", "request": wire,
        "subject": "companies-over-revenue", "intent": "revenue-screening",
        "freshness": "published-annual-filings",
        "asked_at": "2026-03-02T12:00:00+00:00",
        "parameters": {"revenue_threshold": 1000000000},
    })

Returned (empty deployment, so `count: 0` — see the note below):

    content_address: b2c2f9a434308a2c78413107871c541eab311b95890cb1ea4c5f6f8de355df2e
    replay_ref:      ccf-artifact://hw1-demo/hw1.replay-record/277db390...@43eca126...
    refusal:         null
    request (echo):  {"parameters":{"revenue_threshold":1000000000},
                      "product_id":"hw1.companies-over-revenue","temporal_boundary":null}

The response is a JSON document with `content_address`, `product_json`, `refusal`,
`replay_ref` and the echoed `request`. **`json.loads` and printing is the whole client-side
decode** — criterion 4's content address is a top-level key. No CCF code on either side of
the round trip.

An earlier probe sending `"revenue_threshold": "1000000000"` (string) came back as a
well-formed **refusal** — `kind: product-request-violation`, `reason: type-mismatch`,
declared `number` vs presented `str`. Two useful facts: the door decoded the hand-built
string correctly (so the encoding was right and only the *value* was wrong), and the
refusal envelope is itself printable JSON, which is what `CLNT-02`'s "the fabric refusing
is the fabric working" looks like from a foreign harness.

### Three findings planning must absorb

1. **`request` is not self-describing.** Its JSON Schema is a bare `{"type": "string"}`.
   A foreign client cannot learn the `WireRequest` shape from tool discovery — it must be
   *told*, by the example's README and its own source. This is the sharpest teaching burden
   in the phase: the whole point is "an MCP tool registration and nothing else," and this
   one argument is the exception a reader will trip on. **The README must show the literal
   `json.dumps` call.** (Not a defect to fix — `C-16` ruled the argument required, and
   changing the schema would be SDK mechanism, which criterion 7 forbids.)
2. **Eight address values are configuration, not constants.** `tenant`, `product_class`,
   `version`, `subject`, `intent`, `freshness`, `asked_at` and the parameters are deployment
   facts (`deployment/binding.yaml` `question:`; `ccf_config.yaml:19-20,29` for tenant
   `hw1-demo` and version `1.0.0`). Under CLAUDE.md §9 they may not be literals in example
   code, so **`H-03`'s argv flag set is wider than the `command + args` pair `H-02`
   describes** — the runner must pass the question address too. `H-02`/`H-03`'s *intent*
   (the client receives the door's location as input, never as knowledge) is unchanged and
   is in fact reinforced; only the flag count grows. Recommend one `--question-json` flag
   over eight scalar flags, resolved by the runner from `binding.yaml`.
3. **The empty deployment answers with `count: 0` and `debt.signal: fail_closed`.** It does
   yield a real content address — confirming `test_hw1_two_transports` — but it is exactly
   the weak demonstration Dave rejected when ruling out the empty deployment as the CI
   subject. `H-04`/`H-05`'s seeded temp copy is what makes criterion 4's comparison
   interesting rather than merely true.

---

## Q3 — The three harness call shapes, with no model

### Installed versions — measured

`.venv/bin/python -c "import importlib.metadata …"`, run 2026-08-20:

| Package | Version | Note |
|---|---|---|
| `google-adk` | 2.5.0 | |
| `claude-agent-sdk` | 0.2.128 | |
| `langgraph` | 1.2.9 | |
| `langgraph-prebuilt` | 1.1.0 | present (`ToolNode`, `create_react_agent`) |
| `langchain-core` | 1.5.1 | |
| `mcp` | 1.28.1 | |
| `anthropic` | 0.120.2 | |
| **`langchain-mcp-adapters`** | **MISSING** | CONTEXT.md's claim **CONFIRMED** |
| **`langchain`** | **MISSING** | no model provider package of any kind |

Confirmed a second way against the tree:
`ls .venv/lib/python3.12/site-packages/` shows `langchain_core`,
`langchain_protocol`, `langgraph`, `langgraph_sdk`, `langgraph_prebuilt` — and no
`langchain_mcp_adapters`, no `langchain_anthropic`, no `langchain_openai`.

### The door being called

- Tool name: `PRODUCT_REQUEST_TOOL = "request_context_product"` (`src/ccf/products/door.py:132`).
- Registered at `runtime/ccf_runtime/mcp/egress.py:531` with signature
  `(tenant, product_class, version, request, subject, intent, freshness, asked_at, parameters={})`
  → returns **one** `TextContent` block of canonical JSON
  (`runtime/ccf_runtime/mcp/egress.py:533-542`).
- The exact encoding of the `request:` argument is **Q2 (orchestrator)**.
- The SDK's own adapter spawns it as
  `StdioServerParameters(command=sys.executable, args=[str(program), str(root)], env=dict(os.environ))`
  (`src/ccf/client/adapters/mcp_stdio.py:429-433`) where `program` is
  `binding.yaml`'s `server:` resolved against the directory *holding* the deployment,
  and `root` is the deployment root. That two-token `args` list **is** the
  `command + args` pair `H-02` has the runner resolve.

**Environment pitfall, measured in the SDK's own docstring and worth repeating in
every client.** `mcp.client.stdio.get_default_environment()` hands a child only
`HOME`, `LOGNAME`, `PATH`, `SHELL`, `TERM`, `USER`
(`src/ccf/client/adapters/mcp_stdio.py:415-423` records this and the defect it
caused). Every leg should therefore pass `env=dict(os.environ)` explicitly. In this
checkout `ccf` is installed **editable via a `.pth` finder** in site-packages
(`.venv/lib/python3.12/site-packages/__editable__.ccf-0.1.0.pth`) and `PYTHONPATH`
is empty, so the filtered default would *probably* still work here — but it drops
`COVERAGE_PROCESS_START`, which the same `.pth` reads, and it is fragile. Pass the
environment.

### Leg 1 — Google ADK 2.5.0: **WORKS, measured**

Script run against a trivial `FastMCP` stdio echo server exposing
`request_context_product`:

```python
from mcp import StdioServerParameters
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams

toolset = McpToolset(connection_params=StdioConnectionParams(
    server_params=StdioServerParameters(command=..., args=[...], env=dict(os.environ)),
    timeout=30.0))
tools = await toolset.get_tools()                      # spawns the child, tools/list
tool  = next(t for t in tools if t.name == "request_context_product")
result = await tool.run_async(args={...}, tool_context=None)
await toolset.close()
```

Observed output: `TOOLS: ['request_context_product']` and
`RESULT: {'content': [{'type': 'text', 'text': 'ECHOED:hello'}], 'structuredContent': {...}, 'isError': False}`.

- **No `LlmAgent`, no `Runner`, no model is needed.** `McpToolset` is a
  `BaseToolset` that owns its own `McpSessionManager`; `get_tools()` is what spawns
  the child (`google/adk/tools/mcp_tool/mcp_toolset.py:365-379`).
- **`tool_context=None` is accepted.** `McpTool.run_async` is annotated
  `tool_context: ToolContext` (`.../mcp_tool.py:335-337`) but the `None` path was
  measured to work end to end. Constructing a real `ToolContext` is not a cheap
  alternative: `ToolContext` is an alias of `google.adk.agents.context.Context`
  (`google/adk/tools/tool_context.py:26`) whose `__init__` requires an
  `InvocationContext` (`google/adk/agents/context.py:125-142`), i.e. a session
  service, a session and an agent.
  **Flag for the planner:** passing `None` where a type says `ToolContext` is a
  contract the next ADK release could tighten. Two mitigations, pick one at plan
  time: (a) assert on the returned dict shape so a change is loud rather than
  silent, and pin `google-adk==2.5.0` (it is already pinned — see `pyproject.toml`);
  (b) call `toolset._execute_with_session(lambda s: s.call_tool(...), "…")`
  (`.../mcp_toolset.py:324`) — but that is a private method and reads worse in a
  teaching example. Recommend (a).
- **Async-only.** Both `get_tools` and `run_async` are coroutines.
- **Noise.** ADK emits `UserWarning: [EXPERIMENTAL] feature …` for
  `PLUGGABLE_AUTH`, `_MCP_GRACEFUL_ERROR_HANDLING`, `BASE_AUTHENTICATED_TOOL`, and
  `JSON_SCHEMA_FOR_FUNC_DECL`, and the server logs `Processing request of type …`
  to stderr. All on **stderr**, so a runner comparing stdout is unaffected — but the
  README should not promise clean output, and any `check=True` subprocess assertion
  must read stdout only.
- **Use `McpToolset`, not `MCPToolset`.** The uppercase alias emits
  `DeprecationWarning: MCPToolset class is deprecated, use McpToolset instead`
  (`.../mcp_toolset.py:531-534`). Measured.
- **`isError` handling.** ADK 2.5.0 has `_MCP_GRACEFUL_ERROR_HANDLING` enabled, so a
  tool error is converted into `{"error": "..."}` rather than raised
  (`.../mcp_tool.py:368-388`). Leg 1 must branch on that key or a refusal will print
  as a success.

### Leg 3 — LangGraph 1.2.9: **WORKS, measured, no new dependency**

Same echo server, raw `mcp` + `StructuredTool` inside a `StateGraph`:

```python
from langchain_core.tools import StructuredTool
from langgraph.graph import END, START, StateGraph
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
```

Observed output: `RESULT: ECHOED:hello-lg`. `StructuredTool.from_function(coroutine=…,
args_schema=<raw JSON Schema dict>)` accepts a plain mapping — no Pydantic model
needed — and `await tool.ainvoke({...})` drives it from inside a node.

- **`examples/s2-01-external-consumers/client_langgraph.py` is the shape to
  inherit**, transport swapped. Its `connect()` helper
  (`examples/s2-01-external-consumers/client_langgraph.py:83-91`) becomes
  `stdio_client(StdioServerParameters(...))` instead of `streamablehttp_client(url, headers=…)`;
  everything else — the `TypedDict` state, `bind()`, the two-node
  `discover`→`read` topology, `StructuredTool.from_function(coroutine=…, args_schema=…)`
  — transfers verbatim. **Read it before `H-13` moves it** (it also already carries
  the written rationale for *not* taking a bridge package, lines 24-27).
- **Does a graph with no model read as "a LangGraph agent" for criterion 3?**
  Honest answer: **yes, and it is the only reading available in this tree.** No
  langchain model provider is installed, so a model-driven LangGraph leg is not
  merely deferred by `H-06` — it is not runnable at all today. What criterion 3
  literally asks for is *"A LangGraph agent … registers the door as a tool, calls
  it, and prints"*, and a compiled `StateGraph` whose node binds a
  `langchain_core` tool and invokes it satisfies every clause. The existing
  `client_langgraph.py` docstring already frames this correctly: *"LangGraph exposes
  no agent loop to hook, so the topology is the caller's"* (line 96). Recommend the
  README say exactly that rather than leaving a reader to wonder.
- **Dependency decision (flagged, not decided): `langchain-mcp-adapters`.** It is
  not installed and it is not needed — the hand-binding cost is ~15 lines, measured.
  Acquiring it would (a) add a supply-chain surface for a demonstration whose whole
  point is *how little you need*, (b) reverse a rationale already written into this
  repository's tree, and (c) require `pyproject.toml` + lockfile churn in a phase
  whose criterion 7 is "no new SDK mechanism". **Recommendation: do not acquire it.**
  If planning disagrees, that is a `D-IMPL-NN`, not a detail.
- `langgraph-prebuilt` 1.1.0 **is** installed, so `ToolNode` is available if a plan
  prefers it to a hand-written node. It is not required and it drags `messages`
  state semantics that only make sense with a model. Recommend the plain node.

### Leg 2 — Claude Agent SDK 0.2.128: shape only (verdict is Q1's)

`McpStdioServerConfig` is a **`TypedDict`**, not a dataclass, at
`.venv/lib/python3.12/site-packages/claude_agent_sdk/types.py:603-609` — measured:
`{type: NotRequired[Literal["stdio"]], command: str, args: NotRequired[list[str]],
env: NotRequired[dict[str, str]]}`. `ClaudeSDKClient` and `ClaudeAgentOptions` are
both public exports (`claude_agent_sdk/__init__.py:56, 534, 567`). Its role is
**configuration handed to the `claude` CLI**, not an in-process MCP client:
`claude_agent_sdk/_internal/transport/subprocess_cli.py` locates the binary with
`shutil.which("claude")` (CONTEXT.md `H-07`, line ~136). So leg 2's code is
structurally different from legs 1 and 3 — this is exactly the asymmetry `H-07`
tells the README to state rather than smooth over.

**Under a PASS Q1 verdict** (the CLI drives offline against the copied
`replay_server.py`), leg 2 is roughly:

```python
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient  # names per types.py
options = ClaudeAgentOptions(
    mcp_servers={"ccf": McpStdioServerConfig(command=..., args=[...], env={...})},
    allowed_tools=["mcp__ccf__request_context_product"],
    ...)
```
with `ANTHROPIC_BASE_URL` pointed at the replay server, and the printed product
recovered from the tool-result block in the streamed messages. Note the tool name
the *model* sees is namespaced `mcp__<server>__<tool>`, not the bare
`request_context_product` — so leg 2's printed identity check must account for it.

**Under a FAIL Q1 verdict**, per `H-07`'s own closing paragraph and the CONTEXT.md
risk note, this is a `D-IMPL-NN` and a **stop** — not a quiet demotion of leg 2 to
`--live`. Criterion 6 requires a deterministic default for every leg and criterion
10 requires `make ci` exit 0.

**A second, independent Q1-adjacent risk the planner must carry either way:** the
`claude` binary is not a Python package, cannot be pinned in `pyproject.toml`, and
`.github/workflows/ci.yml` has no install step for it today. Even a PASS verdict
leaves an unpinned always-on CI dependency.

### Async/sync: where `asyncio.run` goes

| Component | Sync or async | Where the boundary sits |
|---|---|---|
| `consume.py` | sync (`def main() -> int`, `sys.exit(main())`) | the SDK adapter hides `asyncio` internally |
| the Phase 20 runner | sync | `subprocess.run` per child; no event loop of its own |
| `client_adk.py` | async core | `asyncio.run(main())` under `if __name__ == "__main__":` |
| `client_langgraph.py` | async core | same |
| `client_anthropic.py` | async core (SDK is async) | same |

So all three clients own exactly one `asyncio.run` at module bottom, matching
`examples/s2-01-external-consumers/client_langgraph.py:192-193`. The runner never
enters an event loop.

### Does `install_no_model_guard()`'s technique transfer?

**Read in full** at `examples/03-harness-portability/legs/deterministic.py:92-123`.
It is **not** a model-import guard, which matters: it is a `@contextmanager` that
patches `socket.socket.connect` and `socket.create_connection` to raise
`AssertionError`, restoring both in `finally` (lines 115-123). Its docstring records
the two disciplines worth inheriting: the guard is process-global and installed
before any leg runs, and *"the driver refuses to proceed unless it actually fires"*
(line 97-98) — i.e. the guard carries its own non-vacuity control.

**The technique transfers, but not uniformly, and the split is the interesting
finding:**

- **Legs 1 and 3 make no socket call at all in the default path.** `stdio_client`
  spawns a child over pipes; `FastMCP.run(transport="stdio")` serves over pipes.
  A socket-refusal guard around either leg is therefore not merely a model guard —
  it proves *no network egress whatsoever*, which is strictly stronger than
  "no model call" and is the same claim example 03 makes.
- **Leg 2 cannot be guarded this way.** Its default path deliberately reaches
  `ANTHROPIC_BASE_URL` — a real TCP connection to the copied local replay server.
  Its equivalent proof is the replay server's own fail-loud-on-drift/exhaustion
  behaviour (`examples/external/00-hello-context/replay_server.py`), already built.

**Mechanical constraint the planner must not miss:** the guard is *process-global*,
and the three clients run as **child processes of the runner**. The runner cannot
install a socket guard in a child's interpreter without the client importing
something — which would be exactly the non-teaching clutter the clients must not
carry. So the guard belongs in a **test** under `tests/examples/` that executes legs
1 and 3 in-process (`runpy.run_path`, or importing `main()` and driving it), inside
a copied guard, with a control that opens a socket and watches the guard refuse.
That is also what example 03 already does — its docstring notes the drive *"now runs
inside `pytest` as well as under `make example-03`"* (line 102).

Recommend **one** such test covering legs 1 and 3, not three per-leg ones, and an
explicit written statement that leg 2 is excluded and why.

---

## Q4 — The runner, the seed, and criterion 4

### The seed-then-close sequence

`tests/client/conftest.py::seed` (lines 106-149) is the pattern. Reproduced as the
runner needs it, with **hw1's** vocabulary rather than the fixture's:

```python
attributes = yaml.safe_load((root / "scenario.yaml").read_text())["attributes"]
registry = ControlPlaneRegistry()
booted = load_config_and_boot(
    root / "ccf_config.yaml",
    registry=registry,
    connection=load_binding_document(root).connection,   # NEVER recomposed
)
try:
    for index, row in enumerate(declared_rows):
        booted.handle.worker.ingest(SignalEnvelope(
            tenant_id=booted.tenant_id,
            envelope_id=f"...{index}",
            source=SourceIdentity(system_id="..."),
            ingestion_timestamp=SEEDED_AT,
            observed_time=SEEDED_AT,
            raw_payload={
                attributes["reference"]: ...,
                attributes["name"]:      ...,
                attributes["revenue"]:   ...,   # hw1's third key, NOT "score"
            },
        ))
finally:
    booted.handle.close()          # <- releases `_LIVE_WRITERS`; load-bearing
```

Two differences from the test fixture that will bite a plan that copies blindly:

1. **hw1's third attribute key is `revenue`, not `score`.**
   `examples/hw1-companies-over-revenue/deployment/scenario.yaml` declares
   `{reference: company_ref, name: company_name, revenue: company_revenue}`;
   `tests/client/fixtures/deployment/scenario.yaml` declares a `score` key
   (`tests/client/conftest.py:136` reads `attributes["score"]`). Read the keys from
   the document; do not restate them.
2. **The connection must come from `load_binding_document(root).connection`**, not
   be recomposed. `binding.yaml` states `connection.database_path.path: graph.sqlite3`
   *relative to the deployment root*, so a recomposed connection seeds a different
   file and the door boots an empty graph — the exact drift `seed`'s own docstring
   warns about (`tests/client/conftest.py:141-148`).

The writer close is `booted.handle.close()`. Confirmed load-bearing:
`ccf.graph._writer::_LIVE_WRITERS` holds the writer per graph and a second boot
raises `SingleWriterViolation` — recorded at `tests/client/conftest.py:113-118` and
again at `tests/client/conformance/conftest.py:11-14`.

### What transfers from `examples/external/00-hello-context/run.py` — and what does not

| Element | Location | Transfers? |
|---|---|---|
| `--live` flag, `argparse`, `--legs` subset selection | `run.py:565-585` | **Yes** |
| Children terminated in `finally` with `_terminate()` kill fallback | `run.py:306-314, 786-788` | **Yes** — but see below |
| `_run_leg()`: `subprocess.run([sys.executable, script], env=…, capture_output=True)` then raise on non-zero with both streams in the message | `run.py:360-372` | **Yes, directly** — this is exactly what Phase 20's runner does three times |
| Bounded `READY <port>` handshake via `select.select(..., READY_TIMEOUT_SECONDS)` | `run.py:254-302` | **NO for the door. Yes for leg 2's replay server.** |
| `_assert_zero_ccf_imports()` static grep | `run.py:441-450` | **NO** — `H-12` refuses it explicitly |
| `_assert_seven_heading_readme()` | `run.py:452-…` | No — that is ext-00's own `README_HEADINGS` contract |

**The `READY` handshake does not apply to the door, and this is the structural
difference `H-01` already named.** ext-00's runner `_spawn`s `serve.py` itself and
waits for `READY <port>` because it must learn a TCP port. Phase 20's door is
**stdio and is spawned by the client library**; the runner never sees it, never
gets a port, and has no handshake to wait for. The runner's whole job for legs 1 and
3 is: seed a copy → resolve `command + args` → `subprocess.run` the client → compare.

**The handshake DOES still apply to leg 2's replay server**, which is an HTTP
server the runner stands up exactly as ext-00 does — same `_spawn`, same `READY`
line, same `finally` termination. That is one more reason `H-08`'s "copy the replay
harness for leg 2 only" is the right shape: what gets copied is `replay_server.py`
**and** the `_spawn`/`_terminate`/`READY` machinery that drives it.

### The declared scenario document (`H-04`)

**Precedent shape confirmed.** `examples/external/00-hello-context/artifacts/events.yaml`
is a YAML document with a `# yaml-language-server: $schema=…` header, a `semver:`,
a `tenant_id:`, and an `envelopes:` list using the **SDK's own envelope vocabulary**
(`source: {system_id}`, `raw_payload:`) rather than a flat shape needing translation
— its own header says *"A translation removed is one that cannot drift"* (line 25).

**Recommendation:**

| Question | Recommendation | Why |
|---|---|---|
| Filename | `artifacts/scenario-rows.yaml` | `scenario.yaml` is **taken** — hw1's deployment already owns that name for its attribute-role document, and a second file called `scenario` next door is a name collision a reader has to disambiguate. |
| Location | `examples/hw1-harness-clients/artifacts/` | mirrors `00-hello-context/artifacts/`; keeps the example root holding **only** the three `client_*.py`, which `H-11`/`H-12` require. |
| Schema | `semver`, `tenant_id`, `observed_at`, and a `companies:` list of `{reference, name, revenue}` | Keyed by the **roles** hw1's `scenario.yaml` names, not by the raw source keys — the runner reads `scenario.yaml` for the mapping and applies it, so the two documents cannot drift. |
| Rows | 5–6, with 3 above the threshold and 2–3 below | Criterion 4 compares content addresses; a non-empty, visibly *filtered* answer makes the printed output teach something. A row set where everything passes the threshold does not demonstrate the screening. |

**`no-hardcoding` is satisfied by that shape, confirmed by measurement.**
`RULE_TREE_SCOPE["no-hardcoding"] = ("src", "runtime", "examples", "tests")`
(`tools/lints/__main__.py:124`) — so `examples/` **is** in scope. But the walk is
`for path in sorted(root.rglob("*.py"))` (`tools/lints/__main__.py:180`): the lint
only reads Python modules. **A YAML document under `examples/` is not scanned at
all**, and the runner reading it is an interpreter, which is exactly the posture
`examples/hw1-companies-over-revenue/deployment/scenario.yaml`'s own header
describes (lines 4-9).

**Also confirmed for criterion 7:** `RULE_TREE_SCOPE["harness-imports"] = ("src", "runtime")`
(`tools/lints/__main__.py:125`). The three clients importing `google.adk`,
`claude_agent_sdk` and `langgraph` under `examples/` do **not** trip the
harness-import lint. No exemption is needed and none should be added.

### Criterion 4 — pointing `consume.py` at the temp copy

**`CCF_BINDING`, an environment variable, and there is no other channel.**
`consume.py` calls `ProductClient.for_product("hw1.companies-over-revenue")` with no
address argument (`examples/hw1-companies-over-revenue/consume.py:48`); the address
is `CCF_BINDING`'s business (module docstring lines 6-8). The two shipped forms are
`CCF_BINDING="inprocess:<deployment-root>"` and `CCF_BINDING="mcp+stdio:<deployment-root>"`
(`Makefile:317` and `Makefile:337`) — the address is **one token, the deployment
root**, so the runner points `consume.py` at the temp copy by setting
`CCF_BINDING=inprocess:<tmp>/deployment` in the child's environment. No argv change,
no `binding.yaml` edit.

**`as_of` pins identically across all four invocations.** `consume.py --as-of` takes
an ISO 8601 string with a UTC offset (`consume.py:37`). The `make` targets use
`--as-of 2026-08-01T00:00:00+00:00`. The runner passes the *same literal* to
`consume.py` and the same instant into each client's `asked_at` argument. Note
`binding.yaml`'s `question.asked_at: "2026-03-02T12:00:00+00:00"` is the deployment's
answer to *`as_of=None`* only — with `--as-of` supplied it is not consulted, so a
plan must supply it explicitly on all four legs or the comparison is not pinned.

### What `H-05`'s `copytree` must copy

**Copying `deployment/` alone is not sufficient.** `binding.yaml`'s `server:` key is
the ONE key resolved against **the directory holding the deployment**, not against
the deployment root (`src/ccf/client/adapters/binding_document.py:698-738`;
`D-10`), and the loader **refuses** a `server:` value resolving *inside* the root
(same file, lines 730-738). `examples/hw1-companies-over-revenue/deployment/binding.yaml`
states `server: server/serve.py`, so the copy must reproduce the parent/child
relationship:

```
<tmp>/                     <- the "directory holding the deployment"
├── deployment/            <- copytree of examples/hw1-companies-over-revenue/deployment
└── server/                <- copytree of examples/hw1-companies-over-revenue/server
    ├── serve.py
    ├── compose.py
    └── egress-door.yaml
```

`tests/client/conformance/conftest.py:60-63` does exactly this shape for the fixture
(copies the program into `root.parent` and rewrites `server:` via `declare_server`).
Phase 20 needs **no rewrite** if it copies both directories under a common parent,
because `server: server/serve.py` is already correct relative to that parent.

`server/serve.py` also does `from compose import compose` relying on its own
directory being on `sys.path` as a spawned script (`serve.py:60-62`), so `compose.py`
and `egress-door.yaml` must travel with it.

**Nothing in that tree is path-absolute.** Checked: `binding.yaml` uses relative
`config:`, `plan:`, `artifact_store:`, `connection.database_path.path`, and
`server:`; `ccf_config.yaml` and `scenario.yaml` carry only relative
`# yaml-language-server: $schema=…` comments, which are editor hints and are not
read by the loader; `egress-door.yaml` carries only `.invalid` URLs. The one thing
that will be *stale* in a copy is the `$schema` comment's `../../../` depth — cosmetic,
and it should be left alone rather than rewritten.

Also confirmed clean: `deployment/graph.sqlite3` **exists in the working tree today**
but is gitignored (`examples/hw1-companies-over-revenue/deployment/.gitignore`), as
is `artifact-store/`. A `copytree` of a developer's populated tree would carry a
pre-populated graph in and make the seed's own effect unmeasurable. **Recommend the
runner copy with `shutil.copytree(..., ignore=shutil.ignore_patterns("graph.sqlite3*", "artifact-store", "__pycache__"))`**
so CI and a developer's machine produce the same subject. This is a real hazard, not
a hypothetical: the file is present at
`examples/hw1-companies-over-revenue/deployment/graph.sqlite3` right now.

### Per-leg copies

`H-05` leaves this to discretion. **Recommend one seeded copy per leg** (three
copies). Reasons: `tests/client/conformance/conftest.py` hands out a distinct
directory per subject *"so two subjects sharing one graph is impossible rather than
merely refused"* (lines 51-55); and it lets the runner run the legs concurrently
later without a redesign. The cost is three seeds of ~6 rows, which is negligible.
Criterion 4's `consume.py` reference run takes a **fourth** copy, seeded identically
— or reuses leg 1's copy *after* leg 1's child has exited. Recommend the fourth
copy: it makes the address comparison a claim about four independent assemblies,
which is strictly the stronger reading of *"the harness is the variable, the product
is the constant"*.

---

## Q5 — The purity gate and its sabotage control

### `H-11` HOLDS — measured

`reader_visible_modules` is:

```python
return tuple(sorted(path for path in root.glob("*.py") if path.is_file()))
```

`tests/examples/test_client_example_purity.py:70-80`. **`glob`, not `rglob`** — it is
non-recursive and root-level only, and the docstring states the intent explicitly:
*"Every `.py` file sitting **directly** in the example root is reader-visible;
anything in a subdirectory is not."* A runner under `examples/hw1-harness-clients/runner/`
is structurally invisible to this gate. **`H-11` is not contradicted.**

### `H-12` is contradicted **in its stated mechanics** — BLOCKING for planning

`H-12` says adding the root to `CLIENT_EXAMPLE_ROOTS` *"then gates the three clients
untouched"*. **It does not.** The permitted set is:

```python
PERMITTED_PACKAGE = "ccf.client"

def _permitted(module: str) -> bool:
    root = module.partition(".")[0]
    if root == "__future__" or root in sys.stdlib_module_names:
        return True
    return module == PERMITTED_PACKAGE or module.startswith(f"{PERMITTED_PACKAGE}.")
```

`tests/examples/test_client_example_purity.py:59-62, 108-115`. **Only stdlib and
`ccf.client`.** Adding `examples/hw1-harness-clients/` to `CLIENT_EXAMPLE_ROOTS`
makes `test_the_client_example_imports_only_the_client_and_stdlib` (which **is**
parametrized over every root, line 155-161) go red on `import google.adk`,
`from mcp import ClientSession`, `from langgraph.graph import StateGraph`,
`from claude_agent_sdk import …`.

Worse, the semantics are **inverted** between the two roots:

| Root | `ccf.client` | harness + `mcp` |
|---|---|---|
| `hw1-companies-over-revenue` | **permitted** (it is `consume.py`'s whole point) | forbidden |
| `hw1-harness-clients` | **forbidden** (criterion 5 says so by name) | permitted |

**This is not `H-12` being wrong** — extending that module, keeping the structural
`reader_visible_modules` rule, and putting the runner outside it are all still the
right calls. It is `H-12`'s *mechanics* under-describing the work. The gate needs a
per-root permitted set. **Recommended shape** (keeps every existing control valid,
adds no hole):

```python
#: What each gated client example's reader-visible code may import, by root.
PERMITTED_IMPORTS: dict[pathlib.Path, frozenset[str]] = {
    HW1_ROOT:      frozenset({"ccf.client"}),
    HARNESS_ROOT:  frozenset({"google.adk", "claude_agent_sdk", "langgraph",
                              "langchain_core", "mcp"}),
}
CLIENT_EXAMPLE_ROOTS = tuple(PERMITTED_IMPORTS)      # non-vacuity preserved

def check_example_purity(root, permitted: frozenset[str]) -> list[str]: ...
```

and a **separate, unconditional refusal of `ccf`** for the harness root — because
criterion 5's literal wording is *"an AST check refuses a `ccf.*` import in any of
the three client programs"*, and "not in the permitted set" is a weaker claim than
"named and refused". A `ccf` import must produce a violation naming `ccf`.

This is example-tree/test-tree work only. **It touches no file under `src/`**, so it
does not trigger the criterion-7 stop.

### The budget gate comes along for the ride — a second consequence

`tests/examples/test_client_example_budget.py:49-53` **imports `CLIENT_EXAMPLE_ROOTS`
and `reader_visible_modules` from the purity module**, and
`test_the_client_example_is_within_its_declared_budget` is parametrized over every
root (lines 153-156). So adding the new root also arms the budget gate against it:

- the new README must state **exactly one** `declared budget: <n> lines`
  (`BUDGET_PATTERN`, lines 57-60; hw1 states `**Declared budget: 80 lines.**` at
  `examples/hw1-companies-over-revenue/README.md:15`);
- the budget is enforced **per module**, not on the sum
  (`check_example_budget`, lines 118-131), so each of the three clients must fit;
- physical lines, **no exclusions** — blanks, comments and docstrings all count
  (lines 64-71).

Given `client_langgraph.py` in `s2-01` is 200 lines *with* a long teaching docstring,
and the stdio version is smaller than the HTTP one, a budget in the **120–150** range
is realistic. Measure before declaring; a number the files cannot meet is how a gate
gets weakened at the worst moment. This is a plan-visible deliverable, not a detail.

### What the command-identity checks will require of the new README

The command-identity machinery is pinned to **index 0**, not parametrized:
`documented_commands(CLIENT_EXAMPLE_ROOTS[0])` at lines 340, 372, 396 and 425, and
`MAKE_TARGETS = ("example-hw1:", "example-hw1-mcp:")` at line 293. So adding a root
does **not** silently point these at the new README — which is good (no accidental
red) and bad (no coverage unless deliberately added). `H-03`'s entire rationale for
argv over an env var was *"visible in the README's documented command … which read
the documented command string"*, so **coverage must be added deliberately.**

What it will require, given `H-03`:

1. **A `make` target per documented command**, and the target's recipe must be
   **exactly one line** (`make_recipe`, lines 300-318 asserts `len(recipes) == 1`).
2. **Character-identical** README line and recipe (`command_identity_violations`,
   lines 321-347).
3. The command must spell **`.venv/bin/python`** literally — not `$(PYTHON)`, which
   is refused by name (lines 338-346). The two hw1 recipes already do this and carry
   a `Makefile` comment forbidding the "fix" back to a variable (`Makefile:310-312`).
4. `README_COMMAND = re.compile(r"^(CCF_BINDING=.*)$")` (line 288) **will not match**
   the new commands, which start with `.venv/bin/python`. A second pattern is
   needed. Recommend anchoring on the invocation rather than an assignment, e.g.
   `^(\.venv/bin/python examples/hw1-harness-clients/.*)$`, and generalising
   `documented_commands(root, pattern, targets)` to take all three as parameters —
   same discipline the purity function already follows.
5. `test_every_documented_command_names_a_distinct_binding_scheme` (line 371) is
   **hw1-specific by construction** (it is about `CCF_BINDING` schemes). It must not
   be parametrized over the new root; the new root's analogous claim is *"the three
   documented commands differ only in the client program"*, which is a **new**
   assertion worth writing in the same shape (split each command, assert the
   `client_*.py` token differs and every other token is identical).

### The sabotage controls Phase 20 must add (`CLNT-12` / `D-22`, `C-17` shape)

`tests/client/test_surface.py` is the model: every property is a **module-level
function taking its subject as a parameter**, and every one has numbered `CONTROL n`
tests that feed it a doctored subject and watch it refuse — `CONTROL 1`..`CONTROL 4`
for the surface assertion (lines 385-424), `CONTROL 5`..`CONTROL 9`+ for the
construction-site scan (lines 634-718), including the vacuity cases (`CONTROL 6` zero
sites, `CONTROL 7` a walk that read nothing, `CONTROL 8` an unresolvable root,
`CONTROL 9` an unparsable file). The existing purity module already follows the same
discipline without the numbering.

**Minimum control set Phase 20 must ship in the same plan as the gate:**

| # | Control | Watches |
|---|---|---|
| C-20-1 | `import ccf` prepended to a `tmp_path` copy of a client | the plain-`Import` shape |
| C-20-2 | `from ccf.client import ProductClient` prepended | the `ImportFrom` shape |
| C-20-3 | `import ccf` deferred **inside a function body** | the shape Phase 19 measured the grep missing |
| C-20-4 | `from .runner import …` relative import | sibling reach |
| C-20-5 | `import ccf.client.adapters.mcp_stdio` (a **submodule**, and one that is *permitted for the other root*) | that the per-root permitted set is actually per-root and did not leak hw1's allowance across |
| C-20-6 | an empty new-root copy → violation, not a pass | vacuity (mirrors `test_the_gate_refuses_an_empty_example_root`) |
| C-20-7 | a non-existent new root → violation | vacuity |
| C-20-8 | the new README's documented command vs a divergent recipe | command identity, in `command_identity_violations`' existing shape |

C-20-5 is the one that is *specific to this phase's change* and it is the one most
likely to be omitted. A per-root permitted set implemented as a module-level union
would pass every other control and fail only this one.


---

## Q6 — Retirement, Makefile, CI wiring

### There is no existing quarantine convention — CONFIRMED

```
$ ls examples/
00-quickstart  01-agent-basics  02-skilling  03-harness-portability
04-cross-process  05-workflow-hitl  06-decision-replay  07-artifact-store-mcp
08-e2e-demo  external  hw1-companies-over-revenue  s1-00-companies-over-revenue
s1-01-hello-context-product  s2-01-external-consumers
```

Measured: `find . -maxdepth 4 -type d \( -name '_retired*' -o -name 'attic' -o -name 'archive*' -o -name 'retired*' -o -name 'deprecated' \)` returns **nothing** (`.git`, `.venv`, `node_modules` pruned). CONTEXT.md's `H-13` note is correct.

The nearest existing thing is `.planning/phases/16-…/abandoned/`, which holds unexecuted Phase 16 plans. That is a `.planning/` bookkeeping convention for *documents*, not a code-tree convention, and it is not a precedent for where retired example **code** goes.

**Recommended destination: `docs/retired/16-external-consumers/`.**

| Candidate | Assessment |
|---|---|
| **`docs/retired/16-external-consumers/`** | **Recommended.** Reads as non-example on sight; sits outside `examples/`; `docs/` is already this repo's home for retired-material *records* (`docs/surface/examples/ERGO-03-FROZEN.md`, `docs/surface/examples/RETIREMENT-COUPLINGS.md`, `docs/SURFACE-CHANGES.md`); it is **not published** (`mkdocs` reads only `public/`, CLAUDE.md §14 / `mkdocs.yml:90` `base_path: ["."]` with `restrict_base_path: true` and nothing in `public/` including from there); and it is outside every `RULE_TREE_SCOPE` tree, so no lint fires on code nobody maintains. |
| `retired/` at the repo root | Also fine and arguably clearer, but it invents a new top-level tree — which is closer to the *repository-wide retired-material convention* CONTEXT.md's Deferred list explicitly says is not this phase's job. |
| `tests/fixtures/…` | Refuse: `tests` **is** in `RULE_TREE_SCOPE` for `no-hardcoding`, and moving dead code into a linted tree is a maintenance liability. |
| `examples/_retired/` | Already rejected by `H-13`. |

The move must carry a `README.md` (this repo's precedent for retiring things is
deletion **plus a written record**) naming Phase 16, `D-IMPL-152`, and Phase 20's
trio as the replacement.

### Every reference to `examples/s2-01-external-consumers/`, swept

Repo-wide grep for `s2-01` / `s2_01` / `external-consumers`, excluding `.git`,
`.venv` and `.planning/`:

| File:line | Shape | Liveness | What Phase 20 must do |
|---|---|---|---|
| **`tests/examples/test_s2_client_transport_spike.py:68`** | `LEG_DIR = REPO_ROOT / "examples" / "s2-01-external-consumers"` | **LIVE — build goes red** | See below. This is the load-bearing one. |
| `docs/surface/examples/SECTION-2-TRANSPORT.md:24` | prose naming `client_langgraph.py` | documentary | Update the path, or add a retired note |
| `docs/surface/examples/RETIREMENT-COUPLINGS.md:129-130` | inventory rows | documentary | Regenerate via `tools/retirement_sweep.py --report` (see `CLNT-16`) |
| `tests/examples/test_artifact_schema_headers.py:445` | docstring referring to a `fixtures/` dir plan 16-09 never shipped | documentary | Update or delete the sentence |
| `docs/DECISIONS.md:402` (`D-IMPL-125`) | prose, historical record | documentary — **do not rewrite** | A decision entry is a record of what was decided then; add the new `D-IMPL` entry instead |

**Not found anywhere:** `Makefile`, `.github/workflows/*.yml`, `mkdocs.yml`,
`public/`, `pyproject.toml`. So there is **no `make` target and no CI job** naming
`s2-01` — consistent with the ROADMAP's description of the orphans.

**The `--8<--` snippet markers in `client_langgraph.py` (`mcp-connect`,
`mcp-discover`, `mcp-resource`) are DEFINED but never INCLUDED.** Searched `public/`
for those marker names: the only published includes of those three names are from
`examples/external/00-hello-context/client_bare.py`
(`public/tutorial/adopters-guide.md:409, 417, 427`). Moving `s2-01` therefore breaks
**no published snippet**. Verified.

### `tests/examples/test_s2_client_transport_spike.py` — the blocker inside `H-13`

This is the single live coupling and it is more consequential than a path fix. Facts,
all measured this session:

- It is a **26-assertion-file with 15 tests**, no skip guards of any kind (grepped
  for `importorskip`, `skipif`, `pytest.skip`, `shutil.which` — none present), and it
  is collected by `[tool.pytest] testpaths = ["tests"]`, so `make test`, `make ci-core`
  and `make ci` all run it.
- **It runs green on this host right now.**
  `.venv/bin/python -m pytest tests/examples/test_s2_client_transport_spike.py -q`
  → **`15 passed in 4.87s`**. The Claude leg alone:
  `6 passed in 3.39s`, with `2.86s setup` on
  `test_the_claude_agent_leg_reads_a_context_product_over_mcp` — that setup is the
  real drive.
- Its own docstring says *"This module is a spike, and plan 16-09 retires it"*
  (line 3). Plan 16-09 was abandoned when Phase 16 was retired
  (`D-IMPL-152`), so the spike outlived its retiring owner.
- It asserts `test_the_shipped_external_example_is_untouched()` (line 665) — it
  reads `examples/external/00-hello-context/` and asserts byte-unchanged.

**Recommendation:** retire this module in the same change that moves `s2-01`. Its
subject moves out of `examples/`, its retiring owner no longer exists, and Phase 20
ships a superseding demonstration of exactly the two harnesses it spikes. Keeping it
alive means maintaining a path into quarantined material — the precise "partial
state" `CLNT-17` forbids. **But** — see the next item before deleting.

### Evidence relevant to the orchestrator's Q1 (reported, not adjudicated)

`test_s2_client_transport_spike.py` is **an existing, green, in-tree proof that the
`claude` CLI can be driven fully offline against a scripted Anthropic-shaped
stand-in**, keyless, in ~3 seconds. Its recipe (`tests/examples/test_s2_client_transport_spike.py:598-611`):

```
ANTHROPIC_BASE_URL=<local stand-in>   ANTHROPIC_AUTH_TOKEN=spike
HOME=<tmp>                            CLAUDE_CONFIG_DIR=<tmp>/config
CLAUDE_AGENT_SDK_SKIP_VERSION_CHECK=1 DISABLE_TELEMETRY=1
DISABLE_ERROR_REPORTING=1             DISABLE_AUTOUPDATER=1
DISABLE_NON_ESSENTIAL_MODEL_CALLS=1
```

Two honest limits on that evidence, both of which are Q1's to weigh:

1. **Its MCP transport is HTTP, not stdio.** `examples/s2-01-external-consumers/client_claude_agent.py:99-113`
   configures `mcp_servers={server: {"type": "http", "url": ..., "headers": ...}}`.
   Phase 20 needs `{"type": "stdio", "command": ..., "args": [...]}`. The **CLI**
   half is proven; the **stdio-MCP-under-the-CLI** half is not.
2. **`claude` is on this host's PATH (`/home/parkave/.local/bin/claude`) and there
   is no install step for it in `.github/workflows/ci.yml`** — grepped; the workflow
   installs Python and `pip install -e ".[dev]"` only, with no Node/npm step. Whether
   the `tests` job in GitHub Actions is currently green on this module is
   **UNVERIFIED** — I have no CI token in this session and could not check. **If it
   is currently red in Actions, that is a pre-existing defect Phase 20 inherits, and
   `H-07` makes it Phase 20's problem regardless of Q1's verdict.**

**Consequence for retirement:** if leg 2's default path survives Q1, Phase 20 should
lift the offline-CLI env recipe out of the spike into leg 2's runner **before**
retiring the spike. Do not delete the only working recipe and then rediscover it.

### `H-14` — the `00-hello-context` historical marking

**What exercises it:**
- `Makefile:216-217` — `example-ext-00: $(ENV) $(PYTHON) examples/external/00-hello-context/run.py`,
  and it **is** in the `examples` list (`Makefile:230`), so it runs under `make ci`.
- `Makefile:395-399` — `example-ext-00-live-anthropic` and `example-ext-00-live-adk`,
  opt-in, not in `examples`.
- `tests/examples/test_ext00_hardening.py` (26 tests), `test_ext00_fixture_schemas.py`,
  `test_ext00_serve_output.py`.
- `public/tutorial/adopters-guide.md:409, 417, 427` — **three published snippet
  includes** from `client_bare.py`. Confirms `H-14`'s decision not to move it.

**Does any test assert on that README's content? YES — and this constrains `H-14`
concretely.** `run.py::_assert_seven_heading_readme()` (`examples/external/00-hello-context/run.py:452`)
requires the README to carry **exactly seven `## ` headings, by exact name and in
order** (`README_HEADINGS`, `run.py:133-139`):

```
What this demonstrates | Run it | The story | Artifact-by-artifact
Whitepaper / CLAUDE.md sections exercised | What to change first | What would fail
```

and the shipped README carries exactly those seven at lines 3, 45, 77, 162, 189, 206
and 225. **So `H-14`'s marking must be prose inside an existing heading — most
naturally the first paragraph under `## What this demonstrates` — and must NOT add a
`## ` heading.** A new heading turns `make example-ext-00`, and therefore `make ci`,
red. This is the one way to get `H-14` wrong, and it is easy to get wrong.

`tests/examples/test_ext00_hardening.py` asserts on `fixtures/README.md`'s content
(line 454-463, the Gemini fixture label) but **not** on the main README's prose. So a
prose sentence under an existing heading breaks nothing. **Verified.**

### Floor constants, snippet gates, docs indexes — measured, none break

| Gate | Constant | Current | Headroom for the move |
|---|---|---|---|
| `tests/invariants/test_citation_coverage.py::test_the_citation_walk_is_not_vacuous` | `MINIMUM_SCANNED_CITATION_HOSTS = 953` | **1091 files read** (2 of them under `s2-01`) | 138 — safe |
| `…::test_the_citation_walk_read_real_citations` | `MINIMUM_CITATIONS_READ = 797` | **995 citations** | 198 — safe |
| `…::test_the_held_back_thirteen_…` | `== 14`, exact | scoped to `docs/surface-changes/` only | unaffected |
| `tests/products/*` `MINIMUM_*` floors | 9 / 12 / 14 / 12 | scan `src`/`runtime` | unaffected |

**One ceiling has ZERO headroom and Phase 20 will walk into it.**

```
MAXIMUM_UNANCHORED_PY_CITATIONS = 0     current: 0
```
(`tests/invariants/test_citation_coverage.py:394-404`, measured this session via
`sweepable_citation_sites()`.) **Every new file Phase 20 adds must cite Python
targets as `path.py::Symbol`, never as `path.py:NN`** — unless the line-number
citation is immediately preceded by a backticked anchor, which is the only thing
`anchor_before` accepts (`tools/lints/citations.py:459-…`). Given this repository's
citation-dense docstring style and the volume of new prose Phase 20 ships (three
clients, a runner, a README, a scenario document), **this will fire unless a plan
task states the rule.** `D-IMPL-114`/`D-IMPL-123` are the governing rulings.

No `examples/README.md` index exists, and `mkdocs.yml`'s nav has no examples section
— so no docs index or nav file goes red on a directory move. Verified.

`tools/retirement_sweep.py` exists and `CLNT-16` requires its inventory current
**before** any example tree moves. `docs/surface/examples/RETIREMENT-COUPLINGS.md`'s
own header says *"Generated by `tools/retirement_sweep.py --report`. Do not
hand-edit"*, and its rows are all owned by Phase-16 plans that no longer exist —
so the committed inventory is **stale by construction**. Its checker suite is
`tools/docs_tests/test_retirement_sweep.py` (`Makefile:505`), which `make gate-tools`
runs. A plan discharging `CLNT-16` must re-run the sweep and commit the regenerated
report, and must decide what a row owned by a retired plan means now.

### Makefile — the new targets and where they wire

Measured structure:

- `examples:` (`Makefile:230`) = `example-00 … example-08 example-ext-00`, described
  as *"the ten network-free examples"*.
- `ci-core:` (`Makefile:135`) = `lint typecheck test gate-tools`.
- `ci:` (`Makefile:169`) = `ci-core examples docs-strict gate-tools`.
- `example-hw1` / `example-hw1-mcp` (`Makefile:315-337`) are **NOT** in `examples` —
  their help text says *"needs a populated deployment; never CI"*.
- The `--live` opt-ins (`Makefile:389-399`) are declared `.PHONY` at lines 58-60 and
  are deliberately outside `examples`.

**Recommended wiring** (criterion 10):

```make
.PHONY: example-hw1-harness-clients
example-hw1-harness-clients: ## Run examples/hw1-harness-clients — three harnesses, one door, deterministic
	$(ENV) $(PYTHON) examples/hw1-harness-clients/runner/run.py

# Opt-in, never CI (D-11), alongside example-ext-00-live-*
example-hw1-harness-clients-live-adk:
	$(ENV) $(PYTHON) examples/hw1-harness-clients/runner/run.py --live --legs adk
example-hw1-harness-clients-live-anthropic:
	...--live --legs anthropic
example-hw1-harness-clients-live-langgraph:
	...--live --legs langgraph
```

and append the deterministic target to `examples:` at `Makefile:230`, updating the
help text *"the ten network-free examples"* → eleven in the same edit. Add all four
names to the `.PHONY` block at `Makefile:55-60`.

**A naming collision to resolve at plan time.** The command-identity gate wants the
README's documented command and the recipe **character-identical**, and hw1's two
recipes prove that means a literal `.venv/bin/python`, not `$(PYTHON)`
(`Makefile:310-312` carries a comment forbidding the "fix"). But every target in the
`examples:` list uses `$(ENV) $(PYTHON)` because CI runs `make PYTHON=python`
(`Makefile:108-111` — CI has no `.venv`). **These two requirements conflict.**
Resolutions, in preference order:

1. **Two targets.** `example-hw1-harness-clients` (in `examples:`, `$(ENV) $(PYTHON)`,
   what CI runs) plus per-client documented targets using the literal
   `.venv/bin/python` (not in `examples:`, what the README documents and what the
   identity gate reads). This is exactly the shape hw1 already has —
   `example-hw1`/`example-hw1-mcp` are literal-interpreter and outside `examples:`.
2. Document only the three per-client commands and exclude the runner command from
   the identity gate. Weaker: it leaves the command CI actually runs undocumented.

Recommend (1). It is precedent, not invention.

`.github/workflows/ci.yml` needs **no new job**: the `examples suite` job runs
`make examples` (line 282-283), so appending the target is the whole CI wiring —
*except* for whatever the Q1 verdict requires for the `claude` binary.


---

## Q7 — Requirements and sequencing

### Recommended `CLNT-23+` rows

The `CLNT` lane runs to `CLNT-22` today (`.planning/REQUIREMENTS.md:218`, traceability
table lines 341-362). Phase 20 mints `CLNT-23` onward.

**The mapping is NOT 1:1 with the ten criteria, and forcing it to be would be wrong.**
Criteria 1, 2 and 3 are the same requirement three times (one per harness) — one row
covering all three, parametrized by harness, matches how the gate will actually be
written and how `CLNT-15` is worded for an analogous set. Criteria 8 and 10 each split
in two because they carry genuinely separable obligations (a *move* and a *marking*;
a *target* and a *green pipeline*). Nine rows:

| ID | Wording |
|---|---|
| **CLNT-23** | Three client programs — one Google ADK, one Anthropic Agent SDK, one LangGraph — each register the Phase 18.1 `mcp+stdio` door on `examples/hw1-companies-over-revenue` as an ordinary MCP tool, call it, and print the returned Context Product to the console, receiving the door's `command + args` as configuration rather than knowing it (criteria 1–3; `H-01`, `H-02`, `H-03`) |
| **CLNT-24** | The Context Product each harness prints carries the **same content address** as the one `consume.py` prints for the same question at the same `as_of`, produced by the runner against the same seeded subject rather than compared to a recorded value — the harness is the variable, the product is the constant (criterion 4; `H-05`) |
| **CLNT-25** | Client-side CCF-import purity is enforced by an **AST** gate that refuses a `ccf.*` import in any of the three client programs **by name**, extends the existing `tests/examples/test_client_example_purity.py` rather than duplicating it, weakens no rule to accommodate a file, and carries named sabotage controls in the same plan that adds it (criterion 5; `H-11`, `H-12`, `CLNT-12`/`D-22`) |
| **CLNT-26** | Every leg runs deterministically in the default path with no live model call, and `--live` has **one meaning across all three legs** — point at a real populated deployment — so no code path exists that CI never exercises (criterion 6; `H-06`, `H-09`) |
| **CLNT-27** | CI answers against a **seeded temporary copy** of the deployment, never the tracked tree, seeded through the deployment's own documents by a fabric-side runner that **closes the writer** before the door boots; the declared scenario document is an *input* document under `examples/` and the `D-32` narrowing that permits it is recorded as its own decision entry (`H-04`, `H-05`) |
| **CLNT-28** | No new SDK mechanism ships — no new transport, no new adapter, no change to `ccf.client` or the codec, no `HarnessAdapterProtocol` implementation — verified by the phase diff touching **no file under `src/ccf/client/`** (criterion 7) |
| **CLNT-29** | `examples/s2-01-external-consumers/` is moved out of `examples/` to a path that reads as non-example on sight, with **every** live reference handled in the same change — the transport spike that constructs its path, the coupling inventory, the surface prose — and no partial state left behind (criterion 8, first half; `H-13`, `CLNT-17`) |
| **CLNT-30** | `examples/external/00-hello-context/` stays CI-green and is marked historical **in prose under an existing README heading**, stating that its clients target the pre-Phase-17 surface over HTTP with bearer auth and that Phase 20's trio is canonical going forward (criterion 8, second half; `H-14`) |
| **CLNT-31** | One README names each harness, what the reader installs, what to change first to point it at their own deployment, that how the MCP server is assembled is out of scope, and **states the who-holds-the-MCP-session asymmetry plainly**; a `make` target for the example is wired into `examples` and `make ci` is exit 0 at the phase close (criteria 9 and 10; `H-07`, `H-10`) |

### Recommended wave breakdown

The three legs *look* parallel. They are not: they share a runner, a scenario
document and a seed, and two of them share a gate.

**Wave 0 — the shared substrate. One plan. Nothing else can start.**
- `examples/hw1-harness-clients/` created; `artifacts/scenario-rows.yaml` authored.
- `runner/run.py`: seed-and-close, per-leg `copytree` with the `graph.sqlite3*`
  ignore, `binding.yaml` → `command + args` resolution, `_run_leg`, `_terminate`,
  `--live` / `--legs`.
- The criterion-4 `consume.py` reference invocation and the address comparison.
- **Gate:** the runner produces a real content address from `consume.py` against a
  seeded temp copy, with **zero** client legs wired. If that does not hold, no leg
  can be proven and every subsequent wave is measuring the wrong thing.

**Wave 1 — legs 1 and 3, in parallel. Two plans.**
- `client_adk.py` + wiring; `client_langgraph.py` + wiring.
- Independent of each other; both depend only on Wave 0.
- Each proves criterion 4 for its own harness.

**Wave 2 — the purity gate. Its own plan, and it must be its own plan.**
- The per-root permitted set, the `ccf`-by-name refusal, the budget declaration,
  the command-identity extension, and the eight sabotage controls (C-20-1..8).
- **Separate because it carries a gate plus its controls** — `CLNT-12`/`D-22`'s
  standard, and this project's recorded history (Phase 19's `C-17`, `D-IMPL-156`+)
  is that a gate bundled into a feature plan ships unable to fail. It needs two of
  the three clients in the tree to be non-vacuous, hence after Wave 1 rather than
  beside it.
- The budget number must be **measured from the shipped files**, which is another
  reason it cannot precede Wave 1.

**Wave 2′ — leg 2, in parallel with Wave 2. One plan. CONTINGENT ON Q1.**
- `client_anthropic.py` (or `client_claude_agent.py`), the copied
  `replay_server.py`, the recorded fixtures, the `READY`-handshake spawn, and the
  offline-CLI env recipe lifted from the spike.
- **Structured so a bad Q1 verdict invalidates nothing else:** legs 1 and 3 are
  already green and gated by the end of Wave 2, criterion 4 is already demonstrated,
  and the purity gate already has two subjects. A FAIL verdict turns this plan into
  a `D-IMPL-NN` stop with the rest of the phase intact and presentable — which is
  exactly what `H-07`'s own closing sentence demands and what a leg-2-first ordering
  would forfeit.
- If Q1 fails, Wave 2's `CLIENT_EXAMPLE_ROOTS` entry and the budget must still be
  authored for a two-client root; that is a one-line difference, not a redesign.

**Wave 3 — retirement and hygiene. One plan.**
- The `s2-01` move, the spike's disposition (retire, **after** lifting the CLI env
  recipe if Wave 2′ needs it), the four documentary reference updates, the
  `retirement_sweep` re-run per `CLNT-16`, and the `00-hello-context` README
  sentence.
- **Last, not first** — `CLNT-16` says the sweep inventory must be current *before*
  a tree moves, and the sweep should be run against the tree Phase 20 actually
  produced, not the tree it started from. Also: `client_langgraph.py` must be read
  before it moves (Wave 1 does that), and the CLI env recipe must be extracted
  before the spike is deleted (Wave 2′ does that).

**Wave 4 — README and close.**
- The one README: the frame, the asymmetry, the two documented-command sets,
  the declared budget, "what to change first", the out-of-scope sentence.
- `make ci` green, `git diff --stat -- src/ccf/client/` empty (criterion 7).

Nine plans. The three legs are **not** three interchangeable parallel plans, and
planning them that way is how the runner gets written three times.

---

## Validation Architecture

### Test framework

| Property | Value |
|---|---|
| Framework | `pytest` 9.1.1 (measured), config in `pyproject.toml` (`testpaths = ["tests"]`, line 142) |
| Quick run | `.venv/bin/python -m pytest tests/examples -q` |
| Gate for the example | `make example-hw1-harness-clients` |
| Full suite | `make ci` (= `ci-core examples docs-strict gate-tools`, `Makefile:169`) |
| Interpreter | **`.venv/bin/python` always.** Bare `python` does not exist on this host. CI overrides with `make PYTHON=python`. |

### Criterion → validation map

| # | Criterion | Level | Automated command | Exists? |
|---|---|---|---|---|
| 1 | ADK registers, calls, prints; imports nothing from `ccf` | example run + AST gate | `make example-hw1-harness-clients`; `pytest tests/examples/test_client_example_purity.py -q` | ❌ Wave 0/1/2 |
| 2 | Anthropic Agent SDK, same | example run + AST gate | same | ❌ Wave 2′ — **contingent on Q1** |
| 3 | LangGraph, same | example run + AST gate | same | ❌ Wave 1/2 |
| 4 | Same content address as `consume.py` | assertion **inside the runner**, fabric-side | `make example-hw1-harness-clients` (runner raises on mismatch, `_run_leg` shape) | ❌ Wave 0 |
| 5 | AST purity gate + named sabotage control | unit test + **8 controls** | `pytest tests/examples/test_client_example_purity.py -q` | ⚠️ module exists; per-root permitted set and controls C-20-1..8 are new |
| 6 | Deterministic default, `--live` opt-in | CI target + socket guard | `make examples`; a new `tests/examples/` test running legs 1 and 3 in-process under a copied `install_no_model_guard` with its own "the guard fires" control | ❌ Wave 1/2 |
| 7 | No new SDK mechanism | diff assertion at close | `git diff --stat <base>..HEAD -- src/ccf/client/` must be empty; plus `python -m tools.lints --all` (`harness-imports` scope is `src`+`runtime` only, so it is not the check) | ✅ command exists, assertion is new |
| 8 | Duplicates resolved in-phase | tree assertion + green pipeline | `test -d examples/s2-01-external-consumers` must fail; `make example-ext-00`; `pytest tests/examples/test_ext00_hardening.py -q`; `make gate-tools` | ⚠️ ext-00 gates exist; the move assertion is new |
| 9 | README content | structural test | a new `tests/examples/` test asserting the README's required elements by name, in the `_assert_seven_heading_readme` shape; plus `test_client_example_budget.py` parsing `declared budget` | ❌ Wave 4 |
| 10 | `make ci` exit 0, target wired the CI-determinism way | full pipeline | `make ci`; plus a test asserting the new target **is in the `examples:` prerequisite list** (a target wired nowhere is criterion 6's own failure mode) | ⚠️ `make ci` exists; the wiring assertion is new |

### Sampling rate

- **Per task commit:** `.venv/bin/python -m pytest tests/examples -q` (fast; the s2
  spike in that directory currently runs in ~5 s, so the directory stays cheap).
- **Per wave merge:** `make ci-core` — and note this repo's recorded lesson that a
  gate `ci-core` does not reach is not a gate (`Makefile:129-134`, DEF-17-08).
- **Phase gate:** `make ci` exit 0 before `/gsd:verify-work`, then the §3.1 cross-AI
  panel on shipped code.

### Wave 0 gaps

- [ ] `examples/hw1-harness-clients/runner/run.py` — the seed-and-close runner (CLNT-24, CLNT-27)
- [ ] `examples/hw1-harness-clients/artifacts/scenario-rows.yaml` — the declared input (CLNT-27)
- [ ] Per-root permitted set + 8 controls in `tests/examples/test_client_example_purity.py` (CLNT-25)
- [ ] A no-model socket-guard test for legs 1 and 3, with a control (CLNT-26)
- [ ] A README-structure test (CLNT-31)
- [ ] A `make`-target-wiring test (CLNT-31)
- [ ] A tree assertion that `examples/s2-01-external-consumers/` is gone (CLNT-29)
- [ ] Regenerated `docs/surface/examples/RETIREMENT-COUPLINGS.md` (CLNT-16 precondition)

No framework install is needed.

---

## Package Legitimacy Audit

**No package is installed by this phase, and none should be.** All three harnesses
are already dev dependencies composed by `ccf[harnesses]` into `dev`, and `mcp` is
already a dependency of the SDK's own `mcp+stdio` adapter. Verified present in the
venv at the versions in Q3's table.

| Package | Registry | Disposition |
|---|---|---|
| `google-adk` 2.5.0 | PyPI | already installed — no action |
| `claude-agent-sdk` 0.2.128 | PyPI | already installed — no action |
| `langgraph` 1.2.9 | PyPI | already installed — no action |
| `mcp` 1.28.1 | PyPI | already installed — no action |
| `langchain-mcp-adapters` | PyPI | **NOT installed. Recommended: do not acquire** (Q3, leg 3). Acquiring it is a `D-IMPL-NN`, not a plan detail. |

`slopcheck` was not run: no new package is recommended, so there is nothing to
audit. If planning overrides the recommendation on `langchain-mcp-adapters`, that
package must go through the legitimacy gate first.

---

## Project Constraints (from CLAUDE.md)

| § | Directive | How Phase 20 satisfies it |
|---|---|---|
| §6.4 | **No-Hardcoding**, scoped to `examples/` | The scenario rows live in a YAML document; the runner is an interpreter. Confirmed the lint reads only `*.py` (`tools/lints/__main__.py:180`), so the document is out of its reach and the runner must not spell the rows. |
| §7.3 | *"a harness that already speaks MCP needs no adapter for consumption"* | The claim under test. Legs 1 and 3 **measured true** this session; leg 2 measured *partly* true — the CLI needs the door as *configuration*, still no adapter. |
| §9 | Runnable end-to-end, one documented command, code and artifacts side by side, a README per example, **a broken example is a broken build** | The runner is one command in `examples:`; the artifacts sit in `artifacts/`; one README (`H-10`, ruling 2). |
| §11 | Mechanism, not values; no hidden model calls | The socket guard proves the second. |
| §11 | Prefer Protocols over inheritance | N/A — this phase adds no SDK type. |
| §13 | No new SDK mechanism | Criterion 7. **A conclusion that something under `src/` must change is a `D-IMPL-NN` and a stop.** Nothing in this research reached that conclusion. |
| §3.1 | Cross-AI panel **on shipped code** at close, then single-agent review, verify every finding | Not a research deliverable; noted so planning sequences it. |

---

## Common Pitfalls

1. **Copying a developer's populated `graph.sqlite3` into the temp subject.** The
   file exists in the working tree right now and is gitignored. A plain `copytree`
   makes the seed unmeasurable and makes CI and a developer's machine disagree.
   Use `ignore_patterns("graph.sqlite3*", "artifact-store", "__pycache__")`.
2. **Copying `deployment/` without `server/`.** `server:` resolves against the
   deployment's **parent** (`D-10`). A leg refused for a missing program reads
   exactly like a leg refused for a deployment declaring none.
3. **Adding a `## ` heading to `examples/external/00-hello-context/README.md`.**
   Seven headings, by name and order, enforced by the example's own runner. Turns
   `make ci` red.
4. **`path.py:NN` citations in new prose.** `MAXIMUM_UNANCHORED_PY_CITATIONS = 0`
   with zero headroom. Cite `path.py::Symbol`.
5. **Assuming `CLIENT_EXAMPLE_ROOTS += (new,)` is the whole gate change.** It arms
   the budget gate too, and the permitted set is inverted between the roots.
6. **`$(PYTHON)` in a documented recipe.** Refused by name by the identity gate.
7. **Deleting `test_s2_client_transport_spike.py` before extracting its offline
   `claude` env recipe.** It is the only working one in the tree.
8. **`MCPToolset` (uppercase).** Deprecated; use `McpToolset`.
9. **Not passing `env=dict(os.environ)` to the stdio params.** `get_default_environment()`
   filters to six variables.
10. **Reading ADK's `{"error": ...}` dict as a success.** `_MCP_GRACEFUL_ERROR_HANDLING`
    converts tool errors into a value rather than raising.

---

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|---|---|---|
| A1 | Leg 2's code shape under a PASS Q1 verdict (`ClaudeAgentOptions` with an `McpStdioServerConfig` entry, tool visible as `mcp__ccf__request_context_product`) | Q3 leg 2 | The namespacing is `[ASSUMED]` by analogy with `examples/s2-01-external-consumers/client_claude_agent.py:84` and `tests/examples/test_s2_client_transport_spike.py:75`, which measured it for the **HTTP** case. Not measured for stdio. |
| A2 | A budget in the 120–150 line range is achievable for the three clients | Q5 | Extrapolated from `s2-01`'s 200-line HTTP LangGraph client. **Measure before declaring.** |
| A3 | `docs/retired/` is a suitable destination | Q6 | A recommendation, not a measurement. Dave/planning may prefer a root-level `retired/`. |
| A4 | Recommended `CLNT-23`..`CLNT-31` ids and wordings | Q7 | Discretionary per CONTEXT.md. |
| A5 | The nine-plan wave breakdown | Q7 | A recommendation. |
| A6 | GitHub Actions status of `test_s2_client_transport_spike.py` | Q6 | **UNVERIFIED — no CI token in session.** If it is red there, Phase 20 inherits a defect. |

---

## Open Questions

1. **Is the `tests` job in GitHub Actions currently green on
   `tests/examples/test_s2_client_transport_spike.py`?**
   - Known: the module has no skip guard, requires the `claude` binary, and
     `.github/workflows/ci.yml` installs no Node/npm/`claude` step. It passes locally.
   - Unclear: whether Actions has the binary by some other route, or whether that job
     has been red.
   - Recommendation: Dave runs the CI diagnostic before planning commits leg 2's
     default path. This is adjacent to Q1 and materially changes criterion 10's cost.

2. **Does `tool_context=None` remain acceptable across ADK minor versions?**
   - Known: it works at `google-adk==2.5.0`, measured.
   - Unclear: whether it is contract or tolerance.
   - Recommendation: assert on the returned dict shape so a change is loud; do not
     reach for the private `_execute_with_session`.

3. **Should the retired `client_langgraph.py` be renamed on the way out?**
   - Known: `resolve_cited` falls back to a **bare-name suffix match**, and
     *"ambiguity is never a finding"* (`tools/lints/citations.py:436-437`). Two files
     named `client_langgraph.py` in the tree makes every bare-name citation of either
     silently unchecked.
   - Recommendation: give the retired copies a `-retired` suffix, or accept the
     unchecked citations knowingly and say so.

---

## Sources

### Primary (HIGH — measured in this session against the installed tree)
- `.venv/lib/python3.12/site-packages/google/adk/tools/mcp_tool/{__init__,mcp_toolset,mcp_tool}.py` — live script run against a `FastMCP` stdio echo server
- `.venv/lib/python3.12/site-packages/langgraph`, `langchain_core.tools.StructuredTool`, `mcp.client.stdio` — live script run
- `.venv/lib/python3.12/site-packages/claude_agent_sdk/{types.py,__init__.py}` — read
- `importlib.metadata` version probe; `ls site-packages`
- `pytest tests/examples/test_s2_client_transport_spike.py` — 15 passed / 4.87 s
- `pytest tests/invariants/test_citation_coverage.py` + direct calls to
  `scanned_citation_hosts()`, `sweepable_citation_sites()`, `tools.lints.citations.scan_tree`
- Repo files cited inline throughout, all with `path:line`

### Secondary (HIGH — read, not executed)
- `.planning/ROADMAP.md` Phase 20 entry (lines 1699-1800); `.planning/REQUIREMENTS.md`;
  `20-CONTEXT.md`; `CLAUDE.md`

### Not verified
- GitHub Actions job status (no token)
- Leg 2's stdio call shape end to end (Q1 is the orchestrator's)

---

## Metadata

**Confidence breakdown:**
- Q3 legs 1 and 3: **HIGH** — executed
- Q3 leg 2: **MEDIUM** — shape read, HTTP analogue measured, stdio path not
- Q4: **HIGH** — every claim carries a `path:line`; the `server:`-parent and
  `graph.sqlite3` findings were measured
- Q5: **HIGH** — `H-11` confirmed and `H-12`'s mechanics contradicted, both from source
- Q6: **HIGH** for the sweep, the floors and the ext-00 heading contract;
  **UNVERIFIED** for Actions status
- Q7: **MEDIUM** — recommendation, not measurement

**Research date:** 2026-08-20
**Valid until:** 2026-09-19 (30 days; the harness packages are pinned, so the
measured call shapes do not drift without a deliberate bump)
