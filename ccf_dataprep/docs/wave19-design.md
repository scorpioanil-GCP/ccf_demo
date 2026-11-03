# Wave 19 — `large-exposure-rwa-concentration` · design

The twenty-first and last product in the catalog. Q019 §5 puts it last because
it composes six prerequisites; the vault spec calls it "less a new capability
than a demonstration that the ladder holds together."

All six prerequisites — `corporate-family-tree`, `credit-exposure-rollup`,
`collateral-and-setoff-coverage`, `covenant-in-force-as-of`,
`kyc-refresh-beneficial-ownership`, `mnpi-wall-enforcement` — were confirmed
**registered in `validators/conditions.py`**, not merely built, before this
design was written. That was the gate `docs/HANDOFF.md` set on starting.

---

## 1 · Scope, and the line we do not cross

This wave produces the data a large-exposure calculation rests on: the regime
rule text, the group-forming edges, the limit envelopes, the capital base, the
mitigation inputs, the projection plans, and the departmental workbook.

It does **not** compute a limit utilisation at request time, resolve a
`ProjectionPlan` for a principal, aggregate Context Debt across a cascade, or
implement any of §D's ten steps. Those are Operators — runtime SDK entities —
and CLAUDE.md forbids building them.

The one place this wave computes anything is `validators/large_exposure.py`,
which recomputes group composition and limit utilisation from the stores on
every run in order to answer *does this data support what §F claims*. Per
CLAUDE.md's own carve-out, a build-time validator is not an Operator: it does
not register, does not compose into a plan, does not serve a principal, does
not emit a contract, and does not run at request time.

### `ProjectionPlan` is a name collision, and the docstrings must say so

§C assigns a `ProjectionPlan` per perspective to Postgres, so the rows are
ours to produce. The name is also an SDK Protocol entity, and three
`ProjectionPlan`-named tables already exist in this estate from earlier waves.

The rows this wave writes are **catalog data describing what each perspective
would receive** — nothing more. The loader docstring, the table comment, and
the `conditions.py` registration each state plainly: *does not resolve, does
not assemble, does not run at request time.* `validators/large_exposure.py`
reads these rows to check they exist and differ per perspective; it must never
grow into a shadow §D by walking a plan and producing a payload.

### A trap in §E worth naming

§E reads *"group composition and capital base materialized"*. That is **not** an
instruction to store connected groups. It describes the runtime SDK's caching
posture — an assembly concern — and §D/§E are read for understanding only.
Reading §E as a storage instruction is precisely the misread CLAUDE.md added
its "what operator means" section to prevent. See §4 below for what we do
instead.

---

## 2 · What already exists

Measured against the live estate on 2026-08-27, not carried over from prose.

| Input | State |
|---|---|
| Reporting bank + capital base | **Done.** `ccf_v2.reporting_bank` (2 rows), `ccf_v2.bank_capital` (12 quarters). JPMorgan Chase Bank, N.A., RSSD 852218, LEI `7H6GLXDRUGQFU57RNE97`; holding company RSSD 1039502. Tier 1 $295.8bn, RWA $1.96tn, CET1 15.08% at 2026-03-31 |
| Control edges | **Done.** `ccf_v2.corporate_ownership_record`, 280 ACTIVE GLEIF consolidation edges over 166 entities |
| Connected groups (control basis) | **Derivable, real.** 26 components, each containing exactly one anchor; **9 span ≥ 3 countries** |
| Jurisdictions | **Done, and no longer thin.** 30+ countries across 421 entities in `v_entity_jurisdiction`. The Wave 8 audit's "only 3 non-US entities" finding is stale — Wave 15's GLEIF subsidiary fetch closed it |
| Exposure | **Done.** `ccf_v2.facility`, 60 rows, $55.7bn total commitment / $40.4bn drawn |
| Mitigation | **Done.** `collateral_asset` (91), `collateral_pledge` (95), `haircut_schedule` (6), `setoff_enforceability` (12) |
| Limit scaffolding | **Partly done.** `limit_definition` (3 intents, already carrying a `connection_basis` column), `concentration_limit` (60) |
| Context Debt | **Done.** `ccf_v2.context_debt`, 304 rows |
| Peer bank capital | **Done.** `ccf_v2.member_call_report`, 16 real banks, Wave 18 |

