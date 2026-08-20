---
phase: 19-the-client-seam-integrity-checks-must-be-able-to-fail-insert
plan: 06
subsystem: http door / response siblings / request echo
tags: [http-api, request-echo, sibling-header, C-09, C-10, C-18, D-IMPL-126, D-IMPL-38]
requires:
  - "ccf.products.door.WireRequest (moved to door.py by 19-01)"
  - "ccf.contracts.canonical.canonical_bytes"
  - "ccf_runtime.http_api.routes.canonical_response"
provides:
  - "ccf_runtime.http_api.routes.REQUEST_ECHO_HEADER — the third X-CCF-* sibling"
  - "canonical_response's keyword-only `asked: WireRequest | None = None`"
  - "The product route's producer-side echo, and its absence when no question was posed"
affects:
  - "19-07 (corrective prose; two docstrings this plan made true are named below)"
  - "19-08 (the D-IMPL entry for C-09, plus one deferred error-code question)"
tech-stack:
  added: []
  patterns:
    - "extend a ruling rather than amend it — the same sibling values through whatever channel a surface has"
    - "a sibling that is absent, never empty, when the fact it names does not exist"
    - "refuse a question that cannot be represented rather than publish a sibling that silently disappears"
    - "pair every absence assertion with a control, because an absence check passes for the right and the wrong reason indistinguishably"
key-files:
  created:
    - "docs/surface-changes/19-06-the-http-door-publishes-the-question.md"
  modified:
    - "runtime/ccf_runtime/http_api/routes/__init__.py"
    - "runtime/ccf_runtime/http_api/routes/product.py"
    - "tests/http_api/test_content_address_header.py"
    - "tests/http_api/test_routes.py"
    - "docs/SURFACE-CHANGES.md"
decisions:
  - "The measurement said proceed with the default shape: the two doors ALREADY disagreed on a float, invisibly, because PARAMETER_CASES contains no float case — so refusing at the HTTP door narrows into agreement rather than breaking assert_same_verdicts"
  - "A naive asked_at is refused too, which the plan did not anticipate: building the echo forces it, and until now the HTTP door served it 200 while WireRequest's own docstring claimed both doors refuse it by name"
  - "ERROR_PRODUCT_REQUEST_INCOMPLETE carries the naive-instant refusal because errors.py is outside this plan's file set; the dedicated code is flagged for 19-08 rather than invented here"
metrics:
  duration: "~2h"
  tasks: 2
  commits: 5
  collected_delta: "3935 -> 3942 passed (+7)"
  completed: 2026-08-20
---

# Phase 19 Plan 06: The HTTP Door Publishes the Question It Was Asked — Summary

Gave the HTTP product door the sibling the envelope-carrying doors gained in
`19-01` — the question it parsed — through the channel this door actually has,
so three `X-CCF-*` siblings stand where there were two, absent rather than
empty when the caller posed no question.

## What Was Built

**A third sibling constant.** `REQUEST_ECHO_HEADER = "X-CCF-Request-Echo"`,
declared beside the other two with a `#:` comment in `REPLAY_REF_HEADER`'s
exact form. It says four things and no more: what it publishes; that it is a
sibling of the vessel on the identical argument, and that the four
`X-CCF-*`-over-`ETag` reasons **apply unchanged and are not restated**; why
base64url rather than canonical JSON verbatim; and that it is set only when
there was a question, with its absence meaningful.

**`canonical_response` can publish it.** A keyword-only
`asked: WireRequest | None = None` after `replay_ref`, stamped when not `None`.
The four non-product call sites pass nothing and are untouched. `body` is still
one `canonical_bytes` call over `payload` — the echo is an independent
serialization of a **different object**, which is what `REPLAY_REF_HEADER`
already is.

**The route states what it parsed.** `retrieve` builds the echo from `_asked`'s
own return and the path segment it had already resolved, so every field
originates producer-side, and passes `None` when `_asked` returned `None`.

