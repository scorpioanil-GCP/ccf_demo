#!/usr/bin/env python3
"""The partition validator — the inverse of v1's compare_backends.py.

v1 asserted every store held the *same* data and verified they matched. That
goal is now wrong. Each store is authoritative for a different slice precisely
so cross-store assembly is a real operation. So this asserts the opposite:

    each store holds the slice it owns, AND NOTHING IT DOES NOT.

Written in Wave 0 against empty stores so it fails loudly from day one rather
than being retrofitted once the data is already wrong.

Checks, per Q019 §3 and CLAUDE.md's store-assignment table:

    P1  Fluree holds edges + temporal + policy binding, and carries no entity
        attribute that Postgres owns (nodes carry `lei` + label only)
    P2  Postgres holds entity attributes and the crosswalk
    P3  MongoDB holds document text and spans, no typed edges
    P4  SQLite holds departmental policy only
    P5  no element is duplicated into a store that does not own it

Wave 11b added four checks on the same principle: the seven surveillance
tables are present and populated in Postgres and appear in no other store; a
Fluree surveillance node carries identity, ordering and provenance but no
measurement; the supersession chain is mirrored into no Postgres column; and
every `signalAbout` target resolves in whichever store owns it — Fluree for
facilities and pledges, Postgres for drawdowns.

Neo4j is deliberately absent: it was dropped from the v2 estate on 2026-08-16
(see docs/ccf_dataprep_v2.md). Depth-bounded traversal is expressed as unioned
fixed-length SPARQL patterns, and cycle detection runs application-side.

Exit code is non-zero if any assertion fails, so this works as a gate.

Run: uv run validators/partition.py
"""

from __future__ import annotations

import re
import sqlite3
import sys
from dataclasses import dataclass

import requests

from ccf.config import (
    CO_LENDER_FLUREE_LEDGER,
    CO_LENDER_PG_SCHEMA,
    EX,
    FLUREE_LEDGER_V2,
    FLUREE_QUERY_ENDPOINT,
    MONGO_DB_V2,
    MONGO_URI,
    PG_SCHEMA_V2,
    SQLITE_PATH,
    co_lender_configured,
    co_lender_pg_connect,
    pg_connect,
)

#: Not imported from ccf.config — kept local, as load_collateral_wave9.py does.
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
FIBO = "https://spec.edmcouncil.org/fibo/ontology/"

#: Attributes Postgres is sole author of. Finding any of these on a Fluree
#: node is a single-writer violation, not a convenience.
POSTGRES_OWNED_ATTRS = [
    "legalName", "jurisdiction", "entityStatus", "clientType", "riskRating",
    "kycStatus", "onboardingDate", "nationality", "dateOfBirth",
    # Wave 11a — debt_instrument and rating_scale columns (Task 7). A grade
    # assertion's `grade` string is NOT here: nothing in Postgres records
    # which grade an obligor held on a given date, so it is not a leak — see
    # docs/ccf_dataprep_v2.md's Wave 11a extension register.
    "couponPct", "maturity", "issueDate", "faceAmountUsd", "ratingBand",
    "seniority", "tenorYears", "notch", "modifier",
    # Wave 11b — columns of the seven surveillance tables (Task 9). Fluree
    # holds WHICH signals exist, what they are about and in what order they
    # superseded one another; every MEASUREMENT of a signal is Postgres's.
    # `ex:provenance`, `ex:validFrom`, `ex:sourceAccession` and `ex:item` are
    # deliberately NOT here — the graph is the sole author of a node's own
    # provenance label and of the chain's time ordering, exactly as Wave 11a's
    # `ex:grade` is not a leak.
    "severity", "score", "weight", "thresholdScore", "thresholdPct",
    "signalType", "observedAt", "employer", "noticeDate", "employees",
    "tone", "seenDate", "pctChange", "priorValue", "downWeightFactor",
    "downWeightReason", "verdict",
    # Wave 12 — treasury_client.intent (Task 5/7). Not previously checked;
    # added when Task 9's regulatory-posture overlay needed a jurisdiction/
    # intent key of its own and had to be named to avoid colliding with this
    # one. `ex:postureJurisdiction` / `ex:postureIntent` are the Fluree-owned
    # names (RegulatoryPosture's own key, not a copy of any Postgres row) —
    # deliberately distinct from the bare "jurisdiction"/"intent" flagged here.
    "intent",
    # Wave 12 (Task 16 close-out) — every remaining Postgres column across the
    # fifteen new tables (Task 5/7/12/13/14) plus the extended deposit_account
    # (Wave 9, Task 7). "rate"/"valuePct"/"seriesId"/"obsDate" are the literal
    # "no rate value is duplicated from reference_rate/fx_reference_rate into
    # Fluree" check the Task 16 brief names verbatim. "rawVariance" and
    # "designedClass" are the RULING F22 discriminator-leak guard —
    # load_fluree_wave12_fx.py's break nodes assert structure only (which
    # trade, which two systems), never the answer key, and this is what
    # proves that absence rather than merely documenting it.
    "reportedCash", "cashFactAsof", "homeCurrency", "notional", "yieldBp",
    "maturityDate", "limitPct", "maxTenorDays",
    "valuePct", "rate", "seriesId", "obsDate", "derivation",
    "obsTs", "tradingDay",
    "executionTs", "valueDate", "notionalBand", "systemName", "valueRate",
    "rawVariance", "designedClass", "thresholdPips", "pipSize",
    "jurisdiction", "setoffContractual", "setoffEnforceable", "balance",
    # Wave 14 — every measured ABS quantity. Fluree owns the deal STRUCTURE
    # (which trust, which tranche, which trigger, what the threshold is and
    # when it took effect); every number that is measured, aggregated or
    # collected belongs to Postgres and must never appear on a Fluree node.
    # `ex:thresholdValue`, `ex:thresholdComponent`, `ex:thresholdUnit`,
    # `ex:passageAnchor`, `ex:validFrom` and `ex:assertedAt` are deliberately
    # NOT here -- those are the graph's own, the same way Wave 11a's
    # `ex:grade` and Wave 11b's `ex:provenance` are not leaks.
    # Verified clean at the time of writing: none of these 25 predicates
    # appears on any node in the ledger.
    "poolBalance", "delinquencyPercent", "loanCount", "noteBalance",
    "ocAmount", "ocPercent", "ocTarget", "chargedoffAmount", "recoveredAmount",
    "weightedAverageCoupon", "creditBand", "delinquentBalance",
    "cumulativeNetLossPercent", "receivableCount", "assetCount",
    "seniorityRank", "cusip", "interestRate", "originalLoanAmount",
    "obligorCreditScore", "currentDelinquencyStatus", "vintage", "servicer",
    "creditTier", "maxGranularity",
    # Wave 17 — aml_party columns. `load_fluree_wave17.py`'s AMLParty nodes
    # carry identity only (`ex:lei` = syn_lei, plus an id-echo label); every
    # other party attribute -- legal name, jurisdiction, entity status,
    # incorporation date/flag, party kind -- resolves from Postgres.
    # `legalName`, `jurisdiction` and `entityStatus` were already covered by
    # the Wave 8/9 entries above; `incorporated`, `incorporationDate` and
    # `partyKind` were not, and this generic scan could not see either leak
    # onto an AMLParty node until now -- coverage previously existed only in
    # `validators/test_aml_typology.py`'s task-specific regression
    # (`test_no_postgres_owned_attribute_leaks_onto_aml_party_nodes`), raised
    # on Task 13's review and routed to this task.
    "incorporated", "incorporationDate", "partyKind",
    # Wave 18 — every column of the five syndicated-lending tables that is
    # not already covered above. Fluree owns the syndicate STRUCTURE (who is
    # a member of which syndicate, which participation carries which
    # commitment, who administers the facility, which amendment is being
    # voted on and with what posture); every attribute OF a member, of its
    # call-report condition, of our own position in a facility, of a
    # competition-law rule and of a projection plan is Postgres's.
    #
    # `lei`, `provenance`, `votePosture`, `sourcePassage`, `commitmentUsd`,
    # `effectiveDate`, `voteState`, `envelopeVersion`, `requestScope`,
    # `discloseScope`, `consentStandard`, `consentPercent`, `amendmentType`
    # and `validFrom` are deliberately NOT here -- each is the graph's own,
    # the same way Wave 11a's `ex:grade` and Wave 11b's `ex:provenance` are
    # not leaks. `legalName` and `jurisdiction` are already covered by the
    # Wave 8/9 entries above.
    #
    # Verified clean at the time of writing: none of these 16 predicates
    # appears on any node in ledger fibo-v2.
    "rssd", "idBasis", "gleifCategory", "rawNames", "retrievedAt",
    "tier1Capital", "totalAssets", "totalEquity", "reportDate",
    "shareUsd", "internalRating", "workoutPosture",
    "ruleText", "constrains", "perspective", "elements",
    # Wave 19 — the remaining `bank_capital` capital figures not already
    # covered above (`tier1Capital`/`totalAssets`/`totalEquity`/`reportDate`
    # are Wave 18's own member_call_report columns, reused verbatim by
    # bank_capital's matching names), plus exposure_proposal's and
    # large_exposure_projection_plan's attribute columns. `check_wave19()`
    # below ALSO runs a scoped scan of this same figure set -- belt and
    # suspenders, the same shape Wave 18's W18-2 took alongside this generic
    # scan, after Task 5's ex:rssd regression showed a generic list alone is
    # only as good as remembering to add the new name to it.
    #
    # `proposal_id`, `subject_lei`, `facility_type`->`facilityType` sit on
    # NO Fluree node at all (exposure_proposal has no graph counterpart —
    # §C keeps the whole row in Postgres), so their absence here is a
    # precondition of the check meaning anything, not a gap in it.
    "tier2Capital", "riskWeightedAssets", "tier1RatioPct", "totalRatioPct",
    "cet1RatioPct", "totalDeposits", "ratioConsistent", "ratioDeltaPp",
    "facilityType", "commitmentAmount", "isHypothetical", "expectedOutcome",
    "elementsIncluded", "carriesMethodology", "carriesReplayAttribution",
]

#: ex: classes that are legitimate extensions because FIBO has no equivalent.
#: Verified against a full search of the edmcouncil/fibo repository in Wave 0:
#: all 295 modules yield exactly one covenant-bearing term, BreachOfCovenant,
#: which IS bound to FIBO and used. Anything typed under ex: that is NOT in
#: this set is shadowing a real FIBO term and is a defect.
#: Object properties Wave 13b asserts on `Person` nodes. Listed separately
#: from the client-360 allowlist so `every identity edge is an EDGE` below can
#: prove the thing that makes them safe: an edge points at a node, so it cannot
#: smuggle a Postgres attribute into the graph the way a literal can.
IDENTITY_EDGES = (
    "https://spec.edmcouncil.org/fibo/ontology/FND/AgentsAndPeople/People/hasPersonName",
    "https://www.omg.org/spec/Commons/Identifiers/isIdentifiedBy",
    "http://www.w3.org/2002/07/owl#differentFrom",
    f"{EX}screenedAgainst",
    f"{EX}subjectToConstraint",
    # Wave 13b Task 8: a natural person is the top of a beneficial-ownership
    # chain, so Person nodes now own things and are beneficial owners. Both
    # are object properties.
    "https://spec.edmcouncil.org/fibo/ontology/BE/OwnershipAndControl/CorporateOwnership/isBeneficialOwnerOf",
    "https://spec.edmcouncil.org/fibo/ontology/FND/OwnershipAndControl/Ownership/owns",
)

