#!/usr/bin/env python3
"""Wave 19 Task 4 — regime text (Reg O, CRR, PRA) into document/passage records.

`large-exposure-rwa-concentration` §D's validation gates require "regime
anchoring — every limit must cite a provision", and a citation that cannot be
resolved back to filed text is worthless. This generator turns the 31 payloads
`sources/regimes/manifest.json` (Task 2) already fetched into exactly that:
one MongoDB `document` per fetched file and one `passage` per provision inside
it, each carrying `char_start`/`char_end` -- sorry, **`start_offset`/
`end_offset`**, see the note below -- into that document's own stored `text`.

**Field names deviate from the brief's literal interface list.** The brief
names `doc_id`, `char_start`, `char_end`. This estate's 37,389 pre-existing
passages, and `validators/partition.py`'s P3b orphan-anchor check
(`db.passage... {"document_id": {"$nin": ...}}`), all spell these
`document_id` / `start_offset` / `end_offset`. Wave 18 Task 11 hit this exact
fork before us -- see `validators/test_syndicate.py`'s comment above
`test_voting_threshold_passages_exist` -- and ruled that the brief's literal
names describe the retired `doc_id`/`start`/`end` alias pair
`loaders/load_mongo_wave17.py`'s docstring records removing, precisely
because two fields holding the same offset are two things that can drift.
Following the brief literally here would (a) reintroduce that alias pair and
(b) make every new passage invisible to P3b's `document_id` orphan check,
since it would have none. So this generator and its loader use the estate's
established names throughout; `regime`, `provision`, and `effective_date` are
new fields this task introduces and are spelled exactly as the brief asks.

**The offset invariant, and how HTML/XML structure makes it easy to keep.**
`document.text[start_offset:end_offset]` must equal `passage.text` --
literally, not after re-normalising either side. Rather than track offsets
into the *raw* HTML/XML (where tags, entities, and repealed-text markers
would make that arithmetic fragile) each per-document plain-text body is
*built up incrementally* as its provisions are parsed: every passage's text
is appended to the document buffer, its span recorded as exactly the slice
it just wrote, then a separator appended before the next one. The invariant
holds by construction -- there is no second extraction pass that could
diverge from the first.

**One passage per provision, at whatever granularity the source exposes:**

  * **Reg O** (eCFR XML) -- one passage per lettered/numbered paragraph inside
    each `<DIV8 TYPE="SECTION">`, e.g. `215.4(b)(2)`. A `<P>` with no leading
    enumerator (continuation prose) is folded into the still-open provision
    rather than starting a new one with a duplicate label. Four CFR nesting
    levels are tracked -- letter, digit, roman, capital, `(b)(1)(i)(A)` --
    with each token's level resolved by whether it continues the counting
    sequence already open at a reachable level (`classify_level`), never by
    the token's character class: "i"/"v"/"x" are both a fresh top-level
    letter AND a roman numeral one level down, and only sequence position
    (with an italic-heading tie-break for the one residual ambiguous case,
    see `opens_with_italic_heading`) tells them apart. A run of nesting
    deeper than 4 levels (rare, e.g. a digit list under `(d)(3)(i)`) folds
    into its nearest correctly-labelled ancestor rather than fabricating a
    5th-level label -- coarser in a few places, never wrong or duplicated.
  * **CRR** (legislation.gov.uk HTML) -- one passage per `id="article-N-..."`
    anchor legislation.gov.uk already assigns each numbered point, e.g.
    `id="article-395-1A-a"` -> `Article 395(1A)(a)`. An article with no such
    anchors at all (392, 393, 398, and 395's 2022-01-01 "omitted" version --
    all single-sentence or repealed-to-a-placeholder) falls back to one
    whole-article passage, `Article {N}`.
  * **PRA** (prarulebook.co.uk HTML) -- one passage per `<span
    class="rule-number">` value (`2.1`, `1.2`, ...), which the same markup
    shape serves for both the Large Exposures Part (`LE 2.1`) and the two
    supervisory statements (`SS16/13 1.2`, `SS3/25 4.1`). Chapter-heading
    rows (`rule-number--mega chapter-number`) are skipped -- they label a
    chapter, not a citable rule.

Effective dates: Reg O carries the single eCFR "as of" date the manifest
fetched (`2026-01-01`); each CRR file and each dated PRA Large Exposures
snapshot carries the point-in-time date baked into its own filename/URL; the
two PRA supervisory statements carry none (`null`) -- they are undated
guidance, not versioned snapshots, and inventing a date would misrepresent
the source. All three regimes' text is `public` -- fetched from a named
public source with a recorded retrieval date, carried onto every document
from `sources/regimes/manifest.json`.

Embeddings are deliberately NOT computed here -- see `loaders/embed_passages.py`.

Output: sources/regimes/passages.json  (offsets, no vectors)

Run: uv run generators/extract_regime_passages.py
"""

