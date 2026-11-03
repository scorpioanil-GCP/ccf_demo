#!/usr/bin/env python3
"""Wave 18 Task 6 -- our own positions, ratings, workout postures, and the
competition-law rules that govern what a syndicate desk may say to a
co-lender. Writes `sources/screening/wave18_internal.json`, consumed by
`loaders/load_postgres_wave18.py`.

## Ruling T6-R1 -- record no position where the filing does not name us

We are JPMorgan Chase Bank, N.A. (`member_id = 'SYNM-80cbe8f1'`, per Task 5).
Where a filed commitment schedule names us as a lender, `share_usd` is that
filed figure, verbatim, taken from `sources/screening/wave18_schedules.json`
-- the artifact Task 2 already parsed out of the six EX-10 credit
agreements. ONE EXCEPTION, and it is exact arithmetic, not an invented
number: `FAC-A4A5EE`'s $84,000,000 is the SUM of two separately filed rows
("Revolving A Commitment" $44,000,000 + "Revolving B Commitment"
$40,000,000), because Wave 4 modelled both currency sub-tranches as one
Postgres facility row -- see the RB GLOBAL entry below. Where a schedule
does not name us at all, **no own_position row is written for that facility
at all** -- inventing one would contradict a public document that already
lists a complete lender roster summing to the facility total (breaking Task
16's reconciliation floor). `internal_rating` and `workout_posture` are
ours to invent, `synthetic — internal`, and they attach ONLY to a facility
where we hold a real, filed position.

## Deriving which facilities those are

The preflight ruling states a measured count -- JPMorgan named on 7 of the
14 facilities (RB Global 2, Bausch 4, Paychex 1) -- but that is a document
count, not a facility count. Independently deriving per-facility placement
from the schedule + facility artifacts produced 6, one short of 7 (RB
Global 2, Bausch 3, Paychex 1), and surfaced two Wave 4 facility-extraction
defects in the Bausch document. Ruling T6-R2 (coordinator, independently
verified against the same evidence) settled those two: **Wave 18's facility
set is 12, not 14** -- see `ccf.syndicate.WAVE18_EXCLUDED_FACILITIES` for
the full evidence and the deterministic tiebreak rule. That drops the count
again, from 6 to **5**.

Each JPMorgan schedule row carries a `tranche` label (e.g. "Revolving A
Commitment") but no `facility_id` -- Task 2 parsed rows per AGREEMENT, and
one agreement can carry several facility_ids (Wave 4's per-document
facility split). Assigning a row to a facility therefore requires reading
what the filing text itself says the tranche total is, against
`ccf_v2.facility.commitment_amount` for that document's facility rows:

  RB GLOBAL (tm2511351d1_ex10-1.htm) -- clean, 2 facilities.
    "Revolving A Commitment" ($44,000,000) and "Revolving B Commitment"
    ($40,000,000) both roll into the one Postgres row FAC-A4A5EE
    ("Revolving Credit Facility") -- our recorded share there, $84,000,000,
    is the exact SUM of those two separately filed rows, not itself a
    single verbatim filed figure (see the note above). "New Term A Loan
    Commitment" ($61,500,000) is FAC-6F4065 ("Term Loan A") and IS a single
    verbatim filed figure. Matches the ruling's "RB Global (2)".

  PAYCHEX (payx-ex10_1.htm) -- clean, 1 facility, 1 row, $145,000,000 on
    FAC-E386A4. Matches the ruling's "Paychex (1)".

  BAUSCH (d949183dex101.htm) -- 2 facilities, not 4. Wave 4 parsed FOUR
    facility rows out of this document (FAC-E08688, FAC-105FC5, FAC-08F1D1,
    FAC-DFCB72), but the filing's actual commitment schedule names only TWO
    tranches: "REFINANCING TERM LOAN COMMITMENTS" (1 row) and "THIRD
    AMENDMENT REVOLVING CREDIT COMMITMENTS" (11 rows). FAC-DFCB72 ("Delayed
    Draw Term Loan") has NO schedule support at all -- "delayed draw term
    loan commitments" occurs exactly once (case-insensitive), inside a
    ratio-covenant clause treating a HYPOTHETICAL delayed-draw facility as
    fully drawn for a leverage calculation, not an established tranche;
    its $637,650,000 commitment_amount was then read from a second,
    unrelated secured-debt covenant basket. See
    `ccf.syndicate.WAVE18_EXCLUDED_FACILITIES` for both offsets and the
    exact filed text. FAC-105FC5 ("Term Loan A") and FAC-08F1D1 ("Term
    Loan") both carry commitment_amount = $2,325,000,000, exactly the
    total of Schedule I's "2025 Refinancing Term Loan Commitments" -- two
    `facility_type` labels the same Wave 4 regex pass found for the ONE
    real term-loan tranche, not two loans. Ruling T6-R2 excludes both
    FAC-DFCB72 (no schedule support) and FAC-105FC5 (duplicate; FAC-08F1D1
    kept by a deterministic tiebreak, not because it is "more correct").
    JPMorgan's filed $1,285,342,270 is recorded once, against FAC-08F1D1
    only. "THIRD AMENDMENT REVOLVING CREDIT COMMITMENTS" ($115,000,000) is
    FAC-E08688. So Bausch is (2): FAC-E08688 and FAC-08F1D1.

2 + 2 + 1 = **5**, which is why `test_our_position_exists_on_every_selected_
facility` in `validators/test_syndicate.py` asserts `>= 5`, not `>= 6` --
keeping a row on FAC-105FC5 to hold the floor at 6 would have been exactly
the "counted but not created" failure CLAUDE.md warns against: a position
this generator's own evidence says is a duplicate, kept anyway to satisfy a
number.

This IS a finding to report, not a number to reconcile silently -- see
this task's report (Ruling T6-R1's disagreement) and its fix report
(Ruling T6-R2's resolution).

    uv run generators/generate_syndicate_internal.py
"""
from __future__ import annotations

