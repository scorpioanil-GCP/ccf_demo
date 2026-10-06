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

from ccf.graph._writer import BootToken, SingleWriterViolation
from ccf.graph.backends.sqlite import SqliteGraphStore
from ccf.graph.backends.sqlite_write import SqliteGraphWriter
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
    token = mint_boot_token(store=store)
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


def _neutral_base_importers() -> list[str]:
    """Repo-relative ``src`` paths whose source imports the neutral write base.

    Only real import statements count — the module is *named* in several
    docstrings, and a check that flagged prose would push people to stop
    explaining the invariant.

    **Three spellings, because two of them were a blind spot** (review finding
    CR-02). ``from ccf.graph import _writer`` binds the neutral base as surely
    as the two forms this pattern originally matched, and it mirrored the same
    gap in ``cinv02-graph-writer`` itself — so the test that exists to repeat
    the lint's assertion could not have caught what the lint was missing. The
    third alternative is deliberately loose about what sits between ``import``
    and ``_writer``, because ``from ccf.graph import reader, _writer`` is the
    same import wearing a comma.
    """
    import re

    importers = re.compile(
        r"^\s*(?:"
        r"from\s+ccf\.graph\._writer\s+import"
        r"|import\s+ccf\.graph\._writer"
        r"|from\s+ccf\.graph\s+import\s+[^\n]*\b_writer\b"
        r")",
        re.MULTILINE,
    )
    source_root = Path(__file__).resolve().parents[2] / "src"
    return sorted(
        path.relative_to(source_root).as_posix()
        for path in source_root.rglob("*.py")
        if importers.search(path.read_text(encoding="utf-8"))
    )


def test_only_permitted_modules_name_the_neutral_write_base() -> None:
    """The import restriction, asserted here as well as in CI.

    This is layer 3 of the stack (CINV-02). It is checked by
    ``python -m tools.lints --all``; the assertion is repeated in the test suite
    so a regression fails the run a developer is actually watching, not only
    the pipeline.

    **Stated against the lint's own permitted set, not a literal list (D-01).**
    It used to be the literal ``["ccf/boot.py"]``, which made this test a second
    definition of the invariant — and a second definition drifts. It drifted the
    moment plan 15.4-01 widened ``cinv02-graph-writer``'s permitted importers of
    the *neutral base* to include ``ccf.graph.registry`` (the registry types the
    write seam so ``BackendRegistration.make_writer`` can be typed under
    ``mypy --strict``; it mints no token and calls no factory), and it drifted
    again at plan 15.4-03, where every ``backends/<name>_write`` module
    legitimately names the base it subclasses. That is three classes of
    legitimate consumer over a set that grows per adapter — the per-adapter edit
    D-IMPL-93 exists to remove.

    So the permitted set is imported from the checker:
    :data:`~tools.lints.harness_imports.NEUTRAL_WRITER_OK_MODULES` and
    :func:`~tools.lints.harness_imports.is_write_module`. Whatever the lint
    permits is what this test permits, and the two cannot drift.

    **The membership test mirrors the lint's, dot-bounded.** The rule asks
    ``matches_module(module, permitted) or is_write_module(module)``, so a
    legitimate descendant such as ``ccf.assembly.worker`` is permitted. Plain
    set membership here would be *stricter than the rule it claims to mirror*,
    which is the same disagreement in the other direction.

    Containment is the property; the equality form was a tripwire. So the
    non-vacuity half is asserted separately, below — a regex that matched
    nothing would pass this one silently.
    """
    from tools.lints import matches_module
    from tools.lints.harness_imports import (
        NEUTRAL_WRITER_OK_MODULES,
        is_write_module,
    )

    def permitted(relative_path: str) -> bool:
        module = relative_path.removesuffix(".py").replace("/", ".")
        module = module.removesuffix(".__init__")
        return matches_module(module, NEUTRAL_WRITER_OK_MODULES) or is_write_module(
            module
        )

    offenders = [
        relative for relative in _neutral_base_importers() if not permitted(relative)
    ]

    assert offenders == [], offenders


def test_the_composition_root_is_still_among_the_importers() -> None:
    """Non-vacuity: a scan that found nothing would pass the test above.

    ``ccf/boot.py`` constructs the one writer, so it must name the write
    surface. If it ever stops appearing here, either the composition root
    stopped being the composition root or the scan stopped scanning — and both
    make the assertion above green for the wrong reason.
    """
    assert "ccf/boot.py" in _neutral_base_importers()
