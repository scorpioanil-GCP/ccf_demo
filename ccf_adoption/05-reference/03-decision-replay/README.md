# Decision Replay — Final Capability Rungs

**Current-main additions:** durable `evidence_root`, source-free inspection, launcher `decisions` / `why` / `replay`, and composite reconstruction from retained child evidence are described in [Decision Replay](../05-technical-reference/DECISION_REPLAY.md). The qualified DR tutorials below retain their historical pins.

**Qualified SDK release:** `v1.0.1`  
**Tagged commit:** `a4cf2fb74af4964dcfee29d210d17d94b909d78d`

The Context Product ladder ends at **CP-24**.

The `dr-NN` series does not add more Context Product rungs. It exercises capabilities **over** governed products and determinations.

Complete the CP examples first, then use these two final examples:

1. [DR-01 — Replay a Governed Determination](DR01_REPLAY_A_GOVERNED_DETERMINATION.md)
2. [DR-02 — Package a Context Product](DR02_PACKAGE_A_CONTEXT_PRODUCT.md)

## Why these come last

By this point you already know how to:

- assemble a Context Product;
- declare its policy, temporal, debt and perspective semantics;
- serve or refuse it through a governed boundary;
- compose products;
- use agents, HITL, federation and portfolio-level products.

Decision Replay then answers two final questions:

1. **Can I reconstruct exactly what the fabric decided?**
2. **If a model packages a governed product into human-facing prose, can I prove what model/prompt/output produced it and prevent the packaging from changing the conclusion?**

DR-01 answers the first. DR-02 answers the second.

## Learning sequence

```
governed determination
      ↓
retained five-dimension replay record
      ↓
DR-01: reconstruct served or refused decision
      ↓
DR-02: package a governed product with an LLM
      ↓
pin model / temperature / prompt / output
      ↓
gate the packaging before delivery
```

## Important distinction

**Replay is reconstruction, not re-running today's world.**

The replay engine uses the record's retained addresses, recorded snapshot, pinned declarations, effective request and execution path. It does not call the original producer again or silently substitute current state.

DR-02 likewise does not make the model the source of truth. The algorithmically assembled upstream Context Product remains the artifact-of-record; the model creates a derivative view that must pass ordinary CCF governance before it can be served.
