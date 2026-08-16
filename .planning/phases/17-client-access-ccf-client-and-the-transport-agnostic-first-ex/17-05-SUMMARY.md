---
phase: 17-client-access-ccf-client-and-the-transport-agnostic-first-ex
plan: 05
subsystem: client
tags: [client-sdk, result-contract, refusal-semantics, binding-resolution, ast-gate]

requires:
  - phase: 17-04
    provides: "WireRequest / WireOutcome / TransportAdapter, the codec, TransportError"
  - phase: 17-02
    provides: "RefusalEnvelope and RequestIdentity — the shape Refusal names"
provides:
  - "ccf.client exports exactly four names: ProductClient, Result, TransportError, BindingError"
  - "Result carrying either the answer or the refusal, with a fail-closed guard on all six post-assembly fields"
  - "BindingError(TransportError) and RefusedResultError(RuntimeError) — the two things an exception is allowed to mean"
  - "Three-step binding resolution over a plain-dict scheme registry, with no fourth step"
  - "codec.check_outcome — the outcome-level checks the client runs on anything an adapter hands it"
  - "A root-parameterized AST scan proving Result has exactly one construction site"
affects: [17-06 in-process adapter, 17-07 conformance suite, 17-08 first example, 17-10 MCP adapter]

tech-stack:
  added: []
  patterns:
    - "Assertion functions take their subject as a parameter, so a sabotage control can pass a divergent subject into the shipped assertion rather than into a copy of it"
    - "A structural sweep reports a count for every unit it read, including zeros, and RAISES on anything it cannot resolve"
    - "A guard's message enumerates the tuple the tests parameterize over, so the two cannot drift"

key-files:
  created:
    - src/ccf/client/result.py
    - src/ccf/client/binding.py
    - src/ccf/client/client.py
    - tests/client/test_result_guard.py
    - tests/client/test_binding.py
    - tests/client/test_surface.py
    - tests/client/test_client.py
    - docs/surface-changes/17-05-client-surface.md
  modified:
    - src/ccf/client/__init__.py
    - src/ccf/client/errors.py
    - src/ccf/client/codec.py
    - docs/surface/v0.2-surface.json
    - docs/SURFACE-CHANGES.md

key-decisions:
  - "Refusal is an alias for ccf.products.refusal.RefusalEnvelope, not a copy — a field-identical duplicate would need a gate asserting a rename is still a rename"
  - "RefusedResultError is deliberately neither an AttributeError (swallowed by three-argument getattr) nor a TransportError (a retry loop would retry a caller's bug forever)"
  - "Result is not a Pydantic contract: the guard needs attribute access to be a computation, and a declared field is a value that would be readable as None on a refused result"
  - "codec.check_outcome extracted so ProductClient runs the same checks on adapter output — D-11 types the seam as returning a WireOutcome object, so an adapter that never touched the codec can still answer the wrong question"
  - "SCHEME_REGISTRY ships empty; 17-06 registers `inprocess`. The empty case is real today, so it refuses loudly rather than falling through"

patterns-established:
  - "Parameterized subject + divergent-subject control: eighteen controls across four modules, every one observed failing"
  - "Fail-loud sweeps: a root that does not resolve or a file that does not parse raises, never skips"

requirements-completed: [CLNT-01, CLNT-02, CLNT-03, CLNT-04, CLNT-06, CLNT-12]

duration: 2h05m
completed: 2026-08-15
---

# Phase 17 Plan 05: The Client Surface Summary

**Four exported names, a `Result` that carries the answer or the governed "no", a
guard that raises on all six post-assembly fields of a refusal, and a
three-step binding resolution — with eighteen sabotage controls, every one
observed failing on a divergent subject the shipped assertion actually reads.**

## Performance

- **Duration:** ~2h05m
- **Tasks:** 3 of 3
- **Files created:** 8 · **modified:** 5
- **Commits:** 6

## What shipped

### The four names, and nothing else

```
$ PYTHONPATH=src:runtime .venv/bin/python -c "import ccf.client; print(sorted(ccf.client.__all__))"
['BindingError', 'ProductClient', 'Result', 'TransportError']
```

