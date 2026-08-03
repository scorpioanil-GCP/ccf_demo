"""Unit tests for the D-02 never-publish gate (CLAUDE.md §2.2; D-20).

The gate is itself tested because it *is* the enforcement mechanism for the
never-publish guarantee — the same reason `tools/lints/tests/` exists for
CINV-01/02/03. A gate nobody tests is a gate that can silently stop firing,
which is the exact failure mode `pub01`'s self-test exists to catch.
"""

from __future__ import annotations

import pathlib

from tools.publish_scan import (
    RULE_INCLUDE_ESCAPE,
    RULE_INTERNAL_PATH,
    RULE_SHINGLE,
    RULE_SYMLINK,
    WHITEPAPER,
    main,
    scan_prebuild,
    scan_text,
    whitepaper_shingles,
)

PAGE = pathlib.Path("site/reference/index.html")


def _rules(findings: list[str]) -> list[str]:
    return [f.split()[1] for f in findings]


def _read(rel: str) -> str:
    return pathlib.Path(rel).read_text(encoding="utf-8")


# --- violating cases -------------------------------------------------------


def test_whitepaper_text_trips_the_shingle_rule() -> None:
    # The self-test polarity: fed its own source, the scan must fire.
    findings = scan_text(_read(WHITEPAPER), PAGE, whitepaper_shingles())
    assert findings
    assert RULE_SHINGLE in findings[0]


def test_internal_derived_doc_is_a_positive_control() -> None:
    findings = scan_text(_read("docs/DESIGN.md"), PAGE, whitepaper_shingles())
    assert len([f for f in findings if RULE_SHINGLE in f]) > 20


def test_whitepaper_named_path_trips_the_internal_path_rule() -> None:
    path = pathlib.Path("site/CCF_Whitepaper_1-2/index.html")
    assert RULE_INTERNAL_PATH in _rules(scan_text("hello", path, frozenset()))


def test_figure_reference_trips_the_internal_path_rule() -> None:
    findings = scan_text("see Fig-CH07-03 for the seam", PAGE, frozenset())
    assert RULE_INTERNAL_PATH in _rules(findings)


def test_symlink_under_the_public_tree_trips_the_symlink_rule(
    tmp_path: pathlib.Path,
) -> None:
    root = tmp_path / "public"
    root.mkdir()
    (root / "page.md").write_text("clean\n", encoding="utf-8")
    (root / "leak.md").symlink_to(pathlib.Path(WHITEPAPER).resolve())
    assert RULE_SYMLINK in _rules(scan_prebuild(root))


def test_include_reaching_into_docs_trips_the_include_escape_rule(
    tmp_path: pathlib.Path,
) -> None:
    root = tmp_path / "public"
    root.mkdir()
    (root / "page.md").write_text('--8<-- "docs/DECISIONS.md"\n', encoding="utf-8")
    assert RULE_INCLUDE_ESCAPE in _rules(scan_prebuild(root))


def test_include_reaching_into_planning_trips_the_include_escape_rule(
    tmp_path: pathlib.Path,
) -> None:
    root = tmp_path / "public"
    root.mkdir()
    (root / "page.md").write_text('--8<-- ".planning/ROADMAP.md"\n', encoding="utf-8")
    assert RULE_INCLUDE_ESCAPE in _rules(scan_prebuild(root))


# --- clean cases -----------------------------------------------------------


def test_the_two_moved_public_docs_are_shingle_clean() -> None:
    shingles = whitepaper_shingles()
    for rel in ("docs/security-notes.md", "docs/demo-walkthrough.md"):
        findings = scan_text(_read(rel), PAGE, shingles)
        assert [f for f in findings if RULE_SHINGLE in f] == []


def test_include_of_example_source_is_clean(tmp_path: pathlib.Path) -> None:
    root = tmp_path / "public"
    root.mkdir()
    (root / "page.md").write_text(
        '--8<-- "examples/00-quickstart/run.py:assemble"\n', encoding="utf-8"
    )
    assert scan_prebuild(root) == []


def test_section_reference_and_decision_id_are_clean() -> None:
    # D-18 and D-22 compatibility: a `§7.6` cross-reference and a `D-IMPL-71`
    # identifier are identifiers, not body text, and cannot form a ten-word
    # shingle. Publishing them is legal and must stay legal.
    shingles = whitepaper_shingles()
    assert scan_text("See §7.6 for the delivery contract.", PAGE, shingles) == []
    assert scan_text("Resolved as D-IMPL-71.", PAGE, shingles) == []


# --- the denylist boundary -------------------------------------------------


def test_a_longer_word_containing_a_denylist_token_is_not_flagged() -> None:
    # `PHASE_INTEGRATION` merely starts with `PHASE_I`; the boundary must hold
    # or every future page whose name shares a prefix becomes unpublishable —
    # the same discipline `matches_module` applies to dotted module names.
    path = pathlib.Path("site/PHASE_INTEGRATION_guide/index.html")
    assert scan_text("harmless prose about nothing at all", path, frozenset()) == []


def test_the_real_internal_deliverable_name_still_matches() -> None:
    path = pathlib.Path("site/PHASE_I1_GATE/index.html")
    assert RULE_INTERNAL_PATH in _rules(scan_text("x", path, frozenset()))


# --- exit codes ------------------------------------------------------------


def test_main_exits_one_on_a_leaking_tree(tmp_path: pathlib.Path) -> None:
    tree = tmp_path / "site"
    tree.mkdir()
    (tree / "leak.html").write_text(_read(WHITEPAPER), encoding="utf-8")
    assert main([str(tree)]) == 1


def test_main_exits_zero_on_a_clean_tree(tmp_path: pathlib.Path) -> None:
    tree = tmp_path / "site"
    tree.mkdir()
    (tree / "ok.html").write_text("<p>Nothing to see here.</p>\n", encoding="utf-8")
    assert main([str(tree)]) == 0


def test_main_exits_zero_in_prebuild_mode_on_this_repo() -> None:
    # There is no `--root`: the pre-build tree is a constant, so the mode
    # cannot be pointed somewhere harmless to make it pass.
    assert main(["--pre-build"]) == 0