from __future__ import annotations

import hashlib
import html as html_lib
import json
import re
import sys
from html.parser import HTMLParser

from ccf.config import REPO_ROOT

REGIMES = REPO_ROOT / "sources" / "regimes"

MIN_CHARS = 20  # a one-sentence CRR article can be genuinely this short


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_manifest() -> dict[str, dict]:
    manifest = json.loads((REGIMES / "manifest.json").read_text())
    return {REPO_ROOT / f["path"]: f for f in manifest["fetches"]}


class DocumentBuilder:
    """Accumulates one document's plain-text body and its provisions'
    offsets together, so the offset invariant can never drift from the text.
    """

    def __init__(self) -> None:
        self._parts: list[str] = []
        self._len = 0
        self.provisions: list[dict] = []  # {provision, start, end}

    def add_provision(self, provision: str, text: str) -> None:
        text = text.strip()
        if len(text) < MIN_CHARS:
            return
        start = self._len
        self._parts.append(text)
        self._len += len(text)
        self.provisions.append({
            "provision": provision, "start_offset": start, "end_offset": self._len,
        })
        # Separator AFTER measuring end_offset -- it must never be inside a span.
        sep = "\n\n"
        self._parts.append(sep)
        self._len += len(sep)

    def text(self) -> str:
        return "".join(self._parts)


# ===========================================================================
# Reg O -- eCFR XML
# ===========================================================================

REG_O_SECTION = re.compile(
    r'<DIV8 N="(\d+\.\d+)" TYPE="SECTION"[^>]*>(.*?)</DIV8>', re.S)
REG_O_HEAD = re.compile(r"<HEAD>(.*?)</HEAD>", re.S)
REG_O_P = re.compile(r"<P>(.*?)</P>", re.S)
FTNT_BLOCK = re.compile(r"<FTNT>.*?</FTNT>", re.S)
SU_BLOCK = re.compile(r"<SU>.*?</SU>", re.S)
ANY_TAG = re.compile(r"<[^>]+>")

#: A run of one or more enumerators glued together at the very start of a
#: paragraph -- "(c)(1)" or "(4)(i)" -- consumed left to right.
LEADING_TOKEN = re.compile(r"^\(([A-Za-z0-9]{1,4})\)\s*")

#: The ONE other place a new subordinate marker legitimately opens: right
#: after the `<I>...</I>` heading phrase that follows a top-level letter --
#: e.g. "(a) <I>Terms and creditworthiness</I>\u2014(1) In general. ..." or
#: "(b) <I>Prior approval.</I> (1) No member bank...". Both punctuation
#: shapes (em-dash, or nothing but a space because the period sits inside
#: the italics) are eCFR's, and this matches on the ONE unambiguous anchor
#: common to both: the italic tag boundary itself, not the punctuation
#: after it. Applied to the RAW (untouched) paragraph markup, restricted to
#: its first 250 characters so a coincidental "(digit)" deep in the body,
#: long after some unrelated italicised term, is never mistaken for this.
EMBEDDED_AFTER_ITALIC = re.compile(r"</I>\s*\u2014?\s*\((\d{1,3})\)")

