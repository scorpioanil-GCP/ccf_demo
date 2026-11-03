#!/usr/bin/env python3
"""Wave 18 Task 2 — per-lender commitment shares from filed schedules.

Wave 4 parsed the FACILITY (one total commitment per row). This parses the
SCHEDULE BENEATH IT: who holds what share. §C assigns "syndicate
composition — lender names and commitments" to Fluree as `R`, so these
figures become `participatesIn` edge attributes and live in no Postgres
column — see docs/wave18-design.md §5.

Structure, not layout. A filed commitment schedule is an HTML <table> that
TextExtractor flattens to text while inserting " | " at every <td>/<th>
(see generators.extract_facilities.TextExtractor.handle_starttag). That
pipe marker is reliable: every cell boundary carries one, regardless of
how the filer laid the table out. What is NOT reliable is using
TextExtractor's "\\n" to tell a ROW boundary (a new <tr>) apart from a mere
CELL boundary within one row -- real EDGAR HTML is hand-indented, so a
literal newline sits between `</td>` and the next `<td>` for
readability *whether or not* a new `<tr>` started there, and
TextExtractor's handle_data() faithfully passes that whitespace-only text
node through like any other data. (An earlier version of this parser
split on `\\n(?=[ \\t]*\\|)`, assuming only `<tr>` produced that shape;
against three of the six real filings it fragmented every row into one
"row" per cell and found nothing.) So this file never tries to find row
boundaries. Instead, every PIPE-PRECEDED "$" is treated as one row's
amount anchor -- prose dollar mentions are never preceded by a "|", only
a table cell's own money figure is -- and the row's name is found by
walking BACKWARD from that anchor through the window since the previous
such anchor (or this schedule's own caption, whichever is closer),
skipping cells that are junk (a checkbox, a reference number) or a bare
tax-jurisdiction value, and stopping at the first cell that looks like an
institution. That correctly lands on the name even when a filer puts six
extra columns between it and the dollar sign, AND stops before ever
reaching the schedule's own column-header row on a table's first data
row (where there is no previous row to bound the window) -- see
`_nearest_name_cell` and docs/known-issues.md, "one issuer is not the
format".

Three more real-filing artifacts this file has to name, not paper over:

  REDLINED SCHEDULES. Three of the six agreements (`ahr-ex10_1.htm`,
  `payx-ex10_1.htm`, `d133770dex101.htm` -- Sabre Corp) are amendments
  filed as tracked-changes exhibits: the struck-through OLD dollar figure
  and the underlined NEW one share one HTML run with no separator, so
  TextExtractor renders them concatenated -- "$95,000,000145,000,000" is
  $95,000,000 struck through immediately followed by $145,000,000
  underlined, not one $95-quadrillion figure. `_split_money_run` recovers
  the individual figures and this file keeps the LAST one: the schedule
  states the facility's condition AFTER the amendment, and that is the
  current commitment. Splitting is not always as simple as "take the
  conventional 2 decimal digits for the first figure": Sabre's Schedule I
  glues "2,255,617.21,184,199.01", where a naive 2-decimal read of the
  first figure leaves a remainder ("...,184,199.01") that starts with a
  comma -- no number can begin with one -- so a naive parse silently
  reported NO second figure and this file used the stale pre-amendment
  $2,255,617.21 (asserted nowhere in the filing) instead of the real,
  current $1,184,199.01. `_split_money_run` retries with fewer decimal
  digits until the remainder is itself a well-formed money figure (see its
  docstring). One Sabre row ("50,525,825.24657,888.35") respects NEITHER a
  1- nor a 2-decimal-digit split under this dataset's comma-grouping
  rules -- `parse_schedule` drops that single row with a printed warning
  rather than guess a number for it or crash the rest of the document.
  One row in `payx-ex10_1.htm` glues an OLD LENDER NAME to its NEW
  replacement across an assignment ("CITIZENS BANK,
  N.A.KEYBANK NATIONAL ASSOCIATION" is Citizens being replaced by
  KeyBank); `_split_concatenated_name` applies the same last-wins rule
  there, on the same evidence (a lowercase/period character directly
  abutting a run of capitals -- the shape a struck-out ALL-CAPS name
  gains when its underlined replacement is glued on with no space).
  KNOWN LIMITATION, left unfixed rather than guessed at: one row in
  `ahr-ex10_1.htm` redlines at WORD granularity instead of swapping the
  whole name -- "Barclays"(struck)+"Fifth Third "(new)+"Bank "(unchanged,
  shared by both names)+"PLC"(struck)+", National Association"(new)
  renders as "BarclaysFifth Third Bank PLC, National Association". The
  replacement text here is mixed-case ("Fifth"), not the all-caps run
  NAME_SPLICE looks for, and correctly reconstructing "Fifth Third Bank,
  National Association" from an interleaved word-level diff needs the
  strikethrough/underline CSS TextExtractor deliberately doesn't parse.
  That single row is left exactly as filed-and-flattened rather than
  patched with a narrower heuristic that risks corrupting a legitimate
  name elsewhere -- see docs/known-issues.md and this file's own test
  suite for the acceptance bar a fix would have to clear. Flagged to
  Task 3 (name resolution) for manual review, not automatic matching.

  SUB-LIMIT TABLES ARE NOT THE COMMITMENT SCHEDULE. Some agreements also
  carry a "Letter of Credit Commitments" or "Issuing Bank Individual
  Sublimit" table: a *subset* of lenders' L/C-issuing capacity, drawn from
  their revolving commitment rather than additive to it. Counting those
  rows as syndicate shares would double-count institutions who appear in
  both tables and would corrupt the sum-of-shares check downstream (Task
  16). `_schedule_captions`/`_included` recognise these blocks (by their
  own "Schedule N" caption where they have one, and by a bare sub-heading
  such as "Letter of Credit Commitments" where they don't) and
  `parse_schedule` skips every anchor inside one. RULING T2-R1: the
  brief's original document selection matched this wrong -- Super Micro
  (`d45696dex101.htm`, would-be `FAC-517638`) and Vertiv
  (`d105148dex101.htm`, would-be `FAC-BEDC52`) were selected by a scan
  that matches an institution name within 90 characters of a money
  figure, which cannot tell a commitment schedule from a sub-limit table.
  Vertiv's table is literally headed "Issuing Bank | Issuing Bank
  Individual Sublimit" (and separately references a "Schedule 2.01
  Commitments" whose content is not in the exhibit at all); Super Micro's
  is "each of (a) JPMorgan Chase Bank, N.A., with respect to up to
  $25,436,410.00 of Letters of Credit, (b) BNP Paribas, ..." -- L/C
  issuing capacity per bank, not a lending commitment. Both are REMOVED
  from `AGREEMENTS` entirely, not "not covered" -- they were mis-selected,
  not incompletely parsed, and their facility IDs are not part of this
  product's six agreements. Regis Corp (`d761586dex101.htm`) and Sabre
  Corp (`d133770dex101.htm`) replace them. Do not re-add the originals
  from the same flawed name-proximity scan.

Each row carries an {"offset", "end"} span pair, not an offset sized to
len(lender_raw). `lender_raw` is whitespace-NORMALISED but the raw span in
`text` can contain an embedded newline (a wrapped <p> inside a cell), so
the contract is the checkable invariant
`" ".join(text[offset:end].split()) == lender_raw`, always -- see
test_offset_end_span_survives_an_embedded_newline in
validators/test_commitment_schedules.py. Task 1 hit this exact bug on the
same kind of field ("BANK OF AMERICA,\\nN.A." in a real filing) with an
offset-only contract that a single-spaced test fixture could not catch.
"""
from __future__ import annotations

