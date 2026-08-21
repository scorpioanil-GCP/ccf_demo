---
phase: 20-client-access-from-three-harnesses-adk-anthropic-agent-sdk-a
plan: 04
subsystem: examples — the Anthropic Agent SDK leg and its determinism seam
tags: [claude-agent-sdk, mcp-stdio, sse-stand-in, no-hardcoding, fail-loud, offline-cli]
requires:
  - "20-03: drive.py (known_legs, drive_leg, payload_violations, reference_run, compare_addresses), client_adk.py and client_langgraph.py as the argv/stdout shape leg 2 joins"
  - "20-02: question.yaml, build_question's `tool` + `temporal_boundary`, marker_violations(names, chrome_words), the make target"
  - "20-02 task 4: tools/lints/no_hardcoding.py's destination arm — consumed here, never edited"
  - "tests/examples/test_s2_client_transport_spike.py — the only worked offline `claude` recipe in the tree, extracted before 20-07 deletes it"
provides:
  - "examples/hw1-harness-clients/client_anthropic.py — leg 2, the Claude Agent SDK configuring the hw1 door as an MCP stdio server"
  - "examples/hw1-harness-clients/runner/model_stub.py — a fail-loud Messages-API stand-in over SSE, copied for the one leg that needs it (H-08)"
  - "examples/hw1-harness-clients/runner/model_stub.py::offline_cli_environment — the nine-variable offline `claude` recipe, extracted and named"
  - "examples/hw1-harness-clients/runner/model-conversation.yaml — the declared model label, leg-2 prompt and two exchanges"
  - "examples/hw1-harness-clients/runner/drive.py::leg_environment, ::model_standin, ::_spawn_standin, ::_terminate, ::LEGS_DRIVING_A_MODEL"
affects:
  - "20-05: the socket guard covers legs 1 and 3 only; leg 2's exclusion and its equivalent proof are now written in drive.py's docstring for that test to restate"
  - "20-06: the purity gate and the README line budget now measure THREE client files; client_anthropic.py is 288 lines"
  - "20-07: model_stub.py::offline_cli_environment is the extraction that makes deleting the spike lossless"
  - "20-08: the README's `--live` section must repeat drive.py's sentence — leg 2 requires ANTHROPIC_BASE_URL under --live"
tech-stack:
  added: []
  patterns:
    - "a declared per-leg property (LEGS_DRIVING_A_MODEL) consulted by one driving loop, instead of a per-leg branch chain"
    - "a request reduction whose fields ARE the claims — door_tools/other_tools is the tool-surface assertion, observable only from the model's side of the wire"
    - "refusals answered 4xx, not 5xx, because a retryable refusal is a hang rather than a diagnostic"
    - "a passing run prints no refusal — ancillary vendor traffic is suppressed at source rather than whitelisted, so the refusal channel keeps its whole signal"
    - "prompt and model label travel through the environment MAPPING keyed by variable name, never as a `prompt=` keyword argument"
key-files:
  created:
    - examples/hw1-harness-clients/client_anthropic.py
    - examples/hw1-harness-clients/runner/model_stub.py
    - examples/hw1-harness-clients/runner/model-conversation.yaml
  modified:
    - examples/hw1-harness-clients/runner/drive.py
    - docs/surface/examples/RETIREMENT-COUPLINGS.md
key-decisions:
  - "The stand-in refuses 400, not replay_server.py's 500 — measured: a 500 is retried by the vendor client behind the CLI, turning the exchange-removal control into a 120s TimeoutExpired instead of a named diagnostic"
  - "The declared reduction is {model, door_tools, other_tools, messages, tool_results} rather than the plan's sorted tool-name list: the namespaced name carries a server label this stand-in is deliberately not told, and two counts encode the tool-surface claim directly"
  - "The model label is pinned from the same declared document both sides read, so a client that stopped honouring it is a red run"
  - "client_anthropic.py names the MCP server itself (SERVER_LABEL) rather than taking it on argv — a program's own naming of a server it is about to declare is not a deployment value"
  - "The CLI's title-generation call is SUPPRESSED at its source with CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC, not modelled as a declared exchange — a request that no longer arrives must not have a branch waiting for it"
  - "The inherited recipe's DISABLE_NON_ESSENTIAL_MODEL_CALLS is inert against 0.2.128 (the string is absent from the bundled binary) and is kept with that measurement written beside it rather than dropped silently"
