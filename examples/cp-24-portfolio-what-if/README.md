# CP-24 — Portfolio What-If / Stress

**Rung 24 of the Context Product ladder.** What happens to a coverage book
under explicit assumptions — and the first rung whose answer is **conditional**.

> **CP-24 is not a forecasting or modeling platform.** The scenario assumptions
> are explicit inputs. CCF governs the current context, binds the assumptions,
> produces the scenario-conditioned product, and keeps facts and hypotheticals
> distinguishable and replayable. **No model is fitted, no probability is
> estimated, nothing is predicted.**

> **Illustrative calibration:** This example runs against a point-in-time
> demonstration estate rather than continuously refreshed production data.
> Freshness half-lives, the debt tolerance and the sensitivity values are
> calibrated to make the governed behavior observable in that snapshot. They
> demonstrate how the SDK applies these controls and should not be interpreted
> as recommended production values.

## What this demonstrates

### The governing rule


> **Observed evidence determines Context Debt. Scenario assumptions determine
> scenario-derived outputs. Scenario assumptions are never evidence.**

Six consequences, each gated: scenario magnitudes never become claims
(`WIF-G06`); the assumptions live in the effective request (`WIF-G15`); every
derived value names the assumption that produced it (`WIF-G07`); observed
lineage stays attached to the factual input (`WIF-G08`); no hypothetical
pretends it was observed (`WIF-G06`); and **`D_c` is unchanged when only the
scenario changes** — `WIF-G13` proves that directly.


## Run it

```bash
export CCF_CP_24_POSTGRES_DSN=...  CCF_CP_24_POSTGRES_SCHEMA=ccf_v2
export CCF_CP_24_FLUREE_URL=...    CCF_CP_24_FLUREE_LEDGER=fibo-v2
export CCF_CP_24_TOKEN_COVERAGE=... CCF_CP_24_TOKEN_CREDIT=... \
       CCF_CP_24_TOKEN_PRODUCT=...  CCF_CP_24_TOKEN_UNGRANTED=...

make -s example-cp-24
make -s example-cp-24 PRINCIPAL="--principal PRIN-CO-002" INTENT="--intent credit-review"
make -s example-cp-24 SCENARIO='--scenario {"rate_shift_bp":300,"collateral_shift_bp":-2000,"collateral_class":"real_property"}'
```

**Many scenarios are many requests.** There is no sweep, no scheduler and no
sandbox — each scenario is its own governed determination.


## The story

### Assumptions are integers in canonical units


Every scenario magnitude is an **integer in basis points**. SOFR +150 bps is
`150`; CRE −10 % is `-1000`. This is measured, not stylistic: a bare JSON
fraction parses to a `float`, and the SDK refuses a float as *not bit-stable
across platforms*. **That refusal is correct and is never coerced around** —
rounding would produce a content address nobody could reproduce. The `Decimal`
conversion happens inside the arithmetic and never crosses a wire.

```
scenario: {"rate_shift_bp": 150, "collateral_shift_bp": -1000,
           "collateral_class": "real_property", "horizon_months": 12}
```

The object is **closed**: an undeclared member is refused, and a third level is
not expressible at all — `SkillArgumentMember` carries neither `properties` nor
`items`, and is not widened for this rung.

### A scenario does not refresh its factual inputs


The book's oldest collateral observation is **545 days old**. Stressing it by
−10 % yields a **stressed stale valuation**, and the product says so: every
derived figure carries its observation's instant and age, the arithmetic uses
that same instant, and nothing — `observed_at`, freshness, TTL or debt — is
reset because a calculation ran (`WIF-G11`, `WIF-G12`).

### The three impact limbs


| Limb | Observed | Assumed | Derived |
|---|---|---|---|
| interest cost and headroom | drawn balance, SOFR | `rate_shift_bp` | shifted rate, incremental interest, headroom after |
| secured coverage | valuation, age, the estate's haircut | `collateral_shift_bp`, `collateral_class` | stressed value and stressed secured value |
| portfolio roll-up | the population | both | which members fall below the declared coverage floor |

Nothing else. Rating migration, liquidity and covenant projection are
*forecasts* and are out of scope.

