# Corporate Family Tree — the canonical rung-4 example

Walks a corporate family from an anchor LEI across two systems of record and
returns the tree, the ontology class of every node in it, and the ownership
cycles it contains **as findings rather than as errors** — with the measured
Context Debt in force when the answer was assembled, the content address the
answer hashes to, and the replay record that authorized it.

## What this demonstrates

There are **two** rung-4 examples in this repository and they are not versions
of each other.

| | `examples/cp-04-corporate-family-tree` | **this tree** |
|---|---|---|
| what it is | a **frozen historical specimen** | the **current pattern to copy** |
| status | frozen under `D-IMPL-261`; **zero files changed** by this work | authored against the SDK as it ships today |
| what it teaches | what the SDK looked like when it was built, preserved as evidence | what an adopter should write now |

cp-04 hand-composed the governed path — the door, the gates, the replay record,
the serve. It is kept exactly as it was because a specimen that is quietly
modernized stops being evidence. **This tree reuses cp-04's business problem and
none of its implementation** (`D-IMPL-313`): it was authored forward from the
current canonical shape rather than derived by editing cp-04, because a
successor derived by editing would inherit that shape and teach it.

**Copy from here. Read cp-04 only to see how far the SDK has moved.**

### It is its own determination, not a replay of cp-04's

The two trees answer the same question about the same fixture and **do not
agree**, which is correct rather than a defect. This tree chose its own
demonstration anchor from the data, so it has its own roster, its own Context
Debt and its own content addresses. Nothing here reuses cp-04's addresses, its
published identifiers, its snippet includes or its `D_c` of 0.0909.

---

### Two stores, neither complete on its own

Family edges, the FIBO class chain, labels and LEIs come from a graph store.
GLEIF Level 1 attributes come from a relational store, keyed by LEI. **No schema
author has joined them**, and most of this family's nodes have no row in the
relational leg at all. That is not a defect to repair — it is the measured fact
the product's Context Debt is computed from.

At the declared default depth this family is 49 entities and 119 typed edges, of
which **29 resolve** in the attribute leg. `D_c = 0.408163`, signal `ok`.

### Context Debt that moves with the answer

| you ask | you are served | `D_c` |
|---|---|---|
| `max_depth` absent | 49 entities, 119 edges, 29 resolved | 0.408163 |
| `max_depth=1` | 36 entities, 35 edges, 16 resolved | 0.555556 |
| `max_depth=99` | *refused* — `bound-exceeded`, authority `technical` | — |

A debt that stayed the same whatever was served would be decorative. It moves
because the walk is genuinely bounded at the depth governance resolved, so what
was assembled and what was served are the same set.

### Cycles as findings

Mutual and circular ownership is ordinary in real corporate structures — this
family carries 22 mutual pairs. A product that raised on one could not describe
the estates it exists to describe. Each circuit is returned with an ordered
roster and its **closing edge**, so a reader sees the loop rather than being
told one exists.


## Run it

```bash
make venv

# Credentials and host come from the estate's own environment;
# THE NAMESPACES DO NOT — .env names the v1 estate (CLAUDE.md §9).
set -a; source /home/parkave/ccf_dataprep/.env; set +a
export CCF_CP_04C_FLUREE_URL="http://192.168.4.76:8090"
export CCF_CP_04C_FLUREE_LEDGER="fibo-v2"          # v2, NOT fibo:main
export CCF_CP_04C_POSTGRES_DSN="postgresql://$PGUSER:$PGPASSWORD@$PGHOST:$PGPORT/$PGDATABASE"
export CCF_CP_04C_POSTGRES_SCHEMA="ccf_v2"         # v2, NOT public

make example-cp-04-canonical
make example-cp-04-canonical MAX_DEPTH=1
make example-cp-04-canonical LEI=<some-other-lei> MAX_DEPTH=2
```

Everything is **read-only**: the two source stores receive SPARQL `SELECT`s and
one parameterised SQL `SELECT` and nothing else. The fabric's own graph and the
decision replay record are written to a temporary directory and discarded when
the run exits.

`MAX_DEPTH` omitted asks the question **without** the parameter, so the class
default resolves — a different act from passing the default's value, and the run
prints which happened.

## The story

Two things will bite you if you change them.

### 1. Thin edges first, attributed nodes last

Two kinds of envelope reach L2: **edge** envelopes carrying two endpoint
references and a predicate and *no* attributes, and **node** envelopes carrying
one node's attributes.

**The edges must be ingested first.** The last claim at a URI wins; it does not
merge. An edge envelope arriving *after* a node envelope supersedes it, and the
node is then served with no name, no LEI and no class chain — **and nothing
raises**. Chronological intuition says "edges are facts we learn later, so
ingest them later", and that intuition is exactly what erases the attributes.

The order is asserted in `deployment.ingest`, so reversing it fails loudly
instead of silently. Do not "tidy" it back.

### 2. The caller's depth and the operator's ceiling are two different numbers

* **`max_depth`** is the caller's request state. It folds through the class
  default, the declared domain and the graph leg's technical capability, and the
  effective value that survives is what the **acquisition** walks at.
