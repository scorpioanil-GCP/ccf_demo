"""The consumer never imports the producer — asserted as an AST property.

**Who reads this and what fails when it moves.** ``make ci-core`` runs it on
every invocation and the CI ``tests`` job runs it on every push. The day a
client example's reader-visible code imports a deployment module, a producer
spine, or anything outside the standard library and *its own root's* permitted
packages, this test goes red in the same commit that did it.

Why it exists
-------------
Phase 16 shipped a first example whose ``consume.py`` imported the producer's
``deployment.MANIFEST`` — the consumer holding a path into the producer's
Control Plane configuration. Dave's verdict was that a seasoned developer would
not go near it. ``D-02`` makes the separation a rule; this module makes it a
property, because a rule nothing measures is a rule that lasted one phase.

Why AST and not a regex
------------------------
``tests/examples/test_spine_separation.py``'s regex ancestors were fooled by an
import deferred into a function body — the text ``import`` indented four spaces
does not match a pattern anchored at the start of a line, and a violation that
only executes on the second call is still a violation. :func:`ast.walk` sees
every :class:`ast.Import` and :class:`ast.ImportFrom` in the module regardless
of nesting, which is the whole reason to pay the parse.

Why the permitted set is derived, not enumerated
--------------------------------------------------
Standard-library membership comes from :data:`sys.stdlib_module_names`, so the
gate does not carry a list that goes stale one Python release later. The
example's reader-visible modules come from
:func:`reader_visible_modules`, which reads the example's *structure* — a gate
that names one filename in a constant protects one filename, and the next
example's entry module would be invisible to it.

Why the permitted set is PER ROOT, and why the two roots invert
----------------------------------------------------------------
A reader meeting :data:`PERMITTED_IMPORTS` cold will assume one of its two
entries is a mistake, because they say opposite things about the same package:

===============================  ==============  ==================
root                             ``ccf.client``  harness + ``mcp``
===============================  ==============  ==================
``hw1-companies-over-revenue``   permitted       forbidden
``hw1-harness-clients``          **forbidden**   permitted
===============================  ==============  ==================

Both are right, and the inversion is the whole point of the second example.
``hw1-companies-over-revenue/consume.py`` is a *CCF client*: importing
``ccf.client`` is its entire subject, and importing a harness would make it a
harness demonstration instead. The three ``hw1-harness-clients/client_*.py``
programs are *foreign harness clients* reaching a governed door over MCP: they
import Google ADK, the Claude Agent SDK, LangGraph and an MCP client, and a
``ccf`` import in one of them would silently retract the claim the example
exists to make — that a client learns nothing about CCF to use a Context
Product. So ``ccf`` is not merely absent from that root's permitted set; it is
**refused by name**, in a branch checked *before* the permitted-set test, so
the refusal survives somebody later widening that set (:func:`_refused_by_name`).

The runner is outside all of this, structurally rather than by exemption:
``examples/hw1-harness-clients/runner/drive.py`` imports ``ccf`` legitimately
and lives one directory down, where :func:`reader_visible_modules`'s
non-recursive ``glob`` does not reach. That is ``H-11``, and it is why no
name-based skip was added here — a hole in a structural rule is a hole the next
example widens.

**The subject is a parameter, never a fixed path.** ``check_example_purity``
takes the root it checks **and the permitted and refused sets it checks
against**, so every control below feeds a ``tmp_path`` copy into the **same**
function the shipped assertion calls, with its own policy. A gate pinned to a
hard-coded path cannot be sabotaged, because the sabotaged copy is never what
it reads — the defect class this project found spanning plans ``17-05``,
``17-06`` and ``17-10``. A gate whose *policy* is a module-level constant has
the same weakness one level up: a module-level **union** of the two roots'
permitted sets would pass every control here except ``C-20-5``, which is
exactly why ``C-20-5`` exists.

**Zero matches is a failure, not a pass.** A purity gate that globs an example
directory, finds nothing, and reports green is decorative. :func:`check_example_purity`
returns a violation when a root carries no reader-visible module at all, and
:func:`test_the_gate_refuses_an_empty_example_root` watches it do so.
"""

from __future__ import annotations

import ast
import pathlib
import re
import shlex
import shutil
import sys
from collections.abc import Sequence
from typing import NamedTuple

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The CCF-client example: one ``consume.py`` that imports ``ccf.client``.
HW1_ROOT = REPO_ROOT / "examples" / "hw1-companies-over-revenue"

#: The foreign-harness example: three ``client_*.py`` programs that import a
#: harness and an MCP client and know nothing about CCF (``H-11``/``H-12``).
HARNESS_ROOT = REPO_ROOT / "examples" / "hw1-harness-clients"

#: The one non-stdlib package the **hw1** client example's reader-visible code
#: may import. ``D-02``/``D-03``: the client surface is four names and nothing
#: producer-side crosses it. Submodules are permitted — ``D-05`` ships no
#: discovery chain, so a consumer must import its transport adapter's module
#: for the scheme to reach the registry, and that module lives under here.
PERMITTED_PACKAGE = "ccf.client"

#: What each gated root's reader-visible code may import, beyond the standard
#: library. See the module docstring for why the two entries invert.
#:
#: **THE ENTRIES ARE PACKAGE PREFIXES, NOT MODULE NAMES.** The container type
#: says the opposite and invites ``module in permitted``, which would refuse
#: every real import in this tree: ``consume.py`` imports
#: ``ccf.client.adapters.mcp_stdio``, and the three harness clients import
#: ``google.adk.tools.mcp_tool``, ``mcp.client.stdio``, ``langgraph.graph`` and
#: ``langchain_core.tools``. :func:`_permitted` matches by prefix and
#: ``T-20-40``'s control asserts it against those exact submodules — a change
#: to exact membership would read as a tightened gate and be a broken one.
PERMITTED_IMPORTS: dict[pathlib.Path, frozenset[str]] = {
    HW1_ROOT: frozenset({PERMITTED_PACKAGE}),
    HARNESS_ROOT: frozenset(
        {"google.adk", "claude_agent_sdk", "langgraph", "langchain_core", "mcp"}
    ),
}

#: What each gated root's reader-visible code may **never** import, whatever
#: its permitted set later grows to say. Criterion 5's wording is *"an AST check
#: refuses a ``ccf.*`` import in any of the three client programs"*, and "not in
#: the permitted set" is a weaker claim than "named and refused": the first
#: evaporates the day somebody widens a set, the second does not.
REFUSED_IMPORTS: dict[pathlib.Path, frozenset[str]] = {
    HW1_ROOT: frozenset(),
    HARNESS_ROOT: frozenset({"ccf"}),
}

#: The client examples this module gates. **Derived from the policy mapping
#: rather than maintained beside it** — a root present in one and absent from
#: the other is a root gated by half this module, and the half that goes
#: missing is silent.
CLIENT_EXAMPLE_ROOTS: tuple[pathlib.Path, ...] = tuple(PERMITTED_IMPORTS)


