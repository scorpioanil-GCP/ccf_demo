# Phase 20: Client Access from Three Harnesses — ADK, Anthropic Agent SDK and LangGraph - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-20
**Phase:** 20-client-access-from-three-harnesses-adk-anthropic-agent-sdk-a
**Areas discussed:** What CI answers against, Killing the model call, Finding the door, Cleanup + naming

---

## Area selection

All four offered areas were selected. Dave's selection message also carried a
substantive directional answer rather than a bare pick: a five-option analysis
of the door-handoff problem, a locked preference for "orchestrator outside the
client", explicit rejections of hard-coded spawns / an HTTP door / empty-only
CI, and a four-item list of what discuss must lock.

---

## Finding the door — the handoff contract

**Correction raised before any option was offered.** Dave's option 1 described
"invoking the three zero-CCF client programs with a pre-agreed stdio
endpoint". MCP stdio has no hand-offable endpoint. Measured against the three
installed packages: ADK `StdioConnectionParams(server_params=...)`,
`claude_agent_sdk.McpStdioServerConfig`, and raw
`mcp.client.stdio.stdio_client` — all take `command + args` and spawn the child
themselves.

**Dave's response:** *"Correction accepted. That premise was wrong and the
measurement is decisive."* Refined contract locked: the runner may import
`ccf` and resolves deployment root → `server:` → opaque `command + args`; each
client receives that pair as configuration and spawns through its own harness.

| Option | Description | Selected |
|--------|-------------|----------|
| argv | Explicit flags on each client; visible in the documented command, greppable, readable by the command-identity checks | ✓ |
| One env var | `CCF_MCP_SERVER_CMD`; matches the retired s2-01 clients and most real MCP setups, but invisible in the documented command | |
| Generated `.mcp.json` | The real-world MCP config convention; 00-hello-context already ships an `.mcp.json` docs-only leg — a fourth moving part | |

**Notes:** Dave's own framing of why this is the right shape: *"The client's
experience is exactly what an adopter sees when configuring any MCP server.
That is a stronger teaching artifact than a CCF-specific spawn path, and it
preserves purity."*

---

## What CI answers against — seed source

Two constraints were measured before options were offered, and they collide:
`D-32` forbids a seed artifact under `examples/`; `no-hardcoding`'s
`RULE_TREE_SCOPE` covers `examples/`, so the values cannot be Python constants
in the runner either.

| Option | Description | Selected |
|--------|-------------|----------|
| Document in the new dir + narrow `D-32` | Declared scenario as YAML, interpreted by the runner; `D-32` narrowed on the record to govern producer *output*, not a declared input. `00-hello-context/artifacts/events.yaml` is already this shape | ✓ |
| Reuse the test seed path | Import `tests/client/conftest.py::seed`; zero new data, no narrowing — but couples a shipped example to the test tree | |
| `D-32` binds — empty deployment | Zero pressure and criterion 4 still holds, since an empty deployment prints a real address — but a console with no companies | |

**Notes:** The third option was pre-rejected by Dave in the selection message
(*"weak demonstration"*), and was offered anyway so the narrowing of `D-32` was
taken deliberately rather than by elimination.

---

## What CI answers against — CI subject

| Option | Description | Selected |
|--------|-------------|----------|
| Temp copy, seeded per run | `copytree` hw1's deployment to tmp, seed, close the writer, spawn the door and run `consume.py` against the same copy; mirrors `tests/client/conformance/conftest.py` | ✓ |
| Seed hw1's deployment in place | Legal (gitignored) and leaves the README commands runnable — but CI mutates a tracked example and leaves state behind | |

---

## Killing the model call — call shape

Framed after finding that `examples/03-harness-portability` already solves the
no-model problem for these exact three harnesses, and that
`claude_agent_sdk` routes its MCP client through the `claude` CLI, so example
03's custom-`Transport` technique would remove the door call for leg 2.

| Option | Description | Selected |
|--------|-------------|----------|
| Harness invokes the registered tool, no model | Literally what criteria 1–3 say; deterministic by construction; no fixtures for legs 1 and 3 | ✓ |
| Model-driven, replayed | Richer — an agent choosing CCF context — and what ruling 5 anticipated; costs three recordings, a LangGraph provider, and drift-prone fixtures | |
| Model-driven for leg 2 only | Honest about the architecture difference, but breaks "the same program three ways" | |

---

## Killing the model call — leg 2

| Option | Description | Selected |
|--------|-------------|----------|
| Real CLI + replayed model | Install `claude`, configure via `McpStdioServerConfig`, point `ANTHROPIC_BASE_URL` at the copied replay server; door genuinely reached | ✓ |
| Swap to the raw `anthropic` SDK | No CLI, replay already proven — but criterion 2 says *Anthropic Agent SDK* | |
| Leg 2 is `--live` only | Cheapest, but ruling 1 rejected "unrun" and criterion 6 requires a deterministic default per leg | |