`assert_public_surface(module)` takes a **module object**. The shipped test hands
it the imported `ccf.client`; four controls hand the same function a divergent
one. This is the point the plan was emphatic about and it is worth restating:
the naive control — copy `__init__.py` to `tmp_path`, append a fifth name, assert
the test fails — proves nothing, because the assertion reads `__all__` on the
*imported* package and never looks at the copy.

### The six guarded fields

`GUARDED_FIELDS` in `src/ccf/client/result.py`:

```python
("payload", "debt", "content_address", "replay_ref", "lineage", "expires_at")
```

The guard reads it (`Result._served_or_raise` enumerates it in the message it
raises, so a caller learns every name they must branch before reading), and every
assertion in `tests/client/test_result_guard.py` parameterizes over it. Six
raising assertions, six non-raising ones, six "returns a value and not `None`",
six "survives the three-argument `getattr`" — never one assertion standing for
six.

A second tuple, `PRE_ASSEMBLY_FIELDS`, names the five members readable on either
half, and a partition assertion closes the class in **both** directions: nothing
unclassified, and nothing declared but absent. A seventh property added next year
cannot appear on neither side of the assembly boundary.

### The refusal message, verbatim

```
no binding was given and `CCF_BINDING` is unset, so there is no address to ask —
set `CCF_BINDING` to a scheme-prefixed address such as `inprocess:./deployment`,
or pass `binding=` to `for_product()`. The scheme prefix is the only place a
transport is named, and it lives in the environment rather than in code, so
switching transports stays an ops action
```

**It was not shortened to pass the lint.** `python -m tools.lints --no-hardcoding`
exits 0, and the exemption was *measured* rather than hoped for by scoring the
literal through the checker's own predicates:

| literal | prose candidate | prompt score | developer diagnostic |
|---|---|---|---|
| missing binding | True | **1** (threshold is 2) | True |
| malformed address | True | 0 | True |
| unknown scheme (registry populated) | True | 0 | True |
| unknown scheme (registry empty) | True | 0 | False |

Two independent reasons the first stays green — it scores below the threshold
*and* it carries backticked spans with no second-person pronoun — so there is
headroom rather than a message balanced on one predicate.

### The one `Result` construction site

`count_result_construction_sites(roots)` is an AST walk, not a grep, so an
aliased import (`from ccf.client.result import Result as R; R(...)`) and a
module-qualified call (`r.Result(...)`) are both counted — each has its own
control proving it.

**Measured, on the committed tree:**

```
modules scanned: 240
constructing:    {'src/ccf/client/client.py': 1}
```

## The measurements the definition of done asks for

| Measurement | Value |
|---|---|
| `ccf.client.__all__` | `['BindingError', 'ProductClient', 'Result', 'TransportError']` |
| Guarded field names / where the tuple lives | six, in `src/ccf/client/result.py::GUARDED_FIELDS` |
| Modules scanned by the D-12 scan | **240**, one constructing |
| `command grep -c "decision instant" src/ccf/client/client.py` | **2** |
| `command grep -c "entry_point\|importlib.metadata\|register_scheme" src/ccf/client/binding.py` | **0** |
| `command grep -rn "async def\|await \|import asyncio" src/ccf/client/` | **0 lines** |
| `make typecheck` | `Success: no issues found in 205 source files` |
| `make lint` (`tools.lints --all`) | exit **0** |
| `PYTHONPATH=src:runtime pytest tests/client -q` | **145 passed** |
| Surface gates (drift, completeness, shape capture, class lookup) | **71 passed** |

### Full suite, before and after

Both runs `PYTHONPATH=src:runtime CCF_REQUIRE_HARNESSES=1 pytest -q -p no:randomly`,
in this worktree, at `phase-17` @ `c742e07` and at the final commit.

| | passed | failed | skipped |
|---|---|---|---|
| baseline, no `17-05` file on disk | 3421 | 3 | 118 |
| after `17-05` | **3532** | 3 | 118 |
| **delta** | **+111** | **0** | **0** |

The +111 is exactly the new tests, and it reconciles to the file:

| File | Tests |
|---|---|
| `tests/client/test_result_guard.py` | 51 |
| `tests/client/test_binding.py` | 25 |
| `tests/client/test_surface.py` | 19 |
| `tests/client/test_client.py` | 16 |
| **Total** | **111** |

`tests/client` therefore holds 145 (111 new + `17-04`'s 34, all still passing
after the codec refactor).

## Disputed: the handed baseline, and why three tests fail here and not there

The orchestrator handed **3424 passed / 0 failed / 118 skipped**, honestly
measured in the main checkout. In this worktree the same tree measures **3421
passed / 3 failed / 118 skipped**. Same 3424 total, partitioned differently, and
the difference is not `17-05`'s.

```
FAILED tests/invariants/test_citation_coverage.py::test_the_citation_walk_is_not_vacuous
FAILED tests/invariants/test_citation_coverage.py::test_the_citation_scan_matched_something
FAILED tests/invariants/test_citation_coverage.py::test_the_held_back_thirteen_are_out_of_scope_by_ruling_not_by_accident
```

with `The citation walk read 0 gated files, 953 expected.`

**Cause, measured:** `tools/lints/citations.py` filters on `path.parts` — the
parts of an *absolute* path. Every file in a worktree rooted at
`…/.claude/worktrees/agent-…/` carries `.claude` among its parts, so `DEF-17-03`'s
own repair (adding `.claude` to `SKIP_DIRS`, which is correct in the main
checkout) skips the entire repository when the repository *is* inside `.claude`.
The walk reads zero files.

There is a pleasing symmetry with the lesson the orchestrator handed down, and it
runs the other way: this one fails **closed**. The ratchet fires loudly instead of
reporting a green it did not earn, which is why it is deferrable rather than
urgent. `python -m tools.lints --citations` itself exits 0 in both places.

**Not fixed here, deliberately.** `tools/lints/citations.py` is outside this
plan's `files_modified`, the defect predates it, and six worktrees share that
file. Logged as **DEF-17-06** in `deferred-items.md` with the one-line repair
(filter on `path.relative_to(base).parts` in `iter_scanned_files` and
`repo_index`). Every delta above is stated against the 3-failing baseline for
this reason.

### And the three would pass here too, measured rather than assumed

Leaving it deferred is only defensible if this plan's own prose adds no citation
debt hiding behind a red gate. So the four ratchets were run against **this
committed tree** with `.claude` dropped from `SKIP_DIRS` — which is precisely the
main checkout's behaviour, and changes nothing else about the walk:

| Ratchet | Measured here | Pin | Verdict |
|---|---|---|---|
| gated files read | 1028 | ≥ 953 | pass |
| citations matched | 918 | ≥ 797 | pass |
| sweepable unanchored Python citations | **0** | ≤ 0 | pass |
| held-back citations | **14** | == 14 | pass |
| `citations.check_tree()` findings | **0** | — | pass |

`17-05` contributes **zero** citation sites of any kind — its prose cites
`path.py::Symbol` and backticked module paths throughout, and the held-back
population is unchanged at 14, so the exact-pin test that `17-04` correctly
flagged is untouched by this plan.

## The eighteen sabotage controls, with their observed failures

Each passes a **divergent subject into the shipped assertion function**. None
edits a file under `src/`, `runtime/` or `examples/` — `git status --porcelain`
carries only this plan's own files.

### The guard (`tests/client/test_result_guard.py`) — six

| # | Divergent subject | Observed failure |
|---|---|---|
| 1 | `_LeakyResult`, a `Result` subclass whose `payload` returns `{}` | `AssertionError: reading 'payload' off a refused result returned instead of raising` |
| 2 | the same subject, the other five fields | all five still pass — the leak is detected **for that field specifically**, so the per-field parameterization is not decorative |
| 3 | `_AttributeErrorResult`, whose `debt` raises `AttributeError` | `AssertionError: … raised AttributeError, not RefusedResultError` |
| 4 | `_UnnamedGuardResult`, right type, message naming no field | `AssertionError: … does not name the field` |
| 5 | `_AlwaysRaisingResult`, a guard keyed on nothing, run against a **served** result | `RefusedResultError` — proving the six raising assertions cannot pass vacuously by refusing everything |
| 6 | `_SeventhPropertyResult`, an eighth public property in neither tuple | `AssertionError: ['graph_snapshot_at'] are properties … neither guarded nor declared pre-assembly` |

