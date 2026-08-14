"""Criterion 6's structural half — the spine and the deployment stay apart.

Phase 16 CONTEXT `D-11` answers a reader's complaint in the reader's own words:
*"I can't tell from looking at the code which code is example code and which
code is required by the CCF."* The answer is two files rather than a docs-layer
legend — ``spine.py`` holds every call the fabric requires and ``deployment.py``
holds everything the adopter writes — and the seven Phase 14 `D-07` marker
regions are how the spine's steps are named.

**What this module proves, and what it cannot.** It proves the markers are
present, canonical, ordered, closed, and confined to one module. It does not
prove a reader can *see* which code is CCF's and which is theirs — that is a
human read, it is the plan's blocking checkpoint, and no assertion substitutes
for it. Stating the boundary here keeps the structural check from being mistaken
for the whole of criterion 6.

**Scope: ``examples/s1-*``, by glob.** Section 1 is where the fabric is shown
without an agent in front of it, and the split is Section 1's shape — every
Section-1 example carries it, so plan 16-08's second example arms these
assertions by existing rather than by being listed. Section 2 and 3 examples are
out of scope here; ``examples/00-quickstart/run.py`` carries the same seven
marker names in a single module, which is the pre-`D-11` shape this one replaces
and deliberately not a violation of it.

**`D-11` adds no marker vocabulary.** The seven names below are Phase 14's, and
the closure check is as load-bearing as the ordering one: a suite that grows an
eighth marker per example has gone back to an editorial answer.
"""

from __future__ import annotations

import pathlib
import re
import shutil

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The tree the scan walks. An argument everywhere below, so the negative
#: controls can repoint it at a copy and exercise the real predicates.
EXAMPLES_ROOT = REPO_ROOT / "examples"

#: Section 1 by directory-name convention, and a glob rather than a list.
SECTION_ONE_GLOB = "s1-*"

#: The module that must carry the spine. Named, because "the file with the
#: markers in it" would let a rename pass silently — and a renamed spine is
#: exactly the drift criterion 6 is about.
SPINE_MODULE = "spine.py"

#: The presentation module (plan 16-05). A THIRD category beside the spine and
#: the deployment: what the run prints. Named for the same reason the spine is
#: — a reader looks for it by name — and gated separately, because the property
#: that matters about it is the opposite one: it must carry no canonical
#: region, so that not one printed line is publication surface.
REPORT_MODULE = "report.py"

#: The modules that print, and the modules that must not. `spine.py` is the CCF
#: call spine and `deployment.py` is the adopter's own fabric-facing code;
#: neither writes to a terminal. The driver does, which is what makes the
#: example's output a property of the deployment rather than of the fabric.
SILENT_MODULES = (SPINE_MODULE, "deployment.py")
PRINTING_MODULE = "run.py"

#: How a module writes to the terminal, in the two forms this repository uses.
PRINT_RE = re.compile(r"print\(|sys\.stdout\.write")

#: The seven `D-07` names, in the order the fabric is called in. Ordered, so
#: this is a sequence rather than a set: a spine that gates before it projects
#: is not a spine a beginner can read.
CANONICAL_MARKERS: tuple[str, ...] = (
    "boot",
    "ingest",
    "operators",
    "project",
    "gate",
    "record",
    "serve",
)

#: The pymdownx.snippets marker form, as the published site reads it.
MARKER_RE = re.compile(r"--8<--\s*\[(?P<kind>start|end):(?P<name>[^\]]+)\]")


# ---------------------------------------------------------------------------
# Reading the tree.
# ---------------------------------------------------------------------------


def split_examples(root: pathlib.Path) -> list[pathlib.Path]:
    """Every Section-1 example directory under `root`."""
    return sorted(path for path in root.glob(SECTION_ONE_GLOB) if path.is_dir())


def modules_in(directory: pathlib.Path) -> list[pathlib.Path]:
    """Every Python module in one example directory, at any depth."""
    return sorted(directory.rglob("*.py"))


