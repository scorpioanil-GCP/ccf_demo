# The Tier 1 Examples Gap Ledger — what `D-IMPL-353` exposed about the shipped example doors, dispositioned

**Chartered by `docs/D-IMPL-353-DESIGN.md` §7 ("Unchanged rulings"), under the ledger charter of `D-IMPL-261`
(Dave, 2026-09-05). Built by Lane EXAMPLES on `lane353-examples`, forked from `main` at `d895d889`, 2026-09-24.**
Inventory only. Nothing in `src/`, `runtime/` or `tests/` was changed while building it; no example was edited
except the seven reverts §7 rules, and no rerun was made to turn anything green. Every current-state probe below is a
read (`grep`, `git diff`, `inspect.signature`) on this branch, or a unit-level execution that touches no estate — and
each row says which of the two it is.

**Dispositions, Dave's four states, verbatim from `D-IMPL-261`:** **OPEN** — the example exposed an SDK deficiency
that remains. **FIXED-<phase>** — the example exposed it and the named phase changed the SDK to address it.
**ESTATE-LIMITATION** — the limitation belongs to Fluree/data/environment rather than CCF. **NOT-A-GAP** —
investigation established that the observed behavior was correct SDK behavior or an example/test defect.

**Scope.** A row is here only if the Tier 1 change (`D-IMPL-353`: `SEC-001`/`SEC-002` at the HTTP door, `SEC-018`
at every MCP surface) exposed it in a shipped example under `examples/`. `archive/` is a dated reference surface and
no finding is sourced from it (`D-IMPL-351`). Unless a row narrows it, the population read is **every file under
`examples/`, all types** — 19 of those files are `examples/*/server/serve.py` doors, and that smaller population is
named wherever it is the one that matters.

**STATUS: OPEN — awaiting Dave's disposition.** Every row carries one question and no lane answers it: the frozen
specimens do not build under Tier 1. Whether they are unfrozen and their migration completed under `D-IMPL-261`'s
third allowed reason (*"the SDK surface it legitimately consumes was deliberately changed"*), or their door layer is
retired as pre-Tier-1 evidence, is a ruling, not a lane decision. Until it is made, the `D-IMPL-353` join must not
read these rungs' green test files as coverage: their tests skip without the estate (§ "What this lane measured"),
which is exactly how the incomplete edit read green.

**Rows `SEC353-G-03..06` were added at the join (Lane J-TESTS, `lane353-j-tests`, forked from the join base
`457552ce`, 2026-09-24).** They record what Lane HANDLES' `D-IMPL-353` §1.2 handle signatures do to every frozen
example that constructs its own artifact store (G-03), its own replay and query-pin writers (G-04), registers its own
Control Plane entries (G-05), or requests its own skill grant (G-06). Their population is wider than G-01/G-02's: it
reaches cp-00 through cp-14, dr-01, hw1 and s1-00/s1-01, not only the eight doors. Two example tests were quarantined
under G-05 with an `xfail(strict=False)` mark and nothing else (§ "What Lane J-TESTS measured"); no example, test
intent, prose or expected output was changed. G-06 additionally names a question the design has not answered: a
deployment's own boot-time skill grant is neither a door decision nor one of the two composition kinds
(`D-IMPL-354`), so there is currently no sanctioned way for cp-20's facade to do what it does.

**Roster.** 6 rows, `SEC353-G-01..06`, append-only. Summary by disposition, then the ledger. Every id in the summary
appears in the ledger and vice versa (roster check at the end).

---

## Summary by disposition

| disposition | rows |
| --- | --- |
| **OPEN** (6) | G-01 the HTTP door does not build — `create_app` requires an `authorizer=` no example passes, and the only shipped authorizer needs a `ScopeMappingArtifact` no example declares; G-02 the loopback MCP door refuses every credential — the fork-point grants name no tenant, and under `SEC-018` a tenantless grant reaches nothing; G-03 the artifact store does not construct — `FileArtifactStore` requires a `write_kinds=` declaration no example makes; G-04 the replay and query-pin writers do not construct — `ReplayWriter`/`QueryPinWriter` require a composition-minted `ReplayMint` capability no example holds; G-05 every boot-time registration is refused — the registry takes the key from the capability, and the examples pass the key; G-06 cp-20's boot-time skill grant cannot be requested — `GrantLedger.request` takes the capability first and has no `actor=`, and no composition root may mint the kind it needs |
| **FIXED-<phase>** (0) | — |
| **ESTATE-LIMITATION** (0) | — |
| **NOT-A-GAP** (0) | — |

