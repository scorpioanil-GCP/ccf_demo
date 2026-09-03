"""CCF invariant lints — CINV-01/02/03/04/06 and friends (SDK-defined; CLAUDE.md §6.4, §7.3, §7.4, §11).

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
* ``hash_transparent_key``   — CINV-06, every sentinel-defaulted ``CCFContract``
  field NEW since ``13bd250`` declares ``ccf_hash_transparent`` (D-IMPL-243
  amendments 1 and 2; §7.4). Its universe is bounded by the committed base
  roster ``hash_transparent_base_roster.json``, generated and drift-checked
  by ``base_roster.py`` (``--check``); CINV-05 is reserved by D-GATE-15.4
  ruling (3).

The first six are **per-file AST** checkers and expose the same pair of
entrypoints, so the runner can treat them uniformly::

    check_source(source: str, path: Path, module_name: str) -> list[str]
    check(path: Path, module_name: str) -> list[str]

``substrate_names`` adds an optional trailing ``base=`` keyword to both — its
vocabulary is read from the adapter package on disk, and a test pinning a
synthetic package needs to say which disk. The positional pair is unchanged, so
it registers in ``CHECKERS`` like any other per-file checker.

``citations`` and ``hash_transparent_key`` are the two registered
**whole-tree** checkers and take the repo root instead — a citation is a
claim about a *second* file and lives in prose as much as in code; a
``CCFContract`` subclass is a fact about the whole tree because subclassing
crosses files::

    check_tree(base: Path) -> list[str]

All eight agree on the finding format: ``"{path}:{lineno} {rule} {message}"``.
The rule token is always the second whitespace-separated field; the runner and
the allowlist both key off it — and only ``no_hardcoding`` findings are ever
offered to the allowlist (D-13).

Relative imports (review finding F3)
------------------------------------

``from .graph.backends import sqlite_write`` reaches an adapter exactly as
surely as the absolute spelling does, and both name helpers below used to
report ``[]`` for it — so every rule built on them was blind to the whole
relative family. Resolving a relative import needs the *importing* module's
package, which every checker already has, so the helpers take it as an
optional ``package=`` keyword and :func:`package_for` derives it from the pair
each ``check_source`` is handed.

The keyword defaults to ``""`` (unknown package), which reproduces the old
"report nothing for a relative import" behaviour rather than guessing. A
checker that does not pass it is not silently wrong in a new way; it is exactly
as blind as it was, which is the property a shared helper should have when a
caller declines the new argument.
"""

from __future__ import annotations

import ast
import pathlib
from typing import Iterable

__all__ = [
    "format_finding",
    "imported_module_names",
    "matches_module",
    "package_for",
    "read_tree",
    "reached_module_names",
    "submodule_import_names",
]


def format_finding(path: pathlib.Path, lineno: int, rule: str, message: str) -> str:
    """Render one finding in the shared ``path:line rule message`` format."""
    return f"{path}:{lineno} {rule} {message}"


def read_tree(source: str, path: pathlib.Path) -> ast.Module:
    """Parse `source`, attributing syntax errors to `path`."""
    return ast.parse(source, filename=str(path))


def package_for(path: pathlib.Path, module_name: str) -> str:
    """The package a relative import inside `module_name` resolves against.

    PEP 328's ``__package__``: a module's parent package, and a package's own
    name when the file is its ``__init__.py``. The distinction cannot be read
    off `module_name` alone — the runner maps ``src/ccf/__init__.py`` to
    ``ccf`` and a hypothetical ``src/ccf.py`` would map there too — so the path
    is what settles it.

    Returns ``""`` for a top-level module, where a relative import has nothing
    to resolve against and is unresolvable rather than merely unusual.
    """
    if path.name == "__init__.py":
        return module_name
    return module_name.rpartition(".")[0]


def _absolute_from(node: ast.ImportFrom, package: str) -> str | None:
    """The absolute module an ``ImportFrom`` imports *from*, or None.

    ``None`` means "this statement names no module this helper can resolve":
    an absolute ``from`` with no module is impossible, and a relative one is
    unresolvable when the importing package is unknown or when the leading dots
    climb past the package root. Unresolvable is reported as nothing rather
    than as a guess — a lint that invented a name would deny an import that was
    never written.
    """
    if not node.level:
        return node.module
    if not package:
        return None
    parts = package.split(".")
    kept = len(parts) - (node.level - 1)
    if kept <= 0:
        return None
    base = ".".join(parts[:kept])
    return f"{base}.{node.module}" if node.module else base


def imported_module_names(node: ast.AST, *, package: str = "") -> list[str]:
    """Dotted module names an Import/ImportFrom node brings into scope.

    Relative imports (``from . import x``) carry no absolute module name of
    their own; they are resolved against `package` when one is supplied, and
    reported as an empty list when it is not (review finding F3).
    """
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        absolute = _absolute_from(node, package)
        return [absolute] if absolute else []
    return []


def submodule_import_names(node: ast.AST, *, package: str = "") -> list[str]:
    """Dotted names an ``ImportFrom`` reaches by naming a *submodule*.

    ``from ccf.graph import _writer`` binds ``ccf.graph._writer`` just as surely
    as ``import ccf.graph._writer`` does, but :func:`imported_module_names`
    reports only ``ccf.graph`` for it — correctly, since it cannot tell a
    submodule from an attribute without importing, which a lint must not do.

    This supplements it for the rules that deny a specific *module*. A name that
    is an attribute rather than a submodule simply never matches a deny entry,
    so over-reaching here costs nothing; under-reaching cost the single-writer
    static gate its central claim (review finding CR-02).

    Lives here rather than in one checker because every import rule needs it —
    ``cinv02-harness``, ``cinv02-graph-writer``, ``cinv02-backend-import``,
    ``cinv02-deployment-gates``, ``cinv03-algorithmic`` and
    ``d06-orchestration-split`` — and a helper imported from a sibling checker
    is how one rule's edit silently changes another's.

    Relative imports resolve against `package`, per :func:`imported_module_names`.
    """
    if not isinstance(node, ast.ImportFrom):
        return []
    absolute = _absolute_from(node, package)
    if not absolute:
        return []
    return [f"{absolute}.{alias.name}" for alias in node.names]


def reached_module_names(node: ast.AST, *, package: str = "") -> set[str]:
    """Every module name one import statement could bring into scope.

    The union of :func:`imported_module_names` and
    :func:`submodule_import_names`. A **set**, because a rule that denies a
    module wants one finding per import statement rather than one per spelling
    that statement matches: ``from ccf.graph.backends import sqlite_write``
    matches on both the package and the expanded submodule, and reporting the
    same line twice is noise, not evidence.

    **Every deny loop in this package reads this, not
    :func:`imported_module_names`** (review finding F0). A deny entry with a
    dot in it — ``google.adk``, ``ccf.llm``, ``ccf_runtime.adapters`` — is
    reachable by a spelling that names only the parent (``from google import
    adk``), and that spelling is the idiomatic one for at least one harness the
    SDK must never import. A rule that reads only the unexpanded name enforces
    its deny list against some spellings and not others, which is not an
    invariant.
    """
    return set(imported_module_names(node, package=package)) | set(
        submodule_import_names(node, package=package)
    )


def matches_module(name: str, prefixes: Iterable[str]) -> bool:
    """True when `name` equals or is a dotted descendant of any prefix.

    Dot-bounded so ``langgraphql`` never matches the ``langgraph`` deny entry.
    """
    return any(name == p or name.startswith(p + ".") for p in prefixes)
