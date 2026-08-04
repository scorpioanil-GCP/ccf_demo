"""`python -m tools.lints` — the blocking CI gate for CINV-01/02/03 (D-07).

Walks the linted trees (`src/`, `runtime/`, `examples/`, `tests/`), derives
each file's dotted module name from its path, runs the selected checkers,
applies the D-08 allowlist to CINV-01 findings, prints what survives, and
exits nonzero if anything does. Not every rule runs over every tree — see
`RULE_TREE_SCOPE`.

Exit code is the only gate signal. There is deliberately no report-only,
warning-only, or `--exit-zero` mode: D-07 requires the lints to block from the
first fabric commit, and a non-blocking mode is how an invariant quietly stops
being one.

Usage::

    python -m tools.lints --all
    python -m tools.lints --harness-imports --algorithmic
"""

from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Callable, Iterator, Sequence

from tools.lints import (
    algorithmic,
    harness_imports,
    no_hardcoding,
    orchestration_imports,
)

#: Trees that are linted, and the package root each one contributes.
#: (directory, strip_prefix) — module names are derived relative to the root
#: that actually holds the package, so `src/ccf/x.py` is `ccf.x`.
LINTED_TREES: tuple[str, ...] = ("src", "runtime", "examples", "tests")

#: Per-rule tree scoping — the lint posture over ``/examples``, stated in
#: config rather than left to path accident (plan 08-01; 08-RESEARCH.md Open
#: Question 3). CINV-01 (No-Hardcoding) covers ``examples`` because CLAUDE.md
#: §6.4 applies the rule to ``/src``, ``/runtime``, and ``/examples`` alike.
#: CINV-02 (harness imports) is scoped OFF the examples tree: CLAUDE.md §7.3
#: words the invariant as "zero harness imports in **core**", and example 03
#: (harness portability) necessarily imports harness SDKs. The exemption is
#: this config surface — not an allowlist entry, and not merely a test
#: assertion. Rules absent from this mapping run over every linted tree.
#:
#: The ``harness-imports`` checker carries three rules under one AST walk —
#: ``cinv02-harness``, ``cinv02-graph-writer``, and ``cinv02-deployment-gates``
#: (the D-15A ban on ``ccf.deployment`` importing ``ccf.products.gates``). All
#: three share this checker's ``("src", "runtime")`` scope, which already covers
#: ``ccf.deployment``; the third rule needs no ``CHECKERS`` key of its own, and
#: naming it here keeps the config surface an honest description of what runs.
#:
#: CINV-01 also covers ``tests`` (D-IMPL-78, Dave, 2026-08-04; plan 15-04).
#: D-09 relocates the example CI assertions into ``tests/``, and those
#: assertions carry domain expectations read from ``expected:`` artifact
#: blocks. Without this scope the relocation would move domain values out of
#: a structural invariant's reach with every CI gate still green — a
#: CI-invisible weakening arrived at as a side effect of an ergonomics
#: change. The other three rules stay ``("src", "runtime")`` deliberately:
#: test modules exercising the harness adapters import harness SDKs and
#: would trip CINV-02, and the invariant is worded over core (CLAUDE.md
#: §7.3). As with ``/examples``, the exemption surface is this config file —
#: not an allowlist entry, and not merely a test assertion.
RULE_TREE_SCOPE: dict[str, tuple[str, ...]] = {
    "no-hardcoding": ("src", "runtime", "examples", "tests"),
    "harness-imports": ("src", "runtime"),
    "algorithmic": ("src", "runtime"),
    "orchestration-imports": ("src", "runtime"),
}

#: Directories never worth walking.
SKIP_DIRS: frozenset[str] = frozenset(
    {"__pycache__", ".git", ".venv", "venv", "build", "dist", ".mypy_cache"}
)

Checker = Callable[[pathlib.Path, str], list[str]]

CHECKERS: dict[str, Checker] = {
    "no-hardcoding": no_hardcoding.check,
    "harness-imports": harness_imports.check,
    "algorithmic": algorithmic.check,
    "orchestration-imports": orchestration_imports.check,
}


def module_name_for(path: pathlib.Path, root: pathlib.Path) -> str:
    """Dotted module name for `path` relative to the linted tree `root`.

    ``src/ccf/operators/traversal.py`` -> ``ccf.operators.traversal``;
    ``src/ccf/__init__.py`` -> ``ccf``.
    """
    parts = list(path.relative_to(root).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def iter_python_files(root: pathlib.Path) -> Iterator[pathlib.Path]:
    """Yield every `.py` file under `root`, skipping build/VCS noise."""
    for path in sorted(root.rglob("*.py")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def run(
    base: pathlib.Path,
    rules: Sequence[str],
    allowlist: no_hardcoding.Allowlist | None = None,
) -> list[str]:
    """Run `rules` over every linted tree under `base`; return the findings."""
    active = allowlist if allowlist is not None else no_hardcoding.load_allowlist()
    findings: list[str] = []

    for tree in LINTED_TREES:
        root = base / tree
        if not root.is_dir():
            continue
        for path in iter_python_files(root):
            module_name = module_name_for(path, root)
            for rule in rules:
                if tree not in RULE_TREE_SCOPE.get(rule, LINTED_TREES):
                    continue
                found = CHECKERS[rule](path, module_name)
                if rule == "no-hardcoding":
                    found = no_hardcoding.apply_allowlist(found, active)
                findings.extend(found)

    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.lints",
        description=(
            "CCF invariant lints. Blocking by design (D-07): nonzero exit on any"
            " finding, and no report-only mode exists."
        ),
    )
    parser.add_argument("--all", action="store_true", help="run every checker")
    parser.add_argument(
        "--no-hardcoding",
        dest="selected",
        action="append_const",
        const="no-hardcoding",
        help="CINV-01 (CLAUDE.md §6.4)",
    )
    parser.add_argument(
        "--harness-imports",
        dest="selected",
        action="append_const",
        const="harness-imports",
        help="CINV-02 (CLAUDE.md §7.3)",
    )
    parser.add_argument(
        "--algorithmic",
        dest="selected",
        action="append_const",
        const="algorithmic",
        help="CINV-03 (CLAUDE.md §11)",
    )
    parser.add_argument(
        "--orchestration-imports",
        dest="selected",
        action="append_const",
        const="orchestration-imports",
        help="D-06 orchestration/adapters split (D-IMPL-60)",
    )
    parser.add_argument(
        "--base",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        help="repo root to lint (default: cwd)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rules = list(CHECKERS) if args.all or not args.selected else args.selected

    findings = run(args.base, rules)
    for finding in findings:
        print(finding)

    if findings:
        print(
            f"\n{len(findings)} CCF invariant violation(s)."
            " Fix the code, or — for CINV-01 only — add a reviewed entry to"
            " tools/lints/allowlist.yaml.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
