---
phase: 20-client-access-from-three-harnesses-adk-anthropic-agent-sdk-a
plan: 03
subsystem: examples — harness client legs
tags: [adk, langgraph, mcp-stdio, zero-ccf-imports, payload-assertion, controls]
requires:
  - "20-02: drive.py (build_subject, seed, seeded_subject, resolve_door, build_question, request_violations, reference run, compare_addresses, marker_violations), question.yaml, the make target"
  - "20-01: scenario-rows.yaml and its four declared marker properties"
  - "runtime/ccf_runtime/mcp/egress.py::request_context_product — the door being called"
  - "src/ccf/products/door.py::PRODUCT_REQUEST_TOOL, ::WireRequest — the tool name and the encoded question's three fields"
provides:
  - "examples/hw1-harness-clients/client_adk.py — leg 1, Google ADK over McpToolset/StdioConnectionParams"
  - "examples/hw1-harness-clients/client_langgraph.py — leg 3, a compiled StateGraph over a raw mcp stdio session"
  - "examples/hw1-harness-clients/runner/drive.py::known_legs — structural leg discovery"
  - "examples/hw1-harness-clients/runner/drive.py::payload_violations — criteria 1-3 as a function of three doctorable arguments"
  - "examples/hw1-harness-clients/runner/drive.py::observed_markers, ::drive_leg, ::reference_run"
  - "marker_violations(names, chrome_words) — the console vocabulary is now a parameter"
affects:
  - "20-04: leg 2 joins by adding examples/hw1-harness-clients/client_anthropic.py — no registry line to edit here"
  - "20-05: --live and the no-model guard hang off drive.py::main and the two legs' argv surface"
  - "20-06: the purity gate and the per-module line budget are measured from these two client files"
  - "20-08: the README documents the three-flag argv surface and the WireRequest encode"
tech-stack:
  added: []
  patterns:
    - "structural discovery over a hand-maintained registry (client_*.py IS the leg list)"
    - "assertion functions taking every input as a parameter, so a control can doctor either operand"
    - "one declared question document interpreted by the runner, carried to each client on argv"
key-files:
  created:
    - examples/hw1-harness-clients/client_adk.py
    - examples/hw1-harness-clients/client_langgraph.py
  modified:
    - examples/hw1-harness-clients/runner/drive.py
decisions:
  - "Each leg prints the whole Context Product, not the payload alone — criteria 1-3 say the client prints the returned product, and the vessel is what the door served"
  - "The runner echoes a per-leg DIGEST line rather than each leg's captured stdout, because the product itself carries a 64-hex policy-bundle version that would defeat the one-distinct-address check while proving nothing"
  - "No `_terminate` helper: every child goes through subprocess.run with a timeout and cannot outlive the call; the door is spawned one process further down by the client's own harness library (H-01)"
  - "The question document carries `tool` and `temporal_boundary` beside `arguments`, so no client selects a tool from a literal and none infers the boundary from asked_at"
metrics:
  duration: ~3h
  completed: 2026-08-20
requirements: [CLNT-23, CLNT-24]
---

# Phase 20 Plan 03: The ADK and LangGraph Legs — Summary

Two foreign harnesses reach a governed Context Product through one `mcp+stdio`
door, with no model in either path and no `ccf` import in either file, and both
land on the same content address the reference client does.

## What was built

**`examples/hw1-harness-clients/client_adk.py`** (186 lines) registers the door
as an ordinary MCP tool — `McpToolset(StdioConnectionParams(StdioServerParameters(...)))`
— lists its tools, selects the one the question document names, calls it once,
and prints the content address and the Context Product. No `LlmAgent`, no
`Runner`, no model.

**`examples/hw1-harness-clients/client_langgraph.py`** (235 lines) is the same
program a second way: a compiled two-node `StateGraph` (`discover` → `ask`)
whose node hand-binds the discovered tool as a `langchain_core`
`StructuredTool` over a raw `mcp` stdio session. No bridge package, none
installed, `pyproject.toml` byte-unchanged.

**`examples/hw1-harness-clients/runner/drive.py`** (+360/-58) discovers legs
structurally, gives each its own seeded copy, drives it on three flags, parses
its address from stdout alone, and folds three checks into one non-zero exit
channel.

## The measurement that matters

