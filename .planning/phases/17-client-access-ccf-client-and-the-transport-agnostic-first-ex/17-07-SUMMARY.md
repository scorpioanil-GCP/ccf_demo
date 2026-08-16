---
phase: 17-client-access-ccf-client-and-the-transport-agnostic-first-ex
plan: 07
subsystem: testing
tags: [conformance, parity, adapters, sabotage-controls, d-15, d-22, d-23]

requires:
  - phase: 17-05
    provides: the four-name client surface and the single `Result` decoder
  - phase: 17-06
    provides: the in-process adapter, its binding document and its forced boot cache
provides:
  - "`tests/client/conformance/suite.py` — the D-15 parity gate, written once and parameterized over a collection of adapters, naming none of them"
  - "`tests/client/conformance/test_inprocess_conformance.py` — the in-process transport bound in as the suite's first subject, in 150 lines"
  - "`tests/client/conformance/test_the_suite_fires.py` — 40 sabotage controls, every one running the real suite function and every failure message read"
  - "D-23 asserted through the client seam, before 17-08 removes its producer-side home"
  - "DEF-17-07 answered with a measurement and closed as *surfacing not required*"
  - "`make conformance` — the gate by name, without double-running it"
affects: [17-08, 17-09, 17-10]

tech-stack:
  added: []
  patterns:
    - "Cross-subject parity as a *collection* comparison from the first line, with per-subject non-vacuous work so one bound adapter is still a real gate"
    - "Sabotage controls that invoke the real assertion over a deliberately divergent second subject, never a copy of it"
    - "A recording stand-in that logs attribute access, so *which fields a loop exercised* is observed rather than grepped"
    - "A break hook that damages the substrate and returns the same adapter type, asserted, so the wire-failure leg cannot prove itself"

key-files:
  created:
    - tests/client/conformance/suite.py
    - tests/client/conformance/test_the_suite_fires.py
    - tests/client/conformance/test_inprocess_conformance.py
    - tests/client/conformance/conftest.py
    - tests/client/conformance/__init__.py
  modified:
    - Makefile
    - docs/surface/examples/RETIREMENT-COUPLINGS.md
    - .planning/phases/17-client-access-ccf-client-and-the-transport-agnostic-first-ex/deferred-items.md

key-decisions:
  - "The served-parity field list is derived from `Result`'s own declared properties and cross-checked three ways — non-empty, equal to `PRE_ASSEMBLY_FIELDS | GUARDED_FIELDS`, and containing `content_address`"
  - "Each subject gets its **own** provisioned deployment root, so parity is two transports answering independently rather than one graph read twice — and because a second boot against one graph is a second writer"
  - "The break hook damages a root it owns and returns the same adapter type; the leg asserts the type, because a hook that raised `TransportError` itself would prove only that the hook raises"
  - "The D-23 leg checks the content address BEFORE the payload: two payloads cannot share an address, so a payload check placed first would make the address check unreachable"
  - "DEF-17-07 closes without a seventh guarded field — the decision instant is recoverable on both halves and the suite VERIFIES it by pinning and re-asking"

patterns-established:
  - "A leg refuses an empty subject collection by name, because `for subject in ():` is a silent success"
  - "The baseline control (`test_two_honest_subjects_agree`) runs first, because every other control asserts a failure and an expectation of failure is met by any difference at all"

requirements-completed: [CLNT-11, CLNT-12]

duration: 2h05m
completed: 2026-08-16
---

# Phase 17 Plan 07: The Adapter Conformance Suite Summary

**The D-15 parity gate written once over a collection of adapters, with 40 controls that have each been observed failing — including a control proving the suite is not comparing `payload` alone, and three sabotages of the suite itself that the controls caught.**

## Performance

- **Duration:** ~2h05m
- **Tasks:** 3 of 3
- **Files created:** 5 · **Files modified:** 3
- **Commits:** 4

## What shipped

### The suite (`suite.py`, 759 lines)

