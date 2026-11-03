#!/usr/bin/env python3
"""Extract tranche structure and trigger definitions from the 424B5 prospectuses.

    uv run generators/extract_prospectus.py            # extract and write
    uv run generators/extract_prospectus.py --verify   # re-check what was written

## Offsets must be taken against the SAME text that MongoDB stores

Wave 13a's narrative loader hit this: offsets computed against one
normalization and stored beside text under another point at the wrong
characters, and nothing downstream can tell. So this module writes the
normalized text's sha256 alongside the offsets, and the Mongo loader refuses
to store a document whose hash disagrees.

`normalize()` is the one canonical text. It is deliberately *faithful*: it
strips tags, unescapes entities and collapses whitespace, and does nothing
else. In particular it does NOT fold the non-breaking hyphen (U+2011) that
Toyota uses in "Class A‑1 Notes" -- folding it would change the stored text
away from what was filed. Every pattern in this module is instead written
hyphen-agnostic, and only the *derived* class names are canonicalised to an
ASCII hyphen.

## Three definition forms, not two

One issuer is not the format -- the third time this wave has learned it.
Across these three prospectuses a defined term is introduced in one of three
ways, and a pattern keyed on any one of them finds a fraction of the terms:

    Santander glossary:   " Delinquency Trigger " means, ..., 24.00%.
    Toyota, flat:         The "Delinquency Trigger Percentage" will equal 4.65%.
    Toyota, qualified:    The "Overcollateralization Target Amount" with respect
                          to any Payment Date is equal to approximately 0.85% ...

The third form puts a qualifying phrase between the quoted term and the
copula, and uses `is` / `will be` rather than `means`. `_DEFINITION` allows a
bounded, sentence-internal qualifier and a wider copula set -- but it stays
anchored on the *quoted defined term*, which is what keeps it honest. It will
not wander onto a nearby sentence that merely mentions the concept.

## Why the tranche roster comes from the cover table

Counting `Class X` mentions produces a phantom for Toyota. That prospectus
says, verbatim:

    "The Class A-2a Notes and the Class A-2b Notes are referred to in this
     prospectus collectively as the 'Class A-2 Notes.'"

Class A-2 is a *collective label*, not an instrument -- there is no Class A-2
note, no Class A-2 balance and no Class A-2 CUSIP. A mention count sees it 6
times and issues a seventh tranche, then chains A-2a beneath it. Two errors,
and the second is the one that cannot be undone: `subordinate_to` feeds Task
9's Fluree `isSubordinateTo` assertions, and Fluree is append-only.

So the roster is read from the cover-page note table -- the authoritative list
of instruments actually issued, which carries balance, rate and (Toyota) CUSIP
alongside. It is then cross-checked against the mention set minus the declared
collective labels; a disagreement raises rather than being resolved silently.

A-2a and A-2b are *siblings*: parallel classes at one seniority rank, both
senior to A-3. That grouping is read from the collective declaration itself,
not inferred from the naming -- see `find_collective_labels`.
"""
from __future__ import annotations

import argparse
import hashlib
import html as _html
import json
import re
import sys
from datetime import date
from decimal import Decimal

from ccf.config import REPO_ROOT

REGISTRY = REPO_ROOT / "sources" / "absee" / "deals.json"
OUT = REPO_ROOT / "sources" / "absee" / "prospectus_extract.json"

_TAGS = re.compile(r"<[^>]+>")
_WS = re.compile(r"[\s\xa0]+")

#: Hyphen-alikes seen in these filings: ASCII, U+2010, U+2011 (non-breaking,
#: Toyota's house style inside class names), U+2013.
_H = "[-‐‑–]"

_CLS = rf"A{_H}[0-9][ab]?|[B-E]"

