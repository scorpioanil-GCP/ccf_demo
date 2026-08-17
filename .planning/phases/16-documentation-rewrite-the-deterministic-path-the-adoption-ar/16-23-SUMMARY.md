---
phase: 16-documentation-rewrite-the-deterministic-path-the-adoption-ar
plan: 23
subsystem: L6 MCP egress / product delivery doors
tags: [mcp, egress, product-request, entitlement, authorization, d-impl-126]
requires:
  - "16-22 (surface-change glob and _PLAN_NUMBER widening; _SHAPE_MOVED_BY_FRAGMENT)"
  - "D-IMPL-108 / plan 15.5-15 (ProductResolverProtocol already five arguments)"
provides:
  - "ccf_runtime.mcp.egress.PRODUCT_REQUEST_TOOL — the opt-in parameterised product tool"
  - "ccf_runtime.mcp.egress.NaiveAskedAtRefused — the door's naive-instant refusal"
  - "build_egress_server(expose_product_tool=…, product_tool_description=…)"
  - "an in-process tool/resource parity matrix over all seven governance scenarios"
affects:
  - "D-IMPL-127 HW-2 — unblocked; the MCP door now takes a client's own question"
tech-stack:
  added: []
  patterns:
    - "opt-in exposure switch as a boolean + required prose pair (D-03)"
    - "request address bound to the handler's own path arguments (unrepresentable, not refused)"
    - "forwarded-Perspective asserted by value with a recorded negative control"
key-files:
  created:
    - docs/surface-changes/16-23-mcp-product-tool.md
  modified:
    - runtime/ccf_runtime/mcp/egress.py
    - tests/crossproc/test_mcp_egress.py
    - tests/crossproc/servers/mcp_egress_child.py
    - tests/test_surface_shape_capture.py
    - docs/SURFACE-CHANGES.md
    - .planning/phases/16-.../deferred-items.md
decisions:
  - "The tool takes no `role` parameter, so it is narrower than the resource beside it"
  - "schema_name/schema_version bound to the handler's own path arguments — mis-addressing unrepresentable"
  - "All four §6.3 axes required by the input schema — partial address unrepresentable, not refused"
  - "NaiveAskedAtRefused is a named ValueError subclass, not a typed ERROR_* code (hitl_server precedent)"
metrics:
  duration: ~2h
  completed: 2026-08-14
---

# Phase 16 Plan 23: The MCP Egress Product Tool Summary

An opt-in parameterised Tool now stands beside the egress door's unchanged
`ccf-product://` resource, taking whitepaper §6.3's four axes plus the three
address segments — so an MCP client can ask its own question, and the door
refutes the reading that a Context Product is a precalculated static object.

**BASE, recorded verbatim as the plan requires:**
`753a21d37938876f26ec335338eb273b4e21af71`

Every scope guard below is `git diff --stat $BASE..HEAD -- <path>`.

## Commits

| Task | Commit | What |
| ---- | ------ | ---- |
| 1 | `2c4353a` | `feat(16-23)`: the opt-in parameterised product tool on `egress.py` |
| 2 | `f78ce05` | `test(16-23)`: the in-process parity matrix, forwarded-perspective assertion, two-subjects proof |
| 3 | `e9fba97` | `docs(16-23)`: the surface fragment and three residuals against their rulings |

## What was built

### Task 1 — `runtime/ccf_runtime/mcp/egress.py`

- `PRODUCT_REQUEST_TOOL = "request_context_product"`, a module-level constant in
  `__all__`, on the `product_uri` reasoning (one definition, three readers).
- `NaiveAskedAtRefused(ValueError)` in `__all__`, on the shipped
  `hitl_server.NaiveActionTimeRefused` precedent — a **named** subclass so a
  deployment can catch this specific refusal, and a `ValueError` rather than a
  typed `ERROR_*` because it is a malformed argument, not a governance decision.
- Two keyword-only builder parameters, **both defaulting closed**:
  `expose_product_tool: bool = False`, `product_tool_description: str | None =
  None`. Either without the other raises `ValueError` naming both. No `DEFAULT_*`
  description constant ships (CINV-01).
