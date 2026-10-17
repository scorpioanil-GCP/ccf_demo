<!--
Copyright (c) 2026 David Castillo. All rights reserved.
Use, copying, modification, and distribution of the covered material
are governed by the CCF SDK Interim Software and Patent License
in the repository-root LICENSE.md and any controlling signed agreement.
Rights under that interim license begin only upon its execution
and are limited to its stated scope and term.
-->
# SEC-030 — unexpected failures at the MCP door: brief

**Status, 2026-10-17 01:3x MST: BUILT and verified (`D-IMPL-388`); D1 (a), as ruled.**
Proposed at 00:20 for review only. Dave's 00:44 instruction ("fix SEC-030") took D1 (a), the
fault clause only, and D2 needed no change. Built on branch `sec-030-fix`: red tests
`89528cdb`, fix `b8e19a1c`, records `38179adc`.

- **The change:** exactly §2's: `except Exception`, with `_opaque_failure` unchanged.
- **One departure, from the 00:44 instruction's preferred shape:** no fault-level re-raise of
  the three governed types was added. Raised from anywhere but the resolver, a re-raise would
  let their raw text cross.

**Verification actually performed.**
- **R1 and R2:** `tests/mcp/test_egress_unexpected_failure_is_opaque.py` gave 11 red before
  and 13 green after.
- **Breaks:** all five ran on the in-process tests, each restored from saved bytes with the
  sha checked:
  - S1 (tuple restored): 11 red;
  - S2 (`str(exc)` passed through): 11 red;
  - S3 (no log): 11 red, on the log assertion;
  - S4 (`BaseException`): the structural check alone red;
  - S5 (clause above the governed handlers): 13 red, the governed-absence controls included.

  A first S5 run whose anchor matched twice is kept as INVALID and was redone.
- **One existing test adjusted:** `test_composite_integration`'s source reading. Its
  assertions are unchanged, and a clause narrowed to `(TypeError, OSError)` still reddens it.
- **Through the bank's own `launch.sh`** (read-only estate):
  - on the unbroken fixed tree, the five cp-06C door tests passed, `verify.py` included;
  - with SEC-020's break S4 on a throwaway commit, both routes answered
    `ccf-runtime-failure:<id>`, and `logs/door.err` held the ids with the type name and no
    message text.
- **Regression on `b8e19a1c`:**
  - MCP, skills, crossproc, http_api and client: 1,860 passed;
  - products: 4,602 passed, plus the composite test after its reading was corrected (that
    test re-run alone);
  - examples: identical to `main`;
  - lint and `mypy` clean.

**Scope of the closure:** the protected MCP acquisition and resolution path — the resolver call and the answer's emission inside `_answer_question`, on the product tool and the address-form template. Entitlement failures (the step that runs before the resolver) and every other surface remain outside it: the standing product resource `ccf-product://{tenant}/{class}/{version}` (its handler has no fault clause; the standard door the bank uses does not register it, `build_egress_server` does by default), the HTTP API door, the experience and agent tools, and the HITL resources.

The text below is the proposal as reviewed, unchanged.

**Baseline:** `main` at `0746e701`. **Register:** `OPEN-SECURITY-ITEMS.md` item 17.

## 1. The finding, measured

The MCP door turns a failure into the opaque `ccf-runtime-failure:<id>` only for four
exception types. Any other exception raised while a question is answered reaches the caller
as its own message text, on both routes.

- **Where:** `runtime/ccf_runtime/mcp/egress.py::build_egress_server._answer_question`, the
  fault clause at :1418: `except (ValueError, TypeError, LookupError, OSError)`.
- **Both routes end there:**
  - the product tool, `request_context_product` (:1477, call at :1809);
  - the address-form template, `addressed_context_product` (:1837, call at :1887).

**Probe on `0746e701`.** It is estate-free and was not committed
(`ccf_saves/2026-10-17-sec030/`). The existing door harness ran over a resolver that raises
an exception carrying a marker string:

