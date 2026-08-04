"""ERGO-03 — measure the examples tree's mechanical surface by AST (D-11, D-12).

Success Criterion 1 of Phase 15 is an audit of how much of `/examples` is
mechanical marshalling the SDK could supply. D-11 makes that audit a
phase-close report and D-12 forbids a numeric target, so the audit's honesty
rests entirely on the before-numbers being *measured* rather than estimated.
The ROADMAP's own quickstart breakdown was wrong in both directions
(15-RESEARCH.md §1.1) — it over-counted assertions and under-counted
marshalling. This tool exists so that class of error cannot repeat: the
phase-close number is a re-measurement by the same code that produced the
phase-start number.

Relocation is not removal
-------------------------

The two headline figures are reported under deliberately separate keys and
must never be summed into one headline figure: D-09 **relocates** assertions
and prints into `tests/`, while the helper and wiring work is **removed**, and
D-12's stated risk is a target being hit by moving lines rather than removing
work. `removable` therefore carries the mechanical total and `relocatable`
carries `asserts + prints`; `tests/examples/test_surface_audit.py` asserts
structurally that no combined figure is ever produced.

Why one fragment per file
-------------------------

The baseline is written as one JSON fragment per measured file under
`docs/surface/examples/before/`, not as a single aggregate document, so that
the eight example-rewrite plans can each write their own `after/` fragment in
parallel worktrees without colliding on a shared file.

Measurement method (15-RESEARCH.md §1 Method)
---------------------------------------------

Per Python file under `examples/`, three AST passes produce line *sets* which
are then made disjoint in the order `helpers`, `opblk`, `boot`, `reg` so that a
line is never counted twice:

- `helpers` — summed spans of `FunctionDef` nodes named `_load`, `_instant`,
  `_resolution_spec`, `_envelopes`, `_consumer_resolution_spec`, `_registry`.
- `opblk` — the span from the `OperatorRegistry()` call to the last
  `operators.register(...)` call, or the whole span of a `FunctionDef` named
  `_operators` where the block was already extracted into one.
- `boot` — the span of the `boot(...)` call.
- `reg` — summed spans of `registry.register`, `parse_artifact`,
  `register_product_class`, `Perspective`, and `MaxTTL` calls.

`mech` is the size of their union. `asserts`, `prints`, and `imports` are
counted from `ast.Assert` nodes, `print(...)` expression statements, and
import statements respectively.
"""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

#: The tree whose mechanical surface Criterion 1 audits.
EXAMPLES_ROOT = REPO_ROOT / "examples"

#: The phase-start baseline, one fragment per measured file.
BEFORE_DIR = REPO_ROOT / "docs" / "surface" / "examples" / "before"

#: Marshalling helpers extracted as named functions (15-RESEARCH.md §1 pass 2).
HELPER_NAMES = frozenset(
    {
        "_load",
        "_instant",
        "_resolution_spec",
        "_envelopes",
        "_consumer_resolution_spec",
        "_registry",
    }
)

#: The operator block, where a file has already lifted it into a function.
OPERATOR_FUNCTION_NAME = "_operators"

#: Control Plane registration cluster (15-RESEARCH.md §1 pass 3).
REGISTRATION_CALL_NAMES = frozenset(
    {
        "parse_artifact",
        "register_product_class",
        "Perspective",
        "MaxTTL",
    }
)


def _span(node: ast.AST) -> set[int]:
    """Every source line the node occupies."""
    start = getattr(node, "lineno", None)
    if start is None:
        return set()
    end = getattr(node, "end_lineno", None) or start
    return set(range(start, end + 1))


def _called_name(call: ast.Call) -> str | None:
    """The bare name of a direct `name(...)` call, else None."""
    func = call.func
    return func.id if isinstance(func, ast.Name) else None


def _method_call(call: ast.Call, receiver: str, method: str) -> bool:
    """True for `receiver.method(...)` on a plain name receiver."""
    func = call.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == method
        and isinstance(func.value, ast.Name)
        and func.value.id == receiver
    )