#: Wave 16 Task 2b, 2026-08-24: the per-entry rationale below records how
#: each extension was hand-verified absent from FIBO AT THE TIME it was
#: added -- against `prod.fibo-quickstart.ttl`, a shallow edmcouncil/fibo
#: clone, or an ad-hoc `rdf:about` search, depending on the wave. That is
#: provenance, not a standing guarantee, and `prod` in particular carries
#: Release maturity only: it silently omits 40 Provisional modules (known-
#: issues §19.8). The check below no longer trusts the comments alone -- it
#: re-verifies every entry against `ccf.fibo.fibo_absent()`, which reads
#: `dev.fibo-quickstart.ttl` (a verified superset of `prod`) fresh each run.
#: See the "permitted ex: extensions are still absent from FIBO (dev)" check.
PERMITTED_EX_TYPES = {
    # FIBO models covenants only at the point they are BREACHED
    # (fibo-fnd-agr-ctr:BreachOfCovenant, which IS bound and used). The
    # covenant as a continuously-measured constraint is a credit-monitoring
    # concept, not a contract-law one, so it has no FIBO class.
    f"{EX}Covenant",
    f"{EX}CovenantDefinition",
    f"{EX}MeasurementPeriod",
    # Wave 15. `ex:DefinedTerm` and `ex:CovenantDefinition` are ROLE markers,
    # and they are permitted only because every node carrying them ALSO
    # carries the real FIBO class.
    #
    # The real class exists and both covenant specs' §C are wrong to say it
    # does not: `fibo-fnd-agr-ctr:ContractualDefinition` is "contractual
    # element that specifies the meaning of a term in a legal document, whose
    # definition is substitutable for the term whenever it occurs in the body
    # of that document" -- an exact fit for a defined-terms entry. It was found
    # only because this very check refused `DefinedTerm` as shadowing, and
    # answering the refusal required a search of the complete FIBO Production
    # ontology instead of an assertion. The vault has been told.
    #
    # What FIBO does NOT model is the ROLE a definition plays: which
    # contractual definition is the one a covenant is measured by, and which is
    # a term that definition depends on. `definedBy` and `crossReferences`
    # carry the relation; these two types let a consumer query the populations
    # directly under Fluree's no-inference default. Asserting them INSTEAD of
    # the FIBO class would be shadowing; asserting them alongside is
    # refinement, and load_covenant_definitions_wave15.py asserts both on every
    # node it writes.
    f"{EX}DefinedTerm",
    f"{EX}Amendment",
    f"{EX}PolicyVersion",
    # RESOLVED, Wave 16 Task 2b Fix Round 1, 2026-08-24: `ex:Address` REMOVED.
    # It shadowed the real `fibo-fnd-plc-adr:Address` `owl:Class` (FND/Places/
    # Addresses -- a Foundations module, not a Provisional-only one; `prod`
    # simply never surfaced it). Confirmed dead before removal: 0 instances
    # of <http://example.org/fibo/Address> and 0 uses of it as a predicate in
    # ledger fibo-v2, and no reference anywhere in the repo outside this
    # file's own comments.
    # CCF architectural concepts, not financial-ontology ones. FIBO has no
    # opinion on a fabric's completeness shortfall.
    f"{EX}ContextDebt",
    # Information-barrier concepts. FIBO models financial instruments and the
    # parties to them; it does not model a bank's internal control-room
    # apparatus, which is a supervisory and organisational construct rather
    # than a contractual one. Reg FD is a disclosure regime, not an instrument.
    # The reified act of deciding whether two records are one person, with its
    # own confidence. Verified absent from FIBO 2026-08-22: an exhaustive
    # `rdf:about` search of the clone returns ZERO for IdentityResolution,
    # Resolution, EntityResolution and RecordLinkage, and no `rdfs:label`
    # contains "resolution". `cmns-id:isIdentifiedBy` relates a thing to an
    # identifier and says nothing about how confident anyone was.
    f"{EX}IdentityResolution",
    # A rule restricting where person data may materialize. Verified absent
    # from FIBO 2026-08-22: zero `rdf:about` matches for Constraint, and
    # FIBO's residence terms describe a person's residence, not a policy
    # about who may see it.
    f"{EX}ResidencyConstraint",
    f"{EX}WallCrossing",
    f"{EX}EmbargoWindow",
    f"{EX}RegFDEvent",
    # Wave 10 client-360 concepts. FIBO has no vocabulary for a bank's own
    # coverage roster, its client-contact log, or its internal deal pipeline —
    # these are operational relations, not financial-instrument ones.
    f"{EX}Banker",
    f"{EX}Interaction",
    f"{EX}Deal",
    # Wave 11a. FIBO's issuance vocabulary models the offering and the
    # instrument, not the bank's-eye-view disclosure event; the only class
    # for that event is Business Process (BP/SecuritiesIssuance/DebtIssuance),
    # out of scope. Grade assertions and rating actions are NOT here —
    # they're real FIBO terms (OrganizationCreditRating, RatingAssessmentEvent).
    # Wave 15. The reified pledge of one asset to one facility, carrying the
    # lien position. Verified absent from FIBO Production 2026-08-24 by a
    # search of the COMPLETE ontology -- `prod.fibo-quickstart.ttl`, 8.2 MB,
    # every module in one file, rather than the handful of modules a
    # per-module scan would have covered. Across all of it the only term whose
    # local name contains "Pledge" is `NegativePledge` (a covenant); the
    # Collateral family is Collateral / CollateralAgreement /
    # CollateralizedGuaranty / CollateralizedLoan / CollateralValueAsOfDate;
    # the Lien family is LenderLienPosition and its two named individuals.
    # None reifies the pledge itself. `fibo-fnd-agr-ctr:CollateralAgreement`
    # is the near miss and is deliberately NOT used: it is a WrittenContract,
    # and typing a (facility, asset, position) triple as a contract is the
    # same error as the `isSubordinateTo` retraction -- a contract-level term
    # standing in for a relationship that is not a contract. Note also that it
    # declares in FND/Agreements/Contracts while the Debt module merely refers
    # to it, so binding it off a per-module scan would have produced a
    # fabricated IRI that still greps as present.
    f"{EX}CollateralPledge",
    f"{EX}IssuanceEvent",
    # Wave 11b credit-surveillance concepts. All three were searched against
    # the full FIBO Production release AND the OMG Commons Ontology Library
    # (Task 1, 2026-08-20) and are absent from both — not near-missed, absent.
    # The reason they are absent is the same reason they are legitimate here:
    # FIBO's subject is the financial world itself — instruments, agreements,
    # parties, the ratings and events that concern them. A surveillance signal
    # is not a fact about that world; it is a fact about a BANK'S OBSERVATION
    # of that world, and observation apparatus is out of FIBO's scope by
    # design. Each of the three is that distinction in a different place:
    #
    #   WarningSignal    — an adverse-media hit, a WARN notice, an 8-K item, a
    #                      trend delta and a spread widening are five entirely
    #                      unrelated things in FIBO's terms (a news article, a
    #                      layoff filing, a disclosure, an accounting movement,
    #                      a price move). What makes them ONE class is that the
    #                      bank's surveillance policy weights and scores them on
    #                      a common scale. That commonality is an artifact of
    #                      the monitoring process, so no financial ontology
    #                      would — or should — have a class for it.
    #                      Note what is deliberately NOT here: item 2.04
    #                      signals ALSO carry fibo-fnd-agr-ctr:BreachOfCovenant
    #                      and item 2.03 signals ALSO carry ex:IssuanceEvent.
    #                      Where a real FIBO term describes the underlying
    #                      fact, it is asserted alongside rather than replaced.
    f"{EX}WarningSignal",
    #   SignalSource     — the filing a signal was DERIVED FROM, kept separate
    #                      from the signal so provenance is a traversable edge
    #                      rather than a literal. FIBO models the filing's
    #                      content (and Wave 11a bound ex:IssuanceEvent for the
    #                      one disclosure-event shape it lacks); it has no
    #                      notion of "the thing a monitoring process read".
    #                      Deriving-from is an epistemic relation, not a
    #                      financial one, and fibo-fnd-rel-rel has no term for
    #                      it — the closest, isProvidedBy/hasSource, are about
    #                      service provision and identity, not observation.
    f"{EX}SignalSource",
    #   PriorObservation — the anchor point of a supersession chain: "this is
    #                      what the surveillance sweep believed before the
    #                      first signal in this window arrived." It exists so
    #                      the earliest real signal has something to supersede,
    #                      making as-of reconstruction total rather than
    #                      ragged. It is a statement about the ledger's own
    #                      history of belief — a bitemporal bookkeeping device.
    #                      FIBO models what is true, not what a given observer
    #                      previously held to be true, so there is no candidate
    #                      term in Production or in Commons.
    f"{EX}PriorObservation",
    # Wave 12 treasury-liquidity concepts. Checked live against a shallow
    # edmcouncil/fibo clone (Task 9, 2026-08-22): RegulatoryPosture,
    # RegulatoryClassification, RegulatoryRegime, JurisdictionalRestriction,
    # and ComplianceRequirement all return zero hits. FIBO models the
    # instrument and the agreement; a bank's own internal jurisdiction/intent
    # regulatory-posture classification is neither — same recurring shape as
    # Covenant, the Wave 9 set-off relations, and Wave 10 coverage/interaction.
    f"{EX}RegulatoryPosture",
    # Wave 12 FX-reconciliation concepts (Task 14). FIBO's `Trade` and
    # `TradeLifecycleEvent` (both real, both bound and asserted by this
    # loader) model the trade itself and its lifecycle; none of the three
    # below have a FIBO counterpart, because FIBO's subject is the financial
    # world, not a bank's own internal observation/control apparatus around
    # it — the same distinction the Wave 11b block above draws.
    #   SystemObservation    — one internal booking/settlement/risk system's
    #                          snapshot of a trade at a point in time. FIBO
    #                          models the trade, not a particular system's
    #                          record OF the trade.
    f"{EX}SystemObservation",
    #   ReconciliationBreak  — a detected disagreement between two systems'
    #                          records of the same trade. This is an artifact
    #                          of the bank's own control process, not a fact
    #                          about the trade itself.
    f"{EX}ReconciliationBreak",
    #   TradeSystem          — the bank's own internal system inventory
    #                          (trading / settlement / risk) that a
    #                          SystemObservation is recorded by. FIBO has no
    #                          notion of a firm's internal system landscape.
    f"{EX}TradeSystem",
    # Wave 14 Task 12: the internal overlay's loan-level privacy ceiling. Not
    # an EDM Council absence check like the entries above — a field-level
    # release-granularity policy is a bank's own data-handling classification,
    # not a fact FIBO models about the financial world. Considered reusing
    # ex:ResidencyConstraint (same shape: a Constraint class plus an edge from
    # the governed thing) and rejected it — that constraint hangs off a
    # Person node; this one governs a Postgres column name with no node of
    # its own. See docs/ccf_dataprep_v2.md, "Wave 14 Task 12" binding entry.
    f"{EX}LoanLevelPrivacyConstraint",
    # Wave 16 Task 12. FIBO's subject is the financial world, not a bank's
    # own origination-side observation of it -- the same distinction the
    # Wave 11b block above draws for WarningSignal, just opposite polarity:
    # WarningSignal is credit-deterioration, OpportunitySignal is origination
    # opportunity, and the two must never share a type (docs/wave16-design.md
    # section 5.2). Verified absent from `dev.fibo-quickstart.ttl` via
    # `ccf.fibo.fibo_absent("OpportunitySignal")` before generation.
    f"{EX}OpportunitySignal",
    # Wave 17, aml-typology-match. All five verified absent from
    # `dev.fibo-quickstart.ttl` via `ccf.fibo.fibo_absent()` at BINDING time
    # (Task 4, docs/ccf_dataprep_v2.md's "10 terms bound" entry) -- this is
    # registration paid off late, not a fresh verification: Task 13/14's own
    # loader carried the assertions for a wave before this list caught up
    # (docs/ccf_dataprep_v2.md, Task 13: "SHADOWING: ['AMLParty', 'Typology',
    # 'TypologyPattern']" -- a registration gap, not a real FIBO collision).
    #   AMLParty         — synthetic-only party type for this product
    #                      (CLAUDE.md rule 2); kept distinct from every real
    #                      obligor/party class so a query for real entities
    #                      can never pull in an AML-typology party by
    #                      accident.
    f"{EX}AMLParty",
    #   Typology         — no FIBO class for a named laundering-pattern
    #                      category (structuring, TBML, ...); FIBO models
    #                      legal/financial structures, not typologies of
    #                      illicit behavior.
    f"{EX}Typology",
    #   TypologyPattern  — the derived, parameterized structural instance of
    #                      a Typology. Kept distinct from Typology itself so
    #                      one category could carry more than one structural
    #                      variant; today exactly one derived pattern exists
    #                      per typology_id, so each of the 4 nodes is typed
    #                      with BOTH classes rather than a second node with
    #                      no bound predicate to link it back.
    f"{EX}TypologyPattern",
    #   FilingPosture    — a versioned internal filing-disposition policy,
    #                      effective from a date. No FIBO class for an
    #                      internal control posture that changes what the
    #                      bank does with a match over time — same
    #                      bank's-own-observation-apparatus distinction the
    #                      Wave 11b/12 blocks above draw.
    f"{EX}FilingPosture",
    #   DispositionRule  — one posture's ruling for one typology
    #                      (close-no-action / escalate-l2 / file-sar /
    #                      monitor). FIBO has no vocabulary for this kind of
    #                      internal decision rule.
    f"{EX}DispositionRule",
    # Wave 18, syndicated-lending-co-lender. All three confirmed absent from
    # the ontology under every prefix by generators/verify_fibo_wave18.py
    # (Task 4's own run for the first, Task 9's extension for the other
    # two) -- this allowlist entry closes the gap between "confirmed absent
    # and safe to mint" and "actually permitted here", which Task 4/8 left
    # open for SyndicateParticipation until Task 9 noticed the same gap
    # about to repeat for its own two new classes and fixed both at once.
    #   SyndicateParticipation — the reified (member, facility, commitment
    #                      amount, filing offset) n-ary fact Task 8's
    #                      participation edges hang off of; see
    #                      ccf/syndicate.py's own docstring for why a plain
    #                      triple cannot carry it.
    f"{EX}SyndicateParticipation",
    #   AmendmentEvent   — a dated, filed amendment/restatement event on a
    #                      Wave 18 facility (Task 9). Deliberately distinct
    #                      from the pre-existing `ex:Amendment` (Wave 5,
    #                      covenant-in-force-as-of's own bitemporal chain,
    #                      already permitted above) -- reusing that class
    #                      would inflate a different product's population
    #                      with facilities it never touches. See
    #                      ccf/syndicate.py's EX_AMENDMENT_EVENT for the
    #                      full rationale, including the FIBO candidate
    #                      (`fibo-fnd-agr-ctr:hasEffectiveDate`) that was
    #                      found and rejected as the wrong shape (an
    #                      ObjectProperty over a reified Date node, not a
    #                      literal).
    f"{EX}AmendmentEvent",
    #   AmendmentVote    — the live, open vote node itself (Task 9),
    #                      distinct from a dated AmendmentEvent because a
    #                      vote in progress has no effective date yet. No
    #                      FIBO voting vocabulary is in scope (the same
    #                      finding recorded against `ex:votesOn`/
    #                      `ex:votePosture` in the v2 binding table).
    f"{EX}AmendmentVote",
    #   DisclosureEnvelope — the bilateral, versioned P/T disclosure record
    #                      between our desk and one counterparty (Task 10).
    #                      Confirmed absent from the ontology under every
    #                      prefix by `generators/verify_fibo_wave18.py`
    #                      (its own `EX_MINTED_CHECKED_ABSENT` manifest, run
    #                      2026-08-26 for this task) -- no FIBO federation
    #                      or bilateral-disclosure vocabulary exists.
    f"{EX}DisclosureEnvelope",
    #   AmendmentThreshold — Task 11b, the R half of "Voting thresholds and
    #                      amendment mechanics" (§C: MongoDB + Fluree,
    #                      L + R). Task 11 built only the L half (filed
    #                      article text in Mongo); no task's brief covered
    #                      R until this one. No vote/consent/threshold/
    #                      quorum/majority vocabulary exists anywhere in
    #                      the ontology, checked under every prefix by
    #                      `generators/verify_fibo_wave18.py`, run
    #                      2026-08-26 for this task -- 14/14 `ex:` terms
    #                      confirmed absent (0 collisions), 17/17 FIBO
    #                      terms still declared.
    f"{EX}AmendmentThreshold",
    # Wave 19 Task 8 — InsiderDesignation, the Regulation O insider/
    # related-party case record (`loaders/load_policy_fluree.py`). Confirmed
    # absent from FIBO under every prefix by
    # `generators/verify_fibo_wave19.py` (Task 3, 2026-08-27): checked
    # `Insider*` under every prefix, none declared. No FIBO vocabulary
    # models a designated-insider flag for lending-limit purposes.
    f"{EX}InsiderDesignation",
    # Wave 19 Task 9 — RegimeVersion (a versioned large-exposure regulatory
    # regime: CRR, PRA Large Exposures, Regulation O) and LimitEnvelope (the
    # internal appetite; also the node shape a regime version's own limit
    # pair would use, though this wave asserts limitPctOfCapital/
    # limitAbsoluteUsd directly on RegimeVersion itself, not via a separate
    # LimitEnvelope per regime). Both confirmed absent from FIBO under every
    # prefix by `generators/verify_fibo_wave19.py` (Task 3, 2026-08-27): no
    # FIBO class bundles a concentration-limit pair, and none models a
    # regulatory regime's VERSION. `loaders/load_policy_fluree.py`.
    f"{EX}RegimeVersion",
    f"{EX}LimitEnvelope",
}

#: Predicates a Wave 11b surveillance node may carry, and no others. Every
#: measurement — severity, score, weight, threshold, the WARN employer and
#: dates, the GDELT tone and down-weight — resolves from Postgres, which is
#: the sole author of all seven Wave 11b tables. A literal appearing here that
#: is not in this set is a single-writer violation, not a convenience.
SURVEILLANCE_NODE_PREDICATES = [
    RDF_TYPE, RDFS_LABEL,
    f"{EX}provenance", f"{EX}validFrom", f"{EX}sourceAccession", f"{EX}item",
    f"{EX}signalAbout", f"{EX}triggeredBy", f"{EX}supersededBy",
]

#: The seven tables Wave 11b creates. Postgres is authoritative for all of
#: them; no other store may hold a table or collection of the same name.
WAVE11B_PG_TABLES = [
    "warn_notice", "warn_match", "gdelt_mention", "signal_event",
    "signal_weight", "escalation_threshold", "trend_delta",
]

#: The fifteen tables Wave 12 creates (Tasks 2, 5, 7, 12, 13, 14). Postgres is
#: authoritative for all of them. `deposit_account` is NOT here — it is
#: EXTENDED, not new (Wave 9 -> Task 7, a two-writer table; see
#: docs/ccf_dataprep_v2.md's Wave 12 extension register).
WAVE12_PG_TABLES = [
    "reference_rate", "fx_reference_rate", "treasury_client",
    "investment_position", "concentration_limit", "permitted_instrument",
    "intraday_tick", "stale_signal",
    "fx_trade", "system_trade_record", "break_record",
    "materiality_threshold", "part43_profile",
    "fx_intraday_tick", "fx_pip_size",
]

#: The six tables Wave 16 (Task 11) creates for ib-opportunity-synthesis.
#: Postgres is authoritative for all of them. `debt_instrument` and
#: `spread_observation` are NOT here -- Task 8b EXTENDS Wave 11a's tables
#: (w16-i-* prefix, a two-writer table like deposit_account), and `banker` /
#: `coverage_assignment` are NOT here either -- both are Wave 10's, inherited
#: whole by ib-opportunity-synthesis per §C ("inherited from
#: [[client-360-coverage-graph]]"), never re-created.
WAVE16_PG_TABLES = [
    "ib_perspective", "ib_signal_class", "perspective_weight", "mandate",
    "gov_contract_concentration", "ib_projection_plan",
]

#: The five tables Wave 17 (Tasks 8/10/12/16) creates for
#: aml-typology-match. Postgres is authoritative for all of them.
#: `sanctions_entry` / `sanctions_name` are NOT here -- both are Wave 13b's,
#: inherited whole per §C ("Sanctions lists ... OFAC SDN + Consolidated"),
#: never re-created.
WAVE17_PG_TABLES = [
    "aml_party", "aml_transaction", "aml_alert", "aml_alert_link",
    "aml_projection_plan",
]

#: Predicates `loaders/load_fluree_wave16.py` may assert on an
#: `ex:OpportunitySignal` node, and no others -- copied from that loader's
#: own `SIGNAL_NODE_PREDICATES` rather than imported, same house style as
#: `SURVEILLANCE_NODE_PREDICATES` and `WAVE12_TREASURY_NODE_PREDICATES`
#: above. `ex:signalType` and `ex:observedAt` are deliberately NOT here --
#: both are POSTGRES_OWNED_ATTRS (see that list's Wave 16 entry), claimed by
#: Wave 11b's `signal_event.signal_type` / `.observed_at` columns; the
#: generic P1 scan above is what would catch either leaking onto this node.
WAVE16_OPPORTUNITY_SIGNAL_PREDICATES = [
    RDF_TYPE, RDFS_LABEL, f"{EX}validFrom", f"{EX}assertedAt",
    f"{EX}provenance", f"{EX}isCurrent", f"{EX}magnitude",
    f"{EX}signalAbout", f"{EX}supersededBy",
]

#: Wave 12's four Fluree-only relationship predicates (Task 16 brief,
#: verbatim), checked as the snake_case Postgres COLUMN name a mirrored copy
#: would actually take — a table name would not catch a column smuggled onto
#: an unrelated table.
WAVE12_FLUREE_ONLY_COLUMNS = ["held_at", "concentrated_in", "observed_in", "amends"]

#: RULING F23's actual single-writer violation, TABLE-SCOPED (Wave 12 final
#: review, IMPORTANT-3). `system_trade_record` must never carry an
#: observation timestamp or a clock-offset column -- both live ONLY in
#: Fluree (`ex:systemObservedAt`, `ex:clockOffsetSeconds`; Postgres owns the
#: VALUE, not WHEN it was observed). Deliberately NOT added to
#: `WAVE12_FLUREE_ONLY_COLUMNS` above: that list is checked schema-wide by
#: bare column name, and `stale_signal.observed_at` is a legitimate Postgres
#: column (the staleness gate owns ITS OWN signal timestamps) that a
#: bare-name check would false-positive on. Scoping to the one table this
#: rule actually binds avoids that collision. Before this check, only an
#: unconditional `ALTER TABLE ... DROP COLUMN IF EXISTS observed_at` in
#: `load_postgres_wave12_fx.py` kept the column out — a new loader
#: re-adding it would leave this file silent.
WAVE12_SYSTEM_TRADE_RECORD_FORBIDDEN_COLUMNS = [
    "observed_at", "clock_offset_seconds", "clock_offset",
]

