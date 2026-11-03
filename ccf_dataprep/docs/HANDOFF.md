# Handoff

## State

> **Status block refreshed 2026-08-28.** This section was written at B1's
> Task 10 close and described two branches as unmerged and `main` as
> unpushed. All three claims were false by the time anyone read them — the
> status sentences outlived the state they described, which is the failure
> this file exists to prevent. The historical detail below is preserved
> as-written; only the status sentences are corrected. Where a figure carries
> a date, that date is when it was measured, not when it was true.

**B1 (portable dump and restore of every store) is COMPLETE, MERGED AND
PUSHED.** Merged at `c899026`, loose ends closed at `c1a2dea`. This was the
final phase of the plan (see "Build order" in `CLAUDE.md`); with it done, the
estate is portable to a laptop.

**Estate data catalog published and mirrored, 2026-08-30 (`5206155`).**
`generators/build_store_catalog.py` reads all five stores live and emits
`docs/store-catalog.{md,json}` — 115 Postgres tables / 987 columns / 2 views,
171 Fluree predicates, 6 Mongo collections with inferred document specs, 8
SQLite tables. The vault mirrors it and serves it over MCP as
`get_article("context-products", "estate-data-catalog")`. **Regenerate rather
than correct it.**

**FIBO reporting boundary ruled and mirrored, 2026-08-30 (`6a985ba`).**
`fibo-fnd-acc-cur:MonetaryAmount` + `hasCurrency` bound for
`financial_fact.value`/`.unit`; eighteen reporting terms verified ABSENT from
the EDM Council source. **FIBO models entities, instruments and relationships —
not financial reporting**, so `[UNMAP]` is correct and *permanent* for
reporting-shaped rows. Three near-misses (`Income`, `Debt`, `Amortization`) are
named MUST-NOT-USE.

> **Two zeros that day were broken patterns, not absences** — see
> known-issues §56 and the binding section in `ccf_dataprep_v2.md`. **Run a
> positive control on any search whose result is an absence.**

**Wave 20 shipped, 2026-08-28 (`39f373d`).** The three T1 gaps on
`counterparty-reference-snapshot` are closed so rung 1 can be built: the
addresses are labelled (`legal_address_*` + `hq_address_*`, 153 of 156
loaded), jurisdiction entitlement is recomputed rather than read
(`principal_jurisdiction` + `validators/entitlement.py`), and 30 no-LEI
borrowers now exist in a new `internal_client` table. **The product reports
4 of 4 §C rows with ZERO GAPS.** conditions.py 208 · partition.py 63/63 ·
745 tests. Plan and rulings: `docs/wave20-t1-gaps-plan.md`; schema:
`docs/ccf_dataprep_v2.md` under "Wave 20". **No FIBO terms changed, so the
vault mirror needs no refresh.**

> **The bundle at `/data/laptop` predates this wave** and does not carry any
> of it. Rebuild with `portable/dump/dump_all.sh` before the laptop restore
> if it should.

**Earlier the same day.** Two validator defects in
`corporate-family-tree` found and fixed (`known-issues.md` §53 and §54),
merged at `96b88ae` and pushed: an attribute probe whose population had grown
to every LEI-bearing node in the ledger and sat permanently red, and a check
named "entities carrying a real LEI" that counted neither entities nor real
LEIs. Repo suite **711 passed**; `conditions.py` **199 passed · 0 failed**.
No data changed — both were gates measuring the wrong thing.

**Where the bundle lives.** `/data/data_bundle` on db1 — **373 MB across 11
artifacts**, with a `MANIFEST.json` recording a sha256 per artifact.
Independently re-verified against that manifest with **0 mismatches**.

- **Rebuild the bundle** from the workstation: `portable/dump/dump_all.sh`.
- **Restore** on a target machine: `/data/data_bundle/restore/restore_all.sh`,
  then `uv run --no-project /data/data_bundle/verify_install.py`.
- Reference docs: `docs/b1-portable-dump-design.md` and
  `docs/b1-portable-dump-plan.md`.

**What was actually rehearsed.** The **Ubuntu branch of every restore
script** was rehearsed end to end on db1 (Ubuntu 24.04) — Neo4j included, via
a throwaway container — and the verifier reached **exit 0, 20/20 checks,
"Estate verified," nothing skipped**.

**What was not rehearsed:**
- The **macOS branch of the restore scripts is unexercised** until the
  laptop night — it has the same code path reviewed, not run.
- **A truncated-Fluree damage case** is not exercised — the CLI has no way
  to produce one, and the on-disk ledger format isn't documented well enough
  to hand-craft one safely.
- **No Neo4j case inside `damaged_restore.sh`** — Neo4j's restore
  correctness was proven directly against the throwaway container instead,
  not via the damage-injection harness used for the other stores.

**Records this task corrected as stale** (measured live 2026-08-27/28,
figures verbatim in `docs/known-issues.md` §50–52 and `docs/backlog.md`
§B1): the B1 sizing table, the Fluree "no export path" claim (true of HTTP,
false of the CLI), and `CLAUDE.md`'s "5 tables" description of
`data/departmental.sqlite` (it is 8).

---

