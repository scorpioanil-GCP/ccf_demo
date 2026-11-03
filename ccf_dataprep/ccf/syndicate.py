"""IRI constants for `syndicated-lending-co-lender` (Wave 18).

One definition, imported by every loader and validator that needs these
IRIs (Tasks 8-10, 14-16) — never re-typed per file. CLAUDE.md's "Definition
of done" item 5 and the Wave 8 correction note in `validators/conditions.py`
both name the same failure this exists to prevent: a validator holding its
own copy of a constant agrees with a wrong loader value and can never catch
the drift, because it never reads anything independent.

Every IRI here is bound in `docs/ccf_dataprep_v2.md`'s Canonical FIBO IRI
binding table (Wave 18 section) — that document is the contract; this module
is only its Python mirror. If the two ever disagree, the doc wins and this
file is wrong. Verified against `sources/fibo/dev.fibo-quickstart.ttl` by
`generators/verify_fibo_wave18.py`, run 2026-08-25 — 17/17 FIBO terms
confirmed declared in subject position (0 missing), plus 3 `ex:` local
names (the reified participation node, T4-R1) confirmed absent from the
ontology under every prefix before minting (0 collisions). Re-run
2026-08-26 (Task 9) for 4 more `ex:` local names (`AmendmentEvent`,
`effectiveDate`, `AmendmentVote`, `voteState`) — 7/7 `ex:` terms confirmed
absent, 17/17 FIBO terms still declared. Re-run again 2026-08-26 (Task 10)
for 2 more `ex:` local names (`envelopeVersion`, `counterparty`) — 9/9
`ex:` terms confirmed absent, 17/17 FIBO terms still declared. Re-run again
2026-08-26 (Task 11b) for 5 more `ex:` local names (`AmendmentThreshold`,
`consentStandard`, `consentPercent`, `amendmentType`, `thresholdGoverns`) —
14/14 `ex:` terms confirmed absent, 17/17 FIBO terms still declared. Two
candidate predicate names for the last one, `governs` and `appliesTo`, were
checked and REJECTED before `thresholdGoverns` was picked: both already
exist as declared FIBO properties under other prefixes
(`fibo-fnd-txn-sec:governs`, `cmns-cxtdsg:appliesTo`) — a different full IRI
under `ex:` would not collide in RDF terms, but the absence check this
module has followed since Task 4 polices the bare LOCAL NAME across every
prefix, precisely so a reader grepping the ontology for "governs" is never
misled into thinking this project's edge is that property.

Two traps this module deliberately does NOT bind, recorded so nobody
re-introduces them:

    fibo-loan-ln-reg:administeredBy   domain LoanRegulatoryRequirement,
                                       range cmns-rga:RegulatoryAgency —
                                       a regulator overseeing a rule.
    fibo-sec-fund-civ:administeredBy  domain CollectiveInvestmentVehicle,
                                       range FundAdministrator — a fund's
                                       administrator.

Neither has a domain that admits a credit facility. `EX_ADMINISTERED_BY`
below is minted instead.
"""

from __future__ import annotations

from ccf.config import EX

# --- §B federation constants (Tasks 14-16) ------------------------------
#
# One name each, defined once. Tasks 14-16 each held an independent copy
# (`generators/generate_peer_positions.py`, `loaders/load_peer_wave18.py`,
# `validators/syndicate.py`, `validators/test_syndicate.py`) under two
# different name pairs that happened to agree in value; CLAUDE.md's
# "Definition of done" item 5 names exactly this risk -- a validator
# holding its own copy of a constant agrees with a wrong loader value and
# can never catch the drift. Consolidated here (whole-branch review fix)
# so a future change to either number can only be made once.
#
# These are BOUNDS the data is measured against, not values read from the
# data -- stated here rather than in a table for the same reason
# `LOCAL_COMPOSITE_TTL_SECONDS`'s own docstring below gives: reading a
# bound from the same store as the measurement would let one row move
# both, and the check would stop checking anything.

#: §B, `max_federation_latency`. A declared latency above this is what
#: makes fail-closed observable.
MAX_FEDERATION_LATENCY_MS = 5_000

