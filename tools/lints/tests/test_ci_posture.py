"""Tests for `tools/lints/ci_posture.py` — the SEC-015 exploit test.

The row (``docs/superpowers/specs/2026-10-05-remaining-rows-exploit-tests.md``,
SEC-015, ``D-IMPL-369``) names the subjects: the **committed** workflows, red on
both halves for all four files before the fix, and five fixtures — a
conforming workflow, a tag ref, a ``permissions: write-all``, a job-level
``contents: write`` under a restrictive top level (allowed), and a workflow
whose ``on:`` key parsed as ``True``.
"""

from __future__ import annotations

import pathlib
from typing import Any

import pytest
import yaml

from tools.lints import ci_posture as lint
from tools.lints.__main__ import WHOLE_TREE_CHECKERS, build_parser

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

#: The four workflows the row measured. A fifth file joining the tree must
#: join this roster by an edit here, so the lint's population is never
#: silently wider or narrower than the one reviewed.
COMMITTED = ("ci.yml", "live-legs.yml", "perf.yml", "release-stamp.yml")

SHA = "11d5960a326750d5838078e36cf38b85af677262"

CONFORMING = f"""\
name: conforming
on:
  push:
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{SHA}  # v4
      - run: echo ok
"""


def _findings(text: str) -> list[str]:
    return lint.check_source(text, "w.yml")


# --- the committed workflows ---------------------------------------------------


def test_the_lint_reads_exactly_the_committed_workflows() -> None:
    read = [p.name for p in lint.workflow_paths(REPO_ROOT)]
    assert read == sorted(COMMITTED)