```
reference address   5d7bfa49f5b3f65add25ea61220a191a91982f5ae97901e010b26c5ca8dc37f5
leg adk             5d7bfa49f5b3f65add25ea61220a191a91982f5ae97901e010b26c5ca8dc37f5  MATCH  names: Kestrelmark Industries, Volanti Logistics, Brightpath Materials
leg langgraph       5d7bfa49f5b3f65add25ea61220a191a91982f5ae97901e010b26c5ca8dc37f5  MATCH  names: Kestrelmark Industries, Volanti Logistics, Brightpath Materials
legs compared       2
```

Three programs, three separately-seeded copies, three spawned doors, **one**
content address: `make example-hw1-harness-clients | grep -oE '[0-9a-f]{64}' | sort -u | wc -l` returns `1`.

**The two clients encode the request identically**, measured by importing both
modules and calling `encoded_request` on the same document:

```
adk : {"parameters":{"revenue_threshold":1000000000},"product_id":"hw1.companies-over-revenue","temporal_boundary":"2026-08-01T00:00:00+00:00"}
lg  : {"parameters":{"revenue_threshold":1000000000},"product_id":"hw1.companies-over-revenue","temporal_boundary":"2026-08-01T00:00:00+00:00"}
byte-identical: True
```

## Task-by-task

| Task | Commit | What landed |
|---|---|---|
| 1 — leg 1, Google ADK | `959a7d0` | `client_adk.py`: `parse_args`, `encoded_request`, `outcome_text`, `report`, async `main` |
| 2 — leg 3, LangGraph | `20c0c19` | `client_langgraph.py`: `AskState`, `connect`, `build_graph` (`discover`/`bind`/`ask`), `report`, async `main` |
| 3 — runner registration | `2541806` | `known_legs`, `client_program`, `payload_violations`, `observed_markers`, `drive_leg`, `reference_run`, `_subject_factory`, `_labelled`; `marker_violations` gains `chrome_words`; `build_question` grows `tool` + `temporal_boundary` |

## Hand-driven evidence for the two legs

Both legs were driven by hand against a persistent seeded copy before the
runner knew about them. The subject was built with `drive.py::build_subject`
and `::seed` (so it is the same subject CI uses), and the door and question
came from `::resolve_door` and `::build_question`. Abbreviating the seeded root
as `$S`:

```
.venv/bin/python examples/hw1-harness-clients/client_adk.py \
  --server-command .venv/bin/python \
  --server-arg $S/server/serve.py --server-arg $S/deployment \
  --question-json '{"tool":"request_context_product",
                    "temporal_boundary":"2026-08-01T00:00:00+00:00",
                    "arguments":{"tenant":"hw1-demo",
                                 "product_class":"hw1.companies-over-revenue",
                                 "version":"1.0.0",
                                 "subject":"companies-over-revenue",
                                 "intent":"revenue-screening",
                                 "freshness":"published-annual-filings",
                                 "asked_at":"2026-08-01T00:00:00+00:00",
                                 "parameters":{"revenue_threshold":1000000000}}}'
```

(the same command with `client_langgraph.py` for leg 3). Both exited 0, both
printed `content address    5d7bfa49f5b3f65add25ea61220a191a91982f5ae97901e010b26c5ca8dc37f5`
on stdout, and both printed the product beneath it, carrying all three declared
company `name` values above the threshold. ADK's `[EXPERIMENTAL]` warnings and
the door's `Processing request of type …` logging both landed on stderr, as
predicted.

## Controls — every one observed red, with its mutation named

Two layers were run, because the plan's controls doctor an **input** and that
alone does not show a control is bound to the branch it claims to watch.

### Layer 1 — the six named controls (doctored inputs)

