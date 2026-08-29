"""Assemble this example's documentation page from `template.html`.

**Run from the repository root:**

    python examples/cp-00-institutional-holders/page/build_page.py

Writes `page/cp-00.html`, which is then published as an artifact. The rendered
page is NOT committed — the generator and the template are, because they are the
reproducible things and the embedded source is not.

**THIS IS A PARTIAL GENERATOR, AND THE PARTIALNESS IS THE HONEST PART.**
This page was authored by hand before any generator existed, and it embeds code
three ways: five WHOLE FILES, ten hand-cut EXCERPTS, and eight blocks of
authored or edited text. **Only the five whole files are placeholdered.**

The five cannot drift — they are read from the tree and re-highlighted at build
time. **The excerpts still can**, because an excerpt is a human judgement about
which lines matter and mechanically re-cutting one would change what the page
chose to show. If you edit a file this page excerpts, re-read the page.

`examples/cp-01-counterparty-reference-snapshot/page/` is a FULL generator: it
was written alongside its template, so all fourteen of its collapsibles are
whole files and none can drift. That is the shape to copy for a new example.
This one is the shape you get when the page came first.

**The highlighting is reproduced, not approximated.** The original page used
Pygments' `HtmlFormatter(wrapcode=True)`, and this regenerates the published
bytes exactly — verified by diffing against the artifact before this file was
written. A generator that produced *similar* markup would silently rewrite the
whole page on its first run.
"""

from __future__ import annotations

import pathlib

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

HERE = pathlib.Path(__file__).resolve().parent
EXAMPLE = HERE.parent
REPO = EXAMPLE.parents[1]

TEMPLATE = HERE / "template.html"
OUTPUT = HERE / "cp-00.html"

#: Placeholder -> (example-relative path, Pygments lexer). Five entries, not
#: twenty-three: see the module docstring.
BLOCKS: dict[str, tuple[str, str]] = {
    "backends_yaml": ("backends.yaml", "yaml"),
    "artifacts_question_yaml": ("artifacts/question.yaml", "yaml"),
    "artifacts_ttl_yaml": ("artifacts/ttl.yaml", "yaml"),
    "artifacts_expected_yaml": ("artifacts/expected.yaml", "yaml"),
    "artifacts_assembly_recipe_yaml": ("artifacts/assembly-recipe.yaml", "yaml"),
}


def build() -> str:
    page = TEMPLATE.read_text(encoding="utf-8")
    for key, (path, lexer) in BLOCKS.items():
        source = (EXAMPLE / path).read_text(encoding="utf-8")
        body = highlight(
            source, get_lexer_by_name(lexer), HtmlFormatter(wrapcode=True)
        ).rstrip("\n")
        page = page.replace("{{" + key + "}}", body)
    if "{{" in page:
        raise SystemExit(f"unreplaced placeholder in {TEMPLATE}")
    return page


if __name__ == "__main__":
    rendered = build()
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(REPO)}  {len(rendered) / 1024:.0f} KB")