### A sibling of CP-23, not a composite over it


CP-24 reads the authoritative underlying sources using the population shape
rung 23 proved. It does **not** compose CP-23 as a child: the capability under
test is explicit hypotheticals, not product composition. The duplicated
population reader is recorded in `FINDINGS.md` as a friction **measurement** —
the **second** instance — and no abstraction is pre-authorized.


## Artifact-by-artifact

| file | what it carries |
|---|---|
| `ccf_config.yaml` | the class, the operator keys, and the closed object-valued `scenario` parameter |
| `ccf_environment.yaml` | where the source legs are read from — names only, never values |
| `artifacts/source-vocabulary.yaml` | the estate's own tables, columns and IRIs |
| `artifacts/perspectives.yaml` | the role-conditioned views |
| `artifacts/sensitivities.yaml` | the rate and collateral sensitivities — **illustrative values, declared not coded** |
| `artifacts/question.yaml` | the demonstration book, its instant and the demonstration scenario |
| `artifacts/gates.yaml` | the seventeen declared gates and their observed reds |


## Whitepaper / CLAUDE.md sections exercised

| section | how |
|---|---|
| Whitepaper §7.4 — operator algebra | the declared keys over the current governed context the scenario is applied to |
| Whitepaper §7.5 — Projection | deterministic arithmetic over a Control Plane sensitivity artifact |
| Whitepaper §7.6 — Context Product Contract | a **closed object-valued** request parameter in integer canonical units |
| Whitepaper §7.7 — half-life and Context Debt | **an assumption cannot move `D_c`** — two scenarios over one instant give identical debt |
| Whitepaper §7.10 — Decision Replay | observed evidence on dimension 2, the hypothetical on the recorded request — separated by construction |
| CLAUDE.md §6.4 — No-Hardcoding | the sensitivities are declared values, never code |
| CLAUDE.md §7.1/§7.3 — MCP egress | the standard door; the closed object crosses it byte-identically |
| CLAUDE.md §9 — estate discipline | reads `.76` only; seeds nothing; scenario values are disclosed as illustrative |


## What to change first

Replace `artifacts/source-vocabulary.yaml` with your own estate's names and
rewrite the readers in `acquisition.py`; `produce.py` names no domain value and
does not change.

**Change `artifacts/sensitivities.yaml` before anything else.** The rate and
collateral sensitivities are illustrative values in a Control Plane artifact,
not code — which is what lets a different sensitivity model be an edit to a
document. The scenario itself is a request parameter: a closed object in
integer canonical units, so a new scenario is a new question rather than a new
product.

### Illustrative calibration

This example runs against a point-in-time demonstration estate rather than
continuously refreshed production data. Freshness half-lives and related
thresholds are calibrated to make the governed behavior observable in that
snapshot. They demonstrate how the SDK applies these controls and should not
be interpreted as recommended production coverage-policy thresholds.

The rate and collateral sensitivities in `artifacts/sensitivities.yaml` are
demonstration values chosen to make the scenario arithmetic observable. They
are not recommended production stress parameters.


## What would fail

### Known limitations


All measured and classified in `FINDINGS.md`:

- **The float refusal is a raise, not a governed envelope.** Request
  canonicalization runs before the request contract is consulted, so the
  refusal carries no replay reference — the `D-IMPL-304` residual shape.
  Nothing is coerced, which is the half the ruling requires.
- **The debt tolerance is calibrated to the estate's staleness.** A 545-day-old
  appraisal makes the book's worst-member freshness genuinely low; a tighter
  tolerance would withhold every answer and demonstrate nothing.
- **The estate is not refreshed to make the stress cleaner.** The stale
  observations stay stale and are reported as such.

### Gates


17 declared gates, `WIF-G01`..`WIF-G17`, in `artifacts/gates.yaml`, each claimed
by an executing test under `tests/examples/test_cp_24_*.py`. **All seventeen
observed red** under their own sabotage; none is `unavailable`.

### Specification


`spec/CP-SPEC-024_Portfolio_What_If_Stress.md`, authored to Context Product
Specification Standard v0.3 before any code existed, with Dave's Gate-2 rulings
folded in at §F.4.
