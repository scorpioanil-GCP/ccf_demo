# Collateral & Set-off Coverage — rung 6

`credit-risk.collateral-coverage.v1` · Tier 2 · PostgreSQL + Fluree · reads the
curated `.76` estate, writes nothing.

**What actually secures this exposure, and what can be applied against it.**

## What this demonstrates

**Coverage is a graph question that gets stored as a column.** A collateral
field on a facility record answers *"is this secured?"* — and not *"by what,
shared with whom, and at what priority?"* One asset frequently secures several
facilities, sometimes at different priorities. A second-lien position recorded
as "secured" beside a first-lien position recorded identically produces two
facilities that look equally protected and are not.

That is not a story about somebody else's data model. It is reproducible in this
estate by reading one store instead of two: **`ccf_v2.collateral_pledge` carries
`facility_id, asset_id, provenance, basis` and no priority column at all.**
Priority exists only in the graph, reified as `ex:CollateralPledge` nodes — 95 of
them, 93 `PrimaryLienPosition` and 2 `SubordinateLienPosition` — because priority
belongs to the **(facility, asset) pair** and hanging it on either endpoint
drops half of each fact.

Six things the product shows, each of which changes the conclusion rather than
the decimals:

| ask | what moves |
|---|---|
| default | the governed answer |
| `--no-haircuts` | haircuts were suppressing real coverage |
| `--jurisdiction-basis=contractual` | set-off the jurisdiction will not honor starts counting |
| `--no-setoff` | **covered becomes under-covered** |
| `--shared-collateral=pro-rata` | the shared asset stops being wholly the anchor's |
| MasTec anchor | a lien the contract layer calls secured, which the register says was **released** |

And a seventh the payload carries throughout: **per-asset valuation dates**. §E's
spread is one day against one year inside a single product, and §6.4 Temporal
Validation refuses to let a product flatten that into one freshness figure.

## Run it

```bash
make venv

# Credentials and host come from the estate's environment; THE NAMESPACES DO
# NOT — .env names the v1 estate (CLAUDE.md §9).
set -a; source /home/parkave/ccf_dataprep/.env; set +a
export CCF_CP_06_FLUREE_URL="http://192.168.4.76:8090"
export CCF_CP_06_FLUREE_LEDGER="fibo-v2"            # v2, NOT fibo:main
export CCF_CP_06_POSTGRES_DSN="postgresql://$PGUSER:$PGPASSWORD@$PGHOST:$PGPORT/$PGDATABASE"
export CCF_CP_06_POSTGRES_SCHEMA="ccf_v2"           # v2, NOT public

make example-cp-06
make example-cp-06 HAIRCUTS=--no-haircuts
make example-cp-06 SETOFF=--no-setoff
make example-cp-06 BASIS=--jurisdiction-basis=contractual
make example-cp-06 SHARED=--shared-collateral=pro-rata
make example-cp-06 FACILITY=--facility=FAC-102496 SCOPE=--scope=549300TMDIT8WREDOF45
```

**Everything is read-only.** Two SPARQL `SELECT` legs and parameterised SQL
`SELECT`s; no write verb exists anywhere in the tree. The fabric's own graph and
the decision replay record go to a temporary directory and are discarded when
the run exits.

A flag you do not pass is **omitted**, so the class default resolves — a
different act from passing the default's value, and the run prints which
happened.

## The story

Three things will bite you if you change them.

### 0. Priority is asserted, not derived — and that is a ruling

**Lien priority is an AUTHORITATIVE INPUT on the reified pledge. This product does NOT determine legal UCC priority from filing records. Coverage under `allocation=priority` is coverage under those assertions** (`D-IMPL-321`, Dave, 2026-09-10). The register holds Florida only — 8 of 50 anchors — and does not carry the facility link, so a Π computing priority from filing dates would be a legal claim the estate cannot support. Deriving it is a **different product** for when the register can name the facility, not a completion criterion for this one.

The payload says so itself, in its `basis` block, so a consumer reading the
product rather than this file still cannot miss it.

### 1. Priority belongs to the pair, not to the asset

The fabric reifies the pledge exactly as the source does. An earlier draft of
this example hung `lien_position` on the asset, which carried only the *anchor's*
position — so no other claimant could ever outrank it and a subordinate holder
looked senior. That is §A's counterfactual reproduced *inside* the product built
to refute it. If you flatten the pledge back onto either endpoint, the allocation
silently stops working and every number still looks plausible.

### 2. Thin edges first, attributed nodes last

Two kinds of envelope reach L2: **edge** envelopes carrying two endpoint
references and a predicate and no attributes, and **node** envelopes carrying one
node's attributes.

**Edges must be ingested first.** The last claim at a URI wins and does not
merge, so an edge arriving *after* a node erases that node's attributes and the
payload then serves an asset with no valuation and no haircut — **and nothing
raises**. `deployment.ingest` asserts the outcome so a reorder fails where it
happened. Do not tidy it back into chronological order.

### 3. The estate has three traps, and they are not this SDK's

- **Dates are untyped ISO-8601 strings.** This Fluree build corrupts
  `^^xsd:date` on write — 65 of 65 filing dates stored wrong, 53 distinct
  deltas. ISO-8601 sorts lexicographically, so compare them as strings; casting
  is what breaks.