Seven assertion functions, each taking a `Sequence[AdapterSubject]` and comparing
across it. `AdapterSubject` is a name, a `connect` factory and a `break_transport`
factory — nothing transport-shaped. Adding the MCP adapter in `17-10` is adding one
subject to a tuple.

| Leg | `D-15` row | What it holds |
| --- | --- | --- |
| `assert_served_parity` | 1 | every declared `Result` field, the content address among them |
| `assert_one_question_is_one_address` | 1 / `D-23` | the cross-adapter address form, stated as its own leg |
| `assert_two_parameters_are_two_addresses` | `D-23` | the caller's number is part of the address |
| `assert_refusal_parity` | 2 | `refused`, `reason`, `key`, `kind`, request identity |
| `assert_guard_holds` / `assert_guard_parity` | 3 | all six guarded names, per adapter |
| `assert_wire_failure_parity` | 4 | `TransportError`, no `Result`, same adapter type, and a refusal that does *not* raise |
| `assert_decision_instant_is_auditable` | `DEF-17-07` | the resolved instant is recoverable **and** reproduces when pinned |

### The derived field list

The derivation, verbatim from `tests/client/conformance/suite.py::result_fields`:

```python
declared = tuple(
    name
    for name, member in vars(Result).items()
    if isinstance(member, property) and not name.startswith("_")
)
```

The resulting list, measured (11 fields):

```
('refused', 'refusal', 'product_id', 'parameters', 'temporal_boundary',
 'payload', 'debt', 'content_address', 'replay_ref', 'lineage', 'expires_at')
```

Cross-checked three ways, because a *derivation* that silently returned a short
list is the same defect as a hand-written list nobody updated: non-empty, equal
to `set(PRE_ASSEMBLY_FIELDS) | set(GUARDED_FIELDS)` (measured `True`), and
containing `content_address`. Two controls sabotage the derivation itself.

### The per-adapter "break the transport" hook

```python
def break_in_process(root: Path) -> InProcessAdapter:
    (root / BINDING_DOCUMENT_NAME).unlink()
    return InProcessAdapter(str(root))
```

The hook is handed a root it owns (`provision(f"{name}-broken")`), removes the
binding document so the address names no deployment that can carry a question,
and **raises nothing itself**. `InProcessAdapter.ask` turns that into a
`BindingError`, which is a `TransportError` by inheritance. For `17-10` the same
hook closes the pipe. The leg asserts `type(broken) is type(healthy)`, so a hook
that substituted an always-raising object is caught — one of the ten controls.

## Every control's observed failure message

Read by re-running each sabotage outside pytest and printing what it raised.
*A control whose failure message was never read is a control nobody has checked.*

**1. Served parity — a moved vessel field** (`expires_at` +1s, honestly re-addressed)
> the `served parity` leg found the transports disagreeing — `content_address`: inprocess answered '1506f1e2…' and moved-expiry answered 'adaadab9…'; `expires_at`: inprocess answered `datetime(2026, 3, 2, 12, 10, tzinfo=TzInfo(0))` and moved-expiry answered `datetime(2026, 3, 2, 12, 10, 1, …)`.

**2. THE NAMED TRAP — payload agrees, address does not** (`plan_id` moved; `plan_id` is a vessel member and *not* a `Result` field)
> the `served parity` leg found the transports disagreeing — `content_address`: inprocess answered '1506f1e2…' and payload-agrees answered '1b733b74…'.

**`content_address` is the only difference reported.** Payload, debt, lineage,
`expires_at`, `replay_ref` and the request identity are all identical across the
pair. A suite comparing `payload` alone passes this control; this one does not.

**3. Refusal parity — a dropped key**
> the `refusal parity` leg found the transports disagreeing — `refusal.key`: inprocess answered 'minimum_score' and dropped-key answered None.

**4. Guard leg — six controls, one per name.** Identical shape, one per field:
> `recorder` handed back ['payload'] on a refused result instead of raising `RefusedResultError` …

and the same for `debt`, `content_address`, `replay_ref`, `lineage`,
`expires_at`. Plus `test_the_guard_leg_touches_every_guarded_name`, which asserts
the recording stand-in's logged access list **equals `GUARDED_FIELDS` in order**
— observed, not grepped.