import json
import re
from datetime import timezone, datetime

from ccf.config import REPO_ROOT

SCREEN = REPO_ROOT / "sources" / "screening"
EX10 = REPO_ROOT / "sources" / "ex10"

#: The six selected agreements and the facilities they carry.
AGREEMENTS = [
    ("1046102_0001104659-25-031884_tm2511351d1_ex10-1.htm",
     ["FAC-6F4065", "FAC-A4A5EE"]),
    ("885590_0001193125-25-149731_d949183dex101.htm",
     ["FAC-E08688", "FAC-105FC5", "FAC-08F1D1", "FAC-DFCB72"]),
    ("1632970_0001193125-26-145647_ahr-ex10_1.htm",
     ["FAC-405B7A", "FAC-2A2C38"]),
    ("723531_0001193125-26-021794_payx-ex10_1.htm", ["FAC-E386A4"]),
    # Replacements for the original brief's Super Micro
    # (1375365.../d45696dex101.htm, FAC-517638) and Vertiv
    # (1674101.../d105148dex101.htm, FAC-BEDC52) picks -- ruling T2-R1.
    # Both were REMOVED, not left as "not covered": the brief's selection
    # scan matched an institution name within 90 characters of a money
    # figure, which cannot tell a syndicate commitment schedule apart from
    # an L/C issuing-bank SUB-LIMIT table. Super Micro's apparent schedule
    # is "each of (a) JPMorgan Chase Bank, N.A., with respect to up to
    # $25,436,410.00 of Letters of Credit, (b) BNP Paribas, ..." -- L/C
    # issuing capacity per bank, not a lending commitment. Vertiv's is
    # literally headed "Issuing Bank | Issuing Bank Individual Sublimit";
    # it separately references a "Schedule 2.01 Commitments" whose content
    # is not in the exhibit at all. Their facility_ids are not part of
    # this product's six agreements -- do not re-add them from the same
    # flawed scan.
    ("716643_0001193125-24-281618_d761586dex101.htm",
     ["FAC-E4D2F8", "FAC-25F991", "FAC-01BB3F", "FAC-5F29AF"]),
    ("1597033_0001193125-26-340356_d133770dex101.htm", ["FAC-3DF1D5"]),
]