#: A defined term, in any of the three forms described in the module docstring.
#: `qual` is bounded, may not cross a sentence end, and may not contain a quote
#: -- so the copula it finds belongs to this term's own sentence.
_DEFINITION = re.compile(
    r"[“\"]\s*(?P<name>[A-Z][A-Za-z ]{3,60}?)\s*[”\"]"
    r"(?P<qual>[^.“”\"]{0,120}?)"
    r"\s(?P<copula>means|will equal|will be|is)\b"
    r"(?P<body>.{0,600}?)\.\s",
    re.S)

#: `means` / `will equal` introduce a definition outright; `is` / `will be` can
#: also appear in a restatement elsewhere in the document. When a term is
#: matched by both, prefer the outright definitional form.
_COPULA_RANK = {"means": 0, "will equal": 0, "will be": 1, "is": 1}

#: The triggers this product needs, by the name the prospectus defines.
#: Toyota names the same concepts differently, and adds one Santander has no
#: equivalent for (its pool carries subvened low-APR receivables, so it needs a
#: yield supplement account). That asymmetry is a real structural difference
#: between a prime and a subprime deal and belongs in the extract, not hidden.
WANTED = {
    "delinquency trigger": ("delinquency", "percent_of_pool"),
    "delinquency trigger percentage": ("delinquency", "percent_of_pool"),
    "targeted overcollateralization amount": ("overcollateralization", "amount_or_percent"),
    "overcollateralization target amount": ("overcollateralization", "amount_or_percent"),
    "cumulative net loss": ("cumulative_net_loss", "percent_of_initial_pool"),
    "specified reserve account balance": ("reserve", "amount_or_percent"),
    "yield supplement overcollateralization amount": ("yield_supplement", "amount"),
}

#: Verified by the controller directly against each prospectus, 2026-08-23.
#: The extractor asserts against these rather than trusting a pattern to have
#: matched the right sentence.
#:
#: THE TRAP THIS GUARD EXISTS FOR: `24.00%` appears in the TOYOTA prospectus
#: too -- as the upper bound of the receivable-eligibility APR range
#: ("APR 0.00% to 24.00%"). A pattern that hunts for a percentage near the
#: words "Delinquency Trigger" in that document can land on an underwriting
#: criterion and bind it as a performance trigger. The data would be real and
#: the account of it wrong, and every proximity figure downstream would be
#: measured against a number that means nothing of the sort.
#:
#: This map is an ORACLE, never a source. The value written to the extract is
#: always the one parsed out of the filing.
EXPECTED_DELINQUENCY_TRIGGER = {
    "SDART-2022-6": Decimal("24.00"),
    "SDART-2024-1": Decimal("24.00"),
    "TAOT-2022-B": Decimal("4.65"),
}

_CLASS_MENTION = re.compile(rf"\b[Cc]lass\s+({_CLS})\b")

#: "... are referred to in this prospectus collectively as the "Class A-2 Notes.""
_COLLECTIVE = re.compile(
    r"collectively,?\s*(?:as)?(?:\s+the)?\s*"
    r"[“\"]\s*(?P<label>[^”\"]{0,60}?)\s*[”\"]")
_CLASS_LABEL = re.compile(rf"^[Cc]lass\s+({_CLS})\s+[Nn]otes\.?$")

#: The cover-page note table: the authoritative roster of issued instruments.
_TABLE_HEADER = re.compile(r"Initial Principal Amount\s+Interest Rate")
_TABLE_END = (r"\bTotal\b", r"Initial Public Offering Price")
_NOTE_ROW = re.compile(
    rf"Class\s*(?P<cls>{_CLS})\s+Notes\s*(?:\(\d\)\s*)*"
    rf"\$?\s*(?P<amount>\d[\d,]{{5,}})\s+"
    rf"(?P<rate>SOFR\s+Rate\s*\+\s*\d[\d.]*%|\d[\d.]*%)")
_CUSIP = re.compile(rf"Class\s*({_CLS})\s+Notes\s*:\s*([0-9A-Z]{{9}})\b")

