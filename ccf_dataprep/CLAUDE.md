# CLAUDE.md — ccf_dataprep

## Interactions with Dave

Keep the dialog with Dave as concise as required to communicate the response
and options. Minimize technical jargon and speak to Dave in plain English.
Avoid verbose explanations filled with technical jargon — just get to the point.

## Mission

**Produce the source data.** This project builds and loads the synthetic and public-derived datasets that back a catalog of Commercial Banking / Corporate & Investment Banking **Context Products**, across five datastores.

That is the whole job. You are the data supply chain. Someone else consumes what you produce.

## Explicitly out of scope

Do not build, design, or reason about any of the following. If a task seems to require them, you have misread the task.

- **The CCF SDK** — its API, its client surface, its examples. This project knows nothing about it and does not need to.
- **Context Product assembly at runtime** — operators, projection, contracts, TTL enforcement, replay. Those are consumed downstream.
- **Agent code of any kind.**

The specifications you work from contain an "Assembly Recipe" section describing runtime behaviour. **Read it only to understand what the data must support.** Never implement it.

### What "operator" means — and what it does not

Added 2026-08-24, because this rule was misread once and would be again.

An **Operator** is a *runtime SDK entity*. Per the vault's own definition
(`cognitive-context-fabric/ccf-architecture`, L4): typed, composable primitives —
**Traversal, Temporal, Policy, Similarity** — resolved through an operator
registry, topologically ordered by the Operator Plan DAG Generator, executed in
the **Data Plane**, and composed as `ContextProduct = Π ∘ Traversal ∘ Temporal ∘
Policy ∘ Similarity` to serve a principal at request time. Not all Context
Products are formed ahead of time; operators are how the fabric assembles them
dynamically from this estate.

**That is the thing you must not build.**

A **build-time validator is not an operator**, even when it computes something an
operator would also compute. It does not register, does not compose into a plan,
does not serve a principal, does not emit a contract, and does not run at request
time. It runs against the loaded estate and answers one question: *does this data
support what the spec claims?*

The distinction matters because some `≥ N` conditions are only provable by
computation. `ib-opportunity-synthesis` §F requires one prospect to rank top-3
for the M&A originator and outside the top-20 for the DCM banker **from identical
signals**. That is a claim about ordering, and no count can establish it. The
per-perspective **ranking weights are ours to produce** — §C assigns them to
Postgres as `synthetic — internal` — and shipping a weight vector without ever
confirming it separates the two orderings is exactly the "counted but not
created" failure this file warns about elsewhere.

So: **never build what the SDK invokes at runtime; always check your own
arithmetic.** A validator that recomputes from the stores on every run — reading
no stored score, no cached rank, no boolean flag — is the check, not the product.

---

## Where the requirements live

The authoritative specifications live in a separate Obsidian vault, exposed through the **`obsidian-vault` MCP server**. It is registered at **user scope**, so this project inherits it automatically — confirm with `claude mcp list`.

```
get_response("Q019")                                     # the authoring standard — read this first
list_articles("context-products")                        # 21 product specs, ordered simplest-first
get_article("context-products", "corporate-family-tree")  # one full spec
```

If the server is ever unavailable, stop and ask for `Q019` plus the `context-products` articles to be exported into `docs/specs/`. Do not proceed from memory or inference — the specs contain per-element store assignments and volume targets you cannot reconstruct.

**Two sections of each spec are yours:**

- **§C · Data Catalog** — every raw element, its provenance class, and its target datastore
- **§F · Manufacture envelope** — volumes, and what must be *engineered* rather than fetched

§A, §B, §D, and §E are context. Read them to understand *why* an element is needed; do not act on them.

### Talking to the vault and to peers — the board

**One channel: `contribute()`.** Vault ruling of 2026-10-10
(`contrib/vault/ruling-2026-10-10-exchange-retired`): the filesystem exchange at
`~/.agent-exchange/` is **retired**. Nothing drains an outbox, the vault no
longer writes an inbox, and there is no relay. Do not write there; the
session-start hook warns if anything appears in the old outbox.

