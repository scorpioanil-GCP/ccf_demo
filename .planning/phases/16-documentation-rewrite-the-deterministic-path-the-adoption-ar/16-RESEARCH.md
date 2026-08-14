# Phase 16: Documentation Rewrite — The Deterministic Path & The Adoption Argument - Research

**Researched:** 2026-08-13
**Tree state:** `main @ 6e95da0` (the `--no-ff` merge of `phase-15.6`)
**Domain:** adopter-facing example + published documentation against the post-15.6 surface
**Confidence:** HIGH on everything measured against the tree; LOW/flagged where marked

> **This supersedes the 2026-08-10 research (recoverable at `5b3f4cf`).** That pass
> described the pre-15.5 surface. Where a finding below is *carried forward* from it
> and re-verified, it says so. Where it is *corrected*, it says what the old claim was.
> The scope has also narrowed by Dave's ruling of 2026-08-13 (§0), so most of the old
> document's Section-2/Section-3/matrix material is now Phase 16.1's, retained here
> only as a cheap drift table (§6).

---

<user_constraints>
## User Constraints

### Locked decisions carried from `16-CONTEXT.md` (D-01..D-15) — STILL BINDING
Unchanged and not reopened by this research. `D-03` (KYC/UBO on FIBO is the use-case
spine), `D-04` (FIBO stores are an L1-read enterprise estate, never mirrored into L3),
`D-05` (temporal signal is an authored L1 observation stream), `D-07` (greenfield
examples), `D-11` (structural spine/deployment separation), `D-12` (G-01 fixed by
construction) all survive the narrowing and are the constraints this phase executes
under. `D-13` and `D-14` were **revoked** by `D-IMPL-96` (§5).

### Dave's narrowing rulings, 2026-08-13 — LOCKED
- **R-1 — Phase shape.** Phase 16 = the five shipped infrastructure plans
  (`16-01`, `16-03`, `16-04`, `16-06`, `16-21`) **plus one Hello CCF example**.
  Sections 2 and 3, the six-backend matrix, the terminal retirement of
  `examples/00`–`08`, and the full adoption-argument treatment **defer to Phase 16.1**
  with their criteria intact.
- **R-2 — Example content.** KYC/UBO resolution on the FIBO dataset, **one backend**.
  Salvages `16-05`'s two completed tasks. Drops the matrix and the DGX live legs.
- **R-3 — Docs ship with it.** The example ships with its Section-1 published pages,
  re-cut against the current surface, closing G-01 for the path a newcomer walks first.
- **R-4 — Residuals.** `DI-15.6-01(b)` is **discharged in this phase**.
  `DI-15.6-01(a)`, `DI-15.6-02`, advisory A5 and disposition 2 **defer to 16.1**.
</user_constraints>

---

## 0. THE ANSWER TO R-2's QUESTION — measured, not reasoned

**Which backend: `sqlite`. Can it run with no DGX credentials and no network: YES —
verified by execution at `6e95da0` on this machine, which holds neither
`NEO4J_PASSWORD` nor `PGPASSWORD`.**

```
PYTHONPATH=src:runtime .venv/bin/python examples/s1-01-hello-context-product/run.py
EXIT=0
```

Three declared questions, three served Context Products, content addresses computed
by running (not transcribed):

| Question | `content_hash(product)` (20-hex) | `debt.debt` | `debt.signal` | `obligation_in_force` |
|---|---|---|---|---|
| 1 | `19b230aca20349d21638` | 0.0348251467461090910588235294 | `ok` | `ccf.no-obligation-in-force` |
| 2 | `c9df093534f1ed5e85bd` | 0.0348251467461090910588235294 | `ok` | `ccf.no-obligation-in-force` |
| 3 | `d49f4b869aefd5a3b6b9` | 0.2213415448674956763647368421 | `forced_llm` | `kyc/re-pull-registry-then-restate-with-debt-disclosed` |

`debt_evidence` is `()` on all three (D-IMPL-119 limb 3(b), §1.4).
`source_refresh_recency` is a two-instant `SourceRefreshWindow`
(`2026-08-01T00:00Z` … `2026-08-10T23:45Z`) with no source identity and no count
(D-IMPL-124 Shape B, §1.5).

### (a) The FIBO data that exists **inside** this repo

`examples/s1-01-hello-context-product/artifacts/source-estate.yaml` — **576 lines**, a
`ccf.declared-artifact` envelope with `class_id: fibo-kyc.source-estate`
(`source-estate.yaml:45`). It declares the whole KYC/UBO vocabulary: **14 entities, 16
relationships, `ownershipPercent` on 9 edges, 4 corp→corp ownership edges**
(`16-02-SUMMARY.md`, table under *Task 1*). Every record measured off the DGX estate is
carried forward verbatim; the extension is purely additive.

`examples/s1-01-hello-context-product/source_estate.py` — **338 lines**, a deterministic,
vocabulary-free interpreter that materialises the estate as JSONL (what the DGX loaders
read) and SQLite (what L1 ingress reads). It reads only the artifact; no network, no
credential, no clock read.

**"Who ultimately owns Acme?" is answerable on this in-repo estate, with depth.**
Verified in `16-05-SUMMARY.md`: *"Jane Doe's real interest in the subject is 12.0% direct
plus 60.0% of a holder that itself holds 30.0% — 30.0% in total, stated in no record of
any source system."* The multi-hop property is pinned by
`tests/examples/test_s1_01_output.py::test_the_answer_is_a_sum_over_paths_not_a_single_hop`
against `artifacts/expected.yaml`'s `boundary_case_party` — a natural person at exactly
the 25.0% FinCEN threshold one hop down and 1.125% three hops down, so a regression to
single-hop lookup goes red.

### (b) What `16-02`'s two completed tasks produced, and whether it stands alone