Control 5 is the one that would have been skipped. Without it, a guard keyed on
the wrong condition satisfies every `pytest.raises` in the module while the
client refuses every answer it ever receives.

### Binding (`tests/client/test_binding.py`) — one, plus the empty-registry case

| # | Divergent subject | Observed failure |
|---|---|---|
| 7 | `source_of(tmp_path / "there-is-no-such-module.py")` | `AssertionError: … is not a readable file, so the no-fourth-step assertion would pass over nothing at all` |

The four `mechanism not in source` assertions are only worth anything if the
source is real; without control 7, renaming `binding.py` would turn
`"entry_point" not in ""` green forever.

Beside it, `test_an_unregistered_scheme_refuses_loudly_on_an_empty_registry`
asserts the *positive* fail-open case: with `SCHEME_REGISTRY` monkeypatched to
`{}`, an `inprocess:` binding still raises rather than falling through.

### The surface (`tests/client/test_surface.py`) — four

| # | Divergent subject | Observed failure |
|---|---|---|
| 8 | `types.ModuleType` with a fifth name `DeploymentManifest` | `AssertionError: … unexpected ['DeploymentManifest']` |
| 9 | a module missing `BindingError` | `AssertionError: … missing ['BindingError']` |
| 10 | a module whose `__all__` names four things it does not bind | `AssertionError: … in '__all__' with nothing bound behind them` |
| 11 | a **real** module loaded via `importlib.util.spec_from_file_location` from `tmp_path`, declaring no `__all__` | `AssertionError: … declares no '__all__'` |

Control 11 is the second construction the plan named, and is the one that proves
the assertion is not quietly satisfied by a module with no surface at all.

### The `Result`-construction scan (`tests/client/test_surface.py`) — eight

| # | Divergent subject | Observed failure |
|---|---|---|
| 12 | `tmp_path` root with **two** constructing modules | `AssertionError: 'Result' must be constructed in exactly one module (D-12) and 2 do: ['…/decoder.py', '…/rogue_adapter.py']` — **both named** |
| 13 | `tmp_path` root with zero constructing modules | `AssertionError: … exactly one module …` |
| 14 | an **empty** directory | `AssertionError: the scan read no modules …, so it proved nothing` |
| 15 | a root that does not exist | `AssertionError: … is not a directory, so scanning it would silently contribute nothing` |
| 16 | a module containing `def (:` | `AssertionError: … could not be parsed …; a file that is skipped is a file that is not checked` |
| 17 | `from ccf.client.result import Result as R; R(...)` | counted as 1 — a grep would have missed it |
| 18 | `import ccf.client.result as r; r.Result(...)` | counted as 1 — binds no local name |

**Controls 14, 15 and 16 are the fail-open family**, and they exist because of the
citation gate that ran green for a full wave of this phase by *dropping* what it
could not resolve. The scan raises on an unresolvable root and on an unparsable
file, and reports a count for **every** module it read including the zeros — which
is what makes "read no modules" distinguishable from "found no sites", and what
makes `len(counts) > 200` a real floor rather than a restatement of the one-site
check.

## Deviations from Plan

### 1. [Rule 3 — plan contradicts the tree] The key link's `decode_outcome` was unreachable; `check_outcome` was extracted instead

**Found during:** Task 3.

The plan's `key_links` require `src/ccf/client/client.py` to reach
`src/ccf/client/codec.py` *"via the one decode path every adapter's output
travels"*, pattern `decode_outcome`. That premise is false against the landed
tree:

```
$ command grep -n "def ask" src/ccf/client/wire.py
275:    def ask(self, request: WireRequest) -> WireOutcome:
```

`decode_outcome(raw: bytes, *, sent)` takes **bytes**; the adapter seam `17-04`
froze returns a `WireOutcome` **object**. The client never holds bytes, so it
cannot call `decode_outcome` at all without gratuitously re-encoding what it was
just handed.