#: What legitimately follows a definition's closing full stop: the next quoted
#: defined term, a capitalised word, or a bare page-number token before one.
#:
#: The bare `[A-Z]` branch is deliberately permissive and will also match a
#: mid-sentence abbreviation whose full stop is not a terminator -- "U.S. Bank
#: National Association" is the case to keep in mind, where the stop after "U"
#: is followed by "S". It fails safe in the other direction: over-matching ends
#: a definition EARLY, which the cross-check at the bottom of this module
#: catches by comparing extracted definitions against table mentions and
#: raising rather than emitting. Zero effect on the 10 anchors loaded today.
_NEXT_SENTENCE = re.compile(r"\s*(?:[“\"]|[A-Z]|\d+\s+[“\"A-Z])")

_FLOAT_RATE = re.compile(r"^\d[\d.]*%$")
_PCT = re.compile(r"(\d[\d,]*\.?\d*)\s*%")


def normalize(raw_html: str) -> str:
    """The one canonical text. Offsets mean nothing without it."""
    return _WS.sub(" ", _html.unescape(_TAGS.sub(" ", raw_html))).strip()


def _canon_class(name: str) -> str:
    """`Class A‑2b` (non-breaking hyphen) and `Class A-2b` are one class."""
    return re.sub(_H, "-", name)


def find_collective_labels(text: str) -> tuple[set[str], dict[str, set[str]]]:
    """Class names the prospectus declares to be *labels*, not instruments.

    Returns `(labels, groups)` where `labels` is the set of class names used
    only as a collective shorthand, and `groups` maps each such label to the
    real classes it stands for -- which are, by that declaration, parallel
    classes at one seniority rank.

    Only a collective label that is itself CLASS-SHAPED counts. The same
    sentence pattern also declares "Class A Notes", "Offered Notes" and
    "Notes"; those are not class names, and grouping A-1 through A-4 under
    "Class A" would flatten a real payment-priority ordering.
    """
    labels: set[str] = set()
    groups: dict[str, set[str]] = {}
    for m in _COLLECTIVE.finditer(text):
        shaped = _CLASS_LABEL.match(m.group("label"))
        if not shaped:
            continue
        label = _canon_class(shaped.group(1))
        labels.add(label)
        # The members are the classes named in this same sentence. Walk back
        # to the sentence start -- the previous declaration ends with `."` --
        # so a neighbouring declaration's members cannot leak in.
        seg = text[max(0, m.start() - 400):m.start()]
        seg = re.split(r"[”\"]", seg)[-1]
        seg = re.split(r"\.\s", seg)[-1]
        members = {_canon_class(x.group(1)) for x in _CLASS_MENTION.finditer(seg)}
        members.discard(label)
        if len(members) < 2:
            raise RuntimeError(
                f"collective label 'Class {label} Notes' declared at offset "
                f"{m.start()} but its member classes could not be read from "
                f"the declaring sentence: {seg!r}. Do not guess the members -- "
                f"a wrong sibling group becomes a wrong Fluree subordination "
                f"edge, and Fluree is append-only.")
        groups.setdefault(label, set()).update(members)
    return labels, groups


