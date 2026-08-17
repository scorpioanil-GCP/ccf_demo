"""Every module in ``ccf`` imports when it is the *first* import into the tree.

An adopter's first line of CCF code is an import, and which module they reach
for is theirs to choose. If a module can only be imported *second* — because
some other module has to complete a cycle's far side first — then first contact
fails for that adopter, and the traceback names a circular import rather than
anything they did. CLAUDE.md §1 success condition 4 makes first contact a
deliverable property, not a courtesy.

This is not hypothetical. ``DEF-17-02`` recorded exactly that shape:

    ``ccf.products.payload`` → ``ccf.skills.catalog`` → ``ccf.agents`` →
    ``ccf.replay.record`` → ``ccf.products.request`` → ``ccf.products.payload``

``import ccf.products.request`` succeeded, because it completed the far side of
the cycle before re-entering; ``import ccf.products.payload`` raised
``ImportError``. The whole suite was green throughout, because something always
imported ``request`` — or a module reaching it — before ``payload``. **A warm
interpreter cannot see this defect at all**, which is why every probe below
spends a fresh subprocess.

Why a walk and not a list
-------------------------
The obvious test names the five modules the defect was reported against. That
test rots: it pins the cycle that was found rather than the property that
matters, and the next cycle lands somewhere else and passes. So the population
is **discovered**, and the discovery is cross-checked against an independent
method — the walk must agree file-for-file with a filesystem glob, so a walk
that silently truncates fails loudly instead of reporting a green subset.

Why a structural cycle detector would be the wrong instrument
-------------------------------------------------------------
Import cycles are not per se defects in this tree, and D-IMPL-56 rules a
pattern that deliberately keeps some: a bottom-of-module import plus
``model_rebuild()`` where a contract's *field type* lives across the seam, so
``TYPE_CHECKING`` cannot serve it. :mod:`ccf.skills.catalog` and
:mod:`ccf.replay.record` both apply it, with the ruling cited at the import
site. A detector would refuse those rulings. The property actually owed to an
adopter is narrower and empirical: *whatever the graph looks like, every entry
point works*. That is what runs here.

Why the walk stops at ``src``
-----------------------------
``ccf_runtime`` has the same first-contact property and was measured clean when
this module was written (69 of 69 modules, ``phase-17`` @ ``7d76205``), but it
is not walked unconditionally, and the reason is structural rather than
incidental. CLAUDE.md §7.3 guarantees **zero harness imports in core**, which is
exactly what makes an unconditional probe over ``src/ccf`` sound: nothing there
can fail for want of an optional extra. The runtime's adapter and orchestration
modules import their harness at module scope — correctly, since they *are* the
adapters — so the same probe over ``runtime`` would turn the optional ``adk`` and
``langgraph`` extras into a hard dependency of an always-on invariant test. That
coverage belongs behind the ``harness`` marker, with whoever owns it.
"""

from __future__ import annotations

import os
import pkgutil
import subprocess
import sys
from collections.abc import Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Final

#: The repository root, reached from this file rather than from the working
#: directory: pytest may be invoked from anywhere and these probes address the
#: tree by path.
REPO_ROOT: Final = Path(__file__).resolve().parents[2]

#: The library import root and the package it carries.
SRC_ROOT: Final = REPO_ROOT / "src"
PACKAGE: Final = "ccf"

#: What every probe subprocess puts on ``PYTHONPATH``. ``runtime`` joins ``src``
#: so that a library module reaching a runtime one resolves it exactly as a
#: deployment would — the runtime is on the path, it is simply not the
#: population being walked.
PROBE_PATH: Final[tuple[Path, ...]] = (SRC_ROOT, REPO_ROOT / "runtime")


def _walk(root: Path, package: str) -> Iterator[tuple[str, bool]]:
    """Yield ``(dotted name, is_package)`` for everything under ``root/package``.

    ``onerror`` re-raises rather than swallowing. :func:`pkgutil.walk_packages`
    imports each *package* to read its ``__path__``, and its default on failure
    is to discard the error and carry on with a truncated result. A truncated
    walk reporting zero failures is the precise shape of verification defect
    this module exists not to have, so the failure is made loud;
    :func:`test_a_broken_package_stops_the_walk_instead_of_truncating_it` proves
    it is.
    """

    def onerror(name: str) -> None:
        raise  # noqa: PLE0704 - re-raise the live ImportError, never swallow it

    for info in pkgutil.walk_packages(
        [str(root / package)], prefix=f"{package}.", onerror=onerror
    ):
        yield info.name, info.ispkg


