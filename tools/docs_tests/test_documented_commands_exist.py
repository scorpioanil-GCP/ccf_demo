"""Criterion 1 — the Makefile and the published pages name the same commands.

A bijection, on the `test_diagram_coverage.py` model, and for the same reason:
the two directions fail differently and only one of them fails loudly.

*Forward* — a page naming ``make example-99`` sends a reader to a shell to get
``No rule to make target``. Nothing catches it; the build is green, the page
looks authoritative, and the failure lands on the reader rather than on CI.

*Backward* — an example that runs in CI and is documented by no page is
criterion 1's real content. It is worse than an undocumented feature, because
it is a maintained, tested, green thing that nobody can find. Deleting the
paragraph that mentioned it costs nothing today and silently unpublishes it.

**What is parsed, and why those two things.** The Makefile's ``.PHONY`` list
and the ``examples:`` prerequisite list are both machine-readable and stable,
and they mean different things: ``.PHONY`` is *every* target that exists, while
``examples:`` is the composed set CI actually runs. The forward direction is
checked against the first; the backward direction against the second, because
requiring a published page for every target in ``.PHONY`` would demand prose
for ``help`` and ``install``, which is not a documentation debt.

**Why extraction is scoped to code contexts.** ``make`` is an ordinary English
verb, and the published tree is written in English. A bare ``\\bmake\\s+(\\w+)``
scan over running prose harvests "make it", "make the", "make your", "make a",
"make this", "make that" and "make re-authoring" — measured, all seven, at this
plan's HEAD. Scoping the scan to inline code spans and fenced blocks — which is
how a command is actually written — takes the same corpus from 24 candidates
with 7 false positives to **17 targets with none**. The scoping is what makes
this gate usable rather than a source of noise a maintainer learns to ignore.
"""

from __future__ import annotations

import pathlib
import re
import shutil

import pytest

from tools.docs_tests import _prose

MAKEFILE = _prose.REPO_ROOT / "Makefile"

#: A ``make <target>`` invocation. Applied only to code spans and fenced
#: blocks, never to running prose — see the module docstring.
MAKE_INVOCATION = re.compile(r"\bmake\s+([a-zA-Z0-9][a-zA-Z0-9_.-]*)")

#: An inline code span's contents.
CODE_SPAN = re.compile(r"`([^`]*)`")

#: The ``.PHONY`` declaration, including backslash line continuations.
PHONY_RE = re.compile(r"^\.PHONY:((?:[^\n\\]*\\\n)*[^\n]*)", re.MULTILINE)

#: The ``examples:`` target's prerequisite list, stopping at the ``##`` comment
#: `make help` renders from.
EXAMPLES_RE = re.compile(r"^examples:([^\n#]*)", re.MULTILINE)


def phony_targets(makefile_text: str) -> set[str]:
    """Every target declared ``.PHONY``."""
    match = PHONY_RE.search(makefile_text)
    if match is None:
        return set()
    return set(match.group(1).replace("\\", " ").split())


def composed_examples(makefile_text: str) -> set[str]:
    """The ``example-*`` targets the ``examples:`` target composes."""
    match = EXAMPLES_RE.search(makefile_text)
    if match is None:
        return set()
    return {
        token for token in match.group(1).split() if token.startswith("example-")
    }


def documented_targets(pages: list[pathlib.Path]) -> dict[str, list[str]]:
    """Each ``make`` target named by a published page, to the pages naming it."""
    found: dict[str, list[str]] = {}
    for page, paragraph in _prose.iter_paragraphs(pages, prose_only=False):
        chunks = (
            [paragraph.raw] if paragraph.fenced else CODE_SPAN.findall(paragraph.raw)
        )
        for chunk in chunks:
            for target in MAKE_INVOCATION.findall(chunk):
                found.setdefault(target, []).append(
                    f"{_prose.relative(page)}:{paragraph.lineno}"
                )
    return found


def undefined_commands(
    pages: list[pathlib.Path], makefile_text: str
) -> list[str]:
    """`target (page:line, …)` for every documented target the Makefile lacks."""
    phony = phony_targets(makefile_text)
    return [
        f"make {target} ({', '.join(sites)})"
        for target, sites in sorted(documented_targets(pages).items())
        if target not in phony
    ]


def undocumented_examples(
    pages: list[pathlib.Path], makefile_text: str
) -> list[str]:
    """Every ``example-*`` target CI runs that no published page names."""
    named = set(documented_targets(pages))
    return sorted(composed_examples(makefile_text) - named)


def _makefile_text() -> str:
    return MAKEFILE.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# Preconditions — a vacuous pass is the failure this module exists to prevent.
# --------------------------------------------------------------------------


