---
phase: 18-mcp-transport-the-second-door-and-the-portability-proof
kind: close-fixes-summary
authority: D-IMPL-151 (Dave, 2026-08-17)
subject: the four in-phase blocking findings, plus the B0 claim correction
base: ff8e605b94b459df25d8d1bffececd4ff53eddca
status: complete
date: 2026-08-17
---

# Phase 18 — Close-Review Blocking Fixes

`D-IMPL-151` split the close panel's five surviving blocking findings **4 + 1**.
This is the four, plus the in-phase claim correction for the one that was
deferred. `B0` itself — making the client-seam integrity checks able to fail —
is **not** here, deliberately: it remains an open blocking defect against the
follow-on phase, and the wire shape is untouched.

## The five pieces, and what each turned out to be

| # | Finding | Verdict on the tree | Commit |
| --- | --- | --- | --- |
| `B3` | the closed-set check cannot fail on omission | **true as reported** | `c238258` |
| `B0` | the codec's prose claims a protection the code lacks | **true as reported**; prose corrected, behaviour untouched | `1507e8c` |
| `B0b` | a naive `--as-of` breaks the portability claim | **reproduced exactly**, both exception classes as cited | `a051013` |
| `B1` | replay-ref parity passes on mutual absence | **true as reported**, and demonstrated by sabotage | `8ebd9e3` |
| `B2` | the MCP door defaults what its docstring says it does not | **true as reported**; the JSON-array sub-question resolved *negative* | `510dad8` |

Three further commits are consequences rather than findings: the `D-15B`
migration note (`135a5c7`), an example line-budget repair the gate caught in my
own `B0b` commit (`900420e`), and a regenerated retirement inventory that was
**already stale at the base commit** (`877b1ac` — see *What I found that was not
in the brief*).

**No finding was false.** All five were verified against the tree before being
acted on, per `CLAUDE.md` §3.1.

---

## `B3` — the closed-set check can now fail on an omission

`tests/contracts/test_canonical.py`. `set(carried) <= PERMITTED_CHILD_VARIABLES`
fires on a variable that was **added** and cannot fire on one that went
**missing** — so the module docstring's claim that it *"holds the set closed"*
was half a claim, and a `child_environment` that stopped propagating
`PYTHONPATH` would have reintroduced the `D-IMPL-150` defect this module exists
to have fixed while its own watchdog stayed green.

Extracted `assert_child_environment_is_exactly(carried, expected, when=...)` —
a `D-22`-shaped function over its subject — comparing in both directions and
naming extra and missing separately. Both halves of the test now compare
exactly, the second against a named `PERMITTED_WITHOUT_PYTHONPATH` so the two
halves are two *expectations* rather than one expectation and a subtraction.

**Verified without the fix.** Restoring `<=` inside the assertion:

```
FAILED test_control_a_child_environment_missing_a_variable_is_refused
E       Failed: DID NOT RAISE AssertionError
```

And making `child_environment` stop propagating `PYTHONPATH` turns three tests
red, including `test_the_child_resolves_the_same_ccf_this_test_is_running`.

The first control asserts the pre-`D-IMPL-150` environment **does** satisfy the
old `<=` before showing the new comparison refuses it — so the control cannot
silently stop being the control.

---

## `B0` — the claim corrected, the behaviour untouched

`src/ccf/client/codec.py`, `src/ccf/client/wire.py`. **Prose only.** No wire
shape moved, `DoorOutcome` is unchanged, and neither check's behaviour was
altered — doing any of that here would defeat `D-IMPL-151`'s scoping ruling.

**Amended, not deleted**, per the discipline this phase has now used five times.
The argument for why reconstruction is wrong is exactly right and is kept whole;
what was added is the measured state of the code beside it:

- the module docstring gains a section recording that `DoorOutcome` carries no
  request identity, that both shipped adapters therefore fill
  `WireOutcome.request` from the object the client also passes as `sent`, that
  `check_outcome`'s comparison is consequently an object against itself and
  `verify_content_address` is `sha256(x) != sha256(x)`, and — Dave's
  instruction, stated as a prohibition rather than a caveat — that **the SDK
  must not be described as detecting a transport that answered a different
  question, or a vessel altered in transit, until the follow-on lands**;