@pytest.mark.parametrize("name", COMMITTED)
def test_committed_workflow_has_a_restrictive_top_level_permissions_block(name: str) -> None:
    text = (REPO_ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
    doc = yaml.safe_load(text)
    found = [f for f in lint.check_source(text, name) if "permissions" in f]
    assert found == [], f"{name}: {found}"
    assert doc["permissions"] in ({"contents": "read"}, {})


@pytest.mark.parametrize("name", COMMITTED)
def test_committed_workflow_pins_every_action_to_a_commented_sha(name: str) -> None:
    text = (REPO_ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
    refs = [ref for _, ref in lint._uses_sites(yaml.safe_load(text))]
    assert refs, f"{name} names no action — the pin half would be vacuous"
    found = [f for f in lint.check_source(text, name) if "uses:" in f]
    assert found == [], f"{name}: {found}"


def test_the_committed_tree_has_no_finding_at_all() -> None:
    assert lint.check_tree(REPO_ROOT) == []


def test_dependabot_bumps_the_pinned_actions_weekly() -> None:
    """Q9: the pins move by pull request, not by hand."""
    config = yaml.safe_load((REPO_ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8"))
    ecosystems = {u["package-ecosystem"]: u for u in config["updates"]}
    assert ecosystems["github-actions"]["schedule"]["interval"] == "weekly"


# --- fixtures --------------------------------------------------------------------


def test_a_conforming_workflow_has_no_finding() -> None:
    assert _findings(CONFORMING) == []


def test_the_on_key_parsing_as_true_does_not_trip_the_rule() -> None:
    assert True in yaml.safe_load(CONFORMING)
    assert _findings(CONFORMING) == []


def test_a_tag_ref_is_refused() -> None:
    found = _findings(CONFORMING.replace(f"@{SHA}  # v4", "@v4"))
    assert len(found) == 1 and "mutable ref" in found[0]
    assert found[0].startswith("w.yml:10 ci-posture ")


def test_a_sha_without_its_tag_comment_is_refused() -> None:
    found = _findings(CONFORMING.replace("  # v4", ""))
    assert len(found) == 1 and "`# vN`" in found[0]


def test_a_short_sha_is_refused() -> None:
    found = _findings(CONFORMING.replace(SHA, SHA[:7]))
    assert len(found) == 1 and "mutable ref" in found[0]


def test_a_missing_permissions_block_is_refused() -> None:
    found = _findings(CONFORMING.replace("permissions:\n  contents: read\n", ""))
    assert len(found) == 1 and "no top-level `permissions:`" in found[0]


def test_write_all_at_the_top_level_is_refused() -> None:
    found = _findings(CONFORMING.replace("permissions:\n  contents: read\n", "permissions: write-all\n"))
    assert len(found) == 1 and "not restrictive" in found[0]


@pytest.mark.parametrize("grant", ["contents: write", "packages: write", "contents: read\n  id-token: write"])
def test_any_other_top_level_grant_is_refused(grant: str) -> None:
    found = _findings(CONFORMING.replace("permissions:\n  contents: read\n", f"permissions:\n  {grant}\n"))
    assert len(found) == 1 and "may grant `contents: read` only" in found[0]


def test_a_job_level_write_under_a_restrictive_top_level_is_allowed() -> None:
    text = CONFORMING.replace(
        "    runs-on: ubuntu-latest\n",
        "    runs-on: ubuntu-latest\n    permissions:\n      contents: write\n",
    )
    assert _findings(text) == []


def test_an_empty_top_level_block_is_restrictive() -> None:
    assert _findings(CONFORMING.replace("permissions:\n  contents: read\n", "permissions: {}\n")) == []


def _with_job_permissions(block: str) -> str:
    return CONFORMING.replace(
        "    runs-on: ubuntu-latest\n", f"    runs-on: ubuntu-latest\n    permissions:{block}\n"
    )


@pytest.mark.parametrize("form", [" read-all", " write-all", ""])
def test_every_non_mapping_job_level_permissions_is_refused(form: str) -> None:
    """Corrective round: `read-all` passed before; every string form, and an
    empty value, is now refused — a job-level override names its scopes."""
    found = _findings(_with_job_permissions(form))
    assert len(found) == 1 and "not an explicit mapping" in found[0]


def test_a_job_level_read_mapping_is_allowed() -> None:
    assert _findings(_with_job_permissions("\n      contents: read")) == []


def test_a_job_level_write_is_named_and_allowed_under_a_restrictive_top() -> None:
    text = _with_job_permissions("\n      contents: write")
    assert _findings(text) == []
    assert lint.job_write_grants(yaml.safe_load(text)) == ["jobs.build: contents: write"]


def test_a_job_level_write_under_a_wide_top_level_is_refused_by_name() -> None:
    text = _with_job_permissions("\n      contents: write").replace(
        "permissions:\n  contents: read\n", "permissions:\n  packages: write\n", 1
    )
    found = _findings(text)
    assert len(found) == 2
    assert any("jobs.build grants `contents: write`" in f for f in found)


def test_an_unknown_job_level_level_is_refused() -> None:
    found = _findings(_with_job_permissions("\n      contents: admin"))
    assert len(found) == 1 and "not read, write or none" in found[0]


def test_a_job_level_write_all_is_refused() -> None:
    text = CONFORMING.replace(
        "    runs-on: ubuntu-latest\n",
        "    runs-on: ubuntu-latest\n    permissions: write-all\n",
    )
    found = _findings(text)
    assert len(found) == 1 and "not an explicit mapping" in found[0]


def test_a_reusable_workflow_call_is_pinned_too() -> None:
    text = (
        "on: push\npermissions:\n  contents: read\njobs:\n"
        "  call:\n    uses: org/repo/.github/workflows/x.yml@main\n"
    )
    found = _findings(text)
    assert len(found) == 1 and "mutable ref" in found[0]


def test_a_local_action_is_exempt_and_docker_needs_a_digest() -> None:
    assert _findings(CONFORMING.replace(f"actions/checkout@{SHA}  # v4", "./.github/actions/x")) == []
    found = _findings(CONFORMING.replace(f"actions/checkout@{SHA}  # v4", "docker://alpine:3"))
    assert len(found) == 1 and "sha256" in found[0]


def test_two_uses_of_one_sha_need_two_commented_lines() -> None:
    text = CONFORMING.replace(
        "      - run: echo ok\n", f"      - uses: actions/checkout@{SHA}\n      - run: echo ok\n"
    )
    found = _findings(text)
    assert len(found) == 1 and "`# vN`" in found[0]


def test_the_finding_names_the_step_whose_comment_is_missing() -> None:
    text = CONFORMING.replace(
        "      - run: echo ok\n", f"      - uses: actions/checkout@{SHA}  # v4\n      - run: echo ok\n"
    ).replace("@" + SHA + "  # v4\n      - uses", "@" + SHA + "\n      - uses", 1)
    found = _findings(text)
    assert len(found) == 1 and "w.yml:10 ci-posture jobs.build.steps[0] " in found[0]


def test_a_flow_style_uses_that_cannot_be_paired_is_refused() -> None:
    text = CONFORMING.replace("      - run: echo ok\n", "      - {uses: actions/checkout@v4}\n")
    found = _findings(text)
    assert len(found) == 1 and "do not pair" in found[0]


def test_an_unparseable_workflow_is_a_finding_not_a_skip() -> None:
    assert _findings("jobs: [\n")


def test_a_tree_without_workflows_has_no_finding(tmp_path: pathlib.Path) -> None:
    assert lint.check_tree(tmp_path) == []


# --- registration ---------------------------------------------------------------


def test_the_rule_is_registered_and_has_its_own_flag() -> None:
    assert WHOLE_TREE_CHECKERS["ci-posture"] is lint.check_tree
    assert build_parser().parse_args(["--ci-posture"]).selected == ["ci-posture"]


#: D-IMPL-378 C8 (Dave, 2026-10-07 21:18 MST; confirmed 2026-10-08 04:07 MST),
#: extending D-IMPL-372: every substrate step runs even when an earlier step
#: failed, so a red quick suite cannot leave the legs unmeasured. Coverage stays
#: gated: it only repeats the quick suite (the D-IMPL-378 CI diagnosis, §4.1).
ALWAYS_RUN_STEPS = (
    "Harness adapter conformance (all three legs must run)",
    "Postgres leg (service container)",
    "SEC-013 Postgres lease, focused (service container)",
    "Neo4j leg (service container)",
    "MongoDB leg (service container)",
    "Fluree leg (service container)",
)
GATED_STEPS = ("Coverage (informational)",)
NOT_CANCELLED = "${{ !cancelled() }}"


def _test_job_steps() -> dict[str, dict[str, Any]]:
    doc = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    return {step["name"]: step for step in doc["jobs"]["test"]["steps"] if "name" in step}


@pytest.mark.parametrize("name", ALWAYS_RUN_STEPS)
def test_every_substrate_step_runs_after_an_earlier_failure(name: str) -> None:
    steps = _test_job_steps()
    assert name in steps, f"no step named {name!r}: a renamed leg is renamed here, never dropped"
    assert steps[name].get("if") == NOT_CANCELLED, f"{name!r} is gated on every earlier step passing"


@pytest.mark.parametrize("name", GATED_STEPS)
def test_coverage_stays_gated_on_the_quick_suite(name: str) -> None:
    steps = _test_job_steps()
    assert name in steps, f"no step named {name!r}"
    assert "if" not in steps[name], f"{name!r} must stay gated: it only repeats the quick suite"


def test_no_substrate_step_escapes_the_always_run_list() -> None:
    """A new `make leg-*`, conformance or `-m postgres` step joins ALWAYS_RUN_STEPS by an edit here."""
    steps = _test_job_steps()
    substrate = {
        name
        for name, step in steps.items()
        if any(marker in str(step.get("run", "")) for marker in ("leg-", "conformance", "-m postgres"))
    }
    assert substrate == set(ALWAYS_RUN_STEPS), sorted(substrate ^ set(ALWAYS_RUN_STEPS))