Everything else in §C is this wave's work.

---

## 3 · A units defect this wave must fix first

`bank_capital.tier1_capital` holds `295758000`. That is **thousands of
dollars** — FDIC's BankFind API reports in thousands — so the real figure is
$295.8bn. `facility.commitment_amount` holds plain dollars. **Neither column
records its unit anywhere**, and the loader does not mention it.

Every number this product exists to produce is exposure divided by capital. A
naive ratio is wrong by a factor of 1,000.

**Why nothing caught it.** `loaders/load_reporting_bank.py` verifies that
tier 1 ÷ RWA reproduces the filed CET1 ratio, and it passes — because a ratio
is **unit-invariant**. Both operands are in thousands, so the thousands cancel.
The single check guarding this table is structurally incapable of observing the
unit. This is the same shape as the estate's other silent-pass defects: the
check answers a question whose answer cannot change when the defect is present.

**Remediation, in Task 1**, before any dependent arithmetic:

1. Record the unit explicitly — a `unit` column on `bank_capital` and
   `member_call_report`, valued `USD_THOUSANDS`, with the provenance note.
2. Add a **magnitude** assertion that is not unit-invariant. **Two tiers, not
   one band** — a single JPM-class band is a false red on the peers:

   | Assertion | Applies to | Bound |
   |---|---|---|
   | Universal floor | every FDIC-sourced row — **28 rows across 16 institutions** | total assets in dollars **≥ $10bn** |
   | Reporting-bank band | RSSD 852218 only | total assets **$1tn – $10tn** |

   The universal floor is chosen from the measured population, not guessed.
   The 16 peers span **$159.8bn – $4,091.3bn** in assets; under a 1,000× error
   they would read **$0.16bn – $4.09bn**. Every true value clears $10bn by at
   least 16×, and every wrong value misses it by at least 2.4×. A ~39× gap
   separates the two populations, so the floor discriminates for all 28 rows
   with no per-bank table to maintain.

   **Corrected 2026-08-27, mid-execution.** Earlier drafts of this section
   said "17 rows", and Task 1's review traced the figure here. It is wrong
   under every reading. Measured live: `bank_capital` holds **12 rows for one
   institution** (RSSD 852218); `member_call_report` holds **16 rows for 16
   institutions**; and **852218 is one of those 16** — the two tables overlap.
   So the assertion loops over **28 rows** covering **16 distinct
   institutions**. "1 reporting bank + 16 peers = 17" assumes no overlap, and
   that assumption is false. A count derived by arithmetic rather than
   measured against the tables is exactly the failure this whole section is
   about.

3. **Do not** use tier 1 ÷ assets as the control. It sits in a tight
   7.03%–10.77% band across `member_call_report`'s 16 rows, which looks like a
   strong invariant and is worthless here: it is a ratio, so it is
   unit-invariant, and it would pass identically on the defect. This is the
   same trap the CET1 check fell into.

The magnitude floor is the positive control the ratio check never was.

---

## 4 · Connected groups are computed, never stored

**Decision (Dave, 2026-08-27): always recomputed.**

§C's Data Catalog assigns no element called "connected group" to any store. It
assigns the **edges** — corporate family and control edges, beneficial
ownership, and `economicallyDependentOn` — all to Fluree. Materialising a group
table in Postgres would duplicate into one store what another store owns, which
is exactly what CLAUDE.md's single-writer discipline forbids, and it would go
stale silently the next time an ownership edge is added.

So:

- **Fluree holds edges only.** `connectedTo` (control-derived) and
  `economicallyDependentOn` (engineered, with an assertion date and an author).