def measure_source(source: str) -> dict[str, Any]:
    """Run the three AST passes over one module's source text."""
    tree = ast.parse(source)
    nodes = list(ast.walk(tree))

    helpers: set[int] = set()
    opblk: set[int] = set()
    boot: set[int] = set()
    reg: set[int] = set()
    asserts: set[int] = set()
    prints: set[int] = set()
    imports: set[int] = set()

    operator_registry_starts: list[int] = []
    operator_register_ends: list[int] = []

    for node in nodes:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if node.name in HELPER_NAMES:
                helpers |= _span(node)
            elif node.name == OPERATOR_FUNCTION_NAME:
                opblk |= _span(node)
        elif isinstance(node, ast.Assert):
            asserts |= _span(node)
        elif isinstance(node, ast.Import | ast.ImportFrom):
            imports |= _span(node)
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            if _called_name(node.value) == "print":
                prints |= _span(node)

    for node in nodes:
        if not isinstance(node, ast.Call):
            continue
        name = _called_name(node)
        if name == "OperatorRegistry":
            operator_registry_starts.append(node.lineno)
        elif name == "boot":
            boot |= _span(node)
        elif name in REGISTRATION_CALL_NAMES:
            reg |= _span(node)
        elif _method_call(node, "operators", "register"):
            operator_register_ends.append(node.end_lineno or node.lineno)
        elif _method_call(node, "registry", "register"):
            reg |= _span(node)

    if operator_registry_starts and operator_register_ends:
        opblk |= set(
            range(min(operator_registry_starts), max(operator_register_ends) + 1)
        )

    # Disjoint in precedence order so no line is counted twice.
    opblk -= helpers
    boot -= helpers | opblk
    reg -= helpers | opblk | boot

    mech = helpers | opblk | boot | reg
    relocatable = len(asserts | prints)

    return {
        "raw": len(source.splitlines()),
        "helpers": len(helpers),
        "opblk": len(opblk),
        "boot": len(boot),
        "reg": len(reg),
        "mech": len(mech),
        "asserts": len(asserts),
        "prints": len(prints),
        "imports": len(imports),
        # D-09/D-12: removal and relocation are separate figures. See the
        # module docstring — these two keys are never summed.
        "removable": len(mech),
        "relocatable": relocatable,
    }


def measure_file(path: pathlib.Path) -> dict[str, Any]:
    """Measure one example module, keyed by its repo-relative path."""
    relative = path.relative_to(REPO_ROOT).as_posix()
    measurement = measure_source(path.read_text(encoding="utf-8"))
    return {"path": relative, **measurement}


def example_files() -> list[pathlib.Path]:
    """Every Python module under `examples/`, in deterministic order."""
    return sorted(EXAMPLES_ROOT.rglob("*.py"))


def fragment_name(relative_path: str) -> str:
    """Slugify a repo-relative path into a collision-free fragment name."""
    return relative_path.replace("/", "__").removesuffix(".py") + ".json"


def serialize(measurement: dict[str, Any]) -> str:
    """The one serialization recipe — shared with the audit test."""
    return json.dumps(measurement, indent=2, sort_keys=True) + "\n"


def measure_tree() -> dict[str, dict[str, Any]]:
    """Fragment name -> measurement, for every example module."""
    emitted: dict[str, dict[str, Any]] = {}
    for path in example_files():
        measurement = measure_file(path)
        emitted[fragment_name(measurement["path"])] = measurement
    return emitted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Measure the mechanical surface of examples/ and write the"
            " per-file baseline fragments (ERGO-03)."
        )
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Write nothing; exit 1 if any committed fragment differs from a"
            " fresh measurement."
        ),
    )
    args = parser.parse_args(argv)

    emitted = measure_tree()

    if args.check:
        divergent: list[str] = []
        for name, measurement in emitted.items():
            fragment = BEFORE_DIR / name
            if not fragment.exists():
                continue
            if fragment.read_text(encoding="utf-8") != serialize(measurement):
                divergent.append(name)
        if divergent:
            print(
                "These baseline fragments differ from a fresh measurement: "
                + ", ".join(sorted(divergent))
                + ". Run `make measure-examples` and review the diff — the"
                " before/ baseline is the phase-start record and should not"
                " move.",
                file=sys.stderr,
            )
            return 1
        return 0

    BEFORE_DIR.mkdir(parents=True, exist_ok=True)
    for name, measurement in emitted.items():
        (BEFORE_DIR / name).write_text(serialize(measurement), encoding="utf-8")
    print(f"wrote {len(emitted)} fragments to {BEFORE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
