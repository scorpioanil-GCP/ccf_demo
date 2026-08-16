"""`D-29`'s no-exception boundary: no module under ``src/`` imports ``runtime/``.

Amendment 1 §B of ``docs/superpowers/specs/2026-08-15-ccf-client-design.md``
rests on a measurement — *"the* ``src ↛ runtime`` *boundary stays intact and
CI-enforceable; no exception is documented, because none is needed"*. A ruling
resting on a property nobody re-measures is a ruling resting on a fact about
one afternoon. This module is what turns it into a standing assertion.

**It is not a duplicate of an existing lint.** Measured before writing:
``tools/lints`` ships six rule families — no-hardcoding, harness-imports,
algorithmic, orchestration-imports, backend-imports and substrate-names — and
none of them says anything about ``ccf_runtime``. The nearest existing check,
in ``tests/skills/test_dispatch.py``, asserts the property for **one** module
rather than for the tree. So the boundary the ruling rests on was, until this
file, asserted nowhere.

Why the walk takes its root as a parameter
------------------------------------------
:func:`find_runtime_imports` is a function **of a source root**, and that is
the whole reason the controls below can fire. A control specified as *"copy a
module into* ``tmp_path`` *and break it"* against an assertion pinned to the
real ``src/`` is a control that cannot fire, because the copy is never what the
assertion reads — the check would pass, the control would pass, and neither
would have measured anything. The shipped assertion calls this function with
the real ``src/``; each control calls **the same function** with a ``tmp_path``
tree. There is one walk, and it is the one under test.

Why the walk is an AST walk, over three shapes
----------------------------------------------
A deferred import is still an import. A regex over the head of a file would
miss an import inside a function body and an import inside an
``if TYPE_CHECKING:`` block, and this project has already been fooled that way
once — the regex ancestors of ``tests/examples/test_spine_separation.py`` are
the recorded case. So the walk visits every node of every module, and there is
a control for each of the three shapes rather than one control licensing the
other two.

The vacuity guard
-----------------
A walk that finds no modules passes, having measured nothing. That is the exact
"guard that never fired" defect the phase before this one shipped, so the
scanned-module count is asserted to be non-zero and is reported by
:func:`scan_source_tree` rather than discarded.

Known limitation, stated rather than left to be discovered
----------------------------------------------------------
An AST walk sees ``import`` statements. It does not see a dynamic import
assembled from a string — ``importlib.import_module`` on a computed name would
cross the boundary invisibly to this check. Closing that would need a different
technique and would trade a precise check for a fuzzy one; the honest position
is that this file asserts the three shapes a real violation actually takes, and
says so.

Who reads this number and what fails when it moves: ``make ci-core`` reads it
on every run. The day someone adds a ``runtime`` import to ``src/``, `D-29`'s
*"no documented exception, because none is needed"* becomes false, and this
module says so in the same commit rather than in a later audit.
"""

from __future__ import annotations

import ast
import dataclasses
from pathlib import Path

import pytest

#: The package whose absence from ``src/`` is the property under test. Spelled
#: once: two spellings are two things to keep in step, and the controls below
#: read this same name so a rename cannot leave them testing the old one.
RUNTIME_PACKAGE = "ccf_runtime"

#: The real source root — the tree `D-29` makes its claim about. Resolved from
#: this file rather than from the working directory, so the assertion measures
#: the same tree whichever directory pytest was launched from.
SRC_ROOT = Path(__file__).resolve().parents[2] / "src"

#: Directories that are not source. ``__pycache__`` in particular holds no
#: ``.py`` files but would cost a walk on every run.
SKIP_DIRS: frozenset[str] = frozenset({"__pycache__", ".mypy_cache"})


@dataclasses.dataclass(frozen=True)
class Finding:
    """One import statement that crosses the boundary."""

    path: str
    line: int
    imported: str
    shape: str

    def __str__(self) -> str:
        return f"{self.path} line {self.line}: {self.shape} of {self.imported!r}"


@dataclasses.dataclass(frozen=True)
class Scan:
    """What one walk found, **and** how much it looked at.

    The count travels with the findings deliberately. An empty finding list is
    the answer a healthy tree gives and also the answer a walk over nothing
    gives, and those two are indistinguishable unless the walk reports how many
    modules it read.
    """

    findings: tuple[Finding, ...]
    modules_scanned: int


