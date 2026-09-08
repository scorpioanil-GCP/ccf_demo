# Credit Exposure Rollup — what it does, and why the ordinary answer is wrong

A report tells you what the data says. A **Context Product** tells you what you
may rely on, who may rely on it, how long it stays good, how complete it is —
and refuses rather than guessing.

**What is new at this rung:** the first product where the *arithmetic* is the
architecture. Rungs 1–4 assembled facts. This one adds them up, and adding them
up correctly requires a graph.

---

## The pipeline, in three rows

Every difference between the runs below comes from one of these three.

| | What it does | Layer |
|---|---|---|
| **Resolve** | Turns one LEI into a canonical obligor. Refuses if it does not exist — an empty answer and "no such company" are different facts. | L2 · assembly |
| **Policy** | Loads the group-limit definition bound to the caller's `intent`, and records which version produced the number. | Control Plane |
| **Contract assembly** | Seals the answer: measures, findings, lineage, expiry, and a content address over the whole thing. | L6 · delivery |

---

## Run 1 — the demonstrated question

```bash
make example-cp-05
```

```
  FAMILY
    77 nodes reached at depth 3; 19 carry an LEI; 5 hold a material facility book

  EXPOSURE                     committed        outstanding           undrawn
    gross              10,125,000,000      7,456,090,501     1,656,400,215
    adjusted            9,325,000,000      6,870,556,262     1,449,221,862
    guarantee dedup      -800,000,000   (1 case(s), 7.90% of gross)

  CONTEXT DEBT — confidence in the assembled truth, not in the projection
    debt 1.0000   signal fail_closed

  FULFILLMENT  WITHHELD  D_c 1.000 > tolerance 0.25 (default)
```

**Read that last line carefully. The product was built, it passed every
validation gate, the number is printed — and the fabric declined to say it is
fit to act on.** That is not an error and it is not a bug in the demonstration.
It is the whole point of the rung, and Run 4 below is where it is explained.

### What you'd have missed

**A credit officer asking "what do we have on Regis?" of an ordinary data
product gets `145,000,000`.** The family actually owes **`10,125,000,000`**.

That is not a rounding difference. It is a **70-fold understatement**, returned
without error, in a plausible size for a mid-cap borrower — and nothing about it
looks wrong. A facility approved against that number is approved against a limit
test that never happened.

The number is wrong because exposure is not additive across a list of legal
entities. Guarantees and cross-default clauses move risk across company
boundaries, and a query keyed on the borrower never looks at them.

### How it works

`assembler.py::walk` issues **one** traversal over four relationship types —
ownership, ultimate consolidation, guarantee, cross-default — in both
directions, against the Fluree ledger. `assembler.py::enrich` then resolves all
19 LEI-bearing members to their facilities in **one** query, not nineteen. The
predicate list is in `ccf_config.yaml`; the depth is in
`artifacts/question.yaml`.

---

## Run 2 — the same question under a different credit policy

```bash
make example-cp-05 INTENT=internal-appetite
```

```
  EXPOSURE                     committed        outstanding           undrawn
    gross              10,125,000,000      7,456,090,501     1,656,400,215
    adjusted           10,125,000,000      7,456,090,501                 0
    guarantee dedup                 0   (0 case(s), 0.00% of gross)
```

### What you'd have missed

**The same family, the same graph, a different number — and no code changed.**

Under `internal-appetite` the bank's own policy says guarantees do not net and
undrawn commitments do not count. So the guarantee adjustment does not apply and
undrawn availability drops to zero. Under `group-limit-test` both count.

An institution that hard-codes one interpretation cannot answer both questions,
and will not notice it is answering the wrong one. Here the interpretation is a
**row in a table with a version**, and the version is recorded on the answer —
so a rollup taken last quarter can be re-read against the policy that was
actually in force when it was taken.

### How it works

`assembler.py::load_limit_definition` reads `ccf_v2.limit_definition` by
`intent` and **refuses if there is no row** — there is deliberately no default.
The three columns that move the number are `counts_guarantees`,
`counts_undrawn` and `connection_basis`. The version travels into the contract's
lineage as `policy_version`.

---

## Run 3 — asking for something the product will not do

