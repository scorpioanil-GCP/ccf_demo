# cp-22 — findings

Classified under `docs/EXAMPLE-EVALUATION-CRITERIA.md`. **Nothing here was
repaired by changing the example to make it pass** (`D-IMPL-261`).

Measured 2026-09-21 against the live estate (`CCF_REQUIRE_ESTATE=1`).

---

## Summary

| id | class | disposition |
|---|---|---|
| `AIA-F-01` | 2 · launch ergonomics **candidate** | recorded with the friction measured; not repaired |
| `AIA-F-02` | 4 · example design | deliberate, disclosed |
| `AIA-F-03` | example defect (mine) | fixed during build |
| `AIA-F-04` | proof machinery (mine) | fixed during build |
| `AIA-F-05` | 3 · post-launch enhancement | backlog record below |
| `AIA-F-06` | 4 · estate/example limitation | recorded |
| `AIA-F-07` | example defect (mine) | **fixed** — a cross-tree module collision |
| `AIA-F-08` | 2 · launch ergonomics | **CLOSED** by a structural `CONSUMER` shape (ruled B) |

**Active issue cap: 1 of 3** — `AIA-F-01`, and it is a new instance of a known
family rather than a new defect.

**No stop condition fired.** None of the four ruled stop conditions was met:
no capability was missing, no governance behaved incorrectly, nothing leaked
across the extraction seam, and nothing about satisfying A2A required a CCF
protocol, door or peering change.

---

## `AIA-F-01` — a debt tolerance declared the obvious way cannot govern anything

**Category 2 candidate (launch ergonomics). Measured, not repaired.**

Agent B's tolerance is a declared value, so it lives in
`artifacts/agent-b.yaml`. Written the obvious way —

```yaml
debt_tolerance: 0.98
```

— YAML parses it as a Python `float`, and `canonical_bytes` refuses a float as
not bit-stable. The result is **not** a governed refusal naming the problem:
it is a `CanonicalizationError` raised during request canonicalization, before
the request contract is consulted.

**So a tolerance declared the natural way does not loosen or tighten anything
— it raises.** The artifact must say `"0.98"` and the code must convert:

```yaml
debt_tolerance: "0.98"        # a string, deliberately
```
```python
tolerance = Decimal(str(DECLARATION["debt_tolerance"]))
```

**§C launch test.** Step 1: *could we ship without this?* **Yes** — the
supported path works and is two characters of quoting. Step 2: *would the
supported alternative create enough friction or misuse risk to materially
undermine adoption?* **This is the question worth a ruling.** The failure is
loud rather than silent, which is the mitigating half. The aggravating half is
that the natural spelling of a *configuration* value is the wrong one, the
diagnostic names canonicalization rather than the field, and **an adopter's
first encounter with it is at serve time**.

**This is the `D-IMPL-304` / `LEX-F-02` family at a new seam.** Every prior
instance was a *caller-supplied request parameter* typed by someone writing a
client. This one is a **deployment's own declared configuration**, which is a
different author, a different moment, and a different expectation. Recorded as
a distinct instance for that reason, not as a duplicate.

**Not repaired here**, per `D-IMPL-261`.

---

## `AIA-F-02` — Agent A cannot distinguish "unknown subject" from "low confidence"

**Category 4 (example design). Deliberate, and disclosed.**

Two genuinely different internal outcomes — a subject the estate cannot
resolve, and a determination withheld above Agent B's declared tolerance —
produce the **same** A2A non-success text:

```
the question could not be answered with sufficient confidence
```

This is a choice, and the alternative is worse. Distinguishing them would be
more useful to Agent A and would also make Agent B an **oracle**: a caller
could separate "this identifier is unknown to me" from "known, but I am not
confident", and enumerate the peer's subject space from outside. That is the
cp-02 discipline — byte-identical refusals for missing and withheld — applied
at an agent boundary.

**Recorded rather than silently chosen.** An adopter whose use case needs the
distinction should make it deliberately, knowing what it discloses.

---

## `AIA-F-03` — the agent card advertised a port the server was not bound to

