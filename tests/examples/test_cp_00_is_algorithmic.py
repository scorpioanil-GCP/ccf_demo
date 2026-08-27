"""Criterion 4 — the Context Product trees are ALGORITHMIC END TO END.

Whitepaper §7.6.6 and CLAUDE.md §11 ("No hidden model calls in the algorithmic
path") make Algorithmic ⇄ Semantic Alternation a structural invariant rather
than a convention. `CP-SPEC-000` assembles its product in **Assembly Mode 1**:
every step is a deterministic operator or projection, and no model is consulted
anywhere on the path. A claim of that shape which nothing enforces is an
editorial claim wearing better clothes, so this module is the gate.

**Why it is here and not in ``tools/lints/algorithmic.py``.** That checker
exists and its deny-set is the right one — but
``tools/lints/__main__.py::RULE_TREE_SCOPE`` scopes the ``algorithmic`` rule to
``("src", "runtime")``, deliberately: the rule keys off a module-level
``__ccf_mode__ = "algorithmic"`` dunder that library modules opt into, and
example code carries no such dunder. Widening that scope would be an edit to a
shipped gate, which `24-CONTEXT.md` `D-04` and criterion 16 both say this phase
does not make. So the deny-set is REUSED and the walk is new.

**Why ``LLM_MODULES`` is imported and never re-declared.** A local copy is how
one rule's edit silently changes another's — the argument
``tools/lints/__init__.py`` makes for its own shared helpers, and the argument
``tests/examples/test_section_one_is_agent_free.py`` repeats. A vendor SDK
added to the lint's deny-set arms this gate on the same commit; a copy here
would have to be remembered.

**Why AST rather than grep.** A grep for ``anthropic`` matches a docstring, a
comment and a URL as readily as an import, and misses ``from ccf import llm``.
The import graph is a syntactic fact, so it is read syntactically — and both
``tools.lints`` helpers are used, because
:func:`~tools.lints.imported_module_names` reports only ``ccf`` for ``from ccf
import llm`` (correctly — it cannot tell a submodule from an attribute without
importing, which a lint must not do) and
:func:`~tools.lints.submodule_import_names` supplies ``ccf.llm``. Phase 15.4's
review finding CR-02 was exactly that hole, and
``tools/lints/algorithmic.py``'s own docstring records the same hole being
found by execution in the SDK's own LLM seam. The second control below carries
that spelling deliberately: drop the second helper and that case turns red
rather than turning the whole gate quietly permissive.

**What this module proves, and what it cannot.** It proves that no module
anywhere under ``examples/cp-*`` IMPORTS an LLM client — the SDK's own
``ccf.llm`` seam or any of the vendor SDKs a module might reach for to bypass
it — at module scope or deferred inside a function. It does **not** prove that
no model was consulted: a subprocess, an HTTP call to a model endpoint, or a
shell-out are all invisible to an import walk. Saying so here is what stops a
green tick being read as more than it is. The complementary evidence for the
positive claim is
``tests/examples/test_cp_00_recipe_steps.py``, which checks each recipe step's
declared witness, and ``examples/cp-00-institutional-holders/artifacts/expected.yaml``,
whose content address is reproducible run to run — a thing no model call would
be.

**Scope: ``examples/cp-*``, by glob.** A second Context Product tree arms this
gate by existing rather than by being listed here.
"""

from __future__ import annotations

import ast
import pathlib
import shutil
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

if str(REPO_ROOT) not in sys.path:  # the tools/ package is not installed
    sys.path.insert(0, str(REPO_ROOT))

from tools.lints import (  # noqa: E402
    imported_module_names,
    matches_module,
    submodule_import_names,
)
from tools.lints.algorithmic import LLM_MODULES  # noqa: E402

#: The tree the scan walks. An argument everywhere below, so the injection
#: controls can repoint it at a copy and exercise the real predicate.
EXAMPLES_ROOT = REPO_ROOT / "examples"

#: Context Product examples by directory-name convention, and a glob rather
#: than a list. ``**`` matches the example directory and every subdirectory, so
#: a module nested under one is in scope too.
CONTEXT_PRODUCT_GLOB = "cp-*/**/*.py"

#: The directory form of the same convention, for the non-vacuity precondition.
CONTEXT_PRODUCT_DIR_GLOB = "cp-*"


# ---------------------------------------------------------------------------
# The scan.
# ---------------------------------------------------------------------------


def context_product_trees(root: pathlib.Path) -> list[pathlib.Path]:
    """Every Context Product example directory under `root`."""
    return sorted(
        path for path in root.glob(CONTEXT_PRODUCT_DIR_GLOB) if path.is_dir()
    )