**A consequence the plan asked to be measured, and it went the plan's way.**
A question `WireRequest` cannot represent is refused with a `400` carrying the
guard's own message, rather than a `500` or a served answer with a silently
missing sibling — the pattern `C-10` names.

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | `REQUEST_ECHO_HEADER` and `canonical_response`'s third sibling | `21ae323` | `routes/__init__.py` |
| 2 (RED) | Failing legs, both presence and absence | `56ef4c8` | `test_content_address_header.py`, `test_routes.py` |
| 2 (GREEN) | The route publishes the question, and nothing when there was none | `bf88f69` | `routes/product.py`, `test_content_address_header.py` |
| — | Surface fragment + log reassembly (Rule 3) | `00ec7f8` | `docs/surface-changes/19-06-*.md`, `docs/SURFACE-CHANGES.md` |
| — | Keep the echo call site on one line (declared key link) | `0a7b466` | `routes/product.py` |

## The Measurement the Plan Required Before Any Branch Was Written

The plan instructed: measure a float parameter against the current tree, read
`assert_same_verdicts`' case table, then decide the shape and record why. All
three measurements were taken in throwaway scaffolds created and deleted
inside the tree; `git status --short` was clean immediately after, and no
tracked source file was edited and reverted.

### M1 — the HTTP door, float parameter, current tree

```
FLOAT MEASUREMENT status: 200
FLOAT MEASUREMENT resolver saw parameters: {'x': 1.5}
FLOAT MEASUREMENT parameter types: {'x': 'float'}
```

Served. The float reached the resolver as a Python `float`, forwarded verbatim.

### M2 — the MCP door, same value, current tree

The float is **unrepresentable at the caller**: the module's own
`_tool_arguments` helper cannot build the call, because it constructs a
`WireRequest` first.

```
E  pydantic_core._pydantic_core.ValidationError: 1 validation error for WireRequest
E  parameters
E    Value error, parameters.minimum_score is a `float`, which does not survive
E    the wire unchanged — canonical JSON renders it as text, so the decoded echo
E    would differ from what was sent ...
```

And a hand-crafted encoded request carrying a float is refused **at the door**:

```
DOOR REFUSED: ValidationError
parameters.x is a `float`, which does not survive the wire unchanged ...
```

So the MCP verdict is `REFUSED_AT_DOOR`; the HTTP verdict was `SERVED`.

### M3 — the `assert_same_verdicts` reading

`PARAMETER_CASES` is six rows and **contains no float case**:

```python
PARAMETER_CASES = (
    {REQUIRED_PARAMETER: 11},
    {REQUIRED_PARAMETER: 11, OPTIONAL_PARAMETER: "north"},
    {},
    {REQUIRED_PARAMETER: 11, UNDECLARED_PARAMETER: "smuggled"},
    {REQUIRED_PARAMETER: "11"},
    EXPLICIT_NULL,
)
```

**So the two doors already disagreed on a float, today, and nothing was red.**
The shared width table is blind to it, and
`test_neither_door_is_wider_than_the_other` passes with the divergence live.

### The shape chosen, and why

**The plan's default: refuse with a `400`.** It cannot break
`assert_same_verdicts`, because that table never sees a float; and it moves
the HTTP door into *agreement* with the MCP door rather than widening the MCP
door to match. That is the same narrowing direction `D-IMPL-151` finding `B2`
already chose for this pair — the MCP tool narrowed to the HTTP route then;
the HTTP route narrows to the MCP tool now. `D-08` decides it: the fabric
never silently degrades a caller's value.

`tests/mcp` is green after the change (150 passed over
`tests/http_api tests/mcp`), so no divergence had to be reported.

### M4 — a fourth measurement the plan did not ask for, and it changed the work

Building the echo trips on a **second** `WireRequest` guard, not only the
parameter one. Measured on the current tree:

```
NAIVE ASKED_AT status: 200
```

