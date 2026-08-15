# Phase 17: Client Access — `ccf.client` and the Transport-Agnostic First Example — Research

**Researched:** 2026-08-15
**Branch:** `phase-17` @ `543eda0`
**Domain:** measurement of the existing tree against an already-ruled design
**Confidence:** HIGH for everything below — every claim carries a file path and a line
number read in this session, or a command run in this session with its output quoted.

> **This document designs nothing.** `D-01`..`D-27` in `17-CONTEXT.md` are ruled. What
> follows is what the tree actually contains, so the planner sequences against reality.
> Where a measurement bears on an open sequencing question, the constraint is stated and
> the choice is left to planning.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

Every `D-01`..`D-27` in
`.planning/phases/17-client-access-ccf-client-and-the-transport-agnostic-first-ex/17-CONTEXT.md`
is ruled and is not re-opened here. The ones this research directly measures against:

- **D-02** — the producer side is completely invisible to the client; no client imports
  anything from the producer side of an example.
- **D-03** — exactly four exported names: `ProductClient`, `Result` (carrying `Refusal`),
  `TransportError`, `BindingError`.
- **D-05/D-06** — `binding=` kwarg, else `CCF_BINDING`, else `BindingError`. Scheme
  registry is a plain dict inside `ccf.client`. No bindings file, no discovery chain.
- **D-07/D-08/D-09** — refusal is a value; post-assembly fields on a refused result
  **raise**; a refused `Result` carries `refused`, `refusal.reason`, `refusal.key`, the
  refused request identity (product id, parameters, temporal boundary), and any
  pre-assembly lineage. The assembly boundary is the rule.
- **D-11/D-12/D-13** — `TransportAdapter.ask(WireRequest) -> WireOutcome`; `Result` is
  constructed in exactly one place; the in-process adapter round-trips the same codec.
- **D-14** — home is `src/ccf/client/`; the in-process adapter imports **only core
  boot/deployment machinery**; existing harness-import and `@algorithmic` lints apply
  unchanged.
- **D-15** — one adapter conformance suite, parameterized over adapters.
- **D-16** — lazy boot behind the adapter; **no client call may trigger producer
  *provisioning* semantics**.
- **D-17/D-18/D-19** — `consume.py` + opaque `deployment/` + README; `deployment/` uses
  single-file `ccf_config.yaml`; make target runs the documented command verbatim; purity
  gate (AST: `ccf.client` + stdlib only) and budget gate (≤ 80 lines).
- **D-20..D-23** — codec property tests, binding-resolution tests, **sabotage
  discipline**, two-thresholds-two-addresses re-asserted through the client seam.
- **D-26** — `tests/examples/test_spine_separation.py` must be re-scoped or retired.
- **D-27** — condemned trees removed or quarantined with every gate, make target, CI job
  and published snippet handled in the same change; **no partial state**.

### Claude's Discretion

Plan/wave decomposition; module layout inside `src/ccf/client/`; concrete
`WireRequest`/`WireOutcome` field names and types (subject to the §12.4 freeze
constraint); the form of demo data inside `deployment/` (subject to D-16); delete vs
quarantine for the condemned trees, and in which plan; requirement-ID prefix.

### Deferred Ideas (OUT OF SCOPE)

Bindings file / per-product env vars; HTTP and A2A adapters; client-side caching and TTL
auto-refresh; retry/backoff; auth/credential machinery; contract-level
principal/entitlement at the client seam (`D-IMPL-129` neighborhood); streaming /
pagination; **producer-side construction examples** (a later body of work, different
audience). Neighboring-but-not-gating: `D-IMPL-129`, `16-26` (`D-IMPL-133`).
</user_constraints>

---

## 1. Verified baseline

**Command run in this session, on `phase-17` @ `543eda0`, working tree clean:**

```
make ci-core            # = lint + typecheck + test
```

**Result:**

```
3305 passed, 118 skipped, 105 warnings in 361.10s (0:06:01)
EXIT=0
```

The claimed baseline of **3305 passed / 118 skipped / 0 failed** is **confirmed exactly**.
`make lint` (`tools.lints --all`) and `make typecheck` (`mypy --strict` over
`[tool.mypy] files = ["src","runtime"]`, `pyproject.toml:159`) both passed as part of that
sweep. `docker info` succeeded, so the Postgres-marked legs ran against testcontainers
rather than skipping; `CCF_TEST_POSTGRES_DSN` was unset.

### The baseline `make ci-core` does not cover, and it is already red

`[tool.pytest.ini_options] testpaths = ["tests"]` (`pyproject.toml:142`). The `tools/`
suites are **not** collected by `make test`, `make ci-core`, or `make ci` — but
`.github/workflows/ci.yml` runs them in two other jobs: `pytest tools/lints/tests -q`
(line 35, lint job) and `pytest tools/publish_scan_tests tools/docs_tests -q` (line 314,
docs job). `make docs-strict` (`Makefile:292-296`) is four `publish_scan`/`mkdocs` steps
and reaches none of them.

**Command run in this session:**

```
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest \
  tools/docs_tests tools/publish_scan_tests tools/lints/tests -q
```

**Result: `3 failed, 541 passed in 26.58s`**

| Failing test | What it says |
|---|---|
| `tools/docs_tests/test_retirement_sweep.py::test_the_committed_report_is_current` | `docs/surface/examples/RETIREMENT-COUPLINGS.md is stale`. Committed report says **163 rows / 47 files**; a live sweep finds **248 rows / 68 files**. |
| `tools/docs_tests/test_retirement_sweep.py::test_no_gitignored_path_reaches_the_report` | The sweep reads gitignored `.superpowers/sdd/**` files, so its inventory is not reproducible. |
| `tools/publish_scan_tests/test_docstring_leaks.py::test_no_docstring_reproduces_whitepaper_body_text` | 5 modules quote the whitepaper in docstrings: `deployment/binder.py` (7 shingles), `halflife/assessment.py` (15), `halflife/debt.py` (14), `products/composition.py` (3), `products/request.py` (1). |

