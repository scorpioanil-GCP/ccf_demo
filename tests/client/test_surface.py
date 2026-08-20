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

A second scan now lives here, over exactly one directory
--------------------------------------------------------
``C-17`` — **no module under** ``src/ccf/client/adapters/`` **constructs the
outcome shape**, because an adapter that can construct one can fill the echo
from the argument it was handed and the client's cross-check then compares an
object with itself. :func:`count_outcome_construction_sites` holds it, built to
the standard above and deliberately **not** sharing code with the ``Result``
scan, so a change to one cannot silently change the other.

It is one assertion over one directory, not a framework: ``C-13`` rejected a
general obligations gate, and the way a narrow gate becomes one is by widening
its scope until it needs an exemption list. It also does not replace ``C-05``'s
type change — it survives it, for the reason
:func:`count_outcome_construction_sites` records.
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

#: The one directory ``C-17`` scopes the outcome-construction gate to. One
#: directory, deliberately, and this constant is **not** ``SCANNED_ROOTS``:
#: ``ccf.products.door.door_answer`` constructs the outcome shape and is the
#: **one** place that should, so a wider scope would count the legitimate site
#: and force an exemption list — which is precisely how a narrow gate turns
#: into the general obligations gate ``C-13`` rejected.
ADAPTER_ROOTS: Final[tuple[pathlib.Path, ...]] = (
    _REPO_ROOT / "src" / "ccf" / "client" / "adapters",
)

#: The modules the outcome shape can be imported from, for resolving local
#: aliases. Two, because ``19-01`` merged the two outcome classes into one
#: defined in :mod:`ccf.products.door` and re-exported by
#: :mod:`ccf.client.wire`; an adapter can reach the same class through either.
_OUTCOME_MODULES: Final[frozenset[str]] = frozenset(
    {"ccf.client.wire", "ccf.products.door"}
)

#: Both spellings of that one class. ``WireOutcome`` is an alias of
#: ``DoorOutcome`` rather than a subclass, so these are two names for the same
#: object and a gate that watched only one would miss the other.
_OUTCOME_NAMES: Final[frozenset[str]] = frozenset({"WireOutcome", "DoorOutcome"})


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
# C-17 — no adapter constructs the outcome shape
# --------------------------------------------------------------------------


def _outcome_aliases(tree: ast.Module) -> set[str]:
    """Local names bound to the outcome shape in one module.

    Resolved from the import statements rather than assumed, and against
    **both** spellings: ``19-01`` merged the two outcome classes, so
    ``from ccf.products.door import DoorOutcome`` and
    ``from ccf.client.wire import WireOutcome as _W`` reach the same class.
    All of them count.
    """
    aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in _OUTCOME_MODULES:
            for alias in node.names:
                if alias.name in _OUTCOME_NAMES:
                    aliases.add(alias.asname or alias.name)
    return aliases