patterns-established:
  - "Copy the discipline, not the bytes: H-08 is satisfied by inheriting replay_server.py's five refusal postures with the response shape the measurement forced"
  - "A grep-shaped acceptance criterion is met by stating the teaching without spelling the token"
requirements-completed: [CLNT-23, CLNT-24, CLNT-26, CLNT-32]
duration: ~2h40m
completed: 2026-08-20
---

# Phase 20 Plan 04: Leg 2 — the Anthropic Agent SDK — Summary

**A third foreign harness reaches the same governed Context Product through the
same `mcp+stdio` door — this one by handing the door to an agent binary as
configuration and letting a model call it — and lands on the same content
address, with no live model call and no network beyond loopback.**

## The measurement that matters

```
reference address   5d7bfa49f5b3f65add25ea61220a191a91982f5ae97901e010b26c5ca8dc37f5
leg adk             5d7bfa49f5b3f65add25ea61220a191a91982f5ae97901e010b26c5ca8dc37f5  MATCH  names: Kestrelmark Industries, Volanti Logistics, Brightpath Materials
leg anthropic       5d7bfa49f5b3f65add25ea61220a191a91982f5ae97901e010b26c5ca8dc37f5  MATCH  names: Kestrelmark Industries, Volanti Logistics, Brightpath Materials
leg langgraph       5d7bfa49f5b3f65add25ea61220a191a91982f5ae97901e010b26c5ca8dc37f5  MATCH  names: Kestrelmark Industries, Volanti Logistics, Brightpath Materials
legs compared       3
```

`make example-hw1-harness-clients | grep -oE '[0-9a-f]{64}' | sort -u | wc -l`
returns `1`. Four programs — three harnesses plus the reference client — three
separately seeded copies, three spawned doors, one address. The whole drive
takes **10.5 s**, leg 2's `claude` CLI and its model stand-in included.

`make ci-core` exits **0**: `4018 passed, 118 skipped` in 10m31s, plus
`406 passed` in `tools/lints/tests` and `154 passed` in
`tools/publish_scan_tests tools/docs_tests`.

## What was built

**`examples/hw1-harness-clients/runner/model_stub.py`** (~480 lines) — the
leg-2-only determinism seam. A Messages-API stand-in on loopback that answers a
declared conversation and refuses everything else: half-declared exchanges
refuse at boot before `READY`, a request whose reduction or pinned model label
is not the declared one refuses by name printing both sides, a request past the
last declared exchange refuses rather than repeating, and the CLI's base-URL
probe gets a recorded `404`. `offline_cli_environment(base_url, home)` is the
nine-variable offline `claude` recipe, extracted from the spike that is about to
be deleted.

**`examples/hw1-harness-clients/runner/model-conversation.yaml`** — the declared
model label, the prompt leg 2 sends, and the two exchanges with their measured
reductions. Data, read by two programs, spelled in neither.

**`examples/hw1-harness-clients/client_anthropic.py`** (288 lines) — leg 2. It
never holds an MCP session; it hands the door over as
`ClaudeAgentOptions(mcp_servers={"ccf": McpStdioServerConfig(...)})` and the
agent binary spawns and speaks to it. `tools=[]`, `skills=[]`,
`setting_sources=[]`, `strict_mcp_config=True` and one namespaced
`allowed_tools` entry withdraw everything else. Zero `ccf` imports in every AST
shape.

**`examples/hw1-harness-clients/runner/drive.py`** (+250 lines) — the per-leg
environment as data, the bounded `READY` handshake, the kill fallback, and
`--live`'s drop of the stand-in.

## Task-by-task

| Task | Commit | What landed |
|---|---|---|
| 1 — the stand-in and the extracted recipe | `682cf88` | `model_stub.py` (`offline_cli_environment`, `find_orphans`, `require_paired_exchanges`, `reduction`, `door_tools`, `tool_input`, `sse`, `answer_blocks`, `build_app`, `main`) and `model-conversation.yaml` |
| 2 — leg 2 | `8b085c6` | `client_anthropic.py` (`parse_args`, `required`, `qualified`, `session_options`, `result_text`, `unwrapped`, `report`, `ask`, async `main`) |
| 3 — runner wiring + inventory | `75c7a33` | `drive.py`: `MODEL_STANDIN_PROGRAM`, `READY_TIMEOUT_SECONDS`, `TERMINATE_TIMEOUT_SECONDS`, `LEGS_DRIVING_A_MODEL`, `PROMPT_VARIABLE`, `MODEL_VARIABLE`, `DECLARED_CONVERSATION_DOCUMENT`, `_spawn_standin`, `_terminate`, `model_standin`, `leg_environment`; `drive_leg` gains an `environment` parameter; `RETIREMENT-COUPLINGS.md` regenerated |

