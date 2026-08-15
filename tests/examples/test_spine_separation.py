"""Criterion 6's structural half — the spine and the deployment stay apart.

Phase 16 CONTEXT `D-11` answers a reader's complaint in the reader's own words:
*"I can't tell from looking at the code which code is example code and which
code is required by the CCF."* The answer is a split between the module that
carries the fabric's call spine and everything else the adopter writes, with
the seven Phase 14 `D-07` marker regions naming the spine's steps. The split
is discovered from content, not declared by a filename: the spine is
whichever module opens the seven canonical regions, a property a rename
cannot break. `D-11`'s complaint and the seven `D-07` names are unchanged by
that — this module changed how the spine is *found*, not what it *is*.

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
marker names in a single module, which is the pre-`D-11` shape this one
replaces. It was never inside the `s1-*` glob these checks scan, so it is not a
carve-out from a rule this module enforces — the checks below simply never see
it.

**`D-11` adds no marker vocabulary.** The seven names below are Phase 14's, and
the closure check is as load-bearing as the ordering one: a suite that grows an
eighth marker per example has gone back to an editorial answer.

**P5/P6 — the printing properties — are not in this module yet.** Which
modules print and which stay silent is a separate contract that arrives in a
follow-up change; nothing below is written to assert it until then.
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

#: How a module writes to the terminal, in the two forms this repository uses.
PRINT_RE = re.compile(r"print\(|sys\.stdout\.write")

#: How a module declares itself part of the fabric. The taxonomy applies to
#: modules that make CCF calls, because this gate is about how fabric calls
#: separate from adopter code — a module making none is not party to that
#: separation. `examples/s1-00/scenario/provision.py` fabricates a Postgres
#: source system, imports no `ccf`, prints, and says `THIS IS NOT CCF` in its
#: own docstring; it is out of scope by that principle rather than by name.
#:
#: **This governs the PRINTING properties only.** The region properties scan
#: every module: a `--8<--` region in a module importing no `ccf` is still
#: published-snippet surface, and scoping it would make such a marker invisible.
CCF_IMPORT_RE = re.compile(r"^[ \t]*(?:from|import)[ \t]+ccf\b", re.MULTILINE)

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


def fabric_facing(directory: pathlib.Path) -> list[pathlib.Path]:
    """Every module in the example that makes CCF calls."""
    return [
        module
        for module in modules_in(directory)
        if CCF_IMPORT_RE.search(module.read_text(encoding="utf-8"))
    ]


def region_modules(directory: pathlib.Path) -> list[pathlib.Path]:
    """Every module opening at least one of the seven canonical regions.

    Over ALL modules, not the fabric-facing ones — see `CCF_IMPORT_RE`.
    """
    return [
        module
        for module in modules_in(directory)
        if set(opened(module)) & set(CANONICAL_MARKERS)
    ]


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


def region_report(spine: pathlib.Path) -> tuple[tuple[str, ...], list[str], list[str]]:
    """What the spine opens, and how it differs from the seven canonical names.

    One derivation, two readers: `spine_problems` reports it as part of the
    aggregate, and the P2 test reports each direction separately. Written twice
    it drifted in wording before it shipped, which is the argument for a
    predicate rather than a repetition — the same argument `opened`,
    `unbalanced` and `spine_problems` already make in this module.
    """
    found = opened(spine)
    return (
        found,
        [name for name in CANONICAL_MARKERS if name not in found],
        [name for name in found if name not in CANONICAL_MARKERS],
    )


def spine_problems(directory: pathlib.Path) -> list[str]:
    """Every way one example directory fails the separation contract.

    A single predicate over a directory, so the shipped tree and the injected
    copies below are judged by the same code rather than by two descriptions of
    the same intent. The properties, and which modules each scans:

    * P1/P4 — exactly one module opens canonical regions (ALL modules)
    * P2 — that module opens the seven `D-07` names, in order (that module)
    * P3 — every region it opens, it closes; none interleave (ALL modules)

    P5 and P6 are the printing properties and live in `print_problems`.
    """
    problems: list[str] = []
    carriers = region_modules(directory)
    if not carriers:
        return [
            f"{directory.name}: no module opens any of the seven canonical"
            f" regions {CANONICAL_MARKERS}. Section 1's shape is the CCF call"
            " spine in one module and the adopter's own code in another"
            " (phase 16 CONTEXT D-11, criterion 6) — the spine is whichever"
            " module carries the regions, and this example has none."
        ]
    if len(carriers) > 1:
        problems.append(
            f"{directory.name}: more than one module opens canonical regions"
            f" ({[module.name for module in carriers]}). A canonical region"
            " belongs to exactly one module; a region spanning two publishes a"
            " snippet straddling the boundary this example exists to draw."
        )

    spine = carriers[0]
    found, missing, extra = region_report(spine)
    if missing:
        problems.append(f"{spine.name} opens no region for {missing}")
    if extra:
        problems.append(
            f"{spine.name} opens {extra}, which is marker vocabulary outside"
            " the seven D-07 names — D-11 adds none"
        )
    if not missing and not extra and found != CANONICAL_MARKERS:
        problems.append(
            f"{spine.name} opens the seven regions in order {found},"
            f" expected {CANONICAL_MARKERS}"
        )

    for module in modules_in(directory):
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
    spine = region_modules(split_examples(EXAMPLES_ROOT)[0])[0]
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
def test_exactly_one_module_carries_the_canonical_regions(
    directory: pathlib.Path,
) -> None:
    """P1 and P4, stated from both ends.

    The spine is whichever module carries the seven regions — a property a
    reader can check by opening the files, and one a rename cannot break. The
    previous form named `spine.py`, which made `D-IMPL-127`'s `produce.py` a
    failure while every property it claimed to prove held.
    """
    carriers = region_modules(directory)
    assert carriers, (
        f"{directory.name}: no module opens any canonical region"
    )
    assert len(carriers) == 1, (
        f"{directory.name}: {[module.name for module in carriers]} each open"
        " canonical regions; exactly one module must"
    )


@pytest.mark.parametrize(
    "directory",
    split_examples(EXAMPLES_ROOT),
    ids=lambda path: path.name,
)
def test_the_spine_opens_the_seven_canonical_regions_in_order(
    directory: pathlib.Path,
) -> None:
    """P2 — both directions reported by name: what is missing and what is extra.

    Ordering is asserted as well as membership. The seven names are a
    decomposition a beginner is meant to be able to follow top to bottom, and a
    spine that records before it gates reads as a different story.
    """
    spine = region_modules(directory)[0]
    found, missing, extra = region_report(spine)
    assert not missing, f"{directory.name}/{spine.name} opens no region for {missing}"
    assert not extra, (
        f"{directory.name}/{spine.name} opens {extra}, which is marker"
        " vocabulary outside the seven D-07 names — D-11 adds none"
    )
    assert found == CANONICAL_MARKERS, (
        f"{directory.name}/{spine.name} opens the seven regions in order"
        f" {found}, expected {CANONICAL_MARKERS}"
    )


@pytest.mark.parametrize(
    "directory",
    split_examples(EXAMPLES_ROOT),
    ids=lambda path: path.name,
)
def test_every_region_opened_anywhere_is_closed(directory: pathlib.Path) -> None:
    """P3 — opened, closed, and never interleaved, in every module."""
    for module in modules_in(directory):
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


def test_the_gate_refuses_an_example_with_no_region_carrying_module(
    tmp_path: pathlib.Path,
) -> None:
    """Zero carriers is a refusal, not a vacuous pass.

    This is the direction the deleted rename control used to cover. Renaming a
    module is now legal by design, so the property that replaces it is that
    SOME module carries the seven regions — which a rename cannot break and a
    deletion can.
    """
    example = _copied_example(tmp_path)
    spine = region_modules(example)[0]
    text = spine.read_text(encoding="utf-8")
    for name in CANONICAL_MARKERS:
        text = text.replace(f"[start:{name}]", "").replace(f"[end:{name}]", "")
    spine.write_text(text, "utf-8")

    problems = spine_problems(example)
    assert any("no module opens" in problem for problem in problems), problems


def test_the_gate_refuses_a_second_module_carrying_canonical_regions(
    tmp_path: pathlib.Path,
) -> None:
    """A canonical region belongs to exactly one module, whatever it is called.

    Injected into a module that is NOT fabric-facing, because the region
    properties scan every module: a marker in a module importing no `ccf` still
    publishes a snippet, and scoping the region check would make it invisible.
    """
    example = _copied_example(tmp_path)
    carrier = region_modules(example)[0]
    outsiders = [
        module for module in modules_in(example) if module not in fabric_facing(example)
    ]
    # A non-fabric-facing module when the example has one, because that is the
    # case the scope rule could hide; any sibling otherwise.
    sibling = outsiders[0] if outsiders else next(
        module for module in modules_in(example) if module != carrier
    )
    name = CANONICAL_MARKERS[-1]
    sibling.write_text(
        sibling.read_text(encoding="utf-8")
        + f"\n# --8<-- [start:{name}]\n# --8<-- [end:{name}]\n",
        "utf-8",
    )

    problems = spine_problems(example)
    assert any("more than one module" in problem for problem in problems), problems


def test_the_gate_refuses_a_spine_whose_regions_are_out_of_order(
    tmp_path: pathlib.Path,
) -> None:
    """Membership alone is not the contract; the reading order is."""
    example = _copied_example(tmp_path)
    spine = region_modules(example)[0]
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
    spine = region_modules(example)[0]
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
    spine = region_modules(example)[0]
    text = spine.read_text(encoding="utf-8")
    spine.write_text(
        text + "\n# --8<-- [start:extra]\n# --8<-- [end:extra]\n", "utf-8"
    )

    assert spine_problems(example)
