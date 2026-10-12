<!--
Copyright (c) 2026 David Castillo. All rights reserved.
Use, copying, modification, and distribution of the covered material
are governed by the CCF SDK Interim Software and Patent License
in the repository-root LICENSE.md and any controlling signed agreement.
Rights under that interim license begin only upon its execution
and are limited to its stated scope and term.
-->
# HW-1 — companies over a revenue threshold you choose

The smallest useful Context Product: **which companies have revenue over a
number the caller supplies**, assembled from Postgres, with context debt driven
by the source rows' `last_updated`.

## 1. The one command

**Prerequisites.** `make venv` once (it creates `.venv` from the hash-verified
lock; this repository has no `python` on its PATH, so commands name
`.venv/bin/python`), and **Docker**: a throwaway `postgres:16` container is
started, seeded with ten synthetic rows and removed for you (testcontainers;
its reaper removes the container when the run ends). Alternatively export
`CCF_TEST_POSTGRES_DSN` pointing at a disposable Postgres **you own** — the run
writes DDL and rows there, and a DSN naming a curated estate host is refused
before anything is written. No credential is in this repository and none is
needed. Run from the repository root.

```sh
make example-s1-00 MIN_REVENUE=1000000000
```

What it printed on 2026-10-11 (commit on branch `r2-producer`; values marked
`<…>` change from run to run, explained below):

```
estate fence: clear. Checked (none set — defaults apply). Curated hosts in force: 192.168.4.76 (the default; CCF_CURATED_ESTATE_HOSTS is unset).

Q: which companies have revenue over 1000000000?
   asked as of <now, e.g. 2026-10-11T23:40:20+00:00>

   Contoso Manufacturing       1850000000   updated 2026-07-02
   Litware Systems             7750000000   updated 2025-09-30
   Lucerne Publishing          1500000000   updated 2024-08-09
   Northwind Traders           4200000000   updated 2026-07-20
   Tailspin Logistics         12400000000   updated 2026-03-01
   Wingtip Materials           2900000000   updated 2025-02-04

   6 of 10 companies

What a SELECT would not have told you:
   context debt D_c   <0.4668>  ->  forced_llm   (F=<0.5332> from last_updated on 10 rows against the declared half-life)
   policy version     dd2c515f43012c7908ff9bd82289553be2b2f8d3900291c265e1cc5abeda0f5f
   content address    <depends on the as-of instant and the threshold>
   replay record      <issued per answer>
```

**What changes from run to run, and why.** The question is asked **as of
now**: `consume.py` reads the clock once, and the fabric serves on its own
clock moments later. So:

* `asked as of` is the instant you ran it;
* `D_c` and `F` are **measured at that instant** against the rows' fixed
  `last_updated` dates and the one-year half-life. They rise as the seed rows
  age: on 2026-10-11 they read 0.4668 / 0.5332 (`forced_llm`); from about
  2027-03-13 `D_c` passes the declared 0.60 band and the same command prints
  `fail_closed` (the answer is still delivered — the signal says not to act on
  it algorithmically);
* the **content address** is the hash of the answer, which includes the
  instant it was asked as of, so a new instant is a new address;
* the **replay record** address is issued afresh for every answer.

The six rows, the counts and the policy version do not change.

**To see one address twice**, pin the instant — it must be within the
product's ten-minute lifetime of when you run it:

```sh
ASKED=$(date -u +%Y-%m-%dT%H:%M:%S+00:00)
PYTHONPATH=src:runtime .venv/bin/python examples/s1-00-companies-over-revenue/consume.py --min-revenue 1000000000 --as-of "$ASKED"
PYTHONPATH=src:runtime .venv/bin/python examples/s1-00-companies-over-revenue/consume.py --min-revenue 1000000000 --as-of "$ASKED"
```

Both print the same content address and different replay records. Run it
with a different `--min-revenue` and the address changes too — because the
caller's number is part of the question. `make example-s1-00` with no
`MIN_REVENUE` asks the demonstration threshold in `scenario/question.yaml`
(1000000000). `--explain` adds the governance transcript.

**The governed refusals you can provoke** (each exits 1, prints the reason,
and names the record that authorized saying no):

| `--as-of` | Printed | Why |
| --- | --- | --- |
| more than 10 minutes ago | `refused: ttl-bounds` | the answer's ten-minute lifetime has run out before it is served |
| more than an hour ago, e.g. `2026-08-01T00:00:00+00:00` | `refused: asked-at-outside-temporal-bound` | `temporal_boundary:` in `ccf_config.yaml` answers for at most an hour into the past |
| any instant in the future | `refused: asked-at-outside-temporal-bound` | zero clock skew is permitted |

The `--as-of` value needs a UTC offset (`+00:00`); without one the run stops
with `CanonicalizationError: naive datetime is not canonically encodable`
(`D-IMPL-38`: no implicit UTC).