- **Nothing anywhere stores "these nine entities are a group."**
- `validators/large_exposure.py` walks the edges fresh on every run, forms the
  groups under each `connection_basis`, and recomputes utilisation from
  `facility` and `bank_capital` directly. It reads no stored group, no cached
  percentage, and no boolean breach flag.

The practical consequence: adding an ownership edge next year changes the
groups automatically and the validator notices. Under a stored design it would
not.

---

## 5 · Regime text — three sources, all probed live

Probed 2026-08-27. **§C names EUR-Lex for CRR; EUR-Lex does not work from
here** and the substitute is better.

| Regime | Source | Status |
|---|---|---|
| **Regulation O** — 12 CFR 215 | eCFR versioner API, `title-12.xml?part=215` | ✅ HTTP 200, 50KB structured XML, point-in-time by date |
| **CRR** — Arts 392–403 | **legislation.gov.uk**, `/eur/2013/575/article/{n}/{date}` | ✅ HTTP 200, full text, point-in-time by date |
| **PRA large exposures** | prarulebook.co.uk, `/pra-rules/large-exposures/{DD-MM-YYYY}` | ✅ HTTP 200, server-rendered, point-in-time **in the URL** |

**EUR-Lex is blocked**, not slow: every request returns HTTP 202 with a
zero-byte body, including `eur-lex.europa.eu/homepage.html`, with and without
a cookie jar and with three different user agents. `publications.europa.eu`
cellar content negotiation returns HTTP 400. Recorded the way Wave 17 recorded
FATF's 403 — a measured fact with a date, not an assumption.

