"""Assemble this example's documentation page from `template.html`.

**Run from the repository root:**

    python examples/cp-12-fx-post-trade-reconciliation/page/build_page.py

Writes `page/cp-12.html`, which is then published as an artifact. The rendered
page is NOT committed — the generator and the template are, because they are the
reproducible things and the embedded source is not.

**WHY A GENERATOR AND NOT THE PAGE.** Every collapsible on the page is a
verbatim copy of a file in this example. Committing the rendered HTML would put
each of those files in the tree twice, and the copies would drift the first time
a `.yaml` changed and nobody remembered to republish. This script reads the real
files at build time, so the page cannot describe a version of the example that
no longer exists.

**The printed run is the one thing it does NOT generate.** `RUN_TRANSCRIPT` is a
committed artifact of runs against a NAMED SNAPSHOT, because a page that re-ran
the product on every build would print whatever the estate said today — and a
printed run that can drift is a documentation defect that presents as a fabric
defect. Regenerate it deliberately, with the anchors pinned, and say so.

**NO COUNT ON THIS PAGE IS TYPED** (`24.6-L-11`, and the reason is measured).
cp-09's template inherited cp-01's "the half you write" table with four
hand-typed line counts and a file that does not exist in cp-09 at all. Counts
typed beside a file the same script already reads always drift, so here BOTH the
captions and that whole table are computed from the same read that fills the
page — see `_caption` and `_split`.

**AND THE MASTHEAD IS THIS EXAMPLE'S OWN.** `tests/examples/test_page_identity.py`
asserts it: title, eyebrow and footer must name this example, no other example's
directory may appear, and every file the prose points at must exist here. That
gate exists because cp-09's page published as cp-01 for a day.
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
OUTPUT = HERE / "cp-12.html"

#: Placeholder -> the file whose contents fill it, and the summary label.
#: Paths are relative to the example, except `tests/...` which is repo-relative.
#:
#: The label is a TEMPLATE. `{lines}` and `{tests}` are filled at build time
#: from the file being displayed; a numeric literal in a label here is the
#: defect this shape exists to make impossible.
BLOCKS: dict[str, tuple[str, str, str]] = {
    "spec": (
        "spec/CP-SPEC-012_FX_Post_Trade_Reconciliation.md",
        "The specification — {lines} lines, and the first thing written",
        "Authored at Gate 1 with the estate measured first. Amended twice at"
        " Gate 2: scenario 1 named a trade the product's own binding refuses"
        " (`CP12-F-11`), and §B.5 was split so the 1-hour production reference"
        " and the 48-hour bound value can never read as one contract.",
    ),
    "config": ("ccf_config.yaml",
        "ccf_config.yaml — the whole Control Plane, {lines} lines",
        "The λ_c row here is THE BOUND VALUE — 48 hours, CP-12's disclosed"
        " illustrative half-life. The 1-hour production freshness reference"
        " lives in the specification's prose and is bound nowhere."),
    "backends": ("backends.yaml",
        "backends.yaml — {lines} lines, and no credential in any of them", ""),
    "vocabulary": ("artifacts/source-vocabulary.yaml",
        "artifacts/source-vocabulary.yaml — {lines} lines, every source term named once",
        "Carries `absent_legs`, which names `settlesVia` and `netsWith` as"
        " ABSENT rather than empty. A predicate nothing asserts is not a"
        " predicate asserting nothing."),
    "pipscale": ("artifacts/pip-scale.yaml",
        "artifacts/pip-scale.yaml — {lines} lines, and `no_default: true`",
        "The scale at which a pair quotes is a market convention this product"
        " ASSERTS, not a fact it derives — so it carries a semver and a"
        " provenance. An undeclared pair is refused, because defaulting to"
        " 0.0001 is how a JPY-quoted variance reads a hundred times too small."),
    "question": ("artifacts/question.yaml",
        "artifacts/question.yaml — {lines} lines, including the as-of pin",
        "The as-of pin lives here because it is a REQUEST parameter. A program"
        " that read a clock would make its own answer unreproducible."),
    "gates": ("artifacts/gates.yaml",
        "artifacts/gates.yaml — 28 declared gates, each with its sabotage outcome",
        "Twenty-five `passed`, three `unavailable`. FIVE gates were green under"
        " their first sabotage and all five are recorded — four weak sabotages"
        " and one weak test."),
    "acquisition": ("acquisition.py",
        "acquisition.py — {lines} lines, the two source legs",
        "PostgreSQL carries the values and Fluree carries the instants:"
        " `system_trade_record` has no timestamp column at all."),
    "deployment": ("deployment.py",
        "deployment.py — {lines} lines, the interpreter",
        "An observation's `observed_time` is the instant the system RECORDED."
        " Never the corrected instant — that is `FXR-G24`."),
    "projection": ("projection.py",
        "projection.py — {lines} lines, the partition and the decomposition",
        "Six things it refuses to do, each because one was measured at Gate 1."),
    "produce": ("produce.py",
        "produce.py — {lines} lines, the spine: boot, acquire, govern",
        "No binder, no universal gates, no replay record, no debt scorer."),
    "run_py": ("run.py", "run.py — {lines} lines, the client", ""),
    "tests": ("tests/examples/test_cp_12_output.py",
        "tests/examples/test_cp_12_output.py — {lines} lines, {tests} tests", ""),
    "findings": ("FINDINGS.md",
        "FINDINGS.md — {lines} lines, sixteen findings and none open", ""),
    "readme": ("README.md", "README.md — {lines} lines", ""),
    "summary": ("summary_explanations.md",
        "summary_explanations.md — {lines} lines, for three readers at once", ""),
}

#: The four Python files, and whose they are. **No line count here** — the
#: counts come from the same read that fills the page.
SPLIT: tuple[tuple[str, str, str, str], ...] = (
    ("deployment.py", "yours", "warn",
     "Everything. The request shape, the envelopes and their order, the"
     " measured C and S, and the deployment half of the one declared gate."),
    ("projection.py", "yours", "warn",
     "Everything. The alignment, the agreement partition, the verdict, the"
     " variance decomposition and every refusal to produce one."),
    ("acquisition.py", "yours", "warn",
     "The two source legs and the as-of bound. Nothing else in the tree knows"
     " a table name or an IRI."),
    ("produce.py", "nearly fixed", "yes",
     "Almost nothing. It names no trade, no system and no table — boot,"
     " acquire, govern, and one named plan_factory."),
    ("run.py", "nearly fixed", "yes",
     "The flags a caller needs and what the run prints. The demonstration"
     " question itself is an artifact, not code."),
)

#: Which files count as declared artifacts for the ratio sentence.
ARTIFACTS: tuple[str, ...] = (
    "ccf_config.yaml", "backends.yaml",
    "artifacts/source-vocabulary.yaml", "artifacts/pip-scale.yaml",
    "artifacts/question.yaml", "artifacts/gates.yaml",
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

    An unfilled placeholder raises: a caption reading "{lines} lines" on a
    published page is the same class of defect as a stale number, and it must
    not render.
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

    cp-09's inherited version carried four typed counts and named a file that
    tree does not contain. Reading the files here means the table cannot
    describe an example that no longer exists, and cannot name one that never
    did — a missing file raises rather than rendering.
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
    # THE PLACEHOLDER FORM, not any brace pair: `acquisition.py` embeds a
    # SPARQL f-string whose literal braces are doubled, and that file is
    # displayed verbatim below. Narrowing the check to `{{name}}` keeps what it
    # is for — an unfilled slot must never ship — without failing on the
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
