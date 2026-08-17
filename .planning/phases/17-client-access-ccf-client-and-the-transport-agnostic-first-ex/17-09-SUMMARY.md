---
phase: 17-client-access-ccf-client-and-the-transport-agnostic-first-ex
plan: 09
subsystem: examples
tags: [client, examples, purity-gate, budget-gate, sabotage-controls, d-impl-141, d-impl-137, d-impl-136]
status: CHECKPOINT — tasks 1-3 complete, task 4 blocking-human, TWO GATE FAILURES SURFACED
requires:
  - "`ccf.client` — the four-name surface (17-01..17-06)"
  - "`ccf.products.resolver.build_governed_resolver` — 17-13"
  - "`ccf.client.adapters.binding_document` — the data-only binding document, 17-12"
provides:
  - "`examples/hw1-companies-over-revenue/` — consume.py, an opaque deployment/, a README"
  - "`tests/examples/test_client_example_purity.py` — the AST purity gate + the T-17-35 command-identity assertion"
  - "`tests/examples/test_client_example_budget.py` — the budget gate"
affects:
  - "`Makefile` — new `example-hw1` target"
  - "`tests/examples/test_artifact_schema_headers.py` — the single-file-config boundary, stated"
  - "17-08 — see `## The 17-08 gate` below. The answer is NO."
tech-stack:
  added: []
  patterns: ["subject-as-parameter gates", "vacuity-as-failure", "AST over regex"]
key-files:
  created:
    - examples/hw1-companies-over-revenue/consume.py
    - examples/hw1-companies-over-revenue/README.md
    - examples/hw1-companies-over-revenue/deployment/ccf_config.yaml
    - examples/hw1-companies-over-revenue/deployment/binding.yaml
    - examples/hw1-companies-over-revenue/deployment/scenario.yaml
    - examples/hw1-companies-over-revenue/deployment/projection.py
    - examples/hw1-companies-over-revenue/deployment/.gitignore
    - tests/examples/test_client_example_purity.py
    - tests/examples/test_client_example_budget.py
  modified:
    - Makefile
    - tests/examples/test_artifact_schema_headers.py
decisions:
  - "The deployment is sqlite, not postgres — measured, not preferred: `postgres_write.py::secret_fields` is empty and `binding.yaml`'s `connection:` has no `from_env` form, so a Postgres deployment cannot be authored without a DSN literal in the tree"
  - "No `backends.yaml` and no `resolver.py` — both were in the plan's `files_modified` and both are the pre-17-12 shape"
  - "`EXAMPLE_ROOT_MARKER` NOT widened — the widening the plan asked for cannot hold; the boundary is asserted instead"
metrics:
  duration: one session
  completed: 2026-08-16
---

# Phase 17 Plan 09: The First Example Summary

`examples/hw1-companies-over-revenue/` — a 78-line `consume.py` importing
`ccf.client` and stdlib, an opaque `deployment/` holding one Python module, and
two CI gates with fifteen sabotage controls, six of which are vacuity controls.

**STATUS: CHECKPOINT ANSWERED BY DAVE; ALL FIVE FAILURES CLOSED.** The plan is
complete. `make ci-quick-suite` **exit 0**, `make gate-tools` **exit 0**,
`tools.lints --all` **0**, `make docs-strict` **0**, `make typecheck` **0**.

The five failures were raised at the checkpoint rather than fixed unilaterally,
because all five were gates pinning a population at exactly one member *so that
the second member is red and a human looks* — and this example was that second
member. Dave ruled; the rulings and the work they authorized are in
`## Dave's rulings` and `## Closing the five failures` below.

---

## Dave's rulings (2026-08-16, at the Task 4 checkpoint)

| # | Question | Ruling |
|---|---|---|
| 1 | sqlite vs Postgres / a `from_env` form | **Accept sqlite for the first example.** *"Keeping a DSN literal or forcing Postgres would put credentials or extra machinery into the tree. sqlite is the lowest-friction substrate for 'first answer.' `from_env` support can be added later when a real Postgres deployment is needed; it is not required for this example."* **No code change.** |
| 2 | The `D-IMPL-137` exemption / the second projecting example | **Teach the detector the post-`build_governed_resolver` shape. DO NOT raise the ceiling.** This was the work. |
| 3 | Transport inversion costing one import naming a scheme | **Intended, no change.** *"The scheme belongs in the binding/adapter layer, not in client code. One import that names the scheme inside the official adapter is the correct and expected cost of the design."* |
| 4 | `17-08` and the resolver-seam citations | **The entire removal of `s1-00`/`s1-01` is DEFERRED OUT OF PHASE 17.** Neither tree deleted, no seam docstring edited, none of `17-08`'s files touched. |
| 5 | The three retirement-sweep failures | **Handled with #2** — *"the same population-pinning gates firing because a second projecting example now exists… not independent defects."* |

Ruling 4 also settles the `## The 17-08 gate` section below: its finding stands
on the record, and the removal it blocks is no longer Phase 17's problem.

---

## Closing the five failures

### The specification was my own measurement

`test_every_projecting_example_body_names_the_binder` demanded that
`build_projection()` call `refuse_operator_set_divergence`, while
`_binder_collapses` **property (1) in the same module** refuses exactly the call
that demand would produce. The detector was written when a deployment computed
`required=` itself and could be caught reading the product class's claim. Under
`D-IMPL-141` the deployment writes one module and
`~ccf.products.resolver.build_governed_resolver` hands it the operator set as a
**parameter**, already derived from the registered class.

Instrumented on the shipped scope, before the fix:

```
scope       : build_projection() line 118
root        : examples/hw1-companies-over-revenue/deployment
registers   : False
class_claim : None          <- no ProductLineage in this body to read
plan_sources: {}            <- the construction is a `return`, not an assignment
one_document: False         <- both fail-closed branches fire
names_binder: False
```