#: §B, the local composite's own TTL: four hours. The floor requires a
#: remote TTL strictly below it (so the shortest-wins rule binds) and one
#: strictly ABOVE it -- not equal -- so the rule is being exercised rather
#: than satisfied by every peer tying the local composite. A remote TTL
#: exactly equal to the local composite does not demonstrate "shortest of
#: them wins" in either direction: nothing distinguishes which one bound.
#: Only a remote TTL strictly longer shows the local composite winning
#: because it is shorter. (Whole-branch review fix: the write-time guards
#: previously accepted `>=` here while this validator required strict `<`;
#: the strict form is the one that actually exercises the rule, so it is
#: the one kept.)
LOCAL_COMPOSITE_TTL_SECONDS = 4 * 60 * 60

# --- FIBO namespaces used here -----------------------------------------

_DLN = "https://spec.edmcouncil.org/fibo/ontology/SEC/Debt/DistributedLoans/"
_AGR = "https://spec.edmcouncil.org/fibo/ontology/FND/Agreements/Agreements/"
_COL = "https://www.omg.org/spec/Commons/Collections/"

# --- Syndicate structure — SEC/Debt/DistributedLoans/ classes ----------

FIBO_SYNDICATED_LOAN = f"{_DLN}SyndicatedLoan"
FIBO_FINANCE_SYNDICATE = f"{_DLN}FinanceSyndicate"
FIBO_FINANCE_SYNDICATE_MEMBER = f"{_DLN}FinanceSyndicateMember"
FIBO_ADMINISTRATIVE_AGENT = f"{_DLN}AdministrativeAgent"
FIBO_LEAD_ARRANGER = f"{_DLN}LeadArranger"
FIBO_BOOKRUNNER = f"{_DLN}Bookrunner"
FIBO_SYNDICATION_AGENT = f"{_DLN}SyndicationAgent"
FIBO_DOCUMENTATION_AGENT = f"{_DLN}DocumentationAgent"

# --- Commitment ----------------------------------------------------------

#: The promise-to-act situation. The commitment SHARE amount (a dollar
#: figure per member) has no FIBO property — that stays `EX_COMMITMENT_USD`
#: on the reified participation edge (Task 8).
FIBO_COMMITMENT = f"{_AGR}Commitment"

# --- Membership — the Task 4 open question, settled -----------------------
#
# fibo-sec-dbt-dln:FinanceSyndicateMember's own OWL restriction:
#     cmns-rlcmp:isPlayedBy someValuesFrom [
#         cmns-col:isMemberOf allValuesFrom fibo-sec-dbt-dln:FinanceSyndicate
#     ]
# and fibo-be-fct-fct:Syndicate independently carries:
#     cmns-col:hasMember someValuesFrom cmns-pts:Party
# (isMemberOf is hasMember's declared inverse). Both anchor points already
# use cmns-col:isMemberOf for exactly this relationship, and the property
# carries no domain/range restriction of its own — nothing blocks direct use.
# Settled: ADOPT. Nothing minted for membership.

CMNS_IS_MEMBER_OF = f"{_COL}isMemberOf"

# --- ex: application terms -------------------------------------------------

#: No FIBO property has a domain admitting a credit facility for this
#: relationship — see the module docstring for the two rejected candidates.
EX_ADMINISTERED_BY = f"{EX}administeredBy"

#: The commitment SHARE amount, on the reified participation edge (Task 8).
#: FIBO's Commitment class has no amount property; this is application data.
EX_COMMITMENT_USD = f"{EX}commitmentUsd"
EX_SOURCE_PASSAGE = f"{EX}sourcePassage"

#: T4-R1 fix. A plain triple cannot carry an amount plus a filing offset, so
#: Task 8 reifies the commitment share as its own node: member, facility,
#: EX_COMMITMENT_USD, and EX_SOURCE_PASSAGE all attach to it. Fluree runs
#: without OWL inference (CLAUDE.md rule 7), so the node needs an explicit
#: type — a query for participations must find only nodes typed as one.
#: All three local names confirmed absent from the ontology under every
#: prefix by generators/verify_fibo_wave18.py before minting.
EX_SYNDICATE_PARTICIPATION = f"{EX}SyndicateParticipation"
EX_PARTICIPATION_OF = f"{EX}participationOf"   # participation -> member
EX_PARTICIPATION_IN = f"{EX}participationIn"   # participation -> syndicated loan

