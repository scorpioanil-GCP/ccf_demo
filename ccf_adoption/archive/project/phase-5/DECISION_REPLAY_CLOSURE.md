# Decision Replay Closure

**Qualified SDK:** `drcastillo/ccf_code/main@ff470d400976815e9a1e49176ca51f97e4e691b1`

## Status

**COMPLETE — SUPPORTED FOR RELEASE**

The Phase 5 hold is closed. D-IMPL-346/347-era Replay surfaces are now merged on the qualified SDK mainline and are documented as supported.

## Final adopter surfaces

- `ccf.replay.environment.RecordedEnvironment`
- `ccf.replay.engine.replay`
- `ccf.replay.engine.replay_refusal`
- `ccf.replay.engine.ReplayOutcome`
- `ccf.replay.engine.RefusalReplayOutcome`
- `ccf.replay.record.DecisionReplayRecord`
- `ccf.replay.record.PackagingTrace`
- `ccf.controlplane.artifacts.ReplayBinding`
- first-class Replay evidence on governed refusals
- runtime Replay query/resolve surfaces

## Final examples

### DR-01 — Replay a Governed Determination

`examples/dr-01-replay-a-governed-determination`

Demonstrates exact reconstruction of:

- a served Context Product;
- a governed refusal.

Uses the supported `RecordedEnvironment`; no hand-assembled/private Replay environment is taught.

### DR-02 — Package a Context Product

`examples/dr-02-package-a-context-product`

Demonstrates:

- Assembly Mode 2 / `llm_packaged`;
- versioned prompt/model/temperature;
- Replay dimension-3 packaging trace;
- output hash;
- smoothing gate;
- substrate-based expiry;
- governed refusal when packaging moves the conclusion.

## Ladder rule

The Context Product ladder remains **CP-00 through CP-24**.

DR-01 and DR-02 are capabilities exercised over Context Products and determinations. They are not CP-25 or CP-26.

## Source-document cleanup noted for SDK release

The read-only SDK source contains stale prose in:

- `public/how-to/reconstruct-a-governed-determination.md`
- `public/concepts/replay-anatomy.md`

Those pages still mention private `GovernedResolver._operator_parameters`. Current `RecordedEnvironment` uses public `GovernedResolver.operator_parameters(...)`.

The adoption manual documents the current implementation. The stale SDK-native wording should be corrected by the SDK owner before those pages are published as release documentation.
