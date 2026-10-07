"""Install-time harness neutrality, asserted from `pyproject.toml`.

CLAUDE.md §7.3 makes harness neutrality an invariant with CI enforcement. The
CINV-02 import lint enforces the *import-time* half. This module enforces the
*install-time* half that 06-CONTEXT.md D-08 adds: "a LangGraph deployment must
not be made to install Google's SDK." That property has nothing to do with
imports — it is decided entirely by which extra each harness distribution
appears in, and it regresses the moment someone moves a harness into
`[project] dependencies` to make an import resolve.

06-RESEARCH.md Pitfall 6 is the specific failure this guards: `google-adk`
pulls `fastapi`, `google-genai`, and the OpenTelemetry exporters, so a leak
into core dependencies is an information-disclosure surface (T-06-06) in
deployments that never asked for ADK.

The assertions are **declarative**, read from `pyproject.toml` rather than from
the live environment, because a test process cannot uninstall packages to prove
a negative about what an install would have pulled. The manifest is what `pip`
acts on, so the manifest is the honest place to pin the claim.

Scoped claim (D-21): *these tests enforce that each harness distribution is
named in exactly one extra and never in core dependencies.* They do not, and
cannot, prove anything about a harness arriving transitively under some other
dependency.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

import pytest

#: The three harness distributions ruled into v0 by D-IMPL-24, each mapped to
#: the one extra that is allowed to name it. Not a routing table in the
#: CINV-01 sense — it is the assertion's expected value, which is the test's
#: whole content.
HARNESS_TO_EXTRA: dict[str, str] = {
    "google-adk": "adk",
    "claude-agent-sdk": "claude-agent",
    "langgraph": "langgraph",
}

#: The extra that D-08 requires to install all three in one command.
AGGREGATE_EXTRA = "harnesses"

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: `name==1.2.3`, `name[signing]>=1`, `ccf-sdk[adk,claude-agent]` — capture the
#: distribution name, which is everything before the first version specifier,
#: extras bracket, or whitespace.
_REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9._-]+)")

#: `name[extras]` with nothing after the bracket — the shape of a self-referential
#: extra (`ccf-sdk[adk,claude-agent,langgraph]`) once its name is this project's;
#: see `_self_reference`.
_BARE_EXTRAS = re.compile(r"^\s*[A-Za-z0-9._-]+\s*\[([^\]]+)\]\s*$")


def _normalize(name: str) -> str:
    """PEP 503 normalization, so `Google_ADK` and `google-adk` compare equal."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _requirement_name(requirement: str) -> str:
    match = _REQUIREMENT_NAME.match(requirement)
    assert match is not None, f"unparseable requirement: {requirement!r}"
    return _normalize(match.group(1))


#: This project's own distribution name, READ from `[project] name` rather than
#: spelled here. SEC-027 renamed the distribution `ccf` -> `ccf-sdk`; the copy this
#: module used to spell (`^\s*ccf\s*\[`) was a second place the rename had to find.
_PROJECT_NAME = _normalize(
    tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["name"]
)


def _self_reference(requirement: str) -> str | None:
    """The extras a self-referential requirement names, or None.

    A self-reference is a bare `name[extras]` whose name is this project's own.
    Captured so it can be expanded rather than mistaken for a real distribution.
    """
    match = _BARE_EXTRAS.match(requirement)
    if match is None or _requirement_name(requirement) != _PROJECT_NAME:
        return None
    return match.group(1)


@pytest.fixture(scope="module")
def pyproject() -> dict[str, Any]:
    data: dict[str, Any] = tomllib.loads(
        (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    return data


@pytest.fixture(scope="module")
def extras(pyproject: dict[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = pyproject["project"]["optional-dependencies"]
    return result


@pytest.fixture(scope="module")
def core_dependencies(pyproject: dict[str, Any]) -> list[str]:
    result: list[str] = pyproject["project"]["dependencies"]
    return result


def _resolve_extra(extras: dict[str, list[str]], name: str) -> set[str]:
    """The full set of distribution names an extra installs, self-references expanded.

    `harnesses = ["ccf-sdk[adk,claude-agent,langgraph]"]` must resolve to the same
    answer as spelling the three requirements out, or the aggregate extra could
    satisfy D-08's one-command requirement while the isolation assertions below
    silently examined nothing.
    """
    resolved: set[str] = set()
    for requirement in extras[name]:
        self_ref = _self_reference(requirement)
        if self_ref is not None:
            for referenced in self_ref.split(","):
                resolved |= _resolve_extra(extras, referenced.strip())
            continue
        resolved.add(_requirement_name(requirement))
    return resolved


def _extras_naming(extras: dict[str, list[str]], distribution: str) -> set[str]:
    """Extras that name `distribution` *directly*, ignoring self-references.

    Direct naming is the property under test: the point is that exactly one
    extra is the declaration site. Aggregates that compose it by reference are
    fine and are checked separately.
    """
    target = _normalize(distribution)
    return {
        extra
        for extra, requirements in extras.items()
        for requirement in requirements
        if _self_reference(requirement) is None
        and _requirement_name(requirement) == target
    }


@pytest.mark.parametrize(("distribution", "extra"), sorted(HARNESS_TO_EXTRA.items()))
def test_each_harness_is_declared_in_exactly_one_extra(
    extras: dict[str, list[str]], distribution: str, extra: str
) -> None:
    assert _extras_naming(extras, distribution) == {extra}


def test_a_langgraph_deployment_is_not_made_to_install_googles_sdk(
    extras: dict[str, list[str]],
) -> None:
    """D-08's stated case, asserted directly rather than left as prose."""
    installed = _resolve_extra(extras, "langgraph")
    assert _normalize("google-adk") not in installed
    assert _normalize("claude-agent-sdk") not in installed


@pytest.mark.parametrize("distribution", sorted(HARNESS_TO_EXTRA))
def test_no_harness_is_a_core_dependency(
    core_dependencies: list[str], distribution: str
) -> None:
    """The regression that would silently void install-time neutrality."""
    names = {_requirement_name(requirement) for requirement in core_dependencies}
    assert _normalize(distribution) not in names


def test_the_harnesses_aggregate_installs_exactly_the_three_harnesses(
    extras: dict[str, list[str]],
) -> None:
    """D-08's one-command requirement — and nothing beyond the three."""
    assert AGGREGATE_EXTRA in extras
    assert _resolve_extra(extras, AGGREGATE_EXTRA) == {
        _normalize(name) for name in HARNESS_TO_EXTRA
    }


def test_the_documented_dev_command_enables_all_three_harness_legs(
    extras: dict[str, list[str]],
) -> None:
    """CI installs `[dev]`; D-09 runs all three conformance legs there."""
    installed = _resolve_extra(extras, "dev")
    for distribution in HARNESS_TO_EXTRA:
        assert _normalize(distribution) in installed
