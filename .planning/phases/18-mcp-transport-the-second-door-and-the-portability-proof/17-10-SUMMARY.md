---
phase: 18-mcp-transport-the-second-door-and-the-portability-proof
plan: 10
subsystem: mcp-egress-door
status: partial
tags: [mcp, http-api, product-request, refusal-envelope, replay-ref, d-impl-133, d-impl-148]
requires:
  - D-IMPL-133 (both doors carry parameters — the ruling Task 1 implements)
  - D-IMPL-148 + Addendum A (the refusal envelope, and both doors carry the replay reference)
  - D-IMPL-121 (validation stays at the resolver, never at a door)
  - D-IMPL-103 (one level of declared nested types)
  - D-IMPL-126 (the content-address header whose argument the replay-ref header reuses)
provides:
  - the MCP egress tool's `parameters` argument
  - the HTTP product route's `?parameters=` JSON-object query surface
  - ERROR_PRODUCT_PARAMETERS_MALFORMED
  - assert_same_verdicts / assert_type_mismatch_refused (the width ceiling, mechanized)
  - ccf.products.door — DoorOutcome, ServedAnswer, served_answer, door_refusal
  - the MCP tool's canonical refusal envelope, as a return value
  - X-CCF-Replay-Ref on the HTTP product door
  - assert_refusals_identical / assert_governance_stays_a_raise / assert_both_doors_carry_the_replay_ref
affects:
  - src/ccf/products/door.py
  - runtime/ccf_runtime/mcp/egress.py
  - runtime/ccf_runtime/http_api/routes/product.py
  - runtime/ccf_runtime/http_api/routes/__init__.py
  - runtime/ccf_runtime/http_api/errors.py
  - openapi.json
tech-stack:
  added: []
  patterns:
    - "verdict-over-door-callables: both doors compared as `Callable[[Mapping], Verdict]` so a control substitutes a divergent door into the real assertion"
    - "non-vacuity guard: an assertion refuses a table, or a pair of answers, that cannot fail for the reason it exists"
    - "reflection-over-transcription: field comparison derived from the contract's `model_fields`, never a written-down list"
    - "sibling-channel-per-transport: outcome-level values ride a header on HTTP and an envelope on MCP; the vessel's bytes are never touched"
key-files:
  created:
    - src/ccf/products/door.py
    - tests/mcp/test_egress_parameters.py
    - tests/mcp/test_egress_refusal_envelope.py
    - docs/surface-changes/17-10-both-doors-carry-parameters.md
    - docs/surface-changes/17-10-both-doors-carry-the-replay-reference.md
  modified:
    - runtime/ccf_runtime/mcp/egress.py
    - runtime/ccf_runtime/http_api/routes/product.py
    - runtime/ccf_runtime/http_api/routes/__init__.py
    - runtime/ccf_runtime/http_api/errors.py
    - tests/crossproc/test_mcp_egress.py
    - tests/test_surface_shape_capture.py
    - docs/DECISIONS.md
    - docs/SURFACE-CHANGES.md
    - openapi.json
decisions:
  - "D-IMPL-133 Addendum A — the recorded `parameters={}` objection is half false, half honoured"
  - "D-IMPL-148 Addendum A — both doors carry the replay reference; Task 4 is gated on both"
metrics:
  tasks_completed: 2
  tasks_total: 4
  duration: ~2 sessions
  completed: 2026-08-17
---

# Phase 18 Plan 17-10: MCP Transport — Partial Summary

Tasks 1 and 2 shipped. **Both parameterised product doors carry a client's
parameters, the MCP door now refuses in the canonical envelope rather than in a
raised exception, and both doors name the replay record that authorized a
delivery.** Tasks 3 and 4 were **not executed** — deliberately, because
`D-IMPL-148` Addendum A gates Task 4 on exactly what Task 2 just shipped and a
separate executor takes them from here.

## Status: 2 of 4 tasks

