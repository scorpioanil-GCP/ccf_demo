# Reusable Cowork Prompt — Draft a Context Product Specification

Use this prompt after assembling the business and data evidence packet.

---

## Prompt

You are helping draft an **SDK implementation specification for a CCF Context Product**.

### Non-negotiable rules

1. Use the Context Product Specification Standard v0.3.
2. Use CP-SPEC-000 only as the document-shape/template precedent.
3. Do not write implementation code.
4. Do not invent a missing business, data, policy, calibration, or SDK term.
5. When evidence is missing, write `[TBC — <owner>]` and add it to the readiness/TBC register.
6. Keep source authority explicit:
   - SME/business evidence owns why, decision, scope and counterfactual;
   - data-engineering evidence owns what data exists and measured readiness;
   - qualified SDK evidence owns what the implementation surface can do.
7. This is the **SDK implementation specification**, so name the concrete store/schema/table or equivalent source binding needed to build it.
8. Never put host, port, credential, secret or deployment instance values in the spec.
9. Make every intended validation claim falsifiable.
10. Mark values that can only be known after implementation as `[TBC — this build]`.
11. DR-01 and DR-02 on the qualified SDK baseline are valid precedent for Decision Replay and Assembly Mode 2. Do not use unmerged branches as precedent.
12. Target released SDK `v1.0.2` — `5f85b389efe9e4b1de62e84a5af62ca4b2e12178`.

### Inputs

I will provide:

- business/SME product definition;
- data-estate/source evidence;
- relevant ontology/semantic bindings;
- Standard v0.3;
- qualified SDK reference;
- optionally one or more canonical examples.

### Your process

First produce an **evidence ownership table**:

| Term needed | Owner | Evidence supplied | Status |
|---|---|---|---|

Do not draft the spec until every required term is either supported by evidence or explicitly marked TBC.

Then draft the specification in this order:

- §0 / front matter / data-reality banner
- §A Decision frame
- §B Contract
- §C Data catalog
- §D Assembly recipe
- §E Volatility & materialization
- §F Source binding & readiness
- §G Operate & govern

### Required checks before returning the draft

Check and report separately:

- four-question Context Product admission test;
- scope conflicts;
- source fields with no authoritative writer;
- missing/ambiguous correlation keys;
- missing ontology bindings;
- freshness/TTL confusion;
- request parameters that move no CCF dimension;
- product values accidentally placed in deployment environment;
- deployment values accidentally placed in the spec;
- intended gates that cannot be deliberately made RED;
- Mode 2/3 model-risk requirements if an LLM is in the product trust path;
- all TBCs with named owner.

### Output

Return:

1. the complete Gate-1-ready specification draft;
2. a short **Open TBCs / Decisions Needed** table;
3. a **Gate-1 Review Checklist**.

Then STOP. Do not generate code until I explicitly state Gate 1 is approved.
