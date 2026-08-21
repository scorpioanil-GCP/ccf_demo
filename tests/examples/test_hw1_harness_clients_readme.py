"""The one README carries its required elements, and the `--live` targets exist
outside the always-on list.

Two properties live here, and a third arrives with the phase close.

**The README.** `examples/hw1-harness-clients/README.md` is this example's
adoption contract (CLAUDE.md §9) and criterion 9's whole subject: it must name
each harness, what the reader installs, what to change first to point the
example at their own deployment, and that how the MCP server is assembled is
deliberately out of scope. It must also do two things this phase specifically
owes a reader — state the who-holds-the-MCP-session asymmetry plainly (`H-07`)
rather than smoothing it over, and write out the `request` argument's encode in
full, because the door advertises that argument as a bare string and no amount
of tool discovery will teach its shape. A README that loses one of those
elements to a well-meaning edit is a README that quietly stops discharging the
criterion, and prose is exactly the material where that happens without anybody
noticing.

**The `--live` wiring.** Three opt-in targets exist, are phony, and are *not*
prerequisites of `examples:`. Both halves are failures and they are opposite
ones: a live target on the always-on list is a red check nobody can make green,
because CI holds no populated deployment and no credentials; a live target that
exists nowhere is criterion 6's *documented but never run* failure mode seen
from the other side.

**Every property is a module-level function taking its subject as a
parameter.** That is the design of the module rather than a style choice, and
the defect class it avoids is the one this project has recorded across three
phases: a control specified as *"copy the subject, break it, assert the check
fails"* against an assertion that reads a **fixed path**. The copy is never
what the assertion looks at, so the control passes for the wrong reason and the
property stays unproven. So :func:`readme_element_violations` takes README TEXT
and :func:`live_target_violations` takes Makefile TEXT plus a prerequisite
tuple; the shipped assertions hand them the real files, and `CONTROL 1`
through `CONTROL 5` hand the very same functions doctored ones and watch them
fail.

The Makefile parser is **not** re-implemented here.
`tests/examples/test_hw1_harness_clients_wiring.py::examples_prerequisites` is
imported and reused, because a second implementation of "what is on the
`examples:` line" is a second thing to keep in step. That module owns the claim
that the *deterministic* target is on that line; this one owns the claim that
the three live targets are not. The two claims are complementary and neither
restates the other.
"""

from __future__ import annotations

import pathlib
import re
from collections.abc import Mapping, Sequence

from tests.examples.test_hw1_harness_clients_wiring import examples_prerequisites

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The README this module is about.
README_PATH = REPO_ROOT / "examples" / "hw1-harness-clients" / "README.md"

#: Every element criterion 9, `H-07` and the phase's own teaching burden
#: require the README to carry, mapped to a marker that must appear in it.
#:
#: A marker is a heading name, a distinctive phrase, or a literal token. It is
#: deliberately NOT a full sentence in most cases: this is a structural check
#: over required *content*, not a byte comparison against prose nobody may
#: improve. What it refuses is the element going missing, not the element being
#: reworded — with one exception, `--live`'s `ANTHROPIC_BASE_URL` requirement,
#: whose marker is the variable name itself because the name is the thing an
#: operator greps for after being refused.
REQUIRED_ELEMENTS: Mapping[str, str] = {
    "the frame — same product, same door, three harnesses": (
        "Same product, same door, three harnesses"
    ),
    "what to install for leg 1 (Google ADK)": "`google-adk`",
    "what to install for leg 2 (Claude Agent SDK)": "`claude-agent-sdk`",
    "what to install for leg 3 (LangGraph)": "`langchain-core`",
    "the opaque schema tool discovery advertises": '{"type": "string"}',
    "the literal encode of the `request` argument": "json.dumps(",
    "the canonical rendering the encode uses": 'separators=(",", ":")',
    "the who-holds-the-MCP-session asymmetry (`H-07`)": (
        "agent binary you configure"
    ),
    "the per-leg determinism split": "no network call at all",
    "`--live` has one meaning across every leg": (
        "one thing across all three legs"
    ),
    "leg 2's `--live` requirement": "ANTHROPIC_BASE_URL",
    "where the agent's prompt comes from": "CCF_HARNESS_PROMPT",
    "what to change first": "## What to change first",
    "server assembly is deliberately out of scope": (
        "How the MCP server is assembled and served is deliberately out of"
        " scope"
    ),
    "where the runner is, and why it is not at the root": (
        "reader_visible_modules"
    ),
}

