> [!WARNING]
> **SUPERSEDED IN PART — read this before trusting any number below.**
> Probed **2026-08-30**. The vault sent a `correction` on **2026-09-01**
> (`_archive/received/2026-09-01T06-58-52Z-search-ranking-changed.md`) that
> invalidates three things in this document:
>
> 1. **`search` is no longer an AND over tokens.** It matches ANY token and
>    ranks by distinct tokens matched, then frequency, with a boost for title
>    and summary. §"The query is an AND over tokens" and the quoted line
>    *"Every whitespace-separated token must appear"* are **wrong as of
>    2026-09-01**.
> 2. **Every count measured here is invalid** — not shifted, a *different
>    quantity*. Under OR matching `counts.total` is far larger: a six-token
>    query that reported a handful of canonical matches now reports ~175.
>    Do not carry the tables below forward. Re-probe.
> 3. **The tool surface is larger than the eight listed.** `contribute()`,
>    `record()`, `query()` and `list_contributions()` are live and appear
>    nowhere here. `get_article(root="contrib")` now REQUIRES `agent=`, and
>    passing the agent id as `topic=` raises rather than silently missing.
>
> **What survives:** the security findings (probe 5 — `../` rejected before
> filesystem access, no absolute path in error text) and the correction of the
> earlier handoff's three false claims. Those were about hardening, and
> hardening does not regress.
>
> Kept rather than deleted because the method is reusable and because it
> records that a handoff asserted three things that were not true — which is
> the reason to re-probe rather than inherit. See
> [[vault-specs-patched-in-place]].

# obsidian-vault MCP — probe results

**Run:** 2026-08-30 21:0x MST · session on `main` @ `6d37894`
**Mode:** read-only. No contribution, no mail, no vault session opened.
**Server:** `obsidian-vault` (user scope)

## Headline: the previous handoff was wrong on two counts

The handoff note in `.claude` state claimed:

> MCP server has NO `search` tool (six tools only) and `get_article` has no `root` param.
> Its path handling interpolates `../` rather than rejecting it, and errors leak the vault's
> absolute path.

All three claims are **false as of this run**:

| Claim in handoff | Actual |
|---|---|
| No `search` tool | **`search` exists** and returned grouped results (probe 1) |
| `get_article` has no `root` | **`root` exists**, defaults to `"wiki"`, accepts `"contrib"` (probe 4) |
| `../` is interpolated, path leaks | **`../etc` is rejected** by a validator, before any filesystem access; error text carries **no absolute path** (probe 5) |

Either the server was upgraded/hardened between then and now, or the earlier session
measured something else. Nothing here needs telling the custodian about hardening — the
hardening is already in place.

---

## Tool surface actually available

Eight tools, not six:

- `search(query, limit=20, sources=None)`
- `get_article(topic, name, root="wiki")`
- `get_response(...)`
- `list_articles(topic)`
- `list_responses(...)`
- `list_topics()`
- `submit_for_log(...)`

`search` docstring, verbatim from the schema:

> Search wiki, agent contributions and curated responses for a query.
> Every whitespace-separated token must appear, case-insensitively. Results are
> grouped by source rather than interleaved, so a caller reaches deliberately
> for contributed content instead of receiving it mixed with canonical content.
> The exchange ledger is never searched.
> Hits within a group are ordered by path, not by relevance, so `limit` decides
> WHICH matches you see, not merely how many. Check counts[group]["truncated"]
> before treating a group as a complete answer.
> Returns {"query": str, "results": {"canonical": [...], "contributed": [...],
> "response": [...]}, "counts": {group: {"returned", "total", "truncated"}}}
> where each hit is {"source", "path", "title", "excerpt"}.

`get_article` docstring, verbatim:

> root="wiki" (default) reads wiki/{topic}/content/{name}.md. root="contrib"
> reads contrib/{topic}/{name}.md, where topic is the owning agent id.
> Accepts name with or without .md. Returns {"topic", "name", "root", "path", "markdown"}.

**Ordering caveat that matters.** Hits are ordered **by path, not relevance**. So `limit`
selects *which* matches you see. I ran probe 1 at `limit=50`; canonical still truncated
(50 of 52). Two canonical hits for "context debt" were never shown, and because ordering is
alphabetical by path they are the two whose paths sort last — somewhere at or after
`wiki/wholesale-banking/`.

---

## Probe 1 — `search("context debt")`, limit 50