The substitute is not a compromise. legislation.gov.uk carries CRR as
**assimilated UK law with full point-in-time history**, and Article 395's
operative text ("shall not incur an exposure … the value of which exceeds 25%
of its eligible capital") is retrievable verbatim at any date it was in force.

### The CRR fetch must name in-force dates, and must not trust the word "omitted"

Articles 392–403 were omitted on **2022-01-01**. A fetch of the *live* URL
returns an omission notice, not operative text. Measured 2026-08-27:

| Date requested | Size | Operative text present? |
|---|---|---|
| `2020-12-31` | 69,369 B | **yes** |
| `2021-12-31` | 69,337 B | **yes** |
| `2022-01-01` | 43,449 B | no |
| `2023-01-01` | 43,410 B | no |

So Task 2 fetches **`2020-12-31` and `2021-12-31`** for operative CRR text —
two dates that are both in force and whose text genuinely differs, since
CRR2 (Regulation 2019/876) amended Article 395 in the interval — and treats
**`2022-01-01` as the omission event**, captured as version history rather
than as rule text. PRA Rulebook versions carry the regime from that date on.

**The trap:** the string *"omitted"* appears on **all four** responses,
because the textual-amendment annotation ("Arts. 392-403 omitted (1.1.2022) by
virtue of S.I. 2021/1078") rides along on the in-force versions too. A guard
written as `grep -i omitted` flags every date and discriminates nothing. The
task asserts on the **operative sentence** — `shall not incur an exposure` —
and carries both a known-in-force and a known-omitted date as positive and
negative controls, so a checker that always answers the same way is caught.

### The regime version history is real, not engineered

`docs/spec-digest.md` lists "regime version history" among the **engineered**
elements. It does not have to be.

legislation.gov.uk records that **CRR Articles 392–403 were omitted on
2022-01-01** by The Capital Requirements Regulation (Amendment) Regulations
2021 (SI 2021/1078), when responsibility for large exposures passed to the PRA
Rulebook.

**Corrected 2026-08-27, during Task 9.** An earlier draft of this paragraph
said the UK "moved large exposures out of assimilated CRR and into the PRA
Rulebook", which is half right and misleading about the half it gets wrong.
Measured across the fetched PRA corpus: **the PRA Large Exposures Part states
no prohibition at all** — zero passages contain "must not incur" or "shall not
incur". Every "25%" in it sits in **LE 2.3**, a *notification duty* for
non-core LE group exposures that happens to use the same figure. **LE 2.4**
reads "A firm must exclude from **the limit in Article 395(1) of the CRR**…".

So the operative prohibition for a UK firm remains **Article 395(1)**; the PRA
Part applies and modifies it rather than restating it. The regime boundary is
still real and still load-bearing — it is what makes an `as_of` reconstruction
differ from the live answer — but a limit anchored to LE 2.3 would cite a
reporting trigger as its source. §D's regime-anchoring gate exists to catch
exactly that, and the audience is an examiner who would. The PRA Rulebook publishes its Large Exposures Part at
every effective date it has ever had: `01-01-2014`, `01-01-2020`, `01-01-2022`,
`01-01-2026`, `01-01-2027`.

So §F's *"≥ 2 regime versions with distinct effective dates, so `as_of`
reconstruction differs from the live answer"* is satisfied by a **real
regulatory handover with a real effective date**, which genuinely changes which
rule applies at a given `as_of`. That is strictly better than inventing one,
and it is what §D's examiner replay is for.

**The internal limit envelope's version history remains engineered**, correctly
labelled `synthetic — internal` per §C. Real regime versions, invented internal
versions — each labelled for what it is.

---

## 6 · The breach problem, and how it is actually solved

**Measured, not assumed.** With the units read correctly:

| | |
|---|---|
| Tier 1 capital | $295.8bn |
| 25% regulatory limit | **$73.9bn** |
| Largest connected group's commitment | **$16.0bn — 5.4%** |
| Entire book, all 22 groups holding facilities | **$55.7bn — 18.8%** |

**No group can breach a 25% limit, and the whole book together does not reach
it.** Manufacturing a booked breach would require inventing roughly $74bn of
exposure on one group — about 4.6× the largest that exists.

Two alternatives were measured and rejected:

- **A second consolidation level.** Only two entities under holding company
  RSSD 1039502 are still active: JPMorgan Chase Bank N.A. ($4.09tn) and
  "JPMorgan Chase Bank, Dearborn" ($71m). No usable middle. The UK route —
  J.P. Morgan Securities plc, Companies House 02711006 — fails on
  machine-readability: the filed accounts are a **TIFF scan** (`go-tiff2pdf`,
  114 pages, 113 characters of extractable text) and no OCR is available here.
- **Syndicate participations against each lender's own capital.** Computed
  live from the 97 Wave 18 `SyndicateParticipation` nodes against
  `member_call_report`: the largest is **1.25% of its own tier 1** (Citizens
  Bank). Nowhere near any limit.

### The solution: Regulation O's threshold is an absolute dollar figure

**Decision (Dave, 2026-08-27).** From the real 12 CFR 215.4(b), fetched and
quoted rather than recalled:

> "in no event may a member bank extend credit to any insider of the bank or
> insider of its affiliates in an amount that, when aggregated with all other
> extensions of credit to that person, and all related interests of that
> person, exceeds **$500,000**"

Reg O binds on **$500,000**, not on a percentage of capital. A $250m facility
is 0.08% of JPMorgan's capital — comfortably compliant under both CRR and PRA
— and simultaneously over Reg O's line by a factor of 500.

So §F's *"≥ 1 group compliant under one regime and in breach under another"* is
satisfied **regulation against regulation**, both real, both cited to filed
provision text, with **no invented exposure whatsoever**. The only engineered
element is the insider relationship itself.

**Reg O is a stack, not a flat $500,000 test, and the narrowing must be
written down.** 12 CFR 215.4 layers several limits: a percentage-of-capital
threshold requiring prior board approval (the higher of $25,000 or 5% of
unimpaired capital and surplus, §215.4(b)), the absolute $500,000 cap above
which that approval is required regardless, the single-borrower lending limit
of 15% of unimpaired capital via 12 U.S.C. 84 (§215.2(i)), and an aggregate
ceiling across all insiders and their related interests. **This wave exercises
the $500,000 cap only** — it is the one that binds at this estate's exposure
magnitudes, since 5% of $295.8bn is $14.8bn and nothing approaches it.

Citing only the cap is sufficient for §F's divergence *provided the row says
so*. A methodology document implying Reg O **is** a flat $500k test would be
inaccurate about real regulation. So the narrowing is written in one sentence
in the methodology document itself, and again as a `divergence` string on the
`spec_coverage.py` row — the same treatment the DEF 14A insider narrowing gets,
and the same treatment `shell_company_ownership` got in Wave 17.

**The proposal must never be booked.** §F's *"≥ 1 proposal that breaches"*
needs a hypothetical above $73.9bn. If that lands in `ccf_v2.facility` as
though drawn, we have created precisely the invented $74bn of exposure this
design rejected in §6, and every portfolio total in the estate silently moves.
Proposals live in **their own table**, never in `facility`, carry an explicit
hypothetical marker and `synthetic — engineered` provenance, and
`validators/large_exposure.py` asserts that the estate's booked commitment
total is **unchanged** by this wave — a magnitude assertion on $55.7bn, not a
row count, since a count cannot see an amount being altered.

**A second, softer divergence comes free:** the internal appetite limit is set
below 5.4% so the largest group also breaches house policy. `internal` is a
listed value of §B's `regime` enum, and §C already classes the internal limit
envelope `synthetic — internal`.

### Reg O and real people

**Decision (Dave, 2026-08-27): real rule text, invented insiders.**

Reg O governs a bank lending to its *own* directors and executive officers. A
literal reading of §F's "from a real DEF 14A related-party disclosure" would
name real JPMorgan directors as borrowers on an engineered breach.

We do not. We ingest **12 CFR 215 and JPMorgan's real DEF 14A related-party
disclosure as the citable rule and methodology text**, and the insider and the
insider loan that actually trip the limit are **invented, with synthetic
identifiers**. This is the same shape as the `aml-typology-match` rule — real
definitions from public sources, invented entities exhibiting the pattern — and
it honours CLAUDE.md's pseudonymisation rule for real living people.

Recorded as a **satisfied-with-divergence** row in `spec_coverage.py`, with the
narrowing rendered under the row, the way `shell_company_ownership` was.

### Engineered breaches on a real bank

**Decision (Dave, 2026-08-27): real bank, breaches labelled.**

`generators/fetch_reporting_bank.py` deferred this to the capstone in its own
docstring. The estate already attaches invented facilities and balances to 50
real named obligors; attaching an invented limit envelope and invented insider
cases to a real bank is the same operation, and §F asks for a genuine capital
base in terms.

Every exposure, limit, insider designation, proposal and breach carries an
explicit provenance class, and **no engineered breach may read as a factual
claim about a real institution.**

The internal appetite limit is the sharpest case. Setting house policy below
5.4% makes a **real** control group, built from real GLEIF edges and booked
against a **real** named bank, come out "in breach" — of an entirely invented
policy. That is acceptable only if the envelope is unmistakably
`synthetic — internal` **and** no sentence anywhere in the estate reads as
*"JPMorgan is over its large-exposure limit."*

**So the provenance floor is not a flag check.** A floor that inspects only a
`breach` boolean would pass while a SQLite workbook line said the quiet part in
prose — and the departmental store is exactly where that leaks, because it is
the one store whose contents are free-text working notes. The floor in
`validators/large_exposure.py` covers, by enumeration:

- every **utilisation row** — the computed percentage and the limit it is
  measured against, wherever either is persisted;
- every **workbook line** in the SQLite risk-limit workbook, including free
  text;
- every **methodology and narrative passage** in MongoDB that names the
  reporting bank;
- every **breach and proposal record**.

For each, it asserts the row is labelled `synthetic — internal` or
`synthetic — engineered`, that no row labelled `public` participates in a
breach, and — separately — that no free-text field asserts a regulatory breach
by the real institution. The second is not implied by the first: a correctly
labelled row can still carry a sentence that reads as fact once quoted out of
its table.

---

## 7 · Where everything lands

Per §C, and nowhere else.

| Store | This wave writes |
|---|---|
| **Postgres** (`E`, `Π`) | `unit` columns + magnitude assertions (Task 1); three `ProjectionPlan` rows |
| **Fluree** (`R`, `P`, `T`) | FFIEC NIC RSSD hierarchy; `connectedTo` edges; **≥ 4 `economicallyDependentOn` edges** with assertion date and author; insider and related-party designations; internal limit envelope and sub-limits; regime version history with effective dates |
| **MongoDB** (`L`) | Reg O / CRR / PRA rule text; connected-counterparty definitions (PRA SS03/25, SS16/13); passage spans **with embeddings**; methodology documentation |
| **SQLite** | risk-department limit workbook |
| **Neo4j** | nothing — still optional, still unneeded |

**Embeddings are not optional here.** known-issues §38 and §42 record 84
estate passages that carry none — 12 from Wave 18, 72 from Wave 17 — and a
corpus-wide similarity search silently returns nothing from either. This wave
does not add to that population.

---

## 8 · Semantic binding

FIBO carries real material for this product, verified in subject position
against `sources/fibo/dev.fibo-quickstart.ttl` (`dev`, not `prod` — see
known-issues on the 40 modules `prod` omits):

- `fibo-fbc-pas-fpas:Exposure`, `ExposureBearer`, `ExposureSituation`,
  `FinancialExposure`, `hasExposureTo`, `isExposureOf`
- `fibo-be-oac-cpty:` — a full controlling-party vocabulary including
  `ContractualControl`, `DeFactoControllingInterestParty`,
  `DeJureControllingInterestParty`, `MajorityControllingParty`

Terms with no FIBO declaration — expected to include `ConnectedGroup`,
`economicallyDependentOn`, `governedByRegime`, `CapitalBase` and the regime
version vocabulary — are minted under `ex:`.

**A caution recorded from this session.** The first absence check run here
returned "0 hits" for every candidate term, including `Exposure` and `Capital`,
which FIBO plainly declares. The regex was wrong, not FIBO: declarations open
their own Turtle block with the qname **alone on a line**, and a pattern
requiring a trailing space matches nothing. Task 3 uses
`generators/verify_fibo_wave18.py`'s established subject-position method and
its positive control, and asserts a **known-present** term as well as the
absences. An absence check that cannot produce a hit proves nothing.

Task 3 also updates the binding table in `docs/ccf_dataprep_v2.md`, and the
wave sends the corrected mirror through the agent exchange. Note the mirror is
already stale by four uncollected Wave 18 bundles.

---

## 9 · The §F conditions, and how each becomes data

| §F condition | Route | Class |
|---|---|---|
| ~15 connected groups, ≥ 3 jurisdictions | 26 real components exist; 9 span ≥ 3 countries each — see the reading note below | public |
| Real Call Report / FR Y-9C capital | loaded; units fixed in Task 1 | public |
| ≥ 4 `economicallyDependentOn` edges, ≥ 1 changing the binding limit | engineered, with assertion date and author; the rank-changing one recomputed, never flagged | engineered |
| Regime text for PRA 9/17, CRR, Reg O, limits anchored to provisions | eCFR + legislation.gov.uk + prarulebook.co.uk | public |
| ≥ 2 regime versions, distinct effective dates | **real** — CRR Arts 392–403 omitted 2022-01-01 by SI 2021/1078; PRA Part versions at five dates | public |
| ≥ 1 group compliant under one regime, in breach under another | **Reg O $500k vs CRR/PRA 25%** | rule public, insider engineered |
| ≥ 1 proposal that breaches | hypothetical proposal above $73.9bn | engineered |
| ≥ 1 that fits only after mitigation | proposal sized just over the line until haircuts apply | engineered |
| ≥ 1 Reg O related-party case | real rule text, invented insider | engineered |
| ≥ 1 group breaching `debt_tolerance` | from existing `context_debt` | internal |
| Three ProjectionPlans, examiner carrying methodology + replay | engineered | internal |

### Reading note — which unit "≥ 3 jurisdictions" counts

§F reads *"**~15 connected groups** across the anchor obligor set, spanning
**≥ 3 jurisdictions**"*. That admits two readings, and they are not equally
satisfied:

- **Collective** — the ~15 groups between them span ≥ 3 jurisdictions.
  Satisfied overwhelmingly: 26 groups across 30+ countries.
- **Per-group** — each of the ~15 groups spans ≥ 3 jurisdictions on its own.
  **Satisfied 9 times, not 15**, from real control edges alone.

We build to the **stricter per-group reading** and close the gap the honest
way: several of the engineered `economicallyDependentOn` edges are chosen to
merge groups whose combined footprint crosses a third jurisdiction, which is
precisely the behaviour §C says those edges exist to demonstrate — a group that
control-based grouping alone would miss. If the stricter reading still falls
short of 15 after that, the shortfall is **recorded as a divergence**, not
papered over by switching to the looser reading after the fact. `~15` is an
envelope figure and a shape for a demo dataset; `≥ 3` is a floor.

The validator counts **groups that individually span ≥ 3 jurisdictions**, and
reports the collective figure separately so the two can never be confused.

**Every `≥ N` above is a floor to be recomputed, never a count to be read.**
The two that cannot be established by counting at all — the dependency edge
that *changes the binding limit*, and the group that *flips between regimes* —
are the ones `validators/large_exposure.py` exists for, exactly as
`validators/ib_rank.py` exists for `ib-opportunity-synthesis`'s ordering claim.

---

## 10 · Task breakdown

1. **Units repair** — `unit` columns, magnitude assertions on `bank_capital`
   and `member_call_report`, regression test
2. **Fetch regime text** — eCFR Reg O, legislation.gov.uk CRR (≥ 2 dates),
   PRA Rulebook (≥ 2 versions + SS16/13 + SS03/25), with manifests and
   retrieval dates
3. **FIBO verification and binding** — subject-position check with positive
   control; `docs/ccf_dataprep_v2.md`; exchange bundle
4. **Regime text → MongoDB** — documents, passage spans, **embeddings**
5. **FFIEC NIC RSSD hierarchy → Fluree**
6. **`connectedTo` edges → Fluree** from the real control graph
7. **`economicallyDependentOn` edges → Fluree** — ≥ 4, engineered, assertion
   date and author, ≥ 1 changing the binding limit
8. **Insider and related-party designations → Fluree** — invented insiders
9. **Internal limit envelope and sub-limits → Fluree**
10. **Regime version history → Fluree** — real effective dates
11. **Methodology documentation → MongoDB**
12. **Risk-department limit workbook → SQLite**
13. **Three `ProjectionPlan` rows → Postgres** — with the "does not resolve,
    does not assemble, does not run at request time" disclaimer in the loader
    docstring, the table comment and the registration
14. **Engineered cases** — breaching proposal, mitigation-dependent proposal,
    Reg O breach, debt-tolerance breach. **Proposals go in their own table,
    never in `facility`**, and the task asserts the estate's booked commitment
    total is unchanged at $55.7bn
15. **`validators/large_exposure.py`** — recomputed floors
16. **Registration** — `conditions.py`, `partition.py`, `spec_coverage.py`.
    **Assert this product's lines by name, never "the file is green."** Full
    `spec_coverage.py` runs already exit non-zero for two inherited reasons
    (§11), so a permanently red suite is somewhere new rows can hide
    indefinitely. Task 16 asserts each new PASS and each floor **by its own
    name and expected verdict**, and records the register's PASS count before
    and after so the delta is the number of checks actually added.
17. **Docs, handoff, exchange bundle** — including the correction to
    `docs/spec-digest.md`, whose jurisdiction finding is stale (§2)

---

## 11 · Known hazards carried into this wave

- **Positional identity.** Four loaders on `main` rewrite other waves' rows
  when a table grows. Check before adding rows to any shared table.
- **`spec_coverage.py` full runs are red** — inherited, two causes: the
  `counterparty-reference-snapshot` manifest mapping matches zero catalog rows,
  and DEFERRED rows make a non-zero exit by design. Neither is this wave's.
- **Read the PASS count from `conditions.py`**, never the "0 failed" line.
  `uv run pytest` is broken repo-wide; use `uv run --with pytest pytest`.
- **The peer fabric must be configured** or eight Wave 18 checks SKIP and two
  `partition.py` arms FAIL by design. Configured on this machine from
  `~/.bashrc`, not `.env`.
- **Fluree SPARQL needs an explicit `FROM <fibo-v2>`** or returns HTTP 500, and
  `?s <p> ?s` does not enforce equality on this build (known-issues §27).
- **`shares_reconcile` is FALSE and must not be re-derived** — Wave 18 deleted
  it for four legitimate filing-side reasons. Anyone reaching for a
  commitment-reconciliation floor here is about to redo that work.

---

## 12 · Deliberately not built

- Any §D operator, plan resolution, contract assembly, or TTL enforcement
- FFIEC 101 advanced-approaches detail — the loaded capital is **bank-level**
  FDIC, not holding-company FR Y-9C, and FFIEC 101 is absent. Recorded as a
  divergence in `spec_coverage.py` rather than silently invented
- A stored connected-group table (§4)
- OCR of Companies House scans
- Neo4j

---

## 13 · Decisions taken, with dates

All five put to Dave and **confirmed by him on 2026-08-27**, before
implementation — not assumed:

1. **Real bank, breaches labelled** — JPMorgan stays; every engineered breach
   carries its provenance class and a validator floor enforces it.
2. **Reg O: real rule text, invented insiders** — no real person is named as a
   borrower on an engineered breach.
3. **Connected groups are always recomputed**, never stored.
4. **Two consolidation levels: withdrawn.** Measured and unavailable — no
   second real capital base exists at any level.
5. **Regime divergence via Reg O's $500,000 absolute threshold** against
   CRR/PRA's 25%, plus an internal appetite set below 5.4%.

### Seven corrections from Dave's design review, 2026-08-27

Folded into the sections named, not left as review notes:

| # | Correction | Where it landed |
|---|---|---|
| 1 | A $1tn–$10tn band is JPM-class and a false red on the 16 peers | §3 — split into a universal **$10bn floor** (measured to discriminate all 28 rows with a ~39× margin) and a reporting-bank band |
| 2 | CRR dates must be while Arts 392–403 existed; don't read an omission notice as rule text | §5 — `2020-12-31` and `2021-12-31` named, `2022-01-01` as the omission event, and the "omitted" string trap documented |
| 3 | The provenance floor must cover utilisation rows and workbook lines, not a breach flag — SQLite is the leak | §6 — floor enumerated across four surfaces plus a separate free-text assertion |
| 4 | Reg O is a stack; citing only the $500k cap needs a written narrowing | §6 — one sentence in the methodology doc and a `divergence` string on the coverage row |
| 5 | The $73.9bn proposal must not land in `facility` | §6 and Task 14 — own table, hypothetical marker, and a magnitude assertion that booked commitment is unchanged |
| 6 | `ProjectionPlan` collides with the SDK Protocol name | §1 — disclaimer in docstring, table comment and registration; validator must not grow into a shadow §D |
| 7 | New rows can hide in a permanently red `spec_coverage.py` | Task 16 — assert this product's lines **by name**, with a before/after PASS count
