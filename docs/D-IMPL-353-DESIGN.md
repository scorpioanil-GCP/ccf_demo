# D-IMPL-353 — Authorization as an invariant, not a feature

**Status:** DESIGN, awaiting Dave's approval. Amends Tier 1 of the 2026-09-23
security remediation after the close panel (Fable, Codex, Cursor; `D-IMPL-352`)
**rejected it for amendment**.

**Date:** 2026-09-24. **Author:** the model that designed the original, which is
the point of writing this one down.

---

## 0. What the panel found, in one sentence each — all verified against the tree

| # | Finding | Verified how |
|---|---|---|
| P1 | The HTTP gate reads `grant.tenant`; the shipped `TokenGrant` has `tenants: frozenset` and no `.tenant`. **Every real credential is refused.** The suite is green because a test-only subclass adds the missing field. | reproduced: `tenant_of_grant(TokenGrant(tenants={"acme-bank"}))` raises |
| P2 | A caller authorized for tenant B invokes tenant A's workflow key; the gate decides on the grant, the engine keys the execution on `workflow.definition.tenant` — **the artifact's self-declared tenant**. Filed under A, HITL event enqueued in A's queue. Same on `/agent/declarations`. | read: `routes/workflow.py:113`, `engine.py:370` |
| P3 | The store guard for forged replay records defaults to `NOTHING_GOVERNED`; `GovernedWriteHandle` is constructed **nowhere** outside its own docstring; the fabric's own writers never mint. **Inert in every shipped composition.** | grep: 0 constructions in `src/`, `runtime/`, `examples/` |
| P4 | The MCP HITL door's authorizer is `TenantAuthorizerProtocol \| None = None` with `if authorizer is None: return`. Mandatory on HTTP, optional on MCP, same action. | read: `hitl_server.py:226, 304` |
| P5 | MCP artifact blob/meta resources are `untenanted()` and call `store.get(content_address=...)` directly. Any verified bearer of any tenant reads any tenant's bytes by hash. HTTP's sibling goes through `govern_dereference`. | read: `artifact_server.py:250, 275, 279` |
| P6 | `POST /hitl/actions` derives `subject_id` from the grant and copies `assurance_level`, `method`, `identity_provider_ref`, `session_ref`, `action_time` from the **body**. A step-up-MFA claim written by the client. | read: `routes/hitl.py:174-178` |
| P7 | The `authz_decision` audit event carries action and matched tenant pattern; **not the resource, not the matched resource pattern, not which axis refused**. The gate's own refusal text promises otherwise. | read: `authz/protocol.py` `_audit(...)` |
| P8 | Eight example servers were edited by this branch (+9 lines each: `tenants=`) and none passes the now-required `authorizer=`, so each raises `TypeError` at build. Their tests skip without the estate, so it reads green. | `git diff --stat`, grep `authorizer=` → 0 |
| P9 | `TenantGuardedServer` exposes the raw `FastMCP`; `unguarded_surfaces()` is a test sweep, not a construction-time refusal. | read: `mcp/tenancy.py` |
| P10 | `hitl.queue.read` + `hitl.action.submit` opens every gate in a tenant, through the unstamped fallback leg kept to preserve HTTP tests. `policy_ref` has zero readers. | read: `engine.py::_gate_authority`, grep |

Corrections to numbers I reported: `app.routes` sees **5** of 30, not 6; the
"0 `filterwarnings` repo-wide" claim is true only for the population the test
measures; the branch is 34 commits / 122 files, not 32 / 117.

---

## 1. The structural diagnosis

This project enforces five invariants with CI teeth — single-writer,
composition-preservation, the three validation gates, No-Hardcoding, zero
harness imports. Each has a lint or structural test that turns a violation into
a build failure.

**Authorization was never one of them.** It was built as an option a component
could take — a keyword a router might receive, a check a tool body might
remember, a handle a writer might hold. That is the design error, and it
recurred **five times** in this remediation: the gate asking the caller's
handle (Tier 0), the MCP tenant check opening `if authorizer is None: return`,
the CLI sending a credential only when configured, the store guard inert by
default, and now the engine trusting the artifact's tenant over the grant's.

Every one is the same defect: **a guard whose applicability is decided by
something other than the guard.**