import json
import re
from datetime import date, timezone, datetime

from ccf.config import PG_SCHEMA_V2, REPO_ROOT, assert_v2_schema, pg_connect
from ccf.syndicate import TRANCHE_TO_FACILITIES, WAVE18_EXCLUDED_FACILITIES
from generators.extract_facilities import TextExtractor

SCREEN = REPO_ROOT / "sources" / "screening"
OUT = SCREEN / "wave18_internal.json"
EX10_DIR = REPO_ROOT / "sources" / "ex10"

JPMORGAN_LEI = "7H6GLXDRUGQFU57RNE97"
JPMORGAN_MEMBER_ID = "SYNM-80cbe8f1"

AS_OF = date(2026, 8, 26)  # date of Ruling T6-R1, the measurement this
                            # generator's own derivation is checked against

#: {document -> {tranche -> [facility_id, ...]}}, imported from
#: `ccf.syndicate` (Ruling T8-PRE, Task 8: two tasks need this now, so it no
#: longer lives in one of them). See that module's own comment for the
#: evidence behind every entry, in particular why FAC-DFCB72 is absent and
#: why one tranche maps to two facility_ids for Bausch. `derive_positions`
#: below is untouched by the move -- it still only ever reads the
#: single-item lists for RB Global, Bausch and Paychex, since JPMorgan is
#: not a filed lender on any of the multi-item entries Task 8 added
#: (AHR, whose split those loaders read positionally, not by broadcast).

#: Our invented view of each facility we actually hold, one grade from
#: `ccf_v2.rating_scale` and one posture from the closed vocabulary. Keyed
#: by facility_id so a facility appearing under two entries above (the
#: Bausch duplicate) still gets one, self-consistent rating.
OUR_VIEW: dict[str, dict[str, str]] = {
    "FAC-6F4065": {"internal_rating": "BBB-", "workout_posture": "performing"},
    "FAC-A4A5EE": {"internal_rating": "BBB-", "workout_posture": "performing"},
    "FAC-E08688": {"internal_rating": "B+", "workout_posture": "watch"},
    "FAC-08F1D1": {"internal_rating": "B+", "workout_posture": "watch"},
    "FAC-E386A4": {"internal_rating": "A", "workout_posture": "performing"},
}

