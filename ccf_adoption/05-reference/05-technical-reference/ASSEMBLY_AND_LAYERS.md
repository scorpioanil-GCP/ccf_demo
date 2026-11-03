# Assembly and L1–L6

**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

CCF's L1–L6 layers are responsibility boundaries, not merely a sequential pipeline.

## L1 — Signal

Sources normalize observations into typed `SignalEnvelope` values.

Current main adds an ingress temporal guard:

- `IngressTemporalBound`
- `TemporalWriteRefused`

A source observation outside the tenant's declared temporal window is refused before the single writer mutates L3. The writer does not make old evidence “current” by restamping it.

## L2 — Assembly

`AssemblyWorker` remains the single writer into governed graph state.

Identity resolution now has the named `IdentityRefused` failure for an identity that cannot be safely minted. An empty identity declaration/value does not become a hash of an empty map.

## L3 — Context Graph

Governed temporal/relational state and its query/view protocols.

Read paths must stay scoped to the decision snapshot and policy-shaped view.

## L4 — Operators

Pure/read-only computation categories such as Policy, Temporal, Similarity and Traversal.

## L5 — Projection

Typed perspective-conditioned transformation into decision shape.

Projection is not RBAC filtering.

## L6 — Context Product

The governed delivery contract, request surface, gates, refusal, composition and Replay binding.

## Trusted time across layers

Current main's temporal-boundary policy prevents a caller-controlled `asked_at` from becoming an unrestricted fabric clock.

The same declared time posture is used at the request/serve boundary and the write refusal seam; the ingestion timestamp continues to record actual ingestion rather than being rewritten to make an envelope pass.

## Security invariant

A security decision should be made at the layer that owns it:

- input shape at the request boundary;
- temporal write admissibility at the writer;
- policy before downstream projection;
- delivery authorization at the runtime boundary;
- replay integrity from retained exact evidence.

Pushing all of these into presentation code would create multiple inconsistent sources of truth.

## Classification changes are authority-owned

L2 uses the resolution specification to judge which sources may assert each governed classification attribute. An unauthorized omission is audited and admitted; an authoritative source may change or omit its label. Access consumers then require the boot-minted classification authority at reader/operator construction and use. See [Graph and Storage](GRAPH_AND_STORAGE.md).