**5. Wire failure — a swallowing adapter**
> `swallows` answered a broken transport with a refusal instead of raising `TransportError` — a wire that never spoke reported as a governed answer is the one inversion `D-10` exists to prevent.

**6. Wire failure — a hook that substitutes the adapter**
> `substitutes` broke its transport by substituting a `_AlwaysDead` for a `InProcessAdapter` — the hook must damage the substrate and leave the adapter alone, or this leg proves only that the substitute raises.

**7. Wire failure — a transport that raises on a refusal**
> `TransportError: this transport calls a refusal a failure`

(The leg's healthy-refusal half is what lets this escape; without it, a transport
that raised on everything would pass.)

**8. `D-23` — a projection that ignores the caller's number**
> `ignores-the-threshold` gave two different parameter values one content address, `b49ce33b…` — the caller's number is part of the question and therefore part of the product's address, and a transport where it is not is serving a precalculated object.

**9. `D-23` cross-adapter — two transports, two addresses**
> the `one address` leg found the transports disagreeing — `content_address`: inprocess answered '1506f1e2…' and re-addressed answered '1b733b74…'.

**10. `DEF-17-07` — a misreported decision instant** (anchor moved one second)
> `misreports-its-instant` reported answering at `datetime(2026, 3, 2, 12, 0, 1, …)`, but asking the same question pinned to that instant produced `99acbc33…` rather than `0d051339…` — the reported instant is not the instant that answered.

**11. `DEF-17-07` — a question that pins its own instant**
> this leg asks with `as_of=None` on purpose — handed a question that already names its instant, it would recover the value it was given and prove nothing about what the server resolved.

**12. Every leg, an empty collection** (seven, one per leg, parameterized)
> the `served parity` leg was handed no adapters — an empty collection iterates to a silent success, which is a parity gate reporting green while comparing nothing.

**13. Served parity — an unresolvable deployment**
> `BindingError: …/01-unresolvable/deployment carries no 'binding.yaml', so there is nothing naming this deployment's config or its resolver.`

(Red, not shorter — the leg does not skip what it cannot reach.)

**14. Served parity — a subject that refuses**
> `inprocess` refused the served-parity question with `missing-required-parameter` — this leg compares two served answers …

**15. Guard parity — nothing refused to read a guarded field off**
> `inprocess` answered the refusing question, so this leg had no refused result to read a guarded field off.

**16. Two parameters — one parameter mapping handed over twice**
> this leg was handed one parameter mapping twice, so it would compare a question against itself …

**17. Served parity — two subjects answering to one name**
> two subjects answer to the name `inprocess` — a parity report that cannot tell them apart names the wrong transport when it fails.

## Sabotaging the suite, and watching the controls catch it

The controls are themselves verification code, which is where this project's
defects land. So the suite was deliberately weakened three times:

| Sabotage applied to `suite.py` | Result |
| --- | --- |
| served parity narrowed to `_view_of(result, ("payload",))` | **2 failed, 45 passed** — `test_served_parity_fires_on_a_moved_field` and `…_when_only_the_content_address_differs` both `DID NOT RAISE` |
| guard leg narrowed to `for field in GUARDED_FIELDS[:1]` | **6 failed, 41 passed** — the recording control plus five of six per-field controls |
| wire-failure refusal half pointed at `broken` instead of `healthy` | **1 failed, 46 passed** — the binding module's own `test_wire_failure_parity` went red with a `BindingError` |

`suite.py` was restored from a byte copy and re-verified at **47 passed** after each.

## `DEF-17-07` — answered with a measurement, closed

**The question Dave ruled must be answered this wave:** *can a caller audit which
instant the server resolved, using only what a `Result` already exposes?*

**Yes, on both halves.** Measured against the fixture deployment with `as_of=None`:

| Half | Path | Measured |
| --- | --- | --- |
| served | `result.lineage.graph_snapshot_at` | `2026-03-02T12:00:00+00:00` |
| refused | `result.refusal.request.temporal_boundary` | `2026-03-02T12:00:00+00:00` |
| either | `result.temporal_boundary` | `None` — the **question's** echo |

