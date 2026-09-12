"""A documentation page must describe the example it ships with.

**This exists because it happened.** cp-09's `page/template.html` began as a
copy of cp-01's and the copy was never finished. Measured 2026-09-12, while
building cp-10: the committed template carried

* `<p class="eyebrow">Context Product · cp-01</p>`,
* `<h1>Counterparty Reference Snapshot</h1>`,
* cp-01's "half you write" table — including a row for `assembler.py`, **a file
  cp-09 does not contain** — with four hand-typed line counts, and
* a footer reading `examples/cp-01-counterparty-reference-snapshot`.

The rendered HTML is gitignored (`example_delivery.md` §5: commit the generator,
never the render), so nothing in the tree disagreed with itself and no gate
fired. **Rebuilding cp-09's page today produced cp-01's identity from cp-09's
files**, and would have gone on doing so until a reader noticed.

Why the existing gates could not see it. `test_cp_readme_template.py` reads
READMEs. `check_product_gates.py` resolves gate ids to executing tests. The
page's prose was inside nobody's subject — which is the general shape worth
carrying: **a committed artifact with no reader is a place defects go to live.**

What is asserted, and each fails differently:

* the page NAMES this example — title, eyebrow, footer path;
* the page names NO OTHER example — no sibling slug, no sibling directory;
* every bare filename the page's own prose points at EXISTS here, so a table
  cannot list a file this example does not have.

Scoped to `template.html`, which is the authored prose. The collapsibles below
it embed real files verbatim, and those legitimately cross-reference siblings —
asserting over the render would flag a specification citing `CP-SPEC-009` as a
leak.

**Scoped to the MASTHEAD AND FOOTER for slugs, and the first draft of this
module got that wrong.** It refused any `cp-NN` token anywhere in a template and
went red on four shipped pages that were entirely correct: cp-02 carries a
comparison table whose rows are literally `cp-00` and `cp-01`, which is the page
doing its job. A page may discuss its siblings; what it may not do is *wear one
of their names*. Two more first-draft reds were the same error in a different
place — requiring a footer path that four pages simply do not carry, and
resolving a repo-relative `examples/cp-00-.../run.py` against the example
directory. **Six of the twelve initial failures were defects in this module, not
in the pages**, which is the reason the scope below is narrow and stated.
"""

from __future__ import annotations

import pathlib
import re

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLES_ROOT = REPO_ROOT / "examples"

#: `examples/cp-09-treasury-liquidity-position` -> `cp-09`.
SLUG_RE = re.compile(r"^(cp-\d{2})-")

#: Any `cp-NN` token in the page's prose.
ANY_SLUG_RE = re.compile(r"\bcp-\d{2}\b")

#: `<p class="eyebrow">Context Product · cp-09</p>` — and cp-00's nests a
#: `<b>`, so the capture runs to the closing tag rather than the next `<`.
EYEBROW_RE = re.compile(r'class="eyebrow"[^>]*>(.*?)</p>', re.S)

#: The masthead — where a page declares whose it is. Slug leakage is asserted
#: HERE and in the footer, never over the body: a comparison table naming
#: `cp-00` is the page working, not the page lying.
MASTHEAD_RE = re.compile(r"<header.*?</header>", re.S)

#: The footer, for the same reason.
FOOTER_RE = re.compile(r"<footer.*?</footer>", re.S)

#: A footer path: `<code>examples/cp-09-treasury-liquidity-position</code>`.
EXAMPLE_PATH_RE = re.compile(r"examples/(cp-\d{2}-[a-z0-9-]+)")

#: A bare filename the prose points at, e.g. `<code>deployment.py</code>` or
#: `<code>artifacts/question.yaml</code>`. Restricted to the extensions an
#: example actually ships, so a prose mention of `.env` or a URL is out of
#: scope.
FILE_RE = re.compile(
    r"<code>([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|yaml|yml|md|txt))"
    r"(?:::[A-Za-z0-9_.]+)?</code>"
)


def paged_examples() -> list[pathlib.Path]:
    """Every example directory shipping a page template.

    Returns directories, so a new example with a page is covered the day it
    lands rather than the day someone remembers to add it here.
    """
    return sorted(
        template.parents[1]
        for template in EXAMPLES_ROOT.glob("cp-*/page/template.html")
    )