`contribute(topic, name, title, body, summary, kind=…)` writes
`contrib/ccf-dataprep/<name>.md`, readable by every agent — the custodian and
`ccf-sdk` alike — the moment it returns. Identity comes from the working
directory and is **not** a parameter. `topic` is the SUBJECT, never the
recipient. `kind=finding|measurement|correction` **requires** `measured_against=`
and `reproduce_with=` or the write is refused — use `kind="note"` when nothing
was measured. Names starting with `_` are refused. `kind="ruling"` is the
vault's alone.

Every contribution follows four rules:

- **Open the body with `Affects:`** naming the vault paths you believe change,
  e.g. `Affects: wiki/context-products/content/fibo-iri-binding.md`.
- **State what you remove**, not only what you add. A submission once reported
  123 additions and was silent about 38 deletions.
- **Large artifacts go by commit, not by copy.** Commit and push here, then
  contribute a `note` naming the repository, commit and path.
- **Withdraw or replace with `supersedes="contrib/ccf-dataprep/<old-name>.md"`.**
  Only your own documents. When you read anyone's contribution, **check
  `superseded_by` first** and act on the newest.

**Reading the board.** `.claude/settings.json` runs the vault's read-only
`notify.py` at session start, printing `=== BOARD ===`: new rulings first, then
peers' new contributions, then wiki articles changed since you last looked.
Being listed counts as being shown — the cursor advances when the hook runs —
so to see something again use `query(root="contrib", since="<date>")`,
`list_contributions(agent=)` or `get_article(name=, root="contrib", agent=)`.
If the vault is unreachable the hook prints nothing; absence of the block is
not evidence of an empty board.

**Citing.** A peer's `contrib/` is published on its own authority and is **not
adjudicated** — say *"ccf-sdk states X"*, never *"the vault says X"*. A
`kind: ruling` from `vault` is the custodian's decision: *"the vault ruled X on
<date>"*. Only `wiki/` and vault rulings bind. Disagree with a ruling by
publishing a `note` or `correction`, never by acting against it.

The full contract is **section 5 of the `obsidian-vault-access` skill**
(registered at user scope). Read it before your first contribution in a session.

> History: the exchange ran 2026-08-17 → 2026-10-10. References to
> `~/.agent-exchange/…/outbox/` in `docs/HANDOFF.md`, `docs/ccf_dataprep_v2.md`
> and the wave plans are records of what was sent then, not instructions. The
> vault preserves the exchange's contents at `exchange/_legacy/`.

## Backstory and the IRI contract

**`docs/ccf_dataprep_v2.md` is the current reference.** It records the original prep — curated FIBO subset, synthetic instance graph, Turtle files, transform and load scripts — and, critically, the **Canonical FIBO IRI binding** section: full IRIs for every class and object property, the cross-backend relationship type strings, the `ex:` application predicates, and the instance URI pattern.

