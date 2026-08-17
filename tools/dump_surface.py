"""D-15 — regenerate the committed public-surface manifest for `/src` + `/runtime`.

D-15 asks for two halves of one guarantee: a *generated* manifest of the SDK's
public surface, so that a removed or reshaped export cannot slip through
unnoticed, and a *curated* log (`docs/surface-changes/`, assembled into
`docs/SURFACE-CHANGES.md` at phase close) carrying the rationale and the
migration guidance a generated diff can never supply. This module is the
generator half. The assertion half is `tests/test_surface_drift.py`, which
imports `serialize` from here so the two halves cannot drift apart, and whose
failure message names `make surface` as the fix.

The two files, and why they are named the way they are
------------------------------------------------------

``SURFACE_PATH`` — ``docs/surface/v0.2-surface.json`` — is the **live**
manifest. It is the path this tool writes, the path ``--check`` compares
against, and the path ``tests/test_surface_drift.py`` reads. It holds the
current surface at phase start, and again after plan 15-21 regenerates it at
phase close.

``BASELINE_PATH`` — ``docs/surface/v0.2-surface-baseline.json`` — is a frozen
byte-for-byte copy of the phase-start surface, written once by plan 15-01 and
never again. It is the immutable "before" side of the ROADMAP Success
Criterion 6 diff. **``main()`` never writes it.**

The naming is deliberate and load-bearing. The obvious alternative — freeze
the plain name and qualify the live one — would leave every future contributor
reaching for "the surface manifest", finding ``v0.2-surface.json``, and getting
the *stale* one. Qualifying the *frozen* file instead means the unqualified
path is always the live path, no tool and no test is ever re-pointed, and a
stale read is impossible by naming.

Single-owner regeneration
-------------------------

The live manifest is a whole-tree artifact, so it is written by exactly two
plans — 15-01 at phase start and 15-21 at phase close. Eleven in-flight plans
each regenerating it in its own worktree would each pass ``--check`` pre-merge
and leave the tree stale after the second merge, on a file no plan then owns.

That is what ``--report`` is for. ``--report`` is the mode for a plan
mid-phase: it writes nothing, prints the fully-qualified names added, removed,
and reshaped relative to the committed live manifest, and **always exits 0**.
``--check`` is the mode for the phase gate: it writes nothing and exits 1 on
any difference. A bare ``--check`` mid-phase would fail on every in-flight plan
for a legitimate, documented reason; ``--report`` instead lets a plan positively
assert that the names it claims to add actually appear, which is a stronger
check than ``--check`` ever was.

Determinism recipe
------------------

``json.dumps(..., indent=2, sort_keys=True) + "\\n"`` removes dict-ordering
sensitivity, so the bytes do not depend on the order ``pkgutil`` happened to
walk the trees or Pydantic happened to register its fields. ``__all__`` is
sorted before it is recorded, every per-name entry is keyed rather than
positional, and the file ends in exactly one newline. Docstrings are
deliberately *not* recorded: the manifest tracks signatures, not prose, so a
reworded docstring is not a surface change.

The corollary is deliberate, not a bug: **a Pydantic or Python bump will move
the manifest** — annotation reprs and ``inspect.signature`` output are both
version-sensitive. That diff is desirable and reviewable — it is precisely the
moment a maintainer should look at what the dependency changed about the
public surface — and the correct response is to run ``make surface`` and read
the diff, never to relax the check.

What a shape can and cannot see (`DI-15.5-06`, ruled by `D-IMPL-122`)
---------------------------------------------------------------------

``inspect.signature`` on a **class** resolves ``__init__``, which for a
``Protocol`` is universally ``"(*args, **kwargs)"``. The manifest therefore
recorded nothing about what a Protocol actually takes. `D-IMPL-110` proved the
cost by demonstration rather than by argument: plan `15.5-15` widened both
resolver seams from three arguments to five — a break for every adopter
implementing them — and this manifest was **byte-identical across that
change**. Two plans hit the wall independently and both were forced to classify
their change ``behavior`` rather than ``reshaped``, because ``reshaped`` fails
``tests/test_surface_completeness.py`` when there is no diff line to point at.

`D-IMPL-122` ruled the fix and, just as deliberately, ruled its limit. Two
things move, and one explicitly does not:

1. **A ``Protocol`` defining ``__call__`` records that ``__call__``**, with
   ``self`` elided because ``self`` is not part of the contract an adopter
   implements against. Detection is **structural** — the runtime ``_is_protocol``
   marker — never the class name: two of the capture targets
   (``PeerCardResolver``, ``PeerEndpointResolver``) carry no ``Protocol``
   suffix, and a plain class can be named ``...Protocol`` without being one.
2. **A type alias records its rendered type** rather than a signature. A
   ``Literal`` alias gaining or losing a member is a real surface change; before
   this, every alias rendered ``"(*args, **kwargs)"`` and no such change
   produced a diff line at all. **The alias branch is consulted for every
   export, not only for a callable one** — see :func:`_shape_of`. It was
   originally reachable only from the ``class``/``function`` branch, and
   :func:`_kind_of` classifies by ``callable(obj)``: ``typing.Literal[…]`` and
   ``typing.Annotated[…]`` are callable and rendered correctly, while a PEP-604
   union — ``X | None``, a ``types.UnionType`` — is **not**, so it fell through
   to ``constant`` and recorded the information-free ``"UnionType"``. Phase
   15.6's single-agent review found the alias this phase itself shipped sitting
   in that blind spot: ``SourceRefreshRecency`` recorded
   ``{"kind": "constant", "shape": "UnionType"}`` and did not move when the
   union was widened. The rendering is scrubbed of memory addresses
   (:func:`_render_alias`) — ``str()`` of an ``Annotated`` alias carrying a
   Pydantic validator embeds ``<function ... at 0x...>``, and committing that
   verbatim would make the manifest differ between two runs on an unchanged
   tree, which is a worse defect than the blind spot being fixed.

3. **A ``Protocol`` with named methods but no ``__call__`` is left recording
   ``"(*args, **kwargs)"``, deliberately.** This is a **descope, not an
   oversight**, and it is written here rather than left to be rediscovered.
   Rendering a Protocol's method set is the shape that actually closes the
   blind spot; `D-IMPL-122` declined it on a measured cost — 65 new ``reshaped``
   diff lines against 11 — and Dave chose the smaller fix knowingly. Measured
   at that ruling: ``__call__`` capture reaches **12 of 51** information-free
   Protocol classes, leaving **39 whose entire public contract is a method set
   still invisible to this manifest**, including every one of the seven
   `D-IMPL-110` names by name (``ArtifactStoreProtocol``,
   ``ControlPlaneProtocol``, ``HarnessAdapterProtocol``,
   ``OrchestrationProtocol``, ``HITLTransportProtocol``, ``LLMClientProtocol``,
   ``DebtFactorScorerProtocol``). **The consequence, stated so no gate cites
   this file for more than it proves: after this fix the manifest is still not
   evidence of surface stability for a multi-method Protocol.** A signature
   change to any of their methods still produces no diff line.
   ``tests/test_surface_shape_capture.py`` asserts the descope so that closing
   it is a deliberate scope change with a ruling behind it, not a silent one.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import pathlib
import pkgutil
import re
import sys
import typing
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

#: The **live** public-surface manifest — deliberately the unqualified name,
#: so that whoever reaches for "the surface manifest" gets the current one.
SURFACE_PATH = REPO_ROOT / "docs" / "surface" / "v0.2-surface.json"

#: The frozen phase-start copy. Written once, by plan 15-01's Task 2; read by
#: plan 15-21's Success Criterion 6 diff. Never written by :func:`main`.
BASELINE_PATH = REPO_ROOT / "docs" / "surface" / "v0.2-surface-baseline.json"

#: The two trees whose public surface the manifest covers.
_ROOTS: tuple[tuple[str, pathlib.Path], ...] = (
    ("ccf", REPO_ROOT / "src"),
    ("ccf_runtime", REPO_ROOT / "runtime"),
)


def _is_private(dotted: str) -> bool:
    """True if any dotted segment is private (leading underscore)."""
    return any(segment.startswith("_") for segment in dotted.split("."))


def iter_public_modules() -> list[str]:
    """Dotted names of every importable module under the two trees.

    Modules whose name has a private segment are skipped: a leading underscore
    is the repo's own statement that the module is not part of the surface.
    """
    found: set[str] = set()
    for package_name, tree in _ROOTS:
        package = importlib.import_module(package_name)
        search_path = [str(tree / package_name)]
        found.add(package_name)
        # `onerror` is REQUIRED, not defensive. Without it `walk_packages`
        # swallows an ImportError and silently drops the entire subtree beneath
        # it -- so a surface gate walks less and still reports green. Measured
        # 2026-08-15 (DEF-17-06): three subpackages went undiscovered and
        # twelve public names went undocumented behind a passing run. The
        # fourth instance in this phase of a check that stops checking without
        # going red; it must fail loudly instead.
        def _refuse(name: str) -> None:
            raise RuntimeError(
                f"surface walk could not import {name!r}. The manifest would"
                " silently omit that subtree and every public name beneath it."
                " Fix the import rather than skipping the module."
            )

        for info in pkgutil.walk_packages(
            search_path, prefix=f"{package_name}.", onerror=_refuse
        ):
            if _is_private(info.name):
                continue
            found.add(info.name)
    return sorted(found)


def _kind_of(obj: Any) -> str:
    """Classify an exported object for the manifest."""
    if obj is UNRESOLVED:
        return "unresolved"
    if inspect.isclass(obj):
        try:
            from ccf.contracts.base import CCFContract

            if issubclass(obj, CCFContract):
                return "contract"
        except Exception:  # pragma: no cover - defensive
            pass
        return "class"
    if callable(obj):
        return "function"
    return "constant"


#: Matches the ``at 0x7f...`` tail CPython appends to a default ``repr``.
#: Scrubbed rather than tolerated — see :func:`_render_alias`.
_ADDRESS = re.compile(r" at 0x[0-9a-fA-F]+")


def _protocol_call(obj: Any) -> Any | None:
    """A ``Protocol``'s own ``__call__``, or ``None`` if it defines none.

    Structural on two counts. The class is recognised as a Protocol by the
    runtime ``_is_protocol`` marker rather than by its name — see the module
    docstring for why a name-based rule is wrong in both directions. And
    ``__call__`` is looked up through ``__mro__`` ``__dict__``s rather than with
    ``getattr``, because ``getattr(cls, "__call__")`` finds ``type.__call__``
    on the metaclass for *every* class and would report a signature for
    Protocols that define none.
    """
    if not inspect.isclass(obj) or not getattr(obj, "_is_protocol", False):
        return None
    for klass in getattr(obj, "__mro__", ()):
        found = klass.__dict__.get("__call__")
        if found is not None:
            return found
    return None


def _call_shape(function: Any) -> str | None:
    """``function``'s signature with the leading ``self`` elided."""
    try:
        signature = inspect.signature(function)
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return None
    parameters = list(signature.parameters.values())
    if parameters and parameters[0].name == "self":
        signature = signature.replace(parameters=parameters[1:])
    return str(signature)


