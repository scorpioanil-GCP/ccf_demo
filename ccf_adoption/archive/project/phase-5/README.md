# Phase 5 — SDK Developer and Engineer Manual

## Status

**RELEASE CANDIDATE — DECISION REPLAY COMPLETE**

Branch: `decision-replay-finalize`

## Qualified SDK

- repository: `drcastillo/ccf_code`
- branch: `main`
- commit: `ff470d400976815e9a1e49176ca51f97e4e691b1`
- posture: merged release baseline

`ccf_code` remains **read-only** for adoption-documentation work. All documentation changes land in `drcastillo/ccf_adoption`.

## User-facing structure

```
05-reference/
├── 01-client-developer/
├── 02-context-product-producer/
├── 03-decision-replay/
├── 04-create-your-own/
└── 05-technical-reference/
```

The ordering is intentional:

**consume → produce → replay/package → create your own → reference as needed**

## Completed learning coverage

### Client developer

- Hello World of CCF
- ProductClient / Result
- governed refusal
- in-process vs MCP
- ADK / Claude Agent SDK / LangGraph

### Context Product producer / data engineer

- prerequisite CCF data estate
- CP-00 through CP-24
- README → completed specification → source
- spec-to-code explanation
- run / vary / refuse / validate

### Decision Replay final capability rungs

- **DR-01 — Replay a Governed Determination**
  - served-product reconstruction
  - governed-refusal reconstruction
  - supported `RecordedEnvironment`
  - exact retained/pinned evidence

- **DR-02 — Package a Context Product**
  - Assembly Mode 2 / `llm_packaged`
  - model/prompt/temperature/output pins
  - smoothing gate
  - algorithmic → semantic → algorithmic

The Context Product ladder remains closed at CP-24. DR-01/DR-02 are capabilities exercised over Context Products, not CP-25/26.

### Create Your Own

```
business problem
    ↓
SME + data engineer settle authority-owned terms
    ↓
AI assistant drafts specification
    ↓
GATE 1
    ↓
AI assistant generates implementation
    ↓
run + sabotage + independent validation
    ↓
GATE 2
```

## Authority order

For release documentation:

1. current code at the pinned SDK commit;
2. current tests and gates;
3. current qualified runnable examples;
4. committed public reference pages when consistent with 1–3;
5. historical material only as history.

## Release note

The adoption manual is aligned to the completed Decision Replay implementation. One stale explanatory statement remains in the read-only SDK source documentation: the SDK Replay how-to/anatomy pages still describe `GovernedResolver._operator_parameters` as a private dependency even though D-IMPL-346 and current `RecordedEnvironment` use the public `operator_parameters(...)` surface.

That source-document wording should be corrected in `ccf_code` before publishing those SDK-native pages as release documentation. The adoption manual does not repeat the stale claim.
