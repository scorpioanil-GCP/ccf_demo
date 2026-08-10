# The FIBO KYC/UBO ownership extension — what was added, and what it does not claim

**Status:** provenance record for
`examples/s1-01-hello-context-product/artifacts/source-estate.yaml`.
**Plan:** 16-02 (phase 16, wave 2).
**Rulings it serves:** phase 16 CONTEXT **D-03** (KYC/UBO as the use-case
spine), **D-04** (FIBO stores are an *enterprise source* CCF reads at L1, never
loaded wholesale into CCF's graph), **D-10** (the adoption argument's worked
demonstration is the UBO question).
**Measured:** 2026-08-10, against
`/home/parkave/fluree/examples/fibo/mongo-entities.json` and
`mongo-relationships.json` as they stood on that date, and against the estate
`examples/s1-01-hello-context-product/source_estate.py` generates from the
declared artifact. Every count below is scripted output from those two sides,
not an estimate.

## Why an extension was needed

`16-RESEARCH.md` **FINDING F-1** measured the shipped FIBO dataset and found
two things that make the phase's central question unanswerable on it:

1. **`ownershipPercent` is an attribute of the Party entity, not of the
   ownership relationship.** A party carries *one* percentage regardless of how
   many entities it holds an interest in. No shipped relationship record
   carried a percentage at all — measured: **0 of 11**. A chain whose hops
   carry no fraction cannot be aggregated.
2. **Every `hasOwnershipInterestIn` edge ran Party → Corporation in exactly one
   hop.** No corporation owned another. Measured relationship types in the
   shipped file: `isRelatedTo` ×6, `hasOwnershipInterestIn` ×4,
   `hasControllingInterestIn` ×1.

D-03's stated teaching property — *"multi-hop ownership chains are what a graph
does and what chunk retrieval does badly"* — and D-10's worked demonstration —
*"traversing an ownership chain, aggregating percentages across hops"* — are
both undemonstrable against that shape. Dave's own instruction covers the
remedy: use the use case the FIBO stores can support today *"or be provided
additional data to support"*.

## What was added

The extension is **additive**, not a replacement. Nothing measured was removed,
renamed or re-valued.

| | Shipped | Generated |
|---|---|---|
| Entities | 14 | 14 |
| Relationships | 11 | 16 |
| `isRelatedTo` | 6 | 6 |
| `hasControllingInterestIn` | 1 | 1 |
| `hasOwnershipInterestIn` | 4 | 9 |
| Ownership edges carrying their own `ownershipPercent` | 0 | 9 |
| Corporation → Corporation ownership edges | 0 | 4 |
| Distinct `jurisdiction` values | 4 | 4 |

Two structural additions produce that table:

**(a) Per-edge percentages.** Every `hasOwnershipInterestIn` record now carries
its own `ownershipPercent`. The entity-level field is **kept exactly as
measured** — the extension adds a field, it does not move one — so the existing
out-of-tree loaders and the queries in `compare_backends.py` keep working
unchanged. Hans Müller is the clearest witness for why the edge-level field is
necessary: his Party record carries no percentage whatsoever, and his ownership
edge now does.

**(b) Four corporation → corporation ownership edges**, plus one direct
Party → Corporation edge that makes aggregation the only way to reach an
answer. Design intent, stated so a later reader can tell it from accident:

- **Jane Doe** crosses the 25% beneficial-ownership threshold on Acme *only*
  under aggregation. Her direct edge is 12.0%; her indirect holding is 60.0% of
  Beta Holdings × 30.0% of Acme = 18.0%; together 30.0%. **No passage of any
  document states 30.0%** — the number exists only in the relationships, which
  is exactly the claim the adoption-argument page makes.
- **Sarah Chen** reaches Acme in three hops for 1.125% — a chain that exists,
  is traversable, and lands nowhere near the threshold. Depth is not
  significance.
- **Hans Müller** reaches Acme in three hops through a German bank and a
  British broker for 0.1%, so one chain spans three regulatory regimes and the
  Policy axis has real work to do.
- **John Smith** is 45.0% direct and needs no traversal at all — the case
  retrieve-then-filter gets right, kept so the contrast is visible.

The ownership edges form a DAG (Acme owns nothing), so traversal terminates
without a cycle guard being the thing under test.

**What was deliberately frozen.** Sarah Chen stays at exactly `25.0` — the
FinCEN CDD beneficial-ownership threshold boundary case D-03 names. A threshold
nobody sits exactly on is a threshold no example can show the sense of. Both
planted near-duplicate pairs survive ("Acme Corporation" / "Acme Global Trading
Corporation", "Beta Holdings LLC" / "Beta Investment Holdings"); they are what
makes the Similarity axis non-trivial here.

## How additive was verified

The generator emits the JSONL streams in **declared order**, and the declared
order is the shipped order with additions appended. Measured against the
shipped files:

- The entity stream is **byte-identical** to `mongo-entities.json`.
- **7 of 11** shipped relationship lines come back **verbatim**.
- The remaining **4** — the ownership edges — come back as the shipped line
  with `"ownershipPercent"` appended as the last key, so the shipped content is
  a literal prefix of the extended line.
- **5** relationship lines are new.

That is why the added key is written last in every record: "is the extension
additive?" stays a `diff` a human can read at the checkpoint rather than a set
comparison run by a script nobody has audited.

## A correction to `16-RESEARCH.md` Assumption A2

A2 recorded three jurisdictions as directly observed (`US-DE`, `US-NY`, `DE`)
and flagged CONTEXT's fourth (`GB`) as unread. Measured: **four distinct
`jurisdiction` values exist in the shipped entity records** — the fourth is
Omega Securities' `GB`. D-03's "four jurisdictions" claim stands as written and
needs no correction. Nothing was added to reach four.

## What this extension does **not** claim

- **It is not a corporate registry.** The corporation-to-corporation ownership
  structure is *synthetic*, layered onto a real FIBO shape. The entities, their
  LEIs, their jurisdictions and their one-hop ownership edges are the measured
  dataset; the multi-hop chain and every per-edge percentage are authored for
  this example. A reader must not take the ownership graph as a statement about
  any real company.
- **It is not a compliance artifact.** The 25% figure is used because it is the
  FinCEN CDD beneficial-ownership threshold and therefore makes a *realistic*
  boundary case. Nothing here is a regulatory calculation, and the SDK ships no
  regulatory policy bundle (CLAUDE.md §13).
- **It is not CCF's Context Graph.** `source_estate.py` writes an *enterprise
  source estate* — the world that exists before any fabric does. Nothing it
  produces enters L3 except through L2 ingress (single-writer, CLAUDE.md §10;
  phase 16 CONTEXT D-04). `tests/examples/test_source_estate.py` states that as
  an AST check on the module's imports rather than as a comment.
- **It makes no claim about the four DGX stores.** The in-repo estate is what
  always-on CI reads. Whether the live Fluree, MongoDB, Neo4j and PostgreSQL
  instances hold the same logical dataset is `16-RESEARCH.md` **Assumption A3**,
  which plan 16-02's human checkpoint answers with credentials this environment
  does not have.

## Where the properties are stated

`tests/examples/test_source_estate.py`, against the **generated** estate rather
than against the declaration — a generator that dropped or mangled a record
fails there rather than passing on the strength of what the artifact says about
itself. It states the depth-≥2 chain, the per-edge percentages, the aggregation
that crosses the threshold, the frozen boundary case, both near-duplicate
pairs, byte-level determinism across two runs, that the generator reaches no
graph writer, and that deleting the artifact leaves the module with nothing to
run (CLAUDE.md §6.4).
