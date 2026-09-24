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

from ccf_runtime.cli.commands.skill_import import (
    MAX_REFERENCE_BYTES,
    MAX_REFERENCES,
)

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


# --- SEC-003: an imported skill directory is untrusted input -----------------
#
# The security review of 2026-09-23 found that `references/` was walked with
# `Path.is_file()`, which follows symlinks: a shared skill package could
# point a reference at ~/.aws/credentials and have the importer publish its
# bytes into the Control Plane. These tests fail against the pre-fix CLI.


def _package(root: Path, *, name: str) -> Path:
    """A minimal, well-formed skill directory to hang a probe on."""
    directory = root / name
    (directory / "references").mkdir(parents=True)
    (directory / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: A skill package under test.\n"
        "---\n\nBody text.\n"
    )
    return directory


def test_a_symlinked_reference_is_refused(
    fabric: Fabric,
    deps: Any,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """SEC-003. The exfiltration chain: a reference symlinked at a secret
    outside the package must not be read, let alone published."""
    secret = tmp_path / "credentials"
    secret.write_text("aws_secret_access_key = TOPSECRETVALUE\n")
    directory = _package(tmp_path, name="symlinked-reference")
    (directory / "references" / "usage.md").symlink_to(secret)

    code, out = _import(deps, capsys, directory)
    assert code != 0
    assert "symlink" in out.lower()
    assert "TOPSECRETVALUE" not in out
    # and nothing about it reached the Control Plane
    registered = fabric.registry.keys_of_class(PROMPT_ARTIFACT.class_id)
    assert not any("symlinked-reference-reference" in key for key in registered)


def test_a_symlinked_skill_document_is_refused(
    fabric: Fabric,
    deps: Any,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """SEC-003. SKILL.md itself is read with the same trust as a reference."""
    secret = tmp_path / "id_ed25519"
    secret.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\n")
    directory = tmp_path / "linked"
    (directory / "references").mkdir(parents=True)
    (directory / "SKILL.md").symlink_to(secret)

    code, out = _import(deps, capsys, directory)
    assert code != 0
    assert "symlink" in out.lower()


def test_an_oversized_reference_is_refused(
    fabric: Fabric,
    deps: Any,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """SEC-003. A reference is prompt text; an unbounded read of untrusted
    input is a resource hazard regardless of what the bytes are."""
    directory = _package(tmp_path, name="oversized")
    oversized = directory / "references" / "huge.md"
    oversized.write_bytes(b"x" * (MAX_REFERENCE_BYTES + 1))

    code, out = _import(deps, capsys, directory)
    assert code != 0
    assert "bytes" in out.lower()


def test_too_many_references_are_refused(
    fabric: Fabric,
    deps: Any,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """SEC-003. One import registers a bounded number of artifacts."""
    directory = _package(tmp_path, name="too-many")
    for index in range(MAX_REFERENCES + 1):
        (directory / "references" / f"r{index}.md").write_text("text\n")

    code, out = _import(deps, capsys, directory)
    assert code != 0
    assert "references" in out.lower()


def test_a_plain_reference_directory_still_imports(
    fabric: Fabric,
    deps: Any,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """The guards refuse the hostile case and pass the ordinary one."""
    directory = _package(tmp_path, name="ordinary")
    (directory / "references" / "usage.md").write_text("How to use it.\n")
    code, out = _import(deps, capsys, directory)
    assert code == 0, out
