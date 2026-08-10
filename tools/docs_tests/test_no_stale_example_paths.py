"""Criterion 5 — no published page names an `examples/` path that is not there.

**Two halves, and only one of them was already covered.**

The *mechanical* half is a snippet include: ``--8<-- "examples/…"``.
`mkdocs.yml` runs `pymdownx.snippets` with ``check_paths: true``, so a dangling
include is a hard build error and `make docs-strict` already catches it. This
module re-asserts it anyway, for one reason: `include_targets()` gives a
failure that **names the page, the line and the target**, where the build gives
a traceback ending in ``SnippetMissingError``. The two gates should agree, and
if this assertion ever fires while `make docs-strict` is green, the snippet path
check has regressed — the same relationship
`test_diagram_coverage.test_every_embed_names_an_existing_diagram` holds.

The *silent* half is what this module actually owns, and nothing anywhere
covered it: a path written in **running prose** — "the assembler lives in
`examples/04-cross-process`", "asserted by
`tests/examples/test_workflow_hitl_output.py`". Nothing checks these. They are
not includes, so `check_paths` never sees them; the build stays green; the
sentence quietly starts lying the moment the directory is renamed. This
discharges SURFACE-AUDIT **A-5**'s mis-pointed-include gap for path targets.

Measured at this plan's HEAD, and both figures are stated because the scan
covers more than the running prose the requirement names — **running prose
alone: 13 distinct tokens, 15 references, 7 pages**, which is the surface
``16-RESEARCH.md`` § A.2 enumerates; **prose and fenced blocks together: 56
distinct tokens, 119 references, 15 pages**, which is what this module actually
asserts over. Zero unresolvable in either set.

**Why paragraph scoping, stated accurately.** The phase plan motivates it as
"a wrapped Markdown sentence hides a path from a line-scoped regex", and for
this particular gate that reason does **not** hold: a reflow breaks at
whitespace and a path is a single token, so a line-scoped scan would find these
tokens too. What paragraph scoping actually buys here is worth naming instead
of overstating. One, fence awareness — the scan knows a ```sh``` block from a
sentence, which the command gate needs and which a line loop does not have.
Two, one scoping rule shared with the other two gates in this package rather
than three that drift apart (`tools/docs_tests/_prose.py`, RESEARCH P-2).
Three, a paragraph-anchored line number to report from.

**Known limit, recorded rather than papered over.** A path broken *mid-token*
across a line — ``examples/08-e2e-demo/artifacts/`` then ``scenario.yaml`` on
the next line — is not detected, by this gate or by any line-scoped one. The
join inserts a space, and joining without one would corrupt every ordinary
sentence. The residue is that ``examples/08-e2e-demo/artifacts/`` is checked
and found to exist, so the reference is neither confirmed nor flagged.

**Why the scan reads `raw` rather than `text`.** A path in running prose is
almost always written as an inline code span, and `_prose.Paragraph.text`
strips code spans by design — scanning it would find approximately nothing and
report green forever. This is the one gate in the package that wants the
unstripped form, and saying so here is cheaper than rediscovering it.

**Why fenced blocks are scanned too.** A stale path inside a ```sh``` block is
exactly as rotten as one in a sentence and exactly as invisible to the build.
Measured at HEAD: zero misses in fenced blocks, so including them costs nothing
and closes the gap before the rewrite opens it.
"""

from __future__ import annotations

import pathlib
import re
import shutil

import pytest

from tools.docs_tests import _prose
from tools.publish_scan import include_targets

#: An `examples/…` or `tests/examples/…` path token.
#:
#: The trailing character class excludes ``.``, ``,`` and ``)`` so a path at the
#: end of a sentence does not absorb the punctuation. The lookbehind stops the
#: inner ``examples`` of ``tests/examples/x`` from being re-matched as a bare
#: ``examples/x`` that does not exist — verified at HEAD, where no
#: ``<prefix>/examples/`` token exists anywhere in the published tree.
PATH_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_.-])(?:tests/examples|examples)/[A-Za-z0-9_./-]*[A-Za-z0-9_/]"
)


