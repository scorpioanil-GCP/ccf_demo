# Wave 13a — `credit-memo-context`

**Product.** `credit-risk.credit-memo.v1`, Tier 4, Postgres + Fluree + MongoDB.
**Spec.** `context-products/credit-memo-context`, re-read from the vault 2026-08-22.
**Scope decision.** Wave 13 was split into 13a (this) and 13b
(`kyc-refresh-beneficial-ownership`) on 2026-08-22. The two share neither a
store profile nor a risk profile: this half reuses an established MongoDB
corpus and five already-built prerequisites, while 13b introduces five brand-new
public sources and real-person data. Splitting keeps a defect in either from
holding up the other, matching Wave 11's a/b/c shape.

---

## 1 · What the measurements say, before any design

Every number below was measured against the live stores on 2026-08-22, not
carried from a document. Two of them changed what this wave is.

### 1.1 The wave's real shape: this is a coverage-extension wave, not a fetch wave

§F's first condition is **~20 obligors with full memo-grade coverage across all
five prerequisites**. The five-way intersection is **10**.

| Prerequisite leg | Obligors | Source of the measurement |
|---|---|---|
| `obligor-financial-spread` | 50 | `DISTINCT lei FROM financial_fact` |
| `corporate-family-tree` | 50 | `legal_entity WHERE lei IS NOT NULL` |
| `credit-exposure-rollup` | **15** | `DISTINCT borrower_lei FROM facility` |
| `collateral-and-setoff-coverage` | **13** | `facility ⋈ collateral_pledge` |
| `covenant-cross-reference` | 20 | `covenants_extracted.json`, docs with ≥1 covenant |
| **five-way intersection** | **10** | — |

Dropping one leg at a time shows where the cost sits: without `collateral` it is
11, without `covenant` 13, and dropping any of `spread` / `family` / `exposure`
leaves it at 10 — so **exposure at 15 is the binding leg**, and collateral
tracks it closely.

The consequence is that the headline work of this wave is **not** fetching
10-K/10-Q/EX-99 text. It is extending `facility` and `collateral_pledge` to
about ten further obligors — and specifically to obligors **already inside the
covenant set of 20**, since covenants are the leg that cannot be manufactured
without a filed credit agreement to anchor them to. Facilities, pledges and
exposures are bank-internal by nature and so are legitimately
`synthetic — internal`; the covenant leg is not, which is what fixes the
direction of the extension.

> **A caution this wave must not repeat.** It is tempting to satisfy "~20
> obligors" by counting obligors that have *any* of the five legs. That count is
> 50 and it is meaningless. §F's word is *coverage across all five*, and the
> only honest measure is the intersection. Recording 50 here would be the
> estate's recurring failure — a count that passes while the condition it
> stands for is unmet.

### 1.2 Peer thinness is real, but cohort size alone does not measure it

**This section replaces an earlier version of itself that was wrong, and the
error is worth keeping visible because it is the estate's recurring one.**

The first reading counted cohort sizes over the 1,119 distinct
`(sic, tag, frame)` groups already loaded by Wave 2, found 744 of them holding
exactly one filer, and concluded that §F #4 was already satisfied by natural
`frames` sparsity. That conclusion does not follow, because a cohort can be
small for **two entirely different reasons**:

1. **Real sparsity** — many filers share the SIC, but few tagged that concept in
   that period. This is what the product is about, and what the spec means by
   "arises from the public data's own coverage."
2. **Fetch scope** — few peers were ever fetched for that SIC. This is *our*
   coverage gap wearing the costume of the public data's.

Separating them means comparing each cohort against the number of peers fetched
for its SIC:

| | Cohorts | Share |
|---|---|---|
| Every fetched peer tagged the concept — **no sparsity demonstrated** | **943** | 84% |
| Genuinely thinned by `frames` coverage | **176** | 16% |

So the original 744-of-1,119 figure was measuring Wave 2's fetch scope, not
`frames`. Two further measurements confirm the fetch is the constraint:
`peer_entity` covers **74 SICs against 40 anchor SICs**, but **16 anchor SICs
have no `peer_entity` row at all** — including MASTEC (1623), Super Micro
(3571), Extreme Networks (3576) and CION (SIC empty). Their apparent "cohort of
0" is not a finding about EDGAR; it is a finding about Wave 2.

