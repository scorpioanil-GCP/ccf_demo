# What six runs of cp-01 demonstrate

**Six questions, one store, one instant.** This document records what
`counterparty-reference-snapshot` actually returned, run by run, and what each
answer proves that a `SELECT` against the same rows could not. It is written to
be lifted into a reference guide: every figure below came out of a run, none is
re-derived here, and the snapshot they were taken against is named in the next
section so a reader can reproduce them rather than trust them.

The short version: **a Context Product does not answer "what is in the table?"
It answers "what may *this caller* rely on, as of *this instant*, and what is
the shortfall?"** The six runs are six different ways that second question
diverges from the first.

---

## The snapshot these runs reproduce against

Every figure in this document comes from commit **`1f5e9da`**, with the question
pinned to **`asked_at 2026-08-16T12:00:00+00:00`** in `artifacts/question.yaml`,
against the live counterparty estate (PostgreSQL, schema `ccf_v2`).

The bar is **same question → same answer**, not correspondence with the live
world. A reader whose content addresses differ has **re-derived, not replayed**.

The commits between `39e72bd` — the pin named on this example's published
documentation page — and `1f5e9da` touched the `Makefile`, this example's
`README.md`, and a generated coupling report. **None of them is a file the
product reads**, which is why the addresses below are the same at both commits.

To reproduce, from the repository root:

```bash
make venv
export CCF_CP_01_POSTGRES_DSN="dbname=<your database>"   # host/user/password from libpq's PG* vars
make -s example-cp-01
```

`-s` suppresses `make`'s echo of the recipe. Without it the output is identical
plus six echoed lines, which is the only difference.

---

## The six runs at a glance

| # | Command | Payload | `D_c` | Content address | Exit |
|---|---|---|---|---|---|
| 1 | *(no parameters)* | the counterparty | `0.2929 → ok` | `ab2e1a62…` | 0 |
| 2 | `PRINCIPAL=PRIN-KYC-004` | `null`, **no reason** | `1.0000 → fail_closed` | `1f37263d…` | 0 |
| 3 | `ANCHOR=549300TRW1LZMDJZAQ78` | `null` + `excluded` | `0.2929 → ok` | `d22e96ad…` | 0 |
| 4 | `… INCLUDE_LAPSED=1` | the counterparty, `LAPSED` | `0.2929 → ok` | `a0d5d11c…` | 0 |
| 5 | `ANCHOR=<unknown>` | — refused `404` | — | — | 1 |
| 6 | `AS_OF=2026-01-01T00:00:00+00:00` | — refused `not_supported_at_tier` | — | — | 1 |

A seventh run, `ANCHOR=CLI-000101`, refuses at the `ttl-bounds` gate. It has its
own section at the end, because it is a **defect this example documents rather
than hides**.

**Four different content addresses for one anchor-and-instant.** That is the
single most important line in the table, and §"What the content address proves"
below says why.

---

## Run 1 — the baseline

```bash
make -s example-cp-01
```

```json
{
  "counterparty": {
    "anchor": "529900E95812SYWMCE44",
    "entity_id": "counterparty://24b66aaff16d3369…",
    "entity_status": "ACTIVE",
    "headquarters_address": { "city": "Parsippany", "country": "US", "region": "US-NJ" },
    "identity_authority": "lei-reference-data",
    "internal_client_id": "CLI-000008",
    "legal_address": { "city": "WILMINGTON", "country": "US", "region": "US-DE" },
    "legal_form": "XTIQ",
    "legal_jurisdiction": "US-DE",
    "legal_name": "AVIS BUDGET GROUP, INC.",
    "lei": "529900E95812SYWMCE44",
    "registration_status": "ISSUED",
    "type_chain": ["cmns-pts:Agent", "…", "fibo-be-le-cb:Corporation"]
  },
  "freshness_ceiling_days": 1,
  "perspective_role": "analyst",
  "signal_class": "vendor_identity"
}
```

```
What a plain SELECT would not have told you:
   asked as of        2026-08-16T12:00:00+00:00
   expires at         2026-08-17T00:00:00+00:00   (ttl_anchor from_entity_freshness)
   context debt D_c   0.2929  ->  ok
   identity authority lei-reference-data
   freshness ceiling  1 day(s)   (signal class vendor_identity)
   principal          PRIN-COV-001   sees 10 jurisdiction(s)
   operators invoked  ['policy.principal-subgraph']
   content address    ab2e1a62bf0e5b26c86b3dc122bc77ca4c7e8162ef86510f4a0901224723e9e4
   replay record      5cd4126b9a5eac5009dd1a01e13be27615e60ed75cce086ce2fa16bbf51dd888
```

