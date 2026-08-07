# Fluree Adapter Feasibility — Research

**Researched:** 2026-08-07
**Domain:** Fluree DB v4 as a tier-1 substrate adapter for the Phase 15.2 `GraphQuery` → `GraphView` seam
**Confidence:** HIGH on product/license/API facts (primary sources fetched 2026-08-07, verbatim license text); MEDIUM on two Cypher translation details (named verification items F-A2/F-A3); HIGH on the temporal-mapping verdict; HIGH on the routing recommendation

---

## Executive Summary

**Routing recommendation: insert Phase 15.3 — do not amend 15.2. Confidence: HIGH.**
No finding forces a change to the frozen `GraphQuery` vocabulary, the
`SourceAttestation` contract, or any 15.2 seam. Fluree lands as a routine
tier-1 storage adapter that proves itself against the D-05 conformance suites
unchanged — which is exactly the no-refactor claim the phase exists to
establish, and exactly the slot the CONTEXT's Deferred Ideas already reserves
("a future adapter proves itself against the D-05 suites without SDK change").
Amending 15.2 would add a sixth backend — the first HTTP-wire backend, with a
novel transaction-mapping problem — to a phase already rated HIGH delivery
risk for carrying five.

**One surgical amendment to 15.2 is recommended anyway** (cheap, and it is the
only finding with flip-the-answer potential): plan **15.2-02** (`_GraphTxn`
write seam) should carry an explicit acceptance criterion that the `_GraphTxn`
Protocol is implementable by a **remote, batched substrate** — one whose
commit is a single buffered HTTP transaction rather than a held database
session. If that Protocol's shape silently assumes a held session, adding
Fluree (or any HTTP substrate) later becomes the post-gate seam change the
phase exists to prevent. One design-constraint sentence now; no sixth backend.

The four load-bearing technical findings:

1. **Fluree today is v4 — a Rust rewrite, GA April 2026, current v4.1.4
   (2026-07-23), BSL 1.1 converting to Apache 2.0.** The v2 line (Clojure,
   AGPL-3.0, `fluree/ledger`) is legacy but still maintained; the v3 Clojure
   server never left alpha. **Which line the target financial institution
   actually runs is undetermined and is the gating adoption question** — a v4
   adapter is useless to a v2 shop (different API, different license, different
   product generation).
2. **Fluree v4 speaks openCypher (and Bolt), which makes the Neo4j plan
   (15.2-12) the direct translation template.** Bounded undirected
   variable-length paths, `all(x IN list WHERE ...)` hop predicates, `$param`
   parameters, and `UNWIND` are all documented-supported. One quoted gap
   (bounded type-alternation `[:A|B*1..3]`) has the workaround the Neo4j plan
   already names. SPARQL 1.1 is claimed complete but **standard SPARQL cannot
   express bounded-depth repetition at all** — Cypher, not SPARQL, is the
   traversal target.
3. **Fluree's native time travel must NOT be delegated to for as-of.** Fluree
   `t` is transaction time (commit order); CCF's as-of filters on
   `observed_at`/`superseded_at`, which arrive as *data* from L2. The two
   diverge on late-arriving observations and on supersession timestamps, and a
   delegating adapter would fail the D-05 differential corpus by construction.
   The adapter encodes CCF temporal fields as canonical-text properties and
   filters on them — exactly the SQL/Neo4j/Mongo model. Native time travel
   stays available out-of-band as an auditor bonus, never a replay input.
4. **There is no usable Python client — and no new one is needed.** `fluree-py`
   is not on PyPI (its README's `pip install fluree-py` names an unregistered,
   squattable package — a live supply-chain hazard to avoid, not adopt);
   `aioflureedb` targets the dead v2 API and is dormant. The adapter speaks
   plain HTTP via `httpx==0.28.1`, **already a pinned core dependency** —
   zero new packages, which makes Fluree's packaging burden *lower* than
   Neo4j's or Mongo's (no extra needed; only a pytest marker and a container
   CI leg).

**A scope ambiguity Dave must resolve before anything is planned** (surfaced
per CLAUDE.md §15, not defaulted): "the institution uses Fluree for their
knowledge graph and wants it as an adapter" is ambiguous between two different
products. (a) **CCF deployed with Fluree as its L3 substrate** — L2 writes
claims into a CCF-owned Fluree ledger; single-writer holds; this is the tier-1
adapter this document scopes. (b) **CCF reading the institution's existing
Fluree knowledge graph** — pre-existing data not written by L2 — which is a
**tier-3 raw external source**, explicitly out of scope for 15.2 and deferred
by Dave's own 2026-08-07 ruling (designed-for via D-08/D-09, another gate
producing the same admitted wrapper). A tier-1 adapter does not deliver (b).
See Open Questions.

---

## Q1 — Version and Product Landscape

All claims retrieved 2026-08-07 unless noted.

