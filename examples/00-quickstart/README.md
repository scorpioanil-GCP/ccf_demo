# 00 — Quickstart: "Hello, Context Product"

The smallest possible fabric, end to end in one process: register an
ontology, ingest a handful of events through L1, assemble into the Context
Graph, run the four-category operator chain, project, pass the three L6
validation gates, record the decision, and serve **one typed Context
Product** — keyless and model-free, on the SQLite reference backend and the
file-backed ArtifactStore.

Every later example builds on this shape.

## Run it

```sh
make example-00
```

or, directly:

```sh
PYTHONPATH=src:runtime python examples/00-quickstart/run.py
```

The driver is an asserted program: exit code 0 means every invariant below
held; any failure exits nonzero. CI treats nonzero as red.

## What it demonstrates

| Invariant | What would fail here |
| --- | --- |
| single-writer (INV-CH7-10) | there is no writer to obtain; the fabric is booted through the real composition root |
| idempotent upsert + lineage set-union (INV-CH7-16/17) | the same customer arriving from `core-banking` and `crm` would create a second node, or overwrite instead of accumulating lineage |
| policy substitution (INV-CH7-26) | the restricted mandate — or the `authorizes` edge that would leak its existence by absence — would survive |
| similarity ranking (INV-CH7-27) | the off-query deposit account would survive |
| bounded traversal (INV-CH7-24) | the walk would reach past its typed, depth-bounded neighborhood |
| the three gates (INV-CH7-46/47/48) | an empty-operator, forged-lineage or over-TTL product would become servable |
| lineage strict equality | the product's `operators_invoked` would diverge from what the engine resolved as having run |
| replay before delivery (INV-CH7-79) | a product would be served with no five-dimension record in the store |
| λ_c is configuration, never code (INV-CH7-58) | a half-life would exist somewhere other than `artifacts/halflife.yaml` |

## What it exercises

- **Whitepaper:** §5.2 / §7.3 (Context Graph), §7.4 (operator algebra),
  §7.5 (projection Π), §7.6 (Context Product Contract and its gates),
  §7.7 (context half-life λ_c), §7.10.1 (five-dimension Decision Replay
  record).
- **CLAUDE.md:** §5 (primitives quick reference), §6.4 (the No-Hardcoding
  Rule — see below), §9 (examples discipline), §10 (L1–L6 layering and the
  single-writer invariant).

## Domain rationale (D-09)

This example is a **banking** scenario (a payments-analyst view over a
customer, its accounts, and a restricted direct-debit mandate), per
D-IMPL-52: `examples/00-quickstart` is the suite's banking entry, chosen
because banking puts realistic policy and regulatory pressure on the fabric
— classification-driven substitution and jurisdiction-bearing policy
bundles are load-bearing here, not decoration. All domain values live in
`artifacts/`; the data is synthetic and fictional.

## The No-Hardcoding Rule, made visible

`run.py` contains no entity class, no threshold, no query string, no TTL,
no half-life and no expected result — every one of those is declared in
`artifacts/*.yaml` and loaded at run time. Delete `artifacts/` and the
driver has nothing meaningful to run (CLAUDE.md §6.4). Code is interpreters
and factories; artifacts carry everything specific.

## What to change first

`artifacts/` **is** the specialization surface:

- `ontology.yaml` — your entity classes, identity keys, relationship
  rules, and which attributes carry classification and similarity text.
- `events.yaml` — your source systems' payloads, in their vocabulary.
- `controlplane.yaml` — your policy bundle, operator parameters, product
  class, MAX_TTL, perspective, and decision instants.
- `halflife.yaml` — your λ_c calibrations and debt profile.

Change those and rerun; `run.py` should not need to change until your
projection means something different — `QuickstartPlan` is the one piece of
deployment *code* here, because a projection is what a user writes.
