"""Assemble this example's documentation page from `template.html`.

**Run from the repository root:**

    python examples/cp-13-covenant-cross-reference/page/build_page.py

Writes `page/cp-13.html`, which is then published as an artifact. The rendered
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
OUTPUT = HERE / "cp-13.html"

#: Placeholder -> the file whose contents fill it, and the summary label.
#: Paths are relative to the example, except `tests/...` which is repo-relative.
#:
#: The label is a TEMPLATE. `{lines}` and `{tests}` are filled at build time
#: from the file being displayed; a numeric literal in a label here is the
#: defect this shape exists to make impossible.
BLOCKS: dict[str, tuple[str, str, str]] = {
    "spec": (
        "spec/CP-SPEC-013_Covenant_Cross_Reference.md",
        "The specification — {lines} lines, and the first thing written",
        "Authored at Gate 1 with all three stores measured first. Amended when"
        " the estate owner repaired a defect this rung had been specified"
        " around: the history is preserved as `FIXED-upstream` rather than"
        " rewritten.",
    ),
    "config": ("ccf_config.yaml",
        "ccf_config.yaml — the whole Control Plane, {lines} lines",
        "Every λ_c class is `supersede-only`, and not as a calibration choice:"
        " no class in this chain carries any temporal predicate at all, so a"
        " decaying rate has nothing to read (`CP13-F-15`)."),
    "backends": ("backends.yaml",
        "backends.yaml — {lines} lines, three stores and no credential in any of them", ""),
    "vocabulary": ("artifacts/source-vocabulary.yaml",
        "artifacts/source-vocabulary.yaml — {lines} lines, every source term named once",
        "Carries `absent_predicates`, which names `ex:governedBy` as ABSENT"
        " rather than forgotten. A predicate the published schema names and the"
        " estate does not hold is declared, never proxied."),
    "question": ("artifacts/question.yaml",
        "artifacts/question.yaml — {lines} lines, including the principal and the as-of pin",
        "The principal is the axis this rung is about: it changes which"
        " documents EXIST for the request, not merely which fields return."),
    "gates": ("artifacts/gates.yaml",
        "artifacts/gates.yaml — {gates} declared gates, each with its sabotage outcome",
        "Nineteen `passed`, three `unavailable`. FOUR were green under their"
        " first sabotage and all four were TEST defects, each recorded with"
        " what was wrong."),
    "acquisition": ("acquisition.py",
        "acquisition.py — {lines} lines, three source legs and one rule about citations",
        "A citation is a named passage reached through `ex:evidencedBy`,"
        " re-hashed before it is emitted. `_cite` is the only constructor."),
    "deployment": ("deployment.py",
        "deployment.py — {lines} lines, the interpreter",
        "A citation is its own entity, so a node can carry two without either"
        " becoming a property of the other — the shape the upstream URI"
        " collision violated."),
    "projection": ("projection.py",
        "projection.py — {lines} lines, the chain and the reason for every absence", ""),
    "produce": ("produce.py",
        "produce.py — {lines} lines, the spine: boot, acquire, govern",
        "No binder, no universal gates, no replay record, no debt scorer."),
    "run_py": ("run.py", "run.py — {lines} lines, the client", ""),
    "tests": ("tests/examples/test_cp_13_output.py",
        "tests/examples/test_cp_13_output.py — {lines} lines, {tests} tests", ""),
    "findings": ("FINDINGS.md",
        "FINDINGS.md — {lines} lines, {findings} findings and none open", ""),
    "readme": ("README.md", "README.md — {lines} lines", ""),
    "summary": ("summary_explanations.md",
        "summary_explanations.md — {lines} lines, for three readers at once", ""),
}

#: The four Python files, and whose they are. **No line count here** — the
#: counts come from the same read that fills the page.
SPLIT: tuple[tuple[str, str, str, str], ...] = (
    ("deployment.py", "yours", "warn",
     "Everything. The request shape, the envelopes and their order, and the"
     " deployment half of the one declared gate."),
    ("projection.py", "yours", "warn",
     "Everything. The chain, the checked citations, the closed debt vocabulary"
     " and the policy envelope the payload carries."),
    ("acquisition.py", "yours", "warn",
     "Three source legs and the citation rule. Nothing else in the tree knows"
     " an IRI, a collection or a table name."),
    ("produce.py", "nearly fixed", "yes",
     "Almost nothing. It names no covenant, no document and no store — boot,"
     " acquire, govern, and one named plan_factory."),
    ("run.py", "nearly fixed", "yes",
     "The flags a caller needs and what the run prints. The demonstration"
     " question itself is an artifact, not code."),
)

#: Which files count as declared artifacts for the ratio sentence.
ARTIFACTS: tuple[str, ...] = (
    "ccf_config.yaml", "backends.yaml",
    "artifacts/source-vocabulary.yaml", "artifacts/question.yaml",
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


def _gates(source: str) -> int:
    """Declared gates in `source`, parsed rather than counted by eye.

    The caption used to carry this number as a literal, while this module's
    own docstring said no count on the page is typed. Two typed counts is how
    that claim stops being true, so both are now read from the file being
    displayed.
    """
    import yaml

    return len(yaml.safe_load(source)["declaration"]["gates"])


def _findings(source: str) -> int:
    """Distinct `CPNN-F-NN` ids in `source`, by id rather than by mention.

    The set, not the count of matches: every finding appears in the summary
    table AND, for the Gate-2 ones, in its own section.
    """
    return len(set(re.findall(r"CP\d\d-F-\d\d", source)))


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
    if "{gates}" in filled:
        filled = filled.replace("{gates}", f"{_gates(source):,}")
    if "{findings}" in filled:
        filled = filled.replace("{findings}", f"{_findings(source):,}")
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