def markers(path: pathlib.Path) -> list[tuple[str, str]]:
    """``(kind, name)`` for every marker in the file, in file order."""
    text = path.read_text(encoding="utf-8")
    return [
        (match.group("kind"), match.group("name").strip())
        for match in MARKER_RE.finditer(text)
    ]


def opened(path: pathlib.Path) -> tuple[str, ...]:
    """The names the file opens a region for, in the order it opens them."""
    return tuple(name for kind, name in markers(path) if kind == "start")


def unbalanced(path: pathlib.Path) -> list[str]:
    """Why the file's markers do not pair up, if they do not.

    Regions must open, close, and not interleave — a region left open by the
    end of the file, or closed without being opened, or opened while another is
    still open, publishes a snippet whose extent nobody authored.
    """
    problems: list[str] = []
    open_name: str | None = None
    for kind, name in markers(path):
        if kind == "start":
            if open_name is not None:
                problems.append(
                    f"[start:{name}] opens while [start:{open_name}] is still open"
                )
            open_name = name
        elif open_name is None:
            problems.append(f"[end:{name}] closes a region that was never opened")
        elif open_name != name:
            problems.append(f"[end:{name}] closes [start:{open_name}]")
            open_name = None
        else:
            open_name = None
    if open_name is not None:
        problems.append(f"[start:{open_name}] is never closed")
    return problems


def spine_problems(directory: pathlib.Path) -> list[str]:
    """Every way one example directory fails the separation contract.

    A single predicate over a directory, so the shipped tree and the injected
    copies below are judged by the same code rather than by two descriptions of
    the same intent.
    """
    problems: list[str] = []
    spine = directory / SPINE_MODULE
    if not spine.is_file():
        return [f"no {SPINE_MODULE} in {directory.name}"]

    if opened(spine) != CANONICAL_MARKERS:
        problems.append(
            f"{SPINE_MODULE} opens {opened(spine)}, expected {CANONICAL_MARKERS}"
        )
    problems.extend(f"{SPINE_MODULE}: {problem}" for problem in unbalanced(spine))

    for module in modules_in(directory):
        if module == spine:
            continue
        shared = sorted(set(opened(module)) & set(CANONICAL_MARKERS))
        if shared:
            problems.append(
                f"{module.name} also opens canonical region(s) {shared} —"
                f" a region spanning {SPINE_MODULE} and a sibling"
            )
        problems.extend(f"{module.name}: {problem}" for problem in unbalanced(module))
    return problems


# ---------------------------------------------------------------------------
# Preconditions — a vacuous pass is the failure this module exists to prevent.
# ---------------------------------------------------------------------------


def test_the_section_one_tree_is_populated() -> None:
    """Without this, a renamed ``examples/s1-*`` makes every check below pass
    over an empty set of directories."""
    assert EXAMPLES_ROOT.is_dir(), f"missing examples tree: {EXAMPLES_ROOT}"
    assert split_examples(EXAMPLES_ROOT), (
        f"no Section-1 example directories under {EXAMPLES_ROOT} — the"
        " separation gate is scanning nothing"
    )
    for directory in split_examples(EXAMPLES_ROOT):
        assert modules_in(directory), f"{directory.name} contains no Python module"


def test_the_marker_pattern_matches_the_shipped_form() -> None:
    """The regex is checked against a marker the suite actually ships.

    A pattern that matched nothing would make every assertion below vacuous,
    and the probe form is the one ``tools/docs_tests/test_snippet_gate.py``
    uses: look for the literal a source file contains.
    """
    spine = split_examples(EXAMPLES_ROOT)[0] / SPINE_MODULE
    assert f"[start:{CANONICAL_MARKERS[0]}]" in spine.read_text(encoding="utf-8")
    assert markers(spine), f"{spine} contains markers the pattern does not match"