```bash
make example-cp-05 DEPTH=6
make example-cp-05 DEPTH=9
```

```
  Refused: depth: 6 lies above the declared maximum 5 of this class's request
  contract — the parameter's valid domain, declared beside its type and refused
  by name rather than substituted (D-IMPL-259)

  Refused: depth: 9 exceeds the technical maximum 6 of capability
  'traversal-depth' on 'fluree/credit-risk.exposure-rollup'; the limit is the
  substrate's and is refused by name rather than silently narrowed
  (D-IMPL-253 Q21) [authority: technical]
```

*(Correction of record: an earlier draft of this document quoted a refusal
message that no run ever produced — invented from the shape of the argument
rather than copied from output. Both messages above are verbatim. The error is
recorded here rather than quietly amended, because a plausible fabricated quote
is exactly the failure this whole product exists to argue against.)*

### What you'd have missed

**Most systems would quietly give you depth 5 and call it depth 9.**

That is the failure this refusal exists to prevent: an answer to a question
nobody asked, wearing the label of the question they did ask. A committee paper
citing "exposure to five levels of ownership" that was actually computed to
three is not a smaller answer — it is a false one.

**And notice that the two refusals blame different parties.** Depth 6 is inside
what the store can do and outside what *this product offers*; depth 9 is outside
what the **store** can do at all. One is a product decision, the other a
substrate limit, and a caller who is told which is which knows whether to ask
for a different product or to stop asking.

### How it works

`produce.py` passes both the class's declared domain
(`ccf_config.yaml::request_contract.argument_bounds`) and the backend's own
ceiling (`operators.traversal.typed-neighborhood.depth_limit`) to
`resolve_effective_request`, which refuses by name and names the authority.
Neither bound is a constant in code.

---

## Run 4 — the answer the fabric refuses to stand behind

This is the **demonstrated** run. Nothing extra is passed.

```bash
make example-cp-05
```

```
  CONTEXT DEBT — confidence in the assembled truth, not in the projection
    debt 1.0000   signal fail_closed
    freshness   0E-18    from 15 real balance_as_of dates
    completeness 0.2467  19/77 family members carry an LEI and can be checked
    consistency  1       0 of 5 reconciliations used here disagree

  FULFILLMENT  WITHHELD  D_c 1.000 > tolerance 0.25 (default)
```

### What you'd have missed

**Every system in the building would have served this number.**

The arithmetic is right. The traversal is right. The dedup is right. The
`9,325,000,000` is the correct guarantee-adjusted exposure for this family. And
the balances it was computed from are **two weeks old**, against a loan book
whose drawdowns and repayments land intraday.

A credit officer taking a limit decision on a two-week-old outstanding balance
is taking it on a number that was true and is not. Nothing in an ordinary
report says so, because an ordinary report has no way to know how fast its own
inputs go stale.

**The fabric knows, because someone declared it.** `ccf_config.yaml` says the
outstanding-balance class has a **four-hour** half-life. The evidence says the
balances are 324–396 hours old. Freshness scores `0`. Context Debt is `1.000`.
The product's own default says a consumer should not act on anything above
`0.25`. So the fabric hands over the number **and** the reason it will not vouch
for it.

**What it does not do is hide the number.** Withholding fulfillment is not the
same as refusing to respond. The determination is disclosed in full — what was
calculated, from what, how confident the fabric is, what bar was not met, and
who set that bar. The caller decides what to do with a number the fabric will
not attest to; the fabric's job is to make sure nobody mistakes it for one it
would.

### How it works

Three separate things, deliberately kept apart:

1. **The evidence** — real `balance_as_of` dates, LEI coverage, reconciliation
   agreement. Read from the estate; nothing is manufactured. Zero results are
   not zero knowledge, and cardinality never determines Debt.
2. **The measurement** — `D_c = 1 − min(freshness, completeness, consistency)`,
   the weakest link. This is a *number about the fabric's confidence*, and it is
   the same for every consumer.
3. **The judgment** — `refuse_over_tolerance` compares that number against the
   one tolerance in force. This is where a consumer's requirements enter, and
   nowhere else.

Debt does not refuse the request. Governance uses Debt to decide whether
fulfillment is permitted.

---

