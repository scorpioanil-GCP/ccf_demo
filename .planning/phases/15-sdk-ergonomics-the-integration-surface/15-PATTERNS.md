# Phase 15: SDK Ergonomics — The Integration Surface - Pattern Map

**Mapped:** 2026-08-04
**Files analyzed:** 9 new-file groups + 6 modified surfaces
**Analogs found:** 13 / 15 (2 marked NEW — no analog exists)

This phase builds almost entirely *inside the SDK*, so every analog below is in this repo.
Where the research flagged genuinely new structure, this document says NEW rather than
stretching a near-match.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/ccf/deployment/__init__.py` (new pkg) | package root / config | — | `src/ccf/operators/__init__.py` | exact |
| `src/ccf/deployment/*.py` loaders | utility (interpreter) | file-I/O → transform | `src/ccf/controlplane/artifacts.py` (parse side) + `runtime/.../cli/commands/__init__.py::load_document` (read side) | role-match |
| New `ArtifactClass` constants ×8 in `src/ccf/controlplane/artifacts.py` | model / config | transform | `HALF_LIFE_TABLE` / `DEBT_PROFILE`, `artifacts.py:202-270` | **exact** |
| class-id → `ArtifactClass` lookup | registry | transform | — | **NEW — no analog** (§2.1 of RESEARCH: no class-id registry exists) |
| D-02 timestamp handling in `load_artifact` | utility (parse guard) | transform | `_reject_floats`, `artifacts.py:273-293` | **exact** |
| D-05 manifest entry point (`load_and_boot`-shaped) | service / composition | request-response | `src/ccf/boot.py::boot` (the thing it wraps) | role-match |
| D-07 two-phase operator-registry builder | factory | transform | `src/ccf/operators/registry.py:85-138` (`OperatorRegistry.register`, wrapped not replaced) | role-match |
| `tools/dump_surface.py` (D-15) | tool / generator | file-I/O | `tools/dump_openapi.py` | **exact** |
| `tests/test_surface_drift.py` (D-15) | test (drift gate) | transform | `tests/http_api/test_openapi.py:107-128` | **exact** |
| Committed JSON Schemas + freshness gate (D-04) | tool + test | file-I/O | same triad as above (`dump_openapi` + `Makefile:168-169` + drift test) | **exact** |
| `ccf schema export` CLI noun | CLI command | request-response | `runtime/ccf_runtime/cli/commands/config.py` | **partial — see divergence note** |
| `ccf.deployment` → `ccf.products.gates` import ban | lint rule | transform | `tools/lints/harness_imports.py` (`cinv02-graph-writer` half) | **exact** |
| `tests` added to `RULE_TREE_SCOPE["no-hardcoding"]` | config + test | transform | `tools/lints/__main__.py:47-52` + `tests/lints/test_examples_scope.py` | **exact** |
| `tests/products/test_gate_independence.py` AST guard | test (AST invariant) | transform | `tests/invariants/test_adapter_single_writer.py` + `tests/agents/test_consumption_discipline.py` | **exact** |
| Nine `tests/examples/test_*_output.py` modules (D-09) | test | transform | `tests/examples/test_ext00_hardening.py` | **exact** |
| Rewritten `examples/NN/run.py` | example | request-response | `examples/00-quickstart/` (run.py + artifacts/ + README + `Makefile:65-95`) | **exact** |

---

## Pattern Assignments

### 1. New `ArtifactClass` declarations — `src/ccf/controlplane/artifacts.py`

**Analog:** the two existing registered classes in the same file. This is a verbatim template;
every new class (`ccf.resolution-spec`, `ccf.operator-parameters.*` ×4, `ccf.perspective`,
product-class, signal-batch, `ccf.deployment-manifest`) follows all five parts.

**Part A — the semver base every SDK-owned class inherits** (`artifacts.py:134-142`):

```python
class _VersionedArtifact(CCFContract):
    """Shared surface of every SDK-owned artifact class: its own semver lane."""

    semver: str

    @field_validator("semver")
    @classmethod
    def _semver_is_well_formed(cls, value: str) -> str:
        return validate_semver(value)
```

Note it is **private** (`_`-prefixed, not in `__all__`). New contracts subclass it; the semver
grammar is never re-declared (`validate_semver`, `artifacts.py:73-87`, is the one home — E7).

**Part B — the contract, with per-field and cross-field validators** (`DebtProfile`,
`artifacts.py:216-264`). The shape to copy:

```python
class DebtProfile(_VersionedArtifact):
    """A decision class's D_c calibration (whitepaper §7.7 CAR; INV-CH7-65).
    ...
    """

    risk_sensitivity: Decimal
    forced_llm_threshold: Decimal
    fail_closed_threshold: Decimal

    @field_validator("forced_llm_threshold", "fail_closed_threshold")
    @classmethod
    def _threshold_is_in_the_debt_codomain(cls, value: Decimal) -> Decimal:
        if not _ZERO <= value <= _UNIT:
            raise ValueError("debt thresholds must lie in [0, 1]")
        return value

    @model_validator(mode="after")
    def _bands_are_ordered(self) -> "DebtProfile":
        if self.fail_closed_threshold < self.forced_llm_threshold:
            raise ValueError(
                "fail_closed_threshold must be at or above forced_llm_threshold:"
                " a class cannot fail closed before it escalates"
            )
        return self
```

Closed-world comes free: `CCFContract` is frozen + `extra=forbid` (stated `artifacts.py:5-6`).
D-03's "an unknown key fails at parse" needs **no extra machinery** — it needs only that the
class subclass `CCFContract` and that the artifact stop carrying keys it does not declare.

Docstring convention to copy exactly: cite the whitepaper section in the first line
(`(whitepaper §7.7 CAR; INV-CH7-65)`), then explain *why each field has no default*. Per
CLAUDE.md C-11, `ccf.deployment` classes cite **CLAUDE.md §6.4/§10 and mark themselves
SDK-defined** instead — see `boot.py:1-4` for that variant:
`"SDK-defined mechanism (CLAUDE.md §10; the whitepaper specifies the single-writer *invariant*, not the wiring that realizes it)."`

**Part C — the module-level constant** (`artifacts.py:267-270`), the entire "registration"
mechanism:

```python
#: The λ_c table class (whitepaper §7.7).
HALF_LIFE_TABLE = ArtifactClass(class_id="ccf.half-life-table", contract=HalfLifeTable)
#: The decision-class debt profile class (whitepaper §7.7 CAR).
DEBT_PROFILE = ArtifactClass(class_id="ccf.debt-profile", contract=DebtProfile)
```

`#:` comments (Sphinx-style attribute docs) precede each constant. `ArtifactClass` itself is a
frozen dataclass, **not** a `CCFContract` — `artifacts.py:103-106` gives the reason and it
constrains any new structure built alongside it: "it carries a Python type, which has no
canonical serialization and never belongs in a content hash."

**Part D — `__all__` registration** (`artifacts.py:49-60`). Sorted, capitals before lowercase.
Every new contract name and constant goes here — RESEARCH E8 notes this is also the D-15 diff's
tracking surface.

**Part E — the validation path is untouched.** `parse_artifact` (`artifacts.py:296-309`) and
`load_artifact` (`artifacts.py:312-327`) are generic over `ArtifactClass`; a new class needs
zero loader changes.

**D-01 docstring amendment target — the exact sentence to change** (`artifacts.py:25-29`):

```
Artifact classes whose *schema* belongs to a deployment rather than to the SDK
— policy bundles, operator parameter sets — use :class:`DeclaredArtifact`,
```

…and its restatement inside `DeclaredArtifact` itself (`artifacts.py:146-150`): *"Policy
bundles, operator parameter sets, ontology declarations"*. **Both sites** name operator
parameter sets; the planner must amend both or the module contradicts itself.

---

### 2. The D-02 timestamp guard — `src/ccf/controlplane/artifacts.py`

**Analog:** `_reject_floats` (`artifacts.py:273-293`) — the stated precedent, same file, same
recursion shape, same refuse-never-repair posture.

```python
def _reject_floats(value: object, path: str) -> None:
    """Refuse a parsed YAML float anywhere in an artifact document.

    Converting one to :class:`~decimal.Decimal` here would be a silent repair of
    a value that has *already* lost precision at parse time, ...
    """
    if isinstance(value, float):
        raise ArtifactLoadError(
            f"{path or '<root>'}: float values are not admissible in a Control"
            " Plane artifact (not bit-stable across platforms); quote the value"
            " so it parses as text and is validated as a decimal"
        )
    if isinstance(value, Mapping):
        for key, item in value.items():
            _reject_floats(item, f"{path}.{key}" if path else str(key))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_floats(item, f"{path}[{index}]")
```

Three things to copy: the **dotted path accumulator** (`f"{path}.{key}"` / `f"{path}[{index}]"`,
with `'<root>'` fallback), the **docstring-carries-the-reasoning** convention (this is where
CONTEXT's `<specifics>` "the `Z` reframing belongs in the code comment" lands), and the
`ArtifactLoadError` type (`artifacts.py:90-97`, a `ValueError` subclass).

**Intervention point for suppressing PyYAML's resolver** — `load_artifact:324`:

```python
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise ArtifactLoadError(f"artifact is not valid YAML: {error}") from error
    return parse_artifact(document, artifact_class)
```

A `SafeLoader` subclass with `yaml.resolver.Resolver`'s `tag:yaml.org,2002:timestamp` entry
removed replaces `yaml.safe_load` here. No other line in the module changes.

**Lint trap to design around (RESEARCH §7.2 Trap 1):** the float message above is a 3-line
string opening with a "not"-clause and it does *not* trip CINV-01a. Keep new messages under
200 chars and under 3 sentences and they will behave the same way.

**The 11 duplicated `_instant` sites this deletes** — verbatim body at
`examples/00-quickstart/run.py:85-95`:

```python
def _instant(value: object) -> datetime:
    """Normalize an artifact timestamp to an explicit UTC instant. ..."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
```

---

### 3. The `ccf.deployment` package skeleton (D-13)

**Analog:** `src/ccf/operators/__init__.py` — an algorithmic-tagged package `__init__` whose
docstring enumerates its modules and states the mechanism/values line.

```python
"""L4 — Context Operators, the System of Computation.

Whitepaper §7.4 ...

The package is five modules, split along the mechanism/values line:

:mod:`ccf.operators.base`
    The operator contract, ...
:mod:`ccf.operators.params`
    The declared parameter contracts — schema only, never a value, never a
    default (D-IMPL-38).
...

Algorithmic package (CINV-03): L4 computes, it never interprets.
"""

from __future__ import annotations

__ccf_mode__ = "algorithmic"
```

Copy: `from __future__ import annotations` first, then `__ccf_mode__ = "algorithmic"` at module
level, then `__all__`. The `:mod:` cross-reference list is the house style for a package
docstring (compare `src/ccf/halflife/__init__.py`, same shape).

**The tag is checked by** `tools/lints/algorithmic.py::is_algorithmic` (`algorithmic.py:53-66`),
which AST-matches a top-level `Assign`/`AnnAssign` to the `Name` `__ccf_mode__` with
`Constant` value `"algorithmic"`. It then bans imports of
`{ccf.llm, anthropic, openai, cohere, litellm, google.generativeai, mistralai}`
(`algorithmic.py:40-50`) — **and nothing else**. This is the verbatim confirmation of D-13's
"algorithmic means no model call, not no I/O." The precedent to cite in the package docstring:
`boot.py:55` carries the tag while opening SQLite files; `artifacts.py:47` carries it while
importing `yaml`.

**Per-module tagging is also required**, not just the package `__init__` — the lint runs
per-file. See `runtime/ccf_runtime/cli/commands/config.py:1-14` for the minimal form: a
one-line `"""... (D-IMPL-22).\n\nAlgorithmic module (CINV-03).\n"""` docstring, then
`__ccf_mode__ = "algorithmic"`, then `__all__`.

**File-reading side** — the closest existing "read a path, hand a document onward" helper is
`runtime/ccf_runtime/cli/commands/__init__.py:43-55`:

```python
def load_document(path: str) -> dict[str, Any]:
    """Load one YAML/JSON artifact document from ``path``.

    The file carries the artifact; the CLI carries nothing inline
    (No-Hardcoding Rule, CLAUDE.md §6.4 — T-07-29).
    """
    loaded = yaml.safe_load(Path(path).read_text())
    if not isinstance(loaded, dict):
        raise ValueError(
            f"{path!r} does not hold a mapping document; an artifact file"
            " is a single YAML/JSON mapping"
        )
    return loaded
```

Note the divergence the planner must resolve: this helper calls `yaml.safe_load` directly and
would therefore **bypass D-02's suppressed resolver**. `ccf.deployment`'s loaders must route
through `load_artifact(text, klass)`, not re-implement this.

---

### 4. The class-id → `ArtifactClass` lookup — **NEW, no analog**

RESEARCH §2.1 states this as a verified negative: *"There is **no registry of artifact
classes**. `ArtifactClass` instances are module-level constants."* I re-read
`artifacts.py` end to end and confirm it — the module has no mapping, no decorator, no
`__init_subclass__` hook, nothing that would collect the constants.

The nearest structural cousins in the repo are the lint modules' frozenset constants
(`harness_imports.py:51-80`) and `CHECKERS` in `tools/lints/__main__.py:61-66`:

```python
Checker = Callable[[pathlib.Path, str], list[str]]

CHECKERS: dict[str, Checker] = {
    "no-hardcoding": no_hardcoding.check,
    "harness-imports": harness_imports.check,
    ...
}
```

That is a hand-maintained `dict[str, T]` module constant with a typed alias — the same shape a
`dict[str, ArtifactClass]` would take, and a defensible template. But it is a **partial**
analog: it does not have `declared_artifact_class(class_id)` fallthrough semantics, and it does
not have to stay in sync with `artifacts.__all__`. **The planner should treat this as new
design work and not assume it is free.** Whether the lookup is exhaustive-by-hand or derived
from `artifacts.__all__` is an open plan-level choice; a hand-maintained dict with a test
asserting every `ArtifactClass` constant in `artifacts.__all__` appears in it would match the
repo's "carve-outs are reviewed module constants, never a data file" posture
(`harness_imports.py:29-31`).

---

### 5. The committed-artifact + regenerator + drift-gate triad (D-04 schemas, D-15 surface)

**Analog:** Phase 14's OpenAPI arrangement. Three parts, all needed.

**Part A — the regenerator, `tools/dump_openapi.py`.** Key excerpts:

```python
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

#: The committed contract baseline (D-12).
OPENAPI_PATH = REPO_ROOT / "openapi.json"


def serialize(document: dict[str, Any]) -> str:
    """The one serialization recipe — see "Determinism recipe" above.

    `tests/http_api/test_openapi.py` imports this function rather than
    restating the recipe, so the committed file and the drift assertion
    can never disagree about what "the spec" means.
    """
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(...)
    parser.add_argument("--check", action="store_true", help=(
        "Write nothing; exit 1 if the on-disk file differs from what"
        " create_app() emits."))
    args = parser.parse_args(argv)

    emitted = serialize(build_app().openapi())

    if args.check:
        on_disk = OPENAPI_PATH.read_text(encoding="utf-8") if OPENAPI_PATH.exists() else ""
        if on_disk != emitted:
            print(f"{OPENAPI_PATH} differs from what create_app() emits."
                  " Run `make openapi` and review the diff — ...", file=sys.stderr)
            return 1
        return 0

    OPENAPI_PATH.write_text(emitted, encoding="utf-8")
    print(f"wrote {OPENAPI_PATH}")
    return 0
```

Four things to copy verbatim into `tools/dump_surface.py` and the schema exporter:
`REPO_ROOT` derived from `__file__` (never `cwd`); a **single exported `serialize()`** the test
imports; a `--check` mode that writes nothing and exits 1; and a module docstring with an
explicit **"Determinism recipe"** section (`dump_openapi.py:18-31`) stating why the bytes are
stable and naming the corollary — *"a FastAPI or Pydantic bump will move the spec. That diff is
desirable and reviewable ... and the correct response is to run `make openapi` and read the
diff, never to relax the check."*

**Part B — the make target** (`Makefile:168-169`, with its `.PHONY` entry at `:34`):

```make
openapi: ## Regenerate the committed openapi.json — the D-12 drift baseline
	$(ENV) $(PYTHON) tools/dump_openapi.py
```

The `## comment` is the help-text convention (`Makefile:1`). New targets go in the same
`.PHONY` list.

**Part C — the drift assertion, `tests/http_api/test_openapi.py:26-42, 107-128`:**

```python
# Repo root from this file's own path, never ``Path.cwd()`` — pytest may be
# invoked from anywhere and the baseline is a fixed repo artifact.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_COMMITTED_SPEC = _REPO_ROOT / "openapi.json"

_DRIFT_MESSAGE = (
    "The committed openapi.json no longer matches what create_app() emits."
    " Run `make openapi` and commit the result. ..."
)


def test_the_committed_spec_matches_what_the_app_emits(app: Any) -> None:
    """D-12: the baseline external integrators consume is not stale.

    Asserted on **bytes**, not on parsed dicts, because the committed file
    is reviewed as a diff — whitespace and key order are part of what makes
    that diff readable, so they are part of what is asserted.
    """
    committed = _COMMITTED_SPEC.read_text(encoding="utf-8")
    assert committed == serialize(_document(app)), _DRIFT_MESSAGE


def test_the_drift_message_names_the_regeneration_command(app: Any) -> None:
    """Edge case: a failure nobody can act on is a failure that gets muted."""
    assert "make openapi" in _DRIFT_MESSAGE
    assert "openapi.json" in _DRIFT_MESSAGE
```

Copy all four moves: `parents[N]` from `__file__`; **import `serialize` from the tool** rather
than restating it; assert on **bytes**; and ship the meta-test that the failure message names
its own fix. The docstring at `:9-14` also records *why the test lives in `tests/`* — "the
already-always-on `test` job — so an endpoint change fails CI on the same commit that causes
it, with no new CI wiring." That reasoning transfers directly to both D-04 and D-15.

---

### 6. The `ccf schema export` CLI noun (D-04) — **partial analog, with a real divergence**

**Analog:** `runtime/ccf_runtime/cli/commands/config.py` (the closest read-only noun), plus its
registration in `main.py`.

**Command module shape** (`config.py`, complete file, 63 lines):

```python
"""The ``config`` noun — Control Plane introspection (D-IMPL-22).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import argparse

from ccf_runtime.cli.commands import RequestSpec

__ccf_mode__ = "algorithmic"

__all__ = ["register"]


def _keys(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    return (RequestSpec(method="GET", path="/config/keys",
                        params={"class_id": args.class_id}),)


def register(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Add the config noun and its ruled verbs."""
    noun = subparsers.add_parser("config", help="Control Plane configuration")
    verbs = noun.add_subparsers(dest="verb", required=True)

    keys = verbs.add_parser("keys", help="keys under an artifact class")
    keys.add_argument("--class-id", required=True)
    keys.set_defaults(build=_keys)
```

Conventions: one `register(subparsers)` per noun; `__all__ = ["register"]` only; private
`_verb(args) -> tuple[RequestSpec, ...]` handlers bound via `set_defaults(build=...)`; noun then
`add_subparsers(dest="verb", required=True)`.

**Wiring** — `runtime/ccf_runtime/cli/main.py`, two edits, both mechanical:

```python
from ccf_runtime.cli.commands import (
    RequestSpec, agent, artifact, config, hitl, product, replay, skill, workflow,
)
...
    subparsers = parser.add_subparsers(dest="noun", required=True)
    agent.register(subparsers)
    skill.register(subparsers)
    workflow.register(subparsers)
    hitl.register(subparsers)
    replay.register(subparsers)
    artifact.register(subparsers)
    product.register(subparsers)
    config.register(subparsers)
```

**⚠ The divergence the planner MUST resolve, not paper over.** `main.py`'s own docstring states
the CLI's constitutional constraint:

> *"Every command translates to requests against the HTTP API routes; the CLI holds no fabric
> handle and interprets nothing it moves (T-07-27: zero privileged paths)."*

and `main()` dispatches unconditionally through `args.build(args)` → `_execute(specs, ...)` over
httpx. **Every one of the eight existing nouns returns `RequestSpec`s.** `ccf schema export`
emits JSON Schema from Pydantic models in-process — there is no route to call and no fabric
handle needed. It therefore either (a) needs a new HTTP route to preserve the invariant, or (b)
becomes the first non-`RequestSpec` noun, which requires `main()` to grow a branch before
`_execute`. **Option (b) weakens a stated CLI invariant** ("every action travels the same routes
any client uses") and per CLAUDE.md §15 that is a `D-IMPL-NN`, not a plan-level pick. Flag it.

**CLI tests** live in `tests/cli/test_cli.py` with a `conftest.py`; the D-04 freshness gate is
separately specified by RESEARCH §8 as `tests/cli/test_schema_export.py`.

---

### 7. The `ccf.deployment` → `ccf.products.gates` import ban (D-15A guard, ERGO-02)

**Analog:** the `cinv02-graph-writer` half of `tools/lints/harness_imports.py` — a
module-scoped import ban with a permitted-importer set. This is a *closer* analog than the
harness half because it is the same shape: one forbidden module, an explicit allowlist of
modules that may name it.

**Constants** (`harness_imports.py:78-80`):

```python
#: The concrete GraphWriter module and its permitted importers.
WRITER_MODULE = "ccf.graph._writer"
WRITER_OK_MODULES: frozenset[str] = frozenset({"ccf.assembly", "ccf.boot"})
```

**Check body** (`harness_imports.py:117-130`) — inside the one `ast.walk(tree)`:

```python
            if matches_module(name, (WRITER_MODULE,)) and not matches_module(
                module_name, WRITER_OK_MODULES
            ):
                findings.append(
                    format_finding(
                        path,
                        lineno,
                        RULE_GRAPH_WRITER,
                        f"GraphWriter module {name!r} is importable only from"
                        f" {', '.join(sorted(WRITER_OK_MODULES))}"
                        f" (single-writer invariant, CLAUDE.md §10);"
                        f" {module_name!r} may not name it",
                    )
                )
```

**Module scaffolding** (`harness_imports.py:34-47`): the shared helpers are imported from the
`tools.lints` package —

```python
from tools.lints import (
    format_finding,
    imported_module_names,
    matches_module,
    read_tree,
)

RULE_HARNESS = "cinv02-harness"
RULE_GRAPH_WRITER = "cinv02-graph-writer"
```

and the two-function tail every checker ends with (`harness_imports.py:83, 135-137`;
`algorithmic.py:69, 93-95`):

```python
def check_source(source: str, path: pathlib.Path, module_name: str) -> list[str]: ...

def check(path: pathlib.Path, module_name: str) -> list[str]:
    """Check the Python file at `path`, whose dotted name is `module_name`."""
    return check_source(path.read_text(encoding="utf-8"), path, module_name)
```

`matches_module` is **dot-bounded** (`harness_imports.py:62-65`: "so `adapters_evil` and every
other sibling remain denied") — a `ccf.deployment` ban gets that property for free.

**Governance posture to copy verbatim** (`harness_imports.py:29-31`):

> *"Neither rule takes an allowlist. Carve-outs are module-path constants in this file, reviewed
> with the code, never a data file or per-module opt-out — a data allowlist would void the
> invariant it exists to enforce."*

The D-15A ban is exactly this class of rule and should take no allowlist.

**Registration** — three edits in `tools/lints/__main__.py`: add to the `CHECKERS` dict
(`:61-66`), add a `RULE_TREE_SCOPE` entry (`:47-52`), and add an `--<rule>` `append_const`
argparse flag (`:131-151` pattern). If the ban is folded into the existing `harness_imports`
module as a third rule, only the `RULE_*` constant and the check body are new. **Recommend
folding in** — `harness_imports.py` already carries two rules under one AST walk and its
docstring says so ("Two rules, one AST walk").

---

### 8. `tests` added to `RULE_TREE_SCOPE["no-hardcoding"]` (D-IMPL-78, RULED)

**Analog:** `tools/lints/__main__.py:36-52`. The config surface and its stated rationale:

```python
LINTED_TREES: tuple[str, ...] = ("src", "runtime", "examples")

#: Per-rule tree scoping — the lint posture over ``/examples``, stated in
#: config rather than left to path accident (plan 08-01; ...).
#: ... The exemption is
#: this config surface — not an allowlist entry, and not merely a test
#: assertion. Rules absent from this mapping run over every linted tree.
RULE_TREE_SCOPE: dict[str, tuple[str, ...]] = {
    "no-hardcoding": ("src", "runtime", "examples"),
    "harness-imports": ("src", "runtime"),
    "algorithmic": ("src", "runtime"),
    "orchestration-imports": ("src", "runtime"),
}
```

**Critical catch the planner must not miss:** `run()` (`:98-105`) iterates `LINTED_TREES`, then
filters by `RULE_TREE_SCOPE`. Adding `"tests"` to `RULE_TREE_SCOPE["no-hardcoding"]` alone
**does nothing** — `"tests"` must also be added to `LINTED_TREES`, and the other three rules'
scope tuples must then be checked to confirm they stay off it (they are explicit, so they will).
This is two edits, not one, and RESEARCH §5.6's "one line of config" undercounts it.

**Test analog:** `tests/lints/test_examples_scope.py` — the whole module is the template. It
drives `tools.lints.__main__.run` against synthetic tmp trees, one test per direction:

```python
from tools.lints.__main__ import LINTED_TREES, RULE_TREE_SCOPE, run

def _write(base: pathlib.Path, rel: str, source: str) -> None:
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def test_cinv01_scope_includes_the_examples_tree(tmp_path: pathlib.Path) -> None:
    assert "examples" in LINTED_TREES
    assert "examples" in RULE_TREE_SCOPE["no-hardcoding"]

    _write(tmp_path, "examples/00-quickstart/run.py", PROMPT_LITERAL)
    findings = run(tmp_path, ["no-hardcoding"])
    assert findings, "a prompt-shaped literal in examples/ must be rejected"
    assert any("cinv01a-prompt-shape" in f for f in findings)
```

plus a **regression guard in the opposite direction** (`:68-74`) proving the scope change did
not widen something else. Copy that pairing for the `tests` tree.

Also note `PROMPT_LITERAL` at `:20-25` — a ready-made CINV-01a-tripping fixture string, reusable.

---

### 9. The AST-based gate-independence guard (D-15A, `tests/products/test_gate_independence.py`)

**Analogs:** two, and both contribute. `tests/agents/test_consumption_discipline.py` supplies
the *import-allowlist* half; `tests/invariants/test_adapter_single_writer.py` supplies the
*identifier-scan* half and the honesty discipline.

**Import scan** (`test_consumption_discipline.py:103-130`):

```python
def _ccf_imports(source: str) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(
                alias.name for alias in node.names if alias.name.startswith("ccf")
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("ccf"):
                imported.add(node.module)
    return imported


@pytest.mark.parametrize(
    "module_path", sorted(AGENTS_PACKAGE.glob("*.py")), ids=lambda p: p.name,
)
def test_agents_modules_import_only_the_consumption_surface(module_path: Path) -> None:
    for module in sorted(_ccf_imports(module_path.read_text())):
        assert module.startswith(ALLOWED_CCF_PREFIXES), (
            f"{module_path} imports {module!r}, which is outside the agents"
            " package's permitted consumption surface — no path from Agent"
            " to L1–L5 (AGNT-01; CLAUDE.md §10; DESIGN.md §3.1)"
        )
```

Note `AGENTS_PACKAGE = Path("src/ccf/agents")` (`:46`) and the per-file `parametrize` with
`ids=lambda p: p.name` so a failure names the offending file.

**Identifier scan — the stronger half** (`test_adapter_single_writer.py:128-150`). This is the
one to copy for "no function in `ccf.deployment` constructs both a `ProductLineage` and an
`engine_resolved`-shaped value," because it catches names that are *used* without being
*imported*:

```python
def _identifiers(source: str) -> set[str]:
    """Every name and attribute identifier appearing in ``source``.

    Identifiers, never source text. A text scan cannot tell a violation from a
    docstring that documents compliance — an adapter stating "this holds no
    graph write handle" would fail a grep for the type's name while being
    exactly correct. String constants are not identifiers, so they are outside
    this set and cannot trip it, and a genuine use of the type *is* an
    identifier and cannot escape it.
    """
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.alias):
            names.add(node.asname or node.name.rsplit(".", 1)[-1])
    return names
```

That docstring reasoning is load-bearing and transfers directly: the `ccf.deployment` package
docstring **will** name `run_gates` and `engine_resolved` as its worked example (CONTEXT
`<specifics>`), so a grep-based guard would fail on the very docstring that documents
compliance. **The guard must be identifier-based, not text-based.**

**The vacuity guard** (`test_adapter_single_writer.py:186-192`) — copy this pattern or the whole
suite can go green by discovering nothing:

```python
def test_the_adapter_sources_were_actually_discovered() -> None:
    """A discovery helper that silently returned nothing is the quietest way an
    invariant test stops being one — every parametrized assertion below would
    become vacuously true while staying green."""
    assert len(ADAPTER_SOURCES) >= 7
    found = {path.parent.name for path in ADAPTER_SOURCES}
    assert {"adk", "claude_agent", "langgraph"} <= found
```

**Signature inspection** (`:231-250`) — for asserting the D-07 builder cannot be called without
a `GraphView`, and that no `ccf.deployment` function takes an execution and returns a lineage:

```python
def _annotation_names(annotation: object) -> set[str]:
    """The bare type names an annotation mentions, as whole tokens.

    Whole tokens rather than substrings: ``"Agent" in "agent_name"`` is false
    but ``"Agent" in "AgentDefinition"`` is true ...
    """
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", str(annotation)))


    signature = inspect.signature(type(adapter).__init__)
    for name, parameter in signature.parameters.items():
        if name == "self":
            continue
        named = _annotation_names(parameter.annotation) & CONSTRUCTOR_DENIED_NAMES
        assert not named, (...)
```

**The docstring discipline to copy** (`test_adapter_single_writer.py:10-41`): an explicit
**"What these tests enforce, exactly (D-21)"** section followed by a **"What they do not
enforce"** section. The second section is not optional house style — the I.2 retrospective
flagged overclaiming here specifically. A D-15A guard that overclaims is worse than one that
scopes itself honestly.

**Cross-module constant sharing** (`:68`): `from agents.test_consumption_discipline import
WRITE_SURFACE_NAMES` — *"imported from that module rather than re-listed, so the two checks
cannot drift."* If the gate guard and the import lint both need the forbidden-name set, share it
this way.

---

### 10. Nine parallel `tests/examples/` modules (D-09)

**Analog:** `tests/examples/test_ext00_hardening.py`. The directory already exists with three
modules and an `__init__.py`.

**The load-an-example-module pattern** (`:41-50`) — examples are not packages, so:

```python
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE_DIR = REPO_ROOT / "examples" / "external" / "00-hello-context"


def _load_module(name: str, path: pathlib.Path) -> Any:
    """Load an example module by file path (the example dir is no package)."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_serve() -> Any:
    return _load_module("ext00_serve_under_test", EXAMPLE_DIR / "serve.py")
```

The docstring names the precedent chain explicitly (`:21-23`): *"The example modules are not
packages, so each is loaded by file path with `importlib.util` — the pattern established by
`test_ext00_fixture_schemas.py`."* Nine new modules should say the same about this one.

**Docstring shape** (`:1-20`): a bulleted list of exactly which decision each test pins, then
`Decisions: D-02/D-05/... (Dave, 2026-08-02)`. The D-09 modules should name the assertions they
inherited from the example they replaced, so the "no loss of assertion coverage" claim is
auditable against RESEARCH §1.3's per-file `a+p` counts.

**⚠ The CINV-01 trap (RESEARCH §5.6) has an analog to follow.** Relocated assertions must keep
reading their expected values from artifacts, exactly as
`tests/invariants/test_adapter_single_writer.py:115-125` does:

```python
def _effect_payload() -> dict[str, Any]:
    """A source system's own payload vocabulary, from the event fixture.

    Deliberately a fixture value rather than a literal composed here: L2 has to
    actually resolve it for (a) to observe anything, and a payload this module
    authored would be this module agreeing with itself about what the
    deployment's ontology says.
    """
    stream: dict[str, Any] = yaml.safe_load((FIXTURES / "events.yaml").read_text())
    payload: dict[str, Any] = stream["envelopes"][0]["payload"]
    return payload
```

That is the exact discipline D-09 needs, already written down in a test that is not even in
`tests/examples/`. It is a better argument than a lint-scope change alone — do both.

---

### 11. The example shape (ERGO-13/14/15)

**Analog:** `examples/00-quickstart/` — four parts, all of which the rewrite preserves.

**(a) Directory:** `run.py` + `artifacts/*.yaml` + `README.md`. Quickstart's artifacts are
`controlplane.yaml`, `events.yaml`, `halflife.yaml`, `ontology.yaml` — D-03 splits the last.

**(b) `run.py` module docstring** (`run.py:1-19`), which states the No-Hardcoding claim in the
form that must survive the rewrite:

```
Every domain value — entity classes, source systems, identifiers,
thresholds, policy versions, MAX_TTL, the query, the boundary, the expected
result — is loaded from ``artifacts/*.yaml``. The code below is thin loading
and asserting logic; deleting the artifacts leaves it with nothing
meaningful to run (CLAUDE.md §6.4, the No-Hardcoding Rule).

Run it: ``make example-00`` (or
``PYTHONPATH=src:runtime python examples/00-quickstart/run.py``).
Exit code 0 means every assertion below held; any failure exits nonzero.
```

**Two sentences here go stale under D-09** and must be rewritten, not carried: *"thin loading
and **asserting** logic"* and *"Exit code 0 means every assertion below held."* After D-09 the
assertions are in `tests/`; a docstring still claiming them is a false claim in the file Phase 16
will literal-include.

**(c) Snippet markers** (`run.py:98`, `:120` etc.):

```python
# --8<-- [start:ontology]
def _resolution_spec(ontology: Any) -> EntityResolutionSpec:
    ...
# --8<-- [end:ontology]
```

92 markers across 9 files (RESEARCH §7.3). The `[start:ontology]` and `[start:ingest]` markers
in quickstart bracket **exactly the code D-01/D-03 delete**. The planner must decide per marker:
re-point at the replacement call, or drop the marker and its `public/` include. `make
docs-strict` catches an orphan; it does not catch a marker that still resolves but now brackets
the wrong thing.

**(d) Makefile target** (`Makefile:65-66`, `.PHONY` at `:29-31`, aggregate at `:95`):

```make
example-00: ## Run examples/00-quickstart (reference backends, D-13)
	$(ENV) $(PYTHON) examples/00-quickstart/run.py

examples: example-00 example-01 ... example-ext-00 ## Run all ten examples in order, stopping on first failure
```

Unchanged by this phase — but `make examples` is the CI assertion that the rewrites still run,
and D-09 means it is **no longer** the assertion that they are *correct*. That guarantee moves
to `pytest tests/examples/`. Say so in the plan; a reviewer reading `make ci` will otherwise
assume `examples` still carries it.

**(e) README** (`examples/00-quickstart/README.md`): `## What this demonstrates` →
`## Run it` → (further sections). Bolded CCF terms carry inline glosses plus whitepaper
citations (`**Context Product** — a typed, validated, replay-ready unit of decision context ...
(whitepaper §6.3 (specification), §7.6 (delivery))`). That convention is Phase 14's and must
survive.

---

## Shared Patterns

### Docstring citation discipline
**Sources:** `artifacts.py:1` (whitepaper-derived), `boot.py:1-4` (SDK-defined), `params.py:1-22`
**Apply to:** every new module and public class
Whitepaper-derived: `"""Title (whitepaper §7.8; DESIGN.md §7)."""`. SDK extension:
`"""Title.\n\nSDK-defined mechanism (CLAUDE.md §10; the whitepaper specifies X, not Y)."""`.
Every module ends its docstring with `Algorithmic module (CINV-03).` when tagged.
CLAUDE.md C-11 makes this mandatory, and `ccf.deployment` is an SDK extension throughout.

### The "no default is a value nobody chose" argument
**Source:** `src/ccf/operators/params.py:14-22`
**Apply to:** every new artifact contract's docstring
```
**No field in this module carries a default.** Not a threshold, not a depth
limit, not a score floor, not a flag. Every value is required at plan time
and must arrive from a Control Plane artifact or from the caller. A default
is a value nobody chose, and a value nobody chose cannot be audited, cannot
be versioned, and silently changes the meaning of a replay when the SDK
revises it (D-IMPL-38; CINV-01b enforces this mechanically for modules named
like this one).
```
That last clause is RESEARCH §7.2 Trap 2 made explicit: `PARAM_SCHEMA_MARKERS = ("params",
"parameters", "thresholds")` (`no_hardcoding.py:87`). A `ccf.deployment` module named
`*parameters*` inherits CINV-01b. Name it deliberately.

### Refuse, never repair
**Sources:** `_reject_floats` (`artifacts.py:273-293`), `ArtifactClass.validate`
(`artifacts.py:118-131`), `_open_backend` (`boot.py:113-141`)
**Apply to:** D-02's naive-timestamp refusal, D-08's missing-DSN failure, D-06's glob refusal
The house phrasing pattern is *statement of refusal + the property that would be lost + who owns
the fix*. `ArtifactClass.validate`'s is the tightest: *"A near-miss mapping with the right keys
is still a rejection — structural luck is not a contract."*

### `__all__` + `__ccf_mode__` module header
**Source:** every `/src` module; canonical example `artifacts.py:34-60`
Order: `from __future__ import annotations` → stdlib → third-party → `ccf.*` →
`__ccf_mode__ = "algorithmic"` → `__all__` (sorted) → private constants (`_SEMVER_RE`, `_UNIT`).

### Test module docstring: what it enforces / what it does not
**Source:** `tests/invariants/test_adapter_single_writer.py:10-41`
**Apply to:** `test_gate_independence.py`, `test_operator_builder.py`, `test_manifest.py`
The strongest convention in the test tree and the one most relevant to a phase whose central
risk is silently weakening an invariant.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| class-id → `ArtifactClass` lookup | registry | transform | **Verified negative** — `artifacts.py` has no registry structure at all (RESEARCH §2.1, confirmed by full re-read). `tools/lints/__main__.py::CHECKERS` is a defensible `dict[str, T]` shape but has no fallthrough semantics and no sync obligation. Treat as new design. |
| `ccf schema export` as a non-`RequestSpec` CLI noun | CLI command | file-I/O | All eight existing nouns return `RequestSpec`s and `main()` has no other dispatch path. A local-generation noun is unprecedented and **breaks a stated CLI invariant** (`main.py:1-6`). Not a missing pattern — a missing decision. Surface as `D-IMPL-NN`. |

---

## Metadata

**Analog search scope:** `src/ccf/` (controlplane, operators, boot, assembly, products),
`runtime/ccf_runtime/cli/`, `tools/` (lints, dump_openapi), `tests/` (lints, invariants, agents,
http_api, examples, cli), `examples/00-quickstart/`, `Makefile`
**Files read in full:** `src/ccf/controlplane/artifacts.py`, `tools/lints/harness_imports.py`,
`tools/lints/algorithmic.py`, `tools/lints/__main__.py`, `tools/dump_openapi.py`,
`tests/http_api/test_openapi.py`, `tests/lints/test_examples_scope.py`,
`tests/agents/test_consumption_discipline.py`, `tests/invariants/test_adapter_single_writer.py`,
`runtime/ccf_runtime/cli/main.py`, `runtime/ccf_runtime/cli/commands/config.py`,
`runtime/ccf_runtime/cli/commands/__init__.py`
**Files read in part:** `src/ccf/boot.py` (1-60), `src/ccf/operators/params.py` (1-114),
`src/ccf/assembly/worker.py` (60-120), `examples/00-quickstart/run.py` (1-140),
`tests/examples/test_ext00_hardening.py` (1-60), `Makefile` (example + openapi targets)
**Pattern extraction date:** 2026-08-04