def _is_type_alias(obj: Any) -> bool:
    """True for ``Literal[...]``, ``Union[...]``, ``Callable[...]`` and friends.

    ``typing.get_origin`` is the structural test: it is non-``None`` for every
    subscripted typing form and ``None`` for a plain function, a class, or a
    ``functools.partial``. That keeps the alias branch from reaching anything
    whose signature is meaningful.
    """
    return not inspect.isclass(obj) and typing.get_origin(obj) is not None


def _render_alias(obj: Any) -> str:
    """An alias's type, rendered deterministically.

    ``str()`` is the right rendering — it is what the contract branch already
    records for a field annotation — except that an ``Annotated`` alias
    carrying a Pydantic validator renders the validator's function as
    ``<function name at 0x...>``. The address is process-local, so committing
    it would make two runs on an unchanged tree disagree. Scrubbing just the
    address keeps the informative part (the validator's name) and drops the
    only non-deterministic part.
    ``tests/test_surface_shape_capture.py`` asserts the whole serialized
    manifest carries no address, so a future alias form that leaks one fails
    rather than silently destabilising the gate.
    """
    return _ADDRESS.sub("", str(obj))


def _shape_of(obj: Any, kind: str) -> Any:
    """The version-sensitive detail a reshape has to move.

    Contracts record their fields (name → annotation repr); a ``Protocol``
    defining ``__call__`` records that ``__call__``; a type alias records its
    rendered type; other callables record their signature; everything else
    records only its type name, because a constant's *value* is a deployment
    concern, not a surface one.

    The Protocol and alias branches are `D-IMPL-122`'s scope, and the module
    docstring records what they deliberately leave uncovered.

    **The alias test is asked of every export, not only of a callable one.**
    Guarding it behind ``kind in ("class", "function")`` made it unreachable for
    exactly the aliases :func:`_kind_of` cannot recognise — a PEP-604 union is
    not ``callable``, so it is classified ``constant`` and never reached the
    branch that would have rendered it. That is a blind spot the fix itself
    introduced, and it swallowed `15.6-07`'s own ``SourceRefreshRecency``.
    ``kind`` is left alone: an alias keeps whatever kind it was recorded under,
    so this widens what the manifest *sees* without moving what it *calls*
    things.
    """
    if kind == "unresolved":
        return "unresolved"
    if kind == "contract":
        fields = getattr(obj, "model_fields", {})
        return {
            name: str(field.annotation) for name, field in sorted(fields.items())
        }
    if _is_type_alias(obj):
        return _render_alias(obj)
    if kind in ("class", "function"):
        call = _protocol_call(obj)
        if call is not None:
            shape = _call_shape(call)
            if shape is not None:
                return shape
        try:
            return str(inspect.signature(obj))
        except (TypeError, ValueError):
            return type(obj).__name__
    return type(obj).__name__