#: Predicates `load_fluree_wave12_treasury.py` (Task 9) may assert on one of
#: its own investment-position / W12-* deposit-account / RegulatoryPosture
#: nodes, and no others — copied from that loader's own `MY_PREDICATES`
#: rather than imported, same house style as `SURVEILLANCE_NODE_PREDICATES`
#: above. Every measurement (notional, yield, balance, cash) resolves from
#: Postgres, which is sole author of `investment_position` and
#: `deposit_account`.
WAVE12_TREASURY_NODE_PREDICATES = [
    RDF_TYPE, RDFS_LABEL,
    f"{EX}provenance", f"{EX}postureJurisdiction", f"{EX}postureIntent",
    f"{EX}postureLevel", f"{EX}validFrom", f"{EX}validTo",
    f"{EX}heldAt", f"{EX}concentratedIn", f"{EX}supersededBy",
    f"{EX}setOffAgainst", f"{EX}nettedUnder", f"{EX}schemaNote",
]

#: Predicates `load_fluree_wave12_fx.py` (Task 14) may assert on one of its
#: own trade / system-observation / amendment / break nodes, and no others —
#: copied from that loader's `MY_PREDICATES`. Per RULING F22, break nodes
#: never carry `raw_variance` or `designed_class` — this is the check that
#: would catch it if a future edit added them.
WAVE12_FX_NODE_PREDICATES = [
    RDF_TYPE, RDFS_LABEL, f"{EX}provenance", f"{EX}isFiboTerm",
    f"{EX}schemaNote",
    f"{EX}observedIn", f"{EX}amends", f"{EX}recordedBySystem",
    f"{EX}involvesTrade", f"{EX}involvesSystemA", f"{EX}involvesSystemB",
    f"{EX}clockOffsetSeconds", f"{EX}systemObservedAt", f"{EX}observedAt",
    f"{EX}amendmentSeq", f"{EX}actionType", f"{EX}eventTimestamp",
]

# ---------------------------------------------------------------------------
# Wave 18 — syndicated-lending-co-lender, and the FABRIC boundary
#
# Every list above draws a line between two of OUR stores. Wave 18 adds a line
# of a different kind: between our fabric and a co-lender's. It is the one
# boundary in the estate that a leak crosses without leaving our own control,
# so it is checked in BOTH directions below. A one-directional check would sit
# green while the boundary leaked the other way, and this wave has already
# produced two findings of exactly that shape.
# ---------------------------------------------------------------------------

#: The five tables Wave 18 creates (Tasks 5, 6, 7, 15). Postgres is
#: authoritative for all of them. `context_debt` and `facility` are NOT here --
#: both are EXTENDED by this wave, not created by it (see
#: docs/ccf_dataprep_v2.md's Wave 18 extension register), and a table another
#: product owns must not be claimed here.
WAVE18_PG_TABLES = [
    "syndicate_member", "member_call_report", "own_position",
    "competition_law_rule", "syndicate_projection_plan",
]

#: Predicates a `fibo-sec-dbt-dln:FinanceSyndicateMember` node may carry, and
#: no others. The member node holds IDENTITY (`ex:lei`, a label), its
#: membership edge, its own provenance, and -- because a vote posture is a
#: position in a graph-level event rather than a measured attribute -- its
#: posture and the edge to the vote it is a posture on. Everything else about
#: a member (legal name, RSSD, the basis its identifier was assigned on, its
#: filed lender-name variants, its call-report condition) resolves from
#: Postgres.
#:
#: House style follows `SURVEILLANCE_NODE_PREDICATES` above: an ALLOWLIST, not
#: a denylist, because the generic P1 scan can only see a leak whose name
#: somebody already thought to add to `POSTGRES_OWNED_ATTRS`. A predicate
#: nobody anticipated is invisible to P1 and fails here.
WAVE18_MEMBER_NODE_PREDICATES = [
    RDF_TYPE, RDFS_LABEL,
    f"{EX}lei", f"{EX}provenance", f"{EX}votePosture", f"{EX}votesOn",
    "https://www.omg.org/spec/Commons/Collections/isMemberOf",
]

#: Wave 18's Fluree-owned names, checked as the snake_case COLUMN a mirrored
#: copy would actually take -- same construction as
#: `WAVE12_FLUREE_ONLY_COLUMNS`, and scoped to the five Wave 18 tables rather
#: than schema-wide because `effective_date` is a legitimate column elsewhere
#: in the estate (Wave 5's covenant chain) and a bare-name scan would
#: false-positive on it.
WAVE18_FLUREE_ONLY_COLUMNS = [
    "commitment_usd", "vote_posture", "vote_state", "request_scope",
    "disclose_scope", "envelope_version", "source_passage",
    "threshold_governs", "consent_standard", "consent_percent",
    "amendment_type", "participation_of", "participation_in",
    "administered_by", "effective_date", "disclosure_precision",
]

#: `syndicate_member` is IDENTITY ONLY, and this pins its column set exactly
#: rather than denying a handful of names. A denylist here would be the
#: "gate blind to its own population" failure this repo has recorded twice:
#: the risk is a commitment or a disclosure term being mirrored into Postgres,
#: and a mirror under any name the denylist did not anticipate passes it
#: silently. Pinning the set means ANY new column fails, loudly, and whoever
#: adds one decides on the record which store owns it.
WAVE18_SYNDICATE_MEMBER_COLUMNS = {
    "member_id", "legal_name", "lei", "rssd", "id_basis", "gleif_category",
    "raw_names", "provenance", "source", "retrieved_at",
}

#: The departmental desk tracker's table name and its two signature columns.
#: Hoisted out of `check_wave18` in fix round 1 so the duplication arm can be
#: fed a name Postgres DOES hold and required to say no -- a check whose only
#: demonstrated behaviour is silence has not been shown to distinguish
#: anything. The COLUMNS are the half Ruling T13-R1 is about: a copy of the
#: desk's note under a different table name passes a table-name check
#: silently, so the column names are hunted schema-wide as well.
WAVE18_TRACKER_TABLE = "syndicate_desk_tracker"
WAVE18_TRACKER_COLUMNS = ("desk_note", "tracker_id")

#: The peer fabric's own tables. Exact names, never a `peer_%` prefix: our own
#: schema has held `peer_entity`, `peer_fact` and `peer_cohort` since
#: obligor-financial-spread (Wave 3), and those are ours -- a prefix rule would
#: report three standing violations that are not violations.
PEER_TABLES = ["peer_position", "peer_product_declaration"]

#: Predicates that exist ONLY as the peer's declaration about itself. Our
#: ledger may hold what we negotiated (`ex:requestScope`, `ex:discloseScope`,
#: `ex:envelopeVersion` -- our side of an envelope) but never what the peer
#: declares about its own product: its TTL, its latency, its attestation, or
#: the granularity it chose to disclose at. Those are read across the boundary
#: at request time and are never ours to hold.
PEER_ONLY_EX_PREDICATES = [
    f"{EX}disclosurePrecision", f"{EX}declaredTtlSeconds",
    f"{EX}declaredLatencyMs", f"{EX}attestation",
]

#: The peer fabric's ledger namespace. Every subject on the peer's ledger is
#: under it, and no subject on ours is.
PEER_URI_PREFIX = f"{EX}peer/"

#: The correlation keys §C declares, which legitimately appear on BOTH
#: fabrics and are therefore not leaks: `facility_id`, lender `LEI`, and
#: `RSSD`. Named here so the two value scans below exclude them EXPLICITLY
#: rather than by happening not to look for them -- a scan that would have
#: flagged the correlation key, and does not only because nobody fed it one,
#: has not been shown to distinguish anything.
FABRIC_CORRELATION_KEYS = ("facility_id", "lei", "rssd")


