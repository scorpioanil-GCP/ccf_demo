# Build your first real Context Product — CP-01 Counterparty Reference Snapshot

> **Source and execution:** dated snippets below retain their original source baseline. For current SDK `v1.0.2@5f85b389`, use [setup and configuration](../../examples/CONFIGURATION.md) and the [current developer guide](../../05-reference/README.md).

This tutorial walks one Context Product from a verified demonstration estate to a governed served answer and a governed refusal.

It is intentionally **not** a toy-data tutorial. The source data comes from the same portable `ccf_dataprep` estate used by the Financial Services examples.

---

## What you will build and prove

The product answers a deceptively simple question:

> Give me the governed reference snapshot for this counterparty anchor.

The product has to do more than return a row. It must establish which identity authority resolved the anchor, shape the visible graph through Policy before downstream reads, enforce freshness/TTL, measure Context Debt, validate the product contract, record the decision, and either serve the product or refuse.

By the end of this tutorial you should be able to explain why each of these is a separate engineering responsibility.

### Pinned evidence

SDK:

`drcastillo/ccf_code@374a36007bb2fda3e968a83c2ead7d84993c0b23`

Example:

`examples/cp-01-counterparty-reference-snapshot/`

Data estate:

`drcastillo/ccf_dataprep@fcf7dddf79c7f443300d745e90bf39510ef12ab7`

Specification:

`examples/cp-01-counterparty-reference-snapshot/spec/CP-SPEC-001_Counterparty_Reference_Snapshot.md`

---

# Stage 0 — Restore and verify the data estate

An assembler begins with **data reality**, not with a Python class.

The portable estate is a full offline copy of the `ccf_dataprep` demonstration environment across the stores used by the examples. Follow the platform-specific bundle guide and complete the restore before attempting estate-dependent examples.

The bundle's intended sequence is:

```text
install required stores
        ↓
restore Fluree
        ↓
restore Postgres
        ↓
restore MongoDB
        ↓
restore SQLite
        ↓
restore Neo4j
        ↓
run verify_install.py
```

The bundle documentation makes the verifier authoritative for the installation result:

- exit `0`: every check that ran passed;
- exit `1`: at least one check failed, or zero checks ran;
- exit `2`: a store was unreachable.

Do not start the tutorial by weakening a failed verifier into "close enough."

### Current reproducibility note

The pinned Dataprep repository also records maintenance debt around fixed landmark counts in a moving append-only estate. The portable workstream has been reported operationally good to go, but this tutorial does not pretend a historical frozen count is more authoritative than the estate itself.

For release-quality reproducibility, record the bundle snapshot and verifier output used for the run.

---

# Stage 1 — Read the business problem before the implementation

CP-01 is the first rung of the Context Product ladder. It resolves a counterparty anchor through one of two identity authorities and produces a governed reference snapshot.

The teaching value is not the record count or the sample company. It is the method.

The default product demonstrates four important ideas:

1. **Entity-anchored freshness** — expiry is derived from the source's last observation of the entity rather than simply from request time.
2. **Two identity authorities** — a public LEI path and an internal client-master path can answer the same logical product request while carrying different freshness characteristics.
3. **Data quality as an explicit finding** — an address with ambiguous meaning is more dangerous than a missing address because it can look valid while being wrong.
4. **Policy before downstream graph use** — principals whose jurisdiction grant does not admit the counterparty receive a refusal rather than a subtly filtered or disclosure-bearing payload.

### Data reality

The example is deliberately mixed:

- public legal-entity reference data;
- synthetic internal client-master data;
- synthetic crosswalk data;
- synthetic principal/jurisdiction entitlements.

That proves the assembly/control behavior. It does **not** prove integration with a real institution's IAM, client master, or information-barrier implementation.

---

# Stage 2 — Read the specification before the code

The SDK-level specification is:

```text
examples/cp-01-counterparty-reference-snapshot/
  spec/
    CP-SPEC-001_Counterparty_Reference_Snapshot.md
```

This is the implementation specification for the example, not the implementation-independent Vault article.

