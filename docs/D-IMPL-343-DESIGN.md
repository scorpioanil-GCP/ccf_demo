# D-IMPL-343 — Launch-Quality Context Product Developer Experience — DESIGN

**Status:** DESIGN PACKAGE, awaiting Dave's implementation ruling. No SDK, runtime,
example or test code was written or changed for this document. The branch holds
the three decision entries and this file.

**Branch / SHA:** `d-impl-343-dx` at `1e22dae2` before this file; `main` is also at
`1e22dae2`, so the design was measured against the approved tree.

**Decision-id status, verified from `docs/DECISIONS.md`:** `D-IMPL-343` was free when
it was opened (the footer read `D-IMPL-343`; `D-IMPL-341` at `:3887` is CP03C-F-01
and `D-IMPL-342` at `:3897` is CP03C-F-05 — neither was a helper entry, so nothing was
retired or absorbed). The entry stands at `:3907` with Dave's consolidated amendment.
**Next free id: `D-IMPL-344`.** This design spends no id; every ruling it asks for is
numbered below as `R-n` and becomes a `D-IMPL` entry only when Dave rules it.

**Measured baseline (HEAD `1e22dae2`, counter reproduced in Appendix A):**

| subject | code lines |
|---|---|
| `examples/cp-03-canonical-obligor-financial-spread` — produce / deployment / projection / acquisition / run / server/serve | 99 / 341 / 148 / 442 / 93 / 243 = **1366** |
| the one consumer of a governed `mcp_product` child, `tests/examples/test_cp_03_canonical_cross_deployment.py` | **419** |
| the six example doors (`examples/*/server/serve.py`) + hw1's `compose.py` | 965 + 77 (1743 physical lines) |
| the four producer documents — `ccf_config.yaml` / `backends.yaml` / `server/door.yaml` / `artifacts/ttl.yaml` | 411 / 65 / 54 / 28 physical; 213 / 30 / 24 / 6 non-comment |

The census that ran before this document attributed its baseline to `bff2ff17`.
That attribution was wrong: `git ls-tree bff2ff17 examples/` contains no canonical
spread (the tree entered at `6f062664`, merged `10363356`), and eighteen SDK files
changed between `bff2ff17` and HEAD. Every number and line reference in this
document is at **HEAD `1e22dae2`**, re-measured.

**New launch-relevant findings discovered during design** (detail in §14 and §15):

1. **There is no declarative path for the composing agent today.** The `agent:`
   section the consumer road needs cannot be derived through `_RESERVED_SECTIONS`:
   three existing guards refuse it (`ccf.agent-definition` is an author-versioned
   class; the typed derivation injects `semver`; the reserved-section guard test
   requires a typed class). Every consumer therefore builds its agent definition in
   Python — the §6.4 shape. Ruling `R-2`.
2. **`producers.<label>.offers[].versions_from` is a floor by contract and an exact
   address by use.** A floor below the producer's served lane passes every open-time
   check and is refused at every serve as `class-mismatch → ineligible` with no
   reason retained (CP03C-F-05 compounds it). Ruling `R-13`.
3. **A resolver preview does not delete the effective-request double derivation; it
   relocates it into `src/`.** The resolver's constraint resolution performs audited
   Control Plane reads; a preview runs them twice per question. Only an acquisition
   seam on the governed call satisfies `D-IMPL-289`. Ruling `R-4`.
4. `examples/cp-04-canonical-corporate-family-tree/deployment.py:88-97` mints a
   **fixed** substrate path — the exact shape CP03C-F-02 measured serving one
   obligor's spread for another. Recorded in §4 as a duplication site with a defect
   weight; it is the P2 responsibility the paved road takes over. Not edited here.
5. `artifacts/ttl.yaml:28` on the canonical spread declares a third TTL key,
   `ttl_anchor_basis: latest_filed_date_in_payload`, that no SDK or runtime code reads.
   Evidence for `D-IMPL-341`, not a new decision.

None of the five is CP-14 work, `D-IMPL-341` work or `D-IMPL-342` work.

---

## How this document was produced, and how to read it

A fifteen-agent workflow ran before this file was written: six census agents
(producer, consumer, SDK surface, duplication, misconfiguration and guards, rulings,
CP-14 target), three independent designers (one object, config-first, protocols), one
synthesis, three refuters (rulings and constraints; hidden complexity and leaks;
composability, escape hatches and migration) and one completeness critic. **Every
claim the refuters and the critic made was checked against the tree before it
entered this document**, and where two reviewers disagreed the tree decided —
Appendix B records which findings were accepted, which were rejected, and why.

Reading rules:

- **Measured** figures carry a `file:line` or an instrument. **Estimated** figures
  (every "after" number) are marked as estimates and become measured only at the
  dogfood (§10 step 3).
- "Owner" in §3 means *who legitimately owns the decision*, never who writes the
  most lines.
- Where the design needs a ruling before it can be built, the text says `R-n` and
  §14 carries the options and the recommendation. The design does not present an
  unruled reading as settled.

---

## 1 · Current producer workflow — twelve steps, measured on the canonical spread

Tree: `examples/cp-03-canonical-obligor-financial-spread` (the merged `CP14-F-22`
producer, `D-GATE-cp-03-canonical`). Each step lists the adopter's code and
configuration, the SDK API involved, any duplicated authority, the failure modes the
step can produce today, and whether the step is product-specific or generic
machinery.

### P1 · Declaration and configuration

- **Adopter writes:** `ccf_config.yaml` (411 lines: `product_class` with
  `declared_product_gate` and `discovery`, `operators`, `request_contract`,
  `resolution`, `half_life` with `decay_basis: valid-from` on three rows,
  `debt_profile`, `policy`, `default_perspective`); `backends.yaml` (65: the two
  source stores' env-var names and remedies, plus `per_run: path` with
  `prefix`/`suffix`); `server/door.yaml` (54: `producer_id`, `principal_id`, `role`,
  `tool_description`, OAuth URLs, `serve_entrypoint`); `artifacts/ttl.yaml` (28:
  `declared_ttl_seconds`, `max_ttl_seconds`, `ttl_anchor_basis`); and
  `SpreadScenario` (`deployment.py:549-591`) restating the five section keys as
  properties.
- **SDK API:** `src/ccf/deployment/config.py::load_config_and_boot`,
  `_RESERVED_SECTIONS` (`:184-202`, private), `DeploymentConfig`, `parse_artifact`.
- **Duplicated authority:** the 30-day window (`ttl.yaml:26-27` twice, the gate
  closure, `door.yaml:33` prose, `ccf_config.yaml:57-66` prose); principal and role
  (`door.yaml:42-43` vs `ccf_config.yaml:410-411`, admitted at `door.yaml:39-41`);
  `schema_name`/`schema_version` (config, `deployment.request()`, the door's
  wrong-address check); the five section keys (`SpreadScenario`).
- **Failure modes:** an unknown top-level key is refused at derivation (good);
  `per_run`, `serve_entrypoint`, `ttl_anchor_basis` and the `peer_set` λ_c row
  (CP03C-F-04) are read by nothing — *config nobody reads is documentation, not
  control*; nothing links `ttl_anchor: from_entity_freshness` to `decay_basis`, so a
  tree that forgets the basis reads F = 1 on years-old data and the reading looks
  healthy (CP03C-F-08; eight other trees declare the anchor with no basis);
  `door.yaml` is validated only by the developer's own `REQUIRED` tuple
  (`serve.py:109-112`).
- **Classification:** the sections are **domain-specific**; `sources:` and the
  door's identity are **deployment-specific**; the document set, the key mapping and
  the cross-document consistency checks are **SDK mechanism** that the developer
  performs by hand today.

### P2 · Boot

- **Adopter writes:** `produce.py:93-105` — `ControlPlaneRegistry()`,
  `load_config_and_boot(HERE / "ccf_config.yaml", registry=…, connection=deployment.connection(root=root))`,
  `try/finally booted.handle.close()` (`:215`); `deployment.connection()`
  (`deployment.py:111-127`) re-parses `backends.yaml` and mints
  `root / f"{prefix}_{uuid4().hex}{suffix}"` per call.
- **SDK API:** `load_config_and_boot(connection: Mapping)`, `BootedFabric`,
  `manifest.py::_preflight_adapter`.
- **Duplicated authority:** the substrate prefix/suffix declared in `backends.yaml`
  and composed in code; `per_run: path` declared and honored only by the
  developer's uuid.
- **Failure modes:** a shared root is a shared fabric — a door answering several
  questions under one root served the first obligor's spread for a third LEI that
  resolved to nothing, with a matching content address and nothing raised
  (CP03C-F-02); cp-04-canonical, cp-06 and cp-07 compose a **fixed** path
  (`cp-04-canonical/deployment.py:88-97`, `cp-06:83-87`, `cp-07:65-68`) and cp-06's
  door reuses one root for every question; a missing assembly root surfaces as an
  MCP transport error that reads like a producer that never booted (CP07-F-08).
- **Classification:** **SDK mechanism.**

### P3 · Effective-request resolution

- **Adopter writes:** `deployment.py:207-245` `effective_parameters()` —
  `ProductRequestContract.from_declared`, a `ProvenanceSource` over
  `content_hash(declared)`, `ReferencePolicyConstraintResolver(...).resolve(...)` with
  ten keyword arguments, built with `entitlement_key=None` (`:231`) and
  `capabilities=()` (`:239`); `acquire_for()` (`:248-265`) short-circuits on
  `outcome.refusal`.
- **SDK API:** `ReferencePolicyConstraintResolver`, `resolve_effective_request`;
  the resolver's own derivation is inline in `GovernedResolver.__call__`
  (`resolver.py:1813` `refuse_intent`, `:1845` `constraint_resolver.resolve`,
  `:1917` effective request), built with `product_entitlement_key(tenant)`
  (`:3460`) and `_capabilities_of(fabric)` (`:3479`). **No preview or dry-run method
  exists** (grep `def effective|preview|resolve_effective|dry_run` in
  `resolver.py`: none).
- **Duplicated authority:** the derivation itself — seven example trees
  (`cp-03-canonical`, `cp-04-canonical`, frozen `cp-04/assembler.py`, `cp-05`,
  `cp-06`, `cp-07`, `cp-08`) with seven refusal sentinels (`None` / `0` / `{}` /
  raise / return-object).
- **Failure modes:** equality with the governed path holds by coincidence of inputs,
  not by construction; acquisition at raw values scores `D_c` over rows the payload
  never served (CP04C-F-02); a drifted copy lets a refused request acquire;
  the docstring's claim of sameness (`deployment.py:213-218`) is not checked
  anywhere.
- **Classification:** **SDK mechanism.**

### P4 · Source acquisition

- **Adopter writes:** `acquisition.py` (442 lines; imports no `ccf` symbol by
  design): the SELECTs over the estate, the ratio grammar, the peer cohort, the
  jurisdictions grant expansion; plus the env-var + remedy reader (`:108-131`).
- **SDK API:** none on the query path (correct); `sources:` in `backends.yaml` is
  read by no SDK code.
- **Duplicated authority:** env-var names in `backends.yaml` and in
  `acquisition.py`.
