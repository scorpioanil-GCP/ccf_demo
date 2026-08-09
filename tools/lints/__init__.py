"""CCF invariant lints — CINV-01/02/03/04 and friends (SDK-defined; CLAUDE.md §6.4, §7.3, §11).

Stdlib-only checkers, hand-rolled per D-06 (no plugin framework), run as one
blocking CI gate per D-07 (`python -m tools.lints --all`):

* ``no_hardcoding``          — CINV-01, the No-Hardcoding Rule (CLAUDE.md §6.4)
* ``harness_imports``        — CINV-02, zero harness imports in core (§7.3)
* ``backend_imports``        — CINV-02, no adapter import outside the adapter
  package (D-IMPL-93 property (1))
* ``algorithmic``            — CINV-03, Algorithmic - Semantic Alternation (§11)
* ``substrate_names``        — CINV-04, no substrate name in core, two rule ids
  under one walk (D-IMPL-93 property (2))
* ``orchestration_imports``  — D-06, the orchestration/adapters split
* ``citations``              — cross-file citation drift (SDK-defined)

The first six are **per-file AST** checkers and expose the same pair of
entrypoints, so the runner can treat them uniformly::

    check_source(source: str, path: Path, module_name: str) -> list[str]
    check(path: Path, module_name: str) -> list[str]

``substrate_names`` adds an optional trailing ``base=`` keyword to both — its
vocabulary is read from the adapter package on disk, and a test pinning a
synthetic package needs to say which disk. The positional pair is unchanged, so
it registers in ``CHECKERS`` like any other per-file checker.

``citations`` is the one **whole-tree text** checker — a citation is a claim
about a *second* file and lives in prose as much as in code, so it takes the
repo root instead::

    check_tree(base: Path) -> list[str]

All seven agree on the finding format: ``"{path}:{lineno} {rule} {message}"``.
The rule token is always the second whitespace-separated field; the runner and
the allowlist both key off it — and only ``no_hardcoding`` findings are ever
offered to the allowlist (D-13).
"""

from __future__ import annotations

import ast
import pathlib
from typing import Iterable

__all__ = ["format_finding", "imported_module_names", "matches_module", "read_tree"]


def format_finding(path: pathlib.Path, lineno: int, rule: str, message: str) -> str:
    """Render one finding in the shared ``path:line rule message`` format."""
    return f"{path}:{lineno} {rule} {message}"


def read_tree(source: str, path: pathlib.Path) -> ast.Module:
    """Parse `source`, attributing syntax errors to `path`."""
    return ast.parse(source, filename=str(path))


def imported_module_names(node: ast.AST) -> list[str]:
    """Dotted module names an Import/ImportFrom node brings into scope.

    Relative imports (``from . import x``) carry no absolute module name and are
    reported as an empty list — the checkers only reason about absolute names.
    """
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        if node.level or not node.module:
            return []
        return [node.module]
    return []


def matches_module(name: str, prefixes: Iterable[str]) -> bool:
    """True when `name` equals or is a dotted descendant of any prefix.

    Dot-bounded so ``langgraphql`` never matches the ``langgraph`` deny entry.
    """
    return any(name == p or name.startswith(p + ".") for p in prefixes)