Two independent blind spots, both correct for the shape they were written for.

### What was built: a second route, not a wider one

**`_sdk_supplied_operator_set(scope, path, plan_classes)`** — a *separate*
premise-failure route, joined to the first by `_premise_is_false()` at the
demand site and at `_binder_collapses`. Five **positive** conditions, every one
a fact readable from the tree rather than a gap in it:

1. the body sits in a deployment with a Control Plane authoring surface;
2. that deployment registers no `ccf.projection-requirements`;
3. **the deployment's `binding.yaml` names this module and this function**
   through its single permitted `plan:` reference — the Control Plane saying, on
   disk, that the SDK reaches this function;
4. the function declares the seam's operator-set parameter;
5. every plan it constructs is built from **that parameter**, at least one and
   none from anywhere else.

Condition 3 is the load-bearing one and it is why this is not an inference from
absence. `BINDING_DOCUMENT_NAME` and `REFERENCE_KEYS` are **imported from the
SDK**, not respelled, with
`test_the_binding_documents_reference_surface_is_still_one_key` refusing to let
the import go stale. `_constructed_plan_sources` reuses
`_is_plan_construction`, `_keyword` and `_path` — the same primitives
`_plan_sources` uses — so the two cannot disagree about *what* a plan
construction is, only about which statement forms carry it.

### THE CEILING STAYED AT ONE — both of them

`MAXIMUM_ONE_DOCUMENT_DEPLOYMENTS` is **unchanged at 1** and its claimant list
is still exactly `["examples/s1-00-companies-over-revenue"]`. The new route gets
its **own** ceiling, `MAXIMUM_SDK_SUPPLIED_DEPLOYMENTS = 1`, also with no
headroom.

They are separate because the claims are different in kind: row B is a
deployment that authored **one** document where two were possible; this is a
deployment that authored **none**, because it has no operator set of its own to
author. One shared counter would let either population grow into the other's
headroom while both ceilings read green — so
`test_the_two_exemptions_are_disjoint` asserts no deployment claims both, which
is what makes two ceilings of one bound two populations rather than one of two.

### Nothing was narrowed to pass

`test_the_premise_detector_reads_the_shipped_tree_correctly` came out
**stronger**. It used to assert a one-name list. It now asserts *set equality*
between the roots registering no requirements and the union of the two claimant
lists — i.e. **no root escapes the demand unexplained**, which is `D-IMPL-137`
**row C** and is precisely what must never appear quietly. The two per-route
named assertions are kept on top of that.

### The three retirement-sweep failures — cause proven both ways

The committed report at `6d695b1` carried exactly one `inline-tree-witness`
row: `test_the_plan_recognition_refuses_an_unrelated_required_keyword`,
`witnesses = 1`, sustained solely by `examples/03-harness-portability`. This
plan's example is a **second witness that nothing retires**, so the scan gained
headroom and the row correctly dissolved.

Proven by causing it in both directions, not inferred:

```
with hw1 present : inline-tree-witness rows: 0
with hw1 PARKED  : inline-tree-witness rows: 1
                   tests/products/test_gate_two_call_shape.py | line 4300
                   | examples/03-harness-portability | witnesses 1 | owner 16-15
```

So the sweep was telling the truth and three tests pinned the previous truth.
Restated, each to what is now true:

- **`test_every_no_path_token_shape_is_accounted_for_at_head`** (was
  `test_all_four_…_are_present_at_head`). Every no-path-token shape is in
  exactly one of two named sets — present at HEAD, or absent **with the
  measurement that put it there**. Both directions refused, so the set of
  shapes the real tree exercises can neither shrink nor grow without a
  deliberate edit. A gate that goes red when its subject *improves* teaches the
  reader to edit the gate; this one records the improvement and stays a gate.
- **`test_the_inline_tree_witness_coupling_dissolved_rather_than_vanished`**
  (replaces `…_row_is_owned_three_waves_early`, whose subject no longer
  exists). An empty row list is what a dissolved coupling looks like **and**
  what a deleted subject looks like **and** what a broken detector looks like.
  Only the first is good news, so all three are distinguished: the row set must
  be empty, the module must still exist, and it must still carry the scanning
  assertion the row was filed against. The detector itself stays exercised by
  `test_shape_3_produces_a_row`, which builds the shape under `tmp_path` and
  asserts one row with the right path, witness count and owner.
- **`test_the_gate_two_module_carries_rows_with_two_different_owners`** —
  scope corrected from three hand-picked shapes to the module's whole row set.
  Its docstring's claim is *"a report that gave the whole module one owner
  would hand a plan a red build it had no notice of"* — a claim about the
  sweep's **per-row** ownership resolution, not about any particular pair of
  shapes. The old filter drew its second owner from the inline row; narrowing
  the claim to fit the remaining rows would have been the gate edited to pass.
  Four distinct owners remain and the stated property holds.

### What each touched gate does on ZERO matches — asked, and answered

Every one fails. `per_row_ownership_problems([])` returns a violation rather
than passing an empty `len(owners) >= 2`. `shape_accounting_problems` over an
**empty census** — a broken walk, a moved tree — returns three violations
rather than satisfying every absence claim, which is the shape a gate built
only from absence claims would have silently passed.
`_sdk_supplied_operator_set` returns `False` for a factory that constructs no
plan, because `all(...)` over an empty tuple is `True` and the explicit
emptiness guard is what stops the exemption reaching every function the binding
document happens to name.

### Sabotage: the new detector cannot recognise nothing, or everything

Neutering `_sdk_supplied_operator_set` at its first statement, both directions:

| Sabotage | Result |
|---|---|
| `return False` — recognises **nothing** | `3 failed, 93 passed`. Named: `test_the_sdk_supplied_route_recognises_the_shipped_shape`, plus both original failures returning — *"the D-IMPL-141 route no longer recognises the shipped example, so the exemption it grants is granted to nothing and the controls below would all pass over a detector that matches zero bodies"* |
| `return True` — recognises **everything** | `19 failed, 77 passed`, including every condition control, `test_a_second_operator_set_outside_the_control_plane_is_refused` and `test_the_binder_argument_checks_reject_a_binder_that_cannot_fail` |

Restored: `command grep -c "SABOTAGE" …` → **0**, `96 passed`.

### Every round-2 control, with its observed message

| Control | Observed |
|---|---|
| no `binding.yaml` at all | `_sdk_supplied_operator_set -> False` |
| `binding.yaml` names a different module | `False` |
| `binding.yaml` names a different attribute | `False` |
| `binding.yaml` has no `plan:` reference | `False` |
| no Control Plane authoring surface | `False` |
| deployment **registers** `ccf.projection-requirements` | `False` — two documents means two documents, whatever the file layout |
| plan built from another source (**row C**) | `False` — the demand stands |
| **VACUITY** — factory builds no plan | `_constructed_plan_sources -> ()`, then `False` |
| **CEILING** — a second `D-IMPL-137` claimant | `2 deployments claim the D-IMPL-137 one-document exemption, 1 permitted. …` |
| **CEILING** — a second `D-IMPL-141` claimant | `2 deployments claim the D-IMPL-141 SDK-supplied exemption, 1 permitted. …` |
| shape recorded present with no HEAD row | `no \`indirect-execution\` row at HEAD, but it is recorded as present — the detector is now unexercised against the real tree.` |
| shape recorded absent that reappeared | `` `inline-tree-witness` has a row at HEAD again, but it is recorded as absent… a returning coupling is news.`` |
| shape in neither set | `no-path-token shapes in neither set, so nothing accounts for them: ['indirect-execution', 'inline-tree-witness']` |
| **VACUITY** — an empty shape census | three violations, one per present-recorded shape |
| dissolution — subject module deleted | `…is gone, so an empty row set says nothing about headroom — the subject was DELETED instead` |
| dissolution — scanning assertion deleted | `…no longer carries the scanning assertion the row was filed against, so the detector returning nothing is a DELETION rather than the headroom claimed here` |
| dissolution — a returning coupling | `the inline-tree-witness coupling is back; restore the wave-8 ownership assertion this test replaced.` |
| **VACUITY** — ownership over an empty row set | `…carries no coupling rows at all, so nothing here demonstrates per-row ownership` |
| ownership — every row one owner | `every coupling row in one module resolved to a single owner, which is what a per-file ownership rule would produce and a per-row one would not: ['16-17']` |

### Final verification, exit codes captured directly and branched on

| Command | Exit | Result |
|---|---|---|
| `make ci-quick-suite` | **0** | `3739 passed, 2 skipped, 172 deselected` in 376.30s |
| `make gate-tools` | **0** | `154 passed` (baseline 144, `+10` controls) |
| `tools.lints --all` | **0** | — |
| `make docs-strict` | **0** | — |
| `make typecheck` | **0** | `Success: no issues found in 209 source files` |

**Delta accounted, end to end.** Main-checkout baseline at `6d695b1`:
**3695 passed**. Round 1 (the example and its two gates) added **+29**, measured
by parking each change and re-collecting (3697 → 3726 collected). Round 2 added
**+15**, all in `tests/products/test_gate_two_call_shape.py` (81 → 96
collected): the new route's conditions, the two vacuity controls, the second
ceiling and the disjointness assertion.

**3695 + 29 + 15 = 3739**, exactly, with **0 failures** where there were 2.

`tools/docs_tests` is not in `ci-quick-suite` (`testpaths = ["tests"]`), so the
**+10** controls added to `test_retirement_sweep.py` land in `make gate-tools`
instead: **22 → 32** in that module, **144 → 154** for the target.

**The report was re-swept AFTER this file was written**, per the ordering
hazard — the sweep walks the planning tree and reads this SUMMARY, so
regenerating before writing it is what left `gate-tools` red twice earlier
today. Committed and live now agree at **232 rows across 73 files**.

---

## The plan was stale in four named places

The plan predates `17-11`, `17-12` and `17-13`. Every dispute below carries a
measurement.

### 1. `deployment/resolver.py` — the plan's `files_modified` names a shape that was removed

`REFERENCE_KEYS` is `("plan",)`, a one-element tuple, and `RULED_OUT_KEYS`
refuses `resolver:` **by name**:

```
REFERENCE_KEYS ('plan',) len 1
RULED_OUT_KEYS ['connection_factory', 'resolver']
```

Not written. The deployment holds **one** Python module, `projection.py`,
modelled on `tests/client/fixtures/deployment/`.

### 2. `backends.yaml` — not written, and the reason is a measurement

The plan wanted `backend: postgres` against the FIBO stores with `backends.yaml`
holding variable *names* only. Measured, that cannot be authored:

```
postgres secret_fields= set()
sqlite   secret_fields= set()
```

`backend_secrets:` refuses a reference to a field the adapter does not declare
as a credential field (`manifest.py::_refuse_undeclared_secret_fields`), and the
Postgres adapter declares **none**. And `binding.yaml`'s `connection:` supports
exactly two value forms — a scalar carried verbatim, or `{path: …}` resolved
against the root (`binding_document.py::_connection`). **There is no `from_env`
form.** So the only way to give the Postgres adapter a DSN is a literal in the
tree, which Task 1's own acceptance criteria and CLAUDE.md §2.2 both forbid.

`sqlite` via `{path: …}` is the one backend the post-`17-12` binding document
can express with no value in the tree. That is what shipped.

