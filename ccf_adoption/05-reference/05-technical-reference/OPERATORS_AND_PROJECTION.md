# Operators and Projection

**Packages:** `ccf.operators`, `ccf.projection`  
**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

## Operator model

An operator is a pure, read-only transformation over graph state.

Core types:

- `Operator`
- `OperatorParameters`
- `OperatorOutput`
- `OperatorProvenance`
- `OperatorRegistry`
- `OperatorPlan`
- `PlannedStep`

Canonical categories/operators include:

- `PolicyFilter`
- `SimilaritySelect`
- `TemporalAsOf`
- traversal operators such as descendants/neighborhood

## Ordering

Operator planning is not an arbitrary list.

The established dependency order is:

```
Policy → Similarity → Temporal → Traversal
```

The deeper composition notation is read right-to-left:

```
ContextProduct = Π ∘ Traversal ∘ Temporal ∘ Policy ∘ Similarity
```

The practical rule is to let the planner establish the supported ordering rather than hand-ordering operators in product code.

## Operator parameters

Schemas and values are distinct.

Parameter contracts describe what an operator accepts. Deployment values come from governed configuration/effective request state.

Do not place business-policy defaults into SDK code.

## Registry

`OperatorRegistry` is the set of operator implementations a fabric may execute.

Deployment helper:

`ccf.deployment.build_operator_registry(...)`

The registry can be view-aware because some mechanisms such as similarity require a corpus resolved at a declared boundary.

## Projection

Key types:

- `Perspective`
- `ProjectionOutput`
- `ProjectionPlan`
- `ProjectionEngine`

The operator plan settles the admitted/computed context. Projection settles what that context means for the requested product/perspective.

### Structural protocol

A projection need not inherit a concrete base. It must satisfy the structural contract.

Canonical pattern:

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
        ...
        return ProjectionOutput(plan_id=self._plan_id, payload=payload)
```

## Do not author a second operator set

On the paved road the plan factory receives `required` from the SDK/product declaration and passes it to the projection.

Preferred shape:

```python
def plan_factory(*, required: tuple[str, ...], request: ProductRequest) -> ProjectionPlan:
    return MyProjection(
        plan_id=...,
        required=required,
        subject=request.subject,
    )
```

The deployment should not independently restate the required operator keys in Python.

## Acquisition during projection

Advanced projection surfaces include:

- `ContentAcquirer`
- `ContentAcquiringPlan`
- `ContentRequest`
- `AcquiredContent`

Use this when the approved design requires decision-time content acquisition through the declared seam. Do not use it to bypass L1/L2 policy or graph-state responsibilities.

## Segmentation / pushdown

`ccf.projection.segmentation` can split pushable work from in-process work.

This is a platform/performance concern. Start with the correct product semantics; optimize only where the spec and evidence support pushdown.

## Perspective vs policy

These are related and not interchangeable.

- Policy determines what context may exist/be admitted for the principal/request.
- Projection shapes/interprets admitted context for the decision/perspective.

Do not use presentation filtering as a substitute for formative policy.

## Best examples

- policy at Tier 1: CP-01
- attribute-level temporal spread: canonical CP-03
- graph traversal: canonical CP-04
- perspective as product dimension: CP-18
- Policy-before-Similarity under restricted context: CP-17 / CP-19