# ---------------------------------------------------------------------------
# The separation.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "directory",
    split_examples(EXAMPLES_ROOT),
    ids=lambda path: path.name,
)
def test_every_section_one_example_ships_a_spine_module(
    directory: pathlib.Path,
) -> None:
    """The spine is a named file, not "whichever file has the markers"."""
    assert (directory / SPINE_MODULE).is_file(), (
        f"{directory.name} has no {SPINE_MODULE}. Section 1's shape is the CCF"
        " call spine in one module and the adopter's own code in another"
        " (phase 16 CONTEXT D-11, criterion 6)."
    )


@pytest.mark.parametrize(
    "directory",
    split_examples(EXAMPLES_ROOT),
    ids=lambda path: path.name,
)
def test_the_spine_opens_the_seven_canonical_regions_in_order(
    directory: pathlib.Path,
) -> None:
    """Both directions reported by name: what is missing and what is extra.

    Ordering is asserted as well as membership. The seven names are a
    decomposition a beginner is meant to be able to follow top to bottom, and a
    spine that records before it gates reads as a different story.
    """
    found = opened(directory / SPINE_MODULE)
    missing = [name for name in CANONICAL_MARKERS if name not in found]
    extra = [name for name in found if name not in CANONICAL_MARKERS]
    assert not missing, f"{directory.name}/{SPINE_MODULE} opens no region for {missing}"
    assert not extra, (
        f"{directory.name}/{SPINE_MODULE} opens {extra}, which is marker"
        " vocabulary outside the seven D-07 names — D-11 adds none"
    )
    assert found == CANONICAL_MARKERS, (
        f"{directory.name}/{SPINE_MODULE} opens the seven regions in order"
        f" {found}, expected {CANONICAL_MARKERS}"
    )


@pytest.mark.parametrize(
    "directory",
    split_examples(EXAMPLES_ROOT),
    ids=lambda path: path.name,
)
def test_every_region_the_spine_opens_it_closes(directory: pathlib.Path) -> None:
    """Opened, closed, and never interleaved."""
    problems = unbalanced(directory / SPINE_MODULE)
    assert not problems, f"{directory.name}/{SPINE_MODULE}: " + "; ".join(problems)


@pytest.mark.parametrize(
    "directory",
    split_examples(EXAMPLES_ROOT),
    ids=lambda path: path.name,
)
def test_no_region_spans_the_spine_and_a_sibling_module(
    directory: pathlib.Path,
) -> None:
    """A canonical region belongs to exactly one module.

    A region opened in ``spine.py`` and closed in ``deployment.py`` would
    publish a snippet straddling the boundary this example exists to draw — and
    would mean the boundary is not where the markers say it is.
    """
    spine = directory / SPINE_MODULE
    for module in modules_in(directory):
        if module == spine:
            continue
        shared = sorted(set(opened(module)) & set(CANONICAL_MARKERS))
        assert not shared, (
            f"{directory.name}/{module.name} opens canonical region(s)"
            f" {shared}, which belong to {SPINE_MODULE}"
        )
        problems = unbalanced(module)
        assert not problems, f"{directory.name}/{module.name}: " + "; ".join(problems)


@pytest.mark.parametrize(
    "directory",
    split_examples(EXAMPLES_ROOT),
    ids=lambda path: path.name,
)
def test_the_shipped_example_satisfies_the_whole_contract(
    directory: pathlib.Path,
) -> None:
    """The aggregate predicate, over the shipped tree.

    Same code path the negative controls exercise, so a control that passed
    against a predicate this tree does not satisfy is impossible.
    """
    problems = spine_problems(directory)
    assert not problems, f"{directory.name}: " + "; ".join(problems)


