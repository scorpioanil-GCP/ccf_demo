# 16-24 — the Experience front door's tools are entitled, not merely authenticated

## What did **not** change, stated first

A reader's first question about a change to a shipped door is whether their
door moved. On the resource path it did not.

- `EXPERIENCE_PRODUCT_URI_TEMPLATE` is the same three segments,
  `ccf-experience-product://{tenant}/{product_class}/{version}`, at the same
  value.
- The `context_product` **resource handler is byte-identical** — the same
  decorator, the same `verified_grant()` → `entitled_perspective(...)`
  sequence, the same forwarded perspective, the same `request=None` literal and
  the same `canonical_bytes(servable.product).decode("utf-8")` return. Proved
  rather than asserted: the filtered diff of `experience.py` against the phase
  base `8d24954` deletes eight lines, and not one of them is inside the
  resource body, its URI template or `ExperienceProductResolverProtocol`.
- `ExperienceProductResolverProtocol.__call__` is **unchanged** — the same five
  keyword-only arguments. No entry is filed for it below, and that absence is
  deliberate: a claim on a name that did not move fails the completeness gate
  in the other direction.
- **`get_context`'s wire signature is unchanged** — same name, same two
  arguments, same types. No client edits. What changed is that an unentitled
  caller now receives a refusal where it previously received a product.

## The defect, quoted rather than paraphrased

At the phase base, `runtime/ccf_runtime/mcp/experience.py::get_context` was:

```python
def get_context(tenant: str, entity: str) -> str:
    """Serve one tenant's entity-scoped product via the injected seam."""
    return context_seam(tenant=tenant, entity=entity)
```

Both arguments are client-supplied and the handler called neither
`verified_grant()` nor `entitled_perspective(...)`. The `context_product`
resource **on the same server** called both, at `:686-693`. One module, two
doors onto Context Product assembly, one of them gated.

The module's own docstring at `:48-58` argued the posture the tool beside it
violated: *"a fabric whose external door is less governed than its internal one
has its threat model backwards … shipping the SDK's own front door ungated
would be that complaint, self-inflicted."* `experience.py` **is** the external
door; `egress.py` is the fabric-internal one.

The measurement is not rhetorical. Run against the ungated handler, the
headline test received the whole assembled product — payload, lineage, policy
bundle versions, temporal boundary — on a credential the tenant's entitlement
policy does not declare.

## The tool-by-tool audit

`D-IMPL-128` ruled the finding **evidence about a class, not an incident**, and
required every tool the module can register to be checked for the same shape.
All five were. Measured across `experience.py:715-805` at the phase base, the
substrings `verified_grant` and `entitled_perspective` appeared **zero** times
in any of the five tool bodies.

| Surface | Client-supplied arguments | Reaches | Verdict |
| --- | --- | --- | --- |
| `context_product` resource | tenant, class, version | the product resolver | entitled (15.5-06, unchanged) |
| `get_context` tool | tenant, entity | the context provider | **entitled** (`D-IMPL-128` limb 1) |
| `get_lineage` tool | none | the lineage provider | **entitled** (`D-IMPL-129`) |
| `list_agents` tool | tenant | the agent directory | authenticated, **NOT** entitled |
| `invoke_agent` tool | tenant, key, version, skill, arguments | the agent invoker | authenticated, **NOT** entitled |
| `get_replay_record` tool | none | the replay reader | authenticated, **NOT** entitled |

**Why the two gated ones could be gated.** `get_context` reaches Context
Product assembly, which a `ProductEntitlementPolicy` decides by construction,
and it is decided against the caller's *own* `tenant` argument — so naming a
foreign tenant means being decided against that tenant's policy and refused,
rather than trusted. `get_lineage` returns a **field of the vessel the resource
serves whole**, so the policy deciding who may receive the class decides who
may receive a field of it; no vocabulary is invented. Because that tool carries
no wire arguments at all, its address is deployment-declared.

**Why the other three are not.** See Escalation (A).

## Adopter migration

Three things move for a deployment that composes this server.

1. **Two new builder arguments, required conditionally on exposure.**
   `entitled_product_class` is required when `get_context` **or** `get_lineage`
   is allowlisted; `lineage_tenant` is required when `get_lineage` is. Both are
   refused if supplied for a tool the allowlist does not admit — requiredness
   fails in both directions, so neither a lost front door nor an inert
   governance value is silent. `entitled_product_class` is
   **deployment-supplied by design**: the class the entitlement is decided
   against must be the class the injected provider actually serves, and only
   the deployment knows that. A client-supplied class would let a caller name a
   class it *is* entitled to while the provider returned one it is not. The
   `context_product` resource may take its class from the client precisely
   because that same value *addresses the resolver*, so check and serve cannot
   diverge there.

