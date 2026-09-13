"""Assemble this example's documentation page from `template.html`.

**Run from the repository root:**

    python examples/cp-11-credit-surveillance-early-warning/page/build_page.py

Writes `page/cp-10.html`, which is then published as an artifact. The rendered
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
OUTPUT = HERE / "cp-11.html"

#: Placeholder -> the file whose contents fill it, and the summary label.
#: Paths are relative to the example, except `tests/...` which is repo-relative.
#:
#: The label is a TEMPLATE. `{lines}` and `{tests}` are filled at build time
#: from the file being displayed; a numeric literal in a label here is the
#: defect this shape exists to make impossible.
BLOCKS: dict[str, tuple[str, str, str]] = {
    "spec": (
        "spec/CP-SPEC-011_Credit_Surveillance_Early_Warning.md",
        "The specification — {lines} lines, and the first thing written",
        "Authored at Gate 1 with the estate measured first. Gate 1 was HELD on"
        " §0.4 rather than shipping a substitute for the invalidation cascade,"
        " and §0.4 was amended once the SDK gained the mechanism.",
    ),
    "config": ("ccf_config.yaml",
        "ccf_config.yaml — the whole Control Plane, {lines} lines",
        "The λ_c table here drives `F`, the Context Debt freshness term. The"
        " estate's `signal_weight.decay_days` drives the composite score. Two"
        " models, two questions, and `EWS-G29` keeps them apart."),
    "backends": ("backends.yaml",
        "backends.yaml — {lines} lines, and no credential in any of them", ""),
    "vocabulary": ("artifacts/source-vocabulary.yaml",
        "artifacts/source-vocabulary.yaml — {lines} lines, every source term named once",
        "Carries the SIC -> division mapping with its own semver and"
        " provenance, and the DECLARED list of classes that participate in"
        " supersession. Empty that list and the rung's central trap opens in"
        " one edit."),
    "escalation": ("artifacts/escalation-policy.yaml",
        "artifacts/escalation-policy.yaml — {lines} lines, and the estate's own bands beside them",
        "The estate declares 0.30 / 0.55 / 0.85, calibrated against a reading"
        " this product refuses. Both sets are carried so the calibration"
        " decision is visible rather than silently applied."),
    "question": ("artifacts/question.yaml",
        "artifacts/question.yaml — {lines} lines, including the as-of pin",
        "The as-of pin lives here because it is a REQUEST parameter. A program"
        " that read a clock would make its own answer unreproducible."),
    "gates": ("artifacts/gates.yaml",
        "artifacts/gates.yaml — 29 declared gates, each with its sabotage outcome",
        "Twenty-five `passed`, three `unavailable`, one `not-required`. THREE"
        " gates were wrong on the first attempt and all three are recorded —"
        " two green under their own sabotage, one red against correct code."),
    "acquisition": ("acquisition.py",
        "acquisition.py — {lines} lines, the two source legs",
        "PostgreSQL carries the clock; Fluree carries the chain and NO"
        " timestamp at all. No date is ever parsed out of a label."),
    "deployment": ("deployment.py",
        "deployment.py — {lines} lines, the interpreter", ""),
    "projection": ("projection.py",
        "projection.py — {lines} lines, the delta and the composite", ""),
    "produce": ("produce.py",
        "produce.py — {lines} lines, the spine: boot, acquire, govern",
        "No binder, no universal gates, no replay record, no debt scorer."),
    "run_py": ("run.py", "run.py — {lines} lines, the client", ""),
    "tests": ("tests/examples/test_cp_11_output.py",
        "tests/examples/test_cp_11_output.py — {lines} lines, {tests} tests", ""),
    "findings": ("FINDINGS.md",
        "FINDINGS.md — {lines} lines, ten findings and none open", ""),
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
     "Everything. The delta, the supersession filter, the decayed"
     " contributions, the bands, the coverage and the exclusion list."),
    ("acquisition.py", "yours", "warn",
     "The two source legs and the delta bound. Nothing else in the tree knows"
     " a table name or an IRI."),
    ("produce.py", "nearly fixed", "yes",
     "Almost nothing. It names no obligor, no signal class and no table —"
     " boot, acquire, govern, and one named plan_factory."),
    ("run.py", "nearly fixed", "yes",
     "The flags a caller needs and what the run prints. The demonstration"
     " question itself is an artifact, not code."),
)

#: Which files count as declared artifacts for the ratio sentence.
ARTIFACTS: tuple[str, ...] = (
    "ccf_config.yaml", "backends.yaml",
    "artifacts/source-vocabulary.yaml", "artifacts/escalation-policy.yaml",
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