# --------------------------------------------------------------------------
# Amount anchors: a "$" that sits in its own table cell (or is glued to a
# redlined figure), never a dollar amount mentioned in running prose.
# --------------------------------------------------------------------------

#: A well-formed dollar figure, optionally with cents.
_MONEY = r"\d{1,3}(?:,\d{3}){2,}(?:\.\d{1,2})?"

#: The "|" that always precedes a table cell's own "$" (see module
#: docstring). Prose ("in an amount of $2,000,000,000") never has a pipe
#: there, so this is what keeps the scan out of ordinary paragraphs.
#: Captures the FULL digit/comma/decimal blob right after the dollar sign
#: as ONE group -- it is decomposed into one or two money figures by
#: _split_money_run below, not here, because getting the split point
#: right sometimes needs amt1's decimal-digit count to differ from its
#: own greedy reading (see _split_money_run).
MONEY_ANCHOR = re.compile(r"\|[\s]*\$[\s|]*(?P<run>[\d,.]+)")

#: How far back from an anchor to look for the row's name if there is no
#: closer anchor to bound the search -- generous, because the cell walk
#: itself (not the window size) is what finds the right boundary.
WINDOW_CHARS = 600

#: `_split_money_run` decomposes MONEY_ANCHOR's captured `run` into one
#: or two money figures. The trailing `$` anchor is load-bearing: it is
#: what makes Python's backtracking retry amt1 with FEWER decimal digits
#: when its own greedy 2-decimal reading leaves a remainder that cannot
#: start a second number. Matched with `.match()` against the whole
#: `run` string (not the document), so `$` means end-of-run, not
#: end-of-document.
_MONEY_PAIR = re.compile(r"(?P<amt1>" + _MONEY + r")(?P<amt2>" + _MONEY + r")?$")


def _split_money_run(run: str) -> tuple[str, str | None]:
    """(amt1, amt2_or_None) for one MONEY_ANCHOR "run" capture -- either a
    single money figure, or two concatenated by a redline with no
    separator (see module docstring, "REDLINED SCHEDULES"). A naive
    left-to-right match of "amt1 then optional amt2" gets this WRONG for
    a real row: Sabre Corp's Schedule I glues an old figure to its
    replacement as "2,255,617.21,184,199.01". Taking amt1's conventional
    2 decimal digits ("...617.21") is individually valid, but leaves a
    remainder ("...,184,199.01") that starts with a comma -- which can
    begin no number -- so amt2 silently came back None, and this file
    used the STALE $2,255,617.21 (an amount that isn't even asserted
    anywhere in the filing) instead of the actual, filed, post-amendment
    $1,184,199.01. The correct split is "2,255,617.2" + "1,184,199.01"
    -- amt1 with only ONE decimal digit. Anchoring `_MONEY_PAIR` to the
    end of `run` (`$`) forces Python's regex engine to backtrack amt1's
    own greedy decimal-digit choice when the naive 2-digit reading
    prevents amt2 from consuming the rest of `run`; confirmed against
    both real shapes in this corpus: this Sabre row (which needs the
    backtrack) and ahr-ex10_1.htm's "60,471,879.4415,734,646.43" (whose
    naive 2-decimal reading already works and must NOT be perturbed)."""
    m = _MONEY_PAIR.match(run)
    if m is None or m.end() != len(run):
        # MONEY_ANCHOR only ever captures a run built entirely from
        # digits/commas/dots, and one or two MONEY-shaped figures always
        # accounts for every real run seen in the six filings -- this
        # would mean a THIRD figure got glued on, or some other shape
        # this file has never encountered. Fail loudly rather than
        # silently return a truncated or wrong amount.
        raise ValueError(f"could not decompose money run {run!r}")
    return m.group("amt1"), m.group("amt2")


def _amount_of(m: re.Match) -> int:
    """Cents-exact dollars for one MONEY_ANCHOR match. Two concatenated
    figures (a redline) resolve to the LAST (post-amendment) one."""
    amt1, amt2 = _split_money_run(m.group("run"))
    raw = amt2 or amt1
    return int(float(raw.replace(",", "")))


