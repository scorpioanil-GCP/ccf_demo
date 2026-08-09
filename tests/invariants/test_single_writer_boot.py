"""CINV-04, single-writer leg: the runtime backstop of the D-IMPL-41 stack.

DESIGN.md §2A.5.3 builds single-writer enforcement in four layers. Three of them
are checkable without running anything: the Protocol split is a type property,
the import restriction is a lint, and strict mypy is a build step. The fourth —
the boot token — is behavioral, and this module is where it is asserted.

What these tests are *for*: a violation of single-writer that surfaced only when
the second writer happened to write would be a violation that reached
production, because the interleaved state it produced would be indistinguishable
from legitimate history until someone tried to replay a decision and could not.
So every test here asserts that the fabric refuses **at boot**.

**Honest residual claim (DESIGN.md §9, D-IMPL-41):** Python cannot make
determined-insider evasion impossible. These tests assert exactly the claim the
design makes — *no unforced path exists, and every forced path fails CI or
fails at boot* — and nothing stronger. The final test in this module documents
that boundary rather than pretending it away.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from ccf.graph._writer import (
    BootToken,
    SingleWriterViolation,
    SqliteGraphWriter,
)
from ccf.graph.backends.sqlite import SqliteGraphStore
from ccf.graph.protocols import GraphWriter

if TYPE_CHECKING:
    from ccf.boot import FabricHandle


def test_booting_the_same_graph_twice_raises(
    fabric_boot: Callable[..., "FabricHandle"], tmp_path: Path
) -> None:
    """Two writers over one graph is the violation the whole stack exists for."""
    database_path = tmp_path / "shared.sqlite3"
    fabric_boot(database_path=database_path)

    with pytest.raises(SingleWriterViolation, match="already exists"):
        fabric_boot(database_path=database_path)


def test_booting_distinct_graphs_is_fine(
    fabric_boot: Callable[..., "FabricHandle"], tmp_path: Path
) -> None:
    """The invariant is one writer *per graph*, not one writer per process.

    Worth asserting explicitly: a check that forbade a second fabric outright
    would pass the test above for the wrong reason and would make multi-tenant
    and multi-fabric hosting impossible.
    """
    first = fabric_boot(database_path=tmp_path / "a.sqlite3")
    second = fabric_boot(database_path=tmp_path / "b.sqlite3")

    assert first is not second


def test_a_token_authorizes_exactly_one_writer(tmp_path: Path) -> None:
    """Tokens are single-use, so "reuse the token" is not a second-writer path."""
    from ccf.graph._writer import mint_boot_token

    store = SqliteGraphStore(database_path=tmp_path / "once.sqlite3")
    token = mint_boot_token(graph_identity=store.graph_identity)
    writer = SqliteGraphWriter(store=store, token=token)

    try:
        with pytest.raises(SingleWriterViolation, match="already consumed"):
            SqliteGraphWriter(store=store, token=token)
    finally:
        writer.close()
        store.close()


def test_a_writer_cannot_be_constructed_without_a_token(tmp_path: Path) -> None:
    """Omitting the token is a TypeError; forging one is a violation."""
    store = SqliteGraphStore(database_path=tmp_path / "tokenless.sqlite3")
    try:
        with pytest.raises(TypeError):
            SqliteGraphWriter(store=store)  # type: ignore[call-arg]

        with pytest.raises(SingleWriterViolation, match="requires a BootToken"):
            SqliteGraphWriter(store=store, token=object())  # type: ignore[arg-type]
    finally:
        store.close()


def test_a_token_cannot_be_minted_by_hand(tmp_path: Path) -> None:
    """"Just construct a token" is closed off, or the backstop is decorative."""
    with pytest.raises(SingleWriterViolation, match="composition root"):
        BootToken(graph_identity=str(tmp_path), mint_key=object())


def test_the_fabric_handle_exposes_no_write_capability(
    fabric: "FabricHandle",
) -> None:
    """Nothing reachable from the handle is a ``GraphWriter``.

    Layer 2 of the stack is only as good as what the composition root hands
    back: a handle carrying the writer "for convenience" would undo the
    injection discipline in one attribute.
    """
    assert not hasattr(fabric, "writer")
    public = {
        name: getattr(fabric, name)
        for name in dir(fabric)
        if not name.startswith("_")
    }
    assert not any(isinstance(value, GraphWriter) for value in public.values())
    assert not any(isinstance(value, SqliteGraphWriter) for value in public.values())


def test_a_retired_writer_refuses_further_writes(
    fabric_boot: Callable[..., "FabricHandle"], tmp_path: Path
) -> None:
    """Closing releases the graph *and* invalidates the writer.

    Both halves matter. Release without invalidation would let a caller hold a
    live writer while a second fabric booted over the same graph — a second
    writer by another name.
    """
    database_path = tmp_path / "retired.sqlite3"
    handle = fabric_boot(database_path=database_path)
    handle.close()

    reopened = fabric_boot(database_path=database_path)

    assert reopened is not handle


def test_only_permitted_modules_name_the_neutral_writer_module() -> None:
    """The import restriction, asserted here as well as in CI.

    This is layer 3 of the stack (CINV-02). It is checked by
    ``python -m tools.lints --all``; the assertion is repeated in the test suite
    so a regression fails the run a developer is actually watching, not only
    the pipeline.

    **The permitted set is read from the rule, never restated here.** It used to
    be the literal ``["ccf/boot.py"]``, which made this test a second definition
    of the invariant — and a second definition drifts. It drifted the moment
    plan 15.4-01 widened ``cinv02-graph-writer``'s permitted importers of the
    *neutral base* to include ``ccf.graph.registry`` (the registry types the
    write seam so ``BackendRegistration.make_writer`` can be typed under
    ``mypy --strict``; it mints no token and calls no factory), and it would
    drift again at plan 15.4-03, where every ``backends/<name>_write`` module
    legitimately names the base it subclasses. Importing
    :data:`~tools.lints.harness_imports.NEUTRAL_WRITER_OK_MODULES` and
    :func:`~tools.lints.harness_imports.is_write_module` is the same
    name-the-class-not-the-instance correction D-GATE-15.3 records the project
    learning three times in one phase: the rule and its test cannot disagree
    about what is permitted, because there is one statement of it.

    Containment is the property; the equality form was a tripwire. So the
    non-vacuity half is asserted separately — the composition root must still
    be in the offender list, or a regex that matched nothing would pass this
    silently.
    """
    import re

    from tools.lints import matches_module
    from tools.lints.harness_imports import (
        NEUTRAL_WRITER_OK_MODULES,
        is_write_module,
    )

    # Only real import statements count — the module is *named* in several
    # docstrings, and a check that flagged prose would push people to stop
    # explaining the invariant.
    importers = re.compile(
        r"^\s*(?:from\s+ccf\.graph\._writer\s+import|import\s+ccf\.graph\._writer)",
        re.MULTILINE,
    )
    source_root = Path(__file__).resolve().parents[2] / "src"
    offenders = sorted(
        path.relative_to(source_root).as_posix()
        for path in source_root.rglob("*.py")
        if importers.search(path.read_text(encoding="utf-8"))
    )

    def permitted(relative_path: str) -> bool:
        module = relative_path.removesuffix(".py").replace("/", ".")
        module = module.removesuffix(".__init__")
        return matches_module(module, NEUTRAL_WRITER_OK_MODULES) or is_write_module(
            module
        )

    assert [path for path in offenders if not permitted(path)] == [], offenders
    assert "ccf/boot.py" in offenders, offenders