COMPETITION_LAW_RULES = [
    {
        "rule_id": "CLR-001",
        "jurisdiction": "US",
        "constrains": "forward-looking pricing exchange",
        "rule_text": (
            "A syndicate desk officer must not disclose to another lender "
            "in the same syndicate, outside the arranger-run allocation "
            "process, any indication of the price or spread this bank "
            "intends to bid or hold on a future facility for the same "
            "borrower or sector. Coordinating forward pricing among "
            "competing lenders is a per se Sherman Act Section 1 concern."
        ),
        "provenance": "synthetic — internal",
    },
    {
        "rule_id": "CLR-002",
        "jurisdiction": "US",
        "constrains": "disclosure of another borrower's terms",
        "rule_text": (
            "Covenant levels, pricing grids, or fee terms negotiated with "
            "one borrower must not be shared with a co-lender to inform "
            "that co-lender's negotiation with a DIFFERENT, unrelated "
            "borrower, even where both borrowers sit in the same industry "
            "and the co-lender is also a lender to this bank elsewhere."
        ),
        "provenance": "synthetic — internal",
    },
    {
        "rule_id": "CLR-003",
        "jurisdiction": "US",
        "constrains": "exchange of unannounced workout intent",
        "rule_text": (
            "This bank's internal workout_posture and any related "
            "restructuring, exit, or amendment intent for a shared "
            "facility must not be communicated to a co-lender before it is "
            "raised through the formal steering committee or agent bank "
            "process -- informal advance coordination among lenders on "
            "how they intend to vote or exit risks concerted action "
            "against the borrower's and other lenders' interests."
        ),
        "provenance": "synthetic — internal",
    },
    {
        "rule_id": "CLR-004",
        "jurisdiction": "EU",
        "constrains": "market allocation between competing lenders",
        "rule_text": (
            "This bank must not agree, formally or informally, with a "
            "co-lender to divide prospective borrowers, sectors, or deal "
            "flow between them -- Article 101 TFEU treats market or "
            "customer allocation between competitors as a restriction of "
            "competition by object, regardless of syndicate membership on "
            "any individual facility."
        ),
        "provenance": "synthetic — internal",
    },
]

## Task 9 -- amendment events (public, filed) and the one live vote
## (synthetic -- internal). §C: "Amendment events and effective dates --
## 8-K Item 1.01; amended EX-10 -- public -- Fluree -- T". Every date below
## is EXTRACTED, not invented -- `extract_amendment_events` reads each
## governing EX-10's own title/preamble recital ("dated as of ..." /
## "entered into as of ...") at generation time and asserts a match exists;
## a document with none would raise loudly here and record no event for
## it, the same discipline Task 6 applied when it declined to invent a
## seventh position rather than fabricate a filed figure.

AMENDMENT_DATE_RE = re.compile(
    r"(?:dated as of|entered into as of)\s+"
    r"([A-Z][a-z]+ \d{1,2}, \d{4})",
    re.IGNORECASE,
)


def _facility_ids_for_document(document: str, schedules: dict) -> list[str]:
    """The Wave 18 facility_ids `ccf_v2.facility`/Task 8 associate with this
    document -- read from the schedules artifact's own `facility_ids` list
    (the SAME source `wave18_facility_ids()` in `load_fluree_wave18.py`
    filters), not from `TRANCHE_TO_FACILITIES` -- that dict only has an
    entry for a facility with an actual schedule ROW in this exhibit, and
    Regis's other two facilities (FAC-E4D2F8, FAC-25F991) have none despite
    being governed by the SAME financing agreement and its SAME amendment
    (see the module's own note on `TRANCHE_TO_FACILITIES` for why). Filtered
    through Ruling T6-R2's exclusions, same as every other Wave 18
    consumer of this artifact."""
    for agreement in schedules["agreements"]:
        if agreement["document"] == document:
            return sorted(
                fid for fid in agreement["facility_ids"]
                if fid not in WAVE18_EXCLUDED_FACILITIES
            )
    raise AssertionError(f"{document}: not found in wave18_schedules.json")


