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

**STATUS: OPEN — awaiting Dave's disposition.** Both rows carry one question and this lane does not answer it: the
seven frozen specimens §7 names — and an eighth it does not, Appendix A — do not build under Tier 1. Whether they are
unfrozen and their migration completed under `D-IMPL-261`'s third allowed reason (*"the SDK surface it legitimately
consumes was deliberately changed"*), or their door layer is retired as pre-Tier-1 evidence, is a ruling, not a lane
decision. Until it is made, the `D-IMPL-353` join must not read these rungs' green test files as coverage: their
tests skip without the estate (§ "What this lane measured"), which is exactly how the incomplete edit read green.

**Roster.** 2 rows, `SEC353-G-01..02`, append-only. Summary by disposition, then the ledger. Every id in the summary
appears in the ledger and vice versa (roster check at the end).

---

## Summary by disposition

| disposition | rows |
| --- | --- |
| **OPEN** (2) | G-01 the HTTP door does not build — `create_app` requires an `authorizer=` no example passes, and the only shipped authorizer needs a `ScopeMappingArtifact` no example declares; G-02 the loopback MCP door refuses every credential — the fork-point grants name no tenant, and under `SEC-018` a tenantless grant reaches nothing |
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
| `examples/cp-15-kyc-refresh-beneficial-ownership/server/serve.py` | +8 −1 | **no** | **no** | **still edited** (`a11d2a75`, the same `tenants=` hunk); a frozen `cp-*` specimen; calls `create_app` without `authorizer=` (`examples/cp-15-kyc-refresh-beneficial-ownership/server/serve.py::http_app`), so it is in G-01's and G-02's populations and does not build under Tier 1 either. **Needs the same ruling.** If the ruling is §7's, the revert is one `git checkout d895d889 -- <path>` by whoever owns the file; this lane did not make it because the file is outside its ownership and "while I was here" is the move `D-IMPL-261` refuses |
| `examples/hw1-companies-over-revenue/server/serve.py` | +14 −4 | yes — **stays** | no | untouched by this lane; not a `cp-*` specimen, has no HTTP door (does not call `create_app`), and its tenancy edit is what `D-IMPL-261`'s exception clause permits (§7). Not a row |

---

## Roster check

Summary: `G-01`, `G-02`. Ledger: `SEC353-G-01`, `SEC353-G-02`. Same two, same order. Appendix A rows are not gap
rows and carry no id; the one that needs a ruling (`cp-15`) is named in the STATUS paragraph as well, so it cannot be
missed by a reader who stops there.
