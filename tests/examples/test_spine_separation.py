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

**Scope: ``examples/s1-*`` AND ``examples/cp-*``, by glob** (`SPINE_GLOBS`).
Section 1 is where the fabric is shown without an agent in front of it, and the
split is Section 1's shape — every Section-1 example carries it, so plan
16-08's second example arms these assertions by existing rather than by being
listed.

**Why ``cp-*`` joined the scan** (`24-CONTEXT.md` `D-21`/`D-23`, criterion 15).
The split this module enforces is not really a Section-1 property; it is a
property of any example whose code is PUBLISHED. The site's ``--8<--``
includes address the seven canonical regions by name, so a tree that publishes
snippets must carry the same shape or the page has nothing to include — and a
region that straddles two modules, or a ``print`` inside one, is snippet
surface an adopter would never write, whichever section the tree belongs to.
Context Product examples publish, so they are in.

**Section 2 and 3 examples do not exist and never will** (`24-CONTEXT.md`
`D-20`: the `sN-` scheme is not revived). ``archive/examples/00-quickstart/run.py``
carries the same seven marker names in a single module, which is the pre-`D-11`
shape this one replaces. It was never inside the globs these checks scan, so it
is not a carve-out from a rule this module enforces — the checks below simply
never see it.

**What ``cp-*`` does NOT inherit.** There are two ``s1-*`` globs in this suite
and they enforce different things.
``tests/examples/test_section_one_is_agent_free.py`` is the other one, and it
is **deliberately not widened** — a Context Product tree implements
``ccf.agents.assembler::ContextAssemblerProtocol``, which that gate's deny list
bans. The reason is written into that file (`D-24`) so a reader arriving here
and widening for consistency finds it before doing so.

**`D-11` adds no marker vocabulary.** The seven names below are Phase 14's, and
the closure check is as load-bearing as the ordering one: a suite that grows an
eighth marker per example has gone back to an editorial answer.

**P5/P6 — the printing properties.** Which modules print and which stay
silent is a separate contract from P1–P4, scoped to fabric-facing modules
only (see `CCF_IMPORT_RE`): exactly one fabric-facing module prints, the
module carrying the canonical regions is not it, and the scope exclusion is
itself controlled so it cannot silently swallow the whole check.
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

#: The trees this gate scans, by directory-name convention, as globs rather
#: than a list — so a second Section-1 or Context Product example arms these
#: assertions by existing rather than by being added here.
#:
#: **Renamed from `SECTION_ONE_GLOB` when `cp-*` joined it** (`24-CONTEXT.md`
#: `D-21`/`D-23`, criterion 15). The gate no longer scans Section 1, and a
#: constant whose name says otherwise is the next reader's wrong premise —
#: which is the same failure mode `D-24` guards against in
#: `tests/examples/test_section_one_is_agent_free.py`.
SPINE_GLOBS: tuple[str, ...] = ("s1-*", "cp-*")

#: The Context Product tree criterion 15's control selects. **By NAME, never by
#: index.** `split_examples(...)[0]` is a moving target — widening the glob
#: changed which tree it resolves to — and a control written against `[0]` can
#: silently drift onto a tree it was not written for while staying green, which
#: leaves the criterion unproven and looking proven.
CONTEXT_PRODUCT_EXAMPLE = "cp-00-institutional-holders"

#: The tree that ships a printing module importing no `ccf`
#: (`scenario/provision.py`). The fabric-facing scope control needs THAT file
#: and no other, so it too selects by name — the same reason.
PROVISIONING_EXAMPLE = "s1-00-companies-over-revenue"

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


def is_pre_build(directory: pathlib.Path) -> bool:
    """Is this tree an authored specification with no implementation yet?

    `spec_generation.md` §2 makes a Context Product spec **step one of the
    example project**, authored at `examples/cp-NN-<slug>/spec/` and approved by
    Dave **before any implementation exists**. So a tree carrying a `spec/` and
    no Python at all is a legitimate, intended state — Gate 1 — and it has no
    spine because nothing has been built for a spine to live in.

    **The exclusion is deliberately narrow: `spec/` present AND zero `.py` files
    at any depth.** One module anywhere puts the tree back in scope. The
    dangerous direction here is a rule that skips whatever it cannot parse — a
    shipped example that lost its spine would then leave the scan silently, and
    this gate would report green over the defect it exists to catch. Requiring
    *total* absence of code is what keeps the exclusion unable to do that, and
    `test_the_pre_build_exclusion_releases_a_tree_that_has_any_code` is the
    control that proves it.
    """
    return (directory / "spec").is_dir() and not modules_in(directory)


