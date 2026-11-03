# Worked Shape — Generate a Product on the Paved Road

This is a **structural example**, derived from the qualified canonical CP-03 pattern. It is not a new banking product and does not invent product values.

The purpose is to show a developer what Cowork should generate after Gate 1.

## Approved spec says

Assume the approved spec has already settled:

- one product class;
- one relational source;
- one Policy operator;
- entity-freshness TTL;
- per-signal half-life;
- required caller Debt tolerance;
- one governed projection;
- one product-specific predicate.

The concrete business values come from the spec/evidence packet. They are represented below as placeholders, not guesses.

## 1. ccf_config.yaml

Cowork generates the governed product declarations first.

Conceptual shape:

```yaml
semver: "1.0.0"
tenant_id: <declared-tenant>
backend: sqlite

product_class:
  schema_name: <domain.product>
  schema_version: "1.0.0"
  ttl_anchor: from_entity_freshness
  assembly_mode: algorithmic
  max_ttl_key: <declared-key>
  required_operator_keys:
    - policy.principal-subgraph
  discovery:
    domain: <domain>
    intents: [<approved-intent>]
    capabilities: [<approved-capability>]
    audiences: [<approved-audience>]
  declared_product_gate:
    gate_id: <approved-gate-id>
    gate_version: "1.0.0"

request_contract:
  ...
```

Every placeholder must come from the approved spec. Cowork does not choose it.

## 2. ccf_environment.yaml

Only names of runtime values:

```yaml
config: ccf_config.yaml

substrate:
  setting: database_path
  prefix: <deployment-prefix>
  suffix: .sqlite3

sources:
  source_name:
    dsn:
      from_env: <ENV_VAR_NAME>
      remedy: export a READ-ONLY source connection
```

No DSN, password, hostname, or credential value is committed.

## 3. acquisition.py

This module speaks the source system's language.

Good target:

```python
def acquire_source(*, subject: str, parameters: Mapping[str, object], settings: Mapping[str, str]):
    # parameterized read(s)
    # source-specific interpretation
    # return domain records
    ...
```

It should not:

- boot CCF;
- run product gates;
- write Replay records;
- serve products.

## 4. deployment.py

Map source evidence to fabric claims and assess the governed view.

```python
def acquire(context: AcquisitionContext) -> tuple[SignalEnvelope, ...]:
    rows = acquisition.acquire_source(
        subject=context.request.subject,
        parameters=context.request.parameters,
        settings=context.sources[SOURCE],
    )
    return envelopes(rows, tenant_id=context.tenant_id, at=context.instant)

def assess(context: AssessmentContext) -> DebtAssessment:
    return debt_from_view(
        context.view,
        now=context.decided_at,
        half_life=context.half_life,
        profile=context.profile,
    )

def product_gate(*, candidate, evidence=None) -> str | None:
    # Only the invariant approved in §D.7.
    ...
```

## 5. projection.py

The projection reads the governed view.

```python
class MyProjection:
    def __init__(self, *, plan_id: str, required: tuple[str, ...], subject: str):
        self._plan_id = plan_id
        self._required = required
        self._subject = subject

    @property
    def plan_id(self) -> str:
        return self._plan_id

    def required_operators(self) -> tuple[str, ...]:
        return self._required

    def invoke(self, *, view, operator_outputs, perspective, temporal_boundary):
        # Read admitted entities/relationships from view.
        payload = ...
        return ProjectionOutput(plan_id=self._plan_id, payload=payload)
```

Do not read source rows stored on a closure “because projection needs them.” If the payload depends on the fact, the fact should normally be represented in the governed view.

## 6. produce.py

The fabric side stays tiny.

```python
from ccf.products.product import OpenedProduct, open_product

def plan_factory(*, required, request):
    return projection.MyProjection(
        plan_id=deployment.plan_id(request.subject),
        required=required,
        subject=request.subject,
    )

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

If Cowork generates registry setup, ingest loops, gate execution, record construction and serve plumbing here, it has probably copied an older low-road example instead of the qualified paved road.

## 7. run.py

Presentation/client code:

1. open product;
2. create `opened.question(...)`;
3. call `opened.answer(...)`;
4. branch on refusal;
5. print business result + governed evidence.

The demonstration instant may be pinned for reproducible documentation. Production callers normally choose the actual decision instant.

## 8. tests

Translate the spec's acceptance criteria into executable assertions.

At minimum:

- default governed outcome;
- request-domain failures;
- policy-withheld subject;
- TTL/freshness boundary;
- Debt tolerance;
- product gate;
- content-address change under a semantically material request change.

Then sabotage every load-bearing gate once and observe RED.

## 9. Gate 2

Only after the implementation runs should Cowork propose values for:

- measured p95;
- witnesses;
- content addresses;
- gate observations;
- final TBCs.

Those values come from the run, not from the model.