def _slug(directory: pathlib.Path) -> str:
    match = SLUG_RE.match(directory.name)
    assert match, f"{directory.name} is not a `cp-NN-...` directory"
    return match.group(1)


@pytest.fixture(scope="module")
def covered() -> list[pathlib.Path]:
    found = paged_examples()
    assert found, (
        "no example ships a page/template.html, so every assertion in this"
        " module would pass over an empty set"
    )
    return found


def test_the_population_is_not_empty(covered: list[pathlib.Path]) -> None:
    """The lower bound. Without it the parametrized gates below are vacuous."""
    assert len(covered) >= 2, (
        f"only {len(covered)} example ships a page; cross-example leakage"
        " cannot be detected against a population of one"
    )


@pytest.mark.parametrize("directory", paged_examples(), ids=lambda p: p.name)
def test_the_page_names_the_example_it_ships_with(
    directory: pathlib.Path,
) -> None:
    """Title, eyebrow and footer path all name THIS example.

    Three separate assertions because they fail separately: cp-09's title was
    correct while its eyebrow and footer were cp-01's, so a gate reading only
    the title would have passed.
    """
    slug = _slug(directory)
    page = (directory / "page" / "template.html").read_text(encoding="utf-8")

    title = re.search(r"<title>(.*?)</title>", page, re.S)
    assert title, "the template declares no <title>"
    assert slug in title.group(1), (
        f"the title {title.group(1)!r} does not name {slug}"
    )

    eyebrow = EYEBROW_RE.search(page)
    assert eyebrow, "the template carries no eyebrow"
    assert slug in eyebrow.group(1), (
        f"the eyebrow reads {eyebrow.group(1).strip()!r} on {directory.name};"
        " this is the exact defect measured on cp-09, which published as cp-01"
    )

    # NO OTHER example's directory, rather than exactly one: four shipped
    # pages carry no footer path at all, and an absent path is not leakage.
    # cp-09's footer named `examples/cp-01-counterparty-reference-snapshot`,
    # and that is what this catches.
    paths = set(EXAMPLE_PATH_RE.findall(page))
    assert paths <= {directory.name}, (
        f"the page names example paths {sorted(paths - {directory.name})};"
        f" it ships with {directory.name}"
    )


@pytest.mark.parametrize("directory", paged_examples(), ids=lambda p: p.name)
def test_the_page_names_no_other_example(directory: pathlib.Path) -> None:
    """No sibling's slug appears in the authored prose.

    A page may legitimately discuss a *ruling* that came from another rung, but
    it does so by decision id (`D-IMPL-331`), never by wearing another
    example's name.
    """
    slug = _slug(directory)
    page = (directory / "page" / "template.html").read_text(encoding="utf-8")
    for region, pattern in (("masthead", MASTHEAD_RE), ("footer", FOOTER_RE)):
        block = pattern.search(page)
        if block is None:
            continue
        found = set(ANY_SLUG_RE.findall(block.group(0)))
        assert found <= {slug}, (
            f"{directory.name}'s {region} names {sorted(found - {slug})}; a"
            " page that wears another example's name in the place it declares"
            " whose it is, is how cp-09 came to publish as cp-01"
        )


@pytest.mark.parametrize("directory", paged_examples(), ids=lambda p: p.name)
def test_every_file_the_page_points_at_exists_here(
    directory: pathlib.Path,
) -> None:
    """A table cannot list a file this example does not have.

    cp-09's inherited table carried a row for `assembler.py` with a line count
    of 268. There is no such file in cp-09, and the count was cp-01's.
    """
    page = (directory / "page" / "template.html").read_text(encoding="utf-8")

    def _resolves(name: str) -> bool:
        """`examples/...` and `tests/...` are REPO-relative; the rest are not.

        The first draft resolved every name against the example directory and
        reported cp-00's own `examples/cp-00-institutional-holders/run.py` as
        missing — a citation that is correct, and correct in the form this
        project writes citations in.
        """
        root = REPO_ROOT if name.startswith(("examples/", "tests/", "src/",
                                             "runtime/", "docs/")) else directory
        return (root / name).is_file()

    missing = sorted(
        name for name in set(FILE_RE.findall(page)) if not _resolves(name)
    )
    assert not missing, (
        f"{directory.name}'s page points at {missing}, which do not exist in"
        " that example — the page is describing a different tree"
    )