A naive `asked_at` was **served**. `WireRequest._temporal_boundary_survives_the_wire`'s
own docstring states that *"both product doors refuse a naive `asked_at` by
name"* — and that sentence was **false of this door**. Left unhandled, the echo
would have turned a served `200` into an opaque `500`, which is worse than
either. So it is refused too, and the shipped claim becomes true.

## The Sabotage Controls — Every One Observed Red

Run against a scratch copy of `src` and `runtime` at
`/tmp/.../scratchpad/sabotage`, **outside the tree**, per the standing hazard.
`git status --short` after each showed only this plan's intended edits.

### The RED gate itself (commit `56ef4c8`)

`3 failed, 39 passed`:

| Leg | Observed |
|-----|----------|
| `test_the_door_publishes_the_question_it_was_asked` | `KeyError: 'X-CCF-Request-Echo'` |
| `test_the_echo_comparison_fails_against_a_different_question` | same `KeyError` |
| `test_the_absence_assertion_fails_when_a_question_was_posed` | `Failed: DID NOT RAISE AssertionError` |

**The absence assertion itself PASSED at RED, vacuously**, because the route
never stamped the header at all. That is exactly the phase's thesis observed in
miniature: an absence check passes for the right reason and the wrong reason
indistinguishably, and only its control tells them apart.

### Sabotage 1 — echo a *projection* of the question

Patched `_echo` to send `parameters={}`:

```
E  assert WireRequest(p...fo=TzInfo(0))) == WireRequest(p...timezone.utc))
FAILED ...::test_the_door_publishes_the_question_it_was_asked
1 failed, 41 passed
```

An equality failure, **not** a `KeyError` — so the round trip is a total
comparison (`C-03`) rather than a presence check.

### Sabotage 2 — manufacture a question when none was posed

Patched `retrieve` to stamp the header unconditionally:

```
E  AssertionError: assert 'X-CCF-Request-Echo' not in Headers({...,
   'x-ccf-request-e...N1cmUtc3VtbWFyeSIsInRlbXBvcmFsX2JvdW5kYXJ5IjpudWxsfQ==', ...})
FAILED ...::test_a_caller_who_posed_no_question_gets_no_echo_header
1 failed, 41 passed
```

**Both legs of the "absent when no question was posed" clause are therefore
observed**: present when asked (the leg above), absent when not (this one).

### Sabotage 3 — a door that coerces rather than refuses

Patched `_echo` to stringify floats and stamp UTC on a naive instant — `D-08`'s
forbidden behaviour:

```
E  assert 200 == 400
FAILED ...::test_a_parameter_that_cannot_cross_the_wire_is_refused_by_name
FAILED ...::test_a_naive_asked_at_is_refused_rather_than_answered
2 failed, 8 passed
```

### Sabotage 4 — a door that refuses everything

Patched `_echo` to build an always-unrepresentable question:

```
E   +  where 400 = <Response [400 Bad Request]>.status_code
FAILED ...::test_the_door_publishes_the_question_it_was_asked
FAILED ...::test_the_echo_comparison_fails_against_a_different_question
FAILED ...::test_the_representable_form_of_both_still_serves
3 failed, 7 passed
```

Note which legs stayed **green** here: both refusal legs. They pass against a
door that refuses everything, which is precisely why the vacuity guard
`test_the_representable_form_of_both_still_serves` exists — and it is the leg
that goes red.

## The Collected-Count Delta, and What Each Increment Holds

Baseline at plan start (`8020d67`): **3935 passed / 118 skipped / 0 failed**.
After: **3942 passed / 118 skipped / 0 failed**. Delta **+7**, decomposing
exactly:

| Module | Before | After | Δ |
|--------|--------|-------|---|
| `tests/http_api/test_content_address_header.py` | 5 | 10 | **+5** |
| `tests/http_api/test_routes.py` | 33 | 35 | **+2** |

**The five in `test_content_address_header.py`, each named against `C-09`:**