**Real sparsity nevertheless exists, and is sharp wherever the fetch went deep:**

| SIC | peers fetched | cohort min | cohort max |
|---|---|---|---|
| 7389 | 18 | 7 | 18 |
| 6798 | 16 | 9 | 16 |
| 2834 | 7 | 1 | 7 |
| 3674 | 6 | 1 | 6 |
| 7373 | 5 | 1 | 5 |

SIC 2834 is the cleanest case in the estate: seven peers fetched, and some
concepts in some periods tagged by exactly one of them. That is the product's
mechanism, unengineered.

**What this changes about the wave.** §F #4 asks for cohorts that vary *so that
peer-thinness debt arises naturally*. A memo-grade obligor whose cohort reads 3
because only three peers were ever fetched does not demonstrate that — it
demonstrates our own gap while labelling it `public`, which is a provenance
error of exactly the kind CLAUDE.md rule 1 exists to prevent. So this wave
**must extend the peer fetch** to the real SIC cohort for every memo-grade
obligor before cohort size means anything. Only then is the thin obligor thin
because filers did not tag, and only then is the resulting Context Debt
honestly `public` rather than an artifact relabelled.

**The gate that follows from this.** `validators/memo_debt.py` must assert, per
memo-grade obligor, that its cohort was measured against a **fetched SIC cohort
that is complete** — and must fail where cohort size equals fetched-peer count
for every concept, because that is the signature of a SIC whose peers were never
properly fetched. A peer-thinness number computed over an unfetched SIC is a
check that passes without looking.

### 1.3 Two claims in the inherited documents are wrong; both are corrected here

- **`HANDOFF.md` §8 calls Wave 13 "the first wave to introduce MongoDB."** It is
  not. MongoDB has been live since Wave 6 and currently holds **59 documents,
  15,934 passages, 22 memoranda, 42 research notes**. This wave *extends* an
  established corpus.
- **All 59 documents are EX-10 credit-agreement exhibits.** So while the corpus
  is established, the three document types this product actually names —
  10-K Item 1A/Item 7, 10-Q MD&A, 8-K EX-99 — have **zero** representation. The
  fetch is new even though the store is not.

---

## 2 · §F conditions: status, and what each one needs

| # | §F condition | Now | Needs |
|---|---|---|---|
| 1 | ~20 obligors, five-way memo-grade coverage | **10** | extend `facility` + `collateral_pledge` to ~10 more, chosen from the covenant set |
| 2 | ~60 filed docs across 10-K, 10-Q, EX-99, EX-10 | 59, **all EX-10** | fetch 10-K Item 1A/7, 10-Q MD&A, 8-K EX-99 for the memo-grade set |
| 3 | ~40 internal credit memoranda | 22 | ~18 more, `synthetic — internal` |
| 4 | peer cohorts ≥ 15 and = 3, arising naturally | **not satisfied** | extend the peer fetch to the real SIC cohort for every memo-grade obligor first — 84% of current cohorts measure Wave 2's fetch scope, not `frames`. See §1.2 |
| 5 | ≥ 1 obligor breaching `debt_tolerance` | none | engineered, and see §3 |
| 6 | ≥ 1 cascade case from an unresolvable covenant definition | **carrier exists** | the propagation path, not the carrier |
| 7 | 4 memo types with distinct section templates | none | `synthetic — internal` |
| 8 | ≥ 2 policy versions with distinct effective dates | none | ECOA / Reg O / limit envelopes in Fluree |

**On #6.** `spec-digest.md` records that Wave 6 already loaded ≥ 1 unresolvable
covenant definition and that "that cascade case has an existing carrier." That is
confirmed: `ccf_v2.context_debt` holds a covenant-shaped row reading *"no passage
span contains the extracted offset."* So the **carrier** exists and must not be
regenerated. What does not exist is the **propagation** — the arithmetic by which
that one covenant's debt becomes a named component of the memo's aggregate. The
condition is about the cascade, not the gap, and building another gap would
satisfy a count while missing the mechanism.

---

## 3 · The one condition most likely to be faked, and how it will be gated

§F #5 — **≥ 1 obligor breaching `debt_tolerance`, so fail-closed is observed.**

