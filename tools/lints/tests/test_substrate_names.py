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
    GENERIC_WORD_STEMS,
    PROSE_DISTINCT_THRESHOLD,
    RULE_SUBSTRATE_NAME,
    RULE_SUBSTRATE_PROSE,
    SUBSTRATE_NAME_EXEMPT_PACKAGES,
    EmptySubstrateVocabulary,
    check_source,
    substrate_vocabulary,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
MANIFEST = pathlib.Path("src/ccf/deployment/manifest.py")

VOCABULARY = sorted(substrate_vocabulary(REPO_ROOT))

#: The adapters this repository ships whose stem is also ordinary English, and
#: one of them. Derived rather than named, so the WR-04 assertions below follow
#: the vocabulary the way every other test in this module does.
GENERIC_STEMS_IN_VOCABULARY = sorted(set(VOCABULARY) & GENERIC_WORD_STEMS)
GENERIC_WORD = GENERIC_STEMS_IN_VOCABULARY[0] if GENERIC_STEMS_IN_VOCABULARY else ""

#: A stem that is *not* on the generic list, for the assertions about the loose
#: boundary that the generic ones no longer carry.
DISTINCT_WORD = next(word for word in VOCABULARY if word not in GENERIC_WORD_STEMS)


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


def test_an_empty_adapter_package_is_refused_not_ignored(
    tmp_path: pathlib.Path,
) -> None:
    """WR-03 — a checker that cannot see its vocabulary must not report clean.

    The rule used to answer the empty set here and return no findings for every
    file. That is fail-open on the rule carrying D-IMPL-93 property (2): it
    still runs, still passes, and guards nothing — the exact defect class this
    module's own docstring indicts.
    """
    (tmp_path / "src" / "ccf" / "graph" / "backends").mkdir(parents=True)

    with pytest.raises(EmptySubstrateVocabulary):
        substrate_vocabulary(tmp_path)

    with pytest.raises(EmptySubstrateVocabulary):
        check_source(
            _docstring_module(VOCABULARY),
            MANIFEST,
            "ccf.deployment.manifest",
            base=tmp_path,
        )


def test_a_missing_adapter_package_is_refused_by_name(
    tmp_path: pathlib.Path,
) -> None:
    """The other half of WR-03, and the one `repo_base_for` can reach.

    Its fallback is the working directory, so a run rooted anywhere without the
    adapter package took this path by an ordinary route rather than an exotic
    one. The refusal names the directory it looked in, because "the checker is
    pointed at the wrong tree" and "the package moved" are different problems
    with the same symptom.
    """
    with pytest.raises(EmptySubstrateVocabulary) as caught:
        substrate_vocabulary(tmp_path)

    assert "backends" in str(caught.value)


def test_the_repo_vocabulary_is_non_empty_and_holds_a_known_adapter() -> None:
    # Non-vacuity for the whole module and for `make lint`: the rule really is
    # reading adapters off this repository's own disk.
    assert VOCABULARY
    assert substrate_vocabulary(REPO_ROOT) == frozenset(VOCABULARY)


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
    source = f"def f(cfg: object) -> object:\n    return cfg.{DISTINCT_WORD}_rows\n"
    findings = check_source(source, MANIFEST, "ccf.deployment.manifest")
    assert RULE_SUBSTRATE_NAME in _rules(findings)


# --- generic stems match strictly (WR-04) -----------------------------------
#
# One adapter is named for a word core uses about something else. Under the
# loose boundary the rule read both false positives below as "core names the
# graph substrate", and D-13 forbids an allowlist — so the only escape was
# exempting a whole package, which disables the rule for that package entirely.


@pytest.mark.skipif(
    not GENERIC_STEMS_IN_VOCABULARY,
    reason="no adapter is named for a word on the generic list",
)
@pytest.mark.parametrize("attached", ["in-{word}", "{word}_budget", "{word}-mapped"])
def test_a_generic_stem_inside_a_larger_word_is_not_a_substrate(
    attached: str,
) -> None:
    """The false positives: neither line is about a graph substrate."""
    text = attached.format(word=GENERIC_WORD)
    source = f'CACHE_MODE = "{text}"\n'
    assert check_source(source, MANIFEST, "ccf.artifacts.store") == []