Both are **committed and in-tree**: `c6e3ac0` (the declared estate + the reshaped
artifact-header gate) and `61581cc` (the generator + its ten assertions). Shipped
artifacts: `artifacts/source-estate.yaml`, `source_estate.py`,
`tests/examples/test_source_estate.py`, `docs/surface/examples/FIBO-EXTENSION.md`.

They stand alone. `run.py::materialise_estate` calls
`source_estate.generate(source_estate.load_declaration(), root)` into a caller-supplied
scratch root; nothing in that path reaches the DGX.

### (c) **Hello CCF does not need `16-02` Task 3.**

Task 3 loads the same additive extension into the four **live DGX stores** so that the
out-of-repo harness at `/home/parkave/fluree/examples/fibo/` agrees with the in-repo
declaration. Its only consumers are the deferred six-backend equality matrix (`16-07`,
criterion 4) and the deferred DGX opt-in job (`16-12`). With the matrix deferred by R-1,
**Task 3 is not a dependency of the Hello CCF example, of its tests, or of its published
pages.** It should travel to Phase 16.1 with the matrix, unexecuted.

One consequence to record rather than discover later: Fluree remains unloaded at 4 of 9
ownership pairs, and that is **not** a missing loader line — RDF has nowhere to hang a
qualifier on a triple, which is why the source modelled `ownershipPercent` on the Party
and every chain was one hop (`.planning/STATE.md`, *OPEN, 16-02*). CCF's own adapter
solves it with the interposed-edge layout (`src/ccf/graph/backends/fluree_write.py`,
15.3 §R5). Dave has not ruled write / leave / defer. That ruling belongs to 16.1, not
here.

### (d) Not applicable — an honest in-repo subset exists and is already shipped.

**Backend mechanics, so the planner does not re-derive them.** The manifest declares the
backend as a *kind* only: `manifest.yaml:55` is `backend: sqlite`, and `:54` is
`tenant_id: meridian-bank`. The connection value is caller-supplied at boot —
`deployment.py:115-116` name `CONNECTION_PATH_KEY = "database_path"` and
`DATABASE_FILENAME = "ubo.sqlite3"`, and `deployment.py::connection(*, root)` is the only
place a path exists. No DSN, no port, no credential is in the tree, and none needs to be.

---

## 1. Surface delta — what 15.5 + 15.6 moved

`git diff --stat 84f4501..HEAD -- src/ runtime/` (base = the 2026-08-09 commit the prior
research read): **39 files, 6898 insertions, 229 deletions.**

### 1.1 The content address — what actually moved, and where it is pinned

**Correcting the framing.** `STATE.md` and `docs/15.6-GATE-PACKAGE.md:49` record four
moves — `374f9f4d…` → `06e454f4…` → `36ebd759…` → `7d0a3d60…` → `75365e18…`. Measured:
those are **replay-record** addresses, and their **only in-tree pin is a single line**,
`examples/08-e2e-demo/artifacts/expected_output.txt:46`
(`docs/surface-changes/15.6-13-source-refresh-window.md:132` states this explicitly, and
a repo-wide grep for `75365e18` returns that file and nothing else under `examples/`).

Two consequences:

1. **The Hello CCF example pins no literal address.** `tests/examples/test_s1_01_output.py:495`
   asserts `address == content_hash(result.record)` — computed on both sides. Nothing in
   `s1-01` regenerates when the field set moves. The 2026-08-10 research's landmine —
   *"an example that encodes a stale content address regenerates the wrong artifact"* — is
   real in general and **does not bite this example.**
2. The one artifact that does carry a literal lives in `examples/08-e2e-demo`, retired at
   wave 11 by `16-18` (`tools/retirement_sweep.py:143`) — now deferred to 16.1. It stays
   as-is this phase.

**What determines the address:** `ccf.contracts.canonical.canonical_bytes` walks a model
field-by-field over `type(value).model_fields`, so **any** field added to
`ContextProductContract` moves it. That is why it moved four times in one phase.

### 1.2 `ContextProductContract` — the shape today (`src/ccf/products/contract.py:664-676`)

```
schema_name, schema_version, plan_id, tenant_id, temporal_boundary,
expires_at, ttl_anchor, lineage, payload,
debt: DebtAssessment | None = None,                              # 15.5-11, D-IMPL-100
debt_evidence: DebtEvidence = NO_DEBT_EVIDENCE,                  # 15.6-06, D-IMPL-118
source_refresh_recency: SourceRefreshRecency = NO_SOURCE_REFRESH_RECENCY,  # 15.6-07/13
obligation_in_force: ObligationInForce = NO_OBLIGATION_IN_FORCE,  # 15.6-08
```

**Four new top-level fields**, all `qa-toplevel` per `D-IMPL-118` — siblings of `debt`,
not members of `DebtAssessment`. The nested placement was measured cheaper and declined,
so each pays for its own identity: a matching member on replay dimension 5
(`ContentGenerationPath`, `src/ccf/replay/record.py:436ff`) plus a read-back in every
`rehydrate_product`. `src/ccf/replay/engine.py:161` is the Protocol method; the shipped
implementations outside tests are `examples/06-decision-replay/run.py:387` and
`examples/external/00-hello-context/run.py:207`.

`RegisteredProductClass` (`contract.py:556-575`) gained **eight** fields in 15.5:
`accepted_policy_binding_modes`, `accepted_lineage_modes`, `freshness_sla`, `discovery`,
`addressability`, `constituent_validity_floors`, `payload_schema_key`/`_version`,
`request_contract_key`/`_version` — all defaulted to named positive sentinels so pre-15.5
registrations assert exactly what they always asserted.

### 1.3 `Observation.subject` — new in 15.6 (`src/ccf/halflife/decay.py:188`)