def split_examples(root: pathlib.Path) -> list[pathlib.Path]:
    """Every example directory under `root` that this gate scans.

    The union of `SPINE_GLOBS`, de-duplicated: a tree matching two globs is one
    tree, and a directory appearing twice would run every parametrized check
    twice and report a copy of each failure.

    **Pre-build trees are excluded** — see `is_pre_build`. A Gate-1 spec is not
    an example that publishes snippets, and the seven canonical regions cannot
    be asserted against code nobody has written.
    """
    return sorted(
        {
            path
            for glob in SPINE_GLOBS
            for path in root.glob(glob)
            if path.is_dir() and not is_pre_build(path)
        }
    )


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


def printing_modules(directory: pathlib.Path) -> list[pathlib.Path]:
    """Every fabric-facing module that writes to the terminal."""
    return [
        module
        for module in fabric_facing(directory)
        if PRINT_RE.search(module.read_text(encoding="utf-8"))
    ]


def print_problems(directory: pathlib.Path) -> list[str]:
    """P5 and P6 — which side of the split writes to a terminal.

    Always-on and substrate-free by construction: it reads files. Both
    directions are needed. Without P5, printing creeps back into the spine and
    the published snippets grow lines an adopter would never write; without
    P6's lower bound, this passes just as happily against the silent example
    the ruling of 2026-08-13 rejected.

    Scoped to fabric-facing modules, which is what keeps a per-example
    provisioning utility — printing, importing no `ccf`, and explicitly not CCF
    — from counting as a second driver.
    """
    problems: list[str] = []
    facing = fabric_facing(directory)
    if not facing:
        return [
            f"{directory.name}: no module imports `ccf`, so the printing"
            " properties would pass over an empty set"
        ]

    carriers = region_modules(directory)
    if carriers and PRINT_RE.search(carriers[0].read_text(encoding="utf-8")):
        problems.append(
            f"{directory.name}/{carriers[0].name} carries the regions and"
            " prints. Presentation belongs in the module that drives the run;"
            " a printed line inside a published region is snippet surface an"
            " adopter would never write."
        )

    printers = printing_modules(directory)
    if not printers:
        problems.append(
            f"{directory.name} prints nothing — the example runs and shows a"
            " reader nothing (Dave's ruling, 2026-08-13)"
        )
    elif len(printers) > 1:
        problems.append(
            f"{directory.name}: more than one fabric-facing module prints"
            f" ({[module.name for module in printers]}). Exactly one drives"
            " the run."
        )
    return problems


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
        assert fabric_facing(directory), (
            f"{directory.name} has no module importing `ccf` — the printing"
            " properties would pass over an empty set"
        )


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
def test_the_spine_is_silent_and_exactly_one_module_prints(
    directory: pathlib.Path,
) -> None:
    """P5 and P6, over the shipped tree, through the controls' own predicate."""
    problems = print_problems(directory)
    assert not problems, f"{directory.name}: " + "; ".join(problems)


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


def _copied_named(tmp_path: pathlib.Path, name: str) -> pathlib.Path:
    """One shipped example, chosen BY NAME, copied under a fresh root.

    Copied rather than synthesized so the controls run against the real spine,
    the real markers and the real predicate. By name rather than by index for
    the controls that need a specific tree's contents — see
    `CONTEXT_PRODUCT_EXAMPLE` and `PROVISIONING_EXAMPLE`.
    """
    source = EXAMPLES_ROOT / name
    assert source.is_dir(), (
        f"{source} is gone — the control that selected it by name must be"
        " re-pointed rather than quietly falling back to whichever tree sorts"
        " first"
    )
    destination = tmp_path / source.name
    shutil.copytree(source, destination)
    assert not spine_problems(destination), "the unmodified copy must pass"
    return destination