def find_tranches(text: str, deal_id: str) -> list[dict]:
    """The issued note classes, in seniority order, with sibling ties.

    Read from the cover-page note table rather than counted from mentions:
    a mention count cannot tell an instrument from a collective label, and
    'Class B' appearing 97 times is still one tranche either way.
    """
    hdr = _TABLE_HEADER.search(text)
    if hdr is None:
        raise RuntimeError(
            f"{deal_id}: no cover-page note table found. The tranche roster "
            f"must come from the table -- do not fall back to counting "
            f"mentions, which cannot distinguish a collective label.")
    window_end = len(text)
    for pat in _TABLE_END:
        m = re.search(pat, text[hdr.start():hdr.start() + 2500])
        if m:
            window_end = min(window_end, hdr.start() + m.start())
    window = text[hdr.start():window_end]

    cusips = {_canon_class(m.group(1)): m.group(2) for m in _CUSIP.finditer(text)}

    rows: list[dict] = []
    for m in _NOTE_ROW.finditer(window):
        cls = _canon_class(m.group("cls"))
        if any(r["class_name"] == cls for r in rows):
            continue
        rate = m.group("rate")
        fixed = bool(_FLOAT_RATE.match(rate))
        rows.append({
            "class_name": cls,
            "original_balance": m.group("amount").replace(",", ""),
            "interest_rate": rate.rstrip("%") if fixed else None,
            "interest_rate_text": rate,
            "interest_rate_basis": "fixed" if fixed else "floating",
            "cusip": cusips.get(cls),
        })

    labels, groups = find_collective_labels(text)
    mentioned = {_canon_class(m.group(1)) for m in _CLASS_MENTION.finditer(text)}
    from_table = {r["class_name"] for r in rows}
    expected = mentioned - labels
    if expected != from_table:
        raise RuntimeError(
            f"{deal_id}: the cover-page note table and the body of the "
            f"prospectus disagree about which classes exist. Table: "
            f"{sorted(from_table)}. Mentioned-but-not-in-table: "
            f"{sorted(expected - from_table)}. In-table-but-never-mentioned: "
            f"{sorted(from_table - expected)}. Declared collective labels: "
            f"{sorted(labels)}. Resolve this against the document -- do not "
            f"pick a side.")

    # Seniority: the table lists classes senior-first. Classes the prospectus
    # groups under one collective label are SIBLINGS -- one rank, not a chain.
    sibling_of: dict[str, str] = {}
    for label, members in groups.items():
        for member in members:
            sibling_of[member] = label

    ranks: list[list[dict]] = []
    rank_key_of_group: list[str] = []
    for row in rows:
        key = sibling_of.get(row["class_name"], row["class_name"])
        if rank_key_of_group and rank_key_of_group[-1] == key:
            ranks[-1].append(row)
        else:
            ranks.append([row])
            rank_key_of_group.append(key)

    # Siblings are grouped by adjacency in the table, which is how these
    # filings print them. If a collective group's members were ever split
    # across ranks, one of them would silently sit a notch too junior.
    rank_of = {r["class_name"]: i for i, g in enumerate(ranks) for r in g}
    for label, members in groups.items():
        seen = {rank_of[m] for m in members if m in rank_of}
        if len(seen) > 1:
            raise RuntimeError(
                f"{deal_id}: classes {sorted(members)} are declared collectively "
                f"as 'Class {label} Notes' but land at different seniority ranks "
                f"{sorted(seen)} because the note table does not list them "
                f"adjacently. They are siblings; ranking them in a chain would "
                f"write a subordination edge Fluree cannot retract.")

    tranches: list[dict] = []
    for rank, group in enumerate(ranks):
        senior = [f"{deal_id}-{r['class_name']}" for r in ranks[rank - 1]] if rank else []
        for row in group:
            tranches.append({
                "tranche_id": f"{deal_id}-{row['class_name']}",
                "class_name": row["class_name"],
                "cusip": row["cusip"],
                "original_balance": row["original_balance"],
                # NULL FOR A FLOATING-RATE CLASS. Toyota's A-2b pays
                # "SOFR Rate + 0.49%", which is not a number and must not be
                # made into one -- coercing it to 0.00% would record a
                # floating-rate note as zero-coupon, and nothing downstream
                # could tell. Task 8 loads this into Postgres: the column must
                # be nullable, and the basis is what to branch on.
                "interest_rate": row["interest_rate"],
                "interest_rate_text": row["interest_rate_text"],
                "interest_rate_basis": row["interest_rate_basis"],
                # A LIST, not a scalar: A-2a and A-2b are parallel, so Class
                # A-3 is subordinate to both. A scalar cannot say that, and
                # saying it wrong is unretractable once it reaches Fluree.
                "subordinate_to": senior,
                # Equal rank == equal seniority. Ties are the point.
                "seniority_rank": rank,
                "provenance": "public",
            })
    return tranches


