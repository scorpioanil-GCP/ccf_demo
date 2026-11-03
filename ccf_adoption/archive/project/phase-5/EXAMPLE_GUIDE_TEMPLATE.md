# CP-XX — <Product Name>

**Qualified SDK:** `main@015be95f…`  
**Source:** `examples/cp-XX-<slug>`  
**Status:** canonical | qualified | historical-not-copy-target

## Why this example exists

What new capability/failure mode does this rung add?

## The question

> The exact business/technical question this Context Product answers.

## What to understand first

- concept 1
- concept 2

## Prerequisites

### SDK

```bash
make venv
```

### Data/source estate

Name each required source and whether it must be read-only.

### Environment

```bash
export ...
```

Never put real credentials in this documentation.

## Files to read

Read in this order:

1. `spec/...`
2. `ccf_config.yaml`
3. `ccf_environment.yaml` / backend declaration
4. `acquisition.py`
5. `projection.py`
6. `deployment.py`
7. `produce.py`
8. `run.py`
9. tests / findings

Explain what each file contributes.

## Run it

### Default

```bash
...
```

### Direct/no-Make path

```bash
...
```

## What you should observe

Describe the important governed behavior:

- served or refused;
- key payload/business result;
- Context Debt;
- TTL/expiry;
- lineage/operator evidence;
- content address;
- replay reference if the qualified example emits one.

## How it works

Map source → L1 → L2/L3 → L4 → L5 → L6.

## Variations to try

| Variation | Command | What should change |
|---|---|---|

## Validate it

```bash
...
```

Explain what the tests prove.

## What would fail

Common setup and semantic failure modes.

## What this example proves

Specific claims supported by the example.

## What it does not prove

Explicit boundaries.

## Spec → code lesson for Cowork

What should an AI assistant copy structurally, and what must come from the new product's approved spec instead?