**Wave 19 (`large-exposure-rwa-concentration`) is COMPLETE, MERGED AND
PUSHED.** All 17 tasks done, including registration (Task 17). It is in
`main`'s history; the `wave19-large-exposure` branch is gone.

**This is the 21st and final catalog product.** With it registered,
**21 of 21 context products are now built.** That count is DERIVED, not
incremented: `validators/spec_coverage.py`'s own `PRODUCTS` list holds 21
entries (counted from the list itself), and the vault's `context-products`
topic independently lists 21 product articles (25 files less the four
standards documents — `ccf-sdk-de-requirements`, `ccf-v2-schema-delta`,
`fibo-iri-binding`, `spec-standard-v0-3` — which are not products). Both
counts were taken independently on 2026-08-27 and agree.

**`main` is level with `origin/main`** — pushed 2026-08-27 and again
2026-08-28. Nothing is outstanding. (This paragraph previously said `main`
was 47 commits ahead and unpushed; that stopped being true on 2026-08-27 and
the sentence outlived it by a day.)

| Task | State |
|---|---|
| 1 · repair the capital units defect (`bank_capital`/`member_call_report`) | complete |
| 2 · fetch regime text (Reg O, CRR, PRA) | complete |
| 3 · FIBO verification and semantic binding | complete |
| 4 · regime passages into MongoDB | complete |
| 5 · reporting bank + holding company into Fluree | complete |
| 6 · `connectedTo` edges from real GLEIF control graph | complete |
| 7 · engineered `economicallyDependentOn` edges | complete |
| 8 · Regulation O insider designation | complete |
| 9 · limit envelope and real regime version history | complete |
| 10 · methodology documentation into MongoDB | complete |
| 11 · risk-department limit workbook into SQLite | complete |
| 12 · ProjectionPlans (credit-officer, committee, examiner) | complete |
| 13 · two hypothetical exposure proposals | complete |
| 14 · connected group breaching debt tolerance | complete |
| 15 · `validators/large_exposure.py` — eight recomputed §F floors | complete |
| 16 · registration (`conditions.py`, `partition.py`, `spec_coverage.py`) | complete |
| 17 · docs, handoff, vault exchange | **complete — this close** |

**Green as of 2026-08-27 (Task 17 close). Every number below was re-run and
read from the tool's own output during this close, not copied from an
earlier report. Read the PASS count, never the "0 failed" line:**

- `uv run validators/conditions.py` — **199 passed · 0 failed · 0 skipped**
  (was 184; the 15 new checks are the `#21 large-exposure-rwa-concentration`
  block — 7 direct counts and 8 delegates to `validators/large_exposure.py`).
- `uv run validators/partition.py` — **60/60 checks passed** (was 56/56;
  the 4 new checks are `check_wave19()` — no capital figure leaked onto a
  Fluree node, no connected-group table materialized in Postgres, no regime
  rule text outside MongoDB, no hypothetical proposal leaked into the real
  `facility` table).
- `uv run validators/large_exposure.py` — **8 passed · 0 failed**, each
  floor recomputed live against the stores at `as_of` time — no floor reads
  a stored breach flag, rank, or count.
- `uv run --with pytest pytest validators/test_large_exposure.py -q` —
  **42 passed** (includes negative controls: a gross-over/net-under
  proposal must FAIL the breach floor, and a dataset with no distinct cure
  case must fail the distinctness floor).
