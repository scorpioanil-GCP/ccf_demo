# The deadline rows: SEC-013, SEC-017, SEC-023, SEC-009 under the three-check acceptance

Rulings: `docs/DECISIONS.md` `D-IMPL-374` (the four choices, the base, the specimen re-pin). Acceptance: Dave, 2026-10-06 19:21 MST.
Base: branch `deadline-rows` @ `c6b75f8c` (= `main` `e561e01f` + `integration-batch5` `2433d13e`).

## Global Constraints (binding on every task)

1. **Acceptance per row is exactly three things.** (a) A test RED on the base tree and GREEN after the patch, asserting the
   hole AS WORDED by the finding (not a proxy). (b) ONE named severing: a specific edit that removes the new check, under
   which that test goes RED again — executed with every `__pycache__` purged and `python -B`, the file restored from
   saved bytes with the sha checked, the edit + command + red output recorded. (c) Nothing else closes it. Commit the red
   test FIRST in its own commit (`test(SEC-0NN): red — <hole>`), then the fix (`fix(SEC-0NN): <mechanism>`).
2. **Interpreter and imports.** `/home/parkave/ccf_code/.venv/bin/python`; prefix EVERY python/pytest/mypy invocation with
   `PYTHONPATH=src:runtime` from the worktree root (otherwise the editable install at `/home/parkave/ccf_code` is imported).
   Verify once: `PYTHONPATH=src:runtime python -c "import ccf; print(ccf.__file__)"` must print a path inside your worktree.
3. **Nothing touches the curated estate at `192.168.4.76` and no local database server is started** (Dave's rules; see
   `tests/examples/estate_guard.py`). Tests are offline: SQLite, in-memory, fakes. A network-store lease is proven with a
   fake or a recorded-protocol double, never a live Mongo/Neo4j/Fluree.
4. **Invariants.** No harness import under `src/`. No prompt or instruction string literals in code. Typed contracts
   (`extra="forbid"`). Mechanism, never values: anything a deployment declares is read from an artifact or a constructor
   argument; a roster of SDK field or type NAMES is mechanism. Single-writer: nothing but L2 writes the graph. US English.
   Cite the finding id and `D-IMPL-374` in the docstring of every changed public symbol.
5. **Scope.** Change only the files the task names plus tests and the `docs/surface-changes/374-0N-<slug>.md` fragment
   (seven-field shape per `docs/surface-changes/README.md`) for every new or reshaped public name, so the three surface
   gates stay green (run them directly; regenerate the manifest with `tools/dump_surface.py` if the gate requires). No
   `DECISIONS.md` edits (the controller writes the ledger line). Do not weaken or delete an existing test to get green; if
   an existing test pins the defective behavior, change it in the fix commit with the reason in the commit message.
6. **Counts come from captured files.** Run the covering test directories with `-p no:cacheprovider -q 2>&1 | tee <report
   dir>/<task>-tests.txt`; report passed / failed / errors as three numbers from that file. Then `python -m mypy` (project
   config) and `python -m tools.lints --all` with exit codes.

## Task 1 — SEC-013: a network-store writer refuses to mint without a declared, held lease

Files: `src/ccf/graph/protocols.py` (`WriterLease`, `WriterLeaseHeld`, `ProcessScopedWriterLease`, `WriterLeaseScope`),
`src/ccf/graph/_writer.py` (the mint path, `lease_scope`), `src/ccf/graph/registry.py` (`writer_lease`), the Fluree,
MongoDB and Neo4j store adapters (find them under `src/ccf/graph/` and `runtime/`), tests under `tests/graph/`.

Measured today (batch 5): the SQLite store holds an exclusive lock file and the Postgres store a `pg_try_advisory_lock`
keyed on the graph identity; the Fluree, MongoDB and Neo4j stores only DECLARE `lease_scope="process"` and keep the
process-local writer set, so a second process mints a writer for the same network graph. The hole as worded (SEC-013):
"`_LIVE_WRITERS` is process-local" — single-writer is not enforced across processes for the network stores.

Fix (ruling (a)): a network store's writer construction requires a `WriterLease` to be declared and HELD before minting:
the store's constructor/boot takes a `writer_lease: WriterLease` (deployment-declared; the reference implementations are
the existing SQLite lock-file lease and Postgres advisory lease, reusable against any graph identity), the mint path
acquires it before minting and releases it with the boot token, and a network store with NO declared lease REFUSES to
mint a writer by name (`WriterLeaseRequired`, a typed refusal citing SEC-013 / D-IMPL-374) — refuse-when-undeclared,
the same posture as the temporal window. Red tests: (a) for each of Fluree, Mongo, Neo4j (with the store's network client
faked so no socket opens): two "processes" (two registries in one test, or a subprocess against a shared lock-file
lease) both mint a writer today → the second is refused with `WriterLeaseHeld` once a shared lease is declared;
(b) a network store with no declared lease mints today → refuses with `WriterLeaseRequired`. Severing: delete the
lease acquisition on the mint path (both tests redden) — one edit. The `BootToken.lease_scope` reader gap
(SEC-013-C-03) closes as a consequence: record the held lease's scope and identity on the token. Document on the
security page §4.6 in two sentences (the page already describes the per-store scope).

## Task 2 — SEC-017: within-tenant product entitlement on the grant

Files: the token/grant contract that carries `tenants` (find `TokenGrant` — `runtime/ccf_runtime/mcp/tenancy.py` and the
grant artifact schema it is read from), `runtime/ccf_runtime/mcp/experience.py` (the three agent and replay tools the
`D-IMPL-129` row names), `runtime/ccf_runtime/authz/product_entitlement.py` if the product door's entitlement already
has a reusable shape, tests under `tests/mcp/` and `tests/authz/`.