#: The three opt-in targets. Named once so the shipped assertion and the
#: controls cannot drift into checking different strings.
LIVE_TARGETS: tuple[str, ...] = (
    "example-hw1-harness-clients-live-adk",
    "example-hw1-harness-clients-live-anthropic",
    "example-hw1-harness-clients-live-langgraph",
)

#: Collapses every run of whitespace to one space. Applied to both the README
#: and every marker before comparison, so a marker cannot fail merely because
#: the prose it names got re-wrapped at a different column. A checker that
#: broke on a line wrap would be testing the wrapping.
_WHITESPACE = re.compile(r"\s+")


def _flat(text: str) -> str:
    """``text`` with whitespace normalized, for wrap-insensitive matching."""
    return _WHITESPACE.sub(" ", text).strip()


def readme_element_violations(
    text: str, required: Mapping[str, str]
) -> list[str]:
    """Every required element ``text`` does not carry.

    Args:
        text: The README's contents. A parameter, not a read, so a control can
            hand this function a doctored README and watch it fail.
        required: Element name → the marker that must appear. A parameter for
            the same reason, and because an empty mapping is a vacuity this
            function refuses rather than reports clean over.

    Two vacuity refusals come first and they are the load-bearing ones. An
    empty ``required`` makes this function return ``[]`` for every possible
    input — a check that cannot fail. An empty ``text`` makes every marker
    "missing" for a reason that has nothing to do with the README's content: a
    path that stopped resolving, a read that returned nothing. Reporting
    fifteen missing elements over an unread file names the wrong defect.
    """
    violations: list[str] = []
    if not required:
        violations.append(
            "the required-element mapping is empty, so this check passes over"
            " any text at all — including a README that carries nothing"
        )
        return violations
    if not text.strip():
        violations.append(
            "the README text is empty, so nothing was read. Every element"
            " below would report missing for a reason that is not about the"
            " README's content"
        )
        return violations

    flat = _flat(text)
    for element, marker in sorted(required.items()):
        if not marker.strip():
            violations.append(
                f"the marker for {element!r} is empty, so that element is"
                " asserted by nothing"
            )
            continue
        if _flat(marker) not in flat:
            violations.append(
                f"{README_PATH.name} does not carry {element} — no"
                f" {marker!r} appears in it. Criterion 9 and this phase's"
                " teaching burden require that element by name; if the prose"
                " moved, move the marker with it rather than deleting the row"
            )
    return violations


def phony_declarations(makefile_text: str) -> frozenset[str]:
    """Every target named on a ``.PHONY`` line of ``makefile_text``.

    **Continuation lines are followed**, and that is not a nicety: this
    Makefile's main ``.PHONY`` block is one logical line spelled across ten
    physical ones, and a parser reading only the line that starts with
    ``.PHONY:`` sees the first nine names and misses everything after the first
    backslash. It would then report every target below as non-phony — a
    confident, specific, wrong finding. Measured while writing this module: the
    first version did exactly that against the real Makefile.
    """
    names: set[str] = set()
    continuing = False
    for line in makefile_text.splitlines():
        stripped = line.strip()
        if continuing:
            body = stripped
        elif stripped.startswith(".PHONY:"):
            body = stripped[len(".PHONY:") :]
        else:
            continue
        continuing = body.endswith("\\")
        names.update(body.rstrip("\\").split())
    return frozenset(names)


