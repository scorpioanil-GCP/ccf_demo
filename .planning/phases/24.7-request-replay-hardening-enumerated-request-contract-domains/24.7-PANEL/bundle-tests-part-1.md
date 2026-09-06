# 24.7 close-time panel — bundle-tests-part-1.md

Subject: the SHIPPED tree of `phase-24.7` at `ad8dc5a9` (tests/, perf/, tools/, pyproject.toml), diff base `6a019322`.
Read `prompt.md` for the instruction and `known-findings.md` for what NOT to re-derive.
Feed this file via STDIN, never as an argv string. Quote the line below verbatim in your review;
a review that does not quote it is recorded as a failed reviewer, not a reviewer.

```
READ-PROOF bundle-tests-part-1.md: 7fef7e412f4016c6
```

Subjects in this part (29): `tests/products/test_request_schema_render.py`, `tests/lints/test_archived_examples_non_gating.py`, `perf/suites/replay/conftest.py`, `pyproject.toml`, `tests/authz/test_delivery_boundary.py`, `tests/conformance/test_harness_adapter.py`, `tests/conformance/test_harness_portability.py`, `tests/conftest.py`, `tests/contracts/test_hash_transparency.py`, `tests/crossproc/servers/mcp_egress_child.py`, `tests/crossproc/servers/mcp_experience_child.py`, `tests/crossproc/servers/mcp_hitl_child.py`, `tests/hitl/test_replay_e2e.py`, `tests/http_api/conftest.py`, `tests/http_api/test_hitl_door_identity.py`, `tests/http_api/test_product_declared_obligation_409.py`, `tests/http_api/test_product_disclosure.py`, `tests/integration/test_agent_slice.py`, `tests/integration/test_proto_quickstart.py`, `tests/mcp/test_egress_disclosure.py`, `tests/mcp/test_egress_listing.py`, `tests/mcp/test_egress_refusal_channels.py`, `tests/mcp/test_egress_refusal_envelope.py`, `tests/mcp/test_experience_refusal_channels.py`, `tests/perf_smoke/test_smoke.py`, `tests/products/test_delivery_determinism.py`, `tests/products/test_disclosure.py`, `tests/products/test_policy_constraint_resolver.py`, `tests/products/test_policy_constraints.py`

## tests/products/test_request_schema_render.py — NEW MODULE, FULL TEXT

```python
"""The canonical request-contract render — representation without delivery.

``D-IMPL-264`` D-00 (*one declaration of record*), D-02 as amended by
amendment 1 F-5 d, and principle P-1. Dave, verbatim: *"The legal set is
intrinsically advertisable contract truth and must have a canonical SDK
rendering. 24.7 does not invent the Experience Layer surface on which that
rendering is published."* And P-1: *"The request contract is the authority
for legal values; schemas and discovery advertise that authority but never
independently define it."*

What is asserted here, and nothing more:

* the render composes :meth:`ccf.skills.catalog.SkillArgumentSchema.to_input_schema`
  with :attr:`ccf.products.request.ProductRequestContract.argument_domains` —
  an enumerated domain becomes ``enum``, numeric bounds become ``minimum`` /
  ``maximum`` — and a contract with no domains renders byte-identically to
  the argument schema alone;
* the render reads :class:`~ccf.products.request.ArgumentDomain` ONLY: a
  second declaration planted on the base render is refused, not merged;
* the render takes the contract and nothing else — no consumer-side
  conditioning parameter exists to gate what a caller may learn before
  asking, because request validity is not a per-caller matter (D-02).

Nothing here publishes anything: no MCP tool, no HTTP route, no CLI verb
serves the render. That surface is carry row ``24.7-C-01``, deferred by
ruling. Criterion 8.
"""

from __future__ import annotations

import inspect
import json
from decimal import Decimal
from typing import Any

import pytest

from ccf.products.request import ArgumentDomain, ProductRequestContract
from ccf.skills.catalog import (
    SkillArgumentElement,
    SkillArgumentMember,
    SkillArgumentProperty,
    SkillArgumentSchema,
)

CLASS_NAME = "fixture.render"
CLASS_VERSION = "1.0.0"

REQUIRED_LEAF = "required_leaf"
OPTIONAL_LEAF = "optional_leaf"
FLAG = "flag"
RATIO = "ratio"


def _arguments() -> SkillArgumentSchema:
    """A declared parameter surface over every primitive type plus a nest."""
    return SkillArgumentSchema(
        properties={
            REQUIRED_LEAF: SkillArgumentProperty(
                type="string", description="a required top-level parameter"
            ),
            OPTIONAL_LEAF: SkillArgumentProperty(
                type="integer", description="an optional top-level parameter"
            ),
            FLAG: SkillArgumentProperty(type="boolean", description="a flag"),
            RATIO: SkillArgumentProperty(type="number", description="a ratio"),
            "nested": SkillArgumentProperty(
                type="object",
                description="a one-level nested parameter",
                properties={
                    "member": SkillArgumentMember(
                        type="string", description="a nested member"
                    )
                },
                required=("member",),
            ),
            "listed": SkillArgumentProperty(
                type="array",
                description="a list of objects",
                items=SkillArgumentElement(
                    type="object",
                    description="one element",
                    properties={
                        "element_member": SkillArgumentMember(
                            type="string", description="an element member"
                        )
                    },
                    required=("element_member",),
                ),
            ),
        },
        required=(REQUIRED_LEAF,),
    )


def _contract(**overrides: Any) -> ProductRequestContract:
    fields: dict[str, Any] = {
        "semver": "1.0.0",
        "schema_name": CLASS_NAME,
        "schema_version": CLASS_VERSION,
        "arguments": _arguments(),
    }
    fields.update(overrides)
    return ProductRequestContract(**fields)


def _render(contract: ProductRequestContract) -> dict[str, Any]:
    from ccf.products.request_schema import render_request_input_schema

    return render_request_input_schema(contract)


def _canonical(document: dict[str, Any]) -> str:
    return json.dumps(document, sort_keys=True)


# --- (1) no domains: the render IS the argument schema -----------------------


def test_a_contract_with_no_domains_renders_byte_identically_to_the_argument_schema() -> None:
    """P-1's null case: with nothing to derive, nothing is authored."""
    contract = _contract()
    rendered = _render(contract)
    base = contract.arguments.to_input_schema()

    assert rendered == base
    assert _canonical(rendered) == _canonical(base)
    # And the closed-world keys are the argument schema's own, untouched.
    assert rendered["additionalProperties"] is False
    assert rendered["required"] == [REQUIRED_LEAF]
    assert rendered["properties"]["nested"]["additionalProperties"] is False
    assert (
        rendered["properties"]["listed"]["items"]["additionalProperties"] is False
    )


# --- (2) an enumerated domain renders its members as `enum` ------------------


@pytest.mark.parametrize(
    ("parameter", "members", "expected"),
    [
        (REQUIRED_LEAF, ("alpha", "beta"), ["alpha", "beta"]),
        (OPTIONAL_LEAF, (1, 2), [1, 2]),
        (FLAG, (True,), [True]),
        (RATIO, (Decimal("0.5"), Decimal("2")), [0.5, 2]),
    ],
    ids=["string", "integer", "boolean", "number"],
)
def test_an_enumerated_domain_renders_its_members_as_enum(
    parameter: str, members: tuple[Any, ...], expected: list[Any]
) -> None:
    """Members in declared order; an integral Decimal renders as an int.

    ``D-IMPL-264`` D-06 (Dave: *"Any supported primitive type ... Don't
    unnecessarily make this string-specific."*). The Decimal rule — integral
    → ``int``, otherwise ``float`` — is pinned HERE so a later renderer
    cannot quietly emit ``"2"`` or ``2.0`` and still pass.
    """
    contract = _contract(argument_domains={parameter: ArgumentDomain(members=members)})
    rendered = _render(contract)
    base = contract.arguments.to_input_schema()

    property_rendered = rendered["properties"][parameter]
    assert property_rendered["enum"] == expected
    assert [type(value) for value in property_rendered["enum"]] == [
        type(value) for value in expected
    ]
    assert "minimum" not in property_rendered
    assert "maximum" not in property_rendered
    # Everything else on the property is the base render's, exactly.
    assert {k: v for k, v in property_rendered.items() if k != "enum"} == (
        base["properties"][parameter]
    )
    # And no OTHER property moved.
    for name, spec in base["properties"].items():
        if name != parameter:
            assert rendered["properties"][name] == spec, name
    assert rendered["required"] == base["required"]
    assert rendered["additionalProperties"] is base["additionalProperties"]
    assert rendered["type"] == base["type"]
    # The render is JSON-legal as rendered: `json.dumps` accepts it whole.
    assert json.loads(_canonical(rendered))["properties"][parameter]["enum"] == (
        expected
    )


# --- (3) numeric bounds render `minimum` / `maximum` -------------------------


@pytest.mark.parametrize(
    ("domain", "expected"),
    [
        (ArgumentDomain(minimum=Decimal("1")), {"minimum": 1}),
        (ArgumentDomain(maximum=Decimal("100")), {"maximum": 100}),
        (
            ArgumentDomain(minimum=Decimal("0.25"), maximum=Decimal("1")),
            {"minimum": 0.25, "maximum": 1},
        ),
    ],
    ids=["floor-only", "ceiling-only", "both"],
)
def test_numeric_bounds_render_minimum_and_maximum(
    domain: ArgumentDomain, expected: dict[str, Any]
) -> None:
    """An absent end is not emitted; the Decimal rule is the enum rule."""
    contract = _contract(argument_domains={OPTIONAL_LEAF: domain})
    rendered = _render(contract)
    base = contract.arguments.to_input_schema()

    property_rendered = rendered["properties"][OPTIONAL_LEAF]
    for key in ("minimum", "maximum"):
        if key in expected:
            assert property_rendered[key] == expected[key]
            assert type(property_rendered[key]) is type(expected[key])
        else:
            assert key not in property_rendered
    assert "enum" not in property_rendered
    assert {
        k: v for k, v in property_rendered.items() if k not in ("minimum", "maximum")
    } == base["properties"][OPTIONAL_LEAF]


def test_two_domains_render_side_by_side() -> None:
    contract = _contract(
        argument_domains={
            REQUIRED_LEAF: ArgumentDomain(members=("alpha",)),
            OPTIONAL_LEAF: ArgumentDomain(minimum=Decimal("1")),
        }
    )
    rendered = _render(contract)
    assert rendered["properties"][REQUIRED_LEAF]["enum"] == ["alpha"]
    assert rendered["properties"][OPTIONAL_LEAF]["minimum"] == 1


# --- (4) the render reads ArgumentDomain ONLY (P-1) --------------------------


def _planting(key: str, value: Any, *, on: str) -> Any:
    """A `to_input_schema` that carries a second declaration on one property."""
    real = SkillArgumentSchema.to_input_schema

    def planted(self: SkillArgumentSchema) -> dict[str, Any]:
        rendered = real(self)
        rendered["properties"][on][key] = value
        return rendered

    return planted


@pytest.mark.parametrize(
    ("key", "value"), [("enum", ["planted"]), ("minimum", 0), ("maximum", 9)]
)
@pytest.mark.parametrize(
    "on", [REQUIRED_LEAF, OPTIONAL_LEAF], ids=["domained", "not-domained"]
)
def test_the_render_reads_argument_domains_only_and_refuses_a_planted_enum(
    monkeypatch: pytest.MonkeyPatch, key: str, value: Any, on: str
) -> None:
    """A second declaration is refused by name, wherever it is planted.

    P-1: *"schemas ... never independently define it."* On a domained
    property the plant would compete with the declaration of record; on a
    property with no domain it would BE a declaration the contract never
    made. Both are refused, because the base render is not a declaration
    surface for legal values at all. The message names the property and the
    principle.
    """
    monkeypatch.setattr(
        SkillArgumentSchema, "to_input_schema", _planting(key, value, on=on)
    )
    contract = _contract(
        argument_domains={REQUIRED_LEAF: ArgumentDomain(members=("alpha", "beta"))}
    )
    # The plant is live: the base render now carries the second declaration.
    assert key in contract.arguments.to_input_schema()["properties"][on]

    with pytest.raises(ValueError) as caught:
        _render(contract)
    message = str(caught.value)
    assert on in message
    assert key in message
    assert "one declaration of record" in message


def test_the_control_plants_nothing_when_not_asked() -> None:
    """The positive half of the control: unpatched, no property carries any of
    the three derived keys, so the refusal above is measuring the plant."""
    base = _contract().arguments.to_input_schema()
    for name, spec in base["properties"].items():
        for key in ("enum", "minimum", "maximum"):
            assert key not in spec, (name, key)


# --- (5) the render takes the contract and nothing else ----------------------


def test_the_render_takes_the_contract_and_nothing_else() -> None:
    """D-02's structural form: no parameter could condition what is advertised.

    Dave: *"A caller should be able to know the valid vocabulary before
    making the request ... don't make request validity disclosure-dependent
    here."* A second parameter — whatever its name — would be the place such
    a dependence would be introduced, so the signature is pinned to one.
    """
    from ccf.products.request_schema import render_request_input_schema

    assert list(inspect.signature(render_request_input_schema).parameters) == [
        "contract"
    ]


def test_the_render_does_not_mutate_the_contract() -> None:
    contract = _contract(
        argument_domains={REQUIRED_LEAF: ArgumentDomain(members=("alpha",))}
    )
    before = contract.model_dump()
    _render(contract)
    assert contract.model_dump() == before


def test_the_module_publishes_nothing_and_exports_one_name() -> None:
    """Criterion 9's in-tree half: one export, algorithmic, no consumer."""
    import ccf.products.request_schema as module

    assert module.__all__ == ["render_request_input_schema"]
    assert module.__ccf_mode__ == "algorithmic"
```

## tests/lints/test_archived_examples_non_gating.py — NEW MODULE, FULL TEXT