def reader_visible_modules(root: pathlib.Path) -> tuple[pathlib.Path, ...]:
    """The Python modules a reader of ``root`` is expected to study.

    **A property of the example's structure, not a filename.** Every ``.py``
    file sitting *directly* in the example root is reader-visible; anything in
    a subdirectory is not. That is exactly the boundary ``D-17`` draws — the
    example is an entry module beside an opaque ``deployment/`` — so the
    deployment's own projection is correctly outside this gate. It is the
    producer's world and it imports ``ccf.graph``, ``ccf.operators`` and
    ``ccf.projection`` legitimately.
    """
    return tuple(sorted(path for path in root.glob("*.py") if path.is_file()))


def _imports(tree: ast.AST) -> list[tuple[str, int, bool]]:
    """Every import in ``tree`` as ``(module, line, is_relative)``.

    :func:`ast.walk` rather than a scan of ``tree.body``: an import inside a
    function body, a class body, a ``try`` or an ``if`` is still an import, and
    the deferred form is the one the regex generation of this gate missed.
    """
    found: list[tuple[str, int, bool]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((alias.name, node.lineno, False) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            # `level > 0` is `from .x import y`. `module is None` is
            # `from . import y`. Both are relative and both are refused: a
            # client example importing a sibling is importing the producer.
            found.append((node.module or "", node.lineno, node.level > 0))
    return found


def _covers(module: str, prefix: str) -> bool:
    """Does the package ``prefix`` cover ``module``?

    Prefix matching, and at a package boundary: ``ccf.client`` covers
    ``ccf.client.adapters.mcp_stdio`` and does **not** cover ``ccf.clientele``.
    One function so the permitted test and the refusal test cannot drift into
    two different notions of "under".
    """
    return module == prefix or module.startswith(f"{prefix}.")


def _permitted(module: str, permitted: frozenset[str]) -> bool:
    """Is ``module`` one this root's reader-visible code may import?

    ``permitted`` is a **parameter**, not a module-level constant, because the
    two gated roots permit opposite things and a union of them would be a gate
    that checks neither. Every control below passes its own set to this same
    function.
    """
    root = module.partition(".")[0]
    if root == "__future__" or root in sys.stdlib_module_names:
        return True
    return any(_covers(module, prefix) for prefix in permitted)


def _refused_by_name(module: str, refused: frozenset[str]) -> str | None:
    """The refused package covering ``module``, or ``None``.

    Checked **before** :func:`_permitted` in :func:`check_example_purity`, so
    the refusal is unconditional: widening a root's permitted set cannot admit
    a package this names, and the violation text names the package rather than
    reporting the absence of a permission.
    """
    for prefix in sorted(refused):
        if _covers(module, prefix):
            return prefix
    return None


def check_example_purity(
    root: pathlib.Path, permitted: frozenset[str], refused: frozenset[str]
) -> list[str]:
    """Every purity violation in the example at ``root``, by name.

    Returns an empty list only when the root really was checked: a root with
    no reader-visible module yields a violation rather than a clean pass, so
    a moved or renamed example cannot make this gate green by emptiness.

    Args:
        root: The example root to walk. A parameter so a control can hand this
            function a doctored ``tmp_path`` copy.
        permitted: Package **prefixes** this root's code may import, beyond the
            standard library. A parameter for the same reason: the policy is
            per-root, and a control that could only ever be handed the shipped
            policy would not be watching the policy.
        refused: Package prefixes refused by name whatever ``permitted`` says.
    """
    violations: list[str] = []
    if not root.is_dir():
        return [f"{root} is not a directory, so nothing was checked"]

    modules = reader_visible_modules(root)
    if not modules:
        return [
            f"{root} carries no top-level `.py` module, so this gate checked"
            " nothing. An example whose reader-visible code has moved is an"
            " example this gate no longer protects — which is the vacuous pass"
            " it exists to be immune to"
        ]

    for module_path in modules:
        source = module_path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(module_path))
        except SyntaxError as broken:  # pragma: no cover - defensive
            violations.append(f"{module_path.name} does not parse: {broken}")
            continue
        for imported, line, is_relative in _imports(tree):
            named = _refused_by_name(imported, refused)
            if is_relative:
                violations.append(
                    f"{module_path.name}:{line} imports `{imported or '.'}`"
                    " relatively — a client example importing a sibling module"
                    " is the consumer reaching into the producer's directory,"
                    " which is exactly what `D-02` forbids"
                )
            elif named is not None:
                violations.append(
                    f"{module_path.name}:{line} imports `{imported}`, and"
                    f" `{named}` is refused by name in this example root. This"
                    " client's whole claim is that it learns nothing about CCF"
                    " to use a Context Product: it speaks MCP to a door and"
                    " reads a typed answer. One `ccf` import retracts that,"
                    " whatever the permitted set happens to say"
                )
            elif not _permitted(imported, permitted):
                violations.append(
                    f"{module_path.name}:{line} imports `{imported}`, which"
                    " is neither stdlib nor under"
                    f" {sorted(permitted)}. A client example knows the"
                    " product's identity and the question's parameters; it does"
                    " not know a manifest, a deployment or a producer spine"
                    " (`D-02`)"
                )
    return violations


# ---------------------------------------------------------------------------
# Preconditions — the gate must have a subject before it can have a verdict.
# ---------------------------------------------------------------------------


def test_the_gated_example_roots_exist() -> None:
    """Non-vacuity. A renamed example must turn this red, not make it empty."""
    assert CLIENT_EXAMPLE_ROOTS, "no client example is gated at all"
    for root in CLIENT_EXAMPLE_ROOTS:
        assert root.is_dir(), f"gated client example is missing: {root}"
        assert reader_visible_modules(root), (
            f"{root} carries no top-level `.py` module — every assertion below"
            " would pass over an empty set"
        )


def test_every_gated_root_carries_a_non_empty_permitted_set() -> None:
    """The policy mappings agree with each other and with the roots tuple.

    Three ways a root could be half-gated, each of them quiet:

    * a root in :data:`PERMITTED_IMPORTS` and not in :data:`REFUSED_IMPORTS`
      raises a ``KeyError`` at the call site rather than reporting a policy
      hole, and the two mappings are the whole policy;
    * a root added with an **empty** permitted set forbids every non-stdlib
      import, which turns a green gate red for the wrong reason and invites the
      wrong repair;
    * an entry whose key is not a real directory gates a path, not an example.
    """
    assert set(PERMITTED_IMPORTS) == set(REFUSED_IMPORTS), (
        "the permitted and refused mappings name different roots:"
        f" {sorted(p.name for p in PERMITTED_IMPORTS)} vs"
        f" {sorted(p.name for p in REFUSED_IMPORTS)}"
    )
    assert set(CLIENT_EXAMPLE_ROOTS) == set(PERMITTED_IMPORTS)
    for root in CLIENT_EXAMPLE_ROOTS:
        assert PERMITTED_IMPORTS[root], (
            f"{root.name} declares an empty permitted set, so every non-stdlib"
            " import in it would be a violation"
        )


def test_the_permitted_sets_are_prefixes_and_are_genuinely_per_root() -> None:
    """``T-20-40``. Prefix matching, asserted against what the tree imports.

    A ``frozenset`` invites ``module in permitted``. Exact membership would
    refuse ``ccf.client.adapters.mcp_stdio``, ``google.adk.tools.mcp_tool``,
    ``mcp.client.stdio``, ``langgraph.graph`` and ``langchain_core.tools`` —
    every real import in both gated roots — while reading like a tightened
    rule. The second half asserts the inversion: the submodule permitted for
    one root is refused for the other.
    """
    for module in ("ccf.client", "ccf.client.adapters.mcp_stdio"):
        assert _permitted(module, PERMITTED_IMPORTS[HW1_ROOT]), module
    for module in (
        "google.adk.tools.mcp_tool",
        "mcp",
        "mcp.client.stdio",
        "langchain_core.tools",
        "langgraph.graph",
        "claude_agent_sdk",
        "claude_agent_sdk.types",
    ):
        assert _permitted(module, PERMITTED_IMPORTS[HARNESS_ROOT]), module

    # The inversion, both ways.
    assert not _permitted(
        "ccf.client.adapters.mcp_stdio", PERMITTED_IMPORTS[HARNESS_ROOT]
    )
    assert not _permitted("google.adk.tools.mcp_tool", PERMITTED_IMPORTS[HW1_ROOT])

    # A prefix stops at a package boundary; it is not a string prefix.
    assert not _permitted("ccf.clientele", PERMITTED_IMPORTS[HW1_ROOT])
    assert not _permitted("mcpx", PERMITTED_IMPORTS[HARNESS_ROOT])


# ---------------------------------------------------------------------------
# The property.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "root", CLIENT_EXAMPLE_ROOTS, ids=lambda path: path.name
)
def test_the_client_example_imports_only_the_client_and_stdlib(
    root: pathlib.Path,
) -> None:
    violations = check_example_purity(
        root, PERMITTED_IMPORTS[root], REFUSED_IMPORTS[root]
    )
    assert not violations, "\n".join(violations)


