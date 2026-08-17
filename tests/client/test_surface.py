"""Two properties nobody can hold in their head, made into checks that fire.

``D-03`` — ``ccf.client`` exports exactly four names.
``D-12`` — ``Result`` is constructed in exactly one place.

Both are rulings, and a ruling nobody measures is a comment. ``make ci-core``
reads both on every run, so the day a fifth export or a second construction site
appears the corresponding test goes red in the same commit that introduced it.

Both assertions take their subject as a parameter, and that is the whole design
of this module
---------------------------------------------------------------------------
The defect class this avoids spans three plans of this phase: a control
specified as *"copy the module to* ``tmp_path``\\ *, break it, assert the test
fails"* against an assertion that reads an **imported module** or a **fixed set
of source roots**. The copy is never what the assertion looks at, so the control
passes for the wrong reason and the property stays unproven.

So :func:`assert_public_surface` takes a *module object* and
:func:`count_result_construction_sites` takes a *sequence of roots*. The shipped
tests hand them the real subjects; the controls hand the very same functions a
divergent one and watch them fail.

And the scan fails loudly on anything it cannot resolve
-------------------------------------------------------
The lesson is fresh and expensive: a citation gate in this repo passed
vacuously for a full wave because an ambiguous basename was **dropped from the
sweep rather than flagged**, which meant adding files to the tree made the gate
check less, silently. So :func:`count_result_construction_sites` raises on a
root that does not exist and on a file it cannot parse, reports a count for
every module it read including the zeros, and the shipped assertion refuses a
walk that read nothing at all.
"""

from __future__ import annotations

import ast
import importlib.util
import pathlib
import types
from collections.abc import Sequence
from typing import Final

import pytest

import ccf.client

_REPO_ROOT: Final = pathlib.Path(__file__).resolve().parents[2]

#: The four names ``D-03`` fixes the package's public surface at.
EXPECTED_SURFACE: Final[frozenset[str]] = frozenset(
    {"ProductClient", "Result", "TransportError", "BindingError"}
)

#: The trees a shipped ``Result`` construction could hide in. ``tests/`` is
#: deliberately absent: a test constructing a ``Result`` directly is building a
#: subject, not serving one, and ``D-12`` is a statement about the code path an
#: answer travels.
SCANNED_ROOTS: Final[tuple[pathlib.Path, ...]] = (
    _REPO_ROOT / "src",
    _REPO_ROOT / "runtime",
    _REPO_ROOT / "examples",
)

#: The modules a ``Result`` can be imported from, for resolving local aliases.
_RESULT_MODULES: Final[frozenset[str]] = frozenset(
    {"ccf.client", "ccf.client.result"}
)


# --------------------------------------------------------------------------
# D-03 — the assertion, over a module object
# --------------------------------------------------------------------------


def assert_public_surface(module: types.ModuleType) -> None:
    """Assert ``module`` exports exactly the four ruled names.

    Takes a module **object**, not a path and not a name, because the property
    is about what an importer sees. A control that edited a copied file on disk
    would change nothing this function can read — which is exactly why the
    control below constructs a divergent module object instead.

    Args:
        module: The subject. The shipped test passes the imported
            ``ccf.client``; the controls pass deliberately divergent ones.

    Raises:
        AssertionError: the exported set is not the four ruled names, or a name
            it claims to export does not resolve on the module. The second is
            not pedantry: an ``__all__`` entry with nothing behind it is a
            surface that exists in the manifest and fails at the import a reader
            copies out of the README.
    """
    exported = getattr(module, "__all__", None)
    if exported is None:
        raise AssertionError(
            f"{module.__name__} declares no `__all__`, so it has no public"
            " surface to be exactly four names"
        )
    actual = set(exported)
    if actual != set(EXPECTED_SURFACE):
        missing = sorted(set(EXPECTED_SURFACE) - actual)
        extra = sorted(actual - set(EXPECTED_SURFACE))
        raise AssertionError(
            f"{module.__name__} must export exactly the four ruled names"
            f" {sorted(EXPECTED_SURFACE)} — missing {missing}, unexpected"
            f" {extra}. D-03 fixes the count, because it is the measurable form"
            " of the producer side staying invisible to the client"
        )
    unresolved = [name for name in actual if not hasattr(module, name)]
    if unresolved:
        raise AssertionError(
            f"{module.__name__} exports {sorted(unresolved)} in `__all__` with"
            " nothing bound behind them"
        )


def test_the_client_package_exports_exactly_four_names() -> None:
    assert_public_surface(ccf.client)