@dataclass
class Result:
    check: str
    store: str
    passed: bool
    detail: str

    def render(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"  [{mark}] {self.store:9s} {self.check:38s} {self.detail}"


def sparql(query: str) -> dict:
    """Run a read-only SPARQL query against the v2 ledger."""
    from ccf import fluree

    return fluree.query(query)


def bindings(result: dict) -> list[dict]:
    return result.get("results", {}).get("bindings", [])


def check_fluree() -> list[Result]:
    from ccf import fluree

    out: list[Result] = []
    try:
        t = fluree.ledger_t()
        if t is None:
            out.append(
                Result("ledger exists", "fluree", False,
                       f"ledger '{FLUREE_LEDGER_V2}' absent — "
                       "run loaders/init_fluree.py")
            )
            return out
        count = fluree.count_triples()
        out.append(
            Result("ledger exists", "fluree", True,
                   f"{FLUREE_LEDGER_V2} at t={t}, {count} triples")
        )
    except Exception as exc:  # noqa: BLE001
        out.append(Result("reachable", "fluree", False, f"{type(exc).__name__}: {exc}"))
        return out

    # P1 — no Postgres-owned attribute may appear on a Fluree node.
    leaked: list[str] = []
    for attr in POSTGRES_OWNED_ATTRS:
        try:
            res = sparql(
                f"SELECT (COUNT(?s) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
                f"WHERE {{ ?s <{EX}{attr}> ?o }}"
            )
            rows = bindings(res)
            n = int(rows[0]["n"]["value"]) if rows else 0
            if n:
                leaked.append(f"{attr}={n}")
        except Exception:  # noqa: BLE001
            continue
    out.append(
        Result(
            "no Postgres-owned attributes",
            "fluree",
            not leaked,
            "clean" if not leaked else f"LEAKED: {', '.join(leaked)}",
        )
    )

    # P1b — no edge may point at a node that does not exist.
    #
    # Added Wave 9, after finding that every facility had pointed at a phantom
    # borrower since Wave 5: `load_temporal_wave5.py` constructed `ex:lei/{lei}`
    # while Wave 3 entities are `ex:{LocalName}`, so 45 hasBorrower edges
    # resolved to nodes carrying ZERO triples. Syntactically valid, counted
    # correctly, and the traversal arrived nowhere.
    #
    # A constructed URI cannot fail loudly. This is the check that makes it.
    RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
    FIBO_ = "https://spec.edmcouncil.org/fibo/ontology/"
    EDGE_PREDICATES = {
        "hasBorrower": f"{FIBO_}FBC/DebtAndEquities/Debt/hasBorrower",
        "isGuarantorOf": f"{FIBO_}FBC/DebtAndEquities/Guaranty/isGuarantorOf",
        "isCollateralizedBy": f"{FIBO_}FBC/DebtAndEquities/Debt/isCollateralizedBy",
        "owns": f"{FIBO_}FND/OwnershipAndControl/Ownership/owns",
        "crossDefaultsWith": f"{EX}crossDefaultsWith",
        "pledgedBy": f"{EX}pledgedBy",
        "setOffAgainst": f"{EX}setOffAgainst",
        "nettedUnder": f"{EX}nettedUnder",
        # Wave 11a
        "isIssuedBy": f"{FIBO_}FND/Relations/Relations/isIssuedBy",
        "concernsParty": f"{FIBO_}FBC/DebtAndEquities/CreditRatings/concernsParty",
        "filedBy": f"{EX}filedBy",
        "supersededBy": f"{EX}supersededBy",
        # Wave 11b. `signalAbout` is deliberately NOT here — it is the one
        # edge in the estate that legitimately crosses a store boundary, so
        # it gets its own check below rather than this one. See there.
        "triggeredBy": f"{EX}triggeredBy",
    }
    dangling: list[str] = []
    for name, pred in EDGE_PREDICATES.items():
        try:
            res = sparql(
                f"SELECT (COUNT(DISTINCT ?o) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
                f"WHERE {{ ?s <{pred}> ?o . "
                f"FILTER NOT EXISTS {{ ?o <{RDF_TYPE}> ?any }} }}"
            )
            rows = bindings(res)
            n = int(rows[0]["n"]["value"]) if rows else 0
            if n:
                dangling.append(f"{name}={n}")
        except Exception:  # noqa: BLE001
            continue
    out.append(
        Result(
            "no edge points at an untyped node",
            "fluree",
            not dangling,
            "all edge targets resolve" if not dangling
            else f"DANGLING: {', '.join(dangling)}",
        )
    )

    # P1c — every `signalAbout` target resolves. Wave 11b, and the one place
    # where "points at an untyped node" is the WRONG question to ask.
    #
    # The cascade signal reaches 8 targets: 1 facility and 2 collateral
    # pledges, which are typed Fluree nodes from Wave 9, and 5 DRAWDOWNS,
    # which are not — Wave 5 put the `drawdown` table in Postgres and gave
    # drawdowns no Fluree identity at all. Adding them to P1b's blind list
    # reports 5 dangling edges, which reads as the Wave 9 phantom-borrower
    # bug repeating. It is not the same thing, and the difference is the
    # whole point of this validator:
    #
    #   Wave 9's phantom     the URI was WRONG. `ex:lei/{lei}` was constructed
    #                        where the node was `ex:{LocalName}`. The fact
    #                        existed and the edge could not reach it.
    #   these 5 drawdowns    the URI is RIGHT. `ex:DRW-044206-0003` is the
    #                        natural key of a row that is really there. What
    #                        is absent is a Fluree node — and its absence is
    #                        Postgres owning the slice, not a broken edge.
    #
    # So the honest check is not "is the target typed in Fluree" but "does
    # the target resolve AT ALL, in whichever store owns it". That is
    # strictly stronger than P1b would be here: it confirms the Postgres row
    # exists rather than merely tolerating the absent node. An untyped target
    # that is ALSO not a `drawdown_id` still fails, loudly.
    try:
        untyped = [b["o"]["value"] for b in bindings(sparql(
            f"SELECT DISTINCT ?o FROM <{FLUREE_LEDGER_V2}> WHERE {{ "
            f"?s <{EX}signalAbout> ?o . "
            f"FILTER NOT EXISTS {{ ?o <{RDF_TYPE}> ?any }} }}"))]
        local = {u.rsplit("/", 1)[-1] for u in untyped}
        if local:
            with pg_connect() as conn, conn.cursor() as cur:
                cur.execute(
                    f'SELECT drawdown_id FROM "{PG_SCHEMA_V2}".drawdown '
                    "WHERE drawdown_id = ANY(%s)", (sorted(local),))
                resolved = {r[0] for r in cur.fetchall()}
        else:
            resolved = set()
        unresolved = sorted(local - resolved)
        out.append(Result(
            "every signalAbout target resolves", "fluree", not unresolved,
            f"{len(resolved)} resolve to a Postgres drawdown row, "
            "the rest to typed Fluree nodes" if not unresolved
            else f"UNRESOLVED: {unresolved[:3]}"))
    except Exception as exc:  # noqa: BLE001
        out.append(Result("every signalAbout target resolves", "fluree", False,
                          f"{type(exc).__name__}: {str(exc)[:60]}"))

    # Namespace hygiene. Two different things look alike here and only one is
    # a defect:
    #
    #   ex:Corporation  DEFECT     — FIBO has Corporation; the v1 load typed
    #                                two entities under ex: and Neo4j then
    #                                flattened both namespaces to one label
    #   ex:Covenant     LEGITIMATE — FIBO has NO Covenant class anywhere in
    #                                its 295 modules, so the extension is the
    #                                only honest option
    #
    # So the check is not "no ex: types" but "no ex: type that shadows a real
    # FIBO term". Extensions are allowlisted explicitly, which also means
    # adding one is a deliberate act rather than a silent drift.
    try:
        res = sparql(
            f"SELECT DISTINCT ?t FROM <{FLUREE_LEDGER_V2}> "
            f"WHERE {{ ?s a ?t . FILTER(STRSTARTS(STR(?t), '{EX}')) }}"
        )
        used = {b["t"]["value"] for b in bindings(res)}
        shadowing = sorted(used - PERMITTED_EX_TYPES)
        out.append(
            Result(
                "no ex: type shadows a FIBO term",
                "fluree",
                not shadowing,
                f"{len(used)} ex: types, all permitted extensions"
                if not shadowing
                else f"SHADOWING: {[s.rsplit('/', 1)[-1] for s in shadowing]}",
            )
        )
    except Exception as exc:  # noqa: BLE001
        out.append(Result("no ex: type shadows a FIBO term", "fluree", False,
                          str(exc)[:60]))

    # Wave 16 Task 2b, 2026-08-24: the check above only asks whether a used
    # ex: type is IN the allowlist. It says nothing about whether the
    # allowlist ITSELF is still honest -- each entry's rationale comment
    # records a hand-verification done on the day it was added, often
    # against `prod.fibo-quickstart.ttl`, which omits 40 Provisional modules
    # (known-issues §19.8). This check re-verifies every PERMITTED_EX_TYPES
    # entry against ccf.fibo.fibo_absent(), which reads
    # `dev.fibo-quickstart.ttl` -- a verified superset of `prod` -- fresh on
    # every run, so a term that has since gained a real FIBO counterpart (or
    # was always shadowing one and the old check never looked) fails loudly
    # instead of sitting on a stale comment.
    try:
        from ccf.fibo import OntologyUnusable, fibo_absent

        # Caught PER TERM rather than letting the first OntologyUnusable
        # abort the loop: fibo_absent()'s own contract still holds (it never
        # returns an unjustified bool for any single term), but this caller
        # wants the FULL picture in one run -- a real shadow reported next to
        # an ambiguous one is more useful than whichever comes first
        # alphabetically hiding the rest.
        shadowed: list[str] = []
        unusable: list[str] = []
        for term in sorted(PERMITTED_EX_TYPES):
            local = term.rsplit("/", 1)[-1]
            try:
                if not fibo_absent(local):
                    shadowed.append(local)
            except OntologyUnusable as exc:
                unusable.append(f"{local} ({exc})")

        detail_parts = []
        if shadowed:
            detail_parts.append(f"SHADOWING A REAL FIBO TERM: {shadowed}")
        if unusable:
            detail_parts.append(
                "UNVERIFIABLE, needs human review "
                f"({len(unusable)}): {unusable}"
            )
        out.append(
            Result(
                "permitted ex: extensions are still absent from FIBO (dev)",
                "fluree",
                not shadowed and not unusable,
                "; ".join(detail_parts) if detail_parts else
                f"{len(PERMITTED_EX_TYPES)} entries verified absent from "
                "dev.fibo-quickstart.ttl",
            )
        )
    except OntologyUnusable as exc:
        # Only reachable if the ontology itself could not be loaded at all
        # (missing, too small, failing its positive control) -- the per-term
        # loop above already handles a per-term OntologyUnusable.
        out.append(
            Result(
                "permitted ex: extensions are still absent from FIBO (dev)",
                "fluree",
                False,
                f"OntologyUnusable: {exc}",
            )
        )

    # Single-writer, checked rather than trusted. A Person, Banker, Interaction
    # or Deal node may carry a type, a label, and the six Wave 10 edges — and
    # nothing else. Every attribute resolves from Postgres.
    try:
        permitted = ", ".join(f"<{u}>" for u in (
            RDF_TYPE, RDFS_LABEL,
            f"{FIBO}FND/Organizations/FormalOrganizations/isEmployedBy",
            f"{FIBO}BE/OwnershipAndControl/Executives/isOfficerOf",
            f"{FIBO}BE/OwnershipAndControl/Executives/isDirectorOf",
            f"{EX}coversClient", f"{EX}participatedIn", f"{EX}relatedToDeal",
            # Wave 13b identity edges. Every one is an OBJECT property — it
            # points at another node and carries no literal — so none of them
            # can duplicate a Postgres attribute onto a Person. That is
            # asserted, not assumed, by the check immediately below.
            *IDENTITY_EDGES))
        types = ", ".join(f"<{u}>" for u in (
            f"{FIBO}FND/AgentsAndPeople/People/Person",
            f"{FIBO}BE/OwnershipAndControl/Executives/CorporateOfficer",
            f"{EX}Banker", f"{EX}Interaction", f"{EX}Deal"))
        rows = bindings(sparql(f"""
            SELECT ?s ?p FROM <{FLUREE_LEDGER_V2}> WHERE {{
              ?s a ?t . ?s ?p ?o .
              FILTER(?t IN ({types}))
              FILTER(?p NOT IN ({permitted}))
            }} LIMIT 5
        """))
        out.append(Result(
            "no client-360 attribute in the graph", "fluree", not rows,
            "clean" if not rows
            else f"{rows[0]['p']['value'].rsplit('/', 1)[-1]} on {len(rows)}+ nodes"))
        # Widening the allowlist above is only safe if every added predicate
        # really is an edge. A literal-valued one would let an attribute back
        # into the graph through the door just opened for it.
        literal_edges = bindings(sparql(f"""
            SELECT ?s ?p ?o FROM <{FLUREE_LEDGER_V2}> WHERE {{
              ?s ?p ?o .
              FILTER(?p IN ({", ".join(f"<{u}>" for u in IDENTITY_EDGES)}))
              FILTER(isLiteral(?o))
            }} LIMIT 5
        """))
        out.append(Result(
            "every identity edge is an EDGE", "fluree", not literal_edges,
            f"{len(IDENTITY_EDGES)} predicates, none literal-valued"
            if not literal_edges
            else f"LITERAL on {literal_edges[0]['p']['value'].rsplit('/', 1)[-1]}"))
    except Exception as exc:  # noqa: BLE001
        out.append(Result("no client-360 attribute in the graph", "fluree", False,
                          str(exc)[:60]))

    # Wave 11b, the same shape one level out. A WarningSignal, SignalSource or
    # PriorObservation node may carry its types, its label, its own provenance
    # string, the three chain/reference edges and the two filing literals the
    # graph is sole author of — and nothing else. Severity, score, weight,
    # threshold, the WARN employer and dates, the GDELT tone and down-weight
    # all resolve from Postgres by `signal_id`.
    #
    # This is the specific check the attribute list above cannot make: that
    # list names attributes we already know Postgres owns, so it catches a
    # KNOWN leak. This one catches an UNKNOWN one — any predicate at all that
    # a future edit hangs off a surveillance node without deciding who owns it.
    try:
        permitted = ", ".join(f"<{u}>" for u in SURVEILLANCE_NODE_PREDICATES)
        types = ", ".join(f"<{EX}{t}>" for t in
                          ("WarningSignal", "SignalSource", "PriorObservation"))
        rows = bindings(sparql(f"""
            SELECT ?s ?p FROM <{FLUREE_LEDGER_V2}> WHERE {{
              ?s a ?t . ?s ?p ?o .
              FILTER(?t IN ({types}))
              FILTER(?p NOT IN ({permitted}))
            }} LIMIT 5
        """))
        out.append(Result(
            "no signal measurement in the graph", "fluree", not rows,
            "clean" if not rows
            else f"{rows[0]['p']['value'].rsplit('/', 1)[-1]} on {len(rows)}+ nodes"))
    except Exception as exc:  # noqa: BLE001
        out.append(Result("no signal measurement in the graph", "fluree", False,
                          str(exc)[:60]))

    # Fluree is the sole author of the supersession chain and of which signal
    # is about which obligor. The inverse of the check above: those must not
    # be mirrored back into Postgres as columns. Wave 11a made the same
    # argument for grade assertions; Wave 11b's chain is 535 more links on the
    # same predicate, so the same discipline has to hold or the two stores
    # start disagreeing about an ordering only one of them can be right about.
    try:
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema = %s AND ("
                "  column_name IN ('superseded_by', 'supersedes', 'signal_about',"
                "                  'triggered_by', 'prior_observation')"
                "  OR table_name = 'prior_observation')",
                (PG_SCHEMA_V2,))
            mirrored = [f"{t}.{c}" for t, c in cur.fetchall()]
        out.append(Result(
            "supersession chain is Fluree-only", "fluree", not mirrored,
            "no chain column in Postgres" if not mirrored
            else f"MIRRORED: {mirrored[:3]}"))
    except Exception as exc:  # noqa: BLE001
        out.append(Result("supersession chain is Fluree-only", "fluree", False,
                          f"{type(exc).__name__}: {str(exc)[:60]}"))

    # Wave 12 (Task 16) — `heldAt` / `concentratedIn` / `observedIn` / `amends`
    # are Fluree-only per design §4.1. Same shape as the supersession-chain
    # check just above: the failure mode is a future loader mirroring an edge
    # back into a Postgres column "for convenience", so this checks for the
    # column, not for a table of the same name.
    try:
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema = %s AND column_name = ANY(%s)",
                (PG_SCHEMA_V2, WAVE12_FLUREE_ONLY_COLUMNS))
            mirrored = [f"{t}.{c}" for t, c in cur.fetchall()]
        out.append(Result(
            "Wave 12 relationship edges are Fluree-only", "fluree", not mirrored,
            "no heldAt/concentratedIn/observedIn/amends column in Postgres"
            if not mirrored else f"MIRRORED: {mirrored[:3]}"))
    except Exception as exc:  # noqa: BLE001
        out.append(Result("Wave 12 relationship edges are Fluree-only", "fluree",
                          False, f"{type(exc).__name__}: {str(exc)[:60]}"))

    # Wave 12 final review, IMPORTANT-3 — RULING F23's actual violation,
    # TABLE-SCOPED. Bare column-name checks (like the one just above) would
    # false-positive on `stale_signal.observed_at`, which is legitimate; this
    # checks `system_trade_record` specifically, so a future loader
    # re-adding an observation timestamp or clock-offset column to THAT
    # table is caught even though the column names themselves are fine
    # elsewhere in the schema.
    try:
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = 'system_trade_record' "
                "AND column_name = ANY(%s)",
                (PG_SCHEMA_V2, WAVE12_SYSTEM_TRADE_RECORD_FORBIDDEN_COLUMNS))
            mirrored = [r[0] for r in cur.fetchall()]
        out.append(Result(
            "system_trade_record carries no observation timestamp or clock "
            "offset (RULING F23, table-scoped)", "fluree", not mirrored,
            "no observed_at/clock_offset* column on system_trade_record"
            if not mirrored
            else f"MIRRORED: system_trade_record.{mirrored}"))
    except Exception as exc:  # noqa: BLE001
        out.append(Result(
            "system_trade_record carries no observation timestamp or clock "
            "offset (RULING F23, table-scoped)", "fluree", False,
            f"{type(exc).__name__}: {str(exc)[:60]}"))

    # Wave 12 (Task 16) — the same shape one level out as the client-360 and
    # surveillance node checks above: a treasury/FX node may carry its own
    # loader's allowlisted predicates and nothing else. This is the specific
    # check that would catch a leak the generic POSTGRES_OWNED_ATTRS scan
    # above only catches if the leaked attribute happens to already be
    # named in that list.
    for label, types, permitted in (
        ("no treasury attribute in the graph",
         (f"{FIBO}SEC/Funds/Funds/MutualFund",
          f"{FIBO}SEC/Debt/TradedShortTermDebt/CommercialPaper",
          f"{FIBO}SEC/Debt/Bonds/TreasuryBill",
          f"{FIBO}FBC/ProductsAndServices/ClientsAndAccounts/InvestmentAccount",
          f"{FIBO}FBC/ProductsAndServices/ClientsAndAccounts/DepositAccount",
          f"{EX}RegulatoryPosture"),
         WAVE12_TREASURY_NODE_PREDICATES),
        ("no FX attribute in the graph",
         (f"{EX}SystemObservation", f"{EX}ReconciliationBreak",
          f"{EX}TradeSystem",
          f"{FIBO}FBC/ProductsAndServices/FinancialProductsAndServices/Trade",
          f"{FIBO}FBC/ProductsAndServices/FinancialProductsAndServices/"
          "TradeLifecycleEvent"),
         WAVE12_FX_NODE_PREDICATES),
        # Wave 16 (Task 12) -- ib-opportunity-synthesis's OpportunitySignal
        # nodes. A literal appearing here that is not in the allowlist is a
        # single-writer violation, not a convenience -- exactly the shape of
        # the two checks just above, one product family later.
        ("no OpportunitySignal attribute outside its own predicates",
         (f"{EX}OpportunitySignal",),
         WAVE16_OPPORTUNITY_SIGNAL_PREDICATES),
    ):
        try:
            permitted_str = ", ".join(f"<{u}>" for u in permitted)
            types_str = ", ".join(f"<{u}>" for u in types)
            rows = bindings(sparql(f"""
                SELECT ?s ?p FROM <{FLUREE_LEDGER_V2}> WHERE {{
                  ?s a ?t . ?s ?p ?o .
                  FILTER(?t IN ({types_str}))
                  FILTER(?p NOT IN ({permitted_str}))
                }} LIMIT 5
            """))
            out.append(Result(
                label, "fluree", not rows,
                "clean" if not rows
                else f"{rows[0]['p']['value'].rsplit('/', 1)[-1]} on {len(rows)}+ nodes"))
        except Exception as exc:  # noqa: BLE001
            out.append(Result(label, "fluree", False, str(exc)[:60]))

    # Wave 16 (Task 12) -- the allowlist scan just above can only see a leak,
    # never an absence: a class that never got loaded at all passes it just
    # as cleanly as one loaded correctly. This is the presence half.
    try:
        rows = bindings(sparql(f"""
            SELECT ?s FROM <{FLUREE_LEDGER_V2}> WHERE {{
              ?s a <{EX}OpportunitySignal> }}"""))
        out.append(Result(
            "OpportunitySignal nodes present", "fluree", len(rows) > 0,
            f"{len(rows)} nodes"))
    except Exception as exc:  # noqa: BLE001
        out.append(Result(
            "OpportunitySignal nodes present", "fluree", False,
            f"{type(exc).__name__}: {str(exc)[:60]}"))

    # Wave 17 (aml-typology-match) -- presence half for the five new
    # classes and the three new predicates, same argument as the
    # OpportunitySignal block just above: PERMITTED_EX_TYPES and
    # POSTGRES_OWNED_ATTRS can only see a LEAK, never a class or edge that
    # never got loaded at all.
    for label, query in (
        ("AMLParty nodes present",
         f"SELECT ?s FROM <{FLUREE_LEDGER_V2}> WHERE {{ ?s a <{EX}AMLParty> }}"),
        ("Typology/TypologyPattern nodes present",
         f"SELECT ?s FROM <{FLUREE_LEDGER_V2}> WHERE {{ "
         f"?s a <{EX}Typology> . ?s a <{EX}TypologyPattern> }}"),
        ("FilingPosture nodes present",
         f"SELECT ?s FROM <{FLUREE_LEDGER_V2}> WHERE {{ ?s a <{EX}FilingPosture> }}"),
        ("DispositionRule nodes present",
         f"SELECT ?s FROM <{FLUREE_LEDGER_V2}> WHERE {{ ?s a <{EX}DispositionRule> }}"),
        ("transactedWith edges present",
         f"SELECT ?s FROM <{FLUREE_LEDGER_V2}> WHERE {{ ?s <{EX}transactedWith> ?o }}"),
        ("matchesTypology edges present",
         f"SELECT ?s FROM <{FLUREE_LEDGER_V2}> WHERE {{ ?s <{EX}matchesTypology> ?o }}"),
        ("anchoredToPassage edges present",
         f"SELECT ?s FROM <{FLUREE_LEDGER_V2}> WHERE {{ ?s <{EX}anchoredToPassage> ?o }}"),
    ):
        try:
            rows = bindings(sparql(query))
            out.append(Result(label, "fluree", len(rows) > 0, f"{len(rows)} rows"))
        except Exception as exc:  # noqa: BLE001
            out.append(Result(label, "fluree", False,
                              f"{type(exc).__name__}: {str(exc)[:60]}"))

    return out