## Run 5 — the same answer, two consumers, two verdicts

```bash
make example-cp-05 SCENARIOS=1
```

```
  Exploratory Consumer
    effective    debt_tolerance=1.0(caller)
    assembled    family 77   gross 10,125,000,000   adjusted 9,325,000,000
    debt         1.000  (fail_closed)
    fulfillment  SERVED    against tolerance 1.0 (caller)

  Regulated Consumer
    effective    debt_tolerance=0.10(policy)
    assembled    family 77   gross 10,125,000,000   adjusted 9,325,000,000
    debt         1.000  (fail_closed)
    fulfillment  WITHHELD  against tolerance 0.10 (policy)
```

### What you'd have missed

**Both consumers asked for the same thing and asked to be allowed to act on it
regardless of confidence. One was permitted; one was not — and the one that was
not never asked for a lower bar.**

The Regulated Consumer requested a tolerance of `1.0`, exactly like the
Exploratory one. It is preparing a **regulatory large-exposure return**, and the
bank's policy says such a return may not be founded on context the fabric holds
in low confidence. That registered constraint capped the request at `0.10`. The
consumer's own stated willingness to act was overruled — visibly, with the
authority named on the record.

This is what "the consumer owns fitness, **within policy boundaries**" means in
practice. An analyst sizing a deal may knowingly work from a shaky number. The
same analyst may not file it.

**And the underlying answer never moved.** Family 77, gross `10,125,000,000`,
adjusted `9,325,000,000`, Debt `1.000` — byte-identical for both. The fabric
does not revise what it knows to suit who is asking. It revises only whether it
is willing to attest that what it knows is fit for that particular use.

### How it works

Both consumers' requests go through `resolve_effective_request`, which folds
three authorities **exactly once** in the order `policy > caller > default`. The
Exploratory Consumer's `1.0` survives because no constraint applies to its
intent. The Regulated Consumer's `1.0` is narrowed to the policy's `0.10`, and
the record says `authority=policy` so a reader can see it happened.

**One subtlety worth knowing.** Elsewhere in this product, a policy ceiling
**refuses** a request rather than narrowing it — ask for a `materiality` of 10%
under an internal-appetite review and you are told no, by name. Debt tolerance
is the one exception, and there is a reason: you cannot refuse someone's
confidence requirement before you have measured your confidence. The bar is
bound at request time; the comparison happens after the answer exists.

---

## Run 6 — the decision is written down whether or not it is served

Every run above wrote a **decision record** before it printed anything.

```
  DECISION REPLAY — written BEFORE the response was released
    outcome     withheld   (20639 bytes persisted)
    1 fabric    boundary 2026-09-07T12:00:00+00:00  touched 77 entities
    2 policy    policy@31805dcb…
    2 policy    limit_definition@limit_definition/group-limit-test
    3 model     assembly_mode=algorithmic  model=none
    4 role      PRIN-CRO-001 / credit-officer
    5 content   debt 1.000  refusal recorded: True

    WHAT REPLAY RE-ASKS — the EFFECTIVE question, not the caller's
      debt_tolerance         0.25 [default]
      materiality            0.05 [default]
```

### What you'd have missed

**Most audit trails record what was delivered. This one records what was
decided — including the decision not to deliver.**

That difference matters more than it sounds. Six months from now, a reviewer
asking *"why did the fabric refuse the credit committee on the 7th?"* has an
answer: which state was read, which two credit policies were in force, which
role was asking, what the measured confidence was, and what bar it failed. The
withheld record is actually **larger** than the served one, because it carries
the reason as well as the result.

**And it records the question that was answered, not the question that was
asked.** The Regulated Consumer asked to be allowed to act at any confidence.
Its record says `debt_tolerance 0.10 [policy]`. A trail that stored what the
caller typed would show a request that was never honored and hide the constraint
that overruled it — which is the one fact a reviewer most needs.

### How it works

`produce.py::_record_and_release` builds one
`ccf.replay.record::DecisionReplayRecord` and routes it two ways:
`ccf.replay.serve::serve` when the product is delivered, and
`ccf.replay.serve::record_refusal` when it is withheld. Same writer, same store,
same artifact class — `D-IMPL-253` Q13 requires it: *"Refusal is itself a
decision and deserves the same five-dimensional replay model. Do not create
second-class replay."*