`subject: str = NO_SUBJECT_IDENTITY` where the sentinel is `"ccf.no-subject-identity"`
(`decay.py:131`). Two values are refused and only two: a blank, and anything inside the
SDK's `ccf.` namespace other than the sentinel
(`decay.py:233::_the_subject_is_declared_and_stays_out_of_the_sdk_namespace`). Carried,
never consumed — no function in that module reads it. `observed_at` now **refuses a naive
instant at construction** (`decay.py:197`), which it documented and did not have before
15.6's single-agent review.

### 1.4 `DebtAssessment` evidence — the pointers are FORBIDDEN, not merely absent

`DebtEvidencePointer` ships (`src/ccf/halflife/assessment.py:469`) and `debt_evidence`
ships as a validated carrier. **`D-IMPL-119` limb 3(b) forbids populating it**: raw
interpretable pointers are refused until the assembly path becomes principal-scoped,
which no phase has done. The shipped assembler takes the omission path explicitly —
`examples/s1-01-hello-context-product/deployment.py:308-322` carries the reasoning.
Measured by execution above: `debt_evidence == ()` on all three products.

> **Constraint on this phase:** documentation must not describe a surface in which debt
> points at named observations today. The carrier exists; the pointers do not, by ruling.
> `15.6-GATE-PACKAGE.md` §6.5 calls this *"a paid-for carrier holding a sentinel and no
> pointers … `D-IMPL-118` and `D-IMPL-119` limb 3(b) working as intended together."*

### 1.5 Source-refresh recency — Shape B (`D-IMPL-124`)

`SourceRefreshWindow` (`assessment.py:616`) carries the oldest and newest of the
deployment's declared refresh instants. **No source identity, no count.** The per-source
map that 15.6-07 shipped was deleted in 15.6-13 because a reader entitled to the product
could otherwise learn that a given upstream system exists and when it last published,
with no check that they were entitled to its contents.

**Recorded consequence Phase 16 must not contradict** (`15.6-GATE-PACKAGE.md` §6.3):
deleting the map removed the SDK's duplicate-reference refusal, because the SDK can no
longer see the set. The refusal now lives in the **adopter's parse step** — the last party
able to notice, since `min`/`max` would absorb a duplicate silently. Reducing per-source
instants to a window is deployment work; `deployment.py::_declared_refresh_window` is
where s1-01 does it.

### 1.6 The request surface, entitlement, and the resolver seam

- **`ccf.products.request`** (595 lines, new): `ProductRequest`, `ProductRequestContract`,
  `refuse_request`, `request_seeds`, `refuse_request_contract_pin`,
  `NO_REQUEST_CONTRACT`. A product class is now **callable** — subject and instant are
  caller-supplied arguments, not artifact literals (`D-IMPL-98`).
- **`ccf.products.payload`** (364 lines, new) + **`ccf.products.bind`** (223 lines, new):
  a class pins its payload schema by `(key, version)`, resolved at registration;
  conformity is checked at bind. **No fourth gate** — `run_gates` is untouched and the
  three validation gates stay three (`D-IMPL-102` limb 3).
- **`ccf.products.entitlement`** (226 lines, new): the Control Plane artifact stating
  which classes a principal may be served and which roles it may assert.
- **`ccf.products.composition`** (399 lines, new): N-way lineage union, TTL floor,
  `D-IMPL-31`'s mixing refusal. No `compose_debt` — `D-IMPL-104` ruled its meaning and
  deferred the combinator.
- **`ccf.agents.__all__` gained 7 names** (`src/ccf/agents/__init__.py:57-87`):
  `DETERMINISTIC_ASSEMBLER_ID`, `DETERMINISTIC_ASSEMBLER_VERSION`, `NO_CONSULTATIONS`,
  `AssemblyOutcome`, `ConsultationRecord`, `ContextAssemblerProtocol`,
  `DeterministicAssembler`.

### 1.7 The four delivery doors — every one is now governed

| Door | Signature today | Was |
|---|---|---|
| `runtime/ccf_runtime/mcp/egress.py::build_egress_server` (`:254-262`) | **six required kwargs**: `server_name, resolver, token_verifier, auth_settings, entitlement_source, perspective_resolver` | `(server_name, resolver)` — **no auth at all** |
| `runtime/ccf_runtime/mcp/experience.py::build_experience_server` (`:502-522`) | adds required `token_verifier, auth_settings, entitlement_source, perspective_resolver`, plus `tool_allowlist` | auth only |
| `runtime/ccf_runtime/http_api/routes/product.py::build_router` (`:88-108`) | optional-but-**paired** `entitlement_source` / `perspective_resolver`; supplying exactly one raises | neither |
| CLI `--local` (`runtime/ccf_runtime/cli/local.py:82`) | `_no_products_resolver` widened to 5 args and refuses honestly | 3 args |

**`ProductResolverProtocol` and `ExperienceProductResolverProtocol` went from three
arguments to five** (`egress.py:138-183`, `D-IMPL-108`). The docstring at `egress.py:156`
states a boundary the docs must reproduce: **two refusals this door does not call and your
resolver must** — `refuse_request` and `refuse_bound_payload` (`D-IMPL-113`, extended by
`D-IMPL-121`). A resolver that omits them serves against an unchecked request and an
unvalidated payload.

> **Do not cite the surface manifest as stability evidence for these.** `D-IMPL-122`
> narrowed `DI-15.5-06` and did not close it: 39 multi-method Protocols remain
> information-free, **including all seven `D-IMPL-110` names**. The resolver break above is
> exactly the change `docs/surface/v0.2-surface.json` was byte-identical across.

---

## 2. The Hello CCF example as it stands today