# --------------------------------------------------------------------------
# Name extraction
# --------------------------------------------------------------------------

#: A trailing role note or placeholder ("(as Additional ... Lender)",
#: "[on file with the Administrative Agent]") that names no institution
#: and must be cut from the raw span, not just from the normalised string
#: -- otherwise offset/end stop bounding lender_raw exactly.
PAREN_OR_BRACKET_SUFFIX = re.compile(r"\s*[\(\[].*$", re.DOTALL)

#: Lines that are sums, placeholders or headings — never syndicate members.
#: Checked as a PREFIX (a heading that opens with a generic word, e.g.
#: "Schedule I") and separately as a SUFFIX (a column heading that closes
#: with the generic word instead, e.g. "2025 REFINANCING TERM LOAN
#: LENDERS" or "THIRD AMENDMENT REVOLVING CREDIT COMMITMENTS" -- the
#: filer-specific words at the front are exactly why a prefix check alone
#: cannot catch these; no real institution name ends this way).
NOT_A_LENDER = re.compile(
    r"^(?:TOTAL|AGGREGATE|SUB-?TOTAL|Cashless|Schedule|Annex|Exhibit|"
    r"Commitment|Commitments|Lender|Lenders|Revolving|Term|L/?C|Issuing|"
    r"Select\s+One)\b", re.IGNORECASE)
NOT_A_LENDER_SUFFIX = re.compile(
    r"(?:Lenders?|Commitments?|Percentage)\s*$", re.IGNORECASE)

#: A cell that carries no name at all: empty, a bare currency sign, a
#: checkbox marker ("1. ¨", "3. x"), a percentage or bare number (a
#: neighbouring row's trailing tail), or a reference code with no
#: lowercase letters and no spaces (a treaty-passport number like
#: "13/B/7418/DTTP"). Everything this doesn't reject is a name candidate.
#: The reference-code alternative REQUIRES at least one digit -- without
#: that, it also matched a bare all-caps ENGLISH WORD like "TOTAL" (every
#: character of which happens to satisfy [A-Z0-9]), silently treating a
#: sum line as junk to skip past rather than a substantive cell for
#: _name_from_cell to reject. That distinction matters beyond just
#: excluding TOTAL correctly: parse_schedule's same-row-continuation reuse
#: (SAME_ROW_GAP_CHARS) trusts "no candidate cell was even rejected" to
#: mean "this row has no name of its own, e.g. a second dollar column" --
#: and a TOTAL line silently swallowed as junk satisfies that condition,
#: so its own dollar figure got attributed to the last real lender
#: instead of dropped. Confirmed against real filings: exactly this
#: happened for JPMorgan Chase Bank, N.A. and Goldman Sachs Lending
#: Partners in d949183dex101.htm before this fix.
JUNK_CELL = re.compile(
    r"^(?:\$?|\d\.\s*\S{0,3}|[\d.,%\s]+|[A-Z0-9]*\d[A-Z0-9/.\-]*)$")

#: A struck-through name immediately abutted by its underlined replacement
#: with no separating space -- the redline artifact TextExtractor produces
#: when an assignment/novation replaces one lender with another in the
#: SAME table cell (see module docstring). The boundary is a lowercase
#: letter or a period (the end of an abbreviation like "N.A.") directly
#: followed by two or more capital letters -- the shape a glued full-caps
#: replacement name takes, and a shape no legitimate name in the six
#: filings' lender lists produces (e.g. "JPMorgan" has no such transition;
#: "HSBC" is capitals-then-capitals, never lower/period-then-capitals).
NAME_SPLICE = re.compile(r"(?<=[a-z.])(?=[A-Z]{2,})")


def _split_concatenated_name(name: str) -> str:
    """If `name` is two names glued by a redline (see NAME_SPLICE), keep
    the LAST one -- the post-amendment lender. Otherwise return `name`."""
    parts = NAME_SPLICE.split(name)
    return parts[-1].strip(" ,") if len(parts) > 1 else name


def _cell_spans(base: int, window_text: str) -> list[tuple[int, int, str]]:
    """(start, end, raw_text) for every '|'-delimited cell in a window,
    offsets absolute into the original document (`base` is the window's
    own absolute start)."""
    spans = []
    pos = 0
    for m in re.finditer(r"\|", window_text):
        spans.append((base + pos, base + m.start(), window_text[pos:m.start()]))
        pos = m.end()
    spans.append((base + pos, base + len(window_text), window_text[pos:]))
    return spans


