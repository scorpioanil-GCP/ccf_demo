#!/usr/bin/env python3
"""Person identity: keys, filed-name parsing, normalization, match banding.

§C calls person identity "the hard join": DEF 14A gives names, Form 4 gives a
CIK per reporting person, and the CRM keys on an internal id. The crosswalk is
imperfect ON PURPOSE, per CLAUDE.md rule 5.

`match_band` is where that rule is enforced. A near-unity name score with
DIFFERING CIKs is not a match — it is a false positive, and the estate must say
so. The 2026-08-18 Form 4 probe found a real one at Genesis Energy: `Davison
James E` (CIK 1403411) and `Davison James E. Jr.` (CIK 1403412), two different
people. Because it is real, it is labelled `public`, not engineered.
"""

from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher

#: Generational and honorific suffixes, stripped before comparison so that
#: "Davison James E" and "Davison James E. Jr." collide as the rule intends.
_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v", "md", "phd", "esq"}


def person_key(cik: str | None, name: str) -> str:
    """Zero-padded CIK where one exists, else a deterministic minted key."""
    if cik:
        return f"{int(cik):010d}"
    digest = hashlib.sha256(normalize_name(name).encode("utf-8")).hexdigest()
    return f"syn-p-{digest[:6]}"


def parse_filed_name(name: str) -> dict:
    """Split an EDGAR filed name, which is rendered `Last First Middle Suffix`."""
    tokens = [t for t in re.sub(r",", " ", name).split() if t]
    suffix = ""
    if tokens and tokens[-1].rstrip(".").lower() in _SUFFIXES:
        suffix = tokens.pop()
    last = tokens[0] if tokens else ""
    first = tokens[1] if len(tokens) > 1 else ""
    middle = " ".join(tokens[2:]) if len(tokens) > 2 else ""
    return {"last": last, "first": first, "middle": middle, "suffix": suffix}


def normalize_name(name: str) -> str:
    """Order-insensitive, case-insensitive, punctuation-free comparison form."""
    cleaned = re.sub(r"[^a-z0-9 ]", " ", name.lower())
    tokens = [t for t in cleaned.split() if t and t not in _SUFFIXES]
    return " ".join(sorted(tokens))


def render_display(parsed: dict) -> str:
    """`First Middle Last Suffix` — the human rendering, not the filed one."""
    parts = [parsed["first"], parsed["middle"], parsed["last"], parsed["suffix"]]
    return " ".join(p for p in parts if p)


def match_score(a: str, b: str) -> float:
    """Similarity of two names under `normalize_name`."""
    return SequenceMatcher(None, normalize_name(a), normalize_name(b)).ratio()


def match_band(score: float, same_cik: bool | None) -> str:
    """Band a candidate pair. CIK evidence outranks name similarity.

    A high score with DIFFERING CIKs is a false positive, not a match. This is
    the whole point of rule 5 — a resolver that scores names and stops is the
    failure the dataset exists to make visible.
    """
    if same_cik is False:
        return "false_positive" if score >= 0.90 else "weak"
    if same_cik is True:
        return "exact"
    return "strong" if score >= 0.90 else "weak"
