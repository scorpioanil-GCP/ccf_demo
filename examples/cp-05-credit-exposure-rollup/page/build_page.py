"""Assemble this example's documentation page from `template.html`.

**Run from the repository root:**

    .venv/bin/python examples/cp-05-credit-exposure-rollup/page/build_page.py

Writes `page/cp-05.html`, which is then published as an artifact. **The rendered
page is NOT committed** — the generator and the template are, because they are
the reproducible things and the embedded source is not. `.gitignore` enforces
the split: `examples/*/page/*.html` is excluded and `template.html` re-included.
This is rung 4's convention unchanged; see that generator's docstring for why a
generator and not a page, and why every source file sits behind a placeholder.

**TWO COMMITTED TRANSCRIPTS, AND THE PAGE IS GENERATED FROM THEM RATHER THAN
FROM A RUN.** `run-transcript.txt` is the default consumer — a governed
WITHHELD — and `scenario-transcript.txt` is the eight named consumers, of which
exactly one is served. Neither is re-taken at build time. A page that re-ran the
product on every build would print whatever the estate said today, and at a
FOUR-HOUR half-life (`artifacts/ttl.yaml`) today's answer is guaranteed to
differ from the pinned one: this rung's freshest input decays faster than the
gap between two sittings. Regenerate the transcripts deliberately, against the
`asked_at` pin, and rebuild afterwards.

**THE DISCLOSURE RULE, ENFORCED HERE RATHER THAN OBSERVED BY HAND.**

This rung's whole subject is a refusal of fulfillment. The default consumer is
WITHHELD and its disclosed shell reports `observed "undisclosed"` — the
deployment's disclosure policy is `minimal`, so a refused caller learns the
kind, the tolerance, the authority and the replay reference, and NOT the
determination. The determination is nonetheless known to this repository,
because a DIFFERENT consumer with a wider fitness bar is served it in
`scenario-transcript.txt`.

A page that filled the withheld panel in from the served one would be
undoing, in documentation, precisely the boundary the product exists to draw.
:func:`_refuse_cross_disclosure` therefore checks that the withheld transcript
does not contain the served figures, and the template feeds the withheld panel
from `{{run}}` alone. The rule is that **the page discloses to the withheld
consumer exactly what the fabric disclosed to it** — no more.

**THE SNAPSHOT IS DECLARED HERE AND VERIFIED AGAINST THE TREE AT BUILD TIME**
(`D-IMPL-218`). Every value in :data:`SNAPSHOT` is checked against a source that
did not come from this module, and the sources are deliberately split so no one
file can certify itself:

* `anchor`, `asked_at` and `ttl_seconds` against the **declared artifacts** —
  `artifacts/question.yaml` and `artifacts/ttl.yaml`. These are what was ASKED,
  and the artifacts are where the ask lives.
* `tolerance` against `ccf_config.yaml::product_class.serve_obligations` AND
  against the withheld transcript. Two sources because the tolerance is the one
  value that appears on both sides of the refusal: it is Control Plane state and
  it is disclosed to the refused caller.
* `replay_ref` against the **withheld** transcript.
* `family`, `gross`, `adjusted` and `served_address` against the **served**
  transcript, and the three figures additionally against
  `artifacts/expected.yaml`, which derives nothing from any run. The transcript
  prints them grouped (`10,125,000,000`); the artifact holds them as integers.
  Checking both forms is what makes the check a check rather than a spelling
  test of this module's own string.

A build whose snapshot disagrees with any of them **refuses** rather than
publishing a page that misattributes its own run.
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

#: The default consumer — assembled, gated, recorded, and WITHHELD. Its disclosed
#: shell is all this page may show for a refused caller.
RUN_TRANSCRIPT = HERE / "run-transcript.txt"

#: The eight named consumers of `artifacts/scenarios.yaml`, one of them served.
SCENARIO_TRANSCRIPT = HERE / "scenario-transcript.txt"

OUTPUT = HERE / "cp-05.html"

QUESTION = EXAMPLE / "artifacts" / "question.yaml"
TTL = EXAMPLE / "artifacts" / "ttl.yaml"
EXPECTED = EXAMPLE / "artifacts" / "expected.yaml"
CONFIG = EXAMPLE / "ccf_config.yaml"

#: The snapshot this page names — `D-IMPL-218`. The commit is asked of git
#: below; every other value is verified against the tree by the functions after
#: it, and a disagreement refuses the build.
SNAPSHOT: dict[str, str] = {
    "anchor": "5493000Q1S5TJIDIQH89",
    "asked_at": "2026-09-07T12:00:00+00:00",
    "ttl_seconds": "14400",
    "tolerance": "0.25",
    "family": "77",
    "gross": "10,125,000,000",
    "adjusted": "9,325,000,000",
    "served_address": (
        "e50c27c13814e8ca03b2e487516e2fa34e76853e31262cf96c4552a57dca4fa5"
    ),
    "replay_ref": (
        "ccf-artifact://cp-05-demo/ccf.cp-05.decision-replay-record/"
        "86753577c4c815ab51c03d39b842fc0177a8329f2d425c1e8751fdf63336bdac"
        "@99ac4aa110831cb7b8f711e0c977643967fef04a7eff1caacce98a62a88656a7"
    ),
}

#: Placeholder -> (path, summary label, note). Paths are relative to the
#: example, except `tests/...` which is repo-relative.
BLOCKS: dict[str, tuple[str, str, str]] = {
    "spec": (
        "spec/CP-SPEC-005_Credit_Exposure_Rollup.md",
        "The specification — written first, approved before any code",
        "Everything below derives from it, including the refusal semantics,"
        " the reconciliation guard, and the gaps raised against the SDK and"
        " left visible.",
    ),
    "config": (
        "ccf_config.yaml",
        "ccf_config.yaml — the whole Control Plane, including the default fitness bar",
        "`serve_obligations.default_debt_tolerance` is 0.25 and it lives here"
        " rather than in the request contract, because the value is consumed"
        " INSIDE the governed determination. A default the SDK cannot read is a"
        " default that does not govern.",
    ),
    "backends": (
        "backends.yaml",
        "backends.yaml — two store bindings, and no credential in any of it",
        "",
    ),
    "question": (
        "artifacts/question.yaml",
        "artifacts/question.yaml — the caller's vocabulary, the anchor and the pinned instant",
        "A question is not a permission, so it is read-side and never enters"
        " Control Plane state. Changing the subject here re-asks the same"
        " question of another family.",
    ),
    "scenarios_yaml": (
        "artifacts/scenarios.yaml",
        "artifacts/scenarios.yaml — the eight consumers, as data rather than as a list in the client",
        "2%, 10%, 0.05 and 1.0 are domain values. A scenario table written into"
        " run.py would be the No-Hardcoding Rule firing exactly as it fires on a"
        " threshold in produce.py — the client renders scenarios, it does not"
        " hold them.",
    ),
    "ttl": (
        "artifacts/ttl.yaml",
        "artifacts/ttl.yaml — four hours, and the anchor that flips at this rung",
        "`from_decision`, against rungs 02 and 04's `from_entity_freshness`. An"
        " exposure is not a fact about an entity whose validity period governs"
        " it; it is a fact about a question asked at an instant.",
    ),
    "replay_yaml": (
        "artifacts/replay.yaml",
        "artifacts/replay.yaml — one record class for served and withheld alike",
        "A second class for withheld determinations would be exactly the"
        " second-class replay `D-IMPL-253` Q13 forbids. The document exists at"
        " all because the Control Plane's section vocabulary is closed and"
        " refuses a `replay:` section by name — recorded as a finding.",
    ),
    "recipe": (
        "artifacts/assembly-recipe.yaml",
        "artifacts/assembly-recipe.yaml — the steps, with a witness per step",
        "",
    ),
    "expected": (
        "artifacts/expected.yaml",
        "artifacts/expected.yaml — measured against the estate before the product existed",
        "It carries the naive borrower-keyed answer beside the family total, so"
        " the 69.8x understatement is arithmetic rather than assertion. Its"
        " guarantee-dedup figure was CORRECTED when the product disagreed with"
        " it on the first run and the product was right.",
    ),
    "deployment": (
        "deployment.py",
        "deployment.py — the interpreter, and the only file that names a table or a predicate",
        "",
    ),
    "produce": (
        "produce.py",
        "produce.py — the spine, which composes no governance of its own",
        "After the canonical adoption `produce_governed` is an ADAPTER INTO THE"
        " SDK rather than a smaller second implementation of it: it loads"
        " declarations, acquires content, shapes the business payload, and hands"
        " the rest to `build_governed_resolver`. Zero lines of governance"
        " composition remain.",
    ),
    "projection": (
        "projection.py",
        "projection.py — the perspective, which selects and shapes truth and never creates it",
        "L5 may select, shape and present truth. It must not reach back to a"
        " system of record to create it, which is why gross and adjusted"
        " aggregation stayed in the assembler.",
    ),
    "assembler": (
        "assembler.py",
        "assembler.py — the traversal, the dedup, and the reconciliation guard",
        "Step 5.2 carries the rule the first draft of expected.yaml got wrong: a"
        " guarantee dedup is valid only when BOTH the guarantor and the obligor"
        " are inside the measured family.",
    ),
    "run_py": (
        "run.py",
        "run.py — the command-line driver, and a renderer with two sources",
        "It renders the business answer and the governed context as two blocks,"
        " and has a SEPARATE renderer for a withheld determination — because a"
        " refused caller is handed a different object, not the same object with"
        " fields blanked.",
    ),
    "door_yaml": (
        "server/door.yaml",
        "server/door.yaml — the door's governance values as data",
        "",
    ),
    "serve": (
        "server/serve.py",
        "server/serve.py — the MCP door, measured at zero lines of governance",
        "It re-implements no part of assembly, gating, debt assessment, the"
        " tolerance comparison or the replay record. It got THINNER at the"
        " migration: `D-IMPL-303` removed the conformity check it had been"
        " running of its own, because a door owns transport, address and"
        " standing, and the resolver owns the contract.",
    ),
    "tests_output": (
        "tests/examples/test_cp_05_output.py",
        "tests/examples/test_cp_05_output.py — the served shape, the withheld shell, and the invariant between them",
        "",
    ),
    "tests_door": (
        "tests/examples/test_cp_05_mcp_door.py",
        "tests/examples/test_cp_05_mcp_door.py — the door's entitlement, refusal and delegation",
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


def _declaration(path: pathlib.Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["declaration"]


def _refuse(message: str) -> None:
    raise SystemExit(f"cp-05 page build refused — {message}")


def _verify_against_artifacts() -> None:
    """The ask, checked against the documents that carry the ask."""
    question = _declaration(QUESTION)
    if question["subject"] != SNAPSHOT["anchor"]:
        _refuse(
            f"anchor {SNAPSHOT['anchor']!r} is not"
            f" {QUESTION.relative_to(REPO)}::subject ({question['subject']!r})."
        )
    if question["asked_at"] != SNAPSHOT["asked_at"]:
        _refuse(
            f"asked_at {SNAPSHOT['asked_at']!r} is not"
            f" {QUESTION.relative_to(REPO)}::asked_at ({question['asked_at']!r})."
        )
    declared_ttl = str(_declaration(TTL)["declared_ttl_seconds"])
    if declared_ttl != SNAPSHOT["ttl_seconds"]:
        _refuse(
            f"ttl_seconds {SNAPSHOT['ttl_seconds']} is not"
            f" {TTL.relative_to(REPO)}::declared_ttl_seconds ({declared_ttl})."
        )
    obligations = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["product_class"][
        "serve_obligations"
    ]
    declared_tolerance = str(obligations["default_debt_tolerance"])
    if declared_tolerance != SNAPSHOT["tolerance"]:
        _refuse(
            f"tolerance {SNAPSHOT['tolerance']!r} is not"
            f" {CONFIG.relative_to(REPO)}::product_class.serve_obligations"
            f".default_debt_tolerance ({declared_tolerance!r})."
        )


def _verify_against_expected(figures: dict[str, int]) -> None:
    """The three headline figures, against a document that derives nothing.

    `artifacts/expected.yaml` was measured directly against the estate before a
    line of this product's code existed. It is the only source here that cannot
    have been produced by the program the page is about.
    """
    expected = _declaration(EXPECTED)
    measured = {
        "family": expected["traversal"]["family_nodes"],
        "gross": expected["measures"]["gross"]["committed"],
        "adjusted": expected["measures"]["adjusted"]["committed"],
    }
    for key, value in measured.items():
        if figures[key] != value:
            _refuse(
                f"{key}={SNAPSHOT[key]} disagrees with"
                f" {EXPECTED.relative_to(REPO)} ({value:,}). The page would"
                " print a figure the independently measured expectation does"
                " not carry."
            )


def _verify_against_transcripts(withheld: str, scenarios: str) -> None:
    """Each value against the transcript that actually printed it."""
    for key in ("tolerance", "replay_ref"):
        if SNAPSHOT[key] not in withheld:
            _refuse(
                f"{key}={SNAPSHOT[key]!r} does not appear in"
                f" {RUN_TRANSCRIPT.relative_to(REPO)} — the page would name a"
                " different refusal than the one it prints."
            )
    for key in ("family", "gross", "adjusted", "served_address"):
        if SNAPSHOT[key] not in scenarios:
            _refuse(
                f"{key}={SNAPSHOT[key]!r} does not appear in"
                f" {SCENARIO_TRANSCRIPT.relative_to(REPO)} — the page would"
                " attribute a figure to a served run that did not serve it."
            )


#: How each figure is PROBED FOR inside the refused transcript — anchored to the
#: form the served transcript actually prints it in, never as a bare number.
#:
#: The anchoring is not fussiness; the first version of this guard searched for
#: the bare string ``77`` and fired on every build, because the transcript's
#: replay reference is 128 hex characters and contains ``77`` twice. A guard
#: that cannot be satisfied is a guard that gets deleted, and the figure it was
#: watching then travels unwatched. `family 77` occurs in a refused transcript
#: only if a refused caller was told the family size.
DISCLOSURE_PROBES: dict[str, str] = {
    "family": r"family\s+{}",
    "gross": r"(?<![\d,]){}(?![\d,])",
    "adjusted": r"(?<![\d,]){}(?![\d,])",
}


def _refuse_cross_disclosure(withheld: str) -> None:
    """The withheld consumer's transcript must not carry the determination.

    **This is the page's disclosure rule as a build-time check.** The withheld
    panel is fed from `run-transcript.txt` alone, so this guard is what makes
    that structural choice verifiable rather than merely intended: if the
    withheld transcript is ever re-taken under a disclosure policy that reveals
    the figures, the page's own claim — *this is what a refused caller sees* —
    would silently become false while everything still rendered.

    A build that finds the determination inside the refusal refuses, and the
    remedy is to re-read the disclosure policy rather than to edit this page.
    """
    leaked = [
        key
        for key, probe in DISCLOSURE_PROBES.items()
        if re.search(probe.format(re.escape(SNAPSHOT[key])), withheld)
    ]
    if leaked:
        _refuse(
            f"{RUN_TRANSCRIPT.relative_to(REPO)} discloses {leaked} — this page"
            " presents that transcript as what a WITHHELD caller is told, and"
            " the deployment's disclosure policy is `minimal`. Either the"
            " policy changed, or the transcript was captured from a served"
            " consumer. Do not resolve this by editing the page."
        )
    if "undisclosed" not in withheld:
        _refuse(
            f"{RUN_TRANSCRIPT.relative_to(REPO)} no longer reports the observed"
            " debt as undisclosed. The page's withheld panel claims a minimal"
            " disclosure that the transcript would no longer support."
        )


#: The served consumer's own block, as the program printed it. The first line
#: anchors on `assembled` because a withheld consumer's block carries the
#: parenthetical placeholder there instead of figures, so this pattern cannot
#: match one; the last is the content address, which only a served consumer has.
SERVED_BLOCK = re.compile(
    r"^ +assembled +family .*?^ +address +[0-9a-f]{64}$",
    re.MULTILINE | re.DOTALL,
)


def _served_excerpt(scenarios: str) -> str:
    """The served consumer's disclosure, LIFTED from the transcript.

    The page prints this beside the refused consumer's disclosure, and the two
    have to be comparable as evidence. Retyping the served figures into the
    template would make the right-hand panel an assertion sitting next to a
    verbatim left-hand one, and the whole device depends on both being the same
    kind of object.
    """
    match = SERVED_BLOCK.search(scenarios)
    if match is None:
        _refuse(
            f"no served consumer block found in"
            f" {SCENARIO_TRANSCRIPT.relative_to(REPO)} — the page's served panel"
            " has nothing to quote. Every consumer in the transcript was"
            " refused or withheld, which is itself the thing to investigate."
        )
    return match.group(0)


#: A placeholder, as written in the template. Anchored to lowercase words so it
#: cannot match doubled braces appearing inside embedded source.
PLACEHOLDER = re.compile(r"\{\{([a-z_]+)\}\}")


def _assert_placeholders_agree(template: str) -> None:
    """The template's placeholders and the generator's keys are the same set.

    Checked on the TEMPLATE, before anything is substituted — which names an
    unreplaced placeholder and an unused generator key, in both directions and
    by name, rather than reporting that something somewhere did not substitute.
    """
    in_template = set(PLACEHOLDER.findall(template))
    provided = set(BLOCKS) | set(SNAPSHOT) | {"run", "scenarios", "served", "commit"}
    missing = sorted(in_template - provided)
    unused = sorted(provided - in_template)
    if missing or unused:
        _refuse(
            f"{TEMPLATE.relative_to(REPO)} and this generator disagree —"
            f" placeholders with no value: {missing};"
            f" values with no placeholder: {unused}"
        )


def build() -> str:
    withheld = RUN_TRANSCRIPT.read_text(encoding="utf-8")
    scenarios = SCENARIO_TRANSCRIPT.read_text(encoding="utf-8")

    _verify_against_artifacts()
    _verify_against_expected(
        {
            key: int(SNAPSHOT[key].replace(",", ""))
            for key in ("family", "gross", "adjusted")
        }
    )
    _verify_against_transcripts(withheld, scenarios)
    _refuse_cross_disclosure(withheld)

    page = TEMPLATE.read_text(encoding="utf-8")
    _assert_placeholders_agree(page)

    page = page.replace("{{run}}", html.escape(withheld))
    page = page.replace("{{scenarios}}", html.escape(scenarios))
    page = page.replace("{{served}}", html.escape(_served_excerpt(scenarios)))
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