**The FIBO host was probed, not assumed.** `192.168.4.76:5432` accepts TCP
(exit 0). It is unusable here for two independent reasons: `psycopg` refuses
with `fe_sendauth: no password supplied` and no credential is available to this
executor; and per `MEMORY.md`, each FIBO store holds a **hand-built layout, not
CCF's** — "it is not drop-in fixture data". A CCF graph adapter pointed at it
would not find a CCF graph. I did not attempt to guess credentials.

**This is the checkpoint's first question for Dave** — see `## For Dave` item 1.

### 3. The schema-header widening cannot hold

The plan asked to widen `EXAMPLE_ROOT_MARKER` from `run.py` to a property so the
example became visible to `tests/examples/test_artifact_schema_headers.py`.
Measured, that produces a red check bought by the widening rather than a defect
found:

- The bijection requires every collected root to own a covered `artifacts/`
  directory. A `D-IMPL-136` single-file-config example has **none by design**.
- Pointing the covered set at `deployment/` instead is worse. Observed from
  `tools.check_schema_headers.check_directory`:
  ```
  PROBLEM: …/deployment/binding.yaml: no `# yaml-language-server: $schema=` first line …
  PROBLEM: …/deployment/scenario.yaml: no `# yaml-language-server: $schema=` first line …
  ```
  **Neither is an artifact.** `binding.yaml` is deployment-environment material,
  never registered and never content-hashed (`D-IMPL-141`); `scenario.yaml` is
  the deployment's own vocabulary. Annotating either would make a document
  assert something false to satisfy a checker.
- `examples/s1-00-companies-over-revenue` — the same shape, and the document
  this config was recovered from — is **already** outside that gate today.
  Measured: the collected roots are the eight numbered examples plus
  `external/00-hello-context` and `s1-01`; `s1-00` is absent.

Shipped instead: `test_a_single_file_config_example_is_outside_the_bijection`,
which asserts the boundary and turns red the day the example grows an
`artifacts/` directory.

### 4. A false claim inherited verbatim from the recovered document

`s1-00`'s `ccf_config.yaml` said a filing date "arrives as the envelope's
`observed_time` and becomes the claim's `observed_at`, which is what the
half-life curve reads." **It does not.**
`src/ccf/assembly/worker.py::AssemblyWorker._stitch` sets `observed_at` from
`ingestion_timestamp` **always** (INV-CH7-03) and routes `observed_time` to
`valid_from`.

This is not pedantry — it is the difference between a demonstration and a dud.
Seeding on that claim produced, observed:

```
context debt D_c   0.0000  →  ok
```

D_c pinned at zero, in the example whose entire headline is *what a `SELECT`
would not have told you*. Corrected in the recovered document with the citation.

---

## The recovery command and what changed

```
examples/s1-00-companies-over-revenue/ccf_config.yaml
```
(read from the working tree — `17-08` has not run, so `git show` was
unnecessary; the file is still on disk at `6d695b1`.)

Changed, and nothing else: `backend: postgres` → `sqlite` (§2 above); the
`$schema=` path re-rooted `../../` → `../../../` for the extra directory level;
the `resolution:` comment corrected (§4 above); and the header comment now
records the recovery. **The product class, the request contract, the resolution
rules, the λ_c curve, the debt bands and the policy regime are unchanged** —
that part of the rejected example was never the problem.

---

## `consume.py`

**78 physical lines** against a declared budget of 80. Full import list, the
whole of it:

```
13:from __future__ import annotations
15:import argparse
16:import sys
17:from datetime import datetime
19:from ccf.client import ProductClient
23:import ccf.client.adapters.inprocess  # noqa: E402,F401
```

Two of those needed a measurement.

**`import ccf.client.adapters.inprocess` — `D-05` ships no discovery chain.**
Without it the run dies at `for_product`:

```
ccf.client.errors.BindingError: `inprocess` names no transport this client can
build — no transport scheme is registered in this process at all, so the
deployment installed no adapter.
```

This is by design (`binding.py`: "no plugin lookup and no discovery chain to
fall back on"), and it is inside `ccf.client`, so the purity gate is satisfied.
**But it is worth Dave's eye**: the phase's headline claim is transport
inversion — *same `consume.py`, different `CCF_BINDING`* — and today that claim
costs the consumer one import line that names a scheme. Pointing `CCF_BINDING`
at a different transport needs a different import. Raised as an observation, not
built around. See `## For Dave` item 3.

**`--min-revenue` is `type=int`, not `float`.** `WireRequest` refuses a float,
with a good message: *"canonical JSON renders it as text, so the decoded echo
would differ from what was sent and the `WireOutcome.request` cross-check would
report a transport failure on a healthy wire."* Correct refusal, recorded in a
comment at the flag.

---

## The two command strings, byte for byte

Both assume the **repository root** as working directory.

README (`examples/hw1-companies-over-revenue/README.md`), inside the fenced
block:
```
CCF_BINDING="inprocess:examples/hw1-companies-over-revenue/deployment" .venv/bin/python examples/hw1-companies-over-revenue/consume.py --min-revenue 1000000000 --as-of 2026-08-01T00:00:00+00:00
```

`Makefile`, the single recipe line under `example-hw1:`:
```
CCF_BINDING="inprocess:examples/hw1-companies-over-revenue/deployment" .venv/bin/python examples/hw1-companies-over-revenue/consume.py --min-revenue 1000000000 --as-of 2026-08-01T00:00:00+00:00
```

Character-identical, asserted by
`test_the_make_target_runs_the_readmes_documented_command`.