`examples/s1-01-hello-context-product/` — 3 code modules, 19 artifacts, 1 README.
`make example-s1-01` exists (`Makefile:88-89`) and **leads** the eleven-member
`examples:` aggregate (`Makefile:126`). It runs in the always-on CI `examples` job.

**Test coverage that already exists and is green** (`69 passed`, run at `6e95da0`):
`tests/examples/test_s1_01_output.py`, `test_spine_separation.py`,
`test_section_one_is_agent_free.py`, `test_source_estate.py`,
`test_s2_client_transport_spike.py`.

### 2.1 What `16-05` shipped, and the one thing in its SUMMARY that is now false

Tasks 1–2 are committed (`1a96b3f`, `e44dc66`, `c6aa4ba`). **Task 3 is a blocking
human-verify checkpoint on the spine/deployment split — never executed.**

`16-05-SUMMARY.md` says the two modules are *"held together by two Protocols (`Scenario`,
`DeploymentBinding`)"*. **`DeploymentBinding` was deleted at `6b87a8f` (15.5-04)** with the
commit message *"CCF does not ship a `DeploymentBinding`; the example invented it and
called it 'the adoption checklist', so a reader learning CCF from this example learned a
surface that does not exist."* `spine.py` today declares exactly one Protocol,
`Scenario` (`spine.py:123`); `assemble_and_serve` takes `manifest`, `connection`, `read`,
`plan_class`, `request`, `root` as ordinary keyword arguments.

This is a **finding in Hello CCF's favour** and it must reach the published pages: the
`.planning/STATE.md` measurement that *"55 of those 74 [wiring lines] exist only to satisfy
`DeploymentBinding` — a Protocol the example invented"* has been paid off in the tree.
Any re-run of that measurement for the docs must be re-measured, not quoted.

**Task 3's checkpoint is still open and still worth running** — the human read of spine vs
deployment side by side is the acceptance test for `D-11`, and the modules have changed
substantially since the checkpoint was written (15.5-04, 15.5-13, 15.6-05/06/07/08/13 all
edited them). It should be re-scoped to the current modules rather than replayed.

### 2.2 The spine's seven marker regions — intact, and the artifact of `D-11`

`spine.py` carries the seven Phase-14 `D-07` regions in order:
`boot` (`:295`), `ingest` (`:331`), `operators` (`:340`), `project` (`:361`),
`gate` (`:397`), `record` (`:549`), `serve` (`:577`). `test_spine_separation.py` asserts
both the ordering **and** the closure — seven names and no eighth. This is the snippet
vocabulary the published pages include from; it is `pymdownx.snippets` `--8<-- [start:x]`
form, and `mkdocs.yml:95` sets `check_paths: true` so a mis-typed target fails the strict
build rather than rendering an empty block.

### 2.3 The minimum artifact set the No-Hardcoding Rule forces an adopter to author

Nineteen documents under `artifacts/`. This is the honest answer to *"what do I have to
write?"* and belongs on the published page verbatim:

`manifest.yaml` · `product-class.yaml` · `product-governance.yaml` ·
`request-contract.yaml` · `questions.yaml` · `projection-requirements.yaml` ·
`perspective.yaml` · `policy-bundle.yaml` · `resolution-spec.yaml` ·
`half-life-table.yaml` · `debt-profile.yaml` · `events.yaml` · `source-estate.yaml` ·
`ubo-question.yaml` · `expected.yaml` · and four `operator-parameters-{traversal,
temporal,policy,similarity}.yaml`.

Every one carries a `$schema` header (gated by
`tests/examples/test_artifact_schema_headers.py`, reshaped by `16-02` into a two-sided
bijection so a new example arms it by existing) and `[ADAPT]` / `[MECHANISM]` markers.

**`DebtProfile` is agent-free** — `16-08`'s open worry (*"if the shipped API cannot express
a profile without an agent, stop and record it as a finding"*) is resolved by the tree:
`src/ccf/controlplane/artifacts.py:244` binds nothing to an agent, and
`artifacts/debt-profile.yaml` is a Section-1 artifact under the agent-free AST gate.

### 2.4 The day-1 import path (advisory A-1, already gated)

`from ccf.deployment import …` is the single preferred spelling; submodule FQNs are
implementation detail. `src/ccf/deployment/__init__.py:127-144` exports 16 names
including `load_and_boot`, `BootedFabric`, `DeploymentManifest`, `ResolvedPins`,
`build_operator_registry`, `refuse_operator_set_divergence`.
`tools/docs_tests/test_advisory_discharge.py:296` gates it: a published page must write
the preferred form, and no site may import through `from ccf.deployment.<sub> import`.

---

## 3. Section 1's published pages — R-3

### 3.1 Publication mechanics

`mkdocs.yml:17` — `docs_dir: public`. **Default-deny by existence**: only what is in
`public/` publishes. `:22` — `strict: true`, so any warning is fatal.
`make docs-strict` (`Makefile:270-274`) is four steps: `publish_scan.py --pre-build`,
`publish_scan.py docs/schemas`, `mkdocs build --strict`, `publish_scan.py site`. It is in
`make ci` (`Makefile:81`) per `D-IMPL-72`.
Snippet includes are allowlisted to `examples/`, `public/`, `perf/baselines/`
(`tools/publish_scan.py:104-107`) — a positive allowlist, not a denylist.

`public/` holds **43 pages** today. `docs/SURFACE-CHANGES.md` is *not* published (it is
under `docs/`, not `public/`), which settles `SURFACE-AUDIT` §5.4 for this phase's
purposes.

### 3.2 Which pages are Section 1, which exist, which are wrong

