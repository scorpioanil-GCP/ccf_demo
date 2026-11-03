"""Name normalization shared by every component that compares person names.

## Why this is a module and not three private helpers

`kyc-refresh-beneficial-ownership` §F asks for a **genuine false-positive
pair** — two different people who fuzzy-match strongly — and the design's §5
requires the gate to prove it by running *the resolution scorer the product
actually uses*. If the sanctions loader normalized one way and the resolution
layer another, the gate would exercise a code path nothing else runs and the
false-positive claim would be about a scorer that does not exist.

So every caller normalizes here: the OFAC loader when it indexes
`sanctions_name.name_norm`, the person layer when it indexes variants, and the
resolver when it scores a candidate pair.

## The diacritic fold is a decision, not a detail

`normalize()` strips combining marks, so `Müller` and `Muller` collide, as do
`Mohammed` renderings that differ only by accent. Real screening systems do
this, and it is one of the mechanisms that *creates* the false positives §F
wants observable — folding is lossy on purpose. What it must NOT do is fold
across genuinely different letters (transliteration variants such as
`Yusuf`/`Youssef`/`Jusuf`), because those are the cases §F counts separately
and they have to remain distinguishable *before* the scorer decides they match.
"""

from __future__ import annotations

import re
import unicodedata

#: Punctuation OFAC and registry filings use inside names. Replaced with a
#: space rather than deleted: `SMITH-JONES` and `SMITH JONES` should collide,
#: but `O'BRIEN` must not become `OBRIEN` in one source and `O BRIEN` in
#: another — going through a space makes both land on the same token sequence.
_PUNCT = re.compile(r"[.,'’\-_/\\()\"]+")
_WS = re.compile(r"\s+")

#: Honorifics and corporate suffixes carry no identifying signal but shift
#: token overlap enough to change a similarity score. Removed only as whole
#: tokens, never as substrings — `DRIVER` must not lose its `DR`.
_NOISE_TOKENS = frozenset(
    {
        "MR", "MRS", "MS", "MISS", "DR", "PROF", "SIR", "LORD", "LADY",
        "HON", "REV", "JR", "SR", "II", "III", "IV",
    }
)


def strip_marks(text: str) -> str:
    """Decompose and drop combining marks: `Müller` -> `Muller`."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize(name: str) -> str:
    """Fold a name to its comparison form: marks stripped, upper, tokenized.

    Returns `""` for input that holds no alphanumeric content, so a caller can
    tell "nothing to match on" from "matched nothing".
    """
    folded = strip_marks(name).upper()
    folded = _PUNCT.sub(" ", folded)
    tokens = [t for t in _WS.split(folded) if t]
    kept = [t for t in tokens if t not in _NOISE_TOKENS]
    # An input that is ENTIRELY honorifics keeps its tokens rather than
    # normalizing to the empty string — dropping everything would make two
    # unrelated titles compare equal.
    return " ".join(kept or tokens)


def tokens(name: str) -> list[str]:
    """Normalized tokens, in source order. Order is kept deliberately.

    `SMITH, ROBERT JAMES` and `Robert James Smith` normalize to different
    token ORDERS but the same token SET. That difference is exactly the
    rendering variation §F asks the resolver to see through, so this function
    must not sort — the scorer decides whether order matters, not the
    normalizer.
    """
    n = normalize(name)
    return n.split(" ") if n else []
