"""Task 2 — the commitment-schedule parser.

SCHEDULE_I below is REAL text extracted verbatim (via
generators.extract_facilities.TextExtractor, unedited) from
sources/ex10/885590_0001193125-25-149731_d949183dex101.htm, the "Schedule
I" through "Letter of Credit Commitments" section. It carries the real
"|" cell markers and embedded newlines TextExtractor actually produces --
not a hand-flattened approximation -- because those markers are exactly
what a single flat regex over the text cannot bridge when a filer puts
extra columns (or, as here, an entirely separate sub-limit table) between
a lender's name and its dollar figure. See the parser's module docstring
for the row/cell reconstruction this requires.

Every row carries an {"offset", "end"} span pair, not just an offset sized
to len(lender_raw). `lender_raw` is whitespace-normalised
(`" ".join(...).split()`) while the captured span in the source text is
raw, and TextExtractor.text() deliberately preserves embedded newlines
inside a name (e.g. real text from a MASTEC filing reads
"BANK OF AMERICA,\\nN.A."). An offset-only contract checked by
`SCHEDULE_I[offset:].startswith(lender_raw)` cannot detect that mismatch
on a single-spaced fixture -- it only fails against text with an embedded
newline, which is exactly the case that matters. The contract here is the
checkable invariant `" ".join(text[offset:end].split()) == lender_raw`.
"""
import pytest
from generators.extract_commitment_schedules import parse_schedule

SCHEDULE_I = (
'Schedule I \n\n2025 Refinancing Term Loan Commitments \n \n\n | \n\n | \n | \n | \n | \n\n | \n2025 REFINANCING TERM LOAN LENDERS\n | \n | 2025 REFINANCING TERM\nLOAN COMMITMENTS\n | \n\n | \nJPMorgan Chase Bank, N.A. (as Additional 2025 Refinancing Term Loan Lender)\n | \n | $\n | 1,285,342,270.46\n | \n\n | \nCashless Option Initial Lenders\n\n(cashless roll) [on file with the Administrative Agent]\n | \n | $\n | 1,039,657,729.54\n | \n\n | \n | \n | \n \n | \n \n | \n\n | \nTOTAL\n | \n | $\n | 2,325,000,000.00\n | \n\n | \n | \n | \n \n | \n \n | \n \nThird Amendment Revolving Credit Commitments \n\n \n\n | \n\n | \n | \n | \n | \n\n | \nTHIRD AMENDMENT REVOLVING LENDER\n | \n | THIRD AMENDMENT\nREVOLVING CREDIT\nCOMMITMENTS\n | \n\n | \nJPMorgan Chase Bank, N.A.\n | \n | $\n | 115,000,000.00\n | \n\n | \nBarclays Bank PLC\n | \n | $\n | 97,000,000.00\n | \n\n | \nCiticorp North America, Inc.\n | \n | $\n | 97,000,000.00\n | \n\n | \nHSBC Bank USA, National Association\n | \n | $\n | 97,000,000.00\n | \n\n | \nWells Fargo Bank, National Association\n | \n | $\n | 97,000,000.00\n | \n\n | \nDeutsche Bank AG New York Branch\n | \n | $\n | 50,000,000.00\n | \n\n | \nDNB Capital LLC\n | \n | $\n | 50,000,000.00\n | \n\n | \nGoldman Sachs Bank USA\n | \n | $\n | 50,000,000.00\n | \n\n | \nRoyal Bank of Canada\n | \n | $\n | 50,000,000.00\n | \n\n | \nTruist Bank\n | \n | $\n | 50,000,000.00\n | \n\n | \nGoldman Sachs Lending Partners\n | \n | $\n | 47,000,000.00\n | \n\n | \n | \n | \n \n | \n \n | \n\n | \nTOTAL\n | \n | $\n | 800,000,000.00\n | \n\n | \n | \n | \n \n | \n \n | \n \nLetter of Credit Commitments \n \n\n | \n\n | \n | \n | \n | \n\n | \nISSUING BANK\n | \n | LETTER OF CREDIT\nCOMMITMENTS\n | \n\n | \nJPMorgan Chase Bank, N.A.\n | \n | $\n | 41,666,670.00\n | \n\n | \nBarclays Bank PLC\n | \n | $\n | 41,666,666.00\n | \n\n | \nCitibank, N.A.\n | \n | $\n | 41,666,666.00\n | \n\n | \nGoldman Sachs Bank USA\n | \n | $\n | 41,666,666.00\n | \n\n | \nHSBC Bank USA, National Association\n | \n | $\n | 41,666,666.00\n | \n\n | \nWells Fargo Bank, National Association\n | \n | $\n | 41,666,666.00\n | \n\n | \n | \n | \n \n | \n \n | \n\n | \nTOTAL\n | \n | $\n | 250,000,000.00\n | \n\n | \n | \n | \n \n | \n \n |'
)