| # | Test | Property |
|---|------|----------|
| 1 | `..._door_publishes_the_question_it_was_asked` | `C-09` — the echo is the whole question, producer-sourced |
| 2 | `..._echo_comparison_fails_against_a_different_question` | its **named sabotage control** (`CLNT-12`, `D-22`) |
| 3 | `..._parameter_that_cannot_cross_the_wire_is_refused_by_name` | `C-10` — no silently-vanishing sibling; `D-08` |
| 4 | `..._naive_asked_at_is_refused_rather_than_answered` | `D-IMPL-38`, making `WireRequest`'s claim true |
| 5 | `..._representable_form_of_both_still_serves` | the **vacuity guard** for 3 and 4 |

**The two in `test_routes.py`:**

| # | Test | Property |
|---|------|----------|
| 6 | `..._caller_who_posed_no_question_gets_no_echo_header` | `C-09` absence, asserted as `not in`, never `== ""` |
| 7 | `..._absence_assertion_fails_when_a_question_was_posed` | its **named sabotage control** — the load-bearing half |

`test_routes.py` needed a module-local governed app: the fixture's `app` is
deliberately **ungoverned**, so the product door refuses there and never
reaches `canonical_response`. That is the same shape
`test_content_address_header.py` and `test_product_entitlement.py` each already
build for the same reason.

## Verification

| Step | Result |
|------|--------|
| `pytest tests/http_api tests/mcp` | **150 passed, 0 failed** |
| `pytest tests/http_api` | 122 passed |
| `make typecheck` | **exit 0** — 211 source files |
| `make lint` | **exit 0** |
| `make ci-core` | **exit 0** — 3942 passed / 118 skipped / **0 failed**; 400 conformance/parity; 154 gate-tools |
| `tests/invariants/test_citation_coverage.py` | passed without intervention — the new prose cites symbols, not line ranges |

**Source assertions, all met:**

| Assertion | Required | Measured |
|-----------|----------|----------|
| `grep -c "canonical_bytes(payload)" routes/__init__.py` | **1** | **1** |
| `grep -c "REQUEST_ECHO_HEADER" routes/__init__.py` | ≥ 2 | **4** |
| `grep -c "asked=" routes/product.py` | ≥ 1 | 1 |
| `grep -c "canonical_response(.*asked=" routes/product.py` | ≥ 1 (declared key link) | 1 |
| `grep -c "not in .*headers" tests/http_api/test_routes.py` | +1 or more | 0 → **1** |
| `grep -c 'REQUEST_ECHO_HEADER\].*== ""'` over both test modules | 0 | **0** and **0** |
| `grep -c "X-CCF" openapi.json` | **0**, unchanged | **0** before and after |

**The `canonical_bytes(payload)` count needed one correction to stay a
measurement.** The first draft of the new `Args:` prose contained the literal
string `canonical_bytes(payload)`, which pushed the grep to **2** — a count
defeated by prose rather than by a second call. The sentence was reworded to
``canonical_bytes`` call over ``payload``, and the grep is 1 again. Recording
it because a source assertion a docstring can satisfy is not an assertion.

**`D-IMPL-126`'s block is byte-identical.** `git diff -U0` reports hunks at
`-131 +162,6` (the signature) and `+244,32` (the new `Args:` entry) and
**nothing between them** — so every line of the four `ETag` reasons, the
*"each surface publishes the same sibling values"* sentence and the
five-call-site enumeration is unchanged. The enumeration was re-read and
re-counted against the tree: five call sites, and all four cited line numbers
(`agent.py:74`, `config.py:98`, `replay.py:47`, `replay.py:65`) still resolve.
No correction was owed.

**`grep -c "X-CCF" openapi.json` returns 0 and no `make openapi` ran.** The
precedent was measured, not assumed: neither existing sibling header is
declared, so declaring the third would have made the committed schema
inconsistent with itself.

## The must-have truths, each verified

1. **Reconciled, not converted.** The body is still the vessel; the echo joined
   two existing siblings and displaced neither. Both are asserted present and
   correct in the same tests as the echo.
