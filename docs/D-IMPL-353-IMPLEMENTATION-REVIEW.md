# D-IMPL-353 — implementation review package

**Candidate:** branch `security-tier-0`, HEAD = **the commit that carries this package** (2026-09-25). The code is the pre-merge commit (R6 closed by signature, R11 bound at the handle) on `e385df29` (the ruling of 2026-09-25) on `81b6f1c7` (the first panel's fixes) on `cdd3450c` and `b1ec0e5e` (the join).
2026-09-23 security review). **Nothing is merged to `main`, nothing is tagged, nothing is pushed.** This package is the
stop Dave asked for: *"Return the candidate SHA, changed-signature inventory, static/runtime control results, sabotage
results, panel dispositions, and remaining limitations. Stop for implementation review."*

Written by the coordinator. Every count below names what it ran; every panel claim below was resolved against the tree
before it was accepted or rejected (`D-IMPL-352`).

## 1. What was built

`D-IMPL-353` (design ACCEPTED): authorization is no longer a guard whose applicability the caller decides. A served
surface (HTTP route, MCP tool/resource, stdio ambient identity, CLI in-process leg) mints an `Authorized[Kind]`
capability at exactly two sites — the HTTP gate and the MCP wrapper — from the authorizer's whole decision, and every
state-changing handle (registry register, state put, artifact put, grant request/revoke, workflow execute/resume, HITL
submit) requires the capability for its own action and takes the tenant and the key FROM it. Seven lanes built it in
worktrees; three join lanes migrated the callers and the tests; the join reconciled them and closed the seams the merged
tree surfaced.

Two provisional readings the join had to take, both **OPEN and Dave's** (`docs/DECISIONS.md`, `D-IMPL-354` and its
2026-09-25 addendum):

