---
phase: 16-documentation-rewrite-the-deterministic-path-the-adoption-ar
plan: 22
subsystem: fabric-consumption-ergonomics
tags: [D-IMPL-126, surface-gates, http-api, products, papercuts]
requires: [D-IMPL-126, D-IMPL-96, D-IMPL-84, D-IMPL-98, D-IMPL-26, D-IMPL-122]
provides:
  - ProductRequestContract.from_declared
  - ccf.products.gates.PYDANTIC_MODEL_FORMS
  - ccf.products.gates.ServableProductNotAModel
  - ccf_runtime.http_api.errors.ERROR_ROUTE_HANDLE_ABSENT
  - ccf_runtime.http_api.routes.CONTENT_ADDRESS_HEADER
  - "the surface-change glob and plan-number regex, widened past Phase 15"
affects: [16-23, 16-24, 16-05]
tech-stack:
  added: []
  patterns: [dual-channel-__getattr__, TypeVar-narrowing-helper, positive-read-gate-proof]
key-files:
  created:
    - tests/http_api/test_optional_handles.py
    - tests/http_api/test_content_address_header.py
    - docs/surface-changes/16-22-consumption-papercuts.md
  modified:
    - src/ccf/products/request.py
    - src/ccf/products/gates.py
    - runtime/ccf_runtime/http_api/dependencies.py
    - runtime/ccf_runtime/http_api/errors.py
    - runtime/ccf_runtime/http_api/routes/__init__.py
    - runtime/ccf_runtime/http_api/routes/workflow.py
    - runtime/ccf_runtime/http_api/routes/skill.py
    - runtime/ccf_runtime/http_api/routes/hitl.py
    - tools/assemble_surface_changes.py
    - tests/test_surface_drift.py
    - tests/test_surface_shape_capture.py
    - tests/products/test_request_contract.py
    - tests/products/test_gate_independence.py
    - docs/SURFACE-CHANGES.md
    - .planning/REQUIREMENTS.md
decisions:
  - "from_declared taken over a manifest-loader suffix branch (D-IMPL-84 reserves exactly `ccf.`); rejection recorded in the METHOD docstring, not the module docstring, so no schema regeneration is owed"
  - "ServableProductNotAModel derives from BOTH GateBypassError and AttributeError, because GateBypassError subclasses TypeError and hasattr would otherwise raise"
  - "X-CCF-Content-Address taken; ETag rejected in writing and both not shipped"
  - "The surface-change glob widened to `[0-9]*-*.md` and _PLAN_NUMBER de-anchored, proved by a positive read rather than a green build"
metrics:
  tasks: 3
  commits: 5
  duration: one session
  completed: 2026-08-14
requirements: [DOCS-19]
---

# Phase 16 Plan 22: Consumption Papercuts Summary

The four `D-IMPL-126` papercuts are closed in the fabric before any Hello World
example is written, and the surface-change machinery — which was blind to every
`16-*` fragment — can now read this phase.

## BASE, verbatim

```
b62e3e275b65f2cbec7eca6d47f6d8d6c1abb3ed
```

Captured before the first edit. Every scope guard below is
`git diff --stat $BASE..HEAD -- <path>`; the bare `git diff -- <path>` form was
not used anywhere, because all three tasks commit and it is empty for every path
once they have.

## Commits

| SHA | Message |
| --- | --- |
| `9a4b59c` | `test(16-22): RED for the two src/ccf/products/ consumption papercuts` |
| `dfa4f92` | `feat(16-22): reach a request contract, and say why a product is unconstructible` |
| `fd6aa6e` | `test(16-22): RED for the partially-wired ApiDependencies bundle` |
| `8cf6c6e` | `feat(16-22): ApiDependencies stops demanding eight handles to serve one product` |
| `5d6bf34` | `feat(16-22): the content address travels; the surface gates learn to read Phase 16` |

## Task 1 — `from_declared`, and why `ServableProduct` is unconstructible

`dfa4f92` (RED at `9a4b59c`).

**`ProductRequestContract.from_declared(artifact)`** reads the document's own
`semver` lane plus the three declaration keys off the `DeclaredArtifact` a
manifest returns. Missing keys are named **all at once** in one `ValueError`.
The `DeclaredArtifact` annotation is under `if TYPE_CHECKING:` — the circular
import was a certainty, not a risk, since `artifacts.py:100` already imports
`NO_REQUEST_CONTRACT` from `request.py` — and the plain `ValueError` branch was
taken over a function-local `ArtifactLoadError` import. Both rejected shapes
(the `*.request-contract` suffix branch and registering
`PRODUCT_REQUEST_CONTRACT` in `SDK_VERSIONED_ARTIFACT_CLASSES`) are recorded in
the **method** docstring.