def strip_reg_o_markup(fragment: str) -> str:
    fragment = FTNT_BLOCK.sub(" ", fragment)
    fragment = SU_BLOCK.sub(" ", fragment)
    fragment = re.sub(r"<FTREF\s*/?>", " ", fragment)
    fragment = ANY_TAG.sub("", fragment)
    fragment = html_lib.unescape(fragment)
    return re.sub(r"\s+", " ", fragment).strip()


#: The roman-numeral counting sequence CFR sub-items actually use. Fixed
#: and finite -- eCFR paragraphs never nest 17 romans deep -- so indexing
#: into it also validates the token, not just its shape.
ROMAN_SEQUENCE = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
                  "xi", "xii", "xiii", "xiv", "xv", "xvi"]


def _next_letter(prev: str | None) -> str | None:
    if prev is None:
        return "a"
    if len(prev) == 1 and prev.isalpha() and prev.islower() and prev != "z":
        return chr(ord(prev) + 1)
    return None


def _next_digit(prev: str | None) -> str | None:
    if prev is None:
        return "1"
    return str(int(prev) + 1) if prev.isdigit() else None


def _next_roman(prev: str | None) -> str | None:
    if prev is None:
        return ROMAN_SEQUENCE[0]
    if prev in ROMAN_SEQUENCE:
        i = ROMAN_SEQUENCE.index(prev)
        return ROMAN_SEQUENCE[i + 1] if i + 1 < len(ROMAN_SEQUENCE) else None
    return None


def _next_capital(prev: str | None) -> str | None:
    if prev is None:
        return "A"
    if len(prev) == 1 and prev.isupper() and prev != "Z":
        return chr(ord(prev) + 1)
    return None


def classify_level(token: str, stack: list[str | None],
                    prefer_top_level: bool) -> int:
    """Which of the 4 CFR nesting levels (letter, digit, roman, capital --
    `(b)(1)(i)(A)`) this token opens, given the levels already open in
    `stack` (1-indexed: stack[0] is level 1, ...).

    A bare regex on the token's characters cannot tell a roman numeral from
    a letter -- "i", "v", "x" are both -- and depth alone is not enough
    either: a digit can stay open across an entire top-level letter's run
    (`(b)(1)`, then later `(c)` pops back to level 1 while `stack[1]` is
    still "1"), so "is a digit open" cannot mean "this letter must be
    roman". What actually disambiguates is SEQUENCE: does the token
    continue the counting sequence already open at some level ("c" after
    "b"; "ii" after "i"), checked at every reachable level rather than
    assumed from the token's shape. Only one shape is EVER truly ambiguous
    under this test -- a single roman-shaped letter ("i", "v", "x") that
    happens to also be the next letter in the alphabet AND the first roman
    numeral of a freshly-opened digit -- and CFR paragraphs raise it in
    reality (`215.2(h)` -> `215.2(i)`, where a digit from an EARLIER
    letter's own subitems, if any, could in principle still be open).
    `prefer_top_level` breaks that one case; see its caller for what earns
    it.
    """
    candidates = []
    if _next_letter(stack[0]) == token:
        candidates.append(1)
    if stack[0] is not None and token.isdigit() and _next_digit(stack[1]) == token:
        candidates.append(2)
    if stack[1] is not None and _next_roman(stack[2]) == token:
        candidates.append(3)
    if stack[2] is not None and _next_capital(stack[3]) == token:
        candidates.append(4)
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        return 1 if prefer_top_level else 3
    if stack == [None, None, None, None] and token.isdigit() and token == "1":
        # A section that numbers straight from the top, no letters at all.
        return 1
    return 0  # not a recognisable enumerator -- continuation prose


def leading_tokens(raw_paragraph: str, text: str) -> list[str]:
    """Every enumerator that OPENS this paragraph -- a contiguous run at
    the very start, plus at most one more embedded right after an italic
    heading. Only the head of the paragraph is ever examined; a defined
    term's own body text is never re-searched for something that looks
    like a marker."""
    tokens: list[str] = []
    rest = text
    m = LEADING_TOKEN.match(rest)
    while m:
        tokens.append(m.group(1))
        rest = rest[m.end():]
        m = LEADING_TOKEN.match(rest)
    embed_m = EMBEDDED_AFTER_ITALIC.search(raw_paragraph[:250])
    if embed_m:
        tokens.append(embed_m.group(1))
    return tokens


