# Wave 20 — closing the three T1 gaps before rung 1 is built

**Why this wave exists.** `counterparty-reference-snapshot` is rung 1 of the
build ladder and every other product inherits its contract machinery. Its §C
carries three real, named absences (`known-issues.md` §55). The SDK side asked
whether to build rung 1 against the estate as it stands; the answer was to
close all three first, because the one thing T1 exists to prove is that the
contract fires.

**Order: 3 → 1 → 2.** Gap 3 is mostly a load and gives a quick win; gap 2 is
last because it needs a schema decision that is now made (below).

---

## Rulings — Dave, 2026-08-28

These are decided. They are recorded here because **gap 2's migration was
gated on them being written down** before it starts.

### Gap 3 · second address
- **Close it.** Load the 103 subsidiary HQs already on disk; fetch the 50
  anchors from the proven GLEIF path; add columns; **label** headquarters vs
  legal domicile.
- *"An unlabelled triple is a served-data defect."*

### Gap 1 · jurisdiction entitlement
- **Close it as a recomputed difference, not a populated column.**
- A `jurisdiction` column on `principal` is **necessary and not sufficient**.
  The **visible entity set** must differ between principals.

> **Citation corrected 2026-08-28.** This plan first cited **§F**. That is
> wrong for this spec and wrong in the exact way this repo had already
> written up: `counterparty-reference-snapshot` is on spec-standard-v0-3,
> where **§F is "Source binding & readiness"** — a `[TBC]` ownership table
> that requires nothing of the kind. The envelope meaning of §F belongs to
> the superseded Q019 form. Verified against the live spec's own headings.
>
> **Where the requirement actually lives:** §B binds the T1 policy as
> *"Entitlement scope only — JURISDICTION VISIBILITY per calling principal"*,
> and §D's **Validation gates** line names **suppression silence** among six
> gates. Those two are the basis; the set-difference check is how we make
> them checkable.
>
> **And a floor that no longer exists.** The *"3 principals with differing
> jurisdiction entitlement"* figure came from Q019 §F. **v0.3 states no such
> number.** We keep 3 as *our own* sufficiency choice — it is the smallest
> set that shows pairwise difference is not a coincidence of two — but it
> must be recorded as ours, not cited as the spec's.
- Build-time check must walk the policy binding and assert **set inequality**,
  and that **at least one entity is visible to A and not to B**.
- *"A column with distinct values and a no-op Policy Operator is the 'counted
  but not created' failure in T1."*

### Gap 2 · no-LEI entities
- **Schema: a separate `internal_client` table keyed on `internal_client_id`.**
  Additive; matches §C's "internal client master"; keeps `legal_entity.lei` as
  the GLEIF identity.
- **Do NOT make `legal_entity.lei` nullable** — 9 foreign keys reference that
  table, and it is the positional-identity defect class.
- **`crosswalk.lei` becomes nullable** so an internal client can exist without
  an LEI. Necessary, not sufficient alone.
- **Provenance: `synthetic — internal`, per §C.** *(Dave, 2026-08-28 — this
  OVERRIDES the earlier `synthetic — engineered` ruling.)*

> **Why the call changed.** §C's own row assigns this element the class
> **`synthetic — internal`**:
>
> > `| Internal client identity for no-LEI entities | internal client master | synthetic — internal | Postgres | E |`
>
> The ruling says `synthetic — engineered`, on the reasoning that public
> sources cannot produce a no-LEI entity. Both readings are defensible —
> CLAUDE.md defines engineered as *"invented deliberately to create a
> condition public data will not supply"*, which fits; but §C is one of the
> two sections this project treats as authoritative, and it states a class
> outright.
>
> **Two further facts, measured 2026-08-28, that neither side had:**
> `ccf_v2.legal_entity.provenance` holds exactly one distinct value across
> all 156 rows — `public` — and this estate keeps invented entities in a
> **separate `engineered_entity` table (125 rows)**. So the local convention
> appears to be that engineered things live in their own table rather than
> being labelled inside the reference tables. A new `internal_client` table
> is unconstrained by either precedent, which is why this is cheap to settle
> now and expensive to change after the rows exist.
>
> **The resolution.** `synthetic — engineered` would shelve operational
> identity alongside the typology and insider inventions in
> `engineered_entity`. **Wrong shelf.** A no-LEI internal client is not an
> invented *pattern*; it is identity from the internal client master that §C
> already names. `synthetic — internal` carries both facts at once: not a
> public fact, invented here because public sources cannot supply a no-LEI
> row — **and** belonging to the internal-master axis rather than the
> engineered-pattern table.
- **`lei` IS NULL — no `SYN-` LEI**, or the demonstration defeats itself.