#: Jurisdiction-column values are always exactly one sovereign/territory
#: name, drawn from a small closed set -- and no institution in any of
#: the six filings' lender lists is ITSELF just a country name. That
#: makes an exact-match stoplist a safe way to skip a tax-jurisdiction
#: column (real text: "Bank of America, N.A. | United States | ...",
#: "Royal Bank of Canada | Canada | ...") without also matching part of
#: an institution's own name that happens to end in a place name (e.g.
#: "Royal Bank of Canada" itself, or "MUFG Bank, Ltd., Canada Branch").
JURISDICTION_WORDS = frozenset({
    "united states", "united states1", "canada", "japan", "australia",
    "united kingdom", "ireland", "cayman islands", "germany", "france",
    "switzerland", "netherlands", "luxembourg", "bermuda", "hong kong",
    "singapore", "china", "brazil", "mexico", "italy", "spain", "belgium",
    "austria", "sweden", "denmark", "norway", "finland", "south korea",
    "india", "cayman", "jersey", "guernsey", "bahamas",
})


def _nearest_name_cell(
        window_start: int, window_text: str,
) -> tuple[tuple[str, int, int] | None, bool]:
    """((lender_raw, offset, end) or None, rejected) for the cell NEAREST
    the amount (i.e. last in the window) that looks like an institution
    name. A lender's own row can carry several columns after its name
    before the dollar figure (tax jurisdiction, UK-lender checkboxes, a
    treaty passport reference number, all observed in real schedules) --
    walking BACKWARD from the amount and skipping cells that are junk
    (JUNK_CELL) or a bare jurisdiction (JURISDICTION_WORDS) reaches the
    name without ever needing to walk far enough to reach the PREVIOUS
    row, or -- for a table's first data row, where there is no previous
    row to bound the window -- the schedule's own column-header cells
    ("Tax Jurisdiction", "Treaty Passport Scheme Reference Number") that a
    forward scan from window_start would hit first. Real filings hit both
    failure modes (see docs/known-issues.md, "one issuer is not the
    format").

    `rejected` is True if a SUBSTANTIVE cell was seen but failed the name
    test (e.g. a TOTAL line, a "[on file with...]" placeholder) -- the
    caller needs this to tell "this row genuinely carries no name of its
    own, e.g. a second dollar column on a row already named" (rejected
    False) apart from "this row's OWN name was explicitly disqualified"
    (rejected True), which must never fall back to reusing a PREVIOUS
    row's name -- see SAME_ROW_GAP_CHARS."""
    rejected = False
    for cstart, cend, ctext in reversed(_cell_spans(window_start, window_text)):
        stripped = ctext.strip()
        if not stripped or JUNK_CELL.match(stripped):
            continue
        if stripped.lower() in JURISDICTION_WORDS:
            continue
        result = _name_from_cell(cstart, ctext)
        if result is not None:
            return result, False
        # A substantive cell that fails the name test (e.g. a rejected
        # heading fragment) does not necessarily mean there's no real
        # name further back -- e.g. a stray note between rows. Keep
        # walking rather than giving up on the whole window, but remember
        # it was seen.
        rejected = True
    return None, rejected


def _name_from_cell(cell_start: int, cell_text: str) -> tuple[str, int, int] | None:
    """(lender_raw, offset, end) for the name in one cell, or None if the
    cell holds no name-shaped content. `offset`/`end` bound the RAW span
    such that " ".join(text[offset:end].split()) == lender_raw exactly."""
    m = PAREN_OR_BRACKET_SUFFIX.search(cell_text)
    raw = cell_text[:m.start()] if m else cell_text
    lstrip = len(raw) - len(raw.lstrip(" \t\n,"))
    rstrip = len(raw) - len(raw.rstrip(" \t\n,"))
    raw_start = cell_start + lstrip
    raw_end = cell_start + (len(raw) - rstrip)
    if raw_end <= raw_start:
        return None
    span = cell_text[lstrip: len(raw) - rstrip]
    name = " ".join(span.split())
    if not name or not re.search(r"[A-Za-z]", name):
        return None
    name = _split_concatenated_name(name)
    if len(name) < 6:
        return None
    if NOT_A_LENDER.match(name) or NOT_A_LENDER_SUFFIX.search(name):
        return None
    if name != " ".join(span.split()):
        # The splice dropped a prefix (redline old-name). offset/end must
        # still bound exactly the (now shorter) surviving name, which
        # sits at the END of the raw span -- find where it starts.
        idx = span.rfind(name.split()[0])
        if idx == -1:
            return None
        raw_start += idx
        span = span[idx:]
        if " ".join(span.split()) != name:
            return None
    return name, raw_start, raw_end