def _crosses(name: str | None) -> bool:
    """Whether a dotted module name is, or lives under, the runtime package.

    Prefix-matched on a **dotted boundary**, never on the bare string: a
    hypothetical ``ccf_runtimex`` shares a string prefix with the package and
    is not in it, and a check that conflated the two would refuse an innocent
    module while claiming to enforce this one.
    """
    if name is None:
        return False
    return name == RUNTIME_PACKAGE or name.startswith(f"{RUNTIME_PACKAGE}.")


def scan_source_tree(root: Path) -> Scan:
    """Walk every module under ``root``; report the crossings and the count.

    Visits **every node** of every module, so an import inside a function body,
    inside a class body, inside an ``if TYPE_CHECKING:`` block or inside a
    ``try`` is found exactly as a top-level one is. A relative import
    (``from . import x``) can only ever name a sibling inside the walked
    package and is therefore not a crossing; it is skipped by testing
    ``node.level``, not by inspecting the text.

    Args:
        root: The source tree to read. A **parameter**, so a control can hand
            this function a deliberately broken tree and observe the same code
            path the shipped assertion runs.

    Returns:
        The findings, in path-then-line order, and how many modules were read.
    """
    findings: list[Finding] = []
    scanned = 0
    for path in sorted(root.rglob("*.py")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        scanned += 1
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        relative = path.relative_to(root).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if _crosses(alias.name):
                        findings.append(
                            Finding(
                                path=relative,
                                line=node.lineno,
                                imported=alias.name,
                                shape="import",
                            )
                        )
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                if _crosses(node.module):
                    findings.append(
                        Finding(
                            path=relative,
                            line=node.lineno,
                            imported=node.module or "",
                            shape="from-import",
                        )
                    )
    return Scan(findings=tuple(findings), modules_scanned=scanned)


def find_runtime_imports(root: Path) -> list[str]:
    """Every ``runtime`` import under ``root``, rendered for a failure message.

    The list the assertions below read. It is deliberately a list of strings
    rather than of :class:`Finding` values: what a reader of a red build needs
    is the file, the line and the shape, and a repr of a dataclass buries all
    three in punctuation.
    """
    return [str(finding) for finding in scan_source_tree(root).findings]


# --- the shipped assertion ---------------------------------------------------


def test_no_module_under_src_imports_the_runtime_package() -> None:
    """`D-29`: the boundary the client seam's whole design rests on."""
    found = find_runtime_imports(SRC_ROOT)
    assert found == [], (
        f"a module under src/ imports {RUNTIME_PACKAGE}. `D-29` (client design"
        " spec, Amendment 1 §B) rules there is no such edge and documents no"
        " exception, because none was needed: the resolver Protocol and its"
        " reference implementation both live in `src/`, and the composition"
        " they realize touches nothing outside `ccf`. An edge here is a ruling"
        " becoming false, not a lint becoming inconvenient — either the import"
        " belongs behind an adapter, or the ruling needs revisiting in a"
        " decision entry. Found:" + "".join(f"\n  - {site}" for site in found)
    )


def test_the_walk_read_a_real_tree() -> None:
    """The vacuity guard: an empty result over an empty walk proves nothing."""
    scan = scan_source_tree(SRC_ROOT)
    assert scan.modules_scanned > 0, (
        f"the walk over {SRC_ROOT} read no modules at all, so the assertion"
        " beside it passed without measuring anything — which is the failure"
        " mode this guard exists to make impossible"
    )


# --- the three sabotage controls (`D-22`) ------------------------------------
#
# Three, because three AST shapes. One control covering the top-level shape
# would license the other two on nothing but the claim that `ast.walk` is
# thorough, and the claim is exactly what is under test.
#
# Every control builds its tree under `tmp_path` and passes THAT ROOT into
# `find_runtime_imports`. No file under the real `src/` is touched by any of
# them, which `test_the_controls_leave_the_real_tree_alone` re-checks.

#: The import a violation would actually be — the shape `D-29` names as the one
#: that would have been the first `src` -> `runtime` edge in the tree.
VIOLATION = f"from {RUNTIME_PACKAGE}.mcp.egress import ProductResolverProtocol"


def _tree(root: Path, source: str) -> Path:
    """Write one module carrying ``source`` into a source-root-shaped tree."""
    package = root / "ccf" / "products"
    package.mkdir(parents=True)
    (root / "ccf" / "__init__.py").write_text("", encoding="utf-8")
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "resolver.py").write_text(source, encoding="utf-8")
    return root


