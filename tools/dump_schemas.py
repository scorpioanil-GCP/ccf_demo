"""ERGO-12 — regenerate the committed JSON Schema per SDK artifact class.

D-11's posture for the documentation suite is generate-at-build: nothing
derived from code is committed, because a committed derivative is a
derivative that can go stale. This tool is the *second* deliberate
exception, on exactly the D-12 reasoning that admitted the first
(``tools/dump_openapi.py``): the schemas are what **adopters author
against**, in their editor, before anything runs. A schema that only
exists at build time cannot be the target of a
``# yaml-language-server: $schema=`` header in a checked-in artifact
document, and a schema an adopter cannot point at is a schema that does
not help them.

So one file per SDK-owned artifact class is committed at
``docs/schemas/<class-id>.json``, reviewed as a diff: a renamed field, a
tightened constraint, or a newly required key all surface as reviewable
lines on the same commit that causes them, rather than as a silent
difference between what the SDK validates and what an adopter's editor
claims.

The set is :data:`ccf.deployment.classes.SDK_ARTIFACT_CLASSES` — the
hand-maintained registry of classes the SDK *owns the schema of*. Classes
the SDK does not own resolve to the open ``DeclaredArtifact`` envelope and
deliberately get no committed schema: the SDK never invents a schema for a
namespace that is not its own (CLAUDE.md §11, mechanism-not-values).

This module is the regeneration half. The assertion half is
``tests/cli/test_schema_export.py``, which imports :func:`serialize` from
here so the two halves cannot drift apart, and whose failure message names
``make schemas`` as the fix.

Determinism recipe
------------------

``json.dumps(..., indent=2, sort_keys=True)`` removes dict-ordering
sensitivity, so the bytes do not depend on the order Pydantic happened to
walk a model's fields or register its ``$defs``. ``pydantic`` is an exact
pin in ``pyproject.toml``, so the emitted shapes are fixed for a given
checkout. Every file ends with a trailing newline, so the committed tree is
POSIX-clean and the diffs are line diffs.

The corollary is deliberate, not a bug: **a Pydantic bump will move the
schemas.** That diff is desirable and reviewable — it is precisely the
moment a maintainer should look at what the dependency changed about what
adopters author against — and the correct response is to run ``make
schemas`` and read the diff, never to relax the check.

Why an orphan is drift too
--------------------------

``--check`` fails on a committed schema whose class no longer exists, not
only on one whose bytes moved. An orphan is the worse failure of the two:
a drifted schema tells an adopter something slightly wrong about a class
that exists, while an orphan tells them a class exists that does not. The
freshness gate is over the *set* as much as over the bytes.

The ``x-ccf-class-id`` annotation
---------------------------------

Each emitted document carries its class id under the JSON Schema extension
key ``x-ccf-class-id``. Without it, the only link from a schema file to the
class it describes is the file *name*, and a name is not a checkable claim
— a ``$schema`` header could name a real file that describes a different
class and nothing would fire. ``tools/check_schema_headers.py`` reads this
field rather than parsing the path, so "this document is annotated with the
schema of the class it actually is" is verified rather than assumed.
"""

from __future__ import annotations

import argparse
import importlib
import json
import pathlib
import pkgutil
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

#: The committed schema tree — the ERGO-12 authoring baseline.
SCHEMAS_DIR = REPO_ROOT / "docs" / "schemas"

#: JSON Schema extension key carrying the CCF artifact class id.
CLASS_ID_KEY = "x-ccf-class-id"

#: The committed schema of the open ``DeclaredArtifact`` envelope.
#:
#: Deployment-authored artifact classes — a policy bundle, a deployment's own
#: expectations document — resolve through
#: :func:`~ccf.controlplane.artifacts.declared_artifact_class` and deliberately
#: get **no** class-specific schema: the SDK never invents a schema for a
#: namespace that is not its own. That left such documents with no honest
#: ``$schema`` target at all, and therefore no way to pass
#: ``tools/check_schema_headers.py`` other than a deferral marker that names no
#: real closing plan (plan 15-13).
#:
#: What the SDK *does* own is the **envelope**: ``semver``, ``class_id``, and an
#: open ``declaration``. Committing that one schema lets a deployment-authored
#: document carry a header that is true — it annotates the three envelope keys
#: the SDK validates and says nothing about the declaration's interior, which is
#: precisely the boundary :class:`~ccf.controlplane.artifacts.DeclaredArtifact`
#: draws. It is emitted here but is **not** a member of
#: :data:`~ccf.deployment.classes.SDK_ARTIFACT_CLASSES`, so no manifest can name
#: it as a class and the "unknown id resolves to the envelope" design is
#: untouched.
ENVELOPE_CLASS_ID = "ccf.declared-artifact"