# --------------------------------------------------------------------------
# Section classification -- which schedule (if any) an anchor sits inside
# --------------------------------------------------------------------------
#
# A credit agreement mentions "Schedule 2.01" dozens of times -- as a cross-
# reference in ordinary prose ("...as set forth in Schedule 2.01...") far
# more often than as the table's own caption. Gating on the nearest such
# MENTION (an earlier version of this file did) pulls in whichever
# unrelated table's dollar figures happen to follow a stray cross-
# reference, anywhere in a 400,000-1,300,000 character document -- that
# produced real false positives (a promissory note's principal amount, a
# litigation schedule entry, a signature block) across three of the six
# filings. A caption is different from a cross-reference in one
# structural way: a caption is immediately followed by its table, a
# cross-reference is followed by another sentence. CAPTION_MAX_GAP chars
# to the next "|" is what tells them apart here.

#: A "Schedule N" / "SCHEDULE N.NNa" marker, however the filer numbers it.
SCHEDULE_MARKER = re.compile(
    r"\bSCHEDULE\s+(?:[0-9]+(?:\.[0-9]+)?[A-Z]?(?:\([a-z]\))?|[IVXLC]+)\b",
    re.IGNORECASE)

#: A true caption's own table starts within this many characters -- a
#: prose cross-reference's next table (if any) is always much farther off.
CAPTION_MAX_GAP = 250

#: Caption text that means "this schedule states sub-limits drawn from a
#: lending commitment, not the commitment itself" -- see module docstring,
#: "sub-limit tables are not the commitment schedule".
EXCLUDE_KEYWORDS = re.compile(
    r"letter\s+of\s+credit|l\s*/\s*c\s+commit|swing\s+line|"
    r"sub[\s-]?limit", re.IGNORECASE)

#: Caption text that means "this schedule states lending commitments" --
#: checked only once EXCLUDE_KEYWORDS has failed to match.
INCLUDE_KEYWORDS = re.compile(r"commitment", re.IGNORECASE)

#: The SAME sub-limit keywords, but as a BARE heading with no "Schedule N"
#: marker of its own -- some filings (d949183) nest a "Letter of Credit
#: Commitments" sub-block inside a single outer "Schedule I" without ever
#: re-captioning it, so the caption-classification alone would keep
#: calling it INCLUDE. This is what overrides that.
EXCLUDED_SUBHEADING = re.compile(
    r"(letter\s+of\s+credit\s+commitments?|l\s*/\s*c\s+commitments?|"
    r"swing\s+line\s+commitments?|"
    r"issuing\s+bank[^.\n|]{0,60}sub[\s-]?limit)", re.IGNORECASE)


def _schedule_captions(text: str) -> list[tuple[int, str]]:
    """[(position, 'include'|'exclude'|'irrelevant')] for every TRUE
    schedule caption in `text` -- a SCHEDULE_MARKER whose table starts
    within CAPTION_MAX_GAP characters, classified by the words between
    the marker and that table. Ordinary prose mentions of "Schedule N"
    (the large majority) have no table that close and are skipped."""
    captions = []
    for m in SCHEDULE_MARKER.finditer(text):
        pipe_pos = text.find("|", m.end())
        if pipe_pos == -1 or pipe_pos - m.end() > CAPTION_MAX_GAP:
            continue
        blurb = text[m.end():pipe_pos]
        if EXCLUDE_KEYWORDS.search(blurb):
            captions.append((m.start(), "exclude"))
        elif INCLUDE_KEYWORDS.search(blurb):
            captions.append((m.start(), "include"))
        else:
            captions.append((m.start(), "irrelevant"))
    return captions


def _classification_at(captions: list[tuple[int, str]], pos: int) -> tuple[int, str]:
    """(marker_pos, classification) for the nearest TRUE caption at or
    before `pos`. No caption yet -> (0, 'irrelevant')."""
    marker_pos, cls = 0, "irrelevant"
    for p, c in captions:
        if p > pos:
            break
        marker_pos, cls = p, c
    return marker_pos, cls


def _included(text: str, marker_pos: int, cls: str, pos: int) -> bool:
    """Whether `pos` sits inside a commitment-schedule block: its
    classification (from `_classification_at`) is 'include', AND no bare
    sub-limit sub-heading (EXCLUDED_SUBHEADING) intervened since the
    caption at `marker_pos`."""
    if cls != "include":
        return False
    return EXCLUDED_SUBHEADING.search(text, marker_pos, pos) is None