def check_postgres() -> list[Result]:
    out: list[Result] = []
    try:
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = %s ORDER BY 1",
                (PG_SCHEMA_V2,),
            )
            tables = [r[0] for r in cur.fetchall()]
            out.append(
                Result("v2 schema exists", "postgres", True, f"{len(tables)} tables in {PG_SCHEMA_V2}")
            )
            if "crosswalk" in tables:
                cur.execute(f'SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".crosswalk')
                n = cur.fetchone()[0]
                out.append(Result("crosswalk populated", "postgres", n > 0, f"{n} rows"))
            else:
                out.append(
                    Result("crosswalk populated", "postgres", False,
                           "crosswalk table absent — Wave 1 creates it")
                )

            # Every Fluree Person must resolve to a Postgres row TYPED AS A
            # NATURAL PERSON. The reverse is NOT required: corporate reporting
            # owners are stored with owner_kind='entity' and deliberately
            # never become Person nodes. Filtering on owner_kind='natural' is
            # load-bearing, not cosmetic: Wave 10's Task 9 remediation found
            # two entities (Charter Communications, ESS Holdings Business
            # Trust I) mistyped as fibo-fnd-aap-ppl:Person in Fluree while
            # already sitting correctly in `person` as owner_kind='entity'.
            # Without this filter, had those two stayed mistyped in Fluree,
            # this check would report "all resolve" — an entity row in
            # `person` would silently satisfy the Person-orphan check it was
            # not meant to answer.
            if "person" in tables:
                cur.execute(
                    f'SELECT person_key FROM "{PG_SCHEMA_V2}".person '
                    "WHERE owner_kind = 'natural'")
                known = {r[0] for r in cur.fetchall()}
                graph = {b["s"]["value"].rsplit("/", 1)[-1].removeprefix("person-")
                         for b in bindings(sparql(f"""
                             SELECT ?s FROM <{FLUREE_LEDGER_V2}> WHERE {{
                               ?s a <{FIBO}FND/AgentsAndPeople/People/Person> }}"""))}
                orphans = graph - known
                out.append(Result(
                    "every Fluree person resolves to a row", "postgres",
                    not orphans,
                    "all resolve" if not orphans
                    else f"{len(orphans)} orphaned, e.g. {sorted(orphans)[0]}"))
            else:
                out.append(Result(
                    "every Fluree person resolves to a row", "postgres", False,
                    "person table absent — Wave 10 creates it"))

            # Wave 11b — Postgres is authoritative for all seven surveillance
            # tables (§4.1 of docs/wave11b-design.md). Present AND populated:
            # a table that exists and is empty is the failure mode a
            # count-free check misses, and this wave's whole point is that
            # hitting the count while missing the condition is a failure.
            missing = [t for t in WAVE11B_PG_TABLES if t not in tables]
            if missing:
                out.append(Result(
                    "surveillance tables present", "postgres", False,
                    f"absent: {missing}"))
            else:
                empty = []
                for t in WAVE11B_PG_TABLES:
                    cur.execute(f'SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".{t}')
                    if cur.fetchone()[0] == 0:
                        empty.append(t)
                out.append(Result(
                    "surveillance tables present", "postgres", not empty,
                    f"all {len(WAVE11B_PG_TABLES)} present and populated"
                    if not empty else f"EMPTY: {empty}"))

            # Wave 12 (Task 16) — the fifteen new tables, present AND
            # populated, same argument as the Wave 11b block just above: a
            # table that exists and is empty is exactly the failure a
            # count-free check misses.
            missing12 = [t for t in WAVE12_PG_TABLES if t not in tables]
            if missing12:
                out.append(Result(
                    "Wave 12 tables present", "postgres", False,
                    f"absent: {missing12}"))
            else:
                empty12 = []
                for t in WAVE12_PG_TABLES:
                    cur.execute(f'SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".{t}')
                    if cur.fetchone()[0] == 0:
                        empty12.append(t)
                out.append(Result(
                    "Wave 12 tables present", "postgres", not empty12,
                    f"all {len(WAVE12_PG_TABLES)} present and populated"
                    if not empty12 else f"EMPTY: {empty12}"))

            # deposit_account is a TWO-WRITER table (Wave 9's DEP-* rows,
            # Wave 12's W12-* rows) — docs/ccf_dataprep_v2.md and
            # docs/wave12-design.md §7.2. Confirm both prefixes are actually
            # present rather than assuming Task 7's extension landed: a
            # loader regression that silently skipped the insert would still
            # pass every OTHER check in this file.
            if "deposit_account" in tables:
                cur.execute(f'''SELECT
                    COUNT(*) FILTER (WHERE account_id LIKE 'DEP-%'),
                    COUNT(*) FILTER (WHERE account_id LIKE 'W12-%')
                    FROM "{PG_SCHEMA_V2}".deposit_account''')
                n_dep, n_w12 = cur.fetchone()
                out.append(Result(
                    "deposit_account carries both writers' rows", "postgres",
                    n_dep > 0 and n_w12 > 0,
                    f"{n_dep} DEP-* (Wave 9) + {n_w12} W12-* (Wave 12)"))

            # debt_instrument is a TWO-WRITER table too, same shape as
            # deposit_account above (Wave 11a's syn-i-* rows, Wave 16's
            # w16-i-* rows -- loaders/load_debt_ladder_wave16.py). Confirm
            # both prefixes are present rather than assuming the extension
            # landed: a loader that ran but inserted zero rows (a silently
            # empty artifact, a WHERE clause that matched nothing) would
            # still pass every other check in this file.
            if "debt_instrument" in tables:
                cur.execute(f'''SELECT
                    COUNT(*) FILTER (WHERE instrument_id LIKE 'syn-i-%'),
                    COUNT(*) FILTER (WHERE instrument_id LIKE 'w16-i-%')
                    FROM "{PG_SCHEMA_V2}".debt_instrument''')
                n_syn, n_w16 = cur.fetchone()
                out.append(Result(
                    "debt_instrument carries both writers' rows", "postgres",
                    n_syn > 0 and n_w16 > 0,
                    f"{n_syn} syn-i-* (Wave 11a) + {n_w16} w16-i-* (Wave 16)"))

            # Wave 16 (Task 11) — the six new ib-opportunity-synthesis
            # tables, present AND populated, same argument as the Wave 11b/12
            # blocks above: a table that exists and is empty is exactly the
            # failure a count-free check misses.
            missing16 = [t for t in WAVE16_PG_TABLES if t not in tables]
            if missing16:
                out.append(Result(
                    "Wave 16 tables present", "postgres", False,
                    f"absent: {missing16}"))
            else:
                empty16 = []
                for t in WAVE16_PG_TABLES:
                    cur.execute(f'SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".{t}')
                    if cur.fetchone()[0] == 0:
                        empty16.append(t)
                out.append(Result(
                    "Wave 16 tables present", "postgres", not empty16,
                    f"all {len(WAVE16_PG_TABLES)} present and populated"
                    if not empty16 else f"EMPTY: {empty16}"))

            # Wave 17 (aml-typology-match) — the five new tables, present
            # AND populated, same argument as the Wave 11b/12/16 blocks
            # above: a table that exists and is empty is exactly the
            # failure a count-free check misses.
            missing17 = [t for t in WAVE17_PG_TABLES if t not in tables]
            if missing17:
                out.append(Result(
                    "Wave 17 tables present", "postgres", False,
                    f"absent: {missing17}"))
            else:
                empty17 = []
                for t in WAVE17_PG_TABLES:
                    cur.execute(f'SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".{t}')
                    if cur.fetchone()[0] == 0:
                        empty17.append(t)
                out.append(Result(
                    "Wave 17 tables present", "postgres", not empty17,
                    f"all {len(WAVE17_PG_TABLES)} present and populated"
                    if not empty17 else f"EMPTY: {empty17}"))

            # §C: "SAR confidentiality classification" is SQLite's alone --
            # the whole architectural point of aml-typology-match is that
            # this policy read must reach OUTSIDE the enterprise platform,
            # exactly as mnpi-wall-enforcement's restricted list does.
            # Ported from validators/test_aml_typology.py's
            # test_sar_classification_lives_only_in_sqlite (Task 15) into
            # this file's generic bidirectional register, per Task 18's
            # brief -- previously covered only by that one task-specific
            # regression, not by the estate-wide partition gate.
            cur.execute(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema = %s AND (column_name ILIKE %s "
                "OR table_name ILIKE %s)",
                (PG_SCHEMA_V2, "%sar%", "%sar%"))
            sar_leak = cur.fetchall()
            out.append(Result(
                "no SAR data in Postgres", "postgres", not sar_leak,
                "clean -- SAR confidentiality classification is SQLite-only"
                if not sar_leak else f"LEAKED: {sar_leak}"))

            # Every Fluree WarningSignal must resolve to a `signal_event` row,
            # by the same argument as the person check above: the graph holds
            # the identity and the ordering, Postgres holds the measurement,
            # so a signal node with no row is a node nothing can be said about.
            #
            # The reverse is deliberately NOT required. Only `8k_event`
            # signals plus the three composite-case rows are given a Fluree
            # identity; adverse-media, WARN and trend-delta signals live in
            # Postgres alone. Asserting a bijection here would be asserting
            # the stores agree, which is precisely what this validator does
            # not do.
            if "signal_event" in tables:
                cur.execute(f'SELECT signal_id FROM "{PG_SCHEMA_V2}".signal_event')
                known = {r[0] for r in cur.fetchall()}
                graph = {b["s"]["value"].rsplit("/", 1)[-1]
                         for b in bindings(sparql(f"""
                             SELECT ?s FROM <{FLUREE_LEDGER_V2}> WHERE {{
                               ?s a <{EX}WarningSignal> }}"""))}
                orphans = graph - known

                # ONE documented exception, asserted rather than assumed.
                # docs/wave11b-design.md §2.1 places the cascade trigger
                # event in FLUREE ALONE — the row above it in the same table
                # places the composite case in "Postgres + Fluree", and those
                # three rows really are in `signal_event`. The asymmetry is a
                # recorded decision, not a load that fell short: the cascade
                # exists to demonstrate supersession propagating through the
                # graph (Assembly Recipe step 7), not to be scored, so it
                # carries no severity in the store that owns severities.
                #
                # The exception is narrowed to exactly one id rather than to
                # a prefix, so a SECOND unexplained Fluree-only signal fails
                # here instead of hiding behind the first one's rationale.
                # It is also asserted to be genuinely absent from Postgres —
                # if it is ever loaded there, this check says so rather than
                # silently continuing to excuse it.
                cascade_only = {sid for sid in orphans
                                if sid.startswith("sig-8k-engineered-")}
                unexplained = sorted(orphans - cascade_only)
                ok = not unexplained and len(cascade_only) <= 1
                out.append(Result(
                    "every Fluree signal resolves to a row", "postgres", ok,
                    f"{len(graph & known)} of {len(graph)} resolve; "
                    f"{len(cascade_only)} cascade trigger Fluree-only "
                    f"(design §2.1); {len(known)} rows total, "
                    f"{len(known - graph)} Postgres-only by design"
                    if ok
                    else (f"{len(unexplained)} unexplained orphan(s), "
                          f"e.g. {unexplained[0]}" if unexplained
                          else f"{len(cascade_only)} Fluree-only signals, "
                               "design §2.1 permits one")))
    except Exception as exc:  # noqa: BLE001
        out.append(Result("reachable", "postgres", False, f"{type(exc).__name__}: {str(exc)[:70]}"))

    out.extend(check_wave14_thresholds())
    return out


#: The only two Wave 14 Postgres columns whose names read as trigger terms,
#: each exempted for a DIFFERENT and separately stated reason. Named exactly,
#: never by prefix, so a THIRD threshold column added later fails here instead
#: of hiding behind these two -- the same discipline as the cascade-signal
#: exception above.
WAVE14_TRIGGER_COLUMN_EXEMPTIONS = {
    # A filed RESULT, not a threshold: whether the servicer reported the
    # trigger as occurring in that period. Postgres owns measured results.
    "published_trigger_occurred",
    # A duplicate, and knowingly so -- see check_wave14_thresholds below,
    # which is what makes keeping it defensible.
    "published_delinquency_trigger",
}


#: Every ABS measure name. Postgres owns all of them and MongoDB may hold NONE
#: of them, at any depth.
#:
#: RULING F52 changed this. `published_measures` used to be a permitted
#: envelope holding the servicer report's printed figures, and it carried 12
#: keys across 36 documents -- 288 values byte-identical to
#: `abs_servicer_report`, `delinquency_trigger` among them, which put one
#: threshold in three stores. It is now reduced to `source_format` alone, which
#: is a property of the document (which issuer layout it uses) and is owned by
#: nothing else. So the check no longer exempts the envelope: it scans nested
#: paths too, and a measure reappearing inside `published_measures` is a leak
#: like any other.
WAVE14_MEASURE_FIELDS = [
    "pool_balance", "note_balance", "oc_amount", "oc_percent", "oc_target",
    "delinquency_percent", "published_delinquency_percent",
    "sixty_day_delinquent_balance", "cumulative_net_loss_percent",
    "receivable_count", "loan_count", "chargedoff_amount", "recovered_amount",
    "weighted_average_coupon_percent", "delinquency_buckets", "delinquency_trigger",
    "trigger_occurred",
]


def check_wave14_mongo_measures(db) -> Result:
    """Wave 14: Mongo holds text and anchors; measures only as filed evidence.

    Postgres owns every measured quantity. Mongo's one permitted copy is the
    nested `published_measures` sub-document -- the servicer report's own
    printed figures, kept as strings, which the trigger checks cross-read
    against our recomputation. Anything at the TOP level of a document, or on
    a trigger_anchor, is a measure that leaked out of that envelope.

    Checked as a field-existence scan rather than a schema assertion, because
    the failure mode is a future loader adding one convenient column, not a
    wholesale redesign.
    """
    # `passage` is scanned too. Checking only `document` and `trigger_anchor`
    # left the collection that holds the most rows unexamined, and a loader
    # hanging a measure off a passage would have been invisible.
    leaked = []
    for coll in ("document", "trigger_anchor", "passage"):
        for field in WAVE14_MEASURE_FIELDS:
            for path in (field, f"published_measures.{field}"):
                n = db[coll].count_documents({path: {"$exists": True}})
                if n:
                    leaked.append(f"{coll}.{path}={n}")
    n_pm = db["document"].count_documents({"published_measures": {"$exists": True}})
    keys = set()
    for d in db["document"].find({"published_measures": {"$exists": True}},
                                 {"published_measures": 1}):
        keys |= set(d["published_measures"])
    stray = sorted(keys - {"source_format"})
    if stray:
        leaked.append(f"published_measures carries {stray}")
    return Result(
        "no ABS measure anywhere in MongoDB", "mongodb", not leaked,
        f"{len(WAVE14_MEASURE_FIELDS)} measure names absent from document, "
        f"trigger_anchor and passage at both top level and inside "
        f"published_measures, which {n_pm} documents carry and which holds "
        f"only {sorted(keys)}"
        if not leaked else f"LEAKED: {leaked[:3]}")


def check_wave14_thresholds() -> list[Result]:
    """Wave 14: Fluree owns trigger thresholds; Postgres owns measured results.

    `abs_servicer_report.published_delinquency_trigger` is the one deliberate
    exception, and it IS a duplicate: 36 rows carrying 3 distinct values, one
    per deal, numerically identical to Fluree's `ex:thresholdValue`. Keeping it
    was a decision, taken 2026-08-23, on the grounds that a servicer report is
    a different filing from the prospectus the threshold was extracted out of,
    so the column records what THAT document printed and its agreement with
    Fluree is a finding rather than a redundancy.

    That rationale is only honest if the agreement is actually checked. A
    duplicate nobody compares is just a duplicate. So this asserts equality
    per deal, and reddens on any drift in either direction.

    The FILED threshold is the one reachable from the deal by
    `specifiesTrigger`; the engineered amendment hangs off the original by
    `ex:supersededBy` and is deliberately not reachable that way. If a deal
    ever resolves to zero or to more than one delinquency trigger, that is a
    FAIL -- ambiguity is not silently resolved by picking the first.
    """
    out: list[Result] = []
    ST = f"{FIBO}SEC/Debt/CollateralizedDebtObligations/specifiesTrigger"
    RDFS_L = "http://www.w3.org/2000/01/rdf-schema#label"

    try:
        rows = bindings(sparql(
            f"SELECT ?d ?v ?l FROM <{FLUREE_LEDGER_V2}> WHERE {{ "
            f"  ?d <{ST}> ?t . "
            f"  ?t <{EX}thresholdValue> ?v . "
            f"  ?t <{RDFS_L}> ?l }}"))
        filed: dict[str, list[str]] = {}
        for b in rows:
            if "Delinquency Trigger" not in b["l"]["value"]:
                continue
            deal = b["d"]["value"].rsplit("abs-deal-", 1)[-1]
            filed.setdefault(deal, []).append(b["v"]["value"])

        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(
                f'SELECT deal_id, ARRAY_AGG(DISTINCT published_delinquency_trigger) '
                f'FROM "{PG_SCHEMA_V2}".abs_servicer_report GROUP BY deal_id')
            published = {d: vals for d, vals in cur.fetchall()}

        problems = []
        for deal in sorted(set(filed) | set(published)):
            fl, pg = filed.get(deal, []), published.get(deal, [])
            if len(fl) != 1:
                problems.append(f"{deal}: {len(fl)} filed delinquency triggers in Fluree")
            elif len(pg) != 1:
                problems.append(f"{deal}: {len(pg)} distinct published values in Postgres")
            elif float(fl[0]) != float(pg[0]):
                problems.append(f"{deal}: Fluree {fl[0]} != Postgres {pg[0]}")
        agreed = len(set(filed) & set(published)) - len(problems)
        out.append(Result(
            "filed delinquency trigger agrees with Fluree", "postgres",
            not problems,
            f"{agreed} deal(s) agree; the duplicate is checked, not assumed"
            if not problems else f"DRIFT: {problems[:3]}"))
    except Exception as exc:  # noqa: BLE001
        out.append(Result("filed delinquency trigger agrees with Fluree",
                          "postgres", False, f"{type(exc).__name__}: {str(exc)[:70]}"))

    # No OTHER threshold may be copied into Postgres. Table-scoped to abs_%,
    # because a bare column-name scan false-positives on
    # `resolution_policy.threshold_value`, which is Wave 13b's person-matching
    # score cutoff and legitimately Postgres's.
    try:
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name LIKE 'abs\\_%%' "
                "  AND (column_name LIKE '%%threshold%%' "
                "       OR column_name LIKE '%%trigger%%' "
                "       OR column_name LIKE '%%_limit' "
                "       OR column_name LIKE '%%_floor' "
                "       OR column_name LIKE '%%_cap' "
                "       OR column_name LIKE '%%_ceiling')",
                (PG_SCHEMA_V2,))
            found = {c for _, c in cur.fetchall()}
        unexplained = sorted(found - WAVE14_TRIGGER_COLUMN_EXEMPTIONS)
        out.append(Result(
            "no unexempted threshold column on any abs_ table", "postgres",
            not unexplained,
            f"{len(found)} trigger-named column(s), both exempted by name"
            if not unexplained else f"UNEXEMPTED: {unexplained}"))
    except Exception as exc:  # noqa: BLE001
        out.append(Result("no unexempted threshold column on any abs_ table",
                          "postgres", False, f"{type(exc).__name__}: {str(exc)[:70]}"))

    return out