| Raised | Tool route returns | Template route returns | Door's failure log |
|---|---|---|---|
| an undeclared `Exception` subclass | `Error executing tool request_context_product: <marker>` | `Error creating resource from template: … <marker>` | **no record** |
| `RuntimeError` | the marker text | the marker text | **no record** |
| `LookupError` (control) | `…: ccf-runtime-failure:<32 hex>` | `…: ccf-runtime-failure:<32 hex>` | 1 record |

The leak loses diagnostics as well as hiding nothing. An undeclared failure leaves no
door-log entry, so an operator has nothing to join to.

**First seen** in SEC-020's deliberate break S4, on cp-06C through the bank's own door. With
the out-of-scope exception class renamed so its binding missed, the caller received
*"facility 'FAC-5B8418' is outside the requested borrower_scope; …"* on both routes.

## 2. Proposed error boundary (one file, one clause)

**Change.** In `_answer_question`, widen the fault clause to `except Exception as exc:` and
leave its body unchanged, `raise _opaque_failure(exc) from exc`. That gives both routes the
existing behavior of `_opaque_failure` (:755), which is already used for the four types:
- **To the caller:** only `ccf-runtime-failure:<id>`.
- **To the log** (`ccf_runtime.mcp.egress`): the same id, beside the type names and frames of
  the whole cause chain, and never the exception text (`_types_and_frames`, :1905; SEC-024,
  `D-IMPL-369` choice C).

**What stays exactly as it is:**
- **Governed outcomes.** `ProductNotServable`, `ErasedContentRefused` and
  `GovernedRefusalRaised` are caught by the inner clauses above the fault clause, and
  continue to become recorded governed answers. A `RefusalEnvelope` is a return value, so it
  never reaches the fault clause. Only the catch-all widens.
- **What still propagates.** Exceptions that are not `Exception` (cancellation, interrupt,
  exit) are not caught.
- **Caller-input refusals, outside the `try` by design.** These are a naive `asked_at`, the
  C-01 and C-18 cross-checks, `ProductRequest` validation, and the template's
  address-parsing errors. Their text describes only what the caller sent. The C-01 texts
  are pinned on the wire by `tests/mcp/test_egress_parameters.py`; no test pins the
  address-parsing texts.
- **Tenancy refusals.** These are raised by the tenancy guard before either handler runs,
  for example `ccf-tenant-not-granted` (`runtime/ccf_runtime/mcp/tenancy.py`).
- **Documentation.** The docstring and comments that name the fault tuple (:1245,
  :1379–1380, :1401)
  are restated: governed answers arrive as return values or through the three typed
  clauses, and anything else raised is a failure.

**Not changed:**
- the SDK resolver. An undeclared exception stays a failure, not a determination
  (`D-IMPL-347` B2, `PKG-F-03`);
- `src/`, cp-06C, the timing, and the log policy.

**Rejected:**
- **Convert undeclared acquisition exceptions into governed refusals at the SDK seam.** That
  would turn defects into "no" answers, against the ruling above.
- **A server-wide FastMCP exception handler.** It would reach every tool and resource,
  including deliberate public errors. That is a wider blast radius than this finding needs.

## 3. Tests

The tests go in a new module, `tests/mcp/test_egress_unexpected_failure_is_opaque.py`. It
is estate-free and runs in hosted CI. It reuses `_server_over` from
`test_egress_logs_carry_no_caller_values.py`, plus `_drive_mcp`, `_tool_arguments` and
`_tool_operation` from `test_egress_parameters.py`. It adds one template operation that
returns an `McpError`'s text instead of raising it.

**Red first.** On `0746e701` each test fails on an assertion; the probe above measured it.

- **R1, the opaque response, on both routes.** The cases run on each route:
  - an undeclared `Exception` subclass;
  - `RuntimeError`;
  - `AssertionError`;
  - `httpx.HTTPStatusError`, whose text names a URL;
  - a chain: `RuntimeError` raised from `KeyError`.

  What the caller receives, after FastMCP's own prefix, matches
  `^ccf-runtime-failure:[0-9a-f]{32}$`. The marker appears nowhere on the wire.
- **R2, internal diagnostics are preserved.**
  - There is exactly one `ccf_runtime.mcp.egress` record per failure.
  - **Same id:** the id on the wire equals the id in that record.
  - **Content:** the record names the raised type and every type in its chain, and a frame
    from the raising function.
  - **No marker:** the marker is in no log record, FastMCP's own included.

