"""The consumer never imports the producer — asserted as an AST property.

**Who reads this and what fails when it moves.** ``make ci-core`` runs it on
every invocation and the CI ``tests`` job runs it on every push. The day a
client example's reader-visible code imports a deployment module, a producer
spine, or anything outside ``ccf.client`` and the standard library, this test
goes red in the same commit that did it.

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

**The subject is a parameter, never a fixed path.** ``check_example_purity``
takes the root it checks, so every control below feeds a ``tmp_path`` copy into
the **same** function the shipped assertion calls. A gate pinned to a hard-coded
path cannot be sabotaged, because the sabotaged copy is never what it reads —
the defect class this project found spanning plans ``17-05``, ``17-06`` and
``17-10``.

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

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The client example this module gates. One entry today; a second client
#: example joins by being added here, and every function below already takes
#: its root as an argument.
CLIENT_EXAMPLE_ROOTS: tuple[pathlib.Path, ...] = (
    REPO_ROOT / "examples" / "hw1-companies-over-revenue",
)

#: The one non-stdlib package a client example's reader-visible code may
#: import. ``D-02``/``D-03``: the client surface is four names and nothing
#: producer-side crosses it. Submodules are permitted — ``D-05`` ships no
#: discovery chain, so a consumer must import its transport adapter's module
#: for the scheme to reach the registry, and that module lives under here.
PERMITTED_PACKAGE = "ccf.client"


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


def _permitted(module: str) -> bool:
    """Is ``module`` one a client example's reader-visible code may import?"""
    root = module.partition(".")[0]
    if root == "__future__" or root in sys.stdlib_module_names:
        return True
    return module == PERMITTED_PACKAGE or module.startswith(f"{PERMITTED_PACKAGE}.")


def check_example_purity(root: pathlib.Path) -> list[str]:
    """Every purity violation in the example at ``root``, by name.

    Returns an empty list only when the root really was checked: a root with
    no reader-visible module yields a violation rather than a clean pass, so
    a moved or renamed example cannot make this gate green by emptiness.
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
            if is_relative:
                violations.append(
                    f"{module_path.name}:{line} imports `{imported or '.'}`"
                    " relatively — a client example importing a sibling module"
                    " is the consumer reaching into the producer's directory,"
                    " which is exactly what `D-02` forbids"
                )
            elif not _permitted(imported):
                violations.append(
                    f"{module_path.name}:{line} imports `{imported}`, which is"
                    f" neither stdlib nor `{PERMITTED_PACKAGE}`. A client"
                    " example knows the product's identity and the question's"
                    " parameters; it does not know a manifest, a deployment or"
                    " a producer spine (`D-02`)"
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


# ---------------------------------------------------------------------------
# The property.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "root", CLIENT_EXAMPLE_ROOTS, ids=lambda path: path.name
)
def test_the_client_example_imports_only_the_client_and_stdlib(
    root: pathlib.Path,
) -> None:
    violations = check_example_purity(root)
    assert not violations, "\n".join(violations)


# ---------------------------------------------------------------------------
# Controls. Three import shapes, because three AST shapes — plus the two
# vacuity cases, which are the ones a decorative gate passes silently.
# ---------------------------------------------------------------------------


@pytest.fixture()
def example_copy(tmp_path: pathlib.Path) -> pathlib.Path:
    """A private copy of the real example, for a control to doctor."""
    root = tmp_path / "example"
    shutil.copytree(CLIENT_EXAMPLE_ROOTS[0], root)
    return root


def _entry_module(root: pathlib.Path) -> pathlib.Path:
    return reader_visible_modules(root)[0]


def test_the_unmodified_example_passes_the_checker(
    example_copy: pathlib.Path,
) -> None:
    """The controls' baseline: refusals below must come from the doctoring."""
    assert check_example_purity(example_copy) == []