`debt_tolerance` defaults to 0.3. A breach means aggregate Context Debt > 0.3,
computed per §D step 7 from four contributions: unresolved passage anchors,
peer-set thinness against the expected cohort, signal staleness against
per-section freshness, and **inherited debt from the five prerequisites**.

This is precisely the shape that produced seven defects in Wave 12 — a
threshold gate whose inputs guarantee its own verdict. The specific traps here:

1. **A weighting that makes any obligor breach.** If the component weights sum
   such that a typical obligor lands above 0.3, the condition is met by every
   row and demonstrates nothing. The gate must show a **spread**: obligors
   below tolerance, and at least one above, *from the same weighting*.
2. **A breach driven entirely by one term.** If the breaching obligor is over
   the line because of peer thinness alone, the "cascade from a covenant
   definition" is decorative. The gate must attribute the breach across
   components and show the inherited-covenant term is load-bearing — meaning
   removing it drops the obligor below tolerance.
3. **Debt computed from the generator's own recorded number rather than
   recomputed.** Wave 11a/11b/12 all needed a dedicated recompute-from-loaded-
   data validator (`series.py`, `surveillance.py`, `intraday.py`,
   `reconcile.py`) for exactly this reason. Wave 13a needs the same:
   **`validators/memo_debt.py`**, which recomputes every obligor's aggregate
   debt from the loaded stores and compares against the stored value, rather
   than reading a `designed_debt` column and calling it proof.

**The falsification requirement, stated up front.** Before `memo_debt.py` is
trusted, construct the input that makes it fail and run it: perturb the
inherited covenant-debt term for the breaching obligor and confirm the gate
flips that obligor to compliant. If no perturbation flips it, the gate is not
reading what it claims to read. Match the mutation's scope to the claim's
quantifier — a claim about "≥ 1 obligor" is falsified by moving that one
obligor; a claim about the weighting's spread needs the population moved.

---

## 4 · Store assignment

Unchanged from Q019 §3; nothing here departs from single-writer discipline.

| Store | This wave writes |
|---|---|
| **MongoDB** | 10-K Item 1A/7, 10-Q MD&A, 8-K EX-99 text; their passages with offsets and embeddings; ~18 further internal memoranda |
| **Postgres** | extended `facility` and `collateral_pledge`; memo section templates; Context Debt component weights; relationship/revenue history |
| **Fluree** | ECOA / Reg O / credit-limit policy envelopes with ≥ 2 effective-dated versions |

Peer facts and benchmarks stay where Wave 2 put them (`peer_fact`,
`peer_entity`) and are **read**, not rewritten.

---

## 5 · Decisions taken

**1 · The coverage extension set — confirmed 2026-08-22, and it is not a choice.**
The candidates are constrained to the 20 obligors with an extracted covenant,
since a covenant needs a filed credit agreement to anchor to and cannot be
manufactured. Of those 20, exactly **10 already have both a facility and a
pledge**, and exactly **10 lack one or both** — so reaching §F's ~20 means
extending all ten. The selection criterion (span rich and thin peer cohorts) is
satisfied automatically rather than by choosing.

| Obligor | SIC | peers fetched | has facility | has pledge |
|---|---|---|---|---|
| Pebblebrook Hotel Trust | 6798 | 16 | ✅ | needs pledge only |
| AGILYSYS INC | 7373 | 5 | — | — |
| Sabre Corp | 7370 | 4 | — | — |
| Thermon Group Holdings | 3620 | 1 | — | — |
| B&G Foods | 2000 | 1 | — | — |
| PAYCHEX INC | 8700 | 0 | — | — |
| Super Micro Computer | 3571 | 0 | — | — |
| Container Store Group | 5700 | 0 | — | — |
| MASTEC INC | 1623 | 0 | — | — |
| CION Investment Corp | *(empty)* | 0 | — | — |

Pebblebrook needs only a pledge; the other nine need a facility and a pledge.

**The five zeros are the §1.2 finding in concrete form.** PAYCHEX, Super Micro,
Container Store, MASTEC and CION show a cohort of 0 because **no peer was ever
fetched for their SIC**, not because no comparable filer exists. Extending
coverage to them without extending the peer fetch would put five obligors into
the memo-grade set whose peer-thinness debt is entirely an artifact of our own
gap — and it would be recorded as `public`. The peer fetch therefore precedes
the debt computation in the build order, not after it.