def find_triggers(text: str, deal_id: str) -> list[dict]:
    """The defined thresholds this deal's performance is measured against.

    Every entry is a genuine quoted definition of the named concept in this
    document. `threshold_value` may be None -- a term defined by formula
    rather than by a fixed percentage is still a definition, and inventing a
    number for it would be the exact failure this task exists to avoid.

    `threshold_value` is the FIRST percentage stated in the definition, which
    for a single-number threshold is the threshold. Some definitions state a
    formula over several percentages -- Santander's Targeted
    Overcollateralization Amount is 22.80% of the current pool balance plus
    1.50% of the cut-off pool balance -- and for those the first number alone
    is not the answer. `threshold_all_percents` carries every percentage in
    the definition so a consumer can see that without having to re-parse the
    anchor, and the anchor itself remains the authority.
    """
    candidates: list[dict] = []
    for m in _DEFINITION.finditer(text):
        name = m.group("name").strip()
        kind_unit = WANTED.get(name.lower())
        if kind_unit is None:
            continue
        kind, unit = kind_unit
        body = m.group("body")
        percents = [str(Decimal(x.group(1).replace(",", "")))
                    for x in _PCT.finditer(body)]
        # Trim the sentence-terminating whitespace the pattern consumed, so
        # the anchor ends on the definition's own full stop.
        end = m.end()
        while end > m.start() and text[end - 1].isspace():
            end -= 1
        candidates.append({
            "trigger_id": f"{deal_id}-{kind}",
            "name": name,
            "kind": kind,
            "threshold_value": percents[0] if percents else None,
            "threshold_all_percents": percents,
            "threshold_unit": unit,
            "definition_text": text[m.start():end],
            "start_offset": m.start(),
            "end_offset": end,
            "copula": m.group("copula"),
            "provenance": "public",
        })

    # One entry per concept. Prefer an outright definitional copula over a
    # restatement, then the earliest occurrence.
    best: dict[str, dict] = {}
    for c in candidates:
        prior = best.get(c["trigger_id"])
        if prior is None or (
            (_COPULA_RANK[c["copula"]], c["start_offset"])
            < (_COPULA_RANK[prior["copula"]], prior["start_offset"])
        ):
            best[c["trigger_id"]] = c
    return sorted(best.values(), key=lambda t: t["start_offset"])


def verify_offsets(text: str, triggers: list[dict], deal_id: str) -> None:
    """Confirm each anchor actually brackets its own definition.

    Comparing `text[start:end]` against a `definition_text` that was itself
    cut from `text[start:end]` cannot fail -- it is the same read twice. So
    these checks are STRUCTURAL: the bracketed span must look like the
    definition of that named term, carrying that number, and be followed by
    the start of a new sentence. Shift an offset by one character and the
    trailing full stop moves out of the span; shift it by a sentence and the
    term name leaves it; cut it short and the text after it runs on mid-clause.
    """
    for t in triggers:
        span = text[t["start_offset"]:t["end_offset"]]
        if span != t["definition_text"]:
            raise RuntimeError(
                f"{deal_id} {t['name']}: offsets do not reproduce the stored "
                f"definition text. An anchor that points at the wrong "
                f"characters is worse than none -- it looks defensible.")
        if not span.startswith(("“", '"')):
            raise RuntimeError(
                f"{deal_id} {t['name']}: anchor does not open on the quoted "
                f"defined term; it starts {span[:40]!r}.")
        if not span.endswith("."):
            raise RuntimeError(
                f"{deal_id} {t['name']}: anchor does not close on the end of "
                f"the definition sentence; it ends {span[-40:]!r}.")
        if t["name"] not in span:
            raise RuntimeError(
                f"{deal_id} {t['name']}: anchor does not contain the term it "
                f"claims to define: {span[:120]!r}.")
        # A truncated anchor still opens on a quote, closes on a period and
        # names its term -- which is exactly the anchor that "looks
        # defensible" while pointing at the wrong characters. These two checks
        # are what catch it.
        #
        # Verbatim, with no trimmed fallback: "1.00".rstrip("0") is "1", and
        # "1" appears in almost any span, so the fallback made this check
        # nearly vacuous for round thresholds -- the very case where a
        # truncation that dropped the number would have slipped through. If a
        # future percentage is written with a thousands separator the stored
        # Decimal will not match the filed literal and this raises; that is
        # the right outcome for a shape nobody has looked at.
        if t["threshold_value"] is not None:
            if t["threshold_value"] not in span:
                raise RuntimeError(
                    f"{deal_id} {t['name']}: threshold {t['threshold_value']} "
                    f"does not appear inside its own anchor, so the anchor is "
                    f"not bracketing the sentence that states it: {span[:160]!r}.")
        # Truncation cannot be seen from inside the span -- a short anchor
        # still opens on a quote and closes on a period, and a COMPOSITE
        # threshold keeps its first number, so the value check above passes.
        # It is visible from what FOLLOWS: a definition's terminal period is
        # followed by a new sentence, whereas a stray period inside one is
        # followed by the rest of its own clause ("... and (ii) 1." then
        # "50% of the Pool Balance ...").
        if not _NEXT_SENTENCE.match(text[t["end_offset"]:t["end_offset"] + 40]):
            raise RuntimeError(
                f"{deal_id} {t['name']}: the text after this anchor continues "
                f"its own sentence rather than starting a new one -- the anchor "
                f"is cut short of the end of the definition. It runs on with "
                f"{text[t['end_offset']:t['end_offset'] + 60]!r}.")