```python
"""Archive runners are marked ``archived``, and only archive runners are — D-IMPL-265.

Dave's ruling (2026-09-06, verbatim in ``24.7-RULINGS.md`` §10): *"archive/examples/
contains retired examples whose usage model is not supported guidance. They are
preserved for historical/technical reference but are not compatibility consumers
of the current SDK. No archived source is modified to accommodate 24.7. Tests whose
only purpose is exercising those retired examples are removed from the
release-gating denominator or explicitly marked archived/non-gating. HW/CP
examples remain the supported example and diagnostic surfaces."*

The harness realizes that as a registered ``archived`` marker (``pyproject.toml``)
and a root-``conftest`` hook that DESELECTS marked items unless ``--run-archived``
is passed (``tests/conftest.py``). What this module defends is the category
boundary, in both directions:

* **Every archive RUNNER carries the marker.** A test module that executes a
  retired program — loads it with ``importlib.util.spec_from_file_location`` /
  ``runpy`` or spawns it with ``subprocess`` / a ``_spawn`` helper — and whose
  target is one of the archive's program entry points (``run.py``, ``serve.py``,
  ``producer_child.py``: the three files that hold the twelve archived
  ``build_replay_record`` sites D-IMPL-265 names) must be marked at module level.
  An unmarked runner would put a retired example back into the release gate.
* **Only archive runners carry the marker.** A marked module that does not
  execute an archive program would be hiding a live SDK test behind the
  non-gating category. Guards that merely *read* the archive — retirement
  guards, schema-header gates, README-template readers, the demo-generator and
  fixture-schema smoke tests — are the supported surface's own tests and stay
  gating.

The classifier is one AST walk with three independent kinds of evidence (an
``archive/examples`` path expression, a load-or-spawn call, a program-file
target), and a module is a runner only when all three are present; the
evidence is reported on failure so a misclassification is arguable from the
message. Docstrings are excluded from the evidence — a test that *describes*
an archive path in prose is not executing it. The controls below run the same
classifier over synthetic modules so a silent AST-pattern drift cannot pass
this guard vacuously.

The ``crossproc`` perf-smoke parameter is the one non-module case: the perf
battery's crossproc suite spawns ``archive/examples/04-cross-process/
producer_child.py`` (carry row ``24.7-C-02``), so its smoke parameter carries
the marker — and the rule here is derived, not pinned: a suite's parameter is
marked exactly when a module under ``perf/suites/<suite>/`` is an archive
runner. The day that suite is re-pointed at a supported child, this test says
the mark must come off.

This module deliberately spells the archive prefix as a component tuple and
never joins it into one literal, so the classifier does not read the guard's
own constants as an archive path.
"""

from __future__ import annotations

import ast
import os
import pathlib
import subprocess
import sys
import tomllib
from dataclasses import dataclass

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
TESTS_ROOT = REPO_ROOT / "tests"
PERF_SUITES_ROOT = REPO_ROOT / "perf" / "suites"
PERF_SMOKE = TESTS_ROOT / "perf_smoke" / "test_smoke.py"
PYPROJECT = REPO_ROOT / "pyproject.toml"

#: The marker D-IMPL-265 registers, and the option that re-includes it.
MARKER = "archived"
RUN_ARCHIVED_OPTION = "--run-archived"

#: The retired tree, as path components — see the module docstring for why
#: these are never joined into a single literal here.
ARCHIVE_PREFIX: tuple[str, str] = ("archive", "examples")

#: The archive's program entry points: the files that hold the twelve archived
#: builder sites D-IMPL-265 names (00..08 ``run.py``, ``04-cross-process/
#: producer_child.py``, ``external/00-hello-context/serve.py``). Loading or
#: spawning one of these is "exercising the retired example"; loading a helper
#: beside them (``generator.py``, ``replay_server.py``) is not.
PROGRAMS: frozenset[str] = frozenset({"run.py", "serve.py", "producer_child.py"})

#: Calls that execute a module by path.
LOADERS: frozenset[str] = frozenset(
    {"spec_from_file_location", "exec_module", "run_path", "run_module"}
)
#: ``subprocess`` calls that spawn a program.
SPAWNERS: frozenset[str] = frozenset({"run", "Popen", "call", "check_call", "check_output"})
#: Example-side spawn helpers (``run_module._spawn("serve.py", ...)``).
SPAWN_HELPERS: frozenset[str] = frozenset({"_spawn"})


@dataclass(frozen=True)
class Classification:
    """One module's evidence, each kind as ``what:line`` strings."""

    path: str
    archive_paths: tuple[str, ...]
    programs: tuple[str, ...]
    executes: tuple[str, ...]
    marked: bool

    @property
    def is_runner(self) -> bool:
        return bool(self.archive_paths and self.programs and self.executes)

    def evidence(self) -> str:
        return (
            f"{self.path}: archive_paths={list(self.archive_paths)} "
            f"programs={list(self.programs)} executes={list(self.executes)} "
            f"marked={self.marked}"
        )


def _docstring_ids(tree: ast.AST) -> set[int]:
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                ids.add(id(body[0].value))
    return ids


def _div_chain(node: ast.BinOp) -> list[str]:
    """Flatten ``a / "b" / "c"`` into its components, left to right."""
    parts: list[str] = []
    cursor: ast.expr = node
    while isinstance(cursor, ast.BinOp) and isinstance(cursor.op, ast.Div):
        right = cursor.right
        parts.append(right.value if isinstance(right, ast.Constant) and isinstance(right.value, str) else "<expr>")
        cursor = cursor.left
    parts.append(cursor.value if isinstance(cursor, ast.Constant) and isinstance(cursor.value, str) else "<expr>")
    parts.reverse()
    return parts


def _has_archive_prefix(components: list[str]) -> bool:
    return any(
        tuple(components[i : i + len(ARCHIVE_PREFIX)]) == ARCHIVE_PREFIX
        for i in range(len(components) - len(ARCHIVE_PREFIX) + 1)
    )


def _call_name(node: ast.Call) -> tuple[str | None, str]:
    """``(base, attr)`` for ``base.attr(...)``; ``(None, name)`` for ``name(...)``."""
    func = node.func
    if isinstance(func, ast.Attribute):
        base = func.value
        if isinstance(base, ast.Name):
            return base.id, func.attr
        if isinstance(base, ast.Attribute):
            return base.attr, func.attr
        return "<expr>", func.attr
    if isinstance(func, ast.Name):
        return None, func.id
    return "<expr>", "<expr>"


def _marked_archived(tree: ast.Module) -> bool:
    """A module-level ``pytestmark = pytest.mark.archived`` (or a list holding it)."""
    for statement in tree.body:
        if not isinstance(statement, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in statement.targets):
            continue
        for node in ast.walk(statement.value):
            if (
                isinstance(node, ast.Attribute)
                and node.attr == MARKER
                and isinstance(node.value, ast.Attribute)
                and node.value.attr == "mark"
                and isinstance(node.value.value, ast.Name)
                and node.value.value.id == "pytest"
            ):
                return True
    return False


def classify(path: pathlib.Path, root: pathlib.Path = REPO_ROOT) -> Classification:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    docstrings = _docstring_ids(tree)
    joined_prefix = "/".join(ARCHIVE_PREFIX)
    archive_paths: dict[int, str] = {}
    programs: list[str] = []
    executes: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            components = _div_chain(node)
            if _has_archive_prefix(components):
                joined = "/".join(components)
                # Keep the longest chain per line: sub-chains of one expression
                # are also BinOps and would otherwise repeat as shorter prefixes.
                if len(joined) > len(archive_paths.get(node.lineno, "")):
                    archive_paths[node.lineno] = f"{joined}:{node.lineno}"
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in docstrings:
                continue
            if joined_prefix in node.value:
                archive_paths.setdefault(node.lineno, f"{node.value[:72]!r}:{node.lineno}")
            if node.value.rsplit("/", 1)[-1] in PROGRAMS:
                programs.append(f"{node.value}:{node.lineno}")
        elif isinstance(node, ast.Call):
            base, name = _call_name(node)
            if name in LOADERS or name in SPAWN_HELPERS:
                executes.append(f"{base + '.' if base else ''}{name}:{node.lineno}")
            elif name in SPAWNERS and base == "subprocess":
                executes.append(f"subprocess.{name}:{node.lineno}")

    return Classification(
        path=path.relative_to(root).as_posix(),
        archive_paths=tuple(archive_paths[k] for k in sorted(archive_paths)),
        programs=tuple(programs),
        executes=tuple(executes),
        marked=_marked_archived(tree),
    )


def _python_modules(tree_root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(
        p for p in tree_root.rglob("*.py") if "__pycache__" not in p.parts and p.is_file()
    )


def classify_tree(tree_root: pathlib.Path, root: pathlib.Path = REPO_ROOT) -> dict[str, Classification]:
    return {c.path: c for c in (classify(p, root) for p in _python_modules(tree_root))}


# --- The guard --------------------------------------------------------------------


def test_every_archive_runner_is_marked_and_only_archive_runners_are() -> None:
    """Set equality between "executes an archive program" and "marked archived".

    Both directions are stated: an unmarked runner drags a retired example back
    into the release gate; a marked non-runner hides a live SDK test behind the
    non-gating category. The failure names every offender with its evidence.
    """
    table = classify_tree(TESTS_ROOT)
    runners = {path for path, c in table.items() if c.is_runner}
    marked = {path for path, c in table.items() if c.marked}
    assert runners, "the classifier found no archive runner under tests/ — vacuous"
    unmarked_runners = sorted(runners - marked)
    marked_non_runners = sorted(marked - runners)
    assert not unmarked_runners and not marked_non_runners, (
        "D-IMPL-265: archive runners must carry `pytestmark = pytest.mark.archived`, "
        "and nothing else may\n"
        "unmarked runners (execute an archive program, no marker):\n  "
        + "\n  ".join(table[p].evidence() for p in unmarked_runners)
        + "\nmarked non-runners (marker, but no archive program executed):\n  "
        + "\n  ".join(table[p].evidence() for p in marked_non_runners)
    )


def test_the_perf_smoke_parameter_is_marked_exactly_for_the_suites_that_run_the_archive() -> None:
    """Derived, not pinned: a suite's smoke parameter is ``archived`` iff a module
    under ``perf/suites/<suite>/`` executes an archive program (``24.7-C-02``)."""
    tree = ast.parse(PERF_SMOKE.read_text(encoding="utf-8"), filename=str(PERF_SMOKE))
    suites: dict[str, bool] = {}
    for statement in tree.body:
        if not (
            isinstance(statement, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "SUITES" for t in statement.targets)
        ):
            continue
        assert isinstance(statement.value, (ast.Tuple, ast.List))
        for element in statement.value.elts:
            if isinstance(element, ast.Constant) and isinstance(element.value, str):
                suites[element.value] = False
            elif isinstance(element, ast.Call) and _call_name(element) == ("pytest", "param"):
                first = element.args[0]
                assert isinstance(first, ast.Constant) and isinstance(first.value, str)
                marks = [k.value for k in element.keywords if k.arg == "marks"]
                suites[first.value] = any(
                    isinstance(n, ast.Attribute) and n.attr == MARKER
                    for m in marks
                    for n in ast.walk(m)
                )
            else:  # pragma: no cover — a shape this guard cannot read must fail loudly
                raise AssertionError(f"unreadable SUITES element at line {element.lineno}")
    assert suites, f"no SUITES assignment found in {PERF_SMOKE}"

    should_be_marked = {
        suite: any(c.is_runner for c in classify_tree(PERF_SUITES_ROOT / suite).values())
        for suite in suites
    }
    assert suites == should_be_marked, (
        "D-IMPL-265 / 24.7-C-02: the smoke parameter carries `archived` exactly when its "
        f"suite executes an archive program\n  marked now: {suites}\n  should be: {should_be_marked}"
    )
    assert any(should_be_marked.values()), "no perf suite executes the archive — vacuous"


def test_the_marker_is_registered_citing_the_ruling() -> None:
    markers = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["tool"]["pytest"][
        "ini_options"
    ]["markers"]
    registered = [m for m in markers if m.startswith(f"{MARKER}:")]
    assert len(registered) == 1, f"expected one `{MARKER}:` marker, found {registered}"
    assert "D-IMPL-265" in registered[0] and RUN_ARCHIVED_OPTION in registered[0]


def test_the_hook_deselects_by_default_and_run_archived_reincludes() -> None:
    """The hook as executed: one runner module collected in a child pytest,
    with and without the option. The module is the classifier's first runner,
    so this test pins no file name of its own."""
    table = classify_tree(TESTS_ROOT)
    runner = sorted(p for p, c in table.items() if c.is_runner)[0]

    def collect(*extra: str) -> str:
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", runner, "--collect-only", "-q", "-p", "no:cacheprovider", *extra],
            cwd=REPO_ROOT,
            env=dict(os.environ),
            capture_output=True,
            text=True,
            check=False,
        )
        return completed.stdout + completed.stderr

    default = collect()
    assert " deselected" in default, f"default collection of {runner} did not deselect:\n{default}"
    assert "::" not in default, f"default collection of {runner} still lists ids:\n{default}"

    reincluded = collect(RUN_ARCHIVED_OPTION)
    assert " deselected" not in reincluded, f"{RUN_ARCHIVED_OPTION} still deselected:\n{reincluded}"
    assert f"{runner}::" in reincluded, f"{RUN_ARCHIVED_OPTION} collected no id from {runner}:\n{reincluded}"


# --- Controls: the classifier on synthetic modules ---------------------------------


def _write(base: pathlib.Path, rel: str, source: str) -> pathlib.Path:
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


_RUNNER = (
    "import importlib.util\nimport pathlib\nimport pytest\n"
    "REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]\n"
    'EXAMPLE = REPO_ROOT / "archive" / "examples" / "00-quickstart" / "run.py"\n'
    "def load():\n"
    '    spec = importlib.util.spec_from_file_location("x", EXAMPLE)\n'
    "    return spec\n"
)
_MARK = "pytestmark = pytest.mark.archived\n"
_READER = (
    "import pathlib\n"
    "REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]\n"
    'SOURCE = REPO_ROOT / "archive" / "examples" / "external" / "00-hello-context" / "run.py"\n'
    "def test_reads():\n"
    '    assert "README_HEADINGS" in SOURCE.read_text()\n'
)
_HELPER_LOADER = (
    "import importlib.util\nimport pathlib\n"
    "REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]\n"
    'EXAMPLE_DIR = REPO_ROOT / "archive" / "examples" / "08-e2e-demo"\n'
    "def load():\n"
    '    return importlib.util.spec_from_file_location("g", EXAMPLE_DIR / "generator.py")\n'
)
_PROSE_ONLY = (
    '"""Describes ' + "/".join(ARCHIVE_PREFIX) + '/00-quickstart/run.py, never touches it."""\n'
    "import subprocess\n"
    "def test_git():\n"
    '    subprocess.run(["git", "log", "--", "run.py"], check=True)\n'
)


def test_control_an_unmarked_runner_is_a_runner_and_a_marked_one_is_marked(
    tmp_path: pathlib.Path,
) -> None:
    unmarked = classify(_write(tmp_path, "tests/x/test_runner.py", _RUNNER), tmp_path)
    assert unmarked.is_runner and not unmarked.marked, unmarked.evidence()
    marked = classify(_write(tmp_path, "tests/x/test_marked.py", _RUNNER + _MARK), tmp_path)
    assert marked.is_runner and marked.marked, marked.evidence()


def test_control_readers_helper_loaders_and_prose_are_not_runners(
    tmp_path: pathlib.Path,
) -> None:
    """Each negative control lacks exactly one of the three evidence kinds."""
    reader = classify(_write(tmp_path, "tests/x/test_reader.py", _READER), tmp_path)
    assert reader.archive_paths and reader.programs and not reader.executes, reader.evidence()
    helper = classify(_write(tmp_path, "tests/x/test_helper.py", _HELPER_LOADER), tmp_path)
    assert helper.archive_paths and helper.executes and not helper.programs, helper.evidence()
    prose = classify(_write(tmp_path, "tests/x/test_prose.py", _PROSE_ONLY), tmp_path)
    assert prose.executes and prose.programs and not prose.archive_paths, prose.evidence()
    assert not any(c.is_runner for c in (reader, helper, prose))


def test_control_the_guard_reds_on_a_planted_unmarked_runner(tmp_path: pathlib.Path) -> None:
    """The set-equality check, driven over a synthetic tests/ tree."""
    _write(tmp_path, "tests/x/test_planted.py", _RUNNER)
    _write(tmp_path, "tests/x/test_marked.py", _RUNNER + _MARK)
    table = classify_tree(tmp_path / "tests", tmp_path)
    runners = {p for p, c in table.items() if c.is_runner}
    marked = {p for p, c in table.items() if c.marked}
    assert runners - marked == {"tests/x/test_planted.py"}
    assert marked - runners == set()
```