- `uv run validators/test_fabric_isolation.py` — **7/7 arms green**. Not a
  pytest file: run it directly, `pytest` collects nothing from it. (Unrelated
  to this wave — carried over from Wave 18's co-lender fabric — reconfirmed
  green here because Task 17's Step 5 asks for it explicitly.)
- `uv run validators/spec_coverage.py --product large-exposure-rwa-concentration`
  — **17 of 17 catalog rows accounted for** (12 probed clean · 4 covered by
  `conditions.py` · 0 waived · 1 deferred — FFIEC 101, see below). Exit code
  1 for this product run **by design**: the one honest `GAP` row.
- `uv run --with pytest pytest validators/ -q` — **647 passed**, full sweep.

**What Wave 19 built, end to end:** a real reporting bank (JPMorgan Chase
Bank N.A., RSSD 852218) and its holding company typed into Fluree with 12
quarters of real FDIC Call Report capital and 16 peer institutions, now
carrying a `unit` column and a $10bn magnitude floor after Task 1's repair;
184 `connectedTo` edges over 26 real GLEIF-control-basis connected
components, plus 4 engineered `economicallyDependentOn` edges that collapse
the graph to 23 components and change which limit binds on one merge; three
real regime versions (CRR, PRA Large Exposures, Regulation O) with real
effective dates spanning the 2022-01-01 SI 2021/1078 handover, cited to 464
regime passages fetched from eCFR, legislation.gov.uk, and the PRA
Rulebook; one real Regulation O related-party case built on an actual
JPMorgan director/executive-officer dual hat and a real $455,000,000
aggregate exposure across four facilities; two hypothetical exposure
proposals (one that breaches the limit net of mitigation, one that only
fits after mitigation — resized mid-wave once measurement showed the first
draft collapsed into the same demonstration as the second); a real
connected group shown to breach `debt_tolerance` against the live
`policy_tolerance()`; three ProjectionPlans, pairwise distinct by their
`elements_included` sets; and a five-row SQLite limit workbook whose every
note explicitly disclaims implying a regulatory breach.

## What Wave 19 did NOT build, stated plainly — two honest gaps

**FFIEC 101 is absent.** What is loaded for the reporting bank is FFIEC Call
Report Schedules RC-C/RC-R — **bank-level** FDIC BankFind data. FFIEC 101
(advanced-approaches capital detail) is filed at the **consolidated
holding-company** level, on an FR Y-9C capital base this estate does not
load. There is no holding-company chain here for that row to attach to;
every RWA figure in the estate is the standardized, bank-level number.
Recorded as a `GAP` in `spec_coverage.py`, not waived — see
`docs/ccf_dataprep_v2.md`'s Wave 19 entry for the full text.

**The jurisdiction span is 12 of a ~15 shape**, not the full figure §F's own
words describe. 9 of 26 control-basis connected components span ≥ 3
jurisdictions on real GLEIF control edges alone (Wave 15's fetch). Task 7's
4 engineered dependency edges closed 3 more of the shortfall through
genuinely defensible supplier-concentration merges (9 → 12). **A 4th
candidate (Agilysys ∪ Hain Celestial) was considered and REJECTED** — no
plausible supply, funding, or tenancy link exists between a
hospitality-software vendor and a packaged-foods company, and forcing that
merge to close the gap would be exactly the "counted but not created"
failure CLAUDE.md warns against. The remaining shortfall of 3 is a recorded
divergence in three places (`conditions.py`'s `groups recompute` check
text, `docs/ccf_dataprep_v2.md`, this file) — deliberately **not** added as
a row in `spec_coverage.py`, because that file maps §C catalog *elements*
and no §C row names a jurisdiction-span population for a divergence note to
attach to (Task 16's ruling; inventing one would fabricate a row the vault
spec does not contain).

## Wave 19 deferred findings — named, not counted

Four Minor findings from this wave's task reviews remain open at close (all
review Important/Critical findings were fixed in-wave; nothing above Minor
is outstanding). Writing "4 minors deferred" here would be exactly the
bookkeeping-without-content failure a prior wave already hit once — the
findings are written out, each with a stable id, in
**`docs/wave19-deferred-findings.md`** (committed; the SDD workspace they
originated in, `.superpowers/sdd/wave19-plan/progress.md`, is git-ignored
scratch that `git clean -fdx` destroys). In brief: **W19-D01** a rejected
FIBO-term-candidate list carries hand-written domain/range prose instead of
extracting it live; **W19-D02** a local-name collision fallback in
`load_group_edges.py` has never executed against real data; **W19-D03** one
loader's idempotency was confirmed by read-only inspection rather than a
reviewer's own live re-run (sandbox-blocked, not a live discrepancy);
**W19-D04** a generation-time diagnostic JSON field could be mistaken for
an authoritative figure by a future reader. Start there, not in the ledger.

## Three facts the next task on this data MUST know

**1. The fabric boundary is now checked in BOTH directions, and one crossing
is permitted.** `validators/partition.py::check_wave18` asserts that nothing
peer-owned sits in our stores AND that nothing of ours sits in the peer's.
The single permitted inward crossing is the Context Debt row §D step 5
requires: `ccf_v2.context_debt.subject_key` legitimately holds a peer
`declaration_id`, because a debt record that cannot name what it is debt
about records nothing. The exemption covers declaration ids only, in that
row's two columns only, and the check separately proves the peer's declared
TTL and latency values did NOT ride in with the identifier. `facility_id`,
`lei` and `rssd` are correlation keys §C declares and are excluded by name.
Do not widen either.

**2. `shares_reconcile` was deleted because it is FALSE, and it must not be
re-derived.** Not one of the twelve Wave 18 facilities' parsed shares sums to
`ccf_v2.facility.commitment_amount` — best 4.0% off, worst 3391% — for four
legitimate filing-side reasons. The weaker "no single share exceeds its
facility" fails too. Full account: `docs/known-issues.md` §34 (and §32 for
the Wave 4 facility total that is itself wrong). Anyone who reads the
commitment data and reaches for a reconciliation floor is about to redo this.

**3. The band peer's concealed figure is PUBLIC ON OUR SIDE (Ruling
T14-R1).** Our own ledger holds `ex:participationOf <Citi> → FAC-405B7A
commitmentUsd 70000000`, filed and public. Every claim about that figure
must be phrased about what the PEER DISCLOSES, never "obtainable only as a
range" or "cannot be recovered" — both are false on this estate.
`validators/syndicate.py::precision_is_mixed` is scoped to the peer fabric
for exactly this reason.

## Three facts about WAVE 19's data that are still true

**1. Groups are never stored — they are recomputed live, on every check,
every time.** No `ConnectedGroup` id, table, or node exists anywhere in the
estate. `validators/large_exposure.py`'s union-find runs fresh over
`ex:connectedTo` (and `ex:connectedTo` + `ex:economicallyDependentOn` for the
merged view) on every call. **Do not add a cached group id or count as a
convenience** — `check_wave19()`'s "no connected-group table in Postgres"
check exists specifically to catch that, and it now scans broadly (fix round
1, `f08fa5f`) rather than by two hard-coded name patterns.