def extract_amendment_events(schedules: dict) -> list[dict]:
    """One dated amendment/restatement event per Wave 18 governing
    document (6), read directly from that EX-10's own filed text -- never
    invented. Each of the six documents this wave uses IS itself either an
    amendment or an amended-and-restated agreement (that is why it was
    filed), so its own title/preamble recital names the date in its first
    few hundred characters; `assert` below makes a document with no such
    recital a loud failure, not a silently-skipped one."""
    documents = sorted({a["document"] for a in schedules["agreements"]})
    events: list[dict] = []
    for document in documents:
        facility_ids = _facility_ids_for_document(document, schedules)
        if not facility_ids:
            # Not reachable today -- every Wave 18 document keeps at least
            # one facility after T6-R2's exclusions -- but a real "no event
            # to record" condition if a future exclusion ever emptied one.
            continue

        path = EX10_DIR / document
        parser = TextExtractor()
        parser.feed(path.read_text(errors="ignore"))
        parser.close()
        text = parser.text()

        m = AMENDMENT_DATE_RE.search(text[:3000])
        assert m, (
            f"{document}: no 'dated as of ...' / 'entered into as of ...' "
            f"recital found in the first 3000 characters -- refusing to "
            f"invent an effective date; record no event for this document "
            f"instead of fabricating one")
        date_text = m.group(1)
        effective_date = datetime.strptime(date_text, "%B %d, %Y").date()

        events.append({
            "document": document,
            "facility_ids": facility_ids,
            "effective_date": effective_date.isoformat(),
            "date_text": date_text,
            "source_passage": f"{document}#offset={m.start(1)}-{m.end(1)}",
            "provenance": "public",
        })
    return events


#: The live vote's facility. Every Wave 18 facility's syndicate size was
#: measured directly against the loaded Fluree graph (Task 8's own
#: `ex:participationIn` edges, grouped and counted) before this pick:
#:
#:   FAC-A4A5EE  18   RB Global, Revolving Credit Facility (A+B+C combined)
#:   FAC-6F4065  18   RB Global, Term Loan A               (tied largest)
#:   FAC-E386A4  12   Paychex
#:   FAC-E08688  11   Bausch, Revolving
#:   FAC-405B7A  10   AHR, Revolving
#:   FAC-2A2C38   6   AHR, Term Loan
#:   FAC-3DF1D5   8   Sabre
#:   FAC-01BB3F   3   Regis, Term Loan A
#:   FAC-5F29AF   2   Regis, Term Loan B
#:   FAC-08F1D1   1   Bausch, Term Loan (JPMorgan-only filed row)
#:
#: RB Global's two facilities tie at 18 -- the largest Wave 18 syndicate,
#: matching the interface note ("RB Global's syndicate is the largest").
#: FAC-A4A5EE is picked over FAC-6F4065 because it is the REVOLVING
#: facility -- the instrument type amendment votes (pricing grid resets,
#: covenant relief, maturity extensions) most often touch in practice --
#: and because Bank of America, the administrative agent on BOTH tied
#: facilities, is ALSO a filed lender specifically on FAC-A4A5EE (three
#: separate Revolving A/B/C rows), which lets this vote demonstrate the
#: "agent's own posture" question the brief raises, not just assert it in
#: prose. A vote among Regis's 2-3-lender facilities would show two or
#: three postures at most; 18 members gives room for all four vocabulary
#: values to appear at once, which is the stronger demonstration of
#: "divergent" the brief asks for.
VOTE_FACILITY_ID = "FAC-A4A5EE"
VOTE_DOCUMENT = "1046102_0001104659-25-031884_tm2511351d1_ex10-1.htm"
VOTE_REVOLVING_TRANCHES = (
    "Revolving A Commitment", "Revolving B Commitment", "Revolving C Commitment",
)