### Group names and counts

| Group | returned | total | truncated |
|---|---:|---:|---|
| `canonical` | 50 | **52** | **true** |
| `contributed` | 0 | 0 | false |
| `response` | 20 | 20 | false |

Three groups exist: **`canonical`**, **`contributed`**, **`response`**. `contributed` is
empty for every probe in this run — no agent has contributed anything matching, or the
contrib tree is empty. The exchange ledger is never searched, per the docstring.

### Every path returned — `canonical` (50 of 52)

```
wiki/agent-foundations/content/data-fusion-and-trust.md
wiki/agent-protocols/content/hermes-agent-v0-13-0.md
wiki/agent-protocols/content/mcp-ecosystem-hardening-may-2026.md
wiki/agent-protocols/content/nvidia-servicenow-project-arc.md
wiki/cognitive-context-fabric/content/abstract.md
wiki/cognitive-context-fabric/content/agent-anatomy.md
wiki/cognitive-context-fabric/content/ccf-architecture.md
wiki/cognitive-context-fabric/content/ccf-conceptual-model.md
wiki/cognitive-context-fabric/content/ccf-integration.md
wiki/cognitive-context-fabric/content/ccf-summary.md
wiki/cognitive-context-fabric/content/executive-summary.md
wiki/context-architectures/content/context-engineering-as-discipline.md
wiki/context-architectures/content/context-window-economics.md
wiki/context-products/content/abs-securitization-surveillance.md
wiki/context-products/content/ccf-sdk-de-requirements.md
wiki/context-products/content/collateral-and-setoff-coverage.md
wiki/context-products/content/counterparty-reference-snapshot.md
wiki/context-products/content/covenant-cross-reference.md
wiki/context-products/content/covenant-in-force-as-of.md
wiki/context-products/content/credit-exposure-rollup.md
wiki/context-products/content/credit-memo-context.md
wiki/context-products/content/facility-terms-snapshot.md
wiki/context-products/content/fibo-iri-binding.md
wiki/context-products/content/ib-opportunity-synthesis.md
wiki/context-products/content/large-exposure-rwa-concentration.md
wiki/context-products/content/obligor-financial-spread.md
wiki/context-products/content/rating-and-spread-migration.md
wiki/context-products/content/spec-standard-v0-3.md
wiki/context-products/content/syndicated-lending-co-lender.md
wiki/context-products/content/treasury-liquidity-position.md
wiki/frontier-models/content/ai-co-clinician-deepmind.md
wiki/frontier-models/content/gemini-3-1-family-and-gpt-5-5.md
wiki/frontier-models/content/gpt-5-5-instant-default.md
wiki/frontier-models/content/gpt-5-5-instant-system-card.md
wiki/knowledge-infrastructure/content/probabilistic-knowledge-extraction.md
wiki/llm-platforms/content/claude-code-stability-update.md
wiki/llm-platforms/content/claude-security-beta.md
wiki/llm-platforms/content/google-knowledge-catalog-april-2026.md
wiki/llm-platforms/content/teaching-claude-why-alignment.md
wiki/patents-and-ip/content/alternative-embodiments.md
wiki/patents-and-ip/content/original-claims.md
wiki/patents-and-ip/content/overview.md
wiki/patents-and-ip/content/proposed-claims.md
wiki/pool-safety/content/context-debt-in-practice.md
wiki/pool-safety/content/implementation-architecture.md
wiki/pool-safety/content/multi-agent-orchestration.md
wiki/pool-safety/content/overview.md
wiki/pool-safety/content/system-architecture.md
wiki/wholesale-banking/content/ccf-for-wholesale.md
wiki/wholesale-banking/content/enterprise-integration.md
```

### Every path returned — `contributed` (0 of 0)

```
(empty)
```

### Every path returned — `response` (20 of 20)