def context_product_modules(root: pathlib.Path) -> list[pathlib.Path]:
    """Every Python module under every Context Product tree in `root`."""
    return sorted(root.glob(CONTEXT_PRODUCT_GLOB))


def reached_modules(source: str) -> set[str]:
    """Every module name the source's import statements bring into scope.

    The union of the two ``tools.lints`` helpers, walked over the WHOLE tree
    rather than only its top level: a deferred ``import anthropic`` inside a
    function is still a model call in the algorithmic path, which is the
    position ``tools/lints/algorithmic.py`` takes in its own docstring.

    ``package=`` is left at its default. Neither Context Product tree is a
    Python package — there is no ``__init__.py`` anywhere under
    ``examples/cp-*`` — so a relative import could not resolve at runtime
    either, and resolving one against a package that does not exist would be
    inventing a name. Stated rather than left to path accident.
    """
    reached: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        reached.update(imported_module_names(node))
        reached.update(submodule_import_names(node))
    return reached


def llm_imports(path: pathlib.Path) -> list[str]:
    """The ``LLM_MODULES`` members one module reaches, sorted, deduplicated.

    Matching is :func:`~tools.lints.matches_module`, which is dot-bounded, so
    ``openai_stub`` never matches the ``openai`` deny entry and
    ``ccf.llm.transport`` does match ``ccf.llm``.
    """
    reached = reached_modules(path.read_text(encoding="utf-8"))
    return sorted({name for name in reached if matches_module(name, LLM_MODULES)})


def offenders(root: pathlib.Path) -> dict[str, list[str]]:
    """``module path -> LLM modules it reaches``, for every offender."""
    found: dict[str, list[str]] = {}
    for module in context_product_modules(root):
        reached = llm_imports(module)
        if reached:
            found[module.relative_to(root).as_posix()] = reached
    return found


# ---------------------------------------------------------------------------
# Preconditions — a walk that read nothing would pass forever.
# ---------------------------------------------------------------------------


def test_the_context_product_tree_is_populated() -> None:
    """Both counts, in the message, because either being zero is the failure.

    A renamed ``examples/cp-*`` makes the glob match no directory; a tree of
    YAML and Markdown with no module makes it match no file. Each passes every
    assertion below over an empty set, and the algorithmic claim becomes a
    claim about nothing.
    """
    assert EXAMPLES_ROOT.is_dir(), f"missing examples tree: {EXAMPLES_ROOT}"

    trees = context_product_trees(EXAMPLES_ROOT)
    assert trees, (
        f"no Context Product example directories matching"
        f" {CONTEXT_PRODUCT_DIR_GLOB!r} under {EXAMPLES_ROOT} — the"
        " algorithmic gate is scanning nothing"
    )

    modules = context_product_modules(EXAMPLES_ROOT)
    assert modules, (
        f"{len(trees)} Context Product directory/directories exist"
        f" ({[tree.name for tree in trees]}) but contain no Python module"
        f" matching {CONTEXT_PRODUCT_GLOB!r}"
    )


def test_the_deny_set_is_the_shipped_one_and_is_not_empty() -> None:
    """The imported deny-set is non-empty and carries the SDK's own seam.

    An empty or renamed ``LLM_MODULES`` would make every assertion below pass
    without refusing anything. ``ccf.llm`` is asserted by name because it is
    the one entry that is the SDK's OWN LLM surface (D-IMPL-09) rather than a
    third-party SDK — the entry a walk over example code is most likely to
    meet, and the one whose parent-named spelling opened the hole
    ``tools/lints/algorithmic.py`` records.
    """
    assert LLM_MODULES, "tools.lints.algorithmic::LLM_MODULES is empty"
    assert "ccf.llm" in LLM_MODULES, sorted(LLM_MODULES)


# ---------------------------------------------------------------------------
# The gate.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module",
    context_product_modules(EXAMPLES_ROOT),
    ids=lambda path: path.relative_to(EXAMPLES_ROOT).as_posix(),
)
def test_no_context_product_module_imports_an_llm_client(
    module: pathlib.Path,
) -> None:
    """Criterion 4, per module, named in the failure.

    Parametrized rather than aggregated so the failing module is the test id
    rather than a name buried in an assertion message.
    """
    reached = llm_imports(module)
    assert not reached, (
        f"{module.relative_to(REPO_ROOT).as_posix()} imports {reached} —"
        " a Context Product assembled in Assembly Mode 1 is algorithmic end"
        " to end (whitepaper §7.6.6; CLAUDE.md §11). If this example needs a"
        " semantic stage, it is Assembly Mode 2 and its specification must"
        " say so."
    )


def test_the_shipped_tree_has_no_offender() -> None:
    """The same claim once more, aggregated — so a failure names every
    offending module AND every offending package at once."""
    found = offenders(EXAMPLES_ROOT)
    assert not found, found