def live_target_violations(
    makefile_text: str,
    targets: Sequence[str],
    prerequisites: Sequence[str],
) -> list[str]:
    """Every way the opt-in targets fail to be opt-in targets that exist.

    Args:
        makefile_text: The Makefile's contents.
        targets: The live target names expected to be declared in it.
        prerequisites: The tokens on the ``examples:`` line, from
            `tests/examples/test_hw1_harness_clients_wiring.py::examples_prerequisites`.
            Passed in rather than parsed here so the two modules cannot drift
            into two notions of what a prerequisite is.

    Three violations. Vacuity first, for the same reason as above: an empty
    ``targets`` makes both loops below iterate over nothing and return clean.
    Then absence — a target the README documents and the Makefile does not
    carry. Then presence on the always-on list, which is the opposite defect
    and the more expensive one.
    """
    violations: list[str] = []
    if not targets:
        violations.append(
            "no live targets were named, so this check asserts nothing about"
            " any target's existence or its absence from `examples:`"
        )
        return violations
    if not makefile_text.strip():
        violations.append(
            "the Makefile text is empty, so no target could be found in it for"
            " a reason that is not about the Makefile's content"
        )
        return violations

    phony = phony_declarations(makefile_text)
    declared = {
        line.split(":", 1)[0]
        for line in makefile_text.splitlines()
        if ":" in line and not line.startswith(("\t", "#", " "))
    }
    for target in targets:
        if target not in declared:
            violations.append(
                f"`{target}` is not declared in the Makefile. A `--live` path"
                " documented in the README and runnable from no target is"
                " criterion 6's *documented but never run* failure mode seen"
                " from the other side"
            )
        elif target not in phony:
            violations.append(
                f"`{target}` is declared but is not `.PHONY`. It produces no"
                " file of its own name, so a same-named directory would make"
                " `make` report it up to date and run nothing"
            )
        if target in prerequisites:
            violations.append(
                f"`{target}` is a prerequisite of `examples:`, so CI runs it."
                " A live leg needs a populated deployment and — for leg 2 — a"
                " real endpoint, neither of which the always-on pipeline has."
                " A red check nobody can make green is worse than no check"
            )
    return violations


# ---------------------------------------------------------------------------
# The shipped assertions.
# ---------------------------------------------------------------------------


def test_the_readme_carries_every_required_element() -> None:
    """Criterion 9, `H-07` and the encode obligation, asserted by name."""
    violations = readme_element_violations(
        README_PATH.read_text(encoding="utf-8"), REQUIRED_ELEMENTS
    )
    assert violations == [], "\n".join(violations)


def test_the_required_element_set_is_not_degenerate() -> None:
    """A floor on the element set, so it cannot be emptied into a green run.

    Ten is the number plan `20-08` states as the minimum; the shipped mapping
    carries more. Without this, deleting fourteen rows and keeping one would
    leave every assertion above green.
    """
    assert len(REQUIRED_ELEMENTS) >= 10, (
        f"only {len(REQUIRED_ELEMENTS)} elements are required of the README;"
        " criterion 9 plus this phase's own obligations are at least ten"
    )
    assert all(marker.strip() for marker in REQUIRED_ELEMENTS.values())


def test_the_three_live_targets_exist_and_are_outside_the_always_on_list() -> None:
    """The shipped wiring assertion, over the real Makefile."""
    makefile_text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    violations = live_target_violations(
        makefile_text, LIVE_TARGETS, examples_prerequisites(makefile_text)
    )
    assert violations == [], "\n".join(violations)


# ---------------------------------------------------------------------------
# Controls. Each hands a doctored subject to the SAME function the shipped
# assertion calls, so none of them can pass by reading something else.
# ---------------------------------------------------------------------------


def test_control_1_a_readme_missing_one_element_names_that_element() -> None:
    """CONTROL 1 — the asymmetry deleted from the real README goes red.

    The subject is the real README with one marker removed, so this control
    proves the check is sensitive to the element it claims to guard rather
    than to some other difference between a synthetic text and the real one.
    """
    element = "the who-holds-the-MCP-session asymmetry (`H-07`)"
    marker = REQUIRED_ELEMENTS[element]
    doctored = README_PATH.read_text(encoding="utf-8").replace(marker, "")
    violations = readme_element_violations(doctored, REQUIRED_ELEMENTS)
    assert violations, "removing the asymmetry marker did not go red"
    assert any(element in violation for violation in violations), (
        f"the violation does not name the element it is about: {violations}"
    )