2. **`D-IMPL-126` and `canonical_response`'s ruling stand verbatim.** Measured
   by diff hunk, above. The new constant's comment **defers to** the four
   `ETag` reasons in the same words `REPLAY_REF_HEADER` uses — *"apply here
   unchanged and are not restated"* — and does not repeat them.
3. **Absent, never empty.** Asserted as `header not in response.headers`, with
   a control that fails when a question *was* posed. Both legs observed.
4. **Serialized exactly once.** One `canonical_bytes(payload)` call; the echo
   is a second serialization of a different object, and nothing hashes it.
5. **Coverage stated honestly.** There is **no HTTP client adapter**, so the
   echo is verified **producer-side only**, and nothing in this plan claims
   client-side coverage on this transport. The sentence is in the test
   module's docstring, in the surface fragment, and here.
6. **Every new assertion carries a named sabotage control**, each observed
   red — four sabotages plus the RED gate, above.

## Deviations from Plan

### Where the plan was measurably wrong, or incomplete

**1. `WireRequest` refuses on two axes, not one.** The plan's "one thing this
plan must MEASURE" section is entirely about `parameters`. It does not mention
the temporal guard, which refuses a naive instant — and the HTTP door's
`asked_at: datetime | None` accepts one from FastAPI. Left unhandled that is a
**500** where a `200` used to be, which is worse than either shape the plan
weighed. So a second refusal was added. This is Rule 3 (a blocking issue
created by the task's own mechanism) and Rule 1 (`WireRequest`'s docstring
asserted a refusal that did not happen).

**2. The error code for that second refusal is a compromise, and it is
flagged rather than hidden.** The plan says to use *"the same error code
`_asked` already uses for a malformed `parameters` string"*. That is right for
a wire-unstable parameter and **wrong** for a naive instant — a caller told
`product-parameters-malformed` about their `asked_at` would be misdirected.
`runtime/ccf_runtime/http_api/errors.py` is outside this plan's declared file
set, so no new constant could be added. `ERROR_PRODUCT_REQUEST_INCOMPLETE` is
used instead, whose own recorded meaning — *"a defaulted axis is a question
nobody asked, answered anyway ... the door refuses rather than filling one
in"* — genuinely covers an axis supplied without the offset that makes it
unambiguous. **`19-08` should rule on whether a dedicated
`product-asked-at-naive` code is owed.** Recorded in the surface fragment too.

**3. The plan's `key_links` pattern did not match the natural call site.** The
declared link is `canonical_response\(.*asked=`, and a call wrapped across
three lines does not satisfy a per-line grep. Rather than leave a declared
link unmatched, the replay reference was bound to a local so the whole call
fits one 88-column line (commit `0a7b466`). Recording it because a
verification pattern that the correct implementation fails is a defect in the
pattern, and silently ignoring it is how a link stops being checked.

**4. Line-number citations in the plan's `<read_first>` blocks were stale, as
warned.** `routes/__init__.py`'s `canonical_response` was cited at `:131-208`
and was in fact at `:131-213`; `product.py`'s `_asked` at `:283-419` was
correct, but the sibling-asymmetry paragraph cited at both `:55-75` and
`:60-70` is at `:54-69`. Every symbol name was correct and was used to find
the code.

### Rule 3 — auto-fixed blocking issues

**`[Rule 3 - Blocking]` Two CI surface gates refused the new public name.**
`tests/test_surface_completeness.py::test_every_diff_line_has_a_matching_public_log_entry`
and `tests/deployment/test_class_lookup.py::test_the_phases_fragments_claim_exactly_what_was_added`
both reported `NO ENTRY` for `ccf_runtime.http_api.routes.REQUEST_ECHO_HEADER`
— the same class `19-01` and `19-02` each hit, and a consequence of what this
plan added rather than a pre-existing failure. Filed
`docs/surface-changes/19-06-the-http-door-publishes-the-question.md`, named per
`D-IMPL-155` (a fragment whose filename does not match `[0-9]*-*.md` is
silently excluded with every gate green), then reassembled with
`make surface-changes`. Counters move **up** (741 → 745 entries, 504 → 507
public), so `D-IMPL-155`'s drop-a-record hazard did not fire; all three deleted
lines are counter lines the regeneration recomputed. Commit `00ec7f8`.

