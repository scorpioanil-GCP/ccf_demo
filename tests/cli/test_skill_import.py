"""``ccf skill import`` — the one-way D-18 SKILL.md importer (07-11 Task 2).

Written before the implementation per the TDD discipline. The claims,
each from the D-IMPL-56 SKILL.md-authoring ruling:

**Mapping.** Frontmatter ``name``/``description`` → the catalog entry;
the body → a registered ``ccf.prompt-artifact``; ``references/`` →
further pinned artifacts; the entry is a ``procedure`` bound by an
``InstructionBinding`` reference — never inline text.

**allowed-tools is NOT mapped.** A harness permission token is not a
policy-regime identifier (D-IMPL-29): the fixture declares allowed-tools
and the imported entry's requirements are unaffected.

**One-way.** Re-import registers a new version through normal Control
Plane registration; nothing writes back to the directory.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from ccf.agents.definitions import PROMPT_ARTIFACT, PromptArtifact
from ccf.skills.catalog import SKILL_CATALOG_ENTRY, SkillCatalogEntry

from cli.conftest import Fabric, run_cli

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "skillmd"
    / "covenant-walkthrough"
)


def _import(
    deps: Any,
    capsys: pytest.CaptureFixture[str],
    directory: Path,
    *,
    version: str = "1.0.0",
) -> tuple[int, str]:
    code, out, _ = run_cli(
        [
            "skill",
            "import",
            str(directory),
            "--tenant",
            "acme-bank",
            "--version",
            version,
        ],
        capsys,
        dependencies=deps,
    )
    return code, out


def _entry(fabric: Fabric, name: str) -> SkillCatalogEntry:
    key = f"acme-bank/{SKILL_CATALOG_ENTRY.class_id}/{name}"
    _version, artifact = fabric.registry.resolve_latest(key)
    entry = SKILL_CATALOG_ENTRY.validate(artifact)
    assert isinstance(entry, SkillCatalogEntry)
    return entry


def test_import_yields_a_procedure_entry_with_referenced_artifacts(
    fabric: Fabric, deps: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out = _import(deps, capsys, FIXTURE)
    assert code == 0, out

    entry = _entry(fabric, "covenant-walkthrough")
    assert entry.skill_type == "procedure"
    assert entry.name == "covenant-walkthrough"
    # the description is the frontmatter's statement, verbatim source
    assert entry.description.startswith(
        "Walk a counterparty's covenant metrics"
    )
    # an explicit empty-arguments schema — declared, never a placeholder
    assert dict(entry.argument_schema.properties) == {}
    assert entry.argument_schema.required == ()

    # the body is a registered prompt artifact, bound by InstructionBinding
    # reference (never inline), with parameters derived from the body itself
    binding: Any = entry.binding
    prompt_uri = binding.instruction.prompt
    assert prompt_uri.startswith("ccf-artifact://acme-bank/")
    assert binding.instruction.parameters == ("entity_name",)
    key = f"acme-bank/{PROMPT_ARTIFACT.class_id}/covenant-walkthrough"
    _version, artifact = fabric.registry.resolve_latest(key)
    prompt = PROMPT_ARTIFACT.validate(artifact)
    assert isinstance(prompt, PromptArtifact)
    body = (FIXTURE / "SKILL.md").read_text().split("---", 2)[2]
    assert prompt.template.strip() == body.strip()
    assert prompt.declared_parameters == ("entity_name",)

    # references/ registered as further pinned artifacts
    reference_key = (
        f"acme-bank/{PROMPT_ARTIFACT.class_id}/"
        "covenant-walkthrough-reference-checklist"
    )
    _version, reference = fabric.registry.resolve_latest(reference_key)
    referenced = PROMPT_ARTIFACT.validate(reference)
    assert isinstance(referenced, PromptArtifact)
    assert "Review checklist" in referenced.template


def test_allowed_tools_is_not_mapped_onto_requirements(
    fabric: Fabric, deps: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    frontmatter = (FIXTURE / "SKILL.md").read_text().split("---", 2)[1]
    assert "allowed-tools" in frontmatter  # the fixture really declares it
    entry = _entry(fabric, "covenant-walkthrough")
    # a harness permission token is not a policy-regime identifier
    # (D-IMPL-29): requirements are unaffected by allowed-tools
    assert entry.requirements.required_scopes == frozenset()
    assert entry.requirements.required_context_products == frozenset()


def test_import_is_one_way_and_versioned(
    fabric: Fabric,
    deps: Any,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    working = tmp_path / "covenant-walkthrough"
    shutil.copytree(FIXTURE, working)
    before = {
        p.relative_to(working): p.read_bytes()
        for p in sorted(working.rglob("*"))
        if p.is_file()
    }
    code, _ = _import(deps, capsys, working)
    assert code == 0

    # nothing writes back to the directory — same files, same bytes
    after = {
        p.relative_to(working): p.read_bytes()
        for p in sorted(working.rglob("*"))
        if p.is_file()
    }
    assert after == before

    # a changed body re-imports as a NEW version through normal Control
    # Plane registration (one-way; the directory is never canonical)
    skill_md = working / "SKILL.md"
    skill_md.write_text(skill_md.read_text() + "\n5. File the narrative.\n")
    code, _ = _import(deps, capsys, working, version="1.0.1")
    assert code == 0
    key = f"acme-bank/{SKILL_CATALOG_ENTRY.class_id}/covenant-walkthrough"
    assert len(fabric.registry.versions(key)) >= 2

    # an unbumped changed re-import is the registry's typed refusal
    skill_md.write_text(skill_md.read_text() + "\n6. Archive it.\n")
    code, out = _import(deps, capsys, working, version="1.0.1")
    assert code == 1
    assert json.loads(out.splitlines()[-1])


def test_import_parses_and_dispatches() -> None:
    from ccf_runtime.cli.main import build_parser

    parsed = build_parser().parse_args(
        ["skill", "import", "some-dir", "--tenant", "t", "--version", "1.0.0"]
    )
    assert getattr(parsed, "build", None) is not None