def test_control_2_an_empty_required_mapping_is_a_vacuity_violation() -> None:
    """CONTROL 2 — a check over no elements refuses instead of passing."""
    violations = readme_element_violations("anything at all", {})
    assert violations
    assert "mapping is empty" in violations[0]


def test_control_3_an_empty_readme_is_a_violation_naming_the_read() -> None:
    """CONTROL 3 — an unread README is not fifteen missing elements."""
    violations = readme_element_violations("   \n\n  ", REQUIRED_ELEMENTS)
    assert len(violations) == 1
    assert "is empty, so nothing was read" in violations[0]


def test_control_4_a_makefile_missing_one_live_target_is_a_violation() -> None:
    """CONTROL 4 — a synthetic Makefile carrying two of the three goes red."""
    doctored = (
        ".PHONY: example-hw1-harness-clients-live-adk"
        " example-hw1-harness-clients-live-anthropic\n"
        "examples: example-00 example-hw1-harness-clients ## Run them\n"
        "example-hw1-harness-clients-live-adk: ## live\n"
        "\t$(ENV) $(PYTHON) drive.py --live --legs adk\n"
        "example-hw1-harness-clients-live-anthropic: ## live\n"
        "\t$(ENV) $(PYTHON) drive.py --live --legs anthropic\n"
    )
    violations = live_target_violations(
        doctored, LIVE_TARGETS, examples_prerequisites(doctored)
    )
    assert violations
    assert any("live-langgraph` is not declared" in v for v in violations), (
        f"the violation does not name the missing target: {violations}"
    )


def test_control_5_a_live_target_on_the_examples_line_is_a_violation() -> None:
    """CONTROL 5 — the always-on list carrying a live target goes red.

    This is the defect that costs the most: it does not break a documented
    path, it breaks every push.
    """
    doctored = (
        ".PHONY: example-hw1-harness-clients-live-adk"
        " example-hw1-harness-clients-live-anthropic"
        " example-hw1-harness-clients-live-langgraph\n"
        "examples: example-00 example-hw1-harness-clients-live-adk ## Run\n"
        "example-hw1-harness-clients-live-adk: ## live\n"
        "\techo adk\n"
        "example-hw1-harness-clients-live-anthropic: ## live\n"
        "\techo anthropic\n"
        "example-hw1-harness-clients-live-langgraph: ## live\n"
        "\techo langgraph\n"
    )
    violations = live_target_violations(
        doctored, LIVE_TARGETS, examples_prerequisites(doctored)
    )
    assert violations
    assert any("is a prerequisite of `examples:`" in v for v in violations), (
        f"the violation does not name the wiring defect: {violations}"
    )


def test_control_5b_an_empty_target_tuple_is_a_vacuity_violation() -> None:
    """A check over no targets refuses rather than reporting clean.

    Not numbered among the plan's five because it guards the same vacuity
    `CONTROL 2` guards on the README side, but it is the reason
    :func:`live_target_violations` returns early instead of falling through
    two loops over nothing.
    """
    makefile_text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    violations = live_target_violations(
        makefile_text, (), examples_prerequisites(makefile_text)
    )
    assert violations
    assert "no live targets were named" in violations[0]


def test_a_declared_but_non_phony_live_target_is_a_violation() -> None:
    """The `.PHONY` half of the wiring claim, watched failing.

    Not numbered as one of the plan's five: it guards a property the plan
    states as an acceptance grep rather than as a control. It is here because
    a grep counts occurrences and this says which occurrence is missing.
    """
    doctored = (
        "examples: example-00 ## Run\n"
        "example-hw1-harness-clients-live-adk: ## live\n"
        "\techo adk\n"
        "example-hw1-harness-clients-live-anthropic: ## live\n"
        "\techo anthropic\n"
        "example-hw1-harness-clients-live-langgraph: ## live\n"
        "\techo langgraph\n"
    )
    violations = live_target_violations(
        doctored, LIVE_TARGETS, examples_prerequisites(doctored)
    )
    assert len(violations) == len(LIVE_TARGETS)
    assert all("is not `.PHONY`" in violation for violation in violations)
