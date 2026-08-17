---
phase: 18-mcp-transport-the-second-door-and-the-portability-proof
plan: 10
subsystem: mcp-egress-door
status: partial
tags: [mcp, http-api, product-request, d-impl-133, width-ceiling]
requires:
  - D-IMPL-133 (both doors carry parameters — the standing ruling this implements)
  - D-IMPL-121 (validation stays at the resolver, never at a door)
  - D-IMPL-103 (one level of declared nested types)
provides:
  - the MCP egress tool's `parameters` argument
  - the HTTP product route's `?parameters=` JSON-object query surface
  - ERROR_PRODUCT_PARAMETERS_MALFORMED
  - assert_same_verdicts / assert_type_mismatch_refused (the width ceiling, mechanized)
affects:
  - runtime/ccf_runtime/mcp/egress.py
  - runtime/ccf_runtime/http_api/routes/product.py
  - runtime/ccf_runtime/http_api/errors.py
  - openapi.json
tech-stack:
  added: []
  patterns:
    - "verdict-over-door-callables: both doors compared as `Callable[[Mapping], Verdict]` so a control substitutes a divergent door into the real assertion"
    - "non-vacuity guard: an assertion refuses a table that cannot fail for the reason it exists"
key-files:
  created:
    - tests/mcp/test_egress_parameters.py
    - docs/surface-changes/17-10-both-doors-carry-parameters.md
  modified:
    - runtime/ccf_runtime/mcp/egress.py
    - runtime/ccf_runtime/http_api/routes/product.py
    - runtime/ccf_runtime/http_api/errors.py
    - tests/crossproc/test_mcp_egress.py
    - docs/DECISIONS.md
    - openapi.json
decisions:
  - "D-IMPL-133 Addendum A — the recorded `parameters={}` objection is half false, half honoured"
metrics:
  tasks_completed: 1
  tasks_total: 4
  duration: ~1 session
  completed: 2026-08-17
---

# Phase 18 Plan 17-10: MCP Transport — Partial Summary

Task 1 shipped: **both parameterised product doors now carry a client's
parameters, and one shared case table holds them to the same width.** Tasks 2,
3 and 4 were **not executed**. Two findings below are load-bearing for whoever
picks this up, and one of them says Task 4 cannot pass as the plan writes it.

## Status: 1 of 4 tasks

| Task | Name | Status | Commit |
| --- | --- | --- | --- |
| 1 | The egress tool carries a client's parameters | **complete** | `74a4224` |
| 2 | The MCP door emits the canonical refusal envelope | **not started** | — |
| 3 | The `mcp+stdio` adapter, sync at the surface | **not started** | — |
| 4 | Bind MCP into the conformance suite | **not started** | — |

Stopping after Task 1 was a judgement, not an accident: Tasks 2–4 compose into
the phase's central claim (*"the suite did not move to let it"*), and a
half-built adapter bound into a parity suite is precisely this repository's
recurring defect — a check that reports green while comparing nothing. The
measurements below are recorded so the next executor starts on facts.

## Task 1 — what shipped

`D-IMPL-133` (Dave, 2026-08-14) had already ruled *"both doors carry
`parameters`. Both, not one."* It was unimplemented. It is implemented now.

- **MCP egress tool** takes an optional eighth argument,
  `parameters: dict[str, Any] | None = None`, forwarded **verbatim** to
  `ProductRequest.parameters` — no coercion, no defaulting, no inspection.
- **HTTP product route** takes an optional `?parameters=` carrying **one JSON
  object**, parsed and carried on identical terms.
- **`ERROR_PRODUCT_PARAMETERS_MALFORMED`** refuses text that is not a JSON
  object rather than falling back to the empty mapping — a fallback would
  answer a question the caller did not ask while reporting success.
- Supplying `parameters` with none of the four §6.3 axes is refused
  `ERROR_PRODUCT_REQUEST_INCOMPLETE`: the declared remainder qualifies a
  question and there is none to qualify.
- Neither door validates. `refuse_request` is still the resolver's call
  (`D-IMPL-121`), so this is a two-line repair rather than a seam widening.

### The parameter case table, and its size

**Five cases**, in `PARAMETER_CASES`, run against **both real doors** with
identical verdicts required:

| Case | Verdict (both doors) |
| --- | --- |
| `{minimum_score: 11}` | `served` |
| `{minimum_score: 11, region: "north"}` | `served` |
| `{}` | `missing-required-parameter` |
| `{minimum_score: 11, not_declared_by_this_class: "smuggled"}` | `undeclared-parameter` |
| `{minimum_score: "11"}` | `type-mismatch` |

Plus **two** `COERCION_CASES` for the type-mismatch sibling assertion.

A verdict is what `refuse_request` says about the request **the door actually
carried** — which under `D-IMPL-133` is exactly the half a door is responsible
for, and the only definition under which the two doors are comparable at all.

### The non-vacuity guard is the part that matters