def test_the_four_names_are_the_ruled_ones() -> None:
    """Stated once by equality too, so the failure names them without a walk."""
    assert sorted(ccf.client.__all__) == [
        "BindingError",
        "ProductClient",
        "Result",
        "TransportError",
    ]


def test_no_wire_or_control_plane_type_reaches_the_package_surface() -> None:
    """``D-02``/``D-03`` in the direction a reader would violate it by accident."""
    forbidden = {
        "WireRequest",
        "WireOutcome",
        "TransportAdapter",
        "Refusal",
        "RefusalEnvelope",
        "RefusedResultError",
        "ContextProductContract",
    }
    assert not forbidden & set(ccf.client.__all__)


# --------------------------------------------------------------------------
# D-03 — the controls, each passing a divergent module into the same function
# --------------------------------------------------------------------------


def _module_with(names: Sequence[str], *, called: str = "fake.client") -> types.ModuleType:
    """A module object whose ``__all__`` is ``names`` and which binds each one."""
    module = types.ModuleType(called)
    module.__all__ = list(names)  # type: ignore[attr-defined]
    for name in names:
        setattr(module, name, object())
    return module


def test_control_the_surface_assertion_fires_on_a_fifth_name() -> None:
    """CONTROL 1 — the divergent subject is a module object, not a copied file.

    Stated explicitly because the naive form is the one this phase kept
    shipping: :func:`assert_public_surface` reads ``__all__`` on the *imported*
    package, so appending a name to a copy of ``__init__.py`` on disk changes
    nothing the assertion can see, and the control passes while proving
    nothing. Handing it a module object with a fifth name is a subject the
    assertion actually reads.
    """
    divergent = _module_with([*sorted(EXPECTED_SURFACE), "DeploymentManifest"])

    with pytest.raises(AssertionError) as raised:
        assert_public_surface(divergent)

    assert "DeploymentManifest" in str(raised.value)


def test_control_the_surface_assertion_fires_on_a_missing_name() -> None:
    """CONTROL 2 — the other direction; a shrunk surface is drift too."""
    divergent = _module_with(sorted(EXPECTED_SURFACE - {"BindingError"}))

    with pytest.raises(AssertionError, match="BindingError"):
        assert_public_surface(divergent)


def test_control_the_surface_assertion_fires_on_an_unbound_export() -> None:
    """CONTROL 3 — a name in ``__all__`` with nothing behind it is caught."""
    divergent = types.ModuleType("fake.client")
    divergent.__all__ = sorted(EXPECTED_SURFACE)  # type: ignore[attr-defined]

    with pytest.raises(AssertionError, match="nothing bound behind"):
        assert_public_surface(divergent)