#: Same shape as a real row, but the lender's name has an embedded newline --
#: exactly what TextExtractor.text() preserves when a <br> or </td><td>
#: boundary falls inside a name. Regression pin for the offset/end bug.
#: Written in the same "|"-delimited shape real rows carry.
SCHEDULE_WITH_NEWLINE_IN_NAME = (
    "Schedule I \n\nRevolving Credit Commitments\n\n"
    " | \nREVOLVING LENDER | \nREVOLVING CREDIT COMMITMENTS\n\n"
    " | \nBank of America,\nN.A. | \n | $\n | 50,000,000.00\n\n"
    " | \nCitibank, N.A. | \n | $\n | 45,000,000.00\n\n"
)


def test_finds_every_named_lender():
    rows = parse_schedule(SCHEDULE_I)
    names = {r["lender_raw"] for r in rows}
    assert "JPMorgan Chase Bank, N.A." in names
    assert "Barclays Bank PLC" in names
    assert "Citicorp North America, Inc." in names
    assert "HSBC Bank USA, National Association" in names
    assert "Wells Fargo Bank, National Association" in names


def test_amounts_are_cents_exact_integers():
    rows = parse_schedule(SCHEDULE_I)
    by_name = {(r["lender_raw"], r["amount_usd"]) for r in rows}
    assert ("Barclays Bank PLC", 97_000_000) in by_name
    assert ("JPMorgan Chase Bank, N.A.", 1_285_342_270) in by_name


def test_total_rows_are_not_lenders():
    """TOTAL is a sum line, not a syndicate member. Counting it would
    inflate the member population and break the sum check in Task 16."""
    rows = parse_schedule(SCHEDULE_I)
    assert not [r for r in rows if r["lender_raw"].upper().startswith("TOTAL")]


def test_placeholder_rows_are_not_lenders():
    """'Cashless Option Initial Lenders ... [on file with the
    Administrative Agent]' names no institution and must not become one."""
    rows = parse_schedule(SCHEDULE_I)
    assert not [r for r in rows if "on file with" in r["lender_raw"]]
    assert not [r for r in rows if r["lender_raw"].startswith("Cashless")]


def test_total_amount_is_not_attributed_to_the_last_real_lender():
    """Regression pin: TOTAL is rejected as a NAME by test_total_rows_are_
    not_lenders above, but that test cannot see a different bug -- TOTAL's
    own dollar figure being silently reused for the PRECEDING real lender
    instead of being dropped. That happened here: JUNK_CELL's reference-
    code pattern matched any bare all-caps word (every letter of "TOTAL"
    satisfies [A-Z0-9]), so "TOTAL" got skipped as if it were a treaty-
    passport code rather than rejected by name -- and parse_schedule's
    same-row-continuation logic (SAME_ROW_GAP_CHARS) reads "nothing was
    even rejected" as "this dollar figure belongs to the row already
    named", attributing TOTAL's $2,325,000,000 and $800,000,000 to
    JPMorgan Chase Bank, N.A. and Goldman Sachs Lending Partners
    respectively -- the two lenders whose own rows immediately precede
    each TOTAL line in SCHEDULE_I."""
    rows = parse_schedule(SCHEDULE_I)
    amounts = {r["amount_usd"] for r in rows}
    assert 2_325_000_000 not in amounts, "the term-loan TOTAL leaked through"
    assert 800_000_000 not in amounts, "the revolving TOTAL leaked through"
    jpmorgan_amounts = {r["amount_usd"] for r in rows
                         if r["lender_raw"] == "JPMorgan Chase Bank, N.A."}
    assert jpmorgan_amounts == {1_285_342_270, 115_000_000}
    goldman_lending_amounts = {r["amount_usd"] for r in rows
                                if r["lender_raw"] == "Goldman Sachs Lending Partners"}
    assert goldman_lending_amounts == {47_000_000}


def test_sub_limit_table_is_excluded():
    """The 'Letter of Credit Commitments' block is a subset of lenders'
    L/C-issuing capacity DRAWN FROM (not additive to) the revolving
    commitment above -- counting it as syndicate shares would double-count
    an institution and corrupt the sum-of-shares check (Task 16). JPMorgan
    appears in both blocks; only its Third Amendment Revolving figure
    ($115,000,000) may survive, never its L/C figure ($41,666,670)."""
    rows = parse_schedule(SCHEDULE_I)
    amounts = {r["amount_usd"] for r in rows if r["lender_raw"] == "JPMorgan Chase Bank, N.A."}
    assert 115_000_000 in amounts
    assert 41_666_670 not in amounts
    all_amounts = {r["amount_usd"] for r in rows}
    assert 41_666_666 not in all_amounts, "an L/C sub-limit figure leaked through"


