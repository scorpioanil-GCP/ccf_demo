# Product assembly and refusal sequences

**SDK source:** `ccf_code/main@f07e558ed04c81154687d7efcc6312591e7f6f7d` · **Inspected:** 2026-10-09.

[Design index](README.md) · [Source inventory and verification scope](10_SOURCE_INVENTORY.md)

## Opening and answering on the facade

This sequence follows `open_product` and `OpenedProduct.answer`. It omits helper calls but preserves the lifecycle and ownership boundaries. A configured composite inserts child resolution before parent projection; that branch has its own [composition sequence](06_COMPOSITION_AND_PEERING_DESIGN.md).

```mermaid
sequenceDiagram
    participant App as Producer application
    participant O as OpenedProduct
    participant B as Deployment boot
    participant R as GovernedResolver
    participant D as Domain callbacks
    App->>O: open_product(config_root, acquire, project, assess, authorities)
    O->>O: Parse declarations and bind deployment objects
    O-->>App: OpenedProduct
    App->>O: answer(ProductRequest, perspective)
    O->>O: Admit class and compatible lane
    O->>B: load_config_and_boot for fresh substrate
    B-->>O: BootedFabric
    O->>R: build_governed_resolver(build_arguments)
    O->>R: Resolve question
    R->>R: Resolve defaults, constraints and temporal bounds
    alt Question refused before acquisition
        R->>R: Persist refusal evidence
        R-->>O: RefusalEnvelope
    else Effective question admitted
        R->>D: acquire(AcquisitionContext)
        D-->>R: SignalEnvelope stream through acquisition seam
        R->>R: Read fabric, project, assess and gate
        R->>R: Persist served or refused decision
        R-->>O: ResolverOutcome
    end
    O->>B: Close fabric handle in finally
    O-->>App: Outcome, or propagated failure
```

The application supplies `control_plane` and `erasure_trust` explicitly at this pin. These are composition dependencies, not implied globals. `open_product` also accepts an artifact store, clock, optional product gate and child-question/resolver seams.


Sources: [src/ccf/products/product.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/products/product.py); [src/ccf/deployment/config.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/deployment/config.py); [src/ccf/products/resolver.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/products/resolver.py).

## Acquisition and the graph write boundary

```mermaid
sequenceDiagram
    participant R as GovernedResolver
    participant A as Acquisition seam
    participant D as Domain acquisition
    participant W as AssemblyWorker
    participant G as Graph writer
    R->>A: Effective request and perspective
    A->>A: Read trusted ingress clock
    A->>D: acquire(context)
    loop Each returned envelope
        D-->>A: SignalEnvelope
        A->>A: Check tenant and asked-at identity
        A->>A: Enforce IngressTemporalBound
        A->>W: ingest(envelope)
        W->>W: Resolve entities and relationships
        W->>G: Write resolved claims
    end
    A-->>R: Acquisition complete
```

The question's instant, the source observation time and the trusted ingress/serve clocks answer different questions. In particular, `AcquisitionContext.instant` is the bounded as-of request boundary. The ingress guard compares the envelope against a trusted clock; comparing a timestamp to itself would not enforce an age limit.

A recognized temporal or domain refusal raised at the seam is converted into a recorded refusal by the resolver. Unknown exceptions remain failures. No source database write is implied by `worker.ingest`: it writes the fabric through its own writer.


Sources: [src/ccf/products/product.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/products/product.py); [src/ccf/assembly/worker.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/assembly/worker.py); [src/ccf/controlplane/temporal_boundary.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/controlplane/temporal_boundary.py); [src/ccf/products/resolver.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/products/resolver.py).

## Projection to delivery

```mermaid
sequenceDiagram
    participant R as GovernedResolver
    participant P as ProjectionEngine
    participant G as Gates and tolerance
    participant S as Replay serve seam
    participant A as Artifact store
    R->>R: Build plan from declared required operators
    R->>R: refuse_operator_set_divergence
    R->>P: execute(plan, perspective, request seeds, boundary)
    P-->>R: Output, execution lineage and query sequence
    R->>R: Assess debt and build candidate with declared lineage
    R->>G: Validate candidate and obligations
    alt Gate or delivery-tolerance refusal
        G-->>R: Refusal
        R->>S: Record refusal through ReplayWriter
        S->>A: Persist evidence before returning shell
        S-->>R: Replay reference
    else Admitted and deliverable
        G-->>R: ServableProduct
        R->>S: serve(product, record, queries)
        S->>S: Verify provenance and content-address agreement
        S->>A: Persist query bytes
        S->>A: Append replay record
        S-->>R: ServedProduct
    end
```

This is a summary of the final stages, not a promise of one store transaction across all writes. The explicit ordering is query bytes before replay record and replay record before response. A write failure prevents delivery; previously written evidence need not be rolled back.

The binder checks independently authored declarations before projection. The lineage gate later checks assembly-path integrity. Those checks have different purposes; the existence of a lineage comparison is not proof that a misdeclared plan can pass through the binder.

## Failure semantics

| Condition | Outcome |
| --- | --- |
| Unsupported question, policy constraint, temporal bound or recognized seam refusal | Recorded governed refusal; no empty-success substitute. |
| Required composite child blocks | Retain already admitted child contracts, then record the parent's refusal. |
| Candidate passes gates but exceeds effective debt tolerance | Withheld delivery, recorded as refusal. |
| Replay store cannot persist required evidence | Failure propagates; no successful served product or audited refusal shell is fabricated. |
| Wrong resolver tenant/class wiring | Wiring exception rather than a decision about a valid question. |

The diagrams show source ordering. They do not claim that live example gates or backends were executed during this documentation work.


Sources: [src/ccf/deployment/binder.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/deployment/binder.py); [src/ccf/products/gates.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/products/gates.py); [src/ccf/products/resolver.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/products/resolver.py); [src/ccf/replay/serve.py](https://github.com/drcastillo/ccf_code/blob/f07e558ed04c81154687d7efcc6312591e7f6f7d/src/ccf/replay/serve.py).
