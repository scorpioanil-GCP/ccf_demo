"""ERGO-12, tree-wide — the `$schema` header gate at the point every delegate landed.

Plan 15-12 added `$schema` headers to `examples/00-quickstart/artifacts/` only
and delegated the rest to the eight example rewrites (15-13 through 15-20). Each
of those plans carries the step and each ran `make schema-headers DIR=…` over
its own directory. A **delegated** requirement needs a gate at the point where
every delegate has landed, which is here: 15-12's own test globs one directory
and cannot see the other nine, so as written ERGO-12 would have been satisfied
for one example out of ten with nothing noticing.

Why this defers to `tools/check_schema_headers.py`
--------------------------------------------------

The plan text for this gate describes a weaker check than the tree already has:
first-line presence plus "the path it names resolves to an existing file under
`docs/schemas/`". `tools/check_schema_headers.py` — shipped by 15-12 and
strengthened through the rewrite waves — already checks four stronger things,
each closing a way a header can be wrong while looking right:

1. the header is on the first line;
2. the target resolves **from the document's own directory**, exactly as an
   editor resolves it, not from the repo root where a test happens to run;
3. the schema carries an ``x-ccf-class-id`` naming a real SDK artifact class,
   read out of the *schema document* rather than off the path;
4. **that class actually accepts the document**, through the SDK's own
   ``load_artifact`` — the validator an adopter's fabric uses at boot.

Plus, for any directory carrying a ``ccf.deployment-manifest``, a cross-check
that every entry's declared ``class_id`` equals the class id in the header of
the file at its ``path`` — two independently authored statements of one fact.

Re-implementing a weaker version here would be a second definition of "the
header is right", and the two would eventually disagree. This module supplies
what the tool does not: **always-on, tree-wide, non-vacuous** execution inside
the `test` job, so the gate cannot be forgotten the way a `make` target can.

The exemption, and why the tree now carries exactly one
-------------------------------------------------------

The plan text names ``# no-schema: DeclaredArtifact`` as the single permitted
exemption. **That marker does not exist in the tooling** and never did — 15-16
and 15-17 both recorded hitting it. The implemented mechanism is
``# ccf-schema: deferred(<plan>) <reason>``: explicit, greppable, and *counted*,
so a file with neither a header nor a marker fails rather than falling through.

At the phase close exactly one document carries it, and it is a **permanent**
exemption rather than debt (ruled by 15-16):
``examples/08-e2e-demo/artifacts/scenario.yaml`` is `generator.py`'s input,
describing the synthetic world that exists before any fabric does, and it
carries YAML floats the artifact loader refuses by design — no envelope can
accept it without changing the data and every pinned checksum with it.

This module therefore pins the exemption set **by name**. Adding a second
deferral is then a deliberate edit to this list with a reason, not a quiet
widening — which is the property the plan text was reaching for with its
"single documented exemption mechanism".
"""

from __future__ import annotations

import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

if str(REPO_ROOT) not in sys.path:  # the tools/ package is not installed
    sys.path.insert(0, str(REPO_ROOT))

from tools.check_schema_headers import (  # noqa: E402
    DEFERRED_PREFIX,
    check_directory,
    discover,
)

#: Ten artifact directories: examples 00–08 plus `examples/external/`. A glob
#: that silently matched fewer is the quietest way this gate stops being one,
#: so the floor is asserted rather than assumed. Nine is the plan's stated
#: floor; the tree carries ten.
MINIMUM_ARTIFACT_DIRECTORIES = 9

#: The only documents permitted to carry a deferral marker at the phase close,
#: with the ruling that permits each. See the module docstring.
PERMANENTLY_DEFERRED: dict[str, str] = {
    "examples/08-e2e-demo/artifacts/scenario.yaml": (
        "not a CCF artifact class at all — generator.py's input, and it carries"
        " YAML floats the artifact loader refuses by design (15-16, ruled"
        " permanent rather than debt)"
    ),
}


def _artifact_documents() -> list[pathlib.Path]:
    return sorted(REPO_ROOT.glob("examples/**/artifacts/*.yaml"))


def test_the_glob_covers_every_example_artifact_directory() -> None:
    """Non-vacuity, in both dimensions: directories and documents."""
    directories = discover(require_all=True)
    assert len(directories) >= MINIMUM_ARTIFACT_DIRECTORIES, [
        str(path.relative_to(REPO_ROOT)) for path in directories
    ]
    documents = _artifact_documents()
    assert len(documents) >= 100, len(documents)


@pytest.mark.parametrize(
    "directory",
    discover(require_all=True),
    ids=lambda path: str(path.relative_to(REPO_ROOT)),
)
def test_every_artifact_directory_passes_the_header_check(
    directory: pathlib.Path,
) -> None:
    """The tree-wide form of `make schema-headers --require-all`.

    Parametrized per directory rather than run as one call so a failure names
    the example that broke rather than handing back a wall of problems from
    ten directories at once.
    """
    problems = check_directory(directory)
    assert not problems, "\n".join(problems)


def test_the_only_deferred_documents_are_the_ruled_permanent_ones() -> None:
    """The exemption cannot widen without an edit to this module.

    A deferral marker is the one way a document escapes the header check. At
    the phase close the escape set is closed and named, so the gate's coverage
    is a property of this list rather than of whatever happens to be on disk.
    """
    deferred = sorted(
        str(path.relative_to(REPO_ROOT))
        for path in _artifact_documents()
        if path.read_text(encoding="utf-8")
        .splitlines()[0]
        .startswith(DEFERRED_PREFIX)
    )
    assert deferred == sorted(PERMANENTLY_DEFERRED), (
        "the set of documents carrying a `ccf-schema: deferred` marker is not"
        f" the ruled-permanent set. Found {deferred}; permitted"
        f" {sorted(PERMANENTLY_DEFERRED)}. A new deferral is a deliberate"
        " addition here with a reason, never a quiet widening."
    )


def test_every_permanently_deferred_document_still_exists() -> None:
    """An exemption for a vanished file is an exemption that silently grew."""
    for relative in PERMANENTLY_DEFERRED:
        assert (REPO_ROOT / relative).is_file(), relative
