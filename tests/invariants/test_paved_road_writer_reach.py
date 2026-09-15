"""Single-writer, held at the paved road (`D-IMPL-343`; CLAUDE.md §10).

The paved road's facade, :mod:`ccf.products.product`, is a **producer-side
composition root**: inside the declared acquisition seam it hands a
deployment's envelopes to L2's one writer through ``fabric.handle.worker``.
That makes it the only module under ``ccf.products`` — and one of very few
under ``src/`` at all — that reaches the worker. The writer lint
(``tools/lints/harness_imports.py``, ``cinv02-graph-writer``) guards
*imports* of the write modules, which this reach is not, so this test is the
control the design named: the set of ``src/`` modules that reach
``handle.worker`` is enumerated from the tree and held to a roster of
composition roots, and a new one is a defect until it is named here with a
reason.

Read off the AST, never by grep: an attribute chain ``X.handle.worker`` in
code, not a mention in prose.
"""

from __future__ import annotations

import ast
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src" / "ccf"

#: Every ``src/`` module permitted to reach the assembly worker through a
#: booted fabric's handle, and why. The boot and assembly packages own the
#: writer; the paved road's facade is the composition root the design named.
COMPOSITION_ROOTS: frozenset[str] = frozenset(
    {
        "ccf.products.product",
    }
)

#: Packages that OWN the writer and are outside this control's question.
WRITER_OWNERS: tuple[str, ...] = ("ccf.assembly", "ccf.boot", "ccf.graph")


def _module_name(path: pathlib.Path) -> str:
    relative = path.relative_to(REPO_ROOT / "src").with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _reaches_the_worker(path: pathlib.Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and node.attr == "worker"
            and isinstance(node.value, ast.Attribute)
            and node.value.attr == "handle"
        ):
            return True
    return False


def _reachers() -> set[str]:
    found: set[str] = set()
    for path in sorted(SRC.rglob("*.py")):
        name = _module_name(path)
        if name.startswith(WRITER_OWNERS):
            continue
        if _reaches_the_worker(path):
            found.add(name)
    return found


def test_the_paved_road_facade_is_the_one_products_module_that_reaches_the_worker() -> None:
    """The roster and the tree agree in both directions.

    A module reaching ``handle.worker`` that is not named here is a second
    composition root nobody reviewed; a name here that reaches nothing is a
    permission that has drifted from the code.
    """
    reachers = _reachers()
    assert reachers == COMPOSITION_ROOTS, (
        f"src/ modules reaching `handle.worker`: {sorted(reachers)};"
        f" permitted composition roots: {sorted(COMPOSITION_ROOTS)}"
    )


def test_the_predicate_sees_the_facade_and_not_a_mention(tmp_path: pathlib.Path) -> None:
    """Positive and negative control for the AST predicate itself."""
    reaching = tmp_path / "reaching.py"
    reaching.write_text("def f(fabric):\n    fabric.handle.worker.ingest(None)\n", encoding="utf-8")
    assert _reaches_the_worker(reaching)
    prose = tmp_path / "prose.py"
    prose.write_text('"""nothing here reaches fabric.handle.worker"""\nX = "handle.worker"\n', encoding="utf-8")
    assert not _reaches_the_worker(prose)
    assert _reaches_the_worker(SRC / "products" / "product.py")
