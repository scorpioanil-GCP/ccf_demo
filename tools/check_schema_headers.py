"""ERGO-12 — verify the ``$schema`` headers on artifact documents are *right*.

A ``# yaml-language-server: $schema=...`` header is an editor hint, and an
editor hint has a failure mode no runtime has: it can be wrong for months
and nothing breaks, because nothing reads it except the adopter's editor —
which will happily point at a real file describing the wrong class and
annotate the document with confident nonsense. Existence of the target is
therefore not the property worth gating. Correctness is.

Four things are checked per document, and each one closes a way a header
can be wrong while looking right:

1. **The header is there, on the first line.** A header buried below a
   comment block still works in some editors and not others; requiring the
   first line makes "does this document have one" a one-line answer for a
   reviewer as well as for this tool.
2. **The target resolves from the document's own directory.** Editors
   resolve ``$schema`` relative to the file being edited, not to the repo
   root, so a header that only resolves when a test happens to run from the
   repo root is a header that is broken in the only place it is used. This
   is checked by resolving against the YAML file's parent, exactly as an
   editor does.
3. **The schema describes the class the file is annotated as.** The target
   must live in the committed ``docs/schemas/`` tree and carry an
   ``x-ccf-class-id`` (written by ``tools/dump_schemas.py``) that both names
   a real SDK artifact class and matches the file name. Reading the class id
   out of the *document* rather than off the path is what makes this a
   check rather than a restatement of the path.
4. **The class actually accepts the document.** The named class's contract
   is run over the parsed YAML through the SDK's own
   :func:`~ccf.controlplane.artifacts.load_artifact`. This is the strongest
   available form of "the header is correct", and it needs no new
   dependency: the validator an adopter's fabric will use at boot is the
   validator the header is checked against.

And when the directory carries a ``ccf.deployment-manifest``, one further
cross-check runs: every entry's declared ``class_id`` must equal the class
id in the header of the file at its ``path``. The manifest and the header
are two independent statements of the same fact, authored in two different
files, and this is the assertion that they agree.

Deferred documents
------------------

A document that is not yet a single typed artifact — a multi-artifact
bundle awaiting its split — cannot carry an honest header: pointing it at
any one class annotates every key belonging to the others as an error, so
the "hint" would be a wall of false positives in the adopter's editor.
Those documents carry a ``# ccf-schema: deferred(<plan>) <reason>`` first
line instead. The exemption is explicit, greppable, names who closes it,
and is *counted* — a file with neither a header nor a deferral marker
fails, so nothing falls through the gate silently.

Usage
-----

``python tools/check_schema_headers.py [DIR ...]`` checks the named
directories, or — with no arguments — every ``examples/**/artifacts``
directory that already carries at least one header or deferral marker. That
default is what lets each example-rewrite plan arm its own gate at its own
wave: the moment a rewrite writes its first header, its directory joins the
checked set, and a broken header fails at that wave rather than at the
phase's tree-wide close.

``--require-all`` drops the auto-arming and demands that every discovered
directory be fully annotated. That is the tree-wide form for the phase
close, when no directory is allowed to be unannotated any more.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

#: The exact first-line prefix an annotated artifact document carries.
HEADER_PREFIX = "# yaml-language-server: $schema="

#: The exact first-line prefix a deliberately-unannotated document carries.
DEFERRED_PREFIX = "# ccf-schema: deferred"

#: Where the committed schemas live, relative to the repo root.
SCHEMAS_DIRNAME = "schemas"


def _display(path: pathlib.Path) -> pathlib.Path:
    """Repo-relative for readability, absolute when outside the repo.

    The tool's own tests write documents under ``tmp_path``, which is not
    under the repo root; a bare ``relative_to`` would raise there and turn
    a reported problem into a crash.
    """
    try:
        return path.relative_to(REPO_ROOT)
    except ValueError:
        return path


def _first_line(path: pathlib.Path) -> str:
    with path.open(encoding="utf-8") as handle:
        return handle.readline().rstrip("\n")


def header_class_id(path: pathlib.Path) -> str | None:
    """Return the class id a document's header names, or ``None``.

    ``None`` means the document carries no ``$schema`` header at all — the
    caller distinguishes "deferred" from "missing", because those are
    different failures.
    """
    line = _first_line(path)
    if not line.startswith(HEADER_PREFIX):
        return None
    target = line[len(HEADER_PREFIX) :].strip()
    resolved = (path.parent / target).resolve()
    if not resolved.is_file():
        return None
    try:
        document = json.loads(resolved.read_text(encoding="utf-8"))
    except ValueError:
        return None
    class_id = document.get("x-ccf-class-id")
    return class_id if isinstance(class_id, str) else None


def check_document(path: pathlib.Path) -> list[str]:
    """Return one problem line per way this document's header is wrong."""
    from ccf.controlplane.artifacts import ArtifactLoadError, load_artifact
    from ccf.deployment.classes import SDK_ARTIFACT_CLASSES

    from tools.dump_schemas import CLASS_ID_KEY, schema_path

    relative = _display(path)
    line = _first_line(path)

    if line.startswith(DEFERRED_PREFIX):
        if "(" not in line or ")" not in line:
            return [
                f"{relative}: deferral marker names no closing plan; write"
                f" `{DEFERRED_PREFIX}(<plan>) <reason>`"
            ]
        return []

    if not line.startswith(HEADER_PREFIX):
        return [
            f"{relative}: no `{HEADER_PREFIX}` first line and no"
            f" `{DEFERRED_PREFIX}(<plan>)` marker — an artifact document is"
            " either annotated or explicitly deferred, never neither"
        ]

    target = line[len(HEADER_PREFIX) :].strip()
    if not target:
        return [f"{relative}: `$schema=` names nothing"]

    # Resolved from the document's own directory, exactly as an editor
    # resolves it — a repo-root-relative path that only works under pytest
    # is broken in the only place the header is actually read.
    resolved = (path.parent / target).resolve()
    if not resolved.is_file():
        return [
            f"{relative}: `$schema={target}` does not resolve to a file from"
            f" {relative.parent} (editors resolve it from the document's own"
            " directory, not from the repo root)"
        ]

    try:
        schema = json.loads(resolved.read_text(encoding="utf-8"))
    except ValueError as unparseable:
        return [f"{relative}: `$schema={target}` is not JSON: {unparseable}"]

    class_id = schema.get(CLASS_ID_KEY)
    if not isinstance(class_id, str):
        return [
            f"{relative}: `$schema={target}` carries no {CLASS_ID_KEY}, so"
            " nothing states which artifact class it describes; point the"
            " header at a committed docs/schemas/ file"
        ]

    artifact_class = SDK_ARTIFACT_CLASSES.get(class_id)
    if artifact_class is None:
        return [
            f"{relative}: `$schema={target}` describes {class_id!r}, which is"
            " not an SDK artifact class"
        ]

    if resolved != schema_path(class_id).resolve():
        return [
            f"{relative}: `$schema={target}` is annotated {class_id!r} but is"
            f" not that class's committed schema file"
            f" ({_display(schema_path(class_id))})"
        ]

    try:
        load_artifact(path.read_text(encoding="utf-8"), artifact_class)
    except ArtifactLoadError as rejected:
        return [
            f"{relative}: the header names {class_id!r} but that class does"
            f" not accept this document: {rejected}"
        ]

    return []