- The tool body, in the mandated order: naive-`asked_at` refusal first →
  `verified_grant()` → `entitled_perspective(...)` **with the identical argument
  list the resource passes, `requested_role=None` included** → the returned
  perspective **bound to a local and forwarded** → `ProductRequest` addressed
  from the handler's own `product_class`/`version` with `parameters={}` → the
  unchanged five-argument resolver seam → the **identical**
  `canonical_bytes(servable.product).decode("utf-8")` the resource returns.
- Module docstring gains the two-surfaces paragraph; the builder docstring gains
  the opt-in rationale and `Raises:`.

**The resource, `PRODUCT_URI_TEMPLATE` and `ProductResolverProtocol` are
untouched.** No Protocol widened; nothing under `src/`.

### Task 2 — the security proof, in process

- `_local_world` gains a straight pass-through for the two tool arguments,
  defaulting closed, plus `_open_world` for the exposed case.
- `_call_tool_in_process` — the ASGI twin of `_read_in_process`, written to look
  like it (same `streamable_http_app()`, same explicit lifespan entry, same
  Bearer client factory), differing in the `operation` coroutine and in reading
  the refusal off `CallToolResult.isError` **as well as** from a raised
  `McpServerUnreachable`.
- `_both_surfaces_in_process` — **required, not an optimisation.** See
  *Deviations* below.
- A parametrized matrix over **all seven** governance scenarios, one
  `_local_world` server / one policy / one grant each, asserting served-vs-served
  or refused-vs-refused with the same `error_code`.
- The forwarded-`Perspective` assertion, by **value**, parametrized across two
  `resolved_role` values so a hard-coded perspective fails rather than coincides;
  the resource leg's request pinned to `None` and the tool leg's to a typed
  `ProductRequest` with its address, axes and empty `parameters` all asserted.
- `inputSchema` `properties.keys()` and `set(required)` compared to the seven
  names **by equality**; `inspect.signature` over the registered function for the
  absence of `role`/`schema_name`/`schema_version`/`parameters`.
- The zero-tools regression guard, the XOR builder test, the naive-instant
  refusal over the wire (with `forwarded` **and** `calls` both empty), and the
  tool-presence pin comparing raw bytes with `==`.
- The child (`mcp_egress_child.py`) now declares a request contract, discharges
  the `refuse_request` obligation, and **re-gates a per-question answer through
  `run_gates`** (a `ServableProduct` is unconstructible outside the gate path, so
  varying the answer means re-gating, never hand-building). It registers the
  tool, and two cross-process tests assert two `sha256` content addresses for two
  subjects and for two `asked_at` instants.

### Task 3 — the fragment and the residuals

`docs/surface-changes/16-23-mcp-product-tool.md` claims exactly the three names
that moved and no name that did not; three residuals recorded in the fragment and
in `deferred-items.md`, each **against the ruling that already governs it**.

## The two recorded negative controls

### 1. Fabricated perspective — the `DI-15.5-03` demonstration

The tool body was temporarily edited to keep the `entitled_perspective(...)` call
and then hand the resolver
`Perspective(principal_id=perspective.principal_id, role="NEGATIVE-CONTROL-FABRICATED-ROLE")`.

**Result: `2 failed, 7 passed, 29 deselected`.**

- The **2 failures** are both rows of
  `test_the_tool_forwards_the_perspective_it_resolved`.
- The **7 passes** are every row of `test_the_tool_is_never_the_weaker_path` —
  the complete parity matrix, unbothered.

Failure message, verbatim:

```
E   AssertionError: assert Perspective(p...RICATED-ROLE') == Perspective(p...='local-role')
E   AssertionError: assert Perspective(p...RICATED-ROLE') == Perspective(p...-role-second')
```

That contrast **is** the demonstration: outcome parity alone would not have
caught `DI-15.5-03` on this door. Reverted; `git status --porcelain runtime/`
clean, and `command grep -c "requested_role=None," egress.py` back to `2`.