Three options were weighed:

| Option | Cost |
|---|---|
| `decode_outcome(encode_outcome(outcome), sent=request)` | satisfies the pattern literally; ~3× the serialization per `ask`, on every transport, forever |
| re-implement the three checks in `client.py` | duplicates the echo comparison and its message; two spellings of one rule |
| **extract `check_outcome` and call it from both** | one definition, no extra serialization, and `decode_outcome`'s behaviour unchanged |

Taken: the third. `codec.check_outcome(outcome, *, sent) ->
ContextProductContract | None` now holds the echo cross-check, the address
recomputation and the vessel parse; `decode_outcome` calls it and is otherwise
untouched (**all 34 of `17-04`'s codec tests pass unmodified**). The vessel is
returned rather than discarded so the client does not parse the same text twice.

**Why this matters beyond satisfying a link.** Because `D-11` types the seam as
returning an object, an adapter that never went near the codec can hand the
client a well-formed outcome that answers a different question or carries an
address disagreeing with its own bytes. `ProductClient` running the same function
`decode_outcome` runs makes `D-12`'s *"a code path adapters cannot avoid"* a
property of the **checks** as well as of `Result` construction. Two tests in
`tests/client/test_client.py` are conforming-but-lying adapters proving it:
`_CrossedQuestionAdapter` and `_AlteredVesselAdapter`, both of which reach a
`TransportError` and no `Result`.

### 2. [Rule 3 — blocking] `SCHEME_REGISTRY` ships **empty**, not `{"inprocess": …}`

**Found during:** Task 2.

The plan's Task 2 says the registry is *"`{"inprocess": …}` now"*. Measured:

```
$ ls src/ccf/client/
__init__.py  codec.py  errors.py  wire.py
```

There is no in-process adapter to register — `17-06` (wave 4) builds it. The
registry is therefore a module-level dict that starts empty, and `17-06` assigns
into it at import.

This makes the empty case *real today rather than hypothetical*, which is why it
gets its own assertion: an unresolvable scheme against an empty registry raises
with `no transport scheme is registered in this process at all`, never falls
through to a default. A lookup that quietly does nothing when it can resolve
nothing is the fail-open shape this phase has already paid for once.

### 3. [Rule 2 — missing critical functionality] `tests/client/test_client.py` was added

**Found during:** Task 3.

The plan's Task 3 `<files>` names `client.py`, `__init__.py` and
`test_surface.py` only. `test_surface.py` proves the decoder is the *only* place
a `Result` is built and says nothing about whether it is **right** — so the plan
as written ships the single point every transport's answer travels through with
no behavioural test at all, leaving it to `17-06`/`17-07`.

16 tests added: the request that goes out (product id, parameters,
`as_of=None` → absent temporal boundary, `{}` as a real question), the served
half (payload, lineage, `expires_at`, `debt`, `replay_ref`, recomputed content
address, request identity), the refused half (returned not raised, kind/reason/key
carried, the guard firing through the real path), the wire failing, the two
lying adapters, and `for_product` end to end over a registered fake scheme.

### 4. [naming] `RefusedResultError` exists and is not a fifth export

The plan says the guard raises but does not name the exception. `D-03` fixes the
*package* surface at four names, so the negligence exception is declared in
`ccf.client.errors` and is **not** re-exported from `ccf.client`.

Deliberately not an `AttributeError` — the idiomatic choice, and the wrong one:
`getattr(result, "payload", None)` and `hasattr` both convert it straight back
into the silent `None` `D-08` exists to prevent, and there is a per-field test
asserting the three-argument `getattr` cannot swallow it. Deliberately not a
`TransportError` either — a retry loop around `except TransportError` would
re-issue a question whose answer already arrived.

### 5. [design] `Refusal` is an alias, not a client-side copy

The plan says *"`Refusal` exposes `reason`, `key`, `kind`, `detail` and the
request identity — the client-facing reading of `17-02`'s `RefusalEnvelope`."*
The envelope already exposes exactly those, plus `fields`, `request` and
`pre_assembly_lineage`. A parallel type with the same members would need a gate
asserting the two agree — a gate whose whole content is that a rename is still a
rename — and the day it drifted, a client's `refusal.kind` would name a
vocabulary the fabric no longer speaks. So `Refusal is RefusalEnvelope`, asserted
by identity in `test_refusal_names_the_one_canonical_envelope_and_not_a_copy`.

### 6. [design] `Result` is not a Pydantic contract

Every other public shape in this package derives from `CCFContract`. This one
cannot: the guard requires attribute access to be a **computation**, and a
declared Pydantic field is a **value** — a `payload` field would be readable as
`None` on a refused result before any guard code ran, which is verbatim the
defect `D-08` forbids. Validation is not deferred by the choice: the boundary
`Result` sits behind is `WireOutcome` (frozen, `extra=forbid`) and the vessel is
re-parsed as a `ContextProductContract` before it reaches the constructor. The
reasoning is recorded in the module docstring so it is not "fixed" later.

### 7. [deliberate omission] The served vessel's own `temporal_boundary` is not exposed

A caller passing `as_of=None` cannot read back which instant the server used;
`Result.temporal_boundary` is the instant that was *asked* (`None` in that case).
Exposing the resolved one would be a **seventh** post-assembly field, and `D-08`
enumerates exactly six. Not added, because widening the guarded set is a ruling
rather than a convenience. Flagged for `17-06`/`17-07`: the first example passes a
fixed `--as-of` (`D-18`), so it does not need this, but a caller who defers to the
server's clock currently cannot audit which clock it was.

### 8. [required by CI] Surface manifest and fragment

Not in `files_modified` and not a deviation from intent: adding modules with
`__all__` moves the public-surface manifest. Eighteen names crossed
(`ccf.client` × 4, `ccf.client.result` × 4, `ccf.client.binding` × 6,
`ccf.client.errors` × 2, `ccf.client.client` × 1, `ccf.client.codec` × 1), so
`docs/surface/v0.2-surface.json` was regenerated,
`docs/surface-changes/17-05-client-surface.md` written with all seven fields per
entry, and `docs/SURFACE-CHANGES.md` reassembled. Four gates enforce this
(`test_surface_drift`, `test_surface_completeness` in both directions,
`test_surface_shape_capture`, `test_class_lookup`); all 71 pass.

### 9. [environment] The worktree spawned stale and without a `.venv`

`DEF-17-05` again, fourth confirmed instance. HEAD was at `6e95da0` (the phase
15.6 merge, no Phase 17 files at all). Fast-forwarded to `phase-17` @ `c742e07`
(strict ancestor, clean tree, no local commits) and symlinked `.venv` before
starting.

## Threat surface

The plan's register is discharged as written.

- **T-17-15** (a refusal silently returning `None`) — *mitigated*. The guard
  raises on all six post-assembly fields, asserted once per field against a tuple
  both the guard and the tests read, with five controls including the one that
  proves the assertions do not pass vacuously.
- **T-17-16** (`CCF_BINDING` pointing at an attacker-chosen address) —
  *accepted*, unchanged. The binding is process environment inside the
  deployment's own trust boundary; credential machinery is transport-level and on
  the v0 not-list. Recorded rather than omitted.
- **T-17-17** (no principal entitlement check at the client seam) — *accepted*,
  unchanged and deferred to the MCP adapter work. `17-06` makes the exemption a
  named, asserted one.
- **T-17-18** (a second `Result` construction site) — *mitigated*. AST scan, 240
  modules, one site, seven controls including three for the fail-open family.
- **T-17-SC** — holds: **this plan installed no package.**

No new threat surface: no network endpoint, no auth path, no file access beyond
reading `os.environ["CCF_BINDING"]`, and no schema at a trust boundary. The one
environment read is a single named variable whose value is an opaque address the
client never interprets beyond its scheme prefix.

## Known Stubs

**One, and it is declared rather than hidden.** `SCHEME_REGISTRY` is empty, so
`ProductClient.for_product` cannot yet reach any transport — every binding
refuses with "no transport scheme is registered in this process at all". That is
the correct behaviour for a client with no adapter installed, it is asserted as
such, and `17-06` resolves it by registering `inprocess`. No placeholder value
and no unwired path exists anywhere else: every field on `Result` is populated
from the outcome by construction.

## Notes for `17-06`, `17-07` and `17-10`

- **Register your scheme by assigning into `ccf.client.binding.SCHEME_REGISTRY`.**
  The factory receives the address *after* the scheme prefix — `./deployment` for
  `inprocess:./deployment`, `//host/path` for `http://host/path`.
- **Do not build a `Result`.** The AST scan will fail your commit, naming your
  module. Return a `WireOutcome`; `ProductClient._result_from` is the one decoder.
- **`ProductClient` re-runs `codec.check_outcome` on whatever you return**, so an
  outcome whose `request` does not equal the one sent, or whose `content_address`
  does not hash its `product_json`, is a `TransportError` at the client — not a
  mystery three layers down. Round-tripping through `decode_outcome` (D-13) still
  earns its keep; this is the belt beside it.
- **The guard leg of the conformance suite should read
  `ccf.client.result.GUARDED_FIELDS`**, not a copy of the six names. It is
  exported for exactly that.
- **`Refusal` is `RefusalEnvelope`.** Refusal parity across adapters can compare
  the envelope directly.
- The observation in deviation 7 (no resolved server instant on the result) is
  worth raising if the conformance suite wants to assert *"same question, same
  instant"* for a caller who passed `as_of=None`.

## Self-Check: PASSED

All eight created files exist on disk:

```
FOUND: src/ccf/client/result.py
FOUND: src/ccf/client/binding.py
FOUND: src/ccf/client/client.py
FOUND: tests/client/test_result_guard.py
FOUND: tests/client/test_binding.py
FOUND: tests/client/test_surface.py
FOUND: tests/client/test_client.py
FOUND: docs/surface-changes/17-05-client-surface.md
```

All five implementation commits exist on `worktree-agent-a719e265e60663525`,
branched from `phase-17` @ `c742e07`, verified with `git log --oneline`:

```
9e3b8a4 test(17-05): the fail-closed guard, asserted once per field with six controls
998debe feat(17-05): Result, Refusal, and the fail-closed guard
e7bc837 test(17-05): binding resolution — three steps, precedence proven by dispatch
fe5899d feat(17-05): binding resolution — kwarg, then CCF_BINDING, then a refusal
49fa41c feat(17-05): ProductClient, the single Result decoder, and the four-name surface
```

(plus this SUMMARY's own commit.)

Final verification, `make ci-core` run as a whole against the committed tree:

```
$ make ci-core
PYTHONPATH=src:runtime .venv/bin/python -m tools.lints --all
PYTHONPATH=src:runtime .venv/bin/python -m mypy
Success: no issues found in 205 source files
...
FAILED tests/invariants/test_citation_coverage.py::test_the_citation_walk_is_not_vacuous
FAILED tests/invariants/test_citation_coverage.py::test_the_citation_scan_matched_something
FAILED tests/invariants/test_citation_coverage.py::test_the_held_back_thirteen_are_out_of_scope_by_ruling_not_by_accident
3 failed, 3532 passed, 118 skipped, 105 warnings in 370.26s (0:06:10)
```

and separately, `PYTHONPATH=src:runtime pytest tests/client -q` → **145 passed**.

The 3 failures are the pre-existing, worktree-only `test_citation_coverage`
ratchet documented above as **DEF-17-06**; they fail identically on the baseline
with no `17-05` file on disk, and pass in the main checkout.

## Note on state files

`.planning/STATE.md`, `.planning/ROADMAP.md` and `.planning/REQUIREMENTS.md` were
**not** written by this plan. The standing hazard is explicit and has five
confirmed instances: every `state.*` and `roadmap.*` SDK writer corrupts those
files whether it reports success or failure. The requirement IDs this plan
completes are in the frontmatter above (`CLNT-01`, `-02`, `-03`, `-04`, `-06`,
`-12`) for the orchestrator to record by hand.