def _resolves(target: str) -> bool:
    return (_prose.REPO_ROOT / target).exists()


def _include_stem(target: str) -> str:
    """An include target minus any section suffix.

    Mirrors `tools.publish_scan.include_escapes`, which splits on ``::`` then
    ``:`` — `pymdownx.snippets` accepts both spellings for a named section, and
    the file half is the only part that has to exist on disk.
    """
    return target.split("::", 1)[0].split(":", 1)[0].strip()


def prose_path_offenders(pages: list[pathlib.Path]) -> list[str]:
    """`page:line -> missing path` for every unresolvable prose path token."""
    offenders: list[str] = []
    for page, paragraph in _prose.iter_paragraphs(pages, prose_only=False):
        for token in PATH_TOKEN.findall(paragraph.raw):
            if not _resolves(token):
                offenders.append(
                    f"{_prose.relative(page)}:{paragraph.lineno} -> {token}"
                )
    return offenders


def include_offenders(pages: list[pathlib.Path]) -> list[str]:
    """`page:line -> missing target` for every unresolvable snippet include."""
    offenders: list[str] = []
    for page in pages:
        text = page.read_text(encoding="utf-8")
        for lineno, target in include_targets(text):
            stem = _include_stem(target)
            if stem and not _resolves(stem):
                offenders.append(f"{_prose.relative(page)}:{lineno} -> {target}")
    return offenders


def prose_path_tokens(pages: list[pathlib.Path]) -> set[str]:
    """Every distinct path token found, for the non-vacuity precondition."""
    return {
        token
        for _, paragraph in _prose.iter_paragraphs(pages, prose_only=False)
        for token in PATH_TOKEN.findall(paragraph.raw)
    }


# --------------------------------------------------------------------------
# Preconditions — a vacuous pass is the failure this module exists to prevent.
# --------------------------------------------------------------------------


def test_the_published_tree_is_populated() -> None:
    assert _prose.PUBLIC_DIR.is_dir(), f"missing published tree: {_prose.PUBLIC_DIR}"
    assert _prose.published_pages(), f"no markdown pages under {_prose.PUBLIC_DIR}"


def test_the_scan_finds_path_tokens_to_check() -> None:
    """The corpus contains example paths at all.

    Without this the assertion below passes over an empty set — and it would do
    so most convincingly right after a rewrite renamed every example directory,
    which is precisely when it is needed.
    """
    tokens = prose_path_tokens(_prose.published_pages())
    assert tokens, (
        "no examples/ or tests/examples/ path token found in published prose — "
        "this gate is scanning nothing"
    )