#: Every posture is `synthetic — internal` -- bank-internal desk knowledge
#: of how each lender is currently leaning on a pending amendment, no
#: filing states this. Assigned per member_id (content-keyed, not
#: positional) so a future re-run of Task 3's resolver cannot silently
#: reassign a posture to the wrong institution. All four vocabulary values
#: are used, not just the floor of two, so the vote demonstrates the full
#: closed vocabulary at once:
#:
#:   consent (8)    -- JPMorgan (this bank; own_position on FAC-A4A5EE is
#:                     "performing" -- Task 6 -- so we support the
#:                     amendment) plus seven other large, well-capitalized
#:                     relationship lenders with no filed reason to object.
#:   decline (4)     -- lenders with a plausible reason to push back: a
#:                     narrower commercial-banking mandate (Goldman Sachs
#:                     Bank USA, HSBC) or a foreign parent less exposed to
#:                     this borrower relationship (Westpac, Bank of
#:                     Montreal).
#:   abstain (2)     -- Bank of America, the ADMINISTRATIVE AGENT on this
#:                     facility (and also a filed lender here) -- an agent
#:                     is usually neutral on a vote it administers, per the
#:                     brief's own note; and Export Development Canada, a
#:                     Canadian export-credit agency whose mandate
#:                     constrains it from taking a position on an ordinary
#:                     commercial amendment.
#:   undecided (4)   -- the four smaller Canadian syndicate members
#:                     (Canadian Imperial Bank of Commerce, Fédération des
#:                     Caisses Desjardins du Québec, The Bank of Nova
#:                     Scotia, The Toronto-Dominion Bank), still awaiting
#:                     their own internal credit-committee sign-off.
MEMBER_POSTURES: dict[str, str] = {
    # -- consent (8) ------------------------------------------------------
    "SYNM-80cbe8f1": "consent",  # JPMorgan Chase Bank, N.A. (us)
    "SYNM-81d79474": "consent",  # Wells Fargo Bank, N.A.
    "SYNM-d855a7a6": "consent",  # PNC Bank, N.A.
    "SYNM-774d74e4": "consent",  # Truist Bank
    "SYNM-bd62e4cb": "consent",  # U.S. Bank National Association
    "SYNM-296cd7b6": "consent",  # Citizens Bank, N.A.
    "SYNM-b61d5481": "consent",  # Royal Bank of Canada
    "SYNM-ec5e05e6": "consent",  # MUFG Bank, Ltd.
    # -- decline (4) -------------------------------------------------------
    "SYNM-6d33e219": "decline",  # Goldman Sachs Bank USA
    "SYNM-90ba8afa": "decline",  # HSBC Bank USA, N.A.
    "SYNM-e7bed519": "decline",  # Westpac Banking Corporation
    "SYNM-3e7b26ef": "decline",  # Bank of Montreal
    # -- abstain (2) ---------------------------------------------------
    "SYNM-9d3fd0fd": "abstain",  # Bank Of America, N.A. -- administrative agent
    "SYNM-ff996510": "abstain",  # Export Development Canada
    # -- undecided (4) -------------------------------------------------
    "SYNM-2e08b511": "undecided",  # Canadian Imperial Bank of Commerce
    "SYNM-600395b6": "undecided",  # Fédération des Caisses Desjardins du Québec
    "SYNM-fcb706ef": "undecided",  # The Bank of Nova Scotia
    "SYNM-9bc30105": "undecided",  # The Toronto-Dominion Bank
}

POSTURE_VOCABULARY = {"consent", "decline", "abstain", "undecided"}


def _facility_a4a5ee_lenders(schedules: dict, institutions: dict) -> set[str]:
    """Every member_id with a filed row on VOTE_FACILITY_ID -- derived
    independently from the raw schedule rows (not trusted from Task 8's
    Fluree load), so `build_amendment_vote` can assert MEMBER_POSTURES'
    key set is EXACTLY this set before a single triple is written. RB
    Global's three Revolving sub-tranches all broadcast to the one
    combined Postgres facility FAC-A4A5EE (`ccf.syndicate.
    TRANCHE_TO_FACILITIES`'s documented BROADCAST case) -- every row on
    any of the three tranches counts."""
    raw_to_member: dict[str, dict] = {
        raw: m for m in institutions["members"] for raw in m["raw_names"]
    }
    lenders: set[str] = set()
    for agreement in schedules["agreements"]:
        if agreement["document"] != VOTE_DOCUMENT:
            continue
        for row in agreement["rows"]:
            if row["tranche"] not in VOTE_REVOLVING_TRANCHES:
                continue
            member = raw_to_member.get(row["lender_raw"])
            assert member is not None, (
                f"{VOTE_DOCUMENT}: lender_raw {row['lender_raw']!r} on a "
                f"revolving tranche resolves to no member")
            lenders.add(member["member_id"])
    return lenders