## perf/suites/replay/conftest.py — diff 6a019322..HEAD (M)

```diff
diff --git a/perf/suites/replay/conftest.py b/perf/suites/replay/conftest.py
index c4348b87..f9398480 100644
--- a/perf/suites/replay/conftest.py
+++ b/perf/suites/replay/conftest.py
@@ -65,6 +65,7 @@ from ccf.projection.plan import Perspective, ProjectionOutput  # noqa: E402
 from ccf.replay.record import (  # noqa: E402
     DecisionReplayRecord,
     PolicyBinding,
+    ResolutionNotApplicable,
     build_replay_record,
 )
 from ccf.replay.serve import ReplayWriter  # noqa: E402
@@ -269,6 +270,10 @@ def recorded_decision(fabric_1k: Any) -> RecordedDecision:
         ),
         assembly_mode=declared_class["assembly_mode"],
         recorded_at=now,
+        # 24.7-06 (D-IMPL-264 D-09/D-10): this perf fixture serves a fabric-
+        # direct decision and runs no resolution step, so it states the typed
+        # not-applicable marker the builder now requires.
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
     )
     return RecordedDecision(
         tenant_id=tenant_id,
```

## pyproject.toml — diff 6a019322..HEAD (M)

```diff
diff --git a/pyproject.toml b/pyproject.toml
index da920783..5282fb6c 100644
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -149,6 +149,7 @@ markers = [
   "conformance: shared parametrized Protocol conformance suite — D-16",
   "crossproc: spawns real subprocesses over loopback — D-15/D-16",
   "harness: requires a harness extra (adk | claude-agent | langgraph) — D-08/D-09",
+  "archived: exercises a retired program under archive/examples/ — retired usage-model history, not a compatibility consumer of the SDK; deselected unless --run-archived — D-IMPL-265",
 ]
 
 # `runtime` joins `src` here per 06-RESEARCH.md finding B2: the majority of Phase I.3's
```

## tests/authz/test_delivery_boundary.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/authz/test_delivery_boundary.py b/tests/authz/test_delivery_boundary.py
index 0f2eed77..19f4b893 100644
--- a/tests/authz/test_delivery_boundary.py
+++ b/tests/authz/test_delivery_boundary.py
@@ -72,13 +72,16 @@ from ccf.projection.plan import Perspective
 from ccf.replay.record import (
     NO_FABRIC_READ,
     NO_PRODUCT_ADDRESS,
+    NO_REQUEST_RESOLUTION,
     NO_ROLE_RESOLVED,
     DecisionReplayRecord,
+    ResolutionNotApplicable,
 )
 from ccf_runtime.authz.delivery_boundary import (
     SURFACE_HTTP_ROUTE,
     SURFACE_MCP_RESOURCE,
     UnrecordableDeliveryBoundaryError,
+    govern_absence,
     govern_entitlement,
     recorded_boundary,
 )
@@ -475,6 +478,71 @@ def test_an_unregistered_tenants_denial_names_the_absence_and_pins_nothing(
     assert shell.fields["error_code"] == '"undisclosed"'
 
 
+# --- 24.7-04: a boundary denial states that resolution never began ----------
+
+
+REFUSED_BEFORE_RESOLUTION = ResolutionNotApplicable(
+    reason="refused-before-resolution"
+)
+
+
+def _resolution_state_of(record: DecisionReplayRecord) -> ResolutionNotApplicable:
+    rendered = record.policy_bindings.request_resolution
+    assert rendered != NO_REQUEST_RESOLUTION, rendered
+    return ResolutionNotApplicable.model_validate_json(rendered)
+
+
+def test_an_entitlement_denial_states_it_was_refused_before_resolution_began(
+    fixture: _Fixture,
+) -> None:
+    """``D-IMPL-264`` D-09 and D-10 at the door: an entitlement denial is
+    decided before any resolver runs, and its record SAYS so — the typed
+    marker with the reason ``refused-before-resolution`` on dimension 2,
+    never the legacy sentinel and never an inferred absence.
+
+    What would fail here: a denial whose dimension 2 read exactly like a
+    record whose caller dropped the resolution (the sentinel), or a
+    marker with the wrong reason (``no-resolution-step`` is the direct
+    validator's claim, not the door's).
+    """
+    shell = fixture.govern(product_class=OTHER_PRODUCT_CLASS)
+    assert isinstance(shell, RefusalEnvelope), type(shell)
+
+    record = fixture.record_at(shell.replay_reference)
+    assert _resolution_state_of(record) == REFUSED_BEFORE_RESOLUTION
+    assert _resolution_state_of(record).reason == "refused-before-resolution"
+
+
+def test_an_absence_denial_states_it_was_refused_before_resolution_began(
+    fixture: _Fixture,
+) -> None:
+    """The same claim on the other boundary denial (``D-IMPL-260`` P-C):
+    the class the deployment does not serve is refused before resolution
+    could begin, and the record states that with its reason.
+    """
+    shell = govern_absence(
+        grant=_grant(),
+        tenant=TENANT,
+        product_class=PRODUCT_CLASS,
+        product_version=PRODUCT_VERSION,
+        parameters={"threshold": 1},
+        asked_at=DETERMINED_AT,
+        surface=SURFACE_HTTP_ROUTE,
+        address=ADDRESS,
+        perspective=Perspective(principal_id=PRINCIPAL, role=ROLE),
+        absent=LookupError("nothing servable at that address (fixture)"),
+        entitlement_source=fixture.source,
+        refusal_recorder=fixture.recorder,
+    )
+    assert isinstance(shell, RefusalEnvelope), type(shell)
+    assert shell.kind == "subject-unavailable"
+    assert shell.replay_reference != NO_REPLAY_REFERENCE
+
+    record = fixture.record_at(shell.replay_reference)
+    assert record.policy_bindings.bindings == ()
+    assert _resolution_state_of(record) == REFUSED_BEFORE_RESOLUTION
+
+
 # --- (3) the subject-conflict path is a recorded decision now ----------------
```

## tests/conformance/test_harness_adapter.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/conformance/test_harness_adapter.py b/tests/conformance/test_harness_adapter.py
index 0b280837..2fe7da09 100644
--- a/tests/conformance/test_harness_adapter.py
+++ b/tests/conformance/test_harness_adapter.py
@@ -84,6 +84,7 @@ from ccf.replay.record import (
     NO_HARNESS,
     HarnessTrace,
     PolicyBinding,
+    ResolutionNotApplicable,
     build_replay_record,
 )
 from ccf.skills.catalog import SKILL_CATALOG_ENTRY, SkillCatalog, SkillCatalogEntry
@@ -1076,6 +1077,7 @@ def test_seam_4_cannot_touch_a_governed_replay_dimension(
         "policy_bindings": (PolicyBinding(key="policy.bundle", version="1.1.0"),),
         "assembly_mode": "algorithmic",
         "recorded_at": BOUNDARY,
+        "resolution": ResolutionNotApplicable(reason="no-resolution-step"),
         "agent_conditioning": world.agent_a.perspective_conditioning(
             principal_id=world.actor,
             grant_set_hash=world.ledger.grant_set_hash(
```

## tests/conformance/test_harness_portability.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/conformance/test_harness_portability.py b/tests/conformance/test_harness_portability.py
index e24995af..ff5e1811 100644
--- a/tests/conformance/test_harness_portability.py
+++ b/tests/conformance/test_harness_portability.py
@@ -114,6 +114,7 @@ from ccf.replay.record import (
     HarnessTrace,
     ModelVersionRecord,
     PolicyBinding,
+    ResolutionNotApplicable,
     build_replay_record,
 )
 from ccf.skills.grants import SkillGrant
@@ -476,6 +477,7 @@ def _drive(
         ),
         assembly_mode="algorithmic",
         recorded_at=BOUNDARY,
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
         agent_conditioning=agent.perspective_conditioning(
             principal_id=world.actor,
             grant_set_hash=world.ledger.grant_set_hash(agent.identity.definition_hash),
```

## tests/conftest.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/conftest.py b/tests/conftest.py
index 2d5299b9..892f1be7 100644
--- a/tests/conftest.py
+++ b/tests/conftest.py
@@ -440,3 +440,42 @@ def _skills_callable_values() -> dict[str, Any]:
     )
     values: dict[str, Any] = document["callables"]
     return values
+
+
+# ---------------------------------------------------------------------------
+# D-IMPL-265 — ``archive/examples/`` is retired usage-model history, not a
+# compatibility consumer of the SDK. A test whose only purpose is exercising a
+# retired program there carries the registered ``archived`` marker
+# (``pyproject.toml``) and is DESELECTED by default: it leaves the pass/fail
+# denominator, shows up as ``N deselected`` in every summary line, and runs on
+# demand with ``--run-archived`` as preserved evidence. Deselected, never
+# skipped — a skipped item is still counted; a deselected one is not. The guard
+# that keeps the category honest (every archive runner is marked, only archive
+# runners are marked) is ``tests/lints/test_archived_examples_non_gating.py``.
+# ---------------------------------------------------------------------------
+
+RUN_ARCHIVED_OPTION = "--run-archived"
+
+
+def pytest_addoption(parser: pytest.Parser) -> None:
+    parser.addoption(
+        RUN_ARCHIVED_OPTION,
+        action="store_true",
+        default=False,
+        help=(
+            "also run the tests marked `archived` — the modules that execute a "
+            "retired program under archive/examples/ (D-IMPL-265); they are "
+            "deselected by default and are not release-gating"
+        ),
+    )
+
+
+def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
+    """Deselect ``archived`` items unless ``--run-archived`` was passed (D-IMPL-265)."""
+    if config.getoption(RUN_ARCHIVED_OPTION, default=False):
+        return
+    archived = [item for item in items if item.get_closest_marker("archived") is not None]
+    if not archived:
+        return
+    config.hook.pytest_deselected(items=archived)
+    items[:] = [item for item in items if item.get_closest_marker("archived") is None]
```

## tests/contracts/test_hash_transparency.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/contracts/test_hash_transparency.py b/tests/contracts/test_hash_transparency.py
index afe43e28..62b60a32 100644
--- a/tests/contracts/test_hash_transparency.py
+++ b/tests/contracts/test_hash_transparency.py
@@ -434,6 +434,13 @@ _MARKED_IN_THE_TREE = frozenset(
         "ccf.products.request.ProductRequestContract.argument_domains",
         "ccf.products.request.ArgumentDomain.minimum",
         "ccf.products.request.ArgumentDomain.maximum",
+        # 24.7-01, the enumerated shape (`D-IMPL-264` D-03/D-06): the
+        # closed member set beside the two numeric ends. Silent at `None`,
+        # so no committed request contract's address moves — every
+        # numeric domain written before the member set existed
+        # canonicalizes as it did, and the `ProductRequestContract`
+        # digest below still reproduces.
+        "ccf.products.request.ArgumentDomain.members",
     }
 )
```

## tests/crossproc/servers/mcp_egress_child.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/crossproc/servers/mcp_egress_child.py b/tests/crossproc/servers/mcp_egress_child.py
index 271f1ad1..ede5b52c 100644
--- a/tests/crossproc/servers/mcp_egress_child.py
+++ b/tests/crossproc/servers/mcp_egress_child.py
@@ -70,7 +70,11 @@ from ccf.products.request import (  # noqa: E402
     refuse_request,
 )
 from ccf.projection.plan import Perspective  # noqa: E402
-from ccf.replay.record import PolicyBinding, build_replay_record  # noqa: E402
+from ccf.replay.record import (  # noqa: E402
+    PolicyBinding,
+    ResolutionNotApplicable,
+    build_replay_record,
+)
 from ccf.replay.serve import ReplayWriter, ServedProduct, serve  # noqa: E402
 from ccf_runtime.authz.product_entitlement import (  # noqa: E402
     ControlPlaneProductEntitlementSource,
@@ -367,6 +371,7 @@ def _served(
         policy_bindings=(policy_binding,),
         assembly_mode="algorithmic",
         recorded_at=recorded_at,
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
     )
     return serve(product=gated, record=record, replay_writer=replay_writer)
```

## tests/crossproc/servers/mcp_experience_child.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/crossproc/servers/mcp_experience_child.py b/tests/crossproc/servers/mcp_experience_child.py
index 0fcfcd46..a9c39b45 100644
--- a/tests/crossproc/servers/mcp_experience_child.py
+++ b/tests/crossproc/servers/mcp_experience_child.py
@@ -76,7 +76,11 @@ from ccf.products.request import ProductRequest  # noqa: E402
 from ccf.products.resolver import ReplayRefusalRecorder  # noqa: E402
 from ccf.projection.engine import ExecutionResult, ExecutionStep  # noqa: E402
 from ccf.projection.plan import Perspective, ProjectionOutput  # noqa: E402
-from ccf.replay.record import PolicyBinding, build_replay_record  # noqa: E402
+from ccf.replay.record import (  # noqa: E402
+    PolicyBinding,
+    ResolutionNotApplicable,
+    build_replay_record,
+)
 from ccf.replay.serve import ReplayWriter, ServedProduct  # noqa: E402
 from ccf.skills.callables import CallableRegistry  # noqa: E402
 from ccf.skills.catalog import (  # noqa: E402
@@ -484,6 +488,7 @@ def build_server(
             ),
             assembly_mode="algorithmic",
             recorded_at=world.boundary,
+            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
             agent_conditioning=conditioning,
         )
         capability = writer.write_replay_record(record=record)
```

## tests/crossproc/servers/mcp_hitl_child.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/crossproc/servers/mcp_hitl_child.py b/tests/crossproc/servers/mcp_hitl_child.py
index 41fb381f..77dd9e5e 100644
--- a/tests/crossproc/servers/mcp_hitl_child.py
+++ b/tests/crossproc/servers/mcp_hitl_child.py
@@ -73,7 +73,11 @@ from ccf.products.contract import (  # noqa: E402
 )
 from ccf.projection.engine import ExecutionResult, ExecutionStep  # noqa: E402
 from ccf.projection.plan import Perspective, ProjectionOutput  # noqa: E402
-from ccf.replay.record import PolicyBinding, build_replay_record  # noqa: E402
+from ccf.replay.record import (  # noqa: E402
+    PolicyBinding,
+    ResolutionNotApplicable,
+    build_replay_record,
+)
 from ccf.replay.serve import ReplayWriter  # noqa: E402
 from ccf_runtime.mcp.auth import (  # noqa: E402
     FileTokenSource,
@@ -256,6 +260,7 @@ def build_server(*, workspace: Path) -> FastMCP:
             ),
             assembly_mode="algorithmic",
             recorded_at=submission.principal.action_time,
+            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
             hitl_actions=resolution.hitl_actions_block,
         )
         capability = writer.write_replay_record(record=record)
```

## tests/hitl/test_replay_e2e.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/hitl/test_replay_e2e.py b/tests/hitl/test_replay_e2e.py
index e1d42811..80f0cc99 100644
--- a/tests/hitl/test_replay_e2e.py
+++ b/tests/hitl/test_replay_e2e.py
@@ -60,6 +60,7 @@ from ccf.replay.record import (
     NO_HITL_ACTIONS,
     DecisionReplayRecord,
     PolicyBinding,
+    ResolutionNotApplicable,
     build_replay_record,
 )
 
@@ -145,6 +146,7 @@ def _replay_record(*, hitl_actions: str | None) -> DecisionReplayRecord:
         policy_bindings=(PolicyBinding(key="policy.bundle", version="v1"),),
         assembly_mode="algorithmic",
         recorded_at=datetime(2026, 3, 1, tzinfo=UTC),
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
         hitl_actions=hitl_actions,
     )