Recall the ownership model:

| Question | Authority |
|---|---|
| Why does this product exist? | Vault / domain requirement |
| What data actually exists? | `ccf_dataprep` |
| What does this implementation do? | `ccf_code` |

For a new Context Product, the SDK-level specification is Gate 1: approve the decision frame, contract, source bindings, operator intent, temporal policy and acceptance criteria **before implementation**.

During implementation, measurable values such as observed witnesses, replay results and final performance evidence close at Gate 2.

### What to look for in CP-SPEC-001

Do not try to memorize a 90K specification. Read it with questions:

- What decision is being supported?
- Who consumes the product?
- What is the scope boundary?
- What does the caller supply?
- Which data elements are public vs synthetic?
- Which store/schema/table supplies each element?
- What freshness model applies to each signal class?
- Which steps assemble the product?
- Which witnesses prove those steps ran?
- Which outcomes are served vs refused?
- What is explicitly **not** proven?

That is the specification-as-engineering-contract mindset.

---

# Stage 3 — Inspect the Control Plane before the Python

The first implementation file to inspect is not `run.py`. It is:

```text
examples/cp-01-counterparty-reference-snapshot/ccf_config.yaml
```

The top of that document makes the architectural boundary explicit:

```yaml
semver: "1.0.0"
tenant_id: cp-01-demo

# Fabric-owned Context Graph substrate for this run.
backend: sqlite

product_class:
  schema_name: reference.counterparty
  schema_version: "1.0.0"
  ttl_anchor: from_entity_freshness
  assembly_mode: algorithmic
  max_ttl_key: cp-01/product/counterparty-reference/max-ttl
  required_operator_keys:
    - policy.principal-subgraph
```

Two stores are involved for different reasons:

- **PostgreSQL** is part of the read-only enterprise/source estate for this example.
- **SQLite** is the fabric's own temporary Context Graph substrate for the run.

Do not confuse "where source data lives" with "where CCF holds its own assembled graph state."

## Policy is data/configuration, not a branch in application code

The product declares the operator key:

```yaml
required_operator_keys:
  - policy.principal-subgraph
```

The configuration then declares the operator's parameter shape. At runtime the deployment supplies the calling principal's permitted jurisdictions from the estate.

The important pattern is:

```text
Control Plane declaration
        ↓
operator registry
        ↓
Policy shapes the graph before downstream interpretation
```

not:

```text
query everything
        ↓
if principal == ...
        ↓
remove some rows
```

## The request contract is also declared

The configuration declares caller-supplied parameters such as:

```yaml
request_contract:
  schema_name: reference.counterparty
  schema_version: "1.0.0"
  arguments:
    properties:
      debt_tolerance:
        type: number
      include_lapsed:
        type: boolean
      as_of:
        type: string
  required:
    - debt_tolerance
  unsupported_arguments:
    as_of: not_supported_at_tier
```

`as_of` is a useful teaching detail: it is visible/discoverable but explicitly unsupported at this tier. A parameter that silently appears to work is more dangerous than one that fails loudly.

---

# Stage 4 — Bind the real source estate

The example keeps credentials and hosts out of source-controlled Control Plane artifacts.

`backends.yaml` declares the **environment-variable name**. The deployment environment supplies the actual DSN.

From the `ccf_code` repository root:

```bash
make venv
```

Then export a read-only connection to the restored CP-01 PostgreSQL estate:

```bash
export CCF_CP_01_POSTGRES_DSN='postgresql://<read-only-role>@<host>/<db>'
```

The role requires `SELECT`, not write access.

This separation matters:

```text
specification says where the implementation data lives
configuration says what backend kind / variable name is required
environment supplies deployment-specific connection material
```

No credential should become part of a content-addressed Control Plane artifact or tutorial source file.

---

# Stage 5 — Read the three code seams

A first-time assembler does not need to understand every line. Read the code in this order.

## 5.1 Caller: `run.py`

The caller owns request values. It does not own the product's Control Plane rules.

The essential path is:

```python
anchor = args.anchor or deployment.demonstration_anchor()

parameters = {
    deployment.PARAM_DEBT_TOLERANCE: Decimal(...),
    deployment.PARAM_INCLUDE_LAPSED: (...),
}

asked = deployment.request(parameters=parameters)

product = assembler.CounterpartyAssembler(
    config=deployment.CONFIG,
    root=root,
    connection=deployment.connection(root=root),
    read=deployment.read,
    plan_class=deployment.plan_class(),
    observer=captured.append,
)

governed = product.assemble(
    request=asked,
    perspective=deployment.perspective(),
    tenant_id=deployment.tenant_id(),
)
```

The key distinction is visible: **the caller asks; it does not declare how the answer is assembled.**

The caller also branches on governed outcomes as data:

```python
if isinstance(outcome, produce.AnchorUnresolvable):
    ...

if not isinstance(outcome, produce.Assembled):
    print(f"refused: {outcome.reason} — {outcome.key}")
    return 1
```

A refusal is not automatically an infrastructure exception.

## 5.2 Assembler seam: `assembler.py`

The domain assembler structurally conforms to the SDK assembler protocol and delegates the actual end-to-end fabric work to the governed spine.

The central handoff is intentionally small:

```python
assembled = produce.assemble_and_serve(
    config=self.config,
    connection=self.connection,
    read=self.read,
    plan_class=self.plan_class,
    request=request,
    root=self.root,
    unsupported=self.unsupported,
)
```

This seam owns identity/perspective checks and maps product-specific availability behavior. It does not duplicate the fabric mechanisms below it.

## 5.3 Fabric spine: `produce.py`

This is where the L1–L6 responsibilities become executable.

The spine is deliberately ordered.

### Boot

```python
booted = load_config_and_boot(
    config,
    registry=registry,
    connection=connection,
)
```

### Resolve the scenario and refuse an unsupported question before graph work

```python
scenario = read(booted, request)
if scenario is None:
    return AnchorUnresolvable(anchor=request.subject)

violation = refuse_request(
    request=scenario.request,
    declared=scenario.request_contract,
)
if violation is not None:
    return violation
```

### L1 → L2 → L3 ingest through the sole write handle

```python
for envelope in scenario.envelopes:
    booted.handle.worker.ingest(envelope)
```

The source system is read-only from this path. The writer writes CCF-owned graph state.

### L3 view and L4 operators

```python
view = booted.handle.reader.as_of(
    tenant_id=booted.tenant_id,
    at=scenario.temporal_boundary,
)

operators = build_operator_registry(
    parameters=scenario.operator_parameters,
    view=view,
    pins=booted.pins,
    policy_bundle_key=scenario.policy_bundle_key,
)
```

### L5 projection

```python
execution = ProjectionEngine(
    reader=booted.handle.reader,
    registry=operators,
).execute(
    plan=plan,
    perspective=scenario.perspective,
    tenant_id=booted.tenant_id,
    temporal_boundary=scenario.temporal_boundary,
)
```

### L6 candidate with measured Debt

```python
candidate = ContextProductContract(
    ...,
    lineage=ProductLineage(
        operators_invoked=frozenset(declared.required_operator_keys),
        policy_bundle_versions=frozenset({policy_version}),
        graph_snapshot_at=scenario.temporal_boundary,
    ),
    payload=execution.projection.payload,
    debt=scenario.debt(execution.view),
)
```

The Debt value is measured against what was actually assembled. It is not decorative metadata supplied by the caller.

### Validation gates

```python
match run_gates(
    candidate,
    engine_resolved=execution.operators_invoked,
    now=scenario.now,
    registry=registry,
    product_class=product_class,
):
    case ServableProduct() as gated:
        pass
    case refusal:
        raise RuntimeError(
            f"the three validation gates refused this product: {refusal}"
        )
```

The `ServableProduct` type is the evidence that the product made it through the serving gates.

### Replay before delivery