## Hand-driven evidence, before the runner knew about leg 2

A persistent seeded subject was built with `drive.py::build_subject` and
`::seed`; the door and question came from `::resolve_door` and
`::build_question`, so it is the same subject CI uses. The stand-in was spawned,
its `READY <port>` read, and the client driven with the recipe plus the two
declared values. Abbreviating the seeded root as `$S` and the stand-in's port as
`$P`:

```
ANTHROPIC_BASE_URL=http://127.0.0.1:$P ANTHROPIC_AUTH_TOKEN=offline \
HOME=$TMPHOME CLAUDE_CONFIG_DIR=$TMPHOME/config \
CLAUDE_AGENT_SDK_SKIP_VERSION_CHECK=1 DISABLE_TELEMETRY=1 \
DISABLE_ERROR_REPORTING=1 DISABLE_AUTOUPDATER=1 \
DISABLE_NON_ESSENTIAL_MODEL_CALLS=1 \
CCF_HARNESS_MODEL=claude-sonnet-4-5 CCF_HARNESS_PROMPT='<from the document>' \
.venv/bin/python examples/hw1-harness-clients/client_anthropic.py \
  --server-command .venv/bin/python \
  --server-arg $S/server/serve.py --server-arg $S/deployment \
  --question-json '{"tool":"request_context_product", ... }'
```

Exit `0`. `content address    5d7bfa49f5b3f65add25ea61220a191a91982f5ae97901e010b26c5ca8dc37f5`
on stdout — leg 1's address for the same subject — followed by the Context
Product, whose printed text carries all three declared company names
(`Kestrelmark Industries`, `Volanti Logistics`, `Brightpath Materials`).

## Controls — every one observed red, with its mutation named

### Task 1 — the stand-in's four refusals

| Control | Mutation | Observed |
|---|---|---|
| **Drift refuses** | POST advertising two tools (`mcp__ccf__request_context_product` + `Bash`) against exchange 0 | `400 {"error":"request reduction mismatch","ordinal":1,...,"expected":{"messages":3,"door_tools":1,"other_tools":0,"tool_results":1},"actual":{"messages":1,"door_tools":1,"other_tools":1,"tool_results":0}}` — both reductions, never an answer |
| **Exhaustion refuses** | one POST more than there are declared exchanges | `400 {"error":"declared exchanges exhausted","served":2,"declared":2}` — not a repeat of the last answer |
| **Orphan declaration refuses at boot** | `exchanges[1]` with its `response:` removed, in a scratch document | exit `1`, no `READY` line, stderr: *"half-declared exchanges — every exchange needs both a 'request:' and a 'response:': exchange 1 ('report-what-came-back'): response"* |
| **Pinned model drift refuses** | POST carrying `"model": "some-other-model"` | `400 {"error":"the request did not carry the pinned model label","expected":"claude-sonnet-4-5","actual":"some-other-model"}` |

The unrouted probe was observed answering rather than crashing:
`404 {"error":"unrouted"}` on `GET /v1/whatever`, recorded in `seen`.

**Controls that could not be made to fail: none.**

### Task 3 — the stand-in's failure is the run's failure, end to end

The tracked `model-conversation.yaml` was doctored to one exchange (backed up,
restored, `git diff` verified empty afterwards) and the real runner driven:

```
PYTHONPATH=src:runtime .venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs anthropic
→ exit 1 in 4.3s
AssertionError: leg 'anthropic' exited 1
stderr: the session ended in error: API Error: 400 {"error":"declared exchanges exhausted","served":1,"declared":1}
```

The stand-in's own stderr echo appeared twice in the same run
(`model stand-in refused: {...}`), so the reason is visible even where the CLI
does not republish the body.

### Task 2 — the two refusals that keep a live model out