**One deviation from the plan's letter, and it is forced.** The plan wrote the
command as `export CCF_BINDING=…` on one line then `.venv/bin/python consume.py`
on a second. Two lines cannot be character-identical to a `make` recipe, because
a multi-line recipe needs `; \` continuations that the README block does not
carry — and joining them by a rule ("strip the continuations first") is a fudge
that makes the identity criterion a comparison of two *transformations*. The
env-prefix single-line form makes the identity trivially true and keeps it to
**one** command block, which is what the criterion is protecting. `.venv/bin/python`
is spelled in both, and the README's one-line note about an activated virtual
environment introduces no second block.

---

## The observed run

Populated out of tree (a scratchpad script, never committed, mirroring
`tests/client/conftest.py::seed` — boot, ingest, close), then:

```
$ make example-hw1
CCF_BINDING="inprocess:examples/hw1-companies-over-revenue/deployment" .venv/bin/python examples/hw1-companies-over-revenue/consume.py --min-revenue 1000000000 --as-of 2026-08-01T00:00:00+00:00

Q: which companies have revenue over 1000000000?
   Contoso Manufacturing          1850000000
   Litware Systems                7750000000
   Lucerne Publishing             1500000000
   Northwind Traders              4200000000
   Tailspin Logistics             12400000000
   Wingtip Materials              2900000000

   6 of 10 assembled

and what a SELECT would not have told you:
   context debt D_c   0.3886  →  forced_llm
   content address    090b1b701d02f4be1711a9b645761959fec8502283e07144dc3a23dbdbc46737
   replay record      ccf-artifact://hw1-demo/hw1.replay-record/8c4994edd816aa7b95827021737d3025dd4d4f3d97d11296d12d3d3be76141ae@e99c78dd06cc93175908b80fd010d3b53962774c3eb7ab9e23398c5a1f00cbe8
   answer expires     2026-08-01 00:10:00+00:00
```
`EXIT=0`, captured directly, not through a pipe.

**Content address, two consecutive runs:**
```
run 1: 090b1b701d02f4be1711a9b645761959fec8502283e07144dc3a23dbdbc46737
run 2: 090b1b701d02f4be1711a9b645761959fec8502283e07144dc3a23dbdbc46737
```
Identical. The reproducibility claim is a claim only until it has been printed
twice and compared; it has been.

**`D_c` is measured, and was shown to move.** Holding the graph fixed and
varying only the boundary:

| `--as-of` | D_c | F | signal |
|---|---|---|---|
| 2026-08-01 | 0.3886 | 0.6114 | `forced_llm` |
| 2027-08-01 | 0.5000 | 0.5000 | `forced_llm` |
| 2029-08-01 | 0.8752 | 0.1248 | `fail_closed` |

The 2027 row is exactly one half-life on: F = 0.5. That is the λ_c curve being
the curve it declares.

**The refusal path, exercised:**
```
refused= True missing-required-parameter | revenue_threshold
```

**`--explain`** additionally prints the perspective, the temporal boundary and
the lineage (`operators_invoked=frozenset({'temporal.as-of-boundary'})`,
`policy_bundle_versions=frozenset({'dd2c515f…'})`, `graph_snapshot_at=…`).

**Worktree-local caveat, stated (`DEF-17-04`).** `make example-hw1` ran with no
`PYTHONPATH`, so `ccf` resolved through the editable install to the **main
checkout**; the `PYTHONPATH=src:runtime` runs resolved to this worktree. Both
printed the identical content address, so the two agree — but the make-target
run is not by itself evidence about this branch's `src/`.

---

## The credential and data scans

```
$ command grep -rniE "(dsn|password|secret|token|://|[0-9]{1,3}(\.[0-9]{1,3}){3})" \
    examples/hw1-companies-over-revenue/deployment/
GREP_EXIT=1
```
**Zero hits.** Not one to justify.

```
$ find examples/hw1-companies-over-revenue \( -name '*.db' -o -name '*.sql' \
    -o -name '*.sqlite*' -o -name '*.jsonl' \) -print
FIND_DONE
```
Nothing. `deployment/.gitignore` names `graph.sqlite3` and `artifact-store/`, so
`D-32`'s "nothing committed as data" is a mechanism rather than a rule —
confirmed by `git status --short` staying clean of both after a real run.

---

## The gates, and every control's observed refusal

Both take their subject as a parameter:

```python
def check_example_purity(root: pathlib.Path) -> list[str]
def check_example_budget(example_root: pathlib.Path) -> list[str]
```

Every control feeds a `tmp_path` copy into the **same** function the shipped
assertion calls.

**Reader-visible modules are derived, not named.** `reader_visible_modules(root)`
returns every `.py` sitting *directly* in the example root. No filename appears
in a constant. That is also why `deployment/projection.py` is correctly outside
the purity gate — it is the producer's world and imports `ccf.graph`,
`ccf.operators` and `ccf.projection` legitimately.

**`command grep -c "stdlib_module_names" tests/examples/test_client_example_purity.py` → 2.**

### What the gates do on ZERO matches — the question this phase demanded

**They fail.** Both. A purity gate that globs an example directory and finds
nothing would otherwise report green *precisely when the example has been
renamed away*; a budget gate counting lines in a moved tree counts zero and
passes. Six of the fifteen controls are vacuity controls, and each was observed.

### Observed failure messages

| # | Control | Observed message (abridged) |
|---|---|---|
| P1 | `import deployment` (`ast.Import`) | `consume.py:1 imports \`deployment\`, which is neither stdlib nor \`ccf.client\`…` |
| P2 | `from produce import x` (`ast.ImportFrom`) | `consume.py:1 imports \`produce\`, which is neither stdlib nor \`ccf.client\`…` |
| P3 | import deferred into a function body | `consume.py:43 imports \`deployment\`…` — **line 43, inside `main`**, the shape the regex ancestors missed |
| P4 | relative import of a sibling | `consume.py:1 imports \`deployment\` relatively — a client example importing a sibling module is the consumer reaching into the producer's directory…` |
| P5 | **VACUITY** — root with no module | `…/no-modules-here carries no top-level \`.py\` module, so this gate checked nothing… which is the vacuous pass it exists to be immune to` |
| P6 | **VACUITY** — root does not exist | `…/was-renamed-away is not a directory, so nothing was checked` |
| B1 | 20 appended blank lines | `example/consume.py is 98 physical lines against a declared budget of 80. Blank lines and comments count…` |
| B2 | 20 appended comment lines | `example/consume.py is 98 physical lines against a declared budget of 80…` |
| B3 | README figure lowered 80 → 77, **file untouched** | `example/consume.py is 78 physical lines against a declared budget of 77…` |
| B4 | **VACUITY** — README declares no budget | `example/README.md declares no line budget in a form this gate can parse… with none there, this gate enforces nothing at all` |
| B5 | **VACUITY** — root with no module | `…/example carries no top-level \`.py\` module, so this gate counted zero lines and would otherwise have passed…` |
| B6 | **VACUITY** — root does not exist | `…/was-renamed-away is not a directory, so no line was counted and nothing was checked` |
| I1 | command with a changed flag name | `the README's documented command and the \`make\` recipe have diverged. README: '…--min-revenue…' Makefile: '…--minimum…'` |
| I2 | command with a changed threshold | `…README: '…1000000000…' Makefile: '…5000000000…'` |
| I3 | a bare `python` | `…README: '….venv/bin/python…' Makefile: '…python…'` |
| I4 | `$(PYTHON)` in the recipe | diverged, **plus** `the recipe uses \`$(PYTHON)\`, which is not a string a reader can type…` |
| I5 | **VACUITY** — both sides empty | `one side of the comparison is empty, so nothing was compared — documented='' recipe=''` |