| Page | Exists | State against the current surface |
|---|---|---|
| `public/tutorial/hello-ccf.md` | **NO** | must be created — the Section-1 narrative |
| `public/how-to/assemble-a-context-product.md` | **NO** | must be created — G-01's named gap: *no how-to for deterministic assembly exists* |
| `public/concepts/context-graph-axes.md` | **NO** | must be created — the six axes of `G(E,R,T,P,Π,L)` |
| `public/concepts/pillars/data-context.md` | yes | **WRONG BY CONSTRUCTION** — G-01's primary evidence: opens on *"how does an agent get at first-party records"*, the page is 105 lines and the SDK-ships-no-agents line is not on it; that sentence is at `public/tutorial/adopters-guide.md:161` (corrected 2026-08-13 — the earlier "line 133" citation named a line that does not exist) |
| `public/reference/protocols/context-products.md` | yes | **STALE PROSE.** 30 lines. Its prose still frames the surface as *"the three validation gates"* only, and names no request contract, no payload schema, no entitlement, no debt. The `:::` mkdocstrings directives auto-track the code; the prose does not. |
| `public/reference/artifacts/product-registration.md` | yes | **STALE** — `RegisteredProductClass` gained eight fields (§1.2) |
| `public/reference/protocols/halflife-and-debt.md` | yes | **STALE** — renders four `ccf.halflife.debt` symbols and has no worked example to point at |
| `public/reference/artifacts/control-plane-artifacts.md` | yes | needs the debt-profile `signal_obligations` block (15.6-08) |
| `public/reference/artifacts/deployment-manifest.md` | yes | **CURRENT** — created by `16-06`, discharges A-1 and A-8 |
| `public/reference/surface-toolchain.md` | yes | **CURRENT** — created by `16-06`, discharges A-2 |

### 3.3 The vocabulary gap, measured

Occurrences across all 43 pages of `public/`:

| Term | Files |
|---|---|
| `ProductRequest` | **0** |
| `refuse_request` | **0** |
| `payload schema` | **0** |
| `SourceRefreshWindow` | **0** |
| `ContextAssembler` | **0** |
| `entitlement` | 1 |
| `DebtAssessment` | 1 |
| `assembler` | 1 |
| `obligation` | 3 |

**The published tree describes a Context Product surface that predates 15.5 entirely.**

### 3.4 A-3's discharge gate is now under-scoped — a finding, not a defect of `16-06`

`tools/docs_tests/test_advisory_discharge.py:99-105` sets A-3's floor as
`("load_and_boot", "backend", "ccf backends", "GraphQuery", "registry")` — **Phase
15.2–15.4 vocabulary only**. It passes today over a tree that says nothing about 15.5 or
15.6. `16-06` discharged A-3 correctly against the surface at its HEAD (`5bf819b`,
2026-08-10); the surface then moved. The gate needs its floor widened in this phase, or
criterion 9 is measured against a stale ruler. **This is cheap** — it is a tuple of
strings — and it is the kind of thing that rots silently, which is A-3's own defect class.

---

## 4. `DI-15.6-01(b)` — the scanner coverage hole (DISCHARGED THIS PHASE, R-4)

Dave, 2026-08-13: *"Treat the disagreement as a real coverage hole, not a false positive
on either side."*

### 4.1 Both halves reproduce at `6e95da0`

```
PYTHONPATH=. .venv/bin/python tools/publish_scan.py docs/schemas   → EXIT 0   (26 files, 0 findings)
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/ -q      → 4 failed, 540 passed
```

The five `src/` files reproducing whitepaper body text, with shingle counts —
**unchanged from `9905e8f`**, which is Dave's positive result:

| File | Node | Shingle hits |
|---|---|---|
| `src/ccf/deployment/binder.py` | `<module>` | 7 |
| `src/ccf/halflife/assessment.py` | `<module>` | 15 |
| `src/ccf/halflife/debt.py` | `<module>` | 14 |
| `src/ccf/products/composition.py` | `<module>` | 3 |
| `src/ccf/products/request.py` | `<module>` | 1 |

`assessment.py` and `debt.py` are the two modules Track B rewrote most heavily across four
waves and their counts did not move at all. Keep that on the record.

### 4.2 The two scanners' **actual** coverage — measured, and it is not what the ruling assumed

| Scanner | Reads | In a blocking gate? |
|---|---|---|
| `tools/publish_scan.py --pre-build` | the `public/` tree, structurally | yes — `docs-strict` |
| `tools/publish_scan.py docs/schemas` | 26 committed JSON schemas, incl. every `description` field | yes — `docs-strict` |
| `tools/publish_scan.py site` | the **built** site | yes — `docs-strict` |
| `tools/publish_scan_tests/test_docstring_leaks.py` | **every** docstring under `src/` + `runtime/` — module, class/function, PEP-258 attribute, and `#:` runs (`:33`, `:102-110`) | **NO** |

**The mechanism, named as Dave required:** `testpaths = ["tests"]` at
`pyproject.toml:142`. A bare `pytest` never reaches `tools/`. `make ci` is
`ci-core examples docs-strict` (`Makefile:70,81`) and reaches none of the three
gate-checker suites. CI reaches two of them, as separate steps —
`.github/workflows/ci.yml:35` (`pytest tools/lints/tests -q`) and `:314`
(`pytest tools/publish_scan_tests tools/docs_tests -q`). So `make ci` green has never
meant CI green, and a red package crossed at least one phase boundary while every plan in
that phase reported a green gate.

**And a correction the ruling's own framing invites.** Dave's option (a) was *"extend the
D-20 / docs-strict surface to cover the schema-description channel."* Measured: **that
channel is already covered** — `publish_scan.py docs/schemas` is step 2 of `docs-strict`
(`Makefile:272`) and it is clean. The five leaks are **module** docstrings, and
`tools/dump_schemas.py::emit` copies *class* docstrings into `description` fields, so the
five never reach `docs/schemas` at all. Nor do they reach the built site: no page carries
a module-level `::: ccf.halflife.debt` — `public/reference/protocols/halflife-and-debt.md`
renders four *symbols* (`:12,14,16,18`), and mkdocstrings emits only those symbols'
docstrings. **The two scanners do not disagree about a shared surface; they cover
different surfaces, and the wider one does not block.** Option (a) is therefore already
satisfied and closes nothing. Option (b) is the live remedy.