# ---------------------------------------------------------------------------
# Controls. Three import shapes, because three AST shapes — plus the two
# vacuity cases, which are the ones a decorative gate passes silently.
# ---------------------------------------------------------------------------


#: What a copied example root never needs and must not carry into a control.
NOT_COPIED = shutil.ignore_patterns("__pycache__", "graph.sqlite3*", "artifact-store")


@pytest.fixture()
def example_copy(tmp_path: pathlib.Path) -> pathlib.Path:
    """A private copy of the **hw1** example, for a control to doctor."""
    root = tmp_path / "example"
    shutil.copytree(HW1_ROOT, root, ignore=NOT_COPIED)
    return root


@pytest.fixture()
def harness_copy(tmp_path: pathlib.Path) -> pathlib.Path:
    """A private copy of the **harness-clients** example, for ``C-20-*``.

    A second fixture rather than a parametrized one, because the two roots are
    doctored with opposite forgeries: the hw1 controls prepend a producer
    import, the harness controls prepend a ``ccf`` one. Sharing a fixture would
    force every control to carry a policy argument it does not use.
    """
    root = tmp_path / "harness-example"
    shutil.copytree(HARNESS_ROOT, root, ignore=NOT_COPIED)
    return root


def _entry_module(root: pathlib.Path) -> pathlib.Path:
    return reader_visible_modules(root)[0]


def _hw1_purity(root: pathlib.Path) -> list[str]:
    """Run the shipped checker over ``root`` under the **hw1** root's policy."""
    return check_example_purity(
        root, PERMITTED_IMPORTS[HW1_ROOT], REFUSED_IMPORTS[HW1_ROOT]
    )


def _harness_purity(root: pathlib.Path) -> list[str]:
    """Run the shipped checker over ``root`` under the **harness** root's policy."""
    return check_example_purity(
        root, PERMITTED_IMPORTS[HARNESS_ROOT], REFUSED_IMPORTS[HARNESS_ROOT]
    )


def _prepend(module: pathlib.Path, line: str) -> None:
    """Put ``line`` at the top of ``module``. The plainest forgery shape."""
    module.write_text(line + module.read_text(encoding="utf-8"), encoding="utf-8")


def test_the_unmodified_example_passes_the_checker(
    example_copy: pathlib.Path,
) -> None:
    """The controls' baseline: refusals below must come from the doctoring."""
    assert _hw1_purity(example_copy) == []


def test_the_gate_refuses_a_plain_import_of_the_deployment(
    example_copy: pathlib.Path,
) -> None:
    """Shape 1 — ``ast.Import``. The Phase 16 defect, in its original form."""
    module = _entry_module(example_copy)
    module.write_text(
        "import deployment\n" + module.read_text(encoding="utf-8"), encoding="utf-8"
    )
    violations = _hw1_purity(example_copy)
    assert any("deployment" in entry for entry in violations), violations


