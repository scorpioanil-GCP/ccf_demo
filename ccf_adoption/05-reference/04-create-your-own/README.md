# Create Your Own Context Product

This path is for a **new** Context Product that does not already have an approved implementation specification.

If you are studying CP-00→CP-24, go back to the [producer examples](../02-context-product-producer/README.md). Their specifications are already complete.

## New-product workflow

### Step 1 — Start from the Standard

[Understand the specification and authority model →](01-standard-and-specification.md)

### Step 2 — Use AI to draft, not invent

[AI-assisted specification workflow →](02-ai-assisted-spec.md)

The SME and data engineer remain authoritative for business and source reality.

Missing terms stay `[TBC — owner]`.

### Step 3 — Gate 1

Human review approves the product design **before implementation**.

### Step 4 — Translate the approved spec into code

[Spec → code map →](03-spec-to-code-map.md)

[AI-assisted implementation prompt →](04-ai-assisted-codegen.md)

### Step 5 — Run and prove it

[Independent validation and Gate 2 →](05-validation-and-gate2.md)

## The rule

```
SME + data engineer settle the design
          ↓
AI drafts a rigorous spec from evidence
          ↓
GATE 1 — human approval
          ↓
AI generates implementation from approved spec
          ↓
run + deliberate gate failures + evidence
          ↓
independent validation
          ↓
GATE 2 — human close-out
```

AI accelerates the work. It does not become the authority for a missing business term, source fact, policy, calibration, or SDK behavior.