| Control | Doctored input | Observed violation |
|---|---|---|
| **A** — address-only stdout | `payload_violations('ACME WIDGETS ' + 'a'*64, 'a'*64, ['ACME WIDGETS'])` | *"the leg's stdout carries no declared company name, so it printed a content address rather than the Context Product the address names"* + the set-divergence violation |
| **B** — one fewer name than the reference | `payload_violations('Ambervale Holdings Krellwyn Industrial', 'Ambervale Holdings', ['Ambervale Holdings','Krellwyn Industrial'])` | *"the leg's stdout names ['Ambervale Holdings'] and the reference names ['Ambervale Holdings', 'Krellwyn Industrial']; an equal content address does not by itself make two printed products the same product"* |
| **C** — empty marker list | `payload_violations(ref, leg, [])` | *"no declared markers — a payload assertion over an empty marker set passes without reading any output at all"* |
| **D** — the substring mutation | `marker_violations(good[:5] + ['Tavenmoor Group International'], chrome)` where `good` already holds `'Tavenmoor Group'` | *"'Tavenmoor Group' is a substring of 'Tavenmoor Group International'; a stdout match on the shorter one cannot say which row printed"* |
| **E** — the hex-only mutation | `marker_violations(good[:5] + ['Beadface'], chrome)` | *"'Beadface' is hex digits and spaces only, so it matches inside the 64-character content address every leg prints"* |
| **F** — the chrome-collision mutation | `marker_violations(good[:5] + ['Revenue Partners'], chrome)` | *"'Revenue Partners' collides with console vocabulary ['revenue']; a marker the runner prints itself is true of a run that printed no payload"* |

Baselines: `payload_violations(ref, leg, ['ACME WIDGETS'])` and
`marker_violations(good, chrome)` both return `[]`.

**`chrome_words` is genuinely a parameter, demonstrated rather than asserted:**
`marker_violations(good, ['ambervale'])` — an otherwise-clean marker set against
a doctored one-word vocabulary — returns
*"'Ambervale Holdings' collides with console vocabulary ['ambervale']"*. A
function reading `CONSOLE_VOCABULARY` internally could not produce that.

### Layer 2 — branch binding (sabotage the shipped code)

Each guard branch was deleted from a scratch copy of the shipped `drive.py`
(the removed lines printed and inspected on every cut, so no mutation silently
took a `return` with it), the copy imported, and the matching probe re-run.

| Property | Branch deleted | Probe before | Probe after |
|---|---|---|---|
| P1 empty `declared_names` (CONTROL C) | `if not declared_names:` (5 lines) | RED | **GREEN** |
| P2 no marker in leg stdout (CONTROL A) | `if declared_names and not in_leg:` (5) | RED | **GREEN** |
| P3 marker-set divergence (CONTROL B) | `if set(in_leg) != set(in_reference):` (6) | RED | **GREEN** |
| M1 empty marker set | `if not names:` (5) | RED | **GREEN** |
| M2 duplicate names | `if lowered in seen:` (2) | RED | **still RED — see below** |
| M3 four-character floor | `if len(name) < MINIMUM_MARKER_CHARS:` (5) | RED | **GREEN** |
| M4 hex-only (CONTROL E) | `if _HEX_ONLY_RE.fullmatch(name):` (5) | RED | **GREEN** |
| M5 chrome collision (CONTROL F) | the `collisions = …` block (6) | RED | **GREEN** |
| M6 substring pair (CONTROL D) | the substring double loop (7) | RED | **GREEN** |

**Controls that could not be made to fail: none.**

**M2 is double-gated, and that is a finding rather than a gap.** Deleting the
duplicate branch alone does not silence a duplicate marker set, because an
exact duplicate is also a substring of itself and M6 catches it. Verified by
deleting **both** branches: the duplicate probe then returns `[]`, as does
CONTROL D's. So the distinctness property is measured by two independent
branches rather than none — the opposite of the failure this register exists
to refuse. M2 is a wave-2 property and is not one of controls A–F.

### Layer 3 — two end-to-end controls, driven through the real runner

Both used a scratch `client_*.py` written into the example root, driven, then
deleted. They also incidentally prove **structural leg discovery**: neither
file was registered anywhere, and both were driven by name.

- **The divergence control.** `client_scratchdiverge.py` — leg 1 with the first
  character of its printed address flipped, and everything else identical, so
  only the address diverges. The runner exited **1**, printed
  `leg scratchdiverge  0d7bfa49…  DIVERGED  names: Kestrelmark Industries, Volanti Logistics, Brightpath Materials`,
  and raised *"the harness legs did not agree with the reference: leg
  'scratchdiverge' reported 0d7bfa49…, the reference reported 5d7bfa49…"*.