That binding table is a **contract shared with downstream consumers.** Prefer full IRIs in code and queries; use local names only as labels. When you extend FIBO coverage — Loans, Securities, Derivatives, FX, and Collateral modules are all referenced by the specs — **add to that table first**, then generate data against it. Verify new terms against [spec.edmcouncil.org/fibo](https://spec.edmcouncil.org/fibo/) or the `edmcouncil/fibo` repo before writing them in; module membership does not pin an IRI.

`docs/ccf_dataprep.md` is the superseded v1. `docs/fibo_files/` holds the original working artifacts.

Keep v2 updated. When the dataset grows, its entity tables, file names, counts, and binding table grow with it.

### The binding table is mirrored — say when you change it

The binding table is published into the Obsidian vault as `wiki/context-products/content/fibo-iri-binding`, so the **CCF SDK project can reach it through the same MCP calls it already uses for the specs**. That project has no access to this repository.

**This repo is source of truth. The mirror can go stale.** Extending the table here does not update it there.

So: **whenever you add or change a binding, say so explicitly in your response** — name the terms added and state that the vault mirror needs refreshing. Do not edit the vault yourself; the custodian applies the refresh. But surfacing it is no longer the whole job — **publish the corrected mirror with `contribute()`** (above) — by commit if it is large — then say that you have published it.

**Expect the first trigger early.** The table currently binds the v1 starter set only — five classes, five object properties, covering ownership, control, and party-relatedness. That is enough for `corporate-family-tree` and essentially nothing else. The moment work starts on `facility-terms-snapshot` you will need Loans-module terms (facility, covenant, guarantee, cross-default) that do not exist in the binding yet. Fourteen of the twenty-one specs are in the same position.

The failure this prevents is silent and expensive: generating data against invented local names, which validates cleanly here and cannot be consumed downstream. Bind upstream, verify against the EDM Council source, generate, then flag the mirror.

---

## Settled decisions

These are decided. Do not re-open them.

**Real GLEIF LEIs, alongside synthetic identifiers.** Public anchor obligors carry **real GLEIF LEIs**, because several specs join public sources on LEI → CIK → ticker and fake identifiers cannot join. Invented entities carry synthetic identifiers in a **visibly distinct format** so the two can never be confused. Record which format signals which in `docs/ccf_dataprep_v2.md`.

Instance URIs stay under `http://example.org/fibo/` for everything, per the existing pattern. The real LEI lives in the `lei` attribute, not in the URI.

**Keep the existing cast.** Acme Corporation, Beta Holdings, Gamma Bank, Delta Fund, Omega Securities, John Smith, Jane Doe, Hans Müller, Sarah Chen all stay. "ACME Corp" is the worked example in the CCF whitepaper's own Chapter 8, so the naming carries narrative continuity. They become the **synthetic overlay** cast sitting alongside the real public anchors, and they keep synthetic identifiers per the rule above.

**SQLite is approved.** *(Done — `data/departmental.sqlite`, 8 tables.)* It is deliberately a *local file*, which is the entire point of the departmental-store narrative: the fabric must reach a small, locally-maintained system to enforce an enterprise-critical policy. `sqlite3` plus the Python `sqlite3` module is sufficient; no server. Confirm the file path in `docs/ccf_dataprep_v2.md` once chosen.

**You are not obligated to follow the prior structure.** The v1 pipeline (Turtle → Fluree → SPARQL export → mirror to every store) was built to make four backends hold identical data. That goal is now wrong — see below. Redesign the pipeline, the file layout, and the loaders as the target requires. Preserve the **IRI binding contract** and the **instance URI pattern**; everything else is yours to change.

## Still open — ask before acting

**Which public anchor obligors?** No spec names a required company; selection criteria are given instead. The binding one is `covenant-cross-reference`: an EX-10 credit agreement with a defined-terms article, three or more financial covenants, a guarantor schedule, and at least one filed amendment. Select by inspection via EDGAR full-text search, then **propose the list before loading**.

**Keep Neo4j at all?** It is demoted to optional and only earns a place if a product needs graph algorithms Fluree lacks — cycle detection in `corporate-family-tree` and `kyc-refresh-beneficial-ownership`. The cheaper alternative is application-side cycle detection. Decide before maintaining a fourth loader.

---

## Current state vs. target

The existing dataset is a **hello-world sample**. The gap is mostly structural rather than volumetric.

| | Now | Target |
|---|---|---|
| Entities | ~14 | ~500 legal entities, ~50 anchor obligors with full overlay |
| Relationships | ~11 | ~800 ownership edges, plus guarantee, cross-default, collateral, set-off, covenant, syndicate |
| Store topology | **Same data mirrored to all four** | **Deliberately partitioned; each store authoritative for its slice** |
| Identifiers | Made-up 20-char LEI-like strings | Real GLEIF LEIs for public anchors; distinct synthetic format for invented entities |
| Temporal | None | Bitemporal — valid time and assertion time, with supersession |
| Documents | None | Filed text with span offsets and embeddings (MongoDB) |
| SQLite | Not installed | Departmental store — restricted lists, trackers, local workbooks |
| FIBO coverage | 5 classes, 4 properties | Extended to Loans, Securities, Derivatives, FX, Collateral |

### The change that matters most

**The old pipeline mirrors; the target partitions.**

v1 ended with every store holding the same content, and `compare_backends.py` verifying they matched. That is exactly wrong here. The specs require each store to be **authoritative for a different slice**, precisely so cross-store assembly is a real operation rather than a staged one. A demo where every store holds everything proves nothing about the architecture.

So the validator **inverts**: it stops asserting the stores agree and starts asserting each holds **the slice it owns and nothing it doesn't**. Write that validator early — it is your regression suite, and it is the thing that catches a silently-wrong load.

---

## Store assignment

Authoritative per Q019 §3. Do not deviate without recording the change in `docs/ccf_dataprep_v2.md`.

| Store | Owns | Contents | Connection |
|---|---|---|---|
| **Fluree** ⭐ | `R`, `T`, lineage, policy binding | FIBO ontology; typed edges — ownership, guarantee, cross-default, syndicate-participant-in, collateral, set-off, covenant-of; as-of-time state; policy versions | `http://192.168.4.76:8092` (**Fluree 4.2.4** since 2026-10-15; the old 4.1.4 on :8090 was stopped 2026-10-15 — no rollback server runs), ledger **`fibo-v2`** |
| **Postgres** | `E`, policy reference | Obligors, facilities, exposures, balances, limits, thresholds, entitlement grants, the internal↔LEI crosswalk | `192.168.4.76:5432`, db `parkavedb`, user `parkave` |
| **MongoDB** | passage-level lineage | Filing text, credit agreements, memoranda, adverse media + span offsets + embeddings | `mongodb://192.168.4.76:27017`, db **`fibo_v2`** |
| **SQLite** | departmental | Control-room restricted list, covenant tracker, banker prospect notes, risk limit workbook | **`data/departmental.sqlite`** — created, 8 tables |
| **Neo4j** | optional | Graph algorithms only | `bolt://192.168.4.76:7687` — see open decisions |

> **Store identifiers, corrected 2026-08-24.** This table named ledger `fibo:main` and Mongo db `fibo` for many waves; the estate has used `fibo-v2` and `fibo_v2` since Wave 2. `ccf/config.py` is authoritative — `FLUREE_LEDGER_V2`, `MONGO_DB_V2`, `PG_SCHEMA_V2` — and code should read it rather than these literals. (`fibo` and `fibo:main` still exist as the superseded v1 names, which is why the drift was survivable and therefore invisible.)

**Fluree is preferred over Neo4j.** FIBO is OWL/RDF, so it loads unmodified and *is* the schema; the immutable ledger gives exact as-of reconstruction. This is a firm decision from the partner institution, not a preference to revisit.

**Single-writer discipline.** One store is authoritative per element. Fluree nodes carry `lei` plus a display label and nothing else — all attributes resolve from Postgres. Never duplicate an attribute across stores "for convenience."

---

## Non-negotiable rules

**1 · Three provenance classes, labelled per element.** Not two.

| Class | Meaning |
|---|---|
| `public` | Fetched from a named public source; record the source and retrieval date |
| `synthetic — internal` | Invented because it is bank-internal by nature: entitlements, credit opinions, CRM interactions, balances, deal pipeline |
| `synthetic — engineered` | Invented **deliberately** to create a condition public data will not supply |

The third class is where the demonstrations earn their keep, and it must be labelled honestly. Presenting an engineered condition as emergent misrepresents what the data proves. Engineered elements include: a planted cross-shareholding cycle, an amendment whose booking date lags its effective date with a drawdown in the gap, a false-positive name match, an interpolated intraday tick series, a break that inverts under clock alignment.

**2 · AML uses synthetic entities only — hard rule.** The `aml-typology-match` spec must never involve a named real company or real natural person. Typology definitions (FinCEN advisories, FATF reports) and sanctions entries are public and should be used; **the entities exhibiting the patterns must be invented.** Enforce at generation time, not at review. This is a legal constraint, not a style preference.

**3 · Pseudonymize person data at ingestion.** UK Companies House PSC records concern real living people. Preserve the *structure* — name-variant patterns, control types, ownership cycles — and replace the identities. The structural lesson survives pseudonymization completely; the privacy exposure does not survive publication.

**4 · Build the correlation key first.** `LEI` spans public data; `internal_client_id` keys the bank side. The crosswalk between them is synthetic and **mandatory** — generate it before any internal element loads, or nothing joins. This is the single most likely way to produce five stores that cannot be assembled.

**5 · Some joins must be imperfect on purpose.** Person identity across sources (PSC names vs. registry names vs. sanctions lists) should include genuine variants, transliterations, and at least one false-positive pair — two different people who fuzzy-match strongly. A dataset where every name resolves cleanly teaches the wrong lesson and makes the resolution logic untestable.

**6 · Depth, not breadth, for ABS.** A single SEC Form ABS-EE file carries tens of thousands of loans. Load **2–3 deals across 12 periods**, not a wide cross-section. Breadth costs a great deal and buys nothing.

**7 · Do not assume OWL inference.** Fluree runs without reasoning by default — a query for `Party` returns only entities *explicitly* typed as `Party`, not every `Corporation`. Type entities explicitly for every role you need to query against.

---

## Working conventions

**Keep FIBO IRIs for types and core predicates**, and application attributes under `ex:` (`http://example.org/fibo/`). The v2 binding table is the source of truth for both; never mix them.

**Normalize to full IRIs before comparing across stores.** Fluree SPARQL sometimes returns compact forms, and the v1 transforms stored only the last path segment in Mongo and Neo4j `types` arrays. Whatever you build, be explicit about which representation is in play at each hop.

**Load order.** Ontology → correlation crosswalk → entities → relationships → temporal assertions → documents → departmental. Each stage depends on the one before.

**Idempotency.** Loaders must be safely re-runnable. You will reload many times.

**Volume targets are floors with a purpose.** Each `≥ N` in a Manufacture envelope exists to make a specific behaviour demonstrable — *"≥ 1 amendment with an engineered booking lag, with a drawdown falling inside the gap"* is not a quota, it is the only way one product's central mechanism can be shown at all. Hitting the count while missing the condition is a failure.

---

## Definition of done, per product

A product's data is complete when all four hold:

1. Every element in its **§C Data Catalog** exists, in the store the catalog names, with its provenance class recorded.
2. The **correlation keys resolve** — every join the catalog implies actually joins.
3. Every **`≥ N` condition** in §F is satisfiable by a real query against the loaded data, not merely counted.
4. **Single-writer discipline holds** — no element duplicated into a store that does not own it.
5. **Any new FIBO terms are bound** in `docs/ccf_dataprep_v2.md`, verified against the EDM Council source, and the **vault mirror flagged for refresh** in your response.

A product that passes counts but fails a `≥ N` condition is not done. Neither is one that generated against an unbound term.

---

## Build order

Follow the tier ladder in Q019 §5. It is ordered so each tier's data reuses the last.

**First three, end to end:** `counterparty-reference-snapshot` → `corporate-family-tree` → `covenant-in-force-as-of`. That spans T1→T3 and needs only Postgres and Fluree.

Then `covenant-cross-reference` (introduces MongoDB and document text), then `mnpi-wall-enforcement` (introduces SQLite).

**Last:** `syndicated-lending-co-lender`, which needs a second Fluree/Postgres instance to represent a co-lender, and `large-exposure-rwa-concentration`, which composes six prerequisites.

---

## Suggested repository layout

Advisory, not binding — the prior structure is not a constraint.

```
docs/ccf_dataprep_v2.md   # current reference + IRI binding contract — KEEP UPDATED
docs/ccf_dataprep.md      # superseded v1
docs/fibo_files/          # original Turtle, transforms, loaders (reference)
ontology/                 # extended FIBO subset (Turtle)
sources/                  # fetched public data, by source, with retrieval dates
generators/               # synthetic and engineered data generation
loaders/                  # per-store loaders
validators/               # partition checks, join checks, condition checks
```

## When you are unsure

Ask. The open decisions above are the known forks; there will be others. The failure mode to avoid is a large, plausible, silently wrong dataset — a load that runs clean and produces stores that cannot be assembled, or conditions that were counted but not created. Both are expensive to discover downstream and cheap to prevent with a question.