def test_the_walk_does_not_depend_on_the_process_cwd(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    assert _prose.published_pages(), "the walk resolved against the CWD, not the repo"
    assert prose_path_tokens(_prose.published_pages()), (
        "path resolution followed the CWD rather than the repo root"
    )


# --------------------------------------------------------------------------
# The two halves.
# --------------------------------------------------------------------------


def test_every_prose_path_reference_resolves_on_disk() -> None:
    offenders = prose_path_offenders(_prose.published_pages())
    assert not offenders, (
        "published prose names paths that do not exist. These are invisible to "
        "the strict build because they are not snippet includes — the page just "
        "starts lying: " + "; ".join(offenders)
    )


def test_every_snippet_include_resolves_on_disk() -> None:
    offenders = include_offenders(_prose.published_pages())
    assert not offenders, (
        "snippet includes name files that do not exist. `make docs-strict` "
        "should already have failed on these; if it is green, check_paths has "
        "regressed: " + "; ".join(offenders)
    )


# --------------------------------------------------------------------------
# Controls — a gate nobody has watched fail is a gate that may scan nothing.
# --------------------------------------------------------------------------


def _copied_page(tmp_path: pathlib.Path, extra: str) -> list[pathlib.Path]:
    source = _prose.PUBLIC_DIR / "tutorial" / "adopters-guide.md"
    assert source.is_file(), f"control fixture source missing: {source}"
    target = tmp_path / source.name
    shutil.copy(source, target)
    with target.open("a", encoding="utf-8") as handle:
        handle.write("\n\n" + extra + "\n")
    return [target]


def test_the_unmodified_copy_passes(tmp_path: pathlib.Path) -> None:
    """The controls' baseline: refusal below must come from the injection."""
    source = _prose.PUBLIC_DIR / "tutorial" / "adopters-guide.md"
    target = tmp_path / source.name
    shutil.copy(source, target)
    assert prose_path_offenders([target]) == []
    assert include_offenders([target]) == []


def test_the_gate_refuses_an_injected_missing_prose_path(
    tmp_path: pathlib.Path,
) -> None:
    pages = _copied_page(
        tmp_path,
        "The assembler for this walkthrough lives in "
        "`examples/does-not-exist/run.py`, which you should read first.",
    )
    offenders = prose_path_offenders(pages)
    assert offenders, "the gate admitted a prose path that does not exist"
    assert any("examples/does-not-exist/run.py" in o for o in offenders), offenders


def test_the_gate_refuses_a_missing_path_inside_a_fenced_block(
    tmp_path: pathlib.Path,
) -> None:
    """Fence awareness, in the direction that matters.

    A run command naming a deleted example is exactly as broken as a sentence
    naming one, and exactly as invisible to `check_paths` — it is not an
    include, so nothing in the build looks at it.
    """
    pages = _copied_page(
        tmp_path,
        "```sh\npython examples/does-not-exist/run.py\n```",
    )
    offenders = prose_path_offenders(pages)
    assert offenders, "a stale path inside a fenced block escaped the scan"


def test_a_path_reference_split_across_lines_is_still_read_as_one_paragraph(
    tmp_path: pathlib.Path,
) -> None:
    """The reflow case that paragraph scoping *does* handle.

    The path is intact; the sentence around it wraps. A line-scoped scan reports
    the wrong line number for the paragraph, and a naive one that reads a page
    line-at-a-time loses the surrounding context entirely. The token is found
    and reported against the paragraph's first line.
    """
    pages = _copied_page(
        tmp_path,
        "The fixture asserting this behaviour lives in the always-on suite,\n"
        "at `tests/examples/test_does_not_exist.py`, and is run by\n"
        "`make test`.",
    )
    offenders = prose_path_offenders(pages)
    assert any(
        "tests/examples/test_does_not_exist.py" in offender for offender in offenders
    ), offenders


def test_a_tests_examples_path_is_not_mis_reported_as_a_bare_examples_path(
    tmp_path: pathlib.Path,
) -> None:
    """The lookbehind, held from the failing side.

    Without it, ``tests/examples/x.py`` would also match as ``examples/x.py``,
    and the gate would report a path the page never wrote — sending a reader to
    look for a file nobody named.
    """
    pages = _copied_page(
        tmp_path,
        "See `tests/examples/test_does_not_exist.py` for the assertion.",
    )
    offenders = prose_path_offenders(pages)
    assert len(offenders) == 1, offenders
    assert offenders[0].endswith("tests/examples/test_does_not_exist.py"), offenders


def test_the_gate_refuses_an_injected_missing_include(
    tmp_path: pathlib.Path,
) -> None:
    pages = _copied_page(
        tmp_path,
        '```py\n--8<-- "examples/does-not-exist/run.py"\n```',
    )
    offenders = include_offenders(pages)
    assert offenders, "the gate admitted an include target that does not exist"


def test_the_include_half_sees_the_block_form(tmp_path: pathlib.Path) -> None:
    """`include_targets` is imported, not re-implemented, and this is why.

    `pymdownx.snippets` accepts a block form in which a bare ``--8<--`` opens a
    one-per-line list. A hand-rolled inline-only regex is defeated by that
    two-line edit; the shared parser is not.
    """
    pages = _copied_page(
        tmp_path,
        "```py\n--8<--\nexamples/does-not-exist/block-form.py\n--8<--\n```",
    )
    offenders = include_offenders(pages)
    assert offenders, (
        "the block include form escaped the scan — the include parser was "
        "re-implemented instead of imported from tools.publish_scan"
    )