def _last_inner_stop(text: str, t: dict) -> int | None:
    """The last full stop strictly inside the anchor, or None if it has none."""
    at = text.rfind(".", t["start_offset"], t["end_offset"] - 1)
    return at + 1 if at > t["start_offset"] else None


def _self_test_offsets(text: str, triggers: list[dict], deal_id: str) -> None:
    """Prove `verify_offsets` is not decoration.

    For every trigger, perturb the anchor three ways and require a rejection
    each time. A gate nobody has watched fail is a gate nobody knows works.
    """
    import copy
    for i, t in enumerate(triggers):
        for label, mutate in (
            ("shift +1", lambda x: (x["start_offset"] + 1, x["end_offset"] + 1)),
            ("shift -1", lambda x: (x["start_offset"] - 1, x["end_offset"] - 1)),
            ("next sentence", lambda x: (x["end_offset"] + 1, x["end_offset"] + 200)),
            # The failure mode the deliverable is defined by: a stray ". "
            # inside the definition yields a SHORTER anchor that still opens
            # on a quote, closes on a period and names its term.
            ("truncated", lambda x: (x["start_offset"], _last_inner_stop(text, x))),
        ):
            if mutate(triggers[i])[1] is None:
                continue  # no interior full stop in this span; nothing to cut at
            mutated = copy.deepcopy(triggers)
            s, e = mutate(mutated[i])
            mutated[i]["start_offset"], mutated[i]["end_offset"] = s, e
            mutated[i]["definition_text"] = text[s:e]
            try:
                verify_offsets(text, mutated, deal_id)
            except RuntimeError:
                continue
            raise RuntimeError(
                f"{deal_id} {t['name']}: verify_offsets ACCEPTED a '{label}' "
                f"corruption of the anchor. The check is decoration -- fix it "
                f"before trusting any offset in this file.")


def _load_deals() -> list[dict]:
    return json.loads(REGISTRY.read_text())["deals"]


def _text_for(deal: dict) -> str:
    path = REPO_ROOT / "sources" / "absee" / deal["slug"] / "prospectus.htm"
    return normalize(path.read_text(errors="replace"))


