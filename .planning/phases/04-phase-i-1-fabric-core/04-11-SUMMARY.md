---
phase: 04-phase-i-1-fabric-core
plan: 11
subsystem: similarity-substrate
tags: [l4, similarity, d-impl-03, d-impl-07, conformance, vector-index]
requires:
  - 04-05 (SimilarityIndexProtocol seam, TokenOverlapIndex, SimilaritySelect operator)
  - 04-06 (operator registry, planner, compose/IntermediateCache, params)
  - 04-01 (pyproject pins — sqlite-vec 0.1.9 core, chromadb 1.5.9 as the `chroma` extra)
provides:
  - a finalized two-Protocol seam — read-only SimilarityIndexProtocol (what the operator holds) and MutableSimilarityIndexProtocol (what a deployment holds)
  - EmbedderProtocol, the D-IMPL-07 text-to-vector seam, with no implementation in /src by design
  - SqliteVecIndex, the D-IMPL-03 dev-default vector substrate on sqlite-vec vec0
  - ChromaIndex, the D-13 second reference substrate, importable and shippable without chromadb installed
  - one parametrized conformance suite covering all three backends (D-16)
  - cosine_score_percent and order_hits — the two renderings every backend shares so that swapping substrates cannot shift a score or a tie
affects:
  - nothing above L4 changed; SimilaritySelect was already typed against the Protocol and was not touched
  - a deployment can now populate a similarity corpus through the Protocol rather than by constructing an index around a prebuilt mapping
  - the λ_c/D_c and product waves are unaffected — this plan added no clock read and no Control-Plane key
tech-stack:
  added:
    - sqlite-vec 0.1.9 (already a core pin; first use)
    - chromadb 1.5.9 behind the `chroma` optional extra (first use; never a core dep)
  patterns:
    - two Protocols where the consumer needs less than the producer, so the read-only half is what the operator is typed against and corpus admission is not reachable from L4
    - shared rendering helpers (cosine_score_percent, order_hits) instead of per-backend arithmetic, so backend parity is structural rather than tested-for
    - lazy vendor import inside __init__, so the module is importable and the dependency is demanded only at construction
    - conformance param carrying its own marker and skipif, so `-m chroma` selects a backend leg of every test rather than a module
key-files:
  created:
    - src/ccf/similarity/embedder.py
    - src/ccf/similarity/sqlite_vec_index.py
    - src/ccf/similarity/chroma_index.py
    - tests/conformance/test_similarity_index.py
  modified:
    - src/ccf/similarity/protocol.py
    - src/ccf/similarity/__init__.py
    - .gitignore