**`ServableProduct`** refuses all thirteen spellings in the new public
`PYDANTIC_MODEL_FORMS` frozenset on **both** attribute channels — a metaclass
`__getattr__` for the class channel and a `__getattr__` on the class itself for
the instance channel, since `model_copy`, `model_dump` and `parse_obj` are
instance methods and are the beginner spelling. `ServableProductNotAModel`
derives from both `GateBypassError` and `AttributeError`.

**Measured results:**

| Criterion | Result |
| --- | --- |
| `pytest tests/products/test_request_contract.py tests/products/test_gate_independence.py -q` | exit 0 — **112 passed** (HEAD baseline: **58**) |
| `import ccf.products.request, ccf.controlplane.artifacts` | exit 0 |
| `import ccf.controlplane.artifacts, ccf.products.request` | exit 0 |
| class channel `ServableProduct.model_construct()` | non-zero; stderr carries `run_gates` and `INV-CH7-52` |
| instance channel `.model_copy()` | non-zero; stderr carries `run_gates` and `INV-CH7-52` |
| `hasattr(ServableProduct,'model_construct') is False` | exit 0 |
| negative control, both channels | plain `AttributeError`, `INV-CH7-52` absent |
| `command grep -rn "request-contract" src/ccf/deployment/classes.py` | exit 1 (no output) — loader shape not taken |
| `git diff --stat $BASE..HEAD -- examples/` | empty |
| `mypy` | exit 0, 195 files |

## Task 2 — `ApiDependencies` stops demanding eight handles

`8cf6c6e` (RED at `fd6aa6e`).

Five handles typed `X | None` with `None` defaults; `control_plane`,
`artifact_store` and `product_resolver` stay required. The falsified module
docstring is rewritten and the fail-at-boot-to-fail-at-call posture change is
stated with its mitigation. One private `_required_handle` narrows all eleven
sites through a `TypeVar`, bound once per handler body.

| Criterion | Result |
| --- | --- |
| `pytest tests/http_api -q` | exit 0 — 110 passed |
| `pytest tests/cli tests/hitl tests/crossproc/test_mcp_tenant_authz.py -q` | exit 0 — 211 passed |
| `tools/dump_openapi.py` | exit 0 |
| `mypy` | exit 0 — **the proof the narrowing reached every site** |
| `grep -c _required_handle .../workflow.py` | **4** (≥2 required) |
| `grep -c _required_handle .../skill.py` | **5** (≥2) |
| `grep -c _required_handle .../hitl.py` | **3** (≥2) |
| `grep -c ERROR_ROUTE_HANDLE_ABSENT .../errors.py` | **2** |
| `grep -c "no default for anything" .../dependencies.py` | **0** (was 1 at HEAD) |
| three-handle construction one-liner | exit 0 |
| `git diff --stat $BASE..HEAD -- .../app.py` | empty |

## Task 3 — the header, the glob widening, the requirement rows

`5d6bf34`.

### The glob-widening positive read — actual output

`16-23` and `16-24` depend on this. Both halves were run and their real output
is reproduced verbatim:

```
$ PYTHONPATH=src:runtime .venv/bin/python -c "from tools.assemble_surface_changes import fragment_paths; ..."
POSITIVE READ fragment_paths OK; last 3: ['15.6-12-single-agent-review-fixes.md', '15.6-13-source-refresh-window.md', '16-22-consumption-papercuts.md']
total fragments: 61
proof-1 exit=0

$ PYTHONPATH=src:runtime .venv/bin/python -c "from test_surface_drift import _fragment_text; ..."
POSITIVE READ _fragment_text OK; found: '- Surface: ccf_runtime.http_api.errors.ERROR_ROUTE_HANDLE_ABSENT'
fragment text chars: 754115
proof-2 exit=0
```

`16-22` sorts **after** `15.6-13`, which is the ordering the widened `major`
group buys. Both assertions are also standing tests
(`test_a_phase_16_fragment_is_actually_read`,
`test_the_fragment_globs_are_not_phase_anchored`), so a future re-anchoring of
either glob fails.