| Task | Name | Status | Commit |
| --- | --- | --- | --- |
| 1 | The egress tool carries a client's parameters | **complete** | `74a4224` |
| 2 | The MCP door emits the canonical refusal envelope (+ both doors carry the replay ref) | **complete** | `36c78fb` |
| 3 | The `mcp+stdio` adapter, sync at the surface | **not started** | — |
| 4 | Bind MCP into the conformance suite | **not started** | — |

---

# Task 1 — what shipped

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

## The parameter case table, and its size

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

A verdict is what `refuse_request` says about the request the door **actually
carried** — which under `D-IMPL-133` is exactly the half a door is responsible
for, and the only definition under which the two doors are comparable at all.

## The non-vacuity guard is the part that matters

`assert_same_verdicts` **refuses a table in which no case is served.** Without
that guard the table passes against the two *unrepaired* doors: both carried
`{}`, so every case reached the resolver as the same empty mapping and the two
agreed perfectly while carrying nothing. This was not theoretical — it was
observed during the RED run, where the wider-door control tripped the vacuity
guard instead of the width assertion because the HTTP door still carried
nothing.

## Sabotage controls (D-22) — three, all shipped tests, all observed firing

| Control | Divergent subject passed into the **real** assertion | Observed |
| --- | --- | --- |
| `test_the_width_assertion_fires_on_a_wider_mcp_door` | a fake `ask_mcp` that admits the undeclared parameter | raises, matches `wider` |
| `test_the_width_assertion_fires_on_a_table_that_never_serves` | two doors that never serve | raises, matches `no served case` |
| `test_the_coercion_assertion_fires_on_a_coercing_door` | a door that reads `"11"` as `11` and serves | raises, matches `type-mismatch` |

No control edits `runtime/` and reverts. **`git status --porcelain runtime/`
was empty after running them** (verified). Each is a test that runs on every CI
run forever, not an edit that leaves nothing in the tree.

## The `16-26` absorption, as written into `docs/DECISIONS.md`

Recorded as **`D-IMPL-133` Addendum A**. Its measured justification, in short:
`16-26` was filed *"neighboring, not gating"* and is gating, because the
conformance fixture class declares `minimum_score` **required**
(`tests/client/fixtures/deployment/ccf_config.yaml:46`). With `parameters={}`
hard-wired, an MCP adapter could not ask the phase's own question, could not
pass `D-15(a)` served parity, and could not carry `D-23` — every call would
have refused `missing-required-parameter` identically, so the parity legs would
have compared two refusals and reported green while proving nothing.

## The recorded reason was amended, never deleted — and its two halves differed

- **The coercion half is FALSE as measured.** It claimed *"a flat tool-argument
  map cannot carry `D-IMPL-103`'s declared nested types without the door
  guessing at coercions."* An MCP tool-argument map is **not flat and not
  string-valued — it is JSON.** Probed against `mcp==1.28.1`: a presented `3`
  arrived `int`, `"3"` arrived `str`, `true` arrived `bool`, and
  `{"a":[1,2]}` arrived a nested `dict`. Nothing is left to guess at.
- **The width half is TRUE and still binding.** The HTTP door hard-wired the
  identical `parameters={}` for the identical reason, and those two were the
  only two `ProductRequest` construction sites for a door in `runtime/`.
  Honoured by repairing **both** — which is what `D-IMPL-133` ruled.

---

# Task 2 — what shipped

Task 2's original content was *the MCP door emits the canonical refusal
envelope*. **Dave widened it the same day**, and the amendment is the reason
this task is larger than the plan wrote it.

## The ruling that widened the task

`D-IMPL-148` (Dave, 2026-08-17) had scoped the replay-reference fix to the MCP
door and recorded the HTTP door's identical gap as **deferred, not fixed**,
explicitly *"stated as an assumption rather than a ruling, because Dave was
offered the sub-question and did not annotate it."* Dave annotated it:

1. **Both doors carry the reference** — `egress.py` **and** `routes/product.py`.
2. **Only after both emit it** may the MCP adapter be bound into the
   conformance suite. That ordering is why this executor's scope stopped
   before Task 3.
3. **Do not special-case MCP, do not drop `replay_ref` from the parity
   comparison, do not weaken the parity suite.** Making a second adapter
   official while it and the HTTP door silently omit a compared field *"would
   make the conformance suite lie."*

Recorded as **`D-IMPL-148` Addendum A**, appended at the end of
`docs/DECISIONS.md` so no line-anchored citation shifts. The base entry's scope
paragraph is **amended and marked superseded, never deleted** — the paragraph
stands as the record of what was assumed, and the addendum carries the
behaviour.

## Why one change and not two

A refusal **cannot be raised** at this door. Measured against `mcp==1.28.1`,
FastMCP wraps a raised tool exception as
`ToolError: Error executing tool <name>: <message>` and delivers it
`isError=True` with that prose prefix — so a client wanting the governed answer
would have to strip a server's wording. String-parsing prose for an audited
verdict is not a channel.

So the refusal had to become the tool's **return value**, the return therefore
became a structure, and **the replay reference rides that same shape change
instead of forcing a second one.** That is the whole reason the two rulings
landed as one commit.

## What was built

**`src/ccf/products/door.py`** — new, and in `src/` for the reason
`ccf.products.refusal` gives for its own placement: the shape is emitted by a
door in `runtime/` and decoded by a client in `src/ccf/client`, and `src/`
cannot import `runtime/`.

| Name | What it is |
| --- | --- |
| `DoorOutcome` | The wire shape: `product_json`, `replay_ref`, `refusal`, with a model validator enforcing exactly one half |
| `ServedAnswer` | A frozen dataclass — the vessel and its reference. Not a contract; it never crosses a wire |
| `served_answer(resolved)` | Reads both served shapes; `TypeError` naming the type on anything else |
| `door_refusal(resolved, *, asked, product_class, version)` | Passes a `RefusalEnvelope` through untouched; translates a bare refusal value; `None` when it is not a refusal at all |

**The MCP tool** returns `canonical_bytes(DoorOutcome(...)).decode("utf-8")`.
**The HTTP route** publishes the same string under the new
`REPLAY_REF_HEADER` (`X-CCF-Replay-Ref`), via one keyword-only, defaulted
`replay_ref` parameter on `canonical_response`.

## The asymmetry is the transports, not the doors

Both doors carry the same values; each uses the sibling channel it actually
has. The argument is not new — it is `canonical_response`'s own, recorded for
the content address and reused verbatim: **the body *is* the product, so
anything carried inside it changes the bytes and therefore changes the address
they claim.** HTTP has a header, so the reference goes in a header and the body
is untouched. The MCP tool has an envelope, so it goes in the envelope and the
vessel rides as text inside it.

**The MCP resource is deliberately excluded, and that boundary is stated
rather than left to be inferred.** It carries no request, so it has no question
a refusal envelope could name; it has neither a header nor an envelope, so it
has no sibling channel. Giving it one means making it a different resource, and
the `mcp+stdio` adapter calls the **tool** (it must, to carry `parameters`), so
conformance is unaffected.

## Task 1's byte-identity assertion: restated, and why that is not weaker

**This is the item the ruling told me to face honestly rather than delete.**

Task 1 shipped `assert tool_text == resource_text` — the tool's *whole return*
was the vessel, byte for byte. Two shipped assertions rested on it:

| Assertion | Before | After |
| --- | --- | --- |
| `tests/mcp/test_egress_parameters.py::test_the_tool_carries_the_resources_bytes_without_re_serializing_them` (renamed from `..._the_tool_body_is_byte_identical_to_the_resources`) | `tool_text == resource_text` | `DoorOutcome.model_validate_json(tool_text).product_json == resource_text` |
| `tests/crossproc/test_mcp_egress.py::test_the_tool_is_never_the_weaker_path` | `tool_text == expected` | `DoorOutcome.model_validate_json(tool_text).product_json == expected` |

