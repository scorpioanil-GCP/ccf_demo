"""`EXAM-01`'s second limb — the seven-heading README template, on a LIVE subject.

Phase 13 `D-08`/`D-17` fixed a seven-heading README template for every example,
by exact name and in exact order, and
``archive/examples/external/00-hello-context/run.py::_assert_seven_heading_readme``
enforces it. That enforcement has one property this module exists to correct:
it reads ``_EXAMPLE_ROOT / "README.md"`` where ``_EXAMPLE_ROOT`` is its OWN
directory — **it scans exactly one file, takes no argument, and is not a
glob.** Phase 23 moved that tree under ``archive/``, so since then the template
obligation has reached **no live example at all**. `24-CONTEXT.md` `D-21`
requires the row be RE-POINTED rather than silently inherited, and names the
new target: every ``cp-*`` example.

**This is an ADDITIONAL gate, not a move.** The archived gate keeps guarding
its own README; nothing under ``archive/examples/`` is edited (`D-07` — no
retrofitting — and criterion 17 requires that tree diff-empty). What changes is
that the template now also has a subject somebody is still writing.

**Why the seven names are read by AST rather than imported.** They have ONE
definition —
``archive/examples/external/00-hello-context/run.py::README_HEADINGS`` — and a
hand-copied second one is a second template whose first divergence would be
silent. But that module cannot be imported to reach it: at import time it
resolves ``_REPO_ROOT`` from ``__file__``, mutates ``sys.path``, and then
imports ``httpx``, ``mcp``, ``yaml``, a large slice of ``ccf`` and its own
sibling ``serve`` module — an import graph this gate has no business
executing, and one that would make a template check depend on the MCP client
libraries being installed. So the tuple is read out of the source with
:mod:`ast` and :func:`ast.literal_eval`, which touches no import and runs no
code. :func:`test_the_template_matches_the_readme_the_shipped_gate_guards` is
the control that the tuple so extracted is the one the shipped gate actually
enforces.

**What this module proves, and what it cannot.** It proves every live
``cp-*/README.md`` carries exactly the seven template headings, by name and in
order. It says nothing about what is written UNDER those headings — a README
with seven correct headings and empty sections passes here. Criterion 8's
content obligations are `24.1-08`'s and are checked by that plan's own
assertions; this is the structural half.

**Scope: ``examples/cp-*/README.md``, by glob.** A second Context Product tree
arms this gate by existing.
"""

from __future__ import annotations

import ast
import pathlib
import shutil

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The tree the scan walks. An argument everywhere below, so the negative
#: controls can repoint it at a copy and exercise the real predicate.
EXAMPLES_ROOT = REPO_ROOT / "examples"

#: Context Product examples by directory-name convention, and a glob rather
#: than a list.
README_GLOB = "cp-*/README.md"

#: The single definition of the seven names, read rather than re-typed.
TEMPLATE_SOURCE = (
    REPO_ROOT / "archive" / "examples" / "external" / "00-hello-context" / "run.py"
)

#: The name of the tuple inside that module.
TEMPLATE_SYMBOL = "README_HEADINGS"

#: How a template heading is written. ``"### Foo"`` does not start with
#: ``"## "``, so sub-headings are out of scope — the same reading the shipped
#: predicate takes, deliberately identical so the two gates cannot diverge on
#: what counts as a heading.
HEADING_PREFIX = "## "


# ---------------------------------------------------------------------------
# The template, from its one definition.
# ---------------------------------------------------------------------------


def read_template(source: pathlib.Path = TEMPLATE_SOURCE) -> tuple[str, ...]:
    """The seven template names, extracted from `source` by AST.

    ``ast.literal_eval`` on the assignment's value, so no import runs and no
    code executes. A missing or renamed symbol raises here rather than
    returning an empty tuple, because an empty template would make every
    assertion below vacuous — a README with zero headings would satisfy it.
    """
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == TEMPLATE_SYMBOL
            for target in node.targets
        ):
            continue
        value = ast.literal_eval(node.value)
        return tuple(str(name) for name in value)
    raise AssertionError(
        f"{source} defines no module-level {TEMPLATE_SYMBOL} — the template"
        " moved, and this gate must be re-pointed at its new single definition"
        " rather than given a copy of its own"
    )