**Notes:** Combined with the previous answer, this makes leg 2 the odd one out
in the default path. That consequence was stated back to Dave rather than left
for a reviewer, and is written into CONTEXT.md `H-07` as a lesson the README
must carry: *who holds the MCP session* differs by harness; CCF does not.

**Risk carried forward, not resolved:** the `claude` CLI is a non-Python,
unpinnable CI dependency with no install step in `ci.yml`, and it is unverified
whether it can be driven fully offline against a replay server. Recorded in
CONTEXT.md as a research blocker for leg 2's default path, with an explicit
instruction that an undriveable CLI is a `D-IMPL-NN` and a stop rather than a
quiet demotion of leg 2.

---

## Killing the model call — the copied replay harness

| Option | Description | Selected |
|--------|-------------|----------|
| Only if a leg needs it | Copy `replay_server.py` for leg 2 alone; ruling 5 discharged as scoped, since what it said Phase 20 inherits is the runner *design* | ✓ |
| Copy it regardless | Honors ruling 5 literally and serves `--live` recording — but a 400-line file the default path never exercises is the pattern `C-10` refuses | |

---

## Killing the model call — `--live` semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Real deployment only | One flag, one meaning across all three legs; leg 2 additionally drops its replay. No path exists that CI never exercises | ✓ |
| Real deployment AND a model-driven loop | Strongest demo, but builds a second per-leg path CI never runs, and LangGraph lacks a model provider | |
| Two orthogonal flags | Most precise about the two real axes; four combinations per harness of which CI runs one | |

---

## Cleanup + naming — layout and gate

Framed after finding that the two existing purity mechanisms disagree: the AST
gate in `tests/examples/` treats every `.py` in an example root as
reader-visible (which would catch a `ccf`-importing runner), while
`00-hello-context/run.py` uses a static grep — the shape Phase 19 measured
inadequate.

| Option | Description | Selected |
|--------|-------------|----------|
| Clients at root, runner in a subdir | The existing structural rule gates the three clients untouched; no rule weakened to accommodate a file | ✓ |
| Runner at root, teach the gate to skip it | Keeps the familiar 00-hello-context shape, at the cost of a hole in a deliberately structural rule | |
| New gate in the example's own suite | Most freedom, no coupling — but a second implementation of one invariant, with controls starting from zero | |

---

## Cleanup + naming — s2-01

| Option | Description | Selected |
|--------|-------------|----------|
| Delete it | Two orphan files, retired phase, git history keeps them | |
| Quarantine it | Preserves the LangGraph `StructuredTool`-over-MCP shape as a visible reference | ✓ |

Follow-up, after noting the repo has no quarantine convention at all (its
precedent is deletion plus a written record):

| Option | Description | Selected |
|--------|-------------|----------|
| Out of `examples/` entirely | The only option that literally discharges ruling 3 — afterwards `examples/` holds exactly one LangGraph client | ✓ |
| `examples/_retired/` | Cheap and discoverable, but `examples/` still holds two, and the underscore is a convention this repo does not use | |
| Leave in place, mark it retired | Smallest diff, weakest reading of "quarantine" | |

---

## Cleanup + naming — 00-hello-context

| Option | Description | Selected |
|--------|-------------|----------|
| Mark historical in its README | Stays running and CI-green; ruling 3 satisfied by a sentence, not a move | ✓ |
| Retire the whole example | Cleanest tree, but deletes eight passing CI assertions unrelated to this phase | |

---

## Cleanup + naming — directory name

| Option | Description | Selected |
|--------|-------------|----------|
| `examples/hw1-harness-clients/` | The ROADMAP's own float; sorts beside the door it reaches | ✓ |
| `examples/external/01-three-harnesses/` | 00-hello-context's numbered successor — but adjacency to the directory being marked historical is the confusability ruling 3 avoids | |
| `examples/hw1-three-harnesses/` | Leads with the rhetorical point rather than "clients" | |

---

## Claude's Discretion

- Scenario document filename, schema, and row count
- The runner's subdirectory name
- The retired-material destination path for s2-01
- Per-leg seeded copy vs sequential legs against one copy
- `argv` flag names
- Which `CLNT-NN` numbers are minted and their wording

## Deferred Ideas

- A model-driven leg for ADK and LangGraph — its own phase, its own fixtures
- A fourth harness — out of scope in the ROADMAP entry
- `HarnessAdapterProtocol` work (`D-IMPL-24`/`D-IMPL-25`) — producer-side
- Retiring `00-hello-context` entirely and rehoming its unique assertions
- A repository-wide retired-material convention