### 4.3 What a real fix looks like

1. **Make the wider scanner blocking.** Add `pytest tools/lints/tests
   tools/publish_scan_tests tools/docs_tests -q` to `make ci` so the Makefile's stated
   *"full local reproduction of the always-on pipeline"* (`Makefile:81`, `D-10`) becomes
   true. This is `DOCS-08`'s existing text, verbatim, and it is the option (b) remedy.
2. **Close the five leaks**, which is now permitted: `D-IMPL-96` revoked the
   no-fabric-change constraint, so a docstring rewrite in `src/` needs no carve-out.
   CLAUDE.md §11 requires the whitepaper *citation* stays — trading a leak for a fidelity
   defect is not a fix, and `test_docstring_leaks.py`'s own module docstring says so.
3. **Record the coverage asymmetry** rather than leaving it implicit: the blocking gate
   reads what publishes, the non-blocking one reads what *could* publish. If step 1 lands,
   they are both blocking and the asymmetry is a stated design choice, not a hole.

**Ordering caution.** Step 1 turns the *other three* `tools/` failures red inside
`make ci`. Those are `DI-15.6-01(a)`, deferred to 16.1 by R-4. Either step 1 lands after
(a) closes — which is 16.1 — or this phase closes (a)'s three as a precondition of its own
discharge. **This is the sharpest sequencing question in the phase and it needs a
planner-level decision** (§7, Q-1).

---

## 5. Constraints the replan must not violate

**CI-enforced, all four green today** (`python -m tools.lints --all` exit 0 at `6e95da0`):
zero harness imports in `src/`; no LLM client in an `__ccf_mode__ = "algorithmic"` module;
no prompt/agent/task/threshold literal outside an artifact (No-Hardcoding, CLAUDE.md §6.4);
no substrate name outside the backend registry. Single-writer holds: `spine.py:332-337`
notes `booted.handle.worker` is the only write handle to L3 in the process.

**ROADMAP criterion 8 (URGENT, unchanged):** Gate 2 / `INV-CH7-47` is documented as
**assembly-path integrity** and **nowhere** as a comparison of two independently authored
sets. `spine.py:441-448` already states it correctly in the tree — *"the engine is a
faithful TRANSCRIBER of the plan rather than an independent witness of it … Gate 2
therefore does not catch a producer misdeclaring. Authorable drift fails upstream instead,
at the binder call in step 5."* Carry that wording to the page.
`tools/docs_tests/test_gate_two_wording.py` (shipped by `16-04`) is the standing gate.
The `SURFACE-AUDIT` §5.3 **A-4** caveat travels attached to any
`required_operator_keys` vs `operators_invoked` assertion and is never promoted into an
independence claim.

**ROADMAP criterion 10 — READ THE CURRENT TEXT, NOT THE PLANS.** `D-IMPL-96`
(`docs/DECISIONS.md:332`, Dave, 2026-08-10) **revoked** the *"no fabric changed"* wording,
and with it `D-13`'s docstring carve-out, `D-14`'s two-limb bound, and `16-19`'s
`gate_16.py` allowlist. Dave: *"the fabric MUST change to do this the right way… I don't
want to use the 'not fabric change' [wording] because it has been used out of context."*
The criterion now reads *"Nothing leaks into the core"* + the four CI lints, *"while
changes to the fabric itself are permitted and expected where this phase finds a defect."*
Plans `16-12` (`:398`), `16-18` (`:426,598`) and `16-19` (`:18,35,323,327`) all still
assert `git diff --stat -- src/ runtime/` is empty or names one file. **Every one of those
assertions is void.** `16-19` is deferred by R-1; if this narrowed phase writes any close
gate, it must be written against the current criterion text.

**CLAUDE.md §3.1** — the cross-AI panel (`/gsd-review --phase 16 --all`) is mandatory and
unsubstitutable at close, against **shipped code**, to a distinct `16-CLOSE-REVIEWS.md`;
the single-agent review is additive; every finding is verified against the tree before
being recorded or acted on, and rejections are recorded as rejections. This project has
produced fabricated findings in **three** separate reviews.

---

## 6. Compact drift table — for whoever plans Phase 16.1

All 14 untouched plans defer. This is the cheap inventory of what is now false in each, so
16.1's planner starts from a corrected base rather than re-deriving it. Verify before
acting; these are drift flags, not a plan.