**The claim these assertions exist to make is *the parameterised surface is not
a second serialization of the product*** — a re-encode there would silently
change the content address of the resource beside it. That claim is asserted at
full strength, on raw text, unchanged. What is **no longer** claimed is that
the tool's return has *no frame around* those bytes — which is exactly and only
what the ruling changed.

It is also **stronger** in one respect it was not before: the text must now
validate as a `DoorOutcome`, so a door emitting an ad-hoc shape fails here
rather than being read as a vessel.

A third assertion got strictly stronger as a side effect.
`tests/crossproc/test_mcp_egress.py::test_two_questions_reach_two_content_addresses`
hashed *whatever the tool returned*; it now hashes the vessel the envelope
carries, which is the product's **actual** content address. The test's name was
already making that claim and only now measures it.

## Served vs refused: discriminated structurally, never by sniffing

Three mechanisms, and the conjunction is the claim:

1. `DoorOutcome`'s halves are **exclusive named members** under a model
   validator — a caller cannot construct their way to "both" or "neither".
2. `RefusalEnvelope` and `ContextProductContract` are both frozen and
   `extra=forbid` with **disjoint required fields**, so neither validates as
   the other.
3. The bare vessel is **not** a `DoorOutcome`, so a door emitting one is caught
   rather than read as an outcome with missing halves.

All three are asserted in
`test_the_served_and_refused_shapes_cannot_validate_as_each_other`. Nothing in
the module branches on the presence of a key.

## The governance boundary, drawn rather than missed

**A `ProductEntitlementRefused` still RAISES.** It is decided *before* the
resolver is reached, and contract-level entitlement at the client seam is on
the v0 not-list (`D-IMPL-129`). Enveloping it would report *"the fabric
answered no"* about a caller the fabric never answered at all — an audit record
of a decision that was not made.

Asserted on **both** halves, because neither implies the other:

- on the wire, an unentitled caller gets the protocol-native error and **no**
  `DoorOutcome` at all (`pytest.raises(ValidationError)` on the returned text);
- in the translation, the shipped `door_refusal` produces **no** envelope for
  the type — asserted through `assert_governance_stays_a_raise`, which takes
  the renderer as its subject.

A door could get the first right by accident and still acquire a translation
later. That is why both are checked.

## Nine behaviours

| # | Behaviour | Test |
| --- | --- | --- |
| 1 | A request the class does not answer returns an envelope; `kind` names the violation | `test_a_request_the_class_does_not_answer_returns_an_envelope` |
| 2 | A gate refusal carries its own typed fields, unflattened | `test_a_gate_refusal_carries_its_own_typed_fields` |
| 3 | The envelope carries the pre-assembly request identity, `parameters` included | `test_the_envelope_carries_the_pre_assembly_request_identity` |
| 4 | A governance refusal still raises and is not enveloped | `test_a_governance_refusal_still_raises_and_is_not_enveloped` |
| 5 | The MCP refusal is **field-identical** to the in-process one | `test_the_mcp_refusal_is_field_identical_to_the_in_process_one` |
| 6 | The MCP door carries the replay reference, and the vessel is byte-identical | `test_the_mcp_door_carries_the_replay_reference` |
| 7 | **Both** doors carry the **same** reference for the same product | `test_both_doors_carry_the_same_replay_reference` |
| 8 | A resolver carrying no reference has its absence reported, by omission | `test_a_resolver_that_carries_no_reference_reports_its_absence` |
| 9 | Served and refused cannot validate as each other | `test_the_served_and_refused_shapes_cannot_validate_as_each_other` |

Behaviours 1–5 are the plan's five. Behaviours 6–8 are the ruling's widening.
Behaviour 9 is the ruling's *"structurally, not by sniffing"* made executable.

