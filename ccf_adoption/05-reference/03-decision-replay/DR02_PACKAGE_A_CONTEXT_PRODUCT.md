# DR-02 — Package a Context Product

> **Current execution baseline:** SDK `v1.0.2@5f85b389`. Follow [setup and configuration](../../examples/CONFIGURATION.md); dated qualification results below retain their original scope.

**Qualified SDK:** `drcastillo/ccf_code/main@a4cf2fb74af4964dcfee29d210d17d94b909d78d`  
**README:** `examples/dr-02-package-a-context-product/README.md`  
**Qualified specification:** `examples/dr-02-package-a-context-product/spec/DR-SPEC-002_Package_A_Context_Product.md`  
**Qualified source:** `examples/dr-02-package-a-context-product`

> **Read the README and the qualified specification before opening the implementation code.**

## Why this example exists

DR-02 is the first shipped Context Product whose delivered payload is written by a model.

It exercises **Assembly Mode 2 — `llm_packaged`**.

The important architecture is:

```
finished governed Context Product
             ↓
          MODEL
      packages the result
             ↓
      packaged claims
             ↓
algorithmic projection + gates
             ↓
           serve
```

The model does **not** replace the algorithmic Context Product. The upstream product remains the artifact-of-record.

The packaged memo is a derivative governed view.

## The question

The demonstrated upstream is:

`cp-06-canonical-collateral-and-setoff-coverage`

That product carries assets, haircuts, realizable values and a coverage ratio.

DR-02 asks:

> How should that governed product be rendered as prose for a credit officer without losing the product's governance or allowing the packaging to change the conclusion?

## Prerequisites

Complete the producer/data-estate setup first.

Start the CP-06 door:

```bash
.venv/bin/python examples/cp-06-canonical-collateral-and-setoff-coverage/run.py --door
```

It prints:

```text
READY <port>
```

Export the DR-02 upstream connection:

```bash
export CCF_DR_02_UPSTREAM_URL=http://127.0.0.1:<port>/mcp
export CCF_DR_02_UPSTREAM_TOKEN=<credential accepted by the upstream door>
```

The CP-06 door also needs its own `CCF_CP_06C_*` estate variables.

DR-02 itself reads **no source datastore directly**. Its source is the already-governed upstream Context Product.

## Run it

```bash
.venv/bin/python examples/dr-02-package-a-context-product/run.py
```

## Read the spec before the code

Use this sequence:

1. `README.md`
2. `spec/DR-SPEC-002_Package_A_Context_Product.md`
3. `ccf_config.yaml`
4. `ccf_environment.yaml`
5. `artifacts/memo-prompt.yaml`
6. `acquisition.py`
7. `memo_packaging.py`
8. `projection.py`
9. `deployment.py`
10. `produce.py`
11. `run.py`
12. `artifacts/gates.yaml`
13. `FINDINGS.md`

## Spec → code map

| Spec concern | Implementation |
|---|---|
| Assembly Mode 2 | `ccf_config.yaml → product_class.assembly_mode: llm_packaged` |
| upstream product | `ccf_environment.yaml → sources.upstream_product` |
| model + temperature + prompt | `artifacts/memo-prompt.yaml` |
| ask upstream product | `acquisition.py` |
| package the product | `memo_packaging.py` |
| emit packaged claims | `acquisition.py` |
| audience conditioning | Policy operator in `ccf_config.yaml` |
| packaged payload | `projection.py` |
| smoothing gate | `deployment.py` |
| Replay dimension-3 packaging pins | `deployment.py → packaging_trace`, wired through `produce.py` |
| executable acceptance | `tests/examples/test_dr_02_packaging.py` + `artifacts/gates.yaml` |

## The five packaging pins

A retained Replay record carries the Mode-2 packaging trace:

- model version;
- temperature;
- prompt artifact URI;
- prompt artifact hash;
- output hash.

The product also carries the packaging identity needed to inspect the delivered memo.

This lets an examiner distinguish:

- the algorithmic product that was the substrate;
- the model/prompt that packaged it;
- the exact packaged bytes that were delivered.

## The smoothing gate

The product gate is:

`packaging.did-not-move-the-conclusion`

It refuses when the prose claims something the substrate does not support.

The shipped build caught this against its own first implementation: the renderer computed and stated an asset count that was not carried by the upstream product. The correct fix was to change the prose, not weaken the gate.

That is the central lesson of DR-02:

> **Model output is a claim. It must be judged before delivery.**

## Why the model sits at acquisition

The model packages an already-finished product at the acquisition seam.

Its prose then enters the fabric as claims and passes through ordinary algorithmic projection and validation.

Putting the model inside projection would let semantic output reach delivery without a downstream gate. DR-02 intentionally avoids that architecture.

## Expiry and Debt

A packaged rendering cannot be fresher than its substrate.

The product therefore uses:

`ttl_anchor: from_entity_freshness`

and its expiry follows the upstream evidence rather than the time the prose happened to be generated.

The rendered product also remains subject to Context Debt and governed refusal.

## Validate it

Run the complete DR-02 acceptance module:

```bash
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest \
  tests/examples/test_dr_02_packaging.py -q
```

The module holds nine declared gates covering:

- Assembly Mode 2 on the record;
- populated rendering primitives;
- versioned prompt identity;
- smoothing-gate refusal;
- audience exclusion before materialization;
- upstream refusal propagation;
- substrate-based expiry;
- content-address determinism and movement when a pin changes;
- the real packaging trace on the **retained** replay record.

## What to vary

### Prompt artifact

Change the prompt artifact first.

Adding a heading the deterministic packager does not understand should fail loudly. Then teach the packager that heading and let the smoothing gate judge the resulting output.

### Audience

Narrow the `audience` parameter and observe that excluded sections never materialize.

### Temperature

A different packaging temperature is a different packaging determination and must move the content identity.

### Real model

The shipped CI path uses a deterministic fail-loud packager. A real provider model is opt-in.

The governance path is the same: pin the rendering primitives, produce claims, project, gate, serve.

## What this proves

- Assembly Mode 2 is a real shipped Context Product mode.
- A model can package a governed product without becoming the artifact-of-record.
- Model, temperature, prompt and output are replay-visible.
- Unsupported prose can be refused before delivery.
- Audience policy applies before materialization.
- Packaged output inherits the substrate's temporal truth rather than manufacturing new freshness.

## What it does not prove

- Portability to arbitrary upstream products; only CP-06 is demonstrated.
- Correctness or quality of every external model provider.
- That an unreachable upstream is automatically a governed refusal.
- That prose generation should happen inside projection.
- That a model may derive new figures and present them as if the substrate carried them.

## Engineering lesson

Mode 2 is not “put an LLM after the data.”

It is:

> **algorithmic truth → pinned semantic packaging → algorithmic validation**

That separation is what lets the human-facing form remain governed.