| Generation | Repo / artifact | Language | License | Status |
|---|---|---|---|---|
| **v2** | `github.com/fluree/ledger` | Clojure | **AGPL-3.0** | Legacy stable line; still maintained (pushed 2026-01-27) [VERIFIED: GitHub API] |
| **v3** | `github.com/fluree/server` (Clojure) | Clojure | **no license file detected** by GitHub [VERIFIED: GitHub API] | Never left alpha — latest release v3.0.0-alpha3, 2025-04-29 [VERIFIED: GitHub releases API] |
| **v4 (current)** | `github.com/fluree/db` | **Rust** (full rewrite in the original repo) | **BSL 1.1 → Apache 2.0** | GA v4.0.0 2026-04-23; current **v4.1.4** (2026-07-23); very active (pushed 2026-08-07, 442 stars) [VERIFIED: GitHub API + releases] |

**What v4 ships** [CITED: github.com/fluree/db README + fluree.github.io/db docs]:
- One `fluree` binary: CLI, `fluree server run` (HTTP on :8090), embedded Rust
  library, and an MCP server (`fluree mcp serve`).
- Docker image **`fluree/server`** — note the naming trap: the *image* is now
  built from the v4 Rust `fluree/db` repo (tags 4.0.0–4.1.4 align exactly with
  db release dates), while the *GitHub repo* named `fluree/server` is the
  abandoned v3 Clojure codebase. Image is ~63–70 MB [VERIFIED: Docker Hub API].
- Three query languages over one engine: **JSON-LD Query**, **SPARQL 1.1**
  ("zero compliance failures against the W3C test suite" — README claim),
  **openCypher 9** (plus Bolt protocol for Neo4j drivers).
- Time travel: any prior state by transaction number `@t:N`, ISO-8601
  `@iso:...`, or content-addressed commit `@commit:...`.

**Officially supported HTTP API surface** (base path discovered via
`GET /.well-known/fluree.json`, default `/v1/fluree`)
[CITED: fluree.github.io/db/api/endpoints.md]:

| Concern | Endpoint(s) |
|---|---|
| Query | `POST /query`, `POST /query/{ledger}` — accepts JSON-LD, SPARQL (`application/sparql-query`), Cypher (`application/cypher`, raw or `{"cypher": "...", "params": {...}}` envelope); content-negotiated results (SPARQL-results JSON, JSON-LD, CSV/TSV) |
| Write | `POST /insert`, `POST /upsert`, `POST /update` (JSON-LD txn, SPARQL UPDATE `application/sparql-update`, or Cypher writes). Response carries `t`, `timestamp`, `commit_id`, **`flakes_added`, `flakes_retracted`**; `409` on optimistic-concurrency exhaustion |
| History / time travel | time selectors in query `from` (`ledger:main@t:N` / `@iso:` / `@commit:`); history ranges `from`/`to` with `@t`/`@op` annotations; SPARQL `FROM <ledger@t:N>` |
| Read-after-write | **`Fluree-Min-T` header** (or `opts.min-t`) — the mechanism the adapter must thread to guarantee the differential suite's write-then-read discipline |
| Ledger mgmt | `POST /create`, `GET /ledgers`, `GET /exists/{ledger}`, branches/merge/drop |
| Health | **`GET /health`** → `{"status": ..., "version": ...}`, 200/503 — documented for k8s liveness/readiness |

**Which line would a financial institution most plausibly run today?**
Undetermined from public evidence — and it matters totally. v2 was the only
long-stable line before April 2026; v4 has been GA for ~4 months. An FI with a
years-old Fluree knowledge graph is most plausibly on v2 (AGPL, `/fdb/`-style
API, signed commands) or on a Fluree PBC commercial arrangement; a recent
adopter is plausibly v4. **The adapter this document scopes targets v4 only**
— the only current, documented, CI-able line. A v2 adapter would be a
different codebase against a different API. This is D-IMPL question 2 below.
[ASSUMED: institutional-deployment inference; no public data]

## Q2 — License Posture

Verbatim from `fluree/db` `LICENSE` at `main` [VERIFIED: raw.githubusercontent.com, fetched 2026-08-07]:

- **License:** Business Source License 1.1. **Licensor:** Fluree, PBC.
- **Licensed Work:** "Fluree DB version 4.0.0, and each subsequent version of
  Fluree DB first publicly distributed by Licensor under this License"
- **Change Date:** "The fourth anniversary of the first publicly available
  distribution of each specific version of the Licensed Work" (so v4.0.0 →
  Apache 2.0 in April 2030, per-version rolling)
- **Change License:** Apache License, Version 2.0
- **Additional Use Grant (verbatim):** "You may make use of the Licensed Work,
  provided that you may not use the Licensed Work for a Database Service."
  With: "A 'Database Service' is a commercial offering that allows third
  parties (other than your employees, contractors, and service providers
  acting solely on your behalf) to access a substantial portion of the
  functionality of the Licensed Work as a hosted or managed service, including
  where such third parties create, manage, query, transact against, or
  administer databases, ledgers, graphs, datasets, or similar data stores
  whose structure, contents, or access patterns are controlled by such third
  parties."

