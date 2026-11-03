# CP-02 — Facility Terms Snapshot

> **Current run instructions — 18 October 2026:** checked against [SDK `v1.0.2@5f85b389`](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/cp-02-facility-terms-snapshot/README.md). Use [the shared setup and configuration rules](../../../examples/CONFIGURATION.md), Fluree **4.2.4** where required, explicit ports and complete connection strings. The qualified source/specification pins below preserve earlier evidence; they do not select the checkout used by these commands.

> **Design companion (draft for review):** [Banking problem and specification analysis](CP02_FACILITY_TERMS_SNAPSHOT_ANALYSIS.md) · [HTML review edition](CP02_FACILITY_TERMS_SNAPSHOT_ANALYSIS.html).

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/cp-02-facility-terms-snapshot/README.md`  
**Qualified specification:** `examples/cp-02-facility-terms-snapshot/spec/CP-SPEC-002_Facility_Terms_Snapshot.md`  
**Qualified source:** `examples/cp-02-facility-terms-snapshot`

> **Read the README and the qualified specification before opening the implementation code.**

## Start with the completed specification

For this shipped example, the design work is already complete. **Do not draft a new spec.**

Open the qualified SDK specification first:

`examples/cp-02-facility-terms-snapshot/spec/CP-SPEC-002_Facility_Terms_Snapshot.md`

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

Shows a product whose lifetime belongs to the underlying instrument/document rather than to the request. It also teaches honest handling of source defects—impossible dates, missing maturity and incomplete amendment history—without repairing them in code.

## The question

> What facility terms are valid for this principal, when does that answer expire based on the agreement itself, and which source defects must remain visible?

## What to understand before you run it

- `from_entity_freshness` can anchor to a filed/effective instrument date.
- Need-to-know and jurisdiction are separate policy conditions.
- Bad source facts are served or refused honestly; they are not silently normalized into plausible values.

## Prerequisites

Run from the `ccf_code` repository root.

```bash
make venv
```

The source estate is read-only. Supply the environment values below for your restored/qualified estate; placeholders deliberately avoid turning one developer machine into part of the contract.

```bash
export CCF_CP_02_POSTGRES_DSN='host=<host> port=<port> dbname=<database> user=<read-only-user> password=<password>'
```

## Files to read

Read these in order if you want to understand the implementation rather than only run it.

| Path | Why |
|---|---|
| `examples/cp-02-facility-terms-snapshot/spec/` | The instrument-anchored contract and source traps. |
| `examples/cp-02-facility-terms-snapshot/artifacts/` | Question, recipe, TTL and expected behavior. |
| `examples/cp-02-facility-terms-snapshot/deployment.py` | Source-to-envelope and TTL/debt rules. |
| `examples/cp-02-facility-terms-snapshot/produce.py` | Governed assembly path. |
| `examples/cp-02-facility-terms-snapshot/run.py` | Documented variations. |
| `tests/examples/test_cp_02_output.py` | Behavioral/gate evidence. |

## Run it

```bash
make venv
make -s example-cp-02
make -s example-cp-02 ASKED_AT=2026-09-15T23:45:00+00:00
make -s example-cp-02 FACILITY=FAC-66B83D
make -s example-cp-02 FACILITY=FAC-517638
make -s example-cp-02 NO_PRICING_GRID=1
make -s example-cp-02 FACILITY=FAC-1FF50C
make -s example-cp-02 PRINCIPAL=PRIN-RES-002
make -s example-cp-02 AS_OF=2026-01-01T00:00:00+00:00
```

Commands that intentionally exercise refusal may exit non-zero. That is correct when the program documents the outcome as a governed refusal rather than a crash.

## What you should observe

- Moving asked_at does not move expiry when the facility's own effective date anchors TTL.
- Malformed/missing maturity data remains explicit rather than being converted into a fabricated tenor.
- An old facility can refuse on TTL bounds.
- A principal with jurisdiction visibility but no facility-level need-to-know is refused.
- Dropping the pricing grid changes payload shape and therefore content identity.

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
| Move decision time | `make -s example-cp-02 ASKED_AT=2026-09-15T23:45:00+00:00` | Expiry remains anchored to the facility date. |
| Impossible maturity | `make -s example-cp-02 FACILITY=FAC-66B83D` | Serves source defect honestly; does not invent tenor. |
| Expired facility | `make -s example-cp-02 FACILITY=FAC-1FF50C` | TTL refusal. |
| Need-to-know denied | `make -s example-cp-02 PRINCIPAL=PRIN-RES-002` | Governed refusal. |
| Unsupported parameter | `make -s example-cp-02 AS_OF=2026-01-01T00:00:00+00:00` | Explicit request-contract refusal. |

## Validate it

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tests/examples/test_cp_02_output.py -q
```

These tests are the reproduction backstop. A manual run demonstrates the story; the tests/gates hold the implementation to it.

## What this example proves

- Instrument/source-date anchored TTL.
- Two-condition policy behavior.
- Refusal prevents probing suppressed existence.
- Data traps can be first-class documented findings.

## What it does not prove

- That the engineered source defects are production defect rates.
- That a 90-day TTL is a recommended policy.

## Spec → code lesson for Cowork

Copy the discipline: source anomalies belong in §C/§F and tests; do not 'clean' them in generated code unless the approved spec explicitly defines a governed transformation.

When generating a new product, Cowork must take product-specific values from the **approved new spec and source evidence**, never from this demonstration merely because the code is convenient to copy.