```

## tests/http_api/conftest.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/http_api/conftest.py b/tests/http_api/conftest.py
index 7ecfcea0..13e74bec 100644
--- a/tests/http_api/conftest.py
+++ b/tests/http_api/conftest.py
@@ -48,6 +48,7 @@ from ccf.replay.record import (
     DecisionReplayRecord,
     PerspectiveConditioning,
     PolicyBinding,
+    ResolutionNotApplicable,
     build_replay_record,
 )
 from ccf.skills.catalog import SKILL_CATALOG_ENTRY, SkillCatalog, SkillCatalogEntry
@@ -216,6 +217,7 @@ def _replay_record() -> DecisionReplayRecord:
         policy_bindings=(PolicyBinding(key="policy.bundle", version="v1"),),
         assembly_mode="algorithmic",
         recorded_at=datetime(2026, 3, 1, tzinfo=UTC),
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
         agent_conditioning=PerspectiveConditioning(
             principal_id="principal-1",
             role="analyst",
```


<!-- mid-payload read-proof -->
```
READ-PROOF bundle-tests-part-1.md: 7fef7e412f4016c6
```

## tests/http_api/test_hitl_door_identity.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/http_api/test_hitl_door_identity.py b/tests/http_api/test_hitl_door_identity.py
index d7db05a1..882312a0 100644
--- a/tests/http_api/test_hitl_door_identity.py
+++ b/tests/http_api/test_hitl_door_identity.py
@@ -211,7 +211,11 @@ class TestHardenedPath:
         )
         from ccf.projection.engine import ExecutionResult, ExecutionStep
         from ccf.projection.plan import Perspective, ProjectionOutput
-        from ccf.replay.record import PolicyBinding, build_replay_record
+        from ccf.replay.record import (
+            PolicyBinding,
+            ResolutionNotApplicable,
+            build_replay_record,
+        )
         from ccf_runtime.http_api.app import create_app
         from ccf_runtime.http_api.auth import BearerTokenAuth
         from ccf_runtime.http_api.dependencies import ApiDependencies
@@ -325,6 +329,7 @@ class TestHardenedPath:
             ),
             assembly_mode="algorithmic",
             recorded_at=recorded.principal.action_time,
+            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
             hitl_actions=resolution.hitl_actions_block,
         )
         assert _CLIENT_ID in record.policy_bindings.hitl_actions
```

## tests/http_api/test_product_declared_obligation_409.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/http_api/test_product_declared_obligation_409.py b/tests/http_api/test_product_declared_obligation_409.py
index 697ca503..4f355b37 100644
--- a/tests/http_api/test_product_declared_obligation_409.py
+++ b/tests/http_api/test_product_declared_obligation_409.py
@@ -88,7 +88,7 @@ from ccf.products.refusal import (
 from ccf.products.request import ProductRequest
 from ccf.products.resolver import ReplayRefusalRecorder
 from ccf.projection.plan import Perspective
-from ccf.replay.record import DecisionReplayRecord
+from ccf.replay.record import DecisionReplayRecord, ResolutionNotApplicable
 from ccf_runtime.authz.product_entitlement import (
     ControlPlaneProductEntitlementSource,
 )
@@ -528,6 +528,7 @@ def _minted(
         envelope,
         perspective=Perspective(principal_id=PRINCIPAL, role=ROLE),
         recorded_at=DETERMINED_AT,
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
     )
     governed = _governed(
         fabric,
```

## tests/http_api/test_product_disclosure.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/http_api/test_product_disclosure.py b/tests/http_api/test_product_disclosure.py
index 270f8741..05694e33 100644
--- a/tests/http_api/test_product_disclosure.py
+++ b/tests/http_api/test_product_disclosure.py
@@ -65,7 +65,7 @@ from ccf.products.refusal import (
 )
 from ccf.products.resolver import ReplayRefusalRecorder
 from ccf.projection.plan import Perspective
-from ccf.replay.record import DecisionReplayRecord
+from ccf.replay.record import DecisionReplayRecord, ResolutionNotApplicable
 from ccf_runtime.authz.delivery_boundary import SURFACE_HTTP_ROUTE
 from ccf_runtime.http_api.errors import (
     ERROR_PRINCIPAL_NOT_ENTITLED,
@@ -229,6 +229,7 @@ def _absent_subject_resolver(holder: dict[str, Any], fabric: Fabric) -> Any:
             envelope,
             perspective=perspective,
             recorded_at=DETERMINED_AT,
+            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
             request=request,
         )
```

## tests/integration/test_agent_slice.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/integration/test_agent_slice.py b/tests/integration/test_agent_slice.py
index 938a0251..3196a8b8 100644
--- a/tests/integration/test_agent_slice.py
+++ b/tests/integration/test_agent_slice.py
@@ -63,6 +63,7 @@ from ccf.products.gates import ServableProduct, run_gates
 from ccf.replay.record import (
     NO_GRANTS_SET_HASH,
     PolicyBinding,
+    ResolutionNotApplicable,
     build_replay_record,
 )
 from ccf.skills.catalog import SKILL_CATALOG_ENTRY, SkillCatalog, SkillCatalogEntry
@@ -269,6 +270,7 @@ def test_dimension_4_carries_the_complete_d06_field_set(fabric: _Fabric) -> None
         ),
         assembly_mode=fabric.control["product_class"]["assembly_mode"],
         recorded_at=fabric.now,
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
         agent_conditioning=agent.perspective_conditioning(
             principal_id=principal_id, grant_set_hash=NO_GRANTS_SET_HASH
         ),
@@ -661,6 +663,7 @@ def test_a_granted_decision_captures_the_grant_set_hash_in_dimension_4(
             ),
             assembly_mode=fabric.control["product_class"]["assembly_mode"],
             recorded_at=fabric.now,
+            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
             agent_conditioning=agent.perspective_conditioning(
                 principal_id=principal_id,
                 grant_set_hash=ledger.grant_set_hash(content_hash(definition)),
```

## tests/integration/test_proto_quickstart.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/integration/test_proto_quickstart.py b/tests/integration/test_proto_quickstart.py
index 9c28b29c..b39bfc79 100644
--- a/tests/integration/test_proto_quickstart.py
+++ b/tests/integration/test_proto_quickstart.py
@@ -91,6 +91,7 @@ from ccf.replay.record import (
     NO_GRANTS_SET_HASH,
     DecisionReplayRecord,
     PolicyBinding,
+    ResolutionNotApplicable,
     build_replay_record,
 )
 from ccf.replay.serve import ReplayWriter, ServedProduct, serve
@@ -454,6 +455,7 @@ def _serve(fabric: _Fabric, store: FileArtifactStore) -> tuple[
         ),
         assembly_mode=fabric.control["product_class"]["assembly_mode"],
         recorded_at=fabric.now,
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
     )
     served = serve(
         product=gated,
```

## tests/mcp/test_egress_disclosure.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/mcp/test_egress_disclosure.py b/tests/mcp/test_egress_disclosure.py
index 2131e94c..9bd91463 100644
--- a/tests/mcp/test_egress_disclosure.py
+++ b/tests/mcp/test_egress_disclosure.py
@@ -80,7 +80,11 @@ from ccf.products.refusal import (
 from ccf.products.request import ProductRequest
 from ccf.products.resolver import ReplayRefusalRecorder
 from ccf.projection.plan import Perspective
-from ccf.replay.record import NO_ROLE_RESOLVED, DecisionReplayRecord
+from ccf.replay.record import (
+    NO_ROLE_RESOLVED,
+    DecisionReplayRecord,
+    ResolutionNotApplicable,
+)
 from ccf_runtime.authz.product_entitlement import (
     ControlPlaneProductEntitlementSource,
 )
@@ -254,6 +258,7 @@ class _World:
                 principal_id=perspective.principal_id, role=NO_ROLE_RESOLVED
             ),
             recorded_at=DETERMINED_AT,
+            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
         )
 
     def record_at(self, uri: str) -> DecisionReplayRecord:
```

## tests/mcp/test_egress_listing.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/mcp/test_egress_listing.py b/tests/mcp/test_egress_listing.py
index d24902b9..5ff0958e 100644
--- a/tests/mcp/test_egress_listing.py
+++ b/tests/mcp/test_egress_listing.py
@@ -66,6 +66,7 @@ from ccf.contracts.canonical import canonical_bytes
 from ccf.artifacts.file_store import FileArtifactStore
 from ccf.controlplane.registry import ControlPlaneRegistry
 from ccf.products.resolver import ReplayRefusalRecorder
+from ccf.replay.record import ResolutionNotApplicable
 from ccf.mcp.client import run_with_session
 from ccf.mcp.errors import McpServerUnreachable
 from ccf.products.door import DoorOutcome, WireRequest, door_question
@@ -295,6 +296,7 @@ def _refusing(declared: ProductRequestContract) -> Callable[..., object]:
             ),
             perspective=perspective,
             recorded_at=request.asked_at,
+            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
             request=request,
         )
