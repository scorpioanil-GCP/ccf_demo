# Phase 5 Coverage Matrix

**Qualified SDK:** `ccf_code/main@ff470d400976815e9a1e49176ca51f97e4e691b1`

## User-facing learning paths

| Path | Entry | Coverage | Status |
|---|---|---|---|
| Client Developer | `05-reference/01-client-developer/` | Hello World → Result/refusal → in-process/MCP → ADK/Claude/LangGraph | Complete |
| Context Product Producer / Data Engineer | `05-reference/02-context-product-producer/` | estate prerequisite → completed spec → spec-to-code → CP-00 through CP-24 → run/vary/validate | Complete |
| Decision Replay | `05-reference/03-decision-replay/` | DR-01 exact reconstruction + DR-02 Assembly Mode 2 packaging | Complete |
| Create Your Own | `05-reference/04-create-your-own/` | Standard → AI-assisted spec → Gate 1 → codegen → validation/Gate 2 | Complete |
| Technical Reference | `05-reference/05-technical-reference/` | SDK/API/packages/runtime/Replay/glossary/troubleshooting | Complete/generated |

## Producer example coverage

- CP-00 through CP-24: 25 detailed guides.
- Every CP guide starts with README → qualified specification → qualified source.
- Canonical CP-03/04/06/13 remain the normal copy targets.
- DR-01 and DR-02 are final capability guides, not CP-25/26.

## Decision Replay coverage

### DR-01

Documents:

- `RecordedEnvironment`
- `replay(...)`
- `replay_refusal(...)`
- served vs refused record kinds
- retained snapshot/artifact requirements
- exact content-address reconstruction
- focused CP-06 replay controls

### DR-02

Documents:

- `assembly_mode: llm_packaged`
- upstream Context Product as artifact-of-record
- versioned prompt artifact
- packaging trace
- smoothing gate
- audience policy before materialization
- substrate-based expiry
- nine declared validation gates

## Mechanical reference

The current SDK surface manifest contains **208 public modules**.

Generated appendices include:

- consumer
- products
- fabric
- governance
- agents/integration extensions
- Decision Replay
- runtime

## Remaining release work

1. final relative-link QA;
2. final stale-baseline/deferred-language sweep;
3. record the one SDK-source documentation wording cleanup;
4. final human approval and promotion of `decision-replay-finalize`.