#: Resolved once, at import, so a broken extraction fails collection loudly
#: instead of failing each test with the same message.
README_HEADINGS: tuple[str, ...] = read_template()


# ---------------------------------------------------------------------------
# The scan.
# ---------------------------------------------------------------------------


def readmes(root: pathlib.Path) -> list[pathlib.Path]:
    """Every Context Product README under `root`."""
    return sorted(root.glob(README_GLOB))


def headings(readme: pathlib.Path) -> tuple[str, ...]:
    """The ``## `` headings in the file, in file order.

    Line-oriented, matching the shipped predicate. The limitation is stated
    rather than left to be discovered: a line beginning ``## `` inside a fenced
    code block would be counted as a heading. The shipped gate has the same
    reading, and making this one cleverer would mean two gates disagreeing
    about what a heading is.
    """
    return tuple(
        line[len(HEADING_PREFIX) :].strip()
        for line in readme.read_text(encoding="utf-8").splitlines()
        if line.startswith(HEADING_PREFIX)
    )


def template_problems(readme: pathlib.Path) -> list[str]:
    """Every way one README departs from the template, named.

    A single predicate over a file, so the shipped README and the mutated
    copies below are judged by the same code rather than by two descriptions of
    the same intent. Both directions are reported: what is missing and what is
    present but unexpected, each by name, and every positional mismatch by
    POSITION — because "the headings are wrong" is not something an author can
    act on.
    """
    problems: list[str] = []
    found = headings(readme)

    if len(found) != len(README_HEADINGS):
        problems.append(
            f"{readme.name} has {len(found)} {HEADING_PREFIX!r} headings;"
            f" the Phase-13 template requires exactly {len(README_HEADINGS)}"
            f" (found {list(found)})"
        )

    missing = [name for name in README_HEADINGS if name not in found]
    if missing:
        problems.append(f"{readme.name} is missing the heading(s) {missing}")

    extra = [name for name in found if name not in README_HEADINGS]
    if extra:
        problems.append(
            f"{readme.name} carries {extra}, which is heading vocabulary"
            " outside the seven Phase-13 template names — the template adds"
            " none"
        )

    for position, (actual, expected) in enumerate(
        zip(found, README_HEADINGS), start=1
    ):
        if actual != expected:
            problems.append(
                f"{readme.name} heading {position} is {actual!r}; the"
                f" Phase-13 template requires {expected!r} at that position"
                " (D-08/D-17)"
            )
    return problems


# ---------------------------------------------------------------------------
# Preconditions — a vacuous pass is the failure this module exists to prevent.
# ---------------------------------------------------------------------------


def test_the_template_is_seven_names() -> None:
    """The extracted tuple is non-empty and is the seven the template fixes.

    An empty tuple would make a zero-heading README conform. The count is
    asserted rather than the contents, because the contents are the shipped
    module's to define — but a template that silently shrank to one name would
    otherwise pass every assertion below.
    """
    assert README_HEADINGS, f"{TEMPLATE_SOURCE}::{TEMPLATE_SYMBOL} is empty"
    assert len(README_HEADINGS) == 7, README_HEADINGS
    assert len(set(README_HEADINGS)) == 7, (
        f"the template has a repeated name: {README_HEADINGS}"
    )


def test_the_template_matches_the_readme_the_shipped_gate_guards() -> None:
    """The control that the AST extraction recovered the REAL template.

    ``archive/examples/external/00-hello-context/README.md`` is the one file
    the shipped predicate already guards, so if this module's own extraction
    and its own predicate agree that that README conforms, both are the shipped
    ones rather than a plausible re-typing of them. This is what stands in for
    an import of the tuple.

    It reads the archived tree and writes nothing to it (`D-07`, criterion 17).
    """
    archived = TEMPLATE_SOURCE.parent / "README.md"
    assert archived.is_file(), (
        f"{archived} is gone — this control, and the single definition of the"
        " template it verifies, both need re-pointing"
    )
    assert not template_problems(archived), template_problems(archived)