The fix is therefore not eleven patches. It is to give authorization the status
the other five invariants already have — **enforced by construction, with a lint
that makes the optional arm a build failure** — and then to close the specific
holes under that discipline.

---

## 2. The design — seven parts

### Part A — One tenant, one spelling, one reader  *(closes P1)*

- `TokenGrant.tenants: frozenset[str]` is the **only** representation. The
  singular `.tenant` is deleted from every reader. `TenantedTokenGrant` is
  deleted from the test fixture so the fixture cannot pass where a deployment
  fails.
- One shared reader, `tenants_of_grant(grant) -> frozenset[str]`, used by the
  HTTP gate, the MCP wrapper and the engine. Empty set → refuse. Empty *string*
  → refuse (closes the HTTP/MCP asymmetry Codex found).
- **The acting tenant for a request is selected, never supplied:**
  - the request names a tenant (path segment, resource key, artifact) → it must
    be a **member** of `grant.tenants`, else refuse;
  - the request names none and the grant has exactly one → that one;
  - the request names none and the grant has several → **refuse as ambiguous**.
    The gate will not pick.

### Part B — The tenant a write ACTS ON is bound to the tenant the grant AUTHORIZED  *(closes P2)*

At **two** layers, because P2 was a single-layer check that the second layer
undid.

- **At the door:** every mutating route compares the tenant its write targets —
  the artifact's declared tenant, or the key's tenant segment — with the acting
  tenant from Part A, the way `routes/skill.py` already does. Mismatch is a 403
  naming both, never a redirect.
- **At the engine:** `WorkflowEngine.execute` and `resume` take `acting_tenant`
  as an explicit parameter and refuse a handle whose `definition.tenant`
  differs. The state key is derived from `acting_tenant`, never from the
  artifact. This is the same repair Tier 0 made to `resume` — take the
  predicate from what was authorized, not from what the caller presents —
  applied to the branch it missed.
- The Control Plane registry gains no tenancy (that is its own cycle, `B` of the
  original design). What it gains is that **no door can register or invoke an
  artifact whose declared tenant is not the caller's.**

### Part C — Governed writes are governed by construction  *(closes P3)*

- `ReplayWriter`, `ReplayRefusalRecorder` and every other component that
  **knows** it writes a governed class take a `GovernedWriteHandle`, **not** a
  bare `ArtifactStoreProtocol`. The type system refuses the bare store.
- `create_app` (and the MCP builders) refuse at boot on the mismatch **in both
  directions**: a recorder naming a replay class over a store that governs
  nothing; a store governing a class no writer holds a handle for.
- `NOTHING_GOVERNED` stays as the Protocol default (test doubles need it), but
  no shipped composition can reach a served door with it — the boot refusal is
  the gate, the default is not.

### Part D — MCP parity with HTTP  *(closes P4, P5, P9)*

- The MCP HITL door's authorizer becomes **required**. Same action, same
  posture as HTTP.
- The blob/meta artifact resources go through the same `govern_dereference`
  the HTTP GET uses. There is no untenanted read of artifact bytes.
- `TenantGuardedServer` runs `unguarded_surfaces()` **at construction** and
  refuses; the raw `FastMCP` is not exposed for registration. A body registered
  behind the wrapper is a boot failure, not a test finding.

### Part E — The approval record is server-attested  *(closes P6)*

`POST /hitl/actions` and the MCP submit derive **every** field of the
`HumanPrincipalBinding` from the verified grant or the server — `subject_id`,
`identity_provider_ref`, `method`, `assurance_level`, `session_ref` from the
token's verified claims; `action_time` from the server clock. The body may
carry `product_content_hash` (what the human saw) and `annotation`. Nothing
else. A caller-typed assurance level is deleted from the contract, so it is
unrepresentable, not refused.

*(`action_time` from the server clock is the first, narrowest use of the fabric
clock `SEC-008/010` will generalize in Tier 2. It is taken here for this one
field because a caller-typed time on an approval record is an audit defect
independent of the temporal-integrity work.)*

### Part F — The deny audit says what was denied  *(closes P7)*

`AuthzDecisionAuditEvent` gains `authz_resource`, `authz_matched_resource_pattern`
and `authz_failing_axis` (`tenant` \| `action` \| `resource`). The gate's refusal
text already promises this; the event now delivers it.

### Part G — THE LINT: authorization joins the enforced invariants  *(closes the habit)*