def build_amendment_vote(schedules: dict, institutions: dict) -> dict:
    """The one live, open amendment vote. Asserts, at generation time (not
    only in a later test), that MEMBER_POSTURES names EXACTLY the members
    who actually hold a filed row on VOTE_FACILITY_ID -- no fewer (a
    missing voter silently understates the syndicate) and no more (a vote
    from a non-lender is the fabricated relationship this whole task warns
    against)."""
    eligible = _facility_a4a5ee_lenders(schedules, institutions)
    posted = set(MEMBER_POSTURES)
    assert posted == eligible, (
        f"MEMBER_POSTURES does not match {VOTE_FACILITY_ID}'s real filed "
        f"lender roster -- extra (not a lender): {sorted(posted - eligible)}; "
        f"missing (a lender with no posture recorded): "
        f"{sorted(eligible - posted)}")

    bad_postures = {p for p in MEMBER_POSTURES.values() if p not in POSTURE_VOCABULARY}
    assert not bad_postures, f"posture outside the closed vocabulary: {bad_postures}"

    distinct = set(MEMBER_POSTURES.values())
    assert len(distinct) >= 2, (
        f"all {len(MEMBER_POSTURES)} postures agree ({distinct}) -- the "
        f"§F condition requires the divergence to be real")

    return {
        "facility_id": VOTE_FACILITY_ID,
        "document": VOTE_DOCUMENT,
        "vote_state": "open",
        "rationale": (
            "RB Global's Revolving Credit Facility (A/B/C combined) ties "
            "FAC-6F4065 for the largest Wave 18 syndicate at 18 lenders "
            "(measured against the live Fluree graph, not the schedule "
            "artifact alone), and its administrative agent (Bank of "
            "America) is also a filed lender here, which lets the vote "
            "show the agent's own posture rather than merely assert it. "
            "18 voters is enough room for all four closed-vocabulary "
            "posture values to appear at once, not just the floor of two."
        ),
        "postures": dict(sorted(MEMBER_POSTURES.items())),
        "provenance": "synthetic — internal",
    }


