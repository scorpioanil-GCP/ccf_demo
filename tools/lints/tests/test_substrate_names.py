"""Unit tests for ``cinv04-substrate-name`` / ``-prose`` (D-IMPL-93 property (2)).

Written before the property is true of the tree. The negative controls are the
evidence that the two rules *fire*; a rule with only green tests cannot be told
apart from a rule with a broken matcher (T-15.4-13). The rules are registered in
``CHECKERS`` by plan 15.4-07, in the first commit where they can pass.

Fixture vocabulary is read from the adapter package on disk rather than typed
out, so these tests keep working when the set of adapters changes — which is the
same property the checker itself claims, exercised from the outside.
"""

from __future__ import annotations

import pathlib

import pytest

from tools.lints.substrate_names import (
    PROSE_DISTINCT_THRESHOLD,
    RULE_SUBSTRATE_NAME,
    RULE_SUBSTRATE_PROSE,
    SUBSTRATE_NAME_EXEMPT_PACKAGES,
    check_source,
    substrate_vocabulary,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
MANIFEST = pathlib.Path("src/ccf/deployment/manifest.py")

VOCABULARY = sorted(substrate_vocabulary(REPO_ROOT))


def _rules(findings: list[str]) -> list[str]:
    return [f.split()[1] for f in findings]


def _docstring_module(words: list[str]) -> str:
    """A module that is nothing but a docstring naming `words`."""
    return f'"""A note about {", ".join(words)} and how they differ."""\n'


def test_the_adapter_package_is_actually_populated() -> None:
    # Every other test in this module is vacuous if the vocabulary is empty,
    # and an empty vocabulary makes the checker silent rather than wrong — so
    # it would be a silent vacuum. Fail loudly instead.
    assert len(VOCABULARY) >= PROSE_DISTINCT_THRESHOLD


# --- the vocabulary is derived from disk (V4) -------------------------------


def test_vocabulary_is_read_from_disk_not_from_a_list(
    tmp_path: pathlib.Path,
) -> None:
    # `zzquux` appears nowhere in this repository. If the vocabulary were a
    # typed-out list this assertion could not pass.
    backends = tmp_path / "src" / "ccf" / "graph" / "backends"
    backends.mkdir(parents=True)
    (backends / "__init__.py").write_text("", encoding="utf-8")
    (backends / "zzquux.py").write_text("", encoding="utf-8")
    (backends / "zzquux_write.py").write_text("", encoding="utf-8")

    assert substrate_vocabulary(tmp_path) == frozenset({"zzquux"})
    assert "zzquux" not in VOCABULARY


def test_a_derived_vocabulary_word_is_what_the_rule_matches(
    tmp_path: pathlib.Path,
) -> None:
    # The full loop: a stem that exists only in a temporary tree becomes the
    # forbidden word, with no edit to the checker.
    backends = tmp_path / "src" / "ccf" / "graph" / "backends"
    backends.mkdir(parents=True)
    (backends / "zzquux.py").write_text("", encoding="utf-8")

    findings = check_source(
        "zzquux_dsn: str | None = None\n",
        MANIFEST,
        "ccf.deployment.manifest",
        base=tmp_path,
    )
    assert _rules(findings) == [RULE_SUBSTRATE_NAME]
    assert "zzquux" in findings[0]


def test_an_empty_adapter_package_makes_the_rules_silent(
    tmp_path: pathlib.Path,
) -> None:
    (tmp_path / "src" / "ccf" / "graph" / "backends").mkdir(parents=True)
    assert (
        check_source(
            _docstring_module(VOCABULARY),
            MANIFEST,
            "ccf.deployment.manifest",
            base=tmp_path,
        )
        == []
    )


# --- sub-rule 2a: code positions (V2) --------------------------------------


def test_an_annotated_parameter_naming_a_substrate_is_flagged() -> None:
    findings = check_source(
        "postgres_dsn: str | None = None\n", MANIFEST, "ccf.deployment.manifest"
    )
    assert RULE_SUBSTRATE_NAME in _rules(findings)
    assert "postgres" in findings[0]


def test_a_string_literal_naming_a_substrate_is_flagged() -> None:
    source = 'def required() -> str:\n    return "neo4j_uri"\n'
    findings = check_source(source, MANIFEST, "ccf.deployment.manifest")
    assert RULE_SUBSTRATE_NAME in _rules(findings)


def test_a_function_name_and_a_parameter_name_are_both_positions() -> None:
    for source in ("def open_mongo() -> None:\n    pass\n",
                   "def open_store(fluree_url: str) -> None:\n    pass\n"):
        findings = check_source(source, MANIFEST, "ccf.deployment.manifest")
        assert RULE_SUBSTRATE_NAME in _rules(findings), source


def test_an_import_alias_naming_a_substrate_is_flagged() -> None:
    findings = check_source(
        "import ccf.graph.backends.sqlite as store\n",
        MANIFEST,
        "ccf.deployment.manifest",
    )
    assert RULE_SUBSTRATE_NAME in _rules(findings)


def test_an_attribute_naming_a_substrate_is_flagged() -> None:
    source = "def f(cfg: object) -> object:\n    return cfg.memory_rows\n"
    findings = check_source(source, MANIFEST, "ccf.deployment.manifest")
    assert RULE_SUBSTRATE_NAME in _rules(findings)


def test_a_docstring_is_not_a_code_position() -> None:
    # One name in prose is neither a 2a finding nor a 2b one.
    findings = check_source(
        _docstring_module(VOCABULARY[:1]), MANIFEST, "ccf.deployment.manifest"
    )
    assert findings == []


def test_ordinary_core_source_is_clean() -> None:
    source = (
        '"""Resolve the adapter a deployment names."""\n'
        "from ccf.graph.registry import resolve\n"
        "\n"
        "def open_store(name: str, connection: dict[str, object]) -> object:\n"
        '    """Open the named adapter\'s store."""\n'
        "    return resolve(name).open_store(connection)\n"
    )
    assert check_source(source, MANIFEST, "ccf.deployment.manifest") == []


# --- sub-rule 2b: docstring enumeration (V3) -------------------------------


def test_a_docstring_enumerating_three_substrates_is_flagged() -> None:
    findings = check_source(
        _docstring_module(VOCABULARY[:PROSE_DISTINCT_THRESHOLD]),
        MANIFEST,
        "ccf.deployment.manifest",
    )
    assert _rules(findings) == [RULE_SUBSTRATE_PROSE]
    assert str(PROSE_DISTINCT_THRESHOLD) in findings[0]


def test_a_docstring_naming_two_substrates_is_a_comparison_not_a_catalogue() -> None:
    # The threshold has a step of margin: comparative prose stays legal.
    findings = check_source(
        _docstring_module(VOCABULARY[: PROSE_DISTINCT_THRESHOLD - 1]),
        MANIFEST,
        "ccf.deployment.manifest",
    )
    assert findings == []


def test_repeating_one_substrate_name_is_not_an_enumeration() -> None:
    word = VOCABULARY[0]
    findings = check_source(
        _docstring_module([word, word, word]), MANIFEST, "ccf.deployment.manifest"
    )
    assert findings == []


def test_a_function_docstring_counts_as_its_own_docstring() -> None:
    words = ", ".join(VOCABULARY[:PROSE_DISTINCT_THRESHOLD])
    source = f'def f() -> None:\n    """Differences between {words}."""\n'
    findings = check_source(source, MANIFEST, "ccf.deployment.manifest")
    assert _rules(findings) == [RULE_SUBSTRATE_PROSE]
    assert findings[0].startswith(f"{MANIFEST}:2 ")


# --- scope (V2) -------------------------------------------------------------

VIOLATING = (
    _docstring_module(VOCABULARY[:PROSE_DISTINCT_THRESHOLD])
    + "postgres_dsn: str | None = None\n"
)


def test_the_violating_fixture_really_does_violate() -> None:
    findings = check_source(VIOLATING, MANIFEST, "ccf.deployment.manifest")
    assert set(_rules(findings)) == {RULE_SUBSTRATE_NAME, RULE_SUBSTRATE_PROSE}


@pytest.mark.parametrize(
    "module_name",
    ["ccf.similarity.sqlite_vec_index", "ccf.graph.backends.sqlite"],
)
def test_exempt_packages_are_silent(module_name: str) -> None:
    assert check_source(VIOLATING, MANIFEST, module_name) == []


def test_the_exemption_is_dot_bounded() -> None:
    # `ccf.similarity_evil` shares a string prefix with an exempt package but is
    # not a dotted descendant of it.
    findings = check_source(VIOLATING, MANIFEST, "ccf.similarity_evil")
    assert set(_rules(findings)) == {RULE_SUBSTRATE_NAME, RULE_SUBSTRATE_PROSE}


def test_the_registry_is_not_exempt_and_does_not_need_to_be() -> None:
    # The registry derives its adapter set and names none, so a passing rule is
    # the evidence — not an exemption.
    assert "ccf.graph.registry" not in SUBSTRATE_NAME_EXEMPT_PACKAGES
    source = (
        '"""Resolve a registered adapter by the name a manifest gives."""\n'
        "REGISTRATIONS: dict[str, object] = {}\n"
    )
    assert check_source(source, MANIFEST, "ccf.graph.registry") == []


def test_the_exempt_set_has_exactly_two_reviewed_entries() -> None:
    # T-15.4-12: the exception surface is the checker's own attack surface. A
    # third entry is a decision, and this test makes it one that has to be made
    # on purpose.
    assert len(SUBSTRATE_NAME_EXEMPT_PACKAGES) == 2