**What a `SELECT` would not have told you** — the block is named after the
question it answers, and every line is a different answer to it:

- **`expires at`** — the answer has a shelf life, and it is *computed*, not
  configured. The `ttl_anchor` is `from_entity_freshness`: the expiry derives
  from when the underlying record was last refreshed, not from a fixed clock.
- **`context debt D_c 0.2929 → ok`** — a *quantified* shortfall, not a boolean.
  Something is imperfect and the fabric says how much, then says the amount is
  within tolerance.
- **`identity authority`** — which of two competing authorities resolved this
  anchor. A `SELECT` picks a table; the product records *which registry of truth
  it went through*, because a private borrower resolves differently (Run 2's
  section names the second authority).
- **`principal … sees 10 jurisdiction(s)`** — the answer is scoped to who asked.
  Run 2 changes only this.
- **`content address` / `replay record`** — the answer is addressable and the
  decision is reconstructible. Neither exists for a query result.

### Two addresses, kept deliberately apart

```
"legal_address":         WILMINGTON,  US-DE
"headquarters_address":  Parsippany,  US-NJ
```

Delaware-incorporated, New Jersey-headquartered — and the distinction is
**load-bearing rather than decorative**. The entitlement filter in Run 2 runs on
`legal_jurisdiction: US-DE`, not on the New Jersey headquarters.

**Collapse those two fields into one "address" and the filter entitles on the
wrong jurisdiction.** A data product that models one address per company has
already made an access-control error it cannot detect.

---

## Run 2 — the same question, asked by someone else

```bash
make -s example-cp-01 PRINCIPAL=PRIN-KYC-004
```

```json
{
  "counterparty": null,
  "perspective_role": "analyst"
}
```

```
   context debt D_c   1.0000  ->  fail_closed
   principal          PRIN-KYC-004   sees 9 jurisdiction(s)
   content address    1f37263d83a9dfe68532ace42d0071644356ed1be7ae3712a88343edb36d137c
```

`PRIN-KYC-004` holds nine EU jurisdictions. The counterparty's
`legal_jurisdiction` is `US-DE`, which is not among them, **so the entity was
removed from the graph this principal can see before assembly ran** — not
filtered out of a result afterwards. The product did not hide a record it held;
it never held one.

### The suppression is thorough, and that is the point

| Field | `PRIN-COV-001` | `PRIN-KYC-004` |
|---|---|---|
| `counterparty` | full record | `null` |
| `freshness_ceiling_days` | `1` | **absent** |
| `signal_class` | `vendor_identity` | **absent** |
| `perspective_role` | `analyst` | `analyst` |

**Three fields disappear, not one.** A filter that nulls the entity but leaves
`signal_class: vendor_identity` standing has told an unentitled caller what
*kind* of thing they were not allowed to see. Metadata is a side channel, and
suppression that stops at the payload's headline value is not suppression.

### `fail_closed` is the mechanism, not an error

`D_c` goes to **`1.0000`** — total shortfall — and the signal is `fail_closed`.
The fabric is not saying *"nothing matched."* It is saying **"I could not see
enough to answer, and I will not pretend otherwise."**

The failure mode this replaces is the one worth naming: a query that returns
zero rows to an unentitled caller is indistinguishable from a query that returns
zero rows because the company does not exist. **`D_c` is what makes those two
different answers.**

---

## Run 3 — refused, and told why

```bash
make -s example-cp-01 ANCHOR=549300TRW1LZMDJZAQ78
```

```json
{
  "counterparty": null,
  "excluded": {
    "include_lapsed": false,
    "reason": "registration-lapsed"
  },
  "perspective_role": "analyst"
}
```

```
   context debt D_c   0.2929  ->  ok
   content address    d22e96ad9c0285e92e0a5a1577fdcc79a83afd9ba8762ff264a4a04bf90bdd83
```

### The two silences, and why only one of them explains itself

Runs 2 and 3 both return `counterparty: null`. **Run 3 says why and Run 2
refuses to**, and the asymmetry is deliberate:

| | Run 2 — not entitled | Run 3 — lapsed |
|---|---|---|
| explanation | **none** | `reason: "registration-lapsed"` |
| `D_c` | `1.0000 → fail_closed` | `0.2929 → ok` |
| why | *explaining would leak* — "you may not see it" confirms it exists | the caller **is** entitled; the exclusion is a request default they may change |

### `D_c` measures what the fabric could not see, not what it declined to return

Run 3's debt is **`0.2929 → ok` — identical to the successful Run 1**. Nothing
was stale, nothing was unreachable: the entity was found, read, and then
excluded by an explicit rule.

That is the distinction that makes context debt a *number* rather than a flag.
A boolean cannot express *"I saw everything I needed and chose, by policy, to
return none of it."*

### The refusal names its own escape hatch

```json
"include_lapsed": false
```

The payload does not merely say *excluded*. It names **the parameter that would
change the answer and its current value**. A caller does not have to consult
documentation to discover what to try next — the refusal carries it.

---

## Run 4 — the parameter changes the payload, not the query

```bash
make -s example-cp-01 ANCHOR=549300TRW1LZMDJZAQ78 INCLUDE_LAPSED=1
```

```json
{
  "counterparty": {
    "anchor": "549300TRW1LZMDJZAQ78",
    "entity_status": "ACTIVE",
    "headquarters_address": { "city": "Parsippany-Troy Hills", "country": "US", "region": "US-NJ" },
    "internal_client_id": "CLI-000042",
    "legal_address": { "city": "Wilmington", "country": "US", "region": "US-DE" },
    "legal_jurisdiction": "US-DE",
    "legal_name": "B&G Foods, Inc.",
    "registration_status": "LAPSED",
    "…": "…"
  },
  "freshness_ceiling_days": 1,
  "perspective_role": "analyst",
  "signal_class": "vendor_identity"
}
```

```
   content address    a0d5d11c7881d37d2c4c52197c5d182cdb34155bd15daca9ed5f995136c6354a
```

**Same anchor, same instant, one flag — `d22e96ad…` becomes `a0d5d11c…`.**
Two addresses for one anchor is the proof that the parameter changed the
*payload* rather than the query behind it.

### Two status fields that disagree on purpose

```json
"entity_status":       "ACTIVE"
"registration_status": "LAPSED"
```

B&G Foods is a **live company whose LEI registration has lapsed**. One "status"
column would collapse two different facts into one wrong one, and a reader would
have no way to distinguish a defunct company from a current one with stale
paperwork.

**The lapsed record returns with its status as a first-class field.** You asked
for it, you get it, and you are told what you are holding. The alternative —
returning it quietly — is how a lapsed registration reaches a credit decision.

---

## Runs 5 and 6 — the two refusals that stop the process

```bash
make -s example-cp-01 ANCHOR=NOSUCHENTITY0000000
```

```
assembly refused: anchor 'NOSUCHENTITY0000000' resolved to no entity through
either identity authority (404); §D.2 step 1 fails closed rather than returning
an empty payload
```

**A 404, never an empty payload.** *"No such company"* and *"a company with
nothing in it"* are different answers, and a product that returns `{}` for both
has destroyed the difference.

```bash
make -s example-cp-01 AS_OF=2026-01-01T00:00:00+00:00
```

```
assembly refused: 400 not_supported_at_tier: as_of — declared by this class and
always refused (Standard §2.4). This verdict is raised rather than returned
because ProductRequestViolation.reason is a closed Literal with no member for
it; see CP-SPEC-001 §F.4
```

**`as_of` is in the contract so a caller can discover it, and always refused so
nobody relies on it in a dispute.** A parameter that silently does nothing is
worse than one that does not exist: the caller believes they asked a temporal
question and got a temporal answer.

Both exit **1** from `run.py`; `make` reports `Error 1` and itself exits 2.
**A refusal is not a crash, but it is also not a success.**

---

## The refusal taxonomy

Five distinct shapes, and they deliberately do not behave alike:

| Case | Shape | Carried as | Exit |
|---|---|---|---|
| Not entitled | silent `null`, `D_c → 1.0` | **data** | 0 |
| Lapsed | `null` + `excluded` naming the parameter | **data** | 0 |
| Unknown anchor | `404` | raised | 1 |
| `as_of` | `not_supported_at_tier` | raised | 1 |
| No-LEI anchor | `ttl-bounds` gate | raised | 1 |

The first two are **values**: a bad question and a missing entity are not broken
deployments, and a caller can branch on them without exception handling.