### 2. Child resolver ignoring `subject`

`answer_for` was temporarily edited to write a constant instead of
`request.subject`.

**Result: `1 failed, 1 passed, 36 deselected`** — the `subject` row failed, the
`asked_at` row correctly still passed (only the subject was neutered).

Failure message, verbatim:

```
E   AssertionError: two calls differing only in subject returned the same content
    address; the door is not carrying the caller's question through to the resolver (D-IMPL-126)
E   assert '4d1474c9…b037' != '4d1474c9…b037'
```

Reverted; `command grep -c "NEGATIVE-CONTROL" …` returns `0` in both files.

## Acceptance criteria — measured results

### Task 1

| Criterion | Result |
| --- | --- |
| `mypy` exits 0 | **0** — `Success: no issues found in 195 source files` |
| `tools.lints --all` exits 0 | **0** |
| `pytest tests/crossproc -q` exits 0, seven governance tests unchanged | **0** — `113 passed` |
| server without new args advertises zero tools | **`TOOLS: []`** measured live and pinned by `test_a_server_built_without_the_tool_arguments_advertises_no_tool` |
| server with both args advertises exactly one tool named by the constant | **`['request_context_product']`** |
| `grep -c "requested_role=None," egress.py` == 2 | **2** (HEAD was 1 — a real delta) |
| tool signature has no `role`/`schema_name`/`schema_version`/`parameters` | asserted by `inspect.signature`; measured `{'asked_at','freshness','intent','product_class','subject','tenant','version'}` |
| `git diff $BASE..HEAD -- egress.py \| grep "^-" \| grep -v "^---"` | see below |
| `git diff --stat $BASE..HEAD -- src/` empty | **empty** |

**Filtered removal diff for `egress.py`, verbatim — 4 removed lines:**

```
-identifiers, role names, and token values are all deployment values supplied
-by the caller or carried on the wire. This module holds none of them
-(CINV-01).
-            against the principal's grant before anything is served.
```

Construct each belongs to: the first **three** are the module docstring's CINV-01
paragraph (reflowed to add *tool prose* to the list of deployment values); the
**fourth** is the closing line of the builder docstring's `perspective_resolver`
Args entry (extended to say the tool carries no `role` either). **Every removal is
in the docstring; none is in the resource handler body (`:318`–`:370`), none in
`PRODUCT_URI_TEMPLATE`, none in `ProductResolverProtocol`.** Pass condition met.

### Task 2

| Criterion | Result |
| --- | --- |
| `pytest tests/crossproc -q` exits 0 | **0** — `113 passed` |
| collected count for `test_mcp_egress.py` strictly greater than HEAD | **HEAD: 19 → now: 38** |
| `grep -c "_call_tool_in_process"` ≥ 2 | **3** (definition + 2 calls) |
| `grep -c "parametrize"` > 2 | **7** (HEAD: 2) |
| scenario ids include all seven governance scenarios | `[entitled]`, `[tokenless]`, `[unknown-token]`, `[undeclared-principal]`, `[class-unentitled]`, `[role-ungranted]`, `[policy-absent]` — all present in `--collect-only -q` |
| forwarded-perspective test non-vacuous | **recorded above** — 2 failed / 7 parity rows passed |
| two-subjects test non-vacuous | **recorded above** — 1 failed / 1 passed |
| `inputSchema` compared by equality | `set(properties) == EXPECTED_TOOL_ARGUMENTS` and `set(required) == EXPECTED_TOOL_ARGUMENTS` |
| tool-presence pin compares raw bytes, distinguished from the HEAD pin | `assert from_opened[1] == from_closed[1]` on raw text; both pins named and distinguished in the module docstring |
| `test_the_egress_module_holds_no_route_into_the_graph` passes | **passes** |
| `tests/invariants/test_mcp_role_separation.py` exits 0 | **0** |
| removal diff shows no deletion inside the seven pre-existing governance test bodies | **confirmed** |

**Filtered removal diff for `test_mcp_egress.py`, verbatim:**