#: Live amendment vote, Task 9.
EX_VOTES_ON = f"{EX}votesOn"
EX_VOTE_POSTURE = f"{EX}votePosture"

#: Task 9 -- dated amendment events (public, filing-derived) and the one
#: live, open vote (synthetic -- internal). Verified absent from the
#: ontology under every prefix by `generators/verify_fibo_wave18.py`, run
#: 2026-08-26 -- 7/7 `ex:` terms confirmed absent (0 collisions), 17/17
#: FIBO terms still declared.
#:
#: `ex:AmendmentEvent`/`ex:effectiveDate` are DELIBERATELY DISTINCT from
#: `ex:Amendment`/`ex:validFrom` (Wave 5, `loaders/load_temporal_wave5.py`,
#: 25 assertions -- covenant-in-force-as-of's own bitemporal chain, with
#: `ex:bookingLagDays`/`ex:isEngineeredBookingLag` semantics that do not
#: apply here). Reusing that class would inflate a different product's
#: population with facilities it never touches -- exactly the kind of
#: cross-product drift a validator counting `ex:Amendment` by a stale total
#: would never see coming.
#:
#: `fibo-fnd-agr-ctr:hasEffectiveDate` DOES exist in the ontology (checked,
#: found -- `dev.fibo-quickstart.ttl` ~line 166479) but is an
#: `owl:ObjectProperty` ranging over the reified class `cmns-dt:Date` (a
#: date NODE with its own `hasDateValue` literal), not a literal string.
#: Every temporal predicate this estate has ever written (`ex:validFrom`,
#: `ex:assertedAt`, Wave 5/6/7's own effective-date fields) carries a plain
#: ISO literal instead; introducing the one reified exception here for no
#: benefit besides "it exists" is the module-membership trap CLAUDE.md
#: warns against ("module membership does not pin an IRI"). Rejected;
#: `ex:effectiveDate` minted as a literal-valued property instead.
EX_AMENDMENT_EVENT = f"{EX}AmendmentEvent"
EX_EFFECTIVE_DATE = f"{EX}effectiveDate"

#: Reused, not re-minted -- the same predicate `loaders/load_temporal_wave5.py`
#: already binds as `P_AMENDS` ("links the amendment event to the facility
#: it amends"), disjoint subjects (`AMD-*` there vs. this module's
#: `ex:syndicate/amendment/*` nodes), no domain/range restriction of its
#: own to violate.
EX_AMENDS = f"{EX}amends"

#: The live vote node itself -- distinct from a dated AmendmentEvent
#: because a vote in progress has no effective date yet (Task 9 declines to
#: invent one, the same discipline Task 6 applied).
EX_AMENDMENT_VOTE = f"{EX}AmendmentVote"
EX_VOTE_STATE = f"{EX}voteState"

#: Bound but deliberately unpopulated — see `docs/wave18-design.md` §10 and
#: the binding table row's note. §B lists the relationship; nothing in §C or
#: §F requires an edge, and none exists in this wave's data.
EX_SHARES_COLLATERAL_WITH = f"{EX}sharesCollateralWith"

#: Bilateral disclosure envelope, Tasks 9-10 / 14-16.
EX_DISCLOSURE_ENVELOPE = f"{EX}DisclosureEnvelope"
EX_REQUEST_SCOPE = f"{EX}requestScope"
EX_DISCLOSE_SCOPE = f"{EX}discloseScope"
EX_DECLARED_TTL_SECONDS = f"{EX}declaredTtlSeconds"
EX_ATTESTATION = f"{EX}attestation"
EX_DECLARED_LATENCY_MS = f"{EX}declaredLatencyMs"
EX_DISCLOSURE_PRECISION = f"{EX}disclosurePrecision"

#: Task 10 -- the envelope's own counterparty edge and version label.
#: Checked absent from the ontology under every prefix by
#: `generators/verify_fibo_wave18.py` before minting (0 collisions). No
#: FIBO federation/bilateral-disclosure vocabulary is in scope -- the same
#: finding already recorded against `ex:DisclosureEnvelope` itself.
EX_COUNTERPARTY = f"{EX}counterparty"
#: `fibo-fnd-agr-ctr:Counterparty` (a real, declared FIBO class -- see the
#: v2 binding table's Wave 0 section) is a PARTY ROLE, not a predicate; it
#: answers "is this party playing the counterparty role", not "which node
#: is this envelope's counterparty". Nothing in FIBO supplies the edge
#: itself, so `ex:counterparty` is minted rather than reusing that class's
#: local name for a different grammatical part of speech.
EX_ENVELOPE_VERSION = f"{EX}envelopeVersion"