```

## tests/mcp/test_egress_refusal_channels.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/mcp/test_egress_refusal_channels.py b/tests/mcp/test_egress_refusal_channels.py
index 022d331e..2a74216b 100644
--- a/tests/mcp/test_egress_refusal_channels.py
+++ b/tests/mcp/test_egress_refusal_channels.py
@@ -84,7 +84,11 @@ from ccf.products.refusal import (
 from ccf.products.request import ProductRequest
 from ccf.products.resolver import ReplayRefusalRecorder
 from ccf.projection.plan import Perspective
-from ccf.replay.record import NO_ROLE_RESOLVED, DecisionReplayRecord
+from ccf.replay.record import (
+    NO_ROLE_RESOLVED,
+    DecisionReplayRecord,
+    ResolutionNotApplicable,
+)
 from ccf_runtime.authz.delivery_boundary import UnrecordableDeliveryBoundaryError
 from ccf_runtime.authz.product_entitlement import (
     ControlPlaneProductEntitlementSource,
@@ -490,6 +494,7 @@ def test_the_standing_resource_body_is_the_shell_per_kind_class(
             _refusal_of(kind, assembled.address),
             perspective=Perspective(principal_id=PRINCIPAL, role=ROLE),
             recorded_at=DETERMINED_AT,
+            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
         )
 
     world = _World(tmp_path, address=assembled.address, resolver=resolve)
@@ -807,6 +812,7 @@ def test_the_two_resource_shells_are_both_minted_through_the_one_recorder(
         ),
         perspective=Perspective(principal_id=PRINCIPAL, role=NO_ROLE_RESOLVED),
         recorded_at=DETERMINED_AT,
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
     )
     nonexistent_world = _World(
         tmp_path / "nonexistent",
@@ -1214,6 +1220,7 @@ def test_no_kind_in_the_vocabulary_is_ever_a_tool_error(
             ),
             perspective=Perspective(principal_id=PRINCIPAL, role=ROLE),
             recorded_at=DETERMINED_AT,
+            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
         )
 
     world = _World(tmp_path, address=assembled.address, resolver=resolve)
```

## tests/mcp/test_egress_refusal_envelope.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/mcp/test_egress_refusal_envelope.py b/tests/mcp/test_egress_refusal_envelope.py
index 63a246f7..61602276 100644
--- a/tests/mcp/test_egress_refusal_envelope.py
+++ b/tests/mcp/test_egress_refusal_envelope.py
@@ -102,7 +102,7 @@ from ccf.products.request import (
     refuse_request,
 )
 from ccf.projection.plan import Perspective
-from ccf.replay.record import DecisionReplayRecord
+from ccf.replay.record import DecisionReplayRecord, ResolutionNotApplicable
 from ccf.replay.serve import ServedProduct
 from ccf.skills.catalog import SkillArgumentProperty, SkillArgumentSchema
 from ccf_runtime.authz.delivery_boundary import (
@@ -478,6 +478,7 @@ def _refusing(
             ),
             perspective=perspective,
             recorded_at=request.asked_at,
+            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
             request=request,
         )
 
@@ -513,6 +514,7 @@ def _minted(
         envelope,
         perspective=Perspective(principal_id=PRINCIPAL, role=ROLE),
         recorded_at=ASKED_AT,
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
     )
 
 
@@ -567,6 +569,7 @@ def _refusing_and_recording(
             ),
             perspective=perspective,
             recorded_at=request.asked_at,
+            resolution=ResolutionNotApplicable(reason="no-resolution-step"),
             request=request,
         )
```

## tests/mcp/test_experience_refusal_channels.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/mcp/test_experience_refusal_channels.py b/tests/mcp/test_experience_refusal_channels.py
index 5d005930..1ad89d15 100644
--- a/tests/mcp/test_experience_refusal_channels.py
+++ b/tests/mcp/test_experience_refusal_channels.py
@@ -88,7 +88,11 @@ from ccf.products.refusal import (
 )
 from ccf.products.resolver import ReplayRefusalRecorder
 from ccf.projection.plan import Perspective
-from ccf.replay.record import NO_ROLE_RESOLVED, DecisionReplayRecord
+from ccf.replay.record import (
+    NO_ROLE_RESOLVED,
+    DecisionReplayRecord,
+    ResolutionNotApplicable,
+)
 from ccf_runtime.authz.delivery_boundary import (
     UnrecordableDeliveryBoundaryError,
 )
@@ -538,6 +542,7 @@ def test_the_resource_returns_a_resolvers_refusal_as_its_shell(
         ),
         perspective=Perspective(principal_id=PRINCIPAL, role=ROLE),
         recorded_at=DETERMINED_AT,
+        resolution=ResolutionNotApplicable(reason="no-resolution-step"),
         policy_bindings=(),
     )
```

## tests/perf_smoke/test_smoke.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/perf_smoke/test_smoke.py b/tests/perf_smoke/test_smoke.py
index 91bc2cd5..2d57cf7c 100644
--- a/tests/perf_smoke/test_smoke.py
+++ b/tests/perf_smoke/test_smoke.py
@@ -43,7 +43,15 @@ SUITE_TIMEOUT_SECONDS = 300
 KILL_GRACE_SECONDS = 10
 
 #: The four battery suites under ``perf/suites/`` (D-25 taxonomy).
-SUITES = ("micro", "scale", "crossproc", "replay")
+SUITES = (
+    "micro",
+    "scale",
+    # D-IMPL-265 / carry row 24.7-C-02: the crossproc suite spawns
+    # archive/examples/04-cross-process/producer_child.py — retired usage model,
+    # non-gating until a phase re-points it at a supported child.
+    pytest.param("crossproc", marks=pytest.mark.archived),
+    "replay",
+)
 
 
 @pytest.mark.parametrize("suite", SUITES)
```

## tests/products/test_delivery_determinism.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/products/test_delivery_determinism.py b/tests/products/test_delivery_determinism.py
index b5bd7c97..6859fb21 100644
--- a/tests/products/test_delivery_determinism.py
+++ b/tests/products/test_delivery_determinism.py
@@ -86,7 +86,7 @@ from ccf.products.disclosure import DISCLOSURE_MINIMAL, DisclosureDecision
 from ccf.products.disclosure import WITHHELD
 from ccf.products.entitlement import product_entitlement_key
 from ccf.products.gates import DEBT_TOLERANCE_PARAMETER
-from ccf.products.provenance import EffectiveRequest
+from ccf.products.provenance import EffectiveRequest, ProvenanceSource
 from ccf.products.refusal import (
     NO_REPLAY_REFERENCE,
     REFUSAL_KINDS,
@@ -100,6 +100,8 @@ from ccf.replay.record import (
     NO_DISCLOSURE_DECISION,
     NO_REQUEST_RESOLUTION,
     DecisionReplayRecord,
+    PolicyBinding,
+    ResolutionNotApplicable,
 )
 from ccf.replay.serve import ServedProduct
 
@@ -598,14 +600,144 @@ def test_a_refused_request_records_the_override_it_attempted(
     assert attempt["policy_id"] == POLICY_THRESHOLD
     assert attempt["entitled"] is False and attempt["honored"] is False
     assert attempt["principal_id"] == PERSPECTIVE.principal_id
-    # And the dimension-2 resolution is the sentinel: there was no resolution,
-    # which is exactly why the attempt has to ride on the refusal.
-    assert _resolution_of(record) == NO_REQUEST_RESOLUTION
+    # And the dimension-2 resolution is the resolution that RAN: the attempt
+    # rides on the refusal, AND the partial work resolution established before
+    # the bound refused rides with it (`D-IMPL-264` D-07). The shipped tree
+    # recorded the sentinel here — a refusal minted as if nothing had been
+    # resolved — and that assertion was observed red before the fix.
+    assert _resolution_of(record) != NO_REQUEST_RESOLUTION, _resolution_of(record)
+    partial = EffectiveRequest.model_validate_json(_resolution_of(record))
+    assert [o.policy_id for o in partial.overrides] == [POLICY_THRESHOLD]
     # The shell withholds it at this tenant's level — an entitlement verdict is
     # fabric state — so the record is where the attempt is answerable from.
     assert shell.fields["overrides"] == canonical_bytes(WITHHELD).decode("utf-8")
 
 
+def test_a_refusal_minted_by_resolution_carries_the_partial_resolution_and_the_contract_pin(
+    tmp_path: pathlib.Path,
+) -> None:
+    """``D-IMPL-264`` D-07, criterion 13, ledger row ``CP04-G-33`` — on the RECORD.
+
+    Dave, verbatim (``24.7-RULINGS.md`` §3 Q7): *"Resolution participated
+    whenever the resolution step actually ran. If it refuses halfway through,
+    that partial work is still governed truth and belongs in replay. 'It
+    failed before producing an effective request' must not erase what
+    resolution already established."*
+
+    The scenario is the override-attempt case above with one addition: the
+    product class also declares a default tolerance, so that THREE
+    version-bearing authorities were consulted before a bound refused — the
+    request contract (its pin), the class declaration (its pin) and the
+    threshold constraint (its pin) — plus the request's own identity and the
+    unentitled override attempt. Every one of them is governed truth the
+    refusal was reached with, and every one is asserted where replay reads
+    it: the partial :class:`~ccf.products.provenance.EffectiveRequest` on
+    dimension 2, the pins as ``PolicyBinding`` rows beside it, and the same
+    partial record on the internal shell's ``provenance`` with its
+    ``applied`` as the shell's ``policy_bindings`` — exactly what the two
+    post-assembly refusal branches already record.
+
+    What fails here on the shipped tree, and was OBSERVED failing before the
+    fix (red-first, the plan's discipline): dimension 2 holds the sentinel
+    ``no-request-resolution``, because the governed resolver's pre-assembly
+    refusal branch minted the record with no resolution although defaults,
+    constraints and capabilities had been resolved first. That is the one
+    class-(c) omission ``CP04-G-33`` names inside the SDK.
+    """
+    documents = _tolerance_documents(class_default=CLASS_DEFAULT_TOLERANCE)
+    contract = documents["request_contract"]["declaration"]
+    contract["arguments"]["properties"][DEPTH_PARAMETER] = {
+        "type": "number",
+        "description": "Fixture depth; bounded by what the substrate can do.",
+    }
+    contract["capability_bindings"] = {DEPTH_PARAMETER: CAPABILITY_TRAVERSAL_DEPTH}
+    with _deployment(tmp_path / "partial", **documents) as booted:
+        booted.control_plane.register_typed(
+            KEY_THRESHOLD,
+            _constraint(
+                policy_id=POLICY_THRESHOLD,
+                parameter=THRESHOLD_PARAMETER,
+                operator="maximum",
+                value=THRESHOLD_MAXIMUM_FIRST,
+            ),
+            POLICY_CONSTRAINT,
+        )
+        resolver = _governed(
+            booted,
+            capabilities=(
+                TechnicalCapability(
+                    capability=CAPABILITY_TRAVERSAL_DEPTH,
+                    maximum=DEPTH_MAXIMUM,
+                    identity=BACKEND_IDENTITY,
+                ),
+            ),
+        )
+        request = _request(
+            parameters={
+                THRESHOLD_PARAMETER: CALLER_THRESHOLD,
+                DEPTH_PARAMETER: DEPTH_ASKED,
+            },
+            policy_overrides=(POLICY_THRESHOLD,),
+        )
+        shell = _ask(resolver, request)
+        assert isinstance(shell, RefusalEnvelope), shell
+        assert shell.kind == "constraint-refusal"
+        record = _record_of(booted, shell)
+        # The pins the resolver itself minted, computed the way it computes
+        # them: a content address of the exact bytes it read (`D-IMPL-26`).
+        declaration = resolver._declaration()
+        declared = resolver._request_contract(declaration)
+    contract_source = ProvenanceSource(
+        kind="artifact",
+        identity=resolver.request_contract_key,
+        version=content_hash(declared),
+    )
+    class_source = ProvenanceSource(
+        kind="artifact",
+        identity=resolver.product_class_key,
+        version=content_hash(declaration),
+    )
+
+    # Dimension 2 carries the resolution that ran, not the sentinel.
+    assert _resolution_of(record) != NO_REQUEST_RESOLUTION, _resolution_of(record)
+    partial = EffectiveRequest.model_validate_json(_resolution_of(record))
+    assert contract_source in partial.applied, partial.applied
+    assert class_source in partial.applied, partial.applied
+    constraint_sources = [
+        source
+        for source in partial.applied
+        if source.kind == "artifact" and source.identity == KEY_THRESHOLD
+    ]
+    assert len(constraint_sources) == 1, partial.applied
+    assert partial.asked_at == request.asked_at
+    assert [o.policy_id for o in partial.overrides] == [POLICY_THRESHOLD]
+    assert partial.overrides[0].entitled is False
+    # The defaulted tolerance the class declared WAS resolved before the bound
+    # refused — the partial work D-07 refuses to erase.
+    tolerance = partial.parameter(DEBT_TOLERANCE_PARAMETER)
+    assert tolerance is not None and tolerance.authority == "default"
+    assert tolerance.source == class_source
+
+    # The version-bearing pins land as `PolicyBinding` rows, so the record is
+    # falsifiable from pinned state (D-07, D-08; what D-11 infers from).
+    bindings = record.policy_bindings.bindings
+    assert (
+        PolicyBinding(key=resolver.request_contract_key, version=content_hash(declared))
+        in bindings
+    ), bindings
+    assert (
+        PolicyBinding(key=resolver.product_class_key, version=content_hash(declaration))
+        in bindings
+    ), bindings
+    assert any(binding.key == KEY_THRESHOLD for binding in bindings), bindings
+
+    # And the internal shell says the same thing the record does — one value
+    # serving both readers, so they cannot disagree (`D-IMPL-254`).
+    internal = RefusalEnvelope.model_validate_json(_refusal_block(record))
+    assert internal.provenance == partial
+    assert internal.policy_bindings == partial.applied
+
+
 # --- (3) policy-resolution-conflict -------------------------------------------
 
 
@@ -734,6 +866,7 @@ def test_a_subject_unavailable_refusal_is_the_same_determination_twice(
                 internal,
                 perspective=PERSPECTIVE,
                 recorded_at=ASKED_AT,
+                resolution=ResolutionNotApplicable(reason="no-resolution-step"),
                 request=request,
                 execution=None,
             )
```