def _copied_example(tmp_path: pathlib.Path) -> pathlib.Path:
    """The first shipped example in the scan, copied under a fresh root.

    For the controls whose subject is any conforming tree. The ones that need a
    PARTICULAR tree call `_copied_named` instead.
    """
    return _copied_named(tmp_path, split_examples(EXAMPLES_ROOT)[0].name)


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


def test_the_gate_refuses_a_region_carrying_module_that_prints(
    tmp_path: pathlib.Path,
) -> None:
    """P5 — this is what `D-11` is actually about.

    The published snippets are the spine's regions. A print inside them is a
    line an adopter would never write, inflating the example's apparent
    integration cost — the Phase 14.1 finding, restated as a property of
    whichever module carries the regions rather than of a module named
    `spine.py`.
    """
    example = _copied_example(tmp_path)
    spine = region_modules(example)[0]
    spine.write_text(
        spine.read_text(encoding="utf-8") + '\nprint("noise")\n', "utf-8"
    )

    problems = print_problems(example)
    assert any("carries the regions and prints" in p for p in problems), problems


def test_the_gate_refuses_an_example_that_prints_nothing(
    tmp_path: pathlib.Path,
) -> None:
    """P6, zero direction — the shape Dave's ruling of 2026-08-13 rejected.

    Without this the printing check passes just as happily against a silent
    example: one that runs and shows a reader nothing.
    """
    example = _copied_example(tmp_path)
    for module in printing_modules(example):
        module.write_text(
            PRINT_RE.sub("_muted(", module.read_text(encoding="utf-8")), "utf-8"
        )

    problems = print_problems(example)
    assert any("prints nothing" in problem for problem in problems), problems


def test_the_gate_refuses_two_fabric_facing_printers(
    tmp_path: pathlib.Path,
) -> None:
    """P6, two direction — printing must not creep back across the split."""
    example = _copied_example(tmp_path)
    silent = next(
        module
        for module in fabric_facing(example)
        if not PRINT_RE.search(module.read_text(encoding="utf-8"))
    )
    silent.write_text(
        silent.read_text(encoding="utf-8") + '\nprint("noise")\n', "utf-8"
    )

    problems = print_problems(example)
    assert any("more than one" in problem for problem in problems), problems


def test_the_fabric_facing_scope_admits_and_excludes_on_the_import(
    tmp_path: pathlib.Path,
) -> None:
    """The control for the one new convention, both halves.

    HW-1's `scenario/provision.py` prints and imports no `ccf`. If the scope
    predicate did not exclude it, P6 would be false for a correct example; if
    the predicate excluded everything, P5 and P6 would pass over an empty set.
    One test asserts both directions against the same file.
    """
    # BY NAME. This control's whole subject is one specific file, and after
    # the glob widened, `split_examples(...)[0]` is a `cp-` tree that does not
    # ship it. Selecting by index here would have turned a correct control into
    # a failure about the wrong tree.
    example = _copied_named(tmp_path, PROVISIONING_EXAMPLE)
    outsider = example / "scenario" / "provision.py"
    # Asserted, not skipped. A skip here would silently disable the only
    # control of the one convention this rewrite introduces, on the day
    # somebody moved the file.
    assert outsider.is_file(), (
        f"{example.name} no longer ships scenario/provision.py — repoint this"
        " control at whichever module prints and imports no `ccf`"
    )

    # (a) it prints, imports no `ccf`, and the example is still compliant.
    assert PRINT_RE.search(outsider.read_text(encoding="utf-8"))
    assert not CCF_IMPORT_RE.search(outsider.read_text(encoding="utf-8"))
    assert not print_problems(example), print_problems(example)

    # (b) the same file, now importing `ccf`, is a second printer and refused.
    outsider.write_text(
        "import ccf.deployment\n" + outsider.read_text(encoding="utf-8"), "utf-8"
    )
    problems = print_problems(example)
    assert any("more than one" in problem for problem in problems), problems


# ---------------------------------------------------------------------------
# Criterion 15 — the widened glob, proven to SCAN rather than merely to have
# been widened.
# ---------------------------------------------------------------------------