- `verify_content_address` and `check_outcome` `Raises:` blocks now say which of
  their documented failures are reachable from a shipped adapter and which are
  not. A `Raises:` promising a `TransportError` that cannot be raised is the
  same false claim in miniature;
- `decode_outcome`'s `Raises:` records that all four **are** reachable there,
  which is what makes it the path the follow-on has to bring the adapters onto;
- `wire.py`'s `WireOutcome.request` and `.content_address` attribute docs — which
  point a reader at exactly this argument — carry the same correction rather
  than being left asserting the property one file away.

**One fact I added that the finding implies but does not state.** `grep` for
`decode_outcome` and `encode_outcome` across `src/`, `runtime/` and `examples/`
returns **no call site at all** outside the codec and two prose references. Both
shipped adapters build a `WireOutcome` object directly — which `D-11` permits,
the seam being typed as returning the object rather than bytes, and which is
exactly the permission that lets the reconstruction in. So the one path on which
these checks would be load-bearing is reached today only by this package's own
tests. That is recorded in the docstring, because *"the codec checks it"* reads
as a live guarantee and is not one.

The **third** check in `check_outcome` — contract validity — is unaffected and
is named as unaffected, so the correction does not overstate the damage.

---

## `B0b` — a naive `as_of` is refused at the seam

`src/ccf/client/wire.py`, `src/ccf/client/client.py`,
`tests/client/test_wire.py` (new), plus the example's flag help and README.

**Reproduced first**, by running the two commands
`examples/hw1-companies-over-revenue/README.md` documents with the offset
stripped off `--as-of`:

```
inprocess:  ccf.contracts.canonical.CanonicalizationError
            "naive datetime is not canonically encodable" (canonical.py:125)
mcp+stdio:  ccf.client.errors.TransportError
            "...answered the product tool with an error rather than an outcome"
```

One caller mistake, two exception classes — and on `mcp+stdio` it was reported
as *the wire never spoke*, which is `D-10`'s inversion: the natural response to
a `TransportError` is a retry, and this question can never succeed.