## Task 7 -- projection plans per perspective (`syndicate_projection_plan`,
## own table, keyed `perspective` -- not a widening of Wave 7's
## `projection_plan` or Wave 16's `ib_projection_plan`, both of which encode
## a different product's vocabulary. Wave 16 and 17 both set that precedent;
## this follows it.)
##
## `perspective` is not "which institution is asking" -- it is OUR bank's
## OWN role on a given facility: administrative agent, an existing
## participant, or a prospective participant evaluating a syndicate it has
## not joined (Ruling T6-R1: we hold a filed position on exactly 5 of the
## 12 Wave 18 facilities; the other 7 are the `prospective` population by
## construction, not a gap).
##
## Every element name below is checked against §C's Data Catalog and
## §5-7 of docs/wave18-design.md -- what is ACTUALLY built (Tasks 5-6,
## Postgres) vs. PLANNED for a later task (Tasks 8-15, Fluree/Mongo/
## SQLite/peer) is recorded in this task's report, not silently glossed
## here. Nothing in this list is invented free-hand:
##
##   syndicate_composition    Catalog: "Syndicate composition -- lender
##                             names and commitments" (Fluree, R). PLANNED
##                             Task 8 -- FinanceSyndicate/Member nodes.
##   member_commitment        Catalog row 1's commitment-share half, carried
##                             on the `participatesIn` edge (ccf.syndicate.
##                             EX_COMMITMENT_USD). PLANNED Task 8.
##   own_position              Catalog: "Own position, rating, and workout
##                             posture" (Postgres, E). BUILT -- Task 6,
##                             `ccf_v2.own_position`.
##   administrative_agent     Catalog: "Administrative agent identity"
##                             (Fluree, R). PARTIALLY BUILT -- Task 1 wrote
##                             `ccf_v2.facility.administrative_agent`
##                             already; the Fluree `administeredBy` edge is
##                             PLANNED Task 8.
##   voting_thresholds         Catalog: "Voting thresholds and amendment
##                             mechanics" (MongoDB + Fluree, L/R). PLANNED
##                             Task 11.
##   assignment_terms          Catalog: "Assignment and transfer provisions"
##                             (MongoDB, L). PLANNED Task 11 -- the
##                             administrative agent processes assignments,
##                             so this is agent-only, unlike voting_thresholds.
##   amendment_vote_posture    Catalog: "`participatesIn` . `votesOn` edges"
##                             / "Amendment events and effective dates"
##                             (Fluree, R/T). PLANNED Task 9
##                             (ccf.syndicate.EX_VOTES_ON, EX_VOTE_POSTURE
##                             already bound).
##   member_call_report        Catalog: "Co-lender financial condition"
##                             (Postgres, E). BUILT -- Task 5,
##                             `ccf_v2.member_call_report`. Agent-only: the
##                             desk administering a syndicate has reason to
##                             see every member's Call Report condition; an
##                             ordinary participant does not.
##   desk_tracker_note         Catalog: "Syndicate-desk local position
##                             tracker" (SQLite, E). PLANNED Task 13.
##   peer_position              Catalog: "Simulated peer fabric" / progress.md
##                             ruling P3's `Context.peer_positions`. PLANNED
##                             Task 14/15.
##   divergence_indicator      Not a stored table -- §B Schema lists it as a
##                             contract MEASURE ("divergence indicators"),
##                             and §D step 7 computes it at assembly
##                             ("Compute divergence indicators where a
##                             peer's posture differs from the bank's own").
##                             PLANNED Task 16 (Compose Operator). Precedent
##                             for a computed-measure element name (not a
##                             literal table): Wave 17's aml_projection_plan
##                             carries "reasoning_trail",
##                             "counterparty_network" the same way.
##
## What is explicitly NOT here: "payment_waterfall". §D's own sentence --
## "the agent's perspective carries documentation and waterfall detail no
## participant receives" -- is narrative color describing §A's counterfactual
## ("The administrative agent holds the loan documentation and the payment
## waterfall"), not a §C Data Catalog row. No element in §C, and nothing
## planned in docs/wave18-design.md §5-7, represents a payment waterfall for
## this product -- Wave 18 does not build one. Naming it here would be
## exactly the "generating against an invented local name" failure CLAUDE.md
## warns against. `assignment_terms` and `member_call_report` are the real,
## catalog-grounded elements that carry the "documentation no participant
## receives" half of that sentence instead.
PLANS: dict[str, list[str]] = {
    "prospective": [
        "syndicate_composition", "administrative_agent", "voting_thresholds",
    ],
    "participant": [
        "syndicate_composition", "member_commitment", "own_position",
        "administrative_agent", "voting_thresholds",
        "amendment_vote_posture", "peer_position", "divergence_indicator",
    ],
    "agent": [
        "syndicate_composition", "member_commitment", "own_position",
        "administrative_agent", "voting_thresholds", "assignment_terms",
        "amendment_vote_posture", "member_call_report", "desk_tracker_note",
        "peer_position", "divergence_indicator",
    ],
}


def build_projection_plans() -> list[dict]:
    """Three `syndicate_projection_plan` rows, one per perspective. Asserts
    the nesting is strict here too, at generation time -- so a future edit
    to PLANS that collapses two perspectives to the same set fails loudly
    before it ever reaches the database, not only in the validator."""
    prospective = set(PLANS["prospective"])
    participant = set(PLANS["participant"])
    agent = set(PLANS["agent"])
    assert prospective < participant < agent, (
        "PLANS no longer nests strictly: prospective ⊂ participant ⊂ agent "
        f"required; got prospective={prospective} participant={participant} "
        f"agent={agent}")

    return [
        {
            "perspective": perspective,
            "elements": elements,
            "provenance": "synthetic — internal",
        }
        for perspective, elements in PLANS.items()
    ]


def _jpmorgan_member_id(institutions: dict) -> str:
    """Resolve JPMorgan's member_id from the artifact rather than trusting
    the hard-coded constant blindly -- asserts they agree."""
    matches = [m for m in institutions["members"] if m["lei"] == JPMORGAN_LEI]
    assert len(matches) == 1, (
        f"expected exactly one member with LEI {JPMORGAN_LEI}, found "
        f"{len(matches)}")
    member_id = matches[0]["member_id"]
    assert member_id == JPMORGAN_MEMBER_ID, (
        f"JPMorgan's member_id is {member_id!r}, not the established "
        f"{JPMORGAN_MEMBER_ID!r} -- facts changed underneath this task")
    return member_id