B3 is the one that proves the number has a single home: the README's figure was
lowered with not a line of Python moving, and the gate went red.

### The sabotage measurement that matters most

Neutering **both** checkers to `return []` at their first statement:

```
12 failed, 12 passed in 0.13s
```

Exactly the twelve gate controls turned red — the six purity/budget refusals and
the six vacuity cases. Restored: `24 passed`, and
`command grep -c "NEUTERED" …` → `0` in both files. The controls test the
gate, not each other.

---

## THE TWO FAILURES — as raised at the checkpoint

> **CLOSED.** Dave ruled (#2 above): teach the detector, do not raise the
> ceiling. Both are green. This section is kept as the record of *why the
> checkpoint was raised*, because the reasoning is the specification the fix was
> built from. The measurements below are the pre-fix state.

`make ci-quick-suite` → **EXIT 2**, captured directly:

```
2 failed, 3722 passed, 2 skipped, 172 deselected, 105 warnings in 376.09s
```

**Delta accounted, and measured rather than reasoned.** Collection under the
exact `ci-quick-suite` selection, with every change of this plan parked aside
and then restored:

```
baseline (example + both gate modules parked, schema-header module reverted):
    3697/3869 collected (172 deselected)
now:
    3726/3898 collected (172 deselected)
```

**+29 collected**, and every one is attributed:

| Source | + |
|---|---|
| `test_client_example_purity.py` + `test_client_example_budget.py` | 24 |
| `test_artifact_schema_headers.py::test_a_single_file_config_example_is_outside_the_bijection` | 1 |
| `test_gate_two_call_shape.py` — three tests parametrized over projecting scopes, which the new `deployment/projection.py` joins (78 → 81) | 3 |
| `test_required_operators_guard.py::test_no_required_operators_reads_the_registrys_own_keys[…projection.py-]` | 1 |
| **total** | **29** |

Baseline `3695 passed + 2 skipped = 3697` ✓. Now
`3722 passed + 2 failed + 2 skipped = 3726` ✓. And
**3695 + 29 − 2 = 3722**, exactly. Of the 29 new cases exactly **one** fails;
the second failure is a previously-passing test that flipped. Both are:

```
FAILED tests/products/test_gate_two_call_shape.py::test_every_projecting_example_body_names_the_binder[examples/hw1-companies-over-revenue/deployment/projection.py-]
FAILED tests/products/test_gate_two_call_shape.py::test_the_premise_detector_reads_the_shipped_tree_correctly
```

### They are not defects in the example. They are a ruled exemption meeting a shape that postdates it.

Measured, scope by scope:

```
examples/hw1-companies-over-revenue/deployment/projection.py | build_projection() | line 118 | one_document= False | names_binder= False
examples/s1-00-companies-over-revenue/produce.py             | assemble_and_serve() | line 202 | one_document= True  | names_binder= False
claimants: ['examples/s1-00-companies-over-revenue']
MAXIMUM_ONE_DOCUMENT_DEPLOYMENTS: 1
```

**Failure 1** demands `build_projection()` call
`refuse_operator_set_divergence`. It cannot meaningfully: `required` **arrives
as a parameter** from `ccf.products.resolver.build_governed_resolver`, already
derived from the registered product class. There is no second document.

**And the same module would refuse the call it demands.** `_binder_collapses`
property (1), quoted verbatim: *"A plan built as
`required=declared.required_operator_keys` and then handed to the binder
alongside that same `declared` makes `claimed == required` hold unconditionally…
The binder is green, it cannot fail, and `ccf.projection-requirements` has been
routed around."* That is exactly the shape adding the call would create. **The
coverage assertion demands a call that property (1) refuses.**

This is `D-IMPL-137` row B — the exemption written for precisely this case. The
detector returns `False` only because `_class_claim` reads a claim *in the
body*, and post-`D-IMPL-141` the claim arrives as a **parameter**.

Separately, the comparison the gate is protecting **is performed** for a
`D-IMPL-136` deployment — by the SDK, at boot:
`src/ccf/deployment/config.py::_refuse_operator_set_divergence`, called from
`derive_deployment`. It is not skipped; it moved.

**Failure 2** is the same fact from the other side:
`test_the_premise_detector_reads_the_shipped_tree_correctly` pins the set of
projecting deployments registering no `ccf.projection-requirements` to exactly
`["examples/s1-00-companies-over-revenue"]`. A second such deployment now
exists. Note this does **not** self-heal when `17-08` deletes `s1-00` — the list
becomes `["examples/hw1-companies-over-revenue/deployment"]`, still ≠ expected.

### Why I stopped instead of widening

`MAXIMUM_ONE_DOCUMENT_DEPLOYMENTS = 1` is documented as *"one with no headroom,
on purpose"*, so that **the second claimant is red and a human looks**. The gate
is working exactly as designed. Widening a deliberately-bounded exemption is a
Rule 4 architectural decision, and awarding it to myself is the thing the
constant exists to prevent. It goes to Dave — and Task 4 is a blocking
human-verify checkpoint regardless. See `## For Dave` item 2.

---

## The 17-08 gate — the answer is NO, and here is why

> **Dave's ruling #4: the removal of `s1-00`/`s1-01` is DEFERRED OUT OF PHASE
> 17.** Neither tree was deleted, no resolver-seam docstring was edited, and
> none of `17-08`'s files were touched. The finding below stands on the record
> for whichever phase picks the removal up.

`17-08` deletes `examples/s1-00-*` and `examples/s1-01-*`.
`tools/docs_tests/test_resolver_seam_obligations.py` requires **both** resolver
Protocol docstrings to cite **≥2 distinct** `examples/…py::Symbol` paths that
resolve on disk. Measured, both seams cite the same pair:

```
ccf_runtime.mcp.egress.ProductResolverProtocol
  [('examples/s1-01-hello-context-product/spine.py', 'assemble_and_serve'),
   ('examples/04-cross-process/producer_child.py', 'resolve')]
ccf_runtime.mcp.experience.ExperienceProductResolverProtocol
  [ …identical… ]
```

`04-cross-process` survives `17-08`; `s1-01` does not. So after `17-08` each
seam cites one resolvable path and one dead one — failing both
`test_the_seam_cites_a_shipped_example_that_exists` and
`test_both_seams_cite_both_call_sites`.

**This example cannot take `s1-01`'s place, and it is not close.** `consume.py`
imports `ccf.client` and stdlib only — that is `D-02`, and the purity gate this
plan ships enforces it. `refuse_request` and `refuse_bound_payload` are
**producer-side**, and post-`17-13` they live inside
`ccf.products.resolver.GovernedResolver`, which the SDK builds. There is no
place in this example for either call, by construction. Measured:

```
$ command grep -rn "refuse_request\|refuse_bound_payload" examples/
… examples/s1-01-hello-context-product/spine.py:323
… examples/04-cross-process/producer_child.py:697
… examples/s1-00-companies-over-revenue/produce.py:242
```
Three call sites, all producer-side, none of them mine.

**I did not edit those docstrings.** A citation is an assertion about another
file, and pointing them at an example that does not demonstrate what they claim
would be a false citation that passes a checker — this project's own defect
class, twice over.

**So the re-order did not clear `17-08`'s path.** `17-08` still needs a shipped
`refuse_request` call site in `examples/`, or a decision to change what the seam
docstrings cite. That is a decision, not a plan step. See `## For Dave` item 4.

---

## Verification, exit codes captured directly

| Command | Exit | Result |
|---|---|---|
| `make ci-quick-suite` | **2** | `2 failed, 3722 passed, 2 skipped, 172 deselected` — the two above |
| `PYTHONPATH=src:runtime .venv/bin/python -m tools.lints --all` | **0** | — |
| `make lint` | **0** | — |
| `make typecheck` | **0** | `Success: no issues found in 209 source files` |
| `make docs-strict` | **0** | — |
| `.venv/bin/python -m pytest tests/examples -q` | **0** | `368 passed, 37 skipped` |
| `make example-hw1` | **0** | output above |
| `make gate-tools` | **2** | 4 failures before the re-sweep, **3** after; see below |

No `make … | tail` anywhere: every exit code above came from
`make X > out.log 2>&1; echo "EXIT=$?"` and was branched on.

### `make gate-tools` — one staleness (fixed) and three more of the same finding

The report was re-swept **after** this file was written, per the standing
ordering hazard:

```
$ PYTHONPATH=src:runtime .venv/bin/python tools/retirement_sweep.py --report
wrote docs/surface/examples/RETIREMENT-COUPLINGS.md
231 coupling rows across 72 files (142 rows outside the three swept trees); 1708 files scanned
```

That fixed `test_the_committed_report_is_current` (the `Makefile` line-number
shift). **Three remain, and they are the same finding as the other two, wearing
different clothes:**

```
FAILED tools/docs_tests/test_retirement_sweep.py::test_all_four_no_path_token_shapes_are_present_at_head
        AssertionError: no `inline-tree-witness` row at HEAD
FAILED tools/docs_tests/test_retirement_sweep.py::test_the_head_inline_tree_witness_row_is_owned_three_waves_early
        assert 0 == 1
FAILED tools/docs_tests/test_retirement_sweep.py::test_the_gate_two_module_carries_rows_with_two_different_owners
        assert 1 >= 2, where 1 = len({'17-08'})
```

The committed report at `6d695b1` carried exactly one `inline-tree-witness` row:

```
| tests/products/test_gate_two_call_shape.py | 3737 | examples/03-harness-portability |
  inline-tree-witness | live | 1 | - | 16-15 |
  …scans BINDER_SCANNED_TREES inline… Sustained only by: examples/03-harness-portability.
```

`witnesses = 1` — the scan was sustained by **one** retiring path, which is what
made it a coupling. My example adds a second projecting scope under
`examples/`, so the scan now has headroom and the row correctly **disappears**.

**The sweep is telling the truth; three tests pin the previous truth.** The
first is a non-vacuity precondition — with no `inline-tree-witness` row at HEAD,
that detector is no longer exercised against the real tree, which is a genuine
loss of coverage and not something a new example can manufacture back. This is
Dave's call too, and it will recur every time an example is added. Escalation
item 5.

**`examples/` is not typechecked** (`[tool.mypy] files = ["src","runtime"]`), so
`make typecheck` says nothing about `consume.py`. The purity and budget gates
are the only checks that file has, which is why they were built to fail on
zero matches.

**No public-surface change**: nothing was added to `src/` or `runtime/`, so no
`docs/surface-changes/` entry and no `make surface-changes` run is owed.

**`cinv01a-prompt-shape`** did not fire on anything here; no assertion was
weakened to pass a lint.

---

## For Dave — the four things raised at the checkpoint (ALL ANSWERED)

> Answered in `## Dave's rulings` at the top. Kept as the record of what was
> asked. Items 1 and 3 were ruled *no change*; item 2 was the work; item 4 was
> deferred out of the phase; item 5 was folded into item 2.

1. **The deployment is sqlite, not the FIBO Postgres**, because a Postgres
   deployment cannot be authored under the post-`17-12` binding document without
   a DSN literal in the tree (measurement in §2 above). And the FIBO stores hold
   a hand-built layout, not CCF's. Is the sqlite form acceptable for the first
   example, or does the FIBO deployment need a `from_env` form on
   `binding.yaml`'s `connection:` — which is new surface and a new decision?
2. **The two `test_gate_two_call_shape.py` failures.** Either the `D-IMPL-137`
   premise detector learns the post-`D-IMPL-141` shape (a plan factory whose
   `required` arrives as a parameter), or the ceiling rises to 2 and the pinned
   set is updated. Both are edits to a deliberately-bounded exemption. Which?
3. **Transport inversion costs the consumer one import** naming a scheme
   (`D-05`, no discovery chain). Intended, or worth a follow-up?
4. **`17-08` is still blocked** on the resolver-seam citations. This example
   cannot supply them (§ above). Needs a ruling before `17-08` runs.

5. **Three `tools/docs_tests/test_retirement_sweep.py` failures** because the
   example gave a real coupling headroom and the `inline-tree-witness` detector
   now has nothing at HEAD to exercise it against. Loosen the precondition, or
   accept that adding an example can retire a coupling row?

Also, the plan's own step 7: **no CI leg was built for this example**, and the
README says so. `live-legs.yml`'s three jobs are all `runs-on: ubuntu-latest`
with no database secrets. If you want one it needs a self-hosted runner or a
reachable mirror plus repository secrets — infrastructure, a `D-IMPL-NN`, and
its own plan.

---

## Deviations from Plan

### Auto-fixed

**1. [Rule 1 — Bug] Corrected a false claim in the recovered `ccf_config.yaml`**
- **Found during:** Task 2, when D_c printed `0.0000 → ok`
- **Issue:** the comment said `observed_time` becomes `observed_at`; `_stitch`
  sets `observed_at` from `ingestion_timestamp` always (INV-CH7-03)
- **Fix:** corrected with the `path.py::Symbol` citation
- **Commit:** `1893bf2`

**2. [Rule 3 — Blocking] `--min-revenue` from `float` to `int`**
- `WireRequest` refuses a float parameter. Commit `1893bf2`.

**3. [Rule 3 — Blocking] Added the adapter import to `consume.py`**
- `D-05` ships no discovery chain; without it the run cannot start. Commit
  `1893bf2`.

### Disputed with a measurement, and NOT done

**4. `deployment/resolver.py` and `deployment/backends.yaml` — not written.**
Both are in the plan's `files_modified`. §1 and §2 above.

**5. `EXAMPLE_ROOT_MARKER` — not widened.** §3 above. The boundary is asserted
instead, in `test_a_single_file_config_example_is_outside_the_bijection`.

**6. The documented command is one env-prefixed line, not `export` + a second
line.** Two lines cannot be character-identical to a `make` recipe. Reasoned
above.

### Escalated to the checkpoint, then executed on Dave's ruling (Rule 4)

**7. The five gate failures.** Escalated rather than fixed, because widening a
ceiling whose whole purpose is to be red on the second claimant is Dave's call.
Ruled #2/#5: teach the detector, keep the ceiling at one. Executed — a second,
separately-bounded route, with sixteen new controls across two modules and both
sabotage directions observed. Both ceilings remain at 1 and
`test_the_two_exemptions_are_disjoint` proves they bound two populations rather
than one of two.

---

## Self-Check: PASSED

All nine created files verified present on disk. All three task commits
verified in `git log`: `8139c7e`, `1893bf2`, `a734484`, each a child of
`6d695b1`, plus `125c3a8` (checkpoint SUMMARY) and the round-2 fix commit.

Modified in round 2, on Dave's ruling: `tests/products/test_gate_two_call_shape.py`
and `tools/docs_tests/test_retirement_sweep.py`. **No `STATE.md` or
`ROADMAP.md` edit in either round**, and no file belonging to `17-08`.

## Known Stubs

None. Every printed field is a real value from a real assembly.

## Threat Flags

None. No new network endpoint, auth path, file-access pattern or schema change
at a trust boundary. `T-17-32` (credential in the tree) is discharged by the
zero-hit scan; `T-17-33` by the purity gate; `T-17-34` by the budget gate's
named reader; `T-17-35` by the command-identity assertion; `T-17-36` by adding
the example to no workflow (`git status --porcelain .github/` clean).
