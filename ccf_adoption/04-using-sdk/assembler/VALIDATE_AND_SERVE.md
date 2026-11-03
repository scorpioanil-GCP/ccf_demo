# Validate, Record, and Serve a Context Product

## Wiring is not validation

The CCF deployment package helps an adopter assemble configuration, artifacts, registries, and runtime dependencies. It deliberately does **not** take over the product's validation gates.

That distinction is important because the product must be checked against what actually happened during assembly, not merely against the same authored document that claimed what should happen.

A convenience layer that derives both sides of a gate from one source can make the gate permanently green while proving nothing.

## The validation posture

An assembler should preserve three separate classes of truth:

1. **Authored intent** — specification / Control Plane declarations describing what should happen.
2. **Observed execution** — what assembly, operators, projection, and graph reads actually did.
3. **Delivery verdict** — whether the resulting candidate satisfies the conditions required to cross the product boundary.

The implementation should make drift among those classes observable.

## The three product gates remain three

The current SDK has a defined three-gate delivery sequence. Related checks such as request conformity, payload conformity, entitlement, or composition-time refusal must not be casually renamed as additional gates.

This matters for both documentation and control testing: a reviewer should be able to say exactly which mechanism refused the result.

## Governed refusal is a successful control outcome

A product that refuses because its governing conditions were not satisfied is not an outage.

The served/refused distinction should be explicit at the product boundary so a consumer can distinguish:

- a valid product;
- a governed refusal;
- a transport/infrastructure failure;
- a caller/request validation failure.

The assembler is responsible for producing refusal evidence useful enough for the consumer and reviewer to understand why the answer was not served.

## Measure Context Debt before pretending context is complete

Context Debt should reflect actual coverage/freshness/consistency evidence, using the versioned parameters the deployment declares.

The SDK provides mechanism; the product's specification/data work provides the domain calibration.

Do not hide missing freshness evidence by inventing a timestamp or default score. Explicit absence, degradation, or fail-closed behavior is preferable to false completeness.

## Record Decision Replay

Decision Replay is part of the product's forensic contract.

The record should allow the decision substrate to be reconstructed from the exact evidence available at decision time. The current SDK uses a five-dimension baseline designed to extend without adding a parallel replay model for each runtime mode.

Replay is not a model trace. Even a Mode-1 algorithmic product should be replayable.

Refusal also deserves replay when the producer records it: a governed "no" is itself a decision worth reconstructing.

## Serve through a door / binding

After assembly and validation, the product can be exposed through supported runtime seams. Transport should not redefine product semantics.

Consumers may reach the same governed product through different bindings/harnesses; the product contract remains the constant.

The assembler therefore owns the producer/runtime side of the door but should avoid leaking that machinery into consumer documentation.

## Deployment helper boundary

The current `ccf.deployment` package supports adopter wiring such as:

- load/derive `ccf_config.yaml`;
- load/validate/register a deployment manifest;
- resolve versioned pins/classes;
- build the operator registry;
- boot the wired fabric.

Its own package documentation draws a deliberate line: **wiring a deployment is not running the product gates**.

The assembler tutorial should preserve that line rather than creating a one-call helper that hides the evidence boundary.

## Validate the documented path, not merely the code path

A finished example should prove more than "some test passed."

The delivery workflow should establish that:

- the documented command is the command actually exercised;
- the example runs against the declared environment;
- operator/spec claims have execution witnesses;
- expected output is reviewed rather than regenerated blindly;
- data/provenance limitations are visible;
- sabotage or negative controls prove the gates are load-bearing;
- replay resolves;
- failure/refusal behavior is documented;
- source systems remain read-only where that is the declared posture.

The specification is approved first and proven second.

## What to publish with an assembler tutorial

A strong tutorial should show four layers of evidence together:

### Design

- business decision;
- specification version;
- request/contract surface;
- data/source bindings;
- scope and exclusions.

### Execution

- signal/graph/operator/projection path;
- actual run command;
- key output;
- debt/freshness state.

### Control

- gates/refusal behavior;
- policy/entitlement posture;
- replay reference;
- provenance/lineage.

### Boundary

- data reality / engineered limitations;
- backend-specific limitations;
- SDK limitations;
- claims not proven by the example.

## Composite Context Products — deferred

Do not use the current pre-CP-14 aggregate helpers as the basis for a public composite-product validation tutorial.

CP-14 is expected to define a significant product-level capability, including control semantics that may affect debt, lineage, replay, TTL/freshness, mixing/refusal, and serving.

Once CP-14 is approved, this page should be revisited specifically to answer whether validating a composite product introduces new evidence/gate requirements or composes the existing ones.