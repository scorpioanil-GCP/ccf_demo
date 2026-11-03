# Specification → Paved-Road Implementation Map

This is the translation layer a developer or AI assistant should use after Gate 1.

| Spec | Primary implementation target | What lands there |
|---|---|---|
| §0 / front matter | README / summary / config metadata | product identity, lifecycle, data-reality disclosure |
| §A Decision frame | README / tests | decision, counterfactual acceptance test, scope rationale |
| §B.1 Product contract | `ccf_config.yaml: product_class` + projection payload | schema/version, TTL anchor, assembly mode, discovery, product gate |
| §B.2 Policy/classification | `ccf_config.yaml`, acquisition/view, operator parameters | formative policy and suppression behavior |
| §B.3 Model risk | config + model/harness artifacts when Mode 2/3 | pinned model/prompt and substrate/presentation boundary |
| §B.4 Request surface | `ccf_config.yaml: request_contract` | arguments, required, defaults, domains, unsupported arguments |
| §B.5 Prerequisites | product class `requires`, composition/children | child product dependencies and compatibility floors |
| §C Data catalog | `acquisition.py`, `ccf_environment.yaml` | store/schema/table reads and environment-value names |
| §C temporal/provenance fields | envelope mapping in `deployment.py` / acquisition | `SignalEnvelope` dates, source identity, entity vocabulary |
| §D Assembly recipe | `acquisition.py`, plan factory, `projection.py`, declared gates | executable assembly behavior |
| §D operator set | `ccf_config.yaml: product_class.required_operator_keys` | authored required operators |
| §D operator parameters | `ccf_config.yaml: operators` | governed parameter values/bindings |
| §D emitted payload | `projection.py` | payload shape from governed `GraphView` |
| §D validation gates | config + `deployment.py` predicate + tests | declared invariant and deliberate failures |
| §E half-life | `ccf_config.yaml: half_life` | per-signal decay calibration |
| §E Context Debt | `ccf_config.yaml: debt_profile` + `deployment.assess` | factor evidence and assessment |
| §E materialization | source/fabric deployment posture | on-demand vs materialized behavior |
| §F Source binding | `ccf_environment.yaml` + acquisition | runtime environment names; no raw secrets |
| §F readiness/traps | FINDINGS / tests / README | measured limitations, no invented repairs |
| §G Operate/govern | run/test/docs/server | SLO/observability/ownership/operational evidence |

## The modern code split

### `acquisition.py`

Pure domain/source leg where practical.

A strong acquisition module often imports **no CCF package at all**. It knows the source system and business interpretation, not the fabric.

### `deployment.py`

Maps acquired domain evidence into fabric envelopes and owns product-specific assessment/gate callables.

### `projection.py`

Reads the governed `GraphView` and emits the product payload.

### `produce.py`

Fabric binding only.

Canonical target:

```python
def plan_factory(*, required, request):
    return MyProjection(
        plan_id=...,
        required=required,
        subject=request.subject,
    )

def product(scratch):
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

## Why this mapping matters

Without it, an AI assistant tends to:

- copy values into Python because they are easy to see;
- invent a second operator set;
- carry raw acquisition state into projection;
- manually reproduce gate/replay/serve logic;
- put connection values in versioned config;
- silently fill a missing spec term.

The spec-to-code map gives each term one intended home.