def test_offsets_resolve_back_to_the_source_text():
    """The checkable contract is the SPAN invariant, not a prefix check.
    `lender_raw` is whitespace-normalised; `offset`/`end` bound the RAW span
    in the source text, and normalising that raw span must reproduce
    `lender_raw` exactly -- even when the raw span contains an embedded
    newline (see test_offset_end_span_survives_an_embedded_newline)."""
    for r in parse_schedule(SCHEDULE_I):
        span = SCHEDULE_I[r["offset"]:r["end"]]
        assert " ".join(span.split()) == r["lender_raw"]


def test_offset_end_span_survives_an_embedded_newline():
    """Regression pin: a `lender_raw` that is whitespace-normalised paired
    with an `offset` sized to len(lender_raw) breaks the instant the raw
    span contains a newline TextExtractor preserved. This fixture is built
    to require the {"offset", "end"} span contract, not an offset-only one."""
    rows = parse_schedule(SCHEDULE_WITH_NEWLINE_IN_NAME)
    names = {r["lender_raw"] for r in rows}
    assert "Bank of America, N.A." in names
    row = next(r for r in rows if r["lender_raw"] == "Bank of America, N.A.")
    span = SCHEDULE_WITH_NEWLINE_IN_NAME[row["offset"]:row["end"]]
    assert " ".join(span.split()) == row["lender_raw"]
    # The raw span itself must actually contain the newline -- otherwise
    # this fixture is not exercising the bug it claims to pin.
    assert "\n" in span


def test_text_with_no_schedule_yields_nothing():
    """The checker must be able to say NO."""
    assert parse_schedule("This agreement contains no commitment schedule.") == []
    assert parse_schedule("") == []


#: REAL text (via TextExtractor, unedited) from
#: sources/ex10/1632970_0001193125-26-145647_ahr-ex10_1.htm's Schedule
#: 2.01A. The lender NAME is redlined at WORD granularity -- "Barclays"
#: struck through, "Fifth Third " inserted, "Bank " shared unchanged by
#: both the old and new name, "PLC" struck through, ", National
#: Association" inserted -- which TextExtractor (no CSS awareness) renders
#: as one interleaved run: "BarclaysFifth Third Bank PLC, National
#: Association". This is NOT the same shape as the ALL-CAPS whole-name
#: splice NAME_SPLICE recovers (see KNOWN LIMITATION in the module
#: docstring); reconstructing "Fifth Third Bank, National Association"
#: from this needs the strikethrough/underline CSS TextExtractor
#: deliberately doesn't parse.
WORD_LEVEL_REDLINE_ROW = (
    "Schedule 2.01A\n\nLENDERS AND COMMITMENTS\n\n"
    " | \nLender | \nRevolving Commitment | \n\n"
    " | \nBarclaysFifth Third Bank PLC, National Association"
    "\n | \n$50,000,00090,000,000\n | \n8.333333333%\n\n"
)


def test_word_level_redline_name_is_a_documented_known_limitation():
    """Pins CURRENT behaviour rather than leaving this gap silent: the
    parser cannot untangle a word-level redline the way it untangles a
    whole-name splice, and emits the interleaved raw text instead of
    either "Barclays Bank PLC" or "Fifth Third Bank, National
    Association". The row is still captured (with the correct, later
    redlined amount) rather than dropped -- it is visibly malformed to a
    human reader, not silently plausible, which is why this is
    acceptable to ship with rather than to guess a fix for. See the
    module docstring, "REDLINED SCHEDULES", KNOWN LIMITATION."""
    rows = parse_schedule(WORD_LEVEL_REDLINE_ROW)
    assert len(rows) == 1
    row = rows[0]
    assert row["lender_raw"] == "BarclaysFifth Third Bank PLC, National Association"
    assert row["amount_usd"] == 90_000_000
    span = WORD_LEVEL_REDLINE_ROW[row["offset"]:row["end"]]
    assert " ".join(span.split()) == row["lender_raw"]