`assert_same_verdicts` **refuses a table in which no case is served.** Without
that guard the table passes against the two *unrepaired* doors: both carried
`{}`, so every case reached the resolver as the same empty mapping and the two
agreed perfectly while carrying nothing. This was not theoretical — it was
observed during the RED run, where the wider-door control tripped the vacuity
guard instead of the width assertion because the HTTP door still carried
nothing.

### Sabotage controls (D-22) — three, all shipped tests, all observed firing

| Control | Divergent subject passed into the **real** assertion | Observed |
| --- | --- | --- |
| `test_the_width_assertion_fires_on_a_wider_mcp_door` | a fake `ask_mcp` that admits the undeclared parameter | raises, matches `wider` |
| `test_the_width_assertion_fires_on_a_table_that_never_serves` | two doors that never serve | raises, matches `no served case` |
| `test_the_coercion_assertion_fires_on_a_coercing_door` | a door that reads `"11"` as `11` and serves | raises, matches `type-mismatch` |

No control edits `runtime/` and reverts. **`git status --porcelain runtime/`
was empty after running them** (verified). Each is a test that runs on every CI
run forever, not an edit that leaves nothing in the tree.

### The `16-26` absorption, as written into `docs/DECISIONS.md`

Recorded as **`D-IMPL-133` Addendum A**. Its measured justification, in short:
`16-26` was filed *"neighboring, not gating"* and is gating, because the
conformance fixture class declares `minimum_score` **required**
(`tests/client/fixtures/deployment/ccf_config.yaml:46`). With `parameters={}`
hard-wired, an MCP adapter could not ask the phase's own question, could not
pass `D-15(a)` served parity, and could not carry `D-23` — every call would
have refused `missing-required-parameter` identically, so the parity legs would
have compared two refusals and reported green while proving nothing.

### The recorded reason was amended, never deleted — and its two halves differed

The plan required the `parameters={}` docstring reasoning be treated as a
constraint on the fix. It was, and measurement split it:

- **The coercion half is FALSE as measured.** It claimed *"a flat tool-argument
  map cannot carry `D-IMPL-103`'s declared nested types without the door
  guessing at coercions."* An MCP tool-argument map is **not flat and not
  string-valued — it is JSON.** Probed against `mcp==1.28.1`: a presented `3`
  arrived `int`, `"3"` arrived `str`, `true` arrived `bool`, and
  `{"a":[1,2]}` arrived a nested `dict`. Nothing is left to guess at.
- **The width half is TRUE and still binding.** The HTTP door hard-wired the
  identical `parameters={}` for the identical reason, and those two were the
  only two `ProductRequest` construction sites for a door in `runtime/`.
  Honoured by repairing **both** — which is what `D-IMPL-133` ruled — and the
  HTTP door carries JSON rather than flattened query keys precisely so the
  objection does not become true again on the door where it was written.

`command grep -n "parameters={}" runtime/ccf_runtime/mcp/egress.py` returns
nothing; `command grep -c "coerc" runtime/ccf_runtime/mcp/egress.py` returns 5.

## Deviations from Plan

### 1. `[Rule 2 — missing critical functionality]` `routes/product.py` was edited, and the plan's `files_modified` did not list it

`D-IMPL-133` — the resolved ruling the plan cites as its own authority —
governs `routes/product.py` explicitly and rules *"both, not one."* Repairing
only the MCP tool would have produced exactly the asymmetry the recorded reason
forbids. **The plan's own acceptance criterion is unsatisfiable without this**:
a shared case table asserting identical verdicts cannot pass when one door
structurally cannot carry any case. Commit `74a4224`.

### 2. `[Rule 3 — blocking]` `tests/mcp/` shadows the `mcp` distribution

Creating `tests/mcp/__init__.py` makes `import mcp` resolve to the test package
(`tests/` is on `sys.path`), and collection dies with
`ModuleNotFoundError: No module named 'mcp.client'`. **The directory ships
without `__init__.py`**, which keeps it off the package namespace. This is why
every pre-existing MCP door test lives in `tests/crossproc/`.

### 3. `[Rule 1 — bug]` three shipped assertions moved, none to make a failure go away

- `test_the_tool_advertises_exactly_the_seven_argument_names` — one set was
  asserted by equality against **both** `properties` and `required`, which
  cannot express an optional argument. Now eight properties against seven
  `required`, plus an explicit `role not in properties`. The split is the
  assertion: `parameters` drifting into `required` would force every caller to
  send an empty object; a §6.3 axis drifting out would make a partial address
  representable again.
- `test_the_tool_handler_takes_no_role_and_no_caller_supplied_address` — the
  absent-name list keeps `role`, `schema_name`, `schema_version` and drops
  `parameters`, because those three claim an **address** and `parameters` does
  not.
- `openapi.json` regenerated (one additive query-parameter entry).

### 4. `[Rule 3 — blocking]` four bookkeeping gates went red and were repaired