def opens_with_italic_heading(raw_paragraph: str) -> bool:
    """True when this <P>'s FIRST enumerator is immediately followed by an
    italicised heading/defined-term phrase -- `"(a) <I>Affiliate</I> means"`,
    `"(i) <I>Lending limit.</I> The lending limit..."`.

    Measured across the whole document: every genuine top-level lettered
    paragraph in Reg O opens this way; not one of the 32 roman-numeral
    sub-items (ii/iii/iv/v) does, and only 1 of 19 raw "(i)" occurrences
    does -- exactly the one that is the letter i, not the roman numeral.
    Used only to break the one shape `classify_level` cannot resolve by
    sequence alone.
    """
    stripped = raw_paragraph.lstrip()
    m = LEADING_TOKEN.match(stripped)
    if not m:
        return False
    return stripped[m.end():].startswith("<I>")


def extract_reg_o(path, manifest_entry: dict) -> tuple[dict, list[dict]]:
    raw = path.read_text(encoding="utf-8")
    builder = DocumentBuilder()

    for sec_m in REG_O_SECTION.finditer(raw):
        section = sec_m.group(1)
        block = sec_m.group(2)
        block_no_footnotes = FTNT_BLOCK.sub(" ", block)

        head_m = REG_O_HEAD.search(block_no_footnotes)
        heading = strip_reg_o_markup(head_m.group(1)) if head_m else ""

        # stack[i] is the token currently open at level i+1; a fresh
        # section starts with nothing open.
        stack: list[str | None] = [None, None, None, None]
        current_provision = section
        buf_parts: list[str] = [heading] if heading else []

        def flush() -> None:
            nonlocal buf_parts
            if buf_parts:
                builder.add_provision(current_provision, " ".join(buf_parts))
            buf_parts = []

        for p_m in REG_O_P.finditer(block_no_footnotes):
            raw_p = p_m.group(1)
            p_text = strip_reg_o_markup(raw_p)
            if not p_text:
                continue
            tokens = leading_tokens(raw_p, p_text)
            # Only the paragraph's OWN first enumerator can carry the
            # heading that disambiguates it -- computed once per paragraph,
            # not per token.
            prefer_top_level = opens_with_italic_heading(raw_p)
            levels = [(t, classify_level(t, stack, prefer_top_level)) for t in tokens]
            if not any(level for _, level in levels):
                # Either no enumerator-shaped token at all, or one that
                # LOOKS like an enumerator but does not continue any open
                # sequence (classify_level returned 0 for every candidate).
                # Either way this is continuation prose for the still-open
                # provision -- flushing here would close that provision and
                # immediately reopen an identically-labelled one, which is
                # exactly the duplicate-label defect this generator exists
                # not to produce.
                buf_parts.append(p_text)
                continue
            flush()
            for token, level in levels:
                if level == 0:
                    continue
                stack[level - 1] = token
                for i in range(level, 4):
                    stack[i] = None
            current_provision = section + "".join(
                f"({t})" for t in stack if t is not None)
            buf_parts.append(p_text)
        flush()

    title_m = re.search(r"<HEAD>(PART \d+.*?)</HEAD>", raw, re.S)
    title = strip_reg_o_markup(title_m.group(1)) if title_m else "12 CFR Part 215"

    document_id = path.stem  # "reg-o-12cfr215"
    text = builder.text()
    doc = {
        "document_id": document_id,
        "doc_type": "regime_text",
        "regime": "reg-o",
        "title": title,
        "citation": "12 CFR Part 215 (Regulation O)",
        "effective_date": "2026-01-01",  # eCFR "as of" date the manifest fetched
        "text": text,
        "text_length": len(text),
        "text_sha256": sha256(text),
        "provenance": "public",
        "source": manifest_entry["url"],
        "retrieved_at": manifest_entry["retrieved_at"],
        "source_sha256": manifest_entry["sha256"],
    }
    passages = [
        {**p, "regime": "reg-o", "effective_date": doc["effective_date"],
         "provenance": "public"}
        for p in builder.provisions
    ]
    return doc, passages


