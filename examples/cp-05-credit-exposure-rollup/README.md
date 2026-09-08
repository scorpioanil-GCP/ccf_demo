# cp-05 · Credit Exposure Rollup

**Rung 5 of the Context Product ladder.** Tier 2 — PostgreSQL + Fluree.
`credit-risk.exposure-rollup.v1`

> What is total exposure to a corporate family? Traversal plus aggregation with
> materiality thresholds — the concentration denominator a flat data product
> computes wrongly.

---

## What this demonstrates

**That "total exposure" is not a sum.** A data product that adds facility
balances by borrower LEI returns a number that is confidently wrong in both
directions: it double-counts where a guarantee already captured the risk, and
it under-counts where a cross-default binds an entity holding no facility at
all. Nothing in the output signals either error.

Measured on this estate, for the demonstrated anchor:

| | committed |
|---|---|
| What a borrower-keyed sum returns | **145,000,000** |
| What the family actually owes (gross) | **10,125,000,000** |
| After deduplicating the guarantee path (adjusted) | **9,325,000,000** |

The naive answer understates by **69.8×**, and it does not look wrong.

Four more things this rung is the first to do:

- **One traversal, four predicate types, both directions.** Ownership,
  ultimate-consolidation, guarantee and cross-default in a single walk — not one
  walk per edge type merged afterwards.
- **Materialization is the *wrong* posture.** The fastest input has a ~4 hour
  half-life, so a materialized rollup would be stale inside its own window. Rung
  4 uses the same traversal machinery and materializes; this one must not.
- **A `from_decision` TTL anchor.** Rungs 02 and 04 anchor on entity freshness.
  An exposure has no underlying entity whose validity period governs it.
- **A product-specific validation gate** — the reconciliation guard, which
  catches a *plausible wrong answer* rather than a broken pipeline.
- **A governed refusal of fulfillment.** The demonstrated run is **WITHHELD**,
  and the number is printed anyway. See below.

### The demonstrated run is a governed refusal

Against this estate the outstanding balances are 324–396 hours old and this
product's half-life is **four hours**. Context Debt comes out at `1.000`,
signal `fail_closed`, and the class's own `0.25` tolerance is exceeded — so the
fabric assembles the product, passes every validation gate, and then declines
to attest that it is fit to act on.

**The $9,325,000,000 figure is still printed.** The fabric may know what it
calculated without being willing to say the calculation is fit to serve.
Withholding is a refusal of *fulfillment*, not of *response* (`D-IMPL-251`), so
the run exits `0` and discloses the determination, the measured Debt, the
tolerance that was not met and the authority that set it.

**Nothing was calibrated to make it serve.** Not the half-life, not the
evidence, not the debt calculation. A four-hour window widened to fit old demo
data would make every later run lie about how current its money figures are.

### Every determination is replayed — served or withheld

The decision record is written **before** the response is released
(`D-IMPL-256`), through the same writer, the same store and the same artifact
class on both branches. `D-IMPL-253` Q13 is explicit: *"Refusal is itself a
decision and deserves the same five-dimensional replay model. Do not create
second-class replay."*

Measured, the **withheld record is bigger than the served one** — 20,639 bytes
against 17,157 — because it additionally carries the refusal envelope, its
evidence and the debt breakdown. All five dimensions are populated on both. They
differ in exactly one place: dimension 5 carries a product content address and
`refusal_recorded: false` when served, and `no-product-address` with
`refusal_recorded: true` when withheld.

**Replay re-asks the effective question, not the caller's.** Every parameter is
recorded with the authority that set it, so the Regulated Consumer's record says
`debt_tolerance 0.10 [policy]` rather than the `1.0` it asked for. Under a
narrowing constraint those are different questions and only one was answered.

### Eight named consumers, one estate, one instant

```bash
make example-cp-05 SCENARIOS=1
```

runs the consumers declared in `artifacts/scenarios.yaml`
(`page/scenario-transcript.txt` is its output):

| Consumer | Asks for | Effective (authority) | Outcome |
|---|---|---|---|
| Default | nothing | `materiality 0.05` (default) · `debt_tolerance 0.25` (default) | WITHHELD |
| Detailed | `materiality 0.02` | `0.02` (caller) | WITHHELD |
| Material-Only | `materiality 0.10` | `0.10` (caller) | WITHHELD |
| Strict-Fitness | `debt_tolerance 0.05` | `0.05` (caller) | WITHHELD |
| Exploratory | `debt_tolerance 1.0` | `1.0` (caller) | **SERVED** |
| Regulated | `regulatory-large-exposure` + `debt_tolerance 1.0` | **`0.10` (policy)** — narrowed | WITHHELD |
| Appetite | `internal-appetite` + `materiality 0.10` | — | REFUSED at the request boundary |
| As-Of | `as_of 2026-06-30` | — | REFUSED at the request boundary |

