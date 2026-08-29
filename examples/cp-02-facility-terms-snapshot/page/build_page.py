"""Assemble this example's documentation page from `template.html`.

**Run from the repository root:**

    python examples/cp-02-facility-terms-snapshot/page/build_page.py

Writes `page/cp-01.html`, which is then published as an artifact. The rendered
page is NOT committed — the generator and the template are, because they are the
reproducible things and the embedded source is not.

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
"""

from __future__ import annotations

import html
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
EXAMPLE = HERE.parent
REPO = EXAMPLE.parents[1]

TEMPLATE = HERE / "template.html"
RUN_TRANSCRIPT = HERE / "run-transcript.txt"
OUTPUT = HERE / "cp-02.html"

#: Placeholder -> the file whose contents fill it, and the summary label.
#: Paths are relative to the example, except `tests/...` which is repo-relative.
BLOCKS: dict[str, tuple[str, str, str]] = {
    "spec": (
        "spec/CP-SPEC-002_Facility_Terms_Snapshot.md",
        "The specification — the first thing written",
        "Authored at Gate 1 and approved before a line of code existed."
        " Every artifact below is derived from it.",
    ),
    "config": ("ccf_config.yaml", "ccf_config.yaml — the whole Control Plane", ""),
    "backends": ("backends.yaml", "backends.yaml — and no credential in any of it", ""),
    "question": ("artifacts/question.yaml", "artifacts/question.yaml — the caller's vocabulary", ""),
    "ttl": ("artifacts/ttl.yaml", "artifacts/ttl.yaml — the window, and the measurement that constrains it", ""),
    "recipe": ("artifacts/assembly-recipe.yaml", "artifacts/assembly-recipe.yaml — every step with its runtime witness", ""),
    "expected": ("artifacts/expected.yaml", "artifacts/expected.yaml — deriving nothing from a run", ""),
    "deployment": ("deployment.py", "deployment.py — the interpreter", ""),
    "produce": ("produce.py", "produce.py — the spine, with the seven canonical regions", ""),
    "assembler": ("assembler.py", "assembler.py — the governed seam", ""),
    "run_py": ("run.py", "run.py — the client", ""),
    "readme": ("README.md", "README.md — for somebody building one of these", ""),
    "summary": ("summary_explanations.md", "summary_explanations.md — the same product, for a banker", ""),
    "tests": ("tests/examples/test_cp_02_output.py", "tests/examples/test_cp_02_output.py — 20 tests, 11 sabotaged", ""),
}


def _resolve(path: str) -> pathlib.Path:
    return REPO / path if path.startswith("tests/") else EXAMPLE / path


def _details(path: str, label: str, note: str) -> str:
    body = html.escape(_resolve(path).read_text(encoding="utf-8"))
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