**The split is not entirely by design.** `ProductRequestViolation.reason` is a
closed `Literal` with no member for a tier refusal, so `as_of` must be raised
rather than returned. That is recorded in `CP-SPEC-001` §F.4, which carries
**eight** findings raised by building this product. They are not uniformly
SDK-surface defects — item 7, for one, is a *correction* to a mis-reading of the
Standard rather than a fault — and the section's heading is explicit that none
of them needed a decision before the product could be built.

---

## What the content address proves

| Run | Content address |
|---|---|
| 1 — baseline | `ab2e1a62…` |
| 2 — different principal | `1f37263d…` |
| 3 — lapsed, excluded | `d22e96ad…` |
| 4 — lapsed, included | `a0d5d11c…` |

The address is a hash over the product's **canonical bytes**, so it reproduces
only if *every* input reproduced — the resolved entity, the jurisdiction set for
the calling principal, the debt figure, the TTL window, the operator plan. One
drifted value anywhere and the hash differs.

Three consequences, and they are the reason this is worth computing at all:

1. **Reproducibility is checkable in one line.** A reader compares one hash
   instead of diffing a payload.
2. **Who asked is auditable, not merely logged.** Run 2 differs from Run 1 by
   the principal alone, and it is a *different product* with its own replay
   record — not the same product with a filtered view.
3. **A request parameter that changed nothing is detectable.** Run 3 against Run
   4 is the positive control: had `INCLUDE_LAPSED` been ignored, the two
   addresses would have matched.

---

## What these runs do not show

Stated plainly, because a demonstration that claims everything teaches nothing.

- **No graph traversal.** This is Tier 1 — one store, no multi-hop. The
  `operators invoked` list has exactly one member, `policy.principal-subgraph`.
  Products further up the ladder are where traversal cost becomes a design
  constraint.
- **No model in the path.** Assembly mode 1, pure algorithmic. Nothing here
  demonstrates the Algorithmic ⇄ Semantic alternation, because there is no
  semantic stage to alternate with.
- **The demonstration anchor is chosen, not sampled.** It resolves cleanly
  through the LEI authority. It is not evidence about the estate's overall
  data quality.
- **The printed summary is not the payload.** Below `counterparty: null` in Run
  2, `run.py`'s report block still prints `identity authority
  lei-reference-data` and `signal class vendor_identity` — read from the
  **resolve** stage, which runs before the policy filter. **The governed bytes
  suppress all three fields correctly; this example's own report block does
  not.** Recorded as an observation raised rather than a defect ratified, and
  not among §F.4's eight.

---

## The seventh run — the defect this example documents rather than hides

```bash
make -s example-cp-01 ANCHOR=CLI-000101
```

```
RuntimeError: the three validation gates refused this product:
gate='ttl-bounds'
detail='expires_at 2026-02-24T00:00:00+00:00 is outside
        (now, now + MAX_TTL] = (2026-08-16T12:00:00+00:00, 2026-08-17T12:00:00+00:00]
        (INV-CH7-48)'
max_ttl_seconds=86400
```

`CLI-000101` is a **private borrower with no LEI**, resolved through the second
identity authority — the internal client master — where freshness is anchored on
`kyc_last_refresh` rather than a registry's `retrieved_at`. A KYC refresh is
months old by design; a 24-hour maximum TTL is not. **The two do not compose,
and 30 of 30 no-LEI counterparties refuse.**

This is a **shipped defect, documented and tested**, not a bug that slipped
through. The gate `CPR-G09` asserts the refusal — which means **the test goes
RED when the defect is fixed**, proven by deliberate sabotage.

That inversion is the point: the test is the *evidence the deviation gets taken
back with*, not a test that ratifies a bug. It is recorded as §F.4 finding 8,
and the TTL anchor it names is the whole subject of the next product on the
ladder.

---

## Reading the whole thing in one sentence

A `SELECT` returns rows. **A Context Product returns rows, plus who may rely on
them, plus how long the answer is good for, plus how far short of complete it
is, plus an address that proves the answer reproduces — and it refuses, in five
distinguishable ways, rather than returning something that merely looks like an
answer.**

---

*Runs captured at commit `1f5e9da` against `asked_at
2026-08-16T12:00:00+00:00`. Specification: `spec/CP-SPEC-001_Counterparty_
Reference_Snapshot.md`. Gates: `tests/examples/test_cp_01_output.py`.*
