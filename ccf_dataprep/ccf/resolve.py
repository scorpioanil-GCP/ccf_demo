"""The person-resolution scorer `kyc-refresh-beneficial-ownership` runs.

## Why this is not `generators.persons.match_score`

Wave 10 already has a scorer, and it is right for Wave 10's data and wrong for
this product's. `generators.persons.normalize_name` cleans with
`re.sub(r"[^a-z0-9 ]", " ", name.lower())`, which **deletes** every character
outside ASCII rather than folding it. Measured 2026-08-22:

    'Müller, Hans'  ->  'hans ller m'      score against 'Muller Hans': 0.818
    'Yusuf Al-Husseini' vs 'Youssef Al-Husayni'                        0.743

The first is the same person scoring as a near-miss because `ü` became a space
and split the token. Wave 10's roster is US proxy-statement names, all ASCII, so
this never bit it. §F5 is *specifically* about transliteration and diacritic
variants across registries, so a scorer that cannot see them would make the
condition untestable while appearing to test it.

This module folds instead (`ccf.names.normalize`), and Wave 10 keeps its own.
Two scorers, each named, with the boundary written down — rather than one
shared scorer that is silently wrong for one of its callers.

## Two similarity measures, combined by max

    sequence  character-level, catches spelling and transliteration drift
              (`Husseini` / `Husayni`)
    token     order-insensitive set overlap, catches rendering differences
              (`SMITH, ROBERT JAMES` / `Robert James Smith`)

Neither subsumes the other. A sorted-token normalizer would score the second
pair 1.0 and lose the ability to say *why*; a character-only measure scores
reordered names badly. `combined_score` takes the max and `explain()` reports
which measure carried it, because "these matched on order, not spelling" is the
distinction a reviewer needs.

## Thresholds come from the store, never from here

`Thresholds.load()` reads `ccf_v2.resolution_policy`. §D requires a confidence
per resolution and a review queue that is actually exercised, and
`docs/wave13b-design.md` §5 is explicit that a gate asserting "below certainty"
must read its bounds from loaded policy rows rather than from constants beside
the assertion. A gate holding its own copy of the thresholds agrees with itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from ccf.names import normalize, tokens

#: Bands, in descending confidence. `review` is the band §F6 needs exercised:
#: strictly between auto-clear and auto-reject, where a human must look.
BAND_EXACT = "exact"
BAND_STRONG = "strong"
BAND_REVIEW = "review"
BAND_WEAK = "weak"
BAND_FALSE_POSITIVE = "false_positive"

AGREE = "agree"
CONFLICT = "conflict"
UNKNOWN = "unknown"


def sequence_score(a: str, b: str) -> float:
    """Character-level similarity of two folded names."""
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def token_score(a: str, b: str) -> float:
    """Order-insensitive token overlap (Jaccard) of two folded names."""
    ta, tb = set(tokens(a)), set(tokens(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def combined_score(a: str, b: str) -> float:
    return max(sequence_score(a, b), token_score(a, b))


def explain(a: str, b: str) -> dict:
    """Both measures and which one carried the score."""
    seq, tok = sequence_score(a, b), token_score(a, b)
    return {
        "sequence": round(seq, 4),
        "token": round(tok, 4),
        "score": round(max(seq, tok), 4),
        "carried_by": "sequence" if seq >= tok else "token",
    }


@dataclass(frozen=True)
class Evidence:
    """Corroborating attributes §D names: DOB month/year and nationality."""

    dob_month: int | None = None
    dob_year: int | None = None
    nationality: str | None = None


def corroboration(a: Evidence, b: Evidence) -> str:
    """Do the non-name attributes agree, conflict, or say nothing?

    CONFLICT is returned on ANY disagreement in a field both sides carry.
    Two people with the same name and different birth years are two people,
    and the whole point of §F5's false-positive pair is that name similarity
    alone must not be allowed to overrule that.

    A field only one side carries is not evidence either way — it neither
    corroborates nor conflicts, which is why `unknown` is a third answer
    rather than a synonym for `agree`.
    """
    compared = 0
    for left, right in (
        (a.dob_year, b.dob_year),
        (a.dob_month, b.dob_month),
        (a.nationality, b.nationality),
    ):
        if left is None or right is None:
            continue
        compared += 1
        if str(left).strip().lower() != str(right).strip().lower():
            return CONFLICT
    return AGREE if compared else UNKNOWN


@dataclass(frozen=True)
class Thresholds:
    """Resolution bounds, as loaded from `ccf_v2.resolution_policy`."""

    auto_clear: float
    review_floor: float
    merge_threshold: float
    policy_version: str

    @classmethod
    def load(cls, cur, *, schema: str = "ccf_v2") -> "Thresholds":
        cur.execute(
            f'SELECT threshold_name, threshold_value, policy_version '
            f'FROM "{schema}".resolution_policy'
        )
        rows = cur.fetchall()
        if not rows:
            raise RuntimeError(
                "resolution_policy is empty. The thresholds must come from the "
                "store; a caller that falls back to constants here would be "
                "checking its own copy."
            )
        values = {name: float(value) for name, value, _ in rows}
        missing = {"auto_clear", "review_floor", "merge_threshold"} - set(values)
        if missing:
            raise RuntimeError(f"resolution_policy is missing {sorted(missing)}")
        return cls(
            auto_clear=values["auto_clear"],
            review_floor=values["review_floor"],
            merge_threshold=values["merge_threshold"],
            policy_version=rows[0][2],
        )


def band(score: float, corr: str, t: Thresholds) -> str:
    """Band a candidate pair. Corroborating evidence OUTRANKS name similarity.

    A high score with CONFLICTING evidence is a false positive, not a match —
    the same principle Wave 10 applied with CIK, restated for the attributes
    this product actually has. A resolver that scores names and stops is the
    failure the dataset exists to make visible (CLAUDE.md rule 5).
    """
    if corr == CONFLICT:
        return BAND_FALSE_POSITIVE if score >= t.merge_threshold else BAND_WEAK
    if score >= t.auto_clear:
        return BAND_EXACT if corr == AGREE else BAND_STRONG
    if score >= t.review_floor:
        return BAND_REVIEW
    return BAND_WEAK


def in_review_band(score: float, t: Thresholds) -> bool:
    """STRICTLY between auto-reject and auto-clear — §F6's 'below certainty'.

    Written as one function so the gate and the generator cannot disagree
    about what the band means. Both bounds are exclusive at the top and
    inclusive at the bottom, matching `band()` above.
    """
    return t.review_floor <= score < t.auto_clear


# --- Why there is no blocking function here ---------------------------------
#
# Real screening systems block candidate pairs before scoring, and an earlier
# draft of this module did too, on the longest folded token. Measured before
# keeping it: an EXHAUSTIVE pass of 210 persons against all 45,511
# `sanctions_name` rows is 9.6M comparisons in **4.2 minutes**, which this
# pipeline runs once per load.
#
# Blocking would have cost recall exactly where this product is tested. The
# longest token of `Al-Husseini` is `HUSSEINI` and of `Al-Husayni` is
# `HUSAYNI` — different blocks, so the pair would never have been compared,
# and §F5's transliteration cases would have been invisible to the screening
# leg while every count still looked right.
#
# An optimization that changes what can be FOUND is not an optimization.
