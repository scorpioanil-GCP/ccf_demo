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
import json
import pathlib
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

#: The committed schema tree — the ERGO-12 authoring baseline.
SCHEMAS_DIR = REPO_ROOT / "docs" / "schemas"

#: JSON Schema extension key carrying the CCF artifact class id.
CLASS_ID_KEY = "x-ccf-class-id"


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
    """Return the full committed tree as ``path -> serialized bytes``."""
    from ccf.deployment.classes import SDK_ARTIFACT_CLASSES

    documents: dict[pathlib.Path, str] = {}
    for class_id, artifact_class in SDK_ARTIFACT_CLASSES.items():
        document: dict[str, Any] = artifact_class.contract.model_json_schema()
        document[CLASS_ID_KEY] = class_id
        documents[schema_path(class_id)] = serialize(document)
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