Measured: `tests/mcp/test_tenant_guard.py` pins that the three tools are tenant-guarded; `D-IMPL-129`'s remaining pin is
that WITHIN a tenant any principal reaches every product through those tools (the hole as worded for SEC-017 after
Dave's reading at `D-IMPL-370`: the remedy includes within-tenant entitlement). Fix (ruling (a)): the grant gains a
declared `products` roster (product class names or ids — whatever identity the tools already resolve a product by;
measure and say which); present = the three tools refuse, by name, a product outside the roster for that principal;
absent = tenant-wide, today's behavior, and the security page states that declaring the roster is the deployment's
obligation. No SDK default roster. Red tests: a principal with a declared roster reaches a product outside it today →
refused by name; a principal with no roster still reaches tenant-wide (control). Severing: delete the roster check in the
tools' entitlement path. Delete the `D-IMPL-129` fail-when-fixed pin by name in the fix commit with the reason, if one
exists for this limb.

## Task 3 — SEC-023: classification authority enforced at the construction of the consumer

Files: `src/ccf/assembly/worker.py` (`EntityResolutionSpec` with `_one_authority_per_governed_attribute`,
`_judge_authority`), the artifact-time guard batch 5 added (grep `SEC-023` under `src/` and `runtime/`), the
`PolicyFilter` parameters contract and `GraphQuery` classification map (grep `PolicyFilterParametersArtifact`,
`classification` under `src/ccf/products/` and `src/ccf/operators/`), `ccf.boot.boot` and `build_operator_registry`
(`src/ccf/deployment/`), the frozen specimens `examples/cp-04-corporate-family-tree` and
`examples/cp-05-credit-exposure-rollup` configs, tests under `tests/assembly/`, `tests/products/`, `tests/deployment/`.

Measured (`D-IMPL-372` amendment): the construction-time guard inspects only parsed `PolicyFilterParametersArtifact`
objects on the paved doors; a `GraphQuery`-only classification map, a hand-built `PolicyFilter` in
`deployment_operators`, a hand-composed `ccf.boot.boot`, and a per-request `build_operator_registry` are classification
paths that neither enforce authority nor refuse. Also carried: `SEC-023-C-01` — a non-authoritative source that OMITS the
governed attribute blanks the label with NO audit event. Fix (ruling (a)): a `PolicyFilter` (its parameters) or a
`GraphQuery` carrying a classification map REFUSES TO BE CONSTRUCTED unless the governing `EntityResolutionSpec` declares
authority for every attribute it names (typed refusal citing SEC-023 / D-IMPL-374); the artifact-time door check stays
as the early refusal; an omission by a non-authoritative source emits an audit event. Red tests: one per uncovered path
(four) — each constructs the consumer today and must refuse; plus the C-01 audit test (today no event; after, one).
Severing: delete the authority check in the consumer's constructor — the four tests redden (the artifact-time test stays
green: say so). **Frozen specimens (executor ruling (b) at `D-IMPL-374`):** add the authority declaration to the cp-04
and cp-05 configs with a dated note in each README, so `tests/products/test_cp05_canonical_path.py` (three ERRORs on the
base — name them) goes green; change nothing else in those examples.

## Task 4 — SEC-009: the minimum erasure, built to the ruled design

Spec: `/home/parkave/ccf_wt/d367-design/docs/D-IMPL-367-ERASURE-DESIGN.md` (read §1–§8 and §11 in full; U1–U12 are RULED on
the recommendation column at `D-IMPL-374`), plus `D-IMPL-367` in `docs/DECISIONS.md` (the entry; G1–G10 locked).
Files: a new package `src/ccf/erasure/` (contracts `ErasureSubject`, `ErasureRecord` with `subject_ref` hashed by a
deployment-declared salt per subject class; the registry-mirror index; the decorating `ArtifactStore` that refuses to
serve erased content and is composed ALWAYS; the replay-input path list as a mechanism constant), the artifact store
composition site (`src/ccf/artifacts/`), the HTTP route rendering for `erased-content` (410 at `reasoned`/`full`;
the route's not-found rendering at `minimal`) under `runtime/ccf_runtime/http_api/`, the erasure door and its
deployment-declared, factory-validated request/approval workflow (reuse the HITL `ApprovalGate` and the workflow
definition artifact; no SDK-shipped approval shape), tests under `tests/erasure/`, `tests/artifacts/`, `tests/http_api/`.

The hole as worded (SEC-009): the fabric has no mechanism to erase a subject's content; immutability has no counterpart
for a right-to-erasure obligation. Minimum build, in this order, each red-first: (1) `ErasureRecord` written through a
governed door with a deployment-declared approval, minimum age present with no default, legal-hold refuses; (2) the
decorating store consults the registry mirror on every read and serves an `erased-content` reading (never the bytes)
for an erased artifact — in-process and over HTTP (410); `exists` does NOT consult; (3) replay of a decision whose
inputs include an erased artifact stays positive with the erasure disclosed (the design's §5.2); (4) no un-erasure verb
anywhere. Red tests: an erased artifact is still served today (in-process and HTTP); replay today has no disclosure
layer; a write without approval or under a hold succeeds today. Severing: delete the consult in the decorating store's
read path — the served-reading tests redden (one edit). Field-scoped erasure, the retention lifecycle and pseudonymization
are OUT; say so in the module docstring. This is the largest lane: report BLOCKED with the measurement the moment the
design cannot be realized as written rather than inventing around it.