```
output/content/Q001-2026-04-17-context-half-life.md
output/content/Q007-2026-04-25-context-debt.md
output/content/Q008-2026-04-25-context-debt-banking.md
output/content/Q009-2026-04-25-context-as-a-product.md
output/content/Q010-2026-04-27-compile-whitepaper-authority-three-tiers.md
output/content/Q011-2026-04-27-compile-second-pass-banking-depth.md
output/content/Q012-2026-04-27-ccf-explained-agentic-importance.md
output/content/Q015-2026-05-17-compile-second-fetcher-pass.md
output/content/Q016-2026-05-17-compile-third-pass-foundations.md
output/content/Q017-2026-05-17-ccf-vs-google-knowledge-fabric.md
output/content/Q019-2026-08-15-cb-cib-context-product-requirements.md
output/content/Q023-2026-08-23-wave14-outbox-triage.md
output/content/Q027-2026-08-24-compile-spec-standard-v0-3-and-august-backlog.md
output/content/Q028-2026-08-24-nine-elements-of-the-context-product-contract.md
output/content/Q033-2026-08-29-spec-standard-mirror-vs-source.md
output/content/Q034-2026-08-29-cp-spec-001-mirror-vs-source.md
output/content/Q035-2026-08-29-functional-drift-vault-vs-sdk.md
output/content/Q036-2026-08-29-dataprep-consumer-signal-and-scope-break.md
output/content/Q037-2026-08-29-spec-generation-recipe-for-sdk-claude.md
output/content/Q038-2026-08-29-rung-01-unblocked-and-an-inferred-ruling.md
```

### Observation

The query is an **AND over tokens, not a phrase**. "context debt" matches any article
containing both words anywhere — which is why `gpt-5-5-instant-system-card` and
`nvidia-servicenow-project-arc` appear. Only two of the 70 hits are actually *about*
Context Debt (`pool-safety/content/context-debt-in-practice`, and the Q007/Q008 responses).
The canonical article `cognitive-context-fabric/content/context-debt.md` — linked by name
from four of the hits — **does not itself appear in the results**, which is the sort of
thing that reads as an absence if you do not check. It is one of the 2 truncated hits or it
lacks one of the tokens as a separate word; either way, **a truncated group is not an
answer**.

---

## Probe 2a — `search("fibo-iri-binding")` — a term **ccf_dataprep owns**

Chosen because the IRI binding table is generated in this repo
(`docs/ccf_dataprep_v2.md`) and mirrored into the vault. If group attribution works, our
own artifact should come back as `canonical` (published mirror), not `contributed`.

| Group | returned | total | truncated |
|---|---:|---:|---|
| `canonical` | 14 | 14 | false |
| `contributed` | 0 | 0 | false |
| `response` | 12 | 12 | false |

**Every hit, with the group it came from:**

| Group | Path |
|---|---|
| canonical | `wiki/context-products/content/abs-securitization-surveillance.md` |
| canonical | `wiki/context-products/content/client-360-coverage-graph.md` |
| canonical | `wiki/context-products/content/collateral-and-setoff-coverage.md` |
| canonical | `wiki/context-products/content/corporate-family-tree.md` |
| canonical | `wiki/context-products/content/counterparty-reference-snapshot.md` |
| canonical | `wiki/context-products/content/covenant-cross-reference.md` |
| canonical | `wiki/context-products/content/covenant-in-force-as-of.md` |
| canonical | `wiki/context-products/content/estate-data-catalog.md` |
| canonical | `wiki/context-products/content/facility-terms-snapshot.md` |
| canonical | `wiki/context-products/content/fx-post-trade-reconciliation.md` |
| canonical | `wiki/context-products/content/kyc-refresh-beneficial-ownership.md` |
| canonical | `wiki/context-products/content/rating-and-spread-migration.md` |
| canonical | `wiki/context-products/content/spec-standard-v0-3.md` |
| canonical | `wiki/context-products/content/treasury-liquidity-position.md` |
| response | `output/content/Q019-2026-08-15-cb-cib-context-product-requirements.md` |
| response | `output/content/Q021-2026-08-17-fibo-wave8-binding-refresh.md` |
| response | `output/content/Q022-2026-08-17-drift-punchlist-caveat-correction.md` |
| response | `output/content/Q023-2026-08-23-wave14-outbox-triage.md` |
| response | `output/content/Q024-2026-08-23-wave15-inbox-triage.md` |
| response | `output/content/Q025-2026-08-24-jurisdiction-terms-and-family-tree-corrections.md` |
| response | `output/content/Q026-2026-08-24-dev-quickstart-f-envelope-and-the-ex-register.md` |
| response | `output/content/Q028-2026-08-24-nine-elements-of-the-context-product-contract.md` |
| response | `output/content/Q030-2026-08-24-context-product-definition-v1-2-vs-v2-0.md` |
| response | `output/content/Q033-2026-08-29-spec-standard-mirror-vs-source.md` |
| response | `output/content/Q034-2026-08-29-cp-spec-001-mirror-vs-source.md` |
| response | `output/content/Q036-2026-08-29-dataprep-consumer-signal-and-scope-break.md` |

