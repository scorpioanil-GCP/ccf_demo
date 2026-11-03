# SK-01 — Declare and govern agent skills — Analysis

**SDK source baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178` — reviewed 17 October 2026.

**Audience:** banking SME and Information Architect. **Companion:** [implementation walkthrough](SK01_DECLARE_AND_GOVERN_AGENT_SKILLS.md).

Unlike the CP examples, SK-01 does **not** ship a `spec/` folder or a completed CP-SPEC. Its authoritative target is the shipped README, configuration, question mapping, variant and findings. The journey below maps those actual declarations into [Specification Standard v0.3](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/public/reference/specifications/Context_Product_Specification_Standard_v0-3.md), sections A–G. It is an authoring analysis, not a claim that an unprovided final specification exists or has been approved.

## A — Define the decision before choosing an agent tool

A credit officer needs the bank's collateral and set-off coverage for one facility, within one obligor's scope. The value of the example is controlled delegation: the officer must know which agent asked, what authority it held, and whether an attempt to expand that authority was refused.

The SME frames the decision as “may this analyst obtain the registered collateral product's answer for this facility?” It does not authorize amending the collateral ledger, creating a new collateral valuation, or executing a credit decision. The Information Architect identifies the answering product and the host product separately. `credit-risk.collateral-coverage` owns the collateral determination. `credit-risk.facility-collateral-brief` hosts the composing agent and combines a small obligor identity leg with the admitted answer.

The host's own leg exists because the supported SDK path requires it. It should not be mistaken for an additional banking requirement. The source findings track standalone grant-holding agents as unavailable.

## B — Make the contract and scope explicit

| Specification question | Shipped declaration | SME / architect interpretation |
| --- | --- | --- |
| Which answer is requested? | Host class `credit-risk.facility-collateral-brief`, version `1.0.0` | A scoped brief, not a replacement collateral calculation |
| Which assembly mode? | `swarm_assembled` | Governed composition of a child product; it does not imply an LLM call |
| Who is the subject? | Parent obligor LEI; required string argument `facility_id` | Obligor and facility are separate identities |
| Which child is indispensable? | `credit-risk.collateral-coverage`, required, compatible from `1.0.0` | A refused child cannot be silently dropped or replaced by raw data |
| Which caller perspective? | `PRIN-CRO-001`, role `credit-officer` | Example perspective, not employee-specific authorization proof |
| How is scope passed? | Child subject/facility = requested facility; `borrower_scope` = parent LEI | The mapping constrains the requested answer; caller-chosen scope is not a substitute for employee entitlement |
| How is age bounded? | Decision-scoped parent, 43,200-second TTL; child expiry floors the result | A fresh host cannot make expired collateral usable |

The Information Architect records the exact request mapping: parent `collateral-brief` / `decision-scoped` becomes child `lgd-assessment` / `as-filed`, with the same `asked_at`. The demonstration question names BGC Group LEI `2549001IGRCG4F0RLD36`, facility `FAC-5B8418`, at `2026-09-07T12:00:00+00:00`.

Before production approval, the bank still has to supply classification/residency, ownership, employee entitlement and production calibration decisions. The example is not evidence that those Standard fields have been resolved.

## C — Separate business facts from authorization artifacts

The host reads `legal_entity` identity information from Postgres into obligor state: LEI, legal name and jurisdiction. The child owns the collateral/set-off evidence and calculation. Its answer enters through governed child admission, not a shared raw database read by the composing agent.

The capability decomposition has five declaration groups. The SME chooses the policy envelope; the architect makes producer and class identity unambiguous:

| Group | Exact choice in SK-01 | Why the choice matters |
| --- | --- | --- |
| Policy | Permit only `collateral-coverage.read`; no grant approval required | Defines the allowed envelope for this demonstration |
| Producer | `collateral-coverage-producer`, identity `cp-06-canonical-collateral-and-setoff-coverage-egress`, tenant `cp-06-canonical-demo` | A matching class name alone does not establish a trusted producer |
| Skill | `collateral-ask` version `1.0.0`, produces `credit-risk.collateral-coverage` | Names the delegated capability independently of a prompt |
| Agent | `collateral-analyst` version `1.0.0`, archetype `context_assembly` | Makes the composing identity versioned data |
| Grant | `grants: [collateral-ask]` | Requests the capability through the ledger when opening |

`required_context_products: []` belongs to the skill's requirement envelope. It does not cancel the host's required child. Likewise, a `.read` scope suffix expresses a policy label; the database read-only role is a separate enforcement control.

## D — Turn the decision into the assembly and evidence journey

The SDK opens the declarations, registers the chain and requests the grant. Tier 1 compares the skill requirements with the policy/context contract. Tier 2 applies the approval rule; SK-01's rule requires no approval. An effective grant permits child acquisition through the SDK-derived binding. The developer's contribution is the parent-to-child question mapping and the host's acquisition/projection seams.

```mermaid
sequenceDiagram
    participant O as Product opening
    participant G as Grant ledger
    participant P as Parent resolver
    participant C as Collateral producer
    participant R as Decision evidence
    O->>G: Request declared collateral-ask grant
    alt Scope exceeds policy
        G-->>O: Refuse and audit; opening stops
    else Grant effective
        G-->>O: Bound skill authority
        P->>C: Facility question with borrower scope
        C-->>P: Governed answer or refusal
        P->>P: Verify and admit required child
        P->>R: Record agent, skill-set identity and outcome
    end