**2 · The fetch stays within the existing 50 anchors.** All 50 already carry
XBRL and family data, so no new anchor screening is implied. §F asks for ~20
obligors and the memo-grade set is drawn entirely from the existing cast.

## 6 · Build order

Each stage depends on the one before; the ordering is not cosmetic.

1. **Extend the peer fetch** to the real SIC cohort for all 20 memo-grade
   obligors, so cohort size means something before anything reads it (§1.2).
2. **Extend `facility` and `collateral_pledge`** to the ten obligors above,
   taking the five-way intersection to 20.
3. **Fetch and segment** 10-K Item 1A/Item 7, 10-Q MD&A, 8-K EX-99 for the
   memo-grade set — the three document types with zero current representation.
4. **Generate** ~18 further internal memoranda, the four memo-type section
   templates, the Context Debt component weights, and relationship history.
5. **Load** the ECOA / Reg O / credit-limit policy envelopes into Fluree with
   ≥ 2 effective-dated versions.
6. **Build `validators/memo_debt.py`**, recomputing aggregate debt from the
   loaded stores, and **mutation-test it before trusting it** — per §3.

---

## 7 · Stage 2 outcome — coverage extension, and what "coverage" means for an unsecured borrower

Executed 2026-08-22. The five-way intersection moved **10 → 15**, and the
remaining five are short for reasons that are findings rather than gaps.

| Leg | At wave start | After stage 2 |
|---|---|---|
| exposure (`facility`) | 15 | **22** |
| collateral (`collateral_pledge`) | 13 | **18** |
| five-way intersection | 10 | **15** |

**Facilities.** `TARGET_FACILITIES` was truncating a score-sorted list, so the
cap now bounds the general fill only and a memo-grade obligor is always
admitted — 45 → 57 facilities, 12 new. The sort order was deliberately left
alone: `rng.uniform` is drawn once per appended row from one seeded stream, so
re-sorting would have redrawn every existing facility's `outstanding_balance`,
and the upsert would have written those changes silently. Verified after the
load: **0 of 45 pre-existing rows changed**.

**Collateral.** Wave 9's chain could not simply be re-run. It mints asset ids
positionally over facilities read `ORDER BY facility_id`, and Wave 13a's new
facilities sort *into* that ordering — the first at index 2 of 57 — so a re-run
would renumber essentially all 81 assets while the loader's
`ON CONFLICT (asset_id)` upsert overwrote each in place with a different asset,
leaving existing pledges pointing at the wrong collateral, silently. That is
the §12.8 family exactly, and it is now recorded in `known-issues.md` rather
than triggered. `generators/extend_collateral_wave13a.py` is additive instead:
ids start above the current maximum and no existing row is read or rewritten.

### The distinction that keeps this honest

Three of the five obligors still outside the intersection — **AGILYSYS,
PAYCHEX, Pebblebrook** — are short only on collateral, and the reason is that
their filed credit agreements **contain no security-interest grant clause at
all**. Verified directly against the document text using Wave 9's own grant
anchor, not inferred: `grant_clause=False` for every one of their facilities.
These are unsecured revolvers, which is the normal shape for investment-grade
names.

So there is a real distinction between two things a naive intersection
conflates:

- **uncovered** — `collateral-and-setoff-coverage` has nothing to say because
  the data was never assembled. A genuine gap.
- **unsecured** — the product has a complete and correct answer, and that
  answer is *"no collateral; the facility is unsecured."* That is coverage.

A credit memo for an unsecured revolver has a collateral section, and it reads
"unsecured." Inventing a pledge for PAYCHEX to lift the intersection to 18
would fabricate a security interest the filed agreement does not grant — a
`public`-labelled claim contradicted by its own source document.

**This is deliberately NOT resolved by redefining the condition.** The
temptation is to declare the memo-grade set to be 18 and move on, which is
the estate's recurring failure mode wearing a reasonable-sounding argument.
Instead: the intersection stays reported as **15 strictly-covered**, and
`validators/memo_debt.py` must carry a **separate, explicitly-named** check
that an unsecured obligor's collateral component resolves to a positive
"unsecured" finding rather than to silence — because those two are
indistinguishable in the data unless something looks, and only one of them is
correct.