`WireRequest._temporal_boundary_survives_the_wire` follows
`_parameters_survive_the_wire`'s shape deliberately — same placement, same
docstring structure, same standard for the message (*"the message can name the
wire-stable spelling"*). It admits `None` unchanged, because `None` is the
positive `D-04` assertion *defer to the server's decision instant*; and it
admits **any** offset rather than only UTC, because `D-IMPL-38` refuses an
*ambiguous* instant, not a non-UTC one, and narrowing to UTC would be `D-08`
degradation dressed as a check.

**After the fix both bindings fail identically**, with the same
`pydantic.ValidationError`, before any adapter is reached — verified by
re-running both README commands. `ProductClient.ask`'s `Raises:` block now names
it and says why it is deliberately *not* a `TransportError`.

**Verified without the fix.** Neutering the validator turns 4 of the 13 new
tests red, including
`test_a_naive_as_of_is_refused_before_any_transport_is_reached`, whose adapter
raises if it is reached at all:

```
E  AssertionError: a question the seam should have refused reached a transport —
   WireRequest(product_id=..., temporal_boundary=datetime.datetime(2026, 8, 1, 0, 0))
```

### Should the conformance suite carry a naive-`as_of` case? **No, and the reason is structural.**

The brief invited the question. The answer is that a conformance leg here would
be a leg that cannot fail. The repair's whole property is that the refusal
happens *before an adapter is chosen*, so two subjects would run the identical
validator and agree because they are the same code — not because two transports
were held to a standard. Adding it would be this phase's own defect class,
added deliberately. What the property actually needs is an assertion that **no
transport is reached**, which is non-vacuous with one subject and is
`test_a_naive_as_of_is_refused_before_any_transport_is_reached`. The reasoning
is recorded in the test module's docstring so a later reader does not read the
absence as an oversight. **`suite.py` is untouched.**

### A neighbouring gap found and closed

`_parameters_survive_the_wire` shipped in `17-04` with **no test anywhere in the
tree** — `grep` for its message, for `_unstable_parameter` and for *wire-stable*
across `tests/` returned nothing. A guard whose whole job is to fire, with
nothing watching whether it does. `tests/client/test_wire.py` now covers it
(four unstable types, a nested dotted path, and the converse) alongside the new
guard.

---

## `B1` — replay-ref parity can no longer pass on mutual absence

`tests/client/conformance/test_the_fixture_serves_a_replay_reference.py` (new).

**Where the guard belongs was the whole decision, and it is not `suite.py`.**
Both-`None` is a *legitimate* deployment shape: `served_answer()` returns
`replay_ref=None` for the narrower `ServableProduct` and `door.py` records that
as *"the honest report that this deployment's resolver returned no reference"*.
A suite leg demanding a reference would reject a legitimate deployment on
grounds that have nothing to do with the transport under test, and `suite.py`'s
own contract is to be adapter-agnostic. What must be true is a fact about **this
package's fixture** — that it resolves through a `GovernedResolver`, so a
reference exists for the parity column to be about. Plan `17-10` Task 2 recorded
exactly that precondition in prose and nothing enforced it. The binding is where
the deployment is chosen, so the binding is where the precondition is enforced.

`git diff ff8e605 -- tests/client/conformance/suite.py` is **0 lines.**

The assertion is per-subject, therefore non-vacuous with one subject; it runs
over both real transports, because the reference can be lost in two places (the
deployment stops producing one, an adapter stops propagating one) and only the
pair covers both; and it reports a refusal as its own failure rather than
folding it into "no reference".

**Verified without the fix — this is the demonstration that matters.** Making
*both* sides drop the reference (`served_answer` returning `replay_ref=None` for
`ServedProduct`, and `inprocess.py` sending `replay_ref=None`) reproduces mutual
absence exactly:

```
test_inprocess_conformance.py::test_served_parity                    PASSED  <- vacuous
test_mcp_conformance.py::test_served_parity                          PASSED  <- vacuous
test_every_conformance_subject_serves_a_replay_reference             FAILED
```

An intermediate run is worth recording too: sabotaging **only** `served_answer`
(which the MCP door uses and the in-process adapter does not) produced an
*asymmetry*, and `assert_served_parity` caught it correctly. The parity leg is
not broken — it is blind to the symmetric case, exactly as the finding said.

Three controls (`D-22`), all passing divergent subjects into the **real**
assertion: an adapter that blanks the reference on the way back, an empty
subject collection, and a refusing question.

---

## `B2` — the MCP door stops defaulting `parameters: null`

`runtime/ccf_runtime/mcp/egress.py`, `tests/mcp/test_egress_parameters.py`.

### Which door is right, and why

**The HTTP route's refusal.** `D-08` is that the fabric never silently degrades
a caller's value, and the empty mapping is not a neutral zero here — both doors'
own docstrings record it as the *positive* statement `this question needs
nothing beyond its four axes`. Reading a supplied `null` as that statement
invents an assertion the caller never made, and does it on the argument the
resolver selects a plan from. Widening HTTP to match would satisfy `D-IMPL-133`'s
*"no wider than the other door"* in the direction that **adds** a silent default;
narrowing MCP satisfies it in the direction that does not. So MCP narrowed.

### The repair is in the signature, not the body

`parameters: dict[str, Any] = EMPTY_PARAMETERS` replaces `| None = None`, and
`dict(parameters)` replaces `dict(parameters or {})`. Measured on the generated
tool schema:

| presented | old annotation | new annotation |
| --- | --- | --- |
| omitted | `{}` | `{}` |
| `null` | **`{}` — served** | **refused by the argument model** |
| `{"a": 1}` | verbatim | verbatim |
| `[["a", 1]]` | refused | refused |
| `"x"` | refused | refused |

Omission is unchanged, so a deployment that adopted the tool before `D-IMPL-133`
is unaffected. **Validation stayed at the resolver** (`D-IMPL-121`) — this is
about what the door *carries*, not what it *checks*; the refusal is the argument
model's, in the same place an array or a string was already refused.

`EMPTY_PARAMETERS` is a named constant rather than a `{}` literal in the
signature, so the schema, the handler and the reason for the non-nullable
spelling live in one place and a later reader does not "fix" it back. Pydantic
copies a model's default on every validation (measured), so no call receives the
shared instance, and the handler copies again.

### The table's own defect, also fixed

Its five cases were all well-formed JSON objects **and** the two door callables
`raise`d on a door refusal — so a disagreement of the form *one door refuses
this payload, the other serves it* was outside what the shared table could
represent. That is why it could not see `B2`. `REFUSED_AT_DOOR` is now a verdict
like any other and `EXPLICIT_NULL` a case like any other, giving six. A sentinel
object rather than `None`, because `None` already means *omit the argument*
inside `_tool_arguments` and one spelling for two meanings is how a table stops
saying what it means.

Nothing is weakened: a door that began refusing a well-formed case now
disagrees with the door beside it **by name**, where before it failed only its
own callable; and the non-vacuity guard still demands a **served** case rather
than merely a non-empty table.

**Verified without the fix.** With the two egress lines reverted:

```
AssertionError: the two parameterised doors disagreed —
parameters=null: the MCP tool said 'missing-required-parameter'
                 and the HTTP route said 'refused-at-door'.
```

### The JSON-array question, resolved — **negative**

Cursor asked whether `dict(parameters)` over a sequence of pairs could coerce
`[["a", 1]]` into a mapping the HTTP door would `400`. **Measured: no.** Pydantic
refuses a list for the tool's `dict[str, Any]`-annotated argument under the old
annotation *as well as* the new one, so the array never reached the handler body.
It was unreachable by accident of the argument model rather than by anything the
door did — which is precisely why
`test_neither_door_accepts_a_json_array_as_parameters` now holds it there, and
asserts the handler did not run so the test cannot pass for the wrong reason.

---

## What I found that was **not** in the brief

1. **`make gate-tools` was already red at the base commit.**
   `test_the_committed_report_is_current` failed on a row for
   `.planning/phases/18-.../18-CLOSE-REVIEWS.md`. That file is **byte-identical
   to `ff8e605`** (`git diff` = 0 lines) and I never touched it; the report was
   last regenerated at `2796935` (`D-IMPL-150`), before the close review was
   written. So the *"gate-tools 400 + 154"* baseline handed to this executor did
   not hold — it was 400 + 153. Regenerated with the command the failing
   assertion names (`877b1ac`); the same commit absorbs the line drift my `B2`
   fix caused in `egress.py`. **Recorded rather than quietly absorbed**, because
   a baseline that was wrong is worth more as a finding than as a silent fix.

2. **`_parameters_survive_the_wire` had no test.** See `B0b` above. Closed here.

3. **`decode_outcome` and `encode_outcome` have no call site outside tests.** See
   `B0` above. Recorded in the docstring, not repaired — repairing it is the
   deferred phase's job and doing it here would be the wire-shape change
   `D-IMPL-151` scoped out.

4. **My own `B0b` commit broke the example line budget** (86 against a declared
   80) and `tests/examples/test_client_example_budget.py` caught it. Repaired by
   shrinking the file rather than raising the number (`900420e`) — the gate's own
   message is that changing the number *"is a decision somebody makes on
   purpose"*, and nothing about this work is that decision.

---

## Adjacent prose I corrected beyond the literal citations

Recorded because a correction that stops at the cited line numbers leaves the
same false claim one file away:

- `wire.py`'s `WireOutcome.request` and `.content_address` attribute docs, which
  point a reader at `codec.py`'s argument, now carry the `B0` correction too;
- `egress.py`'s handler docstring paragraph — the *"coerces nothing, defaults
  nothing"* claim — records that it was false for one input until `B2` and where
  the correction lives;
- `tests/mcp/test_egress_parameters.py`'s module docstring gains the "a refusal
  at the door is a verdict" section and the which-door-is-right reasoning;
- `tests/contracts/test_canonical.py`'s test docstring records what the one-sided
  comparison could and could not catch.

---

## Verification

All four gates run **detached**, logs outside the repo, `REAL_EXIT` branched on
rather than a piped exit status.

| Gate | Baseline at `ff8e605` | Now |
| --- | --- | --- |
| `make ci-core` | exit 0 claimed; **actually exit 2** (see finding 1) | **exit 0** — 3871 passed, 118 skipped, 0 failed |
| `make conformance` | exit 0, 63 passed | **exit 0**, 67 passed |
| `make docs-strict` | exit 0 | **exit 0** |
| `make gate-tools` | claimed 400 + 154; **actually 400 + 153, exit 2** | **exit 0**, 400 + 154 |

**Test count: 3850 → 3871, +21, none removed.** The arithmetic reconciles
exactly: `B3` +2 controls, `B0b` +13, `B1` +4, `B2` +2. `conformance` 63 → 67 is
the `B1` module's four.

Working tree clean; no untracked files at any point (the retirement sweep counts
them). All logs written to `/tmp`.

---

## Success criteria

- [x] `B0b`: naive `temporal_boundary` refused at the wire boundary, following
      `_parameters_survive_the_wire`'s shape; both transports verified identical
- [x] `B1`: a non-vacuity guard so replay-ref parity cannot pass on mutual
      absence, demonstrated against a reproduced mutual absence
- [x] `B2`: the doors agree on `parameters: null`; the docstring's claim and the
      code match; the case is in the shared width table; the JSON-array question
      resolved (negative, and asserted)
- [x] `B3`: the closed-set check can fail on omission
- [x] `B0` claim correction: `codec.py` module docstring + both `Raises:` blocks
      amended, not deleted, citing `D-IMPL-151` — plus `decode_outcome` and the
      two `wire.py` attribute docs
- [x] **No wire-shape change**; `DoorOutcome` unchanged; neither check's
      behaviour altered
- [x] `tests/client/conformance/suite.py` **untouched** — `git diff` = 0 lines
- [x] Every fix has a test that fails without it, and the observed failure is
      recorded above
- [x] `ci-core`, `conformance`, `docs-strict`, `gate-tools` all green, detached,
      `REAL_EXIT` branched on
- [x] `STATE.md`, `ROADMAP.md` and `docs/DECISIONS.md` untouched — the
      orchestrator owns those

## Commits

| Commit | Subject |
| --- | --- |
| `c238258` | `test(18)` `B3` — the closed-set check can now fail on an omission |
| `1507e8c` | `docs(18)` `B0` claim correction — the codec's checks are inert today |
| `a051013` | `fix(18)` `B0b` — a naive `as_of` is refused at the seam |
| `8ebd9e3` | `test(18)` `B1` — replay-ref parity cannot pass on mutual absence |
| `510dad8` | `fix(18)` `B2` — the MCP door stops defaulting `parameters: null` |
| `135a5c7` | `docs(18)` `D-15B` migration note for the close-review fixes |
| `900420e` | `fix(18)` keep the hw1 example inside its declared 80-line budget |
| `877b1ac` | `chore(18)` regenerate the retirement-couplings inventory |

## Still open after this work

**`B0` — the client-seam integrity checks remain inert.** Deferred by
`D-IMPL-151` to its own focused follow-on, as an **open blocking defect and not
an accepted risk**. Its sole job: make the request-identity echo and the
content-address check *actually able to fail when a transport answers the wrong
question*. That requires `DoorOutcome` — or the wire form — to carry request
identity, a change across both doors, the adapter and the codec. The claim is
corrected here; the protection is not yet provided.

The ten advisory findings (`A1`–`A10`) in `18-CLOSE-REVIEWS.md` are untouched
and carry forward per `CLAUDE.md` §3.1.