def test_the_widened_glob_actually_scans_the_context_product_tree(
    tmp_path: pathlib.Path,
) -> None:
    """Widening a string and re-running a green suite proves nothing.

    That is the whole point of criterion 15. A glob that matched nothing would
    pass every assertion in this module forever, and "the suite is still green
    after the widening" is exactly what it would look like. So this control
    asserts the widened scan REACHES the Context Product tree and then watches
    the real predicate REFUSE a broken copy of THAT tree, discovered through
    the real glob rather than handed to the predicate by hand.

    Both directions of the union are asserted. Dropping `cp-*` leaves the first
    half red; dropping `s1-*` leaves the second half red — so neither glob can
    be removed on the grounds that the suite still passes.

    The copy subject is `CONTEXT_PRODUCT_EXAMPLE`, selected by NAME. Written
    against `split_examples(...)[0]` it could silently drift back onto an `s1-`
    tree and leave the criterion unproven while this test stayed green.
    """
    scanned = [path.name for path in split_examples(EXAMPLES_ROOT)]

    assert CONTEXT_PRODUCT_EXAMPLE in scanned, (
        f"{SPINE_GLOBS} does not reach {CONTEXT_PRODUCT_EXAMPLE}; the scan"
        f" covers {scanned}. The published page's `--8<--` includes depend on"
        " the canonical regions, so a Context Product tree that publishes"
        " snippets must be inside this gate (24-CONTEXT.md D-21/D-23)."
    )
    assert any(name.startswith("s1-") for name in scanned), (
        f"the widening dropped Section 1; the scan covers {scanned}"
    )

    # A copy of THAT tree, stripped of its canonical markers.
    example = _copied_named(tmp_path, CONTEXT_PRODUCT_EXAMPLE)
    spine = region_modules(example)[0]
    text = spine.read_text(encoding="utf-8")
    for name in CANONICAL_MARKERS:
        text = text.replace(f"[start:{name}]", "").replace(f"[end:{name}]", "")
    spine.write_text(text, "utf-8")

    # Rediscovered through the real glob, so the chain under test is
    # glob -> discovery -> predicate, not predicate alone.
    discovered = split_examples(tmp_path)
    assert [path.name for path in discovered] == [CONTEXT_PRODUCT_EXAMPLE], (
        f"the glob did not rediscover the mutated copy: {discovered}"
    )

    problems = spine_problems(discovered[0])
    assert any("no module opens" in problem for problem in problems), problems


def test_the_pre_build_exclusion_releases_a_tree_that_has_any_code(
    tmp_path: pathlib.Path,
) -> None:
    """The narrow half of `is_pre_build`, and the half that can go wrong.

    An exclusion that skipped whatever it could not parse would let a shipped
    example that lost its spine leave the scan silently — this gate would then
    report green over exactly the defect it exists to catch. So the control
    takes a real, conforming tree, gives it a `spec/` directory, and asserts it
    is **still scanned**: carrying a spec is not what releases a tree, carrying
    no code at all is.
    """
    example = _copied_example(tmp_path)
    (example / "spec").mkdir(exist_ok=True)
    (example / "spec" / "CP-SPEC-999_Control.md").write_text("# a spec\n", "utf-8")

    assert not is_pre_build(example), (
        f"{example.name} has {len(modules_in(example))} modules and was still"
        " classified pre-build — the exclusion is releasing trees that carry"
        " code, which is how a spineless shipped example would leave the scan"
    )
    assert [path.name for path in split_examples(tmp_path)] == [example.name], (
        "a tree with code and a spec must stay in the scan"
    )


def test_the_pre_build_exclusion_releases_a_spec_only_tree(
    tmp_path: pathlib.Path,
) -> None:
    """The Gate-1 case: an authored spec, approved, with nothing built yet.

    `spec_generation.md` §2 requires exactly this state to exist — the spec is
    step one of the example project and Dave approves it *before* any
    implementation. `cp-02-facility-terms-snapshot` sat in it on 2026-08-29 and
    took five parametrized failures, because the gate read a directory with no
    code as an example whose spine had gone missing.
    """
    example = tmp_path / "cp-99-gate-one-only"
    (example / "spec").mkdir(parents=True)
    (example / "spec" / "CP-SPEC-999_Gate_One.md").write_text("# authored\n", "utf-8")

    assert is_pre_build(example)
    assert split_examples(tmp_path) == [], (
        "a spec-only tree must not be scanned for a spine it cannot have;"
        f" got {split_examples(tmp_path)}"
    )