def test_the_makefile_parses() -> None:
    assert MAKEFILE.is_file(), f"missing Makefile: {MAKEFILE}"
    text = _makefile_text()
    assert phony_targets(text), "no .PHONY targets parsed — the declaration moved"
    assert composed_examples(text), (
        "no example-* prerequisites parsed from the examples: target"
    )


def test_the_published_tree_names_commands() -> None:
    assert _prose.PUBLIC_DIR.is_dir(), f"missing published tree: {_prose.PUBLIC_DIR}"
    assert _prose.published_pages(), f"no markdown pages under {_prose.PUBLIC_DIR}"
    assert documented_targets(_prose.published_pages()), (
        "no `make <target>` invocation found in any published page — this gate "
        "is scanning nothing"
    )


def test_the_walk_does_not_depend_on_the_process_cwd(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    assert MAKEFILE.is_file(), "the Makefile resolved against the CWD, not the repo"
    assert documented_targets(_prose.published_pages()), (
        "the page walk resolved against the CWD, not the repo"
    )


# --------------------------------------------------------------------------
# The bijection.
# --------------------------------------------------------------------------


def test_every_documented_make_target_exists() -> None:
    offenders = undefined_commands(_prose.published_pages(), _makefile_text())
    assert not offenders, (
        "published pages tell a reader to run make targets that do not exist "
        "in .PHONY: " + "; ".join(offenders)
    )


def test_every_composed_example_target_is_documented() -> None:
    offenders = undocumented_examples(_prose.published_pages(), _makefile_text())
    assert not offenders, (
        "these example targets run in CI but no published page names them — "
        "they are maintained, tested, and unfindable: " + ", ".join(offenders)
    )


# --------------------------------------------------------------------------
# Controls — both polarities, because the two directions are separate gates.
# --------------------------------------------------------------------------


def _copied_page(tmp_path: pathlib.Path, extra: str) -> list[pathlib.Path]:
    source = _prose.PUBLIC_DIR / "tutorial" / "adopters-guide.md"
    assert source.is_file(), f"control fixture source missing: {source}"
    target = tmp_path / source.name
    shutil.copy(source, target)
    with target.open("a", encoding="utf-8") as handle:
        handle.write("\n\n" + extra + "\n")
    return [target]


def test_the_gate_refuses_a_documented_target_that_does_not_exist(
    tmp_path: pathlib.Path,
) -> None:
    pages = _copied_page(tmp_path, "Run it with `make example-nope`.")
    offenders = undefined_commands(pages, _makefile_text())
    assert any("example-nope" in offender for offender in offenders), offenders


def test_the_gate_refuses_an_undocumented_composed_example() -> None:
    """The backward direction, forced by dropping a target from `examples:`.

    The Makefile text is mutated in memory rather than on disk — this plan does
    not own the Makefile (plan 16-12 does), and a control that edits the tree to
    prove a point is a control that can leave the tree edited.

    The injection anchors on ``examples: example-`` rather than on any
    particular member. It used to name ``example-00`` and stopped taking the
    moment plan 23-09 deleted that target — the ``assert`` below caught it,
    which is the whole reason a fixture carries its own non-vacuity guard.
    """
    mutated = _makefile_text().replace(
        "examples: example-", "examples: example-99 example-", 1
    )
    assert "example-99" in composed_examples(mutated), "the fixture did not take"
    offenders = undocumented_examples(_prose.published_pages(), mutated)
    assert offenders == ["example-99"], offenders


def test_the_unmodified_tree_passes_both_directions(tmp_path: pathlib.Path) -> None:
    """The controls' baseline: refusal above comes from the injection."""
    source = _prose.PUBLIC_DIR / "tutorial" / "adopters-guide.md"
    target = tmp_path / source.name
    shutil.copy(source, target)
    assert undefined_commands([target], _makefile_text()) == []


def test_the_english_verb_make_is_not_read_as_an_invocation(
    tmp_path: pathlib.Path,
) -> None:
    """The scoping boundary, held from the other side.

    Seven such phrases exist in the tree today. If this ever fails, the scan has
    widened from code contexts to running prose and the gate has become noise.
    """
    pages = _copied_page(
        tmp_path,
        "This is what would make the guide easier to follow, and make it "
        "worth re-authoring.",
    )
    offenders = undefined_commands(pages, _makefile_text())
    assert offenders == [], offenders


def test_a_target_named_only_in_a_fenced_block_still_counts(
    tmp_path: pathlib.Path,
) -> None:
    """Fenced blocks are where run commands actually live.

    If fenced content were skipped, the backward direction would report every
    example target as undocumented — the loudest possible false positive.
    """
    pages = _copied_page(tmp_path, "```sh\nmake example-nope\n```")
    offenders = undefined_commands(pages, _makefile_text())
    assert any("example-nope" in offender for offender in offenders), offenders