**Example defect. Mine. Fixed during the build.**

`agent_card()` built its URL from the **declared** port while `--port` bound
another. A2A discovery worked — the card resolved with `200` — and then every
call dialled the advertised port, where nothing listened.

**It reads exactly like an intermittent network fault:**

```
Network communication error: All connection attempts failed
```

Found only because the test harness runs Agent B on two non-default ports to
prove `AIA-G10`. The single-port demonstration would never have exposed it, and
the failure mode names the network rather than the card.

**The transferable shape:** a service that publishes its own address must
publish the address it actually bound, and a discovery document that succeeds
while every subsequent call fails is a *configuration* bug wearing a
*connectivity* bug's error message.

---

## `AIA-F-04` — `AIA-G08`'s first sabotage did not mutate the claim

**Proof-machinery defect. Mine. Fixed.**

`AIA-G08` is the most important gate in the rung: *a caller cannot steer the
determination*. Its first sabotage read a caller-supplied `debt_tolerance` off
the wire and wrote it to an environment variable — and **nothing read it**.

The gate stayed **green**, correctly: the claim is that a caller-supplied field
cannot change the answer, and a leak that changes no answer does not mutate
that claim. The corrected sabotage routes the caller's value into the
strictness of the governed request; the gate went red.

**The durable rule at its next instance** (`ABS-F-09`, `PEW-F-07`, `WIF-F-05`,
now this): *a sabotage must mutate the CLAIM the gate asserts, not merely one
field the claim mentions.*

---

## `AIA-F-05` — the extraction seam is written by hand, and this is the first instance

**Category 3 (post-launch enhancement). Backlog record.**

| field | value |
|---|---|
| **capability** | a supported way to derive a narrow, non-CCF answer from a governed Context Product, with the guarantee that no CCF-shaped structure survives |
| **evidence / rung(s)** | cp-22, `AIA-F-05` — **first instance** |
| **current supported path** | read the payload and build a dict by hand (`agent_b.py::_answer_from`, 18 lines), and assert the absence of forbidden tokens in the example's own test |
| **friction** | low in lines, but the *guarantee* is the example's, not the SDK's: nothing stops the next adopter exporting `result.payload` wholesale, and that is one line |
| **adoption impact** | every adopter embedding CCF inside an agent that answers a non-CCF protocol — which is the whole "CCF layers onto any harness" posture |
| **launch necessity** | §C step 1 **yes, we can ship without it**; step 2 **no** — the supported path is short and correct, and one rung is one data point (§H) |
| **scope / risk** | a redaction or projection helper touches no governed path; the risk is over-generalizing a seam that has appeared once |
| **recommended release** | post-launch, and **only if a second and third rung write the same thing** |

**Explicitly not requested.** §H is the governing rule: one rung's need is one
data point. This record exists so the second instance is recognized as a
second instance.

---

## `AIA-F-06` — CP-22 reads the estate only through cp-21

**Category 4 (example limitation). Recorded.**

CP-22 declares no environment of its own and no binding document. It consumes
`examples/cp-21-large-exposure` and inherits that rung's six `CCF_CP_21_*`
variables. **That is the ruled design** (`Q2`) and the reason no new binding
mechanism was added — but it has a consequence worth stating: **cp-22's tests
skip when cp-21's estate is unconfigured**, and a change to cp-21's request
surface is a change to cp-22's.

The coupling is deliberate and is what "consume an existing paved product"
means. It is recorded so a reader meets it rather than discovers it.

---

## What held without friction

- **`open_product` from outside the product tree** took Agent B unchanged, and
  the **shipped cost is measured** as `Q2` required. Code lines, docstrings and
  comments excluded:

  | | code lines |
  |---|---|
  | the Gate-1 standalone probe | **25** |
  | shipped `_ask_ccf` — the whole CCF half | **34** |
  | shipped `_answer_from` — the extraction | **16** |
  | `_read_request` — the narrow trust map | **11** |
  | `agent_card` + `app` + `main` — the A2A half | **29** |

  The CCF half grew by **9 lines** over the probe, and every one of them is
  named: the declared envelope, the `Decimal` conversion `AIA-F-01` forces, and
  the refusal branch. **No additional SDK glue.**

  Whole files, same measure: `agent_b.py` **144**, `agent_a.py` **61**,
  `run.py` **61** — and `run.py` is a demonstration runner rather than anything
  an adopter must write.