`tools/docs_tests/test_retirement_sweep.py` needed **no** regeneration this
time — unlike `19-01` and `19-02`, no import block in a swept file changed
shape.

### Not done, and deliberately

- **No HTTP client adapter**, and none is implied. The echo is producer-side
  only.
- **Nothing of `C-18` is implemented.** Its cross-check has no subject on this
  door, because the echo's boundary is built **from** the one `asked_at` the
  route parsed — one source, so a cross-check would compare a value with
  itself. That is recorded in one sentence beside the echo construction and in
  `canonical_response`'s `Args:` entry, so a later reader does not read the
  absence as an oversight.
- **No OpenAPI declaration and no `make openapi` run**, following the measured
  precedent.
- **`.planning/STATE.md` and `.planning/ROADMAP.md` were NOT written**, per the
  orchestrator's standing instruction that it owns those writes after the wave
  merges.

## Docstrings this plan made TRUE, for `19-07`

The inverse of `19-02`'s list — two shipped claims that were false against the
tree and now are not:

1. `src/ccf/products/door.py` — `WireRequest._temporal_boundary_survives_the_wire`'s
   *"both product doors refuse a naive `asked_at` by name"*. Measured false of
   the HTTP door before this plan; true after. **No edit was made to that
   docstring** — the code moved to meet the claim, which is the direction that
   needs no prose correction.
2. `runtime/ccf_runtime/http_api/routes/__init__.py` — `canonical_response`'s
   *"each surface publishes the same sibling values through whatever channel it
   actually has"*. It was an argument about the replay reference and the
   content address; it is now true of the request echo as well, which is what
   `C-09` asked for. Also unedited.

## Known Stubs

None. Every name added is set by a producer and read by an assertion:
`REQUEST_ECHO_HEADER` is set at one site and read by three test modules'
assertions; `canonical_response`'s `asked` parameter is passed by the one call
site that has a question and read by the one conditional that stamps the
header. No signature member was reserved (`C-10`).

## Threat Flags

None beyond the plan's own `<threat_model>`. `T-19-18` is mitigated — the echo
is built producer-side and the docstring states that an adapter decodes the
header rather than reconstructing. `T-19-19` is mitigated by base64url, with
the reasoning in the constant's comment. `T-19-20` is accepted as ruled.
`T-19-21` is mitigated and **measured**: the refusal is a `400`, not a `500`,
and it was checked against `assert_same_verdicts` before being committed to.
`T-19-SC` holds — this plan installed no package and added no dependency.

## Self-Check: PASSED

Created files:
- FOUND: `docs/surface-changes/19-06-the-http-door-publishes-the-question.md`
- FOUND: `.planning/phases/19-.../19-06-SUMMARY.md`

Commits (all present in `git log`):
- FOUND: `21ae323` `feat(19-06): a third X-CCF-* sibling, and canonical_response can publish it`
- FOUND: `56ef4c8` `test(19-06): failing legs for the HTTP request echo, both presence and absence`
- FOUND: `bf88f69` `feat(19-06): the product route publishes the question it parsed, and nothing when there was none`
- FOUND: `00ec7f8` `docs(19-06): file the surface fragment and reassemble the generated log`
- FOUND: `0a7b466` `style(19-06): keep the echo call site on one line`

Key links (all matched):
- `runtime/ccf_runtime/http_api/routes/product.py` → `canonical_response\(.*asked=` — 1 match
- `runtime/ccf_runtime/http_api/routes/__init__.py` → `REQUEST_ECHO_HEADER` — 4 matches

Files touched outside the plan's `files_modified`: **two**, both Rule 3 surface
records — `docs/surface-changes/19-06-*.md` (new) and `docs/SURFACE-CHANGES.md`
(regenerated). Neither `.planning/STATE.md` nor `.planning/ROADMAP.md` was
modified.