#: Tranche label only -- purely descriptive, plays no part in the
#: include/exclude decision above. `[A-Z]` under re.IGNORECASE matches
#: lowercase too, so the leading word-group is deliberately loose; a
#: match that swallows a nearby "Applicable Percentage of ..." COLUMN
#: header (the last one before the data rows start, in tables with a
#: percentage column -- not a tranche name) is filtered out afterward in
#: _tranche_for, not prevented here.
TRANCHE_HEADING = re.compile(
    r"\b((?:[A-Za-z][A-Za-z0-9]*\s+){0,5}"
    r"(?:Term\s+(?:[A-Z0-9]\s+)?Loan|Revolving\s+Credit|Revolving|"
    r"Delayed\s+Draw|Class\s+[A-Z])"
    r"(?:\s+[A-Za-z]+){0,3}\s+(?:Commitments?|Loan))", re.IGNORECASE)

#: A TRANCHE_HEADING match dominated by column-header vocabulary rather
#: than a tranche name -- see TRANCHE_HEADING's docstring.
_NOT_A_TRANCHE = re.compile(r"applicable|percentage", re.IGNORECASE)


def _tranche_for(text: str, caption_start: int, pos: int) -> str:
    """The nearest preceding tranche heading FROM THIS SCHEDULE'S OWN
    caption onward, or 'unspecified'. Bounded to caption_start (not 0) so
    a schedule with no tranche-type qualifier in its own caption (payx's
    is just "SCHEDULE 2.01A COMMITMENTS", with the tranche identified
    nowhere in the table at all) falls back to 'unspecified' instead of
    picking up an unrelated "Revolving Loan" mention from earlier body
    prose."""
    label = "unspecified"
    for m in TRANCHE_HEADING.finditer(text, caption_start, pos):
        if _NOT_A_TRANCHE.search(m.group(1)):
            continue
        label = " ".join(m.group(1).split())
    return label


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------

#: How close a name-less anchor must sit to the previous anchor to count
#: as a SECOND dollar column on the SAME row (e.g. a lender with both a
#: Revolving Commitment and a Term Loan Commitment column, real text from
#: ahr-ex10_1.htm: "Bank of America, N.A. | $81,000,000110,000,000 |
#: 13.75...% | $87,000,000 | 15.8...%") rather than a genuinely different,
#: unnamed row. That row's SECOND "$" has nothing before it but a
#: percentage figure -- the name sits only once, before the FIRST column
#: -- so _nearest_name_cell correctly finds nothing there on its own;
#: without this, the row's Term Loan figure would be silently dropped
#: instead of attributed to the same lender its Revolving figure was.
SAME_ROW_GAP_CHARS = 150


def parse_schedule(text: str) -> list[dict]:
    """Every (lender, amount, offset, end, tranche) row a commitment
    schedule states. See the module docstring for the anchor-and-window
    approach and why this file does not try to find HTML row boundaries."""
    rows: list[dict] = []
    captions = _schedule_captions(text)
    prev_anchor_end = 0
    last_name_result: tuple[str, int, int] | None = None
    for m in MONEY_ANCHOR.finditer(text):
        caption_start, cls = _classification_at(captions, m.start())
        # The window can never reach earlier than the caption that makes
        # this anchor INCLUDED -- otherwise the first row of a table with
        # no prior anchor of its own to bound it (nothing else in the
        # table yet) can reach back past the caption into whatever
        # preceded it, e.g. a signature block that happens to mention the
        # same institution's name for an unrelated reason. Confirmed
        # against real filings: payx-ex10_1.htm's very first schedule row
        # ("JPMORGAN CHASE BANK, N.A." at $95,000,000) sits under 600
        # characters from a signature block reading "...JPMORGAN CHASE
        # BANK, N.A., individually as a Lender, as the Swingline
        # Lender...", and an unbounded window captured that instead.
        gap_from_prev = m.start() - prev_anchor_end
        window_start = max(0, m.start() - WINDOW_CHARS, prev_anchor_end,
                            caption_start)
        window_text = text[window_start:m.start()]
        prev_anchor_end = m.end()

        if not _included(text, caption_start, cls, m.start()):
            last_name_result = None
            continue

        name_result, rejected = _nearest_name_cell(window_start, window_text)
        if name_result is None and not rejected and last_name_result is not None \
                and gap_from_prev <= SAME_ROW_GAP_CHARS:
            # No name of its OWN, and nothing in the window was even a
            # candidate (so this isn't a TOTAL/placeholder row that was
            # explicitly disqualified) -- a second dollar column on the
            # row _nearest_name_cell already named. Reuse that name.
            name_result = last_name_result
        if name_result is None:
            last_name_result = None
            continue
        last_name_result = name_result
        name, n_start, n_end = name_result

        try:
            amount = _amount_of(m)
        except ValueError as exc:
            # A run that cannot be decomposed into one or two well-formed
            # money figures at all (see _split_money_run) -- confirmed
            # against a real row in Sabre Corp's Schedule I
            # ("50,525,825.24657,888.35", which respects neither a
            # 1-decimal-digit nor a 2-decimal-digit split under this
            # dataset's comma-grouping rules). Skip the row rather than
            # guess a number for it or crash the whole document's parse;
            # print so this is loud, not silently dropped.
            print(f"  WARNING: unparseable money run for {name!r} near "
                  f"offset {m.start()}: {exc}")
            continue
        if amount < 1_000_000:
            continue

        rows.append({
            "lender_raw": name,
            "amount_usd": amount,
            "offset": n_start,
            "end": n_end,
            "tranche": _tranche_for(text, caption_start, m.start()),
        })
    return rows