- **`a2a-sdk` was used as given.** `AgentExecutor`, `DefaultRequestHandler`,
  `create_jsonrpc_routes`, `create_agent_card_routes`, `A2ACardResolver` and
  `ClientFactory` needed **no adapter**, which is what CLAUDE.md §7.3 predicts
  for a harness the SDK does not absorb.
- **The governed refusal arrived as a value, not an exception**, so translating
  it was a branch rather than an interception.
- **The replay record resolved inside Agent B** with no extra wiring beyond
  `opened.record_of(outcome)`.
- **No SDK source file was touched, no new class was declared, no new
  dependency was added, and no new decision id was spent.**

---

## `AIA-F-07` — Agent B imported another product tree's producer

**Example defect. Mine. Fixed. It only appeared in the full suite, and the
error it produced was the lucky outcome.**

A CCF product tree is imported **by bare module name off `sys.path`** —
`produce`, `deployment`, `projection`, `acquisition`. Any two trees in one
process claim exactly the same four names.

Agent B's tests passed alone and under `-k cp_22`, and failed in the full
`tests/examples` run with:

```
AttributeError: module 'produce' has no attribute 'product'. Did you mean: '_project'?
```

Another example's `produce` was already in `sys.modules`, so Agent B's
`import produce` returned **that tree's module** and Agent B assembled nothing
at all.

**The AttributeError is why this was cheap to find, and it is not the
dangerous case.** Two trees whose producers happen to share a function name —
and this ladder names them similarly on purpose — would have had Agent B
assemble **the wrong product** and answer Agent A from it. That is a
governance failure wearing a successful answer: the right principal, the right
tolerance, the right extraction, and the wrong subject entirely.

**Fixed in `agent_b.py`, not in the test**, because the import is Agent B's:
`_consumed_modules()` evicts the four colliding names, inserts the consumed
tree's path, imports, **verifies the file actually loaded lives in that tree**,
and restores whatever it displaced. A mismatch raises `CannotAnswer` rather
than answering.

**AND THE FIX HAD TO BE APPLIED TWICE, WHICH IS THE INSTRUCTIVE PART.**
Guarding `agent_b.py` cleared two of the three failing tests. The third —
`test_the_decision_is_reconstructible_inside_agent_b` — kept failing because
it rolled its **own** hand-written import of the consumed tree, and so
inherited the identical collision the product had just been fixed for. It now
goes through `agent_b._consumed_modules()`, which is both the guarded route
and the route that actually ships. **A test that reaches the consumed tree by
a different path is not testing the path under test.**

**Second instance of a class already recorded.** `LEX-F-11` (cp-21) was the
same failure in a different namespace — `server.serve` surviving an eviction
that popped only `server`. Two instances, two namespaces, one cause: **bare
module names shared across example trees, evicted incompletely.** The
`sys.modules` isolation sweep Dave carried from CP-21 now has a second data
point, and this one shows the failure is not confined to test harnesses — it
reached shipped agent code.

---

## `AIA-F-08` — the spine contract had four shapes, and none of them was CONSUMER

**CLOSED 2026-09-22 by a structural `CONSUMER` shape. Dave ruled B.**

`tests/examples/test_spine_separation.py` scans `examples/cp-*` by glob and
judges each tree against the regions its **shape** owes. Measured 2026-09-21:

| tree | `paved_entry` | shape | regions owed | has |
|---|---|---|---|---|
| cp-21 | **True** | `paved` | `boot`, `answer` | both |
| **cp-22** | **False** | `spine` *(the default)* | **all seven** | none |