```
$ env -u ANTHROPIC_BASE_URL .venv/bin/python examples/hw1-harness-clients/client_anthropic.py --server-command /bin/true --question-json '{"tool":"t","arguments":{}}'
ANTHROPIC_BASE_URL is not set; it decides where this leg's model lives, and a
client that defaulted to the vendor's endpoint would reach a live model
whenever a variable went missing. The runner injects it on the default path;
under `--live` the runner deliberately does not, and the operator supplies it —
a real endpoint, or a proxy
→ exit 1

$ ANTHROPIC_BASE_URL=http://127.0.0.1:1 .venv/bin/python examples/hw1-harness-clients/client_anthropic.py ...
CCF_HARNESS_PROMPT is not set; it carries this leg's instruction, which is a
declared document the runner reads and never a literal in this file (CLAUDE.md §6.4)
→ exit 1
```

## The per-leg environment, measured

`set(leg_environment(...)) - set(os.environ)`, per leg, both modes:

```
adk        live=False injected=[]                                        overridden=[]
adk        live=True  injected=[]                                        overridden=[]
langgraph  live=False injected=[]                                        overridden=[]
langgraph  live=True  injected=[]                                        overridden=[]
anthropic  live=False injected=['ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_BASE_URL',
                                'CCF_HARNESS_MODEL', 'CCF_HARNESS_PROMPT',
                                'CLAUDE_AGENT_SDK_SKIP_VERSION_CHECK',
                                'CLAUDE_CONFIG_DIR', 'DISABLE_AUTOUPDATER',
                                'DISABLE_ERROR_REPORTING',
                                'DISABLE_NON_ESSENTIAL_MODEL_CALLS',
                                'DISABLE_TELEMETRY']                     overridden=['HOME']
anthropic  live=True  injected=['CCF_HARNESS_MODEL', 'CCF_HARNESS_PROMPT'] overridden=[]
```

Legs 1 and 3 receive **nothing** from the recipe in either mode. Leg 2 receives
all nine recipe variables on the default path (`HOME` as an override, since a
developer already has one) and **none** of them under `--live` — which is
exactly the refusal below.

## The `--live` refusal, and where it is documented

`drive.py --help`:

> `--live` point every leg at the real tracked deployment instead of a seeded
> temporary copy (it must already be populated); one meaning across all legs,
> and for leg 2 it additionally drops the model stand-in so its model is real.
> **UNDER `--live`, LEG 2 REQUIRES `ANTHROPIC_BASE_URL` TO BE SET EXPLICITLY** —
> this runner deliberately stops injecting it, and the client refuses rather
> than falling back to a vendor endpoint.

The client's refusal message (quoted in full above) says the same thing from the
other side. **Plan `20-08`'s README sentence must agree with both.**

## Gates that stayed armed

| Assertion | Result |
|---|---|
| `git diff tools/lints/allowlist.yaml` | empty |
| `git diff -- tools/lints/no_hardcoding.py` | empty |
| `.venv/bin/python -m tools.lints --no-hardcoding` | exit 0 with all three new files in the tree |
| `git diff --stat 9e4bd0e..HEAD -- src/` | empty |
| `git diff --stat -- pyproject.toml .github/workflows/` | empty (no package installed, no CI step added) |
| `git status --porcelain examples/hw1-companies-over-revenue/ examples/external/00-hello-context/` | empty |
| `grep -ci gemini .../model_stub.py` | `0` |
| `grep -c 'api.anthropic.com' .../client_anthropic.py` | `0` |
| `grep -c 'environ.get' .../client_anthropic.py` | `0` |
| orphaned stand-ins after a full drive (`ps -eo cmd` scan) | NONE |
| `pytest tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current` | passed; a second sweep run left the file byte-identical |

The retirement inventory gained exactly three rows, all documentary docstring
citations of `examples/external/00-hello-context` from the two new runner files
— the citations the plan asked for.

## The noisy-refusal defect, diagnosed and closed

Reported by the coordinator after the first three commits: **every healthy run
printed `model stand-in refused: {"error": "request reduction mismatch", ...}`
as its first line.** The run was green and the address was right; the reporting
was not. A refusal that fires on the happy path cannot distinguish healthy from
broken, and an operator who scrolls past it once will scroll past the real one
(`CLNT-14`, the Phase 16 retrospective) — and `20-08`'s README would document a
passing run whose output opens with an alarm.

