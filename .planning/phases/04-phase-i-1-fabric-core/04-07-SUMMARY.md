---
phase: 04-phase-i-1-fabric-core
plan: 07
subsystem: halflife-and-controlplane
tags: [FABR-05, FABR-07, lambda-c, context-debt, control-plane, audit-plane]
requires: [04-03, 04-05]
provides:
  - "ccf.halflife.decay — λ_c formal decay over versioned Control Plane rates"
  - "ccf.halflife.debt — D_c basic/extended forms + typed CAR routing signals"
  - "ccf.controlplane.artifacts — typed artifact classes + validating loader"
  - "ccf.controlplane.audit — AuditEvent contract + append-only AuditLog"
  - "ccf.controlplane.registry — typed registration, actor attribution, ReplayResolver"
affects: [src/ccf/controlplane, src/ccf/halflife, pyproject.toml]
tech-stack:
  added: []
  patterns:
    - "Decimal-only numeric surface for anything that reaches the replay record"
    - "Protocol seam per debt factor with (scorer_id, scorer_version) replay pinning"
    - "ArtifactClass as a frozen dataclass carrying a contract type (never content-hashed)"
key-files:
  created:
    - src/ccf/halflife/__init__.py
    - src/ccf/halflife/decay.py
    - src/ccf/halflife/debt.py
    - src/ccf/controlplane/artifacts.py
    - src/ccf/controlplane/audit.py
    - tests/halflife/test_decay.py
    - tests/halflife/test_debt.py
    - tests/fixtures/banking/halflife.yaml
  modified:
    - src/ccf/controlplane/registry.py
    - src/ccf/controlplane/__init__.py
    - tests/controlplane/test_registry.py
    - pyproject.toml
decisions:
  - "Observation, not Claim, is the decay input: claims carry no observation-type axis in I.1"
  - "Freshness aggregation is the arithmetic mean, shipped as the reference F scorer under a Protocol"
  - "YAML floats are refused at load rather than converted — version identity must not depend on float printing"
metrics:
  duration: ~40m
  completed: 2026-07-25
---

# Phase 04 Plan 07: λ_c / D_c and the Full Control Plane Summary

Context Half-life and Context Debt ship as pure mechanism — every rate,
multiplier and threshold resolved from a versioned Control Plane artifact — and
the minimal 04-03 registry widens into the full subsystem: typed artifact
classes, a separated audit plane, and a replay resolver that structurally
cannot reach "latest".

## What was built

**λ_c (`src/ccf/halflife/decay.py`).** The whitepaper's decay formula
`R(t) = R₀ × (1/2)^((t − t₀) / λ_c)`, computed entirely in `Decimal` inside a
pinned decimal context. Two whitepaper properties are structural rather than
documented: λ_c is Control Plane configuration per observation type
(INV-CH7-58) — so an undeclared type raises `MissingHalfLife` and no fallback
rate exists anywhere in the module — and λ_c is *not* a TTL (INV-CH7-57), so
the curve asymptotes toward zero and never expires. `effective_half_life`
realizes the Freshness Budget (`λ_c × Risk Sensitivity`). An observation dated
after the decision instant raises `TemporalOrderError` rather than being
clamped to "perfectly fresh": clock skew is a data-integrity fault, and
clamping would convert it into a confident decision.

**D_c (`src/ccf/halflife/debt.py`).** Both committed forms —
`1 − (C_available / C_required)` and `1 − (F · C · S)`. The multiplicative form
is the *only* one that exists in the module: there is no weighted-additive
path to fall back to, because INV-CH7-63 rejects it as a defect rather than a
tuning preference. The whitepaper's guarantor worked example (F=0.95, C=0.95,
S=0.05 → D_c ≈ 0.955) is a test, alongside an assertion of the gap against the
additive form that would have scored the same context at 0.23.
`DebtFactorScorerProtocol` is the D-IMPL-47 seam with `(scorer_id,
scorer_version)` on the surface for replay pinning; `FreshnessScorer` is the
reference F computation (decay-ratio aggregation). C and S scorers are
deliberately absent — they need a required-field vocabulary and a contradiction
detector, both deployment knowledge.

`assess_debt` returns `DebtSignal.OK | FORCED_LLM | FAIL_CLOSED` read strictly
from the profile's bands ("above the threshold" means above, not at). The
signals are **values with no side effects**: I.1 ships no LLM path and no
escalation surface, and a function that acted on the signal here would put
routing policy in code.

**Control Plane (`src/ccf/controlplane/`).** `artifacts.py` declares the typed
artifact classes (`HalfLifeTable`, `HalfLifeEntry`, `DebtProfile`, plus
`DeclaredArtifact` for classes whose schema belongs to a deployment — policy
bundles, operator parameter sets) with a mandatory semver lane per artifact,
and the one supported path from serialized to validated (`load_artifact` /
`parse_artifact`). `audit.py` separates the audit-event contract and the
append-only log out of the registry. `registry.py` gains `register_typed`
(validates against the class contract; refuses rebinding a key to a different
class mid-history, which would make older versions un-resolvable at replay),
caller-stated `actor` attribution, and `ReplayResolver` — a view exposing
`resolve` alone.