2. **`ContextProviderProtocol` gains a required, undefaulted `perspective`.**
   A door that computes an authorized perspective and discards it is
   `DI-15.5-03` reintroduced one layer down, where nothing on the wire would
   show it. No default, because a defaulted governance argument is one an
   implementor can be written without noticing.

   **Accepting the argument is not the obligation; using it is.** A provider
   that takes `perspective` and serves regardless has received the conditioning
   and ignored it — the same defect, one layer further down. Both shipped
   providers now compare the perspective's role against the capacity their
   product was assembled under and refuse a mismatch, reproducing the check the
   resource-leg resolver beside them already performed.
   `LineageProviderProtocol` is deliberately **not** widened: it returns a field
   of an already-resolved product and has no resolution to condition, and
   forwarding a perspective into it would imply a per-principal scoping of
   lineage the fabric cannot perform.

3. **The first thing an adopter will hit, named so it is recognised as the gate
   working.** A deployment whose `ProductEntitlementPolicy` does not name the
   class its context provider serves will now be refused at its own front door
   with `product-class-unentitled`. That is not a regression — it is the
   entitlement and the provider having always disagreed, and the door finally
   noticing.

## Escalation (A) — three tools are authenticated and **not** entitled

`D-IMPL-129` rules this disposition. It is recorded here unhedged and it is not
work in hand.

What each discloses to any verified caller:

- `list_agents` — a **client-chosen** tenant's agent population with declared
  versions, archetype compositions and bound skill tool surfaces.
- `invoke_agent` — the sharpest of the three, and arguably sharper than the
  defect `D-IMPL-128` ruled: **every** argument is the client's, the tenant
  included, and the call reaches agent construction and skill dispatch through
  the deployment's injected invoker.
- `get_replay_record` — the most-recent five-dimension Decision Replay record,
  the widest disclosure on this server, dimension 4 carrying perspective
  conditioning and principal identity.

**Why this plan did not gate them.** The artifact they would be decided against
is `ProductEntitlementPolicy`, whose grants are `permitted_schema_names` and
`permitted_roles` (`runtime/ccf_runtime/authz/product_entitlement.py::ProductEntitlementSourceProtocol`)
and which says nothing about agents and nothing about replay records. Deciding
an agent invocation against it would assert *entitlement to receive product
class C implies permission to invoke any agent in tenant T* — a semantic the
SDK would be **inventing**, which CLAUDE.md §11 forbids in those words. Each of
the three therefore gained `verified_grant` as its first statement:
authentication, deciding nothing, and labelled as such in its own docstring.

**What would close it.** `TenantAuthorizerProtocol`
(`runtime/ccf_runtime/authz/protocol.py::TenantAuthorizerProtocol`) with new action ids beside the
three at `src/ccf/authz/actions.py::ACTION_PRODUCT_RETRIEVE`, plus an
adopter-registered policy artifact — the shape the HITL door carried at the
time as a per-body `_enforce_tenant_authz` helper in
`runtime/ccf_runtime/mcp/hitl_server.py` (removed under `D-IMPL-353` §2 P4: the
tenancy wrapper now mints the body's capability from the authorizer's decision,
and no body holds an authorizer). `D-IMPL-129` records that precedent under a
path that does not exist; the correct one is the `mcp/` path above. That is a new required builder seam and a new artifact type, authorised
by nothing so far, and **no owner is assigned**.

**The corroborating measurement, because it shows the cost of the SDK requiring
nothing.** The crossproc fixture's
`tests/crossproc/servers/mcp_experience_child.py::read_replay_record` serves the
record to any caller with no identity check, while the shipped example's
`examples/external/00-hello-context/serve.py::replay_record_reader`
voluntarily scopes it to the verified caller. Two shipped deployments in one
tree already disagree about who may read a replay record, and nothing in the
SDK adjudicates.

The gap is not left as prose. It is pinned by
`tests/crossproc/test_experience_edge.py::test_the_agent_and_replay_tools_are_authenticated_but_not_entitled_open_gap`,
which asserts the three **succeed** for an unentitled credential — and asserts
what they disclose, not merely that they returned — and whose docstring records
that **inverting it is the signature of the fix**.

## Escalation (B) — `D-IMPL-128` limb 2 stands open

Restated as ruled, not re-argued. Client-chosen `entity` / `subject` is **not
entitlement-scoped**: `entitled_perspective`
(`runtime/ccf_runtime/authz/product_entitlement.py::entitled_perspective`) decides on
`(grant, tenant, product_class, resolved role)` and carries no subject
dimension, while `subject` becomes the traversal seed and therefore selects
what is assembled.

It is a **named residual, unassigned by ruling**, because closing it needs a
perspective-scoped assembly path that does not exist: `D-IMPL-119` limb 2
measured the entitled-versus-assembled delta as *empty on the shipped path* and
put the scoped view explicitly out of scope, and `D-IMPL-124` Shape D was
**blocked** on the same absence. This plan gates the door and builds no scoped
assembly.

