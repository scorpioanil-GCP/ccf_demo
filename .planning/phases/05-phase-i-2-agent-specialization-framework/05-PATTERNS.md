# Phase 5: Phase I.2 — Agent Specialization Framework - Pattern Map

**Mapped:** 2026-07-26
**Files analyzed:** 18 new/modified files
**Analogs found:** 15 / 18 (3 no-analog entries, all with RESEARCH.md guidance)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/ccf/agents/definitions.py` (Agent/Task definition schemas) | model (artifact contract) | transform (YAML → typed) | `src/ccf/controlplane/artifacts.py` | exact |
| `src/ccf/agents/factory.py` (AgentFactory/TaskFactory) | service (interpreter/factory) | transform (artifact → object) | `src/ccf/controlplane/artifacts.py` (`load_artifact`/`parse_artifact`) + `src/ccf/products/gates.py` (only-construction-path) | exact |
| `src/ccf/agents/agent.py` (concrete final `Agent`) | model + service | request-response (fabric seams) | `src/ccf/products/gates.py` (`ServableProduct` restricted-construction shape — but NO token per D-12) | role-match |
| `src/ccf/agents/archetypes.py` (`ArchetypeComponent` Protocol + six bundles) | protocol/model | — | `src/ccf/controlplane/registry.py` (`ControlPlaneProtocol`) + `src/ccf/artifacts/protocol.py` | role-match |
| `src/ccf/agents/composition.py` (D-IMPL-19 rules) | utility (pure functions) | transform | `src/ccf/contracts/canonical.py` (pure-function decidability via canonical bytes) | role-match |
| `src/ccf/agents/prompts.py` (Jinja2 parse-only validation) | service (validator) | transform | `src/ccf/controlplane/artifacts.py` (`load_artifact` I/O-free discipline) | role-match |
| `src/ccf/agents/errors.py` (NotYetBound, taxonomy) | utility (error types) | — | `src/ccf/artifacts/protocol.py` (error taxonomy) + `src/ccf/products/gates.py` (refusal contracts) | exact |
| `src/ccf/skills/catalog.py` (entry schema, 4 types, registration/discovery) | model + service | CRUD (Control Plane artifacts) | `src/ccf/controlplane/artifacts.py` | exact |
| `src/ccf/skills/grants.py` (state machine, tier-1 check, ApprovalSink Protocol) | service + protocol | event-driven (state transitions → audit) | `src/ccf/controlplane/registry.py` + `src/ccf/controlplane/audit.py` | exact |
| `src/ccf/skills/dispatch.py` (local-callable/tool dispatch) | service | request-response | `src/ccf/products/gates.py` (typed refusal vs exception split) | role-match |
| `src/ccf/controlplane/registry.py` (extend: hash-verified bump D-05) | service | CRUD | itself (`register_typed`, lines 179–227) | exact |
| `src/ccf/replay/record.py` (extend: dimension 4 fields D-06) | model | transform | itself (`PerspectiveConditioning`, lines 150–162; `MODE_1_MODEL_VERSION` precedent) | exact |
| `tools/lints/no_hardcoding.py` (extend cinv01c if needed) | config/lint | batch (AST scan) | itself (lines 345–358) | exact |
| `tests/invariants/test_replay_by_construction.py` (activate skill-set-capture, D-10) | test | — | itself (Check registry, lines 71–187) | exact |
| `tests/conformance/test_approval_sink.py` | test | — | `tests/conformance/test_artifactstore.py` | exact |
| `tests/fixtures/banking/agents/*.yaml`, `skills/`, `prompts/`, `tasks/` | config (fixture artifacts) | — | `tests/fixtures/banking/halflife.yaml` | exact |
| `tests/agents/harness_double.py` (D-03 test-double driver) | test fixture | request-response | — (see No Analog) | none |
| `tests/agents/test_factory.py`, `tests/skills/*`, `tests/integration/test_agent_slice.py` | test | — | I.1 test suites + conformance pattern | role-match |

## Pattern Assignments

### `src/ccf/agents/definitions.py` + `src/ccf/skills/catalog.py` (artifact-contract models)

**Analog:** `src/ccf/controlplane/artifacts.py` — the single strongest analog of the phase; every new artifact class copies it wholesale.

**Module preamble pattern** (lines 34–47) — imports, mode marker, `__all__`:
```python
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import yaml
from pydantic import Field, field_validator, model_validator

from ccf.contracts.base import CCFContract

__ccf_mode__ = "algorithmic"

__all__ = [ ... ]
```
Every new `/src` module MUST carry `__ccf_mode__ = "algorithmic"` (CINV-03) and a docstring citing the whitepaper section or CLAUDE.md §6 with the SDK-extension label (see the artifacts.py docstring, lines 1–32, as the citation-style model).

**Versioned-artifact base pattern** (lines 64–66, 116–126) — semver-lane field with grammar validation, no default:
```python
_SEMVER_RE = re.compile(
    r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)

class _VersionedArtifact(CCFContract):
    """Shared surface of every SDK-owned artifact class: its own semver lane."""

    semver: str

    @field_validator("semver")
    @classmethod
    def _semver_is_well_formed(cls, value: str) -> str:
        if not _SEMVER_RE.match(value):
            raise ValueError(f"{value!r} is not a semantic version")
        return value
```
Note: D-IMPL-28's two-field versioning (`schema_version` + `artifact_version`) extends this shape; reuse the same regex/validator style. Do not re-declare `_SEMVER_RE` — import or factor it if agents/skills schemas need it (planner's call; a second copy of the regex string is drift risk).

**Artifact-class binding + validation pattern** (lines 82–113):
```python
@dataclass(frozen=True)
class ArtifactClass:
    class_id: str
    contract: type[CCFContract]

    def validate(self, artifact: object) -> CCFContract:
        if not isinstance(artifact, self.contract):
            raise TypeError(
                f"artifact for class {self.class_id!r} must be a"
                f" {self.contract.__name__}, got {type(artifact).__name__}"
            )
        return artifact
```
New artifact classes declare module-level constants exactly like lines 252–254:
```python
HALF_LIFE_TABLE = ArtifactClass(class_id="ccf.half-life-table", contract=HalfLifeTable)
DEBT_PROFILE = ArtifactClass(class_id="ccf.debt-profile", contract=DebtProfile)
```
i.e. `AGENT_DEFINITION = ArtifactClass(class_id="ccf.agent-definition", contract=AgentDefinition)` etc.

**Cross-field validation pattern** (lines 241–248) — `model_validator(mode="after")` for coherence rules (use for archetype-list nonemptiness, instruction-binding shape, etc.):
```python
@model_validator(mode="after")
def _bands_are_ordered(self) -> "DebtProfile":
    if self.fail_closed_threshold < self.forced_llm_threshold:
        raise ValueError(
            "fail_closed_threshold must be at or above forced_llm_threshold:"
            " a class cannot fail closed before it escalates"
        )
    return self
```

**Base contract** — every schema derives from `CCFContract` (`src/ccf/contracts/base.py`, lines 36–47): `model_config = ConfigDict(extra="forbid", frozen=True)`. Subclasses never relax it.

---

### `src/ccf/agents/factory.py` (loading + construction)

**Analog:** `src/ccf/controlplane/artifacts.py` lines 257–311 (loading path) plus DESIGN.md §3.5 ("Factory reads through Control Plane resolution, never raw storage").

**YAML load + float-rejection pattern** (lines 296–311) — the one supported path from serialized artifact to typed contract; the factory reuses `load_artifact`/`parse_artifact` rather than re-implementing:
```python
def load_artifact(text: str, artifact_class: ArtifactClass) -> CCFContract:
    """... Deliberately takes text rather than a path: reading the file is the
    caller's concern, and keeping I/O out of this module keeps it algorithmic."""
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise ArtifactLoadError(f"artifact is not valid YAML: {error}") from error
    return parse_artifact(document, artifact_class)
```
`_reject_floats` (lines 257–277) runs before validation — do not bypass it for agent/task/skill/prompt artifacts. `yaml.safe_load` only (RESEARCH.md security table).

**Only-construction-path pattern** — D-12 rules OUT the `ServableProduct` token pattern (`src/ccf/products/gates.py` lines 112–137). Do NOT copy `_GATE_TOKEN`. The mechanism of record is the lint: the single legitimate `Agent(...)` call site lives inside `factory.py` (path contains `factory` — see the lint pattern below). `Agent` stays a normal public class.

**Error-class pattern** (lines 72–79) — one module exception subclassing a stdlib type, docstring stating why raised-not-repaired:
```python
class ArtifactLoadError(ValueError):
    """A serialized artifact cannot be admitted as written. ..."""
```

---

### `src/ccf/controlplane/registry.py` — hash-verified bump extension (D-05)

**Analog:** itself; the D-05 check is a thin layer on `register_typed`.

**Existing register_typed core** (lines 206–227) — content hash IS version identity; byte-identical re-registration is idempotent; class rebinding refused with `TypeError`:
```python
bound = self._classes.get(key)
if bound is not None and bound != artifact_class.class_id:
    raise TypeError(
        f"key {key!r} is already bound to artifact class {bound!r};"
        f" refusing to rebind it to {artifact_class.class_id!r}"
    )
artifact_class.validate(artifact)
version = content_hash(artifact)
versions = self._versions.setdefault(key, [])
if version not in versions:
    versions.append(version)
    self._artifacts[(key, version)] = artifact
self._classes[key] = artifact_class.class_id
self._record(action="register_typed", key=key, version=version,
             resolved=True, actor=actor, artifact_class=artifact_class.class_id)
return version
```
D-05's four-outcome table (RESEARCH.md "Hash-verified bump outcome table") sits on top: same-content/same-`artifact_version` → idempotent OK; same-content/new-version → typed refusal; new-content/same-version → typed refusal; new-content/new-version → append. Refusals are **returned values** (copy the `GateRefusal` shape below), NOT exceptions — a bad artifact, not a broken fabric. Preserve existing idempotency (Pitfall 6).

**Audit emission pattern** (lines 135–153) — every register/resolve, including failures, goes through `_record` → `AuditLog.append` with the injected clock. Grant-state-machine transitions in `src/ccf/skills/grants.py` follow the identical shape (see next).

**Missing-key exception pattern** (lines 67–72, 236–252) — `ControlPlaneMissing(LookupError)` raised, never a default. `NotYetBound` should mirror this class shape (typed exception subclassing a stdlib type — RESEARCH.md Open Question 2 recommendation).

---

### `src/ccf/skills/grants.py` (state machine + ApprovalSink Protocol + audit)

**Analogs:** `src/ccf/controlplane/audit.py` (event contract + append-only log) and `src/ccf/controlplane/registry.py` (Protocol declaration + clock injection).

**Typed action literal + event contract** (`audit.py` lines 43–74):
```python
AuditAction = Literal["register", "register_typed", "resolve", "resolve_latest"]

class AuditEvent(CCFContract):
    sequence: int
    action: AuditAction
    key: str
    version: str
    resolved: bool
    occurred_at: datetime
    actor: str | None = None
    artifact_class: str | None = None
```
Extend/mirror for grant transitions (requested/pending-approval/effective/refused/revoked). Note the `actor` docstring discipline (lines 58–61): the SDK never synthesizes an identity — the ApprovalSink double records an approver id string only (identity binding is D-IMPL-21, I.4).

**Append-only log** (`audit.py` lines 77–123): `append` + `events()` returning a tuple ("a caller holding the log must not be able to rewrite history through the reference it was handed"). Sequence numbers assigned internally. Route grant transitions through the existing `AuditLog` per RESEARCH.md Don't-Hand-Roll — do not build a new log type.

**Protocol declaration pattern** (`registry.py` lines 75–108):
```python
@runtime_checkable
class ControlPlaneProtocol(Protocol):
    """The read/write surface a Control Plane must offer. ..."""

    def register(self, key: str, artifact: object) -> str:
        """Append ``artifact`` under ``key``; return its version."""
        ...
```
`ApprovalSink` copies this shape: `@runtime_checkable`, docstring stating why a conforming impl cannot drop obligations, one-line docstrings + `...` bodies.

**Clock injection pattern** (`registry.py` lines 111–133) — never read a wall clock inside mechanism:
```python
def _utc_now() -> datetime:
    return datetime.now(tz=UTC)

def __init__(self, *, clock: Callable[[], datetime] | None = None) -> None:
    self._clock: Callable[[], datetime] = clock or _utc_now
```

**Grant-set hash (D-07)** — use `ccf.contracts.canonical.content_hash` over a `frozenset` of grant-artifact hashes; canonical.py lines 121–130 already give deterministic set ordering ("array sorted by each element's own canonical bytes"). No new hashing scheme (canonical.py line 14: "Nothing else in the SDK may define its own canonical form").

---

### `src/ccf/skills/dispatch.py` + tier-1 refusals (typed refusal pattern)

**Analog:** `src/ccf/products/gates.py`.

**Refusal-as-value contract hierarchy** (lines 75–110):
```python
class GateRefusal(CCFContract):
    """Base of the structured refusals the gates return.

    Attributes:
        gate: Which gate refused.
        detail: Human-readable statement of what was wrong. The typed subclass
            fields carry the machine-readable version — the text is for the
            operator reading a log, not for a caller to parse.
    """
    gate: str
    detail: str

class LineageMismatchRefusal(GateRefusal):
    declared: frozenset[str]
    resolved: frozenset[str]
```

**Union return + first-failure semantics** (lines 140–176):
```python
def run_gates(candidate, *, engine_resolved, now, registry, product_class
              ) -> ServableProduct | GateRefusal:
    """...
    Returns:
        A :class:`ServableProduct` when every gate passes, otherwise the
        refusal of the *first* gate that did not.
    Raises:
        ControlPlaneMissing: ... Raised rather than refused: that is a broken
        deployment, not a bad product, and the two must not be reported the
        same way.
    """
```
Apply the exception/refusal line exactly this way: tier-1 policy-incompatibility and D-05 bump violations → returned typed refusals; missing Control Plane key → `ControlPlaneMissing`; MCP/A2A dispatch → `NotYetBound` typed exception (build lacks the transport; nothing about the artifact is bad).

---

### `src/ccf/replay/record.py` — dimension-4 extension (D-06)

**Analog:** itself.

**Contract to extend** (lines 150–162) — additive fields only, done ONCE (Pitfall 1):
```python
class PerspectiveConditioning(CCFContract):
    """Dimension 4 — whose viewpoint conditioned the decision (INV-CH7-84).

    Agent identity, agent version, and the skill-set in force extend this in
    I.2 (CLAUDE.md §6.2). ..."""

    principal_id: str
    role: str
    delegation_chain: tuple[str, ...] = ()
```
Add all D-06 fields in the slice: definition content hash, versioned-URI annotation, composed archetype list, grant-set hash — with the grant-set field carrying an explicit positive "no grants" value until wave (c).

**Positive-claim sentinel precedent** (lines 57–60):
```python
MODE_1_MODEL_VERSION = "none"
```
Mirror this for the empty grant-set: a named module constant asserting "no grants in force," never an omission or `None`-by-default silence.

**Derived-not-reconstructed assembly** (`build_replay_record`, lines 196–235): "Every dimension is derived from artifacts that exist independently of the record ... Nothing is re-observed at record time." Dimension-4 values are the hashes captured at factory-construction/grant time, serialized here — never re-derived from the live `Agent` object (DESIGN.md §3.6 anti-pattern).

**Derived-id builder pattern** (`ContextFabricSnapshot.build`, lines 85–116) — if the plan gives the agent-identity block its own sub-contract, copy this classmethod shape: id = `content_hash` over exactly the named constituents.

---

### `src/ccf/agents/archetypes.py` + `src/ccf/agents/composition.py`

**Analogs:** `ControlPlaneProtocol` (Protocol shape, above) for `ArchetypeComponent`; `src/ccf/contracts/canonical.py` for conflict decidability.

Per RESEARCH.md Pattern 2, `ArchetypeComponent` exposes `fabric_interaction_pattern()`, `replay_obligations()`, `configuration_defaults()`. Make obligation values `CCFContract` instances so "identical" (dedupe) and "contradictory" (error) are decidable by comparing `canonical_bytes(...)` — the same trick canonical.py's set ordering uses (lines 121–130). Composition functions are pure, clock-free, I/O-free, in the canonical.py style (module docstring line 48: "pure functions over typed inputs, no I/O, no clock").

Factory warning on declaration-order default conflicts: use `warnings.warn` at construction inside `factory.py` (no I.1 precedent — new, keep it in the factory so composition.py stays pure and returns the conflict facts).

---

### `src/ccf/agents/prompts.py` (D-13)

**Analog (partial):** `load_artifact` text-in discipline (artifacts.py lines 296–302) — take text, not paths; I/O stays with the caller; module stays algorithmic.

Jinja2 usage per RESEARCH.md (parse-only; any `.render(` is I.3 scope creep):
```python
from jinja2 import Environment
from jinja2.meta import find_undeclared_variables

env = Environment()               # no loader — parse-only validation
ast = env.parse(template_source)  # jinja2.TemplateSyntaxError on bad template
used = find_undeclared_variables(ast)
```
Wrap `TemplateSyntaxError` in the module's own typed load error, mirroring `ArtifactLoadError`'s `raise ... from error` chaining (lines 307–311). Versioned-URI resolution goes through `src/ccf/artifacts/protocol.py` primitives (`artifact_uri`, `ArtifactRef`, `MovingTargetRefused` — `@latest` refused).

---

### `tools/lints/no_hardcoding.py` — cinv01c coverage

**Analog:** itself; extend, don't rebuild.

**Existing dormant rule** (lines 77–79, 345–358):
```python
FACTORY_ONLY_NAMES: frozenset[str] = frozenset({"Agent", "Task"})
FACTORY_PATH_MARKER = "factory"
...
if not in_factory_module:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _called_name(node.func) in (
            FACTORY_ONLY_NAMES
        ):
            emit(node, RULE_FACTORY_BYPASS,
                 f"{_called_name(node.func)} construction outside a factory"
                 " module — agents and tasks come from the Agent & Task"
                 " Factory reading definition artifacts (CLAUDE.md §6.4)", ...)
```
`in_factory_module` (line 271) is `FACTORY_PATH_MARKER in f"{path.as_posix()} {module_name}".lower()`. Consequence: name the factory module `factory.py` and put the single `Agent(...)`/`Task(...)` call site there (Pitfall 2). If extensions are needed (alias detection), extend `cinv01c` in the factory-hardening wave; a new allowlist entry for cinv01c is a warning sign, not a fix. Add a behavioral lint fixture proving cinv01c fires (rule is currently vacuous — RESEARCH.md Wave 0 gap).

---

### `tests/invariants/test_replay_by_construction.py` — CINV-04 activation (D-10)

**Analog:** itself. The `skill-set-capture` entry (lines 126–135) flips from:
```python
Check(
    name="skill-set-capture",
    invariant=("every skill grant and revocation, and the skill-set in force at "
               "decision time, land in replay dimension 4 by construction "
               "(CLAUDE.md §6.2)"),
    status="not-yet-applicable",
    phase="I.2",
)
```
to `status="active"`, `owning_test="<path>::<function>"`, `phase=None` — the registry's own tests (lines 147–173) enforce that shape: active checks must name an existing test function, deferred ones must name a phase. Suite goes 3 skips → 2 skips; the wave-(c) exit criterion is `pytest tests/invariants/test_replay_by_construction.py -rs -x` showing 2 skips.

---

### `tests/conformance/test_approval_sink.py`

**Analog:** `tests/conformance/test_artifactstore.py` (lines 1–60+).

Copy: `pytestmark = pytest.mark.conformance`; module docstring stating the acceptance-bar framing ("implements against a suite that already exists rather than a suite written to describe whatever it happened to build"); parametrization over an implementation factory so I.4's real ApprovalGate sink runs the same suite; assertions about Protocol behavior, never implementation internals; a minimal in-module `CCFContract` helper class rather than reusing SDK domain types.

---

### `tests/fixtures/banking/agents|skills|prompts|tasks/*.yaml`

**Analog:** `tests/fixtures/banking/halflife.yaml`.

Copy the fixture disciplines visible in its header (lines 1–17): comment block citing which whitepaper/CLAUDE.md commitments the fixture exercises and asserting "`/src` holds none of them"; a `keys:` block mapping registry key names (key names are values — they live in fixtures, not code); decimal values QUOTED so YAML parses them as text (the loader refuses floats). Agent definition fixture shape per RESEARCH.md "Six-axis definition artifact" example (illustrative field names; schema naming is the planner's D-IMPL-28 decision).

## Shared Patterns

### Module preamble + citation discipline
**Source:** every I.1 `/src` module (model: `src/ccf/controlplane/artifacts.py` lines 1–47)
**Apply to:** every new `/src` module
Docstring citing whitepaper §/CLAUDE.md § (SDK extensions cite CLAUDE.md §6 and say so explicitly), `from __future__ import annotations`, `__ccf_mode__ = "algorithmic"`, sorted `__all__`. Docstrings explain *why* an invariant holds, not just what the code does — this house style is uniform across I.1.

### Content identity
**Source:** `src/ccf/contracts/canonical.py` (`content_hash`, line 183–189)
**Apply to:** agent version identity (D-05), replay dimension 4 (D-06), grant-set hash (D-07)
```python
from ccf.contracts.canonical import content_hash
grant_set_hash = content_hash(frozenset(active_grant_hashes))
```
Never floats, never naive datetimes, near identity (rejected outright, lines 84–98). Ints/`Decimal`/aware-datetimes only.

### Typed contracts at every boundary
**Source:** `src/ccf/contracts/base.py` (`CCFContract`, `extra="forbid"`, `frozen=True`)
**Apply to:** every new schema, refusal type, replay field, obligation value.

### Refusal vs exception line
**Source:** `src/ccf/products/gates.py` (returned `GateRefusal` values) vs `src/ccf/controlplane/registry.py` (`ControlPlaneMissing` exception)
**Apply to:** tier-1 check, D-05 bump check (refusals); missing keys, `NotYetBound` (exceptions). Document each choice.

### Audit-by-construction
**Source:** `src/ccf/controlplane/audit.py` + `registry.py._record`
**Apply to:** every grant state-machine transition, every registration/resolution the new code adds — including failures (`resolved=False`).

### Injected time
**Source:** `registry.py` clock injection; `record.py` "Nothing here reads a clock. `recorded_at` is supplied by the caller."
**Apply to:** grant state machine, factory, replay extension. No `datetime.now()` outside an injected default.

## No Analog Found

| File | Role | Data Flow | Reason / Guidance |
|------|------|-----------|-------------------|
| `tests/agents/harness_double.py` (D-03 driver) | test fixture | request-response | No harness or agent-driver exists anywhere in the repo (deliberately — §7.3 no-loop). Build per D-03/RESEARCH.md Pitfall 5: linear deterministic script, one product consumption, one skill invocation, one effect emission, no loop, no branching on model output; lives in `/tests` only |
| `src/ccf/agents/agent.py` core surface | model/service | — | `ServableProduct` is the closest shape but its token pattern is ruled OUT (D-12). The Agent's trust-leg surface follows DESIGN.md §3.1; construct only from `factory.py` |
| Jinja2 parse-only validation internals | service | transform | New dependency (jinja2==3.1.6, add to pyproject core deps); API per RESEARCH.md, verify `find_undeclared_variables` signature in the slice's first test (Assumption A1) |

## Metadata

**Analog search scope:** `src/ccf/` (contracts, controlplane, replay, products, artifacts), `tools/lints/`, `tests/conformance/`, `tests/invariants/`, `tests/fixtures/banking/`
**Files scanned:** 11 read in full or targeted; directory listings across `src/ccf`
**Pattern extraction date:** 2026-07-26
**Key rulings constraining pattern reuse:** D-12 (NO construction token — do not copy `_GATE_TOKEN`), D-07 (no epoch counter), D-13 (no `render()`), Pitfall 1 (dimension-4 fields added once)