| Plan | Drift |
|---|---|
| `16-02` T3 | **Not a Hello CCF dependency** (§0c). Travels with the matrix. Fluree's 4-of-9 gap is a design question, unruled. |
| `16-05` T3 | Checkpoint still open; re-scope to the current modules. `DeploymentBinding` is gone (`6b87a8f`) — the SUMMARY's Protocol claim is false. |
| `16-07` | **Most affected.** Its `<interfaces>` lists 9 `ContextProductContract` fields; there are 13. Its byte-identity claim now depends on `debt` (a 28-digit `Decimal` computed off `execution.view`) being substrate-stable — **unverified across backends**, and it must be measured, not asserted. |
| `16-08` | `<interfaces>` predates `Observation.subject`, `DebtProfile.signal_obligations`, `SourceRefreshWindow`, and the four vessel members. Its open worry about an agent-free debt profile is **resolved** (§2.3). Must teach `debt_evidence` as a ruled empty carrier, not a feature. |
| `16-09` | Says `build_egress_server(...)` has *"NO auth parameters"* — **false**, it has four (§1.7). |
| `16-10` | `<interfaces>` predates the 5-arg resolver seams and the two refusals a resolver must call. |
| `16-11` | `ccf.agents.__all__` list is 7 names short (§1.6). |
| `16-12` | Says `make examples` is *"ten targets"*; it is **eleven** (`Makefile:126`). Criterion-10 assertion void. |
| `16-13` | Six-axes mapping still accurate; Section-1 page set is the R-3 set. |
| `16-14` | Its evidence table got **stronger**, not weaker — dim-5 now carries debt, evidence, recency, obligation and the request. The `passage_anchor` caveat stands: the contract ships, Pattern 5 was never built, and the page must not claim CCF extracts passage anchors today. |
| `16-15`/`16-16`/`16-17` | Publication + retirement; unaffected by the *surface* drift, blocked on the deferred examples. |
| `16-18`/`16-19` | Criterion-10 assertions void (§5). `16-19`'s `gate_16.py` allowlist is revoked machinery. |
| `16-20` | Unaffected. |

**Residuals deferring to 16.1** (`15.6-.../deferred-items.md`): `DI-15.6-01(a)` — four red
`tools/` gates, reproduced at `6e95da0` (§4.1); `DI-15.6-02` — the citation ratchet's two
floors sit outside `COUNT_COUPLING_TREES = ("tests/products",)`
(`tools/retirement_sweep.py:792`), closable by one data line plus a report regeneration;
advisory **A5** — docstring cross-reference drift in `src/ccf/graph/backends/fluree.py`,
cleanup-grade; **disposition 2** — `docs/DEBT_COMPLETENESS_RULING_EVIDENCE.md` shows as
unclassified in the census sweep and **must not be regenerated**, *the classification is
the defect, not the document*. Plus Phase 16's own two entries
(`16-.../deferred-items.md`): the retired-ERGO-03 docstring cross-references (owners
`16-15`/`16-18`) and the stale paths in `docs/SURFACE-CHANGES.md` (owners `16-20`/`16-21`).

**One measured correction to a carried figure.** `deferred-items.md` records the retirement
report as stale at *"181 rows across 52 files"*. Measured at `6e95da0`:
`python tools/retirement_sweep.py` → **174 rows across 52 files, 91 outside the three
swept trees, 2768 files scanned**; the committed report says 163 across 47. The `181` does
not reproduce. Re-measure before acting; do not quote it.

---

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework | `pytest` (+`pytest-cov`; `pytest-benchmark` for `perf/` only) |
| Config | `pyproject.toml` `[tool.pytest.ini_options]`, **`testpaths = ["tests"]`** (`:142`), 8 markers |
| Quick run | `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/examples -q` |
| Full suite | `make ci` = `lint typecheck test examples docs-strict` (`Makefile:70,81`) |
| **Gate-checkers CI runs and `make ci` does not** | `pytest tools/lints/tests tools/publish_scan_tests tools/docs_tests -q` — **540 passed / 4 failed at `6e95da0`** *(corrects `16-VALIDATION.md`'s recorded 453/3)* |
| Baseline on `main` | 3086 passed / 81 skipped, `mypy --strict` clean, `tools.lints --all` exit 0, eleven examples green, `docs-strict` green |

### Requirements → verification (narrowed scope)

| Req | Behavior | Automated command | Exists? |
|---|---|---|---|
| DOCS-08 | `make ci` composes the gate-checker suites | `make ci` | ❌ — the composition edit |
| DOCS-09 | in-repo KYC/UBO estate with corp→corp edges | `pytest tests/examples/test_source_estate.py -q` | ✅ 10 tests |
| DOCS-11 | spine/deployment split, canonical ordered markers | `pytest tests/examples/test_spine_separation.py -q` | ✅ |
| DOCS-12 | Section 1 agent-free; published pages teach products/operators/six axes | `pytest tests/examples/test_section_one_is_agent_free.py -q`; `make docs-strict` | ✅ gate / ❌ pages |
| DOCS-16 | A-1/A-2/A-3/A-8 discharged | `pytest tools/docs_tests/test_advisory_discharge.py -q` | ✅ — **A-3 floor needs widening (§3.4)** |
| criterion 8 | Gate 2 documented as assembly-path integrity | `pytest tools/docs_tests/test_gate_two_wording.py -q` | ✅ |
| criterion 5 (partial) | no stale example paths in published prose | `pytest tools/docs_tests/test_no_stale_example_paths.py -q` | ✅ |
| `DI-15.6-01(b)` | the two scanners cannot silently diverge | `pytest tools/publish_scan_tests -q` **inside `make ci`** | ❌ |

### Sampling rate
- **Per task commit:** `pytest tests/examples -q` + `make lint` (< 120 s).
- **Per wave:** `make ci` **plus** `pytest tools/lints/tests tools/publish_scan_tests tools/docs_tests -q` — until step 1 of §4.3 lands, these are two commands.
- **Phase gate:** both green; then the §3.1 close sequence.

### Wave 0 gaps
- [ ] `public/tutorial/hello-ccf.md`, `public/how-to/assemble-a-context-product.md`, `public/concepts/context-graph-axes.md` — do not exist
- [ ] the A-3 vocabulary floor widened past 15.4 (`test_advisory_discharge.py:99-105`)
- [ ] `make ci` composition (DOCS-08) — gated on the §7 Q-1 decision

---

## 7. Open questions

**Q-1 — PLANNER-LEVEL, must be settled before the wave plan.** `DOCS-08`'s
`make ci` composition (the option-(b) remedy for `DI-15.6-01(b)`) turns
`DI-15.6-01(a)`'s three remaining `tools/docs_tests` failures red **inside `make ci`** —
and R-4 defers (a) to 16.1. Three shapes, all consistent with the rulings:
compose `make ci` and close (a)'s three as a precondition; or discharge (b) by closing
the five leaks and adding *only* `tools/publish_scan_tests` to `make ci`, leaving
`tools/docs_tests` for 16.1; or discharge (b) by closing the leaks and compose nothing.
The second is the narrowest reading of R-4 and the one I would plan against. Two of the
three (a) failures are `example-s1-01` *"runs in CI but no published page names it"* —
which **R-3's pages close as a side effect**, so the real residual may be one row (the
stale retirement report), not three. Worth measuring before choosing.

