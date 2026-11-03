# Phase 5 — Release Review Status

## Baseline

`drcastillo/ccf_code/main@ff470d400976815e9a1e49176ca51f97e4e691b1`

`ccf_code` remains read only. All adoption documentation writes are in `drcastillo/ccf_adoption`.

## Learning architecture

```
05-reference/
├── README.md
├── 01-client-developer/
├── 02-context-product-producer/
├── 03-decision-replay/
├── 04-create-your-own/
└── 05-technical-reference/
```

## Completed review decisions

- client path begins with **Hello World of CCF**;
- producer path begins from the restored data-estate prerequisite;
- shipped CP examples teach **README → completed spec → implementation**;
- CP-00 through CP-24 remain the Context Product ladder;
- new-product AI-assisted specification authoring is isolated under Create Your Own;
- technical/API material is reference, not the front door;
- Decision Replay is now qualified and supported.

## Final Decision Replay increment

### DR-01

Reconstructs:

- served Context Products through `replay(...)`;
- governed refusals through `replay_refusal(...)`.

Uses the supported `RecordedEnvironment`; no hand-built/private Replay environment is taught.

### DR-02

Documents Assembly Mode 2:

- finished governed product as substrate;
- LLM packaging at acquisition;
- versioned prompt/model/temperature;
- packaging trace on Replay dimension 3;
- smoothing gate before delivery;
- algorithmic → semantic → algorithmic.

## API/reference refresh

The mechanical public-surface reference was regenerated from the current committed SDK manifest.

- public modules: **208**
- Replay modules: supported
- Replay runtime lookup modules: supported
- old deferred Replay appendix: removed/replaced

## Known release cleanup outside adoption repo

Two SDK-native explanatory pages still contain stale wording that says Replay needs private `GovernedResolver._operator_parameters`:

- `public/how-to/reconstruct-a-governed-determination.md`
- `public/concepts/replay-anatomy.md`

Current SDK code and D-IMPL-346 use public `GovernedResolver.operator_parameters(...)`. The adoption manual uses the current implementation, not the stale prose.

Because `ccf_code` is read-only in this workflow, that wording is recorded for the SDK release owner to correct.

## Review posture

**RELEASE READY — FINAL QA COMPLETE**


## Final release QA

- 76 Markdown files under `05-reference` checked.
- 0 broken relative links.
- 0 stale references to the old `03-create-your-own`, `04-technical-reference`, or nested Replay paths.
- 0 old `015be95f...` SDK baseline references in release-facing `05-reference` pages.
- 0 remaining Decision Replay deferred-language findings.
