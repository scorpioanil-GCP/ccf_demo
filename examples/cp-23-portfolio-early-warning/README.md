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


## Run it

```bash
export CCF_CP_23_POSTGRES_DSN=...   CCF_CP_23_POSTGRES_SCHEMA=ccf_v2
export CCF_CP_23_FLUREE_URL=...     CCF_CP_23_FLUREE_LEDGER=fibo-v2
export CCF_CP_23_TOKEN_COVERAGE=... CCF_CP_23_TOKEN_CREDIT=... \
       CCF_CP_23_TOKEN_PRODUCT=...  CCF_CP_23_TOKEN_UNGRANTED=...

make -s example-cp-23
make -s example-cp-23 PRINCIPAL="--principal PRIN-CO-002" INTENT="--intent credit-review"
make -s example-cp-23 SEVERITY_FLOOR="--severity-floor 0.45"
```


## The story

### The two rulings this rung carries


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

### The three roles


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


## Artifact-by-artifact

| file | what it carries |
|---|---|
| `ccf_config.yaml` | the class, the operator keys, and the population request surface |
| `ccf_environment.yaml` | where the source legs are read from — names only, never values |
| `artifacts/source-vocabulary.yaml` | the estate's own tables, columns and IRIs |
| `artifacts/perspectives.yaml` | the three role-conditioned views |
| `artifacts/severity-tiers.yaml` | the severity thresholds — **values, in a Control Plane artifact, never in code** |
| `artifacts/question.yaml` | the demonstration book and its instant |
| `artifacts/gates.yaml` | the nineteen declared gates and their observed reds |


## Whitepaper / CLAUDE.md sections exercised

| section | how |
|---|---|
| Whitepaper §7.4 — operator algebra | the declared keys over a POPULATION rather than a single anchor |
| Whitepaper §7.5 — Projection | three role-conditioned views of one class |
| Whitepaper §7.6 — Context Product Contract | `extra=forbid` over a book-grain payload |
| Whitepaper §7.7 — half-life and Context Debt | `compose_debt_factors` worst-factor across N members (`D-IMPL-104`) |
| Whitepaper §7.10 — Decision Replay | per-member serve-time invalidation reaching the record |
| CLAUDE.md §6.4 — No-Hardcoding | the severity tiers are a Control Plane artifact, never code constants |
| CLAUDE.md §7.1/§7.3 — MCP egress | the standard door with role overrides |
| CLAUDE.md §9 — estate discipline | reads `.76` only; seeds nothing; asserts relationships, never estate counts |


## What to change first

Replace `artifacts/source-vocabulary.yaml` with your own estate's tables and
IRIs and rewrite the readers in `acquisition.py`; `produce.py` names no domain
value and does not change.

**Change `artifacts/severity-tiers.yaml` before anything else.** The tier
boundaries are this demonstration's, not a bank's — they are declared there
precisely so that adapting them is an edit to a document rather than an edit
to a program (CLAUDE.md §6.4). The membership source is
`artifacts/question.yaml`'s book; a different portfolio is a different book,
not a different code path.

### Illustrative calibration

This example runs against a point-in-time demonstration estate rather than
continuously refreshed production data. Freshness half-lives and related
thresholds are calibrated to make the governed behavior observable in that
snapshot. They demonstrate how the SDK applies these controls and should not
be interpreted as recommended production coverage-policy thresholds.


## What would fail

### Known limitations


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

### Gates


19 declared gates, `PEW-G01`..`PEW-G19`, in `artifacts/gates.yaml`, each claimed
by an executing test under `tests/examples/test_cp_23_*.py`. **All nineteen
observed red** under their own sabotage; none is `unavailable`.

### Specification


`spec/CP-SPEC-023_Portfolio_Early_Warning_Concentration.md`, authored to
Context Product Specification Standard v0.3 before any code existed, with
Dave's Gate-2 rulings folded in at §F.4.