This matches the process finding already on record in `.planning/ROADMAP.md:1219`
(*"`make ci` does not reach `tools/` though CI does — three suites there fail
pre-existing"*). It is stated here as a **measured, current** fact because two of the
three failures are the retirement-sweep machinery **D-27 depends on**.

**Planner consequence:** `make ci-core` green is not the whole gate. Any plan that touches
`examples/` must also run `pytest tools/docs_tests tools/publish_scan_tests -q` and
re-run `python tools/retirement_sweep.py --report`, or the phase closes green locally and
red in Actions.

---

## 2. M1 — the wire shape, side by side

### 2.1 The three doors, measured

| | MCP egress resource | MCP egress tool | MCP experience | HTTP product route |
|---|---|---|---|---|
| File | `runtime/ccf_runtime/mcp/egress.py:414` | `egress.py:472` | `runtime/ccf_runtime/mcp/experience.py:857` | `runtime/ccf_runtime/http_api/routes/product.py:122` |
| Emission expression | `canonical_bytes(servable.product).decode("utf-8")` (`:465`) | identical (`:597`) | identical (`:894`) | `canonical_response(servable.product)` (`:154`) |
| Body bytes | `canonical_bytes(ContextProductContract)` | same | same | same (`routes/__init__.py:172`) |
| Content address on the wire | **no channel** | **no channel** | **no channel** | **yes** — `X-CCF-Content-Address: sha256(body)` (`routes/__init__.py:47`, `:176`) |
| `replay_ref` | **never emitted** | never | never | never |
| Request identity echoed | no | no | no | no |
| Refusal body for a *fabric* refusal | none — exception | none | none | none |
| Refusal body for a *governance* refusal | protocol-native exception | same | same | `HTTPException(detail={"error_code","message"})` |

**The served half is already identical across all four surfaces.** Every one serializes
`servable.product` through `ccf.contracts.canonical.canonical_bytes` and nothing else.
`ServableProduct.product` is a `ContextProductContract`
(`src/ccf/products/gates.py:420-423`).

### 2.2 The vessel — what a served product actually contains

`src/ccf/products/contract.py:686-698`, in canonical-serialization order:

```
schema_name, schema_version, plan_id, tenant_id, temporal_boundary,
expires_at, ttl_anchor,
lineage{operators_invoked, policy_bundle_versions, graph_snapshot_at},
payload,
debt (DebtAssessment | None),
debt_evidence, source_refresh_recency, obligation_in_force
```

`content_hash(obj) = sha256(canonical_bytes(obj))` (`src/ccf/contracts/canonical.py:229`).

### 2.3 Divergences, named

**DIV-1 — the content address travels on HTTP and on no MCP door.** `canonical_response`
(`routes/__init__.py:111-177`) computes the digest from the *same single*
`canonical_bytes` call that produced the body, and publishes it under
`X-CCF-Content-Address`. The MCP doors publish nothing. This is **documented as
deliberate and transport-derived**, not as a defect
(`routes/__init__.py:159-163`: *"The MCP doors are deliberately untouched. They have no
header channel, and their bodies **are** the product — so carrying the address inside the
body would change the body and therefore change the address it claims."*).

*Consequence for `WireOutcome`:* the address cannot be carried *inside* the serialized
vessel without changing the vessel's own address. Under D-12/D-13 the single decoder can
recompute `sha256` over the received bytes, which is exactly what the HTTP header exists
to let a zero-`ccf` client verify. Carrying it as an outcome-level sibling of the vessel
bytes is consistent with both doors; carrying it inside the vessel is not.

**DIV-2 — `replay_ref` reaches no wire consumer at all.** `ServedProduct` carries
`product` + `replay_ref` (`src/ccf/replay/serve.py:94-104`), and `serve.py:42-44` states
plainly: *"all three shipped delivery paths serialize `servable.product` and **none** of
them reads `servable.replay_ref`."* Verified: `command grep -rn "replay_ref" src/ runtime/`
returns hits only in `serve.py` and two docstrings.

The resolver seam is typed `-> ServableProduct`
(`egress.py:258`, `experience.py:348`), so a door **structurally cannot** reach
`replay_ref` — the seam does not carry it.

*Consequence:* the ruled `Result` exposes `.replay_ref` (spec §2, §4.1; D-08 lists it
among guarded post-assembly fields). **No existing door emits it.** `WireOutcome` must
carry it as a member the doors do not have today, and either the in-process adapter's seam
must return `ServedProduct` rather than `ServableProduct`, or the MCP adapter has nothing
to decode into `.replay_ref` when it is built.

**DIV-3 — the request identity is nowhere on the wire.** D-09 requires a refused `Result`
to carry *"product id, parameters, temporal boundary."* The vessel carries `schema_name`,
`schema_version`, `tenant_id` and `temporal_boundary`, and **carries no `parameters`
field** (`contract.py:686-698`). `ProductRequest` — which does carry `parameters`
(`src/ccf/products/request.py:239`) — reaches the replay record's dimension 5
(`ContentGenerationPath.request`, D-IMPL-111 limb (b)) and never the wire.

*Consequence:* the request identity in a `WireOutcome` is a **new member**, not something
read off the vessel. It must be echoed by the outcome or reconstructed by the client from
the `WireRequest` it sent. The latter is cheaper and is what makes it survivable on a
refusal, but it is a decode-path choice the planner should make explicitly, because the
two differ under a proxying transport.

**DIV-4 — no door emits a refusal in any `WireOutcome`-shaped body.** This is the largest
finding, and it is a direct answer to spec §12.4.

Refusals in this tree split into two families:

- **Governance refusals** (`ProductEntitlementRefused`, missing seams, partial address).
  MCP doors: raised, rendered protocol-natively by FastMCP. HTTP: `HTTPException(status,
  detail=refusal_detail(error_code, message))` — a plain `dict[str, str]`
  (`runtime/ccf_runtime/http_api/errors.py:137-139`), so the body is
  `{"detail": {"error_code": …, "message": …}}`.
- **Fabric refusals** — `ProductRequestViolation`, `PayloadSchemaViolation`, the
  `GateRefusal` family, `MixingRefusal`. **These are produced behind the resolver seam
  and have no return path through it**: `ProductResolverProtocol.__call__` is typed
  `-> ServableProduct` with no refusal in the union. A resolver that calls
  `refuse_request` and gets a violation has, at the door, nowhere to put it.

Verified: `refusal_response(refusal: CCFContract, …)` — the function that *does* serialize
a typed refusal contract (`routes/__init__.py:180-185`) — is called by
`http_api/routes/agent.py:57` and `http_api/routes/workflow.py:86` and **not by
`routes/product.py`**.

*Consequence, stated plainly:* **there is no existing shape for the refusal half of
`WireOutcome` to be frozen against.** §12.4's instruction is satisfiable for the served
half (where the two doors already agree byte for byte) and is a genuine greenfield
decision for the refusal half. That is a measurement, not a design objection — but a plan
written on the assumption that §12.4 is purely a transcription task will be wrong.

### 2.4 Which door is closer to the canonical vessel

**Neither is closer; they are identical on the vessel.** The HTTP door carries strictly
*more* verifiable information (the address header) and is the only door with a query
surface, so it is the only one that can carry a `ProductRequest` at all
(`product.py:36-44`, `_asked` at `:245-331`). The MCP resource passes `request=None`
deliberately (`egress.py:440-448`); the MCP tool builds one but with
`parameters={}` hard-wired (`egress.py:588`), so *"a product class whose request contract
declares **any** required parameter is not reachable through this tool"*
(`egress.py:544-549`).

**Planner consequence for D-15 parity:** the MCP adapter, when it arrives, cannot pass
`parameters` through the existing egress *tool*. Either the MCP adapter uses a different
tool shape, or `16-26` (`D-IMPL-133`, client parameters on both doors — recorded as
"neighboring, not gating") becomes gating for the MCP leg of the conformance suite. Worth
recording now so it is not discovered at plan 5.

---

## 3. M2 — the refusal vocabulary as it exists today

### 3.1 Every refusal type on or near the product path

| Type | File:line | Fields | When |
|---|---|---|---|
| `ProductRequestViolation` | `src/ccf/products/request.py:414` | `reason`, `key`, `declared_type`, `presented_type`, `declared_keys`, `presented_keys`, `detail` | **pre-assembly** |
| `PayloadSchemaViolation` | `src/ccf/products/payload.py:115` | same seven fields, `reason` from a 3-member Literal | **post-assembly** (bind) |
| `GateRefusal` (base) | `src/ccf/products/gates.py:130` | `gate`, `detail` | post-assembly, pre-serve |
| `EmptyOperatorRefusal` | `gates.py:144` | (base only) | gate 1 |
| `LineageMismatchRefusal` | `gates.py:148` | `+ declared`, `resolved` | gate 2 |
| `LineageAttributionRefusal` | `gates.py:159` | `+ declared`, `attested_address`, `candidate_address` | federated gate 2 |
| `TTLRefusal` | `gates.py:174` | `+ expires_at`, `now`, `max_ttl_seconds` | gate 3 |
| `AttestationRefusal` | `gates.py:182` | `+ failing_dimension`, `source_mode`, `accepted_modes` | additive gate (D-09) |
| `MixingRefusal` | `src/ccf/products/composition.py:187` | `constituent_id`, `signal_type`, `constituent_expires_at`, `evaluated_at`, `floor_seconds`, + base | assembly (D-IMPL-31) |
| `ProductEntitlementViolation` / `PrincipalNotEntitled` | `src/ccf/products/entitlement.py:95,105` | `LookupError` subclasses — **exceptions, not values** | pre-assembly, at the door |

### 3.2 The four refusal reasons a request can carry

`ProductRequestViolationReason` (`request.py:163-168`) is a closed `Literal`:

```
"undeclared-parameter" | "missing-required-parameter" | "type-mismatch" | "class-mismatch"
```

`refuse_request` (`request.py:525`) checks **address first, then parameters**
(`:566-574`), delegating the parameter comparison to `refuse_payload` and translating its
verdicts through `_REASONS` (`request.py:174-178`). It is *"Pure over its arguments: no
clock, no registry lookup, no I/O"* (`:552`).

### 3.3 The pre/post-assembly split D-09 needs

**Survives onto a refused `Result` (pre-assembly):**

- `ProductRequestViolation` in its entirety — `refuse_request` is called before the graph
  is touched. The shipped worked example proves the ordering:
  `examples/s1-00-companies-over-revenue/produce.py:239-246` calls it under the comment
  *"THE DOOR … Checked before the graph is touched"*, immediately after
  `read(booted, request)` and **before** the L1 ingest loop at `:252`.
- The request identity — but only because the **client** holds the `WireRequest` it sent
  (see DIV-3). Nothing on the wire echoes it.
- Governance refusals (`ProductEntitlementRefused`) are pre-assembly, but are *exceptions*
  at the doors today, not values.

**Only exists after successful assembly:**

- `payload`, `debt`, `debt_evidence`, `source_refresh_recency`, `obligation_in_force`,
  `expires_at`, `lineage` (the full post-assembly one), `plan_id`, `graph_snapshot_at`.
- `content_address` — a function of the whole vessel, so it exists only once the vessel
  does.
- `replay_ref` — exists only after `ReplayWriter.write_replay_record` succeeds
  (`src/ccf/replay/serve.py:153-174`), i.e. strictly after all three gates.

**Sits between:** `PayloadSchemaViolation` and every `GateRefusal`. A candidate
`ContextProductContract` exists at that point — so a *partial* pre-assembly lineage
(`operators_invoked`, `policy_bundle_versions`, `graph_snapshot_at`) is available — but no
`ServableProduct` and therefore no replay record and no authoritative content address.
D-09's *"any pre-assembly lineage/context that existed at the point of refusal"* has a
real, non-empty answer for these refusals and an empty one for a `ProductRequestViolation`.
The planner should decide whether the codec carries that distinction or flattens it.

### 3.4 Is refusal detail dropped at the doors?

**Yes, completely, for every fabric refusal.** The seam type
(`-> ServableProduct`) admits no refusal, so a resolver's `ProductRequestViolation` cannot
cross the door at all. And the door's own governance refusals are flattened to
`{"error_code", "message"}` on HTTP with the typed constant preserved
(`errors.py:44-134` enumerates thirteen `ERROR_*` constants) and to a protocol-native
exception on MCP.

`ProductRequestViolation.detail` is prose *"for the operator reading a log"*; the six
typed fields are *"the machine-readable version"* (`request.py:451-452`). None of the six
reaches any wire today.

---

## 4. M3 — boot: what lazy in-process boot costs and requires (D-16)

### 4.1 The two boot front doors

| | `load_and_boot` | `load_config_and_boot` |
|---|---|---|
| File | `src/ccf/deployment/manifest.py:729` (entry at `:~560`) | `src/ccf/deployment/config.py:614` |
| Authoring form | `manifest.yaml` + N artifact documents | single-file `ccf_config.yaml` (D-IMPL-136 + amendment) |
| Signature | `(manifest_path, *, registry, connection=None, tenant_id=None) -> BootedFabric` | `(config_path, *, registry, connection=None, tenant_id=None) -> BootedFabric` |
| Can express `ccf.signal-batch` | **yes** | **no** |

Underneath both: `ccf.boot.boot(*, backend, connection, secrets, registry,
resolution_spec_key, resolution_spec_version, policy_bundle_key, policy_bundle_version)
-> FabricHandle` (`src/ccf/boot.py:222-232`).

### 4.2 Minimum a caller must supply

Measured by execution. Booting `examples/00-quickstart/artifacts/manifest.yaml` requires
exactly two caller-supplied things beyond the path:

1. **`registry: ControlPlaneProtocol`** — *"A caller argument, never constructed here"*
   (`config.py:691-693`). A bare `ControlPlaneRegistry()` suffices.
2. **`connection`** — the adapter's own settings, validated against the adapter's declared
   contract with `extra="forbid"`. Measured refusal when wrong:
   ```
   InvalidBackendConfig: backend 'sqlite': its connection settings are invalid:
     database_path — Field required
     path — Extra inputs are not permitted
   ```
   `backend:` (the *kind*) is declared in the config/manifest; the connection *values* are
   deliberately never in a content-hashed artifact (`ccf_config.yaml:9-13`;
   `backends.yaml` exists exactly to hold variable *names*, never values).

`tenant_id` is optional when the document names it.

**D-16 consequence:** `CCF_BINDING="inprocess:./deployment"` names a directory. The adapter
must derive *both* the registry (trivial) and the `connection` mapping (not trivial) from
that directory alone. s1-00 solves the second with a `backends.yaml` + a
`connection(root=…)` composer (`deployment.py:130-157`) that reads env-var **names** and
composes values. Whatever the Phase 17 `deployment/` does, it must reach that mapping
without the client ever seeing it — that is real adapter work, and it is not one line.

### 4.3 Cost — measured, and the 74.3 ms figure verified

`.planning/STATE.md:286` records *"boot 74.3 ms once per process"* from **2026-08-10**,
against **s1-01**, not against this branch.

**Measured in this session** (`load_and_boot`, sqlite backend, quickstart manifest, fresh
temp DB per iteration, in one process):

```
load_and_boot ms: [74.2, 63.8, 63.3, 61.4, 64.4, 62.1]
```

**The 74.3 ms figure is confirmed for a cold first boot** (74.2 ms measured). Steady-state
repeat boots in a warm process are **~62-64 ms**.

Separately measured, cold process import cost of the modules an in-process adapter needs
(`ccf.deployment`, `ccf.boot`, `ccf.products.gates`, `ccf.replay.serve`):

```
136.7 ms / 117.8 ms / 127.5 ms
```

So a first `ask()` through a lazy in-process adapter costs roughly **~120 ms import +
~74 ms boot**, before any assembly. `.planning/STATE.md:287` records projection execute at
8.68 ms and the gating replay append at 0.29 ms (2026-08-10, not regression-gated).

### 4.4 Idempotency — boot is **not** repeatable, and this is load-bearing

**Measured in this session:**

```
SECOND BOOT REFUSED: SingleWriterViolation a GraphWriter already exists for graph
  '/tmp/.../g.sqlite'; the fabric permits exactly one writer per graph (INV-CH7-10)
AFTER close(), re-boot OK
```

`manifest.py:626-634` states the contract: *"a loop that never closes leaks one connection
per iteration and will eventually be refused a boot by the single-writer check."*

**Planner consequence, and it is not an optimization:** the in-process adapter **must**
cache the booted `BootedFabric` per binding address for the process lifetime. A
boot-per-`ask()` design does not merely cost 74 ms twice — **the second `ask()` raises
`SingleWriterViolation`** unless the first handle was closed. And a design that closes
after every `ask()` pays the full boot on every call and destroys the graph state if the
store is per-run temporary. Cache-per-binding is effectively forced by the invariant, and
the cache's teardown (process exit? explicit `close()`? never?) is a design point the
spec does not cover and the planner must settle.

### 4.5 Producer-role work to absorb vs provisioning to exclude

Measured against the rejected example. Current line counts (**grown since the handoff's
722**):

| File | lines | AST executable statements |
|---|---:|---:|
| `produce.py` | 411 | 74 |
| `deployment.py` | 417 | 125 |
| `consume.py` | 157 | 58 |
| `scenario/provision.py` | 130 | 55 |
| **Total** | **1115** | **312** |

(The handoff's 722 = `produce` 357 + `deployment` 365 at that time. Both files have since
grown. `MEASUREMENT.md:74-79` records 252 statements across the first three; the current
figure for those three is 257.)

**Provisioning — D-16 forbids a client call triggering any of this:**

- `scenario/provision.py::provisioned()` (`:53`) starts a `postgres:16` testcontainer
  (`:76`) and seeds `companies.sql`. `consume.py:93` wraps the whole call in it. This is
  unambiguously provisioning and must not survive behind the seam.
- `deployment.connection(root=…)` minting a per-run database name from
  `uuid.uuid4().hex` (`deployment.py:156`) — creating a fresh graph per call is
  provisioning too.

**Producer-role work the adapter or the deployment must absorb:**

- `ControlPlaneRegistry()` construction (`produce.py:222`) — trivial.
- `load_config_and_boot(...)` (`produce.py:231`) — this is exactly D-16's *"boot from
  deployment definition"*.
- **L1 ingest** (`produce.py:252-253`): `for envelope in scenario.envelopes:
  booted.handle.worker.ingest(envelope)`. **`load_and_boot` does not ingest** —
  `manifest.py:616-619` states *"the adopter ingests from
  `booted.artifacts[<signal-batch-key>].envelopes` through `booted.handle.worker`."*
  Verified: no `ingest` call exists in `src/ccf/deployment/*.py` or `src/ccf/boot.py`.
- Building the operator registry, reading the graph view, running Π, minting the
  candidate, `run_gates`, `build_replay_record`, `serve` (`produce.py:256-411`).
- The MAX_TTL and product-class registrations, which `manifest.py:622-624` explicitly
  requires stay in adopter code: *"the TTL pin must stay an independently authored
  registration, or Gate 3 compares a ceiling against itself."*

### 4.6 Hard constraint on open sequencing question 1 (demo-data form)

`src/ccf/deployment/config.py:82-91`, verbatim:

> *"There is no `signal_batch` section among the eight reserved names, and that is a
> decision, not a gap. … A deployment that needs one keeps a manifest … and boots it
> through `load_and_boot` instead."*

Confirmed against the artifact class: `ccf.signal-batch` is fixed to `role: load` and is
manifest-only (`src/ccf/deployment/classes.py:200`, `:227`;
`src/ccf/controlplane/artifacts.py:1477`). No example currently carries a `signal_batch`
key in a `ccf_config.yaml`.

**So D-17 ("`deployment/` uses the single-file `ccf_config.yaml` form") and
"boot-consumed seed artifact" are mutually exclusive as the tree stands.** The options,
with their measured costs:

| Option | Cost |
|---|---|
| (a) Pre-seeded store committed into `deployment/` | A binary graph file in `examples/`. Needs a decision on whether it counts as a build artifact; also fixes the backend at author time. |
| (b) `deployment/` carries a `manifest.yaml` with a `signal_batch` entry | Contradicts D-17's `ccf_config.yaml` requirement, which is ruled. |
| (c) Seed data as a plain file in `deployment/` that the adapter ingests | Puts ingest inside `ccf.client`. That is producer work in the SDK's client package — worth a ruling, not an assumption. |
| (d) Extend `ccf_config.yaml` to carry a signal batch | Reverses `config.py:82-91`'s explicit decision (raw events would content-hash into replay dimension 2). Needs a `D-IMPL-140+` ruling. |

This is the single sharpest open item and it should be resolved before plan 4 is written.

---

## 5. M4 — the gate and retirement inventory (D-26, D-27)

### 5.1 D-26 — `tests/examples/test_spine_separation.py`, exactly

**What it asserts** (`tests/examples/test_spine_separation.py`):

- Scope: `SECTION_ONE_GLOB = "s1-*"` (`:56`), directories only (`:97`).
- P1/P4 — exactly one module in the directory opens a canonical `--8<--` region (`:333`).
- P2 — that module opens all seven `D-07` names `("boot","ingest","operators","project",
  "gate","record","serve")` **in that order** (`:76-84`, `:358`).
- P3 — every region opened anywhere is closed and none interleave (`:385`).
- P5 — the region-carrying module does not `print` (`:157-163`).
- P6 — exactly one *fabric-facing* module (one matching `^[ \t]*(?:from|import)[ \t]+ccf\b`)
  prints (`:165-176`).

**Why a Phase 17 example fails it — the answer depends on a directory name, and both
answers are problems:**

1. If the new example is `examples/hw1-companies-over-revenue/` (spec §7's own name), the
   glob `s1-*` **never sees it**. The gate does not refuse it; it goes blind to it. D-26's
   phrasing (*"it will not pass a Phase 17 example"*) is not what the code does.
2. If the new example is named `examples/s1-*`, it is refused on P1 (a `consume.py` that
   imports only `ccf.client` + stdlib opens zero canonical regions → *"no module opens any
   of the seven canonical regions"*), and on P6 if the `deployment/` holds no
   `ccf`-importing module.
3. **Under D-27, whichever name is chosen, removing the `s1-*` trees breaks the gate's own
   vacuity preconditions:**
   - `test_the_section_one_tree_is_populated` (`:295`) asserts `split_examples(...)` is
     non-empty → **fails**.
   - `test_the_marker_pattern_matches_the_shipped_form` (`:311`) does
     `split_examples(EXAMPLES_ROOT)[0]` → **IndexError**.
   - `_copied_example` (`:446`) does the same → every one of the eight negative controls
     **errors**.
   - `test_the_fabric_facing_scope_admits_and_excludes_on_the_import` (`:620`)
     **asserts** — deliberately does not skip (`:635-638`) — that
     `<example>/scenario/provision.py` exists. It breaks the moment s1-00 loses that file,
     even if s1-00 itself survives.

**So D-26 is not "re-scope or retire one test." It is "re-scope or retire one module of
14 test functions whose eight negative controls are all built on `_copied_example`,"** and
the retirement must land in the same change as the tree removal or `make ci-core` goes red
mid-phase.

### 5.2 The three other example gates D-26 does not name, and they behave the same way

| Gate | Scope | Breaks how |
|---|---|---|
| `tests/examples/test_section_one_is_agent_free.py` | `SECTION_ONE_GLOB = "s1-*/**/*.py"` (`:63`) | `test_the_section_one_tree_is_populated` (`:142-156`) asserts s1-* dirs exist **and** contain Python modules. Removing s1-* → fails. A `hw1-*` example is invisible to it. |
| `tests/examples/test_artifact_schema_headers.py` | `EXAMPLE_ROOT_MARKER = "run.py"` (`:159`); artifacts by `examples/**/artifacts/*.yaml` (`:245`) | `test_…_populated` (`:260-267`) asserts at least one `run.py` and at least one `artifacts/*.yaml` exist under `examples/`. **s1-00 has no `run.py`** and no `artifacts/` dir. The Phase 17 example has `consume.py` and `deployment/ccf_config.yaml` — so it satisfies neither marker. Remove `00`–`08` + `s1-01` and both preconditions fail. |
| `tests/examples/test_gate_two_divergence.py` | constructs `examples/00-quickstart/run.py` (`:96`) | Direct path construction — hard break on removal. |

### 5.3 `tests/products/test_gate_two_call_shape.py` — the floors with no headroom

`SCANNED_TREES = ("src","runtime","examples")` (`:474`);
`BINDER_SCANNED_TREES = ("examples",)` (`:478`).

| Constant | Line | Value | Comment's own witness list |
|---|---:|---:|---|
| `MINIMUM_GATE_CALL_SITES` | 582 | **11** | 00, 01, 02, 03, 04/producer_child, 06, 07, 08, external/00/serve.py, **s1-00/produce.py**, **s1-01/spine.py** |
| `MINIMUM_PROJECTING_BODIES` | 592 | **13** | the above plus two `resolve_plan` bodies |
| `MINIMUM_RESOLVED_BINDER_SITES` | 619 | **12** | s1-00 contributes **zero** (it is the one-document exemption) |
| `MAXIMUM_ONE_DOCUMENT_DEPLOYMENTS` | 521 | **1** | s1-00 is the sole claimant, *"no headroom, on purpose"* |
| `MINIMUM_IMPLEMENTATIONS` (`test_required_operators_guard.py`) | 94 | 9 | 12 witnesses, headroom 3 |

Every one of these is explicitly ceilinged with **no headroom** (`:521`, `:582`, `:621-631`).
Removing every condemned tree takes the first three to roughly **0-1**. All three fail,
plus the `_gate_scopes()` / `_projecting_scopes()` / `_resolved_binder_sites()` scan
functions that feed them.

`FLOOR_REMOVAL_INSTRUCTION` (`:625-631`) states the required remedy: *"Lower the constant
in the same commit as the removal and name the removed site in the commit message."*

**Note on `MAXIMUM_ONE_DOCUMENT_DEPLOYMENTS = 1`:** s1-00 currently claims the single
exemption slot. If s1-00 is removed and the Phase 17 `deployment/` also authors one
operator-set document, the count stays at 1 and the ceiling holds. If s1-01 is kept and
the new example claims it too, the count goes to 2 and
`test_the_one_document_exemption_has_not_spread` fires.

### 5.4 The exhaustive-door assertion does **not** see `src/ccf/client/`

`tests/invariants/test_mcp_role_separation.py:541-548`:

```python
PRODUCT_DOOR_MODULES = ("ccf_runtime.mcp.egress", "ccf_runtime.mcp.experience",
                        "ccf_runtime.http_api.routes.product")
RUNTIME_ROOT = .../runtime/ccf_runtime
```

The exhaustiveness proof — built in 15.5 specifically so *"a fourth door fails the
suite"* — walks `RUNTIME_ROOT` only, detecting modules that **call** a
`ProductResolverProtocol`-annotated parameter or a `.product_resolver` attribute
(`_calls_a_product_resolver`, `:579-606`). An in-process product path in
`src/ccf/client/` is outside that walk and will not trip it.

**Verified, and reported as an adjacency rather than a blocker:** the Phase 17 in-process
adapter will serve Context Products with no entitlement check (deliberately — the
not-list defers principal/entitlement at the client seam to the MCP adapter work), and
the gate that exists to catch exactly a new ungoverned product door **will stay green**.
The planner should decide whether to widen `RUNTIME_ROOT` to include `src/ccf/client/`
with a stated exemption, or to record the gap. Silence is the option this project's own
lesson (*"a measurement nobody is looking at protects nothing"*) argues against.

### 5.5 Makefile — every target naming a condemned tree

| Line | Target | Tree |
|---:|---|---|
| 29-31 | `.PHONY` list | all |
| 83-108 | `example-00` … `example-08` | `00`–`08` |
| 110-111 | `example-ext-00` | `external/00-hello-context` |
| 124 | `examples:` aggregate (ten targets) | `00`–`08` + ext-00 |
| 173-175 | `example-s1-01` | `s1-01` |
| 187-190 | `example-s1-00` | `s1-00` |
| 242-252 | four live-leg targets | `03`, `external/00` |
| 360-361 | `measure-examples` | via `tools/measure_examples.py` |

`make ci` = `ci-core examples docs-strict` (`Makefile:81`). Removing the ten aggregate
targets empties `examples:`, so `make ci` needs an explicit decision (empty target vs
removed from `ci`).

### 5.6 CI — `.github/workflows/`

| File:line | Reference |
|---|---|
| `ci.yml:35` | `pytest tools/lints/tests -q` (not in `make ci`) |
| `ci.yml:184,192,199,206,214,226,230` | `pytest tests …` — picks up every `tests/examples/*` module |
| `ci.yml:238-270` | `examples` job, `name: examples suite (00–07, reference backends)`, runs `make examples` |
| `ci.yml:314` | `pytest tools/publish_scan_tests tools/docs_tests -q` (not in `make ci`) |
| `live-legs.yml:6` | comment naming `examples/03-harness-portability` |
| `perf.yml` | via `perf/suites/crossproc/conftest.py:52` → `examples/04-cross-process` |

**No CI job runs `make example-s1-00` or `make example-s1-01`.** s1-00 is exercised only
through `tests/examples/test_s1_00_output.py` (`pytestmark = pytest.mark.postgres`, `:47`);
s1-01 only through `tests/examples/test_s1_01_output.py`
(`pytestmark = pytest.mark.fluree`, `:96`), i.e. the `make leg-fluree` / `-m fluree` leg.

### 5.7 Published snippets

**`command grep -rn "s1-0" public/` returns nothing.** The `s1-*` trees have **zero**
published-snippet exposure. All 53 `snippet-include` couplings in
`RETIREMENT-COUPLINGS.md` belong to `00`–`08` + `external/00`, across seven `public/`
pages:

`public/how-to/bind-a-harness-adapter.md`, `compose-a-workflow-with-hitl.md`,
`grant-and-revoke-a-skill.md`, `run-agents-cross-process.md`, `swap-the-artifact-store.md`,
and `public/reference/artifacts/{agent-definitions,control-plane-artifacts,
product-registration,prompt-artifacts,skill-catalog,skill-grants,task-definitions,
workflow-definitions}.md`.

Plus `README.md:45,58-65` (one prose line + eight markdown links).

### 5.8 The retirement sweep — the tool D-27 should use, and its two defects

`tools/retirement_sweep.py` already exists and produces
`docs/surface/examples/RETIREMENT-COUPLINGS.md`, with a standing freshness gate at
`tools/docs_tests/test_retirement_sweep.py:537`.

Two measured problems the planner must budget for:

1. **`RETIREMENT_SCHEDULE` (`tools/retirement_sweep.py:128-156`) does not list `s1-00` or
   `s1-01`.** It lists the ten Phase-16 retirees only. D-27 must add both, or the sweep
   answers a question nobody asked.
2. **The committed report is already stale and the gate is already red** (§1): 163 rows /
   47 files committed against 248 rows / 68 files live. And
   `test_no_gitignored_path_reaches_the_report` fails because `.superpowers/sdd/**` is
   gitignored and not in the sweep's prune list — so the sweep is currently
   non-reproducible.

**The prescription:** fix the prune list, add `s1-00`/`s1-01` to the schedule, re-run
`python tools/retirement_sweep.py --report`, and use the regenerated table as D-27's
inventory. That is a far better basis than any hand list — including this one — and it is
the only form that comes with a CI gate proving it is complete.

### 5.9 Housekeeping found while sweeping

- A stale git worktree exists at `.claude/worktrees/agent-a687369f976c702a7/` containing a
  full second copy of the tree, including an older `examples/s1-00-.../artifacts/config/`
  layout. It is not on any gate path but it doubles every repo-wide grep. Worth removing
  before D-27's inventory work.
- `Makefile:351-352` references `tests/examples/test_surface_audit.py` as *"the audit
  assertion lives in the always-on `test` job"*. **That file does not exist**
  (`ls tests/examples/` confirms). A stale comment, not a live coupling.

---

## 6. M5 — package placement and invariants

### 6.1 Placement is clean

`src/ccf/__init__.py` is a docstring plus `__all__: list[str] = []`. It exports nothing,
and every subsystem is a subpackage (`agents/`, `artifacts/`, …, `workflow/`). Adding
`src/ccf/client/` requires **no edit to `__init__.py`** and follows the existing
convention exactly. `from ccf.client import ProductClient` works via the src-layout
package find (`pyproject.toml:138-139`, `where = ["src","runtime"]`).

### 6.2 Every lint that will see `src/ccf/client/`

`tools/lints/__main__.py:71`: `LINTED_TREES = ("src","runtime","examples","tests")`.
`RULE_TREE_SCOPE` (`:123-130`):

| Rule | Scope | Sees `src/ccf/client/`? | Sees the new `examples/…/consume.py`? |
|---|---|:--:|:--:|
| `no-hardcoding` (cinv01a/b/c) | src, runtime, examples, tests | **yes** | **yes** |
| `harness-imports` (cinv02-harness / -graph-writer / -deployment-gates) | src, runtime | yes | no |
| `algorithmic` (cinv03) | src, runtime | yes | no |
| `orchestration-imports` (d06) | src, runtime | yes | no |
| `backend-imports` (cinv02-backend-import) | src, runtime | yes | no |
| `substrate-names` (cinv04-substrate-name / -prose) | **src only** | **yes** | no |
| `citations` (cite01/02/03) | own `GATED_TREES` (`citations.py:153`) | yes | yes |

**`algorithmic` only fires on modules that opt in** by declaring
`__ccf_mode__ = "algorithmic"` at top level (`tools/lints/algorithmic.py:70-82`); it bans
importing `ccf.llm` or a vendor SDK. `ccf.client` importing boot/deployment machinery is
unaffected — the rule says nothing about the filesystem
(`src/ccf/deployment/__init__.py:45-62` states this precedent explicitly, citing
`src/ccf/boot.py` opening SQLite files under the same tag).

**`substrate-names` is `("src",)` alone** and is the one rule the client package is
*uniquely* exposed to: no module under `src/` may name a substrate. A `BindingError` or
`TransportError` message that mentions `sqlite`, `postgres`, `neo4j`, `mongo` or `fluree`
will fire `cinv04-substrate-name`. The client's error prose must name **schemes**
(`inprocess`, `mcp+stdio`, `http`), never backends.

### 6.3 The `cinv01a-prompt-shape` hazard, measured precisely

D-05 requires a `BindingError` *"with a refusal-quality message naming exactly what to
set."* That is a long string literal in `src/`, which is what the false positive noted in
the handoff bites.

Mechanism, from `tools/lints/no_hardcoding.py`:

- `_is_prose_candidate` (`:291-301`) — skipped entirely if `len < 40` (`MIN_PROMPT_CHARS`,
  `:80`), if there is no space, if the literal **contains `://`** (`:297-298`), or if it
  opens with a SQL keyword.
- `prompt_score` (`:340-352`) — +1 each for: ≥3 sentences (`MIN_SENTENCES = 3`, `:84`), a
  `ROLE_OPENERS` prefix (`"you are"|"always"|"never"|"respond"`, `:88`), ≥3 `{`
  (`MIN_BRACES = 3`, `:86`), length > 200 (`PROSE_CHARS`, `:82`). Flags at **score ≥ 2**
  (`PROMPT_SCORE_THRESHOLD = 2`, `:90`).
- `is_developer_diagnostic` (`:321-337`) — exempts a literal that carries at least one of
  a backticked span, a repo-relative filename, or a `callable()` reference
  (`DIAGNOSTIC_MARKERS`, `:116-120`) **and** does not `addresses_a_reader`
  (`:304-318`: a role opener, ≥3 `{`, or any `you`/`your`/`you're`/`you've`).

**Actionable prescription, derived not guessed.** A `BindingError` message stays green if
it does *any one* of:

- contains `://` anywhere — and a message illustrating `http://…` as a future scheme does
  exactly this, exempting the literal before scoring even runs; **or**
- carries a `` `backtick` `` span, a `foo.yaml`-style path, or a `for_product()`-style
  callable reference, **and** contains no second-person pronoun and fewer than three `{`.

**Do not weaken the message to pass the lint** (standing hazard note). Prefer the second
form: `Set CCF_BINDING, e.g. inprocess:./deployment, or pass binding= to for_product().`
— naming `for_product()` makes it a developer diagnostic, and avoiding "you" keeps it one.

### 6.4 There is no `src/`-resident seam that yields a gate-admitted product

This is the load-bearing M5 finding.

**Measured:** no module under `src/` imports `ccf_runtime`. Every `ccf_runtime` token in
`src/*.py` is inside a docstring cross-reference (`:class:`/`:mod:`/`:func:` roles) —
17 files, zero import statements.

The two seams that yield an already-gated product live in `runtime/`:

- `ccf_runtime.mcp.egress.ProductResolverProtocol` (`egress.py:195-299`)
- `ccf_runtime.mcp.experience.ExperienceProductResolverProtocol` (`experience.py:288-357`)

Both are `(*, tenant, product_class, version, perspective, request) -> ServableProduct`.

The nearest `src/`-resident seam is **`ccf.agents.assembler.ContextAssemblerProtocol`**
(`src/ccf/agents/assembler.py:242-288`), shipped in 15.5 under D-IMPL-97:

```python
def assemble(self, *, request: ProductRequest, perspective: Perspective,
             tenant_id: str) -> AssemblyOutcome
```

`AssemblyOutcome` (`:188-238`) carries `payload`, `consultations`, `acquisitions`,
`assembler_id`, `assembler_version`, `skill_set_in_force`, `halflife_debt_profile`. **It
is one level below the vessel** — no `ContextProductContract`, no gates, no replay record,
no `ServedProduct`.

**The consequence the planner must sequence around.** The in-process adapter needs a
`ServedProduct` (for `.replay_ref`) or at least a `ServableProduct` (for the vessel). Three
shapes, with their costs:

| Shape | Cost |
|---|---|
| (a) `ccf.client` reaches through a **new `src/`-resident resolver Protocol** the deployment supplies | Consistent with D-14 (*"imports only core boot/deployment machinery"*), keeps the SDK off the verdict path, and mirrors the two `runtime/` seams. But: where does the deployment's resolver *come from* when the client only holds a directory path? It must be discoverable from `deployment/` — an entry-point, a declared module path, or an SDK-supplied generic resolver. |
| (b) `ccf.client` imports `ccf_runtime.mcp.egress.ProductResolverProtocol` | Would be the **first `src` → `runtime` import in the tree**. Contradicts D-14 as written. |
| (c) `ccf.client` runs `run_gates` + `serve` itself | Puts an SDK-owned verdict on the serve path — precisely what `D-IMPL-102` limb 3 declined and what `egress.py:230-241` and `experience.py:322-330` argue against at length (*"The SDK cannot call a comparison whose second operand it does not have"*). Also makes `src/ccf/client/` a fourth product door with no entitlement (§5.4). |

Shape (a) is the only one consistent with the rulings as written. It implies **one new
Protocol in `src/`** that the spec does not name, and how a `deployment/` directory
supplies its implementation is an open question with no measured answer in the tree.

### 6.5 `pyproject.toml`

- `[tool.mypy] files = ["src","runtime"]` (`:159`), `strict = true`,
  `warn_unreachable = true`. **`src/ccf/client/` is fully typechecked. `examples/` is
  not** — any mypy claim about `consume.py` is vacuous (standing hazard, confirmed).
- `[project.scripts] ccf = "ccf_runtime.cli.main:main"` (`:50`) — the client ships no new
  console script under the four-name surface (D-03).
- `[tool.setuptools.packages.find] where = ["src","runtime"]` (`:138-139`) — `ccf.client`
  is picked up with no packaging edit.

---

## 7. Validation architecture — and how to sabotage each check (D-22)

Test framework: **pytest 8.x** via `.venv/bin/python -m pytest`.
Quick run: `PYTHONPATH=src:runtime .venv/bin/python -m pytest tests/client -q`.
Full suite: `make ci-core` **plus** `pytest tools/docs_tests tools/publish_scan_tests -q`
(§1). Phase gate: `make ci` + the `tools/` suites, green.

| Ruled property | Where it can be verified | How to SABOTAGE it so the check is proven to fire |
|---|---|---|
| **D-15(a) parity — identical `Result` fields + identical content address across adapters** | Parameterized conformance suite over the adapter registry | In a copy of the in-process adapter, mutate one vessel field before encoding (e.g. bump `expires_at` by 1s). The address must move and the parity assertion must fail. A parity test that compares only `payload` will stay green — that is the failure mode to prove absent. |
| **D-15(b) refusal parity** | Same suite, refusal leg | Change one adapter's decode to drop `refusal.key`, leaving `reason`. Assert the suite reports a difference, not a pass. |
| **D-08 guard — post-assembly field access raises** | Per-field parameterized test over the six guarded names (`payload`, `debt`, `content_address`, `replay_ref`, post-assembly `lineage`, `expires_at`) | Replace one guard with `return None`. The test must fail **for that field specifically**. A single `pytest.raises` on `result.payload` licenses five unguarded fields — assert per field, never `any()`. |
| **D-15(d) wire failure ≠ refusal** | Kill the transport mid-suite | Make the adapter swallow its transport exception and return a synthesized refusal `WireOutcome`. The test must fail. Without a control here, `except Exception: return refusal` passes silently — this is the exact inversion D-07/D-10 exist to prevent. |
| **D-20 codec round-trip `decode(encode(x)) == x`** | Property tests over served products and refusals; the tree already has `hypothesis` (`.hypothesis/` present) | Drop one field from the encoder. The round-trip must fail. Then drop the *same* field from the decoder's comparison — if the test still passes, the test compares a projection, not the value. |
| **D-19(a) purity gate — AST, `ccf.client` + stdlib only** | New AST gate over the example's reader-visible Python | Add `import deployment` to a `tmp_path` copy of `consume.py`; the gate must refuse. Then add `from produce import x` (a `from`-import, a different AST node) — a gate matching only `ast.Import` misses `ast.ImportFrom`. Also add a deferred import inside a function body: `test_spine_separation.py`'s own regex-based ancestors were fooled this way. |
| **D-19(b) budget gate — `consume.py` ≤ 80 lines** | Line count over the example | Append 20 blank lines and 20 comment lines separately. Decide and *test* which the budget counts; a gate that counts neither can be defeated by a 300-line file of one-statement-per-comment. |
| **D-21 binding resolution** | Unit tests | Set `CCF_BINDING` **and** pass `binding=`; assert the kwarg wins by observing which adapter ran, not by reading back a stored attribute (a stored attribute proves storage, not dispatch). Unset both; assert `BindingError` and assert its message contains the literal `CCF_BINDING`. |
| **D-23 two thresholds → two content addresses, through the client seam** | Replaces `tests/examples/test_s1_00_output.py::test_two_thresholds_are_two_products` | Make the projection ignore the threshold parameter. Both addresses become equal and the test must fail. |
| **D-16 no provisioning inside a client call** | AST/behavioral gate over `src/ccf/client/` | Add a `testcontainers` import or a `CREATE TABLE` to the adapter; the gate must refuse. Also assert positively that a second `ask()` on one client does **not** re-boot (§4.4) — otherwise the caching is unproven and the second call raises `SingleWriterViolation` only in a real deployment. |

**The standing lesson applies with full force here.** `.planning/HANDOFF-2026-08-15.md:170`:
*"Every defect found was in the verification or in the plans, never in the mechanism."*
The gate work shipped five of its own. Every one of the twelve rows above should have its
sabotage control written **in the same plan** as the assertion, not deferred.

---

## 8. Natural requirement groupings for ID minting

`CLNT-` is **free** — verified: `command grep -rn "CLNT" .planning/REQUIREMENTS.md docs/`
returns nothing. Prefixes already in use in `.planning/REQUIREMENTS.md`: `CINV-`, `CPS-`,
`DCD-`, `DEMO-`, `DOCS-`, `ERGO-`, `EXAM-`, `GATE-`, `HARD-`, `PERF-`, `SUBQ-`; plus the
gated-phase set named in `.planning/STATE.md:294`: `RSCH-`, `DSGN-`, `FEAS-`, `FABR-`,
`AGNT-`, `XPRC-`.

The work falls into six natural groups, matching the five ordered deliverables plus the
inherited cleanup:

| Group | Covers | Rulings |
|---|---|---|
| **A — Client surface** | four exported names; `for_product`/`ask`; `Result`/`Refusal`; the fail-closed guard; error taxonomy | D-03, D-04, D-07, D-08, D-09, D-10, D-24 |
| **B — Binding resolution** | kwarg → `CCF_BINDING` → `BindingError`; scheme registry dict | D-05, D-06, D-21 |
| **C — Adapter seam and codec** | `TransportAdapter`, `WireRequest`, `WireOutcome`, the single decoder, the in-process degenerate wire, lazy cached boot | D-11, D-12, D-13, D-14, D-16, D-20 |
| **D — Parity enforcement** | the conformance suite, the sabotage controls | D-15, D-22, D-23 |
| **E — The first example** | `consume.py`, `deployment/`, README, make target, purity gate, budget gate | D-02, D-17, D-18, D-19 |
| **F — Inherited discharge** | `test_spine_separation.py` and its three sibling gates; the floor constants; condemned-tree removal; the retirement sweep; the `tools/` suite failures | D-25, D-26, D-27 |

`CLNT-01..NN` reads naturally over A–E; F is discharge of existing rulings and may be
better carried as `CLNT-` too, so one phase mints one prefix.

**Decision-log numbering:** the high-water mark in `docs/DECISIONS.md` is **`D-IMPL-139`**.
New Phase 17 rulings start at **`D-IMPL-140`**.

---

## 9. Conflicts with a ruling

**One, and it is a scope conflict rather than an unimplementable ruling.**

**Spec §12.4 / CONTEXT `<deferred>` item 4** instructs: *"name and freeze the shape MCP
egress and the HTTP product routes **already emit**. Divergences found between those two
are defects to fix, not shapes to standardize around. This is a measurement task for
research, not a design task for planning."*

**Measured:** for a **served** product the instruction is satisfiable and the answer is
clean — both doors emit `canonical_bytes(ContextProductContract)` and nothing else, and
the one divergence (DIV-1, the HTTP address header) is documented as a property of the
transports rather than a defect.

**For a refusal, there is nothing to freeze.** No product door emits any fabric refusal
in any body (DIV-4, §2.3): the resolver seam is typed `-> ServableProduct` with no refusal
in the union, `refusal_response` is not called by `product.py`, and every fabric refusal
type (`ProductRequestViolation`, the `GateRefusal` family, `PayloadSchemaViolation`,
`MixingRefusal`) reaches no wire. Likewise `replay_ref` (DIV-2) and the request's
`parameters` (DIV-3) are emitted by no door and are required by D-09/§2 of the spec.

So `WireOutcome` is **not** wholly a transcription of an existing shape. Roughly half of
it — the refusal channel, `replay_ref`, and the echoed request identity — is new surface
that the phase must design under D-11's discretion grant, and it should be planned with
that budget rather than as a naming exercise.

I do not propose a shape for it, and I make no recommendation on the codec, the binding
scheme, or the refusal semantics. The point is only that the plan must allocate design
time here that §12.4's phrasing implies is unnecessary.

---

## 10. Open questions the planner must resolve

1. **Demo-data form (spec §12.1).** `ccf_config.yaml` cannot carry a `signal_batch`
   (`src/ccf/deployment/config.py:82-91`), and `load_and_boot` does not ingest
   (`manifest.py:616-619`). *Constraint:* D-17 mandates `ccf_config.yaml`; D-16 forbids
   provisioning in a client call. Four options with costs are in §4.6; option (d) needs a
   `D-IMPL-140+` ruling.

2. **Where the in-process adapter gets a gate-admitted product.** No `src/`-resident seam
   yields one (§6.4). *Constraint:* D-14 says core boot/deployment machinery only, and
   `src` has never imported `ccf_runtime`; `D-IMPL-102` limb 3 and `D-IMPL-113` keep
   SDK-owned verdicts off the serve path.

3. **Boot-cache lifetime.** Caching is forced by `SingleWriterViolation` (§4.4). *Constraint:*
   the spec is silent. Decide: cached for process lifetime, keyed by binding address; is
   there a `close()`; what happens on two `ProductClient`s for one binding.

4. **Example directory name.** `hw1-*` (spec §7) makes the new example invisible to
   `test_spine_separation.py` and `test_section_one_is_agent_free.py`; `s1-*` makes it
   refused by both. *Constraint:* D-26 requires the gates be handled either way, and D-27
   forbids partial state.

5. **Entry-file name.** `consume.py` rather than `run.py` means
   `tests/examples/test_artifact_schema_headers.py` (`EXAMPLE_ROOT_MARKER = "run.py"`,
   `:159`) does not recognise the example as an example root. *Constraint:* D-17 names
   `consume.py`; the gate's own populated-precondition breaks if `00`–`08` and `s1-01` all
   go.

6. **Whether the product-door exhaustiveness gate widens to `src/ccf/client/`** (§5.4).
   *Constraint:* the v0 not-list defers client-seam entitlement, so a widened gate would
   need a stated exemption rather than a passing assertion. Doing nothing leaves a gate
   that cannot see the new door.

7. **`tools/` suites in the local gate.** Three pre-existing failures, two of them the
   retirement-sweep machinery D-27 depends on (§1). *Constraint:* they must be green
   before Actions is green; `make ci` does not reach them today.

8. **MCP adapter parameter passing.** The shipped egress tool hard-wires
   `parameters={}` (`egress.py:588`), so a class with any required parameter is
   unreachable through it. *Constraint:* D-15 requires the MCP adapter to pass the same
   conformance suite as in-process, and D-23's two-thresholds property needs
   `parameters` on the wire. `16-26`/`D-IMPL-133` is recorded as non-gating; it may become
   gating for deliverable 5.

---

## 11. Sources

**Primary — read in full or in the cited range, this session:**

`docs/superpowers/specs/2026-08-15-ccf-client-design.md` ·
`.planning/phases/17-.../17-CONTEXT.md` · `.planning/HANDOFF-2026-08-15.md` ·
`.planning/STATE.md` · `.planning/ROADMAP.md:1302-1352` · `CLAUDE.md` · `Makefile` ·
`pyproject.toml` · `.github/workflows/ci.yml` ·
`src/ccf/products/{contract,request,payload,gates,composition,bind}.py` ·
`src/ccf/contracts/canonical.py` · `src/ccf/replay/serve.py` · `src/ccf/boot.py` ·
`src/ccf/deployment/{__init__,config,manifest}.py` · `src/ccf/agents/assembler.py` ·
`src/ccf/__init__.py` · `runtime/ccf_runtime/mcp/{egress,experience}.py` ·
`runtime/ccf_runtime/http_api/{errors.py,routes/__init__.py,routes/product.py}` ·
`tests/examples/test_spine_separation.py` · `tests/products/test_gate_two_call_shape.py` ·
`tests/invariants/test_mcp_role_separation.py` · `tools/lints/{__main__,no_hardcoding,algorithmic}.py` ·
`tools/retirement_sweep.py` · `docs/surface/examples/RETIREMENT-COUPLINGS.md` ·
`examples/s1-00-companies-over-revenue/{consume,deployment,produce}.py`, `MEASUREMENT.md`

**Commands run this session (outputs quoted above):**

```
git branch --show-current; git log --oneline -3
make ci-core
PYTHONPATH=.:src:runtime .venv/bin/python -m pytest tools/docs_tests tools/publish_scan_tests tools/lints/tests -q
PYTHONPATH=src:runtime .venv/bin/python   # load_and_boot timing × 6, sqlite
PYTHONPATH=src:runtime .venv/bin/python   # double-boot SingleWriterViolation probe
PYTHONPATH=src:runtime .venv/bin/python -c "import ccf.deployment, ccf.boot, ..."  # ×3
.venv/bin/python -c "<ast statement counter>" examples/s1-00-*/{produce,deployment,consume}.py scenario/provision.py
docker info
command grep -rn ...   # every quoted grep used `command grep`, per the ugrep-shim hazard
```

**No claim in this document rests on training data or on an unverified prior report.** The
74.3 ms boot figure and the 3305-test baseline were both carried in from `STATE.md` and
both were **re-measured**; the retirement-couplings table was carried in and was found
**stale by 85 rows**, which is why it is cited as a tool to re-run rather than as an
inventory to trust.

---

## 12. Metadata

**Confidence:** HIGH across all five measurements. Every figure was produced by a command
run on `phase-17` @ `543eda0` or read at a cited line, and no source was modified.

**Valid until:** any commit touching `examples/`, `tests/examples/`,
`tests/products/test_gate_two_call_shape.py`, the three door modules, or the floor
constants. The floor values in §5.3 and the coupling counts in §5.8 in particular are
tree-derived and will move.