The ordering is not a convention. A delivered product is **what the successful
write returns** — there is no path through `serve` that hands back a product
whose record failed to persist, because the product comes out of the same call
that wrote it.

---

## What the replay record caught that nothing else did

This is worth its own heading, because it is the most useful thing that happened
while this rung was built.

The product had been answering **77 family members** for the whole build. Every
gate passed. The lineage was consistent. The numbers reconciled against public
filings. And the answer was coming from a traversal that **never passed through
the policy envelope** — the operator that decides which entities this principal
is allowed to see was being invoked, and its result thrown away.

Nothing noticed, because nothing was looking at the right thing:

- **Lineage strict equality** passed — the operator genuinely *was* invoked.
- **The empty-operator guard** passed — the traversal genuinely *did* return 77.
- **Every validation gate** passed.

What caught it was building dimension 1 of the record, which asks a question no
gate asks: *how many entities did this determination actually touch?* The answer
came back **0** for a product reporting 77. The engine's properly-composed
pipeline was correctly returning nothing, while the served answer came from
somewhere else entirely.

**The fix is now sabotage-verified in both directions.** Leave the policy
envelope unbound and the run refuses by name. Bind it to a different family and
the run refuses by name. Bypass the refusal and mint the family under a value the
request did not ask about, and the traversal returns nothing — caught by the
empty-operator guard, against a positive control of 77. The answer is unchanged
at 77 members and $9,325,000,000; what changed is that it now goes through the
gate it always claimed to.

---

## The assembler lesson this rung teaches

> **Acquisition may use backend-specific logic; decision logic must execute
> through the declared fabric mechanisms.**

Reading someone else's graph is acquisition — it is backend-specific by nature,
and it only *populates* the fabric. Deciding what the family IS must run through
the operator the Control Plane registered, over the fabric's own state, at the
instant the request named.

An earlier build of this example answered from the acquisition read directly. It
returned the same 77 entities. It was still wrong: the Control Plane had
permitted a traversal that never ran, and a hand-rolled walk had run one it
never saw. Nothing in the output would have told you.

## Why you can trust these numbers

**The snapshot.** Every figure above comes from one pinned question asked at
`2026-09-07T12:00:00+00:00` against Fluree ledger `fibo-v2` and PostgreSQL
schema `ccf_v2`. The run reproduces byte for byte; the content address
`299d0e9e…` is a hash over the entire answer, so it only reproduces if every
input did.

**Entity identities are real.** Regis Corporation, Avis Budget, Celanese and XPO
are real companies with real LEIs. **The bank's book against them is
engineered** — no bank lends on these terms, because the lender does not exist.
The topology was built so both halves of the failure are demonstrable, and
calibrated so committed exposure is 49.4% of the obligor's publicly reported
debt, which the estate flags as a plausible share.

**No number here is a claim about any real company's borrowings.**

---

## What these runs do NOT show

- **No scale test.** 77 nodes and 15 facilities. Where the latency cliffs are,
  and what happens at 10× or 100×, is not answered here.
- **The reconciliation guard has been observed firing only on a constructed
  case**, not on a live double-subtraction.