Behaviour 5 is the leg **D-15(b) will consume in Task 4**, and its construction
is what makes it worth leaning on: **one resolver, driven two ways.** In process
a caller holds the envelope the resolver returned; over MCP the *same* envelope
is canonically serialized, carried, and re-validated. Field-identity is
therefore a statement about the **crossing** rather than about two
implementations happening to agree.

## Sabotage controls (D-22) — three more, all observed firing

| Control | Divergent subject passed into the **real** assertion | Observed |
| --- | --- | --- |
| `test_the_identity_assertion_fires_on_a_dropped_kind` | a refusal pair with `kind` changed on one | raises, matches `kind` |
| `test_the_boundary_assertion_fires_on_a_renderer_that_envelopes_governance` | a renderer that turns a governance refusal into a well-formed envelope | raises, matches `governance refusal` |
| `test_the_replay_ref_assertion_fires_on_a_door_that_drops_it` | (a) a door emitting `None`; (b) two doors emitting *different* references | raises, matches `no replay reference` / `property of the decision` |

No control edits `runtime/` and reverts — `git status --short` after the run
shows only the intended, committed files.

**`assert_both_doors_carry_the_replay_ref` checks absence before equality, and
that ordering is the guard.** Two doors both emitting `None` would agree
perfectly while carrying nothing — the vacuous pass this repository ships
repeatedly, and the exact state `D-IMPL-148` was raised about. So a `None` from
either side is refused **by name** rather than compared.

**`assert_refusals_identical` derives its field list from
`RefusalEnvelope.model_fields`, never from a written-down list** — the
discipline `result_fields()` already uses in the conformance suite. A member
added to the envelope next year is compared here without an edit, which is what
stops the assertion narrowing as the contract widens.

## Deviations from Plan (Task 2)

### 1. `[Rule 2 — missing critical functionality]` the HTTP door was repaired, and the plan's Task 2 `files_modified` did not list it

`D-IMPL-148` **Addendum A** is Dave's explicit ruling on exactly this, and it
supersedes the base entry's deferral. Commit `36c78fb`.

### 2. `[Rule 1 — bug]` the plan's *"the door translates a raised refusal"* is not implementable, and the reason is a measurement

The plan's `<action>` says the door should catch *"what its resolver raises or
returns"*. **Nothing raises a refusal.** Every type in `REFUSAL_KINDS` is a
`CCFContract` — a *value* — so none of them can be raised, and no shipped
exception in the tree carries one. `door_refusal` therefore handles the two
**returned** shapes (a ready-made `RefusalEnvelope`, and a bare refusal value)
and says in its own docstring that no third channel exists and why. This is
recorded rather than silently narrowed, because "handle both" was an
acceptance criterion.

### 3. `[Rule 3 — blocking]` the `_serializes_the_whole_vessel` invariant constrained the refactor's shape

`tests/invariants/test_replay_by_construction.py::test_no_enumerated_door_can_drop_the_debt_the_vessel_carries`
walks each door module's **source** for a call `canonical_bytes(<x>.product)`
or `canonical_response(<x>.product)`. Moving the serialization into
`ccf.products.door` would have made every door fail that check while behaving
identically — a false red, but a red the refactor had to respect. So the helper
returns the **vessel and the reference** and each door still serializes
`answer.product` in its own source. This is why `ServedAnswer` exists as a type
rather than the door helper simply returning bytes.

### 4. `[Rule 3 — blocking]` three surface gates went red and were repaired

Caught only because exit codes were branched on rather than echoed.
`tests/test_surface_drift.py`, `tests/test_surface_completeness.py` and
`tests/test_surface_shape_capture.py` all failed on the new public names.
Repairs: a new fragment
`docs/surface-changes/17-10-both-doors-carry-the-replay-reference.md` with six
seven-field entries; `canonical_response` registered in
`_SHAPE_MOVED_BY_FRAGMENT` with its reason; `docs/SURFACE-CHANGES.md`
reassembled via `make surface-changes`.

