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

Amendment, 2026-08-20 — the outcome scan could not fail, and two claims above
are now narrower than they were
-------------------------------------------------------------------------
The paragraph above says the outcome scan is *"built to the standard above"*.
It was not. The close review of this phase built an adapter that constructs the
outcome with ``WireOutcome.model_validate({...})`` — the shipped idiom of
:func:`ccf.client.codec.decode_outcome`, one module over — echoes the question
it was handed, and answers a **different** one. The gate scored it **zero**,
``mypy --strict`` passed, both conformance tamper legs passed, and
:meth:`ccf.client.client.ProductClient.ask` handed the caller the other
question's vessel with nothing raised. ``D-IMPL-151`` finding ``B0``, re-opened
in-tree with the whole build green. Two more spellings scored zero the same
way: a relative ``from ..wire import WireOutcome`` — the idiomatic spelling for
a directory that sits one package below :mod:`ccf.client.wire` — and
``class Forged(WireOutcome)``.

So the walk now counts five shapes rather than two, and the two claims that
have to shrink are recorded here rather than quietly rewritten:

* *"deliberately not sharing code with the* ``Result`` *scan"* — still true of
  everything that decides what counts, and no longer true of import
  resolution. :func:`_import_reaches` and :func:`_with_subclasses` are shared,
  for the reason :func:`_import_reaches` states.
* the ``Result`` scan had the same relative-import hole against a Dave ruling
  (``D-12``), so it is closed in the same pass.

Every one of the new shapes was **watched failing** before it was shipped: each
has a control that hands the shipped walk a forging module and asserts the
count, and each new rule has a deliberately weakened twin asserting the rule is
*necessary* — the pattern ``CONTROL 18`` and ``CONTROL 19`` already set here.
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
from ccf.products.gates import PYDANTIC_MODEL_FORMS

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

#: The dotted package that directory is imported as. Named once, because the
#: controls that hand :func:`_outcome_construction_sites` a parsed tree rather
#: than a path have to state the position the module is being read *from* —
#: relative imports have no meaning without it.
_ADAPTER_PACKAGE: Final[str] = "ccf.client.adapters"

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

#: The pydantic spellings that **serialize** a model rather than hand one back.
#: Enumerated as a *subtraction* from the shipped
#: :data:`~ccf.products.gates.PYDANTIC_MODEL_FORMS` rather than as a positive
#: list, and the direction is the whole point: a spelling added upstream is
#: counted by this gate on the day it lands, because the default membership is
#: "constructs". A hand-written positive list would have to be remembered in
#: two places, and the second list is the one that drifts — which is how this
#: gate came to miss every pydantic spelling in the first place.
_SERIALIZING_FORMS: Final[frozenset[str]] = frozenset(
    {"model_dump", "model_dump_json", "model_json_schema"}
)

#: Every pydantic spelling that returns an instance of the class it is reached
#: through. ``WireOutcome(...)`` is not the only way to build one:
#: ``WireOutcome.model_validate({...})`` is the shipped idiom of this very seam
#: — :func:`ccf.client.codec.decode_outcome` builds the outcome with
#: ``model_validate_json`` — and an adapter author copying that one line out of
#: the module this gate protects defeated the gate completely. That was
#: measured end to end against ``2119ca6`` with the whole build green: zero
#: construction sites, both conformance tamper legs passing, ``mypy --strict``
#: satisfied, and a caller handed another question's vessel with nothing
#: raised. ``D-IMPL-151`` finding ``B0``, re-opened in-tree.
_CONSTRUCTING_FORMS: Final[frozenset[str]] = PYDANTIC_MODEL_FORMS - _SERIALIZING_FORMS

#: The last dotted component of each watched module, for the one case
#: :func:`_resolve_relative` cannot name. See :func:`_import_reaches`.
_OUTCOME_MODULE_TAILS: Final[frozenset[str]] = frozenset(
    module.rsplit(".", 1)[-1] for module in _OUTCOME_MODULES
)
_RESULT_MODULE_TAILS: Final[frozenset[str]] = frozenset(
    module.rsplit(".", 1)[-1] for module in _RESULT_MODULES
)


# --------------------------------------------------------------------------
# Import resolution — shared by both scans, and the *only* thing that is
# --------------------------------------------------------------------------


def _package_of(path: pathlib.Path) -> str:
    """The dotted package a module at ``path`` is imported as part of.

    Read off the filesystem the way the import system reads it — walk up while
    there is an ``__init__.py`` — rather than assumed from a path prefix, so a
    control that writes a package into ``tmp_path`` is resolved by the very
    same rule as ``src/ccf/client/adapters/inprocess.py``.

    Returns the empty string for a module that is in no package at all, which
    is the honest answer for the 35 such modules under ``examples/``.
    """
    parts: list[str] = []
    directory = path.parent
    while (directory / "__init__.py").is_file():
        parts.append(directory.name)
        directory = directory.parent
    return ".".join(reversed(parts))


def _resolve_relative(package: str, level: int, module: str | None) -> str | None:
    """The absolute name a relative ``from … import …`` reaches, if nameable.

    ``None`` when the importing module is in no package, or when the dots
    reach above the package chain the filesystem can show. Neither is an error
    here — both are the caller's cue to fall back to the tail, which
    :func:`_import_reaches` does and documents.
    """
    if not package:
        return None
    parts = package.split(".")
    if level - 1 > len(parts):
        return None
    base = parts[: len(parts) - (level - 1)]
    if not base:
        return None
    return ".".join([*base, module]) if module else ".".join(base)


