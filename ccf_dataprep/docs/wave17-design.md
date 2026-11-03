# Wave 17 — `aml-typology-match`

**Tier 5 · all five stores · `compliance.aml-typology.v1`**

Status: design approved 2026-08-24 (party origin, graph isolation, and the
build approach settled with Dave before any code was written). Plan and
implementation follow.

---

## 1 · Why this product is different

Every other product in this catalog is free to point at a real company.
This one is not, and the constraint is legal rather than stylistic.

The vault spec carries a hard constraint no other spec carries:

> This product must never be demonstrated against a named real company or a
> real natural person. Publishing a worked example in which a real,
> identifiable entity matches a money-laundering typology is defamatory in
> effect regardless of any "illustrative" or "synthetic data" label attached
> to it, and no disclaimer cures it.

CLAUDE.md rule 2 says the same thing and adds the operative word:
**enforce at generation time, not at review.** A generator that can produce a
forbidden entity and relies on a human noticing has already failed, because
the failure is silent and the reviewer is reading 200 rows.

So this wave has two safety properties that must be *provable*, not asserted:

1. **No AML party corresponds to a real entity or person.**
2. **No path in Fluree connects an AML party to a real entity**, at any
   depth, by any predicate.

Property 2 exists because property 1 alone is insufficient. An invented
party that is invented but *transacts with* Charter Communications still
places a real company one hop from a laundering network. The isolation is
the claim; a validator that fails the build on a single crossing edge is
the proof.

---

## 2 · What already exists

Measured against the live stores on 2026-08-24, not carried forward from
memory.

| Asset | Where | Count | Reused how |
|---|---|---|---|
| OFAC SDN + Consolidated | Postgres `sanctions_entry` | 19,730 | The real half of the fuzzy-match condition |
| Sanctions name variants | Postgres `sanctions_name` | 45,511 | Fuzzy matching surface |
| Screening results table | Postgres `sanctions_screening_result` | 19 | Existing shape, extended |
| GDELT adverse media | Postgres `gdelt_mention` | 951 | Adverse-media element of the catalog |
| ICIJ offshore structures | Postgres `offshore_vehicle` / `offshore_intermediary` / `offshore_administration` | 150 / 40 / 150 | **Shape reference only** — never the entities |
| PSC person layer | Postgres `psc_person` | 210 | **Reused.** See section 4 |
| Beneficial-ownership chains | Postgres `bo_chain` / `bo_chain_hop` | 50 / 169 | **Reused** — already a clean island |
| Officer/director persons | Postgres `person` (numeric keys) | 743 | **Never touched** — these hold roles at real companies |
| Passage machinery | MongoDB `passage` | 37,305 | Same span-offset pattern for advisories |
| Projection plans | Postgres `projection_plan` | 3 | Pattern to follow, not a table to extend |

All three prerequisite products are built and registered:
`kyc-refresh-beneficial-ownership`, `mnpi-wall-enforcement`, and
`credit-surveillance-early-warning`.

The genuinely new work is the typology text layer and the entire invented
population.

---

## 3 · Source feasibility — measured, not assumed

Probed live on 2026-08-24 with a self-identifying user agent.

| Source | Result | Consequence |
|---|---|---|
| FinCEN advisory PDF (direct URL) | **HTTP 200**, `application/pdf`, 636 KB | Fetchable |
| FinCEN advisories index | **HTTP 200**, 59 KB, paginated | Enumerable |
| FATF `Methodsandtrends` | **HTTP 403** | Blocked |

The envelope requires four typologies "each anchored to a real FinCEN or
FATF advisory passage". FinCEN alone satisfies the disjunction, so
**all four typologies anchor to FinCEN advisories** and FATF is recorded as
blocked rather than worked around. If FATF access is wanted later it is an
additive change, not a rework.

**The index is paginated and lists recent advisories only.** The four
typologies this product needs — structuring, funnel account, rapid
pass-through, trade-based — are older than the first page. Enumerate through
the pagination and select by matching the advisory's own subject text.
Do **not** guess advisory numbers: this estate has already been burned twice
by URLs that return HTTP 200 for identifiers that do not mean what the
guesser assumed (`known-issues` on EDM Council term URLs, and the EDGAR
`index.json` omission). Resolve each advisory from the index listing, record
its number and issue date, and fail loudly if a required typology has no
advisory backing it.

---

## 4 · The island

**Decision (Dave, 2026-08-24, revised the same day): fresh companies and
transactions; the KYC person and beneficial-ownership layer is REUSED.**

The first version of this design refused to reuse the PSC person layer, on
the reasoning that its control topologies were traced from real UK filings
and that a re-identification argument survives name replacement. **Dave
challenged it and the challenge was correct — the reasoning was factually
wrong.** Measured against the live tables rather than assumed:

- `psc_person` names come from a **closed invented name bank**
  (`generators/name_bank.py`); every emitted token must appear in it or the
  generator's own gate fails. Nationality and date of birth are **resampled
  from a k-anonymised joint distribution**, not copied. **No real-to-pseudonym
  mapping exists anywhere** — the grouping salt is generated per run and
  discarded with the process, and the source snapshot was deleted after
  derivation. There is no individual behind `PSC-0001`; it is a draw from a
  distribution. The rows already carry `synthetic — engineered`.