**Family 77, gross 10,125,000,000, adjusted 9,325,000,000 and `D_c` 1.000 are
identical for every consumer that reached assembly.** The fabric does not
revise what it knows to suit who is asking. What moves is which slice is
projected, and whether the answer is attested.

**Two `maximum` constraints, two behaviors, and the difference is the
teaching.** A ceiling on `materiality` **refuses** the request by name; a
ceiling on `debt_tolerance` **narrows** it and withholds afterwards. A fitness
bar cannot be refused before fitness has been measured — materiality shapes the
answer, debt tolerance judges it.

## Run it

```bash
make venv
export CCF_CP_05_FLUREE_URL=http://<host>:8090
export CCF_CP_05_FLUREE_LEDGER=fibo-v2
export CCF_CP_05_POSTGRES_DSN='host=<host> port=5432 dbname=<db> user=<user> password=<pw>'
export CCF_CP_05_POSTGRES_SCHEMA=ccf_v2

make example-cp-05
```

Every request parameter is optional. Omitted, the run asks the question declared
in `artifacts/question.yaml`.

```bash
make example-cp-05 SCENARIOS=1
make example-cp-05 INTENT=internal-appetite
make example-cp-05 DEBT_TOLERANCE=1.0
make example-cp-05 DEPTH=2
make example-cp-05 MATERIALITY=0.10   # coarser: fewer entities enumerated
make example-cp-05 MATERIALITY=0.01   # finer: the anchor itself comes into view
make example-cp-05 LEI=<lei>
```

The default run reproduces `page/run-transcript.txt` byte for byte.