def _import_reaches(
    node: ast.ImportFrom,
    *,
    package: str,
    modules: frozenset[str],
    tails: frozenset[str],
) -> bool:
    """Does this ``from … import …`` reach one of ``modules``?

    This function is the one piece of machinery the two scans share, and the
    sharing is deliberate against the header's own rule. Relative resolution
    is subtle enough that writing it twice is two chances to write it wrongly,
    and it is not gate *policy* — it answers "which module is this import
    talking about", a question with one right answer. What stays separate is
    everything that decides what counts: the two alias sets, the two site
    walks, the two ceilings.

    Absolute imports match on the dotted name, as they always did. Relative
    ones are **resolved against the importing module's own package** first,
    which is what was missing: adapters live at ``src/ccf/client/adapters/``,
    one package below :mod:`ccf.client.wire`, so ``from ..wire import
    WireOutcome`` is the idiomatic spelling, nothing in this repo bans it, and
    this gate scored it **zero** until this function existed (close-review
    finding ``CR-02``, measured).

    When the dots cannot be resolved — a module in no package, reached by
    ``sys.path`` rather than by import — the **tail** is matched instead. That
    over-counts: ``from ..wire import WireOutcome`` inside some unrelated
    ``wire`` package would be counted here. Over-counting fails the build and
    puts a human in front of the question; scoring zero is the silent
    direction, and silence is the thing this phase exists to end. It is the
    same trade the attribute rule below already makes.
    """
    if node.level == 0:
        return node.module in modules
    resolved = _resolve_relative(package, node.level, node.module)
    if resolved is not None:
        return resolved in modules
    return (node.module or "").rsplit(".", 1)[-1] in tails


def _with_subclasses(
    tree: ast.Module, aliases: set[str], *, names: frozenset[str]
) -> set[str]:
    """``aliases`` plus every local name that subclasses one of them.

    A fixed point rather than a single pass, so ``class A(WireOutcome)``
    followed by ``class B(A)`` is reached: a subclass of a subclass builds the
    same shape, and a gate that stopped at depth one would be defeated by a
    second ``class`` line.

    ``names`` is matched against attribute-spelled bases —
    ``class Forged(ccf.client.wire.WireOutcome)`` binds no local name to the
    class and so resolves nothing for the alias set to have found.
    """
    known = set(aliases)
    while True:
        added = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef) or node.name in known:
                continue
            for base in node.bases:
                if (isinstance(base, ast.Name) and base.id in known) or (
                    isinstance(base, ast.Attribute) and base.attr in names
                ):
                    known.add(node.name)
                    added = True
                    break
        if not added:
            return known


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


def _result_aliases(tree: ast.Module, *, package: str) -> set[str]:
    """Local names bound to the ``Result`` class in one module.

    Resolved from the import statements rather than assumed, so
    ``from ccf.client.result import Result as R`` followed by ``R(...)`` is
    still a construction site. A ``grep`` for ``Result(`` would miss it, which
    is why this is an AST walk.

    **Relative imports resolve too**, against ``package``: ``from .result
    import Result`` reaches the very same class as the absolute spelling and
    scored zero here until the close review of this phase measured it
    (``CR-02``). A second construction site added that way would have left
    ``D-12`` — a Dave ruling — green.

    **A subclass counts as the class.** ``class Forged(Result)`` followed by
    ``Forged(...)`` builds the shape, and ``D-12`` is a statement about how
    many places build the shape.
    """
    aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and _import_reaches(
            node,
            package=package,
            modules=_RESULT_MODULES,
            tails=_RESULT_MODULE_TAILS,
        ):
            for alias in node.names:
                if alias.name == "Result":
                    aliases.add(alias.asname or alias.name)
    return _with_subclasses(tree, aliases, names=frozenset({"Result"}))


def _construction_sites(tree: ast.Module, *, package: str) -> int:
    """Count the calls in one module that build a ``Result``.

    Two shapes are counted: a call to a local name bound to the class — by an
    absolute import, by a relative import, or by subclassing, all three
    resolved in :func:`_result_aliases` — and any attribute call spelled
    ``….Result(...)``. The second is deliberately broader than it needs to be
    — it would also count an unrelated ``other.Result(...)`` — because
    over-counting fails the build and puts a human in front of the question,
    while under-counting is the silent direction. There is no such attribute
    call anywhere in the scanned trees today, which was measured before the
    rule was written.

    Not detectable, and named rather than pretended away
    ----------------------------------------------------
    * a construction reached through ``getattr(module, "Result")(...)``. No
      dynamic dispatch of that shape exists in these trees, and the day one
      does, the honest fix is a ruling rather than a cleverer walk.
    * the pydantic construction spellings the outcome walk below counts are
      **not** counted here, and deliberately: ``Result`` is a plain class, not
      a pydantic model, so ``Result.model_validate(...)`` is an
      ``AttributeError`` rather than a construction. A rule for it would be a
      rule that can never fire, which is the thing this phase is named after.
      If ``Result`` ever becomes a model, this line is the one that has to
      change.
    """
    found = 0
    aliases = _result_aliases(tree, package=package)
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
            counts[key] = _construction_sites(tree, package=_package_of(path))
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


def _write_result_package(root: pathlib.Path, name: str, body: str) -> pathlib.Path:
    """Materialize a module at ``ccf/client/`` depth, where a ``Result`` lives.

    The relative controls below need a real package position, because a
    relative import means nothing without one. Nothing here edits ``src/``.
    """
    directory = root / "ccf" / "client"
    directory.mkdir(parents=True, exist_ok=True)
    for package_directory in (root / "ccf", directory):
        (package_directory / "__init__.py").write_text("", encoding="utf-8")
    path = directory / name
    path.write_text(body, encoding="utf-8")
    return path


