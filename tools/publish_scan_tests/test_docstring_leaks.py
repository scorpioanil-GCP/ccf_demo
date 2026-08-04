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
import io
import pathlib
import tokenize

import pytest

from tools.publish_scan import RULE_SHINGLE, SKIP_DIRS, scan_text, whitepaper_shingles

#: The repo root, resolved from this file rather than from the process CWD:
#: a CWD-relative walk yields zero files off-root and turns the gate below
#: into a test that passes over nothing (WR-04).
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The two trees mkdocstrings renders from.
DOCUMENTED_TREES: tuple[str, ...] = ("src", "runtime")


def _iter_python_files() -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for tree in DOCUMENTED_TREES:
        root = REPO_ROOT / tree
        files.extend(
            path
            for path in sorted(root.rglob("*.py"))
            if not any(part in SKIP_DIRS for part in path.parts)
        )
    return files


def _attribute_docs(body: list[ast.stmt], prefix: str) -> list[tuple[str, str]]:
    """PEP 258 attribute docstrings in one suite.

    A bare string-literal expression immediately following an assignment is
    documentation as far as griffe — and therefore mkdocstrings, and therefore
    the published page — is concerned. It is not reachable through
    `ast.get_docstring`, so it was invisible to this gate (WR-05).
    """
    found: list[tuple[str, str]] = []
    for previous, statement in zip(body, body[1:]):
        if not isinstance(previous, (ast.Assign, ast.AnnAssign)):
            continue
        if not isinstance(statement, ast.Expr):
            continue
        value = statement.value
        if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
            continue
        if isinstance(previous, ast.AnnAssign):
            targets = [previous.target]
        else:
            targets = list(previous.targets)
        names = [t.id for t in targets if isinstance(t, ast.Name)] or ["<attr>"]
        for name in names:
            qualname = f"{prefix}.{name}" if prefix else name
            found.append((qualname, value.value))
    return found


def _hash_colon_docs(path: pathlib.Path) -> list[tuple[str, str]]:
    """Contiguous runs of `#:` comments, which griffe publishes as attribute
    documentation.

    This codebase uses the style heavily — `tools/publish_scan.py` is written
    in it throughout — so proprietary prose in a `#:` run reaches a published
    page exactly as a docstring would. Plain `#` comments are NOT collected:
    griffe does not publish them, and treating an internal note as a
    publication channel would make the gate fire on text that never ships.
    """
    found: list[tuple[str, str]] = []
    run: list[str] = []
    start = 0
    for token in tokenize.generate_tokens(
        io.StringIO(path.read_text(encoding="utf-8")).readline
    ):
        if token.type == tokenize.COMMENT and token.string.startswith("#:"):
            if not run:
                start = token.start[0]
            run.append(token.string[2:].strip())
            continue
        if token.type in (tokenize.NL, tokenize.COMMENT):
            continue
        if run:
            found.append((f"<#: line {start}>", " ".join(run)))
            run = []
    if run:
        found.append((f"<#: line {start}>", " ".join(run)))
    return found


def _iter_docstrings(path: pathlib.Path) -> list[tuple[str, str]]:
    """``(qualified name, doc text)`` for every documented node in `path`.

    Covers all four channels mkdocstrings republishes: the module docstring,
    class/function docstrings, PEP 258 attribute docstrings, and `#:` comment
    documentation.
    """
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[str, str]] = []

    def walk(node: ast.AST, prefix: str) -> None:
        body = getattr(node, "body", None)
        if isinstance(body, list):
            found.extend(_attribute_docs(body, prefix))
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
    found.extend(_hash_colon_docs(path))
    return found


#: A verbatim ten-plus-word run of whitepaper body text, reused as the fixture
#: quote by the collector tests below.
QUOTE = "only the Assembly worker holds a write handle to the graph"


# --------------------------------------------------------------------------
# Preconditions — a vacuous pass is the failure this module exists to prevent.
# WR-04: the walk was CWD-relative, so off-root it scanned zero files and the
# gate below passed over nothing. `tools/docs_tests/test_diagram_coverage.py`
# is the model.
# --------------------------------------------------------------------------


def test_documented_trees_are_populated() -> None:
    for tree in DOCUMENTED_TREES:
        root = REPO_ROOT / tree
        assert root.is_dir(), f"missing documented tree: {root}"
    assert _iter_python_files(), "no python sources scanned"


def test_the_walk_does_not_depend_on_the_process_cwd(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    assert _iter_python_files(), "the walk resolved against the CWD, not the repo"


# --------------------------------------------------------------------------
# WR-05: griffe publishes attribute docstrings and `#:` comments too, so both
# are publication channels and D-02 applies to them.
# --------------------------------------------------------------------------


def test_attribute_docstrings_are_collected(tmp_path: pathlib.Path) -> None:
    module = tmp_path / "m.py"
    module.write_text(f'X = 1\n"""{QUOTE}"""\n', encoding="utf-8")
    assert QUOTE in "\n".join(doc for _, doc in _iter_docstrings(module))


def test_annotated_attribute_docstrings_are_collected(
    tmp_path: pathlib.Path,
) -> None:
    module = tmp_path / "m.py"
    module.write_text(f'X: int = 1\n"""{QUOTE}"""\n', encoding="utf-8")
    assert QUOTE in "\n".join(doc for _, doc in _iter_docstrings(module))


def test_hash_colon_comment_docs_are_collected(tmp_path: pathlib.Path) -> None:
    module = tmp_path / "m.py"
    module.write_text(f"#: {QUOTE}\nX = 1\n", encoding="utf-8")
    assert QUOTE in "\n".join(doc for _, doc in _iter_docstrings(module))


def test_a_leak_in_either_channel_is_flagged(tmp_path: pathlib.Path) -> None:
    shingles = whitepaper_shingles()
    for body in (f'X = 1\n"""{QUOTE}"""\n', f"#: {QUOTE}\nX = 1\n"):
        module = tmp_path / "m.py"
        module.write_text(body, encoding="utf-8")
        hits = [
            f
            for _, doc in _iter_docstrings(module)
            for f in scan_text(doc, module, shingles)
            if RULE_SHINGLE in f
        ]
        assert hits, f"unflagged leak in: {body!r}"


def test_an_ordinary_comment_is_not_collected(tmp_path: pathlib.Path) -> None:
    # Only `#:` is a griffe doc channel. A plain `#` comment is not published,
    # and treating it as documentation would make every internal note a leak.
    module = tmp_path / "m.py"
    module.write_text(f"# {QUOTE}\nX = 1\n", encoding="utf-8")
    assert QUOTE not in "\n".join(doc for _, doc in _iter_docstrings(module))


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