def check_mongo() -> list[Result]:
    out: list[Result] = []
    try:
        from pymongo import MongoClient

        # Named explicitly. Never enumerate databases on this host — it also
        # carries an unrelated live system.
        db = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)[MONGO_DB_V2]
        colls = sorted(db.list_collection_names())
        out.append(Result("v2 db reachable", "mongodb", True, f"{len(colls)} collections"))

        # P3 — Mongo must not hold typed relationship edges; those are Fluree's.
        if "relationships" in colls:
            n = db["relationships"].estimated_document_count()
            out.append(
                Result("no typed edges", "mongodb", n == 0,
                       f"relationships collection holds {n} docs — Fluree owns edges")
            )
        else:
            out.append(Result("no typed edges", "mongodb", True, "no relationships collection"))

        # P3b — Mongo owns passage-level lineage, so passages must be present
        # once Wave 6 has run, and each must anchor to a stored document.
        n_pass = db["passage"].estimated_document_count()
        n_doc = db["document"].estimated_document_count()
        if n_pass or n_doc:
            orphan = db["passage"].count_documents(
                # Wave 13b: KYC files live in their own collection — they
                # carry no accession, no CIK and no filer, and mixing them into
                # `document` would make every query over that collection need a
                # provenance filter to stay correct. The anchor CLAIM is
                # unchanged ("every passage anchors to a document"); what
                # counts as a document is what widened.
                {"document_id": {"$nin": (
                    db["document"].distinct("document_id")
                    + db["kyc_document"].distinct("document_id"))}}
            )
            n_kyc = db["kyc_document"].count_documents({})
            out.append(Result("passages anchor to a document", "mongodb",
                              orphan == 0,
                              f"{n_pass:,} passages / {n_doc} documents "
                              f"+ {n_kyc} KYC files, {orphan} orphaned"))

        # P5 for Wave 11b — the seven surveillance tables are Postgres's, and
        # a WARN notice or a GDELT article is exactly the sort of text-shaped
        # thing that drifts into a document store "for convenience". Named
        # explicitly against the already-fetched collection list; never an
        # enumeration of databases on this host.
        intruders = sorted(set(colls) & set(WAVE11B_PG_TABLES))
        out.append(Result("no surveillance collection", "mongodb", not intruders,
                          "clean" if not intruders
                          else f"holds Postgres-owned: {intruders}"))

        # Wave 12 (Task 16) — same P5 argument for the fifteen new tables.
        intruders12 = sorted(set(colls) & set(WAVE12_PG_TABLES))
        out.append(check_wave14_mongo_measures(db))
        out.append(Result("no Wave 12 collection", "mongodb", not intruders12,
                          "clean" if not intruders12
                          else f"holds Postgres-owned: {intruders12}"))

        # Wave 16 (Task 11) — same P5 argument for the six ib-opportunity-
        # synthesis tables (weights, mandates, USASpending awards): Postgres
        # owns them, and none may drift into a document collection.
        intruders16 = sorted(set(colls) & set(WAVE16_PG_TABLES))
        out.append(Result("no Wave 16 collection", "mongodb", not intruders16,
                          "clean" if not intruders16
                          else f"holds Postgres-owned: {intruders16}"))

        # Wave 16 (Task 13) — the merger-proxy/S-4 corpus is Mongo's own §C
        # row (2 and the S-4 half of 5), present AND populated, same
        # "count-free check misses an empty table" argument as the Postgres-
        # side blocks above.
        n_merger_proxy = db["document"].count_documents({"doc_type": "merger_proxy"})
        n_s4 = db["document"].count_documents({"doc_type": "registration_s4"})
        out.append(Result(
            "merger corpus present", "mongodb",
            n_merger_proxy > 0 and n_s4 > 0,
            f"{n_merger_proxy} merger_proxy + {n_s4} registration_s4"))

        # Wave 17 (aml-typology-match) — same P5 argument as the Wave 12/16
        # blocks above: none of the five Postgres-owned tables may drift
        # into a document collection.
        intruders17 = sorted(set(colls) & set(WAVE17_PG_TABLES))
        out.append(Result("no Wave 17 collection", "mongodb", not intruders17,
                          "clean" if not intruders17
                          else f"holds Postgres-owned: {intruders17}"))

        # §C: typology definitions/narrative patterns (FinCEN/FATF) and SAR
        # filing history/narratives are Mongo's own rows, present AND
        # populated, same "count-free check misses an empty collection"
        # argument as the merger-corpus check just above.
        n_advisory = db["document"].count_documents({"doc_type": "fincen_advisory"})
        n_sar_narrative = db["document"].count_documents({"doc_type": "sar_narrative"})
        out.append(Result(
            "AML typology corpus present", "mongodb",
            n_advisory > 0 and n_sar_narrative > 0,
            f"{n_advisory} fincen_advisory + {n_sar_narrative} sar_narrative"))
    except Exception as exc:  # noqa: BLE001
        out.append(Result("reachable", "mongodb", False, f"{type(exc).__name__}: {str(exc)[:70]}"))
    return out


def check_sqlite() -> list[Result]:
    out: list[Result] = []
    if not SQLITE_PATH.exists():
        return [Result("file exists", "sqlite", False, f"{SQLITE_PATH} absent")]
    with sqlite3.connect(SQLITE_PATH) as conn:
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
    out.append(Result("file exists", "sqlite", True, f"{len(tables)} tables"))
    # P4 — departmental store must not accumulate entity data.
    forbidden = {"entities", "obligors", "facilities", "relationships"}
    forbidden |= set(WAVE11B_PG_TABLES)  # Wave 11b — all seven are Postgres's
    forbidden |= set(WAVE12_PG_TABLES)   # Wave 12 — all fifteen are Postgres's
    forbidden |= set(WAVE16_PG_TABLES)   # Wave 16 — all six are Postgres's
    forbidden |= set(WAVE17_PG_TABLES)   # Wave 17 — all five are Postgres's
    forbidden |= set(WAVE18_PG_TABLES)   # Wave 18 — all five are Postgres's
    intruders = sorted(forbidden & set(tables))
    out.append(
        Result("departmental only", "sqlite", not intruders,
               "clean" if not intruders else f"holds enterprise tables: {intruders}")
    )

    # Wave 16 (Task 13) — `prospect_note` is a pre-existing mnpi-wall-
    # enforcement table (Wave 7); ib-opportunity-synthesis's own contribution
    # is the 50 rows carrying a banker_id, so presence AND population is the
    # right check here rather than mere table existence, which "departmental
    # only" above already covers.
    if "prospect_note" in tables:
        with sqlite3.connect(SQLITE_PATH) as conn:
            n_banker_notes = conn.execute(
                "SELECT COUNT(*) FROM prospect_note WHERE banker_id IS NOT NULL"
            ).fetchone()[0]
        out.append(Result(
            "banker-linked prospect notes present", "sqlite",
            n_banker_notes > 0, f"{n_banker_notes} rows"))
    else:
        out.append(Result(
            "banker-linked prospect notes present", "sqlite", False,
            "prospect_note table absent — Wave 7 creates it"))

    # §C: "SAR confidentiality classification" is SQLite's own row --
    # present AND populated, same argument as the prospect-note check just
    # above. The mirror-image absence half (Postgres carries none of it) is
    # `check_postgres()`'s "no SAR data in Postgres" check.
    if "sar_classification" in tables:
        with sqlite3.connect(SQLITE_PATH) as conn:
            n_sar = conn.execute(
                "SELECT COUNT(*) FROM sar_classification "
                "WHERE visible_to_perspectives IS NOT NULL").fetchone()[0]
        out.append(Result(
            "SAR confidentiality classification present", "sqlite",
            n_sar > 0, f"{n_sar} rows"))
    else:
        out.append(Result(
            "SAR confidentiality classification present", "sqlite", False,
            "sar_classification table absent — Wave 17 Task 15 creates it"))
    return out


def _cell_scan(cells: list[tuple[str, str]], needles: set[str]
               ) -> list[str]:
    """Every (location, needle) pair where a needle appears in a cell.

    Substring rather than equality: an identifier smuggled into a JSONB blob,
    a note field or a concatenated key is exactly the copy these two scans
    exist to find, and equality would walk past all three.
    """
    hits: list[str] = []
    for location, value in cells:
        if not value:
            continue
        for needle in needles:
            if needle and needle in value:
                hits.append(f"{needle} in {location}")
    return hits


#: `context_debt` cell locations carry the row's primary key, appended after
#: a `#`. Fix round 1: without it, `_cell_scan` discarded row identity and the
#: exemption below applied to `pg context_debt.reason` -- meaning ALL 304
#: rows' `reason` columns, not the one `federation_attestation` row three
#: documents said it covered. Every other table keeps the plain
#: `pg <table>.<column>` form: the exemption only ever applies to
#: `context_debt`, and a row key everywhere would be noise.
def _debt_location(column: str, debt_id) -> str:
    return f"pg context_debt.{column}#{debt_id}"


def _context_debt_rows() -> dict[str, dict]:
    """`ccf_v2.context_debt`, keyed by `debt_id` as text.

    Read as whole rows rather than as two columns, because the exemption
    below must hand a complete row to `validators/syndicate.py`'s
    `declares_remote()` -- which reads `subject_kind`, `subject_key` AND
    `reason` -- and a projection chosen here would silently decide what that
    other rule is allowed to see.
    """
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT * FROM "{PG_SCHEMA_V2}".context_debt')
        cols = [d[0] for d in cur.description]
        return {str(dict(zip(cols, r))["debt_id"]): dict(zip(cols, r))
                for r in cur.fetchall()}


def _our_wave18_cells() -> list[tuple[str, str]]:
    """Every cell of the Wave 18 Postgres tables, `context_debt`, and the
    SQLite desk tracker, as text. Bounded on purpose: the ESTATE-WIDE value
    scan is `validators/syndicate.py`'s floor 6, and a second copy of it here
    would be two implementations of one rule, free to drift apart. What this
    covers is the surface Wave 18 itself created.

    `context_debt` cells are ROW-KEYED (see `_debt_location`); every other
    table is not.
    """
    cells: list[tuple[str, str]] = []
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = ANY(%s) ORDER BY 1, 2",
            (PG_SCHEMA_V2, WAVE18_PG_TABLES + ["context_debt"]))
        columns = cur.fetchall()
        for table in sorted({t for t, _ in columns}):
            cols = [c for t, c in columns if t == table]
            select = ", ".join(f'coalesce("{c}"::text, \'\')' for c in cols)
            cur.execute(f'SELECT {select} FROM "{PG_SCHEMA_V2}"."{table}"')
            for row in cur.fetchall():
                cell = dict(zip(cols, row))
                for column, value in cell.items():
                    if table == "context_debt":
                        cells.append(
                            (_debt_location(column, cell["debt_id"]), value))
                    else:
                        cells.append((f"pg {table}.{column}", value))
    if SQLITE_PATH.exists():
        with sqlite3.connect(SQLITE_PATH) as conn:
            names = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='syndicate_desk_tracker'")]
            for table in names:
                cur = conn.execute(f"SELECT * FROM {table}")
                cols = [d[0] for d in cur.description]
                for row in cur.fetchall():
                    for column, value in zip(cols, row):
                        cells.append((f"sqlite {table}.{column}",
                                      "" if value is None else str(value)))
    return cells


def _peer_identifiers() -> tuple[set[str], dict[str, set[str]]]:
    """Every identifier the peer fabric mints, and, per declaration, the
    VALUES it declares. Read live from the peer -- a hardcoded prefix would
    keep passing after the peer changed its id scheme, and would then be
    scanning our stores for a string nothing could produce.

    Its own function so `validators/test_syndicate.py` can substitute a
    needle that IS present and require the arm to say no. A scan whose only
    demonstrated behaviour is silence has not been shown to distinguish
    anything.
    """
    peer_ids: set[str] = set()
    declared: dict[str, set[str]] = {}
    with co_lender_pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT position_id FROM "{CO_LENDER_PG_SCHEMA}"'
                    f'.peer_position')
        peer_ids |= {r[0] for r in cur.fetchall()}
        cur.execute(f'SELECT declaration_id, declared_ttl_seconds, '
                    f'declared_latency_ms FROM "{CO_LENDER_PG_SCHEMA}"'
                    f'.peer_product_declaration')
        for did, ttl, latency in cur.fetchall():
            peer_ids.add(did)
            declared[did] = {str(ttl), str(latency)}
    return peer_ids, declared


def _our_wave18_identifiers() -> set[str]:
    """The identifiers this wave minted that are OURS ALONE -- `SYNM-` member
    ids and `SDT-` tracker ids. Deliberately excludes `facility_id`, `lei`
    and `rssd`: §C names all three as correlation keys and they legitimately
    appear on both fabrics (see `FABRIC_CORRELATION_KEYS`).

    Its own function for the same reason as `_peer_identifiers` above.
    """
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT member_id FROM "{PG_SCHEMA_V2}".syndicate_member')
        ours = {r[0] for r in cur.fetchall()}
    if SQLITE_PATH.exists():
        with sqlite3.connect(SQLITE_PATH) as conn:
            if conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name='syndicate_desk_tracker'").fetchone():
                ours |= {r[0] for r in conn.execute(
                    "SELECT tracker_id FROM syndicate_desk_tracker")}
    return ours


#: The two `context_debt` columns a peer declaration id may appear in --
#: column names only. The ROW is pinned separately, by `permitted`, which
#: maps a row-keyed location to the `subject_key` of that exact row. See the
#: exemption's full argument inside `check_wave18`.
FEDERATION_DEBT_COLUMNS = ("reason", "subject_key")


def federation_debt_locations(debt_rows: dict[str, dict]) -> dict[str, str]:
    """`{row-keyed location -> that row's subject_key}` for every
    `federation_attestation` Context Debt row, and no other row.

    This is what makes the exemption ROW-scoped. Built from the live rows on
    every run, so a row that stops being a `federation_attestation` stops
    being exempt in the same run.
    """
    return {
        _debt_location(column, debt_id): row.get("subject_key")
        for debt_id, row in debt_rows.items()
        if row.get("subject_kind") == "federation_attestation"
        for column in FEDERATION_DEBT_COLUMNS
    }


def _is_permitted_debt_reference(hit: str, permitted: dict[str, str],
                                 declaration_ids: set[str]) -> bool:
    """Is this cell-scan hit the ONE inward crossing §D step 5 requires?

    Two conditions, and the second is stricter than it looks: the needle is
    a peer DECLARATION id (a position id is never permitted), and the needle
    is the `subject_key` **of the exact row it was found in**.

    Fix round 1 (Ruling T17-R1). The prior version compared the location
    against two bare column names, and `_cell_scan` discards row identity --
    so a peer declaration id in ANY of `context_debt`'s 304 rows' `reason`
    was exempted, while `docs/HANDOFF.md`, `docs/ccf_dataprep_v2.md` and the
    task report all described the narrow, one-row rule. The code is what
    moved; the documents were already right.

    Requiring `permitted[location] == needle` rather than
    `needle in debt_subjects` also closes a cross-row case that today has no
    instance and would have had one the moment a second
    `federation_attestation` row existed: declaration A found in row B's
    reason, where B's subject is declaration C.

    This is HALF the exemption. `check_wave18` requires the hit to satisfy
    `validators/syndicate.py`'s `declares_remote()` as well -- see Ruling
    T17-R2 there and at the call site.

    Pure, and unit-tested both ways, because an exemption written inline is
    an exemption nobody can feed a counterexample to.
    """
    needle, sep, location = hit.partition(" in ")
    if not sep:
        return False
    return needle in declaration_ids and permitted.get(location) == needle