```
-from collections.abc import Iterator
-from typing import Any
-from mcp.types import TextResourceContents
-from ccf_runtime.mcp.egress import build_egress_server
-    A refusal is returned rather than raised, and the *reason* is returned
-    with it. Two things make that the right shape here: an exception escaping
-    the lifespan is re-wrapped by its task group into a ``BaseExceptionGroup``
-    that says nothing about the door, and — more importantly — a refusal test
-    that only asserts "it raised" would pass against a door refusing for a
-    reason nobody intended. The returned text carries the typed
-    ``error_code``, which is the assertion worth making.
-    async def operation(session: ClientSession) -> str:
-        result = await session.read_resource(AnyUrl(uri))
-        return "".join(
-            contents.text
-            for contents in result.contents
-            if isinstance(contents, TextResourceContents)
-        )
-    def client_factory() -> httpx.AsyncClient:
-        headers = {} if token is None else {"Authorization": f"Bearer {token}"}
-        return httpx.AsyncClient(
-            transport=httpx.ASGITransport(app=app),
-            base_url=IN_PROCESS_BASE_URL,
-            headers=headers,
-        )
-            try:
-                return True, await run_with_session(
-                    url=f"{IN_PROCESS_BASE_URL}/mcp",
-                    operation=operation,
-                    http_client_factory=client_factory,
-                )
-            except McpServerUnreachable as refused:
-                return False, _flatten(refused)
```

Every removal is either an import line widened in place, or a line of
`_read_in_process`'s body factored into the shared `_client_factory` /
`_resource_operation` / `_attempt` helpers (its docstring paragraph moved to
`_attempt` verbatim). `_read_in_process`'s **contract is unchanged** — still
`(ok, text)`, `True` means served. **No deletion falls inside any of the seven
pre-existing governance test bodies.**

### Task 3