A new CI check, `tools/lints/authorization_invariant.py`, alongside the other
five. It refuses:

1. Any `@router.<verb>` handler in `runtime/` without `@authorizes` — before
   boot, not at boot.
2. Any `@server.tool` / `@server.resource` registration in `runtime/` outside
   `mcp/tenancy.py`'s wrapper.
3. **Any parameter of an authority type with a default of `None`** in
   `runtime/` — `TenantAuthorizerProtocol | None = None`,
   `HttpAuthProtocol | None = None`, `GovernedWriteHandle | None = None`, and
   their kin. This is the pattern that produced P4 and D-IMPL-73 and it becomes
   a build failure by name.
4. Any read of a tenant from a request body, query string or artifact field on
   a mutating route that is not compared against `tenants_of_grant`.

Rules 1–3 are exact and cheap. Rule 4 is heuristic and will need a reviewed
allowlist in the `D-08` shape; it exists so the class is *named* in CI even where
it cannot be *proven* there.

---

## 3. What this does NOT do — kept out deliberately

- **SEC-006 approver eligibility** (four-eyes, `policy_ref` enforcement). Tier 2.
  Named in the panel as a bank blocker; it is, and it is a different mechanism.
- **SEC-005 signing the verdict.** Tier 2, with the verdict→target binding
  (`D-IMPL-350`).
- **Registry tenancy.** Its own cycle. Part B makes it unnecessary for
  correctness at the doors; a bank will still ask.
- **The unstamped HITL leg (P10).** Closing it means giving the door a *resolve*
  route, which changes `D-IMPL-62`'s ruled contract. **Ruling required** — the
  design recommends closing it and folding it into Tier 2's HITL work.
- **The eight edited example servers (P8).** They are frozen specimens
  (`D-IMPL-261`) and the edit was a violation. **Recommendation: revert the eight
  edits** and file a gap-ledger entry that they do not build under Tier 1 —
  which is honest evidence that a real deployment needs a scope mapping the
  examples never declared. Unfreezing them to complete the migration is Dave's
  call, not the remediation's.

---

## 4. Effort and lanes

| lane | parts | h | owns |
|---|---|---|---|
| **HTTP+engine** | A, B, F | 9 | `authz/`, `http_api/`, `workflow/engine.py`, `tests/http_api`, `tests/authz` |
| **store** | C | 4 | `src/ccf/artifacts/`, `src/ccf/replay/serve.py`, the two recorder call sites |
| **MCP** | D | 4 | `mcp/`, `tests/mcp` |
| **HITL door** | E | 3 | `routes/hitl.py`, `mcp/hitl_server.py`, `identity_binding.py`, `src/ccf/hitl/principal.py` |
| **lint** | G | 5 | `tools/lints/`, `Makefile`, `tools/lints/tests` — **fully independent** |
| **examples** | P8 revert + ledger | 1 | 8 example files, `docs/` |
| **join** | regenerate once, sabotage on the merged tree, **panel** | 6 | — |

**~32h; ~14h wall-clock across six lanes.** The lint lane is the one that
prevents the next instance and it depends on nothing.

**Disjoint ownership as before.** `tests/http_api/gate_fixtures.py` is owned by
the HTTP lane and is the one file two lanes will want; the MCP and store lanes
build their own fixtures.

---

## 5. What "done" means this time

Not a green suite. The Tier 1 suite was green while the door was unopenable.

1. **A production credential opens the HTTP door.** A test that mints a
   `TokenGrant` through `FileTokenSource` — the real source, no subclass — and
   is served.
2. **Fable's two reproductions are executable tests and they refuse.** The
   cross-tenant workflow invocation and the cross-tenant agent declaration, as
   written in its review, asserting 403 and *nothing filed under the other
   tenant*.
3. **The lint is red on the fork point.** Run `authorization_invariant.py`
   against `d895d889` and it must find D-IMPL-73's optional `auth=` — a lint that
   would not have caught the original defect is not the lint.
4. **Sabotage on the merged tree**, each guard severed alone, each reddening a
   named test — and this time including *"replace `TokenGrant` with the test
   subclass"* as a severing, so the fixture can never again pass where
   production fails.
5. **The panel accepts**, or names what it rejects, and its findings are
   verified against the tree before they are recorded.

---

**Next free decision id after this: `D-IMPL-354`.**