@pytest.mark.parametrize(
    "directory",
    split_examples(EXAMPLES_ROOT),
    ids=lambda path: path.name,
)
def test_every_section_one_example_ships_a_report_module(
    directory: pathlib.Path,
) -> None:
    """Presentation is a named third file, not a habit of the driver.

    Dave's ruling of 2026-08-13 is that the example prints its work. Where the
    printing LIVES is what keeps that compatible with the Phase 14.1 finding
    that print lines inside published snippets inflate an example's apparent
    integration cost: a separate module, carrying no region, is not snippet
    surface. A report folded back into the driver or the spine would be.
    """
    assert (directory / REPORT_MODULE).is_file(), (
        f"{directory.name} has no {REPORT_MODULE}. Section 1's shape is three"
        " files: the fabric's calls, the adopter's code, and what the run"
        " prints."
    )


@pytest.mark.parametrize(
    "directory",
    split_examples(EXAMPLES_ROOT),
    ids=lambda path: path.name,
)
def test_the_report_module_opens_no_canonical_region(
    directory: pathlib.Path,
) -> None:
    """Not one printed line is publication surface.

    The sibling rule already refuses a canonical region outside the spine; this
    states the property for the module it exists to protect, so the reason is
    on the record beside the assertion rather than only in a plan.
    """
    report = directory / REPORT_MODULE
    shared = sorted(set(opened(report)) & set(CANONICAL_MARKERS))
    assert not shared, f"{directory.name}/{REPORT_MODULE} opens {shared}"
    assert not unbalanced(report), unbalanced(report)


@pytest.mark.parametrize(
    "directory",
    split_examples(EXAMPLES_ROOT),
    ids=lambda path: path.name,
)
def test_the_fabric_facing_modules_stay_silent_and_the_driver_prints(
    directory: pathlib.Path,
) -> None:
    """Which side of the split writes to a terminal, asserted.

    Always-on and substrate-free by construction — it reads files. Both halves
    are needed: without the first, printing creeps back into the spine and the
    published snippets grow lines an adopter would never write; without the
    second, this passes just as happily against the silent example the ruling
    of 2026-08-13 rejected.
    """
    for name in SILENT_MODULES:
        module = directory / name
        assert module.is_file(), module
        assert not PRINT_RE.search(module.read_text(encoding="utf-8")), (
            f"{directory.name}/{name} writes to the terminal; presentation"
            f" belongs in {REPORT_MODULE} and printing in {PRINTING_MODULE}"
        )
    driver = directory / PRINTING_MODULE
    assert PRINT_RE.search(driver.read_text(encoding="utf-8")), (
        f"{directory.name}/{PRINTING_MODULE} prints nothing — the example"
        " runs and shows a reader nothing (Dave's ruling, 2026-08-13)"
    )


