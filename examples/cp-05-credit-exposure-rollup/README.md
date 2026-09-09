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

**The figure is NOT printed, and that changed.** Withholding is a refusal of
*fulfillment*, not of *response* (`D-IMPL-251`), so the run still exits `0` and
still answers — with the refusal's **disclosed shell**: the kind, the tolerance
that was not met, the authority that set it, and the replay reference. What it
does not carry is the determination itself.

The hand-composed spine printed `$9,325,000,000` beside a `withheld` flag,
because it computed the figure locally and decided fulfillment afterwards. On
the canonical path the **fabric** decides, and a refused caller sees exactly
what this deployment's disclosure policy permits — here `minimal`, so the
arithmetic is generalised and the lane undisclosed. That is the more correct
behaviour and it was preserved rather than "restored" for continuity
(`D-IMPL-298`).

The determination is not withdrawn. It was assembled, gated and recorded; a
consumer with a different fitness bar is served the same answer.

**Nothing was calibrated to make it serve.** Not the half-life, not the
evidence, not the debt calculation. A four-hour window widened to fit old demo
data would make every later run lie about how current its money figures are.

### Every determination is replayed — served or withheld

The decision record is written **before** the response is released
(`D-IMPL-256`), through the same writer, the same store and the same artifact
class on both branches. `D-IMPL-253` Q13 is explicit: *"Refusal is itself a
decision and deserves the same five-dimensional replay model. Do not create
second-class replay."*

Measured, the **withheld record is bigger than the served one** — 20,075 bytes
against 16,873 — because it additionally carries the refusal envelope, its
evidence and the debt breakdown. (Both shrank slightly at the canonical
adoption: the payload no longer duplicates envelope state, so the record no
longer carries it twice.) All five dimensions are populated on both. They
differ in exactly one place: dimension 5 carries a product content address and
`refusal_recorded: false` when served, and `no-product-address` with
`refusal_recorded: true` when withheld.

**Replay re-asks the effective question, not the caller's.** Every parameter is
recorded with the authority that set it, so the Regulated Consumer's record says
`debt_tolerance 0.10 [policy]` rather than the `1.0` it asked for. Under a
narrowing constraint those are different questions and only one was answered.

### A Context Product is not just a payload

This is the lesson cp-05 proved most concretely, and it is visible in the
transcript under two headings:

> **The business payload answers the question. The governed envelope explains
> the conditions under which that answer was assembled, authorized, withheld,
> served, and replayed.**

The rule for deciding which is which: *if a value explains **what the answer
is**, it belongs to the payload; if it explains **whether, why or how** the
answer was governed, it belongs to the envelope.*

| Business answer | Governed context |
|---|---|
| anchor, family, entities | fulfillment outcome |
| exposure facts, gross / adjusted | Context Debt and its factors |
| material entities, residuals | effective-parameter authority |
| findings, guarantee-dedup detail | lineage, content address |
| scope-only request values — depth, materiality, basis, flags | `expires_at` and its TTL anchor |
| | obligation in force, replay record |

**cp-05 used to carry both in one payload.** Adopting the canonical path
(`D-IMPL-298`) surfaced at least seven envelope members the old payload
duplicated into business content: the effective request, `expires_at`, lineage,
the content address, Context Debt, the replay block and fulfillment. Keeping
them apart is not tidiness — it is what makes the content address a function of
**the answer** rather than of how the answer was authorised, so two callers
whose parameters resolved by different authorities to the same business content
share an address, and the *record* is what tells their determinations apart.

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

### An MCP door in front of it

```bash
make example-cp-05-server        # stdio; the client spawns it
```

`server/serve.py` exposes the governed path as an authenticated, entitled MCP
tool that records every denial as a decision. It re-implements no part of the
assembly, the gates, the debt assessment, the tolerance comparison or the
replay record — those are all behind `produce.py::produce_governed`.

**Two things the door was built to measure** (spec §D.10):

1. **It proves a record exists; it does not read it.** A served product whose
   payload claims 9,999 family members, wrapping a replay record whose
   dimension 1 observed 77, crosses the boundary unremarked. Both operands are
   in the door's hand and the comparison is not made.