def test_the_context_product_tree_has_a_readme() -> None:
    """The non-vacuity precondition, with the count in the message.

    Without it, a renamed tree makes every check below pass over an empty set —
    the exact failure
    ``tests/examples/test_spine_separation.py::test_the_section_one_tree_is_populated``
    exists for. This is also the assertion that is RED until `24.1-08` writes
    the README, and that RED is the evidence the gate has a live subject rather
    than an archived one.
    """
    assert EXAMPLES_ROOT.is_dir(), f"missing examples tree: {EXAMPLES_ROOT}"

    trees = sorted(path for path in EXAMPLES_ROOT.glob("cp-*") if path.is_dir())
    found = readmes(EXAMPLES_ROOT)
    assert found, (
        f"{len(trees)} Context Product tree(s) {[t.name for t in trees]} and"
        f" {len(found)} README.md matching {README_GLOB!r} under"
        f" {EXAMPLES_ROOT} — the seven-heading template gate is scanning"
        " nothing, which is the state Phase 23 left it in when it moved"
        " archive/examples/external/00-hello-context out of examples/"
    )


# ---------------------------------------------------------------------------
# The gate.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "readme",
    readmes(EXAMPLES_ROOT),
    ids=lambda path: path.relative_to(EXAMPLES_ROOT).as_posix(),
)
def test_every_context_product_readme_matches_the_template(
    readme: pathlib.Path,
) -> None:
    """`EXAM-01` / `D-21`, per README, named in the failure."""
    problems = template_problems(readme)
    assert not problems, f"{readme.relative_to(REPO_ROOT).as_posix()}: " + "; ".join(
        problems
    )


# ---------------------------------------------------------------------------
# Negative controls — a gate that has never refused anything is a gate nobody
# has tested. Two families, and they prove different things.
#
#   * against a SYNTHETIC conforming README — proves the PREDICATE refuses.
#     Green from the day this module lands.
#   * against a copy of the REAL README — proves the predicate refuses the
#     subject it actually guards. RED until `24.1-08` writes that README, and
#     that is the honest ordering rather than a defect.
# ---------------------------------------------------------------------------


def _synthetic_readme(tmp_path: pathlib.Path) -> pathlib.Path:
    """A minimal README built FROM the template tuple, not from a copy of it."""
    readme = tmp_path / "README.md"
    readme.write_text(
        "\n\n".join(f"{HEADING_PREFIX}{name}\n\nbody" for name in README_HEADINGS)
        + "\n",
        "utf-8",
    )
    assert not template_problems(readme), "the unmutated synthetic must pass"
    return readme


def _copied_real_readme(tmp_path: pathlib.Path) -> pathlib.Path:
    """A copy of the FIRST live Context Product README, under a fresh root.

    Copied rather than synthesized so these controls run against the real file.
    Asserted rather than skipped: a skip here would silently disable the only
    controls tied to the live subject, on the day somebody deleted it.
    """
    live = readmes(EXAMPLES_ROOT)
    assert live, (
        f"no README matching {README_GLOB!r} under {EXAMPLES_ROOT} — there is"
        " no live subject to mutate, so this control proves nothing about the"
        " tree this gate guards"
    )
    destination = tmp_path / "README.md"
    shutil.copy(live[0], destination)
    assert not template_problems(destination), (
        f"the unmutated copy of {live[0]} must pass"
    )
    return destination


def _delete_a_heading(readme: pathlib.Path) -> str:
    """Remove the FOURTH heading line, and report which name went."""
    victim = README_HEADINGS[3]
    text = readme.read_text(encoding="utf-8")
    lines = [
        line
        for line in text.splitlines()
        if line.strip() != f"{HEADING_PREFIX}{victim}"
    ]
    readme.write_text("\n".join(lines) + "\n", "utf-8")
    return victim


