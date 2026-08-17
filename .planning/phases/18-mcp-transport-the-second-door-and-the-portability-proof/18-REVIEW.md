---
phase: 18-mcp-transport-the-second-door-and-the-portability-proof
reviewed: 2026-08-17T00:00:00Z
depth: deep
commit: e3fb143
files_reviewed: 20
files_reviewed_list:
  - src/ccf/client/adapters/mcp_stdio.py
  - src/ccf/client/adapters/inprocess.py
  - src/ccf/client/adapters/binding_document.py
  - src/ccf/client/binding.py
  - src/ccf/client/client.py
  - src/ccf/client/codec.py
  - src/ccf/client/result.py
  - src/ccf/client/wire.py
  - src/ccf/products/door.py
  - runtime/ccf_runtime/mcp/egress.py
  - runtime/ccf_runtime/http_api/routes/product.py
  - runtime/ccf_runtime/http_api/routes/__init__.py
  - runtime/ccf_runtime/http_api/errors.py
  - tests/client/conformance/suite.py
  - tests/client/conformance/test_inprocess_conformance.py
  - tests/client/conformance/test_mcp_conformance.py
  - tests/client/conformance/test_the_mcp_binding_fires.py
  - tests/client/conformance/test_the_suite_fires.py
  - tests/client/conformance/conftest.py
  - tests/client/fixtures/stdio_server.py
  - tests/client/test_mcp_stdio_adapter.py
  - tests/contracts/test_canonical.py
  - tests/crossproc/test_mcp_egress.py
  - tests/mcp/test_egress_parameters.py
  - tests/mcp/test_egress_refusal_envelope.py
  - tests/examples/test_hw1_two_transports.py
  - tests/examples/test_client_example_purity.py
  - examples/hw1-companies-over-revenue/server/serve.py
  - examples/hw1-companies-over-revenue/consume.py
  - Makefile
findings:
  critical: 2
  warning: 6
  info: 0
  total: 8
status: issues_found
---

# Phase 18: Code Review Report

**Reviewed:** 2026-08-17
**Depth:** deep (single-agent depth pass, run alongside the cross-AI panel)
**Files Reviewed:** 30
**Status:** issues_found

## Summary

I read the phase's shipped code against the four questions in the brief, treating
every assertion as a suspect and asking of each *what state would make this fail,
and can that state occur?*

Two findings are blocking, and both are the phase's own defect class:

- **CR-01** is a demonstrated cross-transport divergence — I ran both of the
  README's documented commands with one changed flag and got two different
  exception types out of `ProductClient.ask`, neither of them the one the method
  documents. The guard that would have prevented it exists on the neighbouring
  field of the same contract and was not extended to this one.
