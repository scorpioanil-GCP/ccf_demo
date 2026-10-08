"""ERGO-12, tree-wide — the `$schema` header gate at the point every delegate landed.

Plan 15-12 added `$schema` headers to `archive/examples/00-quickstart/artifacts/` only
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

How coverage is pinned, and why it changed in phase 16 (plan 16-02)
-------------------------------------------------------------------

Coverage used to be a **literal named tuple** of the ten artifact directories
that existed at the Phase 15 close, asserted for exact equality against what
the tool discovered. That was the right answer to the hole cross-AI review
raised at that close — an *aggregate floor* lets a directory drop out of
coverage silently while the count stays above it — but it does not survive
phase 16, for a structural reason rather than a stylistic one: the phase
rewrites the examples suite, and plans 16-08, 16-09, 16-10 and 16-11 each
create an example directory **in wave 4, in parallel**. Four concurrent
appends to one constant is a merge conflict by construction. The gate has to
arm on a new example without a source edit, or four plans collide.

So coverage is now a **two-sided bijection** against the examples that exist:

* An **example root** is *a directory that directly contains a file named*
  ``run.py``. Mechanical, checkable, and depth-agnostic — which matters,
  because ``archive/examples/external/00-hello-context`` is at depth 2 and does carry
  ``artifacts/``, so "top-level directories under ``examples/``" would wrongly
  exclude it. The looser predicate "a directory under ``examples/`` containing
  a ``.py``" is *false against this tree*: 12 directories satisfy it and only
  10 carry ``artifacts/``. The two that do not — and the reason the loose
  predicate would make this gate unbuildable — are
  ``archive/examples/03-harness-portability/legs/`` and
  ``archive/examples/external/00-hello-context/fixtures/``, each all-``.py`` and no
  ``artifacts/``. A control below asserts both are excluded, and asserts the
  same for ``fixtures/`` **as a shape**, which is what keeps the rule true
  when plan 16-09 ships its own fixtures directory at wave 4.
* **Left side:** every example root has an ``artifacts/`` directory the gate
  covers.
* **Right side:** every covered ``artifacts/`` directory sits directly under
  an example root.
* Both directions are reported **by name**, on the
  ``tools/docs_tests/test_diagram_coverage.py`` model.
* **Per-directory non-vacuity** replaces the aggregate hundred-document floor
  the previous version carried. That floor has to go regardless of the
  bijection: it was fed by 216 documents across ten directories that are
  almost all retiring in this phase, the five-directory suite that replaces
  them cannot be assumed to reach it, and a floor nobody can meet is a gate
  that gets weakened at the worst possible moment. A per-directory floor is
  also strictly stronger than an aggregate one, which can be satisfied by a
  single fat directory while every other directory is empty.

**Why this does not reopen the silent-drop hole.** The hole was a property of
a *floor*: a count can stay above a threshold while a member leaves the set. A
bijection has no floor and no count. For a directory to leave coverage here,
its example must stop being an example — every ``run.py`` in it must vanish —
and that is loud in four other places:

1. ``make examples``, which runs each example by path and fails on the first
   missing one;
2. the Makefile's ``examples:`` target list, which names each example
   explicitly;
3. ``tools/docs_tests/test_documented_commands_exist.py``, whose
   both-directions assertion ties documented commands to the tree (shipped by
   plan 16-04, in this same wave);
4. ``tools/retirement_sweep.py``, the repo-wide coupling sweep (shipped by
   plan 16-21, in this same wave).

Naming them is what makes that argument checkable rather than asserted. Two of
the four land alongside this module rather than before it, which is stated
here so a reader at this commit is not left hunting for a file that has not
arrived yet.

Controls
--------

A gate nobody has watched fail is a gate that may be scanning nothing, so
three controls run below: the bijection is shown **refusing in each
direction** against a synthetic tree, the two real ``.py``-bearing
non-example directories are shown **excluded**, and a scratch example is
shown **collected without any edit to this module** — which is the property
the four wave-4 plans depend on.

The exemption, and why the tree now carries exactly one
-------------------------------------------------------

The plan text names ``# no-schema: DeclaredArtifact`` as the single permitted
exemption. **That marker does not exist in the tooling** and never did — 15-16
and 15-17 both recorded hitting it. The implemented mechanism is
``# ccf-schema: deferred(<plan>) <reason>``: explicit, greppable, and *counted*,
so a file with neither a header nor a marker fails rather than falling through.

At the phase close exactly one document carries it, and it is a **permanent**
exemption rather than debt (ruled by 15-16):
``archive/examples/08-e2e-demo/artifacts/scenario.yaml`` is `generator.py`'s input,
describing the synthetic world that exists before any fabric does, and it
carries YAML floats the artifact loader refuses by design — no envelope can
accept it without changing the data and every pinned checksum with it.

:data:`PERMANENTLY_DEFERRED` stays a **named** set, deliberately, and is not
reshaped the way coverage was. It is edited by exactly one plan (16-18, which
deletes its only member's file), so it carries no concurrency problem and
loses nothing by staying named: adding a second deferral remains a deliberate
edit to this list with a reason, never a quiet widening.
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

if str(REPO_ROOT) not in sys.path:  # the tools/ package is not installed
    sys.path.insert(0, str(REPO_ROOT))

from tools.check_schema_headers import (  # noqa: E402
    ARTIFACT_GLOBS,
    DEFERRED_PREFIX,
    check_directory,
    discover,
)

#: The tree the bijection closes over.
EXAMPLES_ROOT = REPO_ROOT / "examples"

#: The archive Phase 23 retires ten example trees into (`D-03` pins the path).
#: It does not exist yet when this constant is introduced; every consumer below
#: therefore filters on :func:`present_roots`, so the widening is a strict
#: no-op until the move lands.
ARCHIVE_EXAMPLES_ROOT = REPO_ROOT / "archive" / "examples"

#: Every root this module walks. **The gate must reach both.** Measured on the
#: pre-move tree, 216 artifact documents in the ten condemned trees carry a
#: `$schema` header, and after the move every one of them needs an extra `../`.
#: With the walk narrow, `tools/check_schema_headers.py::discover` finds
#: nothing in the archive and the gate reports CLEAN over 216 rotten headers
#: while producing only 2 failures — the "reports clean because it did not
#: look" defect, arriving inside the phase written to prevent it.
GATED_EXAMPLE_ROOTS: tuple[pathlib.Path, ...] = (
    EXAMPLES_ROOT,
    ARCHIVE_EXAMPLES_ROOT,
)


def present_roots() -> tuple[pathlib.Path, ...]:
    """The gated roots that exist on disk right now.

    ``archive/`` is absent before Phase 23's move and ``examples/`` will still
    exist after it, so filtering here is what lets the roots be widened ahead
    of the move without a single assertion changing result.
    """
    return tuple(root for root in GATED_EXAMPLE_ROOTS if root.is_dir())

#: The mechanical example-root predicate: a directory that *directly* contains
#: a file with this name. See the module docstring for why it is this and not
#: "a directory containing a ``.py``" or "a top-level directory".
EXAMPLE_ROOT_MARKER = "run.py"

#: The directory name an example's Control Plane artifacts live under.
ARTIFACTS_DIRNAME = "artifacts"

#: The two directories in the tree at phase 16 wave 2 that carry ``.py``
#: modules and no ``artifacts/`` — the counter-examples that make the
#: ``run.py`` predicate load-bearing rather than incidental. Each maps to the
#: wave that retires it, so the control below degrades to a *named* skip
#: instead of turning red once its subject is gone: a control that outlives
#: its subject is a coupling of exactly the class ``tools/retirement_sweep.py``
#: exists to find.
PY_BEARING_NON_EXAMPLES: dict[str, str] = {
    "archive/examples/03-harness-portability/legs": (
        "deleted, whenever that is ruled. Plan 16-17 was named here as the"
        " retiring wave; `D-IMPL-152` retired Phase 16, and phase 23 MOVED this"
        " directory to the archive (plan 23-04) rather than deleting it, so the"
        " skip below fires only on a deletion `D-27`'s undecided half has yet"
        " to authorise"
    ),
    "archive/examples/external/00-hello-context/fixtures": (
        "deleted, whenever that is ruled. Plan 16-18 was named here as the"
        " retiring wave; `D-IMPL-152` retired Phase 16, and phase 23 MOVED this"
        " directory to the archive (plan 23-04) rather than deleting it, so the"
        " skip below fires only on a deletion `D-27`'s undecided half has yet"
        " to authorise"
    ),
}

#: The only documents permitted to carry a deferral marker at the phase close,
#: with the ruling that permits each. See the module docstring.
PERMANENTLY_DEFERRED: dict[str, str] = {
    "archive/examples/08-e2e-demo/artifacts/scenario.yaml": (
        "not a CCF artifact class at all — generator.py's input, and it carries"
        " YAML floats the artifact loader refuses by design (15-16, ruled"
        " permanent rather than debt)"
    ),
}


# ---------------------------------------------------------------------------
# The two sides of the bijection, each computed over an arbitrary tree so the
# controls can exercise them against a synthetic one.
# ---------------------------------------------------------------------------


def example_roots(tree: pathlib.Path) -> set[pathlib.Path]:
    """Every example root under ``tree``.

    An example root is a directory that *directly* contains
    :data:`EXAMPLE_ROOT_MARKER`. This is the same set as
    ``find examples -name "run.py" -printf "%h\\n" | sort -u``.
    """
    return {
        path.parent
        for path in tree.rglob(EXAMPLE_ROOT_MARKER)
        if path.is_file()
    }


def covered_artifact_directories(tree: pathlib.Path) -> set[pathlib.Path]:
    """Every ``artifacts/`` directory the header gate covers under ``tree``.

    Mirrors ``tools.check_schema_headers.discover``'s glob, parameterized on
    the root so a control can run it over ``tmp_path``. The precondition
    below asserts the two agree on the real tree — otherwise this module
    would be gating a different set than the tool checks.
    """
    return {
        path.parent
        for path in tree.glob(f"**/{ARTIFACTS_DIRNAME}/*.yaml")
    }


def bijection_violations(
    tree: pathlib.Path,
) -> tuple[list[str], list[str]]:
    """Return ``(uncovered roots, orphaned artifact directories)``, by name."""
    roots = example_roots(tree)
    covered = covered_artifact_directories(tree)
    uncovered = sorted(
        str(root.relative_to(tree))
        for root in roots
        if (root / ARTIFACTS_DIRNAME) not in covered
    )
    orphaned = sorted(
        str(directory.relative_to(tree))
        for directory in covered
        if directory.parent not in roots
    )
    return uncovered, orphaned


def all_example_roots() -> set[pathlib.Path]:
    """Every example root under every gated root that exists.

    The union, so a control asserting "this directory is NOT an example root"
    keeps meaning that after the archive move relocates the directory. Asserting
    against ``EXAMPLES_ROOT`` alone would make such a control silently vacuous
    the day its subject moved into the archive.
    """
    found: set[pathlib.Path] = set()
    for root in present_roots():
        found |= example_roots(root)
    return found


def all_covered_artifact_directories() -> set[pathlib.Path]:
    """Every covered ``artifacts/`` directory under every gated root."""
    found: set[pathlib.Path] = set()
    for root in present_roots():
        found |= covered_artifact_directories(root)
    return found


def _artifact_documents() -> list[pathlib.Path]:
    found: list[pathlib.Path] = []
    for pattern in ARTIFACT_GLOBS:
        found.extend(REPO_ROOT.glob(pattern))
    return sorted(found)


# ---------------------------------------------------------------------------
# Preconditions — a vacuous pass is the failure this module exists to prevent.
# ---------------------------------------------------------------------------


def test_the_example_tree_is_populated() -> None:
    """Both sides of the bijection are non-empty.

    Without this, a renamed or moved ``examples/`` tree would make every
    assertion below pass over empty sets — which is the exact failure mode a
    coverage gate is supposed to be immune to.
    """
    assert EXAMPLES_ROOT.is_dir(), f"missing example tree: {EXAMPLES_ROOT}"
    assert present_roots(), "no gated example root exists on disk at all"
    for root in present_roots():
        assert example_roots(root), (
            f"no `{EXAMPLE_ROOT_MARKER}` found anywhere under {root} — the"
            " example-root predicate collects nothing there, so the bijection"
            " below would close over an empty set for that root"
        )
        assert covered_artifact_directories(root), (
            f"no `{ARTIFACTS_DIRNAME}/*.yaml` found under {root}"
        )


def test_this_module_gates_the_same_set_the_tool_checks() -> None:
    """The local glob and ``discover(require_all=True)`` agree.

    :func:`covered_artifact_directories` re-expresses the tool's glob so a
    control can point it at ``tmp_path``. Re-expressing it is a second
    definition, and two definitions of one set eventually disagree — so they
    are compared here rather than trusted.
    """
    local = sorted(
        str(path.relative_to(REPO_ROOT))
        for path in all_covered_artifact_directories()
    )
    tool = sorted(
        str(path.relative_to(REPO_ROOT)) for path in discover(require_all=True)
    )
    assert local == tool, (
        "this module's artifact-directory glob and"
        " `tools/check_schema_headers.py`'s have diverged; the gate would be"
        f" covering a different set than the tool checks. local={local}"
        f" tool={tool}"
    )


# ---------------------------------------------------------------------------
# The bijection.
# ---------------------------------------------------------------------------


def test_every_example_root_has_a_covered_artifact_directory() -> None:
    """Left side: an example without covered artifacts is an example the gate cannot see."""
    uncovered = [
        name for root in present_roots() for name in bijection_violations(root)[0]
    ]
    assert not uncovered, (
        "example roots (directories directly containing"
        f" `{EXAMPLE_ROOT_MARKER}`) with no covered `{ARTIFACTS_DIRNAME}/`"
        " directory — their artifact headers are checked by nothing: "
        + ", ".join(uncovered)
    )


def test_every_covered_artifact_directory_sits_under_an_example_root() -> None:
    """Right side: a covered directory under no example root is coverage of a ghost."""
    orphaned = [
        name for root in present_roots() for name in bijection_violations(root)[1]
    ]
    assert not orphaned, (
        f"covered `{ARTIFACTS_DIRNAME}/` directories whose parent is not an"
        f" example root (no `{EXAMPLE_ROOT_MARKER}` beside them) — either the"
        " example lost its driver or the directory is in the wrong place: "
        + ", ".join(orphaned)
    )


def test_every_example_roots_artifact_directory_is_non_vacuous() -> None:
    """Per-directory floor, replacing the aggregate document floor.

    Computed **by name from the example root** rather than from the document
    glob, so it states the property at the point where it must hold rather
    than restating how the covered set was derived. Under today's
    ``discover`` an empty ``artifacts/`` directory also fails the left side;
    stating it separately is what keeps the property true if that derivation
    ever changes to enumerate directories by name.

    The aggregate floor it replaces could be satisfied by one fat directory
    while every other example shipped nothing. This one cannot.
    """
    empty = sorted(
        str(root.relative_to(REPO_ROOT))
        for root in all_example_roots()
        if not sorted((root / ARTIFACTS_DIRNAME).glob("*.yaml"))
    )
    assert not empty, (
        "example roots whose `artifacts/` directory holds no document, so the"
        " header check runs over nothing for them: " + ", ".join(empty)
    )


#: D-IMPL-378 C5 (Dave, 2026-10-07 21:18 MST; confirmed 2026-10-08 04:07 MST).
#: Two archived trees carry documents today's SDK refuses on purpose:
#: `hitl-policy.yaml` under SEC-005 (D-IMPL-363) and `scope-mapping.yaml` under
#: D-IMPL-353. D-IMPL-351 makes `archive/` a dated reference surface with no
#: fixes, so each is a STRICT expected failure: the gate keeps running both, the
#: day one passes CI goes red, and `raises=AssertionError` reports any other error.
_ARCHIVED_REASON = (
    "D-IMPL-351: archived tree; its hitl-policy.yaml omits the signature bounds SEC-005"
    " (D-IMPL-363) requires and its scope-mapping.yaml lacks scopes.hitl.resource_patterns"
    " (D-IMPL-353); quarantined, D-IMPL-261; D-IMPL-378 C5"
)
ARCHIVED_HEADER_REFUSALS: dict[str, str] = {
    "archive/examples/05-workflow-hitl/artifacts": _ARCHIVED_REASON,
    "archive/examples/06-decision-replay/artifacts": _ARCHIVED_REASON,
}


def _header_check_params() -> list[Any]:
    params = []
    for path in discover(require_all=True):
        relative = str(path.relative_to(REPO_ROOT))
        reason = ARCHIVED_HEADER_REFUSALS.get(relative)
        marks = [pytest.mark.xfail(strict=True, raises=AssertionError, reason=reason)] if reason else []
        params.append(pytest.param(path, id=relative, marks=marks))
    return params


@pytest.mark.parametrize("directory", _header_check_params())
def test_every_artifact_directory_passes_the_header_check(
    directory: pathlib.Path,
) -> None:
    """The tree-wide form of `make schema-headers --require-all`.

    Parametrized per directory rather than run as one call so a failure names
    the example that broke rather than handing back a wall of problems from
    every directory at once.
    """
    problems = check_directory(directory)
    assert not problems, "\n".join(problems)


# ---------------------------------------------------------------------------
# Controls. A gate nobody has watched fail may be scanning nothing.
# ---------------------------------------------------------------------------


def test_the_bijection_refuses_an_example_root_with_no_artifacts(
    tmp_path: pathlib.Path,
) -> None:
    """Control, left direction: a driver with no artifacts beside it is named."""
    root = tmp_path / "zz-driver-only"
    root.mkdir()
    (root / EXAMPLE_ROOT_MARKER).write_text("", encoding="utf-8")

    uncovered, orphaned = bijection_violations(tmp_path)
    assert uncovered == ["zz-driver-only"], uncovered
    assert orphaned == [], orphaned


def test_the_bijection_refuses_an_artifact_directory_under_no_example_root(
    tmp_path: pathlib.Path,
) -> None:
    """Control, right direction: a covered directory under no driver is named."""
    stray = tmp_path / "zz-orphan" / ARTIFACTS_DIRNAME
    stray.mkdir(parents=True)
    (stray / "x.yaml").write_text("", encoding="utf-8")

    uncovered, orphaned = bijection_violations(tmp_path)
    assert uncovered == [], uncovered
    assert orphaned == [f"zz-orphan/{ARTIFACTS_DIRNAME}"], orphaned


def test_a_new_example_is_collected_without_editing_this_module(
    tmp_path: pathlib.Path,
) -> None:
    """Control: the gate arms on a new example directory with no source edit.

    This is the property the four wave-4 plans (16-08, 16-09, 16-10, 16-11)
    depend on. Under the literal named tuple this module used to carry, each
    of them would have had to append its own entry to one constant, in
    parallel — a merge conflict by construction.
    """
    probe = tmp_path / "zz-probe"
    (probe / ARTIFACTS_DIRNAME).mkdir(parents=True)
    (probe / EXAMPLE_ROOT_MARKER).write_text("", encoding="utf-8")
    (probe / ARTIFACTS_DIRNAME / "x.yaml").write_text("", encoding="utf-8")

    assert example_roots(tmp_path) == {probe}
    assert covered_artifact_directories(tmp_path) == {
        probe / ARTIFACTS_DIRNAME
    }
    assert bijection_violations(tmp_path) == ([], [])


@pytest.mark.parametrize("relative", sorted(PY_BEARING_NON_EXAMPLES))
def test_the_predicate_excludes_the_py_bearing_non_examples(
    relative: str,
) -> None:
    """Control: a directory of `.py` modules with no `artifacts/` is not an example.

    Asserted against the live tree, because the point is that these two
    directories really exist and really would break a looser predicate. Once
    the wave that retires each has run, the control degrades to a named skip
    rather than turning red.
    """
    directory = REPO_ROOT / relative
    if not directory.is_dir():
        pytest.skip(f"{relative}: {PY_BEARING_NON_EXAMPLES[relative]}")
    assert sorted(directory.glob("*.py")), (
        f"{relative} carries no `.py` module, so it is no longer the"
        " counter-example this control exists to exclude"
    )
    assert directory not in all_example_roots(), (
        f"{relative} was collected as an example root; the predicate has"
        f" loosened from `{EXAMPLE_ROOT_MARKER}` to something that catches"
        " support directories"
    )


def test_the_predicate_excludes_fixtures_directories_as_a_shape() -> None:
    """Control: no `fixtures/` directory is ever an example root.

    Asserted as a shape rather than by path. The sentence here used to justify
    that by a `fixtures/` directory plan 16-09 was going to ship at wave 4;
    that plan was withdrawn with Phase 16 (`docs/DECISIONS.md` `D-IMPL-152`)
    and the example it would have landed in has since been retired out of
    `examples/` altogether, so the directory never existed and never will. The
    justification is unchanged and does not depend on it: a shape rule holds
    for the NEXT `fixtures/` directory an example ships, and
    `archive/examples/external/00-hello-context/fixtures/` is the live one it already
    excludes.
    """
    collected = sorted(
        str(root.relative_to(REPO_ROOT))
        for root in all_example_roots()
        if root.name == "fixtures"
    )
    assert not collected, (
        "a `fixtures/` directory was collected as an example root: "
        + ", ".join(collected)
    )


# ---------------------------------------------------------------------------
# The single-file-config boundary, stated rather than left to look like a gap.
# ---------------------------------------------------------------------------

#: Examples whose whole Control Plane configuration is ONE document
#: (``D-IMPL-136``'s AMENDMENT: the section name IS the class), so they carry no
#: ``artifacts/`` directory and are deliberately outside the bijection above.
SINGLE_FILE_CONFIG_EXAMPLES: tuple[str, ...] = (
    "examples/hw1-companies-over-revenue",
)


@pytest.mark.parametrize("relative", SINGLE_FILE_CONFIG_EXAMPLES)
def test_a_single_file_config_example_is_outside_the_bijection(
    relative: str,
) -> None:
    """The boundary is a decision, and this is where it is written down.

    Plan ``17-09`` was written to widen :data:`EXAMPLE_ROOT_MARKER` from the
    ``run.py`` filename to a property — "a directory directly under
    ``examples/`` holding a module with an ``if __name__`` guard" — so that the
    client example became visible here. **Measured, that widening cannot hold**,
    and the measurement is recorded rather than the widening:

    * The bijection's left side requires every example root to own a covered
      ``artifacts/`` directory. A ``D-IMPL-136`` example has none *by design*:
      its whole Control Plane configuration is one ``ccf_config.yaml``.
      Collecting it would therefore fail
      :func:`test_every_example_root_has_a_covered_artifact_directory`
      immediately — a red check bought by a widening, not a defect found.
    * Redirecting the covered set at ``deployment/*.yaml`` instead is worse.
      Running ``tools.check_schema_headers.check_directory`` over this
      example's ``deployment/`` reports ``binding.yaml`` and ``scenario.yaml``
      as unannotated artifact documents. **Neither is an artifact.**
      ``binding.yaml`` is deployment-environment material that is never
      registered and never content-hashed (``D-IMPL-141``), and
      ``scenario.yaml`` is the deployment's own vocabulary. Giving either an
      artifact schema header would make the document assert something false to
      satisfy a checker.
    * ``examples/s1-00-companies-over-revenue`` — the same shape, and the
      document this example's config was recovered from — is **already**
      outside this gate today for exactly this reason. The exclusion is the
      shipped precedent, not a new hole.

    So this test asserts the boundary instead of hiding it: the example exists,
    it carries a single-file config, and it owns no ``artifacts/`` directory.
    The day somebody gives it one, this turns red and the decision above gets
    re-made on purpose.
    """
    root = REPO_ROOT / relative
    assert root.is_dir(), f"{relative} is missing"
    assert (root / "deployment" / "ccf_config.yaml").is_file(), (
        f"{relative} no longer carries a single-file Control Plane config, so"
        " the reason it sits outside this gate no longer applies"
    )
    assert not (root / ARTIFACTS_DIRNAME).exists(), (
        f"{relative} has grown an `{ARTIFACTS_DIRNAME}/` directory. It was"
        " excluded from the bijection because a `D-IMPL-136` single-file"
        " config has none; now that it has one, widen the example-root"
        " predicate to collect it and delete this test"
    )
    assert root not in all_example_roots(), (
        f"{relative} is now collected as an example root but owns no"
        f" `{ARTIFACTS_DIRNAME}/`, so the bijection's left side cannot hold"
    )


# ---------------------------------------------------------------------------
# The gated roots. A walk that does not reach a tree reports clean over it.
# ---------------------------------------------------------------------------


def test_the_gated_roots_are_the_live_tree_and_the_archive() -> None:
    """Membership of the walked root set, asserted rather than counted.

    ``23-RESEARCH.md`` finding **S-16** in this module's own terms. Nothing here
    is a floor any more — the bijection replaced the aggregate document
    floor — but the same blindness applies to a root set: swapping
    ``EXAMPLES_ROOT`` for ``ARCHIVE_EXAMPLES_ROOT`` leaves the bijection closing
    perfectly over the archived trees while the surviving examples stop being
    gated, and every assertion in this module stays green.

    Asserted by set equality, so a root ADDED without review fails here too.
    """
    assert set(GATED_EXAMPLE_ROOTS) == {EXAMPLES_ROOT, ARCHIVE_EXAMPLES_ROOT}, (
        "the gated root set changed. A root removed here stops a whole tree"
        " being header-checked with no assertion in this module able to say so."
    )
    assert EXAMPLES_ROOT in GATED_EXAMPLE_ROOTS
    assert ARCHIVE_EXAMPLES_ROOT in GATED_EXAMPLE_ROOTS


def test_the_discovery_globs_reach_the_live_tree_and_the_archive() -> None:
    """The tool's own root set, which is the one that decides what is read.

    This module's root set and
    ``tools/check_schema_headers.py::ARTIFACT_GLOBS`` are two statements of one
    thing, and :func:`test_this_module_gates_the_same_set_the_tool_checks`
    compares what they *find*. **When this was written in plan ``23-03`` the
    archive did not yet exist, so that comparison was satisfied by both being
    blind to it at once — which is why the membership is asserted directly as
    well.** The archive exists now (plan ``23-04`` moved ten trees into it, and
    ``discover(require_all=True)`` returns 10 archived artifact directories
    against 1 live one), so the two-blind-at-once case is historical rather
    than current. The direct membership assertion stays: a *future* narrowing
    would re-create exactly that state, and the comparison alone would not say
    so.
    """
    assert set(ARTIFACT_GLOBS) == {
        f"examples/**/{ARTIFACTS_DIRNAME}/*.yaml",
        f"archive/examples/**/{ARTIFACTS_DIRNAME}/*.yaml",
    }, (
        "the tool's artifact-discovery globs changed. Narrowing them is how the"
        " header gate goes SILENT rather than red: measured on the pre-move"
        " tree, 216 documents in the ten condemned trees carry a `$schema`"
        " header, and a walk that does not reach them reports clean over every"
        " one."
    )


def test_the_discovery_finds_an_archived_artifact_directory(
    tmp_path: pathlib.Path,
) -> None:
    """The widening proven by BEHAVIOUR, against a synthetic tree.

    Asserting the glob strings alone would only prove the glob is what it is.
    ``discover`` takes a ``base`` so a control can point it at ``tmp_path``,
    exactly as :func:`covered_artifact_directories` is parameterized on its
    tree and for the same stated reason — and that is what makes this a control
    rather than a restatement.

    Both roots are planted, and both must be found: a widening that reached the
    archive by *losing* the live tree would satisfy a one-sided check.
    """
    for relative in (
        f"examples/live-example/{ARTIFACTS_DIRNAME}",
        f"archive/examples/retired-example/{ARTIFACTS_DIRNAME}",
    ):
        directory = tmp_path / relative
        directory.mkdir(parents=True)
        (directory / "thing.yaml").write_text("a: 1\n", encoding="utf-8")

    found = sorted(
        str(path.relative_to(tmp_path))
        for path in discover(require_all=True, base=tmp_path)
    )
    assert found == [
        f"archive/examples/retired-example/{ARTIFACTS_DIRNAME}",
        f"examples/live-example/{ARTIFACTS_DIRNAME}",
    ], found


def test_the_discovery_ignores_an_artifact_directory_outside_both_roots(
    tmp_path: pathlib.Path,
) -> None:
    """The widening is a widening, not an opening.

    ``archive/`` bare is not a root: only ``archive/examples/`` is, matching the
    narrow spelling plan ``23-02`` chose for the publication allowlist. A
    ``tests/`` or ``archive/scratch/`` directory of YAML is not artifact
    material and must stay outside the gate.
    """
    for relative in (
        f"archive/scratch/{ARTIFACTS_DIRNAME}",
        f"tests/fixtures/{ARTIFACTS_DIRNAME}",
    ):
        directory = tmp_path / relative
        directory.mkdir(parents=True)
        (directory / "thing.yaml").write_text("a: 1\n", encoding="utf-8")

    assert discover(require_all=True, base=tmp_path) == []


# ---------------------------------------------------------------------------
# The exemption set, which stays named.
# ---------------------------------------------------------------------------


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


def test_every_quarantined_archive_directory_is_still_discovered() -> None:
    """A quarantine entry whose directory left the discovery marks nothing, and
    would hide that the gate's population changed (D-IMPL-378 C5)."""
    discovered = {str(path.relative_to(REPO_ROOT)) for path in discover(require_all=True)}
    assert set(ARCHIVED_HEADER_REFUSALS) <= discovered, sorted(set(ARCHIVED_HEADER_REFUSALS) - discovered)
