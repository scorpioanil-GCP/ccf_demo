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
carries `asserts + prints`; the ERGO-03 audit module under `tests/examples/`
asserted structurally that no combined figure was ever produced.

The audit module retired, this tool did not
-------------------------------------------

**Retired 2026-08-10** — `docs/DECISIONS.md` `D-IMPL-94`, recording Phase 16
`D-15`. Phase 16 rebuilds `examples/` greenfield, which makes a comparison
against the Phase-15-start baseline meaningless rather than merely stale, so the
standing check was frozen and removed rather than re-baselined (which would have
destroyed the Phase 15 comparison — see the `--baseline` help text) or deleted
without capture (which would have erased a Complete requirement's evidence).

This tool is unaffected: it still measures, `make measure-examples` still writes
`after/`, and both fragment directories stay committed. What no longer exists is
the module that pinned the achieved numbers. The frozen measurement, with the
tree SHA it was taken at, is `docs/surface/examples/ERGO-03-FROZEN.md`; the
narrative is `docs/SURFACE-AUDIT.md` §2, and §2.5 records the retirement.

Why one fragment per file
-------------------------

The baseline is written as one JSON fragment per measured file under
`docs/surface/examples/before/`, not as a single aggregate document, so that
the eight example-rewrite plans can each write their own `after/` fragment in
parallel worktrees without colliding on a shared file.

Which directory gets written
----------------------------

`after/` is the default write target and `before/` requires `--baseline`,
because the two have opposite lifetimes: `after/` is rewritten by each example
rewrite, while `before/` is the phase-start record that must not move — it is
the whole "before" side of the Criterion 1 comparison. Defaulting to `before/`
would mean every rewrite plan running `make measure-examples`, as those plans
instruct, silently overwrote the baseline it was supposed to be measured
against, leaving the audit comparing the rewritten tree to itself and
reporting no change where the real answer was the phase's headline number.
`--only PREFIX` narrows a run to one example so parallel worktrees do not
overwrite each other's fragments.

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

#: The phase-close re-measurement, written per-example by the rewrite plans.
#: The retired ERGO-03 audit module read this directory to produce the four
#: separate figures Criterion 1 reports; the last such reading is frozen at
#: ``docs/surface/examples/ERGO-03-FROZEN.md`` (D-IMPL-94 / Phase 16 D-15).
AFTER_DIR = REPO_ROOT / "docs" / "surface" / "examples" / "after"

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


def measure_tree(only: str | None = None) -> dict[str, dict[str, Any]]:
    """Fragment name -> measurement, for every example module.

    ``only`` restricts the measurement to modules whose repo-relative path
    starts with the given prefix. That filter is what lets the eight
    example-rewrite plans each write their own ``after/`` fragments from
    parallel worktrees: a plan rewriting ``examples/01-agent-basics`` passes
    that prefix and cannot touch another plan's fragments even by accident.
    Without it, every plan would rewrite all fragments on every run and the
    last worktree merged would silently win.
    """
    emitted: dict[str, dict[str, Any]] = {}
    for path in example_files():
        measurement = measure_file(path)
        if only is not None and not measurement["path"].startswith(only):
            continue
        emitted[fragment_name(measurement["path"])] = measurement
    return emitted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Measure the mechanical surface of examples/ (ERGO-03). Writes"
            " after/ fragments by default; the before/ baseline is written"
            " only under --baseline, because it is the phase-start record."
        )
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help=(
            "Write nothing; exit 1 if any committed after/ fragment differs"
            " from a fresh measurement. The CI mode. Vacuous until the first"
            " example is rewritten, which is correct — an unrewritten example"
            " has nothing to be stale against."
        ),
    )
    mode.add_argument(
        "--baseline",
        action="store_true",
        help=(
            "Rewrite the before/ baseline. Phase-start only — this is the"
            " immutable 'before' side of Criterion 1, and rewriting it"
            " mid-phase destroys the comparison the audit reports."
        ),
    )
    parser.add_argument(
        "--only",
        metavar="PREFIX",
        default=None,
        help=(
            "Restrict to modules whose repo-relative path starts with PREFIX"
            " (e.g. examples/01-agent-basics). Each example-rewrite plan"
            " passes its own prefix so parallel worktrees cannot overwrite"
            " one another's fragments."
        ),
    )
    args = parser.parse_args(argv)

    emitted = measure_tree(args.only)

    if not emitted:
        print(
            f"No example modules matched --only {args.only!r}. Nothing was"
            " written. Check the prefix against a repo-relative path such as"
            " examples/00-quickstart.",
            file=sys.stderr,
        )
        return 1

    if args.check:
        divergent: list[str] = []
        for name, measurement in emitted.items():
            fragment = AFTER_DIR / name
            if not fragment.exists():
                continue
            if fragment.read_text(encoding="utf-8") != serialize(measurement):
                divergent.append(name)
        if divergent:
            print(
                "These after/ fragments no longer match a fresh measurement: "
                + ", ".join(sorted(divergent))
                + ". A rewritten example grew or shrank without its recorded"
                " number moving with it, which would let the Criterion 1"
                " report claim a win the tree no longer delivers. Re-measure"
                " with `make measure-examples ONLY=<path prefix>` and review"
                " the diff.",
                file=sys.stderr,
            )
            return 1
        return 0

    target = BEFORE_DIR if args.baseline else AFTER_DIR
    target.mkdir(parents=True, exist_ok=True)
    for name, measurement in emitted.items():
        (target / name).write_text(serialize(measurement), encoding="utf-8")
    print(f"wrote {len(emitted)} fragments to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