#: REAL text (via TextExtractor, unedited) from
#: sources/ex10/1597033_0001193125-26-340356_d133770dex101.htm's Schedule I
#: ("Lenders & Commitments"). A Sabre Corp amendment redlines dollar figures
#: throughout by gluing the struck-through old figure directly to its
#: underlined replacement with no separator (same artifact as SCHEDULE_I's
#: JPMorgan/Barclays rows), but one row here exposes a sharper case: the
#: CB NC Centerbridge row's run "2,255,617.21,184,199.01" is ambiguous
#: under a naive greedy read -- taking the conventional 2 decimal digits
#: for the OLD figure ("...617.21") leaves a remainder ("...,184,199.01")
#: that starts with a comma, which can begin no number, so a naive parse
#: silently reported no second figure at all and used the stale
#: $2,255,617.21 instead of the actual filed $1,184,199.01. See
#: _split_money_run's docstring for how this is resolved.
SABRE_SCHEDULE_I = (
'SCHEDULE I \n\nLenders & Commitments \n \n\n | \n\n | \n | \n | \n | \n\n | \nClass A Lender\n | \n | Class A Commitment\n | \n\n | \nPNC Bank, National Association\n | \n | $\n | 115,000,000130,000,000\n | \n\n | \n | \n\n | \nClass B Lender\n | \n | Class B Commitment\n | \n\n | \nLake Central Fund\nLP\n | \n | $\n | 30,000,000.00\n | \n\n | \nBank of America,\nN.A.\n | \n | $\n | 25,000,000.00\n | \n\n | \nMassachusetts Mutual\nLife Insurance Company\n | \n | $\n | 22,686,567.16\n | \n\n | \nCenterbridge Credit CS, L.P\n | \n | $\n | 60,471,879.4415,734,646.43\n | \n\n | \nCenterbridge Special Credit Partners IV – I Co-InvestCB SA Fund, L.P.\n | \n | $\n | 4,060,110.9614,736,699.05\n | \n\n | \nMetropolitan Life\nInsurance Company\n | \n | $\n | 10,000,000.00\n | \n\n | \nCB NC\nCenterbridge Special Credit Partners IV – I Co-Invest, L.P.\n | \n | $\n | 2,255,617.21,184,199.01\n | \n\n | \nCB SA\nFundNC Co-Invest, L.P.\n | \n | $\n | 50,525,825.24657,888.35\n | \n\n | \nMassachusetts Mutual Life Insurance Company\n\n | \n | $\n | 2,686,567.16'
)


def test_ambiguous_redline_split_prefers_a_valid_second_figure():
    """Regression pin for a real amount-extraction bug: a redlined run can
    be ambiguous between "old figure with its conventional 2 decimal
    digits, no second figure" and "old figure with 1 decimal digit, a
    valid second figure follows". Preferring whichever reading leaves a
    WELL-FORMED second money figure is what recovers the actual filed
    (post-amendment) amount rather than silently keeping a stale one that
    is asserted nowhere in the filing."""
    rows = parse_schedule(SABRE_SCHEDULE_I)
    by_name = {r["lender_raw"]: r["amount_usd"] for r in rows}
    assert by_name["CB NC Centerbridge Special Credit Partners IV \u2013 I Co-Invest, L.P."] == 1_184_199
    assert 2_255_617 not in by_name.values(), "the stale pre-amendment figure leaked through"
    # A second real row in the same schedule needs the SAME correct
    # behaviour without regressing the ordinary (unambiguous) case.
    assert by_name["Centerbridge Credit CS, L.P"] == 15_734_646


def test_redlined_amounts_still_split_correctly_when_unambiguous():
    """The fix for the ambiguous case above must not perturb the far more
    common case where the naive greedy 2-decimal-digit read of the first
    figure already leaves a valid second figure -- confirmed against
    every other redlined row in this real schedule."""
    rows = parse_schedule(SABRE_SCHEDULE_I)
    by_name = {r["lender_raw"]: r["amount_usd"] for r in rows}
    assert by_name["PNC Bank, National Association"] == 130_000_000
    assert by_name["CB SA Fund, L.P."] == 14_736_699


def test_unparseable_money_run_is_skipped_not_guessed():
    """A third row in this real schedule ("NC Co-Invest, L.P.", run
    "50,525,825.24657,888.35") respects neither a 1-decimal-digit nor a
    2-decimal-digit split under this dataset's comma-grouping rules (no
    split leaves a remainder that is a well-formed second money figure,
    and the whole run is not one well-formed figure either -- its own
    "decimal" segment is 5 digits long). Rather than guess a number for
    it, parse_schedule must drop the row entirely; every OTHER row in the
    same schedule must still come through unaffected."""
    rows = parse_schedule(SABRE_SCHEDULE_I)
    names = {r["lender_raw"] for r in rows}
    assert "NC Co-Invest, L.P." not in names
    assert 50_525_825 not in {r["amount_usd"] for r in rows}
    assert 657_888 not in {r["amount_usd"] for r in rows}
    # The unparseable row is a single casualty, not a signal to distrust
    # the rest of the schedule.
    assert "PNC Bank, National Association" in names
    assert "CB NC Centerbridge Special Credit Partners IV \u2013 I Co-Invest, L.P." in names