decisions:
  - "Corpus admission takes text, not vectors. The plan's behavior sketch said `upsert(id, vector, metadata)`, but the text-to-vector step belongs to the index that chose an embedder (D-IMPL-07), not to the caller. A vector-shaped signature would also have made the lexical reference index unimplementable against the same Protocol, and one shared conformance suite (D-16) is worth more than a signature that matches whichever backend was written first."
  - "The seam is two Protocols, not one. SimilarityIndexProtocol stays read-only and is what SimilaritySelect is typed against; MutableSimilarityIndexProtocol adds upsert/delete. An operator that could admit content to the corpus its own provenance pins a version of is the single-writer discipline failing one layer over."
  - "tenant_id is a vec0 partition key, not a filtered column. Partitioning puts isolation in the physical layout, so a query that lost its scoping clause cannot range over a neighbour's vectors (T-04-25). entity_uri is an auxiliary column rather than the primary key because vec0 enforces primary-key uniqueness globally across partitions — a URI used by two tenants would collide, which is exactly the coupling the partition key exists to prevent."
  - "Ranking scans the supplied candidates exactly, in both vector backends, rather than running KNN and intersecting. Policy runs before Similarity (INV-CH7-26), so the candidate set is already the answer's universe; a top-n over the whole partition would silently drop admissible candidates that lost to inadmissible ones."
  - "Chroma collections are named by SHA-256 digest of the tenant id, one collection per tenant. Chroma constrains names to 3-512 characters of [a-zA-Z0-9._-], which a tenant id is under no obligation to satisfy; a sanitizing transform is not injective, so two ids differing only in rejected characters would collapse onto one collection — a cross-tenant merge produced by a naming convention. Per-tenant collections rather than a tenant_id metadata filter because a collection a query never opened is not one it can leak from."
  - "index_version on the vector backends is the declared corpus version composed with the embedder's model_version. INV-CH7-27 names both, and they are two independent ways for an answer to change — re-ingesting the corpus and re-embedding it. A version identifying only one would let a replay resolve an index that agrees about its own name while disagreeing about every vector in it."
  - "cosine_score_percent is shared rather than implemented per backend. sqlite-vec and Chroma both report 1 - cos; two independent renderings would let a deployment's scores shift when it swapped substrates, with the operator's minimum_score_percent floor still set for the old one."
  - "No embedder implementation ships in /src, breaking the otherwise-universal reference-impl-beside-Protocol rule (CLAUDE.md §11) deliberately. The only honest reference embedder is a model call, which would put a semantic stage inside modules CINV-03 keeps algorithmic and would make `pip install ccf` drag a model runtime behind it. The seam is proven instead by a deterministic hashing fake in the conformance suite."
  - "sqlite_vec_index.py and chroma_index.py are NOT tagged __ccf_mode__ = \"algorithmic\". Both invoke an EmbedderProtocol, and an embedding model is a semantic stage. The tag would assert something untrue about the code path; CINV-03 is worth more as a claim than as a decoration. protocol.py and embedder.py stay tagged, because declaring a shape is not calling a model."
metrics:
  duration: ~45 min
  completed: 2026-07-25
  tasks: 2
  commits: 3
---

# Phase 4 Plan 11: The SimilarityIndex Substrate — sqlite-vec, Chroma, One Suite Summary

D-IMPL-03 is now a seam with three implementations behind it rather than a
Protocol with one reference impl and two promises. `TokenOverlapIndex`,
`SqliteVecIndex`, and `ChromaIndex` pass the same 20-test conformance suite,
and the Similarity operator — untouched by this plan — cannot tell which one it
is holding.

## What Was Built

**Task 1 — the Protocols, the embedder seam, and sqlite-vec** (`34bb8f1` RED,
`1b5539e` GREEN).

The seam split in two. `SimilarityIndexProtocol` keeps exactly what it had —
`index_version` and `rank` — and stays what `SimilaritySelect` is typed
against. `MutableSimilarityIndexProtocol` adds `upsert` and `delete`. The split
is not tidiness: an operator holding the mutable Protocol could edit the corpus
its own provenance pins a version of, which is the single-writer discipline
(CLAUDE.md §10) failing one layer up from where it is enforced.

`EmbedderProtocol` (D-IMPL-07) declares `model_version`, `dimensions`, and
`embed`. It ships no implementation, and that is the one place this plan
deliberately breaks CLAUDE.md §11's reference-impl-beside-Protocol rule — see
the decisions above. The conformance suite proves the seam with a deterministic
SHA-256 bag-of-tokens fake, so the vector backends are testable in I.1 where no
model exists yet.

`SqliteVecIndex` stores vectors in a sqlite-vec `vec0` virtual table with
`tenant_id` as a **partition key**, verified against the installed 0.1.9 rather
than assumed (RESEARCH assumption A3 — `sqlite_vec.load(conn)` and `vec0`
confirmed unchanged; the *global* primary-key uniqueness across partitions was
not in the research and is why `entity_uri` is an auxiliary column). Extension
loading is re-disabled in a `finally` immediately after the load, because
leaving it armed on a connection the deployment goes on to use means arbitrary
SQL on that connection can load arbitrary shared objects.

**Task 2 — Chroma as an optional extra** (`97d957b`).