2. **Measured after the migration, the door is transport and nothing else.**
   204 executable lines, and **zero** of them governance or replay logic — the
   split is 60 in `door` (entitlement, credential, perspective, `build_egress_server`),
   44 module-level, 41 translating and delegating, 31 shaping refusals the door
   itself owns, and the remainder the stdio entry point and a five-field record.
   Before Step 1 this measurement would have been meaningless: the door wrapped
   a hand-composed spine, so "MCP cost" and "governance cost" were the same
   number.

   **The door got thinner, not fatter.** It used to run a full
   `refuse_request` conformity check of its own; `D-IMPL-303` removed it,
   because a door owns transport, address and standing, while the resolver owns
   contract-aware decoding, conformity, effective resolution and the governed
   outcome. **The door is intentionally dumb about logical parameter types** —
   it transports wire-stable lexical values and the resolver, which holds the
   declaration, converts and judges them.

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
| `5` | refused — a request argument outside its declared bound, refused **by name rather than silently narrowed** |

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
| `artifacts/replay.yaml` | Where decision records go and under what artifact class. **Its header records a finding the SDK has since closed:** the Control Plane's section vocabulary had no `replay:` slot, so this lived outside it. Phase 24.10's `R-12` added the section, and `ccf_config.yaml` now declares the binding directly — the resolver consumes it, with no argument and no module constant. The document remains as the record of that finding. |
| `page/run-transcript.txt` | The demonstrated run, byte-reproducible against the pinned instant. |
| `page/scenario-transcript.txt` | All eight consumers, same estate, same instant. |
| `page/template.html` | The documentation page's authored spine, with every file behind a placeholder. |
| `page/build_page.py` | The generator. Reads the two committed transcripts and the declared artifacts, verifies its own snapshot against the tree, and **refuses** a build whose refused transcript carries the served figures. |
| `server/door.yaml` | The door's governance values — scope, issuer, audience, principal, role, tool prose. No host, port or credential. |
| `server/serve.py` | The MCP door. A resolver adapter and a `build_egress_server` call; no governed logic of its own. |
| `backends.yaml` | Variable **names** and remedies. No host, port or credential. |
| `ccf_config.yaml` | The Control Plane document — half-life table, request contract, bounds, defaults. |
| `deployment.py` | The interpreter. Holds no domain value. |
| `assembler.py` | The five steps and the arithmetic. |
| `produce.py` | **The adapter into the SDK, not a spine.** Boot, acquire, assemble the domain truth, hand `GovernedResolver` its four extension points, call it. The gates, the contract, Debt placement, fulfillment, refusal shaping, replay and serve are the SDK's and appear nowhere here (`D-IMPL-298`). |
| `run.py` | The client. Renders from **two sources** — the business payload and the governed envelope — and recomputes nothing. |

## The documentation page

**Published artifact `5734f184-24f5-4f55-ac5d-57c1467b9669`** —
[Credit Exposure Rollup · cp-05](https://claude.ai/code/artifact/5734f184-24f5-4f55-ac5d-57c1467b9669).
Built from the tree at `dbcdd43a`, 425,392 bytes,
sha256 `e96ae35ae25546bc79a2c579c1f2adc337bc5ff9176f4c4c937085d70aa993f3`.

```bash
.venv/bin/python examples/cp-05-credit-exposure-rollup/page/build_page.py
```

The rendered `page/cp-05.html` is **not committed** — `page/build_page.py` and
`page/template.html` are, and `.gitignore` enforces the split. Committing the
rendered page would put every embedded file in the tree twice, and the copies
would drift the first time an artifact changed and nobody remembered to
republish.

**The page is generated from the two committed transcripts, never from a live
run.** At a four-hour half-life that is not a convenience: a page that re-ran
the product on every build would print whatever the estate said today, and
today's answer is *guaranteed* to differ from the pinned one, because this
rung's freshest input decays faster than the gap between two sittings.

**The page shows each consumer exactly what the fabric showed it.** The
withheld panel is fed from `page/run-transcript.txt` alone — the observed Debt
reads `undisclosed`, and the figures do not appear. This repository *knows*
those figures, because the served consumer in `page/scenario-transcript.txt`
receives them, and filling them into the withheld panel would undo, in
documentation, precisely the boundary the product draws.
`build_page.py::_refuse_cross_disclosure` makes that checkable rather than
merely intended: a build whose refused transcript contains the served figures
refuses. The served panel is **lifted verbatim** from the scenario transcript
rather than retyped, so both panels are the same kind of evidence.

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

- **A depth above 5** is refused by name rather than silently narrowed, and
  the refusal says which bound it crossed. Measured: `6` is refused by this
  class's own declared maximum of 5 (`D-IMPL-259`), `9` by the Fluree operator's
  technical maximum of 6 (`D-IMPL-253` Q21). Narrowing either would answer a
  question the caller did not ask and label it as theirs.
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