def author_versioned_classes() -> dict[str, Any]:
    """SDK-owned classes a manifest deliberately cannot address (plan 15-14).

    These carry D-IMPL-28 two-field versioning (``schema_version`` +
    ``artifact_version``) and register through
    :meth:`~ccf.controlplane.registry.ControlPlaneRegistry.register_versioned`,
    which holds the author's version claim against content identity — the D-05
    bump check. :func:`~ccf.deployment.manifest.load_and_boot` registers through
    ``register_typed``, which does **not** run that check, so these classes are
    deliberately absent from
    :data:`~ccf.deployment.classes.SDK_ARTIFACT_CLASSES`: a manifest entry
    naming one would silently drop the governance the class exists to carry.

    They are nonetheless **SDK-owned schemas**, and an adopter authors documents
    of them by hand — an agent definition, a prompt artifact, a skill catalog
    entry. So they get committed schemas here on exactly the reasoning that
    admitted the envelope above: a schema an adopter cannot point a ``$schema``
    header at is a schema that does not help them. What they do *not* get is
    manifest addressability, and keeping the set here rather than in ``/src``
    is what makes the two impossible to confuse.

    The membership rule is checkable rather than editorial — every one of these
    contracts declares an ``artifact_version`` field, and
    ``tests/cli/test_schema_export.py`` holds the set to that rule so a new
    author-versioned class cannot quietly go un-emitted.
    """
    from ccf.agents.definitions import (
        AGENT_DEFINITION,
        PROMPT_ARTIFACT,
        TASK_DEFINITION,
    )
    from ccf.skills.catalog import SKILL_CATALOG_ENTRY
    from ccf.skills.grants import SKILL_GRANT
    from ccf.workflow.definitions import WORKFLOW_DEFINITION

    return {
        artifact_class.class_id: artifact_class
        for artifact_class in (
            AGENT_DEFINITION,
            PROMPT_ARTIFACT,
            TASK_DEFINITION,
            SKILL_CATALOG_ENTRY,
            SKILL_GRANT,
            WORKFLOW_DEFINITION,
        )
    }


def unaddressable_classes() -> dict[str, Any]:
    """SDK-owned classes in neither other set, found rather than listed.

    Plan 15-17 reported two classes with no committed schema — ``ccf.hitl-policy``
    and ``ccf.scope-mapping`` — and this bucket exists to close that. Written as
    a discovery rather than a list, it immediately found **five**: the two
    reported, plus ``ccf.admission-record``, ``ccf.peering-trust-policy`` and
    ``ccf.peering-inbound-payload-ceiling``, which nobody had noticed at all.
    That is the argument for the mechanism in one line — a hand-maintained third
    list would have carried two entries and been wrong the day it was written.

    None is author-versioned (all carry ``semver``, not ``artifact_version``),
    and none is manifest-addressable, for two different reasons:

    * ``ccf.scope-mapping`` lives in :mod:`ccf_runtime`, and
      :data:`~ccf.deployment.classes.SDK_ARTIFACT_CLASSES` lives in ``/src``.
      ``/src`` never imports ``/runtime`` — the dependency runs one way only —
      so that class *cannot* join the set without inverting it.
    * The rest live in ``/src`` and could join. Whether they should is an SDK
      contract question about manifest addressability, and granting a schema
      does not prejudge it either way.

    **These are not all hand-authored documents, and the bucket does not claim
    they are.** ``ccf.hitl-policy`` and ``ccf.scope-mapping`` an adopter writes;
    ``ccf.admission-record`` the fabric *produces* at an A2A boundary. A schema
    serves both cases — one as the contract you author against, the other as the
    published shape of what you receive — and the useful invariant is the
    simple one: **every** :class:`~ccf.controlplane.artifact_base.ArtifactClass`
    in the tree has a committed schema, so no class is invisible to an adopter
    reading ``docs/schemas/``. What a schema never grants is addressability;
    that stays governed by the two sets above.

    **Discovered, not enumerated.** The buckets above are hand-maintained lists
    held to a membership rule by a test. This one walks the ``ccf`` and
    ``ccf_runtime`` trees for ``ArtifactClass`` instances and returns whatever
    is in neither other set, because the failure it exists to fix was precisely
    a class nobody remembered to list.
    """
    from ccf.controlplane.artifact_base import ArtifactClass
    from ccf.deployment.classes import SDK_ARTIFACT_CLASSES

    known = {**SDK_ARTIFACT_CLASSES, **author_versioned_classes()}
    found: dict[str, Any] = {}
    for module_name in _artifact_bearing_modules():
        module = importlib.import_module(module_name)
        for name in dir(module):
            candidate = getattr(module, name, None)
            if not isinstance(candidate, ArtifactClass):
                continue
            if candidate.class_id in known:
                continue
            found[candidate.class_id] = candidate
    return found


def _artifact_bearing_modules() -> list[str]:
    """Dotted names of every importable module under ``ccf`` and ``ccf_runtime``.

    Deliberately a filesystem walk rather than an import list: a class defined
    in a module nobody imports here is exactly the class that goes un-emitted.
    Modules that fail to import are skipped — an optional-dependency module is
    not a schema gap, and raising here would make ``make schemas`` hostage to
    every extra.
    """
    names: list[str] = []
    for package_name in ("ccf", "ccf_runtime"):
        try:
            package = importlib.import_module(package_name)
        except ImportError:  # pragma: no cover - defensive
            continue
        for info in pkgutil.walk_packages(
            list(package.__path__), prefix=f"{package_name}."
        ):
            if any(part.startswith("_") for part in info.name.split(".")):
                continue
            try:
                importlib.import_module(info.name)
            except Exception:  # noqa: BLE001 - optional extras are not gaps
                continue
            names.append(info.name)
    return sorted(names)