#: Task 10's temporal axis (§C assigns the envelope `T`) is deliberately
#: NOT a new `ex:effectiveFrom` mint. `loaders/load_abs_fluree_wave14.py`
#: already tried exactly that spelling for Wave 14's trigger thresholds and
#: it was corrected before any write: "a second spelling in an append-only
#: store is not a synonym: it is a predicate half the estate's queries
#: miss" (`docs/ccf_dataprep_v2.md`, Wave 14 section). `ex:validFrom` is
#: this estate's one standing spelling for "since when this fact is valid
#: in the world" -- 3,022 assertions across Waves 5, 7, 11a, 11b and now
#: Task 10 (re-measured live 2026-08-26; `docs/ccf_dataprep_v2.md`'s row
#: for it had read a stale 1,724 since Wave 11c, corrected the same day),
#: reused (not re-minted) here for the same reason. `ex:effectiveDate` (Task 9,
#: immediately above) is deliberately NOT reused instead: it was scoped
#: specifically to `AmendmentEvent`'s FILED, PUBLIC date, kept apart from
#: `ex:Amendment`'s own `ex:validFrom` precisely to avoid inflating that
#: product's population -- reusing it here, on an unrelated
#: synthetic-internal node type, would blur that same scoping rather than
#: honour it. No local name to check absence for: nothing new is minted.
EX_VALID_FROM = f"{EX}validFrom"

# --- Task 11b -- the R half of "Voting thresholds and amendment mechanics"
#
# §C assigns this element to BOTH MongoDB (`L`, Task 11 -- the filed article
# text, span offsets) AND Fluree (`R`, this task -- a typed relationship).
# Task 11 built only the first half; no task's brief covered the second, and
# the product was left with a live vote (Task 9, FAC-A4A5EE) but nothing in
# the estate stating what threshold that vote must clear. This section binds
# the typed node Task 11b's loader work builds to close that gap.
#
# No FIBO vocabulary exists for a voting/consent threshold anywhere in the
# ontology -- confirmed by grepping `dev.fibo-quickstart.ttl` for `rdf:about`
# in subject position under every prefix for "vote", "voting", "consent",
# "threshold", "quorum", "majority" and "amendment": zero hits. The
# SEC/Debt/DistributedLoans/ module itself (fully enumerated above) has
# exactly the eight classes this file already binds and nothing else --
# no consent-standard or threshold class among them. FND/Agreements/Contracts/
# (fibo-fnd-agr-ctr) was checked too, since it is this estate's other
# agreement-law module (`ExtensionProvision`, `NettingProvision`,
# `DisclosureProvision`, `TerminationProvision` all exist there) -- no
# amendment- or consent-provision class exists among its ~40 declared
# classes either. All five terms below are minted.
EX_AMENDMENT_THRESHOLD = f"{EX}AmendmentThreshold"

#: The consent standard the filing NAMES for this threshold, from a small,
#: closed, cross-document vocabulary so a query can group and compare across
#: all six agreements: "Required Lenders", "Required Class A Lenders",
#: "Required Class B Lenders", "each affected Lender", "each Class A
#: Lender", "each Class B Lender", "all Lenders". The first three are
#: percentage-of-exposure standards (a real number backs them, see
#: EX_CONSENT_PERCENT); the rest are per-Lender veto/unanimity standards
#: that no filing expresses as a percentage of anything -- see
#: EX_CONSENT_PERCENT's own docstring for why that field is genuinely
#: absent on those nodes rather than computed as 100%.
EX_CONSENT_STANDARD = f"{EX}consentStandard"