**Consequences:**
- **CI containers: permitted.** Running `fluree/server` in CI for conformance
  tests is ordinary internal use, nowhere near the "commercial hosted Database
  Service" carve-out. Same posture as the Mongo (SSPL server / Apache driver)
  and Neo4j (GPL server / Apache driver) legs already accepted in 15.2.
- **No SDK contamination.** The adapter is wire-only (HTTP/Bolt). The SDK
  never links, vendors, or distributes BSL code; BSL obligations attach to
  whoever *runs* the server (the deployment), not to clients speaking to it.
  Identical to the neo4j/pymongo posture.
- **AGPL applies to the v2 line only** (`fluree/ledger`). Even there, AGPL's
  network clause binds those who modify/operate the AGPL software, not
  wire clients — but the v4 adapter never touches it. The legacy v3
  `fluree/server` repo carries **no detected license file** — one more reason
  it is not a target.
- A financial institution running Fluree in production is either within the
  grant (internal use) or holds a commercial license from Fluree PBC — their
  problem either way, never the SDK's.

## Q3 — Python Client Legitimacy

Applying the 15.2-RESEARCH Package Legitimacy discipline:

**`fluree-py` (crcresearch) — REJECTED.**
- **Not on PyPI**: `pip index versions fluree-py` → no distribution;
  `pypi.org/pypi/fluree-py/json` → HTTP 404 [VERIFIED: both probes, 2026-08-07].
- GitHub repo: 1 star, 1 fork, 44 commits, MIT, third-party academic (Notre
  Dame CRC), targets the pre-v4 API era [VERIFIED: github.com/crcresearch/fluree-py].
- **Active supply-chain hazard:** its README documents `pip install fluree-py`
  for a name nobody has registered. Anyone following that instruction today
  installs nothing; anyone following it after a squatter registers the name
  installs the squatter's code. Under the project's package-vetting rule this
  is precisely the class of name we refuse to normalize. Do not reference it
  in any plan.

**`aioflureedb` — REJECTED.**
- On PyPI, BSD, first release 2020-09-09, latest 0.8.3 **2024-05-07** (dormant
  2+ years); solo maintainer; targets the **v2** API surface (health/dbs/
  query/block/command — v2 endpoint names) with v2 signed transactions;
  self-described "late beta" [VERIFIED: PyPI JSON API; CITED: pypi.org/project/aioflureedb].
  Useless against v4.