**Controls, green before and after.** Each is held by tests that exist today.

| Control | What stays true | Held by |
|---|---|---|
| C1 | The four types stay opaque, and their logs stay types and frames only. | `test_the_opaque_failure_log_renders_types_and_frames_not_exception_text` |
| C2 | Governed outcomes stay governed answers with `isError` false: a returned refusal, a governed absence, an erasure, a raised governed refusal. | `tests/mcp/test_egress_refusal_channels.py`, `tests/mcp/test_fw3_erasure_at_mcp_doors.py`, `tests/products/test_d_impl_304_governed_refusal_raised.py` |
| C3 | Caller-input refusals keep their wire text. | `tests/mcp/test_egress_parameters.py` (the C-01 texts) |
| C4 | A tenant the grant does not carry is still refused with `ccf-tenant-not-granted`, before the handler runs. | `tests/mcp/test_tenant_guard.py`, and `verify.py`'s line for it |
| C5 (new, structural) | The fault clause names `Exception`: not `BaseException`, and not a bare `except`. | the new module |

**Deliberate breaks.**
- Each runs on a throwaway worktree, never pushed, under `python -B`.
- An error at setup is invalid and is redone.

| Break | What it does | What must go red |
|---|---|---|
| S1 | Restores the four-type tuple. | R1 and R2 |
| S2 | Catches `Exception` but raises `ToolError(str(exc))`. | R1 (the marker reaches the wire) and R2 (no record) |
| S3 | Catches `Exception` and returns an id but writes no log. | R2 alone |
| S4 | Catches `BaseException`. | C5 |
| S5 | Moves the fault clause above the governed clauses. | C2 |

**One integration check** (read-only estate, through the bank's own `launch.sh`). This
reuses SEC-020's break S4 on cp-06C, with the out-of-scope class renamed so its binding
misses, now on top of the fix:
- **Wire:** both routes answer `ccf-runtime-failure:<id>` with no facility text.
- **Log:** `logs/door.err` holds that id and the type name `FacilityOutsideTheRequestedScope`,
  and no message text.
- **Evidence:** the question's pending marker remains, so `serve.py decisions` reports one
  decision that began and never finished.
- **No regression:** on the unbroken fixed tree, the cp-06C bank-door tests (5) and
  `verify.py` (21 of 21) stay green.

## 4. What it does not do

- **A failure stays distinguishable from a governed "no".** It now reads
  `ccf-runtime-failure:<id>`, by design: a failure is a defect, not an answer. The existence
  cases in cp-06C are declared refusals (SEC-020); this repair closes the text leak, not that
  difference.
- **Not examined:** other surfaces, namely the HTTP API door, the experience and agent tools,
  and the HITL resources. Dave ruled out a broader investigation in this round.
- **The entitlement step, unless D1 (b) is chosen.** `govern_entitlement` and
  `govern_scope_denial` run before the `try`, so an unexpected error there still crosses as
  text.

## 5. Bounded verification and cost

- **Red first, then green.** R1 and R2 are red on `0746e701` and green after; the five
  controls stay green; the five breaks go red as stated.
- **Then, all run directly:**
  - `tests/mcp`;
  - the product tests that touch the door;
  - the one integration check;
  - `tools/lints/tests`;
  - `mypy`.
- **Cost: $0.** No paid CI, no wheel, and no change to the sealed delivery.

## 6. Decisions for Dave

**D1. How wide the boundary is.**
- **(a) Recommended: the fault clause only.** That is the closed SEC-030 finding: everything
  the resolver raises, acquisition included, plus the emission.
- **(b) Also move the entitlement and scope-denial step inside the same `try`.** This closes
  the adjacent gap: an unexpected error in governance or its recorder.
  - It must re-raise `UnverifiedProductCallerRefused` unchanged, so its deliberate text
    survives.
  - It needs one more red test and one more control.

**D2. The cp-06C hardening the SEC-020 review suggested** (advisory A2: subclass
`FacilityOutsideRequestedScope` from `LookupError`). **Recommended: no.** The boundary
makes it unnecessary, and cp-06C stays as measured.
