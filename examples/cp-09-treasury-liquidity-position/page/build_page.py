"""Assemble this example's documentation page from `template.html`.

**Run from the repository root:**

    python examples/cp-01-counterparty-reference-snapshot/page/build_page.py

Writes `page/cp-09.html`, which is then published as an artifact. The rendered
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

**THE MASTHEAD, THE FILE TABLE AND THE FOOTER WERE cp-01's UNTIL 2026-09-12.**
This template began as a copy of cp-01's and the copy was never finished: it
carried `Context Product · cp-01`, `<h1>Counterparty Reference Snapshot</h1>`,
cp-01's "half you write" table — including `assembler.py`, a file this example
does not contain — and cp-01's footer path. The render is gitignored, so
rebuilding this page produced cp-01's identity from cp-09's tree. Found while
building cp-10 and repaired narrowly under `D-GATE-cp-10`; no cp-09 evidence or
behavior changed, so cp-09's Gate 2 was not reopened.
`tests/examples/test_page_identity.py` is the regression.

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
import re
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
EXAMPLE = HERE.parent
REPO = EXAMPLE.parents[1]

TEMPLATE = HERE / "template.html"
RUN_TRANSCRIPT = HERE / "run-transcript.txt"
OUTPUT = HERE / "cp-09.html"

#: Placeholder -> the file whose contents fill it, and the summary label.
#: Paths are relative to the example, except `tests/...` which is repo-relative.
#:
#: The label is a TEMPLATE. `{lines}` and `{tests}` are filled at build time
#: from the file being displayed (`24.6-L-11`); a numeric literal in a label
#: here is the defect this shape exists to make impossible.
BLOCKS: dict[str, tuple[str, str, str]] = {
    "spec": (
        "spec/CP-SPEC-009_Treasury_Liquidity_Position.md",
        "The specification — {lines} lines, and the first thing written",
        "Authored at Gate 1 and approved before a line of code existed."
        " Every artifact below is derived from it.",
    ),
    "config": ("ccf_config.yaml",
        "ccf_config.yaml — the whole Control Plane, {lines} lines",
        "The lambda_c table keys on ENTITY CLASS, because that is what the"
        " reference debt scorer reads, and each row declares which instant it"
        " decays against (D-IMPL-331)."),
    "backends": ("backends.yaml",
        "backends.yaml — {lines} lines, and no credential in any of them", ""),
    "question": ("artifacts/question.yaml",
        "artifacts/question.yaml — {lines} lines, including the as-of pin", ""),
    "sources": ("artifacts/signal-sources.yaml",
        "artifacts/signal-sources.yaml — the two rate feeds and the window each CLAIMS",
        "A coverage window is a property of the source, not an age of the"
        " answer. A feed whose window excludes the decision instant is ABSENT."),
    "staleness": ("artifacts/staleness-profile.yaml",
        "artifacts/staleness-profile.yaml — the refusal rule, per signal class",
        "ccf_config.yaml's half_life: is the DECAY model; this is the REFUSAL"
        " rule. A class can decay without being able to refuse."),
    "gates": ("artifacts/gates.yaml",
        "artifacts/gates.yaml — 22 declared gates, each with its sabotage outcome",
        "sabotage_state has three values. Four gates are `unavailable`: their"
        " bad state is unreachable from this example because an SDK guard"
        " prevents it, so they are NOT 'tested and passed'."),
    "acquisition": ("acquisition.py",
        "acquisition.py — {lines} lines, the two source reads", ""),
    "deployment": ("deployment.py",
        "deployment.py — {lines} lines, the interpreter", ""),
    "projection": ("projection.py",
        "projection.py — {lines} lines, where four clocks would otherwise be flattened", ""),
    "produce": ("produce.py",
        "produce.py — {lines} lines, the spine: boot, acquire, govern", ""),
    "run_py": ("run.py", "run.py — {lines} lines, the client", ""),
    "readme": ("README.md", "README.md — {lines} lines", ""),
    "summary": ("summary_explanations.md",
        "summary_explanations.md — {lines} lines, for three readers at once", ""),
    "tests": ("tests/examples/test_cp_09_output.py",
        "tests/examples/test_cp_09_output.py — {lines} lines, {tests} tests", ""),
}


#: The Python files, and whose they are. **No line count here** — the counts
#: come from the same read that fills the page. cp-01's four typed counts, and
#: the file it named that does not exist here, are the measured reason.
SPLIT: tuple[tuple[str, str, str, str], ...] = (
    ("deployment.py", "yours", "warn",
     "Everything. The source reads, the envelopes and their order, the measured"
     " C and S, and the deployment half of the declared gate."),
    ("projection.py", "yours", "warn",
     "Everything. The four temporal classes, the concentration verdicts and the"
     " signal register."),
    ("acquisition.py", "yours", "warn",
     "The queries and the window bound. Nothing else in the tree knows a table"
     " name or a ledger name."),
    ("produce.py", "nearly fixed", "yes",
     "Almost nothing. It names no client, no currency and no table — boot,"
     " acquire, govern, and one named plan_factory."),
    ("run.py", "nearly fixed", "yes",
     "The flags a caller needs and what the run prints. The demonstration"
     " question itself is an artifact, not code."),
)

#: Which files count as declared artifacts for the ratio sentence.
ARTIFACTS: tuple[str, ...] = (
    "ccf_config.yaml", "backends.yaml",
    "artifacts/question.yaml", "artifacts/signal-sources.yaml",
    "artifacts/staleness-profile.yaml", "artifacts/source-vocabulary.yaml",
    "artifacts/gates.yaml",
)


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


def _split() -> tuple[str, str]:
    """The ownership table and its ratio sentence, both COUNTED from the tree.

    The inherited version carried four typed counts and named `assembler.py`,
    which this example does not contain. Reading the files here means the table
    cannot describe an example that no longer exists, and cannot name one that
    never did — a missing file raises rather than rendering.
    """
    rows, yours, fixed = [], 0, 0
    for name, whose, pill, changes in SPLIT:
        count = _lines(_resolve(name).read_text(encoding="utf-8"))
        if whose == "yours":
            yours += count
        else:
            fixed += count
        rows.append(
            f"<tr><td><code>{html.escape(name)}</code></td>"
            f'<td class="num">{count:,}</td>'
            f'<td><span class="pill {pill}">{html.escape(whose)}</span></td>'
            f"<td>{html.escape(changes)}</td></tr>"
        )
    table = (
        "<table><thead><tr><th>File</th><th class=\"num\">Lines</th>"
        "<th>Whose</th><th>What changes per product</th></tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody></table>"
    )
    declared = sum(
        _lines(_resolve(name).read_text(encoding="utf-8")) for name in ARTIFACTS
    )
    ratio = (
        f"<p>The ratio is the honest measure of what adopting this costs:"
        f" roughly <strong>{yours:,} lines you write</strong> against"
        f" <strong>{fixed:,} you read once</strong> — and against"
        f" <strong>{declared:,} lines of declared artifacts</strong> that carry"
        f" everything specific. If your code would still run meaningfully with"
        f" the artifacts deleted, something has been hardcoded that should not"
        f" have been.</p>"
    )
    return table, ratio


def build() -> str:
    page = TEMPLATE.read_text(encoding="utf-8")
    page = page.replace(
        "{{run}}", html.escape(RUN_TRANSCRIPT.read_text(encoding="utf-8"))
    )
    table, ratio = _split()
    page = page.replace("{{split_table}}", table)
    page = page.replace("{{split_ratio}}", ratio)
    for key, (path, label, note) in BLOCKS.items():
        page = page.replace("{{" + key + "}}", _details(path, label, note))
    # THE PLACEHOLDER FORM, not any brace pair. cp-01's version tested
    # `"{{" in page` and would refuse this page forever: `acquisition.py`
    # embeds a SPARQL f-string whose literal braces are doubled, and that file
    # is displayed verbatim below. Narrowing the check to `{{name}}` keeps what
    # it was for — an unfilled slot must never ship — without failing on the
    # content it is displaying.
    leftover = re.findall(r"\{\{\w+\}\}", page)
    if leftover:
        raise SystemExit(
            f"unreplaced placeholder(s) in {TEMPLATE}: {sorted(set(leftover))}"
        )
    return page


if __name__ == "__main__":
    rendered = build()
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(REPO)}  {len(rendered) / 1024:.0f} KB")