- **CONTROL A, end to end.** `client_scratchaddressonly.py` — leg 1 with the two
  product-printing lines removed. It printed a **correct** address and the
  runner's own line read `MATCH  names:` (empty). Every 64-hex check in this
  phase passed, and `payload_violations` refused it anyway: *"leg
  'scratchaddressonly' did not print the product"*, exit **1**. This is the
  exact gap the check exists for, observed rather than argued.

Both scratch files were removed; `git status --porcelain examples/` afterwards
showed only the intended `drive.py` modification.

## Deviations from plan

### 1. [Judgement] The runner echoes a per-leg digest, not each leg's stdout

- **Issue:** two acceptance criteria pull in opposite directions. One requires
  `make example-hw1-harness-clients` stdout to carry a declared company name;
  another requires exactly **one** distinct 64-hex string across that same
  stdout. A served product carries
  `lineage.policy_bundle_versions: ["dd2c515f…"]` — a second 64-hex token that
  is not a content address — so echoing a leg's captured stdout would satisfy
  the first criterion and break the second while proving nothing about address
  agreement.
- **Fix:** each leg still prints the whole Context Product (criteria 1-3 are
  about the *client's* output, and `payload_violations` reads exactly that
  captured stdout). The runner prints a digest line per leg —
  `leg <name>  <address>  MATCH|DIVERGED  names: …` — so both criteria are met
  by the aggregate output and neither is met by weakening the other. Full leg
  output still rides the failure message.
- **Files:** `examples/hw1-harness-clients/runner/drive.py`
- **Commit:** `2541806`

### 2. [Rule 3 — Blocking] The plan's automated probe names a module that does not exist

- **Issue:** this plan's `<verify>` block does
  `importlib.import_module('run')` and reads `run.CONSOLE_CHROME`. There is no
  `run.py` under this example — `H-11` and two shipped gates forbid one, which
  is why wave 2 named the runner `drive.py` — and the console vocabulary
  shipped in wave 2 as `CONSOLE_VOCABULARY`.
- **Fix:** the probe was run against `drive` and `drive.CONSOLE_VOCABULARY`,
  unchanged in every other respect. No file was renamed and no constant was
  renamed to match a plan snippet; renaming either to satisfy the snippet would
  have been the gate-accommodating move `H-12` forbids.

### 3. [Judgement] The bridge package and the prebuilt node are described, not named

- **Issue:** the plan's action text asks `client_langgraph.py` to reproduce the
  rationale for taking no bridge package and for not using the prebuilt
  tool-executing node; its acceptance criteria then require
  `grep -c 'ToolNode\|langchain_mcp_adapters'` to return `0`. Naming them in
  prose satisfies the action and defeats the grep.
- **Fix:** the docstring states both rationales in full without spelling either
  symbol — the same choice `examples/s2-01-external-consumers/client_langgraph.py`
  already made (*"No third-party LangChain-to-MCP bridge package is used"*).
  The grep keeps its signal; the teaching is intact. Both counts are `0` and
  `importlib.util.find_spec('langchain_mcp_adapters')` is `None`.
- **Commit:** `20c0c19`

### 4. [Judgement] `reference_address` → `reference_run`, returning `(address, stdout)`

- **Issue:** `payload_violations` needs what the reference **printed**, not only
  what it hashed to. Re-running `consume.py` to obtain it would mean two
  reference runs and legs compared against whichever answered second.
- **Fix:** one function returning both halves, renamed so the name does not lie
  about what it returns. Nothing outside `drive.py` referenced the old name
  (checked across `*.py`, `*.md`, `*.yaml`, `Makefile`); the plan documents that
  mention it are prose read-lists.
- **Commit:** `2541806`

### 5. [Rule 2 — CLAUDE.md §6.4] The tool name and the boundary are told, not inferred

- **Issue:** the plan says the client must select the tool "by name from the
  question document", but wave 2's `build_question` returned eight flat address
  keys with no tool name in them. A client would have had to spell
  `request_context_product` as a literal. Separately, a client could have
  inferred the `WireRequest`'s `temporal_boundary` from `asked_at` — correct on
  this pinned path and wrong on a deferred one.
- **Fix:** `build_question` now returns `{tool, temporal_boundary, arguments}`.
  `tool` is read from `ccf.products.door::PRODUCT_REQUEST_TOOL`, so the runner
  spells no tool name either and an SDK rename reaches both legs without
  touching them. `temporal_boundary` is stated rather than derived.