def walk_modules(root: Path, package: str) -> tuple[str, ...]:
    """Every importable name under ``root/package``, the root package included.

    Private (``_``-prefixed) names are **not** filtered. A private module that
    cannot be imported is still a broken module, and a filter here would be one
    more place for the population to quietly shrink.
    """
    return (package, *sorted(name for name, _ in _walk(root, package)))


def module_files(root: Path, package: str) -> set[Path]:
    """The same population, answered by the filesystem instead of by import."""
    return {
        root / package / (name[len(package) + 1 :].replace(".", "/") + ".py")
        for name, is_package in _walk(root, package)
        if not is_package
    }


def cold_import_failures(
    names: Sequence[str], *, path_entries: Sequence[Path]
) -> dict[str, str]:
    """Import each name in its own cold interpreter; return every failure.

    One subprocess per name, because "first import into the tree" is a property
    of a *fresh* ``sys.modules`` and nothing short of a new interpreter has one.
    The probes are independent, so they run concurrently — the wait is on
    process startup, not on this thread.

    ``PYTHONDONTWRITEBYTECODE`` is set deliberately: ``DEF-17-03`` recorded a
    stale ``__pycache__`` producing a convincing false failure, and a probe that
    leaves no bytecode behind cannot contribute to that.

    Returns:
        A mapping of module name to the last line of its traceback, empty when
        every name imported. Every failure is collected rather than the first,
        so one run reports the whole population.
    """
    env = {
        "PYTHONPATH": os.pathsep.join(str(p) for p in path_entries),
        "PATH": os.environ.get("PATH", ""),
        "PYTHONDONTWRITEBYTECODE": "1",
    }

    def probe(name: str) -> tuple[str, str | None]:
        completed = subprocess.run(
            [sys.executable, "-c", f"import {name}"],
            capture_output=True,
            text=True,
            env=env,
        )
        if completed.returncode == 0:
            return name, None
        stderr = completed.stderr.strip().splitlines()
        return name, stderr[-1] if stderr else "(no stderr)"

    with ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 1)) as pool:
        results = list(pool.map(probe, names))
    return {name: error for name, error in results if error is not None}


def plant_package(directory: Path, package: str, modules: dict[str, str]) -> None:
    """Write a throwaway package used to prove the probe and the walk fire.

    Test scaffolding only. No control touches the real tree — each walks and
    probes a ``tmp_path`` root, through the *same* functions the real assertion
    uses.
    """
    root = directory / package
    root.mkdir(parents=True, exist_ok=True)
    (root / "__init__.py").write_text("")
    for name, source in modules.items():
        target = root / f"{name}.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source)


# ---------------------------------------------------------------------------
# The assertion
# ---------------------------------------------------------------------------


def test_every_ccf_module_imports_as_the_first_import_into_the_tree() -> None:
    """No module in ``ccf`` requires another to be imported before it.

    The regression pin for ``DEF-17-02`` and for every cycle shaped like it. A
    failure names each module that only imports second; the fix is to remove the
    import edge that closes the cycle, not to reorder around it — reordering
    leaves the property broken for whichever entry point loses.
    """
    names = walk_modules(SRC_ROOT, PACKAGE)
    failures = cold_import_failures(names, path_entries=PROBE_PATH)
    assert failures == {}, (
        f"{len(failures)} of {len(names)} modules under {PACKAGE!r} fail when they"
        " are the first import into the tree:\n"
        + "\n".join(f"  {name}: {error}" for name, error in sorted(failures.items()))
    )


# ---------------------------------------------------------------------------
# Guards on the instrument
# ---------------------------------------------------------------------------