`Result.temporal_boundary` being `None` is correct: it is the boundary the
caller named, echoed back and cross-checked in transit. The server's answer is
one level in.

**Recovering is not auditing, so the suite verifies.** Asking the same question
pinned to the recovered instant reproduces the identical content address —
measured `pinned reproduces address: True` — and the sabotage control that moves
the reported anchor by one second turns the leg red. That mechanizes exactly what
Dave asked for: *"the conformance suite is exactly where what every adapter must
expose identically gets mechanized."*

**Closed as *surfacing not required*.** `D-08`'s six guarded fields are unchanged
and no seventh was added. `deferred-items.md` carries the full measurement, the
mechanism trace through `ccf.products.resolver::GovernedResolver.__call__`, and
the condition that would reopen it with evidence.

## `D-23` — landed before its old home is removed

`tests/examples/test_s1_00_output.py` **still exists and still passes: 9 passed
in 4.01s**, verified at the end of this plan. The property is now asserted in
both places, which is the point of the ordering — `17-08` may remove the module
without the property being unasserted in between.

Both producer-side assertions were carried, not one:

| Producer-side | Client-seam replacement |
| --- | --- |
| `test_two_thresholds_are_two_products` | `assert_two_parameters_are_two_addresses` |
| `test_the_same_question_is_stable` | `test_two_honest_subjects_agree` (two roots, one transport, one address) |

The second was not in the plan and was added because every control asserts a
*failure*, and without a baseline proving two fixture copies are comparable at
all, ten green controls would be evidence of nothing.

The two thresholds are computed from the fixture's own seeded scores
(`_SCORES[0] + 1` and `_SCORES[1] + 1`), so the pair cannot stop partitioning the
rows differently the day the fixture data changes.

## Reachability — asserted, not assumed

**Mechanism used:** `test_the_conformance_suite_is_inside_the_default_collection`
reads `pyproject.toml` with `tomllib` and asserts (a) `testpaths` is non-empty,
(b) the conformance directory `is_relative_to` one of them, (c) no `addopts` and
no `norecursedirs` are configured, (d) at least one `test_*.py` module exists in
the directory, and (e) no `conftest.py` between the repo root and the suite sets
`collect_ignore`. A sibling test holds the `Makefile` target's path and the
directory to each other.

**Collected count, measured directly:**

```
$ PYTHONPATH=src:runtime .venv/bin/python -m pytest --collect-only -q | grep -c "tests/client/conformance"
47
```

47 node ids appear in the **default** collection (no path argument), which is the
collection `make ci` runs. `make conformance` is therefore a name, not a second
path — it is deliberately **not** a prerequisite of `ci`.

## Suite neutrality — asserted over the AST

`test_the_suite_imports_no_adapter` parses `suite.py` and asserts no import path
contains `ccf.client.adapters`. `test_the_suite_names_no_registered_scheme`
asserts no string constant in it is a key of `ccf.client.binding.SCHEME_REGISTRY`
— held against the live registry, so a scheme registered later is covered without
an edit. Both are AST scans rather than greps, because that module's own
docstring explains at length that it names no adapter and a grep would be
counting the explanation.

`test_every_exported_leg_has_a_control_here` holds `suite.__all__` and this
module's control table to each other, so an eighth property added later goes red
rather than quietly being uncovered.

## Deviations from plan

**1. [Rule 3 — blocking] `make gate-tools` was already red on the branch tip.**
`docs/surface/examples/RETIREMENT-COUPLINGS.md` was last regenerated in `17-03`
(`448e51b`); `src/ccf/client/adapters/binding_document.py` landed in `17-06`
(`05c2db7`). Five of the eight rows the regeneration added belong to waves 3
and 4, three to this plan. Regenerated with the tool's own documented remedy;
`make gate-tools` now reports **144 passed**. Logged as `DEF-17-08`, because the
structural cause — `gate-tools` joined `ci` in `17-01` but not `ci-core`, and
`ci-core` is what every wave's verification block runs — is a decision above this
plan. Commit `150b4b2`.

