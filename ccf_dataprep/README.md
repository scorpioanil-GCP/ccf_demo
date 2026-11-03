# ccf_dataprep

Builds and loads the synthetic and public-derived datasets backing a catalog of
Commercial Banking / CIB **Context Products**, across five partitioned datastores.

## About this data — read before using any figure

This dataset is **educational**. It exists to show how Context Products are
assembled across multiple stores — not to be consumed as fact.

**Every element carries one of three provenance classes, labelled at row level:**

- **`public`** — real, fetched from a named source with a retrieval date. Real
  GLEIF LEIs, real SEC EDGAR filing text, real US Treasury par yields, real
  FRED / ICE BofA index series, and real people named in Form 4 and DEF 14A
  filings.
- **`synthetic — internal`** — invented because it is bank-internal by nature and
  no public source exists: exposures, balances, limits, credit opinions,
  coverage assignments, CRM interactions.
- **`synthetic — engineered`** — invented *deliberately* to create a condition
  public data will not supply: a planted cross-shareholding cycle, an amendment
  booked after its effective date with a drawdown in the gap, a false-positive
  name match, engineered spread-divergence windows. **Where a demonstration is
  interesting, assume the condition was planted.**

**Real identities carry invented behaviour.** 704 real individuals appear under
the names and SEC CIKs on their actual filings (of 743 `person` rows — the
other 39 are entities, not people). Every meeting, call, coverage
assignment, and relationship score attributed to them is invented and
corresponds to no real event. The same pattern holds for companies: real LEIs,
invented exposures.

**Use this to learn the assembly patterns, not the numbers.** Apply them to
*your* data. No figure here is a fact about any real company or person.
Third-party index data (ICE BofA, via FRED) is included under FRED's terms and
is not for redistribution.

Row-level `provenance` is authoritative. [`docs/ccf_dataprep_v2.md`](docs/ccf_dataprep_v2.md)
maps every element to its class and its owning store;
[`docs/known-issues.md`](docs/known-issues.md) records every known limitation
and every engineered condition.

**Start here:** [`docs/HANDOFF.md`](docs/HANDOFF.md) — state, what exists, what's open,
and the four commands that verify nothing has regressed.

| Doc | What it is |
|---|---|
| `CLAUDE.md` | Project brief, store assignment, non-negotiable rules |
| `docs/HANDOFF.md` | **Resume point** — verify state in 60 seconds |
| `docs/data-acquisition-plan.md` | Waves 0–7, gates, conditions register |
| `docs/known-issues.md` | **Known bugs, limitations, and what is engineered** — read before trusting any field |
| `docs/ccf_dataprep_v2.md` | Current reference + **FIBO IRI binding contract** |
| `docs/ccf_dataprep.md` | Superseded v1 |
| `docs/fibo_files/` | v1 working artifacts (reference) |

## Layout

```
ccf/         shared library — config, guards, fetch harness
ontology/    extended FIBO subset (Turtle)
sources/     fetched public data + provenance manifests
generators/  synthetic and engineered data generation
loaders/     per-store loaders
validators/  partition, join, and condition checks
```

## Setup

```bash
uv sync
cp .env.example .env      # fill PGPASSWORD; SEC_USER_AGENT must carry a real email
uv run loaders/init_sqlite.py
uv run loaders/init_fluree.py
uv run validators/partition.py
```

## Namespaces

v2 loads into fresh namespaces **beside** v1, never over it:

| Store | v2 target | v1 (read-only) |
|---|---|---|
| Fluree | `fibo-v2` | `fibo:main` |
| Postgres | schema `ccf_v2` | `public` |
| MongoDB | `fibo_v2` | `fibo` |
| SQLite | `./data/departmental.sqlite` | — |

**Neo4j is not part of the v2 estate** (dropped 2026-08-16). Depth-bounded
traversal uses unioned fixed-length SPARQL patterns; cycle detection runs
application-side. The v1 Neo4j graph is left untouched.

> **Fluree `fibo-v2` is a separate ledger, not a branch.** Aliases are
> `name:branch`, so `fibo:v2` would have been a *branch of the v1 ledger*.
> Fluree is append-only — a write to the wrong ledger cannot be undone.

> **The MongoDB host is shared.** It also carries `rtdetect`, a live system with
> ~5.5M documents. `ccf/config.py` refuses writes to any database outside
> `fibo_v2`, and nothing in this repo enumerates databases. Keep it that way.