def test_the_walk_agrees_with_the_filesystem() -> None:
    """The discovered population is the whole population, cross-checked.

    :func:`pkgutil.walk_packages` and a filesystem glob are independent methods
    of answering "which modules ship". If they disagree, the walk is reporting a
    subset and the green result above is worth less than it looks. Compared as
    *sets of paths* rather than as counts, so a walk that lost one module and
    invented another cannot net out to agreement.
    """
    walked = module_files(SRC_ROOT, PACKAGE)
    on_disk = {p for p in (SRC_ROOT / PACKAGE).rglob("*.py") if p.name != "__init__.py"}
    assert walked == on_disk, (
        "walk and filesystem disagree — "
        f"walk-only: {sorted(str(p) for p in walked - on_disk)}, "
        f"disk-only: {sorted(str(p) for p in on_disk - walked)}"
    )
    assert on_disk, f"no modules found under {SRC_ROOT / PACKAGE} — the walk is vacuous"


def test_the_five_modules_the_defect_was_reported_against_are_in_the_walk() -> None:
    """The named victims of ``DEF-17-02`` are covered by the discovered set.

    Not a substitute for the walk — an anchor for it. If a future refactor
    renames or relocates these, this fails and says so, rather than the walk
    silently covering a tree that no longer contains the modules the entry was
    written about.
    """
    walked = set(walk_modules(SRC_ROOT, PACKAGE))
    named = {
        "ccf.products.payload",
        "ccf.products.request",
        "ccf.products.refusal",
        "ccf.skills.catalog",
        "ccf.replay.record",
    }
    assert named <= walked, f"named in DEF-17-02 but not walked: {sorted(named - walked)}"


def test_the_probe_reports_a_planted_cycle(tmp_path: Path) -> None:
    """Sabotage control: the real probe, on a package carrying the real defect.

    ``cyc.a`` and ``cyc.b`` import a name from each other at module scope —
    ``DEF-17-02``'s shape, minimised. Both must fail, and both messages must
    name a partially initialized module, so the control proves the probe detects
    *this* failure mode rather than merely detecting a non-zero exit.
    """
    plant_package(
        tmp_path,
        "cyc",
        {"a": "from cyc.b import B\n\nA = 1\n", "b": "from cyc.a import A\n\nB = 2\n"},
    )
    names = walk_modules(tmp_path, "cyc")
    assert {"cyc.a", "cyc.b"} <= set(names)

    failures = cold_import_failures(names, path_entries=[tmp_path])
    assert set(failures) == {
        "cyc.a",
        "cyc.b",
    }, f"the planted cycle was not detected as expected: {failures}"
    for name, error in failures.items():
        assert "partially initialized" in error, f"{name}: unexpected error {error!r}"


def test_the_probe_passes_the_same_arrangement_without_the_cycle(tmp_path: Path) -> None:
    """The control's twin: identical scaffolding, no cycle, no failure.

    Isolates the cycle as the cause. Without this, a permanently-red probe would
    make the sabotage control above pass for the wrong reason.
    """
    plant_package(
        tmp_path, "cyc", {"a": "A = 1\n", "b": "from cyc.a import A\n\nB = A + 1\n"}
    )
    names = walk_modules(tmp_path, "cyc")
    assert cold_import_failures(names, path_entries=[tmp_path]) == {}


def test_a_broken_package_stops_the_walk_instead_of_truncating_it(
    tmp_path: Path,
) -> None:
    """Sabotage control on the walk itself, not on the probe.

    :func:`pkgutil.walk_packages` swallows a package that fails to import unless
    ``onerror`` says otherwise, and a silently shortened population would make
    every assertion above pass over a subset. A sub-package whose ``__init__``
    raises must therefore propagate out of :func:`walk_modules`, not vanish
    from its result.
    """
    plant_package(tmp_path, "cyc", {"a": "A = 1\n"})
    sub = tmp_path / "cyc" / "sub"
    sub.mkdir()
    (sub / "__init__.py").write_text("raise ImportError('planted')\n")
    (sub / "leaf.py").write_text("LEAF = 1\n")

    sys.path.insert(0, str(tmp_path))
    try:
        try:
            walked = walk_modules(tmp_path, "cyc")
        except ImportError as exc:
            assert "planted" in str(exc)
            return
        raise AssertionError(
            "walk_modules swallowed a broken package and returned a truncated"
            f" population: {walked}"
        )
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("cyc.sub", None)
        sys.modules.pop("cyc", None)
