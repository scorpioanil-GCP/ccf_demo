# CP-01 — Counterparty Reference Snapshot

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-01-counterparty-reference-snapshot/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

**Business-to-spec companion:** [Analysis](CP01_COUNTERPARTY_REFERENCE_SNAPSHOT_ANALYSIS.md) · [HTML reading edition](CP01_COUNTERPARTY_REFERENCE_SNAPSHOT_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-01-counterparty-reference-snapshot/README.md`  
**Qualified specification:** `examples/cp-01-counterparty-reference-snapshot/spec/CP-SPEC-001_Counterparty_Reference_Snapshot.md`  
**Qualified source:** `examples/cp-01-counterparty-reference-snapshot`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-01-counterparty-reference-snapshot/spec/CP-SPEC-001_Counterparty_Reference_Snapshot.md`

Read it in this order before opening the Python:

| Spec section | What to learn | Where it lands |
|---|---|---|
| §A | decision, consumer, counterfactual, scope | README + acceptance tests |
| §B | product contract, request, TTL, policy/perspective | `ccf_config.yaml` + payload |
| §C | sources, identity, ontology, data traps | acquisition + environment/source declarations |
| §D | operators, projection, gates | `acquisition.py`, `deployment.py`, `projection.py`, `produce.py` |
| §E | half-life, Context Debt, materialization | config + assessment code |
| §F | source readiness and limitations | environment/source artifacts + findings |
| §G | acceptance and operational evidence | tests, gates, run evidence |

As you read the code, ask: **which approved spec term is this implementing?**

## Why this example exists

The first catalog Context Product. It adds identity authority, entity-freshness TTL and formative policy. The same anchor surface can resolve through different identity authorities, and an excluded principal receives a governed refusal rather than a redacted/empty success.

## The question

> What counterparty reference facts are valid for this caller now, which identity authority supplied them, and is the answer still fresh enough to serve?

## What to understand before you run it

- TTL can be anchored to source/entity freshness rather than request time.
- Two identity authorities can sit behind one anchor parameter and imply different freshness ceilings.
- Policy is load-bearing even at Tier 1: excluded and nonexistent subjects are deliberately indistinguishable.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

The source estate is read-only. Supply the environment values below for your restored/qualified estate; placeholders deliberately avoid turning one developer machine into part of the contract.

```bash
export CCF_CP_01_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
```

## Files to read

Read these in order if you want to understand the implementation rather than only run it.

| Path | Why |
|---|---|
| `examples/cp-01-counterparty-reference-snapshot/spec/` | Gate-1/2 implementation specification. |
| `examples/cp-01-counterparty-reference-snapshot/artifacts/` | Question, recipe and expected evidence. |
| `examples/cp-01-counterparty-reference-snapshot/deployment.py` | Identity authority/policy/TTL-specific implementation. |
| `examples/cp-01-counterparty-reference-snapshot/produce.py` | Governed assembly path. |
| `examples/cp-01-counterparty-reference-snapshot/run.py` | Variations and presentation. |
| `tests/examples/test_cp_01_output.py` | Executable proof of the documented behaviors. |

## Run it

```bash
make venv
make example-cp-01
make example-cp-01 PRINCIPAL=PRIN-KYC-004
make example-cp-01 ANCHOR=CLI-000101
make example-cp-01 ANCHOR=549300TRW1LZMDJZAQ78
make example-cp-01 ANCHOR=549300TRW1LZMDJZAQ78 INCLUDE_LAPSED=1
make example-cp-01 AS_OF=2026-01-01T00:00:00+00:00
```

Commands that intentionally exercise refusal may exit non-zero. That is correct when the program documents the outcome as a governed refusal rather than a crash.

## What you should observe

- Default anchor serves with identity_authority visible in the payload.
- PRIN-KYC-004 is governed-refused in a form intentionally indistinguishable from a nonexistent counterparty.
- The no-LEI internal-client anchor exercises the second identity authority and may hit TTL bounds because its source freshness is much older.
- AS_OF is declared but unsupported at this tier and refuses `not-supported-at-tier`; it is never silently ignored.

Do not compare volatile content addresses or timestamps with prose unless the qualified SDK example itself publishes a pinned transcript. For exact byte-level claims, use the example's committed tests/transcript.

## How the example works

The general path is:

```
source estate (read only)
        ↓
acquisition / source interpretation
        ↓
SignalEnvelope(s)
        ↓
L2 assembly into governed L3 state
        ↓
L4 operators
        ↓
L5 projection Π over GraphView
        ↓
L6 Context Product gates / fulfillment
        ↓
served product OR governed refusal
```

The product-specific files above show where this rung changes that pattern.

## Variations to try

| Purpose | Command | Expected semantic change |
|---|---|---|
| Excluded principal | `make example-cp-01 PRINCIPAL=PRIN-KYC-004` | Governed refusal; no disclosure that distinguishes suppressed from absent. |
| Internal client ID | `make example-cp-01 ANCHOR=CLI-000101` | Second identity authority and different freshness ceiling. |
| Lapsed registration | `make example-cp-01 ANCHOR=549300TRW1LZMDJZAQ78 INCLUDE_LAPSED=1` | Request semantics change the admitted result. |
| Unsupported as-of | `make example-cp-01 AS_OF=2026-01-01T00:00:00+00:00` | Explicit not-supported refusal. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_01_output.py -q
```

These tests are the reproduction backstop. A manual run demonstrates the story; the tests/gates hold the implementation to it.

## What this example proves

- Identity authority is part of the governed answer.
- Entity-freshness TTL is materially different from request-anchored TTL.
- Policy suppression can be structurally silent.
- Declared-but-inert parameters fail explicitly.

## What it does not prove

- Enterprise IAM integration.
- Production freshness calibration.
- That all products should expose the same request axes at Tier 1.

## Spec → code lesson for Cowork

Use CP-01 to teach how a spec becomes identity/policy/TTL behavior and how refusal semantics are designed. For new code structure, pair it with the current paved-road examples.

When generating a new product, Cowork must take product-specific values from the **approved new spec and source evidence**, never from this demonstration merely because the code is convenient to copy.