`ChromaIndex` on chromadb 1.5.9, verified against the installed package rather
than assumed (RESEARCH assumption A2 — `PersistentClient` and the collection
API confirmed; two things the research did not have surfaced in practice and
are handled in code, below). `import chromadb` lives inside `__init__`, so
`import ccf` *and* `import ccf.similarity.chroma_index` both succeed without the
extra — proven twice, once by a monkeypatched meta-path blocker in the suite and
once by actually building a venv without the extra and running the full suite in
it (351 passed, 23 skipped).

## Key Implementation Details

- **Chroma 1.5.9 raises `InternalError: Error finding id` when `query(ids=...)`
  names an id the collection does not hold.** The Protocol is tolerant here by
  contract — "not in the corpus" is an omission, not an error, because it is a
  different fact from "in the corpus and irrelevant". So `rank` resolves the
  present ids with a `get` first and restricts the search to those. The extra
  round trip is the price of the substrate being strict where the contract is
  tolerant; letting the error escape would have turned an omission into a
  failure.
- **Both vector backends deduplicate the candidate tuple.** A caller who
  repeated a candidate would otherwise see the entity twice in a result set
  that is supposed to be a ranking of a set.
- **`order_hits` is one function, not three.** "Descending score" is a
  *partial* order; the residue gets settled by whatever the substrate's
  iteration happened to do — a dict's insertion order here, a B-tree's key
  order there. Two conformant indexes would then disagree about a tie, and a
  replay comparing provenance bit for bit would call that a changed decision.
- **A zero vector scores 0, not NaN and not an error.** Text the embedder had
  nothing to say about is in the corpus and irrelevant, which the contract
  already has a meaning for.
- **Nothing in `src/ccf/operators/` mentions either backend.** `grep -rn
  "sqlite_vec\|chroma" src/ccf/operators/` returns nothing; `SimilaritySelect`
  was verified against the Protocol and, as the plan instructed, not forked.

## Deviations from Plan

### Interpretations

- **`upsert` takes `text`, not `(vector, metadata)`.** The plan's `<behavior>`
  sketched a vector-shaped signature. Taking vectors would have put the
  embedder choice on the caller and made the lexical reference index
  unimplementable against the same Protocol — which would have cost the single
  shared conformance suite the plan's own success criterion asks for (D-16).
  Recorded as a decision above; no `metadata` parameter was added because
  nothing in I.1 has a use for one and an unused parameter in a Protocol is a
  contract nobody can drop later.
- **The seam is two Protocols, not one.** The plan said "finalize `protocol.py`
  (kw-only `tenant_id`, typed result contract)". Both were already true in the
  04-05 slice. The finalization that was actually missing was the corpus
  admission surface, and putting it on the *same* Protocol the operator holds
  would have handed L4 a write handle.
- **No embedder reference implementation.** The plan said "add `embedder.py`
  with `EmbedderProtocol` plus a deterministic test embedder in tests (not
  src)", which is what was done — noted here because it is a standing exception
  to CLAUDE.md §11 and should not be read as an oversight.
- **`# type: ignore[import-untyped]` on the `sqlite_vec` import rather than a
  `pyproject.toml` mypy override.** sqlite-vec 0.1.9 ships no `py.typed`. The
  established precedent in this repo is the project-wide override used for
  PyYAML, but the untyped surface here is genuinely one module wide (two
  function calls and one SQL function, each coerced to a declared type before
  it leaves the file), and this plan ran in a parallel worktree alongside an
  agent whose scope also touches packaging-adjacent files. A localized ignore
  avoids a merge conflict over an append-only config section. Worth revisiting
  as a convention question if a third untyped dependency appears.

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `build/` left untracked by a non-editable install**

- **Found during:** Task 2, at the commit boundary
- **Issue:** Installing the `chroma` extra with `pip install ".[chroma]"`
  (no `-e`) both produced a `build/` directory and silently replaced the
  editable install, which is what made the first chroma conformance run report
  `No module named 'ccf.similarity.chroma_index'` for a module that existed on
  disk.