Caught only because `make ci-core`'s exit code was branched on. The first
`ci-core` run reported `EXIT=2` with 10 failures while the background-task
notification claimed exit 0 — the notification reflected a trailing `echo`.
Repairs: the surface fragment over-claimed `Change type: added` for two
existing names (now `behavior`); `docs/surface/v0.2-surface.json` was
regenerated and reverted (single-owner rule — only `15-01` and `15-21` write
it); `docs/SURFACE-CHANGES.md` reassembled; and three unanchored `path.py:line`
citations converted to `path.py::Symbol` per `D-IMPL-114`, keeping the held-back
population at 14 rather than raising a ratchet.

## Findings — verified against the tree, not asserted

### FINDING 1 (blocking for Task 4): served parity across in-process and MCP **cannot pass** as the plan is written

`replay_ref` is in `GUARDED_FIELDS` (`src/ccf/client/result.py`), so
`result_fields()` includes it and `assert_served_parity` compares it on every
served result. `Result.replay_ref` reads `WireOutcome.replay_ref`
(`client.py:208`). The in-process adapter supplies
`outcome.replay_ref.uri`. **The MCP egress door emits
`canonical_bytes(servable.product)` and nothing else — it has no replay-ref
channel at all**, so an `mcp+stdio` adapter would produce `replay_ref=None` and
the served-parity leg would report a disagreement on that field.

The plan half-notices this — `WireOutcome.replay_ref`'s own docstring says
*"No shipped door emits this today, which is a defect the client seam exists to
fix"* — but neither Task 2 nor Task 3 schedules the fix, while Task 4 asserts
served parity will hold. **Task 4 needs either a replay-ref channel on the MCP
door or an explicit ruling that this field is exempt from cross-adapter
parity.** The second would weaken a shipped assertion to admit a feature, which
`D-GATE-17` names as this phase-family's signature defect.

### FINDING 2 (design input for Task 2): a refusal must be the tool's RETURN value, not a raised exception

Measured against `mcp==1.28.1`: a tool that raises is wrapped by FastMCP as
`ToolError: Error executing tool <name>: <message>` and reaches the client as
`isError=True` with that **prose prefix**. Carrying a `RefusalEnvelope` that
way would force the client to strip a server's wording — string-parsing prose
for a governed answer.

The workable shape: the served path keeps returning the product JSON
(byte-identical to the resource, which Task 1 asserts), and the refusal path
returns the envelope's canonical JSON. The two are discriminable **structurally**
rather than by sniffing, because `RefusalEnvelope` and `ContextProductContract`
are both `extra=forbid` with disjoint required fields, so neither can validate
as the other.

### FINDING 3 (advisory): the plan's Task 3 verification command names a symbol that does not exist

The plan's automated check is
`from ccf.client.binding import SCHEMES`. The registry is named
**`SCHEME_REGISTRY`** (`src/ccf/client/binding.py`). A later executor running
that command verbatim gets an `ImportError` rather than a verdict.

## Requirements

`CLNT-15` is **partially** satisfied — its parameters clause is discharged; its
refusal-envelope and conformance clauses are not. `CLNT-12` is untouched by
this plan's shipped half. Neither is marked complete.

## Verification

Every run set `PYTHONPATH` to the worktree's `src:runtime` (the venv's editable
install resolves `ccf` to the main checkout), and every exit code was captured
and **branched on** rather than echoed.

| Command | Exit | Result |
| --- | --- | --- |
| `make ci-core` | **0** | `3804 passed, 118 skipped, 0 failed` |
| `gate-tools` (within `ci-core`) | 0 | `400 passed`, `154 passed` |
| `tools.lints --all` | 0 | clean |
| `mypy --strict` | 0 | 209 source files |
| `pytest tests/mcp/test_egress_parameters.py` | 0 | 9 passed |
| `pytest tests/crossproc tests/http_api tests/mcp` | 0 | 253 passed |

`make conformance` and `make docs-strict` were **not** run — they belong to
Tasks 3 and 4, which were not executed.

## Not done, and what it would take

- **Task 2** — refusal envelope at the door. Start from FINDING 2.
- **Task 3** — `mcp+stdio` adapter. `src/ccf/mcp/client.py` speaks
  **streamable HTTP only and reads resources only**: it has no stdio transport
  and no tool-call surface, so the adapter needs both added (that is the "say
  what is missing" the plan asks for). The harness-import lint permits the
  `mcp` import in `src/` — confirmed green with four such imports already
  present.
- **Task 4** — conformance binding. Needs a stdio server entry point that boots
  a deployment root the way `inprocess::_boot` does, and needs FINDING 1 ruled
  on first.

**`tests/client/conformance/suite.py` was not touched.**
`git diff tests/client/conformance/suite.py` is empty — but that is the trivial
truth, since Task 4 never ran. It is **not** evidence for the phase's
adapter-agnostic claim, and should not be reported as though it were.

## Self-Check: PASSED

- `runtime/ccf_runtime/mcp/egress.py` — FOUND
- `runtime/ccf_runtime/http_api/routes/product.py` — FOUND
- `runtime/ccf_runtime/http_api/errors.py` — FOUND
- `tests/mcp/test_egress_parameters.py` — FOUND
- `docs/surface-changes/17-10-both-doors-carry-parameters.md` — FOUND
- commit `74a4224` — FOUND in `git log`
