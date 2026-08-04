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
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import pathlib
import pkgutil
import sys
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
        for info in pkgutil.walk_packages(search_path, prefix=f"{package_name}."):
            if _is_private(info.name):
                continue
            found.add(info.name)
    return sorted(found)


def _kind_of(obj: Any) -> str:
    """Classify an exported object for the manifest."""
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


def _shape_of(obj: Any, kind: str) -> Any:
    """The version-sensitive detail a reshape has to move.

    Contracts record their fields (name → annotation repr); callables record
    their signature; everything else records only its type name, because a
    constant's *value* is a deployment concern, not a surface one.
    """
    if kind == "contract":
        fields = getattr(obj, "model_fields", {})
        return {
            name: str(field.annotation) for name, field in sorted(fields.items())
        }
    if kind in ("class", "function"):
        try:
            return str(inspect.signature(obj))
        except (TypeError, ValueError):
            return type(obj).__name__
    return type(obj).__name__


def _resolve_export(module: Any, module_name: str, name: str) -> Any:
    """The object ``name`` denotes on ``module``, import-order independently.

    A package that lists submodules in ``__all__`` (``ccf.signal`` lists
    ``envelope`` and ``source``) only binds them as attributes once something
    imports them. A bare ``getattr`` therefore describes the *interpreter's
    current import state* rather than the package's declared surface, and the
    manifest changes depending on what else ran first — deterministic when
    ``build_surface`` runs alone, drifting under the full test suite. Import
    the submodule explicitly so the answer is the same either way.
    """
    obj = getattr(module, name, None)
    if obj is not None:
        return obj
    try:
        return importlib.import_module(f"{module_name}.{name}")
    except ImportError:
        return None


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