- **`COUNT(*)` under-reports** on a multi-pattern `WHERE` — 17 where the query
  returns 65 rows. Everything here counts client-side.
- **An amendment's action is not scalar.** Two amendments in the register carry
  two actions each (`Add a secured` + `Remove a secured`; `Termination` +
  `Amendment`), which is why 15 amendments carry a Termination while only 13
  filings do.

## Artifact-by-artifact

| file | what it is |
|---|---|
| `ccf_config.yaml` | the single Control Plane document — including `declared_product_gate` |
| `backends.yaml` | how the two stores are reached. Variable **names** only |
| `artifacts/source-vocabulary.yaml` | the sources' own IRIs, tables and columns |
| `artifacts/projection.yaml` | Π's declared values: the seniority ranking and the roster cap |
| `acquisition.py` | the two source legs. **Imports no `ccf` at all** |
| `deployment.py` | this deployment's vocabulary, the envelopes, the debt |
| `projection.py` | Π — allocation, set-off filtering, the over-allocation finding |
| `produce.py` | **the fabric's half.** Three regions: `boot`, `acquire`, `govern` |
| `run.py` | presentation. The only module that prints |
| `server/door.yaml` | the door's governance values, and its `serve_entrypoint` |
| `server/serve.py` | the MCP door — translation, and no governance of its own |
| `FINDINGS.md` | what authoring this against the current SDK exposed |

`produce.py` contains **no domain vocabulary at all** — no predicate, no table,
no column, no asset class, no haircut, no number.

**Deliberately absent:** no `gate` region, no `record` region, no `serve`
region, and no call to `run_gates`, `build_replay_record` or `serve` anywhere.
The door, the view, both operators, Π, the three L6 gates, this product's
declared fourth gate, the five-dimension replay record, the query pins and the
delivery are **one object the SDK owns**, reached by a single
`build_governed_resolver` call.

**The MCP door duplicates none of it.** `server/door.yaml` names its
implementation as `serve:serve` — a module and callable, never a filesystem
path. A consumer asks for the Context Product; it does not learn how the
producer happens to start, because a client carrying
`python examples/…/serve.py` has bound itself to this deployment's directory
layout, interpreter and language, none of which is part of the product contract.

## Whitepaper / CLAUDE.md sections exercised

Whitepaper §7.3 (typed graph state), §7.4 (operator algebra, and §8.5's typed
edge vocabulary — `securedBy`, `setOffAgainst`, `nettedUnder` — as the wholesale
graph's distinguishing feature), §7.5 (Π), §7.6 (the product contract and its
three validation gates, here joined by the product's own fourth), §7.7
(half-life and debt), §7.10 (Decision Replay). CLAUDE.md §6.4 (No-Hardcoding),
§9 (**the curated estate is evidence, not a fixture**), §10 (single-writer).

Rulings it is authored against: `D-IMPL-256` (a door that cannot record a
refusal is not a governed door), `D-IMPL-259`/`D-IMPL-264` (a parameter's valid
domain, and why `intent` is not an argument), `D-IMPL-282` (a product gate's
identity is the Control Plane's half), `D-IMPL-295` (a binding supplies a value
and never converts one), `D-IMPL-309`/`D-IMPL-310` (store pin and replay
dimension 2), `D-IMPL-315` (adjudicate, don't edit), `D-IMPL-316` (a position is
not an identity).

## What to change first

1. **The facility.** `run.py`'s `DEMONSTRATION_FACILITY`, or `--facility`.
   Everything follows from which exposure you name.
2. **`borrower_scope`.** The identifiers the policy operator admits on —
   ordinarily the anchor's own borrower, as a one-element list. Stated by the
   caller rather than derived, because a binding supplies a value and never
   converts one.
3. **The basis.** `--jurisdiction-basis` and `--shared-collateral` are the two
   that change *what the answer means* rather than its size.

To point this at **your own estate**, edit `artifacts/source-vocabulary.yaml`
(the IRIs, tables and columns) and `backends.yaml` (the environment variable
names and the declared walk ceiling). No Python changes.

## What would fail

Each is asserted in `tests/examples/test_cp_06_output.py`, so breaking one is
loud rather than silent.

- **Apply the haircut as a premium** and coverage rises where it must fall. The
  test asserts the *direction*, not a figure, so it survives a policy change to
  the schedule and still catches an inverted discount.
- **Collapse `pro-rata` onto `priority`** and the two bases agree — which means
  the graph's subordinate lien stopped mattering, and the product no longer
  demonstrates its own subject.
- **Serve fabric URIs instead of the source's ids** and the payload can no
  longer be joined to anything; sharing detection breaks with it, because
  matching a readable anchor against a content hash matches nothing.
- **Reverse the ingestion order** and every node is served bare, with nothing
  raised.
- **Flatten per-asset valuation dates** into one product-level freshness and a
  two-day mark becomes indistinguishable from an eighteen-month appraisal.
- **Drop `declared_product_gate`** and the SDK refuses to build the resolver at
  all: replay would have no identity to stamp on a refusal the gate produced.
- **Point a test at a pinned number** such as `1.089` and it goes red on the
  next legitimate valuation change, having turned the curated estate back into a
  fixture.
- **Seed the curated estate** and `estate_guard` refuses; a seeded Fluree ledger
  is permanent.