## tests/products/test_disclosure.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/products/test_disclosure.py b/tests/products/test_disclosure.py
index 6d344fd7..6d5b3147 100644
--- a/tests/products/test_disclosure.py
+++ b/tests/products/test_disclosure.py
@@ -634,3 +634,175 @@ def test_no_sabotage_edits_the_real_source_tree() -> None:
     source = DISCLOSURE_SOURCE.decode("utf-8")
     assert MARKER + REAL_LINE in source
     assert PASS_THROUGH not in source
+
+
+# --- (6) the allowed set crosses only where `detail` crosses (24.7-01) -------
+#
+# `D-IMPL-264` D-05 (Dave): *"The presented value can be named; disclosure
+# controls whether the allowed set is exposed."* The set travels ONLY in
+# `detail`, so `PERMITTED_AT_MINIMAL` decides its exposure without a new
+# member; advertisement of the set is the other channel (D-02) and is not a
+# refusal shell's business. Criterion 6.
+
+_ENUMERATED_MEMBERS = ("alpha", "beta")
+_ENUMERATED_PARAMETER = "kind"
+
+
+def _not_in_domain() -> RefusalEnvelope:
+    """A REAL `not-in-domain` verdict from `refuse_request`, enveloped."""
+    from datetime import datetime as _dt
+
+    from ccf.products.request import (
+        ArgumentDomain,
+        ProductRequest,
+        ProductRequestContract,
+        refuse_request,
+    )
+    from ccf.skills.catalog import SkillArgumentProperty, SkillArgumentSchema
+
+    declared = ProductRequestContract(
+        semver="1.0.0",
+        schema_name="ccf.test-product",
+        schema_version="1.0.0",
+        arguments=SkillArgumentSchema(
+            properties={
+                _ENUMERATED_PARAMETER: SkillArgumentProperty(
+                    type="string", description="an enumerated parameter"
+                )
+            },
+            required=(_ENUMERATED_PARAMETER,),
+        ),
+        argument_domains={
+            _ENUMERATED_PARAMETER: ArgumentDomain(members=_ENUMERATED_MEMBERS)
+        },
+    )
+    verdict = refuse_request(
+        request=ProductRequest(
+            schema_name="ccf.test-product",
+            schema_version="1.0.0",
+            subject="fixture:subject/one",
+            intent="fixture-intent",
+            freshness="fixture-freshness",
+            asked_at=_dt(2026, 3, 2, 9, 30, tzinfo=UTC),
+            parameters={_ENUMERATED_PARAMETER: "gamma"},
+        ),
+        declared=declared,
+    )
+    assert verdict is not None and verdict.reason == "not-in-domain"
+    return envelope_for(
+        verdict,
+        request=RequestIdentity(
+            product_id="ccf.test-product",
+            product_version="1.0.0",
+            parameters={_ENUMERATED_PARAMETER: "gamma"},
+            temporal_boundary=_INSTANT,
+        ),
+    )
+
+
+@pytest.mark.parametrize("level", sorted(DISCLOSURE_LEVELS))
+def test_the_allowed_set_crosses_only_where_detail_crosses(level: str) -> None:
+    """Absent at ``minimal``, present at ``reasoned`` and at ``full``.
+
+    The `fields` roster is the one `test_refusal_envelope.py` pins — no
+    member was added to carry the set, so `PERMITTED_AT_MINIMAL` needs no
+    row and the observational-equivalence controls at both doors stand.
+    """
+    internal = _not_in_domain()
+    shell, decision = disclose(internal, level=level, policy=None)
+    rendered = canonical_bytes(shell).decode("utf-8")
+
+    assert set(shell.fields) == {
+        "declared_type",
+        "presented_type",
+        "declared_keys",
+        "presented_keys",
+        "overrides",
+    }
+    assert shell.reason == "not-in-domain"
+    assert shell.key == _ENUMERATED_PARAMETER
+    if level == "minimal":
+        assert shell.detail == EXTERNAL_STATEMENTS["product-request-violation"]
+        for member in _ENUMERATED_MEMBERS:
+            assert member not in rendered, (member, rendered)
+        assert "detail" in decision.withheld
+    else:
+        assert shell.detail == internal.detail
+        for member in _ENUMERATED_MEMBERS:
+            assert member in shell.detail
+    # The caller's own value crosses at every level — it is the caller's.
+    assert "gamma" in rendered
+
+
+# --- (7) the declared intent set crosses only where `detail` crosses (24.7-07)
+#
+# `D-IMPL-264` amendment 3 A-8 a (Dave): *"The intent set is always
+# advertisable through the canonical contract/discovery representation, but a
+# refusal shell reveals it only according to the disclosure level."* The set
+# travels ONLY in `detail` — the channel the enumerated argument domain uses
+# in (6) — never in `declared_type`, which `PERMITTED_AT_MINIMAL` lets cross.
+# Criterion 10.
+
+_DECLARED_INTENTS = ("credit-screening", "onboarding-review")
+_PRESENTED_INTENT = "other-intent"
+
+
+def _intent_refusal() -> RefusalEnvelope:
+    """A REAL intent verdict from `refuse_intent`, enveloped."""
+    from ccf.products.contract import ProductDiscovery
+    from ccf.products.request import ProductRequest, refuse_intent
+
+    verdict = refuse_intent(
+        request=ProductRequest(
+            schema_name="ccf.test-product",
+            schema_version="1.0.0",
+            subject="fixture:subject/one",
+            intent=_PRESENTED_INTENT,
+            freshness="fixture-freshness",
+            asked_at=_INSTANT,
+            parameters={},
+        ),
+        discovery=ProductDiscovery(
+            domain="fixture-domain",
+            intents=frozenset(_DECLARED_INTENTS),
+            capabilities=frozenset(),
+        ),
+    )
+    assert verdict is not None and verdict.key == "intent"
+    return envelope_for(verdict, request=_request_identity())
+
+
+@pytest.mark.parametrize("level", sorted(DISCLOSURE_LEVELS))
+def test_the_declared_intent_set_crosses_only_where_detail_crosses(
+    level: str,
+) -> None:
+    """Absent at ``minimal``, present at ``reasoned`` and at ``full``.
+
+    Same `fields` roster as (6): no member was added to carry the set, so
+    `PERMITTED_AT_MINIMAL` needs no row. Sabotage (recorded in the plan
+    SUMMARY): carry the set in `declared_type` and the `minimal` case reds.
+    """
+    internal = _intent_refusal()
+    shell, decision = disclose(internal, level=level, policy=None)
+    rendered = canonical_bytes(shell).decode("utf-8")
+
+    assert set(shell.fields) == {
+        "declared_type",
+        "presented_type",
+        "declared_keys",
+        "presented_keys",
+        "overrides",
+    }
+    assert shell.reason == "class-mismatch"
+    assert shell.key == "intent"
+    if level == "minimal":
+        assert shell.detail == EXTERNAL_STATEMENTS["product-request-violation"]
+        for declared in _DECLARED_INTENTS:
+            assert declared not in rendered, (declared, rendered)
+        assert "detail" in decision.withheld
+    else:
+        assert shell.detail == internal.detail
+        for declared in _DECLARED_INTENTS:
+            assert declared in shell.detail
+    # The caller's own intent crosses at every level — it is the caller's.
+    assert _PRESENTED_INTENT in rendered
```

## tests/products/test_policy_constraint_resolver.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/products/test_policy_constraint_resolver.py b/tests/products/test_policy_constraint_resolver.py
index 6864315c..2aaad050 100644
--- a/tests/products/test_policy_constraint_resolver.py
+++ b/tests/products/test_policy_constraint_resolver.py
@@ -67,6 +67,7 @@ from ccf.controlplane.registry import ControlPlaneRegistry
 from ccf.products import constraints as constraints_module
 from ccf.products.constraints import (
     ConstraintEffectivityConflict,
+    ConstraintRefusal,
     ReferencePolicyConstraintResolver,
     constraints_in_force,
 )
@@ -343,6 +344,62 @@ def _scratch_constraints(
     return module
 
 
+# --- the paired outcome at the seam (`D-IMPL-264` D-08) ------------------------
+
+#: A presence constraint on the threshold, which the fixture question never
+#: supplies and the fixture contract never defaults — so the seam REFUSES
+#: after the tolerance ceiling in force has already folded.
+KEY_PRESENCE = "policy_constraints.presence"
+POLICY_PRESENCE = "presence"
+
+
+def test_a_refused_resolution_still_carries_the_evidence_at_the_seam(
+    registry: ControlPlaneRegistry,
+) -> None:
+    """D-08 through the Protocol: a refused outcome's `evidence.applied` names
+    `declared_source` and the constraint that folded before the refusal.
+
+    Sorted by key, the tolerance (`a`, in force before `T1`) folds first and
+    clamps — worked case 3 — and only then does the presence constraint on the
+    threshold refuse. Everything the first step established is on the outcome
+    beside the refusal, at the seam and not only in the pure function.
+    """
+    version_a, _version_b = _register_two_windows(registry)
+    version_presence = registry.register_typed(
+        KEY_PRESENCE,
+        PolicyConstraint(
+            semver="1.0.0",
+            policy_id=POLICY_PRESENCE,
+            applies_to=ConstraintApplicability(),
+            parameter=THRESHOLD_PARAMETER,
+            operator="required",
+            value=None,
+            overridable=False,
+            source_authority="fixture-authority",
+            effective_from=T0,
+            effective_until=None,
+            reason="a fixture reason",
+        ),
+        POLICY_CONSTRAINT,
+    )
+
+    outcome = _resolve(registry, asked_at=BEFORE_T1)
+
+    assert isinstance(outcome.refusal, ConstraintRefusal), outcome
+    assert outcome.refusal.reason == "required-absent"
+    assert outcome.refusal.key == THRESHOLD_PARAMETER
+    assert outcome.completed is False
+    evidence = outcome.evidence
+    assert DECLARED_SOURCE in evidence.applied
+    assert (KEY_A, version_a) in _constraint_pins(evidence)
+    assert ProvenanceSource(
+        kind="artifact", identity=KEY_PRESENCE, version=version_presence
+    ) in evidence.applied
+    tolerance = evidence.parameter(DEBT_TOLERANCE_PARAMETER)
+    assert tolerance is not None
+    assert tolerance.authority == "policy" and tolerance.value == MAXIMUM_EARLY
+
+
 # --- (a) effectivity: the window decides, at the request's own instant --------
 
 
@@ -354,7 +411,9 @@ def test_a_request_inside_the_first_window_resolves_the_first_constraint(
 
     resolved = _resolve(registry, asked_at=BEFORE_T1)
 
-    assert isinstance(resolved, EffectiveRequest)
+    assert resolved.refusal is None, resolved.refusal
+
+    resolved = resolved.evidence
     tolerance = resolved.parameter(DEBT_TOLERANCE_PARAMETER)
     assert tolerance is not None
     assert tolerance.value == MAXIMUM_EARLY
@@ -375,7 +434,9 @@ def test_a_request_at_the_boundary_instant_resolves_the_second(
 
     resolved = _resolve(registry, asked_at=T1)
 
-    assert isinstance(resolved, EffectiveRequest)
+    assert resolved.refusal is None, resolved.refusal
+
+    resolved = resolved.evidence
     tolerance = resolved.parameter(DEBT_TOLERANCE_PARAMETER)
     assert tolerance is not None
     assert tolerance.value == MAXIMUM_LATE
@@ -406,7 +467,9 @@ def test_the_pinned_versions_are_the_registrys_own_content_addresses(
     version_a, _ = _register_two_windows(registry)
     resolved = _resolve(registry, asked_at=BEFORE_T1)
 
-    assert isinstance(resolved, EffectiveRequest)
+    assert resolved.refusal is None, resolved.refusal
+
+    resolved = resolved.evidence
     ((key, version),) = _constraint_pins(resolved)
     assert (key, version) == (KEY_A, version_a)
     assert version == content_hash(registry.peek(KEY_A, version_a))
@@ -433,7 +496,9 @@ def test_the_resolution_never_reaches_for_the_latest_version(
     monkeypatch.setattr(ControlPlaneRegistry, "resolve_latest", _refuse)
     resolved = _resolve(registry, asked_at=BEFORE_T1)
 
-    assert isinstance(resolved, EffectiveRequest)
+    assert resolved.refusal is None, resolved.refusal
+
+    resolved = resolved.evidence
 
 
 def test_the_latest_guard_can_fire(
@@ -543,7 +608,9 @@ def test_an_entitled_principal_overrides_the_constraint(
         registry, asked_at=BEFORE_T1, perspective=ENTITLED, overrides=(POLICY_A,)
     )
 
-    assert isinstance(resolved, EffectiveRequest)
+    assert resolved.refusal is None, resolved.refusal
+
+    resolved = resolved.evidence
     tolerance = resolved.parameter(DEBT_TOLERANCE_PARAMETER)
     assert tolerance is not None
     assert tolerance.value == CALLER_ASKS, "the constraint did not apply"
@@ -578,7 +645,9 @@ def test_a_name_only_override_is_not_honored(
         registry, asked_at=BEFORE_T1, perspective=UNENTITLED, overrides=(POLICY_A,)
     )
 
-    assert isinstance(resolved, EffectiveRequest)
+    assert resolved.refusal is None, resolved.refusal
+
+    resolved = resolved.evidence
     tolerance = resolved.parameter(DEBT_TOLERANCE_PARAMETER)
     assert tolerance is not None
     assert tolerance.value == MAXIMUM_EARLY, "the constraint applied"
@@ -613,7 +682,9 @@ def test_an_override_of_a_policy_nobody_registered_is_recorded_and_not_honored(
         overrides=(UNREGISTERED_POLICY,),
     )
 
-    assert isinstance(resolved, EffectiveRequest)
+    assert resolved.refusal is None, resolved.refusal
+
+    resolved = resolved.evidence
     tolerance = resolved.parameter(DEBT_TOLERANCE_PARAMETER)
     assert tolerance is not None
     assert tolerance.value == MAXIMUM_EARLY, "the applicable constraint still applied"
@@ -643,7 +714,9 @@ def test_an_entitled_override_of_a_non_overridable_constraint_is_not_honored(
         registry, asked_at=BEFORE_T1, perspective=ENTITLED, overrides=(POLICY_A,)
     )
 
-    assert isinstance(resolved, EffectiveRequest)
+    assert resolved.refusal is None, resolved.refusal
+
+    resolved = resolved.evidence
     tolerance = resolved.parameter(DEBT_TOLERANCE_PARAMETER)
     assert tolerance is not None
     assert tolerance.value == MAXIMUM_EARLY
@@ -661,7 +734,9 @@ def test_with_no_entitlement_policy_registered_no_override_is_entitled(
         registry, asked_at=BEFORE_T1, perspective=ENTITLED, overrides=(POLICY_A,)
     )
 
-    assert isinstance(resolved, EffectiveRequest)
+    assert resolved.refusal is None, resolved.refusal
+
+    resolved = resolved.evidence
     tolerance = resolved.parameter(DEBT_TOLERANCE_PARAMETER)
     assert tolerance is not None
     assert tolerance.value == MAXIMUM_EARLY
@@ -699,7 +774,9 @@ def test_a_name_only_override_being_honored_is_red_sabotage(
         module=scratch,
     )
 
-    assert isinstance(sabotaged, EffectiveRequest)
+    assert sabotaged.refusal is None, sabotaged.refusal
+
+    sabotaged = sabotaged.evidence
     tolerance = sabotaged.parameter(DEBT_TOLERANCE_PARAMETER)
     assert tolerance is not None
     assert tolerance.value == CALLER_ASKS, (
```

