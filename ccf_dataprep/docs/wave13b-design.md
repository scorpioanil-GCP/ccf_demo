# Wave 13b — `kyc-refresh-beneficial-ownership`

**Product.** `compliance.beneficial-ownership.v1`, Tier 4, Postgres + Fluree + MongoDB.
**Spec.** `context-products/kyc-refresh-beneficial-ownership`, re-read from the
vault 2026-08-22.
**Prerequisites.** `corporate-family-tree`, `counterparty-reference-snapshot` —
both built.

---

## 1 · Measured state, 2026-08-22

### 1.1 The vocabulary is bound; nothing is asserted against it

Every FIBO term this product needs is **already in the binding table**, under
its own `BENEFICIAL OWNERSHIP` and `PERSON` sections
(`docs/ccf_dataprep_v2.md`) — bound when the Wave 3 binding gaps closed. So
13b is a **materialization** wave, not a binding wave. Measured against the
live ledger:

| Term | Assertions |
|---|---|
| `fibo-fnd-oac-own:owns` | 466 |
| `fibo-fnd-rel-rel:controls` | **3** |
| `fibo-be-oac-cown:hasBeneficialOwner` | **0** |
| `fibo-be-oac-cown:isBeneficialOwnerOf` | **0** |
| `cmns-id:isIdentifiedBy` | **0** |
| `fibo-fnd-aap-ppl:hasPersonName` | **0** |
| `owl:sameAs` | **0** |
| `a fibo-be-oac-cown:BeneficialOwnership` | **0** |
| `a fibo-be-oac-cctl:SignificantShareholder` | **0** |
| `a fibo-fnd-aap-ppl:PersonName` | **0** |

503 `cmns-org:LegalEntity` and 704 `fibo-fnd-aap-ppl:Person` nodes exist, so
the graph has both endpoints — what is missing is every edge and reification
between them.

> **One spec caveat is already stale.** The §B currency note records `controls`
> at **zero** assertions as of 2026-08-17. It now has **3** (Wave 11b's
> golden-share / dual-class / board-rights engineering). The note's *advice* —
> match both `owns` and `controls`, because matching `controls` alone returns
> almost nothing — remains exactly right, and 3-against-466 makes it more
> pressing rather than less. Flag for the vault mirror.

### 1.2 Three §F conditions are already satisfied — by the wrong data

`validators/conditions.py` reports, from earlier waves:

| Condition | Reported | But |
|---|---|---|
| cross-shareholding cycle | 3 / 3, engineered and labelled | jurisdiction-spanning **not** established |
| person name variants | 571 / 5 | **all 571 are `source='def14a'`, `rendering='display_order'`** |
| false-positive person pair | 1 / 1 | drawn from the SEC roster, not across registries |

The name-variant number is the one to distrust. §F asks for variants **across
sources**, with **≥ 2 transliteration cases** — the spec's own example is
*"Robert J. Smith"* in a UK PSC filing against *"Bob Smith"* in a US registry
against *"SMITH, ROBERT JAMES"* on a sanctions list. What exists is 571
variants from **one** source in **one** rendering, all Latin-script US
proxy-statement names. Zero transliteration cases. Counting 571 against a floor
of 8 would satisfy the count and miss the condition entirely — the estate's
recurring failure, and it is pre-loaded here waiting to be repeated.

**So 13b's variant work is not "add a few more". It is the first variants this
estate will hold that cross a registry boundary at all.**

---

## 2 · Person data — the rule that governs everything else

**CLAUDE.md rule 3, and the spec agree: PSC records concern real, named, living
people.** The structural lesson survives pseudonymization completely; the
privacy exposure does not survive publication. This repository is a teaching
artifact that is privately distributed, which makes publication a live risk
rather than a theoretical one.

**Approved by the user 2026-08-22: fetch, and pseudonymize at ingestion.**

### 2.1 What "at ingestion" has to mean

Pseudonymizing after loading is not pseudonymizing. The rule this wave holds
itself to:

> **No real PSC person name is written to any store, any artifact under
> `sources/`, or any file this repository tracks — at any point, including
> intermediate state.**

Concretely:

1. The PSC bulk file is fetched to a **scratch path outside the repository**
   and is **never committed**. Its retrieval provenance — URL, snapshot date,
   sha256, record count — is recorded; its contents are not.
2. Pseudonymization happens in the **same pass that reads it**. The reader
   emits structural features and a synthetic identity; the real name is never
   returned by the parsing function at all, so no downstream caller can
   accidentally persist it.
3. **No real→pseudonym mapping is written anywhere.** A mapping table is a
   re-identification key, and keeping one would reintroduce precisely the
   exposure this removes.
4. The raw file is deleted after the derivation runs.

### 2.2 What must survive pseudonymization, or the product teaches nothing

The `sameAs` resolution problem is about name **shapes**. Synthetic names
carrying the same shapes teach it identically — but only if the shapes are
actually carried across:

| Preserved | Replaced |
|---|---|
| name-variant patterns — initials, ordering, particles (`van`, `de`, `al-`), hyphenation | the name itself |
| **script and transliteration structure** — a name whose source script admits several Latin renderings must map to a synthetic name that also does | the specific characters |
| nature-of-control codes, verbatim (they are a public controlled vocabulary, not personal data) | — |
| DOB month/year **distribution**, nationality **distribution** | the individual's DOB and nationality |
| ownership-graph shape, including any cycles found | company and person identities |

Point 2 is the one that is easy to lose. Replacing a Cyrillic-origin name with
"John Smith" destroys the transliteration case that §F #5 explicitly requires,
and the loss is invisible — the count still reads 200.

---

## 3 · Sources — verified reachable 2026-08-22, and one substitution