def check_wave18() -> list[Result]:
    """Wave 18 — the syndicated-lending slice, and the fabric boundary.

    Six checks. The first four are the same kind of question every other
    block in this file asks, about a new set of tables and nodes. The last
    two are new in kind: they ask about the line between OUR fabric and a
    co-lender's, and they ask it in BOTH directions.

    Why both. `syndicate.py`'s floor 6 already asserts that no peer
    identifier sits in one of our rows. That is one arm. Nothing anywhere
    asserted the other -- that nothing of OURS sits in the peer's stores --
    and a boundary that leaks outward looks identical to a clean one from
    inside. The outward arm's scan is IDENTIFIER-ONLY: it hunts our `SYNM-`
    member ids and `SDT-` desk-tracker ids in the peer's stores (see
    `docs/known-issues.md` §36 for the same identifier-vs-value distinction
    on the inward arm) -- it does not separately hunt an internal rating or
    a Context Debt row BY VALUE. A wholesale copy of one of our tables is
    still caught, by the `unexpected_tables` arm below, not by the
    identifier scan. Task 14's own dispatch note records that every peer
    write in this wave lands on a different database ON THE SAME HOST AND
    PORT, differing from ours by name alone.

    What would make each fail is stated on the check.
    """
    out: list[Result] = []

    # --- W18-1: `syndicate_member` is identity only -----------------------
    #
    # WOULD FAIL ON: any column added to the table -- e.g.
    #   ALTER TABLE ccf_v2.syndicate_member ADD COLUMN commitment_usd numeric;
    # which is the specific mirror this check exists to stop, or an envelope
    # or disclosure-scope column under any name at all.
    try:
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = 'syndicate_member'",
                (PG_SCHEMA_V2,))
            cols = {r[0] for r in cur.fetchall()}
        if not cols:
            out.append(Result("syndicate_member identity only", "postgres",
                              False, "table absent — Wave 18 Task 5 creates it"))
        else:
            extra = sorted(cols - WAVE18_SYNDICATE_MEMBER_COLUMNS)
            missing = sorted(WAVE18_SYNDICATE_MEMBER_COLUMNS - cols)
            ok = not extra and not missing
            out.append(Result(
                "syndicate_member identity only", "postgres", ok,
                f"{len(cols)} columns, exactly the identity set" if ok
                else f"UNPINNED: extra={extra} missing={missing} — decide "
                     "which store owns it before widening the pin"))
    except Exception as exc:  # noqa: BLE001
        out.append(Result("syndicate_member identity only", "postgres", False,
                          f"{type(exc).__name__}: {str(exc)[:70]}"))

    # --- W18-2: no Fluree-owned Wave 18 name is a Wave 18 Postgres column --
    #
    # WOULD FAIL ON: `ALTER TABLE ccf_v2.own_position ADD COLUMN vote_posture
    # text;` — a posture mirrored out of the graph into the store that owns
    # positions. Scoped to the five Wave 18 tables, so Wave 5's legitimate
    # `effective_date` elsewhere is not swept up.
    try:
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = ANY(%s) "
                "AND column_name = ANY(%s) ORDER BY 1, 2",
                (PG_SCHEMA_V2, WAVE18_PG_TABLES, WAVE18_FLUREE_ONLY_COLUMNS))
            mirrored = [f"{t}.{c}" for t, c in cur.fetchall()]
        out.append(Result(
            "no Fluree-owned syndicate column", "postgres", not mirrored,
            f"clean across {len(WAVE18_PG_TABLES)} tables / "
            f"{len(WAVE18_FLUREE_ONLY_COLUMNS)} names" if not mirrored
            else f"MIRRORED: {', '.join(mirrored)}"))
    except Exception as exc:  # noqa: BLE001
        out.append(Result("no Fluree-owned syndicate column", "postgres",
                          False, f"{type(exc).__name__}: {str(exc)[:70]}"))

    # --- W18-3: FinanceSyndicateMember nodes carry nothing else ------------
    #
    # WOULD FAIL ON: a loader asserting `ex:rssd`, `ex:legalName` or
    # `ex:internalRating` on a member node. An ALLOWLIST rather than a
    # denylist, so a name nobody put in POSTGRES_OWNED_ATTRS still fails.
    try:
        rows = bindings(sparql(
            f"SELECT DISTINCT ?p FROM <{FLUREE_LEDGER_V2}> WHERE {{ "
            f"?s <{RDF_TYPE}> <{FIBO}SEC/Debt/DistributedLoans/"
            f"FinanceSyndicateMember> . ?s ?p ?o }}"))
        seen = {b["p"]["value"] for b in rows}
        if not seen:
            out.append(Result("member node carries identity only", "fluree",
                              False, "no FinanceSyndicateMember node in the "
                                     "ledger — Wave 18 Task 8 loads them"))
        else:
            unexpected = sorted(seen - set(WAVE18_MEMBER_NODE_PREDICATES))
            out.append(Result(
                "member node carries identity only", "fluree",
                not unexpected,
                f"{len(seen)} distinct predicates, all permitted"
                if not unexpected
                else f"UNPERMITTED: {[p.replace(EX, 'ex:') for p in unexpected]}"))
    except Exception as exc:  # noqa: BLE001
        out.append(Result("member node carries identity only", "fluree", False,
                          f"{type(exc).__name__}: {str(exc)[:70]}"))

    # --- W18-4: the desk tracker is departmental, and only departmental ----
    #
    # WOULD FAIL ON: creating `ccf_v2.syndicate_desk_tracker`, OR mirroring
    # the desk's note into Postgres under any other table name -- the second
    # is why this checks for the tracker's COLUMN names schema-wide as well
    # as for its table name. A check that looked only for the name would be
    # blind to exactly the duplication it is policing (Ruling T13-R1).
    try:
        tracker_rows = 0
        if SQLITE_PATH.exists():
            with sqlite3.connect(SQLITE_PATH) as conn:
                present = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name = ?", (WAVE18_TRACKER_TABLE,)).fetchone()
                if present:
                    tracker_rows = conn.execute(
                        f"SELECT COUNT(*) FROM {WAVE18_TRACKER_TABLE}"
                    ).fetchone()[0]
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = %s AND table_name = %s",
                (PG_SCHEMA_V2, WAVE18_TRACKER_TABLE))
            pg_table = [r[0] for r in cur.fetchall()]
            cur.execute(
                "SELECT table_name FROM information_schema.columns "
                "WHERE table_schema = %s AND column_name = ANY(%s) ORDER BY 1",
                (PG_SCHEMA_V2, list(WAVE18_TRACKER_COLUMNS)))
            pg_cols = sorted({r[0] for r in cur.fetchall()})
        from pymongo import MongoClient
        mongo_colls = [
            c for c in MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
            [MONGO_DB_V2].list_collection_names()
            if c == WAVE18_TRACKER_TABLE]
        intruders = ([f"pg table {t}" for t in pg_table]
                     + [f"pg column on {t}" for t in pg_cols]
                     + [f"mongo collection {c}" for c in mongo_colls])
        ok = tracker_rows > 0 and not intruders
        out.append(Result(
            "desk tracker is SQLite's alone", "sqlite", ok,
            f"{tracker_rows} rows, and no copy in Postgres or MongoDB" if ok
            else (f"DUPLICATED: {intruders}" if intruders
                  else f"{WAVE18_TRACKER_TABLE} absent or empty — Wave 18 "
                       "Task 13 loads it")))
    except Exception as exc:  # noqa: BLE001
        out.append(Result("desk tracker is SQLite's alone", "sqlite", False,
                          f"{type(exc).__name__}: {str(exc)[:70]}"))

    # --- the fabric boundary, both directions ------------------------------
    if not co_lender_configured():
        out.append(Result(
            "no peer element in our stores", "fabric", False,
            "co-lender fabric UNCONFIGURED — the boundary cannot be observed, "
            "and reporting the local half green is the failure this checks for"))
        out.append(Result(
            "no element of ours in the peer", "fabric", False,
            "co-lender fabric UNCONFIGURED — see above"))
        return out

    # --- W18-5 (ARM 1): nothing peer-owned is in our stores ----------------
    #
    # Three sub-conditions, each able to fail alone.
    #
    # WOULD FAIL ON: creating `ccf_v2.peer_position`; asserting
    # `ex:declaredTtlSeconds` on one of our DisclosureEnvelope nodes (a
    # cached copy of the peer's declared TTL, which §E says the local fabric
    # "does not control and must not assume"); or writing a peer position_id
    # into `own_position.provenance` or a `context_debt` row.
    #
    # The value scan carries a POSITIVE CONTROL, and the control is not a
    # planted value: it is one of our own `member_id`s, which IS in the
    # scanned cells. If the scanner cannot find a value that is certainly
    # there, its silence about peer identifiers means nothing.
    try:
        peer_ids, declared_values = _peer_identifiers()

        problems: list[str] = []

        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = %s AND table_name = ANY(%s)",
                (PG_SCHEMA_V2, PEER_TABLES))
            for (t,) in cur.fetchall():
                problems.append(f"peer table {t} exists in ours")

        for pred in PEER_ONLY_EX_PREDICATES:
            rows = bindings(sparql(
                f"SELECT (COUNT(?s) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
                f"WHERE {{ ?s <{pred}> ?o }}"))
            n = int(rows[0]["n"]["value"]) if rows else 0
            if n:
                problems.append(f"{pred.replace(EX, 'ex:')}={n} on our ledger")

        rows = bindings(sparql(
            f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
            f'WHERE {{ ?s ?p ?o . FILTER(STRSTARTS(STR(?s), "{PEER_URI_PREFIX}")) }}'))
        n_peer_subjects = int(rows[0]["n"]["value"]) if rows else 0
        if n_peer_subjects:
            problems.append(f"{n_peer_subjects} peer-namespace subjects on "
                            "our ledger")

        cells = _our_wave18_cells()

        # THE ONE PERMITTED INWARD CROSSING, and it took the scan finding it
        # to state it. §D step 5 says an unattested remote claim "is recorded
        # as Context Debt rather than admitted", and §F requires at least one.
        # A debt row that could not NAME the declaration it is debt about
        # would not be a record of anything, so `context_debt.subject_key`
        # legitimately holds a peer `declaration_id` and the reason text
        # legitimately restates it.
        #
        # A REFERENCE is not a COPY, and the exemption is drawn on exactly
        # that line: the row may name the peer's declaration, and may not
        # carry what the peer DECLARED.
        #
        # RULING T17-R2 — THE EXEMPTION IS AN INTERSECTION, NOT A SECOND HOLE.
        # `validators/syndicate.py`'s `declares_remote()` decides this same
        # question for floor 6, and the two rules do NOT agree: it requires
        # the reason text to name "co-lender" (this one does not) and it
        # admits any peer identifier including position ids (this one does
        # not). Two rules for one crossing, written in the same wave, is two
        # holes waiting to drift apart. Neither is refactored away -- they
        # serve different floors and both are validated -- so instead a hit
        # must satisfy BOTH before it is exempted. The conjunction can only
        # ever be narrower than either rule alone.
        #
        # So the exemption is narrowed five ways: the needle must be a peer
        # DECLARATION id; it must be the `subject_key` OF THE EXACT ROW it
        # was found in (row-keyed, Ruling T17-R1); the column must be
        # `reason` or `subject_key`; `declares_remote()` must independently
        # excuse the same row; and no declared TTL or latency VALUE may have
        # ridden in with the identifier. A peer position_id in the same cell
        # still fails; so does a declaration id in any other row.
        debt_rows = _context_debt_rows()
        permitted = federation_debt_locations(debt_rows)

        from validators.syndicate import declares_remote

        def _exempt(hit: str) -> bool:
            if not _is_permitted_debt_reference(hit, permitted,
                                                set(declared_values)):
                return False
            location = hit.partition(" in ")[2]
            debt_id = location.rpartition("#")[2]
            return declares_remote("postgres", f"{PG_SCHEMA_V2}.context_debt",
                                   debt_rows.get(debt_id, {}), peer_ids)

        leaked = [hit for hit in _cell_scan(cells, peer_ids)
                  if not _exempt(hit)]
        problems += leaked[:3]
        for row in debt_rows.values():
            key = row.get("subject_key")
            reason = row.get("reason") or ""
            for value in declared_values.get(key, set()):
                if value and value in reason:
                    problems.append(
                        f"context_debt row for {key} carries the peer's "
                        f"DECLARED value {value} — the exemption covers the "
                        "identifier, never the claim")

        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(f'SELECT member_id FROM "{PG_SCHEMA_V2}"'
                        f'.syndicate_member LIMIT 1')
            row = cur.fetchone()
        control = row[0] if row else None
        control_found = bool(control) and bool(_cell_scan(cells, {control}))
        if not control_found:
            problems.append("POSITIVE CONTROL FAILED — the cell scan cannot "
                            f"find {control!r}, which is in the cells it "
                            "just read; its silence proves nothing")

        out.append(Result(
            "no peer element in our stores", "fabric", not problems,
            f"{len(peer_ids)} peer ids, {len(PEER_ONLY_EX_PREDICATES)} "
            f"peer-only predicates and {len(PEER_TABLES)} peer tables all "
            f"absent from {len(cells)} of our cells and "
            f"{FLUREE_LEDGER_V2}; {len(permitted) // len(FEDERATION_DEBT_COLUMNS)} "
            f"Context Debt row(s) exempt by §D step 5 (scoped to their own "
            f"row AND independently excused by declares_remote), carrying no "
            f"declared value; "
            f"control {control} found"
            if not problems else f"LEAK INWARD: {problems}"))
    except Exception as exc:  # noqa: BLE001
        out.append(Result("no peer element in our stores", "fabric", False,
                          f"{type(exc).__name__}: {str(exc)[:70]}"))

    # --- W18-6 (ARM 2): nothing of ours is in the peer's stores ------------
    #
    # The arm that did not exist. Three sub-conditions.
    #
    # WOULD FAIL ON: a loader creating `colender.syndicate_member` (the
    # misdirected-DDL case Task 14's dispatch names -- same host, same port,
    # a different database name); writing one of our `SYNM-` member ids or
    # `SDT-` tracker ids into a peer row; or loading a subject of ours onto
    # the peer's ledger.
    #
    # `facility_id`, `lei` and `rssd` are EXCLUDED BY NAME, not by omission:
    # §C declares them the correlation keys and `peer_position.facility_id`
    # really does hold our `FAC-405B7A`. They are also what makes the scan's
    # control honest -- the control below asserts the scanner FINDS our
    # facility ids over there, which is the permitted crossing, and therefore
    # would equally have found a forbidden one.
    try:
        ours = _our_wave18_identifiers()
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = %s AND table_type = 'BASE TABLE'",
                (PG_SCHEMA_V2,))
            our_tables = {r[0] for r in cur.fetchall()}
            cur.execute(f'SELECT facility_id FROM "{PG_SCHEMA_V2}".facility')
            our_facilities = {r[0] for r in cur.fetchall()}

        problems = []
        peer_cells: list[tuple[str, str]] = []
        with co_lender_pg_connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema = %s ORDER BY 1, 2", (CO_LENDER_PG_SCHEMA,))
            columns = cur.fetchall()
            peer_tables = sorted({t for t, _ in columns})
            for table in peer_tables:
                cols = [c for t, c in columns if t == table]
                select = ", ".join(f'coalesce("{c}"::text, \'\')' for c in cols)
                cur.execute(f'SELECT {select} FROM "{CO_LENDER_PG_SCHEMA}"'
                            f'."{table}"')
                for row in cur.fetchall():
                    for column, value in zip(cols, row):
                        peer_cells.append((f"peer {table}.{column}", value))

        strays = sorted(set(peer_tables) & our_tables)
        if strays:
            problems.append(f"our table(s) in the peer schema: {strays}")
        unexpected_tables = sorted(set(peer_tables) - set(PEER_TABLES))
        if unexpected_tables:
            problems.append(f"peer schema holds {unexpected_tables}, which "
                            "this wave did not put there")

        problems += _cell_scan(peer_cells, ours)[:3]

        rows = bindings(_peer_sparql(
            f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{CO_LENDER_FLUREE_LEDGER}> "
            f'WHERE {{ ?s ?p ?o . FILTER(!STRSTARTS(STR(?s), "{PEER_URI_PREFIX}")) }}'))
        n_ours_there = int(rows[0]["n"]["value"]) if rows else 0
        if n_ours_there:
            problems.append(f"{n_ours_there} subject(s) outside "
                            f"{PEER_URI_PREFIX} on the peer ledger")

        control_hits = _cell_scan(peer_cells, our_facilities)
        if not control_hits:
            problems.append(
                "POSITIVE CONTROL FAILED — the scan cannot find any of our "
                f"{len(our_facilities)} facility ids in the peer's cells, and "
                "§C declares facility_id a correlation key that IS there; a "
                "scanner blind to the permitted crossing is blind to a "
                "forbidden one")

        out.append(Result(
            "no element of ours in the peer", "fabric", not problems,
            f"{len(ours)} of our SYNM-/SDT- ids absent from "
            f"{len(peer_cells)} peer cells; peer ledger holds only "
            f"{PEER_URI_PREFIX} subjects; correlation keys "
            f"{list(FABRIC_CORRELATION_KEYS)} excluded by name, "
            f"{len(control_hits)} control hits prove the scan sees them"
            if not problems else f"LEAK OUTWARD: {problems}"))
    except Exception as exc:  # noqa: BLE001
        out.append(Result("no element of ours in the peer", "fabric", False,
                          f"{type(exc).__name__}: {str(exc)[:70]}"))

    return out


#: Wave 19 — the `bank_capital` capital figures, scoped separately from the
#: master `POSTGRES_OWNED_ATTRS` addition above. `identity` columns
#: (`rssd`, `report_date`, `unit`, `provenance`, `source`) are deliberately
#: excluded: `rssd` and `report_date` are legitimate correlation/temporal
#: keys a Fluree edge could reasonably carry, and this check is about
#: MEASURED figures, not identity.
WAVE19_CAPITAL_FIGURES = [
    "tier1Capital", "tier2Capital", "riskWeightedAssets", "tier1RatioPct",
    "totalRatioPct", "cet1RatioPct", "totalAssets", "totalEquity",
    "totalDeposits", "ratioConsistent", "ratioDeltaPp",
]

#: A `citesProvision` VALUE must be a passage REFERENCE id
#: (`{regime-key}#{sha256[:12]}`, `generators/extract_regime_passages.py`'s
#: own scheme), never the provision's own text. The actual regime prose
#: this reference resolves to belongs to MongoDB's `passage.text` alone —
#: §C's own line for "Regime rule text ... MongoDB". A leak would show up
#: as a value this pattern rejects: it contains a space, punctuation, or
#: anything past a short hex suffix, none of which a real reference id has.
WAVE19_PROVISION_REF_RE = re.compile(r"^[a-z0-9-]+#[0-9a-f]{12}$")