class _Unresolved:
    """A declared export that resolves to nothing at all.

    Distinct from ``None`` **because an export's value may legitimately be
    ``None``**: ``ccf.halflife.assessment.NO_SOURCE_REFRESH_RECENCY`` is a
    ``Final[SourceRefreshWindow | None] = None`` sentinel, and before this
    marker existed it was indistinguishable from a name that could not be
    resolved. Both recorded the shape ``"NoneType"``, which is the fingerprint
    ``tests/test_surface_drift.py::test_no_export_resolves_to_nothing`` reads —
    so a legitimate sentinel tripped a gate whose whole point is to catch
    import-order sensitivity. Making the failure a positive marker rather than
    an inferred type name keeps the gate exact in both directions.
    """

    __slots__ = ()


#: The one instance. Compared by identity, never by truthiness.
UNRESOLVED = _Unresolved()


def _resolve_export(module: Any, module_name: str, name: str) -> Any:
    """The object ``name`` denotes on ``module``, import-order independently.

    A package that lists submodules in ``__all__`` (``ccf.signal`` lists
    ``envelope`` and ``source``) only binds them as attributes once something
    imports them. A bare ``getattr`` therefore describes the *interpreter's
    current import state* rather than the package's declared surface, and the
    manifest changes depending on what else ran first — deterministic when
    ``build_surface`` runs alone, drifting under the full test suite. Import
    the submodule explicitly so the answer is the same either way.

    Returns :data:`UNRESOLVED` — never ``None`` — when the name denotes
    nothing, so that an export whose *value* is ``None`` is recorded as the
    ``None`` it is rather than as a resolution failure.
    """
    obj = getattr(module, name, UNRESOLVED)
    if obj is not UNRESOLVED:
        return obj
    try:
        return importlib.import_module(f"{module_name}.{name}")
    except ImportError:
        return UNRESOLVED