**Exit codes.** These are `run.py`'s own, each measured on the interpreter
rather than on a pipe. Invoked through `make`, the shell sees **make's** exit
status (`2`) with the program's code in its message — `make: *** [example-cp-05]
Error 5`. Call `.venv/bin/python examples/cp-05-credit-exposure-rollup/run.py`
directly if a script needs to branch on the code itself.

| Code | Meaning |
|---|---|
| `0` | served |
| `2` | a declared setting is unset — the message carries the remedy `backends.yaml` supplies |
| `3` | the graph leg could not be read; **not** degraded to an empty family |
| `4` | refused — unresolvable anchor, or an intent with no limit definition |
| `5` | refused — a request argument outside its declared bound, refused **by name and never clamped** |

No document in this example runs a bare `python`; use `.venv/bin/python` if you
invoke a module directly.

## The story

A credit officer is testing a proposed facility against a group limit, or
answering *"what do we actually have on this name?"* before a committee.

The anchor is **REGIS CORP** (`5493000Q1S5TJIDIQH89`) — a real LEI, a real
US-MN jurisdiction, a real SIC code. **The bank's book against it is
engineered**; no bank lends to Regis on these terms, because the lender does not
exist. The topology was built so both halves of the failure are demonstrable,
and calibrated so committed exposure is **49.4%** of the obligor's
XBRL-reported total debt — a plausible share, which the estate flags.

**Step 3 walks once.** 77 nodes at depth 3 (21 at depth 1, 49 at depth 2), of
which 19 carry an LEI and only 4 hold a material facility book. The family
reaches *outside* the Regis ownership group entirely — Avis Budget, Celanese,
XPO — bound in by cross-default. No ownership-only walk finds them; no
borrower-keyed query finds them either.

**Step 5.2 is where the product is won.** Regis guarantees RB Global at 100%,
and RB Global holds 800,000,000 of its own. Counted naively that exposure
appears twice. The dedup counts it once, and **gross ships beside adjusted** so
the consumer can see what the adjustment did — a single number is
indistinguishable from the wrong one.

**And the policy decides what counts.** The same anchor under
`internal-appetite` returns a different product: that limit definition sets
`counts_guarantees=false` and `counts_undrawn=false`, so no dedup applies and
undrawn availability is excluded. Different number, different content address,
**no code changed** — the definition is a row in `limit_definition`.

## Artifact-by-artifact

| File | What it holds |
|---|---|
| `spec/CP-SPEC-005_…md` | The specification. Everything else derives from it. |
| `artifacts/question.yaml` | The caller's vocabulary — anchor, pinned instant, declared parameters. Read-side; not Control Plane state. |
| `artifacts/ttl.yaml` | 4 hours, `from_decision`, and its ceiling as a separately reviewable number. |
| `artifacts/expected.yaml` | What the product should contain — **derived from the estate, never from a run**. |
| `artifacts/assembly-recipe.yaml` | §D.2 as data, one witness per step. |
| `artifacts/scenarios.yaml` | The eight named consumers and what each one teaches. Read-side: a fitness bar is something callers ask for, not something this deployment is permitted to do. |
| `artifacts/replay.yaml` | Where decision records go and under what artifact class. A separate document because the Control Plane's section vocabulary is closed and has no slot for it. |
| `page/run-transcript.txt` | The demonstrated run, byte-reproducible against the pinned instant. |
| `page/scenario-transcript.txt` | All eight consumers, same estate, same instant. |
| `backends.yaml` | Variable **names** and remedies. No host, port or credential. |
| `ccf_config.yaml` | The Control Plane document — half-life table, request contract, bounds, defaults. |
| `deployment.py` | The interpreter. Holds no domain value. |
| `assembler.py` | The five steps and the arithmetic. |
| `produce.py` | The spine, the four gates, and the typed `ContextProductContract`. |
| `run.py` | The client. Renders; recomputes nothing. |

## Whitepaper / CLAUDE.md sections exercised

- **§7.4 Context Operators** — one traversal over four predicate types; the
  operator registry's closed vocabulary (`traversal.typed-neighborhood`,
  `policy.principal-subgraph`) declared in `ccf_config.yaml`.
- **§7.6 Context Product Contract** — a typed `ContextProductContract` with
  `extra=forbid`; the three standard validation gates plus this product's own.
- **§7.7 Half-life and Context Debt** — a five-class `λ_c` table spanning
  ~2,190× and a fail-closed posture on the fastest class only. `D_c` is
  assessed from evidence — real `balance_as_of` dates, LEI coverage,
  reconciliation agreement — never from result cardinality.
- **§7.7.4–§7.7.8 fulfillment** — `refuse_over_tolerance` holds a gate-admitted
  `ServableProduct` to the one resolved tolerance. Debt measures; governance
  decides; the two are separate objects and separate steps.
- **§7.8 Control Plane vs Data Plane** — the limit definition is versioned
  policy read from the store, recorded in lineage, never defaulted.
- **§7.10 Decision Replay** — the five-dimension record, written before the
  response is released, on the served and the withheld branch alike. Lineage
  carries operators, ledger, policy version and the pinned instant; the content
  address reproduces.
- **CLAUDE.md §6.4 No-Hardcoding** — no anchor, threshold, half-life, host or
  ledger name appears in any `.py` file here.

## What to change first

**The anchor.** `artifacts/question.yaml::subject`. Nothing in the code names an
LEI.

Then `intent` — the three limit definitions in `ccf_v2.limit_definition` are
real policy rows, and changing which one you ask under changes the answer
without touching a line of code. That is the point of the rung.

Then `depth`. It is part of product identity, not a tuning knob: 21 / 49 / 77
nodes at depths 1 / 2 / 3 are three different answers with three content
addresses.

## What would fail

- **A depth above 5** is refused by name, never clamped — clamping would answer
  a question the caller did not ask and label it as theirs.
- **An unknown intent** refuses and lists the intents that exist. There is no
  default, because a defaulted limit regime is the confidently-wrong number this
  product exists to prevent.
- **An unresolvable anchor** refuses; it does not return an empty rollup. A
  zero-exposure answer for a real obligor and a no-such-obligor answer are
  different facts.
- **An unreachable graph** exits `3` rather than reporting a one-node family. An
  unreachable store and a store with no matching edges are different facts.
- **A double-subtracting dedup** trips the reconciliation guard: adjusted
  exceeding gross is arithmetically impossible.
- **A `debt_tolerance` above 1.0 or below 0.0** is refused by name at the
  request boundary, like any other out-of-domain argument.
- **A `debt_tolerance` above a registered policy ceiling** is *not* refused —
  it is narrowed to the ceiling with authority `policy`, and the product is
  withheld afterwards if the observed Debt exceeds it. This is the SDK's only
  parameter-name-keyed branch and it is deliberate: fitness cannot be judged
  before it is measured.
- **A policy envelope left unbound** — or bound to a family the request did not
  name — is refused by `refuse_unbound_family_scope`, by name. Both directions
  were observed firing. If the guard were bypassed, the traversal returns
  nothing and the empty-operator guard catches it; that too was observed,
  against a positive control of 77.
- **A dedup whose obligor sits outside the measured family** would remove
  exposure the rollup never added. That one is *not* caught by the guard —
  `gross ≥ adjusted` does not watch for under-counting — and it is why
  `expected.yaml` is written from the estate rather than from a run. It is how
  the defect was found.