```

For acceptance, distinguish what is recorded from what can later be reconstructed. Dimension 4 identifies the agent by definition hash, versioned URI and archetypes, and identifies the granted set by hash, even on refusal. Dimension 5 names the producing skill/version and grant hash only when the child is admitted. A refused child row contains refusal evidence; a temporal refusal can precede all child rows.

The Standard's replay section must state the retained-evidence dependency. Current SDK composite replay reconstructs using retained child contracts and graphs without asking producers again, but SK-01 has no replay acceptance gate of its own. The record alone cannot enumerate the skill-set or re-evaluate its requirements; the necessary catalog/grant artifacts live in the example's in-memory Control Plane. A production specification requiring durable authority reconstruction must leave that acceptance item unresolved until it is implemented and tested.

## E — Specify volatility and debt without inventing production policy

The shipped identity half-life is 31,536,000 seconds with `gleif-record-refresh` decay and `lei-record-update` supersession. Risk sensitivity is `1.0`, forced-LLM threshold `0.30`, fail-closed threshold `0.60`. The maximum past interval is 3,600 seconds with no permitted clock skew. The declared demonstration serve instant is `2026-09-07T12:05:00+00:00`.

These values make the dated teaching estate observable. The SME must justify production thresholds against the actual collateral policy and evidence refresh process; neither a one-year identity half-life nor a twelve-hour host TTL extends the child's validity. The presence of a forced-LLM threshold does not mean this example invokes a model.

## F — Bind the sources and expose readiness gaps

The deployment references endpoint and credential **variable names**, never their values, for the collateral producer. Four variables are required for SK-01: complete Postgres DSN, schema `ccf_v2`, producer MCP URL, and producer token. The producer has its own source settings and must be started separately. Use Fluree **4.2.4** for its graph source and a read-only Postgres role. Host-side SQLite is the fabric backend, not the banking estate.

Readiness is conditional on those dependencies. Missing settings are a setup failure; a governed refusal is a valid recorded result; an unexpected unbound exception is a runtime failure. Keep those three outcomes distinct in the specification and the review evidence.

## G — Define reviewable acceptance criteria

| Check | Expected result at the source baseline | Evidence / qualification |
| --- | --- | --- |
| Open declared configuration | Requested then effective grant | Opening audit in memory |
| Add `collateral-ledger.write` and advance skill artifact to `1.1.0` | `DeclaredGrantRefused`, `tier-1-policy-compatibility` | Shipped over-reach variant; original policy unchanged |
| Ask the demonstration facility | Governed answer with composing identity; admitted child names skill/grant | SDK README reports estate measurement; not rerun here |
| Ask `FAC-D3D1A4` for LEI `B3BS7ACMDUWISF18KY76` | Parent `composite-child-refusal`; child `ttl-refusal` / `ttl-bounds` | Expired collateral remains unusable |
| Ask at `2026-09-07T10:00:00+00:00` | `asked-at-outside-temporal-bound`, still naming agent/set | Early refusal need not acquire a child |
| Inspect harness tools | Empty lists | Correct for `mcp_product`; no LLM is started |
| Recover every granted member from only the record | Not supported | Set hash and in-memory artifacts do not satisfy durable enumeration |
| Change grants while running / host agent independently | Not demonstrated through an authorized example entry point | Parked SDK gaps, not completed acceptance items |
| Replay SK-01 after restart | Not measured by this example | SDK has composite replay tests; add a scenario-specific gate before claiming acceptance |

The SME can approve the capability's banking scope; the architect can check exact class, subject, producer, policy and artifact identities. Operations and audit must resolve the retention and authorization gaps before treating the demonstration as a production control.

## Source trail

- [README and reported estate outcomes](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/sk-01-declare-and-govern-agent-skills/README.md)
- [Actual final configuration](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/sk-01-declare-and-govern-agent-skills/ccf_config.yaml) and [over-reach configuration](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/sk-01-declare-and-govern-agent-skills/variants/over-reach/ccf_config.yaml)
- [Question](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/sk-01-declare-and-govern-agent-skills/artifacts/question.yaml), [mapping](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/sk-01-declare-and-govern-agent-skills/deployment.py), [acquisition](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/sk-01-declare-and-govern-agent-skills/acquisition.py)
- [Findings and unavailable capabilities](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/sk-01-declare-and-govern-agent-skills/FINDINGS.md)
- [Standard v0.3](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/public/reference/specifications/Context_Product_Specification_Standard_v0-3.md), used as the A–G authoring structure, not as evidence of a missing final spec
- [Composite replay change](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/docs/surface-changes/389-01-composite-replay-from-the-record.md)
