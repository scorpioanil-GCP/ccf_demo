# How to Read a Shipped Context Product Example

Every CP-00→CP-24 example already has an approved implementation specification.

Your job as a learner is **not to recreate it**.

Your job is to understand how the specification becomes an executable Context Product.

## Step 1 — open the completed spec

Each example guide gives you the exact `CP-SPEC-...` path in `ccf_code`.

Read the spec before the Python.

## Step 2 — read the spec in the same order every time

### §A — Decision frame

Ask:

- What decision is being supported?
- Who consumes it?
- What conventional/data-only answer would be wrong?
- What is explicitly out of scope?

### §B — Contract

Ask:

- What is the product class?
- What can the caller ask?
- What is the TTL anchor?
- What policy/perspective applies?
- What is the assembly mode?

### §C — Data catalog

Ask:

- Which source systems actually supply each element?
- Which store/schema/table is used?
- What are the identity/correlation keys?
- What data traps or incomplete coverage are explicitly admitted?

### §D — Assembly recipe

Ask:

- Which operators run?
- What does acquisition produce?
- What does projection emit?
- Which gates can refuse the candidate?

### §E — Freshness, half-life, Debt, materialization

Ask:

- Which signal classes decay?
- At what declared calibration?
- How is Context Debt measured?
- Is the product assembled on demand or materialized?

### §F — Source readiness

Ask:

- What data is real, synthetic, engineered, derived, missing, or deliberately limited?
- What must exist in the environment for this example to run?

### §G — Operate and govern

Ask:

- What tests and operational evidence close the specification?
- Which values were measured at Gate 2?

## Step 3 — map spec sections to files

The modern paved-road shape is:

| Spec concern | Typical implementation home |
|---|---|
| product class / TTL / discovery | `ccf_config.yaml → product_class` |
| request surface | `ccf_config.yaml → request_contract` |
| operator declaration/parameters | `ccf_config.yaml → operators` |
| source location variable names | `ccf_environment.yaml` |
| source reads / source-domain logic | `acquisition.py` |
| source facts → SignalEnvelope | `deployment.py` |
| Context Debt assessment | `deployment.py::assess` |
| product-specific invariant | `deployment.py` gate callable |
| emitted payload | `projection.py` |
| product wiring | thin `produce.py` using `open_product` |
| multi-principal access, where used | `ccf_config.yaml → product_entitlement` |
| declared agent skill grants, where used | `ccf_config.yaml → grants` |
| dated development demonstration, where used | `ccf_config.yaml → demonstration_serve_instant` + temporal boundary |
| demonstration caller | `run.py` |
| spec evidence / gates | `tests/examples/`, `artifacts/gates.yaml`, `FINDINGS.md` |

Older examples may expose more plumbing. When a canonical successor exists, the canonical tree is the copy target.

## Step 4 — run before editing

Run the documented default case from the **current SDK tree** first. Historical companion text explains lineage; the current example README/command is the execution authority.

Then change **one governed dimension**:

- subject;
- decision instant;
- principal/perspective;
- request parameter;
- corpus/scope;
- tolerance;
- traversal depth;
- scenario.

Observe which of these move:

- payload;
- Context Debt;
- expiry;
- content address;
- refusal outcome;
- lineage/evidence.

## Step 5 — validate

The example guide gives the tests that prove the documented behavior.

A successful demo is not the same as a proved invariant.

## When you are ready to build something new

Only after you understand this spec→code relationship should you move to [Create Your Own Context Product](../04-create-your-own/README.md).