def test_discovery_is_independent_of_the_working_directory(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every path is resolved from ``__file__``, never from the CWD.

    ``pytest`` is run from the repository root, from ``tests/``, and from a
    worktree by different people and by CI. A gate that only finds its tree
    from one of those is a gate that silently scans nothing from the others.
    """
    before = [path.name for path in split_examples(EXAMPLES_ROOT)]
    monkeypatch.chdir(tmp_path)
    after = [path.name for path in split_examples(EXAMPLES_ROOT)]
    assert before == after and before

    for directory in split_examples(EXAMPLES_ROOT):
        assert not spine_problems(directory), directory.name


# ---------------------------------------------------------------------------
# Negative controls — a structural check that has never refused anything is a
# structural check nobody has tested.
# ---------------------------------------------------------------------------


def _copied_example(tmp_path: pathlib.Path) -> pathlib.Path:
    """The first shipped Section-1 example, copied under a fresh root.

    Copied rather than synthesized so the controls run against the real spine,
    the real markers and the real predicate.
    """
    source = split_examples(EXAMPLES_ROOT)[0]
    destination = tmp_path / source.name
    shutil.copytree(source, destination)
    assert not spine_problems(destination), "the unmodified copy must pass"
    return destination


def test_the_gate_refuses_a_renamed_spine(tmp_path: pathlib.Path) -> None:
    """Renaming ``spine.py`` away is a failure, not a vacuous pass.

    The obvious implementation — "check whichever module carries the markers" —
    would go quiet here, because the renamed file still carries them. The
    contract is that the spine has a name a reader can look for.
    """
    example = _copied_example(tmp_path)
    (example / SPINE_MODULE).rename(example / "assembly.py")

    problems = spine_problems(example)
    assert problems and SPINE_MODULE in problems[0], problems


def test_the_gate_refuses_a_spine_whose_regions_are_out_of_order(
    tmp_path: pathlib.Path,
) -> None:
    """Membership alone is not the contract; the reading order is."""
    example = _copied_example(tmp_path)
    spine = example / SPINE_MODULE
    text = spine.read_text(encoding="utf-8")
    first, last = CANONICAL_MARKERS[0], CANONICAL_MARKERS[-1]
    swapped = (
        text.replace(f"[start:{first}]", "[start:__SWAP__]")
        .replace(f"[start:{last}]", f"[start:{first}]")
        .replace("[start:__SWAP__]", f"[start:{last}]")
        .replace(f"[end:{first}]", "[end:__SWAP__]")
        .replace(f"[end:{last}]", f"[end:{first}]")
        .replace("[end:__SWAP__]", f"[end:{last}]")
    )
    spine.write_text(swapped, "utf-8")

    assert spine_problems(example)


def test_the_gate_refuses_an_unclosed_region(tmp_path: pathlib.Path) -> None:
    """A region left open publishes a snippet whose extent nobody authored.

    The LAST region's close is the one removed. Removing an earlier one is also
    refused, but as an interleaving — the next ``start`` arrives while the
    previous region is still open — and this control is aimed at the case with
    nothing after it to notice.
    """
    example = _copied_example(tmp_path)
    spine = example / SPINE_MODULE
    text = spine.read_text(encoding="utf-8")
    spine.write_text(text.replace(f"[end:{CANONICAL_MARKERS[-1]}]", "", 1), "utf-8")

    assert any("never closed" in problem for problem in spine_problems(example)), (
        spine_problems(example)
    )


def test_the_gate_refuses_marker_vocabulary_outside_the_seven(
    tmp_path: pathlib.Path,
) -> None:
    """`D-11` adds no marker names, and an eighth is how that erodes."""
    example = _copied_example(tmp_path)
    spine = example / SPINE_MODULE
    text = spine.read_text(encoding="utf-8")
    spine.write_text(
        text + "\n# --8<-- [start:extra]\n# --8<-- [end:extra]\n", "utf-8"
    )

    assert spine_problems(example)


def test_the_gate_refuses_a_canonical_marker_in_the_report_module(
    tmp_path: pathlib.Path,
) -> None:
    """The control for the property ``report.py`` exists to hold.

    A canonical region injected into the presentation module would publish a
    printed line as a snippet — the exact cost the Phase 14.1 finding measured.
    The scan root is repointed at the copy so the real predicate runs against a
    real spine and a real report.
    """
    example = _copied_example(tmp_path)
    report = example / REPORT_MODULE
    assert report.is_file(), report
    name = CANONICAL_MARKERS[0]
    report.write_text(
        report.read_text(encoding="utf-8")
        + f"\n# --8<-- [start:{name}]\n# --8<-- [end:{name}]\n",
        "utf-8",
    )

    problems = spine_problems(example)
    assert any(REPORT_MODULE in problem for problem in problems), problems


def test_the_gate_refuses_a_region_that_spans_both_modules(
    tmp_path: pathlib.Path,
) -> None:
    """The spanning case, injected: the spine opens ``serve`` and a sibling
    opens it too, so the region is no longer confined to one side of the
    boundary this example draws."""
    example = _copied_example(tmp_path)
    sibling = next(
        module
        for module in modules_in(example)
        if module.name != SPINE_MODULE
    )
    name = CANONICAL_MARKERS[-1]
    sibling.write_text(
        sibling.read_text(encoding="utf-8")
        + f"\n# --8<-- [start:{name}]\n# --8<-- [end:{name}]\n",
        "utf-8",
    )

    problems = spine_problems(example)
    assert any("spanning" in problem for problem in problems), problems