- **Commit:** `2541806`

### 6. [Deferred again] Still no `_terminate` helper

Wave 2 deferred it to "the first leg that needs it". No leg needs it. Every
child this runner starts goes through `subprocess.run` with
`LEG_TIMEOUT_SECONDS`, which cannot outlive its own call and kills the child on
timeout; the door is spawned by each client's own harness library (`H-01`), one
process further down than the runner can reach. `drive_leg`'s docstring records
the reasoning where a reader looking for the helper will find it. A
`_terminate` with no caller would still be dead code.

## Known stubs

None. Both legs run on the default path, against a seeded subject, in CI.

## Threat flags

None. No new network endpoint, auth path, file-access pattern or schema change
at a trust boundary. The plan's register is discharged as written:

- **T-20-09** — each leg's address is parsed from **stdout only** and compared
  against a `consume.py` run on the same seeded copy; `compare_addresses` still
  refuses an empty observation.
- **T-20-39** — `payload_violations` is called per leg on the default path;
  CONTROL A was observed red both as a unit probe and end to end through a real
  address-only client.
- **T-20-10** — `client_adk.py::outcome_text` branches on the graceful
  `"error"` key before anything is printed.
- **T-20-11** — `env=dict(os.environ)` is passed explicitly by both legs and by
  the runner's leg driver, the accepted posture.
- **T-20-12** — the AST probe (plain import, from-import, deferred, relative)
  reports zero `ccf` imports in both clients.
- **T-20-SC** — no package installed; `git diff --stat -- pyproject.toml` is
  empty.

## Verification

| Command | Result |
|---|---|
| `make example-hw1-harness-clients` | exit 0; names `adk` and `langgraph`; 2 `MATCH` lines |
| `… \| grep -oE '[0-9a-f]{64}' \| sort -u \| wc -l` | **1** |
| `… \| grep -c 'Kestrelmark Industries'` | 2 (the payload markers reach the aggregate stdout) |
| `drive.py --legs nosuchleg` | exit 1 — *"unknown legs: ['nosuchleg']; discovered ['adk', 'langgraph']"* |
| `drive.py --legs adk` | exit 0, `legs compared 1` |
| AST zero-`ccf`-import probe, both clients | `ok` |
| domain-literal grep, both clients | `0` |
| `grep -c 'MCPToolset'` (`client_adk.py`) | `0` |
| `grep -c 'ToolNode\|langchain_mcp_adapters'` (`client_langgraph.py`) | `0` |
| `find_spec('langchain_mcp_adapters')` | `None` |
| `mypy` on each client file | no issues (both are outside `[tool.mypy] files = ["src","runtime"]`) |
| `make examples` | exit 0 (eleven examples) |
| `make gate-tools` | exit 0, 154 passed |
| **`make ci-core`** | **exit 0 — 4018 passed, 118 skipped** |
| `.venv/bin/python -m tools.lints --all` | exit 0 |
| `pytest tests/examples -q` | 391 passed, 37 skipped |
| `pytest tests/invariants/test_citation_coverage.py -q` | 5 passed |
| `pytest tests/examples/test_hw1_harness_clients_wiring.py test_client_example_purity.py -q` | 27 passed |
| `pytest tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current -q` | **passed** |
| `git diff --stat 9e4bd0e..HEAD -- src/ pyproject.toml` | empty |
| `git status --porcelain examples/hw1-companies-over-revenue/` | empty |

**The retirement inventory was regenerated as the last action of task 3**
(`.venv/bin/python tools/retirement_sweep.py --report` → *"234 coupling rows
across 75 files … 1812 files scanned"*) and came back **byte-identical**; the
criterion is the currency test passing, which it does, not the file changing.

Layout, as ruled: no `run.py` and no `artifacts/` anywhere under
`examples/hw1-harness-clients/`; the example root holds exactly the two
`client_*.py`.

## Self-Check: PASSED

`examples/hw1-harness-clients/client_adk.py`,
`examples/hw1-harness-clients/client_langgraph.py` and
`examples/hw1-harness-clients/runner/drive.py` all exist on disk; commits
`959a7d0`, `20c0c19` and `2541806` all resolve in `git log`. Checked
mechanically, not by recollection.