### Diagnosis — it is (a), deterministically, but not for the reason either of
us assumed

Five consecutive `--legs anthropic` runs: `rc=0`, **exactly one** refusal each,
byte-identical (`ordinal 0`, `door_tools: 0`). Not a race — answer (a).

The working hypothesis on both sides was "the CLI sends the agent turn before
its MCP session is up, is refused, and retries". **Recording the raw request
bodies showed that is wrong**, and the correction matters because it changes the
fix. There are three requests, and request 0 is not an agent turn at all:

| # | `tools` | `messages` | `output_config` | `thinking` | what it is |
|---|---|---|---|---|---|
| 0 | `[]` | 1 | `{"format": {"type": "json_schema", "schema": {..."title"...}}}` | `disabled` | the CLI's **title-generation** call |
| 1 | `['mcp__ccf__request_context_product']` | 1 | absent | `enabled` | the agent turn |
| 2 | `['mcp__ccf__request_context_product']` | 3 | absent | `enabled` | the turn carrying the tool result |

Request 0's user message is literally
`<session>…</session>\n\nWrite the title in the predominant language of the
session…`. It is ancillary traffic around the session, not part of it, and the
CLI does **not** retry it — it tolerates the failure and proceeds. So the
sequence was never "refuse then retry"; it was "refuse an unrelated call, then
have the real conversation". The ordinal never advanced because it never should
have.

### Why it was happening at all — a defect in the inherited recipe

The recipe extracted from the spike sets `DISABLE_NON_ESSENTIAL_MODEL_CALLS=1`,
which reads exactly as though it covers this. **It does not, because the CLI
never reads it:**

```
$ strings claude_agent_sdk/_bundled/claude | grep -c DISABLE_NON_ESSENTIAL_MODEL_CALLS
0
```

The name does not occur in the binary. The variable that governs this traffic is
`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`, which does occur, and which the
inherited recipe was missing. The spike never noticed because it asserted on the
tool surface the model saw, not on the request count.

### The fix — suppress it, do not model it

`offline_cli_environment` gains `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`.
Measured: the CLI then makes **exactly the two declared requests**, the address
is unchanged, and five consecutive runs print zero refusals.

**Declaring the title call as an exchange was considered and rejected.** It
would have put a turn about title generation into a document whose subject is
CCF, required the stand-in to answer a JSON-schema-shaped output it otherwise
knows nothing about, and — worst — left a branch in the stand-in for a request
that no longer arrives, which is the `C-10` member-nothing-reads pattern. The
same objection rules out "classify a tool-less request as ancillary and answer
it": that would have punched a hole exactly the shape of a real drift, because a
genuine agent turn whose door tool vanished has the *same* reduction the title
call had (`door_tools: 0, other_tools: 0`). Control B below shows that shape is
still refused.

`DISABLE_NON_ESSENTIAL_MODEL_CALLS` is **kept**, with the measurement written
beside it in the code. Dropping it would erase the finding from the place the
next reader looks, and the extraction is meant to be the recipe as inherited
*plus* what measurement added.

### Controls — three observed, each with its mutation named

| Control | Mutation | Observed |
|---|---|---|
| **A — the suppressor is load-bearing** | the single line `"CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",` deleted from the shipped `offline_cli_environment` (deleted line printed on the cut, then restored from backup) | the refusal returns, one per run, byte-identical to the reported defect. Without this control the new variable would be indistinguishable from decoration |
| **B — a genuine drift is still refused** | (i) an extra non-CCF tool advertised; (ii) **the door tool vanished** — the same `door_tools: 0` shape the title call had | (i) `400 … "actual":{"door_tools":1,"other_tools":1,…}`; (ii) `400 … "actual":{"door_tools":0,"other_tools":0,…}`. Baseline declared turn 1 still serves `200`. No hole was punched |
| **C — the stand-in's failure is still the run's failure** | `exchanges[1]` removed from the tracked document | exit `1` in 4.2 s: `API Error: 400 {"error":"declared exchanges exhausted","served":1,"declared":1}` |

**Controls that could not be made to fail: none.**

### The invariant, restored and measured