- The ownership chains are **not** traced arrangements either. All 50
  `bo_chain` rows anchor on invented offshore vehicles (`ICJ-SPV-*`), every
  hop runs person → holding company → holding company → offshore vehicle
  across invented ids, and **zero chains join a real `legal_entity`**.

So the KYC person and ownership layer is already the clean island this
design proposed to rebuild. Rebuilding it would have duplicated a generator,
produced a second population indistinguishable in kind from the first, and
abandoned §C's "inherited" wording for no gain. It is reused, and §C is
honoured literally rather than as a divergence.

### 4.0 The boundary that check surfaced — two person populations

Verifying the above turned up a hazard worth stating precisely, because
"reuse the persons" is the wrong instruction:

| Population | Key form | Rows | Touches a real company? |
|---|---|---|---|
| PSC-derived | `PSC-####` | 210 | **No** — 0 roles at any real entity; used only in `bo_chain` |
| Officers / directors | numeric (`0001*`, `0002*`, `0000*`) | 743 | **Yes** — 817 `person_role` rows join `legal_entity` |

**Wave 17 may use `PSC-*` person keys and must never use a numeric person
key.** Reusing "the person table" wholesale would silently import 817 paths
from real companies into a laundering network — the precise failure
property 2 exists to prevent. The disconnect validator in section 4.2
enforces this by key form, not by trust.

All ~200 AML **parties** (companies) and all transactions and alerts remain
newly invented. Only the person and ownership-chain layer is inherited.

**Identifier format.** AML parties carry synthetic identifiers in the
estate's established visibly-distinct form (the `SYN-` prefix with hyphens,
which no real 20-character GLEIF LEI can collide with). Their instance URIs
stay under the existing `http://example.org/fibo/` pattern per the IRI
contract.

### 4.1 Enforcing property 1 at generation time

Every generated party name is checked, before it is written, against every
real-entity name the estate holds:

- `legal_entity` legal names and all known variants (156 rows)
- `sanctions_entry` / `sanctions_name` (19,730 entries, 45,511 name forms)
- `person` (953), `psc_person` (210), `person_name_variant`
- `peer_entity`, `registry_company`, `institutional_holder`

A candidate that matches any of them above a conservative similarity
threshold is **rejected and regenerated**, not flagged. The check runs
inside the generator, so a forbidden name cannot reach a store at all.

**The one deliberate exception is the OFAC fuzzy-match condition**, which
requires exactly one invented party to resemble a real sanctions entry at
moderate confidence. That party is generated through a separate, explicitly
named path with its intended match recorded, so the exception is a single
declared case rather than a hole in the guard. The guard must **prove** it
would have rejected that name had it arrived by the ordinary path — a check
that cannot demonstrate its own teeth is decoration, and this estate has
recorded seven instances of exactly that.

### 4.2 Enforcing property 2 after load

**Decision (Dave, 2026-08-24): hard disconnect, validated.**

A validator walks Fluree from every AML party across every predicate, at
unbounded depth, and asserts it never reaches a **real** entity. The
permitted neighbourhood is the AML parties plus the inherited `PSC-*` and
`ICJ-SPV-*` / holding-company island, which section 4.0 establishes touches
no real company; anything else is a violation. Reaching a numeric person key
is a violation for the same reason a real LEI is. It also walks the other direction — from the 50 real anchors
outward — because a check that only looks one way cannot see an edge whose
subject is the real entity. Both directions must come back empty, and the
validator must be shown to fail on a deliberately planted crossing edge
before it is trusted.

---

## 5 · Store assignment

Follows §C exactly. Each store is authoritative for its slice; nothing is
duplicated for convenience.

| Store | Owns | Contents |
|---|---|---|
| **Postgres** | `E` | Parties, transactions, alerts and prior-alert history, sanctions entries (existing), screening results, adverse media, projection plans |
| **Fluree** | `R`, `P`, `T` | `transactedWith` network, ownership chains, typology structural patterns, filing-posture versions with effective dates, disposition rules |
| **MongoDB** | `L` | FinCEN advisory text with passage spans, SAR narratives |
| **SQLite** | `P` | SAR confidentiality classification — deliberately outside the enterprise platform |
| **Neo4j** | — | Not used |

### 5.1 New Postgres tables

Named with an `aml_` prefix so the island is legible in a 103-table schema
and so no existing table is widened. This follows the Wave 16 precedent:
when `projection_plan` collided, a separate `ib_projection_plan` was created
rather than overloading the shared table.

- `aml_party`, `aml_transaction`, `aml_alert`, `aml_alert_link`
- `aml_projection_plan` (three rows: `l1`, `l2`, `examiner`)

**Positional identity.** Every one of these tables is keyed by its own
stable id, never by a row's position in a query result. This estate has
recorded five instances of the positional-identity defect, most recently in
Wave 16's note-key repair. Ids are assigned from the row's own content, so
inserting a row cannot silently re-key its neighbours.

