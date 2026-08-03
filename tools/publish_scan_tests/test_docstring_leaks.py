"""D-20 — no docstring in the published surface quotes the whitepaper.

mkdocstrings republishes docstring text verbatim, so a docstring is a
publication channel and D-02 applies to it exactly as it applies to a
hand-written page. This is the standing regression gate: every module, class
and function docstring under ``src/`` and ``runtime/`` is fed to the same
shingle check the built tree gets, and the flagged set must be empty.

Rewriting a docstring to pass this test must never mean deleting its
whitepaper section citation — CLAUDE.md §11 requires the citation, and trading
a leak for a fidelity defect is not a fix.
"""

from __future__ import annotations

import ast
import pathlib

from tools.publish_scan import RULE_SHINGLE, SKIP_DIRS, scan_text, whitepaper_shingles

#: The two trees mkdocstrings renders from.
DOCUMENTED_TREES: tuple[str, ...] = ("src", "runtime")


def _iter_python_files() -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for tree in DOCUMENTED_TREES:
        root = pathlib.Path(tree)
        files.extend(
            path
            for path in sorted(root.rglob("*.py"))
            if not any(part in SKIP_DIRS for part in path.parts)
        )
    return files


def _iter_docstrings(path: pathlib.Path) -> list[tuple[str, str]]:
    """``(qualified name, docstring)`` for every documented node in `path`."""
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[str, str]] = []

    def walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(
                child,
                (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                name = f"{prefix}.{child.name}" if prefix else child.name
                doc = ast.get_docstring(child)
                if doc:
                    found.append((name, doc))
                walk(child, name)

    module_doc = ast.get_docstring(module)
    if module_doc:
        found.append(("<module>", module_doc))
    walk(module, "")
    return found


def test_no_docstring_reproduces_whitepaper_body_text() -> None:
    shingles = whitepaper_shingles()
    leaks: list[str] = []
    for path in _iter_python_files():
        for qualname, doc in _iter_docstrings(path):
            hits = [
                f
                for f in scan_text(doc, path, shingles)
                if RULE_SHINGLE in f
            ]
            if hits:
                leaks.append(f"{path}::{qualname} — {len(hits)} shingle hit(s)")
    assert not leaks, "docstrings quoting the whitepaper:\n" + "\n".join(leaks)