- **The threshold sweep is narrow, and the book is concentrated.** Measured:
  1% enumerates 5 entities (the anchor's own 145,000,000 book comes into view),
  2% and 5% both enumerate 4, and 10% enumerates 3 as RB Global's 800,000,000
  falls into the residual. Five entities hold facilities at all, so the
  threshold has few places it can bite. A family with a long tail would
  exercise it harder.
- **Only one thing makes this product refuse fulfillment here — staleness.**
  Completeness is `0.2467` and consistency is `1`, but freshness is `0` and
  `D_c` is the weakest link, so freshness alone decides the outcome. What a
  *completeness*-driven withholding looks like is not demonstrated.
- **No MCP delivery yet.** The typed contract crosses the boundary; the
  authenticated door around it is not built.
- **One store pair.** Postgres and Fluree. No document store, no A2A, no second
  institution.

---

## Vocabulary — two readings per term

| Term | What it means to you | What it is in the system |
|---|---|---|
| **Content address** | A tamper-evident seal on one answer | `sha256` over the canonical bytes of the served product, excluding `expires_at` |
| **Gross vs adjusted** | Before and after removing double-counted guarantees | Two `Money` records; both required fields on the contract |
| **Guarantee dedup** | Counting a guaranteed subsidiary's debt once, not twice | `assembler.py::aggregate` step 5.2, gated on `counts_guarantees` |
| **Materiality** | Small positions are summarized, not listed | A share of gross committed; does **not** apply to cross-default-only members |
| **Connected without exposure** | Companies your risk touches that hold none of your loans | Family members with no `facility` row — 14 of them here |
| **TTL, `from_decision`** | The answer is good for the decision you are taking now | `expires_at = asked_at + 14400s`; no entity timestamp involved |
| **Policy version** | Which credit policy produced this number | A `limit_definition` row id, carried in contract lineage |
| **Refusal** | The product declining rather than guessing | A typed exit with a reason; codes 2–5 |
| **Context Debt (`D_c`)** | How much the fabric's confidence falls short | `1 − min(freshness, completeness, consistency)`; measured from evidence, identical for every consumer |
| **Debt tolerance** | The most uncertainty *you* will act on | A resolved request parameter; folded once from class default, caller and policy |
| **Withheld** | The number is shown; the fabric will not vouch for it | `refuse_over_tolerance` on a gate-admitted product; a refusal of fulfillment, not of response — exit `0` |
| **Decision record** | The written account of what was decided and why | A five-dimension `DecisionReplayRecord`, appended before the response is released — for a refusal exactly as for a delivery |
| **Policy envelope** | What this principal is allowed to see | `policy.principal-subgraph`, bound at request time to the one family asked about; an unbound envelope admits nothing and is refused by name |

---

## Where each claim is enforced

This is the section that separates a demonstration from a guarantee.

| Claim | Mechanism | What fails if it stops being true |
|---|---|---|
| The family is traversed, not listed | `assembler.py::walk`, one walk over four predicates | Empty-operator guard: a traversal returning nothing refuses |
| Lineage describes the run | `produce.py`, five operators declared | Lineage strict-equality gate |
| The answer expires | `artifacts/ttl.yaml`, 4h `from_decision` | TTL-bounds gate |
| The dedup never over-subtracts | `assembler.py::reconciliation_guard` | Gate raises when adjusted > gross — **observed firing** |
| Policy decides what counts | `limit_definition`, read by `intent` | A missing definition refuses; there is no default |
| Bounds are declared, not coded | `ccf_config.yaml::argument_bounds` | Out-of-bound arguments refuse by name |
| No domain value lives in code | `deployment.py` holds none | The No-Hardcoding lint |
| Debt is measured, not asserted | `deployment.py::assess_context_debt` reads real `balance_as_of` dates, LEI coverage and reconciliation rows | A debt figure derived from result cardinality would be a number about the query, not about the knowledge |
| A stale answer is not attested | `produce.py` -> `run_gates` -> `refuse_over_tolerance` | Without the last call a producer that never checks is indistinguishable from one whose tolerance was met — the debt figure becomes an ornament |
| Fitness is the consumer's, within policy | `resolve_effective_request` folds `policy > caller > default` once | A second fold anywhere downstream is where a product re-acquires the power to overrule its own governance |
| Every decision is written down | `serve` / `record_refusal`, before the response is released | A delivery whose record failed to write cannot happen — the product is what the successful write returns |
| The walk sees only what the principal may | `policy.principal-subgraph`, bound per request, chained ahead of the traversal | An unbound envelope admits nothing and is refused by name; a bypassed one served 77 entities that had passed through no policy at all — the defect this rung found |
| The answer reproduces | Content address over canonical bytes | The pinned transcript diff |

**One gap, named rather than left implicit.** `gross ≥ adjusted` catches
double-subtraction. It does **not** catch under-counting — a dedup whose obligor
sits outside the measured family would remove exposure that was never added, and
the gate would stay green. That defect was found by an expectation written
independently of the program, not by a gate, and the rule it produced — a dedup
is valid only when both parties are inside the measured family — is now enforced
in the assembler.