def schema_owned_classes() -> dict[str, Any]:
    """Every class with a committed schema, keyed by ``class_id``.

    The union a ``$schema`` header may name: manifest-addressable classes, the
    author-versioned ones, and the unaddressable remainder. The **envelope** is
    deliberately not here — it is not a class any document *is*, it is the shape
    every deployment-authored document shares, and the header checker routes it
    separately.
    """
    from ccf.deployment.classes import SDK_ARTIFACT_CLASSES

    return {
        **SDK_ARTIFACT_CLASSES,
        **author_versioned_classes(),
        **unaddressable_classes(),
    }


def schema_path(class_id: str) -> pathlib.Path:
    """Return the committed path for ``class_id``.

    Class ids are dotted-and-dashed lowercase identifiers
    (``ccf.operator-parameters.traversal``), which are already path-safe
    on every supported platform, so the id is used verbatim rather than
    mangled: a mangled name would make the file harder to find from the
    ``$schema`` header that names it.
    """
    if "/" in class_id or "\\" in class_id or class_id in {".", ".."}:
        raise ValueError(
            f"artifact class id {class_id!r} is not path-safe; it cannot"
            " address a committed schema file"
        )
    return SCHEMAS_DIR / f"{class_id}.json"


def emit() -> dict[pathlib.Path, str]:
    """Return the full committed tree as ``path -> serialized bytes``.

    One file per SDK-owned class — manifest-addressable
    (:data:`~ccf.deployment.classes.SDK_ARTIFACT_CLASSES`) and author-versioned
    (:func:`author_versioned_classes`) alike — plus the
    :data:`ENVELOPE_CLASS_ID` schema of the open ``DeclaredArtifact`` envelope.
    See those two for why each set is committed and why they are separate.
    """
    from ccf.controlplane.artifacts import DeclaredArtifact

    documents: dict[pathlib.Path, str] = {}
    for class_id, artifact_class in schema_owned_classes().items():
        document: dict[str, Any] = artifact_class.contract.model_json_schema()
        document[CLASS_ID_KEY] = class_id
        documents[schema_path(class_id)] = serialize(document)

    envelope: dict[str, Any] = DeclaredArtifact.model_json_schema()
    envelope[CLASS_ID_KEY] = ENVELOPE_CLASS_ID
    documents[schema_path(ENVELOPE_CLASS_ID)] = serialize(envelope)
    return documents


def serialize(document: dict[str, Any]) -> str:
    """The one serialization recipe — see "Determinism recipe" above.

    ``tests/cli/test_schema_export.py`` imports this function rather than
    restating the recipe, so the committed files and the drift assertion
    can never disagree about what "the schema" means.
    """
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def committed() -> dict[pathlib.Path, str]:
    """Return what is on disk today, keyed the same way as :func:`emit`."""
    if not SCHEMAS_DIR.is_dir():
        return {}
    return {
        path: path.read_text(encoding="utf-8")
        for path in sorted(SCHEMAS_DIR.glob("*.json"))
    }


#: Named so the meta-test can assert the failure is actionable: a failure
#: nobody can act on is a failure that gets muted.
DRIFT_MESSAGE = (
    "The committed docs/schemas/ tree no longer matches what the SDK"
    " artifact classes emit. Run `make schemas` and commit the result."
    " A renamed field or a Pydantic version bump legitimately changes what"
    " adopters author against — that diff is reviewable and desirable, not"
    " a test bug."
)


def differences() -> list[str]:
    """Return one human-readable line per drifted, missing, or orphan file."""
    expected = emit()
    on_disk = committed()

    problems: list[str] = []
    for path in sorted(set(expected) | set(on_disk)):
        relative = path.relative_to(REPO_ROOT)
        if path not in on_disk:
            problems.append(f"missing: {relative}")
        elif path not in expected:
            problems.append(
                f"orphan: {relative} (no such artifact class in"
                " SDK_ARTIFACT_CLASSES)"
            )
        elif on_disk[path] != expected[path]:
            problems.append(f"drifted: {relative}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Regenerate the committed docs/schemas/ tree from"
            " SDK_ARTIFACT_CLASSES (ERGO-12)."
        )
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Write nothing; exit 1 if any committed schema is missing,"
            " drifted, or orphaned."
        ),
    )
    args = parser.parse_args(argv)

    if args.check:
        problems = differences()
        if problems:
            for problem in problems:
                print(problem, file=sys.stderr)
            print(DRIFT_MESSAGE, file=sys.stderr)
            return 1
        return 0

    expected = emit()
    SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)
    for orphan in set(committed()) - set(expected):
        orphan.unlink()
        print(f"removed {orphan.relative_to(REPO_ROOT)}")
    for path, text in sorted(expected.items()):
        path.write_text(text, encoding="utf-8")
    print(f"wrote {len(expected)} schemas to {SCHEMAS_DIR.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