**2. The two hypothetical exposure proposals are hypothetical all the way
down.** `ccf_v2.exposure_proposal` rows are `is_hypothetical=true` and
`synthetic — engineered`; neither is booked into `ccf_v2.facility`, and
`check_wave19()`'s "no proposal row in facility" check verifies this by id
prefix AND by exact `(borrower_lei, commitment_amount)` match, not by id
alone. **Do not derive a real breach claim from either proposal** —
`no_public_row_in_a_breach` (floor 8) exists to catch exactly a `public`-
provenance row sitting inside a breach narrative.

**3. `RegimeVersion.effectiveTo` is asserted only when a regime version has
actually closed.** CRR carries a literal `2021-12-31`; PRA and Reg O (both
still open) carry **no `ex:effectiveTo` triple at all**, not a sentinel
date. Any future query over `effectiveTo` must treat its absence as
open-ended, not as missing data to backfill.

## Two facts about WAVE 17's data that are still true

**1. The depth-3 network floor rests on a single graph edge.** Per Task 11's
design, exactly one engineered case establishes a party pair reachable at
depth 3 and invisible at depth 2 (`AMLP-0049` -> `AMLP-0166`, confirmed live
in `validators/aml_typology.py`'s floor 2). Against 201 parties (C(201,2) =
20,100 possible pairs), roughly 70 of those pairs would — if added as a new
`transactedWith` edge — create a shortcut that collapses this one
established case back to depth 2 or less. **Any future task that adds rows
to `sources/screening/wave17_transactions.json` must re-run
`generators/inject_typology_cases.py` afterward**, not merely re-run the
Fluree loader — the injector is what re-establishes the depth-3 case against
whatever the transaction population now is; skipping it risks silently
erasing the one condition this floor exists to demonstrate.

**2. `generators/generate_aml_transactions.py`'s `main()` refuses to run
while `sources/screening/wave17_cases.json` exists — deliberately, exit code
2.** That script rewrites the transaction artifact with the ORDINARY
population only; running it after Task 11 injected the engineered cases
would silently delete every injected transaction and leave the cases'
`txn_ids` dangling. The refusal is intentional and documented in the
script's own `main()` docstring/error text — to regenerate BOTH populations,
run `generators/inject_typology_cases.py` (which regenerates the ordinary
base in-process, then re-injects), not the base generator alone. A
`--regenerate-base` escape hatch exists for the ordinary population alone,
but it destroys the injected block and requires the injector to be re-run
immediately after.

## What Wave 17 and Wave 16 did — unchanged from the prior handoff

Wave 17 (`aml-typology-match`) is summarised in `docs/ccf_dataprep_v2.md`'s
2026-08-25 entries and in the carry-forward section below; it is merged to
`main` at `2be7abb`.

### Wave 16 (merged, pushed)

1. **`ib-opportunity-synthesis`** built across all five stores: Postgres
   (perspectives, weight vectors, mandates, coverage, debt ladder extended to
   48 obligors), Fluree (1,270 `OpportunitySignal` nodes, `coveredBy`,
   `comparableTo`/`comparabilityBasis` edges), MongoDB (15-document merger
   corpus: DEFM14A/PREM14A/S-4/S-4A), SQLite (`prospect_note` grown 18 → 50,
   6 flagged `rank_changing`).
2. **Six new FIBO/`ex:` bindings**, all Task 12, verified absent from FIBO
   before use, all already in `docs/ccf_dataprep_v2.md`: `OpportunitySignal`,
   `coveredBy`, `comparableTo`, `comparabilityBasis`, `isCurrent`,
   `primaryBankerId`.