def extract() -> int:
    out = {"generated_at": date.today().isoformat(), "deals": []}

    for deal in _load_deals():
        deal_id = deal["deal_id"]
        text = _text_for(deal)
        tranches = find_tranches(text, deal_id)
        triggers = find_triggers(text, deal_id)

        if len(tranches) < 4:
            raise RuntimeError(
                f"{deal_id}: found {len(tranches)} tranches, floor is 4. "
                f"Fix the extractor -- do not lower the floor.")
        if len(triggers) < 3:
            raise RuntimeError(
                f"{deal_id}: found {len(triggers)} trigger definitions "
                f"{[t['name'] for t in triggers]}, floor is 3. Widen WANTED "
                f"with the names THIS deal uses, read out of the document -- "
                f"do not relax the pattern until something matches.")

        # Assert the delinquency threshold is the one this deal actually
        # states. See EXPECTED_DELINQUENCY_TRIGGER for why a pattern match is
        # not sufficient evidence on its own. The value written out is the
        # parsed one; this only refuses to write a wrong one.
        expected = EXPECTED_DELINQUENCY_TRIGGER[deal_id]
        got = next((Decimal(t["threshold_value"]) for t in triggers
                    if t["kind"] == "delinquency"
                    and t["threshold_value"] is not None), None)
        if got != expected:
            raise RuntimeError(
                f"{deal_id}: delinquency trigger extracted as {got}, "
                f"expected {expected}. Do NOT relax the pattern to make this "
                f"pass -- read the prospectus sentence the extractor matched. "
                f"In the Toyota document 24.00% is an APR eligibility bound, "
                f"not a trigger.")

        verify_offsets(text, triggers, deal_id)
        _self_test_offsets(text, triggers, deal_id)

        out["deals"].append({
            "deal_id": deal_id,
            "legal_name": deal["legal_name"],
            "prospectus_accession": deal["prospectus"][0],
            "prospectus_file": deal["prospectus"][1],
            "prospectus_filed": deal["prospectus_filed"],
            "source_url": deal["prospectus_url"],
            "provenance": "public",
            "text_length": len(text),
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "tranches": tranches,
            "triggers": triggers,
        })
        print(f"  {deal_id:14s} {len(tranches)} tranches, "
              f"{len(triggers)} triggers, delinquency={got}%")
        ranks: dict[int, list[str]] = {}
        for tr in tranches:
            ranks.setdefault(tr["seniority_rank"], []).append(tr["class_name"])
        print("      seniority: " + " > ".join(
            "/".join(ranks[r]) for r in sorted(ranks)))
        for t in triggers:
            print(f"      {t['kind']:22s} {str(t['threshold_value']):>7s}  "
                  f"@{t['start_offset']}-{t['end_offset']}  {t['name']}")

    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\n  -> {OUT}")
    return 0


def verify() -> int:
    """Re-derive the text from source and re-check what was written.

    Independent of the extraction run: it reads the JSON back off disk and
    re-normalizes the HTML, so a hash or offset that only held in memory
    fails here.
    """
    written = json.loads(OUT.read_text())
    by_id = {d["deal_id"]: d for d in written["deals"]}
    for deal in _load_deals():
        deal_id = deal["deal_id"]
        rec = by_id[deal_id]
        text = _text_for(deal)
        digest = hashlib.sha256(text.encode()).hexdigest()
        if digest != rec["text_sha256"] or len(text) != rec["text_length"]:
            raise RuntimeError(
                f"{deal_id}: re-derived text does not match the recorded hash. "
                f"Every offset in this file is meaningless until it does.")
        verify_offsets(text, rec["triggers"], deal_id)
        _self_test_offsets(text, rec["triggers"], deal_id)
        expected = EXPECTED_DELINQUENCY_TRIGGER[deal_id]
        got = next((Decimal(t["threshold_value"]) for t in rec["triggers"]
                    if t["kind"] == "delinquency"
                    and t["threshold_value"] is not None), None)
        if got != expected:
            raise RuntimeError(f"{deal_id}: delinquency {got} != {expected}")
        print(f"  {deal_id:14s} sha256 ok, {len(rec['triggers'])} anchors "
              f"bracket their definitions, {len(rec['tranches'])} tranches, "
              f"delinquency={got}%")
    print("\n  verified")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verify", action="store_true",
                    help="re-check the written extract against the sources")
    args = ap.parse_args()
    return verify() if args.verify else extract()


if __name__ == "__main__":
    sys.exit(main())
