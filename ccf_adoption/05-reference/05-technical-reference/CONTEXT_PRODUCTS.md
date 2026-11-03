# Context Products

**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

A Context Product is the governed vessel served to a consumer. The payload is only one member; the contract also carries decision fitness, lineage, debt, temporal validity, evidence and governed refusal semantics.

## Product request

A product is **called**, not configured per request.

Core axes remain:

- schema name/version;
- subject;
- asked-at;
- intent;
- freshness;
- parameters;
- policy overrides.

`ProductRequestContract` includes subject and parameter-domain controls. `ArgumentDomain` supports numeric bounds, members and patterns, and `refuse_floor(...)` applies the current SDK floor before downstream domain logic.

## Trusted time

Current main distinguishes the caller's decision question from the fabric's trusted serve instant.

A pinned temporal-boundary policy limits accepted question/decision instants. A question outside that bound returns `TemporalBoundRefusal`.

### Demonstration serve instant

Current main adds:

- `ccf.controlplane.demonstration_serve_instant.DemonstrationServeInstant`
- `ccf.products.demonstration_clock.DeclaredServeClock`
- `compose_serve_clock(...)`

A paved deployment may declare:

```yaml
demonstration_serve_instant:
  serve_instant: "<ISO instant>"
```

When `open_product` is called without a custom `clock=`, it takes the declaration as a startup snapshot and serves demonstration questions at that instant. The ingress temporal guard uses the same declared instant. A caller-composed clock beside the declaration is refused, as are misplaced/multiple declarations and unsupported production-store use.

This is a **development/demonstration clock**, not a general production time override.

## Product facade

Normal product authors use:

```python
from ccf.products.product import open_product
```

Do not recreate the governed resolver sequence by hand.

Current `OpenedProduct` also exposes the product's scoped invalidation sink, composed for that product's tenant, and records whether the paved road honored a demonstration serve instant.

## Declared entitlement and skill grants

Current deployment configuration can declare:

- `product_entitlement:` — one tenant-scoped policy with multiple principals/roles/classes;
- `grants:` — the declared skills that composition requests through the governed `GrantLedger`.

The paved road registers the declared entitlement at open. The standard product door only installs its one-principal default when no declared entitlement exists.

Declared skill grants use the composition-only `DeclaredSkillGrant` authority. A declared grant that the policy regime refuses raises `DeclaredGrantRefused`; a declared skill that is not granted still refuses `GrantNotInForce`.

## Composition and child question binding

Current child/composite contracts preserve the exact question asked of a child.

Relevant shapes include:

- `ChildCandidate.asked_question`;
- `QuestionBoundChildResolver`;
- `ChildArguments`;
- `ChildQuestionReferenceMismatch`;
- `ChildRecordAltered`.

A composite must not infer a child's subject/question from the child answer.

A complete declared producer/skill/agent/grant chain may now be combined with `questions=` and `build_children=`. The SDK derives and registers the chain; the deployment's child factory decides only the request-scoped optional-child choice and performs no Control Plane writes.

## Governed refusals

A refusal is an answer about governance, not a transport exception.

Current refusal behavior includes:

- `TemporalBoundRefusal`;
- `EvidenceAfterDecisionRefusal` when debt/scoring sees evidence dated after the decision instant;
- product/request/policy/debt/gate refusals;
- erasure-derived/refusal disclosure paths.

`EvidenceAfterDecisionRefusal` is recorded with a Replay reference. Other unexpected scorer exceptions still propagate.

## Subject-withholding controls on current main

`ProductClassDeclaration.subject_withholding` is now explicit:

- `may-withhold`;
- `never`.

For a class affirming `never`, the plan factory must positively declare `withholds_no_subject() -> True`; silence is refused by `NeverWithholdingNeedsAPositiveDeclaration`. The serve-time contradiction check remains as defense against a false positive declaration.

For classes that may withhold, current main contains additional SEC-020 defenses, including:

- an **unheld-subject probe** before the real subject-keyed acquisition;
- verification that the fixed probe identifier is actually absent;
- separation of population acquisition from subject-keyed acquisition;
- question-fabric/question-store freshness and exclusivity checks;
- early-policy and request-aware-child requirements where needed;
- stand-in / held-subject checks and constant-refusal paths;
- Replay evidence for `subject_withholding`, issuance and executed seeds.

These mechanisms reduce observable channels; they do **not** justify a blanket statement that a withheld subject and a nonexistent subject are universally indistinguishable. Use the current SDK decision log for SEC-020 governance status.

## Product door disclosure

On the product HTTP/MCP path, an undeclared product class can be answered with the same external `subject-unavailable` posture as an unentitled caller while the authorizer's denial remains in audit/Replay. Authentication, tenant selection, product roster and other gate failures remain distinct.

The standard product door can also expose the governed product resource when `expose_product_resource=True`.

For hand-composed governed products, use:

- `ccf_runtime.mcp.composed_product.ComposedProduct`;
- `compose_for_door(...)`.

This supplies the standard door with the same pinned Control Plane/refusal-recorder/policy composition rather than copying a per-example conformer.

## Assembly Mode 2

`assembly_mode: llm_packaged` remains supported. The algorithmic substrate stays the artifact-of-record and model packaging is gated before serve.

See DR-02 and [Decision Replay](DECISION_REPLAY.md).

## Exact current shapes

Use [Context Product API signatures](api/products.md) and the [Current Public Surface Index](PUBLIC_SURFACE_INDEX.md).

## Source outages and skill-governed composition

A declared seam exception with `cause: source-unavailable` produces `SourceUnavailableRefusal`, HTTP 409, with driver detail withheld below full disclosure; an early policy may still collapse it to `subject-unavailable`. Matching remains exact exception module/name, not subclasses. `SeamRefusalCause` extends binding causes without changing the subject-only `RefusalCause`. Composite acquisition can use a declared [Context Skill](CONTEXT_SKILLS.md); [replay](DECISION_REPLAY.md) now reconstructs admitted child lineage/expiry from retained evidence without recontacting producers.