## Verification

| Check | Result |
|---|---|
| `pytest tests/halflife` | 42 passed |
| `pytest tests/controlplane tests/halflife tests/gates` | 88 passed |
| `pytest tests -m "not postgres and not chroma"` | 176 passed (was 115) |
| `python -m tools.lints --all` | exit 0 |
| `mypy --strict src` | Success, 41 files |
| float literals in `halflife/` + `controlplane/artifacts.py` (AST audit) | zero |
| threshold/rate literals in `/src` | zero — all in `tests/fixtures/banking/halflife.yaml` |

The plan's acceptance criterion `grep -rEc "[0-9]+\.[0-9]+" decay.py = 0`
returns 5, and all five matches are whitepaper section citations in docstrings
(`§7.7`, `§7.10`). The criterion's intent — no literal rates — is verified more
precisely by an AST float-literal audit, which returns zero for every module in
this plan.

## Deviations from Plan

### Auto-fixed / adjusted

**1. [Rule 3 — Blocking] `mypy --strict` failed on the untyped PyYAML import**
- **Found during:** Task 1
- **Issue:** `artifacts.py` imports `yaml` for the load helper the plan calls
  for; PyYAML ships no inline types and `types-PyYAML` is not a project
  dependency. `mypy --strict src` is in the plan's own verification command.
- **Fix:** Added a scoped `[[tool.mypy.overrides]]` for `yaml` in
  `pyproject.toml` rather than installing a stub package. Installing into the
  shared `.venv` mid-wave would have affected the other wave-5 agent, and
  package installs are excluded from auto-fix. The untyped boundary is one call
  deep and closed by contract validation on the very next line.
- **Commit:** `0801fad`

**2. [Design] Decay takes an `Observation`, not a `Claim`**
- The plan sketches `freshness(claim, ...)`, but the I.1 claim contracts
  (`ccf.contracts.claims`) carry no observation-type axis, and λ_c is keyed by
  observation type by whitepaper commitment ("per observation type, not as a
  per-document attribute"). Introducing the axis onto `EntityClaim` would be a
  graph-contract change owned by another plan, so decay declares its own
  minimal typed input instead. Wiring claims to observation types is a
  follow-on for whichever plan owns the claim/observation-type binding.

**3. [Scope] `HalfLifeTable` landed in `artifacts.py` immediately**
- The plan allowed defining it in `decay.py` and moving it in Task 3 "if
  cleaner". It was cleaner: `decay.py` re-exports both names, so the public
  import surface matches the plan either way.

**4. [Scope] MAX_TTL was not re-declared as an artifact class**
- The plan lists MAX_TTL among the artifact classes, but `MaxTTL` already
  exists in `src/ccf/products/contract.py` (owned by 04-05, and being widened
  by the concurrent wave-5 agent). Declaring a second MAX_TTL type would create
  exactly the duplicate-contract drift the typed registry exists to prevent.
  Binding the existing type to an `ArtifactClass` is a one-line follow-on in
  whichever plan next touches `products/contract.py`.

## Known Stubs

None. `DebtFactors` requires the caller to supply C and S because the SDK has
no basis to compute them yet — this is a documented Protocol seam
(`DebtFactorScorerProtocol`, D-IMPL-47), not an unwired placeholder: F has a
working reference scorer, and the extended formula is fully exercised.

## Threat Flags

None. The plan's two registered threats are both mitigated: T-04-15 (silent
default substitution) by typed no-default fields plus `MissingHalfLife` /
`ControlPlaneMissing` and their tests; T-04-16 (repudiation on config change)
by append-only versions, the append-only `AuditLog` with no delete surface, and
actor attribution that is recorded when stated and never invented.

## Commits

| Task | Commit | Gate |
|---|---|---|
| 1 | `cf640f4` | RED — decay tests + fixture λ_c table |
| 1 | `0801fad` | GREEN — `decay.py`, `artifacts.py` |
| 2 | `1eb7d7f` | RED — debt tests incl. guarantor example |
| 2 | `13e467b` | GREEN — `debt.py` |
| 3 | `495b952` | Full Control Plane subsystem |

## TDD Gate Compliance

Tasks 1 and 2 ran RED→GREEN with separate commits per gate; both RED runs were
confirmed failing (collection error on the absent module) before implementation.
No REFACTOR commit was needed. Task 3 was a non-TDD widening task per the plan.

## Self-Check: PASSED

All eight created files and four modified files verified present; all five
commit hashes verified in `git log`.
