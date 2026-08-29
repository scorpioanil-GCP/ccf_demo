"""Assemble this example's documentation page from `template.html`.

**Run from the repository root:**

    python examples/cp-01-counterparty-reference-snapshot/page/build_page.py

Writes `page/cp-01.html`, which is then published as an artifact. The rendered
page is NOT committed — the generator and the template are, because they are the
reproducible things and the 273 KB of embedded source is not.

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
OUTPUT = HERE / "cp-01.html"

#: Placeholder -> the file whose contents fill it, and the summary label.
#: Paths are relative to the example, except `tests/...` which is repo-relative.
BLOCKS: dict[str, tuple[str, str, str]] = {
    "spec": (
        "spec/CP-SPEC-001_Counterparty_Reference_Snapshot.md",
        "The specification — 1,351 lines, and the first thing written",
        "Authored at Gate 1 and approved before a line of code existed."
        " Every artifact below is derived from it.",
    ),
    "config": ("ccf_config.yaml", "ccf_config.yaml — the whole Control Plane, 334 lines", ""),
    "backends": ("backends.yaml", "backends.yaml — 75 lines, and no credential in any of them", ""),
    "question": ("artifacts/question.yaml", "artifacts/question.yaml — 95 lines", ""),
    "ttl": ("artifacts/ttl.yaml", "artifacts/ttl.yaml — 66 lines", ""),
    "recipe": ("artifacts/assembly-recipe.yaml", "artifacts/assembly-recipe.yaml — every step with its runtime witness", ""),
    "expected": ("artifacts/expected.yaml", "artifacts/expected.yaml — 171 lines, deriving nothing from a run", ""),
    "deployment": ("deployment.py", "deployment.py — 970 lines, the interpreter", ""),
    "produce": ("produce.py", "produce.py — 389 lines, the spine", ""),
    "assembler": ("assembler.py", "assembler.py — 268 lines, the governed seam", ""),
    "run_py": ("run.py", "run.py — 187 lines, the client", ""),
    "readme": ("README.md", "README.md — 220 lines", ""),
    "tests": ("tests/examples/test_cp_01_output.py", "tests/examples/test_cp_01_output.py — 386 lines, 13 tests", ""),
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