Counts are of rows, and the ids beside each count are the roster; a wrong member would show here.

---

## The ledger

Columns are Dave's (`D-IMPL-261`): `Gap ID | requirement | observed behavior | why this is an SDK/estate issue |
evidence | disposition | phase fixed / target phase`.

| Gap ID | requirement | observed behavior | why SDK / estate | evidence | disposition | phase |
| --- | --- | --- | --- | --- | --- | --- |
| `SEC353-G-01` | Each rung with an HTTP door builds it over the same opened product, tokens and recorder as its MCP door — "the same product over HTTP" (representative: `examples/cp-16-abs-securitization-surveillance/server/serve.py::http_app`; the other seven bodies are the same call) | `runtime/ccf_runtime/http_api/app.py::create_app` now takes a **required, keyword-only** `authorizer: TenantAuthorizerProtocol` with no default. The eight `http_app` bodies pass `auth=`, `product_entitlement=`, `perspective_resolver=`, `refusal_recorder=` and **no `authorizer=`**. **Executed** (no estate needed): `inspect.signature(create_app).bind(deps=…, auth=…, product_entitlement=…, perspective_resolver=…, refusal_recorder=…)` → `TypeError: missing a required argument: 'authorizer'`. So each rung's HTTP door raises at build, before a route exists. **Population:** 8 of 19 `examples/*/server/serve.py` call `create_app` — `cp-15`, `cp-16`, `cp-17`, `cp-18`, `cp-19`, `cp-21`, `cp-23`, `cp-24` (`grep -rn "create_app(" examples/ --include=*.py`); the other 11 doors have no HTTP arm and are outside this row. | **SDK, deliberately changed — and the migration has a step the examples never showed.** The keyword is not the gap; what it must be bound to is. Per the `create_app` docstring the SDK ships exactly one authorizer, `runtime/ccf_runtime/authz/protocol.py::ControlPlaneTenantAuthorizer` (measured: `grep -rn "^class .*TenantAuthorizer" src/ runtime/` → the Protocol and that one class), deny-by-default, which resolves a `runtime/ccf_runtime/authz/artifact.py::ScopeMappingArtifact` (class id `ccf.scope-mapping`, `runtime/ccf_runtime/authz/artifact.py::SCOPE_MAPPING`) under a **deployment-named key at an exact pinned version**; nothing at the pinned version is a deny, and there is deliberately no permissive or dev authorizer. **No shipped example registers one:** `grep -rlE "authorizer\|ScopeMapping\|scope-mapping\|scope_mapping" examples/` → **0 files** (population: every file under `examples/`, all types). A real deployment therefore needs a scope mapping — scope string → tenants, door-declared actions, resources (`runtime/ccf_runtime/authz/artifact.py::ScopeEntry`) — authored as a deployment value, registered, and its returned version pinned into the authorizer. That obligation is real for every adopter of the HTTP door and the ladder never demonstrated it: the examples were the launch story for the door and the story was missing its authorization artifact. | `git diff d895d889 --stat -- <seven paths>` → empty (the seven are byte-identical to the fork point); the `bind` output above; the two `grep` populations above; `docs/D-IMPL-353-DESIGN.md` §7; `create_app`'s own docstring on the missing-authorizer posture (`SEC-001`, `SEC-002`) | **OPEN.** Not this lane's to rule. The choice is Dave's: **(a)** unfreeze the eight under `D-IMPL-261`'s third reason and complete the migration — each rung declares a `ScopeMappingArtifact` in its artifacts, registers it at boot, pins the returned version, passes `authorizer=`, and scopes its grants (G-02); **(b)** retire the eight HTTP doors and keep the MCP doors; **(c)** retire the door layer of these rungs as pre-Tier-1 specimens. Whatever is chosen, the change is an example edit and is made after `D-IMPL-353` closes, as the separate validation step `D-IMPL-261` prescribes — never inside the remediation | awaiting ruling |
| `SEC353-G-02` | Each rung mints four credentials, one per principal, and serves them over the loopback transport — the transport its own tests (`served` fixtures) and `cp-22`'s cross-process consumer use; three principals are entitled and the fourth is the ungranted negative control (representative: `examples/cp-16-abs-securitization-surveillance/server/serve.py::token_source`, `::open_abs_door`) | At fork-point bytes `token_source` mints `TokenGrant(client_id=…, scopes=(scope,))` and **no `tenants`**. Under `SEC-018`, `runtime/ccf_runtime/mcp/auth.py::TokenGrant` defaults `tenants` to the empty set and *"empty means no tenant, never every tenant"*. **Executed** (no estate needed): a grant of exactly that shape, verified through `runtime/ccf_runtime/mcp/auth.py::SourceBackedTokenVerifier` over a `runtime/ccf_runtime/mcp/auth.py::StaticTokenSource`, yields token claims `ccf.tenants = []` (`runtime/ccf_runtime/mcp/auth.py::TENANT_CLAIM`) and `runtime/ccf_runtime/mcp/auth.py::granted_tenants` → `frozenset()`. **Read**: every product surface the egress registers goes through `runtime/ccf_runtime/mcp/tenancy.py::TenantGuardedServer` as a tenant subject (`from_argument("tenant")`, three registrations in `runtime/ccf_runtime/mcp/egress.py`), and its guard raises `runtime/ccf_runtime/mcp/tenancy.py::TenantlessGrantRefused` before the handler's first statement when the held set is empty. So on loopback **every credential is refused for the same reason** — the three entitled and the negative control alike — and the entitlement distinction each rung exists to demonstrate never runs. **Not affected:** the stdio transport — `runtime/ccf_runtime/mcp/product_door.py::ProductDoor` states an ambient identity built by `runtime/ccf_runtime/mcp/tenancy.py::ambient_stdio_identity`, scoped to the door's own tenant (read), so a stdio child still reads what it was spawned to serve. | **SDK, deliberately changed (`SEC-018`); the example half is one field per rung, and it is still an example edit.** The Tier 1 lanes made exactly that edit — `tenants=frozenset({opened.tenant_id})`, +9 lines in each of the eight `cp-*` doors, commit `a11d2a75` (and `2ae6b3fc` for `hw1`). It is **reverted here for the seven §7 names**, on two grounds §7 states: it edited frozen specimens, and it was incomplete — alone it left G-01 standing, so the rungs still did not build. The revert is not a judgment that the edit was wrong in content; it is the ruling that the content belongs in the same disposition as G-01, made by Dave, after the remediation closes. | the executed script output above (`grant.tenants = frozenset()`; `claims['ccf.tenants'] = []`; `granted_tenants(token) = frozenset()`); `git log --oneline d895d889..HEAD -- examples/*/server/serve.py` → `2ae6b3fc`, `a11d2a75`; the guard's tenantless branch, read | **OPEN** — one ruling with G-01. **Not measured against the estate:** 0 of the `CCF_CP_*` variables are set in this environment, so the refusal is proven at the unit (`granted_tenants` on a fork-point-shaped grant) and read at the guard, not observed on a served rung. The estate rerun is the validation step that follows the ruling | awaiting ruling |
| `SEC353-G-03` | Each rung that files evidence opens its own artifact store as `FileArtifactStore(root=…)` and lets the fabric's writers file replay records, query pins and admission records into it (representative: `examples/cp-00-institutional-holders/produce.py::assemble_and_serve`, `examples/s1-00-companies-over-revenue/produce.py::assemble_and_serve`; door-side, `examples/hw1-companies-over-revenue/server/compose.py::compose`) | `src/ccf/artifacts/file_store.py::FileArtifactStore` now takes a **required, keyword-only** `write_kinds: WriteKinds` beside `root` — the deployment's declaration of which artifact classes its own mechanism writes and under which kinds (`src/ccf/artifacts/protocol.py::WriteKinds`: *"No default. Both shipped stores take `write_kinds` as a required constructor argument"*). **Executed** (no estate needed): `inspect.signature(FileArtifactStore)` → `(*, root, write_kinds)`; `.bind(root="deployment/artifacts")` → `TypeError: missing a required argument: 'write_kinds'`. So each rung raises at store construction, before any record is written. **Population:** 23 of 579 files under `examples/` (all types; 38 example directories), 25 call sites — `grep -rl "FileArtifactStore(" examples/` and `grep -rn "FileArtifactStore(" examples/ \| wc -l` — `cp-00`, `cp-01`, `cp-02`, `cp-03` (`produce.py`), `cp-04` (`produce.py`; `deployment.py`, 2 sites), `cp-05` (`deployment.py`, `produce.py`), `cp-06` and `cp-07` (`produce.py`, `server/serve.py`), `cp-08` … `cp-13` (`produce.py`), `cp-14` (`run.py`), `dr-01` (`replay.py`, 2 sites), `hw1-companies-over-revenue` (`server/compose.py`), `s1-00` (`produce.py`), `s1-01` (`spine.py`). **Not in this population:** `archive/` (12 more files; a dated reference surface, `D-IMPL-351`) and the rungs that reach a store only through `load_config_and_boot` or `open_door` — SDK composition roots, not example code | **SDK, deliberately changed (`D-IMPL-353` §1.2, "Per-class write kinds at the artifact store") — and the migration has a step the examples never showed.** The keyword is a declaration, not a flag: the replay-record class and the query-pin class under `ReplayMint`, the workflow trace under `Execute`/`Resume`, the admission-record class under `ReplayMint` (`D-IMPL-354` (b)); whatever is undeclared is the client lane under `ArtifactWrite`. No example's `ccf_config.yaml`, manifest or artifacts names such a declaration today (`grep -rl "write_kinds\|WriteKinds" examples/` → 0 files). The obligation is real for every adopter — a store whose replay class is undeclared refuses the fabric's own writer at first use, the loud boot-time failure the design wants — and the ladder never demonstrated it. One migration with G-04: the declared kinds and the capability the writer holds are the two halves of the same statement | the `inspect.signature` and `bind` output above; the two `grep` populations; `docs/D-IMPL-353-DESIGN.md` §1.2; the `WriteKinds` docstring; `tests/replay/authority.py::replay_store` for the shape a deployment states | **OPEN.** Not this lane's to rule; the choice is Dave's and it is the G-01 choice: **(a)** unfreeze under `D-IMPL-261`'s third reason and complete the migration — each rung declares its mechanism-written classes beside the store's root in its artifacts and constructs the store with them; **(b)** retire the affected rungs as pre-Tier-1 specimens. Either way the change is an example edit made after `D-IMPL-353` closes, as the separate validation step `D-IMPL-261` prescribes | awaiting ruling |
| `SEC353-G-04` | The first six product rungs hand the fabric their own replay-record and query-pin writers — `ReplayWriter(store=…, artifact_class=…)`, `QueryPinWriter(store=…, artifact_class=…)` — beside the store of G-03 (representative: `examples/cp-00-institutional-holders/produce.py::assemble_and_serve`; `examples/cp-05-credit-exposure-rollup/deployment.py::replay_writers`) | `src/ccf/replay/serve.py::ReplayWriter` and `src/ccf/replay/serve.py::QueryPinWriter` now take `(*, authorized: Authorized[ReplayMint], store)`; `artifact_class` is deleted — the class is `authorized.resource`, the evidence class the composition root minted for. **Executed** (no estate needed): `inspect.signature(ReplayWriter).bind(store=…, artifact_class="ccf.decision-replay-record")` → `TypeError: missing a required keyword-only argument: 'authorized'`; `QueryPinWriter` identical. **Population:** 6 of 579 files, 12 sites (6 + 6) — `grep -rnE "ReplayWriter\(\|QueryPinWriter\(" examples/`: `cp-00` `produce.py:448/451`, `cp-01` `produce.py:356/359`, `cp-02` `produce.py:372/375`, `cp-03` `produce.py:434/437`, `cp-04` `produce.py:692/695`, `cp-05` `deployment.py:451/452`. `cp-06` and later reach the writers through `load_config_and_boot`, an SDK composition root, and are outside this row | **SDK, deliberately changed (`D-IMPL-353` §2 P3; `D-IMPL-354` (b), PROPOSED).** `ReplayMint` has no door: it is minted only by `src/ccf/authz/capability.py::mint_at_composition`, once, at the composition root, after the decision is recorded on the audit log. A rung that builds its writers in its own `produce.py` IS a composition root and now has to make that statement itself — a step none of the six specimens shows, and one whose shape (`Register` and `ReplayMint` as the closed composition pair) is still Dave's to rule under `D-IMPL-354`. The tests do exactly this at `tests/controlplane/capabilities.py::replay_mint` and `tests/replay/authority.py::replay_writer` | the two `bind` outputs; the `grep`; `docs/D-IMPL-353-DESIGN.md` §1.6; `docs/DECISIONS.md` `D-IMPL-354` | **OPEN** — one ruling with G-03 (the store's declared kinds and the writer's capability are one migration), and blocked twice: on the ruling on the frozen rungs and on `D-IMPL-354`'s ruling on composition authority | awaiting ruling |
| `SEC353-G-05` | A rung's own compose/produce/serve registers its Control Plane entries as `registry.register(key, artifact)` or `control_plane.register_typed(key, artifact, artifact_class)` — its MAX_TTL and request-contract defaults in `produce.py`/`deployment.py` (`cp-00` … `cp-05`), its door's own entitlement policy in `server/serve.py` or `server/compose.py` (`cp-04` … `cp-07`, `cp-15` … `cp-19`, `cp-21`, `cp-23`, `cp-24`, `hw1`), a derived skill/agent chain in `cp-20`'s `deployment.py` (representative: `examples/cp-04-corporate-family-tree/server/compose.py::compose`, `examples/cp-16-abs-securitization-surveillance/server/serve.py::entitle`, `examples/cp-00-institutional-holders/produce.py::assemble_and_serve`) | `src/ccf/controlplane/registry.py::ControlPlaneRegistry` — `register(authorized, artifact)`, `register_typed(authorized, artifact, artifact_class)`, `register_versioned(authorized, artifact, artifact_class)`: **the key is `authorized.resource`** and there is no key parameter. The old call still *binds* (the key string lands in `authorized`), so the failure is not a `TypeError` but the seam's refusal at the handle's first statement. **Executed** (no estate needed): `ControlPlaneRegistry().register("acme-bank/max-ttl/default", {"seconds": 300})` → `CapabilityBypassError: no genuine capability accompanies this call; the handle is reached only through the authorization gate (D-IMPL-353 §1.1)`; `register_typed("acme-bank/hitl/policy", {…}, HITL_POLICY)` → the same; `registry.versions(…)` → `()` for both keys — nothing was registered. **Observed on a served rung too**, not only at the unit: `tests/examples/test_cp_04_two_callers.py::test_an_unentitled_principal_gets_a_recorded_shell_and_not_an_error` fails with this exception inside `compose.py::compose` (run without the CI marker and without estate variables — cp-04's door raises before the estate is consulted). **Population:** 28 sites in 21 of 579 files — 15 `.register(`, 13 `.register_typed(`, 0 `.register_versioned(` (`grep -rnE "\.register(_typed\|_versioned)?\(" examples/`; each of the 28 lines was read and is a `ControlPlaneRegistry` call — none is an operator-registry or skill-catalog registration): `cp-00` (`produce.py` ×2, `deployment.py`), `cp-01`/`cp-02`/`cp-03` (`produce.py` ×2 each), `cp-04` (`produce.py` ×2, `server/compose.py`), `cp-05` (`deployment.py` ×2, `server/serve.py`), `cp-06`, `cp-07`, `cp-15`, `cp-16`, `cp-17`, `cp-18`, `cp-19`, `cp-21`, `cp-23`, `cp-24` (`server/serve.py`), `cp-20` (`deployment.py` ×2), `hw1-companies-over-revenue` (`server/compose.py`) | **SDK, deliberately changed (`D-IMPL-353` §1.2 table row 1; §1.5f "the target is the capability's, never the caller's").** A rung registering at boot is a composition root: under `D-IMPL-354` (a) (PROPOSED) it mints `Register` for ONE key per registration through `mint_at_composition`, after recording the decision on the audit log — the obligation `src/ccf/deployment/manifest.py::register_manifest_entries` carries for manifest entries and no example shows for the registrations it makes in its own code. Whether `Register` at composition is the intended shape is Dave's ruling under `D-IMPL-354`; until then the examples have no sanctioned form to migrate to | the executed refusal and the empty `versions`; the `grep` and the per-line read; `docs/D-IMPL-353-DESIGN.md` §1.2; `docs/DECISIONS.md` `D-IMPL-354`; the two quarantined node ids | **OPEN** — same ruling as G-01. **Quarantined (marks only, `D-IMPL-261`):** `tests/examples/test_cp_04_two_callers.py::test_an_unentitled_principal_gets_a_recorded_shell_and_not_an_error` (cp-04's own door); `tests/examples/test_s1_00_config_equivalence.py::test_hw1_eight_documents_register_at_identical_content_addresses_in_both_forms` — this one fails at the TEST's own two `register_typed(key, …)` calls (its lines 176 and 201), the same retired shape; the mark says so, and its repair is a test edit under `D-IMPL-261`'s third reason after the ruling, not before | awaiting ruling |
| `SEC353-G-06` | `cp-20`'s consumer facade requests a governed skill grant for its derived agent when the product opens: `ledger.request(SkillGrant(…), definition=agent, actor=agent.name)` (`examples/cp-20-syndicated-lending-co-lender/deployment.py::FederatedChildren`) | `src/ccf/skills/grants.py::GrantLedger` — `request(authorized: Authorized[SkillGrant], grant, *, definition)`: the capability is first and **`actor` is deleted** (the actor is `authorized.principal`). **Executed** (no estate needed): binding cp-20's exact shape, `request(SkillGrant(…), definition=agent, actor=agent.name)` → `TypeError: missing a required argument: 'grant'` (the `SkillGrant` lands in `authorized`); with a capability supplied, `actor=` → `TypeError: got an unexpected keyword argument 'actor'`. **Population:** 1 of 579 files, 1 request site — `grep -rnE "GrantLedger\(\|ledger\.request\(\|\.revoke\(" examples/` → `deployment.py:494` (the ledger's construction), `:499` (the request), 0 revokes. For the denominator: `grep -rn "\.request(" examples/` returns 19 lines, 18 of which are `deployment.request(…)` — a product-request builder, not the ledger — so a count of "grant requests" built from that grep is not a population this row recognizes | **SDK, deliberately changed (`D-IMPL-353` §1.2, last row) — and different in kind from G-03 … G-05.** `SkillGrant` is a DOOR kind (`skill.grant`), minted by `mint()` from an allowed authorizer decision; a composition root may not mint it — `src/ccf/authz/capability.py::COMPOSITION_KINDS` is exactly `(ReplayMint, Register)` and `mint_at_composition` refuses anything else. cp-20's facade grants a skill to itself at open, with no authorizer and no door; under the design as built there is no sanctioned way for example code to do that at all. Not a rung defect: the first place the ladder asks how a deployment's own boot-time grants are authorized | the two `bind` outputs; the `grep`; `COMPOSITION_KINDS`; `docs/DECISIONS.md` `D-IMPL-354` items (2) and (3) | **OPEN** — needs its own answer inside the `D-IMPL-354` ruling (a boot-time grant is neither a door decision nor one of the two composition kinds), then the example edit after `D-IMPL-353` closes | awaiting ruling |

---

## What this lane measured, and what it did not

**The revert (§7).** `git checkout d895d889 -- <the seven paths>`, then the proof:

```
$ git diff d895d889 --stat -- examples/cp-16-abs-securitization-surveillance/server/serve.py \
    examples/cp-17-mnpi-wall-enforcement/server/serve.py examples/cp-18-ib-opportunity-synthesis/server/serve.py \
    examples/cp-19-aml-typology-match/server/serve.py examples/cp-21-large-exposure/server/serve.py \
    examples/cp-23-portfolio-early-warning/server/serve.py examples/cp-24-portfolio-what-if/server/serve.py
(no output)
```

and per file, `git diff --quiet d895d889 -- <path>` → exit 0 for all seven. Byte-identical to the fork point.

**The tests.** The 21 files under `tests/examples/` named `test_cp_16_*`, `test_cp_17_*`, `test_cp_18_*`,
`test_cp_19_*`, `test_cp_21_*`, `test_cp_23_*`, `test_cp_24_*`, run with
`PYTHONPATH=src:runtime python -m pytest <the 21> -q -rs -p no:randomly`:

| rung | files | collected | passed | skipped | failed | error | skip reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cp-16 | 4 | 41 | 1 | 40 | 0 | 0 | `CCF_CP_16_*` (6 estate variables) unset |
| cp-17 | 4 | 24 | 0 | 24 | 0 | 0 | `CCF_CP_17_*` (7 estate variables; 10 of the 24 also name the 4 `CCF_CP_17_TOKEN_*`) unset |
| cp-18 | 3 | 18 | 0 | 18 | 0 | 0 | `CCF_CP_18_*` (7 estate variables) unset |
| cp-19 | 4 | 19 | 0 | 19 | 0 | 0 | `CCF_CP_19_*` (7 estate variables; 2 of the 19 also name the 4 `CCF_CP_19_TOKEN_*`) unset |
| cp-21 | 2 | 49 | 0 | 49 | 0 | 0 | `CCF_CP_21_*` (6 estate variables) unset |
| cp-23 | 2 | 30 | 2 | 28 | 0 | 0 | `CCF_CP_23_*` (4 estate variables) unset |
| cp-24 | 2 | 26 | 0 | 26 | 0 | 0 | `CCF_CP_24_*` (4 estate variables) unset |
| **total** | **21** | **207** | **3** | **204** | **0** | **0** | every skip is the rung's `estate` fixture (e.g. `tests/examples/test_cp_16_surveillance.py::estate`) finding its variables unset; with `CCF_REQUIRE_ESTATE=1` (`tests/examples/test_cp_16_surveillance.py::ESTATE_REQUIRED`) each would fail instead of skipping |

The three that passed touch no estate and no door:
`tests/examples/test_cp_16_surveillance.py::test_tranche_ordering_is_by_seniority_and_not_by_identifier`,
`tests/examples/test_cp_23_sabotage.py::test_the_ruled_law_differs_from_max_member_debt_in_general`,
`tests/examples/test_cp_23_sabotage.py::test_canonicalization_is_the_deployments_and_is_order_insensitive`.
**204 skips is not 204 passes**, and it is not a statement about G-01 or G-02 in either direction: it is the reason
the Tier 1 edit read green. Read `passed`, never `collected`.

**Not done here, by design.** No estate run (0 `CCF_CP_*` variables set; standing one up for seven rungs is the
validation step, not the ledger step). No test weakened, marked or quarantined. No edit to any example outside the
seven, including the eighth `create_app` caller in Appendix A.

---

## What Lane J-TESTS measured at the join, and what it did not

**Where the examples' tests are collected in CI** (read, not assumed): three routes and no fourth. (1) `make
ci-quick-suite` → `pytest tests -q -m "not postgres and not chroma and not neo4j and not mongo and not fluree"`, which
includes `tests/examples/` (`pyproject.toml` `testpaths = ["tests"]`; 106 test files there); (2) the four substrate
legs (`leg-postgres`, `leg-neo4j`, `leg-mongo`, `leg-fluree`) select the marked members of the same files against a
service container; (3) `make examples` runs `examples/hw1-harness-clients/runner/drive.py` directly — a program, not a
pytest node, so it cannot carry a mark. `make product-gates` (`tools/check_product_gates.py`) collects node ids from
`tests/examples/` with `--collect-only`; an `xfail`-marked test still collects. No `examples/*/tests` directory exists
(`find examples -name 'test_*.py'` → 0 files).

**Run 1 — the CI shape, without estate variables** (`PYTHONPATH=.:src:runtime python -m pytest tests/examples -q -m
"<the marker expression>" -p no:randomly`, 0 `CCF_CP_*` variables set): **9 failed, 4 errors, 770 passed, 57 skipped,
1195 deselected.** Every red was attributed to the frame that raised, and **none is at a frozen example's own
signature site**, so none was quarantined from this run: 2 are pre-existing and unrelated
(`tests/examples/test_artifact_schema_headers.py` on `archive/examples/05-workflow-hitl` and `06-decision-replay` — red
at `d895d889` on `main` as well, measured by running the same two nodes there read-only); 2 F + 4 E are hw1 programs
(`runner/seed.py`, `runner/drive.py`) that stop inside `src/ccf/deployment/config.py::load_config_and_boot` →
`src/ccf/deployment/manifest.py::register_manifest_entries`, an SDK composition root the join is migrating; 3 F are
hw1's in-process door stopping inside `src/ccf/client/adapters/inprocess.py`, another composition root; 1 F is
`tests/examples/test_product_tree_import_isolation.py` importing cp-21's door, which imports
`runtime/ccf_runtime/http_api/app.py`, which still imports the retired `GovernedRecordClasses` (the runtime lane's
file). Those causes are the join's other lanes', and each is expected to move: once the composition roots land, hw1
proceeds to `server/compose.py::compose` (G-05) and then to its `FileArtifactStore(root=…)` (G-03).

**Run 2 — without the marker** (same command, no `-m`): **28 failed, 6 errors, 965 passed, 740 skipped, 224
deselected, 72 xfailed.** The 19 F + 2 E beyond Run 1: `tests/examples/test_cp_04_two_callers.py` (1 F, at cp-04's own
`compose.py::compose` — **quarantined under G-05**); `tests/examples/test_s1_00_config_equivalence.py` (1 F, at the
test's own `register_typed(key, …)` — **quarantined under G-05**); `test_s1_00_output.py` ×9, `test_cp_00_output.py`
×2, `test_cp_01_output.py` ×1 (all at `load_config_and_boot`, the composition root above — reported, not marked);
`test_cp_19_door.py` (2 E, the `app.py` import above — reported, not marked);
`test_s1_01_governed_resolver_adoption.py` ×6 (`RuntimeError: CCF_TEST_FLUREE_URL is unset` — environment, a leg-only
member, not a defect). **Quarantined node ids, complete:** the two named under G-05. Each carries
`pytest.mark.xfail(strict=False, reason="SEC353-G-05: …")` and nothing else; `test_s1_00_config_equivalence.py` gained
the one `import pytest` line the mark requires and no other change.

**Not done here, by design.** No example code, prose, configuration, expected output or test intent was changed. No
estate run. The G-03/G-04 populations were not observed on a served rung: every rung that would reach them stops
earlier today, at the composition roots named above, so their proof is the executed `inspect.signature`/`bind` at the
unit and the read of each call site. The validation rerun after the join lands is where the per-rung failure order
(G-05, then G-03, then G-04) will be observed rather than predicted.

## Appendix A — the denominator: every example server edited since the fork point

`git diff d895d889 --stat -- examples/` names **nine** files, all `server/serve.py`. §7 enumerated eight ("seven
`cp-*` plus `hw1`"). Recorded here so the miss is visible rather than resolved the easy way (`D-IMPL-353-DESIGN.md`
§0: *"The enumeration has been wrong three times in this remediation."*).

| file | drift | in §7's list | this lane's ownership | state after this lane |
| --- | --- | --- | --- | --- |
| `examples/cp-16-abs-securitization-surveillance/server/serve.py` | +9 −1 | yes | yes | **reverted**, byte-identical to `d895d889` |
| `examples/cp-17-mnpi-wall-enforcement/server/serve.py` | +9 −1 | yes | yes | **reverted** |
| `examples/cp-18-ib-opportunity-synthesis/server/serve.py` | +9 −1 | yes | yes | **reverted** |
| `examples/cp-19-aml-typology-match/server/serve.py` | +9 −1 | yes | yes | **reverted** |
| `examples/cp-21-large-exposure/server/serve.py` | +9 −1 | yes | yes | **reverted** |
| `examples/cp-23-portfolio-early-warning/server/serve.py` | +9 −1 | yes | yes | **reverted** |
| `examples/cp-24-portfolio-what-if/server/serve.py` | +9 −1 | yes | yes | **reverted** |
| `examples/cp-15-kyc-refresh-beneficial-ownership/server/serve.py` | +8 −1 | **no** (found by this lane) | **yes — at the join**, `c9da1c80`, byte-identical to `d895d889` | **reverted at the join** under the same §7 ruling (the enumeration was short by one); the lane's finding stands as written: it carried `a11d2a75`'s `tenants=` hunk; a frozen `cp-*` specimen; calls `create_app` without `authorizer=` (`examples/cp-15-kyc-refresh-beneficial-ownership/server/serve.py::http_app`), so it is in G-01's and G-02's populations and does not build under Tier 1 either. **Needs the same ruling.** If the ruling is §7's, the revert is one `git checkout d895d889 -- <path>` by whoever owns the file; this lane did not make it because the file is outside its ownership and "while I was here" is the move `D-IMPL-261` refuses |
| `examples/hw1-companies-over-revenue/server/serve.py` | +14 −4 | yes — **stays** | no | untouched by this lane; not a `cp-*` specimen, has no HTTP door (does not call `create_app`), and its tenancy edit is what `D-IMPL-261`'s exception clause permits (§7). Not a row |

---

## Roster check

Summary: `G-01`, `G-02`, `G-03`, `G-04`, `G-05`, `G-06`. Ledger: `SEC353-G-01`, `SEC353-G-02`, `SEC353-G-03`,
`SEC353-G-04`, `SEC353-G-05`, `SEC353-G-06`. Same six, same order; G-03 … G-06 were appended at the join and the
STATUS paragraph names them. Appendix A rows are not gap
rows and carry no id; the eighth door (`cp-15`) is named in the STATUS paragraph as well and was reverted at the join (`c9da1c80`), so it cannot be
missed by a reader who stops there.