def test_the_gate_refuses_a_from_import_of_a_producer_module(
    example_copy: pathlib.Path,
) -> None:
    """Shape 2 — ``ast.ImportFrom``. A gate matching only ``ast.Import`` misses it."""
    module = _entry_module(example_copy)
    module.write_text(
        "from produce import assemble_and_serve\n"
        + module.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    violations = _hw1_purity(example_copy)
    assert any("produce" in entry for entry in violations), violations


def test_the_gate_refuses_an_import_deferred_into_a_function_body(
    example_copy: pathlib.Path,
) -> None:
    """Shape 3 — the one the regex ancestors were fooled by.

    Indented four spaces inside ``main``, so a pattern anchored at the start of
    a line finds nothing. It is still a producer import and it still executes.
    """
    module = _entry_module(example_copy)
    source = module.read_text(encoding="utf-8")
    doctored = source.replace(
        "    args = parse_args()",
        "    import deployment  # deferred\n    args = parse_args()",
        1,
    )
    assert doctored != source, "the control did not modify the module"
    module.write_text(doctored, encoding="utf-8")
    violations = _hw1_purity(example_copy)
    assert any("deployment" in entry for entry in violations), violations


def test_the_gate_refuses_a_relative_import(example_copy: pathlib.Path) -> None:
    """A sibling reached relatively is still the producer's directory."""
    module = _entry_module(example_copy)
    module.write_text(
        "from .deployment import projection\n"
        + module.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    violations = _hw1_purity(example_copy)
    assert any("relativ" in entry for entry in violations), violations


def test_the_gate_refuses_an_empty_example_root(tmp_path: pathlib.Path) -> None:
    """**The vacuity control.** Zero matches must fail, or the gate is decorative.

    A purity gate that globs a directory, finds no module and reports green
    protects nothing — and it reports green precisely when the example has been
    moved or renamed, which is when protection is most needed.
    """
    empty = tmp_path / "no-modules-here"
    empty.mkdir()
    violations = _hw1_purity(empty)
    assert violations, "an example root with no module passed the purity gate"
    assert any("checked nothing" in entry for entry in violations), violations


def test_the_gate_refuses_a_root_that_does_not_exist(
    tmp_path: pathlib.Path,
) -> None:
    """The other vacuity case: an unresolvable subject is a failure, not a pass."""
    violations = _hw1_purity(tmp_path / "was-renamed-away")
    assert violations, "a non-existent example root passed the purity gate"
    assert any("nothing was checked" in entry for entry in violations), violations


# ---------------------------------------------------------------------------
# C-20-1..C-20-7 — the harness root's controls (`CLNT-12`/`D-22`).
#
# The three `client_*.py` programs were written in waves 3 and 4 with no purity
# gate watching them; this is the first plan in which anything checks them. So
# the controls here are not decoration on a rule already proven — they are the
# only evidence the rule can fire against *this* root at all, and every one of
# them was observed red under a named mutation before it was committed.
#
# Every control feeds a doctored `tmp_path` copy to `check_example_purity`, the
# same function the shipped assertion calls, under the same policy the shipped
# assertion passes. Nothing below re-implements a check.
# ---------------------------------------------------------------------------


def test_the_unmodified_harness_example_passes_the_checker(
    harness_copy: pathlib.Path,
) -> None:
    """The harness controls' baseline: refusals below come from the doctoring.

    Also the non-vacuity guard for them all — a copy that already violated
    would make every ``C-20-*`` below pass without doctoring anything.
    """
    assert _harness_purity(harness_copy) == []
    assert len(reader_visible_modules(harness_copy)) >= 1, (
        "the harness copy carries no client program, so the controls below"
        " would doctor nothing"
    )


def test_c20_1_the_gate_refuses_a_plain_ccf_import_in_a_client(
    harness_copy: pathlib.Path,
) -> None:
    """``C-20-1`` — shape 1, ``ast.Import``, refused by name."""
    _prepend(_entry_module(harness_copy), "import ccf\n")
    violations = _harness_purity(harness_copy)
    assert violations, "a `ccf` import in a harness client passed the gate"
    assert all("ccf" in entry for entry in violations), violations
    assert any("refused by name" in entry for entry in violations), violations


def test_c20_2_the_gate_refuses_a_from_import_of_the_client_surface(
    harness_copy: pathlib.Path,
) -> None:
    """``C-20-2`` — shape 2, ``ast.ImportFrom``.

    ``from ccf.client import ProductClient`` is the *sympathetic* forgery: it
    imports the supported four-name surface rather than a producer spine, and a
    reader could talk themselves into it. It is still the thing this example
    claims not to do.
    """
    _prepend(_entry_module(harness_copy), "from ccf.client import ProductClient\n")
    violations = _harness_purity(harness_copy)
    assert violations, "`from ccf.client import ...` passed the gate"
    assert any("ccf.client" in entry for entry in violations), violations


def test_c20_3_the_gate_refuses_a_ccf_import_deferred_into_a_function_body(
    harness_copy: pathlib.Path,
) -> None:
    """``C-20-3`` — the shape Phase 19 measured a static grep missing.

    Indented four spaces inside ``main``, so a pattern anchored at the start of
    a line finds nothing. This is precisely why
    ``archive/examples/external/00-hello-context/run.py::_assert_zero_ccf_imports`` is
    **not** the precedent for criterion 5: it is a grep, and criterion 5 says
    AST.
    """
    module = _entry_module(harness_copy)
    source = module.read_text(encoding="utf-8")
    doctored = source.replace(
        "    args = parse_args()",
        "    import ccf  # deferred\n    args = parse_args()",
        1,
    )
    assert doctored != source, "the control did not modify the module"
    module.write_text(doctored, encoding="utf-8")
    assert "\n    import ccf" in doctored, (
        "the deferred import is not indented, so this control is testing the"
        " top-level shape `C-20-1` already covers"
    )
    violations = _harness_purity(harness_copy)
    assert violations, "a deferred `ccf` import passed the gate"
    assert any("refused by name" in entry for entry in violations), violations


def test_c20_4_the_gate_refuses_a_relative_import_of_the_runner(
    harness_copy: pathlib.Path,
) -> None:
    """``C-20-4`` — the fourth import shape.

    ``H-11`` puts the ``ccf``-importing runner one directory down, structurally
    outside :func:`reader_visible_modules`. A client reaching it relatively
    would walk straight back through that boundary, and the module name it
    reaches for is not ``ccf`` — so the by-name refusal cannot be what catches
    it. The relative branch is.
    """
    _prepend(_entry_module(harness_copy), "from .runner import drive\n")
    violations = _harness_purity(harness_copy)
    assert violations, "a relative import in a harness client passed the gate"
    assert any("relativ" in entry for entry in violations), violations


def test_c20_5_a_submodule_permitted_for_the_other_root_is_refused_here(
    harness_copy: pathlib.Path, example_copy: pathlib.Path
) -> None:
    """``C-20-5`` — **the control specific to this phase's change**.

    ``ccf.client.adapters.mcp_stdio`` is not a forgery in the abstract: it is
    exactly what ``hw1-companies-over-revenue/consume.py`` imports, legitimately
    and by design. The claim being controlled is that the permitted set is
    genuinely **per root** — that the same import is refused here and permitted
    there. A module-level *union* of the two roots' sets, which is the obvious
    simplification and the likely regression, passes every other control in this
    file and fails only this one (``T-20-23``).

    Both directions are asserted in one test on purpose. Half of it — the
    refusal — would also pass under a gate that refused ``ccf`` everywhere,
    which would break ``consume.py`` and be discovered somewhere else.
    """
    forgery = "import ccf.client.adapters.mcp_stdio\n"

    _prepend(_entry_module(harness_copy), forgery)
    refused = _harness_purity(harness_copy)
    assert refused, "a `ccf.client` submodule passed the harness root's gate"
    assert any("ccf.client.adapters.mcp_stdio" in entry for entry in refused), refused

    _prepend(_entry_module(example_copy), forgery)
    assert _hw1_purity(example_copy) == [], (
        "the same import was refused for the hw1 root, so the permitted set is"
        " not per-root — it is one union, and `consume.py` is inside it only by"
        " luck"
    )


def test_c20_6_the_gate_refuses_an_empty_harness_root(
    harness_copy: pathlib.Path,
) -> None:
    """``C-20-6`` — vacuity, for the newly gated root specifically.

    The three clients are the only reader-visible modules here, so a rename
    that moved them (into ``runner/``, say, which is the tidying this layout
    invites) would leave this gate globbing an empty directory and reporting
    green.
    """
    for module in reader_visible_modules(harness_copy):
        module.unlink()
    violations = _harness_purity(harness_copy)
    assert violations, "a harness root with no client program passed the gate"
    assert any("checked nothing" in entry for entry in violations), violations


def test_c20_7_the_gate_refuses_a_harness_root_that_does_not_exist(
    tmp_path: pathlib.Path,
) -> None:
    """``C-20-7`` — the other vacuity case for the new root."""
    violations = _harness_purity(tmp_path / "hw1-harness-clients-was-renamed")
    assert violations, "a non-existent harness root passed the purity gate"
    assert any("nothing was checked" in entry for entry in violations), violations


def test_the_runner_is_structurally_outside_the_gate() -> None:
    """``H-11``, asserted rather than assumed.

    ``runner/drive.py`` imports ``ccf`` and must: it seeds the subjects and
    computes the reference answer. It is outside this gate because it is one
    directory down and :func:`reader_visible_modules` does not recurse — not
    because anything here skips it by name. The day somebody moves it up beside
    the clients, ``C-20-1``'s rule fires on it, which is the correct outcome.
    """
    visible = {path.name for path in reader_visible_modules(HARNESS_ROOT)}
    assert visible == {"client_adk.py", "client_anthropic.py", "client_langgraph.py"}, (
        visible
    )
    assert (HARNESS_ROOT / "runner" / "drive.py").is_file(), (
        "the runner has moved; this assertion is no longer about anything"
    )


# ---------------------------------------------------------------------------
# T-17-35 — the documented commands and the run commands are the same strings.
#
# It lives in this module rather than its own because it is the same claim the
# rest of the file makes, one level out: *the example is what it says it is*. A
# documented command nobody runs and a run command nobody documents are the
# same defect seen from two sides.
#
# `D-IMPL-150` (Dave, 2026-08-17) made this a claim about a SET rather than a
# single string. Plan `17-10` documented an `mcp+stdio:` invocation that could
# not run — `consume.py` imported one adapter module and `D-05` ships no
# discovery chain — and a gate holding the README to *exactly one* command was
# structurally unable to notice, because the un-runnable one was in prose the
# gate did not read. Both transports are now documented, both have a `make`
# target, and the pairing is what is asserted. A third transport joins by being
# added to :data:`MAKE_TARGETS` and to the README, and the day only one of those
# two happens, this goes red.
# ---------------------------------------------------------------------------

#: The example's declared commands, in the README's fenced blocks. Matched by
#: their leading environment assignment rather than by position, so re-ordering
#: the README's sections cannot silently select a different block.
README_COMMAND = re.compile(r"^(CCF_BINDING=.*)$", re.MULTILINE)

#: The example's `make` targets, in the order their commands appear in the
#: README. Tab-indented recipe lines, which is what makes them recipes rather
#: than prose. The order is asserted, not merely assumed: pairing by set would
#: pass on a README that documented the MCP command under the in-process
#: heading, which is a documentation defect this gate is well placed to see.
MAKE_TARGETS: tuple[str, ...] = ("example-hw1:", "example-hw1-mcp:")

#: The harness example's declared commands. Anchored on the **invocation**
#: rather than on an environment assignment, because these three carry none:
#: what varies between them is a flag value, not a binding. :data:`README_COMMAND`
#: would match nothing here, which is why the pattern is a parameter.
HARNESS_README_COMMAND = re.compile(
    r"^(\.venv/bin/python examples/hw1-harness-clients/.*)$", re.MULTILINE
)

#: The harness example's per-leg `make` targets, in the order the README states
#: their commands. The all-legs target `example-hw1-harness-clients:` is
#: deliberately absent: it is the CI spelling, `$(ENV) $(PYTHON) …`, which is
#: correctly *not* a string a reader can type and correctly not documented as
#: one. A gate pairing it with a README block would be asserting the wrong
#: claim.
HARNESS_MAKE_TARGETS: tuple[str, ...] = (
    "example-hw1-harness-clients-adk:",
    "example-hw1-harness-clients-anthropic:",
    "example-hw1-harness-clients-langgraph:",
)


class CommandSpec(NamedTuple):
    """How one example root's documented commands are found and paired."""

    pattern: re.Pattern[str]
    targets: tuple[str, ...]


#: Per-root, for the same reason :data:`PERMITTED_IMPORTS` is per-root: the two
#: examples document different *shapes* of command, and a single module-level
#: pattern would read one root and silently find nothing in the other — a
#: findall over the wrong pattern returns an empty list, not an error.
#:
#: The hw1 assertions below still spell ``CLIENT_EXAMPLE_ROOTS[0]``, which is
#: the hw1 root and is what they are about; they were not repointed. The
#: harness assertions pass their pattern and targets explicitly instead, so
#: neither set can be silently redirected by a change to the tuple's order.
COMMAND_SPECS: dict[pathlib.Path, CommandSpec] = {
    HW1_ROOT: CommandSpec(README_COMMAND, MAKE_TARGETS),
    HARNESS_ROOT: CommandSpec(HARNESS_README_COMMAND, HARNESS_MAKE_TARGETS),
}


def documented_commands(
    root: pathlib.Path,
    pattern: re.Pattern[str] | None = None,
    targets: tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    """Every command the example's README tells a reader to type, in order.

    Args:
        root: The example root whose ``README.md`` is read.
        pattern: How that README states a command. Defaults to the root's entry
            in :data:`COMMAND_SPECS` — a lookup, never a module-level constant,
            so a caller who passes only a root still gets *that root's* rule.
        targets: The `make` targets those commands must pair with, in order.
    """
    if pattern is None or targets is None:
        spec = COMMAND_SPECS.get(root)
        assert spec is not None, (
            f"{root} has no entry in COMMAND_SPECS, so there is no rule for"
            " reading its documented commands. Pass a pattern and targets"
            " explicitly, or register the root"
        )
        pattern = spec.pattern if pattern is None else pattern
        targets = spec.targets if targets is None else targets

    readme = (root / "README.md").read_text(encoding="utf-8")
    matches = pattern.findall(readme)
    assert len(matches) == len(targets), (
        f"{root.name}/README.md states {len(matches)} commands matching"
        f" {pattern.pattern!r} and the Makefile carries {len(targets)} targets"
        " for them. Every documented command runs from a target and every"
        f" target is documented, so the two counts are one number: {matches}"
    )
    return tuple(match.strip() for match in matches)


def make_recipe(target: str, makefile_path: pathlib.Path | None = None) -> str:
    """The single recipe line ``make <target>`` runs.

    ``makefile_path`` is a parameter so a control can hand this function a
    synthetic ``Makefile`` whose target grew a second recipe line. The one-line
    rule below is what makes a recipe comparable to a README block at all, and
    a rule nothing has been watched enforcing is a rule on paper.
    """
    if makefile_path is None:
        makefile_path = REPO_ROOT / "Makefile"
    makefile = makefile_path.read_text(encoding="utf-8").splitlines()
    start = next(
        (index for index, line in enumerate(makefile) if line.startswith(target)),
        None,
    )
    assert start is not None, (
        f"`{target}` is not declared in {makefile_path}. A target the README"
        " documents and the Makefile does not carry is the divergence this"
        " check exists to find, so it is a failure rather than a lookup miss"
    )
    recipes: list[str] = []
    for line in makefile[start + 1 :]:
        if not line.startswith("\t"):
            break
        recipes.append(line.lstrip("\t"))
    assert len(recipes) == 1, (
        f"`{target}` has {len(recipes)} recipe lines; the identity criterion"
        f" needs exactly one so it can be compared to one README line: {recipes}"
    )
    return recipes[0].strip()


def command_identity_violations(documented: str, recipe: str) -> list[str]:
    """Every way ``documented`` and ``recipe`` fail to be the same command.

    A function of two strings so the controls can feed it a divergent pair.
    A comparison that can only ever be handed the passing pair is a comparison
    nobody has watched fail.
    """
    violations: list[str] = []
    if not documented or not recipe:
        violations.append(
            "one side of the comparison is empty, so nothing was compared —"
            f" documented={documented!r} recipe={recipe!r}"
        )
        return violations
    if documented != recipe:
        violations.append(
            "the README's documented command and the `make` recipe have"
            f" diverged.\n  README:   {documented!r}\n  Makefile: {recipe!r}"
        )
    if ".venv/bin/python" not in documented:
        violations.append(
            "the documented command does not spell the interpreter"
            " `.venv/bin/python` — `which python` returns nothing in this"
            " repository, so a documented bare `python` does not run"
        )
    if "$(PYTHON)" in recipe:
        violations.append(
            "the recipe uses `$(PYTHON)`, which is not a string a reader can"
            " type, so it cannot be character-identical to any README line"
        )
    return violations


@pytest.mark.parametrize("index", range(len(MAKE_TARGETS)), ids=MAKE_TARGETS)
def test_the_make_target_runs_the_readmes_documented_command(index: int) -> None:
    """``T-17-35``. A divergence makes the documented command untested."""
    violations = command_identity_violations(
        documented_commands(CLIENT_EXAMPLE_ROOTS[0])[index],
        make_recipe(MAKE_TARGETS[index]),
    )
    assert not violations, "\n".join(violations)


def scheme_and_address(binding: str) -> tuple[str, str]:
    """Split one documented ``CCF_BINDING=<scheme>:<address>`` token into its two halves.

    A module-level function taking its subject as a **parameter**, so the
    sabotage control below can hand the *shipped* splitter a deliberately
    malformed token and be watched refusing it. Splitting inline would leave
    the vacuity case — a token with no address, whose two halves are two empty
    strings that compare equal to each other — measured by nothing.
    """
    name, assigned, value = binding.partition("=")
    assert assigned and name == "CCF_BINDING", (
        f"`{binding}` is not a `CCF_BINDING` assignment, so the tokens this"
        " test compares are not the ones the README's claim is about"
    )
    scheme, separator, address = value.partition(":")
    assert scheme and separator and address, (
        f"`{binding}` does not state `<scheme>:<address>`. Empty halves would"
        " make the comparisons below pass on nothing, which is the shape this"
        " test was found in: `18.1-CLOSE-REVIEWS` finding 3"
    )
    return scheme, address


def test_every_documented_command_names_a_distinct_binding_scheme() -> None:
    """``D-IMPL-150``: the two commands differ in the SCHEME and nowhere else.

    The portability claim is *"the same* ``consume.py``\\ *, a different*
    ``CCF_BINDING``\\ *"*, and a README that documented the same binding twice —
    or that quietly changed the threshold alongside the transport — would be
    demonstrating something weaker while reading the same.

    **Three legs, and the middle one was missing until `18.1-06`.** The schemes
    are distinct, the address *after* the scheme is the same string in both, and
    everything after the assignment is identical. Without the middle leg the
    README's sentence — *"the two strings differ by one word, the scheme"* — was
    credited to this test while resting on nothing: measured at close review by
    repointing the documented ``mcp+stdio`` address at a nonexistent
    ``…/OTHERDEPLOYMENT`` in both README and Makefile, which left all 17 purity
    tests green. Two commands naming two different deployments are not a
    portability demonstration; they are two demonstrations.
    """
    # `shlex.split` rather than a naive `split(" ", 1)`, so this stays correct
    # for any address a scheme cares to define — and because the assertions
    # below compare the tokens AFTER the assignment, which a hand-rolled split
    # would have to reconstruct.
    tokens = [shlex.split(command) for command in documented_commands(
        CLIENT_EXAMPLE_ROOTS[0]
    )]
    bindings = [parts[0] for parts in tokens]
    remainders = {tuple(parts[1:]) for parts in tokens}
    halves = [scheme_and_address(binding) for binding in bindings]

    assert len(set(bindings)) == len(bindings), (
        f"two documented commands carry the same binding: {bindings}"
    )
    schemes = [scheme for scheme, _ in halves]
    assert len(set(schemes)) == len(schemes), (
        f"two documented commands name the same scheme: {schemes}"
    )
    addresses = {address for _, address in halves}
    assert len(addresses) == 1, (
        "the documented commands name different addresses — the README's claim"
        " is that only the SCHEME changes, so the same deployment must be"
        f" reached both ways, and these reach {sorted(addresses)}"
    )
    assert len(remainders) == 1, (
        "the documented commands differ in more than `CCF_BINDING` — the claim"
        " is that only the binding changes, and these change"
        f" {sorted(remainders)}"
    )


@pytest.mark.parametrize(
    ("label", "binding"),
    [
        ("no assignment at all", "inprocess:examples/x/deployment"),
        ("some other variable", "CCF_OTHER=inprocess:examples/x/deployment"),
        ("no scheme separator", "CCF_BINDING=examples/x/deployment"),
        ("an empty address", "CCF_BINDING=inprocess:"),
        ("an empty scheme", "CCF_BINDING=:examples/x/deployment"),
    ],
)
def test_the_binding_splitter_refuses_a_token_it_cannot_compare(
    label: str, binding: str
) -> None:
    """The vacuity control for the address leg — two empty halves compare equal.

    ``len(addresses) == 1`` is satisfied by ``{""}`` just as well as by one
    real address, so a splitter that quietly returned empty halves would hand
    the strengthened test back the weakness it was written to remove. Each
    malformed shape is fed to the **shipped** splitter and watched refusing.
    """
    with pytest.raises(AssertionError):
        scheme_and_address(binding)


@pytest.mark.parametrize(
    ("label", "mutate"),
    [
        ("a changed flag name", lambda c: c.replace("--min-revenue", "--minimum")),
        ("a changed threshold", lambda c: c.replace("1000000000", "5000000000")),
        ("a bare interpreter", lambda c: c.replace(".venv/bin/python", "python")),
        ("a make variable", lambda c: c.replace(".venv/bin/python", "$(PYTHON)")),
    ],
)
def test_the_identity_check_refuses_a_divergent_pair(
    label: str, mutate: object
) -> None:
    """Control: the shipped comparison, fed a pair that differs."""
    documented = documented_commands(CLIENT_EXAMPLE_ROOTS[0])[0]
    recipe = mutate(documented)  # type: ignore[operator]
    assert recipe != documented, f"the {label} control did not change anything"
    assert command_identity_violations(documented, recipe), label


def test_the_identity_check_refuses_an_empty_side() -> None:
    """The vacuity control: comparing nothing to nothing is not agreement."""
    violations = command_identity_violations("", "")
    assert violations, "two empty strings were reported as an identical command"
    assert any("nothing was compared" in entry for entry in violations), violations


# ---------------------------------------------------------------------------
# The harness example's documented commands — the same claim, one root over.
#
# Coverage here had to be added DELIBERATELY. The machinery above is pinned to
# `CLIENT_EXAMPLE_ROOTS[0]` and to `MAKE_TARGETS`, so adding a root to
# `PERMITTED_IMPORTS` pointed the *purity* assertions at the new README and
# pointed none of these at it. That is the good half — no accidental red — and
# the bad half — no coverage — of the same fact, and the bad half is the one
# that goes unnoticed.
#
# The hw1 claim is "the two commands differ in the CCF_BINDING SCHEME and
# nowhere else". This root's claim is its analogue: "the three commands differ
# in the LEG NAME and nowhere else" — one product, one door, three harnesses.
# `test_every_documented_command_names_a_distinct_binding_scheme` above is NOT
# parametrized over this root: it is about `CCF_BINDING` values, which these
# commands do not carry, and stretching it would make it a test of two
# unrelated things.
# ---------------------------------------------------------------------------


def single_token_difference_violations(
    commands: Sequence[str], minimum: int = 3
) -> list[str]:
    """Every way ``commands`` fail to differ at exactly one token position.

    A function of a command list so the controls can feed it a doctored set —
    the same discipline :func:`command_identity_violations` follows. A
    comparison that can only ever be handed the passing set is a comparison
    nobody has watched fail, and the ``18.1-CLOSE-REVIEWS`` finding recorded in
    :func:`test_every_documented_command_names_a_distinct_binding_scheme` is
    what that costs: a strengthened assertion resting on a vacuous split.

    Args:
        commands: The documented commands, in README order.
        minimum: How many are needed before the conclusion means anything.
            Two commands naming two different subjects are not one
            demonstration; they are two. Below this count the answer is a
            violation, never a trivially-satisfied comparison.
    """
    violations: list[str] = []
    if len(commands) < minimum:
        return [
            f"only {len(commands)} documented command(s) were found and the"
            f" claim needs {minimum}. A one-token difference across a set this"
            " small is arithmetic, not a demonstration — and an empty set"
            " satisfies every comparison below by having nothing to compare"
        ]

    token_lists = [shlex.split(command) for command in commands]
    if not all(token_lists):
        return [
            "a documented command split into no tokens, so the comparison"
            f" below would run over nothing: {commands}"
        ]
    widths = {len(tokens) for tokens in token_lists}
    if len(widths) != 1:
        return [
            "the documented commands are different lengths, so they differ in"
            f" more than one token by construction: {sorted(widths)} tokens"
            f" across {commands}"
        ]

    width = widths.pop()
    differing = [
        index
        for index in range(width)
        if len({tokens[index] for tokens in token_lists}) != 1
    ]
    if len(differing) != 1:
        return [
            f"the documented commands differ at {len(differing)} token"
            f" positions {differing}, and the README's claim is exactly one."
            " Everything but the harness must be the same string: the same"
            f" runner, the same flag, the same interpreter. {commands}"
        ]

    values = [tokens[differing[0]] for tokens in token_lists]
    if len(set(values)) != len(values):
        violations.append(
            "two documented commands name the same value at the one differing"
            f" position: {values}. A set with a repeat is demonstrating fewer"
            " subjects than it appears to"
        )
    return violations


@pytest.mark.parametrize(
    "index", range(len(HARNESS_MAKE_TARGETS)), ids=HARNESS_MAKE_TARGETS
)
def test_the_harness_make_target_runs_the_readmes_documented_command(
    index: int,
) -> None:
    """``T-17-35``, for the harness root. A divergence leaves a command untested."""
    violations = command_identity_violations(
        documented_commands(
            HARNESS_ROOT, HARNESS_README_COMMAND, HARNESS_MAKE_TARGETS
        )[index],
        make_recipe(HARNESS_MAKE_TARGETS[index]),
    )
    assert not violations, "\n".join(violations)


def test_the_three_harness_commands_differ_in_exactly_one_token() -> None:
    """One product, one door, three harnesses — made checkable.

    Not the door, not the deployment, not the question, not the temporal
    boundary. One token, and it is the name of the harness. A README that
    quietly changed the flag alongside the leg would be demonstrating something
    weaker while reading the same, which is the failure
    ``18.1-CLOSE-REVIEWS`` found one root over.
    """
    commands = documented_commands(
        HARNESS_ROOT, HARNESS_README_COMMAND, HARNESS_MAKE_TARGETS
    )
    violations = single_token_difference_violations(commands)
    assert not violations, "\n".join(violations)

    # And the differing token really is the leg name, not an accident of
    # position: every value it takes is a leg this example ships a client for.
    differing = {
        shlex.split(command)[-1] for command in commands
    }
    shipped = {
        path.stem.removeprefix("client_")
        for path in reader_visible_modules(HARNESS_ROOT)
    }
    assert differing == shipped, (
        "the documented commands name legs the example does not ship, or omit"
        f" ones it does: documented {sorted(differing)}, shipped {sorted(shipped)}"
    )


# ---------------------------------------------------------------------------
# C-20-8 and the two further command-identity controls.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "mutate"),
    [
        ("a make variable", lambda c: c.replace(".venv/bin/python", "$(PYTHON)")),
        ("a bare interpreter", lambda c: c.replace(".venv/bin/python", "python")),
        ("a changed leg name", lambda c: c.replace("--legs adk", "--legs anthropic")),
        ("a changed flag name", lambda c: c.replace("--legs", "--leg")),
        ("a changed runner path", lambda c: c.replace("runner/drive.py", "drive.py")),
    ],
)
def test_c20_8_the_identity_check_refuses_a_divergent_harness_pair(
    label: str, mutate: object
) -> None:
    """``C-20-8`` — the shipped comparison, fed a pair that differs.

    The first two shapes are the ones :func:`command_identity_violations` names
    in its own text, and they are here rather than assumed: `$(PYTHON)` in a
    recipe and a bare `python` in a README block are the two spellings a
    well-meaning tidy-up produces, and both would leave a documented command
    that does not run in this repository.
    """
    documented = documented_commands(
        HARNESS_ROOT, HARNESS_README_COMMAND, HARNESS_MAKE_TARGETS
    )[0]
    recipe = mutate(documented)  # type: ignore[operator]
    assert recipe != documented, f"the {label} control did not change anything"
    assert command_identity_violations(documented, recipe), label


@pytest.mark.parametrize(
    ("label", "unusable", "because"),
    [
        (
            "both sides spell `$(PYTHON)`",
            "$(PYTHON) examples/hw1-harness-clients/runner/drive.py --legs adk",
            "not a string a reader can type",
        ),
        (
            "both sides spell a bare `python`",
            "python examples/hw1-harness-clients/runner/drive.py --legs adk",
            "does not spell the interpreter",
        ),
    ],
)
def test_c20_8_the_identity_check_refuses_an_identical_but_untypeable_pair(
    label: str, unusable: str, because: str
) -> None:
    """``C-20-8``, the half a divergence control cannot reach.

    Every mutation above is caught by ``documented != recipe`` once the two
    sides disagree — which measured the ``$(PYTHON)`` and ``.venv/bin/python``
    branches **redundant** when they were fed a divergent pair, and this test
    exists because that measurement came back green and had to be answered
    rather than reported.

    The shape those two branches alone can catch is a README and a recipe that
    **agree perfectly** and are still not a command a reader can run: both
    sides written as ``$(PYTHON) …``, or both as a bare ``python …``. Identity
    is necessary for this gate and it was never sufficient — a documented
    command is a promise that typing it works.

    The expected *reason* is asserted, not just the count. Both branches fire
    on the ``$(PYTHON)`` pair, so a test asserting only "some violation" would
    stay green with the ``$(PYTHON)`` branch deleted — measured, and the reason
    this parametrization carries a third column.
    """
    violations = command_identity_violations(unusable, unusable)
    assert violations, (
        f"an identical pair that nobody can type was accepted ({label}):"
        f" {unusable!r}"
    )
    assert any(because in entry for entry in violations), (
        f"the refusal for {label} did not say why: expected {because!r} in"
        f" {violations}"
    )


@pytest.mark.parametrize(
    ("label", "commands"),
    [
        (
            "two tokens differ",
            (
                ".venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs adk",
                ".venv/bin/python examples/hw1-harness-clients/runner/drive.py --live anthropic",
                ".venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs langgraph",
            ),
        ),
        (
            "a repeated value at the one differing position",
            (
                ".venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs adk",
                ".venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs adk",
                ".venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs langgraph",
            ),
        ),
        (
            "two tokens differ and BOTH carry distinct values",
            (
                ".venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs adk --scratch /tmp/adk",
                ".venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs anthropic --scratch /tmp/anthropic",
                ".venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs langgraph --scratch /tmp/langgraph",
            ),
        ),
        (
            "no token differs at all",
            (
                ".venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs adk",
                ".venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs adk",
                ".venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs adk",
            ),
        ),
        (
            "different lengths",
            (
                ".venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs adk",
                ".venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs anthropic --live",
                ".venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs langgraph",
            ),
        ),
        (
            "**the vacuity case** — fewer than three commands",
            (
                ".venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs adk",
                ".venv/bin/python examples/hw1-harness-clients/runner/drive.py --legs anthropic",
            ),
        ),
        ("**the vacuity case** — no commands at all", ()),
    ],
)
def test_the_one_token_claim_refuses_a_set_that_cannot_carry_it(
    label: str, commands: tuple[str, ...]
) -> None:
    """Control: the shipped comparison, fed sets that do not support the claim.

    Three of these are load-bearing beyond the obvious, and each was **measured
    necessary** by mutating the shipped function and watching this test:

    * *two tokens differ and both carry distinct values* — the only case that
      holds the ``len(differing) != 1`` rule itself. Loosening it to ``< 1``
      leaves every other case here green, because they are caught by the
      length check, the distinctness check or the minimum. It is also the
      realistic defect: three commands that change the *subject* alongside the
      harness, which is the ``18.1-CLOSE-REVIEWS`` finding one root over.
    * the two vacuity cases. ``len(differing) == 1`` is satisfied by a
      two-command set as readily as by a three-command one, and an empty set
      satisfies it by never entering the loop — so a README that lost a fenced
      block would strengthen this test's arithmetic while destroying its
      subject.
    """
    assert single_token_difference_violations(commands), label


def test_the_recipe_reader_refuses_a_target_with_two_recipe_lines(
    tmp_path: pathlib.Path,
) -> None:
    """Control: a recipe that grew a second line is no longer one command.

    Fed to the **shipped** :func:`make_recipe` through its ``makefile_path``
    parameter, because the rule lives in that function and a control that
    re-implemented the scan would be watching itself. A target whose recipe
    grows a second line silently stops being comparable to a README block, and
    the natural repair — comparing the first line only — is how a gate ends up
    blessing a command that does something else afterwards.
    """
    target = HARNESS_MAKE_TARGETS[0]
    body = target + " ## two lines\n\t.venv/bin/python one.py\n\t.venv/bin/python two.py\n"
    two_lines = tmp_path / "Makefile"
    two_lines.write_text(body, encoding="utf-8")
    with pytest.raises(AssertionError, match="2 recipe lines"):
        make_recipe(target, two_lines)

    one_line = tmp_path / "Makefile.one"
    one_line.write_text(
        target + " ## one line\n\t.venv/bin/python one.py\n", encoding="utf-8"
    )
    assert make_recipe(target, one_line) == ".venv/bin/python one.py", (
        "the control's own Makefile shape is not readable by the shipped"
        " function, so the refusal above proved nothing"
    )


def test_the_recipe_reader_refuses_a_target_that_is_not_declared(
    tmp_path: pathlib.Path,
) -> None:
    """Control: a documented target the Makefile does not carry fails loudly.

    Without this the lookup raised ``StopIteration``, which pytest reports as
    an error rather than as the divergence it is — and which a caller could
    catch and read as "no recipe", i.e. as nothing to compare.
    """
    empty = tmp_path / "Makefile"
    empty.write_text("# nothing here\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="is not declared"):
        make_recipe(HARNESS_MAKE_TARGETS[0], empty)