Five consecutive `--legs anthropic` runs and one full three-leg
`make example-hw1-harness-clients`: `rc=0`, **`grep -c 'model stand-in refused'`
returns `0`** on every one. The first line of a passing run is the `make`
recipe echo. All three legs and the reference still print
`5d7bfa49f5b3f65add25ea61220a191a91982f5ae97901e010b26c5ca8dc37f5` with the
three declared company names.

## Deviations from plan

### 1. [Rule 1 — Bug] The stand-in refuses `400`, not `replay_server.py`'s `500`

- **Found during:** Task 3, running the exchange-removal control.
- **Issue:** the control was red, but for the wrong reason and 28× too slowly.
  With a `500`, the vendor client behind the `claude` CLI **retries with
  backoff**; the leg burned the runner's full `LEG_TIMEOUT_SECONDS = 120` and
  died as `subprocess.TimeoutExpired`, so the diagnostic an operator saw was
  "the command timed out" and not "declared exchanges exhausted". A refusal
  nobody can read is a hang with extra steps, and "fail loudly" was only half
  true.
- **Fix:** `REFUSAL_STATUS = 400` — a client error, which is not retried — with
  the same JSON diagnostic body, plus an echo of every refusal to the
  stand-in's stderr (inherited from the runner, so it reaches the console even
  when the CLI swallows the body). The control now exits `1` in **4.3 s** with
  the stand-in's own sentence on the failure. The constant carries the
  measurement as its comment, and the module docstring gains a fifth refusal
  posture: *refuse promptly*.
- **Files:** `examples/hw1-harness-clients/runner/model_stub.py`
- **Commit:** `75c7a33`

### 2. [Rule 3 — Blocking] `McpStdioServerConfig` is not a top-level export

- **Issue:** `from claude_agent_sdk import McpStdioServerConfig` raises
  `ImportError` on `0.2.128`; the `TypedDict` lives in `claude_agent_sdk.types`
  (`dir(claude_agent_sdk)` offers `McpSdkServerConfig`, a different thing).
- **Fix:** imported from `claude_agent_sdk.types`. The plan's key-link pattern
  `McpStdioServerConfig` is satisfied and the constructed value is the exact
  `TypedDict` the research measured.

### 3. [Rule 1 — Bug] The tool result is twice-wrapped

- **Issue:** the first hand drive raised `KeyError: 'content_address'`. Measured:
  the harness surfaces the door's answer inside MCP's own
  `{"result": "<document>"}` envelope. The siblings never see that layer,
  because they call the tool themselves; this leg does, because the agent
  binary called it.
- **Fix:** `client_anthropic.py::unwrapped` unwraps by name with a loud refusal
  on a missing key — a harness that changed the envelope must not look like a
  door that answered oddly.
- **Commit:** `8b085c6`

### 4. [Judgement] The declared reduction is four counts plus a pinned model, not a tool-name list

- **Issue:** the plan's reduction is `{model, sorted tool names, message count}`.
  Two problems, both measured. (a) The advertised name is
  `mcp__<server>__request_context_product`, and the server label is the
  *client's* choice — declaring the full name would either put a harness wire
  fact in the fabric-side document or force the stand-in to be told a label it
  has no other use for. (b) A bare `model` value declared as "whatever the CLI
  sends" is a value that breaks silently on a CLI update.
- **Fix:** the reduction is
  `{messages, door_tools, other_tools, tool_results}` compared against the
  declared exchange, plus the **pinned** model label compared separately. The
  door/other split is matched on the bare tool name as a suffix, so no label is
  needed, and `other_tools: 0` on every turn **is** the tool-surface claim —
  the same assertion the retired spike made in
  `test_the_claude_agent_leg_saw_only_ccf_tools`, now enforced by the wire
  rather than by a test reading a recorder. The model label is pinned from the
  declared document that the client also reads, so both sides of the comparison
  come from one declaration and a client that stopped honouring it is red.
- **Consequence:** `CCF_HARNESS_MODEL` joins `CCF_HARNESS_PROMPT` as a runner-set
  variable. Model names never appear in code, per the precedent in
  `examples/s2-01-external-consumers/client_claude_agent.py`.

### 5. [Judgement] Two grep-shaped criteria met by stating the teaching without spelling the token