def main() -> int:
    from generators.extract_facilities import TextExtractor

    out = []
    missing: list[tuple[str, list[str], int]] = []
    for filename, facility_ids in AGREEMENTS:
        path = EX10 / filename
        if not path.exists():
            raise SystemExit(f"missing source document: {path}")
        parser = TextExtractor()
        parser.feed(path.read_text(errors="ignore"))
        parser.close()
        text = parser.text()
        rows = parse_schedule(text)
        if not rows:
            # Every current AGREEMENTS entry is verified (ruling T2-R1)
            # to carry a real commitment schedule, independent of this
            # parser -- against the raw filed HTML directly, bypassing
            # it entirely. So this branch firing today would mean either
            # a genuinely NEW data-availability problem (a swapped-in
            # document that, like the original Super Micro/Vertiv picks,
            # turns out not to carry the schedule it appears to) or a
            # parser regression (an anchor count > 0 with zero surviving
            # rows means every candidate got filtered -- THIS file's
            # bug). Either way, this does not raise SystemExit and abort
            # the other agreements -- discarding correctly-parsed
            # schedules to "fail loudly" about one bad one is not a
            # trade this file makes unilaterally. It fails loudly a
            # different way: a prominent summary below, and a non-zero
            # exit code.
            n_anchors = len(list(MONEY_ANCHOR.finditer(text)))
            missing.append((filename, facility_ids, n_anchors))
            print(f"  {filename[:44]:46s}   0 rows  ({n_anchors} raw $ "
                  f"anchors in the doc -- see warning below)")
            continue
        out.append({
            "document": filename,
            "facility_ids": facility_ids,
            "rows": rows,
        })
        names = sorted({r["lender_raw"] for r in rows})
        print(f"  {filename[:44]:46s} {len(rows):>3} rows  "
              f"{len(names):>2} lenders")

    artifact = {
        "generated_for": "wave18 · syndicated-lending-co-lender",
        "method": "structural parse of filed commitment schedules",
        "provenance": "public",
        "source": "SEC EDGAR EX-10 commitment schedules",
        "retrieved_at": datetime.now(timezone.utc).date().isoformat(),
        "agreements": out,
        "facility_ids_not_covered": [
            fid for _, fids, _ in missing for fid in fids],
    }
    (SCREEN / "wave18_schedules.json").write_text(
        json.dumps(artifact, indent=2))
    total = sum(len(a["rows"]) for a in out)
    lenders = sorted({r["lender_raw"] for a in out for r in a["rows"]})
    print(f"\n  {total} schedule rows across {len(out)} agreements, "
          f"{len(lenders)} distinct lender names")
    for name in lenders:
        print(f"    {name}")

    if missing:
        # As of ruling T2-R1 all six AGREEMENTS entries are known-good
        # (verified against the raw filed text, not just this parser) --
        # every current document should reach here with rows > 0, so this
        # branch firing means something NEW went wrong (a bad document
        # substitution, a source file that changed) and deserves the same
        # scrutiny the original Super Micro/Vertiv mis-selection got, not
        # a silent partial artifact.
        print("\n  " + "!" * 70)
        print("  WARNING: {} of {} agreements yielded ZERO schedule rows "
              "and are NOT in the".format(len(missing), len(AGREEMENTS)))
        print("  artifact. Every entry in AGREEMENTS is expected to carry")
        print("  a real commitment schedule (verified against the raw")
        print("  filed HTML, independent of this parser) -- if this fires,")
        print("  something has changed (a swapped source file, a bad")
        print("  substitution) and needs the same scrutiny as the original")
        print("  mis-selection this file's docstring records.")
        for filename, facility_ids, n_anchors in missing:
            print(f"    - {filename}  (facility_ids: "
                  f"{', '.join(facility_ids)}; {n_anchors} raw $ "
                  f"table-cell anchors found, none inside a commitment "
                  f"schedule)")
        print("  These facility_ids have NO Task 2 schedule coverage.")
        print("  " + "!" * 70)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
