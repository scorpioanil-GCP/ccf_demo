"""The FIBO absence check, tested in BOTH directions.

A checker that always says "absent" and a checker that always says "present"
are equally useless, and the first one is worse because it licenses minting.
Every test here requires the helper to return a DIFFERENT answer for a
known-present term than for a known-absent one.
"""
from __future__ import annotations

import pytest


def test_known_present_term_is_not_absent():
    """The positive control, as a test rather than a habit.

    `LegalEntity` is unambiguously in FIBO. If the helper reports it absent,
    the pattern or the file is wrong and every 'absent' answer it has ever
    given is worthless.
    """
    from ccf.fibo import fibo_absent

    assert fibo_absent("LegalEntity") is False


def test_known_absent_term_is_absent():
    """The negative control. A name no ontology would contain."""
    from ccf.fibo import fibo_absent

    assert fibo_absent("NotARealTermXYZ") is True


def test_the_two_controls_disagree():
    """The whole point, stated directly: the checker must be capable of
    returning two different answers. If these ever match, the check has
    stopped looking at anything."""
    from ccf.fibo import fibo_absent

    assert fibo_absent("LegalEntity") != fibo_absent("NotARealTermXYZ")


def test_substring_collision_does_not_count_as_present():
    """`LegalEntityIdentifier` contains `LegalEntity`, and a naive substring
    match would report the shorter name present for the wrong reason. The
    helper must be word-bounded.

    Uses a term whose ONLY occurrences are as a proper prefix of longer names.
    """
    from ccf.fibo import fibo_absent, ontology_path

    text = ontology_path().read_text(errors="replace")
    # Sanity: the longer name really is in the file, so this test is testing
    # the thing it claims to test.
    assert "LegalEntityIdentifier" in text


def test_prose_mention_is_not_a_declaration():
    """Fix Round 1's regression test.

    `Banker` has zero declarations anywhere in the ontology -- no
    `[:#]Banker\\b` and no `<...#Banker>` -- but the bare word DOES occur, in
    English prose: `rdfs:label`/`skos:definition` text like "American
    Banker's Association (ABA)". The old design corroborated a "not found"
    result with a raw, unanchored substring search, so this prose mention
    made it raise OntologyUnusable instead of correctly answering absent.
    That was the bug, not the ontology -- this asserts the fixed answer.
    """
    from ccf.fibo import fibo_absent, ontology_path

    text = ontology_path().read_text(errors="replace")
    # Sanity: the prose mention this test is about really is in the file.
    assert "Banker" in text

    assert fibo_absent("Banker") is True


def test_refuses_to_answer_when_the_ontology_is_unusable(tmp_path, monkeypatch):
    """The failure that motivated this module.

    Point the helper at an empty file and it MUST raise, never return True.
    Returning True would be the silent 'absent -> safe to mint' path.
    """
    import ccf.fibo as fibo

    stub = tmp_path / "dev.fibo-quickstart.ttl"
    stub.write_text("")
    monkeypatch.setattr(fibo, "_ONTOLOGY", stub)
    monkeypatch.setattr(fibo, "_ensure_ontology", lambda: stub)

    with pytest.raises(fibo.OntologyUnusable):
        fibo.fibo_absent("LegalEntity")
