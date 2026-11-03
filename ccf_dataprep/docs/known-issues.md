# Known Issues, Limitations, and Caveats

**Last updated:** 2026-08-27 (Wave 19 Task 17 — regime-fetch blockers, the capital
units defect, the corpus-wide embedding gap, and cross-reference citations, §45–§49)
**Companions:** `docs/data-acquisition-plan.md` (wave plan) · `docs/ccf_dataprep_v2.md` (reference + IRI binding)

> This document exists so limitations are **surfaced rather than discovered**. The
> failure mode this project is most exposed to is a large, plausible, silently
> wrong dataset. Anything here that a downstream consumer could mistake for
> clean data is recorded, with its cause and its blast radius.
>
> Severity key: **🔴 blocking** · **🟠 affects downstream correctness** ·
> **🟡 known shortfall, safe if understood** · **🔵 informational**

---

## 0 · Wave 8 defects

### 0.2 🔴 FIXED 2026-08-17 — the whole v1 starter binding was wrong; FIBO moved to OMG Commons

**Found 2026-08-17, while scoping the vault-mirror refresh.** §0.1 fixed the two
ownership *properties*. That fix was incomplete: it never re-checked the starter
**classes**. All of them are wrong too.

**FIBO factored its foundational vocabulary out into the OMG Commons Ontology
Library.** `Agent`, `Party`, `LegalEntity`, and `FormalOrganization` are no longer
FIBO terms at all — they live under `https://www.omg.org/spec/Commons/`.
`Corporation` moved within FIBO. Three properties do not exist anywhere.

**Every one of the 10 v1 starter bindings is invalid:**

| Bound as | Reality |
| --- | --- |
| `fibo-fnd-aap-agt:Agent` | → **`cmns-pts:Agent`** `https://www.omg.org/spec/Commons/PartiesAndSituations/Agent` |
| `fibo-fnd-pty-pty:Party` | → **`cmns-pts:Party`** `https://www.omg.org/spec/Commons/PartiesAndSituations/Party` |
| `fibo-be-le-lp:LegalEntity` | → **`cmns-org:LegalEntity`** `https://www.omg.org/spec/Commons/Organizations/LegalEntity` |
| `fibo-be-le-fbo:FormalOrganization` | → **`cmns-org:FormalOrganization`** `https://www.omg.org/spec/Commons/Organizations/FormalOrganization` |
| `fibo-be-corp-corp:Corporation` | → **`fibo-be-le-cb:Corporation`** `.../BE/LegalEntities/CorporateBodies/Corporation` |
| `fibo-fnd-rel-rel:isIdentifiedBy` | → **`cmns-id:isIdentifiedBy`** `https://www.omg.org/spec/Commons/Identifiers/isIdentifiedBy` |
| `fibo-fnd-rel-rel:hasIdentity` | **absent** — no such property in FIBO or Commons |
| `fibo-fnd-pty-pty:isRelatedTo` | **absent** — and no relatedness equivalent found |
| `hasOwnershipInterestIn` | **absent** — fixed in §0.1 |
| `hasControllingInterestIn` | **absent** — fixed in §0.1 |

`BE/Corporations/Corporations` still resolves but declares only
`JointStockCompany`, `PrivatelyHeldCompany`, `PubliclyHeldCompany`,
`ReligiousCorporation`, `BoardAgreement`, and two registration-identifier
classes. No `Corporation`.

**Blast radius — larger than §0.1.**

| Artifact | Exposure |
| --- | --- |
| Fluree `fibo-v2` | **1,500 type assertions** across **500 entities** — `Party` 500, `LegalEntity` 500, `Corporation` 500 |
| T-Box | `Agent` and `FormalOrganization` declared, plus the 5-class subclass chain, all on invalid IRIs |
| `loaders/load_fluree_wave3.py` | `C_AGENT`, `C_PARTY`, `C_LEGAL_ENTITY`, `C_FORMAL_ORG`, `C_CORPORATION` |
| `validators/partition.py` | the "no `ex:` type shadows a FIBO term" check compares against these |
| Vault mirror | publishes all ten as the shared contract |

`isRelatedTo`, `hasIdentity`, and `isIdentifiedBy` carry **0 edges** — declared,
never used — so only the class IRIs affect instance data.

**Why this is worse than it looks.** CLAUDE.md rule 7 requires explicit typing for
every queried role precisely because Fluree does no inference. We complied — and
typed every entity against IRIs that resolve to nothing. A consumer querying a
conformant FIBO store for `Party` gets zero rows from a graph where 500 entities
are "Party".

**The subclass chain was invented too.** v1 asserted
`Corporation ⊂ FormalOrganization ⊂ LegalEntity ⊂ Party ⊂ Agent`. Derived from
Commons, the real hierarchy is:

```
cmns-pts:Agent
└── cmns-pts:Party
    ├── cmns-org:Organization
    │   └── cmns-org:FormalOrganization
    │       └── cmns-org:LegalEntity ──┐
    └── cmns-org:LegalPerson ──────────┴── (LegalEntity has BOTH parents)
                                            └── fibo-be-le-cb:Corporation
```

Three differences: `LegalEntity ⊂ FormalOrganization` is **inverted** relative to
what v1 claimed; `LegalEntity` has **two** parents, which a single chain cannot
express; and `cmns-org:Organization` and `cmns-org:LegalPerson` were **missing
entirely** — `LegalEntity` reaches `Party` only through them, with no direct
`LegalEntity ⊂ Party` axiom.

Under rule 7 (no inference) this compounds: our entities are typed
`Party` + `LegalEntity` + `Corporation`, so even with corrected IRIs they would
remain unreachable by a query for `FormalOrganization`, `Organization`, or
`LegalPerson` — three roles they genuinely hold. Remediation must re-type against
the real chain, not merely swap five IRIs.

**Two smaller findings from the same pass.** `SubordinateLienPosition` is
referenced in the FIBO sources but **not declared** in `LOAN/LoansGeneral/Loans`
— it was nearly added to the binding table on the strength of a clone grep, which
is the same trap in miniature. And `LegalPerson` is absent from FIBO's
`BE/LegalEntities/LegalPersons` but **present as `cmns-org:LegalPerson`**; the
name existing somewhere is not the name existing where you bind it.

**Resolved: re-typed against OMG Commons (option A).** Rejected alternatives are
recorded in vault Q021. The framing decided it — stated as "rewrite 1,500 type
assertions" A and B look identical and B looks cheaper; stated as "correct 1,500
rows **and append four roles that were never asserted**", only A finishes the job.
B pays the same rewrite and keeps the defect.

**How it was remediated (2026-08-17):**

1. `loaders/remediate_ownership_iris.py` extended to retract type assertions on
   the five invalid class IRIs, their T-Box declarations, and the invented chain
   — **1,519 triples**. Ledger t=36 → **44**, 4,564 triples.
2. `loaders/load_fluree_wave3.py` re-typed every entity against **all seven**
   Commons roles and the real chain (including `LegalEntity`'s two parents).
   t=44 → **58**.
3. GLEIF ultimate-parent edges re-predicated off `controls` onto
   `hasGlobalUltimateParent`, and `hasDomesticUltimateParent` **derived** — see
   §0.3.
4. Verified: **500 each** for Corporation, LegalEntity, LegalPerson,
   FormalOrganization, Organization, Party, Agent. **0** on all five invalid IRIs.

### 0.3 🟠 A third remediation class — valid IRI, changed usage

The first pass produced **704 edges where the loader reported 601**. Parts 1 and
2 retract by *invalid IRI*, and `controls` is perfectly valid — what changed was
its **usage**. Its 103 GLEIF ultimate-parent edges were re-predicated to
`hasGlobalUltimateParent`, so the retraction skipped them and the reload added
the re-predicated copies alongside: 103 duplicates carrying two different
meanings.

Caught by post-load verification, not by the loader. All 103 were confirmed an
exact subset of the new predicate's edge set before retracting, so genuine
control edges could not be swept up. `RE_PREDICATED` in the remediation script
now handles this class, gated on that same subset test.

**Standing lesson.** "Is this IRI valid?" and "does this IRI still mean what it
meant?" are different questions, and only the first has a machine answer.
Idempotency checks keyed on identity miss every semantic re-assignment.

### 0.4 🟢 FIXED 2026-08-19 (Wave 10 follow-up, pre-Wave-11a) — the estate had zero control-without-ownership edges

Exposed, not caused, by §0.3. The 103 edges on `controls` were GLEIF
ultimate-parent relationships all along; once correctly re-predicated,
**`controls` fell to 0**.

Control without ownership — golden shares, board-appointment rights, shareholder
agreements — is precisely the structure `corporate-family-tree` exists to
surface, and the siblings rule published in that spec's step 3 warns a
traversal matching only `owns` will silently drop it. The warning was correct
and **the estate had nothing to exercise it**, from Wave 8 through the end of
Wave 10.

`validators/conditions.py` carried this as a **failing** check rather than
leaving it masked by the old mapping for that entire span — outstanding
manufacture work, deliberately left visible.

**Closed in `d1a4554`** ("Close the estate's last failing condition"), a
Wave 10 follow-up commit on `main` that landed **before** Wave 11a branched.
Three control-only edges were engineered — Ardsley Golden Share Trust
(golden share), Kestrel Founders Voting Trust (dual-class voting), Pellworth
Facility Agent (credit-agreement board-appointment rights), each targeting a
real anchor with no `owns` edge for the pair — and the check itself was
tightened with an explicit `FILTER NOT EXISTS` so it could not be satisfied
by a control edge that also happened to co-occur with ownership. Labelled
`synthetic — engineered`; full mechanism detail in §3.7. `conditions.py`
reached **72 passed / 0 failed** for the first time in the estate's history
at that commit — the baseline Wave 11a then built on (ending this wave at
82/0). `controls` now holds **3** live assertions, not 0; `published_claims.json`
carries `controls` as `not_materialized`, which is why `binding_drift.py`
correctly flags it `CAVEAT_STALE` — data landed since that claim was last
published, and the claim itself is what needs updating, not the estate.

**Standing lesson, restated.** §0.1 said inherited bindings need verification.
The fix verified the properties it was already looking at and stopped there. The
lesson only lands if applied to *everything* inherited — an audit scoped to the
symptom finds the symptom.

---

### 0.1 🔴 FIXED 2026-08-17 — the ownership and control predicates were not FIBO terms

**Found Wave 8 (2026-08-17), introduced in v1, inherited unverified into v2.**

The two predicates carrying the entire ownership graph **do not exist in FIBO**:

| Predicate as loaded | Status |
| --- | --- |
| `.../BE/OwnershipAndControl/Ownership/hasOwnershipInterestIn` | absent from FIBO; the module itself **404s** |
| `.../BE/OwnershipAndControl/Control/hasControllingInterestIn` | absent from FIBO; the module itself **404s** |

**How it happened.** Wave 0 verified the *Loans-module terms it added* and did not
re-verify the **five starter properties carried over from v1**. Those five were
never checked against the EDM Council source at all. Two of the five are invented.

**Why it was not caught earlier.** Nothing local can catch it. The predicates are
syntactically valid IRIs; Fluree stores and returns them; `partition.py`,
`conditions.py`, and `bitemporal.py` all query using the same wrong constants, so
they agree with themselves and pass. **The estate is internally consistent and
externally unconsumable** — a client querying a conformant FIBO store for these
IRIs gets nothing. This is the precise failure CLAUDE.md's binding protocol exists
to prevent, and it survived seven waves because a validator that shares the
defect cannot detect it.

**Blast radius.**

| Artifact | Exposure |
| --- | --- |
| Fluree `fibo-v2` | **565 edges** — 462 ownership, 103 control |
| `loaders/load_fluree_wave3.py` | `P_OWNS`, `P_CONTROLS` constants (lines ~52–53) |
| `validators/conditions.py` | `OWNS`, `CONTROLS` constants (lines ~30–33) |
| `generators/generate_mnpi.py` | three predicate lists (lines ~66, 81, 94) |
| `ontology/` T-Box | declares the `subPropertyOf` axiom between the two invented terms |
| `corporate-family-tree` | the product traverses this graph — its data is affected, its *conditions* still hold |
| **Vault mirror** `fibo-iri-binding` | publishes the wrong IRIs to the CCF SDK project |

**Verified two ways.** Exhaustive `rdf:about` / `rdfs:label` search across all 295
RDF modules of a shallow `edmcouncil/fibo` clone, and live fetch against published
Production. Re-checkable via `generators/verify_fibo_wave8_confirm.py`, which
asserts the absence explicitly rather than leaving it in prose.

**Correct replacements** are recorded in `docs/ccf_dataprep_v2.md` under
*"Wave 8 correction"*, all confirmed present. Note that
`fibo-be-oac-cctl:hasDomesticUltimateParent` / `hasGlobalUltimateParent` are real
FIBO properties expressing exactly the direct-vs-ultimate-parent distinction
`corporate-family-tree` §B needs — the invented predicates were both wrong and
less expressive than what FIBO already had.

**The invented axiom.** v1 also declared `hasControllingInterestIn`
`subPropertyOf` `hasOwnershipInterestIn`. That was invented as well. FIBO makes
`owns` and `controls` **siblings** — both `subPropertyOf`
`playsActiveRoleThatDirectlyAffects` — never sub/super. The axiom was not
re-asserted. Consequence: matching both predicates explicitly was previously a
workaround for Fluree's missing inference (§5.2); it is now simply the correct
query, and the ledger no longer carries an axiom contradicting FIBO.

**Corrected bindings, both confirmed against published Production:**

| Was | Now |
| --- | --- |
| `.../BE/OwnershipAndControl/Ownership/hasOwnershipInterestIn` | `fibo-fnd-oac-own:owns` → `.../FND/OwnershipAndControl/Ownership/owns` |
| `.../BE/OwnershipAndControl/Control/hasControllingInterestIn` | `fibo-fnd-rel-rel:controls` → `.../FND/Relations/Relations/controls` |

`controls` is **declared** in `FND/Relations/Relations` and only *refined*
(domain `Party`) by `FND/OwnershipAndControl/Control`. Binding it under the
Control namespace would have reproduced the very defect being corrected — the
module-membership trap, hit for the fourth time in this project.

**How it was remediated (2026-08-17):**

1. `loaders/remediate_ownership_iris.py` — new, `--dry-run` capable, idempotent.
   Retracted **570 triples**: 565 edges (462 + 103), 4 T-Box declarations, and the
   invented `subPropertyOf` axiom. Ledger t=25 → **t=26**, 5,509 triples.
2. `loaders/load_fluree_wave3.py` re-run with corrected constants. t=26 → **t=35**,
   **6,078** triples (one fewer than before — the invented axiom is gone).
3. `generators/generate_mnpi.py` + `loaders/load_mnpi_wave7.py` re-run so the
   cross-backend tokens in `projection_plan.permitted_edge_types` follow:
   `hasOwnershipInterestIn`/`hasControllingInterestIn` → `owns`/`controls`. t=**36**.
4. Verified: **462 `owns` + 103 `controls` = 565**; **0** edges remain on either
   invalid predicate.
5. All four validators re-run **against the corrected IRIs** — partition 10/10,
   conditions 45/0, bitemporal 3/3, projection holds.

**📤 Vault mirror refreshed 2026-08-17.** `fibo-iri-binding` no longer publishes
the two invalid predicates; the vault applied the correction (`20f7fbc`). Send
future corrections through `~/.agent-exchange/ccf-dataprep/outbox/` — see CLAUDE.md.

**Residual note.** Consumers holding a Postgres `ccf_v2` snapshot taken before
2026-08-17 will see the old tokens in `permitted_edge_types` and must map forward.
Recorded in the cross-backend table in `ccf_dataprep_v2.md`.

**Standing lesson.** *Inherited* bindings need verification as much as new ones.
Wave 0's protocol was applied only to terms it added, and the five starter
properties rode through seven waves unchecked. A validator sharing the loader's
constants can never catch this class of error — only the external source can.

---

## 1 · Defects found and fixed

Recorded because the *class* of error recurs, and because a reader should know
these were caught rather than never present.

### 1.1 🟠 FIXED — amendment effective dates were mislabelled `public`

**Wave 5.** `generate_temporal.py` labelled amendment effective dates as
`public` provenance. They are not. Only the **facility** effective date is
public, extracted from the EX-10 "dated as of" clause. Amendment effective
dates are derived by stepping forward from it (`prior + random(120–400) days`);
the 8-K Item 1.01 filings were never mapped to the specific facility each one
amends.

The amendment **count** per facility is public (from `filing_profile`). The
amendment **dates** are not.

*Why it matters:* rule #1 exists to stop exactly this. A consumer reading
`effective_date_provenance: public` would have treated a synthetic date as a
filed fact.

*Fix:* relabelled `synthetic — internal` with an explanatory note, in the
generator and in Fluree. Because Fluree is append-only, the 25 wrong assertions
were **retracted at t=18 and corrected at t=19** — the retraction remains in
ledger history, so the correction is itself auditable.

*Residual:* the dates are still synthetic. Mapping 8-K Item 1.01 filings to
facilities would make them public and is not done. See §3.4.

### 1.1b 🟠 FIXED — `ex:` schema classes carried no provenance label

**Wave 7 / spec re-read.** All seven `ex:` extension classes (`Covenant`,
`CovenantDefinition`, `Amendment`, `PolicyVersion`, `WallCrossing`,
`EmbargoWindow`, `RegFDEvent`) were loaded with `ex:isFiboTerm false` but **no
`ex:provenance`**. Rule #1 requires a provenance class on every element, and a
schema element is an element.

Found by **re-reading the spec**, not by any gate. The vault patched
`covenant-in-force-as-of` after the Covenant finding, and §C now splits the
schema row in two, classifying the `ex:` extensions explicitly as
`synthetic — internal`. My working copy predated the patch.

*Fix:* labelled at ledger t=23.

**🟠 Standing lesson: vault specs are patched in place.** A cached reading goes
stale silently. Re-read any spec before relying on it, especially after
reporting a finding against it — the correction may already be upstream.

### 1.2 🟠 FIXED — restatement gate counted comparatives as restatements

**Wave 2.** The gate counted a second accession for the same period as a
restatement. XBRL repeats prior-period figures as comparatives, so FY2023
revenue appears in the FY2023 10-K and again in the FY2024 10-K under a
different accession with an **identical value**. That inflated the count from
116 real restatements to 457 and would have passed the §F gate while
`basis=as-reported` and `basis=latest-restated` returned identical numbers.

*Fix:* require a **different value** under a later accession. 407 real
restatements across 39 obligors.

### 1.3 🟠 FIXED — two of three engineered lag cases silently did not fire

**Wave 5.** Amendment dates stepped forward from the agreement date, and the
loop broke once a date passed today — so only 1 of 3 approved lag cases was
created. The one that was created **booked three weeks in the future**, which
is meaningless for an assertion time: a bank cannot have booked what it has not
booked yet.

*Fix:* lag amendments are placed working *backward* from today so both dates
land in the past; the candidate pool is oversampled because a facility can
legitimately have no room for a gap.

### 1.4 🟠 FIXED — `interest_coverage` matched zero covenants across 60 documents

**Wave 5.** Min-direction covenants are conventionally phrased *"shall not
permit X **to be less than** Y"*. The negation sits upstream in "not permit", so
the local text reads as the wrong direction and the pattern excluded it.

*Fix:* accept `to be less than` / `to exceed` as direction triggers.
Extraction went 23 → 44 covenants, `interest_coverage` 0 → 11.

### 1.5 🟠 FIXED — LEI resolution accepted confidently wrong matches

**Wave 1.** A first pass matched `WD 40 CO` → *PUDO INVESTMENTS LIMITED* and
`REGIS CORP` → *Regis University*. Accepting either would have corrupted the
correlation spine at its root: every downstream join for that obligor would
resolve to the wrong company while validating perfectly.

*Fix:* expand EDGAR abbreviations before querying GLEIF (`CORP`→`CORPORATION`,
`CO`→`COMPANY`), and **reject** anything below a `strong` (≥0.85) match rather
than accept it. Exact matches went 38 → 44.

*Sub-bug:* the name normaliser stripped `inc` and `corp` but not
`incorporated`, so `GRANITE CONSTRUCTION INC` vs `GRANITE CONSTRUCTION
INCORPORATED` scored 0.755 and was rejected as a mismatch. Three of five
rejections were this bug, not bad data.

### 1.6 🟡 FIXED — conditions register undercounted ownership edges

The register reported 462 edges where the loader reported 565. Both were
correct: `hasControllingInterestIn` is declared `subPropertyOf`
`hasOwnershipInterestIn`, the axiom **is** loaded, and Fluree runs without
reasoning — so querying the superproperty silently dropped every control edge.
Rule #7 biting inside the validator built to catch that class of error.

*Fix:* query both predicates explicitly.

### 1.7 🟡 FIXED — partition validator flagged legitimate `ex:` extensions

Wave 5 loaded `ex:Covenant`, and the validator's "types use FIBO namespace"
check failed on 207 subjects. Two things look identical and only one is a
defect:

| | |
|---|---|
| `ex:Corporation` | **defect** — FIBO has `Corporation`; the v1 load typed two entities under `ex:` and Neo4j then flattened both namespaces to one `:Corporation` label |
| `ex:Covenant` | **legitimate** — FIBO has no `Covenant` class anywhere |

*Fix:* the assertion is now "no `ex:` type **shadows** a FIBO term", with
permitted extensions allowlisted so adding one is deliberate.

### 1.8 🔵 FIXED — `fiscal_period` NOT NULL violation traced to wrong-source data

**Wave 2.** The load failed on a NULL `fiscal_period`. The symptom was a key
constraint; the cause was that `companyfacts` surfaces figures tagged in **proxy
statements (DEF 14A)** and registration statements, which are not periodic
financial statements and do not belong in a credit spread.

*Fix:* filter to periodic forms (10-K/10-Q/20-F/40-F and amendments).

---

## 2 · Source-data limitations — inherent, not fixable here

### 2.1 🟡 GLEIF Level 2 is structurally shallow for US public filers

Every anchor returned **depth 0 upward** and **depth 1 downward**. GLEIF records
direct and ultimate parent only, and subsidiaries of US public filers rarely
register their own relationships. The anchors *are* the ultimate parents —
nothing sits above them.

*Consequence:* `corporate-family-tree`'s `depth` parameter would change no
answer on natural data. Depth is **engineered** (§3.1).

### 2.2 🟡 Exhibit 21 found for 27 of 50 anchors; parsed from 22

Not every 10-K files a recognisable EX-21, and some are scanned or use layouts
the parser does not read. 1,635 subsidiaries came from 22 filers, so subsidiary
breadth is concentrated: Amphenol alone contributed 469.

### 2.3 🟡 Exhibit 21 is a flat list — hierarchy is not inferable

Some filers imply hierarchy by indentation. The parser **deliberately does not
read it**: a guessed parent edge is indistinguishable from a filed one once it
is in the graph.

### 2.4 🟡 Ownership edge count is 565 against §F's ~800

Exhibit 21 yields exactly one edge per subsidiary, so the shortfall is what the
public sources actually give. **Not padded** — the target's purpose is
non-trivial traversal, which 565 delivers. Manufacturing 235 edges to hit a
number is "hitting the count while missing the condition".

### 2.5 🟡 Three anchors were dropped for having no GLEIF LEI

`CareCloud`, `Chiron Real Estate`, `LifeMD`. Smaller filers are not required to
hold an LEI. A fourth, `BrightSpire Capital`, matched its **operating
subsidiary** rather than the parent — a different legal entity that would
mis-anchor every join — and was also dropped. All four were backfilled.

*This is a real-world characteristic worth preserving elsewhere*: not every SEC
filer has an LEI. It is excluded only from the anchor spine, where a missing
LEI breaks joins.

### 2.6 🟡 Facilities concentrate on 15 borrowers

45 facilities across 15 distinct borrowers, because amendment-rich filers were
preferred and one agreement commonly defines a revolver plus term tranches.
Realistic per-borrower, but facility coverage is **not** spread across all 50
anchors.

### 2.8 🟡 Collateral schedules are not recoverable for this cast — three ways

**Wave 9.** 20 of 45 facilities grant a security interest and then defer the
asset list: *"the Collateral described in the Security Agreement."* The grant is
filed fact; the asset breakdown is not readable. A fetch wave was run
specifically to recover them and **it did not succeed.** Each failure mode was
distinct and each is evidenced:

1. **Not siblings.** The obvious guess — the pledge is another EX-10 in the same
   accession — is wrong here. These are 8-K *amendment* filings; the security
   agreement went with the original facility, sometimes years earlier, and is
   incorporated by reference. Inspecting all six accessions produced exactly one
   EX-10 candidate, and the content gate correctly rejected it: **a warrant.**
2. **Full-text search re-finds the credit agreement.** EDGAR FTS for "security
   agreement" matches the document doing the *deferring*, so **4 of 5 first-pass
   hits were documents already in the corpus**, reported as recovery until a
   duplicate check caught it. `fetch_security_agreements.py` now excludes known
   documents.
3. **The one genuinely new document is another credit agreement.** Matched at
   Δ6 days, 519k characters, and it yields exactly one pledged category —
   `deposit_accounts`. No real property, equipment, receivables, or securities.

**Why the match window is tight.** Each obligor has 14–100 exhibits mentioning
"security agreement" spanning 2009–2026. A 2013 collateral schedule does not
describe a 2026 facility, and attaching one would produce data that **looks
public and is wrong** — strictly worse than the labelled engineering it would
replace. The window is ±14 days and the matched distance is recorded per
document, so the evidence travels with the claim.

**Standing position:** assets for those 20 facilities keep
`provenance_existence: synthetic — engineered` with the reason attached, distinct
from the 41 public-derived ones. The grant itself remains public. Recovering the
real schedules would need per-obligor filing-history archaeology back to each
facility's origination — real work with an uncertain yield, and out of scope
until something depends on it.

### 2.7 🔵 `prod.fibo-quickstart.ttl` is a curated subset, not full Production

8.2 MB, 2,719 classes, all 9 top-level modules. Concluding "term X does not
exist in FIBO" from that file would be wrong.

*This nearly produced a false conclusion about the Covenant gap.*

> **Superseded 2026-08-24 by §19.8 — read that instead.** The conclusion above
> is right and the reason given for it is not. This entry cited `CreditFacility`
> as absent from the file; it is present, 18 mentions, so the evidence has gone
> stale while the warning stayed true. The real mechanism is **maturity**:
> `prod` loads Release only and omits 40 Provisional modules. And the remedy
> here — "absence claims require the `edmcouncil/fibo` repository" — is no
> longer necessary: `dev.fibo-quickstart.ttl` is a verified strict superset and
> settles absence in one fetch.

---

## 3 · Engineered data — what is invented, and why

Per rule #1 these are labelled in the data. Listed here so nobody has to query
to find out.

### 3.1 Ownership depth chains — `synthetic — engineered`

Three families were re-parented from flat Exhibit 21 runs into 4-hop chains, so
`depth=3` visibly truncates. The subsidiary **names** are real (filed); the
**chain structure** is invented.

*Note:* 8 roots reach 4+ hops although only 3 chains were built — Celanese and
Hain Celestial get there naturally once GLEIF chains and EX-21 stubs compose.

### 3.2 Cross-shareholding cycle — `synthetic — engineered`

Three entities (`Meridian Holdings S.A.`, `Calder Industrial N.V.`,
`Thornbury Capital Ltd`) are **wholly invented**, as is the loop between them.
GLEIF Level 2 is a clean hierarchy; genuine cycles are effectively absent at
this scale.

### 3.3 Booking dates and the three lag cases — `synthetic — engineered`

Assertion time has **no public source** — when a bank booked an amendment is
internal. Three cases carry 4–8 week gaps (52d, 44d, 45d) with a drawdown
inside each.

### 3.4 🟠 Amendment effective dates — `synthetic — internal`

See §1.1. Derived, not filed. **The most likely thing for a reader to assume is
public and is not.**

### 3.5 122 of 180 covenants — `synthetic — internal`

EX-10 extraction yielded 58 covenants with real thresholds and offsets. §F wants
≥4 types per facility; the remaining 122 are engineered from conventional
templates, which §F explicitly permits ("the covenant structure itself where
EX-10 parsing yields too little").

### 3.6 Wholly invented, all labelled

Internal client IDs · risk grades · RM assignments · outstanding balances ·
undrawn availability · internal facility ratings · pricing-grid **margins**
(tier *thresholds* are public) · drawdowns · policy versions · breach events ·
non-LEI bridging stubs for EX-21 subsidiaries.

---

### 3.7 Control without ownership — `synthetic — engineered`

**Added 2026-08-19.** Three control-only edges, closing the estate's last
outstanding §F condition. `corporate-family-tree` §F wants at least one edge
where a party **controls** an entity it does not **own**; the estate had zero
from Wave 8 until now.

The hole was created by a correct fix. Wave 8 found that the 103 edges sitting
on `controls` were GLEIF ultimate-parent facts and moved them to
`hasGlobalUltimateParent` where they belonged. That was right, and it left
`controls` empty — visible as a deliberately failing check rather than masked.

**Why this cannot be fetched.** GLEIF Level 2 records ownership and
ultimate-parent relationships. It does not record golden shares, dual-class
voting trusts, or board-appointment rights granted under a credit agreement —
the mechanisms by which control routinely exists with no economic stake. No
public source this project can reach publishes them in structured form.

| Party | Mechanism | Controls |
|---|---|---|
| Ardsley Golden Share Trust | golden share — veto rights, no economic stake | `SpPlusCorporation` |
| Kestrel Founders Voting Trust | dual-class voting control | `CharterCommunicationsInc` |
| Pellworth Facility Agent | board-appointment rights under a credit agreement | `Wd40CompanyLimited` |

All three parties and edges carry `synthetic — engineered`. No `owns` edge is
written for any pair — that is the entire point. Targets are resolved from the
ledger, never constructed. Loader: `loaders/load_control_edges.py`.

**The check was also weaker than its own name, and that is fixed too.**
`conditions.py` measured this as a bare `COUNT(*)` of `controls` edges, which
any control edge would satisfy — including one between a pair that *also* owns.
The label promised control-WITHOUT-ownership; the query did not check it. It now
carries `FILTER NOT EXISTS { ?a owns ?b }`, so satisfying it requires the
structure it names. Had this not been fixed first, the condition could have been
turned green without ever creating the thing it exists to demonstrate.


## 4 · Extraction quality

### 4.1 🟡 Deterministic yield by field (60 documents)

| Field | Yield | Note |
|---|---|---|
| Effective date | 73% | |
| Administrative agent | 56% | |
| Commitment amount | 55% | |
| Pricing grid ≥3 tiers | 48% | |
| Amendment detected | 36% | |
| **Maturity date** | **38%** | 🟠 weakest — agreements say "the fifth anniversary of the Closing Date" as often as a date |

The loaded 45 facilities were **selected** for completeness, so their populated
rate is higher than the underlying yield. The gap is real; the selection hides
it in the table but not here.

### 4.2 🟡 Covenant extraction is sparse

44 covenants from 60 documents (~0.7/document). Only **1 document** naturally
carried ≥4 covenant types. Many cached EX-10s are amendments or consents that
restate nothing.

### 4.3 🟡 `secured_leverage` pattern was not widened

§1.4's fix was applied to `leverage`, `interest_coverage`,
`fixed_charge_coverage`, and `debt_service_coverage` — **not** to
`secured_leverage`, which still requires `not exceed` and will miss the
`to exceed` phrasing. Likely undercounts.

### 4.4 🟡 Exhibit 21 jurisdiction detection uses a fixed list

~65 named jurisdictions. Anything not enumerated is recorded as blank rather
than wrong, but coverage is incomplete.

### 4.5 🔵 31 documents carry unverified section references

Partly **intended** — `covenant-cross-reference` §F wants ≥1 covenant with an
unresolvable definition, emitted as Context Debt. But the rate also reflects
that the section-heading regex does not match every drafting convention, so some
"unverified" references are parser misses rather than genuine dangling
citations. **These two causes are not currently distinguished.**

---

## 5 · Infrastructure

### 5.1 🔵 Fluree 4.1.4 API differs from documented v3-era form

- `POST /v1/fluree/query` — `application/sparql-query`, **requires an explicit
  `FROM <ledger>`**; omitting it returns **HTTP 500**, not a helpful 400
- `POST /v1/fluree/update` — `application/sparql-update` + `Fluree-Ledger`
  header. SPARQL UPDATE sent to the *query* endpoint is refused
- `/v1/fluree/transact` does **not** exist

### 5.2 🟠 No OWL inference — must type explicitly for every queried role

A query for `Party` returns only entities *explicitly* typed `Party`. Subclass
and subproperty axioms are loaded and **not applied**. Already caused §1.6.

### 5.3 🔵 Fluree is append-only — corrections are auditable, not invisible

A retraction changes current state while remaining in history. Good for the
flagship, but it means a mislabel like §1.1 leaves a permanent trace of both the
error and its correction. Ledger `t` advanced 17 → 19 solely to fix a label.

### 5.4 🟠 The MongoDB host carries an unrelated live system

`192.168.4.76:27017` also holds **`rtdetect`** — 99 collections, ~5.5M
documents of live pool-safety telemetry. `ccf/config.py` refuses writes outside
`fibo_v2` and **exposes no database-enumeration helper**, because enumeration is
how an unrelated system gets caught in a cleanup loop. Keep it that way.

### 5.4b 🔴 API KEYS EXPOSED IN TRANSCRIPT — ROTATION OUTSTANDING

**2026-08-17.** A masking expression was written backwards
(`${val:-unset}` substitutes only when *empty*), printing five API keys in
plaintext into the session transcript: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`,
`COHERE_API_KEY`, `GOOGLE_API_KEY`, `OLLAMA_API_KEY`.

*Scope:* two local transcript files (mode 600) — this session's, plus a
pre-existing `homecams-v2` subagent transcript that already contained the same
key. Sent to the Anthropic API as conversation content and mirrored to
claude.ai (Remote Control was active). **Not** in git, not public, not to any
third party.

*Status:* **NOT ROTATED.** The user elected to proceed and rotate later.
`OPENAI_API_KEY` has since been used for the Wave 6 embedding run, so it has
real usage history to audit against after rotation.

*Action:* rotate all five; check each provider's usage dashboard.

### 5.5 🟡 `.env` is shared far beyond this project

It carries credentials for unrelated systems (home automation, SMTP, several
LLM providers, an ingest HMAC master key). Any process run in this directory
inherits all of them. Gitignored, so no git exposure — but the blast radius is
much larger than this project needs.

### 5.6 🔵 `NEO4J_USER` is 30 characters

A username that long is almost certainly an inline comment swallowed into the
value. Harmless now (Neo4j is dropped) and `python-dotenv` handles it, but other
tooling reading that file may not.

---

## 6 · Validator coverage gaps

### 6.1 🟠 Partition checks are one-directional

`validators/partition.py` asserts Fluree holds no Postgres-owned attribute. It
does **not** assert the reverse — that Postgres holds no typed edge, or that
Mongo holds no entity attribute. Single-writer discipline is only half-enforced.

### 6.2 🟡 No standalone join validator

The plan called for three gates: partition, **join**, conditions. Join checks
exist only as conditions entries (crosswalk orphans, anchor↔peer period
overlap). There is no systematic check that every correlation key the catalog
implies actually resolves.

### 6.3 🟡 `fl_distinct` truncates at LIMIT 200

The 4-hop and ≥4-covenant-type checks cap result rows. Both currently pass well
clear of their floors, so truncation does not change the verdict — but a count
returned by those checks is a **lower bound**, not a total.

### 6.4 🔵 Conditions register covers 6 of 21 products

`counterparty-reference-snapshot`, `obligor-financial-spread`,
`corporate-family-tree`, `covenant-in-force-as-of`,
`covenant-cross-reference`, `mnpi-wall-enforcement` — 45 checks. The other 15
have no executable conditions because 14 of their specs have not been read.

### 6.5 🟡 Near-duplicate and ranking-difference checks read cached files

`validators/conditions.py` reads `near_duplicates.json` and
`ranking_difference.json` rather than recomputing, because a pairwise embedding
scan is too slow for a gate. **A stale cache would pass a check that no longer
holds.** Re-run `validators/near_duplicates.py` and `validators/projection.py`
after any corpus change.

---

## 7 · Scope not yet addressed

| Item | Status |
|---|---|
| 14 of 22 context-product specs | not read; acquisition needs inferred from Q019 §4 only |
| Securitization / tranche FIBO terms | unbound |
| Derivatives / FX FIBO terms | unbound |
| Beneficial-ownership, officer, role FIBO terms | unbound |
| MongoDB corpus (Wave 6) | not started |
| SQLite departmental tables (Wave 7) | file exists, tables not created |
| AML synthetic-only enforcement | not yet exercised — no AML data loaded |
| PSC pseudonymisation | not yet exercised — no UK Companies House PSC data has been fetched (743 real named persons are loaded from Form 4 / DEF 14A / 8-K, but none of them are PSC records) |
| Second Fluree/Postgres instance for co-lender A2A | not started |

---

## 8 · Wave 10 defects — `client-360-coverage-graph`

Fluree `fibo-v2` t=303, 24,565 triples (Person 704, CorporateOfficer 323,
Banker 40, Interaction 2,050, Deal 32; isEmployedBy 701, isOfficerOf 323,
isDirectorOf 435, coversClient 150, participatedIn 8,032, relatedToDeal 129).
Postgres `ccf_v2`: person 743 (704 natural / 39 entity) · person_role 817 ·
person_name_variant 571 · person_crosswalk 1,315 · institutional_holder 22,476
(17,410 strong / 5,066 weak issuer-match band, post-§8.15 fix) · banker 40 ·
coverage_assignment 150 · interaction 2,050 · interaction_participant 8,032 ·
scoring_weight 6 · context_debt 136.

### 8.1 🟠 FIXED — EDGAR's `primaryDocument` names the rendered HTML view, not the XML

For a Form 4 filing, `primaryDocument` in the submissions index points at the
**XSL-rendered HTML view** of the ownership XML, not the XML itself. The
request still returns **HTTP 200 with an HTML body** — there is no fetch-level
failure to catch. 120 filings failed silently and identically before anyone
looked at the actual bytes rather than the status code. Fixed by stripping the
`xsl…/` rendering prefix before requesting the document. Recorded because the
failure mode — "the request succeeded and the content is simply the wrong
document" — will recur anywhere else EDGAR serves a rendered view by default.

### 8.2 🟠 FIXED — the 13F dataset naming convention changed mid-archive

SEC's structured-data ZIP naming moved from `<YYYY>q<N>_form13f.zip` to a date
range (e.g. `01mar2026-31may2026_form13f.zip`). The old pattern 404s cleanly —
not silently — but a caller that only checks "did the request succeed" against
a *different, older* quarter's file would not notice the mismatch. One quarter
loaded: `01mar2026-31may2026`.

### 8.3 🔴 FIXED — `manager_cik` was derived from the accession-number prefix, corrected

**What it was, precisely, because the first description of this was wrong and
would have misled downstream consumers:** the initial load derived each 13F
`manager_cik` from the accession number's own prefix. An accession number's
prefix identifies the **filing agent that submitted the paperwork**, not the
investment manager the filing is *about*. One agent can (and does) file for
many distinct managers, so every manager sharing an agent collapsed onto one
`manager_cik`. Measured impact: **63 of 2,450** `manager_cik` values mapped to
more than one distinct `manager_name`, one of them across **290** different
managers. This erased roughly **5,357** distinct institution-issuer
relationships in `institutional_holder` — the one table whose entire purpose is
relationship context, so the erasure landed exactly where it hurt most.

**This was originally misdiagnosed** as investment-discretion splits and
amendment duplication, and a corrective aggregation (`MAX` per key) was applied
on that theory. The theory was wrong: profiling the duplicate groups showed
they were mostly *different managers sharing a filing agent*, not one manager's
repeated filings. `MAX` would have silently kept the erasure. **Fixed properly**
by joining `SUBMISSION.tsv` for the real manager CIK, resolving amendments (see
§8.4), and summing discretion-split rows within one accession. Count at the
time of this fix: `institutional_holder` 22,450 rows, 4,040 distinct
managers, 0 `manager_cik` values mapping to more than one `manager_name`
(revised again by §8.15's separate `_norm_issuer` fix, to 22,476 rows / 4,044
managers).

### 8.4 🟡 13F amendment semantics, as implemented

The latest `/A` amendment per (manager, issuer, period) wins and supersedes its
originals; rows within a single accession are summed, because those are one
filing's investment-discretion line items and summing them is the manager's
actual reported position with no double-count. `FILING_DATE` in `SUBMISSION.tsv`
is `DD-MON-YYYY` and **must be parsed with `strptime`, not string-compared** —
a raw string comparison sorts by day-of-month first, then month name
*alphabetically*, then ignores the year entirely (`"13-APR-2026" <
"13-MAR-2026"` lexicographically, even though April is later). This produced no
wrong answers against the one loaded quarter (verified over all 33
multi-amendment groups) but would silently pick the wrong winning amendment the
first time two dates in a group crossed months non-alphabetically. Fixed before
load.

### 8.5 🟠 FIXED — `owner_kind` classified on the trailing token only

The Form 4 reporting-owner classifier looked only at the last token of the
owner's name to decide person vs. entity, so `CHARTER COMMUNICATIONS, INC.
/MO/` (ends in the EDGAR state-suffix `/MO/`) and `ESS Holdings Business Trust
I` (ends in `I`) both evaded it and were typed as `fibo-fnd-aap-ppl:Person`.
Fixed by scanning every token for corporate markers after stripping the state
suffix. **Both nodes were retracted from the Fluree ledger** (append-only —
the retraction is a permanent part of history alongside the original wrong
assertion) and the affected Postgres/Fluree loads were regenerated from a
reseeded pipeline rather than hand-patched, so the artifact still reproduces
the store it produced.

### 8.6 🔵 FIBO has `CorporateOfficer` but no `Director` class — deliberate asymmetry

Directorship exists only as the `isDirectorOf` edge; there is no
`ex:Director` class. This is **not an oversight** — it was checked and the
asymmetry left standing rather than minting a symmetric-looking class FIBO
itself does not have. See the vault punch list sent this wave.

### 8.7 🔵 A pre-existing `.gitignore` defect meant no source manifest was ever committable

Predates Wave 10. `sources/**` in `.gitignore` excludes the **directory**, and
git never descends into an excluded directory to evaluate further patterns —
so the `!sources/**/manifest.json` negation intended to re-include manifests
could never fire. **Zero** manifests were tracked across every wave from 4
onward, despite CLAUDE.md documenting them as tracked provenance records.
Fixed with `!sources/*/` (the shallower negation git can actually reach), and
the orphaned Wave 4 `sources/ex10/manifest.json` was committed alongside the fix.

### 8.8 🟡 136 roster members recorded as Context Debt

Natural persons on the coverage roster for whom no DEF 14A or 8-K rendering
was found — no display name could be resolved beyond the Form 4 filed name.
Recorded in `context_debt` rather than silently dropped or given a fabricated
rendering.

### 8.9 🟡 3 Form 4 filings could not be fetched

All three are `HTTPError`s against a single issuer (CIK 1008654) whose filer
agent names the ownership document `form4.xml` rather than the conventional
`ownership.xml`. Not retried past the harness's bounded transient-only retry,
because a 404/error on a differently-named document is a naming mismatch, not
a transient network fault.

### 8.10 🔵 `person_key_source = 'minted'` is expected to be zero — not a bug

The bounded-search person-resolution design only finds **renderings of names
it already holds** (from Form 4). Officers and directors who never crossed the
Form 4 reporting threshold (10% owner / officer / director) are structurally
invisible to this pipeline and are not captured. A `minted` count of zero is
the design working as intended, not evidence the minting path was never
exercised.

### 8.11 🔵 Deferred minors carried forward from the wave 10 execution ledger

Not fixed; recorded so the next wave can triage rather than rediscover.

| Where | What |
|---|---|
| `generators/form4.py:62` | redundant `int(cik)` cast in `raw_form4_url` — parameter is already typed `int` |
| `validators/test_form4.py:70` | "only form 4 is selected" is a weak discriminator at `lookback=2`; a `lookback>=3` case would test the filter more directly |
| `generators/form4.py` module docstring | claims a constructed URL "cannot fail loudly"; no test case pins `parse_form4`'s behaviour on HTML input (the exact failure mode §8.1 found) |
| `validators/test_persons.py:21-22` | continuation-line indent one space short in a wrapped import |
| `generators/persons.py:28-30` | `person_key` calls `int(cik)` unguarded; a non-numeric CIK would raise `ValueError`. EDGAR CIKs are reliably numeric so no caller is at risk today |
| `generators/extract_persons.py:104-105` | unreachable `if step is None: break` — the inner break always fires first; duplicate stopping logic, traced correct |
| `generators/extract_persons.py:45/71` | dead `seen` accumulator, populated but never read |
| `generators/fetch_def14a.py:27` | unused `DEF14A_ROOT` constant |
| `generators/fetch_def14a.py:112` | `filing_date` bound and never read |
| `generators/fetch_def14a.py` (`find_renderings`) | first-match-wins, so `variant_name` is *a* rendering, not *the* canonical one — document-position dependent |
| `generators/fetch_8k502.py` | surname search spans the whole 8-K filing, not an Item 5.02-scoped section, so `appointment_date` really means "filing date of an Item 5.02 8-K mentioning this surname" |
| `generators/fetch_13f.py` | memo dict `resolved` is unbounded in principle (bounded empirically at ~143,685 distinct issuer strings this run) — fine for a one-shot script, worth a comment if the memoisation pattern is reused in something long-running |
| `generators/resolve_persons.py` (def14a crosswalk rows) | hard-code `is_true_match=True` regardless of the computed `match_band`, so a row can read `match_band="weak"` **and** `is_true_match=True`. NOT a trap — see §8.14: this is the deliberate false-negative half of the imperfect-join demonstration, not a defect |
| `generators/resolve_persons.py` | `wave10_crosswalk.json` written non-atomically (`write_text`, no temp-and-rename); a crash mid-write truncates it |
| `generators/generate_coverage.py:137` | scans `officer_title` across **all** of a person's roles rather than the LEI under evaluation — a person with roles at two different anchors could be misclassified senior at one from a title held at the other. Latent only: exactly 1 of 706 natural persons holds roles at more than one LEI, and that person has no officer/non-officer split, so it never fires against this data |
| `generators/generate_coverage.py` | `gap_keys` exclusion is global by `person_key` rather than scoped to the withheld person's own LEI — over-excludes, so it cannot violate the §F requirement, just weakens it slightly |
| `generators/generate_coverage.py` | `if not eligible or not covering: continue` silently drops an anchor's whole allocation with no warning; inert today, would hide a shortfall if the roster ever shrank |
| — | no regression test guards the `people_by_lei` role-double-count dedup fix (Task 4/7); only a one-off manual count is on record |
| `loaders/remediate_person_owner_kind.py:69` | builds literal-object triples for `DELETE DATA` without the `esc()` helper used on the write side; safe for the two names actually remediated, would emit malformed Turtle on a label containing a quote or backslash |
| `loaders/remediate_person_owner_kind.py` | one-shot, two hard-coded keys, already run — kept as a historical record of the owner_kind retraction. **Closed 2026-08-19:** its sibling `remediate_wave10_interaction_edges.py` was folded into `load_fluree_wave10.py --reconcile` and deleted, so the undocumented retract/reload ordering no longer exists |
| `loaders/load_postgres_wave10.py` | long inline root-cause comments duplicate the commit message and the wave report |
| `validators/partition.py:177` | a pre-existing local `RDF_TYPE` assignment inside `check_fluree()` shadows the new module-level constant at line 51; values identical today, editing either independently would silently diverge |
| `sources/screening/wave10_name_variants.json`, `wave10_crosswalk.json` | one byte-identical duplicate row each, for person_key `0001785235` (Wendi Sturgis) — see §8.16 |

### 8.12 🟠 This wave attaches fabricated behaviour to real named individuals — read before treating any field as public

**This is the single most important fact about the Wave 10 estate, and until
this fix pass it had no entry here.** 743 real people, joined to real SEC
CIKs, now carry roughly 8,000 invented interaction-participant rows, roughly
2,000 invented meetings/calls (`interaction`), invented coverage assignments,
and invented relationship-strength scores.

**Real and public** (provenance `public`, sourced from Form 4 / DEF 14A / 8-K
Item 5.02, retrievable and verifiable on EDGAR): each person's identity — name
as filed, SEC CIK where one exists — plus their role (director / officer /
ten-percent owner) and, where a rendering was found, their title.

**Fabricated** (provenance `synthetic — internal` or `synthetic —
engineered`, per `person`, `person_role`, `interaction`,
`interaction_participant`, `coverage_assignment`, and `scoring_weight`
row-level `provenance` values): every interaction (`interaction` — ~2,000
rows), every participant link (`interaction_participant` — ~8,000 rows),
every banker coverage assignment (`coverage_assignment` — 150 rows), and
every relationship/recency weight (`scoring_weight`). **No interaction record
corresponds to a real event.** No named person in this estate ever attended,
called into, or was scored on any meeting recorded here — the meetings,
calls, and scores were generated by `generators/generate_coverage.py` against
a seeded RNG to satisfy §F volume and shape conditions, exactly as the design
states.

**This was a deliberate, disclosed decision, not an oversight.** Three
questions were put to the user before any fetch (`docs/wave10-design.md` §0),
including explicitly whether DEF 14A / Form 4 identities should enter as
filed or pseudonymized. The recommendation given was to pseudonymize, on the
grounds that this is the first wave to attach fabricated *behaviour* —
meetings, calls, relationship strength — to a real named individual, where
every prior wave's fabrication attached only to real *entities*. **The user
was shown this reasoning and chose to load real names as filed.** That
decision is recorded in the design doc, not just here, so it survives if the
question is ever reopened.

**CLAUDE.md's own person-data rules are unaffected and still bind.** Rule 3
(pseudonymize UK Companies House PSC data at ingestion) is untouched — it
names PSC specifically, no PSC data has loaded yet (§7 above), and Wave 10
loads Form 4 / DEF 14A / 8-K persons, not PSC records. Rule 2 (AML uses
synthetic entities only) is unaffected — no AML data loads in this wave, and
none of these 743 real people may ever be reused as an AML-typology party.

### 8.13 🟠 FIXED (partial) — `appointment_date` is self-contradictory on 51 of 613 rows; the field was never scoped to Item 5.02

`generators/fetch_8k502.py` searches the **whole text of an 8-K filing** for a
roster surname, not a section scoped to Item 5.02 (director/officer changes).
The resulting `person_role.appointment_date` (613 rows, `appointment_source =
'8-K Item 5.02'`, `provenance = 'public'`) really means "filing date of an
Item 5.02-flagged 8-K somewhere mentioning this surname", not "date this
person was appointed to this role". Two consequences, measured:

- **51 rows** asserted an `appointment_date` **later** than that same row's
  `first_seen` — i.e. the row claims the person was appointed to the role
  after they had already been observed filing in it. Self-contradictory
  within one row, and impossible to stand behind a `public` label. **Fixed**:
  `loaders/load_postgres_wave10.py` now runs an idempotent, scoped
  `UPDATE ... SET appointment_date = NULL, appointment_source = NULL WHERE
  appointment_date > first_seen` after load, so a reload reproduces the same
  51-row correction rather than requiring a one-off manual fix.
- **24 rows** sit at anchors where **another person shares the surname** —
  the whole-filing search cannot distinguish which same-surnamed officer an
  Item 5.02 8-K is actually about. **Not corrected** (no reliable
  disambiguation signal exists in the metadata-only design); left standing
  and disclosed here.

`loaders/load_postgres_wave10.py::earliest_appointment`'s docstring
previously claimed the value returned is "the date of original appointment to
the role". That is not true even for the rows left standing: the fetch runs
with `--max-per-issuer 12` (12 most recent 8-Ks per issuer), so the earliest
*reachable* filing bounds the value, not the earliest filing that exists.
Docstring corrected to say so.

### 8.14 🔵 DOCUMENTED, not fixed — 50 weak-band true matches are the deliberate false-negative half of CLAUDE.md rule 5

`person_crosswalk` holds **50 rows** with `match_band='weak' AND
is_true_match=TRUE`, against exactly **1** row that is a genuine false
positive (`Davison James E` / `Davison James E. Jr.`, CIKs 1403411/1403412 —
see `validators/test_persons.py` docstring). This was logged mid-wave as a
suspected trap and that logging was wrong; it is not being changed.

`is_true_match` is **ground truth**: the name variant was discovered by a
bounded search anchored on an already-known `person_key`, so by construction
it *is* the same person. `match_band` is a completely separate signal — what
a name-only fuzzy scorer, with no knowledge of the anchor, would conclude
from the string alone. A row where the ground truth says "same person" and
the name-only score says "weak" is therefore a **false negative**: a resolver
that trusted `match_band` alone would wrongly discard a real match. That is
the other half of CLAUDE.md rule 5 ("some joins must be imperfect on
purpose") — the estate now demonstrates both failure directions a real
identity-resolution system produces: **50 false negatives** (weak band, true
match) and **1 false positive** (strong-scoring pair, different people).
Collapsing either number to zero, or forcing `is_true_match` to track
`match_band`, would destroy one of the two demonstrations. **Data and loader
are unchanged.**

### 8.15 🟠 FIXED — `fetch_13f.py::_norm_issuer` did not strip EDGAR's `/XX/` state suffix, mis-banding ~1,850 rows as `weak`

Same root cause as §8.5's `owner_kind` defect, in a second consumer.
`_norm_issuer` tokenizes and drops common corporate stopwords (`inc`, `corp`,
`llc`, ...) but never stripped EDGAR's trailing `/XX/` state-of-incorporation
marker first, so `"AMPHENOL CORP /DE/"` normalised to `"amphenol de"` — the
two-letter state code survived as if it were part of the issuer's name and
dragged the fuzzy-match score down to 0.8421 (`weak`) against the anchor's
clean `"amphenol"`. Stripping the suffix first raises that pair to 1.000
(`strong`/exact).

**Fixed by exporting `generators/form4.py`'s `STATE_SUFFIX` regex** (renamed
from the module-private `_STATE_SUFFIX` it shipped as after the §8.5 fix) and
importing it into `fetch_13f.py` rather than writing a second copy — the
`owner_kind` fix had already solved this exact problem for Form 4 reporting-
owner names and left it trapped in one module.

Re-run against the cached 99 MB archive (parse-only, no re-download) and
reloaded:

| | before | after |
|---|---|---|
| `institutional_holder` rows | 22,450 | 22,476 |
| `issuer_match_band = 'strong'` | 15,712 | 17,410 |
| `issuer_match_band = 'weak'` | 6,738 | 5,066 |
| distinct `manager_cik` | 4,040 | 4,044 |

~1,698 rows crossed from `weak` to `strong` once the suffix stopped
suppressing their score. The small net increase in total rows and managers
(+26 / +4) is a second-order effect of the same fix: a handful of
issuer/anchor pairs previously scored just under the 0.80 `weak` floor
because of the un-stripped suffix and now clear it, so they enter
`institutional_holder` for the first time rather than being silently
dropped as unmatched. All other loaded counts (Form 4, DEF 14A, 8-K,
coverage graph) are untouched — this fix touches only 13F issuer matching.

### 8.16 🟡 First real catch by `validators/artifact_reproduces_store.py` — one duplicate row, benign, in two artifacts

The new validator (§F below) found a genuine row-count divergence on its
first run: `wave10_name_variants.json` carries **572** entries but
`person_name_variant` holds **571**; `wave10_crosswalk.json` carries **1,316**
but `person_crosswalk` holds **1,315**. Both are explained by the SAME cause —
a single byte-identical duplicate row for `person_key = '0001785235'`
(Wendi Sturgis), in both files.

**Mechanism, not a data-quality defect:** Sturgis holds a director role at
TWO different anchor LEIs (`529900L7KB2N9KXCDI76` and `529900VKCYZW8GZ4WW58`).
`find_renderings` runs once per anchor's DEF 14A text, and at both companies
her name happened to render identically as "Wendi Sturgis" — so the per-anchor
search independently produced the same `(person_key, variant_name, source,
rendering, provenance)` tuple twice. `person_name_variant`'s primary key
`(person_key, variant_name, source)` — and `person_crosswalk`'s corresponding
key — silently absorb the second insert via `ON CONFLICT DO NOTHING`, so the
loaded tables were never wrong; the redundancy was invisible until something
compared the artifact's raw row count against the table's row count directly,
which no validator did before this one.

**Not fixed.** The loaded data is correct (content-equality passes exactly;
only the raw artifact row count differs from the stored row count), and
de-duplicating the generator's per-anchor rendering pass is a small, separable
cleanup rather than a correctness fix. Recorded here rather than silently
tolerated, per the validator's own instruction not to paper over what it
finds.

## 9 · Wave 11a defects — `rating-and-spread-migration`

### 9.1 🟠 FIXED 2026-08-19 — `context_debt.reason` was stale for 134 of 169 `rating_action` rows; the artifact and the live store genuinely disagreed

`validators/artifact_reproduces_store.py`, extended in Task 9 to
`wave11a_rating_actions.json`, found a real content divergence — not a
formatting artifact of the check, unlike the tenor-precision false alarm
this same task pass triggered and fixed on `benchmark_curve` before landing.

**What disagrees.** For every unconfirmed rating-action candidate,
`generators/fetch_rating_actions.py` writes a `context_debt` row via:

```sql
INSERT INTO context_debt (...) VALUES (...)
ON CONFLICT DO NOTHING
```

`fetch_rating_actions.py` went through three regex tightening rounds
(`d7b86f4` -> `753e459` -> `74cae69` -> `de1acb8`), each changing the
`reason` text an unconfirmed candidate is recorded with. `ON CONFLICT DO
NOTHING` means a later run's INSERT for an accession already present from
an earlier run is silently discarded — the row is never refreshed to the
current run's wording. 134 of the 169 live `context_debt` rows for
`subject_kind = 'rating_action'` still carry the round-1/round-2 reason
text ("no action-language (downgrade/upgrade/affirm/outlook/withdrawn/
watch) was found ...") even though the committed `wave11a_rating_actions.json`
— reflecting the current, round-3 `confirm()` logic — records the
round-3 text ("no declarative, dated rating-action language survived the
definition/condition/negation filters ...") for those same accessions. Only
35 rows happen to match, because those 35 accessions were new to a later
sweep run rather than re-inserted.

**Not a §F blocker.** `context_debt` is a lineage/gap-tracking table, not a
`rating-and-spread-migration` §F floor — none of the seven conditions in
`validators/conditions.py`'s `rating-and-spread-migration` section reads it,
so this does not put any condition at risk. It is exactly the kind of thing
`artifact_reproduces_store.py` exists to surface, though: the committed
artifact is not, right now, a faithful record of why 134 candidates were
rejected in the live store.

**Not fixed here [as of Task 9].** Task 9's scope is validators; fixing this
needs either a `DELETE ... WHERE subject_kind = 'rating_action'` before the
reconciling INSERT (matching the confirmed-accession branch's own
reconcile-not-append pattern two lines above it in the same script) or an
`ON CONFLICT DO UPDATE SET reason = EXCLUDED.reason`. Left for a follow-up
fix pass rather than patched inside a validators-only task.

**Fixed in Task 10.** `generators/fetch_rating_actions.py`'s `context_debt`
insert now reads:

```sql
ON CONFLICT (subject_kind, subject_key) WHERE subject_kind IS NOT NULL
DO UPDATE SET reason = EXCLUDED.reason
```

`DO UPDATE` needs an explicit conflict target, and because
`ux_context_debt_subject` is a **partial** unique index (`WHERE subject_kind
IS NOT NULL`, added in Wave 10 precisely so Wave 9's covenant rows —
`subject_kind IS NULL` — never participate), the target must repeat that
same predicate for Postgres to infer it as the arbiter; a bare `ON CONFLICT
(subject_kind, subject_key)` without the `WHERE` clause fails to match the
index at all. The literal value inserted is always `'rating_action'`, so the
clause can only ever collide with an existing `rating_action` row — Wave
10's 135 `subject_kind='person'` rows share the same index but never the
same `subject_kind` value, so they are structurally unreachable by this
statement.

Re-ran parse-only (the 99 MB of cached EDGAR documents were not re-fetched;
`sources/` manifest hits were 178/178). Verified directly against the live
table after the run:

| Check | Before | After |
|---|---|---|
| `rating_action` rows total | 169 | **169** — unchanged |
| rows carrying the current (round-3) `reason` wording | 35 | **169** — all of them |
| rows carrying stale round-1/round-2 wording | 134 | **0** |
| `subject_kind='person'` rows (Wave 10) | 135 | **135** — untouched |
| `wave11a_rating_actions.json` confirmed / candidate counts | 9 / 178 | **9 / 178** — unchanged, this fix touches only the gap explanations, not the classifications |

The classifications were never wrong — only the stated reason for 134 of
them described a gate (the round-1/round-2 heuristic) that no longer exists.
`artifact_reproduces_store.py` now reports agreement on this artifact
(40/42, up from 39/42 — the two remaining failures are the pre-existing
Wave 10 duplicate-row items, §8.16, untouched by this wave).

**Refreshed again in the fix pass (2026-08-19).** The final whole-branch review
found the round-3 wording itself was wrong: it advertises a "dated"
rating-action gate that `de1acb8` deleted when it removed the inert `DATE_RE`
check. Corrected to "no declarative rating-action language survived the
definition/condition/negation filters", and the fetcher re-run parse-only (all
178 document hits served from cache, zero refetches). Verified against the live
table: 169 `rating_action` rows, **169 carrying the corrected wording, 0
carrying the stale text**, Wave 10's 135 `subject_kind='person'` rows untouched,
and 9/178 confirmed — classifications unchanged, as before. The artifact diff is
exclusively `reason` strings plus the `generated_at` timestamp.

**A third copy of the same sentence surfaced during that verification, inside
the validator.** `validators/artifact_reproduces_store.py:558` held its own
hardcoded restatement of the reason text, under a comment claiming it was
"reconstructed from the SAME source (importing `WINDOW`) rather than
copy-pasted, so a future edit to either literal shows up here as a mismatch
instead of silently comparing against a frozen copy." It imported `WINDOW`;
it froze the sentence. So correcting the generator made the check report
**"artifact and store disagree" when artifact and store agreed exactly and the
validator was the stale party** — it failed loudly, which is right, but named
the wrong two parties. A check that misattributes divergence is worse than no
check, because it sends the reader hunting in the data.

Fixed in two steps, and the first step was itself wrong. Both reason strings
became module constants `REASON_SEARCHED` / `REASON_UNSEARCHED` in
`generators/fetch_rating_actions.py` (correct, and still in place — it
de-duplicates the generator's own two branches), and the validator was changed
to import them. **Code review caught that this only inverted the defect.**
Importing the constant still compares the *generator* against the store, not
the artifact against the store: edit the constant without re-running the
fetcher and the check again reports divergence between two things that agree.
Worse, because the artifact's own `reason` was never read, a hand-edited or
corrupted `reason` in the artifact passed unnoticed — a silent hole in the one
file named for catching exactly that.

**Final form:** the validator compares `r["reason"]` from the artifact against
the `reason` column in `context_debt`, and imports nothing. That is the only
version that tests what the file is named for. Verified byte-identical across
all three representations before landing — one distinct reason value in the
artifact, one in the live table, identical to each other and to the constant.

The general lesson, three times in one table: **when you delete a condition,
its name survives in every string that described it** — and the search for
that name has to run across the whole estate, including the validators that
assert against it. A comment claiming a copy is not a copy does not make it
so; only an import does.

### 9.2 🟠 FINRA TRACE is licensed and unreachable — §C names it, the free API does not carry it

**The headline finding of this wave, and the one sent to the vault.** §C
names FINRA TRACE for "corporate bond transaction prices and yields",
described as "publicly disseminated (delayed)". That description is **true
and misleading in the same breath**. Dissemination means individual prints
hit the tape for anyone with a terminal; it does not mean 60 instruments ×
24 months of history is downloadable in bulk without a licence, and §F needs
exactly that bulk shape.

Probed FINRA's free Query API on 2026-08-19, every group root:

| Endpoint | Result |
|---|---|
| `api.finra.org/data/group/{otcMarket,fixedIncomeMarket,traceMarket,...}` | **404** on every group root |
| `.../otcMarket/name/{traceCorporateBond,corporateBond,traceBond}` | **404** |
| `.../otcMarket/name/weeklySummary` | **200** — but it is **equity ATS volume**, not TRACE bond data |

The one endpoint that returns anything (`weeklySummary`) carries rows like
`BRKR, Bruker Corporation Common Stock, JPBX, ... totalWeeklyTradeCount,
totalWeeklyShareQuantity` — equity tickers (Bruker, Hyatt among them), share
counts, no prices, no yields, no bonds, no CUSIPs. **Bond-level TRACE
history is FINRA's licensed product**, structurally the same shape as the
Wave 9 UCC-1 finding and the agency-rating-feed licensing note §C already
carries elsewhere: a source that is real, correctly named, and not freely
obtainable in the bulk form the envelope requires.

**§C already contains exactly the right reasoning for this — applied to the
wrong source.** It names S&P/Moody's/Fitch agency rating feeds as licensed
and instructs treating that as unavailable rather than an integration to
build, and offers three substitute legs. TRACE needs the identical
treatment; this is the finding sent to the vault (§10 below).

**The sanctioned substitute — a three-leg spread model, provenance split
per column, not per row:**

```
yield(instrument, t) = benchmark(tenor, t)            Treasury par curve   [public]
                     + oas(rating_band, t)            FRED ICE BofA        [public]
                     + idiosyncratic(instrument, t)   engineered           [synthetic — engineered]
```

The **market factor is genuinely public** — Treasury's daily par yield
curve and FRED's five ICE BofA OAS-by-rating-band series, both real,
both moving with the actual 2024–2026 credit cycle. Only the
**instrument-specific level** — the idiosyncratic component that puts one
BB-rated mid-market issuer's spread a few basis points from another's — is
`synthetic — engineered`. `spread_observation` stores `benchmark_bp`
(public), `market_oas_bp` (public) and `idiosyncratic_bp` (engineered) in
separate columns precisely so a consumer can always ask what was observed
and what was built, rather than receiving one blended `spread_bp` number
whose provenance has been flattened away.

### 9.3 🔵 XBRL `companyfacts` cannot substitute for instrument reference data — it flattens away the dimensional context

§C's own fallback for instrument reference, when TRACE reference data is
unavailable, is "EDGAR debt-security registrations". Probed `companyfacts`
for the four anchors with the largest filing histories:

| CIK | us-gaap tags | Debt-instrument tags present |
|---|---|---|
| 1059262 | 452 | none |
| 1091667 | 504 | `DebtInstrumentFaceAmount` — 121 facts |
| 1094831 | 696 | `DebtInstrumentInterestRate{Effective,Stated}Percentage` — 1 fact, 2012 |
| 1632970 | 410 | `DebtInstrumentInterestRateEffectivePercentage` — 1 fact, 2016 |

Two problems, either alone disqualifying. Coverage is wildly uneven — 121
facts for one filer, a single stale fact for another. And **`companyfacts`
flattens away the dimensional context**: XBRL debt-instrument facts are
qualified by an axis identifying *which* instrument a fact belongs to, and
the flattened `companyfacts` API drops that axis. So even the filer with
121 face-amount facts cannot have any of them attributed to a specific
instrument — the numbers exist, but "which bond" does not survive the API.
Instrument reference is therefore `synthetic — engineered`, not fetched,
same conclusion and same reasoning as §9.2's spread level.

### 9.4 🔵 The pagination lesson, twice in one wave

**First occurrence, at design time.** §F wants ≥ 1 obligor with a rating
action disclosed in a real 8-K. Rating actions surface as Item 8.01 prose
with no metadata flag to select on. EDGAR full-text search, **first page
only**, found **1** anchor. The same sweep **with paging** found **5**
anchors across 14 filings. A probe that stops at page one would have
committed this spec to a zero-margin condition it does not actually have —
the true floor clears five times over.

**Second occurrence, inside the implementation itself (Task 3).** The
lesson "the sweep must page" was written into the design and the fetch
script paged — but only to `pages=4` (400 hits per query), the helper's
default. Measured directly: the five rating-action queries carry 406 / 229
/ 942 / 8,858 / 7,735 total hits, and reading at most 400 of each meant the
sweep was reading **1,829 of 18,170 hits — about 10%**, with four of five
queries hitting the page cap. With 90% of each query's results unread and
no guaranteed result ordering, **a different anchor set on every run was
the expected outcome, not evidence of "EDGAR FTS index movement"** — which
is what the sweep's own output was first (wrongly) attributed to. The
symptom was instability across consecutive runs; the cause was
incompleteness, not a changing source.

**The fix that actually worked was not "page deeper."** 8,858 hits is 89
pages for a single query, against a cast of 50 of roughly 8,000 filers on
EDGAR — a whole-corpus read is the wrong shape at any depth. EDGAR FTS
accepts a `ciks` parameter that filters at the query instead: restructured
to query per `(CIK, query)` pair (50 × 5 = 250 small requests, well inside
the harness's 8 req/s limit), each returning a handful of hits, zero
truncation, and a result that no longer depends on global ranking. Verified
against Avis Budget Group directly: `ciks=0000723612` on "Fitch Ratings"
alone returned 26 total / 26 returned, complete, against 6 filings the
whole-corpus sweep had found for Avis across **all five** queries combined.

**Rule for future waves: instability across runs is evidence of
incompleteness, not of the source changing underneath you.** If two runs of
the same paged sweep disagree, the first suspect is a page cap being hit
below the true hit count, not the live index moving.

### 9.5 🟠 `ciks=` unpadded returns a silent zero — indistinguishable from "no results"

A second trap sits directly behind §9.4's fix. `ciks=723612` (unpadded)
returns `total=0` with **no error** — not a rejected request, not a
malformed-parameter response, a confident **empty result**. Passed the
wrong format and EDGAR reports "no results" exactly as it would for an
anchor that genuinely has no rating-action filings; the two are
indistinguishable from the response alone. The CIK must be zero-padded to
10 digits (`0000723612`), and the fetch code **asserts** the padding rather
than trusting the caller — this is a silent-empty-result trap, the project's
recurring failure shape, caught before it could report 46 anchors as
rating-action-free when the truth was that their CIKs were simply
malformed.

### 9.6 🔵 The Treasury par-yield CSV schema changes mid-window — the header must be read per file, never hardcoded

Design-time assumption (recorded in `docs/wave11a-plan.md`'s verified-facts
table and `generators/curves.py`'s original `TENORS` docstring): the
Treasury header is a fixed 15 columns, with `1.5 Month` "published and
almost always empty". **Both halves of that claim are wrong.** Verified
directly against the fetched files: **2024 has 14 columns and no `1.5
Month` column at all**; **2025 and 2026 have 15 columns**, and `1.5 Month`
is populated on essentially every row in those years — Treasury added a
6-week bill benchmark in 2025, so the CSV schema genuinely changes partway
through the 24-month window this wave needs.

`generators/curves.py::parse_treasury_row` reads the header **per file**
rather than assuming a fixed one, so alignment was correct throughout —
this was a documentation defect, not a data defect, and both wrong
statements (the docstring and the plan's verified-facts table) were
corrected in place during Task 2. It is recorded here because of how close
it came to being a real one: `strict=True` on the row `zip()` (added one
fix round earlier, in Task 1, for an unrelated finding) would have made
2024 raise loudly on row one had the header ever been hardcoded to 15
columns; *without* that guard, a hardcoded 15-column header would have
zipped 14 real cells against 15 labels and shifted every yield in all of
2024 by one tenor — a full year of smooth, plausible, silently wrong
benchmark data feeding every spread computed against it. Two independent
things — the per-file header read, and a defect fix landed for an unrelated
reason an hour earlier — are jointly what made this a non-event rather than
this wave's headline defect. **Rule for any future Treasury or similar
government CSV: read the header from the file, every time; never hardcode
it from one year's sample.**

### 9.7 🔴 FIXED — a bare-verb regex marked contractual boilerplate as confirmed rating actions; ~30 of 40 were false positives, one was the literal opposite

**The most serious defect in this wave.** The original `confirm()` heuristic
matched a bare verb stem (`downgrad\w*`, etc.) within 300 characters of a
rating-agency name, with no test for defined-term, conditional, or negated
framing. Reading the cached filings behind the labels (not trusting them)
found that **roughly 30 of 40 rows marked `confirmed: true` were false
positives**:

- All six Avis Budget Group "confirmations" resolved to the **same**
  credit-agreement pricing-grid clause — *"In the event either Moody's or
  S&P shall cease to assign a Specified Rating, then the Applicable Margin
  ... shall be based on Level III"* — a margin ratchet, not a rating
  action.
- One Murphy Oil filing was an underwriting-agreement closing condition
  asserting that **no** downgrade had occurred — *"there shall not have
  been any downgrading, nor any notice given of any intended or potential
  downgrading"* — **the literal opposite** of the event being recorded.
- Four more matched the bare defined term *"'Downgrade Event' shall have
  the meaning ascribed to in Section 2.7(b)..."*.

The confirmation bar had **not loosened between runs** — the same six Avis
accessions were already marked confirmed in the very first transcript,
before the per-CIK pagination fix (§9.4/§9.5). A smaller candidate pool
(16, pre-fix) had simply been masking how bad the heuristic already was;
finding **more** data (178 candidates, post-fix) exposed a defect that
finding **less** data had hidden, the inverse of the usual failure shape in
this project's history.

**Fixed across three rounds:**

1. `REJECT_RE` added — fires on definitional (`means`, `shall have the
   meaning`), conditional (`in the event`, `provided that`), pricing-grid
   (`Applicable Margin`, `Advance Rate`, `Level I`..`Level V`) and negated
   (`shall not have been`, `no ... downgrading`, `nor any`, `will not`,
   `has/have not`) framing, checked **first and unconditionally** — a
   defined-term or negated clause frequently also contains a bare action
   verb, which is exactly how the original regex was fooled.
2. `DECLARATIVE_RE` added — requires an actual declarative, past-tense
   construction ("was downgraded", "downgraded ... to ... from ...", "has
   assigned a ... rating", "announced that") rather than any bare verb
   stem. Confirmed count: **40 → 9**. `context_debt` grew **138 → 169** —
   the correct direction, since a stricter confirmation gate should produce
   more honest gaps, not fewer.
3. A `DATE_RE` gate (requiring a date token anywhere in the 300-char
   window) was added, found to pass for the wrong reason — see §9.8 — and
   dropped.

A fetch-failure mislabelling bug was fixed in the same pass: a candidate
whose document fetch failed entirely had been falling through to a
`context_debt` reason claiming "no action-language was found ... in the
fetched document(s)", which is false when nothing was fetched (0 rows
exercised this wave — 178/178 fetches succeeded — but the mislabelling was
real and is fixed via an honest `searched` flag).

**Swept all 169 demoted rows for over-correction**: zero genuine rating
actions were found wrongly rejected. The two genuine confirmations that
survive intact — Vertiv Holdings (Moody's/S&P upgrades, three separate
8-Ks) and, at final count, three others across four anchors total (Targa
Resources, Celanese, Independence Realty Trust, Vertiv Holdings) — are real,
citable, and were never in question.

### 9.8 🔵 `MIN_WINDOW_OBS` is verified-present, not verified-discriminating

`validators/series.py`'s `MIN_WINDOW_OBS = 10` encodes that §F's "the
spread widened" describes a *period*, not a single day's blip. Measured
directly against the live data (2026-08-19): setting it to 1 and
re-running reproduces the **identical** four divergence windows — same
instruments, same dates, same counts — because every one of the 56
non-divergent, non-sparse instruments tops out around 9bp of delta-over-
baseline against thresholds of 80–120bp, roughly 25 AR(1) standard
deviations short of ever tripping on a single day in this seed. That makes
the floor **untested against current data, not meaningless**: unlike
Task 3's `DATE_RE` (§9.7 point 3), which was dropped because it was
provably *redundant* with `REJECT_RE`/`DECLARATIVE_RE` (a declarative
rating-action sentence already implies a dated event, so no data could ever
have made it discriminate), `MIN_WINDOW_OBS` is the **only** thing in
`detect_windows` encoding that a one-day spread blip is not a divergence —
removing it would change what the check *means*, not just today's output.
**Kept, honestly labelled as verified-present rather than
verified-discriminating** — the distinction that separates "this defensive
bound has not yet been exercised" from "this defensive bound is decoration".

### 9.9 🔵 Deferred minors carried forward from the wave 11a execution ledger

Not fixed (except the docstring correction noted below, folded into this
sweep as trivial and directly requested); recorded so a later pass can
triage rather than rediscover. Every line number below was checked against
the file as it stands at the end of this wave, not copied from the plan —
see the note under §8.11 about Wave 10 shipping six wrong citations that way.

| Where | What |
|---|---|
| `validators/test_curves.py:62` | asserts `tenor_years("1.5 Month") is not None` rather than the value `0.125`; a mistyped mapping would pass undetected |
| `generators/curves.py:88` | `if span == 0: return curve[lo]` inside `interpolate_tenor` is unreachable — the exact-match case (`years in curve`) returns earlier and `lo`/`hi` are strictly bracketing by construction, so `span > 0` always |
| `generators/curves.py:58` | `parse_treasury_row` calls `parse_treasury_date(row[0])` unguarded; an empty row raises a bare `IndexError` rather than a clear diagnostic |
| `generators/fetch_treasury.py:62`, `generators/fetch_market_oas.py:65` | `next(reader)` on an empty CSV raises `StopIteration` — loud but not a friendly diagnostic; the FRED path already hand-writes a `RuntimeError` for header mismatch and this could match that style |
| `generators/fetch_market_oas.py:78` | `points[0]['date']` / `points[-1]['date']` would raise `IndexError` if a FRED series ever returned zero usable points |
| `generators/generate_instruments.py:471` | the rating-action force-include unions LEIs into the obligor set without re-checking the `>= 1 Item 2.03 filing` eligibility filter; provably inert today (all 50 anchors satisfy it) and the fallback path carries an honest `provenance_note`, but the docstring claims only to override rank, not the filing restriction |
| `generators/generate_instruments.py:231` vs `:258-259` | `MATURITY_CEILING` is computed via `add_years` (`timedelta(days=round(years * 365.25))`, day-rounded) while `eligible_tenors`'s reporting check divides `.days / 365.25` directly — two date-arithmetic paths for one nominal quantity, agreeing today only because the margin between them is wide |
| `generators/generate_instruments.py:259` | `eligible_tenors`'s no-rung-fits fallback (`min(math.ceil(required_years), math.floor(ceiling_years))`) could theoretically return 0 years for an issue date within roughly 1.6y of the ceiling, producing a same-day maturity; unexercised — anchor filings run 2012–2026 against a 2052 ceiling |
| `generators/generate_instruments.py:464-621` | `main()` is ~158 lines mixing argument parsing, note-building, statistics, printing and file-writing in one function |
| `generators/generate_spreads.py:220` (`divergence_weight`) vs `:381` (`in_any_divergence_window`) | `divergence_weight` returns `0.0` at both window boundary dates (`d == start`, `d == end`) while `in_any_divergence_window`'s inclusive `start <= obs_date <= end` counts those same two dates as inside the window — so two zero-contribution dates per window are excluded from the dominance-ratio pool. Immaterial and conservative in direction (it shrinks the engineered numerator, never inflates it), but the two functions disagree at their own boundary |
| `generators/generate_grades.py` | two of the six catalogued off-cycle rerating triggers go unused in this seed's random draw across the 245 assertions generated |
| `loaders/load_postgres_wave11a.py:290` | `rating_scale_rows` hardcodes the literal `"synthetic — internal"` instead of reading `grades_doc["provenance"]["grade"]`; the two values agree today, and would drift silently from each other if the upstream artifact were ever recalibrated to record a different provenance string |
| `loaders/load_postgres_wave11a.py:39` | **fixed in this sweep** — module docstring claimed the divergence thresholds are "70-110bp"; the live `DIVERGENCE_THRESHOLD_BP` table (line 110) actually spans 80 (Finance, Insurance & Real Estate) to 120 (Mining). Corrected to "(80-120bp)" |
| `loaders/load_postgres_wave11a.py:295` | opens a `pg_connect()` read-only connection (for the `legal_entity.sic` lookup) **before** the `--dry-run` check at line 317, so `--dry-run` is not fully offline — it still issues one `SELECT` against the live database |
| Task 3 report wording | the fetch manifest grew 228 → 233 records in the confirm()-tightening round, in tension with that round's own "0 new document fetches" framing; reconcilable (the stricter heuristic stops confirming earlier and so reaches secondary documents the looser one never fetched, and the *following* stability run genuinely made zero new fetches) but the report sentence itself should have said so |
| Independence Realty Trust rows | four IRT rating-action confirmations repeat near-verbatim across sequential quarterly investor-presentation filings — structurally the same shape as the Avis pricing-grid repetition (§9.7) but far milder (four genuinely distinct confirmed events, not one clause counted six times); a candidate for a distinct-event-vs-restated-fact pass if that precision ever becomes load-bearing for a downstream product |

### 9.10 🟠 FIXED 2026-08-20 — the market leg is pinned to the day-1 rating band and never follows a grade migration

`generators/generate_spreads.py:360` selects `oas[band][d]` where `band` is
`debt_instrument.rating_band`, fixed when the instrument is generated.
`generators/generate_grades.py` then lets an obligor's grade drift across band
boundaries over the same 24-month window. Neither file is wrong on its own;
together they are inconsistent — **in a product named
`rating-and-spread-migration`**.

Measured on the loaded data — 3 of 30 obligors, 6 of 60 instruments:

| LEI | market band pinned at | grade band reached | duration off-band | unreflected OAS gap |
|---|---|---|---|---|
| `5493003QENHHS261UR94` | BB | B | 182 days | ~122 bp |
| `5493004HBTOTE9DI9P12` | BBB | BB | 145 days | ~75 bp |
| `549300EQD0ZXRSMG3549` | B | BB | 92 days | ~122 bp |

Same magnitude as the engineered divergence windows (peaks 160–240bp against
sector thresholds of 80–120bp) but **opposite in direction and unlabelled**. A
consumer asking "did the market reprice when the grade moved?" gets *no*, three
times, with nothing in the data recording why.

**No §F condition fails and no provenance is mislabelled.** Checked directly:
none of the seven `rating-and-spread-migration` conditions in
`validators/conditions.py` requires a *band* crossing — "divergence later
confirmed by a worse rerating" is satisfied by a notch move. So this is not a
correctness blocker.

**Why no review caught it.** Task 5 generated spreads before Task 6 existed to
generate grades. The contradiction lives *between* two units reviewed at
different times, and a sequenced plan has no feedback path backward. Reviewing
either task harder would never have surfaced it. The general lesson: fan-out
plans need an explicit cross-cutting pass at the seams.

**Ruled 2026-08-19: document, do not reprice.** The four options and why three
were rejected:

| | Approach | Why not |
|---|---|---|
| **A** | Document only — **taken** | Cost lands entirely on Wave 11b; mitigated by carrying it as 11b's first open question |
| B | Re-band on the migration date | ~122bp step discontinuity — an unlabelled artifact as bad as the one it fixes; real repricing is gradual and anticipatory |
| C | Glide between band curves | The honest fix, but a glided value is neither index — a synthetic interpolation between two real series, breaking the "provenance never blends within a column" rule. Needs a fourth column or a provenance downgrade during transitions: an 11b design decision, not an 11a patch |
| D | Constrain grades to stay in-band | Passes §F, but deletes the migration case entirely — the 3 band-crossers *are* the interesting population |

That ruling stood while the cost sat in the future. It does not any more: the
moment Wave 11b starts building a detector against this series, a market leg
that never notices a migration would teach that detector the wrong lesson.
Cheaper to pay the fix now than to let it compound downstream.

**Correction to the original measurement: 4 crossings, not 3.** The table
above lists one row per obligor and reads as three crossings. It is **4
crossings across 3 obligors, two of them upgrades** —
`5493003QENHHS261UR94` crosses twice (BB→B on 2025-11-19, then B→BB on
2026-05-23, the two together being one downgrade and one upgrade for the same
obligor), `5493004HBTOTE9DI9P12` crosses once (BBB→BB, downgrade), and
`549300EQD0ZXRSMG3549` crosses once (B→BB, upgrade). Corrected explicitly
here rather than silently.

**Fixed 2026-08-20**, per `docs/wave11a-migration-transition-design.md`
(approved 2026-08-19, implemented 2026-08-20), which supersedes option A
above with a variant of option C that survives the objection recorded against
it: the market leg (`market_oas_bp`) now steps to the in-force band exactly
at the announcement date (`asserted_at`), staying a real, unblended index at
every date, and the transition is carried entirely by `idiosyncratic_bp`
(already `synthetic — engineered`) through a linear anticipation ramp. Three
response profiles — assigned by a seeded permutation over the crossing LEIs,
so signal strength and warning horizon are deliberately uncorrelated —
observed on this seed as:

| LEI | profile | α (anticipation) | lead (observation dates) |
|---|---|---|---|
| `5493003QENHHS261UR94` | faint | 0.30 | 110 |
| `5493004HBTOTE9DI9P12` | moderate | 0.60 | 40 |
| `549300EQD0ZXRSMG3549` | pronounced | 0.90 | 75 |

This assignment is an *outcome* of the seeded permutation, not a configured
input — a reseed would reassign it. Full mechanics, the `>= 1` crossing
existence guard that makes that seed-dependency survivable, and the one
deliberate discontinuity the ramp introduces: the design doc §§2–3.

**Measured before/after:**

| | Before | After |
|---|---|---|
| Market leg at a crossing | Pinned to the day-1 band; ~75–141bp gap unreflected and unlabelled | Steps to the in-force band at `asserted_at`; the gap is carried by an explicit, labelled ramp |
| Market dominance ratio (vs. 0.40 ceiling) | 0.1893 as recomputed by `validators/series.py` from the loaded store before this fix (the generator's own prior artifact recorded 0.189 — the two sources differ slightly, same as after) | 0.1861 as computed by the generator; 0.1847 as recomputed by `validators/series.py` from the loaded store — both recorded, since they differ slightly |
| `spread_observation` rows | 29,885 | 29,885 unchanged — **1,022 of 29,885 rows changed**, confined to exactly the 6 instruments belonging to the 3 migrating obligors; no row added or dropped |
| `conditions.py` | 82 passed / 0 failed | 82 passed / 0 failed, unchanged — no §F condition depends on this behaviour, then or now |
| `generate_grades.py` output, Fluree | — | untouched: byte-identical grade generation, all 245 assertions and the 215-edge supersession chain stand, no reload |

No longer carried as an open question for Wave 11b — `docs/HANDOFF.md` §8 now
points 11b at the design doc instead of at this entry.

### 9.11 🟠 Estate-wide — every EDGAR sweep reads the capped `filings.recent` index; `filings.files[]` shards are never read

`https://data.sec.gov/submissions/CIK##########.json` returns
`filings.recent`, which EDGAR **caps at roughly 1000 filings per issuer** and
shards the remainder into `filings.files[]`. No fetcher in this estate reads
the shards.

**Measured: 40 of the 50 anchors have unread shards.** For Avis Budget Group
(CIK 723612), `recent` reaches back only to 2016-03-29, with two unread shard
files behind it.

**All seven affected fetchers**, each now carrying an inline warning at the
call site (grep ``EDGAR `recent`-only``):

| File | Line | Sweep |
|---|---|---|
| `generators/fetch_rating_actions.py` | `sweep_issuance` | Item 2.03 debt-issuance 8-Ks |
| `generators/fetch_def14a.py` | | DEF 14A proxy statements |
| `generators/fetch_exhibit21.py` | | Exhibit 21 subsidiary lists |
| `generators/fetch_8k502.py` | | 8-K Item 5.02 officer/director changes |
| `generators/fetch_form4.py` | | Form 4 insider transactions |
| `generators/fetch_ex10.py` | | EX-10 credit agreements |
| `generators/verify_obligors.py` | | filing-profile eligibility |

**Downstream impact in Wave 11a is nil.** Task 4 uses only the two most recent
filings per obligor, and instrument eligibility comes from `filing_profile`,
not from the issuance sweep. But 788 `IssuanceEvent` nodes load with
`provenance: public`, and `ccf_dataprep_v2.md` and `HANDOFF.md` both read as
the complete public record. **788 is a floor.** Both docs now say so.

**Ruled 2026-08-19: soften the claim, do not page the shards.** The code fix is
perhaps 15 lines in a shared helper — the expense is not the code. Paging shards
would change published counts across six earlier waves, each with its own
committed claims and its own review surface, making every count in
`ccf_dataprep_v2.md` provisional until re-verified. That is an estate-wide
re-baselining and belongs in its own wave.

**Additionally ruled: warn at every call site.** This repo is used to teach, and
the `recent`-only pattern is exactly what a reader copies into their own
fetcher. Softening the docs protects this repo's accuracy; it does not stop the
pattern from propagating. Seven inline warnings do.

### 9.12 🔵 DETERMINED — ICE BofA index values are committed to this repo; use is educational and private

`sources/screening/wave11a_oas.json` (15,756 lines) carries **3,930 daily OAS
values verbatim** across five ICE BofA indices — `BAMLC0A2CAA`, `BAMLC0A3CA`,
`BAMLC0A4CBBB`, `BAMLH0A1HYBB`, `BAMLH0A2HYB` — retrieved through FRED, which
redistributes them under ICE Data Indices' terms. The same values populate
`market_oas_series` (3,930 rows) and are an additive component of all 29,885
`spread_observation` rows.

**The raw CSVs are NOT committed.** `.gitignore:20` excludes `sources/**` apart
from manifests and `sources/screening/*.json`, so
`sources/fred/BAML*.csv` exist on local disk only. The exposure is the derived
JSON and the loaded rows.

**Determined by the user 2026-08-19: not an issue, and not a blocker.** The
repository is held private and exists to teach others how to use the CCF SDK
against *their own* data. There is no public release and no redistribution
channel. Recorded here with the reasoning rather than the conclusion alone, so
that it can be re-evaluated if the hosting decision ever changes — **"private"
describes the hosting, not the distribution**, and a teaching repo handed to N
learners is N copies. The relevant fact is audience scope, not repository
visibility.

The README acknowledgement names the ICE BofA data explicitly and states it is
not for redistribution.

**Why this was surfaced rather than silently recorded:** the index values are
not confined to one artifact — they are folded additively into every composed
spread. Had the determination gone the other way, scrubbing would have meant
regenerating the series, not deleting a file. Cheap while Wave 11a is the tip;
expensive once Wave 11b builds on it.

---

## 10 · Wave 11b defects — `credit-surveillance-early-warning`

Merged 2026-08-21. Baseline at merge: `partition.py` **19/19** ·
`conditions.py` **91/0** · `surveillance.py` **PASS** ·
`verify_fibo_wave11b_confirm.py` **10 confirmed · 0 missing** ·
11 pure-function suites, **279 cases**, all passing.

### 10.1 🟠 GDELT's event and mention streams were substituted with the DOC API

§C of `credit-surveillance-early-warning` names GDELT's **event and mention
streams** — the raw CAMEO-coded 15-minute CSVs at
`data.gdeltproject.org/gdeltv2/`. Twenty-four months is roughly **52,000
files**. Not tractable, and the cost buys nothing the product needs.

**Substituted with** the GDELT DOC API
(`api.gdeltproject.org/api/v2/doc/doc`), article-level, queried by entity name,
carrying the same 15-minute `seendate` granularity, with GDELT's tone filter
applied so "adverse media" is genuinely adverse rather than any mention at all.
Recorded the same way §9.2 records the TRACE substitution: name the intractable
source, state what is reachable, label the provenance honestly.

**What it costs, stated rather than buried:**

- **GDELT's own entity tagging is not used.** Matching is by name query, which
  is lossy in both directions. That loss is not a defect to hide — it is the
  same lossy name resolution §C already demands for WARN, and it is now
  visible in the data rather than asserted in prose.
- **CAMEO event codes are gone.** A consumer cannot ask "which mentions are
  coded as a protest, a lawsuit, a plant closure". Tone is the only severity
  proxy, and tone is a document-level average.
- **Name collisions collect other people's bad news.** Measured on the first
  full sweep: `"Regis"` 0/25 genuine (Bognor Regis, Lyme Regis, an Australian
  gold miner), `"Sabre"` 0/25 (a wrestler; "sabre-rattling"), `"Griffon"` 0/155
  (a vulture, a radio host). **1,809 mentions — 66% of the artifact — none of
  it about the obligors.** All three return zero under every qualified
  corporate form measured, so the noise was replaced by a fetched zero and the
  findings ride along in `coverage[lei].precision_review`. This is why 20 of
  the 50 obligors legitimately have `active_days: 0`.
- **Three silent-empty failure modes were found during implementation**, all of
  the same family — the API returns something that looks like a clean empty
  answer when it is nothing of the kind. `mode=artlist` silently clamps a long
  date range to its trailing ~3 months while stopping short of `maxrecords`, so
  a truncation test never fires; the stated 5s rate limit is a floor, not a
  guarantee, and the penalty state is probabilistic rather than a timed lockout;
  and a phrase GDELT considers too short is refused with **HTTP 200** and a
  plain-text body. Each is defended against in `generators/fetch_gdelt.py` and
  each would otherwise have produced a confidently wrong dataset.

### 10.2 🔵 Item 4.02 has ZERO in-window instances — loaded as a type with no rows

§C names six 8-K item types. Five are populated. **Item 4.02 (non-reliance on
previously issued financial statements) has zero instances in the 24-month
window**, and this is a fact about the cast, not a fetch failure:

| Window | Item 4.02 events |
| --- | --- |
| 18 months | 0 |
| **24 months (chosen)** | **0** |
| all history | **26 events across 18 obligors** |

The history read was exhaustive — `filings.recent` **plus** all 41 shard files,
which is the §9.11 correction applied rather than merely recorded. The 26 exist;
every one predates the window.

**Decision D5: load the signal type with zero instances and record the absence.**
Manufacturing 4.02 filings would have put synthetic rows in a column §C classes
as `public`, which is the exact failure CLAUDE.md rule 1 exists to prevent. The
alternative — widening the window until a 4.02 appears — would have been chosen
to produce a number rather than a condition.

**The cost is real and is not hidden.** A consumer asking "show me non-reliance
signals" gets an empty, correct answer. The demonstration that a restatement
invalidates every downstream product that consumed the restated figures cannot
be run on this data. If a later wave needs it, the honest routes are to widen
the anchor cast to include an obligor with a recent 4.02, or to label a
manufactured one `synthetic — engineered` and put it beside the public column,
never inside it.

### 10.3 🟠 The third WARN state was never added — and California carries the whole floor

Design decision **D2** committed to **Texas + California + one further state**,
the third to be scoped during planning, because TX+CA alone was believed to land
on §F's ≥3-obligor floor with zero margin.

**The third state was not added.** Task 4's Step 5 gate (≥3 resolved obligors,
≥1 ambiguous pair) passed on TX+CA: 3 distinct obligors resolved, 32 ambiguous
pairs. The gate was the correct place to stop and it was not loosened to reach
that result. NJ, OH, FL and IL had already been probed and are JS portals
returning 403/404 on direct request; Texas is the only US state WARN dataset on
Socrata. The third state's cost was unscoped and it bought no §F condition.

**What the decision actually costs, which is not what D2 predicted:**

| | D2's belief | Measured |
| --- | --- | --- |
| Resolved obligors | 3 (Charter, Avis, Quanex) | 3 (Charter, Quanex, **Bausch Health**) |
| States carrying them | TX and CA | **CA only** |
| Loaded notices | — | **3,099 CA / 415 TX** |
| Single point of failure | "losing Charter" | **losing California** |

Texas contributes **415 of 3,514 notices and not one resolved obligor.** Every
true positive is Californian. The concentration is worse than D2 anticipated
and in a different place: the design worried about losing an *obligor*, and the
real exposure is losing a *source*. A CA EDD format change — the live XLSX is
current-FY only, with prior years as per-FY PDFs read through
`pdftotext -layout` — drops the wave below §F on its own.

**Not fixed.** Adding a third state now means scraping a JS portal, which is
unscoped work at the end of a wave, and the §F floor is met. Recorded here so
the next wave that touches WARN starts from the real exposure rather than D2's
estimate. See also §10.4, which is how D2 came to believe otherwise.

**Ruling — user, 2026-08-21: deferred, not ratified.** Presented with the
measured exposure above (zero margin, and all three resolved obligors arriving
through the CA PDF leg specifically), the user chose to **accept two states for
Wave 11b and schedule the third as a task in the next wave that touches WARN.**

So this is an open commitment, not a closed deviation. The distinction matters:
D2 was not overruled, its execution was postponed. The next WARN-touching wave
**starts with adding a third state as a planned task**, not as a judgement call
to be re-made under end-of-wave time pressure — which is the pressure that
produced this shortfall in the first place.

Entry conditions for that task: network access (no state's WARN data is
reachable offline), and a scoped cost for a JS portal — WA, VA and NY are the
remaining candidates, all JS; CO and MI return 403. Success is a resolved
obligor from a **non-CA-PDF** leg, not merely a third state loaded: the exposure
being closed is source concentration, and a third state that resolves nobody
closes nothing.

> **CORRECTED 2026-08-21, same day, by actually probing the sources.** The
> paragraph above says "WA, VA and NY … all JS". **Virginia and New York are
> not JS portals.** That was inherited from the Wave 11b design's write-off,
> which was made by inspecting the pages, not by fetching them.
>
> | State | Reality when fetched | In-window notices | Obligors resolved |
> | --- | --- | --- | --- |
> | **VA** | server-rendered table **plus a CSV download** (`/warn_notices_*.csv`), 1,122 rows | **121** | **0** |
> | **NY** | server-rendered table; `?page=N` is ignored (every page identical); public listing stops at **March 2025** | 68 | **0** |
> | WA, WI | genuinely JS — zero `<tr>` in the served HTML | — | — |
> | Socrata catalog | re-queried: **Texas is the only state WARN dataset on Socrata.** That claim holds | — | — |
>
> **The task's entry condition is unchanged but its expected outcome is not.**
> A third state is *reachable* — Virginia is a cleaner source than the CA PDF
> leg, structurally — and it does **not** satisfy the success test, because no
> anchor obligor has a genuine Virginia or New York layoff in window. The
> success test stands as written; what is now known is that VA and NY cannot
> meet it. A future attempt must either widen the anchor set or accept that the
> source-concentration exposure is not closable from public WARN data alone.
>
> **The probe's real yield was a defect, not a state.** Virginia produced one
> pair scoring 0.907 — RESOLVED — between *American Healthcare REIT* and
> *American Woodmark Corporation*, a cabinet manufacturer. See §11.1.

### 10.4 🔴 FIXED — `docs/wave11b-design.md` claimed Avis Budget has 6 real Texas WARN notices; in-window it has none

§1.3's true-positive table and §1.5's cascade-anchor justification both stated
that **Avis Budget Group has 6 real Texas WARN notices**. Both were wrong, and
wrong in the estate's own recurring shape: **the six were counted against the
full Texas source, not the 24-month window.**

Every Avis Budget WARN notice in Texas is from **2020** — COVID-era rental-fleet
closures. The most recent Texas notice mentioning the name at all is 2022-06-28.
The loaded window opens **2024-08-19**. Verified against the loaded
`warn_notice` table: `employer ILIKE '%avis%'` returns exactly two rows,
"Davis Street Community Center" and "Management & Training Corporation (Travis
County State Jail)" — substring collisions, not Avis Budget.

**It did not reach the data.** `generators/warn_match.py` ran against the
windowed artifact and never resolved an Avis pair; `validators/test_warn_match.py`
keeps the Avis pair only as a scorer fixture, explicitly commented out-of-window.
The engineered cascade touches no WARN row — `surveillance.py` check 1 walks the
signal's 8 `signalAbout` targets and finds exactly 1 facility, 2 collateral
pledges and 5 drawdowns.

**It did reach two decisions.** It made D2 (§10.3) misjudge where the WARN
concentration risk sits, and it made the D6 cascade anchor look better-evidenced
than it is. **D6 itself stands**: Avis was selected on the intersection §F
actually constrains — facility + collateral pledge + drawdown + a
`covenant_breach` row (one of only two in the estate) + real Item 2.04 filing
history. WARN was never part of that intersection. The bullet was supporting
colour that happened to be false.

**Corrected in place in `docs/wave11b-design.md`, with the previous wording
quoted** rather than silently rewritten — this wave's third such correction and
now the house convention.

**Why it happened.** §1.2 of the same document states the lesson it then broke:
*"this is the estate's recurring lesson in its own shape — hitting the count
while missing the condition is a failure."* An aggregate measured over the wrong
span hides the decision. The probe that produced the six ran before the window
was fixed and was never re-run afterwards.

### 10.5 🔴 FIXED — Wave 11b silently turned `load_fluree_wave11a.py --reconcile` into a data-loss hazard

`loaders/load_fluree_wave11a.py` declared four `OWNED_PREDICATES` — `isIssuedBy`,
`concernsParty`, `supersededBy`, `filedBy` — under a docstring stating the
loader **"owns four edge predicates outright"** and that `--reconcile`
**"retracts every edge on them before rebuilding."** The code matched: a blind,
predicate-wide `DELETE DATA` of every edge found on all four, ledger-wide.

**That was true on 2026-08-19 and false on 2026-08-21.** `load_fluree_wave11b.py`
now asserts **535** `ex:supersededBy` edges of its own — 486 on `sig-8k-*`
subjects, 49 on `prior-obs-*` — beside Wave 11a's 215 on `syn-g-*`. A real
(non-dry-run) `--reconcile` today would have:

1. read all **750** `supersededBy` edges,
2. retracted all 750,
3. rebuilt only its own **215** from `wave11a_grades.json`,
4. left Wave 11b's supersession chain **gone** — the chain the product exists to
   demonstrate.

Fluree is append-only, so the retraction is itself a commit. There is no undo;
the history would record both the assertion and the retraction, and current
state would simply not have the edges.

**Nobody ran it.** Found by reading the code during Task 13, not by damage.

**Fixed** by scoping retraction to **subject membership** in the exact set of
node URIs that loader mints (`my_node_uris()` — `syn-i-*` instruments, `syn-g-*`
grade assertions, `issuance-{accession}`, `rating-action-{accession}`), which is
the pattern `load_fluree_wave11b.py` had independently established and proved.
`main()` now reads its artifacts **before** reconciling, because the safe scope
is a function of the artifacts. Dry-run confirms the split:

```
supersededBy      215 asserted (ours)  (535 on other loaders' subjects, left alone)
```

**All four predicates are scoped this way, including the three still exclusive
to that loader.** The assumption that failed was *"no one else will ever write
this predicate"*, so it is no longer relied on anywhere in the file. The false
docstring is corrected in place, with the previous claim quoted.

**The generalisable lesson, which is why this is 🔴 and not 🟡.** "This loader
is the sole author of predicate P" is a claim about the whole estate made from
inside one file. It is **true when written and decays silently** — nothing
recomputes it, nothing fails when it stops being true, and the failure it
eventually causes is a deletion rather than an error. Exactly the shape §0 of
this document gives for a vault caveat. **Scope a reconcile by subject, never by
predicate**, even when you are genuinely the only writer today. The subject
scope costs one extra set-membership test and cannot decay.

**A second victim of the same root cause, also fixed.**
`validators/artifact_reproduces_store.py` compared
`wave11a_grades.json[assertions.supersedes]` against a **blind predicate scan**
of `ex:supersededBy` and so went from 40/42 to **38/42** the moment Wave 11b
loaded: it reported 535 edges "in store not in artifact", which is not a
divergence — it is a different wave's data. Scoped by subject to the assertion
ids the artifact itself carries; back to **40/42** (the two remaining failures
are §8.16's artifact duplicates, unrelated). The check is not weakened: an
artifact edge missing from the store still fails, and a store edge on a
`syn-g-*` subject the artifact does not name still fails, because that subject
is in `assertion_ids`.

That this validator broke *silently into a red state nobody had run yet* is the
same decay the reconcile hazard has, one step less dangerous — a false alarm
rather than a deletion. Both come from the same sentence: **"this predicate is
mine."**

**What the fix costs, so the trade is on the record whole.** Subject scoping is
not a pure win. The blind scan retracted every edge on the four predicates
regardless of subject, so a stale edge whose id had dropped out of the artifact
was still swept up. A subject-scoped retraction cannot see it — `node_uris` is
built from the ids the CURRENT artifact names. Two of the four id families are
SEED-derived (`mint_assertion_id()` and `mint_instrument_id()` are both
`sha256(f"{SEED}|…")`, `SEED = 20260817`), so a regeneration under a different
seed would leave the old `syn-g-*` / `syn-i-*` edges unretracted beside the new
ones. The other two families are keyed on EDGAR accession numbers and are not
exposed. **This widened the existing node-lifecycle gap to cover edges, which it
did not cover before.**

Accepted, and not close. The new gap is hypothetical — it needs a seed change,
which nothing in the pipeline does — and **loud** when it fires: orphaned edges
show up in `partition.py`'s dangling check and in
`artifact_reproduces_store.py`'s content comparison. The hazard it replaced was
live, silent and irreversible. A narrow, documented idempotency gap beats
cross-wave data loss. Recorded because the next reader should see the whole
trade rather than only the half that improves; the loader's own docstring
carries the same note, including what to do if a seed ever does change (retract
by subject against the OLD artifact first, then regenerate).

**Estate sweep.** `load_fluree_wave10.py` was checked and carries the identical
pattern — a blind predicate-wide retraction over **six** `OWNED_PREDICATES`
(`isEmployedBy`, `isOfficerOf`, `isDirectorOf`, `coversClient`,
`participatedIn`, `relatedToDeal`) under the same "sole author" claim. All six
are genuinely exclusive to it **today**, which is exactly what Wave 11a's
docstring said, so the exposure is dormant rather than absent. It was **not**
changed in this wave: no current loader writes any of the six, the fix is the
same subject-scoping refactor, and doing it at the last task of a different
wave would be an untested change to a loader nothing in this wave touches.
Recorded here as the next place this bites — and the first three
(`isEmployedBy` / `isOfficerOf` / `isDirectorOf`) are the ones to watch, since
they are generic FIBO employment properties any future wave might reasonably
assert. `load_collateral_wave9.py` and `load_temporal_wave5.py` have no
`--reconcile` at all.

### 10.6 🔵 The score distribution was measured, not assumed — and it varies

Design §7.1 recorded the risk that decision **D3** (load everything, ~1,600
events rather than sub-selecting to §F's ~400) would flatten the composite
warning score into a cluster, satisfying the count while destroying the
condition it exists to make demonstrable.

**Measured by `validators/surveillance.py` check 3, recomputed from the loaded
stores rather than from a generator flag:**

| Statistic | Value |
| --- | --- |
| Obligors scored | 50 |
| min / Q1 / median / Q3 / max | 0.2539 / 1.2053 / 2.2626 / 3.1073 / 10.9400 |
| Quartile counts (rank-based) | 12 / 13 / 13 / 12 |
| Coefficient of quartile deviation | **0.4410** (floor 0.15) |

**The risk did not materialise.** The middle half of obligors spans 44% of the
(Q3+Q1) scale, well clear of the floor. The shape is right-skewed — a few
obligors carry far more real 8-K and adverse-media volume than most, and
`max/median` is 4.8× — but the *typical* obligor's score still differs
materially from the next typical obligor's, which is what "vary rather than
cluster" asks for. The count is not standing in for the condition here.

Recorded as 🔵 rather than dropped because the measurement is the point: D3 was
taken against the recommendation, with the trade-off stated, and the honest
close is to report which way it came out.

### 10.7 ✅ PAID 2026-08-21 (Wave 11c) — 45 `ex:` terms asserted data with no row in the binding contract; the guard that found them was itself blind three times over

> **CLOSED 2026-08-21 by Wave 11c.** All 45 terms now carry a real full-IRI row
> in `docs/ccf_dataprep_v2.md` § *Wave 11c: the binding debt paid*. The estate
> is **67 / 67**. `KNOWN_UNBOUND` is **empty** — deliberately kept in place
> rather than deleted, because emptying it changes the shape of the rule the
> gate enforces:
>
> ```
> non-empty:  fail if a term is NEW and unbound   <- needs a maintained list
> empty:      fail if a term is unbound           <- nothing left to rot
> ```
>
> Re-attacked after the change, since a green gate has meant nothing here three
> times running. Five injected terms — a novel name, a prefix of a bound term
> (`signal`), a prefix of two bound terms (`valid`), a suffix-extension of a
> bound term (`provenanceX`), and a bare word appearing in the document's prose
> (`schema`) — all exit `1`. The real, unmodified estate exits `0`.
>
> **Two of the 45 were not debt.** `ex:schemaNote` (9 assertions) and
> `ex:effectiveDateNote` (25) had no writer anywhere in the repo — ledger
> residue from a loader version since changed. Binding them as they stood would
> have published vocabulary a rebuild cannot produce, which is worse than
> leaving them unbound because it is invisible until someone rebuilds. Writers
> restored (user's decision, over deleting the triples); `ex:MeasurementPeriod`
> and `ex:ContextDebt` gained the T-Box declarations they had never had; ledger
> 38,582 → 38,588, idempotent on a second run. New guard:
> **`validators/orphan_terms.py`**, written before the fix and watched fail on
> exactly those two.
>
> **A gap this exposed, still open.** `validators/binding_drift.py` reports
> `CLAIM_MISSING` for a bound term the vault makes no claim about — which is
> precisely the state all 45 are in until the custodian applies the Wave 11c
> punch list. It reports none of them. Its `CLAIM_MISSING` rows are derived
> from `sources/screening/fibo_wave8_confirmed.json`, a Wave 8 artifact
> listing confirmed **FIBO** terms; no `ex:` term appears in it, so the
> verdict was 11 agree · 29 disagree both before and after binding 45 terms.
> The check that exists to notice unpublished terms cannot see the largest
> population of unpublished terms. Not fixed in this wave: extending it adds
> 45 failures to a validator already carrying 29, and the two populations want
> separate handling. Worth its own task.
>
> The rest of this section is the original record, kept because the three
> corrections below are the reason the guard is now trustworthy.

### 10.7a 🟠 The original record — 33 `ex:` terms assert data in Fluree with no row in the binding contract, and the guard that found them was itself blind

> **CORRECTED 2026-08-21 by the whole-branch review. This section previously
> claimed two things that were false.** It was headed *"31 `ex:` terms … all
> predate Wave 11b"* and stated in bold: *"**None is Wave 11b's**."* Both were
> wrong, and they were wrong for the same reason: the script that produced the
> number decided "is this term bound?" with a bare Python `in` against the raw
> text of a 1,700-line document, so any `ex:` term whose local name is an
> ordinary English word matched an unrelated prose sentence and never entered
> the count. Three terms hid there. One of them, **`ex:item`, was Wave 11b's
> own** — 535 live Fluree assertions across 409 `ex:SignalSource` nodes, with
> no binding-table row and no `published_claims.json` entry. It is now bound
> (`docs/ccf_dataprep_v2.md`, *"A sixth term — `ex:item`"*). The other two are
> Wave 5 covenant attributes, 180 assertions each, and are added to the list
> below: **31 → 33**.

> **CORRECTED AGAIN 2026-08-21, by the scoped re-review of the fix above.**
> The "tightened" test still had a hole, and it was a **gate bypass**, not
> just a reporting gap: the full-IRI check was `f"{EX}{local}" in text`, an
> unanchored substring test, so any local name that is a *prefix* of an
> already-bound term's IRI read as bound-by-IRI on zero evidence — `signal`
> inside `.../signalAbout`, `Warning` inside `.../WarningSignal`, `trigger`
> inside `.../triggeredBy`. Injecting `ex:signal` into the estate term set
> made `main()` exit `0` with *"no NEW unbound term"*. Fixed with a
> word-boundary-anchored `re.search`. Re-deriving the split moves one real
> term: `ex:trigger` (245 live assertions, Wave 11a's) was misclassified as
> bound-by-IRI and is now correctly bound-by-mention, where it already had
> genuine evidence (`ccf_dataprep_v2.md:713`). The table below said
> **23 / 11 / 33**; it is **22 / 12 / 33**. Total published debt (mention-only
> plus fully-unbound) is **45 rows, not 44**.

> **CORRECTED A THIRD TIME 2026-08-21, same day, second pass of the scoped
> re-review.** The anchor fix above closed the IRI half of the check but left
> the **gate itself** bypassable: `main()`'s pass/fail decision accepted
> either `iri` **or** `mention` as "bound enough," via `doc_binds()`. A
> `mention` is a backtick occurring anywhere in a 1,700-line document —
> coincidental hits included, since `signal` itself reads as `mention` off an
> unrelated sentence in this document's own absence-search prose, not a
> binding row. Concretely: injecting `ex:signal` into the estate term set
> still made `main()` exit `0`, because `signal` now correctly classified as
> `mention` rather than the old false `iri` — but `mention` still satisfied
> the gate either way. **The gate and the published debt arithmetic already
> disagreed**: 45 = 33 + 12 treats mention-only terms as debt, while the gate
> treated them as bound. Fixed by requiring `strength == "iri"` for the gate;
> `mention` is now treated the same as no evidence and must be frozen in
> `KNOWN_UNBOUND`, like the 33, or it fails as a NEW unbound term. All 12
> mention-only terms are pre-existing and already asserted in the estate, so
> they are added to the freeze: **`KNOWN_UNBOUND` grows 33 → 45.** Re-attacked
> per the same method: `ex:signal` now exits `1`; a second mention-only,
> non-frozen probe (`ex:source`, also backticked elsewhere in this document)
> exits `1`; a genuinely new term (`ex:zzzBogus`) exits `1`; the real,
> unmodified estate (45 pre-existing debt terms) still exits `0`; `item`
> still reads `iri`; `grade` still reads `mention` and still appears in the
> debt list. No fourth hole was found.

Found by `generators/verify_fibo_wave11b_confirm.py`, built in this wave to
restore the machine-checkable auditability Wave 8's
`verify_fibo_wave8_confirm.py` established — and then re-found, larger, when
that script's own membership test was tightened.

The estate asserts **67** distinct `ex:` terms. Under the tightened test they
split three ways:

| Evidence in `docs/ccf_dataprep_v2.md` | Count | Status |
| --- | --- | --- |
| a **full IRI** (`http://example.org/fibo/…`) — a real binding row | 22 | bound; the vault mirror can consume these |
| a **code-span mention** only (`` `grade` `` / `` `ex:grade` ``) | 12 | named in the document, no binding row — see *"the residual hole"* below |
| **nothing at all** | 33 | this issue |

The 33 with no mention anywhere:

| Kind | Terms |
| --- | --- |
| classes (Waves 4, 5, 7) | `Amendment`, `ContextDebt`, `EmbargoWindow`, `PolicyVersion`, `RegFDEvent`, `WallCrossing` |
| attributes (Waves 4–7) | `amendmentNumber`, `amends`, `anchorVerified`, `basis`, `bookingDateProvenance`, `bookingLagDays`, `compliantToday`, `direction`, `documentId`, `edgeProvenance`, `effectiveDateNote`, `effectiveDateProvenance`, `endOffset`, `evidencedBy`, `isEngineeredBookingLag`, `isEngineeredRecordingLag`, `isFiboTerm`, `noteId`, `passageSha256`, `principalId`, `recordingLagDays`, `schemaNote`, `sourceOffset`, `startOffset`, `testFrequency`, `unit`, `widensAccess` |

`direction` and `unit` are the two newly-surfaced ones — Wave 5 covenant
attributes written by `loaders/load_temporal_wave5.py:208-210` (a covenant's
`min`/`max` sense and its threshold unit), 180 assertions each. Worth one note
when this debt is paid: `unit` is the only term in the list whose local name
collides with a real FIBO term — `fibo-fnd-plc-adr:Unit`, an address
component (apartment/suite designator), an entirely different concept.

> **CORRECTED 2026-08-21 by the scoped re-review.** This paragraph previously
> called `fibo-fnd-plc-adr:Unit` *"a capitalised **class**"* and used that to
> argue the collision with the estate's lowercase `ex:unit` was not a
> shadowing defect. That was wrong. Verified at source
> (`FND/Places/Addresses.rdf:720`, `edmcouncil/fibo` clone `119fa8c`):
> `fibo-fnd-plc-adr:Unit` is an **`owl:NamedIndividual`** typed
> `SecondaryUnitDesignator`, not a class, and its `rdfs:label` is
> **lowercase `"unit"`** — an exact string match, not a case difference. This
> project's own absence methodology (Task 1, restated throughout this
> section) searches `rdf:about` / `rdf:ID` / **`rdfs:label`**, all three, with
> no case-folding rule anywhere in it. Under that same rule, `unit` **does**
> collide: the label is identical. The estate's `ex:unit` (a lowercase
> covenant-threshold *property*) and FIBO's individual (a lowercase
> *secondary-unit-designator label*) name different concepts under the same
> string, which is exactly what "shadowing" means here. This does not change
> §10.7's disposition — `unit` is still cross-wave debt to bind, not a defect
> to fix in this wave — but the binding row, when written, should record the
> collision honestly rather than the reasoning that dismissed it.

**All 33 predate Wave 11b** — that part of the original claim survives, now that
`ex:item` has been separated out and bound. None is a shadowed FIBO type: the
six classes are allowlisted with written rationale in `validators/partition.py`'s
`PERMITTED_EX_TYPES`, and the 27 attributes are the same kind of thing as the
`ex:` predicate table already in the document. What is missing is the
**binding-table row**, which CLAUDE.md's definition of done item 5 requires and
which the vault mirror consumes.

**Why it matters more than it looks.** The binding table is a contract shared
with a downstream project that has no access to this repository and reaches it
only through the vault mirror. A term that carries data here and has no row
there is invisible to that consumer — the precise failure CLAUDE.md names as
"silent and expensive". `binding_drift.py` cannot see them either: it compares
published claims against the estate, and there is no claim to compare.

**The residual hole, now closed at the gate (though not at the report).** The
tightened test accepts a **backticked token or a full IRI** as *evidence that
the document knows about a term* — that is a large improvement, it rejects 8
of the 11 ordinary English words the old test passed — but it still cannot
tell a *binding-table row* from a *deliberate code-span mention* when
**describing** a term. What changed on the third pass is that this ambiguity
no longer matters for **pass/fail**: only a full IRI satisfies `main()`'s
gate, so a `mention` is now gated exactly like no evidence at all — it must
be frozen in `KNOWN_UNBOUND` or it fails as new. Twelve terms sit in the
mention-only gap and the script prints them every run, both as a named debt
category and as gated entries in the freeze:

`assertedAt`, `covenantType`, `evidence`, `grade`, `observedValue`,
`provenance`, `reason`, `sourceAccession`, `threshold`, `trigger`, `validFrom`,
`validTo`

> **CORRECTED 2026-08-21.** This list previously held eleven terms and did not
> include `trigger`. `ex:trigger` (Wave 11a's, `loaders/load_fluree_wave11a.py:399`,
> 245 assertions) was misclassified by the unanchored-IRI-substring bug above —
> its local name is a prefix of `.../triggeredBy`'s IRI, so it read as
> bound-by-IRI on zero evidence. It has genuine mention evidence of its own
> (`ccf_dataprep_v2.md:713`, in the same Wave 11a paragraph that names `grade`),
> so under the anchored test it correctly lands here rather than among the 33
> with nothing at all: **eleven → twelve**.

These are **not** an oversight of the same kind. The Wave 11a paragraph in the
`ex:` extension register names eight of them precisely in order to record a
decision that they get no row, citing Wave 5's `covenantType` / `threshold` /
`observedValue` precedent for the other side of the same rule. So the document
knows about them; the *contract* still does not carry them, and a mirror consumer
still cannot see them. Wave 11b narrowed that precedent for `ex:item` (an
attribute earns a row when a downstream query pivots on its value) without
re-adjudicating the other twelve, which belong to earlier waves.

A worked consequence, now narrower than before: this section still could not
name `direction` and `unit` in code spans **inside `docs/ccf_dataprep_v2.md`**
without the check reading them as `mention` rather than `None` — but, since the
third-pass fix, that reclassification no longer changes the gate's verdict:
both strengths are gated identically and both are already frozen in
`KNOWN_UNBOUND`. The residual risk that remains is narrower and reporting-only
— a term could move between the "mention" and "pre-existing unbound" debt rows
without a human noticing which — not a gate bypass. They are still named here,
in `known-issues.md`, which the check does not read, as a workable convention
for keeping the two debt rows legible rather than a pass/fail concern.

**Not fixed in this wave, deliberately.** It is cross-wave documentation debt
spanning Waves 4–7 with a punch-list consequence, and this wave's punch list is
scoped to its own six terms. Fixing it means 33 binding rows (45 if the twelve
mention-only terms are adjudicated at the same time, which they should be — was
stated as 44 before `ex:trigger` moved from the false-`iri` bucket into this
one), the matching `published_claims.json` entries and a much larger mirror
refresh — a task, not a footnote.

**Pinned so it cannot grow.** `KNOWN_UNBOUND` in
`generators/verify_fibo_wave11b_confirm.py` freezes the list and reports its
members as `DEBT` rather than `FAIL`; a **new** unbound term, from any wave, is
not in that set and fails. A Wave 11b gate held permanently red by a Wave 4
omission is a gate people learn to ignore.

> **CORRECTED 2026-08-21, third pass.** This paragraph said the frozen list
> holds **33**. It now holds **45** — the 33 fully-unbound terms plus the 12
> mention-only terms, added once `mention` stopped satisfying the gate (see
> the correction block above). Every added entry was verified as already
> asserted in the estate before being added; the freeze only protects against
> silent growth if nothing is added to it that isn't real, pre-existing debt.

**How the freeze was re-proved, and why the old proof did not count.** Task 13's
review demonstrated the freeze by injecting a *synthetic, distinctive* term and
watching it surface as `new_unbound`. That proof passes straight through the
defect this section corrects — a distinctive token is exactly the case a
substring test handles correctly. The re-proof therefore used the failing shape
instead: with the `ex:item` binding row removed from a scratch copy of the
document, the old substring test still reports it **bound** while the tightened
test reports `FAIL` on two rows and the script exits `1`. Eight further ordinary
English words (`unit`, `direction`, `value`, `note`, `scale`, `period`, `state`,
and `item` itself) flip from "bound" to "unbound" under the new rule.


### 10.8 🟡 The cascade trigger exists in Fluree with no `signal_event` row — by design, and it is the one asymmetry worth re-examining

`sig-8k-engineered-529900E95812SYWMCE44-2.04` is typed `ex:WarningSignal` in
Fluree and has **no row in Postgres `signal_event`**. Design §2.1 places the
cascade trigger event in **Fluree alone**, while the row above it in the same
table places the composite case in "Postgres + Fluree" — and those three rows
really are loaded in both. The asymmetry is a recorded decision, not a load that
fell short.

**The argument for it:** the cascade exists to demonstrate supersession
propagating through the graph (Assembly Recipe step 7), not to be scored, so it
carries no severity in the store that owns severities.

**The argument against, recorded so it is not lost:** every other
`ex:WarningSignal` in the ledger resolves to a measurement. A consumer that
walks `ex:WarningSignal` and joins `signal_event` on `signal_id` gets 537 of 538
and one silent miss. If the product's step 6 (composite score) is ever run over
the graph rather than over Postgres, the cascade trigger scores zero — the one
signal in the estate that should score highest.

`validators/partition.py` asserts this explicitly rather than tolerating it: the
exception is narrowed to **one** id, so a second unexplained Fluree-only signal
fails rather than hiding behind the first one's rationale.

### 10.9 🔵 Deferred minors carried forward from the Wave 11b execution ledger

Recorded during execution; none blocked a task. Triaged at Task 13 — every one
is disposed of here, none silently dropped.

| # | Task | Finding | Disposition |
| --- | --- | --- | --- |
| 1 | T1 | `fibo-fnd-dt-oc` used in compact form in the Wave 11b binding section but never added to the prefix registration table | **FIXED.** Registered, with a note that it is registered for a **rejected** term and that registering a prefix is not binding a term |
| 2 | T1 | No machine-checkable verification artifact committed; prior waves ship e.g. `verify_fibo_wave8_confirm.py` | **FIXED, and it earned its keep immediately** — `generators/verify_fibo_wave11b_confirm.py`, 10 confirmed · 0 missing, and it found §10.7 on its first run |
| 3 | T2 | TDD "see it fail" step skipped once, disclosed honestly at the time | **Recorded, no action.** The test in question passes and pins real behaviour; re-deriving its red state now would prove nothing about how it was written. Kept visible rather than dropped, because the disclosure is the thing worth preserving |
| 4 | T3 | TX `source_ref` is a module constant, so all 415 TX notices share one ref, while CA rows carry a per-row / per-line ref — asymmetric traceability | **Recorded, not fixed.** The Socrata response is a single JSON document with no per-row identifier, so a per-row ref would have to be synthesised (row index), which is traceable to *our fetch* rather than to *the source* — weaker evidence wearing a stronger shape. Fixing properly needs a re-fetch, and this machine is under a no-external-network constraint. The asymmetry is real and now stated |
| 5 | T4 | `generators/warn_match.py` docstring said "registered name" where the code compares `normalise()` output | **FIXED**, both occurrences (module docstring and the `LEADING_BRAND_WEIGHT` note), with the previous wording named |
| 6 | T5 | `fetch_timeline` comment said "17 of the 50 obligors"; post-fix it is 20 | **FIXED.** The count rose when Task 5's fix round removed the 1,809 name-collision mentions, moving Regis, Sabre and Griffon from noisy coverage to a fetched, corroborated zero. The comment now says so |
| 7 | T8 | `CASCADE_LEI` never lands in `__dict__`, so it is absent from `dir()` and from a star-import | **Accepted, no action.** It is a module-level `__getattr__` resolving lazily against Postgres — deliberate, so importing the module does not require a live database. No star-import consumer exists in the estate. `test_signals.py` pins both halves: that it is callable immediately after import, and that it *raises* rather than returning something silently wrong when the DB is down |
| 8 | T9 | `gdelt_mention.down_weight_reason` says "24/49 on-topic"; `signal_event.source_ref.down_weight_reason` says "25/49 off-topic" — same numbers, opposite framing | **Recorded, not fixed.** Both strings are correct and 24 + 25 = 49; the confusion is cosmetic. Aligning them means editing a string that is already **stored in Postgres**, so the fix is a code change plus a reload, and a reload at the last task of a wave to correct a comment is a poor trade. The arithmetic is stated here so no reader has to work it out |
| 9 | T9 | `gdelt_mention.seendate` kept as raw `TEXT` rather than a timestamp | **Accepted, documented.** GDELT's `seendate` is fixed-width `YYYYMMDDTHHMMSSZ`, so lexicographic order **is** chronological order and range predicates work unchanged. Storing it verbatim keeps the row byte-identical to the artifact it came from, which is the property `validators/artifact_reproduces_store.py` checks for Wave 11a's tables and which a Wave 11b extension of it would need. One `CAST` is needed downstream for date arithmetic; that is the whole cost |
| 10 | T10 | `load_postgres_wave11b.py` lacked the provenance guard its Fluree sibling has | **FIXED.** The two stores hold the same three composite signals under the same `signal_id`s; a guard on one side only means a mislabelled artifact is refused by Fluree and silently accepted by Postgres, leaving the halves disagreeing about a provenance class CLAUDE.md rule 1 says must be honest |

### 10.10 🟠 A multi-item 8-K collapses two SignalSource properties into an unjoinable pair

**Found by the whole-branch review, 2026-08-21.**
`loaders/load_fluree_wave11b.py`'s module docstring concluded: *"each accession
yields exactly one SignalSource/WarningSignal pair."* That claim is **false**,
and unlike the wave's other four false claims it is false in the *data shape*,
not only in the prose.

| | Claimed | Live |
| --- | --- | --- |
| SignalSource nodes | 535 | **409** (408 real + 1 engineered) |
| distinct accessions behind 534 real events | 534 | **408** |
| `ex:item` triples | one per node | **535 over 409 subjects** — 287×1, 118×2, 4×3 |

A SignalSource node is keyed by accession alone (`ex:{EX}8k-{accession}`), and a
single 8-K routinely reports more than one item. So **122 nodes carry two or
three `rdfs:label` values *and* two or three `ex:item` values, in parallel, with
nothing linking one to the other.** A SPARQL pattern that pairs them returns the
cross product:

```sparql
?s rdfs:label ?l . ?s ex:item ?i .
```

On `8k-0001104659-24-126817` that returns **four** rows, two of them nonsense —
`"Item 2.03 filing 0001104659-24-126817 (2024-12-09)"` paired with item
`"1.01"`, and its mirror image.

**Not re-modelled, and the reasoning is recorded rather than assumed.** One
filing genuinely reporting two items is *correct*: the node **is** the filed
document, and the document really does carry both codes. Re-keying it to
`(accession, item)` would mint 534 SignalSource nodes for 408 real documents and
assert that one filing is two filings — a worse model, bought late in a wave, in
exchange for a query nothing in the estate runs. Fluree is append-only, so the
change would also be a permanent recorded retraction of 409 nodes.

**The safe path, for anyone querying this.** Go through the WarningSignal node:
there is exactly one per `(accession, item)`, its `rdfs:label` and its
`triggeredBy` edge are single-valued, and Postgres `signal_event.source_ref`
carries the item code per signal. The docstring now states all of this and
quotes the claim it replaces.

### 10.11 🟡 The §5 artifact-currency guard was promised, shipped missing, and is now built — with a limit worth naming

**Design §5 committed to it in these words:** *"the dependency is enforced with
an explicit guard that raises naming the required order — and, unlike Wave 11a's
guard, checks that the artifact is **current** rather than merely present …
that residual hazard is not repeated here."* Wave 11b shipped with **every
artifact read as a bare `json.loads`**. No ruling waived it; it was simply never
built. The whole-branch review found it.

**The concrete failure it left open.** Someone re-runs `generate_signals.py`
against a `wave11b_gdelt.json` from before Task 5's fix round. It silently
produces the 2,760-mention ledger containing the 1,809 rows about Bognor Regis,
a wrestler and a vulture (§10.1), and both loaders load it without a word.

**Built 2026-08-21: `ccf/currency.py`.** A generator records the sha256 of every
artifact it consumed under `_inputs`; each consumer re-hashes those files and
raises `StaleArtifact` naming the required order if the bytes have moved.
`generate_signals.py` records four inputs, `narrative_wave11b.py` records one,
and `narrative_wave11b.py` plus both Wave 11b loaders verify before reading.
Proven by mutation: a one-byte edit to `wave11b_gdelt.json` takes all three
consumers from exit 0 to exit 1, and restoring the bytes returns them to 0.
The loaders print a per-artifact currency verdict on every run, so the guard's
**coverage** is visible rather than inferred — the three fetch outputs
legitimately carry no `_inputs`, because they read the network rather than
another artifact, and the run says so instead of quietly passing them.

**🟡, not closed, because of what a content hash cannot do.** It establishes
*"these are the bytes I was built from"*. It cannot establish *"these were the
right bytes"*. In the scenario above, if the operator restores the pre-fix
GDELT artifact **and** re-runs `generate_signals.py`, the new ledger records the
old file's hash, the hashes agree, and this guard passes. The ordering hazard
§5 actually named is closed; the wrong-input hazard is not, and no hash can
close it. What defends against *that* is
`validators/surveillance.py` check 6 (§10.12): the pre-fix GDELT head was three
obligors whose mentions were ~100% off-topic, and that head fails the
"concentration survives dropping down-weighted mentions" sub-check.

### 10.12 🔵 Two validator gaps the whole-branch review found, both now closed

Recorded because both were **silent** — the estate reported 19/19 · 91/0 · PASS
with each defect live — and because the fix for each is a check that has been
proven to discriminate by mutation rather than asserted to work.

**(a) §F's GDELT concentration clause was gated by nothing.** §F asks for ~200
mentions *"weighted toward a handful of names"*. `conditions.py` checked the
count (951 ≥ 200) and **nothing checked the concentration**. That is not a
theoretical gap: §10.1 records that the first sweep's 77.8% top-5 concentration
was *entirely a noise artifact*, so the clause could have been satisfied by
exactly the data the wave spent a fix round removing.

`validators/surveillance.py` check 6 now recomputes it from `gdelt_mention` as
loaded, in three directions — there is a head (top-5 ≥ 40%; live **66.46%**,
against 16.67% for a uniform spread over the 30 obligors that carry mentions);
the head is a handful of names rather than one (largest single obligor < 50%;
live **21.03%**); and the head survives dropping every down-weighted mention
(live **70.07%** of 902). The third is the one the pre-fix sweep would have
failed. Boundary-tested: a synthetic distribution at top-5 = 39.90% FAILS and
one at 40.12% PASSES, so 40% is a real edge and not a token gate; a flat
30-obligor distribution FAILS; a single obligor holding 60% FAILS on the
single-name clause alone.

**(b) No artifact-reproduces-store check covered any Wave 11b table.** Halve
`trend_delta` (3,705 rows) or `warn_notice` (3,514) and the estate still
reported 19/19 · 91/0 · PASS. `validators/artifact_reproduces_store.py` now
covers all seven Wave 11b Postgres tables (14 new checks, 42 → 56 total), by
calling the loader's own `build_rows` — the same decision `check_rating_scale`
makes for `grade_to_notch`, because the claim under test is *"loading this exact
file would reproduce these tables"* and a second independent transform would
test a different claim. Proven discriminating: halving `trend_delta` fails
exactly its two checks; halving `warn_notice` fails exactly its two; wiping
`decay_days` on one signal type, editing one `signal_event.severity`, and
dropping the 49 Celanese down-weight flags each fail exactly one content check
and nothing else. Every mutation was run inside a rolled-back transaction.

**What (b) still cannot catch**, stated because the boundary matters: a bug
inside `build_rows` itself. The check proves the store matches what the loader
would produce from the committed artifact, not that the loader's transform is
right.

---

## 11 · Wave 11c defects — consolidation (binding debt, orphan terms, name matcher)

### 11.1 🔴 FIXED — the WARN name matcher resolved two unrelated companies on a shared generic first word

`generators/warn_match.py` scores an anchor obligor's legal name against a WARN
notice's employer string. One of its two token-level signals is **leading-brand
match**: if both normalised names begin with the same token of six or more
letters, and the employer's normalised form is no longer than the anchor's, the
pair scores `0.8 + 0.2 × ratio` — comfortably above the `0.85` resolve
threshold almost regardless of what follows.

That is correct for `quanex` and `bausch`. It is wrong for `american`.

| Anchor | Employer | Score | Verdict before fix |
| --- | --- | --- | --- |
| American Healthcare REIT, Inc. | American Woodmark Corporation | **0.907** | **resolved** |
| American Healthcare REIT, Inc. | American Airlines Group | **0.898** | **resolved** |
| National Fuel Gas Company | National Vision Holdings | **0.930** | **resolved** |
| Standard Motor Products | Standard Register | **0.910** | **resolved** |

American Woodmark makes kitchen cabinets. American Healthcare REIT owns medical
office buildings. The only thing the two names share is the word *American*.

**`MIN_BRAND_LEN` could not have caught this, and reading the code would not
have suggested it.** That guard was raised from 4 to 6 precisely to stop
short-word collisions (`City Office REIT` / `City of Hope`, `Super Micro
Computer` / `Super 7`), on the reasonable theory that longer leading tokens are
more distinctive. `american` is eight letters. **Length is not
distinctiveness** — the comment now says so at the constant, because that is
where the next person will look before raising it to 9.

**It was live through the whole of Wave 11b and never fired.** Not
wrong-but-tolerated — *wrong-and-unfired*. No in-window Texas or California
notice happened to lead with a word one of the 50 anchors also leads with. The
input that exposed it came from probing Virginia, a source this project had
written off without fetching (§10.3).

**Fix.** The leading-brand signal is withheld when the shared token is in
`GENERIC_LEADING` (ordinary English adjectives and geographies); the pair falls
through to the plain-ratio branch, which is capped below the resolve threshold.
All four pairs above now land *rejected*, at 0.54–0.65.

**Why withholding cannot lose a true positive**, which is the property that
makes the list safe to be incomplete: a genuine parent/subsidiary pair
(`Pioneer Natural Resources` / `Pioneer Natural Resources USA`) satisfies
**full token containment**, signal 1, which is evaluated *first* and is
untouched by this change. Only a pair whose sole evidence is the shared generic
word is demoted. So `GENERIC_LEADING` is a floor, not a ceiling — the next
generic prefix is not on it, and its absence costs precision, never recall.

**Verified.** Six generic-prefix pairs added to `validators/test_warn_match.py`
and watched fail before the fix; 44/44 after. All **36 loaded `warn_match` rows
re-scored under the fix: zero change** in score or verdict, so the estate needs
no reload and no §F verdict moves.

### 11.2 🟠 FIXED — two `ex:` terms carried data in Fluree that no code in the repo could produce

Found while writing binding rows for the 45 unbound terms (§10.7).
`ex:schemaNote` (9 assertions) and `ex:effectiveDateNote` (25) were asserted by
a loader version that no longer exists.

**The cause is structural and will recur.** Fluree is append-only and the
loaders upsert rather than replace. When a loader stops writing a predicate —
the line deleted, renamed, or rewritten — the triples it already wrote do not
disappear. They stop being refreshed and remain in the ledger, indistinguishable
from live data to every query and to every audit that counts rows. The estate
slowly accumulates content whose source no longer exists.

**Nothing was watching for it.** `validators/artifact_reproduces_store.py`
exists to catch exactly this class of drift and cannot see it: that validator
compares generated artifacts against Postgres **tables**. A Fluree predicate
with no writer is outside its reach entirely.

**Why binding them would have been worse than leaving them unbound.** A binding
row publishes a term to a downstream consumer that reaches this project only
through the vault mirror. Publishing a term no code produces tells that
consumer to expect vocabulary that vanishes the next time the ledger is rebuilt
from empty — and the failure is invisible until someone rebuilds.

**Fixed by restoring the writers**, on the user's decision, over deleting the
triples: both notes carry information worth keeping (`schemaNote` is the graph
explaining its own invented vocabulary to a consumer holding only the graph).
`ex:MeasurementPeriod` and `ex:ContextDebt` gained the T-Box declarations they
had never had. The literal is defined once in `ccf/config.py` because three
loaders assert it — a reworded copy would appear in the ledger as a competing
second value for the same predicate.

**New guard: `validators/orphan_terms.py`** — every `ex:` term the estate
asserts must have a writer in this repo. Written **before** the fix and watched
fail on exactly these two. Detection is source-level and excludes the frozen
`KNOWN_UNBOUND` list and its own file: counting a *list of terms* as a writer
would make the check vacuous, which is the mistake the Wave 11b binding
verifier made three times by matching against raw document text.

**Verified.** Restored literals are byte-identical to the ledger's existing
values (one distinct value per predicate, before and after). Ledger 38,582 →
38,588; `schemaNote` stays at 9 and `effectiveDateNote` at 25, so the restored
writers upserted rather than duplicated. Second run: 38,588 — idempotent.

## 12 · Wave 12 defects — `treasury-liquidity-position`, `fx-post-trade-reconciliation`

Design: `docs/wave12-design.md`. Plan: `docs/wave12-plan.md`
(`progress.md` carries every ruling by number, F1–F25; the seven below are
the ones with a lasting, generalisable lesson — the rest were caught and
fixed the same session with no residue). Every defect here was **found and
fixed inside this branch**, before merge; nothing below is outstanding.

### 12.1 🔴 FIXED (RULING F12) — a units error made the wave's headline gate pass on every input

`generators/ticks.py`'s `max_rolling_move_bp` was changed from `* 100` to
`* 10000` mid-implementation, to satisfy a failing test. Verified: under the
`* 10000` version, a real 8bp move (2-year par yield 4.10 → 4.18, percent
units) reported **800bp**. `validators/intraday.py`'s "≥1 day carries a ≥8bp
90-minute move" claim — the wave's single most load-bearing check, the one
proving the product's central mechanism exists at all — would have passed
against **every** input, correct or not, because a genuine 8bp move and a
genuine 0.08bp move both clear a threshold measured in units 100x too coarse.

**The multiplier was right; the test fixture was wrong**, and both were wrong
in the *same direction*, which is why the failure was silent rather than
loud. The fixture ramped values at `0.0001` per tick — 0.01bp per tick in
percent-yield units — then asserted that 18 ticks summed to 18bp. They sum to
0.18bp. Treating the assertion as ground truth and dragging the multiplier to
match it is how a synthetic fixture with an invented magnitude can validate a
100x-wrong implementation: nothing about the fixture's own scale was ever
checked against the domain.

**The generalisable lesson.** A test built from an arbitrary synthetic ramp
carries no external anchor — its magnitude is whatever the test's author
typed, and a mis-scaled implementation can be made to satisfy it by
mis-scaling the test to match. A test anchored to a **real, independently
known magnitude** cannot be satisfied this way: 4.10 → 4.18 on the actual
loaded par-yield curve **is** 8bp by definition, not by construction, so no
multiplier error can make both the domain fact and a wrong implementation
agree. Fix: reverted the multiplier to `100`, corrected the ramp fixtures to
their intended `0.01`/tick, and added two new tests pinned to real curve
magnitudes (4.10→4.18 = 8bp, 4.00→4.01 = 1bp) specifically so the units
cannot drift again without a domain fact catching it, not merely another
synthetic ramp.

### 12.2 🔴 FIXED (RULING F15) — the staleness gate compared against `now()`, so the claim could never fail

`stale_signal` originally baked absolute wall-clock timestamps, and the
validator measured age as `now() - observed_at`. Minutes after generation,
every signal in the table is older than the 15-minute bound — the
fresh/stale contrast the check exists to demonstrate disappears entirely,
and the claim **cannot fail regardless of what is loaded**, the same disease
as §12.1's units error: a gate that is structurally incapable of reporting
red is not a gate.

**Fixed by measuring against a recorded `as_of`** rather than the wall
clock: `stale_signal` rows carry their own `as_of` decision-time reference,
and age is `as_of - observed_at`, both loaded values. This also matches the
spec's real semantics more faithfully than the original design did —
`max_staleness` is evaluated against decision time, and under bitemporal
replay `as_of` is a request parameter the caller supplies, not the clock the
validator happens to run at. Added the counterpart claim that ≥1 signal must
be **inside** the bound: a population that is uniformly stale demonstrates a
broken feed, not a working staleness gate, and the contrast is the point.

### 12.3 🟡 FIXED — three FIBO terms were needed that design §1.1 said would not be

§1.1 measured "no new FIBO binding is required by this wave" by checking
every class name the two specs' own §C prose mentions against
`docs/ccf_dataprep_v2.md` — and every one of those was indeed already bound.
That measurement answered the wrong question. Typing 200 investment
positions by instrument (CLAUDE.md rule 7 — no OWL inference, so every
queried role needs an explicit type) required `CommercialPaper`
(`fibo-sec-dbt-tstd`), `TreasuryBill` (`fibo-sec-dbt-bnd`), and `MutualFund`
(`fibo-sec-fund-fund`) — none named in either spec's prose, all three real,
all three verified against the EDM Council source and bound in
`docs/ccf_dataprep_v2.md`. A fourth term, `ex:RegulatoryPosture`, is a
genuine non-FIBO extension (checked against `RegulatoryClassification`,
`RegulatoryRegime`, `JurisdictionalRestriction`, `ComplianceRequirement` too
— zero hits on all five).

**The generalisable lesson.** A binding audit run against a spec's prose
text is not a binding audit — it can only confirm that the words the spec
happened to use are bound, and a spec's prose does not enumerate every
concrete type a compliant loader must assert. Only the loader's actual
typing decisions can answer that question, which means the honest time to
run the audit is **after** the loader exists, not before design closes.
§8's definition-of-done item 5 already said this claim must be verified at
close rather than assumed; this is that verification firing one task
earlier than the design expected, against the design's own §1.1. Sent to
the vault 2026-08-22 (`2026-08-22T00-50-00Z-wave12-treasury-bindings`) —
see `docs/ccf_dataprep_v2.md`'s Wave 12 changelog entry.

### 12.4 🔴 FIXED (RULING F21) — the FX intraday path reused a 6.5-hour equity session, so all timing breaks landed in the same six hours

`generators/generate_fx_trades.py`'s tick path initially reused
`generators/ticks.py`'s Treasury session (13:30–19:55 UTC, 78 ticks) — correct
for a par-yield instrument, wrong for FX, which trades continuously. Measured
consequence before the fix: only 228 of 500 trades (46%) executed inside that
window, so per-second drift was defined for under half the trade population,
and **every one of the 40 engineered timing breaks had to be drawn from that
half**. Result: all 40 timing breaks landed in hours 14–19 UTC while the 20
genuine breaks spread across hours 00–17 — **a consumer could separate the
two classes by hour of day alone, performing no clock alignment whatsoever**,
which is the exact discrimination `align_clocks` exists to demonstrate. Every
§F count would have been satisfied while the product's whole argument was
falsifiable by inspection.

**Fixed with a genuine 24-hour tick calendar** — 288 five-minute ticks per
pair per day (10,368 total, vs 2,808 under the 6.5-hour session) — dedicated
to FX and left `ticks.py`'s Treasury session untouched, since it remains
correct for that instrument. Re-measured after the fix: timing breaks span 17
distinct hours (was 6), genuine breaks span 13, **twelve hours carry both
classes**, and 44 of 60 breaks (73%) sit in hours that cannot be separated by
time of day alone. Structural separability by a shortcut the product does not
intend is gone.

### 12.5 🔴 FIXED (RULING F24) — `system_trade_record` gave all three systems the same value, so the engineered break never reached either store

Found by the Task 15 implementer while building `validators/reconcile.py`,
**missed by two prior task reviews** (Tasks 12 and 14). `system_trade_record`
loaded the identical `true_rate` for trading, settlement, and risk on every
trade, break or not — the engineered per-system disagreement lived only
inside the generator artifact's `breaks` list, and per RULING F22 (§12.6)
only `raw_variance` and `designed_class` cross into Postgres, nothing at all
into Fluree. A validator reading Postgres values plus Fluree timestamps —
exactly what `reconcile.py` is required to do — would have recomputed a raw
difference of **exactly zero** for all 60 breaks. Neither the inversion claim
nor the survivor claim could ever have been *established* by recomputation;
they could only have been asserted from the answer-key column, which is the
one thing the gate exists to avoid consulting.

**Why two reviews missed it.** Both checked counts, schema shape, provenance
labelling, and idempotency — every property a review normally verifies — and
neither asked the one domain question that mattered: *do the systems actually
disagree with each other?* A table can be perfectly well-formed, fully
populated, and correctly provenanced while still being unable to demonstrate
the one thing the product is built to demonstrate.

**Fixed** via `apply_break_overrides()`, which writes each break's per-system
engineered values into `system_trade_record` rather than leaving them
artifact-only. Verified after the fix: all 60 break trades carry ≥2 distinct
per-system values; the 440 non-break trades correctly still agree across all
three systems.

### 12.6 🟠 FIXED (RULING F22 / F23) — the observation timestamp was duplicated into Postgres, and its Fluree name collided with an earlier wave's Postgres-owned attribute

Two related defects, found and fixed together. First (F22, self-imposed):
the design's initial `system_trade_record` schema carried an `observed_at`
column, duplicating a value the spec's §C assigns to Fluree alone ("system
observation timestamps and clock offsets" → Fluree; "internal trade records
per system" → Postgres). Fixed by dropping the column — `system_trade_record`
now carries exactly the value each system recorded, nothing about when.

Second (F23): the Fluree side asserted the timestamp under `ex:observedAt` —
already claimed, since Wave 11b, as a **Postgres**-owned surveillance-signal
attribute in `validators/partition.py`'s `POSTGRES_OWNED_ATTRS`. Asserting it
in Fluree made the partition validator report a genuine cross-wave predicate
**collision** as if it were a single-writer **leak** — the two look
identical to that check (a name it doesn't own, appearing in Fluree) but are
different failures with different fixes. A reviewer's first proposed fix —
strip the predicate from Fluree entirely — would have been wrong in the
opposite direction: it deletes the attribute from the store the spec
explicitly assigns it to, for a problem that was actually about the *name*,
not the *location*. Fixed by renaming to `ex:systemObservedAt`, the same
precedent this wave's own Task 9 had already set (`ex:jurisdiction` /
`ex:intent` → `ex:postureJurisdiction` / `ex:postureIntent`) for the
identical reason: **a predicate name is estate-wide, not scoped to whichever
loader happens to be writing it this wave.**

### 12.7 🟡 FIXED (RULING F25) — a mutation test aimed at the clock offsets failed to falsify the inversion, because offsets are a minority of what alignment corrects

The first mutation-test attempt at `validators/reconcile.py`'s inversion
claim zeroed every recorded `ex:clockOffsetSeconds` value and expected the
inversion to disappear. It did not: 32 of 40 timing flips survived. Measured
cause: the clock-offset spread (159s across the three systems) is a median
**11.9%** of the true observation-time gap (458.7s) that `align_clocks`
actually corrects — offsets are a real but secondary input, and the
observation-time gap between systems (trading books at execution, settlement
after affirmation, risk on its own snapshot cadence — genuinely different
*moments*, not clock error) dominates the correction.

**Ruled: the data is right and must not change.** Inflating the offsets to
make the mutation fail would be the same error as tuning a threshold until a
breach appears — it manufactures the mutation's success rather than testing
the claim. The test was wrong, not the data: retargeted at the decisive
input — collapsing the true observation instants (`obs_x − offset_x`)
themselves to a single point, leaving offsets untouched — which correctly
drives the inversion claim to 0/40. A second mutation (neutralising all 20
survivor breaks) also initially under-tested: one corrupted witness cannot
falsify a claim quantified over ~20, so the fix corrupts the full witness
set, not a sample of it.

**The generalisable lesson.** A mutation must match its scope and its target
to the claim it is meant to falsify — a mutation aimed at a term that is only
a minor contributor to a computation, or aimed at one witness of a claim
quantified over many, reports green for the wrong reason: not because the
gate is sound, but because the mutation never touched what the gate actually
depends on. The fix also added a dedicated "offset input is live" claim,
proving the recorded offset changes the aligned result on ≥1 break by
comparing two in-memory computations — so the offset term is exercised by
the gate even though it is not what the inversion mutation should target.

### Validator baseline after Wave 12

`partition.py` **25/25** · `conditions.py` **111/0** · `intraday.py` **9/9**
· `reconcile.py` **10/10** · `series.py` PASS (Wave 11a unmoved) ·
`surveillance.py` PASS (Wave 11b unmoved) · `traversal.py`, `bitemporal.py`,
`projection.py` PASS · `orphan_terms.py` **86/86** · `binding_drift.py`
**11 agree / 32 disagree** (+3 from §12.3's new FIBO terms, unpublished at
the vault — not a regression) · `artifact_reproduces_store.py` **52/56**,
pre-existing (Wave 10 duplicate rows §8.16, Wave 11a rating-actions gap;
confirmed none of the four failures touches a Wave 12 table) · 15
pure-function suites, all green.

### Deferred minors, Wave 12 — none block merge, none affect a loaded §F condition

| Item | Decision | Why |
| --- | --- | --- |
| `test_ndf_pairs_are_rejected` would also pass against a module rejecting every input | **Record and defer** | It is sound only *alongside* the positive tests in the same file (`validators/test_part43.py`), which do exercise acceptance — as a suite the file is not vacuous, and splitting one test's soundness from its neighbours is not how this file is read or run. Isolating it would cost a real test for a theoretical risk nothing in this wave depends on |
| All 60 loaded breaks carry `intent="break-investigation"`; the `control-review` and `regulatory-report` threshold rows load but are never exercised by a break | **Record and defer** | Reachable, not orphaned (RULING F13/F22 note) — `materiality_threshold` is correctly populated for all three intents and a future break population can use either row without a schema change. No §F condition names intent diversity among breaks |
| `P_OBSERVED_AT_LEGACY` (`ex:observedAt`, §12.6) **and** the unconditional `ALTER TABLE ... DROP COLUMN IF EXISTS observed_at` in `loaders/load_postgres_wave12_fx.py:131` are both inert migration scaffolding with no expiry | **Record and defer, not delete** | Same class, same disposition, recorded together (Wave 12 final review, Minor 8) so they don't drift apart. `P_OBSERVED_AT_LEGACY` exists so a real `--reconcile` retracts the 1,815 stale triples fix round 0 asserted under the old Fluree predicate name before rebuilding under `ex:systemObservedAt`. The `ALTER TABLE ... DROP COLUMN` is the Postgres-side twin — it exists so a table this loader already created in fix round 0, when `observed_at` was still a column, gets that column removed on every run (`CREATE TABLE IF NOT EXISTS` is a no-op against an existing table, so the drop has to be explicit); it is also the one thing today enforcing RULING F23 against `system_trade_record` (`validators/partition.py`'s table-scoped check, added this pass, is the actual regression guard — see IMPORTANT-3 above — but the ALTER is still what makes a stale table clean on load). Deleting either now would be safe against *today's* stores (confirmed 0 legacy triples remain in Fluree; the column starts absent in a fresh Postgres load) but removes the one thing that would clean up a **second** deployment of either loader that has not yet run the migration — both migrations are proven done here, not everywhere either loader might be deployed. Left for whoever confirms the last such deployment has migrated |
| A `designed_raw_variance` field is fetched by `reconcile.py`'s `fetch_postgres()` and never used | **Fix now** | Trivial and free to fix, unlike the other three: `break_rows` builds a `"designed_raw_variance"` key from `break_record.raw_variance` that no claim in the file reads (only `designed_class` is consulted, deliberately, inside `disagreement_report()`). Removed the dead field from the dict construction; `raw_variance` is **no longer selected in the query either** (`fetch_postgres()`'s `break_record` SELECT now names only `break_id, trade_id, system_a, system_b, designed_class`) — corrected here, as this entry previously (and incorrectly) said `raw_variance` was still selected for the tuple unpacking. Verified: `uv run validators/reconcile.py` still reports 10/10 PASS, disagreement 0/60, unchanged |

### 12.8 ✅ PAID 2026-08-22 — `context_debt` was 1 row where the Wave 11a artifact expects 169

`artifact_reproduces_store.py` reports **52/56**, not the 54/56 recorded in
`HANDOFF.md`. Four failures, of which two are the long-known §8.16 Wave 10
artifact duplicates. The other two are new to the *reading*, not to Wave 12:

```
[FAIL] context_debt  wave11a_rating_actions.json[unconfirmed]
       -> row count artifact=169 store=0
[FAIL] context_debt  ... content 169 in artifact not in store
```

**Established during Wave 12's close:**

- The check was added by **Wave 11a** (`5e3a2dc`), which **predates this
  branch's base** (`38b5e21`) — verified with `git merge-base --is-ancestor`.
- **No Wave 12 commit touches `context_debt`** or any of its three writers
  (`load_anchors_wave6.py`, `load_postgres_wave10.py`,
  `fetch_rating_actions.py`) — verified by path-scoped `git log` over
  `38b5e21..HEAD`.
- The table currently holds **1 row**; the artifact carries 169 `[unconfirmed]`
  rating-action candidates recorded as context debt.

**Now established (Wave 12 final review) — the mechanism, not merely the
symptom.** `loaders/load_anchors_wave6.py:208` runs an unconditional
`TRUNCATE "ccf_v2".context_debt` immediately before inserting its own rows,
with no guard against a prior wave's rows already sitting in that table. Any
re-run of this Wave 6 loader — for any reason, on any later wave's checkout —
destroys whatever Wave 10 and Wave 11a wrote there and replaces it with only
Wave 6's own debt population. Confirmed against the live table: it holds
**exactly 1 row**, `covenant_type='leverage'`, `recorded_at` = **today**
(2026-08-21) — a Wave 6-shaped row stamped with a load date from this branch's
work, not a stale Wave 11a row, which is inconsistent with "nothing in Wave 12
touched this table" only in the sense that nothing *edited* the loader; running
it (directly or via a shared setup step) is enough. This is a **latent
cross-wave destructive loader on `main`**, not a Wave-12-introduced defect, and
explains why *when* the divergence opened cannot be pinned to a commit range —
it opens on whichever run last executed this TRUNCATE, regardless of branch.

**Not established, and deliberately not guessed:** which specific run (which
wave's re-verification, whose local reload) last executed the TRUNCATE.
`HANDOFF.md` last recorded 54/56 at Wave 11c's close; the mechanism above
explains *how* a divergence like this opens, but pinning the exact triggering
run would need reload logs this wave does not have.

**Why it is recorded rather than fixed here.** Re-running `fetch_rating_actions.py`
or a Wave 10 loader would very likely make the numbers agree — and that is
precisely what this validator's own failure message forbids: *"do not paper over
this by re-running the loader without first finding WHY they disagree."* An
unexplained agreement is worth less than an explained disagreement. It belongs to
whoever opens the next wave, with this note as the starting point.

**Fixing `load_anchors_wave6.py`'s unconditional `TRUNCATE` is explicitly out of
scope for Wave 12.** It is a `main`-branch defect this wave's final review
identified but did not introduce and must not repair here — repairing it belongs
to whoever opens the next wave.

> **CLOSED 2026-08-22, opening Wave 13.** Two commits, deliberately separate.
>
> **The mechanism.** `loaders/load_anchors_wave6.py`'s `TRUNCATE` is now a
> `DELETE ... WHERE subject_kind IS NULL`, exported as `DEBT_OWNED_BY_WAVE6`.
> That predicate is the **exact complement** of Wave 10's partial unique index
> `ux_context_debt_subject ... WHERE subject_kind IS NOT NULL`, so the three
> writers' territories are now disjoint **by schema rather than by
> convention** — no new ownership rule was invented for this fix.
> Delete-then-insert was kept over an upsert on purpose: Wave 6 recomputes the
> complete covenant-debt population every run, so a covenant that stops being
> debt must disappear, which an upsert would never do.
> `validators/test_context_debt_scope.py` proves it and **carries a
> falsification arm** — it runs the original `TRUNCATE` through the identical
> assertions and requires them to fail — because §12's lesson is that a green
> check proves nothing until you have seen it go red. Mutation-tested three
> ways: predicate `true` (6/9), predicate `false` (7/9), `TRUNCATE` restored
> in the loader (7/9), each failing the assertions it should.
>
> **The data.** `loaders/restore_context_debt.py` replays both destroyed
> populations from tracked artifacts — no EDGAR re-fetch. §12.8's own bar
> ("do not paper over this by re-running the loader without first finding WHY
> they disagree") is met: the WHY was established before the replay, and the
> replay is what the finding implies. `artifact_reproduces_store.py` is back
> to **54/56**, the reading `HANDOFF.md` last recorded at Wave 11c's close;
> the two remaining failures are the §8.16 Wave 10 artifact duplicates and are
> untouched by this.
>
> **The circularity, stated rather than discovered later.**
> `artifact_reproduces_store.py` deliberately reads the artifact's *own*
> `reason` string (§9.1). Replaying that string into the store therefore makes
> that check pass **by construction** for these rows. That is inherent to any
> replay. What claws the information back is the restore script's default
> refusal to replay an artifact whose `reason` text no longer matches the
> generator constants — so the artifact is checked against live code before it
> is allowed to define the store. This is the **opposite** coupling choice
> from the validator's, and deliberately so: a validator that hard-couples
> reports false divergence, whereas a replay that does not hard-couple
> silently reinstates a stale sentence. Mutation-tested: a hand-edited reason
> makes it exit 1.
>
> **Not established, and still not guessed:** which specific run last executed
> the `TRUNCATE`. That would need reload logs nobody has. It no longer
> matters operationally — the statement that did it cannot run again — but the
> question is closed as unanswerable, not as answered.
>
> **A second defect fell out of the repair — see §12.9.**

### 12.9 🔴 FIXED 2026-08-22 — `ccf_dataprep_v2.md` recorded `context_debt` at 136 with a note describing a number the tracked artifacts have never produced

Restoring §12.8's destroyed rows meant recomputing Wave 10's person-debt
population from its artifacts. It comes to **133**, not the **136** recorded
in `docs/ccf_dataprep_v2.md`'s Wave 10 Postgres table, whose note reads
*"roster members with no DEF 14A / 8-K rendering found."*

**133 is forced, not chosen.** `wave10_persons.json` holds 704 natural
members; `wave10_name_variants.json` holds 571 distinct rendered
`person_key`s, every one of them in the roster and every one natural;
704 − 571 = 133. There are **no duplicate `person_key`s** among the natural
roster, and `wave10_name_variants.json` has exactly **one revision in git
history** (`928bfa6`), so the artifact has never implied any other number. No
alternative predicate over the tracked artifacts yields 136 — the only other
counts available are 172 (all persons minus rendered) and 39 (entity members).

**What 136 most likely was.** The table it sits in is headed `Table | Rows`
and its other cells are whole-table counts — `person_name_variant` reads 571,
the *stored* count, not the artifact's 572. So 136 is very probably the whole
`context_debt` table at Wave 10's close: 133 person rows plus 3 covenant-shaped
rows left by Waves 6/9. The **note** is then the actual error, describing the
whole table as though all of it were roster members.

**That 3-row residue is NOT established** and is not asserted in the
correction. Confirming it would mean replaying Wave 6 at its Wave 10-era
commit against the then-MongoDB corpus, which no longer exists in that state;
the repo records no covenant-debt count anywhere for the period. The
correction therefore states the reproducible number and names the likely
explanation as likely.

**The shape to recognise.** This is `claims-outlive-the-data-that-refutes-them`
again: the *data* was right, the *account* of it was wrong, and the account
survived because nothing recomputed the number from the artifacts. It was
caught only because the restore had to derive the figure independently — had
the restore trusted the doc and written 136 rows, the doc and the store would
have agreed and both would have been wrong.


---

## 13 · Wave 13a defects — `credit-memo-context`

### 13.1 🟠 OPEN on `main` — re-running the Wave 9 collateral chain renumbers and overwrites every existing asset

**Not triggered. Found while extending coverage, and routed around rather than
fixed, because fixing it is a data migration and this wave had no mandate for
one.**

`generators/generate_collateral.py` mints asset ids **positionally**:

```python
aid = f"COL-{len(assets) + 1:05d}"
```

over a facility list that `generators/extract_collateral.py` reads from
Postgres with `ORDER BY facility_id`. Facility ids are content-derived
(`accession` + facility type), so a facility added later does **not** sort last
— it sorts wherever its accession puts it. Wave 13a added twelve facilities and
**the first lands at index 2 of 57**.

So a re-run of the chain assigns `COL-00003` to a different asset than the one
that currently holds it, and every id after it shifts likewise. Then
`loaders/load_collateral_wave9.py` writes them with:

```sql
ON CONFLICT (asset_id) DO UPDATE SET valuation=..., valuation_date=...,
                                     haircut=..., provenance_existence=...
```

**Every one of the 81 existing `collateral_asset` rows is overwritten in place
with a different asset**, while `collateral_pledge` rows — keyed on
`(facility_id, asset_id)` — keep pointing at ids whose meaning has changed
underneath them. A facility ends up pledged to collateral it never pledged.
Nothing errors. Counts stay plausible. `partition.py` still passes, because the
rows exist and the edges resolve; they are simply wrong.

**Why it has not bitten before.** The chain has only ever been run against a
facility set that did not change between runs, so the positional assignment was
stable by accident rather than by design. It is a latent defect that arms itself
the moment `facility` gains or loses a row — which is exactly what a coverage
extension does, and what any future wave touching exposure will do again.

**Routed around, not repaired.** `generators/extend_collateral_wave13a.py`
mints ids strictly above the current maximum and writes only the new
facilities' assets, so nothing existing is read or rewritten. That closes
Wave 13a's need without a migration.

**The real fix, for whoever takes it.** Derive the asset id from content, the
way `facility_id` already is — `(facility_id, category)` is unique and stable
under insertion. That change is small; the migration behind it is not, because
the existing 91 assets and 95 pledges carry positional ids that would all have
to be rewritten together, in one transaction, with the Fluree
`ex:collateralAsset` nodes and `collateralizedBy` edges rewritten to match. Do
not attempt it piecemeal.

**The generalisable lesson.** This is the same shape as §12.8, which is why it
was recognised quickly: **a loader that is idempotent for a fixed input is not
idempotent.** `load_collateral_wave9.py` re-runs cleanly all day on unchanged
facilities and is genuinely safe there. Its danger is entirely in the coupling
between a positional identifier and an input set that can grow. Before trusting
any loader's idempotency, ask what happens when its *input* changes, not
whether re-running it on the same input is clean.

### 13.2 🟠 OPEN on `main` — the same positional-assignment defect, in a second loader: memoranda repoint to different facilities

**Found while extending the memoranda for §F3, by asking §13.1's question of a
different loader. It is not a one-off; it is a pattern.**

`loaders/load_mongo_wave6.py` assigns each generated memorandum to a facility
positionally:

```python
facilities = <SELECT ... FROM facility ORDER BY facility_id>
for i in range(MEMO_COUNT):
    fid, ftype, name, lei = facilities[i % len(facilities)]
    ...
    "memorandum_id": f"MEMO-{i:04d}",
```

`facility_id` is content-derived, so a facility added later sorts *into* the
ordering rather than onto the end. Wave 13a added twelve. Measured against the
live stores:

> **20 of the 22 existing memoranda would be assigned to a different facility
> on a re-run.** `MEMO-0002` currently cites `FAC-08F1D1` and would be rewritten
> to cite `FAC-08D5BB`.

The write is `UpdateOne({"_id": memorandum_id}, {"$set": ...}, upsert=True)`, so
each would be overwritten in place: same `memorandum_id`, same body text, a
different `facility_id` and `borrower_lei`. A credit opinion would silently come
to be about a different borrower. Nothing errors, the count stays 22, and
`partition.py` still passes because the rows exist and the keys resolve.

**Routed around, not repaired.** Wave 13a's additional memoranda are generated
by a separate additive module with **content-derived ids** keyed on the facility
they concern, so they cannot collide with `MEMO-NNNN` and cannot move.

**Why this one is worse than §13.1.** A renumbered collateral asset is wrong
data. A repointed credit memorandum is wrong data that reads as a considered
human judgement about a named borrower — precisely the kind of artefact a
reader trusts most and can least easily check.

**The lesson, now confirmed across two independent loaders.** §13.1 stated it as
*a loader that is idempotent for a fixed input is not idempotent*. Two instances
make it a class, and the estate should assume more exist. The signature to grep
for is an index into a sorted query result — `[i % len(...)]`, `enumerate` over a
`SELECT ... ORDER BY`, or any id minted from a running counter — anywhere the
underlying table can gain a row. **Identity must be derived from content, never
from position**, exactly as `facility_id` already is.

### 13.3 🔴 OPEN on `main` — estate-wide: four loaders derive identity from POSITION in a query result, and Wave 13a armed all of them

**§13.1 and §13.2 are not two bugs. They are two symptoms.** After the second,
the estate was swept for the signature — an index into a sorted query result
whose underlying table can gain a row. Four instances are confirmed against the
live stores, all latent until Wave 13a's coverage extension added twelve
facilities and seven borrowers.

| Module | Positional expression | Confirmed impact of a re-run |
|---|---|---|
| `generators/generate_collateral.py` | `COL-{len(assets)+1:05d}` over facilities `ORDER BY facility_id` | **all 81** collateral assets renumbered and overwritten in place; pledges point at the wrong asset (§13.1) |
| `loaders/load_mongo_wave6.py` | `facilities[i % len(facilities)]` | **20 of 22** credit memoranda reassigned to a different borrower (§13.2) |
| `generators/generate_exposure.py` | `borrowers[i % len(borrowers)]`, `borrowers` derived from `facility` | **13 of 15** cross-default edges repoint to a different source entity |
| `loaders/load_sqlite_wave7.py` | `enumerate(entities)`, `entities[:12]` over a live query | restricted-list and prospect rows shift entity — not yet quantified |

**Benign, and deliberately listed so the next sweep does not re-flag them.**
`X[i % len(X)]` over a *module constant* — `MEMO_TEMPLATES`, `ROLES`,
`INTENTS`, `CURRENCIES`, `NOTES` — is safe: the list cannot grow with the
database. The signature that matters is indexing into a **query result**.

**One measurement discipline this investigation nearly failed on.** The first
attempt to quantify the cross-default impact compared stored `from_uri` values
(entity URI slugs like `BgcGroupInc`) against LEIs, and reported *0 of 15
unchanged* — a confident, wrong number that overstated the damage. Normalising
both sides to the same identifier first gives **13 of 15**. CLAUDE.md's rule —
*normalize to full IRIs before comparing across stores* — exists for exactly
this, and it applies to a diagnosis just as much as to a validator.

**Why this is 🔴 rather than 🟠.** Individually each is a latent re-run hazard.
Together they mean **the estate has no safe "reload everything" path**, which
is precisely the property `docs/backlog.md` B2 wants and which B1's dump-and-
restore phase was scoped to avoid depending on. That scoping decision now looks
load-bearing rather than merely convenient.

**The fix is one change applied four times: derive identity from content, not
position** — as `facility_id` already does from `accession` + facility type.
Each carries a migration, because existing rows hold positional ids that must be
rewritten together with the Fluree nodes and edges referencing them. **Do not
attempt them piecemeal, and do not attempt any of them inside a product wave.**
This wants its own wave, with a validator that re-runs every loader twice and
asserts the stores are identical — the check that would have caught all four on
the day each was written.

---

## 14 · Wave 13b defects — `kyc-refresh-beneficial-ownership`

### 14.1 · A 200 with an empty body was recorded as a successful fetch — FIXED

OFAC publishes `CONS.XML` at a path that answers **HTTP 200 with zero bytes**.
`ccf.fetch.fetch()` wrote the empty file, computed its sha256
(`e3b0c442…` — the hash of nothing), and recorded a provenance entry in the
manifest for a payload that would fail to parse three functions later.

Every signal short of reading the bytes said the fetch had worked. `fetch()`
now refuses a zero-byte payload outright: it deletes the file, records nothing,
and raises. Verified against the live endpoint that produces the failure.

**The generalisable lesson.** Status code, file written and digest computed are
three checks that all pass on an empty body. When a guard's inputs are all
*about the transfer*, it cannot see a fact about the *content*. The real list
of what could be wrong includes "the server said yes and sent nothing."

The correct consolidated list is `CONSOLIDATED.XML`, same legacy `sdnList`
schema as `SDN.XML`.

### 14.2 · A Fluree aggregate read straight after a write returned zero — GUARDED

`loaders/load_offshore_wave13b.py` verifies its own load by counting from the
ledger. On its first run, three aggregates over the **same freshly written
predicate**, issued back to back, returned:

    COUNT(DISTINCT ?s)   40      correct
    COUNT(*)              0      wrong
    COUNT(DISTINCT ?s) on the type   40   correct

The 0 was the index, not the data — the edges were all present, and a re-run
reported 150 with nothing changed in between. A verification query issued
immediately after `INSERT DATA` can be served before indexing completes.

This is dangerous in both directions. Here it produced a false FAILURE, which
is cheap. The same race can produce a false PASS: a loader that re-asserts an
unchanged value and counts it while the index still holds the old, matching
number learns nothing and says everything is fine.

`ccf.fluree.stable_scalar()` now reads an aggregate repeatedly until
**consecutive reads agree**, then returns. The retry condition is deliberately
*stability*, not *correctness*: retrying until the number matches the caller's
expectation would be a check that cannot fail — this estate's most-repeated
defect (§12). `stable_scalar` does not know what the caller expects.

**Where else this applies.** Every loader that verifies a Fluree write by
counting is exposed. Waves 3, 5, 9, 10, 11a, 11b and 12 all do. None is known
to have been bitten, and none has been re-checked; that sweep is not part of
this wave.

### 14.3 · Three Wave 10 comparisons claimed ownership of tables Wave 10 shares — FIXED

`validators/artifact_reproduces_store.py` asserted full set equality between
Wave 10's artifacts and the **entire** `person`, `person_name_variant` and
`person_crosswalk` tables. That is not the claim the validator exists to make.
"This artifact reproduces what it loaded" became "no other wave may ever write
here", and Wave 13b's 210 pseudonymized PSC persons would have been reported as
a Wave 10 regression.

Same shape as the `context_debt` TRUNCATE (§12.8): a wave treating a shared
table as its own. Now scoped to `person_key_source = 'sec_cik'`. The scoping
was verified to be a **no-op at the moment it was made** (only `sec_cik` rows
existed, 54/56 unchanged) and verified **load-bearing afterwards** (unscoped it
would compare 953 store rows against a 743-row artifact).

### 14.4 · The name bank had to be falsified three times before it was right

The PSC name-leak gate — every emitted token must come from the closed bank —
caught three real defects in its own generator while being built:

    O'Hollingsworth   flush-bound particles produce ONE token, so the bare
                      token is absent from a vocabulary built by splitting
    StFairbairn       `St` stands off the surname; it was in the no-space set
    leksandr          stripping the particle rendering `O` unconditionally
                      mangled the bank's own `Oleksandr`

The third is the instructive one. The fix for the first (strip a known particle
prefix before comparing) introduced the third, because `O` is itself one of the
renderings of the `O'` particle. The correct order is: try the token **as-is
first**, and only fall back to stripping. A gate that rewrites its input before
checking it is testing something other than its input.

### 14.5 · A faithful draw could not satisfy §F5 — DOCUMENTED, engineered

Two findings that change how the person layer must be *labelled*, not how it is
built:

**Companies House publishes PSC names already romanized.** The
transliteration ambiguity §F5 asks for — one native form admitting several
Latin renderings — is therefore **not observable in the source at all**. It is
reconstructed from the nationality distribution using an invented name bank,
which makes those cases `synthetic — engineered`. Recording them as `public`
would misrepresent what the data proves.

**A faithful resample yields zero transliteration-capable persons.** British
nationals are 147k of 184k in snapshot part 1; 210 persons drawn faithfully
produced **0**. §F5 could not be met by a faithful draw at any sample size this
product would use. `MIN_PER_SCRIPT` forces a 42-person cohort that can, every
such person carries `stratified: true`, and the artifact records both the
stratified and the unstratified script mix.

### 14.6 · ICIJ names are deliberately not loaded — RECORDED DEVIATION

§C reads as though Offshore Leaks records are loaded into Fluree. They are not.
Asserting a relationship between a real named offshore entity and a synthetic
demonstration graph fabricates a claim about a real company, and ICIJ's own
terms state that inclusion implies no wrongdoing. The structure is taken —
fan-out, jurisdiction pairings, officer-role vocabulary, and the published
resolution-edge vocabulary with its real weights — and the names are not.

ICIJ's real fan-out is also too skewed to reproduce at this scale:
proportional allocation over a 150-vehicle budget gave one intermediary 116
vehicles and left 21 of 40 with none. Compressed by `log1p`, preserving the
ordering and the dominant agent but not the magnitudes; recorded in the
artifact as `fanout_compression`.

**Punch list for the vault.** Three §C statements need correcting where they
describe sources rather than the data model:

1. **OpenCorporates** is presented as a free bulk source. Its API now returns
   **401**. GLEIF Level 2 substitutes (user-approved), and joins better — it is
   keyed on LEI, already this estate's correlation key.
2. **ICIJ Offshore Leaks** is presented as records to load. This project loads
   the structure and not the names, for the reason above.
3. **Person-level beneficial ownership** is filed under Fluree. Attributes go
   to Postgres here and the graph to Fluree, matching what Wave 10 already did
   with its 743 persons and 704 Fluree Person nodes, and matching CLAUDE.md's
   single-writer rule. §C's `E, R` marking is consistent with that split; the
   single named store is not.

### 14.7 · The cycle check counted cycle MEMBERS, not cycles — FIXED

`validators/conditions.py` checked §F4's cross-shareholding condition with

    SELECT ?a WHERE { ?a owns ?b . ?b owns ?c . ?c owns ?a }

and counted DISTINCT `?a` against a floor of 3. A single 3-cycle produces three
bindings — one per starting node — so the estate's **one** engineered cycle had
been reporting **3 / 3 PASS** for every wave since it was built.

The condition asks for **≥ 2 cycles**. The check could not have failed at any
point: with two cycles loaded it now returns **6** distinct members, still
sailing past a floor of 3, and it would keep passing if a cycle were deleted.

Fixed by canonicalising each result triple as a `frozenset` and counting
distinct sets, which collapses the three rotations of one cycle to one. The
floor is now 2, matching §F4's wording, and the check reports 2.

**The generalisable lesson.** *Count the unit the condition names.* The
condition said "cycles" and the query counted nodes; both are integers, both
grow when the data grows, and only one of them answers the question. A check
whose unit differs from its condition's unit is not approximately right — it is
measuring a different quantity that happens to correlate.

Related: the existing cycle also could not have satisfied "spanning
jurisdictions", because its three nodes carried **no jurisdiction at all** —
no Fluree predicate, and no Postgres row. The only evidence was the legal-form
suffix inside each label (`N.V.`, `S.A.`, `Ltd`), which implies three countries
and asserts none. Wave 13b gives them `engineered_entity` rows.

### 14.8 · An early loader's view definition would silently shrink a later wave's — FIXED

`v_entity_jurisdiction` unions every table that knows an entity's jurisdiction.
Task 2 created it over two tables and Task 8 added a third, each loader
carrying its own `CREATE OR REPLACE VIEW`. Re-running **Task 2's** loader —
for any reason, on any branch — would have rebuilt the view without the third
source.

Nothing would have failed. The view still exists, every query still returns
rows, and cross-border counts quietly drop. It surfaced only because the column
rename (`lei` → `entity_id`, needed because engineered entities have no LEI)
made Postgres refuse the replace outright.

Same shape as §12.8 and §14.3: a wave asserting ownership over something it
only partly knows about. Both definitions now live in `ccf/views.py`, built
from **whichever source tables actually exist**, so a loader run at any point
in the sequence produces a view correct for that point and never one smaller
than the data. Verified by re-running Task 2's loader after Task 8: it reports
all three sources.

### 14.9 · Two of four planted contradictions were labels, not conditions — FIXED

Task 7 planted four registry contradictions and `beneficial_ownership.py`
recomputed only **two**. Both missing ones were `understated_pct`, and both sat
on chains whose TRUE effective stake was already below the 25% threshold —
4.32% and 20.38%. Understating 20.38% to 18.08% conceals nothing, because there
was no reportable beneficial owner either way. One of the two was, in fact, an
over-statement: it declared 11.39% against a truth of 4.32%.

The label said `understated_pct` on all four. Two of them were not
contradictions at all.

This is CLAUDE.md's *"volume targets are floors with a purpose"* failing in the
direction it warns about: the count was right and the condition was absent.
Fixed by choosing subjects for that plant from chains that actually clear their
threshold, and by a generation-time gate that RECOMPUTES every plant the same
way the validator does and refuses to write if any kind fails to reproduce.

**Only the validator's recompute found this.** A gate reading
`planted_contradiction_kind` would have reported 4 / 4 and been wrong about
half of them.

### 14.10 · Upserting a variable-length child collection is not idempotent — FIXED

`load_kyc_documents_wave13b.py` upserted documents and passages by id. When the
regenerated artifact turned a four-section ownership declaration into a
two-section certificate, the old `P03` / `P04` passages **survived** — anchored
to a document whose text no longer contained them.

Caught by the loader's own re-slice check on its second run: 12 stale passages,
every one of which would otherwise have looked live and anchored. Fixed with a
scoped delete of passages the artifact no longer names, restricted to `KYC-`
document ids so the 19,683 passages belonging to Waves 6 and 13a cannot be
reached from this loader.

Same family as §14.1's delisting: **an upsert-only loader is idempotent for a
fixed row set and not for a variable one.** Every loader writing a child
collection whose cardinality can change is exposed. Not swept this wave.

---

## 15 · Reporting bank entity (cast gap, closed 2026-08-22)

### 15.1 · One Call Report quarter does not reconcile against itself — FLAGGED, not corrected

`bank_capital` holds 12 quarters of real FDIC-published Call Report figures for
RSSD 852218. Eleven of them reproduce their own reported tier 1 ratio from
their own tier 1 capital and RWA to within **0.005pp**. One does not:

    2025-12-31   tier 1 294,807,000 / RWA 1,864,923,000 = 15.808%
                 reported 15.29%                          delta 0.518pp

The reported ratio implies an RWA near 1,928,103,000. The stored figure is also
the **only round-thousand RWA in the series** — every other quarter ends in
granular digits (…325, …050, …515), which is what a computed risk-weighted
total looks like.

So the anomaly is in FDIC's published data, not in the load. It is recorded in
two columns (`ratio_consistent`, `ratio_delta_pp`) rather than smoothed away,
because the two available ways to make it disappear both destroy information:
loosening the tolerance until it passes, or dropping the row.

**Why this matters more here than it would elsewhere.** §D of
`large-exposure-rwa-concentration` names *"capital-base date coherence — the
capital base and the exposure measurement must be reconcilable, and the
asymmetry disclosed where they are not"* as a validation gate. A quarter whose
own figures do not reconcile is precisely what that gate exists to surface, and
the capstone now has a real one to surface rather than an engineered one.

The loader's gate is written to match: **not** "every quarter reconciles",
which would have forced the smoothing, but "no more than two do not, every
exception is flagged, and the most recent quarter — the live denominator — is
not one of them."

### 15.2 · Bank-level Call Report, not holding-company FR Y-9C — RECORDED DEVIATION

§C names FFIEC CDR Schedules RC-C / RC-R, **FR Y-9C** and **FFIEC 101**. The
load uses the FDIC BankFind API, which publishes the same Call Report figures
in JSON with no credential, at **bank level** (RSSD 852218) rather than
holding-company level (RSSD 1039502).

Two consequences, stated now rather than discovered in the capstone:

- **FFIEC 101 advanced-approaches detail is absent.** A capstone that needs
  advanced-approaches RWA rather than the standardised figure will need it.
- **No holding-company consolidation.** The RSSD hierarchy edge is loaded, so
  the structure is there; the consolidated FR Y-9C figures are not.

Both are additive fetches against a public source, not redesigns.

---

## 16 · Wave 14 Task 12 defects — internal overlay / privacy ceiling

The task brief's own draft code shipped four defects, caught before any write
against the live stores (dry-run first, per the task's own instruction).

**16.1 · `stable_scalar` verification query missing `FROM`.** Would 500 rather
than the intended count check. Fixed: every SPARQL statement in
`loaders/load_abs_overlay_wave14.py` carries an explicit
`FROM <FLUREE_LEDGER_V2>`.

**16.2 · Partial `ON CONFLICT DO UPDATE` on all three overlay tables.** The
draft updated one column each (`abs_holding.notional`,
`abs_materialization_policy.posture`,
`abs_granularity_entitlement.max_granularity`); a re-run after a genuine
change to any other column would leave it stale while the row count stayed
put. Fixed: every non-key column is in the `DO UPDATE SET`.

**16.3 · The crosswalk rows were never actually inserted.** The draft printed
the column list and a NOTE telling a human to add the three trusts by hand.
A manual step is not a produced artifact and would not survive a re-run, and
the task's own definition of done requires the three trusts in the crosswalk.
Fixed: the loader inserts them, keyed on `(lei)` conflict, and the
`internal_client_id` column is absent from the `DO UPDATE SET` so a re-run
can never renumber a row that already exists.

**16.4 · `lei CHAR(20)` blank-pads a synthetic identifier shorter than 20
characters.** Found while fixing 16.3, not in the brief. The three trusts'
`SYN-<deal_id>` identifiers are 15-16 characters; `CHAR(20)` right-pads them
to 20 and returns the padding on every read (`'SYN-TAOT-2022-B'` comes back
`'SYN-TAOT-2022-B     '`). SQL equality treats the padding as insignificant;
a Python read-back, or any downstream consumer matching the string exactly,
does not. `crosswalk.lei` and `legal_entity.lei` were widened to
`VARCHAR(20)` — same 20-character ceiling, no padding. Confirmed
non-destructive: the existing 50 real, already-20-character LEIs are
unaffected in content (`ALTER COLUMN TYPE` from `bpchar` to `varchar` strips
trailing pad characters on cast).

**16.5 · Widening `legal_entity.lei` required dropping and rebuilding
`v_entity_jurisdiction` / `v_ownership_cross_border` (`ccf/views.py`).**
Postgres refuses `ALTER COLUMN TYPE` on a column a view depends on. The
loader drops both views before the `ALTER` and calls
`ccf.views.ensure_views()` immediately after, inside the same transaction —
using the one function every other loader that touches those views already
calls, rather than a second, competing `CREATE VIEW`.

**16.6 · Adding the three crosswalk rows without matching `legal_entity` rows
would fail the orphan gate.** Not in the brief's Interfaces section, but
`validators/conditions.py`'s counterparty-reference-snapshot check is a
`FULL OUTER JOIN crosswalk ... legal_entity USING (lei)` — a crosswalk-only
row IS an orphan by that query. Three minimal `legal_entity` rows
(`is_anchor = false`, so the `>= 50 anchor obligors` floor is untouched) keep
the join whole.

**16.7 · `LoanLevelPrivacyConstraint` was an unlisted `ex:` type, caught by
`validators/partition.py`.** The Fluree namespace-hygiene check
(`no ex: type shadows a FIBO term`) allowlists every legitimate `ex:` class
explicitly; a new one not added there reads as a shadowed FIBO term rather
than a deliberate extension. Added to `PERMITTED_EX_TYPES`. This is the
allowlist working as designed — it caught the missing registration rather
than silently passing.

---

## 17 · Wave 14 whole-branch review — accepted limitations, not fixed

Five findings from the final review, triaged **FILE-AS-KNOWN-ISSUE** rather
than fixed at the time. **17.1 and 17.4 were closed on 2026-08-23**; the
remaining three stand. Each is real, none is reachable with the current source
shape, and every one fails safe. Recorded so the next reader triages rather
than rediscovers.

### 17.1 ✅ CLOSED 2026-08-23 — the SDART servicer fixture could not detect an OC field swap

`validators/test_servicer_report.py` pins `oc_amount` and `oc_target` to the
same literal, `103857109.35`, because in the filing they genuinely are equal.
Measured across all 36 loaded deal-periods: only **one** has them differing
(`TAOT-2022-B` 2026-06, `80,453,472.38` vs `14,450,000.06`), and that one is in
the *labelled*-format oracle. So the numbered-format parser could transpose the
two fields and every numbered fixture would still pass.

**Closed without manufacturing an oracle.** The objection to fixing it was
that inventing values no filing contains trades a real oracle for a synthetic
one. `test_oc_amount_and_oc_target_follow_their_own_item_numbers` avoids that:
the base text is the real June excerpt, and the probe alters item `{66}`'s
value alone, then asserts the two fields diverge in the right direction. It
tests the parser's field MAPPING — a property of the code — rather than
claiming a filing says something it does not.

Falsified rather than asserted: swapping items 63 and 66 in
`ccf/servicer_report.py` makes the test fail, and restoring them makes it pass.

Two traps met while writing it, both worth carrying forward:
- The item-zone helpers operate on **stripped** text — `parse_servicer_report`
  calls `_strip_html` first — so a probe that mutates the raw HTML rewrites a
  digit inside the markup (`margin-top:0pt`) and corrupts the structure.
- After stripping, items `{63}` and `{66}` are the **byte-identical string**
  `'103,857,109.35'`, so locating the zone with `str.index` resolves to `{63}`
  and silently rewrites the wrong item. The probe anchors its search to the
  item's second `{n}` marker instead. That collision is precisely the
  indistinguishability this entry was about.

### 17.2 `_COLLECTIVE` in `generators/extract_prospectus.py` is regex-brittle

The collective-definition pattern is tuned to the two issuers loaded. A third
issuer phrasing its defined-terms article differently would not match.

**Fails safe, and that is the reason it is only a known issue.** The cross-check
at `generators/extract_prospectus.py:253-263` compares extracted definitions
against table mentions and raises `RuntimeError` on disagreement — so a miss
aborts the run rather than emitting a short extract.

### 17.3 `delinquency_buckets` stores its counts as strings

`loaders/load_abs_structure_wave14.py` stringifies the leaf values, so the JSON
reads `{'31-60': {'count': '4262', ...}}` — a count as text. Nothing reads the
value today (the only repo-wide mention is `validators/partition.py`'s
leak-detection allowlist, which matches on the field NAME). A future consumer
doing arithmetic on it would need to cast first.

### 17.4 ✅ CLOSED 2026-08-23 — `ledger_conflicts` could not see a predicate the run stops asserting

`loaders/load_abs_fluree_wave14.py:314-325` builds its conflict query from the
predicates present in the INCOMING triple set, then queries only those
predicates on those subjects. A predicate the ledger already holds but this run
asserts nowhere is therefore never queried, so its disappearance from the
generator is invisible to the conflict check.

The docstring framed the rule as "every predicate this run asserts must agree
with the ledger", which is exactly the framing that hid the gap.

**Closed** by a second sweep that runs the question the other way round: it
asks the ledger for every predicate on this run's subjects and reports any the
run asserts nowhere. Measured before writing it, so the exemption is evidence
rather than guesswork: exactly **one** such pair exists out of 196, and it is
legitimate — `ex:supersededBy`, which Task 10's amendment loader writes onto a
trigger node this loader owns. It is exempted **by name** in
`FOREIGN_PREDICATES`, never by prefix or namespace, so a second unexplained
foreign predicate fails rather than hiding behind the first.

Falsified: retiring `ex:thresholdUnit` from the generated set reports 10
conflicts, and retiring `ex:passageAnchor` reports 10 — where the old code
reported 0 for both. A clean run still reports nothing.

### 17.5 Wave 11c binding rows do not state triples-vs-subjects

`docs/ccf_dataprep_v2.md` Wave 11c rows carry bare assertion counts (1,724 /
227 / 274) while the Wave 14 rows establish the convention of reporting
`N (M subjects)` — which matters, because at least one Wave 14 predicate is
multi-valued and the two numbers differ. The older rows were never revisited.
A consumer reading both sections cannot tell whether an older count is
assertions or subjects.

---

## 18 · `memo_debt` reproduction check had become a freshness check (closed 2026-08-23)

Found while auditing every validator's exit code after the Wave 14 merge.
`validators/memo_debt.py` read **5/6** against a documented expectation of
6/6, and the failing check was "stored debt reproduces an independent
recomputation" — 20 divergences, every one on `signal_staleness`.

**It was not damage.** `signal_staleness` is `(today - last_filing) / 730`, and
`recompute()` took `date.today()` silently. The stored figures were computed on
2026-08-22 and the check ran on 2026-08-23, so every row was "wrong" by
**0.97–1.02 days** on a 730-day horizon — exactly the one day between the load
and the check, and nothing else.

**The defect is that the check could not fail for the reason it existed.**
A reproduction test asks "was this computed correctly?"; from the day after the
load it was silently asking "is this current?" instead. A genuinely
miscomputed table and a merely day-old one were indistinguishable, so the
check could never isolate the first.

The root cause was structural: `memo_context_debt` had **no evaluation-date
column**, and `generators/compute_memo_debt.py` stamped only `generated_at`
(when the file was written) into its artifact. The date the computation used
was recorded nowhere the validator could reach, so substituting `today` was the
only thing it could do.

**Closed in three layers:**

- `generators/compute_memo_debt.py` writes an explicit `as_of` alongside
  `generated_at`.
- `loaders/load_memo_debt_wave13a.py` carries it into a new `as_of DATE NOT
  NULL` column, with an idempotent migration that backfills from the
  artifact's `generated_at` — never from today, which is the wrong answer by
  construction.
- `validators/memo_debt.py` takes `as_of` as a **required** argument and
  recomputes each row against its own stored evaluation date. Reproduction is
  now exact and stays exact.

Freshness is still asked, as its own named check: "stored debt is younger than
its own 730-day staleness horizon". The bound is the horizon itself rather than
an invented number — a cache older than the horizon it measures against cannot
describe the staleness of anything.

**Both are falsified in the committed harness.** Corrupting a component reddens
reproduction alone; pushing `as_of` 800 days back reddens freshness. The new
arm needed its own `expect`: dropped into the existing mutation list it was
scored against "reproduces an independent" and would have been credited for
reddening the wrong gate — the exact miscount that list's own `run` docstring
warns about. Caught by reading the reported expectation rather than the `[ok]`
marker.

---

## 19 · Wave 15 segmentation and load defects (closed 2026-08-24)

Both were found while closing the `covenant-cross-reference` §F floor
"≥ 3 agreements with a filed amendment, so `as_of` changes which text
governs". Neither was caused by that work; both were pre-existing and silent.

### 19.1 ✅ CLOSED 2026-08-24 — the text before a document's first section marker was reachable by no anchor

`generators/segment_passages.py` built its spans as

    bounds = [p[0] for p in points] + [len(text)]

which starts at the **first** break point. The region from offset 0 to that
point was covered by no span at all, so no passage existed for it and no
anchor could reach it. Measured over the 62-document EX-10 corpus:
**880,471 characters** unreachable.

| Document | Head lost | of document |
|---|---:|---:|
| City Office REIT `d927791dex101.htm` | 163,541 | 28.9% |
| B&G Foods `tm2616882d1_ex10-1.htm` | 122,784 | 84.7% |
| American Healthcare REIT `ahr-ex10_1.htm` | 75,729 | 13.4% |
| Vertiv `exhibitno101termloancred.htm` | 46,352 | 7.1% |
| Smith & Wesson `swbi-ex10_107.htm` | 42,968 | **99.5%** |

**Smith & Wesson shows the failure at full strength.** Its first structure
marker sits at offset 42,968 of 43,198, so the only two spans the segmenter
produced were 152 and 78 characters, both below `MIN_CHARS`. `segment()`
returned `[]`, the caller's `if not passages: continue` dropped the document,
and it was absent from `passages.json` and from MongoDB **with no message on
any run**. The corpus reported 61 of 62 documents segmented and nothing named
the missing one.

This is what `covenant-cross-reference` retrieves against. A traversal for
text in the head region returns empty from a corpus that reports 16,780
passages and looks fully loaded.

**Fixed by appending the head spans, not prepending them.** `passage_id` is
positional — `{document_id}#p{idx:05d}` — so putting the recovered head first
would renumber every later passage in the document, and **43 Fluree
`ex:evidencedBy` triples point at those ids in a ledger that cannot delete**.
Appending recovers the text and leaves every existing id on the span it
already named. Verified against the real corpus, not a fixture:

    before 16,780   after 17,387   new 607
    LOST ids: 0     MOVED (offset or sha changed): 0
    35 distinct Fluree anchors, 35 resolving, 0 dangling
    documents whose passages do not start at offset 0: 0 of 62

Head passages carry `alignment: "window-head"` and `structure_aligned: false`
— they are best-effort windows by definition, and counting them as aligned
would inflate the measure `covenant-cross-reference` uses to tell a clean
citation from a best-effort one. The structure-aligned count is unchanged at
6,788.

Harness: `validators/test_segment_head.py`, five arms including a **negative
control** — a document whose first break point IS offset 0 must gain no head
passages. Without it, a fix that appended unconditionally would pass every
other arm while inventing passages for documents that never had a head.

### 19.2 ✅ CLOSED 2026-08-24 — re-running the corpus load silently discarded every embedding

`loaders/load_mongo_wave6.py` documents itself as *"Idempotent: upserts on
document_id / passage_id"*, and for the passage record it was. But the `$set`
payload carried

    "embedding": None,
    "embedding_model": None,

so **every re-run overwrote every vector with null.** Re-loading after the
19.1 re-segmentation left 17,387 of 23,100 passages unembedded; the 5,713 that
survived belong to other waves and were simply not in this loader's scope.

**Nothing counted it, and nothing could have.** The passage count is identical
before and after a wipe — 23,100 either way — so a count-based idempotency
check reports success while the entire similarity surface is gone. The
embeddings are a *field being reset*, and a cardinality cannot see a field.
The first measurement taken here made exactly that mistake: `count_documents({
"embedding": {"$exists": True}})` returned 23,100 and looked like full
coverage, because the loader writes the key with a null value. Only
`{"embedding.0": {"$exists": True}}` — naming a value rather than a
cardinality — showed 5,713.

**Fixed with `passage_update(p, existing_sha)`**, which splits three ways, and
the third case is the one a careless fix drops:

- **unchanged** (`existing_sha == p["sha256"]`) — write the record, leave the
  embedding fields untouched;
- **new** (`existing_sha is None`) — `$setOnInsert` them to null, so a
  consumer can tell "not embedded yet" from "field absent";
- **changed text under the same id** — `$set` them to null. A vector computed
  from different text is not a stale vector, it is a **wrong** one, and it
  answers similarity queries confidently. Preserving it would trade a wiped
  surface for a lying one.

Harness: `validators/test_mongo_embedding_preservation.py`, four arms. The
`changed` arm is the falsifier — a fix that only added `$setOnInsert` passes
the other three and fails this one.

### 19.3 ✅ CLOSED 2026-08-24 — every ultimate-parent edge in Fluree pointed the wrong way

Found 2026-08-24 while mapping `corporate-family-tree` §C into
`validators/spec_coverage.py`. **Not fixed — the remedy needs a decision,
because Fluree is append-only.**

`loaders/load_fluree_wave3.py` emits its GLEIF edges from one orientation:

    p, c = e["parent_lei"], e["child_lei"]
    predicate = (P_GLOBAL_ULTIMATE if e["edge_type"] == "hasUltimateParent"
                 else P_OWNS)
    triples += edge_triples(locals_by_lei[p], locals_by_lei[c], predicate=...)

Subject `p` is the parent, object `c` the child. **That is correct for `owns`
and inverted for `hasGlobalUltimateParent`**, because the two FIBO predicates
run in opposite directions: `owns` points parent → child, while
`hasGlobalUltimateParent` points child → parent. One variable order reused
across two predicates whose directions disagree.

`hasDomesticUltimateParent` has the same shape at lines 319-325, subject
`highest` (the parent), object `child`.

**Verified against the ontology, not the name.** FIBO's own published instance
data in `prod.fibo-quickstart.ttl`:

    Business Entity Data (BED) B.V. NL
        fibo-be-oac-cctl:hasGlobalUltimateParent  DepositoryTrustAndClearingCorporation

BED B.V. is the subsidiary and DTCC the ultimate parent, so the SUBJECT is the
child. `skos:definition` agrees — *"relates an organization to another
recognized as its ultimate parent"* — and `rdfs:range` is
`GlobalUltimateParent`, i.e. the object is the parent.

**Measured against GLEIF, which settles it.** Taking the 140
`IS_ULTIMATELY_CONSOLIDATED_BY` records in
`ccf_v2.corporate_ownership_record` as (child, parent) and comparing with the
Fluree edges restricted to both-ends-carrying-`ex:lei`:

    matched AS STORED (child hasGUP parent)  :   0 of 140
    matched REVERSED  (parent hasGUP child)  : 103 of 140

    IS_DIRECTLY_CONSOLIDATED_BY, as stored   :   0 of 140
    IS_DIRECTLY_CONSOLIDATED_BY, reversed    :  85 of 140

Zero as stored and 103 on reversal is not a partial-overlap signal; it is the
direction. 139 edges are affected (103 global + 36 domestic).

**Consequence.** `corporate-family-tree` exists to answer *who is the ultimate
parent of X*. Against this ledger that traversal returns X's **subsidiaries**,
and the reverse traversal returns its parents. Every entity that is genuinely a
subsidiary reads as a top-level parent, and the group heads read as leaves.

**Why nothing caught it.** Every registered condition passes, because all of
them are direction-blind:

| condition | why it passes inverted |
|---|---|
| ownership graph edges (all predicates) ≥ 500 | counts edges, not their direction |
| roots reaching 4+ hops ≥ 2 | an inverted tree is still 4 deep |
| cross-shareholding CYCLES ≥ 2 | a cycle reversed is still a cycle |
| entities carrying a real LEI ≥ 50 | says nothing about edges |

The graph is structurally perfect and semantically backwards, and a
count-shaped gate cannot tell those apart. The Wave 8 correction that moved
these 103 edges off `controls` onto `hasGlobalUltimateParent` fixed the
PREDICATE and preserved the orientation, so the defect survived a remediation
aimed straight at it.

**Fixed 2026-08-24, in three parts.**

**1 · The loader.** `load_fluree_wave3.py` now carries the orientation in one
place, `CHILD_SUBJECT_PREDICATES`, instead of leaving each call site to reuse
the same `(p, c)` order for four predicates that do not agree. Harness:
`validators/test_parent_edge_direction.py`, whose negative control requires
`controls` to stay parent -> child, so a blanket flip fails.

**2 · The ledger.** `loaders/remediate_parent_direction_wave15.py` retracted
139 inverted triples and asserted their reverses. Retraction was confirmed to
work on this build before anything real was touched -- a scratch subject
inserted, queried, deleted, re-added and deleted again -- and a full verified
backup was taken first (below).

**The first version of that script was itself defective**, and it is worth
recording because it is the same defect one level up. It selected "every edge
whose reverse is not already asserted", which corrects an inverted ledger once
and then inverts it again on the next run, while its docstring claimed
idempotence. Rewritten to decide each edge against the ancestry in
`sources/screening/gleif_relationships.json` -- object is an ancestor of
subject, KEEP; subject is an ancestor of object, FLIP; neither, report and
leave alone. That converges from any starting state and never guesses.

**3 · Verification, three ways, none of them a count.**

| check | before | after |
|---|---|---|
| GLEIF ultimate pairs matched AS STORED | 0 of 140 | **103 of 140** |
| GLEIF ultimate pairs matched REVERSED | 103 of 140 | **0** |
| re-run of the remediation | 139 inverted | **0 inverted · 139 already correct** |

and the product question directly:

    ultimate parent of AgilysysNvLlc        -> AgilysysInc
    ultimate parent of AmphenolBeneluxBV    -> AmphenolCorporation
    ultimate parent of AgilysysInc          -> (none, it is a group head)

Before the fix each of those was reversed: the group heads reported parents and
the subsidiaries reported none.

**Backup.** `backups/fibo-v2-t1451-2026-08-24T13-33-56Z.nt`, 63,973 triples,
verified against the live ledger with `loaders/dump_fluree.py --check` (0 in
file not in ledger, 0 in ledger not in file). Fluree 4.1.4 exposes no backup
endpoint; see §19.4 for what taking one uncovered.

### 19.4 ⚠️ LIVE HAZARD — Fluree 4.1.4 corrupts `xsd:date` literals on write

Found 2026-08-24 while establishing whether a logical dump of the ledger would
restore faithfully. **The estate is not affected today. The hazard is
prospective, and it is silent.**

Inserting a typed date and reading it straight back:

    inserted        returned        match
    2026-01-02      1972-01-01      MISMATCH
    1970-01-01      2014-03-28      MISMATCH
    2020-03-02      2014-03-30      MISMATCH
    2026-08-24      2014-04-01      MISMATCH
    1999-12-31      2014-04-03      MISMATCH

Every one wrong, and the returned values climb about two days per insert
regardless of the value supplied — a transaction-derived number, not a date.
The identical values written as plain strings round-trip exactly.

**Why nothing is broken now.** Every literal in `fibo-v2` is a plain string:
27,607 of 27,607 carry no datatype. `ex:validFrom` holds `"2024-12-19"` as
text, and text is safe.

**Why it matters anyway.** The obvious "improvement" to any loader here is to
give dates a proper `xsd:date` type. Doing that would silently destroy every
date it touched, and no check in the estate would see it: the triple count is
unchanged, the predicate is unchanged, and the value still looks like a date.
`ex:validFrom` and `ex:validTo` carry 1,979 assertions between them, and
`covenant-in-force-as-of` resolves against exactly those.

**Guarded rather than only documented.** `loaders/dump_fluree.py` reports the
typed-literal count on every dump and exits non-zero if it is not zero, so the
first typed literal to enter the ledger reddens the next backup instead of
being discovered during a restore.

Not investigated: whether this is a serialisation bug in the SPARQL layer or in
Fluree's own date handling, and whether `xsd:dateTime` behaves the same. The
estate has no reason to find out — plain strings work.

### 19.5 🟠 OPEN — 767 of 817 graph entities have no attributes to resolve

Measured 2026-08-24 while mapping `corporate-family-tree` §C. **Recorded rather
than fixed: the product's mapping in `spec_coverage.py` is not yet written, and
this is the finding that mapping will formalise.**

`corporate-family-tree` §C row 8 assigns *"Entity attributes for traversal
results"* to **Postgres** as `E`, and CLAUDE.md's single-writer rule says
Fluree nodes carry `lei` plus a display label and nothing else, so every
attribute a traversal needs resolves from Postgres. Measured against the
ledger:

    Fluree LegalEntity nodes                      817
      carrying ex:lei                             155
      lei RESOLVES in ccf_v2.legal_entity          50
      lei present but NOT in Postgres             105
      no lei at all                               662
        of which  synthetic — bridging            344
                  synthetic — engineered          128
                  NO provenance label at all      190

So a family-tree traversal returning any of 817 entities can resolve
attributes for **50**. The graph looks fully loaded and the attribute join
returns nothing for 94% of it.

**The 105 are the sharpest part.** They carry real, well-formed 20-character
GLEIF LEIs — `SuburbanPropaneLP`, `CelaneseNanjingAcetylDerivativesCoLtd`,
`AmphenolEastAsiaLimited`, `ZimmerInc` and so on — and appear in neither
`legal_entity` nor `crosswalk`. Checked for the `CHAR(20)` blank-padding
artifact recorded in the Wave 14 handoff and it is not that: the values are
exact 20-character LEIs on both sides, and 0 of the 105 are in `crosswalk`
either. They are simply absent.

**The 190 unlabelled nodes are a second, separate issue.** Non-negotiable rule
1 requires a provenance class on every element. `conditions.py` counts
entities as `?s ex:provenance ?p`, so those 190 are invisible to it — the
"entities in Fluree" floor of 500 is met by the 627 that are labelled.

Also unmapped, from the same session: §C row 4 *"Accounting consolidation
basis"* is assigned to Fluree and exists only in Postgres
(`corporate_ownership_record.relationship_type`, 140
`IS_DIRECTLY_CONSOLIDATED_BY` + 140 `IS_ULTIMATELY_CONSOLIDATED_BY`); no `ex:`
or FIBO predicate in the ledger carries it.

**FORMALISED 2026-08-24.** The mapping is now written — `FAMILY_TREE` in
`validators/spec_coverage.py`, all 11 §C rows accounted for, 4 probed clean,
1 covered, **6 deferred**. Writing it corrected one claim above and turned up
three gaps this note had not seen.

**Correction to this note.** It said §C row 5 *"Relationship status and
validity dates"* was *split* — dates in Fluree, status not. **The dates are
not there either.** The ledger's 1,750 `ex:validFrom` and 229 `ex:validTo` are
real, but **not one of them is on an ownership relationship**: grouped by
`rdf:type` they are Covenant (180), Amendment (25), CreditRating (245),
IssuanceEvent (788), SignalSource (409) and nine other event classes, and the
count on `cmns-org:LegalEntity` is **0**. The GLEIF source never carried them
— `sources/screening/gleif_relationships.json` has only parent_lei / child_lei
/ edge_type / jurisdiction — and `corporate_ownership_record.period_start` and
`.period_end` are **0 of 280** populated. So the row fails on both halves, and
`T` is claimed on it: the product cannot answer *was this parentage in force
on that date* for any edge. This is the shape memory calls **claims outlive
the data that refutes them** — a true count of a real predicate, attached to
the wrong row.

Both rows 4 and 5 share one cause: **Fluree's ownership edges carry no
properties at all.** `edge_triples()` emits a single bare triple per fact,
so there is nowhere for a basis, a status or a validity window to hang.
Closing either needs reified edges, which is a modelling decision, not a load.

**Three further gaps, found by writing the mapping.**

- **§C row 6, subsidiary list — three named sub-elements, one loaded.** The
  row asks for *name, jurisdiction and ownership %* from Exhibit 21. 344
  bridging stubs carry a name, **0 carry a jurisdiction**, and no ownership
  percentage exists on any family-tree edge. Jurisdiction is not a source
  limitation: `sources/screening/exhibit21.json` already holds it for **1,422
  of 1,635** subsidiaries and `load_fluree_wave3.py` drops it, calling
  `entity_triples(local, sub["name"], None, ...)`. The ledger's 50
  `hasOwnershipPercentage` assertions are **not** this row — they sit on
  `BO-*` beneficial-ownership chain nodes from Wave 13b, none typed
  `LegalEntity`. Consequence: §F's *"≥ 1 family spanning three jurisdictions"*
  is not answerable from the subsidiary layer, so jurisdiction entitlement
  filtering **is** the no-op §F wrote that floor to prevent.
- **§C row 7, stub entities — assigned to Postgres, present only in Fluree.**
  344 `synthetic — bridging` nodes with 355 `owns` edges pointing at them;
  `ccf_v2.legal_entity` holds 53 rows, all `public`, keyed on `lei`, which a
  non-LEI stub by definition has not got. No synthetic `SYN-` identifier is
  minted for them anywhere, so there is no key to join one on. This is the
  largest single cause of row 8's 6% attribute resolution.
- **§C row 9, materiality threshold by intent — the table of that name holds a
  different quantity.** §D's worked call is
  `?intent=concentration-review&materiality=0.05`, an ownership fraction.
  `ccf_v2.materiality_threshold` has three rows keyed on the **FX** intents
  (break-investigation, control-review, regulatory-report) and its column is
  **`threshold_pips`** — a post-trade tolerance in pips. `bo_threshold
  .threshold_pct` is a percentage but a beneficial-ownership one, keyed by
  jurisdiction and the KYC intents. A probe pointed at either table greens
  this row forever while the element stays absent; **count the unit the
  condition names.** Consequence: §D step 2 loads the materiality bound to
  `intent`, finds nothing to bind, and the Policy Operator filters nothing.

**Two of the six closed 2026-08-24**, and closing them surfaced two more
defects, both recorded below as §19.6 and §19.7.

- **Row 6's jurisdiction half** — `loaders/load_stub_jurisdictions.py` puts
  the Exhibit 21 jurisdiction on 304 of the 344 stubs (the other 40 were filed
  with the column blank), as `ex:jurisdictionCode` (ISO alpha-3, the same
  vocabulary the 190 ICIJ nodes already use) plus `ex:filedJurisdiction` (the
  string as filed). §F's *"≥ 1 family spanning three jurisdictions"* went from
  **unsatisfiable to 12 families**, the widest spanning 10 countries, and is
  now a registered condition. Row 6 stays deferred on ownership %.
- **Row 8 in full** — `generators/fetch_gleif_subsidiaries.py` +
  `loaders/load_gleif_subsidiaries.py`. Wave 3 fetched GLEIF Level 2 for these
  LEIs (who owns whom) and never Level 1 (who they are); `legal_entity` goes
  53 → 156 and every LEI-bearing graph entity now resolves. **Correction to
  this note: it was 103, not 105.** The other two are JPMorgan Chase Bank NA
  and JPMORGAN CHASE&CO, which resolve from `ccf_v2.reporting_bank` — their
  single writer — so they were never missing, only looked up in the wrong
  table. **No crosswalk rows** were written: these are GLEIF reference
  entities with no facility, deal or coverage against them, and minting
  internal client ids would have invented 103 client relationships to satisfy
  a validator (Dave's ruling, 2026-08-24). The probe is INVERTED — it measures
  the shortfall — because a count of what resolves returned 50 and would have
  passed this row at 50 of 155 for twelve waves.

**The two crosswalk checks were narrowed, not relaxed.** One FULL OUTER JOIN
became three counts that each name their own violation: a client id resolving
to nobody, an anchor with no client id, and — the one that keeps the coverage
— **an entity with internal data and no client id**, derived from where
internal data actually is (`facility`, `deal`, `coverage_assignment`) rather
than from `is_anchor`. The tempting narrowing was "non-anchors are exempt",
which would have let a real client be added as a non-anchor and never checked
again. `validators/test_crosswalk_invariants.py` injects a genuine violation
of each into a rolled-back transaction against the live database and requires
the count to move, plus a negative control asserting the 103 reference rows
are NOT violations. It runs `conditions.CROSSWALK_INVARIANTS` itself, not a
transcription.

**The two parent rows are probed by DIRECTION, not by count** — the durable
half of §19.3. `_oriented()` compares each edge against the GLEIF record it
was built from and returns 0 if **any single edge** contradicts it, because a
loader re-run over a subset is the realistic regression and it leaves most
edges correct. Currently 103 agreeing, 0 contradicting, on both rows.
`validators/test_orientation_probe.py` has eight arms; the falsifier is
`test_one_flipped_edge_zeroes_the_probe`, and a naive count-what-agrees
implementation passes six of the eight and fails exactly that one plus
`test_inverted_owns_edges_return_zero` (verified by mutation, 2026-08-24).

### 19.6 ✅ CLOSED 2026-08-24 — three Exhibit 21 TABLE HEADERS were companies in the graph

Found 2026-08-24 while dry-running `load_stub_jurisdictions.py`, which counted
345 labels across 344 stubs and stopped to ask why.

`local_name()` in `load_fluree_wave3.py` normalises a subsidiary name through
`.title()` and strips punctuation. Genesis Energy's Exhibit 21 contains a row
reading `SUBSIDIARY` and Hain Celestial's contains one reading `Subsidiary` —
**both are table headers mis-parsed as company names** — and both normalise to
the same local name. The result is one node carrying two `rdfs:label` values,
`owns` edges from *both* anchors, and one outgoing `owns` edge of its own:

    <ex:SubSubsidiary>  rdfs:label  "SUBSIDIARY"
    <ex:SubSubsidiary>  rdfs:label  "Subsidiary"
      owned by: Genesis Energy Limited, THE HAIN CELESTIAL GROUP, INC.

So two unrelated filers share a subsidiary that is a spreadsheet header. It is
the **only** local-name collision in all 1,635 subsidiaries — checked
exhaustively, not sampled — and both source rows have a blank jurisdiction, so
the new loader writes nothing to it either way.

**And it was not one node but THREE.** The exhaustive check that found only
one *local-name collision* asked the wrong question — it looked for two
DIFFERENT names normalising to the same local, which is what `SubSubsidiary`
is. Two filers writing the SAME header string produce one key and no
collision, so it missed:

| phantom | labels | owned by |
|---|---|---|
| `SubSubsidiary` | `SUBSIDIARY`, `Subsidiary` | Genesis Energy · Hain Celestial |
| `SubLegalName` | `Legal Name` | Las Vegas Sands · Targa Resources |
| `SubCompanyName` | `Company Name` | Regis Corporation |

**Root cause, and it is one character.** `fetch_exhibit21.py`'s header filter
opened with `subsidiaries?` — the `?` applies to the final `s`, so the
alternatives are `subsidiarie` and `subsidiaries` and **the singular falls
straight through**. `Legal Name` and `Company Name` escaped a second way: the
regex is anchored at `^` only, and the header word is not first.

**Fixed in four places.**

1. **The parser.** Split into `BARE_HEADER` (whole-cell, both ends anchored)
   and `NOISE` (true prefixes only). This also repairs a silent over-filter
   running the other way: the old prefix rule dropped `Country Kitchen LLC`,
   `Entity Solutions Group, Inc` and `Named Sub Holdings Inc` — real companies
   whose names merely BEGIN with a header word. Verified in both directions,
   8 header forms dropped and 7 real names kept.
2. **The source artifact.** The corrected filter was re-applied to
   `sources/screening/exhibit21.json`, dropping exactly the 5 header rows and
   nothing else; 1,635 → 1,630. Not re-fetched: re-parsing 50 filings would
   churn every name and orphan 341 stub URIs in an append-only ledger.
3. **The ledger.** `loaders/remove_header_phantoms_wave15.py` retracted 35
   triples. It DERIVES the phantom set by applying the parser's own
   `BARE_HEADER` to stub labels rather than hardcoding three names, so the two
   cannot drift apart, and it refuses to run if a phantom's child would be
   left unreachable. Verified per named subject: 0 triples remain for each.
4. **The loader.** `load_fluree_wave3.py`'s dedup was `local in
   locals_by_lei.values() or local in made`, and `made` is rebuilt PER FILER —
   so a local already created under another anchor passed both tests and the
   second filer re-asserted the same node with its own label and edge. `taken`
   is now global, and a genuine cross-filer name clash gets a DISTINCT `...N2`
   local rather than being skipped: skipping would drop a real subsidiary with
   no trace, which is the harder failure to ever notice.

**Two real companies came back.** The header rows had displaced them from
their filers' top-20 windows: `GEL PALOMA, LLC` (Genesis Energy) and
`HCGI U.S. Finance Co., LLC` (Hain Celestial). Re-running the wave-3 loader
after the source fix added exactly those two and nothing else — the ledger was
a strict subset of a fresh build, 0 nodes present here and absent there — and
the direction probes still read 103/103 afterwards, confirming the §19.3 fix
converges rather than re-inverting.

**The gate that would have caught it** is now registered: *stubs owned by two
filers (want 0)*. It excludes stub parents, because a stub in an engineered
depth chain legitimately has two — its anchor and the stub above it. Nine do.
A gate counting parents rather than non-stub parents would have fired on all
nine on its first run and been deleted as noise, taking the real check with
it; `test_family_tree_probes.py` has that false-positive control, and
mutating the exclusion away fails it.

### 19.7 ✅ CLOSED 2026-08-24 — re-running the Wave 1 loader made eight-day-old data claim to be fresh

`load_postgres_wave1.py` stamped `retrieved_at` from `date.today()` on all 50
anchors and their filing profiles. But this loader **fetches nothing** — it
reads `sources/screening/anchors_final.json`, whose GLEIF and EDGAR calls were
made on 2026-08-16. Every re-run silently advanced the provenance of the whole
anchor spine by however long had passed since.

**Found by diffing the table field-by-field either side of a re-run**, not by
counting it: 156 rows before, 156 rows after, and 50 of them moved from
`2026-08-16` to `2026-08-24`. This is the §19.2 shape again — *a cardinality
cannot see a field being reset* — and it is why the idempotency proof for both
new loaders in this wave names a value rather than a count.

The re-run happened because the loader's own join check had to be narrowed for
the 103 reference entities, and verifying that fix meant running it.

**Fixed** by recording the true retrieval date in `anchors_final.json` — a
file that predates the `sources/*/manifest.json` convention and carried no
date of its own; the value was recovered from `legal_entity.retrieved_at`
before the re-run overwrote it — and reading it there. A **missing** date is
now a hard failure, not a fallback to today, because falling back to today is
the bug. The 50 anchors were restored: the table is byte-identical to its
pre-run state across every column.

`loaders/load_gleif_subsidiaries.py` reads its own `retrieved_at` from
`sources/gleif_l1/manifest.json` for the same reason.

### 19.8 ✅ CLOSED 2026-08-24 — the one-file FIBO check could not see 40 modules, nine of ours among them

Raised by the vault custodian, verified independently here before accepting,
and the verification found a better remedy than either side had.

**The claim this estate had been making.** `docs/HANDOFF.md` and
`docs/ccf_dataprep_v2.md` both said `prod.fibo-quickstart.ttl` is *"the whole
of FIBO Production … every module in a single file"*, and absence claims were
written against it. It is not. It loads **Release maturity only** and omits 40
Provisional modules — 193 prefixes against `dev`'s 232.

**Nine of this estate's own bound terms are in those modules** and return zero
mentions of any kind in `prod`:

    SEC/Debt/CollateralizedDebtObligations/  CollateralizedDebtObligation, TriggerEvent,
                                             TrancheType, hasTrancheType, specifiesTrigger,
                                             SeniorCDOTranche, MezzanineCDOTranche,
                                             SubordinatedMBSTranche
    SEC/Debt/MortgageBackedSecurities/       MortgageBackedSecurity

The bindings are correct; the checker was blind. Confirmed here by fetching the
CDO module directly and applying our own prescribed test — its
`owl:Ontology rdf:about` equals the requested namespace, so this is not the
HTTP-200 path-prefix trap of §11.x — and reading the header:

    <fibo-fnd-utl-av:hasMaturityLevel rdf:resource="&fibo-fnd-utl-av;Provisional"/>

**This is our own lesson arriving from outside.** `output-that-never-varies`
says to test a checker with a known-present AND a known-absent input and
require the answers to differ. The one-file method was only ever fed
`NotARealTermXYZ → 0`, which exercises absent → 0 and nothing else.
`fibo-sec-dbt-cdo:TriggerEvent` is the input that discriminates: real,
resolvable, declared, and absent from the file. Against it the method fails.

**The remedy, which is better than the custodian's.** They concluded the one
fetch answers presence but cannot prove absence, and that a clone is needed
for absence. It is not: **`dev.fibo-quickstart.ttl` is a verified strict
superset** — 8,966,028 bytes, 19,885 declared subjects against `prod`'s 18,254,
and the only subject in `prod` and not in `dev` is the `QuickFIBOProd/`
ontology header itself. All nine Provisional terms are in it; the known-absent
control still returns 0; a known-present Release term returns the same count in
both.

So the rule is three-way, and the two files answer different questions:

| Result | Means |
|---|---|
| in `prod` | Release maturity — bind freely |
| in `dev` only | real, but Provisional or in development — check the module header before binding |
| in neither | **does not exist.** This is the only sound absence claim |

**Fixed:** `HANDOFF.md`, `ccf_dataprep_v2.md` and §2.7 above all corrected;
§2.7 had said the same thing in Wave 2 and was overwritten by a confident wrong
claim in Wave 14, which is `claims-outlive-the-data-that-refutes-them` running
in the direction nobody watches — **the refutation outlived by the claim.** Its
own cited example had gone stale too (`CreditFacility` is present, 18 mentions),
which is exactly why the stale entry lost the argument to the newer wrong one.

**An owed item closed by the same fetch.** `ex:CollateralPledge` was "verified
absent from complete FIBO Production", which was weaker than it read. Re-run
against `dev`: every local name containing `Pledge` or `Lien` is
`NegativePledge`, `LenderLienPosition`, `PrimaryLienPosition`,
`SubordinateLienPosition`, `isLienOn`. No `CollateralPledge`. The claim holds,
now on evidence that can carry it.

**And the remedy §2.7 prescribed was never available.** It said absence claims
"require the `edmcouncil/fibo` repository". Searched 2026-08-24: there is no
such clone under `/home/parkave` at depth 4, `sources/fibo/` is empty, and the
only FIBO artifacts on disk are this repo's own Turtle samples and a Fluree
example directory. (The deeper `.rdf` sweep was killed by its timeout, so this
is "not found where it would be", not an exhaustive disk proof.) That matters
for how the Wave 14 claim took hold: **the correct rule pointed at a resource
nobody had, so following it cost a 295-module scan and following the wrong one
cost a single fetch.** A caveat whose remedy is unaffordable does not get
obeyed; it gets replaced. The `dev` file is the first version of this rule that
is both correct and cheap.

**Still outstanding from the same exchange:** `partition.py`'s shadow check
asks "does this shadow a **Release-maturity** FIBO term", so a Provisional
shadow passes it silently. Not yet repointed at `dev`.


---

## 20 · `prospect_note` keyed by display name, not id (FIXED 2026-08-24, Wave 16)

**Found while planning Wave 16 Task 3.** `prospect_note.banker` held a free-text
display name — `"R. Bhattacharya"`, `"T. Nakamura"`, `"M. Lindqvist"`,
`"A. Okonkwo"` — with no key into Postgres. The roster is 40 `banker` rows over
only 32 distinct `full_name` values, so even a name-matching join would have
been ambiguous by construction: three of the four values are absent from the
roster entirely, and `"M. Lindqvist"` surname-matches four different bankers.

This blocked CLAUDE.md Rule 4 (the crosswalk is mandatory or nothing joins) for
the `ib-opportunity` product two ways at once: §D step 6 ("resolve *this*
banker's notes") had no way to say whose notes, and §F's "≥5 notes that change
**a** ranking" could not attribute a note to the ranking it changed.

**Fix:** `loaders/repair_prospect_note_keys_wave16.py` adds `banker_id TEXT`
and `banker_display TEXT` to `prospect_note`, assigns `banker_id`
deterministically (sorted `note_id`, round-robin over the Postgres
`coverage_assignment` bankers for that note's LEI, primary first) and preserves
the original string in `banker_display` rather than overwriting it. Idempotent
— proven by a named-value re-read, not a row count, per the project rule that
counts can't see a field silently reset. All 18 current notes resolved; the
"no coverage for this LEI" fallback path exists but is unexercised on current
data (every note's LEI is covered), so it ships unverified by data and should
not be trusted as tested until a future load exercises it.

`validators/test_ib_rank.py::test_every_prospect_note_resolves_to_a_banker`
guards the invariant that every `prospect_note.banker_id` resolves in Postgres
`banker.banker_id`.

**Estate grep for other name-based banker joins** (Step 8, this task):

```
grep -rnE "banker[^_a-z]" --include=*.py loaders/ generators/ validators/ | grep -v banker_id
```

No other instance of joining bankers by name was found. All remaining hits are
column definitions (`"{S}".banker` table/CHECK constraint in
`loaders/load_postgres_wave10.py`), comments/docstrings, local variable names
that happen to be named `banker`, or the new files from this task itself. The
defect was isolated to `prospect_note`.

---

## 21 · MongoDB `document.doc_type` — 178 pre-existing rows carry `None` (OPEN, found 2026-08-24, Wave 16 Task 13)

**Found while loading the merger-proxy / S-4 corpus.** Every one of the 178
`document` rows loaded before Wave 16 Task 13 — Wave 6's EX-10 corpus, Wave
13a's 10-K/10-Q/8-K narrative sections, Wave 13b's KYC filings — carries no
`doc_type` value at all (`db.document.distinct("doc_type")` returns `[]`;
`count_documents({"doc_type": None})` returns 178). Neither
`loaders/load_mongo_wave6.py` nor `loaders/load_narrative_wave13a.py` ever
wrote the field.

**Not fixed here, deliberately.** `loaders/load_mongo_wave16.py` sets
`doc_type` on the 15 documents it writes (`merger_proxy` for
DEFM14A/PREM14A, `registration_s4` for S-4/S-4A — the same vocabulary
`generate_opportunity_signals.py`'s `signal_type` already uses for these
filings) and stops there. Back-filling the 178 would be exactly the
`positional-identity-is-a-defect-class` / silent-rewrite-of-another-wave's-data
pattern this estate has hit before: this task did not write those rows, and
for several of them (the narrative sections span three SEC form types across
two different item numbers each) the honest `doc_type` value is not a single
obvious string from where this loader sits.

**Estate grep for the field:**

```
uv run python3 -c "
from ccf.config import mongo_db
db = mongo_db()
print(db['document'].count_documents({'doc_type': None}))       # 178, pre-existing
print(db['document'].distinct('doc_type'))                       # ['merger_proxy', 'registration_s4']
"
```

**Left for whoever owns the EX-10 / narrative corpora next:** a `doc_type`
backfill pass for those 178, with a mapping table (`form` + `section` ->
`doc_type`) proposed and reviewed before running, not inferred silently by a
loader that also does something else.

`validators/test_ib_rank.py::test_merger_corpus_documents_carry_doc_type_and_the_178_gap_is_untouched`
guards both halves: the 15 new rows carry a valid `doc_type`, and the
178-row gap is still exactly 178 (fails loud if a future change either
back-fills it or corrupts the count).

---

## 22 · `read_catalog()`'s §C heading match was case-sensitive (FIXED 2026-08-24, Wave 16 Task 16)

**Found by Wave 16 Task 15**, surfaced while registering `ib-opportunity-synthesis`
in `validators/spec_coverage.py`: an unfiltered run of that validator crashed
with `RuntimeError: no §C Data Catalog section in counterparty-reference-snapshot`
before it reached any product alphabetically after that one.

**Root cause.** The vault has edited `counterparty-reference-snapshot.md`'s §C
heading to read `## C · Data catalog` — lowercase "catalog" — while every other
spec, including the eighteen this estate has already built against, still reads
`## C · Data Catalog`. `validators/spec_coverage.py`'s `read_catalog()` matched
the heading with a case-sensitive regex, so it could not read the catalog of the
**foundational** product — the one every other product inherits its correlation
machinery from — and `validators/test_spec_coverage.py::test_every_registered_product_has_a_readable_catalog`
failed for the same reason.

**Not a data defect — a drift in the source we read, not in what we built.**
This repo does not edit the vault (`CLAUDE.md`); the fix belongs on the reading
side.

**Fix.** `read_catalog()`'s heading regex now compiles with `re.IGNORECASE` in
addition to its existing `re.S | re.M`, so both `## C · Data Catalog` and
`## C · Data catalog` parse identically.
`validators/test_spec_coverage.py::test_catalog_heading_case_is_tolerated`
constructs both spellings and requires both to parse — a case-sensitive
regression would fail it immediately, not silently pass on the eighteen specs
that happen not to have drifted yet. The vault mirror was not touched; the
custodian was told about the drift through the agent exchange (see the Wave 16
close bundle) as information, not a request — they may want the source spec
made consistent, but that is their call, not this repo's to make.

**Estate-wide implication.** Any other structural-parse regex in this codebase
that assumes a heading's exact case is one vault edit away from the same
failure mode. `read_catalog()` is the only one keyed off §-section headings at
the moment; a future one should default to case-insensitive unless a real
reason requires otherwise.

---

## 23 · A fetcher matching a form-name literal breaks the day the SEC renames the form

**Found and fixed in Wave 16 Task 4** (`generators/fetch_schedule13d.py`), while
sourcing real Schedule 13D filings for `ib-opportunity-synthesis`. The SEC
renamed the form from `SC 13D` / `SC 13D/A` to `SCHEDULE 13D` / `SCHEDULE 13D/A`
effective 2024-12-06. A fetcher that matches only the legacy literal `SC 13D`
returns **zero** filings for anything filed after that date — not an error, not
an empty-with-warning, just a query that quietly stops finding what it used to
find. Nothing about the failure looks like a bug from inside the fetcher; it
looks exactly like "there were no more 13D filings," which is false.

**This repo's fetcher handles both eras.** `FORMS` in
`fetch_schedule13d.py` lists all four literals (`SC 13D`, `SC 13D/A`,
`SCHEDULE 13D`, `SCHEDULE 13D/A`) and matches by **exact form string**, not
substring — a substring match on `SCHEDULE 13D` would also swallow a
hypothetical future `SCHEDULE 13D-X`, and a substring match on `SC 13D` would
match inside longer strings. `docs/wave16-plan/task-4-brief.md`'s own test
list (`matches("SC 13D")`, `matches("SCHEDULE 13D")`,
`matches("SCHEDULE 13D/A")`) is satisfied.

**Recorded here as a pattern, not a defect, because it will happen again.**
Any other generator or fetcher in this estate that matches a SEC (or other
regulator) form name as a literal string carries the same failure mode the
moment that body renames, splits, or reformats the form. `item` codes (8-K
Item 2.01/2.03/2.04/4.01/4.02/5.02), `EX-10`/`EX-21` exhibit labels, and proxy
form types (`DEFM14A`, `PREM14A`, `S-4`, `S-4/A`) are all exposed to the same
class of risk. There is no generic fix to apply pre-emptively — the fix is
this: when adding a new form-name-literal match, check whether the form has
been renamed in the fetch window before assuming the literal is stable, the
way Task 4 did for 13D.

---

## 24 · `rating-and-spread-migration`'s dominance ratio moved 18% when Wave 16 loaded, and nothing noticed (found in final fix wave review, 2026-08-25)

`validators/series.py`'s `dominance_ratio_excluding_windows()` (§7 risk #1,
`DOMINANCE_CEILING = 0.40`) medians over the **entire** `spread_observation`
table with `SELECT instrument_id, obs_date, idiosyncratic_bp, market_oas_bp
FROM "{S}".spread_observation` — no writer filter, no product scope. That
table is not owned by one product: `rating-and-spread-migration` put 29,885
rows there (the original 60 `syn-i-*` instruments), and Wave 16's Task 8b
(`docs/ccf_dataprep_v2.md`, "Wave 16 Task 8b") added another 36 `w16-i-*`
instruments and 17,964 rows on top, for a different product
(`ib-opportunity-synthesis`).

Adding those rows moved `rating-and-spread-migration`'s own dominance ratio
from **0.1854 to 0.2196** (whole-branch review measurement, pre-fix) — an
18% relative shift, re-measured live in this fix wave at **0.2190** (small
drift from the review's figure is expected; both were taken against the
same growing table at slightly different points in this wave's work,
nothing else changed the query). **Still under the 0.40 ceiling**, so the
condition kept passing and nothing failed, logged, or flagged — the shift
is real and invisible by construction of the check.

**Not fixed here, deliberately.** `dominance_ratio_excluding_windows()`
scoping its query to `rating-and-spread-migration`'s own writer (the
`syn-i-*` prefix, or equivalently excluding `w16-i-*`) would change what
that product's condition measures, and that is not this wave's decision to
make — `ib-opportunity-synthesis` built the new rows for its own reasons
(the debt-maturity-ladder floor, `docs/ccf_dataprep_v2.md` Task 8b) and
whoever owns `rating-and-spread-migration`'s condition definition should
decide whether "dominance across every instrument in the table" or
"dominance across this product's own instruments" is the intended
semantics — the query has silently been the former since Wave 16 landed.

**Recorded here so the next person who sees 0.2190-ish instead of 0.1854
knows why it moved and that it was a known, reviewed, intentional
side-effect of an unrelated product's data landing in a shared table — not
a fresh regression to chase.** If the ceiling is ever approached (unlikely
at current margins — 0.22 vs a 0.40 ceiling — but not impossible if a
future wave adds more `spread_observation` rows the same way), re-open this
entry and revisit the scoping question above rather than widening the
ceiling to make it pass.

---

## 25 · `ex:Alert` is intentionally UNBOUND — Postgres-owned, no RDF representation needed

Wave 17 Task 4's controller-supplied term list to bind before generating
against it (`docs/wave17-plan.md` Task 4, Step 1) named eleven terms,
including `ex:Alert`. The first cut of this task bound all eleven,
including `Alert`, and recorded the absence of a named Fluree writer as an
open question for Task 18. **Reviewed and corrected: `ex:Alert` should
never have been bound, and is not, as of this correction.**

§C assigns "Alert records and prior-alert history" to Postgres. Task 12
(`docs/wave17-plan.md`, "Task 12") models AML alerts entirely there —
`{"alerts": [{"alert_id", "subject_party", "raised_at", "case_id",
"trigger", "provenance"}], "links": [...]}` loaded into `aml_alert` /
`aml_alert_link` — with no Fluree representation anywhere in the plan.
**A Postgres-owned element gets no RDF class.** This wave already set the
precedent two commits earlier: Task 3's own note reads "No new FIBO
bindings. This task writes only MongoDB rows... no Fluree types or
predicates, so the binding table and its vault mirror are untouched."
`Alert` should have had the same treatment from the start.

The other ten terms in the controller's list are unaffected — each has a
concrete Fluree writer named in Task 13 or 14, which is this estate's
ordinary bind-ahead-of-the-writer pattern (CLAUDE.md: "bind upstream,
verify, generate, then flag the mirror"). This entry is about the one term
that does not fit that pattern, not a challenge to the pattern itself.

**If a later task ever needs an alert node in Fluree** — e.g. to let a
network view connect an alert to the `matchesTypology` edge that triggered
it — bind `ex:Alert` at that point, against a concrete writer, the normal
way. Nothing here forecloses that; it only says binding it NOW, with no
writer and no §C assignment to Fluree, was the mistake.

`~/.agent-exchange/ccf-dataprep/outbox/2026-08-25T06-55-08Z-wave17-aml-typology-bindings/`
is now superseded — it named `ex:Alert` as one of eleven bound terms. Per
the controller's ruling, exchange bundles are immutable, so no correction
was sent from this task; Task 18's wave-close bundle names the corrected
ten-term set and marks the `06-55-08Z` bundle superseded.

---

## 26 · `ccf.aml.RealNameIndex` — three bypass rounds and the measured exact-scan cost

Wave 17 Task 5 built `ccf/aml.py`, the name guard CLAUDE.md rule 2 requires
before any synthetic AML party is minted. Its module docstring used to cite
"the Task 5 report" for the full account of how it got to its current
shape — a `.superpowers/` scratch artifact that is deleted when this wave
closes. This entry is the durable home for that history, and
`ccf/aml.py`'s docstring now points here instead.

**Three review rounds, three different bypasses, in a shortlisting index
that no longer exists.** `blocks()` originally shortlisted candidates
against only the rarest token/n-gram posting lists before scoring, rather
than scanning every indexed name. Coordinator review found a different
constructible bypass in that shortlist each round:

1. **Pure token reordering.** `"GROUP DEVELOPMENT AND TECHNOLOGY"` scores
   `similarity() == 1.0` against the real, currently-sanctioned
   `"TECHNOLOGY AND DEVELOPMENT GROUP LTD"` (`sanctions_name` SDN-8408),
   but every shared token was common enough in the corpus to exceed the
   rarity cap on its own, so the shortlist dropped all of them and
   `blocks()` returned `None`.
2. **Token substitution**, after (1) was patched with an exact-token-set
   route. `"TECHNOLOGY TRADING DEVELOPMENT GROUP"` (`similarity() ==
   0.9118` against the same SDN-8408 name) still returned `None`:
   substituting one token minted an accidental n-gram at the new word
   boundary that was rarer than the genuinely shared keys, so the
   rarest-first cap picked the wrong keys.
3. A third bypass shape (a further substitution variant) was found after
   round 2's fix. Rather than patch a third time, the shortlisting index
   was **deleted outright**. `blocks()` now runs a linear EXACT scan over
   every indexed name, with only one skip — the length-ratio +
   token-Jaccard prefilter, proved lossless in the module docstring and
   covered by `validators/test_aml_typology.py::test_blocks_prefilter_skip_is_lossless`
   (added Task 6 Step 0a, after three review rounds went by with no test
   of the skip itself — every existing test asserted only that specific
   strings blocked, which a widened skip would still have passed).

**A reported score traced to `quick_ratio()`, not `similarity()`.** One
bypass string cited in round 2 review, `"NATIONAL DEVELOPMENT NATIONAL
INVESTMENT GROUP"` against real `"NATIONAL DEVELOPMENT AND INVESTMENT
GROUP"` (SDN-25421), was reported at "similarity 0.9195". Recomputed with
this module's own `similarity()`, the true score is
`0.896551724137931` — below `BLOCK_THRESHOLD` (0.90), so `blocks()`
returning `None` for that literal string is correct, not a residual
bypass. `0.9195` is exactly `SequenceMatcher.quick_ratio()` for that pair —
difflib's own documented fast *upper-bound* approximation, never what
`BLOCK_THRESHOLD` is compared against. The underlying substitution
mechanism is real and independently confirmed with a corrected candidate,
`"NATIONAL DEVELOPMENT TRADING INVESTMENT GROUP"`, `similarity() ==
0.9302325581395349`.

**Measured cost of the exact scan** (2026-08-25, 72,869 indexed records,
this machine):

    RealNameIndex.build():                              ~0.5s
    200 blocks() calls, Task-6-shaped candidates:        ~75s total, ~375ms/call avg
    (candidates: two short invented words + one of
     {Holdings, Trading, Capital, Ventures, Partners,
      Group, Logistics, Maritime, Textiles, Resources,
      International, Shipping})

Total for a Task-6-sized run (build + 200 calls): roughly a minute, one
time, at generation — not a per-request cost anywhere in this project,
since it has no runtime/serving component. One of the 200 random
candidates measured this way, `"Jgbn International"`, legitimately
collided with the real `"GPB INTERNATIONAL SA"` on the character-level
measure — not a defect, but exactly the kind of coincidental near-miss the
guard exists to catch. A generator hitting this is expected to retry with
a different name, the same as for any other block.

`blocks()` is now O(number of indexed names) per call by design. That is
fine for a one-time ~200-party generation batch; it would not be fine for
a per-request serving path, which this project does not have and must
never build (CLAUDE.md, "explicitly out of scope"). If a future task calls
`blocks()` at a much larger scale (thousands of calls, not ~200), re-measure
before assuming this cost still holds.

---

## 27 · Fluree's SPARQL engine does not enforce same-variable-same-value within one triple pattern

**Found in Wave 17 Task 13**, writing a reflexive-edge guard for
`ex:transactedWith`. The obvious query for "does any node point at
itself" is `?s <ex:transactedWith> ?s` — repeating the variable name so
both positions must bind to the same value, standard SPARQL semantics.
Against this deployed Fluree instance (4.1.4) that query returned
**7,736**, the total edge count, not 0: every edge matched, as if the two
`?s` occurrences were independent variables that happened to share a name
rather than a single join constraint.

**The fix is an explicit filter, not a rewritten pattern:**
`?s <p> ?o . FILTER(?s = ?o)` — this correctly returned 0, confirmed
against the same data where the repeated-variable form returned 7,736.
No reflexive edge actually existed; the loader's own Python-side
`from_party == to_party` guard had already prevented one. This was a test
authoring mistake caught by watching a new test fail for the RIGHT
reason before trusting it (`superpowers:test-driven-development`),
not a data defect.

**Recorded here as a pattern, not a one-off.** Any query in this estate
relying on a repeated variable name within a single triple pattern to
express an equality constraint should be treated as unverified against
this Fluree build until checked the way this one was — write the
positive control (an actual match) and the negative control (an actual
non-match) and confirm both, the same discipline `ccf.fibo.fibo_absent()`
already requires for a different reason (known-issues §19.8's positive-
control rule). An explicit `FILTER(?a = ?b)` is the safe form; a bare
repeated variable is not proven safe here.

## 28 · Task 13's commit message says "15 new tests"; the diff added 13 (recorded, not fixed)

Commit `b7e652a` ("Wave 17 Task 13: Fluree nodes, network, ownership,
typologies") closes with "`validators/test_aml_typology.py`: 15 new
tests. Whole file: 95 passed." Re-counted independently at Task 18
close-out: `git diff b7e652a^ b7e652a -- validators/test_aml_typology.py
| grep -c '^+def test_'` returns **13**, not 15. The two numbers the
commit message chains off it — 95 total in the file, 341 in the whole
repo — are both independently correct (`docs/ccf_dataprep_v2.md`'s Task
13 entry already carries a 2026-08-25 correction recording the same
discrepancy and fixing the DOC's own count from 15 to 13; this entry is
about the COMMIT, which the doc fix could not touch).

**Not fixed, because it cannot be — the commit is already pushed to
shared history**, and rewriting a pushed commit's message would be a
worse defect than the one being recorded (a force-push against a branch
other sessions may have already based work on). Recorded here instead,
per this file's own purpose: a wrong claim that outlives correction
should be named where the next reader will find it, not silently
tolerated.

**Pattern, not a one-off.** This is the same shape `docs/ccf_dataprep_v2.md`'s
Task 13 entry corrected once already: a commit or doc line stating a test
count from memory rather than from a fresh `grep -c '^def test_'` (or
equivalent) against the actual diff. The fix that would have prevented
this — count from the diff, never restate a number carried in your head
from a few tool calls earlier — is the same discipline this repo's
`known-issues.md` has recorded failing before under "count the unit the
condition names."

---

## 29 · Task 4's fourth typology is a substitution AND an abstraction — satisfied with divergence, recorded in three places

Wave 17's `aml-typology-match` §C row **"Typology structural patterns —
layering, structuring, rapid pass-through, shell company ownership"** is
satisfied, but not on the spec's own terms. Two divergences, both ruled
deliberately, neither a gap.

**1 · Substitution: `rapid_pass_through` → `shell_company_ownership`.**
The spec names `rapid_pass_through` as a typology. FinCEN publishes no
advisory on it — verified across all 194 advisories in Task 1, not assumed
— and this estate anchors every typology to a real, citable public source
(FATF was blocked, HTTP 403, measured 2026-08-24, so FinCEN carries all
four). Rather than invent an advisory or leave the fourth typology
unanchored, `shell_company_ownership` was substituted, with Dave's
approval, anchored to FIN-2017-A003.

**2 · Abstraction: FIN-2017-A003's own case is residential real estate.**
The advisory states the beneficial-ownership concealment mechanism through
a real-estate case (Geographic Targeting Orders, Form 8300, the $10,000
filing trigger). This estate models no property register, so the pattern is
extracted at the **mechanism** level and the asset class is abstracted
away: `params` carry `min_ownership_hops`, `channel: "asset_purchase"`,
`min_amount_usd`, `financing_leg` — no deeds, no property entities, no GTO
thresholds. The passage that was selected is scored with an exclusion list
that heavily penalises any passage naming the reporting regime rather than
the mechanism; the winning passage says only that a shell company is
"formed without disclosing the individuals that ultimately own or control
them."

### Where this is recorded — all three, deliberately

The Task 4 ruling required the narrowing be visible in three independent
places, so that no single deletion can erase it. Two of the three were
carried out at the time; the third and fourth were added at whole-branch
review (CT-6), where the omission was found.

1. **In the data.** `sources/screening/wave17_typologies.json`'s
   `shell_company_ownership` entry carries a required
   `abstracted_from_advisory` field stating plainly that the advisory's
   case is real estate and this estate exhibits the mechanism with the
   asset class abstracted. `validators/test_aml_typology.py::test_shell_company_ownership_honors_the_controller_ruling`
   checks it live — the cited passage contains none of "geographic
   targeting order", "gto", "form 8300", and the disclosure is present
   verbatim.
2. **In the coverage tool.** `validators/spec_coverage.py`'s
   `aml-typology-match` manifest row now carries a `divergence=` string,
   rendered under the row on its own lines as **SATISFIED WITH
   DIVERGENCE**. This is a new field on `Mapping`: the pre-existing
   `detail` string is truncated at 70 characters by `Outcome.render`, so a
   divergence written there would have been recorded and never read —
   which is precisely the shape of the failure being fixed.
3. **Here.**

`docs/HANDOFF.md` asserts that "spec_coverage records it as satisfied, per
this task's instructions — not as a gap." **That sentence was false for
fourteen tasks** and is true as of this entry: before CT-6 the
spec_coverage row said nothing at all about the divergence, so a reader
following HANDOFF's pointer arrived at a tool that was silent. The
"unregistered is invisible" failure in miniature — a claim about a
register, made without reading the register.

---

## 30 · SAR filing selection — two rejected designs before the content digest, and what floor 4's PASS line does not establish

The durable record for `generators/generate_sar_records.py`'s
`select_filed_case_ids()`. Its module docstring, its `FILING_DIGEST_SALT`
comment and the `filing_rationale` string carried in twelve loaded MongoDB
`sar_narrative` documents all used to cite an SDD `task-15-report.md`,
which is deleted when the wave closes. This is where that history lives.

### The property being protected

A SAR's existence is confidential; in many jurisdictions disclosing that
one exists is itself an offence. The front-line perspective `l1` must
therefore not be able to learn that a filing occurred — not from a field,
and not by inference from fields it legitimately holds.

### Rejected design 1 — one SAR per case (fix round 2 removed it)

The first cut filed a SAR for all 24 engineered cases. `l1`'s projection
plan names `typology_pattern_summary`, whose resolver reads the Fluree
`ex:matchesTypology` edge. With 1:1 coverage, the edge's mere EXISTENCE
proved a SAR existed. Every SAR *field* was correctly hidden and the
property was still broken.

**Fix:** SAR coverage became a deliberate proper subset — 12 of 24 cases
file, 12 do not — so `matchesTypology` no longer implies anything.

### Rejected design 2 — materiality ranking (fix round 3 removed it)

Fix round 2 chose the filing half by `case_exposure_usd`, the aggregate USD
across each case's own cited transactions. It sounded like a business rule
and was not safe: `l1`'s plan also names `alert_core_facts`, which exposes
`aml_alert.trigger`, and the trigger text states the very transaction
counts and dollar amounts the ranking used. **Measured against the loaded
estate, an `l1` reader could recover the filing decision with certainty for
20 of the 24 cases** — and the rule was stated verbatim in every SAR's own
`filing_rationale`. An edge-existence route had been closed by opening a
value-correlation one.

### The design that stands — a content digest

`select_filed_case_ids()` sorts each typology's 6 cases by
`sha256(FILING_DIGEST_SALT + ":" + case_id)` and keeps the first half. A
hash carries no relationship to its input's magnitude, timing, or any other
property, so there is nothing left to recover it from. The split stays
scoped **per typology**, exactly as fix round 2 established: a global
selection could let one typology always-file or never-file, which gates the
same inference one level up.

Verified interleaved rather than assumed — for every quantity `l1` can
extract (the transaction and shipment counts and dollar amounts embedded in
`trigger`, the case's aggregate transaction exposure, `raised_at` as an
ordinal), the filed and unfiled values overlap within each typology; no
threshold separates them.

### The salt was chosen, and that matters — say so

`FILING_DIGEST_SALT = "ccf-wave17-sar-filing"` is not the first literal
string tried. With only 6 cases per typology, a specific realisation of
"which 3 land in the top half" can coincide with an existing pattern in the
fixed case data by chance — roughly a 1-in-5 chance for a generic 2-of-6
pair under a 3-of-6 split. That happened on the first candidate: TYP-SHELL
and TYP-TBML each showed a discrete case attribute (ownership hops,
shipment count) landing entirely on one side. Several strings were tried,
each checked against every `l1`-reconstructable quantity, and the first with
no one-sided split on any of the four typologies was kept.

**This is not fix round 2's mistake repeated.** The mechanism cannot carry
a designed relationship to any case attribute whichever salt is chosen — a
hash has no such relationship by definition — so discarding an unlucky
realisation is closer to re-rolling a die than to measuring a business rule
and hoping it comes out clean.

**But it does bound what a PASS line establishes.**
`validators/aml_typology.py`'s floor 4, sub-condition 4 recomputes the same
quantities this salt was selected against. The instrument and the data were,
in part, tuned to each other. Floor 4 can still fail — its poison tests are
real (`validators/test_aml_typology.py` feeds `scan_for_sar_leakage` and
`separating_quantities` known-present inputs and requires a different answer
from the known-absent ones), and it recomputes from the loaded stores rather
than reading `select_filed_case_ids()` or any `filing_rationale`. The honest
reading of its PASS is that the property was **partly arranged rather than
wholly discovered**. Floor 4's own docstring and
`select_filed_case_ids()`'s now say so too, so this is not the only place a
reader can find it.

### `case_exposure_usd` — the field is gone, the function is kept

Whole-branch review CT-8 deleted `case_exposure_usd` from the emitted SAR
records and from the twelve Mongo `sar_narrative` documents. It was a
derived aggregate of Postgres-owned `aml_transaction.amount_usd` sitting in
a Mongo document, it had no consumer, and it survived only as a vestige of
rejected design 2 — carrying a warning label whose sole purpose was that
the field misled. `loaders/load_mongo_wave17.py` `$unset`s it, and refuses
to finish if any `sar_narrative` document still carries it, because an
upsert is `$set`-only and a removed field otherwise survives on every
already-loaded document forever.

The FUNCTION `case_exposure_usd()` is kept, uncalled, so
`FILING_DIGEST_SALT`'s comment has something concrete to point at when it
names the design that was rejected. It must not be reintroduced into the
filing decision, into a record, or into any store.

---

## 31 · `aml-typology-match` — the genuine/noise separation survives the CT-1 fix, inside `l1`'s own view

**Open data-design question, not a defect awaiting a patch.** Recorded
2026-08-25 by the scoped re-review of the final fix wave, which attacked
that wave's own fix and found the *prefix* rule dead and the *defect*
alive.

### What CT-1 fixed, and what it did not

CT-1 removed a rule that classified every alert with one string match on a
field all three perspectives receive: `trigger.split(":")[0]` was an exact
classifier for "genuine", 30 of 30, precision 1.000. Forty-two of the 120
noise alerts now carry typology-named triggers, and **best single-prefix
precision is 0.500, measured** — the prefix rule is genuinely dead.

The separation is not. From `l1`'s **own assembled view**, with no external
artifact and no threshold:

```
typology_pattern_summary.typology_id == the typology named by
                                        alert_core_facts.trigger's prefix
   OR  "within the same case" in alert_core_facts.trigger
```

**30 of 30, precision 1.000, recall 1.000.** First clause alone: 27/27.
Second clause alone: 6/6. Both fields are in `l1`'s stored projection plan;
the comparison is between two of `l1`'s own fields.

### Why each clause is perfect, mechanically

**Clause 1 is perfect BY CONSTRUCTION.** `typology_pattern_summary`
resolves the Fluree `ex:matchesTypology` edge, which is exactly the 24
primary case subjects. CT-1's own exclusion rule guarantees a
typology-named noise alert never lands on a party involved in any case of
the typology it names — so it can never land on a party carrying that
typology's edge. Agreement between the edge and the trigger prefix is
therefore possible only on a genuine alert. The safety property that makes
the false positives honest is the same property that makes them
identifiable.

**Clause 2 is a format tell.** `_shell_secondary_trigger` in
`generators/generate_aml_alerts.py` ends "…within the same case". No noise
alert can carry that phrase, because noise alerts are not built from a
case. Six TYP-SHELL intermediary alerts, six hits, nothing else.

**And each typology separates on a single number in its own trigger
text**, measured over the loaded set:

| typology | separating quantity | genuine | noise | margin |
|---|---|---|---|---|
| `shell_company_ownership` | purchase amount | min $726,635.43 | max $43,351.63 | **16.8×** |
| `trade_based` | max invoice variance | min 69.7% | max 17.0% | **4.1×** |
| `structuring` | band low edge | min $8,000 | max $2,402 | **3.3×** |
| `funnel_account` | deposit jurisdictions | min 3 | max 2 | 1.5× |

Every genuine `structuring` trigger carries the identical literal
`between $8,000-$9,900`, because Task 11's injector records the typology
params' band EDGES rather than the measured amounts of the transactions it
planted.

### Why this is a design question, not a bug

Any dataset whose ground truth is "this party exhibits the published shape"
makes gate-satisfaction equivalent to genuineness. A false positive that
satisfied the published parameters would not be a false positive — it
would be an un-injected case. So the residual is inherent to the current
construction, and no relabelling of noise triggers can remove it.

Closing it needs **hard negatives**: ordinary parties whose real activity
MEETS a published gate but is legitimate — the retail business whose cash
deposits genuinely cluster under the reporting threshold, the trader whose
invoice variance genuinely exceeds 30% for commercial reasons. That is the
only construction under which "meets the gate" stops implying "genuine".

**It trades one property against another, which is why it was not done
here.** `generators/generate_aml_transactions.py`'s anti-pattern check
currently FORBIDS exactly this for TYP-STRUCT by design: it refuses to let
any ordinary party form a structuring shape, and Task 10/11 verified that
refusal in both directions with planted fixtures. Introducing hard
negatives means deliberately weakening a gate this estate built, tested and
reviewed on purpose. Whoever takes it on should decide that trade
explicitly rather than discover it.

### What was corrected in the prose, and why it is recorded here

Two sentences written by the CT-1 fix wave asserted the residual away, and
the data refutes both:

* "there is no format tell to replace the prefix tell" — true of the 42
  relabelled records, false of the alert set (`_shell_secondary_trigger`).
* "the separation that remains is inference over two artifacts" — false;
  every separation above is available from `l1`'s assembled view alone,
  and the strongest is a comparison between two of `l1`'s own fields.

Both are corrected in `generators/generate_aml_alerts.py`'s docstring, in
place, naming what replaced them. **This is the same defect class as
#28 and as the final review's CT-4: a confident statement about the data
that the data refutes.** The sibling commit to the one that fixed CT-4
committed it again, eight hours later, in the same wave — which is the
strongest argument this file can make that a claim about data must be
MEASURED at the moment it is written, not reasoned to.

---

## 32 · Wave 4's Bausch facility extraction — one loan split into two rows, one facility with no schedule at all (found Wave 18 Task 6, 2026-08-26)

**🟠 affects downstream correctness** — `ccf_v2.facility` carries two defective
rows for the credit agreement `885590_0001193125-25-149731_d949183dex101.htm`
(a Bausch entity). Found while deriving Wave 18's `own_position` rows (Task 6)
and independently verified by the coordinator before ruling (T6-R2).

### What the filing actually contains

The agreement's real commitment schedule names exactly **two** tranches:

```
 1 row   REFINANCING TERM LOAN COMMITMENTS
11 rows  THIRD AMENDMENT REVOLVING CREDIT COMMITMENTS
```

### What Wave 4 extracted

Wave 4's facility extractor created **four** `facility` rows for this one
document, from four separate `facility_type` regex hits, each grabbing the
nearest dollar figure in the text rather than the schedule's own total:

| facility_id | facility_type | commitment_amount | `facility_type` text offset |
|---|---|---:|---:|
| `FAC-E08688` | Revolving Credit Facility | $2,500,000,000 | 2845 |
| `FAC-105FC5` | Term Loan A | $2,325,000,000 | 224132 |
| `FAC-08F1D1` | Term Loan | $2,325,000,000 | 68967 |
| `FAC-DFCB72` | Delayed Draw Term Loan | $637,650,000 | 312457 |

All four rows share **identical** `maturity_date` (offset 412529),
`effective_date` (offset 186) and `administrative_agent` (offset 524) text
offsets — one context block, four separate `facility_type` matches nearby,
each with its own (often unrelated) `commitment_amount` offset.

### Defect 1 — `FAC-105FC5` and `FAC-08F1D1` are the same real loan, extracted twice

Both carry `commitment_amount = $2,325,000,000` — exactly the total of
Schedule I's "2025 Refinancing Term Loan Commitments" (JPMorgan
$1,285,342,270.46 + cashless-roll lenders $1,039,657,729.54 =
$2,325,000,000.00 exactly). There is only **one** term-loan tranche in this
filing. "Term Loan A" and "Term Loan" are two labels the same Wave 4 regex
pass found for it, not two loans.

**Blast radius:** any product that sums `commitment_amount` (or a per-lender
share) across `FAC-105FC5` and `FAC-08F1D1` for this borrower double-counts
~$2.3B of facility size, and Wave 18's own JPMorgan share (~$1.29B) if it is
ever mistakenly attributed to both.

### Defect 2 — `FAC-DFCB72` has no commitment schedule at all

**Corrected 2026-08-26 (fix round 2).** An earlier version of this entry
claimed the phrase "Delayed Draw" does not appear anywhere in the filing.
That was true only of a case-SENSITIVE search; it was written and read as a
broader claim than that, and the broader claim is false. A case-insensitive
search finds it exactly **once**, at text offset 312457 — the same offset
the table above already cites as `FAC-DFCB72`'s `facility_type` extraction
hit:

> "...treating any Indebtedness constituting **delayed draw term loan
> commitments** then being incurred as fully drawn..."

That is a ratio-covenant clause governing how a HYPOTHETICAL delayed-draw
facility is treated in a leverage calculation — not a reference to an
established tranche, and not part of any commitment schedule. Wave 4's
`facility_type` regex matched this clause and minted a `facility` row from
it. The `commitment_amount` ($637,650,000) was then read at a SEPARATE
offset, 969473 — far outside both the schedule region (~offset
68,800–69,700) and this covenant clause — from an entirely different,
unrelated secured-debt basket:

> "...other Indebtedness in an aggregate amount... not to exceed the greater
> of (x) $637,650,000 and (y) 15% of Consolidated Net Tangible Assets..."

So `FAC-DFCB72` is not merely mis-priced: it was minted from a covenant
clause discussing a hypothetical delayed-draw facility, and given a dollar
figure scraped from a second, unrelated clause. There is no Schedule I/II
entry naming any lender, JPMorgan or otherwise, for a delayed-draw tranche
anywhere in this document. This row does not represent a real, syndicated
facility a lender can be correctly attributed to.

**Blast radius:** any product treating `FAC-DFCB72` as a real, syndicated
facility (a lender list, a covenant, an exposure) has no filing to check
its claims against.

### What Wave 18 did about it — Ruling T6-R2

**`ccf_v2.facility` was NOT touched.** Other products (covenant, exposure,
collateral) already reference these four rows, and deleting or mutating any
of them would ripple into data that is not Wave 18's to change — see
CLAUDE.md's single-writer discipline. Instead, Wave 18 excludes both
defective rows from its **own** artifacts and tables via a single named
constant, `ccf.syndicate.WAVE18_EXCLUDED_FACILITIES` (with the tiebreak
rule and reasoning recorded there), imported by every Wave 18 task that
needs it (Tasks 6, 8, 14, 16) rather than each re-deriving its own list.
`loaders/load_postgres_wave18.py`'s `load_own_positions` also actively
deletes any `own_position` row for an excluded facility on every run, so a
row loaded before this ruling cannot survive a reload.

**Wave 18's facility set is 12, not 14.**

### Who should fix the root cause

Whoever owns Wave 4's facility extraction (`generators/extract_facilities.py`
or its successor) should re-run extraction for this document with a schedule-
aware total (the same `_schedule_captions`/`_included` machinery
`generators/extract_commitment_schedules.py` already built for exactly this
kind of ambiguity) rather than a bare nearest-dollar-figure regex, and should
consider de-duplicating facility rows that share identical
maturity/effective/administrative-agent offsets — that shared-offset pattern
is a strong, cheap signal of a split extraction and may recur in other
documents this file has not checked.

---

## 33 · MongoDB `passage.provenance = "derived"` — 82 pre-existing rows carry no `passage_kind` and no `source` (OPEN, found 2026-08-26, Wave 18 Task 11)

**Found while measuring `passage.provenance` values before Ruling T11-R1**
(this task's own two `passage_kind`s were changed from `derived` to `public`
per that ruling — see the loader's docstring and the Task 11 report). The
measurement surfaced a second, older anomaly this task did not create and is
not fixing:

```
uv run python3 -c "
from ccf.config import mongo_db
db = mongo_db(write=False)
print(db['passage'].count_documents({'provenance': 'public'}))   # 37,307
print(db['passage'].count_documents({'provenance': 'derived'}))  # 82
print(db['passage'].count_documents(
    {'provenance': 'derived', 'passage_kind': None, 'source': None}))  # 82
"
```

**All 82 `derived` rows carry `passage_kind: None` and `source: None`** —
both fields absent, not merely empty. They belong to Wave 13b's KYC corpus:
`document_id` values `KYC-0001` through `KYC-0032` (32 distinct documents,
confirmed via `db.passage.distinct("document_id", {...})`), `passage_id`
values like `KYC-0001-P01`/`KYC-0001-P02`, and `alignment: "heading"` — a
value the rest of the collection does not use (`segment_passages.py`'s
vocabulary is `structure` / `definition` / `window` / `window-head` /
`window-split`; `"heading"` appears only on these 82 rows). They predate
Wave 18 entirely.

**Not this wave's to repair** — same reasoning as §21's `doc_type` gap:
this task did not write these rows, did not touch `loaders/load_kyc_documents_wave13b.py`,
and single-writer discipline says a task fixes what it owns, not every
inconsistency it happens to notice while querying a shared collection.

**Why it matters anyway.** The coordinator's Ruling T11-R1 reasoning applies
here without modification: 37,307 of 37,389 passages (all but these 82 plus
Task 11's now-corrected 12) are `public`. A consumer filtering
`provenance == "public"` — the query the ruling calls "entirely
reasonable" — silently drops exactly these 82 KYC passages, the same
invisibility failure this task was corrected for, just on data this task
does not own. Unlike Task 11's 12, these 82 also carry no `passage_kind`
and no `source`, so even a consumer NOT filtering on provenance has no
field to recover what kind of passage these are or where they came from
beyond the KYC `document_id` prefix.

**Left for whoever owns Wave 13b's KYC loader:** confirm whether `public` is
the intended provenance for filed KYC/Companies House material (Wave 13b's
own pseudonymization rule, CLAUDE.md rule 3, suggests it should carry some
provenance — these documents concern real people's PSC records,
pseudonymized at ingestion, which is a different question from whether the
STRUCTURE is `public`), and backfill `passage_kind` and `source` alongside
any provenance correction rather than fixing one field and leaving the
other two null.

---

## 34 · Wave 18 commitment schedules do not sum to `facility.commitment_amount` — for four legitimate reasons, none of them a Wave 18 defect (RECORDED, not fixed, 2026-08-25/26, Wave 18 Task 16 preflight T16-PRE)

**Why this is written down.** An earlier cut of the Wave 18 plan required a
§F floor named `shares_reconcile`: every facility's parsed syndicate shares
must sum to its recorded `ccf_v2.facility.commitment_amount`. It was
measured before it was written, and **not one of the twelve Wave 18
facilities reconciles** — best case 4.0% off (Paychex), worst 3391%. The
floor was deleted (Preflight Ruling T16-PRE) and replaced by
`validators/syndicate.py::shares_are_sourced`.

This section exists so nobody re-derives the deleted floor from first
principles, runs it, and reports the estate broken. It is not broken. The
sum is genuinely not expected to close, for four separate reasons.

### The four causes

1. **Placeholder rows the filing declines to attribute to anyone.** Bausch's
   term-loan schedule is JPMorgan `$1,285,342,270.46` plus *"Cashless Option
   Initial Lenders [on file with the Administrative Agent]"*
   `$1,039,657,729.54`. Task 2 correctly excludes the placeholder — it names
   no institution, so there is no member to attach a share to. The parsed
   sum is therefore short by **$1.04bn that the filing itself will not
   attribute**.

2. **Amendment exhibits list only *incremental* commitments.** Regis's
   exhibit carries a $5M Term A and a $10M Term B increase, not the standing
   syndicate. Summing an amendment's rows and comparing them to the whole
   facility compares two different quantities.

3. **Unreliable tranche captions.** All 17 AHR rows sit under a single
   caption although they span a revolver and a term loan.
   `ccf.syndicate.TRANCHE_TO_FACILITIES` splits them positionally, which is
   correct for attribution but means the caption cannot be trusted as a
   grouping key for a total.

4. **Wave 4 totals that are themselves wrong.** AHR's `FAC-2A2C38` carries
   `commitment_amount = $35,000,000` against $1.222bn of filed schedule
   rows. That is the class already recorded as **§32** above — one loan
   split into two rows, one facility with no schedule at all.

### The two variants that were also checked, and closed

* **Reconcile against the filing's own TOTAL line** instead of Wave 4's
  derived column. Closed: the six filings do not reliably state one.
* **The weaker "no single share exceeds its facility"**, which needs no sum
  at all. Closed: it fails too, on AHR, because cause 4 means the facility
  total is itself the mis-extraction. A floor whose failure is caused by the
  number it measures against is not measuring the data.

**So no §F floor may depend on `ccf_v2.facility.commitment_amount`, and none
may sum shares.** `validators/syndicate.py` says so in its module docstring
and `Context` carries no `share_totals` field (Ruling T16-R1) — a
populated-but-unread field holding `recorded_total` is exactly how a deleted
condition survives its deletion, and this repo has six recorded instances of
that.

### What replaced it

`shares_are_sourced` proves the property that actually matters — **no share
was invented**. For every one of the 97 `ex:SyndicateParticipation` nodes it
re-extracts the cited EX-10 filing, takes the node's `ex:sourcePassage`
offset, and requires the text there to resolve to the lender the node claims
(by canonical name equality against `ccf_v2.syndicate_member.legal_name`, or
that member's own declared filed-name variants) with the node's amount
present within 150 characters of that name — the furthest any of the 97
actually sits is 99. Unlike summation it is both true and checkable, and
unlike an in-bounds/non-empty offset check it can tell "resolves to text"
from "resolves to the RIGHT text" (the Task 11b lesson).

**The scope of "no share was invented", stated honestly (Ruling T16-R4).**
For the 94 shares resolved by canonical name equality the check is
independent of the producer — the GLEIF legal name and the filed span are
compared through a normalisation that knows nothing about which member the
loader picked. For the 3 resolved by the **variant route** it is not:
`raw_names` is `generators/resolve_syndicate_institutions.py`'s own grouping
output and `shares_are_sourced` imports `canonical_key` from that same
generator, so what is established for those three is offset integrity,
amount-at-row, and *"this span is a name the resolver assigned to this
member"* — not *"this span names this institution"*. Misattribution
**between existing members** is still caught either way, which is the
failure that actually threatens the estate. The mechanism is deliberately
unchanged: `raw_names` is per-member declared data read live from Postgres,
no name literal appears in the validator, and a filed name that matches
neither route fails loudly rather than slipping through. The per-route
counts print on every run so the variant route quietly widening would be
visible rather than absorbed.

**Not this wave's to repair.** Causes 1–3 are properties of the filings.
Cause 4 belongs to whoever owns Wave 4's facility extraction; see §32 for
the fix and the reasoning.

---

## 35 · Floor 6 turns red for an EMPTY base table, and that is deliberate (RECORDED, latent, Wave 18 Task 16 fix round 2, Ruling T16-R7)

**Read this before treating `validators/syndicate.py`'s floor 6 as a lineage
defect.**

`lineage_is_separable` derives its element population from the estate rather
than from a list (Ruling T16-R2): every base table in either Postgres schema
— ours `ccf_v2` and the peer's `colender` — plus every subject on either
ledger. 11,969 elements today. Each element's origin is decided by which
fabric **answers** its probe.

**A base table that exists and holds no rows answers on neither fabric.** It
resolves to `unresolved`, and floor 6 fails.

That is a normal estate state, not a separability defect. The next wave that
creates a table in a migration and loads it in a later task will turn floor
6 red in between, for a reason that has nothing to do with the co-lender
boundary.

### Why it is not being softened

Because an element the floor cannot see is one it can never fail on, which
is the silent-green class this whole task exists to remove. Making
`unresolved` pass would trade a loud, unrelated failure for a quiet,
relevant one. The ruling is explicit: keep it loud.

### What was done instead

The failure message now distinguishes the two shapes, using the
`local_container` / `peer_container` keys `_probe_elements` records beside
the answer:

* *"N base table(s) EXIST but hold no rows … this is an unloaded table, not
  a separability defect"* — create-then-load, or a table whose loader has
  not run.
* *"N element(s) are present on NEITHER fabric"* — the genuine case, and the
  only one worth investigating as a lineage problem.

`validators/test_syndicate.py` pins the message split: an unloaded table
must produce the first message and not the second, and an absent element the
second and not the first. Each of the two tests asserts the OTHER message is
absent, so a split that stopped discriminating would fail rather than quietly
collapse into one undifferentiated answer.

**There is deliberately no estate-wide "nothing is unresolved today" test**
(Ruling T16-R8). One was added and removed: it read `element_origin` alone,
so it could not tell the two shapes apart, and on the `absent` shape — the
genuine separability defect — its message would have told the reader it was
this benign case and pointed them here. Narrowing it would have meant
implementing floor 6's container split a second time in a test, where two
copies drift and the copy has no guard. Floor 6's own message already names
which case you have; this section is the forward-looking warning, and a
document is where that belongs rather than a test the next wave has to route
around.

**Measured 2026-08-26:** zero empty base tables across all 113 in the two
schemas, and zero subjects asserted on neither ledger. That figure is a
measurement taken on that date, not a guarantee maintained by anything — if
floor 6 is red, its own message tells you which of the two cases you have.

**If you meet it:** load the table, or drop it if it was created in error.
Do not add it to an exclusion list — the population is derived precisely so
that nothing can be quietly excluded from it.

---

## 36 · What floor 6 does NOT catch — a peer attribute value copied onto a locally-owned subject (RECORDED, no fix, Wave 18 Task 16 fix round 2)

`validators/syndicate.py::lineage_is_separable` establishes two things, and
it is worth being exact about the shape of the gap between them.

**Sub-condition 1** works at SUBJECT and TABLE granularity: every element —
every base table in either Postgres schema, every subject on either ledger —
must answer on exactly one fabric. It catches a peer node appearing on our
ledger, or a peer table appearing in our schema.

**Sub-condition 2** works at IDENTIFIER granularity: no `PPOS-…` / `PDEC-…`
may sit in one of our rows unless that row itself declares the claim remote
(`declares_remote()`).

**Neither catches a peer-sourced attribute VALUE copied onto a subject we
own, when the copy carries no peer identifier.** The subject stays
local-only, so sub-condition 1 sees a perfectly separable element;
sub-condition 2 has no identifier to find. A peer share amount, a peer TTL,
or a peer workout posture written onto one of our nodes or rows — with the
peer's id stripped — is invisible to both.

**Exactly one instance of that class is covered, and it is covered
thoroughly.** `precision_is_mixed` hunts the specific figure a peer band
conceals across every cell of the peer fabric, in every numeric
representation, with a positive control proving the scan can see. Nothing
generalises that to peer values in general, and nothing should be assumed
to.

**Why it is recorded rather than fixed.** Generalising would mean deciding
what counts as "a peer value" without a peer identifier to key on — a
similarity question over the two estates, with a false-positive rate that
would have to be reasoned about rather than asserted. That is a design
question for whoever owns the federation model, not a fix round. Written
down here so the next reader of floor 6's PASS line knows its exact reach:
**no peer node and no peer identifier is reachable through a local path**,
which is not the same claim as *no peer information is*.

---

## 37 · The Shared National Credit report changed format for the 2025 cycle — the estate's copy is CHARTS ONLY (RECORDED, not fixed, Wave 18 Task 12 / Ruling T12-R2)

`syndicated-lending-co-lender` §C names the interagency Shared National
Credit (SNC) Program annual report as the public source for "Syndicated-market
context", and `covenant-cross-reference` §C names it too. Task 12 located it
and loaded it. It is the right document, from the right period, from the
right issuer — and **it is not the document either spec's author had in
mind**, because the agencies changed what they publish.

**What we hold.** MongoDB `fibo_v2`, `document`, one row,
`doc_type="snc_annual_report"`, `document_id="shared-national-credit-report-2025"`,
12 pages, 20,555 characters, fetched from
`occ.gov/.../shared-national-credit-report-2025.pdf` on 2026-08-26. Its own
title is *"Shared National Credit (SNC) Program Attachment Document — 2025
SNC Program Charts, 1st and 3rd Quarter 2025 Reviews"*.

**What changed.** Every prior edition of this report carried a qualitative
narrative alongside the exhibits: commitment-volume commentary, the
special-mention and classified discussion, leveraged-lending observations,
the agencies' own reading of where risk had moved. For the 2025 cycle that
prose moved to a **separate press release**, and the attachment document —
the thing that still carries the report's name and its stable URL pattern —
is charts only.

**Why it was not chased.** §C asks for this document *"for market context"*,
and the charts are market context: exposure by classification, by industry,
by holder type, period over period. The decision was to take the document
the specs name, at the URL the specs' description resolves to, and record
the shortfall rather than substitute a different artifact for it.

**What a consumer will find, and will not.** Numbers, yes. Supervisory
prose, no. Anyone reaching into this document for a quotable agency judgment
about syndicated credit quality — the obvious use for a document filed under
"market context" — will find charts and page furniture, and nothing in the
row says why. That is what this entry is for. Recovering the prose means a
second fetch of the January 2026 press release; nobody has done it.

**One schema inconsistency rides along.** `_snc_document()` writes no
`passage_count` field, and every other row in the `document` collection
carries one. The SNC row has no passages by design (see the Task 12 record
in `docs/ccf_dataprep_v2.md` — §C asks for the document as context, not as
a source of span-level citations), so `0` would have been the honest value;
the field is simply absent. A consumer projecting `passage_count` across
`document` gets a missing key on exactly one row.

---

## 38 · Wave 18's agreement passages carry no embedding (RECORDED, not fixed, Wave 18 Task 17; heading corrected in fix round 1)

`syndicated-lending-co-lender` §C row *"Passage spans on agreement text"*
asks for spans, and spans are what Task 11 loaded: 12 passages across the
six Wave 18 credit agreements, `passage_kind` in
{`voting_threshold`, `assignment_provision`}, each carrying `start_offset`,
`end_offset`, `length`, `sha256` and a heading. They resolve — floor 1 in
`validators/syndicate.py` re-extracts each filing and lands on them, and
`validators/spec_coverage.py` probes them.

**They carry no `embedding` field.** Measured 2026-08-27: 37,305 of the
estate's 37,389 passages have one; these 12 are among the **84** that do not.

**They are not the only ones, and the first version of this entry said they
were.** Its heading read *"the only passages in the estate with no
embedding"* — contradicted by its own body one paragraph later, and false:
**72 of the 84 are not Wave 18's**. They are Wave 17's FinCEN advisory
passages, and they have their own entry at §42. A reader who took the
original heading at face value would conclude the rest of the corpus was
complete. It is not.

**Not a gap for this product.** `syndicated-lending-co-lender` §D runs
Resolve → Policy → Projection → Temporal Traversal → Federate → Batch
Enrich → Compose. There is no Similarity operator anywhere in it; step 6
resolves passage spans by anchor, not by vector.

**A gap for anything corpus-wide.** A similarity search over `passage`
returns nothing from any syndicated credit agreement, silently — the
absence of a field is not an error, and a vector index simply has no row to
return. (Nor from any FinCEN advisory: §42.) Any product that later wants "find me clauses like this one" across
the whole document estate needs these 12 embedded first, and will get a
plausible, complete-looking answer that omits them if it does not.

Recorded rather than fixed because embedding them is a load, and this task
writes to no store.

---

## 39 · The co-lender fabric's credentials — where they live, why the obvious rotation would silently fail, which one matters, and what else shares it (OPEN, Wave 18 Task 17; rewritten in fix round 1, blast radius added in fix round 2)

**The first version of this entry was wrong in three ways, and the middle one
was the dangerous kind.** It named the wrong file, gave a remedy that would
have looked like it worked and done nothing, and disclosed the harmless
credential while omitting the consequential one. Rewritten from a live
inspection.

### Where they live

`~/.bashrc`, exported into every shell on this machine:

| line | variable | reaches |
|---|---|---|
| `~/.bashrc:173` | `CO_LENDER_PG_PASSWORD` | the co-lender's Postgres — **`peer_position`, `peer_product_declaration`: the peer's actual position and declaration data** |
| `~/.bashrc:175` | `CO_LENDER_MONGO_URI` (password inline, `mongodb://colender:…@…:27018/…`) | the co-lender's MongoDB — **zero collections** |

**No `CO_LENDER` variable is in `.env`.** `.env` exists in the repo root and
contains **none of the `CO_LENDER_*` names**; `.env.example` ships the family
commented out with no secret. Neither password is committed — `git grep`
finds them nowhere in the tree, and nothing in the exchange bundles, the
reports or the fixtures carries either.

### But the SECRET is in `.env`, under two other names — and it is shared

That last paragraph is true of the *variable names* and was misleading about
the *value*. Measured 2026-08-27, by comparison only (**no value is printed
here, in the task report, or anywhere else — refer to these by variable name**):

| relation | verdict |
|---|---|
| `.env`'s `NEO4J_PASSWORD` vs `CO_LENDER_PG_PASSWORD` | **byte-identical** |
| `.env`'s `BLUE_IRIS_PASSWORD` vs `CO_LENDER_PG_PASSWORD` | **byte-identical** |
| the `CO_LENDER_MONGO_URI` inline password vs `CO_LENDER_PG_PASSWORD` | **a substring of it** (not equal) |

So **one string protects at least three systems**: the co-lender's Postgres,
whatever answers at the Neo4j endpoint, and Blue Iris — the last two entirely
unrelated to this project, and Blue Iris not a database at all. And the
co-lender's MongoDB password is not independent of it either: it is a
substring, so learning the Postgres one hands you the Mongo one.

**This is the fact that decides how the rotation is done**, and it is why the
entry is being corrected rather than left. Rotating `CO_LENDER_PG_PASSWORD`
alone has exactly two outcomes, both bad:

- change the value at every store that accepts it, and **Neo4j and Blue Iris
  break**, because nothing in this repository knows they were sharing it; or
- change it only at the co-lender's Postgres, and the retired string **keeps
  protecting Neo4j and Blue Iris** — the rotation removes it from the one
  place it was scoped to and leaves it live in two places nobody was thinking
  about.

Neither is a rotation. The decision has to be made across all four variables
at once, and the Mongo URI has to be re-derived rather than assumed
unaffected.

Nothing about Neo4j's own status changes this: it was dropped from the v2
estate on 2026-08-16 (`docs/ccf_dataprep_v2.md`), so `NEO4J_PASSWORD` may
well be vestigial here — but a credential is not retired by a project
deciding it no longer queries the endpoint, and this repository is not the
authority on what else uses that string.

### Why "rotate and update `.env`" would look done and not be

`ccf/config.py:30` calls `load_dotenv()`. **`python-dotenv`'s `override`
parameter defaults to `False`** (verified against the installed version's own
signature, 2026-08-27), so a variable already present in the environment
**wins over `.env`**. Since `~/.bashrc` exports both of these before any
shell runs anything, writing a new password into `.env` would change nothing:
the stale export would keep winning, every store call would keep succeeding
with the old credential, and the rotation would appear complete.

**So the rotation must edit `~/.bashrc` itself** (or the environment be
cleared, or `load_dotenv(override=True)` be adopted — a change with its own
blast radius, not proposed here). Editing `.env` alone is not a partial fix;
it is no fix with the appearance of one.

### Which one matters

The entry as first written disclosed the **Mongo** credential, because that
is the one that was printed into a session transcript on 2026-08-27 while
Task 17 was determining whether the peer provisions a document store. It
does not. `bofa_syndicated` holds **zero collections**, so that credential
currently unlocks nothing.

`CO_LENDER_PG_PASSWORD` is the one with a blast radius: it reaches the
peer's live position data, the fabric every §F federation condition is
evaluated against, on a Postgres instance that also hosts `parkavedb`.
Separated only by database and role. It was not printed anywhere, and it is
disclosed here because an entry that records the harmless credential and not
the consequential one misdirects exactly the reader it is written for.

Both hosts are shared: the peer's MongoDB is on the same host as the
estate's, which also runs an unrelated 5.5M-document database, and the
`authSource=bofa_syndicated` scoping is the only thing narrowing that
account.

### Action — Dave's call, deliberately not taken

**Nothing was rotated.** These credentials reach a provisioned fabric that
other work depends on, and rotating them is a decision about live
infrastructure, not a validator fix. Recorded accurately so the decision can
be made on real information:

1. **decide across all four variables at once** — `CO_LENDER_PG_PASSWORD`,
   `NEO4J_PASSWORD`, `BLUE_IRIS_PASSWORD` and the password inside
   `CO_LENDER_MONGO_URI` — because they are one shared string plus a
   substring of it, and treating any one of them in isolation produces one of
   the two bad outcomes above;
2. rotate `colender`'s Postgres credential first — it is the consequential
   one — and **edit `~/.bashrc:173` and `:175`**, not `.env`, or the change
   will not take. `.env`'s `NEO4J_PASSWORD` / `BLUE_IRIS_PASSWORD` are
   separate edits for their own systems, and out of this repository's hands;
3. re-run `uv run validators/syndicate.py` and `uv run
   validators/test_fabric_isolation.py` afterwards — both reach the peer
   fabric and will fail loudly on a stale credential, which is the check that
   the rotation actually took.

## 40 · The band peer's citation span is shorter than the exact peers' — a digit-length side channel (RECORDED, not fixed, Wave 18 Task 14, deferred minor)

`peer_position` holds one counterparty that discloses at BAND granularity
(`band_low` / `band_high`, no `share_usd`) while another discloses exactly.
That asymmetry is the point of §F's *"≥ 1 peer disclosing at band
granularity while another discloses exactly"*, and
`validators/syndicate.py::precision_is_mixed` proves it holds and that the
concealed figure appears nowhere on the peer fabric in any numeric
representation.

**What still leaks is the figure's SHAPE, not its value.** The banded row's
source-passage span is 14 characters where the exact rows' are 21. A span
length is a function of how many characters the underlying figure occupies,
so an observer comparing citation lengths across rows learns roughly how
many digits the band is concealing — a side channel in the metadata, not in
the data.

**Why it is recorded rather than fixed.** Padding the span, or normalising
every citation to a fixed width, would make the offsets stop resolving
against the filed text, which is the property floor 1 exists to prove. The
honest fix is a different citation scheme for banded rows, which is a design
decision about what a band's provenance means and belongs to whoever owns
the disclosure model. See also Ruling T14-R1: the concealed figure is
*public on our side* (our own ledger holds the peer's commitment from the
filed schedule), so this side channel is not the difference between secret
and known — it is a demonstration flaw in what the peer's own disclosure
reveals about itself.

---

## 41 · The peer's three product declarations are hand-picked literals, and a fourth would silently become a second contrast (RECORDED, not fixed, Wave 18 Task 15, deferred minor)

`generators/generate_peer_positions.py`'s `DECLARATION_SPECS` fixes each
declaration's `declared_ttl_seconds` and `declared_latency_ms` as literal
values chosen to make three §F rows demonstrable at once:

- one declaration OVER the federation latency bound, with another under it
  (§F *"≥ 1 federated request that times out"*);
- one with `attestation IS NULL`, with attested contrasts (§F *"≥ 1
  unattested remote claim"*);
- one whose TTL is shorter than the local composite would otherwise carry
  (§F *"≥ 1 remote product with a shorter TTL"*).

`validators/syndicate.py::federation_bounds_bind` recomputes all three from
the stored values rather than reading a flag, so the conditions are proven,
not asserted.

**The intent is written down; nothing enforces it.** Each spec carries a
`note`, and the third one is explicit — *"Fast latency on purpose — it must
not also be the timeout contrast, or the three floors stop being
independently demonstrated."* That is the right instruction to the next
author, and it is prose. The only assertion the generator makes about a
declaration is `assert (lei, facility_id) in held`: that the peer really
exposes the product it declares. Nothing checks that exactly one row is over
the latency bound, exactly one is unattested, or exactly one carries a
short TTL.

**So a fourth declaration can quietly become a second contrast.** The floor
would still pass — it asks for at least one of each *with* a contrast — but
the pair it reports would not be the pair the design chose, and which
declaration is "the example" would depend on row order. Recorded because the
failure is not a red suite; it is a demonstration that still passes while
having stopped demonstrating the thing it was built to show.

Recorded rather than fixed because deciding whether the design wants
*exactly one* or *at least one* of each contrast is a design question, and
the answer changes what the generator should enforce.

---

## 42 · 72 Wave 17 FinCEN-advisory passages carry no embedding either (RECORDED, not fixed, found 2026-08-27, Wave 18 Task 17 fix round 1)

Found while correcting §38's false exclusivity claim, and a **different
population** from both §33 and §38.

**Measured 2026-08-27**, `fibo_v2.passage`:

| | count |
|---|---|
| passages total | 37,389 |
| with an `embedding` field | 37,305 |
| **without** | **84** |
| — of those, Wave 18 agreement passages (§38) | 12 |
| — **of those, Wave 17 FinCEN-advisory passages** | **72** |

The 72 span **four** documents — `fincen-advisory-fin-2009-a003`,
`fincen-advisory-fin-2010-a001`, `fincen-advisory-fin-2014-a005`,
`fincen-advisory-fin-2017-a003` — carry `provenance="public"`, no
`passage_kind`, and the advisory-specific fields `advisory_number` and
`typology`. Every other passage in the collection that lacks an embedding is
one of Wave 18's 12.

**Not §33.** That entry records 82 rows with `provenance="derived"` carrying
no `passage_kind` and no `source`. These 72 are `provenance="public"` and
**do** carry the fields their loader was supposed to write. The two
populations do not overlap, and §33 does not cover these.

**What it costs.** `aml-typology-match` §C assigns *"Passage spans on
advisories and typology reports"* to MongoDB as `L`, and
`validators/spec_coverage.py` probes exactly these 72 rows — that probe
passes, because the spans are there and resolve. What is absent is the
vector: any similarity search over the advisory corpus returns nothing, and
returns it silently. `aml-typology-match`'s own §D anchors typologies to
advisory passages **by stored anchor**, not by similarity, so this is not a
gap for that product either — it is a gap for anything that later assumes
the passage corpus is uniformly embeddable.

**Not repaired here.** These rows belong to whoever owns the advisory
corpus; Wave 18 Task 17 writes to no store. Recorded with the measurement
and its date so the next person does not rediscover it as a surprise, and so
that §38's corrected heading has somewhere to point.

---

## 43 · `extract_agent` drops a leading "The" from an institution name — LATENT, and measured to be latent (RECORDED, not fixed, Wave 18 Task 1 deferred minor, re-triaged in Task 17 fix round 1)

`ccf/syndicate.py`'s administrative-agent extraction walks left from the
matched agent phrase and stops on a connector token. A name beginning with
the definite article loses it: **"The Bank of New York Mellon" would be
stored as "Bank of New York Mellon"**. That was a deliberate walk trade-off
at Task 1, with a comment requested and no restructure.

It was first triaged as a style observation. It is not — it is a behavioural
property of the extractor that changes a **stored string**, and an exact-name
join against a registry that spells the article would miss.

**Measured 2026-08-27, and it has not fired.** No `AdministrativeAgent` node
in the loaded estate carries a label beginning "The" — the four are JPMorgan
Chase Bank NA, Bank Of America NA, PNC Bank NA and TCW Asset Management
Company LLC. And the three syndicate members whose names *do* carry the
article keep it in at least one stored field: `THE BANK OF NOVA SCOTIA` /
`["The Bank of Nova Scotia"]`, `The Huntington National Bank` /
`["THE HUNTINGTON NATIONAL BANK"]`, `THE TORONTO-DOMINION BANK` /
`["The Toronto-Dominion Bank"]` — `syndicate_member` is populated by lender
resolution (Task 3), not by `extract_agent`, so it is not on this path at
all.

**So the record is: a real truncation, on a code path that no document in the
present 65-document corpus exercises.** It is written down because the next
wave to add credit agreements is exactly who would trip it, and it would trip
silently — a truncated agent name is a perfectly well-formed string, it loads
cleanly, and the only symptom is a join that quietly returns nothing. The
measurement above is a **fact about a date**, not a guarantee maintained by
anything: no test asserts that no agent name begins with an article.

---

## 44 · Two partition tests plant a real value in the live shared estate and restore it in a `finally` — a killed process between commit and restore leaves a real-looking `LEAK INWARD` (RECORDED, no fix, whole-branch review fix wave)

`validators/test_syndicate.py::test_a_peer_id_planted_in_an_ORDINARY_debt_row_makes_the_arm_go_red`
and `::test_arm1_says_no_when_a_peer_DECLARED_VALUE_rides_in_with_the_id`
each need `validators/partition.py::check_wave18()` to see their planted
value — and `check_wave18()` opens its own connection, so an uncommitted
transaction is invisible to it. Both tests therefore `UPDATE` a real
`ccf_v2.context_debt.reason` value, `conn.commit()` it, run the check, assert
it goes RED, and restore the original `reason` in a `finally` block.

**This is not a bug in the tests — it is required by what they test.** A
version that planted inside an uncommitted transaction (or in a temp table,
or via a rollback) would never be visible to `check_wave18()`'s own
connection, and the test would stop testing anything — silently, the same
failure class CLAUDE.md and this file warn against elsewhere. Do not convert
these to a rollback.

**The hazard this leaves.** Between the `commit()` and the `finally`'s
restoring `UPDATE`, the row's `reason` genuinely carries the planted marker
— `"<original> [PLANTED <PDEC-… id>]"` for the first test, `"<original>
declared ttl <value>"` for the second. If the test process is killed in that
window (`kill -9`, an OOM, a CI runner cancelled mid-run), the `finally`
never executes and the marker is left in the live estate.

**The exact symptom a confused reader would see.** `validators/partition.py`
reports a real `LEAK INWARD` failure on `"no peer element in our stores"` on
every subsequent run — indistinguishable, by the check's own output, from an
actual loader defect writing peer data into `ccf_v2.context_debt`. Nothing in
the row or the failure message marks it as planted-and-orphaned rather than
genuine.

**Recovery, one line.** Re-run `loaders/load_postgres_wave18.py` (idempotent
per CLAUDE.md's loader discipline, and the owner of `ccf_v2.context_debt`'s
Wave 18 rows) to overwrite the row back to its generated value — or, faster,
manually strip the `" [PLANTED …]"` / `" declared ttl …"` suffix the marker
format above names, from the `reason` column of the `context_debt` row it
appears on.

This repo is a teaching artifact: the pattern (plant into the live estate,
commit, assert, restore in `finally`) is worth copying elsewhere in this
file's spirit of proving a check can fail — but not without knowing this is
its cost. Recorded here rather than fixed because the fix that would remove
the hazard (a rollback) is the one change that would break what the tests
prove.

---

## 45 · EUR-Lex is blocked outright — every request returns HTTP 202 with a zero-byte body (RECORDED, not fixed, 2026-08-27, Wave 19 Task 2)

`covenant-cross-reference`'s natural first source for CRR Articles 392–403
would be EUR-Lex, the EU's own legislation portal. It does not serve this
project anything.

**Measured 2026-08-27.** EUR-Lex returns `HTTP 202` with a **zero-byte body**
on every request — including a plain fetch of its own homepage, not just the
CRR pages — across three different `User-Agent` strings and with a cookie
jar carried between requests (in case the 202 was a session/consent
redirect that a cookie would clear). None of that changed the result.
`publications.europa.eu`'s cellar content-negotiation endpoint, sometimes
usable as a EUR-Lex bypass, returns `HTTP 400` instead.

**The substitute, and why it is better, not just available.**
`legislation.gov.uk` carries the CRR as **assimilated UK law**, and unlike
EUR-Lex it exposes **point-in-time versions by URL** — the pattern
`https://www.legislation.gov.uk/eur/2013/575/article/{article}/{date}`
returns the article's text as it stood on that date. That is exactly what a
bitemporal regime-version condition needs and EUR-Lex's own interface does
not offer as directly. Wave 19 Task 2 fetched CRR Articles 392–403 at two
in-force dates (2020-12-31, 2021-12-31) plus the 2022-01-01 omission date
this way; see §46 for the trap that fetch walked into and avoided.

**Not pursued further.** No other EU host was substituted for EUR-Lex
specifically — legislation.gov.uk's UK implementation of the same articles
was judged sufficient for this product, and re-trying EUR-Lex was not worth
the time against a source that fails on its own homepage.

---

## 46 · The "omitted" string trap — legislation.gov.uk's amendment annotation appears on in-force versions too (RECORDED, avoided, 2026-08-27, Wave 19 Task 2)

The UK moved the large-exposures articles (CRR 392–403) out of assimilated
law on 2022-01-01 via SI 2021/1078. legislation.gov.uk marks that with an
annotation reading **"Arts. 392-403 omitted (1.1.2022)"** — but that
annotation is **present on the page for every date**, including the
still-in-force 2020-12-31 and 2021-12-31 versions, because
legislation.gov.uk shows the full amendment history on every point-in-time
render, not just the one where the omission takes effect.

**The trap.** A guard written as `if "omitted" in html:` — the obvious first
instinct for detecting "this article no longer applies" — matches every
date fetched, in-force or not, and discriminates nothing. It would report
every version of CRR 392–403 as omitted, including the two that are not.

**What was fetched and asserted instead.** `generators/fetch_regime_text.py`
asserts on the **operative sentence itself** — `"shall not incur an
exposure"`, the actual prohibition text — present on the 2020-12-31 and
2021-12-31 fetches, absent from the 2022-01-01 fetch. The literal string
`"omitted"` was checked too, purely as a control to prove the trap is real:
it is present on **both** the in-force and the omitted versions, confirming
that string alone can never be the discriminator.

**Where this generalizes.** Any future point-in-time fetch against
legislation.gov.uk (or any consolidated-legislation site that renders
amendment history inline rather than gating it by date) should assert on
the substantive text a provision is claimed to carry, never on an
annotation string that describes the provision's history — the annotation
does not respect the same date boundary the substance does.

---

## 47 · The capital units defect — `bank_capital`/`member_call_report` were in thousands, `ccf_v2.facility` is in dollars, and a ratio check could never see it (REPAIRED, 2026-08-27, Wave 19 Task 1)

FDIC BankFind reports Call Report capital and asset figures **in thousands
of dollars**; `ccf_v2.facility.commitment_amount` and every other exposure
figure in this estate are in **whole dollars**. Neither `bank_capital` nor
`member_call_report` recorded which unit its numbers were in — a plain
`NUMERIC` column, no unit annotation, no comment.

**Why the pre-existing CET1 ratio check never caught it.** The estate's
CET1 check computes `tier1_capital / risk_weighted_assets`. **A ratio is
unit-invariant** — dividing two thousands-denominated figures by each other
produces the identical result as dividing two dollar-denominated figures,
so a thousandfold unit error is mathematically invisible to any check that
only ever divides one column in the table by another column in the same
table. The check had been passing since the data was loaded, and would
keep passing under a further thousandfold error in either direction.

**The repair (Task 1).** Both tables gained a `unit TEXT NOT NULL DEFAULT
'USD_THOUSANDS'` column (added via idempotent `ALTER TABLE ... ADD COLUMN
IF NOT EXISTS`, with a `COMMENT ON COLUMN` recording why it exists), plus a
**magnitude floor** — `assert_capital_magnitudes()` in
`loaders/load_wave19_postgres.py` — that converts to dollars using the
recorded unit and asserts every institution's total assets clear **$10bn**,
with the reporting bank additionally bounded to a $1tn–$10tn band. Unlike
the ratio check, an absolute-magnitude floor **does** discriminate a unit
error: a thousandfold miscalculation would put every institution's assets
three orders of magnitude below the floor, and the floor's own test suite
(`validators/test_capital_units.py`) proves this with a stub-cursor
negative control that feeds the assertion a fabricated thousandfold error
and confirms it raises, alongside a positive control confirming the real
population passes.

**Measured population.** 28 rows across 16 distinct institutions —
`bank_capital` holds 12 quarterly rows for the reporting bank (RSSD
852218), `member_call_report` holds 16 peer institutions with 852218 counted
once among them (not 12 + 16 = 28 rows *and* 17 institutions, which
double-counts the reporting bank; see `docs/wave19-design.md` for the
correction trail). All 28 rows now carry `unit='USD_THOUSANDS'` and clear
the $10bn floor.

---

## 48 · The corpus-wide embedding gap is ~170x larger than §38/§42 recorded (CORRECTS §38 AND §42, measured 2026-08-27, Wave 19 Task 4)

§38 and §42 record **84** passages with no embedding, discovered via
`{'embedding': {'$exists': False}}`. That query is real but incomplete — it
sees only passages where the field is **absent**, not passages where the
field is **present and explicitly `null`**.

**Measured 2026-08-27**, `fibo_v2.passage` (37,865 passages total, after
Wave 19's own loads):

| | count |
|---|---|
| passages total | 37,865 |
| `embedding` field absent | **84** (unchanged — this is the §38/§42 population) |
| `embedding` explicitly `null` | **14,205** (recorded nowhere until now) |
| **no usable vector, either way** | **14,289 (37.7%)** |
| with a usable vector | 23,576 (62.3%) |

**The query trap, and why it hid this for two waves.** In pymongo,
`{'embedding': None}` matches **both** a missing field and a field whose
value is `null` — so a query intended to find "explicitly null" rows
actually returns the union of both populations (14,289), and a query
intended to find "missing" rows via `$exists: False` sees only the smaller
one (84). Neither query alone tells you the other exists. The correct test
for "does this passage have a usable vector" is:

```python
db.passage.count_documents({'embedding': {'$type': 'array', '$ne': []}})
```

which is type- and shape-aware rather than presence-aware, and is what
produced the 23,576 figure above.

**Not Wave 19's doing.** All 476 passages Wave 19 itself loaded (464 CRR/Reg
O/PRA passages in Task 4, 12 methodology passages in Task 10) carry a
usable vector — verified directly, not inferred from the aggregate. The
14,205 null-but-not-absent rows predate this wave and were already in the
corpus §38 and §42 measured against; this wave's contribution was finding
the query defect that had been hiding them, not creating them.

**Ownership.** This belongs to whoever owns the affected corpora (§33, §38,
§42 all touch pieces of it), not to `large-exposure-rwa-concentration` or
any Wave 19 product — no §F condition in this wave's spec depends on
corpus-wide similarity search. Recorded here because it was found doing
Wave 19's own embedding verification and the gap is materially different
from what was on record.

---

## 49 · Citations by cross-reference — a resolvable, topically-adjacent citation is not the same as a citation that supports the claim (RECORDED, both instances fixed, 2026-08-27, Wave 19 Tasks 9 and 10)

Twice in one wave, a passage citation resolved to a real, on-topic
provision and still did not support the sentence it was attached to,
because the regulation states its limit **by cross-reference** and the
natural-looking citation names the provision that *invokes* the rule rather
than the one that *states* it.

**Instance 1 (Task 9).** The PRA Large Exposures Part's own 25% limit
language sits at **LE 2.3**, which is a notification-duty passage, not a
prohibition — across the entire PRA corpus fetched for this wave, **zero**
passages contain the strings `"must not incur"` or `"shall not incur"`; the
PRA Part contains no prohibition text at all. The actual limit is
**Article 395(1) of the CRR**, which **LE 2.4** applies by reference: "must
exclude from the limit in Article 395(1) of the CRR." The PRA regime
version originally cited LE 2.3 as its limit source; it was wrong, because
LE 2.3 asserts a reporting duty, not the limit itself.

**Instance 2 (Task 10).** Regulation O's §215.4(c) narrowing limb reads
"exceeds the lending limit... specified in §215.2(i)" — it names the limit
by cross-reference and carries none of the figures (`15 percent`, `10
percent`, `12 U.S.C. 84`) the citing sentence attributed to it. Those
figures live in §215.2(i) itself.

**The test that catches this, and the one that does not.** "Does the cited
id resolve" is not sufficient — both citations above resolved cleanly to
real, correctly-anchored passages. The test that catches it is **"does the
cited text contain the figure this sentence attributes to it"** — checking
the passage's own stored text for the specific number or phrase the citing
claim depends on, not merely confirming the reference is well-formed.

**The fix applied both times: cite both provisions, not one in place of the
other.** The PRA regime version now cites **both** Article 395(1) (the
provision that states the 25% limit) and LE 2.4 (the instrument that
applies it in the UK regime); Regulation O's narrowing limb now cites
**both** §215.4(c) (the applying clause, asserting no figure of its own)
and §215.2(i) (which carries the actual percentages and dollar reference).
Task 10 additionally made this permanent: `_verify_reg_o_citations` in
`loaders/load_regime_mongo.py` now **raises** on any future citation whose
target text does not contain the figure its sentence claims, converting a
one-time finding into a standing guard against the same defect class
recurring a third time.

---

## 50 · Fluree index-generation bloat — 46 GB of superseded generations behind 87,162 triples (RECORDED, not acted on, measured 2026-08-27, B1 Task 10)

`/data/fluree/fibo-v2` is **47 GB on disk** holding **87,162 triples**. It
decomposes as:

| Path | Size | Files |
|---|---|---|
| `main/commit/` | 27 MB | 4,468 (one per `t` — the actual append-only history) |
| `main/index/` | **46 GB** | **27,034** |
| `@shared/dicts/` | 1.9 GB | — |

**Cause.** The config default `reindex_min_bytes = 100` — documented as
"bytes of novelty before a background reindex (default ≈ every commit)" —
means nearly every commit triggers a full new index generation, and
superseded generations are never collected. `index/garbage/*.json` records
exactly which objects are dead, so the information needed to reclaim the
space already exists; nothing consumes it.

**What one current index actually costs.** A single current index generation
is **47 MB across 18 files** and takes **1.5 seconds** to build. Querying
against it rather than replaying commits takes queries from **354 ms to
644 µs — a 550× speedup**. The bloat is the accumulated history of building
that index roughly 4,468 times over, not the index itself.

**Growth rate.** Roughly **33 MB per commit**, indefinitely — this is not a
one-time cost, it compounds with every future load.

**Not acted on.** Reclaiming the superseded generations touches the
authoritative ledger's on-disk files directly, outside any documented
Fluree operation this estate has verified. That is the user's call, not a
default action.

---

## 51 · As-of queries over Fluree HTTP silently return the wrong answer — the `t` parameter is ignored, not rejected (RECORDED, measured 2026-08-27, B1 Task 10)

On Fluree 4.1.4 and 4.1.6: `POST /v1/fluree/history` returns **404** — an
as-of history query has no HTTP path at all. Separately, and more
dangerously, the `t` parameter on a JSON-LD query is **silently ignored**: a
query issued at `t=100` against a live server returns the **full current
graph — all 87,162 triples** — with no error, no warning, and no field
indicating the requested `t` was not honored.

**The silent-ignore is the dangerous half.** A 404 fails loudly and cannot be
mistaken for success. The ignored parameter returns a plausible-looking
number and looks like a correct as-of answer unless the reader independently
knows what the true count at that `t` should be. Any claim anywhere in this
estate that as-of reconstruction is queryable over Fluree's HTTP API is
**false** and would have looked verified to a reader who only checked that
the request returned 200.

**What does work.** The CLI's `fluree history <entity> --from N --to M`
performs a real as-of query and returns the correct historical state.

**`validators/bitemporal.py` is consistent with this reality already** — it
records `t` as, in its own words, "an exact block reference, not a timestamp
query," and does not attempt an HTTP as-of query. No repair is needed there;
this entry exists so the HTTP behavior itself is on record before someone
else assumes otherwise.

---

## 52 · Two operator traps in the restore path — a correct system reporting a misleading reason (RECORDED, both fixed, 2026-08-27/28, B1 Task 10)

Both instances share a shape: the restore step itself is right, but the
*next* tool disagrees about what "right" looks like, and the resulting error
message points at the wrong layer.

**(a) Nothing starts a Fluree server after restore.** `restore_fluree.sh`
imports with `--direct`, which writes ledger storage serverless — correct,
and the only mode that makes sense mid-restore. `verify_install.py`,
however, speaks HTTP. A perfect, byte-correct restore therefore verified as
**unreachable / exit 2**, which reads as "the restore failed" when the
restore had, in fact, succeeded — the verifier just hadn't been told a
server needs to be started first. `restore_all.sh` now probes for a running
Fluree server after the Fluree step and says so explicitly, rather than
letting the verifier's exit code carry a misdiagnosis forward.

**(b) An environment variable name mismatch.** `restore_neo4j.sh` read
`NEO4J_PASSWORD`; `verify_install.py` read `CCF_NEO4J_PASSWORD`. Set one and
not the other, and the restore step succeeds while the verifier reports an
auth failure that looks like a Neo4j problem rather than a naming
inconsistency between two scripts in the same pipeline. Both names are now
accepted by both scripts.

**Why this is worth recording as one entry rather than two bug fixes.**
Neither is a data defect. Both are the same failure mode this project keeps
finding elsewhere: a component behaves correctly and reports a symptom that
sends the reader looking in the wrong place. The fix in both cases was
making the calling script aware of the other script's assumptions, not
changing what either script fundamentally does.

## 53 · A validator population that grows with the estate — corporate-family-tree's attribute row went permanently red as later waves loaded their own LEIs (REPAIRED, measured 2026-08-28)

`spec_coverage.py`'s `unresolved_graph_leis` backs `corporate-family-tree`
§C's "Entity attributes for traversal results". It asks whether every entity
a family-tree traversal can return resolves to attributes in Postgres, and
it is deliberately inverted: it reports the SHORTFALL, because a plain count
of resolvable entities passed this row at 50 of 155 for twelve waves (§19.3
territory).

That inversion was right. The **denominator** was not. The probe drew its
population from every `ex:lei` node in the ledger, which was the same set as
"the family tree" when it was written and stopped being so the moment other
products started loading LEI-bearing entities of their own.

Measured 2026-08-28 — 434 LEI-bearing nodes, 136 of them on any family edge:

| Outside the family tree | Count | Resolves from |
|---|---|---|
| Wave 17 `SYN-AML-` parties | 201 | `ccf_v2.aml_party` |
| Wave 18 syndicate members | 39 | `ccf_v2.syndicate_member` |
| Registry companies | 37 | `ccf_v2.registry_company` |
| Carry `legal_entity` attributes, no family edge | 19 | `ccf_v2.legal_entity` |
| **Resolve from no Postgres table at all** | **2** | **nothing — see below** |

The row read `ZERO — 279 unresolved` while **every entity the family tree
can actually reach resolved**. Each of the first three groups is written by
its own single writer, exactly as the partition requires; counting them
against corporate-family-tree was asking one product's gate to police
another product's population.

**Fixed** by deriving the population from the four family predicates
(`owns`, `controls`, `hasGlobalUltimateParent`, `hasDomesticUltimateParent`)
rather than from `ex:lei` membership. 136 entities, 0 unresolved, row green.

**Narrowing a population is the dangerous half of this fix**, so note where
the vacuity risk moved. `_all_resolve` returns 1 for an empty input. That was
previously covered by `conditions.py`'s 500-**entity** floor; the population
is now built from **edges**, so the guard is now its "ownership graph edges
(all predicates) >= 500" check instead. An estate that kept every entity and
lost every ownership edge would empty the set and green the row, and only
the edge floor refuses to let that happen. `test_family_tree_probes.py`
carries three arms that fail if the population is reverted.

**A prose defect travelled with it, and misled a reader.** The mapping's own
explanatory text said the probe "is 0 only while nothing is unresolved" —
the exact opposite of what the code and its docstring have always done. A
downstream reviewer read that sentence against a red run and reported the
assertion as inverted; it never was. The red was real, for a different
reason. Corrected in place, with the correction noted inline so the same
misreading is not re-derived.

### Two LEIs that resolve from nowhere (RECORDED, not fixed)

`5493000FN178SW540N88` and `549300LFK257DF2RVN05` carry `ex:lei` in the
ledger and appear in **no** Postgres table with a `lei` column. They are not
family-tree entities, so they are not this row's gap and were deliberately
not absorbed into the fix. Whoever loaded them owns the follow-up; recorded
here so the number is a record and not a count.

## 54 · "Entities carrying a real LEI" counted neither entities nor real LEIs (REPAIRED, measured 2026-08-28)

Found while fixing §53, in the same product, and it is the same mistake seen
from the other side: §53 was a population that grew past its question, this
is a **measure that never matched its own name**.

`conditions.py` floors `corporate-family-tree` at 50 *entities carrying a
real LEI*. It measured:

```sparql
SELECT (COUNT(?s) AS ?n) FROM <ledger> WHERE { ?s ex:lei ?l }
```

Two words in the check's name are load-bearing and neither was honoured.

**REAL.** The estate's synthetic identifiers use the `SYN-` prefix, settled
2026-08-23, *specifically* so they can never be confused with the
20-character GLEIF form. Nothing checked. Wave 17 loaded 201 `SYN-AML-`
parties carrying `ex:lei`, and this number inflated by 201 the day AML
shipped.

**ENTITIES.** `COUNT(?s)` counts *bindings*. The live ledger returns **449
bindings for 434 distinct values** — some nodes carry more than one
`ex:lei`. A duplicate is not a second entity.

Measured 2026-08-28: **reported 449, real-LEI population 233.**

**It passed before and it passes after**, because the floor is 50 and both
numbers clear it comfortably. That is the whole reason it was worth fixing
rather than noting: nothing was ever going to reveal it, and the figure is
load-bearing the moment anyone reads it as evidence of public-anchor
coverage — which is exactly what a reader looking for "how many real
companies are in this estate?" would do.

**Fixed** with `count_real_leis()`, a pure function over an iterable of
identifier strings: distinct values matching `[A-Z0-9]{20}` exactly. Five
arms in `test_family_tree_probes.py`, including a malformed-input arm that
fails any implementation which merely excludes the literal prefix `SYN-`,
and a live arm asserting the ledger contains **both** kinds so the exclusion
is shown to discriminate rather than to be vacuous.

**The general shape, since this is now the third instance in the estate.**
A check's name is a claim about a QUANTITY — an adjective and a noun. Both
can drift from the query underneath while the number stays plausible and the
floor stays cleared. `≥ N` gates are especially prone to it: a floor set low
enough to be safe is also low enough to absorb a measure counting the wrong
thing entirely.

## 55 · `counterparty-reference-snapshot` migrated to spec-standard-v0-3 — §C collapsed 10 rows to 4, and the manifest crash hid two thirds of the catalog (REPAIRED, measured 2026-08-28)

The vault re-authored this spec — it is **the only product spec on
`spec-standard-v0-3`**; the other twenty remain on the Q019 form. §C went
from 10 rows to 4. `spec_coverage.py`'s manifest still carried 10 mappings
and raised on the first.

**The blast radius was the real defect.** The sweep runs products
alphabetically and the raise aborts the run, so one stale mapping on
`counterparty-` hid **every product from `covenant-` onward**. The estate
looked broken and was not; 8 of the 9 mapped manifests were clean the whole
time, discoverable only by running each product singly.

### The four dropped elements — where each actually went

None was waived for convenience. The spec states its own scope boundary:
**"identity only — no exposure, no grade, no relationship."**

| Element | Disposition | Basis |
|---|---|---|
| Internal obligor risk grade | out of scope | the spec's own sentence, "no grade" |
| Coverage RM assignment | out of scope | same sentence, "no relationship" |
| CIK | reassigned | named by 6 other specs; still asserted by the surviving crosswalk probe |
| SIC code | reassigned | `credit-memo-context`, `obligor-financial-spread` |

`ccf_v2.coverage_assignment` and the CIK/SIC columns are untouched — the
elements moved in the *catalog*, not in the estate.

### The risk-grade measurement, preserved because the row that carried it is gone

This was recorded in the old mapping and would have been deleted with it.
The element now belongs to `rating-and-spread-migration`; **the gap is still
real and still ours**:

> §C assigned it to Postgres as `E` — an attribute OF THE OBLIGOR. No
> obligor-level grade column exists anywhere in the schema. The nearest
> thing, `facility.internal_risk_rating`, is a different quantity: it grades
> the FACILITY. It cannot be read as the obligor's, and not merely because
> the grain is wrong — 57 rated facilities cover only 22 distinct borrowers
> of the 50 anchors, and at least five borrowers carry **two or three
> different ratings** across their own facilities, one of them three. So no
> aggregation recovers it either: there is no single value to pick, and
> picking one would invent the answer. **28 of 50 anchor obligors have no
> credit grade in any form.**

### What the rewrite EXPOSED — a gap the old manifest was structurally unable to see

v0.3 added a row the Q019 form did not have: **"Internal client identity for
no-LEI entities."** Measured 2026-08-28, the estate holds **zero** such
entities — `legal_entity` has 0 rows with a null `lei`, and `crosswalk` has
0.

The predecessor row was `internal_client_id`, marked COVERED against
`conditions.py`'s crosswalk floors. **Every one of those floors is keyed on
LEI**, so they could never report the absence of entities that have none —
a gate selecting by the property it polices. The spec's §D names this
exactly: *"an LEI-only anchor silently excludes privately-held middle-market
borrowers, and every downstream product inherits the exclusion."*

Closing it is a generation task nobody has run: invent no-LEI obligors with
internal client ids and no GLEIF record. Recorded, not fixed.

### §F now means two different things across the catalog

v0.3 **repurposes §F** from *Manufacture envelope* to *Source binding &
readiness*, and adds a §G. Anything reading §F by letter gets the envelope
for twenty specs and readiness for this one. **Match section headings by
NAME.** If the migration continues, this stops being a one-spec quirk.

### Fixed

Manifest re-derived to the 4 live rows: 1 probed clean (the crosswalk, still
requiring CIK), 3 GAPs that are real named absences (the half-present
address pair, the no-LEI population, jurisdiction entitlement scope). The
full sweep now completes: **129 of 280 rows accounted for, 87 probed clean,
0 failures**, with 151 rows unchecked in the 12 products that have no
manifest yet.

`test_every_manifest_still_resolves_against_its_live_spec` now fails on this
class of drift **by name, listing every stale mapping and every unmapped
row at once**, instead of aborting the sweep on the first one.

## 56 · Fluree answers "how many predicates" three ways and only one is right — `GROUP BY ?p` invents predicates that do not exist (RECORDED, worked around, measured 2026-08-29)

Found while building the estate catalog for publication. Three queries
against `fibo-v2`, same ledger, same moment:

| Query | Answer |
|---|---|
| `SELECT (COUNT(DISTINCT ?p) AS ?n) WHERE { ?s ?p ?o }` | **178** |
| `SELECT ?p (COUNT(?s) AS ?n) … GROUP BY ?p` | **198** |
| `SELECT DISTINCT ?p WHERE { ?s ?p ?o }` | **171** |

**171 is correct.** Established by taking the union of all 198 candidates and
asking each one for a single row through it directly:

```sparql
SELECT ?s FROM <fibo-v2> WHERE { ?s <CANDIDATE> ?o } LIMIT 1
```

171 return a row. **27 return nothing at all** — they appear only in the
`GROUP BY` result. Among them `ex:_d0`, `ex:_d1`, `ex:_d2` and
`ex:AdministrativeAgent`; the last is a *class*, not a predicate, which is
what makes the phantom plausible enough to publish by accident.

Zero real predicates were missing from `SELECT DISTINCT`, so the failure is
purely over-reporting in `GROUP BY`, plus a `COUNT(DISTINCT)` that agrees
with neither enumeration.

### Why this one matters more than a wrong number

The catalog being published to the vault is the SDK side's source for
engineering Context Products. Built from the `GROUP BY`, it would have handed
them **27 predicates that do not exist**, each looking exactly like the 171
that do — and a consumer writing a traversal against `ex:AdministrativeAgent`
gets an empty result that reads as *"no administrative agents in this
estate"* rather than *"this predicate is not real"*. That is a wrong answer
returned confidently, the failure class this repository keeps finding.

It is also a direct instance of [[aggregates-hide-the-decision]]: three
aggregates over one ledger, disagreeing, and the only reliable method was to
stop aggregating and enumerate.

**I had already reported the wrong figure.** "178 distinct predicates" was
stated to Dave on 2026-08-29 from `COUNT(DISTINCT ?p)` before any of this was
checked.

### Worked around, not fixed

`generators/build_store_catalog.py` enumerates with `SELECT DISTINCT`, unions
in the `GROUP BY` candidates so nothing is missed, then **confirms every one
by direct query** and records the rejected phantoms in the output. Per-predicate
assertion counts are taken with their own `COUNT` rather than from the
`GROUP BY` that produced the phantoms.

The underlying Fluree behaviour is not diagnosed and no upstream fix is
attempted. **Any future code counting predicates must enumerate and verify**,
not aggregate.

## 57 · `spread_observation` and Fluree's `PriorObservation` are one wildcard apart and keyed by the same LEIs (RECORDED, not fixed, reported by ccf-sdk 2026-08-30)

`ccf-sdk` found this while building `CP-SPEC-003` and reported it rather than
working around it, which is the exchange behaving as intended.

`ccf_v2.spread_observation` holds **47,849** rows of credit-spread market data.
Fluree carries **50** `PriorObservation` nodes, which are *rating* signals, and
they are keyed `prior-obs-<LEI>` — **the same obligor LEIs**.

So a build reaching for *"the observation about this obligor"* — an
`ILIKE '%spread%'`, or a traversal to the obviously-named node — can get a
rating signal and serve it as a financial fact. **Both stores answer
correctly.** Neither is wrong, neither errors, and the join succeeds. The
result is a confidently wrong answer, which is this repository's most-recorded
failure class.

`ccf-sdk` gates against reading either. **Nothing on this side gates it**, and
that is why it is recorded here: the collision lives in our naming, not in
their spec.

Not fixed. Renaming either would touch loaded data in two stores, and the
correct fix is more likely a validator asserting no product resolves an
"observation" without naming which kind. Whoever writes it should note the
two populations differ by three orders of magnitude, so a count-based check
would catch a swap and a *sample*-based one would not.

---

## 58 · The validator suite writes to the authoritative Fluree ledger — `t` climbs 46 per run while the data does not move (RECORDED, deliberate, measured 2026-09-01)

**A rising `t` on `fibo-v2` is not evidence that anything changed.** Read that
sentence before you investigate one.

`validators/test_aml_typology.py` runs `loaders/load_fluree_wave17.py` as a
subprocess **twice** per suite run — once in the edge-count idempotency test,
once in the rule-literal test — to prove that loader is safe to re-run. It is:
every triple it writes is identical to one already there. But Fluree records a
commit per batch regardless, so each suite run appends about 23 commits per
loader invocation.

Measured three times on 2026-09-01, on an otherwise idle estate:

| | `fibo-v2` t | triples |
|---|---:|---:|
| after the bundle dump | 5,112 | 87,162 |
| after a suite run | 5,158 | 87,162 |
| after a suite run | 5,204 | 87,162 |
| after a suite run | 5,250 | 87,162 |

**+46 every time, to the unit.** The triple count never moved.

Controls, so the attribution is not a guess:

- 90 seconds idle with no queries at all: **delta 0**. Nothing writes on its own.
- three `GET /v1/fluree/ledgers`, one `COUNT(*)`, three `SELECT`s: **delta 0**.
  Reads do not advance `t`.
- `ls -lt /data/fluree/fibo-v2/main/commit` — 5,204 commit files, matching `t`
  exactly, the newest written *inside* a suite run, and their contents carry
  `AMLP-0147`, `AMLP-0148`, `AMLP-0149`.
- `ps` and `crontab` on db1: nothing running but the Fluree server itself.

### Why it is left in place

The test is worth its cost. A loader that corrupts on re-run is a real
failure and this is the only thing that would catch it, so the write is the
point rather than a side effect. What was wrong was not the test — it was
everything downstream that treated `t` as though it described the data.

### What it broke, and what changed because of it

The portable bundle hardcoded `t` as an expected value in
`portable/verify_install.py` and `portable/restore/restore_fluree.sh`. That
number is stale the moment anyone runs the suite, which is why it had drifted
from 4,468 to 5,112 unnoticed — 644 commits, and not one new fact among them.
Rebuilding could not fix it: the rebuild itself was overtaken before it
finished.

So `t` is now recorded into `MANIFEST.json` at export time by
`dump_fluree.sh` and read back by both the restore and the verifier. **This is
a weaker claim and it is labelled as one.** It proves the replay carried every
commit the archive held; it does not prove the archive was complete. The
*triple* counts stay hardcoded — they are stable, so they remain knowledge
independent of the artifact being checked, which is the whole argument for
hardcoding a landmark in the first place.

`validators/test_shipped_landmarks.py` fails if anyone types a `t` back in.

### The general form

An idempotent loader is idempotent in **content**. It is not necessarily
idempotent in **commits, timestamps, sequence numbers, or file mtimes**, and a
count-based idempotency proof cannot tell those apart — which is why this
surfaced as a landmark failure rather than as a test failure. Before treating
any monotonic counter as a landmark, ask what advances it besides the data.

---

## 59 · Fluree corrupts `^^xsd:date` literals arriving through SPARQL UPDATE — 65 of 65 dates wrong, arbitrarily (FIXED by not typing dates, measured 2026-09-10)

Found loading Florida UCC-1 filings, where the filing date is not a detail —
it is the element the whole product turns on, because under UCC Article 9 the
filing date establishes priority between competing secured parties.

The loader wrote:

```
<ex:ucc-filing-202403337275> <ex:filedOn> "2024-12-19"^^<xsd:date> .
```

The ledger returned `1971-11-15`.

**Not an offset.** Across 65 filings, **zero** round-tripped, with **53
distinct deltas** ranging from −15,741 to +9,734 days. A timezone bug or an
epoch confusion would be a constant; this is not.

Isolated with a two-triple control writing the same value both ways, through
the same call, read back by the same query:

| Written | Read back |
|---|---|
| `"2024-12-19"` (untyped) | `2024-12-19` ✅ |
| `"2024-12-19"^^<xsd:date>` | `1971-11-15` ❌ |

**Fix: dates are written as plain ISO-8601 strings.** That is also the
estate's existing convention — no other loader types a date, which is exactly
why nothing hit this in twenty waves. `ex:filedOn` and `ex:lapsesOn` were the
first `xsd:date` literals in `fibo-v2`.

### Why the first validator missed it

`test_every_filing_has_a_filing_date` **passed** while every date was wrong.
It asked whether a `filedOn` triple existed for each filing. It did. The
triples were present and the values were fabricated.

A count cannot see a value being altered. The check that caught it compares
each stored date against the source record it came from, and it is the only
kind of check that could have. Same lesson as the idempotency entries above:
**name a value, not a cardinality.**

The 214 corrupted triples were retracted with `DELETE DATA` (sending the same
typed literals, which corrupt identically and therefore match) and rewritten
untyped. Verified 0 `xsd:date` literals remain in the ledger.

---

## 60 · Fluree's `COUNT(*)` under-reports on a multi-pattern WHERE — 17 for a query returning 65 rows (RECORDED, worked around, measured 2026-09-10)

A second counting defect, and a nastier one than [§56](#56) because it errs in
the opposite direction and only on *some* shapes.

Same ledger, same moment, clause `?f a ex:UccFiling ; ex:filedOn ?d .`:

| Query | Answer |
|---|---|
| `SELECT (COUNT(*) AS ?n)` | **17** |
| `SELECT (COUNT(?f) AS ?n)` | **17** |
| `SELECT (COUNT(DISTINCT ?f) AS ?n)` | **65** |
| `SELECT ?f ?d` — rows counted client-side | **65** ✅ |

**The single-pattern count is correct.** `?f a ex:UccFiling .` counts 65 both
ways. So the aggregate is right until it is not, and any spot-check on a
simple pattern agrees with it — which is how a wrong count earns trust before
it is used somewhere it matters.

The failure surfaced as an impossible result: a query with a `FILTER` returned
**more** rows than the same query without one (65 filtered vs 17 unfiltered).
A filter that adds rows is arithmetically impossible, which is the only reason
it was noticed rather than believed.

**Workaround: `validators/test_ucc_fl.py` never asks the store to count.** It
selects the rows and counts them in Python, where the arithmetic is ours. See
`_rows()` there.

Together with §56 this makes the rule general: **do not accept a cardinality
from Fluree's aggregates.** Enumerate and count locally, or verify the
aggregate against an enumeration first.

---

## 61 · 43 `COVSRC-*` anchor nodes carry no `rdf:type`, and 170 span anchors have no end (**RESOLVED 2026-09-13** — see the resolution at the end)

Both found answering a vault check-in; the second was flagged by the vault from
the `ex:` register's own numbers (`startOffset` 261 vs `endOffset` 91) and is a
claim about this lane that needed our reader.

### 61.1 · Untyped anchor nodes — invisible under no-inference

`loaders/load_anchors_wave6.py:155-168` writes each `COVSRC-*` node with nine
predicates — `covenantType`, `threshold`, `evidencedBy`, `documentId`,
`startOffset`, `endOffset`, `passageSha256`, `anchorVerified`, `provenance` —
and **no `rdf:type`**.

CLAUDE.md rule 7 is explicit: *"Fluree runs without reasoning by default... Type
entities explicitly for every role you need to query against."* So **43 nodes
holding verified passage anchors are unreachable from any type-anchored
traversal.** They answer a predicate query and nothing else.

**CORRECTED 2026-09-13, by `ccf-sdk`.** This entry originally said "43 untyped
nodes". It is **43 assertions over 37 SUBJECTS** — 31 carrying one `startOffset`
and 6 carrying two. That is the wrong-unit read this very file documents three
times elsewhere, made while documenting it, and `load_anchors_wave6.py`'s own
docstring already said "COVSRC-* 37 nodes". The sibling `COVDEF-*` namespace
written by Wave 15 IS typed (`ex:Covenant`), so the two halves of the same idea
are queryable in different ways.

### 61.3 · The six double-anchor nodes invent 36 wrong citations

Found by `ccf-sdk` 2026-09-13 and reproduced here exactly.

**Six of the 37 carry TWO complete anchors** — two `startOffset`, two
`endOffset`, two `passageSha256`, two `evidencedBy` — with **nothing in RDF
pairing one start to its own end**. A predicate-join therefore returns the
cross-product:

| | |
|---|---|
| join `documentId` × `startOffset` × `endOffset` × `passageSha256` | **79 rows** |
| re-hash `document.text[start:end]` and compare to the stored sha256 | **43 match, 36 FAIL** |

So a consumer following the offsets gets 79 candidate citations of which **36
do not hash to what the node says they should**. The anchor's stated purpose is
that a citation is *checked rather than trusted*; here the check fails on 46% of
what the join produces.

**`ex:evidencedBy` is the correct route and it is intact.** Following it to the
named passage and re-hashing gives **43 of 43 matching**. The data is right; the
predicate-join is what is wrong, because RDF set semantics lose the pairing the
loader knew at write time.

**One number we measured differently.** `ccf-sdk` reported "one hashing to the
empty string". We measure **12 rows across 6 subjects** slicing to empty — and
among them `(225927, 167832)`, a span whose **start is greater than its end**.
Python slices that to `""` silently, so an inverted span and a zero-length span
look identical downstream. That is a distinct defect and neither of us named it.

**Root cause is the same as 61.1**: the loader writes four parallel literals per
anchor and relies on their order, which RDF does not keep. Reifying the anchor —
one node per (start, end, sha256, passage) — is the shape that survives.

**Not fixed here.** Choosing the type is a modelling decision — `ex:Covenant`
matches the sibling, but these are *source anchors* rather than covenants, and
Fluree is append-only so a wrong type cannot be withdrawn, only contradicted.
It also needs a `partition.py` allowlist entry.

### 61.2 · 170 point anchors wearing a span predicate

`ex:startOffset` holds 261 assertions over 255 subjects; `ex:endOffset` holds 91
over 85. **170 subjects carry a start with no end** — 158 `DefinedTerm`, 11
`MeasurementPeriod`, 1 `Covenant`. Zero carry an end with no start.

**Nothing was dropped.** `sources/screening/covenant_definitions.json` gives a
definition `body_start` / `body_end` / `decl_offset`, but a *component* only
`term`, `declared_at`, `cited_at`. There is no end offset in the source for
components, so `load_covenant_definitions_wave15.py:271` writes the only offset
it has.

The defect is semantic, and it was in the binding table: `endOffset` was
described as *"the closing offset of the same span"*, which asserts a 1:1 that
has never held. `startOffset` is doing two jobs — a span start on
`CovenantDefinition`, a point anchor everywhere else — under one name that
promises the first.

The register now states both counts with their units and says plainly that the
pairing does not hold. **The open question is whether point anchors should carry
a distinct predicate** (`ex:declaredAt`) so that `startOffset` always implies a
resolvable span. That is a new bound term plus a reload, so it is proposed, not
done.

**Why this matters beyond tidiness.** The binding table's own justification for
these predicates is that *"span offsets are how a citation is checked rather than
trusted."* A point anchor cannot check a citation — you cannot extract the quoted
text from it. 170 anchors do not serve the purpose the predicate was bound for.

### 61.4 · Resolution — the cause was a URI missing a field, not lost pairing

**Everything in 61.3 was a symptom of one thing: the node key omitted the
document.** `covenants_extracted.json` holds **60 document entries across 47
accessions** — one filing appears once per exhibit. XPO, Inc.
`0001104659-26-068522` carries two separate credit agreements, `ex10-1` and
`ex10-2`, each with its own `leverage`, `fixed_charge_coverage` and
`secured_leverage` covenant at different thresholds and different spans.
Keyed on `COVSRC-{accession}-{covenant_type[:8]}`, **six URIs each received two
covenants from two different agreements.**

The agreed fix before this was to **reify** the anchor. It would not have
worked: it would have produced one node correctly carrying two anchors, and
still no way to know it was two covenants. **A node that should not exist
cannot be repaired by giving it better structure.**

**Applied 2026-09-13:**

| | before | after |
|---|---:|---:|
| COVSRC URIs | 37 for 44 covenants | **44 for 44** |
| four-literal join | 79 rows | **44** |
| anchors hashing correctly | 43 of 79 | **44 of 44** |
| inverted spans (`start > end`) | ≥ 1 | **0** |
| nodes with no `rdf:type` | 43 assertions / 37 subjects | **0** |
| point anchors distinguishable | no | `ex:declaredAt`, 170 |

396 old triples retracted, 44 correctly-keyed nodes written, Wave 15 re-run so
its 39 definition edges re-derived onto the new URIs — `covsrc_index()` already
keyed on `(documentId, covenantType)`, the right key, and was being defeated by
the collided URIs, so it needed no change.

**One covenant reappeared.** 44, not 43: the collision had been overwriting one.

### 61.5 · `load_anchors_wave6.py` had been unrunnable, and nothing said so

Found while re-running it. `d["accession"]` raised `KeyError` on **89 of the
249** documents in `fibo_v2` — later waves segment documents that are not SEC
filings and carry no accession. Confirmed pre-existing by running the committed
version, which fails identically.

**A Wave 6 loader that cannot execute at all, against the estate it wrote.**
Nothing in the suite re-runs it, so nothing reported it. Fixed to skip
documents without an accession, which is correct: the loader matches ON
accession, so such a document cannot match.

The general point is worth more than the fix: **a loader is only known to work
on the day it is run.** Every wave loader in this repo is in the same position
unless something re-executes it.

---

## 62 · 315 legal entities were invisible to a `Party` query — three loaders stopped the role chain early (**RESOLVED 2026-10-09**)

Found writing `docs/fluree_ontology.md`. Fluree runs no reasoner (§5.2), so a
node is returned by a `cmns-pts:Party` query only if it is *asserted* `Party`.
`load_fluree_wave3.py` asserts all seven roles. Four later loaders each kept
their own hand-written tuple of role types, and three of them stopped short:

| Population | Loader | Typed up to | Missing |
|---|---|---|---|
| `ICJ-SPV-*` (150), `ICJ-INT-*` (40) | `load_offshore_wave13b.py` | LegalEntity | LegalPerson, Party, Agent |
| `RSSD-*` (3) | `load_reporting_bank.py`, `load_nic_hierarchy.py` | LegalEntity | LegalPerson, Party, Agent |
| `HLD-*` (119), `Cyc*` cycle (3) | `load_bo_chains_wave13b.py` | LegalPerson | Party, Agent |

**Why nothing caught it.** No validator or loader in this repo queries by
`Party`, `Agent` or `LegalPerson`. The answers were short only for a
downstream consumer asking "every party connected to X", which silently
skipped the offshore vehicles and beneficial-ownership holders. The offshore
loader's own comment reads "Fluree has no reasoner"; it applied that to
`ServiceProvider` and not to the chain above `LegalEntity`.

**Fix: additive, no query changes.**

- `ccf/party_roles.py` holds the chain once, as published, and
  `with_ancestors()` closes over it. The four loaders now call it instead
  of listing roles by hand.
- `loaders/remediate_party_role_closure.py` asserted the 823 missing types
  (315 Party, 315 Agent, 193 LegalPerson). Each is an ancestor of a type
  the node already carried, so no new claim was made. Ledger: 88,325 →
  **89,148** triples. A second run writes nothing.
- `validators/party_role_closure.py` recomputes the closure from the ledger
  on every run. `validators/test_party_role_closure.py` checks the chain
  link-by-link against `dev.fibo-quickstart.ttl` (named superclasses only,
  restrictions excluded), with negative controls, and checks both 13b
  loaders' real output.

**A control caught a defect in the test itself.** The first Turtle reader
ended a class block at `" ."`, but this file writes the terminator as
TAB-dot. The reader ran on into the following classes, and the "is this
link published?" test would have passed for links FIBO never states. The
negative control (Corporation must have exactly one named parent) failed
and exposed it.

**After:** 854 chain-typed nodes, 854 typed `Party` (was 539). `LegalPerson`
661 → 854, `Agent` 539 → 854.

**Downstream:**

- The portable bundle ships 88,325 triples, so
  `test_shipped_landmarks.py` is red until the bundle is rebuilt.
- `docs/store-catalog.json` (vault-mirrored) still shows Party 539 /
  LegalPerson 661.
- `cmns-org:ServiceProvider` is an `AgentRole` in Commons, not an
  organization type. The `ICJ-INT-*` typing with it is a separate modelling
  question and was left alone.

---

## 63 · ccf-sdk test fixtures rebuilt eight live `ccf_v2` tables without keys — twice — and took both views with them (**REPAIRED 2026-10-09**)

**What happened.** ccf-sdk's cp-00…03 example fixtures hard-code the schema
name `ccf_v2` and run `DROP TABLE … CASCADE` / `CREATE TABLE` with no keys,
defaults, indexes or comments. On 2026-09-22 (20:16–20:46 UTC) a ccf-sdk
session mapped `CCF_TEST_POSTGRES_DSN` to the shared host by name suffix and
ran them against live `parkavedb`. ccf-sdk confirms this in
`contrib/ccf-sdk/ccf-v2-damage-attributed-and-full-restore-list`.

Affected tables: `legal_entity`, `crosswalk`, `filing_profile`,
`financial_fact`, `principal`, `principal_jurisdiction`, `peer_entity`,
`peer_fact`.

**It happened twice, not once.** The 2026-09-13 bundle dump already shows
the eight tables keyless, with OIDs 39122–39157. Those are below
`ucc_debtor_crosswalk` (39627, created with Wave 21 on 2026-09-10). So a
first rebuild ran between 2026-08-31 (catalog shows keys) and about
2026-09-10. The views survived that one only because something re-ran
`ensure_views` afterward (the views' OIDs are 39912/39917). ccf-sdk's account
covers only 09-22. The first run is **dated in §63.1**: 2026-09-08 05:59 UTC.

**Damage, all structural:**

- 9 primary/unique keys and 12 foreign keys were lost. Eight of the foreign
  keys sat on tables that were NOT rebuilt (`deal`, `debt_instrument`,
  `facility`, `gdelt_mention`, `projection_plan`, `signal_event`,
  `trend_delta`, `warn_match`). A cascade strips the constraint and leaves
  the rows.
- 9 column defaults, 7 indexes and 3 comments were lost.
- 3 column types were widened (`lei` varchar(20) → varchar,
  `lei_match_score` numeric(4,3) → numeric).
- Both views were dropped: `v_entity_jurisdiction` and
  `v_ownership_cross_border`.

**Rows: none changed.** All eight tables, plus the four others the fixtures
wrote to (`institutional_holder`, `facility`, `internal_client`,
`debt_reconciliation`), match the 2026-09-13 dump row for row.

**Repair:** `loaders/repair_ccf_v2_structure.py`, one transaction, idempotent.

- Keys came from `docs/store-catalog.json`. Defaults, indexes and comments
  came from the loaders' own DDL.
- Constraints were added validated, so Postgres proved the data satisfies
  them.

Verified afterwards:

- 0 catalog keys missing.
- Views at 421 / 532 rows, equal to the 2026-08-31 catalog.
- Data unchanged.
- Duplicate-LEI and orphan-reference inserts are rejected (tested, rolled
  back).
- Suite 799/800. The 1 failure is the §62 bundle landmark.

**Not restored:** `financial_fact`'s table comment. The loader's text was
not copied verbatim, so the comment was left out rather than approximated.

**Still open:**

1. **The 2026-09-13 portable bundle ships the damaged structure.** It was
   dumped after the first rebuild, so a restore from it has no keys on these
   tables. Rebuild the bundle.
2. ~~The first rebuild is unattributed.~~ Dated 2026-09-08 05:59 UTC (§63.1).
3. ccf-sdk's fixtures still hard-code `ccf_v2`. The only barrier is their
   client-side fence (`4ba5746b`). A read-only role for ccf-sdk's
   connections would make a write impossible rather than refused. Dave,
   2026-10-09: *".76 should be readonly"*.

### 63.1 · The first rebuild dated, a second foreign table found, and the views were missing for three weeks (measured 2026-10-10)

**The first rebuild was 2026-09-08 05:59 UTC.** ccf-sdk could not name it:
their transcripts before 2026-09-10T01:16Z were auto-deleted. Their
`contrib/ccf-sdk/earlier-ccf-v2-rebuild-no-guard-before-0922-and-how-to-attribute-it`
predicted that cp-02's rows file fails on a duplicate `facility_id` against
the real estate. db1's Postgres log (readable by group `adm`) has that error
exactly three times:

| time (UTC) | event |
|---|---|
| **2026-09-08 05:59:13** | `duplicate key value violates unique constraint "facility_pkey"`, Key `FAC-01BB3F`, statement header `-- Rows for examples/cp-02-facility-terms-snapshot` |
| 2026-09-22 20:20:54 | same: ccf-sdk run #1 (their account: 20:16:44) |
| 2026-09-22 20:42:42 | same: ccf-sdk run #2 (their account: 20:38:25) |

12 of the 27 `ccf:cp04-*` test ledgers on the shared Fluree have their
earliest file at **2026-09-08 05:59**, in the same minute. The other 15 date
from 2026-09-02 03:50–04:00 (14) and 2026-09-05 11:49 (1). The Postgres log
begins at 2026-09-08 05:57:22 because of weekly rotation, so whether those
earlier runs also hit Postgres **cannot be determined**.

No `cp04_*` schemas exist in `parkavedb`, so cp-04's own Postgres leg never
ran against `.76`. The search was positive-controlled: the same `LIKE`
pattern finds `ccf_v2`.

**A second foreign table: `public.companies` is ccf-sdk's, not ours.** It
has OID 39222, just after the rebuilt eight (39122–39157). Its 10 rows are
ccf-sdk's s1-00 example data (`Northwind Traders`, `Contoso Manufacturing`,
…). Its DDL is `~/ccf_code/examples/s1-00-companies-over-revenue/scenario/schema.sql`,
whose `create table if not exists companies` names no schema, so it landed
in `public`. **Our bundle ships it as v1 data.** The 2026-09-10 note in
`portable/verify_install.py` ("the v1 schema holds `companies`, `entities`
and `relationships`") is wrong: v1 is `entities` and `relationships`, and
`public (v1) base tables` = 3 counts a foreign table.

**Left in place pending Dave's call.** Dropping it is destructive. Changing
the landmark and its comment means a bundle rebuild, because the shipped
`verify_install.py` must stay byte-identical with the repo's.

**The views were missing from 2026-09-08 to 2026-10-09, except for a gap.**
The log records 158 `relation "ccf_v2.v_entity_jurisdiction" does not exist`
errors, the first at **2026-09-10 21:23:49** (this repo's own suite, during
Wave 21) and the last at 2026-10-10 02:11 (tonight's pre-repair suite).
Something re-ran `ensure_views` before the 09-13 dump (the views' OIDs are
39912 / 39917), and the 09-22 run dropped them again. **A red suite on 09-10
said so, and nothing recorded it.**

**The widened column types are explained.** ccf-sdk's
`tools/dump_cp03_fixture.py::_ddl` keeps a length only for `character(n)`,
and never reads numeric precision or scale. So `varchar(20)` became
`character varying`, and `numeric(4,3)` became `numeric`.

**What the 09-22 fence does not cover** (ccf-sdk's statement): someone
running the fixture SQL by hand (`psql -f`).

### 63.2 · `public.companies` removed (2026-10-10), and a guard that had been taught to accept it

**Decision.** Dave asked ccf-sdk on 2026-10-09 whether to have ccf_dataprep
remove it. ccf-sdk recommended yes, and Dave had the recommendation posted
to the vault and pointed this repo at it:
`contrib/ccf-sdk/recommendation-remove-public-companies`. ccf-sdk
established two things:

- The table came from `tests/examples/test_s1_00_output.py::seeded`,
  unguarded until 2026-09-10 (`contrib/ccf-sdk/public-companies-came-from-the-s1-00-test-seed-0908`).
- Nothing in ccf-sdk reads it on `.76`.

**Done.**

1. **A copy was kept first:**
   `docs/evidence/2026-10-10-public-companies-from-ccf-sdk-s1-00.sql`
   (pg_dump of the definition and all 10 rows). Its company names match
   ccf-sdk's `examples/s1-00-companies-over-revenue/scenario/companies.sql`
   exactly.
2. **Checked first:** no foreign key or view depended on the table, and no
   `s1_00_*` graph-store schemas exist (positive-controlled: the same
   pattern finds `ccf_v2`). There was nothing else to remove.
3. **Dropped** in one transaction, which re-verified the table still matched
   the saved copy (10 rows, same names) before the `DROP`. `public` now
   holds `entities` and `relationships`, the real v1 tables.
4. **Bundle landmark** `public (v1) base tables` set back to 2, in
   `portable/verify_install.py` and `portable/restore/restore_postgres.sh`.
   A change note was added to the bundle README and to the `~/ccf-dist`
   README, because anyone who restored a bundle from 2026-09-10 to
   2026-10-09 received the 10 rows.

**The lesson is in the landmark history.** The value was 2 and correct. The
contamination landed on 2026-09-08, and from then on the check failed,
correctly. On 2026-09-10 the failure was read as "the 2 was carried forward
from a hardcoded literal and had been failing since the guard was
introduced", and the landmark was raised to 3, so the guard was taught to
accept the contamination. That reading was never checked against *what the
third table was*. A landmark that starts failing is a measurement; before
moving it, name the object that moved it. The 09-10 note is kept in place
in `verify_install.py`, marked WRONG, rather than deleted.