```python
record = build_replay_record(
    execution=execution,
    product=gated.product,
    perspective=scenario.perspective,
    policy_bindings=(
        PolicyBinding(
            key=scenario.policy_bundle_key,
            version=policy_version,
        ),
    ),
    assembly_mode=declared.assembly_mode,
    recorded_at=scenario.now,
    request=scenario.request,
)
```

### Serve only after replay persistence

```python
served = serve(
    product=gated,
    record=record,
    replay_writer=ReplayWriter(...),
    query_pin_writer=QueryPinWriter(...),
    executed_queries=execution.executed_queries,
)
```

The order is part of the control design. Replay is not an after-the-fact log appended if convenient.

---

# Stage 6 — Run the default served path

From the `ccf_code` repository root, with the venv created and the read-only DSN exported:

```bash
make example-cp-01
```

For output without Make's command echo:

```bash
make -s example-cp-01
```

Or call the example directly:

```bash
.venv/bin/python examples/cp-01-counterparty-reference-snapshot/run.py
```

The default demonstration question is intentionally pinned rather than "now" because the example estate is a snapshot. Running against today's clock would correctly make the historical source observations stale.

## What to inspect in the output

Do not stop when you see the JSON payload. The example deliberately prints the warrant around the answer:

```text
asked as of
expires at / ttl_anchor
context debt D_c / routing signal
identity authority
freshness ceiling / signal class
principal / permitted jurisdiction count
operators invoked
content address
replay record
assembled by <assembler-id>@<version>
```

A plain relational query can return identity data. It does not automatically establish that full decision-time contract.

---

# Stage 7 — Run a governed Policy refusal

Now ask the same product as a principal whose jurisdiction grant does not admit the demonstration counterparty:

```bash
make example-cp-01 PRINCIPAL=PRIN-KYC-004
```

A non-zero exit is expected.

The important behavior is not merely "access denied."

The product makes an entity that is unavailable to the principal indistinguishable at the product boundary from an unavailable counterparty. It does not reveal:

- that the entity exists in this estate;
- how many records were removed;
- which entitlement caused the removal;
- what hidden values would otherwise have been present.

That is a much stronger control story than filtering fields after assembly and adding a message that says something was hidden.

### What this proves

It proves the **example's policy-shaping behavior** with synthetic entitlement data.

It does not prove enterprise IAM integration or a complete production information-barrier implementation.

---

# Stage 8 — Read the answer's evidence

On the served path, focus on five pieces of evidence.

## 8.1 Expiry and temporal boundary

The product declares an entity-freshness anchor. The validity window is therefore tied to what the relevant authority last observed about that entity.

## 8.2 Context Debt

`D_c` is carried with the product and is part of the product's content-addressed state.

Treat it as an assembly quality/control result, not a confidence score invented by a language model.

## 8.3 Content address

The content address identifies the exact served product state. It makes equality/difference of products testable rather than rhetorical.

## 8.4 Lineage / operator evidence

The candidate declares which operators should have produced it; the engine reports what actually ran; validation compares them.

That separation matters. If both sides of the comparison were derived from the same runtime list, the check would prove nothing.

## 8.5 Decision Replay

The replay record binds the served decision to its request, temporal boundary, perspective, policy bindings, execution state and query pins before delivery.

Replay means reconstructing the decision substrate. It is not merely retaining a model transcript.

---

# Stage 9 — Run the correctness test

The example command proves the path executes and lets you inspect its output.

Correctness assertions live separately in the test suite:

```bash
.venv/bin/python -m pytest tests/examples/test_cp_01_output.py
```

The tests use a seeded container rather than depending on the live/restored demonstration estate. That separation is deliberate:

- example run: demonstrates behavior against the estate you supplied;
- test run: asserts invariants against deterministic fixtures.

A green demonstration command by itself is not the full correctness argument.

---

# Stage 10 — Change one axis at a time

Once the default path is understood, use the existing example switches to see which dimensions change behavior.

### Change the principal

```bash
make example-cp-01 PRINCIPAL=PRIN-KYC-004
```

Expected: governed Policy refusal.