# ===========================================================================
# CRR -- legislation.gov.uk HTML, one file per article per point-in-time date
# ===========================================================================

CRR_FILENAME = re.compile(r"^crr-art-(\d+)-(\d{4}-\d{2}-\d{2})\.html$")
ARTICLE_ID = re.compile(r"^article-(\d+)-(.+)$")


class CrrArticleParser(HTMLParser):
    """Splits one article's HTML into (provision, text) pairs.

    Every numbered point legislation.gov.uk itself anchors with
    `id="article-N-<suffix>"` becomes its own provision boundary -- offsets
    are read off THIS anchor, never re-searched for matching text. Text
    inside the anchor span itself (the printed "1 ." / "(a)" label) is
    dropped rather than kept, so a passage's stored text is the provision's
    substance, not its own citation echoed back at the start of itself.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._buf_parts: list[str] = []
        self._buf_len = 0
        self._stopped = False
        self._in_h2 = False
        self._in_label = False
        self._label_depth = 0
        self._pending_id: str | None = None
        self.markers: list[tuple[int, str]] = []  # (offset, suffix)

    def _append(self, s: str) -> None:
        self._buf_parts.append(s)
        self._buf_len += len(s)

    def handle_starttag(self, tag, attrs) -> None:
        if self._stopped:
            return
        d = dict(attrs)
        tid = d.get("id") or ""
        m = ARTICLE_ID.match(tid)
        if not self._in_label and m:
            self._in_label = True
            self._label_depth = 1
            self._pending_id = m.group(2)
            return
        if self._in_label:
            if tag == "span":
                self._label_depth += 1
            return
        cls = (d.get("class") or "").split()
        if tag == "div" and "LegAnnotations" in cls:
            # Editorial/commentary boilerplate follows -- not operative text.
            self._stopped = True
            return
        if tag == "h2":
            self._in_h2 = True
        elif tag in ("p", "div", "li", "br"):
            self._append("\n")

    def handle_endtag(self, tag) -> None:
        if self._stopped:
            return
        if self._in_label:
            if tag == "span":
                self._label_depth -= 1
                if self._label_depth == 0:
                    self._in_label = False
                    self.markers.append((self._buf_len, self._pending_id))
                    self._pending_id = None
            return
        if tag == "h2":
            self._in_h2 = False

    def handle_data(self, data) -> None:
        if self._stopped or self._in_label or self._in_h2:
            return
        self._append(data)

    def text(self) -> str:
        return "".join(self._buf_parts)


def provision_label_from_suffix(article_num: str, suffix: str) -> str:
    parts = [p for p in suffix.split("-") if p]  # "5--a" -> ["5", "a"]
    return f"Article {article_num}(" + ")(".join(parts) + ")"


def extract_crr_file(path, manifest_entry: dict) -> tuple[dict, list[dict]]:
    m = CRR_FILENAME.match(path.name)
    if not m:
        raise ValueError(f"unrecognised CRR filename: {path.name}")
    article_num, effective_date = m.group(1), m.group(2)

    raw = path.read_text(encoding="utf-8", errors="ignore")
    parser = CrrArticleParser()
    parser.feed(raw)
    parser.close()
    body = parser.text()

    builder = DocumentBuilder()
    if parser.markers:
        bounds = [off for off, _ in parser.markers] + [len(body)]
        for i, (offset, suffix) in enumerate(parser.markers):
            span = body[offset:bounds[i + 1]]
            builder.add_provision(
                provision_label_from_suffix(article_num, suffix), span)
    else:
        # Single-sentence or repealed-to-a-placeholder article -- no
        # anchors at all. The whole body is still real point-in-time text.
        builder.add_provision(f"Article {article_num}", body)

    title_m = re.search(
        r'LegP1GroupTitle\w*"[^>]*>\s*(?:<span[^>]*>)?\s*'
        r'([^<]+?)\s*(?:</span>)?\s*</span>', raw)
    title = title_m.group(1).strip() if title_m else f"Article {article_num}"

    document_id = path.stem
    text = builder.text()
    doc = {
        "document_id": document_id,
        "doc_type": "regime_text",
        "regime": "crr",
        "title": f"CRR Article {article_num} — {title}",
        "citation": f"Regulation (EU) No 575/2013, Article {article_num}",
        "effective_date": effective_date,
        "text": text,
        "text_length": len(text),
        "text_sha256": sha256(text),
        "provenance": "public",
        "source": manifest_entry["url"],
        "retrieved_at": manifest_entry["retrieved_at"],
        "source_sha256": manifest_entry["sha256"],
    }
    passages = [
        {**p, "regime": "crr", "effective_date": effective_date,
         "provenance": "public"}
        for p in builder.provisions
    ]
    return doc, passages


# ===========================================================================
# PRA -- prarulebook.co.uk HTML (Large Exposures Part + 2 supervisory
# statements share the same rule-number / div-row__col-2 markup)
# ===========================================================================

PRA_LE_FILENAME = re.compile(r"^pra-large-exposures-(\d{2})-(\d{2})-(\d{4})\.html$")
PRA_SS_FILENAME = re.compile(r"^pra-ss(\d+)-(\d+)\.html$")


class PraRuleParser(HTMLParser):
    """Pairs each `rule-number` span with the `div-row__col-2` text that
    follows it in the same row. Chapter-heading rows
    (`rule-number--mega chapter-number`) are skipped: they label a chapter,
    not a citable rule, and letting one through would attach a bare
    chapter number ("1", "2") to whatever heading text follows it -- a
    false, un-resolvable citation.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rules: list[tuple[str, str]] = []
        self._in_number = False
        self._number_is_chapter = False
        self._number_buf: list[str] = []
        self._current_number: str | None = None
        self._in_col2 = False
        self._col2_depth = 0
        self._col2_buf: list[str] = []

    def handle_starttag(self, tag, attrs) -> None:
        d = dict(attrs)
        cls = (d.get("class") or "").split()
        if tag == "span" and "rule-number" in cls:
            self._in_number = True
            self._number_is_chapter = "chapter-number" in cls
            self._number_buf = []
            return
        if self._in_col2:
            if tag == "div":
                self._col2_depth += 1
            elif tag in ("p", "li", "br"):
                self._col2_buf.append("\n")
            return
        if tag == "div" and "div-row__col-2" in cls:
            self._in_col2 = True
            self._col2_depth = 1
            self._col2_buf = []

    def handle_endtag(self, tag) -> None:
        if tag == "span" and self._in_number:
            number = "".join(self._number_buf).strip()
            self._current_number = None if self._number_is_chapter else number
            self._in_number = False
            return
        if self._in_col2 and tag == "div":
            self._col2_depth -= 1
            if self._col2_depth == 0:
                self._in_col2 = False
                text = "".join(self._col2_buf)
                if self._current_number:
                    self.rules.append((self._current_number, text))
                self._current_number = None

    def handle_data(self, data) -> None:
        if self._in_number:
            self._number_buf.append(data)
        elif self._in_col2:
            self._col2_buf.append(data)


