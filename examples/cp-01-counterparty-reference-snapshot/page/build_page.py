"""Assemble this example's documentation page from `template.html`.

**Run from the repository root:**

    python examples/cp-01-counterparty-reference-snapshot/page/build_page.py

Writes `page/cp-01.html`, which is then published as an artifact. The rendered
page is NOT committed — the generator and the template are, because they are the
reproducible things and the embedded source is not. The run prints the rendered
size rather than this docstring asserting one.

**WHY A GENERATOR AND NOT THE PAGE.** Every collapsible on the page is a
verbatim copy of a file in this example. Committing the rendered HTML would put
each of those files in the tree twice, and the copies would drift the first time
a `.yaml` changed and nobody remembered to republish. This script reads the real
files at build time, so the page cannot describe a version of the example that
no longer exists.

**The printed run is the one thing it does NOT generate.** `RUN_TRANSCRIPT` is a
committed artifact of a run against a NAMED SNAPSHOT, because a page that
re-ran the product on every build would print whatever the estate said today —
and a printed run that can drift is a documentation defect that presents as a
fabric defect. Regenerate it deliberately, with the anchor pinned, and say so.

**EVERY CAPTION COUNT IS COMPUTED, NOT TYPED** (`24.6-L-11`). The labels below
carried twelve line counts and one test count as literals; measured on
2026-09-04, EIGHT of the thirteen were wrong — the specification was captioned
1,351 for a file of 1,395, and the test module 386/13 for a file of 728/18.
They were true when they were typed and drifted afterwards, which is what a
hand-typed count about a file the same script already reads always does.
`_lines` and `_tests` compute them from that same read, so the page cannot
misdescribe a file it is displaying directly beside the caption.
"""

from __future__ import annotations

import ast
import html
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
EXAMPLE = HERE.parent
REPO = EXAMPLE.parents[1]

TEMPLATE = HERE / "template.html"
RUN_TRANSCRIPT = HERE / "run-transcript.txt"
OUTPUT = HERE / "cp-01.html"

#: Placeholder -> the file whose contents fill it, and the summary label.
#: Paths are relative to the example, except `tests/...` which is repo-relative.
#:
#: The label is a TEMPLATE. `{lines}` and `{tests}` are filled at build time
#: from the file being displayed (`24.6-L-11`); a numeric literal in a label
#: here is the defect this shape exists to make impossible.
BLOCKS: dict[str, tuple[str, str, str]] = {
    "spec": (
        "spec/CP-SPEC-001_Counterparty_Reference_Snapshot.md",
        "The specification — {lines} lines, and the first thing written",
        "Authored at Gate 1 and approved before a line of code existed."
        " Every artifact below is derived from it.",
    ),
    "config": ("ccf_config.yaml", "ccf_config.yaml — the whole Control Plane, {lines} lines", ""),
    "backends": ("backends.yaml", "backends.yaml — {lines} lines, and no credential in any of them", ""),
    "question": ("artifacts/question.yaml", "artifacts/question.yaml — {lines} lines", ""),
    "ttl": ("artifacts/ttl.yaml", "artifacts/ttl.yaml — {lines} lines", ""),
    "recipe": ("artifacts/assembly-recipe.yaml", "artifacts/assembly-recipe.yaml — every step with its runtime witness", ""),
    "expected": ("artifacts/expected.yaml", "artifacts/expected.yaml — {lines} lines, deriving nothing from a run", ""),
    "deployment": ("deployment.py", "deployment.py — {lines} lines, the interpreter", ""),
    "produce": ("produce.py", "produce.py — {lines} lines, the spine", ""),
    "assembler": ("assembler.py", "assembler.py — {lines} lines, the governed seam", ""),
    "run_py": ("run.py", "run.py — {lines} lines, the client", ""),
    "readme": ("README.md", "README.md — {lines} lines", ""),
    "tests": ("tests/examples/test_cp_01_output.py", "tests/examples/test_cp_01_output.py — {lines} lines, {tests} tests", ""),
}


def _resolve(path: str) -> pathlib.Path:
    return REPO / path if path.startswith("tests/") else EXAMPLE / path


def _lines(source: str) -> int:
    """Lines in the text the page is about to display, counted from that text."""
    return source.count("\n")


def _tests(source: str) -> int:
    """`test_`-prefixed functions in `source`, by AST rather than by grep.

    A grep would count a name inside a docstring or a string literal; the walk
    counts definitions, which is what the caption claims.
    """
    tree = ast.parse(source)
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )


def _caption(template: str, source: str) -> str:
    """`template` with every count filled from `source` — never from memory.

    An unfilled placeholder raises, in the voice of :func:`build`'s own
    `{{`-check: a caption reading "{lines} lines" on a published page is the
    same class of defect as a stale number, and it must not render.
    """
    filled = template
    if "{lines}" in filled:
        filled = filled.replace("{lines}", f"{_lines(source):,}")
    if "{tests}" in filled:
        filled = filled.replace("{tests}", f"{_tests(source):,}")
    if "{" in filled:
        raise SystemExit(f"unfilled caption placeholder in {template!r}")
    return filled


def _details(path: str, label: str, note: str) -> str:
    source = _resolve(path).read_text(encoding="utf-8")
    label = _caption(label, source)
    body = html.escape(source)
    note_html = f'<p class="note">{html.escape(note)}</p>' if note else ""
    return (
        f"<details><summary>{html.escape(label)}</summary>{note_html}"
        f'<div class="scroll"><pre><code>{body}</code></pre></div></details>'
    )


def build() -> str:
    page = TEMPLATE.read_text(encoding="utf-8")
    page = page.replace(
        "{{run}}", html.escape(RUN_TRANSCRIPT.read_text(encoding="utf-8"))
    )
    for key, (path, label, note) in BLOCKS.items():
        page = page.replace("{{" + key + "}}", _details(path, label, note))
    if "{{" in page:
        raise SystemExit(f"unreplaced placeholder in {TEMPLATE}")
    return page


if __name__ == "__main__":
    rendered = build()
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(REPO)}  {len(rendered) / 1024:.0f} KB")