**`docs/surface/v0.2-surface.json` was NOT regenerated** — single-owner rule,
only `15-01` and `15-21` write it. `git status` confirms it is untouched.

### 5. `[Rule 1 — bug]` a stale citation in Task 1's own fragment was repaired

`docs/surface-changes/17-10-both-doors-carry-parameters.md` cited
`test_the_tool_body_is_byte_identical_to_the_resources` by `path::Symbol`
(`D-IMPL-114`). Renaming the test would have left a citation resolving to
nothing. Updated, with a pointer to the restatement and its reason.

---

## Findings — verified against the tree, not asserted

### FINDING 1 (was blocking for Task 4): **CLOSED.** Served parity's `replay_ref` leg can now pass

The previous summary recorded that `assert_served_parity` compares `replay_ref`
and that no shipped door emitted one, so an `mcp+stdio` adapter would produce
`replay_ref=None` and the parity leg would report a disagreement. **Both doors
now emit it**, and the field was neither exempted nor dropped from the
comparison — which was Dave's explicit condition. `tests/client/conformance/`
is untouched: `git diff` against it is empty.

The remaining Task 4 dependency is Task 3, not this.

### FINDING 2 (design input for Task 2): **CONSUMED.** A refusal is the tool's return value

Recorded in full above and in `D-IMPL-148` Addendum A. `mcp==1.28.1` was
re-confirmed as the installed version.

### FINDING 3 (advisory, still open): the plan's Task 3 verification command names a symbol that does not exist

The plan's automated check is `from ccf.client.binding import SCHEMES`. The
registry is named **`SCHEME_REGISTRY`** (`src/ccf/client/binding.py`, confirmed
again at this commit). A later executor running that command verbatim gets an
`ImportError` rather than a verdict.

### FINDING 4 (new, advisory): the HTTP door still has no refusal channel

DIV-4 is unclosed on HTTP and this is **deliberately** so, recorded in
`routes/product.py`'s module docstring and in Addendum A. A resolver answering
with a `RefusalEnvelope` there reaches `served_answer` and raises a `TypeError`
**naming the shape** — an opaque 500, exactly as the pre-existing
`AttributeError` produced, but now saying what went wrong. Rendering a fabric
refusal over HTTP is a status-code and body-shape decision nobody has ruled,
and inventing one on a shipped door would put an unruled contract in front of
adopters.

### FINDING 5 (new, operational): `make` targets need a `.venv` inside a worktree

`Makefile:10` is `PYTHON := .venv/bin/python` — a **relative** path — and a
fresh Claude Code worktree has no `.venv`, so every `make` target fails with
`No such file or directory` before running anything. A gitignored symlink to
the main checkout's `.venv` fixes it. `ENV := PYTHONPATH=src:runtime` is also
relative and therefore resolves to the **worktree's** `src` and `runtime`,
which is correct — but a bare `.venv/bin/python` invocation without that
`PYTHONPATH` would grade the **main checkout's** code, because the venv's
editable install points there. Verified at this commit:
`PYTHONPATH=<worktree>/src:<worktree>/runtime` resolves `ccf` to the worktree.

---

## Requirements

`CLNT-15` is **partially** satisfied — its parameters clause and its
refusal-envelope clause are discharged; its conformance clause is not.
`CLNT-12` is untouched by the shipped half. Neither is marked complete.

## Verification

Every run set `PYTHONPATH` to the worktree's `src:runtime`, and every exit code
was **captured and branched on** rather than echoed. `make ci-core` was run
**detached** with a `REAL_EXIT` sentinel, because it takes ~10 minutes and a
foregrounded run is killed mid-sweep — a truncated log is not a pass.