- **Composition authority (`D-IMPL-354`).** A composition root — the config loader, `boot`, the paved road, the
  resolver, the MCP product door — mints `CompositionRegister` / `ReplayMint` (distinct from every door kind, ruled
  2026-09-25) for its own fabric by one recipe (append a
  `composition` audit event, mint with that event's content hash as `decision_id`). `mint_at_composition` refuses
  every door kind by overload and at runtime; the lint names the five roots.
- **One key derivation.** A deployment's Control Plane keys are placed under its resolved tenant before anything is
  minted (`namespaced_key`, confinement; `manifest_under_tenant`, `keys_under_tenant`); the register loop is told which
  tenant it composes for and refuses any key under another.

## 2. Commits (join)

| SHA | what |
|---|---|
| lane merges (see `docs/surface-changes/353-01` … `353-08`) | seam + relocation; CAP-GATE; ENGINE; LINT; EXAMPLES (frozen doors reverted); MCP2; HITL-DOOR; HANDLES; J-SRC; J-RUNTIME; J-TESTS |
| `b1ec0e5e` | **one key derivation** (`namespaced_key`, `manifest_under_tenant`, `keys_under_tenant`; `OpenedProduct.keys` names the placed strings); the paved road requests no grant (`grants_in_force` pre-grants in tests); **SEC353-J-02** fixed in `run_with_session`; children path fixes; stale `tenant_from_request` removed; regenerated surface log, manifest, `openapi.json`, retirement report |
| `cdd3450c` | the merged-tree sabotage's own controls (`TestNoDoorMintsTheGovernedRecord`, after M18 reddened nothing) and the served-surface probe over every mounted route; the SEC-001 strict xfail on `openapi.json` removed as it said it would be |
| `81b6f1c7` | **the panel's blocking findings, fixed in-phase:** F-FORGE-01 (mint record off the object into a module-private identity table; `__reduce__` refuses copy/pickle; lint rule 3 covers the table); the register loop takes `tenant=`; the agent/config/skill read routes see one tenant; the composition roster is the five callers |

## 3. Changed-signature inventory

The per-name record is the surface log: `docs/surface-changes/353-01-…` through `353-09-the-join.md`, assembled into
`docs/SURFACE-CHANGES.md`, held to the regenerated manifest `docs/surface/v0.2-surface.json` by
`tests/test_surface_completeness.py`, `tests/test_surface_drift.py`, `tests/test_surface_shape_capture.py` and
`tests/deployment/test_class_lookup.py` (all green at the candidate). The names the JOIN itself changed:

- `ccf.controlplane.registry.namespaced_key`
- `ccf.deployment.manifest.manifest_under_tenant`
- `ccf.deployment.manifest.keys_under_tenant`
- `ccf.products.product.OpenedProduct`
- `ccf.mcp.client.run_with_session`
- `ccf.replay.serve.QueryPinWriter`
- `ccf.authz.capability.verify`
- `ccf.authz.capability.Authorized`
- `ccf.deployment.manifest.register_manifest_entries`
- `ccf.deployment.register_manifest_entries`
- `ccf_runtime.http_api.grants.within_tenant`
- `ccf_runtime.http_api.grants.absent`
- `ccf_runtime.http_api.routes.agent.build_router`
- `ccf_runtime.http_api.routes.config.build_router`
- `ccf_runtime.http_api.routes.skill.build_router`
- `ccf_runtime.http_api.grants.tenant_from_request`
- `ccf_runtime.mcp.product_door.scope_mapping_key`

## 4. Controls, measured on the candidate (code `e385df29`)

| control | result |
|---|---|
| `make lint` (the six-rule `D-IMPL-353` authorization lint — rule 3 now also refuses the issuance table's names; roster of standing reds EMPTY) | rc 0 |
| `mypy --strict` over `src` + `runtime` | clean, 241 files |
| `tests/` — chunk A (`examples`, `conformance`) | 25 failed / 1337 passed — **all 25 pre-existing** at the join's census base `457552ce` (0 new; node ids diffed); frozen specimens under `D-IMPL-261`, rows in the gap ledger |
| `tests/` — chunk B (`products`, `crossproc`, `client`, `invariants`), post-commit | 4278 passed |
| `tests/` — chunk C (everything else under `tests/`), post-commit | 3607 passed, 28 skipped |
| `tools/lints/tests`, `tools/product_gates_tests`, `tools/publish_scan_tests`, `tools/docs_tests` | 976 passed (the retirement report regenerated last, as the standing rule requires) |
| seam controls (`tests/authz`: capability incl. `TestFabrication`'s real-sentinel and copy/pickle controls, `TestCompositionKindIsDistinct`, `TestNoDoorMintsTheGovernedRecord`; the static control marks the door kind as the type error) | green |
| served-surface probe (`tests/http_api/test_join_routes_under_the_capability.py::test_on_every_mounted_route_no_credential_mints_nothing_and_a_foreign_one_mints_only_for_itself`) | every path the app publishes + the doc routes: no credential / malformed → nothing minted, 401/403; a foreign-tenant credential mints only for its own tenant |
| cross-tenant reads (`…::test_a_read_after_an_allow_sees_only_the_capabilitys_tenant`) | lists are the capability's tenant's; foreign keyed reads and the skill-grant definition key read as absent, byte-identical |
| surface gates + fragment-claim gate | 93 passed |

## 5. Sabotage

Lane tables are in the lane fragments and reports (CAP-GATE 18, ENGINE 7, LINT per rule, seam S1–S4 + stub-sentinel).
The merged-tree run (main checkout, one severing at a time, the file restored byte-for-byte between; driver and logs in
the coordinator's scratch, summarised here):

| # | severing | named control that went red |
|---|---|---|
| M1 | gate mints even on deny | `TestTheGateMints::test_a_refusal_mints_nothing` (+1) |
| M2 | gate does not park `authorized` in scope | 212 reds — every route body |
| M3 | verify: drop kind identity | `TestWrongKind` (25) |
| M4 | verify: trust a stand-in's fields (table skipped) | `TestFabrication` (20) |
| M5 | verify: drop resource equality | `TestWrongResource`, `TestMintAtComposition` one-key (3) |
| M6 | `Authorized.__setattr__` allows | `TestRetargeting` (6) |
| M7 | registry handle skips `verify_any` | `test_registry_capability_controls::TestWrongKind` (17) |
| M8 | state put files under the record's tenant | `…another_tenant_is_refused_before_the_write` |
| M9 | artifact put skips `verify_any` | `test_write_kinds::TestWrongKind` (19) |
| M10 | grant ledger skips verify | `test_grants_capability_controls` (10) |
| M11 | engine execute skips verify | `test_tenant_is_the_capabilitys` (7) |
| M12 | engine resume skips verify (SEC-001's neighbourhood) | same module (6) |
| M13 | factory drops the tenant comparison | `test_factory::…tenant_mismatch_is_refused_once` (5) |
| M14 | MCP wrapper registers the bare handler | 187 reds across `tests/mcp` (lint stays green: it guards call sites, not the wrapper's internals) |
| M15 | MCP wrapper acts on a tenant the grant does not carry | `test_mint_site::…tenancy_floor_runs_before_the_authorizer` (8) |
| M16 | HITL approver not the capability's principal | `test_principal_from_authorized`, `test_was_called_derivation` (5) |
| M17 | a `.tenant`-carrying `TokenGrant` subclass in a fixture | cap-gate S7 controls (2) |
| M18 | `kind_for_action("replay.mint")` allowed | **0 → 1 after the join added `TestNoDoorMintsTheGovernedRecord`** (the invariant had been carried only by the action map's content) |
| M19 | `mint_at_composition` from the HTTP gate | lint rule 3 + roster test |
| M20 | `create_app(authorizer: … | None = None)` | lint rules 1+2 + roster test |
| M21 | CLI `# type: ignore[arg-type]` over a Mapping authority | lint rule 6 + `tests/cli` bundle controls |
| M22 | a route without `@authorizes` | lint rule 5 + 288 boot refusals |
| M23 | codex's proposed gap: constant composition `decision_id`, no audit event | **REJECTED** — `test_every_registered_entry_is_preceded_by_its_own_composition_event` (5) |
| M24 | gemini's proposed gap: drop the `principal` field check | **REJECTED** — `TestRetargeting[principal]`, dereference retarget control (6) |
| M25 | cursor's S-FORGE: honor an exact-type instance not in the table | `TestFabrication` incl. the real-sentinel forgery (14) |
| M26 / M27 | read routes: list unfiltered / foreign key resolved | `test_a_read_after_an_allow_sees_only_the_capabilitys_tenant` |
| M28 | register loop mints for the key's segment, not the given tenant | `test_the_register_loop_mints_for_the_tenant_it_is_given…` |
| M29 | resolver composition mint from the key's segment | 47 reds while the fix was in; the fix was REVERTED under the ruling (residual R1) — the severing is withdrawn and the pinned test documents the current behavior |
| M30 | `skill.grant` resolves a foreign definition key before the ledger | `test_a_read_after_an_allow_sees_only_the_capabilitys_tenant` |
| M31 | `mint_at_composition` accepts the door's `Register` (runtime check gone) | `TestMintAtComposition::test_a_door_kind_cannot_be_minted_at_composition` (6) |
| M32 | a door declares `composition.register` (`kind_for_action` yields it) | `TestCompositionKindIsDistinct` (2) |
| M33 | `config.resolution` no longer refuses a parameter that differs from the capability's resource | `test_a_keyed_read_resolves_the_capabilitys_resource_and_a_differing_parameter_reads_nothing` |
| M34 | a shipped module calls the reader without a kind, through an ALIASED import | first run: 0 reds — the roster matched the bare name only; the roster now resolves every `ImportFrom` alias, and M34 reddens `test_every_shipped_caller_of_the_reader_names_its_kind` (the signature makes the call a `TypeError` besides) |

## 6. Panel — round 1 (codex, cursor, gemini; executing model excluded per D-GATE-21)

Payload: the frame + join summary + 194 KB of inlined source at `cdd3450c`; every citation resolved against the tree.

| finding | who | disposition |
|---|---|---|
| **F-FORGE-01 — the mint sentinel readable off every capability via `_minted[0]`; `verify` never required the type; one capability forges all** | all three | **CONFIRMED (reproduced) and FIXED in-phase** (`81b6f1c7`): the record moved into a module-private identity-keyed table; `verify` resolves by exact type and identity; copy/pickle refused; lint rule 3 covers the table; two new controls; M4/M25 redden them |
| register loop mints for the tenant it reads off the key (tautology) | codex HIGH, cursor | **FIXED**: `register_manifest_entries(..., tenant=)` required; foreign keys refused before minting; M28 |
| F-READ-01..04 — cross-tenant list/resolve after an allow | cursor HIGH | **CONFIRMED and FIXED**: `within_tenant`, `absent`; agent/config/skill routes; M26/M27 |
| F-ROSTER-01 — two allow-listed modules never mint | cursor MEDIUM | **FIXED**: roster = five callers |
| F-SCOPE-01 — `_SENTINEL` importable from `examples/`/`tools/` (lint scope) | cursor HIGH | **PARTLY MOOT after F-FORGE-01** (the sentinel no longer confers anything); the table's name is out of scope the same way — recorded as a limitation (below) |
| F-KIND-01 — composition `Register` is the door's `ConfigRegister` by identity | cursor MEDIUM, codex | **RULING** (`D-IMPL-354` addendum): the panel recommends a distinct `CompositionRegister` kind |
| F-ATTEST-01 — composition `decision_id` is a self-hash, attestation not authorization | codex MEDIUM, cursor LOW | **RULING** (`D-IMPL-354` addendum) |
| no composition-time skill grants | all three | agreed; `GrantNotInForce` stays |
| `authorized_from_request` kind-less overload returns `Authorized[ActionKind]` | gemini LOW, cursor | advisory; no route uses it; recorded |
| `execution_id` / `DerivedWrite.name` caller-influenced within a tenant | gemini HIGH | **REJECTED as a defect**: `execute` refuses an existing execution id; both ids are the tenant's own namespace under the capability's tenant; `DerivedWrite.name` is chosen by SDK mechanism, not the wire |
| sabotage gap: constant composition `decision_id` | codex | **REJECTED** — M23 reddens an existing control |
| sabotage gap: drop the `principal` check | gemini | **REJECTED** — M24 reddens two existing controls |
| sabotage gap: S-FORGE | cursor | **ACCEPTED** — it was the CRITICAL; now M25 |

## 7. Panel — round 2 (scoped re-review of the fixes, at `81b6f1c7`)

Payload: the round-1 findings and their fixes, 107 KB of inlined source at `81b6f1c7` (capability, grants, the register
loop, the read routes, the lint rule, the new controls) and five scoped questions.

| finding | who | disposition |
|---|---|---|
| the three round-1 fixes (sentinel off the instance, register loop `tenant=`, read routes) hold; both round-1 rejections verified (each named what it re-read) | all three | recorded |
| **F-FORGE-02 — the issuance table is a module global reachable by introspection** (`verify.__globals__`, `vars(sys.modules[...])`, `gc.get_referrers`) without naming it; an exact-type instance inserted there is honored; equally, the sentinel via `Authorized.__init__.__globals__` | codex (CRITICAL), cursor (CRITICAL), gemini | **CONFIRMED (measured) — RULED OUTSIDE THE THREAT MODEL (Dave, 2026-09-25).** Arbitrary code already executing inside the same interpreter is outside `D-IMPL-353`; the claim is that governed served surfaces cannot mint, forge or use a protected capability for the wrong kind, resource or tenant. Stated in `StateWriteToken`'s words in `ccf.authz.capability`; no hiding machinery added; residual R2 below |
| F-COMP-01 — `ccf.products.resolver._mint_register_at_composition` still reads its tenant off the key | cursor HIGH | **CONFIRMED — NOT fixed at the join; a RULING** (§8 item 10). The same fix was tried (tell the mint the fabric's tenant, refuse any other) and 159 tests went red: `ProductClassDeclaration.max_ttl_key` is authored inside the declaration and is not tenant-keyed by any enforced grammar (fixtures name `tenant-fixture/max-ttl` under other tenants; cp-05's frozen declaration names `cp-05/product/…/max-ttl` under `cp-05-demo`), so the MAX_TTL artifact registers under a pseudo-tenant segment two deployments could share. Reverted to the pre-panel behavior; pinned by `tests/products/test_resolver_composition_tenant.py` so the ruling's implementation turns it red |
| F-READ-05 — `skill.grant` resolved a caller-named `definition_key` before the ledger's tenant binding (an existence oracle through a write door) | codex HIGH, cursor advisory | **CONFIRMED and FIXED**: `within_tenant` before the resolve, the absent 404, no audit `resolve` of the foreign key; M30 |
| `__reduce__` refusing pickle | codex, cursor, gemini | no legitimate SDK path serializes a capability (crossproc children re-mint in their own process); a future worker pool must re-decide at the gate — by design (§1.5g) |
| `tests/composition.py::composition_register` reads the tenant off the key | cursor | test helper; the `http_api` spelling already takes `tenant=`; noted |


## 7a. The distinct composition kind (ruled 2026-09-25, done inside D-IMPL-353)

`CompositionRegister` (`composition.register`) replaces the door's `Register` on every composition path: `boot`, the
config loader's register loop, the resolver's own two registrations, the MCP product door's registration, the test
recipe helpers. One new kind; one mint path (`mint_at_composition`, whose overloads and runtime check now refuse the
door's `Register`/`ConfigRegister`); the same static tooth (`RegisterAuthority`, `SkillCatalog.register`,
`ControlPlaneInvalidationSink` name it; the static control `tests/authz/static_controls/composition_kind.py` marks the
door kind as the type error); the same runtime tooth (`verify` by identity: a composition capability is not a
`ConfigRegister` one and vice versa; `kind_for_action` refuses `composition.register` by name, so `mint()` cannot
produce it; the registry's `REGISTER_KINDS` admit it beside the three door kinds with the same one tenant-segment
check). Controls: `tests/authz/test_capability.py::TestCompositionKindIsDistinct` (three), the roster and static
tests updated; severings M31 (runtime check gone) and M32 (a door declares it) redden them. Fragment entries: eight,
in `353-09-the-join.md`.

## 7b. Residuals (explicit; none is hidden beside a green gate)

| # | residual | where it is visible |
|---|---|---|
| R1 | **composition key grammar** — max-TTL resource identity (`ProductClassDeclaration.max_ttl_key`) is not tenant-keyed by an enforced grammar; the resolver's composition root mints `CompositionRegister` for whatever segment the declaration names. Ruled: not retuned in this phase; cp-05 stays frozen | `tests/products/test_resolver_composition_tenant.py` pins the current behavior and flips when ruled; `D-IMPL-354` ruling (2) |
| R2 | **arbitrary in-process Python introspection** of the module-private issuance table / sentinel (F-FORGE-02) — outside the threat model by ruling; the process is the boundary | `ccf.authz.capability` module docstring ("Scope, ruled"); `D-IMPL-354` ruling (1) |
| R3 | the authorization lint's tree scope is `src/` + `runtime/`; `examples/` and `tools/` may name the private names, register a raw FastMCP body, or pass a weak authority — examples are frozen specimens | `tools/lints/__main__.py::RULE_TREE_SCOPE`; §9 item 1 |
| R4 | SEC353-J-01 — FastMCP drops unknown wire arguments rather than refusing them (HTTP refuses via `extra=forbid`) | `tests/mcp` assert no effect; ruling owed |
| R5 | SEC353-J-02 (half) — a producer that REFUSED by error at its tenancy floor reads `producer-unavailable` in the child-admission row (the client classification itself is fixed) | `tests/products/test_d_impl_342_producer_refusal_evidence.py::test_c_a4a_a_door_refusal_whose_claims_fail_carries_no_producer_refusal` asserts the vocabulary and says so; ruling owed |
| R6 | **CLOSED by construction (pre-merge check).** `authorized_from_request(request, *, kind)` — `kind` is a required keyword; the kind-less overload is gone, so no HTTP route, MCP route, HITL path, door or dereference can reach a kind-less read (the MCP wrapper and the dereference never import the reader; only the six route modules do). Roster: every shipped call in `runtime/` and `src/` names its kind (`test_every_shipped_caller_of_the_reader_names_its_kind`, an AST walk, ≥20 calls) | `runtime/ccf_runtime/http_api/grants.py`; severing M34 |
| R7 | `open_product(approval_sink=)` is vestigial now that the road requests no grant | ruling owed on the paved road's posture (panel: keep) |
| R8 | two spellings of the test recipe helper (`tests/composition.py`, `tests/http_api/composition_authority.py`) | test infrastructure |
| R9 | `register_manifest_entries` requires `tenant=`: the frozen `cp-20` deployment's direct call raises `TypeError`. **Carried (pre-merge check):** not reachable from a governed served path — it is a `build_children=` hook that runs inside `open_product` at composition, in-process; its qualification exposure is the estate leg (`tests/examples/test_cp_20_*.py`, `postgres`+`fluree`, `CCF_CP_20_*`), where cp-20's open is already red independently by `SEC353-G-06` (the facade self-grants through `ledger.request(…, actor=)`, the posture D-IMPL-353 removed — no keyword repairs it). Not repaired; the required arguments are not weakened | gap ledger `SEC353-G-05` / `G-06` |
| R10 | 25 `tests/examples` reds, all pre-existing at the census base, 0 new | gap ledger, §10 |
| R11 | **CLOSED, non-defect (pre-merge check): one resource source.** For a `ResourceBinding.query(name)` route the gate reads `scope["query_string"]` once, decodes it latin-1, parses it with `parse_qs(keep_blank_values=True)`, requires exactly one non-blank value or denies before minting, and mints `authorized.resource` from that value; the router's parameter is Starlette's `QueryParams(scope["query_string"])` — `parse_qsl(latin-1-decoded, keep_blank_values=True)` over the same bytes with the same stdlib decoder; the gate is the app's only middleware (`add_middleware` once), so nothing rewrites the scope between mint and handler. The handles no longer rely on the argument: `agent.declaration`/`versions`, `config.keys`/`versions`/`resolution` and `workflow.execution` resolve `authorized.resource` and refuse a differing parameter before the first read. Negative control: `test_a_keyed_read_resolves_the_capabilitys_resource_and_a_differing_parameter_reads_nothing` (calls the endpoints directly with a capability for one key and a parameter naming another — a state no wire request can produce — and asserts nothing is read); severing M33 reddens it | routes `agent.py`, `config.py`, `workflow.py` |

## 7c. Panel — final round (Dave's one question, at `e385df29`)

> *Find a governed served route that reaches a protected handle without a valid authorization mint for that exact kind + resource + tenant.*

Payload: the brief with the ruled limit and the named residuals, 200 KB of inlined source (the capability module, the gate, the reader, the MCP wrapper, HITL, execute/resume, the factory, every registry/state/artifact/grant handle, the governed dereference, every composition mint site, the six route modules, the lint).

| reviewer | answer | disposition |
|---|---|---|
| codex | **not found** — walked the HTTP mint path, the reader, the MCP path, every protected handle's `verify`, and the tenant/resource bindings; counted the ruled limit and the named residuals as such | CLEAR |
| cursor | **CLEAR** — walked the same; considered and RETRACTED four candidates with what it re-read (keyed GETs use `key` not `authorized.resource`; `experience.get_replay_record` drops the capability before a deployment seam; `invoke_agent` under `workflow.invoke`; product doors' entitlement plane); one optional hardening | CLEAR; the hardening is residual R11 |
| gemini | claimed a bypass: a `DerivedWrite` payload steers `authorized_write_target` to a class/name the capability was not minted for | **REJECTED, measured**: with a store declaring nothing the derived branch refuses by name (`ArtifactWriteRefused: a derived write names class 'classB', which this store does not declare mechanism-written`); with the class declared under `ReplayMint` the `ArtifactWrite` capability dies at `verify_any` (wrong kind). And no served route can present a `DerivedWrite`: the HTTP and MCP artifact doors pass the wire body (a JSON value) to `store.put`; every `DerivedWrite` constructor in the tree is an SDK mechanism writer |

No served-surface defect was confirmed in the final round; nothing was fixed after `e385df29`.

## 7d. Pre-merge check (Dave, 2026-09-25): R6 and R11 resolved, R9 carried

- **R6 — kind-less reader overload:** no governed served path reached it (all 21 shipped calls named `kind=`; the MCP wrapper, the dereference and the HITL transport never import the reader), and it is now unreachable by construction — the overload is removed and `kind` is a required keyword. Control: the signature test and the AST roster; severing M34.
- **R11 — keyed HTTP read, one resource source or two:** one, structurally (the statement in the R11 row above); and the handles now read the capability's resource and refuse a differing parameter, with a wrong-resource negative control; severing M33.
- **R9 — cp-20's direct register call:** not reachable from a governed served path; its only qualification exposure is the estate leg, where the same open is already red by `SEC353-G-06`; carried, arguments not weakened.

## 8. Rulings owed to Dave

1. **`D-IMPL-354` composition authority** — accept (A) as implemented, or rule (B)/(C); the panel's unanimous
   recommendations: a distinct `CompositionRegister` kind; the composition `decision_id` named as attestation (or a
   registry-side presence check); no composition-time grants.
2. **Bare-key confinement** (`namespaced_key`): a key under another prefix is placed under the deployment's tenant
   rather than refused — chosen because a section label may contain `/`; confirm.
3. **SEC353-J-01** — FastMCP drops unknown wire arguments instead of refusing them (recorded; hardening = a strict
   argument model at registration).
4. **SEC353-J-02** — the client re-wrap is fixed; the child-admission row vocabulary still reads `producer-unavailable`
   for a producer that REFUSED by error (`SEC-018` at its tenancy floor); a `producer-refused` reason is the proposal.
5. **D-16** — a `SignedPrincipalBinding` now verifies against the door-minted `action_time` (HITL-DOOR).
6. **MCP blob split** (governed evidence classes via the dereference, other classes tenant-scoped) — confirm.
7. **`invoke_agent` action id** (provisional `workflow.invoke`).
8. **`WorkflowTenantMismatchError` → 404 byte-identical to absent** (and now the read routes' foreign key → absent).
9. **The paved road cannot grant** (`GrantNotInForce`) — confirm the posture (panel: yes).
10. **`max_ttl_key` is not tenant-keyed (F-COMP-01):** rule whether `ProductClassDeclaration.max_ttl_key` must be in the
    `{tenant}/{class}/{name}` grammar (as `D-IMPL-343` R-2 rules for an agent's refs — cp-05's frozen declaration
    then needs a ledger row) or whether the loader places it; until then the resolver's composition root mints
    `Register` for whatever segment the declaration names.
11. **In-process introspection (F-FORGE-02):** rule that arbitrary code inside the fabric's interpreter is outside the
    capability model's threat model (the process is the boundary; the lint keeps the private names out of first-party
    code), or fund a non-Python issuer. Nothing in the language closes it.
12. Carried from before: verdict→target (`D-IMPL-350`), `D-IMPL-62`, the four frozen cp-* token tables, archived scope
    mappings, `--local` revival, the examples gap ledger dispositions (`SEC353-G-01` … `G-08`).

## 9. Remaining limitations

1. **The lint's scope is `src/` + `runtime/`.** `examples/` and `tools/` may name `_SENTINEL`, `_ISSUED` or
   `_issued`, register a raw FastMCP body, or pass a weak authority; the examples are frozen specimens
   (`D-IMPL-261`). After F-FORGE-01 the sentinel confers nothing, but the table's name would — widening rule 3's tree
   scope is a one-constant change once the examples are unfrozen.
2. **The identity table is Python (F-FORGE-02, measured; RULED outside the threat model 2026-09-25).** `verify.__globals__`, `vars(sys.modules[...])` or
   `gc.get_referrers` reach the table and the sentinel without naming them, and code that can do that can replace
   `verify`. What F-FORGE-01 removed is the cheap path (one held capability → all). The module states the limit; the
   ruling on it is §8 item 10.
3. **Two spellings of the test recipe helper** remain (`tests/composition.py`, canonical, and
   `tests/http_api/composition_authority.py`, importable by a bare child process); consolidation is blocked by the
   children's `sys.path` shape. Test infrastructure only.
4. **`open_product(approval_sink=)`** is vestigial now that the road requests no grant; left for the ruling on 9.
5. **`register_manifest_entries` now requires `tenant=`** — the frozen `cp-20` deployment's direct call raises
   `TypeError` (gap ledger `SEC353-G-05`).
6. Pre-join instrument note: before `b7b30be7`, pytest in a worktree imported `main`; every lane was re-measured; the
   merged-tree runs in the main checkout are the evidence.

## 10. Examples

`docs/D-IMPL-353-EXAMPLES-GAP-LEDGER.md`: `SEC353-G-01` … `G-08`, the join's measurement paragraph (25 reds, all
pre-existing at `457552ce`, 0 new), and the roster of frozen doors reverted byte-identical to `d895d889`.