| Criterion | Result |
| --- | --- |
| `pytest tests/test_surface_drift.py tests/test_surface_completeness.py -q` exits 0 | **0** |
| `fragment_paths()` includes `16-23-mcp-product-tool.md` | **yes** — confirmed before writing the fragment (16-22's widening had landed; 61 fragments incl. `16-22-consumption-papercuts.md`) |
| every `added`/`removed`/`reshaped` name has exactly one fragment entry | **3 of mine ↔ 3 entries; equal in both directions** (see report below) |
| `parse_entries()` count for the fragment | **3** — every entry parses with all seven fields |
| `grep -c "Surface: …ProductResolverProtocol"` == 0 | **0** |
| residual (c) is a cross-reference | `D-IMPL-128` count **5**; `D-IMPL-129\|16-24` count **1**; `candidate D-IMPL\|unruled\|unowned` count **1** — reading recorded below |
| residual (a) cites `D-IMPL-128` limb 2 and carries its standing constraint | **yes**, verbatim |
| `deferred-items.md` gains three entries with owners | **yes** — (a) *unassigned by ruling*; (b) *the HW-1 plan*; (c) *plan `16-24`* |
| guarded-paths diff empty | **empty** for `.planning/ROADMAP.md`, `REQUIREMENTS.md`, `16-CONTEXT.md`, `16-RESEARCH.md`, `16-PATTERNS.md`, **every** `16-*-PLAN.md`, and `docs/DECISIONS.md` |

**`dump_surface.py --report`, verbatim:**

```
added (6):
  ccf.products.gates.PYDANTIC_MODEL_FORMS
  ccf.products.gates.ServableProductNotAModel
  ccf_runtime.http_api.errors.ERROR_ROUTE_HANDLE_ABSENT
  ccf_runtime.http_api.routes.CONTENT_ADDRESS_HEADER
  ccf_runtime.mcp.egress.NaiveAskedAtRefused
  ccf_runtime.mcp.egress.PRODUCT_REQUEST_TOOL
removed (0):
reshaped (2):
  ccf_runtime.http_api.dependencies.ApiDependencies
  ccf_runtime.mcp.egress.build_egress_server
```

Four of those six `added` and one of the two `reshaped` are plan **16-22**'s and
are claimed by `16-22-consumption-papercuts.md`. **Mine are exactly three:**
`NaiveAskedAtRefused` (added), `PRODUCT_REQUEST_TOOL` (added),
`build_egress_server` (reshaped) — and the fragment files exactly three entries.
Counts equal in both directions.

**The `candidate D-IMPL|unruled|unowned` reading, recorded as required.** The
single match is `deferred-items.md:112`:

> *"fix it in this phase."* Not unruled, not unowned, and no candidate `D-IMPL`
> id is filed for it.

That is a **denial** on the `get_context` entry, not an assertion attached to it.
The criterion is satisfied in its intended direction: nothing in that entry
claims the gap is unruled, unowned, or a candidate ruling — it names
`D-IMPL-128` limb 1 as the ruling and plan `16-24` (via `D-IMPL-129`) as the
owner.

## Phase gates

| Gate | Result |
| --- | --- |
| `make ci-core` | **exit 0** — `3154 passed, 118 skipped` (HEAD: 3135/118; +19 = the new tests) |
| `make examples` | **exit 0** — ten network-free examples, none edited |
| `make surface-changes` | **exit 0**; the `16-23` fragment orders after `15.6-*` and after `16-22` |
| `make docs-strict` | **exit 0**, including the `docs/schemas/` scan root |
| `CCF_TEST_FLUREE_URL=http://localhost:8090 make leg-fluree` | **exit 0** — `76 passed, 3196 deselected` against live Fluree 4.1.4 |
| `git diff --stat $BASE..HEAD -- src/ pyproject.toml` | **empty** |
| `tools/lints/allowlist.yaml` | **untouched** — no entry added |

## Deviations from Plan

### 1. `[Rule 3 — blocking]` `_both_surfaces_in_process` was required; two separate helper calls cannot drive one server

**Found during:** Task 2, first run of the matrix.

**Issue:** `StreamableHTTPSessionManager.run()` raises
*"can only be called once per instance"*, and `FastMCP` holds **one** manager per
server object. Entering the lifespan twice on one server — once for
`_read_in_process`, once for `_call_tool_in_process` — fails outright. All seven
matrix rows and both forwarded-perspective rows failed with that `RuntimeError`.

**Why the obvious workaround was refused:** building two servers would satisfy the
runtime and destroy the assertion. The plan's own words are *"one server, one
policy and one grant"*; a two-server matrix compares two deployments, not two
surfaces of one door.

**Fix:** `_read_in_process` and `_call_tool_in_process` were factored onto shared
`_client_factory` / `_resource_operation` / `_tool_operation` / `_attempt`
helpers, and `_both_surfaces_in_process` was added — it enters the lifespan
**once** and drives both surfaces in sequence on one credential.
`_read_in_process`'s public contract is unchanged and every pre-existing test
passes unmodified. `_call_tool_in_process` still exists and is still called
directly (tokenless test, naive-instant test), so the criterion counting it is
satisfied on real uses rather than on a vestigial definition.

**Files:** `tests/crossproc/test_mcp_egress.py`. **Commit:** `f78ce05`.

### 2. `[Rule 3 — blocking]` `tests/test_surface_shape_capture.py` was not in `files_modified` but had to be edited

**Found during:** Task 3.

**Issue:** `test_no_committed_plain_class_or_function_shape_is_disturbed` compares
the **committed live manifest** (`docs/surface/v0.2-surface.json`) against a
freshly built surface, and `build_egress_server` is a `function`-kind entry whose
shape moved. The gate failed.

**Fix:** the `_SHAPE_MOVED_BY_FRAGMENT` allowance that plan **16-22** established
for exactly this case (recorded as `D-IMPL-130`) gains one entry mapping
`ccf_runtime.mcp.egress.build_egress_server` to `16-23-mcp-product-tool.md`. The
mechanism requires the named fragment to claim the name, which it does as
`reshaped`. The alternative — regenerating the live manifest — was rejected: it
would sweep in unrelated deliberately-stale contract entries and would bypass the
claim requirement 16-22 built.

**Files:** `tests/test_surface_shape_capture.py` (9 lines). **Commit:** `e9fba97`.

### 3. `[Rule 3 — blocking]` `docs/SURFACE-CHANGES.md` regenerated

`test_the_curated_log_is_assembled_from_the_current_fragments` fails unless the
assembled log matches the fragments. `make surface-changes` is in the plan's own
verification list; the file is that command's mechanical output. **Commit:**
`e9fba97`.

### 4. `[Rule 1 — bug]` Two citation-lint corrections in my own new prose

- `product_entitlement.py:386-446` — the plan's `<interfaces>` block cites this
  range; the file has **445** lines and `cite01-resolves` failed. Corrected.
- `test_citation_coverage.py`'s **coverage ratchet** (`D-IMPL-123`) caps
  line-anchored Python citations at zero for new prose; `D-IMPL-114` ruled that
  prose cites `path.py::Symbol`. All five line-anchored citations in the new
  fragment and the new deferred-items entries were converted to symbol form
  (`product_entitlement.py::entitled_perspective`,
  `http_api/routes/product.py::build_router`,
  `mcp/experience.py::build_experience_server`). No ratchet constant was raised.

## Findings for Dave

**None requiring a ruling.** Three residuals are recorded, and all three are
already governed:

- **(a) client-chosen `subject` is not entitlement-scoped** — `D-IMPL-128`
  limb 2, **unassigned by ruling**, shipping on the measured zero delta. Its
  standing constraint is carried verbatim in both the fragment and
  `deferred-items.md`: *no plan may cite the tool's shipping as evidence that
  subject-scoping is unnecessary.* **This plan does not close `D-IMPL-128`
  limb 2 and does not propose closing it.**
- **(b) a class declaring any required request parameter is unreachable through
  either parameterised door** — attaches to `D-IMPL-113`; **owner: the HW-1
  plan**, as a design constraint on that plan. Measured against the committed
  `s1-01` contract: `reason='missing-required-parameter' key='decision_instant'`.
  HW-2 changes only the client, so HW-1's class must declare no required request
  parameters — or `decision_instant` must stop being one.
- **(c) `get_context` is authenticated but not entitled** — recorded as a
  **cross-reference**, `D-IMPL-128` limb 1 + `D-IMPL-129`, **owner plan
  `16-24`**. No candidate id filed.

One observation worth carrying forward without a ruling attached: the FastMCP
single-run session-manager constraint (deviation 1) means any future test that
wants to compare two surfaces of one MCP server must use
`_both_surfaces_in_process` or an equivalent. A plan that reaches for two
`_read_in_process`-style calls on one server will fail with a `RuntimeError` that
says nothing about doors.

## Known Stubs

None. No hardcoded empty value, placeholder string or unwired component was
introduced; the tool's every argument reaches a typed `ProductRequest`, and the
`parameters={}` mapping is a documented positive assertion (*this question needs
nothing beyond its four axes*) with its consequence recorded as residual (b)
rather than left silent.

## Threat Flags

None. The one new surface — the parameterised tool — is fully enumerated in the
plan's `<threat_model>` (T-16-23-01 through T-16-23-12 plus T-16-23-SC), and no
network endpoint, auth path, file-access pattern or schema change was introduced
beyond it. The tool returns the identical `canonical_bytes(servable.product)`
expression the resource returns, so it inherits `D-IMPL-119` limb 3(b) and
`D-IMPL-124` Shape B by construction rather than by a second serialization.

## Self-Check: PASSED

Created files verified present:

- `FOUND: docs/surface-changes/16-23-mcp-product-tool.md`
- `FOUND: .planning/phases/16-.../16-23-SUMMARY.md`

Commits verified present in `git log --oneline --all`:

- `FOUND: 2c4353a` — `feat(16-23): give the egress door an opt-in parameterised product tool`
- `FOUND: f78ce05` — `test(16-23): prove the product tool is not the door's weaker path`
- `FOUND: e9fba97` — `docs(16-23): the surface fragment and three residuals against their rulings`
