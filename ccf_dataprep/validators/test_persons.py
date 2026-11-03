#!/usr/bin/env python3
"""Pure tests for person identity: keys, name parsing, scoring, banding.

Case group 4 pins the FALSE-POSITIVE PAIR found in the 2026-08-18 Form 4 probe:
`Davison James E` and `Davison James E. Jr.` file against the same issuer under
DISTINCT CIKs (1403411, 1403412). They are two different people whose names
fuzzy-match at near unity. CLAUDE.md rule 5 requires exactly one such pair, and
this one is REAL, so it is labelled `public` rather than engineered.

The banding function therefore must not resolve a near-unity score to a match
when the CIKs differ. A resolver that scores names and stops is the bug this
dataset exists to make visible.

    uv run validators/test_persons.py
"""

from __future__ import annotations

import sys

from generators.persons import (match_band, match_score, normalize_name,
                                parse_filed_name, person_key, render_display)


def check_keys() -> list[tuple[str, bool]]:
    real = person_key("0001277036", "SRINIVASAN RAMESH")
    minted_a = person_key(None, "Jane Q Public")
    minted_b = person_key(None, "Jane Q Public")
    minted_c = person_key(None, "John Q Public")
    return [
        ("a real CIK becomes the key verbatim", real == "0001277036"),
        ("a short CIK is zero-padded", person_key("78749", "X") == "0000078749"),
        ("a minted key carries the syn-p- prefix", minted_a.startswith("syn-p-")),
        ("minted keys are deterministic", minted_a == minted_b),
        ("different names mint different keys", minted_a != minted_c),
        ("a minted key is visibly not a CIK", not minted_a.isdigit()),
    ]


def check_name_parsing() -> list[tuple[str, bool]]:
    a = parse_filed_name("SRINIVASAN RAMESH")
    b = parse_filed_name("Davison James E. Jr.")
    c = parse_filed_name("Wood William David III")
    return [
        ("last name first is the filed order", a["last"] == "SRINIVASAN"),
        ("first name follows", a["first"] == "RAMESH"),
        ("a middle initial is captured", b["middle"] == "E."),
        ("a generational suffix is split off", b["suffix"] == "Jr."),
        ("suffix is not mistaken for a middle name", c["suffix"] == "III"),
        ("multi-token middle names survive", c["middle"] == "David"),
    ]


def check_normalization() -> list[tuple[str, bool]]:
    return [
        ("case is folded",
         normalize_name("SRINIVASAN RAMESH") == normalize_name("Srinivasan Ramesh")),
        ("filed order and display order agree",
         normalize_name("SRINIVASAN RAMESH") == normalize_name("Ramesh Srinivasan")),
        ("punctuation is dropped",
         normalize_name("Davison James E.") == normalize_name("Davison James E")),
        ("suffixes are stripped before comparison",
         normalize_name("Davison James E Jr.") == normalize_name("Davison James E")),
        ("distinct people still differ",
         normalize_name("Jones Dana Sue") != normalize_name("Jones Dana Lee")),
    ]


def check_false_positive_pair() -> list[tuple[str, bool]]:
    a, b = "Davison James E", "Davison James E. Jr."
    score = match_score(a, b)
    return [
        ("the real pair scores at or near unity", score >= 0.95),
        ("differing CIKs force a false_positive band",
         match_band(score, same_cik=False) == "false_positive"),
        ("the same CIK at the same score is exact",
         match_band(score, same_cik=True) == "exact"),
        ("an unknown CIK at a high score is only strong",
         match_band(score, same_cik=None) == "strong"),
        ("a middling score with no CIK is weak",
         match_band(0.72, same_cik=None) == "weak"),
        ("unrelated names do not band as strong",
         match_band(match_score("Jones Dana Sue", "MUTCH JOHN"), None) == "weak"),
    ]


def check_display() -> list[tuple[str, bool]]:
    d = render_display(parse_filed_name("SRINIVASAN RAMESH"))
    e = render_display(parse_filed_name("Davison James E. Jr."))
    return [
        ("display order is first-last", d == "RAMESH SRINIVASAN"),
        ("middle and suffix are preserved in display",
         e == "James E. Davison Jr."),
    ]


def main() -> int:
    cases = (check_keys() + check_name_parsing() + check_normalization()
             + check_false_positive_pair() + check_display())
    failures = sum(not ok for _, ok in cases)
    for label, ok in cases:
        print(f"  [{'ok  ' if ok else 'FAIL'}] {label}")
    print(f"\n  {len(cases) - failures}/{len(cases)} cases behave as specified\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