def extract_pra_file(path, manifest_entry: dict) -> tuple[dict, list[dict]]:
    m_le = PRA_LE_FILENAME.match(path.name)
    m_ss = PRA_SS_FILENAME.match(path.name)
    if m_le:
        dd, mm, yyyy = m_le.groups()
        effective_date = f"{yyyy}-{mm}-{dd}"
        label_prefix = "LE"
        title = "PRA Rulebook — Large Exposures Part"
        citation = f"PRA Rulebook, Large Exposures Part, as at {effective_date}"
    elif m_ss:
        ss_num, ss_year = m_ss.groups()
        effective_date = None  # undated guidance, not a versioned snapshot
        label_prefix = f"SS{ss_num}/{ss_year}"
        title = f"PRA Supervisory Statement SS{ss_num}/{ss_year} — Large Exposures"
        citation = f"PRA SS{ss_num}/{ss_year}"
    else:
        raise ValueError(f"unrecognised PRA filename: {path.name}")

    raw = path.read_text(encoding="utf-8", errors="ignore")
    parser = PraRuleParser()
    parser.feed(raw)
    parser.close()

    builder = DocumentBuilder()
    for number, text in parser.rules:
        builder.add_provision(f"{label_prefix} {number}", text)

    document_id = path.stem
    text = builder.text()
    doc = {
        "document_id": document_id,
        "doc_type": "regime_text",
        "regime": "pra",
        "title": title,
        "citation": citation,
        "effective_date": effective_date,
        "text": text,
        "text_length": len(text),
        "text_sha256": sha256(text),
        "provenance": "public",
        "source": manifest_entry["url"],
        "retrieved_at": manifest_entry["retrieved_at"],
        "source_sha256": manifest_entry["sha256"],
    }
    passages = [
        {**p, "regime": "pra", "effective_date": effective_date,
         "provenance": "public"}
        for p in builder.provisions
    ]
    return doc, passages