def _valid_grades() -> set[str]:
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT grade FROM "{PG_SCHEMA_V2}".rating_scale')
        return {r[0] for r in cur.fetchall()}


def derive_positions(schedules: dict, institutions: dict) -> list[dict]:
    member_id = _jpmorgan_member_id(institutions)
    jpmorgan_raw = {
        n for m in institutions["members"] if m["member_id"] == member_id
        for n in m["raw_names"]
    }

    totals: dict[str, int] = {}
    for agreement in schedules["agreements"]:
        doc = agreement["document"]
        tranche_map = TRANCHE_TO_FACILITIES.get(doc, {})
        for row in agreement["rows"]:
            if row["lender_raw"] not in jpmorgan_raw:
                continue
            targets = tranche_map.get(row["tranche"])
            assert targets, (
                f"{doc}: JPMorgan row on tranche {row['tranche']!r} has no "
                f"facility mapping -- TRANCHE_TO_FACILITIES is stale "
                f"against the schedule artifact")
            for facility_id in targets:
                assert facility_id not in WAVE18_EXCLUDED_FACILITIES, (
                    f"{facility_id} is excluded by Ruling T6-R2 "
                    f"({WAVE18_EXCLUDED_FACILITIES[facility_id]}) but "
                    f"TRANCHE_TO_FACILITIES still routes a row to it")
                totals[facility_id] = totals.get(facility_id, 0) + row["amount_usd"]

    valid_grades = _valid_grades()
    positions = []
    for facility_id, share_usd in sorted(totals.items()):
        view = OUR_VIEW[facility_id]
        assert view["internal_rating"] in valid_grades, (
            f"{facility_id}: {view['internal_rating']!r} is not a grade in "
            f"ccf_v2.rating_scale")
        positions.append({
            "facility_id": facility_id,
            "member_id": member_id,
            "share_usd": share_usd,
            "internal_rating": view["internal_rating"],
            "workout_posture": view["workout_posture"],
            "as_of": AS_OF.isoformat(),
            "provenance": "synthetic — internal",
        })
    return positions


def main() -> int:
    assert_v2_schema(PG_SCHEMA_V2)

    schedules = json.loads((SCREEN / "wave18_schedules.json").read_text())
    institutions = json.loads((SCREEN / "wave18_institutions.json").read_text())

    positions = derive_positions(schedules, institutions)
    projection_plans = build_projection_plans()
    amendment_events = extract_amendment_events(schedules)
    amendment_vote = build_amendment_vote(schedules, institutions)

    doc = {
        "generated_for": "wave18 · syndicated-lending-co-lender · Task 6/7/9",
        "method": (
            "filed JPMorgan rows in wave18_schedules.json, mapped to "
            "facility_id via TRANCHE_TO_FACILITIES (see module docstring "
            "for the evidence behind each mapping); ratings and postures "
            "invented and labelled synthetic — internal. Amendment event "
            "dates extracted from each governing EX-10's own title/preamble "
            "recital (Task 9); vote postures invented and labelled "
            "synthetic — internal"
        ),
        "ruling": "T6-R1, T6-R2",
        "derived_facility_count": len(positions),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "own_positions": positions,
        "competition_law_rules": COMPETITION_LAW_RULES,
        "projection_plans": projection_plans,
        "amendment_events": amendment_events,
        "amendment_vote": amendment_vote,
    }
    OUT.write_text(json.dumps(doc, indent=2) + "\n")

    print(f"wrote {OUT.relative_to(REPO_ROOT)}: "
          f"{len(positions)} own_position rows on facilities "
          f"{[p['facility_id'] for p in positions]}, "
          f"{len(COMPETITION_LAW_RULES)} competition_law_rule rows, "
          f"{len(projection_plans)} syndicate_projection_plan rows "
          f"({[p['perspective'] for p in projection_plans]}), "
          f"{len(amendment_events)} amendment_events, "
          f"amendment_vote on {amendment_vote['facility_id']} with "
          f"{len(amendment_vote['postures'])} voters "
          f"({len(set(amendment_vote['postures'].values()))} distinct "
          f"postures)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