3. **`validators/ib_rank.py`** (Task 14) — the four §F floors §F itself says
   cannot be established by counting, recomputed live on every run: a named
   divergence pair (Braemar M&A #3/DCM #22, Thermon mirrored), 4 of 4
   restricted LEIs exercised, 31 of 50 notes moving their own entity's rank,
   39 of 52 candidates reordering under a weight-version replay.
4. **Registration** (Task 15) — 5 conditions in `conditions.py`, 18/18 §C
   rows in `spec_coverage.py` (1 genuinely-absent S-1 row, not a fetch gap),
   7 new `partition.py` checks.
5. **Two validator hardening fixes** (Task 16): `spec_coverage.py`'s §C
   heading match is case-insensitive; `conditions.py`'s
   `ib_restricted_in_coverage()` no longer swallows every exception into
   SKIP.
6. **Three defects found and recorded** — `prospect_note.banker` keyed by an
   ambiguous display name (FIXED), 178 pre-existing MongoDB documents with
   no `doc_type` (OPEN, deliberately not back-filled), the SEC's SC 13D →
   SCHEDULE 13D form rename (handled, recorded as a pattern).

## Next

**Updated 2026-08-28, after B1 shipped.** Items 1 and 2 below described Wave
19's close and are now historical — Wave 19 was merged and pushed, and B1 was
built on top of it, merged at `c899026` and pushed. They are struck rather
than deleted so the sequence stays legible.

**The live list, in the order it matters:**

- **NEXT: `facility-terms-snapshot` is UNMAP — 0 of 12 §C rows.** Rung 02, and
  **nothing has ever asserted that an element it names is present** — not
  probed, not covered, not waived, not deferred. Reported by `ccf-sdk`
  2026-08-30; they request no action, but it is the same silence that hid rung
  01's gaps, and `spec_coverage.py`'s own docstring names why: *"silence reads
  exactly like success."* Write the manifest **against the current article** —
  the vault split the amendment row and added an entitlement-scope row on
  2026-08-30, so it is **12 rows, not the 10** they measured. Note
  `conditions.py` already carries volumetric checks for this product (~line
  1955); those are not element satisfaction.
- **RESOLVED 2026-08-28 — `counterparty-reference-snapshot` was migrated to
  `spec-standard-v0-3`, not casually trimmed.** The ruling this list asked
  for turned out to be answered by the spec itself: it declares **"Scope
  boundary: identity only — no exposure, no grade, no relationship"**, which
  accounts for risk grade and RM assignment; CIK and SIC were reassigned to
  the six and two other specs that name them, and CIK is still asserted by
  the surviving crosswalk probe. No custodian question was needed. Manifest
  re-derived to the 4 live rows; the sweep completes again — **129 of 280
  rows accounted for, 87 probed clean, 0 failures**. Details, including the
  preserved risk-grade measurement, in `known-issues.md` §55.
  **Two things came out of it that are still open:**
  - **The estate holds ZERO no-LEI entities.** v0.3 added a §C row for
    "Internal client identity for no-LEI entities" and we satisfy none of
    it. The old manifest could not see this: its predecessor row was covered
    by crosswalk floors that are all keyed on LEI. Closing it is a
    generation task nobody has run.
  - **§F means two different things across the catalog now** — "Manufacture
    envelope" on Q019, "Source binding & readiness" on v0.3. Worth asking
    the custodian whether the other twenty specs are migrating, and when;
    that answer changes how manifests should be built, not just what they
    waive.
- **B1's macOS branch is unexercised.** The Ubuntu branch was rehearsed on db1
  (Ubuntu 24.04): verifier exit 0, 20/20 checks, "Estate verified" with nothing
  skipped, Neo4j via a throwaway container. The macOS run is scheduled for the
  evening of 2026-08-28 in Arizona. Until it passes, B1 is delivered but proven
  on one target only. Start at `/data/data_bundle/laptop-loader.sh`; see
  `docs/backlog.md` §B1 and `docs/b1-portable-dump-design.md`.
- **Rotate `NEO4J_PASSWORD` and the co-lender Mongo credential.** Three
  exposures during B1's execution, all from grepping shell config for a
  variable NAME and receiving its VALUE. Neither is committed; both are
  exported from `~/.bashrc` on the workstation. See `known-issues.md` §39 for
  the trap: `load_dotenv()` does not override an already-set variable, so
  editing `.env` while the stale export survives leaves the old value winning
  and the rotation looking done.
- **B2 has never been started** (`docs/backlog.md` §B2) — making re-derivation
  from persisted sources actually hold. Three loaders still fetch live from the
  SEC at load time; the reproduction gate covers 18 of 51 artifacts; one
  fetch/load pair is fused with no saved intermediate.
- **The one test worth adding from B1's close:** a unit test constructing a
  bundle directory with `mongo-fibo_v2/` removed, asserting `restore_mongo.sh`
  exits 2. It retires the single standard the controller relaxed during
  execution — see `docs/b1-rulings.md`.
- **Fluree's ledger grows ~33 MB per commit indefinitely** (`known-issues.md`
  §50). `fibo-v2` is 47 GB holding 87,162 triples, of which 46 GB is ~1,421
  accumulated index generations that are never collected. One current index is
  47 MB. Reclaiming it touches the authoritative ledger and is Dave's call.
- **As-of over HTTP silently returns the wrong answer** (`known-issues.md`
  §51). `/v1/fluree/history` is 404 and the `t` parameter is ignored without
  error — a query at `t=100` returns the full current graph. Any claim that
  as-of is queryable over HTTP is false and would have looked verified. The
  CLI's `fluree history --from/--to` does work.

**Carried, unchanged, still unowned:** the corpus-wide embedding gap (14,205
of 37,865 passages with no usable vector, `known-issues.md` §48);
`spec_coverage.py` mapping 9 of 21 products; its unfiltered run still raising
on `counterparty-reference-snapshot`'s moved §C wording; 178 MongoDB
`document` rows with no `doc_type` (§21); 8-K Item 4.02 empty (§10.2).

<details>
<summary>Historical — Wave 19's close (items 1 and 2, now done)</summary>

1. ~~**There is no 22nd product.**~~ All 21 catalog products are built and
   registered — the last one deliberately last per CLAUDE.md's build order
   because it composes six prerequisites. Wave 19 has since been merged and
   pushed; B1 followed it.