## tests/products/test_policy_constraints.py — diff 6a019322..HEAD (M)

```diff
diff --git a/tests/products/test_policy_constraints.py b/tests/products/test_policy_constraints.py
index 6705bc43..7221fa98 100644
--- a/tests/products/test_policy_constraints.py
+++ b/tests/products/test_policy_constraints.py
@@ -63,6 +63,7 @@ from ccf.products.constraints import (
     ConstraintRefusal,
     PinnedConstraint,
     PolicyResolutionConflict,
+    ResolutionOutcome,
     TechnicalCapability,
     applicable,
 )
@@ -71,7 +72,11 @@ from ccf.products.provenance import (
     OverrideRecord,
     ProvenanceSource,
 )
-from ccf.products.request import ProductRequest, ProductRequestContract
+from ccf.products.request import (
+    ProductRequest,
+    ProductRequestContract,
+    ProductRequestViolation,
+)
 from ccf.projection.plan import Perspective
 from ccf.skills.catalog import SkillArgumentProperty, SkillArgumentSchema
 
@@ -265,7 +270,9 @@ def test_case_1_caller_value_over_default() -> None:
     """
     resolved = _resolve(_request(**{TOLERANCE: Decimal(".30")}))
 
-    assert isinstance(resolved, EffectiveRequest)
+    assert resolved.refusal is None, resolved.refusal
+
+    resolved = resolved.evidence
     parameter = resolved.parameter(TOLERANCE)
     assert parameter is not None
     assert parameter.value == Decimal(".30")
@@ -287,7 +294,9 @@ def test_case_2_omission_takes_the_default() -> None:
     """
     resolved = _resolve(_request())
 
-    assert isinstance(resolved, EffectiveRequest)
+    assert resolved.refusal is None, resolved.refusal
+
+    resolved = resolved.evidence
     parameter = resolved.parameter(TOLERANCE)
     assert parameter is not None
     assert parameter.value == Decimal(".25")
@@ -316,7 +325,9 @@ def test_case_3_policy_maximum_bounds_the_caller() -> None:
         _request(**{TOLERANCE: Decimal(".30")}), constraints=(pinned,)
     )
 
-    assert isinstance(resolved, EffectiveRequest)
+    assert resolved.refusal is None, resolved.refusal
+
+    resolved = resolved.evidence
     parameter = resolved.parameter(TOLERANCE)
     assert parameter is not None
     assert parameter.value == Decimal(".20")
@@ -349,7 +360,9 @@ def test_case_4_depth_within_the_technical_limit_is_valid() -> None:
     """
     resolved = _resolve(_request(**{DEPTH: 8}))
 
-    assert isinstance(resolved, EffectiveRequest)
+    assert resolved.refusal is None, resolved.refusal
+
+    resolved = resolved.evidence
     parameter = resolved.parameter(DEPTH)
     assert parameter is not None
     assert parameter.value == 8
@@ -397,7 +410,8 @@ def test_a_refused_request_keeps_the_override_it_attempted() -> None:
     or that it was refused as unentitled.
     """
     technical = _resolve(_request(**{DEPTH: 101}), overrides=_ATTEMPTED)
-    assert isinstance(technical, ConstraintRefusal)
+    assert isinstance(technical.refusal, ConstraintRefusal), technical
+    technical = technical.refusal
     assert technical.overrides == _ATTEMPTED
 
     policy = _resolve(
@@ -405,7 +419,8 @@ def test_a_refused_request_keeps_the_override_it_attempted() -> None:
         constraints=(_pinned(parameter=DEPTH, operator="maximum", value=Decimal(5)),),
         overrides=_ATTEMPTED,
     )
-    assert isinstance(policy, ConstraintRefusal)
+    assert isinstance(policy.refusal, ConstraintRefusal), policy
+    policy = policy.refusal
     assert policy.reason == "bound-exceeded" and policy.bound.authority == "policy"
     assert policy.overrides == _ATTEMPTED
 
@@ -417,13 +432,15 @@ def test_a_refused_request_keeps_the_override_it_attempted() -> None:
         ),
         overrides=_ATTEMPTED,
     )
-    assert isinstance(conflict, PolicyResolutionConflict)
+    assert isinstance(conflict.refusal, PolicyResolutionConflict), conflict
+    conflict = conflict.refusal
     assert conflict.overrides == _ATTEMPTED
 
     # And nothing attempted is the empty tuple — hash-transparent, so a
     # refusal written before the member existed renders as it did.
     bare = _resolve(_request(**{DEPTH: 101}))
-    assert isinstance(bare, ConstraintRefusal)
+    assert isinstance(bare.refusal, ConstraintRefusal), bare
+    bare = bare.refusal
     assert bare.overrides == ()
     assert b"overrides" not in canonical_bytes(bare)
 
@@ -438,7 +455,9 @@ def test_a_depth_over_the_technical_limit_is_refused_by_name() -> None:
     """
     refused = _resolve(_request(**{DEPTH: 101}))
 
-    assert isinstance(refused, ConstraintRefusal)
+    assert isinstance(refused.refusal, ConstraintRefusal), refused
+
+    refused = refused.refusal
     assert refused.reason == "bound-exceeded"
     assert refused.key == DEPTH
     assert refused.requested == 101
@@ -452,7 +471,9 @@ def test_the_technical_bound_never_clamps_the_request() -> None:
     """T-24.6-08: case 4 resolves to 8, and never to the declared 6 or the limit."""
     resolved = _resolve(_request(**{DEPTH: 8}))
 
-    assert isinstance(resolved, EffectiveRequest)
+    assert resolved.refusal is None, resolved.refusal
+
+    resolved = resolved.evidence
     assert resolved.values()[DEPTH] == 8
     assert resolved.values()[DEPTH] != 6
     assert resolved.values()[DEPTH] != Decimal(100)
@@ -471,7 +492,9 @@ def test_two_ceilings_fold_to_the_smaller() -> None:
         ),
     )
 
-    assert isinstance(resolved, EffectiveRequest)
+    assert resolved.refusal is None, resolved.refusal
+
+    resolved = resolved.evidence
     parameter = resolved.parameter(DEPTH)
     assert parameter is not None
     assert parameter.bound is not None
@@ -488,7 +511,9 @@ def test_a_value_over_the_smaller_of_two_ceilings_is_refused() -> None:
         ),
     )
 
-    assert isinstance(refused, ConstraintRefusal)
+    assert isinstance(refused.refusal, ConstraintRefusal), refused
+
+    refused = refused.refusal
     assert refused.reason == "bound-exceeded"
     assert refused.bound.value == Decimal(5)
 
@@ -503,7 +528,9 @@ def test_two_floors_fold_to_the_larger() -> None:
         ),
     )
 
-    assert isinstance(refused, ConstraintRefusal)
+    assert isinstance(refused.refusal, ConstraintRefusal), refused
+
+    refused = refused.refusal
     assert refused.reason == "bound-exceeded"
     assert refused.bound.value == Decimal(8)
     assert refused.bound.operator == "minimum"
@@ -529,7 +556,9 @@ def test_two_allowed_sets_fold_to_their_intersection() -> None:
         ),
     )
 
-    assert isinstance(resolved, EffectiveRequest)
+    assert resolved.refusal is None, resolved.refusal
+
+    resolved = resolved.evidence
     parameter = resolved.parameter(TIER)
     assert parameter is not None
     assert parameter.bound is not None
@@ -556,7 +585,9 @@ def test_a_value_outside_the_intersection_is_not_in_allowed_set() -> None:
         ),
     )
 
-    assert isinstance(refused, ConstraintRefusal)
+    assert isinstance(refused.refusal, ConstraintRefusal), refused
+
+    refused = refused.refusal
     assert refused.reason == "not-in-allowed-set"
     assert refused.key == TIER
     assert refused.requested == "gold"
@@ -584,7 +615,9 @@ def test_a_ceiling_below_a_floor_is_a_policy_resolution_conflict() -> None:
         ),
     )
 
-    assert isinstance(conflict, PolicyResolutionConflict)
+    assert isinstance(conflict.refusal, PolicyResolutionConflict), conflict
+
+    conflict = conflict.refusal
     assert conflict.reason == "policy-resolution-conflict"
     assert conflict.key == DEPTH
     assert conflict.conflicting == (
@@ -615,7 +648,9 @@ def test_an_empty_intersection_is_a_policy_resolution_conflict() -> None:
         ),
     )
 
-    assert isinstance(conflict, PolicyResolutionConflict)
+    assert isinstance(conflict.refusal, PolicyResolutionConflict), conflict
+
+    conflict = conflict.refusal
     assert conflict.key == TIER
     assert conflict.conflicting == (
         ProvenanceSource(kind="artifact", identity="bronze-key", version="2.0.0"),
@@ -653,7 +688,9 @@ def test_priority_orders_the_reported_bound_and_nothing_else() -> None:
     """8 clears both; the reported bound is the higher-priority ceiling."""
     resolved = _resolve(_request(**{DEPTH: 8}), constraints=_non_comparable_pair())
 
-    assert isinstance(resolved, EffectiveRequest)
+    assert resolved.refusal is None, resolved.refusal
+
+    resolved = resolved.evidence
     parameter = resolved.parameter(DEPTH)
     assert parameter is not None
     assert parameter.bound is not None
@@ -671,7 +708,9 @@ def test_a_value_violating_the_lower_priority_bound_is_refused() -> None:
     """2 clears the ceiling that outranks and misses the floor that does not."""
     refused = _resolve(_request(**{DEPTH: 2}), constraints=_non_comparable_pair())
 
-    assert isinstance(refused, ConstraintRefusal)
+    assert isinstance(refused.refusal, ConstraintRefusal), refused
+
+    refused = refused.refusal
     assert refused.reason == "bound-exceeded"
     assert refused.bound.operator == "minimum"
     assert refused.bound.value == Decimal(4)
@@ -699,7 +738,9 @@ def test_a_ceiling_beside_an_allowed_set_both_apply() -> None:
         ),
     )
 
-    assert isinstance(refused, ConstraintRefusal)
+    assert isinstance(refused.refusal, ConstraintRefusal), refused
+
+    refused = refused.refusal
     assert refused.reason == "not-in-allowed-set"
     assert refused.bound.operator == "allowed_set"
 
@@ -719,7 +760,9 @@ def test_a_required_parameter_absent_after_defaults_is_refused() -> None:
         constraints=(_pinned(parameter=TIER, operator="required", value=None),),
     )
 
-    assert isinstance(refused, ConstraintRefusal)
+    assert isinstance(refused.refusal, ConstraintRefusal), refused
+
+    refused = refused.refusal
     assert refused.reason == "required-absent"
     assert refused.key == TIER
     assert refused.requested is None
@@ -733,7 +776,9 @@ def test_a_required_parameter_a_default_supplies_is_not_refused() -> None:
         constraints=(_pinned(parameter=DEPTH, operator="required", value=None),),
     )
 
-    assert isinstance(resolved, EffectiveRequest)
+    assert resolved.refusal is None, resolved.refusal
+
+    resolved = resolved.evidence
     parameter = resolved.parameter(DEPTH)
     assert parameter is not None
     assert parameter.authority == "default"
@@ -762,7 +807,9 @@ def test_a_verified_entitled_override_is_honored() -> None:
         ),
     )
 
-    assert isinstance(resolved, EffectiveRequest)
+    assert resolved.refusal is None, resolved.refusal
+
+    resolved = resolved.evidence
     assert resolved.values()[DEPTH] == 60
     assert resolved.overrides[0].entitled is True
 
@@ -794,7 +841,9 @@ def test_an_unentitled_override_changes_nothing_and_is_still_recorded() -> None:
         ),
     )
 
-    assert isinstance(refused, ConstraintRefusal)
+    assert isinstance(refused.refusal, ConstraintRefusal), refused
+
+    refused = refused.refusal
     assert refused.bound.value == Decimal(50)
 
 
@@ -816,7 +865,9 @@ def test_a_non_overridable_constraint_is_not_yielded_to() -> None:
         ),
     )
 
-    assert isinstance(refused, ConstraintRefusal)
+    assert isinstance(refused.refusal, ConstraintRefusal), refused
+
+    refused = refused.refusal
     assert refused.bound.value == Decimal(50)
 
 
@@ -854,7 +905,9 @@ def test_an_inapplicable_constraint_passed_in_is_ignored() -> None:
         constraints=(wrong_tenant, not_yet_effective, expired),
     )
 
-    assert isinstance(resolved, EffectiveRequest)
+    assert resolved.refusal is None, resolved.refusal
+
+    resolved = resolved.evidence
     assert resolved.values()[DEPTH] == 8
     assert {source.identity for source in resolved.applied}.isdisjoint(
         {"wrong-tenant", "not-yet", "expired"}
@@ -931,7 +984,9 @@ def test_provenance_is_recorded_even_when_nothing_constrained_the_request() -> N
     """
     resolved = _resolve(_request())
 
-    assert isinstance(resolved, EffectiveRequest)
+    assert resolved.refusal is None, resolved.refusal
+
+    resolved = resolved.evidence
     for parameter in resolved.parameters:
         assert parameter.authority
         assert parameter.source.identity
@@ -953,7 +1008,9 @@ def test_preferred_never_refuses() -> None:
         ),
     )
 
-    assert isinstance(resolved, EffectiveRequest)
+    assert resolved.refusal is None, resolved.refusal
+
+    resolved = resolved.evidence
     assert resolved.values()[DEPTH] == 8
     assert len(resolved.guidance) == 1
     assert resolved.guidance[0].operator == "preferred"
@@ -986,11 +1043,11 @@ def test_preferred_refusing_is_red_sabotage(tmp_path: pathlib.Path) -> None:
 
     sabotaged = _resolve(request, constraints=constraints, module=scratch)
 
-    assert type(sabotaged).__name__ == "ConstraintRefusal"
+    assert type(sabotaged.refusal).__name__ == "ConstraintRefusal"
     with pytest.raises(AssertionError):
-        assert type(sabotaged).__name__ == "EffectiveRequest"
+        assert sabotaged.refusal is None
     # And the real module serves the same request.
-    assert isinstance(_resolve(request, constraints=constraints), EffectiveRequest)
+    assert _resolve(request, constraints=constraints).refusal is None
 
 
 # --- (e) priority never erases a hard constraint ------------------------------
@@ -1023,19 +1080,22 @@ def test_priority_never_erases_a_hard_constraint_sabotage(
 
     sabotaged = _resolve(request, constraints=constraints, module=scratch)
 
-    assert type(sabotaged).__name__ == "EffectiveRequest"
+    assert sabotaged.refusal is None
     with pytest.raises(AssertionError):
-        assert type(sabotaged).__name__ == "ConstraintRefusal"
+        assert type(sabotaged.refusal).__name__ == "ConstraintRefusal"
     # And the real module refuses it, naming the outranked floor.
     refused = _resolve(request, constraints=constraints)
-    assert isinstance(refused, ConstraintRefusal)
+    assert isinstance(refused.refusal, ConstraintRefusal), refused
+    refused = refused.refusal
     assert refused.bound.operator == "minimum"
 
 
 # --- (f) the resolution is a record, never a scalar ---------------------------
 
 COLLAPSE_NEEDLE = "    return resolved\n"
-COLLAPSE_SABOTAGE = "    return resolved.values()  # type: ignore[return-value]\n"
+COLLAPSE_SABOTAGE = (
+    "    return resolved.evidence.values()  # type: ignore[return-value]\n"
+)
 
 
 def _assert_provenance_survives(resolved: Any) -> None:
@@ -1084,7 +1144,8 @@ def test_provenance_is_never_a_scalar_sabotage(tmp_path: pathlib.Path) -> None:
 
     # And the real module answers it.
     resolved = _resolve(request)
-    assert isinstance(resolved, EffectiveRequest)
+    assert resolved.refusal is None, resolved.refusal
+    resolved = resolved.evidence
     _assert_provenance_survives(resolved)
 
 
@@ -1104,3 +1165,201 @@ def test_no_sabotage_edits_the_real_source_tree() -> None:
     assert source.count(PRIORITY_NEEDLE) == 1
     assert source.count(COLLAPSE_NEEDLE) == 1
     assert "never dropped because another outranks it" in source
+
+
+# --- (h) the paired outcome: every exit carries what resolution established ----
+#
+# `D-IMPL-264` D-08 (Dave, `24.7-RULINGS.md` §3 Q8): *"a common resolution
+# outcome shape: completed request or governed refusal, both with the
+# resolution evidence accumulated so far."* One test per exit of
+# `resolve_effective_request`, in the order the exits occur in the function;
+# what each asserts is the evidence RESEARCH § Measurement 8 measured to be in
+# scope at that exit. Criterion 12.
+
+#: The three refusal classes' field rosters as measured at the phase base
+#: (`9a2e4bcf`) by `sorted(C.model_fields)`. Criterion 12: the paired outcome
+#: adds the evidence BESIDE the refusal, never as a field cloned into it — so
+#: these rosters must not grow. Spelled as the fixture's own constants rather
+#: than read off the classes, because a roster read off the thing it guards
+#: guards nothing.
+CONSTRAINT_REFUSAL_FIELDS = frozenset(
+    {"bound", "detail", "key", "overrides", "reason", "requested"}
+)
+POLICY_RESOLUTION_CONFLICT_FIELDS = frozenset(
+    {"conflicting", "detail", "key", "overrides", "reason"}
+)
+PRODUCT_REQUEST_VIOLATION_FIELDS = frozenset(
+    {
+        "declared_keys",
+        "declared_type",
+        "detail",
+        "key",
+        "overrides",
+        "presented_keys",
+        "presented_type",
+        "reason",
+    }
+)
+
+#: The fixture capability's provenance, as the resolution records it — a
+#: capability identity and never an artifact pin.
+CAPABILITY_SOURCE = ProvenanceSource(
+    kind="capability", identity=CAPABILITY.identity, version=None
+)
+
+
+def _constraint_source(key: str, version: str = "1.0.0") -> ProvenanceSource:
+    """The pin a `_pinned` constraint is recorded under in `applied`."""
+    return ProvenanceSource(kind="artifact", identity=key, version=version)
+
+
+def test_the_conflict_exit_carries_the_evidence_accumulated_so_far() -> None:
+    """Exit 1: the fold found a contradiction — and both defaults, the caller's
+    value, every consulted pin and the override attempts are on the evidence."""
+    outcome = _resolve(
+        _request(**{DEPTH: 4}),
+        constraints=(
+            _pinned(parameter=DEPTH, operator="maximum", value=Decimal(3), key="c"),
+            _pinned(parameter=DEPTH, operator="minimum", value=Decimal(9), key="f"),
+        ),
+        overrides=_ATTEMPTED,
+    )
+
+    assert isinstance(outcome, ResolutionOutcome)
+    assert isinstance(outcome.refusal, PolicyResolutionConflict), outcome
+    assert outcome.completed is False
+    evidence = outcome.evidence
+    assert isinstance(evidence, EffectiveRequest)
+    assert evidence.values() == {TOLERANCE: Decimal(".25"), DEPTH: 4}
+    depth = evidence.parameter(DEPTH)
+    assert depth is not None and depth.authority == "caller"
+    tolerance = evidence.parameter(TOLERANCE)
+    assert tolerance is not None and tolerance.authority == "default"
+    assert DECLARED_SOURCE in evidence.applied
+    assert _constraint_source("c") in evidence.applied
+    assert _constraint_source("f") in evidence.applied
+    assert evidence.overrides == _ATTEMPTED
+    assert evidence.asked_at == INSTANT
+
+
+def test_the_required_absent_exit_carries_the_evidence_accumulated_so_far() -> None:
+    """Exit 2: presence refused — the defaults resolved before it are on the
+    evidence, the requiring constraint's pin is in `applied`, and the absent
+    key has no record (the positive statement *nothing was presented*)."""
+    outcome = _resolve(
+        _request(),
+        constraints=(
+            _pinned(parameter=TIER, operator="required", value=None, key="presence"),
+        ),
+    )
+
+    assert isinstance(outcome.refusal, ConstraintRefusal), outcome
+    assert outcome.refusal.reason == "required-absent"
+    evidence = outcome.evidence
+    assert evidence.values() == {TOLERANCE: Decimal(".25"), DEPTH: 6}
+    assert evidence.parameter(TIER) is None
+    assert DECLARED_SOURCE in evidence.applied
+    assert _constraint_source("presence") in evidence.applied
+
+
+def test_the_bound_refusal_exit_carries_the_bounds_attached_to_earlier_keys() -> None:
+    """Exit 3: a policy ceiling refused the depth — and the tolerance ceiling
+    that folded FIRST (worked case 3, the one clamp) is on the evidence with
+    authority `policy` and its bound attached, exactly as it was resolved."""
+    outcome = _resolve(
+        _request(**{TOLERANCE: Decimal(".30"), DEPTH: 10}),
+        constraints=(
+            _pinned(parameter=TOLERANCE, operator="maximum", value=Decimal(".20"), key="t"),
+            _pinned(parameter=DEPTH, operator="maximum", value=Decimal(5), key="d"),
+        ),
+    )
+
+    refusal = outcome.refusal
+    assert isinstance(refusal, ConstraintRefusal), outcome
+    assert refusal.key == DEPTH and refusal.bound.authority == "policy"
+    tolerance = outcome.evidence.parameter(TOLERANCE)
+    assert tolerance is not None
+    assert tolerance.authority == "policy" and tolerance.value == Decimal(".20")
+    assert tolerance.bound is not None
+    assert tolerance.bound.source == _constraint_source("t")
+    # The refused value is still the caller's on the evidence: nothing clamped.
+    depth = outcome.evidence.parameter(DEPTH)
+    assert depth is not None and depth.value == 10 and depth.authority == "caller"
+    assert _constraint_source("t") in outcome.evidence.applied
+    assert _constraint_source("d") in outcome.evidence.applied
+
+
+def test_the_capability_exit_carries_the_technical_bounds_attached_so_far() -> None:
+    """Exit 4: the technical ceiling refused the depth — and the technical bound
+    already attached to the parameter bound before it is on the evidence, with
+    the capability's own provenance in `applied`."""
+    outcome = _resolve(
+        _request(**{DEPTH: 101}),
+        capability_bindings={
+            TOLERANCE: CAPABILITY_TRAVERSAL_DEPTH,
+            DEPTH: CAPABILITY_TRAVERSAL_DEPTH,
+        },
+    )
+
+    refusal = outcome.refusal
+    assert isinstance(refusal, ConstraintRefusal), outcome
+    assert refusal.key == DEPTH and refusal.bound.authority == "technical"
+    tolerance = outcome.evidence.parameter(TOLERANCE)
+    assert tolerance is not None and tolerance.bound is not None
+    assert tolerance.bound.authority == "technical"
+    assert tolerance.bound.source == CAPABILITY_SOURCE
+    assert CAPABILITY_SOURCE in outcome.evidence.applied
+    assert DECLARED_SOURCE in outcome.evidence.applied
+
+
+def test_the_validation_exit_carries_the_full_effective_set_and_the_overrides() -> None:
+    """Exit 5: conformity refused an effective value — the WHOLE effective set
+    was resolved (defaults, caller, capability consulted) and rides with the
+    refusal, as do the override attempts, on both halves."""
+    outcome = _resolve(_request(**{"undeclared": 1}), overrides=_ATTEMPTED)
+
+    refusal = outcome.refusal
+    assert isinstance(refusal, ProductRequestViolation), outcome
+    assert refusal.reason == "undeclared-parameter"
+    assert refusal.overrides == _ATTEMPTED
+    evidence = outcome.evidence
+    assert evidence.values() == {TOLERANCE: Decimal(".25"), DEPTH: 6, "undeclared": 1}
+    assert evidence.overrides == _ATTEMPTED
+    assert CAPABILITY_SOURCE in evidence.applied
+    assert DECLARED_SOURCE in evidence.applied
+
+
+def test_the_completion_exit_evidence_is_the_effective_request_as_before() -> None:
+    """Exit 6: completed — `refusal` is stated `None`, and `evidence` is exactly
+    the `EffectiveRequest` the function returned bare before D-08."""
+    outcome = _resolve(_request(**{TOLERANCE: Decimal(".30")}))
+
+    assert outcome.refusal is None
+    assert outcome.completed is True
+    assert isinstance(outcome.evidence, EffectiveRequest)
+    assert outcome.evidence.values() == {TOLERANCE: Decimal(".30"), DEPTH: 6}
+    assert outcome.evidence.applied == (DECLARED_SOURCE, CAPABILITY_SOURCE)
+    assert outcome.evidence.overrides == ()
+    assert outcome.evidence.guidance == ()
+
+
+def test_the_three_refusal_classes_gained_no_resolution_field() -> None:
+    """Criterion 12 — Q8's second sentence, measured against the phase-base
+    rosters: *"rather than cloning resolution fields into multiple refusal
+    classes."* The outcome has exactly its two members."""
+    assert set(ConstraintRefusal.model_fields) == CONSTRAINT_REFUSAL_FIELDS
+    assert set(PolicyResolutionConflict.model_fields) == POLICY_RESOLUTION_CONFLICT_FIELDS
+    assert set(ProductRequestViolation.model_fields) == PRODUCT_REQUEST_VIOLATION_FIELDS
+    assert set(ResolutionOutcome.model_fields) == {"evidence", "refusal"}
+
+
+def test_the_outcome_requires_both_members_stated() -> None:
+    """Neither member is defaulted (`D-IMPL-264` P-2: absence is stated, never
+    inferred from omission). Omitting either is refused at construction."""
+    evidence = _resolve(_request()).evidence
+
+    with pytest.raises(ValueError, match="refusal"):
+        ResolutionOutcome(evidence=evidence)  # type: ignore[call-arg]
+    with pytest.raises(ValueError, match="evidence"):
+        ResolutionOutcome(refusal=None)  # type: ignore[call-arg]
+    assert ResolutionOutcome(evidence=evidence, refusal=None).completed is True
```


---
End of bundle-tests-part-1.md. Read-proof, again:
```
READ-PROOF bundle-tests-part-1.md: 7fef7e412f4016c6
```