> **Illustrative calibration:** This example runs against a point-in-time
> demonstration estate rather than continuously refreshed production data.
> Freshness half-lives and related thresholds are calibrated to make the
> governed behavior observable in that snapshot. They demonstrate how the SDK
> applies these controls and should not be interpreted as recommended
> production coverage-policy thresholds.

**The tests** (`tests/examples/test_s1_00_output.py`, 12 tests, needs Docker or
`CCF_TEST_POSTGRES_DSN`):

```sh
CCF_REQUIRE_POSTGRES=1 PYTHONPATH=src:runtime:. .venv/bin/python -m pytest -q tests/examples/test_s1_00_output.py   # measured 2026-10-11: 12 passed
make leg-postgres                                                                                                 # every Postgres-marked test
```

They ask the dated scenario question (2026-08-01) on a **controlled serve
clock** held at the question's instant, so their answers are the same every
day; two of them use the real clock — a question asked now is served, and the
2026-08-01 question served today is refused `asked-at-outside-temporal-bound`.

### History — what this section used to show

**Amended 2026-10-11 (`examples/AMENDMENTS-2026-10-11.md`).** Until then the
default question was pinned at 2026-08-01 and this section showed the output
below, recorded before `D-IMPL-358` (temporal bound and serve-time expiry).
Asked today, that pinned question is a governed refusal
(`refused: asked-at-outside-temporal-bound`), and this example cannot declare
the SDK's demonstration serve instant to keep it answering, because that
mechanism is admitted only on the SDK's development substrates (`D-IMPL-378`
C1, decision 6 (b)) and this example's graph is Postgres. So the default now
asks as of now. The historical output, kept as evidence:

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

## 2. What you would have written instead

```sql
SELECT name, revenue FROM companies WHERE revenue > :threshold;
```

That returns the same six rows. Here is what it does not return, and what each
one cost:

| What CCF added | What it tells you | Where it comes from |
| --- | --- | --- |
| `D_c` (0.3886 as of 2026-08-01, 0.4668 on 2026-10-11) `→ forced_llm` | This estate is stale enough that you should **not** act on it algorithmically alone. Two of the six rows are over a year old. | `half-life-table.yaml` (λ_c) + `debt-profile.yaml` (the bands), measured off `last_updated` |
| `policy version dd2c515f…` | *Which* rules produced this answer — pinned, not "whatever is current". | `policy-bundle.yaml`, pinned at boot |
| `content address` | This exact answer to this exact question, addressable and comparable. Change the threshold and it changes. | the product's own content hash |
| `replay record` | The decision is reproducible: the graph snapshot, the policy version, the operator set and the question are all recorded **before** the answer is delivered. | `produce.py`'s `record` and `serve` regions |

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
* **No MCP.** In-process only; the MCP door for this product class is in
  `examples/hw1-companies-over-revenue`, over its own deployment (§5).
* **No `projection-requirements.yaml`.** Design E2's divergence guard compares
  two independently authored operator sets, and this deployment authors one. An
  unused guard is not a missing one.
* **No `debt_evidence`, `source_refresh_recency` or `obligation_in_force`.**
  Three real governance surfaces `s1-01` exercises; naming them here is what
  stops you concluding they do not exist.

## 5. The required parameter, and how this relates to the client tutorial

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
`parameters`, implemented by plan `16-26`.

**How this example relates to the client tutorial's
`examples/hw1-companies-over-revenue`, measured 2026-10-11** (amended; this
paragraph used to say *"HW-2 reuses this product unchanged, changes only the
client"*, which is true of the product class and not of the deployment):

* **Same product class and same question.** Both deployments declare
  `hw1.companies-over-revenue` 1.0.0 under tenant `hw1-demo`, and their
  `ccf_config.yaml` sections `product_class`, `request_contract`, `operators`,
  `resolution`, `half_life`, `debt_profile`, `policy`, `default_perspective`
  and `temporal_boundary` are identical (that file says it was recovered from
  this one). Both answer *"which companies have revenue over the
  `revenue_threshold` the caller supplies?"*
* **A different deployment with different data.** hw1 has its own
  `deployment/`: a SQLite graph seeded from `runner/signal-batch.yaml` (eight
  companies — Ardent Fenwick Holdings, Marrowgate Shipping, …), a
  `demonstration_serve_instant:` it may declare on that development substrate,
  a `binding.yaml` and an MCP server. This example is ten different companies
  (Contoso, Litware, …) in a Postgres it provisions. So the same threshold
  gives different answers: here 6 of 10, there 5 of 8.
* **The hw1 client cannot retrieve this example's product.** `consume.py`
  here is the in-process client and is the only one that reaches it. Pointed
  at this directory, the hw1 client refuses before asking:
  `CCF_BINDING="inprocess:examples/s1-00-companies-over-revenue" … hw1-companies-over-revenue/consume.py`
  → `BindingError: … carries no binding.yaml`. This example has no door.

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
