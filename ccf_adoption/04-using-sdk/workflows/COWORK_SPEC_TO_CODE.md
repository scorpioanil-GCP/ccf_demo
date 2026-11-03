# Cowork Workflow — Business Problem to Governed Context Product

**SDK evidence baseline for this workflow:** `ccf_code@v1.0.1` — `a4cf2fb74af4964dcfee29d210d17d94b909d78d`

## Outcome

Use an AI assistant to accelerate two distinct engineering products:

1. an **approved implementation specification**;
2. an **implementation proven against that specification**.

The AI assistant is an accelerator and evidence organizer. Humans remain accountable for design decisions and authoritative values.

---

## Stage 0 — Build the evidence packet

Before asking the AI to draft anything, assemble a bounded evidence packet.

### Required inputs

#### Business / SME

- decision being supported;
- trigger;
- consuming roles/principals;
- counterfactual: what ordinary retrieval/data product would get wrong;
- scope boundary;
- prerequisites and known consumers;
- classification / information-barrier expectations.

#### Data engineering

- actual systems of record;
- store/schema/table or equivalent implementation binding;
- element/column mappings;
- measured coverage/crosswalk quality;
- timestamps and temporal semantics;
- provenance reality;
- known traps/limitations;
- ontology/semantic bindings;
- source access constraints.

#### SDK

- Specification Standard v0.3;
- qualified SDK baseline;
- smallest canonical example exercising the required primitive;
- public reference pages for required SDK mechanisms.

### Evidence-packet rule

Do not give the AI a whole repository and say “figure it out” if the authoritative evidence can be bounded.

Cowork should be able to state **which source owns each term** before drafting the spec.

---

## Stage 1 — AI drafts Gate-1 specification

Start a **Spec Authoring** Cowork work unit with:

- evidence packet;
- Standard v0.3;
- CP-SPEC-000 as the document-shape template;
- the qualified Phase 5 Specification Reference.

Use [AI Spec Prompt](AI_SPEC_PROMPT.md).

### Required AI behaviors

The assistant must:

1. preserve authority ownership;
2. mark unknown terms `[TBC — <owner>]`;
3. produce sections A–G in Standard order;
4. distinguish implementation-independent business terms from SDK implementation bindings;
5. name store/schema/table in the SDK implementation spec;
6. keep deployment host/credential values out of the spec;
7. make each intended gate falsifiable;
8. identify every value expected to be measured only after build.

### Output

`CP-SPEC-NNN_<Product_Name>.md`

### Stop condition

**STOP. No code.**

---

## GATE 1 — Human design approval

The SME, data engineer, and accountable technical owner review:

- decision and scope;
- request/product contract;
- source bindings;
- semantic/temporal model;
- operator/projection design;
- policy;
- freshness / Debt design;
- intended gates;
- TBC register.

Gate 1 answers:

> **If this exact design were implemented, is it the product we intend to build?**

If no: revise the spec.

If yes: record approval and begin implementation.

---

## Stage 2 — Select the implementation pattern

Do not tell the AI to “write a Context Product from scratch.”

Select the smallest qualified canonical example that already uses the required primitives.

### Default paved-road anchor

`examples/cp-03-canonical-obligor-financial-spread`

Use it for the structural pattern:

- `ccf_config.yaml`
- `ccf_environment.yaml`
- `acquisition.py`
- `projection.py`
- `deployment.py`
- thin `produce.py`
- `run.py`
- server/door if required

### Other anchors

| Need | Preferred example |
|---|---|
| graph + multi-store | canonical CP-04 |
| typed relationship semantics | canonical CP-06 |
| document evidence | canonical CP-13 |
| composite product | CP-14 |
| HITL handoff | CP-15 |
| information barrier | CP-17 |
| perspective/ranking | CP-18 |
| peering/federation | CP-20 |
| agent-internal assembly | CP-22 |
| population product | CP-23 |
| scenario/what-if | CP-24 |

---

## Stage 3 — AI generates implementation from approved spec

Start a new **Implementation** Cowork work unit.

Inputs:

- approved Gate-1 spec;
- selected canonical example(s);
- qualified SDK reference pages;
- data/source access contract;
- current source tree.

Use [AI Code Generation Prompt](AI_CODEGEN_PROMPT.md).

### Generation order

Generate in this order:

1. `ccf_config.yaml`
2. `ccf_environment.yaml`
3. source acquisition adapter
4. envelope mapping / domain assembly helpers
5. projection
6. Debt assessment
7. declared product-specific gate, only if the spec requires one
8. thin paved-road `produce.py`
9. `run.py`
10. door/server only if the product must expose one
11. tests / gate sabotages
12. documentation/delivery artifacts

Why configuration first?

Because code should interpret approved declarations rather than become the hidden place where those declarations live.

---

## Stage 4 — Build discipline

The implementation assistant must maintain these boundaries.

### Acquisition

Owns:

- source access;
- source-specific vocabulary;
- source admission;
- domain arithmetic that is part of acquiring/normalizing the declared evidence.

It should not:

- run product gates;
- create replay records;
- serve products;
- silently substitute Control Plane values.

### Deployment

Owns:

- product-specific callables;
- domain vocabulary;
- acquisition → SignalEnvelope mapping;
- Debt assessment;
- product-specific governed predicate where declared.

### Projection

Owns:

- reading the governed `GraphView`;
- shaping the payload;
- perspective-conditioned interpretation where applicable.

It should not read around the view to raw acquisition state.

### Produce

On the modern paved road, keep it thin:

```python
def product(scratch: Path) -> OpenedProduct:
    return open_product(
        config_root=HERE,
        scratch=scratch,
        acquire=deployment.acquire,
        project=plan_factory,
        assess=deployment.assess,
        gate=deployment.product_gate,
    )

def assemble_and_serve(*, asked, scratch, perspective=None):
    with product(scratch) as opened:
        return opened.answer(asked, perspective=perspective)
```

Do not re-create the governed resolver, gate sequence, record construction, store plumbing, or serving logic in product code unless the qualified SDK explicitly requires an extension surface.

---

## Stage 5 — Run and observe

Run the exact documented default question.

Capture:

- served/refused outcome;
- payload shape;
- content address;
- Debt and factors;
- expiry/TTL anchor;
- operator lineage;
- evidence/witnesses;
- product-specific gate result;
- performance values needed to close TBCs.

Run deliberate variations that move product semantics, not formatting.

Examples:

- alternate principal;
- alternate temporal instant;
- alternate basis;
- boundary value;
- out-of-domain value;
- stale input;
- policy-withheld subject;
- composite child withheld/absent if applicable.

---

## Stage 6 — Make every gate red once

A green test only proves the test did not fail on the current implementation.

For each declared gate:

1. identify the load-bearing implementation fact;
2. sabotage it;
3. observe the intended gate/test turn RED;
4. restore;
5. record the evidence.

The assistant may propose sabotages. A human reviews that the sabotage actually targets the claimed invariant.

---

## Stage 7 — Independent AI review

Start a separate **Validation** Cowork work unit.

Give it:

- approved Gate-1 spec;
- implementation tree;
- captured outputs;
- tests/gates;
- qualified SDK reference;
- no implementation-assistant narrative.

Use [Independent Validation Prompt](AI_VALIDATION_PROMPT.md).

The reviewer must find:

- approved term not implemented;
- code behavior absent from the spec;
- hard-coded deployment values;
- source assumptions not supported by evidence;
- stale/historical API patterns;
- undocumented refusal;
- gate with no load-bearing sabotage;
- copied historical example shape where a canonical paved-road pattern exists.

---

## GATE 2 — Evidence close-out

Gate 2 is not another product-design meeting.

It asks:

> **Did the implementation discharge the approved design, and what did the run measure?**

Close:

- build-measured TBCs;
- budgets;
- witnesses;
- hashes/addresses;
- run observations;
- gate/sabotage evidence;
- data-readiness findings;
- final operation/materialization posture.

### Deviation rule

If implementation evidence disproves a Gate-1 design term:

**STOP. Record a deviation. Return to the accountable human.**

Do not silently rewrite the approved spec to match the implementation.

---

## Stage 8 — Delivery

Follow the qualified `example_delivery.md` discipline:

- reproducible run command;
- environment variable names and read-only requirements;
- canonical example docs;
- exact output or clearly labeled excerpt;
- tests/gates;
- summary for technical product manager + engineer + SME;
- limitations / what is not proven.

---

## Current Replay boundary

Do not instruct Cowork to build a manual Replay environment from the qualified baseline.

Active D-IMPL-346/347 work is replacing that pattern. Phase 5 will add the new supported Replay workflow only after it is qualified and merged.