Per the ruling's own words, and recorded here explicitly: **this plan does not
cite the gating as evidence that entity-scoping is unnecessary.**

## Reconciliation with plan `16-23`

`16-23` Task 3 recorded this defect as residual (c) with a candidate `D-IMPL`,
having found it while establishing exactly where each protection is enforced on
the resource path before claiming its own new tool traversed the same checks.
`D-IMPL-128` has since ruled it. This plan closes limb 1 and leaves limb 2 open
as above. `16-23`'s plan, its fragment and the phase's `deferred-items.md` are
untouched by this plan.

## Surface measurement — the two comparisons, kept apart

Both are recorded because they answer different gates and conflating them is
how a fragment gets written against the wrong state.

**Frozen-baseline-vs-live** — the *completeness* picture,
`tests/test_surface_completeness.py::_diff()` against
`docs/surface/v0.2-surface-baseline.json`:

| | added | removed | reshaped |
| --- | --- | --- | --- |
| at phase base `8d24954` | 247 | 0 | 55 |
| after this plan | 247 | 0 | 55 |

**The counts did not move, and this fragment is not what keeps that gate
green.** `build_experience_server` and `ContextProviderProtocol` were already in
`reshaped` — claimed by `15.5-06-egress-entitlement.md` and
`15.6-10-protocol-call-capture.md` — and they stay in `reshaped`. Zero new diff
lines. Two entries are filed below anyway, and they are the right thing to file:
the earlier fragments' `Before`/`After` describe entirely different changes, and
the completeness gate accepts multiple entries per name.

**Committed-manifest-vs-live** — the *drift* picture,
`tools/dump_surface.py --report`:

| | added | removed | reshaped |
| --- | --- | --- | --- |
| at phase base `8d24954` | 6 | 0 | 2 |
| after this plan | 6 | 0 | 4 |

Drift gains **exactly** the two names this plan moved, as predicted. It was
already non-empty at the phase base because the committed manifest trails the
live surface across Phase 16; the gate survives because `unclaimed_drift`
claims a name when the name or its dotted module appears in the fragment union,
and both appear here as well as in the two `15*` fragments.

The fragment exists because `D-15` requires the curated log to carry the
adopter migration a signature diff cannot say — not because a gate forced it.

## ccf_runtime.mcp.experience.build_experience_server

- Surface: ccf_runtime.mcp.experience.build_experience_server
- Public surface: true
- Change type: reshaped
- Before: nine optional seam/prose parameters plus the two required governance seams; the gated consumption tools had no declared address, so `get_context` and `get_lineage` registered handlers that reached their providers with no entitlement decision
- After: two additional keyword-only parameters, `entitled_product_class` and `lineage_tenant`, both `str | None = None` and both required conditionally on exposure — and refused when supplied for a tool the allowlist does not admit
- Why: `D-IMPL-128` limb 1 ruled the ungated `get_context` a defect in the SDK's external front door, and an entitlement decides on a *(tenant, class)* pair the deployment must supply — the class because check and serve would otherwise be free to diverge, the tenant because `get_lineage` carries no wire arguments at all and inventing one would be the SDK holding a deployment value (CINV-01). A second entry for this name after `15.5-06-egress-entitlement.md` is deliberate: that fragment recorded the arrival of the governance seams, this one records the declared address the two now-gated tools are decided against
- Migration: supply `entitled_product_class` when either gated tool is allowlisted and `lineage_tenant` when `get_lineage` is; both are ordinary deployment values and the shipped example binds them to `assembled.address.product_class` and `assembled.address.tenant`. A deployment whose entitlement policy does not name the class its context provider serves will now be refused at its own front door — that is the gate working

## ccf_runtime.mcp.experience.ContextProviderProtocol

- Surface: ccf_runtime.mcp.experience.ContextProviderProtocol
- Public surface: true
- Change type: reshaped
- Before: `__call__(*, tenant: str, entity: str) -> str` — the provider received no conditioning, because the door that calls it computed none
- After: `__call__(*, tenant: str, entity: str, perspective: Perspective) -> str` — required, no default, carrying the perspective the door's entitlement authorized
- Why: `D-IMPL-108`'s reasoning applied to the newly gated tool: a door that computes an authorized perspective and discards it is `DI-15.5-03` reintroduced one layer down, where nothing on the wire would show it. No default, because a defaulted governance argument is one an implementor can be written without noticing. A second entry for this name after `15.6-10-protocol-call-capture.md` is deliberate: that fragment recorded a different change to the same Protocol
- Migration: add `perspective: Perspective` to your provider's signature — and **use it**. Compare its `role` against the capacity your product was assembled under and refuse a mismatch; a provider that accepts the conditioning and serves regardless has moved the defect one layer down rather than closing it. `LineageProviderProtocol` is unchanged and needs no edit