- **Issue:** two acceptance criteria are literal greps that a *docstring* would
  trip: `grep -ci 'gemini' model_stub.py == 0` while the plan's action asks the
  docstring to say which branches of `replay_server.py` were not carried, and
  `grep -c 'environ.get' client_anthropic.py == 0` while the plan's action asks
  the file to explain why a defaulted read is the violation.
- **Fix:** the same choice plan `20-03` made for the LangGraph bridge package —
  *"That server's second-vendor branch, its URL-model helper and its model-label
  environment seam are not carried"*, and *"a defaulted environment read is a
  prompt in code wearing an environment variable as a hat"*. The greps keep
  their signal; the teaching is intact.

### 6. [Judgement] `client_anthropic.py` is 288 lines, not the plan's "~150 target"

The siblings it is asked to match are 186 (`client_adk.py`) and 235
(`client_langgraph.py`), so "~150" describes neither. Leg 2 additionally carries
three named environment refusals and the MCP envelope unwrap that the siblings
do not need. The module docstring was trimmed once (293 → 288) and no further:
the asymmetry `H-07` asks to be *stated* is the docstring. The line budget is
declared in the README by plan `20-06`/`20-08` and measured from what exists, so
nothing is gated on this today — flagged here so that plan measures three files
and not two.

### 7. [Judgement] The prompt document also carries the model label and the exchanges

`model-conversation.yaml` is one declared document read by two programs, rather
than a prompt document plus a script document. The prompt, the pinned model and
the conversation are one fact about leg 2, and splitting them would create two
files that have to agree.

### 8. [Rule 1 — Bug, post-review] The extracted recipe was incomplete, and the gap was audible

- **Found during:** coordinator review of the three committed tasks.
- **Issue:** the offline recipe inherited verbatim from the spike omits
  `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` and carries
  `DISABLE_NON_ESSENTIAL_MODEL_CALLS`, a name absent from the bundled binary.
  The CLI therefore opened every session with a title-generation call, which
  the stand-in correctly refused — on every green run.
- **Fix:** the real variable added; the inert one kept and labelled; the
  declared document's header now says exchange 0 is only the first request
  *because* of that variable. Full diagnosis, rejected alternatives and three
  controls in the section above.
- **Files:** `examples/hw1-harness-clients/runner/model_stub.py`,
  `examples/hw1-harness-clients/runner/model-conversation.yaml`
- **Consequence for `20-07`:** the extraction that plan depends on is now
  *better* than the spike it replaces, not merely equal to it. Worth saying
  when the spike is deleted.

## Known stubs

None. Leg 2 runs on the default path, in CI, against a seeded subject, and its
default path makes no live model call.

## Open residual, carried unchanged

**That the x86_64 wheel of `claude-agent-sdk==0.2.128` bundles the CLI binary is
still UNVERIFIED** and cannot be observed from this aarch64 host. It is recorded
in `20-VALIDATION.md` as the phase's one manual-only check. **No fallback path
was built** — a second leg-2 path CI never exercises is criterion 6's own
failure mode. Verified here instead: the aarch64 wheel does carry
`claude_agent_sdk/_bundled/claude`, and every drive above ran against it.

## Threat flags

None. The plan's register is discharged as written:

- **T-20-13** — the CLI's egress is `ANTHROPIC_BASE_URL` at loopback with the
  four `DISABLE_*` variables, the version-check skip, and `HOME` /
  `CLAUDE_CONFIG_DIR` in a per-run temporary directory. Measured injected set
  above.
- **T-20-14** — drift, exhaustion, pinned-model drift and the unrouted probe
  each observed refusing.
- **T-20-15** — the stand-in's failure is the run's failure, observed by
  removing a declared exchange. Leg 2's exclusion from the socket guard and the
  reason are written into `drive.py`'s docstring for `20-05` and `20-08` to
  restate.
- **T-20-16** — `ANTHROPIC_AUTH_TOKEN` is the non-empty placeholder `"offline"`;
  no real credential is introduced and no code path would reach a real endpoint
  with it.
- **T-20-17** — `_terminate` in a `finally` with a kill fallback, per leg;
  a process-table scan after a full drive found no surviving stand-in.
- **T-20-SC** — no package installed, no CI step added; `pyproject.toml` and
  `.github/workflows/` byte-unchanged.

## Self-Check: PASSED

All three created files exist on disk; all three task commits resolve
(`682cf88`, `8b085c6`, `75c7a33`).