### `dump_surface.py --report`, recorded verbatim

```
added (4):
  ccf.products.gates.PYDANTIC_MODEL_FORMS
  ccf.products.gates.ServableProductNotAModel
  ccf_runtime.http_api.errors.ERROR_ROUTE_HANDLE_ABSENT
  ccf_runtime.http_api.routes.CONTENT_ADDRESS_HEADER
removed (0):
reshaped (1):
  ccf_runtime.http_api.dependencies.ApiDependencies
```

Reconciled in **both** directions: 5 names moved, and `parse_entries()` finds
exactly **5** entries in `16-22-consumption-papercuts.md`, name-for-name and
direction-for-direction. The frozen-baseline diff agrees (245 added / 0 removed
/ 55 reshaped, up from 241/0/54, with the same five names).

`from_declared` is deliberately **not** claimed as an entry: it is an ordinary
method and `D-IMPL-122` left the manifest blind to method sets. That blindness
is recorded as prose in the fragment rather than papered over.

| Criterion | Result |
| --- | --- |
| `pytest .../test_content_address_header.py .../test_surface_drift.py .../test_surface_completeness.py -q` | exit 0 |
| `pytest tests/ -q -k "surface"` | exit 0 — 90 passed |
| `grep -c '"15*-*.md"' tools/assemble_surface_changes.py` | 0 |
| `grep -c '"15*-*.md"' tests/test_surface_drift.py` | 0 |
| `grep -c "response.content" .../test_content_address_header.py` | 5 |
| `grep -c "response.json()" .../test_content_address_header.py` | 0 |
| `grep -rn "ETag" runtime/ccf_runtime/http_api/` | prose only, inside `canonical_response`'s docstring (plus its `.pyc`); asserted by test that no header is set under that name |
| `grep -rn "X-CCF-Content-Address" runtime/ccf_runtime/mcp/` | exit 1 (no output) — MCP untouched |
| `grep -c "DOCS-19\|DOCS-20\|DOCS-21" .planning/REQUIREMENTS.md` | **6** |
| `make surface-changes` | exit 0; `16-*` orders after `15.6-*` in both the Added and Reshaped sections |

**The negative control exists and was read**:
`test_a_refusal_carries_no_content_address` drives the product route with no
credential and asserts `CONTENT_ADDRESS_HEADER not in response.headers`. Without
it the suite would pass against middleware stamping every response.

## Gate results

| Gate | Result |
| --- | --- |
| `make ci-core` | **exit 0** — 3135 passed, 118 skipped |
| `make examples` | **exit 0** |
| `make docs-strict` | **exit 0** |
| `make surface-changes` | **exit 0** |
| `python -m tools.lints --all` | **exit 0** |
| `mypy` (`src` + `runtime`, strict) | **exit 0** — 195 files |
| `CCF_TEST_FLUREE_URL=http://localhost:8090 make leg-fluree` | **exit 0** — 76 passed |
| `pytest tools/ -q` | exit 1 — **2 pre-existing failures**, see below |

## Scope guards, all run as `$BASE..HEAD`

Every one empty: `examples/`, `pyproject.toml`, `docs/DECISIONS.md`,
`.planning/ROADMAP.md`, `runtime/ccf_runtime/http_api/app.py`,
`tools/lints/allowlist.yaml`, `.planning/phases/16-*/16-CONTEXT.md`,
`16-RESEARCH.md`, `16-PATTERNS.md`, and every `16-0*`/`16-1*`/`16-2*-PLAN.md`.
`docs/surface/` is untouched — the live manifest was **not** regenerated.

## Deviations from Plan

### `[Rule 3 — blocking]` `tests/test_surface_shape_capture.py` forbade any class-shape move

**Found during:** Task 3, `pytest -k surface`.
**Issue:** `test_no_committed_plain_class_or_function_shape_is_disturbed`
asserts that **no** `class`- or `function`-kind entry in the committed manifest
may read differently from live. Its audit claim — *"the shapes that moved moved
because the tool can now see them, not because anything about them changed"* —
was written inside Phase 15.6, where no plan was permitted to reshape a
signature. `D-IMPL-96` revoked that wording for Phase 16 *"precisely so Phase 16
could repair defects it finds"*, and `ApiDependencies` is the first repair to
move a plain class's `__init__`. The file is not in the plan's `files_modified`.
**Fix:** amended in reach, not withdrawn — a named `_SHAPE_MOVED_BY_FRAGMENT`
mapping, in the spirit of the module's existing narrow-and-named `contract`-kind
exclusion. It is not a mute list: the test now requires each entry's cited
fragment to exist **and** to claim the name, and `test_surface_completeness.py`
independently requires a matching `reshaped` entry. Every *unlisted* shape must
still read identically.
**Commit:** `5d6bf34`.