- **Failure modes:** a missing variable produces the developer's remedy text (good);
  a v1 namespace is silent (CLAUDE.md §9's namespace trap).
- **Classification:** the queries and vocabulary are **domain**; connection material
  is **deployment**; resolving declared source names to values is **SDK mechanism**.

### P5 · Fabric ingestion

- **Adopter writes:** `deployment.py:273-410` `_instant`/`_amount`/`_envelope`/
  `envelopes()` — per-class attribute mapping, `observed_time` from the filing (the
  claim's `valid_from`), `ingestion_timestamp=at` (the request instant), tenant
  restated; `ingest()` (`:413-426`) loops over `booted.handle.worker.ingest`.
- **SDK API:** `SignalEnvelope`, L2's `AssemblyWorker.ingest`, `resolution.entity_rules`.
- **Duplicated authority:** the ingest loop in every tree; `tenant_id` restated on
  each envelope.
- **Failure modes:** F = 1 for years-old columns unless every scored row declares
  `decay_basis: valid-from` **and** the envelope carries `observed_time` — nothing on
  the public surface states that `observed_at` is the ingestion instant
  (CP03C-F-08); last-claim-wins erasure ordered only by the developer's loop
  (cp-04-canonical, `D-IMPL-316`); a foreign-tenant or future-stamped envelope is
  accepted.
- **Classification:** the temporal mapping is **domain**; the loop and the
  tenant/instant boundary check are **SDK mechanism**.

### P6 · Projection

- **Adopter writes:** `projection.py` (148) and the named `plan_factory`
  (`produce.py:136-147`) — `FinancialSpreadProjection(plan_id, required, subject)`,
  subject-scoped after F-02.
- **SDK API:** `resolver.py::ProjectionPlanFactoryProtocol`,
  `ProjectionPlan`, the operator classes.
- **Duplicated authority:** the `plan_id` literal.
- **Failure modes:** an unscoped Π serves another subject's claims (F-02's second
  half); a `lambda` factory reads as `D-IMPL-137` row C.
- **Classification:** **domain** — unchanged by this design (`D-IMPL-141` A.2).

### P7 · Debt assessment

- **Adopter writes:** `deployment.debt()` (`:434-489`, including the empty-view
  F = 0 branch) and a closure in `produce.py:149-159` capturing `asked_at` and the
  booted `half_life`/`debt_profile` artifacts.
- **SDK API:** `FreshnessScorer`, `Observation(valid_from=)`, `DebtAssessment`,
  `DebtFactors`, `HalfLifeEntry.decay_basis` (`D-IMPL-331`),
  `resolver.py::AssemblyDebtScorerProtocol`,
  `ChildAwareDebtScorerProtocol` (`:544`).
- **Duplicated authority:** the artifact keys (restated through `SpreadScenario`);
  the decision instant captured by closure rather than handed by the resolver.
- **Failure modes:** the reference scorer refuses an empty view, so every tree
  re-writes a fallback; a closure over `asked_at` ignores
  `decision_instant_parameter` (the two-clock rule CP-14 depends on,
  `DECISIONS.md:3829`).
- **Classification:** the rule is **domain**; handing it the instant, the booted
  bindings and (for composites) the admitted children is **SDK mechanism**.

### P8 · Governed serve and refuse

- **Adopter writes:** `produce.py:161-202` — `FileArtifactStore(root/"artifact-store")`,
  the fifteen-keyword `build_governed_resolver(...)` call (five keys, store, two
  replay class literals, two TTL ints, `plan_factory`, `debt_scorer`,
  `product_gate=deployment.freshness_window_gate(ttl_seconds=…)`),
  `resolve(tenant=, product_class=, version=, request=, perspective=)`, the
  `isinstance(outcome, RefusalEnvelope)` branch, record readback (`:204-206`).
- **SDK API:** `resolver.py::build_governed_resolver`, `GovernedResolver`,
  `ServedProduct` / `RefusalEnvelope`, the declared product gate (`D-IMPL-282`
  R-11, both-or-neither).
- **Duplicated authority:** `max_ttl_seconds`/`product_ttl_seconds` restated from
  `ttl.yaml`; the replay classes as literals; the same call in fifteen trees
  (§4).
- **Failure modes:** a gate declared without a predicate is refused (good); an
  address the resolver was never wired for is an exception, i.e. a broken
  deployment (`resolver.py:355-361`); a wrong key is silent until the first request.
- **Classification:** **SDK mechanism** — the developer legitimately supplies only
  the factory, the scorer and the gate predicate.

### P9 · Replay

- **Adopter writes:** the record class literal twice (`produce.py:187`,
  `serve.py:107`), a hand-rooted store (`produce.py:162` `root/artifact-store` vs
  `serve.py:277-282` `root/replay`), two `ReplayRefusalRecorder`s in the door
  (`serve.py:182-193`, `:305-311`), record readback by
  `DecisionReplayRecord.model_validate_json(store.get(...))`.
- **SDK API:** `ReplayBinding` (`replay:` section; `artifacts.py:599`,
  `_RESERVED_SECTIONS["replay"]`) — **exists and is unused by this tree** (no
  `replay:` in its config); the resolver builds its own recorder
  (`resolver.py:3494-3510`) and exposes it as `refusal_recorder` (`:1586`);
  `recorded_boundary` checks only structural conformance.
- **Duplicated authority:** record class 2× (3× in cp-05); two stores per door
  process; three recorders per door process.
- **Failure modes:** served and refused decisions filed under two classes in two
  stores; nothing compares the door's recorder to the spine's; the door cannot reach
  the resolver's recorder because the resolver is built per question inside
  `assemble_and_serve` and never returned.
- **Classification:** the binding is **deployment configuration** (`R-12`); the
  recorder, the store and the readback are **SDK mechanism**.

### P10 · Runtime door

- **Adopter writes:** `server/serve.py` (243 code lines): `door_values`, `_typed`,
  `_wrong_address`, `build_resolver`, `Door`, a second `ControlPlaneRegistry`, a
  hand-built `ProductEntitlementPolicy`, `tokens.json`, `FileTokenSource`,
  `resolve_perspective`, the thirteen-keyword `build_egress_server` call, the stdio
  identity block (`auth_context_var.set`), the socket/uvicorn/anyio loopback.
- **SDK API:** `build_egress_server` (`egress.py:778`), `ProductEntitlementPolicy`,
  `ControlPlaneProductEntitlementSource`, `SourceBackedTokenVerifier`,
  `AuthSettings`, `ReplayRefusalRecorder`, `auth_context_var`.
- **Duplicated authority:** everything in P3, P9, P11 and P12 restated; the
  ~106-line door body in six example trees and three test fixtures, differing by
  seven comment lines between cp-06 and cp-07.
- **Failure modes:** a stale `ProductRequestViolation` constructor leaves the door
  as `ccf-runtime-failure:<id>` (CP03C-F-07: pydantic's `ValueError` is caught at
  `egress.py:1254` into `_opaque_failure`); cp-06's door never compares class or
  lane and answers a wrong address with its own product; a door that prints makes
  two printers (spine-separation P6); stdio auth pre-set on HTTP admits every
  caller; an uncreated assembly root fails as transport.
- **Classification:** **SDK mechanism**; the deployment supplies identity and a
  credential source.

### P11 · Producer identity

- **Adopter writes:** `door.yaml producer_id`; `serve.py:318-319`
  `producer_id=door.producer_id, producer_tenant=tenant`; the principal/role pair in
  `door.yaml` copied from `default_perspective`.
- **SDK API:** `build_egress_server(producer_id, producer_tenant)` (`egress.py:790-791`,
  both-or-neither at `:942`), `ProducerAssertion`, `DoorOutcome`.
- **Duplicated authority:** `producer_tenant` vs `tenant_id`; principal/role vs
  `default_perspective`. The D-IMPL-340 as-built record calls the producer pair
  "free deployment values … deriving it would make the door reach into the
  resolver" (`docs/D-IMPL-340-DESIGN.md:687-691`).
- **Failure modes:** principal drift makes `serve.py:225` route every caller as an
  override principal, changing the recorded perspective without the grant expansion
  the in-process path performs (`deployment.py:173-176`); a wrong tenant is refused
  at every consumer (by design, never an admission).
- **Classification:** `producer_id` is a **deployment value**; the assertion is
  **SDK mechanism**; the principal pair has **one** legitimate home
  (`default_perspective`) and the door restates it.

### P12 · Remote request handling

- **Adopter writes:** `serve.py:128-144` `_typed` (int/bool/Decimal coercion),
  `:147-165` `_wrong_address` (a hand-built `ProductRequestViolation` with the
  current seven fields), `:211-219` a rebuilt `ProductRequest`, `:225` the principal
  mapping, the `refused` closure.
- **SDK API:** `ProductRequestViolation` (`request.py:1503-1568`; reasons
  `:232-242`), `envelope_for`/`RequestIdentity`, the egress handler passing
  parameters verbatim (`egress.py:1174-1200`), `WireRequest` decode
  (`D-IMPL-302`, `DECODED_DECLARED_TYPE = "number"`).
- **Duplicated authority:** the door re-types what the SDK decodes and adds
  coercions the SDK refuses (a float for `debt_tolerance`); a second request
  constructor with different grant semantics from `deployment.request()`.
- **Failure modes:** one correct wrong-address site, one broken (cp-05, plus a
  second unnamed site `_no_standing_answer` at `cp-05/server/serve.py:217-223` with
  the same stale shape), four absent; intent is judged only at the resolver.
- **Classification:** **SDK mechanism.**

**Line attribution (this document's cut, measured):** domain ≈ 775 (acquisition 429,
projection 148, deployment's vocabulary/envelopes/debt/gate/grant ≈ 190, the named
factory 8); plumbing ≈ 497 (acquisition's env reader 13, deployment's
config/ttl/connection/request/perspective/effective/acquire_for/ingest/`SpreadScenario`
≈ 150, `produce.py` 91, `server/serve.py` 243); presentation 93 (`run.py`). The
ruling's ≈ 680 / ≈ 700 figure counted `run.py` and the request/perspective
constructors as plumbing. Under either cut the plumbing-to-domain ratio is between
0.65 and 1.0, and — as Dave ruled — the composition, not the count, is the finding.

---

## 2 · Current consumer workflow — ten steps, measured on the one governed consumer

Subject: `tests/examples/test_cp_03_canonical_cross_deployment.py` (419 code lines),
the only consumer of a governed `mcp_product` child on `main`. **No example tree
contains consumer wiring:** no `examples/*/ccf_config.yaml` declares `producers:` or
`requires:`; `SkillCatalog(`, `GrantLedger(` and `SkillGrant(` appear in no example;
`register_declared_producer` is called from `src/ccf/skills/producers.py` and three
test modules only.

### C1 · Requires declaration
- **Adopter writes:** three lines under `product_class.requires` (`test:139-144`):
  `product_class`, `required`, `compatible_from`.
- **SDK API:** `ChildRequirement` (`contract.py:781-799`), `accepts` (same-major floor).
- **Duplicated authority:** the floor (`1.0.0`) and the lane asked (`1.1.0`) live in
  two authorities (C3).
- **Failure modes:** silence on `required` is refused; a required row carrying
  `absence_treatment` is refused; both at derivation (good).
- **Classification:** **domain** — unchanged (`D-IMPL-340` ruling 7).

### C2 · Producer registration
- **Adopter writes:** the `ccf.mcp-producer` document (`test:199-212`, 14 lines;
  `producer_id` read off the producer's `door.yaml`, `producer_tenant` off its
  `ccf_config.yaml`, `test:85-88`); `SyncMcpBridge` + `McpSkillRegistry`
  (`:131-134`, `:307-308`); a bearer `httpx` client factory (`:178-196`, 19 lines);
  `register_declared_producer(...)` (`:309-315`).
- **SDK API:** `MCP_PRODUCER`/`parse_artifact`, `register_declared_producer`
  (`producers.py:75-115`), `McpSkillRegistry`, `SyncMcpBridge`; the `producers:`
  section derives and validates one artifact per label (`config.py:739-756`) and
  **registers nothing** (`DECISIONS.md:3859` residual 3).
- **Duplicated authority:** `SERVER_NAME` in the registration and the binding;
  `producer_id`/`producer_tenant` copied from the producer's documents by hand.
- **Failure modes:** `credential_factory=None` requires the credential variable to be
  set **and empty** (`producers.py:93-97`); an unregistered server or an unoffered
  class is an exception at dispatch, not a governed refusal.
- **Classification:** the values are **deployment**; registering is **SDK mechanism**
  the consumer restates because the section is unwired.

### C3 · Catalog and skill declaration
- **Adopter writes:** one `SkillCatalogEntry(skill_type="mcp_product", ...)` per child
  (`test:248-262`, 15 lines): `description`, empty `SkillArgumentSchema`,
  `McpProductBinding(server, product_class, product_version)`, empty
  `SkillRequirements`, `produces`.
- **SDK API:** `SkillCatalog.register` (returns `str | RegistrationRefusal`,
  `catalog.py:699-712`), `McpProductBinding`, the `produces == binding.product_class`
  validator.
- **Duplicated authority:** `PRODUCT_VERSION` in the binding, the registration and
  `consumes`; the class in `produces` and the binding.
- **Failure modes:** a name held by a producer is refused; `artifact_version` must
  be semver (`catalog.py:630-633`); every value except `description` is determined
  by the registration plus the requirement — yet `D-IMPL-56` and `D-IMPL-29` ruled
  that the **entry** declares `description`, `argument_schema` and `requirements`
  (`R-7`).
- **Classification:** **SDK mechanism** by derivability; **ruled declared** by
  `D-IMPL-56`/`D-IMPL-29` — the conflict is put to Dave, not assumed away.

### C4 · Grant
- **Adopter writes:** a policy-bundle regime with
  `skill_governance: {grant_requires_approval: false, permitted_scopes: []}`
  (`test:220-235`, 16); an `AgentDefinition` built in Python (`:236-247`) with
  `archetypes=("context_assembly",)`, five `consumes` rows, a `halflife_debt_profile`
  ref to an artifact **never registered** (decorative — `grants.py:663-664` resolves
  the regime only); `GrantLedger(...)` (`:263`); `SkillGrant` with seven fields and
  `ledger.request(..., definition=, actor=)` (`:264-277`); a `_LEDGERS` cache keyed by
  `id(registry)` (`:117`, `:218-219`, `:278`).
- **SDK API:** `GrantLedger.request`, `SkillGrant`, `AgentDefinition`
  (`definitions.py:282`, `_TwoLaneVersioned`), `content_hash`.
- **Duplicated authority:** `REGIME_KEY` (`test:98` and `:244`); the definition's
  `consumes` restating the `requires` rows.
- **Failure modes:** a grant is single-use per `(definition, registry)` — the second
  `ledger.request` raises `GrantTransitionError` (the cache hides it); the hash on
  the grant must be of the exact definition; a wrong `consumes` fires the
  context-contract check at grant, not at boot.
- **Classification:** the composing agent and its regime are **deployment**
  Control Plane artifacts (CLAUDE.md §6.4: data, not code); the ledger, hash binding
  and grant request are **SDK mechanism**.

### C5 · Argument and question mapping
- **Adopter writes:** `questions_at` (`test:282-299`, 18 lines): subject = the LEI,
  intent `annual-review`, freshness `filing-cadence`, `debt_tolerance` as decimal
  text.
- **SDK API:** `ChildQuestion` (`child_resolver.py:142-156`), `ChildQuestions =
  Callable[[ChildRequirement, ProductRequest], ChildQuestion]` (`:165`).
- **Duplicated authority:** the `freshness` token `filing-cadence` has no declared
  home (`deployment.py:136`, the spec, the test).
- **Failure modes:** a wrong mapping is refused at serve, never at boot; only the
  spread judges intent — the other four CP-14 children declare no `discovery`, so a
  nonsense intent passes unjudged (`request.py:2057-2058`).
- **Classification:** **domain** — the one genuinely product-specific consumer
  artifact.

### C6 · Dispatch
- **Adopter writes:** `QuestionBoundChildResolver(ledger, agent_definition_hash,
  gate, child_questions, callable_registry=CallableRegistry(), artifact_store,
  mcp_skills=registry)` (`test:317-325`) and `GovernedResolver(**arguments,
  composite_children=, admission_clock=)` where `arguments` is
  `tests/products/test_resolver_seam.py:2106-2181` — a **test fixture** restating
  ≈ 20 keywords including the recorder's store/class/bundle pin.
- **SDK API:** `QuestionBoundChildResolver` (`child_resolver.py::QuestionBoundChildResolver`), the
  composite keywords on `GovernedResolver`.
- **Duplicated authority:** the parent's keywords; a second clock.
- **Failure modes:** a non-`mcp_product` grant without `child_arguments` is
  `unsupported-outcome`; an empty `CallableRegistry` is still required.
- **Classification:** **SDK mechanism.**

### C7 · Admission
- **Adopter writes:** one constructor line, `CompositeAdmissionGate(tenant_id,
  consumer_scope, registry)` (`test:319`).
- **SDK API:** `CompositeAdmissionGate.hold_producer_claims` (`composite.py:1229`;
  checks 1p/1p′/1q/1q′/1r then 2–7).
- **Duplicated authority:** none.
- **Failure modes:** `producer-unasserted` for a pre-340 door (cp-05, cp-06);
  `producer-mismatch`; `as-of-mismatch` unless the composite's `asked_at` equals
  cp-05's pinned instant (CP14-F-19).
- **Classification:** **SDK mechanism.**

### C8 · Child-contract consumption
- **Adopter writes:** `build_with_children` on the plan factory
  (`tests/products/composite_fixture.py` `_ChildReadingFactory`).
- **SDK API:** `resolver.py::CompositePlanFactoryProtocol`,
  `ChildContractView`.
- **Duplicated authority:** none. **Failure modes:** a factory that ignores the
  children composes blind. **Classification:** **domain.**

### C9 · Composition
- **Adopter writes:** nothing.
- **SDK API:** `GovernedResolver.__call__`'s composite path (`resolver.py:1965-2069`):
  per-factor debt minimum (`D-IMPL-31`/`D-IMPL-104`), lineage set-union, expiry
  floor, mixing refusal.
- **Duplicated authority:** none.
- **Failure modes:** a refused required child yields a composite refusal that names
  the child but carries no reason and no child replay reference (CP03C-F-05,
  `D-IMPL-342`); the expiry floor inherits a decision-anchored child expiry that
  overstates validity (CP03C-F-01, `D-IMPL-341`).
- **Classification:** **SDK mechanism** — unchanged by this design.

### C10 · Replay (consumer side)
- **Adopter writes:** ≈ 20 lines of readback helpers (`test:349-367`): the record by
  address, the child row, the retained child; `child_replay_ref` is a producer URI
  the consumer cannot resolve (`:430-434`).
- **SDK API:** `DecisionReplayRecord.content_generation_path.child_resolutions`
  (`record.py:910-1008`), `FileArtifactStore.get`/`resolve_uri`; re-execution via
  `replay()` reaches the private `_operator_parameters`
  (`tests/crossproc/test_d_impl_340_cross_deployment.py:495`).
- **Duplicated authority:** two read idioms.
- **Failure modes:** none governed; the private reach is the gap.
- **Classification:** reading is **SDK mechanism**; re-execution stays
  **advanced-optional**.

**Consumer totals (measured):** ≈ 106 wiring lines around 18 of mapping for one
child in the test (the ruling's 106:18), plus ≈ 75 restated parent keywords, 19 for
the bearer factory and ≈ 20 for readback — **≈ 219 non-domain lines per child, in
Python, from fixtures the SDK does not ship.**

---

## 3 · Responsibility classification — by who owns the decision

| # | Responsibility | Owner of the decision today | Legitimate owner | Class |
|---|---|---|---|---|
| P1 | Product declaration (class, contract, operators, resolution, λ_c, debt profile, policy, perspective) | developer, correctly | developer | **DOMAIN** |
| P1′ | Document set, section-key mapping, cross-document consistency (principal pair, TTL, class/lane) | developer, by hand | SDK | **SDK MECHANISM** |
| P1″ | Source connection material, door credential, substrate location | developer (`backends.yaml`, `door.yaml`) | deployment | **DEPLOYMENT** |
| P2 | Boot, per-question substrate, handle lifecycle | developer | SDK | **SDK MECHANISM** |
| P2′ | Naming the dev substrate (prefix/suffix values) | developer (`backends.yaml`) | deployment (values); the SDK mints, never names a backend in `src/` (cinv04) | **DEPLOYMENT** |
| P2″ | A long-lived, pre-populated or non-SQLite L3 (per-process lifecycle: hw1, `tests/crossproc/servers/mcp_product_producer.py:208-283`) | developer, by hand | deployment, on the low road in v0 (§6 hatch 5; `R-3` names the consequence) | **ADVANCED-OPTIONAL** |
| P3 | Effective-request derivation | developer re-runs the resolver | SDK, once | **SDK MECHANISM** |
| P4 | Source acquisition (queries, vocabulary) | developer | developer | **DOMAIN** |
| P4′ | Resolving declared source names to values | developer | SDK | **SDK MECHANISM** |
| P5 | Envelope temporal semantics (`observed_time`, class mapping) | developer | developer | **DOMAIN** |
| P5′ | Ingest loop; tenant/instant boundary refusal | developer | SDK | **SDK MECHANISM** |
| P6 | Projection Π and the named factory | developer | developer | **DOMAIN** |
| P7 | Debt rule (F, C, S) | developer | developer | **DOMAIN** |
| P7′ | Handing the scorer the decision instant, the booted bindings, the admitted children | developer (closure) | SDK | **SDK MECHANISM** |
| P8 | Gate predicate | developer | developer | **DOMAIN** |
| P8′ | Resolver composition, serve/refuse, record readback | developer | SDK | **SDK MECHANISM** |
| P9 | Replay binding (classes, store dirname) | developer, as literals | deployment (`replay:`) | **DEPLOYMENT** |
| P9′ | One store, one recorder, the readback | developer | SDK | **SDK MECHANISM** |
| P10 | The standard door | developer | SDK | **SDK MECHANISM** |
| P10′ | A custom transport, IdP, resource exposure, HTTP hosting | developer | deployment, on the low road | **ADVANCED-OPTIONAL** |
| P11 | `producer_id` | developer (`door.yaml`) | deployment | **DEPLOYMENT** |
| P11′ | `producer_tenant`; the principal pair | developer (copied) | one authority: `tenant_id` / `default_perspective` (`R-6`) | **SDK MECHANISM** |
| P11″ | Expanding a verified non-default principal's `jurisdictions` grant onto a door request (`serve.py:225` + `_typed` never expands; in-process `deployment.py:173-176` does) | nobody — unowned today | the door serves the declared principal only in v0; a second principal is `entitlement_source=` on the low road, and the expansion is the deployment's `acquire` reading `context.request.perspective` | **ADVANCED-OPTIONAL** |
| P12 | Wire-to-typed translation, wrong-address verdict | developer | SDK (verbatim parameters, `D-IMPL-302`; one `class-mismatch` site) | **SDK MECHANISM** |
| C1 | `requires:` rows | developer | developer | **DOMAIN** |
| C2 | Producer registration values | developer | deployment (`producers:`) | **DEPLOYMENT** |
| C2′ | Registering, bridge, credential resolution | developer | SDK | **SDK MECHANISM** |
| C3 | Catalog entry | developer | SDK by derivability; **the entry** by `D-IMPL-56`/`29` (`R-7`) | **SDK MECHANISM (ruling pending)** |
| C4 | The composing agent definition and its regime | developer, in Python | deployment (a declared artifact; `R-2`) | **DEPLOYMENT** |
| C4′ | Ledger, hash binding, grant issuance | developer | SDK | **SDK MECHANISM** |
| C5 | Question mapping | developer | developer | **DOMAIN** |
| C6–C7 | Dispatch and admission | developer (fixtures) | SDK | **SDK MECHANISM** |
| C8 | Child-contract consumption | developer | developer | **DOMAIN** |
| C9 | Composition | SDK | SDK | **SDK MECHANISM** |
| C10 | Replay readback | developer | SDK | **SDK MECHANISM** |
| C10′ | Consumer-side re-execution | developer (private reach) | advanced | **ADVANCED-OPTIONAL** |
| — | Clocks (three injected in the consumer test; one wall clock in the door) | developer | SDK: one `clock` per open; the entitlement audit's wall clock stays separate by ruling (`serve.py:270-272`) | **SDK MECHANISM** |

---

## 4 · Duplication census — per pattern, with defect weight

Copies are rosters, not counts; "drifted" means two copies now differ in a way that
changes behavior; "defect weight" names the finding a copy has already caused.

| pattern | copies (roster) | structurally identical? | drifted? | consequence of drift | SDK can own centrally? | defect weight |
|---|---|---|---|---|---|---|
| Effective-request re-derivation (`ReferencePolicyConstraintResolver(` / `resolve_effective_request(`) | 7 trees: cp-03c `deployment.py:207-245`; cp-04c `:159-213`; frozen cp-04 `assembler.py:296`; cp-05 `:391`; cp-06 `:133-160`; cp-07 `:117-123`; cp-08 `:160-166` | same call, ten keywords; **seven refusal sentinels** | YES — cp-03c builds with `entitlement_key=None`, `capabilities=()`; the SDK's own uses the tenant key and the fabric's capabilities | acquisition at values governance never resolved; `D_c` scored over rows never served | YES — `R-4` | CP04C-F-02 |
| The builder spine (`replay_record_class=`, `query_pin_class=`, `max_ttl_seconds=`, `product_ttl_seconds=` literals) | 15 trees / 19 files: `produce.py` in cp-03c, cp-04c, cp-06, cp-07, cp-08, cp-09, cp-10, cp-11, cp-12, cp-13, s1-00; doors in cp-03c, cp-05, cp-06, cp-07; frozen cp-04 `deployment.py`; s1-01 `deployment.py` + `spine.py`; hw1 `compose.py` | copyable but for three names (the ruling's own words) | cp-05 states the class three times; s1-00/s1-01/hw1 read it from a document | a record class stated twice files served and refused decisions under two classes | YES — `replay:` exists (`R-12`); `ttl:` proposed (`R-3`) | none yet; latent everywhere |
| The door body (`door_values`, entitlement policy, token source, recorders, `build_egress_server`, stdio block, loopback) | 6 example doors (cp-03c 243, cp-05 199, cp-07 151, cp-06 150, frozen cp-04 114, hw1 108 code lines) + 3 test fixtures (`tests/crossproc/servers/mcp_product_producer.py`, `tests/client/fixtures/stdio_server.py`, `tests/crossproc/servers/mcp_experience_child.py`) | the ≈ 106-line body is copied; cp-06/cp-07 differ by 7 comment lines | YES — cp-05's `ProductRequestViolation(parameter=…)` no longer matches the contract; cp-06 never compares class/lane; hw1 reuses the resolver's recorder where the canonical trees build two | an opaque `ccf-runtime-failure` where a governed refusal is owed; a wrong address answered | YES — `open_door` (§5.4) | **CP03C-F-07**, CP07-F-08, CP07-F-09 |
| Hand-built wrong-address refusal | cp-03c `serve.py:147-165` (correct); cp-05 `:206-211` and `:217-223` (both stale); cp-06, cp-07, frozen cp-04, hw1: absent | no | YES (two of three sites) | see above | YES — one emission site in `src/` (§5.4; `R-9`) | CP03C-F-07 |
| Principal + role restated beside `default_perspective` | cp-03c `door.yaml:42-43`; cp-05 `door.yaml:35-36`; cp-06 `:41-42`; cp-07 `:45-46`; hw1 `binding.yaml:50-52` (third copy); counter-examples: frozen cp-04 `egress-door.yaml:21-25` and hw1 `egress-door.yaml:20-23` refuse to restate | yes | not yet; **compared by nothing** | `serve.py:225` silently routes callers as override principals with un-expanded grants | YES — `door:` carries no principal keys (§5.2) | latent, behavioral |
| Per-question substrate minting | cp-03c `deployment.py:111-127` (uuid); **fixed path** in cp-04c `:88-97`, cp-06 `:83-87`, cp-07 `:65-68`; cp-06's door reuses one root (`serve.py:133, :212`) | no — one correct, three latent | YES | one obligor's spread served for another with a matching content address and nothing raised | YES — `answer()` mints per question (§5.3) | **CP03C-F-02** (latent in three siblings) |
| `decay_basis` omitted under `ttl_anchor: from_entity_freshness` | eight trees declare the anchor with no basis: cp-04c, cp-06, cp-01, cp-02, cp-08, cp-00, frozen cp-04, frozen cp-03 | n/a (an absence) | n/a | F = 1 on a run-populated fabric; the reading looks healthy | YES — a derivation-time refusal, or the scorer refusing `observed_at == ingestion instant` under `observed-at` (backlog B-05) | **CP03C-F-08** |
| The producer spine (`assemble_and_serve`: boot / acquire / build / resolve / readback / `Assembled`) | cp-03c 99, cp-04c ≈ 96, cp-06 ≈ 88 code lines; cp-05's 549-line variant | identical lines: `try/finally close`, `FileArtifactStore(root/…)`, the four literals, `resolve(tenant=booted.tenant_id, …)`, the `D-IMPL-137` paragraph | cp-05 raises `RequestRefused` where the others return the envelope | a deployment exception replaces a governed determination | YES — `open_product` (§5.3) | none |
| `SpreadScenario`-shaped section-key restatement | cp-03c `deployment.py:549-591`; cp-04c `:417-434`; cp-06 `:381-397`; cp-05 `produce.py:439-448` (literals) | yes | no | a renamed section is silent until the first request | YES — `BootedFabric.keys` (§5.3) | none |
| `semver: "1.0.0"` in code for the perspective/request documents | cp-03c `deployment.py:198`; cp-04c `:129, :403`; cp-06 `:91, :356-357`; cp-07 `:72, :374-376`; cp-05 `rc.get("semver", "1.0.0")` | yes | no | none today | YES — read the booted artifact | none |
| Consumer: policy-bundle regime + `AgentDefinition` + `SkillCatalogEntry` + `SkillGrant` | 6 / 7 / 7 / 8 copies across `tests/` (duplication census tables c); `SkillGrant(` and `GrantLedger(` in 14 test files each; **0 in `examples/`** | all-constant fields | no | a copier learns nothing from the decorative `halflife_debt_profile` ref; the `_LEDGERS` cache is re-invented in three files | YES for issuance and the catalog (§5.5); the agent is a declared artifact (`R-2`); the entry's declared halves are `R-7` | none yet |
| The `--8<-- [start:boot/acquire/govern]` region markers | ten `produce.py` files | publication surface only; read by no test or tool | n/a | none | keep (spine-separation reads them) | none |

**Weighting, as ruled:** the three patterns that have already caused a correctness
defect — the door body (F-07), the substrate mint (F-02), the decay basis (F-08) —
plus the effective-request copy (CP04C-F-02) are the ones the paved road must make
**impossible by construction** rather than merely shorter; §11 criterion 4 and §12
carry one sabotage each.

---

## 5 · Proposed paved-road API — one coherent surface over the ruled mechanisms

**Principle (the amendment's own words):** `D-IMPL-336`–`D-IMPL-340` remain the
mechanisms and contracts; the paved road is a facade that orchestrates them. Every
object below is an EXISTING type, an EXISTING call, or a new *seam* that the low
road may also use on its own. There is no second resolver, door, registry, ledger
or gate.

### 5.1 · The two documents

`ccf_config.yaml` — Control Plane content, hashed, every existing section unchanged:

```yaml
tenant_id: cp-03-canonical-demo
semver: "1.0.0"
product_class: { schema_name: credit-risk.spread, schema_version: "1.1.0", ttl_anchor: from_entity_freshness,
                 declared_product_gate: {...}, discovery: {...}, requires: [...],
                 decision_instant_parameter: as_of }      # NEW optional field (composites; R-3b)
operators: ...        request_contract: ...        resolution: ...
half_life: ...        debt_profile: ...            policy: ...        default_perspective: ...
replay:               # EXISTING ccf.replay-binding (R-12); REQUIRED on the paved road
  record_class: ccf.replay-record
  query_pin_class: ccf.graph-query
  store_dirname: artifact-store
ttl:                  # NEW reserved section -> ccf.ttl-binding (R-3a)
  max_ttl_seconds: 7776000
  product_ttl_seconds: 2592000
door:                 # NEW reserved section -> ccf.egress-door (R-9, R-10 for the URL boundary)
  producer_id: cp-03-canonical-obligor-financial-spread-egress
  tool_description: |
    ...
  issuer_url: https://issuer.cp-03-canonical.example
  resource_server_url: https://door.cp-03-canonical.example
  required_scope: ccf.product.read
producers:            # EXISTING ccf.mcp-producer, one per label (D-IMPL-340) — consumers only
  spread: { server: canonical-spread-producer, producer_id: ..., producer_tenant: ...,
            endpoint_from_env: CCF_CP14_SPREAD_URL, credential_from_env: CCF_CP14_SPREAD_TOKEN,
            offers: [{product_class: credit-risk.spread, versions_from: "1.1.0"}] }   # lane reading: R-13
```

The composing agent (consumers only) is a `ccf.agent-definition` document. **It
cannot be an `agent:` reserved section on today's typed derivation path** — see
`R-2` for the two buildable shapes; whichever Dave rules, the adopter writes the
six axes once and never a Python `AgentDefinition(...)`.

`ccf_environment.yaml` — deployment environment, unhashed, replaces `backends.yaml`,
`server/door.yaml`'s credential half and `artifacts/ttl.yaml` (`R-10` for the name):

```yaml
config: ccf_config.yaml
substrate: { prefix: cp03c_spread, suffix: .sqlite3 }     # VALUES the SDK joins onto `scratch`; src/ names no backend (cinv04)
sources:
  financial_spread:
    dsn:    { from_env: CCF_CP_03C_DSN,    remedy: "export the ccf_v2 read-only DSN" }
    schema: { from_env: CCF_CP_03C_SCHEMA, remedy: "the v2 schema name (ccf_v2), not .env's v1" }
door:   { credential_from_env: CCF_CP_03C_DOOR_TOKEN }
remote: { call_timeout_seconds: 120 }                      # consumers
```

`load_environment_document` refuses by name any key that belongs to the Control
Plane (`principal_id`, `role`, `product_ttl_seconds`, `record_class`, a literal URL
or token — the `D-IMPL-340` ruling-10 posture), so the two documents cannot restate
each other. `substrate.lifecycle` is **not** a key: v0 has exactly one lifecycle,
and a key with one legal value is documentation, not control (`R-3` names the
per-process consequence).

### 5.2 · The producer surface

```python
from ccf.products.product import open_product, OpenedProduct, AcquisitionContext, AssessmentContext

opened = open_product(
    config_root=HERE,                    # read-only: ccf_config.yaml + ccf_environment.yaml
    scratch=Path(scratch),               # writable: substrate files and the replay store; refused inside config_root
    acquire=deployment.acquire,          # AcquireProtocol   (AcquisitionContext) -> Iterable[SignalEnvelope]   DOMAIN
    project=plan_factory,                # ProjectionPlanFactoryProtocol | CompositePlanFactoryProtocol, NAMED   DOMAIN
    assess=deployment.assess,            # AssessProtocol    (AssessmentContext) -> DebtAssessment   DOMAIN, required in v0 (R-3c)
    gate=deployment.freshness_window_gate,   # ProductGateProtocol | None — both-or-neither with declared_product_gate (R-11)
    questions=None,                      # ChildQuestions — REQUIRED iff product_class.requires is non-empty   DOMAIN
    clock=_utc_now,
    # closed pass-throughs, every one an EXISTING type (§6):
    control_plane=None, artifact_store=None, constraint_resolver=None, capabilities=None,
    approval_sink=None, children=None, child_arguments=None,
)
with opened:
    request = opened.question(subject="…", asked_at=…, intent="annual-review", freshness="filing-cadence",
                              parameters={"debt_tolerance": Decimal("1.0")})   # ProductRequest, contract-validated; no intent in parameters (D-IMPL-264 D-01)
    outcome = opened.answer(request, perspective=None)   # ServedProduct | RefusalEnvelope — never an exception for a governed "no"
    record = opened.record_of(outcome)                   # DecisionReplayRecord from the ONE store, by the outcome's replay_ref
```

`OpenedProduct` exposes, read-only: `tenant_id`, `declaration`, `keys`
(`DeploymentKeys`), `ttl`, `replay`, `door`, `default_perspective`,
`control_plane`, `artifact_store`, `refusal_recorder`, `mcp_skills`, and two seams
for the low road: `build_arguments(fabric) -> Mapping` (the exact keyword mapping
`answer()` hands `build_governed_resolver`) and `resolve(...)` (conforms to
`ProductResolverProtocol`, so a door can hold it).

**Contexts** (new, small, frozen):

- `AcquisitionContext(request: ProductRequest /* effective */, tenant_id, sources:
  Mapping[str, Mapping[str, str]], instant: datetime)` — `instant` is the question's
  `asked_at`, exposed so an SDK L1 adapter used inside `acquire` can be constructed
  with `clock=lambda: context.instant` (the adapters stamp `ingestion_timestamp` from
  a clock: `signal/acquisition.py:235`, `signal/mcp_source.py:172`).
- `AssessmentContext(view, evidence, decided_at, half_life, profile, children:
  ChildContractView | None)`.

**Protocols** (new, structural): `AcquireProtocol`, `AssessProtocol`, and a
companion scorer Protocol `InstantAwareDebtScorerProtocol.score_at(view, evidence,
decided_at, children)` on the `D-IMPL-339` precedent, so the decision instant and
the admitted children reach a deployment's scorer without the facade re-deriving
`_decision_instant`'s rule (`R-3c`). Adopting it needs one hoist in `__call__`:
today `assessed` is computed at `resolver.py:2137-2143` and `decided_at` bound after
it at `:2150`; the hoist is inside the body whose regression check is "every shipped
canonical content address unchanged", and the seam test gains a
`decided_at`-before-scoring assertion.

### 5.3 · What `answer()` does, per question, and which mechanism does it

1. **Boot.** Mint `scratch / f"{prefix}_{uuid4().hex}{suffix}"` from the
   environment's `substrate:` values and call the EXISTING
   `load_config_and_boot(config_path, registry=self.control_plane,
   connection={"database_path": …})` — the same mapping `deployment.connection()`
   hands today, minted by the facade so CP03C-F-02 cannot recur. One
   `ControlPlaneRegistry` per open; per-question re-registration of identical
   content is idempotent on every path (`registry.py:321-323` for `register`,
   `:404-405` for `register_versioned`; `register_typed` appends only when the
   version is new) — measured, not assumed — **but every outcome is audited
   (`:412-413`), so one audit row per section per question is the cost (§9 (c)).**
   The facade never names a backend: `substrate.prefix/suffix` are opaque values,
   and backend selection remains whatever `_preflight_adapter` does today, so
   `tools/lints/substrate_names.py` (cinv04) is satisfied by construction.
2. **Resolve the effective request once.** This is `R-4`. Recommended shape (a):
   `build_governed_resolver(..., acquisition=self._acquisition_seam)` — the resolver
   runs `refuse_intent` and `constraint_resolver.resolve` exactly as today
   (`resolver.py:1813-1917`), then hands the **effective** request to the seam
   before it builds the view. The seam is the facade's closure: it calls the
   deployment's `acquire(AcquisitionContext(...))`, runs `refuse_foreign_envelope`
   (tenant mismatch or `ingestion_timestamp != asked_at`, refused by name — the
   as-of boundary must not precede a claim's observation, CP03C-F-08), and ingests
   through `fabric.handle.worker.ingest` — **L2 writes; the resolver holds no
   writer and hands no envelope to it** (`resolver.py:1337-1345` stays true; the
   facade is the producer-side composition root, the role every `produce.py` and
   hw1's `compose.py` play today). A refused request acquires nothing because the
   seam is reached only after resolution succeeds. Shape (b) — a
   `GovernedResolver.effective_request` preview — is the fallback and doubles the
   audited reads (`constraints.py:1344`, `:1698`); §14 `R-4` puts the choice to Dave.
3. **Build the resolver** via the EXISTING `build_governed_resolver(**self.build_arguments(fabric))`:
   keys from `fabric.keys` (new `DeploymentKeys`, the section→key mapping the
   `SpreadScenario`s restate); `max_ttl_seconds`/`product_ttl_seconds` from the
   `ttl:` binding, with the two builder keywords relaxed to optional and held
   **equal** to the binding when both are given (`R-3a`, the `D-IMPL-292` equality
   shape); `artifact_store` and the two classes from `replay:` (`R-12`, unchanged
   precedence); **one** recorder — `declared_refusal_recorder(fabric, replay,
   store)` passed through a NEW `refusal_recorder=` keyword on the builder (today it
   constructs its own at `resolver.py:3494-3510`, so the door cannot share it);
   `plan_factory=project`; `debt_scorer=` an adapter over `assess`; `product_gate=gate`;
   `decision_instant_parameter` from the declaration (`R-3b`); `capabilities`,
   `constraint_resolver`, `approval_sink` pass-throughs; and for a composite the
   derived children (§5.5).
4. **Serve.** `resolver(request, perspective=perspective or default_perspective)`;
   the governed outcome is returned as data; the resolver's own recorder records
   every governed refusal; the fabric handle is closed in `finally`.

### 5.4 · The standard door

```python
from ccf_runtime.mcp.product_door import open_door, ProductDoor, ServesProducts

door = open_door(opened, perspective_resolver=None, token_verifier=None, entitlement_source=None)
door.serve_stdio()                      # the stdio identity block, once, in the runtime
door.serve_loopback(announce=callback)  # the socket/uvicorn body, once; the port goes to the caller, never to stdout
door.server                             # the unstarted FastMCP — mount it under your own host
```

`open_door` is typed over a **structural Protocol** `ServesProducts` (`tenant_id`,
`declaration`, `default_perspective`, `control_plane`, `refusal_recorder`, the
`door` binding, and a `resolve` conforming to `ProductResolverProtocol`), not over
`OpenedProduct`, so a hand-composed hw1-shaped deployment reaches the standard door
with the pieces it already holds. Inside, `open_door` derives from EXISTING calls
only: refuses when `door` is `None`; registers `ProductEntitlementPolicy(tenant,
policy_version=declaration.schema_version, principals={default.principal_id:
Grant({schema_name}, {default.role})})` under `product_entitlement_key(tenant)`
into the product's ONE registry (the hw1 `compose.py:115-131` shape);
`ControlPlaneProductEntitlementSource(clock=wall)` (the audit clock stays wall time by
ruling); `SourceBackedTokenVerifier(StaticTokenSource(grants={credential:
TokenGrant(client_id=principal_id, scopes=(scope,))}))` — `StaticTokenSource` is
new, ≈ 10 lines, `hmac.compare_digest` as `FileTokenSource`; a perspective resolver
returning `Perspective(principal_id=grant.client_id, role=default.role)`; and
`build_egress_server(server_name=tenant, resolver=opened, token_verifier=…,
auth_settings=AuthSettings(issuer_url, resource_server_url, required_scopes=[scope]),
entitlement_source=…, perspective_resolver=…, refusal_recorder=opened.refusal_recorder,
expose_product_resource=False, expose_product_tool=True,
product_tool_description=door.tool_description, producer_id=door.producer_id,
producer_tenant=<R-6>)`.

**Remote request handling on the road** (`OpenedProduct.resolve`): parameters cross
the door **verbatim** (`egress.py:1174-1200`; `D-IMPL-264` D-04, `D-IMPL-302`) —
there is no `_typed` (`R-8` records the behavior change for the canonical tree);
the wrong-address verdict is one site in `src/` built against the current
`ProductRequestViolation` contract. **Its reach, verified:** `_answer_question` runs
`govern_entitlement` (`egress.py:1201`) before the resolver (`:1226`), and the derived
policy permits exactly `{schema_name}`, so a **wrong class** is denied by
entitlement at the door and a **wrong lane** reaches `resolve()` and is refused
`class-mismatch` at `key="schema_version"` with a record — `R-9` records that this
is the "bad question" reading of `D-IMPL-253` Q15 rather than the resolver
docstring's "broken deployment" reading (`resolver.py:355-361`).

### 5.5 · The consumer surface — the same object, three more declarations

A class whose declaration has `requires` opens only if `questions=` is supplied and
the composing agent is declared (`R-2`); `open_product` then derives, refusing by
name at open when inconsistent, from EXISTING mechanisms:

- **Producer registration** (C2): for every `producers.<label>` in the booted
  artifacts, `register_declared_producer(registry, artifact=, environ=os.environ,
  bridge=SyncMcpBridge(call_timeout_seconds=remote.call_timeout_seconds),
  credential_factory=bearer_client_factory)` — one bridge, one
  `McpSkillRegistry(audit_log=control_plane.audit_log)` per open, exposed as
  `opened.mcp_skills`. **Registration happens whether or not the composite chain is
  derived**, so the `children=` hatch shares the registry the SDK populated (the
  refuter's cliff, repaired). `bearer_client_factory` is a new ≈ 6-line seam in
  `ccf.mcp.client`.
- **Catalog** (C3): one `mcp_product` entry per `(requirement × the one offering
  producer)`; two offers for one class refuse at open (`R-12′` records the
  narrowing of `D-IMPL-340` ruling 7: registration-level, with the grant-level
  ambiguity rule reachable only through `children=`). `artifact_version` is the
  registration document's own `semver` (`config.py:747` sets it from
  `config.semver`), never a content hash — `SkillCatalogEntry.artifact_version` is
  semver-validated (`catalog.py:630-633`). `description`, `argument_schema` and
  `requirements` are `R-7`: the design does **not** decide them in `src/`.
- **Grant** (C4): one `SkillGrant(agent_definition_hash=content_hash(agent), …)`
  per entry through `GrantLedger.request` with the derived regime
  (`policy.skill_governance`, `policy.key`); issuance is **idempotent** by looking up
  an existing effective grant for `(agent_definition_hash, skill_name)` through the
  ledger's bound view before requesting, so a second open over a shared registry
  does not raise `GrantTransitionError`/`GrantCollisionError` (`grants.py:771-782`,
  `:1057-1060`); `approval_sink=` is the `D-IMPL-29` tier-2 hatch. The SDK **checks**
  `agent.context_contract.consumes ⊇ requires` and refuses a disagreement — a
  checked cross-reference, the `declared_product_gate` posture, not a second
  authority (`R-2` asks Dave to confirm the check).
- **Dispatch and admission** (C6, C7): `QuestionBoundChildResolver(ledger, hash,
  gate=CompositeAdmissionGate(tenant_id, consumer_scope=<derived>, registry),
  child_questions=questions, callable_registry=CallableRegistry(), artifact_store,
  mcp_skills=opened.mcp_skills, child_arguments=child_arguments)`, handed to the
  builder as `composite_children=` with `admission_clock=clock`.
- **Question mapping** (C5): the adopter's `questions` callable, unchanged in type.
- **Composition and replay** (C9, C10): unchanged; `record_of` reads the row.

### 5.6 · Mapping onto D-IMPL-336…340

| paved-road element | mechanism it orchestrates | new or existing |
|---|---|---|
| `requires:`, `ChildRequirement.accepts`, `CompositePlanFactoryProtocol`, `ChildContractView`, the composite path | `D-IMPL-336` | existing, untouched |
| the guarded types the facade returns (`ServedProduct`, `RefusalEnvelope`, `DecisionReplayRecord`) | `D-IMPL-337` — the facade asserts no new guarded authority; no new guarded type | existing |
| composite Gate 1 refusals, admission checks 1p–7, `ChildResolution` rows | `D-IMPL-338`/`D-IMPL-340` | existing |
| `InstantAwareDebtScorerProtocol` | the `D-IMPL-339` structural-companion precedent | new Protocol |
| `producers:` → `register_declared_producer`, `McpProductBinding`, `DoorOutcome`/`ProducerAssertion`, `producer-unasserted` | `D-IMPL-340` | existing, now wired |
| `open_product`, `OpenedProduct`, contexts, `open_door`, `ServesProducts`, `DeploymentKeys`, `TtlBinding`, `EgressDoorBinding`, `load_environment_document`, `refuse_foreign_envelope`, `bearer_client_factory`, `StaticTokenSource`, `declared_refusal_recorder`, `refusal_recorder=` and `acquisition=` on the builder | the facade and its seams | new |

---

## 6 · Escape hatches retained — one mechanism plus a facade, never two architectures

Every hatch is the EXISTING low-level surface, selected by writing a call, never by
a flag the facade inspects.

1. **The governed resolver itself.** `build_governed_resolver` and
   `GovernedResolver(...)` remain the canonical low road (`D-IMPL-301`: ownership
   "established by the program"). `opened.build_arguments(fabric)` returns the exact
   mapping `answer()` uses; a deployment copies it, edits one entry, calls the
   builder. The per-question fabric a low-road caller hands in comes from the same
   `load_config_and_boot(connection=)` call the facade makes — nothing is hidden.
2. **Closed pass-throughs on `open_product`,** each an existing type: `control_plane`
   (a shared registry; grant issuance is idempotent so a second open is safe),
   `artifact_store` (an `McpArtifactStore`, §7.4 — wins under `R-12` and becomes the
   recorder's store, so the two cannot split; a declared `store_dirname` beside
   `artifact_store=` is refused by name, so no key is declared that nothing reads),
   `constraint_resolver`, `capabilities` (cp-04-canonical's `traversal_capability()`),
   `approval_sink`, `children` (a hand-built `QuestionBoundChildResolver` /
   `GrantBoundChildResolver` for two producers per class, peering, or a same-fabric
   child), `child_arguments`. `children=` is refused **only together with the
   composing-agent declaration**, never with `producers:` — the registrations stay
   declared and pinned.
3. **Custom doors and transports.** `build_egress_server` with `opened.resolve` and
   `opened.refusal_recorder` (the hw1 shape) gives any verifier, IdP, entitlement
   source, resource exposure or hosting; `open_door`'s three typed overrides cover
   the common partial departures; `ProductDoor.server` mounts under your own host.
   The HTTP door (`ccf_runtime.http_api`) and the in-process client
   (`ccf.client`, `binding.yaml`) are untouched.
4. **Custom policy and constraints.** `policy_constraints:` and the entitlement leg
   are unchanged; pass your own `PolicyConstraintResolver` through hatch 2.
5. **Long-lived fabrics and non-SQLite L3.** v0's paved road boots per question on
   the dev backend. A CDC-fed, Postgres/Fluree/Neo4j or pre-populated fabric
   composes the hw1 way — `load_config_and_boot` once plus `build_governed_resolver`
   — **and still reaches the standard door**, because `open_door` takes the
   structural `ServesProducts`, and it may use the seams individually
   (`DeploymentKeys`, the `ttl:`/`replay:` fallbacks, `declared_refusal_recorder`,
   `StaticTokenSource`, `bearer_client_factory`, the `acquisition=` seam with its
   own ingestion). What it does not get is `open_product`'s lifecycle; `R-3`
   states this plainly and backlog B-09 carries the per-process lifecycle.
6. **Specialized acquisition.** `acquire` returns `Iterable[SignalEnvelope]` from
   anything — `FileRecordAcquisitionSource`, `MCPSourceAdapter`, any
   `SignalSourceProtocol` — constructed per question with
   `clock=lambda: context.instant`; the boundary checks only tenant and instant.
   Proven through the public surface by a paved test that drives
   `FileRecordAcquisitionSource` through `acquire` (§12).
7. **Custom stores and replay infrastructure.** `artifact_store=` selects any
   `ArtifactStoreProtocol`; `replay()` and `CompositeReplayEnvironment` are untouched
   and remain the advanced path.
8. **Documents.** The multi-file manifest form (`load_and_boot`) is the `D-IMPL-136`
   amendment's documented hatch; `binding.yaml` and `REFERENCE_KEYS` are untouched.

**Deliberately not a knob** (leaving it is a visible step, not a flag):
`replay_record_class=`/`query_pin_class=`/`max_ttl_seconds=`/`product_ttl_seconds=`
as arguments on the road (`D-IMPL-292`: no argument for a declared value); a
principal/role override for the door; a wire-coercion hook (`D-IMPL-302`); a
per-child producer preference (`D-IMPL-340` ruling 7); a resource-exposing door; a
`per-process` lifecycle; the reference-scorer path (its declared C/S have no
Control Plane home — backlog B-03).

---

## 7 · cp-03-canonical before / after target — measured before, estimated after

The re-expression is NOT performed here. Preserved unchanged: domain behavior, the
calculations, `projection.py`, the debt rule, the class and lane
(`credit-risk.spread@1.1.0`), serve/refuse outcomes, replay dimensions 1/3/4/5,
cross-process behavior, and frozen cp-03 (untouched). The **content address of the
demonstration spread at the CP-14 instant must be byte-identical** — that is the
success signal.

| measure | before (measured, HEAD) | after (target, estimate) |
|---|---|---|
| code lines (produce / deployment / projection / acquisition / run / server) | 99 / 341 / 148 / 442 / 93 / 243 = **1366** | ≈ 20 / ≈ 215 / 148 / ≈ 429 / ≈ 85 / ≈ 8 = **≈ 905** |
| domain code | ≈ 775 | ≈ 795 (+ 12 lines of glue: `acquire`/`assess` adapters; − 13: the env reader) — unchanged in substance |
| plumbing code | ≈ 497 | **≈ 35–45** |
| presentation (`run.py`) | 93 | ≈ 85 |
| Python files authored | 6 | 6 (`server/serve.py` becomes an ≈ 8-line launcher) |
| documents | 4 (411 / 65 / 54 / 28) | 2 (`ccf_config.yaml` ≈ 440; `ccf_environment.yaml` ≈ 22) |
| SDK-mechanism names imported | 30 (`produce.py` + `deployment.py` + `serve.py`) | ≈ 11 |
| duplicated authorities (a value stated in > 1 place) | 6 (replay class; principal+role; TTL; class/lane; five section keys; producer tenant) | **0 in documents; 1 residual in code** — the gate's window, see below |
| effective-request derivations | 2, with two postures | 1 (`R-4` (a)); 1 function called twice (`R-4` (b)) |
| Control Plane registries per door process | 2 | 1 |
| artifact stores per door process | 2 | 1 |
| refusal recorders per door process | 3 | 1 |
| custom door code | 243 | ≈ 8 |
| custom effective-request code | 39 (`effective_parameters`) + 18 (`acquire_for`) | 0 |
| consumer integration (one child; `test_cp_03_canonical_cross_deployment.py`) | ≈ 219 non-domain lines in Python | 1 keyword (`questions=`) + ≈ 10 YAML lines per child + ≈ 25 YAML lines once |
| failure modes reachable by writing the accepted documents | F-02, F-07, F-08 shape, principal drift, replay split, ungoverned derivation | none of the six (§11 criterion 4; §12) |
| replay record | five dimensions | 1/3/4/5 byte-identical; dimension 2 a superset by exactly the `replay`, `ttl`, `door` pins (to be **measured**, §11 criterion 7) |
| cross-process (OFC-G16..G22) | green through today's door | green through `open_door`, with two stated behavior changes (§9) |

**Per file:** `produce.py` → the named `plan_factory` (8 lines, stays in this module
because gate-two condition 3 scans the factory's own module), `product(scratch)` and
`assemble_and_serve` (≈ 12 lines); gone: the registry, boot, `acquire_for`/`ingest`,
the scorer closure, `SpreadScenario`, the store, the fifteen-keyword call, the
`isinstance` branch, the readback, `try/finally`, `Assembled`.
`deployment.py` keeps the vocabulary constants, `envelopes()`, `debt()`'s body,
`NO_OBLIGOR` + `freshness_window_gate`, the `jurisdictions` grant helper; adds
`acquire(context)` (≈ 8) and `assess(context)` (≈ 3); **deletes, not relocates**
(`D-IMPL-289`): `config()`, `ttl()`, `connection()`, `request()`'s schema reads,
`perspective()`, `effective_parameters()`, `acquire_for()`, `ingest()`,
`SpreadScenario`. `acquisition.py` loses the env reader and takes `settings` from the
context. `server/serve.py` → `serve()` and `loopback(announce)` over `open_door`.
`run.py` → `opened.question(...)`/`opened.answer(...)`; `--door` unchanged in shape.

**The one residual restatement, finalized.** The gate today closes over
`ttl_seconds` restated from `ttl.yaml`. On the road the predicate reads **no
configuration**: the `candidate` it already receives carries `expires_at` and
`temporal_boundary` (fields of `contract.py::ContextProductContract`), and for a class without a
decision-instant parameter `expires_at − temporal_boundary` IS the declared window
(`resolver.py:2245-2249`). So the window is read once, from the served contract —
not re-parsed in `produce.py`, not bound in a second step. Recorded beside it: the
gate exists only because `expires_at` is decision-anchored (CP03C-F-01); when
`D-IMPL-341` lands, the serving half is deleted, not moved.

**Test bodies that change (classified under `D-IMPL-261` as "the SDK surface it
legitimately consumes was deliberately changed"; node ids and
`artifacts/gates.yaml`'s 27 ids unchanged, so `tools/check_product_gates.py` is
untouched):** in `tests/examples/test_cp_03_canonical_output.py`, the `served`
fixture (`:121-123`) and every test that calls `deployment.request`,
`deployment.connection`, `deployment.ttl()`, `deployment.config()` or
`produce.assemble_and_serve` — `:296-313` (OFC-G07/G08 window reads), `:326-336`,
`:372-403`, `:414-435`, `:584-612` (OFC-G24, re-expressed over `opened.answer` under
one `scratch`, asserting per-question minting through the public surface) — move to
`opened.question`/`opened.answer`/`opened.record_of`; **OFC-G13 (`:508-518`) asserts
`"canonical"` and a `build_governed_resolver` call and is red by construction on a
paved tree** — it is re-authored to assert `"paved"` and the paved-entry ownership
(`R-1`); OFC-G14 (`:525`) keeps reading `produce.py` for a `FunctionDef` named
`plan_factory` and passes unchanged. In
`test_cp_03_canonical_cross_deployment.py`, OFC-G23's in-process leg (`:587-590`)
moves to `opened.answer`. "Same ids, same count" is true; "tests unchanged" is not,
and this document does not claim it.

**Behavior changes the dogfood must MEASURE, not assume:** (a) parameters cross the
door verbatim — a hand-typed `"periods": "8"` is refused `type-mismatch` where
`_typed` coerced (the SDK consumer sends JSON numbers and decimal text, so OFC-G16/G23
are unaffected); (b) one registry per product makes the door's entitlement policy
visible to every per-question resolver: resolver refusals through the door now
**disclose under the policy** (`resolver.py:886-900`) and `_entitlement` performs an
audited read on every override attempt (`constraints.py:1698`) — the content address
is unaffected (lineage reads operators, policy version and snapshot; no contract
field reads the entitlement key), but OFC-G16..G22's refusal transcripts and the
audit log differ; (c) per-question boot into one registry writes one audit row per
section per question; (d) dimension 2 gains three pins; (e) a second `open_door` on
one product with a different `default_perspective` content must be refused at open
by name, not at the first override by `ConstraintEffectivityConflict`.

---

## 8 · CP-14 consumer target — requirement, configuration, mapping; no new subsystem

The five children per `spec/CP-SPEC-014` §B.7 (`e955df40`, rows `:646-650`), as
they stand on `main` and what CP-14 writes on the paved road. **The premise that
both canonical siblings carry doors is false on `main`:** cp-04-canonical has no
`server/` directory and no `--door`.

| # | `requires` row / floor | producer today | door today | what CP-14 writes | owed first, elsewhere |
|---|---|---|---|---|---|
| 1 | `credit-risk.spread` / `1.0.0` | cp-03-canonical @ `1.1.0`, tenant `cp-03-canonical-demo` | 340-conforming (`serve.py:294-319`) — acquirable (OFC-G16, G23) | `requires` row; `producers.spread` (7 lines, lane `1.1.0` per `R-13`); `consumes` row; branch: `subject=request.subject`, `intent="annual-review"`, `freshness="filing-cadence"`, `parameters={"debt_tolerance": <decimal text>}`; 2 env vars | nothing (the producer's own re-expression is dogfood A, not a prerequisite) |
| 2 | `reference.corporate-family` / `2.0.0` | cp-04-canonical @ `2.0.0`, tenant `cp-04-canonical-demo` | **none** | row; `producers.family`; `consumes`; branch with the tree's `credit-concentration`/`standard`, `families=[lei]`, `max_depth` | a door: on the paved road ≈ 17 lines of `door:`/`ttl:`/`replay:` + an 8-line `server.py`, once that tree is re-expressed (its own rung; `capabilities=(traversal_capability(),)` passes through) |
| 3 | `credit-risk.exposure-rollup` / `1.0.0` | cp-05 (frozen) @ `1.0.0`, tenant `cp-05-demo`, pinned instant `2026-09-07T12:00:00+00:00` | pre-340: no producer identity; forwards neither `asked_at` nor `freshness` (`serve.py:182-192`) — refused `producer-unasserted` | row; `producers.exposure`; `consumes`; branch with the composite's `asked_at` held at the pin (CP14-F-19), tolerance ≥ `1.0` | a 340-conforming door on a frozen specimen — its own ruling (`D-IMPL-261`) |
| 4 | `credit-risk.collateral-coverage` / `1.0.0` | cp-06 (frozen) @ `1.0.0`, tenant `cp-06-demo` | pre-340 (`serve.py:210-235`) — `producer-unasserted` | row; `producers.collateral`; `consumes`; branch: `subject=str(request.parameters["facility_id"])` + `borrower_scope` (CP14-F-20: explicit facility grain, no implicit fan-out); **CP-14's own request contract must first declare `facility_id`** (spec §B.2 `:464-473` has no such row; §0.9 records "at the next revision") — a memo parameter not on CP-14's contract cannot reach a child | same as row 3 |
| 5 | `credit-risk.covenant-cross-reference` / `1.0.0` | cp-13 (frozen) @ `1.0.0`, tenant `cp-13-crossref-demo` | **none** | row; `producers.covenant`; `consumes`; branch: anchor URI set or `scope` from the memo's request, `corpus_scope` mapped from CP-14's own | a door on a frozen specimen — its own ruling |

**Once, for the whole composite:** the composing-agent document (six axes, five
`consumes` rows; `R-2`); `policy.key` in the `{tenant}/policy-bundle/{name}` form and
`policy.skill_governance` (3 lines); `product_class.decision_instant_parameter:
as_of` (CP14-F-25 — the request contract must declare `as_of`, checked at
derivation); `replay:`, `ttl:`, `door:` (≈ 17; CP-14 is itself consumable);
`ccf_environment.yaml` with `substrate` and `remote.call_timeout_seconds`; and one
`open_product(..., project=MemoPlanFactory(), assess=deployment.assess,
questions=questions)`. **The composite factory — the class carrying
`build_with_children` — is defined in the module that calls `open_product`
(CP-14's `produce.py`)**, because gate-two condition 3
(`test_gate_two_call_shape.py:3084-3120`) scans the factory's own module for the
entrypoint; the projection plan class itself may live in `projection.py`.

**Consumer non-domain total (estimate):** 1 keyword + ≈ 25 YAML lines once + ≈ 10
YAML lines per child ≈ 75 lines of declaration and **0 lines of Python** beyond the
mapping, the plan, the scorer, the gate and §B.8 acquisition. Today's ≈ 425 (five
children by analogy with the measured test) become ≈ 75; the ratio inverts from
≈ 6:1 plumbing:mapping to ≈ 1.5:1 declaration:mapping. Per additional child: +1
`requires` row, +7 `producers` lines, +1 `consumes` row, +≈ 8 mapping lines, +2
environment variables, no new Python object.

**Two clocks** (`DECISIONS.md:3829`): `decision_instant_parameter: as_of` moves
`decided_at` (TTL anchor, gate instant, `AssessmentContext.decided_at`);
`temporal_boundary` stays `request.asked_at`, held at cp-05's pin; admission check 4
is unaffected.

**Inherited unchanged, consumer-visible:** CP03C-F-01 (the spread's `expires_at` is
decision-anchored; the composite's floor is not filing-anchored; masked today by
cp-05's four-hour TTL) and CP03C-F-05 (a producer's refusal arrives as `ineligible`
with no reason) — `D-IMPL-341`/`342`, ruled not developer-experience work. **What
this design cannot give CP-14:** rows 2–5 have no 340-conforming door; that is
producer-side rung work (`DECISIONS.md:3824`), never a CP-14 workaround, and no
supported path reaches four of five slots today whatever the road looks like.
**CP-14 Gate 2 stays HOLD** until the paved road is implemented, separately
approved and merged, and dogfood A and B are green (§10).

---

## 9 · Compatibility impact — nothing existing breaks; every change named

**APIs.** *Wrapped, unchanged in signature:* `load_config_and_boot`,
`GovernedResolver`, `build_egress_server`, `register_declared_producer`,
`SkillCatalog`, `GrantLedger`, `QuestionBoundChildResolver`,
`CompositeAdmissionGate`, `ReplayBinding`, `FileArtifactStore`. *Unchanged and
untouched:* `binding.yaml`, `REFERENCE_KEYS`, `ccf.client.adapters.*`, hw1, the HTTP
door, `replay()`, `CompositeReplayEnvironment`, every frozen specimen. *Additive:*
`build_governed_resolver` relaxes `max_ttl_seconds`/`product_ttl_seconds` to
optional (equality-checked against `ttl:` when both given) and gains
`refusal_recorder=` and `acquisition=` (`R-4` (a)); `BootedFabric.keys` defaulted
`None` (the manifest form sets nothing — its runtime callers to be read at
implementation); three hash-transparent optional `DeploymentConfig` fields (`ttl`,
`door`, and the agent document reference per `R-2`) on the `replay` precedent
(`artifacts.py:2189-2191`, held by
`tests/contracts/test_hash_transparency.py::test_a_config_naming_no_replay_binding_hashes_as_it_did`);
one hash-transparent optional field on `ProductClassDeclaration`
(`decision_instant_parameter`, the `requires` precedent at `artifacts.py:1507`);
`InstantAwareDebtScorerProtocol` is a structural companion no existing scorer
implements, so no existing branch changes; new modules only otherwise.

**Configuration.** `_RESERVED_SECTIONS` gains `ttl` and `door` (`R-9`/`R-10`);
`SDK_ARTIFACT_CLASSES` gains `ccf.ttl-binding` and `ccf.egress-door`
(`tests/deployment/test_config_derivation.py:122-132` requires it); the composing
agent follows `R-2`; `producers:` gains no field unless `R-13` rules `lane`; no
committed `ccf_config.yaml` uses `ttl:` or `door:` as a key (unknown keys were
already refused, so none could).

**Hash and content address.** Every committed config's content address and pin is
unchanged (hash-transparent fields); the demonstration spread's content address is
the dogfood's identity check; lineage does not read the entitlement key, so one
registry per product does not move it.

**Replay.** Dimension 2 gains the `replay`, `ttl`, `door` pins on a paved tree —
an expected superset, to be measured; dimensions 1/3/4/5 unchanged.

**Control Plane.** One registry per open; audit volume rises by one row per section
per question (measured cost, §5.3); no new artifact class is registered outside the
two bindings and the agent per `R-2`.

**Examples.** Fifteen shipped trees keep calling the builder with their literals and
keep their doors; only cp-03-canonical is re-expressed, in place, as dogfood A
(`R-11` records that `D-IMPL-313/314/315`'s shape clauses and
`D-GATE-cp-03-canonical`'s roster confirmation are superseded for that one tree by
`D-IMPL-343`'s dogfood instruction).

**Third-party adapters.** `HarnessAdapterProtocol`, `ArtifactStoreProtocol`,
`SignalSourceProtocol`, `PolicyConstraintResolver`, `ProductResolverProtocol` are
unchanged; a third-party artifact store or constraint resolver enters through hatch 2.

**No silent low-level semantic change.** The explicit ones, all stated in §7 and
`R-8`: verbatim wire parameters on the re-expressed door; the door's policy visible
to the per-question resolver; the one-hoist in `__call__` (`decided_at` before the
scorer) with the shipped canonical content addresses as the regression check.

**Tests and gates that must move with the surface, in the same change:**
- `tests/examples/test_spine_separation.py`: a fourth shape `"paved"` and a fifth
  named refusal `"double-spined"` (`R-1`). **`PAVED_PATH_MARKERS` keeps `boot` as its
  first marker** (`("boot", "product", "answer")`): `region_modules` (`:310-318`)
  finds carriers by intersection with the seven legacy names, and `boot` is the
  shared name that keeps P1/P2 and `spine_problems` working on a paved tree — the
  design's `product()` IS the boot. `expected_markers` returns per shape;
  `CANONICAL_SHAPE_FLOOR = 1` unchanged (cp-04-canonical and cp-06 remain
  canonical); a `PAVED_SHAPE_FLOOR = 1` lands after dogfood A. **A synthetic
  paved-tree positive control** (a copied tree rewritten to the paved shape under
  `tmp_path`, asserted `"paved"` and problem-free) ships in the SDK phase beside
  the double-spined negative, so the predicate has a witness before the dogfood
  (memory: gate the thing the phase is for). The print gate is unchanged.
- `tests/products/test_gate_two_call_shape.py`: `CANONICAL_RESOLVER_ENTRYPOINTS`
  gains `open_product`; the named factory stays in the calling module;
  `RULED_SDK_SUPPLIED_DEPLOYMENTS` already names cp-03-canonical and keeps it only
  because condition 3 shape B is widened (`R-1`); `MINIMUM_PROJECTING_BODIES = 14`
  is not lowered.
- `tests/products/test_resolver_defaults.py::test_the_named_inputs_are_this_helper_s_own_optional_parameters`
  enumerates the two TTL keywords, `refusal_recorder` and `acquisition` explicitly (a
  scoped denominator, not a widened one).
- `tests/deployment/test_config_derivation.py` and `test_class_lookup.py`: the two
  new typed classes; the agent per `R-2`.
- `docs/schemas/*.json` regenerate (`make schemas`); a
  `docs/surface-changes/343-01-<slug>.md` fragment (**digit-first**; `r01`/`r10`
  already fell into the invisible-fragment hole) and the surface capture.
- Lints: `src/ccf/products/product.py` imports `ccf.*` only; it authors no prose
  (`R-7` decides the entry's `description`; the facade emits no sentence);
  `runtime/ccf_runtime/mcp/product_door.py` imports `mcp`, `uvicorn` (already pinned,
  `pyproject.toml:33`) and `anyio` (transitive via `mcp`; pin it explicitly);
  `substrate_names.py` (cinv04) is satisfied because `src/` names no backend
  (§5.3 step 1); a new invariant test that no `src/` module other than the facade
  and `ccf.assembly`/`ccf.boot` reaches `handle.worker` — the writer lint
  (`harness_imports.py:145-168`) guards imports only, so the composition-root role
  needs its own control.

---

## 10 · Migration strategy — no flag day; incremental; the lower level stays valid

1. **Rulings logged first** — `R-1`…`R-13` (§14), each a `D-IMPL` entry, none an
   edit; then Dave's implementation GO. Nothing below starts before it.
2. **SDK phase on `d-impl-343-paved-road` off `main`,** each step landing with its
   proof and its sabotage together: (a) contracts — `TtlBinding`,
   `EgressDoorBinding`, the `DeploymentConfig` fields,
   `ProductClassDeclaration.decision_instant_parameter`, the reserved sections and
   class tables, derivation-time refusals, schemas; (b) `DeploymentKeys` /
   `BootedFabric.keys`; (c) the builder relaxation, `refusal_recorder=`,
   `declared_refusal_recorder`, `InstantAwareDebtScorerProtocol` with the hoist —
   regression: every shipped canonical content address unchanged; (d) the
   `acquisition=` seam (`R-4` (a)) or the preview (`R-4` (b)); (e)
   `load_environment_document` and the `references.py` move (`looks_like_a_reference`
   re-exported under its name); (f) `ccf.products.product` producer half; (g)
   `refuse_foreign_envelope`, `bearer_client_factory`, `StaticTokenSource`; (h)
   `product_door.py` over `ServesProducts`; (i) the consumer half; (j) the two gate
   widenings, the `"double-spined"` refusal, the synthetic paved positive control,
   the `examples/` AST controls (`ReferencePolicyConstraintResolver(`,
   `ProductRequestViolation(` in a paved tree); (k) cross-AI panel over the shipped
   code (inline the source, brief the known findings, ask for what is adjacent),
   every finding verified against the tree, blocking fixed in phase, present, `D-GATE`.
3. **Dogfood A — cp-03-canonical re-expressed IN PLACE** on its own branch after
   step 2 merges (it is the canonical successor, not a frozen specimen). Acceptance,
   measured: the demonstration content address at the CP-14 instant byte-identical
   (OFC-G23); dimensions 1/3/4/5 byte-identical and dimension 2 a superset by
   exactly three pins; OFC-G01..G27 green by the same node ids with the test-body
   changes of §7 classified; the cross-deployment proof green through `open_door`
   with the SAME `consumer()` in the test (the producer half is proven before the
   consumer half is dogfooded); `shape_of == "paved"`; §7's table filled with
   measured numbers; every miss classified (SDK gap / example wrong / estate) rather
   than fixed downward (`D-IMPL-261`, `D-IMPL-313` carry 3).
4. **Dogfood B — the cross-deployment test's `consumer()` re-expressed as an
   `open_product` with `producers:`, the agent document and `questions=`**, same
   proof set. Only then **CP-14 Gate 2 resumes** as the consumer-side dogfood.
5. **Everything else converts only when next rebuilt for its own reasons.** The
   doors CP-14 needs on rows 2–5 are separate rung work; frozen trees need their
   own rulings; no bulk migration (`D-IMPL-136` amendment (5)).
6. **In no step:** `D-IMPL-341`, `D-IMPL-342`, any CP-14 artifact.

---

## 11 · Success criteria — measurements with positive controls, defined before code

1. **Producer non-domain code + config** to turn `acquire + project + assess` into a
   governed, remotely consumable product: ≤ 45 Python lines that are neither domain
   vocabulary nor a call the adopter must make (Appendix A's counter over
   `produce.py` + `server/serve.py` + the glue in `deployment.py`); exactly two
   documents; `ccf_environment.yaml` ≤ 30 lines. Baseline ≈ 497 and four documents.
   *Positive control:* the counter reports the baseline's 1366 on HEAD.
2. **Consumer non-domain code + config** to add one independently produced child:
   0 Python lines beyond the mapping branch; ≤ 10 YAML lines per child; ≤ 30 once.
   Baseline ≈ 219 per child. *Positive control:* the same counter over the shipped
   test's wiring reports ≈ 219.
3. **Concepts restated:** SDK-mechanism names imported by the producer's Python
   ≤ 12 (baseline 30); values stated in more than one document = 0 (baseline 6);
   the gate's window read once, from the served candidate.
4. **Safety, per defect class — can the common path still produce it?**
   Stale door contract → NO (no `ProductRequestViolation(` in any paved tree,
   AST-checked; positive control: the AST check finds cp-05's site). Mismatched
   replay configuration → NO (no class, pin class or store path is stateable on the
   road; one store per process, measured by listing the store's classes after a
   served and a door-refused decision). Duplicated principal/role → NO (`door:` and
   the environment document refuse the keys by name; positive control: the refusal
   test names the section). Ungoverned effective-request derivation → NO on the
   road (a spy `acquire` receives exactly `record.request_resolution.values()`;
   sabotage §12) and DIFFICULT off it (AST control on `examples/`). Wrong producer
   identity → DIFFICULT (one statement; a mismatch is refused `producer-mismatch`,
   OFC-G18). Bypassed admission → NO (a class with `requires` cannot open without
   the derived chain or an explicit `children=`). Missing refusal evidence → the
   producer's own refusals are always recorded (`recorded_boundary`); CP03C-F-05
   stays open and is named, never silently improved.
5. **Debuggability at the config/binding boundary:** every misdeclaration in the
   derivation list fails at `derive_deployment`/`open_product`/`open_door` with the
   section and key named — never at the first request, never as
   `ccf-runtime-failure:<id>`; a parametrized test over the refusal list asserts the
   message names the section, and its positive control asserts a correct document
   opens.
6. **Escape hatch without modifying SDK internals:** cp-03-canonical built through
   `build_arguments()` + `build_governed_resolver` yields the same content address
   as `answer()`; a deployment on `McpArtifactStore` passes `artifact_store=` and the
   door's denials land in that store; a hand-composed `QuestionBoundChildResolver`
   passed as `children=` serves the same child over `opened.mcp_skills`; an
   hw1-shaped per-process deployment opens the standard door through
   `ServesProducts` — each driven through the public surface.
7. **Dogfood identity:** the demonstration content address byte-identical before
   and after; OFC-G01..G27 green by the same node ids; dimension 2 differs by
   exactly the `replay`, `ttl`, `door` pins — traced at implementation to
   `_register_and_boot`'s pin list (`manifest.py:490-533`), not assumed.
8. **Structural gates:** `shape_of(cp-03-canonical) == "paved"`;
   `shape_of(cp-04-canonical) == "canonical"`; the synthetic paved tree is `"paved"`
   and problem-free; a tree calling both `open_product` and `build_governed_resolver`
   is refused `"double-spined"` by name; `CANONICAL_SHAPE_FLOOR` not raised;
   `check_product_gates` reports 15 trees clean.
9. **Compatibility:** the full-suite failure roster at the branch base versus the
   candidate, by node id: none new, none gone; every committed `ccf_config.yaml`
   content address unchanged.
10. **Authority count toward zero,** stated as a roster: the six authorities of §7
    are each either deleted (the document no longer carries the second statement)
    or checked (equality refused at derivation), and the roster is enumerated in
    the close report, not counted.
11. **Rulings:** every HARD ruling in §14's "respected" list held as written; the
    thirteen `R-n` asks logged before code — none discovered during implementation.

---

## 12 · Sabotage and negative-control strategy — driven through the public paved surface

Each mutation must turn a named test RED; a sabotage that stays green stops the
work (the `D-IMPL-340` proof-package discipline). Sabotage agents never share a tree.

| guarantee | mutation (through the public surface) | must go RED |
|---|---|---|
| Standard door wiring is load-bearing | delete `producer_id=`/`producer_tenant=` from `open_door`'s builder call | consumer admission refuses `producer-unasserted`; OFC-G16/G18; `test_product_door::asserts_producer` |
| The door is tool-only and governed | delete `server/serve.py` from the paved tree | the cross-deployment fixture cannot boot the producer; OFC-G16 |
| Duplicated authority refused at configuration (key) | add `principal_id:` or `role:` under `door:`; add `product_ttl_seconds:` to `ccf_environment.yaml` | parse refusal naming the key |
| **Duplicated authority with CONFLICTING VALUES refused at configuration** | declare `ttl.product_ttl_seconds: 2592000` and pass `product_ttl_seconds=86400` through `build_arguments()`; declare `consumes` for a class `requires` does not name | `TypeError`/open-time refusal naming both values; positive control: equal values build, matching rows open |
| One replay authority | remove `replay:` from the paved config | `open_product` refuses by name (not the builder) |
| One store, one class | patch `open_door` to build its recorder over `FileArtifactStore(scratch/"replay")` | the door-denial's `replay_reference` is unresolvable from the product's store |
| Effective request governed, not re-derived | patch `answer()`/the seam to hand `acquire` the RAW request | the spy's `context.request.parameters` lacks a defaulted `periods` while the record's `request_resolution` has it |
| Resolution runs exactly once (`R-4` (a)) | insert a second `constraint_resolver.resolve` before the seam | the audit log shows two resolution reads for one question |
| Intent judged before acquisition | remove `refuse_intent` from the resolution step | an undeclared intent triggers `acquire` (the spy counts a call) and then refuses |
| No re-derivation in example trees | insert `ReferencePolicyConstraintResolver(` into the paved tree's `deployment.py` | `test_spine_separation::paved_tree_constructs_no_constraint_resolver` |
| Stale door contract impossible on the road | insert `ProductRequestViolation(` into the paved `server/serve.py`; and delete the lane comparison in `OpenedProduct.resolve` | the AST control; and a `1.0.0` ask against the `1.1.0` door yields `ProductNotResolvable` → opaque failure instead of a governed `class-mismatch` at `key="schema_version"` |
| Wrong class denied by entitlement | ask for `reference.corporate-family` at the spread's door | `SubjectUnavailableRefusal(cause="unauthorized")`, never a served spread; positive control: the right class at the right lane serves |
| Wrong producer binding | edit `producers.spread.producer_id` in the consumer config | admission `producer-mismatch`; OFC-G18 |
| **`producer_tenant` equals `tenant_id` (`R-6`)** | declare `door.producer_tenant` ≠ `tenant_id` (if declared-and-checked) or patch the derivation to a literal | refused at derivation by name; every consumer refuses `producer-mismatch` |
| No dynamic producer selection | declare two `producers.*` offering `credit-risk.spread` | `open_product` refuses by name; sabotage the derivation to pick the first → the refusal test goes RED |
| Lane floor held at open | `offers.versions_from: "2.0.0"` against `compatible_from: "1.0.0"` | refused at open (`ChildRequirement.accepts`) — the earlier boundary than today's admission |
| **Lane asked equals the lane served (`R-13`)** | `versions_from: "1.0.0"` (or `lane: "1.0.0"`) against a producer serving `1.1.0` | under an explicit `lane`, refused at the first serve as `class-mismatch` with the reason retained once `D-IMPL-342` lands; until then the paved test asserts the `ineligible` row and names the limitation |
| Unadmitted child cannot be used | patch `open_product` to pass `composite_children=None` with `requires` non-empty | serve refuses `no-producing-skill`; the admitted-row assertion goes RED |
| Half-wired composite refused | `requires:` non-empty and `questions=` omitted; or `children=` together with the agent document | `open_product` refuses by name, both cases |
| The SDK synthesizes no agent | remove the agent document from a consumer | `open_product` refuses naming §6.4; sabotage: derive one → the refusal test goes RED |
| Registrations stay declared with the hatch | pass `children=` with `producers:` declared | opens; `opened.mcp_skills` holds the five servers; dimension 2 pins the five registrations |
| Per-question substrate | patch `answer()` to reuse one `database_path` | OFC-G24 (a second obligor under one `scratch` hashes as alone) |
| Scratch never inside the config root | `open_product(config_root=HERE, scratch=HERE)` | refused by name |
| Foreign envelope refused | remove `refuse_foreign_envelope`; have `acquire` emit `ingestion_timestamp = asked_at + 1 day` | the CP03C-F-08 directional test inverts |
| SDK L1 adapters reachable through `acquire` | drive `FileRecordAcquisitionSource` through `acquire` with `clock=lambda: context.instant`; then with a wall clock | the first serves; the second is refused by the boundary by name |
| One principal authority | change `default_perspective.role` and nothing else | served role and entitlement grant change together (positive control); sabotage: read a role from `door:` → parse refusal |
| Idempotent grant issuance | open twice over one `control_plane=` | the second open serves; sabotage: bypass the bound-view lookup → `GrantTransitionError` → RED |
| Second door on one product refused at open | `open_door` twice with differing `default_perspective` content | refused at open by name, not `ConstraintEffectivityConflict` at the first override |
| Structural gate is content, not vocabulary | a tree calling `open_product` AND `build_governed_resolver`; a tree calling `open_product` with a `lambda` factory | `"double-spined"`; `D-IMPL-137` row C |
| Paved vocabulary has a witness | delete the synthetic paved tree's `boot` region | `spine_problems` names the missing carrier |
| Low road reachable through the paved surface | build via `build_arguments()` + the builder, change `product_class_key` | content address differs from `answer()` (the mapping is load-bearing) |
| Replay read idiom | corrupt the served `replay_ref.content_address` | `record_of` raises by name |
| Harness neutrality | `import langgraph` in `product.py` | `harness_imports` lint RED |
| No substrate name in `src/` | write `"sqlite"` into `product.py` | `substrate_names` lint RED |
| No prose in `src/` | put a sentence into the derived entry's `description` (if `R-7` fixes it structurally) | `no_hardcoding` lint RED |
| The `decided_at` hoist | move `decided_at` below the scorer call | the seam test's `decided_at`-before-scoring assertion |

---

## 13 · What remains backlog — §I records

Each record carries the eight fields `docs/EXAMPLE-EVALUATION-CRITERIA.md` §I
requires. **Repeated evidence raises priority.**

- **B-01 · Entity-anchored expiry computed by the resolver.** *capability:* `expires_at` honors `ttl_anchor: from_entity_freshness`. *evidence:* cp-03-canonical CP03C-F-01; `ttl_anchor_basis` declared and unread. *current path:* a developer-authored gate withholds the serving half; the advertised expiry stays overstated. *friction:* one restatement, one gate, one xfail (OFC-G07). *impact:* every entity-anchored producer and every composite inheriting its floor (CP-14). *launch necessity:* §C step 1 — YES, ruled launch-blocking correctness (`D-IMPL-341`). *scope/risk:* resolver TTL computation; content addresses of entity-anchored trees move. *release:* before launch, its own decision — **not this phase**.
- **B-02 · Refused-child evidence on the consumer's row.** *capability:* `child_refusal_reason`/`kind`/`child_replay_ref` on `ChildResolution`. *evidence:* CP03C-F-05; §12's lane sabotage depends on it. *current path:* the consumer reads `ineligible` and nothing else. *friction:* undiagnosable serve-time misses. *impact:* every composite consumer. *launch necessity:* YES, ruled launch-level evidence gap (`D-IMPL-342`). *scope/risk:* record shape, hash-transparent addition. *release:* before launch, its own decision — **not this phase**.
- **B-03 · A Control Plane home for the reference scorer's declared C/S.** *capability:* `assess=None` on the road. *evidence:* hw1's `binding.yaml debt:` carries them outside the Control Plane; every ladder producer authors its own scorer. *current path:* author `assess`. *friction:* ≈ 30 lines per tree of scorer boilerplate for trees that want the reference rule. *impact:* simple producers. *launch necessity:* §C — NO; the road works with an authored scorer. *scope/risk:* a `D-IMPL-292`-shaped declaration. *release:* post-launch.
- **B-04 · `ProductGateProtocol` receiving the class's declared bindings.** *capability:* a gate that reads declared values without deriving them from the candidate. *evidence:* cp-03-canonical's window. *current path:* `expires_at − temporal_boundary`. *friction:* one derivation, documented. *impact:* gates over declared values other than TTL. *launch necessity:* NO. *scope/risk:* touches `R-11`'s Protocol. *release:* post-launch, or deleted by B-01.
- **B-05 · Refuse `from_entity_freshness` with an `observed-at` scored row at derivation.** *capability:* CP03C-F-08 impossible by declaration. *evidence:* eight trees declare the anchor with no basis. *current path:* the author remembers. *friction:* a silent F = 1. *impact:* every entity-anchored producer. *launch necessity:* §C step 2 — arguably YES; recommended for the SDK phase as one derivation-time refusal (≈ 10 lines) if Dave folds it in, else post-launch. *scope/risk:* derivation only; frozen trees are not edited (they would read red — evidence, per `D-IMPL-261`). *release:* SDK phase if ruled in; else next.
- **B-06 · A declared home for the request `freshness` vocabulary.** *capability:* `ProductDiscovery` carries freshness tokens. *evidence:* `filing-cadence` lives in code, spec and test. *current path:* a literal. *friction:* one unjudged token. *impact:* producers and their consumers' mappings. *launch necessity:* NO. *scope/risk:* `contract.py:389-404`. *release:* post-launch.
- **B-07 · An explicit `lane` on a producer offer** (if `R-13` rules it). *capability:* the lane asked declared distinctly from the floor. *evidence:* the test binds `1.1.0` read off the producer's config. *current path:* `versions_from` read as the lane. *friction:* a floor-vs-address misread refused only at serve. *impact:* every `mcp_product` consumer. *launch necessity:* §C — YES if `R-13` selects it (it is a correctness-of-declaration gap). *scope/risk:* `ProducerOfferDeclaration`, hash-transparent. *release:* SDK phase under `R-13`.
- **B-08 · The dangling `halflife_debt_profile` ref passes the ledger unchecked.** *capability:* the ledger resolves every ref on the definition. *evidence:* three consumer sites point at an unregistered artifact. *current path:* decorative. *friction:* a copier learns nothing. *impact:* every agent definition. *launch necessity:* NO (grant machinery, not 343's). *scope/risk:* `grants.py:663-664`. *release:* post-launch.
- **B-09 · A `per-process` lifecycle and non-SQLite L3 on the paved road.** *capability:* `open_product` over a long-lived, CDC-fed fabric. *evidence:* hw1, the crossproc producer fixture, the stdio fixture. *current path:* the hw1 composition; the standard door via `ServesProducts`. *friction:* boot + builder by hand (≈ 60 lines). *impact:* production deployments. *launch necessity:* §C — NO for the examples; stated plainly in `R-3`. *scope/risk:* lifecycle semantics, single-writer. *release:* first post-launch enhancement.
- **B-10 · `ReplayBinding` selecting an MCP-backed store.** *capability:* `replay:` alone binds a production store. *evidence:* `artifacts.py:640-650` limitation. *current path:* `artifact_store=`. *friction:* one keyword. *impact:* production. *launch necessity:* NO. *scope/risk:* `R-12`. *release:* post-launch.
- **B-11 · `ccf product serve --root` and an HTTP-door builder over `door:`.** *capability:* a CLI verb on the EXISTING `product` noun (`runtime/ccf_runtime/cli/commands/product.py:32-35` already registers `product get`). *evidence:* six `serve.py` launchers. *current path:* an 8-line `server.py`. *friction:* 8 lines. *impact:* every producer. *launch necessity:* NO — tooling, excluded by ruling. *scope/risk:* the CLI's own §8.3 surfaces (`agent.py`, `skill.py`, `artifact.py`, `replay.py`) were not surveyed by the census and should be before any verb lands. *release:* post-launch.
- **B-12 · Doors for cp-04-canonical and cp-13; 340-conforming doors for cp-05 and cp-06.** *capability:* CP-14's rows 2–5 acquirable. *evidence:* §8. *current path:* none. *friction:* ≈ 17 YAML lines + 8 code lines each on the paved road; frozen trees need rulings. *impact:* CP-14 only. *launch necessity:* CP-14's own gate, not the SDK's. *scope/risk:* rung work. *release:* after dogfood A, per rung.
- **B-13 · A YAML lint for literal URLs/tokens in `ccf_config.yaml`.** *evidence:* `D-GATE-340` residual 4. *current path:* `parse_artifact` refuses at derivation. *friction:* none until a copier pastes a token. *launch necessity:* NO. *release:* post-launch.
- **B-14 · Close the attribute-form hole in `test_spine_separation._qualified_calls`** (`:360-366` reads `ast.Name` callees only). *evidence:* the misconfiguration census. *current path:* OFC-G13's text grep on one tree. *friction:* a detector that can be evaded. *launch necessity:* NO. *release:* with the `R-1` widening if cheap, else post-launch.
- **B-15 · Multi-principal entitlement on the standard door.** *current path:* `entitlement_source=`. *launch necessity:* NO. *release:* post-launch.
- **B-16 · An HITL `ApprovalSink` reference for approval-gated grants** (`D-IMPL-29` tier 2). *current path:* `approval_sink=`. *launch necessity:* NO. *release:* post-launch.
- **B-17 · hw1's `binding.yaml` composed onto `BootedFabric.keys` and the declared bindings.** *launch necessity:* NO (`D-IMPL-141` unchanged). *release:* post-launch consolidation.
- **B-18 · A `SignalEnvelope` helper for relational rows against `entity_rules`** (≈ 27 lines per tree). *launch necessity:* NO — deliberately not a paved-road convenience; wait for a third tree. *release:* unscheduled.
- **B-19 · A public operator-registry rebuild for consumer-side replay** and a paved `OpenedProduct.replay(address)`. *evidence:* the private `_operator_parameters` reach. *launch necessity:* NO — advanced. *release:* post-launch.
- **B-20 · Explicitly excluded by the ruling:** fan-out, swarm scheduling, dynamic producer selection, a parameterized-product DSL, scaffolding, visual tooling, templates, discovery, convenience APIs beyond the facade. *current path:* not applicable. *launch necessity:* NO by ruling. *release:* none scheduled; each would need its own §I record when evidence arrives.

---

## 14 · Rulings asked of Dave before implementation

**Respected as HARD, with the design's specific obedience:** `D-IMPL-343`'s
amendment (one facade over the existing mechanisms; no second resolver, door,
registry, ledger or gate); `D-IMPL-282` R-11 (gate declared + predicate supplied,
both-or-neither), R-12 (the binding consumed exclusively on the road; precedence
untouched on the low road), R-09 (acquisition through a declared interface; the
resolver holds no writer — `resolver.py:1337-1345` unchanged); `D-IMPL-279` R-01
(the wrong-address verdict in the spine-side adapter before transport);
`D-IMPL-289` (every deleted line deleted because a declaration or the SDK's own
derivation supplies it); `D-IMPL-253` Q13/Q18/Q20 (inherited through
`build_egress_server`); `D-IMPL-264` D-01/D-07 (intent judged once; `question()`
cannot place intent in parameters; no marker manufactured); `D-IMPL-136`/`138`
(backends out of the Control Plane; unknown keys refused; no adopter class id
derived); `D-IMPL-137`/`141`/`301` (named factory sourcing only `required`;
`binding.yaml` and `REFERENCE_KEYS` untouched); `D-IMPL-306` (no roster;
half-migrated refused by name); `D-IMPL-313`–`315`/`319` (the developer-authored
things stay theirs; no binder/gate/record/serve in acquisition or deployment
layers); `D-IMPL-337` (no new guarded type; `ServesProducts` asserts no guarded
authority); `D-IMPL-340` rulings 1–11 (registration is the authority; `requires:`
about the product; no producer on `ChildRequirement`); `D-IMPL-224` (`gates.yaml` +
checker untouched); `D-IMPL-261` (no frozen specimen edited); CLAUDE.md §6.4/§10/§11
(no value in `src/`; the SDK synthesizes no agent; L2 is the only writer; zero
harness imports).

**Asked — each an entry before code; the recommendation is marked:**

- **R-1 · A fourth structural shape (`D-IMPL-306`/`D-IMPL-301`).** `shape_of` gains
  `"paved"` and the named refusal `"double-spined"`; `PAVED_PATH_MARKERS = ("boot",
  "product", "answer")` (`boot` kept so `region_modules` keeps working);
  `CANONICAL_RESOLVER_ENTRYPOINTS` gains `open_product`; `RULED_SDK_SUPPLIED_DEPLOYMENTS`
  keeps cp-03-canonical only under that widening; `CANONICAL_PATH_MARKERS` is not
  required of a paved tree. Vocabulary, no roster. **Recommend: rule as written.**
- **R-2 · The composing agent as a declared document (`D-IMPL-85`/`D-IMPL-136`).**
  Measured: `ccf.agent-definition` is in `SDK_VERSIONED_ARTIFACT_CLASSES`
  (`classes.py:209-210`), not in `SDK_ARTIFACT_CLASSES` (`:137`; the two are disjoint
  by construction, `:199`); the typed derivation injects `semver` (`config.py:435`)
  which `_TwoLaneVersioned` refuses; a reserved section defaults to `registration:
  typed` (`:400`) which `refuse_registration_the_sdk_fixes` (`:412`) refuses for an
  author-versioned class; the guard test (`test_config_derivation.py:122-132`)
  requires a typed class. Options: **(a) recommended** — a reserved-section
  mechanism for author-versioned classes: a third table member selecting the
  versioned path (no `semver` injection; `registration: versioned` fixed by the
  SDK), the guard widened to both tables under an explicit ruling, so the adopter
  writes `agent:` in `ccf_config.yaml` once; **(b)** a separate `ccf.agent-definition`
  document registered through the versioned manifest path and referenced from
  `ccf_config.yaml` by key (no derivation change; a second document). Under either,
  confirm the SDK may **check** `consumes ⊇ requires` and refuse a disagreement as a
  checked cross-reference, not count it as a second authority. The census's "if
  absent it is added" fallback is struck.
- **R-3 · `D-IMPL-292` applied three times.** (a) TTL as a `ttl:` binding with
  equality on the builder's two (now optional) keywords; (b)
  `decision_instant_parameter` on `ProductClassDeclaration` (hash-transparent),
  closing the "architecture question" 24.10-F-09 recorded at
  `resolver.py:1436-1443`, with the builder keyword held equal; (c) `assess=` REQUIRED
  in v0 and `InstantAwareDebtScorerProtocol` as the way the instant and children
  reach a scorer. Also under R-3: confirm that the paved road accepts ONLY the
  per-question dev-backend lifecycle in v0, **with the stated consequence** that a
  long-lived L3 gets the standard door and the seams but not `open_product`'s
  lifecycle (B-09). **Recommend: all as written.**
- **R-4 · One resolution per question (`D-IMPL-282` R-09 / `D-IMPL-289`).** A
  preview method relocates the double derivation into `src/` and doubles the audited
  Control Plane reads (`constraints.py:1344`, `:1698`). Options: **(a) recommended**
  — an `acquisition=` seam on the governed call: the resolver resolves the effective
  request once, hands it to the declared seam, the facade acquires and ingests
  through L2, the same call continues; the resolver still hands no envelope to a
  writer. Reading asked: this is "a prepared context input produced through a
  declared acquisition interface", not the resolver "talking to sources". **(b)** a
  preview, with the doubled audited reads accepted explicitly and the sabotage row
  "preview equals `__call__`" in place of "resolution ran exactly once".
- **R-5 · `D-IMPL-141` Amendment A.3–A.4 — confirm the reading** that a Python
  binding site (`open_product(acquire=, project=, assess=, gate=)`, as
  `produce.py:131-191` binds today) is the intended canonical shape, so the
  "exactly one Python module" clause governs `binding.yaml` only and A.4's precedent
  clause is not tripped. **Recommend: confirm.**
- **R-6 · `producer_tenant` (`D-IMPL-340` as-built §14, a REVERSAL if derived).**
  Options: **(a) recommended** — `door.producer_tenant` **declared** and checked
  EQUAL to `tenant_id` at derivation (the `D-IMPL-292` equality shape; the door
  never reaches into the product for a value; a disagreement is refused by name);
  **(b)** derived from `tenant_id`, which reverses the recorded decision.
- **R-7 · The derived `mcp_product` catalog entry (`D-IMPL-56`/`D-IMPL-29`).** Every
  value except three is determined by the registration and the requirement, but
  `D-IMPL-56` ruled the ENTRY declares `description` and `argument_schema`
  ("compose from fields … a workaround, not a resolution") and `D-IMPL-29` makes
  `requirements` the tier-1 governance input the entry declares. Options: **(a)
  recommended** — rule that for `skill_type: mcp_product` the three are structurally
  fixed by the skill type (empty schema, empty requirements, an identifier
  description) and record the fixed values as mechanism; **(b)** a minimal declared
  `skills:` block per child carrying the three, the adopter's statement. The design
  does not present the derivation as settled.
- **R-8 · The `_typed` drop (`D-IMPL-264` D-04 / `D-IMPL-302`).** Wire parameters
  cross verbatim; a hand-typed `"periods": "8"` is refused `type-mismatch` where the
  canonical tree's door coerced. The ruled behavior, but a change to a shipped door
  — stated for the record. **Recommend: accept.**
- **R-9 · A wrong lane at a door is a bad question (`D-IMPL-253` Q15).** The
  resolver's docstring (`resolver.py:355-361`) classifies a wrong address as a
  broken deployment; the two shipped doors already treat it as a governed
  `class-mismatch` with a record. Rule the door reading and record it against the
  docstring; a wrong **class** is denied by the derived entitlement before the
  resolver is reached (§5.4). **Recommend: rule the door reading.**
- **R-10 · Reserved sections and the environment document (`D-IMPL-136`).** Three
  points: `ttl:` and `door:` as reserved sections; the `door:` URL boundary —
  `issuer_url`/`resource_server_url` as Control Plane binding (**recommended**; four
  door documents already carry them under semver + class id) or as environment;
  and `backends.yaml` renamed/widened into `ccf_environment.yaml` as the documented
  deployment-environment companion (`D-IMPL-136` names `backends.yaml` by file and
  the amendment makes `ccf_config.yaml` the only documented authoring surface — the
  companion is environment, not a second authoring surface). **Recommend: all
  three as written.**
- **R-11 · `D-IMPL-313`/`314`/`315` and `D-GATE-cp-03-canonical` superseded for one
  tree.** The dogfood exits the canonical shape those entries require ("uses
  boot/acquire/govern … delegates governance to `GovernedResolver`"; "`shape_of`
  must prove canonical"). Rule that `D-IMPL-343`'s dogfood instruction supersedes
  them for cp-03-canonical only, and that cp-04-canonical remains the canonical
  witness. **Recommend: rule as written.**
- **R-12′ · `D-IMPL-340` ruling 7 narrowed at registration level.** The road refuses
  two offers for one class at open; the grant-level ambiguity rule
  (`composite.py:985-994`) stays reachable through `children=`. **Recommend:
  accept the narrowing, named.**
- **R-13 · The lane asked (`ProducerOfferDeclaration.versions_from`).** It is a
  floor by contract (`artifacts.py:2287`) and an exact address by use
  (`dispatch.py:1004-1006` sends it as `version`; the door serves exactly its lane).
  Options: **(a) recommended** — an explicit `lane` on the offer (B-07), with
  `versions_from` keeping its floor meaning and defaulting to `lane`; **(b)** rename
  the field on the road and document that the lane asked must equal the served
  lane. Under either, `D-IMPL-342` is what makes the serve-time miss diagnosable.

**Closed by measurement, no ruling needed:** OQ-7 (per-question re-registration
into one registry is idempotent on every path; the audit-row cost is stated); OQ-8
(resolved the *other* way — it became `R-2`).

---

## 15 · Stop conditions and what this document does not do

This design does not implement anything, does not touch CP-14, does not implement
`D-IMPL-341` or `D-IMPL-342`, does not re-express cp-03-canonical, and does not edit
a frozen specimen. It asks thirteen rulings and then stops. The two carried
findings on frozen trees — cp-05's second stale wrong-address site and
cp-04-canonical's fixed substrate path — are recorded here as evidence and are not
repaired.

---

## 16 · As built — the consumer half (2026-09-15, synchronization of this design to the tree)

Written after the consumer half landed on `d-impl-343-dx`, so a reader of §5.5, §8, §12
and §14 knows where the tree departs from the design's estimate and why. Nothing above is
rewritten; this section is the record of what was built where the design offered options.

**`skills:` — R-7 as ruled (a declared block, with derivation).** Dave ruled *"GO only from
declared config keys (produces, name, requirements). No invented third field. D-IMPL-56 and
D-IMPL-29 stand."* The section is therefore the design's option (b): one `ccf.skill-catalog-entry`
per label, author-versioned (`_RESERVED_VERSIONED_SECTIONS["skills"]`), carrying what only the
author can state — `schema_version`, `artifact_version`, `description` (`D-IMPL-56`),
`requirements` (`D-IMPL-29`) and `produces` — while the SDK fills, from other declared keys,
`name` (the label), `skill_type` (`mcp_product`), `binding` (the ONE `producers.*` entry whose
`offers` name `produces`, at that producer's `versions_from` floor) and the structurally empty
`argument_schema` (the dispatch passes no arguments). A stated value is held EQUAL to its
derivation (`_hold_equal`), never overridden; a `key:` override is refused because the entry
registers under the `{tenant}/ccf.skill-catalog-entry/{name}` key its grant resolves through.
No or two producers offering the class, a class the composite does not require, and a floor
outside the requirement's lane are refused at derivation by name (`R-12′` accepted). The grant
is derived from the entry alone — its lanes are the entry's two, its name the entry's, its
agent the agent's content hash — and requested at open, idempotently over a shared registry.

**`agent:` — R-2 as built.** The section is the agent document in reduced form: `name`, the
two lanes and `archetypes` are declared; `context_contract` is filled from `requires` (each
class at its `compatible_from`) or, when stated, checked to cover every requirement at a lane
it accepts; `perspective` is filled from `default_perspective` or held to its role;
`policy_regime` and `halflife_debt_profile` are filled as pinned references to the deployment's
own `policy:` and `debt_profile:` sections at the config's `semver`, or held equal when stated;
`instruction_bindings` defaults to none. Because a pinned reference is
`ccf-artifact://{tenant}/{class}/{name}@{version}`, the two sections carry a `key:` override in
that form (two lines) — the refusal names exactly that remedy. `policy.skill_governance` is the
regime's skilling envelope, one authority for the product and for the agent.

**R-13 as built — the floor at three boundaries, and no `lane` field.** Dave's ruling
superseded both options in §14: *"versions_from is a floor everywhere … Do not tighten the
contract to 'exact lane only'."* B-07 is therefore withdrawn and §12's row *"Lane asked equals
the lane served"* is superseded. The one rule (`ccf.products.contract.version_satisfies_floor`:
same major, at or above, by semver precedence) is read at derivation (the offer floor must lie
inside the requirement's lane), at the standard door (`OpenedProduct.resolve` serves its ONE lane
when it satisfies the floor the address names, answering at the served lane, and refuses
`class-mismatch` at `schema_version` with BOTH lanes in its record otherwise), and at admission
(unchanged: `version-incompatible`, reason retained). The binding's `product_version` — sent on
the wire — is the offer floor. Where the reason lives: the producer's record holds both lanes;
the consumer's record retains the producer's refusal by kind, reason and key
(`class-mismatch at 'schema_version'`), as the producer's door disclosed it; the consumer's row
says `ineligible` and carries no `child_replay_ref` for a refused child — that last gap is
`D-IMPL-342`, excluded by ruling. Measured against the real producer (`1.1.0`): floor `1.0.0`
serves; floor `2.0.0` refuses with the reason retained (dogfood B).

**The environment document as built** (§5.1 sketched it): `substrate: {setting, prefix,
suffix}` — the SETTING names which connection setting of the declared adapter receives the
minted path; `door: {credential, issuer_url, resource_server_url}`, each `{from_env, remedy}`;
`sources.<name>.<setting>: {from_env, remedy}`; `remote: {call_timeout_seconds}`. A pure consumer
declares no `sources:`.

**The consumer surface as built** (§5.5): `open_product(…, questions=, approval_sink=)`;
`OpenedProduct.mcp_skills` (the one registry, populated whether the chain is derived or handed
in), `OpenedProduct.agent`, `close()` (the bridge). Registration of the regime, the agent and the
skills at open goes through the manifest's one register loop
(`ccf.deployment.manifest.register_manifest_entries`), extracted rather than copied; open still
boots nothing.

**Measured, consumer side** (the counter in Appendix A; dogfood B's own documents): the low
road's consumer wiring in `test_cp_03_canonical_cross_deployment.py` is 129 code lines plus the
38-line resolver-argument mapping it depends on; the paved consumer is 15 code lines of Python
(the question mapping and the open call) plus 26 lines of YAML (21 under `producers`/`skills`/
`agent`, the `requires` row, two `key:` overrides, `skill_governance`, `remote`). SDK objects
the adopter constructs: 0 (from 9: registry, bridge, client factory, regime, agent definition,
catalog entry, ledger, grant, gate/resolver). Values stated more than once: 0 (from 3: the
producer's lane in the offer, the binding and the agent's contract; the tenant in four objects).

**Dogfood B equivalence** (`tests/examples/test_cp_03_canonical_paved_consumer.py`): against
one canonical producer process, the low road and the paved road admit the same child — every
child-level row member equal (25 members, enumerated), the retained child byte-identical, the
registration address identical (the derived document IS the hand-built one) — and the
parent-owned members (`grant_hash`, `child_admitted_at`, `child_reported_address`,
`child_debt_factors`, `refusal_ref`) are the ones that differ, by name.

## Appendix A · The line counter (reproducible)

Code lines = physical lines carrying at least one token that is not a comment,
blank, indentation or end marker, excluding docstring lines. Run from the repo root
with the project's interpreter; it reports the baseline's `1366` and `419` on HEAD
`1e22dae2`.

```python
import ast, io, sys, tokenize

def code_lines(path):
    src = open(path, encoding="utf-8").read()
    doc = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            first = node.body[0] if node.body else None
            if isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant) \
                    and isinstance(first.value.value, str):
                doc.update(range(first.lineno, first.end_lineno + 1))
    skip = {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT,
            tokenize.DEDENT, tokenize.ENCODING, tokenize.ENDMARKER}
    lines = set()
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type in skip:
            continue
        lines.update(ln for ln in range(tok.start[0], tok.end[0] + 1) if ln not in doc)
    return len(lines)

for path in sys.argv[1:]:
    print(f"{code_lines(path):5d}  {path}")
```

## Appendix B · Review record — what was accepted, what was rejected, and why

Fifteen agents: six censuses, three designers, one synthesis, three refuters, one
critic. Findings were verified against the tree before use.

**Accepted (blocking) and applied:** the `agent:` reserved-section impossibility
(rulings refuter and leaks refuter; three guards verified — `R-2`); semver on the
derived catalog entry (both; `catalog.py:630-633` — §5.5); the entry's declared
halves (`D-IMPL-56`/`29` — `R-7`); the preview's doubled audited reads (rulings
refuter; `constraints.py:1344`, `:1698` — `R-4`); `PAVED_PATH_MARKERS` must keep
`boot` (escape refuter; `region_modules` `:310-318` — §9); OFC-G13 red by
construction and the wider test-body change set (escape refuter and critic; §7);
the `children=` cliff (escape refuter; §5.5, §6 hatch 2); one `root` conflating
three locations (leaks refuter; `config_root`/`scratch` — §5.2); the composition
step missing from the consumer decomposition (critic; C9); the failure-mode column
(critic; §1, §2); the door grant-expansion and per-process responsibilities
(critic; §3 P11″, P2″); cinv04 on a substrate-minting facade (critic; §5.3 step 1);
`ttl_anchor_basis` dropped without being named (critic; finding 5); the baseline
misattributed to `bff2ff17` (critic; header); the existing `product` CLI noun
(critic; B-11); §I-shaped backlog records (critic; §13); the return wrapper
(critic; header); the composite factory's module under gate-two condition 3
(escape refuter; §8); the `decided_at` hoist (leaks refuter; §5.2); the
class-vs-lane reach of the door's refusal (leaks refuter; §5.4, §12); the gate
window read from the candidate (leaks refuter; §7); the grant collision on a shared
registry (escape refuter; §5.5); `store_dirname` beside `artifact_store=` (escape
refuter; §6 hatch 2); the audit-row cost of per-question boot (rulings refuter;
§5.3); `uvicorn` already pinned, `anyio` only (both; §9); the client-adapter
location of the "ships no server program" rule (critic; not cited as governing
doors).

**Rejected, by measurement:** the escape refuter's and the critic's claim that
`ccf.agent-definition` is a member of the typed table — the line they pointed at
is inside `classes.py::SDK_VERSIONED_ARTIFACT_CLASSES`, and
`classes.py::SDK_ARTIFACT_CLASSES` does not contain it. Two reviewers
agreeing was not evidence; the tree was. The synthesis's "shared `_resolve_request`"
was likewise not an existing site: the derivation is inline in `__call__`
(`:1813-1917`), and the shared site is the refactor `R-4` proposes.

**Recorded as advisory, carried into §14:** `producer_tenant` as a reversal
(`R-6`); `versions_from` floor-vs-address (`R-13`); `D-IMPL-313/314/315` supersession
(`R-11`); `backends.yaml` naming (`R-10`); ruling-7 narrowing (`R-12′`); the Q15
classification (`R-9`); `substrate.lifecycle` as a one-value key (dropped);
`refuse_foreign_envelope`'s rule stated on the Protocol (§5.3); the L1 adapters'
clock (§5.2, §12).