---

## Measured starting state (2026-08-28)

| Fact | Value |
|---|---|
| `legal_entity` rows | 156, **0** with a null `lei` (`lei` is the PK, NOT NULL) |
| `crosswalk` rows | 53, `lei` NOT NULL + UNIQUE, PK is `internal_client_id` |
| Foreign keys referencing `legal_entity` | 9 |
| `principal` rows | 4 — coverage banker, EU KYC analyst, research analyst, trader |
| `principal` jurisdiction column | **none** |
| Distinct `legal_jurisdiction` values | 34 (US-DE 52, GB 15, US-MD 8, IN 8, CA 6, …) |
| Subsidiary HQ addresses already on disk | **103 of 103** in `sources/gleif_l1/subsidiaries_l1.json` |
| Anchor HQ addresses on disk | **0 of 50** — the retained pages are explicitly non-anchor |
| Files referencing `address_*` columns | 6 |

---

## Tasks

### Gap 3 — headquarters vs legal domicile
1. **Rename `address_*` → `legal_address_*`** on `legal_entity`, and add
   `hq_address_country / _city / _region`. Rename rather than leave ambiguous:
   the existing triple IS the legal domicile, and the source field names in
   `sources/screening/anchors_final.json` already say so. 6 files to update.
2. **Load the 103** subsidiary HQs from `sources/gleif_l1/subsidiaries_l1.json`
   (`hq_country/_city/_region`, already fetched and 103/103 populated).
3. **Fetch the 50 anchors'** Level 1 HQ from
   `https://api.gleif.org/api/v1/lei-records`, the endpoint
   `generators/fetch_gleif_subsidiaries.py` already uses. Persist under
   `sources/gleif_l1/` with a retrieval date, per the source convention.
4. **Validator:** the §C row asserts BOTH addresses present, and that they are
   distinguishable. A row where HQ == legal is fine and real; a row where
   nothing records which is which is the defect.

### Gap 1 — jurisdiction entitlement
5. **`principal.jurisdiction_scope`** — the set of jurisdictions a principal
   may see. Provenance `synthetic — internal` (entitlements are bank-internal
   by nature, CLAUDE.md rule 1).
6. **Values for ≥ 3 principals that genuinely differ**, chosen against the real
   distribution above so the resulting sets cannot coincide.
7. **The check that matters:** recompute the visible entity set per principal
   from `legal_entity.legal_jurisdiction` ∩ scope, and assert
   (a) the sets are pairwise unequal for at least 3 principals, and
   (b) at least one entity is visible to A and not to B.
   **Recomputed every run — no stored visibility flag, no cached set.**

### Gap 2 — no-LEI entities *(starts only now that the rulings above are logged)*
8. **`internal_client`** table, PK `internal_client_id`, carrying the identity
   attributes §C names for entities the client master owns.
9. **`crosswalk.lei` → nullable**, so an internal client can exist with no LEI.
10. **Generate the population** — privately-held middle-market borrowers,
    `lei IS NULL`, provenance `synthetic — engineered`, labelled as invented to
    demonstrate §D's exclusion.
11. **Validator:** a no-LEI client resolves to identity attributes, and the
    LEI-keyed crosswalk floors do **not** silently cover it — the failure that
    hid this gap in the first place was floors keyed on the very property the
    population lacks.

---

## The trap this wave must not fall into

Every one of these three can be "closed" in a way that passes and proves
nothing: a populated column with a no-op operator, an HQ address copied from
the legal one, a no-LEI table nothing queries. `known-issues.md` §53 and §54
are both instances of exactly that shape, found the same day this plan was
written. **Each gap's check must recompute from the stores and be shown to go
red on data that should fail it.**