# ---------------------------------------------------------------------------
# The injection controls — a guard that has never refused anything is a guard
# nobody has tested. TWO spellings, because one of them is the hole.
# ---------------------------------------------------------------------------


def _copied_tree(tmp_path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    """The shipped Context Product modules, copied under a fresh scan root.

    Copied rather than synthesized so the controls exercise the real files, the
    real glob and the real AST walk. Returns ``(root, target module)``.
    """
    for module in context_product_modules(EXAMPLES_ROOT):
        destination = tmp_path / module.relative_to(EXAMPLES_ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(module, destination)

    copied = context_product_modules(tmp_path)
    assert copied, "the copy walked no module — the control would prove nothing"
    return tmp_path, copied[0]


@pytest.mark.parametrize(
    ("injected", "expected_package"),
    [
        pytest.param(
            "import anthropic\n",
            "anthropic",
            id="import-anthropic (the plain spelling)",
        ),
        pytest.param(
            "from ccf import llm\n",
            "ccf.llm",
            id="from-ccf-import-llm (CR-02 spelling)",
        ),
    ],
)
def test_the_gate_refuses_an_injected_llm_import(
    tmp_path: pathlib.Path, injected: str, expected_package: str
) -> None:
    """Watched RED on an injected import, in BOTH spellings.

    ``from ccf import llm`` is the spelling that passes
    :func:`~tools.lints.imported_module_names` alone — it reports ``ccf``,
    which matches no deny entry. It is caught only because
    :func:`reached_modules` also asks
    :func:`~tools.lints.submodule_import_names`, and it is parametrized here so
    that dropping that call turns this case red rather than turning the whole
    gate quietly permissive (review finding CR-02;
    ``tools/lints/algorithmic.py`` review finding F0).

    The import is APPENDED rather than prepended. These modules open with a
    docstring followed by ``from __future__ import annotations``, and only a
    docstring and comments may precede a ``__future__`` import — a prepended
    line would make the copy unparseable, which is a syntax error masquerading
    as a caught violation.

    The failure names BOTH the module and the package, and both halves are
    asserted: a gate that says "something is wrong somewhere" is a gate whose
    output nobody can act on.
    """
    root, target = _copied_tree(tmp_path)

    # The copies alone still pass — so the refusal below is the injection and
    # not something the copy brought with it.
    assert not offenders(root), offenders(root)

    target.write_text(target.read_text(encoding="utf-8") + injected, "utf-8")

    found = offenders(root)
    assert found, (
        f"the gate admitted {injected.strip()!r} — it is not reading the"
        " import graph it claims to read"
    )
    key = target.relative_to(root).as_posix()
    assert key in found, found
    assert expected_package in found[key], found


def test_the_gate_ignores_the_denied_names_in_prose(
    tmp_path: pathlib.Path,
) -> None:
    """A comment or a docstring naming an LLM package is not an import.

    This is why the scan is an AST walk: a grep-shaped gate would fail on this
    module's own header, which names ``anthropic``, ``openai`` and ``ccf.llm``
    in prose — and a gate that cries wolf gets switched off.
    """
    root, target = _copied_tree(tmp_path)
    prose = "\n# Consults no anthropic, openai or ccf.llm client at any point.\n"
    target.write_text(target.read_text(encoding="utf-8") + prose, "utf-8")

    assert not offenders(root), offenders(root)


def test_the_gate_sees_an_import_deferred_inside_a_function(
    tmp_path: pathlib.Path,
) -> None:
    """A lazily-imported client is still a model call in the algorithmic path.

    ``tools/lints/algorithmic.py`` takes that position in its own docstring —
    "at module scope or deferred inside a function" — and this control is what
    makes :func:`reached_modules`' ``ast.walk`` (rather than a scan of
    ``tree.body``) load-bearing rather than incidental.
    """
    root, target = _copied_tree(tmp_path)
    deferred = "\n\ndef _late() -> None:\n    import openai\n\n    return openai\n"
    target.write_text(target.read_text(encoding="utf-8") + deferred, "utf-8")

    found = offenders(root)
    assert found, "a deferred import walked straight through the gate"
    assert "openai" in found[target.relative_to(root).as_posix()], found


def test_a_near_miss_package_name_is_not_a_finding(
    tmp_path: pathlib.Path,
) -> None:
    """The dot boundary, from the other side.

    ``matches_module`` is dot-bounded so ``openai_stub`` is not ``openai``. A
    prefix match would make this gate refuse a legitimately-named module, and a
    gate that refuses correct code is one somebody exempts rather than fixes.
    """
    root, target = _copied_tree(tmp_path)
    target.write_text(
        target.read_text(encoding="utf-8") + "\nimport openai_stub\n", "utf-8"
    )

    assert not offenders(root), offenders(root)