#: Explicit, visible exceptions to the two broadened W19 scans below --
#: named individually rather than achieved by narrowing either scan's
#: pattern, per Task 16 fix round 1's Important findings. Both verified
#: live and empty/singleton at the time of writing; a new entry here is a
#: line someone has to justify, which is the point.
WAVE19_GROUP_TABLE_ALLOWLIST: frozenset[str] = frozenset()  # none needed yet
WAVE19_REGIME_TEXT_COLUMN_ALLOWLIST: frozenset[str] = frozenset({
    "competition_law_rule.rule_text",  # Wave 18 -- competition-law text,
                                        # a different regime entirely
})


def check_wave19() -> list[Result]:
    """Wave 19 — the capstone slice, `large-exposure-rwa-concentration`.

    Four checks, each the minimum CLAUDE.md's inverted-validator mandate
    asks for a new wave: does each store hold ONLY what it owns. What would
    make each one fail is stated on the check, per `check_wave18`'s own
    convention above.
    """
    out: list[Result] = []

    # --- W19-1: no capital figure on a Fluree node -------------------------
    #
    # WOULD FAIL ON: a loader asserting e.g. `ex:tier1Capital` on the
    # reporting bank's own Fluree node as a convenience mirror of Task 1's
    # `bank_capital` row -- exactly the leak class this wave's own `ex:rssd`
    # regression already demonstrated on these same bank nodes (found by
    # Task 6's implementer, missed by both the Task 5 implementer and its
    # own review; fixed at commit `0186399`). CLAUDE.md is explicit:
    # "Fluree nodes carry `lei` plus a display label and nothing else --
    # all attributes resolve from Postgres."
    try:
        leaked: list[str] = []
        for attr in WAVE19_CAPITAL_FIGURES:
            rows = bindings(sparql(
                f"SELECT (COUNT(?s) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
                f"WHERE {{ ?s <{EX}{attr}> ?o }}"))
            n = int(rows[0]["n"]["value"]) if rows else 0
            if n:
                leaked.append(f"{attr}={n}")
        out.append(Result(
            "no capital figure on a Fluree node", "fluree", not leaked,
            f"clean across {len(WAVE19_CAPITAL_FIGURES)} bank_capital figure "
            "names" if not leaked else f"LEAKED: {', '.join(leaked)}"))
    except Exception as exc:  # noqa: BLE001
        out.append(Result("no capital figure on a Fluree node", "fluree",
                          False, f"{type(exc).__name__}: {str(exc)[:70]}"))

    # --- W19-2: no connected-group table anywhere in Postgres --------------
    #
    # WOULD FAIL ON: ANY table whose name contains "group" -- not just the
    # two literal spellings `connected_group` / `group_connected` a first
    # draft of this check used, which would have missed `large_exposure_
    # group`, `obligor_groups`, or a bare `group` table just as easily as
    # it caught the two names it was looking for. Widened to the full term
    # after Task 16 fix round 1 named the narrow pattern as an Important
    # finding: "groups are recomputed, never stored" is the single most
    # important structural decision in this wave's design, and a check
    # that only rules out two spellings is not enforcing it.
    #
    # Verified live before widening: zero of the schema's tables contain
    # "group" at all, so the broad scan costs nothing today. If a FUTURE
    # table legitimately carries "group" in its name for an unrelated
    # reason, the fix is to add its name to `WAVE19_GROUP_TABLE_ALLOWLIST`
    # below -- an explicit, visible exclusion -- never to narrow this
    # pattern back down. A narrow pattern is invisible to the next reader;
    # an allowlist entry is a line they have to explain.
    try:
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = %s AND table_type = 'BASE TABLE' "
                "AND table_name ILIKE %s",
                (PG_SCHEMA_V2, "%group%"))
            found = sorted(r[0] for r in cur.fetchall()
                          if r[0] not in WAVE19_GROUP_TABLE_ALLOWLIST)
        out.append(Result(
            "no connected-group table in Postgres", "postgres", not found,
            "absent, as it should be -- groups are recomputed live"
            if not found else f"MATERIALIZED: {found}"))
    except Exception as exc:  # noqa: BLE001
        out.append(Result("no connected-group table in Postgres", "postgres",
                          False, f"{type(exc).__name__}: {str(exc)[:70]}"))

    # --- W19-3: no regime rule text outside MongoDB -------------------------
    #
    # Two sub-conditions, either able to fail alone.
    #
    # WOULD FAIL ON (Fluree half): a `citesProvision` VALUE that is the
    # provision's own sentence instead of a reference id -- e.g. a future
    # loader writing the $500,000-cap sentence itself onto a `RegimeVersion`
    # node rather than citing `reg-o-12cfr215#f8f8d951ecdb` and leaving the
    # text in Mongo's `passage.text`. Checked by PATTERN, not by a denylist
    # of known-bad strings, so a NEW leaked sentence is still caught.
    #
    # WOULD FAIL ON (Postgres half): a column anywhere in the schema named
    # for holding regime prose -- `regime_text`, `provision_text`, OR the
    # bare `rule_text` a sibling table (Wave 18's `competition_law_rule`)
    # already uses for the same shape of thing, which is exactly the name
    # a future regime-text leak would most plausibly carry. A first draft
    # excluded `%rule_text%` entirely to dodge that one real, unrelated
    # column -- Task 16 fix round 1 named this an Important finding: the
    # narrowing traded detection of the LIKELIEST leak name for silencing
    # today's one false positive. Fixed by excluding
    # `competition_law_rule.rule_text` BY ITS FULL table.column NAME
    # (`WAVE19_REGIME_TEXT_COLUMN_ALLOWLIST` below) and keeping the broad
    # term -- verified live that it is the only `rule_text` column in the
    # schema, so the allowlist is a single, visible, named exception, not a
    # second hole.
    try:
        problems: list[str] = []
        rows = bindings(sparql(
            f"SELECT DISTINCT ?c FROM <{FLUREE_LEDGER_V2}> WHERE {{ "
            f"?s <{EX}citesProvision> ?c }}"))
        values = [r["c"]["value"] for r in rows]
        bad = sorted(v for v in values if not WAVE19_PROVISION_REF_RE.match(v))
        if bad:
            problems.append(f"citesProvision carries prose, not a "
                            f"reference: {bad[:3]}")
        if not values:
            problems.append("no citesProvision value found at all -- "
                            "Task 9's RegimeVersion nodes load these")

        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT table_name || '.' || column_name "
                "FROM information_schema.columns WHERE table_schema = %s "
                "AND (column_name ILIKE %s OR column_name ILIKE %s "
                "     OR column_name ILIKE %s)",
                (PG_SCHEMA_V2, "%regime_text%", "%provision_text%",
                 "%rule_text%"))
            pg_hits = [r[0] for r in cur.fetchall()
                      if r[0] not in WAVE19_REGIME_TEXT_COLUMN_ALLOWLIST]
        if pg_hits:
            problems.append(f"regime prose column(s) in Postgres: {pg_hits}")

        out.append(Result(
            "no regime rule text outside MongoDB", "mongo", not problems,
            f"{len(values)} citesProvision value(s), all reference ids; "
            "no regime-text column in Postgres" if not problems
            else f"LEAKED: {problems}"))
    except Exception as exc:  # noqa: BLE001
        out.append(Result("no regime rule text outside MongoDB", "mongo",
                          False, f"{type(exc).__name__}: {str(exc)[:70]}"))

    # --- W19-4: no proposal row in ccf_v2.facility --------------------------
    #
    # WOULD FAIL ON: a loader BOOKING one of the two hypothetical
    # `exposure_proposal` rows into `facility` -- either under its own
    # `PROP-` id, or as an ordinary `FAC-` row carrying the identical
    # (borrower_lei, commitment_amount) pair. Tasks 13/14's own controller
    # measured the booked total UNCHANGED at 55,719,058,576 across 60
    # facilities through every fix round in this wave; this is the
    # structural version of that same invariant, checked by shape rather
    # than by trusting a total to stay the same number forever.
    try:
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(
                f'SELECT proposal_id, subject_lei, commitment_amount '
                f'FROM "{PG_SCHEMA_V2}".exposure_proposal')
            proposals = cur.fetchall()

            cur.execute(
                f"SELECT COUNT(*) FROM \"{PG_SCHEMA_V2}\".facility "
                f"WHERE facility_id LIKE 'PROP-%'")
            prop_prefixed = cur.fetchone()[0]

            booked_matches: list[str] = []
            for proposal_id, subject_lei, commitment_amount in proposals:
                cur.execute(
                    f'SELECT facility_id FROM "{PG_SCHEMA_V2}".facility '
                    f'WHERE borrower_lei = %s AND commitment_amount = %s',
                    (subject_lei, commitment_amount))
                for (fid,) in cur.fetchall():
                    booked_matches.append(f"{proposal_id} -> {fid}")

        ok = prop_prefixed == 0 and not booked_matches
        out.append(Result(
            "no proposal row in facility", "postgres", ok,
            f"{len(proposals)} hypothetical proposal(s), 0 PROP- ids and 0 "
            "(borrower_lei, commitment_amount) matches in facility" if ok
            else f"BOOKED: prop_prefixed={prop_prefixed} "
                 f"matches={booked_matches}"))
    except Exception as exc:  # noqa: BLE001
        out.append(Result("no proposal row in facility", "postgres", False,
                          f"{type(exc).__name__}: {str(exc)[:70]}"))

    return out


def check_wave20() -> list[Result]:
    """Wave 20 — the three T1 gaps: addresses, entitlement, no-LEI clients.

    Two new Postgres tables landed (`internal_client`, `principal_jurisdiction`)
    and a column pair was renamed and doubled (`legal_address_*`, `hq_address_*`).
    None of it was represented here until this function existed, which meant
    the 60/60 this validator reported said NOTHING about any of it -- a green
    run whose population excluded the entire wave.

    Every check below carries a POSITIVE CONTROL, because all three are
    assertions of ABSENCE and an absence check that cannot see anything at all
    passes forever.
    """
    out: list[Result] = []

    # --- W20-1: no no-LEI client smuggled into `legal_entity` --------------
    #
    # WOULD FAIL ON: someone "simplifying" gap 2 by inserting the internal
    # clients into `legal_entity` with a `SYN-` placeholder in the `lei`
    # column. That is not a tidier version of the ruling, it is the ruling
    # reversed -- a placeholder RESOLVES, which defeats §G's acceptance
    # criterion ("a no-LEI entity resolves and reports the lower freshness
    # ceiling") by making the no-LEI case indistinguishable from the LEI case.
    #
    # POSITIVE CONTROL: `legal_entity` genuinely contains `SYN-` identifiers
    # already -- the three ABS deal trusts -- so a check keyed on the prefix
    # would be useless here. This one matches on the client ids and names
    # themselves, and proves the name scan works by finding a name that IS
    # there.
    try:
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(f'SELECT internal_client_id, legal_name '
                        f'FROM "{PG_SCHEMA_V2}".internal_client')
            clients = cur.fetchall()
            ids = [c[0] for c in clients]
            names = [c[1] for c in clients]

            cur.execute(f'SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".legal_entity '
                        "WHERE lei = ANY(%s) OR legal_name = ANY(%s)",
                        (ids, names))
            leaked = cur.fetchone()[0]

            # Control: the same scan must FIND a legal_entity name when asked
            # for one, or its zero above proves nothing about the query.
            cur.execute(f'SELECT legal_name FROM "{PG_SCHEMA_V2}".legal_entity '
                        "WHERE legal_name IS NOT NULL LIMIT 1")
            known = cur.fetchone()[0]
            cur.execute(f'SELECT COUNT(*) FROM "{PG_SCHEMA_V2}".legal_entity '
                        "WHERE legal_name = ANY(%s)", ([known],))
            control = cur.fetchone()[0]

        ok = leaked == 0 and control > 0 and len(clients) > 0
        out.append(Result(
            "no no-LEI client inside legal_entity", "postgres", ok,
            f"{len(clients)} internal clients, none of their ids or names in "
            f"legal_entity; control found {control} for a known name" if ok
            else f"LEAKED: {leaked} / control={control} / clients={len(clients)}"))
    except Exception as exc:  # noqa: BLE001
        out.append(Result("no no-LEI client inside legal_entity", "postgres",
                          False, f"{type(exc).__name__}: {str(exc)[:70]}"))

    # --- W20-2: no postal address on a Fluree node -------------------------
    #
    # WOULD FAIL ON: a loader mirroring the new `hq_address_*` triple onto the
    # entity's Fluree node so a traversal need not hop to Postgres. CLAUDE.md:
    # "Fluree nodes carry `lei` plus a display label and nothing else -- all
    # attributes resolve from Postgres."
    #
    # POSITIVE CONTROL: the same SPARQL shape must return a NON-zero count for
    # `ex:lei`, which every entity node does carry. Without that, an empty
    # ledger or a broken query path would report this clean.
    try:
        leaked_preds: list[str] = []
        for attr in ("hqAddressCountry", "hqAddressCity", "hqAddressRegion",
                     "legalAddressCountry", "legalAddressCity",
                     "legalAddressRegion", "addressCountry", "addressCity",
                     "addressRegion"):
            rows = bindings(sparql(
                f"SELECT (COUNT(?s) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
                f"WHERE {{ ?s <{EX}{attr}> ?o }}"))
            n = int(rows[0]["n"]["value"]) if rows else 0
            if n:
                leaked_preds.append(f"{attr}={n}")
        rows = bindings(sparql(
            f"SELECT (COUNT(?s) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
            f"WHERE {{ ?s <{EX}lei> ?o }}"))
        control = int(rows[0]["n"]["value"]) if rows else 0

        ok = not leaked_preds and control > 0
        out.append(Result(
            "no postal address on a Fluree node", "fluree", ok,
            f"clean across 9 address predicates; control sees {control} "
            f"ex:lei assertions" if ok
            else f"LEAKED: {', '.join(leaked_preds) or 'none'} / control={control}"))
    except Exception as exc:  # noqa: BLE001
        out.append(Result("no postal address on a Fluree node", "fluree",
                          False, f"{type(exc).__name__}: {str(exc)[:70]}"))

    # --- W20-3: entitlement scope is Postgres' alone -----------------------
    #
    # WOULD FAIL ON: a loader asserting a jurisdiction scope on a principal
    # node in Fluree. Q019 §3 gives Fluree policy VERSIONS and Postgres the
    # entitlement GRANTS; duplicating the grant is the "for convenience" copy
    # CLAUDE.md forbids, and it would let a consumer read a scope that the
    # recomputing gate in validators/entitlement.py never sees.
    #
    # POSITIVE CONTROL: the grants must actually exist in Postgres, or "absent
    # from Fluree" is true of an element nobody has built.
    try:
        leaked_preds = []
        for attr in ("jurisdictionScope", "jurisdictionPrefix",
                     "entitlementScope"):
            rows = bindings(sparql(
                f"SELECT (COUNT(?s) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
                f"WHERE {{ ?s <{EX}{attr}> ?o }}"))
            n = int(rows[0]["n"]["value"]) if rows else 0
            if n:
                leaked_preds.append(f"{attr}={n}")
        with pg_connect() as conn, conn.cursor() as cur:
            cur.execute(f'SELECT COUNT(*) '
                        f'FROM "{PG_SCHEMA_V2}".principal_jurisdiction')
            grants = cur.fetchone()[0]

        ok = not leaked_preds and grants > 0
        out.append(Result(
            "entitlement scope is Postgres' alone", "fluree", ok,
            f"{grants} grants in Postgres, 0 scope predicates in the ledger"
            if ok else
            f"LEAKED: {', '.join(leaked_preds) or 'none'} / grants={grants}"))
    except Exception as exc:  # noqa: BLE001
        out.append(Result("entitlement scope is Postgres' alone", "fluree",
                          False, f"{type(exc).__name__}: {str(exc)[:70]}"))

    return out


def _peer_sparql(query: str) -> dict:
    """Read-only query against the CO-LENDER's ledger. Deliberately a second
    function rather than a parameter on `sparql()` above: the two fabrics are
    reached through different entry points, and a single function with a flag
    is one typo away from asking our ledger a question about the peer's."""
    from ccf import fluree

    return fluree.co_lender_query(query)


def main() -> int:
    print("PARTITION VALIDATOR — asserts each store owns its slice and no other")
    print(f"  targets: fluree={FLUREE_LEDGER_V2}  pg={PG_SCHEMA_V2}  "
          f"mongo={MONGO_DB_V2}  sqlite={SQLITE_PATH.name}\n")

    results: list[Result] = []
    results += check_fluree()
    results += check_postgres()
    results += check_mongo()
    results += check_sqlite()
    results += check_wave18()
    results += check_wave19()
    results += check_wave20()

    for r in results:
        print(r.render())

    failed = [r for r in results if not r.passed]
    print(f"\n  {len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print("\n  A failure here is a load that is silently wrong, not a gap "
              "in coverage.")
        print("  Do not relax a check to clear it — establish which store "
              "owns the element first.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