The cause is exact. `PAVED_ENTRY_CALLS` is
`{"ccf.products.product.open_product"}`, matched by **qualified call name
within the tree**. Agent B reaches the paved road through **cp-21's**
`produce.product(...)` wrapper, so the detector cannot see it, and `shape_of`
falls through to its `"spine"` default — which demands a full producer's call
spine (`ingest`, `operators`, `project`, `gate`, `record`, `serve`) **from a
tree that produces nothing**.

`shape_of` has four shapes — `paved`, `canonical`, `half-migrated`,
`double-spined` — plus `"spine"` as the default. **None of them is
"consumer."** CP-22 is the first `cp-*` tree that consumes a product rather
than producing one, and the glob was written before such a tree existed.

**Five tests fail as a result**, all introduced by cp-22's arrival (measured:
`main` at `ec0c153e` has **zero** spine failures), including
`test_discovery_is_independent_of_the_working_directory`, a cross-tree
aggregate that cp-22's presence breaks.

**Why nothing was changed to make them pass.**

- **Not `agent_b.py`.** Calling `open_product` directly would mean duplicating
  cp-21's entire boot — its `config_root` and its `acquire` / `project` /
  `assess` / `gate` wiring — purely so a detector fires. That is the inversion
  `D-IMPL-326` exists to prevent: *the tool accepts the authority that governs
  the product, not the other way round.* It would also make Agent B a worse
  demonstration, since reusing the tree's own boot is exactly what an adopter
  should do.
- **Not the gate.** It governs 28 trees and carries rulings from phase 16
  D-11, `D-IMPL-306` and `D-IMPL-343`. Widening a shared classifier on one
  rung's authority is not this rung's call.
- **Not a `# ccf-schema: deferred(...)`-shaped exception.** That is the move
  this project refuses everywhere else.

### The ruling, and what it settled

> **Dave, 2026-09-22.** *"Do not create a CONSUMER allowlist. The spine gate
> remains structural. Add a `CONSUMER` structural classification … A `cp-*`
> tree is `CONSUMER` when it: (1) declares no Context Product class of its
> own; and (2) reaches an existing paved product entry belonging to another
> product tree. That answers the gate's actual question: Does this tree
> produce a Context Product, or consume one? It does not answer: Is this tree
> approved?"*

**I had first been told to add CP-22 to "the existing human-ruled spine
roster." There is no such roster**, and the module's own ruled text forbids
one — *"There is no roster of canonical examples anywhere in this module and
none may be added"* (line 176), and again for the paved shape at line 247. The
`D-IMPL-141` ruled-list mechanism lives in a different module,
`tests/products/test_gate_two_call_shape.py`. Surfacing that rather than
inventing a roster is what produced ruling B.

**What shipped** (`5169d191`), in `tests/examples/test_spine_separation.py`
only:

- `declares_product_class` reads the deployment document, because a class is a
  Control Plane artifact and that is where a producer names it;
- `foreign_paved_reach` is structural on **both** ends — the call site from
  this tree's AST, the target from the other trees' — so a reach counts only
  when the symbol it names really is a paved entry somewhere else. A tree
  calling its own `produce.product` matches nothing, which is what keeps every
  shipped producer out of the shape;
- a consumer owes no producer regions **and may not publish them**:
  `consumer_problems` refuses a tree that opens `gate`/`record`/`serve` while
  producing nothing.

**Nothing consults a list of approved directories.** No glob was narrowed, no
`agent_b.py` line changed, no `src/` or `runtime/` file touched.

**Six controls, each selecting its subject BY PREDICATE rather than by name**,
so they follow the tree and fail loudly if the last consumer regresses. Four
are the ones the ruling required; two more break **each limb alone**, which
Dave's both-limbs sabotage cannot distinguish from a disjunction. Measured:
**181 passed**, and four sabotages of the classifier itself — `AND`→`OR`, the
reach losing FOREIGN, the product class ignored, a consumer allowed to publish
a spine — each observed **RED**.

**Carried forward, per the ruling:** the follow-up to add a first-class
CONSUMER shape *"before another agent-internal consumer tree is introduced"* is
discharged by this commit. What remains open is nothing.
