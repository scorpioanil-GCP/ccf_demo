"""Assemble this example's documentation page from `template.html`.

**Run from the repository root:**

    .venv/bin/python examples/cp-04-corporate-family-tree/page/build_page.py

Writes `page/cp-04.html`, which is then published as an artifact. **The rendered
page is NOT committed** — the generator and the template are, because they are
the reproducible things and the embedded source is not. `.gitignore` enforces
the split: `examples/*/page/*.html` is excluded and `template.html` re-included.

**WHY A GENERATOR AND NOT THE PAGE.** Every collapsible on the page is a
verbatim copy of a file in this example. Committing the rendered HTML would put
each of those files in the tree twice, and the copies would drift the first time
an artifact changed and nobody remembered to republish. This script reads the
real files at build time, so the page cannot describe a version of the example
that no longer exists.

**EVERY SOURCE FILE IS BEHIND A PLACEHOLDER** — cp-01's shape rather than
cp-00's. A partial generator keeps hand-cut excerpts in the template, and an
excerpt is a copy that can drift while looking authoritative.

**THE PRINTED RUN IS THE ONE THING IT DOES NOT GENERATE.** `RUN_TRANSCRIPT` is a
committed artifact of a run against a NAMED SNAPSHOT, because a page that re-ran
the product on every build would print whatever the estate said today — and a
printed run that can drift is a documentation defect that presents as a fabric
defect. Regenerate it deliberately, with the anchor and the `asked_at` pinned,
and say so.

**THE SNAPSHOT IS DECLARED HERE AND VERIFIED AGAINST THE TREE AT BUILD TIME.**
`D-IMPL-218` requires the page to name its snapshot: the commit, the `asked_at`
pin, the `ledger_t` and the content address. Two of those four are checkable
against files this repository already holds, and :func:`_verify_snapshot` checks
them rather than trusting this module:

* `asked_at` and `content_address` must appear **in the committed transcript**.
  A snapshot sentence that named a different run than the one printed beside it
  is precisely the drift `D-IMPL-218` exists to prevent, and it would otherwise
  be invisible — both are long opaque strings that look right whatever they say.
* `ledger_t` must equal `artifacts/expected.yaml::census.ledger_t_read_at`,
  which is the reviewed artifact that derives nothing from a run. The
  transaction counter is NOT printed by the program, so the transcript cannot
  check it; the reviewed artifact can.

A build whose snapshot disagrees with either **refuses** rather than publishing
a page that misattributes its own run.

**WHY THE SNAPSHOT IS NOT A HEADER INSIDE THE TRANSCRIPT.** `run-transcript.txt`
is the program's exact stdout and nothing else, so `make -s example-cp-04`
reproduces it **byte for byte** and the diff that proves it needs no
normalization step to go wrong in. A header would have made that diff
approximate, and an approximate diff is the check that quietly stops
discriminating.

**THE COMMIT IS INJECTED RATHER THAN TYPED.** A commit hash written into the
template by hand is stale the moment the next commit lands, and nobody notices
because it still looks like a hash. This script asks `git` at build time, so the
commit the page names is the tree it was built from — which is the tree that
holds this transcript.
"""

from __future__ import annotations

import html
import pathlib
import re
import subprocess

import yaml

HERE = pathlib.Path(__file__).resolve().parent
EXAMPLE = HERE.parent
REPO = EXAMPLE.parents[1]

TEMPLATE = HERE / "template.html"
RUN_TRANSCRIPT = HERE / "run-transcript.txt"
OUTPUT = HERE / "cp-04.html"

#: The reviewed artifact the ledger transaction is cross-checked against.
EXPECTED = EXAMPLE / "artifacts" / "expected.yaml"

#: The snapshot the committed transcript is a run at — `D-IMPL-218`. Three of
#: the four values are here; the fourth, the commit, is asked of git below.
#: :func:`_verify_snapshot` refuses a build whose values disagree with the tree.
SNAPSHOT: dict[str, str] = {
    "asked_at": "2026-08-31T12:00:00+00:00",
    "ledger_t": "5112",
    "content_address": (
        "fad6e55da2c0e6276b69d9a053e4eff155e5c3266b68f3fffb873b0c5e754fc7"
    ),
    "anchor": "54930022CZO1N2UGVW07",
}

