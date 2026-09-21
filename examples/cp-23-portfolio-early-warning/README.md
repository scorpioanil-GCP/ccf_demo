# CP-23 — Portfolio Early-Warning / Concentration

**Rung 23 of the Context Product ladder.** One coverage book's
proactive-monitoring state — and the first product on the ladder whose
**subject is a population**.

> **This is a coverage probe, not a Portfolio Management application.** Four
> limbs, chosen because between them they exercise population-grain assembly,
> multi-signal early warning, policy-conditioned views, freshness and debt
> propagation, and concentration. `spec/CP-SPEC-023_...md` §0.3 records what is
> deliberately left out and why.

> **Illustrative calibration:** This example runs against a point-in-time
> demonstration estate rather than continuously refreshed production data.
> Freshness half-lives and related thresholds are calibrated to make the
> governed behavior observable in that snapshot. They demonstrate how the SDK
> applies these controls and should not be interpreted as recommended
> production coverage-policy thresholds.

## What this demonstrates

**Three things the first nineteen rungs did not prove**, none needing a new
SDK symbol:

1. **A subject that is a POPULATION.** Every earlier rung anchored on one
   thing. Here 25 clients are the assembly unit and the measures are set
   properties.
2. **Context Debt as a property of a population** — the SDK's own
   `compose_debt_factors` under the `D-IMPL-104` worst-factor rule: per-factor
   minimum strength across members, never `max(member D_c)`.
3. **Multi-class signal freshness aggregated across members** — five classes
   whose ages run 12 to 53 days, so the book's freshness is a distribution.

It also **corrects Gate 0**: CP-23 was predicted to be the first *low-road*
rung, measured against cp-05's 2,382 lines. It is not. `ExecutionResult.touched_entities`
returns every entity URI in the composed view and the governed resolver threads
it into the gate sequence, so on the paved road `touched_entities` is never
`None` and the **A10 hazard does not arise here**.

## The two rulings this rung carries

**`Q1` — population debt uses the SDK's combinator.** Members are passed to
`compose_debt_factors` as the composed sequence. The API's contract names
*children*; calling it with members is the ruled reuse and the naming is
recorded as friction, not repaired. The payload is **understandable by
factor**: it names the member each weak factor came from, so a weak member
cannot disappear behind a stronger aggregate.

**`Q2` — the deployment canonicalizes the member set.** CP-23 knows its
membership is semantically a set, so `produce.book_question` sorts and
deduplicates before the effective request exists. `[A,B,C]` and `[C,B,A]` are
**one determination**; a genuinely different membership is a **different** one.
SDK list canonicalization is not changed globally.

## Running it

```bash
export CCF_CP_23_POSTGRES_DSN=...   CCF_CP_23_POSTGRES_SCHEMA=ccf_v2
export CCF_CP_23_FLUREE_URL=...     CCF_CP_23_FLUREE_LEDGER=fibo-v2
export CCF_CP_23_TOKEN_COVERAGE=... CCF_CP_23_TOKEN_CREDIT=... \
       CCF_CP_23_TOKEN_PRODUCT=...  CCF_CP_23_TOKEN_UNGRANTED=...

make -s example-cp-23
make -s example-cp-23 PRINCIPAL="--principal PRIN-CO-002" INTENT="--intent credit-review"
make -s example-cp-23 SEVERITY_FLOOR="--severity-floor 0.45"
```

## The three roles

The role names are **the estate's own** — `ccf_v2.banker.role` holds exactly
`coverage`, `credit` and `product`, so nothing is invented that the estate
already says.

| credential | role | what the book looks like |
|---|---|---|
| `CCF_CP_23_TOKEN_COVERAGE` | `coverage` | every member, utilization, signals |
| `CCF_CP_23_TOKEN_CREDIT` | `credit` | and covenant history and concentration |
| `CCF_CP_23_TOKEN_PRODUCT` | `product` | only members that have a facility |
| `CCF_CP_23_TOKEN_UNGRANTED` | — | granted nothing (negative control) |

**A member the role excluded still counts against completeness** — a role that
sees 14 of 25 members cannot reach completeness 1.0, or the entitlement would
look free. A member the *caller* narrowed away does not count, because
narrowing your own question denies you nothing.

## Known limitations

Measured and classified in `FINDINGS.md`. The ones a reader meets first:

- **Raising the severity floor has a real cost.** Narrowing what the book looks
  at thins its evidence, debt rises, and above tolerance the product is
  **withheld** rather than served thin. That is the SDK working.
- **On this book the ruled debt law and `max(member D_c)` happen to agree**,
  because the member weakest on freshness also sits at the completeness floor.
  A positive control shows they differ in general.
- **The covenant limb is genuinely quiet**: the estate's only two breaches are
  both cured. The member states zero active and two historical rather than
  being dropped.
- **Book concentration is not regulatory large exposure.** CP-21 owns that;
  `limit_definition`, `bank_capital` and `connection_basis` are named nowhere
  in this tree, and `PEW-G18` fails if they ever are.

## Gates

19 declared gates, `PEW-G01`..`PEW-G19`, in `artifacts/gates.yaml`, each claimed
by an executing test under `tests/examples/test_cp_23_*.py`. **All nineteen
observed red** under their own sabotage; none is `unavailable`.

## Specification

`spec/CP-SPEC-023_Portfolio_Early_Warning_Concentration.md`, authored to
Context Product Specification Standard v0.3 before any code existed, with
Dave's Gate-2 rulings folded in at §F.4.