def test_control_the_result_scan_counts_a_relative_import(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 12a — ``from .result import Result`` is the same class.

    ``D-12`` is a Dave ruling, and until 19's close review a second module
    could have constructed a ``Result`` through the relative spelling with this
    gate green (``CR-02``). The subject sits at ``ccf/client/`` depth so
    :func:`_package_of` resolves the dot exactly as it does in the shipped
    tree.
    """
    written = _write_result_package(
        tmp_path,
        "second_site.py",
        "from .result import Result\n"
        "def build():\n"
        "    return Result(product_id='x')\n",
    )

    counts = count_result_construction_sites([tmp_path])

    assert counts[written.as_posix()] == 1, (
        "the relative spelling reaches `ccf.client.result`; a second"
        " construction site written that way would leave D-12 green"
    )


def test_control_the_result_scan_counts_a_subclass(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 12b — a subclass builds the shape, so it is a construction site."""
    _write_module(
        tmp_path,
        "subclassed.py",
        "from ccf.client.result import Result\n"
        "class Forged(Result):\n"
        "    pass\n"
        "def build():\n"
        "    return Forged(product_id='x')\n",
    )

    assert count_result_construction_sites([tmp_path]) == {
        (tmp_path / "subclassed.py").as_posix(): 1
    }


def test_control_the_result_scan_does_not_count_a_neighbouring_relative_import(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 12c — the vacuity guard for the rule above.

    ``from .errors import TransportError`` is a relative import that reaches
    nothing this gate watches. Without this, a resolver that counted every
    relative import would pass CONTROL 12a and prove nothing.
    """
    written = _write_result_package(
        tmp_path,
        "innocent.py",
        "from .errors import TransportError\n"
        "def build():\n"
        "    raise TransportError('no')\n",
    )

    assert count_result_construction_sites([tmp_path])[written.as_posix()] == 0


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


def _outcome_aliases(tree: ast.Module, *, package: str) -> set[str]:
    """Local names bound to the outcome shape in one module.

    Resolved from the import statements rather than assumed, and against
    **both** spellings: ``19-01`` merged the two outcome classes, so
    ``from ccf.products.door import DoorOutcome`` and
    ``from ccf.client.wire import WireOutcome as _W`` reach the same class.
    All of them count.

    **Relative imports resolve too**, against ``package``. This directory sits
    one package below :mod:`ccf.client.wire`, so ``from ..wire import
    WireOutcome`` is the shortest honest spelling an adapter author would
    reach for, nothing in this repo bans it, and it scored **zero** until the
    close review of this phase measured it (``CR-02``).

    **A subclass counts as the class.** ``class Forged(WireOutcome)`` followed
    by ``Forged(request=…)`` constructs the outcome shape by every meaning
    ``C-17`` has; it scored zero too, for the same measured reason.
    """
    aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and _import_reaches(
            node,
            package=package,
            modules=_OUTCOME_MODULES,
            tails=_OUTCOME_MODULE_TAILS,
        ):
            for alias in node.names:
                if alias.name in _OUTCOME_NAMES:
                    aliases.add(alias.asname or alias.name)
    return _with_subclasses(tree, aliases, names=_OUTCOME_NAMES)


def _receiver_is_the_outcome(value: ast.expr, aliases: set[str]) -> bool:
    """Is ``value`` — the thing left of the dot — the outcome class itself?

    Two spellings, matching the two the call walk already knows: a local name
    the imports bound to the class (or to a subclass of it), and an
    attribute-qualified ``ccf.client.wire.WireOutcome`` that binds no local
    name at all.

    Deliberately **not** true of an arbitrary expression. ``decoded.model_copy(
    update=…)`` — an instance, not the class — is the re-labelling shape, and
    it stays outside this gate rather than being swept in by a looser receiver
    rule that would also count every honest ``request.model_copy(...)``. See
    :func:`count_outcome_construction_sites` for what does and does not cover
    it, stated as a measurement.
    """
    return (isinstance(value, ast.Name) and value.id in aliases) or (
        isinstance(value, ast.Attribute) and value.attr in _OUTCOME_NAMES
    )


def _outcome_construction_sites(tree: ast.Module, *, package: str) -> int:
    """Count the calls in one module that build the outcome shape.

    Three call shapes are counted, over an alias set that resolves five
    spellings (absolute import, relative import, ``as`` alias, subclass,
    subclass of a subclass — :func:`_outcome_aliases`):

    1. a call to a local name in that alias set;
    2. any attribute call spelled ``….WireOutcome(...)`` or
       ``….DoorOutcome(...)`` whatever it is an attribute of;
    3. a **pydantic construction spelling** reached through either of those —
       ``WireOutcome.model_validate({...})``,
       ``ccf.products.door.DoorOutcome.model_construct(...)``, and every other
       member of :data:`_CONSTRUCTING_FORMS`.

    Rule 3 is the one this gate shipped without, and its absence was not
    theoretical: ``WireOutcome.model_validate`` is one character away from the
    idiom in :mod:`ccf.client.codec`, and an adapter spelling it that way
    forged an answer past every check in the build. The spellings are taken
    from :data:`~ccf.products.gates.PYDANTIC_MODEL_FORMS` — the enumeration the
    repo already ships and already calls *"the machine-readable statement of
    what this type is not"* — minus the three that serialize, so a spelling
    added there is counted here without anyone remembering to.

    Rule 2 is deliberately broader than it needs to be — it would also count an
    unrelated ``other.WireOutcome(...)`` — because over-counting fails the
    build and puts a human in front of the question, while under-counting is
    the silent direction. It is also the only rule that reaches
    ``import ccf.client.wire`` followed by ``ccf.client.wire.WireOutcome(...)``,
    which binds no local name to the class and so resolves nothing for alias
    matching to find. There is no attribute call and no pydantic-form call
    anywhere under ``src/ccf/client/adapters/`` today — four modules, zero
    hits, measured with a one-off AST run before each rule was written.

    The walk is :func:`ast.walk` over the whole module rather than over module
    scope, because a construction deferred into a function body is exactly
    where an adapter would put one — an adapter constructs inside ``ask``, not
    at import time. Measured: a module-scope-only walk counts zero for that
    shape, which is why the control below writes it.
    """
    found = 0
    aliases = _outcome_aliases(tree, package=package)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if isinstance(function, ast.Name) and function.id in aliases:
            found += 1
        elif isinstance(function, ast.Attribute):
            if function.attr in _OUTCOME_NAMES:
                found += 1
            elif function.attr in _CONSTRUCTING_FORMS and _receiver_is_the_outcome(
                function.value, aliases
            ):
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
    named after — and this list was itself short by two until the close review
    measured them, which is why the two it missed now appear above as rules
    rather than here as excuses:

    * a construction reached through ``getattr(module, "WireOutcome")(...)``.
      No dynamic dispatch of that shape exists in this directory, and the day
      one does the honest fix is a ruling rather than a cleverer walk.
    * **instance-spelled re-labelling**, which is not a construction at all:
      ``decode_outcome(raw)`` followed by ``.model_copy(update={"request":
      …})`` and ``encode_outcome``. The receiver there is a *value*, not the
      class, so :func:`_receiver_is_the_outcome` is false and no construction
      counter can see it — and it is the shape most likely to re-open ``B0``.
      This is not hypothetical: this phase's own controls in ``19-03`` and
      ``19-04`` are built with exactly that idiom, one directory over, so a
      docstring here claiming *"no adapter can produce a forged outcome"*
      would be falsified by this repo's own test code. The **class**-spelled
      half of the same idiom — ``WireOutcome.model_copy(...)`` — *is* counted,
      because ``model_copy`` is a member of :data:`_CONSTRUCTING_FORMS`; the
      gap is the receiver, not the spelling.

    What covers the second, measured rather than assumed
    -----------------------------------------------------
    Until 2026-08-20 this docstring said the second shape was covered by
    ``19-04``'s conformance obligation, *"a leg an adapter author neither
    writes nor can opt out of."* That was false, and it is recorded here
    rather than deleted because it is what this module claimed for a wave.

    ``19-04``'s tamper legs wrap the subject's adapter in a byte-corrupting
    decorator and require the **client** to raise. They prove the client's
    integrity checks are live on every registered adapter. They do not, and
    structurally cannot, prove an adapter is *honest*: a forging adapter's
    bytes are self-consistent, so a corrupted copy of them still makes the
    client raise and the leg still passes. Both legs were run against a fully
    forging adapter and both passed (close-review finding ``WR-01``).

    Nothing in this repo covers instance-spelled re-labelling today. The shape
    a real control would take is a conformance leg that asks question *A*
    through the subject and asserts the served ``content_address`` equals the
    address the **door** produced for *A* when driven directly — an operand
    the adapter never supplied. Building it is a ruling, not a refactor, and
    it is recorded as an open item rather than implied by a sentence here.
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
            counts[key] = _outcome_construction_sites(
                tree, package=_package_of(path)
            )
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
# C-17 — the controls, each passing a divergent adapter into the same function
# --------------------------------------------------------------------------


def _write_adapter(root: pathlib.Path, name: str, body: str) -> pathlib.Path:
    """Materialize one adapter module into ``root`` and return its path.

    These controls write **files**, where :func:`assert_public_surface`'s
    controls build a **module object**, and the difference is not stylistic.
    That assertion reads ``__all__`` off an imported module, so a file on disk
    is not a subject it can see; this one reads files, so a module object is
    not a subject it can see. Each control hands the shipped function the kind
    of divergent subject that function actually reads — which is the whole
    design this module's header states.

    Nothing here edits ``src/``.
    """
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    path.write_text(body, encoding="utf-8")
    return path


#: The construction a forging adapter would write, in five spellings. Every
#: one of them reaches the same class, so a gate that caught only some of them
#: would be a gate an adapter author defeats by changing an import line.
_FORGES_BY_NAME: Final = (
    "from ccf.client.wire import WireOutcome\n"
    "def ask(request):\n"
    "    return WireOutcome(request=request, product_json='{}',\n"
    "                       content_address='a', replay_ref=None,\n"
    "                       refusal=None)\n"
)
_FORGES_FROM_THE_DOOR_MODULE: Final = (
    "from ccf.products.door import DoorOutcome\n"
    "def ask(request):\n"
    "    return DoorOutcome(request=request, product_json='{}',\n"
    "                       content_address='a', replay_ref=None,\n"
    "                       refusal=None)\n"
)
_FORGES_UNDER_AN_ALIAS: Final = (
    "from ccf.client.wire import WireOutcome as _Shape\n"
    "def ask(request):\n"
    "    return _Shape(request=request, product_json='{}',\n"
    "                  content_address='a', replay_ref=None, refusal=None)\n"
)
_FORGES_DEEP_IN_A_FUNCTION_BODY: Final = (
    "from ccf.client.wire import WireOutcome\n"
    "def ask(request):\n"
    "    def _answer():\n"
    "        return WireOutcome(request=request, product_json='{}',\n"
    "                           content_address='a', replay_ref=None,\n"
    "                           refusal=None)\n"
    "    return _answer()\n"
)
_FORGES_THROUGH_AN_ATTRIBUTE: Final = (
    "import ccf.client.wire\n"
    "def ask(request):\n"
    "    return ccf.client.wire.WireOutcome(request=request,\n"
    "                                       product_json='{}',\n"
    "                                       content_address='a',\n"
    "                                       replay_ref=None, refusal=None)\n"
)


@pytest.mark.parametrize(
    ("source", "why"),
    [
        pytest.param(
            _FORGES_BY_NAME,
            "the plain import, which is the shape the seam retype removed",
            id="imported-from-ccf.client.wire",
        ),
        pytest.param(
            _FORGES_FROM_THE_DOOR_MODULE,
            "the same class reached through the module that defines it",
            id="imported-from-ccf.products.door",
        ),
        pytest.param(
            _FORGES_UNDER_AN_ALIAS,
            "a two-character rename, which is all it takes to defeat a grep",
            id="imported-under-an-as-alias",
        ),
        pytest.param(
            _FORGES_DEEP_IN_A_FUNCTION_BODY,
            "a construction deferred into a nested function, where an adapter"
            " would actually put one",
            id="nested-in-a-function-body",
        ),
        pytest.param(
            _FORGES_THROUGH_AN_ATTRIBUTE,
            "an attribute-qualified call, which binds no local name at all",
            id="attribute-qualified-call",
        ),
    ],
)
def test_control_the_outcome_scan_counts_a_forging_adapter(
    tmp_path: pathlib.Path, source: str, why: str
) -> None:
    """CONTROL 13-17 — five spellings of one forgery, all counted.

    ``CLNT-12`` / ``D-22``: the gate ships with a control that makes it fail.
    The subject is a ``tmp_path`` tree passed **into the shipped function**, so
    each case exercises the walk the build runs rather than a copy of its
    logic.
    """
    written = _write_adapter(tmp_path, "rogue_adapter.py", source)

    counts = count_outcome_construction_sites([tmp_path])

    assert counts[written.as_posix()] == 1, (
        f"the gate must count {why}; it did not, so an adapter written that"
        " way would forge the echo with the build green"
    )
    with pytest.raises(AssertionError, match="rogue_adapter.py"):
        assert_no_adapter_constructs_the_outcome([tmp_path])


def _names_only_sites(tree: ast.Module) -> int:
    """A deliberately weakened walk — import-resolved names only.

    Exists for exactly one control, which holds the **necessity** of the
    attribute rule rather than merely its presence.
    """
    aliases = _outcome_aliases(tree, package=_ADAPTER_PACKAGE)
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in aliases
    )


def _module_scope_only_sites(tree: ast.Module) -> int:
    """A deliberately weakened walk — module-level statements only.

    The other half of the same argument, for the control below.
    """
    aliases = _outcome_aliases(tree, package=_ADAPTER_PACKAGE)
    found = 0
    for statement in tree.body:
        if isinstance(
            statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            continue
        for node in ast.walk(statement):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in aliases
            ):
                found += 1
    return found


def test_control_the_attribute_rule_is_the_only_thing_that_catches_case_five() -> None:
    """CONTROL 18 — the attribute shape binds no local name, and that is the point.

    ``import ccf.client.wire`` followed by ``ccf.client.wire.WireOutcome(...)``
    never binds the class to a name in the module, so alias resolution has
    nothing to resolve and a name-only walk counts **zero** for a module that
    plainly forges an outcome. This is not a hypothesis about the walk — it is
    asserted here against a deliberately weakened copy, so a reader who later
    "simplifies" :func:`_outcome_construction_sites` back to one shape finds a
    red test that explains what the simplification costs.
    """
    tree = ast.parse(_FORGES_THROUGH_AN_ATTRIBUTE)

    assert _names_only_sites(tree) == 0
    assert _outcome_construction_sites(tree, package=_ADAPTER_PACKAGE) == 1


def test_control_the_full_walk_is_the_only_thing_that_catches_case_four() -> None:
    """CONTROL 19 — the construction is inside a function, which is where it lives.

    An adapter does not construct an outcome at import time; it constructs one
    inside ``ask``. A walk over module-level statements counts **zero** for
    exactly that shape, asserted here rather than assumed, which is why the
    shipped walk is :func:`ast.walk` over the whole module. ``CLNT-14``'s
    purity gate carries the same lesson about function-body-deferred imports.
    """
    tree = ast.parse(_FORGES_DEEP_IN_A_FUNCTION_BODY)

    assert _module_scope_only_sites(tree) == 0
    assert _outcome_construction_sites(tree, package=_ADAPTER_PACKAGE) == 1


def test_control_the_outcome_scan_does_not_count_a_mere_annotation(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 20 — the first vacuity case: importing is not constructing.

    Without this and its sibling, a walk that returned non-zero for every
    module would pass every control above and prove nothing. The assertion is
    ``== 0`` on **this module's entry**, not on the mapping being empty — an
    empty mapping would mean nothing was read, which is a different and worse
    condition.
    """
    written = _write_adapter(
        tmp_path,
        "honest_adapter.py",
        "from ccf.client.wire import WireOutcome\n"
        "def ask(request) -> WireOutcome: ...\n",
    )

    assert count_outcome_construction_sites([tmp_path])[written.as_posix()] == 0


def test_control_the_outcome_scan_does_not_count_an_unrelated_module(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 21 — the second vacuity case, and the zeros that make it countable."""
    written = _write_adapter(tmp_path, "innocent.py", "X = 1\n")

    counts = count_outcome_construction_sites([tmp_path])

    assert counts == {written.as_posix(): 0}


def test_control_the_outcome_scan_refuses_a_root_it_cannot_resolve(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 22 — an unresolvable root fails loudly rather than contributing nothing.

    This is the shape of the defect that ran for a full wave: a sweep that
    skips what it cannot resolve reports green while checking less.
    """
    with pytest.raises(AssertionError, match="is not a directory"):
        count_outcome_construction_sites([tmp_path / "there-is-no-such-tree"])


def test_control_the_outcome_scan_refuses_a_file_it_cannot_parse(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 23 — an unparsable module is flagged, never skipped.

    Skipping it would mean a single syntax error hides every construction site
    in that module from the gate.
    """
    _write_adapter(tmp_path, "broken.py", "def (:\n")

    with pytest.raises(AssertionError, match="could not be parsed"):
        count_outcome_construction_sites([tmp_path])


def test_control_the_outcome_assertion_refuses_a_walk_that_read_nothing(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 24 — the vacuous walk, which is the failure mode that hides.

    An empty directory yields no counts, and "no module constructs one" is
    satisfied by a scan that looked at nothing. Checked first and separately,
    because every ceiling this gate places is satisfied by an empty walk.
    """
    empty = tmp_path / "nothing-here"
    empty.mkdir()

    with pytest.raises(AssertionError, match="read no modules"):
        assert_no_adapter_constructs_the_outcome([empty])


# --------------------------------------------------------------------------
# C-17 — the controls for the three rules the close review had to add
#
# Every limb below was watched failing before it was shipped: the forging
# module is written, the shipped walk is handed it, the count is asserted, and
# the shipped assertion is required to raise naming the module. The weakened
# twins hold each new rule's *necessity* — the pattern CONTROL 18 and 19 set.
# --------------------------------------------------------------------------


def _write_packaged_adapter(
    root: pathlib.Path, name: str, body: str
) -> pathlib.Path:
    """Materialize a module at the adapters' **real** package depth.

    ``src/ccf/client/adapters/x.py`` is imported as
    ``ccf.client.adapters.x``, and a relative import means nothing without
    that position. So the control reproduces the position rather than
    asserting about it: three ``__init__.py`` files, and
    :func:`_package_of` reads the package back off the filesystem by the same
    rule it applies to the shipped tree.

    Nothing here edits ``src/``.
    """
    directory = root / "ccf" / "client" / "adapters"
    directory.mkdir(parents=True, exist_ok=True)
    for package_directory in (root / "ccf", root / "ccf" / "client", directory):
        (package_directory / "__init__.py").write_text("", encoding="utf-8")
    path = directory / name
    path.write_text(body, encoding="utf-8")
    return path


def _forges_through(form: str) -> str:
    """A forging adapter that builds the outcome with one pydantic spelling."""
    return (
        "from ccf.client.wire import WireOutcome\n"
        "def ask(request, payload):\n"
        f"    return WireOutcome.{form}(payload)\n"
    )


#: The adapter the close review of this phase ran end to end against
#: ``2119ca6``. It never spells a constructor, echoes the question it was
#: handed, and returns another question's vessel; the gate scored it **zero**
#: and :meth:`ccf.client.client.ProductClient.ask` raised nothing. Reproduced
#: here in full — not imported from anywhere — so the module that re-opened
#: ``B0`` is a subject this gate is measured against on every run.
_FORGES_THE_WAY_THE_CLOSE_REVIEW_DID: Final = (
    "import hashlib\n"
    "from ccf.client.codec import encode_outcome\n"
    "from ccf.client.wire import WireOutcome, WireRequest\n"
    "class ForgingAdapter:\n"
    "    def __init__(self, other_vessel):\n"
    "        self._vessel = other_vessel\n"
    "    def ask(self, request):\n"
    "        forged = WireOutcome.model_validate(\n"
    "            {\n"
    "                'request': request,\n"
    "                'product_json': self._vessel,\n"
    "                'content_address': hashlib.sha256(\n"
    "                    self._vessel.encode('utf-8')\n"
    "                ).hexdigest(),\n"
    "                'replay_ref': None,\n"
    "                'refusal': None,\n"
    "            }\n"
    "        )\n"
    "        return encode_outcome(forged)\n"
)

#: ``..wire`` from ``ccf.client.adapters`` is ``ccf.client.wire``. One package
#: up, no lint against it anywhere in this repo, and zero sites until 19's
#: close review.
_FORGES_THROUGH_A_RELATIVE_IMPORT: Final = (
    "from ..wire import WireOutcome\n"
    "def ask(request):\n"
    "    return WireOutcome(request=request, product_json='{}',\n"
    "                       content_address='a', replay_ref=None,\n"
    "                       refusal=None)\n"
)

#: ``...products.door`` from the same place is ``ccf.products.door`` — two
#: levels up and back down, which is the spelling a resolver that only handles
#: one dot would miss.
_FORGES_THROUGH_A_DEEPER_RELATIVE_IMPORT: Final = (
    "from ...products.door import DoorOutcome\n"
    "def ask(request):\n"
    "    return DoorOutcome(request=request, product_json='{}',\n"
    "                       content_address='a', replay_ref=None,\n"
    "                       refusal=None)\n"
)

_FORGES_THROUGH_A_SUBCLASS: Final = (
    "from ccf.client.wire import WireOutcome\n"
    "class Forged(WireOutcome):\n"
    "    pass\n"
    "def ask(request):\n"
    "    return Forged(request=request, product_json='{}',\n"
    "                  content_address='a', replay_ref=None, refusal=None)\n"
)

#: Depth two, because a gate that stopped at depth one is defeated by one more
#: ``class`` line.
_FORGES_THROUGH_A_SUBCLASS_OF_A_SUBCLASS: Final = (
    "from ccf.client.wire import WireOutcome\n"
    "class Middle(WireOutcome):\n"
    "    pass\n"
    "class Forged(Middle):\n"
    "    pass\n"
    "def ask(request):\n"
    "    return Forged(request=request, product_json='{}',\n"
    "                  content_address='a', replay_ref=None, refusal=None)\n"
)

#: A base spelled as an attribute binds no local name to the class, so the
#: alias set has nothing to have found — the subclass rule has to read the
#: attribute too.
_FORGES_THROUGH_AN_ATTRIBUTE_SUBCLASS: Final = (
    "import ccf.client.wire\n"
    "class Forged(ccf.client.wire.WireOutcome):\n"
    "    pass\n"
    "def ask(request):\n"
    "    return Forged(request=request, product_json='{}',\n"
    "                  content_address='a', replay_ref=None, refusal=None)\n"
)


@pytest.mark.parametrize("form", sorted(_CONSTRUCTING_FORMS))
def test_control_the_outcome_scan_counts_every_pydantic_construction_form(
    tmp_path: pathlib.Path, form: str
) -> None:
    """CONTROL 25 — one case per spelling in the shipped enumeration.

    Parametrized over :data:`_CONSTRUCTING_FORMS` rather than over a list
    written here, so a spelling added to
    :data:`~ccf.products.gates.PYDANTIC_MODEL_FORMS` arrives with its control
    already written. A hand-listed control set would be the second list that
    drifts, and the drift is the defect.

    ``model_validate`` in this set is the exact spelling that carried a forged
    answer past every check in the build.
    """
    written = _write_adapter(tmp_path, "rogue_adapter.py", _forges_through(form))

    counts = count_outcome_construction_sites([tmp_path])

    assert counts[written.as_posix()] == 1, (
        f"`WireOutcome.{form}(...)` hands back an instance of the outcome"
        " shape; an adapter spelling it that way builds the answer it was"
        " supposed to carry"
    )
    with pytest.raises(AssertionError, match="rogue_adapter.py"):
        assert_no_adapter_constructs_the_outcome([tmp_path])


def test_control_the_scan_counts_the_adapter_that_re_opened_b0(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 26 — the close review's own forging adapter, scored.

    This is the module that, against ``2119ca6``, was counted zero, passed
    ``mypy --strict``, passed both conformance tamper legs, and handed the
    caller another question's vessel with nothing raised. It is the whole
    reason this fix exists, so it is a shipped subject rather than a paragraph
    in a review file.
    """
    written = _write_adapter(
        tmp_path, "rogue_adapter.py", _FORGES_THE_WAY_THE_CLOSE_REVIEW_DID
    )

    counts = count_outcome_construction_sites([tmp_path])

    assert counts[written.as_posix()] == 1, (
        "this exact module forged an answer past the whole build; a gate that"
        " scores it zero is the gate that was fixed"
    )
    with pytest.raises(AssertionError, match="rogue_adapter.py"):
        assert_no_adapter_constructs_the_outcome([tmp_path])


@pytest.mark.parametrize(
    ("source", "why"),
    [
        pytest.param(
            _FORGES_THROUGH_A_RELATIVE_IMPORT,
            "one dot up, which is where `ccf.client.wire` sits from here",
            id="relative-import-one-package-up",
        ),
        pytest.param(
            _FORGES_THROUGH_A_DEEPER_RELATIVE_IMPORT,
            "two dots up and back down into `products.door`",
            id="relative-import-two-packages-up",
        ),
    ],
)
def test_control_the_outcome_scan_counts_a_relative_import(
    tmp_path: pathlib.Path, source: str, why: str
) -> None:
    """CONTROL 27-28 — the relative spelling, at the real package depth.

    The subject is written into ``ccf/client/adapters/`` under ``tmp_path``
    with the ``__init__.py`` chain, so :func:`_package_of` resolves it exactly
    as it resolves the shipped directory. A control that wrote the module flat
    would be exercising the fallback instead, which is a different rule and is
    controlled separately below.
    """
    written = _write_packaged_adapter(tmp_path, "rogue_adapter.py", source)

    counts = count_outcome_construction_sites([tmp_path])

    assert counts[written.as_posix()] == 1, (
        f"the gate must resolve {why}; it did not, so an adapter written that"
        " way would forge the echo with the build green"
    )
    with pytest.raises(AssertionError, match="rogue_adapter.py"):
        assert_no_adapter_constructs_the_outcome([tmp_path])


def test_control_a_relative_import_in_no_package_falls_back_to_the_tail(
    tmp_path: pathlib.Path,
) -> None:
    """CONTROL 29 — the unresolvable case counts rather than scoring zero.

    A module in no package cannot have its dots resolved to a dotted name at
    all. :func:`_import_reaches` matches the tail there, which over-counts —
    and over-counting fails the build and puts a human in front of the
    question, while scoring zero is the silent direction. Asserted, because a
    fallback nobody measures is a fallback that quietly became a `return
    False`.
    """
    written = _write_adapter(
        tmp_path, "rogue_adapter.py", _FORGES_THROUGH_A_RELATIVE_IMPORT
    )

    assert _package_of(written) == "", "the control's premise is a module in no package"
    assert count_outcome_construction_sites([tmp_path])[written.as_posix()] == 1


@pytest.mark.parametrize(
    ("source", "why"),
    [
        pytest.param(
            _FORGES_THROUGH_A_SUBCLASS,
            "a subclass builds the shape by every meaning C-17 has",
            id="subclass",
        ),
        pytest.param(
            _FORGES_THROUGH_A_SUBCLASS_OF_A_SUBCLASS,
            "one more `class` line defeats a depth-one rule",
            id="subclass-of-a-subclass",
        ),
        pytest.param(
            _FORGES_THROUGH_AN_ATTRIBUTE_SUBCLASS,
            "an attribute-spelled base binds no local name to the class",
            id="subclass-of-an-attribute-base",
        ),
    ],
)
def test_control_the_outcome_scan_counts_a_subclass(
    tmp_path: pathlib.Path, source: str, why: str
) -> None:
    """CONTROL 30-32 — three depths of the subclass spelling."""
    written = _write_adapter(tmp_path, "rogue_adapter.py", source)

    counts = count_outcome_construction_sites([tmp_path])

    assert counts[written.as_posix()] == 1, (
        f"the gate must count the subclass: {why}"
    )
    with pytest.raises(AssertionError, match="rogue_adapter.py"):
        assert_no_adapter_constructs_the_outcome([tmp_path])


@pytest.mark.parametrize(
    ("source", "why"),
    [
        pytest.param(
            "class Elsewhere:\n"
            "    pass\n"
            "def ask(payload):\n"
            "    return Elsewhere.model_validate(payload)\n",
            "a pydantic form on a class that is not the outcome",
            id="pydantic-form-on-an-unrelated-class",
        ),
        pytest.param(
            "from ccf.client.wire import WireOutcome\n"
            "def ask(outcome):\n"
            "    return WireOutcome.model_dump(outcome)\n",
            "a form that serializes rather than constructs",
            id="serializing-form-on-the-outcome",
        ),
        pytest.param(
            "from ..wire import WireRequest\n"
            "def ask(request):\n"
            "    return WireRequest(product_id='p', parameters={},\n"
            "                       temporal_boundary=None)\n",
            "a relative import of a name that is not the outcome",
            id="relative-import-of-another-name",
        ),
        pytest.param(
            "class Elsewhere:\n"
            "    pass\n"
            "class Forged(Elsewhere):\n"
            "    pass\n"
            "def ask(request):\n"
            "    return Forged()\n",
            "a subclass of something that is not the outcome",
            id="subclass-of-an-unrelated-class",
        ),
    ],
)
def test_control_the_new_rules_do_not_count_everything(
    tmp_path: pathlib.Path, source: str, why: str
) -> None:
    """CONTROL 33-36 — the vacuity guards for the three new rules.

    Without these, a walk that returned non-zero for every module would satisfy
    every control above and prove nothing. One case per new rule, each written
    to be *nearly* the forging shape: an unrelated receiver, a serializing form
    on the right receiver, a relative import of the wrong name, a subclass of
    the wrong base.

    The serializing case is the one that makes the subtraction in
    :data:`_CONSTRUCTING_FORMS` load-bearing rather than decorative.
    """
    written = _write_adapter(tmp_path, "honest_adapter.py", source)

    counts = count_outcome_construction_sites([tmp_path])

    assert counts[written.as_posix()] == 0, f"the gate must not count {why}"


def _absolute_imports_only_aliases(tree: ast.Module) -> set[str]:
    """A deliberately weakened resolver — absolute imports only.

    The shape this gate shipped with. Exists for the control below, which holds
    the **necessity** of relative resolution rather than merely its presence.
    """
    aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in _OUTCOME_MODULES:
            for alias in node.names:
                if alias.name in _OUTCOME_NAMES:
                    aliases.add(alias.asname or alias.name)
    return aliases


def _without_subclasses_sites(tree: ast.Module) -> int:
    """A deliberately weakened walk — imported names only, no subclasses."""
    aliases = _absolute_imports_only_aliases(tree)
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in aliases
    )


def _without_construction_forms_sites(tree: ast.Module) -> int:
    """A deliberately weakened walk — the two rules this gate shipped with."""
    aliases = _outcome_aliases(tree, package=_ADAPTER_PACKAGE)
    found = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if isinstance(function, ast.Name) and function.id in aliases:
            found += 1
        elif isinstance(function, ast.Attribute) and function.attr in _OUTCOME_NAMES:
            found += 1
    return found


def test_control_relative_resolution_is_the_only_thing_that_catches_the_dots() -> None:
    """CONTROL 37 — the weakened resolver scores zero on the relative spelling.

    Asserted against a deliberately weakened copy rather than assumed, so a
    reader who later "simplifies" :func:`_outcome_aliases` back to
    ``node.module in _OUTCOME_MODULES`` finds a red test naming what the
    simplification costs. That exact expression is what the gate shipped with,
    and it is why ``from ..wire import WireOutcome`` scored zero.
    """
    tree = ast.parse(_FORGES_THROUGH_A_RELATIVE_IMPORT)

    assert _absolute_imports_only_aliases(tree) == set()
    assert _outcome_construction_sites(tree, package=_ADAPTER_PACKAGE) == 1


def test_control_the_subclass_rule_is_the_only_thing_that_catches_a_subclass() -> None:
    """CONTROL 38 — a walk without :func:`_with_subclasses` counts zero."""
    tree = ast.parse(_FORGES_THROUGH_A_SUBCLASS)

    assert _without_subclasses_sites(tree) == 0
    assert _outcome_construction_sites(tree, package=_ADAPTER_PACKAGE) == 1


def test_control_the_form_rule_is_the_only_thing_that_catches_model_validate() -> None:
    """CONTROL 39 — the two-rule walk counts zero on the shape that forged B0.

    This is the measurement the close review made against ``2119ca6``, kept
    here as a live assertion: the gate as shipped saw **nothing** in the module
    that re-opened ``B0``.
    """
    tree = ast.parse(_FORGES_THE_WAY_THE_CLOSE_REVIEW_DID)

    assert _without_construction_forms_sites(tree) == 0
    assert _outcome_construction_sites(tree, package=_ADAPTER_PACKAGE) == 1


def test_the_construction_forms_are_the_shipped_enumeration_minus_the_dumps() -> None:
    """CONTROL 40 — the subtraction cannot quietly become a no-op.

    :data:`_CONSTRUCTING_FORMS` is
    :data:`~ccf.products.gates.PYDANTIC_MODEL_FORMS` minus three names. If one
    of those three is renamed upstream the subtraction removes nothing and this
    gate silently starts counting a serializing call as a construction — a
    different failure from the one being fixed, and still a gate that does not
    mean what it says.
    """
    assert _SERIALIZING_FORMS <= PYDANTIC_MODEL_FORMS, (
        "a name in the serializing set is no longer a shipped spelling, so the"
        " subtraction below removed less than it was written to remove"
    )
    assert not (_CONSTRUCTING_FORMS & _SERIALIZING_FORMS)
    assert {"model_validate", "model_validate_json", "model_copy"} <= (
        _CONSTRUCTING_FORMS
    )


# --------------------------------------------------------------------------
# D-04 — the documented `as_of` rule, asserted where a reader would look
# --------------------------------------------------------------------------


def test_the_as_of_rule_is_documented_on_ask() -> None:
    """``D-04`` puts the rule on ``ask()``, not in a design document."""
    from ccf.client.client import ProductClient

    documentation = ProductClient.ask.__doc__ or ""
    assert "decision instant" in documentation
    assert "as_of" in documentation