- **Fix:** Reinstalled editable (`pip install -e ".[dev,chroma]"`), removed
  `build/`, and added it to `.gitignore` so the artifact cannot be committed by
  a future `git add`.
- **Files modified:** `.gitignore`
- **Commit:** `97d957b`

## TDD Gate Compliance

Task 1 ran a clean RED → GREEN, with the failing suite committed before any
implementation existed:

| Gate | Commit | State |
|---|---|---|
| RED | `34bb8f1` | collection error — `ccf.similarity.embedder` absent |
| GREEN | `1b5539e` | 37 passed |

Task 2 was not marked `tdd="true"` in the plan and extended the existing suite
with a third backend param plus the optionality and composition assertions;
those tests and the implementation landed together in `97d957b`.

## Verification

| Check | Result |
|---|---|
| `.venv/bin/pytest tests/conformance/test_similarity_index.py -q` | 62 passed (3 backends) |
| `.venv/bin/pytest tests/conformance/test_similarity_index.py -q -m chroma` | 18 passed, 38 deselected |
| `HYPOTHESIS_PROFILE=ci .venv/bin/pytest tests/properties -q` | 73 passed |
| `.venv/bin/pytest tests -q` (chroma installed) | 371 passed, 3 skipped |
| `pytest tests -q` in a venv **without** the chroma extra | 351 passed, 23 skipped |
| `python -c "import ccf, ccf.similarity.chroma_index"` without chromadb | succeeds |
| Skip reason without the extra | contains `chroma` — "the optional \`chroma\` extra is not installed" |
| `.venv/bin/mypy --strict src` | Success, 49 source files |
| `.venv/bin/python -m tools.lints --all` | exit 0, zero allowlist entries added |
| `grep -rn "sqlite_vec\|chroma" src/ccf/operators/` | 0 matches |
| Composition-preservation with each backend under `SimilaritySelect` | green, 3 params × curated graphs × both orders |
| sqlite-vec 0.1.9 API (`load`, `vec0`, partition key, `vec_distance_cosine`) | verified against the installed package, not assumed (A3) |
| chromadb 1.5.9 API (`PersistentClient`, `get_or_create_collection`, `query(ids=...)`) | verified against the installed package, not assumed (A2) |
| Post-commit deletion check, all 3 commits | no deletions |
| Files outside scope (`src/ccf/graph/*`, `tests/conftest.py`, `tests/conformance/test_graphstore.py`, `.github/workflows/ci.yml`, `pyproject.toml`, `STATE.md`, `ROADMAP.md`) | untouched |

## Known Stubs

None.

Two bounded-scope items, both deliberate and both named above rather than
deferred silently:

- **No embedder implementation in `/src`.** A deployment supplies its own; the
  vendor adapters land with the semantic surface in a later phase. The seam is
  real and conformance-tested.
- **`TokenOverlapIndex` remains lexical.** It is the reference index, not a
  recommendation — genuinely enough to make the Similarity category rank,
  threshold, and pin a version, and deliberately not enough to be mistaken for
  production retrieval.

## Threat Flags

None new. The two registered threats are mitigated as planned:

- **T-04-25 (cross-tenant similarity hits)** — tenant scoping is in the storage
  layout in both vector backends (vec0 partition key; per-tenant Chroma
  collections named by digest), and the conformance suite asserts it three
  ways on every backend: another tenant's entity is absent rather than ranked
  last, one URI holds independent content in two tenants, and a delete in one
  tenant leaves the other intact.
- **T-04-26 (chromadb transitive supply chain)** — chromadb is the `chroma`
  optional extra at the slopcheck-audited pin 1.5.9, never a core dependency,
  with the import deferred to construction. Proven in a real venv without the
  extra, not only by monkeypatch.

## Self-Check: PASSED

All 4 created files and 3 modified files exist on disk; all three commit hashes
(`34bb8f1`, `1b5539e`, `97d957b`) are present in `git log`.