- **CR-02** is the next instance of *an assertion that passes because it compares
  nothing*, and it is not in a test — it is in `src/`. Two client-seam integrity
  checks (`check_outcome`'s echo cross-check and `verify_content_address`) are
  structurally incapable of failing on either shipped adapter, including the new
  cross-process one, which is the case both were written for. Their docstrings
  claim the opposite in so many words.

The warnings are, in order: a residue of KF5 in the purity gate (the count is
still a literal, not a relationship); an `except` clause on the HTTP door that
does not cover everything `json.loads` raises; and the observation that the
cross-subject half of the new `assert_one_instant_is_one_decision` leg is fully
subsumed by two legs already running over the same subjects with the same
question in the same module.

What I checked and found sound, so the panel does not re-derive it: subprocess
lifecycle (`mcp==1.28.1`'s `stdio_client` closes stdin, waits, then escalates
SIGTERM→SIGKILL on its own task-group exit, so no orphan on any exception path);
argument handling (`command=sys.executable` with a list `args`, no shell, so no
injection surface from the binding string beyond what env-var control already
grants); served/refused discrimination (`DoorOutcome`'s validator plus two
`extra=forbid` frozen contracts with disjoint required fields, and
`test_the_served_and_refused_shapes_cannot_validate_as_each_other` is a real
check); the content-address computation across the frame change (round-trip is
byte-exact); and the `D-IMPL-133` parameter width table, whose non-vacuity guard
(`assert_same_verdicts`, `tests/mcp/test_egress_parameters.py:187`) is the
correct shape and is watched failing.

I did not re-derive KF1–KF5 or revive the REJECTED finding.

## Critical Issues

### CR-01: A naive `as_of` raises two different exception types on the two shipped transports, and neither is the one `ask()` documents

**Classification:** blocking
**Confidence:** high — reproduced by running both shipped commands.
**Files:**
- `src/ccf/client/wire.py:138` (the unguarded field)
- `src/ccf/client/wire.py:140-175` (the guard that exists for the neighbouring field)
- `src/ccf/client/client.py:160-165` (the documented `Raises:`)
- `src/ccf/client/adapters/mcp_stdio.py:209-211`
- `src/ccf/client/adapters/inprocess.py:377`
- `runtime/ccf_runtime/mcp/egress.py:703-712`

**Issue:**

`WireRequest.temporal_boundary: datetime | None` carries no validator.
`ProductRequest.asked_at: datetime` carries none either (the egress door records
this at `egress.py:183-199`: *"`ProductRequest` accepts a naive instant and the
failure surfaces later"*). Both shipped adapters therefore forward a naive
instant, and the two transports fail in two different places with two different
types. Measured on this tree, same `consume.py`, same deployment, same
parameters, one changed flag:

```
$ CCF_BINDING="inprocess:examples/hw1-companies-over-revenue/deployment" \
    .venv/bin/python examples/hw1-companies-over-revenue/consume.py \
    --min-revenue 1000000000 --as-of 2026-08-01T00:00:00
...
  File ".../src/ccf/graph/backends/sqlite.py", line 343, in _translated_statements
    boundary = canonical_timestamp(q.as_of)
ccf.contracts.canonical.CanonicalizationError: naive datetime is not canonically
encodable; attach an explicit timezone (no implicit UTC — D-IMPL-38)

$ CCF_BINDING="mcp+stdio:examples/hw1-companies-over-revenue/server/serve.py \
    examples/hw1-companies-over-revenue/deployment" ... --as-of 2026-08-01T00:00:00
...
  File ".../src/ccf/client/adapters/mcp_stdio.py", line 348, in _call
    raise TransportError(
ccf.client.errors.TransportError: the `mcp+stdio` server ... answered the product
tool with an error rather than an outcome — Error executing tool
request_context_product: asked_at '2026-08-01T00:00:00' carries no UTC offset...
```

Three separate defects fall out of one omission:

1. **The portability claim is false for this input.** `D-15`'s property is *same
   question, identical `Result` whichever transport carried it*. Here the two
   transports do not even raise the same class, and one of them (`mcp+stdio`)
   reports a **transport failure for a caller's malformed argument** — the exact
   inversion `D-10` and `ccf.client.errors` exist to prevent, stated at
   `mcp_stdio.py:80-89`. The wire spoke perfectly; nothing was broken.
2. **The public contract is wrong.** `ProductClient.ask`'s `Raises:` block
   (`client.py:161-165`) names only `TransportError`. A caller who wrote the one
   `except TransportError` clause the package tells them to write gets an
   unhandled `CanonicalizationError` from `ccf.contracts.canonical` on the
   in-process path.
3. **The guard for exactly this hazard already exists one field away and was not
   extended.** `WireRequest._parameters_survive_the_wire` (`wire.py:140-175`)
   refuses a `parameters` value that "does not survive the wire unchanged", and
   its docstring states the principle: *"the choice is not between strict and
   lax. It is between refusing the value at construction, where the message can
   name the wire-stable spelling, and reporting a transport failure that never
   happened at a point where nothing can diagnose it."* That sentence describes
   `temporal_boundary` precisely, and `temporal_boundary` has no such validator.

Nothing catches it: every conformance `Question` is either `as_of=None` or a
zone-bearing literal (`test_inprocess_conformance.py:99-138`), so the suite never
asks with a naive instant, and `hw1`'s two-transport test runs the README's
pinned, zoned `--as-of`.

**Fix:** add the missing field validator beside the one that already exists, so
the refusal happens at construction on every transport identically:

```python
# src/ccf/client/wire.py, on WireRequest
@field_validator("temporal_boundary")
@classmethod
def _boundary_is_zoned(cls, value: datetime | None) -> datetime | None:
    """Refuse a naive instant here rather than on one transport's wire.

    `D-IMPL-38`: a zone-less instant is a silent default, and which zone it
    silently meant is the difference between two answers. Refused at
    construction because the two shipped transports fail it in two different
    places with two different types — `CanonicalizationError` in process,
    `TransportError` over `mcp+stdio` — and a transport failure for a caller's
    malformed argument is the one inversion `D-10` forbids.
    """
    if value is None or value.utcoffset() is not None:
        return value
    raise ValueError(
        "`as_of` names no time zone, so the instant a question is asked as of"
        " is ambiguous — attach one, as in"
        " `datetime(2026, 8, 1, tzinfo=UTC)` (D-IMPL-38)"
    )
```

and add a conformance leg (or a case in `tests/client/test_mcp_stdio_adapter.py`
plus its in-process twin) asserting that a naive `as_of` raises the *same* type
on every subject. Note this is a client-surface widening in behaviour — it turns
two different runtime failures into one `ValueError` at construction — so it may
need a `D-IMPL` entry rather than an in-phase fix.

---

### CR-02: The two client-seam integrity checks cannot fail on any shipped adapter — including `mcp+stdio`, the transport they were written for

**Classification:** blocking
**Confidence:** high on the mechanism (it is provable from the code); the ruling
on what to do about it is Dave's.
**Files:**
- `src/ccf/client/codec.py:166-173` (the echo cross-check)
- `src/ccf/client/codec.py:88-123` (`verify_content_address`)
- `src/ccf/client/codec.py:30-42` (the docstring that claims the opposite)
- `src/ccf/client/adapters/mcp_stdio.py:396-412`
- `src/ccf/client/adapters/inprocess.py:420-442`
- `src/ccf/client/client.py:172`, `src/ccf/client/client.py:180-187`
- `src/ccf/products/door.py:139-141` (the wire shape with no request identity)

**Issue — half one, the echo.** `codec.py`'s module docstring is explicit that
the request identity is compared rather than reconstructed, and says why:

> The client could instead reconstruct the request identity from what it holds —
> cheaper, and one fewer thing on the wire. It is rejected because reconstruction
> cannot detect a transport that answered a *different question* than the one
> asked.

But `DoorOutcome` (`door.py:139-141`) carries **no request identity** — only
`product_json`, `replay_ref`, `refusal`. There is nothing on the MCP wire to echo.
So `McpStdioAdapter._decode` sets `request=request` from the argument it was
handed (`mcp_stdio.py:398` and `:406`), `InProcessAdapter._encode` does the same
(`inprocess.py:422`, `:437`), and `ProductClient.ask` then passes *that same
object* as `sent` (`client.py:172`). The comparison at `codec.py:166`

```python
if outcome.request != sent:
```

is `x != x`. It cannot fail for either shipped adapter. The one transport where a
proxying or multiplexing wire is physically possible is the one this phase
shipped, and on it the guard is inert. `_result_from`'s comment
(`client.py:180-187`) — *"taken from the outcome's echo rather than from `sent`,
which is only safe because `check_outcome` has just proven the two equal.
Reading it from the echo is what makes that check load-bearing instead of
advisory"* — describes a property the code does not have.

The phase's own control makes the point: `_AnswersAnotherQuestion`
(`tests/client/conformance/test_the_mcp_binding_fires.py:57-70`) is *exactly* the
failure the echo check claims to catch, and it is caught only by the
**cross-adapter content-address comparison** — i.e. by the test having a second
transport to diff against. An adopter running only `mcp+stdio` has no second
transport and therefore no protection at all.

**Issue — half two, the address.** `verify_content_address`'s docstring
(`codec.py:104-113`) says:

> The recomputed value is authoritative and the claimed one is never trusted: an
> address that travelled beside the bytes it describes is a claim about them, and
> the whole value of a content address is that the claim is checkable.

But the "claimed" address is computed **by the adapter itself, from the same
string it puts in `product_json`** — `mcp_stdio.py:407-409`
(`hashlib.sha256(outcome.product_json.encode("utf-8")).hexdigest()`) and
`inprocess.py:439` (`hashlib.sha256(vessel).hexdigest()` over the very bytes it
decodes into `product_json`). So `codec.py:116`

```python
if recomputed != claimed:
```

is `sha256(x) != sha256(x)`. It cannot fail either. `Result.content_address`'s
docstring (`result.py:327-333`) repeats the unbacked claim: *"Never the value the
wire claimed."* The MCP door publishes no address at all
(`mcp_stdio.py:373-381` records this as deliberate); the HTTP door does publish
`X-CCF-Content-Address` (`routes/__init__.py:210`) but no client adapter consumes
HTTP, so the "checkable claim" story is currently true on zero shipped paths.

**Why this is blocking rather than advisory:** the phase's deliverable is a real
process boundary, and both defences a client has against that boundary
misbehaving are decorative on it. This is precisely the recorded defect class —
*treating absence of a failure signal as presence of a success signal* — sitting
in `src/` rather than in verification code, with three docstrings asserting the
guarantee.

**Fix (either limb, but the decision must be recorded):**

1. **Make the wire carry what the checks need.** `RequestIdentity` is already a
   shipped type (`ccf.products.refusal.RequestIdentity`) and the refusal half of
   `DoorOutcome` already carries one. Add it as a sibling on the served half, and
   have `_decode` cross-check the *server's* identity against the request that
   was sent before building the `WireOutcome`. Likewise, have the door publish
   its own `content_address` on `DoorOutcome` and have `_decode` pass the
   **server's** value as `claimed` rather than its own recomputation. Both are
   additive to a frame this phase already changed once.
2. **Or state the limitation where a reader will find it.** Amend
   `codec.py`'s module docstring, `verify_content_address`,
   `Result.content_address` and `ProductClient._result_from` to say that on
   transports whose wire carries neither identity nor address the checks
   degenerate to identities, name which shipped transports those are, and log
   the residual as a `D-IMPL` entry. Do not leave three docstrings claiming a
   guarantee no shipped path provides.

## Warnings

### WR-01: The purity gate's command count is still a literal, and its own message overclaims the relationship it enforces

**Classification:** advisory (adjacent to KF5, not a re-report of it)
**Confidence:** high
**File:** `tests/examples/test_client_example_purity.py:330`, `:333-343`

`documented_commands` now asserts `len(matches) == len(MAKE_TARGETS)` instead of
`== 1`. But `MAKE_TARGETS` is a hand-written two-element tuple in the test file,
not anything derived from the Makefile — so the assertion still reduces to
*"the README states exactly two `CCF_BINDING=` commands"*, and a third documented
transport is still structurally impossible without editing this constant. That is
KF5's shape one increment up.

Worse, the failure message (`:339-342`) claims a bidirectional property the
mechanism does not enforce:

> Every documented command runs from a target and every target is documented, so
> the two counts are one number

Only the first half holds. `make_recipe` (`:346-361`) proves each *named* target
exists in the Makefile; nothing proves the Makefile carries no **other**
`CCF_BINDING=` recipe. A third target added to the Makefile and left out of both
the README and `MAKE_TARGETS` passes this gate silently.

**Fix:** derive the target set instead of writing it down — scan the Makefile for
recipe lines beginning `CCF_BINDING=`, assert the resulting set has the same
cardinality as the README's blocks and that each pairs, and keep the ordering
assertion. Then the message's claim becomes true and a third transport joins by
editing two files rather than three.

---

### WR-02: `_parameters` catches only `ValueError`, and `json.loads` does not only raise `ValueError`

**Classification:** advisory
**Confidence:** the `except` gap is certain (verified: `json.loads` on a
100000-deep nesting raises `RecursionError`, which is not a `ValueError`).
Reachability through a production HTTP server is **uncertain** — at ~8000 nesting,
roughly the h11 request-line ceiling, `json.loads` still parses fine, so the
`RecursionError` may only be reachable in-process/over ASGI or behind a server
with a larger request-line limit. I am not asserting an exploit.
**File:** `runtime/ccf_runtime/http_api/routes/product.py:435-452`

```python
try:
    decoded = json.loads(supplied)
except ValueError as malformed:
    raise HTTPException(status_code=400, ...)
```

`runtime/ccf_runtime/http_api/app.py` registers no catch-all exception handler,
so anything `json.loads` raises other than `ValueError` becomes an opaque 500
rather than this door's own typed `ERROR_PRODUCT_PARAMETERS_MALFORMED`. The
door's docstring (`product.py:340-345`) says it *"refuses only text that is not a
JSON object at all — a malformed argument"*; a nesting-bomb is malformed and is
not refused, it crashes.

Separately, and independent of the `except` clause: there is **no bound at all**
on the size or nesting depth of the decoded object, which is subsequently walked
by recursive pure-Python code — `ccf.contracts.canonical._normalize` (which
renders the refusal envelope carrying these very parameters) and, client-side,
`ccf.client.wire._unstable_parameter`. Both have a ~1000-frame ceiling.

**Fix:** widen the clause and state a bound.

```python
except (ValueError, RecursionError) as malformed:
    raise HTTPException(status_code=400, detail=refusal_detail(
        error_code=ERROR_PRODUCT_PARAMETERS_MALFORMED, ...)) from malformed
```

and consider refusing a decoded object deeper than the canonical serializer can
normalize, so a caller's structure cannot reach `_normalize` at a depth that
raises there instead.

---

### WR-03: `assert_one_instant_is_one_decision`'s cross-subject half is fully subsumed by two legs already running beside it

**Classification:** advisory
**Confidence:** high
**File:** `tests/client/conformance/suite.py:838-867`; called at
`tests/client/conformance/test_mcp_conformance.py:143`

The compared view (`suite.py:862-866`) has three keys. Two of them —
`temporal_boundary` and `lineage.graph_snapshot_at` — were *just* asserted equal
to `question.as_of` for every subject at `:847-861`, so no subject can reach the
comparison with a different value for either; those two keys cannot differ. The
only live key is `content_address`, and `content_address` is already compared
across the same subjects, for the same `QUESTION`, twice in the same module:
`assert_served_parity` (which compares every declared field,
`test_mcp_conformance.py:86`) and `assert_one_question_is_one_address`
(`:126`). The control that watches this leg fire
(`test_the_suite_fires.py:709-734`) uses the identical divergence
(`_move_only_the_address`) as the control for
`assert_one_question_is_one_address` (`:576-585`).

The leg is **not vacuous** — its per-subject half (anchor checked against the
*input* rather than against another subject) is genuinely new and is the correct
repair for KF2. But its advertised cross-adapter value is not there, and the
docstring at `:816-822` argues for including the address on the ground that
without it the comparison "cannot fail" — which is true, and the remedy chosen
was to add a key that three other assertions already cover.

**Fix:** either state in the docstring that the cross-subject half is a
restatement retained for locality (so the next reader does not count it as
independent coverage), or replace it with something the other legs do not carry —
e.g. compare the *replay reference* across subjects at a pinned instant, which
`assert_served_parity` compares only as one of N fields and which is the field
`D-IMPL-148` was actually raised about.

---

### WR-04: The fixture stdio server contradicts its own no-hardcoding claim and never closes its graph handle

**Classification:** advisory
**Confidence:** high
**File:** `tests/client/fixtures/stdio_server.py:56-58`, `:93`, `:97`, `:101`,
`:104-182`

The module docstring states:

> Every value that identifies this deployment is read from its own documents
> rather than spelled — the No-Hardcoding Rule (CLAUDE.md §6.4) scopes to
> ``tests`` through ``tools/lints/__main__.py::RULE_TREE_SCOPE``.

Immediately below it, three deployment values are spelled: `TOOL_DESCRIPTION`
(`:93`), `SCOPE = "ccf.product.read"` (`:97`), `TOKEN_FILE` (`:101`). The
`no-hardcoding` checker does scope to `tests` (`tools/lints/__main__.py:124`) and
passes, so the lint does not treat a tool description as a deployment value — but
`build_egress_server`'s own docstring (`egress.py:396-397`) says *"the prose an
adopter's consumers read is a deployment value and not the SDK's to write
(CINV-01)"*, and the hw1 server reads exactly these four from `egress-door.yaml`
(`serve.py:123-149`). The two shipped servers disagree about whether these are
data, and one of them says in prose that it does what it does not do.

Second, smaller: `serve()` (`:104-182`) never closes `booted.fabric.handle`.
hw1's `serve.py:285-288` wraps `server.run` in `try/finally` and closes. The
fixture relies on process exit; that is fine in practice but it is the same
function in two shipped programs written two ways.

**Fix:** give the fixture an `egress-door.yaml`-equivalent (or narrow the
docstring claim to "every value that identifies this *deployment*", excluding the
door's own governance prose), and add the `try/finally`.

---

### WR-05: The example server pre-sets an authenticated identity in the root context, and nothing stops an adopter carrying that edit onto a network transport

**Classification:** advisory (hardening)
**Confidence:** **low-to-medium** on the exploit path; high that the file is
undefended against the edit. I have not exercised a network-transport variant.
**File:** `examples/hw1-companies-over-revenue/server/serve.py:276-284`; same
pattern at `tests/client/fixtures/stdio_server.py:173-181`

```python
auth_context_var.set(
    AuthenticatedUser(AccessToken(token=credential, client_id=..., scopes=[scope]))
)
server.run(transport="stdio")
```

Over stdio the reasoning is sound and is stated at length (`:50-64`): there is no
bearer channel, the security boundary is process ownership, and without this the
door refuses every caller as unverified. My concern is the *filing*: this is the
file the docstring nominates as the one an adopter opens *"when they want to know
how the second door is stood up"*, and the same file also supplies a real
`token_verifier` and `AuthSettings` on the stated ground that *"this same
deployment is reachable over HTTP with them in force"*. An adopter who follows
that sentence and changes `transport="stdio"` inherits a pre-set authenticated
identity in the context every request task descends from. FastMCP's
`RequireAuthMiddleware` should reject unauthenticated HTTP requests before a
handler runs, which is why I rate this low-confidence — but nothing in the file
warns against the edit, and no test asserts the pattern is stdio-only.

**Fix:** make the coupling structural rather than narrative — e.g. bind the
context var inside a small function that takes the transport name and raises for
anything but `"stdio"`, or add a two-line comment at the `auth_context_var.set`
call naming the edit that must not be made. A one-line assertion in
`tests/examples/test_hw1_two_transports.py` that the example's server only ever
calls `server.run(transport="stdio")` would make it a gate.

---

### WR-06: `_call`'s `CancelledError` re-raise is likely defeated by anyio's exception grouping, and the no-timeout posture pushes an unstatable obligation onto adopters

**Classification:** advisory
**Confidence:** **medium**, unverified by execution — I reasoned this from
`mcp/client/stdio/__init__.py:180-213` (the `anyio.create_task_group()` the
session runs under) rather than by inducing a cancellation.
**File:** `src/ccf/client/adapters/mcp_stdio.py:334-340`, `:64-78`

```python
except asyncio.CancelledError:
    raise
except Exception as unreachable:
    raise TransportError(...)
```

`stdio_client` and `ClientSession` run inside an anyio task group, which wraps
child-task failures in a `BaseExceptionGroup`. An `ExceptionGroup` (the
`Exception`-derived variant) is caught by the second clause, so a cancellation
surfacing as a *member* of a group is converted into a `TransportError` rather
than re-raised — defeating the explicit first clause. If that is right, the fix
is `except* asyncio.CancelledError` or an explicit group unwrap; if it is not,
the first clause is dead code and should be removed rather than left as a claim.
Either way one of the two is true and it is worth ten minutes to find out which.

Separately, and as an observation on a ruled decision rather than a defect:
`T-17-41` dispositions the no-timeout posture as accepted for v0, and the module
declines to invent a number (`:64-78`). But `ask()` takes no options and the
address has no field for one, so an adopter cannot supply the number either — the
only recourse is a thread or a signal. This project's own test gives itself
`TIMEOUT_SECONDS = 300` (`tests/examples/test_hw1_two_transports.py:95`) for
exactly this reason, and its comment says *"a test runner is a different reader
with a different obligation"* — but every adopter has that obligation too, and
today no seam expresses it. Worth a line in the v0 known-limitations record if it
is not already there.

---

_Reviewed: 2026-08-17_
_Reviewer: Claude Opus 5 (gsd-code-reviewer), depth pass_
_Depth: deep_
_Commit: e3fb143_