#: The numeric percentage the filing states for a percentage-of-exposure
#: standard ("more than 50%", "at least 50.1%"), as a plain decimal string
#: literal -- present ONLY when a filing states one. A "such Lender" / "each
#: [Class X] Lender directly affected" carve-out is a per-Lender veto right,
#: not a percentage of the syndicate: no filing among the six ever expresses
#: it as "100%" or any other number, and minting one here would be exactly
#: the "counted but not created" failure CLAUDE.md warns against -- a number
#: this task computed standing in for a number the filing never stated.
EX_CONSENT_PERCENT = f"{EX}consentPercent"

#: A short description, drawn from the filing's own enumerated carve-out
#: list, of which kinds of amendment/waiver require this consent standard
#: (e.g. "commitment increase; principal, interest or fee reduction;
#: payment postponement -- as to the Lender(s) directly affected").
EX_AMENDMENT_TYPE = f"{EX}amendmentType"

#: `AmendmentThreshold` node -> the `fibo-sec-dbt-dln:SyndicatedLoan` (Wave
#: 18 facility) it governs -- via `ccf.syndicate.TRANCHE_TO_FACILITIES`,
#: imported, never re-derived (one agreement can carry more than one Wave 18
#: facility; the same threshold governs all of them). Two real FIBO
#: candidates for the bare word "governs" were checked and rejected:
#: `fibo-fnd-txn-sec:governs` and `cmns-rga:governs` ("has and exercises
#: authority over" -- a regulator/polity over a jurisdiction, not a consent
#: rule over a credit facility) are both declared, real properties under
#: OTHER prefixes. Minting `ex:governs` would not collide in RDF terms (a
#: different full IRI), but this module's own absence-check discipline
#: (`generators/verify_fibo_wave18.py::find_any_prefix_subject`) polices the
#: bare LOCAL NAME across every prefix specifically so a term that reads
#: right does not silently borrow a real term's shape -- the same standard
#: `EX_ADMINISTERED_BY` was held to. `cmns-cxtdsg:appliesTo` was checked and
#: rejected for the same reason. `EX_THRESHOLD_GOVERNS` is minted instead.
EX_THRESHOLD_GOVERNS = f"{EX}thresholdGoverns"

#: `EX_SOURCE_PASSAGE` (bound above, Task 8) is REUSED here, not re-minted --
#: but its VALUE on a threshold node is deliberately the same raw
#: `f"{document}#offset={start}-{end}"` string Task 8 uses for commitment
#: shares, not Task 11's real Mongo `passage_id`. Measured before deciding
#: (findings round 1 fix: re-measured against the REGENERATED artifact's own
#: offsets, not a human read of the filings -- the original version of this
#: note was accurate in its conclusion but was not yet checked against what
#: the code actually emitted, which is how four wrong carve-out citations
#: shipped alongside it undetected):
#:
#: Task 11's `voting_threshold` passage starts exactly at the article's own
#: heading and runs at most 3,000 characters -- long enough to hold the
#: general "Required Lenders" sentence in four of six documents (RB Global,
#: AHR, Regis, Sabre), but the PERCENTAGE that names each standard is always
#: defined earlier, in the document's own defined-terms article, never
#: inside that passage in ANY of the six documents -- and in three of six
#: (Bausch, Paychex x2) even the elevated carve-out clause itself falls just
#: past the passage's own captured end offset: Bausch's "each affected
#: Lender" clause 33 chars past it, Paychex's "each affected Lender" clause
#: 897 chars past it, Paychex's "all Lenders" clause 2,261 chars past it.
#: (RB Global, AHR, Regis, and all three of Sabre's elevated tiers land
#: inside the passage.) A single citation field cannot honestly point at a
#: real Mongo passage for some threshold nodes and a document region outside
#: any passage for others without a reader having to guess which is which
#: from the node alone. Citing the raw document+offset uniformly, for every
#: threshold node, is the one scheme that is true for all sixteen -- and it
#: is exactly the standard the dispatch for this task names as the bar to
#: clear: traceable "exactly as the commitment shares are", which is this
#: same raw-offset citation, not a passage lookup.
# EX_SOURCE_PASSAGE is imported above, not redefined.