* **`depth_limit`** on the traversal operator is the **backend's ceiling**. It
  is what a request above it is refused against, with authority `technical`.

One number serving as both would make a product decision look like a capability
limit. `max_depth=99` is refused because of the ceiling; `max_depth=1` is served
at 1 because of the caller.


## Artifact-by-artifact

| file | what it is |
|---|---|
| `ccf_config.yaml` | the single Control Plane document — every section this deployment puts in force |
| `backends.yaml` | how the two source stores are reached. Variable **names** only; no host, port, path or credential |
| `artifacts/source-vocabulary.yaml` | the sources' own names — six predicate IRIs, the table, its columns |
| `artifacts/projection.yaml` | Π's declared values: the cycle bound and the roster cap |
| `acquisition.py` | the two source legs. **Imports no `ccf` at all** |
| `deployment.py` | this deployment's vocabulary, the envelopes, the debt |
| `projection.py` | Π — the payload, and the cycle enumeration |
| `produce.py` | **the fabric's half.** Three regions: `boot`, `acquire`, `govern` |
| `run.py` | presentation. The only module that prints |
| `FINDINGS.md` | what authoring this against the current SDK surface exposed |

`produce.py` contains **no domain vocabulary at all** — no predicate, no table,
no column, no entity class, no LEI, no number. Delete `ccf_config.yaml` and
nothing in `deployment.py` has anything left to interpret. That separation is
the No-Hardcoding Rule (CLAUDE.md §6.4) being structural rather than
aspirational.

### What is deliberately absent

No `gate` region, no `record` region, no `serve` region, and no call to
`run_gates`, `build_replay_record` or `serve` anywhere in this tree. The door,
the graph view, both operators, Π, the three L6 gates, the five-dimension
Decision Replay record, the query pins and the delivery are **one object the SDK
owns**, reached by a single `build_governed_resolver` call. cp-04 hand-composed
every one of them; the difference between the two trees is the clearest
statement of what the canonical path now carries.


## Whitepaper / CLAUDE.md sections exercised

Whitepaper §7.3 (typed graph state), §7.4 (operator algebra), §7.5 (Π), §7.6
(the product contract and its three validation gates), §7.7 (half-life and
debt), §7.10 (Decision Replay). CLAUDE.md §6.4 (No-Hardcoding), §10
(single-writer — `booted.handle.worker` is the only write handle to L3 anywhere
in this process).

Rulings it is authored against: `D-IMPL-309` (the store pin is execution
provenance recorded in replay, not product identity), `D-IMPL-310` (replay
dimension 2 is a **superset** of product policy lineage and carries the
request-contract binding), `D-IMPL-311` (`RefusalEnvelope` is the canonical
consumer-facing refusal), `D-IMPL-313`/`D-IMPL-314` (this successor's charter),
`D-IMPL-315` (a richer canonical path is a finding to adjudicate, not a licence
to edit the example), `D-IMPL-316` (a position is not an identity).

## What to change first

1. **The anchor.** `run.py`'s `DEMONSTRATION_ANCHOR`, or pass an LEI as the
   first argument. Everything else follows from which family you name.
2. **`families`.** The identifiers the request is entitled to walk, which become
   the policy operator's admitted set. Ordinarily the anchor's own LEI as a
   one-element list; a caller entitled to two families names both, with no
   second code path.
3. **The depth.** Pass a second argument to `run.py`, or omit it to let the
   class default in `ccf_config.yaml` resolve — which is a different thing from
   passing the default's value, and the run prints which happened.

To point this at **your own estate**, edit `artifacts/source-vocabulary.yaml`
(the IRIs, the table and its columns) and `backends.yaml` (the environment
variables and the backend's declared traversal ceiling). No Python changes.


## What would fail

Each of these is asserted in `tests/examples/test_cp_04_canonical_output.py`, so
breaking one is loud rather than silent.

- **Reverse the ingestion order** — attributed node claims before thin edge
  envelopes — and every node is served with no name, no LEI and no class chain.
  Nothing raises; `deployment.ingest` asserts the outcome so the reorder fails
  where it happened.
- **Read to the backend ceiling and let Π discard the excess**, and `D_c` stops
  moving with the served roster. It sat at a constant 0.4 across every depth
  before that was repaired — a debt about the estate rather than about the
  answer.
- **Collapse `max_depth` and `depth_limit` into one number** and a product
  decision starts reporting as a capability limit, or a request above the
  ceiling is quietly answered at a narrower depth and seals to a content
  address that greens.
- **Build the plan from anything but the resolver's `required` tuple** — or
  write the factory as a lambda — and the deployment has authored a second
  operator set the Control Plane cannot see.
- **Borrow the specimen's identity** — its content addresses, its `D_c` of
  0.0909, its published artifact ids, or a snippet include from its tree — and
  this stops being its own determination.
- **Modify `examples/cp-04-corporate-family-tree`** at all. It is frozen under
  `D-IMPL-261`; a test measures it at zero files changed against the branch
  point.
