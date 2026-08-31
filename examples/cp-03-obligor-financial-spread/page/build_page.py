"""Assemble this example's documentation page from `template.html`.

**Run from the repository root:**

    .venv/bin/python examples/cp-03-obligor-financial-spread/page/build_page.py

Writes `page/cp-03.html`, which is then published as an artifact. **The rendered
page is NOT committed** — the generator and the template are, because they are
the reproducible things and the embedded source is not.

**WHY A GENERATOR AND NOT THE PAGE.** Every collapsible on the page is a
verbatim copy of a file in this example. Committing the rendered HTML would put
each of those files in the tree twice, and the copies would drift the first time
an artifact changed and nobody remembered to republish. This script reads the
real files at build time, so the page cannot describe a version of the example
that no longer exists.

**THE PRINTED RUN IS THE ONE THING IT DOES NOT GENERATE.** `RUN_TRANSCRIPT` is a
committed artifact of a run against a NAMED SNAPSHOT, because a page that re-ran
the product on every build would print whatever the estate said today — and a
printed run that can drift is a documentation defect that presents as a fabric
defect. Regenerate it deliberately, with the anchor pinned, and say so.

**THE COMMIT IS INJECTED RATHER THAN TYPED.** `D-IMPL-218` requires the page to
name its snapshot: the commit, the `asked_at` pin and the content address. A
commit hash written into the template by hand is stale the moment the next
commit lands, and nobody notices because it still looks like a hash. This script
asks `git` at build time instead.
"""

from __future__ import annotations

import html
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
EXAMPLE = HERE.parent
REPO = EXAMPLE.parents[1]

TEMPLATE = HERE / "template.html"
RUN_TRANSCRIPT = HERE / "run-transcript.txt"
OUTPUT = HERE / "cp-03.html"

#: Placeholder -> (path, summary label, note). Paths are relative to the
#: example, except `tests/...` which is repo-relative.
#:
#: EVERY SOURCE FILE IS BEHIND A PLACEHOLDER — cp-01's shape rather than
#: cp-00's. A partial generator keeps hand-cut excerpts in the template, and an
#: excerpt is a copy that can drift while looking authoritative.
BLOCKS: dict[str, tuple[str, str, str]] = {
    "spec": (
        "spec/CP-SPEC-003_Obligor_Financial_Spread.md",
        "The specification — written first, approved before any code",
        "Gate 1 was approved on a full read of this document. Everything below"
        " is derived from it, including the fourteen gates and the record of"
        " what each was sabotaged with.",
    ),
    "config": ("ccf_config.yaml", "ccf_config.yaml — the whole Control Plane", ""),
    "backends": (
        "backends.yaml",
        "backends.yaml — the store binding, and no credential in any of it",
        "It carries the environment variable's NAME. No host, no port, no"
        " password ever enters the tree.",
    ),
    "question": (
        "artifacts/question.yaml",
        "artifacts/question.yaml — the caller's vocabulary and the pinned question",
        "Nothing in any module names an LEI. Changing the subject here re-asks"
        " the same question of another obligor.",
    ),
    "spread_lines": (
        "artifacts/spread-lines.yaml",
        "artifacts/spread-lines.yaml — the line vocabulary and each line's declared kind",
        "",
    ),
    "restatement": (
        "artifacts/restatement.yaml",
        "artifacts/restatement.yaml — the two credit-policy judgments",
        "What makes two rows the same fact, and which corrections are material."
        " Both are values wearing numeric clothing, which is why neither is a"
        " constant in code.",
    ),
    "ttl": ("artifacts/ttl.yaml", "artifacts/ttl.yaml — the anchor and the window", ""),
    "recipe": (
        "artifacts/assembly-recipe.yaml",
        "artifacts/assembly-recipe.yaml — every step with what it reads",
        "",
    ),
    "expected": (
        "artifacts/expected.yaml",
        "artifacts/expected.yaml — deriving nothing from a run",
        "It also declares the witnesses the gates address by name. A gate that"
        " picked its own subject would pick the subject that makes it pass.",
    ),
    "deployment": (
        "deployment.py",
        "deployment.py — the interpreter, and the only file that names a table",
        "",
    ),
    "produce": (
        "produce.py",
        "produce.py — the spine, which names no table, no column and no domain word",
        "",
    ),
    "assembler": ("assembler.py", "assembler.py — the governed client seam", ""),
    "run_py": ("run.py", "run.py — the command-line driver", ""),
    "tests": (
        "tests/examples/test_cp_03_output.py",
        "tests/examples/test_cp_03_output.py — the fourteen gates",
        "Every one of them has been made to fail deliberately. Three passed"
        " their first sabotage and had to be rewritten.",
    ),
    "tests_census": (
        "tests/examples/test_cp_03_census.py",
        "tests/examples/test_cp_03_census.py — the census, and four wrong methods",
        "Each control asserts BOTH its specific wrong number AND that it"
        " differs from the census, so a control that stops discriminating is"
        " itself detected rather than passing quietly.",
    ),
    "readme": ("README.md", "README.md — for somebody building one of these", ""),
    "summary": (
        "summary_explanations.md",
        "summary_explanations.md — the same product, for the people funding it",
        "",
    ),
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


def _commit() -> str:
    """The tree this page was built from, asked of git rather than typed."""
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):  # pragma: no cover
        return "unknown"


def build() -> str:
    page = TEMPLATE.read_text(encoding="utf-8")
    page = page.replace(
        "{{run}}", html.escape(RUN_TRANSCRIPT.read_text(encoding="utf-8"))
    )
    page = page.replace("{{commit}}", html.escape(_commit()))
    for key, (path, label, note) in BLOCKS.items():
        page = page.replace("{{" + key + "}}", _details(path, label, note))
    if "{{" in page:
        raise SystemExit(f"unreplaced placeholder in {TEMPLATE}")
    return page


if __name__ == "__main__":
    rendered = build()
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(REPO)}  {len(rendered) / 1024:.0f} KB")