**2. [Deviation] The plan's four files became five: `conftest.py` was added.**
The `provision` fixture is needed by both the binding module and the controls.
Putting it in either would have made the other import from a test module; a
package-local `conftest.py` is the clean answer and keeps
`test_inprocess_conformance.py` at the 150 lines the plan wanted.

**3. [Deviation] The provisioner hands out a *distinct directory per call*
rather than refusing a repeated name.** The plan's shape was a uniqueness guard;
the first version of it broke `test_two_honest_subjects_agree`, which runs two
legs in one test and legitimately provisions `inprocess` twice. **The tree
disputed the design and the tree won:** sharing a graph is now impossible by
construction (counter-prefixed paths), and the hazard that actually needed
refusing — two *subjects* answering to one name — is refused in `_ask_each`,
which is the thing that would otherwise report one transport's answer under
another's. Control 17 covers it.

**4. [Deviation] `assert_two_parameters_are_two_addresses` checks the content
address before the payload.** The first draft checked the payload first "to make
the address difference attributable". That made the address assertion
**unreachable** — the codec recomputes the address from the vessel's own bytes,
so two differing payloads cannot share an address, and a payload check placed
first would always fire first. A check that can never fail, dressed as a check,
is the exact defect class this plan exists to avoid. Reordered; the payload check
is now live for the remaining real case (addresses differ, payloads identical).

**5. [Addition] A fifth and sixth leg beyond the plan's four.**
`assert_one_question_is_one_address` (`D-23`'s cross-adapter form, stated as its
own leg because it is the half a reader checks first) and
`assert_decision_instant_is_auditable` (`DEF-17-07`'s mechanization, which Dave's
ruling required to land in this suite).

**6. [Note] Tasks 1 and 2 were committed together.** `D-23`'s assertions live
inside `suite.py` alongside the four properties; splitting the file across two
commits would have committed a syntactically complete but property-incomplete
suite. Commit `b1d9e9f` names both.

## Verification

| Command | Before | After |
| --- | --- | --- |
| `make test` | 3595 passed, 118 skipped | **3642 passed, 118 skipped** |
| `make conformance` | *(target did not exist)* | **47 passed in 3.6s** |
| `make lint` | exit 0 | **exit 0** |
| `make typecheck` | exit 0 | **Success: no issues found in 208 source files** |
| `make gate-tools` | **1 failed, 143 passed** | **144 passed** |
| `make docs-strict` | exit 0 | **exit 0** |
| `pytest tests/examples/test_s1_00_output.py` | 9 passed | **9 passed** |

**Delta derivation:** 3642 − 3595 = **+47**, exactly the conformance suite's
collected count (7 in `test_inprocess_conformance.py` + 40 in
`test_the_suite_fires.py`). No pre-existing test changed state.

## Commits

- `b1d9e9f` — `test(17-07): the adapter conformance suite, and D-23 on its new path`
- `f3993b1` — `test(17-07): prove the conformance suite fires — 40 controls, every one observed`
- `55a9c0d` — `docs(17-07): answer DEF-17-07 with a measurement — surfacing not required`
- `150b4b2` — `chore(17-07): re-measure the retirement couplings, and log why nobody saw them`

## What `17-10` inherits

Adding the MCP adapter to this gate is:

```python
SUBJECTS = (
    AdapterSubject(name=SCHEME, connect=..., break_transport=...),
)
```

in one new module. `suite.py` does not change. If it has to, the suite was not
adapter-agnostic and the change is the finding.

## Self-Check: PASSED

- All five created files present under `tests/client/conformance/`.
- All four commits (`b1d9e9f`, `f3993b1`, `55a9c0d`, `150b4b2`) found in `git log --oneline --all`.
- `conformance` present in `Makefile` `.PHONY` (line 29) and as a target (line 85) running `pytest tests/client/conformance -q`; **not** a prerequisite of `ci` (line 105: `ci: ci-core examples docs-strict gate-tools`).
- Every number quoted above was measured in this session, not carried from the plan.