**Q-2 — DAVE.** Does the narrowed phase still mint a `D-GATE-16`, or does it close as a
partial gate with 16.1 inheriting the criteria? ROADMAP criteria 1, 3, 4, 5, 7 and 9 are
not satisfiable at this scope by construction. §3.1 requires a `D-GATE-<Phase>` entry
before the next phase begins, and there is no precedent in this project for a phase gated
against a subset of its own criteria. **Planning should not proceed past the wave layout
without this.**

**Q-3 — DAVE, low urgency.** `16-05` Task 3's human-verify checkpoint predates six plans'
worth of edits to the modules it reads. Re-run it against the current `spine.py` /
`deployment.py`, or accept `test_spine_separation.py` as having subsumed it? The
structural half is now gated; the *legibility* half — Dave's original *"I can't tell which
code is example code and which is required by the CCF"* — is not testable and was the
point of the checkpoint.

**Q-4 — planner discretion, flagged.** ROADMAP criterion 4 names the six-backend matrix.
R-2 drops it. The ROADMAP entry needs updating through `gsd-sdk query roadmap.*` (never a
direct edit) to reflect R-1/R-2 before planning, or the phase plans against text Dave has
superseded.

**Not a question — a warning.** `16-07`'s cross-substrate byte-identity claim now rests on
`debt` being substrate-stable. Nobody has measured it. When 16.1 revives the matrix, that
measurement is a task, not an assumption.

---

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|---|---|---|
| A1 | The three `s1-01` product addresses in §0 are stable across runs on this machine | §0 | low — the example forbids clock reads and derives every instant from a declared epoch; re-run to confirm on another machine |
| A2 | Fixing the five module-docstring leaks needs no signature or behavior change | §4.3 | low — they are `<module>` nodes; but re-check `binder.py`, whose 7 hits sit in a module that `docs/reference/artifacts/deployment-manifest.md` names |
| A3 | Two of `DI-15.6-01(a)`'s three residual failures close as a side effect of R-3's pages | §7 Q-1 | medium — measure before planning against it |

## Sources

**Executed against the tree at `6e95da0`:** `examples/s1-01-hello-context-product/run.py`
(EXIT 0); `content_hash` over the three served products; `pytest tools/ -q`;
`pytest tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current`;
`python tools/retirement_sweep.py`; `PYTHONPATH=. python tools/publish_scan.py docs/schemas`;
`pytest tests/examples/{test_s1_01_output,test_spine_separation,test_section_one_is_agent_free,test_s2_client_transport_spike}.py -q` (69 passed);
`git diff --stat 84f4501..HEAD -- src/ runtime/`; `git show 6b87a8f`.

**Read:** `src/ccf/products/{contract,request,payload,bind,entitlement,composition}.py`;
`src/ccf/halflife/{assessment,decay}.py`; `src/ccf/replay/record.py`;
`src/ccf/agents/__init__.py`; `src/ccf/deployment/__init__.py`;
`runtime/ccf_runtime/mcp/{egress,experience}.py`;
`runtime/ccf_runtime/http_api/routes/product.py`; `runtime/ccf_runtime/cli/local.py`;
`examples/s1-01-hello-context-product/{spine,deployment,run}.py` and its 19 artifacts;
`tools/publish_scan.py`; `tools/publish_scan_tests/test_docstring_leaks.py`;
`tools/docs_tests/test_advisory_discharge.py`; `tools/retirement_sweep.py`;
`Makefile`; `mkdocs.yml`; `pyproject.toml`; `.github/workflows/{ci,live-legs}.yml`.

**Project canon:** `CLAUDE.md` (rev 4) §1, §3.1, §6.4, §7.3, §9, §10, §11, §15;
`16-CONTEXT.md` D-01..D-15; `.planning/ROADMAP.md` Phase 16 (`:1155-1291`);
`.planning/STATE.md` frontmatter; `.planning/REQUIREMENTS.md` DOCS-07..18 (`:32-43`,
`:216-227`); `docs/DECISIONS.md` D-IMPL-96/98/100/102/104/106/108/110/113/117/118/119/
120/121/122/123/124, D-GATE-15.5, D-GATE-15.6; `docs/15.6-GATE-PACKAGE.md`;
`docs/SURFACE-AUDIT.md` §5.3 (A-1..A-8); `docs/surface-changes/15.5-*.md`,
`15.6-*.md`; `.planning/phases/15.6-*/deferred-items.md`;
`.planning/phases/15.5-*/deferred-items.md`; `16-{PATTERNS,VALIDATION}.md`;
`16-{01,02,03,04,05,06,21}-SUMMARY.md`; the 14 unexecuted `16-*-PLAN.md`.

**Metadata.** Standard stack: unchanged, no new package. **Package Legitimacy Audit:
N/A — this phase installs no external package.** Confidence: surface delta HIGH (read the
code, ran it); the backend/credentials answer HIGH (executed); `DI-15.6-01(b)` HIGH (both
scanners run, coverage traced); the drift table MEDIUM (grep-and-read, flagged as
verify-before-acting). Valid until the next `src/` or `runtime/` change to
`ccf.products`, `ccf.halflife` or the four doors.