### Change the identity authority

```bash
make example-cp-01 ANCHOR=CLI-000101
```

This currently surfaces a known TTL/freshness declaration finding and is expected to refuse at the TTL gate. The tutorial preserves the finding; it does not paper over it.

### Ask for a lapsed registration

```bash
make example-cp-01 ANCHOR=549300TRW1LZMDJZAQ78
make example-cp-01 ANCHOR=549300TRW1LZMDJZAQ78 INCLUDE_LAPSED=1
```

Expected: the request parameter changes whether the lapsed entity is included.

### Exercise an explicitly unsupported parameter

```bash
make example-cp-01 AS_OF=2026-01-01T00:00:00+00:00
```

Expected: `not-supported-at-tier`, returned as a governed request verdict rather than silently pretending the parameter was honored.

---

# What is code, what is configuration, what is data

After working through the example, classify the pieces:

| Artifact | Responsibility |
|---|---|
| Vault article | implementation-independent business requirement |
| CP-SPEC-001 | implementation specification |
| Dataprep estate | what data actually exists |
| `ccf_config.yaml` | versioned Control Plane declaration |
| `backends.yaml` | backend recipe / environment-variable names |
| environment DSN | deployment-specific connection material |
| `artifacts/question.yaml` | demonstration request/scenario |
| `artifacts/ttl.yaml` | deployment-authored TTL value/measurement |
| `artifacts/assembly-recipe.yaml` | spec step table expressed as testable data |
| `deployment.py` | interprets product/domain declarations |
| `run.py` | caller/demo surface |
| `assembler.py` | product-specific assembler seam |
| `produce.py` | generic governed assembly/serve spine for the example |
| SDK packages | fabric mechanism |

If a future implementation puts a counterparty ID, jurisdiction list, credential, business threshold or other deployment value into generic SDK mechanism, stop and ask why.

---

# Known limitations and findings

A good tutorial teaches what the example does **not** prove.

## Data is demonstration data

Public legal-entity data is combined with synthetic internal data and synthetic entitlements. Do not relabel those synthetic inputs as real bank data.

## Portable-estate reproducibility has a maintenance note

The pinned Dataprep repository records stale/frozen landmark-count debt on a moving estate. Record the exact bundle/verifier outcome used for a published tutorial run.

## Snapshot freshness is real

The example pins the demonstration instant because the estate is a snapshot. Asking "now" and receiving a freshness/TTL refusal is the system behaving correctly, not a reason to disable temporal controls.

## CP-01 contains a documented TTL composition finding

The no-LEI/internal-client path currently exposes a mismatch between the product's single TTL declaration and the longer internal-client freshness ceiling. The gate refusal is evidence of that design issue. Do not rewrite the tutorial to make the failing case look successful.

## No enterprise IAM claim

Synthetic entitlement fixtures demonstrate policy behavior. They do not establish production IAM or MNPI-wall assurance.

## No model is required

This is Assembly Mode 1. It proves algorithmic Context Product assembly, not Mode 2/3 model-risk controls.

## No composite Context Product claim

This tutorial assembles one Context Product. Current SDK main also includes [CP-14 composite products](../../05-reference/02-context-product-producer/examples/CP14_CREDIT_MEMO_CONTEXT.md), outside this tutorial's scope. L4 operator composition shown here is not product-level composition.

---

# What you should now understand

If this tutorial worked as intended, you should be able to answer all of these without reverse-engineering the repository:

1. What decision does CP-01 support?
2. Why is the specification read before implementation code?
3. Which data is source-estate data and which state belongs to CCF itself?
4. Why is L2 the only graph writer?
5. Why does Policy run before downstream interpretation?
6. What is the difference between a caller request and Control Plane configuration?
7. Why is a governed refusal different from an outage?
8. Where is Context Debt measured?
9. What do the validation gates compare?
10. Why is replay written before delivery?
11. What does the content address identify?
12. Which claims are demonstrated here and which remain outside the evidence?

That is the foundation the remaining CP-02 through CP-13 examples build on.