| Source | Status | Note |
|---|---|---|
| **UK Companies House PSC snapshot** | ✅ 200 | `psc-snapshot-2026-08-22`, 32 parts × ~73 MB. **One part is ample** for ~200 person nodes — depth, not breadth |
| **UK Companies House company/officer bulk** | ✅ 200 | |
| **OFAC SDN + Consolidated** | ✅ 200 | SDN.XML 28.8 MB, CONS_ADVANCED.XML 4.5 MB |
| **ICIJ Offshore Leaks** | ✅ 200 | `full-oldb.LATEST.zip`, 72 MB |
| **OpenCorporates** | ❌ **401** | Requires a paid API token. No longer the free public source §C assumes |
| **GLEIF Level 2 (substitute)** | ✅ 200 | 485,276 relationship records, 23 MB, published daily |

**The substitution, and why it is an improvement rather than a concession.**
The user approved replacing OpenCorporates with GLEIF Level 2 relationship
records for the *"corporate ownership records across jurisdictions"* element.
GLEIF is keyed on **LEI**, which is already this estate's correlation key —
so it joins to everything without a new crosswalk, where OpenCorporates would
have needed one built on company number and jurisdiction. `generators/
fetch_gleif_relationships.py` already exists from Wave 3 and fetched 309 edges
across 153 entities for the anchor cast; 13b widens that draw rather than
inventing a second mechanism.

**This is a documented deviation from §C and must be sent to the vault** —
the spec presents OpenCorporates as free and bulk-downloadable, which is no
longer true. Punch list, not a silent swap.

---

## 4 · §F conditions: status and plan

| # | Condition | Now | Plan |
|---|---|---|---|
| 1 | ~50 anchor entities with chains reaching natural persons | 0 chains reach a person | materialize `hasBeneficialOwner` from the pseudonymized PSC layer |
| 2 | ~200 pseudonymized person nodes with real PSC patterns | **0** | §2 |
| 3 | ≥ 3 chains reaching depth 5+ | GLEIF reports **0** anchors at depth ≥ 4 | engineered, labelled — the public hierarchy is genuinely shallow |
| 4 | ≥ 2 engineered cycles, ≥ 1 cross-jurisdictional | 3 cycles exist | verify jurisdiction-spanning; engineer one if not |
| 5 | ≥ 8 variant persons, ≥ 2 transliteration, ≥ 1 false positive | 571 variants but **one source, zero transliteration** | §1.2 — first cross-registry variants in the estate |
| 6 | ≥ 1 person on a sanctions list below certainty | 0 | OFAC fetch + deliberate sub-certainty match |
| 7 | ≥ 2 entities with EU-resident persons | 0 | residency constraints in Fluree |
| 8 | ~30 KYC docs, ≥ 1 contradicting the registry | 0 | MongoDB, `synthetic — internal` |

---

## 5 · The conditions most likely to be faked, and the gates that must bite

Three of these have the shape that produced Wave 12's seven defects.

**#5, the false-positive pair.** A pair engineered to fuzzy-match will match
under whatever scorer wrote it. The gate must run the **resolution scorer the
product actually uses**, show the pair scoring above the merge threshold, and
show that they are nonetheless different people on corroborating evidence
(DOB month/year, nationality). A gate that asserts "a false-positive pair
exists" by reading a `is_false_positive` flag is decoration — it cannot fail.

**#6, the sanctions match below certainty.** "Below certainty" is a band, not a
boolean. If the engineered match scores 0.99 or 0.30, the review queue is not
exercised — it is bypassed or trivially rejected. The gate must assert the score
falls **strictly between** the auto-clear and auto-reject thresholds, and those
thresholds must come from the loaded policy rows, not from constants in the
gate.

**#7, EU-resident invisibility.** The claim is that a principal without EU
entitlement never sees EU-resident person nodes materialize. The gate must
**run the same traversal twice under two principals** and diff the result. A
check that counts EU-resident persons and separately counts entitlements proves
nothing about whether policy actually filters — that is a check that passes
without looking, and residency containment is a **legal** claim here, not a
cosmetic one.

**The falsification requirement, stated up front.** For each of the three:
construct the input that makes the gate fail and run it. If none exists, the
gate is decoration. Match the mutation's scope to the claim's quantifier — a
claim about "≥ 2 transliteration cases" is not falsified by perturbing one
Latin-script name.

---

## 6 · Build order

1. **OFAC** (smallest, no privacy surface) — SDN + Consolidated into Postgres.
2. **GLEIF Level 2** widened draw — cross-jurisdiction ownership.
3. **PSC** — fetch to scratch, pseudonymize in the reading pass, derive the
   person layer, delete the raw file. §2.
4. **ICIJ Offshore Leaks** — intermediary relationships into Fluree.
5. **Resolution layer** — `identifiedAs` / `sameAs` with per-resolution
   confidence, including the transliteration and false-positive cases.
6. **Policy** — jurisdictional thresholds, residency constraints, refresh state.
7. **KYC documents** — MongoDB, with the registry contradiction.
8. **Engineered** — depth-5 chains, the cross-jurisdictional cycle.
9. **`validators/beneficial_ownership.py`** — with the three gates of §5,
   mutation-tested before being trusted.

---

## 7 · Open question for the user

**Retention of the raw PSC file.** §2.1 commits to deleting it after
derivation and never committing it, so the repository holds only pseudonymized
output plus retrieval provenance. That is the safe default and needs no
decision. The one thing worth confirming: a **re-run** then requires
re-downloading 73 MB, and the snapshot is dated — Companies House publishes a
new one and removes the old, so an exact re-derivation may become impossible.
The alternative is retaining the raw file **outside the repository** at a
recorded path. Assumed: delete, accept the re-derivation risk, because a
retained file is a standing exposure and the pseudonymized artifact is what
everything downstream reads.