#: Placeholder -> (path, summary label, note). Paths are relative to the
#: example, except `tests/...` which is repo-relative.
BLOCKS: dict[str, tuple[str, str, str]] = {
    "spec": (
        "spec/CP-SPEC-004_Corporate_Family_Tree.md",
        "The specification — written first, approved before any code",
        "Gate 1 was approved on a full read of this document. Everything below"
        " derives from it, including the sixteen gates, the sabotage recorded"
        " against each, and the eleven gaps raised and left open.",
    ),
    "config": ("ccf_config.yaml", "ccf_config.yaml — the whole Control Plane", ""),
    "backends": (
        "backends.yaml",
        "backends.yaml — two store bindings, and no credential in any of it",
        "It carries four environment variable NAMES and their remedy strings."
        " No host, no port, no path, no password ever enters the tree.",
    ),
    "question": (
        "artifacts/question.yaml",
        "artifacts/question.yaml — the caller's vocabulary and the pinned question",
        "Nothing in any module names an LEI. Changing the subject here re-asks"
        " the same question of another family.",
    ),
    "vocabulary": (
        "artifacts/source-vocabulary.yaml",
        "artifacts/source-vocabulary.yaml — where every value comes from",
        "The six family predicates with the DIRECTION each is read in, the"
        " attribute table and its columns, the duplicate-identity rule, and the"
        " served jurisdiction set, closed in both directions.",
    ),
    "ttl": (
        "artifacts/ttl.yaml",
        "artifacts/ttl.yaml — the window, the ceiling, and the anchor they measure against",
        "Two fields rather than one, deliberately: the declared TTL is what this"
        " class CLAIMS and the ceiling is what the gate REFUSES above. One"
        " figure serving as both would have the gate check arithmetic it had"
        " already agreed with.",
    ),
    "recipe": (
        "artifacts/assembly-recipe.yaml",
        "artifacts/assembly-recipe.yaml — ten steps, with a witness per step",
        "",
    ),
    "expected": (
        "artifacts/expected.yaml",
        "artifacts/expected.yaml — deriving nothing from a run",
        "It carries the estate census and three deliberately WRONG methods with"
        " the number each would have produced, so every control can be shown to"
        " discriminate rather than merely to differ.",
    ),
    "gates": (
        "artifacts/gates.yaml",
        "artifacts/gates.yaml — the sixteen gates as data, each with its observed red",
        "The ladder's first machine-readable gate declaration. Every record"
        " carries the sabotage applied and the result observed under that"
        " gate's own id.",
    ),
    "deployment": (
        "deployment.py",
        "deployment.py — the interpreter, and the only file that names a table or a predicate",
        "",
    ),
    "produce": (
        "produce.py",
        "produce.py — the spine, which names no table, no column and no domain word",
        "",
    ),
    "projection": (
        "projection.py",
        "projection.py — the perspective, conditioned on a FIBO class axis",
        "",
    ),
    "assembler": (
        "assembler.py",
        "assembler.py — the standalone seam both callers reach",
        "It knows nothing about MCP. That is what makes one assembler serving"
        " two callers a property rather than a coincidence.",
    ),
    "transport": (
        "transport.py",
        "transport.py — the in-process transport adapter behind ProductClient",
        "",
    ),
    "run_py": ("run.py", "run.py — the command-line driver, the first caller", ""),
    "door_yaml": (
        "server/egress-door.yaml",
        "server/egress-door.yaml — the door's governance values as data",
        "",
    ),
    "compose": (
        "server/compose.py",
        "server/compose.py — the ONE resolver, built over assembler.py",
        "",
    ),
    "serve": (
        "server/serve.py",
        "server/serve.py — the MCP door, the second caller and the ladder's first",
        "The product TOOL serves; the registered product RESOURCE refuses by"
        " name, because this class is parameterized and a resource URL carries"
        " no parameters.",
    ),
    "tests_census": (
        "tests/examples/test_cp_04_census.py",
        "tests/examples/test_cp_04_census.py — the estate census and the wrong methods",
        "",
    ),
    "tests_traversal": (
        "tests/examples/test_cp_04_traversal.py",
        "tests/examples/test_cp_04_traversal.py — the walk, its ceiling and its default",
        "",
    ),
    "tests_cycles": (
        "tests/examples/test_cp_04_cycles.py",
        "tests/examples/test_cp_04_cycles.py — the roster, never the count",
        "A cycle asserted as len(findings) > 0 accepts a three-member roster"
        " with one member swapped in from the other cycle — a circuit that does"
        " not exist in the graph at all.",
    ),
    "tests_payload": (
        "tests/examples/test_cp_04_payload.py",
        "tests/examples/test_cp_04_payload.py — the served shape and the two stores",
        "",
    ),
    "tests_debt": (
        "tests/examples/test_cp_04_debt.py",
        "tests/examples/test_cp_04_debt.py — the debt figure and the two twenties",
        "",
    ),
    "tests_seams": (
        "tests/examples/test_cp_04_seams.py",
        "tests/examples/test_cp_04_seams.py — the seam gates",
        "",
    ),
    "tests_callers": (
        "tests/examples/test_cp_04_two_callers.py",
        "tests/examples/test_cp_04_two_callers.py — one request, two callers, one seal",
        "",
    ),
    "tests_gates": (
        "tests/examples/test_cp_04_gates_declaration.py",
        "tests/examples/test_cp_04_gates_declaration.py — the gate declaration itself",
        "",
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


def _verify_snapshot(transcript: str) -> None:
    """Refuse to publish a snapshot sentence that disagrees with the tree.

    Two independent checks against two different sources, because neither
    source can carry both facts. See the module docstring.
    """
    for key in ("asked_at", "content_address"):
        if SNAPSHOT[key] not in transcript:
            raise SystemExit(
                f"snapshot {key}={SNAPSHOT[key]!r} does not appear in"
                f" {RUN_TRANSCRIPT.relative_to(REPO)} — the page would name a"
                " different run than the one it prints. Re-capture the"
                " transcript, or correct SNAPSHOT, in the same commit."
            )
    census = yaml.safe_load(EXPECTED.read_text(encoding="utf-8"))
    declared = census["declaration"]["census"]["ledger_t_read_at"]
    if str(declared) != SNAPSHOT["ledger_t"]:
        raise SystemExit(
            f"snapshot ledger_t={SNAPSHOT['ledger_t']} disagrees with"
            f" {EXPECTED.relative_to(REPO)}::census.ledger_t_read_at={declared}."
            " The program does not print the transaction counter, so the"
            " reviewed artifact is the only thing that can check it."
        )


#: A placeholder, as written in the template. Anchored to lowercase words so it
#: cannot match the doubled braces that appear inside embedded source — the
#: SPARQL builders in ``deployment.py`` write ``f"... WHERE {{ ?s ... }}"``, and
#: those braces are legitimate content of a file this page reproduces.
PLACEHOLDER = re.compile(r"\{\{([a-z_]+)\}\}")


def _assert_placeholders_agree(template: str) -> None:
    """The template's placeholders and the generator's keys are the same set.

    **Checked on the template, BEFORE anything is substituted**, which is where
    cp-03's guard cannot look: that one tests the RENDERED page for a remaining
    ``{{``, and the rendered page legitimately contains doubled braces from the
    source it embeds. Checking the template instead is also strictly stronger —
    it names an unreplaced placeholder AND an unused generator key, in both
    directions and by name, rather than reporting that something somewhere did
    not substitute.
    """
    in_template = set(PLACEHOLDER.findall(template))
    provided = set(BLOCKS) | set(SNAPSHOT) | {"run", "commit"}
    missing = sorted(in_template - provided)
    unused = sorted(provided - in_template)
    if missing or unused:
        raise SystemExit(
            f"{TEMPLATE.relative_to(REPO)} and this generator disagree —"
            f" placeholders with no value: {missing};"
            f" values with no placeholder: {unused}"
        )


def build() -> str:
    transcript = RUN_TRANSCRIPT.read_text(encoding="utf-8")
    _verify_snapshot(transcript)

    page = TEMPLATE.read_text(encoding="utf-8")
    _assert_placeholders_agree(page)

    page = page.replace("{{run}}", html.escape(transcript))
    page = page.replace("{{commit}}", html.escape(_commit()))
    for key, value in SNAPSHOT.items():
        page = page.replace("{{" + key + "}}", html.escape(value))
    for key, (path, label, note) in BLOCKS.items():
        page = page.replace("{{" + key + "}}", _details(path, label, note))
    return page


if __name__ == "__main__":
    rendered = build()
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(REPO)}  {len(rendered) / 1024:.0f} KB")