**No official Fluree Python client exists.** v4's documented client surfaces
are: HTTP API, Rust API, CLI, and **Bolt** ("official Neo4j drivers and
Bolt-compatible tools connect directly" — port 7687, bearer-token auth)
[CITED: fluree.github.io/db/guides/bolt.md].

**Verdict: plain HTTP via `httpx` — Approved, zero new dependency.**
`httpx==0.28.1` is already a direct core pin (pyproject.toml:44, promoted from
transitive in Phase I.3) [VERIFIED: pyproject.toml]. The adapter needs exactly
these calls, all enumerated in Q1's endpoint table: `POST /create` (bootstrap),
`POST /update` with `application/sparql-update` or Cypher (write seam, returns
`flakes_added` for the rowcount contract), `POST /query/{ledger}` with
`application/cypher` envelope + `params` (read seam), `Fluree-Min-T` header
(read-after-write), `GET /health` (CI gating). No extra, no slopcheck run
needed (nothing installs), no mypy override, no lazy import. The alternative
wire — the already-Approved `neo4j` driver over Bolt — works but couples the
Fluree adapter to the `neo4j` extra and to Bolt's explicit-transaction
restriction ("Raft/peer deployments reject BEGIN"); HTTP is the recommended
default. [Wire choice surfaced in Open Questions; recommendation on record.]

## Q4 — Query Pushdown Capability

Against the frozen `GraphQuery` vocabulary (D-02), family by family
[CITED: fluree.github.io/db/query/{sparql,cypher,jsonld-query}.md, fetched 2026-08-07]:

**(a) Entity/relationship selection with property filters — YES, in all three
languages.** SPARQL FILTER ("filters can be placed anywhere in the WHERE
clause"), JSON-LD Query `filter`/`values`, Cypher `WHERE`. Canonical-text
timestamp comparison works as plain string comparison in all three (the repo's
lexicographic-RFC3339 property carries over).

**(b) Bounded-hop traversal — YES, via Cypher; NOT via SPARQL.**
- **SPARQL:** property paths support `+ * ? ^ | / !` — but SPARQL 1.1 has no
  bounded-repetition syntax (dropped from the W3C spec; Fluree documents
  none). Bounded depth in SPARQL means hand-expanding unions of fixed-length
  sequences per depth — exactly the translation pain the seam exists to avoid.
- **Cypher:** documented-supported: variable-length with bounds
  (`-[:T*m..n]->`, "bounded ranges expand to unions"), **undirected**
  patterns (`-[:T]-`, "forward ∪ reverse union"), path functions `nodes()`/
  `relationships()`, list predicates `all/any/none/single(x IN list WHERE
  pred)`, `$param` parameters, `UNWIND` over runtime lists. This is the
  15.2-12 Cypher shape almost verbatim.
- **One exactly-quoted gap:** "Bounded type-alternation var-length
  `-[:A|B*1..3]->`" is a deferred feature. The workaround is the form the
  Neo4j plan already names as its alternative: untyped bounded pattern +
  `all(r IN relationships(p) WHERE type(r) IN $types)` (parameterized).
  Verification item F-A3.
- Whether Cypher bounds accept parameters (`*0..$depth`) is undocumented —
  the same A2 question as Neo4j, same mitigation (validated-integer literal at
  one documented site, Pitfall 7). Verification item F-A2.

**(c) `allowed_entities` translation — YES.** Cypher `$param` list +
`IN`/`UNWIND` (identical to the 15.2-12 wire realization: membership predicates
fully parameterized, `all(n IN nodes(p) WHERE ... AND n.entity_uri IN
$allowed)` for the uniform rule); SPARQL `VALUES` is supported for the
non-traverse families. No documented size limit; HTTP body carries the list
(practical limits are request-size limits — same class as Mongo `$in`).
[ASSUMED: no hard cap documented; probe at implementation]

**(d) Result ordering — non-issue by construction.** `ORDER BY` exists in all
three languages, but locked constraint 3 puts canonical ordering in the
interface: the adapter feeds dict rows into the 15.2-03 materialization core
exactly as Neo4j/Mongo do. Stable retrieval only needs deterministic row
*content*, which as-of filtering on data properties provides.

**(e) SPARQL 1.1 completeness** — README claims W3C-suite-clean; the docs list
full aggregation, subqueries, VALUES, named graphs; documented exclusions:
nested transitive steps `(a+/b)+`, graph-management UPDATE ops
(LOAD/CLEAR/DROP), federation. None of the exclusions touch the GraphQuery
vocabulary. But per (b), SPARQL completeness is *not* the load-bearing fact —
bounded-hop lives in Cypher.

**Posture verdict:** the evidence supports **full Neo4j-style pushdown as the
end state, landed Mongo-style (staged)**: stage 1 pushes the non-traverse
families (Cypher or SPARQL filters + `allowed_entities` membership) with
fallback traversal — fully conformant under D-04, cannot fail whole; stage 2
promotes traversal to bounded undirected Cypher var-length after differential
parity, with F-A2/F-A3 verified first. This is strictly stronger than Mongo's
position (no directedness doubling, no maxDepth off-by-one, no seed
exclusion — Cypher's semantics match CCF BFS far more closely than
`$graphLookup` does).

## Q5 — Temporal Mapping (the standout question)

**Verdict: encode `observed_at`/`superseded_at`/`valid_*` as canonical-text
RDF properties and filter in-query — the SQL-adapter model. Do NOT delegate
as-of to Fluree's native `t`. Confidence: HIGH.**

Fluree's own model statement [CITED: fluree.github.io/db/concepts/time-travel.md]:
"Every transaction in Fluree receives a unique **transaction time** (`t`) — a
monotonically increasing integer that represents the logical time of the
transaction," i.e., **when the fact was recorded in the database**. Fluree's
docs themselves direct valid-time modeling to explicit properties filtered in
WHERE — which is precisely CCF's existing posture.

Why delegation fails CCF's as-of (INV-CH7-14, "the state you held at T"),
whose implementation of record is the row filter
`observed_at <= T AND (superseded_at IS NULL OR superseded_at > T)` over
values that **arrive as data from L2** (no clock reads below the caller):

1. **Late-arriving observations.** A claim written at wall-clock W with
   `observed_at = O < W` must appear in `as_of(T)` for any `O ≤ T`. Fluree
   ledger state at the commit corresponding to T excludes it (not yet
   committed). Divergence class 1.
2. **Supersession timestamps are data.** Logical supersession sets
   `superseded_at = X` where X is supplied by L2, not the commit clock. A
   time-travel read at T brackets by commit order, not by X. Divergence
   class 2.
3. **Fluree's own backdating escape hatch cannot close the gap.** `/update`'s
   `eventTime` requires RFC 3339 values that are "monotonically
   non-decreasing, not future" — L2's write stream carries no monotonicity
   guarantee on `observed_at`. [CITED: endpoints.md]
4. **Decisive and structural:** the D-05 differential suite compares every
   adapter byte-identical to `ccf.graph.fallback`, which filters on the data
   properties. Corpus fixtures write claims whose `observed_at` values are
   arbitrary canonical timestamps uncorrelated with write order. A delegating
   adapter is **non-conformant by construction**, not merely unfaithful in
   theory.

Comparison with the Neo4j plan's physical-model choices (15.2-12): identical
posture, different serialization. Neo4j stores claim fields as node/
relationship properties in canonical RFC3339 text and refuses native temporal
types (the byte-drift trap); the Fluree adapter stores claim fields as JSON-LD
properties under an adapter-owned `@context` with **no `@type` coercion** —
plain JSON strings land as `xsd:string`, preserving lexicographic-equals-
chronological. The one Fluree-specific hazard: a context that maps a timestamp
property to `xsd:dateTime` would reintroduce the drift trap through the back
door. Verification item F-A5.

**The bi-temporal subtlety, answered directly:** yes — Fluree `t` is
transaction time, and CCF's as-of is observation-time-carried-as-data. L2
being the single writer makes the write *stream* well-ordered, but nothing
makes `observed_at` monotone in that stream, so transaction time can never
stand in for observation time. If anyone wishes to argue that "the state you
held at T" *should* mean transaction time, that is a whitepaper-semantics
question (§15 discipline: D-IMPL entry, stop, ask Dave) — not a decision an
adapter may take by choosing a substrate feature.

**What native time travel is still good for:** out-of-band audit. A Fluree
substrate gives auditors an independently immutable, content-addressed commit
history *underneath* CCF's replay record — a genuinely nice story for a
financial-services deployment ("the substrate itself cannot silently rewrite
state"). It is telemetry-tier value: never a replay input, never queried by
the adapter's `query()` path.

## Q6 — CI Container Story

[CITED: fluree.github.io/db/operations/{docker,admin-and-health}.md; Docker Hub API — all 2026-08-07]

| Property | Finding |
|---|---|
| Image / tag | `fluree/server:4.1.4` (exact pin per repo discipline; `4.1` minor tag exists). ~63–70 MB (debian:trixie-slim + Rust binary) — smaller than the neo4j or mongo images |
| Startup | Rust binary, `fluree server run`; docs' own k8s probes use `initialDelaySeconds: 5` — startup is seconds, not the JVM-scale wait of `neo4j:5-community` |
| Health gate | `GET /health` → 200 `{"status": ..., "version": ...}` / 503 — purpose-built for readiness gating; cleaner than the pg_isready/cypher-shell probes the existing legs use |
| Ephemeral mode | Default: no volume mounted → data lives in the container's writable layer and dies with it ("Ephemeral (testing)" is a documented mode). `docker run --rm -p 8090:8090 fluree/server:4.1.4` is the entire incantation |
| Auth | **Off by default** (data and admin auth both) — CI needs no token plumbing; production enables OIDC/DID-JWS per-environment |
| Memory | Cache auto-tiers by system memory; `FLUREE_CACHE_MAX_MB` caps it explicitly under CI limits. Indexing disabled by default (fine for corpus-scale data) |
| Env | `CCF_TEST_FLUREE_URL` mirrors `CCF_TEST_POSTGRES_DSN`/`CCF_TEST_NEO4J_URI` — the live-legs.yml service-block + pytest-mark pattern fits unchanged |

Fit with the container-gated CI leg pattern from plans 12/13: **drop-in, and
operationally the lightest of the four container legs.** One caution: release
cadence is fast (five patch releases April–July 2026) and 4.1.3 shipped
breaking SPARQL changes mid-minor — pin exact, and treat image bumps as
deliberate acts with a differential re-run, exactly the A1-style discipline
15.2-12 applies to the neo4j image.

## Q7 — Seam Fit and Effort

**Seam fit: nothing grows.**
- `GraphQuery` vocabulary: unchanged. Every family translates (Q4); what
  doesn't translate falls back (D-04). Fluree's extra powers (time travel,
  branches, SHACL, vector/BM25 graph sources) are *not reachable through the
  seam and must not be* — the vocabulary is a fixed commitment by D-02, and
  none of them are needed for conformance.
- `SourceAttestation`: unchanged. Fluree is tier-1 storage: the standard
  well-known value (`assembly-stamped` / `graph-supplied` / `None`). Its
  commit-signing/DID features do **not** tempt a new attestation dimension —
  D-09's dimensions describe *fabric* provenance, not substrate internals.
- Read seam: `query(q) → GraphView` is transport-agnostic; an HTTP adapter
  returning dict rows into the 15.2-03 materialization core is structurally
  identical to Neo4j's driver-record path. Rows come back as SPARQL-results
  JSON or Cypher JSON over httpx.
- **Write seam (`_GraphTxn`, plan 15.2-02) — the one real risk.** L2's writer
  drives typed per-operation calls with a rowcount contract (0 for an ignored
  duplicate claim id). SQL and Neo4j implement this inside a held database
  session/transaction. Fluree over HTTP has no held session: each `POST
  /update` is one atomic commit. Three candidate postures:
  1. **Buffered batch (recommended):** `_FlureeTxn` accumulates operations,
     commits as one `POST /update` (SPARQL UPDATE or multi-clause Cypher —
     "multi-clause write composition with atomic commits" is documented);
     atomicity preserved. Per-op rowcounts resolved by read-before-buffer —
     **safe precisely because of INV-CH7-10:** single-writer means no
     concurrent writer can invalidate the read between buffer and commit.
     Conditional inserts express as `INSERT ... WHERE FILTER NOT EXISTS`
     (SPARQL UPDATE) or `MERGE ... ON CREATE` (Cypher); the commit receipt's
     `flakes_added` cross-checks. Verification item F-A4.
  2. Bolt explicit transactions via the neo4j driver — works, but "explicit
     transactions require a single-node server; Raft/peer deployments reject
     BEGIN" [CITED: bolt.md] — fine for CI, a landmine for the exact
     enterprise cluster deployments motivating this adapter. Not recommended.
  3. Per-op autocommit — abandons write atomicity; not acceptable without a
     ruling.
  Whether `_GraphTxn`'s final Protocol shape (15.2-02 is unexecuted) admits
  posture 1 is the flip-condition risk named in the Executive Summary; the
  15.2-02 acceptance-criterion amendment retires it for one sentence.
- Idempotency: L2's idempotent claim upsert maps to conditional insert +
  `flakes_added==0` for duplicates. Fluree's `/upsert` endpoint
  (retract-then-assert per subject-predicate) is *not* the right primitive for
  claim-append semantics — use `/update` with explicit conditions.

**Fluree-specific pitfalls (the adapter plan's named-risk list):**
1. **JSON-LD datatype coercion** — timestamps must stay `xsd:string` (F-A5);
   the adapter owns a fixed minimal `@context` and never lets Fluree's default
   ledger context apply (a `PUT /context` default on the ledger could coerce
   silently — create the ledger with no default context).
2. **Read-after-write** — thread the last commit `t` from every write into
   subsequent reads via `Fluree-Min-T`, or the differential suite flakes
   against an eventually-indexed read path.
3. **Bounded type-alternation gap** (F-A3) and **parameterized bounds** (F-A2)
   — both have the 15.2-12 workarounds ready.
4. **Ledger addressing** — one CCF-owned ledger (e.g., `ccf:main`),
   `tenant_id` as a property predicate in every query (the SQL multi-tenant
   posture). Ledger-per-tenant is adapter-internal (D-IMPL-34) but complicates
   `Fluree-Min-T` and CI; not recommended v1.
5. **Auth/credential hygiene** — production bearer tokens env-templated in the
   manifest connection field; `graph_identity` = host/port/ledger only
   (T-04-24 precedent).
6. **Fast-moving upstream** — exact image pin; breaking changes have shipped
   inside a minor (4.1.3).

**Effort estimate relative to the Neo4j plan (15.2-12): similar overall;
read-side slightly cheaper, write-side meaningfully harder.**
- Cheaper: no new package, no extra, no lazy-import/mypy-override machinery,
  no driver-compat matrix (A1 collapses to "server image pin"); Cypher
  translation shapes lift from 15.2-12 nearly verbatim.
- Comparable: translation hook + differential leg + CI service block +
  boot/manifest wiring (backend Literal + env-templated URL + `make schemas`).
- Harder: `_FlureeTxn` buffered-batch write path (~1.5–2× the `_Neo4jTxn`
  effort) plus four F-A verification probes.
- Net: **one plan-pair of 15.2-12/13's size — two to three tasks, one wave** —
  *provided* the 15.2 suites and seams exist to build against, which is the
  routing argument.

## Q8 — Routing Recommendation

**Insert Phase 15.3. Amend one sentence of 15.2-02. Do not add a sixth
backend to 15.2.**

| Consideration | Weight |
|---|---|
| Seam-change findings | **None.** Read seam, vocabulary, attestation all fit unchanged (Q7). The flip condition the question names is absent |
| 15.2 delivery risk | Already HIGH with five backends / 14 plans / 9 waves. Fluree adds a *new class* of backend (first HTTP-wire substrate, novel transaction mapping) — the worst possible marginal addition to a phase whose cross-AI review flagged backend count as the risk |
| Suite reuse | Total. The D-05 differential + property suites, the corpus (incl. `allowed_entities`/resurrection strategies), the container-leg pattern, the extras/boot/manifest precedents all exist when 15.3 starts. 15.3's cost is one adapter plan-pair, nothing else |
| The no-refactor claim | A post-gate adapter that goes green against the suites **without an SDK change is the phase's own success criterion demonstrated on a real substrate** — stronger evidence than a sixth in-phase backend, which proves nothing about post-gate extensibility |
| Adoption timeline | 15.2 is planned, not executing. 15.3 inserted immediately after is one phase gate away; amending 15.2 puts Fluree *behind* waves 1–8 anyway (it would slot as wave 8.5/9) — the calendar difference is small, the risk difference is not |
| The one hedge | The `_GraphTxn` Protocol (15.2-02, wave 1) is the only 15.2 artifact whose shape could foreclose an HTTP substrate. Amend its acceptance criteria now: "the `_GraphTxn` Protocol must be implementable by a remote substrate whose commit is a single batched transaction (no held session), with per-operation rowcounts resolvable before commit." Cheap, testable in review, and it converts the flip risk into a design constraint |
| The precondition | D-IMPL question 2 (which Fluree line the institution runs) and question 1 (tier-1 substrate vs tier-3 external source) should be answered before 15.3 is *planned* — a v2 shop or a read-their-existing-graph ask changes the deliverable entirely |

**What would flip this to amending 15.2:** only a ruling that the write-seam
constraint cannot be expressed as an acceptance criterion and must instead be
proven by an in-phase implementation — i.e., Dave judging the one-sentence
hedge insufficient. On the evidence, it is sufficient: posture-1 batching is
implementable against the documented API, and single-writer makes its one
tricky step (read-before-buffer) sound.

---

## Package Legitimacy Audit

No package installation is proposed; no slopcheck install run was needed
(nothing to install — the recommended wire client is the already-pinned core
dependency). Candidate clients were vetted against the registries directly:

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `httpx` | PyPI | mature, already pinned `==0.28.1` in core (pyproject.toml:44) | very high | github.com/encode/httpx | previously vetted in-tree | **Approved — already a core dependency; zero new packages for this adapter** |
| `fluree-py` | **NOT on PyPI** (404 verified 2026-08-07) | n/a | n/a | github.com/crcresearch/fluree-py (1 star, third-party) | n/a — nothing to check | **Rejected.** Unregistered name documented as `pip install fluree-py` upstream — a squattable-name supply-chain hazard; never reference it in plans |
| `aioflureedb` | PyPI | 2020-09 → last release 2024-05 (dormant) | low | github.com/pibara/aioflureedb (solo maintainer) | not run (rejected pre-install) | **Rejected.** Targets the dead v2 API (block/command/dbs endpoints, v2 signed txns); "late beta" self-description |
| *(alternative wire)* `neo4j` | PyPI | — | — | github.com/neo4j/neo4j-python-driver | Approved in 15.2-RESEARCH audit | Viable Bolt-wire alternative; **not recommended** as default (couples Fluree to the `neo4j` extra; Bolt explicit txns are single-node-only) |

**Packages removed due to slopcheck [SLOP] verdict:** none (none proposed)
**Packages flagged as suspicious [SUS]:** none — but the unregistered
`fluree-py` name is recorded above as a hazard for any future vetting pass.

---

## Open Questions for Dave (D-IMPL candidates)

Per CLAUDE.md §15, these are surfaced, not defaulted. Numbered locally;
`D-IMPL-NN` numbers are minted in `docs/DECISIONS.md` if/when ruled.

1. **Tier-1 substrate or tier-3 source? (the scope ambiguity — gating.)**
   Does the institution want (a) CCF deployed *with Fluree as its L3
   substrate* (L2 writes a CCF-owned ledger; the adapter researched here), or
   (b) CCF *reading their existing Fluree knowledge graph* (data CCF never
   wrote)? (b) is a tier-3 raw external source — explicitly deferred by
   Dave's own 2026-08-07 scope ruling and reachable later via the D-08/D-09
   design (another admission gate, same wrapper) — a tier-1 adapter does not
   deliver it. If the answer is (b) or "both," the routing conversation
   changes shape entirely (it becomes the tier-3 phase's first concrete
   customer, not a 15.3 storage adapter).
2. **Which Fluree line does the institution run?** v2 (Clojure/AGPL, legacy
   stable) vs v4 (Rust/BSL, GA April 2026). The researched adapter targets v4
   only; a v2 adapter is a different codebase against a different API and
   license. If the institution is on v2, is their v4 migration timeline known?
3. **Routing ruling:** insert Phase 15.3 + amend 15.2-02's acceptance criteria
   with the remote-batched-substrate constraint (recommended), vs amend 15.2
   with a sixth backend. Recommendation and weighing in Q8; the ruling is
   Dave's.
4. **Write-transaction posture for remote HTTP substrates** (only if 15.3 is
   ruled in): buffered-batch single-commit (recommended; sound under
   single-writer) vs Bolt explicit transactions (single-node-only) vs per-op
   autocommit (abandons atomicity — presumably unacceptable, listed for
   completeness). This can also be left to the 15.3 planner against the
   amended 15.2-02 contract if Dave prefers.

## If Ruled In: Planning Implications

**Phase 15.3 shape (assuming the Q8 recommendation): 2 plans, 2 waves.**

- **Wave 1 — 15.3-01: Fluree backend + write path + wiring.** Mirrors 15.2-12
  Task 1: `src/ccf/graph/backends/fluree.py` (httpx client, store envelope,
  credential-free `graph_identity`, adapter-owned JSON-LD `@context` with
  string-typed temporal properties, dict rows into `materialize_view`);
  `_FlureeTxn` in `ccf.graph._writer` (buffered-batch posture, rowcount
  contract via read-before-buffer + `flakes_added` cross-check — F-A4 verified
  first); boot exclusivity + manifest `backend` Literal + env-templated URL
  (+ optional bearer token) + `make schemas`. **No extra, no lazy import** —
  httpx is core; only a `fluree` pytest marker. Verification probes F-A1
  (container round trip), F-A4, F-A5 run before code commits to them.
- **Wave 2 — 15.3-02: Cypher translation + differential leg + CI.** Mirrors
  15.2-12 Task 2 with the 15.2-13 staging discipline: stage 1 = non-traverse
  pushdown (filters + `allowed_entities` membership as `$param`) + fallback
  traversal — conformant under D-04, cannot fail whole; stage 2 = bounded
  undirected Cypher var-length promotion after F-A2 (parameterized bounds) and
  F-A3 (type-set predicate form) verify, hop admissibility via
  `all(n IN nodes(p) WHERE ... AND n.entity_uri IN $allowed)`, promotion only
  at byte-identity over the full corpus incl. resurrection shapes.
  `fluree/server:4.1.4` service block in ci.yml/live-legs.yml gated on
  `GET /health`, `CCF_TEST_FLUREE_URL` env. Phase close re-runs the 15.2-14
  gate checks scoped to the new leg.

**Do the 15.2 conformance suites cover it unchanged? Yes — by design.**
The differential suite is backend-parametrized against the fallback oracle;
adding a `fluree` param with a mark is the entire suite change (the same
one-fixture-param extension 15.2-12/13 make). The property suite runs on the
fallback and does not change at all. The semantics prose
(`GRAPH_QUERY_SEMANTICS.md`) does not change — Fluree implements existing
clauses; its translation choices cite the same `GQ-NN` anchors. The corpus
(incl. `allowed_entities`/resurrection strategies) transfers whole. **That the
suite-side diff is one fixture parameter is itself the demonstrated no-refactor
claim** — worth stating in the 15.3 gate package as D-IMPL-87-adjacent
evidence.

**What 15.3 must not do:** touch the `GraphQuery` vocabulary or
`SourceAttestation` (nothing in Fluree needs it — Q7); expose Fluree time
travel, branching, or SHACL through the seam; introduce a Python Fluree client
dependency; let the adapter construct records or ordering (Pitfall 5); let
timestamps become typed literals (F-A5).

---

## Sources

### Primary (HIGH confidence — all fetched 2026-08-07)
- `github.com/fluree/db` — README, `LICENSE` (verbatim BSL 1.1 text incl.
  Additional Use Grant and Change Date), GitHub API metadata, releases API
  (v4.0.0…v4.1.4 dates)
- `fluree.github.io/db` (the db repo's official docs; main docs portal is
  labs.flur.ee/docs) — `api/endpoints.md`, `query/sparql.md`,
  `query/cypher.md`, `query/jsonld-query.md`, `concepts/time-travel.md`,
  `guides/bolt.md`, `operations/docker.md`, `operations/admin-and-health.md`,
  `llms.txt`
- GitHub API — `fluree/ledger` (AGPL-3.0, Clojure, v2), `fluree/server`
  (Clojure, no license file detected, v3.0.0-alpha3 latest)
- Docker Hub API — `fluree/server` tags 4.0.0–4.1.4 with dates and sizes
- PyPI — `pip index versions` probes + `pypi.org/pypi/{fluree-py,aioflureedb}/json`
- Repository tree — `pyproject.toml` (httpx==0.28.1 core pin),
  15.2-CONTEXT/RESEARCH/12-PLAN/13-PLAN, ROADMAP §Phase 15.2, CLAUDE.md

### Secondary (MEDIUM confidence)
- `github.com/crcresearch/fluree-py` repo page (maintenance/status read)
- Web search corroboration of the Python client landscape

### Marked assumptions ([ASSUMED], each with a named verification item)
- F-A2: Cypher var-length bounds not parameterizable (mirror of 15.2's A2;
  harmless either way — verify with one HTTP call)
- F-A3: `all(r IN relationships(p) WHERE type(r) IN $types)` correctly
  substitutes for the deferred bounded type-alternation form
- F-A4: SPARQL UPDATE conditional insert + `flakes_added` faithfully
  implements the `_GraphTxn` rowcount contract
- F-A5: adapter-context JSON strings land as `xsd:string` with no datatype
  coercion (byte-drift trap)
- `allowed_entities` list size limits over HTTP body (no documented cap)
- Institutional-deployment inference in Q1 (which line an FI runs) — no
  public data; resolved only by asking (D-IMPL question 2)

**Research date:** 2026-08-07
**Valid until:** ~2026-09-06 for ecosystem facts — shorter than usual because
the v4 line ships weekly-scale patches with at least one in-minor breaking
change on record (4.1.3); re-verify current version and Cypher feature list
when 15.3 planning starts.