| Command | Exit | Result |
| --- | --- | --- |
| `make ci-core` (first run) | **2** | `make test` **3816 passed, 118 skipped, 0 failed**; `lint` 0; `typecheck` 0; **`gate-tools` red** on one stale generated report — see below |
| `make ci-core` (confirming re-run) | **0** | `3816 passed, 118 skipped, 0 failed`; `gate-tools` `400 passed` + `154 passed` |
| `make lint` | 0 | clean |
| `make typecheck` | 0 | `Success: no issues found in 210 source files` |
| `pytest tests/mcp/test_egress_refusal_envelope.py` | 0 | 12 passed |
| `pytest tests/mcp tests/crossproc/test_mcp_egress.py tests/http_api` | 0 | 174 passed |
| `pytest tests/crossproc tests/http_api tests/mcp tests/invariants` | 0 | 445 passed |
| surface gates (drift, completeness, shape capture, citation coverage) | 0 | 44 passed |
| `make gate-tools` | 0 | `400 passed`, `154 passed` |
| `make openapi` | 0 | **no diff** — the HTTP response *body* did not move |

Baseline for comparison was **3804 passed, 118 skipped** at Task 1's merge. The
delta is **+12**, which is this task's twelve new tests, and **no test was
removed** to get there.

### The first `ci-core` run went red, and reporting it is the point

`REAL_EXIT=2`. It was branched on rather than echoed, which is the only reason
it was seen: the failure is a **single** stale generated report
(`docs/surface/examples/RETIREMENT-COUPLINGS.md`), two lines of line-number
drift caused by the docstring paragraphs added to `egress.py`. It was
regenerated and the gate went green.

**One measurement worth carrying forward, because it cost a cycle.** The
retirement sweep scans **every file in the repository**, including untracked
scratch files. Regenerating the report while transcript logs sat in the
worktree root produced a report claiming `234 rows across 74 files`; with those
files deleted the true figure is `232 rows across 73 files`, and the committed
report was then stale in the *opposite* direction. **A regenerated report is
only correct if the working tree is clean of scratch files when it is
regenerated.** Every log this task produced was written outside the repository
after that was discovered.

`make conformance` and `make docs-strict` were **not** run — they belong to
Tasks 3 and 4, which were not executed.

### `openapi.json` — measured, not assumed

The success criterion was *"regenerated if the HTTP response surface moved."*
It did not move: the change is a **response header**, and FastAPI declares
neither `X-CCF-Replay-Ref` nor the pre-existing `X-CCF-Content-Address` in the
OpenAPI document. `make openapi` was run and `git status` showed `openapi.json`
unmodified. The precedent is `D-IMPL-126`'s content-address header, which is
likewise absent from the document.

## Not done, and what it would take

- **Task 3** — `mcp+stdio` adapter. `src/ccf/mcp/client.py` speaks
  **streamable HTTP only and reads resources only**: it has no stdio transport
  and no tool-call surface, so the adapter needs both added. The
  harness-import lint permits the `mcp` import in `src/` — confirmed green,
  and `src/` already imports it in four modules. The adapter parses the tool's
  text as a `DoorOutcome` and maps it onto a `WireOutcome`: `product_json`
  straight across, `content_address` recomputed by the decoder,
  `replay_ref` straight across, `refusal` straight across. **It builds no
  `Result`** (`D-12`). Note `SCHEME_REGISTRY`, not `SCHEMES` (FINDING 3).
- **Task 4** — conformance binding. Needs a stdio server entry point that boots
  a deployment root the way `inprocess::_boot` does. FINDING 1 is now closed,
  so the `replay_ref` parity leg is satisfiable — **provided the deployment's
  resolver is a `GovernedResolver`**, which returns `ServedProduct` and
  therefore carries a reference. A fixture resolver returning the narrower
  `ServableProduct` would emit `replay_ref=None` over MCP and disagree with the
  in-process leg. That is the first thing to check when wiring the fixture.

**`tests/client/conformance/` was not touched.** `git diff` against the
directory is empty — but that is the trivial truth, since Tasks 3 and 4 never
ran. It is **not** evidence for the phase's adapter-agnostic claim, and should
not be reported as though it were.
