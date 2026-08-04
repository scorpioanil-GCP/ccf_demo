# Pillar: Data and Context Layer

This pillar is where the fabric earns its name. It is the SDK's answer to a
single question: *how does an agent get at first-party records, third-party
feeds, and material produced by other agents — in a form that is typed, fresh
enough to act on, governed, and reconstructible afterwards?*

Everything else in the SDK consumes what this pillar produces.

## What the pillar is for

Users reach for the Data and Context Layer when they have systems of record
that already work and no appetite for replatforming them. The pillar lays a
governed layer *over* those systems rather than replacing them: sources stay
where they are, change flows in, and what comes out the far end is a typed
Context Product with an SLO envelope and a lineage set attached.

Three properties distinguish that from a query result:

- **Derivation, not storage.** A Context Product is computed at request time
  from graph state under an operator plan and a projection, so it carries the
  policy regime and the freshness posture in force when it was derived.
- **Decay is modelled, not assumed.** Every observation type carries a
  half-life (`λ_c`); the shortfall when freshness or completeness falls below
  the configured floor is Context Debt (`D_c`), and debt is what triggers
  forced escalation or fail-closed behaviour rather than a silently stale
  answer.
- **One writer.** Assembly is the only component holding a write handle to the
  graph. That is what makes the lineage trustworthy, and it is enforced at
  boot, not by convention — see [the invariants page][invariants].

## How the SDK realizes it

The pillar is the fabric's L1–L6 (CLAUDE.md §10) plus two cross-cutting
surfaces: the bidirectional MCP integration surface (§7.1) and artifact
persistence (§7.4).

| Layer | Role |
| --- | --- |
| L1 Signal | Ingest and normalize — change-data capture, MCP-client ingress, file and stream adapters. No interpretation happens here. |
| L2 Assembly | Entity resolution, temporal stitching, policy binding. The sole writer to the graph. |
| L3 Context Graph | The typed persisted state `G(E, R, T, P, Π, L)` — append-only, with logical supersession. |
| L4 Operators | Read-only, composable, planned as a DAG: traversal, temporal, policy, similarity. |
| L5 Projection | `Π` as a typed transformation, selected by perspective, product class, and parameters. |
| L6 Products | The delivery contract, gated on three validations before anything is served. |

The Control Plane sits orthogonal to all six, holding the values the mechanism
interprets — policy definitions, operator parameter sets, half-life tables and
debt thresholds, materialization policy, and the definition artifacts the
factories read. It is also the audit plane.

The diagram below shows both planes at once: the Control Plane feeding
versioned configuration down into the fabric, the single write edge from
assembly into the graph, the read-only path out through operators and
projection to the three egress surfaces, and the replay record that every
served product produces by construction.

```mermaid
--8<-- "public/diagrams/pillar-data-context.mmd"
```

## The persistence seam

The live graph and the immutable artifacts are deliberately different
substrates. Hot state lives on the graph store; replay records, snapshots,
products at rest, Control Plane bundles, and the definition artifacts live
behind `ArtifactStoreProtocol`, which ships with an MCP-backed reference
implementation and a file-backed development one.

The seam matters for one structural reason: retrieving an artifact never
becomes a second path into the graph. Anything recovered from the store
re-enters through assembly like any other input.

```mermaid
--8<-- "public/diagrams/seam-artifact-store.mmd"
```

## Where this lives

The surfaces that realize this pillar:

- [Storage and Context Graph][storage] — the graph store protocol and its
  reference backends.
- [Similarity][similarity] — the similarity index protocol.
- [Operators and projection][operators] — the operator algebra and `Π`.
- [Context Products][products] — the product contract and its validation
  gates.
- [Half-life and debt][halflife] — `λ_c` and `D_c` computation.
- [Artifact store][store] — the persistence protocol and its implementations.

Related concepts: [architectural invariants][invariants] and
[the anatomy of a replay record][replay].

Whitepaper readers: this pillar corresponds to chapters 5 through 7 —
see the [cross-reference index][index] for the section-by-section mapping.

[storage]: ../../reference/protocols/storage-and-graph.md
[similarity]: ../../reference/protocols/similarity.md
[operators]: ../../reference/protocols/operators-and-projection.md
[products]: ../../reference/protocols/context-products.md
[halflife]: ../../reference/protocols/halflife-and-debt.md
[store]: ../../reference/protocols/artifact-store.md
[invariants]: ../invariants.md
[replay]: ../replay-anatomy.md
[index]: ../whitepaper-index.md