def main() -> int:
    manifest = load_manifest()
    print(f"Wave 19 Task 4 — extracting {len(manifest)} regime payloads\n")

    documents: list[dict] = []
    all_passages: list[dict] = []
    counts = {"reg-o": [0, 0], "crr": [0, 0], "pra": [0, 0]}  # [docs, passages]

    for path, entry in sorted(manifest.items()):
        name = path.name
        if name.startswith("reg-o-"):
            doc, passages = extract_reg_o(path, entry)
        elif name.startswith("crr-art-"):
            doc, passages = extract_crr_file(path, entry)
        elif name.startswith("pra-"):
            doc, passages = extract_pra_file(path, entry)
        else:
            print(f"  SKIP unrecognised: {name}")
            continue

        for p in passages:
            p["passage_id"] = None  # assigned below, once we know the doc id
            p["document_id"] = doc["document_id"]

        # Content-derived passage ids, following the estate convention
        # (`generators/extract_advisory_passages.py`): identical text always
        # earns the identical id, and a same-document collision is
        # disambiguated by a trailing suffix rather than by position.
        seen_hash: dict[str, int] = {}
        for p in passages:
            # `builder.provisions` carries only the offsets -- the text is
            # read back from the document body via those offsets, which IS
            # the offset invariant Task 15 checks, not a separate claim of it.
            body = doc["text"][p["start_offset"]:p["end_offset"]]
            h = sha256(body)[:12]
            n = seen_hash.get(h, 0)
            seen_hash[h] = n + 1
            pid = f"{doc['document_id']}#{h}" if n == 0 else f"{doc['document_id']}#{h}-{n + 1}"
            p["passage_id"] = pid
            p["text"] = body
            p["length"] = len(body)

        documents.append(doc)
        all_passages.extend(passages)
        counts[doc["regime"]][0] += 1
        counts[doc["regime"]][1] += len(passages)
        print(f"  {name:<40} regime={doc['regime']:<5} "
              f"{len(passages):>3} passages")

    print(f"\n  {len(documents)} documents, {len(all_passages)} passages total")
    for regime, (n_doc, n_pass) in counts.items():
        print(f"    {regime:<6} {n_doc:>3} documents  {n_pass:>4} passages")

    out = REGIMES / "passages.json"
    out.write_text(
        json.dumps(
            {
                "generated_for": "Wave 19 Task 4 — regime text passages",
                "note": "Offsets index into each document's own stored "
                        "`text` (assembled AS the provisions were parsed, "
                        "never re-extracted). Field names are the estate "
                        "convention (document_id/start_offset/end_offset), "
                        "not the brief's literal doc_id/char_start/char_end "
                        "-- see this generator's module docstring.",
                "document_count": len(documents),
                "passage_count": len(all_passages),
                "documents": documents,
                "passages": all_passages,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"\n  written: {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