def build_surface() -> dict[str, Any]:
    """The manifest document: dotted module name → its public surface."""
    document: dict[str, Any] = {}
    for module_name in iter_public_modules():
        module = importlib.import_module(module_name)
        exported = getattr(module, "__all__", None)
        if not exported:
            continue
        names = sorted(exported)
        entries: dict[str, Any] = {}
        for name in names:
            obj = _resolve_export(module, module_name, name)
            kind = _kind_of(obj)
            entries[name] = {"kind": kind, "shape": _shape_of(obj, kind)}
        document[module_name] = {"__all__": names, "exports": entries}
    return document


def serialize(document: dict[str, Any]) -> str:
    """The one serialization recipe — see "Determinism recipe" above.

    ``tests/test_surface_drift.py`` imports this function rather than
    restating the recipe, so the committed file and the drift assertion can
    never disagree about what "the surface" means.
    """
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def _flatten(document: dict[str, Any]) -> dict[str, Any]:
    """``{"<dotted.module>.<name>": entry}`` for every exported name."""
    flat: dict[str, Any] = {}
    for module_name, record in document.items():
        for name, entry in record.get("exports", {}).items():
            flat[f"{module_name}.{name}"] = entry
    return flat


def diff_surfaces(
    before: dict[str, Any], after: dict[str, Any]
) -> dict[str, list[str]]:
    """Fully-qualified names added, removed, and reshaped between two manifests.

    Name granularity, not module granularity. Plan 15-21's completeness
    cross-check and its ``SURFACE-AUDIT.md`` diff both consume this function,
    and a module-granular diff cannot tell an addition from a removal inside a
    module that both gained and lost exports.

    This is the function the **name-level** completeness guarantee is built
    on. The standing drift gate (``tests/test_surface_drift.py``) is a
    coarser, module-granular tripwire by design — see its docstring for why
    the two are a pair.
    """
    old = _flatten(before)
    new = _flatten(after)
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    reshaped = sorted(
        name for name in set(old) & set(new) if old[name] != new[name]
    )
    return {"added": added, "removed": removed, "reshaped": reshaped}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Regenerate the committed public-surface manifest for src +"
            " runtime (D-15)."
        )
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help=(
            "Write nothing; exit 1 if the on-disk manifest differs from the"
            " live surface. The phase-gate mode."
        ),
    )
    mode.add_argument(
        "--report",
        action="store_true",
        help=(
            "Write nothing; print the names added/removed/reshaped relative"
            " to the committed manifest and always exit 0. The in-flight mode."
        ),
    )
    args = parser.parse_args(argv)

    document = build_surface()
    emitted = serialize(document)

    if args.check:
        on_disk = (
            SURFACE_PATH.read_text(encoding="utf-8")
            if SURFACE_PATH.exists()
            else ""
        )
        if on_disk != emitted:
            print(
                f"{SURFACE_PATH} differs from the live public surface."
                " Run `make surface` and review the diff — a removed export"
                " or a Pydantic version bump is a reviewable change to the"
                " public surface, not a test bug. Rationale and migration"
                " guidance belong in a docs/surface-changes/ fragment.",
                file=sys.stderr,
            )
            return 1
        return 0

    if args.report:
        committed: dict[str, Any] = (
            json.loads(SURFACE_PATH.read_text(encoding="utf-8"))
            if SURFACE_PATH.exists()
            else {}
        )
        report = diff_surfaces(committed, document)
        for key in ("added", "removed", "reshaped"):
            print(f"{key} ({len(report[key])}):")
            for name in report[key]:
                print(f"  {name}")
        return 0

    SURFACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SURFACE_PATH.write_text(emitted, encoding="utf-8")
    print(f"wrote {SURFACE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