**B&G Foods and CION Investment Corp** remain short on exposure: neither has a
credit agreement from which facility terms could be extracted (B&G's document
yields no effective date, CION's no facility type). Both become Context Debt
carriers, which for this product is a use rather than a loss — and CION is now
short on three legs at once (no SIC, so no peer cohort; no facility; no
pledge), making it the most naturally debt-laden obligor in the set.

---

## 8 · CLOSED 2026-08-22 — what was built, and what the numbers are

All seven outstanding items are complete. `credit-memo-context` is registered
in `validators/conditions.py` at **8 passing conditions**, and
`validators/memo_debt.py` carries the arithmetic proof at 6/6 with a six-way
mutation self-test.

| § | Condition | Result |
|---|---|---|
| F1 | ~20 obligors, five-way coverage | 15 strictly covered; 3 more **unsecured rather than uncovered**, 2 short on exposure |
| F2 | ~60 filed docs across 4 types | **77 narrative sections** (20 risk-factor, 19 10-K MD&A, 19 10-Q MD&A, 19 EX-99) + 59 EX-10 |
| F3 | ~40 internal memoranda | **40** |
| F4 | peer cohorts 15+ and 3 | **11 SICs** at ≥15 active, **1** at ≤3 — natural, 176 of 1,119 cohorts genuinely thinned |
| F5 | ≥1 obligor breaching tolerance | **14 breaching, 6 below** — the spread is the point, not the breach |
| F6 | covenant definition cascading | **13 of 14** breaches drop below tolerance without the definition term |
| F7 | 4 memo types, distinct sections | **4 types, 31 rows, 29 distinct section names** |
| F8 | ≥2 policy versions, distinct dates | **2**, the earlier closed the day before the later begins and pointing at it |

**Both §5 commitments were honoured.** `memo_debt.py` recomputes rather than
reads, and its first three mutations all tripped the recomputation check —
which would have *masked* whether the spread and load-bearing checks bite at
all. Three further mutations therefore drive the tolerance while leaving the
stored table alone, and every mutation now names the check it must falsify. The
unsecured-versus-uncovered distinction has its own named check.

**What this wave cost elsewhere.** Extending facilities armed four latent
loaders that derive identity from position in a query result;
`known-issues.md` §13.3 records all four with measured impact. None were
triggered, and none are repaired here — they want their own wave with a
validator that runs every loader twice and asserts the stores are identical.

---

## 9 · Original plan — what remained when §8 was written

**Merged to `main` 2026-08-22 while incomplete, deliberately.** Stages 1, 1b and
2 are self-contained, green, and — critically — **already applied to the shared
live stores**: `facility` holds 57 rows, `collateral_asset` 91, and
`peer_cohort` exists at all only because this branch created it. Leaving that
code on an unmerged branch would mean `main` no longer describes the data in the
databases, which is the divergence `known-issues.md` §12.8 records the cost of.
Code and stores are kept in step; the wave stays open.

**Still outstanding for `credit-memo-context`:**

| § | Condition | State |
|---|---|---|
| F2 | ~60 filed docs across 10-K, 10-Q, EX-99, EX-10 | **not started** — 59 EX-10 only; the other three types have zero representation |
| F3 | ~40 internal credit memoranda | **22 of ~40** |
| F5 | ≥ 1 obligor breaching `debt_tolerance` | not started — see §3 for the traps |
| F6 | ≥ 1 cascade from an unresolvable covenant definition | carrier exists; **propagation not built** |
| F7 | 4 memo types with distinct section templates | not started |
| F8 | ≥ 2 policy versions with distinct effective dates | not started |
| — | `validators/memo_debt.py` + its mutation tests | not started |

**Two commitments made in this document that the remaining work must honour**,
recorded here because they are easy to lose across a wave boundary:

1. **§3** — `memo_debt.py` recomputes aggregate debt from the loaded stores and
   is mutation-tested before it is trusted. A breach driven entirely by peer
   thinness does not satisfy F6; the inherited covenant term must be
   load-bearing, meaning removing it drops the obligor below tolerance.
2. **§7** — a separately-named check that an unsecured obligor's collateral
   component resolves to a positive *"unsecured"* finding rather than to
   silence. AGILYSYS, PAYCHEX and Pebblebrook are the cases; "unsecured" and
   "uncovered" are indistinguishable in the data unless something looks.