**Notable:** `wiki/context-products/content/fibo-iri-binding.md` — the mirror itself —
appears in the **canonical** group. Our own upstream is therefore reachable as canonical
vault content, exactly as intended. **`contributed` is empty**, meaning the binding was
published into `wiki/` by the custodian rather than sitting in a contrib tree.

**What I would cite, and from where:** for the binding contract itself,
`wiki/context-products/content/fibo-iri-binding.md` (**canonical**). For the history of
corrections to it — the ten invalid starter bindings, the Commons relocation, the
one-file method that cannot prove absence — `Q021`, `Q024`, `Q026` (all **response**).
Note the split: **canonical carries the contract, response carries the reasoning.** Citing
only canonical loses every caveat about how the terms were verified.

---

## Probe 2b — `search("operator registry")` — a term **ccf-sdk owns**

Chosen because Operators are explicitly out of scope for this repo (CLAUDE.md: "That is
the thing you must not build"), so anything found here is the SDK's territory.

| Group | returned | total | truncated |
|---|---:|---:|---|
| `canonical` | 12 | 12 | false |
| `contributed` | 0 | 0 | false |
| `response` | 8 | 8 | false |

**Every hit, with the group it came from:**

| Group | Path |
|---|---|
| canonical | `wiki/agent-governance/content/binding-agent-regulation.md` |
| canonical | `wiki/cognitive-context-fabric/content/ccf-architecture.md` |
| canonical | `wiki/cognitive-context-fabric/content/context-as-product.md` |
| canonical | `wiki/context-products/content/ccf-sdk-de-requirements.md` |
| canonical | `wiki/context-products/content/counterparty-reference-snapshot.md` |
| canonical | `wiki/context-products/content/fibo-iri-binding.md` |
| canonical | `wiki/context-products/content/kyc-refresh-beneficial-ownership.md` |
| canonical | `wiki/context-products/content/spec-standard-v0-3.md` |
| canonical | `wiki/llm-platforms/content/google-knowledge-catalog-april-2026.md` |
| canonical | `wiki/pool-safety/content/implementation-architecture.md` |
| canonical | `wiki/pool-safety/content/projection-layer-design.md` |
| canonical | `wiki/wholesale-banking/content/ccf-for-wholesale.md` |
| response | `output/content/Q004-2026-04-19-compile-projection-layer.md` |
| response | `output/content/Q005-2026-04-19-projection-implementation-lens.md` |
| response | `output/content/Q009-2026-04-25-context-as-a-product.md` |
| response | `output/content/Q012-2026-04-27-ccf-explained-agentic-importance.md` |
| response | `output/content/Q017-2026-05-17-ccf-vs-google-knowledge-fabric.md` |
| response | `output/content/Q019-2026-08-15-cb-cib-context-product-requirements.md` |
| response | `output/content/Q027-2026-08-24-compile-spec-standard-v0-3-and-august-backlog.md` |
| response | `output/content/Q033-2026-08-29-spec-standard-mirror-vs-source.md` |

**What I would cite, and from where:** for the operator definition this repo must not
implement, `wiki/cognitive-context-fabric/content/ccf-architecture.md` (**canonical**, L4
layer model) and `wiki/context-products/content/ccf-sdk-de-requirements.md`
(**canonical**, step 4 "build assembly"). For the live disagreement over whether the
closed eight-operator vocabulary or the whitepaper's four-category algebra is canonical —
open ruling `D-IMPL-31` — `Q027` (**response**). That conflict is *unresolved and lives
only in a response document*; nothing canonical records it.

### The group distinction is load-bearing

Both probes show the same shape: **canonical states the contract, response carries the
open questions and the corrections.** A search that reads only `canonical` returns a
cleaner and more confident picture than the vault actually holds. `contributed` was empty
in all three searches, so nothing in this run exercised the contrib path.

Cross-cutting hits are real: `fibo-iri-binding.md` and `counterparty-reference-snapshot.md`
appear in **both** 2a and 2b. Ownership of a *term* does not partition the *articles*.

---

## Probe 3 — `get_article("context-products", "estate-data-catalog")`

**Result: SUCCESS.** Returned envelope fields:

| Field | Value |
|---|---|
| `topic` | `context-products` |
| `name` | `estate-data-catalog` |
| `root` | `wiki` (defaulted) |
| `path` | `wiki/context-products/content/estate-data-catalog.md` |

The mirror we published on 2026-08-30 (commit `5206155`) is live and readable over MCP.
Its frontmatter self-identifies the upstream and the generator, so a downstream reader can
tell it is a mirror and knows how to get it regenerated.

**Raw markdown, verbatim:**

~~~markdown
---
kind: reference
upstream: ccf_dataprep/docs/store-catalog.md
upstream_json: ccf_dataprep/docs/store-catalog.json
generator: generators/build_store_catalog.py
generated: 2026-08-30T01:56:48Z
upstream_commit: 5206155
---
# Estate Data Catalog — what the stores actually hold

**Status:** mirror of the `ccf_dataprep` estate catalog · **generated 2026-08-30T01:56:48Z** from live introspection · upstream commit `5206155`.

> The specs in this topic name *elements*. This article says what the estate holds to satisfy them — the partition across five stores, the scale of each, and the three traps that make a naive count wrong.

**Upstream source of truth:** `ccf_dataprep/docs/store-catalog.md` and its machine-readable companion `store-catalog.json`. This article is a **mirror**. **When the two disagree, the repository wins.**

**Regenerate rather than correct.** The catalog is produced by `generators/build_store_catalog.py`, which reads the live stores on every run. A hand-maintained catalog of 987 columns is stale the day it is typed. If a number here looks wrong, run the generator — do not edit this article.

> ### ⏱ Every number below is dated, and the estate is live.
>
> This is a **snapshot, not a stability promise** — `ccf_dataprep` says so explicitly. Counts, row totals and field-presence percentages are true as of the generation stamp above and nothing guarantees they are true now. **Cite the stamp whenever you cite a figure**, and ask for a regeneration when currency matters. It is one command on their side.

## The partition — nothing is mirrored

Each store is authoritative for a different slice, which is what makes cross-store assembly a real operation rather than a staged one.

| Store | Owns | Scale (as of the stamp) |
|---|---|---|
| **Fluree** `fibo-v2` | `R`, `T`, lineage, policy binding | 87,162 triples · 11,906 subjects · **171 predicates** |
| **Postgres** `ccf_v2` | `E`, policy reference | **115 tables · 987 columns · 2 views** |
| **MongoDB** `fibo_v2` | passage-level lineage | 6 collections · 38k+ passages |
| **SQLite** `data/departmental.sqlite` | departmental | 8 tables · 148 rows |
| **Neo4j** | optional | 14 nodes — **v1 starter set only** |

Fluree nodes carry `lei` plus a display label and nothing else; **every attribute resolves from Postgres.**

## Three traps — read before trusting a number

### 1 · Fluree predicate counts cannot be obtained by aggregate

The ledger answers *"how many predicates"* three ways and only one is right:

| Query | Answer |
|---|---:|
| `COUNT(DISTINCT ?p)` | 178 |
| `GROUP BY ?p` | 198 |
| **`SELECT DISTINCT ?p`** | **171 — correct** |

The `GROUP BY` invents **27 phantoms** — `ex:_d0` and `ex:AdministrativeAgent` among them, the latter a **class, not a predicate** — every one of which returns **zero rows** when queried directly.

> **Why this is the most dangerous item in the catalog.** A traversal written against `ex:AdministrativeAgent` returns an empty result, and an empty result reads as *"this estate has no administrative agents"* rather than *"this predicate is not real."* A wrong answer announces itself; **a silenced one does not.**
>
> **Enumerate and verify. Never aggregate.** Every predicate upstream was enumerated and then confirmed by asking for a row through it; the rejected phantoms are listed in the JSON under `phantom_predicates_rejected`. Recorded as `ccf_dataprep` known-issues §56.

This is the fourth recorded instance of **a check whose population is not its question** — and the first caught *before* it shipped rather than after. See [[counterparty-reference-snapshot]] for the other three.

### 2 · MongoDB field presence is sampled

500 documents per collection, and the percentages say so. **A field in 100% of a sample is not a field that is always present, and absence from a sample is not absence.** Sample sizes are stated per collection upstream.

One real signal this surfaces: `document.doc_type` is present in only **28.5%** of its sample.

### 3 · Neo4j holds the v1 starter set only

14 nodes, 16 relationships. **No v2 Context Product depends on it. Treat it as absent when designing.** This is why [[../_index|the catalog]] favours Fluree — see also the FIBO binding, which is RDF-native and loads unmodified.

## Provenance classes are per table, and mixed

Postgres tables carry one or more of `public`, `synthetic — engineered`, `synthetic — internal`, `derived`. Many carry **more than one** — `interaction`, `person_crosswalk`, `coverage_assignment` and `signal_event` each mix classes across their columns.

**A table is not a provenance class.** Read the class at column level from `store-catalog.json`, not from the table summary, whenever a §C row's classification depends on it.

> Note the vocabulary gap: `synthetic — engineered` and `synthetic — internal` are **estate properties**, not members of the Standard's closed provenance list (`internal-SOR · vendor · public-filing · derived · inherited`). They describe how the demonstration data was produced. Do not put them in a §C provenance column — see [[spec-standard-v0-3]].

## What this catalog is NOT

Stated by `ccf_dataprep`, and carried here because each line prevents a specific misuse:

- **Not a §C.** These are the raw stores. Mapping a store column to a §C row, its capability class and its `G` axis is the design work this is *input* to.
- **Not semantics.** It says a column exists, its type and its provenance class. What it *means* lives in the specs and in `docs/ccf_dataprep_v2.md`'s binding table.
- **Not a stability promise.** A snapshot of a live estate, dated in its own header.

## Looking something up

| You need | Go to |
|---|---|
| Which store owns a slice | the partition table above |
| Whether a column exists, its type, nullability, keys | **`store-catalog.json`** — every one of the 987 |
| Full MongoDB document specs, per-table detail, all 171 predicates | **`store-catalog.md`** upstream |
| What an element *means* | the product spec in this topic, and `ccf_dataprep_v2.md` |
| Exact IRIs behind a module name | [[fibo-iri-binding]] |

**The JSON is not reachable over MCP** — this server serves markdown from `wiki/` and `output/` only. Read it from the `ccf_dataprep` repository directly, or ask `ccf-dataprep` for a regeneration through the exchange.

## Where to push back

`ccf_dataprep` asks for this explicitly: if a `[TBC — ccf_dataprep]` marker in a spec names a measurement this catalog does not answer, **that is a gap in the catalog and they want to hear it rather than have it worked around.** Same for any column whose purpose is not inferable from its name and type — that is exactly the case where a guess becomes a wrong §C row.

## Key Takeaways

- **Five stores, nothing mirrored.** Each owns a different slice; Fluree carries the edges and Postgres every attribute.
- **171 predicates, not 178 or 198.** Aggregate queries invent 27 that return nothing, and one of them is a class. Enumerate and verify.
- **A phantom predicate fails silently** — an empty traversal reads as "no such entities" rather than "no such predicate." This is the catalog's most expensive trap.
- **Mongo presence is sampled**; 100% of a sample is not always-present.
- **Neo4j is the v1 starter set — treat it as absent.**
- **`synthetic — engineered` and `synthetic — internal` are estate properties, not provenance classes.** They do not belong in a §C provenance column.
- **Every figure is dated.** Cite the stamp, and ask for a regeneration rather than trusting an old number.

## Related

- [[fibo-iri-binding]] — the IRI mirror from the same upstream; read together when binding a §C row
- [[spec-standard-v0-3]] — the closed provenance and capability-class vocabularies this catalog does *not* use
- [[../_index|the catalog index]] — which products read which stores
~~~

### One labelling ambiguity to note

The mirror's partition table reads **Postgres `ccf_v2`**, in a column where the Fluree row
gives a ledger name (`fibo-v2`) and the Mongo row a database name (`fibo_v2`). Checked
against `ccf/config.py`, which is authoritative:

- `PG_SCHEMA_V2 = "ccf_v2"` — a **schema** (`ccf/config.py:42`)
- `PGDATABASE` defaults to `parkavedb` — the **database** (`ccf/config.py:60`)

So `ccf_v2` is correct but is a schema sitting next to two database/ledger names. A reader
could take it for a database and fail to connect. The counts themselves came from live
introspection and are unaffected — this is a label, not a number.

---

## Probe 4 — `get_article("context-products", "estate-data-catalog", root="contrib")`

**Result: ERROR.** Raw error text:

```
Error executing tool get_article: Article not found: contrib/context-products/estate-data-catalog.md
```

**This is the correct behaviour, not a bug.** Per the docstring, `root="contrib"` reads
`contrib/{topic}/{name}.md` **where topic is the owning agent id** — not a wiki topic.
`context-products` is a wiki topic, so `contrib/context-products/` does not exist. The
correct contrib path would use an agent id such as `ccf-dataprep` or `ccf-sdk`.

**What this proves:** the `root` parameter **exists and is honoured**. It changed the
resolved path from `wiki/{topic}/content/{name}.md` to `contrib/{topic}/{name}.md` — you
can read the switch directly in the error. The handoff claim that `get_article` has no
`root` parameter is refuted by this probe alone.

**What this does not prove:** that nothing exists in `contrib/`. This is an absence, and
an absence with no positive control is not a fact. The `contributed` group returned 0 hits
in all three searches too, which is consistent with an empty contrib tree — but equally
consistent with a contrib tree that no probe in this run addressed correctly. **To settle
it, retry with an agent id as the topic.** I did not, because the ask was these five
probes only.

---

## Probe 5a — `get_article("../etc", "passwd")` — path traversal

**Result: REJECTED.** Raw error text:

```
Error executing tool get_article: Invalid topic or name: '../etc'/'passwd'
```

**The server validates and refuses.** Three things to read off this:

1. **It is rejected, not interpolated.** The message is `Invalid topic or name`, a
   validation verdict — not `Article not found`, which is what a filesystem miss produces
   (compare probes 4 and 5b). So the check fires **before** any path is resolved.
2. **No absolute path leaks.** The error echoes only the two arguments the caller already
   supplied. The vault's location on disk is not disclosed.
3. **It contrasts cleanly with 5b.** Two different error strings for two different
   failures — a validation refusal versus a genuine miss — which is exactly the
   discrimination you want, and it means the guard is not simply swallowing everything.

This directly refutes the handoff's third claim. Whatever was true before, **the traversal
guard is in place now and it does not leak the path.** Nothing to report to the custodian.

---

## Probe 5b — `get_article("wiki", "x")` — the negative control

**Result: ERROR.** Raw error text:

```
Error executing tool get_article: Article not found: wiki/wiki/content/x.md
```

**This is the most informative line in the run.** The resolved path is `wiki/wiki/content/x.md`
— the literal template `wiki/{topic}/content/{name}.md` with `topic="wiki"`. So:

- `wiki` is treated as an ordinary **topic name**, not as a root. There is no special-casing.
- The template is confirmed exactly as documented.
- The error reveals the resolution rule but **still no absolute path** — it is relative to
  the vault root throughout.

**Why this probe matters as a control.** It is the known-absent case. It produces
`Article not found` where probe 5a produced `Invalid topic or name`. Without 5b you could
not tell whether 5a's refusal was a real guard or just the same generic miss dressed
differently — the two probes together are what make the guard finding trustworthy rather
than assumed. Probe 3 is the known-present control on the same tool. **All three answers
differ, so the tool discriminates.**

---

## Summary

| # | Probe | Result |
|---|---|---|
| 1 | `search("context debt")` | **OK** — 3 groups; 50/52 canonical (**truncated**), 0/0 contributed, 20/20 response |
| 2a | `search("fibo-iri-binding")` | **OK** — 14 canonical, 0 contributed, 12 response |
| 2b | `search("operator registry")` | **OK** — 12 canonical, 0 contributed, 8 response |
| 3 | `get_article(context-products, estate-data-catalog)` | **OK** — full markdown, our mirror @ `5206155` |
| 4 | same, `root="contrib"` | **Not found** — `root` works; path switched to `contrib/…` |
| 5a | `get_article("../etc", "passwd")` | **Rejected** — validated, no path leak |
| 5b | `get_article("wiki", "x")` | **Not found** — `wiki/wiki/content/x.md`, template confirmed |

### What changed since the last handoff

The handoff's three claims about this server — no `search`, no `root`, leaky traversal —
are **all false now**. That entry should be treated as stale and not carried forward.

### The one caveat worth carrying

**Search hits are ordered by path, not relevance, and groups truncate silently.** Probe 1
returned 50 of 52 canonical and the two it dropped are the two sorting last. A caller who
does not read `counts[group]["truncated"]` will read a partial result as a complete one.
Check `truncated` before treating any group as an answer.

### Not done, as instructed

No contribution, no mail sent, no vault session opened. Report only.