def test_a_top_level_import_is_refused(tmp_path: Path) -> None:
    """Shape 1 — the ordinary import at the head of a module."""
    root = _tree(tmp_path / "src", f"{VIOLATION}\n")

    found = find_runtime_imports(root)

    assert found, "the walk admitted a top-level runtime import"
    assert RUNTIME_PACKAGE in found[0]
    assert "ccf/products/resolver.py" in found[0]


def test_an_import_inside_a_function_body_is_refused(tmp_path: Path) -> None:
    """Shape 2 — the deferred import, which a head-of-file regex misses.

    Not a hypothetical shape: this tree defers imports deliberately in several
    places to break cycles, so a deferred `runtime` import is the crossing most
    likely to be written by someone acting in good faith.
    """
    root = _tree(
        tmp_path / "src",
        f"def resolve() -> object:\n    {VIOLATION}\n    return ProductResolverProtocol\n",
    )

    found = find_runtime_imports(root)

    assert found, "the walk admitted a runtime import inside a function body"
    assert RUNTIME_PACKAGE in found[0]


def test_an_import_inside_a_type_checking_block_is_refused(tmp_path: Path) -> None:
    """Shape 3 — the typing-only import, which never executes.

    It still crosses the boundary: it makes `src/` unable to typecheck without
    `runtime/` present, which is the dependency `D-29` denies exists. A check
    that admitted this one would be asserting a property about *runtime
    behaviour* while claiming to assert one about *architecture*.
    """
    root = _tree(
        tmp_path / "src",
        "from typing import TYPE_CHECKING\n\n"
        f"if TYPE_CHECKING:\n    {VIOLATION}\n",
    )

    found = find_runtime_imports(root)

    assert found, "the walk admitted a runtime import under TYPE_CHECKING"
    assert RUNTIME_PACKAGE in found[0]


# --- the controls' own controls ---------------------------------------------


def test_a_clean_tree_is_admitted(tmp_path: Path) -> None:
    """The negative control: the walk is not simply refusing everything.

    Without this, all three sabotage controls would pass against a walk that
    reported a finding for every module it read, and the suite would be
    measuring nothing at all.
    """
    root = _tree(tmp_path / "src", "from ccf.products.gates import run_gates\n")

    scan = scan_source_tree(root)

    assert scan.findings == ()
    assert scan.modules_scanned == 3


def test_a_name_that_merely_shares_a_prefix_is_admitted(tmp_path: Path) -> None:
    """Prefix matching is on a dotted boundary, not on a bare string."""
    root = _tree(tmp_path / "src", f"import {RUNTIME_PACKAGE}x\n")

    assert find_runtime_imports(root) == []


def test_a_relative_import_is_admitted(tmp_path: Path) -> None:
    """A relative import names a sibling and cannot reach another package."""
    root = _tree(tmp_path / "src", "from . import gates\n")

    assert find_runtime_imports(root) == []


def test_the_controls_leave_the_real_tree_alone(tmp_path: Path) -> None:
    """Sabotage happens in a copy, never in the tree the assertion reads."""
    before = scan_source_tree(SRC_ROOT)
    _tree(tmp_path / "src", f"{VIOLATION}\n")
    after = scan_source_tree(SRC_ROOT)

    assert before == after
    assert after.findings == ()


@pytest.mark.parametrize(
    "shape",
    [
        f"{VIOLATION}\n",
        f"def f() -> None:\n    {VIOLATION}\n",
        "from typing import TYPE_CHECKING\n\n"
        f"if TYPE_CHECKING:\n    {VIOLATION}\n",
    ],
    ids=["top-level", "function-body", "type-checking"],
)
def test_every_shape_reports_its_line_and_kind(tmp_path: Path, shape: str) -> None:
    """A refusal a reader cannot act on is half a refusal."""
    root = _tree(tmp_path / "src", shape)

    (finding,) = scan_source_tree(root).findings

    assert finding.shape == "from-import"
    assert finding.line > 0
    assert finding.imported == f"{RUNTIME_PACKAGE}.mcp.egress"
