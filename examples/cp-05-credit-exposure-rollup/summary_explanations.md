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
    77 nodes reached at depth 3; 19 carry an LEI; 4 hold a material facility book

  EXPOSURE                     committed        outstanding           undrawn
    gross              10,125,000,000      7,456,090,501     1,656,400,215
    adjusted            9,325,000,000      6,870,556,262     1,449,221,862
    guarantee dedup      -800,000,000   (1 case(s), 7.90% of gross)
```

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
make example-cp-05 DEPTH=9
```

```
  Refused: depth 9 is outside the declared bound [1, 5]. Refused BY NAME, never
  clamped — clamping would answer a question the caller did not ask and label it
  as theirs.
```

### What you'd have missed

**Most systems would quietly give you depth 5 and call it depth 9.**

That is the failure this refusal exists to prevent: an answer to a question
nobody asked, wearing the label of the question they did ask. A committee paper
citing "exposure to five levels of ownership" that was actually computed to
three is not a smaller answer — it is a false one.

### How it works

`produce.py` reads the bound from `ccf_config.yaml::request_contract.argument_bounds`
and refuses by name. The bound is declared data, not a constant in code.

---

## Why you can trust these numbers

**The snapshot.** Every figure above comes from one pinned question asked at
`2026-09-07T12:00:00+00:00` against Fluree ledger `fibo-v2` and PostgreSQL
schema `ccf_v2`. The run reproduces byte for byte; the content address
`b4963e01…` is a hash over the entire answer, so it only reproduces if every
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
- **The anchor is filtered out of its own rollup.** At the declared materiality
  of 5%, Regis's own 145,000,000 is 1.43% of the family and does not appear in
  the enumerated entities. Arithmetically right; as a product behavior,
  surprising. It is recorded rather than special-cased, because whether the
  anchor should be exempt from its own materiality floor is a decision for the
  product owner, not for the example.
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
| The answer reproduces | Content address over canonical bytes | The pinned transcript diff |

**One gap, named rather than left implicit.** `gross ≥ adjusted` catches
double-subtraction. It does **not** catch under-counting — a dedup whose obligor
sits outside the measured family would remove exposure that was never added, and
the gate would stay green. That defect was found by an expectation written
independently of the program, not by a gate, and the rule it produced — a dedup
is valid only when both parties are inside the measured family — is now enforced
in the assembler.