# --- Ruling T6-R2 — two Wave 4 facility rows excluded from Wave 18 --------
#
# Wave 4 created FOUR Postgres `facility` rows for one Bausch agreement
# (`885590_0001193125-25-149731_d949183dex101.htm`), from four separate
# `facility_type` regex hits at text offsets 2845 / 68967 / 224132 / 312457.
# The filing's actual commitment schedule names exactly TWO tranches:
#
#     1 row   REFINANCING TERM LOAN COMMITMENTS
#     11 rows THIRD AMENDMENT REVOLVING CREDIT COMMITMENTS
#
# Two of the four rows are Wave 4 extraction defects, found and confirmed
# independently while deriving Task 6's own_position rows:
#
#   FAC-105FC5 "Term Loan A"  commitment_amount = $2,325,000,000  — DUPLICATE
#   FAC-08F1D1 "Term Loan"    commitment_amount = $2,325,000,000  — of each other
#
#   Both carry the identical filed total for the ONE real term-loan tranche
#   (Schedule I, "2025 Refinancing Term Loan Commitments": JPMorgan
#   $1,285,342,270.46 + cashless-roll lenders $1,039,657,729.54 =
#   $2,325,000,000.00) — two `facility_type` labels the same regex pass
#   found for one real loan, not two loans.
#
#   FAC-DFCB72 "Delayed Draw Term Loan"  commitment_amount = $637,650,000
#   — its `facility_type` match, offset 312457 above, IS a real (case-
#   insensitive) hit: "...treating any Indebtedness constituting delayed
#   draw term loan commitments then being incurred as fully drawn..." — a
#   ratio-covenant clause about how a HYPOTHETICAL delayed-draw facility is
#   treated in a leverage calculation, not a reference to an established
#   tranche, and not part of any commitment schedule. (Corrected
#   2026-08-26, fix round 2: an earlier version of this note claimed the
#   phrase appears nowhere in the filing at all — true only of a case-
#   SENSITIVE search, and written and read as the broader, false claim.)
#   `commitment_amount` ($637,650,000) was then read at a SEPARATE offset,
#   969473, far outside both the schedule region (~offset 68,800–69,700)
#   and this covenant clause, from an entirely different, unrelated
#   secured-debt basket ("...not to exceed the greater of $637,650,000 and
#   15% of Consolidated Net Tangible Assets..."). So the row was minted
#   from a covenant clause about a hypothetical facility and priced from a
#   second, unrelated clause. No commitment schedule for a delayed-draw
#   tranche exists anywhere in this filing for it to be a lender on.
#
# Ruling T6-R2 (coordinator, 2026-08-26, independently verified against the
# evidence above): **Wave 18's facility set is 12, not 14** — both
# excluded. `ccf_v2.facility` is NOT touched: other products (covenant,
# exposure, collateral) reference those rows, and deleting or mutating them
# would ripple into data that is not Wave 18's to change. Every Wave 18
# artifact and loader excludes these two facility_ids from its OWN output
# instead. This dict is the one place that exclusion list lives — Tasks 8,
# 14 and 16 import it rather than each re-deriving their own.
#
# The FAC-105FC5/FAC-08F1D1 tiebreak is DETERMINISTIC BY RULE, not a
# judgement that one row is more correct than the other — they are two
# labels for one real tranche and neither is right. Two reasons, both
# recorded because either alone is weak: the filing calls the tranche
# "2025 Refinancing Term Loans" (plain, not "A"), so "Term Loan" is the
# closer label; and FAC-08F1D1 sorts first, which makes the tiebreak
# reproducible rather than a matter of taste.
#: {document -> {tranche -> [facility_id, ...]}}. Moved here from
#: `generators/generate_syndicate_internal.py` by Ruling T8-PRE (Task 8):
#: Task 6 only needed the three documents where JPMorgan is a filed lender
#: (RB Global, Bausch, Paychex), so its copy never had to resolve AHR,
#: Regis or Sabre. Task 8 builds edges for all 45 members across all six
#: agreements and needs every tranche. `generators/generate_syndicate_internal
#: .py` imports this dict rather than defining its own; its `derive_positions`
#: still does its own broadcast-to-every-listed-facility loop and its own
#: "no mapping" assertion, both untouched by this move.
#:
#: TWO DIFFERENT MEANINGS hide behind "a tranche maps to more than one
#: facility_id", and the two consumers below use them differently:
#:
#:   BROADCAST (RB Global's three Revolving tranches, each -> the single
#:   combined FAC-A4A5EE): every facility in the list gets the row's full
#:   amount. `generate_syndicate_internal.py::derive_positions` implements
#:   this, and only this -- every value it ever reads is a single-item list
#:   (JPMorgan is absent from the one document below with a multi-item list).
#:
#:   POSITIONAL SPLIT (AHR's "Term Loan Commitment" -> [FAC-405B7A,
#:   FAC-2A2C38]): the row order for a repeated (lender_raw, offset, end)
#:   key IS the split -- position 0 is that lender's Revolving Commitment
#:   figure, position 1 its Term Loan Commitment figure. See the note below
#:   the dict for the evidence. `loaders/load_fluree_wave18.py` implements
#:   this reading; it is the ONLY entry with more than one facility_id where
#:   broadcast would be wrong, and nothing in Task 6 ever visits it (JPMorgan
#:   is not a filed lender on AHR), so the two readings never collide.
#:
#: A tranche not present here (zero facilities) is a stale-artifact
#: condition and every consumer must fail loudly rather than skip the row.
TRANCHE_TO_FACILITIES: dict[str, dict[str, list[str]]] = {
    "1046102_0001104659-25-031884_tm2511351d1_ex10-1.htm": {
        "Revolving A Commitment": ["FAC-A4A5EE"],
        "Revolving B Commitment": ["FAC-A4A5EE"],
        # RB Global's third revolving sub-tranche -- same combined Postgres
        # row as A and B (see the module's RB GLOBAL note below), $30M
        # across 3 lenders. Absent from Task 6's original copy only because
        # JPMorgan does not lend on this sub-tranche, not because it lacks
        # a mapping.
        "Revolving C Commitment": ["FAC-A4A5EE"],
        "New Term A Loan Commitment": ["FAC-6F4065"],
    },
    "885590_0001193125-25-149731_d949183dex101.htm": {
        # Ruling T6-R2: FAC-105FC5 dropped -- it is a Wave 4 duplicate of
        # FAC-08F1D1, not a second real tranche. See
        # ccf.syndicate.WAVE18_EXCLUDED_FACILITIES for the evidence.
        "REFINANCING TERM LOAN COMMITMENTS": ["FAC-08F1D1"],
        "THIRD AMENDMENT REVOLVING CREDIT COMMITMENTS": ["FAC-E08688"],
    },
    "723531_0001193125-26-021794_payx-ex10_1.htm": {
        "unspecified": ["FAC-E386A4"],
    },
    # --- AHR (American Healthcare REIT), added Task 8 -----------------
    #
    # Task 2's own report names this tranche label "imprecise": AHR's
    # Schedule 2.01A has TWO dollar columns per lender row -- "Revolving
    # Commitment" then "Term Loan Commitment" -- but the parser attributes
    # BOTH to the single label "Term Loan Commitment" (both columns share
    # one heading region with no distinct per-column marker in the source
    # text). Verified directly against the raw filing
    # (sources/ex10/1632970_..._ahr-ex10_1.htm, plain-text offset ~564076):
    # the header row reads "Lender | Revolving Commitment | Revolving
    # Commitment Percentage | Term Loan Commitment | Term Loan Commitment
    # Percentage", and for every lender with two schedule rows sharing one
    # (lender_raw, offset, end) key, the FIRST row's amount matches that
    # lender's Revolving Commitment cell and the SECOND matches their Term
    # Loan Commitment cell -- checked against all 6 such pairs (Bank of
    # America $110M/$87M, KeyBank $90M/$73M, Citizens $90M/$73M, Fifth
    # Third $45M/$60M, Truist $70M/$42M, Regions $70M/$42M). A lender with
    # only ONE row (Citibank, Credit Agricole, Morgan Stanley, Royal Bank
    # of Canada, and the corrupt merged "BarclaysFifth Third..." row) has
    # "--" (no figure) in the raw text's Term Loan Commitment cell, so a
    # single row is that lender's Revolving Commitment only.
    #
    # `loaders/load_fluree_wave18.py` reads this list positionally: for a
    # repeated (lender_raw, offset, end) key, the Nth occurrence (in the
    # artifact's own row order, which matches the raw text's left-to-right
    # column order) goes to `facility_ids[N]`. A single occurrence goes to
    # `facility_ids[0]`.
    #
    # FLAGGED, NOT FIXED HERE (out of Task 8's scope -- it touches neither
    # ccf_v2.facility nor WAVE18_EXCLUDED_FACILITIES, both owned by
    # Ruling T6-R2): neither Postgres total reconciles cleanly against this
    # reading. Summing the "new" (post-redline) Revolving Commitment figures
    # across all 11 rows (the 10 resolved lenders plus the corrupt merged
    # row) gives ~$845M against FAC-405B7A's recorded $550,000,000; summing
    # the "new" Term Loan Commitment figures gives $377M against
    # FAC-2A2C38's recorded $35,000,000. The filing's own defined-terms
    # article states the Term Loan Commitments' aggregate as exactly
    # "$550,000,000" (offset ~192545) -- the figure actually recorded
    # against FAC-405B7A, labelled "Revolving Credit Facility" in Postgres.
    # And $35,000,000 appears in the filing only as the unrelated
    # "Threshold Amount" covenant defined term (offset ~196393), never as a
    # schedule total. This is the same SHAPE of defect T6-R2 found and
    # excluded twice in Bausch (a covenant figure mistaken for a facility
    # total); it has NOT been independently verified or ruled to that same
    # standard here, and Task 8 does not exclude a facility on its own
    # authority. Reported to the coordinator in the Task 8 report; Task 16's
    # reconciliation floor should expect this document not to sum cleanly.
    "1632970_0001193125-26-145647_ahr-ex10_1.htm": {
        "Term Loan Commitment": ["FAC-405B7A", "FAC-2A2C38"],
    },
    # --- Regis Corp, added Task 8 --------------------------------------
    #
    # A "First Amendment" schedule -- both tranche labels name their
    # facility directly (Term Loan A / Term Loan B), matching
    # FAC-01BB3F ("Term Loan A") and FAC-5F29AF ("Term Loan B") by label,
    # not by inference. The other two Wave 18 Regis facilities
    # (FAC-E4D2F8 "Term Loan", FAC-25F991 "Revolving Credit Facility") have
    # no schedule rows in this exhibit at all -- the First Amendment only
    # lists the newly-added incremental commitments, not the full existing
    # facility -- so they get a SyndicatedLoan node (Task 8) but no
    # participation edges, which is expected, not a gap.
    "716643_0001193125-24-281618_d761586dex101.htm": {
        "First Amendment Term Loan A Commitment": ["FAC-01BB3F"],
        "First Amendment Term Loan B Commitment": ["FAC-5F29AF"],
    },
    # --- Sabre Corp, added Task 8 ---------------------------------------
    #
    # One Wave 18 facility for this document (FAC-3DF1D5); both Class A and
    # Class B tranches roll into it. `commitment_amount` is NULL on this
    # facility (Wave 4 gap, carried forward from Task 2's report) -- Task 8
    # still builds the SyndicatedLoan node and both classes' participation
    # edges from the schedule's own filed amounts; a NULL facility total is
    # Task 16's reconciliation-floor problem to name explicitly, not a
    # reason to skip the edges here.
    "1597033_0001193125-26-340356_d133770dex101.htm": {
        "Class A Commitment": ["FAC-3DF1D5"],
        "Class B Commitment": ["FAC-3DF1D5"],
    },
}

WAVE18_EXCLUDED_FACILITIES: dict[str, str] = {
    "FAC-105FC5": (
        "duplicate of FAC-08F1D1 — both carry the identical filed "
        "$2,325,000,000 total for the ONE real term-loan tranche "
        "('2025 Refinancing Term Loan Commitments'); a Wave 4 "
        "facility_type regex hit (offset 224132) split one real tranche "
        "into two rows. Deterministic tiebreak: FAC-08F1D1 is kept "
        "(closer label to the filing's own wording, and sorts first) — "
        "this is not a claim that FAC-08F1D1 is the 'correct' row."
    ),
    "FAC-DFCB72": (
        "no commitment-schedule support at all — its facility_type match "
        "(offset 312457) is a real but hypothetical mention, a ratio-"
        "covenant clause treating a delayed-draw facility as fully drawn "
        "for leverage purposes, not an established tranche; "
        "commitment_amount ($637,650,000) was then read at a separate "
        "offset, 969473, from an unrelated secured-debt covenant basket, "
        "far outside the schedule region (~offset 68,800–69,700)."
    ),
}