2. ~~**No whole-branch review ran for Wave 19**~~, unlike Wave 18. Every task
   review (1 through 16) closed clean with its findings addressed in-wave;
   nothing in this wave's plan called for an additional whole-branch pass
   the way Wave 18's did. If one is wanted before merge, run it against
   `main..wave19-large-exposure` before merging, not after.
3. **`spec_coverage.py`'s `MANIFEST` covers 9 of 21 `PRODUCTS`** (was 8 of
   20; Wave 19 added `large-exposure-rwa-concentration`'s `LARGE_EXPOSURE`
   manifest). The unmapped twelve are pre-existing gaps — walk them the same
   way `aml-typology-match`, `syndicated-lending-co-lender`, and
   `large-exposure-rwa-concentration` were walked, one product at a time,
   before assuming any of them is done.
4. **A pre-existing, unrelated `spec_coverage.py` failure — INHERITED, NOT
   CAUSED BY WAVE 19**: a full unfiltered run (`uv run validators/spec_coverage.py`,
   no `--product`) still raises on `counterparty-reference-snapshot` — its
   manifest's mapping `'LEI, legal name, legal jurisdiction'` matches 0
   catalog rows because the vault's §C wording for that product has moved
   since the mapping was written. Reconfirmed live at this close, unchanged
   from Wave 18's close: same `RuntimeError`, same message, on the
   unmodified file. Not fixed — out of scope for three waves running — but
   it blocks every full-repo `spec_coverage.py` run until whoever owns
   `counterparty-reference-snapshot` re-reads its current §C.
5. **`spec_coverage.py` exits non-zero BY DESIGN while any row is DEFERRED**,
   and rows in `collateral-and-setoff-coverage`, `corporate-family-tree`,
   `ib-opportunity-synthesis`, and now `large-exposure-rwa-concentration`
   (the FFIEC 101 row) still are. Its own header says so: "This validator is
   expected to be RED until the catalog is complete. That is the point of
   it; do not waive a row to clear it." A non-zero exit from that file is
   not evidence of a break.