def _manifest_problems(directory: pathlib.Path) -> list[str]:
    """Cross-check every manifest entry against the header of its file."""
    from ccf.controlplane.artifacts import (
        DEPLOYMENT_MANIFEST,
        ArtifactLoadError,
        load_artifact,
    )

    manifest_path = directory / "manifest.yaml"
    if not manifest_path.is_file():
        return []
    try:
        manifest = load_artifact(
            manifest_path.read_text(encoding="utf-8"), DEPLOYMENT_MANIFEST
        )
    except ArtifactLoadError:
        # Not this tool's failure to report: the manifest's own contract
        # test says what is wrong with it, in its own words.
        return []

    problems: list[str] = []
    for entry in getattr(manifest, "artifacts", ()):
        entry_path = (directory / entry.path).resolve()
        if not entry_path.is_file():
            continue
        annotated = header_class_id(entry_path)
        if annotated is None:
            continue
        if annotated != entry.class_id:
            problems.append(
                f"{_display(entry_path)}: the manifest declares"
                f" class {entry.class_id!r} and the `$schema` header names"
                f" {annotated!r} — two statements of one fact that disagree"
            )
    return problems


def check_directory(directory: pathlib.Path) -> list[str]:
    """Return every problem in one artifact directory."""
    problems: list[str] = []
    for path in sorted(directory.glob("*.yaml")):
        problems.extend(check_document(path))
    problems.extend(_manifest_problems(directory))
    return problems


def discover(require_all: bool) -> list[pathlib.Path]:
    """Return the artifact directories to check.

    Auto-arming by default: a directory joins the checked set as soon as it
    carries its first header or deferral marker. ``require_all`` returns
    every artifact directory regardless, which is the tree-wide form.
    """
    directories = sorted(
        {
            path.parent
            for path in REPO_ROOT.glob("examples/**/artifacts/*.yaml")
        }
    )
    if require_all:
        return directories
    armed = []
    for directory in directories:
        for path in sorted(directory.glob("*.yaml")):
            line = _first_line(path)
            if line.startswith(HEADER_PREFIX) or line.startswith(
                DEFERRED_PREFIX
            ):
                armed.append(directory)
                break
    return armed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that artifact documents' $schema headers name the class"
            " that actually accepts them (ERGO-12)."
        )
    )
    parser.add_argument(
        "directories",
        nargs="*",
        help="artifact directories to check (default: auto-armed set)",
    )
    parser.add_argument(
        "--require-all",
        action="store_true",
        help=(
            "check every examples/**/artifacts directory, armed or not —"
            " the tree-wide form for the phase close"
        ),
    )
    args = parser.parse_args(argv)

    directories = (
        [pathlib.Path(name).resolve() for name in args.directories]
        if args.directories
        else discover(args.require_all)
    )

    problems: list[str] = []
    for directory in directories:
        if not directory.is_dir():
            problems.append(f"{directory}: not a directory")
            continue
        problems.extend(check_directory(directory))

    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        print(
            "Fix the headers above, or mark a not-yet-typed document"
            f" `{DEFERRED_PREFIX}(<plan>) <reason>`. Run"
            " `make schema-headers` to re-check.",
            file=sys.stderr,
        )
        return 1

    print(f"checked {len(directories)} artifact directories")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
