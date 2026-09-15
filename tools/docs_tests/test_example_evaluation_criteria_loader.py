"""The example-evaluation policy is loaded from `CLAUDE.md` and exists where it points.

The smallest guard the policy change asked for: the loader text is present in
the root `CLAUDE.md`, the canonical document exists at the path the loader
names, and the reference resolves to that file. Nothing here parses or
enforces the policy's content — the policy requires human and agent judgment,
and a checker that pretended otherwise would be the vacuous gate this
repository refuses elsewhere.
"""

from __future__ import annotations

import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
POLICY = REPO_ROOT / "docs" / "EXAMPLE-EVALUATION-CRITERIA.md"
POLICY_REFERENCE = "docs/EXAMPLE-EVALUATION-CRITERIA.md"
LOADER_HEADING = "### Example Development and Evaluation — REQUIRED"


def test_the_policy_document_exists_and_is_titled() -> None:
    assert POLICY.is_file(), f"{POLICY_REFERENCE} is missing"
    first_heading = next(
        line for line in POLICY.read_text(encoding="utf-8").splitlines() if line.startswith("# ")
    )
    assert first_heading == "# CCF Example Evaluation Criteria"


def test_claude_md_carries_the_required_loader() -> None:
    text = CLAUDE_MD.read_text(encoding="utf-8")
    assert LOADER_HEADING in text, "CLAUDE.md lacks the required loader section"
    body = text[text.index(LOADER_HEADING) + len(LOADER_HEADING):]
    following = body.find("\n### ")
    section = body if following < 0 else body[:following]
    assert f"`{POLICY_REFERENCE}`" in section
    assert re.search(r"MUST read `docs/EXAMPLE-EVALUATION-CRITERIA\.md` in full", section)
    assert "STOP and surface the conflict" in section


def test_the_reference_resolves_from_the_repository_root() -> None:
    text = CLAUDE_MD.read_text(encoding="utf-8")
    referenced = {match for match in re.findall(r"`(docs/EXAMPLE-EVALUATION-CRITERIA\.md)`", text)}
    assert referenced == {POLICY_REFERENCE}
    assert (REPO_ROOT / POLICY_REFERENCE).resolve() == POLICY.resolve()
    assert (REPO_ROOT / POLICY_REFERENCE).is_file()