6. **The corpus-wide embedding gap needs an owner** (`docs/known-issues.md`
   §48, found this wave while verifying Wave 19's own passages). 14,289 of
   37,865 passages (37.7%) carry no usable vector — 84 with the field
   absent, 14,205 with it explicitly `null` — against the 84/0.2% previously
   on record. Wave 19 did not create this population and none of its own
   §F conditions depend on corpus-wide similarity search; it belongs to
   whoever owns the affected corpora (§33, §38, §42 all touch pieces of it).
7. **178 MongoDB `document` rows still have no `doc_type`** (known-issues
   §21) — a deliberate non-fix; belongs to whoever next owns the EX-10 /
   narrative corpora.
8. **8-K Item 4.02 is still empty** (known-issues §10.2) — zero in-window
   instances across all 53 anchors. Belongs to `credit-surveillance-early-warning`.
9. **Register generator welds a stale count into 58 of 83 notes** (flagged
   by the vault custodian, `ex-register-full-back-catalogue.md`, `t=1474`).
   No such generator exists in this repo; belongs to whoever owns it
   elsewhere.

</details>

## Wave 19 carry forward

- **The vault exchange bundle `2026-08-27T23-37-18Z-wave19-large-exposure-bindings`
  was sent this close.** `~/.agent-exchange/ccf-dataprep/outbox/` held zero
  uncollected bundles when this task started — the vault had drained every
  prior wave's mail since Wave 18's close (all of it now shows under
  `_archive/sent/` on this end). This is a fresh, standalone bundle: **3 new
  FIBO prefixes, 11 new FIBO class/property bindings, 1 FIBO term reused
  rather than re-minted (`hasSubsidiary`), 17 new `ex:` terms**. Not
  collected as of this writing — check `~/.agent-exchange/ccf-dataprep/outbox/`
  before assuming it has been.
- **The capital units defect is repaired, not merely documented.**
  `bank_capital`/`member_call_report` now carry a `unit` column and a $10bn
  magnitude floor (`docs/known-issues.md` §47). The floor exists *because* a
  ratio-based check is mathematically incapable of seeing a unit error — any
  future capital-adjacent check added to this estate should ask "does this
  compute a ratio of two figures from the same table" before trusting it to
  catch a unit mismatch.
- **Citations by cross-reference bit twice in one wave** (`docs/known-issues.md`
  §49) — PRA LE 2.4 and Reg O §215.4(c) both apply a limit stated elsewhere,
  and a citation that resolves cleanly is not proof it supports the figure
  attached to it. `loaders/load_regime_mongo.py::_verify_reg_o_citations` is
  now a standing guard against a third occurrence; nothing analogous exists
  yet for the PRA side because Task 9 fixed that instance by hand rather
  than adding a permanent check. Worth doing if PRA regime text is extended
  again.
- **EUR-Lex is confirmed blocked** (`docs/known-issues.md` §45) — HTTP 202,
  zero-byte body, on its own homepage, across three user agents. Do not
  re-attempt it for a future EU-sourced regime; go straight to
  legislation.gov.uk (assimilated UK law, point-in-time by URL) or the
  regime's native-jurisdiction publisher.
- **The "omitted" string trap is now a documented pattern**
  (`docs/known-issues.md` §46) — legislation.gov.uk's amendment annotations
  ride along on in-force versions too. Any future point-in-time fetch from a
  consolidated-legislation site must assert on the substantive operative
  text, never on an annotation string describing history.

## Wave 18 carry forward

- **CORRECTED at Wave 19's close: the four Wave 18 bundles named below are
  no longer sitting uncollected.** This bullet originally said the vault
  mirror was stale by four uncollected Wave 18 bundles. Checked at Wave 19
  Task 17 close: `~/.agent-exchange/ccf-dataprep/outbox/` held **zero**
  entries, and every bundle named below (Tasks 9, 10, 11b, Task 17's
  close-out) now appears under `_archive/sent/` — the custodian drained the
  outbox sometime between Wave 18's close and Wave 19's. The binding table
  in `docs/ccf_dataprep_v2.md` remains source of truth regardless of
  collection state; whether the vault mirror has actually been *applied*
  (not merely collected) was not verified here — that is the custodian's
  side of the exchange, not this repo's. Original text, left for context:
  the vault mirror was stale by four uncollected Wave 18 bundles — Tasks 9,
  10, 11b, and Task 17's close-out — and the custodian had drained none of
  them. **Task 17 minted no new term and retracted none** — its bundle
  existed only because the mirrored section gained a correction paragraph
  in Task 11b's fix round that the earlier bundle predates.
- **The peer fabric must be configured for `conditions.py` and
  `partition.py` to run fully.** Unconfigured, **eight** of the twelve Wave
  18 checks in `conditions.py` SKIP — the six floor delegates *and* the two
  `_syndicate_peer_check` counts, which also return `None` (the first
  version of this bullet said six; corrected in fix round 1) — and the two
  `partition.py` fabric arms **FAIL**, deliberately: reporting the local half
  green while the boundary is unobservable is the failure those checks exist
  to catch.
  **On this machine the peer is configured from `~/.bashrc`, not `.env`**,
  and under the `CO_LENDER_PG_*` spellings rather than `.env.example`'s
  `CO_LENDER_PGHOST` family (`ccf/config.py` accepts both). `.env` holds no
  `CO_LENDER` variable at all. See known-issues §39 before changing any of
  them — `load_dotenv()` does not override an already-set variable, so an
  edit to `.env` alone will not take.
- **`validators/test_fabric_isolation.py` is not a pytest file.** `pytest`
  collects nothing from it and reports "no tests ran", which reads like a
  pass. Run it directly: `uv run validators/test_fabric_isolation.py`.
- **`conditions.py` builds one `validators.syndicate.Context` per
  `collect()` run** and shares it across the six Wave 18 delegates, because
  `load_context()` costs 21s. If a future delegate ever MUTATES the context,
  that sharing becomes a defect — the floors today read only.
- **CORRECTED at Wave 19's close: the true gap is ~170x this bullet's
  figure.** This bullet originally said 84 of 37,389 passages carry no
  embedding. Wave 19 Task 4 measured the corpus with a query that also
  catches an explicitly-`null` `embedding` field (the original 84 came from
  `$exists: False` alone, which cannot see `null`) and found **14,289 of
  37,865 passages (37.7%) have no usable vector** — 84 absent plus 14,205
  explicitly `null`, the latter recorded nowhere before now. Full account:
  `docs/known-issues.md` §48. The original 84-passage figure below is
  accurate as far as it goes (Wave 18's twelve agreement passages,
  known-issues §38, and 72 Wave 17 FinCEN-advisory passages, known-issues
  §42) but is a small fraction of the real gap, not the whole of it. Neither
  population is a gap for its own product's §D; both, and the much larger
  null population, are a gap for anything that assumes the passage corpus is
  uniformly embeddable.
- **The co-lender credentials want rotating, and the obvious rotation would
  silently fail** (known-issues §39). Neither is committed. Both are exported
  from `~/.bashrc` (`:173` Postgres, `:175` Mongo), and because
  `load_dotenv()` defaults to `override=False`, writing a new password into
  `.env` would leave the stale export winning and the rotation looking done.
  The **Postgres** one is the consequential one — it reaches the peer's live
  position data; the Mongo one unlocks zero collections. **Nothing was
  rotated: that is Dave's call on a provisioned fabric.**
- **`docs/ccf_dataprep_v2.md`'s §C-mapping note answers Task 7's deferred
  granularity question.** `member_commitment` and `amendment_vote_posture`
  are sub-facets of §C rows 1 and 11 rather than rows of their own; both are
  accounted for, and where each is proven is now written on the mapping
  itself rather than left as a ledger note.

## Wave 17 carry forward

- **The vault exchange bundle `2026-08-25T06-55-08Z-wave17-aml-typology-bindings`
  is SUPERSEDED**, not deleted (bundles are immutable). It listed eleven
  terms including `ex:Alert`; `ex:Alert` was retracted (§C assigns alerts to
  Postgres; Task 13 confirmed no Fluree class was ever created for it).
  Task 18's close-out bundle names it as superseded and states plainly that
  **ten terms stand, not eleven**. See `docs/known-issues.md` #25.
- **FATF is blocked (HTTP 403, measured 2026-08-24).** All four typologies
  anchor to FinCEN instead. FinCEN publishes no `rapid_pass_through`
  advisory — verified across all 194 — so that typology was replaced with
  `shell_company_ownership`, with Dave's approval.
- **`shell_company_ownership` is a satisfied-with-divergence row, not a
  gap.** Its advisory (FIN-2017-A003) describes the concealment mechanism
  through a *residential real estate* case; this estate models no property
  register, so it is extracted at the mechanism level, and the narrowing is
  disclosed in the typology record's own `abstracted_from_advisory` field.
  `validators/spec_coverage.py` records it as satisfied **with the
  divergence rendered under the row** (a `divergence=` field on `Mapping`,
  printed in full as "SATISFIED WITH DIVERGENCE") — not as a gap. Full
  record, including the `rapid_pass_through` substitution and why the
  narrowing is deliberately written down in three independent places:
  `docs/known-issues.md` #29. Until the final fix wave that row said
  nothing about the divergence, so this sentence pointed at a silent tool.
- **`ccf/aml.py` is the legal guard and it is exact, not heuristic.** Two
  successive shortlisting designs were bypassed (token reordering, then
  token substitution) before the shortlisting index was deleted outright.
  `blocks()` now runs a linear exact scan (~375ms/call, ~75s for a 200-party
  run, once, at generation time — never a runtime cost, since this project
  has no serving component). Do not reintroduce a fast path without a test
  proving it agrees with the exact scan on a large adversarial sample. Full
  account: `docs/known-issues.md` #26.
- **The Fluree SPARQL repeated-variable quirk** (`?s <p> ?s` matches every
  edge on this build, not just reflexive ones — use `FILTER(?s = ?o)`
  instead) is recorded at `docs/known-issues.md` #27. Treat any query
  anywhere in this estate that relies on a repeated variable name for an
  equality constraint as unverified until checked the same way.
- **A commit message overstated a test count** — `b7e652a` ("Wave 17 Task
  13") says "15 new tests"; the diff added 13. Recorded, not fixed (the
  commit is already pushed): `docs/known-issues.md` #28.
- **OPEN DESIGN QUESTION — Dave's call, not a defect awaiting a patch.**
  From `l1`'s own assembled view, genuine alerts are still separable from
  noise: `typology_pattern_summary.typology_id` equal to the typology named
  by the `trigger` prefix, OR the phrase `"within the same case"` in the
  trigger, classifies **30/30, precision 1.000, recall 1.000** — two of
  `l1`'s own fields, no external artifact, no threshold. Per-typology
  numeric thresholds inside the trigger text separate too, at margins
  1.5×–16.8×.
  **Already fixed, so do not redo it:** the *prefix* tell is dead — best
  single-prefix precision **0.500**, down from 1.000, with 42
  typology-named false positives added and each verified below its gate.
  **Read this before attempting a fix:** clause 1 is perfect *by
  construction*. The exclusion rule guarantees a typology-named noise alert
  never lands on a party bearing that typology's `matchesTypology` edge,
  because that party is the case subject — so tightening the exclusion, the
  obvious remedy, makes it worse.
  **Closing it needs hard negatives** — ordinary parties whose real
  activity meets a published gate but is legitimate — and
  `generators/generate_aml_transactions.py`'s anti-pattern check forbids
  exactly that for `TYP-STRUCT` by design, to keep the engineered cases
  distinguishable from background. The two properties trade against each
  other. Full record, with every measurement: `docs/known-issues.md` #31.
- **Do not trust a reviewer's numeric claim without measuring it.** One
  reported bypass during Task 5/6's review turned out to be
  `difflib.quick_ratio()` — an upper bound — rather than `.ratio()`.
  Verified independently; the implementer was right to push back.

## Carry forward (pre-Wave-17, still true)

- **`uv run pytest` is broken repo-wide.** Use `uv run --with pytest pytest`.
- **`conditions.py` can still SKIP on a broken query elsewhere in the file
  outside the `ib-opportunity-synthesis`, `aml-typology-match` and
  `syndicated-lending-co-lender` blocks** — only those three have had every
  delegate hardened to FAIL-not-SKIP so far. Read the PASS count, never the
  "0 failed" line.
- A term URL on spec.edmcouncil.org returns HTTP 200 for names that do not
  exist. Verify a binding by grepping the ontology (`dev.fibo-quickstart.ttl`,
  not `prod` — see known-issues §19.8), never by fetching the URL.
- `legal_entity` holds 156 rows: 50 anchors, 3 ABS trusts, 103 GLEIF
  reference entities with no crosswalk row by design. Anything reading it
  unfiltered and expecting 50 is wrong.
- Do not re-fetch. `sources/absee/` holds 4.88 GB already fetched.
- CLAUDE.md's store-assignment table names Mongo db `fibo` and Fluree ledger
  `fibo:main`; the estate uses `fibo_v2` and `fibo-v2`. **This is now
  annotated in CLAUDE.md itself** ("Store identifiers, corrected 2026-08-24")
  rather than silently wrong — read identifiers from `ccf/config.py`
  (`FLUREE_LEDGER_V2`, `MONGO_DB_V2`, `PG_SCHEMA_V2`), never from either
  document's literals.
