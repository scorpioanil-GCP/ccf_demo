# Context Half-life and Context Debt

**Package:** `ccf.halflife`  
**Current SDK reference baseline:** `drcastillo/ccf_code/v1.0.2@5f85b389efe9e4b1de62e84a5af62ca4b2e12178`\
**Release:** `v1.0.2` @ `5f85b389efe9e4b1de62e84a5af62ca4b2e12178` (17 October 2026)

## Two different concepts

### Context Half-life — λ_c

Half-life models decay of decision relevance over time.

It is **not** a TTL.

- TTL answers whether a product remains servable.
- half-life contributes to how trustworthy/current the assembled context is.

The SDK supplies decay mechanism. The deployment supplies calibrated values through versioned Control Plane artifacts.

### Context Debt — D_c

Context Debt quantifies shortfall in the context required by the decision versus the context actually assembled.

The standard factor model uses:

- freshness `F`
- completeness `C`
- semantic consistency `S`

A qualified debt assessment carries:

- factor values;
- resulting debt;
- governance signal/band;
- evidence pointers where configured.

## Key surfaces

### Decay

`ccf.halflife.decay` includes the observation/decay machinery.

A product/deployment should never invent a half-life when the observation type has no declared calibration.

### Debt

`ccf.halflife.debt` and `ccf.halflife.assessment` provide:

- `DebtFactors`
- `DebtAssessment`
- debt signals
- freshness scoring
- debt assessment functions/protocols

## Assessment belongs to the actual assembled view

Modern paved-road assessment receives `AssessmentContext` containing the governed `GraphView`, decision instant, evidence and the booted calibration artifacts.

Preferred pattern:

```python
def assess(context: AssessmentContext) -> DebtAssessment:
    assert context.half_life is not None
    assert context.profile is not None

    return calculate_debt(
        view=context.view,
        now=context.decided_at,
        half_life=context.half_life,
        profile=context.profile,
    )
```

Do not calculate Debt from a raw acquisition object if policy/operators changed what was admitted.

## Freshness is per signal class

A mixed product can legitimately contain signals with very different decay rates.

Examples:

- CP-03: annual vs quarterly financial facts
- CP-09: market observation vs policy effectivity vs reporting period
- CP-10: daily market spreads vs slower internal grades

One product-wide “freshness” label is insufficient when the underlying signals decay differently.

## Absence is not staleness

If a source did not claim to cover the requested instant, that source is absent for the question. Do not take its latest historical observation and call it stale unless the source semantics actually say the observation remains applicable.

CP-09 is the clearest example.

## Leading edge vs history

Historical time series may intentionally preserve years of observations. Freshness must score the observation(s) the decision actually depends on, not average the age of the entire retained history.

CP-10 demonstrates this distinction.

## Debt and fulfillment

A product can be structurally valid and still not be fit for the caller's tolerance.

Debt tolerance is part of the governed request/effective parameter set. A product over tolerance can be withheld/refused according to the declared policy rather than served with an informal warning.

CP-05 is the clearest early example.

## Composite Debt

For composite products, do not invent a new arithmetic by averaging child debt numbers.

Use the SDK's governed composition mechanisms and the rules encoded by the qualified composite surface.

CP-14 and CP-23 are useful evidence:

- CP-14 composes child product evidence;
- CP-23 demonstrates population-level factor composition.

## Calibration is domain work

Example half-lives and thresholds are demonstrations, not recommended production policy.

A production team must establish calibration with the SME, data owner and governance/control owners.

## Decision Replay

Decision Replay is supported on current main. Debt, debt evidence, source-refresh recency, obligation-in-force and trusted timing evidence are retained where the Replay contract requires them; use [Decision Replay](DECISION_REPLAY.md) and DR-01 rather than hand-building a Replay environment.