@pytest.mark.skipif(
    not GENERIC_STEMS_IN_VOCABULARY,
    reason="no adapter is named for a word on the generic list",
)
@pytest.mark.parametrize(
    "source",
    [
        'BACKEND = "{word}"\n',
        "def open_store({word}: object) -> None:\n    pass\n",
        "def {word}() -> None:\n    pass\n",
    ],
)
def test_a_generic_stem_as_a_whole_token_is_still_flagged(source: str) -> None:
    """The true positive the strict boundary keeps.

    The bare adapter name in a code position is the form every deletion in this
    phase took — a value in a `Literal`, a branch key, a per-database keyword
    argument. Losing that would have made the escape a hole rather than a
    narrowing.
    """
    findings = check_source(
        source.format(word=GENERIC_WORD), MANIFEST, "ccf.deployment.manifest"
    )
    assert _rules(findings) == [RULE_SUBSTRATE_NAME]
    assert GENERIC_WORD in findings[0]


@pytest.mark.skipif(
    not GENERIC_STEMS_IN_VOCABULARY,
    reason="no adapter is named for a word on the generic list",
)
def test_a_generic_stem_still_counts_toward_the_prose_threshold() -> None:
    # The escape is about compound *tokens*, not about prose: a docstring that
    # lists it alongside two others is still a catalogue.
    words = [GENERIC_WORD] + [
        word for word in VOCABULARY if word != GENERIC_WORD
    ][: PROSE_DISTINCT_THRESHOLD - 1]
    findings = check_source(
        _docstring_module(words), MANIFEST, "ccf.deployment.manifest"
    )
    assert _rules(findings) == [RULE_SUBSTRATE_PROSE]


def test_a_distinctive_stem_keeps_the_loose_boundary(
    tmp_path: pathlib.Path,
) -> None:
    """The trade is per-word, not global.

    A stem that is not on the generic list still matches inside a compound
    token, which is what catches a reintroduced `<name>_dsn` parameter. Pinned
    against a synthetic adapter package so the assertion does not depend on
    which adapters this repository happens to ship.
    """
    backends = tmp_path / "src" / "ccf" / "graph" / "backends"
    backends.mkdir(parents=True)
    (backends / "zzquux_write.py").write_text("", encoding="utf-8")

    findings = check_source(
        "zzquux_dsn: str | None = None\n",
        MANIFEST,
        "ccf.deployment.manifest",
        base=tmp_path,
    )
    assert _rules(findings) == [RULE_SUBSTRATE_NAME]


def test_a_generic_stem_in_a_synthetic_package_is_matched_strictly(
    tmp_path: pathlib.Path,
) -> None:
    """The measured half of WR-04: the trade pinned, not left latent.

    A synthetic adapter package whose stem is on the generic list, so the
    behaviour is asserted over a vocabulary this test controls rather than over
    whichever adapters ship today. Both directions in one place: the compound
    token is silent, the whole token still fires.
    """
    assert GENERIC_WORD_STEMS, "an escape with no entries measures nothing"
    word = sorted(GENERIC_WORD_STEMS)[0]
    backends = tmp_path / "src" / "ccf" / "graph" / "backends"
    backends.mkdir(parents=True)
    (backends / f"{word}_write.py").write_text("", encoding="utf-8")

    quiet = check_source(
        f'MODE = "in-{word}"\n', MANIFEST, "ccf.deployment.manifest", base=tmp_path
    )
    loud = check_source(
        f'BACKEND = "{word}"\n', MANIFEST, "ccf.deployment.manifest", base=tmp_path
    )
    assert quiet == []
    assert _rules(loud) == [RULE_SUBSTRATE_NAME]


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


def test_the_generic_stem_escape_has_exactly_one_reviewed_entry() -> None:
    # Same discipline as the exempt set below and for the same reason: this is
    # the other place the checker gives ground, so growing it should be a
    # decision somebody makes on purpose rather than a line somebody adds.
    assert GENERIC_WORD_STEMS == frozenset({"memory"})


def test_the_exempt_set_has_exactly_two_reviewed_entries() -> None:
    # T-15.4-12: the exception surface is the checker's own attack surface. A
    # third entry is a decision, and this test makes it one that has to be made
    # on purpose.
    assert len(SUBSTRATE_NAME_EXEMPT_PACKAGES) == 2