### `[Rule 3 — blocking]` line-anchored citations violate `D-IMPL-114`

**Found during:** Task 3, `make ci-core`.
**Issue:** `tests/invariants/test_citation_coverage.py` ratchets unanchored
citations to a ceiling of 0. Six new `path.py:LINE` citations in this plan's
docstrings and comments, plus one in the fragment, tripped it.
**Fix:** converted to the `path.py::Symbol` form `D-IMPL-114` ruled —
`deployment.py::read`, `experience.py::build_experience_server`,
`product.py::build_router`. No constant was raised; nothing was allowlisted.
**Commit:** `5d6bf34`.

### `[Rule 3 — blocking]` `docs/SURFACE-CHANGES.md` regeneration

**Found during:** Task 3.
**Issue:** `test_the_curated_log_is_assembled_from_the_current_fragments`
requires the assembled log to match the fragments. Filing a new fragment makes
it stale. The file is not in `files_modified`.
**Fix:** `make surface-changes`, committed alongside the fragment.
**Commit:** `5d6bf34`.

### `[minor]` two prose rewordings to satisfy criteria exactly as written

`grep -c "response.json()"` must be 0; the literal appeared only in two prose
sentences describing what the test does *not* do. Reworded rather than the
criterion weakened — the intent (no assertion parses the body) was already met
and remains met. Likewise `test_the_fragment_globs_are_not_phase_anchored`
builds its forbidden needle from parts, because a source scan whose own scanner
trips it can only ever fail.

## Findings that are not this plan's to fix

**Two `tools/` test failures are pre-existing residuals** under
`DI-15.6-01(a)`, confirmed not caused by this plan:

- `tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current`
  — the stale report is about rows in `examples/`, `tests/examples/` and
  `public/`; `git diff --stat $BASE..HEAD` over all three is **empty**.
- `tools/publish_scan_tests/test_docstring_leaks.py::test_no_docstring_reproduces_whitepaper_body_text`
  — names five **module** docstrings including `src/ccf/products/request.py`.
  This plan's first hunk in that file starts at line 96; the module docstring
  ends at line 93 and is byte-untouched.

`tools/` is outside `testpaths` and outside `LINTED_TREES`, so neither is in
`make ci-core`.

**A third fragment reader exists and needed no change.**
`tests/deployment/test_class_lookup.py::_fragment_public_added` already globbed
`*.md` rather than `15*-*.md`. It is named in the fragment so a later
contributor auditing this seam finds all three readers at once. It did fail
transiently between Task 1's GREEN and Task 3, because the two names Task 1 added
were unclaimed until the fragment was written; it is green now.

## For Dave's ruling rather than mine

1. **`tests/test_surface_shape_capture.py`'s allowance.** I amended a Phase 15.6
   audit claim rather than stopping, on the reading that `D-IMPL-96` already
   revoked its premise for Phase 16 and that the amendment preserves the claim
   for every unlisted name. If the preferred disposition is a `D-IMPL` entry
   recording the amendment explicitly, that entry is not written — this plan
   does not edit `docs/DECISIONS.md`.
2. **`PYDANTIC_MODEL_FORMS` is public.** The plan asked for "one module-level
   greppable frozenset" without ruling on export. I exported it, which costs one
   surface entry and buys a non-vacuous parametrized test plus a machine-readable
   statement of what the type is not. A private spelling is a one-line change.
3. **The two `tools/` residuals** are carried, per the standing instruction not
   to fix them.

## Known Stubs

None.

## Threat Flags

None. No new network endpoint, auth path, file-access pattern or schema at a
trust boundary. `X-CCF-Content-Address` discloses only `sha256` of bytes the
caller already holds in full (T-16-22-01), and the negative control asserts
refusals carry none.

## Self-Check: PASSED

Files verified present: all three created files and all fifteen modified files.
Commits verified present in `git log`: `9a4b59c`, `dfa4f92`, `fd6aa6e`,
`8cf6c6e`, `5d6bf34`.
