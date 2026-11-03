# Reusable Cowork Prompt — Generate a Context Product from an Approved Spec

Use this only after Gate 1 is explicitly approved.

---

## Prompt

You are implementing an **approved CCF Context Product specification** against qualified SDK:

`drcastillo/ccf_code@v1.0.1` — `a4cf2fb74af4964dcfee29d210d17d94b909d78d`

### Preconditions

- Gate 1 is approved.
- The approved spec is the design authority.
- Data/source access evidence is supplied.
- You may inspect qualified canonical examples for implementation pattern.
- Do not use active `dr*` Decision Replay work or unqualified branches.

### Primary rule

**Generate code from the approved spec. Do not redesign the product while implementing it.**

If the spec is impossible, ambiguous, contradicted by the data, or unsupported by the qualified SDK:

1. stop the affected path;
2. report a deviation/finding;
3. identify the exact spec term and evidence;
4. do not silently “fix” the spec in code.

### Choose the smallest canonical precedent

Default structural precedent:

`examples/cp-03-canonical-obligor-financial-spread`

Use another canonical example only when the approved spec needs its primitive:

- canonical CP-04 — graph/multi-store;
- canonical CP-06 — typed relationship;
- canonical CP-13 — document evidence;
- CP-14 — composite product;
- CP-15 — HITL;
- CP-17 — information barrier;
- CP-18 — perspective/ranking;
- CP-20 — peering/federation;
- CP-22 — agent-internal assembly;
- CP-23 — population product;
- CP-24 — scenario product.

### Generate in this order

1. `ccf_config.yaml`
2. `ccf_environment.yaml`
3. `acquisition.py`
4. `projection.py`
5. `deployment.py`
6. thin paved-road `produce.py`
7. `run.py`
8. server/door only if required
9. artifacts/tests required by the spec and delivery standard
10. README / delivery documentation

### Implementation boundaries

#### Configuration
Put governed product/configuration terms in `ccf_config.yaml`.

#### Environment
Put **names of runtime values** in `ccf_environment.yaml`; never raw secrets/DSNs/hosts.

#### Acquisition
May access domain stores. Should not import product gate/replay/serve machinery.

#### Projection
Must shape from the governed `GraphView`; do not reach around the view to source rows held on the side.

#### Deployment
Own product-specific acquire/assess/gate callables and vocabulary.

#### Produce
Use the paved road:

`open_product(...)` + `opened.answer(...)`.

Do not hand-assemble registry → boot → ingest → gates → record → serve when the qualified product facade owns that path.

### Spec-to-code traceability

For every generated file, prepend a short mapping:

- spec sections discharged;
- authoritative input used;
- TBCs it does not resolve.

Do not copy business constants from a canonical example into the new product.

### Validation to generate

Generate tests that prove:

- request contract rejects undeclared/out-of-domain values;
- policy/suppression behavior;
- temporal boundaries;
- every product-specific declared gate;
- Debt/fulfillment behavior;
- content address changes when a semantically relevant request changes;
- canonical/historical paths are not mixed;
- no deployment secret/value is committed;
- each gate can be sabotaged RED.

### Output after generation

Return:

1. files created/changed;
2. spec-section → file mapping;
3. commands to run;
4. expected served/refused cases;
5. unresolved findings/deviations;
6. exact items still `[TBC — this build]`.

Do not declare Gate 2 complete.