def test_the_gate_refuses_a_plain_import_of_the_deployment(
    example_copy: pathlib.Path,
) -> None:
    """Shape 1 — ``ast.Import``. The Phase 16 defect, in its original form."""
    module = _entry_module(example_copy)
    module.write_text(
        "import deployment\n" + module.read_text(encoding="utf-8"), encoding="utf-8"
    )
    violations = check_example_purity(example_copy)
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
    violations = check_example_purity(example_copy)
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
    violations = check_example_purity(example_copy)
    assert any("deployment" in entry for entry in violations), violations


def test_the_gate_refuses_a_relative_import(example_copy: pathlib.Path) -> None:
    """A sibling reached relatively is still the producer's directory."""
    module = _entry_module(example_copy)
    module.write_text(
        "from .deployment import projection\n"
        + module.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    violations = check_example_purity(example_copy)
    assert any("relativ" in entry for entry in violations), violations


def test_the_gate_refuses_an_empty_example_root(tmp_path: pathlib.Path) -> None:
    """**The vacuity control.** Zero matches must fail, or the gate is decorative.

    A purity gate that globs a directory, finds no module and reports green
    protects nothing — and it reports green precisely when the example has been
    moved or renamed, which is when protection is most needed.
    """
    empty = tmp_path / "no-modules-here"
    empty.mkdir()
    violations = check_example_purity(empty)
    assert violations, "an example root with no module passed the purity gate"
    assert any("checked nothing" in entry for entry in violations), violations


def test_the_gate_refuses_a_root_that_does_not_exist(
    tmp_path: pathlib.Path,
) -> None:
    """The other vacuity case: an unresolvable subject is a failure, not a pass."""
    violations = check_example_purity(tmp_path / "was-renamed-away")
    assert violations, "a non-existent example root passed the purity gate"
    assert any("nothing was checked" in entry for entry in violations), violations


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


def documented_commands(root: pathlib.Path) -> tuple[str, ...]:
    """Every command the example's README tells a reader to type, in order."""
    readme = (root / "README.md").read_text(encoding="utf-8")
    matches = README_COMMAND.findall(readme)
    assert len(matches) == len(MAKE_TARGETS), (
        f"{root.name}/README.md states {len(matches)} commands beginning"
        f" `CCF_BINDING=` and the Makefile carries {len(MAKE_TARGETS)} targets"
        " for them. Every documented command runs from a target and every"
        f" target is documented, so the two counts are one number: {matches}"
    )
    return tuple(match.strip() for match in matches)


def make_recipe(target: str) -> str:
    """The single recipe line ``make <target>`` runs."""
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8").splitlines()
    start = next(
        index for index, line in enumerate(makefile) if line.startswith(target)
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


def test_every_documented_command_names_a_distinct_binding_scheme() -> None:
    """``D-IMPL-150``: the two commands differ in ``CCF_BINDING`` and nowhere else.

    The portability claim is *"the same* ``consume.py``\\ *, a different*
    ``CCF_BINDING``\\ *"*, and a README that documented the same binding twice —
    or that quietly changed the threshold alongside the transport — would be
    demonstrating something weaker while reading the same. So the schemes must
    be distinct and everything after the assignment must be identical.
    """
    # `shlex.split`, because an `mcp+stdio:` address is two whitespace-separated
    # tokens inside one quoted value — the very shape a naive `split(" ", 1)`
    # would tear in half, reporting the deployment root as part of the command.
    tokens = [shlex.split(command) for command in documented_commands(
        CLIENT_EXAMPLE_ROOTS[0]
    )]
    bindings = [parts[0] for parts in tokens]
    remainders = {tuple(parts[1:]) for parts in tokens}

    assert len(set(bindings)) == len(bindings), (
        f"two documented commands carry the same binding: {bindings}"
    )
    assert len(remainders) == 1, (
        "the documented commands differ in more than `CCF_BINDING` — the claim"
        " is that only the binding changes, and these change"
        f" {sorted(remainders)}"
    )


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