def _add_an_eighth_heading(readme: pathlib.Path) -> str:
    """Append a heading the template does not name."""
    extra = "What this leaves out"
    readme.write_text(
        readme.read_text(encoding="utf-8") + f"\n{HEADING_PREFIX}{extra}\n\nbody\n",
        "utf-8",
    )
    return extra


def _reorder_two_headings(readme: pathlib.Path) -> tuple[str, str]:
    """Swap the second and third headings, leaving membership intact."""
    second, third = README_HEADINGS[1], README_HEADINGS[2]
    text = (
        readme.read_text(encoding="utf-8")
        .replace(f"{HEADING_PREFIX}{second}", f"{HEADING_PREFIX}__SWAP__")
        .replace(f"{HEADING_PREFIX}{third}", f"{HEADING_PREFIX}{second}")
        .replace(f"{HEADING_PREFIX}__SWAP__", f"{HEADING_PREFIX}{third}")
    )
    readme.write_text(text, "utf-8")
    return second, third


def test_the_predicate_refuses_a_missing_heading(tmp_path: pathlib.Path) -> None:
    """Control 1, synthetic subject — RED, and it NAMES which heading went."""
    readme = _synthetic_readme(tmp_path)
    victim = _delete_a_heading(readme)

    problems = template_problems(readme)
    assert problems, "a README missing a template heading was admitted"
    assert any(victim in problem for problem in problems), problems
    assert any("missing" in problem for problem in problems), problems


def test_the_predicate_refuses_an_eighth_heading(tmp_path: pathlib.Path) -> None:
    """Control 2, synthetic subject — RED.

    An eighth heading fails. That is the shipped predicate's behaviour and it
    is deliberate: a template that tolerates additions is a template that
    stops being one, example by example.
    """
    readme = _synthetic_readme(tmp_path)
    extra = _add_an_eighth_heading(readme)

    problems = template_problems(readme)
    assert problems, "a README with an eighth heading was admitted"
    assert any(extra in problem for problem in problems), problems


def test_the_predicate_refuses_reordered_headings(tmp_path: pathlib.Path) -> None:
    """Control 3, synthetic subject — RED, and it names the POSITION.

    Membership alone is not the contract; the reading order is. This is the
    mutation a set-based check would admit, which is why the predicate zips
    against position rather than comparing sorted collections.
    """
    readme = _synthetic_readme(tmp_path)
    second, third = _reorder_two_headings(readme)

    problems = template_problems(readme)
    assert problems, "a README with reordered headings was admitted"
    assert any("heading 2" in problem for problem in problems), problems
    assert any(second in problem and third in problem for problem in problems), (
        problems
    )


def test_the_gate_refuses_a_missing_heading_in_the_live_readme(
    tmp_path: pathlib.Path,
) -> None:
    """Control 1, LIVE subject — the real README, mutated, through the real
    predicate. RED until `24.1-08` writes it."""
    readme = _copied_real_readme(tmp_path)
    victim = _delete_a_heading(readme)

    problems = template_problems(readme)
    assert problems and any(victim in problem for problem in problems), problems


def test_the_gate_refuses_an_eighth_heading_in_the_live_readme(
    tmp_path: pathlib.Path,
) -> None:
    """Control 2, LIVE subject. RED until `24.1-08` writes the README."""
    readme = _copied_real_readme(tmp_path)
    extra = _add_an_eighth_heading(readme)

    problems = template_problems(readme)
    assert problems and any(extra in problem for problem in problems), problems


def test_the_gate_refuses_reordered_headings_in_the_live_readme(
    tmp_path: pathlib.Path,
) -> None:
    """Control 3, LIVE subject. RED until `24.1-08` writes the README."""
    readme = _copied_real_readme(tmp_path)
    second, third = _reorder_two_headings(readme)

    problems = template_problems(readme)
    assert problems and any("heading 2" in problem for problem in problems), problems
    assert any(second in problem and third in problem for problem in problems), (
        problems
    )
