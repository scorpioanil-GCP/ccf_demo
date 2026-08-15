# HW-1 — companies over a revenue threshold you choose

The smallest useful Context Product: **which companies have revenue over a
number the caller supplies**, assembled from Postgres, with context debt driven
by the source rows' `last_updated`.

## 1. The one command

```sh
make example-s1-00 MIN_REVENUE=1000000000
```

Needs **Docker** (a `postgres:16` container is started and seeded for you), or
export `CCF_TEST_POSTGRES_DSN` to point at a Postgres you already run. No
credential is in this repository and none is needed.

```
Q: which companies have revenue over 1000000000?
   asked as of 2026-08-01T00:00:00+00:00

   Contoso Manufacturing       1850000000   updated 2026-07-02
   Litware Systems             7750000000   updated 2025-09-30
   Lucerne Publishing          1500000000   updated 2024-08-09
   Northwind Traders           4200000000   updated 2026-07-20
   Tailspin Logistics         12400000000   updated 2026-03-01
   Wingtip Materials           2900000000   updated 2025-02-04

   6 of 10 companies

What a SELECT would not have told you:
   context debt D_c   0.3886  ->  forced_llm   (F=0.6114 from last_updated on 10 rows against the declared half-life)
   policy version     dd2c515f43012c7908ff9bd82289553be2b2f8d3900291c265e1cc5abeda0f5f
   content address    5cfee793e5fb686a82becac08cddf2ca187c3ef9ae26bd9a8fd41030656a6d36
   replay record      437d9b10dcc400426c17357567e4af5e7dd1336820ca3c4f469437f833fc8726
```

Run it again with a different number. The answer changes, **and so does the
content address** — because the caller's number is part of the question.

## 2. What you would have written instead

```sql
SELECT name, revenue FROM companies WHERE revenue > :threshold;
```

That returns the same six rows. Here is what it does not return, and what each
one cost:

| What CCF added | What it tells you | Where it comes from |
| --- | --- | --- |
| `D_c = 0.3886 → forced_llm` | This estate is stale enough that you should **not** act on it algorithmically alone. Two of the six rows are over a year old. | `half-life-table.yaml` (λ_c) + `debt-profile.yaml` (the bands), measured off `last_updated` |
| `policy version dd2c515f…` | *Which* rules produced this answer — pinned, not "whatever is current". | `policy-bundle.yaml`, pinned at boot |
| `content address 5cfee793…` | This exact answer to this exact question, addressable and comparable. Change the threshold and it changes. | the product's own content hash |
| `replay record 437d9b10…` | The decision is reproducible: the graph snapshot, the policy version, the operator set and the question are all recorded **before** the answer is delivered. | `produce.py`'s `record` and `serve` regions |

The `forced_llm` line is the one to sit with. A row count cannot tell you that
your answer is built on two-year-old filings; this does, as a number, delivered
with the answer rather than in a log.

## 3. What you author

**Two documents, fifty-eight non-comment lines.** `D-IMPL-136`'s AMENDMENT
(Dave, 2026-08-15) converts this deployment's Control Plane configuration to
one file — `ccf_config.yaml` — plus `backends.yaml`, which stays separate by
design. Before this conversion HW-1 authored the same commitments across ten
documents, ninety-nine lines; see [`MEASUREMENT.md`](MEASUREMENT.md) for the
before/after in full, the refusal that demanded each section, and the
commands that reproduce every figure.

| Document | What it says |
| --- | --- |
| `ccf_config.yaml` | Everything CCF requires: what this deployment puts in force, one section per concern (`product_class`, `operators`, `request_contract`, `resolution`, `half_life`, `debt_profile`, `policy`, `default_perspective`). The section name **is** the class — no file, key and class id restated three times over. |
| `backends.yaml` | How the backend's connection settings are composed — a variable's **name**, never a value. |

Inside `ccf_config.yaml`, each section carries what its equivalent document
used to:

| Section | What it says |
| --- | --- |
| `resolution:` | How a source row becomes an entity. |
| `policy:` | The regime in force. Its *version* rides the answer. |
| `half_life:` | λ_c — how fast this data goes stale. |
| `debt_profile:` | Where the D_c bands sit. |
| `default_perspective:` | Whose view the product is served under. |
| `product_class:` | What the product is, and the operator set it claims. |
| `request_contract:` | Which questions it answers. `revenue_threshold` lives here. |
| `operators:` | The one operator category, two lines. |

`scenario/` — **this is not CCF.** It fabricates the demonstration: the table
DDL, ten seed rows, the caller's question vocabulary, and a provisioner that
starts a container. **You delete all of it** and point the deployment at the
database you already have.

`produce.py` is CCF's calls and names no vocabulary of yours. `deployment.py` is
yours and names all of it. `consume.py` is the client.

## 4. What this example does not do

* **One operator category, not four.** `D-IMPL-132`: *"context assembly is
  specific to whatever I want it to be. Operators help me assemble it but I
  should not be forced into a single format."* Gate 1 refuses an *empty*
  operator set, so one is the floor — measured, not assumed.
* **No traversal**, because the question is about a *set*, not a *path*. There
  is no walk to seed.
* **No MCP.** In-process only; that is HW-2.
* **No `projection-requirements.yaml`.** Design E2's divergence guard compares
  two independently authored operator sets, and this deployment authors one. An
  unused guard is not a missing one.
* **No `debt_evidence`, `source_refresh_recency` or `obligation_in_force`.**
  Three real governance surfaces `s1-01` exercises; naming them here is what
  stops you concluding they do not exist.

## 5. The required parameter, and what it means for HW-2

`revenue_threshold` is a **required** declared request parameter, because a
threshold nobody supplied is not a question this class answers. Omit it and the
request is refused with `missing-required-parameter` **before the graph is
touched** — a reason, not an approximate answer.

That validation lives in `produce.py` rather than at a door, and that is not an
accident of layout: `refuse_request`'s own docstring says it is *"called by the
deployment's own resolver, not by any door"* (`D-IMPL-121`), because a door never
holds the registered product class the comparison needs. This in-process spine
**is** that resolver.

`D-IMPL-133` rules that both parameterised doors carry client-supplied
`parameters`, implemented by plan `16-26`. So **HW-2 reuses this product
unchanged**, changes only the client, and demonstrates both halves of
`D-IMPL-127` — that remoteness costs nothing, *and* that the client owns the
question.

## 6. What to change first

1. **`scenario/`** — delete it. Point `deployment.py`'s `TABLE` / `COLUMN_*`
   block at your own table, and `backends.yaml` at your own database.
2. **`half-life-table.yaml`** — one year is right for annual revenue filings and
   almost certainly wrong for your data. This single number moves every D_c the
   example prints.
3. **`debt-profile.yaml`** — where *your* decision class stops trusting the
   answer.
4. **`request-contract.yaml`** — the questions your class answers.

## 7. Sections exercised

Whitepaper §6.3 (Addressability, the Context Product Contract), §7.4
(operators), §7.6 (the three validation gates), §7.7 (half-life and debt), §7.10
(Decision Replay). CLAUDE.md §6.4 (No-Hardcoding), §9 (examples suite), §10
(L1–L6 and the single-writer invariant).