def test_control_the_surface_assertion_fires_on_a_module_with_no_all(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 4 — the unresolvable case: a real module declaring no surface.

    Loaded through ``importlib.util.spec_from_file_location`` so the subject is
    a genuinely imported module rather than a hand-built stand-in, which is the
    second construction the plan names. A module with no ``__all__`` must fail
    loudly; returning an empty set and comparing it would have been the quiet
    answer, and quiet is how a gate stops finding things.
    """
    source = tmp_path / "surfaceless.py"
    source.write_text("PRODUCT_CLIENT = 1\n", encoding="utf-8")
    spec = importlib.util.spec_from_file_location("surfaceless", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    with pytest.raises(AssertionError, match="declares no `__all__`"):
        assert_public_surface(module)


# --------------------------------------------------------------------------
# D-12 — the scan, over an explicit sequence of roots
# --------------------------------------------------------------------------


def _result_aliases(tree: ast.Module) -> set[str]:
    """Local names bound to the ``Result`` class in one module.

    Resolved from the import statements rather than assumed, so
    ``from ccf.client.result import Result as R`` followed by ``R(...)`` is
    still a construction site. A ``grep`` for ``Result(`` would miss it, which
    is why this is an AST walk.
    """
    aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in _RESULT_MODULES:
            for alias in node.names:
                if alias.name == "Result":
                    aliases.add(alias.asname or alias.name)
    return aliases


def _construction_sites(tree: ast.Module) -> int:
    """Count the calls in one module that build a ``Result``.

    Two shapes are counted: a call to a local name bound to the class by an
    import, and any attribute call spelled ``….Result(...)``. The second is
    deliberately broader than it needs to be — it would also count an unrelated
    ``other.Result(...)`` — because over-counting fails the build and puts a
    human in front of the question, while under-counting is the silent
    direction. There is no such attribute call anywhere in the scanned trees
    today, which was measured before the rule was written.

    Not detectable, and named rather than pretended away: a construction
    reached through ``getattr(module, "Result")(...)``. No dynamic dispatch of
    that shape exists in these trees, and the day one does, the honest fix is a
    ruling rather than a cleverer walk.
    """
    found = 0
    aliases = _result_aliases(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if isinstance(function, ast.Name) and function.id in aliases:
            found += 1
        elif isinstance(function, ast.Attribute) and function.attr == "Result":
            found += 1
    return found


def count_result_construction_sites(
    roots: Sequence[pathlib.Path],
) -> dict[str, int]:
    """Count ``Result`` constructions per module across ``roots``.

    Takes its roots as a parameter so a control can point it at a ``tmp_path``
    tree the function actually reads, rather than at a copy the function never
    looks at.

    **Every module read gets an entry, including the zeros.** That is what lets
    a caller distinguish *nothing constructs a* ``Result`` from *nothing was
    read*, and the shipped assertion refuses the second.

    Args:
        roots: Directories to walk. Each must exist.

    Returns:
        Repo-relative module path to the number of construction sites in it.

    Raises:
        AssertionError: a root does not exist, or a file under one cannot be
            parsed. Both are refused rather than skipped: a sweep that drops
            what it cannot resolve reports less as the tree grows, which is the
            exact shape that let a citation gate in this repo pass vacuously
            for a full wave.
    """
    counts: dict[str, int] = {}
    for root in roots:
        if not root.is_dir():
            raise AssertionError(
                f"{root} is not a directory, so scanning it would silently"
                " contribute nothing and the total would look healthy"
            )
        for path in sorted(root.rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source, filename=str(path))
            except SyntaxError as unparsable:
                raise AssertionError(
                    f"{path} could not be parsed, so the scan cannot say"
                    " whether it constructs a `Result`; a file that is skipped"
                    f" is a file that is not checked ({unparsable})"
                ) from unparsable
            try:
                key = path.relative_to(_REPO_ROOT).as_posix()
            except ValueError:
                key = path.as_posix()
            counts[key] = _construction_sites(tree)
    return counts


def assert_one_result_construction_site(roots: Sequence[pathlib.Path]) -> None:
    """Assert exactly one module under ``roots`` constructs a ``Result``.

    ``D-12``. Shape identity across transports is only a code path an adapter
    cannot avoid while there is one path.

    Raises:
        AssertionError: the walk read no modules at all, or the number of
            constructing modules is not one. The first case is checked first
            and separately, because a walk that finds nothing satisfies "not
            more than one" and would otherwise pass forever.
    """
    counts = count_result_construction_sites(roots)
    if not counts:
        raise AssertionError(
            f"the scan read no modules under {[str(root) for root in roots]},"
            " so it proved nothing — a walk that reads nothing satisfies every"
            " ceiling placed over it"
        )
    constructing = sorted(module for module, count in counts.items() if count)
    if len(constructing) != 1:
        raise AssertionError(
            f"`Result` must be constructed in exactly one module (D-12) and"
            f" {len(constructing)} do: {constructing}. Adapters never build a"
            " `Result`; one decoder inside `ProductClient` does, which is what"
            " makes every transport return the same shape a code path rather"
            f" than a convention. The scan read {len(counts)} modules"
        )


def test_result_is_constructed_in_exactly_one_place() -> None:
    assert_one_result_construction_site(SCANNED_ROOTS)


def test_the_one_construction_site_is_the_client_decoder() -> None:
    """Not merely *one* site — the right one."""
    counts = count_result_construction_sites(SCANNED_ROOTS)
    constructing = {module for module, count in counts.items() if count}
    assert constructing == {"src/ccf/client/client.py"}


def test_the_construction_scan_reads_the_whole_shipped_tree() -> None:
    """The walk is not vacuous, and the floor is high enough to notice a break.

    A floor rather than an exact count, because the number of modules moves
    with every plan; a floor near the current population still fails loudly if
    a root stops resolving or the suffix filter breaks.
    """
    counts = count_result_construction_sites(SCANNED_ROOTS)
    assert len(counts) > 200, (
        f"the scan read {len(counts)} modules, which is far short of the"
        " shipped tree — a root probably stopped resolving"
    )


# --------------------------------------------------------------------------
# D-12 — the controls, each passing a divergent root into the same function
# --------------------------------------------------------------------------


def _write_module(root: pathlib.Path, name: str, body: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(body, encoding="utf-8")


def test_control_the_one_site_assertion_fires_on_two_sites(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 5 — two constructing modules, named in the failure.

    The subject is a ``tmp_path`` root passed **into the shipped assertion**,
    so the control exercises the function the build runs rather than a copy of
    its logic.
    """
    _write_module(
        tmp_path,
        "decoder.py",
        "from ccf.client.result import Result\n"
        "def build():\n"
        "    return Result(product_id='x')\n",
    )
    _write_module(
        tmp_path,
        "rogue_adapter.py",
        "from ccf.client.result import Result\n"
        "def build():\n"
        "    return Result(product_id='y')\n",
    )

    with pytest.raises(AssertionError) as raised:
        assert_one_result_construction_site([tmp_path])

    message = str(raised.value)
    assert "decoder.py" in message and "rogue_adapter.py" in message


def test_control_the_one_site_assertion_fires_on_zero_sites(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 6 — a tree where nothing constructs a ``Result`` is not one site."""
    _write_module(tmp_path, "innocent.py", "X = 1\n")

    with pytest.raises(AssertionError, match="exactly one module"):
        assert_one_result_construction_site([tmp_path])


def test_control_the_assertion_refuses_a_walk_that_read_nothing(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 7 — the vacuous walk, which is the failure mode that hides.

    An empty directory yields no counts. Without the explicit check, the
    "exactly one" comparison would see zero constructing modules out of zero
    read and be satisfied by a scan that looked at nothing.
    """
    empty = tmp_path / "nothing-here"
    empty.mkdir()

    with pytest.raises(AssertionError, match="read no modules"):
        assert_one_result_construction_site([empty])


def test_control_the_scan_refuses_a_root_it_cannot_resolve(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 8 — the unresolvable root fails loudly rather than contributing nothing.

    This is the shape of the defect that ran for a full wave of this phase: a
    sweep that skips what it cannot resolve reports green while checking less.
    """
    with pytest.raises(AssertionError, match="is not a directory"):
        count_result_construction_sites([tmp_path / "there-is-no-such-tree"])


def test_control_the_scan_refuses_a_file_it_cannot_parse(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 9 — an unparsable module is flagged, never skipped.

    A file the walker cannot read is the ambiguous case for an AST scan, and
    skipping it means a single syntax error hides every construction site in
    that module from the gate.
    """
    _write_module(tmp_path, "broken.py", "def (:\n")

    with pytest.raises(AssertionError, match="could not be parsed"):
        count_result_construction_sites([tmp_path])


def test_control_the_scan_counts_an_aliased_import(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 10 — the shape a ``grep`` would miss.

    ``from ccf.client.result import Result as R`` followed by ``R(...)`` never
    spells ``Result(``. A scan defeated by a two-character rename is a scan
    that stops working the first time anybody is clever.
    """
    _write_module(
        tmp_path,
        "aliased.py",
        "from ccf.client.result import Result as R\n"
        "def build():\n"
        "    return R(product_id='x')\n",
    )

    assert count_result_construction_sites([tmp_path]) == {
        (tmp_path / "aliased.py").as_posix(): 1
    }


def test_control_the_scan_counts_an_attribute_call(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 11 — the module-qualified shape, which binds no local name."""
    _write_module(
        tmp_path,
        "qualified.py",
        "import ccf.client.result as r\n"
        "def build():\n"
        "    return r.Result(product_id='x')\n",
    )

    assert count_result_construction_sites([tmp_path]) == {
        (tmp_path / "qualified.py").as_posix(): 1
    }


def test_control_the_scan_records_a_zero_for_a_module_that_builds_nothing(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 12 — the zeros are present, which is what makes the walk countable.

    If non-constructing modules were omitted, ``len(counts)`` would report the
    number of *sites* rather than the number of *modules read*, and the
    not-vacuous check above would become a restatement of the one-site check.
    """
    _write_module(tmp_path, "innocent.py", "X = 1\n")

    counts = count_result_construction_sites([tmp_path])
    assert counts == {(tmp_path / "innocent.py").as_posix(): 0}


# --------------------------------------------------------------------------
# D-04 — the documented `as_of` rule, asserted where a reader would look
# --------------------------------------------------------------------------


def test_the_as_of_rule_is_documented_on_ask() -> None:
    """``D-04`` puts the rule on ``ask()``, not in a design document."""
    from ccf.client.client import ProductClient

    documentation = ProductClient.ask.__doc__ or ""
    assert "decision instant" in documentation
    assert "as_of" in documentation