def _outcome_construction_sites(tree: ast.Module) -> int:
    """Count the calls in one module that build the outcome shape.

    Two shapes are counted, because :func:`_construction_sites` above counts
    two and a gate weaker than the pattern it claims to mirror is not a mirror:
    a call to a local name bound to the class by an import, and any attribute
    call spelled ``….WireOutcome(...)`` or ``….DoorOutcome(...)`` whatever it
    is an attribute of.

    The second is deliberately broader than it needs to be — it would also
    count an unrelated ``other.WireOutcome(...)`` — because over-counting fails
    the build and puts a human in front of the question, while under-counting
    is the silent direction. It is also the only rule that reaches
    ``import ccf.client.wire`` followed by ``ccf.client.wire.WireOutcome(...)``,
    which binds no local name to the class and so resolves nothing for alias
    matching to find. There is no such attribute call anywhere under
    ``src/ccf/client/adapters/`` today — four modules, zero hits, measured with
    a one-off AST run before this rule was written.

    The walk is :func:`ast.walk` over the whole module rather than over module
    scope, because a construction deferred into a function body is exactly
    where an adapter would put one — an adapter constructs inside ``ask``, not
    at import time. Measured: a module-scope-only walk counts zero for that
    shape, which is why the control below writes it.
    """
    found = 0
    aliases = _outcome_aliases(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if isinstance(function, ast.Name) and function.id in aliases:
            found += 1
        elif isinstance(function, ast.Attribute) and function.attr in _OUTCOME_NAMES:
            found += 1
    return found


def count_outcome_construction_sites(
    roots: Sequence[pathlib.Path],
) -> dict[str, int]:
    """Count outcome-shape constructions per module across ``roots``.

    ``C-17``. The property: **no adapter constructs the outcome.** An adapter
    that can construct one can fill ``request`` from the very argument it was
    handed, and the client's echo cross-check then compares an object with
    itself — which is ``D-IMPL-151`` finding ``B0``, the defect this phase
    exists to close. The door mints the shape
    (:func:`ccf.products.door.door_answer`); a transport carries bytes.

    Why this exists *beside* the type change rather than instead of it
    ------------------------------------------------------------------
    ``C-05`` retyped the seam to ``-> bytes`` and ``mypy --strict`` enforces
    it — but ``[tool.mypy] files`` is ``["src", "runtime"]``, so an
    **out-of-tree** adapter is invisible to it, and an in-tree adapter could
    construct the shape and then encode it, satisfying ``-> bytes`` without
    ever violating the return type. Both checks hold; neither replaces the
    other.

    Takes its roots as a parameter so a control can point it at a ``tmp_path``
    tree the function actually reads, rather than at a copy the function never
    looks at.

    **Every module read gets an entry, including the zeros.** That is what lets
    a caller distinguish *no adapter constructs one* from *nothing was read*,
    and :func:`assert_no_adapter_constructs_the_outcome` refuses the second.

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

    Not detectable, and named rather than pretended away
    ----------------------------------------------------
    Two shapes this walk cannot reach. They are stated because a gate whose
    docstring claims more than its walk holds is the defect this phase is
    named after:

    * a construction reached through ``getattr(module, "WireOutcome")(...)``.
      No dynamic dispatch of that shape exists in this directory, and the day
      one does the honest fix is a ruling rather than a cleverer walk.
    * **re-labelling**, which is not a construction at all: ``decode_outcome``
      followed by ``.model_copy(update={"request": …})`` and
      ``encode_outcome``. Nothing is constructed, so no construction counter
      can see it — and it is the shape most likely to re-open ``B0``. This is
      not hypothetical: this phase's own controls in ``19-03`` and ``19-04``
      are built with exactly that idiom, one directory over, so a docstring
      here claiming *"no adapter can produce a forged outcome"* would be
      falsified by this repo's own test code.

    What covers the second is not this gate. It is ``19-04``'s conformance
    obligation, which wraps every registered adapter in a byte-corrupting
    decorator and requires the client to raise — a leg an adapter author
    neither writes nor can opt out of.
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
                    " whether it constructs the outcome shape; a file that is"
                    f" skipped is a file that is not checked ({unparsable})"
                ) from unparsable
            try:
                key = path.relative_to(_REPO_ROOT).as_posix()
            except ValueError:
                key = path.as_posix()
            counts[key] = _outcome_construction_sites(tree)
    return counts


def assert_no_adapter_constructs_the_outcome(
    roots: Sequence[pathlib.Path],
) -> None:
    """Assert no module under ``roots`` constructs the outcome shape.

    ``C-17``.

    Raises:
        AssertionError: the walk read no modules at all, or some module
            constructs the shape. The first is checked first and separately,
            because a walk that reads nothing satisfies every ceiling placed
            over it — which is how a gate in this repo passed vacuously for a
            full wave.
    """
    counts = count_outcome_construction_sites(roots)
    if not counts:
        raise AssertionError(
            f"the scan read no modules under {[str(root) for root in roots]},"
            " so it proved nothing — a walk that reads nothing satisfies every"
            " ceiling placed over it"
        )
    constructing = sorted(
        (module, count) for module, count in counts.items() if count
    )
    if constructing:
        named = ", ".join(f"{module} ({count} site(s))" for module, count in constructing)
        raise AssertionError(
            f"no adapter may construct the outcome shape (C-17), and"
            f" {len(constructing)} module(s) do: {named}. An adapter that"
            " builds the answer can fill `request` from the argument it was"
            " handed, and the client's echo cross-check then compares an"
            " object with itself — D-IMPL-151 finding B0. The door mints the"
            " shape (`ccf.products.door.door_answer`); a transport carries"
            f" bytes. The scan read {len(counts)} modules"
        )


def test_no_adapter_constructs_the_outcome() -> None:
    assert_no_adapter_constructs_the_outcome(ADAPTER_ROOTS)


def test_the_outcome_scan_reads_every_adapter_module() -> None:
    """The walk is not vacuous, and the zeros are what make it countable.

    Named modules rather than a bare count, because this directory is small
    enough to name in full: if a root stops resolving or the suffix filter
    breaks, the mapping loses an entry and this goes red rather than reporting
    a healthy-looking zero over a tree it never read.
    """
    counts = count_outcome_construction_sites(ADAPTER_ROOTS)

    assert {
        "src/ccf/client/adapters/__init__.py",
        "src/ccf/client/adapters/binding_document.py",
        "src/ccf/client/adapters/inprocess.py",
        "src/ccf/client/adapters/mcp_stdio.py",
    } <= set(counts), (
        f"the scan read {sorted(counts)}, which is short of the adapters"
        " directory — a root probably stopped resolving"
    )
    assert set(counts.values()) == {0}


# --------------------------------------------------------------------------
# D-04 — the documented `as_of` rule, asserted where a reader would look
# --------------------------------------------------------------------------


def test_the_as_of_rule_is_documented_on_ask() -> None:
    """``D-04`` puts the rule on ``ask()``, not in a design document."""
    from ccf.client.client import ProductClient

    documentation = ProductClient.ask.__doc__ or ""
    assert "decision instant" in documentation
    assert "as_of" in documentation