### 5.2 SQLite

One new table, `sar_classification`, taking the departmental store from five
objects to six (four business tables, one schema-meta table, plus this one). The point of putting it here is architectural: the policy read must
reach a small, locally-maintained file before anything else runs, exactly as
`mnpi-wall-enforcement` does with `restricted_list`.

### 5.3 New bindings

The typology, posture, alert and transaction vocabulary does not exist in
the current binding table. Every new term is verified absent from FIBO
before use — against `dev.fibo-quickstart.ttl`, never `prod`, which omits
40 Provisional modules — with a positive control required to fire first, and
never by fetching a term URL, which returns HTTP 200 for names that do not
exist. New bindings go into `docs/ccf_dataprep_v2.md` first, then the vault
mirror is flagged and a bundle sent.

---

## 6 · The demonstration

Extract the typology patterns from the advisories first, then build the
ordinary population, then inject the engineered cases into it.

**Order matters.** Patterns come from the advisories, so every typology
match cites the passage that defines it — anchoring is true by construction
rather than asserted afterwards. The ordinary population comes next, so the
~120 noise alerts are genuine noise and precision is measurable rather than
assumed. The engineered cases go in last, into a population that already
exists, so they sit among real activity instead of being the only thing
present.

Everything in this product is `synthetic — engineered` or
`synthetic — internal`. The only `public` elements are the advisory text,
the sanctions entries, and the adverse media. No part of this demonstration
is emergent, and the design must not describe it as though it were.

---

## 7 · The floors that cannot be counted into existence

The envelope's headline figures — ~200 parties, ~5,000 transactions, ~150
alerts — are **shape**, per Dave's standing ruling that §F scale numbers
describe a demo dataset rather than a target. The following are **floors**,
because each one makes a specific behaviour demonstrable and hitting the
count while missing the condition is a failure:

| # | Floor | What proves it |
|---|---|---|
| 1 | ≥ 4 typologies, each anchored to a real advisory passage | Resolve every passage span and confirm the advisory number and issue date; a typology with an unresolvable anchor fails |
| 2 | ≥ 1 network requiring **depth 3** | Run the traversal at depth 2 and depth 3 and assert the pattern is absent at 2 and present at 3 — an ordering claim, not a count |
| 3 | ≥ 2 posture versions where a disposition **flips** permitted → forbidden | Evaluate the same disposition under both `as_of` values and assert the two answers differ |
| 4 | ≥ 3 SARs invisible to at least one principal | Assemble from an unauthorized perspective and assert no indication of existence leaks — including absence of the field, not merely a null |
| 5 | ≥ 1 invented party fuzzy-matching a **real** OFAC entry at moderate confidence | Recompute the similarity live and assert it lands in the intended band — not too low to be a match, not so high it is a duplicate |
| 6 | ≥ 1 alert whose three renderings differ in **assembled content** | Compare the three projections and assert the element sets differ, not the formatting |

Plus the two safety properties from section 1, which are floors of a
different kind: they must hold absolutely rather than meet a threshold.

Each floor is recomputed from the stores on every run. None reads a stored
score, a cached rank, or a boolean flag. This is a build-time validator, not
an operator: it registers nothing, composes into no plan, serves no
principal, and emits no contract.

---

## 8 · Load order

Ontology and bindings → advisory fetch and passage extraction → typology
patterns → parties → ownership chains → transactions → network edges →
alerts and prior-alert history → posture versions and disposition rules →
SAR narratives and classification → projection plans → validators.

Each stage depends on the one before. Loaders are idempotent and safely
re-runnable; idempotency is proved by naming a value that must survive a
second run, never by comparing a row count, which cannot see a field being
reset.

---

## 9 · Definition of done

1. Every §C element exists, in the store §C names, with its provenance class
   recorded. §C's "inherited from kyc-refresh-beneficial-ownership" is
   satisfied literally by the reuse in section 4, not as a divergence.
2. Correlation keys resolve: `alert_id` and the synthetic party identifiers
   join across all five stores.
3. All six floors and both safety properties are satisfiable by a real query
   against the loaded data.
4. Single-writer discipline holds; nothing is duplicated into a store that
   does not own it.
5. New terms are bound in `docs/ccf_dataprep_v2.md`, verified against the
   EDM Council source, and the vault mirror flagged and a bundle sent.

---

## 10 · Open

- **FATF is blocked (403).** All four typologies anchor to FinCEN instead.
  Revisit only if a fifth typology is wanted that FinCEN does not cover.
- **Advisory selection is not yet made.** The four required typologies must
  be matched to specific advisories by enumerating the paginated index and
  reading subject text — not by guessing advisory numbers. This is the first
  implementation task and its output should be reviewed before the text
  layer is built on it.
- **Similarity threshold for the name guard** is stated as "conservative"
  and needs a measured value. It should be calibrated against the known
  false-positive pair this estate already carries, so the threshold is set
  from evidence rather than taste.
